# Start Google Chrome with remote debugging (Windows PowerShell)
# From project root:  .\start_chrome_debug.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path $ScriptDir -Parent
$Port = if ($env:CHROME_DEBUG_PORT) { $env:CHROME_DEBUG_PORT } else { "9222" }

$Chrome = & "$ScriptDir\find_chrome.ps1"
if (-not $Chrome -or -not (Test-Path -LiteralPath $Chrome)) {
    Write-Host ""
    Write-Host "Google Chrome was not found."
    Write-Host 'Set:  $env:CHROME_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"'
    Write-Host "Get path from chrome://version in Chrome."
    exit 1
}

# Dedicated profile avoids "Chrome already running" blocking debug port
$UserData = Join-Path $ProjectRoot "data\chrome_cdp_profile"
New-Item -ItemType Directory -Force -Path $UserData | Out-Null

$chromeProcs = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
if ($chromeProcs) {
    Write-Host ""
    Write-Host "WARNING: Chrome is still running ($($chromeProcs.Count) processes)."
    Write-Host "Remote debugging will NOT work until Chrome is fully closed."
    Write-Host ""
    Write-Host "  1. Close all Chrome windows"
    Write-Host "  2. System tray -> Chrome -> Exit"
    Write-Host "  3. Or run:  .\scripts\kill_chrome.ps1"
    Write-Host ""
    $ans = Read-Host "Kill all Chrome processes now? (y/N)"
    if ($ans -eq "y" -or $ans -eq "Y") {
        $chromeProcs | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Host "Chrome processes stopped."
    } else {
        Write-Host "Continuing anyway (debug port may fail)..."
    }
}

Write-Host "Chrome CDP URL: http://127.0.0.1:$Port"
Write-Host "Chrome exe:    $Chrome"
Write-Host "Profile:       $UserData"
Write-Host "(First time: sign in to The RealReal in the window that opens.)"
Write-Host ""

$args = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=`"$UserData`"",
    "https://www.therealreal.com/"
)
Start-Process -FilePath $Chrome -ArgumentList $args

Write-Host "Waiting for debug port $Port ..."
$ready = $false
1..30 | ForEach-Object {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/version" -TimeoutSec 2
        Write-Host "OK — Chrome debugging is active."
        Write-Host "Browser: $($r.Browser)"
        $ready = $true
        break
    } catch {}
}
if (-not $ready) {
    Write-Host ""
    Write-Host "FAILED — nothing listening on port $Port."
    Write-Host "Try: close Chrome completely, run .\scripts\kill_chrome.ps1, then run this script again."
    exit 1
}
