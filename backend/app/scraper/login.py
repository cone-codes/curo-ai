"""Detect and wait for manual TheRealReal login (triggered from Re-scrape, not at startup)."""

from __future__ import annotations

import asyncio
import logging
import re

from backend.app.config import settings
from backend.app.session_state import is_session_authenticated, mark_session_authenticated

logger = logging.getLogger(__name__)

SIGN_IN_PATTERN = re.compile(r"sign\s*in", re.I)


async def detect_logged_in(page) -> bool:
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


async def ensure_logged_in(page, *, interactive: bool) -> tuple[bool, str]:
    """
    Ensure user is logged in.

    interactive=True: open login page and wait for manual sign-in (first Re-scrape).
    interactive=False: quick check only (should not be used before session exists).
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

    wait_seconds = settings.scrape_login_wait_seconds
    logger.info(
        "Waiting up to %s seconds for sign-in (first Re-scrape authentication).",
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
