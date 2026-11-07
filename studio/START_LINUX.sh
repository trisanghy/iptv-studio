#!/bin/sh
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3 chua duoc cai. Dang tim trinh quan ly goi...'
  if [ -t 0 ]; then
    printf 'Cho phep cai Python bang trinh quan ly goi he thong? [y/N]: '
    read answer
    case "$answer" in y|Y|yes|YES) ;; *) echo 'Da huy, chua sua he thong.'; exit 1;; esac
  else
    echo 'Khong the tu cai Python khi chay nen. Cai Python 3 thu cong mot lan.'; exit 1
  fi
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y python3
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --needed python
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper install -y python3
  else
    echo 'Khong phat hien package manager. Cai Python 3 bang quan ly goi distro.'; exit 1
  fi
fi
exec python3 server.py
