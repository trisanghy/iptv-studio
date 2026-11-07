IPTV STUDIO 5.0 — HƯỚNG DẪN NHANH (MAC / WINDOWS / LINUX)
======================================================
MỤC ĐÍCH
- Gộp hai nguồn IPTV mặc định và nguồn M3U mới bạn thêm qua giao diện.
- Xếp danh mục: 01 - VTV NGUỒN 1; 02 - VTV NGUỒN 3;
  03 - LIVE EVENTS 🔴 | Kiểm tra: DD/MM/YYYY HH:mm; các nhóm khác;
  99 - KÊNH LỖI (cuối cùng).
- Thời gian ghi theo Việt Nam (UTC+7) sau khi hoàn tất vòng kiểm tra.
- File chính: iptv.m3u; đồng thời có iptv_goc_chua_loc.m3u,
  BAO_CAO_KENH_IPTV.csv (lý do chi tiết và kết quả từng vòng).
- Kênh lỗi rõ ràng (FAIL) chuyển sang 99 - KÊNH LỖI, không xóa URL.
  Kênh UNKNOWN giữ nguyên nhóm để tránh loại nhầm kênh sống.

CHẠY ỨNG DỤNG (KHÔNG CẦN GH, HOMEBREW, THƯ VIỆN PIP)
- Mac: giải nén, chạy START_MAC.command, hoặc Terminal: bash START_MAC.command.
- Windows: giải nén, chạy START_WINDOWS.bat (cần Python 3, cài tại python.org).
- Linux: trong Terminal chạy bash START_LINUX.sh (cần python3).
- Giao diện sẽ tự mở trên trình duyệt qua http://127.0.0.1:PORT
- Chương trình không tải nội dung lên GitHub nếu bạn không bấm Đăng.
- Để thoát: Ctrl+C ở Terminal hoặc đóng cửa sổ Console.

4 BƯỚC TRONG GIAO DIỆN
1. Nguồn: nhập M3U URL, chọn nguồn VTV ưu tiên hoặc nguồn thông thường.
2. Kiểm tra: chọn 2 / 3 / 4 vòng độc lập (khuyến nghị 3), timeout 8–12s;
   số luồng 4–12 nếu mạng yếu; số thử lại 2. Bật ffprobe nếu bạn đã cài
   FFmpeg và muốn xử lý luồng UNKNOWN. Tránh bật chế độ nghiêm ngặt nếu VPN/CDN hay chặn.
3. Xuất file: bấm tạo playlist, chờ kiểm tra xong. Xem CSV khi nhiều FAIL/UNKNOWN.
4. GitHub (TÙY CHỌN): chỉ cập nhật Gist bạn sở hữu; để tên file iptv.m3u.
   Nếu bạn vẫn cần link VTV_FULL_2_NGUON.m3u, chọn Giữ link cũ.

THUẬT TOÁN KIỂM TRA
- Vòng 1: cú pháp URL, HTTP GET, redirect, status, HTML/JSON giả video;
  xử lý UA/Referer từ M3U/Kodi URL.
- Vòng 2: nếu HLS, giải playlist master -> media -> segment gần nhất, kiểm tra
  MPEG-TS/MP4/AAC bytes thật, xem init segment, kiểm tra AES-128 key nếu cần.
- Vòng 3 và 4: yêu cầu lại độc lập để giảm sai do CDN/playlist cũ/hết token.
- Nếu >=2 vòng có bằng chứng dữ liệu media thật: OK. Nếu liên tiếp lỗi rõ ràng:
  FAIL. Trường hợp mập mờ/403/429/timeout/DRM: UNKNOWN.
- Không bảo đảm 100% kênh chạy ở mọi mạng, iPhone hoặc vào mọi thời điểm.
  Luồng IP khóa vùng, DRM hoặc cần cookie đăng nhập có thể không kiểm tra được.
- Khi kênh chập chờn, CSV có kết quả từng vòng để bạn đối chiếu.

CHỨNG NHẬN THỜI GIAN
- Gắn ngay vào tên nhóm thứ 3: "03 - LIVE EVENTS 🔴 | Kiểm tra: DD/MM/YYYY HH:mm".
- Nếu bỏ tick kiểm tra: "03 - LIVE EVENTS 🔴 | CHƯA KIỂM TRA".
- M3U không hỗ trợ thư mục rỗng; nếu tất cả kênh Live Events chuyển KÊNH LỖI,
  nhóm Live Events sẽ không xuất hiện trong app IPTV (dù thứ tự được giữ theo quy tắc).

GITHUB GIST — CẦN GH CLI CHỈ KHI BẠN CHỦ ĐỘNG ĐĂNG
- Cài GitHub CLI từ https://cli.github.com/
- Đăng nhập: gh auth login -h github.com --scopes gist
- Kiểm tra đang dùng tài khoản nào: gh api user --jq .login
- Gist hiện tại: e63b2927598a4b932b3708ddd3183aaa / tài khoản trisanghy.
- Chương trình không mặc định tự tạo Gist khác khi cập nhật lỗi.
- Nếu API ghi thành công mà link Raw chưa xác minh, chỉ báo CẢNH BÁO.
- Tài khoản GitHub từng bị đình chỉ: KHÔNG dùng tài khoản khác để né đình chỉ;
  hãy kiểm tra chính sách dịch vụ trước khi đưa playlist lên mạng.

CHẠY KIỂM THỬ NỘI BỘ
  Mac/Linux: python3 -m unittest discover -s tests -v
  Windows: py -3 -m unittest discover -s tests -v
Bản 5.0 đã được thử bằng server giả lập HTTP/HLS, không kiểm tra tất cả
nguồn kênh thật từ mạng của bạn.

CÁCH ĐÓNG GÓI FILE CHẠY ĐỘC LẬP
- Có thư mục build_scripts với script tạo .app (Mac), .exe (Windows),
  binary (Linux). Cần build trên ĐÚNG hệ điều hành tương ứng.
- ZIP nguồn vẫn dùng chung Mac / Windows / Linux nếu đã cài Python 3.
- Xem thêm: HUONG_DAN_MAC.txt, HUONG_DAN_WINDOWS.txt, HUONG_DAN_LINUX.txt.
