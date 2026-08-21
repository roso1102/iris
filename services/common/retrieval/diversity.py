"""Diversity / dedup pass — prevents single-page flooding.

Applies a configurable penalty multiplier to chunks whose (doc_id, page_number)
has already appeared in the current top-K window. The page-level key (Stage 1b)
keeps same-document DIFFERENT-page chunks unpenalized — that multi-page
evidence is exactly what Page-Recall@K measures — while still stopping one
long page (several 256-token chunks) from starving the rest of the window.

Doc-scoped searches (doc_ids filter set, i.e. single-document sessions)
skip the pass entirely: every result is same-doc by construction and the
penalty only distorts intra-document ranking.
"""

from __future__ import annotations

from typing import List

from services.common.retrieval.models import ScoredChunk


def diversity_penalty(
    ranked_chunks: List[ScoredChunk],
    top_k: int = 10,
    penalty: float = 0.5,
) -> List[ScoredChunk]:
    """Apply penalty to duplicate (doc, page) sources in the top-K window.

    For each chunk in the list, if its (doc_id, page_number) has already been
    seen in the first top_k positions, multiply its score by the penalty
    factor.

    Args:
        ranked_chunks: Chunks sorted by relevance score (highest first).
        top_k: Size of the considered window for source tracking.
        penalty: Multiplier for duplicate source chunks (default 0.5).

    Returns:
        Re-sorted list after applying penalties.
    """
    seen: set[tuple[str, int]] = set()

    for i, chunk in enumerate(ranked_chunks):
        if i >= top_k:
            break
        key = (chunk.doc_id, chunk.page_number)
        if key in seen:
            chunk.score *= penalty
        seen.add(key)

    ranked_chunks.sort(key=lambda c: c.score, reverse=True)
    return ranked_chunks
