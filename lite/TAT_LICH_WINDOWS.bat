@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0BOOTSTRAP_WINDOWS.ps1" -Mode lite-remove
if errorlevel 1 (
  echo.
  echo KHONG THANH CONG. Xem loi phia tren.
)
echo.
pause
endlocal
