"""Persistent user settings stored in a local config file."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Any

_SETTINGS_LOCK = threading.RLock()

DEFAULT_SETTINGS: dict[str, Any] = {
    "device": "cpu",
    "model_path": "",
    "port": 5847,
    "convert_output_dir": "",
    "clean_output_dir": "",
}


def get_settings_dir() -> str:
    """Return OS-specific settings directory."""
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return os.path.join(appdata, "MangaAICleaner")
    return os.path.join(os.path.expanduser("~"), ".config", "manga_ai_cleaner")


def get_settings_path() -> str:
    return os.path.join(get_settings_dir(), "settings.json")


def load_settings() -> dict[str, Any]:
    """Load settings file with defaults fallback."""
    path = get_settings_path()
    with _SETTINGS_LOCK:
        settings = dict(DEFAULT_SETTINGS)
        if not os.path.isfile(path):
            return settings
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                settings.update(data)
        except Exception:
            return settings
        return settings


def save_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Merge and atomically persist settings."""
    with _SETTINGS_LOCK:
        settings = load_settings()
        settings.update(updates)
        settings_dir = get_settings_dir()
        os.makedirs(settings_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix="settings_", suffix=".json", dir=settings_dir)
        os.close(fd)
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2, sort_keys=True)
            os.replace(tmp_path, get_settings_path())
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        return settings
