"""Crawl The RealReal via ScrapFly API + existing HTML parser."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from backend.app.chrome_bridge.parser import (
    extract_product_urls_from_html,
    parse_failure_reason,
    parse_product_html,
)
from backend.app.config import settings
from backend.app.models import Listing
from backend.app.scrapfly_bridge.client import (
    ScrapflyNotConfiguredError,
    fetch_page,
)
logger = logging.getLogger(__name__)


@dataclass
class ScrapflyCrawlResult:
    listings: list[Listing] = field(default_factory=list)
    product_urls_found: int = 0
    pages_visited: int = 0
    api_cost_total: int = 0
    errors: list[str] = field(default_factory=list)
    message: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "listings": len(self.listings),
            "product_urls_found": self.product_urls_found,
            "pages_visited": self.pages_visited,
            "api_cost_total": self.api_cost_total,
            "errors": self.errors[:10],
            "message": self.message,
        }


async def _discover_product_urls() -> list[str]:
    urls: list[str] = []
    for list_url in settings.listing_urls()[: max(1, settings.scrape_max_pages)]:
        logger.info("ScrapFly category fetch: %s", list_url)
        fetched = await fetch_page(list_url, auto_scroll=settings.scrapfly_auto_scroll)
        if fetched.success and fetched.html:
            found = extract_product_urls_from_html(fetched.html)
            logger.info("  -> %d product links", len(found))
            urls.extend(found)
        else:
            logger.warning("  -> failed: %s", fetched.error)
        await asyncio.sleep(settings.scrapfly_delay_seconds)
    seen: set[str] = set()
    unique: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique[: settings.scrapfly_max_listings]


async def run_scrapfly_crawl(
    product_urls: list[str] | None = None,
) -> ScrapflyCrawlResult:
    result = ScrapflyCrawlResult()

    try:
        if not settings.scrapfly_api_key.strip():
            raise ScrapflyNotConfiguredError(
                "Set SCRAPFLY_API_KEY in .env — get a key at https://scrapfly.io/dashboard"
            )

        if settings.scrapfly_use_cookies_file:
            from backend.app.scrapfly_bridge.login import has_saved_cookies, cookie_file_path

            if not has_saved_cookies():
                path = cookie_file_path()
                result.message = "cookies_required_export_to_data/trr_cookies.json"
                print(
                    "\nScrapFly needs TRR login cookies.\n"
                    f"  1. Sign in at https://www.therealreal.com/ in Chrome\n"
                    f"  2. Export cookies (Cookie-Editor extension) to:\n"
                    f"     {path}\n"
                    "  3. Run this again\n"
                    "  See docs/SCRAPFLY.md or data/trr_cookies.README.md\n",
                    flush=True,
                )
                result.errors.append(result.message)
                return result

        if product_urls is None:
            product_urls = await _discover_product_urls()
        result.product_urls_found = len(product_urls)

        if not product_urls:
            result.message = "no_product_urls_found"
            return result

        print(
            f"\nScrapFly: fetching {len(product_urls)} product pages "
            f"(est. {len(product_urls) * 30}+ API credits)\n",
            flush=True,
        )

        for i, url in enumerate(product_urls):
            logger.info("ScrapFly (%d/%d) %s", i + 1, len(product_urls), url)
            fetched = await fetch_page(url, auto_scroll=False)
            result.pages_visited += 1
            result.api_cost_total += fetched.api_cost

            if not fetched.success or not fetched.html:
                result.errors.append(f"fetch_failed:{fetched.error}:{url}")
                await asyncio.sleep(settings.scrapfly_delay_seconds)
                continue

            listing = parse_product_html(fetched.html, url)
            if not listing:
                reason = parse_failure_reason(fetched.html, url)
                result.errors.append(f"parse_failed:{reason}:{url}")
                await asyncio.sleep(settings.scrapfly_delay_seconds)
                continue

            result.listings.append(listing)
            print(f"  Saved: {listing.title[:70]}", flush=True)
            await asyncio.sleep(settings.scrapfly_delay_seconds)

        result.message = "ok" if result.listings else "no_listings_parsed"
        print(f"\nScrapFly API credits used (this run): ~{result.api_cost_total}\n", flush=True)

    except ScrapflyNotConfiguredError as exc:
        result.message = str(exc)
        result.errors.append(str(exc))
    except Exception as exc:
        logger.exception("ScrapFly crawl failed")
        result.message = f"scrapfly_error:{exc}"
        result.errors.append(str(exc))

    return result
