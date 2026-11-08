"""Training and fine-tuning YOLO."""

import os
import shutil
import threading
import traceback
from pathlib import Path

from .config import YOLO_DIR, logger, state, state_lock
from .log_context import log_event
from .models import _ensure_imports


def add_log(msg):
    with state_lock:
        state["training_log"].append(msg)
    logger.info(msg)


def _log_training_event(message: str, *, phase: str, level: str = "info", **fields) -> None:
    log_event(logger, message, component="train", phase=phase, level=level, **fields)


def _is_training_active():
    with state_lock:
        return bool(state["training"])


def _yolo_load(model_path):
    """Load YOLO model without mutating process-wide working directory."""
    from ultralytics import YOLO

    os.makedirs(YOLO_DIR, exist_ok=True)
    return YOLO(model_path)


def _init_training_state(epochs: int):
    with state_lock:
        if state["training"]:
            _log_training_event("Training start rejected: already running", phase="start_rejected")
            return False, "Training already running"
        state["training"] = True
        state["training_progress"] = 0
        state["training_log"] = []
        state["training_epochs_total"] = epochs
        state["training_epoch_current"] = 0
    _log_training_event("Training state initialized", phase="start", epochs=epochs)
    return True, None


def _finalize_training_state():
    with state_lock:
        state["training"] = False
    _log_training_event("Training state finalized", phase="finalize")


def _finalize_trained_model(
    best_weights_path: Path,
    *,
    output_model_path: str,
    move_model_to_cuda: bool,
    complete_log: str,
) -> bool:
    if not best_weights_path.exists():
        return False

    shutil.copy(str(best_weights_path), output_model_path)
    loaded_model = _yolo_load(output_model_path)
    with state_lock:
        state["model_path"] = output_model_path
        state["yolo_model"] = loaded_model
        if move_model_to_cuda and state["device"] == "cuda":
            state["yolo_model"].to("cuda")
    add_log(complete_log)
    return True


def _run_yolo_training(
    *,
    yaml_path: str,
    epochs: int,
    img_size: int,
    base_model_path: str,
    progress_base: int,
    progress_span: int,
    log_label: str,
    log_metrics: bool,
    output_model_path: str,
    move_model_to_cuda: bool,
    complete_log: str,
):
    if not _is_training_active():
        add_log(f"{log_label} cancelled")
        _log_training_event("Training cancelled before train() call", phase="cancelled_pre_start")
        return

    _log_training_event(
        "YOLO training started",
        phase="train_start",
        epochs=epochs,
        img_size=img_size,
    )
    model = _yolo_load(base_model_path)

    def _on_epoch_end(trainer):
        if not _is_training_active():
            setattr(trainer, "stop", True)
            return
        ep = trainer.epoch + 1
        with state_lock:
            state["training_epoch_current"] = ep
            state["training_progress"] = progress_base + int(ep / epochs * progress_span)
        ls = ""
        ms = ""
        if log_metrics:
            if hasattr(trainer, "loss") and trainer.loss is not None:
                try:
                    loss_value = (
                        trainer.loss.item()
                        if hasattr(trainer.loss, "item")
                        else float(trainer.loss)
                    )
                    ls = f" | loss:{loss_value:.4f}"
                except Exception:
                    pass
            if hasattr(trainer, "metrics") and trainer.metrics:
                metrics = trainer.metrics
                map50 = metrics.get(
                    "metrics/mAP50(M)",
                    metrics.get("metrics/mAP50(B)", metrics.get("metrics/mAP50", 0)),
                )
                ms = f" | mAP50:{map50:.3f}" if map50 else ""
        add_log(f"  Epoch {ep}/{epochs}{ls}{ms}")

    model.add_callback("on_train_epoch_end", _on_epoch_end)
    with state_lock:
        train_device = state["device"]
    results = model.train(
        data=yaml_path,
        epochs=epochs,
        imgsz=img_size,
        plots=False,
        device=train_device,
        verbose=False,
        exist_ok=True,
        workers=0,
        project=YOLO_DIR,
    )
    best_weights_path = Path(results.save_dir) / "weights" / "best.pt"
    _finalize_trained_model(
        best_weights_path,
        output_model_path=output_model_path,
        move_model_to_cuda=move_model_to_cuda,
        complete_log=complete_log,
    )
    with state_lock:
        state["training_progress"] = 100
    _log_training_event("YOLO training completed", phase="train_done", output_model=output_model_path)


def _build_yolo_segmentation_labels(contours, image_width: int, image_height: int, cv2, *, min_area: int) -> list[str]:
    """Convert contours to YOLO segmentation label lines."""
    label_lines: list[str] = []
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
        eps = 0.01 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, eps, True)
        if len(approx) < 3:
            continue
        points = []
        for pt in approx:
            px, py = pt[0]
            points.append(f"{px/image_width:.6f}")
            points.append(f"{py/image_height:.6f}")
        label_lines.append("0 " + " ".join(points))
    return label_lines


