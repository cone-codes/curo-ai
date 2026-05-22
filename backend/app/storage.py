import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from backend.app.config import LISTINGS_DB
from backend.app.models import Listing


def _ensure_db() -> None:
    LISTINGS_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(LISTINGS_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                designer TEXT,
                category TEXT,
                price REAL,
                currency TEXT DEFAULT 'USD',
                condition TEXT,
                size TEXT,
                image_urls TEXT NOT NULL,
                metadata TEXT,
                scraped_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    _ensure_db()
    conn = sqlite3.connect(LISTINGS_DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def row_to_listing(row: sqlite3.Row) -> Listing:
    return Listing(
        id=row["id"],
        url=row["url"],
        title=row["title"],
        description=row["description"],
        designer=row["designer"],
        category=row["category"],
        price=row["price"],
        currency=row["currency"] or "USD",
        condition=row["condition"],
        size=row["size"],
        image_urls=json.loads(row["image_urls"]),
        metadata=json.loads(row["metadata"] or "{}"),
        scraped_at=datetime.fromisoformat(row["scraped_at"]),
    )


def upsert_listing(listing: Listing) -> None:
    now = listing.scraped_at or datetime.now(timezone.utc)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO listings (
                id, url, title, description, designer, category, price, currency,
                condition, size, image_urls, metadata, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                url=excluded.url,
                title=excluded.title,
                description=excluded.description,
                designer=excluded.designer,
                category=excluded.category,
                price=excluded.price,
                currency=excluded.currency,
                condition=excluded.condition,
                size=excluded.size,
                image_urls=excluded.image_urls,
                metadata=excluded.metadata,
                scraped_at=excluded.scraped_at
            """,
            (
                listing.id,
                listing.url,
                listing.title,
                listing.description,
                listing.designer,
                listing.category,
                listing.price,
                listing.currency,
                listing.condition,
                listing.size,
                json.dumps(listing.image_urls),
                json.dumps(listing.metadata),
                now.isoformat(),
            ),
        )
        conn.commit()


def upsert_many(listings: list[Listing]) -> int:
    for listing in listings:
        upsert_listing(listing)
    return len(listings)


def get_all_listings() -> list[Listing]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM listings ORDER BY scraped_at DESC").fetchall()
    return [row_to_listing(r) for r in rows]


def count_listings() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM listings").fetchone()
    return int(row["c"])


def existing_ids() -> set[str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT id FROM listings").fetchall()
    return {r["id"] for r in rows}


def load_seed_from_file(path: Path) -> list[Listing]:
    raw = json.loads(path.read_text())
    listings: list[Listing] = []
    for item in raw:
        listings.append(Listing.model_validate(item))
    return listings
