# ScrapFly setup — full instructions

ScrapFly fetches The RealReal in the cloud. **You sign in once in a local browser** — cookies are saved automatically (no export).

---

## Step 1 — Install

```powershell
cd C:\Users\CØNY\curo-ai
git pull origin cursor/therealreal-search-app-351e
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

---

## Step 2 — ScrapFly API key

1. https://scrapfly.io/register
2. Copy key from https://scrapfly.io/dashboard

---

## Step 3 — `.env`

```env
SCRAPFLY_API_KEY=scp-live-your-key-here
SCRAPFLY_LOGIN_FIRST=true
SCRAPFLY_SKIP_LOGIN_IF_COOKIES=true
SCRAPFLY_USE_COOKIES_FILE=true
SCRAPFLY_COUNTRY=us
SCRAPFLY_ASP=true
SCRAPFLY_RENDER_JS=true
SCRAPFLY_PROXY_POOL=public_residential_pool
SCRAPFLY_MAX_LISTINGS=40
SCRAPE_HEADLESS=false
SCRAPE_LOGIN_WAIT_SECONDS=180
```

---

## Step 4 — Sign in (automatic — no cookie export)

When you run ScrapFly, a **browser window opens first**:

1. Sign in to The RealReal (Google or email).
2. Wait until the terminal shows: `[OK] Signed in — saved N cookies to data\trr_cookies.json`
3. ScrapFly crawl starts automatically.

**Next runs:** if cookies are still valid, sign-in is skipped. To sign in again, delete `data\trr_cookies.json` and re-run.

---

## Step 5 — Run

```powershell
$env:PYTHONPATH = "."
python scrapfly_crawler.py
```

Or: `python run.py` → **Scrape via ScrapFly**

---

## Step 6 — Search

http://localhost:8000

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No browser opens | `SCRAPFLY_LOGIN_FIRST=true`, `SCRAPE_HEADLESS=false` |
| Login timeout | Sign in faster; increase `SCRAPE_LOGIN_WAIT_SECONDS=300` |
| Force new login | Delete `data\trr_cookies.json`, run again |
| ScrapFly still fails | Check `SCRAPFLY_API_KEY`; lower `SCRAPFLY_MAX_LISTINGS=5` for a test |
