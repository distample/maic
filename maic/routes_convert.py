"""Routes for /api/convert endpoints (KCC conversion pipeline)."""

from __future__ import annotations

import os
import io
import json
import posixpath
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import uuid
import xml.etree.ElementTree as ET
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, Callable, cast

from flask import Blueprint, jsonify, request
from PIL import Image

from . import error_codes as EC
from ._comicinfo import (
    read_raw_title as _read_comicinfo_raw_title,
    read_title_author as _read_comicinfo_title_author,
    split_people as _split_people,
    xml_local_name as _xml_local_name,
)
from .api_errors import fail
from .config import KCC_AVAILABLE, logger, persist_runtime_settings, state, state_lock
from .convert_validation import validate_convert_log_mode_payload, validate_convert_start_payload
from .dto import ConvertLogModePayload, ConvertStartPayload
from .kcc_argv import build_kcc_argv
from .kcc_env import ensure_kcc_deps, ensure_kcc_path
from .kcc_scan import (
    compute_crop_preview,
    scan_source_entries,
    scan_spread_pages,
    serve_thumb_response,
)
from .log_context import log_event
from .path_access import add_allowed_root
from .sevenzip import find_7z
from .sidecar import get_sidecar_path, save_sidecar
from .validation import as_bool, as_float, as_int, json_body, require_non_empty_str


def _spread_preview_mode(payload, no_processing=False):
    """Resolve the tri-state while accepting the former checkbox payload."""
    if no_processing:
        return 0
    if payload.get("spread_preview_mode") is not None:
        return as_int(payload.get("spread_preview_mode"), 1)
    if "force_spread_preview" in payload:
        return 2 if bool(payload.get("force_spread_preview")) else 0
    return 1


class _LiveWriter:
    """Line-buffered stream adapter used to parse live KCC stdout/stderr."""

    def __init__(self, log_line: Callable[[str], None], on_line: Callable[[str], None] | None = None):
        self._buf = ""
        self._log_line = log_line
        self._on_line = on_line

    def write(self, s: str):
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            self._log_line(line)
            if self._on_line is not None:
                self._on_line(line)

    def flush(self):
        return None


def _log_convert_event(
    message: str,
    *,
    phase: str,
    source: str = "",
    index: int | None = None,
    total: int | None = None,
    job_id: str | None = None,
    level: str = "info",
) -> None:
    log_event(
        logger,
        message,
        component="convert",
        phase=phase,
        job_id=job_id,
        level=level,
        source=source or None,
        index=index,
        total=total,
    )


def _find_kpr_exe() -> str:
    """Find Kindle Previewer 3 executable for KPF generation."""
    if os.name == "nt":
        candidates: list[str] = []
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            candidates.append(
                os.path.join(local_app_data, "Amazon", "Kindle Previewer 3", "Kindle Previewer 3.exe")
            )
        for base in [r"C:\Program Files", r"C:\Program Files (x86)"]:
            candidates.append(os.path.join(base, "Amazon", "Kindle Previewer 3", "Kindle Previewer 3.exe"))
        for p in candidates:
            if os.path.isfile(p):
                return p
    elif sys.platform == "darwin":
        p = "/Applications/Kindle Previewer 3.app/Contents/MacOS/Kindle Previewer 3"
        if os.path.isfile(p):
            return p
    return ""


