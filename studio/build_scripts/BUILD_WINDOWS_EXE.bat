@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0\.."
py -3 -m venv .venv-build
if errorlevel 1 goto FAIL
.venv-build\Scripts\python.exe -m pip install --upgrade pyinstaller
if errorlevel 1 goto FAIL
.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --name IPTVStudio --add-data "web;web" server.py
if errorlevel 1 goto FAIL
echo Da tao dist\IPTVStudio.exe
pause
exit /b 0
:FAIL
echo Khong build duoc. Kiem tra Python 3, pip va Internet.
pause
exit /b 1
