"""Shared request parsing helpers used by route modules."""

from __future__ import annotations

import os
from typing import Any

from flask import request

from . import error_codes as EC
from .api_errors import fail


def json_body() -> dict[str, Any]:
    """Return request JSON as a dict, falling back to empty dict."""
    data = request.get_json(silent=True) or {}
    if isinstance(data, dict):
        return data
    return {}


def as_float(value: Any, default: float) -> float:
    """Best-effort float conversion with fallback."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int) -> int:
    """Best-effort int conversion with fallback."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_bool(value: Any, default: bool = False) -> bool:
    """Parse common textual boolean values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def require_path_exists(path: str | None, *, code: str = "PATH_NOT_FOUND"):
    """Validate path presence and existence, returning fail response tuple on error."""
    if not path:
        return False, fail("Path is required", code=code)
    if not isinstance(path, str):
        return False, fail("Path must be a string", code=EC.INVALID_PATH)
    if not path.strip():
        return False, fail("Path is required", code=code)
    if not os.path.exists(path):
        return False, fail("Path not found", code=code)
    return True, None


def require_non_empty_str(value: Any, *, field: str, code: str):
    """Validate required non-empty string field."""
    if not isinstance(value, str) or not value.strip():
        return False, fail(f"{field} is required", code=code)
    return True, None
