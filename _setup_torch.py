"""Install and verify the tested Torch/torchvision pair in a separate process."""
import argparse
import json
from importlib import metadata
from pathlib import Path
import subprocess
import sys

from maic.dependencies import ROOT, python_problem, requirements

INDEXES = {
    "cpu": "https://download.pytorch.org/whl/cpu",
    "cu130": "https://download.pytorch.org/whl/cu130",
}
PROBE = """
import json
import torch
import torchvision
from torchvision.ops import nms
assert nms(torch.tensor([[0., 0., 1., 1.]]), torch.tensor([1.]), 0.5).tolist() == [0]
cuda = torch.cuda.is_available()
if cuda:
    x = torch.ones((8, 8), device="cuda")
    assert (x @ x).sum().item() == 512.
    assert nms(torch.tensor([[0.,0.,1.,1.]], device="cuda"),
               torch.tensor([1.], device="cuda"), 0.5).tolist() == [0]
print(json.dumps({"torch":torch.__version__, "torchvision":torchvision.__version__,
                  "cuda":cuda, "build_cuda":torch.version.cuda}))
"""


def versions():
    return dict(spec.split("==", 1) for spec in requirements(("ml",))
                if spec.startswith(("torch==", "torchvision==")))


def probe():
    result = subprocess.run([sys.executable, "-c", PROBE], text=True,
                            capture_output=True, timeout=180)
    if result.returncode:
        return None, result.stderr.strip() or result.stdout.strip()
    try:
        return json.loads(result.stdout.strip().splitlines()[-1]), ""
    except (ValueError, IndexError):
        return None, "Torch probe returned no valid result."


def matches(info, profile):
    if not info or any(info.get(name, "").split("+")[0] != version
                       for name, version in versions().items()):
        return False
    if profile == "cu130":
        return info.get("cuda") and info.get("build_cuda") == "13.0"
    if profile == "cpu":
        return info.get("build_cuda") is None
    return info.get("build_cuda") is None or bool(info.get("cuda"))


def detect_profile():
    """Only select the tested CUDA runtime when the driver advertises >=13.0."""
    if sys.platform == "darwin":
        return "cpu"
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
        import re
        match = re.search(r"CUDA (?:UMD )?Version:\s*(\d+)\.(\d+)", result.stdout)
        if result.returncode == 0 and match and tuple(map(int, match.groups())) >= (13, 0):
            return "cu130"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "cpu"


def install(profile, find_links=None, offline=False):
    source = ["--index-url", INDEXES[profile], "--extra-index-url", "https://pypi.org/simple"]
    if sys.platform == "darwin":
        if profile != "cpu":
            raise RuntimeError("The cu130 profile is supported only on Windows/Linux.")
        source = ["--index-url", "https://pypi.org/simple"]
    if find_links:
        source += ["--find-links", str(Path(find_links).resolve())]
    if offline:
        source = ["--no-index"] + (["--find-links", str(Path(find_links).resolve())] if find_links else [])
    suffix = "" if sys.platform == "darwin" else "+" + profile
    specs = [f"{name}=={version}{suffix}" for name, version in versions().items()]
    pip_spec = requirements(("bootstrap",))[0]
    if metadata.version("pip") != pip_spec.split("==", 1)[1]:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "--only-binary=:all:", pip_spec, *source],
            check=True,
        )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "--only-binary=:all:",
         "-c", str(ROOT / "requirements" / "constraints-python314.txt"), *specs, *source],
        check=True,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("auto", "cpu", "cu130"), default="auto")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--find-links")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    problem = python_problem()
    if problem:
        print(problem, file=sys.stderr)
        return 1
    try:
        info, error = probe()
        profile = args.profile
        if profile == "auto":
            profile = "cu130" if matches(info, "cu130") else detect_profile()
        if matches(info, profile):
            print(f"Torch/torchvision verified: {info['torch']} / {info['torchvision']} ({profile})")
            return 0
        if args.check:
            raise RuntimeError(error or f"Installed Torch pair does not satisfy the {profile} profile: {info}")
        if sys.prefix == sys.base_prefix:
            raise RuntimeError("Activate a virtual environment before installing Torch.")
        try:
            install(profile, args.find_links, args.offline)
            info, error = probe()
            if not matches(info, profile):
                raise RuntimeError(error or f"The installed {profile} build failed verification: {info}")
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            if args.profile != "auto" or profile == "cpu":
                raise
            print(f"CUDA setup failed: {exc}\nTrying the explicit CPU profile.")
            profile = "cpu"
            install(profile, args.find_links, args.offline)
            info, error = probe()
            if not matches(info, profile):
                raise RuntimeError(error or f"CPU verification failed: {info}")
        print(f"Torch/torchvision verified: {info['torch']} / {info['torchvision']} ({profile})")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"Torch setup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
