"""Manga upscaling, for pages that have to be lifted to the render height.

KFX pages are built 1920 px tall so the device performs the last reduction
itself.  Most scanlation sources are shorter than that -- 1400 and 1200 are the
common ones -- so nearly every page is enlarged, and a plain resample costs
about a quarter of the linework's sharpness: measured over a real volume, edge
energy falls from 15.6 to 11.5 when a page goes from 959x1400 to 1315x1920.

The UI exposes two deliberately different passes.  ``Fast`` uses MangaJaNai,
choosing one of its seven source-height models and restoring the white point.
``Exact`` enlarges with Manga Ora.  JPEG cleanup is an independent pass, so it
runs before either upscaler only when the user enables Scan cleanup.  Unlike
the fast pass, Exact does no extra white-point remapping.

Models by the-database, CC BY-NC 4.0, published as one archive.  It is fetched
on demand and read from where it lies: maic keeps no copy in the repository and
the credit stays with the author.
"""

import hashlib
import io
import os
import threading
import zipfile

MODEL_CREDIT = "MangaJaNai by the-database (CC BY-NC 4.0)"
EXACT_MODEL_CREDIT = "Manga Ora by Ora/null-llun (CC BY-NC-SA 4.0)"
ARCHIVE = {
    "filename": "MangaJaNai_V1_ModelsOnly.zip",
    "url": ("https://github.com/the-database/MangaJaNai/releases/download/1.0.0/"
            "MangaJaNai_V1_ModelsOnly.zip"),
    "sha256": "5156f4167875bba51a8ed52bd1c794b0d7277f7103f99b397518066e4dda7e55",
}

# One model per source height, as the author trained them.  The 2x models are
# taken rather than the 4x: the lift needed here is 1.1x to 1.6x, so 4x would be
# thrown away in the resize that follows while costing several times the work.
MODELS = {
    1200: "2x_MangaJaNai_1200p_V1_ESRGAN_70k.pth",
    1300: "2x_MangaJaNai_1300p_V1_ESRGAN_75k.pth",
    1400: "2x_MangaJaNai_1400p_V1_ESRGAN_70k.pth",
    1500: "2x_MangaJaNai_1500p_V1_ESRGAN_90k.pth",
    1600: "2x_MangaJaNai_1600p_V1_ESRGAN_90k.pth",
    1920: "2x_MangaJaNai_1920p_V1_ESRGAN_70k.pth",
    2048: "2x_MangaJaNai_2048p_V1_ESRGAN_95k.pth",
}
MODEL_HEIGHTS = tuple(sorted(MODELS))

# Tiles bound memory: the model sees a fixed patch rather than a whole page.
TILE_SIZE = 512
TILE_OVERLAP = 16

# The paper beside the linework.  The models clean it but do not flatten it,
# and a page whose white is a couple of levels short reaches the screen as
# visible dither.  Measured over eight pages of a quality-60 volume, the share
# of the zone beside the linework that is not clean white falls from 27% to 12%.
WHITE_POINT = 245

MODE_OFF = 0
MODE_FAST = 1
MODE_EXACT = 2

# Kept as aliases for callers importing the old names.  Their old scheduling
# meaning (auto/always) is gone: both new modes only run where enlargement is
# required, and the value now selects the restoration pipeline.
MODE_AUTO = MODE_FAST
MODE_ALWAYS = MODE_EXACT

EXACT_PIPELINE = "2x_MangaOra_exact"
MANGA_ORA_MODEL = {
    "filename": "2x_Manga_Ora.pth",
    "sha256": "27c57d6ce5d3e8934a93279e979a8813dcb5fe749b0f194f7e21d7e086170c6e",
}


def model_for_height(height):
    """The model trained closest to a page *height* pixels tall."""
    height = int(height)
    return MODELS[min(MODEL_HEIGHTS, key=lambda trained: abs(trained - height))]


