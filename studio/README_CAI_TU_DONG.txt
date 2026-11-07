IPTV STUDIO 5.2 - TU KIEM TRA / TAI PYTHON KHI THIEU

WINDOWS 10/11:
1. Giai nen file ZIP ra thu muc co quyen ghi, vi du Downloads\iptv_studio.
2. Bam dup START_WINDOWS.bat. Neu thieu Python 3.10+, chuong trinh tu tai
   Python 3.13.17 embeddable tu https://www.python.org (khoang 11 MB),
   xac minh SHA-256 theo trang phat hanh chinh thuc, giai nen vao runtime\python.
   KHONG can quyen Admin, KHONG sua PATH, KHONG ghi de Python san co.
3. Sau do giao dien mo trong trinh duyet; lan sau se dung lai Python da tai.
4. Neu khong co Internet khi chay lan dau va may chua co Python: se bao loi ro rang.
5. Tat ca code IPTV Studio su dung thu vien chuan cua Python, KHONG can pip.
6. ffprobe la tuy chon nang cao: neu chua cai, chuc nang co the duoc bo qua.

MAC:
Bam START_MAC.command; neu khong co Python va Homebrew da cai, tu cai Python.
Neu chua co ca Python/Homebrew, can cai Python tu trang chinh thuc mot lan.

LINUX:
Chay bash START_LINUX.sh; neu thieu Python, script hoi xac nhan
truoc khi sudo apt/dnf/pacman/zypper. Khong cai thang khi chay ngam.

AN TOAN:
- Chi tai Python tu python.org va doi chieu SHA256 truoc khi chay.
- Chuong trinh khong tu dang GitHub, khong tu tao Gist neu khong duoc yeu cau.
- Neu loi, chup man hinh thong bao khoi dong de duoc ho tro.
