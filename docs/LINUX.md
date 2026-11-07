# Hướng dẫn Linux

## Yêu cầu
Python 3, Internet. Hầu hết chức năng chạy với standard library. Các script Lite sử dụng **systemd user timer**, nên môi trường Linux cần có systemd user service.

## Studio giao diện
```bash
cd studio
bash START_LINUX.sh
```
Mở địa chỉ `http://127.0.0.1:<cổng>` mà chương trình in ra. Máy headless có thể cần trình duyệt từ môi trường desktop hoặc chuyển tiếp cổng an toàn (không mở công khai 0.0.0.0).

## Lite chạy nền
```bash
cd lite
bash INSTALL_LINUX.sh
python3 cli.py status
python3 cli.py run --no-publish
python3 cli.py config times '07:00,19:00'
python3 cli.py reschedule
python3 cli.py remove-schedule
```

Dùng `systemctl --user` để theo dõi timer/service nếu cần. Không tắt đăng nhập phiên người dùng nếu chưa bật `lingering`. Máy tắt không thể cập nhật. Gist mặc định không tự đăng.
