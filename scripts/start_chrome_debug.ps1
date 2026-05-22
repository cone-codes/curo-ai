# Start Google Chrome with remote debugging (Windows)
# Run from project root:  .\start_chrome_debug.ps1

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path $ScriptDir -Parent
$Port = if ($env:CHROME_DEBUG_PORT) { $env:CHROME_DEBUG_PORT } else { "9222" }

Write-Host "=== Start Chrome for TRR scraping ===" -ForegroundColor Cyan

# --- Find Chrome (dot-source avoids nested PowerShell swallowing errors) ---
$findScript = Join-Path $ScriptDir "find_chrome.ps1"
$Chrome = $null
try {
    $Chrome = & $findScript 2>&1 | Where-Object { $_ -is [string] -and $_.Trim() } | Select-Object -Last 1
    $Chrome = "$Chrome".Trim().Trim('"')
} catch {
    $Chrome = $null
}

if (-not $Chrome -or -not (Test-Path -LiteralPath $Chrome)) {
    Write-Host ""
    Write-Host "ERROR: Google Chrome not found." -ForegroundColor Red
    Write-Host ""
    Write-Host '  $env:CHROME_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"'
    Write-Host "  (Get path from chrome://version — copy 'Executable path')"
    Write-Host ""
    Write-Host "Then run:  .\start_chrome_debug.ps1"
    exit 1
}

# --- Profile folder (separate from daily Chrome) ---
$UserData = Join-Path $ProjectRoot "data\chrome_cdp_profile"
New-Item -ItemType Directory -Force -Path $UserData | Out-Null

# Stale lock can block debug port when Chrome was killed abruptly
$lockFiles = @(
    (Join-Path $UserData "SingletonLock"),
    (Join-Path $UserData "SingletonSocket"),
    (Join-Path $UserData "SingletonCookie")
)
foreach ($lf in $lockFiles) {
    if (Test-Path -LiteralPath $lf) {
        Remove-Item -LiteralPath $lf -Force -ErrorAction SilentlyContinue
    }
}

# --- Kill existing Chrome (required for debug port) ---
$chromeProcs = @(Get-Process -Name "chrome" -ErrorAction SilentlyContinue)
if ($chromeProcs.Count -gt 0) {
    Write-Host "Stopping $($chromeProcs.Count) Chrome process(es)..." -ForegroundColor Yellow
    $chromeProcs | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    $still = @(Get-Process -Name "chrome" -ErrorAction SilentlyContinue)
    if ($still.Count -gt 0) {
        Write-Host "WARNING: $($still.Count) Chrome process(es) still running. Close them in Task Manager, then re-run." -ForegroundColor Yellow
    }
}

# --- Launch Chrome (array ArgumentList is reliable on Windows) ---
$chromeArgList = @(
    "--remote-debugging-port=$Port",
    "--remote-debugging-address=127.0.0.1",
    "--user-data-dir=$UserData",
    "--no-first-run",
    "--no-default-browser-check",
    "https://www.therealreal.com/"
)

Write-Host "Chrome:  $Chrome"
Write-Host "Profile: $UserData"
Write-Host "Port:    $Port"
Write-Host ""

try {
    $proc = Start-Process -FilePath $Chrome -ArgumentList $chromeArgList -PassThru -ErrorAction Stop
    if (-not $proc) {
        throw "Start-Process returned no process handle"
    }
} catch {
    Write-Host "ERROR starting Chrome: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "If you see 'access denied', run PowerShell as your normal user (not elevated mismatch)."
    exit 1
}

Start-Sleep -Seconds 2
if ($proc.HasExited) {
    Write-Host "ERROR: Chrome exited immediately (exit code $($proc.ExitCode))." -ForegroundColor Red
    Write-Host "Check antivirus or try:  `$env:CHROME_EXECUTABLE = '...'  from chrome://version"
    exit 1
}

# --- Wait for debug port (for-loop + break; avoid return inside ForEach-Object) ---
Write-Host "Waiting for debug port (up to 45s)..."
$ready = $false
$lastErr = ""
$url = "http://127.0.0.1:$Port/json/version"

for ($i = 1; $i -le 45; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-RestMethod -Uri $url -TimeoutSec 2 -ErrorAction Stop
        Write-Host ""
        Write-Host "SUCCESS — Chrome debugging is active on port $Port" -ForegroundColor Green
        if ($r.Browser) { Write-Host "Browser: $($r.Browser)" }
        $ready = $true
        break
    } catch {
        $lastErr = $_.Exception.Message
    }
    if ($i % 5 -eq 0) {
        Write-Host "  still waiting ($i s)..."
    }
}

if (-not $ready) {
    Write-Host ""
    Write-Host "FAILED — port $Port is not responding." -ForegroundColor Red
    if ($lastErr) { Write-Host "Last error: $lastErr" }
    Write-Host ""
    Write-Host "Try:"
    Write-Host "  1. Task Manager -> end all Google Chrome"
    Write-Host "  2. .\scripts\kill_chrome.ps1"
    Write-Host "  3. .\scripts\diagnose_chrome_debug.ps1"
    Write-Host "  4. Run this script again"
    Write-Host ""
    Write-Host "Or set another port:"
    Write-Host '  $env:CHROME_DEBUG_PORT = "9223"'
    Write-Host '  $env:CHROME_CDP_URL = "http://127.0.0.1:9223"  # in .env too'
    exit 1
}

exit 0
