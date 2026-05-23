#!/usr/bin/env python3
"""Open The RealReal login in a persistent browser profile. Run once to save your session."""
import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.app.config import settings
from backend.app.scraper.login import detect_logged_in, ensure_logged_in
from backend.app.scraper.stealth import STEALTH_INIT_SCRIPT


async def main():
    from playwright.async_api import async_playwright

    profile = settings.browser_profile_path()
    profile.mkdir(parents=True, exist_ok=True)
    print(f"Profile: {profile}")
    print("A browser window will open — sign in to The RealReal.")
    print(f"Waiting up to {settings.scrape_login_wait_seconds}s...")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            slow_mo=300,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.add_init_script(STEALTH_INIT_SCRIPT)
        ok, msg = await ensure_logged_in(page)
        print("Result:", ok, msg)
        if ok:
            await page.goto(settings.scrape_list_url, wait_until="domcontentloaded", timeout=90000)
            print("Visited listing page to verify session. Leave browser open briefly.")
            await asyncio.sleep(10)
        await context.close()

    print("Done. Session saved in profile — re-scrape from the app should reuse it.")


if __name__ == "__main__":
    asyncio.run(main())
