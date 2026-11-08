"""Small LaMa TorchScript adapter using the existing big-lama.pt weights.

Input normalization and symmetric modulo-eight padding match the public LaMa
model contract. No dependency on the obsolete simple-lama-inpainting package.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import urlparse

MODEL_URL = "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt"
MODEL_SHA256 = "7ba7aa7ac37a4d41fdbbeba3a2af7ead18058552997e3a3cd1a3b2210c9e6b4c"
_DOWNLOAD_LOCK = threading.Lock()


def model_path():
    import torch
    override = os.environ.get("LAMA_MODEL")
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"LaMa model not found: {path}")
        return path
    url = os.environ.get("LAMA_MODEL_URL", MODEL_URL)
    name = Path(urlparse(url).path).name
    if not name:
        raise ValueError("LAMA_MODEL_URL must name a model file")
    path = Path(torch.hub.get_dir()) / "checkpoints" / name
    with _DOWNLOAD_LOCK:
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=name + ".", suffix=".download", dir=path.parent)
            os.close(fd)
            try:
                torch.hub.download_url_to_file(url, temporary, progress=True)
                if url == MODEL_URL:
                    with open(temporary, "rb") as stream:
                        if hashlib.file_digest(stream, "sha256").hexdigest() != MODEL_SHA256:
                            raise ValueError("Downloaded LaMa weights do not match the tested model checksum")
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
    return path


class Lama:
    def __init__(self, device="cpu", path=None):
        import torch
        self.device = torch.device(device)
        self.path = Path(path) if path is not None else model_path()
        self.model = torch.jit.load(str(self.path), map_location=self.device).eval()
        self._lock = threading.Lock()

    def __call__(self, image, mask):
        import numpy as np
        import torch
        from PIL import Image

        image = image.convert("RGB") if isinstance(image, Image.Image) else Image.fromarray(image).convert("RGB")
        mask = mask.convert("L") if isinstance(mask, Image.Image) else Image.fromarray(mask).convert("L")
        if image.size != mask.size:
            raise ValueError("LaMa image and mask dimensions must match")
        width, height = image.size
        if width < 1 or height < 1:
            raise ValueError("LaMa needs a nonempty image")
        pixels = np.asarray(image, dtype=np.float32).transpose(2, 0, 1) / 255.0
        selected = np.asarray(mask) > 0
        if not selected.any():
            return image.copy()
        padded = np.pad(pixels, ((0, 0), (0, (-height) % 8), (0, (-width) % 8)), mode="symmetric")
        binary = np.pad(selected[None], ((0, 0), (0, (-height) % 8), (0, (-width) % 8)), mode="symmetric")
        tensor = torch.from_numpy(np.ascontiguousarray(padded)).unsqueeze(0).to(self.device)
        # The reference adapter supplies an int64 mask.
        mask_tensor = torch.from_numpy(binary.astype(np.int64)).unsqueeze(0).to(self.device)
        with self._lock, torch.inference_mode():
            output = self.model(tensor, mask_tensor)
        restored = output[0, :, :height, :width].permute(1, 2, 0).detach().cpu().numpy()
        restored = np.clip(restored * 255, 0, 255).astype(np.uint8)
        return Image.fromarray(restored)
