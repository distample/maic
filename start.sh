#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -e venv/bin/python ]; then
    PY=""
    for candidate in python3.14 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 &&
           "$candidate" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 14))'; then
            PY="$candidate"
            break
        fi
    done
    if [ -z "$PY" ]; then
        echo "Python 3.14 is required. Install Python and its venv support first." >&2
        exit 1
    fi
    "$PY" -m venv venv
fi
venv/bin/python -c 'from maic.dependencies import python_problem; import sys; sys.exit(python_problem())'
if ! venv/bin/python -m maic.launch_check torch >/dev/null 2>&1; then
    echo "Verifying Torch and torchvision..."
    venv/bin/python _setup_torch.py
    venv/bin/python -m maic.launch_check record-torch
fi
if ! venv/bin/python -m maic.launch_check deps >/dev/null 2>&1; then
    echo "Setting up Python dependencies..."
    venv/bin/python _setup_deps.py
    venv/bin/python -m maic.launch_check record-deps
fi
venv/bin/python tools/bundled_modules.py --apply-patches
exec venv/bin/python run.py "$@"
