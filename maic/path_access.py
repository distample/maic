"""Path access guards for traversal and file-serving safety checks."""

from __future__ import annotations

import os
from typing import Iterable

from .config import IMAGE_EXTS


def _real(path: str) -> str:
    """Return canonical absolute path used for security comparisons."""
    return os.path.realpath(os.path.abspath(path))


def add_allowed_root(state_obj: dict, path: str, root_key: str = "allowed_read_roots") -> None:
    """Register file/dir parent as trusted root for read/write endpoint guards."""
    if not isinstance(path, str) or not path:
        return
    root = _real(path if os.path.isdir(path) else os.path.dirname(path))
    roots = state_obj.setdefault(root_key, [])
    if root and root not in roots:
        roots.append(root)


def is_under_allowed_root(path: str, roots: Iterable[str]) -> bool:
    """Check whether path is contained by at least one configured root."""
    if not path:
        return False
    rp = _real(path)
    for root in roots:
        rr = _real(root)
        try:
            if os.path.commonpath([rp, rr]) == rr:
                return True
        except ValueError:
            # Different drives on Windows.
            continue
    return False


def is_allowed_image_file(path: str, roots: Iterable[str]) -> bool:
    """Guard regular image file reads by extension and trusted root."""
    ext = os.path.splitext(path)[1].lower()
    return ext in IMAGE_EXTS and os.path.isfile(path) and is_under_allowed_root(path, roots)


def is_safe_archive_internal_path(internal: str) -> bool:
    """Reject traversal/absolute archive member selectors."""
    if not isinstance(internal, str) or not internal:
        return False
    if "\x00" in internal:
        return False
    normalized = internal.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("../"):
        return False
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        return False
    if os.path.splitdrive(normalized)[0]:
        return False
    return True
