IPTV STUDIO LITE 5.2 - TU CAI THIEU PYTHON, KHONG CUA SO KHI CHAY LICH

WINDOWS:
1. Giai nen ZIP. Bam INSTALL_WINDOWS.bat (cai dat co hien CMD mot lan).
2. Neu thieu Python 3.10+, tu tai bo Python portable 3.13.17 tu python.org,
   doi chieu SHA-256, luu trong thu muc chuong trinh, khong can Admin.
3. Sau khi cai, app copy ca Python portable vao %LOCALAPPDATA%\IPTVStudioLite
   de lich khong bi mat khi xoa thu muc giai nen.
4. Task Scheduler chay pythonw.exe nen KHONG hien hop thoai/CMD khi den gio.
5. CHAY_THU_WINDOWS.bat: tao file local mot lan, KHONG dang GitHub.
6. XEM_TRANG_THAI_WINDOWS.bat: xem ket qua/log.
7. TAT_LICH_WINDOWS.bat: tat lich tu dong.
8. CAP_NHAT_LICH_WINDOWS.bat: tai lap lich sau khi thay gio.

MAC: bash INSTALL_MAC.command. Tu cai python@3.13 qua Homebrew neu can.
LINUX: bash INSTALL_LINUX.sh. Neu thieu python3, hoi truoc khi cai
        bang distro package manager.

KHONG CAN PIP: Toan bo thu vien chay IPTV la Python standard library.
ffprobe la cong cu nang cao TUY CHON, khong bat buoc.

CHU Y:
- May phai dang bat va co phien dang nhap de task user tu chay.
- Lich khong mo Chrome/trinh duyet/console, chi ghi log.
- GitHub tu dong MAC DINH TAT; can chap thuan rieng.
