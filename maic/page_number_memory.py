"""Persistent user-taught page-number examples scoped to a manga series."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid
from typing import Any

from PIL import Image

from .config import DATA_DIR


PAGE_NUMBER_MEMORY_DIR = os.path.join(DATA_DIR, "page_number_examples")
_memory_lock = threading.RLock()
_memory_cache: dict[str, tuple[int, list[dict[str, Any]]]] = {}


def _volume_like_name(value: str) -> bool:
    name = os.path.splitext(str(value or ""))[0].strip().casefold()
    return bool(
        re.search(
            r"(?:^|[-_.\s])(?:v|vol|volume|том)?\s*\d{1,4}"
            r"(?:[-_.\s]*(?:clean|cleaned))?$",
            name,
        )
        or re.match(r"^(?:v|vol|volume|том)[-_.\s]*\d+", name)
    )


def page_number_scope(scope_path: str) -> dict[str, str]:
    """Return a stable per-series scope shared by sibling volume sources."""
    raw = str(scope_path or "").split("||", 1)[0]
    resolved = os.path.realpath(raw) if raw else ""
    if not resolved:
        resolved = os.path.realpath(os.getcwd())
    source_name = os.path.basename(resolved.rstrip("\\/"))
    if os.path.isfile(resolved):
        source_name = os.path.splitext(source_name)[0]
    series_root = os.path.dirname(resolved) if _volume_like_name(source_name) else resolved
    normalized = os.path.normcase(os.path.realpath(series_root))
    scope_id = hashlib.sha1(normalized.encode("utf-8", errors="surrogatepass")).hexdigest()[:20]
    label = os.path.basename(series_root.rstrip("\\/")) or source_name or "Manga"
    return {"id": scope_id, "label": label[:120], "root": series_root}


def page_digest(image: Image.Image) -> str:
    """Create a resize-stable fingerprint for exact-page feedback overrides."""
    grayscale = image.convert("L").resize((64, 64), getattr(Image.Resampling, "BILINEAR", Image.BILINEAR))
    return hashlib.sha1(grayscale.tobytes()).hexdigest()


def _scope_dir(scope_path: str) -> tuple[dict[str, str], str]:
    scope = page_number_scope(scope_path)
    return scope, os.path.join(PAGE_NUMBER_MEMORY_DIR, scope["id"])


def _manifest_path(scope_path: str) -> tuple[dict[str, str], str, str]:
    scope, directory = _scope_dir(scope_path)
    return scope, directory, os.path.join(directory, "manifest.json")


def _read_manifest(scope_path: str) -> tuple[dict[str, str], list[dict[str, Any]], int]:
    scope, directory, manifest_path = _manifest_path(scope_path)
    try:
        revision = os.stat(manifest_path).st_mtime_ns
    except OSError:
        return scope, [], 0
    cached = _memory_cache.get(scope["id"])
    if cached is not None and cached[0] == revision:
        return scope, [dict(item) for item in cached[1]], revision
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError, TypeError):
        return scope, [], revision
    entries = raw.get("examples", []) if isinstance(raw, dict) else []
    cleaned = []
    for item in entries if isinstance(entries, list) else []:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "")
        reference_name = os.path.basename(str(item.get("reference") or ""))
        if action not in {"number", "not_number"} or not reference_name:
            continue
        candidate = dict(item)
        candidate["referencePath"] = os.path.join(directory, "references", reference_name)
        cleaned.append(candidate)
    _memory_cache[scope["id"]] = (revision, [dict(item) for item in cleaned])
    return scope, cleaned, revision


def load_page_number_examples(scope_path: str, *, include_images: bool = True) -> tuple[list[dict[str, Any]], int]:
    """Load examples for recognition; damaged references are ignored."""
    with _memory_lock:
        _scope, entries, revision = _read_manifest(scope_path)
        result = []
        for entry in entries:
            item = dict(entry)
            if include_images:
                try:
                    with Image.open(item["referencePath"]) as opened:
                        item["referenceImage"] = opened.convert("RGB").copy()
                except Exception:
                    continue
            result.append(item)
        return result, revision


def page_number_memory_metadata(scope_path: str) -> dict[str, Any]:
    scope, entries, revision = _read_manifest(scope_path)
    positive = sum(1 for item in entries if item.get("action") == "number")
    negative = sum(1 for item in entries if item.get("action") == "not_number")
    return {
        "scope": {"id": scope["id"], "label": scope["label"]},
        "positiveCount": positive,
        "negativeCount": negative,
        "total": positive + negative,
        "revision": str(revision),
        "examples": [
            {
                "id": str(item.get("id") or ""),
                "action": item.get("action"),
                "digits": str(item.get("digits") or ""),
                "createdAt": item.get("createdAt"),
                "sourceName": item.get("sourceName"),
            }
            for item in entries
        ],
    }


def save_page_number_example(
    image: Image.Image,
    box: list[int],
    *,
    scope_path: str,
    action: str,
    digits: str = "",
    source_name: str = "",
) -> dict[str, Any]:
    """Persist one explicit user label and its normalized location metadata."""
    action = str(action or "").lower()
    digits = str(digits or "").strip()
    if action not in {"number", "not_number"}:
        raise ValueError("Invalid page-number example action")
    if action == "number" and (not digits.isascii() or not digits.isdecimal() or not 1 <= len(digits) <= 4):
        raise ValueError("Number examples require one to four digits")
    width, height = image.size
    x1, y1, x2, y2 = [int(value) for value in box]
    x1, y1 = max(0, min(width - 1, x1)), max(0, min(height - 1, y1))
    x2, y2 = max(x1 + 1, min(width, x2)), max(y1 + 1, min(height, y2))
    if x2 - x1 < 3 or y2 - y1 < 3:
        raise ValueError("Selected number area is too small")
    if (x2 - x1) * (y2 - y1) > width * height * 0.05:
        raise ValueError("Selected number area is too large")

    with _memory_lock:
        scope, directory, manifest_path = _manifest_path(scope_path)
        _loaded_scope, entries, _revision = _read_manifest(scope_path)
        if len(entries) >= 256:
            raise ValueError("Page-number example limit reached for this manga")
        references_dir = os.path.join(directory, "references")
        os.makedirs(references_dir, exist_ok=True)
        example_id = uuid.uuid4().hex
        reference_name = f"{example_id}.png"
        image.crop((x1, y1, x2, y2)).save(
            os.path.join(references_dir, reference_name), format="PNG", optimize=True
        )
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        entry = {
            "id": example_id,
            "action": action,
            "digits": digits if action == "number" else "",
            "reference": reference_name,
            "createdAt": now,
            "sourceName": os.path.basename(str(source_name or ""))[:160],
            "pageDigest": page_digest(image),
            "box": [x1, y1, x2, y2],
            "sourceSize": [width, height],
            "centerXRatio": round(((x1 + x2) / 2) / width, 6),
            "centerYRatio": round(((y1 + y2) / 2) / height, 6),
            "widthRatio": round((x2 - x1) / width, 6),
            "heightRatio": round((y2 - y1) / height, 6),
        }
        serializable = []
        for old in entries:
            item = {key: value for key, value in old.items() if key not in {"referencePath", "referenceImage"}}
            serializable.append(item)
        serializable.append(entry)
        payload = {
            "version": 1,
            "scope": {"id": scope["id"], "label": scope["label"]},
            "updatedAt": now,
            "examples": serializable,
        }
        os.makedirs(directory, exist_ok=True)
        temporary = manifest_path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, manifest_path)
        _memory_cache.pop(scope["id"], None)
        metadata = page_number_memory_metadata(scope_path)
        return {
            "id": example_id,
            "action": action,
            "digits": entry["digits"],
            "box": entry["box"],
            "scope": metadata["scope"],
            "revision": metadata["revision"],
            "positiveCount": metadata["positiveCount"],
            "negativeCount": metadata["negativeCount"],
        }


def delete_page_number_example(scope_path: str, example_id: str) -> bool:
    """Delete one user example, keeping the operation recoverable via source."""
    value = str(example_id or "").lower()
    if len(value) != 32 or any(character not in "0123456789abcdef" for character in value):
        return False
    with _memory_lock:
        scope, directory, manifest_path = _manifest_path(scope_path)
        _loaded_scope, entries, _revision = _read_manifest(scope_path)
        removed = next((item for item in entries if item.get("id") == value), None)
        if removed is None:
            return False
        remaining = [item for item in entries if item.get("id") != value]
        payload = {
            "version": 1,
            "scope": {"id": scope["id"], "label": scope["label"]},
            "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "examples": [
                {key: val for key, val in item.items() if key not in {"referencePath", "referenceImage"}}
                for item in remaining
            ],
        }
        temporary = manifest_path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, manifest_path)
        try:
            os.remove(os.path.join(directory, "references", os.path.basename(str(removed.get("reference") or ""))))
        except OSError:
            pass
        _memory_cache.pop(scope["id"], None)
        return True
