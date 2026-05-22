# Chrome crawler — Windows (full instructions)

Use **Google Chrome** (not Edge). All commands run in **PowerShell** from the project root (`curo-ai`).

---

## Step 0 — Get the latest code (do this first)

```powershell
cd C:\Users\CØNY\curo-ai
git fetch origin cursor/therealreal-search-app-351e
git checkout cursor/therealreal-search-app-351e
git pull origin cursor/therealreal-search-app-351e
```

If step 3 ever shows a **parser error** (`ForEach-Object`, `Missing Catch`), your script is stale. Force-replace it:

```powershell
git checkout origin/cursor/therealreal-search-app-351e -- scripts/start_chrome_debug.ps1
```

Or download:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/cone-codes/curo-ai/cursor/therealreal-search-app-351e/scripts/start_chrome_debug.ps1" -OutFile ".\scripts\start_chrome_debug.ps1"
```

Verify (must print **nothing**):

```powershell
Select-String -Path .\scripts\start_chrome_debug.ps1 -Pattern "ForEach-Object"
```

---

## Step 1 — One-time setup

```powershell
cd C:\Users\CØNY\curo-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

If Chrome is not auto-detected, set the path from `chrome://version` → **Executable path**:

```powershell
$env:CHROME_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

(Add the same line to `.env` as `CHROME_EXECUTABLE=...` if you want it permanent.)

---

## Step 2 — Kill all Chrome (every session)

```powershell
.\scripts\kill_chrome.ps1
```

Wait until it says all Chrome processes stopped. If any remain, end them in **Task Manager**.

---

## Step 3 — Start Chrome with remote debugging

Run from **project root** (not from inside `scripts`):

```powershell
.\start_chrome_debug.ps1
```

You **must** see:

```text
SUCCESS - Chrome debugging is active on port 9222
```

If you see `FAILED` or a red parser error, run:

```powershell
.\scripts\diagnose_chrome_debug.ps1
```

Do **not** continue until step 3 succeeds.

---

## Step 4 — Confirm the debug port

```powershell
.\scripts\check_chrome_debug.ps1
```

Or:

```powershell
Invoke-RestMethod http://127.0.0.1:9222/json/version
```

**Do not** use `curl` in PowerShell (it is an alias for `Invoke-WebRequest` and behaves differently).

---

## Step 5 — Sign in to The Real Real

In the **Chrome window that just opened** (profile folder: `data\chrome_cdp_profile`):

1. Open https://www.therealreal.com/
2. Sign in (Google or email)
3. Browse to a category with products (e.g. New Arrivals)

Use only this Chrome window for scraping — not your normal daily Chrome profile.

---

## Step 6 — Crawl listings

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
python chrome_crawler.py
```

Wait until it reports listings saved and indexes rebuilt.

---

## Step 7 — Start the search app

```powershell
$env:PYTHONPATH = "."
python run.py
```

Open http://localhost:8000 and search. You can also click **Scrape via my Chrome** in the UI (Chrome must still be running with step 3 active).

---

## Quick reference (every session)

```powershell
cd C:\Users\CØNY\curo-ai
.\scripts\kill_chrome.ps1
.\start_chrome_debug.ps1          # wait for SUCCESS
.\scripts\check_chrome_debug.ps1
# sign in to TRR in that Chrome window
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
python chrome_crawler.py
python run.py
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Parser error, `ForEach-Object`, `Missing Catch` | Step 0 — replace `start_chrome_debug.ps1` |
| `Google Chrome not found` | Set `$env:CHROME_EXECUTABLE` from `chrome://version` |
| `FAILED - port 9222` | `kill_chrome.ps1`, wait 5s, run `start_chrome_debug.ps1` again |
| Scripts disabled | Use `.\start_chrome_debug.ps1` from project root |
| Port check fails but Chrome is open | You may have opened normal Chrome; use only the script’s window / `data\chrome_cdp_profile` |

---

## CMD fallback

```cmd
cd C:\Users\CØNY\curo-ai
start_chrome_debug.bat
```
