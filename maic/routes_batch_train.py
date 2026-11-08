"""Routes for batch processing and model training orchestration."""

import os
from typing import cast

from flask import Blueprint, jsonify, request

from . import error_codes as EC
from .api_errors import fail
from .batch import (
    batch_lock,
    batch_state,
    remove_detection_and_mask,
    request_batch_stop,
    run_batch_clean,
    run_batch_detect,
    set_user_mask,
)
from .config import YOLO_DIR, state, state_lock
from .dto import BatchCleanPayload, BatchDetectPayload
from .payload_validation import validate_batch_clean_payload, validate_batch_detect_payload
from .training import add_log, start_finetune, start_training
from .validation import as_float, as_int, json_body

batch_train_bp = Blueprint("batch_train", __name__)


@batch_train_bp.route("/api/batch/status")
def api_batch_status():
    """Return current batch progress snapshot excluding heavy binary mask payloads."""
    with batch_lock:
        safe = {k: v for k, v in batch_state.items() if k not in ("user_masks", "user_edits")}
        safe["corrections_count"] = batch_state.get("corrections_count", 0)
        safe["corrections_dir"] = batch_state.get("corrections_dir", "")
    return jsonify(safe)


@batch_train_bp.route("/api/batch/remove-detection", methods=["POST"])
def api_batch_remove():
    """Remove auto-detection and user mask for a single path."""
    data = json_body()
    path = data.get("path", "")
    remove_detection_and_mask(path)
    return jsonify({"ok": True})


@batch_train_bp.route("/api/batch/set-mask", methods=["POST"])
def api_batch_set_mask():
    """Store user-provided mask and mark file as manually edited."""
    from .models import _ensure_imports, cv2, np

    _ensure_imports()
    mask_file = request.files.get("mask")
    path = request.form.get("path", "")
    if not mask_file or not path:
        return fail("Mask and path are required", code=EC.MISSING_MASK_OR_PATH)

    mask_bytes = mask_file.read()
    mask_arr = cv2.imdecode(np.frombuffer(mask_bytes, np.uint8), cv2.IMREAD_UNCHANGED)
    has_content = False
    if mask_arr is not None:
        if len(mask_arr.shape) == 3 and mask_arr.shape[2] >= 3:
            has_content = bool(
                np.any(mask_arr[:, :, 0] > 50)
                or np.any(mask_arr[:, :, 1] > 50)
                or np.any(mask_arr[:, :, 2] > 50)
            )
        else:
            has_content = bool(np.any(mask_arr > 50))

    if has_content:
        evicted = set_user_mask(path, mask_bytes)
        with batch_lock:
            if path not in batch_state["detections"]:
                batch_state["detections"][path] = {"boxes": [], "masks": []}
            batch_state["user_edits"].add(path)
        return jsonify({"ok": True, "has_mask": True, "evicted_masks": evicted})

    remove_detection_and_mask(path)
    with batch_lock:
        batch_state["user_edits"].add(path)
    return jsonify({"ok": True, "has_mask": False})


@batch_train_bp.route("/api/batch/detect", methods=["POST"])
def api_batch_detect():
    """Start asynchronous batch detection process."""
    data = json_body()
    valid, message = validate_batch_detect_payload(data)
    if not valid:
        return fail(message, code=EC.INVALID_PAYLOAD)
    payload = cast(BatchDetectPayload, data)
    files = payload.get("files", [])
    ok, msg = run_batch_detect(files, as_float(payload.get("confidence", 0.3), 0.3))
    if not ok:
        return fail(msg, code=EC.BATCH_DETECT_FAILED)
    return jsonify({"ok": True, "error": None})


@batch_train_bp.route("/api/batch/clean", methods=["POST"])
def api_batch_clean():
    """Start asynchronous batch cleaning process."""
    data = json_body()
    valid, message = validate_batch_clean_payload(data)
    if not valid:
        return fail(message, code=EC.INVALID_PAYLOAD)
    payload = cast(BatchCleanPayload, data)
    all_files = payload.get("all_files", [])
    ok, msg = run_batch_clean(
        payload.get("method", "white"),
        as_int(payload.get("padding", 2), 2),
        payload.get("output_dir", ""),
        payload.get("root_dir", ""),
        payload.get("has_subfolders", False),
        all_files,
    )
    if not ok:
        return fail(msg, code=EC.BATCH_CLEAN_FAILED)
    return jsonify({"ok": True, "error": None})


@batch_train_bp.route("/api/batch/stop", methods=["POST"])
def api_batch_stop():
    """Request batch worker stop via shared stop flag."""
    requested = request_batch_stop()
    return jsonify({"ok": True, "stop_requested": requested})


@batch_train_bp.route("/api/train/status")
def api_train_status():
    """Return current training status and short progress log tail."""
    corrections_dir = os.path.join(YOLO_DIR, "corrections")
    originals = os.path.join(corrections_dir, "original")
    if os.path.isdir(originals):
        corrections_count = len(
            [f for f in os.listdir(originals) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
        )
    else:
        corrections_count = 0
    with state_lock:
        training_snapshot = {
            "training": state["training"],
            "progress": state["training_progress"],
            "epoch_current": state["training_epoch_current"],
            "epochs_total": state["training_epochs_total"],
            "log": state["training_log"][-50:],
        }
    return jsonify(
        {
            **training_snapshot,
            "corrections_count": corrections_count,
            "corrections_dir": corrections_dir,
        }
    )


@batch_train_bp.route("/api/train/start", methods=["POST"])
def api_train_start():
    """Start full training from original/cleaned folder pairs."""
    data = json_body()
    ok, msg = start_training(
        data.get("original_dir", ""),
        data.get("cleaned_dir", ""),
        as_int(data.get("epochs", 30), 30),
        as_int(data.get("img_size", 640), 640),
        data.get("base_model", "yolov8n-seg.pt"),
    )
    if not ok:
        return fail(msg, code=EC.TRAIN_START_FAILED)
    return jsonify({"ok": True, "message": msg, "error": None})


@batch_train_bp.route("/api/train/finetune", methods=["POST"])
def api_train_finetune():
    """Start fine-tuning based on corrections dataset."""
    data = json_body()
    ok, msg = start_finetune(
        as_int(data.get("epochs", 10), 10),
        as_int(data.get("img_size", 640), 640),
        data.get("corrections_dir", "") or None,
        data.get("base_model", "") or None,
    )
    if not ok:
        return fail(msg, code=EC.FINETUNE_START_FAILED)
    return jsonify({"ok": True, "error": None})


@batch_train_bp.route("/api/train/stop", methods=["POST"])
def api_train_stop():
    """Request training loop stop via shared state flag."""
    with state_lock:
        state["training"] = False
    add_log("Training stop requested")
    return jsonify({"ok": True})
