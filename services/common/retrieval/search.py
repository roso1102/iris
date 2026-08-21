"""Phase 2.0 Search Orchestrator — Standard + Deep search paths.

Standard Mode (Task 2.4a):
  1. embed(query)
  2. dense + sparse search in parallel
  3. RRF fusion
  4. Diversity / dedup pass
  5. Return top-K

Deep Search Mode (Task 2.4b):
  1. rewrite_query(query, history) → self-contained query
  2. generate_hyde(rewritten) → hypothetical answer
  3. embed(hyde) → dense vector
  4. dense + sparse search (dense uses hyde embedding, sparse uses rewritten text)
  5. RRF fusion
  6. Diversity / dedup pass
  7. Return top-K
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Tuple

from services.common.ingestion.models import Chunk
from services.common.ingestion.store import ChunkStore
from services.common.models.base import ModelProvider
from services.common.retrieval.diversity import diversity_penalty
from services.common.retrieval.models import ScoredChunk
from services.common.retrieval.rrf import fuse_rerank_scores, reciprocal_rank_fusion

logger = logging.getLogger(__name__)

# Phase 6.5 pronoun/dependency heuristic gate: if the raw query contains none of
# these ambiguous indicators, skip the (costly) SLM rewriter entirely.
_AMBIGUOUS_REFERENCE_RE = re.compile(
    r"\b(it|this|that|these|those|former|latter|above|previous|the\s+(?:former|latter))\b",
    re.IGNORECASE,
)


def _needs_rewrite(query: str, history: Optional[List[dict]]) -> bool:
    """Phase 6.5 gate: true only when there is history AND an ambiguous reference.

    Standalone queries without pronouns bypass the rewriter (0ms, 0 cost),
    preserving the fast standard path.
    """
    if not history:
        return False
    return bool(_AMBIGUOUS_REFERENCE_RE.search(query))


class SearchOrchestrator:
    """Orchestrates Standard + Deep search over the chunk store."""

    def __init__(self, store: ChunkStore, provider: ModelProvider) -> None:
        self.store = store
        self.provider = provider

    async def standard_search(
        self,
        query: str,
        tenant_id: str,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 10,
        rerank_blend: Optional[float] = None,
        history: Optional[List[dict]] = None,
    ) -> List[ScoredChunk]:
        """Task 2.4a: Standard non-blocking async search path.

        `rerank_blend` (Phase 12.1): when set (0.0..1.0), the top candidates are
        cross-encoder reranked and fused with the original RRF scores via
        weighted rank fusion (`fuse_rerank_scores` — scale-free, unlike a raw
        score blend). Used by the eval harness to sweep the blend ratio. None
        disables reranking (MVP behaviour).

        `history` (Phase 6.0a): when follow-ups contain an ambiguous reference
        (it/this/that/...), the SLM rewriter resolves them into a self-contained
        query before retrieval. Gated by `_needs_rewrite` (Phase 6.5).
        """
        t0 = time.time()

        if _needs_rewrite(query, history):
            query = await asyncio.to_thread(
                self.provider.rewrite_query, query, history or []
            )

        # Query-side embedding uses task_type=RETRIEVAL_QUERY (Stage 1a):
        # text-embedding-004 is asymmetric and doc-task queries rank worse.
        embedding = await asyncio.to_thread(self.provider.embed_query, query)

        dense_future = asyncio.to_thread(
            self.store.search_dense, embedding, tenant_id, doc_ids, limit=top_k * 3
        )
        sparse_future = asyncio.to_thread(
            self.store.search_sparse, query, tenant_id, doc_ids, limit=top_k * 3
        )
        dense, sparse = await asyncio.gather(dense_future, sparse_future)

        fused = reciprocal_rank_fusion(dense, sparse)

        scored = await asyncio.to_thread(
            self._resolve_chunks, fused, top_k * 3, tenant_id
        )

        # Diversity BEFORE the rerank leg (Stage 1b): page-level dedup only,
        # skipped for doc-scoped sessions, so the precision stage (reranker)
        # always has the final say on ordering.
        if not doc_ids:
            scored = diversity_penalty(scored, top_k=top_k)

        if rerank_blend is not None and scored:
            scores = await asyncio.to_thread(
                self.provider.rerank, query, [c.text for c in scored]
            )
            blended = fuse_rerank_scores(
                [c.score for c in scored], scores, rerank_blend
            )
            for chunk, blended_score in zip(scored, blended):
                chunk.score = blended_score
            scored.sort(key=lambda c: c.score, reverse=True)

        results = scored[:top_k]

        latency = round((time.time() - t0) * 1000, 2)
        logger.info(
            "search_completed",
            extra={
                "query": query[:100],
                "mode": "standard",
                "rerank_blend": rerank_blend,
                "latency_ms": latency,
                "top_score": results[0].score if results else 0.0,
                "tenant_id": tenant_id,
                "num_results": len(results),
            },
        )
        return results

    async def deep_search(
        self,
        query: str,
        tenant_id: str,
        history: Optional[List[dict]] = None,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> List[ScoredChunk]:
        """Deep Search with async SLM rewrite, HyDE generation, and fusion."""
        t0 = time.time()

        rewritten = await asyncio.to_thread(
            self.provider.rewrite_query, query, history or []
        )
        try:
            hyde = await asyncio.to_thread(
                self.provider.generate_hyde, rewritten
            )
        except Exception:
            hyde = rewritten

        embedding = await asyncio.to_thread(self.provider.embed, hyde)

        dense_future = asyncio.to_thread(
            self.store.search_dense, embedding, tenant_id, doc_ids, limit=top_k * 3
        )
        sparse_future = asyncio.to_thread(
            self.store.search_sparse, rewritten, tenant_id, doc_ids, limit=top_k * 3
        )
        dense, sparse = await asyncio.gather(dense_future, sparse_future)

        fused = reciprocal_rank_fusion(dense, sparse)

        scored = await asyncio.to_thread(
            self._resolve_chunks, fused, top_k * 3, tenant_id
        )
        if not doc_ids:
            scored = diversity_penalty(scored, top_k=top_k)
        results = scored[:top_k]

        latency = round((time.time() - t0) * 1000, 2)
        logger.info(
            "search_completed",
            extra={
                "query": query[:100],
                "mode": "deep",
                "latency_ms": latency,
                "top_score": results[0].score if results else 0.0,
                "tenant_id": tenant_id,
                "num_results": len(results),
            },
        )
        return results

    def _resolve_chunks(
        self, fused: List[Tuple[str, float]], limit: int, tenant_id: str
    ) -> List[ScoredChunk]:
        """Resolve RRF-fused (chunk_id, score) into full ScoredChunk objects."""
        fused_ids = [cid for cid, _ in fused[:limit]]
        if not fused_ids:
            return []

        chunks = self.store.get_by_ids(fused_ids, tenant_id)
        chunk_map: Dict[str, Chunk] = {c.id: c for c in chunks}

        results: List[ScoredChunk] = []
        for chunk_id, rrf_score in fused:
            chunk = chunk_map.get(chunk_id)
            if chunk is None:
                continue
            results.append(
                ScoredChunk(
                    chunk_id=chunk.id,
                    doc_id=chunk.doc_id,
                    tenant_id=chunk.tenant_id,
                    session_id=chunk.session_id,
                    text=chunk.text,
                    bbox=list(chunk.bbox),
                    page_number=chunk.page_number,
                    element_type=chunk.element_type.value,
                    source=chunk.source.value,
                    score=rrf_score,
                    metadata=dict(chunk.metadata or {}),
                )
            )
        return results
