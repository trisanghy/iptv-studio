#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGIN="trisanghy"
NAME="${1:-iptv-studio}"
DESCRIPTION='IPTV Studio 5.2 & Lite: gop M3U, kiem tra HLS/stream nhieu vong, chay nen Mac Windows Linux'

if ! [[ "$NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then echo 'Tên repository không hợp lệ.'; exit 2; fi
for cmd in git gh; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Thiếu $cmd. Hãy cài $cmd trước (Mac: brew install git gh)."; exit 2
  fi
done

# Avoid GH_TOKEN/GITHUB_TOKEN from an unrelated shell session.
unset GH_TOKEN GITHUB_TOKEN GH_HOST || true
ACTUAL="$(gh api user --jq '.login')" || { echo 'GitHub CLI chưa đăng nhập, chạy: gh auth login'; exit 2; }
if [[ "$ACTUAL" != "$LOGIN" ]]; then
  echo "DỪNG: GitHub CLI đang dùng '$ACTUAL', cần '$LOGIN'."
  echo "Chạy: gh auth switch -h github.com -u $LOGIN"
  exit 2
fi

if [[ -e "$ROOT/.git" ]]; then
  echo 'Thư mục đã có .git; bộ đăng lần đầu từ ZIP không tự ghi đè repository cũ.'
  echo 'Dùng tools/update_github.sh sau khi đã xác nhận remote.'
  exit 2
fi

if gh repo view "$LOGIN/$NAME" --json nameWithOwner >/dev/null 2>&1; then
  echo "Repository $LOGIN/$NAME đã tồn tại; dừng để tránh ghi đè."
  echo 'Hãy mở repository hoặc chọn tên khác: bash tools/upload_github.sh iptv-studio-v2'
  exit 2
fi

cd "$ROOT"
git init -b main
GITHUB_ID="$(gh api user --jq '.id')"
git config --local user.name "$LOGIN"
git config --local user.email "${GITHUB_ID}+${LOGIN}@users.noreply.github.com"
git add HUONG_DAN_DANG_GITHUB.md README.md .gitignore .gitattributes docs studio lite tools DANG_LEN_GITHUB_MAC.command DANG_LEN_GITHUB_WINDOWS.bat CAP_NHAT_MA_NGUON_MAC.command
if ! git diff --cached --quiet; then
  git commit -m 'Initial source: IPTV Studio 5.2 + Lite 5.2'
else
  echo 'Không có file mã nguồn để commit.'; exit 2
fi
# Only create PRIVATE repo. No Gist, M3U, report or private config upload.
if gh repo create "$LOGIN/$NAME" --private --description "$DESCRIPTION" --source "$ROOT" --remote origin --push; then
  echo
  echo "THÀNH CÔNG: https://github.com/$LOGIN/$NAME"
  echo 'Repository Private. Không có playlist, log, token hoặc dữ liệu cá nhân được commit.'
else
  echo 'GitHub chưa hoàn tất. Không tự thử lại / không tạo repo mới.'
  echo 'Kiểm tra bằng gh repo view, git status và git remote -v trước khi chạy tiếp.'
  exit 1
fi
