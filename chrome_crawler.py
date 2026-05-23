#!/usr/bin/env python3
"""
Chrome CDP crawler for The RealReal.

Recommended (most reliable):
  1. start_chrome_debug.ps1
  2. Sign in to TRR in that Chrome
  3. PYTHONPATH=. python chrome_crawler.py --passive
  4. Click through product pages in Chrome; Ctrl+C when done
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def _run_crawl():
    from backend.app.config import settings

    if "--diagnose" in sys.argv:
        from scripts.chrome_crawl_diagnose import main as diagnose_main
        return await diagnose_main()

    if "--passive" in sys.argv or settings.chrome_crawl_mode.lower() == "passive":
        from backend.app.chrome_bridge.passive import run_chrome_passive_crawl
        return await run_chrome_passive_crawl()

    if "--from-file" in sys.argv:
        idx = sys.argv.index("--from-file")
        path = Path(sys.argv[idx + 1] if idx + 1 < len(sys.argv) else settings.chrome_crawl_urls_file)
        from backend.app.chrome_bridge.passive import run_chrome_crawl_from_file
        return await run_chrome_crawl_from_file(path)

    from backend.app.chrome_bridge import run_chrome_crawl
    return await run_chrome_crawl()


async def main() -> int:
    from backend.app.indexing.manager import IndexManager
    from backend.app.storage import count_listings, existing_ids, upsert_many

    known = existing_ids()
    logger.info("Existing listings in DB: %d", len(known))

    result = await _run_crawl()
    print("\n--- Chrome crawl result ---")
    print(result.to_dict())

    if not result.listings:
        print("\nNo listings saved.")
        print(f"  Pages visited: {result.pages_visited}")
        print(f"  URLs seen: {result.product_urls_found}")
        if result.errors:
            print("  Errors:")
            for err in result.errors[:8]:
                print(f"    - {err}")
        print(
            "\nTry PASSIVE mode (recommended):\n"
            "  PYTHONPATH=. python chrome_crawler.py --passive\n"
            "  Then click product pages in debug Chrome. Ctrl+C when done.\n"
            "\nOr diagnose:\n"
            "  PYTHONPATH=. python chrome_crawler.py --diagnose"
        )
        return 1

    new = [l for l in result.listings if l.id not in known]
    upsert_many(result.listings)
    logger.info("Saved %d listings (%d new)", len(result.listings), len(new))
    IndexManager().build()
    logger.info("Done. Total listings: %d", count_listings())
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(130)
