"""Local autonomous manga cleanup and crop pipeline."""

from __future__ import annotations

import io
import json
import math
import os
import shutil
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from flask import Blueprint, jsonify, request
from PIL import Image, ImageDraw, ImageFont, ImageOps

from . import error_codes as EC
from .api_errors import fail
from .config import DATA_DIR, IMAGE_EXTS, logger, state
from .kcc_scan import _detect_fill_color, _ensure_kcc_importable
from .models import clean_image, create_mask_image
from .page_number_memory import (
    delete_page_number_example,
    load_page_number_examples,
    page_digest,
    page_number_memory_metadata,
    save_page_number_example,
)
from .page_number_sequence import PageNumberSequence, page_number_chapter, page_number_minimum
from .path_access import is_under_allowed_root
from .sevenzip import run_7z


ARTIFACT_PROFILE_DIR = os.path.join(DATA_DIR, "artifact_profiles")
_LOCAL_GLYPH_TEMPLATES: tuple[Any, list[str]] | None = None
_LOCAL_GLYPH_TEMPLATE_LOCK = threading.Lock()
_USER_PAGE_NUMBER_MODEL_CACHE: dict[tuple[str, int], dict[str, Any]] = {}
_USER_PAGE_NUMBER_MODEL_LOCK = threading.RLock()


@dataclass(frozen=True)
class CropCandidate:
    """Inclusive content bounds before a small source margin is preserved."""

    name: str
    left: int
    top: int
    right: int
    bottom: int
    ambiguous: bool = False


def _is_quiet_margin_box(image: Image.Image, box: list[int], *, gray=None) -> bool:
    """Return whether a glyph group is surrounded by a mostly blank margin."""
    from . import models

    width, height = image.size
    x1, y1, x2, y2 = box
    ring_pad_x = max(12, x2 - x1)
    ring_pad_y = max(12, y2 - y1)
    rx1, ry1 = max(0, x1 - ring_pad_x), max(0, y1 - ring_pad_y)
    rx2, ry2 = min(width, x2 + ring_pad_x), min(height, y2 + ring_pad_y)
    if gray is None:
        gray = models.np.array(image.convert("L"))
    # A folio is normally printed just under the last panel, so padding the
    # ring by the glyph height reaches into that artwork. The page body is not
    # the folio's margin: start the ring below the last solidly inked row.
    above = gray[ry1:y1, rx1:rx2]
    if above.size:
        solid = models.np.flatnonzero(models.np.mean(above < 200, axis=1) >= 0.5)
        if solid.size:
            ry1 += int(solid[-1]) + 1
    ring = gray[ry1:ry2, rx1:rx2]
    if ring.size == 0:
        return False
    ring_mask = models.np.ones(ring.shape, dtype=bool)
    ring_mask[y1 - ry1 : y2 - ry1, x1 - rx1 : x2 - rx1] = False
    surrounding = ring[ring_mask]
    if surrounding.size == 0:
        return False
    return float(models.np.median(surrounding)) >= 220 and float(models.np.mean(surrounding < 200)) <= 0.12


def _filter_vertical_text_sequences(boxes: list[list[int]]) -> list[list[int]]:
    """Reject glyph groups that form a vertical caption rather than a folio."""
    rejected: set[int] = set()
    for index, box in enumerate(boxes):
        aligned = []
        for other_index, other in enumerate(boxes):
            overlap = max(0, min(box[2], other[2]) - max(box[0], other[0]))
            narrower_width = max(1, min(box[2] - box[0], other[2] - other[0]))
            if overlap / narrower_width >= 0.60:
                aligned.append(other_index)
        if len(aligned) < 3:
            continue
        tallest = max(boxes[item][3] - boxes[item][1] for item in aligned)
        # Alignment alone is not enough: a real folio can happen to sit below
        # a vertical caption in the same column. Only reject contiguous runs;
        # a large blank margin between glyphs starts a new sequence.
        gap_limit = max(12, tallest * 1.5)
        ordered = sorted(aligned, key=lambda item: boxes[item][1])
        runs: list[list[int]] = [[ordered[0]]]
        for item in ordered[1:]:
            previous = runs[-1][-1]
            vertical_gap = max(0, boxes[item][1] - boxes[previous][3])
            if vertical_gap <= gap_limit:
                runs[-1].append(item)
            else:
                runs.append([item])
        for run in runs:
            if len(run) < 3:
                continue
            tops = [boxes[item][1] for item in run]
            bottoms = [boxes[item][3] for item in run]
            if max(bottoms) - min(tops) >= tallest * 2.5:
                rejected.update(run)
    return [box for index, box in enumerate(boxes) if index not in rejected]


def _filter_split_horizontal_words(boxes: list[list[int]], maximum_span: float) -> list[list[int]]:
    """Reject a long credit/word split by the bounded grouping stage."""
    rejected: set[int] = set()
    for index, box in enumerate(boxes):
        for other_index in range(index + 1, len(boxes)):
            other = boxes[other_index]
            tallest = max(box[3] - box[1], other[3] - other[1])
            mid = (box[1] + box[3]) / 2
            other_mid = (other[1] + other[3]) / 2
            gap = max(0, other[0] - box[2], box[0] - other[2])
            span = max(box[2], other[2]) - min(box[0], other[0])
            if abs(mid - other_mid) <= max(5, tallest * 0.60) and gap <= max(10, tallest * 1.25) and span > maximum_span:
                rejected.update((index, other_index))
    return [box for index, box in enumerate(boxes) if index not in rejected]


def _is_sparse_outer_margin_band(image: Image.Image, box: list[int], *, gray=None, fill=None) -> bool:
    """A folio must sit in a locally empty horizontal strip, not inside text."""
    from . import models

    models._ensure_imports()
    width, height = image.size
    x1, y1, x2, y2 = box
    top, bottom = max(0, y1 - 3), min(height, y2 + 3)
    box_width = max(1, x2 - x1)
    left, right = max(0, x1 - box_width * 2), min(width, x2 + box_width * 2)
    if gray is None:
        gray = models.np.array(image.convert("L"))
    band = gray[top:bottom, left:right]
    if band.size == 0:
        return False
    if fill is None:
        fill = _detect_fill_color(image, "none")
    foreground = band < 235 if fill == "white" else band > 20
    # Candidate generation is intentionally permissive; the local digit
    # classifier makes the semantic decision. Bold/antialiased folios near an outer edge can occupy
    # a little more than twelve percent of this clipped local band.
    return float(models.np.mean(foreground)) <= 0.16


