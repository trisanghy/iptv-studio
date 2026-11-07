#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv-build
.venv-build/bin/python -m pip install --upgrade pyinstaller
.venv-build/bin/python -m PyInstaller --noconfirm --clean --onefile \
  --name IPTVStudio --add-data 'web:web' server.py
printf '\nLinux executable: %s/dist/IPTVStudio\n' "$PWD"
