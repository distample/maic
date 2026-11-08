"""Validation helpers for convert endpoint payloads."""

from __future__ import annotations

from typing import Any


def _validate_int_option(data: dict[str, Any], field: str, *, min_value: int | None, max_value: int | None):
    raw = data.get(field)
    if raw is None:
        return None
    if isinstance(raw, bool):
        return f"{field} must be an integer"
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return f"{field} must be an integer"
    if min_value is not None and value < min_value:
        return f"{field} must be >= {min_value}"
    if max_value is not None and value > max_value:
        return f"{field} must be <= {max_value}"
    return None


def _validate_float_option(data: dict[str, Any], field: str, *, min_value: float | None, max_value: float | None):
    raw = data.get(field)
    if raw is None:
        return None
    if isinstance(raw, bool):
        return f"{field} must be a number"
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return f"{field} must be a number"
    if min_value is not None and value < min_value:
        return f"{field} must be >= {min_value}"
    if max_value is not None and value > max_value:
        return f"{field} must be <= {max_value}"
    return None


def validate_convert_log_mode_payload(data: dict[str, Any]):
    """Validate `/api/convert/log-mode` payload."""
    if "advanced" in data and not isinstance(data.get("advanced"), bool):
        return False, "advanced must be a boolean"
    return True, None


def validate_convert_start_payload(data: dict[str, Any]):
    """Validate `/api/convert/start` nested structures and numeric ranges."""
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        return False, "sources must be a list"
    for idx, src in enumerate(sources):
        if not isinstance(src, str) or not src.strip():
            return False, f"sources[{idx}] must be a non-empty string"

    per_source_crop = data.get("per_source_crop", {})
    if not isinstance(per_source_crop, dict):
        return False, "per_source_crop must be an object"
    for src, crop_data in per_source_crop.items():
        if not isinstance(src, str) or not src.strip():
            return False, "per_source_crop keys must be non-empty strings"
        if not isinstance(crop_data, dict):
            return False, f"per_source_crop[{src}] must be an object"
        nocrop = crop_data.get("no-crop", [])
        if not isinstance(nocrop, list) or any(not isinstance(item, str) for item in nocrop):
            return False, f"per_source_crop[{src}].no-crop must be a list of strings"
        custom_crop = crop_data.get("custom-crop", {})
        if not isinstance(custom_crop, dict):
            return False, f"per_source_crop[{src}].custom-crop must be an object"
        for rel_path, bounds in custom_crop.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                return False, "custom-crop keys must be non-empty strings"
            if not isinstance(bounds, dict):
                return False, f"custom-crop[{rel_path}] must be an object"
            for key in ("top", "bottom", "left", "right", "width", "height"):
                if key in bounds and not isinstance(bounds[key], (int, float)):
                    return False, f"custom-crop[{rel_path}].{key} must be numeric"
        custom_split = crop_data.get("custom-split", {})
        if not isinstance(custom_split, dict):
            return False, f"per_source_crop[{src}].custom-split must be an object"
        for rel_path, split_cfg in custom_split.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                return False, "custom-split keys must be non-empty strings"
            if not isinstance(split_cfg, dict):
                return False, f"custom-split[{rel_path}] must be an object"
            for key in ("split", "width", "height"):
                if key in split_cfg and not isinstance(split_cfg[key], (int, float)):
                    return False, f"custom-split[{rel_path}].{key} must be numeric"
            if "axis" in split_cfg and str(split_cfg.get("axis", "")).lower() not in {"x", "y"}:
                return False, f"custom-split[{rel_path}].axis must be 'x' or 'y'"

    excluded_files = data.get("excluded_files", [])
    if not isinstance(excluded_files, list) or any(not isinstance(item, str) for item in excluded_files):
        return False, "excluded_files must be a list of strings"

    bookmarks = data.get("bookmarks", {})
    if not isinstance(bookmarks, dict):
        return False, "bookmarks must be an object"
    for key, value in bookmarks.items():
        if not isinstance(key, str):
            return False, "bookmarks keys must be strings"
        if not isinstance(value, str):
            return False, "bookmarks values must be strings"

    if "auto_balance_margins" in data and not isinstance(data.get("auto_balance_margins"), bool):
        return False, "auto_balance_margins must be a boolean"
    if "maic_crop" in data and not isinstance(data.get("maic_crop"), bool):
        return False, "maic_crop must be a boolean"
    if "maic_watermarks" in data and not isinstance(data.get("maic_watermarks"), bool):
        return False, "maic_watermarks must be a boolean"
    if "maic_page_numbers" in data and not isinstance(data.get("maic_page_numbers"), bool):
        return False, "maic_page_numbers must be a boolean"
    if "scan_cleanup" in data and not isinstance(data.get("scan_cleanup"), bool):
        return False, "scan_cleanup must be a boolean"
    if "facing_pages" in data and not isinstance(data.get("facing_pages"), bool):
        return False, "facing_pages must be a boolean"
    if "force_spread_preview" in data and not isinstance(data.get("force_spread_preview"), bool):
        return False, "force_spread_preview must be a boolean"
    if "spread_preview_mode" in data:
        err = _validate_int_option(data, "spread_preview_mode", min_value=0, max_value=2)
        if err:
            return False, err
    if "maic_margin_pct" in data:
        err = _validate_float_option(data, "maic_margin_pct", min_value=0.0, max_value=10.0)
        if err:
            return False, err
    if "cleanup_method" in data and str(data.get("cleanup_method", "")).lower() not in {"white", "inpaint", "lama"}:
        return False, "cleanup_method must be one of: white, inpaint, lama"
    if "cleanup_padding" in data:
        err = _validate_int_option(data, "cleanup_padding", min_value=0, max_value=100)
        if err:
            return False, err
    if "auto_balance_margin_px" in data:
        err = _validate_int_option(data, "auto_balance_margin_px", min_value=0, max_value=2000)
        if err:
            return False, err
    if "auto_balance_margin_unit" in data:
        unit = str(data.get("auto_balance_margin_unit", "") or "").strip().lower()
        if unit not in {"px", "pct"}:
            return False, "auto_balance_margin_unit must be one of: px, pct"
    if "auto_balance_margin_pct" in data:
        err = _validate_float_option(data, "auto_balance_margin_pct", min_value=0.0, max_value=100.0)
        if err:
            return False, err
    if "kindle_doc_type" in data:
        kdt = str(data.get("kindle_doc_type", "") or "").strip().lower()
        if kdt not in {"auto", "pdoc", "ebok"}:
            return False, "kindle_doc_type must be one of: auto, pdoc, ebok"

    numeric_specs = (
        ("preserve_margin_h", 0, 100),
        ("preserve_margin_v", 0, 100),
        ("splitter", 0, 2),
        ("metadata_title", 0, 2),
        ("jpeg_quality", 1, 100),
        ("chunk_size", 0, 2000),
        ("custom_width", 0, 20000),
        ("custom_height", 0, 20000),
        ("batch_split", 0, 10),
        ("inter_panel_crop", 0, 100),
        # Off / fast (MangaJaNai) / exact (JPEG cleanup + Manga Ora).
        ("manga_upscale", 0, 2),
    )
    for field, min_value, max_value in numeric_specs:
        error = _validate_int_option(data, field, min_value=min_value, max_value=max_value)
        if error:
            return False, error

    float_specs = (
        ("cropping_power", 0.1, 10.0),
        ("gamma", 0.0, 10.0),
    )
    for field, fmin, fmax in float_specs:
        error = _validate_float_option(data, field, min_value=fmin, max_value=fmax)
        if error:
            return False, error

    return True, None
