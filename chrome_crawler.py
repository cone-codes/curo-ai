#!/usr/bin/env python3
"""
Standalone Chrome CDP crawler for The RealReal.

Uses YOUR Google Chrome (already logged in) via remote debugging.
Does not launch a separate Playwright browser.

Steps:
  1. ./scripts/start_chrome_debug.sh   (or start Chrome with --remote-debugging-port=9222)
  2. Sign in to therealreal.com in that Chrome window
  3. PYTHONPATH=. python chrome_crawler.py
"""

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> int:
    from backend.app.chrome_bridge import run_chrome_crawl
    from backend.app.indexing.manager import IndexManager
    from backend.app.storage import count_listings, existing_ids, upsert_many

    known = existing_ids()
    logger.info("Starting Chrome crawl (existing listings in DB: %d)", len(known))

    result = await run_chrome_crawl()
    print("\n--- Chrome crawl result ---")
    print(result.to_dict())

    if not result.listings:
        print("\nNo listings parsed.")
        print(f"  Pages visited: {result.pages_visited}")
        print(f"  Product URLs found: {result.product_urls_found}")
        if result.errors:
            print("  Errors (first few):")
            for err in result.errors[:5]:
                print(f"    - {err}")
        print(
            "\nCommon causes:"
            "\n  - login_required / captcha: sign in on TRR in the Chrome window from start_chrome_debug.ps1"
            "\n  - page_not_ready: page loaded before product data; pull latest code (longer wait added)"
            "\n  - parse_failed: open data/html_snapshots/failed_*.html in a browser"
            "\n  - no_product_urls_found: browse a category with items while signed in, then re-run"
        )
        return 1

    new = [l for l in result.listings if l.id not in known]
    upsert_many(result.listings)
    logger.info("Saved %d listings (%d new)", len(result.listings), len(new))

    logger.info("Building search indexes...")
    IndexManager().build()
    logger.info("Done. Total listings: %d", count_listings())
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
