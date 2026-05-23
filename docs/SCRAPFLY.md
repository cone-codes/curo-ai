# ScrapFly setup

ScrapFly fetches The RealReal in the cloud. **You export cookies once** after signing in in Chrome — no automatic browser from this app.

---

## Step 1 — Install

```powershell
cd C:\Users\CØNY\curo-ai
git pull origin cursor/therealreal-search-app-351e
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Step 2 — ScrapFly API key

1. https://scrapfly.io/register  
2. Copy key → `.env`:

```env
SCRAPFLY_API_KEY=scp-live-your-key-here
SCRAPFLY_USE_COOKIES_FILE=true
SCRAPFLY_LOGIN_FIRST=false
```

---

## Step 3 — Export cookies (required)

### A. Sign in

Open **normal Chrome**, go to https://www.therealreal.com/, sign in (Google or email).

### B. Export with Cookie-Editor

1. Install **Cookie-Editor** (Chrome Web Store).
2. On therealreal.com, open the extension → **Export** (JSON).
3. Save as:

   `C:\Users\CØNY\curo-ai\data\trr_cookies.json`

   (Must be that exact path/name.)

### C. Check file

File should be JSON — a list of objects with `"name"` and `"value"`, or `{"cookies": [...]}`.

More detail: `data/trr_cookies.README.md`

---

## Step 4 — Run ScrapFly

```powershell
$env:PYTHONPATH = "."
python scrapfly_crawler.py
```

Or `python run.py` → **Scrape via ScrapFly**

---

## Step 5 — Search

http://localhost:8000

---

## When cookies expire

Sign in again in Chrome → re-export → overwrite `data\trr_cookies.json` → run crawl again.

---

## Optional: browser login (off by default)

If you prefer the app to open a browser for sign-in (old behavior), set in `.env`:

```env
SCRAPFLY_LOGIN_FIRST=true
SCRAPE_HEADLESS=false
```

Default is **manual cookie export only** (`SCRAPFLY_LOGIN_FIRST=false`).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `cookies_required_export` | Create `data\trr_cookies.json` (Step 3) |
| Circular import | `git pull` latest |
| `Set SCRAPFLY_API_KEY` | Add key to `.env` |
| 0 listings | Re-export cookies; lower `SCRAPFLY_MAX_LISTINGS=5` for a test |
