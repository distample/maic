from __future__ import annotations

"""Batch processing: detection and cleaning."""

import os
import shutil
import threading
from collections.abc import Callable
from typing import Any, cast

from .config import YOLO_DIR, logger, state, state_lock
from .log_context import log_event
from .models import (
    _ensure_imports,
    clean_image,
    create_mask_image,
    extract_detections,
    load_lama,
    load_yolo,
)
from .sevenzip import run_7z
from .state_types import BatchState

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}

batch_state: BatchState = {
    "running": False,
    "stop_requested": False,
    "phase": "",
    "current": 0,
    "total": 0,
    "currentFile": "",
    "log": [],
    "detections": {},
    "user_masks": {},
    "user_edits": set(),
    "corrections_dir": "",
    "corrections_count": 0,
}
batch_lock = threading.RLock()
USER_MASKS_MAX_ITEMS = 256
USER_MASKS_MAX_BYTES = 64 * 1024 * 1024
_archive_map_getter: Callable[[], dict[str, Any]] | None = None
_list_images_in_tmp_fn: Callable[[str], list[str]] | None = None


def _user_masks_locked() -> dict[str, bytes]:
    return cast(dict[str, bytes], batch_state["user_masks"])


def _detections_locked() -> dict[str, dict[str, Any]]:
    return cast(dict[str, dict[str, Any]], batch_state["detections"])


def configure_archive_runtime(
    archive_map_getter: Callable[[], dict[str, Any]],
    list_images_in_tmp_fn: Callable[[str], list[str]],
) -> None:
    """Inject archive runtime dependencies to avoid importing app globals."""
    global _archive_map_getter, _list_images_in_tmp_fn
    _archive_map_getter = archive_map_getter
    _list_images_in_tmp_fn = list_images_in_tmp_fn


def request_batch_stop() -> bool:
    """Request cooperative stop for active batch worker."""
    with batch_lock:
        if not batch_state["running"]:
            return False
        batch_state["stop_requested"] = True
        return True


def _total_user_masks_bytes_locked() -> int:
    return sum(len(v) for v in _user_masks_locked().values())


def _evict_user_masks_locked(*, keep_path: str | None = None) -> int:
    evicted = 0
    while (
        len(_user_masks_locked()) > USER_MASKS_MAX_ITEMS
        or _total_user_masks_bytes_locked() > USER_MASKS_MAX_BYTES
    ):
        keys = list(_user_masks_locked().keys())
        if not keys:
            break
        victim = None
        for key in keys:
            if keep_path is None or key != keep_path:
                victim = key
                break
        if victim is None:
            break
        _user_masks_locked().pop(victim, None)
        evicted += 1
    return evicted


def set_user_mask(path: str, mask_bytes: bytes) -> int:
    """Store user mask bytes and evict oldest entries if limits are exceeded."""
    with batch_lock:
        _user_masks_locked()[path] = mask_bytes
        return _evict_user_masks_locked(keep_path=path)


def remove_detection_and_mask(path: str) -> None:
    """Remove both auto-detection and user mask for a file."""
    with batch_lock:
        _detections_locked().pop(path, None)
        _user_masks_locked().pop(path, None)


def _get_archive_map() -> dict[str, Any]:
    if _archive_map_getter is None:
        return {}
    try:
        return _archive_map_getter()
    except Exception:
        return {}


def _count_images_in_tmp(tmp_dir: str) -> int:
    if _list_images_in_tmp_fn is None:
        return 0
    try:
        return len(_list_images_in_tmp_fn(tmp_dir))
    except Exception:
        return 0


def batch_log(msg, *, phase: str | None = None, level: str = "info", **fields):
    with batch_lock:
        batch_state["log"].append(msg)
        runtime_phase = str(batch_state.get("phase", "") or "")
    log_event(
        logger,
        msg,
        component="batch",
        phase=phase or (runtime_phase or None),
        level=level,
        **fields,
    )


