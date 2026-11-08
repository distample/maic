"""Routes for cleaning operations, file browsing, and folder scan workflows."""

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import OrderedDict
from contextlib import nullcontext
from typing import Any, cast

from flask import Blueprint, jsonify, request, send_file

from . import error_codes as EC
from .api_errors import fail
from .config import logger, persist_runtime_settings, state, state_lock
from .dto import BrowseSourcePayload, ScanFolderPayload
from .models import clean_image
from .path_access import add_allowed_root, is_under_allowed_root
from .payload_validation import validate_browse_source_payload, validate_scan_folder_payload
from .sevenzip import find_7z, run_7z
from .validation import as_bool, json_body, require_path_exists


def _nat_parts(value: str):
    return [
        (0, int(chunk), "") if chunk.isdigit() else (1, 0, chunk.lower())
        for chunk in re.split(r"(\d+)", value)
        if chunk
    ]


def _ask_sibling_folders(root, filedialog, tk):
    """Select one folder, then allow Ctrl/Shift selection among its siblings."""
    initial = filedialog.askdirectory(parent=root, title="Select a source folder")
    if not initial:
        return []

    initial = os.path.abspath(initial)
    parent = os.path.dirname(initial)
    try:
        siblings = sorted(
            (entry.path for entry in os.scandir(parent) if entry.is_dir()),
            key=lambda path: _nat_parts(os.path.basename(path)),
        )
    except OSError:
        return [initial]
    if len(siblings) < 2:
        return [initial]

    selected: list[str] = []
    dialog = tk.Toplevel(root)
    dialog.title("Select source folders")
    dialog.attributes("-topmost", True)
    dialog.resizable(True, True)
    dialog.minsize(520, 320)

    tk.Label(
        dialog,
        text="Select sibling folders with Ctrl or Shift. Each folder becomes a separate source.",
        anchor="w",
        justify="left",
        wraplength=620,
    ).pack(fill="x", padx=14, pady=(14, 4))
    tk.Label(dialog, text=parent, anchor="w", fg="#666666").pack(
        fill="x", padx=14, pady=(0, 8)
    )

    list_frame = tk.Frame(dialog)
    list_frame.pack(fill="both", expand=True, padx=14)
    scrollbar = tk.Scrollbar(list_frame, orient="vertical")
    folder_list = tk.Listbox(
        list_frame,
        selectmode=tk.EXTENDED,
        exportselection=False,
        yscrollcommand=scrollbar.set,
        width=68,
        height=min(max(len(siblings), 8), 18),
    )
    scrollbar.config(command=folder_list.yview)
    folder_list.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    initial_key = os.path.normcase(os.path.normpath(initial))
    for index, path in enumerate(siblings):
        folder_list.insert(tk.END, os.path.basename(path))
        if os.path.normcase(os.path.normpath(path)) == initial_key:
            folder_list.selection_set(index)
            folder_list.see(index)

    def accept(_event=None):
        selected.extend(siblings[index] for index in folder_list.curselection())
        dialog.destroy()

    def cancel(_event=None):
        dialog.destroy()

    buttons = tk.Frame(dialog)
    buttons.pack(fill="x", padx=14, pady=14)
    tk.Button(buttons, text="Cancel", command=cancel).pack(side="right")
    tk.Button(buttons, text="Add selected", command=accept, default=tk.ACTIVE).pack(
        side="right", padx=(0, 8)
    )
    dialog.bind("<Return>", accept)
    dialog.bind("<Escape>", cancel)
    dialog.protocol("WM_DELETE_WINDOW", cancel)
    folder_list.focus_set()
    dialog.grab_set()
    root.wait_window(dialog)
    return selected


