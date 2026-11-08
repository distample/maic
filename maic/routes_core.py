"""Core HTTP routes for app shell, health, language, and basic model operations."""

import os
from typing import cast

from flask import Blueprint, current_app, jsonify, make_response, request, send_file

from .api_errors import fail
from .config import BASE_DIR, KCC_AVAILABLE, persist_runtime_settings, state, state_lock
from . import error_codes as EC
from .dto import DetectPathPayload, FileMtimesPayload
from .models import extract_detections, load_yolo
from .path_access import is_allowed_image_file
from .payload_validation import validate_detect_path_payload, validate_file_mtimes_payload
from .validation import as_float, json_body
from .version import __version__

core_bp = Blueprint("core", __name__)


@core_bp.route("/")
def index():
    """Serve frontend HTML from static assets."""
    return current_app.send_static_file("index.html")


@core_bp.route("/api/lang/<lang>")
def api_lang(lang):
    """Return language pack by code from `locale/<lang>.json`."""
    lang_dir = os.path.realpath(os.path.join(BASE_DIR, "locale"))
    path = os.path.realpath(os.path.join(lang_dir, f"{lang}.json"))
    try:
        if os.path.commonpath([path, lang_dir]) != lang_dir:
            return fail("Invalid language path", code=EC.INVALID_PATH, status=400)
    except ValueError:
        return fail("Invalid language path", code=EC.INVALID_PATH, status=400)
    if not os.path.isfile(path):
        return fail("Not found", code=EC.FILE_NOT_FOUND, status=404)
    return send_file(path, mimetype="application/json")


@core_bp.route("/api/langs")
def api_langs():
    """Return available language codes discovered in locale directory."""
    lang_dir = os.path.join(BASE_DIR, "locale")
    langs = []
    vol_prefixes = []
    if os.path.isdir(lang_dir):
        for filename in sorted(os.listdir(lang_dir)):
            if filename.endswith(".json"):
                langs.append(filename[:-5])
                try:
                    import json as _json
                    with open(os.path.join(lang_dir, filename), "r", encoding="utf-8-sig") as f:
                        data = _json.load(f)
                    vp = str(data.get("conv.vol_prefix", "") or "").strip()
                    if vp and vp not in vol_prefixes:
                        vol_prefixes.append(vp)
                except Exception:
                    pass
    if not vol_prefixes:
        vol_prefixes = ["Vol."]
    return jsonify({"langs": langs, "vol_prefixes": vol_prefixes})


@core_bp.route("/api/health")
def health():
    """Return process and model health snapshot consumed by frontend polling."""
    with state_lock:
        snapshot = {
            "device": state["device"],
            "gpu_name": state["gpu_name"],
            "cpu_name": state["cpu_name"],
            "cuda_available": state["cuda_available"],
            "model_loaded": state["yolo_model"] is not None,
            "model_path": state["model_path"],
            "lama_available": state["lama_model"] is not None,
        }
    return jsonify(
        {
            "status": "ok",
            "version": __version__,
            "kcc_available": KCC_AVAILABLE,
            # The Conversion tab is usable without KCC: the three
            # native formats build a volume with nothing installed.
            "native_available": True,
            **snapshot,
        }
    )


@core_bp.route("/api/set-device", methods=["POST"])
def api_set_device():
    """Switch inference device and move loaded YOLO model if necessary."""
    data = json_body()
    new = data.get("device", "cpu")
    with state_lock:
        cuda_available = bool(state["cuda_available"])
    if new == "cuda" and not cuda_available:
        return fail("CUDA is unavailable", code=EC.DEVICE_UNAVAILABLE)
    with state_lock:
        old = state["device"]
        model = state["yolo_model"]
        state["device"] = new
    if model is not None:
        try:
            model.to(new)
        except Exception as exc:
            with state_lock:
                state["device"] = old
            return fail(str(exc), code=EC.DEVICE_SWITCH_FAILED)
    persist_runtime_settings()
    with state_lock:
        current_device = state["device"]
    return jsonify({"ok": True, "device": current_device})


@core_bp.route("/api/load-model", methods=["POST"])
def api_load_model():
    """Load YOLO model from provided path or default configured path."""
    data = json_body()
    ok, msg = load_yolo(data.get("path", ""))
    if ok:
        persist_runtime_settings()
    return jsonify({"ok": ok, "message": msg})


@core_bp.route("/api/detect", methods=["POST"])
def api_detect():
    """Run object detection for an uploaded image file."""
    from .models import cv2, np

    if state["yolo_model"] is None:
        ok, msg = load_yolo()
        if not ok:
            return fail(msg, code=EC.MODEL_LOAD_FAILED, boxes=[])

    uploaded = request.files.get("file")
    conf = as_float(request.form.get("confidence", 0.3), 0.3)
    if not uploaded:
        return fail("No file provided", code=EC.MISSING_FILE, boxes=[])

    img = cv2.imdecode(np.frombuffer(uploaded.read(), np.uint8), cv2.IMREAD_COLOR)
    results = state["yolo_model"].predict(img, conf=conf, verbose=False)
    boxes, masks = extract_detections(results)
    return jsonify({"boxes": boxes, "masks": masks, "count": len(boxes)})


@core_bp.route("/api/detect-path", methods=["POST"])
def api_detect_path():
    """Run object detection for an image loaded directly from filesystem path."""
    from .models import cv2

    data = json_body()
    valid, message = validate_detect_path_payload(data)
    if not valid:
        return fail(message, code=EC.INVALID_PAYLOAD, boxes=[])
    payload = cast(DetectPathPayload, data)
    path = payload.get("path", "")
    conf = as_float(payload.get("confidence", 0.3), 0.3)
    if not os.path.isfile(path):
        return fail("File not found", code=EC.FILE_NOT_FOUND, boxes=[])

    if state["yolo_model"] is None:
        ok, msg = load_yolo()
        if not ok:
            return fail(msg, code=EC.MODEL_LOAD_FAILED, boxes=[])

    img = cv2.imread(path)
    if img is None:
        return fail("Failed to read image", code=EC.IMAGE_READ_FAILED, boxes=[])

    results = state["yolo_model"].predict(img, conf=conf, verbose=False)
    boxes, masks = extract_detections(results)
    return jsonify({"boxes": boxes, "masks": masks, "count": len(boxes)})


@core_bp.route("/api/serve-image")
def api_serve_image():
    """Serve image bytes from disk for preview widgets."""
    path = request.args.get("path", "")
    if not path:
        return fail("path must be provided", code=EC.INVALID_PAYLOAD, status=400)
    allowed_roots = state.get("allowed_read_roots", [])
    if not is_allowed_image_file(path, allowed_roots):
        if os.path.isfile(path):
            return fail("Access denied", code=EC.INVALID_PATH, status=403)
        return fail("Not found", code=EC.FILE_NOT_FOUND, status=404)

    ext = os.path.splitext(path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    resp = make_response(send_file(path, mimetype=mime_map.get(ext, "image/png")))
    resp.headers["Cache-Control"] = "private, max-age=5"
    return resp


@core_bp.route("/api/file-mtimes", methods=["POST"])
def api_file_mtimes():
    """Return mtime map for a list of file paths."""
    data = json_body()
    valid, message = validate_file_mtimes_payload(data)
    if not valid:
        return fail(message, code=EC.INVALID_PAYLOAD)
    payload = cast(FileMtimesPayload, data)
    paths = payload.get("paths", [])
    result = {}
    for path in paths:
        try:
            result[path] = os.path.getmtime(path)
        except Exception:
            result[path] = 0
    return jsonify(result)
