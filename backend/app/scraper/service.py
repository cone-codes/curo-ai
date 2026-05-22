import logging
from datetime import datetime, timezone

from backend.app.config import ROOT_DIR, SEED_LISTINGS_PATH, settings

SEED_EXTRA_PATH = ROOT_DIR / "data" / "seed_listings_extra.json"

from backend.app.models import Listing, ScrapeStatus
from backend.app.scraper.playwright_scraper import ScrapeRunResult, scrape_listings_async
from backend.app.session_state import auth_status, is_session_authenticated
from backend.app.storage import count_listings, existing_ids, load_seed_from_file, upsert_many

logger = logging.getLogger(__name__)


def _apply_seed_fallback(known: set[str]) -> tuple[list[Listing], int]:
    seed = load_seed_from_file(SEED_LISTINGS_PATH)
    if SEED_EXTRA_PATH.exists():
        seed = seed + load_seed_from_file(SEED_EXTRA_PATH)
    refreshed: list[Listing] = []
    for item in seed:
        item.scraped_at = datetime.now(timezone.utc)
        item.metadata = {**(item.metadata or {}), "seed_refresh": True}
        refreshed.append(item)
    new_items = [l for l in refreshed if l.id not in known]
    upsert_many(refreshed)
    return refreshed, len(new_items)


def _map_status(
    run: ScrapeRunResult,
    *,
    used_seed: bool,
    new_count: int,
) -> ScrapeStatus:
    blocked = run.outcome in ("blocked", "captcha")
    if run.listings and not used_seed:
        status = "completed" if run.outcome == "success" else "partial_success"
    elif used_seed:
        status = "completed_with_seed_fallback"
    elif run.outcome == "login_required":
        status = "login_required"
    elif blocked:
        status = "captcha_required" if run.outcome == "captcha" else "blocked"
    elif run.outcome == "timeout":
        status = "timeout"
    elif run.outcome == "error":
        status = "error"
    else:
        status = "empty"

    message = run.message
    if used_seed and run.outcome != "success":
        message = f"{message};loaded_seed_data"

    return ScrapeStatus(
        status=status,
        outcome=run.outcome,
        message=message,
        new_listings=new_count,
        total_listings=count_listings(),
        used_seed_fallback=used_seed,
        blocked=blocked and not run.listings,
        block_type=run.block_type,
        pages_scraped=run.pages_scraped,
        products_found=len(run.listings),
        blocked_at_url=run.blocked_at_url,
        diagnostics=run.to_diagnostics(),
        awaiting_login=run.outcome == "login_required",
        session_authenticated=is_session_authenticated(),
    )


class ScrapeService:
    async def scrape(self) -> ScrapeStatus:
        known = existing_ids()
        run: ScrapeRunResult

        try:
            run = await scrape_listings_async()
        except Exception as exc:
            logger.exception("Playwright scrape failed")
            run = ScrapeRunResult(
                outcome="error",
                message=f"scrape_exception:{exc}",
                block_type="navigation_error",
            )

        new_from_live = [l for l in run.listings if l.id not in known]
        used_seed = False

        if run.listings:
            upsert_many(run.listings)
            return _map_status(run, used_seed=False, new_count=len(new_from_live))

        if settings.scrape_fallback_to_seed and SEED_LISTINGS_PATH.exists():
            _, new_from_seed = _apply_seed_fallback(known)
            used_seed = True
            run.message = (
                f"{run.message};loaded_seed_data"
                if run.message not in ("ok", "")
                else "loaded_seed_data_bot_protection_active"
            )
            return _map_status(run, used_seed=used_seed, new_count=new_from_seed)

        return _map_status(run, used_seed=False, new_count=0)

    def scrape_sync(self) -> ScrapeStatus:
        import asyncio

        return asyncio.run(self.scrape())
