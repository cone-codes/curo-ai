"""Fetch The RealReal pages via ScrapFly Scrape API."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from backend.app.config import settings
from backend.app.scraper.cookies import load_cookie_file

logger = logging.getLogger(__name__)


class ScrapflyNotConfiguredError(RuntimeError):
    """Raised when SCRAPFLY_API_KEY is missing."""


@dataclass
class ScrapflyFetchResult:
    url: str
    html: str
    status_code: int
    api_cost: int
    success: bool
    error: str | None = None


def _cookie_header() -> str | None:
    if not settings.scrapfly_use_cookies_file:
        return None
    from pathlib import Path as PathLib

    path: PathLib | None = None
    if settings.scrapfly_cookies_path.strip():
        path = PathLib(settings.scrapfly_cookies_path.strip())
    cookies = load_cookie_file(path)
    if not cookies:
        return None
    parts: list[str] = []
    for c in cookies:
        name = c.get("name")
        value = c.get("value")
        if name and value is not None:
            parts.append(f"{name}={value}")
    return "; ".join(parts) if parts else None


def _build_scrape_config(url: str, *, auto_scroll: bool = False):
    from scrapfly import ScrapeConfig

    headers: dict[str, str] | None = None
    cookie = _cookie_header()
    if cookie:
        headers = {"Cookie": cookie}

    kwargs: dict[str, Any] = {
        "url": url,
        "asp": settings.scrapfly_asp,
        "render_js": settings.scrapfly_render_js,
        "country": settings.scrapfly_country,
        "proxy_pool": settings.scrapfly_proxy_pool,
        "auto_scroll": auto_scroll,
    }
    if headers:
        kwargs["headers"] = headers
    if settings.scrapfly_session.strip():
        kwargs["session"] = settings.scrapfly_session.strip()
    if settings.scrapfly_cost_budget:
        kwargs["cost_budget"] = settings.scrapfly_cost_budget

    return ScrapeConfig(**kwargs)


def _scrape_sync(url: str, *, auto_scroll: bool = False) -> ScrapflyFetchResult:
    from scrapfly import ScrapflyClient, ScrapeApiResponse

    client = ScrapflyClient(key=settings.scrapfly_api_key)
    config = _build_scrape_config(url, auto_scroll=auto_scroll)
    try:
        response: ScrapeApiResponse = client.scrape(scrape_config=config)
    except Exception as exc:
        logger.warning("ScrapFly request failed %s: %s", url, exc)
        return ScrapflyFetchResult(
            url=url,
            html="",
            status_code=0,
            api_cost=0,
            success=False,
            error=str(exc),
        )

    result = response.scrape_result or {}
    content = response.content or result.get("content") or ""
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    status = int(response.status_code or result.get("status_code") or 0)
    try:
        cost = int(response.cost or 0)
    except (TypeError, ValueError):
        cost = 0

    ok = bool(response.scrape_success or response.success) and status < 400 and len(content) > 500
    return ScrapflyFetchResult(
        url=url,
        html=content,
        status_code=status,
        api_cost=cost,
        success=ok,
        error=None if ok else f"http_{status}_or_empty",
    )


async def fetch_page(url: str, *, auto_scroll: bool = False) -> ScrapflyFetchResult:
    if not settings.scrapfly_api_key.strip():
        raise ScrapflyNotConfiguredError(
            "Set SCRAPFLY_API_KEY in .env (https://scrapfly.io/dashboard)"
        )
    return await asyncio.to_thread(_scrape_sync, url, auto_scroll=auto_scroll)
