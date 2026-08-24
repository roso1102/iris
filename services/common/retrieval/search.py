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

Pipeline #3 — Cross-lingual dual-query: when the query is Latin-script
and the tenant has Devanagari (Hindi) content, Flash-Lite generates a
Hindi variant; original + variant are each searched (dense+sparse) and
all ranked lists are merged via multi_ranked_fusion (4 lists total).
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
from services.common.retrieval.rrf import (
    fuse_rerank_scores,
    multi_ranked_fusion,
    reciprocal_rank_fusion,
)

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


def _needs_cross_lingual(query: str, has_devanagari_corpus: bool) -> bool:
    """Pipeline #3 gate: true when the query would benefit from a Hindi variant.

    Uses ``hindi.needs_cross_lingual_boost`` for the detection logic.
    Called AFTER ``_needs_rewrite`` so pronoun resolution happens first.
    """
    from services.common.retrieval.hindi import needs_cross_lingual_boost

    return needs_cross_lingual_boost(query, has_devanagari_corpus)


class SearchOrchestrator:
    """Orchestrates Standard + Deep search over the chunk store."""

    def __init__(self, store: ChunkStore, provider: ModelProvider) -> None:
        self.store = store
        self.provider = provider
        self._devanagari_cache: Dict[str, bool] = {}

    def _has_devanagari_corpus(self, tenant_id: str) -> bool:
        """Check if tenant has Devanagari content. Cached after first call."""
        if tenant_id not in self._devanagari_cache:
            self._devanagari_cache[tenant_id] = self.store.has_devanagari_content(
                tenant_id
            )
        return self._devanagari_cache[tenant_id]

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

        # ── Phase 1: Rewrite (existing) + Cross-lingual detection ────
        if _needs_rewrite(query, history):
            query = await asyncio.to_thread(
                self.provider.rewrite_query, query, history or []
            )

        has_dev = self._has_devanagari_corpus(tenant_id)
        needs_xling = _needs_cross_lingual(query, has_dev)

        # ── Phase 2: Original embedding + variant generation (parallel) ──
        orig_embed_task = asyncio.to_thread(self.provider.embed_query, query)
        variant_task = (
            asyncio.to_thread(self.provider.generate_cross_lingual_variants, query)
            if needs_xling
            else asyncio.sleep(0, result=[])
        )
        orig_embedding, hindi_variants = await asyncio.gather(
            orig_embed_task, variant_task
        )
        hindi_variants = hindi_variants or []

        # ── Phase 3: Embed Hindi variants (parallel) ─────────────────
        if hindi_variants:
            variant_embeddings = list(
                await asyncio.gather(
                    *[
                        asyncio.to_thread(self.provider.embed_query, v)
                        for v in hindi_variants
                    ]
                )
            )
        else:
            variant_embeddings = []

        # ── Phase 4: All store searches in parallel ──────────────────
        search_tasks = [
            asyncio.to_thread(
                self.store.search_dense,
                orig_embedding,
                tenant_id,
                doc_ids,
                limit=top_k * 3,
            ),
            asyncio.to_thread(
                self.store.search_sparse,
                query,
                tenant_id,
                doc_ids,
                limit=top_k * 3,
            ),
        ]
        for variant, v_emb in zip(hindi_variants, variant_embeddings):
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_dense,
                    v_emb,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 3,
                )
            )
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_sparse,
                    variant,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 3,
                )
            )

        all_ranked = list(await asyncio.gather(*search_tasks))

        # ── Phase 5: Multi-list RRF or standard 2-list RRF ──────────
        if len(all_ranked) > 2:
            fused = multi_ranked_fusion(all_ranked)
        else:
            fused = reciprocal_rank_fusion(all_ranked[0], all_ranked[1])

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
                "cross_lingual": bool(hindi_variants),
                "hindi_variants_count": len(hindi_variants),
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

        # ── Cross-lingual on the REWRITTEN query ─────────────────────
        has_dev = self._has_devanagari_corpus(tenant_id)
        needs_xling = _needs_cross_lingual(rewritten, has_dev)

        if needs_xling:
            hindi_variants = await asyncio.to_thread(
                self.provider.generate_cross_lingual_variants, rewritten
            )
        else:
            hindi_variants = []
        hindi_variants = hindi_variants or []

        # ── HyDE for original query (unchanged) ──────────────────────
        try:
            hyde = await asyncio.to_thread(self.provider.generate_hyde, rewritten)
        except Exception:
            hyde = rewritten

        hyde_embedding = await asyncio.to_thread(self.provider.embed, hyde)

        # ── Embed Hindi variants ─────────────────────────────────────
        if hindi_variants:
            variant_embeddings = list(
                await asyncio.gather(
                    *[
                        asyncio.to_thread(self.provider.embed_query, v)
                        for v in hindi_variants
                    ]
                )
            )
        else:
            variant_embeddings = []

        # ── All store searches in parallel ───────────────────────────
        search_tasks = [
            asyncio.to_thread(
                self.store.search_dense,
                hyde_embedding,
                tenant_id,
                doc_ids,
                limit=top_k * 3,
            ),
            asyncio.to_thread(
                self.store.search_sparse,
                rewritten,
                tenant_id,
                doc_ids,
                limit=top_k * 3,
            ),
        ]
        for variant, v_emb in zip(hindi_variants, variant_embeddings):
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_dense,
                    v_emb,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 3,
                )
            )
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_sparse,
                    variant,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 3,
                )
            )

        all_ranked = list(await asyncio.gather(*search_tasks))

        if len(all_ranked) > 2:
            fused = multi_ranked_fusion(all_ranked)
        else:
            fused = reciprocal_rank_fusion(all_ranked[0], all_ranked[1])

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
                "cross_lingual": bool(hindi_variants),
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
