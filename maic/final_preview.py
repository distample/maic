"""Render native page geometry through the conversion page builder."""

import base64
import os
import tempfile

from .validation import as_bool, as_float, as_int


def render_final_preview(image_bytes, options):
    from ._image_pipeline import page_render_canvas
    from ._page_groups import _pages_from_file
    from .autonomous import _load_artifact_profiles

    width = as_int(options.get("profile_width"), 0)
    height = as_int(options.get("profile_height"), 0)
    if not (1 <= width <= 10000 and 1 <= height <= 10000):
        raise ValueError("Select a device profile first")
    processing = not as_bool(options.get("no_processing", False))
    if as_bool(options.get("hq", False)):
        width, height = int(width * 1.5), int(height * 1.5)
    cover = as_bool(options.get("is_cover", False))
    watermarks = processing and as_bool(options.get("maic_watermarks", False))
    numbers = processing and not cover and as_bool(options.get("maic_page_numbers", False))
    profiles = _load_artifact_profiles("") if watermarks or numbers else []
    padding = max(0, min(100, as_int(options.get("cleanup_padding"), 2)))
    color = str(options.get("borders_color") or "none")
    if color not in {"none", "white", "black"}:
        color = "none"
    # Use the same native builder, including its crop, split and edge-padding
    # rules. Neural restoration is deliberately omitted from interactive previews.
    with tempfile.TemporaryDirectory(prefix="maic-final-preview-") as directory:
        path = os.path.join(directory, "page.img")
        with open(path, "wb") as handle:
            handle.write(image_bytes)
        pages = _pages_from_file(
            path, "page", canvas=page_render_canvas((width, height)),
            resize=processing, no_padding=cover or as_bool(options.get("no_padding", False)),
            righttoleft=as_bool(options.get("manga_mode", False)),
            split_spreads=processing and not cover,
            rotate_spreads=not as_bool(options.get("no_rotate", False)),
            spread_preview_mode=max(0, min(2, as_int(options.get("spread_preview_mode"), 1))),
            borders_color=color, upscale=True, quality=90,
            grayscale=processing and not as_bool(options.get("force_color", False)),
            crop=processing and not cover and as_bool(options.get("maic_crop", False)),
            margin_pct=max(0, min(10, as_float(options.get("maic_margin_pct"), 0.6))),
            custom_crop=options.get("custom_crop") if processing else None,
            custom_split=options.get("custom_split") if processing and not cover else None,
            extra_margin=options.get("extra_margin") if processing else None,
            edit_ops=options.get("edit_ops") if processing else None,
            artifact_profiles=profiles if watermarks and as_bool(options.get("maic_watermark_page_enabled", True)) else None,
            artifact_cleanup={"profiles": profiles, "padding": padding} if (
                watermarks and not cover and as_bool(options.get("maic_watermark_page_enabled", True))
            ) else None,
            cleanup={"profiles": profiles, "padding": padding,
                     "method": "fill", "scope_path": str(options.get("page_number_scope") or ""),
                     "minimum_page_number": options.get("minimum_page_number", 1)}
            if numbers else None,
            build_previews=False,
        )
    return {"ok": True, "pages": [
        {"width": page["width"], "height": page["height"],
         "url": "data:image/jpeg;base64," + base64.b64encode(page["data"]).decode("ascii")}
        for page in pages
    ]}
