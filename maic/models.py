"""ML models (YOLO, LaMa) with lazy imports."""

import os
import threading

from .config import logger, state, state_lock

cv2 = None
np = None
Image = None
_imports_lock = threading.Lock()
_lama_fallback_lock = threading.Lock()
_lama_fallback_warned = False
_lama_load_lock = threading.Lock()


def _ensure_imports():
    global cv2, np, Image
    if cv2 is not None:
        return
    with _imports_lock:
        if cv2 is not None:
            return
        import cv2 as _cv2
        import numpy as _np
        from PIL import Image as _Image

        cv2 = _cv2
        np = _np
        Image = _Image


def load_yolo(path=None):
    with state_lock:
        if path:
            state["model_path"] = path
        model_path = state["model_path"]
        device = state["device"]
    if not os.path.exists(model_path):
        return False, f"File not found: {model_path}"
    try:
        from ultralytics import YOLO

        loaded_model = YOLO(model_path)
        if device == "cuda":
            loaded_model.to("cuda")
        with state_lock:
            state["yolo_model"] = loaded_model
        return True, f"Model loaded: {os.path.basename(model_path)}"
    except Exception as exc:
        return False, f"Error: {exc}"


def load_lama():
    with _lama_load_lock:
        with state_lock:
            if state["lama_model"] is not None:
                return True
            device = state["device"]
        try:
            from .lama import Lama
            loaded_model = Lama(device=device)
            with state_lock:
                state["lama_model"] = loaded_model
            return True
        except Exception as exc:
            logger.warning("LaMa loading failed (%s): %s", type(exc).__name__, exc)
            return False


def extract_detections(results):
    _ensure_imports()
    boxes = []
    masks = []
    for result in results:
        for box in result.boxes:
            coords = box.xyxy[0].tolist()
            boxes.append([int(c) for c in coords])
        if hasattr(result, "masks") and result.masks is not None:
            for m in result.masks.xy:
                poly = [[int(p[0]), int(p[1])] for p in m]
                if len(poly) >= 3:
                    masks.append(poly)
    return boxes, masks


def create_mask_image(h_img, w_img, det, pad=2):
    _ensure_imports()
    mask = np.zeros((h_img, w_img), dtype=np.uint8)
    polygons = det.get("masks", [])
    boxes_list = det.get("boxes", [])
    if polygons:
        for poly in polygons:
            pts = np.array(poly, dtype=np.int32)
            cv2.fillPoly(mask, [pts], 255)
        if pad > 0:
            kernel = np.ones((pad * 2 + 1, pad * 2 + 1), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)
    else:
        for x1, y1, x2, y2 in boxes_list:
            mask[max(0, y1 - pad - 3) : min(h_img, y2 + pad + 3), max(0, x1 - pad - 3) : min(w_img, x2 + pad + 3)] = 255
    return mask


def _mask_fill_color_from_surroundings(img, binary_mask):
    mask = binary_mask > 0
    if not np.any(mask):
        return [255, 255, 255]

    mask_u8 = mask.astype(np.uint8) * 255
    kernel = np.ones((15, 15), np.uint8)
    ring = (cv2.dilate(mask_u8, kernel, iterations=1) > 0) & ~mask
    if not np.any(ring):
        ring = ~mask
    if not np.any(ring):
        return [255, 255, 255]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    median_luma = float(np.median(gray[ring]))
    fill = 0 if median_luma < 128 else 255
    return [fill, fill, fill]


def _normalize_mask_shape(binary_mask, img):
    h_img, w_img = img.shape[:2]
    if binary_mask is None:
        return np.zeros((h_img, w_img), dtype=np.uint8)
    if len(binary_mask.shape) == 3:
        binary_mask = binary_mask[:, :, 0]
    if binary_mask.shape[:2] != (h_img, w_img):
        binary_mask = cv2.resize(binary_mask, (w_img, h_img), interpolation=cv2.INTER_NEAREST)
    if binary_mask.dtype != np.uint8:
        binary_mask = binary_mask.astype(np.uint8)
    _, binary_mask = cv2.threshold(binary_mask, 0, 255, cv2.THRESH_BINARY)
    return binary_mask


def clean_image(img, binary_mask, method="white"):
    global _lama_fallback_warned
    _ensure_imports()
    h_img, w_img = img.shape[:2]
    binary_mask = _normalize_mask_shape(binary_mask, img)
    if method == "white":
        result = img.copy()
        result[binary_mask > 0] = [255, 255, 255]
    elif method == "fill":
        # Flat fill with the dominant surrounding colour. This is the same
        # visible outcome as the "lama" branch below, which discards the model
        # output inside the mask anyway, so previews can use it to match the
        # converted page without paying for a model load.
        result = img.copy()
        result[binary_mask > 0] = _mask_fill_color_from_surroundings(img, binary_mask)
    elif method == "inpaint":
        result = cv2.inpaint(img, binary_mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
    elif method == "lama":
        if load_lama():
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            mask_pil = Image.fromarray(binary_mask)
            result_pil = state["lama_model"](img_pil, mask_pil)
            result = cv2.cvtColor(np.array(result_pil), cv2.COLOR_RGB2BGR)
            if result.shape[:2] != (h_img, w_img):
                result = cv2.resize(result, (w_img, h_img), interpolation=cv2.INTER_LINEAR)
            # Some LaMa implementations reconstruct the whole image and can
            # introduce faint pixels far outside the requested mask. Apart
            # from needlessly altering the page, those pixels can anchor the
            # later margin detector to an otherwise blank scanner edge.
            # Inpainting is only allowed to affect explicitly masked pixels.
            result[binary_mask == 0] = img[binary_mask == 0]
        else:
            with _lama_fallback_lock:
                if not _lama_fallback_warned:
                    logger.warning("LaMa model unavailable; falling back to OpenCV inpaint")
                    _lama_fallback_warned = True
            result = cv2.inpaint(img, binary_mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
        result[binary_mask > 0] = _mask_fill_color_from_surroundings(img, binary_mask)
    else:
        result = img.copy()
        result[binary_mask > 0] = [255, 255, 255]
    return result
