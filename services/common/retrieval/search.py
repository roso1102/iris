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
import time
from typing import Dict, List, Optional, Tuple

from services.common.ingestion.models import Chunk
from services.common.ingestion.store import ChunkStore
from services.common.models.base import ModelProvider
from services.common.retrieval.diversity import diversity_penalty
from services.common.retrieval.models import ScoredChunk
from services.common.retrieval.rrf import reciprocal_rank_fusion

logger = logging.getLogger(__name__)


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
    ) -> List[ScoredChunk]:
        """Task 2.4a: Standard non-blocking async search path."""
        t0 = time.time()
        embedding = await asyncio.to_thread(self.provider.embed, query)

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
        diversified = diversity_penalty(scored, top_k=top_k)
        results = diversified[:top_k]

        latency = round((time.time() - t0) * 1000, 2)
        logger.info(
            "search_completed",
            extra={
                "query": query[:100],
                "mode": "standard",
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
        diversified = diversity_penalty(scored, top_k=top_k)
        results = diversified[:top_k]

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
