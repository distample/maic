"""KCC source scanning and preview helpers."""

from __future__ import annotations

import io
import hashlib
import json
import math
import os
import re
import sys
import threading
from collections import OrderedDict
from typing import Any, Callable, cast

from .config import KCC_DIR
from .sevenzip import find_7z, run_7z
from .page_number_sequence import page_number_minimum

ARCHIVE_SEP = "||"

_PAGE_NUMBER_PREVIEW_CACHE: OrderedDict[str, tuple[Any, int, dict[str, Any], str]] = OrderedDict()
_PAGE_NUMBER_PREVIEW_LOCK = threading.RLock()
_PAGE_NUMBER_PREVIEW_CACHE_LIMIT = 24


def _page_number_preview_cache_key(
    image_bytes: bytes,
    edit_ops: Any,
    method: str,
    padding: int,
    page_number_scope: str = "",
    minimum_page_number: int = 1,
) -> str:
    digest = hashlib.sha1(image_bytes).hexdigest()
    try:
        edits = json.dumps(edit_ops or [], ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        edits = "[]"
    memory_revision = "0"
    if page_number_scope:
        try:
            from .page_number_memory import page_number_memory_metadata

            memory_revision = str(page_number_memory_metadata(page_number_scope).get("revision") or "0")
        except Exception:
            memory_revision = "0"
    return "|".join((
        digest, edits, method, str(padding),
        os.path.realpath(str(page_number_scope or "")), memory_revision, str(page_number_minimum(minimum_page_number)),
    ))


def _apply_preview_page_number_cleanup(
    image: Any,
    cache_key: str,
    *,
    method: str,
    padding: int,
    page_number_scope: str = "",
    minimum_page_number: int = 1,
) -> tuple[Any, int, dict[str, Any], str]:
    # The thumbnail and crop-metadata requests arrive together. Serialize and
    # share their local cleanup result so the page is analysed only once.
    with _PAGE_NUMBER_PREVIEW_LOCK:
        cached = _PAGE_NUMBER_PREVIEW_CACHE.get(cache_key)
        if cached is not None:
            _PAGE_NUMBER_PREVIEW_CACHE.move_to_end(cache_key)
            cached_image, count, decision, error = cached
            return cached_image.copy(), count, dict(decision), error
        try:
            from .autonomous import apply_maic_page_number_cleanup

            # Preview the method the conversion will actually use. "lama" is
            # rendered as a flat fill: clean_image discards the model output
            # inside the mask and fills it with the surrounding colour, so the
            # result is identical without loading the model for a preview.
            # Telea used to be hardcoded here and left a grey smear where the
            # folio had been, which the converted page never showed.
            preview_method = str(method or "lama")
            if preview_method == "lama":
                preview_method = "fill"
            cleaned, count, decision = apply_maic_page_number_cleanup(
                image,
                method=preview_method,
                padding=padding,
                # None, not []: the conversion protects logo/watermark profiles
                # from the folio pass, and the preview has to show the same
                # thing. Profiles are still only loaded once a folio is found.
                artifact_profiles=None,
                scope_path=page_number_scope,
                minimum_page_number=minimum_page_number,
            )
            error = ""
        except Exception as exc:
            cleaned, count, decision, error = image.copy(), 0, {}, str(exc)[:300]
        _PAGE_NUMBER_PREVIEW_CACHE[cache_key] = (cleaned.copy(), int(count), dict(decision), error)
        while len(_PAGE_NUMBER_PREVIEW_CACHE) > _PAGE_NUMBER_PREVIEW_CACHE_LIMIT:
            _PAGE_NUMBER_PREVIEW_CACHE.popitem(last=False)
        return cleaned, int(count), dict(decision), error


def scan_source_entries(
    source: str,
    ensure_kcc_path: Callable[[], None],
    load_sidecar: Callable[[str], dict[str, Any]],
    logger: Any,
) -> dict[str, Any]:
    """Scan source contents and return grouped image entries payload."""
    if not source or not os.path.exists(source):
        return {"ok": False, "error": "Not found"}

    img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}
    files: list[dict[str, Any]] = []
    arch_exts = {".zip", ".cbz", ".cbr", ".cb7", ".rar", ".7z"}

    def _scan_archive_contents(arch_path: str, folder_prefix: str):
        sz = find_7z(ensure_kcc_path=ensure_kcc_path)
        if not sz:
            return []

        result = []
        try:
            r = run_7z(
                ["l", "-slt", "-sccUTF-8", arch_path],
                timeout=30,
                ensure_kcc_path=ensure_kcc_path,
                text=True,
            )
            if r is None or r.returncode != 0:
                return []
            current_path = None
            current_folder = False
            for line in r.stdout.split("\n"):
                line = line.strip()
                if line.startswith("Path = "):
                    current_path = line[7:].replace("\\", "/")
                    current_folder = False
                elif line.startswith("Folder = +"):
                    current_folder = True
                elif line.startswith("Size = ") and current_path and not current_folder:
                    if os.path.splitext(current_path)[1].lower() in img_exts:
                        inner_folder = "/".join(current_path.split("/")[:-1])
                        folder = (
                            (folder_prefix + "/" + inner_folder).rstrip("/")
                            if inner_folder
                            else folder_prefix
                        )
                        rel = (
                            folder_prefix + "/" + current_path
                            if inner_folder
                            else folder_prefix + "/" + current_path
                        )
                        ref = arch_path + ARCHIVE_SEP + current_path
                        result.append(
                            {
                                "name": current_path.split("/")[-1],
                                "path": ref,
                                "relPath": rel,
                                "folder": folder,
                                "archive": True,
                            }
                        )
                    current_path = None
                elif line == "":
                    current_path = None
                    current_folder = False
        except Exception as exc:
            logger.error(f"Scan archive contents: {exc}")
        return result

    if os.path.isdir(source):
        for root, dirs, fnames in os.walk(source):
            dirs.sort()
            for fn in sorted(fnames):
                fp = os.path.join(root, fn)
                ext = os.path.splitext(fn)[1].lower()
                rel_root = os.path.relpath(root, source).replace("\\", "/")
                if ext in img_exts:
                    rel = os.path.relpath(fp, source).replace("\\", "/")
                    folder = os.path.dirname(rel) or ""
                    files.append({"name": fn, "path": fp, "relPath": rel, "folder": folder})
                elif ext in arch_exts:
                    arch_name = os.path.splitext(fn)[0]
                    folder_prefix = rel_root.rstrip("/") + "/" + arch_name if rel_root != "." else arch_name
                    files.extend(_scan_archive_contents(fp, folder_prefix))
    else:
        ext = os.path.splitext(source)[1].lower()
        if ext in arch_exts:
            sz = find_7z(ensure_kcc_path=ensure_kcc_path)
            if sz:
                try:
                    r = run_7z(
                        ["l", "-slt", "-sccUTF-8", source],
                        timeout=30,
                        ensure_kcc_path=ensure_kcc_path,
                        text=True,
                    )
                    if r is None or r.returncode != 0:
                        r = None
                    if r is None:
                        raise RuntimeError("Failed to scan archive")
                    current_path = None
                    current_folder = False
                    for line in r.stdout.split("\n"):
                        line = line.strip()
                        if line.startswith("Path = "):
                            current_path = line[7:].replace("\\", "/")
                            current_folder = False
                        elif line.startswith("Folder = +"):
                            current_folder = True
                        elif line.startswith("Size = ") and current_path and not current_folder:
                            if os.path.splitext(current_path)[1].lower() in img_exts:
                                folder = "/".join(current_path.replace("\\", "/").split("/")[:-1])
                                ref = source + ARCHIVE_SEP + current_path
                                files.append(
                                    {
                                        "name": current_path.split("/")[-1],
                                        "path": ref,
                                        "relPath": current_path,
                                        "folder": folder,
                                        "archive": True,
                                    }
                                )
                            current_path = None
                        elif line == "":
                            current_path = None
                            current_folder = False
                except Exception as exc:
                    logger.error(f"Scan archive: {exc}")
        elif ext == ".pdf":
            try:
                import pymupdf

                doc = pymupdf.open(source)
                for i in range(min(doc.page_count, 500)):
                    ref = source + ARCHIVE_SEP + f"page:{i}"
                    files.append(
                        {
                            "name": f"page_{i+1:04d}.png",
                            "path": ref,
                            "relPath": f"page_{i+1}",
                            "folder": "",
                            "archive": True,
                        }
                    )
                doc.close()
            except Exception as exc:
                logger.error(f"Scan PDF: {exc}")

    def _nat_parts(s: str):
        return [(0, int(c), "") if c.isdigit() else (1, 0, c.lower()) for c in re.split(r"(\d+)", s) if c]

    files.sort(key=lambda f: (_nat_parts(f.get("folder", "")), _nat_parts(f.get("name", ""))))

    sidecar_data = load_sidecar(source)
    sidecar_nocrop = sidecar_data["no-crop"]
    sidecar_custom = sidecar_data["custom-crop"]
    sidecar_custom_split = sidecar_data.get("custom-split", {}) or {}
    sidecar_excluded = sidecar_data["excluded"]
    sidecar_bookmarks = sidecar_data.get("bookmarks", [])
    sidecar_extra_margin = sidecar_data.get("extra-margin", {}) or {}
    sidecar_edit_ops = sidecar_data.get("edit-ops", {}) or {}
    sidecar_watermark_matches = sidecar_data.get("watermark-matches", []) or []
    sidecar_watermark_matches_saved = bool(sidecar_data.get("_watermark-matches-saved", False))

    remapped_custom: dict[str, Any] = {}
    remapped_custom_split: dict[str, Any] = {}
    remapped_extra_margin: dict[str, Any] = {}
    remapped_edit_ops: dict[str, Any] = {}
    for item in files:
        rel = item.get("relPath", "")
        name_lower = os.path.splitext(item["name"])[0].lower()
        if "_nocrop" in name_lower:
            item["no-crop"] = True
        elif rel in sidecar_nocrop:
            item["no-crop"] = True
        if rel in sidecar_custom:
            remapped_custom[rel] = sidecar_custom[rel]
        if rel in sidecar_custom_split:
            remapped_custom_split[rel] = sidecar_custom_split[rel]
        if rel in sidecar_extra_margin:
            remapped_extra_margin[rel] = sidecar_extra_margin[rel]
        if rel in sidecar_edit_ops:
            remapped_edit_ops[rel] = sidecar_edit_ops[rel]

    groups: dict[str, list[dict[str, Any]]] = {}
    for item in files:
        folder = item.get("folder", "")
        if folder not in groups:
            groups[folder] = []
        groups[folder].append(item)

    ci_bookmarks: list[list[Any]] = []
    ci_path = os.path.join(source, "ComicInfo.xml") if os.path.isdir(source) else None
    if ci_path and os.path.isfile(ci_path):
        try:
            import xml.dom.minidom as _md

            dom = _md.parse(ci_path)
            for page in dom.getElementsByTagName("Page"):
                if page.hasAttribute("Bookmark") and page.hasAttribute("Image"):
                    ci_bookmarks.append([int(page.getAttribute("Image")), page.getAttribute("Bookmark")])
        except Exception:
            pass

    return {
        "ok": True,
        "files": files,
        "total": len(files),
        "custom-crop": remapped_custom,
        "custom-split": remapped_custom_split,
        "excluded": list(sidecar_excluded),
        "bookmarks": ci_bookmarks,
        "bookmarkAnchors": sidecar_bookmarks,
        "extra-margin": remapped_extra_margin,
        "edit-ops": remapped_edit_ops,
        "watermark-matches": list(sidecar_watermark_matches),
        "watermark-matches-saved": sidecar_watermark_matches_saved,
        "groups": [{"folder": key, "files": value} for key, value in groups.items()],
    }


