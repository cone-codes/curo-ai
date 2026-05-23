"""Reciprocal Rank Fusion (RRF) across lexical and semantic channels."""

from __future__ import annotations

from collections import defaultdict

from backend.app.config import settings


def reciprocal_rank_fusion(
    ranked_lists: list[tuple[list[tuple[str, float]], float]],
    k: int | None = None,
) -> list[tuple[str, float]]:
    """
    ranked_lists: [( [(doc_id, score), ...], channel_weight ), ...]
    Returns fused (doc_id, score) sorted by descending RRF score.
    """
    k = k or settings.rrf_k
    fused: dict[str, float] = defaultdict(float)

    for rankings, weight in ranked_lists:
        for rank, (doc_id, _score) in enumerate(rankings, start=1):
            fused[doc_id] += weight * (1.0 / (k + rank))

    return sorted(fused.items(), key=lambda x: -x[1])
