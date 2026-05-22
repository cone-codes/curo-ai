@echo off
setlocal EnableExtensions
REM From project root:  start_chrome_debug.bat
REM Or PowerShell:      .\scripts\start_chrome_debug.bat

set PORT=9222
if not "%CHROME_DEBUG_PORT%"=="" set PORT=%CHROME_DEBUG_PORT%

echo Chrome CDP URL: http://127.0.0.1:%PORT%
echo.

REM --- Find Chrome (env override, then PowerShell helper) ---
set "CHROME="
if defined CHROME_EXECUTABLE (
    if exist "%CHROME_EXECUTABLE%" set "CHROME=%CHROME_EXECUTABLE%"
)

if not defined CHROME (
    for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0find_chrome.ps1" 2^>nul`) do set "CHROME=%%i"
)

if not defined CHROME (
    if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
        set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
    )
)
if not defined CHROME (
    if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
        set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
    )
)
if not defined CHROME (
    if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
        set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
    )
)

if not defined CHROME (
    echo.
    echo Google Chrome not found.
    echo.
    echo 1. Install Chrome: https://www.google.com/chrome/
    echo.
    echo 2. Or set your path manually, then run this script again:
    echo    set CHROME_EXECUTABLE=C:\Program Files\Google\Chrome\Application\chrome.exe
    echo    start_chrome_debug.bat
    echo.
    echo To find the path: in Chrome open chrome://version and copy "Executable path".
    echo.
    pause
    exit /b 1
)

set "USER_DATA=%LOCALAPPDATA%\Google\Chrome\User Data"
if not exist "%USER_DATA%" (
    set "USER_DATA=%~dp0..\data\chrome_debug_profile"
    if not exist "%USER_DATA%" mkdir "%USER_DATA%"
)

echo Using: %CHROME%
echo Profile: %USER_DATA%
echo.
echo Close ALL Chrome windows first ^(system tray - Exit^).
echo Sign in to https://www.therealreal.com/ when Chrome opens.
echo.

start "" "%CHROME%" --remote-debugging-port=%PORT% --user-data-dir="%USER_DATA%" https://www.therealreal.com/

endlocal
