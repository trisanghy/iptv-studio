# Hướng dẫn Windows 10/11

## Studio có giao diện
1. Giải nén repository (tránh chạy trực tiếp trong file ZIP).
2. Mở `studio\START_WINDOWS.bat`.
3. Nếu thiếu Python, script sẽ thử tải Python portable chính thức và kiểm tra SHA-256. Cần kết nối Internet. Nếu tải tự động thất bại, cài Python 3 từ https://www.python.org/downloads/windows/.
4. Trình duyệt sẽ mở giao diện nội bộ. Thêm nguồn M3U, kiểm tra, xem CSV, xuất `iptv.m3u`.

## Lite chạy tự động
1. Giải nén, nhấp đúp `lite\INSTALL_WINDOWS.bat` (lần cài có cửa sổ CMD).
2. Sau khi cài, Windows Task Scheduler chạy theo lịch qua `pythonw.exe`, **không hiện CMD**.
3. Các lệnh hỗ trợ: `lite\CHAY_THU_WINDOWS.bat`, `lite\XEM_TRANG_THAI_WINDOWS.bat`, `lite\CAP_NHAT_LICH_WINDOWS.bat`, `lite\TAT_LICH_WINDOWS.bat`.
4. Thử bằng file `CHAY_THU_WINDOWS.bat` trước khi bật đăng Gist.

Lịch mặc định: 07:00 và 19:00 giờ máy. Máy phải đang bật và tác vụ trong phiên người dùng phải được phép chạy. Tệp runtime nằm ở thư mục dữ liệu người dùng theo cách cài Lite, không yêu cầu Admin để đăng ký lịch người dùng nếu quyền hệ thống cho phép.

## Kiểm tra lỗi
Nếu CMD chỉ báo thiếu Python và bộ tải tự động thất bại, kiểm tra kết nối mạng, tường lửa, hoặc cài Python trực tiếp. Không tắt Windows Defender để chạy phần mềm. Xem nhật ký tại `~/.iptv_studio/lite/run.log` (đường dẫn tương ứng trong thư mục hồ sơ Windows).
