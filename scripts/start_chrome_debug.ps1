# Start Google Chrome with remote debugging (Windows)
# Run from project root:  .\start_chrome_debug.ps1

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path $ScriptDir -Parent
$Port = if ($env:CHROME_DEBUG_PORT) { $env:CHROME_DEBUG_PORT } else { "9222" }

Write-Host "=== Start Chrome for TRR scraping ===" -ForegroundColor Cyan

# --- Find Chrome ---
$findScript = Join-Path $ScriptDir "find_chrome.ps1"
$Chrome = & powershell -NoProfile -ExecutionPolicy Bypass -File $findScript 2>$null | Select-Object -Last 1
$Chrome = "$Chrome".Trim()

if (-not $Chrome -or -not (Test-Path -LiteralPath $Chrome)) {
    Write-Host ""
    Write-Host "ERROR: Google Chrome not found." -ForegroundColor Red
    Write-Host ""
    Write-Host '  $env:CHROME_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"'
    Write-Host "  (Get path from chrome://version)"
    exit 1
}

# --- Profile folder (separate from daily Chrome) ---
$UserData = Join-Path $ProjectRoot "data\chrome_cdp_profile"
New-Item -ItemType Directory -Force -Path $UserData | Out-Null

# --- Kill existing Chrome (required for debug port) ---
$chromeProcs = @(Get-Process -Name "chrome" -ErrorAction SilentlyContinue)
if ($chromeProcs.Count -gt 0) {
    Write-Host "Stopping $($chromeProcs.Count) Chrome process(es)..." -ForegroundColor Yellow
    $chromeProcs | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
}

# --- Launch Chrome (single argument string = reliable on Windows) ---
$chromeArgs = "--remote-debugging-port=$Port --user-data-dir=`"$UserData`" --no-first-run --no-default-browser-check https://www.therealreal.com/"

Write-Host "Chrome:  $Chrome"
Write-Host "Profile: $UserData"
Write-Host "Port:    $Port"
Write-Host ""

try {
    Start-Process -FilePath $Chrome -ArgumentList $chromeArgs
} catch {
    Write-Host "ERROR starting Chrome: $_" -ForegroundColor Red
    exit 1
}

# --- Wait for debug port ---
Write-Host "Waiting for debug port (up to 45s)..."
$ready = $false
$url = "http://127.0.0.1:$Port/json/version"

1..45 | ForEach-Object {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-RestMethod -Uri $url -TimeoutSec 2 -ErrorAction Stop
        Write-Host ""
        Write-Host "SUCCESS — Chrome debugging is active on port $Port" -ForegroundColor Green
        if ($r.Browser) { Write-Host "Browser: $($r.Browser)" }
        $ready = $true
        return
    } catch {}
    if ($_ % 5 -eq 0) { Write-Host "  still waiting ($_ s)..." }
}

if (-not $ready) {
    Write-Host ""
    Write-Host "FAILED — port $Port is not responding." -ForegroundColor Red
    Write-Host ""
    Write-Host "Try:"
    Write-Host "  1. Task Manager -> end all Google Chrome"
    Write-Host "  2. .\scripts\kill_chrome.ps1"
    Write-Host "  3. Run this script again"
    Write-Host "  4. If Chrome opened, sign in manually then run: .\scripts\check_chrome_debug.ps1"
    Write-Host ""
    Write-Host "Or set another port:"
    Write-Host '  $env:CHROME_DEBUG_PORT = "9223"'
    Write-Host '  $env:CHROME_CDP_URL = "http://127.0.0.1:9223"  # in .env too'
    exit 1
}
