"""
Unified sidecar storage for per-book settings.

Stored next to the source as:
  Folder:  <folder>/<foldername>.sidecar.json
  Archive: <dir>/<archivename>.sidecar.json

Keys:
  - "no-crop": [relPath, ...]
  - "auto-no-crop": [relPath, ...]   pages the spread scan has already offered
    No Crop to, so one un-marked by hand is never marked again
  - "custom-crop": {relPath: {top,bottom,left,right,width,height}, ...}
  - "custom-split": {relPath: {split,width,height,axis}, ...}
  - "excluded": [relPath, ...]
  - "bookmarks": [{"relPath": "...", "name": "..."}, ...]
  - "extra-margin": {relPath: {top,bottom,left,right}, ...}
  - "edit-ops": {relPath: [{type,x,y,w,h,color,...}, ...], ...}
  - "watermark-matches": [relPath, ...]  detected pages shown in the conversion UI
  - "spread-scan": {fingerprint, spreads}  completed detection for unchanged pages
"""
from __future__ import annotations

import logging
import os
import json
from typing import Any

logger = logging.getLogger("MangaAICleaner")


def _source_base(source: str) -> str:
    """Return stable base name for a folder or archive path."""
    # Normalize trailing slashes/backslashes
    source = source.rstrip("/\\")
    return os.path.splitext(os.path.basename(source))[0]

def get_sidecar_path(source: str) -> str:
    """Return sidecar path next to the source (in parent directory).

    Both folders and archives with the same base name resolve to the same
    sidecar file, so settings created for a folder apply to its archive and
    vice versa.
    """
    base = _source_base(source)
    parent = os.path.dirname((source or "").rstrip("/\\")) or "."
    return os.path.join(parent, base + ".sidecar.json")


def _get_legacy_folder_sidecar_path(source: str) -> str | None:
    """Old layout stored sidecar inside the folder itself."""
    source = (source or "").rstrip("/\\")
    if os.path.isdir(source):
        base = os.path.splitext(os.path.basename(source))[0]
        return os.path.join(source, base + ".sidecar.json")
    return None

def _normalize_relpath(p: str) -> str:
    return (p or "").replace("\\", "/").lstrip("/")


def parse_bookmark(bm: dict) -> tuple[str, str] | None:
    """Extract (relPath, name) from a bookmark dict with legacy key fallbacks.

    Returns None if the bookmark is invalid or incomplete.
    """
    if not isinstance(bm, dict):
        return None
    rp = bm.get("relPath") or bm.get("anchor_relpath") or bm.get("anchorRelPath")
    nm = bm.get("name") or bm.get("Bookmark") or bm.get("title")
    if isinstance(rp, str) and isinstance(nm, str) and nm.strip():
        return _normalize_relpath(rp), nm.strip()
    return None


def _normalize_bookmarks(raw_bms: Any) -> list[dict[str, str]]:
    """Normalize a list of raw bookmark dicts into canonical form."""
    bms: list[dict[str, str]] = []
    if not isinstance(raw_bms, list):
        return bms
    for bm in raw_bms:
        parsed = parse_bookmark(bm)
        if parsed:
            bms.append({"relPath": parsed[0], "name": parsed[1]})
    return bms


def _normalize_spread_scan(raw: Any) -> dict[str, Any] | None:
    """Keep an explicitly completed scan, including one with no wide pages."""
    if not isinstance(raw, dict):
        return None
    fingerprint = raw.get("fingerprint")
    spreads = raw.get("spreads")
    if not (isinstance(fingerprint, str) and len(fingerprint) == 64
            and all(ch in "0123456789abcdef" for ch in fingerprint)
            and isinstance(spreads, list)
            and all(isinstance(rel, str) and rel.strip() for rel in spreads)):
        return None
    return {"fingerprint": fingerprint,
            "spreads": sorted({_normalize_relpath(rel) for rel in spreads})}


