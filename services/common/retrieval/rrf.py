"""Reciprocal Rank Fusion — merges two score-incompatible ranked lists.

RRF is rank-based and score-agnostic: score = 1 / (k + rank).
This handles the incompatibility between cosine similarity scores
and BM25 scores without normalisation hacks.
"""

from __future__ import annotations

from typing import List, Tuple


def reciprocal_rank_fusion(
    dense_results: List[Tuple[str, float]],
    sparse_results: List[Tuple[str, float]],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """Merge dense and sparse ranked lists via RRF.

    Args:
        dense_results:  [(chunk_id, cosine_score), ...] in rank order.
        sparse_results: [(chunk_id, sparse_score), ...] in rank order.
        k: Smoothing constant (default 60, standard value).

    Returns:
        [(chunk_id, rrf_score), ...] sorted by RRF score descending.
    """
    rrf_scores: dict[str, float] = {}

    for rank, (chunk_id, _) in enumerate(dense_results, start=1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank)

    for rank, (chunk_id, _) in enumerate(sparse_results, start=1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank)

    merged = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return merged
