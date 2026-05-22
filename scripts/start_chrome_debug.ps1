# Start Google Chrome with remote debugging (Windows)
# Run in PowerShell:  .\scripts\start_chrome_debug.ps1

$Port = if ($env:CHROME_DEBUG_PORT) { $env:CHROME_DEBUG_PORT } else { "9222" }

Write-Host "Chrome CDP URL: http://127.0.0.1:$Port"
Write-Host ""
Write-Host "IMPORTANT:"
Write-Host "  1. Close ALL Chrome windows first (check system tray too)."
Write-Host "  2. This opens Chrome with remote debugging on port $Port."
Write-Host "  3. Sign in to https://www.therealreal.com/ (Google or email)."
Write-Host "  4. Open a category page with products (e.g. New Arrivals)."
Write-Host "  5. In a NEW terminal:  `$env:PYTHONPATH='.'; python chrome_crawler.py"
Write-Host ""

$ChromePaths = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$Chrome = $ChromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Chrome) {
    Write-Error "Google Chrome not found. Install Chrome or set path manually."
    exit 1
}

$UserData = "$env:LOCALAPPDATA\Google\Chrome\User Data"

Write-Host "Using: $Chrome"
Write-Host "Profile: $UserData"
Write-Host ""

Start-Process -FilePath $Chrome -ArgumentList @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=`"$UserData`"",
    "https://www.therealreal.com/"
)
