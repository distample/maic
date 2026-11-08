"""Helpers for consistent API error payloads with backward compatibility."""

from __future__ import annotations

from flask import jsonify


def fail(message: str, code: str = "BAD_REQUEST", status: int = 400, **extra):
    """Standardized failed response with legacy `error` string retained."""
    payload = {
        "ok": False,
        "error": message,
        "error_obj": {"code": code, "message": message},
    }
    payload.update(extra)
    return jsonify(payload), status
