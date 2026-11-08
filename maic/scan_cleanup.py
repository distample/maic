"""Automatic 1x JPEG-artifact cleanup for scanned manga pages.

The MangaJPEG model names describe the quality of the *input* JPEG, not the
quality of their output.  JPEG does not store that number in its header, so we
recover the nearest IJG quality from the luminance quantisation table and use
the range published for each model.  PNG, GIF and JPEGs above quality 95 are
left alone: there is no matching compression-restoration model for them.

The networks are grayscale, but :func:`maic.manga_upscale.restore_image` runs
one over luma and carries the original chroma alongside it.  A colour cover or
colour insert therefore stays colour.
"""

import io
import threading

from .manga_upscale import ensure_model_file, restore_image, uses_half_precision


MODEL_CREDIT = "MangaJPEG by Bunzero++ (CC BY-NC-SA 4.0)"

JPEG_MODELS = {
    "HQPlus": {
        "filename": "1x-MangaJPEGHQPlus.pth",
        "url": (
            "https://objectstorage.us-phoenix-1.oraclecloud.com/n/"
            "ax6ygfvpvzka/b/open-modeldb-files/o/1x-MangaJPEGHQPlus.pth"
        ),
        "sha256": "3126339603a3876f541d054bd40cdad417141a32c14e91fd6adaeaf04677be34",
    },
    "HQ": {
        "filename": "1x-MangaJPEGHQ.pth",
        "url": (
            "https://objectstorage.us-phoenix-1.oraclecloud.com/n/"
            "ax6ygfvpvzka/b/open-modeldb-files/o/1x-MangaJPEGHQ.pth"
        ),
        "sha256": "e2898bfba74083025a2bd2326b6c159031b882a890bd1cc30fd6910cda2ce4ee",
    },
    "MQ": {
        "filename": "1x-MangaJPEGMQ.pth",
        "url": (
            "https://objectstorage.us-phoenix-1.oraclecloud.com/n/"
            "ax6ygfvpvzka/b/open-modeldb-files/o/1x-MangaJPEGMQ.pth"
        ),
        "sha256": "42529335f43ac04f615af3442b2570d23dc64a206e2da4741bf5f835206354ae",
    },
    "LQ": {
        "filename": "1x-MangaJPEGLQ.pth",
        "url": (
            "https://objectstorage.us-phoenix-1.oraclecloud.com/n/"
            "ax6ygfvpvzka/b/open-modeldb-files/o/1x-MangaJPEGLQ.pth"
        ),
        "sha256": "af11ec91b6a38e0109cbb926b19e8a01975f947aacb3490f008dcab06e9b922d",
    },
}

# ITU-T T.81 / IJG base luminance table.  Pillow exposes JPEG quantisation in
# this same order, so standard encoder qualities match with zero error.
_LUMA_BASE = (
    16, 11, 10, 16, 24, 40, 51, 61,
    12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56,
    14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77,
    24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101,
    72, 92, 95, 98, 112, 100, 103, 99,
)


