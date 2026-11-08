@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title maic
set "VENV_PY=%~dp0venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    py -3.14 -c "import sys; sys.exit(sys.version_info[:2] != (3, 14))" >nul 2>&1
    if not errorlevel 1 (
        py -3.14 -m venv "%~dp0venv"
    ) else (
        python -c "import sys; sys.exit(sys.version_info[:2] != (3, 14))" >nul 2>&1
        if errorlevel 1 (
            echo Python 3.14 is required. Install it from https://python.org
            exit /b 1
        )
        python -m venv "%~dp0venv"
    )
    if errorlevel 1 exit /b 1
)
"%VENV_PY%" -c "from maic.dependencies import python_problem; import sys; sys.exit(python_problem())"
if errorlevel 1 (
    echo Existing venv was preserved. Select or create a Python 3.14 environment.
    exit /b 1
)
"%VENV_PY%" -m maic.launch_check torch >nul 2>&1
if errorlevel 1 (
    echo Verifying Torch and torchvision...
    "%VENV_PY%" "%~dp0_setup_torch.py"
    if errorlevel 1 exit /b 1
    "%VENV_PY%" -m maic.launch_check record-torch
    if errorlevel 1 exit /b 1
)
"%VENV_PY%" -m maic.launch_check deps >nul 2>&1
if errorlevel 1 (
    echo Setting up Python dependencies...
    "%VENV_PY%" "%~dp0_setup_deps.py"
    if errorlevel 1 exit /b 1
    "%VENV_PY%" -m maic.launch_check record-deps
    if errorlevel 1 exit /b 1
)
"%VENV_PY%" "%~dp0tools\bundled_modules.py" --apply-patches
if errorlevel 1 exit /b 1
"%VENV_PY%" "%~dp0run.py" %*
exit /b %errorlevel%
