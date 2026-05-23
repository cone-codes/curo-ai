"""Interactive TRR sign-in before ScrapFly — saves cookies automatically (no export)."""

from __future__ import annotations

import logging
from pathlib import Path

from backend.app.config import settings
from backend.app.scraper.cookies import COOKIES_PATH, load_cookie_file, save_cookies_to_file
from backend.app.scraper.stealth import STEALTH_INIT_SCRIPT
from backend.app.session_state import mark_session_authenticated

logger = logging.getLogger(__name__)


def cookie_file_path() -> Path:
    if settings.scrapfly_cookies_path.strip():
        return Path(settings.scrapfly_cookies_path.strip())
    return COOKIES_PATH


def has_saved_cookies(min_count: int = 3) -> bool:
    cookies = load_cookie_file(cookie_file_path())
    if len(cookies) < min_count:
        return False
    for c in cookies:
        domain = str(c.get("domain", ""))
        if "therealreal.com" in domain:
            return True
    return False


async def interactive_login_for_scrapfly(*, force: bool = False) -> tuple[bool, str]:
    if not settings.scrapfly_login_first:
        return True, "login_skipped"

    if (
        not force
        and settings.scrapfly_skip_login_if_cookies
        and has_saved_cookies()
    ):
        logger.info("Using existing cookies at %s", cookie_file_path())
        return True, "cookies_on_file"

    print(
        "\n" + "=" * 60,
        "\nSIGN IN — The RealReal (for ScrapFly)",
        "\n" + "=" * 60,
        "\nA browser window will open. Sign in (Google or email).",
        "\nCookies are saved automatically — no manual export.",
        f"\nWaiting up to {settings.scrape_login_wait_seconds} seconds...",
        "\n" + "=" * 60 + "\n",
        flush=True,
    )

    from playwright.async_api import async_playwright

    profile = settings.browser_profile_path()
    profile.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            slow_mo=max(100, settings.scrape_slow_mo_ms or 200),
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.add_init_script(STEALTH_INIT_SCRIPT)

        from backend.app.scraper.login import ensure_logged_in

        ok, msg = await ensure_logged_in(
            page,
            interactive=True,
            use_landing_page=False,
        )

        if ok:
            cookies = await context.cookies()
            path = cookie_file_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            save_cookies_to_file(cookies, path)
            mark_session_authenticated()
            print(
                f"\n[OK] Signed in — saved {len(cookies)} cookies to {path}\n",
                flush=True,
            )
        else:
            print(f"\n[FAILED] {msg}\n", flush=True)

        await context.close()

    return ok, msg