_PAGE_SIZE_CACHE: OrderedDict[str, tuple[int, int]] = OrderedDict()
_PAGE_SIZE_LOCK = threading.RLock()
_PAGE_SIZE_CACHE_LIMIT = 20000


def _container_stamp(path: str) -> str:
    """What identifies a file on disk, and changes the moment its bytes do."""
    try:
        st = os.stat(path)
    except OSError:
        return ""
    return "%s|%d|%d" % (os.path.realpath(path), st.st_mtime_ns, st.st_size)


def _cached_page_size(key: str, compute: Callable[[], tuple[int, int] | None]) -> tuple[int, int] | None:
    """Measure a page once per session, so reopening a source costs nothing."""
    if not key:
        return compute()
    with _PAGE_SIZE_LOCK:
        hit = _PAGE_SIZE_CACHE.get(key)
        if hit is not None:
            _PAGE_SIZE_CACHE.move_to_end(key)
            return hit
    size = compute()
    if size is None:
        return None
    with _PAGE_SIZE_LOCK:
        _PAGE_SIZE_CACHE[key] = size
        while len(_PAGE_SIZE_CACHE) > _PAGE_SIZE_CACHE_LIMIT:
            _PAGE_SIZE_CACHE.popitem(last=False)
    return size


def _image_size_from_stream(stream: Any) -> tuple[int, int] | None:
    """Read only as much of an image as its header needs to give up its size."""
    from PIL import ImageFile

    parser = ImageFile.Parser()
    while True:
        chunk = stream.read(65536)
        if not chunk:
            break
        parser.feed(chunk)
        if parser.image is not None:
            return (int(parser.image.width), int(parser.image.height))
    try:
        image = parser.close()
    except Exception:
        return None
    return (int(image.width), int(image.height))


def _probe_pdf_page_sizes(archive: str, entries: list[tuple[dict[str, Any], str]],
                          sizes: dict[str, tuple[int, int]], logger: Any) -> None:
    """A PDF page states its own box, so nothing has to be rendered to measure it."""
    try:
        import pymupdf

        doc = pymupdf.open(archive)
    except Exception:
        logger.debug("Probe PDF page sizes: %s", archive, exc_info=True)
        return
    try:
        for item, internal in entries:
            if not internal.startswith("page:"):
                continue
            try:
                rect = cast(Any, doc[int(internal.split(":")[1])]).rect
                width, height = int(round(rect.width)), int(round(rect.height))
            except Exception:
                continue
            if width > 0 and height > 0:
                sizes[str(item.get("relPath") or "")] = (width, height)
    finally:
        doc.close()


def _probe_zip_page_sizes(archive: str, entries: list[tuple[dict[str, Any], str]],
                          sizes: dict[str, tuple[int, int]], logger: Any) -> bool:
    """Measure a zip's pages in-process; False leaves them to 7z.

    Most sources are CBZ, and reading their entries here spares one 7z process
    per page -- the difference between a book opening in a moment and in half
    a minute.
    """
    import zipfile

    try:
        if not zipfile.is_zipfile(archive):
            return False
        stamp = _container_stamp(archive)
        found = 0
        with zipfile.ZipFile(archive) as zf:
            index = {name.replace("\\", "/"): name for name in zf.namelist()}
            for item, internal in entries:
                name = index.get(internal.replace("\\", "/"))
                if name is None:
                    continue
                found += 1

                def _read(name: str = name) -> tuple[int, int] | None:
                    try:
                        with zf.open(name) as fh:
                            return _image_size_from_stream(fh)
                    except Exception:
                        return None

                size = _cached_page_size("%s|%s" % (stamp, name) if stamp else "", _read)
                if size:
                    sizes[str(item.get("relPath") or "")] = size
        return found > 0
    except Exception:
        logger.debug("Probe zip page sizes: %s", archive, exc_info=True)
        return False


