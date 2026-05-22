# Check if Chrome remote debugging is reachable (Windows)
$Port = if ($env:CHROME_DEBUG_PORT) { $env:CHROME_DEBUG_PORT } else { "9222" }
$url = "http://127.0.0.1:$Port/json/version"
Write-Host "Testing $url"
try {
    $r = Invoke-RestMethod -Uri $url -TimeoutSec 3
    Write-Host "SUCCESS — Chrome debugging is running."
    Write-Host ($r | ConvertTo-Json -Compress)
    exit 0
} catch {
    Write-Host "FAILED — cannot connect to port $Port."
    Write-Host ""
    Write-Host "Fix:"
    Write-Host "  1. .\scripts\kill_chrome.ps1"
    Write-Host "  2. .\start_chrome_debug.ps1"
    Write-Host "  3. Run this script again"
    exit 1
}
