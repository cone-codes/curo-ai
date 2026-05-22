# Find Google Chrome on Windows. Prints full path to stdout; exit 1 if not found.
$ErrorActionPreference = "SilentlyContinue"

if ($env:CHROME_EXECUTABLE -and (Test-Path -LiteralPath $env:CHROME_EXECUTABLE)) {
    Write-Output $env:CHROME_EXECUTABLE.Trim()
    exit 0
}

$regKeys = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
)
foreach ($key in $regKeys) {
    try {
        $path = (Get-ItemProperty -LiteralPath $key -ErrorAction Stop).'(default)'
        if ($path) {
            $path = "$path".Trim().Trim('"')
            if (Test-Path -LiteralPath $path) {
                Write-Output $path
                exit 0
            }
        }
    } catch {}
}

$where = & where.exe chrome 2>$null | Select-Object -First 1
if ($where -and (Test-Path -LiteralPath $where.Trim())) {
    Write-Output $where.Trim()
    exit 0
}

$candidates = @(
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    ${env:ProgramFiles(x86)} + "\Google\Chrome\Application\chrome.exe"
)
foreach ($p in $candidates) {
    if ($p -and (Test-Path -LiteralPath $p)) {
        Write-Output $p
        exit 0
    }
}

[Console]::Error.WriteLine("Google Chrome not found. Set CHROME_EXECUTABLE or install Chrome.")
exit 1