def _is_horizontal_text_fragment(image: Image.Image, box: list[int]) -> bool:
    """Look at all neighbouring ink, including words too long to be candidates."""
    from . import models

    models._ensure_imports()
    x1, y1, x2, y2 = box
    glyph_height = max(1, y2 - y1)
    left = max(0, x1 - glyph_height * 6)
    right = min(image.width, x2 + glyph_height * 6)
    top = max(0, y1 - glyph_height // 2)
    bottom = min(image.height, y2 + glyph_height // 2)
    mask = _local_ocr_mask(image, [left, top, right, bottom])
    _, _, stats, _ = models.cv2.connectedComponentsWithStats(mask, 8)
    pieces = []
    for x, y, width, height, area in stats[1:]:
        if height < glyph_height * 0.55 or height > glyph_height * 1.5:
            continue
        if area < max(3, glyph_height * glyph_height * 0.04):
            continue
        if abs(top + y + height - y2) > max(3, glyph_height * 0.35):
            continue
        pieces.append((int(left + x), int(left + x + width)))
    # Grow the run touching the proposed glyph. A four-digit folio and its
    # brackets fit comfortably in this span; a caption continuing on either
    # side does not. Rejected long groups must still count as surrounding text.
    run_left, run_right = x1, x2
    remaining = pieces
    while remaining:
        following = []
        grew = False
        for start, end in remaining:
            gap = max(0, start - run_right, run_left - end)
            if gap <= max(3, glyph_height * 0.5):
                run_left, run_right = min(run_left, start), max(run_right, end)
                grew = True
            else:
                following.append((start, end))
        if not grew:
            break
        remaining = following
    return run_right - run_left > max(24, glyph_height * 3.5)


def _has_clear_bottom_margin_below(image: Image.Image, box: list[int], *, gray=None, fill=None) -> bool:
    """A page folio must not have continuing panel artwork below it."""
    from . import models

    models._ensure_imports()
    width, height = image.size
    x1, _y1, x2, y2 = box
    box_width = max(1, x2 - x1)
    left, right = max(0, x1 - box_width * 2), min(width, x2 + box_width * 2)
    top = min(height, y2 + 3)
    if gray is None:
        gray = models.np.array(image.convert("L"))
    below = gray[top:height, left:right]
    if below.size == 0:
        return True
    if fill is None:
        fill = _detect_fill_color(image, "none")
    foreground = below < 235 if fill == "white" else below > 20
    ink_ratio = float(models.np.mean(foreground))
    active_row_ratio = float(models.np.mean(models.np.any(foreground, axis=1)))
    return ink_ratio <= 0.03 and active_row_ratio <= 0.20


def _is_outer_corner_folio_proposal(image: Image.Image, box: list[int]) -> bool:
    """Allow a tiny edge glyph to reach semantic OCR even beside a panel rule.

    This is deliberately only candidate generation. The mark is not removed
    unless the local classifier subsequently reads it as one to four digits.
    """
    width, height = image.size
    x1, y1, x2, _y2 = box
    edge_band = max(18, round(width * 0.075))
    return y1 >= round(height * 0.75) and (x2 <= edge_band or x1 >= width - edge_band)


def _folio_cluster_gap(
    first: dict[str, float], second: dict[str, float], width: int, height: int
) -> float | None:
    """Return the joining gap when two ink clusters can share one folio."""
    # Prevent chains of nearby artwork strokes from growing into one huge
    # group and swallowing a small, otherwise valid folio.
    if first["components"] + second["components"] > 4:
        return None
    combined_width = max(first["right"], second["right"]) - min(first["left"], second["left"])
    combined_height = max(first["bottom"], second["bottom"]) - min(first["top"], second["top"])
    if combined_width > max(24, width * 0.10) or combined_height > max(12, height * 0.05):
        return None
    tallest = max(first["bottom"] - first["top"], second["bottom"] - second["top"])
    first_mid_y = (first["top"] + first["bottom"]) / 2
    second_mid_y = (second["top"] + second["bottom"]) / 2
    if abs(first_mid_y - second_mid_y) > max(5, tallest * 0.60):
        return None
    gap = max(0.0, second["left"] - first["right"], first["left"] - second["right"])
    return gap if gap <= max(10, tallest * 1.25) else None


def _absorb_folio_cluster(group: dict[str, float], other: dict[str, float]) -> None:
    group["left"] = min(group["left"], other["left"])
    group["top"] = min(group["top"], other["top"])
    group["right"] = max(group["right"], other["right"])
    group["bottom"] = max(group["bottom"], other["bottom"])
    group["area"] += other["area"]
    group["components"] += other["components"]


def _find_page_number_candidates(
    image: Image.Image,
    y_offset: int,
    max_candidates: int = 16,
    *,
    allow_internal_gutters: bool = False,
) -> list[dict[str, Any]]:
    """Find small quiet ink groups for local digit classification."""
    from . import models

    models._ensure_imports()
    width, height = image.size
    y_offset = max(0, min(height - 1, int(y_offset)))
    # All candidate checks inspect the same sheet. Decode it once and lazily
    # determine its background once, rather than scanning a full spread for
    # every small ink group near the bottom edge.
    page_gray = models.np.array(image.convert("L"))
    fill = None
    gray = page_gray[y_offset:height, :]
    _threshold, binary = models.cv2.threshold(
        gray, 0, 255, models.cv2.THRESH_BINARY_INV | models.cv2.THRESH_OTSU
    )
    count, _labels, stats, _centroids = models.cv2.connectedComponentsWithStats(binary, 8)
    components: list[dict[str, float]] = []
    min_height = max(3, round(height * 0.002))
    max_height = max(12, min_height, round(height * 0.040))
    max_width = max(8, round(width * 0.07))
    for index in range(1, count):
        cx, cy, cw, ch, area = (int(value) for value in stats[index])
        if not (min_height <= ch <= max_height and 1 <= cw <= max_width and area >= 3):
            continue
        if area > max(64, width * height * 0.002):
            continue
        components.append({
            "left": float(cx),
            "top": float(y_offset + cy),
            "right": float(cx + cw),
            "bottom": float(y_offset + cy + ch),
            "area": float(area),
            "components": 1.0,
        })

    groups: list[dict[str, float]] = []
    for component in sorted(components, key=lambda item: (item["top"], item["left"])):
        best_group = None
        best_gap = float("inf")
        for group in groups:
            gap = _folio_cluster_gap(group, component, width, height)
            if gap is not None and gap < best_gap:
                best_group, best_gap = group, gap
        if best_group is None:
            groups.append(dict(component))
        else:
            _absorb_folio_cluster(best_group, component)

    # The pass above visits components in (top, left) order, so the closing
    # bracket of a folio like "( 67 )" is grouped while only the taller opening
    # bracket exists, is too far from it to join, and never sees the digits
    # that later bridge the gap. Merge whole clusters until nothing else joins.
    merging = True
    while merging:
        merging = False
        for index, group in enumerate(groups):
            partner = next(
                (
                    other for other in groups[index + 1:]
                    if _folio_cluster_gap(group, other, width, height) is not None
                ),
                None,
            )
            if partner is None:
                continue
            _absorb_folio_cluster(group, partner)
            groups.remove(partner)
            merging = True
            break

    boxes: list[list[int]] = []
    min_group_height = max(7, round(height * 0.005))
    for group in groups:
        group_width = group["right"] - group["left"]
        group_height = group["bottom"] - group["top"]
        if not (min_group_height <= group_height <= max(12, height * 0.05)):
            continue
        # Keep multi-digit page numbers, but do not offer long author/title
        # words to the model as removable number candidates.
        if group_width > max(24, width * 0.10) or not (1 <= group["components"] <= 4):
            continue
        if group_width > max(24, group_height * 3):
            continue
        box = [
            max(0, int(group["left"]) - 1),
            max(y_offset, int(group["top"]) - 1),
            min(width, int(group["right"]) + 1),
            min(height, int(group["bottom"]) + 1),
        ]
        if fill is None:
            fill = _detect_fill_color(image, "none")
        quiet_margin = (
            _is_quiet_margin_box(image, box, gray=page_gray)
            and _is_sparse_outer_margin_band(image, box, gray=page_gray, fill=fill)
        )
        edge_proposal = _is_outer_corner_folio_proposal(image, box)
        if not (quiet_margin or edge_proposal):
            continue
        if _is_horizontal_text_fragment(image, box):
            continue
        if allow_internal_gutters or _has_clear_bottom_margin_below(image, box, gray=page_gray, fill=fill):
            boxes.append(box)

    boxes = _filter_vertical_text_sequences(boxes)
    boxes = _filter_split_horizontal_words(boxes, max(24, width * 0.10))
    # Bottom-most candidates are the most likely page folios. Keep left-to-right
    # order for equal baselines so the labels stay stable and easy to inspect.
    boxes.sort(key=lambda box: (-box[3], box[0]))
    return [{"id": f"P{index:02d}", "box": box} for index, box in enumerate(boxes[:max_candidates], 1)]


def _normalize_local_ocr_glyph(mask) -> Any | None:
    """Normalize a binary glyph for the tiny built-in digit classifier."""
    from . import models

    coordinates = models.np.argwhere(mask > 0)
    if coordinates.size == 0:
        return None
    top, left = coordinates.min(axis=0)
    bottom, right = coordinates.max(axis=0) + 1
    glyph = (mask[top:bottom, left:right] > 0).astype(models.np.uint8) * 255
    glyph_height, glyph_width = glyph.shape
    if glyph_height < 2 or glyph_width < 1:
        return None
    scale = min(24.0 / glyph_width, 26.0 / glyph_height)
    target_width = max(1, int(round(glyph_width * scale)))
    target_height = max(1, int(round(glyph_height * scale)))
    interpolation = models.cv2.INTER_AREA if scale < 1 else models.cv2.INTER_CUBIC
    resized = models.cv2.resize(glyph, (target_width, target_height), interpolation=interpolation)
    normalized = models.np.zeros((32, 32), dtype=models.np.uint8)
    x = (32 - target_width) // 2
    y = (32 - target_height) // 2
    normalized[y : y + target_height, x : x + target_width] = resized
    _threshold, normalized = models.cv2.threshold(normalized, 96, 255, models.cv2.THRESH_BINARY)
    return normalized


def _local_ocr_feature(mask) -> Any:
    """Return a compact shape descriptor insensitive to the original size."""
    from . import models

    descriptor = models.cv2.HOGDescriptor((32, 32), (16, 16), (8, 8), (8, 8), 9)
    feature = descriptor.compute(mask).reshape(-1).astype(models.np.float32)
    length = float(models.np.linalg.norm(feature))
    return feature / length if length > 0 else feature


def _non_glyph_shape_masks() -> list[tuple[str, Any]]:
    """Render the pen marks a folio must not be confused with."""
    from . import models

    np, cv2 = models.np, models.cv2
    shapes: list[tuple[str, Any]] = []
    span, centre = 34, 36
    for degrees in range(0, 180, 10):
        dx, dy = float(np.cos(np.deg2rad(degrees))), float(np.sin(np.deg2rad(degrees)))
        perpendicular = np.array([-dy, dx])
        start = (int(centre - dx * span), int(centre - dy * span))
        end = (int(centre + dx * span), int(centre + dy * span))
        for width in (2, 4, 7, 11, 16):
            line = np.zeros((72, 72), np.uint8)
            cv2.line(line, start, end, 255, width)
            shapes.append(("stroke", line))
            # A speed line thins along its length; a scan or a halftone it
            # crosses breaks it into pieces.
            taper = np.zeros((72, 72), np.uint8)
            dashed = np.zeros((72, 72), np.uint8)
            for step in range(24):
                head = step / 24
                tail = (step + 1) / 24
                segment = (
                    (int(centre + dx * (-span + 2 * span * head)),
                     int(centre + dy * (-span + 2 * span * head))),
                    (int(centre + dx * (-span + 2 * span * tail)),
                     int(centre + dy * (-span + 2 * span * tail))),
                )
                cv2.line(taper, *segment, 255, max(1, int(round(width * (1 - head)))))
                if step % 2 == 0:
                    cv2.line(dashed, *segment, 255, width)
            shapes.append(("taper", taper))
            shapes.append(("dashed", dashed))
        # Solid artwork cut by the sheet edge or by a panel rule.
        for spread in (10, 18, 30):
            wedge = np.zeros((72, 72), np.uint8)
            tip = np.array([centre - dx * span, centre - dy * span])
            base = np.array([centre + dx * span, centre + dy * span])
            corners = np.array(
                [tip, base + perpendicular * spread, base - perpendicular * spread], np.int32
            )
            cv2.fillPoly(wedge, [corners], 255)
            shapes.append(("wedge", wedge))
            notched = wedge.copy()
            cv2.circle(
                notched,
                (int(centre + dx * 20 + perpendicular[0] * spread * 0.5),
                 int(centre + dy * 20 + perpendicular[1] * spread * 0.5)),
                max(4, spread // 2), 0, -1,
            )
            shapes.append(("notched", notched))
        half = np.zeros((72, 72), np.uint8)
        far = perpendicular * 90
        cv2.fillPoly(half, [np.array([
            [centre - dx * 90, centre - dy * 90], [centre + dx * 90, centre + dy * 90],
            [centre + dx * 90 + far[0], centre + dy * 90 + far[1]],
            [centre - dx * 90 + far[0], centre - dy * 90 + far[1]]], np.int32)], 255)
        shapes.append(("half", half))
        arc = np.zeros((72, 72), np.uint8)
        cv2.ellipse(arc, (centre, centre), (30, 30), degrees, 0, 120, 255, 4)
        shapes.append(("arc", arc))
        parallel = np.zeros((72, 72), np.uint8)
        for offset in (-14, 0, 14):
            shift = perpendicular * offset
            cv2.line(
                parallel,
                (int(start[0] + shift[0]), int(start[1] + shift[1])),
                (int(end[0] + shift[0]), int(end[1] + shift[1])), 255, 3,
            )
        shapes.append(("lines", parallel))
    for first in range(0, 180, 20):
        for second in range(first + 40, 180, 40):
            cross = np.zeros((72, 72), np.uint8)
            for degrees in (first, second):
                dx, dy = float(np.cos(np.deg2rad(degrees))), float(np.sin(np.deg2rad(degrees)))
                cv2.line(cross, (int(centre - dx * span), int(centre - dy * span)),
                         (int(centre + dx * span), int(centre + dy * span)), 255, 4)
            shapes.append(("cross", cross))
    return shapes


def _get_local_glyph_templates() -> tuple[Any, list[str]]:
    """Build small in-memory digit/letter templates without an ML download."""
    global _LOCAL_GLYPH_TEMPLATES

    if _LOCAL_GLYPH_TEMPLATES is not None:
        return _LOCAL_GLYPH_TEMPLATES
    with _LOCAL_GLYPH_TEMPLATE_LOCK:
        if _LOCAL_GLYPH_TEMPLATES is not None:
            return _LOCAL_GLYPH_TEMPLATES
        from . import models

        models._ensure_imports()
        font_names = (
            "DejaVuSans.ttf",
            "DejaVuSans-Bold.ttf",
            "DejaVuSerif.ttf",
            "DejaVuSerif-Bold.ttf",
            "DejaVuSansMono.ttf",
            "arial.ttf",
            "arialbd.ttf",
            "times.ttf",
            "timesbd.ttf",
            "calibri.ttf",
            "calibrib.ttf",
            "consola.ttf",
        )
        # Letters are negative examples: a locally isolated caption fragment
        # must not be accepted merely because it resembles 1, 3, or 7.
        characters = (
            "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
            "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
            ".,:;-!?"
            + _FOLIO_BRACKET_GLYPHS
        )
        features = []
        labels: list[str] = []
        loaded_fonts = []
        for name in font_names:
            try:
                loaded_fonts.append(ImageFont.truetype(name, 46))
            except OSError:
                continue
        if not loaded_fonts:
            loaded_fonts.append(ImageFont.load_default())
        for font in loaded_fonts:
            for character in characters:
                canvas = Image.new("L", (72, 72), 0)
                draw = ImageDraw.Draw(canvas)
                box = draw.textbbox((0, 0), character, font=font, stroke_width=0)
                text_width = max(1, box[2] - box[0])
                text_height = max(1, box[3] - box[1])
                draw.text(
                    ((72 - text_width) // 2 - box[0], (72 - text_height) // 2 - box[1]),
                    character,
                    font=font,
                    fill=255,
                )
                source = models.np.array(canvas)
                for angle in (-4, 0, 4):
                    center = (source.shape[1] / 2.0, source.shape[0] / 2.0)
                    matrix = models.cv2.getRotationMatrix2D(center, angle, 1.0)
                    rotated = models.cv2.warpAffine(
                        source,
                        matrix,
                        (source.shape[1], source.shape[0]),
                        flags=models.cv2.INTER_CUBIC,
                        borderValue=0,
                    )
                    normalized = _normalize_local_ocr_glyph(rotated)
                    if normalized is None:
                        continue
                    features.append(_local_ocr_feature(normalized))
                    labels.append(character)
        for shape_name, canvas in _non_glyph_shape_masks():
            normalized = _normalize_local_ocr_glyph(canvas)
            if normalized is None:
                continue
            features.append(_local_ocr_feature(normalized))
            labels.append(shape_name)
        _LOCAL_GLYPH_TEMPLATES = (models.np.stack(features), labels)
        return _LOCAL_GLYPH_TEMPLATES


def _split_local_ocr_glyphs(mask) -> list[Any]:
    """Split a candidate into one to four horizontally arranged glyphs."""
    from . import models

    active_columns = models.np.any(mask > 0, axis=0)
    padded = models.np.concatenate((models.np.array([False]), active_columns, models.np.array([False])))
    changes = models.np.flatnonzero(padded[1:] != padded[:-1])
    runs = [(int(changes[index]), int(changes[index + 1])) for index in range(0, len(changes), 2)]
    # Antialiasing or scan damage may split one glyph by a one-pixel gap. At
    # folio size a digit is only about nine pixels wide, so the gap between two
    # digits can also be a single pixel: closing it unconditionally glued "084"
    # into one blob and lost the page number. Only close the gap while the
    # result still fits a single glyph, which is taller than it is wide.
    glyph_height = mask.shape[0]
    merged: list[list[int]] = []
    for start, end in runs:
        if (
            merged
            and start - merged[-1][1] <= 1
            and (end - merged[-1][0]) <= glyph_height
        ):
            merged[-1][1] = end
        else:
            merged.append([start, end])
    if not 1 <= len(merged) <= 6:
        return []
    return [mask[:, start:end] for start, end in merged]


def _local_ocr_mask(image: Image.Image, box: list[int]) -> Any | None:
    """Return the least-dense Otsu polarity for a candidate or reference crop."""
    from . import models

    models._ensure_imports()
    x1, y1, x2, y2 = box
    gray = models.np.array(image.convert("L"))[y1:y2, x1:x2]
    if gray.size == 0:
        return None
    _threshold, dark = models.cv2.threshold(
        gray, 0, 255, models.cv2.THRESH_BINARY_INV | models.cv2.THRESH_OTSU
    )
    _threshold, light = models.cv2.threshold(
        gray, 0, 255, models.cv2.THRESH_BINARY | models.cv2.THRESH_OTSU
    )
    return dark if int(models.np.count_nonzero(dark)) <= int(models.np.count_nonzero(light)) else light


def _get_user_page_number_model(scope_path: str) -> dict[str, Any]:
    """Compile persisted examples into lightweight HOG prototypes."""
    if not scope_path:
        return {
            "examples": [], "positiveFeatures": None, "positiveLabels": [],
            "negativeFeatures": None, "revision": 0,
        }
    from . import models

    models._ensure_imports()
    revision = int(page_number_memory_metadata(scope_path).get("revision") or 0)
    cache_key = (os.path.realpath(str(scope_path)), int(revision))
    with _USER_PAGE_NUMBER_MODEL_LOCK:
        cached = _USER_PAGE_NUMBER_MODEL_CACHE.get(cache_key)
        if cached is not None:
            return cached
    examples, revision = load_page_number_examples(scope_path, include_images=True)
    positive_features = []
    positive_labels: list[str] = []
    negative_features = []
    for example in examples:
        reference = example.get("referenceImage")
        if not isinstance(reference, Image.Image):
            continue
        mask = _local_ocr_mask(reference, [0, 0, reference.width, reference.height])
        if mask is None:
            continue
        normalized_group = _normalize_local_ocr_glyph(mask)
        if example.get("action") == "not_number":
            if normalized_group is not None:
                negative_features.append(_local_ocr_feature(normalized_group))
            continue
        digits = str(example.get("digits") or "")
        glyphs = _split_local_ocr_glyphs(mask)
        if len(glyphs) != len(digits):
            continue
        for glyph, digit in zip(glyphs, digits):
            normalized = _normalize_local_ocr_glyph(glyph)
            if normalized is not None:
                positive_features.append(_local_ocr_feature(normalized))
                positive_labels.append(digit)
    model = {
        "examples": examples,
        "positiveFeatures": models.np.stack(positive_features) if positive_features else None,
        "positiveLabels": positive_labels,
        "negativeFeatures": models.np.stack(negative_features) if negative_features else None,
        "revision": int(revision),
    }
    with _USER_PAGE_NUMBER_MODEL_LOCK:
        # Keep a few scopes. Converting several sources in one run alternates
        # between them, and a single-entry cache recompiled every example
        # (PNG decode plus HOG) on every page.
        _USER_PAGE_NUMBER_MODEL_CACHE[cache_key] = model
        while len(_USER_PAGE_NUMBER_MODEL_CACHE) > 4:
            _USER_PAGE_NUMBER_MODEL_CACHE.pop(
                next(iter(_USER_PAGE_NUMBER_MODEL_CACHE))
            )
    return model


def _learned_folio_profile(examples: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Summarise where a folio sits in this series, from taught examples.

    Folios are printed at a fixed spot, so a handful of examples pin the
    location far more tightly than the permissive tolerance used to propose
    candidates. Horizontal positions are folded to a distance from the nearest
    edge, which collapses the recto/verso pair into one band.
    """
    positives = [item for item in examples if item.get("action") == "number"]
    if not positives:
        return None
    edge_distances: list[float] = []
    center_ys: list[float] = []
    heights: list[float] = []
    digit_counts: set[int] = set()
    for example in positives:
        center_x = float(example.get("centerXRatio") or 0.5)
        edge_distances.append(min(center_x, 1.0 - center_x))
        center_ys.append(float(example.get("centerYRatio") or 0.9))
        heights.append(max(0.002, float(example.get("heightRatio") or 0.015)))
        digits = str(example.get("digits") or "")
        if digits:
            digit_counts.add(len(digits))

    def band(values: list[float], floor: float) -> tuple[float, float]:
        low, high = min(values), max(values)
        margin = max(floor, high - low)
        return low - margin, high + margin

    return {
        "edgeDistance": band(edge_distances, 0.03),
        "centerY": band(center_ys, 0.02),
        "height": (min(heights) * 0.5, max(heights) * 2.0),
        "digitCounts": digit_counts,
    }


def _candidate_matches_learned_profile(
    box: list[int],
    image_size: tuple[int, int],
    profile: dict[str, Any] | None,
    glyph_count: int,
) -> bool:
    """Gate a confirmed candidate against the taught folio profile."""
    if not profile:
        return True
    width, height = image_size
    center_x = ((box[0] + box[2]) / 2) / max(1, width)
    center_y = ((box[1] + box[3]) / 2) / max(1, height)
    height_ratio = (box[3] - box[1]) / max(1, height)
    edge_distance = min(center_x, 1.0 - center_x)
    for value, key in (
        (edge_distance, "edgeDistance"),
        (center_y, "centerY"),
        (height_ratio, "height"),
    ):
        low, high = profile[key]
        if not (low <= value <= high):
            return False
    digit_counts = profile["digitCounts"]
    if digit_counts and glyph_count:
        if not (min(digit_counts) - 1 <= glyph_count <= max(digit_counts) + 1):
            return False
    return True


def _candidate_matches_learned_location(
    box: list[int], image_size: tuple[int, int], examples: list[dict[str, Any]]
) -> bool:
    width, height = image_size
    center_x = ((box[0] + box[2]) / 2) / max(1, width)
    center_y = ((box[1] + box[3]) / 2) / max(1, height)
    height_ratio = (box[3] - box[1]) / max(1, height)
    for example in examples:
        if example.get("action") != "number":
            continue
        ex = float(example.get("centerXRatio") or 0.5)
        ey = float(example.get("centerYRatio") or 0.9)
        eh = max(0.002, float(example.get("heightRatio") or 0.015))
        x_distance = min(abs(center_x - ex), abs(center_x - (1.0 - ex)))
        if (
            x_distance <= 0.18
            and abs(center_y - ey) <= max(0.08, eh * 6.0)
            and 0.35 <= height_ratio / eh <= 2.8
        ):
            return True
    return False


def _scale_example_box(example: dict[str, Any], target_size: tuple[int, int]) -> list[int] | None:
    source_size = example.get("sourceSize")
    box = example.get("box")
    if not (
        isinstance(source_size, list) and len(source_size) == 2
        and isinstance(box, list) and len(box) == 4
    ):
        return None
    sw, sh = max(1, int(source_size[0])), max(1, int(source_size[1]))
    tw, th = target_size
    return [
        max(0, min(tw - 1, round(int(box[0]) * tw / sw))),
        max(0, min(th - 1, round(int(box[1]) * th / sh))),
        max(1, min(tw, round(int(box[2]) * tw / sw))),
        max(1, min(th, round(int(box[3]) * th / sh))),
    ]


def _boxes_overlap_ratio(first: list[int], second: list[int]) -> float:
    left, top = max(first[0], second[0]), max(first[1], second[1])
    right, bottom = min(first[2], second[2]), min(first[3], second[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    area = max(1, (first[2] - first[0]) * (first[3] - first[1]))
    return intersection / area


# Folios are often printed wrapped in a pair of brackets, "( 67 )". Those
# glyphs are neither digits nor evidence against one, so they are classified
# apart from the letters that veto a match.
_FOLIO_BRACKET_GLYPHS = "()[]"

# The marks artwork leaves in a page margin. Without them the classifier has
# no way to answer "this is not a glyph at all": a bare diagonal is scored
# against digits and letters only, and "7" wins by default with the same
# comfortable margin over every letter that a printed "7" has.
_NON_GLYPH_SHAPES = frozenset({
    "stroke", "taper", "dashed", "wedge", "notched", "half", "arc", "lines", "cross",
})

# A printed digit at folio size (13-22 px tall) beats the closest non-glyph
# shape by at least 0.026 across every font measured, and the thinnest case is
# "1", which genuinely is a bar. Artwork fragments score from -0.16 upwards.
_NON_GLYPH_DIGIT_MARGIN = 0.02


# Letters whose printed shape is the digit's shape. Deliberately omits "7" and
# "4": they have no true twin, and they are the digits artwork strokes imitate.
_DIGIT_LETTER_TWINS: dict[str, frozenset[str]] = {
    "0": frozenset({"O", "o", "О", "о", "D", "Q"}),
    "1": frozenset({"I", "l", "i"}),
    "2": frozenset({"Z", "z", "З", "з"}),
    "3": frozenset({"З", "з", "E", "Э", "э"}),
    "5": frozenset({"S", "s", "Б"}),
    "6": frozenset({"b", "G", "Ь", "ь", "б"}),
    "8": frozenset({"B", "g", "В", "в"}),
    "9": frozenset({"g", "q", "p", "P", "Р"}),
}


def _mark_runs_off_the_sheet(image: Image.Image, box: list[int], mask: Any) -> bool:
    """Whether the mark's ink crosses the sheet boundary.

    Page-number cleanup runs before margin cropping, so a printed folio always
    keeps the original scan margin around it. Ink reaching the sheet edge is a
    cut-off piece of artwork: only part of its shape is on the page, and what
    is left of a speed line or a filled corner reads as "7" or "4".
    """
    from . import models

    width, height = image.size
    x1, y1, x2, y2 = box
    borders = []
    if x1 <= 0:
        borders.append(mask[:, 0])
    if x2 >= width:
        borders.append(mask[:, -1])
    if y1 <= 0:
        borders.append(mask[0, :])
    if y2 >= height:
        borders.append(mask[-1, :])
    return any(int(models.np.count_nonzero(border)) > 0 for border in borders)


def _folio_glyph_ink_height(glyph: Any) -> int:
    from . import models

    rows = models.np.flatnonzero(models.np.any(glyph > 0, axis=1))
    return int(rows[-1] - rows[0] + 1) if rows.size else 0


def _strip_folio_brackets(glyphs: list[Any], templates: Any, bracket_mask: Any) -> list[Any]:
    """Drop the brackets a folio is printed inside, keeping only its digits.

    The whole group is still what gets erased; only the digit reading is taken
    from the glyphs between the brackets.
    """
    from . import models

    def bracket_shaped(glyph: Any) -> bool:
        normalized = _normalize_local_ocr_glyph(glyph)
        if normalized is None:
            return False
        similarities = templates @ _local_ocr_feature(normalized)
        bracket = float(models.np.max(models.np.where(bracket_mask, similarities, -2.0)))
        other = float(models.np.max(models.np.where(~bracket_mask, similarities, -2.0)))
        return bracket >= 0.70 and bracket >= other

    if len(glyphs) < 2:
        return glyphs
    leading = bracket_shaped(glyphs[0])
    trailing = bracket_shaped(glyphs[-1])
    core = glyphs[1 if leading else 0 : len(glyphs) - (1 if trailing else 0)]
    if not core:
        return glyphs
    # Shape alone is not enough to tell "[" from "1": at folio size a thin "1"
    # scores a hair higher as a bracket, and stripping it turned "128" into
    # "28". Type sets a bracket taller than the digits it wraps, while a "1" is
    # exactly as tall as its neighbours.
    tallest = max(_folio_glyph_ink_height(glyph) for glyph in core)
    if leading and _folio_glyph_ink_height(glyphs[0]) < tallest * 1.12:
        leading = False
    if trailing and _folio_glyph_ink_height(glyphs[-1]) < tallest * 1.12:
        trailing = False
    return glyphs[1 if leading else 0 : len(glyphs) - (1 if trailing else 0)]


def _recognize_local_digit_group(
    image: Image.Image,
    box: list[int],
    user_model: dict[str, Any] | None = None,
) -> tuple[str, float]:
    """Recognize a small candidate as digits using synthetic local templates."""
    from . import models

    models._ensure_imports()
    mask = _local_ocr_mask(image, box)
    if mask is None:
        return "", 0.0
    if _mark_runs_off_the_sheet(image, box, mask):
        return "", 0.0
    glyphs = _split_local_ocr_glyphs(mask)
    if not glyphs:
        return "", 0.0
    templates, labels = _get_local_glyph_templates()
    label_array = models.np.asarray(labels)
    digit_mask = models.np.asarray([label.isdigit() for label in labels], dtype=bool)
    bracket_mask = models.np.asarray(
        [label in _FOLIO_BRACKET_GLYPHS for label in labels], dtype=bool
    )
    non_glyph_mask = models.np.asarray(
        [label in _NON_GLYPH_SHAPES for label in labels], dtype=bool
    )
    glyphs = _strip_folio_brackets(glyphs, templates, bracket_mask)
    # One to four digits, optionally wrapped in a pair of brackets. A longer
    # run of glyphs is a caption fragment, not a folio.
    if not 1 <= len(glyphs) <= 4:
        return "", 0.0
    recognized = []
    confidences = []
    learned_features = (user_model or {}).get("positiveFeatures")
    learned_labels = list((user_model or {}).get("positiveLabels") or [])
    negative_features = (user_model or {}).get("negativeFeatures")
    group_normalized = _normalize_local_ocr_glyph(mask)
    negative_similarity = 0.0
    if group_normalized is not None and negative_features is not None and len(negative_features):
        negative_similarity = float(
            models.np.max(negative_features @ _local_ocr_feature(group_normalized))
        )
    for glyph in glyphs:
        normalized = _normalize_local_ocr_glyph(glyph)
        if normalized is None:
            return "", 0.0
        feature = _local_ocr_feature(normalized)
        similarities = templates @ feature
        best_digit_index = int(models.np.argmax(models.np.where(digit_mask, similarities, -2.0)))
        best_other_index = int(models.np.argmax(models.np.where(
            ~digit_mask & ~bracket_mask & ~non_glyph_mask, similarities, -2.0)))
        best_other = float(similarities[best_other_index])
        best_digit = float(similarities[best_digit_index])
        best_non_glyph = float(
            models.np.max(models.np.where(non_glyph_mask, similarities, -2.0))
        )
        learned_digit = ""
        learned_similarity = -2.0
        if learned_features is not None and len(learned_features):
            learned_similarities = learned_features @ feature
            learned_index = int(models.np.argmax(learned_similarities))
            learned_similarity = float(learned_similarities[learned_index])
            learned_digit = learned_labels[learned_index]
            if learned_similarity > best_digit:
                best_digit = learned_similarity
                best_digit_index = -1
        # Require both an absolute digit-like shape and separation from common
        # letter shapes. Uncertain marks remain untouched in the fast preview.
        # Several digits have a twin letter, so that separation is unreachable
        # for them: "0"/"O" differ by 0.005 and "8"/"g" by 0.021 at folio size.
        # A taught example of the same digit in this series is the ground truth
        # the margin is standing in for, so strong agreement lifts it even when
        # the synthetic template scores a hair higher.
        template_digit = "" if best_digit_index < 0 else str(label_array[best_digit_index])
        learned_match = (
            (best_digit_index < 0 and learned_similarity >= 0.70)
            or (learned_similarity >= 0.85 and learned_digit == template_digit)
        )
        # Losing to a letter that is the same shape says nothing: a folio is
        # printed in a margin with no text around it, so "9" scoring below "g"
        # is not evidence against a digit. Digits without a real twin, "7" and
        # "4" above all, keep the requirement, because those are the shapes an
        # artwork stroke imitates.
        #
        # Only for a series the user has taught. There the learned profile
        # rejects anything outside the folio's position and digit count, which
        # is what this margin is standing in for. Without that backstop the
        # exemption turned 4 detections into 28 on the same volume.
        twin_letter = bool(learned_labels) and str(
            label_array[best_other_index]
        ) in _DIGIT_LETTER_TWINS.get(template_digit, frozenset())
        # A pen stroke is not a digit that happens to score badly: it is a
        # different kind of mark, and the shape bank can now say so. This holds
        # even for a taught series, where `best_digit` already carries the
        # learned similarity and a real folio clears the margin easily.
        if best_digit - best_non_glyph < _NON_GLYPH_DIGIT_MARGIN:
            return "", max(0.0, best_digit)
        if best_digit < (0.70 if learned_match else 0.76) or (
            not learned_match
            and not twin_letter
            and best_digit - best_other < 0.025
        ):
            return "", max(0.0, best_digit)
        recognized.append(learned_digit if best_digit_index < 0 else str(label_array[best_digit_index]))
        confidences.append(best_digit)
    confidence = min(confidences) if confidences else 0.0
    if negative_similarity >= 0.90 and negative_similarity >= confidence - 0.015:
        return "", max(0.0, confidence - 0.10)
    return "".join(recognized), confidence


def _spread_partner_folio(
    selected: list[tuple[dict[str, Any], dict[str, Any]]],
    confirmed: list[tuple[dict[str, Any], dict[str, Any]]],
    size: tuple[int, int],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """The best folio of a spread's other half, when it prints like the first.

    The two pages of a spread are numbered in one type at nearby baselines.
    Scan alignment can shift one page vertically by a glyph's height; a much
    larger shift or a different glyph size is not a matching folio.
    ``confirmed`` is sorted by confidence, so the first match in the other
    half is that half's best.
    """
    width, height = size
    if width <= height or not selected:
        return None
    box = selected[0][0]["box"]
    box_height = max(1, box[3] - box[1])

    def half(candidate_box: list[int]) -> bool:
        return (candidate_box[0] + candidate_box[2]) < width

    for candidate, decision in confirmed[1:]:
        other = candidate["box"]
        if half(other) == half(box):
            continue
        other_height = max(1, other[3] - other[1])
        if abs(other_height - box_height) > max(3, 0.35 * max(box_height, other_height)):
            continue
        # The Berserk 84/85 spread has equally sized 31 px folios offset by
        # 23 px. Half a glyph's height discarded one valid reading. Use the
        # shorter height so the tolerance is independent of confidence order
        # without letting a taller candidate inflate it.
        if abs(other[3] - box[3]) > max(3, min(box_height, other_height)):
            continue
        return candidate, decision
    return None


def detect_page_numbers_locally(
    image: Image.Image,
    bottom_ratio: float = 0.20,
    scope_path: str = "",
    *,
    minimum_page_number: int = 1,
) -> dict[str, Any]:
    """Fast conservative page-number decision using local user feedback."""
    minimum = page_number_minimum(minimum_page_number)
    safe_ratio = max(0.05, min(0.50, float(bottom_ratio)))
    width, height = image.size
    y_offset = max(0, min(height - 1, int(round(height * (1.0 - safe_ratio)))))
    user_model = _get_user_page_number_model(scope_path)
    examples = list(user_model.get("examples") or [])
    digest = page_digest(image) if examples else ""
    exact_positive = [
        item for item in examples
        if item.get("action") == "number" and item.get("pageDigest") == digest
    ]
    exact_negative = [
        item for item in examples
        if item.get("action") == "not_number" and item.get("pageDigest") == digest
    ]
    candidates = _find_page_number_candidates(image, y_offset)
    if any(item.get("action") == "number" for item in examples):
        learned_top_ratio = min(
            [0.80] + [
                max(0.55, float(item.get("centerYRatio") or 0.8) - 0.08)
                for item in examples if item.get("action") == "number"
            ]
        )
        learned_offset = max(0, min(height - 1, round(height * learned_top_ratio)))
        learned_candidates = (
            candidates
            if learned_offset >= y_offset
            else _find_page_number_candidates(
                image, learned_offset, max_candidates=64, allow_internal_gutters=True
            )
        )
        known_boxes = {tuple(item["box"]) for item in candidates}
        for item in learned_candidates:
            if (
                tuple(item["box"]) not in known_boxes
                and _candidate_matches_learned_location(item["box"], image.size, examples)
            ):
                learned_item = dict(item)
                learned_item["id"] = f"L{len(candidates) + 1:02d}"
                candidates.append(learned_item)
                known_boxes.add(tuple(item["box"]))
    exact_ids: dict[str, dict[str, Any]] = {}
    for example in exact_positive:
        scaled = _scale_example_box(example, image.size)
        if scaled is None:
            continue
        candidate_id = f"U{len(exact_ids) + 1:02d}"
        exact_ids[candidate_id] = example
        candidates.insert(0, {"id": candidate_id, "box": scaled})
    negative_boxes = [
        box for item in exact_negative
        if (box := _scale_example_box(item, image.size)) is not None
    ]
    # Taught examples pin the folio to one spot and one digit count. Without
    # that gate a single artwork stroke read as "7" anywhere in the bottom
    # fifth of the page was enough to erase a piece of the drawing.
    learned_profile = _learned_folio_profile(examples)
    exact_boxes = [candidate["box"] for candidate in candidates if candidate["id"] in exact_ids]
    decisions = []
    confirmed = []
    for candidate in candidates:
        exact = exact_ids.get(candidate["id"])
        recognized, confidence = (
            (str(exact.get("digits") or ""), 1.0)
            if exact is not None
            else _recognize_local_digit_group(image, candidate["box"], user_model)
        )
        vetoed = any(
            _boxes_overlap_ratio(candidate["box"], box) >= 0.35
            for box in negative_boxes
        )
        # An automatic candidate sitting on a box the user already taught is
        # the same folio found twice, not a second one.
        duplicate = exact is None and any(
            _boxes_overlap_ratio(candidate["box"], box) >= 0.50
            for box in exact_boxes
        )
        off_profile = exact is None and not _candidate_matches_learned_profile(
            candidate["box"], image.size, learned_profile, len(recognized)
        )
        below_minimum = bool(recognized and recognized.isascii() and recognized.isdecimal()
                             and int(recognized) < minimum)
        is_number = (
            not below_minimum
            and bool(recognized)
            and confidence >= (0.70 if examples else 0.76)
            and not vetoed
            and not duplicate
            and not off_profile
        )
        decision = {
            "candidate_id": candidate["id"],
            "classification": "page_number" if is_number else "uncertain",
            "recognized_text": recognized,
            "confidence": confidence,
            "validDigits": is_number,
            "belowChapterMinimum": below_minimum,
            "learned": bool(exact is not None or examples),
            "vetoedByUser": vetoed,
            "duplicateOfTaughtBox": duplicate,
            "offLearnedProfile": off_profile,
        }
        decisions.append(decision)
        if is_number:
            confirmed.append((candidate, decision))
    confirmed.sort(key=lambda item: item[1]["confidence"], reverse=True)
    # One folio per page: a second read on a portrait page is a stroke of
    # the drawing. A scanned spread is two pages, so its facing half may
    # keep its own number.
    selected = confirmed[:1]
    partner = _spread_partner_folio(selected, confirmed, image.size)
    if partner is not None:
        selected.append(partner)
    manual_exact_boxes = [
        list(item[0]["box"])
        for item in selected
        if item[0].get("id") in exact_ids
    ]
    return {
        "has_page_number": bool(selected),
        "minimumPageNumber": minimum,
        "confidence": selected[0][1]["confidence"] if selected else 0.0,
        "boxes": [list(item[0]["box"]) for item in selected],
        "reason": (
            "Fast local digit classifier with user feedback."
            if examples else
            "Fast local digit classifier."
        ),
        "model": "opencv-local-digits+user-memory" if examples else "opencv-local-digits",
        "scan_top": y_offset,
        "candidateCount": len(candidates),
        "selectedIds": [item[0]["id"] for item in selected],
        "recognizedDigits": {item[0]["id"]: item[1]["recognized_text"] for item in selected},
        "manualExactBoxes": manual_exact_boxes,
        "decisions": decisions,
        "hasAmbiguousCandidates": bool(candidates) and not bool(selected),
        "memoryRevision": str(user_model.get("revision") or 0),
        "memoryPositiveCount": sum(1 for item in examples if item.get("action") == "number"),
        "memoryNegativeCount": sum(1 for item in examples if item.get("action") == "not_number"),
    }


def _safe_candidate(
    name: str,
    box: tuple[float, float, float, float],
    width: int,
    height: int,
    ambiguous: bool = False,
) -> CropCandidate | None:
    left = max(0, min(width - 1, int(round(box[0]))))
    top = max(0, min(height - 1, int(round(box[1]))))
    right = max(left, min(width - 1, int(round(box[2]))))
    bottom = max(top, min(height - 1, int(round(box[3]))))
    kept_w, kept_h = right - left + 1, bottom - top + 1
    if kept_w < width * 0.42 or kept_h < height * 0.42 or kept_w * kept_h < width * height * 0.30:
        return None
    return CropCandidate(name, left, top, right, bottom, ambiguous)


def _uniform_outer_background(image: Image.Image) -> tuple[int, int, int] | None:
    """Return a shared RGB edge color only when every page side is uniform."""
    from . import models

    models._ensure_imports()
    rgb = models.np.array(image.convert("RGB"))
    if rgb.shape[0] < 2 or rgb.shape[1] < 2:
        return None
    perimeter = models.np.concatenate((rgb[0], rgb[-1], rgb[1:-1, 0], rgb[1:-1, -1]), axis=0)
    median = models.np.median(perimeter, axis=0)
    for side in (rgb[0], rgb[:, -1], rgb[-1], rgb[:, 0]):
        distance = models.np.max(models.np.abs(side.astype(models.np.float32) - median), axis=1)
        if float(models.np.mean(distance <= 18.0)) < 0.80:
            return None
    return tuple(int(round(float(value))) for value in median)


def _sheet_edge_line_bands(foreground) -> dict[str, int]:
    """Find the dark line a scan leaves along each edge of the sheet.

    It runs the full height or width of the page, so every strength test reads
    it as an intentional rule and the paper behind it can never be trimmed --
    and the ink it holds is enough to make the crop look unsafe as well. What
    separates it from a printed rule is what lies behind it: the page's own art
    for a rule, a finger of blank margin for the scan.  That margin need only
    be mostly blank: a panel that bleeds off the same edge reaches the line
    over part of its length (Rent-a-Girlfriend v1 ch2 p29), and the scan is
    no less a scan for it.

    Returns the width of the line band found at each side, in lines.
    """
    from . import models

    height, width = foreground.shape
    bands: dict[str, int] = {}
    for axis, sides in ((1, ("top", "bottom")), (0, ("left", "right"))):
        counts = models.np.sum(foreground, axis=axis)
        cross = foreground.shape[axis]
        solid = counts >= max(1, round(cross * 0.50))
        mostly_blank = counts <= max(3, round(cross * 0.25))
        gap_needed = max(8, round(len(counts) * 0.01))
        for near_edge, side in zip((False, True), sides):
            line = solid[::-1] if near_edge else solid
            empty = mostly_blank[::-1] if near_edge else mostly_blank
            band = 0
            while band < len(line) and line[band]:
                band += 1
            if not 0 < band <= 4:
                continue
            gap = 0
            while band + gap < len(empty) and empty[band + gap]:
                gap += 1
            if gap < gap_needed:
                continue
            bands[side] = band
    return bands


def _clear_sheet_edge_lines(foreground):
    """Erase the scan's sheet-edge lines from a foreground mask."""
    height, width = foreground.shape
    for side, band in _sheet_edge_line_bands(foreground).items():
        if side == "top":
            foreground[0:band, :] = False
        elif side == "bottom":
            foreground[height - band:height, :] = False
        elif side == "left":
            foreground[:, 0:band] = False
        else:
            foreground[:, width - band:width] = False
    return foreground


def _clear_sheet_edge_smears(foreground):
    """Erase the short marks a scan leaves on the sheet edge from a foreground mask.

    A smear a few columns wide and a few dozen rows tall, sitting on the
    physical edge, is too wide for the outermost-columns rule of the blank-edge
    search and far too short to be a sheet-edge line, so it read as content
    and held the whole margin behind it (Berserk v1 ch2 p137 and p145).  A
    stroke hanging a few dozen rows down from the top edge near a corner did
    the same to the side it was nearest (Berserk v1 ch1 p003).  What tells
    such a mark from a panel bleeding off the same edge is, again, blank
    paper: the mark reaches the edge of the sheet, goes no deeper than a
    few dozen lines, and has nothing but paper around it on the page's side.
    """
    from . import models

    models._ensure_imports()
    height, width = foreground.shape
    count, labels, stats, _ = models.cv2.connectedComponentsWithStats(
        foreground.astype(models.np.uint8),
        connectivity=8,
    )
    if count <= 1:
        return foreground
    left = stats[1:, models.cv2.CC_STAT_LEFT]
    top = stats[1:, models.cv2.CC_STAT_TOP]
    right = left + stats[1:, models.cv2.CC_STAT_WIDTH] - 1
    bottom = top + stats[1:, models.cv2.CC_STAT_HEIGHT] - 1
    smears = models.np.zeros(count - 1, dtype=bool)
    for sideways, axis_length, cross_length, near, far, along_start, along_end in (
        (True, width, height, left, right, top, bottom),
        (False, height, width, top, bottom, left, right),
    ):
        edge = max(4, round(axis_length * 0.004))
        reach = max(edge, round(axis_length * 0.02))
        gap = max(8, round(axis_length * 0.01))
        short = (along_end - along_start + 1) < cross_length * 0.50
        for on_far_side in (False, True):
            if on_far_side:
                touching = (near >= axis_length - reach) & (far >= axis_length - edge)
            else:
                touching = (far < reach) & (near < edge)
            # A faint scan streak can sit just inside the sheet rather than
            # touch it (Berserk v4 ch0-11 p89). Its thresholded fragments
            # share a very thin band with a long horizontal/vertical extent.
            # Keep the blank-paper check below: nearby artwork must still
            # prevent this band from being discarded.
            inset = max(edge, round(axis_length * 0.01))
            thin = (far - near + 1) <= max(3, round(axis_length * 0.0015))
            peripheral = near >= axis_length - inset if on_far_side else far < inset
            fragments = models.np.flatnonzero(thin & peripheral & short)
            if fragments.size:
                band_depth = int(models.np.max(far[fragments]) - models.np.min(near[fragments]) + 1)
                span = int(models.np.max(along_end[fragments]) - models.np.min(along_start[fragments]) + 1)
                longest = int(models.np.max(along_end[fragments] - along_start[fragments] + 1))
                if band_depth <= max(3, round(axis_length * 0.0015)) and span >= cross_length * 0.15 and longest >= cross_length * 0.03:
                    touching[fragments] = True
            candidates = models.np.flatnonzero(touching & short & ~smears)
            if candidates.size == 0:
                continue
            # A mark broken into pieces by the threshold must not shelter
            # itself: only ink that is no such mark counts as company.
            company = foreground & ~models.np.isin(labels, candidates + 1)
            for index in candidates:
                along = slice(max(0, int(along_start[index]) - gap), int(along_end[index]) + gap + 1)
                if on_far_side:
                    inward = slice(max(0, int(near[index]) - gap), axis_length)
                else:
                    inward = slice(0, int(far[index]) + 1 + gap)
                window = (along, inward) if sideways else (inward, along)
                if not models.np.any(company[window]):
                    smears[index] = True
    if models.np.any(smears):
        foreground = foreground & ~models.np.isin(labels, models.np.flatnonzero(smears) + 1)
    return foreground


def _erase_sheet_edge_lines(image: Image.Image) -> tuple[Image.Image, bool]:
    """Paint the scan's sheet-edge lines out of the page itself.

    Clearing them from the crop's mask stops them holding a margin, but a
    line beside a panel that genuinely reaches the edge still lands inside
    the crop's retained margin and survives into the output.  It is an
    artefact of the scan, not of the page, so each line -- with the halo it
    leaves on the lines just inside it -- is replaced by the line beyond:
    paper where the page is paper, and the panel's own bleed where the panel
    reaches the edge.
    """
    from . import models

    models._ensure_imports()
    foreground, _background = _raw_crop_foreground(image)
    bands = _sheet_edge_line_bands(foreground)
    if not bands:
        return image, False
    rgb = models.np.array(image.convert("RGB"))
    gray = models.np.array(image.convert("L"), dtype=models.np.float32)
    height, width = rgb.shape[:2]

    def with_halo(lines, band):
        # The line's own antialiasing and JPEG ringing sit just inside it, a
        # shade or two darker than the paper beyond: take those along, up to
        # two lines, while each is still darker than the next one in.
        means = [float(models.np.mean(line)) for line in lines]
        while band < min(len(means) - 1, 6) and means[band] < means[band + 1] - 8.0:
            band += 1
        return band

    for side, band in bands.items():
        if side == "top":
            band = with_halo(gray, band)
            if band < height:
                rgb[0:band, :] = rgb[band:band + 1, :]
        elif side == "bottom":
            band = with_halo(gray[::-1], band)
            if band < height:
                rgb[height - band:height, :] = rgb[height - band - 1:height - band, :]
        elif side == "left":
            band = with_halo(gray.T, band)
            if band < width:
                rgb[:, 0:band] = rgb[:, band:band + 1]
        else:
            band = with_halo(gray.T[::-1], band)
            if band < width:
                rgb[:, width - band:width] = rgb[:, width - band - 1:width - band]
    painted = Image.fromarray(rgb, "RGB")
    return painted if image.mode == "RGB" else painted.convert(image.mode), True


def _crop_foreground_mask(image: Image.Image, ignore_mask=None):
    """Classify content against a uniform RGB border, with black/white fallback."""
    from . import models

    models._ensure_imports()

    def finish(foreground, background):
        foreground = _clear_sheet_edge_smears(_clear_sheet_edge_lines(foreground))
        if ignore_mask is not None:
            ignored = models.np.asarray(ignore_mask, dtype=models.np.uint8)
            if ignored.shape[:2] != foreground.shape[:2]:
                ignored = models.cv2.resize(
                    ignored,
                    (foreground.shape[1], foreground.shape[0]),
                    interpolation=models.cv2.INTER_NEAREST,
                )
            foreground = foreground.copy()
            foreground[ignored > 0] = False
        return foreground, background

    return finish(*_raw_crop_foreground(image))


def _raw_crop_foreground(image: Image.Image):
    """The crop's content mask before any scan lines are cleared from it."""
    from . import models

    models._ensure_imports()
    rgb = models.np.array(image.convert("RGB"))
    background = _uniform_outer_background(image)
    if background is not None:
        distance = models.np.max(
            models.np.abs(rgb.astype(models.np.int16) - models.np.array(background, dtype=models.np.int16)),
            axis=2,
        )
        return distance > 18, background
    gray = models.np.array(image.convert("L"))
    fill = _detect_fill_color(image, "none")
    return (gray < 235 if fill == "white" else gray > 20), None


def _vertical_gradient_side_depths(image: Image.Image) -> dict[str, int]:
    """Return left/right field widths whose colour changes down the page.

    Top and bottom paper remains easy for the ordinary blank-edge detector: it
    is locally black, white, or near either one.  The troublesome field is a
    side strip cut from that same background.  One column contains the whole
    black-to-white vertical gradient, so it has no single colour to compare
    with the rest of the perimeter even though the neighbouring field columns
    are nearly identical to it.

    A side becomes crop capacity only when its vertical profile is smooth and
    strongly monotonic, adjacent columns repeat that profile, and several
    substantially different columns begin immediately after it.  A gradient
    continuing through the artwork therefore does not look like a margin.
    """
    from . import models

    models._ensure_imports()
    source_width, source_height = image.size
    analysis = image.convert("L")
    if max(source_width, source_height) > 960:
        scale = 960.0 / max(source_width, source_height)
        analysis = analysis.resize(
            (
                max(16, int(round(source_width * scale))),
                max(24, int(round(source_height * scale))),
            ),
            getattr(Image.Resampling, "BILINEAR", Image.BILINEAR),
        )
    gray = models.np.asarray(analysis, dtype=models.np.float32)

    def scan(columns) -> int:
        width, height = columns.shape
        minimum_depth = max(8, round(width * 0.01))
        if width < minimum_depth * 2 or height < 24:
            return 0

        vertical_inset = max(1, round(height * 0.04))
        sample = columns[:, vertical_inset : height - vertical_inset]
        seed_width = max(2, min(8, round(width * 0.006)))
        profile = models.np.median(sample[:seed_width], axis=0)

        # Confirm the edge itself is the stated kind of field: a smooth
        # top-to-bottom (or bottom-to-top) transition with a useful tonal span.
        smooth_window = max(3, min(31, (round(height * 0.008) | 1)))
        kernel = models.np.ones(smooth_window, dtype=models.np.float32) / smooth_window
        smooth = models.np.convolve(profile, kernel, mode="valid")
        if smooth.size < 4:
            return 0
        delta = float(smooth[-1] - smooth[0])
        if abs(delta) < 80.0:
            return 0
        # A blurred boundary between two full-bleed frames can spread across
        # enough samples to pass the movement-support check below. It is still
        # a step, not a gradient field: one adjacent profile change carries a
        # large part of the total tonal span. Kemono Jihen 01/02 page 3 exposes
        # this only after its ordinary white side margins have been removed.
        raw_steps = models.np.abs(models.np.diff(profile))
        distinct_level_ratio = len(models.np.unique(models.np.round(profile))) / max(1, profile.size)
        if (
            raw_steps.size
            and float(models.np.max(raw_steps)) > max(48.0, abs(delta) * 0.40)
            and distinct_level_ratio < 0.05
        ):
            return 0
        direction = 1.0 if delta > 0 else -1.0
        movement = direction * models.np.diff(smooth)
        positive_movement = models.np.maximum(movement, 0.0)
        forward = float(models.np.sum(positive_movement))
        backward = float(models.np.sum(models.np.maximum(-movement, 0.0)))
        if forward < 80.0 or backward > max(16.0, forward * 0.15):
            return 0

        # A black frame beside a white physical page margin produces one
        # enormous step in the edge profile. Smoothing makes that step look
        # monotonic, which used to classify the full-bleed top panels on Tower
        # Dungeon 03/10 pages 6 and 7 as sideways gradients. A real gradient
        # distributes its movement over a useful part of the profile; a colour
        # boundary only moves across the smoothing kernel's handful of samples.
        movement_floor = max(0.05, (forward / max(1, movement.size)) * 0.10)
        movement_support = int(models.np.sum(positive_movement > movement_floor))
        if movement_support < max(6, round(movement.size * 0.03)):
            return 0

        difference = models.np.abs(sample - profile[None, :])
        similar = (
            (models.np.median(difference, axis=1) <= 10.0)
            & (models.np.percentile(difference, 90, axis=1) <= 24.0)
        )

        # Three consecutive columns that no longer repeat the edge profile are
        # the beginning of the printed page. A scratch in one column cannot
        # end the margin by itself.
        changed = (~similar).astype(models.np.uint8)
        runs = models.np.convolve(changed, models.np.ones(3, dtype=models.np.uint8), mode="valid")
        starts = models.np.flatnonzero(runs >= 3)
        if starts.size == 0:
            return 0
        depth = int(starts[0])
        if depth < minimum_depth or depth > round(width * 0.25):
            return 0

        # A small piece of artwork can occupy less than the percentile-based
        # allowance above (Gachiakuta 07/57 p19's sleeve). Check contiguous
        # rows across the entire candidate strip, including the end caps.
        full_profile = models.np.median(columns[:seed_width], axis=0)
        row_difference = models.np.median(
            models.np.abs(columns[:depth] - full_profile[None, :]), axis=0,
        )
        intrusion = (row_difference > 80.0).astype(models.np.uint8)
        intrusion_run = max(3, round(height * 0.004))
        if models.np.any(models.np.convolve(
            intrusion, models.np.ones(intrusion_run, dtype=models.np.uint8), mode="valid",
        ) >= intrusion_run):
            return 0

        context_end = min(width, depth + max(6, round(width * 0.04)))
        if float(models.np.mean(~similar[depth:context_end])) < 0.50:
            return 0
        return depth

    horizontal_scale = source_width / float(analysis.width)
    return {
        # Round toward the edge: an interpolated analysis boundary must never
        # promise a source column that may already belong to the drawing.
        "left": max(0, int(math.floor(scan(gray.T) * horizontal_scale))),
        "right": max(0, int(math.floor(scan(gray.T[::-1]) * horizontal_scale))),
    }


def _horizontal_gradient_edge_depths(image: Image.Image) -> dict[str, int]:
    """Return top/bottom gradient-field depths up to the first page mark.

    A horizontal field may change colour as it moves into the page while each
    individual row remains almost uniform.  Its boundary is the first stable
    run of rows containing pixels that depart materially from that row's
    background level.  This keeps sparse lettering protruding above a panel:
    the lettering, rather than the panel rectangle, is the start of content.
    """
    from . import models

    models._ensure_imports()
    source_width, source_height = image.size
    analysis = image.convert("L")
    if max(source_width, source_height) > 960:
        scale = 960.0 / max(source_width, source_height)
        analysis = analysis.resize(
            (
                max(16, int(round(source_width * scale))),
                max(24, int(round(source_height * scale))),
            ),
            getattr(Image.Resampling, "BILINEAR", Image.BILINEAR),
        )
    gray = models.np.asarray(analysis, dtype=models.np.float32)

    def scan(rows, *, bottom: bool = False) -> int:
        height, width = rows.shape
        minimum_depth = max(4, round(height * 0.005))
        if height < minimum_depth * 2 or width < 24:
            return 0

        horizontal_inset = max(1, round(width * 0.04))
        sample = rows[:, horizontal_inset : width - horizontal_inset]
        levels = models.np.median(sample, axis=1)
        difference = models.np.abs(sample - levels[:, None])
        changed = models.np.sum(difference > 18.0, axis=1) >= max(
            2,
            round(sample.shape[1] * 0.002),
        )

        # Require a stable entrance into content. A single dusty row or a
        # compression blemish inside the field cannot set the crop boundary.
        runs = models.np.convolve(
            changed.astype(models.np.uint8),
            models.np.ones(3, dtype=models.np.uint8),
            mode="valid",
        )
        starts = models.np.flatnonzero(runs >= 3)
        if starts.size == 0:
            return 0
        depth = int(starts[0])
        if depth < minimum_depth or depth > round(height * 0.25):
            return 0

        # This path is specifically for a gradient. Flat black/white paper is
        # handled by the ordinary blank-edge detector.
        field_levels = levels[:depth]
        smooth_window = max(3, min(15, (round(depth * 0.08) | 1)))
        if field_levels.size < smooth_window + 1:
            return 0
        # A halftone/patterned frame can touch the physical edge and then be
        # followed by a black gutter.  Downsampling its alternating rows may
        # leave a broad overall tonal drift, but it is still artwork rather
        # than a smooth field.  Page 25 of Usuzumi-no-Hate 02/10 exposed this:
        # the striped cap survived the ordinary edge pass at y=0, then a second
        # pass mistook it for a gradient and removed the whole frame.  Real
        # gradients move a little on most adjacent rows; repeated large jumps
        # are texture and must anchor the edge.
        level_steps = models.np.abs(models.np.diff(field_levels))
        # A thin panel outline followed by smooth, dark artwork can resemble
        # a gradient once the white side margins are removed. Dandadan 01/01
        # page 2 exposes this at the asphalt along the bottom edge. A single
        # abrupt step carrying much of the tonal span anchors the panel; it
        # must not be blurred into removable gradient capacity.
        tonal_span = float(models.np.ptp(field_levels))
        if float(models.np.max(level_steps)) > max(12.0, tonal_span * 0.40):
            return 0
        if (
            float(models.np.median(level_steps)) > 8.0
            and float(models.np.mean(level_steps > 12.0)) > 0.30
        ):
            return 0
        kernel = models.np.ones(smooth_window, dtype=models.np.float32) / smooth_window
        smooth = models.np.convolve(field_levels, kernel, mode="valid")
        delta = float(smooth[-1] - smooth[0])
        if abs(delta) < 12.0:
            return 0
        direction = 1.0 if delta > 0 else -1.0
        movement = direction * models.np.diff(smooth)
        forward = float(models.np.sum(models.np.maximum(movement, 0.0)))
        backward = float(models.np.sum(models.np.maximum(-movement, 0.0)))
        if forward < 12.0 or backward > max(8.0, forward * 0.25):
            return 0

        context_end = min(height, depth + max(6, round(height * 0.04)))
        if float(models.np.mean(changed[depth:context_end])) < 0.50:
            return 0

        # Downsampling can erase printed dots and turn a screentone into an
        # apparently smooth gradient (Berserk 16/117 image129). Confirm the
        # proposed field at source resolution before discarding any artwork.
        source_depth = max(1, int(math.floor(depth * source_height / height)))
        source_inset = max(1, round(source_width * 0.04))
        source_top = source_height - source_depth if bottom else 0
        field = models.np.asarray(
            image.crop((source_inset, source_top, source_width - source_inset,
                        source_top + source_depth)).convert("L"),
            dtype=models.np.int16,
        )
        texture_steps = models.np.abs(models.np.diff(field, axis=1))
        if (
            float(models.np.median(texture_steps)) > 8.0
            and float(models.np.mean(texture_steps > 18.0)) > 0.30
        ):
            return 0
        return depth

    vertical_scale = source_height / float(analysis.height)
    axial = {
        "top": max(0, int(math.floor(scan(gray) * vertical_scale))),
        "bottom": max(0, int(math.floor(scan(gray[::-1], bottom=True) * vertical_scale))),
    }

    # A top/bottom field may instead carry its gradient across the page. After
    # a 90-degree turn it is exactly the side-field case handled above. Both
    # left-to-right and right-to-left profiles are accepted by that detector.
    transverse_sides = _vertical_gradient_side_depths(image.transpose(Image.Transpose.ROTATE_90))
    transverse = {
        "top": int(transverse_sides.get("left", 0)),
        "bottom": int(transverse_sides.get("right", 0)),
    }

    # When both physical side fields carry a top-to-bottom gradient, neither
    # edge row is necessarily uniform and a single black/white fill cannot
    # describe the page. Reconstruct the background level for every row from
    # those verified side fields, then locate the first/last meaningful mark
    # against that surface. This crops top/bottom only; side fields remain
    # reserved for target-aspect correction.
    surface = {"top": 0, "bottom": 0}
    side_depths = _vertical_gradient_side_depths(analysis)
    left_depth = int(side_depths.get("left", 0))
    right_depth = int(side_depths.get("right", 0))
    if left_depth > 0 or right_depth > 0:
        left_levels = (
            models.np.median(gray[:, :left_depth], axis=1)
            if left_depth > 0
            else None
        )
        right_levels = (
            models.np.median(gray[:, gray.shape[1] - right_depth :], axis=1)
            if right_depth > 0
            else None
        )
        if left_levels is None:
            left_levels = right_levels
        if right_levels is None:
            right_levels = left_levels
        horizontal_position = models.np.linspace(
            0.0,
            1.0,
            gray.shape[1],
            dtype=models.np.float32,
        )
        background_surface = (
            left_levels[:, None] * (1.0 - horizontal_position[None, :])
            + right_levels[:, None] * horizontal_position[None, :]
        )
        surface_foreground = _clear_sheet_edge_lines(
            models.np.abs(gray - background_surface) > 18.0
        )
        row_ink = models.np.sum(surface_foreground, axis=1)
        minimum_ink = max(3, round(gray.shape[1] * 0.004))
        active = row_ink >= minimum_ink
        neighbours = models.np.convolve(
            active.astype(models.np.uint8),
            models.np.ones(3, dtype=models.np.uint8),
            mode="same",
        )
        meaningful = active & ((neighbours >= 3) | (row_ink >= minimum_ink * 4))
        content_rows = models.np.flatnonzero(meaningful)
        if content_rows.size:
            minimum_depth = max(4, round(gray.shape[0] * 0.005))
            top_depth = int(content_rows[0])
            bottom_depth = int(gray.shape[0] - 1 - content_rows[-1])
            if minimum_depth <= top_depth <= round(gray.shape[0] * 0.25):
                surface["top"] = max(0, int(math.floor(top_depth * vertical_scale)))
            if minimum_depth <= bottom_depth <= round(gray.shape[0] * 0.25):
                surface["bottom"] = max(0, int(math.floor(bottom_depth * vertical_scale)))

    def earliest_supported_boundary(side: str) -> int:
        candidates = [
            depth
            for depth in (axial[side], transverse[side], surface[side])
            if depth > 0
        ]
        return min(candidates) if candidates else 0

    return {
        "top": earliest_supported_boundary("top"),
        "bottom": earliest_supported_boundary("bottom"),
    }


def _gradient_aspect_crop_box(
    image: Image.Image,
    target_size: tuple[int, int] | None,
    preserved_margin: int,
    locked: set[str],
    base_box: tuple[int, int, int, int] | None = None,
) -> tuple[int, int, int, int] | None:
    """Crop horizontal gradient fields, then move toward target aspect.

    The returned box is inclusive. Top/bottom fields are reduced to the first
    content while retaining the configured source margin. Left/right gradient
    capacity is then calculated against that shorter height. No edge ever
    consumes the retained margin, and insufficient safe side capacity leaves
    the page short of the target aspect instead of touching artwork.
    """
    width, height = image.size
    full_box = (0, 0, width - 1, height - 1)
    left, top, right, bottom = base_box or full_box

    horizontal_depths = _horizontal_gradient_edge_depths(image)
    if "top" not in locked:
        top = max(top, max(0, int(horizontal_depths.get("top", 0)) - preserved_margin))
    if "bottom" not in locked:
        bottom = min(
            bottom,
            height - 1 - max(0, int(horizontal_depths.get("bottom", 0)) - preserved_margin),
        )

    valid_target = False
    target_width = target_height = 0
    if target_size:
        try:
            target_width, target_height = (int(target_size[0]), int(target_size[1]))
        except (TypeError, ValueError, IndexError):
            pass
        else:
            valid_target = target_width > 0 and target_height > 0

    def balanced_cut(required: int, first: int, second: int) -> tuple[int, int]:
        wanted = min(max(0, required), first + second)
        if wanted <= 0:
            return 0, 0
        take_first = min(first, (wanted + 1) // 2)
        take_second = min(second, wanted - take_first)
        remainder = wanted - take_first - take_second
        if remainder:
            extra = min(first - take_first, remainder)
            take_first += extra
            remainder -= extra
        if remainder:
            take_second += min(second - take_second, remainder)
        return take_first, take_second

    projected_width = right - left + 1
    projected_height = bottom - top + 1
    if valid_target and projected_width * target_height > projected_height * target_width:
        side_depths = _vertical_gradient_side_depths(image)
        capacities = {
            "left": 0
            if "left" in locked or left > 0
            else max(0, int(side_depths.get("left", 0)) - preserved_margin),
            "right": 0
            if "right" in locked or right < width - 1
            else max(0, int(side_depths.get("right", 0)) - preserved_margin),
        }
        desired_width = max(1, int(round(projected_height * target_width / target_height)))
        cut_left, cut_right = balanced_cut(
            projected_width - desired_width,
            capacities["left"],
            capacities["right"],
        )
        left += cut_left
        right -= cut_right

    if (left, top, right, bottom) == full_box:
        return None
    return left, top, right, bottom


def _terminal_caption_panel_edges(image: Image.Image) -> set[str]:
    """Keep the breathing room of a centered caption in a terminal panel.

    A bounded block with sparse centered text is composition rather than a
    margin. It ends either at contrasting paper or at the step in tone where
    the page itself begins. Normalize
    light panels to dark so black-on-white and white-on-black obey the same
    geometry. Blank strips, small page numbers and a whole uniform background
    do not qualify. Both physical ends are checked in the same orientation.
    """
    from . import models

    models._ensure_imports()
    np = models.np
    gray = np.asarray(image.convert("L"))
    height, width = gray.shape
    band = max(2, round(width * 0.04))
    protected = set()
    for side, rows in (("bottom", gray), ("top", gray[::-1])):
        terminal = np.concatenate((rows[-1, :band], rows[-1, -band:]))
        if float(np.mean(terminal >= 223)) >= 0.98:
            rows = 255 - rows
        dark_sides = ((np.mean(rows[:, :band] <= 32, axis=1) >= 0.98)
                      & (np.mean(rows[:, -band:] <= 32, axis=1) >= 0.98))
        non_dark = np.flatnonzero(~dark_sides)
        if not non_dark.size or not dark_sides[-1]:
            continue
        start = int(non_dark[-1]) + 1
        panel_height = height - start
        if not max(24, height * 0.12) <= panel_height <= height * 0.45:
            continue
        reach = max(3, round(height * 0.004))
        before = rows[max(0, start - reach):start]
        # Paper between the panel and the page is the clearest boundary, but a
        # band can equally end where the page simply begins: its own edge stays
        # filled while what lies beyond it does not. Gachiakuta v5 ch32 p2 runs
        # its lettering band straight into the panel below, and without this
        # the crop eats the breathing room above the lettering -- 69 of the 78
        # rows that balance the 82 below it.
        if not (
            np.any(np.mean(before >= 232, axis=1) >= 0.95)
            or (
                float(np.mean(rows[start:start + reach] <= 32)) >= 0.95
                and float(np.mean(before <= 64)) <= 0.50
            )
        ):
            continue
        panel = rows[start:]
        light = panel >= 192
        # A caption may be lettering or a solid box (Gachiakuta v5 ch40 p12),
        # so the share the caption covers only has to leave the panel mostly
        # its own fill. Its shape is bounded below in any case.
        if not 0.002 <= float(np.mean(light)) <= 0.35:
            continue
        # Ignore isolated compression flecks when measuring the caption.
        ys = np.flatnonzero(np.sum(light, axis=1) >= max(3, round(width * 0.005)))
        xs = np.flatnonzero(np.sum(light, axis=0) >= max(3, round(panel_height * 0.01)))
        if not ys.size or not xs.size:
            continue
        text_height = int(ys[-1] - ys[0] + 1)
        text_width = int(xs[-1] - xs[0] + 1)
        # No upper bound on the caption's height: the breathing room required
        # at both ends already leaves it at most seven tenths of the panel,
        # and a second, tighter answer to the same question only rejects
        # composed bands (Gachiakuta v6 ch47 p9, a blob filling two thirds of
        # a band that keeps 108 rows of paper above it against 103 below).
        if (
            0.08 * width <= text_width <= 0.70 * width
            and text_height >= 0.08 * panel_height
            and abs((xs[0] + xs[-1] + 1) / 2 - width / 2) <= width * 0.12
            and abs((ys[0] + ys[-1] + 1) / 2 - panel_height / 2) <= panel_height * 0.15
            and ys[0] >= panel_height * 0.15
            and panel_height - 1 - ys[-1] >= panel_height * 0.15
        ):
            protected.add(side)
    return protected


def _find_blank_edge_candidate(
    image: Image.Image,
    include_ambiguous: bool = False,
    ignore_mask=None,
) -> CropCandidate | None:
    """Find independently removable, nearly uniform borders on each side."""
    from . import models

    models._ensure_imports()
    width, height = image.size
    if width < 8 or height < 8:
        return None
    foreground, background = _crop_foreground_mask(image, ignore_mask)
    if background is not None:
        background_luma = (77 * background[0] + 150 * background[1] + 29 * background[2]) >> 8
        if background_luma < 128 and float(models.np.mean(foreground)) < 0.12:
            return None
    # Requiring more than a single pixel prevents scanner dust from anchoring
    # an otherwise empty side while retaining real lines, text, and artwork.
    min_column_ink = max(3, round(height * 0.004))
    min_row_ink = max(3, round(width * 0.004))
    column_ink = models.np.sum(foreground, axis=0)
    row_ink = models.np.sum(foreground, axis=1)

    def meaningful_indices(ink_counts, minimum: int, cross_size: int):
        active = ink_counts >= minimum
        # Weak isolated edge columns/rows are usually scanner dust. Preserve
        # contiguous marks and genuinely long one-pixel rules.
        neighbours = models.np.convolve(active.astype(models.np.uint8), models.np.ones(3, dtype=models.np.uint8), mode="same")
        strong = ink_counts >= minimum * 4
        extended_run = models.np.zeros_like(active)
        extended_run[2:] |= active[1:-1] & active[:-2]
        extended_run[:-2] |= active[1:-1] & active[2:]
        meaningful = active & ((neighbours >= 3) | extended_run | strong)
        # Scanner streaks can occupy both outermost columns, so the former
        # two-neighbour rule still treated them as page content. At either
        # physical edge require a three-pixel run unless the mark spans at
        # least half of the opposite axis (an intentional page/frame rule).
        edge_width = min(3, len(meaningful))
        if edge_width:
            edge_strong = ink_counts >= max(minimum * 4, round(cross_size * 0.50))
            left_run = bool(models.np.all(active[:edge_width]))
            right_run = bool(models.np.all(active[-edge_width:]))
            meaningful[:edge_width] &= left_run | edge_strong[:edge_width]
            meaningful[-edge_width:] &= right_run | edge_strong[-edge_width:]
        return models.np.flatnonzero(meaningful)

    active_columns = meaningful_indices(column_ink, min_column_ink, height)
    active_rows = meaningful_indices(row_ink, min_row_ink, width)
    if active_columns.size == 0 or active_rows.size == 0:
        return None
    foreground_ratio = float(models.np.mean(foreground))
    def has_half_page_run(lines) -> bool:
        for line in lines:
            padded = models.np.concatenate((models.np.array([False]), line, models.np.array([False])))
            changes = models.np.flatnonzero(padded[1:] != padded[:-1])
            if changes.size >= 2 and int(models.np.max(changes[1::2] - changes[::2])) >= line.size * 0.50:
                return True
        return False

    if foreground_ratio < 0.06 and not (
        has_half_page_run(foreground) or has_half_page_run(foreground.T)
    ):
        return None
    # Two panel rows are separated by a horizontal rule, but on a page whose
    # panels sit side by side the gutters break that rule into several
    # collinear segments, none of them a quarter of the page wide. Requiring
    # one uninterrupted run would miss such a rule and leave the paper above
    # the first panel row uncropped, so segments that are each panel wide may
    # make up the rule between them.
    rule_length = max(12, round(width * 0.25))
    rule_segment_length = max(12, round(width * 0.12))
    split_rule_length = max(12, round(width * 0.40))

    def is_panel_rule_row(y: int) -> bool:
        padded = models.np.concatenate((models.np.array([False]), foreground[y], models.np.array([False])))
        changes = models.np.flatnonzero(padded[1:] != padded[:-1])
        if changes.size < 2:
            return False
        runs = changes[1::2] - changes[::2]
        if int(models.np.max(runs)) >= rule_length:
            return True
        return int(models.np.sum(runs[runs >= rule_segment_length])) >= split_rule_length

    content_top = int(active_rows[0])
    content_bottom = int(active_rows[-1])
    top_weak = content_top > 5 and int(row_ink[content_top]) < max(min_row_ink * 4, round(width * 0.05))
    bottom_weak = (
        content_bottom < height - 6
        and int(row_ink[content_bottom]) < max(min_row_ink * 4, round(width * 0.05))
    )

    def has_coherent_top_block() -> bool:
        """Report whether the topmost mark opens a solid run of page content.

        A caption or title line tapers to a handful of antialiased pixels on
        its first row, which reads exactly like scanner dust. What separates
        them is what follows: dust stops, a line of text keeps going for
        several rows with real ink behind it. This mirrors the coherent-tail
        test the bottom edge already applies.

        Only a margin-sized strip of paper qualifies. Further down the page
        the emptiness above the first mark is a deliberate composition -- a
        note or a title page -- and stays where the artist put it.
        """
        if content_top > max(20, round(height * 0.10)):
            return False
        end = content_top
        while end < height and int(row_ink[end]) >= min_row_ink:
            end += 1
        head = foreground[content_top:end]
        if head.shape[0] < 4:
            return False
        head_columns = models.np.flatnonzero(models.np.any(head, axis=0))
        head_width = int(head_columns[-1] - head_columns[0] + 1) if head_columns.size else 0
        return (
            head_width >= max(8, round(width * 0.01))
            and int(models.np.sum(head)) >= max(64, min_row_ink * 12)
        )

    def has_coherent_bottom_block() -> bool:
        """Report whether the lowest mark closes a solid run of page content.

        The mirror of ``has_coherent_top_block``, and the last thing asked
        before the bottom edge gives up and keeps the whole page. A panel
        border tapers to a few antialiased pixels on its final row, which
        reads exactly like scanner dust; what tells them apart is what sits
        above. Dust has nothing there, a border has the panel.

        It is the only anchor a page whose background is black has to offer:
        the artwork inside such a page's panels reads as background too, so
        the rows break into short runs and none of them is ever wide enough to
        pass for a panel rule.

        Only a margin-sized band of background qualifies. Deeper than that the
        emptiness below the last mark is a deliberate composition and stays
        where the artist put it.
        """
        if (height - 1 - content_bottom) > max(20, round(height * 0.10)):
            return False
        start = content_bottom
        while start >= 0 and int(row_ink[start]) >= min_row_ink:
            start -= 1
        tail = foreground[start + 1 : content_bottom + 1]
        if tail.shape[0] < 4:
            return False
        tail_columns = models.np.flatnonzero(models.np.any(tail, axis=0))
        tail_width = int(tail_columns[-1] - tail_columns[0] + 1) if tail_columns.size else 0
        return (
            tail_width >= max(8, round(width * 0.01))
            and int(models.np.sum(tail)) >= max(64, min_row_ink * 12)
        )

    ambiguous = False
    if top_weak and bottom_weak:
        structural_top = None
        structural_bottom = None
        for y in range(content_top, min(height, content_top + 13)):
            if is_panel_rule_row(y):
                structural_top = y
                break
        for y in range(content_bottom, max(-1, content_bottom - 13), -1):
            if is_panel_rule_row(y):
                structural_bottom = y
                break
        # When both outermost marks are weak, the lower panel rule can still
        # sit far above a large protruding bubble. Search farther inward and
        # retain the coherent content tail instead of falling back to the
        # physical page edge (which would keep all blank paper below it).
        if structural_bottom is None:
            context_depth = max(20, round(height * 0.12))
            for y in range(
                max(0, content_bottom - 13),
                max(-1, content_bottom - context_depth - 1),
                -1,
            ):
                if is_panel_rule_row(y):
                    structural_bottom = y
                    break
        top_replacement = structural_top
        if top_replacement is None:
            top_replacement = content_top if has_coherent_top_block() else 0
        if structural_bottom is not None:
            bottom_replacement = structural_bottom
        elif has_coherent_bottom_block():
            bottom_replacement = content_bottom
        else:
            bottom_replacement = height - 1
        if structural_bottom is not None and content_bottom > structural_bottom:
            tail = foreground[structural_bottom + 1 : content_bottom + 1]
            tail_row_ink = models.np.sum(tail, axis=1)
            tail_active_rows = models.np.flatnonzero(tail_row_ink >= min_row_ink)
            tail_columns = models.np.flatnonzero(models.np.any(tail, axis=0))
            tail_span = (
                int(tail_active_rows[-1] - tail_active_rows[0] + 1)
                if tail_active_rows.size
                else 0
            )
            tail_width = (
                int(tail_columns[-1] - tail_columns[0] + 1)
                if tail_columns.size
                else 0
            )
            if (
                tail_active_rows.size >= 4
                and tail_span >= 4
                and tail_width >= max(8, round(width * 0.01))
                and int(models.np.sum(tail_row_ink)) >= max(64, min_row_ink * 12)
            ):
                bottom_replacement = content_bottom
        active_rows = models.np.concatenate(
            (
                models.np.array([top_replacement], dtype=active_rows.dtype),
                active_rows,
                models.np.array([bottom_replacement], dtype=active_rows.dtype),
            )
        )
    elif top_weak:
        structural_top = None
        nearby_panel_rule = None
        for y in range(content_top, min(height, content_top + 13)):
            if is_panel_rule_row(y):
                structural_top = y
                break
        if structural_top is not None:
            active_rows = models.np.concatenate(
                (models.np.array([structural_top], dtype=active_rows.dtype), active_rows[active_rows > structural_top])
            )
        else:
            context_depth = max(20, round(height * 0.03))
            for y in range(min(height - 1, content_top + 13), min(height, content_top + context_depth + 1)):
                if is_panel_rule_row(y):
                    nearby_panel_rule = y
                    break
            if nearby_panel_rule is None and not has_coherent_top_block():
                ambiguous = True
                if not include_ambiguous:
                    active_rows = models.np.concatenate((models.np.array([0], dtype=active_rows.dtype), active_rows))
    elif bottom_weak:
        structural_bottom = None
        for y in range(content_bottom, max(-1, content_bottom - 13), -1):
            if is_panel_rule_row(y):
                structural_bottom = y
                break
        # The lowest speech bubble may extend much farther below its panel
        # rule than the small anti-noise window above.  Look deeper into the
        # page for that rule before declaring the whole bottom edge
        # ambiguous.  The coherent-tail check below still retains every
        # connected bubble/caption pixel below the rule; this only gives it a
        # structural anchor from which to distinguish content from blank
        # trailing paper.
        if structural_bottom is None:
            context_depth = max(20, round(height * 0.12))
            for y in range(
                max(0, content_bottom - 13),
                max(-1, content_bottom - context_depth - 1),
                -1,
            ):
                if is_panel_rule_row(y):
                    structural_bottom = y
                    break
        # A speech bubble, sound effect, or caption can deliberately cross a
        # panel rule. Do not snap to that rule when the weaker ink below it is
        # a coherent multi-row continuation; only isolated scanner noise may
        # be discarded this way.
        coherent_tail = False
        if structural_bottom is not None and content_bottom > structural_bottom:
            tail = foreground[structural_bottom + 1 : content_bottom + 1]
            tail_row_ink = models.np.sum(tail, axis=1)
            tail_active_rows = models.np.flatnonzero(tail_row_ink >= min_row_ink)
            tail_columns = models.np.flatnonzero(models.np.any(tail, axis=0))
            tail_span = (
                int(tail_active_rows[-1] - tail_active_rows[0] + 1)
                if tail_active_rows.size
                else 0
            )
            tail_width = (
                int(tail_columns[-1] - tail_columns[0] + 1)
                if tail_columns.size
                else 0
            )
            coherent_tail = (
                tail_active_rows.size >= 4
                and tail_span >= 4
                and tail_width >= max(8, round(width * 0.01))
                and int(models.np.sum(tail_row_ink)) >= max(64, min_row_ink * 12)
            )
        if coherent_tail:
            replacement = content_bottom
        elif structural_bottom is not None:
            replacement = structural_bottom
        elif has_coherent_bottom_block():
            replacement = content_bottom
        else:
            replacement = height - 1
        active_rows = models.np.concatenate(
            (active_rows[active_rows < replacement], models.np.array([replacement], dtype=active_rows.dtype))
        )
    # A horizontal panel rule can reach the physical left/right edge while
    # contributing too few pixels to each column to pass the column-density
    # threshold (for example a three-pixel rule on a 1400px page). The same is
    # true for thin vertical rules at the top/bottom. Such long edge-contacting
    # rules are page content and must anchor that side against cropping.
    def long_rule_edge_contacts(lines, ignore_solid_outer_line: bool = False) -> tuple[bool, bool]:
        # Only runs starting/ending within two pixels of the sheet edge can
        # anchor it. Test those six strips in bulk, without enumerating every
        # ink run throughout the drawing.
        minimum_run = max(12, round(lines.shape[1] * 0.25))
        if minimum_run > lines.shape[1]:
            return False, False
        eligible = models.np.ones(lines.shape[0], dtype=bool)
        if ignore_solid_outer_line:
            for index in (0, len(lines) - 1):
                eligible[index] = float(models.np.mean(lines[index])) < 0.98
        touches = []
        for oriented in (lines, lines[:, ::-1]):
            hits = models.np.zeros(lines.shape[0], dtype=bool)
            for offset in range(min(3, lines.shape[1] - minimum_run + 1)):
                hits |= models.np.all(oriented[:, offset:offset + minimum_run], axis=1)
            touches.append(bool(models.np.any(hits & eligible)))
        return touches[0], touches[1]

    rule_touches_left, rule_touches_right = long_rule_edge_contacts(
        foreground,
        ignore_solid_outer_line=True,
    )
    rule_touches_top, rule_touches_bottom = long_rule_edge_contacts(
        foreground.T,
        ignore_solid_outer_line=True,
    )
    if rule_touches_left:
        active_columns = models.np.concatenate(
            (models.np.array([0], dtype=active_columns.dtype), active_columns[active_columns > 0])
        )
    if rule_touches_right:
        active_columns = models.np.concatenate(
            (active_columns[active_columns < width - 1], models.np.array([width - 1], dtype=active_columns.dtype))
        )
    caption_edges = _terminal_caption_panel_edges(image)
    if rule_touches_top or "top" in caption_edges:
        active_rows = models.np.concatenate(
            (models.np.array([0], dtype=active_rows.dtype), active_rows[active_rows > 0])
        )
    if rule_touches_bottom or "bottom" in caption_edges:
        active_rows = models.np.concatenate(
            (active_rows[active_rows < height - 1], models.np.array([height - 1], dtype=active_rows.dtype))
        )
    # A panel border is not necessarily the outermost content. Pointed speech
    # bubbles, sound effects, or irregular frame artwork can cross it on any
    # side. Density-based row/column filtering may classify the narrow tip as
    # noise and snap the crop to the stronger rule. Restore an outer extension
    # when it belongs to the same connected foreground component as content on
    # the retained side of the proposed boundary. This is deliberately
    # symmetric: the same protection applies to top, bottom, left, and right.
    protected_left = int(active_columns[0])
    protected_top = int(active_rows[0])
    protected_right = int(active_columns[-1])
    protected_bottom = int(active_rows[-1])

    component_count, component_labels, component_stats, _ = models.cv2.connectedComponentsWithStats(
        foreground.astype(models.np.uint8),
        connectivity=8,
    )

    def coherent_extension(extension) -> bool:
        if not models.np.any(extension):
            return False
        coordinates = models.np.argwhere(extension)
        normal_span = int(coordinates[:, 0].max() - coordinates[:, 0].min() + 1)
        tangent_span = int(coordinates[:, 1].max() - coordinates[:, 1].min() + 1)
        pixel_count = int(coordinates.shape[0])
        active_layers = int(models.np.count_nonzero(models.np.any(extension, axis=1)))
        # A broad multi-row continuation is plainly intentional. Also retain
        # a genuinely pointed tip, which may contain only a few pixels near
        # its outermost end but must extend coherently for several layers.
        return active_layers >= 3 and tangent_span >= 2 and (
            pixel_count >= 24
            or (normal_span >= 4 and tangent_span >= 2 and pixel_count >= 8)
        )

    for component_index in range(1, component_count):
        component_left, component_top, component_width, component_height, _area = (
            int(value) for value in component_stats[component_index]
        )
        component_right = component_left + component_width - 1
        component_bottom = component_top + component_height - 1

        if component_top < protected_top <= component_bottom:
            outside = component_labels[
                component_top:protected_top,
                component_left : component_right + 1,
            ] == component_index
            if coherent_extension(outside):
                protected_top = component_top
        if component_top <= protected_bottom < component_bottom:
            # Transpose so the first dimension always points away from the
            # candidate boundary, matching ``coherent_extension`` above.
            outside = component_labels[
                protected_bottom + 1 : component_bottom + 1,
                component_left : component_right + 1,
            ] == component_index
            if coherent_extension(outside):
                protected_bottom = component_bottom
        if component_left < protected_left <= component_right:
            outside = (
                component_labels[
                    component_top : component_bottom + 1,
                    component_left:protected_left,
                ]
                == component_index
            ).T
            if coherent_extension(outside):
                protected_left = component_left
        if component_left <= protected_right < component_right:
            outside = (
                component_labels[
                    component_top : component_bottom + 1,
                    protected_right + 1 : component_right + 1,
                ]
                == component_index
            ).T
            if coherent_extension(outside):
                protected_right = component_right

    if protected_left < int(active_columns[0]):
        active_columns = models.np.concatenate(
            (models.np.array([protected_left], dtype=active_columns.dtype), active_columns)
        )
    if protected_top < int(active_rows[0]):
        active_rows = models.np.concatenate(
            (models.np.array([protected_top], dtype=active_rows.dtype), active_rows)
        )
    if protected_right > int(active_columns[-1]):
        active_columns = models.np.concatenate(
            (active_columns, models.np.array([protected_right], dtype=active_columns.dtype))
        )
    if protected_bottom > int(active_rows[-1]):
        active_rows = models.np.concatenate(
            (active_rows, models.np.array([protected_bottom], dtype=active_rows.dtype))
        )
    # A saturated full-page color frequently belongs to an intentional title
    # composition. Only remove it as a frame when real content is inset from
    # every side; neutral black/white margins may remain one-sided.
    if background is not None and max(background) - min(background) > 12:
        if (
            int(active_columns[0]) <= 5
            or int(active_rows[0]) <= 5
            or int(active_columns[-1]) >= width - 6
            or int(active_rows[-1]) >= height - 6
        ):
            return None
    candidate = _safe_candidate(
        "blank_edges",
        (int(active_columns[0]), int(active_rows[0]), int(active_columns[-1]), int(active_rows[-1])),
        width,
        height,
        ambiguous,
    )
    if candidate is None or (candidate.left, candidate.top, candidate.right, candidate.bottom) == (0, 0, width - 1, height - 1):
        return None
    return candidate


def build_crop_candidates(image: Image.Image, ignore_mask=None) -> list[CropCandidate]:
    """Build conservative deterministic options for the vision model to judge."""
    width, height = image.size
    candidates = [CropCandidate("keep", 0, 0, width - 1, height - 1)]
    blank_edges = _find_blank_edge_candidate(
        image,
        include_ambiguous=True,
        ignore_mask=ignore_mask,
    )
    if blank_edges:
        candidates.append(blank_edges)
    fill = _detect_fill_color(image, "none")
    try:
        _ensure_kcc_importable()
        from kindlecomicconverter.page_number_crop_alg import get_bbox_crop_margin, get_bbox_crop_margin_page_number

        for name, fn in (("page_numbers", get_bbox_crop_margin_page_number), ("margins", get_bbox_crop_margin)):
            bbox = fn(image, 1.0, fill)
            if bbox:
                candidate = _safe_candidate(name, (bbox[0], bbox[1], float(bbox[2]) - 1, float(bbox[3]) - 1), width, height)
                if candidate:
                    candidates.append(candidate)
    except Exception as exc:
        logger.warning("KCC crop candidates unavailable: %s", exc)

    unique: list[CropCandidate] = []
    seen: set[tuple[int, int, int, int]] = set()
    for candidate in candidates:
        key = (candidate.left, candidate.top, candidate.right, candidate.bottom)
        if key not in seen:
            unique.append(candidate)
            seen.add(key)
    return unique


def render_candidate(image: Image.Image, candidate: CropCandidate, margin: int = 5) -> Image.Image:
    """Crop while retaining up to ``margin`` existing source pixels around content."""
    margin = max(0, min(100, int(margin)))
    width, height = image.size
    left = max(0, candidate.left - margin)
    top = max(0, candidate.top - margin)
    right = min(width - 1, candidate.right + margin)
    bottom = min(height - 1, candidate.bottom + margin)
    return image.crop((left, top, right + 1, bottom + 1))


def apply_maic_crop(
    image: Image.Image,
    *,
    preserved_margin_percent: float = 0.6,
    max_passes: int = 4,
    target_size: tuple[int, int] | None = None,
    artifact_profiles: list[dict[str, Any]] | None = None,
    artifact_ignore_mask=None,
) -> tuple[Image.Image, dict[str, int], bool]:
    """Apply the conservative maic margin crop used by conversion and preview.

    The retained margin is 0.6% of the original shorter side by default, as in
    maic Mini. Ambiguous edges are kept, and a side cropped in one pass is
    locked so subsequent discovery passes cannot consume the retained margin,
    as is an edge carrying a caption panel.
    Verified top/bottom gradient fields are reduced to their first content.
    When ``target_size`` is supplied, verified left/right fields carrying a
    vertical black-to-white gradient may then be shortened just enough to move
    the page to that aspect ratio. Returned bounds are inclusive and use
    coordinates of the input image.
    """
    working = image.convert("RGB")
    source_width, source_height = working.size
    bounds = {"top": 0, "bottom": source_height - 1, "left": 0, "right": source_width - 1}
    if source_width < 8 or source_height < 8:
        return working, bounds, False
    # A scan's sheet-edge line is painted out before anything is measured:
    # left in, it joins whatever reaches that edge into one component that
    # spans the page and holds every margin.
    working, erased = _erase_sheet_edge_lines(working)

    if artifact_ignore_mask is None and artifact_profiles:
        artifact_ignore_mask, _artifact_matches = _peripheral_artifact_ignore_mask(
            working,
            artifact_profiles,
        )
    working_ignore = artifact_ignore_mask

    try:
        margin_percent = float(preserved_margin_percent)
    except (TypeError, ValueError):
        margin_percent = 0.6
    margin_percent = max(0.0, min(10.0, margin_percent))
    preserved_margin = max(
        0,
        int(math.floor(min(source_width, source_height) * margin_percent / 100.0 + 0.5)),
    )
    # A caption panel is composition on the page as it arrives.  Deciding
    # that again on each pass reads it off a page a previous pass has already
    # narrowed, and the panel can fall out of its own proportions: Gachiakuta
    # v5 ch40 p12 keeps its band through the first pass, then loses 82 rows of
    # it to the second because taking the left margin put the caption four
    # pixels past the share of the width a caption may cover.
    locked: set[str] = set(_terminal_caption_panel_edges(working))
    applied = erased

    for _ in range(max(1, min(4, int(max_passes)))):
        candidate = _find_blank_edge_candidate(
            working,
            include_ambiguous=False,
            ignore_mask=working_ignore,
        )
        width, height = working.size
        regular_box = None
        if candidate is not None:
            adjusted = CropCandidate(
                "blank_edges",
                0 if "left" in locked else candidate.left,
                0 if "top" in locked else candidate.top,
                width - 1 if "right" in locked else candidate.right,
                height - 1 if "bottom" in locked else candidate.bottom,
            )
            if _outside_foreground_ratio(
                working,
                adjusted,
                preserved_margin,
                ignore_mask=working_ignore,
            ) <= 0.003:
                proposed = (
                    max(0, adjusted.left - preserved_margin),
                    max(0, adjusted.top - preserved_margin),
                    min(width - 1, adjusted.right + preserved_margin),
                    min(height - 1, adjusted.bottom + preserved_margin),
                )
                if proposed != (0, 0, width - 1, height - 1):
                    regular_box = proposed

        crop_box = _gradient_aspect_crop_box(
            working,
            target_size,
            preserved_margin,
            locked,
            base_box=regular_box,
        )
        if crop_box is None:
            break
        crop_left, crop_top, crop_right, crop_bottom = crop_box

        old_left, old_top = bounds["left"], bounds["top"]
        bounds = {
            "top": old_top + crop_top,
            "bottom": old_top + crop_bottom,
            "left": old_left + crop_left,
            "right": old_left + crop_right,
        }
        if crop_left > 0:
            locked.add("left")
        if crop_top > 0:
            locked.add("top")
        if crop_right < width - 1:
            locked.add("right")
        if crop_bottom < height - 1:
            locked.add("bottom")
        working = working.crop((crop_left, crop_top, crop_right + 1, crop_bottom + 1))
        if working_ignore is not None:
            working_ignore = working_ignore[
                crop_top : crop_bottom + 1,
                crop_left : crop_right + 1,
            ]
        applied = True

    return working, bounds, applied


def _heuristic_choice(candidates: list[CropCandidate]) -> CropCandidate:
    for name in ("page_numbers", "margins", "keep"):
        found = next((candidate for candidate in candidates if candidate.name == name), None)
        if found:
            return found
    return candidates[0]


def _outside_foreground_ratio(
    image: Image.Image,
    candidate: CropCandidate,
    preserved_margin: int = 5,
    ignore_mask=None,
) -> float:
    """Estimate ink discarded outside the actual crop, including its retained margin."""
    from . import models

    models._ensure_imports()
    working = image.convert("RGB")
    width, height = working.size
    if max(width, height) > 640:
        scale = 640.0 / max(width, height)
        working = working.resize(
            (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
            getattr(Image.Resampling, "BILINEAR", Image.BILINEAR),
        )
    else:
        scale = 1.0
    scaled_ignore = ignore_mask
    if ignore_mask is not None:
        scaled_ignore = models.cv2.resize(
            models.np.asarray(ignore_mask, dtype=models.np.uint8),
            (working.width, working.height),
            interpolation=models.cv2.INTER_NEAREST,
        )
    foreground, _background = _crop_foreground_mask(working, scaled_ignore)
    preserved_margin = max(0, int(preserved_margin))
    left = max(0, int(max(0, candidate.left - preserved_margin) * scale))
    top = max(0, int(max(0, candidate.top - preserved_margin) * scale))
    right = min(working.width, math.ceil((min(width - 1, candidate.right + preserved_margin) + 1) * scale))
    bottom = min(working.height, math.ceil((min(height - 1, candidate.bottom + preserved_margin) + 1) * scale))

    if candidate.name == "blank_edges":
        # The fallback foreground mask has to choose one page colour.  A dark
        # page with a white lower field therefore classifies that whole field
        # as foreground (and the inverse happens on a white page with a black
        # field), even after the blank-edge detector has found its boundary.
        # Suppress only an almost-pure black/white strip outside that verified
        # boundary. Mixed strips still reach the ordinary loss guard unchanged.
        gray = models.np.asarray(working.convert("L"))

        def clear_blank_strip(rows, columns) -> None:
            strip = gray[rows, columns]
            if strip.size == 0:
                return
            near_white = float(models.np.mean(strip >= 245))
            near_black = float(models.np.mean(strip <= 10))
            if max(near_white, near_black) >= 0.985:
                foreground[rows, columns] = False

        clear_blank_strip(slice(0, top), slice(None))
        clear_blank_strip(slice(bottom, working.height), slice(None))
        clear_blank_strip(slice(None), slice(0, left))
        clear_blank_strip(slice(None), slice(right, working.width))

    total = int(foreground.sum())
    if total <= 0:
        return 0.0
    inside = int(foreground[top:max(top + 1, bottom), left:max(left + 1, right)].sum())
    return max(0.0, min(1.0, (total - inside) / total))


def filter_automatic_candidates(
    image: Image.Image,
    candidates: list[CropCandidate],
    ignore_mask=None,
) -> tuple[list[CropCandidate], list[str]]:
    """Remove crop options that appear to discard meaningful page content."""
    safe: list[CropCandidate] = []
    rejected: list[str] = []
    limits = {"blank_edges": 0.003, "page_numbers": 0.04, "margins": 0.025}
    for candidate in candidates:
        if candidate.name == "keep":
            safe.append(candidate)
            continue
        outside_ratio = _outside_foreground_ratio(image, candidate, ignore_mask=ignore_mask)
        if outside_ratio <= limits.get(candidate.name, 0.02):
            safe.append(candidate)
        else:
            rejected.append(f"{candidate.name}:{outside_ratio:.3f}")
    return safe, rejected


def build_automatic_crop_candidates(
    cleaned_image: Image.Image,
    *,
    artifact_profiles: list[dict[str, Any]] | None = None,
    artifact_ignore_mask=None,
) -> tuple[list[CropCandidate], list[str]]:
    """Detect and safety-check crop bounds on the already cleaned page."""
    if artifact_ignore_mask is None and artifact_profiles:
        artifact_ignore_mask, _artifact_matches = _peripheral_artifact_ignore_mask(
            cleaned_image,
            artifact_profiles,
        )
    candidates = (
        build_crop_candidates(cleaned_image)
        if artifact_ignore_mask is None
        else build_crop_candidates(cleaned_image, ignore_mask=artifact_ignore_mask)
    )
    if artifact_ignore_mask is None:
        return filter_automatic_candidates(cleaned_image, candidates)
    return filter_automatic_candidates(
        cleaned_image,
        candidates,
        ignore_mask=artifact_ignore_mask,
    )


def _load_artifact_profiles_from_root(root: str) -> list[dict[str, Any]]:
    if not root or not os.path.isdir(root):
        return []
    profiles: list[dict[str, Any]] = []
    for entry in sorted(os.listdir(root)):
        profile_dir = os.path.realpath(os.path.join(root, entry))
        if not os.path.isdir(profile_dir) or not is_under_allowed_root(profile_dir, [root]):
            continue
        manifest: dict[str, Any] = {}
        manifest_path = os.path.join(profile_dir, "manifest.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    manifest = loaded
            except (OSError, ValueError, TypeError) as exc:
                logger.warning("Invalid artifact manifest %s: %s", manifest_path, exc)
        references_dir = os.path.join(profile_dir, "references")
        search_dir = references_dir if os.path.isdir(references_dir) else profile_dir
        references = []
        reference_details = []
        reference_meta = manifest.get("referenceMeta")
        if not isinstance(reference_meta, dict):
            reference_meta = {}
        for name in sorted(os.listdir(search_dir)):
            if os.path.splitext(name)[1].lower() not in IMAGE_EXTS:
                continue
            try:
                with Image.open(os.path.join(search_dir, name)) as opened:
                    reference = ImageOps.exif_transpose(opened).convert("RGB")
                    if reference.width >= 4 and reference.height >= 4:
                        references.append(reference.copy())
                        raw_meta = reference_meta.get(name)
                        reference_details.append({
                            "image": reference.copy(),
                            "name": name,
                            "sourceSize": (
                                list(raw_meta.get("sourceSize"))
                                if isinstance(raw_meta, dict)
                                and isinstance(raw_meta.get("sourceSize"), list)
                                and len(raw_meta["sourceSize"]) == 2
                                else None
                            ),
                            "normalizedBox": (
                                list(raw_meta.get("normalizedBox"))
                                if isinstance(raw_meta, dict)
                                and isinstance(raw_meta.get("normalizedBox"), list)
                                and len(raw_meta["normalizedBox"]) == 4
                                else None
                            ),
                        })
            except Exception:
                continue
            if len(references) >= 8:
                break
        if not references:
            continue
        try:
            threshold = max(0.70, min(0.99, float(manifest.get("threshold", 0.88))))
        except (TypeError, ValueError):
            threshold = 0.88
        action = str(manifest.get("action") or "remove").lower()
        if action not in {"remove", "exclude"}:
            action = "remove"
        profiles.append({
            "id": str(manifest.get("id") or entry),
            "name": entry,
            "label": str(manifest.get("label") or entry)[:80],
            "action": action,
            "threshold": threshold,
            "references": references,
            "referenceDetails": reference_details,
            "managed": os.path.realpath(root) == os.path.realpath(ARTIFACT_PROFILE_DIR),
        })
    return profiles


def _load_artifact_profiles(path: str) -> list[dict[str, Any]]:
    """Load folder-based and web-managed removable artifact profiles."""
    examples_root = os.path.join(path, "artifacts") if path else ""
    profiles = _load_artifact_profiles_from_root(examples_root)
    profiles.extend(_load_artifact_profiles_from_root(ARTIFACT_PROFILE_DIR))
    return profiles


def _managed_artifact_profile_metadata() -> list[dict[str, Any]]:
    metadata = []
    if not os.path.isdir(ARTIFACT_PROFILE_DIR):
        return metadata
    for profile in _load_artifact_profiles_from_root(ARTIFACT_PROFILE_DIR):
        metadata.append({
            "id": profile["id"],
            "label": profile["label"],
            "action": profile["action"],
            "threshold": profile["threshold"],
            "referenceCount": len(profile["references"]),
        })
    return metadata


def _managed_profile_path(profile_id: str) -> str | None:
    value = str(profile_id or "").lower()
    if len(value) != 32 or any(character not in "0123456789abcdef" for character in value):
        return None
    root = os.path.realpath(ARTIFACT_PROFILE_DIR)
    target = os.path.realpath(os.path.join(root, value))
    return target if is_under_allowed_root(target, [root]) else None


def _write_managed_profile_manifest(profile_dir: str, manifest: dict[str, Any]) -> None:
    os.makedirs(profile_dir, exist_ok=True)
    target = os.path.join(profile_dir, "manifest.json")
    temporary = target + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, target)



def _box_iou(first: list[int], second: list[int]) -> float:
    left, top = max(first[0], second[0]), max(first[1], second[1])
    right, bottom = min(first[2], second[2]), min(first[3], second[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    if intersection <= 0:
        return 0.0
    first_area = max(1, (first[2] - first[0]) * (first[3] - first[1]))
    second_area = max(1, (second[2] - second[0]) * (second[3] - second[1]))
    return intersection / max(1, first_area + second_area - intersection)


def _box_is_excluded(box: list[int], exclusions: list[dict[str, Any]]) -> bool:
    center_x, center_y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    for exclusion in exclusions:
        excluded_box = exclusion["box"]
        if _box_iou(box, excluded_box) >= 0.15:
            return True
        if excluded_box[0] <= center_x <= excluded_box[2] and excluded_box[1] <= center_y <= excluded_box[3]:
            return True
    return False


def _uniform_artifact_background(
    image: Image.Image,
    box: list[int],
) -> tuple[bool, tuple[int, int, int], dict[str, float]]:
    """Infer a safe solid fill from a narrow ring around an artifact box."""
    from . import models

    models._ensure_imports()
    rgb = models.np.array(image.convert("RGB"))
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = [int(value) for value in box]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(width, x2), min(height, y2)
    if x2 <= x1 or y2 <= y1:
        return False, (255, 255, 255), {"uniformRatio": 0.0, "variation": 255.0}
    pad = max(6, min(24, round(min(x2 - x1, y2 - y1) * 0.50)))
    ox1, oy1, ox2, oy2 = max(0, x1 - pad), max(0, y1 - pad), min(width, x2 + pad), min(height, y2 + pad)
    outer = rgb[oy1:oy2, ox1:ox2]
    ring_mask = models.np.ones(outer.shape[:2], dtype=bool)
    ring_mask[y1 - oy1 : y2 - oy1, x1 - ox1 : x2 - ox1] = False
    samples = outer[ring_mask]
    minimum_samples = max(64, (x2 - x1 + y2 - y1) * 2)
    if samples.shape[0] < minimum_samples:
        return False, (255, 255, 255), {"uniformRatio": 0.0, "variation": 255.0}
    median = models.np.median(samples, axis=0)
    distance = models.np.max(models.np.abs(samples.astype(models.np.float32) - median), axis=1)
    uniform_ratio = float(models.np.mean(distance <= 14.0))
    variation = float(models.np.percentile(distance, 95))
    side_ratios: list[float] = []
    for side in (
        rgb[oy1:y1, ox1:ox2],
        rgb[y2:oy2, ox1:ox2],
        rgb[y1:y2, ox1:x1],
        rgb[y1:y2, x2:ox2],
    ):
        if side.size:
            side_distance = models.np.max(
                models.np.abs(side.reshape(-1, 3).astype(models.np.float32) - median), axis=1
            )
            side_ratios.append(float(models.np.mean(side_distance <= 14.0)))
    # A nearby panel rule can occupy a few percent of the outer ring without
    # crossing the artifact itself. Requiring a 95% dominant color still
    # rejects artwork while allowing such clean page-margin backgrounds.
    minimum_side_ratio = min(side_ratios, default=0.0)
    safe = uniform_ratio >= 0.95 and variation <= 18.0 and minimum_side_ratio >= 0.90
    color = tuple(int(round(float(value))) for value in median)
    return safe, color, {
        "uniformRatio": round(uniform_ratio, 4),
        "variation": round(variation, 2),
        "minimumSideUniformRatio": round(minimum_side_ratio, 4),
    }


def _find_reference_artifact_candidates(
    image: Image.Image,
    profiles: list[dict[str, Any]],
    max_candidates: int = 12,
) -> list[dict[str, Any]]:
    """Propose multi-scale template matches for deterministic profile rules."""
    from . import models

    if not profiles:
        return []
    models._ensure_imports()
    page_gray = models.np.array(image.convert("L"))
    page_height, page_width = page_gray.shape[:2]
    matches: list[dict[str, Any]] = []
    for profile in profiles:
        for reference in profile.get("references", []):
            reference_gray = models.np.array(reference.convert("L"))
            # Logos are often resized between chapters/scan passes. Use denser
            # scales around the common range and allow a tiny interpolation
            # tolerance; the profile threshold still gates removal.
            # Candidate proposal is deliberately broader than direct removal:
            # resampled copies can lose substantial pixel correlation. The
            # profile threshold gates deterministic removal; near-threshold
            # candidates remain untouched.
            proposal_threshold = max(0.55, float(profile["threshold"]) - 0.20)
            for scale in (0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 1.0, 1.10, 1.25, 1.40, 1.60):
                target_width = max(4, round(reference_gray.shape[1] * scale))
                target_height = max(4, round(reference_gray.shape[0] * scale))
                if target_width > page_width or target_height > page_height:
                    continue
                resized = models.cv2.resize(reference_gray, (target_width, target_height), interpolation=models.cv2.INTER_AREA if scale < 1 else models.cv2.INTER_CUBIC)
                # CCOEFF preserves the shape under a brightness/contrast change;
                # taking the absolute value also recognises an inverted logo
                # (for example white artwork on a dark coloured margin).
                response = models.np.abs(models.cv2.matchTemplate(page_gray, resized, models.cv2.TM_CCOEFF_NORMED))
                for _ in range(3):
                    _min_value, max_value, _min_location, max_location = models.cv2.minMaxLoc(response)
                    if float(max_value) < proposal_threshold:
                        break
                    x1, y1 = int(max_location[0]), int(max_location[1])
                    box = [x1, y1, x1 + target_width, y1 + target_height]
                    # Keep overlapping scale proposals until they are sorted:
                    # an early, weaker scale must not hide the exact match found
                    # later in the scale sweep.
                    matches.append({
                        "box": box,
                        "profile": profile["id"],
                        "label": profile["label"],
                        "action": profile.get("action", "remove"),
                        "threshold": profile["threshold"],
                        "score": round(float(max_value), 4),
                    })
                    suppress_x1, suppress_y1 = max(0, x1 - target_width // 2), max(0, y1 - target_height // 2)
                    suppress_x2 = min(response.shape[1], x1 + target_width // 2 + 1)
                    suppress_y2 = min(response.shape[0], y1 + target_height // 2 + 1)
                    response[suppress_y1:suppress_y2, suppress_x1:suppress_x2] = -1
    matches.sort(key=lambda item: item["score"], reverse=True)
    selected: list[dict[str, Any]] = []
    for match in matches:
        if any(_box_iou(match["box"], existing["box"]) > 0.45 for existing in selected):
            continue
        selected.append(match)
        if len(selected) >= max_candidates:
            break
    for index, candidate in enumerate(selected, 1):
        candidate["id"] = f"A{index:02d}"
    return selected


def _artifact_midtone_mask(image: Image.Image):
    """Return broad non-black/non-white strokes used by translucent marks.

    Manga artwork is predominantly made of hard black/white pixels and fine
    screentone. A translucent watermark turns either background into broad
    middle-grey strokes. Taking the distance from the nearest tonal extreme
    makes the same mark comparable on black, white, and mixed artwork without
    attempting to reconstruct or alter the pixels below it.
    """
    from . import models

    models._ensure_imports()
    gray = models.np.asarray(image.convert("L"), dtype=models.np.uint8)
    middle = models.np.minimum(gray, 255 - gray)
    mask = (middle >= 24).astype(models.np.uint8) * 255
    if min(image.size) >= 80:
        mask = models.cv2.morphologyEx(
            mask,
            models.cv2.MORPH_OPEN,
            models.np.ones((3, 3), dtype=models.np.uint8),
        )
    return mask


def _artifact_reference_shape(reference: Image.Image):
    """Extract a tight, reusable translucent-stroke silhouette from a sample."""
    from . import models

    models._ensure_imports()
    mask = _artifact_midtone_mask(reference)
    component_count, labels, stats, _centroids = models.cv2.connectedComponentsWithStats(
        (mask > 0).astype(models.np.uint8), connectivity=8
    )
    minimum_area = max(6, round(reference.width * reference.height * 0.00025))
    cleaned = models.np.zeros_like(mask)
    for component_index in range(1, component_count):
        _x, _y, component_width, component_height, area = (
            int(value) for value in stats[component_index]
        )
        if area >= minimum_area and component_width >= 2 and component_height >= 2:
            cleaned[labels == component_index] = 255
    rows, columns = models.np.where(cleaned > 0)
    if rows.size < 32:
        return None
    left, top = int(columns.min()), int(rows.min())
    right, bottom = int(columns.max()) + 1, int(rows.max()) + 1
    shape = cleaned[top:bottom, left:right]
    density = float(models.np.mean(shape > 0))
    if shape.shape[0] < 4 or shape.shape[1] < 4 or not 0.015 <= density <= 0.80:
        return None
    return shape, (left, top, right, bottom)


def _profile_reference_details(profile: dict[str, Any]) -> list[dict[str, Any]]:
    details = profile.get("referenceDetails")
    if isinstance(details, list) and details:
        return [item for item in details if isinstance(item, dict) and item.get("image") is not None]
    return [
        {"image": reference, "name": "", "sourceSize": None, "normalizedBox": None}
        for reference in profile.get("references", [])
    ]


def _peripheral_artifact_ignore_mask(
    image: Image.Image,
    profiles: list[dict[str, Any]] | None,
    *,
    perimeter_ratio: float = 0.24,
    max_candidates: int = 12,
) -> tuple[Any | None, list[dict[str, Any]]]:
    """Find taught translucent marks around the page and return crop-only ink.

    The central rectangle is never searched. A confirmed match clears only its
    tight matched box from crop analysis; the original image is returned and
    rendered untouched. A relaxed score is allowed near the sample's original
    normalized position, while a wandering mark elsewhere on the perimeter
    must pass a stricter shape score.
    """
    from . import models

    if not profiles:
        return None, []
    models._ensure_imports()
    source_width, source_height = image.size
    if source_width < 32 or source_height < 32:
        return None, []
    perimeter_ratio = max(0.12, min(0.35, float(perimeter_ratio)))

    source_midtone = _artifact_midtone_mask(image)
    source_gray = models.np.asarray(image.convert("L"), dtype=models.np.uint8)
    source_edges = models.cv2.Laplacian(source_gray, models.cv2.CV_32F)
    analysis_scale = min(1.0, 900.0 / max(source_width, source_height))
    analysis_width = max(16, int(round(source_width * analysis_scale)))
    analysis_height = max(16, int(round(source_height * analysis_scale)))
    if analysis_scale < 1.0:
        resized = models.cv2.resize(
            source_midtone,
            (analysis_width, analysis_height),
            interpolation=models.cv2.INTER_AREA,
        )
        analysis_mask = (resized >= 64).astype(models.np.uint8)
    else:
        analysis_mask = (source_midtone > 0).astype(models.np.uint8)
    target = analysis_mask.astype(models.np.float32)
    target_dilated = (
        models.cv2.dilate(analysis_mask, models.np.ones((3, 3), dtype=models.np.uint8)) > 0
    ).astype(models.np.float32)

    matches: list[dict[str, Any]] = []
    for profile in profiles:
        action = str(profile.get("action") or "remove").lower()
        if action not in {"remove", "exclude"}:
            continue
        try:
            saved_threshold = max(0.70, min(0.99, float(profile.get("threshold", 0.88))))
        except (TypeError, ValueError):
            saved_threshold = 0.88
        near_threshold = max(0.48, min(0.64, 0.54 + (saved_threshold - 0.88) * 0.35))
        roaming_threshold = max(0.60, min(0.78, 0.66 + (saved_threshold - 0.88) * 0.35))

        for detail in _profile_reference_details(profile):
            reference = detail.get("image")
            if not isinstance(reference, Image.Image):
                continue
            extracted = _artifact_reference_shape(reference)
            if extracted is None:
                continue
            reference_shape, trim_box = extracted
            trim_left, trim_top, trim_right, trim_bottom = trim_box
            reference_gray = models.np.asarray(reference.convert("L"), dtype=models.np.uint8)[
                trim_top:trim_bottom, trim_left:trim_right
            ]
            source_size = detail.get("sourceSize")
            if (
                isinstance(source_size, (list, tuple))
                and len(source_size) == 2
                and float(source_size[0]) > 0
                and float(source_size[1]) > 0
            ):
                base_scale = min(
                    analysis_width / float(source_size[0]),
                    analysis_height / float(source_size[1]),
                )
            else:
                base_scale = analysis_scale

            normalized_box = detail.get("normalizedBox")
            origin_center = None
            if isinstance(normalized_box, (list, tuple)) and len(normalized_box) == 4:
                try:
                    box_left, box_top, box_right, box_bottom = [float(value) for value in normalized_box]
                    origin_center = (
                        box_left + ((trim_left + trim_right) * 0.5 / reference.width) * (box_right - box_left),
                        box_top + ((trim_top + trim_bottom) * 0.5 / reference.height) * (box_bottom - box_top),
                    )
                except (TypeError, ValueError, ZeroDivisionError):
                    origin_center = None

            relative_scales = (
                (0.88, 1.0, 1.12)
                if isinstance(source_size, (list, tuple)) and len(source_size) == 2
                else (0.72, 0.86, 1.0, 1.16, 1.34)
            )
            for relative_scale in relative_scales:
                scale = base_scale * relative_scale
                target_width = max(4, int(round(reference_shape.shape[1] * scale)))
                target_height = max(4, int(round(reference_shape.shape[0] * scale)))
                if target_width >= analysis_width or target_height >= analysis_height:
                    continue
                template = (
                    models.cv2.resize(
                        reference_shape,
                        (target_width, target_height),
                        interpolation=models.cv2.INTER_AREA if scale < 1 else models.cv2.INTER_NEAREST,
                    )
                    >= 96
                ).astype(models.np.float32)
                positive_count = float(models.np.sum(template))
                if positive_count < 16:
                    continue
                overlap = models.cv2.matchTemplate(target_dilated, template, models.cv2.TM_CCORR)
                target_count = models.cv2.matchTemplate(
                    target,
                    models.np.ones(template.shape, dtype=models.np.float32),
                    models.cv2.TM_CCORR,
                )
                recall = models.np.clip(overlap / positive_count, 0.0, 1.0)
                precision = models.np.clip(overlap / models.np.maximum(target_count, 1.0), 0.0, 1.0)
                # The selected sample can contain drawing below a translucent
                # logo. The geometric mean still requires evidence in both
                # directions, but does not punish that unavoidable reference
                # clutter as harshly as harmonic/F1 scoring does.
                score = models.np.sqrt(precision * recall)
                score = models.np.nan_to_num(score, nan=-1.0, posinf=-1.0, neginf=-1.0)

                response_height, response_width = score.shape
                yy, xx = models.np.indices((response_height, response_width))
                center_x = xx + target_width * 0.5
                center_y = yy + target_height * 0.5
                normalized_x = center_x / analysis_width
                normalized_y = center_y / analysis_height
                perimeter = (
                    (normalized_x <= perimeter_ratio)
                    | (normalized_x >= 1.0 - perimeter_ratio)
                    | (normalized_y <= perimeter_ratio)
                    | (normalized_y >= 1.0 - perimeter_ratio)
                )
                required = models.np.full(score.shape, roaming_threshold, dtype=models.np.float32)
                if origin_center is not None:
                    near_origin = (
                        (models.np.abs(normalized_x - origin_center[0]) <= 0.075)
                        & (models.np.abs(normalized_y - origin_center[1]) <= 0.075)
                    )
                    required[near_origin] = near_threshold
                eligible = perimeter & (score >= required)
                if not models.np.any(eligible):
                    continue
                local_max = score >= models.cv2.dilate(score.astype(models.np.float32), models.np.ones((9, 9), dtype=models.np.uint8)) - 1e-6
                peak_rows, peak_columns = models.np.where(eligible & local_max)
                if peak_rows.size == 0:
                    continue
                peak_scores = score[peak_rows, peak_columns]
                order = list(models.np.argsort(peak_scores)[::-1][:4])
                # Artwork elsewhere in the perimeter can generate several
                # stronger coarse peaks. Always carry the best peak from the
                # taught neighbourhood into full-resolution verification too.
                if origin_center is not None:
                    near_peaks = (
                        (models.np.abs(normalized_x[peak_rows, peak_columns] - origin_center[0]) <= 0.075)
                        & (models.np.abs(normalized_y[peak_rows, peak_columns] - origin_center[1]) <= 0.075)
                    )
                    near_peak_indices = models.np.flatnonzero(near_peaks)
                    if near_peak_indices.size:
                        best_near = int(
                            near_peak_indices[models.np.argmax(peak_scores[near_peak_indices])]
                        )
                        if best_near not in order:
                            order.append(best_near)
                for peak_index in order:
                    x1 = int(peak_columns[peak_index])
                    y1 = int(peak_rows[peak_index])
                    x2, y2 = x1 + target_width, y1 + target_height
                    source_box = [
                        max(0, int(math.floor(x1 / analysis_scale))),
                        max(0, int(math.floor(y1 / analysis_scale))),
                        min(source_width, int(math.ceil(x2 / analysis_scale))),
                        min(source_height, int(math.ceil(y2 / analysis_scale))),
                    ]
                    source_x1, source_y1, source_x2, source_y2 = source_box
                    source_template = models.cv2.resize(
                        template.astype(models.np.uint8),
                        (source_x2 - source_x1, source_y2 - source_y1),
                        interpolation=models.cv2.INTER_NEAREST,
                    )
                    target_patch = (source_midtone[source_y1:source_y2, source_x1:source_x2] > 0).astype(models.np.uint8)
                    tolerance_kernel = models.np.ones((3, 3), dtype=models.np.uint8)
                    target_near = models.cv2.dilate(target_patch, tolerance_kernel) > 0
                    template_near = models.cv2.dilate(source_template, tolerance_kernel) > 0
                    template_pixels = source_template > 0
                    target_pixels = target_patch > 0
                    verified_recall = (
                        float(models.np.mean(target_near[template_pixels]))
                        if models.np.any(template_pixels)
                        else 0.0
                    )
                    verified_precision = (
                        float(models.np.mean(template_near[target_pixels]))
                        if models.np.any(target_pixels)
                        else 0.0
                    )
                    verified_score = math.sqrt(verified_precision * verified_recall)
                    # Precision and recall both saturate on a solid midtone
                    # field, so a halftone fill scores sqrt(template density)
                    # -- above the relaxed threshold used at the taught
                    # position -- without resembling the mark at all. A real
                    # mark leaves the paper around its strokes lighter than
                    # the strokes themselves, so require the midtone to be
                    # denser inside the silhouette than beside it.
                    background_pixels = ~template_pixels
                    inside_ratio = (
                        float(models.np.mean(target_pixels[template_pixels]))
                        if models.np.any(template_pixels)
                        else 0.0
                    )
                    outside_ratio = (
                        float(models.np.mean(target_pixels[background_pixels]))
                        if models.np.any(background_pixels)
                        else 0.0
                    )
                    silhouette_contrast = inside_ratio - outside_ratio
                    if silhouette_contrast < 0.12:
                        continue
                    # A broad midtone silhouette alone can align with manga
                    # screentone, clothing or roof hatching. Confirm that the
                    # local edge arrangement also resembles the taught mark.
                    # Absolute NCC keeps white-on-black/inverted variants
                    # valid, while a small search pad absorbs coarse-scale
                    # rounding without making the check position-dependent.
                    patch_width = source_x2 - source_x1
                    patch_height = source_y2 - source_y1
                    edge_reference = models.cv2.resize(
                        reference_gray,
                        (patch_width, patch_height),
                        interpolation=(
                            models.cv2.INTER_AREA
                            if patch_width < reference_gray.shape[1]
                            or patch_height < reference_gray.shape[0]
                            else models.cv2.INTER_CUBIC
                        ),
                    )
                    edge_template = models.cv2.Laplacian(edge_reference, models.cv2.CV_32F)
                    edge_pad = max(2, int(round(max(patch_width, patch_height) * 0.025)))
                    edge_left = max(0, source_x1 - edge_pad)
                    edge_top = max(0, source_y1 - edge_pad)
                    edge_right = min(source_width, source_x2 + edge_pad)
                    edge_bottom = min(source_height, source_y2 + edge_pad)
                    edge_region = source_edges[edge_top:edge_bottom, edge_left:edge_right]
                    edge_score = 0.0
                    if (
                        edge_region.shape[1] >= patch_width
                        and edge_region.shape[0] >= patch_height
                        and float(models.np.std(edge_template)) > 1e-6
                    ):
                        edge_response = models.np.abs(models.cv2.matchTemplate(
                            edge_region,
                            edge_template,
                            models.cv2.TM_CCOEFF_NORMED,
                        ))
                        if edge_response.size:
                            edge_score = float(models.np.nanmax(edge_response))
                    if edge_score < 0.075:
                        continue
                    # Neither signal separates a mark from artwork on its own:
                    # dense screentone reaches the contrast of a faint logo,
                    # and a busy corner reaches its edge correlation. Their
                    # product does, and it still lets a strong showing on one
                    # carry a weaker showing on the other.
                    if edge_score * silhouette_contrast < 0.033:
                        continue
                    near_saved_position = bool(
                        origin_center is not None
                        and abs(float(normalized_x[y1, x1]) - origin_center[0]) <= 0.075
                        and abs(float(normalized_y[y1, x1]) - origin_center[1]) <= 0.075
                    )
                    verification_threshold = (
                        max(0.48, min(0.62, 0.52 + (saved_threshold - 0.88) * 0.30))
                        if near_saved_position
                        else max(0.55, min(0.70, 0.60 + (saved_threshold - 0.88) * 0.30))
                    )
                    if verified_score < verification_threshold:
                        continue
                    matches.append({
                        "box": source_box,
                        "profile": str(profile.get("id") or profile.get("name") or "artifact"),
                        "label": str(profile.get("label") or profile.get("name") or "Artifact"),
                        "action": action,
                        "score": round(verified_score, 4),
                        "threshold": round(verification_threshold, 4),
                        "proposalScore": round(float(peak_scores[peak_index]), 4),
                        "edgeScore": round(edge_score, 4),
                        "contrast": round(silhouette_contrast, 4),
                        "method": "peripheral_midtone_shape",
                        "_template": source_template,
                    })

    matches.sort(key=lambda item: item["score"], reverse=True)
    selected: list[dict[str, Any]] = []
    per_profile: dict[str, int] = {}
    for match in matches:
        profile_id = match["profile"]
        # A saved logo profile normally occurs once per page. Keeping only its
        # strongest perimeter instance prevents a dense screentone elsewhere
        # from becoming a second crop-only match. Separate recurring marks can
        # still be taught as separate profiles.
        if per_profile.get(profile_id, 0) >= 1:
            continue
        if any(_box_iou(match["box"], existing["box"]) > 0.40 for existing in selected):
            continue
        selected.append(match)
        per_profile[profile_id] = per_profile.get(profile_id, 0) + 1
        if len(selected) >= max_candidates:
            break

    exclusions = [item for item in selected if item.get("action") == "exclude"]
    removable = [
        item for item in selected
        if item.get("action") == "remove" and not _box_is_excluded(item["box"], exclusions)
    ]
    public = [{key: value for key, value in item.items() if not key.startswith("_")} for item in selected]
    for index, item in enumerate(public, 1):
        item["id"] = f"W{index:02d}"
    if not removable:
        return None, public

    ignore = models.np.zeros((source_height, source_width), dtype=models.np.uint8)
    for match in removable:
        x1, y1, x2, y2 = match["box"]
        if x2 <= x1 or y2 <= y1:
            continue
        # The silhouette supplies identity and placement; the tight matched
        # box is the crop-only exclusion. This also covers opaque lettering and
        # JPEG fringe that are absent from a translucent midtone silhouette.
        # No source pixel is painted: content elsewhere on the page still has
        # to support every crop boundary through the ordinary loss guards.
        ignore[y1:y2, x1:x2] = 1
    dilation = max(1, min(4, round(min(source_width, source_height) * 0.0015)))
    ignore = models.cv2.dilate(
        ignore,
        models.np.ones((dilation * 2 + 1, dilation * 2 + 1), dtype=models.np.uint8),
    ).astype(bool)
    return ignore, public


_job_lock = threading.RLock()
_job: dict[str, Any] = {
    "running": False,
    "stop_requested": False,
    "phase": "idle",
    "current": 0,
    "total": 0,
    "currentFile": "",
    "progress": 0,
    "log": [],
    "processed": 0,
    "failed": 0,
    "fallbacks": 0,
    "results": [],
}


def _set_job(**values: Any) -> None:
    with _job_lock:
        _job.update(values)


def _log(message: str) -> None:
    with _job_lock:
        _job["log"].append(str(message))
        _job["log"] = _job["log"][-500:]


def autonomous_status() -> dict[str, Any]:
    with _job_lock:
        return json.loads(json.dumps(_job))


def _normalized_files(items: Any, root_dir: str) -> list[dict[str, str]]:
    roots = list(state.get("allowed_read_roots", []))
    out = []
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        path = os.path.realpath(str(item.get("path") or ""))
        if not os.path.isfile(path) or os.path.splitext(path)[1].lower() not in IMAGE_EXTS:
            continue
        if not is_under_allowed_root(path, roots):
            continue
        rel = str(item.get("relPath") or "").replace("\\", "/").lstrip("/")
        if not rel and root_dir:
            try:
                rel = os.path.relpath(path, root_dir).replace("\\", "/")
            except ValueError:
                rel = os.path.basename(path)
        if not rel or os.path.splitdrive(rel)[0] or ".." in rel.split("/"):
            rel = os.path.basename(path)
        archive_tmp = os.path.realpath(str(item.get("archiveTmp") or "")) if item.get("archiveTmp") else ""
        if archive_tmp and not is_under_allowed_root(path, [archive_tmp]):
            archive_tmp = ""
        output_prefix = str(item.get("outputPrefix") or "").replace("\\", "/").strip("/")
        if os.path.splitdrive(output_prefix)[0] or ".." in output_prefix.split("/"):
            output_prefix = ""
        out.append({"path": path, "name": os.path.basename(path), "relPath": rel, "archiveTmp": archive_tmp, "outputPrefix": output_prefix})
    return out


def _save_image(image: Image.Image, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ext = os.path.splitext(path)[1].lower()
    if ext in {".jpg", ".jpeg"}:
        image.convert("RGB").save(path, quality=95, subsampling=0)
    elif ext == ".webp":
        image.save(path, quality=95, method=6)
    else:
        image.save(path, optimize=ext == ".png")


def _page_number_cleanup_from_decision(
    image: Image.Image,
    decision: dict[str, Any],
    method: str,
    padding: int,
    protected_candidates: list[dict[str, Any]] | None = None,
) -> tuple[Image.Image, int, dict[str, Any]]:
    """Apply an already completed local page-number decision."""
    from . import models

    models._ensure_imports()
    # Never let the page-number pass erase a fragment of a known logo/profile
    # match. Removable profiles are handled as a whole by the artifact pass;
    # exclusion profiles stay untouched by both passes.
    protected = protected_candidates or []
    boxes = [box for box in decision["boxes"] if not _box_is_excluded(box, protected)]
    manual_boxes = [
        list(box) for box in decision.get("manualExactBoxes", [])
        if isinstance(box, list) and len(box) == 4 and not _box_is_excluded(box, protected)
    ]
    excluded_count = len(decision["boxes"]) - len(boxes)
    if excluded_count:
        decision["boxes"] = boxes
        decision["has_page_number"] = bool(boxes)
        decision["selectedIds"] = [] if not boxes else decision.get("selectedIds", [])
        decision["protectedByArtifactProfiles"] = excluded_count
    if not boxes:
        return image, 0, decision
    bgr = models.cv2.cvtColor(models.np.array(image.convert("RGB")), models.cv2.COLOR_RGB2BGR)
    cleaned = bgr.copy()
    # A hand-drawn rectangle is an explicit correction in a page gutter. Do
    # not send that rectangle to Telea/LaMa: their neighbourhood search can
    # pull a nearby black frame line into the cleared area. Fill only the exact
    # selected pixels with the dominant surrounding colour, with zero hidden
    # dilation. The stored reference is already cropped tightly by the user.
    manual_keys = {tuple(int(value) for value in box) for box in manual_boxes}
    for box in manual_boxes:
        x1, y1, x2, y2 = [int(value) for value in box]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(bgr.shape[1], x2), min(bgr.shape[0], y2)
        if x2 <= x1 or y2 <= y1:
            continue
        _safe, rgb_fill, fill_stats = _uniform_artifact_background(image, box)
        cleaned[y1:y2, x1:x2] = [rgb_fill[2], rgb_fill[1], rgb_fill[0]]
        decision.setdefault("manualFill", []).append({
            "box": [x1, y1, x2, y2],
            "color": list(rgb_fill),
            "background": fill_stats,
        })
    automatic_boxes = [box for box in boxes if tuple(int(value) for value in box) not in manual_keys]
    if automatic_boxes:
        mask = create_mask_image(
            bgr.shape[0], bgr.shape[1], {"boxes": automatic_boxes, "masks": []}, padding
        )
        automatic_cleaned = clean_image(bgr, mask, method)
        cleaned[mask > 0] = automatic_cleaned[mask > 0]
    return (
        Image.fromarray(models.cv2.cvtColor(cleaned, models.cv2.COLOR_BGR2RGB)),
        len(boxes),
        decision,
    )


def apply_maic_page_number_cleanup(
    image: Image.Image,
    *,
    method: str = "lama",
    padding: int = 2,
    bottom_ratio: float = 0.20,
    artifact_profiles: list[dict[str, Any]] | None = None,
    scope_path: str = "",
    minimum_page_number: int = 1,
    sequence: PageNumberSequence | None = None,
    chapter_key: str = "",
) -> tuple[Image.Image, int, dict[str, Any]]:
    """Remove a page number confirmed by the local digit detector."""
    source = image.convert("RGB")
    minimum = max(page_number_minimum(minimum_page_number), sequence.minimum(chapter_key) if sequence else 1)
    local_decision = detect_page_numbers_locally(
        source, bottom_ratio, scope_path, minimum_page_number=minimum
    )
    if sequence is not None:
        sequence.observe(chapter_key, local_decision)
    # The usual case is a page without a folio. Return before loading and
    # matching watermark profiles; doing that work for every preview page was
    # another avoidable source of latency.
    if not local_decision.get("has_page_number"):
        return source, 0, local_decision
    profiles = artifact_profiles if artifact_profiles is not None else _load_artifact_profiles("")
    protected = _find_reference_artifact_candidates(source, profiles) if profiles else []
    return _page_number_cleanup_from_decision(
        source,
        local_decision,
        str(method or "lama"),
        max(0, min(100, int(padding))),
        protected,
    )


def _artifact_fill_keep_mask(
    image: Image.Image,
    fill_box: tuple[int, int, int, int],
    color: tuple[int, int, int],
    *,
    margin: int = 12,
    ink_distance: int = 140,
    faint_distance: int = 60,
) -> Any:
    """Ink that only passes through the filled box and must outlive it.

    A logo is self-contained: every stroke of it ends inside the matched box,
    so the fill may take all of them. A panel rule, a speech-bubble tail or a
    figure crossing the corner continues past the edge, and painting over it
    cuts the drawing in two. Those are kept by tracing each ink component into
    a ring around the box and sparing the ones with ink beyond it.

    Only strong ink earns the exemption: a translucent mark never lands this
    far from the paper it sits on, so its own strokes can never claim it. The
    The mark does wash out the line it covers, so the line is traced through
    the fainter ink it becomes underneath: components are grown at the faint
    level and kept only where strong ink reaches out of the box. Otherwise the
    rule comes back with a hole exactly where the two crossed. The mark's own
    strokes stay below the faint level as well, so growing at that level never
    drags the mark back in with the line it sits on.
    """
    from . import models

    models._ensure_imports()
    left, top, right, bottom = fill_box
    outer_left, outer_top = max(0, left - margin), max(0, top - margin)
    outer_right, outer_bottom = min(image.width, right + margin), min(image.height, bottom + margin)
    region = models.np.asarray(
        image.convert("RGB").crop((outer_left, outer_top, outer_right, outer_bottom)),
        dtype=models.np.int16,
    )
    distance = models.np.max(
        models.np.abs(region - models.np.array(color, dtype=models.np.int16)), axis=2
    )
    ink = distance > int(ink_distance)
    inside = models.np.zeros(ink.shape, dtype=bool)
    inside[top - outer_top : bottom - outer_top, left - outer_left : right - outer_left] = True
    keep = models.np.zeros(ink.shape, dtype=bool)
    escaping = ink & ~inside
    if models.np.any(escaping):
        faint = (distance > int(faint_distance)).astype(models.np.uint8)
        _count, labels, _stats, _centroids = models.cv2.connectedComponentsWithStats(
            faint, connectivity=8
        )
        for label in models.np.unique(labels[escaping]):
            if label:
                keep |= labels == label
    return keep[
        top - outer_top : bottom - outer_top,
        left - outer_left : right - outer_left,
    ]


def _reference_artifact_cleanup(
    image: Image.Image,
    profiles: list[dict[str, Any]],
    padding: int,
    precomputed_candidates: list[dict[str, Any]] | None = None,
) -> tuple[Image.Image, int, dict[str, Any]]:
    candidates = precomputed_candidates if precomputed_candidates is not None else _find_reference_artifact_candidates(image, profiles)
    if not candidates:
        return image, 0, {"candidateCount": 0, "selectedIds": [], "reason": "No reference matches."}
    exclusions = [candidate for candidate in candidates if candidate.get("action") == "exclude"]
    removable = [
        candidate for candidate in candidates
        if candidate.get("action", "remove") == "remove" and not _box_is_excluded(candidate["box"], exclusions)
    ]
    if not removable:
        return image, 0, {
            "candidateCount": len(candidates),
            "selectedIds": [],
            "excludedMatches": len(exclusions),
            "reason": "All matches are exclusions or no removable references matched.",
        }
    direct = [
        candidate for candidate in removable
        if float(candidate["score"]) >= float(candidate.get("threshold", 1.0))
    ]
    decision = {
        "selectedIds": [],
        "decisions": [],
        "reason": "High-confidence local reference matches applied directly.",
    }
    requested = direct
    selected: list[dict[str, Any]] = []
    background_checks = []
    fill_colors: dict[str, tuple[int, int, int]] = {}
    for candidate in requested:
        safe, color, metrics = _uniform_artifact_background(image, candidate["box"])
        background_checks.append({"id": candidate["id"], "safe": safe, "color": list(color), **metrics})
        if safe:
            selected.append(candidate)
            fill_colors[candidate["id"]] = color
    decision["matchedIds"] = [candidate["id"] for candidate in requested]
    decision["selectedIds"] = [candidate["id"] for candidate in selected]
    decision["skippedUnsafeBackgroundIds"] = [candidate["id"] for candidate in requested if candidate not in selected]
    decision["backgroundChecks"] = background_checks
    decision["directReferenceMatches"] = [candidate["id"] for candidate in direct]
    decision["candidateCount"] = len(candidates)
    decision["excludedMatches"] = len(exclusions)
    decision["candidates"] = [
        {"id": candidate["id"], "profile": candidate["profile"], "action": candidate.get("action", "remove"), "score": candidate["score"], "threshold": candidate.get("threshold"), "box": candidate["box"]}
        for candidate in candidates
    ]
    if not selected:
        return image, 0, decision
    from . import models

    models._ensure_imports()
    source = image.convert("RGB")
    pixels = models.np.array(source)
    fill_padding = max(3, min(20, int(padding)))
    preserved = 0
    for candidate in selected:
        x1, y1, x2, y2 = candidate["box"]
        fill_box = (
            max(0, x1 - fill_padding),
            max(0, y1 - fill_padding),
            min(source.width, x2 + fill_padding),
            min(source.height, y2 + fill_padding),
        )
        left, top, right, bottom = fill_box
        if right <= left or bottom <= top:
            continue
        color = fill_colors[candidate["id"]]
        keep = _artifact_fill_keep_mask(source, fill_box, color)
        window = pixels[top:bottom, left:right]
        original = window.copy()
        window[...] = color
        if models.np.any(keep):
            window[keep] = original[keep]
            preserved += int(models.np.count_nonzero(keep))
    decision["cleanupMethod"] = "background_fill_keeping_crossing_ink"
    decision["preservedInkPixels"] = preserved
    return Image.fromarray(pixels), len(selected), decision


def _run_job(config: dict[str, Any]) -> None:
    files = config["files"]
    output_dir = config["output_dir"]
    margin = config["margin"]
    artifact_profiles = _load_artifact_profiles(config.get("examples_dir", ""))
    results: list[dict[str, Any]] = []
    archive_jobs: dict[str, dict[str, str]] = {}
    for item in files:
        archive_tmp = item.get("archiveTmp", "")
        archive_info = config.get("archive_map", {}).get(archive_tmp) if archive_tmp else None
        if not archive_info or archive_tmp in archive_jobs:
            continue
        source_archive = os.path.realpath(str(archive_info.get("archive_path") or ""))
        archive_name = os.path.splitext(os.path.basename(source_archive))[0]
        source_ext = os.path.splitext(source_archive)[1].lower()
        out_ext = ".cbz" if source_ext in {".rar", ".cbr"} else source_ext
        relative_parent = item.get("outputPrefix", "")
        if config.get("root_dir"):
            try:
                relative_parent = os.path.dirname(os.path.relpath(source_archive, config["root_dir"]))
                if relative_parent == "." or ".." in relative_parent.replace("\\", "/").split("/"):
                    relative_parent = ""
            except ValueError:
                relative_parent = ""
        work_dir = os.path.join(output_dir, "__auto_arch_tmp__", f"{len(archive_jobs):04d}_{archive_name}")
        if os.path.isdir(work_dir):
            shutil.rmtree(work_dir)
        shutil.copytree(archive_tmp, work_dir)
        archive_jobs[archive_tmp] = {
            "work_dir": work_dir,
            "output": os.path.join(output_dir, relative_parent, archive_name + out_ext),
            "extension": out_ext,
        }
    _log(f"Autonomous processing: {len(files)} files")
    _log(f"Output: {output_dir}")
    _log(f"Local page-number scan: bottom {round(config['bottom_scan_ratio'] * 100)}%")
    _log("Order: local page-number cleanup -> local artifact cleanup -> safe crop")
    if artifact_profiles:
        _log(f"Artifact profiles loaded: {len(artifact_profiles)}")

    folio_sequence = PageNumberSequence()
    from ._native_source import natural_key
    files = sorted(files, key=lambda item: natural_key(item["path"]))
    for index, item in enumerate(files, 1):
        with _job_lock:
            if _job["stop_requested"]:
                _set_job(running=False, phase="cancelled")
                _log("Cancelled")
                return
        _set_job(current=index, currentFile=item["name"], progress=round((index - 1) / max(1, len(files)) * 100), phase="processing")
        record: dict[str, Any] = {
            "source": item["path"],
            "output": "",
            "choice": "",
            "decision": "heuristic",
            "pageNumbersRemoved": 0,
            "artifactsRemoved": 0,
        }
        try:
            with Image.open(item["path"]) as opened:
                original = ImageOps.exif_transpose(opened).convert("RGB")
            cleaned = original
            reference_candidates = _find_reference_artifact_candidates(original, artifact_profiles) if artifact_profiles else []
            artifact_ignore_mask, artifact_crop_matches = _peripheral_artifact_ignore_mask(
                original,
                artifact_profiles,
            )
            if artifact_crop_matches:
                record["artifactCropMatches"] = artifact_crop_matches
            page_number_decision = detect_page_numbers_locally(
                original,
                config["bottom_scan_ratio"],
                config.get("root_dir", ""),
                minimum_page_number=folio_sequence.minimum(page_number_chapter(item["path"])),
            )
            folio_sequence.observe(page_number_chapter(item["path"]), page_number_decision)
            cleaned, page_numbers_removed, page_number_decision = _page_number_cleanup_from_decision(
                original,
                page_number_decision,
                config["method"],
                config["padding"],
                reference_candidates,
            )
            record["pageNumberDecision"] = page_number_decision
            record["pageNumbersRemoved"] = page_numbers_removed
            artifacts_removed = 0
            if artifact_profiles:
                cleaned, artifacts_removed, artifact_decision = _reference_artifact_cleanup(
                    cleaned,
                    artifact_profiles,
                    config["padding"],
                    reference_candidates,
                )
                record["artifactDecision"] = artifact_decision
            record["artifactsRemoved"] = artifacts_removed
            # Detect crop geometry only after page-number/artifact cleanup.
            # Otherwise a removed number still anchors the bottom content bound
            # and leaves an unnecessarily large lower margin.
            candidates, rejected_candidates = build_automatic_crop_candidates(
                cleaned,
                artifact_ignore_mask=artifact_ignore_mask,
            )
            record["cropAnalysis"] = "after_cleanup"
            if rejected_candidates:
                record["rejectedCandidates"] = rejected_candidates
            objective_blank_crop = next(
                (candidate for candidate in candidates if candidate.name == "blank_edges" and not candidate.ambiguous),
                None,
            )
            selected = objective_blank_crop or _heuristic_choice(candidates)
            if objective_blank_crop is not None:
                record.update({
                    "decision": "deterministic_blank_edges",
                    "confidence": 1.0,
                    "reason": "Removed independently detected uniform outer margins.",
                })
            archive_job = archive_jobs.get(item.get("archiveTmp", ""))
            if archive_job:
                output_path = os.path.realpath(os.path.join(archive_job["work_dir"], os.path.relpath(item["path"], item["archiveTmp"])))
            else:
                output_path = os.path.realpath(os.path.join(output_dir, *item["relPath"].split("/")))
            if not is_under_allowed_root(output_path, [output_dir]):
                raise ValueError("Unsafe output path")
            final = render_candidate(cleaned, selected, margin)
            _save_image(final, output_path)
            record.update({"output": archive_job["output"] if archive_job else output_path, "choice": selected.name, "crop": asdict(selected), "sourceSize": list(original.size), "outputSize": list(final.size)})
            with _job_lock:
                _job["processed"] += 1
            _log(
                f"[{index}/{len(files)}] {item['name']} -> {selected.name}"
                + (f"; page numbers removed: {page_numbers_removed}" if page_numbers_removed else "")
                + (f"; reference artifacts removed: {artifacts_removed}" if artifacts_removed else "")
            )
        except Exception as exc:
            record["error"] = str(exc)
            with _job_lock:
                _job["failed"] += 1
            _log(f"[ERR] {item['name']}: {exc}")
        results.append(record)
        with _job_lock:
            _job["results"] = results[-200:]

    for archive_job in archive_jobs.values():
        os.makedirs(os.path.dirname(archive_job["output"]), exist_ok=True)
        if os.path.isfile(archive_job["output"]):
            os.remove(archive_job["output"])
        args = ["a", "-y"]
        if archive_job["extension"] in {".zip", ".cbz"}:
            args.append("-tzip")
        packed = run_7z([*args, archive_job["output"], os.path.join(archive_job["work_dir"], ".")], timeout=300)
        if packed and packed.returncode == 0:
            shutil.rmtree(archive_job["work_dir"], ignore_errors=True)
            _log(f"[PACKED] {archive_job['output']}")
        else:
            _log(f"[ERR] Failed to pack archive: {archive_job['output']}")

    report_path = os.path.join(output_dir, "maic_autonomous_report.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "preservedMarginPx": margin,
                "pageNumberScanBottomPercent": round(config["bottom_scan_ratio"] * 100),
                "results": results,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
    _log(f"Report: {report_path}")
    _set_job(running=False, phase="done", current=len(files), progress=100, currentFile="", report=report_path)


def _run_job_guarded(config: dict[str, Any]) -> None:
    try:
        _run_job(config)
    except Exception as exc:
        _log(f"[FATAL] {exc}")
        _set_job(running=False, phase="error", currentFile="")


def create_autonomous_blueprint(archive_snapshot=lambda: {}) -> Blueprint:
    bp = Blueprint("autonomous", __name__)

    @bp.route("/api/artifact-profiles", methods=["GET"])
    def artifact_profiles_list():
        return jsonify({"ok": True, "profiles": _managed_artifact_profile_metadata()})

    @bp.route("/api/artifact-profiles", methods=["POST"])
    def artifact_profiles_create():
        data = request.get_json(silent=True) or {}
        source_path = str(data.get("source_path") or "")
        try:
            from .kcc_scan import _load_image_bytes

            source_bytes = _load_image_bytes(source_path, state.get("allowed_read_roots", []))
        except Exception:
            source_bytes = None
        if not source_bytes:
            return fail("Source image not found or access denied", code=EC.INVALID_PATH, status=400)
        action = str(data.get("action") or "remove").lower()
        if action not in {"remove", "exclude"}:
            return fail("Invalid artifact profile action", code=EC.INVALID_PAYLOAD, status=400)
        label = str(data.get("label") or "").strip()[:80]
        if not label:
            return fail("Profile name is required", code=EC.INVALID_PAYLOAD, status=400)
        try:
            threshold = max(0.70, min(0.99, float(data.get("threshold", 0.88))))
            raw_box = data.get("box")
            if not isinstance(raw_box, list) or len(raw_box) != 4:
                raise ValueError("box")
            raw_coordinates = [int(round(float(value))) for value in raw_box]
        except (TypeError, ValueError):
            return fail("Invalid profile coordinates", code=EC.INVALID_PAYLOAD, status=400)

        profile_id = str(data.get("profile_id") or "").lower()
        is_new = not profile_id
        if is_new:
            if len(_managed_artifact_profile_metadata()) >= 64:
                return fail("Artifact profile limit reached", code=EC.INVALID_PAYLOAD, status=400)
            profile_id = uuid.uuid4().hex
        profile_dir = _managed_profile_path(profile_id)
        if profile_dir is None:
            return fail("Invalid profile id", code=EC.INVALID_PAYLOAD, status=400)
        manifest_path = os.path.join(profile_dir, "manifest.json")
        manifest: dict[str, Any] = {}
        if not is_new:
            if not os.path.isfile(manifest_path):
                return fail("Artifact profile not found", code=EC.INVALID_PATH, status=404)
            try:
                with open(manifest_path, "r", encoding="utf-8") as handle:
                    loaded_manifest = json.load(handle)
                if isinstance(loaded_manifest, dict):
                    manifest = loaded_manifest
            except (OSError, ValueError, TypeError):
                return fail("Artifact profile is damaged", code=EC.INVALID_PAYLOAD, status=400)
            if str(manifest.get("action") or "remove") != action:
                return fail("Profile action does not match", code=EC.INVALID_PAYLOAD, status=400)

        try:
            with Image.open(io.BytesIO(source_bytes)) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
            x1 = max(0, min(image.width - 1, raw_coordinates[0]))
            y1 = max(0, min(image.height - 1, raw_coordinates[1]))
            x2 = max(x1 + 1, min(image.width, raw_coordinates[2]))
            y2 = max(y1 + 1, min(image.height, raw_coordinates[3]))
            if x2 - x1 < 4 or y2 - y1 < 4:
                return fail("Selected area is too small", code=EC.INVALID_PAYLOAD, status=400)
            if (x2 - x1) * (y2 - y1) > image.width * image.height * 0.50:
                return fail("Selected area is too large", code=EC.INVALID_PAYLOAD, status=400)
            references_dir = os.path.join(profile_dir, "references")
            existing_references = [] if not os.path.isdir(references_dir) else [
                name for name in os.listdir(references_dir) if os.path.splitext(name)[1].lower() in IMAGE_EXTS
            ]
            if len(existing_references) >= 8:
                return fail("Reference limit reached for this profile", code=EC.INVALID_PAYLOAD, status=400)
            os.makedirs(references_dir, exist_ok=True)
            reference_name = f"reference_{time.time_ns()}.png"
            image.crop((x1, y1, x2, y2)).save(os.path.join(references_dir, reference_name), format="PNG", optimize=True)
            now = time.strftime("%Y-%m-%dT%H:%M:%S")
            reference_meta = manifest.get("referenceMeta")
            if not isinstance(reference_meta, dict):
                reference_meta = {}
            reference_meta[reference_name] = {
                "sourceSize": [image.width, image.height],
                "normalizedBox": [
                    x1 / image.width,
                    y1 / image.height,
                    x2 / image.width,
                    y2 / image.height,
                ],
            }
            manifest.update({
                "id": profile_id,
                "label": label,
                "action": action,
                "threshold": threshold,
                "referenceMeta": reference_meta,
                "createdAt": str(manifest.get("createdAt") or now),
                "updatedAt": now,
            })
            _write_managed_profile_manifest(profile_dir, manifest)
        except Exception as exc:
            logger.exception("Failed to save artifact profile")
            return fail(f"Failed to save artifact profile: {exc}", code=EC.INVALID_PAYLOAD, status=400)
        profile = next((item for item in _managed_artifact_profile_metadata() if item["id"] == profile_id), None)
        return jsonify({"ok": True, "profile": profile})

    @bp.route("/api/artifact-profiles/<profile_id>", methods=["DELETE"])
    def artifact_profiles_delete(profile_id: str):
        profile_dir = _managed_profile_path(profile_id)
        root = os.path.realpath(ARTIFACT_PROFILE_DIR)
        if profile_dir is None or not os.path.isdir(profile_dir) or not is_under_allowed_root(profile_dir, [root]):
            return fail("Artifact profile not found", code=EC.INVALID_PATH, status=404)
        shutil.rmtree(profile_dir)
        return jsonify({"ok": True})

    @bp.route("/api/artifact-profiles/rescan", methods=["POST"])
    def artifact_profiles_rescan():
        data = request.get_json(silent=True) or {}
        raw_files = data.get("files")
        if not isinstance(raw_files, list):
            return fail("files are required", code=EC.INVALID_PAYLOAD, status=400)
        profile_id = str(data.get("profile_id") or "").strip().lower()
        profiles = _load_artifact_profiles("")
        if profile_id:
            profiles = [profile for profile in profiles if str(profile.get("id") or "").lower() == profile_id]
        if not profiles:
            return fail("Artifact profile not found", code=EC.INVALID_PATH, status=404)

        from .kcc_scan import _load_image_bytes

        matches = []
        failed = 0
        for raw_item in raw_files:
            item = raw_item if isinstance(raw_item, dict) else {"path": raw_item}
            source_path = str(item.get("path") or "")
            if not source_path:
                continue
            try:
                image_bytes = _load_image_bytes(source_path, state.get("allowed_read_roots", []))
                if not image_bytes:
                    failed += 1
                    continue
                with Image.open(io.BytesIO(image_bytes)) as opened:
                    image = ImageOps.exif_transpose(opened).convert("RGB")
                _ignore_mask, page_matches = _peripheral_artifact_ignore_mask(image, profiles)
                if page_matches:
                    matches.append({
                        "path": source_path,
                        "relPath": str(item.get("relPath") or os.path.basename(source_path)),
                        "matches": page_matches,
                    })
            except Exception:
                failed += 1
        return jsonify({
            "ok": True,
            "scanned": len(raw_files),
            "matchedCount": len(matches),
            "failed": failed,
            "matches": matches,
        })

    @bp.route("/api/page-number-examples", methods=["GET"])
    def page_number_examples_list():
        scope_path = str(request.args.get("scope_path") or "")
        if not scope_path:
            return fail("scope_path must be provided", code=EC.INVALID_PAYLOAD, status=400)
        return jsonify({"ok": True, **page_number_memory_metadata(scope_path)})

    @bp.route("/api/page-number-examples", methods=["POST"])
    def page_number_examples_create():
        data = request.get_json(silent=True) or {}
        source_path = str(data.get("source_path") or "")
        scope_path = str(data.get("scope_path") or "")
        action = str(data.get("action") or "").lower()
        raw_box = data.get("box")
        if not source_path or not scope_path or action not in {"number", "not_number"}:
            return fail("Invalid page-number feedback", code=EC.INVALID_PAYLOAD, status=400)
        if not isinstance(raw_box, list) or len(raw_box) != 4:
            return fail("Invalid selection coordinates", code=EC.INVALID_PAYLOAD, status=400)
        try:
            from .kcc_scan import _load_image_bytes

            image_bytes = _load_image_bytes(source_path, state.get("allowed_read_roots", []))
            if not image_bytes:
                return fail("Source image not found", code=EC.INVALID_PATH, status=404)
            # Keep the same coordinate space as serve-thumb and conversion.
            with Image.open(io.BytesIO(image_bytes)) as opened:
                image = opened.convert("RGB")
            box = [int(round(float(value))) for value in raw_box]
            saved = save_page_number_example(
                image,
                box,
                scope_path=scope_path,
                action=action,
                digits=str(data.get("digits") or ""),
                source_name=source_path,
            )
            return jsonify({"ok": True, "example": saved, **page_number_memory_metadata(scope_path)})
        except ValueError as exc:
            return fail(str(exc), code=EC.INVALID_PAYLOAD, status=400)
        except Exception as exc:
            logger.exception("Failed to save page-number example")
            return fail(f"Failed to save example: {exc}", code=EC.INVALID_PAYLOAD, status=400)

    @bp.route("/api/page-number-examples/<example_id>", methods=["DELETE"])
    def page_number_examples_delete(example_id: str):
        data = request.get_json(silent=True) or {}
        scope_path = str(data.get("scope_path") or request.args.get("scope_path") or "")
        if not scope_path:
            return fail("scope_path must be provided", code=EC.INVALID_PAYLOAD, status=400)
        if not delete_page_number_example(scope_path, example_id):
            return fail("Page-number example not found", code=EC.INVALID_PATH, status=404)
        return jsonify({"ok": True, **page_number_memory_metadata(scope_path)})

    @bp.route("/api/page-number-examples/rescan", methods=["POST"])
    def page_number_examples_rescan():
        data = request.get_json(silent=True) or {}
        scope_path = str(data.get("scope_path") or "")
        raw_files = data.get("files")
        if not scope_path or not isinstance(raw_files, list):
            return fail("scope_path and files are required", code=EC.INVALID_PAYLOAD, status=400)
        from .kcc_scan import _load_image_bytes

        sequence = PageNumberSequence(data.get("chapter_minimums"))
        matches = []
        failed = 0
        # This is an explicit preview action. A bounded scan keeps a malformed
        # request from monopolizing the UI worker.
        for raw_item in raw_files[:500]:
            item = raw_item if isinstance(raw_item, dict) else {"path": raw_item}
            source_path = str(item.get("path") or "")
            if not source_path:
                continue
            try:
                image_bytes = _load_image_bytes(source_path, state.get("allowed_read_roots", []))
                if not image_bytes:
                    failed += 1
                    continue
                with Image.open(io.BytesIO(image_bytes)) as opened:
                    image = ImageOps.exif_transpose(opened).convert("RGB")
                chapter = str(item.get("chapter_key") if "chapter_key" in item
                              else page_number_chapter(item.get("relPath") or source_path))
                decision = detect_page_numbers_locally(
                    image, scope_path=scope_path, minimum_page_number=sequence.minimum(chapter)
                )
                sequence.observe(chapter, decision)
                if decision.get("has_page_number"):
                    matches.append({
                        "path": source_path,
                        "relPath": str(item.get("relPath") or os.path.basename(source_path)),
                        "boxes": decision.get("boxes") or [],
                        "recognizedDigits": decision.get("recognizedDigits") or {},
                        "confidence": float(decision.get("confidence") or 0.0),
                    })
            except Exception:
                failed += 1
        return jsonify({
            "ok": True,
            "scanned": min(len(raw_files), 500),
            "matchedCount": len(matches),
            "failed": failed,
            "matches": matches,
            "chapterMinimums": sequence.minimums,
            **page_number_memory_metadata(scope_path),
        })

    @bp.route("/api/autonomous/status", methods=["GET"])
    def api_autonomous_status():
        return jsonify(autonomous_status())

    @bp.route("/api/autonomous/stop", methods=["POST"])
    def api_autonomous_stop():
        with _job_lock:
            _job["stop_requested"] = True
        return jsonify({"ok": True})

    @bp.route("/api/autonomous/start", methods=["POST"])
    def api_autonomous_start():
        data = request.get_json(silent=True) or {}
        with _job_lock:
            if _job["running"]:
                return fail("Autonomous processing is already running", code=EC.AUTONOMOUS_BUSY, status=409)
        root_dir = os.path.realpath(str(data.get("root_dir") or "")) if data.get("root_dir") else ""
        source_roots = []
        for value in data.get("source_roots", []) if isinstance(data.get("source_roots"), list) else []:
            candidate_root = os.path.realpath(str(value or ""))
            if candidate_root and os.path.exists(candidate_root) and is_under_allowed_root(candidate_root, state.get("allowed_read_roots", [])):
                source_roots.append(candidate_root)
        files = _normalized_files(data.get("files"), root_dir)
        if not files:
            return fail("No allowed image files", code=EC.INVALID_PAYLOAD, status=400)
        output_raw = str(data.get("output_dir") or "").strip()
        if not output_raw:
            return fail("Output directory is required", code=EC.INVALID_PATH, status=400)
        output_dir = os.path.realpath(output_raw)
        if root_dir and any(not item.get("archiveTmp") and not is_under_allowed_root(item["path"], [root_dir]) for item in files):
            return fail("Source root does not contain all input images", code=EC.INVALID_PATH, status=400)
        allowed_writes = list(state.get("allowed_write_roots", [])) + [os.path.dirname(files[0]["path"])]
        if root_dir:
            allowed_writes.append(os.path.dirname(root_dir))
        allowed_writes.extend(os.path.dirname(source_root) for source_root in source_roots)
        if not is_under_allowed_root(output_dir, allowed_writes):
            return fail("Output access denied", code=EC.INVALID_PATH, status=403)
        if root_dir and is_under_allowed_root(output_dir, [root_dir]):
            return fail("Output directory cannot be inside the source directory", code=EC.INVALID_PATH, status=400)
        for source_root in source_roots:
            output_inside_folder = os.path.isdir(source_root) and is_under_allowed_root(output_dir, [source_root])
            if output_inside_folder or is_under_allowed_root(source_root, [output_dir]):
                return fail("Output directory must be separate from all sources", code=EC.INVALID_PATH, status=400)
        for item in files:
            if not item.get("archiveTmp"):
                source_dir = os.path.dirname(item["path"])
                if is_under_allowed_root(output_dir, [source_dir]) or is_under_allowed_root(item["path"], [output_dir]):
                    return fail("Output directory must be separate from source images", code=EC.INVALID_PATH, status=400)
        examples_dir = os.path.realpath(str(data.get("examples_dir") or "")) if data.get("examples_dir") else ""
        if examples_dir and not is_under_allowed_root(examples_dir, state.get("allowed_read_roots", [])):
            return fail("Examples directory access denied", code=EC.INVALID_PATH, status=403)

        try:
            config = {
                "files": files,
                "root_dir": root_dir,
                "output_dir": output_dir,
                "margin": max(0, min(100, int(data.get("margin", data.get("border", 5))))),
                "padding": max(0, min(50, int(data.get("padding", 2)))),
                "bottom_scan_ratio": max(
                    0.05,
                    min(0.50, float(data.get("artifact_scan_bottom_percent", 20)) / 100.0),
                ),
                "method": str(data.get("method") or "lama"),
                "examples_dir": examples_dir,
                "archive_map": archive_snapshot(),
            }
        except (TypeError, ValueError):
            return fail("Invalid autonomous settings", code=EC.INVALID_PAYLOAD, status=400)
        _set_job(running=True, stop_requested=False, phase="starting", current=0, total=len(files), currentFile="", progress=0, log=[], processed=0, failed=0, fallbacks=0, results=[], output_dir=output_dir)
        threading.Thread(target=_run_job_guarded, args=(config,), daemon=True, name="maic-autonomous").start()
        return jsonify({"ok": True, "total": len(files)})

    return bp
