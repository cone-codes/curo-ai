"""Passive Chrome crawl: you browse TRR manually, we capture open product tabs."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse

from backend.app.chrome_bridge.connector import ChromeNotRunningError, connect_to_chrome, disconnect
from backend.app.chrome_bridge.crawler import (
    ChromeCrawlResult,
    _human_pause,
    _process_product_page,
    _save_html,
    _should_wait_for_label,
    _wait_for_manual_resolution,
)
from backend.app.chrome_bridge.discover import normalize_product_url
from backend.app.chrome_bridge.parser import detect_page_issue, parse_product_html
from backend.app.config import settings
from backend.app.models import Listing

logger = logging.getLogger(__name__)


def _all_browser_pages(browser):
    for context in browser.contexts:
        for page in context.pages:
            yield page


def _product_url_from_page(page) -> str | None:
    url = (page.url or "").strip()
    if "therealreal.com" not in url:
        return None
    norm = normalize_product_url(url)
    return norm


def _load_urls_from_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        norm = normalize_product_url(line)
        if norm:
            urls.append(norm)
    return urls


async def _capture_page_listing(page, url: str) -> tuple[Listing | None, str | None]:
    """Snapshot current tab (no navigation)."""
    from backend.app.chrome_bridge.crawler import _snapshot_page

    html, next_raw, title = await _snapshot_page(page)
    if not html:
        return None, None

    issue = detect_page_issue(html, title)
    if issue and _should_wait_for_label(issue):
        html, next_raw, title, ok = await _wait_for_manual_resolution(
            page, url, issue, require_product=True
        )
        if not ok:
            return None, None

    listing = parse_product_html(html, url, next_data_raw=next_raw, page_title=title)
    if listing:
        return listing, html

    reason = issue or "parse_failed"
    if _should_wait_for_label(reason if issue else "page_not_ready"):
        html, next_raw, title, ok = await _wait_for_manual_resolution(
            page, url, issue or "page_not_ready", require_product=True
        )
        if ok:
            listing = parse_product_html(
                html, url, next_data_raw=next_raw, page_title=title
            )
            if listing:
                return listing, html
    return None, None


async def run_chrome_passive_crawl() -> ChromeCrawlResult:
    """
    Watch Chrome tabs while YOU click through products on The RealReal.
    Each product page you open is captured automatically.
    """
    result = ChromeCrawlResult()
    playwright = None
    browser = None

    try:
        playwright, browser, _ctx, page = await connect_to_chrome()
    except ChromeNotRunningError as exc:
        result.message = str(exc)
        result.errors.append(str(exc))
        return result

    poll = settings.chrome_crawl_passive_poll_seconds
    max_items = settings.chrome_crawl_max_listings
    seen_urls: set[str] = set()

    print(
        "\n"
        "=" * 60 + "\n"
        "PASSIVE CRAWL — browse The RealReal in Chrome yourself\n"
        "=" * 60 + "\n"
        "1. Use the Chrome window from start_chrome_debug.ps1\n"
        "2. Sign in and click into product pages (one at a time is fine)\n"
        "3. This script captures each product tab automatically\n"
        f"4. Press Ctrl+C when done (max {max_items} items)\n"
        "=" * 60 + "\n",
        flush=True,
    )

    try:
        while len(result.listings) < max_items:
            captured_this_round = 0
            for tab in _all_browser_pages(browser):
                product_url = _product_url_from_page(tab)
                if not product_url or product_url in seen_urls:
                    continue

                print(f"\n[Capture] {product_url}", flush=True)
                try:
                    await tab.bring_to_front()
                except Exception:
                    pass
                await asyncio.sleep(1.5)
                await _human_pause(tab)

                listing, html = await _capture_page_listing(tab, product_url)
                result.pages_visited += 1
                seen_urls.add(product_url)

                if listing and html:
                    _save_html(listing.id, html)
                    result.listings.append(listing)
                    result.html_saved += 1
                    captured_this_round += 1
                    print(f"  Saved: {listing.title[:60]}", flush=True)
                else:
                    result.errors.append(f"passive_parse_failed:{product_url}")
                    print("  Could not parse — complete captcha/login on this tab, wait.", flush=True)

            if captured_this_round == 0:
                print(
                    f"  Waiting... open a product page in Chrome (polling every {poll}s)",
                    flush=True,
                )
            await asyncio.sleep(poll)

    except KeyboardInterrupt:
        print("\n[Stopped by user]", flush=True)
    except Exception as exc:
        logger.exception("Passive crawl error")
        result.message = f"passive_crawl_error:{exc}"
        result.errors.append(str(exc))
    finally:
        await disconnect(playwright, browser)

    result.product_urls_found = len(seen_urls)
    result.message = "ok" if result.listings else "no_listings_parsed"
    return result


async def run_chrome_crawl_from_file(path: Path) -> ChromeCrawlResult:
    """Visit each URL in a text file (one per line); still uses your Chrome session."""
    from backend.app.chrome_bridge.crawler import run_chrome_crawl_for_urls

    urls = _load_urls_from_file(path)
    if not urls:
        r = ChromeCrawlResult()
        r.message = f"no_urls_in_file:{path}"
        r.errors.append(r.message)
        return r
    print(f"\nCrawling {len(urls)} URLs from {path}\n", flush=True)
    return await run_chrome_crawl_for_urls(urls)
