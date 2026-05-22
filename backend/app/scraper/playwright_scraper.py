"""Playwright-based scraper for TheRealReal listing pages."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from backend.app.config import settings
from backend.app.models import Listing

logger = logging.getLogger(__name__)

PRODUCT_PATH = re.compile(r"/products/[a-z0-9-]+", re.I)


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] if path else url


def _listing_from_product_payload(data: dict[str, Any], base_url: str) -> Listing | None:
    """Normalize assorted JSON shapes into a Listing."""
    product_id = str(data.get("id") or data.get("slug") or data.get("sku") or "")
    url = data.get("url") or data.get("permalink") or ""
    if url and not url.startswith("http"):
        url = urljoin(base_url, url)
    if not url and product_id:
        url = f"https://www.therealreal.com/products/{product_id}"

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
        url=url or f"https://www.therealreal.com/products/{listing_id}",
        title=title,
        description=description or title,
        designer=str(designer) if designer else None,
        category=data.get("category") or data.get("taxonomy"),
        price=float(price) if price is not None else None,
        condition=data.get("condition"),
        size=data.get("size"),
        image_urls=images[:8],
        metadata={"source": "playwright", "raw_keys": list(data.keys())[:20]},
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
    # Deduplicate by id
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


async def scrape_listings_async() -> tuple[list[Listing], str]:
    from playwright.async_api import async_playwright

    listings: list[Listing] = []
    message = "ok"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.scrape_headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )
        page = await context.new_page()
        list_url = settings.scrape_list_url

        for page_num in range(1, settings.scrape_max_pages + 1):
            url = list_url if page_num == 1 else f"{list_url}?page={page_num}"
            try:
                response = await page.goto(
                    url, wait_until="domcontentloaded", timeout=settings.scrape_timeout_ms
                )
            except Exception as exc:
                logger.warning("Navigation failed for %s: %s", url, exc)
                message = f"navigation_error:{exc}"
                break

            status = response.status if response else 0
            await page.wait_for_timeout(2500)
            html = await page.content()
            title = await page.title()

            if status == 403 or "denied" in title.lower() or "px-captcha" in html:
                message = "blocked_by_bot_protection"
                break

            page_listings = _extract_products_from_next_data(html, "https://www.therealreal.com")
            if not page_listings:
                page_listings = await _extract_from_dom_cards_async(page, "https://www.therealreal.com")

            if not page_listings:
                message = "no_products_on_page"
                break

            listings.extend(page_listings)

        await browser.close()

    # Deduplicate
    by_id: dict[str, Listing] = {l.id: l for l in listings}
    return list(by_id.values()), message
