"""A source folder to sections and a table of contents.

This is the half of the native pipeline that no container knows about.  It
walks the source with :mod:`maic._native_source`, applies every page transform
maic offers -- crop, hand split, edit ops, extra margins, page-number cleanup,
device sizing, upscaling -- encodes the result, and pairs facing pages into
sections.

What comes out is the contract both serializers consume:

``page_groups``
    list of sections in reading order.  Group 0 is the cover and holds exactly
    one page.  Later groups hold one page, or two for a facing spread.  Each
    page is ``{"data": bytes, "width": int, "height": int, "rel": str,
    "path": str}``, plus ``thumb_data``/``thumb_size`` when previews were
    asked for.
``toc_entries``
    ``(page index, title)`` pairs, counting pages of the finished book with
    the cover as page 0 -- the numbering the KFX page list labels 1..N.  A
    chapter can open on the far half of a facing pair, so an entry names the
    page it opens on and not the section that holds it.

The page-blob helpers live here too rather than in the KFX module, so the
dependency runs one way only: a serializer imports this, never the reverse.
"""

import io
import os


_THUMB_BOX = (512, 512)
_THUMB_QUALITY = 30
# The cover's preview is the library tile and the standby screen, and there is
# exactly one of it, so it is not worth compressing at all.
_THUMB_COVER_QUALITY = 100


def _decode_image_size(data):
    from PIL import Image
    with Image.open(io.BytesIO(data)) as img:
        return img.size


def _thumbnail_from_image(img, aspect=None, pad_rgb=(255, 255, 255), quality=None):
    """Thumbnail for the Page Flip strip, from an image already in hand.

    The strip letterboxes a thumbnail into its slot -- device-confirmed -- so a
    thumbnail keeps the art's own shape and needs no padding.  *aspect* pads it
    to a given shape for callers that want one anyway; nothing does.
    """
    from PIL import Image
    if img.mode not in {"RGB", "L"}:
        img = img.convert("RGB")
    img = img.copy()
    img.thumbnail(_THUMB_BOX, Image.LANCZOS)
    if aspect:
        w, h = img.size
        box = (max(w, int(round(h * aspect))), max(h, int(round(w / aspect))))
        if box != (w, h):
            canvas = Image.new("RGB", box, pad_rgb)
            canvas.paste(img.convert("RGB"), ((box[0] - w) // 2, (box[1] - h) // 2))
            img = canvas
    w, h = img.size
    out = io.BytesIO()
    img.save(out, "JPEG", quality=quality or _THUMB_QUALITY, optimize=True)
    return out.getvalue(), w, h


def _make_thumbnail(data, aspect=None, pad_rgb=(255, 255, 255), quality=None):
    """Thumbnail for a page that is only available as encoded bytes."""
    from PIL import Image
    with Image.open(io.BytesIO(data)) as img:
        return _thumbnail_from_image(img, aspect, pad_rgb, quality)


def _thumb_mode(value):
    """Which preview a page gets: "full", "reuse" or "off".

    ``full`` is Amazon's own arrangement -- a second, downscaled copy of every
    page, which costs 8-17% of a book.  ``reuse`` points ``$214`` at the page's
    own entity so no second blob is stored, and ``off`` leaves the page with no
    preview at all.  The parameter used to be a bool, and both spellings still
    name the two ends of the range.
    """
    if value is True:
        return "full"
    if value is False or value is None:
        return "off"
    mode = str(value).strip().lower()
    return mode if mode in {"full", "reuse", "off"} else "full"


def _sniff_format(data):
    """The container format, or None when KFX cannot carry it."""
    if data[:2] == b"\xff\xd8":
        return "jpg"
    if data[:4] == b"\x89PNG":
        return "png"
    if data[:3] == b"GIF":
        return "gif"
    return None


def _image_format(data):
    return _sniff_format(data) or "jpg"


def _read_page_bytes(path):
    """Read a normal image or a virtual ZIP/CBZ member from the source walk."""
    from ._native_source import ARCHIVE_SEP

    if ARCHIVE_SEP not in path:
        with open(path, "rb") as source:
            return source.read()

    archive_path, internal = path.split(ARCHIVE_SEP, 1)
    import zipfile

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            return archive.read(internal)
    except (KeyError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ValueError(
            "cannot read %s from archived chapter %s: %s"
            % (internal, archive_path, exc)
        ) from exc


def _custom_crop_box(bounds, size):
    """PIL box for a sidecar custom crop, or None when it no longer applies.

    The sidecar stores inclusive edges together with the image size they were
    picked on; a mismatch means the page has changed since, and cropping to a
    stale box would cut the art.
    """
    width, height = size
    try:
        if int(bounds.get("width", 0)) != width or int(bounds.get("height", 0)) != height:
            return None
        top = max(0, int(bounds.get("top", 0)))
        bottom = min(height - 1, int(bounds.get("bottom", height - 1)))
        left = max(0, int(bounds.get("left", 0)))
        right = min(width - 1, int(bounds.get("right", width - 1)))
    except (TypeError, ValueError, AttributeError):
        return None
    if top >= bottom or left >= right:
        return None
    return (left, top, right + 1, bottom + 1)


def _margin_rgb(value):
    """RGB for a sidecar margin colour, accepting #rgb as well as #rrggbb."""
    text = str(value or "#ffffff").strip()
    if text.startswith("#") and len(text) == 4:
        text = "#" + text[1] * 2 + text[2] * 2 + text[3] * 2
    try:
        return int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16)
    except (ValueError, IndexError):
        return 255, 255, 255


def _apply_edit_ops(image, ops, log_fn=None):
    """Paint the user's rectangles and brush strokes onto the page.

    Their coordinates are in the untouched image's space, which is why this
    runs before anything trims or resizes the page -- the same reason the KCC
    path applies edit-ops to the source files before every other pass.
    """
    from PIL import ImageDraw

    _log = log_fn or (lambda msg: None)
    draw = ImageDraw.Draw(image)
    painted = 0
    for op in ops or ():
        if not isinstance(op, dict):
            continue
        color = op.get("color", "#fff")
        kind = str(op.get("type", "") or "").strip().lower()
        try:
            if kind == "rect":
                x, y = int(op.get("x", 0)), int(op.get("y", 0))
                w, h = int(op.get("w", 0)), int(op.get("h", 0))
                draw.rectangle([x, y, x + w, y + h], fill=color)
                painted += 1
            elif kind == "brush":
                points = op.get("points") or []
                size = int(op.get("size", 20))
                radius = size // 2
                if len(points) == 1:
                    cx, cy = int(points[0][0]), int(points[0][1])
                    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)
                    painted += 1
                elif len(points) > 1:
                    for first, second in zip(points, points[1:]):
                        draw.line(
                            [(int(first[0]), int(first[1])), (int(second[0]), int(second[1]))],
                            fill=color, width=size,
                        )
                    # Round caps, so a stroke that changes direction has no notch.
                    for point in points:
                        cx, cy = int(point[0]), int(point[1])
                        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)
                    painted += 1
        except (TypeError, ValueError, IndexError) as exc:
            _log("EDIT: skipped a %s op (%s)" % (kind or "?", exc))
    return painted


