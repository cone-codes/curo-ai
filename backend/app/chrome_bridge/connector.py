"""Attach to the user's real Chrome via Chrome DevTools Protocol (CDP)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)


class ChromeNotRunningError(RuntimeError):
    """Raised when Chrome is not listening for CDP connections."""


async def check_cdp_available(endpoint: str | None = None) -> dict[str, Any]:
    url = (endpoint or settings.chrome_cdp_url).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{url}/json/version")
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        raise ChromeNotRunningError(
            f"Cannot reach Chrome at {url}. Start Chrome with remote debugging enabled. "
            f"See scripts/start_chrome_debug.sh. ({exc})"
        ) from exc


async def connect_to_chrome(endpoint: str | None = None):
    """
    Connect Playwright to an existing Chrome instance.
    Returns (playwright, browser, context, page).
    """
    from playwright.async_api import async_playwright

    endpoint = (endpoint or settings.chrome_cdp_url).rstrip("/")
    await check_cdp_available(endpoint)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.connect_over_cdp(endpoint)

    trr_pages = []
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "therealreal.com" in (pg.url or ""):
                trr_pages.append(pg)
    if trr_pages:
        page = trr_pages[-1]
        context = page.context
    else:
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()

    logger.info(
        "Connected to Chrome via CDP (%s) — tab: %s",
        endpoint,
        page.url or "(blank)",
    )
    return playwright, browser, context, page


async def disconnect(playwright, browser=None) -> None:
    # CDP: only disconnect Playwright; leave the user's Chrome running.
    try:
        await playwright.stop()
    except Exception:
        pass
