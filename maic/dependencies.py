"""Dependency checks without ML imports or installation side effects."""
from __future__ import annotations

from importlib import metadata
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GROUPS = ("bootstrap", "core", "ml", "pdf", "kcc", "kfx")
GROUPS = (*DEFAULT_GROUPS, "gui")
OPENCV_PACKAGES = (
    "opencv-python", "opencv-python-headless",
    "opencv-contrib-python", "opencv-contrib-python-headless",
)


def python_problem(version=None):
    version = sys.version_info if version is None else version
    if tuple(version[:2]) != (3, 14):
        return "maic's tested environment requires CPython 3.14 (see .python-version)."
    return None


def requirements(groups=DEFAULT_GROUPS):
    """Read the same direct requirements files consumed by pip."""
    result = []
    for group in groups:
        if group not in GROUPS:
            raise ValueError(f"Unknown dependency group: {group}")
        for line in (ROOT / "requirements" / f"{group}.txt").read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                result.append(line)
    return result


def installed_opencv():
    result = []
    for name in OPENCV_PACKAGES:
        try:
            metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
        result.append(name)
    return result


def dependency_problems(groups=DEFAULT_GROUPS):
    try:
        from packaging.requirements import Requirement
    except ImportError:
        return ["packaging is missing; run python _setup_deps.py"]
    problems = []
    for spec in requirements(groups):
        req = Requirement(spec)
        try:
            version = metadata.version(req.name)
        except metadata.PackageNotFoundError:
            problems.append(f"Missing {spec}")
        else:
            if not req.specifier.contains(version):
                problems.append(f"{req.name} {version} does not satisfy {spec}")
    variants = installed_opencv()
    if len(variants) > 1:
        problems.append("Conflicting cv2 providers: " + ", ".join(variants))
    try:
        metadata.version("simple-lama-inpainting")
    except metadata.PackageNotFoundError:
        pass
    else:
        problems.append("Legacy simple-lama-inpainting conflicts with this environment; run python _setup_deps.py")
    return problems


def require_dependencies(groups=DEFAULT_GROUPS):
    problems = dependency_problems(groups)
    if problems:
        raise RuntimeError("\n".join(problems) + "\nRun python _setup_deps.py before starting maic.")
