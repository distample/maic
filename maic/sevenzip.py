"""Shared 7z discovery and subprocess execution helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from typing import Literal, overload

from .config import KCC_DIR

WIN32_NO_WINDOW = 0x08000000


def find_7z(ensure_kcc_path: Callable[[], None] | None = None) -> str | None:
    """Locate 7z binary from PATH or bundled KCC directory."""
    seven_zip = shutil.which("7z")
    if seven_zip:
        return seven_zip

    if ensure_kcc_path is not None:
        try:
            ensure_kcc_path()
        except Exception:
            pass
        seven_zip = shutil.which("7z")
        if seven_zip:
            return seven_zip

    if KCC_DIR:
        for path in (
            os.path.join(KCC_DIR, "kindlecomicconverter", "7z"),
            os.path.join(KCC_DIR, "kindlecomicconverter", "7z.exe"),
        ):
            if os.path.isfile(path):
                return path
    if os.name == "nt":
        for path in (
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "7-Zip", "7z.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "7-Zip", "7z.exe"),
        ):
            if os.path.isfile(path):
                return path
    return None


@overload
def run_7z(
    args: list[str],
    *,
    timeout: int = 30,
    ensure_kcc_path: Callable[[], None] | None = None,
    text: Literal[True],
    encoding: str = "utf-8",
    errors: str = "replace",
) -> subprocess.CompletedProcess[str] | None: ...


@overload
def run_7z(
    args: list[str],
    *,
    timeout: int = 30,
    ensure_kcc_path: Callable[[], None] | None = None,
    text: Literal[False] = False,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> subprocess.CompletedProcess[bytes] | None: ...


def run_7z(
    args: list[str],
    *,
    timeout: int = 30,
    ensure_kcc_path: Callable[[], None] | None = None,
    text: bool = False,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str] | None:
    """Run 7z with unified timeout/flags and capture output."""
    seven_zip = find_7z(ensure_kcc_path=ensure_kcc_path)
    if not seven_zip:
        return None

    cmd = [seven_zip, *args]
    if text:
        if sys.platform == "win32":
            return subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                text=True,
                encoding=encoding,
                errors=errors,
                creationflags=WIN32_NO_WINDOW,
            )
        return subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            text=True,
            encoding=encoding,
            errors=errors,
        )

    if sys.platform == "win32":
        return subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            creationflags=WIN32_NO_WINDOW,
        )
    return subprocess.run(cmd, capture_output=True, timeout=timeout)
