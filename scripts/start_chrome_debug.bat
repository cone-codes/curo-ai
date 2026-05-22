@echo off
REM Start Google Chrome with remote debugging (Windows CMD)
REM Double-click or run: scripts\start_chrome_debug.bat

set PORT=9222
if not "%CHROME_DEBUG_PORT%"=="" set PORT=%CHROME_DEBUG_PORT%

echo Chrome CDP URL: http://127.0.0.1:%PORT%
echo.
echo IMPORTANT:
echo   1. Close ALL Chrome windows first (check system tray).
echo   2. Sign in to https://www.therealreal.com/ when Chrome opens.
echo   3. Open a page with product listings.
echo   4. In a NEW terminal:  set PYTHONPATH=. ^&^& python chrome_crawler.py
echo.

set CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe
if not exist "%CHROME%" set CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe
if not exist "%CHROME%" (
    echo Google Chrome not found.
    pause
    exit /b 1
)

set USER_DATA=%LOCALAPPDATA%\Google\Chrome\User Data

start "" "%CHROME%" --remote-debugging-port=%PORT% --user-data-dir="%USER_DATA%" https://www.therealreal.com/
