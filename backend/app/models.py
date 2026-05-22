from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Listing(BaseModel):
    id: str
    url: str
    title: str
    description: str
    designer: str | None = None
    category: str | None = None
    price: float | None = None
    currency: str = "USD"
    condition: str | None = None
    size: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    scraped_at: datetime | None = None


class SearchResult(BaseModel):
    listing: Listing
    score: float
    rank: int
    match_reasons: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResult]
    took_ms: float


class ScrapeStatus(BaseModel):
    status: str
    outcome: str
    message: str
    new_listings: int = 0
    total_listings: int = 0
    used_seed_fallback: bool = False
    blocked: bool = False
    block_type: str | None = None
    pages_scraped: int = 0
    products_found: int = 0
    blocked_at_url: str | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)
