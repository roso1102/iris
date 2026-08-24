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


def fuse_rerank_scores(
    hybrid_scores: List[float],
    rerank_scores: List[float],
    blend: float,
    k: int = 60,
) -> List[float]:
    """Fuse hybrid RRF scores with cross-encoder reranker scores, rank-based.

    The reranker's (possibly unbounded) scores are converted to RANKS first;
    each chunk's fused score is `(1-blend)*hybrid + 2*blend/(k+rank)`. Rank
    bases are scale-free — a direct `(1-b)*rrf + b*rerank` blend mixes RRF's
    ~0.001-0.03 range with arbitrary ranker scores, which made any nonzero
    blend effectively "pure reranker" (Phase 12.1 fix).

    Weight semantics: blend is the fraction of total weight on the ranker —
    0.0 preserves the hybrid order exactly, 1.0 is pure ranker order (ties
    broken by input position), 0.5 puts the ranker on par with the combined
    dense+sparse signal.
    """
    n = min(len(hybrid_scores), len(rerank_scores))
    out = list(hybrid_scores)
    if n == 0:
        return out
    blend = max(0.0, min(1.0, blend))
    if blend == 0.0:
        return out
    # Rank passages by rerank score descending; ties keep earlier position.
    order = sorted(range(n), key=lambda i: (rerank_scores[i], -i), reverse=True)
    # Bump sized to the FULL hybrid list: passages beyond the reranker's
    # returned scores keep a zero bump (hybrid-only) instead of being dropped.
    bump = [0.0] * len(hybrid_scores)
    for rank_pos, idx in enumerate(order, start=1):
        bump[idx] = (2.0 * blend) / (k + rank_pos)
    return [
        (1.0 - blend) * h + b for h, b in zip(hybrid_scores, bump)
    ]


def multi_ranked_fusion(
    ranked_lists: List[List[Tuple[str, float]]],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """Generalized RRF merging N ranked lists.

    Each list is [(chunk_id, score), ...] in rank order. Score values
    are ignored — only rank position matters (standard RRF semantics).
    Empty lists are silently skipped.

    Used by cross-lingual dual-query to merge original + Hindi-variant
    search results (typically 4 lists: dense_orig, sparse_orig,
    dense_hindi, sparse_hindi).
    """
    rrf_scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (chunk_id, _) in enumerate(ranked, start=1):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
