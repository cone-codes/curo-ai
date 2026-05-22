@echo off
cd /d "%~dp0\.."
echo === Starting Chrome with remote debugging ===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_chrome_debug.ps1"
exit /b %ERRORLEVEL%