def _probe_7z_page_sizes(archive: str, entries: list[tuple[dict[str, Any], str]],
                         sizes: dict[str, tuple[int, int]],
                         ensure_kcc_path: Callable[[], None], logger: Any) -> None:
    """One 7z call per page -- what the sidebar already pays per thumbnail."""
    from concurrent.futures import ThreadPoolExecutor

    from PIL import Image

    stamp = _container_stamp(archive)

    def _measure(entry: tuple[dict[str, Any], str]) -> tuple[str, tuple[int, int] | None]:
        item, internal = entry

        def _read() -> tuple[int, int] | None:
            try:
                result = run_7z(["e", "-so", archive, internal], timeout=30,
                                ensure_kcc_path=ensure_kcc_path)
            except Exception:
                return None
            if result is None or result.returncode != 0 or not result.stdout:
                return None
            try:
                with Image.open(io.BytesIO(result.stdout)) as image:
                    return (int(image.width), int(image.height))
            except Exception:
                return None

        key = "%s|%s" % (stamp, internal) if stamp else ""
        return str(item.get("relPath") or ""), _cached_page_size(key, _read)

    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for rel, size in pool.map(_measure, entries):
                if rel and size:
                    sizes[rel] = size
    except Exception:
        logger.debug("Probe archive page sizes: %s", archive, exc_info=True)


def _probe_page_sizes(files: list[dict[str, Any]], ensure_kcc_path: Callable[[], None],
                      logger: Any) -> dict[str, tuple[int, int]]:
    """Measure every scanned page, reading headers rather than whole images."""
    from PIL import Image

    loose: list[dict[str, Any]] = []
    by_archive: dict[str, list[tuple[dict[str, Any], str]]] = {}
    for item in files:
        raw = str(item.get("path") or "")
        if not raw:
            continue
        if ARCHIVE_SEP in raw:
            archive, internal = raw.split(ARCHIVE_SEP, 1)
            by_archive.setdefault(archive, []).append((item, internal))
        else:
            loose.append(item)

    sizes: dict[str, tuple[int, int]] = {}
    for item in loose:
        path = str(item["path"])

        def _read(path: str = path) -> tuple[int, int] | None:
            try:
                with Image.open(path) as image:
                    return (int(image.width), int(image.height))
            except Exception:
                return None

        size = _cached_page_size(_container_stamp(path), _read)
        if size:
            sizes[str(item.get("relPath") or "")] = size

    for archive, entries in by_archive.items():
        if os.path.splitext(archive)[1].lower() == ".pdf":
            _probe_pdf_page_sizes(archive, entries, sizes, logger)
            continue
        if _probe_zip_page_sizes(archive, entries, sizes, logger):
            continue
        _probe_7z_page_sizes(archive, entries, sizes, ensure_kcc_path, logger)

    return sizes


