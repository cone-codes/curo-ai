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
