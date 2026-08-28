"""Diversity / dedup pass — prevents near-duplicate flooding.

Applies a configurable penalty multiplier to chunks whose text content
has >80% token overlap with an already-seen chunk. This preserves
diverse chunks from the same page (e.g., Forms 3, 4, 5) while killing
near-duplicate noise from overlapping retrieval windows.

Doc-scoped searches (doc_ids filter set, i.e. single-document sessions)
skip the pass entirely: every result is same-doc by construction and the
penalty only distorts intra-document ranking.
"""

from __future__ import annotations

from typing import List

from services.common.retrieval.models import ScoredChunk


def _token_set(text: str) -> set[str]:
    """Extract lowercased word tokens from text."""
    return set(text.lower().split())


def _token_overlap_ratio(a: set[str], b: set[str]) -> float:
    """Jaccard-ish overlap: |intersection| / min(|a|, |b|)."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def diversity_penalty(
    ranked_chunks: List[ScoredChunk],
    top_k: int = 10,
    penalty: float = 0.5,
    overlap_threshold: float = 0.8,
) -> List[ScoredChunk]:
    """Apply penalty to near-duplicate chunks in the top-K window.

    A chunk is penalized if its token set has >overlap_threshold overlap
    with any previously seen chunk in the top_k window.

    Args:
        ranked_chunks: Chunks sorted by relevance score (highest first).
        top_k: Size of the considered window for source tracking.
        penalty: Multiplier for duplicate source chunks (default 0.5).
        overlap_threshold: Token overlap ratio above which chunks are
            considered duplicates (default 0.8).

    Returns:
        Re-sorted list after applying penalties.
    """
    seen_tokens: list[set[str]] = []

    for i, chunk in enumerate(ranked_chunks):
        if i >= top_k:
            break
        chunk_tokens = _token_set(chunk.text)
        for seen in seen_tokens:
            if _token_overlap_ratio(chunk_tokens, seen) > overlap_threshold:
                chunk.score *= penalty
                break
        seen_tokens.append(chunk_tokens)

    ranked_chunks.sort(key=lambda c: c.score, reverse=True)
    return ranked_chunks
