#!/usr/bin/env python3
"""
maic - Desktop Edition
Launch via start.bat/start.sh (recommended) or python run.py.
"""

import multiprocessing
import sys

multiprocessing.freeze_support()


def ensure_dependencies() -> None:
    """Validate source installations without changing the environment."""
    if getattr(sys, "frozen", False):
        return
    from maic.dependencies import python_problem, require_dependencies
    problem = python_problem()
    if problem:
        raise RuntimeError(problem)
    require_dependencies(("core",))


if __name__ == "__main__":
    try:
        ensure_dependencies()
    except RuntimeError as exc:
        sys.exit(str(exc))
    from maic.main import main

    main()
