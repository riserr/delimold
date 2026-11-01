@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :error
python -m PyInstaller --noconfirm --clean --onedir --windowed --name DELIMOLD main.py
if errorlevel 1 goto :error
echo Build selesai: dist\DELIMOLD\DELIMOLD.exe
pause
exit /b 0
:error
echo Build gagal. Lihat pesan di atas.
pause
exit /b 1
