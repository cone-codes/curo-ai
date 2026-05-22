#!/usr/bin/env python3
"""Open a visible browser to The RealReal — run this to verify headed Playwright works."""
import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.app.config import settings
from backend.app.scraper.login import ensure_logged_in
from backend.app.scraper.stealth import STEALTH_INIT_SCRIPT


async def main():
    from playwright.async_api import async_playwright

    headless = settings.scrape_headless
    slow_mo = settings.scrape_slow_mo_ms or (250 if not headless else 0)
    print(f"headless={headless} slow_mo={slow_mo} DISPLAY={os.environ.get('DISPLAY', '(not set)')}")

    async with async_playwright() as p:
        kwargs = {"headless": headless, "slow_mo": slow_mo}
        if settings.scrape_browser_channel.strip():
            kwargs["channel"] = settings.scrape_browser_channel.strip()
        browser = await p.chromium.launch(**kwargs)
        page = await browser.new_page()
        await page.add_init_script(STEALTH_INIT_SCRIPT)
        ok, msg = await ensure_logged_in(page)
        print("Login:", ok, msg)
        print("Navigating to", settings.scrape_list_url)
        await page.goto(settings.scrape_list_url, wait_until="domcontentloaded", timeout=60000)
        wait = settings.scrape_keep_browser_open_seconds or 30
        print(f"Browser open for {wait}s — look for the Chromium/Chrome window now.")
        await asyncio.sleep(wait)
        await browser.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
