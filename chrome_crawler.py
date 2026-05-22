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
        print(
            "\nNo listings parsed. Ensure Chrome is running with remote debugging, "
            "you are signed in to The RealReal, and a category page loads product links."
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
