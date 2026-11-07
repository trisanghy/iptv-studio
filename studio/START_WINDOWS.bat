@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0BOOTSTRAP_WINDOWS.ps1" -Mode gui
if errorlevel 1 (
  echo.
  echo CO LOI KHI KHOI DONG. Xem thong bao phia tren.
  pause
)
endlocal
