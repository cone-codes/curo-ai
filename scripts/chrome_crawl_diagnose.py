#!/usr/bin/env python3
"""Check Chrome CDP + TRR page state before running chrome_crawler.py."""

from __future__ import annotations

import asyncio
import sys


async def main() -> int:
    from backend.app.chrome_bridge.connector import ChromeNotRunningError, connect_to_chrome, disconnect
    from backend.app.chrome_bridge.discover import extract_urls_combined, scroll_category_page
    from backend.app.chrome_bridge.parser import detect_page_issue, parse_product_html
    from backend.app.config import settings

    print("=== Chrome crawl diagnose ===\n")
    print(f"CDP URL: {settings.chrome_cdp_url}")

    try:
        playwright, browser, _ctx, page = await connect_to_chrome()
    except ChromeNotRunningError as exc:
        print(f"\nFAIL: {exc}")
        print("\nStart Chrome: .\\start_chrome_debug.ps1  (Windows)")
        return 1

    try:
        url = page.url or ""
        print(f"Active tab: {url}\n")

        title = await page.title()
        html = await page.content()
        issue = detect_page_issue(html, title)
        print(f"Page issue: {issue or 'none'}")
        print(f"Title: {title[:80]}")

        nd_len = await page.evaluate(
            "() => document.getElementById('__NEXT_DATA__')?.textContent?.length || 0"
        )
        print(f"__NEXT_DATA__ length: {nd_len}")

        links: list[str] = []
        if "therealreal.com" in url:
            await scroll_category_page(page)
            links = await extract_urls_combined(page, html)
            print(f"Product links on page: {len(links)}")
            for u in links[:5]:
                print(f"  - {u}")
            if len(links) > 5:
                print(f"  ... and {len(links) - 5} more")
        else:
            print("Tab is not on therealreal.com — open a TRR category in debug Chrome.")

        if links:
            test_url = links[0]
            print(f"\nTest navigate + parse: {test_url}")
            await page.goto(test_url, wait_until="load", timeout=60000)
            await asyncio.sleep(5)
            html2 = await page.content()
            t2 = await page.title()
            nd2 = await page.evaluate(
                "() => document.getElementById('__NEXT_DATA__')?.textContent || null"
            )
            issue2 = detect_page_issue(html2, t2)
            listing = parse_product_html(html2, test_url, next_data_raw=nd2, page_title=t2)
            print(f"  Issue after nav: {issue2 or 'none'}")
            print(f"  Parsed: {listing.title if listing else 'FAILED'}")

        print("\nIf product links = 0: sign in, open New Arrivals, scroll, re-run.")
        print("If Parsed = FAILED: complete captcha in Chrome, then re-run.")
        return 0
    finally:
        await disconnect(playwright, browser)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