def _extract_archive_to_tmp(archive_path: str, *, prefix: str, register_tmp_dir):
    seven_zip = find_7z()
    if not seven_zip:
        return None, fail("7z not found", code=EC.SEVEN_ZIP_NOT_FOUND)
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    register_tmp_dir(temp_dir)
    try:
        result = run_7z(["x", "-o" + temp_dir, "-y", archive_path], timeout=120)
        if result is None or result.returncode != 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None, fail("Archive extraction failed", code=EC.ARCHIVE_EXTRACT_FAILED)
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, fail(f"Archive extraction failed: {exc}", code=EC.ARCHIVE_EXTRACT_FAILED)
    return temp_dir, None


def _collect_scan_files(
    actual_dir: str,
    *,
    img_exts,
    arch_exts,
    arch_map,
    map_lock,
    register_tmp_dir,
    prune_tmp_dirs,
):
    all_files = []
    for root, dirs, file_names in os.walk(actual_dir):
        dirs.sort()
        for file_name in sorted(file_names):
            ext = os.path.splitext(file_name)[1].lower()
            file_path = os.path.join(root, file_name)
            if ext in img_exts:
                rel = os.path.relpath(file_path, actual_dir).replace("\\", "/")
                folder = os.path.dirname(rel) or ""
                all_files.append(
                    {"name": file_name, "path": file_path, "relPath": rel, "folder": folder}
                )
                continue
            if ext not in arch_exts:
                continue
            seven_zip = find_7z()
            if not seven_zip:
                continue
            archive_tmp = tempfile.mkdtemp(prefix="maic_arch_")
            register_tmp_dir(archive_tmp)
            try:
                result = run_7z(["x", "-o" + archive_tmp, "-y", file_path], timeout=120)
                if result is None or result.returncode != 0:
                    shutil.rmtree(archive_tmp, ignore_errors=True)
                    continue
            except Exception:
                shutil.rmtree(archive_tmp, ignore_errors=True)
                continue
            with map_lock:
                arch_map[archive_tmp] = {
                    "archive_path": file_path,
                    "fmt": ext.lstrip("."),
                    "source_dir": actual_dir,
                    "created_at": time.time(),
                }
            add_allowed_root(cast(dict[Any, Any], state), archive_tmp)
            prune_tmp_dirs()

            archive_name = os.path.splitext(file_name)[0]
            rel_root = os.path.relpath(root, actual_dir).replace("\\", "/")
            folder_prefix = (
                rel_root.rstrip("/") + "/" + archive_name if rel_root != "." else archive_name
            )
            for archive_root, archive_dirs, archive_files in os.walk(archive_tmp):
                archive_dirs.sort()
                for archive_file_name in sorted(archive_files):
                    if os.path.splitext(archive_file_name)[1].lower() not in img_exts:
                        continue
                    archive_file_path = os.path.join(archive_root, archive_file_name)
                    inner_rel = os.path.relpath(archive_file_path, archive_tmp).replace("\\", "/")
                    inner_dir = os.path.dirname(inner_rel)
                    folder = (
                        (folder_prefix + "/" + inner_dir).rstrip("/")
                        if inner_dir
                        else folder_prefix
                    )
                    all_files.append(
                        {
                            "name": archive_file_name,
                            "path": archive_file_path,
                            "relPath": folder_prefix + "/" + inner_rel,
                            "folder": folder,
                            "archiveTmp": archive_tmp,
                        }
                    )
    return all_files


def _build_scan_groups_payload(rd: str, actual_dir: str, source_name: str, files):
    files.sort(key=lambda item: (_nat_parts(item["folder"]), _nat_parts(item["name"])))
    groups = []
    group_map: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for item in files:
        folder = item["folder"]
        if folder not in group_map:
            group_map[folder] = []
        group_map[folder].append(item)

    for folder, folder_files in group_map.items():
        folder_name = folder if folder else source_name
        groups.append(
            {
                "folder": os.path.join(actual_dir, folder) if folder else actual_dir,
                "folderName": folder_name,
                "files": folder_files,
                "isRoot": not folder,
            }
        )
    total_files = len(files)
    has_subfolders = any(not group["isRoot"] for group in groups)
    if os.path.isdir(rd):
        default_output = os.path.join(os.path.dirname(rd), source_name + "_cleaned")
    else:
        default_output = os.path.join(
            os.path.dirname(rd), os.path.splitext(source_name)[0] + "_cleaned"
        )
    return {
        "ok": True,
        "groups": groups,
        "totalFiles": total_files,
        "hasSubfolders": has_subfolders,
        "defaultOutput": default_output,
    }

