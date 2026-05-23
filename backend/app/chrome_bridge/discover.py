"""Discover product URLs from a live Chrome page (JS-rendered grids)."""

from __future__ import annotations

import asyncio
import logging
import random
from urllib.parse import urljoin, urlparse

from backend.app.config import settings
from backend.app.chrome_bridge.parser import extract_product_urls_from_html, is_product_path

logger = logging.getLogger(__name__)

BASE = "https://www.therealreal.com"


def normalize_product_url(href: str) -> str | None:
    if not href or "/products/" not in href:
        return None
    full = href if href.startswith("http") else urljoin(BASE, href)
    parsed = urlparse(full)
    if parsed.netloc and "therealreal.com" not in parsed.netloc:
        return None
    if not is_product_path(parsed.path):
        return None
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


async def scroll_category_page(page) -> None:
    """Scroll listing grids so lazy-loaded product cards appear."""
    rounds = settings.chrome_crawl_category_scroll_rounds
    pause = random.uniform(
        settings.chrome_crawl_scroll_pause_min_ms,
        settings.chrome_crawl_scroll_pause_max_ms,
    ) / 1000.0
    for i in range(rounds):
        delta = random.randint(350, 900)
        try:
            await page.mouse.wheel(0, delta)
        except Exception:
            try:
                await page.evaluate(f"window.scrollBy(0, {delta})")
            except Exception:
                pass
        await asyncio.sleep(pause)
        if i % 4 == 3:
            try:
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(0.4)
            except Exception:
                pass


async def extract_urls_from_live_dom(page) -> list[str]:
    """Read product links from the DOM after React has rendered."""
    try:
        hrefs: list[str] = await page.evaluate(
            """() => {
                const out = new Set();
                for (const a of document.querySelectorAll('a[href]')) {
                    const h = a.href || a.getAttribute('href') || '';
                    if (h.includes('/products/')) {
                        out.add(h.split('#')[0].split('?')[0]);
                    }
                }
                return [...out];
            }"""
        )
    except Exception as exc:
        logger.warning("DOM link extract failed: %s", exc)
        hrefs = []

    seen: set[str] = set()
    urls: list[str] = []
    for href in hrefs:
        norm = normalize_product_url(href)
        if norm and norm not in seen:
            seen.add(norm)
            urls.append(norm)
    return urls


async def extract_urls_combined(page, html: str | None = None) -> list[str]:
    """DOM links + optional static HTML parse."""
    urls = await extract_urls_from_live_dom(page)
    if html:
        for u in extract_product_urls_from_html(html):
            if u not in urls:
                urls.append(u)
    return urls
