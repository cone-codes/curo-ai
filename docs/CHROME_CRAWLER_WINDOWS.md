# Chrome crawler — Windows (full instructions)

Use **Google Chrome** (not Edge). All commands in **PowerShell** from project root.

---

## Recommended: passive mode (most reliable)

The bot does **not** navigate for you. **You** click products in Chrome; the script captures each product page.

```powershell
git pull origin cursor/therealreal-search-app-351e
.\scripts\kill_chrome.ps1
.\start_chrome_debug.ps1
```

In **that** Chrome window:

1. Sign in at https://www.therealreal.com/
2. Run:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
python chrome_crawler.py --passive
```

3. **Click into product pages** in Chrome (one by one or several tabs).
4. Watch the terminal — you should see `Saved: (product title)` for each.
5. Press **Ctrl+C** when you have enough items.

Then start search:

```powershell
python run.py
```

Open http://localhost:8000

---

## Step 0 — Get latest code

```powershell
cd C:\Users\CØNY\curo-ai
git pull origin cursor/therealreal-search-app-351e
```

If step 3 ever shows a PowerShell **parser error**, replace the script:

```powershell
git checkout origin/cursor/therealreal-search-app-351e -- scripts/start_chrome_debug.ps1
```

---

## Diagnose (if passive still saves nothing)

```powershell
.\start_chrome_debug.ps1
# Sign in, open ONE product page in Chrome
$env:PYTHONPATH = "."
python chrome_crawler.py --diagnose
```

Need: `Product links on page` or open a **product** URL directly, and `Parsed: (a title)`.

---

## Option B: URL file

Copy product URLs from Chrome (address bar), one per line in `data\crawl_urls.txt`, then:

```powershell
python chrome_crawler.py --from-file data/crawl_urls.txt
```

---

## Option C: active mode (auto-navigate)

Slower and often blocked by TRR. Only if passive fails:

```powershell
$env:CHROME_CRAWL_MODE = "active"
python chrome_crawler.py
```

---

## Start Chrome (debug port)

```powershell
.\scripts\kill_chrome.ps1
.\start_chrome_debug.ps1
```

Must show: `SUCCESS - Chrome debugging is active on port 9222`

```powershell
.\scripts\check_chrome_debug.ps1
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Cannot reach port 9222 | `kill_chrome.ps1`, `start_chrome_debug.ps1` again |
| Passive shows "Waiting..." forever | Click a **product** page (URL contains `/products/.../...`) |
| Parsed FAILED on diagnose | Complete captcha / sign-in in debug Chrome |
| No listings after crawl | Use `--passive` and confirm `Saved:` lines in terminal |

---

## .env

```env
CHROME_CDP_URL=http://127.0.0.1:9222
CHROME_CRAWL_MODE=passive
CHROME_CRAWL_PASSIVE_POLL_SECONDS=3
```
