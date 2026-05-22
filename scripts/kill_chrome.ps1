# Force-close all Google Chrome processes (Windows)
Write-Host "Stopping Chrome processes..."
Get-Process -Name "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$left = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
if ($left) {
    Write-Host "Some Chrome processes may still be running. Check Task Manager."
} else {
    Write-Host "All Chrome processes stopped."
}
