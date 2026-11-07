# IPTV Studio 5.2 + IPTV Studio Lite 5.2

Công cụ **quản lý, hợp nhất và kiểm tra playlist IPTV M3U**, gồm hai phiên bản:

- **Studio (GUI)**: giao diện web chạy tại máy của bạn, thêm/sửa nguồn M3U, kiểm tra kênh nhiều vòng, xuất file và chủ động cập nhật GitHub Gist.
- **Studio Lite (chạy nền)**: không mở giao diện web; kiểm tra và cập nhật theo lịch của macOS / Windows / Linux, ghi nhật ký, không hiện CMD khi chạy theo lịch trên Windows.

**Mô tả repository:** Mã nguồn Python đa nền tảng cho công cụ gộp M3U, kiểm tra HLS/media, phân nhóm kênh lỗi, xuất `iptv.m3u` và cập nhật Gist tùy chọn.

> Repo này chỉ chứa **mã nguồn và hướng dẫn**; không kèm playlist đã tổng hợp, token GitHub, mật khẩu hay kết quả quét kênh. Repo nên để ở chế độ **Private**. Các URL nguồn trong cấu hình mặc định có thể thuộc bên thứ ba; chỉ sử dụng hoặc chia sẻ nội dung khi bạn có quyền.

## Tính năng chính

| Tính năng | Studio | Lite |
|---|:---:|:---:|
| Giao diện 4 bước | ✓ | — |
| Quản lý nhiều URL M3U | ✓ | ✓ (CLI) |
| Kiểm tra URL/HTTP, HLS master/media, segment TS/MP4/AAC và thử lại nhiều vòng | ✓ | ✓ |
| Báo cáo `OK` / `FAIL` / `UNKNOWN` | ✓ | ✓ |
| Giữ `FAIL` trong nhóm cuối `99 - KÊNH LỖI` | ✓ | ✓ |
| Tên nhóm thứ ba có ngày giờ kiểm tra (UTC+7) | ✓ | ✓ |
| File đầu ra `iptv.m3u` | ✓ | ✓ |
| Cập nhật Gist cũ nếu chủ động bật | ✓ | ✓ |
| Chạy nền và hẹn giờ không mở hộp thoại | — | ✓ |

**Thứ tự nhóm mặc định:** `01 - VTV NGUỒN 1` → `02 - VTV NGUỒN 3` → `03 - LIVE EVENTS 🔴 | Kiểm tra: DD/MM/YYYY HH:mm` → các nhóm khác → `99 - KÊNH LỖI`.

Phân loại: `OK` có bằng chứng nội dung media phù hợp; `FAIL` là lỗi rõ ràng; `UNKNOWN` được giữ ở nhóm cũ vì có thể do DRM, chặn vùng, yêu cầu cookie, giới hạn mạng hoặc timeout. **Kiểm tra tự động không bảo đảm 100% khả năng xem trên mọi thiết bị**.

## Bắt đầu nhanh

### macOS

```bash
cd studio
bash START_MAC.command
```

Để cài bản chạy nền (bản Lite):

```bash
cd lite
bash INSTALL_MAC.command
```

### Windows

Giải nén repository, vào `studio` và chạy **`START_WINDOWS.bat`**. Hoặc vào `lite` và chạy **`INSTALL_WINDOWS.bat`**. Trình cài sẽ kiểm tra Python; nếu thiếu thì thử tải bản Python portable. Chạy theo lịch bằng Task Scheduler với `pythonw.exe` để không hiện cửa sổ.

### Linux

```bash
cd studio && bash START_LINUX.sh
# hoặc:
cd lite && bash INSTALL_LINUX.sh
```

Cần Python 3 (khuyến nghị 3.10+) và mạng Internet khi lấy playlist. **Không có thư viện pip bắt buộc** (standard library); `ffprobe`/FFmpeg là tùy chọn nâng cao.

## Sử dụng Studio (GUI)

1. **Nguồn M3U:** Thêm URL, đổi tên, bật/tắt nguồn và chọn vai trò VTV/nguồn thường.
2. **Kiểm tra:** Chọn 2–4 vòng, timeout và số tác vụ song song; kiểm tra mẫu segment HLS, xác định kênh `FAIL` và `UNKNOWN`.
3. **Xuất playlist:** Xem báo cáo CSV và tải `iptv.m3u`. Kiểm tra kết quả trước khi đăng.
4. **GitHub (tùy chọn):** Chỉ bấm cập nhật Gist khi đúng tài khoản và chắc chắn về quyền phân phối các luồng.

GUI chạy nội bộ trên `127.0.0.1` của máy; đóng terminal để dừng GUI.

## Sử dụng Studio Lite

```bash
cd lite
python3 cli.py status
python3 cli.py run --no-publish
python3 cli.py sources list
python3 cli.py sources add 'https://example.com/play.m3u' 'Nguồn của tôi'
python3 cli.py config times '07:00,19:00'
python3 cli.py reschedule
python3 cli.py remove-schedule
```

Windows có thể dùng `py -3` hoặc file `.bat` tương ứng. Lite mặc định **không tự đăng GitHub**. Muốn kích hoạt (sau khi đã kiểm tra tài khoản, Gist và quyền sử dụng nội dung): `python3 cli.py config publish on`.

## Cấu trúc mã nguồn

```text
iptv-studio/
├── studio/                # GUI, API server, web frontend, kiểm tra stream, xuất M3U
│   ├── core.py
│   ├── advanced_probe.py
│   ├── server.py
│   ├── github_publish.py
│   ├── web/
│   └── tests/
├── lite/                  # CLI, worker nền, lịch, log, kiểm tra stream
│   ├── cli.py
│   ├── lite_worker.py
│   ├── scheduler_lite.py
│   └── tests/
├── docs/                  # hướng dẫn và an toàn
├── tools/                 # công cụ đăng mã nguồn vào repository riêng
└── README.md
```

## Kiểm thử

```bash
cd studio && python3 -m unittest discover -s tests -v
cd ../lite && python3 -m unittest discover -s tests -v
```

Các bài test mô phỏng HTTP/HLS, Gist hoặc logic gộp; **không chứng thực mọi luồng phát thực tế**. Để kiểm tra chi tiết, xem [docs/KIEM_THU_VA_VAN_HANH.md](docs/KIEM_THU_VA_VAN_HANH.md).

## Tài liệu

- [Hướng dẫn macOS](docs/MACOS.md)
- [Hướng dẫn Windows](docs/WINDOWS.md)
- [Hướng dẫn Linux](docs/LINUX.md)
- [Kiểm thử, lỗi thường gặp và GitHub Gist](docs/KIEM_THU_VA_VAN_HANH.md)
- [Lưu ý bảo mật và quyền sử dụng](docs/AN_TOAN.md)

Tài liệu gốc chi tiết nằm trong mỗi thư mục (`HUONG_DAN_*.txt`, `README_CAI_TU_DONG.txt`).

## Giấy phép

Chưa gắn giấy phép nguồn mở. Repository mặc định là **Private**; chỉ chuyển sang Public và bổ sung giấy phép nếu chủ sở hữu lựa chọn và đã xác minh quyền đối với toàn bộ mã và tài nguyên liên quan.
