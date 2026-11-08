"""Structured runtime logging helpers."""

from __future__ import annotations

from typing import Any


def log_event(
    logger: Any,
    message: str,
    *,
    component: str,
    phase: str | None = None,
    job_id: str | None = None,
    level: str = "info",
    **fields: Any,
) -> None:
    """Log a message with compact structured context prefix."""
    parts = [f"component={component}"]
    if phase:
        parts.append(f"phase={phase}")
    if job_id:
        parts.append(f"job_id={job_id}")
    for key in sorted(fields.keys()):
        value = fields[key]
        if value is not None:
            parts.append(f"{key}={value}")
    payload = f"[CTX] {' '.join(parts)} | {message}"
    log_fn = getattr(logger, level, logger.info)
    log_fn(payload)
