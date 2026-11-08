"""Chapter names remembered on disk beside a manga source.

One file per manga, written to the same directory the sidecar uses, so every
volume folder sitting under it reads and writes the same list. A volume added
to the converter months later finds the names its siblings already fetched.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

CHAPTER_NAMES_FILE = "chapter_names.json"


class ChapterNamesError(Exception):
    """The stored file exists but cannot be understood."""


def get_chapter_names_path(source: str) -> str:
    """Return the shared chapter-name file for a source, beside its folder."""
    parent = os.path.dirname((source or "").rstrip("/\\")) or "."
    return os.path.join(parent, CHAPTER_NAMES_FILE)


def _tidy_number(value: Any) -> int | float:
    """Write 36 rather than 36.0, while 12.5 stays as it is."""
    number = float(value)
    return int(number) if number.is_integer() else number


def _clean_volume(value: Any) -> int | None:
    """Return a whole volume number, or None when the page named none."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def group_by_volume(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group flat chapters under their volumes, ascending, unknown volume last."""
    buckets: dict[int | None, list[dict[str, Any]]] = {}
    for chapter in chapters:
        buckets.setdefault(_clean_volume(chapter.get("volume")), []).append(
            {
                "number": _tidy_number(chapter.get("number", 0)),
                "label": chapter.get("label", "") or "",
                "title": chapter.get("title", "") or "",
            }
        )
    ordered: list[int | None] = sorted(v for v in buckets if v is not None)
    if None in buckets:
        ordered.append(None)
    return [
        {"volume": volume, "chapters": sorted(buckets[volume], key=lambda c: c["number"])}
        for volume in ordered
    ]


def flatten_volumes(volumes: Any) -> list[dict[str, Any]]:
    """Return the chapters of every volume, each carrying its volume back."""
    chapters: list[dict[str, Any]] = []
    for group in volumes or []:
        if not isinstance(group, dict):
            continue
        volume = _clean_volume(group.get("volume"))
        for chapter in group.get("chapters", []) or []:
            if not isinstance(chapter, dict):
                continue
            chapters.append(
                {
                    "number": _tidy_number(chapter.get("number", 0)),
                    "label": chapter.get("label", "") or "",
                    "title": chapter.get("title", "") or "",
                    "volume": volume,
                }
            )
    return chapters


def _chapter_key(chapter: dict[str, Any]) -> tuple[int | None, int | float]:
    """Identify a chapter: numbers restart per volume on some sites."""
    return (_clean_volume(chapter.get("volume")), _tidy_number(chapter["number"]))


def merge_chapters(
    existing: list[dict[str, Any]], incoming: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Fold a fresh scrape into what is stored; the fresh row wins per chapter.

    Order is not settled here: `group_by_volume` is the single ordering
    authority downstream. A row the page no longer lists is kept regardless —
    including one stored without a volume before the page's volumes were
    read — so the None-volume group can go on accumulating.
    """
    by_key = {_chapter_key(chapter): chapter for chapter in existing}
    for chapter in incoming:
        by_key[_chapter_key(chapter)] = chapter
    return list(by_key.values())


def load_chapter_names(source: str) -> dict[str, Any]:
    """Read the stored chapter names for a source.

    Raises `ChapterNamesError` when the file is there but unreadable, so a
    hand-edited file with a typo is reported rather than quietly replaced.
    """
    path = get_chapter_names_path(source)
    if not os.path.isfile(path):
        return {"exists": False, "path": path, "url": "", "updated": "", "chapters": []}
    try:
        with open(path, encoding="utf-8") as handle:
            stored = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ChapterNamesError("%s cannot be read: %s" % (CHAPTER_NAMES_FILE, exc)) from exc
    if not isinstance(stored, dict):
        raise ChapterNamesError("%s does not hold an object" % CHAPTER_NAMES_FILE)
    return {
        "exists": True,
        "path": path,
        "url": str(stored.get("url", "") or ""),
        "updated": str(stored.get("updated", "") or ""),
        "chapters": flatten_volumes(stored.get("volumes", [])),
    }


def save_chapter_names(source: str, chapters: list[dict[str, Any]], url: str) -> str:
    """Merge a scrape into the stored file and return where it was written."""
    path = get_chapter_names_path(source)
    merged = merge_chapters(load_chapter_names(source)["chapters"], chapters)
    payload = {
        "url": url or "",
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "volumes": group_by_volume(merged),
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path
