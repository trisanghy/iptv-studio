# Hướng dẫn macOS

## Yêu cầu
- macOS có Terminal, Internet và Python 3 (khuyến nghị 3.10+).
- Script `START_MAC.command`/`INSTALL_MAC.command` có thể thử cài Python qua Homebrew nếu thiếu. Nếu chưa có Homebrew thì cài từ https://www.python.org/downloads/.

## Bản Studio (giao diện)
Mở Terminal trong thư mục mã nguồn:

```bash
cd studio
bash START_MAC.command
```

Cửa sổ trình duyệt mở `http://127.0.0.1:<cổng>`. Thao tác theo bốn bước quản lý nguồn → kiểm tra → xuất file → cập nhật Gist (tùy chọn). Nhấn `Control+C` trong Terminal để thoát.

## Bản Lite chạy nền

```bash
cd lite
bash INSTALL_MAC.command
```

Lịch mặc định **07:00, 19:00 theo giờ máy**. `launchd` gọi lệnh ở chế độ nền; không mở hộp thoại giao diện. Máy phải bật và phiên đăng nhập hoạt động để lịch chạy.

```bash
python3 cli.py status                  # kiểm tra trạng thái
python3 cli.py run --no-publish        # chạy thử KHÔNG đăng Gist
python3 cli.py config times '06:30,18:30'
python3 cli.py reschedule              # áp dụng lịch mới
python3 cli.py remove-schedule         # tắt lịch (giữ lại file)
```

Xem log trong `~/.iptv_studio/lite/run.log`. Không chạy đồng thời lịch của các phiên bản cũ.

## Gist
Nếu muốn cập nhật Gist từ chương trình: cài GitHub CLI từ https://cli.github.com/, đăng nhập với `gh auth login`, kiểm tra tài khoản bằng `gh api user --jq .login`. Không đưa token lên repository. Lịch Lite mặc định không đăng.
