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

# Acronym ↔ expansion synonyms from the golden corpus (zero LLM cost).
_SYNONYM_MAP: Dict[str, List[str]] = {
    "sdg": ["sustainable development goals"],
    "csr": ["corporate social responsibility"],
    "gdp": ["gross domestic product"],
    "fdi": ["foreign direct investment"],
    "nda": ["national democratic alliance"],
    "upa": ["united progressive alliance"],
    "gva": ["gross value added"],
    "cagr": ["compound annual growth rate"],
    "roe": ["return on equity"],
    "nim": ["net interest margin"],
    "npj": ["non-performing assets"],
    "npa": ["non-performing assets"],
    "rmsa": ["rashtriya madhyamik shiksha abhiyan"],
    "ssa": ["sarva shiksha abhiyan"],
    "pmjay": ["pradhan mantri jan arogya yojana"],
    "mgnrega": ["mahatma gandhi national rural employment guarantee act"],
    "rera": ["real estate regulatory authority"],
    "sebi": ["securities and exchange board of india"],
    "rbi": ["reserve bank of india"],
    "gst": ["goods and services tax"],
    "cpcb": ["central pollution control board"],
    "ngt": ["national green tribunal"],
    "cag": ["comptroller and auditor general"],
    "epfo": ["employees provident fund organisation"],
    "ed": ["enforcement directorate"],
    "cbi": ["central bureau of investigation"],
    "nclt": ["national company law tribunal"],
    "nclat": ["national company law appellate tribunal"],
    "tds": ["tax deducted at source"],
    "pan": ["permanent account number"],
    "gstn": ["goods and services tax network"],
    "digi": ["digital india"],
    "ayushman": ["pradhan mantri jan arogya yojana"],
}

_SPECIFIC_QUERY_RE = re.compile(
    r"(?:\b(?:section|clause|article|schedule|annexure|chapter|part|rule|regulation|page|table|figure|paragraph|act)\s+\d"
    r"|\b(?:20\d{2}|19\d{2})\b"  # years
    r"|\b(?:annual report|budget|gazette|notification|circular)\b)",  # document names
    re.IGNORECASE,
)


def _expand_synonyms(query: str) -> str:
    """Expand acronyms in the query with their full forms for BM25."""
    words = query.split()
    expanded = []
    for word in words:
        lower = word.lower().strip(".,;:!?")
        if lower in _SYNONYM_MAP:
            expanded.append(word)
            expanded.extend(_SYNONYM_MAP[lower])
        else:
            expanded.append(word)
    return " ".join(expanded)


def _needs_rewrite(query: str, history: Optional[List[dict]]) -> bool:
    """Phase 6.5 gate: true only when there is history AND an ambiguous reference.

    Standalone queries without pronouns bypass the rewriter (0ms, 0 cost),
    preserving the fast standard path.
    """
    if not history:
        return False
    return bool(_AMBIGUOUS_REFERENCE_RE.search(query))


