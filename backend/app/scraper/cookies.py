"""Load Playwright cookies exported from your browser."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from playwright.async_api import BrowserContext

from backend.app.config import DATA_DIR

logger = logging.getLogger(__name__)

COOKIES_PATH = DATA_DIR / "trr_cookies.json"


def load_cookie_file(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or COOKIES_PATH
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read cookies from %s: %s", path, exc)
        return []
    if isinstance(data, dict) and "cookies" in data:
        data = data["cookies"]
    if not isinstance(data, list):
        return []
    return data


def cookie_site_key(cookie: dict[str, Any]) -> str:
    """Domain from Playwright exports or host from Cookie-Editor exports."""
    return str(cookie.get("domain") or cookie.get("host") or "").lower()


def cookies_for_trr(cookies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in cookies if "therealreal.com" in cookie_site_key(c)]


def has_usable_trr_cookies(path: Path | None = None, min_count: int = 3) -> bool:
    cookies = load_cookie_file(path)
    trr = cookies_for_trr(cookies)
    if len(trr) >= min_count:
        return True
    named = [c for c in cookies if c.get("name") and c.get("value") is not None]
    return len(named) >= max(min_count, 8)


def describe_cookie_file(path: Path | None = None) -> str:
    path = path or COOKIES_PATH
    if not path.exists():
        return f"missing:{path}"
    try:
        json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return f"invalid_json:{path}:{exc}"
    cookies = load_cookie_file(path)
    if not cookies:
        return f"empty_or_wrong_shape:{path}"
    trr = cookies_for_trr(cookies)
    with_host = sum(1 for c in cookies if c.get("host"))
    with_domain = sum(1 for c in cookies if c.get("domain"))
    if len(trr) >= 3:
        return f"ok:{len(cookies)}_cookies_{len(trr)}_for_trr"
    named = [c for c in cookies if c.get("name") and c.get("value") is not None]
    if len(named) >= 8:
        return f"ok_no_site_field:{len(named)}_name_value_pairs"
    return (
        f"unrecognized:{len(cookies)}_entries_"
        f"trr={len(trr)}_host_fields={with_host}_domain_fields={with_domain}"
    )


async def apply_cookies_to_context(context: BrowserContext, path: Path | None = None) -> int:
    cookies = load_cookie_file(path)
    if not cookies:
        return 0
    try:
        await context.add_cookies(cookies)
        logger.info("Loaded %d cookies into browser context", len(cookies))
        return len(cookies)
    except Exception as exc:
        logger.warning("Failed to apply cookies: %s", exc)
        return 0


def save_cookies_to_file(cookies: list[dict[str, Any]], path: Path | None = None) -> None:
    path = path or COOKIES_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cookies, indent=2))
