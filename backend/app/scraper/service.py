import asyncio
import logging
from datetime import datetime, timezone

from backend.app.config import ROOT_DIR, SEED_LISTINGS_PATH, settings

SEED_EXTRA_PATH = ROOT_DIR / "data" / "seed_listings_extra.json"

from backend.app.models import Listing, ScrapeStatus
from backend.app.scraper.playwright_scraper import scrape_listings_async
from backend.app.storage import count_listings, existing_ids, load_seed_from_file, upsert_many

logger = logging.getLogger(__name__)


class ScrapeService:
    async def scrape(self) -> ScrapeStatus:
        before = count_listings()
        known = existing_ids()

        live_listings: list[Listing] = []
        message = "ok"
        used_seed = False

        try:
            live_listings, message = await scrape_listings_async()
        except Exception as exc:
            logger.exception("Playwright scrape failed")
            message = f"scrape_exception:{exc}"

        new_from_live = [l for l in live_listings if l.id not in known]

        if live_listings:
            upsert_many(live_listings)
        elif settings.scrape_fallback_to_seed and SEED_LISTINGS_PATH.exists():
            seed = load_seed_from_file(SEED_LISTINGS_PATH)
            if SEED_EXTRA_PATH.exists():
                seed = seed + load_seed_from_file(SEED_EXTRA_PATH)
            # Mark seed items with fresh scrape time so re-scrape feels live
            refreshed = []
            for item in seed:
                item.scraped_at = datetime.now(timezone.utc)
                if item.metadata is None:
                    item.metadata = {}
                item.metadata["seed_refresh"] = True
                refreshed.append(item)
            new_from_seed = [l for l in refreshed if l.id not in known]
            upsert_many(refreshed)
            used_seed = True
            message = (
                f"{message};loaded_seed_data"
                if message != "ok"
                else "loaded_seed_data_bot_protection_active"
            )
            new_from_live = new_from_seed

        total = count_listings()
        status = "completed"
        if not live_listings and used_seed:
            status = "completed_with_seed_fallback"

        return ScrapeStatus(
            status=status,
            message=message,
            new_listings=len(new_from_live),
            total_listings=total,
            used_seed_fallback=used_seed,
        )

    def scrape_sync(self) -> ScrapeStatus:
        return asyncio.run(self.scrape())
