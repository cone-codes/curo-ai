## Quick start

**Recommended:** use your real Chrome — see [docs/CHROME_CRAWLER.md](docs/CHROME_CRAWLER.md).

# TheRealReal Search

Hybrid search over luxury resale listings from [The RealReal](https://www.therealreal.com): **BM25 lexical** retrieval plus **multimodal semantic** search (text embeddings + CLIP image embeddings), fused with **Reciprocal Rank Fusion (RRF)**.

## Features

- Playwright scraper with **session warmup**, **stealth init scripts**, **human-like delays/scroll**, and **persistent browser profile**
- Seed-data fallback when bot protection blocks automated access
- Indexes title, description, designer, category, condition, size, images, and metadata
- Search API combining lexical + semantic text + semantic image channels
- Web UI with search bar and **Re-scrape listings** button


```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m playwright install chromium
cp .env.example .env   # recommended for local scraping

PYTHONPATH=. python run.py
```

Open http://localhost:8000

On first launch, seed listings load automatically so search works immediately. Click **Re-scrape listings** to attempt a live scrape.


## Login required

The RealReal often **requires you to be signed in** before listing pages load. The scraper supports **manual login** in a headed browser; your session is saved in `data/browser_profile/`.

### Sign in on first Re-scrape (no setup before starting the app)

1. Start the app: `PYTHONPATH=. python run.py`
2. Open http://localhost:8000
3. Click **Re-scrape listings** — a browser opens and asks you to sign in
4. After sign-in, scraping continues and the session is saved to `data/browser_profile/`

Later Re-scrape clicks reuse that session (no login prompt unless the session expired).

Optional: run `PYTHONPATH=. python scripts/login_trr.py` if you prefer to sign in before opening the UI.

To skip login (seed data only): `SCRAPE_REQUIRE_LOGIN=false`

## Local scraping (recommended settings)

Copy `.env.example` to `.env`. Defaults are tuned for **local** use:

| Setting | Default | Why |
|---------|---------|-----|
| `SCRAPE_HEADLESS=false` | Headed browser | Solve captchas; fewer automation signals |
| `SCRAPE_PERSISTENT_PROFILE=true` | `data/browser_profile/` | Reuse cookies between runs |
| `SCRAPE_WARMUP_ENABLED=true` | Visit homepage first | Looks like a real shopper session |
| `SCRAPE_DELAY_MIN_MS` / `MAX` | 2–6s between pages | Avoid hammering; human pacing |
| `SCRAPE_USE_STEALTH=true` | Init scripts | Reduces basic `navigator.webdriver` flags |

If PerimeterX still blocks you, a **headed** browser window opens—complete the “Press & Hold” challenge once; the profile should remember the session.

## Configuration

See `.env.example` for all scrape-related variables. Highlights:

| Variable | Description |
|----------|-------------|
| `SCRAPE_LIST_URL` | Primary listing page |
| `SCRAPE_LIST_URLS` | Comma-separated extra category/sale URLs |
| `SCRAPE_MAX_PAGES` | Max pages per scrape run (across URLs) |
| `SCRAPE_STOP_ON_BLOCK` | Stop immediately on captcha/403 |
| `SCRAPE_FALLBACK_TO_SEED` | Load seed JSON when live scrape returns nothing |

## API

- `GET /api/search?q=chanel+bag` — hybrid search
- `POST /api/scrape` — scrape + reindex (returns **503** with diagnostics if blocked and no seed fallback)
- `POST /api/reindex` — rebuild indexes from DB
- `GET /api/health` — status + scrape defaults

### Scrape response fields

`status`, `outcome`, `block_type`, `pages_scraped`, `products_found`, `blocked_at_url`, `diagnostics`, `used_seed_fallback`

## Ranking

1. **Lexical**: BM25 over tokenized title, description, and metadata fields
2. **Semantic text**: cosine similarity of query vs listing text embeddings
3. **Semantic image**: CLIP — query text vs listing image embeddings
4. **Fusion**: weighted Reciprocal Rank Fusion across the three ranked lists

## Live scraping notes

The RealReal uses PerimeterX. The scraper:

1. Opens a **persistent Chromium profile** (cookies survive restarts)
2. **Warms up** on the homepage (scroll, optional cookie dismiss)
3. Waits a **random delay**, then visits listing pages
4. Reports **blocked** vs **captcha** vs **partial success** clearly

Slower scraping alone does not bypass a hard block, but pacing + headed mode + session reuse gives the best chance on a residential IP.

## Project layout

```
backend/app/          # FastAPI app, scraper, indexes
backend/static/       # Search UI
data/seed_listings.json
data/browser_profile/ # persistent Playwright profile (gitignored)
run.py
```

## Troubleshooting live scrape

If Re-scrape fails silently, check the status line for `blocked`, `login_required`, or `warmup_blocked`.

1. Set `SCRAPE_HEADLESS=false` and `SCRAPE_FALLBACK_TO_SEED=false`
2. Click **Re-scrape** — sign in with Google or email in the browser window (wait up to 3 min)
3. Optional: export cookies from a logged-in browser session to `data/trr_cookies.json` (Playwright format) or `POST /api/auth/cookies`
4. Use `SCRAPE_BROWSER_CHANNEL=chrome` to reuse your normal Chrome profile path via `SCRAPE_USER_DATA_DIR`

Bot protection often blocks the site **before** login — the app now opens the login page **first**, not the homepage warmup.