def _resolve_requested_output_dir(src: str, root_dir: str, output_dir_raw: str):
    output_dir = ""
    output_dir_value = (output_dir_raw or "").strip()
    if not output_dir_value:
        return output_dir, None
    output_dir = os.path.realpath(output_dir_value)
    allowed_write_roots = list(state.get("allowed_write_roots", []))
    allowed_write_roots.append(os.path.dirname(os.path.realpath(src)))
    if root_dir:
        allowed_write_roots.append(os.path.realpath(root_dir))
    if not is_under_allowed_root(output_dir, allowed_write_roots):
        return "", fail("Access denied", code=EC.INVALID_PATH, status=403)
    with state_lock:
        state["default_clean_output_dir"] = output_dir
    persist_runtime_settings()
    return output_dir, None


def _find_archive_info_for_source(src: str, arch_map, map_lock):
    with map_lock:
        arch_items = list(arch_map.items())
    for tmp_dir, info in arch_items:
        if src.startswith(tmp_dir + os.sep) or src.startswith(tmp_dir + "/"):
            return tmp_dir, info
    return None, None


def _build_archive_clean_paths(src: str, arch_tmp_dir: str, arch_info, output_dir: str):
    rel_in_arch = os.path.relpath(src, arch_tmp_dir)
    arch_path = arch_info["archive_path"]
    arch_name = os.path.splitext(os.path.basename(arch_path))[0]
    arch_ext = os.path.splitext(arch_path)[1]
    if output_dir:
        cleaned_dir = output_dir
    else:
        cleaned_dir = os.path.join(
            os.path.dirname(arch_path),
            os.path.splitext(os.path.basename(arch_info["source_dir"]))[0] + "_cleaned",
        )
    arch_cleaned_tmp = os.path.join(cleaned_dir, "__arch_tmp__", arch_name)
    out_file = os.path.join(arch_cleaned_tmp, rel_in_arch)
    out_ext = ".cbz" if arch_ext.lower() in {".rar", ".cbr"} else arch_ext
    out_archive = os.path.join(cleaned_dir, arch_name + out_ext)
    return cleaned_dir, arch_cleaned_tmp, out_file, out_archive


def _maybe_repack_cleaned_archive(
    arch_tmp_dir: str,
    arch_cleaned_tmp: str,
    cleaned_dir: str,
    out_archive: str,
    *,
    list_images,
):
    orig_files = [entry for entry in list_images(arch_tmp_dir)]
    done_files = [entry for entry in list_images(arch_cleaned_tmp)]
    if len(done_files) < len(orig_files) or not orig_files:
        return False
    os.makedirs(cleaned_dir, exist_ok=True)
    args = ["a", "-y"]
    if os.path.splitext(out_archive)[1].lower() in {".zip", ".cbz"}:
        args.append("-tzip")
    result = run_7z([*args, out_archive, os.path.join(arch_cleaned_tmp, "*")], timeout=300)
    if not result or result.returncode != 0:
        return False
    shutil.rmtree(arch_cleaned_tmp, ignore_errors=True)
    return True


