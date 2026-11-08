"""Fast checks for launchers; the installers perform full runtime verification."""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib import metadata
import os
from pathlib import Path
import sys

from .dependencies import DEFAULT_GROUPS, ROOT, dependency_problems, python_problem, requirements


TORCH_STAMP = Path(sys.prefix) / ".maic-torch-verified.json"
DEPS_STAMP = Path(sys.prefix) / ".maic-deps-verified.json"


def _hash_inputs(names: tuple[str, ...]) -> dict[str, str]:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def _stamp_matches(path: Path, snapshot: dict[str, object] | None) -> bool:
    if snapshot is None:
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")) == snapshot
    except (OSError, ValueError):
        return False


def _record_stamp(path: Path, snapshot: dict[str, object] | None) -> bool:
    if snapshot is None or sys.prefix == sys.base_prefix:
        return False
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)
        return False
    return True


def torch_snapshot() -> dict[str, object] | None:
    """Identify the interpreter, tested wheel pair, and verification inputs."""
    if python_problem():
        return None
    from _setup_torch import detect_profile

    try:
        installed = {name: metadata.version(name) for name in ("torch", "torchvision")}
    except metadata.PackageNotFoundError:
        return None
    expected = dict(spec.split("==", 1) for spec in requirements(("ml",))
                    if spec.startswith(("torch==", "torchvision==")))
    if any(installed[name].split("+", 1)[0] != expected[name] for name in expected):
        return None
    inputs = ("_setup_torch.py", "requirements/ml.txt", "requirements/constraints-python314.txt")
    return {
        "python": str(Path(sys.executable).resolve()),
        "version": sys.version,
        "wheels": installed,
        "detected_profile": detect_profile(),
        "verification_inputs": _hash_inputs(inputs),
    }


def torch_verified() -> bool:
    return _stamp_matches(TORCH_STAMP, torch_snapshot())


def record_torch_verification() -> bool:
    return _record_stamp(TORCH_STAMP, torch_snapshot())


def dependency_snapshot() -> dict[str, object] | None:
    """Track the installed pinned packages and files used by general setup."""
    if python_problem() or dependency_problems():
        return None
    inputs = ("requirements.txt", "_setup_deps.py", "requirements/constraints-python314.txt") + tuple(
        f"requirements/{group}.txt" for group in DEFAULT_GROUPS
    )
    constraint_lines = (ROOT / "requirements/constraints-python314.txt").read_text(encoding="utf-8").splitlines()
    names = [line.split("==", 1)[0].strip() for line in constraint_lines
             if line.strip() and not line.lstrip().startswith("#") and "==" in line]
    installed = {}
    for name in names:
        try:
            installed[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pass  # Constraints may list optional packages that are absent.
    return {
        "python": str(Path(sys.executable).resolve()),
        "version": sys.version,
        "packages": installed,
        "verification_inputs": _hash_inputs(inputs),
    }


def dependencies_verified() -> bool:
    return _stamp_matches(DEPS_STAMP, dependency_snapshot())


def record_dependency_verification() -> bool:
    return _record_stamp(DEPS_STAMP, dependency_snapshot())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("torch", "record-torch", "deps", "record-deps"))
    mode = parser.parse_args(argv).mode
    if mode == "torch":
        return 0 if torch_verified() else 1
    if mode == "record-torch":
        return 0 if record_torch_verification() else 1
    if mode == "deps":
        return 0 if dependencies_verified() else 1
    return 0 if record_dependency_verification() else 1


if __name__ == "__main__":
    sys.exit(main())
