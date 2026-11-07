#!/bin/bash
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "Thieu Python 3, dang cai qua Homebrew..."
    brew install python@3.13
  else
    echo "Thieu Python 3. Cai tai https://www.python.org/downloads/macos/"
    exit 1
  fi
fi
python3 cli.py install
