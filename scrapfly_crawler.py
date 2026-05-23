#!/usr/bin/env python3
"""Crawl The RealReal via ScrapFly API (no local Chrome required)."""

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


async def main() -> int:
    from backend.app.scrapfly_bridge import run_scrapfly_crawl
    from backend.app.indexing.manager import IndexManager
    from backend.app.storage import count_listings, existing_ids, upsert_many

    result = await run_scrapfly_crawl()
    print("\n--- ScrapFly crawl result ---")
    print(result.to_dict())

    if not result.listings:
        print("\nNo listings. Set SCRAPFLY_API_KEY in .env and check errors above.")
        return 1

    known = existing_ids()
    upsert_many(result.listings)
    new = sum(1 for l in result.listings if l.id not in known)
    IndexManager().build()
    print(f"Saved {len(result.listings)} listings ({new} new). Total: {count_listings()}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
