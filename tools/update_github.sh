#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED="https://github.com/trisanghy/iptv-studio"
# For a custom repository name, pass full 'trisanghy/name' as first argument.
REPO="${1:-trisanghy/iptv-studio}"
[[ "$REPO" =~ ^trisanghy/[A-Za-z0-9._-]+$ ]] || { echo 'Tên repo không phù hợp.'; exit 2; }
unset GH_TOKEN GITHUB_TOKEN GH_HOST || true
ACCOUNT="$(gh api user --jq '.login')" || exit 2
[[ "$ACCOUNT" == 'trisanghy' ]] || { echo 'Sai tài khoản GitHub, dừng.'; exit 2; }
[[ -d "$ROOT/.git" ]] || { echo 'Chưa có repository local. Hãy đăng lần đầu trước.'; exit 2; }
REMOTE="$(git -C "$ROOT" remote get-url origin)" || exit 2
case "$REMOTE" in
  "https://github.com/$REPO"|"https://github.com/$REPO.git"|"git@github.com:$REPO"|"git@github.com:$REPO.git") ;;
  *) echo "Origin không đúng: $REMOTE. Không push."; exit 2;;
esac
cd "$ROOT"
git add HUONG_DAN_DANG_GITHUB.md README.md .gitignore .gitattributes docs studio lite tools DANG_LEN_GITHUB_MAC.command DANG_LEN_GITHUB_WINDOWS.bat CAP_NHAT_MA_NGUON_MAC.command
if ! git diff --cached --quiet; then
 git commit -m "Update source $(date +%Y-%m-%d)"
fi
git push origin main
echo "Đã cập nhật https://github.com/$REPO"
