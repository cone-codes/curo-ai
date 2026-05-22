"""Parse The RealReal product HTML into Listing objects."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from backend.app.models import Listing

PRODUCT_PATH = re.compile(r"/products/([a-z0-9-]+)", re.I)


def _slug_from_url(url: str) -> str:
    match = PRODUCT_PATH.search(url)
    return match.group(1) if match else urlparse(url).path.rstrip("/").split("/")[-1]


def _extract_next_data(soup: BeautifulSoup) -> dict[str, Any] | None:
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return None
    try:
        return json.loads(script.string)
    except json.JSONDecodeError:
        return None


def _walk_for_product(node: Any, found: list[dict]) -> None:
    if isinstance(node, dict):
        keys = set(node.keys())
        if {"title", "name"} & keys and ({"id", "slug"} & keys or "url" in keys):
            title = (node.get("title") or node.get("name") or "").strip()
            if title:
                found.append(node)
        for v in node.values():
            _walk_for_product(v, found)
    elif isinstance(node, list):
        for item in node:
            _walk_for_product(item, found)


def _images_from_node(data: dict) -> list[str]:
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
                    u = item.get("url") or item.get("src")
                    if u:
                        images.append(str(u))
    return images[:12]


def _listing_from_payload(data: dict, url: str) -> Listing | None:
    title = (data.get("title") or data.get("name") or "").strip()
    if not title:
        return None
    slug = str(data.get("slug") or data.get("id") or _slug_from_url(url))
    description = data.get("description") or data.get("long_description") or title
    if isinstance(description, list):
        description = " ".join(str(x) for x in description)
    designer = data.get("designer") or data.get("brand")
    if isinstance(designer, dict):
        designer = designer.get("name")
    price = data.get("price") or data.get("sale_price")
    if isinstance(price, dict):
        price = price.get("amount") or price.get("value")

    return Listing(
        id=slug,
        url=url if url.startswith("http") else f"https://www.therealreal.com/products/{slug}",
        title=title[:500],
        description=str(description)[:8000],
        designer=str(designer) if designer else None,
        category=data.get("category"),
        price=float(price) if price is not None else None,
        condition=data.get("condition"),
        size=data.get("size"),
        image_urls=_images_from_node(data),
        metadata={"source": "chrome_cdp_html"},
        scraped_at=datetime.now(timezone.utc),
    )


def parse_product_html(html: str, url: str) -> Listing | None:
    soup = BeautifulSoup(html, "lxml")
    next_data = _extract_next_data(soup)
    if next_data:
        candidates: list[dict] = []
        _walk_for_product(next_data, candidates)
        for data in candidates:
            listing = _listing_from_payload(data, url)
            if listing:
                return listing

    title = soup.find("meta", property="og:title")
    desc = soup.find("meta", property="og:description")
    title_text = title["content"].strip() if title and title.get("content") else ""
    desc_text = desc["content"].strip() if desc and desc.get("content") else title_text
    if not title_text:
        h1 = soup.find("h1")
        title_text = h1.get_text(strip=True) if h1 else ""
    if not title_text:
        return None

    images: list[str] = []
    for img in soup.select('img[src*="therealreal"], img[src*="product"]'):
        src = img.get("src") or img.get("data-src")
        if src and src.startswith("http"):
            images.append(src)
    if not images:
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            images.append(og_img["content"])

    price_val = None
    price_match = re.search(r"\$[\d,]+(?:\.\d{2})?", html[:50000])
    if price_match:
        price_val = float(price_match.group().replace("$", "").replace(",", ""))

    return Listing(
        id=_slug_from_url(url),
        url=url,
        title=title_text[:500],
        description=(desc_text or title_text)[:8000],
        image_urls=images[:12],
        price=price_val,
        metadata={"source": "chrome_cdp_dom"},
        scraped_at=datetime.now(timezone.utc),
    )


def extract_product_urls_from_html(html: str, base_url: str = "https://www.therealreal.com") -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    seen: set[str] = set()
    for a in soup.select('a[href*="/products/"]'):
        href = a.get("href") or ""
        if not PRODUCT_PATH.search(href):
            continue
        full = href if href.startswith("http") else f"{base_url.rstrip('/')}{href}"
        slug = _slug_from_url(full)
        if slug in seen:
            continue
        seen.add(slug)
        urls.append(full.split("?")[0])
    return urls
