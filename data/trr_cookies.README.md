# Importing The RealReal cookies (for ScrapFly)

ScrapFly runs in the cloud and cannot show you a sign-in window. **Export cookies from your browser** after you sign in.

## Steps (Windows)

1. Open **Google Chrome** (normal Chrome, not debug mode).
2. Go to https://www.therealreal.com/ and **sign in**.
3. Install the **Cookie-Editor** extension from the Chrome Web Store.
4. While on therealreal.com, click Cookie-Editor → **Export** (JSON).
5. Save the file as:

   ```
   data\trr_cookies.json
   ```

   inside your project folder (e.g. `C:\Users\CØNY\curo-ai\data\trr_cookies.json`).

6. In `.env` set:

   ```env
   SCRAPFLY_USE_COOKIES_FILE=true
   SCRAPFLY_LOGIN_FIRST=false
   ```

7. Run:

   ```powershell
   python scrapfly_crawler.py
   ```

## File format

JSON array (Playwright-style), for example:

```json
[
  {
    "name": "session_id",
    "value": "your-value-here",
    "domain": ".therealreal.com",
    "path": "/"
  }
]
```

Some extensions export `{"cookies": [...]}` — that works too.

## Alternative: API import

If the app is running, you can POST cookies from an extension export:

```http
POST http://localhost:8000/api/auth/cookies
Content-Type: application/json

{"cookies": [ ... paste array here ... ]}
```

## Security

Do not commit `trr_cookies.json` to git. Treat it like a password.

## Re-export when

- ScrapFly says `cookies_required` or `parse_failed` / login pages  
- You signed out of TRR in the browser  
- Session expired (usually after days/weeks)
