"""Application entry point."""

import argparse
import multiprocessing
import os
import signal
import threading
import time

multiprocessing.freeze_support()

from .app import cleanup_runtime_resources, flask_app, register_atexit_cleanup
from .batch import request_batch_stop
from .config import MODULES_DIR, logger, persist_runtime_settings, probe_hardware, state, state_lock
from .models import _ensure_imports
from .settings import load_settings
from .version import __version__


def main():
    persisted_settings = load_settings()
    default_port = int(persisted_settings.get("port", 5847) or 5847)
    parser = argparse.ArgumentParser(description="maic")
    parser.add_argument("--gui", action="store_true", help="Run in a pywebview window")
    parser.add_argument("--port", type=int, default=default_port, help="Port")
    args = parser.parse_args()

    _ensure_imports()
    probe_hardware()
    port = args.port
    os.makedirs(MODULES_DIR, exist_ok=True)
    register_atexit_cleanup()
    persist_runtime_settings(port=port)
    logger.info(f"Backend version: {__version__}")

    shutting_down = threading.Event()

    def _graceful_shutdown(reason: str):
        if shutting_down.is_set():
            return
        shutting_down.set()
        logger.info(f"Shutdown requested: {reason}")
        request_batch_stop()
        with state_lock:
            state["training"] = False
            state["converting"] = False
        cleanup_runtime_resources()
        persist_runtime_settings(port=port)

    def _signal_handler(sig_num, _frame):
        sig_name = signal.Signals(sig_num).name
        _graceful_shutdown(sig_name)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)

    if args.gui:
        try:
            import webview

            def start_flask():
                flask_app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

            threading.Thread(target=start_flask, daemon=True).start()
            time.sleep(1)
            webview.create_window(
                "maic",
                f"http://127.0.0.1:{port}",
                width=1280,
                height=820,
                min_size=(900, 600),
            )
            webview.start()
            _graceful_shutdown("gui window closed")
            return
        except ImportError:
            logger.info("pywebview is not installed, opening in browser")

    import webbrowser

    url = f"http://127.0.0.1:{port}"
    logger.info(f"Starting: {url}")

    def open_browser():
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()
    try:
        flask_app.run(host="127.0.0.1", port=port, debug=False)
    finally:
        _graceful_shutdown("server stop")
