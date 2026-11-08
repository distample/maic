"""Routes for ComicInfo metadata, sidecar storage, and presets."""

import json as _json
import os
import re
from typing import cast

from flask import Blueprint, jsonify

from . import error_codes as EC
from .api_errors import fail
from .chapter_names import (
    ChapterNamesError,
    get_chapter_names_path,
    load_chapter_names,
    save_chapter_names,
)
from .config import MODULES_DIR, state
from .dto import (
    ComicInfoWritePayload,
    CropSidecarSavePayload,
    PresetsSavePayload,
    TocScrapePayload,
)
from .path_access import is_under_allowed_root
from .payload_validation import (
    validate_comicinfo_write_payload,
    validate_crop_sidecar_save_payload,
    validate_presets_save_payload,
    validate_toc_scrape_payload,
)
from .sidecar import load_sidecar, parse_bookmark, save_sidecar
from .toc_scrape import TocScrapeError, extract_chapters, fetch_page
from .validation import json_body, require_non_empty_str, require_path_exists

metadata_bp = Blueprint("metadata", __name__)


def _resolve_preset_path(name: str) -> tuple[bool, str]:
    """Return canonical preset file path or failure message."""
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name or ""):
        return False, "name contains unsupported characters"
    if name.startswith("."):
        return False, "name must not start with dot"
    presets_dir = os.path.realpath(os.path.join(MODULES_DIR, "kcc_presets"))
    path = os.path.realpath(os.path.join(presets_dir, name + ".json"))
    try:
        if os.path.commonpath([path, presets_dir]) != presets_dir:
            return False, "invalid preset path"
    except ValueError:
        return False, "invalid preset path"
    return True, path


@metadata_bp.route("/api/comicinfo/read", methods=["POST"])
def api_comicinfo_read():
    """Read ComicInfo.xml from a source folder (or next to archive)."""
    data = json_body()
    source = data.get("source", "").rstrip("/\\")
    valid, err = require_path_exists(source, code=EC.SOURCE_NOT_FOUND)
    if not valid:
        return err
    if os.path.isdir(source):
        xml_path = os.path.join(source, "ComicInfo.xml")
    else:
        xml_path = os.path.join(os.path.dirname(source), "ComicInfo.xml")
    if not os.path.isfile(xml_path):
        return jsonify({"ok": True, "exists": False, "path": xml_path, "fields": {}})
    try:
        import xml.etree.ElementTree as ET

        tree = ET.parse(xml_path)
        root = tree.getroot()
        fields = {}
        bookmarks = []
        for child in root:
            if child.tag == "Pages":
                for page in child:
                    img = page.get("Image")
                    bm = page.get("Bookmark")
                    if img is not None and bm is not None:
                        bookmarks.append([int(img), bm])
            elif child.text:
                fields[child.tag] = child.text
        anchors = []
        try:
            sc = load_sidecar(source)
            anchors = sc.get("bookmarks", []) or []
        except Exception:
            anchors = []
        return jsonify(
            {
                "ok": True,
                "exists": True,
                "path": xml_path,
                "fields": fields,
                "bookmarks": bookmarks,
                "bookmarkAnchors": anchors,
            }
        )
    except Exception as exc:
        return fail(str(exc), code=EC.COMICINFO_READ_FAILED)


