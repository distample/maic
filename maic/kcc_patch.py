"""KCC monkey-patch helpers for nocrop/custom-crop/excluded handling."""

from __future__ import annotations

import os
import shutil
import sys
import threading

from PIL import Image

from ._image_pipeline import save_jpeg as _maic_save_jpeg
from .sevenzip import find_7z


def _noop_log(_msg: str) -> None:
    return


def _maic_clamp_crop_box(box, img_w: int, img_h: int):
    left, upper, right, lower = box
    return (
        min(0.1 * img_w, left),
        min(0.1 * img_h, upper),
        max(0.9 * img_w, right),
        max(0.9 * img_h, lower),
    )


def _maic_preserve_margin_box(box, img_w: int, img_h: int, pm_h: int, pm_v: int):
    rh = 1.0 - (pm_h / 100.0)
    rv = 1.0 - (pm_v / 100.0)
    left, upper, right, lower = box
    return (
        left * rh,
        upper * rv,
        right + (img_w - right) * (1.0 - rh),
        lower + (img_h - lower) * (1.0 - rv),
    )


def _maic_preview_crop_bounds(pil_img, *, mode, power, preserve_margin_h, preserve_margin_v, borders_color, cropping_minimum):
    if int(mode or 0) not in (1, 2):
        return None

    import math

    from kindlecomicconverter.page_number_crop_alg import (
        get_bbox_crop_margin,
        get_bbox_crop_margin_page_number,
    )

    from .kcc_scan import _detect_fill_color

    width, height = pil_img.size
    if width <= 1 or height <= 1:
        return None

    safe_power = max(0.1, min(10.0, float(power or 1.0)))
    safe_pm_h = max(0, min(100, int(preserve_margin_h or 0)))
    safe_pm_v = max(0, min(100, int(preserve_margin_v or 0)))
    safe_minimum = max(0.0, float(cropping_minimum or 0.0))
    explicit_fill = str(borders_color or "none").strip().lower()
    if explicit_fill not in ("none", "white", "black"):
        explicit_fill = "none"
    fill = _detect_fill_color(pil_img, explicit_fill)

    if int(mode or 0) == 2:
        bbox = get_bbox_crop_margin_page_number(pil_img, safe_power, fill)
    else:
        bbox = get_bbox_crop_margin(pil_img, safe_power, fill)
    if not bbox:
        return None

    crop_box = _maic_clamp_crop_box(
        (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
        width,
        height,
    )
    if safe_pm_h > 0 or safe_pm_v > 0:
        crop_box = _maic_preserve_margin_box(crop_box, width, height, safe_pm_h, safe_pm_v)

    box_area = max(0.0, (crop_box[2] - crop_box[0]) * (crop_box[3] - crop_box[1]))
    image_area = float(width * height) if width > 0 and height > 0 else 1.0
    if box_area / image_area < safe_minimum:
        return None

    top = max(0, min(height - 1, int(math.floor(crop_box[1]))))
    left = max(0, min(width - 1, int(math.floor(crop_box[0]))))
    bottom = max(top, min(height - 1, int(math.ceil(crop_box[3])) - 1))
    right = max(left, min(width - 1, int(math.ceil(crop_box[2])) - 1))
    if top <= 0 and left <= 0 and bottom >= height - 1 and right >= width - 1:
        return None
    if top >= bottom or left >= right:
        return None
    return top, bottom, left, right


_MAIC_ORIG_GETWORKFOLDER = None
_MAIC_PATCHED_GETWORKFOLDER = False
_MAIC_GETWORKFOLDER_PATCH_LOCK = threading.Lock()
_MAIC_ORIG_COMICPAGE_SAVE_WITH_CODEC = None
_MAIC_ORIG_COMICPAGE_SPLIT_CHECK = None
_MAIC_ORIG_COVER_SAVE_TO_EPUB = None
_MAIC_PATCHED_PRESERVE_MARGIN_HV = False
_EPUB_AUTHOR_SEPARATOR = "‚ "


def _maic_patched_save_with_codec(self, image, targetPath):
    global _MAIC_ORIG_COMICPAGE_SAVE_WITH_CODEC
    if getattr(self.opt, "forcepng", False):
        if _MAIC_ORIG_COMICPAGE_SAVE_WITH_CODEC is None:
            raise RuntimeError("maic original ComicPage.save_with_codec is not installed")
        return _MAIC_ORIG_COMICPAGE_SAVE_WITH_CODEC(self, image, targetPath)

    targetPath += ".jpg"
    try:
        quality = int(getattr(self.opt, "jpegquality", 90) or 90)
    except Exception:
        quality = 90

    is_kfx = bool(getattr(self.opt, "kfx", False)) or str(getattr(self.opt, "format", "") or "").upper() == "KFX"
    requested_mozjpeg = bool(getattr(self.opt, "mozjpeg", False))
    use_mozjpeg = requested_mozjpeg and not is_kfx
    save_image = image
    if is_kfx and getattr(image, "mode", "") != "RGB":
        # Kindle Previewer in this KFX path has been observed to keep JPEG restart
        # markers only on RGB page images. Normalizing grayscale pages here keeps
        # the KFX pipeline deterministic without touching upstream KCC sources.
        save_image = image.convert("RGB")

    if use_mozjpeg:
        try:
            import io
            import mozjpeg_lossless_optimization

            with io.BytesIO() as output:
                _maic_save_jpeg(save_image, output, quality)
                input_jpeg_bytes = output.getvalue()
            output_jpeg_bytes = mozjpeg_lossless_optimization.optimize(input_jpeg_bytes)
            with open(targetPath, "wb") as output_jpeg_file:
                output_jpeg_file.write(output_jpeg_bytes)
        except Exception:
            _maic_save_jpeg(save_image, targetPath, quality)
    else:
        _maic_save_jpeg(save_image, targetPath, quality)

    return targetPath


def _maic_patched_resize_image(self):
    from kindlecomicconverter import image as kcc_image

    if self.opt.norotate and self.targetPathOrder in ("-kcc-a", "-kcc-d") and not self.opt.kindle_scribe_azw3:
        if self.opt.kindle_azw3 and any(dim > 1920 for dim in self.image.size):
            self.image = kcc_image.ImageOps.contain(self.image, (1920, 1920), kcc_image.Image.Resampling.LANCZOS)
        elif self.image.size[0] > self.size[0] * 2 or self.image.size[1] > self.size[1]:
            self.image = kcc_image.ImageOps.contain(
                self.image, (self.size[0] * 2, self.size[1]), kcc_image.Image.Resampling.LANCZOS
            )
        return

    # The decision itself lives in _image_pipeline so the native KFX path,
    # which has no KCC to patch, sizes pages exactly the same way.
    from ._image_pipeline import resize_to_device

    background_source = None
    if self.targetPathOrder == "-kcc-x" and not bool(getattr(self.opt, "bordersColor", None)):
        reference_path = getattr(self.opt, "maic_crop_background_sources", {}).get(
            os.path.normcase(self.targetPathStart),
        )
        if reference_path:
            with kcc_image.Image.open(reference_path) as reference:
                background_source = reference.convert("RGB")
    self.image = resize_to_device(
        self.image,
        self.size,
        # KFX spread halves (S1/S2) keep their natural aspect; the sH style in
        # KFX post-processing wraps at the actual entity dimensions.
        spread_half=bool(self.opt.kfx and self.targetPathOrder in ("-kcc-b", "-kcc-c")),
        # "No padding" (KFX maic): no margin pixels baked in.  Whatever screen
        # area is left over is painted by the reader, and that is always white
        # -- KFX has no property that colours it.
        no_padding=bool(getattr(self.opt, "maic_kfx_no_padding", False)),
        pad_allowed=bool(
            (self.opt.kfx or self.opt.format in ("CBZ", "PDF")) and not self.opt.white_borders),
        fill=self.fill,
        edge_padding=not bool(getattr(self.opt, "bordersColor", None)),
        background_hint=getattr(self.opt, "maic_crop_backgrounds", {}).get(
            os.path.normcase(self.targetPathStart),
        ) if self.targetPathOrder == "-kcc-x" else None,
        background_source=background_source,
        upscale=bool(self.opt.upscale),
        stretch=bool(self.opt.stretch),
    )


def _maic_patched_cover_save_to_epub(self, target, tomeid, len_tomes=0):
    from PIL import ImageDraw

    try:
        save_image = self.image
        if tomeid != 0:
            save_image = self.image.copy()
            draw = ImageDraw.Draw(save_image)
            w, h = save_image.size
            draw.text(
                xy=(w / 2, h * 0.85),
                text=f"{tomeid}/{len_tomes}",
                anchor="ms",
                font_size=h // 7,
                fill=255,
                stroke_fill=0,
                stroke_width=25,
            )
        if bool(getattr(self.options, "kfx", False)) or str(getattr(self.options, "format", "") or "").upper() == "KFX":
            if getattr(save_image, "mode", "") != "RGB":
                save_image = save_image.convert("RGB")
            _maic_save_jpeg(save_image, target, getattr(self.options, "jpegquality", 90))
        else:
            if _MAIC_ORIG_COVER_SAVE_TO_EPUB is None:
                raise RuntimeError("maic original Cover.save_to_epub is not installed")
            return _MAIC_ORIG_COVER_SAVE_TO_EPUB(self, target, tomeid, len_tomes)
    except IOError:
        raise RuntimeError("Failed to save cover.")


def _maic_patched_split_check(self):
    """Pad landscape/portrait spreads to even dimensions before split."""
    global _MAIC_ORIG_COMICPAGE_SPLIT_CHECK
    if getattr(self.image, "mode", "") == "P":
        if "transparency" in getattr(self.image, "info", {}):
            rgba_image = self.image.convert("RGBA")
            background = Image.new("RGBA", rgba_image.size, (255, 255, 255, 255))
            background.alpha_composite(rgba_image)
            self.image = background.convert("RGB")
        else:
            self.image = self.image.convert("RGB")
    w, h = self.image.size
    if w > h and w % 2:
        # Duplicate rightmost pixel column to make width even.
        ext = Image.new(self.image.mode, (w + 1, h))
        ext.paste(self.image, (0, 0))
        ext.paste(self.image.crop((w - 1, 0, w, h)), (w, 0))
        self.image = ext
    elif h > w and h % 2:
        # Duplicate bottom pixel row to make height even.
        ext = Image.new(self.image.mode, (w, h + 1))
        ext.paste(self.image, (0, 0))
        ext.paste(self.image.crop((0, h - 1, w, h)), (0, h))
        self.image = ext
    return _MAIC_ORIG_COMICPAGE_SPLIT_CHECK(self)


def _install_preserve_margin_hv_patch():
    """Add --preservemarginh/--preservemarginv args and patch maybeCrop for separate H/V margins."""
    global _MAIC_PATCHED_PRESERVE_MARGIN_HV
    if _MAIC_PATCHED_PRESERVE_MARGIN_HV:
        return

    from kindlecomicconverter import comic2ebook as c2e
    from kindlecomicconverter import image as kcc_image

    # Inject KPW12 profile (Kindle Paperwhite 6" 12th gen, 1272x1696)
    if "KPW12" not in kcc_image.ProfileData.ProfilesKindlePDOC:
        kcc_image.ProfileData.ProfilesKindlePDOC["KPW12"] = (
            "Kindle Paperwhite 12 (6\")", (1272, 1696), kcc_image.ProfileData.Palette16, 1.0,
        )
        kcc_image.ProfileData.ProfilesKindle["KPW12"] = kcc_image.ProfileData.ProfilesKindlePDOC["KPW12"]
        kcc_image.ProfileData.Profiles["KPW12"] = kcc_image.ProfileData.ProfilesKindlePDOC["KPW12"]

    # Patch makeParser to add --preservemarginh / --preservemarginv when the
    # active KCC bundle does not already provide them.
    _orig_makeParser = c2e.makeParser

    def _patched_makeParser():
        psr = _orig_makeParser()
        existing = set(getattr(psr, "_option_string_actions", {}))

        def _add_arg(parser_or_group, option, dest, help_text=None):
            if option in existing:
                return
            kwargs = {"type": int, "dest": dest, "default": -1}
            if help_text is not None:
                kwargs["help"] = help_text
            parser_or_group.add_argument(option, **kwargs)
            existing.add(option)

        target = psr
        for grp in psr._action_groups:
            if grp.title and "PROCESSING" in grp.title.upper():
                target = grp
                break

        # Add H/V overrides (silently accepted; -1 means "use --preservemargin").
        _add_arg(
            target,
            "--preservemarginh",
            "preservemarginh",
            "Horizontal preserve margin override. -1 = use --preservemargin. [Default=-1]",
        )
        _add_arg(
            target,
            "--preservemarginv",
            "preservemarginv",
            "Vertical preserve margin override. -1 = use --preservemargin. [Default=-1]",
        )
        return psr

    c2e.makeParser = _patched_makeParser

    # Patch maybeCrop to use separate H/V ratios
    _orig_maybeCrop = kcc_image.ComicPage.maybeCrop

    def _patched_maybeCrop(self, box, minimum):
        pm_h = getattr(self.opt, "preservemarginh", -1)
        pm_v = getattr(self.opt, "preservemarginv", -1)
        pm = getattr(self.opt, "preservemargin", 0)
        if pm_h < 0:
            pm_h = pm
        if pm_v < 0:
            pm_v = pm
        # If both are zero or both equal the base value, use original
        if pm_h == pm and pm_v == pm:
            return _orig_maybeCrop(self, box, minimum)
        # Separate H/V logic
        from PIL import Image
        w, h = self.image.size
        left, upper, right, lower = box
        if pm_h or pm_v:
            ratio_h = 1 - pm_h / 100 if pm_h else 1.0
            ratio_v = 1 - pm_v / 100 if pm_v else 1.0
            box = (
                left * ratio_h,
                upper * ratio_v,
                right + (w - right) * (1 - ratio_h),
                lower + (h - lower) * (1 - ratio_v),
            )
        box_area = (box[2] - box[0]) * (box[3] - box[1])
        image_area = w * h
        if (box_area / image_area) >= minimum:
            self.image = self.image.crop(box)

    kcc_image.ComicPage.maybeCrop = _patched_maybeCrop
    _MAIC_PATCHED_PRESERVE_MARGIN_HV = True


def _install_comicpage_runtime_patches():
    from kindlecomicconverter import image as kcc_image

    global _MAIC_ORIG_COMICPAGE_SAVE_WITH_CODEC, _MAIC_ORIG_COMICPAGE_SPLIT_CHECK, _MAIC_ORIG_COVER_SAVE_TO_EPUB
    if kcc_image.ComicPage.save_with_codec is not _maic_patched_save_with_codec:
        _MAIC_ORIG_COMICPAGE_SAVE_WITH_CODEC = kcc_image.ComicPage.save_with_codec
    if kcc_image.ComicPageParser.splitCheck is not _maic_patched_split_check:
        _MAIC_ORIG_COMICPAGE_SPLIT_CHECK = kcc_image.ComicPageParser.splitCheck
    cover_save_to_epub = getattr(kcc_image.Cover, "save_to_epub", None)
    if cover_save_to_epub is not None and cover_save_to_epub is not _maic_patched_cover_save_to_epub:
        _MAIC_ORIG_COVER_SAVE_TO_EPUB = cover_save_to_epub

    kcc_image.ComicPage.resizeImage = _maic_patched_resize_image
    kcc_image.ComicPage.save_with_codec = _maic_patched_save_with_codec
    kcc_image.ComicPageParser.splitCheck = _maic_patched_split_check
    if cover_save_to_epub is not None:
        kcc_image.Cover.save_to_epub = _maic_patched_cover_save_to_epub
    return kcc_image


def _init_kcc_worker_runtime():
    _install_preserve_margin_hv_patch()
    _install_comicpage_runtime_patches()


def apply_getworkfolder_patch() -> None:
    """Patch KCC getWorkFolder to expand archive folders directly in KCC workspace."""
    global _MAIC_ORIG_GETWORKFOLDER, _MAIC_PATCHED_GETWORKFOLDER
    with _MAIC_GETWORKFOLDER_PATCH_LOCK:
        if _MAIC_PATCHED_GETWORKFOLDER:
            return

        from kindlecomicconverter import comic2ebook as c2e
        import shutil
        import zipfile
        import subprocess

        _MAIC_ORIG_GETWORKFOLDER = c2e.getWorkFolder

        arch_exts = {".zip", ".cbz", ".cbr", ".cb7", ".rar", ".7z"}
        img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif"}

        def _is_dir_of_archives(path: str) -> bool:
            try:
                for fn in os.listdir(path):
                    fp = os.path.join(path, fn)
                    if os.path.isfile(fp) and os.path.splitext(fn)[1].lower() in arch_exts:
                        return True
            except Exception:
                return False
            return False

        def _flatten_single_top_dir(extract_dir: str) -> None:
            try:
                entries = [entry for entry in os.listdir(extract_dir) if entry not in (".", "..")]
                if len(entries) != 1:
                    return
                only = os.path.join(extract_dir, entries[0])
                if not os.path.isdir(only):
                    return
                for name in os.listdir(only):
                    os.replace(os.path.join(only, name), os.path.join(extract_dir, name))
                try:
                    os.rmdir(only)
                except Exception:
                    pass
            except Exception:
                pass

        def _extract_archive(archive_path: str, out_dir: str) -> None:
            ext = os.path.splitext(archive_path)[1].lower()
            os.makedirs(out_dir, exist_ok=True)
            if ext in (".zip", ".cbz"):
                with zipfile.ZipFile(archive_path, "r") as zf:
                    zf.extractall(out_dir)
                _flatten_single_top_dir(out_dir)
                return

            seven_zip = find_7z()
            if not seven_zip:
                raise UserWarning("7z tool not found (required for RAR/7Z/CBR/CB7 sources).")
            args = [seven_zip, "x", "-y", "-bd", f"-o{out_dir}", archive_path]
            if sys.platform == "win32":
                proc = subprocess.run(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    creationflags=0x08000000,
                )
            else:
                proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if proc.returncode != 0:
                raise UserWarning(f"Failed to extract archive: {os.path.basename(archive_path)}")
            _flatten_single_top_dir(out_dir)

        def _patched_getworkfolder(afile, workdir=None):
            if not os.path.isdir(afile) or not _is_dir_of_archives(afile):
                return _MAIC_ORIG_GETWORKFOLDER(afile, workdir)

            if not workdir:
                from tempfile import mkdtemp

                workdir = mkdtemp("", "KCC-")
                full_path = os.path.join(workdir, "OEBPS", "Images")
            else:
                full_path = workdir

            os.makedirs(full_path, exist_ok=True)

            archives = []
            for fn in os.listdir(afile):
                fp = os.path.join(afile, fn)
                if os.path.isfile(fp) and os.path.splitext(fn)[1].lower() in arch_exts:
                    archives.append(fn)
            archives.sort(key=c2e.OS_SORT_KEY)

            for fn in archives:
                fp = os.path.join(afile, fn)
                stem = os.path.splitext(fn)[0]
                out_dir = os.path.join(full_path, stem)
                _extract_archive(fp, out_dir)

            for root, dirs, files in os.walk(afile):
                dirs.sort(key=c2e.OS_SORT_KEY)
                files.sort(key=c2e.OS_SORT_KEY)
                for fn in files:
                    fp = os.path.join(root, fn)
                    ext = os.path.splitext(fn)[1].lower()
                    if ext not in img_exts:
                        continue
                    rel = os.path.relpath(fp, afile)
                    dst = os.path.join(full_path, rel)
                    try:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(fp, dst)
                    except Exception:
                        pass

            try:
                c2e.sanitizePermissions(full_path)
            except Exception:
                pass
            return workdir

        c2e.getWorkFolder = _patched_getworkfolder
        _MAIC_PATCHED_GETWORKFOLDER = True


def apply_nocrop_patch(
    nocrop_files,
    watermark_match_files=None,
    custom_crops=None,
    custom_splits=None,
    excluded_files=None,
    edit_ops=None,
    extra_margin=None,
    convert_log=None,
    stop_requested_fn=None,
    kindle_doc_type="auto",
    auto_balance_margins=False,
    auto_balance_margin_px=0,
    auto_balance_margin_unit="px",
    auto_balance_margin_pct=0.0,
    match_spread_width=False,

    screen_margins=False,
    kfx_no_padding=False,
    cropping_mode=0,
    cropping_power=1.0,
    preserve_margin_h=0,
    preserve_margin_v=0,
    borders_color="none",
    webtoon=False,
    no_processing=False,
    cropping_minimum=0.0,
    maic_crop=False,
    maic_margin_pct=0.6,
    maic_watermarks=False,
    maic_page_numbers=False,
    cleanup_method="lama",
    cleanup_padding=2,
    page_number_scope="",

):
    """Patch KCC sanitize/img processing and optional post-KCC margin balancing."""
    # NOTE: internal processing detail.
    # NOTE: internal processing detail.
    _install_preserve_margin_hv_patch()
    if convert_log is None:
        convert_log = _noop_log

    def _is_stop_requested() -> bool:
        try:
            return bool(stop_requested_fn is not None and stop_requested_fn())
        except Exception:
            return False

    from kindlecomicconverter import comic2ebook as c2e
    from kindlecomicconverter import image as kcc_image
    from copy import copy as _copy

    def _relpath_variants(rel):
        norm = str(rel or "").replace("\\", "/").strip("/")
        variants = {norm.lower()}
        parts = [p for p in norm.split("/") if p]
        if len(parts) >= 3 and parts[0].casefold() == parts[1].casefold():
            variants.add("/".join([parts[0], *parts[2:]]).lower())
        return variants

    nocrop_norm = set()
    for nf in (nocrop_files or []):
        nocrop_norm.update(_relpath_variants(nf))

    watermark_match_norm = None
    if watermark_match_files is not None:
        watermark_match_norm = set()
        for rel in watermark_match_files:
            watermark_match_norm.update(_relpath_variants(rel))

    excluded_norm = set()
    for ef in (excluded_files or []):
        excluded_norm.update(_relpath_variants(ef))

    custom_crops = custom_crops or {}
    cc_norm = {}
    for rel, bounds in custom_crops.items():
        for key in _relpath_variants(rel):
            cc_norm[key] = bounds

    custom_splits = custom_splits or {}
    cs_norm = {}
    for rel, split_cfg in custom_splits.items():
        if isinstance(split_cfg, dict):
            for key in _relpath_variants(rel):
                cs_norm[key] = split_cfg

    edit_ops = edit_ops or {}
    eo_norm: dict[str, list] = {}
    for rel, ops in edit_ops.items():
        if isinstance(ops, list) and ops:
            for key in _relpath_variants(rel):
                eo_norm[key] = ops

    extra_margin = extra_margin or {}
    em_norm: dict[str, dict] = {}
    for rel, margins in extra_margin.items():
        if isinstance(margins, dict) and any(margins.get(s, 0) for s in ("top", "bottom", "left", "right")):
            for key in _relpath_variants(rel):
                em_norm[key] = margins

    # NOTE: internal processing detail.
    nocrop_kcc_names = set()
    watermark_kcc_names = None if watermark_match_norm is None else set()
    customcrop_kcc_map = {}  # kcc_name.lower() -> bounds
    customsplit_kcc_map = {}  # kcc_name.lower() -> split config
    editops_kcc_map: dict[str, list] = {}  # kcc_name.lower() -> ops list
    extramargin_kcc_map: dict[str, dict] = {}  # kcc_name.lower() -> margins
    deferred_cover_tmp_dirs: list[str] = []
    crop_background_tmp_dirs: list[str] = []

    # NOTE: internal processing detail.
    _orig_sanitize = c2e.sanitizeTree

    def _patched_sanitizeTree(filetree, prefix='kcc'):
        nonlocal nocrop_kcc_names, watermark_kcc_names, customcrop_kcc_map, customsplit_kcc_map, editops_kcc_map, extramargin_kcc_map
        nocrop_kcc_names = set()
        watermark_kcc_names = None if watermark_match_norm is None else set()
        customcrop_kcc_map = {}
        customsplit_kcc_map = {}
        editops_kcc_map = {}
        extramargin_kcc_map = {}
        nonlocal deferred_cover_tmp_dirs
        deferred = {}
        deferred_tmp_dir = None
        fmt = str(getattr(c2e.options, "format", "") or "").strip().upper()
        is_mobi = fmt.startswith("MOBI")

        # Special step: detach root cover/credits before sanitize, then place them explicitly.
        # MOBI keeps root cover untouched so KCC can use its native first-page cover handling.
        try:
            from tempfile import mkdtemp as _mkdtemp
            root_entries = []
            for n in os.listdir(filetree):
                fp = os.path.join(filetree, n)
                if os.path.isfile(fp):
                    root_entries.append(n)
            root_entries.sort(key=c2e.OS_SORT_KEY)
            for n in root_entries:
                stem, ext = os.path.splitext(n)
                if ext.lower() not in {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff'}:
                    continue
                stem_l = stem.lower()
                rel_l = n.replace("\\", "/").lower()
                if rel_l in excluded_norm:
                    continue
                kind = None
                if stem_l == "cover" and not is_mobi and "cover" not in deferred:
                    kind = "cover"
                elif stem_l in ("credits", "credit") and "credits" not in deferred:
                    kind = "credits"
                if not kind:
                    continue
                if deferred_tmp_dir is None:
                    deferred_tmp_dir = _mkdtemp(prefix="maic_defer_")
                src = os.path.join(filetree, n)
                tmp_name = f"{kind}{ext.lower()}"
                dst_tmp = os.path.join(deferred_tmp_dir, tmp_name)
                os.replace(src, dst_tmp)
                deferred[kind] = {"tmp": dst_tmp, "ext": ext.lower()}
        except Exception as e:
            convert_log(f"  [WARN] Root cover/credits defer failed: {e}")

        # NOTE: internal processing detail.
# NOTE: internal processing detail.
        all_ordered = []
        try:
            from kindlecomicconverter.shared import getImageFileName
            for root0, dirs0, files0 in os.walk(filetree):
                files0.sort(key=c2e.OS_SORT_KEY)
                rel0 = os.path.relpath(root0, filetree).replace("\\","/")
                if rel0 == '.': rel0 = ''
                for n0 in files0:
                    _, ext0 = getImageFileName(n0)
                    if ext0:  # image
                        all_ordered.append(os.path.join(rel0, n0).lstrip("/").replace("\\","/").lower())
                dirs0.sort(key=c2e.OS_SORT_KEY)
        except Exception:
            all_ordered = []

        if excluded_norm:
            from ._image_pipeline import apply_exclusions

            apply_exclusions(filetree, excluded_norm, log_fn=convert_log)

        # NOTE: internal processing detail.
        # NOTE: internal processing detail.
        from kindlecomicconverter.shared import getImageFileName
        page = 1
        # NOTE: internal processing detail.
        chapter_first_kcc = {}  # dir_rel_lower -> filelist_idx
        rel_to_filelist_idx = {}  # orig_rel_lower -> filelist_idx (pre-split)
        rel_to_kcc_stem = {}  # orig_rel_lower -> kcc-NNNN (pre-split stem)
        idx_to_kcc_stem = {}  # filelist_idx -> kcc-NNNN
        # NOTE: internal processing detail.
        # NOTE: internal processing detail.
        # filelist index = page - 1 (0-based)
        # NOTE: internal processing detail.
        # NOTE: internal processing detail.
        for root, dirs, files in os.walk(filetree):
            files.sort(key=c2e.OS_SORT_KEY)
            rel_dir = os.path.relpath(root, filetree).replace("\\", "/")
            if rel_dir == '.':
                rel_dir = ''
            first_in_dir = True
            for name in files:
                _, ext = getImageFileName(name)
                orig_rel = os.path.relpath(os.path.join(root, name), filetree).replace("\\", "/")
                kcc_name = f'{prefix}-{page:04}{ext}'
                kcc_stem = os.path.splitext(kcc_name)[0].lower()
                orig_lower = orig_rel.lower()
                # NOTE: internal processing detail.
                filelist_idx = page - 1
                rel_to_filelist_idx[orig_lower] = filelist_idx
                rel_to_kcc_stem[orig_lower] = kcc_stem
                idx_to_kcc_stem[filelist_idx] = kcc_stem
                if orig_lower in nocrop_norm:
                    nocrop_kcc_names.add(kcc_name.lower())
                    convert_log(f"  [NOCROP] NoCrop: {orig_rel} -> {kcc_name}")
                if watermark_match_norm is not None and orig_lower in watermark_match_norm:
                    watermark_kcc_names.add(kcc_name.lower())
                if orig_lower in cc_norm:
                    customcrop_kcc_map[kcc_name.lower()] = cc_norm[orig_lower]
                    nocrop_kcc_names.add(kcc_name.lower())
                    convert_log(f"  [CROP] Custom crop: {orig_rel} -> {kcc_name}")
                if orig_lower in cs_norm:
                    customsplit_kcc_map[kcc_name.lower()] = cs_norm[orig_lower]
                    nocrop_kcc_names.add(kcc_name.lower())
                    convert_log(f"  [SPLIT] Custom split: {orig_rel} -> {kcc_name}")
                if orig_lower in eo_norm:
                    editops_kcc_map[kcc_name.lower()] = eo_norm[orig_lower]
                if orig_lower in em_norm:
                    extramargin_kcc_map[kcc_name.lower()] = em_norm[orig_lower]
                # NOTE: internal processing detail.
                # NOTE: internal processing detail.
                if first_in_dir and rel_dir and filelist_idx >= 0 and not name.startswith('000_cover'):
                    chapter_first_kcc[rel_dir.lower()] = filelist_idx
                    first_in_dir = False
                page += 1
            dirs.sort(key=c2e.OS_SORT_KEY)

        if nocrop_kcc_names:
            convert_log(f"  [NOCROP] NoCrop mapped: {len(nocrop_kcc_names)} kcc-files")
        if customcrop_kcc_map:
            convert_log(f"  [CROP] Custom crop mapped: {len(customcrop_kcc_map)} kcc-files")
        if customsplit_kcc_map:
            convert_log(f"  [SPLIT] Custom split mapped: {len(customsplit_kcc_map)} kcc-files")
        if editops_kcc_map:
            convert_log(f"  [EDIT] Edit ops mapped: {len(editops_kcc_map)} kcc-files")
        if extramargin_kcc_map:
            convert_log(f"  [MARGIN] Extra margin mapped: {len(extramargin_kcc_map)} kcc-files")

        # NOTE: internal processing detail.
        # NOTE: internal processing detail.
        anchor_bms = []
        try:
            # Prefer sidecar placed in filetree root (tmp) if present
            candidates = [f for f in os.listdir(filetree) if f.lower().endswith('.sidecar.json')]
            sc_path = None
            if candidates:
                # prefer matching folder name
                folder_base = os.path.basename(filetree.rstrip('/\\')).lower()
                for c in candidates:
                    if c.lower().startswith(folder_base + '.'):
                        sc_path = os.path.join(filetree, c)
                        break
                if sc_path is None:
                    sc_path = os.path.join(filetree, candidates[0])
            if sc_path and os.path.isfile(sc_path):
                import json as _json
                with open(sc_path, 'r', encoding='utf-8') as f:
                    sc = _json.load(f) or {}
                if isinstance(sc, dict):
                    anchor_bms = sc.get('bookmarks', sc.get('bookmarkAnchors', [])) or []
            else:
                env_sc = os.environ.get('MAIC_SIDECAR_PATH','')
                if env_sc and os.path.isfile(env_sc):
                    import json as _json
                    with open(env_sc,'r',encoding='utf-8') as f:
                        sc = _json.load(f) or {}
                    if isinstance(sc, dict):
                        anchor_bms = sc.get('bookmarks', sc.get('bookmarkAnchors', [])) or []
        except Exception:
            anchor_bms = []

        if hasattr(c2e, 'options') and anchor_bms:
            # anchor_bms: [{"relPath": "...", "name": "..."}]
            mapped = []
            pos_map = {}
            if all_ordered:
                for i0, rp0 in enumerate(all_ordered):
                    if rp0 not in pos_map:
                        pos_map[rp0] = i0

            def _fallback_next(rel_lower):
                if rel_lower in rel_to_filelist_idx:
                    return rel_to_filelist_idx[rel_lower]
                if not all_ordered:
                    return None
                start_i = pos_map.get(rel_lower, None)
                if start_i is None:
                    return None
                rel_dir = os.path.dirname(rel_lower).replace("\\", "/").strip("/")
                for j in range(start_i + 1, len(all_ordered)):
                    rp = all_ordered[j]
                    rp_dir = os.path.dirname(rp).replace("\\", "/").strip("/")
                    if rp_dir != rel_dir:
                        continue
                    if rp in rel_to_filelist_idx:
                        return rel_to_filelist_idx[rp]
                return None

            for bm in anchor_bms:
                try:
                    rp = (bm.get('relPath') or bm.get('anchor_relpath') or bm.get('anchorRelPath') or '').replace('\\', '/').lstrip('/')
                    name = (bm.get('name') or bm.get('Bookmark') or bm.get('title') or '').strip()
                    if not rp or not name:
                        continue
                    rp_l = rp.lower()
                    idx = rel_to_filelist_idx.get(rp_l)
                    if idx is None:
                        idx = _fallback_next(rp_l)
                    if idx is None:
                        convert_log(f"  [TOC] Skip '{name}': anchor not found (excluded or missing): {rp}")
                        continue
                    exp_dir = os.path.dirname(rp).replace('\\','/').strip('/').lower()
                    stem = rel_to_kcc_stem.get(rp_l) or idx_to_kcc_stem.get(idx)
                    mapped.append((idx, name, exp_dir, stem))
                except Exception:
                    continue

            mapped.sort(key=lambda x: x[0])
            # Keep all explicit anchors (including multiple bookmarks inside one chapter folder).
            uniq = []
            seen = set()
            for idx, nm, exp_dir, stem in mapped:
                k = (int(idx), str(nm), str(exp_dir), str(stem or ""))
                if k in seen:
                    continue
                seen.add(k)
                uniq.append((int(idx), str(nm), str(exp_dir), str(stem or "")))
            dedup = [(v[0], v[1]) for v in uniq]
            maic_dirs = [v[2] for v in uniq]
            maic_stems = [v[3] for v in uniq]

            if dedup:
                c2e.options.comicinfo_chapters = dedup
                c2e.options.maic_chapter_dirs = maic_dirs
                c2e.options.maic_anchor_stems = maic_stems
                c2e.options.maic_anchor_mode = True
                convert_log(f"  [TOC] Anchors mapped: {len(dedup)} chapters -> {dedup[:3]}{'...' if len(dedup)>3 else ''}")
            else:
                c2e.options.maic_anchor_stems = []
                c2e.options.maic_anchor_mode = False
                convert_log(f"  [TOC] Anchors present but nothing mapped (all anchors excluded?)")
        else:
            try:
                c2e.options.maic_anchor_stems = []
                c2e.options.maic_anchor_mode = False
            except Exception:
                pass
            convert_log(f"  [TOC] No bookmark anchors in sidecar; keeping KCC ComicInfo mapping")


        sanitize_ret = _orig_sanitize(filetree, prefix)

        # KCC sanitizeTree slugifies folder names; remap expected chapter dirs to slug form
        # so buildEPUB TOC boundary fix can match final OEBPS/Images paths.
        try:
            chapter_names = None
            if isinstance(sanitize_ret, tuple) and sanitize_ret:
                chapter_names = sanitize_ret[0]
            if isinstance(chapter_names, dict):
                exp_dirs = list(getattr(c2e.options, "maic_chapter_dirs", []) or [])
                if exp_dirs:
                    # chapter_names: {slugified_dir_name: original_dir_name}
                    orig_to_slug = {}
                    for slug_name, orig_name in chapter_names.items():
                        o = str(orig_name or "").replace("\\", "/").strip("/").lower()
                        s = str(slug_name or "").replace("\\", "/").strip("/").lower()
                        if o and s and o not in orig_to_slug:
                            orig_to_slug[o] = s

                    if orig_to_slug:
                        remapped = []
                        changed = 0
                        for d in exp_dirs:
                            d_norm = str(d or "").replace("\\", "/").strip("/").lower()
                            if not d_norm:
                                remapped.append(d_norm)
                                continue

                            # Most cases are single-level chapter folders.
                            mapped = orig_to_slug.get(d_norm)
                            # Fallback for nested paths: remap path segments where possible.
                            if mapped is None and "/" in d_norm:
                                parts = [orig_to_slug.get(p, p) for p in d_norm.split("/")]
                                mapped = "/".join(parts)
                            if mapped is None:
                                mapped = d_norm
                            if mapped != d_norm:
                                changed += 1
                            remapped.append(mapped)

                        c2e.options.maic_chapter_dirs = remapped
                        if changed:
                            convert_log(f"  [TOC] Expected chapter dirs remapped to slug names: {changed}/{len(remapped)}")
        except Exception as e:
            convert_log(f"  [WARN] TOC dir remap after sanitize failed: {e}")

        # Reinsert deferred root images explicitly: MOBI cover at start, credits at end.
        # KFX/EPUB keep root cover metadata-only so existing reading order stays stable.
        explicit_cover_path = None
        try:
            if deferred:
                chapter_dirs_abs = []
                # Prefer logical chapter order captured from sidecar/bookmarks.
                # Natural sort may place "7.5" before "7", which breaks credits placement.
                exp_dirs = list(getattr(c2e.options, "maic_chapter_dirs", []) or [])
                for d in exp_dirs:
                    d_norm = str(d or "").replace("\\", "/").strip("/")
                    if not d_norm:
                        continue
                    abs_d = os.path.join(filetree, d_norm.replace("/", os.sep))
                    if os.path.isdir(abs_d) and abs_d not in chapter_dirs_abs:
                        chapter_dirs_abs.append(abs_d)
                if not chapter_dirs_abs:
                    for r0, d0, _ in os.walk(filetree):
                        d0.sort(key=c2e.OS_SORT_KEY)
                        rel0 = os.path.relpath(r0, filetree).replace("\\", "/")
                        if rel0 != ".":
                            chapter_dirs_abs.append(r0)
                first_dir = chapter_dirs_abs[0] if chapter_dirs_abs else filetree
                last_dir = chapter_dirs_abs[-1] if chapter_dirs_abs else filetree

                keep_cover_metadata_only = bool(deferred.get("cover"))
                if keep_cover_metadata_only:
                    explicit_cover_path = deferred["cover"]["tmp"]
                    if deferred_tmp_dir and deferred_tmp_dir not in deferred_cover_tmp_dirs:
                        deferred_cover_tmp_dirs.append(deferred_tmp_dir)
                    convert_log("  [TOC] Root cover kept for metadata only (not inserted as first page)")

                if deferred.get("credits"):
                    extc = deferred["credits"]["ext"]
                    credits_dst = os.path.join(last_dir, f"zzz_credits{extc}")
                    os.replace(deferred["credits"]["tmp"], credits_dst)
                    credits_keys = {f"credits{extc}", f"credit{extc}", "credits.png", "credit.png"}
                    if any(key in nocrop_norm for key in credits_keys):
                        nocrop_kcc_names.add(os.path.basename(credits_dst).lower())
                        convert_log(f"  [NOCROP] NoCrop: credits.png -> {os.path.basename(credits_dst)}")

                if deferred_tmp_dir and os.path.isdir(deferred_tmp_dir) and not keep_cover_metadata_only:
                    try:
                        os.rmdir(deferred_tmp_dir)
                    except Exception:
                        pass
        except Exception as e:
            convert_log(f"  [WARN] Deferred cover/credits reinsertion failed: {e}")

        # If we inserted explicit cover, force KCC to use it as ebook cover.
        try:
            if explicit_cover_path and isinstance(sanitize_ret, tuple) and len(sanitize_ret) >= 2:
                sanitize_ret = (sanitize_ret[0], explicit_cover_path)
                convert_log("  [TOC] Cover path overridden for KCC cover metadata")
        except Exception as e:
            convert_log(f"  [WARN] Cover path override failed: {e}")

        return sanitize_ret

    # NOTE: internal processing detail.
    _orig_imgDir = c2e.imgDirectoryProcessing
    _orig_resizeImage = kcc_image.ComicPage.resizeImage
    _orig_save_with_codec = kcc_image.ComicPage.save_with_codec
    _orig_cover_save_to_epub = getattr(kcc_image.Cover, "save_to_epub", None)
    _install_comicpage_runtime_patches()

    def _patched_imgDirProc(path, job_progress=''):
        from multiprocessing import Pool
        from time import perf_counter

        # Options travel to KCC's workers; keep the verified pre-crop shade
        # there rather than depending on metadata surviving image re-encoding.
        c2e.options.maic_crop_backgrounds = {}
        c2e.options.maic_crop_background_sources = {}
        crop_background_dir = None

        setattr(c2e.options, "maic_kindle_doc_type", str(kindle_doc_type or "auto").strip().upper())
        setattr(c2e.options, "maic_kfx_no_padding", bool(kfx_no_padding))
        is_kfx = str(getattr(c2e.options, "format", "") or "").strip().upper() == "KFX"
        setattr(c2e.options, "maic_nosplit", is_kfx)
        if is_kfx and bool(getattr(c2e.options, "mozjpeg", False)):
            convert_log("  [JPEG] KFX disables mozjpeg to preserve restart markers")
            c2e.options.mozjpeg = False

        # Apply edit-ops FIRST (coordinates are in original image space, before any crop)
        if editops_kcc_map:
            from PIL import Image as _PILImage, ImageDraw as _PILDraw
            edit_count = 0
            for dirpath, _, filenames in os.walk(path):
                if _is_stop_requested():
                    raise UserWarning("Conversion interrupted.")
                for afile in filenames:
                    if afile.lower() in editops_kcc_map:
                        ops = editops_kcc_map[afile.lower()]
                        fp = os.path.join(dirpath, afile)
                        try:
                            pil_img = _PILImage.open(fp)
                            draw = _PILDraw.Draw(pil_img)
                            for op in ops:
                                color = op.get("color", "#fff")
                                if op.get("type") == "rect":
                                    x, y = int(op.get("x", 0)), int(op.get("y", 0))
                                    w, h_val = int(op.get("w", 0)), int(op.get("h", 0))
                                    draw.rectangle([x, y, x + w, y + h_val], fill=color)
                                elif op.get("type") == "brush":
                                    pts = op.get("points", [])
                                    sz = int(op.get("size", 20))
                                    if len(pts) == 1:
                                        cx, cy = int(pts[0][0]), int(pts[0][1])
                                        r = sz // 2
                                        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
                                    elif len(pts) > 1:
                                        for i in range(len(pts) - 1):
                                            x1, y1 = int(pts[i][0]), int(pts[i][1])
                                            x2, y2 = int(pts[i + 1][0]), int(pts[i + 1][1])
                                            draw.line([(x1, y1), (x2, y2)], fill=color, width=sz)
                                        # Round caps at each point
                                        r = sz // 2
                                        for pt in pts:
                                            cx, cy = int(pt[0]), int(pt[1])
                                            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
                            pil_img.save(fp)
                            edit_count += 1
                        except Exception as e:
                            convert_log(f"  [!] Edit ops failed: {afile}: {e}")
            if edit_count:
                convert_log(f"  [EDIT] Edit ops applied: {edit_count} files")

        # Watermark cleanup is independent from cropping. It only fills a
        # taught match when the surrounding background is locally uniform;
        # matches over artwork remain untouched and are handled crop-only.
        if bool(maic_watermarks) and not bool(no_processing):
            from ._image_pipeline import apply_artifact_cleanup

            apply_artifact_cleanup(
                path,
                padding=cleanup_padding,
                only_names=watermark_kcc_names,
                stop_requested_fn=_is_stop_requested,
                log_fn=convert_log,
            )

        # Page-number cleanup is independent from cropping. Use the same local
        # digit detector and user-taught examples as the preview.
        # Cleanup precedes margin detection.
        if bool(maic_page_numbers) and not bool(no_processing):
            from ._image_pipeline import apply_page_number_cleanup

            apply_page_number_cleanup(
                path,
                method=str(cleanup_method or "lama"),
                padding=cleanup_padding,
                scope_path=page_number_scope,
                chapter_root=filetree,
                chapter_anchors=zip(getattr(c2e.options, "maic_chapter_dirs", []) or [],
                                    getattr(c2e.options, "maic_anchor_stems", []) or []),
                stop_requested_fn=_is_stop_requested,
                log_fn=convert_log,
            )

        # Apply the conservative maic crop before KCC splitting/cropping. NoCrop
        # and custom-crop pages stay in their original coordinate space.
        if bool(maic_crop) and not bool(webtoon) and not bool(no_processing):
            from ._image_pipeline import apply_margin_crop

            apply_margin_crop(
                path,
                margin_pct=maic_margin_pct,
                watermarks=bool(maic_watermarks),
                skip_names=set(nocrop_kcc_names) | set(customcrop_kcc_map),
                artifact_only_names=watermark_kcc_names,
                stop_requested_fn=_is_stop_requested,
                log_fn=convert_log,
            )

        # Apply custom crops in-place (after edit-ops, so edits use original coordinates)
        if customcrop_kcc_map:
            try:
                import cv2
            except ImportError:
                from .models import _ensure_imports
                _ensure_imports()
                import cv2
            cropped_count = 0
            for dirpath, _, filenames in os.walk(path):
                if _is_stop_requested():
                    raise UserWarning("Conversion interrupted.")
                for afile in filenames:
                    if _is_stop_requested():
                        raise UserWarning("Conversion interrupted.")
                    if afile.lower() in customcrop_kcc_map:
                        bounds = customcrop_kcc_map[afile.lower()]
                        fp = os.path.join(dirpath, afile)
                        try:
                            img = cv2.imread(fp)
                            if img is None:
                                continue
                            ih, iw = img.shape[:2]
                            if bounds.get("width", 0) != iw or bounds.get("height", 0) != ih:
                                continue
                            t2 = max(0, int(bounds.get("top", 0)))
                            b2 = min(ih - 1, int(bounds.get("bottom", ih - 1)))
                            l2 = max(0, int(bounds.get("left", 0)))
                            r2 = min(iw - 1, int(bounds.get("right", iw - 1)))
                            if t2 >= b2 or l2 >= r2:
                                continue
                            cropped = img[t2:b2+1, l2:r2+1]
                            from PIL import Image as _PILImage_crop
                            from ._image_pipeline import cropped_page_background, has_gradient_background

                            original_rgb = _PILImage_crop.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                            background = cropped_page_background(
                                original_rgb,
                                _PILImage_crop.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)),
                            )
                            cv2.imwrite(fp, cropped)
                            if background is not None:
                                c2e.options.maic_crop_backgrounds[
                                    os.path.normcase(os.path.splitext(fp)[0])
                                ] = background
                            if background is not None or has_gradient_background(original_rgb):
                                if crop_background_dir is None:
                                    from tempfile import mkdtemp
                                    crop_background_dir = mkdtemp(prefix="maic-crop-background-")
                                    crop_background_tmp_dirs.append(crop_background_dir)
                                reference_path = os.path.join(crop_background_dir, afile + ".png")
                                from PIL.PngImagePlugin import PngInfo
                                import json as _crop_reference_json
                                reference_info = PngInfo()
                                reference_info.add_text("maic_crop_reference_box", _crop_reference_json.dumps(
                                    [l2, t2, r2 + 1, b2 + 1],
                                ))
                                original_rgb.save(reference_path, format="PNG", pnginfo=reference_info)
                                c2e.options.maic_crop_background_sources[
                                    os.path.normcase(os.path.splitext(fp)[0])
                                ] = reference_path
                            cropped_count += 1
                        except Exception as e:
                            convert_log(f"  [!] Custom crop failed: {afile}: {e}")
            if cropped_count:
                convert_log(f"  [CROP] Custom crop applied: {cropped_count} files")

        # Apply extra-margin pre-KCC: preview/KCC crop -> add margin -> mark nocrop.
        if extramargin_kcc_map:
            try:
                import cv2
            except ImportError:
                from .models import _ensure_imports
                _ensure_imports()
                import cv2
            import numpy as np
            from PIL import Image as _PILImage_em
            em_count = 0
            em_crop_count = 0
            for dirpath, _, filenames in os.walk(path):
                if _is_stop_requested():
                    raise UserWarning("Conversion interrupted.")
                for afile in filenames:
                    afile_l = afile.lower()
                    if afile_l not in extramargin_kcc_map:
                        continue
                    margins = extramargin_kcc_map[afile_l]
                    fp = os.path.join(dirpath, afile)
                    try:
                        img = cv2.imread(fp)
                        if img is None:
                            continue
                        ih, iw = img.shape[:2]

                        if (
                            afile_l not in customcrop_kcc_map
                            and not bool(webtoon)
                            and not bool(no_processing)
                            and int(cropping_mode or 0) in (1, 2)
                        ):
                            try:
                                pil_img = _PILImage_em.open(fp).convert("RGB")
                                bounds = _maic_preview_crop_bounds(
                                    pil_img,
                                    mode=cropping_mode,
                                    power=cropping_power,
                                    preserve_margin_h=preserve_margin_h,
                                    preserve_margin_v=preserve_margin_v,
                                    borders_color=borders_color,
                                    cropping_minimum=cropping_minimum,
                                )
                                if bounds:
                                    t2, b2, l2, r2 = bounds
                                    img = img[t2:b2+1, l2:r2+1]
                                    ih, iw = img.shape[:2]
                                    em_crop_count += 1
                            except Exception as e:
                                convert_log(f"  [!] Extra margin preview crop failed: {afile}: {e}")

                        # Add margin
                        mT = int(margins.get("top", 0) or 0)
                        mB = int(margins.get("bottom", 0) or 0)
                        mL = int(margins.get("left", 0) or 0)
                        mR = int(margins.get("right", 0) or 0)
                        if mT or mB or mL or mR:
                            _mc = str(margins.get("color", "#ffffff") or "#ffffff")
                            if _mc.startswith("#") and len(_mc) == 4:
                                _mc = "#" + _mc[1]*2 + _mc[2]*2 + _mc[3]*2
                            try:
                                _cr, _cg, _cb = int(_mc[1:3], 16), int(_mc[3:5], 16), int(_mc[5:7], 16)
                            except (ValueError, IndexError):
                                _cr, _cg, _cb = 255, 255, 255
                            crop_key = os.path.normcase(os.path.splitext(fp)[0])
                            original_color = c2e.options.maic_crop_backgrounds.get(crop_key)
                            if original_color is None or max(abs(a - b) for a, b in zip(
                                original_color, (_cr, _cg, _cb),
                            )) > 8:
                                c2e.options.maic_crop_background_sources.pop(crop_key, None)
                            c2e.options.maic_crop_backgrounds[
                                os.path.normcase(os.path.splitext(fp)[0])
                            ] = (_cr, _cg, _cb)
                            fill = (_cb, _cg, _cr)  # cv2 uses BGR
                            new_h, new_w = ih + mT + mB, iw + mL + mR
                            canvas = np.full((new_h, new_w, 3), fill, dtype=np.uint8) if len(img.shape) == 3 else np.full((new_h, new_w), int(0.299*_cr + 0.587*_cg + 0.114*_cb), dtype=np.uint8)
                            canvas[mT:mT+ih, mL:mL+iw] = img
                            cv2.imwrite(fp, canvas)
                            em_count += 1
                            convert_log(f"  [MARGIN] Applied: {afile} crop={iw}x{ih} -> {new_w}x{new_h}, color={_mc}")

                        # Mark as nocrop so KCC doesn't remove the margin
                        nocrop_kcc_names.add(afile_l)
                    except Exception as e:
                        convert_log(f"  [!] Extra margin failed: {afile}: {e}")
            if em_count:
                convert_log(f"  [MARGIN] Extra margin applied: {em_count} files")
            if em_crop_count:
                convert_log(f"  [MARGIN] Preview crop before extra margin: {em_crop_count} files")

        # Apply custom split in-place before processing.
        if customsplit_kcc_map:
            try:
                import cv2
            except ImportError:
                from .models import _ensure_imports

                _ensure_imports()
                import cv2
            split_count = 0
            for dirpath, _, filenames in os.walk(path):
                if _is_stop_requested():
                    raise UserWarning("Conversion interrupted.")
                filenames.sort(key=c2e.OS_SORT_KEY)
                for afile in list(filenames):
                    if _is_stop_requested():
                        raise UserWarning("Conversion interrupted.")
                    cfg = customsplit_kcc_map.get(afile.lower())
                    if not cfg:
                        continue
                    fp = os.path.join(dirpath, afile)
                    try:
                        img = cv2.imread(fp)
                        if img is None:
                            continue
                        ih, iw = img.shape[:2]
                        splitter_mode = int(getattr(c2e.options, "splitter", 0) or 0)
                        if splitter_mode == 1 or bool(getattr(c2e.options, "webtoon", False)):
                            continue
                        profile_data = getattr(c2e.options, "profileData", ((0, 0), (iw, ih), None, 1.0))
                        try:
                            dstw, dsth = profile_data[1]
                            dstw, dsth = int(dstw), int(dsth)
                        except Exception:
                            dstw, dsth = iw, ih
                        orientation_mismatch = (iw > ih) != (dstw > dsth)
                        if not orientation_mismatch:
                            continue
                        axis = str(cfg.get("axis", "") or "").strip().lower()
                        if axis not in {"x", "y"}:
                            axis = "x" if iw >= ih else "y"

                        size_key = "width" if axis == "x" else "height"
                        total = iw if axis == "x" else ih
                        src_total = int(cfg.get(size_key, 0) or 0)
                        raw_split = cfg.get("split", total // 2)
                        split = int(raw_split) if isinstance(raw_split, (int, float)) else total // 2
                        if src_total > 0 and src_total != total:
                            split = int(round((float(split) / float(src_total)) * float(total)))
                        split = max(1, min(total - 1, split))

                        if axis == "x":
                            part_a = img[:, :split]
                            part_b = img[:, split:]
                        else:
                            part_a = img[:split, :]
                            part_b = img[split:, :]

                        # Mirror KCC split semantics:
                        # S1 follows reading order, S2 is the opposite page.
                        if bool(getattr(c2e.options, "righttoleft", False)):
                            s1_img = part_b
                            s2_img = part_a
                        else:
                            s1_img = part_a
                            s2_img = part_b

                        # Match KCC split order semantics:
                        # first page in reading order (S1) -> "-a", second page (S2) -> "-b".
                        # For split+rotate mode add rotated spread as well, respecting rotate_first order.
                        stem, ext = os.path.splitext(afile)
                        generated = []
                        if splitter_mode > 0:
                            rot_img = img
                            if not bool(getattr(c2e.options, "norotate", False)):
                                rot_img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                            rotate_name = f"{stem}-0r{ext}" if bool(getattr(c2e.options, "rotatefirst", False)) else f"{stem}-r{ext}"
                            generated.append((rotate_name, rot_img))
                        generated.append((f"{stem}-a{ext}", s1_img))
                        generated.append((f"{stem}-b{ext}", s2_img))

                        # If rotate-first is disabled, keep KCC-like order S1,S2,R.
                        if splitter_mode > 0 and not bool(getattr(c2e.options, "rotatefirst", False)):
                            generated = [generated[1], generated[2], generated[0]]

                        for out_name, out_img in generated:
                            out_path = os.path.join(dirpath, out_name)
                            if not cv2.imwrite(out_path, out_img):
                                raise RuntimeError(f"Failed writing {out_name}")

                        os.remove(fp)
                        for out_name, _ in generated:
                            nocrop_kcc_names.add(out_name.lower())
                        split_count += 1
                    except Exception as e:
                        convert_log(f"  [!] Custom split failed: {afile}: {e}")
            if split_count:
                convert_log(f"  [SPLIT] Custom split applied: {split_count} files")

        # Use bounded worker pool for image processing.
        worker_env = str(os.environ.get("MAIC_IMG_WORKERS", "") or "").strip()
        try:
            requested_workers = int(worker_env) if worker_env else 0
        except Exception:
            requested_workers = 0
        cpu_count = int(os.cpu_count() or 1)
        auto_workers = max(2, min(cpu_count, 8))
        worker_count = requested_workers if requested_workers > 0 else auto_workers

        c2e.workerPool = Pool(
            processes=worker_count,
            maxtasksperchild=100,
            initializer=_init_kcc_worker_runtime,
        )
        pool_mode = f"process-pool({worker_count})"
        convert_log(f"  [IMG] image-processing={pool_mode}")
        c2e.workerOutput = []
        c2e.options.imgMetadata = {}
        work = []
        pagenumber = 0
        matched = 0
        for dirpath, _, filenames in os.walk(path):
            if _is_stop_requested():
                raise UserWarning("Conversion interrupted.")
            filenames.sort(key=c2e.OS_SORT_KEY)
            for afile in filenames:
                if _is_stop_requested():
                    raise UserWarning("Conversion interrupted.")
                pagenumber += 1
                afile_l = afile.lower()
                fp = os.path.join(dirpath, afile)
                is_nocrop = afile_l in nocrop_kcc_names

                if is_nocrop:
                    file_opts = _copy(c2e.options)
                    file_opts.cropping = 0
                    file_opts.interpanelcrop = 0
                    work.append([afile, dirpath, file_opts])
                    matched += 1
                else:
                    work.append([afile, dirpath, c2e.options])

        if matched:
            convert_log(f"  [NOCROP] NoCrop matched: {matched}/{pagenumber}")

        _valign_map = {}  # {rel_path_lower: 'top' | 'bottom'} — pre-scanned vertical alignment

        def _detect_edge_margin_px(gray_img, from_left):
            import numpy as np

            h, w = gray_img.shape[:2]
            if h < 8 or w < 8:
                return 0
            edge_x = 0 if from_left else (w - 1)
            edge_col = gray_img[:, edge_x]
            edge_med = float(np.median(edge_col))
            # Only treat near-black/near-white edge as a true blank field.
            if not (edge_med <= 32.0 or edge_med >= 223.0):
                return 0
            max_scan = max(1, min(w // 2, w))
            margin = 0
            edge_ref = int(round(edge_med))
            for i in range(max_scan):
                x = i if from_left else (w - 1 - i)
                col = gray_img[:, x].astype(np.int16)
                diff = np.abs(col - edge_ref)
                near_ratio = float((diff <= 14).mean())
                if near_ratio >= 0.995:
                    margin += 1
                else:
                    break
            return margin

        def _detect_edge_margin_px_vertical(gray_img, from_top):
            """Detect blank margin rows from top or bottom edge."""
            import numpy as np

            h, w = gray_img.shape[:2]
            if h < 8 or w < 8:
                return 0
            edge_y = 0 if from_top else (h - 1)
            edge_row = gray_img[edge_y, :]
            edge_med = float(np.median(edge_row))
            if not (edge_med <= 32.0 or edge_med >= 223.0):
                return 0
            max_scan = max(1, min(h // 2, h))
            margin = 0
            edge_ref = int(round(edge_med))
            for i in range(max_scan):
                y = i if from_top else (h - 1 - i)
                row = gray_img[y, :].astype(np.int16)
                diff = np.abs(row - edge_ref)
                near_ratio = float((diff <= 14).mean())
                if near_ratio >= 0.995:
                    margin += 1
                else:
                    break
            return margin

        def _median_border_value(img_strip, channels):
            import numpy as np

            if channels == 1:
                return int(np.clip(np.median(img_strip), 0, 255))
            flat = img_strip.reshape(-1, channels)
            med = np.median(flat, axis=0)
            return tuple(int(np.clip(v, 0, 255)) for v in med.tolist())

        def _write_processed_image(fp, img, options):
            ext = os.path.splitext(fp)[1].lower()
            if ext not in {".jpg", ".jpeg", ".png", ".gif"}:
                return bool(cv2.imwrite(fp, img))
            try:
                from PIL import Image
            except Exception:
                return bool(cv2.imwrite(fp, img))

            try:
                if img.ndim == 2:
                    pil_img = Image.fromarray(img)
                else:
                    ch = int(img.shape[2]) if img.ndim == 3 else 1
                    if ch == 4:
                        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA))
                    elif ch == 3:
                        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                    else:
                        pil_img = Image.fromarray(img[:, :, 0])
            except Exception:
                return bool(cv2.imwrite(fp, img))

            should_save_jpeg = ext in {".jpg", ".jpeg"} or (
                ext == ".png"
                and bool(getattr(options, "mozjpeg", False))
                and not bool(getattr(options, "forcepng", False))
            )

            if should_save_jpeg:
                if pil_img.mode not in {"L", "RGB"}:
                    pil_img = pil_img.convert("RGB")
                try:
                    quality = int(getattr(options, "jpegquality", 90) or 90)
                except Exception:
                    quality = 90
                quality = max(1, min(100, quality))
                jpeg_save_kwargs = {"optimize": 1, "quality": quality, "restart_marker_rows": 32}

                def _save_jpeg(target):
                    try:
                        pil_img.save(target, "JPEG", **jpeg_save_kwargs)
                    except TypeError:
                        legacy_kwargs = dict(jpeg_save_kwargs)
                        legacy_kwargs.pop("restart_marker_rows", None)
                        pil_img.save(target, "JPEG", **legacy_kwargs)

                target_fp = fp
                if ext == ".png":
                    candidate_fp = os.path.splitext(fp)[0] + ".jpg"
                    if os.path.exists(candidate_fp):
                        return bool(cv2.imwrite(fp, img))
                    target_fp = candidate_fp

                if bool(getattr(options, "mozjpeg", False)):
                    try:
                        import io
                        import mozjpeg_lossless_optimization

                        with io.BytesIO() as output:
                            _save_jpeg(output)
                            input_jpeg_bytes = output.getvalue()
                        output_jpeg_bytes = mozjpeg_lossless_optimization.optimize(input_jpeg_bytes)
                        with open(target_fp, "wb") as output_jpeg_file:
                            output_jpeg_file.write(output_jpeg_bytes)
                        if target_fp != fp:
                            os.remove(fp)
                        return True
                    except Exception:
                        pass
                try:
                    _save_jpeg(target_fp)
                    if target_fp != fp:
                        os.remove(fp)
                    return True
                except Exception:
                    return bool(cv2.imwrite(fp, img))

            if ext == ".png":
                try:
                    pil_img.save(fp, "PNG", optimize=1)
                    return True
                except Exception:
                    return bool(cv2.imwrite(fp, img))

            # GIF output is used in some forcepng Kindle EPUB/MOBI paths.
            try:
                if pil_img.mode not in {"P", "L"}:
                    pil_img = pil_img.convert("P", palette=Image.ADAPTIVE)
                pil_img.save(fp, "GIF", optimize=1, interlace=False)
                return True
            except Exception:
                return bool(cv2.imwrite(fp, img))

        def _auto_balance_side_margins(
            root_path,
            target_margin_px=0,
            target_margin_unit="px",
            target_margin_pct=0.0,
            match_spread_width=False,
        ):
            try:
                import cv2
                import numpy as np
            except ImportError:
                from .models import _ensure_imports

                _ensure_imports()
                import cv2
                import numpy as np

            img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif"}
            changed = 0
            scanned = 0
            try:
                target_margin_px = int(target_margin_px or 0)
            except Exception:
                target_margin_px = 0
            target_margin_px = max(0, target_margin_px)
            unit = str(target_margin_unit or "px").strip().lower()
            if unit in {"%", "percent"}:
                unit = "pct"
            if unit not in {"px", "pct"}:
                unit = "px"
            try:
                target_margin_pct = float(target_margin_pct or 0.0)
            except Exception:
                target_margin_pct = 0.0
            target_margin_pct = max(0.0, min(100.0, target_margin_pct))
            manual_target_enabled = (target_margin_px > 0) or (unit == "pct" and target_margin_pct > 0.0)

            def _is_split_spread_page(filename: str) -> bool:
                stem = os.path.splitext(str(filename or ""))[0].lower()
                return (
                    ("-kcc-a" in stem)
                    or ("-kcc-b" in stem)
                    or ("-kcc-c" in stem)
                    or ("-kcc-d" in stem)
                )

            def _is_cover_image(dirpath: str, filename: str) -> bool:
                return os.path.normcase(os.path.abspath(dirpath)) == os.path.normcase(os.path.abspath(root_path)) and filename.lower() in ("cover.jpg", "cover.png", "cover.webp")

            # Match spread width: detect spread-half dimensions and pad singles to match.
            _spread_half_w = 0
            if match_spread_width:
                _spread_widths = []
                for _dp, _, _fns in os.walk(root_path):
                    for _fn in _fns:
                        # Only measure -kcc-b/-kcc-c (actual half-spread pages).
                        # -kcc-a/-kcc-d are rotated full spreads with device-height width.
                        _fn_lower = _fn.lower()
                        if not ("-kcc-b" in _fn_lower or "-kcc-c" in _fn_lower):
                            continue
                        _ext = os.path.splitext(_fn)[1].lower()
                        if _ext not in img_exts:
                            continue
                        _sp_img = cv2.imread(os.path.join(_dp, _fn), cv2.IMREAD_UNCHANGED)
                        if _sp_img is not None:
                            _spread_widths.append(int(_sp_img.shape[1]))
                if _spread_widths:
                    # Use most common spread-half width
                    from collections import Counter as _Ctr
                    _spread_half_w = _Ctr(_spread_widths).most_common(1)[0][0]

            for dirpath, _, filenames in os.walk(root_path):
                if _is_stop_requested():
                    raise UserWarning("Conversion interrupted.")
                for afile in filenames:
                    if _is_stop_requested():
                        raise UserWarning("Conversion interrupted.")
                    ext = os.path.splitext(afile)[1].lower()
                    if ext not in img_exts:
                        continue
                    # Skip KCC split-spread pages and cover image
                    if _is_split_spread_page(afile):
                        continue
                    if _is_cover_image(dirpath, afile):
                        continue
                    fp = os.path.join(dirpath, afile)
                    img = cv2.imread(fp, cv2.IMREAD_UNCHANGED)
                    if img is None:
                        continue
                    scanned += 1
                    if img.ndim == 2:
                        gray = img
                        channels = 1
                    else:
                        channels = int(img.shape[2]) if img.ndim == 3 else 1
                        if channels == 1:
                            gray = img[:, :, 0]
                        elif channels == 4:
                            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                        else:
                            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                    h, w = gray.shape[:2]
                    if h < 16 or w < 16:
                        continue
                    left_margin = _detect_edge_margin_px(gray, True)
                    right_margin = _detect_edge_margin_px(gray, False)

                    # Match spread width: adjust all single-page images to spread-half width.
                    # Narrower → pad sides; wider → resize + pad top/bottom.
                    if _spread_half_w > 0 and w != _spread_half_w:
                        content_w = max(1, int(w) - int(left_margin) - int(right_margin))
                        if content_w <= _spread_half_w:
                            # Narrow: strip margins, pad to target
                            total_pad = _spread_half_w - content_w
                            pad_l = int(total_pad // 2)
                            pad_r = int(total_pad - pad_l)
                            if left_margin >= right_margin and left_margin > 0:
                                strip = img[:, :max(1, int(left_margin))]
                            elif right_margin > 0:
                                strip = img[:, w - max(1, int(right_margin)):]
                            else:
                                strip = img[:, :1]
                            bv = _median_border_value(strip, channels)
                            x0 = int(left_margin)
                            x1 = int(w - right_margin)
                            if x1 > x0:
                                work = img[:, x0:x1]
                                padded = cv2.copyMakeBorder(
                                    work, 0, 0, pad_l, pad_r,
                                    cv2.BORDER_CONSTANT, value=bv
                                )
                                if _write_processed_image(fp, padded, c2e.options):
                                    changed += 1
                            continue
                        else:
                            # Wide: strip margins → resize to spread_half_w →
                            # pad top/bottom if needed to fill screen_h.
                            try:
                                _pd = getattr(c2e.options, "profileData", ((0, 0), (w, h), None, 1.0))
                                screen_h = int(_pd[1][1] or 0)
                            except Exception:
                                screen_h = 0
                            if screen_h <= 0:
                                screen_h = int(h)

                            # Detect and strip margins. Keep black side margins
                            # (likely intentional artwork); always strip vertical.
                            import numpy as np
                            top_m = _detect_edge_margin_px_vertical(gray, True)
                            bottom_m = _detect_edge_margin_px_vertical(gray, False)
                            lm = int(left_margin) if (left_margin > 0 and float(np.median(gray[:, 0])) > 32.0) else 0
                            rm = int(right_margin) if (right_margin > 0 and float(np.median(gray[:, w - 1])) > 32.0) else 0
                            x0 = lm
                            x1 = max(x0 + 1, int(w) - rm)
                            y0 = int(top_m)
                            y1 = max(y0 + 1, int(h) - int(bottom_m))
                            content = img[y0:y1, x0:x1]
                            ch, cw = content.shape[:2]

                            # Border color from stripped margins
                            if top_m >= bottom_m and top_m > 0:
                                strip = img[:max(1, int(top_m)), :]
                            elif bottom_m > 0:
                                strip = img[h - max(1, int(bottom_m)):, :]
                            elif left_margin >= right_margin and left_margin > 0:
                                strip = img[:, :max(1, int(left_margin))]
                            elif right_margin > 0:
                                strip = img[:, w - max(1, int(right_margin)):]
                            else:
                                strip = img[:1, :]
                            bv = _median_border_value(strip, channels)

                            # Resize content to target width
                            new_h = int(round(float(ch) * float(_spread_half_w) / float(cw)))
                            resized = cv2.resize(content, (_spread_half_w, new_h), interpolation=cv2.INTER_AREA)

                            if new_h >= screen_h:
                                if _write_processed_image(fp, resized, c2e.options):
                                    changed += 1
                                continue

                            # Pad top/bottom to fill screen height.
                            # Use original pre-strip margins to decide alignment:
                            # more margin on a side → content is away from that edge → pad that side.
                            vert_pad = screen_h - new_h
                            if top_m > 0 or bottom_m > 0:
                                if top_m > bottom_m:
                                    pad_top, pad_bottom = vert_pad, 0
                                elif bottom_m > top_m:
                                    pad_top, pad_bottom = 0, vert_pad
                                else:
                                    pad_top = vert_pad // 2
                                    pad_bottom = vert_pad - pad_top
                            else:
                                pad_top = vert_pad // 2
                                pad_bottom = vert_pad - pad_top
                            padded = cv2.copyMakeBorder(
                                resized, pad_top, pad_bottom, 0, 0,
                                cv2.BORDER_CONSTANT, value=bv
                            )
                            if _write_processed_image(fp, padded, c2e.options):
                                changed += 1
                            continue

                    # Manual mode:
                    # px  -> enforce a fixed, symmetric side margin width.
                    # pct -> enforce final total page width as a percentage of the
                    #        device/screen width by adjusting left/right margins only.
                    # Top/bottom stay unchanged in both cases.
                    if manual_target_enabled:
                        if unit == "pct":
                            try:
                                screen_w = int((getattr(c2e.options, "profileData", ((0, 0), (w, h), None, 1.0))[1])[0] or 0)
                            except Exception:
                                screen_w = 0
                            if screen_w <= 0:
                                screen_w = int(w)
                            desired_total_w = int(round(float(screen_w) * (target_margin_pct / 100.0)))
                            desired_total_w = max(1, min(desired_total_w, int(screen_w)))
                            content_w = max(1, int(w) - int(left_margin) - int(right_margin))
                            desired_total_w = max(content_w, desired_total_w)
                            desired_total_margin = max(0, desired_total_w - content_w)
                            desired_left = int(desired_total_margin // 2)
                            desired_right = int(desired_total_margin - desired_left)
                        else:
                            desired = int(target_margin_px)
                            desired = max(0, min(desired, max(0, (w // 2) - 1)))
                            if desired <= 0:
                                continue
                            if left_margin < 1 and right_margin < 1:
                                continue
                            desired_left = int(desired)
                            desired_right = int(desired)

                        crop_left = max(0, int(left_margin) - desired_left)
                        crop_right = max(0, int(right_margin) - desired_right)
                        if crop_left + crop_right >= (w - 2):
                            continue

                        x0 = int(crop_left)
                        x1 = int(w - crop_right)
                        if x1 <= x0:
                            continue
                        work_img = img[:, x0:x1]

                        if left_margin >= right_margin and left_margin > 0:
                            strip = img[:, :max(1, int(left_margin))]
                        elif right_margin > 0:
                            strip = img[:, w - max(1, int(right_margin)):]
                        else:
                            strip = img[:, :1]
                        border_value = _median_border_value(strip, channels)

                        cur_left = max(0, int(left_margin) - crop_left)
                        cur_right = max(0, int(right_margin) - crop_right)
                        pad_left = max(0, desired_left - cur_left)
                        pad_right = max(0, desired_right - cur_right)
                        if crop_left == 0 and crop_right == 0 and pad_left == 0 and pad_right == 0:
                            continue

                        padded = cv2.copyMakeBorder(
                            work_img, 0, 0, int(pad_left), int(pad_right), cv2.BORDER_CONSTANT, value=border_value
                        )
                        if _write_processed_image(fp, padded, c2e.options):
                            changed += 1
                        continue

                    # Auto mode: equalize only left/right margins by padding the
                    # smaller side up to the wider detected side. Top/bottom are
                    # intentionally left untouched.
                    min_margin = 3
                    desired = max(int(left_margin), int(right_margin))
                    if desired < min_margin:
                        continue
                    add_left = max(0, desired - int(left_margin))
                    add_right = max(0, desired - int(right_margin))
                    if add_left <= 0 and add_right <= 0:
                        continue
                    if left_margin >= right_margin and left_margin > 0:
                        strip = img[:, :max(1, int(left_margin))]
                    elif right_margin > 0:
                        strip = img[:, w - max(1, int(right_margin)):]
                    else:
                        strip = img[:, :1]
                    border_value = _median_border_value(strip, channels)
                    padded = cv2.copyMakeBorder(
                        img, 0, 0, int(add_left), int(add_right), cv2.BORDER_CONSTANT, value=border_value
                    )
                    if padded is img:
                        continue
                    if _write_processed_image(fp, padded, c2e.options):
                        changed += 1
            return scanned, changed, _spread_half_w

        def _match_spread_width_pass(root_path):
            """Pad single-page images to match the width of spread halves.

            Narrow pages (content <= target): strip margins, pad sides to target.
            Wide pages (content > target): strip margins, resize content to target,
            pad top/bottom using pre-scanned vertical alignment.
            """
            try:
                import cv2
                import numpy as np
            except ImportError:
                from .models import _ensure_imports

                _ensure_imports()
                import cv2
                import numpy as np

            img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif"}

            def _is_spread_half(filename):
                stem = os.path.splitext(str(filename or ""))[0].lower()
                return "-kcc-b" in stem or "-kcc-c" in stem

            def _is_split_page(filename):
                stem = os.path.splitext(str(filename or ""))[0].lower()
                return (
                    "-kcc-a" in stem
                    or "-kcc-b" in stem
                    or "-kcc-c" in stem
                    or "-kcc-d" in stem
                )

            # Phase 1: collect spread half width (most common)
            spread_widths = []
            for dirpath, _, filenames in os.walk(root_path):
                for afile in filenames:
                    ext = os.path.splitext(afile)[1].lower()
                    if ext not in img_exts:
                        continue
                    if not _is_spread_half(afile):
                        continue
                    fp = os.path.join(dirpath, afile)
                    img = cv2.imread(fp, cv2.IMREAD_UNCHANGED)
                    if img is not None:
                        spread_widths.append(int(img.shape[1]))

            if not spread_widths:
                return 0, 0

            from collections import Counter as _Ctr
            target_w = _Ctr(spread_widths).most_common(1)[0][0]
            convert_log(f"  [SPREAD] target_w={target_w} from {len(spread_widths)} spread halves, widths={dict(_Ctr(spread_widths))}")

            try:
                screen_h = int(c2e.options.profileData[1][1])
            except Exception:
                screen_h = 0
            if screen_h <= 0:
                screen_h = int(np.median([cv2.imread(os.path.join(d, f), cv2.IMREAD_UNCHANGED).shape[0]
                    for d, _, fns in os.walk(root_path)
                    for f in fns if _is_spread_half(f) and os.path.splitext(f)[1].lower() in img_exts
                    and cv2.imread(os.path.join(d, f), cv2.IMREAD_UNCHANGED) is not None
                ]) if spread_widths else 0)

            convert_log(f"  [SPREAD] screen_h={screen_h}")

            # Phase 2: adjust single pages
            changed = 0
            scanned = 0
            for dirpath, _, filenames in os.walk(root_path):
                if _is_stop_requested():
                    raise UserWarning("Conversion interrupted.")
                for afile in filenames:
                    if _is_stop_requested():
                        raise UserWarning("Conversion interrupted.")
                    ext = os.path.splitext(afile)[1].lower()
                    if ext not in img_exts:
                        continue
                    if _is_split_page(afile):
                        continue
                    stem = os.path.splitext(afile)[0].lower()
                    if stem == "cover" or stem.startswith("cover-"):
                        continue
                    fp = os.path.join(dirpath, afile)
                    rel_dir = os.path.relpath(dirpath, root_path).lower()
                    # Strip KCC processing suffix (-kcc-x, -kcc-a, etc.) to match prescan keys
                    base_stem = stem
                    for _sfx in ("-kcc-x", "-kcc-a", "-kcc-b", "-kcc-c", "-kcc-d"):
                        if base_stem.endswith(_sfx):
                            base_stem = base_stem[: -len(_sfx)]
                            break
                    valign_key = os.path.join(rel_dir, base_stem)
                    img = cv2.imread(fp, cv2.IMREAD_UNCHANGED)
                    if img is None:
                        continue
                    scanned += 1
                    h, w = img.shape[:2]

                    if img.ndim == 2:
                        channels = 1
                    else:
                        channels = int(img.shape[2]) if img.ndim == 3 else 1

                    if img.ndim == 2:
                        gray = img
                    elif channels == 4:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                    else:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                    left_margin = _detect_edge_margin_px(gray, True)
                    right_margin = _detect_edge_margin_px(gray, False)
                    content_w = max(1, w - left_margin - right_margin)

                    _force_wide = False
                    if content_w == target_w and left_margin == 0 and right_margin == 0:
                        _force_wide = True  # equal width → route to wide path for 3% side padding

                    # Border color from the widest margin strip
                    if left_margin >= right_margin and left_margin > 0:
                        bv_strip = img[:, :max(1, left_margin)]
                    elif right_margin > 0:
                        bv_strip = img[:, w - max(1, right_margin):]
                    else:
                        bv_strip = img[:, :1]
                    border_value = _median_border_value(bv_strip, channels)

                    if content_w <= target_w and not _force_wide:
                        # Narrow: strip existing margins, pad sides to target.
                        x0 = left_margin
                        x1 = max(x0 + 1, w - right_margin)
                        content = img[:, x0:x1]
                        total_pad = target_w - content_w
                        pad_l = total_pad // 2
                        pad_r = total_pad - pad_l
                        padded = cv2.copyMakeBorder(
                            content, 0, 0, pad_l, pad_r,
                            cv2.BORDER_CONSTANT, value=border_value,
                        )
                        # Vertical pad to screen height using pre-scan alignment
                        ph = padded.shape[0]
                        if screen_h > 0 and ph < screen_h:
                            vert_pad = screen_h - ph
                            prescan_align = _valign_map.get(valign_key)
                            if prescan_align:
                                convert_log(f"    [MSW] {afile} valign={prescan_align}")
                            if prescan_align == "top":
                                pt, pb = 0, vert_pad
                            elif prescan_align == "bottom":
                                pt, pb = vert_pad, 0
                            else:
                                pt = vert_pad // 2
                                pb = vert_pad - pt
                            padded = cv2.copyMakeBorder(
                                padded, pt, pb, 0, 0,
                                cv2.BORDER_CONSTANT, value=border_value,
                            )
                        if _write_processed_image(fp, padded, c2e.options):
                            changed += 1
                    else:
                        # Wide or equal: strip margins, resize content to target_w,
                        # then pad top/bottom to fill screen height.
                        top_margin = _detect_edge_margin_px(gray.T, True)
                        bot_margin = _detect_edge_margin_px(gray.T, False)
                        x0 = left_margin
                        x1 = max(x0 + 1, w - right_margin)
                        y0 = top_margin
                        y1 = max(y0 + 1, h - bot_margin)
                        content = img[y0:y1, x0:x1]
                        ch, cw = content.shape[:2]

                        # Border color from stripped margins
                        if top_margin >= bot_margin and top_margin > 0:
                            bv_strip = img[:max(1, top_margin), :]
                        elif bot_margin > 0:
                            bv_strip = img[h - max(1, bot_margin):, :]
                        border_value = _median_border_value(bv_strip, channels)

                        # Always add 3% side padding for wide/equal images
                        side_pad = max(1, int(round(target_w * 0.03)))
                        fit_w = target_w - 2 * side_pad

                        new_h = int(round(float(ch) * float(fit_w) / float(cw)))
                        resized = cv2.resize(
                            content, (fit_w, new_h), interpolation=cv2.INTER_AREA
                        )

                        if side_pad > 0:
                            resized = cv2.copyMakeBorder(
                                resized, 0, 0, side_pad, side_pad,
                                cv2.BORDER_CONSTANT, value=border_value,
                            )

                        if screen_h > 0 and new_h < screen_h:
                            vert_pad = screen_h - new_h
                            prescan_align = _valign_map.get(valign_key)
                            if prescan_align:
                                convert_log(f"    [MSW] {afile} valign={prescan_align}")
                            if prescan_align == "top":
                                pad_top, pad_bot = 0, vert_pad
                            elif prescan_align == "bottom":
                                pad_top, pad_bot = vert_pad, 0
                            else:
                                pad_top = vert_pad // 2
                                pad_bot = vert_pad - pad_top
                            resized = cv2.copyMakeBorder(
                                resized, pad_top, pad_bot, 0, 0,
                                cv2.BORDER_CONSTANT, value=border_value,
                            )

                        if _write_processed_image(fp, resized, c2e.options):
                            changed += 1
            return scanned, changed

        def _screen_margins_pass(root_path):
            """Add 3% side margins to images whose width reaches the screen width."""
            try:
                import cv2
            except ImportError:
                from .models import _ensure_imports
                _ensure_imports()
                import cv2

            try:
                screen_w = int(c2e.options.profileData[1][0])
            except Exception:
                screen_w = 0
            if screen_w <= 0:
                return 0, 0

            img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif"}
            margin_pct = 0.03
            side_pad = max(1, int(round(screen_w * margin_pct)))
            fit_w = screen_w - 2 * side_pad

            changed = 0
            scanned = 0
            for dirpath, _, filenames in os.walk(root_path):
                if _is_stop_requested():
                    raise UserWarning("Conversion interrupted.")
                for afile in filenames:
                    if _is_stop_requested():
                        raise UserWarning("Conversion interrupted.")
                    ext = os.path.splitext(afile)[1].lower()
                    if ext not in img_exts:
                        continue
                    stem = os.path.splitext(afile)[0].lower()
                    if stem == "cover" or stem.startswith("cover-"):
                        continue
                    fp = os.path.join(dirpath, afile)
                    img = cv2.imread(fp, cv2.IMREAD_UNCHANGED)
                    if img is None:
                        continue
                    h, w = img.shape[:2]
                    if w < screen_w:
                        continue  # narrower than screen, skip
                    scanned += 1

                    if img.ndim == 2:
                        channels = 1
                    else:
                        channels = int(img.shape[2]) if img.ndim == 3 else 1

                    # Border color from left/right edge
                    bv_strip = img[:, :1]
                    border_value = _median_border_value(bv_strip, channels)

                    new_h = int(round(float(h) * float(fit_w) / float(w)))
                    resized = cv2.resize(img, (fit_w, new_h), interpolation=cv2.INTER_AREA)
                    result = cv2.copyMakeBorder(
                        resized, 0, 0, side_pad, side_pad,
                        cv2.BORDER_CONSTANT, value=border_value,
                    )
                    if _write_processed_image(fp, result, c2e.options):
                        changed += 1
            return scanned, changed

        def _cleanup_workspace():
            try:
                from shutil import rmtree

                rmtree(os.path.join(path, '..', '..'), True)
            except Exception:
                pass

        def _prescan_valign_images():
            """Pre-scan original images to record vertical content alignment
            before KCC crops margins. Stores results in ``_valign_map``."""
            import cv2

            img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif"}
            for dirpath, _, filenames in os.walk(path):
                if _is_stop_requested():
                    break
                for afile in filenames:
                    ext = os.path.splitext(afile)[1].lower()
                    if ext not in img_exts:
                        continue
                    stem = os.path.splitext(afile)[0].lower()
                    if stem == "cover" or stem.startswith("cover-"):
                        continue
                    fp = os.path.join(dirpath, afile)
                    img = cv2.imread(fp, cv2.IMREAD_UNCHANGED)
                    if img is None:
                        continue
                    if img.ndim == 2:
                        gray = img
                    elif img.ndim == 3 and img.shape[2] == 4:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                    else:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    top_m = _detect_edge_margin_px(gray.T, True)
                    bot_m = _detect_edge_margin_px(gray.T, False)
                    rel_dir = os.path.relpath(dirpath, path).lower()
                    valign_key = os.path.join(rel_dir, stem)
                    if top_m == 0 and bot_m > 0:
                        _valign_map[valign_key] = "top"
                    elif bot_m == 0 and top_m > 0:
                        _valign_map[valign_key] = "bottom"

        if bool(match_spread_width):
            _prescan_valign_images()
            if _valign_map:
                convert_log(
                    f"  [SPREAD] Pre-scan valign: {len(_valign_map)} files marked "
                    f"(top={sum(1 for v in _valign_map.values() if v == 'top')}, "
                    f"bottom={sum(1 for v in _valign_map.values() if v == 'bottom')})"
                )

        gui = getattr(c2e, 'GUI', None)
        if gui:
            gui.progressBarTick.emit(str(pagenumber))
        if len(work) > 0:
            img_processing_start = perf_counter()
            if c2e.workerPool is not None:
                stop_monitor_done = threading.Event()
                stop_logged = False

                def _terminate_worker_pool(reason: str) -> None:
                    nonlocal stop_logged
                    pool = getattr(c2e, "workerPool", None)
                    if pool is None:
                        return
                    if reason == "stop" and not stop_logged:
                        stop_logged = True
                        convert_log("  [!] Stop requested, terminating image workers...")
                    try:
                        pool.terminate()
                    except Exception:
                        pass

                def _worker_callback(output):
                    if isinstance(output, tuple):
                        c2e.workerOutput.append(output)
                        _terminate_worker_pool("worker_error")
                    else:
                        for page in output:
                            if page is not None:
                                c2e.options.imgMetadata[page[0]] = page[1]
                    if gui:
                        gui.progressBarTick.emit('tick')
                        if not getattr(gui, "conversionAlive", True):
                            _terminate_worker_pool("gui")
                    if _is_stop_requested():
                        _terminate_worker_pool("stop")

                def _monitor_stop():
                    while not stop_monitor_done.wait(0.2):
                        if _is_stop_requested():
                            _terminate_worker_pool("stop")
                            break

                threading.Thread(target=_monitor_stop, daemon=True).start()
                try:
                    submitted_all = True
                    for i in work:
                        if _is_stop_requested():
                            submitted_all = False
                            _terminate_worker_pool("stop")
                            break
                        c2e.workerPool.apply_async(
                            func=c2e.imgFileProcessing,
                            args=(i,),
                            callback=_worker_callback,
                        )
                    if submitted_all:
                        c2e.workerPool.close()
                    c2e.workerPool.join()
                finally:
                    stop_monitor_done.set()
                    c2e.workerPool = None
            else:
                for i in work:
                    if _is_stop_requested():
                        _cleanup_workspace()
                        raise UserWarning("Conversion interrupted.")
                    output = c2e.imgFileProcessing(i)
                    if isinstance(output, tuple):
                        c2e.workerOutput.append(output)
                        break
                    for page in output:
                        if page is not None:
                            c2e.options.imgMetadata[page[0]] = page[1]
                    if gui:
                        gui.progressBarTick.emit('tick')
                        if not gui.conversionAlive:
                            break

            img_processing_end = perf_counter()
            print(f"{job_progress}imgFileProcessing: {img_processing_end - img_processing_start} seconds")

            if _is_stop_requested():
                _cleanup_workspace()
                raise UserWarning("Conversion interrupted.")

            if bool(screen_margins):
                try:
                    sm_scanned, sm_changed = _screen_margins_pass(path)
                    if sm_changed > 0 or sm_scanned > 0:
                        convert_log(
                            f"  [SCREEN-MARGINS] {sm_changed}/{sm_scanned} files updated (3% side padding)"
                        )
                except Exception as e:
                    convert_log(f"  [WARN] Screen margins failed: {e}")

            _do_margin = bool(auto_balance_margins) or bool(match_spread_width)
            if _do_margin:
                try:
                    scanned_cnt, changed_cnt, _matched_spread_w = _auto_balance_side_margins(
                        path,
                        target_margin_px=auto_balance_margin_px if bool(auto_balance_margins) else 0,
                        target_margin_unit=auto_balance_margin_unit if bool(auto_balance_margins) else "px",
                        target_margin_pct=auto_balance_margin_pct if bool(auto_balance_margins) else 0.0,
                        match_spread_width=bool(match_spread_width),
                    )
                    margin_unit = str(auto_balance_margin_unit or "px").strip().lower()
                    if margin_unit in {"%", "percent"}:
                        margin_unit = "pct"
                    try:
                        margin_pct = float(auto_balance_margin_pct or 0.0)
                    except Exception:
                        margin_pct = 0.0
                    if _matched_spread_w > 0:
                        convert_log(
                            f"  [MARGIN] Match spread width ({_matched_spread_w}px): {changed_cnt}/{scanned_cnt} files updated"
                        )
                    elif margin_unit == "pct" and margin_pct > 0.0:
                        convert_log(
                            "  [MARGIN] Auto-balance side margins "
                            f"(final width={margin_pct:g}% of screen): {changed_cnt}/{scanned_cnt} files updated"
                        )
                    elif int(auto_balance_margin_px or 0) > 0:
                        convert_log(
                            "  [MARGIN] Auto-balance side margins "
                            f"(target={int(auto_balance_margin_px)}px): {changed_cnt}/{scanned_cnt} files updated"
                        )
                    else:
                        convert_log(
                            f"  [MARGIN] Auto-balance side margins: {changed_cnt}/{scanned_cnt} files updated"
                        )
                except Exception as e:
                    convert_log(f"  [WARN] Auto-balance side margins failed: {e}")

            if bool(match_spread_width):
                try:
                    msw_scanned, msw_changed = _match_spread_width_pass(path)
                    if msw_changed > 0 or msw_scanned > 0:
                        convert_log(
                            f"  [SPREAD] Match spread width: {msw_changed}/{msw_scanned} files updated"
                        )
                    else:
                        convert_log("  [SPREAD] Match spread width: no spread halves found, skipped")
                except Exception as e:
                    convert_log(f"  [WARN] Match spread width failed: {e}")
            from kindlecomicconverter.shared import dot_clean
            dot_clean(path)

            if _is_stop_requested() or (gui and not gui.conversionAlive):
                _cleanup_workspace()
                raise UserWarning("Conversion interrupted.")
            if len(c2e.workerOutput) > 0:
                _cleanup_workspace()
                raise RuntimeError("One of workers crashed. Cause: " +
                                   c2e.workerOutput[0][0], c2e.workerOutput[0][1])
        else:
            _cleanup_workspace()
            raise UserWarning("C2E: Source directory is empty.")


    # maic: buildEPUB fix for TOC landing on split spread halves
    _orig_buildEPUB = c2e.buildEPUB

    def _is_mobi_format() -> bool:
        return str(getattr(c2e.options, "format", "") or "").strip().upper().startswith("MOBI")

    # Wrapper: diagnostics + safe retry
    def _rewrite_toc_by_chapter_dirs(epub_root, chapter_titles, chapter_dirs, chapter_indices=None, chapter_stems=None):
        """Rewrite TOC files using explicit chapter anchors (preferred) or chapter dirs fallback."""
        try:
            text_root = os.path.join(epub_root, "OEBPS", "Text")
            images_root = os.path.join(epub_root, "OEBPS", "Images")
            if not os.path.isdir(text_root) or not os.path.isdir(images_root):
                convert_log("  [WARN] TOC rewrite skipped: OEBPS/Text or OEBPS/Images not found")
                return

            # Primary mode: explicit anchor indexes from comicinfo_chapters.
            # This preserves bookmarks inside a chapter folder (not only first page of folder).
            from kindlecomicconverter.shared import getImageFileName
            hrefs = []
            use_idx_mode = bool(chapter_indices and len(chapter_indices) == len(chapter_titles))
            if use_idx_mode:
                filelist = []
                stemlist = []
                for r0, d0, f0 in os.walk(images_root):
                    d0.sort(key=c2e.OS_SORT_KEY)
                    f0.sort(key=c2e.OS_SORT_KEY)
                    rel_dir = os.path.relpath(r0, images_root).replace("\\", "/")
                    if rel_dir == ".":
                        rel_dir = ""
                    for fn in f0:
                        stem, ext = getImageFileName(fn)
                        if not ext:
                            continue
                        # KCC may add a synthetic top-level cover.jpg used for metadata.
                        # It is not part of logical page anchors from sidecar bookmarks.
                        if rel_dir == "" and fn.lower() == "cover.jpg":
                            continue
                        href = f"Text/{rel_dir}/{stem}.xhtml" if rel_dir else f"Text/{stem}.xhtml"
                        filelist.append(href)
                        stemlist.append(str(stem or "").lower())
                for n, idx in enumerate(chapter_indices):
                    target_stem = ""
                    if chapter_stems and n < len(chapter_stems):
                        target_stem = str(chapter_stems[n] or "").lower()
                    if target_stem:
                        hit = None
                        for j, s in enumerate(stemlist):
                            if s == target_stem or s.startswith(target_stem + "-") or s.startswith(target_stem + "_"):
                                hit = j
                                break
                        if hit is not None:
                            hrefs.append(filelist[hit])
                            continue
                    try:
                        i = int(idx)
                    except Exception:
                        i = -1
                    hrefs.append(filelist[i] if 0 <= i < len(filelist) else None)
            else:
                # Fallback mode: resolve first page per expected chapter dir.
                for d in (chapter_dirs or []):
                    d_norm = (d or "").replace("\\", "/").strip("/").lower()
                    if not d_norm:
                        hrefs.append(None)
                        continue
                    img_abs = os.path.join(images_root, *d_norm.split("/"))
                    first_rel = None
                    if os.path.isdir(img_abs):
                        for r0, d0, f0 in os.walk(img_abs):
                            d0.sort(key=c2e.OS_SORT_KEY)
                            f0.sort(key=c2e.OS_SORT_KEY)
                            for fn in f0:
                                stem, ext = getImageFileName(fn)
                                if ext:
                                    rel_dir = os.path.relpath(r0, images_root).replace("\\", "/")
                                    if rel_dir == ".":
                                        rel_dir = ""
                                    href = f"Text/{rel_dir}/{stem}.xhtml" if rel_dir else f"Text/{stem}.xhtml"
                                    first_rel = href
                                    break
                            if first_rel:
                                break
                    # Fallback: scan Text folder directly.
                    if not first_rel:
                        d_abs = os.path.join(text_root, *d_norm.split("/"))
                        if os.path.isdir(d_abs):
                            for r0, d0, f0 in os.walk(d_abs):
                                d0.sort(key=c2e.OS_SORT_KEY)
                                f0.sort(key=c2e.OS_SORT_KEY)
                                for fn in f0:
                                    if fn.lower().endswith(".xhtml"):
                                        rel = os.path.relpath(os.path.join(r0, fn), os.path.join(epub_root, "OEBPS")).replace("\\", "/")
                                        first_rel = rel
                                        break
                                if first_rel:
                                    break
                    hrefs.append(first_rel)

            if not any(hrefs):
                try:
                    dirs_dbg = []
                    for r0, d0, _ in os.walk(images_root):
                        rel = os.path.relpath(r0, images_root).replace("\\", "/")
                        if rel != ".":
                            dirs_dbg.append(rel.lower())
                        d0.sort(key=c2e.OS_SORT_KEY)
                        if len(dirs_dbg) >= 8:
                            break
                    convert_log(f"  [WARN] TOC rewrite skipped: no chapter hrefs resolved; chapter_dirs={list(chapter_dirs or [])[:3]}... images_dirs={dirs_dbg[:8]}")
                except Exception:
                    convert_log("  [WARN] TOC rewrite skipped: no chapter hrefs resolved")
                return

            # Update toc.ncx (replace navMap entirely)
            ncx_path = os.path.join(epub_root, "OEBPS", "toc.ncx")
            if os.path.isfile(ncx_path):
                import xml.etree.ElementTree as _ET
                ns_ncx = "{http://www.daisy.org/z3986/2005/ncx/}"
                tree = _ET.parse(ncx_path)
                root = tree.getroot()
                updated = 0
                navmap = root.find(f".//{ns_ncx}navMap")
                if navmap is not None:
                    for child in list(navmap):
                        navmap.remove(child)
                    for i, href in enumerate(hrefs):
                        if not href:
                            continue
                        np = _ET.SubElement(navmap, f"{ns_ncx}navPoint")
                        np.set("id", f"maic-{i + 1}")
                        navlabel = _ET.SubElement(np, f"{ns_ncx}navLabel")
                        text = _ET.SubElement(navlabel, f"{ns_ncx}text")
                        text.text = chapter_titles[i] if i < len(chapter_titles) else f"Chapter {i + 1}"
                        content = _ET.SubElement(np, f"{ns_ncx}content")
                        content.set("src", href)
                        updated += 1
                if updated:
                    tree.write(ncx_path, encoding="utf-8", xml_declaration=True)
                    convert_log(f"  [TOC] toc.ncx rewritten from chapter anchors: {updated} entries")

            # Update nav.xhtml (replace TOC/page-list entries entirely)
            nav_path = os.path.join(epub_root, "OEBPS", "nav.xhtml")
            if os.path.isfile(nav_path):
                import xml.etree.ElementTree as _ET
                ns = {"x": "http://www.w3.org/1999/xhtml", "epub": "http://www.idpf.org/2007/ops"}
                tree = _ET.parse(nav_path)
                root = tree.getroot()
                toc_ol = root.find(".//x:nav[@epub:type='toc']/x:ol", ns)
                page_ol = root.find(".//x:nav[@epub:type='page-list']/x:ol", ns)
                updated = 0
                if toc_ol is not None:
                    for child in list(toc_ol):
                        toc_ol.remove(child)
                if page_ol is not None:
                    for child in list(page_ol):
                        page_ol.remove(child)
                xhtml_ns = "{http://www.w3.org/1999/xhtml}"
                for i, href in enumerate(hrefs):
                    if not href:
                        continue
                    title = chapter_titles[i] if i < len(chapter_titles) else f"Chapter {i + 1}"
                    if toc_ol is not None:
                        li = _ET.SubElement(toc_ol, f"{xhtml_ns}li")
                        a = _ET.SubElement(li, f"{xhtml_ns}a")
                        a.set("href", href)
                        a.text = title
                    if page_ol is not None:
                        li = _ET.SubElement(page_ol, f"{xhtml_ns}li")
                        a = _ET.SubElement(li, f"{xhtml_ns}a")
                        a.set("href", href)
                        a.text = title
                    updated += 1
                if updated:
                    tree.write(nav_path, encoding="utf-8", xml_declaration=True)
                    convert_log(f"  [TOC] nav.xhtml rewritten from chapter anchors: {updated} entries")
        except Exception as e:
            convert_log(f"  [WARN] TOC rewrite from chapter anchors failed: {e}")

    def _patched_buildEPUB(path, chapternames_arg, tomenumber, ischunked, cover, originalpath, job_progress='', len_tomes=0):
        # maic: splitter + Kindle TOC boundary fix
        # Ensure each chapter anchor lands inside its expected chapter folder in the *final* Images tree (after split).
        try:
            if bool(getattr(c2e.options, "maic_anchor_mode", False)):
                # In explicit-anchor mode we preserve exact bookmark positions from sidecar.
                # Folder-boundary auto-shift can incorrectly move all subsequent chapters.
                raise RuntimeError("skip-folder-shift-in-anchor-mode")
            chapters = list(getattr(c2e.options, "comicinfo_chapters", []) or [])
            exp_dirs = list(getattr(c2e.options, "maic_chapter_dirs", []) or [])
            if chapters and exp_dirs and len(exp_dirs) == len(chapters):
                # Repeated chapter dirs mean we have extra bookmarks inside the same chapter folder.
                # Folder-boundary shift is unsafe in this mode and can move all subsequent chapters.
                if len(set([str(d or "").strip("/").lower() for d in exp_dirs])) < len(exp_dirs):
                    convert_log("  [TOC] Chapter-folder fix skipped: repeated chapter dirs (intra-chapter bookmarks)")
                    raise RuntimeError("skip-folder-shift-repeated-dirs")
                images_root = os.path.join(path, "OEBPS", "Images")
                # Build final ordered list of image relpaths as KCC walks them
                filelist = []
                try:
                    from kindlecomicconverter.shared import getImageFileName
                    for r0, d0, f0 in os.walk(images_root):
                        d0.sort(key=c2e.OS_SORT_KEY)
                        f0.sort(key=c2e.OS_SORT_KEY)
                        rel_dir = os.path.relpath(r0, images_root).replace("\\", "/")
                        if rel_dir == ".":
                            rel_dir = ""
                        for fn in f0:
                            _, ext0 = getImageFileName(fn)
                            if ext0:
                                if rel_dir == "" and fn.lower() == "cover.jpg":
                                    continue
                                relp = (rel_dir + "/" + fn if rel_dir else fn).lower()
                                filelist.append(relp)
                except Exception:
                    filelist = []

                if filelist:
                    fixed = []
                    shifts = 0
                    prev = -1
                    for (idx, title), exp in zip(chapters, exp_dirs):
                        idx = int(idx)
                        exp = (exp or "").strip("/").lower()
                        if idx < 0:
                            idx = 0
                        if idx <= prev:
                            idx = prev + 1
                        if idx >= len(filelist):
                            idx = len(filelist) - 1
                        # Move forward until we land inside expected chapter folder.
                        # If folder is not found in the remaining list, keep original index.
                        if exp:
                            old_idx = idx
                            probe = idx
                            while probe < len(filelist) and not filelist[probe].startswith(exp + "/"):
                                probe += 1
                            if probe < len(filelist):
                                idx = probe
                                shifts += (idx - old_idx)
                        fixed.append((idx, title))
                        prev = idx
                    if fixed != chapters:
                        c2e.options.comicinfo_chapters = fixed
                        convert_log(f"  [TOC] Adjusted chapter anchors to chapter folders: {shifts} shifts")
        except Exception as e:
            if str(e) not in ("skip-folder-shift-in-anchor-mode", "skip-folder-shift-repeated-dirs"):
                convert_log(f"  [WARN] TOC chapter-folder fix failed: {e}")

        chapter_indices_for_rewrite = [i for i, _ in list(getattr(c2e.options, "comicinfo_chapters", []) or [])]
        chapter_titles_for_rewrite = [t for _, t in list(getattr(c2e.options, "comicinfo_chapters", []) or [])]
        chapter_dirs_for_rewrite = list(getattr(c2e.options, "maic_chapter_dirs", []) or [])
        chapter_stems_for_rewrite = list(getattr(c2e.options, "maic_anchor_stems", []) or [])
        saved_ci = list(getattr(c2e.options, "comicinfo_chapters", []) or [])
        use_external_toc = bool(chapter_titles_for_rewrite and (chapter_indices_for_rewrite or chapter_dirs_for_rewrite))
        if use_external_toc:
            # Disable KCC internal split compensation for comicinfo_chapters;
            # we will rewrite TOC from explicit chapter dirs/titles below.
            c2e.options.comicinfo_chapters = []
            convert_log(f"  [TOC] External TOC mode enabled: {len(chapter_titles_for_rewrite)} chapters")

        try:
            ret = _orig_buildEPUB(
                path,
                chapternames_arg,
                tomenumber,
                ischunked,
                cover,
                originalpath,
                job_progress,
                len_tomes,
            )
            if use_external_toc:
                _rewrite_toc_by_chapter_dirs(
                    path,
                    chapter_titles_for_rewrite,
                    chapter_dirs_for_rewrite,
                    chapter_indices_for_rewrite,
                    chapter_stems_for_rewrite
                )
            c2e.options.comicinfo_chapters = saved_ci
            return ret
        except IndexError as ex:
            convert_log(f"  [!] buildEPUB IndexError: {ex} - retrying without bookmarks")
            c2e.options.comicinfo_chapters = []
            # NOTE: internal processing detail.
            import shutil as _sh2
            text_dir = os.path.join(path, 'OEBPS', 'Text')
            if os.path.isdir(text_dir):
                _sh2.rmtree(text_dir, ignore_errors=True)
            for fname in ['content.opf', 'toc.ncx', 'nav.xhtml']:
                fp = os.path.join(path, 'OEBPS', fname)
                if os.path.isfile(fp):
                    try:
                        os.remove(fp)
                    except Exception:
                        pass
            ret = _orig_buildEPUB(
                path,
                chapternames_arg,
                tomenumber,
                ischunked,
                cover,
                originalpath,
                job_progress,
                len_tomes,
            )
            if use_external_toc:
                _rewrite_toc_by_chapter_dirs(path, chapter_titles_for_rewrite, chapter_dirs_for_rewrite)
            c2e.options.comicinfo_chapters = saved_ci
            return ret

    c2e.buildEPUB = _patched_buildEPUB

    # Patch buildOPF to handle authors differently for EPUB vs MOBI:
    # - EPUB (Send to Kindle): merge into single <dc:creator> with ", " separator,
    #   because Send to Kindle only displays the first <dc:creator> element.
    # - MOBI: split comma-separated authors into separate <dc:creator> elements,
    #   because Kindle natively joins them for display.
    _orig_buildOPF = c2e.buildOPF

    def _patched_buildOPF(*args, **kwargs):
        if hasattr(c2e, 'options') and c2e.options.authors:
            expanded = []
            for a in c2e.options.authors:
                for part in a.split(","):
                    part = part.strip()
                    if part:
                        expanded.append(part)
            if len(expanded) > 1:
                fmt = getattr(c2e.options, 'format', 'EPUB')
                is_kfx = bool(getattr(c2e.options, 'kfx', False))
                keep_epub = bool(getattr(c2e.options, 'keep_epub', False))
                convert_log(f"  [META] format={fmt!r} kfx={is_kfx} keep_epub={keep_epub}")
                if fmt == 'MOBI' and not is_kfx:
                    c2e.options.authors = expanded
                    convert_log(f"  [META] Authors split into {len(expanded)} <dc:creator> elements: {expanded}")
                else:
                    merged = _EPUB_AUTHOR_SEPARATOR.join(expanded)
                    c2e.options.authors = [merged]
                    convert_log(f"  [META] Authors merged into single <dc:creator>: {merged}")
            elif len(expanded) == 1 and (len(c2e.options.authors) != 1 or c2e.options.authors[0] != expanded[0]):
                c2e.options.authors = expanded
        result = _orig_buildOPF(*args, **kwargs)
        return result

    c2e.buildOPF = _patched_buildOPF

    # Same fix for PDF output path — merge authors into single entry.
    _orig_buildPDF = c2e.buildPDF

    def _patched_buildPDF(*args, **kwargs):
        if hasattr(c2e, 'options') and c2e.options.authors:
            expanded = []
            for a in c2e.options.authors:
                for part in a.split(","):
                    part = part.strip()
                    if part:
                        expanded.append(part)
            if len(expanded) > 1:
                merged = " & ".join(expanded)
                c2e.options.authors = [merged]
                convert_log(f"  [META] Authors merged into single entry: {merged}")
            elif len(expanded) == 1 and (len(c2e.options.authors) != 1 or c2e.options.authors[0] != expanded[0]):
                c2e.options.authors = expanded
        return _orig_buildPDF(*args, **kwargs)

    c2e.buildPDF = _patched_buildPDF

    # In MOBI+EPUB mode KCC builds one EPUB (used as MOBI source and kept on disk).
    # After MOBI is produced, rewrite kept EPUB OPF creators for Send to Kindle display.
    _orig_makeMOBIFix = getattr(c2e, 'makeMOBIFix', None)

    def _rewrite_epub_opf_single_creator(epub_path: str, merged_author: str) -> bool:
        if not epub_path or not os.path.isfile(epub_path):
            return False
        if not merged_author.strip():
            return False
        import tempfile
        import zipfile
        import shutil as _sh
        import xml.etree.ElementTree as _ET

        workdir = tempfile.mkdtemp(prefix='maic_epub_meta_')
        try:
            with zipfile.ZipFile(epub_path, 'r') as zin:
                zin.extractall(workdir)

            opf_path = os.path.join(workdir, 'OEBPS', 'content.opf')
            if not os.path.isfile(opf_path):
                return False

            root = _ET.parse(opf_path).getroot()
            ns_opf = 'http://www.idpf.org/2007/opf'
            ns_dc = 'http://purl.org/dc/elements/1.1/'
            _ET.register_namespace('', ns_opf)
            _ET.register_namespace('dc', ns_dc)
            metadata = root.find(f'{{{ns_opf}}}metadata')
            if metadata is None:
                return False

            creator_tag = f'{{{ns_dc}}}creator'
            for node in list(metadata):
                if node.tag == creator_tag:
                    metadata.remove(node)
            creator = _ET.Element(creator_tag)
            creator.text = merged_author
            metadata.append(creator)

            meta_tag = f'{{{ns_opf}}}meta'
            author_meta = None
            for node in metadata.findall(meta_tag):
                if (node.get('name') or '').strip().lower() == 'author':
                    author_meta = node
                    break
            if author_meta is None:
                author_meta = _ET.Element(meta_tag)
                author_meta.set('name', 'author')
                metadata.append(author_meta)
            author_meta.set('content', merged_author)

            _ET.ElementTree(root).write(opf_path, encoding='utf-8', xml_declaration=True)

            temp_epub = epub_path + '.tmp'
            with zipfile.ZipFile(temp_epub, 'w') as zout:
                mimetype_path = os.path.join(workdir, 'mimetype')
                if os.path.isfile(mimetype_path):
                    zout.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
                else:
                    zout.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
                for dirpath, _, filenames in os.walk(workdir):
                    for filename in filenames:
                        abs_path = os.path.join(dirpath, filename)
                        rel_path = os.path.relpath(abs_path, workdir).replace('\\', '/')
                        if rel_path == 'mimetype':
                            continue
                        zout.write(abs_path, rel_path, compress_type=zipfile.ZIP_DEFLATED)
            os.replace(temp_epub, epub_path)
            return True
        finally:
            _sh.rmtree(workdir, ignore_errors=True)

    def _patched_makeMOBIFix(item, uuid):
        if _orig_makeMOBIFix is None:
            return [False, 'makeMOBIFix unavailable']
        forced_doc_type = str(getattr(c2e.options, "maic_kindle_doc_type", "AUTO") or "AUTO").upper()
        if forced_doc_type in {"PDOC", "EBOK"}:
            try:
                from shutil import move as _move
                is_pdoc = forced_doc_type == "PDOC"
                keep_epub = bool(getattr(c2e.options, "keep_epub", False))
                if not keep_epub:
                    os.remove(item)
                mobi_path = item.replace('.epub', '.mobi')
                _move(mobi_path, mobi_path + '_toclean')
                c2e.dualmetafix.DualMobiMetaFix(
                    mobi_path + '_toclean',
                    mobi_path,
                    bytes(uuid, 'UTF-8'),
                    is_pdoc,
                )
                convert_log(f"  [MOBI] Kindle doc type forced: {forced_doc_type}")
                result = [True]
            except Exception as err:
                result = [False, format(err)]
        else:
            result = _orig_makeMOBIFix(item, uuid)
        try:
            keep_epub = bool(getattr(c2e.options, 'keep_epub', False))
            fmt = getattr(c2e.options, 'format', '')
            if keep_epub and fmt == 'MOBI' and result and result[0]:
                expanded = []
                for a in (getattr(c2e.options, 'authors', None) or []):
                    for part in str(a).replace(';', ',').split(','):
                        part = part.strip()
                        if part:
                            expanded.append(part)
                if len(expanded) > 1:
                    def _is_translator_like(value: str) -> bool:
                        text = value.strip().casefold()
                        return (
                            text.startswith('translator')
                            or text.startswith('translation')
                            or text.startswith('перевод')
                        )

                    regular = [p for p in expanded if not _is_translator_like(p)]
                    translators = [p for p in expanded if _is_translator_like(p)]
                    merged = _EPUB_AUTHOR_SEPARATOR.join(regular + translators)
                    if _rewrite_epub_opf_single_creator(item, merged):
                        convert_log(f"  [META] EPUB OPF authors rewritten for Send to Kindle: {merged}")
                    else:
                        convert_log("  [WARN] EPUB OPF author rewrite skipped (content.opf not found or update failed)")
        except Exception as ex:
            convert_log(f"  [WARN] EPUB OPF author rewrite failed: {ex}")
        return result

    if _orig_makeMOBIFix is not None:
        c2e.makeMOBIFix = _patched_makeMOBIFix

    # NOTE: internal processing detail.
    c2e.sanitizeTree = _patched_sanitizeTree
    c2e.imgDirectoryProcessing = _patched_imgDirProc
    nc_count = len(nocrop_norm)
    cc_count = len(cc_norm)
    cs_count = len(cs_norm)
    if nc_count:
        convert_log(f"  [NOCROP] NoCrop patch applied: {nc_count} files")
    if cc_count:
        convert_log(f"  [CROP] Custom crop patch applied: {cc_count} files")
    if cs_count:
        convert_log(f"  [SPLIT] Custom split patch applied: {cs_count} files")

    def restore():
        c2e.sanitizeTree = _orig_sanitize
        c2e.imgDirectoryProcessing = _orig_imgDir
        kcc_image.ComicPage.resizeImage = _orig_resizeImage
        kcc_image.ComicPage.save_with_codec = _orig_save_with_codec
        if _orig_cover_save_to_epub is not None:
            kcc_image.Cover.save_to_epub = _orig_cover_save_to_epub
        elif getattr(kcc_image.Cover, "save_to_epub", None) is _maic_patched_cover_save_to_epub:
            try:
                delattr(kcc_image.Cover, "save_to_epub")
            except Exception:
                pass
        c2e.buildEPUB = _orig_buildEPUB
        c2e.buildOPF = _orig_buildOPF
        c2e.buildPDF = _orig_buildPDF
        if _orig_makeMOBIFix is not None:
            c2e.makeMOBIFix = _orig_makeMOBIFix
        # Cleanup temporary deferred cover dirs kept for metadata-only cover handling.
        for tmp_dir in list(deferred_cover_tmp_dirs):
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass
        deferred_cover_tmp_dirs.clear()
        for tmp_dir in crop_background_tmp_dirs:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        crop_background_tmp_dirs.clear()

    return restore
