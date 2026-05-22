"""Text and multimodal (CLIP) semantic indexes."""

from __future__ import annotations

import io
import logging
from typing import Sequence

import numpy as np
import httpx
from PIL import Image

from backend.app.config import settings
from backend.app.models import Listing

logger = logging.getLogger(__name__)


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / (norms + 1e-9)


class SemanticIndex:
    def __init__(self) -> None:
        self._listings: list[Listing] = []
        self._text_model = None
        self._clip_model = None
        self._text_embeddings: np.ndarray | None = None
        self._image_embeddings: np.ndarray | None = None

    def _load_text_model(self):
        if self._text_model is None:
            from sentence_transformers import SentenceTransformer

            self._text_model = SentenceTransformer(settings.text_embedding_model)
        return self._text_model

    def _load_clip_model(self):
        if self._clip_model is None:
            from sentence_transformers import SentenceTransformer

            self._clip_model = SentenceTransformer(settings.clip_model)
        return self._clip_model

    @staticmethod
    def listing_text(listing: Listing) -> str:
        return " | ".join(
            filter(
                None,
                [
                    listing.title,
                    listing.description,
                    listing.designer,
                    listing.category,
                    listing.condition,
                    listing.size,
                ],
            )
        )

    def _fetch_image(self, url: str) -> Image.Image | None:
        try:
            with httpx.Client(timeout=12.0, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return Image.open(io.BytesIO(resp.content)).convert("RGB")
        except Exception as exc:
            logger.debug("Image fetch failed %s: %s", url, exc)
            return None

    def build(self, listings: Sequence[Listing]) -> None:
        self._listings = list(listings)
        if not self._listings:
            self._text_embeddings = None
            self._image_embeddings = None
            return

        texts = [self.listing_text(l) for l in self._listings]
        text_model = self._load_text_model()
        text_emb = text_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        self._text_embeddings = _l2_normalize(text_emb.astype(np.float32))

        clip_model = self._load_clip_model()
        image_vectors: list[np.ndarray] = []
        for listing in self._listings:
            vec = None
            for url in listing.image_urls[:3]:
                img = self._fetch_image(url)
                if img is None:
                    continue
                emb = clip_model.encode(img, convert_to_numpy=True)
                vec = emb
                break
            if vec is None:
                # Text-to-image space fallback using listing text
                vec = clip_model.encode(self.listing_text(listing), convert_to_numpy=True)
            image_vectors.append(vec.astype(np.float32))
        self._image_embeddings = _l2_normalize(np.vstack(image_vectors))

    def _search_embeddings(
        self, query: str, matrix: np.ndarray | None, use_clip: bool
    ) -> list[tuple[str, float]]:
        if matrix is None or not self._listings:
            return []
        if use_clip:
            model = self._load_clip_model()
        else:
            model = self._load_text_model()
        q = model.encode(query, convert_to_numpy=True).astype(np.float32)
        q = q / (np.linalg.norm(q) + 1e-9)
        scores = matrix @ q
        order = np.argsort(-scores)[: settings.search_top_k * 2]
        smin, smax = float(scores.min()), float(scores.max())
        norm = (scores - smin) / (smax - smin + 1e-9)
        return [
            (self._listings[i].id, float(norm[i]))
            for i in order
            if norm[i] > 0.01
        ]

    def search_text(self, query: str, top_k: int = 50) -> list[tuple[str, float]]:
        results = self._search_embeddings(query, self._text_embeddings, use_clip=False)
        return results[:top_k]

    def search_image(self, query: str, top_k: int = 50) -> list[tuple[str, float]]:
        # CLIP aligns text queries with image embeddings
        results = self._search_embeddings(query, self._image_embeddings, use_clip=True)
        return results[:top_k]
