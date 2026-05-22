"""Parse The RealReal product HTML into Listing objects."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from backend.app.models import Listing

BASE_URL = "https://www.therealreal.com"

# Matches /products/slug and /products/women/handbags/.../product-slug
PRODUCT_HREF = re.compile(r"/products/", re.I)

_CATEGORY_SEGMENTS = frozenset(
    {"women", "men", "kids", "jewelry", "home", "art", "watches", "beauty"}
)


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] if path else ""


def is_product_path(path: str) -> bool:
    """True for PDP URLs, false for /products/women or search pages."""
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2 or parts[0].lower() != "products":
        return False
    segments = parts[1:]
    if len(segments) == 1:
        seg = segments[0].lower()
        if seg in _CATEGORY_SEGMENTS:
            return False
        return len(segments[0]) >= 8
    return len(segments[-1]) >= 5


def detect_page_issue(html: str, page_title: str = "") -> str | None:
    """Return a short reason when HTML is not a product page."""
    lower = html.lower()
    title_lower = (page_title or "").lower()
    if "press & hold" in lower or "px-captcha" in lower:
        return "captcha"
    if "access to this page has been denied" in lower or "access denied" in title_lower:
        return "blocked"
    if "perimeterx" in lower and ("captcha" in lower or "blocked" in lower):
        return "blocked"
    if "auth_modal" in lower or "sign in to continue" in lower:
        return "login_required"
    return None


def _extract_next_data_raw(html: str, next_data_raw: str | None = None) -> dict[str, Any] | None:
    if next_data_raw:
        try:
            return json.loads(next_data_raw)
        except json.JSONDecodeError:
            pass
    marker = '<script id="__NEXT_DATA__" type="application/json">'
    start = html.find(marker)
    if start >= 0:
        start += len(marker)
        end = html.find("</script>", start)
        if end > start:
            try:
                return json.loads(html[start:end])
            except json.JSONDecodeError:
                pass
    soup = BeautifulSoup(html, "lxml")
    script = soup.find("script", id="__NEXT_DATA__")
    if script and script.string:
        try:
            return json.loads(script.string)
        except json.JSONDecodeError:
            return None
    return None


def _product_from_page_props(next_data: dict[str, Any]) -> dict[str, Any] | None:
    props = next_data.get("props") or {}
    page = props.get("pageProps") or {}
    for key in ("product", "productData", "initialProduct", "listing", "pdp"):
        val = page.get(key)
        if isinstance(val, dict) and (val.get("title") or val.get("name")):
            return val
    return None


def _walk_for_product(node: Any, found: list[dict]) -> None:
    if isinstance(node, dict):
        keys = set(node.keys())
        if {"title", "name"} & keys and ({"id", "slug", "sku"} & keys or "url" in keys):
            title = (node.get("title") or node.get("name") or "").strip()
            if title and title.lower() not in ("the realreal", "sign in"):
                found.append(node)
        for v in node.values():
            _walk_for_product(v, found)
    elif isinstance(node, list):
        for item in node:
            _walk_for_product(item, found)


def _images_from_node(data: dict) -> list[str]:
    images: list[str] = []
    for key in ("images", "image_urls", "photos", "media"):
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
                    u = item.get("url") or item.get("src") or item.get("image_url")
                    if u:
                        images.append(str(u))
    return images[:12]


def _listing_from_payload(data: dict, url: str) -> Listing | None:
    title = (data.get("title") or data.get("name") or "").strip()
    if not title:
        return None
    slug = str(data.get("slug") or data.get("sku") or data.get("id") or _slug_from_url(url))
    slug = slug.replace("/", "-")[:120]
    description = (
        data.get("description")
        or data.get("long_description")
        or data.get("short_description")
        or title
    )
    if isinstance(description, list):
        description = " ".join(str(x) for x in description)
    designer = data.get("designer") or data.get("brand") or data.get("designer_name")
    if isinstance(designer, dict):
        designer = designer.get("name")
    price = data.get("price") or data.get("sale_price") or data.get("list_price") or data.get("final_price")
    if isinstance(price, dict):
        price = price.get("amount") or price.get("value")
    if isinstance(price, str):
        price = price.replace("$", "").replace(",", "").strip()
        try:
            price = float(price)
        except ValueError:
            price = None

    product_url = data.get("url") or data.get("permalink") or url
    if product_url and not str(product_url).startswith("http"):
        product_url = urljoin(BASE_URL, str(product_url))

    return Listing(
        id=slug,
        url=str(product_url),
        title=title[:500],
        description=str(description)[:8000],
        designer=str(designer) if designer else None,
        category=data.get("category") or data.get("taxonomy"),
        price=float(price) if price is not None else None,
        condition=data.get("condition"),
        size=data.get("size"),
        image_urls=_images_from_node(data),
        metadata={"source": "chrome_cdp_html"},
        scraped_at=datetime.now(timezone.utc),
    )


def _listing_from_json_ld(soup: BeautifulSoup, url: str) -> Listing | None:
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") not in ("Product", "ProductGroup") and "Product" not in str(
                item.get("@type", "")
            ):
                continue
            title = (item.get("name") or "").strip()
            if not title:
                continue
            images = item.get("image") or []
            if isinstance(images, str):
                images = [images]
            price = None
            offers = item.get("offers")
            if isinstance(offers, dict):
                price = offers.get("price")
            return Listing(
                id=_slug_from_url(url),
                url=url,
                title=title[:500],
                description=(item.get("description") or title)[:8000],
                image_urls=[str(u) for u in images if u][:12],
                price=float(price) if price is not None else None,
                metadata={"source": "chrome_cdp_jsonld"},
                scraped_at=datetime.now(timezone.utc),
            )
    return None


def parse_product_html(
    html: str,
    url: str,
    *,
    next_data_raw: str | None = None,
    page_title: str = "",
) -> Listing | None:
    issue = detect_page_issue(html, page_title)
    if issue:
        return None

    next_data = _extract_next_data_raw(html, next_data_raw)
    if next_data:
        direct = _product_from_page_props(next_data)
        if direct:
            listing = _listing_from_payload(direct, url)
            if listing:
                return listing
        candidates: list[dict] = []
        _walk_for_product(next_data, candidates)
        best: Listing | None = None
        for data in candidates:
            listing = _listing_from_payload(data, url)
            if listing and (not best or len(listing.image_urls) > len(best.image_urls)):
                best = listing
        if best:
            return best

    soup = BeautifulSoup(html, "lxml")
    json_ld = _listing_from_json_ld(soup, url)
    if json_ld:
        return json_ld

    title = soup.find("meta", property="og:title")
    desc = soup.find("meta", property="og:description")
    title_text = title["content"].strip() if title and title.get("content") else ""
    desc_text = desc["content"].strip() if desc and desc.get("content") else title_text
    if not title_text:
        h1 = soup.find("h1")
        title_text = h1.get_text(strip=True) if h1 else ""
    if not title_text or title_text.lower() in ("the realreal", "sign in"):
        return None

    images: list[str] = []
    for img in soup.select('img[src*="therealreal"], img[src*="product-images"]'):
        src = img.get("src") or img.get("data-src")
        if src and src.startswith("http"):
            images.append(src)
    if not images:
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            images.append(og_img["content"])

    price_val = None
    price_match = re.search(r"\$[\d,]+(?:\.\d{2})?", html[:80000])
    if price_match:
        price_val = float(price_match.group().replace("$", "").replace(",", ""))

    return Listing(
        id=_slug_from_url(url),
        url=url.split("?")[0],
        title=title_text[:500],
        description=(desc_text or title_text)[:8000],
        image_urls=images[:12],
        price=price_val,
        metadata={"source": "chrome_cdp_dom"},
        scraped_at=datetime.now(timezone.utc),
    )


def extract_product_urls_from_html(
    html: str, base_url: str = BASE_URL
) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    seen: set[str] = set()
    for a in soup.select('a[href*="/products/"]'):
        href = (a.get("href") or "").strip()
        if not href or not PRODUCT_HREF.search(href):
            continue
        full = href if href.startswith("http") else urljoin(base_url, href)
        parsed = urlparse(full)
        if not is_product_path(parsed.path):
            continue
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        if normalized in seen:
            continue
        seen.add(normalized)
        urls.append(normalized)
    return urls


def parse_failure_reason(
    html: str,
    url: str,
    *,
    next_data_raw: str | None = None,
    page_title: str = "",
) -> str:
    """Human-readable reason when parse_product_html returns None."""
    issue = detect_page_issue(html, page_title)
    if issue:
        return issue
    if parse_product_html(html, url, next_data_raw=next_data_raw, page_title=page_title):
        return "ok"
    if len(html) < 2000:
        return "empty_html"
    if "__NEXT_DATA__" not in html and "og:title" not in html.lower():
        return "page_not_ready"
    return "no_product_fields"
