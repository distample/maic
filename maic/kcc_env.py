"""KCC runtime environment bootstrap helpers."""

from __future__ import annotations

import os
import sys

from .config import KCC_DIR, logger


def ensure_kcc_path() -> None:
    """Ensure KCC is importable and add 7-Zip/kindlegen to PATH."""
    if KCC_DIR and KCC_DIR not in sys.path:
        sys.path.insert(0, KCC_DIR)

    import shutil

    if not shutil.which("7z"):
        if sys.platform == "win32":
            paths_7z = [
                r"C:\Program Files\7-Zip",
                r"C:\Program Files (x86)\7-Zip",
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\7-Zip"),
                r"D:\Program Files\7-Zip",
            ]
        else:
            paths_7z = ["/usr/bin", "/usr/local/bin", "/snap/bin"]
        for base in paths_7z:
            exe = "7z.exe" if sys.platform == "win32" else "7z"
            full = os.path.join(base, exe)
            if os.path.isfile(full):
                os.environ["PATH"] = base + os.pathsep + os.environ.get("PATH", "")
                logger.info(f"[KCC] Found 7z: {full}")
                break

    if not shutil.which("kindlegen"):
        if sys.platform == "win32":
            paths_kg = [
                os.path.expandvars(r"%LOCALAPPDATA%\Amazon\Kindle Previewer 3\lib\fc\bin"),
                os.path.expandvars(r"%LOCALAPPDATA%\Amazon\KC2"),
                os.path.expandvars(r"%USERPROFILE%\Kindle Previewer 3\lib\fc\bin"),
                r"C:\Apps\Kindle Previewer 3\lib\fc\bin",
            ]
        elif sys.platform == "darwin":
            paths_kg = [
                "/Applications/Kindle Previewer 3.app/Contents/lib/fc/bin",
                "/Applications/Kindle Comic Creator/Kindle Comic Creator.app/Contents/MacOS",
            ]
        else:
            paths_kg = [os.path.expanduser("~/.local/bin"), "/usr/local/bin"]
        for base in paths_kg:
            exe = "kindlegen.exe" if sys.platform == "win32" else "kindlegen"
            full = os.path.join(base, exe)
            if os.path.isfile(full):
                os.environ["PATH"] = base + os.pathsep + os.environ.get("PATH", "")
                logger.info(f"[KCC] Found kindlegen: {full}")
                break


def ensure_kcc_deps() -> None:
    """Validate KCC dependencies without invoking pip from a request worker."""
    if getattr(sys, "frozen", False):
        return
    from .dependencies import require_dependencies
    require_dependencies(("core", "kcc", "pdf"))