@metadata_bp.route("/api/comicinfo/write", methods=["POST"])
def api_comicinfo_write():
    """Write ComicInfo.xml fields and store bookmarks in sidecar next to source."""
    data = json_body()
    payload = cast(ComicInfoWritePayload, data)
    source = payload.get("source", "").rstrip("/\\")
    valid, message = validate_comicinfo_write_payload(data)
    if not valid:
        return fail(message, code=EC.INVALID_PAYLOAD)
    fields = payload.get("fields", {})
    bookmarks = payload.get("bookmarks", [])
    valid, err = require_path_exists(source, code=EC.SOURCE_NOT_FOUND)
    if not valid:
        return err
    if os.path.isdir(source):
        xml_path = os.path.join(source, "ComicInfo.xml")
    else:
        xml_path = os.path.join(os.path.dirname(source), "ComicInfo.xml")
    try:
        import xml.etree.ElementTree as ET

        root = ET.Element("ComicInfo")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")
        ordered_keys = [
            "Title",
            "Series",
            "Number",
            "Count",
            "Volume",
            "AlternateSeries",
            "AlternateNumber",
            "AlternateCount",
            "Summary",
            "Notes",
            "Year",
            "Month",
            "Day",
            "Writer",
            "Penciller",
            "Inker",
            "Colorist",
            "Letterer",
            "CoverArtist",
            "Editor",
            "Translator",
            "Publisher",
            "Imprint",
            "Genre",
            "Tags",
            "Web",
            "PageCount",
            "LanguageISO",
            "Format",
            "BlackAndWhite",
            "Manga",
            "AgeRating",
            "ScanInformation",
        ]
        for key in ordered_keys:
            val = fields.get(key)
            if val is not None and str(val).strip() != "":
                el = ET.SubElement(root, key)
                el.text = str(val)

        anchors = []
        try:
            for bm in (bookmarks or []):
                parsed = parse_bookmark(bm)
                if parsed:
                    anchors.append({"relPath": parsed[0], "name": parsed[1]})
        except Exception:
            anchors = []

        try:
            save_sidecar(source, bookmarks=anchors)
        except Exception:
            pass

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        with open(xml_path, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
            tree.write(f, encoding="utf-8", xml_declaration=False)
        return jsonify({"ok": True, "path": xml_path})
    except Exception as exc:
        return fail(str(exc), code=EC.COMICINFO_WRITE_FAILED)


@metadata_bp.route("/api/crop-sidecar/save", methods=["POST"])
def api_crop_sidecar_save():
    """Save nocrop + custom_crops + custom_split + excluded (+ optional bookmarks) to sidecar."""
    data = json_body()
    payload = cast(CropSidecarSavePayload, data)
    source = payload.get("source", "")
    nocrop = payload.get("no-crop", [])
    custom_crops = payload.get("custom-crop", {})
    custom_splits = payload.get("custom-split", {})
    excluded = payload.get("excluded", [])
    bookmarks = payload.get("bookmarks", None)
    extra_margin = payload.get("extra-margin", None)
    edit_ops = payload.get("edit-ops", None)
    watermark_matches = payload.get("watermark-matches", None)
    valid, err = require_non_empty_str(source, field="source", code=EC.MISSING_SOURCE)
    if not valid:
        return err
    valid, message = validate_crop_sidecar_save_payload(data)
    if not valid:
        return fail(message, code=EC.INVALID_PAYLOAD)
    ok, path, removed = save_sidecar(
        source,
        nocrop=nocrop,
        custom_crop=custom_crops,
        custom_split=custom_splits,
        excluded=excluded,
        bookmarks=bookmarks,
        extra_margin=extra_margin,
        edit_ops=edit_ops,
        watermark_matches=watermark_matches,
    )
    if not ok:
        return fail("save failed", code=EC.SIDECAR_SAVE_FAILED)
    return jsonify({"ok": True, "path": path, "removed": removed})


@metadata_bp.route("/api/crop-sidecar/load", methods=["POST"])
def api_crop_sidecar_load():
    """Load unified sidecar data from an explicit path."""
    data = json_body()
    path = data.get("path", "")
    if isinstance(path, str) and path:
        if not is_under_allowed_root(path, state.get("allowed_read_roots", [])):
            return fail("Access denied", code=EC.INVALID_PATH, status=403)
    if not path or not os.path.isfile(path):
        return fail("not found", code=EC.SIDECAR_NOT_FOUND)
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = _json.load(f)
        nocrop = []
        custom_crops = {}
        custom_splits = {}
        excluded = []
        bookmarks = []
        extra_margin = {}
        edit_ops = {}
        watermark_matches = []
        watermark_matches_saved = False
        if isinstance(payload, list):
            nocrop = payload
        elif isinstance(payload, dict):
            nocrop = payload.get("no-crop", payload.get("nocrop", []))
            custom_crops = payload.get("custom-crop", payload.get("custom_crops", {}))
            custom_splits = payload.get("custom-split", payload.get("custom_split", {}))
            excluded = payload.get("excluded", [])
            bookmarks = payload.get("bookmarks", payload.get("bookmarkAnchors", []))
            extra_margin = payload.get("extra-margin", {})
            edit_ops = payload.get("edit-ops", {})
            watermark_matches = payload.get("watermark-matches", [])
            watermark_matches_saved = "watermark-matches" in payload
        return jsonify(
            {
                "ok": True,
                "no-crop": nocrop,
                "custom-crop": custom_crops,
                "custom-split": custom_splits,
                "excluded": excluded,
                "bookmarks": bookmarks,
                "extra-margin": extra_margin,
                "edit-ops": edit_ops,
                "watermark-matches": watermark_matches,
                "watermark-matches-saved": watermark_matches_saved,
            }
        )
    except Exception as exc:
        return fail(str(exc), code=EC.SIDECAR_LOAD_FAILED)


@metadata_bp.route("/api/browse-json", methods=["POST"])
def api_browse_json():
    """Open file dialog to select a JSON file."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Select sidecar JSON", filetypes=[("JSON", "*.json"), ("All", "*.*")]
        )
        root.destroy()
        return jsonify({"ok": bool(path), "path": path or ""})
    except Exception as exc:
        return fail(str(exc), code=EC.BROWSE_JSON_FAILED)


@metadata_bp.route("/api/presets/save", methods=["POST"])
def api_presets_save():
    """Persist KCC preset data by name."""
    data = json_body()
    typed = cast(PresetsSavePayload, data)
    name = typed.get("name", "")
    payload = typed.get("data", {})
    valid, err = require_non_empty_str(name, field="name", code=EC.MISSING_PRESET_NAME)
    if not valid:
        return err
    ok_path, preset_path = _resolve_preset_path(name)
    if not ok_path:
        return fail(preset_path, code=EC.INVALID_PATH, status=400)
    valid, message = validate_presets_save_payload(data)
    if not valid:
        return fail(message, code=EC.INVALID_PAYLOAD)
    presets_dir = os.path.realpath(os.path.join(MODULES_DIR, "kcc_presets"))
    os.makedirs(presets_dir, exist_ok=True)
    with open(preset_path, "w", encoding="utf-8") as f:
        _json.dump(payload, f, ensure_ascii=False, indent=2)
    return jsonify({"ok": True, "path": preset_path})


@metadata_bp.route("/api/presets/load", methods=["POST"])
def api_presets_load():
    """Load named KCC preset."""
    data = json_body()
    name = data.get("name", "")
    valid, err = require_non_empty_str(name, field="name", code=EC.MISSING_PRESET_NAME)
    if not valid:
        return err
    ok_path, path = _resolve_preset_path(name)
    if not ok_path:
        return fail(path, code=EC.INVALID_PATH, status=400)
    if not os.path.isfile(path):
        return fail("not found", code=EC.PRESET_NOT_FOUND)
    with open(path, "r", encoding="utf-8") as f:
        payload = _json.load(f)
    return jsonify({"ok": True, "data": payload})


@metadata_bp.route("/api/presets/delete", methods=["POST"])
def api_presets_delete():
    """Delete named KCC preset."""
    data = json_body()
    name = data.get("name", "")
    valid, err = require_non_empty_str(name, field="name", code=EC.MISSING_PRESET_NAME)
    if not valid:
        return err
    ok_path, path = _resolve_preset_path(name)
    if not ok_path:
        return fail(path, code=EC.INVALID_PATH, status=400)
    if os.path.isfile(path):
        os.remove(path)
    return jsonify({"ok": True})


@metadata_bp.route("/api/presets/list")
def api_presets_list():
    """List available KCC presets."""
    presets_dir = os.path.join(MODULES_DIR, "kcc_presets")
    files = []
    if os.path.isdir(presets_dir):
        files = [f[:-5] for f in sorted(os.listdir(presets_dir)) if f.endswith(".json")]
    return jsonify({"presets": files})


@metadata_bp.route("/api/toc/scrape", methods=["POST"])
def api_toc_scrape():
    """Read a chapter list off a web page the user linked to."""
    data = json_body()
    valid, message = validate_toc_scrape_payload(data)
    if not valid:
        return fail(message, code=EC.INVALID_PAYLOAD)
    typed = cast(TocScrapePayload, data)
    url = typed.get("url", "")
    try:
        html = fetch_page(url)
    except TocScrapeError as exc:
        return fail(str(exc), code=EC.TOC_SCRAPE_FETCH_FAILED)
    except Exception as exc:
        return fail("Could not read the page: %s" % exc, code=EC.TOC_SCRAPE_FETCH_FAILED)
    chapters = extract_chapters(html)
    if not chapters:
        return fail("No chapter list found on that page", code=EC.TOC_SCRAPE_NO_CHAPTERS)
    result: dict = {"ok": True, "chapters": chapters}
    # Persisting is best-effort: the names are useful even when the file is not
    # writable, so a failed save is reported beside a successful scrape.
    source = str(typed.get("source", "") or "").rstrip("/\\")
    if source:
        if not os.path.exists(source):
            result["saved"] = False
            result["saveError"] = "Source folder not found"
        else:
            try:
                result["path"] = save_chapter_names(source, chapters, url)
                result["saved"] = True
            except (ChapterNamesError, OSError) as exc:
                result["saved"] = False
                result["saveError"] = str(exc)
    return jsonify(result)


@metadata_bp.route("/api/toc/chapter-names", methods=["POST"])
def api_toc_chapter_names():
    """Return the chapter names already stored beside a source."""
    data = json_body()
    source = str(data.get("source", "") or "").rstrip("/\\")
    valid, err = require_path_exists(source, code=EC.SOURCE_NOT_FOUND)
    if not valid:
        return err
    try:
        stored = load_chapter_names(source)
    except ChapterNamesError as exc:
        # An unreadable file is reported, not replaced: the user may have
        # written it by hand.
        return jsonify(
            {
                "ok": True,
                "exists": False,
                "path": get_chapter_names_path(source),
                "url": "",
                "updated": "",
                "chapters": [],
                "warning": str(exc),
            }
        )
    return jsonify({"ok": True, **stored})