def choose_model(height, mode, target_height):
    """Which pipeline a page of this height gets, or ``None`` to leave it alone."""
    try:
        mode = int(mode)
    except (TypeError, ValueError):
        return None
    if mode not in (MODE_FAST, MODE_EXACT):
        return None
    if int(height) >= int(target_height):
        return None
    if mode == MODE_EXACT:
        return EXACT_PIPELINE
    return model_for_height(height)


def _noop_log(message):
    pass


def _tile_offsets(total, tile, step):
    """Left edges of the tiles covering *total* pixels, last one flush to the end."""
    if total <= tile:
        return [0]
    offsets = list(range(0, total - tile, step))
    offsets.append(total - tile)
    return offsets


def restore_image(image, infer, *, scale, tile=TILE_SIZE, overlap=TILE_OVERLAP):
    """Run *infer* over *image* in tiles and return the enlarged page.

    *infer* maps a float32 array of luma in 0-255 to one *scale* times as large.
    Keeping it a plain callable is what lets the page walk be tested without
    torch: the real pass passes a callable closing over a loaded model.

    The models are trained on grey manga, so a colour page is carried through
    its luma and its chroma is enlarged separately -- covers stay colour, and
    nothing invents colour where the linework is.
    """
    import numpy as np
    from PIL import Image

    scale = max(1, int(scale))
    if image.mode == "L":
        luma, chroma = image, None
    else:
        source = image if image.mode == "RGB" else image.convert("RGB")
        luma, blue, red = source.convert("YCbCr").split()
        chroma = (blue, red)

    array = np.asarray(luma, dtype=np.float32)
    height, width = array.shape
    tile = max(1, int(tile))
    step = max(1, tile - max(0, int(overlap)))

    total = np.zeros((height * scale, width * scale), dtype=np.float32)
    counts = np.zeros_like(total)
    for top in _tile_offsets(height, tile, step):
        for left in _tile_offsets(width, tile, step):
            bottom = min(top + tile, height)
            right = min(left + tile, width)
            patch = np.ascontiguousarray(array[top:bottom, left:right])
            out = np.asarray(infer(patch), dtype=np.float32)
            total[top * scale:bottom * scale, left * scale:right * scale] += out
            counts[top * scale:bottom * scale, left * scale:right * scale] += 1.0

    restored = np.clip(total / counts, 0.0, 255.0)
    result = Image.fromarray(restored.round().astype(np.uint8), "L")
    if chroma is None:
        return result
    size = (width * scale, height * scale)
    planes = [plane.resize(size, Image.Resampling.BICUBIC) for plane in chroma]
    return Image.merge("YCbCr", (result, planes[0], planes[1])).convert("RGB")


def apply_white_point(image, white=WHITE_POINT):
    """Pull everything at or above *white* to paper, rescaling the range below.

    A hard cut would leave the haze sitting just under the threshold exactly as
    it was; rescaling lifts the whole light end with it.  A colour page is
    adjusted through its luma so the hue is left alone.
    """
    from PIL import Image

    white = int(white)
    if white <= 0 or white > 255:
        return image

    table = [255 if value >= white else int(round(255.0 * value / white)) for value in range(256)]
    if image.mode == "L":
        return image.point(table)

    source = image if image.mode == "RGB" else image.convert("RGB")
    luma, blue, red = source.convert("YCbCr").split()
    return Image.merge("YCbCr", (luma.point(table), blue, red)).convert("RGB")


def models_dir():
    """``models/`` beside the package, where the fetched archive lives."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


def archive_path():
    return os.path.join(models_dir(), ARCHIVE["filename"])


def verify_checksum(path, expected):
    """Raise unless *path* is exactly the published file."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        raise ValueError(
            "checksum mismatch for %s: expected %s, got %s"
            % (os.path.basename(path), expected, actual)
        )
    return actual


