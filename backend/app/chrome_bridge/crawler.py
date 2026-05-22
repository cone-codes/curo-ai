"""Slowly crawl TRR in the user's real Chrome — human-paced navigation + HTML capture."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.config import DATA_DIR, settings
from backend.app.chrome_bridge.connector import ChromeNotRunningError, connect_to_chrome, disconnect
from backend.app.chrome_bridge.parser import extract_product_urls_from_html, parse_product_html
from backend.app.models import Listing

logger = logging.getLogger(__name__)

HTML_CACHE_DIR = DATA_DIR / "html_snapshots"


@dataclass
class ChromeCrawlResult:
    listings: list[Listing] = field(default_factory=list)
    product_urls_found: int = 0
    pages_visited: int = 0
    html_saved: int = 0
    errors: list[str] = field(default_factory=list)
    message: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "listings": len(self.listings),
            "product_urls_found": self.product_urls_found,
            "pages_visited": self.pages_visited,
            "html_saved": self.html_saved,
            "errors": self.errors[:10],
            "message": self.message,
        }


def _delay_ms() -> float:
    return random.uniform(
        settings.chrome_crawl_delay_min_ms,
        settings.chrome_crawl_delay_max_ms,
    ) / 1000.0


async def _human_pause(page) -> None:
    await asyncio.sleep(_delay_ms())
    for _ in range(settings.chrome_crawl_scroll_steps):
        delta = random.randint(200, 600)
        try:
            await page.mouse.wheel(0, delta)
        except Exception:
            try:
                await page.evaluate(f"window.scrollBy(0, {delta})")
            except Exception:
                pass
        await asyncio.sleep(random.uniform(0.3, 0.9))


async def _navigate_slow(page, url: str) -> str | None:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=settings.scrape_timeout_ms)
        await _human_pause(page)
        return await page.content()
    except Exception as exc:
        logger.warning("Navigation failed %s: %s", url, exc)
        return None


def _save_html(listing_id: str, html: str) -> Path:
    HTML_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = HTML_CACHE_DIR / f"{listing_id}.html"
    path.write_text(html, encoding="utf-8")
    return path


async def _collect_listing_urls(page) -> list[str]:
    urls: list[str] = []
    seed_pages = settings.listing_urls()
    for list_url in seed_pages[: max(1, settings.scrape_max_pages)]:
        html = await _navigate_slow(page, list_url)
        if not html:
            continue
        found = extract_product_urls_from_html(html)
        urls.extend(found)
        await asyncio.sleep(_delay_ms())
    # dedupe preserve order
    seen: set[str] = set()
    unique: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique[: settings.chrome_crawl_max_listings]


async def run_chrome_crawl() -> ChromeCrawlResult:
    """
    Attach to the user's Chrome, discover product URLs, visit each slowly,
    save HTML snapshots, and parse listings.
    """
    result = ChromeCrawlResult()
    playwright = None
    browser = None

    try:
        playwright, browser, _context, page = await connect_to_chrome()
    except ChromeNotRunningError as exc:
        result.message = str(exc)
        result.errors.append(str(exc))
        return result

    try:
        product_urls = await _collect_listing_urls(page)
        result.product_urls_found = len(product_urls)
        logger.info("Found %d product URLs in Chrome", len(product_urls))

        if not product_urls:
            result.message = "no_product_urls_found_sign_in_and_open_category_in_chrome"
            return result

        for i, url in enumerate(product_urls):
            logger.info("Visiting (%d/%d) %s", i + 1, len(product_urls), url)
            html = await _navigate_slow(page, url)
            result.pages_visited += 1
            if not html:
                result.errors.append(f"no_html:{url}")
                continue

            listing = parse_product_html(html, url)
            if not listing:
                result.errors.append(f"parse_failed:{url}")
                continue

            _save_html(listing.id, html)
            result.html_saved += 1
            result.listings.append(listing)

            if i < len(product_urls) - 1:
                await asyncio.sleep(_delay_ms())

        result.message = "ok" if result.listings else "no_listings_parsed"
    except Exception as exc:
        logger.exception("Chrome crawl failed")
        result.message = f"chrome_crawl_error:{exc}"
        result.errors.append(str(exc))
    finally:
        if playwright and browser:
            await disconnect(playwright, browser)

    return result
