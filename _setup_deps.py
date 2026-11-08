"""Install the shared requirements and repair legacy cv2/LaMa conflicts."""
import argparse
import json
from importlib import metadata
from pathlib import Path
import subprocess
import sys
import tempfile

from maic.dependencies import ROOT, dependency_problems, installed_opencv, python_problem


def pip(*args):
    subprocess.run([sys.executable, "-m", "pip", *args], check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate without installing anything")
    parser.add_argument("--find-links", type=Path, help="Use a previously prepared wheel directory")
    parser.add_argument("--offline", action="store_true", help="Do not contact package indexes")
    args = parser.parse_args(argv)
    problem = python_problem()
    if problem:
        print(problem, file=sys.stderr)
        return 1
    try:
        if not args.check:
            if sys.prefix == sys.base_prefix:
                raise RuntimeError("Activate a virtual environment before installing dependencies.")
            source = []
            if args.find_links:
                source += ["--find-links", str(args.find_links.resolve())]
            if args.offline:
                source += ["--no-index"]
            # Resolve/download all requirements before removing legacy packages.
            with tempfile.TemporaryDirectory(prefix="maic-wheels-") as staging:
                variants = installed_opencv()
                report = Path(staging) / "install.json"
                pip("install", "--dry-run", "--report", str(report), "--only-binary=:all:",
                    "-r", str(ROOT / "requirements.txt"), *source)
                urls = [item["download_info"]["url"]
                        for item in json.loads(report.read_text(encoding="utf-8"))["install"]]
                if urls:
                    pip("download", "--no-deps", "--only-binary=:all:", "--dest", staging, *urls)
                if any(name != "opencv-python" for name in variants):
                    from maic.dependencies import requirements
                    cv2_spec = next(spec for spec in requirements(("core",)) if spec.startswith("opencv-python=="))
                    pip("download", "--no-deps", "--only-binary=:all:", "--dest", staging, cv2_spec, *source)
                legacy = []
                # torchaudio was installed by the old bootstrap, but maic
                # has no audio feature. Its exact Torch pin blocks upgrades.
                for package in ("simple-lama-inpainting", "torchaudio"):
                    try:
                        metadata.version(package)
                        legacy.append(package)
                    except metadata.PackageNotFoundError:
                        pass
                if any(name != "opencv-python" for name in variants):
                    # All variants share files: remove all, then reinstall just one.
                    legacy.extend(variants)
                if legacy:
                    pip("uninstall", "-y", *legacy)
                pip("install", "--no-index", "--find-links", staging,
                    "-r", str(ROOT / "requirements.txt"))
        problems = dependency_problems()
        if problems:
            raise RuntimeError("\n".join(problems))
        pip("check")
        subprocess.run([sys.executable, "-c",
                        "import cv2; import numpy as np; "
                        "assert cv2.cvtColor(np.zeros((2,2,3), dtype=np.uint8), cv2.COLOR_BGR2GRAY).shape == (2,2)"],
                       check=True)
        print("Python dependencies: OK")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Dependency setup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