def ensure_archive(log_fn=None):
    """The local path to the model set, fetching it once if need be.

    The author publishes the seven heights as one archive, so it is taken whole
    -- 433 MB -- and read from where it lies rather than unpacked.
    """
    import urllib.request

    log = log_fn or _noop_log
    path = archive_path()
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        verify_checksum(path, ARCHIVE["sha256"])
        return path

    os.makedirs(models_dir(), exist_ok=True)
    log("UPSCALE: fetching %s, 433 MB (%s)" % (ARCHIVE["filename"], MODEL_CREDIT))
    partial = path + ".part"
    try:
        with urllib.request.urlopen(ARCHIVE["url"], timeout=120) as response:
            with open(partial, "wb") as handle:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    handle.write(chunk)
        verify_checksum(partial, ARCHIVE["sha256"])
        os.replace(partial, path)
    except Exception:
        try:
            os.remove(partial)
        except OSError:
            pass
        raise
    log("UPSCALE: %s ready" % ARCHIVE["filename"])
    return path


def ensure_model_file(spec, log_fn=None):
    """Return one verified loose model, downloading it when a URL is available."""
    import urllib.request

    log = log_fn or _noop_log
    path = os.path.join(models_dir(), spec["filename"])
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        verify_checksum(path, spec["sha256"])
        return path

    url = spec.get("url")
    if not url:
        raise FileNotFoundError(
            "%s is required for Exact manga upscale; place the published model "
            "in %s" % (spec["filename"], models_dir())
        )

    os.makedirs(models_dir(), exist_ok=True)
    log("UPSCALE: fetching %s" % spec["filename"])
    partial = path + ".part"
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            with open(partial, "wb") as handle:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    handle.write(chunk)
        verify_checksum(partial, spec["sha256"])
        os.replace(partial, path)
    except Exception:
        try:
            os.remove(partial)
        except OSError:
            pass
        raise
    log("UPSCALE: %s ready" % spec["filename"])
    return path


def uses_half_precision(device):
    """Whether inference on *device* should run at half precision."""
    return str(device) == "cuda"


def _cache_dat_attention_masks(model, device, max_bytes=288 * 1024 * 1024):
    """Reuse DAT's identical shifted-window masks across CUDA tiles/blocks.

    Spandrel constructs these masks on the CPU on every forward whose tile is
    larger than the training patch. The 384 px Manga Ora tile needs the same
    pair four times. Keep only one geometry per model, bounded to 288 MiB;
    narrow tiles replace it, and larger masks follow Spandrel's original path.
    """
    if str(device).split(":")[0] != "cuda":
        return 0
    import inspect
    import types
    import weakref

    try:
        from spandrel.architectures.DAT.__arch.DAT import Adaptive_Spatial_Attention
    except ImportError:
        return 0
    method = getattr(Adaptive_Spatial_Attention, "calculate_mask", None)
    try:
        # Private Spandrel APIs can change; an unfamiliar signature must keep
        # its own implementation rather than prevent a model from loading.
        if tuple(inspect.signature(method).parameters) != ("self", "H", "W", "dtype"):
            return 0
    except (TypeError, ValueError):
        return 0

    cached = {}
    cache_lock = threading.Lock()
    patched = 0
    patched_modules = []
    for module in model.modules():
        if (type(module) is not Adaptive_Spatial_Attention
                or getattr(module.calculate_mask, "__func__", None) is not method):
            continue
        def calculate_mask(self, H, W, dtype=None):
            target = self.qkv.weight.device
            if str(target).split(":")[0] != "cuda":
                return method(self, H, W, dtype=dtype)
            key = (H, W, dtype, target, tuple(self.split_size), tuple(self.shift_size))
            with cache_lock:
                if cached.get("key") == key:
                    return cached["masks"]
                cached.clear()
                masks = method(self, H, W, dtype=dtype)
                size = sum(mask.numel() * mask.element_size() for mask in masks)
                if size > max_bytes:
                    return masks
                # The forward already calls .to(x.device); returning masks on
                # that device makes those calls no-ops without changing values.
                try:
                    device_masks = tuple(mask.to(target) for mask in masks)
                except RuntimeError:
                    # A cache is optional: under memory pressure let the
                    # original forward transfer and release each mask in turn.
                    return masks
                cached.update(key=key, masks=device_masks)
                return device_masks

        module.calculate_mask = types.MethodType(calculate_mask, module)
        patched_modules.append((weakref.ref(module), calculate_mask))
        patched += 1
    if patched:
        def clear_masks():
            with cache_lock:
                cached.clear()
                for reference, replacement in patched_modules:
                    module = reference()
                    if module is not None and getattr(module.calculate_mask, "__func__", None) is replacement:
                        del module.calculate_mask
                patched_modules.clear()
        model._maic_clear_dat_masks = clear_masks
    return patched


