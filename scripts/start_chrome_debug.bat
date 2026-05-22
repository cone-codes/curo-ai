@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set PORT=9222
if not "%CHROME_DEBUG_PORT%"=="" set PORT=%CHROME_DEBUG_PORT%

echo Chrome CDP URL: http://127.0.0.1:%PORT%
echo.

set "CHROME="
if defined CHROME_EXECUTABLE if exist "%CHROME_EXECUTABLE%" set "CHROME=%CHROME_EXECUTABLE%"

if not defined CHROME (
    for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0find_chrome.ps1" 2^>nul`) do set "CHROME=%%i"
)

if not defined CHROME if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)
if not defined CHROME if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
)

if not defined CHROME (
    echo Google Chrome not found.
    echo Set CHROME_EXECUTABLE=full path to chrome.exe from chrome://version
    pause
    exit /b 1
)

REM Dedicated profile in project — avoids profile lock when Chrome was already open
set "USER_DATA=%~dp0..\data\chrome_cdp_profile"
if not exist "%USER_DATA%" mkdir "%USER_DATA%"

tasklist /FI "IMAGENAME eq chrome.exe" 2>nul | find /I "chrome.exe" >nul
if %ERRORLEVEL%==0 (
    echo.
    echo WARNING: Chrome is still running. Debug port will NOT work.
    echo Close Chrome completely or run:  powershell -File scripts\kill_chrome.ps1
    echo.
    pause
)

echo Using: %CHROME%
echo Profile: %USER_DATA%
echo.

start "" "%CHROME%" --remote-debugging-port=%PORT% --user-data-dir="%USER_DATA%" https://www.therealreal.com/

echo Waiting for port %PORT% ...
timeout /t 5 /nobreak >nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_chrome_debug.ps1"
set ERR=%ERRORLEVEL%
if %ERR% NEQ 0 pause
exit /b %ERR%
