# Launcher from project root — sets execution policy for this session only
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force | Out-Null
Set-Location $PSScriptRoot
& "$PSScriptRoot\scripts\start_chrome_debug.ps1"
exit $LASTEXITCODE
