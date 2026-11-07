#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v python3 >/dev/null || { echo 'Thiếu Python 3'; exit 1; }
python3 -m venv .venv-build
.venv-build/bin/python -m pip install --upgrade pyinstaller
.venv-build/bin/python -m PyInstaller --noconfirm --clean --windowed --onefile \
  --name IPTVStudio --add-data 'web:web' server.py
printf '\nỨng dụng Mac: %s/dist/IPTVStudio.app\n' "$PWD"
