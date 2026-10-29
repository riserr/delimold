@echo off
setlocal
set "APP_NODE=%~dp0Aplikasi\Runtime\node.exe"
if not exist "%APP_NODE%" (
echo Salin folder Runtime dari paket DELIMOLD lama yang sudah berfungsi ke Aplikasi\Runtime.
pause
exit /b 1
)
"%APP_NODE%" "%~dp0tools\manage.js" "%~dp0." supervisor
if errorlevel 1 pause