def _apply_extra_margin(image, margins):
    """Add the user's margin around an already-trimmed page.

    Order matters: the margin goes on after cropping, or the crop would simply
    take it off again.  The KCC path arranges the same thing the long way
    round, by marking the page NoCrop once the margin is on.
    """
    from PIL import Image

    try:
        top = max(0, int(margins.get("top", 0) or 0))
        bottom = max(0, int(margins.get("bottom", 0) or 0))
        left = max(0, int(margins.get("left", 0) or 0))
        right = max(0, int(margins.get("right", 0) or 0))
    except (TypeError, ValueError, AttributeError):
        return image, False
    if not (top or bottom or left or right):
        return image, False

    width, height = image.size
    canvas = Image.new(
        "RGB", (width + left + right, height + top + bottom), _margin_rgb(margins.get("color")))
    canvas.paste(image, (left, top))
    return canvas, True


def _encoded_page(image, rel, path, quality, fmt="jpg", mozjpeg=False, log_fn=None):
    from ._image_pipeline import encode_page

    data = encode_page(image, fmt=fmt, quality=quality, mozjpeg=mozjpeg, log_fn=log_fn)
    return {
        "data": data, "width": image.size[0], "height": image.size[1],
        "rel": rel, "path": path,
    }


def _pages_from_file(
    path,
    rel,
    *,
    canvas=None,
    resize=False,
    no_padding=False,
    righttoleft=True,
    quality=85,
    borders_color="none",
    split_spreads=True,
    rotate_spreads=True,
    force_spread_preview=False,
    spread_preview_mode=None,
    upscale=True,
    stretch=False,
    grayscale=False,
    page_format="jpg",
    mozjpeg=False,
    crop=False,
    margin_pct=0.0,
    watermarks=False,
    custom_crop=None,
    custom_split=None,
    cleanup=None,
    artifact_cleanup=None,
    artifact_profiles=None,
    edit_ops=None,
    extra_margin=None,
    restore=None,
    scan_cleanup=None,
    build_previews=True,
    log_fn=None,
):
    """One source image -> the one or two pages that make up its section.

    A facing spread comes back as two pages, reading half first, which is the
    shape ``build_native_kfx_book`` reads as a spread.  This is the work KCC
    does in ``ComicPage.splitCheck``/``resizeImage``; the decisions themselves
    live in :mod:`maic._image_pipeline` so both paths share them.

    Everything happens on the whole page before it is cut, in the order the
    KCC path applies to the source files in place, because each step depends on
    the one before it: edit-ops first (their coordinates are in the untouched
    image), then safe watermark cleanup and page-number cleanup (either can
    otherwise anchor the margin), then the crop (this is what makes a page
    fill the screen), then any requested extra margin, optional 1x scan
    cleanup, model upscaling, and the final resize.

    An image that needs nothing keeps its original bytes -- re-encoding a page
    that is already a fine JPEG only loses detail.

    *build_previews* is the Page Flip strip, and only the KFX serializer
    stores one; a serializer that writes none can turn it off and skip a
    512px resize and a re-encode on every page.
    """
    from ._image_pipeline import (
        SPREAD_PREVIEW_DEEP_BLACK_THRESHOLD,
        _resize_method, cropped_page_background, custom_split_plan, detect_fill, has_gradient_background, match_split_join,
        pad_to_even, resize_to_device, rotate_page, save_jpeg, split_at,
        split_spread, spread_plan, spread_preview_edge_metrics,
        spread_preview_likely,
    )

    _log = log_fn or (lambda msg: None)
    data = _read_page_bytes(path)

    size = _decode_image_size(data)
    # KFX carries JPEG, PNG and GIF; anything else -- WebP above all, which is
    # what most scanlation sources ship -- has to be re-encoded or the device
    # gets a blob it cannot draw.
    transcode = _sniff_format(data) != str(page_format).lower()
    plan = spread_plan(size, canvas, rotate_spreads) if (canvas and split_spreads) else "single"
    rescale = bool(resize and canvas)
    # Decided from the header, before anything is decoded: a page that already
    # reaches the render height has nothing to gain from the model and stays
    # the file it was.
    restore_kind = restore.model_for(size) if restore is not None else None
    cleanup_kind = scan_cleanup.model_for(data) if scan_cleanup is not None else None

    if (plan == "single" and not rescale and not transcode and not crop and not cleanup
            and not artifact_cleanup
            and not custom_crop and not custom_split and not edit_ops and not extra_margin
            and not grayscale and not restore_kind and not cleanup_kind):
        return [{
            "data": data, "width": size[0], "height": size[1], "rel": rel, "path": path,
        }]

    from PIL import Image

    with Image.open(io.BytesIO(data)) as opened:
        image = opened.convert("RGB")

    touched = False
    background_hint = None
    background_source = None
    if edit_ops:
        painted = _apply_edit_ops(image, edit_ops, log_fn=_log)
        if painted:
            touched = True
            _log("EDIT: %d ops painted on %s" % (painted, rel))

    if artifact_cleanup:
        from .autonomous import (
            _peripheral_artifact_ignore_mask,
            _reference_artifact_cleanup,
        )

        try:
            profiles = artifact_cleanup.get("profiles") or []
            _ignore_mask, candidates = _peripheral_artifact_ignore_mask(image, profiles)
            cleaned, removed, _ = _reference_artifact_cleanup(
                image,
                profiles,
                max(0, min(100, int(artifact_cleanup.get("padding") or 0))),
                precomputed_candidates=candidates,
            )
        except Exception as exc:
            _log("WATERMARK: failed on %s (%s)" % (rel, exc))
        else:
            if removed:
                image = cleaned
                size = image.size
                touched = True
                _log("WATERMARK: removed %d safe match(es) from %s" % (removed, rel))

    if cleanup:
        from .autonomous import apply_maic_page_number_cleanup

        try:
            cleaned, removed, _ = apply_maic_page_number_cleanup(
                image,
                artifact_profiles=cleanup.get("profiles"),
                method=str(cleanup.get("method") or "lama"),
                padding=max(0, min(100, int(cleanup.get("padding") or 0))),
                scope_path=str(cleanup.get("scope_path") or ""),
                minimum_page_number=cleanup.get("minimum_page_number", 1),
                sequence=cleanup.get("sequence"),
                chapter_key=cleanup.get("chapter_key", ""),
            )
        except Exception as exc:
            _log("NUMBERS: failed on %s (%s)" % (rel, exc))
        else:
            if removed:
                image = cleaned
                size = image.size
                touched = True

    if custom_crop:
        # The user's own crop box, in the coordinates of the untouched image --
        # which is why these pages are kept out of the automatic crop.  The
        # stored size is checked first: if the file changed under the sidecar,
        # the box means nothing any more.
        box = _custom_crop_box(custom_crop, image.size)
        if box is None:
            _log("CROP: custom crop ignored for %s (image is %dx%d now)"
                 % (rel, image.size[0], image.size[1]))
        else:
            cropped = image.crop(box)
            background_hint = cropped_page_background(image, cropped)
            if background_hint is not None or has_gradient_background(image):
                background_source = image.copy()
                background_source.info["maic_crop_reference_box"] = box
            image = cropped
            size = image.size
            touched = True
            if canvas and split_spreads:
                plan = spread_plan(size, canvas, rotate_spreads)
    elif crop:
        from .autonomous import apply_maic_crop

        try:
            cropped, _, applied = apply_maic_crop(
                image,
                preserved_margin_percent=margin_pct,
                target_size=canvas if rescale and plan == "single" else None,
                artifact_profiles=artifact_profiles,
            )
        except Exception as exc:
            _log("CROP: failed on %s (%s)" % (rel, exc))
        else:
            if applied:
                image = cropped
                # Cutting is decided on the cropped page: trimming a wide scan's
                # borders changes its ratio, and with it whether it is a spread.
                size = image.size
                touched = True
                if canvas and split_spreads:
                    plan = spread_plan(size, canvas, rotate_spreads)

    if extra_margin:
        image, added = _apply_extra_margin(image, extra_margin)
        if added:
            # The user's margin colour also defines any further canvas
            # extension, even when the added strip is too thin to detect.
            margin_color = _margin_rgb(extra_margin.get("color"))
            if background_hint is None or max(abs(a - b) for a, b in zip(background_hint, margin_color)) > 8:
                background_source = None
            background_hint = margin_color
            _log("MARGIN: %s %dx%d -> %dx%d"
                 % (rel, size[0], size[1], image.size[0], image.size[1]))
            size = image.size
            touched = True
            # A wide margin changes the page's proportions, and with them
            # whether it still reads as a facing spread.
            if canvas and split_spreads:
                plan = spread_plan(size, canvas, rotate_spreads)

    if cleanup_kind:
        # Keep the established Exact pipeline order: crop first, restore JPEG
        # artifacts at 1x second, then let the selected upscaler run below.
        cleaned = scan_cleanup.apply(image, cleanup_kind)
        if cleaned is not image:
            image = cleaned
            size = image.size
            touched = True
            _log("SCAN CLEANUP: %s input quality %s -> %s" % (
                rel, scan_cleanup.quality_for(cleanup_kind) or "?", cleanup_kind
            ))

    if restore_kind:
        # Last, and on purpose: the model enlarges the page, while edit-ops and
        # the sidecar's crop boxes are in the coordinates of the file the user
        # was looking at.  Running it here keeps those valid and still leaves
        # the resize below to bring the result to the canvas.
        restored = restore.apply(image, restore_kind)
        if restored is not image:
            image = restored
            size = image.size
            touched = True
            _log("UPSCALE: %s %s -> %dx%d" % (rel, restore_kind.split("_")[1], size[0], size[1]))
            if canvas and split_spreads:
                plan = spread_plan(size, canvas, rotate_spreads)

    if plan == "single" and not rescale and not transcode and not touched:
        # Nothing found anything to do, so the page is what it was.
        return [{
            "data": data, "width": size[0], "height": size[1], "rel": rel, "path": path,
        }]

    if grayscale and image.mode != "L":
        # KCC converts colour pages to grey before it resizes them; the e-ink
        # screen shows grey either way, and the file is a third smaller.
        image = image.convert("L")
        touched = True

    fill = detect_fill(image, borders_color) if (rescale and not no_padding) else "white"

    # Explicit mode supersedes the original boolean, while a direct caller
    # that still supplies only that boolean keeps exactly the old behaviour.
    preview_mode = spread_preview_mode
    if preview_mode is None:
        preview_mode = 2 if force_spread_preview else 0
    elif isinstance(preview_mode, str):
        preview_mode = {"off": 0, "auto": 1, "always": 2}.get(
            preview_mode.strip().lower(), preview_mode
        )
    try:
        preview_mode = max(0, min(2, int(preview_mode)))
    except (TypeError, ValueError):
        preview_mode = 2 if force_spread_preview else 0

    def _prepare_spread_join(source, axis, position):
        if preview_mode == 0:
            return source
        metrics = spread_preview_edge_metrics(source, axis, position)
        likely = spread_preview_likely(source, axis, position, metrics=metrics)
        signal = "ink %.1f%%, solid %.1f%%, continuity %.1f%%, deep black %.1f%%" % (
            metrics["joint_ink"] * 100.0, metrics["solid_ink"] * 100.0,
            metrics["continuity"] * 100.0, metrics["deep_black"] * 100.0
        )
        if preview_mode == 1 and likely:
            _log("SPREAD PREVIEW: %s already likely (%s); unchanged" % (rel, signal))
            return source
        # Berserk 10's device probe accepted 2/4 px on a mostly black join,
        # but rejected 1/16 px. Use the smallest confirmed band in Auto.
        band = 2 if (
            preview_mode == 1 and
            metrics["deep_black"] >= SPREAD_PREVIEW_DEEP_BLACK_THRESHOLD
        ) else 1
        source = match_split_join(source, axis, position, band=band)
        reason = "auto correction" if preview_mode == 1 else "always"
        _log("SPREAD PREVIEW: %s matched %d px at %s=%d (%s; %s)"
             % (rel, band, axis, position, reason, signal))
        return source

    # The user's own cut wins over the automatic one: they placed it because
    # the middle was the wrong place.
    manual = custom_split_plan(size, canvas, custom_split) if (canvas and custom_split) else None
    if manual is not None:
        axis, position = manual
        image = _prepare_spread_join(image, axis, position)
        parts = split_at(image, axis, position, righttoleft=righttoleft)
        plan = "split"
        _log("SPREAD: %s cut by hand at %s=%d -> %dx%d + %dx%d"
             % (rel, axis, position, parts[0].size[0], parts[0].size[1],
                parts[1].size[0], parts[1].size[1]))
    elif plan == "split":
        # Bring the spread to its final height before cutting it.  Resampling
        # each half on its own leaves the edge at the cut interpolated against
        # nothing, and the two halves then meet with a step the art never had;
        # lifting first keeps the sampling continuous across the fold.  Nothing
        # is resampled twice by it: a half is sized by its height alone, and
        # the lift has already put it at exactly that height, whether or not it
        # comes out wider than the canvas.
        whole = image
        if rescale and canvas and size[1] != canvas[1]:
            whole = image.resize(
                (max(2, int(round(size[0] * canvas[1] / float(size[1])))), canvas[1]),
                _resize_method(image, canvas),
            )
        whole = pad_to_even(whole)
        axis = "x" if whole.width > whole.height else "y"
        position = (whole.width if axis == "x" else whole.height) // 2
        whole = _prepare_spread_join(whole, axis, position)
        parts = split_spread(whole, righttoleft=righttoleft)
        _log("SPREAD: %s split %dx%d -> 2 x %dx%d"
             % (rel, size[0], size[1], parts[0].size[0], parts[0].size[1]))
    elif plan == "rotate":
        parts = [rotate_page(image)]
        _log("SPREAD: %s rotated %dx%d (too wide to bisect)" % (rel, size[0], size[1]))
    else:
        parts = [image]

    # The Page Flip preview is built from the page before it is padded out to
    # the canvas, so the strip shows art edge to edge instead of the white the
    # padding adds.  It is cut here, off the art the model and the resize have
    # just finished with, rather than stashed full size for the generator to
    # re-encode: that cost a JPEG generation per page and held the book twice.
    unpadded = [None] * len(parts)
    if rescale:
        sized = []
        for index, part in enumerate(parts):
            fitted = resize_to_device(
                part, canvas,
                spread_half=(plan == "split"),
                no_padding=no_padding,
                fill=fill,
                edge_padding=str(borders_color or "none").strip().lower() not in {"white", "black"},
                background_hint=background_hint if plan == "single" else None,
                background_source=background_source if plan == "single" else None,
                upscale=upscale,
                stretch=stretch,
            )
            if build_previews and fitted.size != part.size and not no_padding and plan != "split":
                unpadded[index] = _thumbnail_from_image(part)
            sized.append(fitted)
        parts = sized
    elif transcode:
        _log("PAGE: re-encoded %s as JPEG" % rel)

    pages = [
        _encoded_page(part, rel, path, quality, fmt=page_format, mozjpeg=mozjpeg, log_fn=_log)
        for part in parts
    ]
    for page, preview in zip(pages, unpadded):
        if preview is not None:
            page["thumb_data"], width, height = preview
            page["thumb_size"] = (width, height)
    return pages


