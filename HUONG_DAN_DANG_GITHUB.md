# Đưa mã nguồn lên GitHub bằng tài khoản `trisanghy`

## Trên Mac

Sau khi tải file ZIP vào Downloads:

```bash
cd ~/Downloads
unzip -o IPTV_STUDIO_GITHUB_SOURCE_5_2.zip
bash iptv-studio/DANG_LEN_GITHUB_MAC.command
```

Script kiểm tra `gh api user`, yêu cầu tài khoản `trisanghy`, tạo repo **Private** `trisanghy/iptv-studio` và đẩy commit `main`. Không đăng playlist/Gist; không in hoặc thu thập token. Máy cần có `git` và `gh`; nếu thiếu: `brew install git gh`. Nếu chưa đăng nhập CLI: `gh auth login`.

Nếu tên repo đã tồn tại, chương trình **dừng** để tránh ghi đè. Có thể tạo repo tên khác bằng `bash iptv-studio/DANG_LEN_GITHUB_MAC.command iptv-studio-source`.

## Windows

- Cài [Git for Windows](https://git-scm.com/download/win) và [GitHub CLI](https://cli.github.com/).
- Đăng nhập GitHub CLI và kiểm tra: `gh api user --jq .login`.
- Giải nén, nhấp đúp `DANG_LEN_GITHUB_WINDOWS.bat` trong thư mục `iptv-studio`.

## Cập nhật mã nguồn sau này

Sau khi đã tạo repo lần đầu, khi thay đổi các file của **bản mã nguồn đã giải nén**, chạy:

```bash
bash iptv-studio/CAP_NHAT_MA_NGUON_MAC.command
```

Nó kiểm tra remote phải thuộc `trisanghy/iptv-studio` và chỉ `git push origin main`; không đụng Gist. Nếu dùng tên repo khác, truyền `trisanghy/ten-repo` vào script cập nhật.

## Quan trọng

Không có lệnh nào trong bộ này tự đẩy lên GitHub từ môi trường ChatGPT. Bạn phải chạy trên máy đã đăng nhập GitHub. Repo Private giúp tránh công khai mã khi chưa rà soát. Không tái đăng tải playlist có vấn đề bản quyền lên tài khoản khác để né đình chỉ GitHub.