# All temp/data dirs live inside yolo/
DATASET_DIR = os.path.join(YOLO_DIR, "dataset_temp")
FINETUNE_DIR = os.path.join(YOLO_DIR, "finetune_temp")
CORRECTIONS_DIR = os.path.join(YOLO_DIR, "corrections")


def _prepare_runtime_dir(preferred_dir: str, fallback_name: str) -> str:
    """Create an empty runtime directory; fallback to workspace if preferred path is blocked."""
    target_dir = preferred_dir
    try:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir, exist_ok=True)
        return target_dir
    except OSError as exc:
        fallback_root = os.path.join(os.getcwd(), "tmp_test_run")
        fallback_dir = os.path.join(fallback_root, fallback_name)
        add_log(
            f"  [WARN] Runtime dir unavailable: {target_dir} ({exc}); using fallback: {fallback_dir}"
        )
        if os.path.exists(fallback_dir):
            shutil.rmtree(fallback_dir, ignore_errors=True)
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir


def start_training(orig_dir, clean_dir, epochs=30, img_size=640, base_model="yolov8n-seg.pt"):
    if not orig_dir or not clean_dir:
        return False, "Specify both folders"
    if not os.path.isdir(orig_dir):
        return False, f"Folder not found: {orig_dir}"
    if not os.path.isdir(clean_dir):
        return False, f"Folder not found: {clean_dir}"
    ok, err = _init_training_state(epochs)
    if not ok:
        return False, err

    def train_thread():
        _ensure_imports()
        from .models import cv2, np
        import yaml

        try:
            add_log("=== DATASET PREPARATION ===")
            dataset_dir = _prepare_runtime_dir(DATASET_DIR, "dataset_temp")
            images_train_dir = os.path.join(dataset_dir, "images", "train")
            labels_train_dir = os.path.join(dataset_dir, "labels", "train")
            images_val_dir = os.path.join(dataset_dir, "images", "val")
            labels_val_dir = os.path.join(dataset_dir, "labels", "val")
            for target_dir in [images_train_dir, labels_train_dir, images_val_dir, labels_val_dir]:
                os.makedirs(target_dir, exist_ok=True)
            orig_files = sorted(
                [
                    f
                    for f in os.listdir(orig_dir)
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                ]
            )
            add_log(f"Found {len(orig_files)} files")
            count = 0
            for idx, fname in enumerate(orig_files):
                if not _is_training_active():
                    add_log("Training cancelled")
                    return
                op = os.path.join(orig_dir, fname)
                cp = os.path.join(clean_dir, fname)
                if not os.path.exists(cp):
                    stem = os.path.splitext(fname)[0]
                    found = False
                    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                        alt = os.path.join(clean_dir, stem + ext)
                        if os.path.exists(alt):
                            cp = alt
                            found = True
                            break
                    if not found:
                        continue
                original_img = cv2.imread(op)
                cleaned_img = cv2.imread(cp)
                if original_img is None or cleaned_img is None:
                    continue
                if original_img.shape != cleaned_img.shape:
                    cleaned_img = cv2.resize(
                        cleaned_img, (original_img.shape[1], original_img.shape[0])
                    )
                diff = cv2.absdiff(original_img, cleaned_img)
                gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(gray_diff, 15, 255, cv2.THRESH_BINARY)
                kernel = np.ones((3, 3), np.uint8)
                mask = cv2.dilate(mask, kernel, iterations=1)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                image_height, image_width = original_img.shape[:2]
                label_lines = _build_yolo_segmentation_labels(
                    contours,
                    image_width,
                    image_height,
                    cv2,
                    min_area=80,
                )
                if label_lines:
                    is_val = (count % 5 == 0) and count > 0
                    image_dest_dir = images_val_dir if is_val else images_train_dir
                    label_dest_dir = labels_val_dir if is_val else labels_train_dir
                    output_name = f"{count:05d}{os.path.splitext(fname)[1]}"
                    shutil.copy(op, os.path.join(image_dest_dir, output_name))
                    with open(os.path.join(label_dest_dir, f"{count:05d}.txt"), "w") as label_file:
                        label_file.write("\n".join(label_lines))
                    count += 1
                with state_lock:
                    state["training_progress"] = int((idx + 1) / len(orig_files) * 20)
            add_log(f"Prepared {count} images")
            if count == 0:
                add_log("No differences found")
                with state_lock:
                    state["training"] = False
                return
            yaml_config = {
                "path": os.path.abspath(dataset_dir),
                "train": "images/train",
                "val": "images/val" if count // 5 > 0 else "images/train",
                "nc": 1,
                "names": ["artifact"],
            }
            yaml_path = os.path.join(dataset_dir, "data.yaml")
            with open(yaml_path, "w") as yaml_file:
                yaml.dump(yaml_config, yaml_file)
            add_log("")
            add_log(f"=== TRAINING: {epochs} epochs ===")
            with state_lock:
                state["training_progress"] = 20
            output_model_path = os.path.join(YOLO_DIR, "best_manga_cleaner.pt")
            _run_yolo_training(
                yaml_path=yaml_path,
                epochs=epochs,
                img_size=img_size,
                base_model_path=base_model,
                progress_base=20,
                progress_span=75,
                log_label="Training",
                log_metrics=True,
                output_model_path=output_model_path,
                move_model_to_cuda=True,
                complete_log=f"Model saved: {output_model_path}",
            )
        except Exception as exc:
            add_log(f"Error: {exc}")
            add_log(traceback.format_exc())
            _log_training_event(f"Training worker failed: {exc}", phase="error", level="error")
        finally:
            _finalize_training_state()

    threading.Thread(target=train_thread, daemon=True).start()
    return True, "Training started"