def _find_kfxlib_output_dir() -> str:
    """Return path to bundled KFX Output plugin modules, if present."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(here, "modules", "KFX Output"),
        os.path.join(here, "modules", "KFX", "output"),
        # kfxlib unpacked straight into modules/, without the plugin folder
        # around it.
        os.path.join(here, "modules"),
    ]
    for output_dir in candidates:
        if os.path.isfile(os.path.join(output_dir, "kfxlib", "__init__.py")):
            return output_dir
    return ""


def _resolve_kfx_cde_type(kindle_doc_type: str) -> str:
    """Map UI kindle_doc_type to KFX cde_content_type.

    Anything that is not an explicit EBOK is a personal document.  The device
    looks an EBOK's cover art up in the content catalogue by ASIN, and for a
    sideloaded book that lookup fails: the library tile and the standby screen
    stay blank even though the cover renders inside the book.  Since the route
    passes a value on every build, defaulting to EBOK here would override the
    PDOC the generator deliberately defaults to.
    """
    dt = str(kindle_doc_type or "auto").strip().lower()
    return "EBOK" if dt == "ebok" else "PDOC"


def _format_kfx_progress_bar(elapsed_seconds: int, *, width: int = 24, step_seconds: int = 10) -> str:
    """Return an indeterminate fill bar that advances every ``step_seconds``."""
    if width < 3:
        width = 3
    if step_seconds < 1:
        step_seconds = 1
    filled = int(elapsed_seconds // step_seconds) % (width + 1)
    if filled > width:
        filled = width
    cells = ("#" * filled) + ("-" * (width - filled))
    return "[" + cells + f"] {elapsed_seconds}s"


def _is_kfx_runtime_available() -> bool:
    return bool(_find_kpr_exe() and _find_kfxlib_output_dir())


def _install_kfxlib_calibre_shim() -> Callable[[], None]:
    """Install minimal ``calibre.utils.config_base`` shim for bundled kfxlib.

    Bundled ``kfxlib`` imports ``calibre.utils.config_base.tweaks`` while running
    KPR conversion. maic may execute this path under system Python where calibre
    package is not importable. We provide a tiny runtime shim and restore
    ``sys.modules`` afterwards.
    """
    if "calibre.utils.config_base" in sys.modules:
        return lambda: None

    import types

    touched: dict[str, Any | None] = {
        "calibre": sys.modules.get("calibre"),
        "calibre.utils": sys.modules.get("calibre.utils"),
        "calibre.utils.config_base": sys.modules.get("calibre.utils.config_base"),
    }

    calibre_mod = touched["calibre"]
    if calibre_mod is None:
        calibre_mod = types.ModuleType("calibre")

    utils_mod = touched["calibre.utils"]
    if utils_mod is None:
        utils_mod = types.ModuleType("calibre.utils")

    cfg_mod = types.ModuleType("calibre.utils.config_base")
    cfg_mod.tweaks = {}

    setattr(utils_mod, "config_base", cfg_mod)
    setattr(calibre_mod, "utils", utils_mod)

    sys.modules["calibre"] = cast(Any, calibre_mod)
    sys.modules["calibre.utils"] = cast(Any, utils_mod)
    sys.modules["calibre.utils.config_base"] = cfg_mod

    def _restore() -> None:
        for name, prev in touched.items():
            if prev is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = prev

    return _restore



def _run_native_epub_to_kfx(
    epub_path: str,
    out_kfx_path: str,
    *,
    kindle_doc_type: str = "auto",
    reading_direction: str | None = None,
    log_fn: Any = None,
    status_fn: Callable[[str, int | None], None] | None = None,
) -> tuple[int, str]:
    """EPUB -> KFX with maic's own generator, without Kindle Previewer.

    KCC has already produced the page images; this replaces only the KPR stage,
    so the conversion no longer depends on Kindle Previewer being installed.
    """
    def _log(msg: str) -> None:
        if log_fn:
            log_fn(f"  [KFX maic] {msg}")

    kfxlib_dir = _find_kfxlib_output_dir()
    if not kfxlib_dir:
        return 1, "bundled kfxlib not found (modules/KFX/output)"

    restore_shim = _install_kfxlib_calibre_shim()
    sys_path_added = False
    plugin_path_added = False
    plugin_modules = ""
    try:
        if status_fn is not None:
            try:
                status_fn("KFX maic: building container", 95)
            except Exception:
                pass

        if kfxlib_dir not in sys.path:
            sys.path.insert(0, kfxlib_dir)
            sys_path_added = True

        # kfxlib imports pypdf, which ships vendored inside the plugin rather
        # than being installed; without this the import fails.
        plugin_modules = os.path.join(kfxlib_dir, "kfxlib", "calibre-plugin-modules")
        if os.path.isdir(plugin_modules) and plugin_modules not in sys.path:
            sys.path.insert(0, plugin_modules)
            plugin_path_added = True

        from kfxlib import set_logger  # type: ignore[import-not-found]
        from ._kfx_native import build_kfx_from_epub

        class _Log:
            def info(self, msg: object) -> None:
                pass

            def warning(self, msg: object) -> None:
                _log(f"WARN: {msg}")

            def error(self, msg: object) -> None:
                _log(f"ERROR: {msg}")

            def debug(self, msg: object) -> None:
                pass

        set_logger(_Log())
        build_kfx_from_epub(
            epub_path,
            out_kfx_path,
            cde_type=_resolve_kfx_cde_type(kindle_doc_type),
            reading_direction=reading_direction,
            thumbnails="full",
            log_fn=_log,
        )
        return 0, "native KFX generated without Kindle Previewer"
    except Exception:
        return 1, traceback.format_exc()
    finally:
        for added, entry in ((plugin_path_added, plugin_modules), (sys_path_added, kfxlib_dir)):
            if added:
                try:
                    sys.path.remove(entry)
                except ValueError:
                    pass
        try:
            restore_shim()
        except Exception:
            pass


def _is_native_kfx_mobi_format(requested: str) -> bool:
    normalized = " ".join(str(requested or "").strip().upper().split())
    return normalized in {"KFX + MOBI MAIC", "KFX+MOBI MAIC"}


def _is_native_format(requested: str) -> bool:
    """Whether this format is built by maic rather than by KCC.

    The native formats share a pipeline and write their own containers, so they
    are the ones that still work when modules/ is empty.  "KFX maic" needs the
    bundled kfxlib on top of that, which is checked where it is used.
    """
    return (_is_native_epub_format(requested) or _is_native_mobi_format(requested)
            or _is_native_kfx_mobi_format(requested)
            or str(requested or "").strip().upper() == "KFX MAIC")


def _native_device_canvas(payload: dict[str, Any]) -> str | tuple[int, int]:
    """What the native writers should be handed as their device screen.

    Normally the profile key, which ``device_canvas`` looks up.  KCC's free-size
    profile has no screen of its own -- the width and height are typed into the
    UI beside it -- so for that one the numbers are passed straight through
    instead, and a profile picked without them falls back to the default rather
    than handing the pipeline a zero to divide by.
    """
    profile = str(payload.get("profile", "") or "").strip()
    width = as_int(payload.get("custom_width", 0), 0)
    height = as_int(payload.get("custom_height", 0), 0)
    if width > 0 and height > 0 and (not profile or profile.upper() == "OTHER"):
        return width, height
    if profile.upper() == "OTHER":
        # Asked for a free size and gave none: the default screen is a better
        # answer than a crash, and the log line above it says which was used.
        return "KPW12"
    return profile or "KPW12"


def _native_source_blocker(source: str, payload: dict[str, Any]) -> str:
    """Why this source cannot take the native path, or "" when it can.

    The native walk reads a directory of images and ZIP/CBZ chapter files.
    Anything else -- a source archive, another archived-chapter format, webtoon
    mode, output splitting -- goes the KCC way instead, because producing a
    book that quietly ignores one of them is worse than being slower.
    """
    if not os.path.isdir(source):
        return "source is a file, not a folder of images"
    if bool(payload.get("webtoon", False)):
        return "webtoon mode"
    if as_int(payload.get("batch_split", 0), 0) or as_int(payload.get("chunk_size", 0), 0):
        return "output splitting (batch split / target size)"
    archive_exts = {".rar", ".cbr", ".7z", ".cb7", ".pdf"}
    for root, _, files in os.walk(source):
        for name in files:
            if os.path.splitext(name)[1].lower() in archive_exts:
                return f"archived chapter: {name}"
        del root

    return ""


def _run_native_dir_to_kfx(
    source: str,
    out_kfx_path: str,
    *,
    payload: dict[str, Any],
    title: str = "",
    author: str = "",
    excluded: list[str] | None = None,
    nocrop: list[str] | None = None,
    custom_crops: dict[str, Any] | None = None,
    custom_splits: dict[str, Any] | None = None,
    edit_ops: dict[str, Any] | None = None,
    extra_margin: dict[str, Any] | None = None,
    watermark_matches: list[str] | None = None,
    log_fn: Any = None,
    status_fn: Callable[[str, int | None], None] | None = None,
    stop_requested_fn: Callable[[], bool] | None = None,
) -> tuple[int, str]:
    """Build KFX from a supported image folder without KCC or Kindle Previewer.

    maic processes pages and constructs KFX fragments itself. Final Ion/YJ
    container serialization uses the separately supplied kfxlib module.
    """
    def _log(msg: str) -> None:
        if log_fn:
            log_fn(f"  [KFX maic] {msg}")

    kfxlib_dir = _find_kfxlib_output_dir()
    if not kfxlib_dir:
        return 1, "bundled kfxlib not found (modules/KFX/output)"

    restore_shim = _install_kfxlib_calibre_shim()
    added: list[str] = []
    try:
        if kfxlib_dir not in sys.path:
            sys.path.insert(0, kfxlib_dir)
            added.append(kfxlib_dir)
        # kfxlib imports pypdf, which ships vendored inside the plugin.
        plugin_modules = os.path.join(kfxlib_dir, "kfxlib", "calibre-plugin-modules")
        if os.path.isdir(plugin_modules) and plugin_modules not in sys.path:
            sys.path.insert(0, plugin_modules)
            added.append(plugin_modules)

        from kfxlib import set_logger  # type: ignore[import-not-found]
        from ._kfx_native import build_kfx_from_dir

        class _Log:
            def info(self, msg: object) -> None:
                pass

            def warning(self, msg: object) -> None:
                _log(f"WARN: {msg}")

            def error(self, msg: object) -> None:
                _log(f"ERROR: {msg}")

            def debug(self, msg: object) -> None:
                pass

        set_logger(_Log())

        no_processing = bool(payload.get("no_processing", False))

        def _on_page(done: int, total: int) -> None:
            if status_fn is None or not total:
                return
            # Page work is nearly all of the wall clock; the container itself
            # takes seconds.
            status_fn(f"KFX maic: page {done}/{total}", int(done / total * 90))

        build_kfx_from_dir(
            source,
            out_kfx_path,
            title=title or None,
            # Split the resolved author string back into names so the generator
            # joins them with the same separator the EPUB path uses.
            authors=_split_people(author) if author else None,
            vol_prefix=str(payload.get("vol_prefix", "") or "").strip() or "Vol.",
            excluded=list(excluded or []),
            nocrop=list(nocrop or []),
            custom_crops=dict(custom_crops or {}),
            custom_splits=dict(custom_splits or {}),
            edit_ops=dict(edit_ops or {}),
            extra_margin=dict(extra_margin or {}),
            watermark_matches=(None if watermark_matches is None else list(watermark_matches)),
            cde_type=_resolve_kfx_cde_type(str(payload.get("kindle_doc_type", "auto") or "auto")),
            thumbnails="full",
            reading_direction="rtl" if bool(payload.get("manga_mode", False)) else "ltr",
            device_canvas=_native_device_canvas(payload),
            hq=bool(payload.get("hq", False)),
            resize=not no_processing,
            no_padding=bool(payload.get("kfx_no_padding", False)),
            upscale=bool(payload.get("upscale", False)),
            stretch=bool(payload.get("stretch", False)),
            grayscale=not bool(payload.get("force_color", False)),
            page_format="png" if bool(payload.get("force_png", False)) else "jpg",
            mozjpeg=bool(payload.get("mozjpeg", False)),
            split_spreads=not no_processing,
            # "No rotate" reaches the native path too: with it on, a panorama
            # too wide for KCC's bisect threshold is cut in half like any other
            # spread instead of being turned sideways.
            rotate_spreads=not as_bool(payload.get("no_rotate", False)),
            # The app always sends a value; 85 is what it defaults to, and
            # what build_kcc_argv passes KCC, so the two paths match.
            quality=as_int(payload.get("jpeg_quality", 0), 0) or 85,
            borders_color=str(payload.get("borders_color", "none") or "none"),
            crop=bool(payload.get("maic_crop", False)) and not no_processing,
            margin_pct=as_float(payload.get("maic_margin_pct", 0.6), 0.6),
            watermarks=bool(payload.get("maic_watermarks", False)) and not no_processing,
            page_numbers=bool(payload.get("maic_page_numbers", False)) and not no_processing,
            cleanup_method=str(payload.get("cleanup_method", "lama") or "lama"),
            cleanup_padding=as_int(payload.get("cleanup_padding", 2), 2),
            page_number_scope=source,
            # Off / fast / exact; "no processing" ships the source unchanged.
            manga_upscale=0 if no_processing else as_int(payload.get("manga_upscale", 0), 0),
            scan_cleanup=bool(payload.get("scan_cleanup", False)) and not no_processing,
            # Two portrait pages to a section, which is what a landscape screen
            # shows side by side.  The KFX path through Previewer does this
            # unconditionally; here it is a choice, on unless turned off.
            facing_pages=bool(payload.get("facing_pages", True)) and not no_processing,
            # Kindle decides whether to offer the small combined-spread button
            # from the two inner image edges.  Matching one pixel on either
            # side makes known false negatives deterministic on device.
            force_spread_preview=(
                bool(payload.get("force_spread_preview", True)) and not no_processing
            ),
            spread_preview_mode=_spread_preview_mode(payload, no_processing),
            progress_fn=_on_page,
            stop_requested_fn=stop_requested_fn,
            log_fn=_log,
        )
        return 0, "native KFX generated without KCC or Kindle Previewer"
    except UserWarning as exc:
        if str(exc).strip() == "Conversion interrupted.":
            return 130, "Conversion interrupted."
        return 1, traceback.format_exc()
    except Exception:
        return 1, traceback.format_exc()
    finally:
        for entry in added:
            try:
                sys.path.remove(entry)
            except ValueError:
                pass
        try:
            restore_shim()
        except Exception:
            pass


def _is_native_mobi_format(requested: str) -> bool:
    return str(requested or "").strip().upper() == "MOBI MAIC"


def _run_native_dir_to_kfx_mobi(
    source: str,
    out_kfx_path: str,
    out_mobi_path: str,
    *,
    payload: dict[str, Any],
    title: str = "",
    author: str = "",
    excluded: list[str] | None = None,
    nocrop: list[str] | None = None,
    custom_crops: dict[str, Any] | None = None,
    custom_splits: dict[str, Any] | None = None,
    edit_ops: dict[str, Any] | None = None,
    extra_margin: dict[str, Any] | None = None,
    watermark_matches: list[str] | None = None,
    log_fn: Any = None,
    status_fn: Callable[[str, int | None], None] | None = None,
    stop_requested_fn: Callable[[], bool] | None = None,
) -> tuple[int, str]:
    """Prepare native pages once, then serialize KFX followed by MOBI."""
    def _log(message: str) -> None:
        if log_fn:
            log_fn(f"  [KFX + MOBI maic] {message}")

    kfxlib_dir = _find_kfxlib_output_dir()
    if not kfxlib_dir:
        return 1, "bundled kfxlib not found (modules/KFX/output)"

    restore_shim = _install_kfxlib_calibre_shim()
    added: list[str] = []
    try:
        if kfxlib_dir not in sys.path:
            sys.path.insert(0, kfxlib_dir)
            added.append(kfxlib_dir)
        plugin_modules = os.path.join(kfxlib_dir, "kfxlib", "calibre-plugin-modules")
        if os.path.isdir(plugin_modules) and plugin_modules not in sys.path:
            sys.path.insert(0, plugin_modules)
            added.append(plugin_modules)

        from kfxlib import set_logger  # type: ignore[import-not-found]
        from ._native_combo import build_kfx_mobi_from_dir

        class _Log:
            def info(self, msg: object) -> None:
                pass

            def warning(self, msg: object) -> None:
                _log(f"WARN: {msg}")

            def error(self, msg: object) -> None:
                _log(f"ERROR: {msg}")

            def debug(self, msg: object) -> None:
                pass

        set_logger(_Log())
        no_processing = bool(payload.get("no_processing", False))

        def _on_page(done: int, total: int) -> None:
            if status_fn is not None and total:
                status_fn(
                    f"KFX + MOBI maic: preparing page {done}/{total}",
                    int(done / total * 88),
                )

        def _on_stage(message: str, percent: int) -> None:
            if status_fn is not None:
                status_fn(f"KFX + MOBI maic: {message}", percent)

        build_kfx_mobi_from_dir(
            source,
            out_kfx_path,
            out_mobi_path,
            title=title or None,
            authors=_split_people(author) if author else None,
            vol_prefix=str(payload.get("vol_prefix", "") or "").strip() or "Vol.",
            excluded=list(excluded or []),
            nocrop=list(nocrop or []),
            custom_crops=dict(custom_crops or {}),
            custom_splits=dict(custom_splits or {}),
            edit_ops=dict(edit_ops or {}),
            extra_margin=dict(extra_margin or {}),
            watermark_matches=(None if watermark_matches is None else list(watermark_matches)),
            cde_type=_resolve_kfx_cde_type(str(payload.get("kindle_doc_type", "auto") or "auto")),
            reading_direction="rtl" if bool(payload.get("manga_mode", False)) else "ltr",
            device_canvas=_native_device_canvas(payload),
            hq=bool(payload.get("hq", False)),
            resize=not no_processing,
            no_padding=bool(payload.get("kfx_no_padding", False)),
            upscale=bool(payload.get("upscale", False)),
            stretch=bool(payload.get("stretch", False)),
            grayscale=not bool(payload.get("force_color", False)),
            page_format="png" if bool(payload.get("force_png", False)) else "jpg",
            mozjpeg=bool(payload.get("mozjpeg", False)),
            split_spreads=not no_processing,
            rotate_spreads=not as_bool(payload.get("no_rotate", False)),
            quality=as_int(payload.get("jpeg_quality", 0), 0) or 85,
            borders_color=str(payload.get("borders_color", "none") or "none"),
            crop=bool(payload.get("maic_crop", False)) and not no_processing,
            margin_pct=as_float(payload.get("maic_margin_pct", 0.6), 0.6),
            watermarks=bool(payload.get("maic_watermarks", False)) and not no_processing,
            page_numbers=bool(payload.get("maic_page_numbers", False)) and not no_processing,
            cleanup_method=str(payload.get("cleanup_method", "lama") or "lama"),
            cleanup_padding=as_int(payload.get("cleanup_padding", 2), 2),
            page_number_scope=source,
            manga_upscale=0 if no_processing else as_int(payload.get("manga_upscale", 0), 0),
            scan_cleanup=bool(payload.get("scan_cleanup", False)) and not no_processing,
            facing_pages=bool(payload.get("facing_pages", True)) and not no_processing,
            force_spread_preview=(
                bool(payload.get("force_spread_preview", True)) and not no_processing
            ),
            spread_preview_mode=_spread_preview_mode(payload, no_processing),
            progress_fn=_on_page,
            stage_fn=_on_stage,
            stop_requested_fn=stop_requested_fn,
            log_fn=_log,
        )
        return 0, "native KFX and MOBI generated from one prepared page set"
    except UserWarning as exc:
        if str(exc).strip() == "Conversion interrupted.":
            return 130, "Conversion interrupted."
        return 1, traceback.format_exc()
    except Exception:
        return 1, traceback.format_exc()
    finally:
        for entry in added:
            try:
                sys.path.remove(entry)
            except ValueError:
                pass
        try:
            restore_shim()
        except Exception:
            pass


def _run_native_dir_to_mobi(
    source: str,
    out_mobi_path: str,
    *,
    payload: dict[str, Any],
    title: str = "",
    author: str = "",
    excluded: list[str] | None = None,
    nocrop: list[str] | None = None,
    custom_crops: dict[str, Any] | None = None,
    custom_splits: dict[str, Any] | None = None,
    edit_ops: dict[str, Any] | None = None,
    extra_margin: dict[str, Any] | None = None,
    watermark_matches: list[str] | None = None,
    log_fn: Any = None,
    status_fn: Callable[[str, int | None], None] | None = None,
    stop_requested_fn: Callable[[], bool] | None = None,
) -> tuple[int, str]:
    """Source folder -> MOBI, with neither KCC nor kindlegen in the path.

    The sibling of _run_native_dir_to_kfx, and deliberately the same shape: the
    pages are cleaned, cropped, split and sized by the same code, and only the
    container differs.  Unlike the KFX one this needs nothing installed --
    there is no kfxlib equivalent here, so the bytes are written directly.
    """
    def _log(message: str) -> None:
        if log_fn:
            log_fn(f"  [MOBI maic] {message}")

    try:
        from ._mobi_native import build_mobi_from_dir

        no_processing = bool(payload.get("no_processing", False))

        def _on_page(done: int, total: int) -> None:
            if status_fn is None or not total:
                return
            status_fn(f"MOBI maic: page {done}/{total}", int(done / total * 90))

        build_mobi_from_dir(
            source,
            out_mobi_path,
            title=title or None,
            # Split the resolved author string back into names so the generator
            # joins them with the same separator the EPUB path uses.
            authors=_split_people(author) if author else None,
            vol_prefix=str(payload.get("vol_prefix", "") or "").strip() or "Vol.",
            excluded=list(excluded or []),
            nocrop=list(nocrop or []),
            custom_crops=dict(custom_crops or {}),
            custom_splits=dict(custom_splits or {}),
            edit_ops=dict(edit_ops or {}),
            extra_margin=dict(extra_margin or {}),
            watermark_matches=(None if watermark_matches is None else list(watermark_matches)),
            cde_type=_resolve_kfx_cde_type(str(payload.get("kindle_doc_type", "auto") or "auto")),
            reading_direction="rtl" if bool(payload.get("manga_mode", False)) else "ltr",
            device_canvas=_native_device_canvas(payload),
            hq=bool(payload.get("hq", False)),
            resize=not no_processing,
            no_padding=bool(payload.get("kfx_no_padding", False)),
            upscale=bool(payload.get("upscale", False)),
            stretch=bool(payload.get("stretch", False)),
            grayscale=not bool(payload.get("force_color", False)),
            page_format="png" if bool(payload.get("force_png", False)) else "jpg",
            mozjpeg=bool(payload.get("mozjpeg", False)),
            split_spreads=not no_processing,
            # "No rotate" reaches the native path too: with it on, a panorama
            # too wide for KCC's bisect threshold is cut in half like any other
            # spread instead of being turned sideways.
            rotate_spreads=not as_bool(payload.get("no_rotate", False)),
            # The app always sends a value; 85 is what it defaults to, and
            # what build_kcc_argv passes KCC, so the two paths match.
            quality=as_int(payload.get("jpeg_quality", 0), 0) or 85,
            borders_color=str(payload.get("borders_color", "none") or "none"),
            crop=bool(payload.get("maic_crop", False)) and not no_processing,
            margin_pct=as_float(payload.get("maic_margin_pct", 0.6), 0.6),
            watermarks=bool(payload.get("maic_watermarks", False)) and not no_processing,
            page_numbers=bool(payload.get("maic_page_numbers", False)) and not no_processing,
            cleanup_method=str(payload.get("cleanup_method", "lama") or "lama"),
            cleanup_padding=as_int(payload.get("cleanup_padding", 2), 2),
            page_number_scope=source,
            # Off / fast / exact; "no processing" ships the source unchanged.
            manga_upscale=0 if no_processing else as_int(payload.get("manga_upscale", 0), 0),
            scan_cleanup=bool(payload.get("scan_cleanup", False)) and not no_processing,
            # KCC-style synthetic spreads are on by default.  Each image still
            # gets its own KF8 skeleton; RESC supplies the left/right pairing,
            # so this never creates a double-width XHTML viewport.
            facing_pages=bool(payload.get("facing_pages", True)) and not no_processing,
            progress_fn=_on_page,
            stop_requested_fn=stop_requested_fn,
            log_fn=_log,
        )
        return 0, "native MOBI generated without KCC or kindlegen"
    except UserWarning as exc:
        if str(exc).strip() == "Conversion interrupted.":
            return 130, "Conversion interrupted."
        return 1, traceback.format_exc()
    except Exception:
        return 1, traceback.format_exc()


def _is_native_epub_format(requested: str) -> bool:
    return str(requested or "").strip().upper() == "EPUB MAIC"


def _run_native_dir_to_epub(
    source: str,
    out_epub_path: str,
    *,
    payload: dict[str, Any],
    title: str = "",
    author: str = "",
    excluded: list[str] | None = None,
    nocrop: list[str] | None = None,
    custom_crops: dict[str, Any] | None = None,
    custom_splits: dict[str, Any] | None = None,
    edit_ops: dict[str, Any] | None = None,
    extra_margin: dict[str, Any] | None = None,
    watermark_matches: list[str] | None = None,
    log_fn: Any = None,
    status_fn: Callable[[str, int | None], None] | None = None,
    stop_requested_fn: Callable[[], bool] | None = None,
) -> tuple[int, str]:
    """Source folder -> EPUB 3 fixed layout, with KCC out of the path.

    The third sibling of _run_native_dir_to_kfx, and the same shape: the pages
    are cleaned, cropped, split and sized by the same code, and only the
    container differs.  Like the MOBI one it needs nothing installed -- KCC was
    the only thing an EPUB ever depended on here, and this is what drops it.
    """
    def _log(message: str) -> None:
        if log_fn:
            log_fn(f"  [EPUB maic] {message}")

    try:
        from ._epub_native import build_epub_from_dir

        no_processing = bool(payload.get("no_processing", False))

        def _on_page(done: int, total: int) -> None:
            if status_fn is None or not total:
                return
            status_fn(f"EPUB maic: page {done}/{total}", int(done / total * 90))

        build_epub_from_dir(
            source,
            out_epub_path,
            title=title or None,
            # Split the resolved author string back into names so each one
            # becomes its own dc:creator.
            authors=_split_people(author) if author else None,
            vol_prefix=str(payload.get("vol_prefix", "") or "").strip() or "Vol.",
            excluded=list(excluded or []),
            nocrop=list(nocrop or []),
            custom_crops=dict(custom_crops or {}),
            custom_splits=dict(custom_splits or {}),
            edit_ops=dict(edit_ops or {}),
            extra_margin=dict(extra_margin or {}),
            watermark_matches=(None if watermark_matches is None else list(watermark_matches)),
            reading_direction="rtl" if bool(payload.get("manga_mode", False)) else "ltr",
            device_canvas=_native_device_canvas(payload),
            hq=bool(payload.get("hq", False)),
            resize=not no_processing,
            no_padding=bool(payload.get("kfx_no_padding", False)),
            upscale=bool(payload.get("upscale", False)),
            stretch=bool(payload.get("stretch", False)),
            grayscale=not bool(payload.get("force_color", False)),
            page_format="png" if bool(payload.get("force_png", False)) else "jpg",
            mozjpeg=bool(payload.get("mozjpeg", False)),
            split_spreads=not no_processing,
            # "No rotate" reaches the native path too: with it on, a panorama
            # too wide for KCC's bisect threshold is cut in half like any other
            # spread instead of being turned sideways.
            rotate_spreads=not as_bool(payload.get("no_rotate", False)),
            # The app always sends a value; 85 is what it defaults to, and
            # what build_kcc_argv passes KCC, so the two paths match.
            quality=as_int(payload.get("jpeg_quality", 0), 0) or 85,
            borders_color=str(payload.get("borders_color", "none") or "none"),
            crop=bool(payload.get("maic_crop", False)) and not no_processing,
            margin_pct=as_float(payload.get("maic_margin_pct", 0.6), 0.6),
            watermarks=bool(payload.get("maic_watermarks", False)) and not no_processing,
            page_numbers=bool(payload.get("maic_page_numbers", False)) and not no_processing,
            cleanup_method=str(payload.get("cleanup_method", "lama") or "lama"),
            cleanup_padding=as_int(payload.get("cleanup_padding", 2), 2),
            page_number_scope=source,
            # Off / fast / exact; "no processing" ships the source unchanged.
            manga_upscale=0 if no_processing else as_int(payload.get("manga_upscale", 0), 0),
            scan_cleanup=bool(payload.get("scan_cleanup", False)) and not no_processing,
            # Unlike the other two containers, nothing here draws the pair: the
            # spine names the side of the fold each page falls on and the
            # reader puts them side by side.  maic still decides which pages
            # pair, which is what the option is.
            facing_pages=bool(payload.get("facing_pages", True)) and not no_processing,
            # Reaches a Kindle too: Send-to-Kindle turns the EPUB into KFX, and
            # the reader still judges the combined-spread button by the pixels
            # on either side of the cut.
            force_spread_preview=(
                bool(payload.get("force_spread_preview", True)) and not no_processing
            ),
            spread_preview_mode=_spread_preview_mode(payload, no_processing),
            progress_fn=_on_page,
            stop_requested_fn=stop_requested_fn,
            log_fn=_log,
        )
        return 0, "native EPUB generated without KCC"
    except UserWarning as exc:
        if str(exc).strip() == "Conversion interrupted.":
            return 130, "Conversion interrupted."
        return 1, traceback.format_exc()
    except Exception:
        return 1, traceback.format_exc()


def _run_kfxlib_epub_to_kfx(
    epub_path: str,
    out_kfx_path: str,
    *,
    kindle_doc_type: str = "auto",
    reading_direction: str | None = None,
    multi_container: bool = False,
    timeout: int = 600,
    log_fn: Any = None,
    status_fn: Callable[[str, int | None], None] | None = None,
    stop_requested_fn: Callable[[], bool] | None = None,
    use_windows_console_capture: bool = True,
) -> tuple[int, str]:
    """Convert EPUB -> KFX using bundled kfxlib (KPR CLI + repack)."""
    def _is_stop_requested() -> bool:
        try:
            return bool(stop_requested_fn is not None and stop_requested_fn())
        except Exception:
            return False

    def _update_status(phase: str, progress: int | None = None) -> None:
        try:
            if status_fn is not None:
                status_fn(phase, progress)
        except Exception:
            pass

    kfxlib_dir = _find_kfxlib_output_dir()
    if not kfxlib_dir:
        return 1, "Bundled kfxlib not found at modules/KFX/output"

    sys_path_added = False
    restore_shim: Callable[[], None] = lambda: None
    stripped_input: str | None = None
    gkc: Any | None = None
    orig_wait_for_completion: Any | None = None
    kpr_cli_process: Any | None = None
    orig_use_wincon: bool | None = None
    # Kindle Previewer has a much smaller effective path limit than modern
    # Windows APIs. Keep its nested cTemp/mTemp workspace under a short system
    # temp root instead of nesting it beside an arbitrarily deep output path.
    tmp_dir = tempfile.mkdtemp(prefix="maic_kfxlib_")
    tmp_kpf = os.path.join(tmp_dir, "stage.kpf")

    old_tmp = os.environ.get("TMP")
    old_temp = os.environ.get("TEMP")

    try:
        os.environ["TMP"] = tmp_dir
        os.environ["TEMP"] = tmp_dir

        restore_shim = _install_kfxlib_calibre_shim()

        if kfxlib_dir not in sys.path:
            sys.path.insert(0, kfxlib_dir)
            sys_path_added = True

        plugin_modules = os.path.join(kfxlib_dir, "kfxlib", "calibre-plugin-modules")
        if os.path.isdir(plugin_modules) and plugin_modules not in sys.path:
            sys.path.insert(0, plugin_modules)

        from kfxlib import YJ_Book, file_write_binary  # type: ignore[import-not-found]
        from kfxlib import generate_kpf_common as gkc  # type: ignore[import-not-found]
        from kfxlib.generate_kpf_using_cli import KPR_CLI_Process as kpr_cli_process  # type: ignore[import-not-found]

        orig_wait_for_completion = gkc.ConversionProcess.wait_for_completion
        orig_use_wincon = bool(kpr_cli_process.use_wincon)
        if not use_windows_console_capture:
            kpr_cli_process.use_wincon = False

        def _wait_for_completion_with_stop(self):
            start_time = time.time()
            timeout_reached = False
            cancelled = False

            while self.process.poll() is None:
                if self.wincon is not None:
                    self.wincon.restore_original_console_buffer_on_change()

                if _is_stop_requested() and not cancelled:
                    gkc.log.warning("Killing process due to stop request")
                    cancelled = True
                    try:
                        if getattr(gkc, "psutil", None) is not None:
                            parent = gkc.psutil.Process(self.process.pid)
                            children = parent.children(recursive=True)
                            for child in children:
                                child.kill()
                            gkc.psutil.wait_procs(children, timeout=5)
                            parent.kill()
                        else:
                            self.process.kill()
                    except Exception as exc:
                        self.error("Failed to kill conversion process: %s" % repr(exc))

                if self.timeout_sec and (time.time() - start_time > self.timeout_sec) and not timeout_reached:
                    timeout_reached = True
                    try:
                        if getattr(gkc, "psutil", None) is not None:
                            parent = gkc.psutil.Process(self.process.pid)
                            children = parent.children(recursive=True)
                            for child in children:
                                child.kill()
                            gkc.psutil.wait_procs(children, timeout=5)
                            parent.kill()
                        else:
                            self.process.kill()
                    except Exception as exc:
                        self.error("Failed to kill conversion process: %s" % repr(exc))

                time.sleep(gkc.CONVERSION_SLEEP_SEC)

            duration = time.time() - start_time
            if duration > gkc.LOG_CONVERSION_DURATION_SEC:
                gkc.log.info("Conversion process took %d seconds" % duration)

            time.sleep(gkc.COMPLETION_SLEEP_SEC)

            if self.wincon is not None:
                self.wincon.restore_original_console_buffer()
                self.write_out_file(self.wincon.get_alternate_console_data())
                self.wincon.free_alternate_console_buffer()

            if cancelled:
                self.returncode = -1
                self.error("Process Terminated: %s cancelled by stop request" % self.function_name)
            elif timeout_reached:
                self.returncode = -1
                self.error(
                    "Process Terminated: %s did not complete within %d seconds"
                    % (self.function_name, self.timeout_sec)
                )
            else:
                self.returncode = self.process.returncode & 0xFFFFFFFF
                if self.returncode:
                    self.error("Process Failure: %s return code %08x" % (self.function_name, self.returncode))
                else:
                    self.process_failure = False

            self.out_file.close()
            self.output = gkc.file_read_utf8(self.out_file_name).rstrip()

            if self.log_output:
                gkc.log.info(self.output)
            else:
                self.log_data[os.path.basename(self.out_file_name)] = self.output

        gkc.ConversionProcess.wait_for_completion = _wait_for_completion_with_stop

        # KPR CLI often returns MOBI-only for fixed-layout EPUB. Stripping
        # fixed-layout OPF markers keeps ET path enabled, then KFX metadata
        # is restored in post-process.
        conv_input = _strip_fixed_layout_from_epub(epub_path) or epub_path
        if conv_input != epub_path:
            stripped_input = conv_input
            if log_fn:
                log_fn("  [KFX] Using stripped EPUB input for KPR ET compatibility")

        if log_fn:
            log_fn("  [KFX] Stage 1/2: Kindle Previewer conversion (KPF)")
        _update_status("KFX Stage 1/2: Kindle Previewer conversion", 92)
        conv_box: dict[str, Any] = {"result": None, "error": None, "trace": ""}
        done = threading.Event()

        def _run_kpr_stage() -> None:
            try:
                conv_box["result"] = YJ_Book(conv_input).convert_to_kpf(timeout_sec=timeout)
            except Exception as exc:
                conv_box["error"] = exc
                conv_box["trace"] = traceback.format_exc()
            finally:
                done.set()

        started_at = time.time()
        worker = threading.Thread(target=_run_kpr_stage, daemon=True)
        worker.start()
        _KPR_PROGRESS_PREFIX = "  [KFX] Kindle Previewer conversion in progress... "
        while not done.wait(1.0):
            if log_fn:
                elapsed = int(time.time() - started_at)
                bar = _format_kfx_progress_bar(elapsed, width=24, step_seconds=10)
                msg = f"{_KPR_PROGRESS_PREFIX}{bar}"
                # Update last log line in-place if it's a progress bar.
                with state_lock:
                    log_list = state.get("convert_log")
                    if (log_list
                            and isinstance(log_list, list)
                            and log_list[-1].startswith(_KPR_PROGRESS_PREFIX)):
                        log_list[-1] = msg
                    else:
                        log_fn(msg)
                _update_status(f"KFX Stage 1/2: Kindle Previewer conversion {bar}", 92)
            if _is_stop_requested():
                worker.join(timeout=5.0)
                return 130, "Conversion interrupted."
        worker.join()

        if _is_stop_requested():
            return 130, "Conversion interrupted."

        if conv_box["error"] is not None:
            return 1, str(conv_box.get("trace") or conv_box["error"])
        conv = conv_box["result"]
        if conv is None:
            return 1, "kfxlib conversion returned no result"
        if not conv.kpf_data:
            err = (conv.error_msg or "kfxlib failed to generate KPF").strip()
            if conv.guidance:
                err += "\n" + "\n".join(conv.guidance.splitlines()[:10])
            if stripped_input:
                err = "Using stripped EPUB input for KPR ET compatibility\n" + err
            return 1, err

        file_write_binary(tmp_kpf, conv.kpf_data)
        if log_fn:
            log_fn("  [KFX] Stage 2/2: Packing KFX + post-processing (in-process)")
        _update_status("KFX Stage 2/2: Packing KFX + post-processing", 97)

        from kfxlib import YJ_Metadata  # type: ignore[import-not-found]
        from ._kfx_postprocess import postprocess_kfx_book

        cde_type = _resolve_kfx_cde_type(kindle_doc_type)
        explicit_split_pairs = _extract_explicit_split_pairs_meta_from_epub(epub_path)
        epub_first_spine_is_cover = _epub_first_spine_is_cover(epub_path)
        if log_fn:
            log_fn(
                "  [KFX META] Explicit split pairs detected for KFX postprocess: "
                f"{len(explicit_split_pairs)}"
            )
            if epub_first_spine_is_cover is not None:
                log_fn(
                    "  [KFX META] EPUB first spine cover detected: "
                    f"{'yes' if epub_first_spine_is_cover else 'no'}"
                )
        md = YJ_Metadata()
        md.cde_content_type = cde_type
        md.asin = True
        md.authors = None

        book = YJ_Book(tmp_kpf)
        book.decode_book(set_metadata=md, set_approximate_pages=-1)

        def _pp_log(msg):
            if log_fn:
                log_fn(f"  [KFX] {msg}")

        postprocess_kfx_book(
            book,
            cde_type=cde_type,
            reading_direction=reading_direction,
            enable_facing=True,
            merge_adjacent_pairs=True,
            explicit_split_pairs=explicit_split_pairs,
            epub_first_spine_is_cover=epub_first_spine_is_cover,
            log_fn=_pp_log,
        )

        if _is_stop_requested():
            return 130, "Conversion interrupted."

        if multi_container:
            from ._kfx_postprocess import convert_book_to_kfx_files
            out_files = convert_book_to_kfx_files(book, out_kfx_path, log_fn=_pp_log)
            if not out_files:
                return 1, "convert_book_to_kfx_files returned no output"
            msg = f"kfxlib packed KFX +sdr ({cde_type}), {len(out_files)} file(s)"
        else:
            kfx_data = book.convert_to_single_kfx()
            if not kfx_data:
                return 1, "kfxlib convert_to_single_kfx returned empty result"
            file_write_binary(out_kfx_path, kfx_data)
            msg = f"kfxlib packed KFX ({cde_type}) with post-processing"

        if stripped_input:
            msg = "Using stripped EPUB input for KPR ET compatibility\n" + msg
        return 0, msg
    except Exception:
        return 1, traceback.format_exc()
    finally:
        if gkc is not None and orig_wait_for_completion is not None:
            try:
                gkc.ConversionProcess.wait_for_completion = orig_wait_for_completion
            except Exception:
                pass
        if kpr_cli_process is not None and orig_use_wincon is not None:
            try:
                kpr_cli_process.use_wincon = orig_use_wincon
            except Exception:
                pass
        if old_tmp is None:
            os.environ.pop("TMP", None)
        else:
            os.environ["TMP"] = old_tmp
        if old_temp is None:
            os.environ.pop("TEMP", None)
        else:
            os.environ["TEMP"] = old_temp

        try:
            restore_shim()
        except Exception:
            pass

        if sys_path_added:
            try:
                sys.path.remove(kfxlib_dir)
            except ValueError:
                pass
        if stripped_input:
            try:
                os.remove(stripped_input)
            except Exception:
                pass
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


_FL_STRIP_NAMES = frozenset({
    "book-type", "fixed-layout", "original-resolution",
    "region-mag", "zero-gutter", "zero-margin",
    "ke-border-color", "ke-border-width", "orientation-lock",
})
_FL_STRIP_PROPERTIES = frozenset({
    "rendition:layout", "rendition:spread", "rendition:orientation",
})


def _strip_fixed_layout_from_epub(epub_path: str) -> str | None:
    """Create a temp copy of *epub_path* with ALL fixed-layout metadata removed.

    Kindle Previewer rejects *any* fixed-layout EPUB for Enhanced Typesetting,
    not just comics.  Stripping every fixed-layout indicator lets the CLI
    conversion produce a KPF/KFX that we then post-process to re-inject the
    comic capability metadata at the KFX level.

    Returns the temp file path, or *None* on failure.
    """
    import tempfile

    opf_rel = _find_epub_opf_path(epub_path)
    if not opf_rel:
        return None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".epub", delete=False)
        tmp_path = tmp.name
        tmp.close()
        with zipfile.ZipFile(epub_path, "r") as zin, zipfile.ZipFile(tmp_path, "w") as zout:
            for info in zin.infolist():
                raw = zin.read(info.filename)
                if info.filename == opf_rel:
                    root = ET.fromstring(raw)
                    ns_opf = "http://www.idpf.org/2007/opf"
                    for md in root.iter():
                        if _xml_local_name(md.tag) != "metadata":
                            continue
                        for m in list(md.findall(f"{{{ns_opf}}}meta")):
                            name = str(m.attrib.get("name", "")).strip().lower()
                            prop = str(m.attrib.get("property", "")).strip().lower()
                            if name in _FL_STRIP_NAMES or prop in _FL_STRIP_PROPERTIES:
                                md.remove(m)
                    raw = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                zout.writestr(info, raw)
        return tmp_path
    except Exception:
        return None


def _discover_recent_files(root_dir: str, since_ts: float, exts: set[str]) -> list[str]:
    out: list[str] = []
    if not os.path.isdir(root_dir):
        return out
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in exts:
                continue
            fp = os.path.join(dirpath, name)
            try:
                if os.path.getmtime(fp) >= since_ts:
                    out.append(fp)
            except Exception:
                continue
    out.sort(key=lambda p: os.path.getmtime(p) if os.path.isfile(p) else 0, reverse=True)
    return out


def _find_epub_opf_path(epub_path: str) -> str:
    try:
        with zipfile.ZipFile(epub_path, "r") as zf:
            if "META-INF/container.xml" in zf.namelist():
                container = zf.read("META-INF/container.xml")
                root = ET.fromstring(container)
                for elem in root.iter():
                    if _xml_local_name(elem.tag) != "rootfile":
                        continue
                    full_path = str(elem.attrib.get("full-path", "") or "").strip()
                    if full_path:
                        return full_path
            for name in zf.namelist():
                if name.lower().endswith(".opf"):
                    return name
    except Exception:
        return ""
    return ""


def _extract_explicit_split_pairs_meta_from_epub(epub_path: str) -> list[dict[str, int]]:
    """Extract split pairs with optional image-size hints from EPUB spine.

    Returned items are dictionaries with at least:
      ``left_idx`` and ``right_idx`` (0-based spine indexes)
    and, when resolvable from XHTML -> IMG, size hints:
      ``left_w``, ``left_h``, ``right_w``, ``right_h``.
    """
    opf_rel = _find_epub_opf_path(epub_path)
    if not opf_rel:
        return []
    try:
        with zipfile.ZipFile(epub_path, "r") as zin:
            opf_bytes = zin.read(opf_rel)
            root = ET.fromstring(opf_bytes)

            manifest_map: dict[str, str] = {}
            spine = None
            for elem in root.iter():
                local = _xml_local_name(elem.tag)
                if local == "item":
                    item_id = str(elem.attrib.get("id", "") or "").strip()
                    href = str(elem.attrib.get("href", "") or "").strip()
                    if item_id and href:
                        manifest_map[item_id] = href
                elif local == "spine" and spine is None:
                    spine = elem

            if spine is None:
                return []

            itemrefs = [elem for elem in list(spine) if _xml_local_name(elem.tag) == "itemref"]
            opf_dir = posixpath.dirname(opf_rel.replace("\\", "/"))

            def _zip_norm(path: str) -> str:
                p = path.replace("\\", "/")
                if opf_dir:
                    p = posixpath.join(opf_dir, p)
                return posixpath.normpath(p).lstrip("/")

            def _img_size_from_xhtml(href: str) -> tuple[int, int] | None:
                try:
                    xhtml_path = _zip_norm(href)
                    x_root = ET.fromstring(zin.read(xhtml_path))
                    img_src = ""
                    for node in x_root.iter():
                        if _xml_local_name(node.tag) == "img":
                            img_src = str(node.attrib.get("src", "") or "").strip()
                            if img_src:
                                break
                    if not img_src:
                        return None
                    img_path = posixpath.normpath(
                        posixpath.join(posixpath.dirname(xhtml_path), img_src.replace("\\", "/"))
                    ).lstrip("/")
                    data = zin.read(img_path)
                    with Image.open(io.BytesIO(data)) as img:
                        return int(img.width), int(img.height)
                except Exception:
                    return None

            pairs: list[dict[str, int]] = []
            for idx in range(len(itemrefs) - 1):
                cur = itemrefs[idx]
                nxt = itemrefs[idx + 1]
                cur_id = str(cur.attrib.get("idref", "") or "").strip()
                nxt_id = str(nxt.attrib.get("idref", "") or "").strip()
                cur_href = manifest_map.get(cur_id, "").replace("\\", "/").strip()
                nxt_href = manifest_map.get(nxt_id, "").replace("\\", "/").strip()
                cur_l = cur_href.lower()
                nxt_l = nxt_href.lower()
                if not (cur_l.endswith("-kcc-b.xhtml") and nxt_l.endswith("-kcc-c.xhtml")):
                    continue

                entry: dict[str, int] = {
                    "left_idx": idx,
                    "right_idx": idx + 1,
                }
                left_size = _img_size_from_xhtml(cur_href)
                right_size = _img_size_from_xhtml(nxt_href)
                if left_size is not None:
                    entry["left_w"], entry["left_h"] = left_size
                if right_size is not None:
                    entry["right_w"], entry["right_h"] = right_size
                pairs.append(entry)
            return pairs
    except Exception:
        return []



def _epub_first_spine_is_cover(epub_path: str) -> bool | None:
    """Return whether the first EPUB spine item looks like a cover page.

    Returns:
      - ``True``  if first spine item id/href indicates cover
      - ``False`` if first spine item resolved but does not look like cover
      - ``None``  if EPUB spine cannot be resolved
    """
    opf_rel = _find_epub_opf_path(epub_path)
    if not opf_rel:
        return None
    try:
        with zipfile.ZipFile(epub_path, "r") as zin:
            opf_bytes = zin.read(opf_rel)
        root = ET.fromstring(opf_bytes)
    except Exception:
        return None

    manifest_map: dict[str, str] = {}
    first_idref = ""
    for elem in root.iter():
        local = _xml_local_name(elem.tag)
        if local == "item":
            item_id = str(elem.attrib.get("id", "") or "").strip()
            href = str(elem.attrib.get("href", "") or "").strip()
            if item_id and href:
                manifest_map[item_id] = href
        elif local == "itemref" and not first_idref:
            first_idref = str(elem.attrib.get("idref", "") or "").strip()

    if not first_idref:
        return None
    first_href = manifest_map.get(first_idref, "")
    fid_l = first_idref.lower()
    href_l = os.path.basename(first_href.replace("\\", "/")).lower()
    return ("cover" in fid_l) or ("cover" in href_l)


def _ensure_epub_comic_metadata(epub_path: str, manga_mode: bool) -> tuple[bool, list[str]]:
    """
    Ensure EPUB OPF carries comic/fixed-layout hints used by KFX conversion.
    Returns (changed, log_lines).
    """
    logs: list[str] = []
    opf_rel = _find_epub_opf_path(epub_path)
    if not opf_rel:
        return False, ["[KFX META] OPF not found in EPUB; skipped metadata check"]

    try:
        with zipfile.ZipFile(epub_path, "r") as zin:
            opf_bytes = zin.read(opf_rel)
    except Exception as exc:
        return False, [f"[KFX META] Failed reading OPF: {exc}"]

    try:
        root = ET.fromstring(opf_bytes)
    except Exception as exc:
        return False, [f"[KFX META] Invalid OPF XML: {exc}"]

    ns_opf = "http://www.idpf.org/2007/opf"
    metadata = None
    spine = None
    for elem in root.iter():
        local = _xml_local_name(elem.tag)
        if local == "metadata" and metadata is None:
            metadata = elem
        elif local == "spine" and spine is None:
            spine = elem
    if metadata is None:
        package = root
        metadata = ET.SubElement(package, f"{{{ns_opf}}}metadata")
        logs.append("[KFX META] Added missing <metadata> section")

    def _set_meta_name(name: str, content: str):
        nonlocal metadata
        target = None
        for m in metadata.findall(f"{{{ns_opf}}}meta"):
            if str(m.attrib.get("name", "")).strip().lower() == name.lower():
                target = m
                break
        if target is None:
            target = ET.SubElement(metadata, f"{{{ns_opf}}}meta")
            target.set("name", name)
            target.set("content", content)
            logs.append(f"[KFX META] Added meta name={name} content={content}")
            return
        old = str(target.attrib.get("content", "") or "")
        if old != content:
            target.set("content", content)
            logs.append(f"[KFX META] Updated meta name={name}: {old!r} -> {content!r}")

    def _set_meta_property(prop: str, value: str):
        nonlocal metadata
        target = None
        for m in metadata.findall(f"{{{ns_opf}}}meta"):
            if str(m.attrib.get("property", "")).strip().lower() == prop.lower():
                target = m
                break
        if target is None:
            target = ET.SubElement(metadata, f"{{{ns_opf}}}meta")
            target.set("property", prop)
            target.text = value
            logs.append(f"[KFX META] Added meta property={prop} value={value}")
            return
        old = str(target.text or "")
        if old != value:
            target.text = value
            logs.append(f"[KFX META] Updated meta property={prop}: {old!r} -> {value!r}")

    _set_meta_name("fixed-layout", "true")
    _set_meta_name("book-type", "comic")
    _set_meta_name("zero-gutter", "true")
    _set_meta_name("zero-margin", "true")
    _set_meta_name("region-mag", "false")
    _set_meta_name("ke-border-color", "#FFFFFF")
    _set_meta_name("ke-border-width", "0")
    _set_meta_name("orientation-lock", "none")
    _set_meta_property("rendition:layout", "pre-paginated")
    _set_meta_property("rendition:spread", "auto")
    _set_meta_property("rendition:orientation", "auto")

    if manga_mode:
        _set_meta_name("primary-writing-mode", "horizontal-rl")
        desired_ppd = "rtl"
    else:
        _set_meta_name("primary-writing-mode", "horizontal-lr")
        desired_ppd = "ltr"

    if spine is not None:
        old_ppd = str(spine.attrib.get("page-progression-direction", "") or "")
        if old_ppd.lower() != desired_ppd:
            spine.set("page-progression-direction", desired_ppd)
            logs.append(
                f"[KFX META] Updated spine page-progression-direction: {old_ppd!r} -> {desired_ppd!r}"
            )

        # Normalize split-page facing properties for KCC split pairs (-kcc-b / -kcc-c).
        manifest_map: dict[str, str] = {}
        for elem in root.iter():
            if _xml_local_name(elem.tag) != "item":
                continue
            item_id = str(elem.attrib.get("id", "") or "").strip()
            href = str(elem.attrib.get("href", "") or "").strip()
            if item_id and href:
                manifest_map[item_id] = href

        def _normalize_itemref_spread(itemref: ET.Element, expected: str) -> bool:
            old_props = str(itemref.attrib.get("properties", "") or "").strip()
            keep: list[str] = []
            for token in old_props.split():
                tok = token.strip()
                if not tok:
                    continue
                if tok in {
                    "page-spread-left",
                    "page-spread-right",
                    "rendition:page-spread-left",
                    "rendition:page-spread-right",
                }:
                    continue
                keep.append(tok)
            new_props = " ".join(keep + [expected]).strip()
            if old_props == new_props:
                return False
            itemref.set("properties", new_props)
            return True

        itemrefs = [elem for elem in list(spine) if _xml_local_name(elem.tag) == "itemref"]
        pairs_total = 0
        pairs_fixed = 0
        for idx in range(len(itemrefs) - 1):
            cur = itemrefs[idx]
            nxt = itemrefs[idx + 1]
            cur_id = str(cur.attrib.get("idref", "") or "").strip()
            nxt_id = str(nxt.attrib.get("idref", "") or "").strip()
            cur_href = manifest_map.get(cur_id, "").lower()
            nxt_href = manifest_map.get(nxt_id, "").lower()
            if not (cur_href.endswith("-kcc-b.xhtml") and nxt_href.endswith("-kcc-c.xhtml")):
                continue
            pairs_total += 1
            first_expected = "page-spread-right" if manga_mode else "page-spread-left"
            second_expected = "page-spread-left" if manga_mode else "page-spread-right"
            changed = _normalize_itemref_spread(cur, first_expected)
            changed = _normalize_itemref_spread(nxt, second_expected) or changed
            if changed:
                pairs_fixed += 1

        if pairs_total:
            logs.append(
                f"[KFX META] Split facing pairs normalized: {pairs_fixed}/{pairs_total}"
            )
    else:
        logs.append("[KFX META] <spine> not found; page progression not updated")

    if not logs:
        return False, ["[KFX META] Comic metadata already valid"]

    new_opf = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    tmp_epub = epub_path + ".maic_meta_tmp"
    try:
        with zipfile.ZipFile(epub_path, "r") as zin, zipfile.ZipFile(tmp_epub, "w") as zout:
            for info in zin.infolist():
                data = new_opf if info.filename == opf_rel else zin.read(info.filename)
                zout.writestr(info, data)
        os.replace(tmp_epub, epub_path)
        logs.insert(0, "[KFX META] EPUB OPF metadata normalized for comic conversion")
    except Exception as exc:
        try:
            if os.path.isfile(tmp_epub):
                os.remove(tmp_epub)
        except Exception:
            pass
        return False, [f"[KFX META] Failed to write normalized OPF: {exc}"]

    return True, logs


def _resolve_convert_title_author(data: dict[str, Any], source: str) -> tuple[str, str]:
    explicit_title = str(data.get("title", "") or "").strip()
    explicit_author = str(data.get("author", "") or "").strip()
    if explicit_title and explicit_author:
        return explicit_title, explicit_author
    vol_prefix = str(data.get("vol_prefix", "") or "").strip() or "Vol."
    ci_title, ci_author = _read_comicinfo_title_author(source, vol_prefix=vol_prefix)
    return explicit_title or ci_title, explicit_author or ci_author

def _get_profiles() -> dict[str, Any] | None:
    """Load KCC device profiles in GUI-compatible grouping/order.

    Without KCC this is the short table in maic/_device_profiles.py instead of
    nothing: the native formats run no KCC code, and the only reason
    they ever needed it here was to look a screen size up.
    """
    from .config import KCC_AVAILABLE

    # Still worth running without KCC: besides putting KCC on sys.path it is
    # what finds 7-Zip and kindlegen and puts them on PATH, and the endpoint
    # around this reports both.
    ensure_kcc_path()
    if not KCC_AVAILABLE:
        from ._device_profiles import native_profile_groups

        return native_profile_groups()
    ensure_kcc_deps()
    try:
        from .kcc_patch import _install_preserve_margin_hv_patch
        _install_preserve_margin_hv_patch()
        from kindlecomicconverter.image import ProfileData

        def _info(key: str) -> dict[str, Any] | None:
            data = ProfileData.Profiles.get(key)
            if not data:
                return None
            w, h = data[1]
            gamma = data[3] if len(data) > 3 else 1.0
            return {"width": w, "height": h, "gamma": gamma}

        ordered = {
            "Kindle": [
                ("Kindle Scribe Colorsoft", "KSCS"),
                ("Kindle Scribe 3", "KS3"),
                ("Kindle Colorsoft", "KCS"),
                ("Kindle Paperwhite 12", "KPW12"),
                ("Kindle Scribe 1/2", "KS"),
                ("Kindle Paperwhite 11", "KPW5"),
                ("Kindle 11", "K11"),
                ("Kindle Oasis 9/10", "KO"),
            ],
            "Kindle Legacy": [
                ("Kindle 1920x1920", "KS1920"),
                ("Kindle 1860x1920", "KS1860"),
                ("Kindle 1240x1860", "KS1240"),
                ("Kindle 8/10", "K810"),
                ("Kindle Oasis 8", "KPW34"),
                ("Kindle Paperwhite 7/10", "KPW34"),
                ("Kindle Voyage", "KV"),
                ("Kindle Paperwhite 5/6", "KPW"),
                ("Kindle 4/5/7", "K57"),
                ("Kindle Touch", "K34"),
                ("Kindle Keyboard", "K34"),
                ("Kindle DX", "KDX"),
                ("Kindle 2", "K2"),
                ("Kindle 1", "K1"),
            ],
            "Kobo": [
                ("Kobo Clara 2E", "KoC"),
                ("Kobo Clara Colour", "KoCC"),
                ("Kobo Sage", "KoS"),
                ("Kobo Libra 2", "KoL"),
                ("Kobo Libra Colour", "KoLC"),
                ("Kobo Elipsa", "KoE"),
                ("Kobo Nia", "KoN"),
            ],
            "Kobo Legacy": [
                ("Kobo Aura", "KoA"),
                ("Kobo Aura ONE", "KoAO"),
                ("Kobo Aura H2O", "KoAH2O"),
                ("Kobo Aura HD", "KoAHD"),
                ("Kobo Clara HD", "KoC"),
                ("Kobo Forma", "KoF"),
                ("Kobo Glo HD", "KoGHD"),
                ("Kobo Glo", "KoG"),
                ("Kobo Libra H2O", "KoL"),
                ("Kobo Mini/Touch", "KoMT"),
            ],
            "reMarkable": [
                ("reMarkable 1", "Rmk1"),
                ("reMarkable 2", "Rmk2"),
                ("reMarkable Paper Pro", "RmkPP"),
                ("reMarkable Paper Pro Move", "RmkPPMove"),
            ],
            "Other": [("Other", "OTHER")],
        }

        groups: dict[str, dict[str, Any]] = {}
        for group, items in ordered.items():
            entries: dict[str, Any] = {}
            seen_keys: dict[str, str] = {}
            for display_name, key in items:
                if display_name in seen_keys:
                    continue
                info = _info(key)
                if info:
                    entry_key = display_name.replace(" ", "_").replace("/", "_")
                    info["name"] = display_name
                    info["profile_key"] = key
                    entries[entry_key] = info
                    seen_keys[display_name] = key
            if entries:
                groups[group] = entries

        return groups
    except Exception as exc:
        logger.error(f"KCC profiles error: {exc}")
        return None


def create_convert_blueprint(
    *,
    convert_log: Callable[[str], None],
    get_source_relpaths: Callable[[str], set[str]],
    apply_getworkfolder_patch_fn: Callable[[], None],
    apply_nocrop_patch_fn: Callable[..., Callable[[], None]],
    load_sidecar_for_source: Callable[[str], dict[str, Any]],
) -> Blueprint:
    """Create convert blueprint with injected KCC integration helpers."""

    bp = Blueprint("convert", __name__)

    def _is_convert_stop_requested() -> bool:
        with state_lock:
            return bool(state.get("convert_stop_requested", False))

    @bp.route("/api/convert/profiles", methods=["GET"])
    def api_convert_profiles():
        from .config import KCC_AVAILABLE

        profiles = _get_profiles()
        if profiles is None:
            return jsonify({"profiles": {}, "mobi_available": False,
                            "mobi_tool": None, "mobi_path": "",
                            "kcc_available": False, "native_only": True})
        kg = shutil.which("kindlegen")
        kpr_exe = _find_kpr_exe()
        kfxlib_dir = _find_kfxlib_output_dir()
        sz = find_7z()
        kfx_available = bool(kpr_exe and kfxlib_dir)
        return jsonify(
            {
                "profiles": profiles,
                "mobi_available": kg is not None,
                "mobi_tool": "kindlegen" if kg else None,
                "mobi_path": kg or "",
                "sevenzip_available": sz is not None,
                "previewer_available": bool(kpr_exe),
                "kfx_available": kfx_available,
                "kfx_cli_available": bool(kfxlib_dir),
                "kfx_kpr_path": kpr_exe,
                "kfx_kfxlib_path": kfxlib_dir,
                "kfx_backend": "kpr+kfxlib" if kfx_available else "",
                # Which half of the Conversion tab is usable.  Without KCC the
                # native formats still are, and they are all the tab offers.
                "kcc_available": KCC_AVAILABLE,
                "native_only": not KCC_AVAILABLE,
            }
        )

    @bp.route("/api/convert/status", methods=["GET"])
    def api_convert_status():
        with state_lock:
            snapshot = {
                "converting": state["converting"],
                "stop_requested": bool(state.get("convert_stop_requested", False)),
                "progress": state["convert_progress"],
                "phase": state["convert_phase"],
                "current_file": state["convert_current_file"],
                "total": state["convert_total"],
                "done": state["convert_done"],
                "log": list(state["convert_log"]),
                "output_files": list(state["convert_output_files"]),
                "advanced_log": bool(state.get("convert_advanced_log", False)),
            }
        return jsonify(snapshot)

    @bp.route("/api/convert/log-mode", methods=["POST"])
    def api_convert_log_mode():
        data = json_body()
        ok, message = validate_convert_log_mode_payload(data)
        if not ok:
            return fail(message, code=EC.INVALID_PAYLOAD)
        payload = cast(ConvertLogModePayload, data)
        with state_lock:
            state["convert_advanced_log"] = bool(payload.get("advanced", False))
            advanced = state["convert_advanced_log"]
        return jsonify({"ok": True, "advanced_log": advanced})

    @bp.route("/api/convert/start", methods=["POST"])
    def api_convert_start():
        data = json_body()
        ok, message = validate_convert_start_payload(data)
        if not ok:
            return fail(message, code=EC.INVALID_PAYLOAD)
        payload = cast(ConvertStartPayload, data)
        output_dir = str(payload.get("output_dir", "") or "").strip()
        if output_dir:
            with state_lock:
                state["default_convert_output_dir"] = output_dir
            persist_runtime_settings()
        sources = payload.get("sources", [])
        if not sources:
            return jsonify({"ok": False, "error": "No source files provided"})
        if not KCC_AVAILABLE and not _is_native_format(payload.get("format", "")):
            return jsonify({
                "ok": False,
                "error": ("KCC not found in modules/. Only the native formats "
                          "-- EPUB maic, MOBI maic, KFX maic, KFX + MOBI maic -- can be built "
                          "without it."),
            })

        with state_lock:
            if state["converting"]:
                return jsonify({"ok": False, "error": "Conversion is already running"})
            state["converting"] = True
            state["convert_stop_requested"] = False
            state["convert_progress"] = 0
            state["convert_log"] = []
            state["convert_phase"] = "Preparing..."
            state["convert_current_file"] = ""
            state["convert_total"] = len(sources)
            state["convert_done"] = 0
            state["convert_output_files"] = []
        convert_job_id = uuid.uuid4().hex
        requested_format_global = str(payload.get("format", "") or "").strip().upper()
        # KPF output option was removed; treat legacy requests as KFX.
        if requested_format_global == "KPF":
            requested_format_global = "KFX"
        # "KFX (+SDR)" → multi-container output; normalize to "KFX" for pipeline.
        kfx_multi_container = requested_format_global == "KFX (+SDR)"
        if kfx_multi_container:
            requested_format_global = "KFX"
        # One native image pass, followed by two container writers.  Keep KFX
        # as the normalized format so output collection applies its usual
        # no-intermediate-EPUB rule while still accepting the MOBI result.
        kfx_mobi_native = _is_native_kfx_mobi_format(requested_format_global)
        if kfx_mobi_native:
            requested_format_global = "KFX"
        # "KFX MAIC" → build the container natively instead of via Kindle
        # Previewer; the KCC stage ahead of it is identical.
        kfx_native = requested_format_global == "KFX MAIC"
        if kfx_native:
            requested_format_global = "KFX"
        # "MOBI MAIC" -> write the container ourselves.  Unlike "MOBI" this
        # needs no kindlegen, so it is never greyed out for a missing binary.
        mobi_native = _is_native_mobi_format(requested_format_global)
        if mobi_native:
            requested_format_global = "MOBI"
        # "EPUB MAIC" -> the same native pipeline, written straight into an
        # EPUB 3 container.  Nothing to install here either: KCC was the only
        # thing an EPUB ever needed, and this is the branch that drops it.
        epub_native = _is_native_epub_format(requested_format_global)
        if epub_native:
            requested_format_global = "EPUB"
        source_file_inputs = {
            os.path.normcase(os.path.normpath(os.path.abspath(src)))
            for src in sources
            if isinstance(src, str) and os.path.isfile(src)
        }
        convert_started_at = time.time()

        def convert_thread():
            stopped = False
            stop_summary_logged = False
            failed_sources = 0

            def _collect_recent_output_files() -> int:
                out_dir = payload.get("output_dir", "")
                search_dirs: set[str] = set()
                if out_dir and os.path.isdir(out_dir):
                    search_dirs.add(out_dir)
                for src in sources:
                    src_dir = os.path.dirname(src) if os.path.isfile(src) else src
                    if os.path.isdir(src_dir):
                        search_dirs.add(src_dir)
                    parent = os.path.dirname(src_dir)
                    if os.path.isdir(parent):
                        search_dirs.add(parent)
                output_exts = {".epub", ".cbz", ".mobi", ".pdf", ".kfx"}
                if requested_format_global == "KFX":
                    output_exts.discard(".epub")

                for directory in search_dirs:
                    try:
                        for filename in os.listdir(directory):
                            ext = os.path.splitext(filename)[1].lower()
                            if ext not in output_exts:
                                continue
                            full = os.path.join(directory, filename)
                            with state_lock:
                                present = full in state["convert_output_files"]
                            if not present and os.path.getmtime(full) >= convert_started_at - 2.0:
                                with state_lock:
                                    if full not in state["convert_output_files"]:
                                        state["convert_output_files"].append(full)
                    except Exception:
                        pass

                with state_lock:
                    return len(state["convert_output_files"])

            def _finalize_stopped() -> None:
                nonlocal stop_summary_logged
                output_count = _collect_recent_output_files()
                with state_lock:
                    state["convert_phase"] = "Stopped"
                    state["convert_current_file"] = ""
                if stop_summary_logged:
                    return
                stop_summary_logged = True
                convert_log(f"[!] Conversion stopped. Files: {output_count}")
                _log_convert_event(
                    f"Convert worker stopped. Files: {output_count}",
                    phase="stopped",
                    total=len(sources),
                    job_id=convert_job_id,
                )

            _log_convert_event(
                "Convert worker started",
                phase="start",
                total=len(sources),
                job_id=convert_job_id,
            )
            try:
                ensure_kcc_path()
                ensure_kcc_deps()
                # Imported up here so one missing install is reported once
                # rather than per source -- but only when a source can still
                # reach it. The native formats never do, and on a checkout
                # with an empty modules/ this import is the whole difference
                # between a volume and a traceback.
                kcc_main = None
                if KCC_AVAILABLE:
                    from kindlecomicconverter.comic2ebook import main as kcc_main

                for src_idx, source in enumerate(sources):
                    if _is_convert_stop_requested():
                        stopped = True
                        with state_lock:
                            state["convert_phase"] = "Stopping..."
                        break

                    src_name = os.path.basename(source.rstrip("/\\"))
                    with state_lock:
                        state["convert_current_file"] = src_name
                        state["convert_phase"] = f"[{src_idx+1}/{len(sources)}] {src_name}"
                    _log_convert_event(
                        "Converting source",
                        phase="source_start",
                        source=src_name,
                        index=src_idx + 1,
                        total=len(sources),
                        job_id=convert_job_id,
                    )
                    convert_log(f"[DIR] {src_name}")

                    kcc_source = source
                    if KCC_AVAILABLE:
                        apply_getworkfolder_patch_fn()
                    try:
                        scp = get_sidecar_path(source)
                        os.environ["MAIC_SIDECAR_PATH"] = scp if os.path.isfile(scp) else ""
                    except Exception:
                        os.environ["MAIC_SIDECAR_PATH"] = ""

                    argv_data = dict(data)
                    explicit_title = str(argv_data.get("title", "") or "").strip()
                    metadata_title_mode = as_int(argv_data.get("metadata_title", 0), 0)
                    resolved_title, resolved_author = _resolve_convert_title_author(argv_data, source)
                    if resolved_title:
                        use_resolved_title = True
                        if metadata_title_mode == 2:
                            if explicit_title:
                                # Keep user-resolved title deterministic; KCC mode 2 overwrites with ComicInfo <Title>.
                                argv_data["metadata_title"] = 0
                                convert_log("  [META] metadata_title=2 overridden to preserve explicit title")
                            else:
                                # Respect Title-only mode only when ComicInfo <Title> exists.
                                raw_meta_title = _read_comicinfo_raw_title(source)
                                if raw_meta_title:
                                    use_resolved_title = False
                                else:
                                    argv_data["metadata_title"] = 0
                                    convert_log(
                                        "  [META] metadata_title=2 requested but ComicInfo <Title> is empty; "
                                        "falling back to resolved Series/Volume title"
                                    )
                        if use_resolved_title:
                            argv_data["title"] = resolved_title
                        else:
                            argv_data.pop("title", None)
                    else:
                        argv_data.pop("title", None)
                    if resolved_author:
                        argv_data["author"] = resolved_author
                    else:
                        argv_data.pop("author", None)
                    requested_format = requested_format_global
                    if requested_format == "KFX":
                        argv_data["format"] = "KFX"
                    elif requested_format == "MOBI":
                        # argv_data still carries the pre-normalisation payload
                        # (dict(data), taken before "MOBI MAIC" was rewritten
                        # above); if the native path below falls back to KCC,
                        # -f needs the literal KCC-recognised value, not the
                        # maic suffix.
                        argv_data["format"] = "MOBI"
                    argv = []
                    if KCC_AVAILABLE:
                        argv = build_kcc_argv(argv_data)
                        argv.append(kcc_source)
                        convert_log(f"  KCC args: {' '.join(argv[:6])}...")
                    source_started_at = time.time()

                    per_source = payload.get("per_source_crop", {})
                    src_crop = per_source.get(source, {})
                    nocrop_files: set[str] = set()
                    for name in src_crop.get("no-crop", []):
                        if name:
                            nocrop_files.add(name)
                            nocrop_files.add(name.lower())
                    custom_crops = src_crop.get("custom-crop", {})
                    custom_splits = src_crop.get("custom-split", {})
                    # The KCC pipeline still ignores these; the native one
                    # applies them, so keep a copy before they are dropped.
                    custom_splits_native = dict(custom_splits or {})
                    if custom_splits:
                        convert_log(
                            "  [SPLIT] Custom split is disabled and ignored "
                            f"({len(custom_splits)} entries)"
                        )
                        custom_splits = {}

                    all_excluded = payload.get("excluded_files", [])
                    src_files = get_source_relpaths(source)
                    excluded_for_src = [rel for rel in all_excluded if rel in src_files]
                    if excluded_for_src:
                        convert_log(f"  [INFO] Exclude pages: {len(excluded_for_src)} matched")
                    elif all_excluded:
                        convert_log(
                            "  [WARN] Exclude pages: 0 matched for this source "
                            f"({len(all_excluded)} requested)"
                        )
                    # Load edit-ops and extra-margin from sidecar
                    _sidecar_data = load_sidecar_for_source(source)
                    _edit_ops = _sidecar_data.get("edit-ops", {}) or {}
                    _extra_margin = _sidecar_data.get("extra-margin", {}) or {}
                    _watermark_matches = (
                        list(_sidecar_data.get("watermark-matches", []) or [])
                        if _sidecar_data.get("_watermark-matches-saved")
                        else None
                    )
                    # The native writers call this to take KCC's image
                    # monkeypatch back off before they build; with no patch
                    # installed there is nothing to undo.
                    restore_patch = (lambda: None)
                    if KCC_AVAILABLE:
                        restore_patch = apply_nocrop_patch_fn(
                            nocrop_files,
                            custom_crops=custom_crops,
                            custom_splits=custom_splits,
                            excluded_files=excluded_for_src,
                            edit_ops=_edit_ops,
                            extra_margin=_extra_margin,
                            watermark_match_files=_watermark_matches,
                            convert_log=convert_log,
                            stop_requested_fn=_is_convert_stop_requested,
                            kindle_doc_type=str(payload.get("kindle_doc_type", "auto") or "auto"),
                            auto_balance_margins=bool(payload.get("auto_balance_margins", False)),
                            auto_balance_margin_px=as_int(payload.get("auto_balance_margin_px", 0), 0),
                            auto_balance_margin_unit=str(payload.get("auto_balance_margin_unit", "px") or "px"),
                            auto_balance_margin_pct=as_float(payload.get("auto_balance_margin_pct", 0.0), 0.0),
                            match_spread_width=bool(payload.get("match_spread_width", False)),
                            screen_margins=bool(payload.get("screen_margins", False)),
                            kfx_no_padding=(kfx_native or kfx_mobi_native) and bool(payload.get("kfx_no_padding", False)),
                            cropping_mode=as_int(payload.get("cropping", 0), 0),
                            cropping_power=as_float(payload.get("cropping_power", 1.0), 1.0),
                            preserve_margin_h=as_int(payload.get("preserve_margin_h", 0), 0),
                            preserve_margin_v=as_int(payload.get("preserve_margin_v", 0), 0),
                            borders_color=str(payload.get("borders_color", "none") or "none"),
                            webtoon=bool(payload.get("webtoon", False)),
                            no_processing=bool(payload.get("no_processing", False)),
                            cropping_minimum=as_float(payload.get("cropping_minimum", 0.0), 0.0),
                            maic_crop=bool(payload.get("maic_crop", False)),
                            maic_margin_pct=as_float(payload.get("maic_margin_pct", 0.6), 0.6),
                            maic_watermarks=bool(payload.get("maic_watermarks", False)),
                            maic_page_numbers=bool(payload.get("maic_page_numbers", False)),
                            cleanup_method=str(payload.get("cleanup_method", "lama") or "lama"),
                            cleanup_padding=as_int(payload.get("cleanup_padding", 2), 2),
                            page_number_scope=source,
                        )

                    src_base_progress = int(src_idx / len(sources) * 100)
                    src_progress_span = int(1 / len(sources) * 100)

                    def _on_kfx_status(phase: str, pct: int | None = None) -> None:
                        with state_lock:
                            state["convert_phase"] = phase
                            if pct is not None:
                                pct = max(0, min(99, int(pct)))
                                state["convert_progress"] = src_base_progress + int(
                                    pct / 100 * src_progress_span
                                )

                    # The combined native format performs the expensive image
                    # work once, writes KFX first, then reuses the same prepared
                    # page groups for MOBI. There is no lossless KCC fallback
                    # for an unsupported source that preserves this guarantee.
                    if kfx_mobi_native:
                        blocker = _native_source_blocker(source, payload)
                        if blocker:
                            failed_sources += 1
                            convert_log(
                                f"  [!] KFX + MOBI maic cannot read this source ({blocker})"
                            )
                            _log_convert_event(
                                "KFX + MOBI maic source unsupported",
                                phase="source_nonzero",
                                source=src_name,
                                index=src_idx + 1,
                                total=len(sources),
                                job_id=convert_job_id,
                                level="error",
                            )
                            with state_lock:
                                state["convert_done"] += 1
                                state["convert_progress"] = int(
                                    state["convert_done"] / len(sources) * 100
                                )
                            continue

                        restore_patch()
                        out_base = str(payload.get("output_dir", "") or "").strip()
                        if out_base and os.path.isdir(out_base):
                            out_kfx = os.path.join(out_base, src_name + ".kfx")
                            out_mobi = os.path.join(out_base, src_name + ".mobi")
                        else:
                            out_kfx = source.rstrip("/\\") + ".kfx"
                            out_mobi = source.rstrip("/\\") + ".mobi"
                        convert_log(
                            f"  [KFX + MOBI maic] Preparing {src_name} once; "
                            f"then {os.path.basename(out_kfx)}, then {os.path.basename(out_mobi)}"
                        )
                        code_native, out_native = _run_native_dir_to_kfx_mobi(
                            source,
                            out_kfx,
                            out_mobi,
                            payload=payload,
                            title=resolved_title,
                            author=resolved_author,
                            excluded=excluded_for_src,
                            nocrop=sorted(nocrop_files),
                            custom_crops=custom_crops,
                            custom_splits=custom_splits_native,
                            edit_ops=_edit_ops,
                            extra_margin=_extra_margin,
                            watermark_matches=_watermark_matches,
                            log_fn=convert_log,
                            status_fn=_on_kfx_status,
                            stop_requested_fn=_is_convert_stop_requested,
                        )
                        if out_native.strip():
                            for ln in out_native.strip().splitlines()[-12:]:
                                convert_log(f"  [KFX + MOBI] {ln}")
                        if code_native == 130:
                            stopped = True
                            with state_lock:
                                state["convert_phase"] = "Stopping..."
                            break
                        if (code_native == 0 and os.path.isfile(out_kfx)
                                and os.path.isfile(out_mobi)):
                            convert_log(
                                f"  [KFX + MOBI] OK: {os.path.basename(out_kfx)}, "
                                f"{os.path.basename(out_mobi)}"
                            )
                            _collect_recent_output_files()
                            convert_log(f"  [OK] Done: {src_name}")
                            _log_convert_event(
                                "Source conversion completed",
                                phase="source_done",
                                source=src_name,
                                index=src_idx + 1,
                                total=len(sources),
                                job_id=convert_job_id,
                            )
                        else:
                            failed_sources += 1
                            convert_log("  [!] KFX + MOBI maic stage failed")
                            _collect_recent_output_files()
                            _log_convert_event(
                                "KFX + MOBI maic stage failed",
                                phase="source_nonzero",
                                source=src_name,
                                index=src_idx + 1,
                                total=len(sources),
                                job_id=convert_job_id,
                                level="error",
                            )
                        with state_lock:
                            state["convert_done"] += 1
                            state["convert_progress"] = int(
                                state["convert_done"] / len(sources) * 100
                            )
                        continue

                    # "KFX maic" builds straight from the source folder: no KCC,
                    # no EPUB, no Kindle Previewer.  Sources the native walk
                    # cannot read fall back to the KCC pipeline below.
                    if kfx_native:
                        blocker = _native_source_blocker(source, payload)
                        if blocker and not KCC_AVAILABLE:
                            failed_sources += 1
                            # Nothing to fall back to: say so once, here,
                            # rather than let the KCC stage below fail
                            # further down on a missing import.
                            convert_log(
                                f"  [!] KFX maic cannot read this source ({blocker}), "
                                "and KCC is not installed to fall back to"
                            )
                            _log_convert_event(
                                "KFX maic source unsupported without KCC",
                                phase="source_nonzero",
                                source=src_name,
                                index=src_idx + 1,
                                total=len(sources),
                                job_id=convert_job_id,
                                level="error",
                            )
                            with state_lock:
                                state["convert_done"] += 1
                                state["convert_progress"] = int(
                                    state["convert_done"] / len(sources) * 100
                                )
                            continue
                        if blocker:
                            convert_log(f"  [KFX maic] Falling back to KCC: {blocker}")
                        else:
                            restore_patch()
                            out_base = str(payload.get("output_dir", "") or "").strip()
                            if out_base and os.path.isdir(out_base):
                                out_kfx = os.path.join(out_base, src_name + ".kfx")
                            else:
                                out_kfx = source.rstrip("/\\") + ".kfx"
                            convert_log(
                                f"  [KFX maic] Building {os.path.basename(out_kfx)} "
                                "from source images"
                            )
                            code_native, out_native = _run_native_dir_to_kfx(
                                source,
                                out_kfx,
                                payload=payload,
                                title=resolved_title,
                                author=resolved_author,
                                excluded=excluded_for_src,
                                nocrop=sorted(nocrop_files),
                                custom_crops=custom_crops,
                                custom_splits=custom_splits_native,
                                edit_ops=_edit_ops,
                                extra_margin=_extra_margin,
                                watermark_matches=_watermark_matches,
                                log_fn=convert_log,
                                status_fn=_on_kfx_status,
                                stop_requested_fn=_is_convert_stop_requested,
                            )
                            if out_native.strip():
                                for ln in out_native.strip().splitlines()[-12:]:
                                    convert_log(f"  [KFX] {ln}")
                            if code_native == 130:
                                stopped = True
                                with state_lock:
                                    state["convert_phase"] = "Stopping..."
                                break
                            if code_native == 0 and os.path.isfile(out_kfx):
                                convert_log(f"  [KFX] OK: {os.path.basename(out_kfx)}")
                                _collect_recent_output_files()
                                convert_log(f"  [OK] Done: {src_name}")
                                _log_convert_event(
                                    "Source conversion completed",
                                    phase="source_done",
                                    source=src_name,
                                    index=src_idx + 1,
                                    total=len(sources),
                                    job_id=convert_job_id,
                                )
                            else:
                                failed_sources += 1
                                convert_log("  [!] KFX maic stage failed")
                                _log_convert_event(
                                    "KFX maic stage failed",
                                    phase="source_nonzero",
                                    source=src_name,
                                    index=src_idx + 1,
                                    total=len(sources),
                                    job_id=convert_job_id,
                                    level="error",
                                )
                            with state_lock:
                                state["convert_done"] += 1
                                state["convert_progress"] = int(
                                    state["convert_done"] / len(sources) * 100
                                )
                            continue

                    # "MOBI maic" mirrors "KFX maic" exactly: no KCC, no EPUB,
                    # no kindlegen.  Sources the native walk cannot read fall
                    # back to the KCC pipeline below.
                    if mobi_native:
                        blocker = _native_source_blocker(source, payload)
                        if blocker and not KCC_AVAILABLE:
                            failed_sources += 1
                            # Nothing to fall back to: say so once, here,
                            # rather than let the KCC stage below fail
                            # further down on a missing import.
                            convert_log(
                                f"  [!] MOBI maic cannot read this source ({blocker}), "
                                "and KCC is not installed to fall back to"
                            )
                            _log_convert_event(
                                "MOBI maic source unsupported without KCC",
                                phase="source_nonzero",
                                source=src_name,
                                index=src_idx + 1,
                                total=len(sources),
                                job_id=convert_job_id,
                                level="error",
                            )
                            with state_lock:
                                state["convert_done"] += 1
                                state["convert_progress"] = int(
                                    state["convert_done"] / len(sources) * 100
                                )
                            continue
                        if blocker:
                            convert_log(f"  [MOBI maic] Falling back to KCC: {blocker}")
                        else:
                            restore_patch()
                            out_base = str(payload.get("output_dir", "") or "").strip()
                            if out_base and os.path.isdir(out_base):
                                out_mobi = os.path.join(out_base, src_name + ".mobi")
                            else:
                                out_mobi = source.rstrip("/\\") + ".mobi"
                            convert_log(
                                f"  [MOBI maic] Building {os.path.basename(out_mobi)} "
                                "from source images"
                            )
                            code_native, out_native = _run_native_dir_to_mobi(
                                source,
                                out_mobi,
                                payload=payload,
                                title=resolved_title,
                                author=resolved_author,
                                excluded=excluded_for_src,
                                nocrop=sorted(nocrop_files),
                                custom_crops=custom_crops,
                                custom_splits=custom_splits_native,
                                edit_ops=_edit_ops,
                                extra_margin=_extra_margin,
                                watermark_matches=_watermark_matches,
                                log_fn=convert_log,
                                status_fn=_on_kfx_status,
                                stop_requested_fn=_is_convert_stop_requested,
                            )
                            if out_native.strip():
                                for ln in out_native.strip().splitlines()[-12:]:
                                    convert_log(f"  [MOBI] {ln}")
                            if code_native == 130:
                                stopped = True
                                with state_lock:
                                    state["convert_phase"] = "Stopping..."
                                break
                            if code_native == 0 and os.path.isfile(out_mobi):
                                convert_log(f"  [MOBI] OK: {os.path.basename(out_mobi)}")
                                _collect_recent_output_files()
                                convert_log(f"  [OK] Done: {src_name}")
                                _log_convert_event(
                                    "Source conversion completed",
                                    phase="source_done",
                                    source=src_name,
                                    index=src_idx + 1,
                                    total=len(sources),
                                    job_id=convert_job_id,
                                )
                            else:
                                failed_sources += 1
                                convert_log("  [!] MOBI maic stage failed")
                                _log_convert_event(
                                    "MOBI maic stage failed",
                                    phase="source_nonzero",
                                    source=src_name,
                                    index=src_idx + 1,
                                    total=len(sources),
                                    job_id=convert_job_id,
                                    level="error",
                                )
                            with state_lock:
                                state["convert_done"] += 1
                                state["convert_progress"] = int(
                                    state["convert_done"] / len(sources) * 100
                                )
                            continue
                    # "EPUB maic" is the third of the same shape: no KCC, and
                    # nothing else to install.  Sources the native walk cannot
                    # read fall back to the KCC pipeline below.
                    if epub_native:
                        blocker = _native_source_blocker(source, payload)
                        if blocker and not KCC_AVAILABLE:
                            failed_sources += 1
                            # Nothing to fall back to: say so once, here,
                            # rather than let the KCC stage below fail
                            # further down on a missing import.
                            convert_log(
                                f"  [!] EPUB maic cannot read this source ({blocker}), "
                                "and KCC is not installed to fall back to"
                            )
                            _log_convert_event(
                                "EPUB maic source unsupported without KCC",
                                phase="source_nonzero",
                                source=src_name,
                                index=src_idx + 1,
                                total=len(sources),
                                job_id=convert_job_id,
                                level="error",
                            )
                            with state_lock:
                                state["convert_done"] += 1
                                state["convert_progress"] = int(
                                    state["convert_done"] / len(sources) * 100
                                )
                            continue
                        if blocker:
                            convert_log(f"  [EPUB maic] Falling back to KCC: {blocker}")
                        else:
                            restore_patch()
                            out_base = str(payload.get("output_dir", "") or "").strip()
                            if out_base and os.path.isdir(out_base):
                                out_epub = os.path.join(out_base, src_name + ".epub")
                            else:
                                out_epub = source.rstrip("/\\") + ".epub"
                            convert_log(
                                f"  [EPUB maic] Building {os.path.basename(out_epub)} "
                                "from source images"
                            )
                            code_native, out_native = _run_native_dir_to_epub(
                                source,
                                out_epub,
                                payload=payload,
                                title=resolved_title,
                                author=resolved_author,
                                excluded=excluded_for_src,
                                nocrop=sorted(nocrop_files),
                                custom_crops=custom_crops,
                                custom_splits=custom_splits_native,
                                edit_ops=_edit_ops,
                                extra_margin=_extra_margin,
                                watermark_matches=_watermark_matches,
                                log_fn=convert_log,
                                status_fn=_on_kfx_status,
                                stop_requested_fn=_is_convert_stop_requested,
                            )
                            if out_native.strip():
                                for ln in out_native.strip().splitlines()[-12:]:
                                    convert_log(f"  [EPUB] {ln}")
                            if code_native == 130:
                                stopped = True
                                with state_lock:
                                    state["convert_phase"] = "Stopping..."
                                break
                            if code_native == 0 and os.path.isfile(out_epub):
                                convert_log(f"  [EPUB] OK: {os.path.basename(out_epub)}")
                                _collect_recent_output_files()
                                convert_log(f"  [OK] Done: {src_name}")
                                _log_convert_event(
                                    "Source conversion completed",
                                    phase="source_done",
                                    source=src_name,
                                    index=src_idx + 1,
                                    total=len(sources),
                                    job_id=convert_job_id,
                                )
                            else:
                                failed_sources += 1
                                convert_log("  [!] EPUB maic stage failed")
                                _log_convert_event(
                                    "EPUB maic stage failed",
                                    phase="source_nonzero",
                                    source=src_name,
                                    index=src_idx + 1,
                                    total=len(sources),
                                    job_id=convert_job_id,
                                    level="error",
                                )
                            with state_lock:
                                state["convert_done"] += 1
                                state["convert_progress"] = int(
                                    state["convert_done"] / len(sources) * 100
                                )
                            continue
                    kcc_phases = [
                        ("Preparing source images", 5),
                        ("Checking images", 15),
                        ("Processing images", 65),
                        ("Creating EPUB file", 85),
                        ("buildEPUB", 90),
                    ]

                    def _on_kcc_line(line: str) -> None:
                        for phrase, pct in kcc_phases:
                            if phrase.lower() in line.lower():
                                with state_lock:
                                    state["convert_phase"] = phrase
                                    state["convert_progress"] = src_base_progress + int(
                                        pct / 100 * src_progress_span
                                    )
                                break

                    live = _LiveWriter(
                        log_line=lambda line: convert_log(f"  {line}"),
                        on_line=_on_kcc_line,
                    )
                    try:
                        with redirect_stdout(live), redirect_stderr(live):
                            if kcc_main is None:
                                raise RuntimeError(
                                    "KCC not found in modules/, and this format "
                                    "cannot be built without it"
                                )
                            result = kcc_main(argv)
                    except SystemExit as exc:
                        result = exc.code if exc.code else 0
                        if _is_convert_stop_requested() and (result == 0 or result is None):
                            result = 130
                    except Exception as exc:
                        exc_text = str(exc).strip()
                        interrupted = _is_convert_stop_requested() or exc_text == "Conversion interrupted."
                        if interrupted:
                            result = 130
                            with state_lock:
                                state["convert_phase"] = "Stopping..."
                            convert_log("  [!] Conversion interrupted.")
                        else:
                            convert_log(f"  [ERR] KCC error: {exc}")
                            convert_log(traceback.format_exc())
                            _log_convert_event(
                                f"KCC error: {exc}",
                                phase="source_error",
                                source=src_name,
                                index=src_idx + 1,
                                total=len(sources),
                                job_id=convert_job_id,
                                level="error",
                            )
                            result = 1
                    finally:
                        restore_patch()

                    if _is_convert_stop_requested() and (result == 0 or result is None):
                        result = 130

                    if (result == 0 or result is None) and requested_format == "KFX":
                        # The native backend writes the container itself, so
                        # Kindle Previewer is only required by the KPR one.
                        kpr_exe = "" if kfx_native else _find_kpr_exe()
                        kfxlib_dir = _find_kfxlib_output_dir()
                        if (not kpr_exe and not kfx_native) or not kfxlib_dir:
                            missing = []
                            if not kpr_exe and not kfx_native:
                                missing.append("Kindle Previewer 3")
                            if not kfxlib_dir:
                                missing.append("modules/KFX/output/kfxlib")
                            convert_log(
                                "  [ERR] KFX backend unavailable (requires "
                                + " + ".join(missing)
                                + ")"
                            )
                            result = 1
                        else:
                            per_source_dirs: set[str] = set()
                            out_dir = str(payload.get("output_dir", "") or "").strip()
                            if out_dir and os.path.isdir(out_dir):
                                per_source_dirs.add(out_dir)
                            src_dir = os.path.dirname(source) if os.path.isfile(source) else source
                            if os.path.isdir(src_dir):
                                per_source_dirs.add(src_dir)
                            src_parent = os.path.dirname(src_dir)
                            if os.path.isdir(src_parent):
                                per_source_dirs.add(src_parent)

                            candidate_epubs: list[str] = []
                            for d in per_source_dirs:
                                candidate_epubs.extend(
                                    _discover_recent_files(d, source_started_at - 2.0, {".epub"})
                                )
                            seen_epub: set[str] = set()
                            epubs: list[str] = []
                            for fp in sorted(candidate_epubs, key=lambda p: os.path.getmtime(p), reverse=True):
                                if fp not in seen_epub:
                                    seen_epub.add(fp)
                                    epubs.append(fp)
                            # KCC can leave multiple fresh EPUB candidates for one source
                            # (or same-name files in nearby dirs). Keep newest per stem.
                            epubs_by_stem: dict[str, str] = {}
                            for fp in epubs:
                                stem = os.path.splitext(os.path.basename(fp))[0]
                                prev = epubs_by_stem.get(stem)
                                if prev is None:
                                    epubs_by_stem[stem] = fp
                                    continue
                                try:
                                    if os.path.getmtime(fp) > os.path.getmtime(prev):
                                        epubs_by_stem[stem] = fp
                                except Exception:
                                    pass
                            epubs = sorted(
                                epubs_by_stem.values(),
                                key=lambda p: os.path.getmtime(p) if os.path.isfile(p) else 0,
                                reverse=True,
                            )

                            if not epubs:
                                convert_log("  [ERR] KFX stage: no EPUB outputs found for this source")
                                result = 1
                            else:
                                produced_kfx: list[str] = []
                                seen_kfx_targets: set[str] = set()
                                out_base = out_dir if out_dir else os.path.dirname(epubs[0])
                                os.makedirs(out_base, exist_ok=True)

                                def _cleanup_intermediate_epub(path: str) -> None:
                                    try:
                                        normalized_path = os.path.normcase(
                                            os.path.normpath(os.path.abspath(path))
                                        )
                                        if normalized_path in source_file_inputs:
                                            convert_log(
                                                f"  [KFX] Skip EPUB cleanup (is source input): "
                                                f"{os.path.basename(path)}"
                                            )
                                            return
                                        if os.path.isfile(path):
                                            os.remove(path)
                                            convert_log(
                                                f"  [KFX] Removed intermediate EPUB: {os.path.basename(path)}"
                                            )
                                        else:
                                            convert_log(
                                                f"  [KFX] EPUB already gone: {os.path.basename(path)}"
                                            )
                                    except Exception as exc:
                                        convert_log(
                                            "  [KFX] WARN: failed to remove intermediate EPUB "
                                            f"{os.path.basename(path)}: {exc}"
                                        )

                                for epub_path in epubs:
                                    epub_stem = os.path.splitext(os.path.basename(epub_path))[0]
                                    out_kfx = os.path.join(out_base, epub_stem + ".kfx")
                                    if out_kfx in seen_kfx_targets:
                                        convert_log(
                                            f"  [KFX] Skip duplicate EPUB candidate for target: "
                                            f"{os.path.basename(out_kfx)}"
                                        )
                                        _cleanup_intermediate_epub(epub_path)
                                        continue
                                    seen_kfx_targets.add(out_kfx)

                                    convert_log(f"  [KFX] Converting: {os.path.basename(epub_path)}")
                                    convert_log(
                                        "  [KFX] Backend: "
                                        + ("maic native (no Kindle Previewer)" if kfx_native
                                           else "KPR CLI + kfxlib"
                                                + (" (+sdr multi-container)" if kfx_multi_container else ""))
                                    )
                                    _, meta_logs = _ensure_epub_comic_metadata(
                                        epub_path,
                                        manga_mode=bool(payload.get("manga_mode", False)),
                                    )
                                    for ln in meta_logs:
                                        convert_log(f"  {ln}")
                                    _reading_direction = (
                                        "rtl" if bool(payload.get("manga_mode", False)) else "ltr"
                                    )
                                    if kfx_native:
                                        code_pack, out_pack = _run_native_epub_to_kfx(
                                            epub_path,
                                            out_kfx,
                                            kindle_doc_type=str(payload.get("kindle_doc_type", "auto") or "auto"),
                                            reading_direction=_reading_direction,
                                            log_fn=convert_log,
                                            status_fn=_on_kfx_status,
                                        )
                                    else:
                                        code_pack, out_pack = _run_kfxlib_epub_to_kfx(
                                            epub_path,
                                            out_kfx,
                                            kindle_doc_type=str(payload.get("kindle_doc_type", "auto") or "auto"),
                                            reading_direction=_reading_direction,
                                            multi_container=kfx_multi_container,
                                            log_fn=convert_log,
                                            status_fn=_on_kfx_status,
                                            stop_requested_fn=_is_convert_stop_requested,
                                        )
                                    if out_pack.strip():
                                        for ln in out_pack.strip().splitlines()[-12:]:
                                            convert_log(f"  [KFX] {ln}")
                                    if code_pack == 0 and os.path.isfile(out_kfx):
                                        produced_kfx.append(out_kfx)
                                        convert_log(f"  [KFX] OK: {os.path.basename(out_kfx)}")
                                    elif code_pack == 130:
                                        result = 130
                                        stopped = True
                                    else:
                                        result = 1
                                        convert_log(
                                            f"  [ERR] KFX stage failed for {os.path.basename(epub_path)}"
                                            f" (kfxlib exit={code_pack})"
                                        )
                                    _cleanup_intermediate_epub(epub_path)
                                    if code_pack == 130:
                                        break

                                # Safety-net: sweep output dirs for any leftover
                                # intermediate EPUBs whose stem matches a produced KFX.
                                if produced_kfx:
                                    kfx_stems = {
                                        os.path.splitext(os.path.basename(k))[0].lower()
                                        for k in produced_kfx
                                    }
                                    sweep_dirs: set[str] = set()
                                    sweep_dirs.add(out_base)
                                    for d in per_source_dirs:
                                        sweep_dirs.add(d)
                                    for sd in sweep_dirs:
                                        if not os.path.isdir(sd):
                                            continue
                                        try:
                                            for fn in os.listdir(sd):
                                                if not fn.lower().endswith(".epub"):
                                                    continue
                                                stem = os.path.splitext(fn)[0].lower()
                                                if stem in kfx_stems:
                                                    fp = os.path.join(sd, fn)
                                                    np = os.path.normcase(
                                                        os.path.normpath(os.path.abspath(fp))
                                                    )
                                                    if np in source_file_inputs:
                                                        continue
                                                    try:
                                                        os.remove(fp)
                                                        convert_log(
                                                            f"  [KFX] Cleaned leftover EPUB: {fn}"
                                                        )
                                                    except Exception:
                                                        pass
                                        except Exception:
                                            pass

                                if result != 130 and not produced_kfx:
                                    result = 1

                    if result == 130:
                        stopped = True
                        with state_lock:
                            state["convert_phase"] = "Stopping..."
                        break

                    if result == 0 or result is None:
                        _collect_recent_output_files()
                        convert_log(f"  [OK] Done: {src_name}")
                        _log_convert_event(
                            "Source conversion completed",
                            phase="source_done",
                            source=src_name,
                            index=src_idx + 1,
                            total=len(sources),
                            job_id=convert_job_id,
                        )
                    else:
                        failed_sources += 1
                        convert_log(f"  [!] KCC returned code: {result}")
                        _log_convert_event(
                            f"Source conversion returned code: {result}",
                            phase="source_nonzero",
                            source=src_name,
                            index=src_idx + 1,
                            total=len(sources),
                            job_id=convert_job_id,
                            level="error",
                        )
                    with state_lock:
                        state["convert_done"] += 1
                        state["convert_progress"] = int(state["convert_done"] / len(sources) * 100)

                if stopped or _is_convert_stop_requested():
                    stopped = True
                    _finalize_stopped()
                else:
                    with state_lock:
                        state["convert_progress"] = 100
                        state["convert_phase"] = "Error" if failed_sources else "Done!"
                        state["convert_current_file"] = ""
                    output_count = _collect_recent_output_files()
                    if failed_sources:
                        convert_log(
                            f"[ERR] Completed with errors: {failed_sources}/{len(sources)} sources. "
                            f"Files: {output_count}"
                        )
                    else:
                        convert_log(f"[OK] Completed. Files: {output_count}")
                    _log_convert_event(
                        f"Convert worker completed. Failed sources: {failed_sources}. Files: {output_count}",
                        phase="error" if failed_sources else "done",
                        total=len(sources),
                        job_id=convert_job_id,
                        level="error" if failed_sources else "info",
                    )

            except Exception as exc:
                exc_text = str(exc).strip()
                interrupted = stopped or _is_convert_stop_requested() or exc_text == "Conversion interrupted."
                if interrupted:
                    stopped = True
                    _finalize_stopped()
                else:
                    with state_lock:
                        state["convert_phase"] = "Error"
                        state["convert_current_file"] = ""
                    _collect_recent_output_files()
                    convert_log(f"[ERR] Error: {exc}")
                    convert_log(traceback.format_exc())
                    _log_convert_event(
                        f"Convert worker crashed: {exc}",
                        phase="fatal",
                        total=len(sources),
                        job_id=convert_job_id,
                        level="error",
                    )
            with state_lock:
                state["converting"] = False
                state["convert_stop_requested"] = False

        threading.Thread(target=convert_thread, daemon=True).start()
        return jsonify({"ok": True, "message": "Conversion started"})

    @bp.route("/api/convert/stop", methods=["POST"])
    def api_convert_stop():
        with state_lock:
            if not state["converting"]:
                state["convert_stop_requested"] = False
                return jsonify({"ok": True, "stop_requested": False})
            already_requested = bool(state.get("convert_stop_requested", False))
            state["convert_stop_requested"] = True
            state["convert_phase"] = "Stopping..."
        if not already_requested:
            convert_log("[!] Stopping conversion...")
        return jsonify({"ok": True, "stop_requested": True})

    @bp.route("/api/convert/scan-source", methods=["POST"])
    def api_convert_scan_source():
        data = json_body()
        source = data.get("path", "")
        valid, err = require_non_empty_str(source, field="path", code=EC.INVALID_PAYLOAD)
        if not valid:
            return err
        add_allowed_root(state, source)
        payload = scan_source_entries(
            source=source,
            ensure_kcc_path=ensure_kcc_path,
            load_sidecar=load_sidecar_for_source,
            logger=logger,
        )
        return jsonify(payload)

    @bp.route("/api/convert/detect-spreads", methods=["POST"])
    def api_convert_detect_spreads():
        """Mark the source's wide pages No Crop, once each."""
        data = json_body()
        source = data.get("path", "")
        valid, err = require_non_empty_str(source, field="path", code=EC.INVALID_PAYLOAD)
        if not valid:
            return err
        add_allowed_root(state, source)
        payload = scan_spread_pages(
            source=source,
            ensure_kcc_path=ensure_kcc_path,
            load_sidecar=load_sidecar_for_source,
            save_sidecar=save_sidecar,
            logger=logger,
        )
        return jsonify(payload)

    @bp.route("/api/convert/crop-preview", methods=["POST"])
    def api_convert_crop_preview():
        data = json_body()
        path = data.get("path", "")
        valid, err = require_non_empty_str(path, field="path", code=EC.INVALID_PAYLOAD)
        if not valid:
            return err
        power = as_float(data.get("power", 1.0), 1.0)
        mode = as_int(data.get("mode", 1), 1)
        preserve_margin_h = as_int(data.get("preserve_margin_h", 0), 0)
        preserve_margin_v = as_int(data.get("preserve_margin_v", 0), 0)
        inter_panel_crop = as_int(data.get("inter_panel_crop", 0), 0)
        borders_color = str(data.get("borders_color", "none") or "none").strip().lower()
        if borders_color not in {"none", "white", "black"}:
            borders_color = "none"
        webtoon = as_bool(data.get("webtoon", False))
        no_processing = as_bool(data.get("no_processing", False))
        preview_variant = str(data.get("preview_variant", "auto") or "auto").strip().upper()
        if preview_variant not in {"AUTO", "N", "S1", "S2", "R"}:
            preview_variant = "AUTO"
        splitter = as_int(data.get("splitter", 0), 0)
        no_rotate = as_bool(data.get("no_rotate", False))
        # Which pipeline is going to build the book, so the preview splits by
        # the same rule it will.
        native = as_bool(data.get("native", False))
        rotate_first = as_bool(data.get("rotate_first", False))
        manga_mode = as_bool(data.get("manga_mode", False))
        profile_width = as_int(data.get("profile_width", 0), 0)
        profile_height = as_int(data.get("profile_height", 0), 0)
        cropping_minimum = as_float(data.get("cropping_minimum", 0.0), 0.0)
        edit_ops = data.get("edit_ops", [])
        if not isinstance(edit_ops, list):
            edit_ops = []
        maic_crop = as_bool(data.get("maic_crop", False))
        maic_margin_pct = as_float(data.get("maic_margin_pct", 0.6), 0.6)
        maic_watermarks = as_bool(data.get("maic_watermarks", False))
        maic_watermark_page_enabled = as_bool(data.get("maic_watermark_page_enabled", True))
        maic_page_numbers = as_bool(data.get("maic_page_numbers", False))
        cleanup_method = str(data.get("cleanup_method", "lama") or "lama")
        cleanup_padding = as_int(data.get("cleanup_padding", 2), 2)
        page_number_scope = str(data.get("page_number_scope", "") or "")
        payload = compute_crop_preview(
            path=path,
            power=power,
            mode=mode,
            preserve_margin_h=preserve_margin_h,
            preserve_margin_v=preserve_margin_v,
            allowed_roots=state.get("allowed_read_roots", []),
            inter_panel_crop=inter_panel_crop,
            borders_color=borders_color,
            webtoon=webtoon,
            no_processing=no_processing,
            cropping_minimum=cropping_minimum,
            preview_variant=preview_variant,
            splitter=splitter,
            no_rotate=no_rotate,
            native=native,
            rotate_first=rotate_first,
            manga_mode=manga_mode,
            profile_width=profile_width,
            profile_height=profile_height,
            edit_ops=edit_ops,
            maic_crop=maic_crop,
            maic_margin_pct=maic_margin_pct,
            maic_watermarks=maic_watermarks,
            maic_watermark_page_enabled=maic_watermark_page_enabled,
            maic_page_numbers=maic_page_numbers,
            cleanup_method=cleanup_method,
            cleanup_padding=cleanup_padding,
            page_number_scope=page_number_scope,
            minimum_page_number=max(1, min(10000, as_int(
                (data if request.method == "POST" else request.args).get("minimum_page_number", 1), 1))),
        )
        return jsonify(payload)

    @bp.route("/api/convert/final-preview", methods=["POST"])
    def api_convert_final_preview():
        from .final_preview import render_final_preview
        from .kcc_scan import _load_image_bytes
        from .path_access import is_under_allowed_root

        data = json_body()
        path = data.get("path", "")
        valid, err = require_non_empty_str(path, field="path", code=EC.INVALID_PAYLOAD)
        if not valid:
            return err
        roots = state.get("allowed_read_roots", [])
        if not is_under_allowed_root(path.split("||", 1)[0], roots):
            return jsonify(ok=False, error="Cannot read image"), 400
        try:
            image_bytes = _load_image_bytes(path, roots)
            if not image_bytes:
                return jsonify(ok=False, error="Cannot read image"), 400
            return jsonify(render_final_preview(image_bytes, data))
        except (ValueError, TypeError, OSError) as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @bp.route("/api/convert/serve-thumb")
    def api_convert_serve_thumb():
        path = request.args.get("path", "")
        full = request.args.get("full", "")
        preview_variant = str(request.args.get("preview_variant", "auto") or "auto").strip().upper()
        if preview_variant not in {"AUTO", "N", "S1", "S2", "R"}:
            preview_variant = "AUTO"
        splitter = as_int(request.args.get("splitter", 0), 0)
        no_rotate = as_bool(request.args.get("no_rotate", False))
        native = as_bool(request.args.get("native", False))
        rotate_first = as_bool(request.args.get("rotate_first", False))
        manga_mode = as_bool(request.args.get("manga_mode", False))
        webtoon = as_bool(request.args.get("webtoon", False))
        no_processing = as_bool(request.args.get("no_processing", False))
        profile_width = as_int(request.args.get("profile_width", 0), 0)
        profile_height = as_int(request.args.get("profile_height", 0), 0)
        maic_crop = as_bool(request.args.get("maic_crop", False))
        maic_watermarks = as_bool(request.args.get("maic_watermarks", False))
        maic_watermark_page_enabled = as_bool(request.args.get("maic_watermark_page_enabled", True))
        maic_page_numbers = as_bool(request.args.get("maic_page_numbers", False))
        cleanup_method = str(request.args.get("cleanup_method", "lama") or "lama")
        cleanup_padding = as_int(request.args.get("cleanup_padding", 2), 2)
        page_number_scope = str(request.args.get("page_number_scope", "") or "")
        erase_artifacts = as_bool(request.args.get("erase_artifacts", True))
        edit_ops: list[Any] = []
        raw_edit_ops = request.args.get("edit_ops", "")
        if raw_edit_ops:
            try:
                parsed_edit_ops = json.loads(raw_edit_ops)
                if isinstance(parsed_edit_ops, list):
                    edit_ops = parsed_edit_ops
            except (TypeError, ValueError, json.JSONDecodeError):
                edit_ops = []
        return serve_thumb_response(
            path=path,
            full=full,
            allowed_roots=state.get("allowed_read_roots", []),
            fail=fail,
            ec=EC,
            preview_variant=preview_variant,
            splitter=splitter,
            no_rotate=no_rotate,
            native=native,
            rotate_first=rotate_first,
            manga_mode=manga_mode,
            webtoon=webtoon,
            no_processing=no_processing,
            profile_width=profile_width,
            profile_height=profile_height,
            maic_crop=maic_crop,
            edit_ops=edit_ops,
            maic_watermarks=maic_watermarks,
            maic_watermark_page_enabled=maic_watermark_page_enabled,
            maic_page_numbers=maic_page_numbers,
            cleanup_method=cleanup_method,
            cleanup_padding=cleanup_padding,
            page_number_scope=page_number_scope,
            minimum_page_number=max(1, min(10000, as_int(
                (data if request.method == "POST" else request.args).get("minimum_page_number", 1), 1))),
            erase_artifacts=erase_artifacts,
        )

    return bp
