# Force-close all Google Chrome processes (Windows)
$ProjectRoot = Split-Path $PSScriptRoot -Parent

Write-Host "Stopping Chrome processes..."
Get-Process -Name "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$left = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
if ($left) {
    Write-Host "Some Chrome processes may still be running. Check Task Manager."
} else {
    Write-Host "All Chrome processes stopped."
}

# Remove stale profile locks (Chrome killed mid-session)
$profile = Join-Path $ProjectRoot "data\chrome_cdp_profile"
foreach ($name in @("SingletonLock", "SingletonSocket", "SingletonCookie")) {
    $f = Join-Path $profile $name
    if (Test-Path -LiteralPath $f) {
        Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue
        Write-Host "Removed stale lock: $name"
    }
}
