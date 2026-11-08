"""KCC runtime helpers used by convert routes and patches."""

from __future__ import annotations

import os
import sys
from typing import Any

from .config import logger, state, state_lock
from .sevenzip import find_7z
from .sidecar import load_sidecar


def is_user_facing_log(msg: str) -> bool:
    s = (msg or "").strip()
    if not s:
        return False
    if bool(state.get("convert_advanced_log", False)):
        return True
    low = s.lower()

    always = ("[err]", "[warn]", "[ok]", "[dir]", "[!]")
    if any(token in low for token in always):
        return True

    user_steps = (
        "working on ",
        "preparing source images",
        "checking images",
        "processing images",
        "creating epub file",
        "creating mobi files",
    )
    if any(token in low for token in user_steps):
        return True

    noisy = (
        "[dbg]",
        "[toc]",
        "[nfo]",
        "kcc args:",
        "nocrop",
        "custom crop",
        "imgfileprocessing:",
        "buildhtml:",
        "makezip time:",
        "makebook:",
        "anchors mapped",
        "external toc mode enabled",
        "rewritten from chapter",
        "expected chapter dirs remapped",
        "chapter-folder fix",
        "saved .sidecar.json",
    )
    if any(token in low for token in noisy):
        return False

    return True


def convert_log(msg: str) -> None:
    if not is_user_facing_log(msg):
        return
    with state_lock:
        state["convert_log"].append(msg)
        if len(state["convert_log"]) > 2000:
            state["convert_log"] = state["convert_log"][-1500:]
    logger.info(f"[KCC] {msg}")


def load_sidecar_for_convert(source: str) -> dict[str, Any]:
    """Load sidecar payload normalized for convert scan endpoint contract."""
    data = load_sidecar(source)
    return {
        "no-crop": set(data.get("no-crop", []) or []),
        "auto-no-crop": set(data.get("auto-no-crop", []) or []),
        "spread-scan": data.get("spread-scan"),
        "custom-crop": data.get("custom-crop", {}) or {},
        "custom-split": data.get("custom-split", {}) or {},
        "excluded": set(data.get("excluded", []) or []),
        "bookmarks": data.get("bookmarks", []) or [],
        "extra-margin": data.get("extra-margin", {}) or {},
        "edit-ops": data.get("edit-ops", {}) or {},
        "watermark-matches": data.get("watermark-matches", []) or [],
        "_watermark-matches-saved": bool(data.get("_watermark-matches-saved", False)),
    }


def _list_archive_images(sz_bin: str, archive_path: str, img_exts: set[str]) -> list[str]:
    """List image paths inside an archive using 7z."""
    import subprocess as _sp

    kwargs: dict[str, Any] = dict(
        capture_output=True, timeout=30, encoding="utf-8", errors="replace",
    )
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000000
    try:
        result = _sp.run([sz_bin, "l", "-slt", "-sccUTF-8", archive_path], **kwargs)
        paths: list[str] = []
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("Path = "):
                p = line[7:].replace("\\", "/")
                if os.path.splitext(p)[1].lower() in img_exts:
                    paths.append(p)
        return paths
    except Exception:
        return []


def get_source_relpaths(source: str) -> set[str]:
    """Return relPath set for all source images (used to filter excluded files)."""
    img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}
    arch_exts = {".zip", ".cbz", ".cbr", ".cb7", ".rar", ".7z"}
    relpaths: set[str] = set()
    if os.path.isdir(source):
        sz2 = find_7z()
        for root, _, fnames in os.walk(source):
            for fn in fnames:
                ext = os.path.splitext(fn)[1].lower()
                fp = os.path.join(root, fn)
                if ext in img_exts:
                    rel = os.path.relpath(fp, source).replace("\\", "/")
                    relpaths.add(rel)
                elif ext in arch_exts and sz2:
                    arch_stem = os.path.splitext(fn)[0]
                    for p in _list_archive_images(sz2, fp, img_exts):
                        relpaths.add(arch_stem + "/" + p)
    elif os.path.isfile(source):
        ext = os.path.splitext(source)[1].lower()
        if ext in arch_exts:
            sz = find_7z()
            if sz:
                for p in _list_archive_images(sz, source, img_exts):
                    relpaths.add(p)
    return relpaths
