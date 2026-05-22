"""Slowly crawl TRR in the user's real Chrome — human-paced navigation + HTML capture."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.app.config import DATA_DIR, settings
from backend.app.chrome_bridge.connector import ChromeNotRunningError, connect_to_chrome, disconnect
from backend.app.chrome_bridge.parser import (
    detect_page_issue,
    extract_product_urls_from_html,
    parse_failure_reason,
    parse_product_html,
)
from backend.app.models import Listing

logger = logging.getLogger(__name__)

HTML_CACHE_DIR = DATA_DIR / "html_snapshots"

_ISSUE_HINTS = {
    "captcha": "Complete the 'Press & Hold' or other challenge in the Chrome window.",
    "login_required": "Sign in to The RealReal in the Chrome window (Google or email).",
    "blocked": "Page was blocked. Try refreshing or signing in again in Chrome.",
    "page_not_ready": "Wait for the product or category page to finish loading.",
    "no_product_urls": "Open a TRR category with products visible (e.g. New Arrivals).",
}


@dataclass
class ChromeCrawlResult:
    listings: list[Listing] = field(default_factory=list)
    product_urls_found: int = 0
    pages_visited: int = 0
    html_saved: int = 0
    manual_waits: int = 0
    errors: list[str] = field(default_factory=list)
    message: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "listings": len(self.listings),
            "product_urls_found": self.product_urls_found,
            "pages_visited": self.pages_visited,
            "html_saved": self.html_saved,
            "manual_waits": self.manual_waits,
            "errors": self.errors[:10],
            "message": self.message,
        }


def _delay_ms() -> float:
    """Pause between listings (main human pacing)."""
    return random.uniform(
        settings.chrome_crawl_delay_min_ms,
        settings.chrome_crawl_delay_max_ms,
    ) / 1000.0

def _ms_range(min_ms: int, max_ms: int) -> float:
    lo = min(min_ms, max_ms)
    hi = max(min_ms, max_ms)
    return random.uniform(lo, hi) / 1000.0


async def _sleep_range(min_ms: int, max_ms: int) -> None:
    await asyncio.sleep(_ms_range(min_ms, max_ms))


async def _pre_nav_pause() -> None:
    """Brief hesitation before navigating to the next URL."""
    await _sleep_range(
        settings.chrome_crawl_pre_nav_min_ms,
        settings.chrome_crawl_pre_nav_max_ms,
    )


async def _read_pause() -> None:
    """Simulate reading the page before/after scrolling."""
    await _sleep_range(
        settings.chrome_crawl_read_min_ms,
        settings.chrome_crawl_read_max_ms,
    )


async def _scroll_pause() -> None:
    await _sleep_range(
        settings.chrome_crawl_scroll_pause_min_ms,
        settings.chrome_crawl_scroll_pause_max_ms,
    )


async def _maybe_idle_break() -> None:
    """Occasional longer pause (checking phone, etc.)."""
    if random.random() < 0.18:
        extra = random.uniform(3.0, 8.0)
        logger.debug("Idle break %.1fs", extra)
        await asyncio.sleep(extra)


async def _human_mouse_wiggle(page) -> None:
    try:
        viewport = page.viewport_size or {"width": 1280, "height": 800}
        w, h = viewport.get("width", 1280), viewport.get("height", 800)
        x = random.randint(int(w * 0.2), int(w * 0.8))
        y = random.randint(int(h * 0.15), int(h * 0.75))
        steps = random.randint(8, 18)
        await page.mouse.move(x, y, steps=steps)
        await asyncio.sleep(random.uniform(0.15, 0.45))
    except Exception:
        pass


def _manual_wait_labels() -> set[str]:
    raw = (settings.chrome_crawl_manual_wait_for or "").strip()
    if not raw:
        return {"captcha", "login_required", "blocked", "page_not_ready"}
    return {part.strip() for part in raw.split(",") if part.strip()}


def _should_wait_for_label(label: str) -> bool:
    return settings.chrome_crawl_wait_for_manual and label in _manual_wait_labels()


def _print_manual_prompt(label: str, url: str, timeout_s: int) -> None:
    hint = _ISSUE_HINTS.get(label, "Fix the issue in the Chrome window.")
    lines = [
        "",
        "=" * 60,
        "ACTION REQUIRED — complete this in your Chrome window",
        "=" * 60,
        f"  Issue:   {label}",
        f"  URL:     {url or '(current tab)'}",
        f"  Hint:    {hint}",
        f"  Timeout: {timeout_s}s (crawler polls until resolved)",
        "=" * 60,
        "",
    ]
    msg = "\n".join(lines)
    print(msg, flush=True)
    logger.info("Waiting for manual fix: %s at %s", label, url)


def _pick_page(browser):
    """Prefer a tab already on therealreal.com."""
    for context in browser.contexts:
        for page in context.pages:
            if "therealreal.com" in (page.url or ""):
                return page
    if browser.contexts and browser.contexts[0].pages:
        return browser.contexts[0].pages[0]
    return None


async def _snapshot_page(page) -> tuple[str, str | None, str]:
    title = await page.title()
    html = await page.content()
    next_raw = None
    try:
        next_raw = await page.evaluate(
            "() => document.getElementById('__NEXT_DATA__')?.textContent || null"
        )
    except Exception:
        pass
    return html, next_raw, title


async def _bring_chrome_forward(page) -> None:
    try:
        await page.bring_to_front()
    except Exception:
        pass


def _page_is_product_ready(
    html: str, url: str, next_raw: str | None, title: str
) -> bool:
    if detect_page_issue(html, title):
        return False
    return parse_product_html(html, url, next_data_raw=next_raw, page_title=title) is not None


async def _wait_for_manual_resolution(
    page,
    url: str,
    label: str,
    *,
    require_product: bool = True,
) -> tuple[str, str | None, str, bool]:
    """
    Block until the user fixes captcha/login/etc. in Chrome.
    Returns (html, next_raw, title, resolved).
    """
    if not _should_wait_for_label(label):
        html, next_raw, title = await _snapshot_page(page)
        return html, next_raw, title, False

    timeout_s = settings.chrome_crawl_manual_wait_seconds
    poll_s = settings.chrome_crawl_manual_poll_seconds
    _print_manual_prompt(label, url, timeout_s)
    await _bring_chrome_forward(page)

    deadline = time.monotonic() + timeout_s
    last_label = label
    html, next_raw, title = await _snapshot_page(page)

    while time.monotonic() < deadline:
        await asyncio.sleep(poll_s)
        html, next_raw, title = await _snapshot_page(page)
        issue = detect_page_issue(html, title)

        if require_product:
            if _page_is_product_ready(html, url, next_raw, title):
                print("\n[OK] Page ready — continuing crawl.\n", flush=True)
                return html, next_raw, title, True
            if issue:
                last_label = issue
            elif parse_failure_reason(html, url, next_data_raw=next_raw, page_title=title) in (
                "page_not_ready",
                "no_product_fields",
            ):
                last_label = "page_not_ready"
        else:
            if not issue and extract_product_urls_from_html(html):
                print("\n[OK] Product links visible — continuing crawl.\n", flush=True)
                return html, next_raw, title, True
            if issue:
                last_label = issue

        # Periodic reminder every ~30s
        elapsed = int(time.monotonic() - (deadline - timeout_s))
        if elapsed > 0 and elapsed % 30 == 0:
            print(f"  ... still waiting ({elapsed}s) — {last_label}", flush=True)

    print(f"\n[TIMEOUT] Manual wait expired after {timeout_s}s.\n", flush=True)
    return html, next_raw, title, False


async def _human_pause(page) -> None:
    """Scroll and idle on page like a shopper reading listings."""
    await _read_pause()
    await _human_mouse_wiggle(page)

    steps = settings.chrome_crawl_scroll_steps
    for step in range(steps):
        delta = random.randint(120, 380)
        if step > 0 and random.random() < 0.22:
            delta = -random.randint(80, 220)
        try:
            await page.mouse.wheel(0, delta)
        except Exception:
            try:
                await page.evaluate(f"window.scrollBy(0, {delta})")
            except Exception:
                pass
        await _scroll_pause()
        if random.random() < 0.35:
            await _human_mouse_wiggle(page)

    await _read_pause()
    await _maybe_idle_break()


async def _navigate_slow(page, url: str) -> tuple[str | None, str | None, str]:
    """
    Returns (html, __NEXT_DATA__ raw JSON, page title).
    Waits for product shell to render before capturing HTML.
    """
    try:
        await _pre_nav_pause()
        await page.goto(url, wait_until="load", timeout=settings.scrape_timeout_ms)
        try:
            await page.wait_for_function(
                """() => {
                    const og = document.querySelector('meta[property="og:title"]')?.content || '';
                    const h1 = document.querySelector('h1')?.innerText || '';
                    const nd = document.getElementById('__NEXT_DATA__')?.textContent || '';
                    return (og.length > 5) || (h1.length > 5) || (nd.length > 200);
                }""",
                timeout=25000,
            )
        except Exception:
            await asyncio.sleep(random.uniform(4.0, 7.0))
        await _human_pause(page)
        return await _snapshot_page(page)
    except Exception as exc:
        logger.warning("Navigation failed %s: %s", url, exc)
        return None, None, ""


def _save_html(name: str, html: str) -> Path:
    HTML_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = HTML_CACHE_DIR / f"{name}.html"
    path.write_text(html, encoding="utf-8")
    return path


async def _extract_urls_with_manual_wait(page, list_url: str) -> list[str]:
    html, next_raw, title = await _navigate_slow(page, list_url)
    if not html:
        return []

    issue = detect_page_issue(html, title)
    if issue and _should_wait_for_label(issue):
        html, next_raw, title, ok = await _wait_for_manual_resolution(
            page, list_url, issue, require_product=False
        )
        if not ok:
            return []

    found = extract_product_urls_from_html(html)
    if found:
        return found

    if _should_wait_for_label("no_product_urls"):
        html, next_raw, title, ok = await _wait_for_manual_resolution(
            page, list_url, "no_product_urls", require_product=False
        )
        if ok:
            return extract_product_urls_from_html(html)
    return []


async def _collect_listing_urls(page, result: ChromeCrawlResult) -> list[str]:
    urls: list[str] = []
    seed_pages = settings.listing_urls()
    for list_url in seed_pages[: max(1, settings.scrape_max_pages)]:
        found = await _extract_urls_with_manual_wait(page, list_url)
        logger.info("Category %s -> %d product links", list_url, len(found))
        urls.extend(found)
        await asyncio.sleep(_delay_ms())
    seen: set[str] = set()
    unique: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique[: settings.chrome_crawl_max_listings]


async def _process_product_page(
    page,
    url: str,
    index: int,
    result: ChromeCrawlResult,
) -> tuple[Listing | None, str | None]:
    html, next_raw, title = await _navigate_slow(page, url)
    result.pages_visited += 1
    if not html:
        result.errors.append(f"no_html:{url}")
        return None, None

    issue = detect_page_issue(html, title)
    if issue:
        _save_html(f"failed_{index}_{issue}", html)
        if _should_wait_for_label(issue):
            result.manual_waits += 1
            html, next_raw, title, ok = await _wait_for_manual_resolution(
                page, url, issue, require_product=True
            )
            if not ok:
                result.errors.append(f"{issue}_timeout:{url}")
                return None, None
        else:
            result.errors.append(f"{issue}:{url}")
            return None, None

    listing = parse_product_html(html, url, next_data_raw=next_raw, page_title=title)
    if listing:
        return listing, html

    reason = parse_failure_reason(html, url, next_data_raw=next_raw, page_title=title)
    _save_html(f"failed_{index}_{reason}", html)

    if _should_wait_for_label(reason):
        result.manual_waits += 1
        html, next_raw, title, ok = await _wait_for_manual_resolution(
            page, url, reason, require_product=True
        )
        if ok:
            listing = parse_product_html(
                html, url, next_data_raw=next_raw, page_title=title
            )
            if listing:
                return listing, html
        result.errors.append(f"parse_failed:{reason}_timeout:{url}")
    else:
        result.errors.append(f"parse_failed:{reason}:{url}")

    logger.warning("Parse failed (%s) %s", reason, url)
    return None, None


async def run_chrome_crawl() -> ChromeCrawlResult:
    """
    Attach to the user's Chrome, discover product URLs, visit each slowly,
    save HTML snapshots, and parse listings.
    """
    result = ChromeCrawlResult()
    playwright = None
    browser = None

    try:
        playwright, browser, _context, default_page = await connect_to_chrome()
    except ChromeNotRunningError as exc:
        result.message = str(exc)
        result.errors.append(str(exc))
        return result

    page = _pick_page(browser) or default_page
    if not page:
        result.message = "no_chrome_tab"
        result.errors.append("no_chrome_tab")
        return result

    try:
        product_urls = await _collect_listing_urls(page, result)
        result.product_urls_found = len(product_urls)
        logger.info("Found %d product URLs in Chrome", len(product_urls))

        if not product_urls:
            if settings.chrome_crawl_wait_for_manual and _should_wait_for_label(
                "no_product_urls"
            ):
                result.manual_waits += 1
                current_url = page.url or settings.scrape_list_url
                _, _, _, ok = await _wait_for_manual_resolution(
                    page,
                    current_url,
                    "no_product_urls",
                    require_product=False,
                )
                if ok:
                    html, _, _ = await _snapshot_page(page)
                    product_urls = extract_product_urls_from_html(html)[
                        : settings.chrome_crawl_max_listings
                    ]
                    result.product_urls_found = len(product_urls)

        if not product_urls:
            result.message = "no_product_urls_found_sign_in_and_open_category_in_chrome"
            return result

        for i, url in enumerate(product_urls):
            logger.info("Visiting (%d/%d) %s", i + 1, len(product_urls), url)
            listing, saved_html = await _process_product_page(page, url, i, result)
            if not listing:
                continue

            if saved_html:
                _save_html(listing.id, saved_html)
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
