# Print diagnostics when Chrome debug (step 3) fails on Windows
$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path $ScriptDir -Parent
$Port = if ($env:CHROME_DEBUG_PORT) { $env:CHROME_DEBUG_PORT } else { "9222" }

Write-Host "=== Chrome CDP diagnostics ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host "Port:    $Port"
Write-Host ""

Write-Host "[1] PowerShell version"
$PSVersionTable.PSVersion
Write-Host ""

Write-Host "[2] Execution policy (current process)"
Get-ExecutionPolicy
Write-Host ""

Write-Host "[3] Chrome executable"
$findScript = Join-Path $ScriptDir "find_chrome.ps1"
try {
    $chrome = & $findScript 2>&1 | Where-Object { $_ -is [string] } | Select-Object -Last 1
    $chrome = "$chrome".Trim()
    if ($chrome -and (Test-Path -LiteralPath $chrome)) {
        Write-Host "  OK: $chrome" -ForegroundColor Green
    } else {
        Write-Host "  NOT FOUND" -ForegroundColor Red
        Write-Host '  Set: $env:CHROME_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"'
    }
} catch {
    Write-Host "  ERROR: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "[4] Chrome processes"
$procs = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
if ($procs) {
    Write-Host "  $($procs.Count) chrome.exe running (debug port usually fails if daily Chrome is open)" -ForegroundColor Yellow
} else {
    Write-Host "  None (good before start_chrome_debug)" -ForegroundColor Green
}
Write-Host ""

Write-Host "[5] Profile directory"
$profile = Join-Path $ProjectRoot "data\chrome_cdp_profile"
Write-Host "  $profile"
if (Test-Path $profile) {
    Write-Host "  Exists" -ForegroundColor Green
} else {
    Write-Host "  Will be created on first start" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "[6] Debug port $Port"
$url = "http://127.0.0.1:$Port/json/version"
try {
    $r = Invoke-RestMethod -Uri $url -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  OK — debugging active" -ForegroundColor Green
    Write-Host "  $($r.Browser)"
} catch {
    Write-Host "  NOT LISTENING: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Run: .\scripts\kill_chrome.ps1  then  .\start_chrome_debug.ps1"
}
Write-Host ""

Write-Host "[7] Port listener (netstat)"
$net = netstat -ano 2>$null | Select-String ":$Port\s"
if ($net) {
    $net | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "  No process listening on $Port"
}
Write-Host ""
Write-Host "Copy this entire output if you need help debugging step 3."
