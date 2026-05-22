import time

from backend.app.indexing.manager import IndexManager
from backend.app.models import SearchResponse, SearchResult


class SearchService:
    def __init__(self, index_manager: IndexManager) -> None:
        self.index_manager = index_manager

    def search(self, query: str, limit: int | None = None) -> SearchResponse:
        start = time.perf_counter()
        self.index_manager.ensure_ready()
        hits = self.index_manager.hybrid_search(query, top_k=limit)
        results = [
            SearchResult(
                listing=listing,
                score=round(score, 6),
                rank=idx + 1,
                match_reasons=reasons,
            )
            for idx, (listing, score, reasons) in enumerate(hits)
        ]
        took_ms = (time.perf_counter() - start) * 1000
        return SearchResponse(
            query=query,
            total=len(results),
            results=results,
            took_ms=round(took_ms, 2),
        )