def load_sidecar(source: str, auto_migrate: bool = True) -> dict[str, Any]:
    """
    Loads unified sidecar for source. Also supports legacy files:
      - <base>.crop.json
      - ComicInfo.bookmarks.json (next to ComicInfo.xml)

    If auto_migrate is True and a legacy file is found while unified sidecar is missing,
    the function will write <base>.sidecar.json and delete the legacy files after a
    successful write.
    Returns dict with normalized keys.
    """
    sidecar = get_sidecar_path(source)
    sidecar_exists = os.path.isfile(sidecar)

    data: dict[str, Any] = {"no-crop": [], "auto-no-crop": [], "custom-crop": {}, "custom-split": {}, "excluded": [], "bookmarks": [], "extra-margin": {}, "edit-ops": {}, "watermark-matches": [], "_watermark-matches-saved": False, "spread-scan": None}

    # Track legacy locations for optional migration cleanup
    legacy_crop_path: str | None = None
    legacy_bm_path: str | None = None
    legacy_found = False

    # 1) Unified sidecar (new location next to source, or legacy inside folder)
    sidecar_to_read = sidecar if sidecar_exists else None
    if not sidecar_to_read:
        legacy_folder = _get_legacy_folder_sidecar_path(source)
        if legacy_folder and os.path.isfile(legacy_folder):
            sidecar_to_read = legacy_folder

    if sidecar_to_read:
        try:
            with open(sidecar_to_read, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                data["no-crop"] = raw.get("no-crop", raw.get("nocrop", [])) or []
                data["auto-no-crop"] = raw.get("auto-no-crop", []) or []
                data["custom-crop"] = raw.get("custom-crop", raw.get("custom_crops", {})) or {}
                data["custom-split"] = raw.get("custom-split", raw.get("custom_split", {})) or {}
                data["excluded"] = raw.get("excluded", []) or []
                data["bookmarks"] = raw.get("bookmarks", raw.get("bookmarkAnchors", [])) or []
                data["extra-margin"] = raw.get("extra-margin", {}) or {}
                data["edit-ops"] = raw.get("edit-ops", {}) or {}
                data["watermark-matches"] = raw.get("watermark-matches", []) or []
                data["_watermark-matches-saved"] = "watermark-matches" in raw
                data["spread-scan"] = _normalize_spread_scan(raw.get("spread-scan"))
        except Exception:
            logger.debug("Failed to read sidecar %s", sidecar_to_read, exc_info=True)

    # 2) Legacy crop.json (merge only if sidecar missing those keys)
    try:
        base = _source_base(source)
        legacy_crop_path = (os.path.join(source, base + ".crop.json")
                            if os.path.isdir(source) else os.path.join(os.path.dirname(source), base + ".crop.json"))
        if legacy_crop_path and os.path.isfile(legacy_crop_path):
            legacy_found = True
            with open(legacy_crop_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                if not data["no-crop"]:
                    data["no-crop"] = raw
            elif isinstance(raw, dict):
                if not data["no-crop"]:
                    data["no-crop"] = raw.get("no-crop", raw.get("nocrop", [])) or []
                if not data["custom-crop"]:
                    data["custom-crop"] = raw.get("custom-crop", raw.get("custom_crops", {})) or {}
                if not data["custom-split"]:
                    data["custom-split"] = raw.get("custom-split", raw.get("custom_split", {})) or {}
                if not data["excluded"]:
                    data["excluded"] = raw.get("excluded", []) or []
    except Exception:
        logger.debug("Failed to read legacy crop %s", legacy_crop_path, exc_info=True)

    # 3) Legacy ComicInfo.bookmarks.json
    try:
        base_dir = source if os.path.isdir(source) else os.path.dirname(source)
        legacy_bm_path = os.path.join(base_dir, "ComicInfo.bookmarks.json")
        if legacy_bm_path and os.path.isfile(legacy_bm_path) and not data["bookmarks"]:
            legacy_found = True
            with open(legacy_bm_path, "r", encoding="utf-8") as f:
                raw = json.load(f) or []
            if isinstance(raw, list):
                data["bookmarks"] = raw
    except Exception:
        logger.debug("Failed to read legacy bookmarks %s", legacy_bm_path, exc_info=True)

    # Normalize
    source_base_norm = _source_base(source).replace("\\", "/").strip("/").lower()

    def _norm_for_source(rel_path: str) -> str:
        rp = _normalize_relpath(rel_path)
        if source_base_norm:
            pref = source_base_norm + "/"
            low = rp.lower()
            if low.startswith(pref):
                rp = rp[len(pref):]
        return rp

    data["no-crop"] = sorted({_norm_for_source(x) for x in (data.get("no-crop") or []) if isinstance(x, str)})
    data["auto-no-crop"] = sorted({_norm_for_source(x) for x in (data.get("auto-no-crop") or []) if isinstance(x, str)})
    data["watermark-matches"] = sorted({_norm_for_source(x) for x in (data.get("watermark-matches") or []) if isinstance(x, str)})
    cc = {}
    raw_cc = data.get("custom-crop") or {}
    if isinstance(raw_cc, dict):
        for k, v in raw_cc.items():
            if not isinstance(k, str) or not isinstance(v, dict):
                continue
            cc[_norm_for_source(k)] = v
    data["custom-crop"] = cc

    cs = {}
    raw_cs = data.get("custom-split") or {}
    if isinstance(raw_cs, dict):
        for k, v in raw_cs.items():
            if not isinstance(k, str) or not isinstance(v, dict):
                continue
            axis = str(v.get("axis", "") or "").strip().lower()
            if axis not in {"x", "y"}:
                axis = "x"
            item: dict[str, Any] = {"axis": axis}
            for key in ("split", "width", "height"):
                val = v.get(key)
                if isinstance(val, (int, float)):
                    item[key] = val
            cs[_norm_for_source(k)] = item
    data["custom-split"] = cs
    data["excluded"] = sorted({_norm_for_source(x) for x in (data.get("excluded") or []) if isinstance(x, str)})

    data["bookmarks"] = [
        {"relPath": _norm_for_source(bm.get("relPath", "")), "name": bm.get("name", "")}
        for bm in _normalize_bookmarks(data.get("bookmarks") or [])
        if bm.get("relPath") and bm.get("name")
    ]

    em = {}
    raw_em = data.get("extra-margin") or {}
    if isinstance(raw_em, dict):
        for k, v in raw_em.items():
            if not isinstance(k, str) or not isinstance(v, dict):
                continue
            item_em: dict = {}
            for side in ("top", "bottom", "left", "right"):
                val = v.get(side)
                if isinstance(val, (int, float)) and val > 0:
                    item_em[side] = int(val)
            if v.get("color") and isinstance(v["color"], str):
                item_em["color"] = v["color"]
            if item_em:
                em[_norm_for_source(k)] = item_em
    data["extra-margin"] = em

    eo = {}
    raw_eo = data.get("edit-ops") or {}
    if isinstance(raw_eo, dict):
        for k, v in raw_eo.items():
            if isinstance(k, str) and isinstance(v, list) and v:
                eo[_norm_for_source(k)] = v
    data["edit-ops"] = eo

    # Auto-migrate legacy inside-folder sidecar to new parent-dir location
    legacy_folder_sc = _get_legacy_folder_sidecar_path(source)
    if auto_migrate and (not sidecar_exists) and legacy_folder_sc and os.path.isfile(legacy_folder_sc):
        legacy_found = True

    # Auto-migrate: if unified sidecar missing but legacy exists, write sidecar and delete legacy files
    if auto_migrate and (not sidecar_exists) and legacy_found:
        try:
            out: dict[str, Any] = {}
            if data.get("no-crop"):
                out["no-crop"] = data["no-crop"]
            if data.get("auto-no-crop"):
                out["auto-no-crop"] = data["auto-no-crop"]
            if data.get("custom-crop"):
                out["custom-crop"] = data["custom-crop"]
            if data.get("custom-split"):
                out["custom-split"] = data["custom-split"]
            if data.get("excluded"):
                out["excluded"] = data["excluded"]
            if data.get("bookmarks"):
                out["bookmarks"] = data["bookmarks"]
            if data.get("extra-margin"):
                out["extra-margin"] = data["extra-margin"]
            if data.get("edit-ops"):
                out["edit-ops"] = data["edit-ops"]
            if data.get("_watermark-matches-saved"):
                out["watermark-matches"] = data["watermark-matches"]
            if data.get("spread-scan") is not None:
                out["spread-scan"] = data["spread-scan"]

            if out:
                os.makedirs(os.path.dirname(sidecar) or ".", exist_ok=True)
                with open(sidecar, "w", encoding="utf-8") as f:
                    json.dump(out, f, ensure_ascii=False, indent=2)

                # Remove legacy files after successful write
                for p in (legacy_crop_path, legacy_bm_path, legacy_folder_sc):
                    if p and os.path.isfile(p):
                        try:
                            os.remove(p)
                        except Exception:
                            pass
        except Exception:
            # If migration fails, still return normalized data and keep legacy files.
            logger.debug("Sidecar migration failed for %s", source, exc_info=True)

    return data


def save_sidecar(source: str,
                nocrop: list[str] | None = None,
                auto_nocrop: list[str] | None = None,
                custom_crop: dict[str, Any] | None = None,
                custom_split: dict[str, Any] | None = None,
                excluded: list[str] | None = None,
                bookmarks: list[dict[str, str]] | None = None,
                extra_margin: dict[str, Any] | None = None,
                edit_ops: dict[str, Any] | None = None,
                watermark_matches: list[str] | None = None,
                remove_if_empty: bool = True,
                spread_scan: dict[str, Any] | None = None) -> tuple[bool, str, bool]:
    """
    Saves sidecar for source. Returns (ok, path, removed).
    Only provided keys are written; missing keys are preserved from existing file.
    If remove_if_empty and resulting dict has no meaningful data -> remove file.
    """
    path = get_sidecar_path(source)
    cur = load_sidecar(source) if os.path.isfile(path) else {"no-crop": [], "auto-no-crop": [], "custom-crop": {}, "custom-split": {}, "excluded": [], "bookmarks": [], "extra-margin": {}, "edit-ops": {}, "watermark-matches": [], "_watermark-matches-saved": False, "spread-scan": None}

    if nocrop is not None:
        cur["no-crop"] = sorted({ _normalize_relpath(x) for x in nocrop if isinstance(x, str) and x.strip() })
    if auto_nocrop is not None:
        cur["auto-no-crop"] = sorted({ _normalize_relpath(x) for x in auto_nocrop if isinstance(x, str) and x.strip() })
    if custom_crop is not None:
        cc = {}
        if isinstance(custom_crop, dict):
            for k,v in custom_crop.items():
                if isinstance(k, str) and isinstance(v, dict):
                    cc[_normalize_relpath(k)] = v
        cur["custom-crop"] = cc
    if custom_split is not None:
        cs = {}
        if isinstance(custom_split, dict):
            for k, v in custom_split.items():
                if not (isinstance(k, str) and isinstance(v, dict)):
                    continue
                axis = str(v.get("axis", "") or "").strip().lower()
                if axis not in {"x", "y"}:
                    axis = "x"
                item: dict[str, Any] = {"axis": axis}
                for key in ("split", "width", "height"):
                    val = v.get(key)
                    if isinstance(val, (int, float)):
                        item[key] = val
                cs[_normalize_relpath(k)] = item
        cur["custom-split"] = cs
    if excluded is not None:
        cur["excluded"] = sorted({ _normalize_relpath(x) for x in excluded if isinstance(x, str) and x.strip() })
    if bookmarks is not None:
        cur["bookmarks"] = _normalize_bookmarks(bookmarks)
    if extra_margin is not None:
        em_out: dict[str, Any] = {}
        if isinstance(extra_margin, dict):
            for k, v in extra_margin.items():
                if not (isinstance(k, str) and isinstance(v, dict)):
                    continue
                item_em: dict = {}
                for side in ("top", "bottom", "left", "right"):
                    val = v.get(side)
                    if isinstance(val, (int, float)) and val > 0:
                        item_em[side] = int(val)
                if v.get("color") and isinstance(v["color"], str):
                    item_em["color"] = v["color"]
                if item_em:
                    em_out[_normalize_relpath(k)] = item_em
        cur["extra-margin"] = em_out
    if edit_ops is not None:
        eo_out: dict[str, Any] = {}
        if isinstance(edit_ops, dict):
            for k, v in edit_ops.items():
                if isinstance(k, str) and isinstance(v, list) and v:
                    eo_out[_normalize_relpath(k)] = v
        cur["edit-ops"] = eo_out
    if watermark_matches is not None:
        cur["watermark-matches"] = sorted({
            _normalize_relpath(x) for x in watermark_matches
            if isinstance(x, str) and x.strip()
        })
        cur["_watermark-matches-saved"] = True
    if spread_scan is not None:
        cur["spread-scan"] = _normalize_spread_scan(spread_scan)

    # Strip empties
    out = {}
    if cur.get("no-crop"):
        out["no-crop"] = cur["no-crop"]
    if cur.get("auto-no-crop"):
        out["auto-no-crop"] = cur["auto-no-crop"]
    if cur.get("custom-crop"):
        out["custom-crop"] = cur["custom-crop"]
    if cur.get("custom-split"):
        out["custom-split"] = cur["custom-split"]
    if cur.get("excluded"):
        out["excluded"] = cur["excluded"]
    if cur.get("bookmarks"):
        out["bookmarks"] = cur["bookmarks"]
    if cur.get("extra-margin"):
        out["extra-margin"] = cur["extra-margin"]
    if cur.get("edit-ops"):
        out["edit-ops"] = cur["edit-ops"]
    if cur.get("_watermark-matches-saved"):
        out["watermark-matches"] = cur["watermark-matches"]
    if cur.get("spread-scan") is not None:
        out["spread-scan"] = cur["spread-scan"]

    if remove_if_empty and not out:
        if os.path.isfile(path):
            try: os.remove(path)
            except Exception: pass
        return True, path, True

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return True, path, False
