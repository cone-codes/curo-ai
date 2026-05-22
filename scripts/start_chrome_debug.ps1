# Start Google Chrome with remote debugging (Windows)
# Run from project root:  .\start_chrome_debug.ps1

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path $ScriptDir -Parent
$Port = if ($env:CHROME_DEBUG_PORT) { $env:CHROME_DEBUG_PORT } else { "9222" }

Write-Host "=== Start Chrome for TRR scraping ===" -ForegroundColor Cyan

# --- Find Chrome ---
$findScript = Join-Path $ScriptDir "find_chrome.ps1"
$Chrome = $null
try {
    $chromeOut = & $findScript 2>&1
    foreach ($line in $chromeOut) {
        if ($line -is [string]) {
            $t = $line.Trim().Trim('"')
            if ($t -and (Test-Path -LiteralPath $t)) {
                $Chrome = $t
                break
            }
        }
    }
}
catch {
    $Chrome = $null
}

if (-not $Chrome) {
    Write-Host ""
    Write-Host "ERROR: Google Chrome not found." -ForegroundColor Red
    Write-Host ""
    Write-Host '  $env:CHROME_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"'
    Write-Host "  (Get path from chrome://version - Executable path)"
    Write-Host ""
    Write-Host "Then run:  .\start_chrome_debug.ps1"
    exit 1
}

# --- Profile folder ---
$UserData = Join-Path $ProjectRoot "data\chrome_cdp_profile"
New-Item -ItemType Directory -Force -Path $UserData | Out-Null

foreach ($name in @("SingletonLock", "SingletonSocket", "SingletonCookie")) {
    $lf = Join-Path $UserData $name
    if (Test-Path -LiteralPath $lf) {
        Remove-Item -LiteralPath $lf -Force -ErrorAction SilentlyContinue
    }
}

# --- Kill Chrome ---
$chromeProcs = @(Get-Process -Name "chrome" -ErrorAction SilentlyContinue)
if ($chromeProcs.Count -gt 0) {
    Write-Host "Stopping $($chromeProcs.Count) Chrome process(es)..." -ForegroundColor Yellow
    $chromeProcs | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
}

# --- Launch Chrome ---
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

$proc = $null
try {
    $proc = Start-Process -FilePath $Chrome -ArgumentList $chromeArgList -PassThru -ErrorAction Stop
}
catch {
    Write-Host "ERROR starting Chrome: $_" -ForegroundColor Red
    exit 1
}

if (-not $proc) {
    Write-Host "ERROR: Chrome did not start." -ForegroundColor Red
    exit 1
}

Start-Sleep -Seconds 2
if ($proc.HasExited) {
    Write-Host "ERROR: Chrome exited immediately (code $($proc.ExitCode))." -ForegroundColor Red
    exit 1
}

# --- Wait for debug port ---
Write-Host "Waiting for debug port (up to 45s)..."
$ready = $false
$lastErr = "unknown"
$url = "http://127.0.0.1:$Port/json/version"

for ($i = 1; $i -le 45; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-RestMethod -Uri $url -TimeoutSec 2 -ErrorAction Stop
        Write-Host ""
        Write-Host "SUCCESS - Chrome debugging is active on port $Port" -ForegroundColor Green
        if ($r.Browser) {
            Write-Host "Browser: $($r.Browser)"
        }
        $ready = $true
        break
    }
    catch {
        $lastErr = $_.Exception.Message
    }
    if (($i % 5) -eq 0) {
        Write-Host "  still waiting ($i s)..."
    }
}

if (-not $ready) {
    Write-Host ""
    Write-Host "FAILED - port $Port is not responding." -ForegroundColor Red
    Write-Host "Last error: $lastErr"
    Write-Host ""
    Write-Host "Try:"
    Write-Host "  1. Task Manager - end all Google Chrome"
    Write-Host "  2. .\scripts\kill_chrome.ps1"
    Write-Host "  3. .\scripts\diagnose_chrome_debug.ps1"
    Write-Host "  4. Run this script again"
    exit 1
}

exit 0