def start_finetune(epochs=10, img_size=640, corrections_dir=None, base_model=None):
    corrections_root = corrections_dir or CORRECTIONS_DIR
    originals_dir = os.path.join(corrections_root, "original")
    masks_dir = os.path.join(corrections_root, "masks")
    if not os.path.isdir(originals_dir) or not os.path.isdir(masks_dir):
        return False, "No corrections found"
    with state_lock:
        base_model_path = base_model or state["model_path"]
    if not os.path.exists(base_model_path):
        return False, f"Model not found: {base_model_path}"
    ok, err = _init_training_state(epochs)
    if not ok:
        return False, err

    def _finetune_thread():
        _ensure_imports()
        from .models import cv2, np
        import yaml

        try:
            add_log("=== FINE-TUNING ===")
            dataset_dir = _prepare_runtime_dir(FINETUNE_DIR, "finetune_temp")
            images_train_dir = os.path.join(dataset_dir, "images", "train")
            labels_train_dir = os.path.join(dataset_dir, "labels", "train")
            os.makedirs(images_train_dir, exist_ok=True)
            os.makedirs(labels_train_dir, exist_ok=True)
            original_files = sorted(
                [
                    f
                    for f in os.listdir(originals_dir)
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                ]
            )
            count = 0
            for idx, file_name in enumerate(original_files):
                if not _is_training_active():
                    add_log("Fine-tuning cancelled")
                    return
                original_path = os.path.join(originals_dir, file_name)
                stem = os.path.splitext(file_name)[0]
                mask_path = os.path.join(masks_dir, stem + ".png")
                if not os.path.exists(mask_path):
                    continue
                img = cv2.imread(original_path)
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                if img is None or mask is None:
                    continue
                if mask.shape[:2] != img.shape[:2]:
                    mask = cv2.resize(mask, (img.shape[1], img.shape[0]))
                _, mask_binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
                kernel = np.ones((3, 3), np.uint8)
                mask_binary = cv2.dilate(mask_binary, kernel, iterations=1)
                contours, _ = cv2.findContours(
                    mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                image_height, image_width = img.shape[:2]
                label_lines = _build_yolo_segmentation_labels(
                    contours,
                    image_width,
                    image_height,
                    cv2,
                    min_area=50,
                )
                output_name = f"ft_{count:04d}{os.path.splitext(file_name)[1]}"
                shutil.copy(original_path, os.path.join(images_train_dir, output_name))
                with open(os.path.join(labels_train_dir, f"ft_{count:04d}.txt"), "w") as label_file:
                    label_file.write("\n".join(label_lines))
                count += 1
                with state_lock:
                    state["training_progress"] = int((idx + 1) / len(original_files) * 20)
            if count == 0:
                add_log("No data")
                with state_lock:
                    state["training"] = False
                return
            yaml_config = {
                "path": os.path.abspath(dataset_dir),
                "train": "images/train",
                "val": "images/train",
                "nc": 1,
                "names": ["artifact"],
            }
            yaml_path = os.path.join(dataset_dir, "data.yaml")
            with open(yaml_path, "w") as yaml_file:
                yaml.dump(yaml_config, yaml_file)
            with state_lock:
                state["training_progress"] = 20
            output_model_path = os.path.join(YOLO_DIR, "best_manga_cleaner.pt")
            _run_yolo_training(
                yaml_path=yaml_path,
                epochs=epochs,
                img_size=img_size,
                base_model_path=base_model_path,
                progress_base=20,
                progress_span=75,
                log_label="Fine-tuning",
                log_metrics=False,
                output_model_path=output_model_path,
                move_model_to_cuda=False,
                complete_log="Fine-tuning complete!",
            )
        except Exception as exc:
            add_log(f"Error: {exc}")
            add_log(traceback.format_exc())
            _log_training_event(f"Fine-tune worker failed: {exc}", phase="error", level="error")
        finally:
            _finalize_training_state()

    threading.Thread(target=_finetune_thread, daemon=True).start()
    return True, "OK"
