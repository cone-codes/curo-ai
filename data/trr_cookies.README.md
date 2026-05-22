# Importing The RealReal cookies

If the automated browser cannot pass bot checks, sign in to [therealreal.com](https://www.therealreal.com/) in your normal Chrome, export cookies, and save them here as `trr_cookies.json` (Playwright cookie format), or POST them to `/api/auth/cookies`.

Use a browser extension that exports cookies as JSON compatible with Playwright, or copy from DevTools → Application → Cookies.

Then set in `.env`:

```bash
SCRAPE_COOKIES_PATH=data/trr_cookies.json
SCRAPE_FALLBACK_TO_SEED=false
```

Click **Re-scrape** again.