def _ensure_archive_clean_overlay(arch_tmp_dir: str, arch_cleaned_tmp: str, *, list_images) -> None:
    if os.path.isdir(arch_cleaned_tmp) and list_images(arch_cleaned_tmp):
        return
    for src in list_images(arch_tmp_dir):
        rel = os.path.relpath(src, arch_tmp_dir)
        dst = os.path.join(arch_cleaned_tmp, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def _repack_archive_overlay(arch_cleaned_tmp: str, cleaned_dir: str, out_archive: str) -> bool:
    if not os.path.isdir(arch_cleaned_tmp):
        return False
    os.makedirs(cleaned_dir, exist_ok=True)
    args = ["a", "-y"]
    if os.path.splitext(out_archive)[1].lower() in {".zip", ".cbz"}:
        args.append("-tzip")
    result = run_7z([*args, out_archive, os.path.join(arch_cleaned_tmp, "*")], timeout=300)
    return bool(result and result.returncode == 0)


def _resolve_regular_clean_destination(
    *,
    src_dir: str,
    root_dir: str,
    output_dir: str,
    has_subfolders: bool,
):
    if output_dir:
        if has_subfolders and root_dir:
            subdir_name = os.path.basename(src_dir)
            if os.path.normpath(src_dir) == os.path.normpath(root_dir):
                return output_dir
            return os.path.join(output_dir, subdir_name)
        return output_dir
    return os.path.join(os.path.dirname(src_dir), os.path.basename(src_dir) + "_cleaned")


def create_cleaning_blueprint(
    arch_map,
    list_images_in_tmp,
    img_exts,
    arch_exts,
    *,
    arch_map_lock=None,
    register_tmp_dir=None,
    prune_tmp_dirs=None,
) -> Blueprint:
    """Create cleaning blueprint with injected archive runtime dependencies."""

    bp = Blueprint("cleaning", __name__)
    _map_lock = arch_map_lock if arch_map_lock is not None else nullcontext()

    if register_tmp_dir is None:
        register_tmp_dir = lambda _path: None
    if prune_tmp_dirs is None:
        prune_tmp_dirs = lambda: None

    @bp.route("/api/clean", methods=["POST"])
    def api_clean():
        """Clean a single uploaded image using a user-provided mask."""
        from .models import cv2, np

        uploaded = request.files.get("file")
        mask_file = request.files.get("mask")
        method = request.form.get("method", "white")
        if not uploaded or not mask_file:
            return fail("Both file and mask are required", code=EC.MISSING_FILE_OR_MASK, status=400)

        img = cv2.imdecode(np.frombuffer(uploaded.read(), np.uint8), cv2.IMREAD_COLOR)
        mask_raw = cv2.imdecode(np.frombuffer(mask_file.read(), np.uint8), cv2.IMREAD_GRAYSCALE)
        if mask_raw.shape[:2] != img.shape[:2]:
            mask_raw = cv2.resize(mask_raw, (img.shape[1], img.shape[0]))
        _, binary_mask = cv2.threshold(mask_raw, 127, 255, cv2.THRESH_BINARY)
        result = clean_image(img, binary_mask, method)
        _, buf = cv2.imencode(".png", result)
        return send_file(io.BytesIO(buf.tobytes()), mimetype="image/png")

    @bp.route("/api/clean-path", methods=["POST"])
    def api_clean_path():
        """Clean an image loaded from filesystem path with an uploaded mask."""
        from .models import cv2, np

        mask_file = request.files.get("mask")
        method = request.form.get("method", "white")
        src = request.form.get("path", "")
        if not src or not os.path.isfile(src):
            return fail("File not found", code=EC.FILE_NOT_FOUND, status=400)
        root_dir = request.form.get("root_dir", "")
        output_dir, output_dir_error = _resolve_requested_output_dir(
            src, root_dir, request.form.get("output_dir", "")
        )
        if output_dir_error is not None:
            return output_dir_error

        img = cv2.imread(src)
        if img is None:
            return fail("Failed to read image", code=EC.IMAGE_READ_FAILED, status=400)
        if not mask_file:
            return fail("Mask file is required", code=EC.MISSING_MASK, status=400)

        mask_raw = cv2.imdecode(np.frombuffer(mask_file.read(), np.uint8), cv2.IMREAD_GRAYSCALE)
        if mask_raw.shape[:2] != img.shape[:2]:
            mask_raw = cv2.resize(mask_raw, (img.shape[1], img.shape[0]))

        _, binary_mask = cv2.threshold(mask_raw, 127, 255, cv2.THRESH_BINARY)
        result = clean_image(img, binary_mask, method)
        has_subfolders = as_bool(request.form.get("has_subfolders", "false"), False)
        fdir = os.path.dirname(src)
        fname = os.path.basename(src)

        # If source file comes from extracted archive temp tree, write into archive temp output.
        arch_tmp_dir, arch_info = _find_archive_info_for_source(src, arch_map, _map_lock)

        if arch_info:
            cleaned_dir, arch_cleaned_tmp, out_file, out_archive = _build_archive_clean_paths(
                src, arch_tmp_dir, arch_info, output_dir
            )
            _ensure_archive_clean_overlay(
                arch_tmp_dir,
                arch_cleaned_tmp,
                list_images=list_images_in_tmp,
            )
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            cv2.imwrite(out_file, result)
            _repack_archive_overlay(arch_cleaned_tmp, cleaned_dir, out_archive)
        else:
            dest = _resolve_regular_clean_destination(
                src_dir=fdir,
                root_dir=root_dir,
                output_dir=output_dir,
                has_subfolders=has_subfolders,
            )
            os.makedirs(dest, exist_ok=True)
            out = os.path.join(dest, fname)
            cv2.imwrite(out, result)

        _, buf = cv2.imencode(".png", result)
        return send_file(io.BytesIO(buf.tobytes()), mimetype="image/png")

    @bp.route("/api/browse-folder", methods=["POST"])
    def api_browse_folder():
        """Open native folder chooser and return selected path."""
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(parent=root)
            root.destroy()
            if folder:
                add_allowed_root(state, folder, root_key="allowed_read_roots")
                add_allowed_root(state, folder, root_key="allowed_write_roots")
            return jsonify({"path": folder if folder else ""})
        except Exception as exc:
            return fail(str(exc), code=EC.BROWSE_FOLDER_FAILED, path="")

    @bp.route("/api/browse-file", methods=["POST"])
    def api_browse_file():
        """Open native file chooser and return selected path."""
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            data = json_body()
            filetypes_payload = data.get("filetypes", [("YOLO Model", "*.pt")])
            fp = filedialog.askopenfilename(
                parent=root,
                filetypes=[tuple(filetype_entry) for filetype_entry in filetypes_payload],
            )
            root.destroy()
            return jsonify({"path": fp if fp else ""})
        except Exception as exc:
            return fail(str(exc), code=EC.BROWSE_FILE_FAILED, path="")

    @bp.route("/api/browse-source", methods=["POST"])
    def api_browse_source():
        """Open native chooser for folder or archive source selection."""
        data = json_body()
        valid, message = validate_browse_source_payload(data)
        if not valid:
            return fail(message, code=EC.INVALID_PAYLOAD)
        payload = cast(BrowseSourcePayload, data)
        source_type = payload.get("type", "folder")
        exts = payload.get("extensions", "*.zip *.cbz *.cbr *.cb7 *.rar *.7z *.pdf")
        multiple = payload.get("multiple", False) and source_type == "folder"

        if sys.platform == "win32" and multiple:
            try:
                from .windows_folder_picker import select_folders

                paths = select_folders("Выберите папки-источники")
                return jsonify({
                    "path": paths[0] if paths else "",
                    "paths": paths,
                    "type": "folder",
                })
            except Exception as exc:
                # Keep the Tk sibling-list picker as a compatibility fallback.
                logger.warning("Native multi-folder picker unavailable: %s", exc)
                pass

        if sys.platform.startswith("linux"):
            if source_type == "folder":
                if shutil.which("zenity"):
                    try:
                        command = [
                            "zenity", "--file-selection", "--directory", "--title=Select Folder"
                        ]
                        if multiple:
                            command.extend(["--multiple", "--separator=\n"])
                        r = subprocess.run(
                            command,
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )
                        paths = [path for path in r.stdout.splitlines() if path]
                        if paths:
                            response: dict[str, Any] = {"path": paths[0], "type": "folder"}
                            if multiple:
                                response["paths"] = paths
                            return jsonify(response)
                        response = {"path": ""}
                        if multiple:
                            response["paths"] = []
                        return jsonify(response)
                    except Exception:
                        pass
                if shutil.which("kdialog") and not multiple:
                    try:
                        r = subprocess.run(
                            ["kdialog", "--getexistingdirectory", ".", "--title", "Select Folder"],
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )
                        path = r.stdout.strip()
                        if path:
                            return jsonify({"path": path, "type": "folder"})
                        return jsonify({"path": ""})
                    except Exception:
                        pass
            else:
                if shutil.which("zenity"):
                    try:
                        filt = " ".join(exts.split())
                        r = subprocess.run(
                            [
                                "zenity",
                                "--file-selection",
                                "--title=Select Source",
                                f"--file-filter=Files | {filt}",
                                "--file-filter=All Files | *",
                            ],
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )
                        path = r.stdout.strip()
                        if path:
                            return jsonify({"path": path, "type": "file"})
                        return jsonify({"path": ""})
                    except Exception:
                        pass
                if shutil.which("kdialog"):
                    try:
                        r = subprocess.run(
                            [
                                "kdialog",
                                "--getopenfilename",
                                ".",
                                f"Files ({exts})",
                                "--title",
                                "Select Source",
                            ],
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )
                        path = r.stdout.strip()
                        if path:
                            return jsonify({"path": path, "type": "file"})
                        return jsonify({"path": ""})
                    except Exception:
                        pass

        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            if source_type == "folder":
                if multiple:
                    paths = _ask_sibling_folders(root, filedialog, tk)
                    root.destroy()
                    return jsonify({
                        "path": paths[0] if paths else "",
                        "paths": paths,
                        "type": source_type,
                    })
                path = filedialog.askdirectory(parent=root, title="Select Folder")
            else:
                filetype_filters = [("Files", exts), ("All Files", "*.*")]
                path = filedialog.askopenfilename(
                    parent=root,
                    title="Select Source",
                    filetypes=filetype_filters,
                )
            root.destroy()
            return jsonify({"path": path or "", "type": source_type})
        except Exception as exc:
            return fail(str(exc), code=EC.BROWSE_SOURCE_FAILED, path="")

    @bp.route("/api/scan-folder", methods=["POST"])
    def api_scan_folder():
        """Scan source and return grouped image entries, including archive content."""
        data = json_body()
        valid, message = validate_scan_folder_payload(data)
        if not valid:
            return fail(message, code=EC.INVALID_PAYLOAD)
        payload = cast(ScanFolderPayload, data)
        rd = (payload.get("path", "") or "").strip()
        valid, err = require_path_exists(rd, code=EC.PATH_NOT_FOUND)
        if not valid:
            return err
        add_allowed_root(state, rd)
        prune_tmp_dirs()
        source_name = os.path.basename(rd)
        actual_dir = rd

        if os.path.isfile(rd):
            ext = os.path.splitext(rd)[1].lower()
            if ext in (".zip", ".cbz", ".cbr", ".cb7", ".rar", ".7z"):
                extracted_dir, error_response = _extract_archive_to_tmp(
                    rd, prefix="maic_clean_", register_tmp_dir=register_tmp_dir
                )
                if error_response is not None:
                    return error_response
                actual_dir = extracted_dir
            else:
                return fail("Unsupported file format", code=EC.UNSUPPORTED_FILE_FORMAT)

        all_files = _collect_scan_files(
            actual_dir,
            img_exts=img_exts,
            arch_exts=arch_exts,
            arch_map=arch_map,
            map_lock=_map_lock,
            register_tmp_dir=register_tmp_dir,
            prune_tmp_dirs=prune_tmp_dirs,
        )
        return jsonify(_build_scan_groups_payload(rd, actual_dir, source_name, all_files))

    return bp