def pair_facing_pages(page_groups, toc_entries=(), log_fn=None):
    """Merge adjacent portrait pages into facing pairs, and re-key the TOC.

    The device draws a section holding two pages side by side, which is what
    fills a landscape screen instead of centring one page in it.  The KPR path
    reaches that by merging finished sections after the fact; here the pairing
    is decided while the groups are still lists, because the native builder
    already draws a two-page group as a facing spread -- the same branch a
    bisected spread goes through.

    What is left alone:

    * the cover, which opens the book on its own;
    * a group that already holds two pages, being a bisected spread;
    * a landscape page, which fills a landscape screen by itself;
    * one page of a run whose length is odd.

    Which page that is decides every pair around it, so it is not simply the
    last one.  A bisected spread is the source's own record of where a printed
    spread falls: the pages running into one have to pair the way the paper
    paired them, or the whole stretch before it reads a page out of step.  So a
    run that ends against a spread is laid out from that end backwards, and the
    odd page falls at the front of the run instead.

    That is the whole of it.  A chapter opening used to claim a fresh pair of
    its own where the parity allowed, which cut the run at the break and left
    the page before it alone on a screen; the spreads the source itself records
    are the only thing worth keeping in step with, and everything else pairs as
    it falls.

    Returns the new groups and the TOC unchanged: pairing regroups pages
    without reordering or losing any, so a page keeps the number it had.
    """
    log = log_fn or (lambda msg: None)
    if len(page_groups) < 3:
        return page_groups, list(toc_entries or ())

    def pairable(group):
        return len(group) == 1 and int(group[0]["width"]) < int(group[0]["height"])

    # The book as units: a group that cannot pair stands alone, and each stretch
    # between two of those is a run to be paired.
    units, current = [], []
    for index, group in enumerate(page_groups):
        if index == 0 or not pairable(group):
            if current:
                units.append(("run", current))
                current = []
            units.append(("alone", [index]))
            continue
        current.append(index)
    if current:
        units.append(("run", current))

    def _sections(run, flush):
        """One run of pairable groups -> the sections it becomes."""
        sections, block, trailing = [], list(run), None
        if len(block) % 2:
            if flush:
                # A spread closes this run, so the pages have to reach it in
                # step and the odd one goes to the front.
                sections.append([block[0]])
                block = block[1:]
            else:
                # Nothing to keep step with: the blank falls at the end, which
                # is where the paper puts it.
                trailing = block[-1]
                block = block[:-1]
        sections.extend([left, right] for left, right
                        in zip(block[0::2], block[1::2]))
        if trailing is not None:
            sections.append([trailing])
        return sections

    out = []
    for position, (kind, indices) in enumerate(units):
        if kind == "alone":
            out.append(page_groups[indices[0]])
            continue
        following = units[position + 1] if position + 1 < len(units) else None
        # Only a bisected spread fixes the parity.  A landscape page takes a
        # whole screen of its own whatever the pages around it do, so nothing
        # about the paper survives it to be kept in step with.
        flush = bool(following and following[0] == "alone"
                     and len(page_groups[following[1][0]]) == 2)
        for section in _sections(indices, flush):
            out.append([page for index in section for page in page_groups[index]])

    paired = sum(1 for group in out if len(group) == 2)
    log("FACING: %d sections for %d pages (%d hold a facing pair)"
        % (len(out), sum(len(g) for g in out), paired))
    return out, list(toc_entries or ())


