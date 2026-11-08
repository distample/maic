"""Flask application: API endpoints and frontend serving."""

import atexit
import os
import shutil
import threading
import time
from functools import partial

from flask import Flask

from .batch import configure_archive_runtime
from .autonomous import create_autonomous_blueprint
from .config import IMAGE_EXTS
from .kcc_patch import apply_getworkfolder_patch, apply_nocrop_patch
from .kcc_runtime import convert_log, get_source_relpaths, load_sidecar_for_convert
from .models import _ensure_imports
from .routes_batch_train import batch_train_bp
from .routes_cleaning import create_cleaning_blueprint
from .routes_convert import create_convert_blueprint
from .routes_core import core_bp
from .routes_metadata import metadata_bp

ARCH_EXTS = {".zip", ".cbz", ".cbr", ".cb7", ".rar", ".7z"}


class TempDirManager:
    """Encapsulates temporary directory and archive map state for extraction workflows."""

    TTL_SECONDS = 6 * 60 * 60
    MAX_ITEMS = 128

    def __init__(self) -> None:
        self._arch_map: dict = {}
        self._lock = threading.RLock()
        self._tmp_dirs: dict[str, float] = {}

    @property
    def arch_map(self) -> dict:
        return self._arch_map

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    def register(self, path: str) -> None:
        """Track temp directories to prevent unbounded growth across scans."""
        if not path:
            return
        with self._lock:
            self._tmp_dirs[path] = time.time()

    def prune(self) -> None:
        """Remove missing/stale temp dirs and cap tracked entries by count."""
        now = time.time()
        with self._lock:
            tracked = sorted(self._tmp_dirs.items(), key=lambda item: item[1])
        overflow = max(0, len(tracked) - self.MAX_ITEMS)
        stale = {
            path
            for path, created_at in tracked
            if (not os.path.isdir(path)) or (now - created_at > self.TTL_SECONDS)
        }
        stale.update(path for path, _ in tracked[:overflow])
        if not stale:
            return
        for path in stale:
            shutil.rmtree(path, ignore_errors=True)
        with self._lock:
            for path in stale:
                self._tmp_dirs.pop(path, None)
                self._arch_map.pop(path, None)

    def list_images(self, tmp_dir: str) -> list[str]:
        """Return all image file paths found recursively in a directory."""
        result = []
        for root, _, fnames in os.walk(tmp_dir):
            for fn in fnames:
                if os.path.splitext(fn)[1].lower() in IMAGE_EXTS:
                    result.append(os.path.join(root, fn))
        return result

    def snapshot(self) -> dict:
        """Return a shallow copy of the archive map."""
        with self._lock:
            return dict(self._arch_map)

    def cleanup(self) -> None:
        """Best-effort cleanup for tracked extraction temp directories."""
        with self._lock:
            paths = set(self._tmp_dirs.keys()) | set(self._arch_map.keys())
            self._tmp_dirs.clear()
            self._arch_map.clear()
        for path in paths:
            shutil.rmtree(path, ignore_errors=True)


_temp_mgr = TempDirManager()


def cleanup_runtime_resources():
    """Public cleanup hook used by shutdown handlers."""
    _temp_mgr.cleanup()


_ATEXIT_REGISTERED = False


def register_atexit_cleanup() -> None:
    """Register one-time atexit cleanup for temporary runtime artifacts."""
    global _ATEXIT_REGISTERED
    if _ATEXIT_REGISTERED:
        return
    atexit.register(_temp_mgr.cleanup)
    _ATEXIT_REGISTERED = True


def create_app() -> Flask:
    """Application factory used by runtime and tests."""
    flask_app = Flask(__name__, static_folder="static", static_url_path="/static")
    flask_app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

    convert_bp = create_convert_blueprint(
        convert_log=convert_log,
        get_source_relpaths=get_source_relpaths,
        apply_getworkfolder_patch_fn=apply_getworkfolder_patch,
        apply_nocrop_patch_fn=partial(apply_nocrop_patch, convert_log=convert_log),
        load_sidecar_for_source=load_sidecar_for_convert,
    )
    cleaning_bp = create_cleaning_blueprint(
        _temp_mgr.arch_map,
        _temp_mgr.list_images,
        IMAGE_EXTS,
        ARCH_EXTS,
        arch_map_lock=_temp_mgr.lock,
        register_tmp_dir=_temp_mgr.register,
        prune_tmp_dirs=_temp_mgr.prune,
    )

    flask_app.register_blueprint(core_bp)
    flask_app.register_blueprint(batch_train_bp)
    flask_app.register_blueprint(metadata_bp)
    flask_app.register_blueprint(cleaning_bp)
    flask_app.register_blueprint(convert_bp)
    flask_app.register_blueprint(create_autonomous_blueprint(_temp_mgr.snapshot))
    configure_archive_runtime(_temp_mgr.snapshot, _temp_mgr.list_images)

    @flask_app.before_request
    def ensure_deps():
        _ensure_imports()

    return flask_app


flask_app = create_app()