def _torch_infer_factory(log_fn=None):
    """The real inference step: a model name -> (callable, scale)."""
    log = log_fn or _noop_log
    warned = []

    def factory(name):
        import numpy as np
        import torch

        from ._esrgan import build_generator, describe_state_dict

        with zipfile.ZipFile(ensure_archive(log_fn=log)) as archive:
            blob = archive.read(name)
        state = torch.load(io.BytesIO(blob), map_location="cpu", weights_only=True)
        for wrapper in ("params_ema", "params", "state_dict"):
            if isinstance(state, dict) and wrapper in state:
                state = state[wrapper]
        shape = describe_state_dict(state)
        model = build_generator(state)
        model.train(False)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu" and not warned:
            warned.append(True)
            log("UPSCALE: no CUDA device, upscaling will run on the CPU and be slow")
        model.to(device)
        log("UPSCALE: %s loaded on %s, scale %dx (%s)"
            % (name, device, shape["scale"], MODEL_CREDIT))

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
            if channels > 1:
                out = out.mean(dim=0)
            else:
                out = out.squeeze(0)
            return out.mul(255.0).cpu().numpy()

        def close():
            nonlocal model
            model = None
        infer.close = close
        return infer, int(shape["scale"])

    return factory


def _torch_exact_factory(log_fn=None):
    """Load the 2x Manga Ora model used by Exact upscale."""
    log = log_fn or _noop_log

    def factory():
        import numpy as np
        import torch
        from spandrel import ModelLoader

        ora_path = ensure_model_file(MANGA_ORA_MODEL, log_fn=log)

        ora_model = ModelLoader(device="cpu").load_from_file(ora_path)
        ora_model.eval()

        device = "cuda" if torch.cuda.is_available() else "cpu"
        ora_model.to(device)
        if device == "cpu":
            log("UPSCALE: no CUDA device, Exact upscaling will be slow")
        log("UPSCALE: Exact model loaded on %s (%s)" % (device, EXACT_MODEL_CREDIT))
        half = uses_half_precision(device)
        _cache_dat_attention_masks(ora_model.model, device)

        ora_channels = int(ora_model.input_channels)
        ora_scale = int(ora_model.scale)

        def ora_infer(tile):
            # DAT's split/window sizes are happiest on multiples of 32.  Full
            # tiles already are; this also makes narrow pages and final edge
            # tiles safe without changing their returned dimensions.
            height, width = tile.shape
            pad_h = (-height) % 32
            pad_w = (-width) % 32
            if pad_h or pad_w:
                pad_mode = "reflect" if min(height, width) > 1 else "edge"
                tile = np.pad(tile, ((0, pad_h), (0, pad_w)), mode=pad_mode)
            batch = torch.from_numpy(np.ascontiguousarray(tile)).to(device) / 255.0
            batch = batch.unsqueeze(0).unsqueeze(0)
            if ora_channels > 1:
                batch = batch.repeat(1, ora_channels, 1, 1)
            with torch.no_grad():
                if half:
                    with torch.autocast("cuda", dtype=torch.float16):
                        out = ora_model(batch)
                else:
                    out = ora_model(batch)
            out = out.float().clamp(0.0, 1.0).squeeze(0)
            out = out.mean(dim=0) if out.shape[0] > 1 else out.squeeze(0)
            return out[:height * ora_scale, :width * ora_scale].mul(255.0).cpu().numpy()

        def close():
            nonlocal ora_model
            if ora_model is not None:
                clear_masks = getattr(ora_model.model, "_maic_clear_dat_masks", None)
                if clear_masks is not None:
                    clear_masks()
                    del ora_model.model._maic_clear_dat_masks
                ora_model = None
        ora_infer.close = close
        return ora_infer, ora_scale

    return factory


