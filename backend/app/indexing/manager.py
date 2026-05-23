import logging
import pickle
from pathlib import Path

from backend.app.config import INDEX_DIR
from backend.app.indexing.hybrid import reciprocal_rank_fusion
from backend.app.indexing.lexical import LexicalIndex
from backend.app.indexing.semantic import SemanticIndex
from backend.app.models import Listing
from backend.app.storage import get_all_listings

logger = logging.getLogger(__name__)

INDEX_META = INDEX_DIR / "meta.pkl"


class IndexManager:
    def __init__(self) -> None:
        self.lexical = LexicalIndex()
        self.semantic = SemanticIndex()
        self._listings_by_id: dict[str, Listing] = {}
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready and bool(self._listings_by_id)

    def build(self, listings: list[Listing] | None = None) -> None:
        listings = listings if listings is not None else get_all_listings()
        self._listings_by_id = {l.id: l for l in listings}
        logger.info("Building indexes for %d listings", len(listings))
        self.lexical.build(listings)
        self.semantic.build(listings)
        self._persist_meta()
        self._ready = True

    def _persist_meta(self) -> None:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        with INDEX_META.open("wb") as f:
            pickle.dump({"count": len(self._listings_by_id)}, f)

    def ensure_ready(self) -> None:
        if not self._ready:
            self.build()

    def hybrid_search(self, query: str, top_k: int | None = None) -> list[tuple[Listing, float, list[str]]]:
        from backend.app.config import settings

        self.ensure_ready()
        top_k = top_k or settings.search_top_k
        limit = top_k * 3

        lexical_hits = self.lexical.search(query, top_k=limit)
        text_hits = self.semantic.search_text(query, top_k=limit)
        image_hits = self.semantic.search_image(query, top_k=limit)

        fused = reciprocal_rank_fusion(
            [
                (lexical_hits, settings.lexical_weight),
                (text_hits, settings.semantic_text_weight),
                (image_hits, settings.semantic_image_weight),
            ]
        )

        results: list[tuple[Listing, float, list[str]]] = []
        lexical_ids = {d for d, _ in lexical_hits[:20]}
        text_ids = {d for d, _ in text_hits[:20]}
        image_ids = {d for d, _ in image_hits[:20]}

        for doc_id, score in fused[:top_k]:
            listing = self._listings_by_id.get(doc_id)
            if not listing:
                continue
            reasons: list[str] = []
            if doc_id in lexical_ids:
                reasons.append("lexical_bm25")
            if doc_id in text_ids:
                reasons.append("semantic_text")
            if doc_id in image_ids:
                reasons.append("semantic_image")
            results.append((listing, score, reasons))

        return results
