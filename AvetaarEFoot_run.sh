#!/usr/bin/env bash
# Avetaar EFootball - install & run
# ./AvetaarEFoot_run.sh [bot]
set -e
if [ ! -d venv ]; then
    echo "[AvetaarEFoot] Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "[AvetaarEFoot] Installing dependencies..."
pip install -r requirements.txt
echo "[AvetaarEFoot] Running..."
if [ "$1" = "bot" ]; then
    python AvetaarEFoot.py --bot
else
    python AvetaarEFoot.py
fi
