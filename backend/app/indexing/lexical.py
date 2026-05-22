"""BM25 lexical index over listing title + description + metadata."""

from __future__ import annotations

import re
from typing import Sequence

import numpy as np
from rank_bm25 import BM25Okapi

from backend.app.models import Listing

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def document_text(listing: Listing) -> str:
    parts = [
        listing.title,
        listing.description,
        listing.designer or "",
        listing.category or "",
        listing.condition or "",
        listing.size or "",
    ]
    for key, value in (listing.metadata or {}).items():
        if isinstance(value, str):
            parts.append(value)
    return " ".join(p for p in parts if p)


class LexicalIndex:
    def __init__(self) -> None:
        self._listings: list[Listing] = []
        self._bm25: BM25Okapi | None = None
        self._corpus_tokens: list[list[str]] = []

    def build(self, listings: Sequence[Listing]) -> None:
        self._listings = list(listings)
        self._corpus_tokens = [tokenize(document_text(l)) for l in self._listings]
        self._bm25 = BM25Okapi(self._corpus_tokens) if self._corpus_tokens else None

    def search(self, query: str, top_k: int = 50) -> list[tuple[str, float]]:
        if not self._bm25 or not self._listings:
            return []
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = np.array(self._bm25.get_scores(tokens), dtype=np.float32)
        if scores.max() <= 0:
            return []
        # Min-max normalize for fusion
        smin, smax = float(scores.min()), float(scores.max())
        norm = (scores - smin) / (smax - smin + 1e-9)
        order = np.argsort(-norm)[:top_k]
        return [(self._listings[i].id, float(norm[i])) for i in order if norm[i] > 0]