def _spread_scan_fingerprint(
    source: str,
    files: list[dict[str, Any]],
    canvas: tuple[int, int],
) -> str | None:
    """Identify this page listing without opening any image data.

    Loose pages contribute their own stat, archive/PDF pages their container's
    stat. The complete relative-path listing catches added and removed pages.
    Bump the version when the spread classification rule changes.
    """
    digest = hashlib.sha256()

    def _add(value: Any) -> None:
        digest.update(json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii"))
        digest.update(b"\n")

    _add([1, os.path.normcase(os.path.realpath(source)), canvas])
    stamps: dict[str, str] = {}
    if not os.path.isdir(source):
        stamp = _container_stamp(source)
        if not stamp:
            return None
        stamps[source] = stamp
        _add(stamp)
    for item in files:
        raw = str(item.get("path") or "")
        rel = str(item.get("relPath") or "")
        if not raw or not rel:
            return None
        container, _, internal = raw.partition(ARCHIVE_SEP)
        if container not in stamps:
            stamp = _container_stamp(container)
            if not stamp:
                return None
            stamps[container] = stamp
        _add([rel, stamps[container], internal])
    return digest.hexdigest()


def scan_spread_pages(
    source: str,
    ensure_kcc_path: Callable[[], None],
    load_sidecar: Callable[[str], dict[str, Any]],
    save_sidecar: Callable[..., Any],
    logger: Any,
) -> dict[str, Any]:
    """Keep the automatic crop away from the pages that get cut in two.

    A spread is bisected, and the crop then chases the ink of each half on its
    own: the halves come back trimmed differently and stop meeting at the seam.
    So every wide page is marked No Crop the first time its source is opened.
    Which pages that has already been done for is written to the sidecar, so a
    page un-marked by hand is never marked again.
    """
    from ._image_pipeline import NATIVE_PAGE_HEIGHT, NATIVE_PAGE_WIDTH, spread_plan

    payload = scan_source_entries(
        source=source,
        ensure_kcc_path=ensure_kcc_path,
        load_sidecar=load_sidecar,
        logger=logger,
    )
    if not payload.get("ok"):
        return {"ok": False, "error": str(payload.get("error") or "scan failed")}

    files = cast(list[dict[str, Any]], payload.get("files") or [])
    canvas = (NATIVE_PAGE_WIDTH, NATIVE_PAGE_HEIGHT)
    fingerprint = _spread_scan_fingerprint(source, files, canvas)
    data = load_sidecar(source)
    cached = data.get("spread-scan")
    relpaths = [str(item.get("relPath") or "") for item in files]
    relpath_set = set(relpaths)
    cache_valid = (fingerprint is not None and isinstance(cached, dict)
                   and cached.get("fingerprint") == fingerprint
                   and isinstance(cached.get("spreads"), list)
                   and all(isinstance(rel, str) and rel in relpath_set for rel in cached["spreads"]))
    scan_cache = None
    if cache_valid:
        cached_spreads = set(cached["spreads"])
        spreads = [rel for rel in relpaths if rel in cached_spreads]
    else:
        sizes = _probe_page_sizes(files, ensure_kcc_path, logger)
        # Anything but "single": a page too wide to bisect is rotated instead,
        # and its edges are no more croppable than a bisected one's.
        spreads = [rel for rel in relpaths
                   if rel and spread_plan(sizes.get(rel, (0, 0)), canvas) != "single"]
        # Failed or changing pages must be retried next time. A completed empty
        # result is useful too, and cannot be inferred from legacy No Crop data.
        if (fingerprint is not None and all(rel in sizes for rel in relpaths)
                and _spread_scan_fingerprint(source, files, canvas) == fingerprint):
            scan_cache = {"fingerprint": fingerprint, "spreads": spreads}

    # Preserve manual changes made while a potentially long first scan ran.
    data = load_sidecar(source)
    offered = {str(x) for x in (data.get("auto-no-crop") or [])}
    marked = {str(x) for x in (data.get("no-crop") or [])}
    applied = [rel for rel in spreads if rel not in offered and rel not in marked]
    update_marks = applied or not offered.issuperset(spreads)
    if update_marks or scan_cache is not None:
        try:
            updates: dict[str, Any] = {}
            if update_marks:
                updates["nocrop"] = sorted(marked | set(applied))
                updates["auto_nocrop"] = sorted(offered | set(spreads))
            if scan_cache is not None:
                updates["spread_scan"] = scan_cache
            save_sidecar(source, **updates)
        except Exception:
            logger.debug("Failed to record auto No Crop for %s", source, exc_info=True)

    return {"ok": True, "spreads": spreads, "applied": applied}


def _ensure_kcc_importable() -> None:
    if "kindlecomicconverter" in sys.modules:
        return
    if KCC_DIR and os.path.isdir(KCC_DIR) and KCC_DIR not in sys.path:
        sys.path.insert(0, KCC_DIR)


def _load_image_bytes(raw_path: str, allowed_roots: list[str]) -> bytes | None:
    if os.path.isfile(raw_path):
        with open(raw_path, "rb") as fh:
            return fh.read()
    if ARCHIVE_SEP not in raw_path:
        return None

    archive, internal = raw_path.split(ARCHIVE_SEP, 1)
    from .path_access import is_safe_archive_internal_path, is_under_allowed_root

    if not is_under_allowed_root(archive, allowed_roots):
        return None
    if not (internal.startswith("page:") or is_safe_archive_internal_path(internal)):
        return None

    if internal.startswith("page:"):
        try:
            page_num = int(internal.split(":")[1])
            import pymupdf

            doc = pymupdf.open(archive)
            page = cast(Any, doc[page_num])
            pix = page.get_pixmap(matrix=pymupdf.Matrix(0.5, 0.5))
            data = pix.tobytes("png")
            doc.close()
            return cast(bytes, data)
        except Exception:
            return None

    if os.path.isfile(archive):
        try:
            result = run_7z(["e", "-so", archive, internal], timeout=15)
            if result is not None and result.returncode == 0 and result.stdout:
                return cast(bytes, result.stdout)
        except Exception:
            return None
    return None


def _hist_sign(histogram: list[int]) -> int:
    if histogram[0] == 0:
        return -1
    if histogram[255] == 0:
        return 1
    return 0


def _detect_fill_color(img: Any, explicit: str) -> str:
    if explicit == "white":
        return "white"
    if explicit == "black":
        return "black"

    from PIL import ImageChops

    bw = img.convert("L").point(lambda x: 0 if x < 128 else 255, "1")
    image_box_a = bw.getbbox()
    image_box_b = ImageChops.invert(bw).getbbox()
    if image_box_a is None or image_box_b is None:
        surface_b, surface_w, diff = 0.0, 0.0, 0.0
    else:
        surface_b = float((image_box_a[2] - image_box_a[0]) * (image_box_a[3] - image_box_a[1]))
        surface_w = float((image_box_b[2] - image_box_b[0]) * (image_box_b[3] - image_box_b[1]))
        mn = min(surface_b, surface_w)
        diff = ((max(surface_b, surface_w) - mn) / mn) * 100.0 if mn > 0 else 0.0

    if diff > 0.5:
        return "white" if surface_w < surface_b else "black"

    fill_score = 0
    start_y = 0
    while start_y < bw.size[1]:
        if start_y + 5 > bw.size[1]:
            start_y = bw.size[1] - 5
        fill_score += _hist_sign(bw.crop((0, start_y, bw.size[0], start_y + 5)).histogram())
        start_y += 5
    start_x = 0
    while start_x < bw.size[0]:
        if start_x + 5 > bw.size[0]:
            start_x = bw.size[0] - 5
        fill_score += _hist_sign(bw.crop((start_x, 0, start_x + 5, bw.size[1])).histogram())
        start_x += 5
    return "black" if fill_score > 0 else "white"


def _kcc_mode_output_rank(mode: str, rotate_first: bool) -> int:
    mode = mode.upper()
    if mode == "R":
        return 0 if rotate_first else 3
    if mode == "S1":
        return 1
    if mode == "S2":
        return 2
    if mode == "N":
        return 4
    return 99


def _kcc_split_modes(
    width: int,
    height: int,
    dstwidth: int,
    dstheight: int,
    *,
    splitter: int,
    webtoon: bool,
    no_processing: bool,
) -> list[str]:
    if no_processing:
        return ["N"]

    orientation_mismatch = (width > height) != (dstwidth > dstheight)
    if orientation_mismatch and width <= dstheight and height <= dstwidth and not webtoon and splitter == 1:
        return ["R"]
    if orientation_mismatch and not webtoon:
        modes: list[str] = []
        if splitter != 1:
            modes.extend(["S1", "S2"])
        if splitter > 0:
            modes.append("R")
        if modes:
            return modes
    return ["N"]


def _maic_split_modes(
    width: int,
    height: int,
    dstwidth: int,
    dstheight: int,
    *,
    rotate_spreads: bool,
    no_processing: bool,
) -> list[str]:
    """What the native writers make of a page, as preview variant codes.

    KCC decides from the orientation alone plus its splitter tri-state; the
    native path has no splitter and adds the two ratio thresholds, so the two
    disagree about a barely landscape page and about a panorama.  The preview
    follows whichever rule is going to build the book.
    """
    if no_processing:
        return ["N"]
    from ._image_pipeline import spread_plan

    plan = spread_plan((width, height), (dstwidth, dstheight), rotate_spreads)
    if plan == "split":
        return ["S1", "S2"]
    if plan == "rotate":
        return ["R"]
    return ["N"]


def _apply_kcc_variant_transform(
    image: Any,
    mode: str,
    *,
    no_rotate: bool,
    manga_mode: bool,
) -> Any:
    from PIL import Image

    if not hasattr(Image, "Resampling"):
        Image.Resampling = Image

    mode_up = mode.upper()
    if mode_up == "R":
        if no_rotate:
            return image.copy()
        return image.rotate(90, Image.Resampling.BICUBIC, True)
    if mode_up not in {"S1", "S2"}:
        return image.copy()

    width, height = image.size
    if width > height:
        leftbox = (0, 0, int(width / 2), height)
        rightbox = (int(width / 2), 0, width, height)
    else:
        leftbox = (0, 0, width, int(height / 2))
        rightbox = (0, int(height / 2), width, height)
    if manga_mode:
        pageone = image.crop(rightbox)
        pagetwo = image.crop(leftbox)
    else:
        pageone = image.crop(leftbox)
        pagetwo = image.crop(rightbox)
    return pageone if mode_up == "S1" else pagetwo


def _build_preview_variants(
    image: Any,
    *,
    splitter: int,
    no_rotate: bool,
    rotate_first: bool,
    manga_mode: bool,
    webtoon: bool,
    no_processing: bool,
    profile_width: int,
    profile_height: int,
    native: bool = False,
) -> tuple[dict[str, Any], list[str], list[str]]:
    width, height = image.size
    dstwidth = profile_width if profile_width > 0 else width
    dstheight = profile_height if profile_height > 0 else height
    if native:
        modes = _maic_split_modes(
            width,
            height,
            dstwidth,
            dstheight,
            rotate_spreads=not no_rotate,
            no_processing=no_processing,
        )
    else:
        modes = _kcc_split_modes(
            width,
            height,
            dstwidth,
            dstheight,
            splitter=splitter,
            webtoon=webtoon,
            no_processing=no_processing,
        )
    variants: dict[str, Any] = {}
    for mode in modes:
        variants[mode] = _apply_kcc_variant_transform(
            image,
            mode,
            # The native path has no "leave it unturned" state: with No rotate
            # on it bisects the panorama instead, so an "R" here is a real turn.
            no_rotate=no_rotate and not native,
            manga_mode=manga_mode,
        )
    if "N" not in variants:
        variants["N"] = image.copy()
    available = modes if "N" in modes else ["N"] + list(modes)
    output_modes = sorted(modes, key=lambda m: (_kcc_mode_output_rank(m, rotate_first), m))
    return variants, available, output_modes


def _resolve_preview_variant(requested: str, available: list[str], output_modes: list[str]) -> str:
    req = str(requested or "auto").strip().upper()
    if req in available:
        return req
    if req == "AUTO":
        if output_modes:
            return output_modes[0]
        if available:
            return available[0]
    return "N" if "N" in available else (available[0] if available else "N")


def _to_contiguous_ranges(indices: list[int]) -> list[list[int]]:
    if not indices:
        return []
    out: list[list[int]] = []
    start = indices[0]
    prev = indices[0]
    for value in indices[1:]:
        if value == prev + 1:
            prev = value
            continue
        out.append([int(start), int(prev)])
        start = value
        prev = value
    out.append([int(start), int(prev)])
    return out


def _apply_preview_edit_ops(image: Any, edit_ops: Any) -> Any:
    if not isinstance(edit_ops, list) or not edit_ops:
        return image
    try:
        from PIL import ImageDraw
    except Exception:
        return image

    out = image.copy()
    draw = ImageDraw.Draw(out)
    for op in edit_ops:
        if not isinstance(op, dict):
            continue
        color = str(op.get("color", "#fff") or "#fff")
        try:
            if op.get("type") == "rect":
                x = int(op.get("x", 0))
                y = int(op.get("y", 0))
                w = int(op.get("w", 0))
                h_val = int(op.get("h", 0))
                if w > 0 and h_val > 0:
                    draw.rectangle([x, y, x + w, y + h_val], fill=color)
            elif op.get("type") == "brush":
                pts = op.get("points", [])
                if not isinstance(pts, list) or not pts:
                    continue
                size = max(1, int(op.get("size", 20)))
                radius = size // 2
                if len(pts) == 1:
                    cx, cy = int(pts[0][0]), int(pts[0][1])
                    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)
                else:
                    clean_pts = [(int(pt[0]), int(pt[1])) for pt in pts if isinstance(pt, (list, tuple)) and len(pt) >= 2]
                    if len(clean_pts) >= 2:
                        draw.line(clean_pts, fill=color, width=size)
                    for cx, cy in clean_pts:
                        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)
        except Exception:
            continue
    return out


