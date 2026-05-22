"""Detect and wait for manual TheRealReal login in a headed browser."""

from __future__ import annotations

import asyncio
import logging
import re

from backend.app.config import settings

logger = logging.getLogger(__name__)

SIGN_IN_PATTERN = re.compile(r"sign\s*in", re.I)


async def detect_logged_in(page) -> bool:
    """Best-effort check whether the session appears authenticated."""
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

    # Ambiguous — treat as not logged in when login is required
    return False


async def ensure_logged_in(page) -> tuple[bool, str]:
    """
    Ensure user is logged in. Opens login URL and waits for manual login when needed.
    Returns (success, message).
    """
    if not settings.scrape_require_login:
        return True, "login_not_required"

    if await detect_logged_in(page):
        logger.info("Already logged in to The RealReal")
        return True, "already_logged_in"

    if settings.scrape_headless:
        return False, (
            "login_required_but_headless: set SCRAPE_HEADLESS=false, "
            "log in via the browser window, then re-scrape"
        )

    login_url = settings.scrape_login_url
    logger.info("Opening login page: %s", login_url)
    try:
        await page.goto(
            login_url,
            wait_until="domcontentloaded",
            timeout=settings.scrape_timeout_ms,
        )
    except Exception as exc:
        return False, f"login_navigation_failed:{exc}"

    wait_seconds = settings.scrape_login_wait_seconds
    logger.info(
        "Waiting up to %s seconds — sign in to The RealReal in the browser window.",
        wait_seconds,
    )

    deadline = asyncio.get_event_loop().time() + wait_seconds
    while asyncio.get_event_loop().time() < deadline:
        if await detect_logged_in(page):
            logger.info("Login detected, continuing scrape")
            await asyncio.sleep(_random_pause())
            return True, "logged_in_manually"
        await asyncio.sleep(2.0)

    return False, "login_timeout: complete sign-in before the wait period ends"


def _random_pause() -> float:
    return 1.5
