"""Diversity / dedup pass — prevents source-document flooding.

Applies a configurable penalty multiplier to chunks whose doc_id has
already appeared in the current top-K window, preventing a single highly
relevant document from starving synthesis of breadth.
"""

from __future__ import annotations

from typing import List

from services.common.retrieval.models import ScoredChunk


def diversity_penalty(
    ranked_chunks: List[ScoredChunk],
    top_k: int = 10,
    penalty: float = 0.5,
) -> List[ScoredChunk]:
    """Apply penalty to duplicate source docs in the top-K window.

    For each chunk in the list, if its doc_id has already been seen
    in the first top_k positions, multiply its score by the penalty factor.

    Args:
        ranked_chunks: Chunks sorted by relevance score (highest first).
        top_k: Size of the considered window for source tracking.
        penalty: Multiplier for duplicate source chunks (default 0.5).

    Returns:
        Re-sorted list after applying penalties.
    """
    seen_docs: set[str] = set()

    for i, chunk in enumerate(ranked_chunks):
        if i >= top_k:
            break
        if chunk.doc_id in seen_docs:
            chunk.score *= penalty
        seen_docs.add(chunk.doc_id)

    ranked_chunks.sort(key=lambda c: c.score, reverse=True)
    return ranked_chunks