def compute_crop_preview(
    path: str,
    power: float,
    mode: int,
    preserve_margin_h: int,
    preserve_margin_v: int,
    allowed_roots: list[str],
    *,
    inter_panel_crop: int = 0,
    borders_color: str = "none",
    webtoon: bool = False,
    no_processing: bool = False,
    cropping_minimum: float = 0.0,
    preview_variant: str = "auto",
    splitter: int = 0,
    no_rotate: bool = False,
    rotate_first: bool = False,
    native: bool = False,
    manga_mode: bool = False,
    profile_width: int = 0,
    profile_height: int = 0,
    edit_ops: Any = None,
    maic_crop: bool = False,
    maic_margin_pct: float = 0.6,
    maic_watermarks: bool = False,
    maic_watermark_page_enabled: bool = True,
    maic_page_numbers: bool = False,
    cleanup_method: str = "lama",
    cleanup_padding: int = 2,
    page_number_scope: str = "",
    minimum_page_number: int = 1,
) -> dict[str, Any]:
    """Compute preview crop data using the same crop algorithms as KCC."""
    try:
        from PIL import Image, ImageFilter, ImageOps
    except Exception:
        return {"ok": False, "error": "Pillow not available"}

    def _clamp_box_for_kcc(box: tuple[float, float, float, float], img_w: int, img_h: int) -> tuple[float, float, float, float]:
        left, upper, right, lower = box
        return (
            min(0.1 * img_w, left),
            min(0.1 * img_h, upper),
            max(0.9 * img_w, right),
            max(0.9 * img_h, lower),
        )

    def _preserve_margin_box(box: tuple[float, float, float, float], img_w: int, img_h: int, pm_h: int, pm_v: int) -> tuple[float, float, float, float]:
        rh = 1.0 - (pm_h / 100.0)
        rv = 1.0 - (pm_v / 100.0)
        left, upper, right, lower = box
        return (
            left * rh,
            upper * rv,
            right + (img_w - right) * (1.0 - rh),
            lower + (img_h - lower) * (1.0 - rv),
        )


    if not path:
        return {"ok": False, "error": "no path"}

    img_bytes = _load_image_bytes(path, allowed_roots)
    if not img_bytes:
        return {"ok": False, "error": "cannot read image"}

    try:
        source_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        return {"ok": False, "error": "decode failed"}
    source_image = _apply_preview_edit_ops(source_image, edit_ops)
    artifact_ignore_mask = None
    watermark_matches: list[dict[str, Any]] = []
    watermarks_removed = 0
    watermark_decision: dict[str, Any] = {}
    if bool(maic_watermarks) and bool(maic_watermark_page_enabled) and not bool(no_processing):
        try:
            from .autonomous import (
                _load_artifact_profiles,
                _peripheral_artifact_ignore_mask,
                _reference_artifact_cleanup,
            )

            watermark_profiles = _load_artifact_profiles("")
            artifact_ignore_mask, watermark_matches = _peripheral_artifact_ignore_mask(
                source_image,
                watermark_profiles,
            )
            source_image, watermarks_removed, watermark_decision = _reference_artifact_cleanup(
                source_image,
                watermark_profiles,
                max(0, min(100, int(cleanup_padding))),
                precomputed_candidates=watermark_matches,
            )
        except Exception:
            artifact_ignore_mask = None
            watermark_matches = []
            watermarks_removed = 0
            watermark_decision = {}
    page_numbers_removed = 0
    page_number_decision: dict[str, Any] = {}
    page_number_error = ""
    if bool(maic_page_numbers) and not bool(no_processing):
        cleanup_key = _page_number_preview_cache_key(
            img_bytes,
            edit_ops,
            str(cleanup_method or "lama"),
            int(cleanup_padding),
            page_number_scope,
            minimum_page_number,
        )
        source_image, page_numbers_removed, page_number_decision, page_number_error = (
            _apply_preview_page_number_cleanup(
                source_image,
                cleanup_key,
                method=str(cleanup_method or "lama"),
                padding=max(0, min(100, int(cleanup_padding))),
                page_number_scope=page_number_scope,
                minimum_page_number=minimum_page_number,
            )
        )
    preview_source_image = source_image
    maic_source_crop = {
        "top": 0,
        "bottom": source_image.height - 1,
        "left": 0,
        "right": source_image.width - 1,
    }
    maic_crop_applied = False
    try:
        safe_maic_margin_pct = max(0.0, min(10.0, float(maic_margin_pct)))
    except (TypeError, ValueError):
        safe_maic_margin_pct = 0.6
    maic_margin_px = int(
        math.floor(min(source_image.width, source_image.height) * safe_maic_margin_pct / 100.0 + 0.5)
    )
    maic_preview_crop: dict[str, int] | None = None
    maic_content_crop: dict[str, int] | None = None
    if bool(maic_crop) and not bool(no_processing) and not bool(webtoon):
        try:
            from .autonomous import apply_maic_crop

            maic_target_size = None
            if bool(native) and int(profile_width or 0) > 0 and int(profile_height or 0) > 0:
                from ._image_pipeline import page_render_canvas, spread_plan

                render_canvas = page_render_canvas((int(profile_width), int(profile_height)))
                if spread_plan(source_image.size, render_canvas, not bool(no_rotate)) == "single":
                    maic_target_size = render_canvas

            source_image, maic_source_crop, maic_crop_applied = apply_maic_crop(
                source_image,
                preserved_margin_percent=maic_margin_pct,
                target_size=maic_target_size,
                artifact_ignore_mask=artifact_ignore_mask,
            )
        except Exception:
            maic_crop_applied = False

    safe_mode = int(mode) if isinstance(mode, (int, float)) else 0
    safe_mode = max(0, min(2, safe_mode))
    safe_pm_h = max(0, min(100, int(preserve_margin_h)))
    safe_pm_v = max(0, min(100, int(preserve_margin_v)))
    safe_power = float(power) if power else 1.0
    safe_power = max(0.1, min(10.0, safe_power))
    safe_ipc = max(0, int(inter_panel_crop))
    safe_splitter = max(0, min(2, int(splitter)))
    safe_fill = str(borders_color or "none").strip().lower()
    if safe_fill not in ("none", "white", "black"):
        safe_fill = "none"
    fill = _detect_fill_color(source_image, safe_fill)
    safe_cropping_min = max(0.0, float(cropping_minimum))
    safe_profile_w = max(0, int(profile_width))
    safe_profile_h = max(0, int(profile_height))
    variants, available_variants, output_variants = _build_preview_variants(
        source_image,
        splitter=safe_splitter,
        no_rotate=bool(no_rotate),
        rotate_first=bool(rotate_first),
        manga_mode=bool(manga_mode),
        webtoon=bool(webtoon),
        no_processing=bool(no_processing),
        profile_width=safe_profile_w,
        profile_height=safe_profile_h,
        native=bool(native),
    )
    selected_variant = _resolve_preview_variant(preview_variant, available_variants, output_variants)
    image = variants.get(selected_variant, source_image)
    width, height = image.size

    def _page_number_box_for_variant(raw_box: Any) -> list[int] | None:
        """Map source-space cleanup coordinates to the displayed preview."""
        if not isinstance(raw_box, (list, tuple)) or len(raw_box) != 4:
            return None
        source_width, source_height = preview_source_image.size
        x1, y1, x2, y2 = [int(value) for value in raw_box]
        x1, y1 = max(0, min(source_width, x1)), max(0, min(source_height, y1))
        x2, y2 = max(x1, min(source_width, x2)), max(y1, min(source_height, y2))
        variant = str(selected_variant or "N").upper()
        if variant == "R" and not bool(no_rotate):
            return [y1, source_width - x2, y2, source_width - x1]
        if variant not in {"S1", "S2"}:
            return [x1, y1, x2, y2]
        if source_width > source_height:
            first = (0, 0, source_width // 2, source_height)
            second = (source_width // 2, 0, source_width, source_height)
        else:
            first = (0, 0, source_width, source_height // 2)
            second = (0, source_height // 2, source_width, source_height)
        page_one, page_two = (second, first) if manga_mode else (first, second)
        region = page_one if variant == "S1" else page_two
        rx1, ry1, rx2, ry2 = region
        ix1, iy1, ix2, iy2 = max(x1, rx1), max(y1, ry1), min(x2, rx2), min(y2, ry2)
        if ix2 <= ix1 or iy2 <= iy1:
            return None
        return [ix1 - rx1, iy1 - ry1, ix2 - rx1, iy2 - ry1]

    page_number_preview_boxes = []
    for raw_box in page_number_decision.get("boxes", []) if isinstance(page_number_decision, dict) else []:
        mapped_box = _page_number_box_for_variant(raw_box)
        if mapped_box is not None:
            page_number_preview_boxes.append(mapped_box)

    watermark_preview_matches = []
    for match in watermark_matches:
        if not isinstance(match, dict):
            continue
        mapped_box = _page_number_box_for_variant(match.get("box"))
        if mapped_box is not None:
            watermark_preview_matches.append({
                **{key: value for key, value in match.items() if key != "box"},
                "box": mapped_box,
            })

    crop_box = (0.0, 0.0, float(width), float(height))
    crop_applied = False

    if not no_processing and not webtoon and safe_mode in (1, 2):
        try:
            _ensure_kcc_importable()
            from kindlecomicconverter.page_number_crop_alg import (
                get_bbox_crop_margin,
                get_bbox_crop_margin_page_number,
            )
        except Exception:
            return {"ok": False, "error": "KCC crop helpers not available"}

        bbox: tuple[Any, Any, Any, Any] | None
        if safe_mode == 2:
            bbox = get_bbox_crop_margin_page_number(image, safe_power, fill)
        else:
            bbox = get_bbox_crop_margin(image, safe_power, fill)
        if bbox:
            left, upper, right, lower = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
            crop_box = _clamp_box_for_kcc((left, upper, right, lower), width, height)
            if safe_pm_h > 0 or safe_pm_v > 0:
                crop_box = _preserve_margin_box(crop_box, width, height, safe_pm_h, safe_pm_v)
            box_area = max(0.0, (crop_box[2] - crop_box[0]) * (crop_box[3] - crop_box[1]))
            image_area = float(width * height) if width > 0 and height > 0 else 1.0
            if box_area / image_area >= safe_cropping_min:
                crop_applied = True
            else:
                crop_box = (0.0, 0.0, float(width), float(height))

    top_i = max(0, min(height - 1, int(math.floor(crop_box[1]))))
    left_i = max(0, min(width - 1, int(math.floor(crop_box[0]))))
    bottom_i = max(top_i, min(height - 1, int(math.ceil(crop_box[3])) - 1))
    right_i = max(left_i, min(width - 1, int(math.ceil(crop_box[2])) - 1))

    inter_rows: list[list[int]] = []
    inter_cols: list[list[int]] = []
    if not no_processing and safe_ipc > 0:
        try:
            _ensure_kcc_importable()
            from kindlecomicconverter.common_crop import threshold_from_power
            from kindlecomicconverter.inter_panel_crop_alg import empty_sections

            panel_img = image.crop((left_i, top_i, right_i + 1, bottom_i + 1))
            panel_temp = panel_img
            if panel_temp.mode != "L":
                panel_temp = ImageOps.grayscale(panel_temp)
            if fill != "white":
                panel_temp = ImageOps.invert(panel_temp)
            panel_temp = ImageOps.autocontrast(panel_temp, 1).filter(ImageFilter.BoxBlur(1))
            threshold = threshold_from_power(1)
            panel_temp = panel_temp.point(lambda p: 255 if p <= threshold else 0)

            rows_idx: list[int] = []
            cols_idx: list[int] = []
            if safe_ipc in (1, 2):
                rows_idx = [int(v) for v in list(empty_sections(panel_temp, 0.04, horizontal=True))]
            if safe_ipc >= 2:
                cols_idx = [int(v) for v in list(empty_sections(panel_temp, 0.04, horizontal=False))]

            for start, end in _to_contiguous_ranges(rows_idx):
                inter_rows.append([top_i + start, top_i + end])
            for start, end in _to_contiguous_ranges(cols_idx):
                inter_cols.append([left_i + start, left_i + end])
        except Exception:
            inter_rows = []
            inter_cols = []

    # The conversion pipeline crops with maic before KCC, but the preview keeps
    # showing the original page and visualizes the resulting cut with the same
    # shaded overlay used for KCC. Translate the final processing-space crop
    # back into coordinates of the displayed preview variant.
    if maic_crop_applied:
        original_width, original_height = preview_source_image.size
        variant = str(selected_variant or "N").upper()
        processing_variant_width, processing_variant_height = image.size

        def _split_region(img_w: int, img_h: int, mode_name: str) -> tuple[int, int, int, int]:
            if mode_name not in {"S1", "S2"}:
                return 0, 0, img_w, img_h
            if img_w > img_h:
                first = (0, 0, img_w // 2, img_h)
                second = (img_w // 2, 0, img_w, img_h)
            else:
                first = (0, 0, img_w, img_h // 2)
                second = (0, img_h // 2, img_w, img_h)
            page_one, page_two = (second, first) if manga_mode else (first, second)
            return page_one if mode_name == "S1" else page_two

        def _map_box(box: dict[str, int]) -> dict[str, int]:
            if variant == "R" and not bool(no_rotate):
                region_left = int(maic_source_crop["top"])
                region_top = original_width - 1 - int(maic_source_crop["right"])
                return {
                    "top": region_top + int(box["top"]),
                    "bottom": region_top + int(box["bottom"]),
                    "left": region_left + int(box["left"]),
                    "right": region_left + int(box["right"]),
                }

            proc_x0, proc_y0, _, _ = _split_region(
                source_image.width, source_image.height, variant
            )
            view_x0, view_y0, _, _ = _split_region(original_width, original_height, variant)
            return {
                "top": int(maic_source_crop["top"]) + proc_y0 + int(box["top"]) - view_y0,
                "bottom": int(maic_source_crop["top"]) + proc_y0 + int(box["bottom"]) - view_y0,
                "left": int(maic_source_crop["left"]) + proc_x0 + int(box["left"]) - view_x0,
                "right": int(maic_source_crop["left"]) + proc_x0 + int(box["right"]) - view_x0,
            }

        maic_preview_crop = _map_box({
            "top": 0,
            "bottom": processing_variant_height - 1,
            "left": 0,
            "right": processing_variant_width - 1,
        })
        if variant == "N" or (variant == "R" and bool(no_rotate)):
            maic_content_crop = _map_box({
                "top": maic_margin_px if int(maic_source_crop["top"]) > 0 else 0,
                "bottom": source_image.height - 1 - (
                    maic_margin_px if int(maic_source_crop["bottom"]) < original_height - 1 else 0
                ),
                "left": maic_margin_px if int(maic_source_crop["left"]) > 0 else 0,
                "right": source_image.width - 1 - (
                    maic_margin_px if int(maic_source_crop["right"]) < original_width - 1 else 0
                ),
            })

        if variant == "R" and not bool(no_rotate):
            display_width, display_height = original_height, original_width
        else:
            vx0, vy0, vx1, vy1 = _split_region(original_width, original_height, variant)
            display_width, display_height = max(1, vx1 - vx0), max(1, vy1 - vy0)

        mapped_crop = _map_box({
            "top": top_i,
            "bottom": bottom_i,
            "left": left_i,
            "right": right_i,
        })
        top_i = max(0, min(display_height - 1, mapped_crop["top"]))
        bottom_i = max(top_i, min(display_height - 1, mapped_crop["bottom"]))
        left_i = max(0, min(display_width - 1, mapped_crop["left"]))
        right_i = max(left_i, min(display_width - 1, mapped_crop["right"]))
        width, height = display_width, display_height
        crop_applied = True

        if variant == "N" or (variant == "R" and bool(no_rotate)):
            inter_rows = [
                [int(maic_source_crop["top"]) + row[0], int(maic_source_crop["top"]) + row[1]]
                for row in inter_rows
            ]
            inter_cols = [
                [int(maic_source_crop["left"]) + col[0], int(maic_source_crop["left"]) + col[1]]
                for col in inter_cols
            ]
        else:
            inter_rows = []
            inter_cols = []

    return {
        "ok": True,
        "width": int(width),
        "height": int(height),
        "crop": {"top": int(top_i), "bottom": int(bottom_i), "left": int(left_i), "right": int(right_i)},
        "fill": fill,
        "mode": int(safe_mode),
        "crop_applied": bool(crop_applied),
        "maic_crop_applied": bool(maic_crop_applied),
        "maic_source_crop": maic_source_crop,
        "maic_preview_crop": maic_preview_crop,
        "maic_content_crop": maic_content_crop,
        "maic_margin_pct": safe_maic_margin_pct,
        "maic_margin_px": maic_margin_px,
        "maic_page_numbers_removed": int(page_numbers_removed),
        "maic_watermark_matches": watermark_matches,
        "maic_watermark_preview_matches": watermark_preview_matches,
        "maic_watermark_page_enabled": bool(maic_watermark_page_enabled),
        "maic_watermarks_removed": int(watermarks_removed),
        "maic_watermark_decision": watermark_decision,
        "maic_page_number_decision": page_number_decision,
        "maic_page_number_preview_boxes": page_number_preview_boxes,
        "maic_page_number_error": page_number_error,
        "inter_panel": {"rows": inter_rows, "cols": inter_cols, "mode": int(safe_ipc)},
        "preview_variant": selected_variant,
        "available_variants": [str(v) for v in available_variants],
        "output_variants": [str(v) for v in output_variants],
        "bg": None,
    }


_SOURCE_THUMB_CACHE: OrderedDict[tuple[str, str], bytes] = OrderedDict()
_SOURCE_THUMB_LOCK = threading.RLock()
_SOURCE_THUMB_CACHE_LIMIT = 512


def _source_thumbnail_bytes(image_bytes: bytes) -> bytes:
    """Decode at thumbnail resolution where possible, then encode only once."""
    from PIL import Image

    with Image.open(io.BytesIO(image_bytes)) as image:
        # JPEG can discard resolution during decoding. Converting to RGB first
        # forces a full decode, which is expensive for every sidebar page.
        image.draft("RGB", (200, 200))
        if image.mode == "P":
            image = image.convert("RGB")
        image.thumbnail((200, 200), Image.Resampling.LANCZOS)
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=85)
        return output.getvalue()


def serve_thumb_response(
    path: str,
    full: str,
    allowed_roots: list[str],
    fail: Callable[..., Any],
    ec: Any,
    *,
    preview_variant: str = "auto",
    splitter: int = 0,
    no_rotate: bool = False,
    rotate_first: bool = False,
    native: bool = False,
    manga_mode: bool = False,
    webtoon: bool = False,
    no_processing: bool = False,
    profile_width: int = 0,
    profile_height: int = 0,
    maic_crop: bool = False,
    edit_ops: Any = None,
    maic_watermarks: bool = False,
    maic_watermark_page_enabled: bool = True,
    maic_page_numbers: bool = False,
    cleanup_method: str = "lama",
    cleanup_padding: int = 2,
    page_number_scope: str = "",
    minimum_page_number: int = 1,
    erase_artifacts: bool = True,
) -> Any:
    """Build response for thumbnail/full image from file or archive.

    ``erase_artifacts=False`` keeps a found watermark or folio on the page:
    the Crop preview marks it with a mask over the original, and only the
    Final image shows the spot erased.
    """
    from flask import make_response, send_file

    if not path:
        return fail("path must be provided", code=ec.INVALID_PAYLOAD, status=400)

    thumb_size = 200

    # Sidebar requests contain only a path. They need the original page in
    # miniature, not a full preview transform and a second JPEG decode.
    raw_thumbnail = (
        not full
        and str(preview_variant or "auto").strip().upper() in {"AUTO", "N"}
        and not any((splitter, no_rotate, rotate_first, native, manga_mode,
                     webtoon, no_processing, maic_crop, edit_ops,
                     maic_watermarks, maic_page_numbers))
        and profile_width <= 0
        and profile_height <= 0
    )

    def _raw_thumb(stamp: str, internal: str, read_bytes: Callable[[], bytes]) -> Any:
        key = (stamp, internal)
        thumbnail = None
        if stamp:
            with _SOURCE_THUMB_LOCK:
                thumbnail = _SOURCE_THUMB_CACHE.get(key)
                if thumbnail is not None:
                    _SOURCE_THUMB_CACHE.move_to_end(key)
        if thumbnail is None:
            data = read_bytes()
            try:
                thumbnail = _source_thumbnail_bytes(data)
            except Exception:
                return _make_thumb(data)
            if stamp:
                with _SOURCE_THUMB_LOCK:
                    _SOURCE_THUMB_CACHE[key] = thumbnail
                    while len(_SOURCE_THUMB_CACHE) > _SOURCE_THUMB_CACHE_LIMIT:
                        _SOURCE_THUMB_CACHE.popitem(last=False)
        resp = make_response(thumbnail)
        resp.mimetype = "image/jpeg"
        resp.headers["Cache-Control"] = "private, max-age=300"
        return resp

    def _make_thumb(img_bytes: bytes, mime: str = "image/jpeg") -> Any:
        if full:
            resp = make_response(send_file(io.BytesIO(img_bytes), mimetype=mime))
            resp.headers["Cache-Control"] = "private, max-age=5"
            return resp
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(img_bytes))
            img.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            if img.mode in ("RGBA", "P"):
                img_rgb = img.convert("RGB")
                img_rgb.save(buf, format="JPEG", quality=85)
            else:
                img.save(buf, format="JPEG", quality=85)
            buf.seek(0)
            resp = make_response(send_file(buf, mimetype="image/jpeg"))
        except Exception:
            resp = make_response(send_file(io.BytesIO(img_bytes), mimetype=mime))
        resp.headers["Cache-Control"] = "private, max-age=300"
        return resp

    def _transform_for_preview(data: bytes, mime: str) -> tuple[bytes, str]:
        safe_splitter = max(0, min(2, int(splitter)))
        try:
            from PIL import Image
        except Exception:
            return data, mime
        try:
            opened = Image.open(io.BytesIO(data))
            # Crop preview leaves the source pixels intact and draws its masks
            # in the browser. A normal JPEG needs no full decode and re-encode
            # when the selected variant is the unsplit, unrotated page.
            if (not erase_artifacts and not edit_ops and opened.format == "JPEG"
                    and opened.mode == "RGB" and opened.getexif().get(274, 1) == 1):
                width, height = opened.size
                dstwidth = profile_width if profile_width > 0 else width
                dstheight = profile_height if profile_height > 0 else height
                if native:
                    modes = _maic_split_modes(width, height, dstwidth, dstheight,
                                              rotate_spreads=not no_rotate,
                                              no_processing=no_processing)
                else:
                    modes = _kcc_split_modes(width, height, dstwidth, dstheight,
                                             splitter=safe_splitter, webtoon=webtoon,
                                             no_processing=no_processing)
                available = modes if "N" in modes else ["N"] + list(modes)
                output_modes = sorted(modes, key=lambda mode: (
                    _kcc_mode_output_rank(mode, rotate_first), mode))
                if _resolve_preview_variant(preview_variant, available, output_modes) == "N":
                    return data, "image/jpeg"
            source_image = opened.convert("RGB")
        except Exception:
            return data, mime
        source_image = _apply_preview_edit_ops(source_image, edit_ops)
        erase = bool(erase_artifacts) and not bool(no_processing)
        if erase and bool(maic_watermarks) and bool(maic_watermark_page_enabled):
            try:
                from .autonomous import (
                    _load_artifact_profiles,
                    _peripheral_artifact_ignore_mask,
                    _reference_artifact_cleanup,
                )

                profiles = _load_artifact_profiles("")
                _ignore_mask, matches = _peripheral_artifact_ignore_mask(source_image, profiles)
                source_image, _, _ = _reference_artifact_cleanup(
                    source_image,
                    profiles,
                    max(0, min(100, int(cleanup_padding))),
                    precomputed_candidates=matches,
                )
            except Exception:
                pass
        if erase and bool(maic_page_numbers):
            cleanup_key = _page_number_preview_cache_key(
                data,
                edit_ops,
                str(cleanup_method or "lama"),
                int(cleanup_padding),
                page_number_scope,
                minimum_page_number,
            )
            source_image, _, _, _ = _apply_preview_page_number_cleanup(
                source_image,
                cleanup_key,
                method=str(cleanup_method or "lama"),
                padding=max(0, min(100, int(cleanup_padding))),
                page_number_scope=page_number_scope,
                minimum_page_number=minimum_page_number,
            )
        variants, available_variants, output_variants = _build_preview_variants(
            source_image,
            splitter=safe_splitter,
            no_rotate=bool(no_rotate),
            rotate_first=bool(rotate_first),
            manga_mode=bool(manga_mode),
            webtoon=bool(webtoon),
            no_processing=bool(no_processing),
            profile_width=max(0, int(profile_width)),
            profile_height=max(0, int(profile_height)),
            native=bool(native),
        )
        selected_variant = _resolve_preview_variant(preview_variant, available_variants, output_variants)
        out_image = variants.get(selected_variant, source_image)
        buf = io.BytesIO()
        out_image.save(buf, format="JPEG", quality=90)
        return cast(bytes, buf.getvalue()), "image/jpeg"

    from .path_access import (
        is_allowed_image_file,
        is_safe_archive_internal_path,
        is_under_allowed_root,
    )

    if os.path.isfile(path):
        if not is_allowed_image_file(path, allowed_roots):
            return fail("Access denied", code=ec.INVALID_PATH, status=403)
        try:
            if raw_thumbnail:
                def _read_file() -> bytes:
                    with open(path, "rb") as fh:
                        return fh.read()

                return _raw_thumb(_container_stamp(path), "", _read_file)
            with open(path, "rb") as fh:
                data = fh.read()
            transformed, transformed_mime = _transform_for_preview(data, "image/jpeg")
            return _make_thumb(transformed, mime=transformed_mime)
        except Exception:
            return fail("Failed to read file", code=ec.IMAGE_READ_FAILED, status=500)

    if ARCHIVE_SEP in path:
        archive, internal = path.split(ARCHIVE_SEP, 1)
        if not is_under_allowed_root(archive, allowed_roots):
            return fail("Access denied", code=ec.INVALID_PATH, status=403)
        if not (internal.startswith("page:") or is_safe_archive_internal_path(internal)):
            return fail("Invalid archive path", code=ec.INVALID_PATH, status=400)

        if internal.startswith("page:"):
            try:
                page_num = int(internal.split(":")[1])
                import pymupdf

                if raw_thumbnail:
                    def _read_pdf_page() -> bytes:
                        with pymupdf.open(archive) as doc:
                            page = cast(Any, doc[page_num])
                            # Render directly near the sidebar's display size.
                            scale = 200 / max(page.rect.width, page.rect.height, 1)
                            pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale))
                            return cast(bytes, pix.tobytes("png"))

                    return _raw_thumb(_container_stamp(archive), internal, _read_pdf_page)

                doc = pymupdf.open(archive)
                page = cast(Any, doc[page_num])
                scale = 2.0 if full else 1.0
                pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale))
                img_bytes = pix.tobytes("jpeg")
                doc.close()
                transformed, transformed_mime = _transform_for_preview(img_bytes, "image/jpeg")
                return _make_thumb(transformed, mime=transformed_mime)
            except Exception:
                return fail("Failed to render PDF page", code=ec.IMAGE_READ_FAILED, status=500)

        if os.path.isfile(archive):
            try:
                if raw_thumbnail:
                    def _read_archive_member() -> bytes:
                        import zipfile

                        try:
                            with zipfile.ZipFile(archive) as zipped:
                                # Scan-source normalizes member separators.
                                names = {name.replace("\\", "/"): name for name in zipped.namelist()}
                                return zipped.read(names[internal.replace("\\", "/")])
                        except (OSError, KeyError, RuntimeError, NotImplementedError, zipfile.BadZipFile):
                            pass
                        result = run_7z(["e", "-so", archive, internal], timeout=15)
                        if result is None or result.returncode != 0 or not result.stdout:
                            raise OSError("Failed to read archive member")
                        return cast(bytes, result.stdout)

                    return _raw_thumb(_container_stamp(archive), internal, _read_archive_member)
                result = run_7z(["e", "-so", archive, internal], timeout=15)
                if result is not None and result.returncode == 0 and result.stdout:
                    transformed, transformed_mime = _transform_for_preview(cast(bytes, result.stdout), "image/jpeg")
                    return _make_thumb(transformed, mime=transformed_mime)
            except Exception:
                pass

    return fail("Not found", code=ec.FILE_NOT_FOUND, status=404)