def run_batch_detect(files, conf=0.3):
    if not files:
        return False, "No files provided"
    with state_lock:
        model = state["yolo_model"]
    if model is None:
        ok, msg = load_yolo()
        if not ok:
            return False, msg
        with state_lock:
            model = state["yolo_model"]
    with batch_lock:
        if batch_state["running"]:
            return False, "Batch operation is already running"
        batch_state["running"] = True
        batch_state["stop_requested"] = False
        batch_state["phase"] = "detect"
        batch_state["total"] = len(files)
        batch_state["current"] = 0
        batch_state["log"] = []
        batch_state["detections"] = {}
        batch_state["user_masks"] = {}
        batch_state["user_edits"] = set()

    def detect_thread():
        _ensure_imports()
        from .models import cv2

        batch_log(
            f"Detection: {len(files)} files, confidence {conf}",
            phase="detect",
            total=len(files),
            confidence=conf,
        )

        cancelled = False
        for i, file_info in enumerate(files):
            fpath = file_info["path"]
            fname = file_info.get("name", os.path.basename(fpath))
            with batch_lock:
                if batch_state["stop_requested"]:
                    cancelled = True
                    break
                batch_state["current"] = i + 1
                batch_state["currentFile"] = fname
            try:
                img = cv2.imread(fpath)
                if img is None:
                    batch_log(
                        f"  [WARN] Failed to read: {fname}",
                        phase="detect",
                        source=fname,
                        index=i + 1,
                        total=len(files),
                        level="warning",
                    )
                    continue
                # Prefer a stable model reference; fallback keeps backward compatibility
                # for mocked load paths where global state is not populated.
                thread_model = model
                if thread_model is None:
                    with state_lock:
                        thread_model = state["yolo_model"]
                results = thread_model.predict(img, conf=conf, verbose=False)
                boxes, masks = extract_detections(results)
                if boxes:
                    with batch_lock:
                        batch_state["detections"][fpath] = {"boxes": boxes, "masks": masks}
                    batch_log(
                        f"  [OK] {fname}: {len(boxes)} artifacts",
                        phase="detect",
                        source=fname,
                        index=i + 1,
                        total=len(files),
                    )
            except Exception as exc:
                batch_log(
                    f"  [ERR] {fname}: {exc}",
                    phase="detect",
                    source=fname,
                    index=i + 1,
                    total=len(files),
                    level="error",
                )

        if cancelled:
            batch_log("Detection cancelled", phase="cancelled_detect", level="warning")
            with batch_lock:
                batch_state["phase"] = "cancelled_detect"
                batch_state["running"] = False
            return

        with batch_lock:
            detections_snapshot = dict(batch_state["detections"])
        found_total = sum(len(item.get("boxes", [])) for item in detections_snapshot.values())
        batch_log("")
        batch_log(
            f"Done: {found_total} artifacts in {len(detections_snapshot)} files",
            phase="done_detect",
            detections=len(detections_snapshot),
            artifacts=found_total,
        )
        with batch_lock:
            batch_state["phase"] = "done_detect"
            batch_state["running"] = False

    threading.Thread(target=detect_thread, daemon=True).start()
    return True, "OK"


def _scan_root_images(root_dir: str) -> list[dict[str, str]]:
    if not root_dir or not os.path.isdir(root_dir):
        return []
    files = []
    for dirpath, dirs, filenames in os.walk(root_dir):
        dirs.sort()
        for filename in sorted(filenames):
            if os.path.splitext(filename)[1].lower() not in IMG_EXTS:
                continue
            path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(path, root_dir).replace("\\", "/")
            files.append(
                {
                    "path": path,
                    "name": filename,
                    "relPath": rel_path,
                    "folder": os.path.dirname(rel_path).replace("\\", "/"),
                }
            )
    return files


def _infer_root_from_paths(paths) -> str:
    parent_dirs = [os.path.dirname(path) for path in paths if path]
    if not parent_dirs:
        return ""
    try:
        common = os.path.commonpath(parent_dirs)
    except ValueError:
        return ""
    if not common or common == os.path.splitdrive(common)[0] + os.sep:
        return ""
    return common


def _normalize_clean_files(all_files, root_dir: str, fallback_paths=None) -> list[dict[str, str]]:
    normalized = []
    for item in all_files or []:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        if not path:
            continue
        name = str(item.get("name") or os.path.basename(path))
        rel_path = str(item.get("relPath") or "")
        if not rel_path and root_dir:
            try:
                rel_path = os.path.relpath(path, root_dir).replace("\\", "/")
            except ValueError:
                rel_path = ""
        folder = str(item.get("folder") or os.path.dirname(rel_path).replace("\\", "/"))
        normalized.append({"path": path, "name": name, "relPath": rel_path, "folder": folder})
    if normalized:
        return normalized
    scan_root = root_dir if root_dir and os.path.isdir(root_dir) else _infer_root_from_paths(fallback_paths or [])
    return _scan_root_images(scan_root)


def _count_output_images(output_dir: str) -> int:
    if not output_dir or not os.path.isdir(output_dir):
        return 0
    return sum(
        1
        for dirpath, _, filenames in os.walk(output_dir)
        for filename in filenames
        if os.path.splitext(filename)[1].lower() in IMG_EXTS
    )


