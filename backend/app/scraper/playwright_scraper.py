"""Playwright-based scraper with session warming, stealth, and human-like pacing."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urljoin, urlparse

from backend.app.config import settings
from backend.app.models import Listing
from backend.app.scraper.login import detect_logged_in, ensure_logged_in, open_landing_tab
from backend.app.scraper.stealth import STEALTH_INIT_SCRIPT

logger = logging.getLogger(__name__)

PRODUCT_PATH = re.compile(r"/products/[a-z0-9-]+", re.I)
BlockType = Literal["blocked", "captcha", "timeout", "navigation_error", "parse_error", None]
OutcomeType = Literal["success", "partial", "blocked", "captcha", "timeout", "error", "empty", "login_required"]

BASE_URL = "https://www.therealreal.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

COOKIE_DISMISS_SELECTORS = [
    "button:has-text('Accept')",
    "button:has-text('Accept All')",
    "button:has-text('Got it')",
    "[data-testid='cookie-accept']",
]


@dataclass
class ScrapeRunResult:
    listings: list[Listing] = field(default_factory=list)
    outcome: OutcomeType = "empty"
    message: str = "ok"
    block_type: BlockType = None
    pages_scraped: int = 0
    products_per_page: list[int] = field(default_factory=list)
    blocked_at_url: str | None = None
    used_persistent_profile: bool = False
    headless: bool = True
    opened_sign_in_tab: bool = False
    sign_in_landing_url: str = ""

    def to_diagnostics(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "block_type": self.block_type,
            "pages_scraped": self.pages_scraped,
            "products_per_page": self.products_per_page,
            "blocked_at_url": self.blocked_at_url,
            "used_persistent_profile": self.used_persistent_profile,
            "headless": self.headless,
            "listing_urls": settings.listing_urls(),
            "require_login": settings.scrape_require_login,
            "opened_sign_in_tab": self.opened_sign_in_tab,
        }


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] if path else url


def _random_delay_ms(min_ms: int, max_ms: int) -> float:
    return random.uniform(min_ms, max_ms) / 1000.0


def detect_block(html: str, page_title: str, http_status: int | None) -> BlockType:
    lowered = page_title.lower()
    if http_status == 403:
        return "blocked"
    if "denied" in lowered or "access to this page has been denied" in lowered:
        return "blocked"
    if "px-captcha" in html or "press & hold" in html.lower():
        return "captcha"
    if "perimeterx" in html.lower() and "captcha" in html.lower():
        return "captcha"
    return None


def _listing_from_product_payload(data: dict[str, Any], base_url: str) -> Listing | None:
    product_id = str(data.get("id") or data.get("slug") or data.get("sku") or "")
    url = data.get("url") or data.get("permalink") or ""
    if url and not url.startswith("http"):
        url = urljoin(base_url, url)
    if not url and product_id:
        url = f"{BASE_URL}/products/{product_id}"

    title = (data.get("title") or data.get("name") or "").strip()
    if not title:
        return None

    description = (
        data.get("description")
        or data.get("long_description")
        or data.get("short_description")
        or ""
    )
    if isinstance(description, list):
        description = " ".join(str(x) for x in description)
    description = str(description).strip()

    images: list[str] = []
    for key in ("images", "image_urls", "photos"):
        val = data.get(key)
        if not val:
            continue
        if isinstance(val, str):
            images.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    images.append(item)
                elif isinstance(item, dict):
                    u = item.get("url") or item.get("src") or item.get("image_url")
                    if u:
                        images.append(str(u))

    price = data.get("price") or data.get("sale_price") or data.get("list_price")
    if isinstance(price, dict):
        price = price.get("amount") or price.get("value")

    designer = data.get("designer") or data.get("brand") or data.get("designer_name")
    if isinstance(designer, dict):
        designer = designer.get("name") or designer.get("title")

    listing_id = product_id or _slug_from_url(url)
    if not listing_id:
        return None

    return Listing(
        id=listing_id,
        url=url or f"{BASE_URL}/products/{listing_id}",
        title=title,
        description=description or title,
        designer=str(designer) if designer else None,
        category=data.get("category") or data.get("taxonomy"),
        price=float(price) if price is not None else None,
        condition=data.get("condition"),
        size=data.get("size"),
        image_urls=images[:8],
        metadata={"source": "playwright"},
        scraped_at=datetime.now(timezone.utc),
    )


def _extract_products_from_next_data(html: str, base_url: str) -> list[Listing]:
    marker = '<script id="__NEXT_DATA__" type="application/json">'
    start = html.find(marker)
    if start < 0:
        return []
    start += len(marker)
    end = html.find("</script>", start)
    if end < 0:
        return []
    try:
        payload = json.loads(html[start:end])
    except json.JSONDecodeError:
        return []

    found: list[Listing] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            keys = set(node.keys())
            if {"title", "name"} & keys and ({"id", "slug"} & keys or "url" in keys):
                listing = _listing_from_product_payload(node, base_url)
                if listing and listing.title:
                    found.append(listing)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    seen: set[str] = set()
    unique: list[Listing] = []
    for listing in found:
        if listing.id in seen:
            continue
        seen.add(listing.id)
        unique.append(listing)
    return unique


async def _extract_from_dom_cards_async(page, base_url: str) -> list[Listing]:
    cards = page.locator('a[href*="/products/"]')
    try:
        count = await cards.count()
    except Exception:
        return []
    count = min(count, 120)
    listings: list[Listing] = []
    seen_urls: set[str] = set()

    for i in range(count):
        link = cards.nth(i)
        href = await link.get_attribute("href")
        if not href or href in seen_urls:
            continue
        if not PRODUCT_PATH.search(href):
            continue
        seen_urls.add(href)
        url = href if href.startswith("http") else urljoin(base_url, href)
        title = (await link.get_attribute("aria-label") or "").strip()
        if not title:
            try:
                title = (await link.inner_text()).strip().split("\n")[0]
            except Exception:
                title = ""
        if not title or len(title) < 3:
            continue
        listing_id = _slug_from_url(url)
        img = ""
        try:
            img_el = link.locator("img").first
            img = (await img_el.get_attribute("src")) or (await img_el.get_attribute("data-src")) or ""
        except Exception:
            pass
        listings.append(
            Listing(
                id=listing_id,
                url=url,
                title=title[:300],
                description=title,
                image_urls=[img] if img else [],
                metadata={"source": "dom_card"},
                scraped_at=datetime.now(timezone.utc),
            )
        )
    return listings


async def _apply_stealth(page) -> None:
    if settings.scrape_use_stealth:
        await page.add_init_script(STEALTH_INIT_SCRIPT)


async def _simulate_human(page) -> None:
    width = random.randint(280, 920)
    height = random.randint(180, 640)
    try:
        await page.mouse.move(width, height, steps=random.randint(8, 20))
    except Exception:
        pass
    for _ in range(settings.scrape_scroll_steps):
        delta = random.randint(250, 700)
        try:
            await page.mouse.wheel(0, delta)
        except Exception:
            try:
                await page.evaluate(f"window.scrollBy(0, {delta})")
            except Exception:
                pass
        await asyncio.sleep(random.uniform(0.25, 0.9))


async def _try_dismiss_cookies(page) -> None:
    for selector in COOKIE_DISMISS_SELECTORS:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=800):
                await btn.click(timeout=2000)
                await asyncio.sleep(random.uniform(0.4, 1.0))
                return
        except Exception:
            continue


async def _warm_session(page) -> BlockType | None:
    if not settings.scrape_warmup_enabled:
        return None

    logger.info("Warming session via %s", settings.scrape_home_url)
    try:
        response = await page.goto(
            settings.scrape_home_url,
            wait_until="domcontentloaded",
            timeout=settings.scrape_timeout_ms,
        )
    except Exception as exc:
        logger.warning("Warmup navigation failed: %s", exc)
        return "timeout"

    await asyncio.sleep(_random_delay_ms(
        settings.scrape_warmup_delay_min_ms,
        settings.scrape_warmup_delay_max_ms,
    ))
    html = await page.content()
    title = await page.title()
    block = detect_block(html, title, response.status if response else None)
    if block:
        return block

    await _try_dismiss_cookies(page)
    await _simulate_human(page)
    await asyncio.sleep(_random_delay_ms(800, 1800))
    return None


async def _fetch_listing_page(page, url: str) -> tuple[list[Listing], BlockType | None, str | None]:
    """Returns (listings, block_type, error_message)."""
    try:
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=settings.scrape_timeout_ms,
        )
    except Exception as exc:
        logger.warning("Navigation failed for %s: %s", url, exc)
        return [], "timeout", str(exc)

    await asyncio.sleep(_random_delay_ms(1200, 2400))
    await _simulate_human(page)
    await asyncio.sleep(_random_delay_ms(600, 1400))

    html = await page.content()
    title = await page.title()
    status = response.status if response else None
    block = detect_block(html, title, status)
    if block:
        return [], block, None

    page_listings = _extract_products_from_next_data(html, BASE_URL)
    if not page_listings:
        page_listings = await _extract_from_dom_cards_async(page, BASE_URL)

    if not page_listings:
        return [], "parse_error", "no_products_on_page"

    return page_listings, None, None


def _paginated_url(base_url: str, page_num: int) -> str:
    if page_num <= 1:
        return base_url
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}page={page_num}"




async def _collect_listings_from_urls(
    page,
    listing_urls: list[str],
    pages_budget: int,
    result: ScrapeRunResult,
) -> list[Listing]:
    """Scrape listing pages and update result counters."""
    all_listings: list[Listing] = []
    pages_used = 0
    for list_url in listing_urls:
        if pages_used >= pages_budget:
            break
        remaining = pages_budget - pages_used
        for page_num in range(1, remaining + 1):
            url = _paginated_url(list_url, page_num)
            if pages_used > 0:
                await asyncio.sleep(_random_delay_ms(
                    settings.scrape_delay_min_ms,
                    settings.scrape_delay_max_ms,
                ))

            page_listings, block, nav_error = await _fetch_listing_page(page, url)
            pages_used += 1
            result.pages_scraped = pages_used

            if block in ("blocked", "captcha"):
                result.block_type = block
                result.blocked_at_url = url
                result.message = block
                all_listings.extend(page_listings)
                if settings.scrape_stop_on_block:
                    return _dedupe(all_listings)
                continue

            if block == "parse_error":
                result.products_per_page.append(0)
                logger.info("No products parsed at %s, continuing", url)
                continue

            if nav_error:
                result.block_type = "navigation_error"
                result.message = nav_error
                if settings.scrape_stop_on_block:
                    return _dedupe(all_listings)
                continue

            result.products_per_page.append(len(page_listings))
            all_listings.extend(page_listings)
    return _dedupe(all_listings)


async def scrape_listings_async(known_ids: set[str] | None = None) -> ScrapeRunResult:
    from playwright.async_api import async_playwright

    result = ScrapeRunResult(
        headless=settings.scrape_headless,
        used_persistent_profile=settings.scrape_persistent_profile,
    )
    all_listings: list[Listing] = []
    listing_urls = settings.listing_urls()
    pages_budget = settings.scrape_max_pages

    async with async_playwright() as p:
        context = None
        browser = None
        profile_dir = settings.browser_profile_path()

        slow_mo = settings.scrape_slow_mo_ms
        if not settings.scrape_headless and slow_mo <= 0:
            slow_mo = 250

        launch_kwargs: dict[str, Any] = {
            "headless": settings.scrape_headless,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if slow_mo > 0:
            launch_kwargs["slow_mo"] = slow_mo
        if settings.scrape_browser_channel.strip():
            launch_kwargs["channel"] = settings.scrape_browser_channel.strip()

        logger.info(
            "Launching browser headless=%s slow_mo=%s channel=%s profile=%s",
            settings.scrape_headless,
            slow_mo,
            settings.scrape_browser_channel or "chromium",
            profile_dir,
        )

        if settings.scrape_persistent_profile:
            profile_dir.mkdir(parents=True, exist_ok=True)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                user_agent=USER_AGENT,
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                timezone_id="America/New_York",
                **launch_kwargs,
            )
            page = context.pages[0] if context.pages else await context.new_page()
        else:
            browser = await p.chromium.launch(**launch_kwargs)
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                timezone_id="America/New_York",
            )
            page = await context.new_page()

        await _apply_stealth(page)

        warmup_block = await _warm_session(page)
        if warmup_block:
            result.block_type = warmup_block
            result.blocked_at_url = settings.scrape_home_url
            result.outcome = "captcha" if warmup_block == "captcha" else "blocked"
            result.message = f"warmup_{warmup_block}"
            await _close(context, browser)
            return result

        already_logged_in = await detect_logged_in(page)
        login_ok, login_message = await ensure_logged_in(
            page, interactive=not already_logged_in
        )
        if not login_ok:
            result.outcome = "login_required"
            result.message = login_message
            result.blocked_at_url = settings.scrape_login_url
            await _close(context, browser)
            return result

        all_listings = await _collect_listings_from_urls(
            page, listing_urls, pages_budget, result
        )

        known_ids = known_ids or set()
        new_listings = [l for l in all_listings if l.id not in known_ids]

        if (
            len(new_listings) == 0
            and settings.scrape_open_landing_on_no_new
            and settings.scrape_require_login
            and not settings.scrape_headless
        ):
            result.opened_sign_in_tab = True
            result.sign_in_landing_url = settings.scrape_home_url
            sign_in_tab = await open_landing_tab(context)
            login_ok, login_message = await ensure_logged_in(
                sign_in_tab, interactive=True, use_landing_page=True
            )
            if login_ok and settings.scrape_retry_after_sign_in:
                logger.info("Retrying scrape after sign-in on landing tab")
                retry_listings = await _collect_listings_from_urls(
                    sign_in_tab, listing_urls, pages_budget, result
                )
                all_listings = _dedupe(retry_listings + all_listings)
                new_listings = [l for l in all_listings if l.id not in known_ids]
                if new_listings:
                    result.message = "ok_after_sign_in_retry"
            elif not login_ok:
                result.message = login_message
                result.outcome = "login_required"

        await _close(context, browser)

    result.listings = _dedupe(all_listings)
    result.outcome = _finalize_outcome(result)
    if result.listings and result.block_type:
        result.message = f"{result.block_type}_after_partial"
    elif result.listings:
        result.message = "ok"
    elif result.block_type:
        result.message = result.block_type
    elif not result.message or result.message == "ok":
        result.message = "no_products_found"
    return result


async def _hold_browser_open_for_inspection() -> None:
    seconds = settings.scrape_keep_browser_open_seconds
    if seconds > 0:
        logger.info("Keeping browser open for %s seconds (SCRAPE_KEEP_BROWSER_OPEN_SECONDS)", seconds)
        await asyncio.sleep(seconds)


async def _close(context, browser) -> None:
    await _hold_browser_open_for_inspection()
    try:
        if context:
            await context.close()
    except Exception:
        pass
    try:
        if browser:
            await browser.close()
    except Exception:
        pass


def _dedupe(listings: list[Listing]) -> list[Listing]:
    return list({l.id: l for l in listings}.values())


def _finalize_outcome(result: ScrapeRunResult) -> OutcomeType:
    if result.listings and result.block_type:
        return "partial"
    if result.listings:
        return "success"
    if result.block_type == "captcha":
        return "captcha"
    if result.block_type in ("blocked",):
        return "blocked"
    if result.block_type == "timeout":
        return "timeout"
    if result.block_type:
        return "error"
    if result.message and "login" in result.message:
        return "login_required"
    return "empty"
