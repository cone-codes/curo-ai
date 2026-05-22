# Chrome crawler — Windows guide

Use **your real Google Chrome** to scrape The RealReal (signed in with Google), then search in the app.

---

## 1. One-time setup

Open **PowerShell** in your project folder (e.g. `C:\Users\You\curo-ai`):

```powershell
git pull origin cursor/therealreal-search-app-351e

python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Optional config:

```powershell
copy .env.example .env
```

---

## 2. Find your Chrome path (if scripts say “Chrome not found”)

1. Open **Google Chrome** from the Start menu.
2. Address bar: `chrome://version`
3. Copy **Executable path**, for example:
   `C:\Program Files\Google\Chrome\Application\chrome.exe`

Set it for this session:

```powershell
$env:CHROME_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

(Use your actual path.)

---

## 3. Close Chrome completely

- Close all Chrome windows.
- System tray → right-click Chrome → **Exit**.
- Task Manager → end any `chrome.exe` if still running.

---

## 4. Start Chrome with debugging

From the **project root** (folder with `chrome_crawler.py`):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\start_chrome_debug.bat
```

Alternative:

```powershell
.\start_chrome_debug.ps1
```

**Important:** Use `.\` at the beginning.  
`scripts\start_chrome_debug.bat` alone in PowerShell will error.

---

## 5. Sign in on The RealReal

In the Chrome window that opens:

1. Go to https://www.therealreal.com/
2. Sign in (Google or email).
3. Open a page with products (e.g. **New Arrivals**).

Leave Chrome open.

---

## 6. Verify debugging (optional)

New PowerShell window:

```powershell
curl http://127.0.0.1:9222/json/version
```

You should see JSON. If not, repeat steps 3–4.

---

## 7. Run the crawler

New PowerShell window (project folder, venv active):

```powershell
cd C:\path\to\curo-ai
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
python chrome_crawler.py
```

Wait until it finishes (`listings` count at the end).

---

## 8. Search

```powershell
$env:PYTHONPATH = "."
python run.py
```

Browser: **http://localhost:8000**

Or click **Scrape via my Chrome** in the UI (after steps 3–5).

---

## Troubleshooting

| Issue | Fix |
|--------|-----|
| `The module 'scripts' could not be loaded` | Run `.\start_chrome_debug.bat` from project root (with `.\`) |
| `Google Chrome not found` | Set `$env:CHROME_EXECUTABLE` from `chrome://version` |
| `Cannot reach Chrome at 9222` | Quit Chrome fully; run step 4 again |
| `no_product_urls_found` | Signed in + category page with product cards open |
| Only Microsoft Edge | Install Google Chrome (this tool targets Chrome) |

---

## Settings (`.env`)

```env
CHROME_CDP_URL=http://127.0.0.1:9222
CHROME_CRAWL_MAX_LISTINGS=40
CHROME_CRAWL_DELAY_MIN_MS=4000
CHROME_CRAWL_DELAY_MAX_MS=9000
SCRAPE_LIST_URL=https://www.therealreal.com/sales/shop-new-arrivals-5753
```

---

## Quick reference

```powershell
# Terminal 1 — Chrome (once per session)
$env:CHROME_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"  # if needed
.\start_chrome_debug.bat

# Terminal 2 — Crawl + app
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
python chrome_crawler.py
python run.py
```