def run_batch_clean(method, pad, output_dir, root_dir, has_subfolders, all_files):
    if not output_dir:
        return False, "Output directory is required"
    incoming_count = len(all_files) if isinstance(all_files, list) else 0
    with batch_lock:
        if batch_state["running"]:
            return False, "Batch operation is already running"
        detections = dict(batch_state["detections"])
        all_files = _normalize_clean_files(all_files, root_dir, detections.keys())
        batch_state["running"] = True
        batch_state["stop_requested"] = False
        batch_state["phase"] = "clean"
        batch_state["total"] = len(all_files) if all_files else len(batch_state["detections"])
        batch_state["current"] = 0
        batch_state["log"] = []

    def _get_dest_dir(fpath):
        fdir = os.path.dirname(fpath)
        if has_subfolders and root_dir:
            sub = os.path.basename(fdir)
            if os.path.normpath(fdir) == os.path.normpath(root_dir):
                return output_dir
            return os.path.join(output_dir, sub)
        return output_dir

    def _get_regular_out_path(fpath, fname, rel_path):
        safe_rel = str(rel_path or "").replace("\\", "/").lstrip("/")
        if safe_rel and not os.path.splitdrive(safe_rel)[0] and ".." not in safe_rel.split("/"):
            return os.path.join(output_dir, *safe_rel.split("/"))
        return os.path.join(_get_dest_dir(fpath), fname)

    def _arch_info_for(fpath):
        arch_map = _get_archive_map()
        for tmp_dir, info in arch_map.items():
            if fpath.startswith(tmp_dir + os.sep) or fpath.startswith(tmp_dir + "/"):
                return tmp_dir, info
        return None, None

    def _repack_archive(arch_tmp_dir, arch_info, arch_cleaned_tmp):
        del arch_tmp_dir  # kept for signature compatibility
        arch_path = arch_info["archive_path"]
        arch_name = os.path.splitext(os.path.basename(arch_path))[0]
        arch_ext = os.path.splitext(arch_path)[1]
        out_ext = ".cbz" if arch_ext.lower() in {".rar", ".cbr"} else arch_ext
        out_arch = os.path.join(output_dir, arch_name + out_ext)

        args = ["a", "-y"]
        if out_ext.lower() in {".zip", ".cbz"}:
            args.append("-tzip")
        result = run_7z([*args, out_arch, os.path.join(arch_cleaned_tmp, ".")], timeout=300)
        if not result or result.returncode != 0:
            batch_log(f"  [ERR] Failed to pack: {arch_name + out_ext}", phase="clean", level="error")
            return
        shutil.rmtree(arch_cleaned_tmp, ignore_errors=True)
        batch_log(f"  [PACKED] {arch_name + out_ext}")

    def clean_thread():
        _ensure_imports()
        from .models import cv2, np

        lama_loaded = load_lama() if method == "lama" else False
        if method == "lama" and not lama_loaded:
            batch_log("[INFO] LaMa unavailable, falling back to inpaint", phase="clean", level="warning")
        file_list = (
            [
                (
                    f["path"],
                    f.get("name", os.path.basename(f["path"])),
                    f.get("relPath", ""),
                )
                for f in all_files
            ]
            if all_files
            else [(fp, os.path.basename(fp), "") for fp in detections.keys()]
        )
        batch_log(
            f"Cleaning: {len(file_list)} files | Method: {method}",
            phase="clean",
            total=len(file_list),
            method=method,
        )
        batch_log(
            f"[INFO] Clean input: received={incoming_count}, resolved={len(file_list)}, "
            f"detections={len(detections)}, root={root_dir or '<auto>'}",
            phase="clean",
            level="info",
        )

        processed = 0
        copied = 0

        arch_progress = {}
        for f in all_files or []:
            tmp_dir, info = _arch_info_for(f["path"] if isinstance(f, dict) else f)
            if tmp_dir and tmp_dir not in arch_progress:
                arch_name = os.path.splitext(os.path.basename(info["archive_path"]))[0]
                arch_cleaned_tmp = os.path.join(output_dir, "__arch_tmp__", arch_name)
                arch_progress[tmp_dir] = {
                    "info": info,
                    "cleaned_tmp": arch_cleaned_tmp,
                    "total": _count_images_in_tmp(tmp_dir),
                    "done": 0,
                }

        cancelled = False
        for i, (fpath, fname, rel_path) in enumerate(file_list):
            with batch_lock:
                if batch_state["stop_requested"]:
                    cancelled = True
                    break
                batch_state["current"] = i + 1
                batch_state["currentFile"] = fname
            det = detections.get(fpath)

            tmp_dir, arch_info = _arch_info_for(fpath)
            if arch_info:
                ap = arch_progress[tmp_dir]
                rel_in_arch = os.path.relpath(fpath, tmp_dir)
                out_path = os.path.join(ap["cleaned_tmp"], rel_in_arch)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
            else:
                out_path = _get_regular_out_path(fpath, fname, rel_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)

            if det:
                try:
                    img = cv2.imread(fpath)
                    if img is None:
                        batch_log(
                            f"  [WARN] Failed to read: {fname}",
                            phase="clean",
                            source=fname,
                            index=i + 1,
                            total=len(file_list),
                            level="warning",
                        )
                        continue
                    h_img, w_img = img.shape[:2]
                    with batch_lock:
                        user_mask_bytes = batch_state["user_masks"].get(fpath)
                    if user_mask_bytes:
                        mask_raw = cv2.imdecode(
                            np.frombuffer(user_mask_bytes, np.uint8), cv2.IMREAD_UNCHANGED
                        )
                        if mask_raw is None:
                            mask = create_mask_image(h_img, w_img, det, pad)
                        else:
                            gray = mask_raw[:, :, 2] if len(mask_raw.shape) == 3 else mask_raw
                            if gray.shape[:2] != (h_img, w_img):
                                gray = cv2.resize(gray, (w_img, h_img))
                            _, mask = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
                    else:
                        mask = create_mask_image(h_img, w_img, det, pad)
                    result = clean_image(
                        img,
                        mask,
                        method if (method != "lama" or lama_loaded) else "inpaint",
                    )
                    cv2.imwrite(out_path, result)
                    processed += 1
                except Exception as exc:
                    batch_log(
                        f"  [ERR] {fname}: {exc}",
                        phase="clean",
                        source=fname,
                        index=i + 1,
                        total=len(file_list),
                        level="error",
                    )
            else:
                try:
                    shutil.copy2(fpath, out_path)
                    copied += 1
                except Exception as exc:
                    batch_log(
                        f"  [ERR] {fname}: {exc}",
                        phase="clean",
                        source=fname,
                        index=i + 1,
                        total=len(file_list),
                        level="error",
                    )

            if arch_info:
                ap["done"] += 1
                if ap["done"] >= ap["total"]:
                    os.makedirs(output_dir, exist_ok=True)
                    _repack_archive(tmp_dir, ap["info"], ap["cleaned_tmp"])

        if cancelled:
            batch_log("Cleaning cancelled", phase="cancelled_clean", level="warning")
            _save_corrections()
            with batch_lock:
                batch_state["phase"] = "cancelled_clean"
                batch_state["running"] = False
            return

        batch_log("")
        output_count = _count_output_images(output_dir)
        if output_count < len(file_list):
            batch_log(
                f"  [WARN] Output has {output_count}/{len(file_list)} image files",
                phase="done_clean",
                level="warning",
            )
        batch_log(
            f"[OK] Cleaned: {processed}, copied: {copied}",
            phase="done_clean",
            processed=processed,
            copied=copied,
        )
        _save_corrections()
        with batch_lock:
            batch_state["phase"] = "done_clean"
            batch_state["running"] = False

    threading.Thread(target=clean_thread, daemon=True).start()
    return True, "OK"


