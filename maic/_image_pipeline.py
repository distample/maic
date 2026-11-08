"""maic's own image passes, independent of KCC.

These used to live inside the KCC monkeypatch in ``kcc_patch.py``.  They never
depended on KCC -- each is a walk over a directory of image files, opening them
with PIL and writing them back in place -- so they are shared here and called
from both the KCC path and the native "KFX maic" path.

Keeping one implementation is the point: two copies would drift, and the
difference would only show up as pages that look subtly different depending on
which output format was chosen.

The actual image work lives in :mod:`maic.autonomous`; this module is the
orchestration around it -- which files to touch, in what order, how to save,
and when to give up.
"""

import os

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}

# Constants lifted from KCC (``kindlecomicconverter/image.py``).  They are
# reproduced rather than imported because the native KFX path must not depend
# on KCC being installed -- but they have to keep the same values, or the two
# paths disagree about which pages are spreads.
# KCC's AUTO_CROP_THRESHOLD, 0.015, is deliberately not among them: it decides
# nothing about spreads, only whether a page close to the device's shape is
# centre-cropped to it, and maic shrinks such a page instead of cutting the
# preserved margin off it.  See resize_to_device.
# Below this a landscape page is just a wide page, not a facing spread.
SPREAD_MIN_RATIO = 1.16
# Above this it is a panorama: bisecting would cut through a panel, so KCC
# rotates it instead (its BISECT_THRESHOLD).
SPREAD_BISECT_MAX_RATIO = 1.8

# Share the cutoff between Auto's preview predictor and correction width.
SPREAD_PREVIEW_DEEP_BLACK_THRESHOLD = 0.80

# What a native fixed-layout page is rendered at.  Measured across fourteen
# Amazon store comics: every one ships its pages 1920 px tall, while the layout
# block around them varies from 1153x1730 to 1801x2560 -- none of which is any
# Kindle's screen.  Both native writers share this pipeline, so MOBI maic and
# KFX maic deliberately upscale and downscale to the same render canvas before
# their containers diverge.  The device performs the last reduction itself,
# and that is what keeps paper flat: a page handed over at exactly the panel
# size leaves the renderer nothing to resample, so its near-white values reach
# the screen as visible dither instead of being averaged away.  Confirmed on
# device 2026-08-18 with two probe builds, 1280x1920 and 1440x1920, both clean
# where the same volume at 1272x1696 was not.
NATIVE_PAGE_HEIGHT = 1920

# The width that goes with it.  Measured across the fourteen Amazon store
# comics: every one of them ships a single page size per book, 1920 tall, at
# whatever width its own art is -- 1280 (Spy x Family, whose pages happen to be
# exactly two by three), 1338, 1347, 1350, 1351.  1400 clears the widest of
# them with room to spare, so no book's art is ever reduced to reach it, and
# the pages of one volume still come out a single size.
NATIVE_PAGE_WIDTH = 1400

# Kept as a compatibility name for callers/tests written before MOBI maic
# started using the same native render pipeline.
KFX_PAGE_HEIGHT = NATIVE_PAGE_HEIGHT

# Page-number cleanup gives up after this many failures in a row, rather than
# grinding through a whole volume that cannot work.
_MAX_CONSECUTIVE_ERRORS = 3


def _noop_log(msg):
    pass


def _never_stop():
    return False


def encode_page(image, fmt="jpg", quality=90, mozjpeg=False, log_fn=None):
    """Encode a finished page for the container.

    ``mozjpeg`` re-packs the JPEG losslessly, 10-20% smaller for twice the
    time.  The KCC path force-disables it for KFX because Kindle Previewer
    needs the restart markers it can drop; nothing here goes through Previewer,
    and the generator reads ``yj_jpg_rst_marker_present`` off the bytes it
    actually wrote, so the book stays consistent either way.
    """
    import io

    log = log_fn or _noop_log
    buf = io.BytesIO()
    if str(fmt).lower() == "png":
        image.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    save_jpeg(image, buf, quality)
    data = buf.getvalue()
    return repack_jpeg(data, log_fn=log) if mozjpeg else data


def repack_jpeg(data, log_fn=None):
    """Re-pack finished JPEG bytes losslessly, for images never re-encoded.

    Same optimizer ``encode_page`` runs, reachable on its own for the pages
    that reach the container as the file they came from -- the cover above all,
    which is the largest single image in a book and the one nothing resizes.
    The pixels are untouched; only the coding changes.
    """
    log = log_fn or _noop_log
    if not (len(data) >= 2 and data[0] == 0xFF and data[1] == 0xD8):
        return data
    try:
        import mozjpeg_lossless_optimization

        return mozjpeg_lossless_optimization.optimize(data)
    except Exception as exc:
        log("JPEG: mozjpeg skipped (%s)" % exc)
        return data


def save_jpeg(image, target, quality):
    """maic's JPEG encoder, for both the KCC path and the native KFX path.

    Two details matter and are easy to lose in a re-implementation:
    transparency is composited onto white rather than dropped, and the encoder
    is asked for restart markers.  kfxlib checks whether *any* JPEG in a book
    carries them, and the KFX path relies on that being true.
    """
    from PIL import Image

    if getattr(image, "mode", "") not in {"L", "RGB"}:
        if image.mode in {"RGBA", "LA"} or ("transparency" in getattr(image, "info", {})):
            rgba_image = image.convert("RGBA")
            background = Image.new("RGBA", rgba_image.size, (255, 255, 255, 255))
            background.alpha_composite(rgba_image)
            image = background.convert("RGB")
        else:
            image = image.convert("RGB")
    quality = max(1, min(100, int(quality or 90)))
    try:
        image.save(target, format="JPEG", optimize=1, quality=quality, restart_marker_rows=32)
    except TypeError:
        image.save(target, format="JPEG", optimize=1, quality=quality)


def save_in_place(image, path):
    """Write *image* back over *path*, keeping the format's quality settings."""
    ext = os.path.splitext(path.lower())[1]
    if ext in {".jpg", ".jpeg"}:
        image.save(path, quality=95, subsampling=0)
    elif ext == ".webp":
        image.save(path, quality=95, method=6)
    else:
        image.save(path)


def device_canvas(profile, hq=False):
    """Screen size for a device profile name -- ``"KPW12"`` -> ``(1272, 1696)``.

    Resolved through KCC's own profile table so the native path targets exactly
    the screen the UI's device picker means, including maic's own KPW12 entry,
    which is injected into that table rather than shipped with KCC.

    Without KCC the short table in :mod:`maic._device_profiles` answers
    instead.  This is the one thing the native writers still needed KCC for,
    and needing it meant a checkout with an empty ``modules/`` could not build
    a book in any format -- not even the ones that run no KCC code at all.
    """
    if not isinstance(profile, str):
        width, height = profile
        return int(width), int(height)

    from .config import KCC_AVAILABLE
    from .kcc_env import ensure_kcc_path

    data = None
    # Native profiles also work when the optional KCC module is absent.
    if KCC_AVAILABLE:
        ensure_kcc_path()
        from .kcc_patch import _install_preserve_margin_hv_patch

        try:
            _install_preserve_margin_hv_patch()
        except ImportError:
            # Report missing dependencies with setup instructions; runtime
            # profile lookup must never install packages.
            from .kcc_env import ensure_kcc_deps

            ensure_kcc_deps()
            _install_preserve_margin_hv_patch()
        from kindlecomicconverter.image import ProfileData

        data = ProfileData.Profiles.get(profile)

    if data is None:
        from ._device_profiles import native_profile_size

        size = native_profile_size(profile)
        if size is None:
            raise ValueError("unknown device profile: %s" % profile)
        width, height = size
    else:
        width, height = data[1]
    if hq:
        # KCC's own "high quality" lever: render at 1.5x the panel and let the
        # device downsample.
        width, height = int(width * 1.5), int(height * 1.5)
    return int(width), int(height)


def page_render_canvas(canvas, height=NATIVE_PAGE_HEIGHT, width=NATIVE_PAGE_WIDTH):
    """Canvas for native KFX/MOBI pages: 1400x1920, the store's own shape.

    The shape decides how much margin is baked into a page.  Padding out to
    the screen's own shape puts a wide bar down both sides of every page whose
    proportions differ from the device.  1400 is past the widest page any of
    the fourteen store books ships (1351), so the art of a volume is padded a
    little rather than reduced, and every page of it comes out one size.

    Whatever screen is left over around that page is filled by the reader,
    with the page's background colour in MOBI and with white in KFX, where no
    property colours it.

    A screen narrower than the standard keeps its own shape, so a page is
    never wider than the screen it is read on, and a device taller than it
    keeps its height: that is a floor for the render, not a cap.
    """
    screen_width, screen_height = int(canvas[0]), int(canvas[1])
    render_height = max(screen_height, int(height))
    scale = float(render_height) / float(screen_height)
    standard_width = int(round(render_height * float(width) / float(height)))
    return min(int(round(screen_width * scale)), standard_width), render_height


def _paper_edges(image):
    """True when one whole outer edge of the page is really paper.

    ``_has_white_paper_edge`` asks only that an edge be light, which a page
    drawn on grey or on yellow also satisfies. Deciding whether to keep that
    background needs the stricter question.
    """
    from PIL import Image

    width, height = image.size
    if width < 1 or height < 1:
        return False
    rgb = image.convert("RGB")
    for box in ((0, 0, width, 1), (0, height - 1, width, height),
                (0, 0, 1, height), (width - 1, 0, width, height)):
        low, _high = rgb.crop(box).convert("L").getextrema()
        if low >= 232:
            return True
    return False


def _has_white_paper_edge(image):
    """True when one whole outer edge of the page is white."""
    bw = image.convert("L").point(lambda x: 0 if x < 128 else 255, "1")
    width, height = bw.size
    if width < 1 or height < 1:
        return False
    edges = (
        bw.crop((0, 0, width, 1)),
        bw.crop((0, height - 1, width, height)),
        bw.crop((0, 0, 1, height)),
        bw.crop((width - 1, 0, width, height)),
    )
    return any(edge.getextrema()[0] == 255 for edge in edges)


def detect_fill(image, explicit="none"):
    """"white" or "black" -- which colour a page's margins should be.

    KCC's ``fillCheck``, reached through the copy maic already keeps for crop
    previews so the two stay in step, with one rule of maic's own on top: a
    page that still has one entirely white edge pads white, whatever the rest
    of it looks like.  Art bleeding off the other three sides drags KCC's
    vote to black, and a black bar butted against the surviving paper margin
    reads as a defect, while white against the bleeding art reads as the
    page's own margin carried on.
    """
    from .kcc_scan import _detect_fill_color

    requested = str(explicit or "none").strip().lower()
    if requested in {"white", "black"}:
        return requested
    if _has_white_paper_edge(image):
        return "white"
    if _shared_dark_color_background(image) is not None:
        return "black"
    return _detect_fill_color(image, requested)


def _resize_method(image, canvas):
    from PIL import Image

    if image.size[0] <= canvas[0] and image.size[1] <= canvas[1]:
        return Image.Resampling.BICUBIC
    return Image.Resampling.LANCZOS


def _contain_to_height(image, canvas, method):
    """Bring a page to the canvas height, keeping its own proportions.

    The canvas is two by three while most pages are wider than that, so a page
    fitted inside the box would stop short of the render height and hand the
    device an enlargement to do. The height is the part that matters; the
    width is the page's own.
    """
    height = int(canvas[1])
    width = max(1, int(round(image.size[0] * height / float(image.size[1]))))
    if (width, height) == image.size:
        return image
    return image.resize((width, height), method)