def page_groups_from_dir(
    source_dir,
    *,
    excluded=(),
    bookmarks=(),
    comicinfo_bookmarks=(),
    canvas=None,
    resize=False,
    no_padding=False,
    righttoleft=True,
    split_spreads=True,
    rotate_spreads=True,
    force_spread_preview=False,
    spread_preview_mode=None,
    upscale=True,
    stretch=False,
    grayscale=False,
    page_format="jpg",
    mozjpeg=False,
    quality=85,
    borders_color="none",
    crop=False,
    margin_pct=0.0,
    watermarks=False,
    watermark_matches=None,
    nocrop=(),
    custom_crops=None,
    custom_splits=None,
    edit_ops=None,
    extra_margin=None,
    page_numbers=False,
    cleanup_method="lama",
    cleanup_padding=0,
    page_number_scope="",
    manga_upscale=0,
    scan_cleanup=False,
    facing_pages=False,
    build_previews=True,
    resize_cover=False,
    progress_fn=None,
    stop_requested_fn=None,
    log_fn=None,
):
    """A folder of source images -> page groups and a table of contents.

    This is the native counterpart of :func:`page_groups_from_epub`, and the
    point where KCC drops out of the path: the order, the cover, the chapter
    boundaries and the TOC all come from :mod:`maic._native_source` instead of
    being read back out of an EPUB KCC wrote.

    *canvas* is the device screen, e.g. ``(1272, 1696)``.  It is what tells a
    facing spread from a merely wide page, so without it nothing is split.
    *resize* additionally sizes every page to that canvas the way KCC does.
    That one is off by default: the generator emits a leaf style per image, so
    a page that is smaller than the screen still renders at its own
    proportions, and upscaling it would only add bytes.

    *upscale* and *stretch* are the UI's Stretch/Upscale lever, and mean what
    they mean in KCC: without *upscale* a page already smaller than the screen
    is left at its own size, and *stretch* fills the canvas without keeping the
    page's proportions.

    *spread_preview_mode* selects ``0``/``off``, ``1``/``auto`` or
    ``2``/``always``. Auto matches the single pixel on both sides only when
    the cut lacks the ink and continuity signals seen on known Kindle
    positives. *force_spread_preview* is retained as the legacy off/always
    switch for direct callers that omit the new mode. Ordinary portrait pages
    paired later by *facing_pages* never pass through this operation.

    *nocrop* names pages the margin crop must leave alone, in the sidecar's own
    spelling; pages carrying a custom crop belong in it too, since their
    coordinates are in the original image's space.

    *progress_fn* is called as ``(done, total)`` after each page, and
    *stop_requested_fn* is polled between pages: page-number cleanup takes a
    second a page, so a volume is minutes of work that has to stay reportable
    and interruptible.

    *build_previews* is the Page Flip strip, and only the KFX serializer
    stores one; a serializer that writes none can turn it off and skip a
    512px resize and a re-encode on every page.

    *resize_cover* makes the cover go through the same canvas sizing as
    every other page instead of being left exactly as it came. It defaults
    off for callers using this lower-level page walk directly; both native
    container writers enable it so an outsized source cover cannot enlarge
    the shared fixed-layout viewport. Only the sizing changes -- the cover's
    crop, split_spreads, cleanup, no_padding and restore overrides below are
    unconditional either way.
    """
    from ._native_source import build_toc_entries, rekey_toc_entries, rel_variants, walk_source

    _log = log_fn or (lambda msg: None)

    scan = walk_source(source_dir, excluded=excluded, log_fn=_log)
    if not scan["pages"] and not scan["cover"]:
        raise ValueError("no images found in %s" % source_dir)

    if canvas and resize:
        # Both native containers render above the screen and let the device do
        # the last reduction, the way every Amazon comic measured is built.
        # Handing the device a page at exactly the panel size leaves its
        # renderer nothing to resample, and the paper arrives as visible
        # dither. Upscale is not optional here: a page left below the standard
        # puts the device back to enlarging it, which is the same case.
        from ._image_pipeline import page_render_canvas

        lifted = page_render_canvas(canvas)
        if lifted != tuple(canvas):
            _log("RENDER: pages are built at %dx%d" % (lifted[0], lifted[1]))
            canvas = lifted
            upscale = True

    toc = build_toc_entries(
        scan,
        bookmarks=bookmarks,
        comicinfo_bookmarks=comicinfo_bookmarks,
        log_fn=_log,
    )

    source_name = os.path.basename(str(source_dir).rstrip("/\\"))
    nocrop_norm = set()
    for rel in nocrop or ():
        nocrop_norm.update(rel_variants(rel, source_name))
    watermark_match_norm = None
    if watermark_matches is not None:
        watermark_match_norm = set()
        for rel in watermark_matches:
            watermark_match_norm.update(rel_variants(rel, source_name))
    custom_norm = {}
    for rel, bounds in (custom_crops or {}).items():
        if isinstance(bounds, dict):
            for variant in rel_variants(rel, source_name):
                custom_norm[variant] = bounds
    splits_norm = {}
    for rel, cfg in (custom_splits or {}).items():
        if isinstance(cfg, dict):
            for variant in rel_variants(rel, source_name):
                splits_norm[variant] = cfg
    edits_norm = {}
    for rel, ops in (edit_ops or {}).items():
        if isinstance(ops, list) and ops:
            for variant in rel_variants(rel, source_name):
                edits_norm[variant] = ops
    margins_norm = {}
    for rel, margins in (extra_margin or {}).items():
        if isinstance(margins, dict) and any(
                margins.get(side, 0) for side in ("top", "bottom", "left", "right")):
            for variant in rel_variants(rel, source_name):
                margins_norm[variant] = margins

    cleanup = None
    artifact_cleanup = None
    artifact_profiles = None
    if page_numbers or watermarks:
        from .autonomous import _load_artifact_profiles

        # Loaded once: page-number protection and crop-only watermark matching
        # share the user's taught profiles, and disk I/O per page would dominate
        # both passes.
        artifact_profiles = _load_artifact_profiles("")
    if page_numbers:
        from .page_number_sequence import PageNumberSequence

        cleanup = {
            "sequence": PageNumberSequence(),
            "profiles": artifact_profiles,
            "method": cleanup_method,
            "padding": cleanup_padding,
            "scope_path": page_number_scope,
        }
    if watermarks and artifact_profiles:
        artifact_cleanup = {
            "profiles": artifact_profiles,
            "padding": cleanup_padding,
        }

    from .gpu_resources import TemporaryModels

    with TemporaryModels(_log) as gpu_models:
        restorer = None
        if int(manga_upscale or 0):
            from .manga_upscale import MangaUpscaler

            # One per volume: it keeps each model loaded, counts what it did, and
            # switches itself off if the model set cannot be had at all.
            restorer = gpu_models.add(MangaUpscaler(manga_upscale, log_fn=_log,
                                     target_height=(canvas[1] if canvas else 1920)))

        scan_cleaner = None
        if scan_cleanup:
            from .scan_cleanup import ScanCleaner

            scan_cleaner = gpu_models.add(ScanCleaner(log_fn=_log))

        options = {
            "canvas": canvas,
            "resize": resize,
            "no_padding": no_padding,
            "righttoleft": righttoleft,
            "quality": quality,
            "borders_color": borders_color,
            "split_spreads": split_spreads,
            "rotate_spreads": rotate_spreads,
            "force_spread_preview": force_spread_preview,
            "spread_preview_mode": spread_preview_mode,
            "upscale": upscale,
            "stretch": stretch,
            "grayscale": grayscale,
            "page_format": page_format,
            "mozjpeg": mozjpeg,
            "crop": crop,
            "margin_pct": margin_pct,
            "custom_crop": None,
            "custom_split": None,
            "edit_ops": None,
            "extra_margin": None,
            "cleanup": cleanup,
            "artifact_cleanup": artifact_cleanup,
            "artifact_profiles": artifact_profiles if watermarks else None,
            "restore": restorer,
            "scan_cleanup": scan_cleaner,
            "build_previews": build_previews,
            "log_fn": _log,
        }

        page_groups = []
        if scan["cover"]:
            # The cover is left exactly as it came unless resize_cover says
            # otherwise: not cropped, not enlarged, and -- by default -- not
            # resized at all. Product serializers turn the flag on so a large
            # source cover cannot become the viewport for every content page.
            cover_pages = _pages_from_file(
                scan["cover"]["path"], scan["cover"]["rel"],
                **dict(options, split_spreads=False, no_padding=True,
                       resize=(resize if resize_cover else False),
                       crop=False, cleanup=None, artifact_cleanup=None, restore=None))
            if mozjpeg:
                # Nothing re-encodes the cover, so the repack every other page gets
                # on the way out never reached it.  It changes the coding, not the
                # pixels, which is why it does not count as processing.
                from ._image_pipeline import repack_jpeg

                for cover_page in cover_pages:
                    packed = repack_jpeg(cover_page["data"], log_fn=_log)
                    if len(packed) < len(cover_page["data"]):
                        _log("COVER: mozjpeg %d -> %d bytes" % (len(cover_page["data"]), len(packed)))
                        cover_page["data"] = packed
            page_groups.append(cover_pages)

        # Where each source page lands in the finished book's page sequence,
        # which is what a TOC entry names.  A page the splitter cut in half
        # takes two of those numbers, so this cannot be counted off the index.
        page_to_book_page = {}
        book_pages = sum(len(group) for group in page_groups)
        spreads = 0
        cropped_skipped = 0
        custom_cropped = 0
        hand_split = 0
        edited = 0
        margined = 0
        total = len(scan["pages"])
        chapter_starts = {item["first_page"] for item in scan.get("chapters", [])}
        chapter_starts.update(entry[0] for entry in toc)
        chapter_start = 0
        for index, page in enumerate(scan["pages"]):
            if index in chapter_starts:
                chapter_start = index
            if stop_requested_fn is not None and stop_requested_fn():
                raise UserWarning("Conversion interrupted.")
            rel_key = page["rel"].replace("\\", "/").lower()
            overrides = {}
            if cleanup:
                overrides["cleanup"] = dict(cleanup, chapter_key=str(chapter_start))
            bounds = custom_norm.get(rel_key)
            if bounds is not None:
                overrides.update(crop=False, custom_crop=bounds)
                custom_cropped += 1
            elif crop and rel_key in nocrop_norm:
                overrides["crop"] = False
                cropped_skipped += 1
            if rel_key in splits_norm:
                overrides["custom_split"] = splits_norm[rel_key]
                hand_split += 1
            if rel_key in edits_norm:
                overrides["edit_ops"] = edits_norm[rel_key]
                edited += 1
            if rel_key in margins_norm:
                overrides["extra_margin"] = margins_norm[rel_key]
                margined += 1
            if watermark_match_norm is not None and rel_key not in watermark_match_norm:
                # A saved watermark list is authoritative. Ordinary maic margin
                # cropping still applies to pages removed from that list.
                overrides["artifact_cleanup"] = None
                overrides["artifact_profiles"] = None
            page_options = dict(options, **overrides) if overrides else options
            pages = _pages_from_file(page["path"], page["rel"], **page_options)
            page_to_book_page[index] = book_pages
            page_groups.append(pages)
            book_pages += len(pages)
            if len(pages) == 2:
                spreads += 1
            if progress_fn is not None:
                progress_fn(index + 1, total)
        if restorer is not None:
            summary = restorer.summary()
            if summary:
                _log(summary.strip())
        if scan_cleaner is not None:
            summary = scan_cleaner.summary()
            if summary:
                _log(summary.strip())
        if cropped_skipped:
            _log("CROP: %d pages left uncropped (NoCrop)" % cropped_skipped)
        if custom_cropped:
            _log("CROP: %d pages use the sidecar's own crop box" % custom_cropped)
        if hand_split:
            _log("SPLIT: %d pages are cut where the sidecar says" % hand_split)
        if edited:
            _log("EDIT: %d pages carry edit ops" % edited)
        if margined:
            _log("MARGIN: %d pages carry an extra margin" % margined)

        toc_entries = rekey_toc_entries(toc, page_to_book_page)
        if facing_pages:
            # Pairing is decided here rather than after the book is built: the
            # generator already draws a two-page group side by side.
            page_groups, toc_entries = pair_facing_pages(page_groups, toc_entries, log_fn=_log)
        _log("SOURCE: %d sections (%d spreads), %d TOC entries"
             % (len(page_groups), spreads, len(toc_entries)))
        return page_groups, toc_entries


