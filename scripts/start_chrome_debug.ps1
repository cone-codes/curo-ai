# Start Google Chrome with remote debugging (Windows PowerShell)
# From project root:  .\start_chrome_debug.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Port = if ($env:CHROME_DEBUG_PORT) { $env:CHROME_DEBUG_PORT } else { "9222" }

$Chrome = & "$ScriptDir\find_chrome.ps1"
if (-not $Chrome -or -not (Test-Path -LiteralPath $Chrome)) {
    Write-Host ""
    Write-Host "Google Chrome was not found automatically."
    Write-Host ""
    Write-Host "Fix options:"
    Write-Host "  1. Install Chrome: https://www.google.com/chrome/"
    Write-Host "  2. Or set the full path before running:"
    Write-Host '     $env:CHROME_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"'
    Write-Host "     .\start_chrome_debug.ps1"
    Write-Host ""
    Write-Host "To find your path: open Chrome, go to chrome://version — copy 'Executable path'."
    exit 1
}

$UserData = "$env:LOCALAPPDATA\Google\Chrome\User Data"
if (-not (Test-Path $UserData)) {
    Write-Warning "Default profile folder not found; using a debug profile in the project."
    $UserData = Join-Path (Split-Path $ScriptDir -Parent) "data\chrome_debug_profile"
    New-Item -ItemType Directory -Force -Path $UserData | Out-Null
}

Write-Host "Chrome CDP URL: http://127.0.0.1:$Port"
Write-Host "Using: $Chrome"
Write-Host "Profile: $UserData"
Write-Host ""
Write-Host "Close ALL Chrome windows first, then this window will start Chrome."
Write-Host "Sign in to https://www.therealreal.com/ when it opens."
Write-Host ""

Start-Process -FilePath $Chrome -ArgumentList @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=`"$UserData`"",
    "https://www.therealreal.com/"
)
