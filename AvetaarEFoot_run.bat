@echo off
REM Avetaar EFootball - install & run
REM Double-click me, or run from terminal: AvetaarEFoot_run.bat [bot]
if not exist venv (
    echo [AvetaarEFoot] Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo [AvetaarEFoot] Installing dependencies...
pip install -r requirements.txt
echo [AvetaarEFoot] Running...
if "%~1"=="bot" (
    python AvetaarEFoot.py --bot
) else (
    python AvetaarEFoot.py
)
pause