class MangaUpscaler:
    """The pass, as one volume's worth of state.

    Held by the conversion for the length of a book: it decides per page which
    model to use, keeps each loaded once, counts what it did, and -- if a model
    cannot be loaded at all -- turns itself off so the rest of the volume
    converts without it rather than failing page by page.
    """

    def __init__(self, mode, infer_factory=None, exact_factory=None, log_fn=None,
                 white_point=WHITE_POINT, target_height=1920):
        self.mode = int(mode)
        self.enabled = self.mode in (MODE_FAST, MODE_EXACT)
        self.target_height = int(target_height)
        self.white_point = int(white_point)
        self._infer_factory = infer_factory or _torch_infer_factory(log_fn)
        self._exact_factory = exact_factory or _torch_exact_factory(log_fn)
        self._log = log_fn or _noop_log
        self._loaded = {}
        self._exact_loaded = None
        self._count = 0
        self._lock = threading.RLock()

    def model_for(self, size):
        """Which model a page of this size calls for, if any."""
        if not self.enabled:
            return None
        return choose_model(int(size[1]), self.mode, self.target_height)

    def close(self):
        """Wait for this volume's inference, then drop only its models."""
        with self._lock:
            self.enabled = False
            loaded = list(self._loaded.values())
            if self._exact_loaded is not None:
                loaded.append(self._exact_loaded)
            self._loaded.clear()
            self._exact_loaded = None
            for infer, _scale in loaded:
                close = getattr(infer, "close", None)
                if close is not None:
                    close()

    def apply(self, image, name):
        with self._lock:
            return self._apply(image, name)

    def _apply(self, image, name):
        """The upscaled page, or the page itself when the model could not run."""
        if not self.enabled or not name:
            return image

        try:
            if name == EXACT_PIPELINE:
                infer, scale = self._exact_models()
            else:
                infer, scale = self._model(name)
        except Exception as exc:
            self.enabled = False
            self._log("UPSCALE: disabled (%s)" % exc)
            return image

        try:
            tile = 384 if name == EXACT_PIPELINE else TILE_SIZE
            overlap = 24 if name == EXACT_PIPELINE else TILE_OVERLAP
            restored = restore_image(image, infer, scale=scale,
                                     tile=tile, overlap=overlap)
        except Exception as exc:
            self._log("UPSCALE: page left as it was (%s)" % exc)
            return image

        self._count += 1
        if name == EXACT_PIPELINE:
            return restored
        return apply_white_point(restored, self.white_point)

    def summary(self):
        """One line for the log, or ``None`` when the pass did nothing."""
        if not self._count:
            return None
        credit = EXACT_MODEL_CREDIT if self.mode == MODE_EXACT else MODEL_CREDIT
        label = "Exact" if self.mode == MODE_EXACT else "Fast"
        return "  [UPSCALE] %s: %d pages (%s)" % (label, self._count, credit)

    def _model(self, name):
        with self._lock:
            if name not in self._loaded:
                self._loaded[name] = self._infer_factory(name)
            return self._loaded[name]

    def _exact_models(self):
        with self._lock:
            if self._exact_loaded is None:
                self._exact_loaded = self._exact_factory()
            return self._exact_loaded
