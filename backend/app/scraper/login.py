"""Detect and wait for manual TheRealReal login (triggered from Re-scrape, not at startup)."""

from __future__ import annotations

import asyncio
import logging
import re

from playwright.async_api import BrowserContext, Page

from backend.app.config import settings
from backend.app.session_state import mark_session_authenticated

logger = logging.getLogger(__name__)

SIGN_IN_PATTERN = re.compile(r"sign\s*in", re.I)


async def detect_logged_in(page: Page) -> bool:
    """Best-effort check whether the browser appears authenticated."""
    try:
        sign_out = page.get_by_role("link", name=re.compile(r"sign\s*out|log\s*out", re.I))
        if await sign_out.first.is_visible(timeout=1200):
            return True
    except Exception:
        pass

    try:
        account = page.locator('a[href*="/account"], a[href*="/users/"]').first
        if await account.is_visible(timeout=1200):
            return True
    except Exception:
        pass

    try:
        sign_in = page.get_by_role("link", name=SIGN_IN_PATTERN)
        if await sign_in.first.is_visible(timeout=1200):
            return False
    except Exception:
        pass

    html = (await page.content())[:12000].lower()
    if "sign out" in html or "log out" in html or 'href="/account"' in html:
        return True
    if "sign in" in html and "create account" in html:
        return False

    return False


async def open_landing_tab(context: BrowserContext) -> Page:
    """Open The RealReal default landing page in a new browser tab."""
    landing_url = settings.scrape_home_url
    tab = await context.new_page()
    try:
        await tab.bring_to_front()
    except Exception:
        pass
    logger.info("Opened landing page in new tab: %s", landing_url)
    await tab.goto(
        landing_url,
        wait_until="domcontentloaded",
        timeout=settings.scrape_timeout_ms,
    )
    return tab


async def ensure_logged_in(
    page: Page,
    *,
    interactive: bool,
    use_landing_page: bool = False,
) -> tuple[bool, str]:
    """
    Ensure user is logged in.

    interactive=True: wait for manual sign-in in the browser.
    use_landing_page=True: navigate to TRR homepage (for sign-in tab flow).
    """
    if not settings.scrape_require_login:
        return True, "login_not_required"

    if await detect_logged_in(page):
        mark_session_authenticated()
        logger.info("The RealReal session is active")
        return True, "already_logged_in"

    if not interactive:
        return False, "login_required: click Re-scrape to sign in via the browser"

    if settings.scrape_headless:
        return False, (
            "login_required_but_headless: set SCRAPE_HEADLESS=false, "
            "click Re-scrape, and sign in in the browser window"
        )

    if not use_landing_page:
        login_url = settings.scrape_login_url
        logger.info("Opening login for interactive session: %s", login_url)
        try:
            await page.goto(
                login_url,
                wait_until="domcontentloaded",
                timeout=settings.scrape_timeout_ms,
            )
        except Exception as exc:
            return False, f"login_navigation_failed:{exc}"
    else:
        landing_url = settings.scrape_home_url
        logger.info("Landing tab ready for sign-in: %s", landing_url)
        if page.url != landing_url.rstrip("/") and not page.url.startswith(landing_url):
            try:
                await page.goto(
                    landing_url,
                    wait_until="domcontentloaded",
                    timeout=settings.scrape_timeout_ms,
                )
            except Exception as exc:
                return False, f"landing_navigation_failed:{exc}"

    wait_seconds = settings.scrape_login_wait_seconds
    logger.info(
        "Waiting up to %s seconds — sign in on The RealReal in the browser tab.",
        wait_seconds,
    )

    loop = asyncio.get_running_loop()
    deadline = loop.time() + wait_seconds
    while loop.time() < deadline:
        if await detect_logged_in(page):
            mark_session_authenticated()
            logger.info("Login successful — session saved for future Re-scrape runs")
            await asyncio.sleep(1.5)
            return True, "logged_in_manually"
        await asyncio.sleep(2.0)

    return False, "login_timeout: sign in via the browser before time runs out"
