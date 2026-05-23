#!/usr/bin/env python3
"""Check ScrapFly + cookie file setup before a full crawl."""

from __future__ import annotations

import asyncio
import sys


def main() -> int:
    from backend.app.config import settings
    from backend.app.scrapfly_bridge.login import cookie_file_path, cookie_file_status, has_saved_cookies
    from backend.app.scraper.cookies import cookies_for_trr, load_cookie_file

    print("--- ScrapFly diagnose ---")
    key = settings.scrapfly_api_key.strip()
    print(f"SCRAPFLY_API_KEY: {'set (' + key[:12] + '...)' if key else 'MISSING'}")
    print(f"SCRAPFLY_USE_COOKIES_FILE: {settings.scrapfly_use_cookies_file}")
    print(f"SCRAPFLY_LOGIN_FIRST: {settings.scrapfly_login_first}")

    path = cookie_file_path()
    print(f"Cookie path: {path}")
    print(f"Cookie status: {cookie_file_status()}")
    cookies = load_cookie_file(path)
    trr = cookies_for_trr(cookies)
    print(f"Cookies loaded: {len(cookies)} ({len(trr)} for therealreal.com)")
    print(f"has_saved_cookies(): {has_saved_cookies()}")

    if not key:
        print("\nFix: add SCRAPFLY_API_KEY to .env")
        return 1
    if settings.scrapfly_use_cookies_file and not has_saved_cookies():
        print("\nFix: export cookies to the path above (see docs/SCRAPFLY.md)")
        return 1

    async def probe() -> None:
        from backend.app.scrapfly_bridge.client import fetch_page
        from backend.app.chrome_bridge.parser import extract_product_urls_from_html, parse_failure_reason

        url = settings.scrape_list_url
        print(f"\nProbing category page: {url}")
        fetched = await fetch_page(url, auto_scroll=True)
        print(f"  success={fetched.success} status={fetched.status_code} cost={fetched.api_cost}")
        if not fetched.html:
            print(f"  error={fetched.error}")
            return
        links = extract_product_urls_from_html(fetched.html)
        print(f"  product links found: {len(links)}")
        if links:
            sample = links[0]
            print(f"\nProbing product: {sample}")
            p = await fetch_page(sample, auto_scroll=False)
            print(f"  success={p.success} status={p.status_code} cost={p.api_cost}")
            if p.html:
                reason = parse_failure_reason(p.html, sample)
                print(f"  parse check: {reason or 'ok (would parse)'}")

    asyncio.run(probe())
    return 0


if __name__ == "__main__":
    sys.exit(main())