def _save_corrections():
    _ensure_imports()
    from .models import cv2, np

    with batch_lock:
        user_edits = set(batch_state["user_edits"])
    if not user_edits:
        return

    corrections_dir = os.path.join(YOLO_DIR, "corrections")
    orig_dir_c = os.path.join(corrections_dir, "original")
    mask_dir_c = os.path.join(corrections_dir, "masks")
    os.makedirs(orig_dir_c, exist_ok=True)
    os.makedirs(mask_dir_c, exist_ok=True)

    saved = 0
    for edited_path in user_edits:
        fname = os.path.basename(edited_path)
        stem = os.path.splitext(fname)[0]
        try:
            if os.path.isfile(edited_path):
                shutil.copy2(edited_path, os.path.join(orig_dir_c, fname))
            with batch_lock:
                user_mask_bytes = batch_state["user_masks"].get(edited_path)
            if user_mask_bytes:
                mask_raw = cv2.imdecode(np.frombuffer(user_mask_bytes, np.uint8), cv2.IMREAD_UNCHANGED)
                if mask_raw is not None:
                    if len(mask_raw.shape) == 3 and mask_raw.shape[2] >= 3:
                        gray = mask_raw[:, :, 2]
                    elif len(mask_raw.shape) == 3:
                        gray = mask_raw[:, :, 0]
                    else:
                        gray = mask_raw
                    _, mask_bin = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
                    cv2.imwrite(os.path.join(mask_dir_c, stem + ".png"), mask_bin)
            saved += 1
        except Exception as exc:
            batch_log(f"  [WARN] {fname}: {exc}")

    if saved > 0:
        with batch_lock:
            batch_state["corrections_dir"] = corrections_dir
            batch_state["corrections_count"] = saved
        batch_log(f"[INFO] Saved corrections: {saved} -> {corrections_dir}")
