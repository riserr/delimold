@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :error
python -m PyInstaller --noconfirm --clean --onedir --contents-directory RUNTIME --windowed --name DELIMOLD main.py
if errorlevel 1 goto :error
if exist "release\TENDERLOIN" rmdir /s /q "release\TENDERLOIN"
if not exist "release\TENDERLOIN\APLIKASI" mkdir "release\TENDERLOIN\APLIKASI"
copy /Y "dist\DELIMOLD\DELIMOLD.exe" "release\TENDERLOIN\APLIKASI\DELIMOLD.exe" >nul
xcopy "dist\DELIMOLD\RUNTIME" "release\TENDERLOIN\APLIKASI\RUNTIME" /E /I /Y >nul
copy /Y "config.master.example.json" "release\TENDERLOIN\APLIKASI\config.json" >nul
if exist "seed\catalog.js" (
  if not exist "release\TENDERLOIN\APLIKASI\seed" mkdir "release\TENDERLOIN\APLIKASI\seed"
  copy /Y "seed\catalog.js" "release\TENDERLOIN\APLIKASI\seed\catalog.js" >nul
)
echo Build selesai: release\TENDERLOIN\APLIKASI\DELIMOLD.exe
pause
exit /b 0
:error
echo Build gagal. Lihat pesan di atas.
pause
exit /b 1
