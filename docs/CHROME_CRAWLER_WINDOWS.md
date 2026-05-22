# Chrome crawler — Windows guide

## Step 3 fails? Use this

PowerShell (project root):

```powershell
git pull origin cursor/therealreal-search-app-351e

# 1. Kill Chrome
.\scripts\kill_chrome.ps1

# 2. Start Chrome (root launcher sets ExecutionPolicy for this session)
.\start_chrome_debug.ps1
```

You must see **`SUCCESS — Chrome debugging is active`**. If not, do not continue.

Diagnostics (paste this output if you need help):

```powershell
.\scripts\diagnose_chrome_debug.ps1
```

Check port:

```powershell
.\scripts\check_chrome_debug.ps1
```

**Do not use** `curl` in PowerShell for step 4 — use `Invoke-RestMethod` or the check script above.

---

## Full flow

### Setup (once)

```powershell
cd C:\path\to\curo-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If Chrome not found:

```powershell
$env:CHROME_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

(Path from `chrome://version` in Chrome — field **Executable path**.)

### Every session

```powershell
.\scripts\kill_chrome.ps1
.\start_chrome_debug.ps1
```

Sign in on https://www.therealreal.com/ in **that** Chrome window (profile: `data\chrome_cdp_profile`).

```powershell
.\scripts\check_chrome_debug.ps1
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
python chrome_crawler.py
python run.py
```

Open http://localhost:8000

---

## Common step 3 errors

| Error | Fix |
|--------|-----|
| `Google Chrome not found` | `$env:CHROME_EXECUTABLE = "..."` from chrome://version |
| `FAILED — port 9222` | `kill_chrome.ps1`, wait 5s, `start_chrome_debug.ps1` again; run `diagnose_chrome_debug.ps1` |
| `Chrome exited immediately` | Antivirus blocked launch; verify `CHROME_EXECUTABLE` path |
| `Chrome process(es) still running` | Task Manager → end all Google Chrome, then retry |
| `ExecutionPolicy` | Use `.\start_chrome_debug.ps1` from project root (auto Bypass) or `Set-ExecutionPolicy -Scope Process Bypass` |
| Chrome opens but port fails | Only use the window opened by the script; profile is `data\chrome_cdp_profile` |
| `cannot be loaded because running scripts is disabled` | Run from root: `.\start_chrome_debug.ps1` |

---

## CMD fallback (if PowerShell fails)

```cmd
cd C:\path\to\curo-ai
start_chrome_debug.bat
```