def _padding_centering(image, canvas, fill):
    """Keep a full-bleed vertical edge against the same canvas edge.

    ``ImageOps.pad`` centres the contained image by default.  That is right
    when both ends carry paper, but wrong when maic has found paper only at one
    end: half of the compensating margin is then inserted against artwork that
    already runs cleanly to the opposite edge.  A nearly solid fill-coloured
    band is treated as paper/background; when only one of the horizontal edges
    has one, all vertical padding goes there.

    The decision is deliberately limited to vertical padding.  Facing-page
    joins and the crop's aspect-aware side handling own the horizontal edges.
    """
    width, height = image.size
    canvas_width, canvas_height = int(canvas[0]), int(canvas[1])
    if width * canvas_height <= canvas_width * height:
        return 0.5, 0.5

    gray = image.convert("L")
    band_height = max(2, min(12, height // 200))
    inset = max(1, width // 50)
    left, right = inset, max(inset + 1, width - inset)

    def _is_fill_band(top):
        if top:
            band = gray.crop((left, 0, right, band_height))
        else:
            band = gray.crop((left, height - band_height, right, height))
        histogram = band.histogram()
        matching = sum(histogram[:24]) if fill == "black" else sum(histogram[232:])
        return matching >= band.width * band.height * 0.97

    top_is_fill = _is_fill_band(True)
    bottom_is_fill = _is_fill_band(False)
    if top_is_fill and not bottom_is_fill:
        return 0.5, 1.0
    if bottom_is_fill and not top_is_fill:
        return 0.5, 0.0
    return 0.5, 0.5


def _dark_pixel_ratio(edge, threshold=128):
    """Fraction of an edge/band that belongs to a black background field."""
    histogram = edge.convert("L").histogram()
    total = max(1, sum(histogram))
    return sum(histogram[: max(0, min(256, int(threshold)))]) / float(total)


def _corner_mean(gray, *, left, top):
    """Mean luma of a small physical corner, large enough to ignore one line."""
    width, height = gray.size
    band_width = max(4, min(width, int(round(width * 0.06))))
    band_height = max(4, min(height, int(round(height * 0.06))))
    x0 = 0 if left else width - band_width
    y0 = 0 if top else height - band_height
    histogram = gray.crop((x0, y0, x0 + band_width, y0 + band_height)).histogram()
    count = max(1, sum(histogram))
    return sum(value * amount for value, amount in enumerate(histogram)) / float(count)


def _padding_gradient_side_depths(image, minimum_delta=160.0, maximum_step_ratio=0.04):
    """Find textured side fields that are safe to extend, but not to crop.

    The crop detector is deliberately strict: a noisy screentone field is not
    removable unless several columns repeat almost exactly.  Padding has the
    opposite risk profile.  It only needs a broad, monotonic background
    transition at the physical edge, and preserving that transition is safer
    than replacing it with a solid black bar.

    The default contrast is for black/white fields. A verified grey page
    background can use a lower threshold for a white/grey transition.
    """
    import math

    from PIL import Image, ImageFilter

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
            Image.Resampling.BILINEAR,
        )
    analysis = analysis.filter(
        ImageFilter.GaussianBlur(max(2, int(round(analysis.height * 0.006))))
    )
    gray = models.np.asarray(analysis, dtype=models.np.float32)

    full = models.np.asarray(image.convert("L"), dtype=models.np.float32)

    def framed(side, depth):
        """True when the side band's transition lives inside framed panels.

        Read as one column, a black page carrying a panel whose wall shades
        from dark to light and a white panel below it is a black-to-white
        transition (Gachiakuta v17 ch142 p1).  A frame rule crossing the
        band does not settle it on its own: a real page field can carry a
        panel border too (Kemono Jihen v3 ch9 p23), and there the field
        simply continues on the far side of the line.  What says the tone
        belongs to panels rather than to the page is the page showing again
        between them: after a rule-bounded stretch that departs from the
        tone the band had before its first frame, a later gutter between
        rules returns to that tone.

        Rules are thin, so they are read from the page at full size, where
        the resampled analysis copy would dilute them past recognition.
        """
        rows = full if side == "left" else full[:, ::-1]
        height, width = rows.shape
        band = max(1, min(width, int(round(depth * source_width / float(analysis.width)))))
        reach = max(2, round(height * 0.0025))
        if height <= 4 * reach:
            return False
        contrast = models.np.minimum(
            models.np.abs(rows[reach:-reach] - rows[: -2 * reach]),
            models.np.abs(rows[reach:-reach] - rows[2 * reach :]),
        ) > 64.0
        across_band = models.np.mean(contrast[:, :band], axis=1) >= 0.90
        across_page = models.np.mean(contrast, axis=1) >= 0.50
        rules = models.np.flatnonzero(across_band & across_page) + reach
        if rules.size < 2:
            return False
        profile = models.np.mean(rows[:, :band], axis=1)
        first = int(rules[0])
        if first - reach <= 0:
            return False
        page_tone = float(models.np.mean(profile[max(0, first - 2 * reach):first - reach + 1]))
        departed = False
        for start, end in zip(rules[:-1], rules[1:]):
            segment = profile[int(start) + reach : max(int(start) + reach, int(end) - reach)]
            if not segment.size:
                continue
            tone = float(models.np.median(segment))
            if abs(tone - page_tone) > 64.0:
                departed = True
            elif departed and abs(tone - page_tone) <= 24.0:
                return True
        return False

    def scan(columns, side):
        width, height = columns.shape
        if width < 12 or height < 40:
            return 0
        seed_width = max(2, min(8, round(width * 0.006)))
        profile = models.np.median(columns[:seed_width], axis=0)
        cap = max(2, round(height * 0.05))
        delta = float(models.np.mean(profile[-cap:]) - models.np.mean(profile[:cap]))
        if abs(delta) < minimum_delta:
            return 0

        direction = 1.0 if delta > 0 else -1.0
        movement = direction * models.np.diff(profile)
        positive = models.np.maximum(movement, 0.0)
        negative = models.np.maximum(-movement, 0.0)
        forward = float(models.np.sum(positive))
        backward = float(models.np.sum(negative))
        support = int(models.np.sum(positive > 0.10))
        if (
            forward < minimum_delta
            or backward > max(36.0, forward * 0.35)
            or support < max(12, round(height * 0.05))
            or float(models.np.max(positive, initial=0.0)) > max(6.0, forward * maximum_step_ratio)
        ):
            return 0

        difference = models.np.abs(columns - profile[None, :])
        similar = (
            (models.np.median(difference, axis=1) <= 16.0)
            & (models.np.percentile(difference, 90, axis=1) <= 34.0)
        )
        changed = (~similar).astype(models.np.uint8)
        runs = models.np.convolve(changed, models.np.ones(3, dtype=models.np.uint8), mode="valid")
        starts = models.np.flatnonzero(runs >= 3)
        if starts.size == 0:
            return 0
        depth = int(starts[0])
        if depth < max(4, round(width * 0.008)) or depth > round(width * 0.25):
            return 0
        context_end = min(width, depth + max(6, round(width * 0.04)))
        if float(models.np.mean(~similar[depth:context_end])) < 0.50:
            return 0
        if framed(side, depth):
            return 0
        return depth

    horizontal_scale = source_width / float(analysis.width)
    return {
        "left": max(0, int(math.floor(scan(gray.T, "left") * horizontal_scale))),
        "right": max(0, int(math.floor(scan(gray.T[::-1], "right") * horizontal_scale))),
    }


def _hard_field_side_transitions(image):
    """Recognize a sharp background change corroborated by both page sides.

    One side must carry two solid fields over its full height. The other must
    confirm the transition locally, but may contain full-bleed artwork
    farther away (Dandadan v1 ch2 p25). An internal gutter can confirm that
    an earlier panel edge is interrupting one shared page field (Berserk
    v15 ch102 p67). If artwork reaches that transition,
    a solid gutter spanning the page can confirm its short incoming field
    (v1 ch4 p6); that side inherits the boundary of the uninterrupted field.
    The dark fill is sampled from that field to avoid a darker padding seam.
    A lone white panel corner, a scan line, or a gradual
    screentone transition is not enough evidence.
    """
    from PIL import Image

    from . import models

    models._ensure_imports()
    np = models.np
    width, height = image.size
    if width < 40 or height < 80:
        return None
    band = max(3, min(12, round(width * 0.006)))
    gray = image.convert("L")
    profiles = {
        side: np.median(np.asarray(gray.crop(box)), axis=1)
        for side, box in (
            ("left", (0, 0, band, height)),
            ("right", (width - band, 0, width, height)),
        )
    }
    minimum_field = max(12, round(height * 0.15))
    shoulder = max(6, round(height * 0.05))
    tolerance = max(2, round(height * 0.01))
    panel_tolerance = max(3, round(height * 0.03))
    gutter_tolerance = max(3, round(height * 0.02))
    gutter_height = max(3, round(height * 0.006))
    antialias = max(1, round(height * 0.002))

    def matches(values, white):
        return float(np.mean(values >= 232 if white else values <= 24)) >= 0.98

    def internal_gutter_confirms_field(panel_split, field_split, top_white):
        # A panel can start before the surrounding page field ends. Require
        # a real separator between two panels: connected to the incoming
        # cross-page field, keeping its tone past the panel top, and changing
        # near the clean outside margin to the outgoing tone through the foot.
        if panel_split >= field_split - 3 * antialias:
            return False
        pixels = np.asarray(gray)
        thin_gutter = max(3, round(height * 0.001))
        if not any(
            matches(pixels[end - thin_gutter:end], top_white)
            for end in range(panel_split - antialias, panel_split + antialias + 1)
        ):
            return False
        y0, y1 = panel_split + antialias, field_split - 2 * antialias
        incoming = pixels[y0:y1]
        outgoing = pixels[field_split + 2 * antialias:]
        incoming_mask = incoming >= 232 if top_white else incoming <= 24
        outgoing_mask = outgoing <= 24 if top_white else outgoing >= 232
        cores = (np.mean(incoming_mask, axis=0) >= 0.98) & (np.mean(outgoing_mask, axis=0) >= 0.98)
        inset = max(3, round(width * 0.10))
        cores[:inset] = False
        cores[-inset:] = False
        changes = np.flatnonzero(np.diff(np.r_[False, cores, False]))
        minimum_core = max(3, round(width * 0.002))
        frame_gap = max(2, round(width * 0.01))
        panel_width = max(3, round(width * 0.01))
        for start, end in zip(changes[::2], changes[1::2]):
            if end - start < minimum_core:
                continue
            panels = (incoming[:, max(0, start - frame_gap - panel_width):start - frame_gap],
                      incoming[:, end + frame_gap:min(width, end + frame_gap + panel_width)])
            if all(part.size and float(np.mean(part <= 24 if top_white else part >= 232)) >= 0.80
                   for part in panels):
                return True
        return False

    for side, profile in profiles.items():
        top_white = bool(profile[0] >= 128)
        crossings = np.flatnonzero((profile >= 128) != top_white)
        if not crossings.size:
            continue
        split = int(crossings[0])
        if not minimum_field <= split <= height - minimum_field:
            continue
        if not (
            matches(profile[:split - antialias], top_white)
            and matches(profile[split + antialias:], not top_white)
            and matches(profile[split - shoulder:split - antialias], top_white)
            and matches(profile[split + antialias:split + shoulder], not top_white)
        ):
            continue
        other_side = "right" if side == "left" else "left"
        other = profiles[other_side]
        candidates = np.flatnonzero(
            ((other[:-1] >= 128) == top_white)
            & ((other[1:] >= 128) != top_white)
        ) + 1
        for other_split in sorted(candidates, key=lambda y: abs(int(y) - split)):
            other_split = int(other_split)
            distance = abs(other_split - split)
            if distance > max(panel_tolerance, gutter_tolerance):
                continue
            if not matches(other[other_split + antialias:other_split + shoulder], not top_white):
                continue
            local_field = distance <= tolerance and matches(
                other[other_split - shoulder:other_split - antialias], top_white
            )
            shared_field = distance > tolerance and internal_gutter_confirms_field(other_split, split, top_white)
            if shared_field:
                # The clean outer side defines the page background height;
                # the earlier side crossing is the panel's own top edge.
                other_split = split
            elif not local_field:
                if distance > gutter_tolerance:
                    continue
                # A full-bleed panel can leave only a short incoming field.
                # Require a thick, solid gutter across the entire width,
                # rather than accepting a short line at the physical edge.
                gutter_end = other_split - antialias
                gutter = np.asarray(gray.crop(
                    (0, gutter_end - gutter_height, width, gutter_end)
                ))
                if not matches(gutter, top_white):
                    continue
                # The gutter confirms the background, but its panel border
                # is not the end of the full-height field on the clean side.
                other_split = split
            dark_y0, dark_y1 = (
                (split + antialias, height) if top_white else (0, split - antialias)
            )
            dark_x0 = 0 if side == "left" else width - band
            dark_patch = image.crop((dark_x0, dark_y0, dark_x0 + band, dark_y1))
            dark_pixels = np.asarray(dark_patch.convert("RGB"))[
                np.asarray(dark_patch.convert("L")) <= 24
            ]
            dark_rgb = tuple(int(round(value)) for value in np.median(dark_pixels, axis=0))
            dark = Image.new("RGB", (1, 1), dark_rgb).convert(image.mode).getpixel((0, 0))
            top, bottom = ("white", dark) if top_white else (dark, "white")
            return {
                side: (split, top, bottom, side),
                other_side: (other_split, top, bottom, other_side if local_field else side),
            }
    return None


def _hard_field_boundaries(image, side, expected, radius, top_white):
    """Continue a short antialiased transition and locate safe white cleanup.

    Resampling can leave several gray rows around a sharp source boundary.
    Padding repeats the contiguous gray rows at their existing height.
    Source-edge cleanup starts only at full paper white, preserving its gray
    transition. Search locally around the confirmed source boundary so nearby
    artwork cannot move the field's split.
    """
    import numpy as np

    band = max(3, min(12, round(image.width * 0.006)))
    x0 = 0 if side == "left" else image.width - band
    y0, y1 = max(0, expected - radius), min(image.height, expected + radius + 1)
    patch = image.crop((x0, y0, x0 + band, y1))
    profile = np.median(np.asarray(patch.convert("L")), axis=1)
    boundaries = []
    for threshold in (232, 254):
        white = profile >= threshold
        crossings = np.flatnonzero(
            (white[:-1] == top_white) & (white[1:] != top_white)
        ) + 1
        boundary = min((y0 + int(row) for row in crossings),
                       key=lambda row: abs(row - expected), default=expected)
        boundaries.append(boundary)
    intermediate = (profile > 24) & (profile < 254)
    rows = np.flatnonzero(intermediate)
    if not rows.size:
        return boundaries[0], boundaries[1], []
    center = min(rows, key=lambda row: abs(y0 + int(row) - expected))
    start, end = int(center), int(center) + 1
    while start > 0 and intermediate[start - 1]:
        start -= 1
    while end < len(profile) and intermediate[end]:
        end += 1
    if start == 0 or end == len(profile):
        return boundaries[0], boundaries[1], []
    from PIL import Image

    rgb_rows = np.median(np.asarray(patch.convert("RGB"))[start:end], axis=1)
    colors = [
        Image.new("RGB", (1, 1), tuple(int(round(v)) for v in rgb)).convert(image.mode).getpixel((0, 0))
        for rgb in rgb_rows
    ]
    return y0 + start, boundaries[1], colors


def _clean_hard_field_white_seam(image, side, split, top_white):
    """Remove a faint scan fringe only beside a verified blank white field.

    Require nearly the whole region to have white interior paper and a faint
    outer fringe. Artwork, darker outlines and nonwhite interiors are retained.
    Transition rows retain their resampling antialiasing.
    """
    import numpy as np

    depth = max(2, min(6, round(image.width * 0.003)))
    y0, y1 = (0, split) if top_white else (split, image.height)
    x0 = 0 if side == "left" else image.width - 2 * depth
    band = image.crop((x0, y0, x0 + 2 * depth, y1)).convert("RGB")
    values = np.asarray(band)
    edge, interior = (
        (values[:, :depth], values[:, depth:]) if side == "left"
        else (values[:, depth:], values[:, :depth])
    )
    white_rows = np.all(interior >= 254, axis=(1, 2))
    faint_rows = np.all(edge >= 240, axis=(1, 2))
    fringe_rows = np.any(edge < 254, axis=(1, 2))
    if (
        float(np.mean(white_rows)) < 0.98
        or float(np.mean(faint_rows)) < 0.98
        or float(np.mean(fringe_rows & white_rows & faint_rows)) < 0.75
    ):
        return
    # Only the narrow outer strip changes, and only on confirmed paper rows.
    edge_x0 = 0 if side == "left" else image.width - depth
    strip = image.crop((edge_x0, y0, edge_x0 + depth, y1))
    from PIL import Image

    mask = Image.fromarray(((white_rows & faint_rows) * 255).astype(np.uint8)[:, None])
    mask = mask.resize(strip.size, Image.Resampling.NEAREST)
    strip.paste("white", (0, 0, strip.width, strip.height), mask)
    image.paste(strip, (edge_x0, y0))


def _horizontal_padding_plan(image, fill):
    """Choose side colours and retain any verified gradient-field capacity.

    Manga pages can carry a black-to-white background field across one edge.
    Extending both sides with KCC's single global black vote then puts a black
    bar directly beside the light end of that field.  A predominantly light
    physical side is extended with paper instead.  When both full-height sides
    are dark but a strong corner-to-corner transition identifies the field
    (Kemono Jihen v1 ch2 p22), its black and white ends decide their respective
    extensions.  The source remains centred; only the two padding colours
    differ.
    """
    # White manga frames can themselves occupy an outer corner. They are not
    # evidence for a two-colour page field: without a verified gradient the
    # global black background is the only safe continuation on both sides.
    from .autonomous import _horizontal_gradient_edge_depths, _vertical_gradient_side_depths

    crop_gradients = _vertical_gradient_side_depths(image)
    padding_gradients = _padding_gradient_side_depths(image)
    vertical_gradients = {
        side: crop_gradients.get(side, 0) or padding_gradients.get(side, 0)
        for side in ("left", "right")
    }
    vertical_gradients.update({
        f"{side}_clean": not crop_gradients.get(side, 0) and bool(padding_gradients.get(side, 0))
        for side in ("left", "right")
    })
    if str(fill).lower() != "black":
        # A white top edge does not make two verified side gradients white
        # paper. A lone gradient still follows the existing white-field rule.
        if vertical_gradients["left"] and vertical_gradients["right"]:
            return (fill, fill), vertical_gradients
        return (fill, fill), {"left": 0, "right": 0}
    horizontal_gradients = _horizontal_gradient_edge_depths(image)
    if not any(horizontal_gradients.values()) and not any(vertical_gradients.values()):
        if _ink_edges_are_not_textured_field(image, full_bleed=True):
            solid = [_solid_dark_side_color(image, side, "black") for side in ("left", "right")]
            if (solid[0] != "black") != (solid[1] != "black"):
                # A genuine solid ink margin can coexist with full-bleed
                # line art. Continue the solid side; give the drawing paper,
                # rather than copying its strokes into a supposed field.
                return tuple("black" if color != "black" else "white" for color in solid), vertical_gradients
        return ("black", "black"), vertical_gradients

    gray = image.convert("L")
    left_edge = gray.crop((0, 0, 1, gray.height))
    right_edge = gray.crop((gray.width - 1, 0, gray.width, gray.height))
    left_dark = _dark_pixel_ratio(left_edge) >= 0.5
    right_dark = _dark_pixel_ratio(right_edge) >= 0.5

    # A page such as ch2 p41 is globally voted black because of its cropped
    # top band, yet neither side is a black field.  Both added margins are
    # paper in that case.
    if not left_dark and not right_dark:
        return ("white", "white"), vertical_gradients

    top_pair = (
        _corner_mean(gray, left=True, top=True),
        _corner_mean(gray, left=False, top=True),
    )
    bottom_pair = (
        _corner_mean(gray, left=True, top=False),
        _corner_mean(gray, left=False, top=False),
    )
    pair = max((top_pair, bottom_pair), key=lambda values: abs(values[0] - values[1]))
    darker, lighter = min(pair), max(pair)
    if darker <= 48.0 and lighter >= 192.0 and lighter - darker >= 128.0:
        return (
            (
                "black" if pair[0] <= 48.0 else "white",
                "black" if pair[1] <= 48.0 else "white",
            ),
            vertical_gradients,
        )

    return (
        ("black" if left_dark else "white", "black" if right_dark else "white"),
        vertical_gradients,
    )


def _edge_background_candidate(image):
    """One colour repeated around a full-bleed colour page, or ``None``.

    The two side medians must land on the same shade, over actual colour
    artwork. What that shade then has to prove is left to the caller: this
    reports how much of each edge it holds, how much of the page, how far
    apart the two side medians were, and how strong the best rival tone on
    those two edges is.
    """
    import numpy as np

    rgb_image = image.convert("RGB")
    thumbnail = rgb_image.copy()
    thumbnail.thumbnail((128, 128))
    rgb = np.asarray(thumbnail, dtype=np.int16)
    if float(np.mean(np.max(rgb, axis=2) - np.min(rgb, axis=2) >= 24)) < 0.05:
        return None
    w, h = image.size
    band = max(2, min(12, round(min(w, h) * 0.006)))
    boxes = ((0, 0, band, h), (w - band, 0, w, h),
             (0, 0, w, band), (0, h - band, w, h))
    edges = [np.asarray(rgb_image.crop(box), dtype=np.float32) for box in boxes]
    left, right = [np.median(edge, axis=(0, 1)) for edge in edges[:2]]
    if float(np.max(np.abs(left - right))) > 6:
        return None
    candidate = (left + right) / 2
    support = [float(np.mean(np.max(np.abs(edge - candidate), axis=2) <= 8)) for edge in edges]
    page = np.asarray(thumbnail, dtype=np.float32)
    share = float(np.mean(np.max(np.abs(page - candidate), axis=2) <= 12))
    sides = np.concatenate([edge.reshape(-1, 3) for edge in edges[:2]])
    held = float(np.mean(np.max(np.abs(sides - candidate), axis=1) <= 12))
    # The strongest tone on those edges that is not the candidate itself.
    quantised = np.unique((sides // 8).astype(np.int16) * 8, axis=0)
    rival = max(
        [
            float(np.mean(np.max(np.abs(sides - other), axis=1) <= 12))
            for other in quantised
            if float(np.max(np.abs(other - candidate))) > 24
        ]
        + [0.0]
    )
    return {
        "colour": candidate,
        "share": share,
        "support": support,
        "sides_agree": float(np.max(np.abs(left - right))),
        "held": held,
        "rival": rival,
    }


def _as_page_color(image, candidate):
    from PIL import Image

    color = tuple(int(round(value)) for value in candidate)
    return Image.new("RGB", (1, 1), color).convert(image.mode).getpixel((0, 0))


def _shared_dark_color_background(image):
    """The dark case of the shared background, which decides the fill vote.

    A surviving white paper edge keeps the page white whatever the rest of it
    looks like, as in ``detect_fill``.
    """
    import numpy as np

    if _has_white_paper_edge(image):
        return None
    found = _edge_background_candidate(image)
    if found is None:
        return None
    support = found["support"]
    if min(support[:2]) < 0.60 or max(support[2:]) < 0.60:
        return None
    candidate = found["colour"]
    if float(np.dot(candidate, (0.299, 0.587, 0.114))) > 64:
        return None
    return _as_page_color(image, candidate)


def _shared_page_background(image):
    """The colour to pad a page drawn on its own background, or ``None``.

    A page printed on grey concrete or on yellow (Gachiakuta v6 ch46 p1 and
    v5 ch37 p1) bleeds that background off every edge, and paper bars beside
    it read as a defect exactly the way a black bar does beside a dark page.
    Paper is the one background that is not carried out: it is already what
    an unpainted margin is, and a page that is merely off-white would show a
    seam if its grey were.  The colour must also hold a real share of the
    page, so that a narrow band of something else along one edge cannot
    repaint the whole margin.
    """
    import numpy as np

    if _paper_edges(image):
        return None
    found = _edge_background_candidate(image)
    if found is None:
        background = _uniform_gray_page_background(image) or _neutral_color_page_field(image)
        if background is not None:
            return background
        fields = _interrupted_page_fields(image)
        return _as_page_color(image, fields[0][1]) if fields else None
    support = found["support"]
    # Either the shade holds most of both sides and a horizontal edge, or --
    # where display lettering and full-bleed artwork break those edges up, as
    # on Gachiakuta v8 ch64 p1 -- the two side medians land on it exactly,
    # nothing else on those edges is more common, and a horizontal edge still
    # carries some of it.  Two agreeing sides on their own are not a page
    # background; the top and bottom have to know about it too.
    if not (
        (min(support[:2]) >= 0.60 and max(support[2:]) >= 0.60)
        or (
            found["sides_agree"] <= 2.0
            and found["held"] >= 0.35
            and found["held"] > found["rival"]
            and max(support[2:]) >= 0.25
        )
    ):
        return None
    candidate = found["colour"]
    if found["share"] < 0.05:
        return None
    if float(np.min(candidate)) >= 232:
        return None
    return _as_page_color(image, candidate)


def _uniform_gray_page_background(image):
    """Recognize a solid grey outer field on a monochrome manga page.

    Any full edge can establish the field: Jigokuraku v1 ch1 p39 has
    artwork at both sides, but its bottom margin is solid grey. Require
    actual band depth and near-uniformity throughout that edge, rather
    than treating a common midtone inside panels as the page background.
    """
    import numpy as np

    rgb_image = image.convert("RGB")
    thumbnail = rgb_image.copy()
    thumbnail.thumbnail((128, 128))
    rgb = np.asarray(thumbnail, dtype=np.int16)
    if float(np.mean(np.max(rgb, axis=2) - np.min(rgb, axis=2) >= 24)) >= 0.05:
        return None
    width, height = image.size
    band = max(3, round(min(width, height) * 0.02))
    if min(width, height) < band * 2:
        return None
    shades = []
    for box in ((0, 0, band, height), (width - band, 0, width, height),
                (0, 0, width, band), (0, height - band, width, height)):
        edge = np.asarray(rgb_image.crop(box), dtype=np.float32)
        shade = np.median(edge, axis=(0, 1))
        if float(np.max(shade) - np.min(shade)) > 4:
            continue
        if not 48 < float(np.dot(shade, (0.299, 0.587, 0.114))) < 232:
            continue
        matching = np.max(np.abs(edge - shade), axis=2) <= 4
        if float(np.mean(matching)) >= 0.97:
            shades.append(shade)
    if not shades:
        return None
    # Different solid edge tones do not establish one common background.
    if float(np.max(np.ptp(shades, axis=0))) > 6:
        return None
    return _as_page_color(image, np.median(shades, axis=0))


def cropped_page_background(source, cropped):
    """Keep the verified pre-crop background for an explicit manual crop.

    Moving the crop handles may remove the field completely. Its identity
    still comes from the original page, rather than the new artwork edge.
    Return RGB so the hint can cross a later greyscale conversion.
    """
    return _shared_page_background(source.convert("RGB"))


def _neutral_color_page_fields(image):
    """A neutral outer field, including very dark textured page backgrounds.

    Jigokuraku v2 ch7 p2 has a textured grey field only on the right; the
    opposite edge is red artwork. Require a full-height band with real depth
    and a stable neutral shade, so a panel frame or a grey fragment of the
    artwork cannot supply the padding colour. The median tolerates texture
    without allowing a gradient or unrelated colours to become a solid field.
    """
    import numpy as np

    rgb_image = image.convert("RGB")
    thumbnail = rgb_image.copy()
    thumbnail.thumbnail((128, 128))
    rgb = np.asarray(thumbnail, dtype=np.int16)
    colorful = float(np.mean(np.max(rgb, axis=2) - np.min(rgb, axis=2) >= 24)) >= 0.05
    width, height = image.size
    band = max(3, round(width * 0.02))
    if width < band * 2:
        return []
    candidates = []
    for side, x0 in (("left", 0), ("right", width - band)):
        edge = np.asarray(
            rgb_image.crop((x0, 0, x0 + band, height)), dtype=np.float32,
        )
        shade = np.median(edge, axis=(0, 1))
        if float(np.max(shade) - np.min(shade)) > 12:
            continue
        if not 8 < float(np.dot(shade, (0.299, 0.587, 0.114))) < 232:
            continue
        matching = np.max(np.abs(edge - shade), axis=2) <= 20
        # Coverage must hold along the page, not just in one large panel.
        if float(np.mean(matching)) < 0.90:
            continue
        if any(float(np.mean(part)) < 0.85 for part in np.array_split(matching, 4)):
            continue
        if not colorful:
            # A monochrome edge needs corroboration from a horizontal field;
            # grey panel fragments alone must not repaint the page margins.
            horizontal = [np.asarray(rgb_image.crop(box), dtype=np.float32)
                          for box in ((0, 0, width, band), (0, height - band, width, height))]
            if max(float(np.mean(np.max(np.abs(edge - shade), axis=2) <= 20))
                   for edge in horizontal) < 0.60:
                continue
        candidates.append((side, shade))
    if not candidates:
        return []
    if len(candidates) == 2 and float(np.max(np.abs(candidates[0][1] - candidates[1][1]))) > 12:
        return []
    return candidates


def _neutral_color_page_field(image):
    import numpy as np

    fields = _neutral_color_page_fields(image)
    if not fields:
        return None
    return _as_page_color(image, np.mean([shade for _, shade in fields], axis=0))


def _ink_edges_are_not_textured_field(image, *, full_bleed=False):
    """Distinguish monochrome ink/JPEG fringes from dark background grain."""
    import numpy as np

    rgb = image.convert("RGB")
    width, height = rgb.size
    band = max(3, round(width * 0.02))
    sides = np.concatenate([np.asarray(rgb.crop(box), dtype=np.float32)
                            for box in ((0, 0, band, height), (width - band, 0, width, height))], axis=1)
    if height < 2 or float(np.mean(np.abs(np.diff(np.mean(sides, axis=2), axis=0)) > 64)) < 0.015:
        # One white panel corner on a black page is not full-bleed line art.
        return False
    values = np.concatenate([np.asarray(rgb.crop(box), dtype=np.float32).reshape(-1, 3)
                             for box in ((0, 0, band, height), (width - band, 0, width, height),
                                         (0, 0, width, band), (0, height - band, width, height))])
    if float(np.mean(np.ptp(values, axis=1) >= 12)) >= 0.01:
        return False
    levels = np.mean(values, axis=1)
    dark = levels[levels <= 32]
    ink_share = float(np.mean(dark <= 3)) if dark.size else 0.0
    if full_bleed and not (
        ink_share < 0.90 and np.mean(levels >= 232) >= 0.20
        and np.mean((levels > 32) & (levels < 232)) >= 0.12
    ):
        # Crisp black page fields with white frames keep their established
        # black padding. Dense antialiased strokes reaching the edge are a
        # different case; their lighter tones are drawing/JPEG fringes.
        return False
    return bool(dark.size and ink_share >= 0.75 and np.mean(levels >= 232) >= 0.10)


def _interrupted_page_fields(image):
    """Find a dominant outer field interrupted by lettering or full-bleed art.

    Use agreement across several edges and a clear lead over rival colours,
    rather than demanding that every edge be uniform. This includes almost
    black textured fields and tinted fields, while equal competing tones or
    an isolated dark fragment do not establish a page background.
    """
    import numpy as np

    if _paper_edges(image) or _ink_edges_are_not_textured_field(image):
        return []
    # Already verified solid sides keep their own independently sampled tint.
    if all(_solid_dark_side_color(image, side, "black") != "black"
           for side in ("left", "right")):
        return []
    rgb_image = image.convert("RGB")
    width, height = image.size
    band = max(3, round(width * 0.02))
    edges = [np.asarray(rgb_image.crop(box), dtype=np.float32) for box in (
        (0, 0, band, height), (width - band, 0, width, height),
        (0, 0, width, band), (0, height - band, width, height),
    )]
    values = np.concatenate([edge.reshape(-1, 3) for edge in edges])
    bins, counts = np.unique((values // 8).astype(np.int16), axis=0, return_counts=True)
    modes = bins[np.argsort(counts)[-8:][::-1]] * 8 + 4
    for mode in modes:
        if float(np.max(mode)) > 96:
            continue
        seed = values[np.max(np.abs(values - mode), axis=1) <= 12]
        if not len(seed):
            continue
        shade = np.median(seed, axis=0)
        masks = [np.max(np.abs(edge - shade), axis=2) <= 20 for edge in edges]
        held = [float(np.mean(mask)) for mask in masks]
        if min(held[:2]) < 0.35 or sum(held[:2]) / 2 < 0.45 or max(held[2:]) < 0.25:
            continue
        quarter_support = [
            (float(np.mean(left)) + float(np.mean(right))) / 2
            for left, right in zip(np.array_split(masks[0], 4), np.array_split(masks[1], 4))
        ]
        if min(quarter_support) < 0.20:
            continue
        support = float(np.mean(np.max(np.abs(values - shade), axis=1) <= 20))
        rival = max([float(np.mean(np.max(np.abs(values - other), axis=1) <= 20))
                     for other in modes if float(np.max(np.abs(other - shade))) > 32] + [0.0])
        if support <= rival * 1.35:
            continue
        thumbnail = rgb_image.copy()
        thumbnail.thumbnail((128, 128))
        page = np.asarray(thumbnail, dtype=np.float32)
        if float(np.mean(np.max(np.abs(page - shade), axis=2) <= 20)) < 0.05:
            continue
        distance = np.max(np.abs(values - shade), axis=1)
        field_pixels = distance[distance <= 20]
        if len(field_pixels) and float(np.mean(field_pixels <= 3)) >= 0.85:
            # A tightly clustered paint/ink field is genuinely solid. Small
            # lettering and JPEG fringes must not become invented texture.
            return []
        return [("left", shade), ("right", shade)]
    return []


def _textured_page_field_extension(image, side, width, background, fields, pool_edges=False, match_seam=True, output_height=None):
    """Quilt clean patches of a verified grey field into the added margin.

    Random offsets prevent a narrow edge strip from repeating as vertical
    bars. Overlapping patches hide tile boundaries, and the extension next
    to its source edge starts with that edge's own pixels. The fixed seed
    keeps previews and conversion reproducible.
    """
    import numpy as np
    from PIL import Image

    band = max(3, round(image.width * 0.02))
    source_side, shade = next(
        (field for field in fields if field[0] == side), fields[0],
    )
    x0 = 0 if source_side == "left" else image.width - band
    source = np.asarray(
        image.convert("RGB").crop((x0, 0, x0 + band, image.height)), dtype=np.float32,
    ).copy()
    # Exclude stray ink and compression outliers from the sampled field.
    matching = np.max(np.abs(source - shade), axis=2) <= 20
    source[~matching] = shade
    height = output_height or image.height
    if float(np.max(np.std(source, axis=(0, 1)))) < 0.5:
        return Image.new(image.mode, (width, height), background)

    # Draw texture from rows that actually carry the field, not from large
    # replaced fragments of flowers, lettering or panel artwork.
    donor = source[np.mean(matching, axis=1) >= 0.75]
    if pool_edges:
        # Interrupted fields need samples beyond the nearest physical edge:
        # that edge can itself be a black frame or mostly lettering. Gather
        # clean textured portions of all four bands, excluding bright art.
        pools = []
        rgb_image = image.convert("RGB")
        for box, horizontal in (
            ((0, 0, band, image.height), False),
            ((image.width - band, 0, image.width, image.height), False),
            ((0, 0, image.width, band), True),
            ((0, image.height - band, image.width, image.height), True),
        ):
            samples = np.asarray(rgb_image.crop(box), dtype=np.float32).copy()
            if horizontal:
                samples = samples.transpose(1, 0, 2)
            clean = np.max(np.abs(samples - shade), axis=2) <= 20
            samples[~clean] = shade
            textured_rows = np.std(samples, axis=(1, 2)) >= 1.0
            rows = samples[(np.mean(clean, axis=1) >= 0.35) & textured_rows]
            if len(rows):
                pools.append(rows)
        if pools:
            donor = np.concatenate(pools)
    if not len(donor):
        return Image.new(image.mode, (width, height), background)
    tile_w = min(band, width)
    tile_h = min(len(donor), max(8, round(height * 0.06)))
    overlap_x = min(3, tile_w // 3)
    overlap_y = min(16, tile_h // 4)
    step_x, step_y = tile_w - overlap_x, tile_h - overlap_y
    rng = np.random.default_rng(1729 if side == "left" else 1730)
    pixels = np.zeros((height, width, 3), dtype=np.float32)
    weights = np.zeros((height, width), dtype=np.float32)
    for y in range(0, height, step_y):
        h = min(tile_h, height - y)
        for x in range(0, width, step_x):
            w = min(tile_w, width - x)
            sy = int(rng.integers(0, len(donor) - h + 1))
            sx = int(rng.integers(0, band - w + 1))
            patch = donor[sy:sy + h, sx:sx + w]
            if rng.integers(0, 2):
                patch = patch[:, ::-1]
            wx, wy = np.ones(w, dtype=np.float32), np.ones(h, dtype=np.float32)
            ox, oy = min(overlap_x, w), min(overlap_y, h)
            if ox:
                wx[:ox] *= np.arange(1, ox + 1) / (ox + 1)
                wx[-ox:] *= np.arange(ox, 0, -1) / (ox + 1)
            if oy:
                wy[:oy] *= np.arange(1, oy + 1) / (oy + 1)
                wy[-oy:] *= np.arange(oy, 0, -1) / (oy + 1)
            weight = wy[:, None] * wx[None, :]
            pixels[y:y + h, x:x + w] += patch * weight[:, :, None]
            weights[y:y + h, x:x + w] += weight
    pixels /= weights[:, :, None]
    if source_side == side and match_seam:
        # Match the seam, then gradually give way to independently sampled
        # texture. Only the clean field is reflected, never neighbouring art.
        distance = np.arange(width) if side == "right" else np.arange(width)[::-1]
        folded = distance % (2 * band)
        folded = np.minimum(folded, 2 * band - 1 - folded)
        columns = band - 1 - folded if side == "right" else folded
        continuation = source[:, columns]
        blend = np.maximum(0, 1 - distance / max(1, 2 * band)).astype(np.float32)
        pixels = pixels * (1 - blend[None, :, None]) + continuation * blend[None, :, None]
    return Image.fromarray(np.clip(np.rint(pixels), 0, 255).astype(np.uint8)).convert(image.mode)


def _solid_dark_side_color(image, side, fallback):
    """Sample a uniform dark side field, preserving its RGB tint.

    Require near-uniform colour along the full side band so artwork or a
    gradient cannot lend its colour to otherwise solid automatic padding.
    """
    import numpy as np
    from PIL import Image

    if fallback != "black":
        return fallback
    width = max(3, min(12, round(image.width * 0.006)))
    x0 = 0 if side == "left" else image.width - width
    patch = image.crop((x0, 0, x0 + width, image.height)).convert("RGB")
    values = np.asarray(patch, dtype=np.float32)
    rgb = np.median(values, axis=(0, 1))
    if float(np.dot(rgb, (0.299, 0.587, 0.114))) > 64:
        return fallback
    difference = np.max(np.abs(values - rgb), axis=2)
    if float(np.percentile(difference, 98)) > 8:
        return fallback
    color = tuple(int(round(value)) for value in rgb)
    return Image.new("RGB", (1, 1), color).convert(image.mode).getpixel((0, 0))


def _horizontal_padding_colors(image, fill):
    """Back-compatible colour-only view of the automatic padding plan."""
    return _horizontal_padding_plan(image, fill)[0]


def _field_without_edge_ink(field, direction, columns, tolerance=16.0):
    """Refill artwork that bleeds off the page with the field's own texture.

    The repeating-field branch of the gradient padding copies real columns
    outwards, so ink reaching the physical edge -- a panel rule, the tip of a
    frame -- would be redrawn in the margin and made longer than the artist
    drew it.

    Averaged over its screentone a background column is monotonic, so isotonic
    regression pools exactly the rows the artwork disturbs.  That pooled block
    localises the damage but overstates it, because every row running up to
    the disturbance is pooled with it; within the block the ink is the part
    departing from a straight line drawn between the two clean shoulders.
    Artwork is also a connected shape, while the ripple a coarse screentone
    leaves behind the blur is not, so a row survives only where the column
    beside it agrees.

    Surviving rows are refilled by reflecting the nearer shoulder back over
    the run and returning it to the field's own slope, which keeps the dot
    phase and the local tone that substituting a smoothed profile loses.
    Unlike the smoothed branch nothing is dissolved across the seam: the
    margin carries the page's field, and the artwork ends where the page does.
    """
    from PIL import ImageFilter

    height = field.height
    ordered = list(columns)
    if height < 8 or len(ordered) < 2:
        return field
    # Sized to the screentone dot, not to the page: a radius scaled to the
    # height dissolves the thin end of a rule running off the edge along with
    # the dots, and then only its thick end reads as anything but field.
    radius = max(2, int(round(height * 0.0016)))
    measured = field.convert("L").filter(ImageFilter.GaussianBlur(radius))
    levels = measured.load()
    # A shoulder inside the blur's reach still carries the ink's own tone, so
    # the straight line is anchored beyond it.
    margin = radius * 2 + 1

    marks = {}
    backgrounds = {}
    for x in ordered:
        blocks = []
        for y in range(height):
            value = levels[x, y] * direction
            blocks.append([value, 1, value, value])
            while len(blocks) >= 2 and blocks[-2][0] > blocks[-1][0]:
                right = blocks.pop()
                left = blocks.pop()
                count = left[1] + right[1]
                blocks.append([
                    (left[0] * left[1] + right[0] * right[1]) / count,
                    count,
                    min(left[2], right[2]),
                    max(left[3], right[3]),
                ])

        ink = [False] * height
        background = None
        row = 0
        for _, count, lowest, highest in blocks:
            if highest - lowest > tolerance and count < height:
                if background is None:
                    background = [float(levels[x, y]) for y in range(height)]
                above = max(0, row - margin)
                below = min(height - 1, row + count - 1 + margin)
                span = float(below - above) or 1.0
                # Anchor each end on a short run of rows: a screentone coarse
                # enough to survive the blur would otherwise tilt the line off
                # a single noisy row and read as ink.
                anchors = []
                for anchor in (above, below):
                    window = range(
                        max(0, anchor - radius),
                        min(height, anchor + radius + 1),
                    )
                    anchors.append(
                        sum(levels[x, y] for y in window) / float(len(window))
                    )
                # The line runs past the block on both sides so the rows a
                # repair copies from are measured against the same model.
                for y in range(above, below + 1):
                    background[y] = anchors[0] + (anchors[1] - anchors[0]) * (
                        (y - above) / span
                    )
                for y in range(row, row + count):
                    if abs(levels[x, y] - background[y]) > tolerance:
                        ink[y] = True
            row += count
        marks[x] = ink
        backgrounds[x] = background

    healed = None
    for index, x in enumerate(ordered):
        ink = marks[x]
        if not any(ink):
            continue
        neighbours = [
            marks[ordered[position]]
            for position in (index - 1, index + 1)
            if 0 <= position < len(ordered)
        ]
        ink = [
            value
            and any(
                other[max(0, y - 1)] or other[y] or other[min(height - 1, y + 1)]
                for other in neighbours
            )
            for y, value in enumerate(ink)
        ]
        if not any(ink):
            continue

        if healed is None:
            healed = field.copy()
        background = backgrounds[x]
        # Transparency is not part of the field's tone and must not be shifted.
        toned = [band != "A" for band in field.getbands()]
        start = 0
        while start < height:
            if not ink[start]:
                start += 1
                continue
            end = start
            while end < height and ink[end]:
                end += 1
            above, below = start - 1, end
            for y in range(start, end):
                if above >= 0 and (below >= height or y - above <= below - y):
                    source = above - (y - above)
                    if source < 0 or ink[source]:
                        source = above
                elif below < height:
                    source = below + (below - y)
                    if source >= height or ink[source]:
                        source = below
                else:
                    continue
                offset = int(round(background[y] - background[source]))
                pixel = field.getpixel((x, source))
                healed.putpixel(
                    (x, y),
                    max(0, min(255, pixel + offset))
                    if isinstance(pixel, int)
                    else tuple(
                        max(0, min(255, channel + offset)) if shift_band else channel
                        for channel, shift_band in zip(pixel, toned)
                    ),
                )
            start = end
    return field if healed is None else healed


def _gradient_side_extension(
    image,
    side,
    depth,
    size,
    mode,
    *,
    clean_profile=False,
    slope_override=None,
    preserve_texture_direction=False,
    analysis_image=None,
    edge_offset=0.0,
):
    """Continue a verified vertical side field through newly added canvas.

    The outer field is extrapolated as a two-dimensional texture.  Its
    black/white transition may run diagonally and may be made from sharp manga
    screentone rather than a smooth ramp, so reducing it to one averaged
    column would visibly change both the angle and the print texture.
    """
    from PIL import Image, ImageChops, ImageFilter, ImageStat

    width, height = image.size
    depth = max(0, min(width, int(depth)))
    extension_width, extension_height = int(size[0]), int(size[1])
    if depth <= 0 or extension_width <= 0 or extension_height <= 0:
        return None
    if height != extension_height:
        scaled_width = max(1, int(round(width * extension_height / float(height))))
        depth = max(1, int(round(depth * scaled_width / float(width))))
        image = image.resize((scaled_width, extension_height), Image.Resampling.BICUBIC)
        width, height = image.size
        depth = min(width, depth)

    field = (
        image.crop((0, 0, depth, height))
        if side == "left"
        else image.crop((width - depth, 0, width, height))
    )
    analysis_field = (
        analysis_image.resize(image.size, Image.Resampling.BILINEAR).crop(
            (0, 0, depth, height) if side == "left" else (width - depth, 0, width, height)
        ) if analysis_image is not None else field.convert("L")
    )

    # Estimate how far the tonal front moves vertically per horizontal pixel.
    # Smoothing is used only for this measurement; the pixels copied below are
    # the untouched sharp/stippled source field.
    measured = analysis_field.filter(
        ImageFilter.GaussianBlur(
            max(1, int(round(height * (0.006 if clean_profile else 0.002))))
        )
    )
    pixels = measured.load()
    cap = max(1, min(16, height // 20))
    top = sum(pixels[x, y] for x in range(depth) for y in range(cap))
    bottom = sum(
        pixels[x, y]
        for x in range(depth)
        for y in range(height - cap, height)
    )
    direction = 1.0 if bottom >= top else -1.0
    centres = []
    for x in range(depth):
        if clean_profile:
            top_level = sum(pixels[x, y] for y in range(cap)) / cap
            bottom_level = sum(pixels[x, height - cap + y] for y in range(cap)) / cap
            middle = (top_level + bottom_level) / 2.0
            crossing = next(
                (
                    y
                    for y in range(height)
                    if (pixels[x, y] >= middle if direction > 0 else pixels[x, y] <= middle)
                ),
                None,
            )
            if crossing is not None:
                centres.append((x, crossing))
        else:
            weights = [
                max(0.0, direction * (pixels[x, y + 1] - pixels[x, y]))
                for y in range(height - 1)
            ]
            total = sum(weights)
            if total >= 48.0:
                centres.append((x, sum(y * value for y, value in enumerate(weights)) / total))
    if len(centres) >= 3:
        mean_x = sum(point[0] for point in centres) / len(centres)
        mean_y = sum(point[1] for point in centres) / len(centres)
        denominator = sum((point[0] - mean_x) ** 2 for point in centres)
        slope = (
            sum((point[0] - mean_x) * (point[1] - mean_y) for point in centres)
            / denominator
            if denominator
            else 0.0
        )
        # A field detector only promises a locally repeating background.  An
        # extreme fit is therefore noise or nearby artwork, not useful angle.
        slope = max(-3.0, min(3.0, slope))
    else:
        slope = 0.0
    source_slope = slope
    if slope_override is not None:
        slope = max(-3.0, min(3.0, float(slope_override)))

    extension = Image.new(image.mode, (extension_width, height))
    if clean_profile:
        # Average out the stipple, then use isotonic regression to remove panel
        # separators and scan lines from the background model.  Those marks
        # may touch the edge, but they must not be sheared into the new field.
        raw_profile = analysis_field.resize((1, height), Image.Resampling.BOX)
        raw_profile = raw_profile.filter(
            ImageFilter.GaussianBlur(max(1, int(round(height * 0.002))))
        )
        values = [float(raw_profile.getpixel((0, y))) * direction for y in range(height)]
        blocks = []
        for value in values:
            blocks.append([value, 1])
            while len(blocks) >= 2 and blocks[-2][0] > blocks[-1][0]:
                right_value, right_count = blocks.pop()
                left_value, left_count = blocks.pop()
                count = left_count + right_count
                blocks.append([
                    (left_value * left_count + right_value * right_count) / count,
                    count,
                ])
        monotonic = []
        for value, count in blocks:
            monotonic.extend([max(0, min(255, round(value * direction)))] * count)

        transition_rows = [y for y, value in enumerate(monotonic) if 24 < value < 231]
        texture_rows = []
        texture_source_rows = []
        if transition_rows:
            first_transition = transition_rows[0]
            last_transition = transition_rows[-1]
            light_shoulder_limit = max(12, len(transition_rows) // 4)
            texture_source_rows = list(
                range(
                    max(0, first_transition - light_shoulder_limit),
                    min(height, last_transition + light_shoulder_limit + 1),
                )
            )
            texture_rows = [
                y
                for y, value in enumerate(monotonic)
                if 2 < value < 253
                and (
                    value < 231
                    or (
                        first_transition - light_shoulder_limit
                        <= y
                        <= last_transition + light_shoulder_limit
                    )
                )
            ]
        if texture_rows:
            # Outside the last detectable screentone shoulder this is no
            # longer a gradient estimate but the terminal page field.  The
            # averaged source profile may stop at e.g. 250 because of paper
            # grain or nearby artwork; carrying that value through the whole
            # padding creates a visibly gray block after an otherwise white
            # transition.  Snap only the completed tails to their canonical
            # black/white endpoints, leaving every textured row untouched.
            first_texture = texture_rows[0]
            last_texture = texture_rows[-1]
            if direction > 0:
                monotonic[:first_texture] = [0] * first_texture
                monotonic[last_texture + 1 :] = [255] * (
                    height - last_texture - 1
                )
            else:
                monotonic[:first_texture] = [255] * first_texture
                monotonic[last_texture + 1 :] = [0] * (
                    height - last_texture - 1
                )

        clean_monotonic = list(monotonic)
        if transition_rows:
            first_transition = transition_rows[0]
            last_transition = transition_rows[-1]
            if direction > 0:
                for y in range(last_transition + 1, height):
                    if clean_monotonic[y] >= 245:
                        clean_monotonic[y] = 255
            else:
                for y in range(0, first_transition):
                    if clean_monotonic[y] >= 245:
                        clean_monotonic[y] = 255

        profile = Image.new("L", (1, height))
        profile.putdata(clean_monotonic)
        profile = profile if image.mode == "L" else profile.convert(image.mode)
        textured = False
        row_is_background = [True] * height
        texture_row_set = set(texture_rows)
        texture_source_row_set = set(texture_source_rows)
        if transition_rows:
            first_transition = transition_rows[0]
            last_transition = transition_rows[-1] + 1
            transition = analysis_field.crop(
                (0, first_transition, field.width, last_transition)
            )
            detail = ImageChops.difference(
                transition,
                transition.filter(ImageFilter.GaussianBlur(1)),
            )
            detail_histogram = detail.histogram()
            detail_count = max(1, sum(detail_histogram))
            detail_mean = sum(
                value * amount for value, amount in enumerate(detail_histogram)
            ) / detail_count
            textured = detail_mean >= 4.0
            if not textured:
                # A white-to-grey stipple front can occupy only a short part
                # of a very long grey tail. Measuring that tail together with
                # the front dilutes real dots into a "smooth" gradient.
                # Check detail where the tone is actually transitioning too.
                low = min(clean_monotonic[0], clean_monotonic[-1]) + 12
                high = max(clean_monotonic[0], clean_monotonic[-1]) - 12
                active_rows = [
                    y for y in range(first_transition, last_transition)
                    if low < clean_monotonic[y] < high
                ]
                if len(active_rows) >= max(12, round(height * 0.01)):
                    active_detail = sum(
                        ImageStat.Stat(detail.crop(
                            (0, y - first_transition, depth, y - first_transition + 1),
                        )).mean[0]
                        for y in active_rows
                    ) / len(active_rows)
                    textured = active_detail >= 4.0

            # A frame rule is coherent across the whole side field, unlike a
            # screentone dot pattern. Exclude such rows before sampling the
            # texture so they cannot turn into diagonal marks in the padding.
            gray_field = analysis_field
            anomalous_rows = []
            for y in texture_source_rows:
                row = gray_field.crop((0, y, depth, y + 1))
                stats = ImageStat.Stat(row)
                if (
                    abs(stats.mean[0] - monotonic[y]) > 96.0
                    and stats.stddev[0] < 12.0
                ):
                    anomalous_rows.append(y)

            # Screentone itself naturally makes individual rows look darker
            # or flatter than their neighbours.  Disabling texture one row at
            # a time turns that noise into conspicuous horizontal banding.
            # Only a coherent run is a frame/separator worth suppressing.
            run_start = 0
            while run_start < len(anomalous_rows):
                run_end = run_start + 1
                while (
                    run_end < len(anomalous_rows)
                    and anomalous_rows[run_end] == anomalous_rows[run_end - 1] + 1
                ):
                    run_end += 1
                run = anomalous_rows[run_start:run_end]
                if len(run) >= 3:
                    for y in run:
                        row_is_background[y] = False
                run_start = run_end

        reference_x = 0 if side == "left" else width - 1
        centre_by_x = {int(x): float(y) for x, y in centres}
        boundary_field_x = 0 if side == "left" else depth - 1
        edge_indices = (
            range(0, min(depth, 8))
            if side == "left"
            else range(max(0, depth - 8), depth)
        )
        edge_centres = [centre_by_x[x] for x in edge_indices if x in centre_by_x]
        if boundary_field_x in centre_by_x:
            edge_transition = centre_by_x[boundary_field_x]
        elif edge_centres:
            edge_transition = sum(edge_centres) / len(edge_centres)
        elif centres:
            edge_transition = sum(point[1] for point in centres) / len(centres)
        else:
            edge_transition = height / 2.0

        if (textured or analysis_image is not None) and preserve_texture_direction:
            # As with the dark-field repeat, source columns keep their
            # left-to-right order. Translate whole patches along the measured
            # diagonal: reflection reverses it, while per-column shearing
            # stretches the dots. Anchor the first patch on the real edge.
            clean_field = field.copy()
            for y, is_background in enumerate(row_is_background):
                if not is_background:
                    color = profile.getpixel((0, y))
                    if analysis_image is not None:
                        above, below = y - 1, y + 1
                        while above >= 0 and not row_is_background[above]:
                            above -= 1
                        while below < height and not row_is_background[below]:
                            below += 1
                        rows = [row for row in (above, below) if 0 <= row < height]
                        if rows:
                            colors = [ImageStat.Stat(field.crop((0, row, depth, row + 1))).mean for row in rows]
                            color = tuple(round(sum(values) / len(values)) for values in zip(*colors))
                            if image.mode == "L":
                                color = color[0]
                    clean_field.paste(color, (0, y, depth, y + 1))
            guard = min(4, depth // 16)
            usable = max(1, depth - guard)
            # Quilt small, independently sampled two-dimensional pieces.
            # Repeating the entire field also repeats its recognisable dot
            # clusters and local tonal variations, even with a soft join.
            patch_width = max(1, min(24, usable // 2)) if textured else usable
            overlap = min(8, max(2, patch_width // 4), patch_width - 1)
            stride = patch_width - overlap
            for outward in range(0, extension_width, stride):
                # Always use the same full patch; clipping a partial last
                # patch must not change the source phase as crop handles move.
                if side == "right":
                    output_start = outward
                    source_start = guard
                    anchor_source = source_start
                    anchor_target = width + output_start + edge_offset
                else:
                    output_start = extension_width - outward - patch_width
                    source_start = depth - guard - patch_width
                    anchor_source = source_start + patch_width - 1
                    anchor_target = output_start + patch_width - 1 - extension_width + edge_offset
                source_centre = centre_by_x.get(
                    anchor_source,
                    edge_transition + slope * (anchor_source - boundary_field_x),
                )
                shift = round(edge_transition + slope * (anchor_target - reference_x) - source_centre)
                patch = clean_field.crop((source_start, 0, source_start + patch_width, height))
                endpoint = 0 if shift >= 0 else height - 1
                tile = patch.crop((0, endpoint, patch_width, endpoint + 1)).resize((patch_width, height))
                tile.paste(patch, (0, shift))
                if textured:
                    import random

                    # Seed from distance to the original edge, never from the
                    # canvas width. Changing the crop cannot restart the quilt.
                    rng = random.Random(1729 + outward * 104729)
                    block_height, row_overlap = 40, 8
                    for target_y in range(0, height, block_height - row_overlap):
                        source_start = (guard if side == "right" else 0) + rng.randrange(usable - patch_width + 1)
                        source_anchor = source_start if side == "right" else source_start + patch_width - 1
                        # Continue one measured tonal plane. The donor changes
                        # only the grain, not the position of the gradient front.
                        shift = round(slope * (anchor_target - reference_x)
                                      - source_slope * (source_anchor - boundary_field_x))
                        donor = clean_field.crop((source_start, 0, source_start + patch_width, height))
                        source_rows = [max(0, min(height - 1, y - shift))
                                       for y in range(target_y, min(height, target_y + block_height))]
                        for local_y, source_y in enumerate(source_rows):
                            y = target_y + local_y
                            for local_x in range(patch_width):
                                if target_y and local_y < row_overlap:
                                    selector = ((y * 1103515245 + (outward + local_x) * 12345) & 0xFFFF) / 65535
                                    if selector >= (local_y + 1) / (row_overlap + 1):
                                        continue
                                tile.putpixel((local_x, y), donor.getpixel((local_x, source_y)))
                if outward and overlap:
                    for i in range(overlap):
                        local_x = i if side == "right" else patch_width - overlap + i
                        output_x = output_start + local_x
                        if not 0 <= output_x < extension_width:
                            continue
                        new_fraction = (i + 1) / (overlap + 1)
                        if side == "left":
                            new_fraction = 1 - new_fraction
                        for y in range(height):
                            old_pixel = extension.getpixel((output_x, y))
                            new_pixel = tile.getpixel((local_x, y))
                            if textured:
                                distance = output_x if side == "right" else extension_width - 1 - output_x
                                selector = ((y * 1103515245 + distance * 12345) & 0xFFFF) / 65535
                                pixel = new_pixel if selector < new_fraction else old_pixel
                            elif isinstance(new_pixel, int):
                                pixel = round(old_pixel * (1 - new_fraction) + new_pixel * new_fraction)
                            else:
                                pixel = tuple(round(a * (1 - new_fraction) + b * new_fraction)
                                              for a, b in zip(old_pixel, new_pixel))
                            tile.putpixel((local_x, y), pixel)
                extension.paste(tile, (output_start, 0))
            # A short pixel quilt joins the forward patch to the exact edge
            # without averaging away its grain or leaving a hard vertical seam.
            seam_span = min(8, extension_width)
            for distance in range(seam_span):
                output_x = distance if side == "right" else extension_width - 1 - distance
                boundary = depth - 1 + round(edge_offset) if side == "right" else round(edge_offset)
                source_x = boundary - distance if side == "right" else boundary + distance
                source_x = max(0, min(depth - guard - 1 if side == "left" else depth - 1, source_x))
                for y in range(height):
                    if not textured:
                        weight = distance / max(1, seam_span - 1)
                        source_pixel = clean_field.getpixel((source_x, y))
                        target_pixel = extension.getpixel((output_x, y))
                        pixel = (
                            round(source_pixel * (1 - weight) + target_pixel * weight)
                            if isinstance(source_pixel, int)
                            else tuple(round(a * (1 - weight) + b * weight)
                                       for a, b in zip(source_pixel, target_pixel))
                        )
                        extension.putpixel((output_x, y), pixel)
                        continue
                    selector = ((y * 1103515245 + distance * 12345) & 0xFFFF) / 65535
                    if distance == 0 or selector >= distance / max(1, seam_span - 1):
                        extension.putpixel((output_x, y), clean_field.getpixel((source_x, y)))
            return extension if extension.mode == mode else extension.convert(mode)

        patch_start = None
        if textured and slope_override is not None and extension_width < depth:
            # Continue the sampled texture in its original left-to-right
            # direction.  Mirroring the edge makes the first column equal but
            # reverses the dot phase immediately afterwards, which exposes a
            # vertical axis at the join.  Pick a forward source patch whose
            # boundary best matches the real edge after compensating for the
            # shared gradient slope.
            edge_field_x = 0 if side == "left" else depth - 1
            edge_target_x = 0 if side == "left" else width - 1
            if side == "left":
                candidate_starts = range(0, depth - extension_width)
            else:
                candidate_starts = range(1, depth - extension_width + 1)
            best_score = None
            for candidate_start in candidate_starts:
                # Match the source column immediately *after* the candidate
                # patch on the left, or immediately *before* it on the right,
                # to the real page edge.  The patch itself then preserves a
                # genuine neighbouring column pair across the join instead of
                # merely finding two similar standalone columns.
                matching_field_x = (
                    candidate_start + extension_width
                    if side == "left"
                    else candidate_start - 1
                )
                matching_source_x = (
                    matching_field_x
                    if side == "left"
                    else width - depth + matching_field_x
                )
                candidate_shift = int(
                    round(slope * (edge_target_x - matching_source_x))
                )
                differences = []
                for y in texture_rows:
                    source_y = y - candidate_shift
                    if (
                        source_y in texture_source_row_set
                        and row_is_background[source_y]
                    ):
                        differences.append(
                            abs(
                                gray_field.getpixel((matching_field_x, source_y))
                                - gray_field.getpixel((edge_field_x, y))
                            )
                        )
                if differences:
                    score = sum(differences) / len(differences)
                    if best_score is None or score < best_score:
                        best_score = score
                        patch_start = candidate_start

        period = max(1, depth * 2 - 2)
        for output_x in range(extension_width):
            target_x = output_x - extension_width if side == "left" else width + output_x
            shift = int(round(slope * (target_x - reference_x)))
            endpoint_y = 0 if shift >= 0 else height - 1
            column = Image.new(
                image.mode,
                (1, height),
                profile.getpixel((0, endpoint_y)),
            )
            column.paste(profile, (0, shift))

            if textured:
                # Reflect the real field outwards from the physical edge.  In
                # particular, the column touching the page must reuse the
                # page's own edge column; starting the reflected field at the
                # outer canvas edge creates a visible phase jump at the seam.
                distance_from_edge = (
                    extension_width - output_x if side == "left" else output_x + 1
                )
                if patch_start is not None:
                    field_x = patch_start + output_x
                    source_x = (
                        field_x if side == "left" else width - depth + field_x
                    )
                else:
                    phase = (distance_from_edge - 1) % period
                    inward = phase if phase < depth else period - phase
                    source_x = inward if side == "left" else width - 1 - inward
                    field_x = (
                        source_x if side == "left" else source_x - (width - depth)
                    )
                source_transition = (
                    edge_transition + slope * (source_x - reference_x)
                    if slope_override is not None
                    else centre_by_x.get(
                        field_x,
                        edge_transition + slope * (source_x - reference_x),
                    )
                )
                target_transition = edge_transition + slope * (target_x - reference_x)
                texture_shift = int(round(target_transition - source_transition))
                for y in range(height):
                    profile_y = y - shift
                    source_y = y - texture_shift
                    if (
                        0 <= profile_y < height
                        and 0 <= source_y < height
                        and profile_y in texture_row_set
                        and source_y in texture_source_row_set
                        and row_is_background[source_y]
                    ):
                        source_value = gray_field.getpixel((field_x, source_y))
                        if patch_start is not None and distance_from_edge <= min(
                            8, extension_width
                        ):
                            # Quilt the forward patch into a short reflected
                            # edge continuation.  Pixel selection (rather than
                            # alpha blending) retains crisp screentone dots,
                            # while the irregular boundary avoids both a hard
                            # vertical join and a visible mirror axis.
                            mirror_phase = (distance_from_edge - 1) % period
                            mirror_inward = (
                                mirror_phase
                                if mirror_phase < depth
                                else period - mirror_phase
                            )
                            mirror_source_x = (
                                mirror_inward
                                if side == "left"
                                else width - 1 - mirror_inward
                            )
                            mirror_field_x = (
                                mirror_source_x
                                if side == "left"
                                else mirror_source_x - (width - depth)
                            )
                            mirror_source_transition = (
                                edge_transition
                                + slope * (mirror_source_x - reference_x)
                            )
                            mirror_shift = int(
                                round(target_transition - mirror_source_transition)
                            )
                            mirror_source_y = y - mirror_shift
                            if (
                                mirror_source_y in texture_source_row_set
                                and row_is_background[mirror_source_y]
                            ):
                                seam_span = min(8, extension_width)
                                forward_fraction = 0.5 + 0.5 * (
                                    (distance_from_edge - 1)
                                    / max(1.0, seam_span - 1.0)
                                )
                                selector = (
                                    (
                                        y * 1103515245
                                        + output_x * 12345
                                        + (0 if side == "left" else 2654435761)
                                    )
                                    & 0xFFFF
                                ) / 65535.0
                                if selector >= forward_fraction:
                                    source_value = gray_field.getpixel(
                                        (mirror_field_x, mirror_source_y)
                                    )
                        # The transition has already been aligned by
                        # texture_shift, so copying the real pixel preserves
                        # both its stipple phase and its local tone.  Rebuilding
                        # it from the averaged profile would expose the seam.
                        value = source_value
                        if image.mode == "RGB":
                            texture_pixel = (value, value, value)
                        elif image.mode == "RGBA":
                            texture_pixel = (value, value, value, 255)
                        else:
                            texture_pixel = value
                        column.putpixel((0, y), texture_pixel)
                    elif (
                        0 <= profile_y < height
                        and 0 <= source_y < height
                        and profile_y in texture_row_set
                        and source_y in texture_source_row_set
                        and distance_from_edge <= min(8, extension_width)
                    ):
                        # Even an excluded frame/separator row must meet the
                        # physical page edge without a one-pixel discontinuity.
                        # Preserve it exactly at the seam, then dissolve it
                        # quickly into the clean profile instead of dragging it
                        # through the whole padding field.
                        seam_span = min(8, extension_width)
                        seam_weight = (
                            seam_span - distance_from_edge + 1
                        ) / float(seam_span)
                        source_value = gray_field.getpixel((field_x, source_y))
                        clean_value = clean_monotonic[profile_y]
                        value = max(
                            0,
                            min(
                                255,
                                round(
                                    clean_value * (1.0 - seam_weight)
                                    + source_value * seam_weight
                                ),
                            ),
                        )
                        if image.mode == "RGB":
                            texture_pixel = (value, value, value)
                        elif image.mode == "RGBA":
                            texture_pixel = (value, value, value, 255)
                        else:
                            texture_pixel = value
                        column.putpixel((0, y), texture_pixel)

            extension.paste(column, (output_x, 0))
        return extension if extension.mode == mode else extension.convert(mode)

    period = max(1, depth * 2 - 2)
    span = depth if extension_width > depth else min(depth, extension_width)
    healed = _field_without_edge_ink(
        field,
        direction,
        range(0, span) if side == "left" else range(depth - span, depth),
    )
    for output_x in range(extension_width):
        # Both margins lay the field out in the page's own left-to-right
        # order, so the screentone lattice leans the way the artist drew it.
        # Counting from the page instead would mirror the dots on one side.
        outward = output_x if side == "left" else extension_width - 1 - output_x
        phase = outward % period
        inward = phase if phase < depth else period - phase
        field_x = inward if side == "left" else depth - 1 - inward
        source_x = inward if side == "left" else width - 1 - inward
        target_x = output_x - extension_width if side == "left" else width + output_x
        shift = int(round(slope * (target_x - source_x)))
        column = healed.crop((field_x, 0, field_x + 1, height))
        endpoint_y = 0 if shift >= 0 else height - 1
        extension.paste(
            Image.new(image.mode, (1, height), column.getpixel((0, endpoint_y))),
            (output_x, 0),
        )
        extension.paste(column, (output_x, shift))
    return extension if extension.mode == mode else extension.convert(mode)


def _shared_gradient_plane_slope(image, left_depth, right_depth):
    """Measure one left-to-right tonal-front slope across the whole page."""
    from PIL import Image, ImageFilter

    width, height = image.size
    if width < 2 or left_depth <= 0 or right_depth <= 0:
        return None

    def edge_transition(side, depth):
        sample_width = max(1, min(int(depth), max(2, round(width * 0.008))))
        field = (
            image.crop((0, 0, sample_width, height))
            if side == "left"
            else image.crop((width - sample_width, 0, width, height))
        )
        profile = field.convert("L").resize((1, height), Image.Resampling.BOX)
        profile = profile.filter(
            ImageFilter.GaussianBlur(max(2, int(round(height * 0.006))))
        )
        cap = max(2, min(24, height // 20))
        top = sum(profile.getpixel((0, y)) for y in range(cap)) / cap
        bottom = sum(profile.getpixel((0, height - cap + y)) for y in range(cap)) / cap
        if abs(bottom - top) < 128.0:
            return None
        middle = (top + bottom) / 2.0
        increasing = bottom > top
        crossing = next(
            (
                y
                for y in range(height)
                if (
                    profile.getpixel((0, y)) >= middle
                    if increasing
                    else profile.getpixel((0, y)) <= middle
                )
            ),
            None,
        )
        return crossing, increasing

    left = edge_transition("left", left_depth)
    right = edge_transition("right", right_depth)
    if left is None or right is None or left[1] != right[1]:
        return None
    return max(-3.0, min(3.0, (right[0] - left[0]) / float(width - 1)))


def _gradient_color_axis(image, side):
    """Measure progress between the edge's actual RGB endpoints.

    Luminance alone misses, for example, equally bright blue/green endpoints.
    This scalar proxy is used only for detection and diagonal measurement;
    extension pixels always come from the original image in its own colours.
    """
    import numpy as np
    from PIL import Image

    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    height, width = rgb.shape[:2]
    band = max(2, min(8, round(width * 0.006)))
    cap = max(2, round(height * 0.05))
    edge = rgb[:, :band] if side == "left" else rgb[:, -band:]
    physical_edge = rgb[:, 0] if side == "left" else rgb[:, -1]
    if float(np.min(physical_edge)) >= 232:
        # A thin uninterrupted paper edge separates the margin from the
        # drawing. Averaging a wider band can include the art behind it and
        # manufacture a gradient (Berserk v16 ch115 image103).
        return None
    opposite = rgb[:, -1] if side == "left" else rgb[:, 0]
    if float(np.min(opposite)) >= 232:
        # An uninterrupted paper margin establishes the page outside its
        # frame. A tonal transition on the opposite drawing edge belongs to
        # the panel (Berserk v13 ch84 image084), not to that page margin.
        return None
    top, bottom = [np.median(part, axis=(0, 1)) for part in (edge[:cap], edge[-cap:])]
    delta = bottom - top
    if float(np.max(np.abs(delta))) < 32:
        return None
    solid = _edge_background_candidate(image)
    if solid is not None and (
        min(solid["support"][:2]) >= 0.75
        and max(solid["support"][2:]) >= 0.95
        and solid["held"] >= 0.85
        and solid["share"] >= 0.20
    ):
        # Three edges independently establish a solid page field. Artwork
        # bleeding into a small part of the foot must not turn that field into
        # a colour gradient (Gachiakuta v6 ch46 p1).
        return None
    # Keep the established black/white field path and its ink guards intact.
    if max(float(np.ptp(top)), float(np.ptp(bottom))) <= 8 and (
        (float(np.max(top)) <= 48 and float(np.min(bottom)) >= 232)
        or (float(np.max(bottom)) <= 48 and float(np.min(top)) >= 232)
    ):
        return None
    progress = np.sum((rgb - top) * delta, axis=2) / float(np.dot(delta, delta))
    return Image.fromarray(np.clip(np.rint(progress * 255), 0, 255).astype(np.uint8))


def _background_reference_box(source):
    import json

    box = source.info.get("maic_crop_reference_box")
    try:
        if isinstance(box, str):
            box = json.loads(box)
        left, top, right, bottom = map(int, box)
        if 0 <= left < right <= source.width and 0 <= top < bottom <= source.height:
            return left, top, right, bottom
    except (TypeError, ValueError):
        pass
    return 0, 0, source.width, source.height


def has_gradient_background(image):
    """Whether the uncropped page has a verified field worth preserving."""
    if any(_padding_gradient_side_depths(image).values()):
        return True
    for side in ("left", "right"):
        axis = _gradient_color_axis(image, side)
        if axis is not None and _padding_gradient_side_depths(axis, maximum_step_ratio=0.08).get(side, 0):
            return True
    return False


def _pad_to_canvas(image, canvas, method, fill, edge_padding=False, background_hint=None, background_source=None):
    from PIL import ImageOps

    padded = _pad_to_canvas_base(image, canvas, method, fill, edge_padding, background_hint, background_source)
    if not edge_padding:
        return padded
    fitted = ImageOps.contain(image, canvas, method=method)
    if fitted.width >= canvas[0] or fitted.height != canvas[1]:
        return padded
    center_x, _ = _padding_centering(image, canvas, fill)
    offset = int((canvas[0] - fitted.width) * center_x)
    analysis_source = image
    gradient_reference = fitted
    if background_source is not None:
        _, top, _, bottom = _background_reference_box(background_source)
        analysis_source = background_source.crop((0, top, background_source.width, bottom))
        gradient_reference = None
    for side, x0, width in (("left", 0, offset),
                            ("right", offset + fitted.width, canvas[0] - offset - fitted.width)):
        if width <= 0:
            continue
        axis = _gradient_color_axis(analysis_source, side)
        legacy_plan = None
        if axis is None:
            colors, depths = _horizontal_padding_plan(analysis_source, fill)
            if depths.get("left") and depths.get("right"):
                # Two corroborating black/white fields use the established
                # shared-plane and ink-removal rules. The seam fix is for
                # single-sided repeats, not a replacement for those guards.
                if background_source is None:
                    continue
                legacy_plan = depths
            if background_source is None:
                if colors[0 if side == "left" else 1] == "white" and not (
                    depths.get("left") and depths.get("right")
                ):
                    continue
            # The same validated black/white field path serves manual crops
            # and untouched pages, rather than switching to mirrored repeats.
            axis = analysis_source.convert("L")
        depth = (legacy_plan.get(side, 0) if legacy_plan is not None
                 else _padding_gradient_side_depths(axis, maximum_step_ratio=0.08).get(side, 0))
        if not depth:
            continue
        if gradient_reference is None:
            gradient_reference = _contain_to_height(analysis_source.convert(fitted.mode), canvas, method)
        fitted_axis = axis.resize(gradient_reference.size, method)
        edge_offset = 0.0
        if background_source is not None:
            left, _, right, _ = _background_reference_box(background_source)
            scale = gradient_reference.width / background_source.width
            edge_offset = left * scale if side == "left" else (right - background_source.width) * scale
        shared_slope = None
        if legacy_plan is not None and legacy_plan.get("left_clean") and legacy_plan.get("right_clean"):
            scale = gradient_reference.width / analysis_source.width
            shared_slope = _shared_gradient_plane_slope(
                gradient_reference, round(legacy_plan["left"] * scale), round(legacy_plan["right"] * scale),
            )
        extension = _gradient_side_extension(
            gradient_reference, side, round(depth * gradient_reference.width / analysis_source.width),
            (width, canvas[1]), fitted.mode,
            clean_profile=bool(legacy_plan.get(side + "_clean")) if legacy_plan is not None else True,
            preserve_texture_direction=legacy_plan is None,
            analysis_image=fitted_axis if legacy_plan is None else None,
            slope_override=shared_slope,
            edge_offset=edge_offset,
        )
        if extension is not None:
            padded.paste(extension, (x0, 0))
    return padded


def _pad_to_canvas_base(image, canvas, method, fill, edge_padding=False, background_hint=None, background_source=None):
    """Contain and pad, optionally extending the two side fields separately."""
    from PIL import Image, ImageOps

    canvas = int(canvas[0]), int(canvas[1])
    fitted = ImageOps.contain(image, canvas, method=method)
    if fitted.size == canvas:
        return fitted

    center_x, center_y = _padding_centering(image, canvas, fill)
    offset_x = int((canvas[0] - fitted.width) * center_x)
    offset_y = int((canvas[1] - fitted.height) * center_y)
    padded = Image.new(fitted.mode, canvas, fill)

    if edge_padding and fitted.width < canvas[0] and fitted.height == canvas[1]:
        hard_fields = _hard_field_side_transitions(image) if background_hint is None else None
        if hard_fields is not None:
            fitted = fitted.copy()
            transitions = {}
            for side in ("left", "right"):
                split, top, bottom, reference = hard_fields[side]
                transitions[side] = _hard_field_boundaries(
                    fitted, reference, round(split * fitted.height / image.height),
                    max(2, round(3 * fitted.height / image.height)),
                    top == "white",
                )
            for side in ("left", "right"):
                _, white_edge, _ = transitions[side]
                top_white = hard_fields[side][1] == "white"
                _clean_hard_field_white_seam(
                    fitted, side, white_edge, top_white,
                )
            for side, x0, x1 in (
                ("left", 0, offset_x),
                ("right", offset_x + fitted.width, canvas[0]),
            ):
                _, top, bottom, _ = hard_fields[side]
                split, _, colors = transitions[side]
                padded.paste(top, (x0, 0, x1, split))
                padded.paste(bottom, (x0, split, x1, canvas[1]))
                for row, color in enumerate(colors, split):
                    padded.paste(color, (x0, row, x1, row + 1))
            padded.paste(fitted, (offset_x, offset_y))
            return padded

        (left_fill, right_fill), gradient_depths = _horizontal_padding_plan(image, fill)
        shared_background = _shared_page_background(image)
        if background_hint is not None:
            shared_background = _as_page_color(image, background_hint)
        if shared_background is not None and (
            background_hint is not None or not any(gradient_depths.values())
        ):
            padded.paste(shared_background, (0, 0, canvas[0], canvas[1]))
            reference = fitted
            if background_source is not None:
                _, top, _, bottom = _background_reference_box(background_source)
                scale = fitted.height / (bottom - top)
                # A tiny manual crop must not blow up the entire reference
                # page to billions of pixels just to sample its background.
                scale = min(scale, (16_000_000 / (background_source.width * background_source.height)) ** 0.5)
                reference = background_source.resize((max(1, round(background_source.width * scale)),
                                                      max(1, round(background_source.height * scale))), method)
            fields = _neutral_color_page_fields(reference)
            pool_edges = False
            if not fields:
                fields = _interrupted_page_fields(reference)
                pool_edges = bool(fields)
                if fields:
                    color = Image.new(fitted.mode, (1, 1), shared_background).convert("RGB").getpixel((0, 0))
                    fields = [(side, color) for side, _ in fields]
            if background_hint is not None:
                fields = [
                    (side, shade) for side, shade in fields
                    if max(abs(float(a) - b) for a, b in zip(shade, background_hint)) <= 8
                ]
            if fields:
                reference_background = _as_page_color(
                    reference, Image.new(fitted.mode, (1, 1), shared_background).convert("RGB").getpixel((0, 0)),
                )
                for side, x0, width in (
                    ("left", 0, offset_x),
                    ("right", offset_x + fitted.width, canvas[0] - offset_x - fitted.width),
                ):
                    if width > 0:
                        extension = _textured_page_field_extension(
                            reference, side, width, reference_background, fields, pool_edges=pool_edges,
                            match_seam=background_source is None,
                            output_height=fitted.height,
                        )
                        extension = extension.convert(fitted.mode)
                        padded.paste(extension, (x0, 0))
            padded.paste(fitted, (offset_x, offset_y))
            return padded

        mixed_fields = left_fill != right_fill
        extend_gradients = mixed_fields or bool(
            gradient_depths.get("left") and gradient_depths.get("right")
        )
        if not mixed_fields and not any(gradient_depths.values()):
            left_fill = _solid_dark_side_color(image, "left", left_fill)
            right_fill = _solid_dark_side_color(image, "right", right_fill)
        scaled_gradient_depths = {
            side: round(gradient_depths.get(side, 0) * fitted.width / image.width)
            for side in ("left", "right")
        }
        shared_slope = (
            _shared_gradient_plane_slope(
                fitted,
                scaled_gradient_depths["left"],
                scaled_gradient_depths["right"],
            )
            if gradient_depths.get("left_clean") and gradient_depths.get("right_clean")
            else None
        )
        if offset_x > 0:
            left_extension = (
                _gradient_side_extension(
                    fitted,
                    "left",
                    scaled_gradient_depths["left"],
                    (offset_x, canvas[1]),
                    fitted.mode,
                    clean_profile=bool(gradient_depths.get("left_clean")),
                    slope_override=shared_slope,
                )
                if extend_gradients
                else None
            )
            padded.paste(
                left_extension
                if left_extension is not None
                else Image.new(fitted.mode, (offset_x, canvas[1]), left_fill),
                (0, 0),
            )
        right_start = offset_x + fitted.width
        if right_start < canvas[0]:
            right_width = canvas[0] - right_start
            right_extension = (
                _gradient_side_extension(
                    fitted,
                    "right",
                    scaled_gradient_depths["right"],
                    (right_width, canvas[1]),
                    fitted.mode,
                    clean_profile=bool(gradient_depths.get("right_clean")),
                    slope_override=shared_slope,
                )
                if extend_gradients
                else None
            )
            padded.paste(
                right_extension
                if right_extension is not None
                else Image.new(fitted.mode, (right_width, canvas[1]), right_fill),
                (right_start, 0),
            )

    padded.paste(fitted, (offset_x, offset_y))
    return padded


def resize_to_device(
    image,
    canvas,
    *,
    spread_half=False,
    no_padding=False,
    pad_allowed=True,
    fill="white",
    edge_padding=False,
    background_hint=None,
    background_source=None,
    upscale=True,
    stretch=False,
):
    """Fit a page to the device canvas -- maic's decision, in one place.

    This is the tree ``_maic_patched_resize_image`` applies inside KCC, so both
    paths size pages identically:

    * a spread half is brought to the render height and keeps its own width:
      padding it would put a bar between the two halves where they meet;
    * "no padding" also keeps the page's own proportions at the render height,
      baking no margin pixels;
    * otherwise it is brought down whole and padded out to the full canvas,
      which is what makes every page the same size.

    With ``edge_padding`` the automatic black vote is refined per horizontal
    side: uniform dark fields retain their sampled RGB colour. A sharp
    black/white change preserves its short antialiased transition and black
    tone. A full-bleed side confirmed by a gutter uses the uninterrupted
    side's boundary. A genuinely black field remains black, while a verified mixed
    gradient is extended as a sharp two-dimensional field instead of replaced
    by a flat colour. Padding widths stay balanced, so this changes no
    geometry and the source image remains centred.

    Nothing here takes pixels off the page.  KCC centre-crops a page whose
    ratio is within 1.5% of the device's, to spare it a hairline border down
    one edge, and that cost more than it saved: a page
    arrives here framed the way the crop left it, and a page that lands in
    that band by chance had the preserved margin cut off it -- 6 px of each
    of the top and bottom on a real page carrying 8 -- with nothing showing
    the reader that it happened.  A page is shrunk to the canvas instead.

    ``upscale=False`` returns a page smaller than the canvas untouched, KCC's
    behaviour for its own formats.  The KFX branch of KCC's original
    ``resizeImage`` pads regardless, which is why the shipping KFX build has
    every page at exactly the canvas.
    """
    from PIL import Image, ImageOps

    method = _resize_method(image, canvas)
    if stretch:
        return image.resize(canvas, method)
    if method == Image.Resampling.BICUBIC and not upscale:
        return image
    if spread_half or no_padding:
        return _contain_to_height(image, canvas, method)

    if pad_allowed:
        return _pad_to_canvas(image, canvas, method, fill, edge_padding=edge_padding,
                              background_hint=background_hint, background_source=background_source)
    return ImageOps.contain(image, canvas, method=method)


def pad_to_even(image):
    """Duplicate the last row or column so a spread bisects into equal halves.

    An odd width would otherwise leave the halves one pixel apart in size, and
    they stop butting together cleanly on the page-flip strip.
    """
    from PIL import Image

    width, height = image.size
    if width > height and width % 2:
        extended = Image.new(image.mode, (width + 1, height))
        extended.paste(image, (0, 0))
        extended.paste(image.crop((width - 1, 0, width, height)), (width, 0))
        return extended
    if height > width and height % 2:
        extended = Image.new(image.mode, (width, height + 1))
        extended.paste(image, (0, 0))
        extended.paste(image.crop((0, height - 1, width, height)), (0, height))
        return extended
    return image


def spread_plan(size, canvas, rotate=True):
    """"single", "split" or "rotate" for a page of *size* on a *canvas* device.

    KCC's ``ComicPage.splitCheck`` with the options the KFX path uses (no
    webtoon, no maximizestrips, splitter 0).  A page counts as a spread only
    when it lies the other way round from the device and is more than
    ``SPREAD_MIN_RATIO`` wide; past ``SPREAD_BISECT_MAX_RATIO`` KCC stops
    cutting and rotates instead.

    *rotate* is the "No rotate" option: with it off a panorama is bisected like
    any other spread rather than turned sideways.  It cuts through whatever is
    at the middle, which is what the threshold exists to avoid -- but a reader
    who never wants to tilt their Kindle would rather have the two halves.
    """
    width, height = size
    if not width or not height:
        return "single"
    if (width > height) == (canvas[0] > canvas[1]):
        return "single"
    ratio = float(width) / float(height)
    if ratio <= SPREAD_MIN_RATIO:
        return "single"
    if ratio < SPREAD_BISECT_MAX_RATIO:
        return "split"
    return "rotate" if rotate else "split"


def split_spread(image, righttoleft=True):
    """Bisect a spread, reading half first.

    Right half first for manga: KCC emits it as ``-kcc-b``, which is the page
    the reader turns to before ``-kcc-c``.
    """
    width, height = image.size
    if width > height:
        first = (int(width / 2), 0, width, height)
        second = (0, 0, int(width / 2), height)
    else:
        first = (0, int(height / 2), width, height)
        second = (0, 0, width, int(height / 2))
    if not righttoleft:
        first, second = second, first
    return [image.crop(first), image.crop(second)]


def match_split_join(image, axis, position, band=1):
    """Make pixels on both sides of a split agree, without erasing ink.

    Kindle only offers its small ``Preview Double Page Spread`` button when
    the two inner page edges look like one continuous image.  Device probes
    showed that one pixel per side works for ordinary joins, while a mostly
    black Berserk 10 join needed two pixels in Auto. The darker
    pixel wins, so the pass can only extend existing linework across the cut;
    it never paints a light seam through it.

    ``position`` is the first pixel on the second side of the cut.  Wider
    bands are supported for diagnostics; Auto uses two pixels for joins with
    at least 80% deep black coverage, and one pixel for other corrections.
    Invalid or edge cuts leave the original object untouched.
    """
    from PIL import ImageChops, ImageOps

    width, height = image.size
    axis = str(axis or "").strip().lower()
    try:
        position = int(position)
        band = max(1, int(band))
    except (TypeError, ValueError):
        return image

    if axis == "x":
        band = min(band, position, width - position)
        if band <= 0:
            return image
        before = image.crop((position - band, 0, position, height))
        after = ImageOps.mirror(image.crop((position, 0, position + band, height)))
        shared = ImageChops.darker(before, after)
        out = image.copy()
        out.paste(shared, (position - band, 0))
        out.paste(ImageOps.mirror(shared), (position, 0))
        return out

    if axis == "y":
        band = min(band, position, height - position)
        if band <= 0:
            return image
        before = image.crop((0, position - band, width, position))
        after = ImageOps.flip(image.crop((0, position, width, position + band)))
        shared = ImageChops.darker(before, after)
        out = image.copy()
        out.paste(shared, (0, position - band))
        out.paste(ImageOps.flip(shared), (0, position))
        return out

    return image


def spread_preview_edge_metrics(image, axis, position):
    """Return the two inner-edge signals Kindle appears to care about.

    The thresholds come from the four-page device probe that produced one
    positive control and three false negatives.  ``joint_ink`` is the share of
    positions where both sides contain a non-paper pixel; ``solid_ink`` uses a
    stricter paper cutoff and recognizes a fold densely covered by artwork;
    ``continuity`` is the share whose grey values already agree to within four
    levels. ``deep_black`` catches a nearly featureless black fold: despite
    looking dense and continuous to the older signals, Berserk 04 image070-071
    was device-confirmed not to expose Preview Double Page Spread.
    """
    width, height = image.size
    axis = str(axis or "").strip().lower()
    try:
        position = int(position)
    except (TypeError, ValueError):
        return {
            "joint_ink": 0.0, "solid_ink": 0.0,
            "continuity": 0.0, "deep_black": 0.0,
        }

    if axis == "x" and 0 < position < width:
        before = image.crop((position - 1, 0, position, height)).convert("L").tobytes()
        after = image.crop((position, 0, position + 1, height)).convert("L").tobytes()
    elif axis == "y" and 0 < position < height:
        before = image.crop((0, position - 1, width, position)).convert("L").tobytes()
        after = image.crop((0, position, width, position + 1)).convert("L").tobytes()
    else:
        return {
            "joint_ink": 0.0, "solid_ink": 0.0,
            "continuity": 0.0, "deep_black": 0.0,
        }

    total = max(1, len(before))
    joint_ink = sum(a < 250 and b < 250 for a, b in zip(before, after)) / total
    solid_ink = sum(a < 240 and b < 240 for a, b in zip(before, after)) / total
    continuity = sum(abs(a - b) <= 4 for a, b in zip(before, after)) / total
    deep_black = sum(a < 16 and b < 16 for a, b in zip(before, after)) / total
    return {
        "joint_ink": joint_ink, "solid_ink": solid_ink,
        "continuity": continuity, "deep_black": deep_black,
    }


def spread_preview_likely_from_metrics(metrics):
    """Classify measured inner edges using the accumulated device probes."""
    joint_ink = float(metrics.get("joint_ink", 0.0))
    solid_ink = float(metrics.get("solid_ink", 0.0))
    continuity = float(metrics.get("continuity", 0.0))
    deep_black = float(metrics.get("deep_black", 0.0))
    # Kindle accepts two visibly different joins.  A continuous drawing needs
    # only moderate coverage (Tower Dungeon 85); a densely inked fold does not
    # need neighbouring columns to match (six Usuzumi no Hate 01 positives).
    # A nearly uniform black join is the exception: Berserk 04 image070-071 is
    # 89.5% deep black after resizing and failed on device even though every
    # older signal classified it as likely.  The strongest known positive is
    # only 35% deep black, so 80% keeps this correction deliberately narrow.
    if deep_black >= SPREAD_PREVIEW_DEEP_BLACK_THRESHOLD:
        return False
    return solid_ink >= 0.60 or (joint_ink >= 0.25 and continuity >= 0.80)


def spread_preview_likely(image, axis, position, metrics=None):
    """Whether an untouched join is a high-confidence Kindle positive.

    This deliberately recognizes only the two strong cases observed on device:
    either dense artwork covers the fold, or enough ink crosses it and the two
    edge columns already agree. Ambiguous joins are corrected by Auto mode
    instead of gambling on an undocumented reader heuristic.
    """
    metrics = metrics or spread_preview_edge_metrics(image, axis, position)
    return spread_preview_likely_from_metrics(metrics)


def custom_split_plan(size, canvas, cfg):
    """``(axis, position)`` for a sidecar custom split, or None when it does not apply.

    The user places the cut on the page as they see it; by the time it is used
    the crop has usually made the page smaller, so the position is kept
    relative to the page rather than as a pixel offset.  A page already the
    right way round for the device is left alone, as KCC leaves it.
    """
    if not cfg:
        return None
    width, height = size
    if not width or not height:
        return None
    if (width > height) == (canvas[0] > canvas[1]):
        return None

    axis = str(cfg.get("axis", "") or "").strip().lower()
    if axis not in {"x", "y"}:
        axis = "x" if width >= height else "y"
    total = width if axis == "x" else height
    try:
        source_total = int(cfg.get("width" if axis == "x" else "height", 0) or 0)
    except (TypeError, ValueError):
        source_total = 0
    raw = cfg.get("split", total // 2)
    position = int(raw) if isinstance(raw, (int, float)) else total // 2
    if source_total > 0 and source_total != total:
        position = int(round(float(position) / float(source_total) * float(total)))
    return axis, max(1, min(total - 1, position))


def split_at(image, axis, position, righttoleft=True):
    """Cut a page at *position*, reading half first.

    Unlike an automatic spread the halves are deliberately unequal, so nothing
    is padded to make them match.
    """
    width, height = image.size
    if axis == "x":
        first = (position, 0, width, height)
        second = (0, 0, position, height)
    else:
        first = (0, position, width, height)
        second = (0, 0, width, position)
    if not righttoleft:
        first, second = second, first
    return [image.crop(first), image.crop(second)]


def rotate_page(image, rotate_right=False):
    """Turn a panorama upright, the way KCC's 'R' payload does."""
    from PIL import Image

    return image.rotate(-90 if rotate_right else 90, Image.Resampling.BICUBIC, True)


def iter_images(root):
    """Yield every image file under *root*, as (directory, filename, path)."""
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if os.path.splitext(name.lower())[1] in IMAGE_EXTS:
                yield dirpath, name, os.path.join(dirpath, name)


def apply_exclusions(filetree, excluded_norm, log_fn=None):
    """Delete the pages the user excluded, before anything else looks at them.

    *excluded_norm* holds paths relative to *filetree*; both the original and
    lower-cased spellings are accepted because callers build it either way.
    """
    log = log_fn or _noop_log
    if not excluded_norm:
        return 0

    removed = 0
    for root, _, files in os.walk(filetree, topdown=False):
        for name in files:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, filetree).replace("\\", "/")
            if rel.lower() in excluded_norm or rel in excluded_norm:
                try:
                    os.remove(path)
                    removed += 1
                except Exception:
                    pass
    if removed:
        log(f"  [INFO] Excluded: {removed} files removed from processing")
    return removed


def apply_page_number_cleanup(
    path,
    *,
    method="lama",
    padding=0,
    scope_path="",
    chapter_anchors=(),
    chapter_root=None,
    stop_requested_fn=None,
    log_fn=None,
):
    """Erase printed page numbers, using the same detector as the preview.

    Runs before margin detection: a number sitting in the margin would
    otherwise anchor the crop and keep the margin alive.
    """
    from PIL import Image

    from .autonomous import (
        _load_artifact_profiles,
        apply_maic_page_number_cleanup,
    )

    log = log_fn or _noop_log
    stop = stop_requested_fn or _never_stop

    from .page_number_sequence import PageNumberSequence, page_number_chapter
    from ._native_source import natural_key

    sequence = PageNumberSequence()
    anchors = {(str(folder).replace("\\", "/").strip("/").casefold(), str(stem).casefold())
               for folder, stem in chapter_anchors if stem}
    chapter_segments = {}
    profiles = _load_artifact_profiles("")
    numbers_removed = 0
    pages_touched = 0
    consecutive_errors = 0

    for _, name, file_path in sorted(iter_images(path), key=lambda item: natural_key(item[2])):
        if consecutive_errors >= _MAX_CONSECUTIVE_ERRORS:
            break
        if stop():
            raise UserWarning("Conversion interrupted.")
        try:
            with Image.open(file_path) as opened:
                original = opened.convert("RGB")
            folder = page_number_chapter(file_path)
            relative_folder = os.path.relpath(os.path.dirname(file_path), chapter_root or path)
            relative_folder = "" if relative_folder == "." else relative_folder.replace("\\", "/").casefold()
            stem = os.path.splitext(name)[0].casefold()
            if (relative_folder, stem) in anchors:
                chapter_segments[folder] = stem
            chapter = folder + "|" + chapter_segments.get(folder, "")
            cleaned, removed, _ = apply_maic_page_number_cleanup(
                original,
                artifact_profiles=profiles,
                method=str(method or "lama"),
                padding=max(0, min(100, int(padding))),
                scope_path=scope_path,
                sequence=sequence,
                chapter_key=chapter,
            )
            consecutive_errors = 0
            if not removed:
                continue
            save_in_place(cleaned, file_path)
            numbers_removed += int(removed)
            pages_touched += 1
        except UserWarning:
            raise
        except Exception as exc:
            consecutive_errors += 1
            log(f"  [!] maic page-number cleanup failed: {name}: {exc}")
            if consecutive_errors >= _MAX_CONSECUTIVE_ERRORS:
                log("  [WARN] maic page-number cleanup disabled after 3 consecutive errors")
                break

    log(f"  [maic NUMBERS] Removed: {numbers_removed} from {pages_touched} files")
    return numbers_removed, pages_touched


def apply_margin_crop(
    path,
    *,
    margin_pct=0.0,
    watermarks=False,
    skip_names=(),
    artifact_only_names=None,
    stop_requested_fn=None,
    log_fn=None,
):
    """Trim page margins conservatively.

    *skip_names* are lower-cased file names to leave alone -- pages the user
    marked NoCrop, and pages carrying a custom crop, which must stay in their
    original coordinate space.
    """
    from PIL import Image

    from .autonomous import _load_artifact_profiles, apply_maic_crop

    log = log_fn or _noop_log
    stop = stop_requested_fn or _never_stop
    skip = set(skip_names or ())
    artifact_only = None if artifact_only_names is None else set(artifact_only_names)
    artifact_profiles = _load_artifact_profiles("") if watermarks else None

    cropped_count = 0
    for _, name, file_path in iter_images(path):
        if stop():
            raise UserWarning("Conversion interrupted.")
        if name.lower() in skip:
            continue
        try:
            with Image.open(file_path) as opened:
                original = opened.convert("RGB")
            cropped, _, applied = apply_maic_crop(
                original,
                preserved_margin_percent=margin_pct,
                artifact_profiles=(
                    artifact_profiles
                    if artifact_only is None or name.lower() in artifact_only
                    else None
                ),
            )
            if not applied:
                continue
            save_in_place(cropped, file_path)
            cropped_count += 1
        except UserWarning:
            raise
        except Exception as exc:
            log(f"  [!] maic crop failed: {name}: {exc}")

    if cropped_count:
        log(f"  [maic CROP] Applied: {cropped_count} files")
    return cropped_count


def apply_artifact_cleanup(
    path,
    *,
    padding=2,
    only_names=None,
    stop_requested_fn=None,
    log_fn=None,
):
    """Remove taught watermarks only where a solid local fill is safe."""
    from PIL import Image

    from .autonomous import (
        _load_artifact_profiles,
        _peripheral_artifact_ignore_mask,
        _reference_artifact_cleanup,
    )

    log = log_fn or _noop_log
    stop = stop_requested_fn or _never_stop
    only = None if only_names is None else set(only_names)
    profiles = _load_artifact_profiles("")
    if not profiles:
        return 0, 0

    removed_total = 0
    pages_touched = 0
    for _, name, file_path in iter_images(path):
        if stop():
            raise UserWarning("Conversion interrupted.")
        if only is not None and name.lower() not in only:
            continue
        try:
            with Image.open(file_path) as opened:
                original = opened.convert("RGB")
            _ignore_mask, candidates = _peripheral_artifact_ignore_mask(original, profiles)
            cleaned, removed, _decision = _reference_artifact_cleanup(
                original,
                profiles,
                max(0, min(100, int(padding or 0))),
                candidates,
            )
            if not removed:
                continue
            save_in_place(cleaned, file_path)
            removed_total += int(removed)
            pages_touched += 1
        except UserWarning:
            raise
        except Exception as exc:
            log(f"  [!] Watermark cleanup failed: {name}: {exc}")

    if removed_total:
        log(f"  [maic WATERMARKS] Removed: {removed_total} from {pages_touched} files")
    return removed_total, pages_touched