def _set_page_backgrounds(page_groups, mode="none", log_fn=None):
    """Attach KCC's auto/white/black page background to every image.

    KCC detects the colour on the original source before it crops, splits or
    resizes it, and both halves of a spread inherit that decision. Do the same
    here and cache by source path so a split page is decoded only once.
    """
    from PIL import Image

    from ._image_pipeline import detect_fill

    _log = log_fn or (lambda message: None)
    requested = str(mode or "none").strip().lower()
    if requested not in {"none", "white", "black"}:
        requested = "none"
    cache = {}
    counts = {"white": 0, "black": 0}
    for group in page_groups:
        for page in group:
            path = str(page.get("path") or "")
            key = path or id(page)
            if key not in cache:
                if requested in {"white", "black"}:
                    background = requested
                else:
                    try:
                        with Image.open(path) as opened:
                            background = detect_fill(opened.convert("RGB"), "none")
                    except Exception:
                        # The page bytes have already passed the image pipeline,
                        # so they are a safe fallback if its source disappeared.
                        import io
                        with Image.open(io.BytesIO(page["data"])) as opened:
                            background = detect_fill(opened.convert("RGB"), "none")
                cache[key] = background
            page["background_color"] = cache[key]
            counts[cache[key]] += 1
    _log("BACKGROUND: %s (%d white, %d black)"
         % ("auto" if requested == "none" else requested,
            counts["white"], counts["black"]))
