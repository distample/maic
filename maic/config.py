"""Configuration, runtime state, and environment discovery."""

import logging
import os
import sys
import threading
from typing import Any

from .settings import get_settings_dir, load_settings, save_settings
from .state_types import AppState

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("MangaAICleaner")

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_data_root() -> str:
    """Return a writable app-data directory for runtime artifacts."""
    forced = os.environ.get("MAIC_DATA_DIR", "").strip()
    if forced:
        return os.path.realpath(forced)
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
        if local_appdata:
            return os.path.join(local_appdata, "MangaAICleaner")
    return os.path.join(os.path.expanduser("~"), ".local", "share", "manga_ai_cleaner")


DATA_DIR = _resolve_data_root()
MODULES_DIR = os.path.join(BASE_DIR, "modules")
YOLO_DIR = os.path.join(DATA_DIR, "yolo")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif"}
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(YOLO_DIR, exist_ok=True)

_persisted_settings = load_settings()
_preferred_device = str(_persisted_settings.get("device", "cpu")).lower()
_preferred_model_path = str(_persisted_settings.get("model_path", "")).strip()

state: AppState = {
    "yolo_model": None,
    "lama_model": None,
    "device": _preferred_device if _preferred_device in {"cpu", "cuda"} else "cpu",
    "model_path": _preferred_model_path or os.path.join(YOLO_DIR, "best_manga_cleaner.pt"),
    "training": False,
    "training_progress": 0,
    "training_log": [],
    "training_epochs_total": 30,
    "training_epoch_current": 0,
    "converting": False,
    "convert_stop_requested": False,
    "convert_progress": 0,
    "convert_log": [],
    "convert_phase": "",
    "convert_current_file": "",
    "convert_total": 0,
    "convert_done": 0,
    "convert_output_files": [],
    "convert_advanced_log": False,
    "default_convert_output_dir": str(_persisted_settings.get("convert_output_dir", "") or ""),
    "default_clean_output_dir": str(_persisted_settings.get("clean_output_dir", "") or ""),
    "allowed_read_roots": [BASE_DIR],
    "allowed_write_roots": [BASE_DIR, DATA_DIR, YOLO_DIR, get_settings_dir()],
    "cpu_name": "CPU",
    "cuda_available": False,
    "gpu_name": "Unknown",
}
state_lock = threading.RLock()


def find_kcc_dir() -> str | None:
    if not os.path.isdir(MODULES_DIR):
        return None
    for entry in os.listdir(MODULES_DIR):
        if entry.lower().startswith("kcc-") and os.path.isdir(os.path.join(MODULES_DIR, entry)):
            kcc_path = os.path.join(MODULES_DIR, entry)
            if os.path.isdir(os.path.join(kcc_path, "kindlecomicconverter")):
                return kcc_path
    return None


KCC_DIR = find_kcc_dir()
KCC_AVAILABLE = KCC_DIR is not None
if KCC_AVAILABLE:
    logger.info(f"KCC found: {KCC_DIR}")
else:
    logger.info("KCC not found in modules/")


def _detect_cpu_name() -> str:
    try:
        import platform
        import subprocess

        cpu_name = None
        if sys.platform == "win32":
            try:
                import winreg

                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
                )
                cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
                winreg.CloseKey(key)
            except Exception:
                pass
            if not cpu_name:
                try:
                    result = subprocess.run(
                        ["wmic", "cpu", "get", "name"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        creationflags=0x08000000,
                    )
                    lines = [
                        line.strip()
                        for line in result.stdout.strip().split("\n")
                        if line.strip() and line.strip().lower() != "name"
                    ]
                    if lines:
                        cpu_name = lines[0]
                except Exception:
                    pass
        else:
            try:
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            cpu_name = line.split(":")[1].strip()
                            break
            except Exception:
                pass
        return cpu_name or platform.processor() or "CPU"
    except Exception:
        return "CPU"


def _detect_gpu_snapshot() -> tuple[bool, str, str]:
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        if cuda_available:
            return True, "cuda", torch.cuda.get_device_name(0)
    except ImportError:
        return False, "cpu", "PyTorch not installed"
    except Exception:
        return False, "cpu", "Not detected"

    gpu = None
    try:
        import shutil
        import subprocess

        smi = shutil.which("nvidia-smi")
        if not smi:
            for path in (
                "/usr/bin/nvidia-smi",
                "/usr/lib/wsl/lib/nvidia-smi",
                "/usr/local/cuda/bin/nvidia-smi",
            ):
                if os.path.isfile(path):
                    smi = path
                    break
        if smi:
            try:
                if sys.platform == "win32":
                    result = subprocess.run(
                        [smi, "--query-gpu=name", "--format=csv,noheader"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        creationflags=0x08000000,
                    )
                else:
                    result = subprocess.run(
                        [smi, "--query-gpu=name", "--format=csv,noheader"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                if result.returncode == 0 and result.stdout.strip():
                    gpu = result.stdout.strip().split("\n")[0]
            except Exception:
                pass

        if not gpu:
            try:
                result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
                for line in result.stdout.split("\n"):
                    low = line.lower()
                    if "nvidia" in low and ("vga" in low or "3d" in low):
                        gpu = line.split(":")[-1].strip()
                        break
            except Exception:
                pass
    except Exception:
        pass

    gpu_name = f"{gpu} (CUDA unavailable - check PyTorch)" if gpu else "Not detected"
    return False, "cpu", gpu_name


def probe_hardware() -> None:
    """Detect CPU/GPU and update runtime state in a single locked snapshot."""
    cpu_name = _detect_cpu_name()
    cuda_available, suggested_device, gpu_name = _detect_gpu_snapshot()
    with state_lock:
        state["cpu_name"] = cpu_name
        state["cuda_available"] = cuda_available
        state["gpu_name"] = gpu_name
        if suggested_device == "cuda" and state["device"] != "cpu":
            state["device"] = "cuda"
        elif suggested_device != "cuda":
            state["device"] = "cpu"
    logger.info(f"CPU: {state['cpu_name']} | GPU: {state.get('gpu_name', '')} | Device: {state['device']}")


def persist_runtime_settings(*, port: int | None = None) -> dict[str, Any]:
    """Persist selected runtime settings to user config file."""
    with state_lock:
        payload: dict[str, Any] = {
            "device": state["device"],
            "model_path": state["model_path"],
            "convert_output_dir": state.get("default_convert_output_dir", ""),
            "clean_output_dir": state.get("default_clean_output_dir", ""),
        }
    if port is not None:
        payload["port"] = int(port)
    return save_settings(payload)
