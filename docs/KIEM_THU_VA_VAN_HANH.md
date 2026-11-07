# Kiểm thử và vận hành

## Các vòng kiểm tra

- **HTTP**: cú pháp URL, chuyển hướng, status code, MIME/HTML giả video, URL kèm tham số.
- **HLS**: đọc master/media playlist; kiểm tra một số segment từ playlist media; nhận biết MPEG-TS/MP4/AAC; xử lý key AES-128 khi có.
- **Thử lại**: lặp nhiều vòng để tránh kết luận từ một lần phản hồi chập chờn.
- **Kết luận**: OK / FAIL / UNKNOWN; kênh FAIL giữ URL trong nhóm `99 - KÊNH LỖI`, UNKNOWN ở nhóm cũ.

Đây là **heuristic**: URL có thể hết hạn theo thời gian, chặn theo IP/quốc gia, đòi cookie/headers hoặc DRM. Không coi kết quả OK là giấy bảo đảm 100%.

## File đầu ra
- `iptv.m3u`: bản chính, có thư mục `03 - LIVE EVENTS` ghi thời gian theo UTC+7.
- `iptv_goc_chua_loc.m3u`: bản trước khi nhóm lại.
- `BAO_CAO_KENH_IPTV.csv`: thông tin kiểm tra từng kênh và nguyên nhân.
- `iptv_can_kiem_tra.m3u`: bản cần rà soát nếu quá nhiều FAIL.

`*.m3u`, `*.csv`, `*.log`, `.env`, `__pycache__` được loại khỏi Git để tránh vô tình chia sẻ playlist hoặc dữ liệu vận hành.

## Kiểm thử trước khi dùng
Chạy từng bộ test:

```bash
(cd studio && python3 -m unittest discover -s tests -v)
(cd lite && python3 -m unittest discover -s tests -v)
```

## Khi muốn đăng playlist lên GitHub Gist
1. Chỉ làm khi có quyền phân phối nội dung.
2. Đăng nhập GitHub CLI, kiểm tra tài khoản đang dùng: `gh api user --jq .login`.
3. Xem kết quả quét và mở file `iptv.m3u` trước.
4. Chỉ cập nhật Gist đang sở hữu, tránh tự đăng liên tiếp khi lỗi API/404.
5. Sau cập nhật, mở URL Raw để xác nhận nội dung. Đừng coi việc GitHub API trả thành công là bằng chứng video phát được.

**Quan trọng:** Repository chứa mã nguồn và Gist chứa playlist là hai thứ khác nhau. Lệnh tạo repository trong bộ này **không đăng** playlist M3U lên GitHub.
