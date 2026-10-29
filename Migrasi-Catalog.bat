@echo off
setlocal
if "%~1"=="" (
echo Tarik file Database\catalog.js lama ke BAT ini.
pause
exit /b 1
)
"%~dp0Aplikasi\Runtime\node.exe" "%~dp0tools\manage.js" "%~dp0." migrate "%~1"
pause
