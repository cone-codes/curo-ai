# Find Google Chrome on Windows. Prints full path to stdout, or exits 1.
$ErrorActionPreference = "SilentlyContinue"

if ($env:CHROME_EXECUTABLE -and (Test-Path -LiteralPath $env:CHROME_EXECUTABLE)) {
    Write-Output $env:CHROME_EXECUTABLE
    exit 0
}

$regKeys = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
)
foreach ($key in $regKeys) {
    try {
        $item = Get-Item -LiteralPath $key
        $path = $item.GetValue("")
        if (-not $path) { $path = $item.(Get-ItemProperty -LiteralPath $key | Select-Object -ExpandProperty "(default)" -ErrorAction SilentlyContinue) }
        if ($path) {
            $path = $path.Trim('"').Split('"')[0]
            if ($path -and (Test-Path -LiteralPath $path)) {
                Write-Output $path
                exit 0
            }
        }
    } catch {}
}

$where = & where.exe chrome 2>$null | Select-Object -First 1
if ($where -and (Test-Path -LiteralPath $where)) {
    Write-Output $where.Trim()
    exit 0
}

$candidates = @(
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    ${env:ProgramFiles(x86)} + "\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Chromium\Application\chrome.exe",
    "$env:ProgramFiles\Chromium\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome Beta\Application\chrome.exe",
    "$env:ProgramFiles\Google\Chrome Beta\Application\chrome.exe"
)
foreach ($p in $candidates) {
    if ($p -and (Test-Path -LiteralPath $p)) {
        Write-Output $p
        exit 0
    }
}

# Chrome installed under user Downloads / custom (search Program Files subdirs once)
$searchRoots = @("$env:ProgramFiles", "$env:LOCALAPPDATA")
foreach ($root in $searchRoots) {
    if (-not (Test-Path $root)) { continue }
    $found = Get-ChildItem -Path $root -Filter "chrome.exe" -Recurse -Depth 5 -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "Google\\Chrome\\Application\\chrome\.exe$" } |
        Select-Object -First 1
    if ($found) {
        Write-Output $found.FullName
        exit 0
    }
}

Write-Error "Google Chrome not found."
exit 1