def _needs_hyde(query: str) -> bool:
    """Gate for HyDE + query expansion on vague/short queries.

    Triggers when the query is short (< 6 words), doesn't contain a specific
    reference, and is in English (not Hindi/romanized Hindi — HyDE generates
    English hypotheticals which don't help cross-lingual retrieval).
    """
    words = query.split()
    if len(words) >= 6:
        return False
    if _SPECIFIC_QUERY_RE.search(query):
        return False
    if _AMBIGUOUS_REFERENCE_RE.search(query):
        return False
    # Skip HyDE for Hindi/Devanagari/romanized-Hindi queries
    from services.common.retrieval.hindi import contains_devanagari, is_romanized_hindi
    if contains_devanagari(query) or is_romanized_hindi(query):
        return False
    return True


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

        # ── Phase 1: Rewrite (existing) ──────────────────────────────
        if _needs_rewrite(query, history):
            t_rw = time.perf_counter()
            query = await asyncio.to_thread(
                self.provider.rewrite_query, query, history or []
            )
            rewrite_ms = round((time.perf_counter() - t_rw) * 1000, 1)
            logger.info("rewrite_ms=%.1f rewritten=%s", rewrite_ms, query[:80])

        # ── Phase 2: Original embedding + transliteration leg ────────
        # Pipeline #3 revision: ONLY fire for romanized Hindi content
        # words (zero latency for English queries; no LLM call).
        embedding = await asyncio.to_thread(self.provider.embed_query, query)

        # ── Phase 2a: Synonym expansion for BM25 ──────────────────
        # Expand acronyms (SDG → "sustainable development goals") so
        # BM25 can match full-form text in the corpus. Zero LLM cost.
        synonym_query = _expand_synonyms(query)

        # ── Phase 2b: HyDE for vague/short queries ─────────────────
        # Generate a hypothetical answer and embed it for dense search.
        # Catches vocabulary gaps: "risks" → "regulatory non-compliance penalties".
        use_hyde = _needs_hyde(query)
        hyde_embedding = None
        if use_hyde:
            try:
                hyde_text = await asyncio.to_thread(
                    self.provider.generate_hyde, query
                )
                # Parse keywords from HyDE output (format: "paragraph\nKeywords: kw1, kw2")
                hyde_keywords = ""
                if "\nKeywords:" in hyde_text:
                    parts = hyde_text.split("\nKeywords:", 1)
                    hyde_text = parts[0].strip()
                    hyde_keywords = parts[1].strip()
                # Embed both the hypothetical answer and keywords together
                combined_text = hyde_text
                if hyde_keywords:
                    combined_text = f"{hyde_text} {hyde_keywords}"
                hyde_embedding = await asyncio.to_thread(
                    self.provider.embed, combined_text
                )
                logger.info("hyde_generated query=%s hyde=%s keywords=%s", query[:40], hyde_text[:80], hyde_keywords[:50])
            except Exception as exc:
                logger.warning("hyde_failed: %s", exc)

        from services.common.retrieval.hindi import (
            contains_devanagari,
            is_romanized_hindi,
            transliterate_romanized_hindi,
        )

        translit_query = transliterate_romanized_hindi(query)
        needs_translit = (
            translit_query != query
            and self._has_devanagari_corpus(tenant_id)
            and is_romanized_hindi(query)
        )

        # ── Phase 2b: Cross-lingual gate (English→Hindi variant) ────
        # DISABLED: reranker-filtered cross-lingual path causes -0.056
        # Recall, -0.095 MRR, and 12× latency regression (5.3s P95).
        # The Hindi variant is noise the reranker can't fully filter.
        # Keep infrastructure for future re-activation with better gating.
        needs_xling = False
        xling_variant = None
        xling_variant_embedding = None

        # ── Phase 3: All store searches in parallel ──────────────────
        # Core: dense_orig + sparse_orig (always).
        # Transliteration leg: sparse on Devanagari-transliterated query.
        # Cross-lingual leg: dense_hindi + sparse_hindi (if variant generated).
        xling_variant = None
        xling_variant_embedding = None

        if needs_xling:
            # Generate Hindi variant in parallel with original embedding.
            variant_task = asyncio.to_thread(
                self.provider.generate_cross_lingual_variants, query
            )
            _, variants = await asyncio.gather(
                asyncio.sleep(0), variant_task
            )
            xling_variant = variants[0] if variants else None
            if xling_variant:
                xling_variant_embedding = await asyncio.to_thread(
                    self.provider.embed_query, xling_variant
                )

        search_tasks = [
            asyncio.to_thread(
                self.store.search_dense,
                embedding,
                tenant_id,
                doc_ids,
                limit=top_k * 4,
            ),
            asyncio.to_thread(
                self.store.search_sparse,
                synonym_query,
                tenant_id,
                doc_ids,
                limit=top_k * 4,
            ),
        ]
        # HyDE dense search: embed the hypothetical answer for vocabulary bridging
        if hyde_embedding is not None:
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_dense,
                    hyde_embedding,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 4,
                )
            )
        if needs_translit:
            # Sparse search on the Devanagari-transliterated query —
            # BM25 hits Hindi doc passages directly without LLM cost.
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_sparse,
                    translit_query,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 4,
                )
            )
        if xling_variant and xling_variant_embedding:
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_dense,
                    xling_variant_embedding,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 4,
                )
            )
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_sparse,
                    xling_variant,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 4,
                )
            )

        all_ranked = list(await asyncio.gather(*search_tasks))

        # ── Phase 5: Multi-list RRF or standard 2-list RRF ──────────
        if len(all_ranked) > 2:
            fused = multi_ranked_fusion(all_ranked)
        else:
            fused = reciprocal_rank_fusion(all_ranked[0], all_ranked[1])

        # When cross-lingual is active, expand candidate pool for the
        # reranker to filter. Otherwise use the standard pool size.
        pool_size = top_k * 8 if xling_variant else top_k * 3
        scored = await asyncio.to_thread(
            self._resolve_chunks, fused, pool_size, tenant_id
        )

        # When reranker is active (rerank_blend set), skip diversity
        # BEFORE reranking — let the reranker see all candidates.
        # Diversity runs only when reranking is disabled (pure hybrid).
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
        elif not doc_ids:
            scored = diversity_penalty(scored, top_k=top_k)

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
                "transliteration": needs_translit,
                "cross_lingual": bool(xling_variant),
                "hyde": use_hyde,
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
        rewrite_ms = round((time.perf_counter() - t0) * 1000, 1)
        logger.info("rewrite_ms=%.1f (deep) rewritten=%s", rewrite_ms, rewritten[:80])

        # ── Transliteration on the REWRITTEN query ────────────────────
        from services.common.retrieval.hindi import (
            contains_devanagari,
            is_romanized_hindi,
            transliterate_romanized_hindi,
        )

        translit_query = transliterate_romanized_hindi(rewritten)
        needs_translit = (
            translit_query != rewritten
            and self._has_devanagari_corpus(tenant_id)
            and is_romanized_hindi(rewritten)
        )

        # ── Cross-lingual gate (English→Hindi variant) ──────────────
        # DISABLED: see standard_search comment — regression + latency.
        needs_xling = False
        xling_variant = None
        xling_variant_embedding = None

        # ── HyDE for original query (unchanged) ──────────────────────
        try:
            hyde = await asyncio.to_thread(self.provider.generate_hyde, rewritten)
        except Exception:
            hyde = rewritten

        hyde_embedding = await asyncio.to_thread(self.provider.embed, hyde)

        # ── All store searches in parallel ───────────────────────────
        search_tasks = [
            asyncio.to_thread(
                self.store.search_dense,
                hyde_embedding,
                tenant_id,
                doc_ids,
                limit=top_k * 4,
            ),
            asyncio.to_thread(
                self.store.search_sparse,
                rewritten,
                tenant_id,
                doc_ids,
                limit=top_k * 4,
            ),
        ]
        if needs_translit:
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_sparse,
                    translit_query,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 4,
                )
            )
        if xling_variant and xling_variant_embedding:
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_dense,
                    xling_variant_embedding,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 4,
                )
            )
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_sparse,
                    xling_variant,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 4,
                )
            )

        all_ranked = list(await asyncio.gather(*search_tasks))

        if len(all_ranked) > 2:
            fused = multi_ranked_fusion(all_ranked)
        else:
            fused = reciprocal_rank_fusion(all_ranked[0], all_ranked[1])

        scored = await asyncio.to_thread(
            self._resolve_chunks, fused, top_k * 4, tenant_id
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
                "transliteration": needs_translit,
                "cross_lingual": bool(xling_variant),
            },
        )
        return results

    def _resolve_chunks(
        self, fused: List[Tuple[str, float]], limit: int, tenant_id: str
    ) -> List[ScoredChunk]:
        """Resolve RRF-fused (chunk_id, score) into full ScoredChunk objects.

        Pipeline Fix 1: chunks tagged as section_type="reference" (bibliography,
        citations) get a 0.2x score demotion. Reference sections accumulate
        massive term frequency (the same keyword appears in 40+ entries) which
        artificially inflates their BM25 ranking. The demotion pushes genuine
        content chunks above reference-choked candidates.
        """
        fused_ids = [cid for cid, _ in fused[:limit]]
        if not fused_ids:
            return []

        chunks = self.store.get_by_ids(fused_ids, tenant_id)
        chunk_map: Dict[str, Chunk] = {c.id: c for c in chunks}

        REFERENCE_DEMOTION = 0.2
        results: List[ScoredChunk] = []
        for chunk_id, rrf_score in fused:
            chunk = chunk_map.get(chunk_id)
            if chunk is None:
                continue
            meta = dict(chunk.metadata or {})
            score = rrf_score
            if meta.get("section_type") == "reference":
                score *= REFERENCE_DEMOTION
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
                    score=score,
                    metadata=meta,
                )
            )
        return results
