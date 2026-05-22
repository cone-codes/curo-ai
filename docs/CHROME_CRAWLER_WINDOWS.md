# Chrome crawler — Windows guide

## Step 3 fails? Use this

PowerShell (project root):

```powershell
git pull origin cursor/therealreal-search-app-351e
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 1. Kill Chrome
.\scripts\kill_chrome.ps1

# 2. Start Chrome (auto-kills Chrome, waits for port)
.\start_chrome_debug.ps1
```

You must see **`SUCCESS — Chrome debugging is active`**. If not, do not continue.

Check:

```powershell
.\scripts\check_chrome_debug.ps1
```

**Do not use** `curl` in PowerShell for step 4.

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

(Path from `chrome://version` in Chrome.)

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
| `FAILED — port 9222` | Run `kill_chrome.ps1`, wait 5s, run start again |
| `Read-Host` / prompt errors | Pull latest — script no longer prompts |
| `ExecutionPolicy` | `Set-ExecutionPolicy -Scope Process Bypass` |
| Chrome opens but port fails | Use only the window from the script; profile is `data\chrome_cdp_profile` |

---

## CMD fallback (if PowerShell fails)

```cmd
cd C:\path\to\curo-ai
scripts\start_chrome_debug.bat
```