def _quality_table(quality):
    quality = max(1, min(100, int(quality)))
    scale = 5000 // quality if quality < 50 else 200 - quality * 2
    return tuple(max(1, min(255, (value * scale + 50) // 100)) for value in _LUMA_BASE)


_REFERENCE_TABLES = {quality: _quality_table(quality) for quality in range(1, 101)}


def estimate_jpeg_quality(data):
    """Nearest standard IJG/Pillow JPEG quality, or ``None`` for other data."""
    if not data or data[:2] != b"\xff\xd8":
        return None

    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as image:
            table = tuple((image.quantization or {}).get(0, ()))
    except Exception:
        return None
    if len(table) != 64:
        return None

    return min(
        _REFERENCE_TABLES,
        key=lambda quality: sum(
            abs(int(actual) - expected)
            for actual, expected in zip(table, _REFERENCE_TABLES[quality])
        ),
    )


def model_for_quality(quality):
    """Published MangaJPEG range for an estimated input *quality*."""
    if quality is None:
        return None
    quality = int(quality)
    if 81 <= quality <= 95:
        return "HQPlus"
    if 61 <= quality <= 80:
        return "HQ"
    if 26 <= quality <= 60:
        return "MQ"
    if quality <= 25:
        return "LQ"
    return None


def _noop_log(message):
    pass


def _torch_infer_factory(log_fn=None):
    log = log_fn or _noop_log

    def factory(name):
        import numpy as np
        import torch

        from ._esrgan import build_generator, describe_state_dict

        spec = JPEG_MODELS[name]
        path = ensure_model_file(spec, log_fn=log)
        state = torch.load(path, map_location="cpu", weights_only=True)
        for wrapper in ("params_ema", "params", "state_dict"):
            if isinstance(state, dict) and wrapper in state:
                state = state[wrapper]
        shape = describe_state_dict(state)
        model = build_generator(state)
        model.train(False)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        if device == "cuda":
            # These convolution-only models reuse channels-last feature maps
            # on CUDA. Keep the same weights, FP16 policy, tiles and overlap.
            model.to(memory_format=torch.channels_last)
        if device == "cpu":
            log("SCAN CLEANUP: no CUDA device; cleanup will be slow")
        log("SCAN CLEANUP: %s loaded on %s (%s)" % (spec["filename"], device, MODEL_CREDIT))
        channels = int(shape["channels"])
        half = uses_half_precision(device)

        def infer(tile):
            batch = torch.from_numpy(np.ascontiguousarray(tile)).to(device) / 255.0
            batch = batch.unsqueeze(0).unsqueeze(0)
            if channels > 1:
                batch = batch.repeat(1, channels, 1, 1)
            with torch.no_grad():
                if half:
                    with torch.autocast("cuda", dtype=torch.float16):
                        out = model(batch)
                else:
                    out = model(batch)
            out = out.float().clamp(0.0, 1.0).squeeze(0)
            out = out.mean(dim=0) if channels > 1 else out.squeeze(0)
            return out.mul(255.0).cpu().numpy()

        def close():
            nonlocal model
            model = None
        infer.close = close
        return infer

    return factory


class ScanCleaner:
    """One volume's automatic MangaJPEG cleanup state."""

    def __init__(self, enabled=True, infer_factory=None, log_fn=None):
        self.enabled = bool(enabled)
        self._infer_factory = infer_factory or _torch_infer_factory(log_fn)
        self._log = log_fn or _noop_log
        self._loaded = {}
        self._counts = {}
        self._qualities = {}
        self._lock = threading.RLock()

    def model_for(self, data):
        if not self.enabled:
            return None
        quality = estimate_jpeg_quality(data)
        name = model_for_quality(quality)
        if name:
            self._qualities[name] = quality
        return name

    def close(self):
        """Wait for this volume's inference, then drop only its models."""
        with self._lock:
            self.enabled = False
            loaded = list(self._loaded.values())
            self._loaded.clear()
            for infer in loaded:
                close = getattr(infer, "close", None)
                if close is not None:
                    close()

    def apply(self, image, name):
        with self._lock:
            return self._apply(image, name)

    def _apply(self, image, name):
        if not self.enabled or name not in JPEG_MODELS:
            return image
        try:
            infer = self._model(name)
        except Exception as exc:
            self.enabled = False
            self._log("SCAN CLEANUP: disabled (%s)" % exc)
            return image
        try:
            cleaned = restore_image(image, infer, scale=1, tile=512, overlap=24)
        except Exception as exc:
            self._log("SCAN CLEANUP: page left as it was (%s)" % exc)
            return image
        self._counts[name] = self._counts.get(name, 0) + 1
        return cleaned

    def quality_for(self, name):
        return self._qualities.get(name)

    def summary(self):
        if not self._counts:
            return None
        details = ", ".join(
            "%s %d" % (name, self._counts[name])
            for name in ("HQPlus", "HQ", "MQ", "LQ")
            if self._counts.get(name)
        )
        return "  [SCAN CLEANUP] %d pages (%s; %s)" % (
            sum(self._counts.values()), details, MODEL_CREDIT
        )

    def _model(self, name):
        with self._lock:
            if name not in self._loaded:
                self._loaded[name] = self._infer_factory(name)
            return self._loaded[name]
