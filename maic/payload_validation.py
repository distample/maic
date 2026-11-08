"""DTO-style payload validators for non-convert API routes."""

from __future__ import annotations

import re
from typing import Any


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_batch_detect_payload(data: dict[str, Any]):
    """Validate `/api/batch/detect` payload."""
    files = data.get("files", [])
    if not isinstance(files, list):
        return False, "files must be a list"
    for idx, item in enumerate(files):
        if not isinstance(item, dict):
            return False, f"files[{idx}] must be an object"
        if not _is_non_empty_str(item.get("path")):
            return False, f"files[{idx}].path must be a non-empty string"
    return True, None


def validate_batch_clean_payload(data: dict[str, Any]):
    """Validate `/api/batch/clean` payload."""
    all_files = data.get("all_files", [])
    if not isinstance(all_files, list):
        return False, "all_files must be a list"
    for idx, item in enumerate(all_files):
        if not isinstance(item, dict):
            return False, f"all_files[{idx}] must be an object"
        if not _is_non_empty_str(item.get("path")):
            return False, f"all_files[{idx}].path must be a non-empty string"
    return True, None


def validate_comicinfo_write_payload(data: dict[str, Any]):
    """Validate `/api/comicinfo/write` payload shape."""
    fields = data.get("fields", {})
    if not isinstance(fields, dict):
        return False, "fields must be an object"
    bookmarks = data.get("bookmarks", [])
    if not isinstance(bookmarks, list):
        return False, "bookmarks must be a list"
    return True, None


def validate_crop_sidecar_save_payload(data: dict[str, Any]):
    """Validate `/api/crop-sidecar/save` payload shape."""
    nocrop = data.get("no-crop", [])
    if not isinstance(nocrop, list) or any(not isinstance(item, str) for item in nocrop):
        return False, "no-crop must be a list of strings"

    custom_crops = data.get("custom-crop", {})
    if not isinstance(custom_crops, dict):
        return False, "custom-crop must be an object"
    for rel_path, bounds in custom_crops.items():
        if not _is_non_empty_str(rel_path):
            return False, "custom-crop keys must be non-empty strings"
        if not isinstance(bounds, dict):
            return False, f"custom-crop[{rel_path}] must be an object"

    custom_splits = data.get("custom-split", {})
    if not isinstance(custom_splits, dict):
        return False, "custom-split must be an object"
    for rel_path, split_cfg in custom_splits.items():
        if not _is_non_empty_str(rel_path):
            return False, "custom-split keys must be non-empty strings"
        if not isinstance(split_cfg, dict):
            return False, f"custom-split[{rel_path}] must be an object"
        for key in ("split", "width", "height"):
            if key in split_cfg and not isinstance(split_cfg[key], (int, float)):
                return False, f"custom-split[{rel_path}].{key} must be numeric"
        if "axis" in split_cfg and str(split_cfg.get("axis", "")).lower() not in {"x", "y"}:
            return False, f"custom-split[{rel_path}].axis must be 'x' or 'y'"

    excluded = data.get("excluded", [])
    if not isinstance(excluded, list) or any(not isinstance(item, str) for item in excluded):
        return False, "excluded must be a list of strings"

    bookmarks = data.get("bookmarks", None)
    if bookmarks is not None:
        if not isinstance(bookmarks, list):
            return False, "bookmarks must be a list"
        for idx, item in enumerate(bookmarks):
            if not isinstance(item, dict):
                return False, f"bookmarks[{idx}] must be an object"

    extra_margin = data.get("extra-margin", None)
    if extra_margin is not None:
        if not isinstance(extra_margin, dict):
            return False, "extra-margin must be an object"
        for rel_path, margins in extra_margin.items():
            if not _is_non_empty_str(rel_path):
                return False, "extra-margin keys must be non-empty strings"
            if not isinstance(margins, dict):
                return False, f"extra-margin[{rel_path}] must be an object"
            for side in ("top", "bottom", "left", "right"):
                if side in margins and not isinstance(margins[side], (int, float)):
                    return False, f"extra-margin[{rel_path}].{side} must be numeric"

    edit_ops = data.get("edit-ops", None)
    if edit_ops is not None:
        if not isinstance(edit_ops, dict):
            return False, "edit-ops must be an object"
        for rel_path, ops in edit_ops.items():
            if not _is_non_empty_str(rel_path):
                return False, "edit-ops keys must be non-empty strings"
            if not isinstance(ops, list):
                return False, f"edit-ops[{rel_path}] must be a list"

    watermark_matches = data.get("watermark-matches", None)
    if watermark_matches is not None:
        if not isinstance(watermark_matches, list) or any(
            not isinstance(item, str) for item in watermark_matches
        ):
            return False, "watermark-matches must be a list of strings"

    return True, None


def validate_presets_save_payload(data: dict[str, Any]):
    """Validate `/api/presets/save` payload shape."""
    payload = data.get("data", {})
    if not isinstance(payload, dict):
        return False, "data must be an object"
    return True, None


def validate_detect_path_payload(data: dict[str, Any]):
    """Validate `/api/detect-path` payload shape."""
    path = data.get("path", "")
    if not _is_non_empty_str(path):
        return False, "path must be a non-empty string"
    return True, None


def validate_file_mtimes_payload(data: dict[str, Any]):
    """Validate `/api/file-mtimes` payload shape."""
    paths = data.get("paths", [])
    if not isinstance(paths, list):
        return False, "paths must be a list"
    for idx, path in enumerate(paths):
        if not isinstance(path, str):
            return False, f"paths[{idx}] must be a string"
    return True, None


def validate_browse_source_payload(data: dict[str, Any]):
    """Validate `/api/browse-source` payload shape."""
    source_type = data.get("type", "folder")
    if source_type not in {"folder", "file"}:
        return False, "type must be either 'folder' or 'file'"
    exts = data.get("extensions", "*.zip *.cbz *.cbr *.cb7 *.rar *.7z *.pdf")
    if not isinstance(exts, str):
        return False, "extensions must be a string"
    if not isinstance(data.get("multiple", False), bool):
        return False, "multiple must be a boolean"
    return True, None


def validate_scan_folder_payload(data: dict[str, Any]):
    """Validate `/api/scan-folder` payload shape."""
    path = data.get("path", "")
    if not _is_non_empty_str(path):
        return False, "path must be a non-empty string"
    return True, None


def validate_toc_scrape_payload(data: dict[str, Any]):
    """Validate `/api/toc/scrape` payload shape."""
    url = data.get("url")
    if not _is_non_empty_str(url):
        return False, "url must be a non-empty string"
    if not re.match(r"^https?://", url.strip(), re.IGNORECASE):
        return False, "url must start with http:// or https://"
    return True, None
