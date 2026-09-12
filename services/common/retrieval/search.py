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

from services.common.embeddings import validate_embedding_vector
from services.common.ingestion.models import Chunk
from services.common.ingestion.store import ChunkStore
from services.common.models.base import ModelProvider
from services.common.retrieval import hyde as hyde_gating
from services.common.retrieval.diversity import diversity_penalty
from services.common.retrieval.models import ScoredChunk
from services.common.retrieval.rrf import (
    fuse_rerank_scores,
    multi_ranked_fusion,
    reciprocal_rank_fusion,
    weighted_ranked_fusion,
)

logger = logging.getLogger(__name__)

# Phase 6.5 pronoun/dependency heuristic gate: if the raw query contains none of
# these ambiguous indicators, skip the (costly) SLM rewriter entirely.
_AMBIGUOUS_REFERENCE_RE = re.compile(
    r"\b(it|its|this|that|these|those|their|theirs|his|her|former|latter|above|previous|"
    r"the\s+(?:former|latter))\b",
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


_PROTECTED_NUMBER_RE = re.compile(r"\d[\d,./:-]*")
_PROTECTED_IDENTIFIER_RE = re.compile(r"\b[A-Z][A-Z0-9-]{2,}\b")
_PROTECTED_QUOTED_RE = re.compile(r"[\"'“”‘’][^\"'“”‘’]{1,}[\"'“”‘’]")


def _protected_tokens(query: str) -> List[str]:
    """Quoted strings, numbers/amounts/dates and ALL-CAPS identifiers."""
    tokens = _PROTECTED_QUOTED_RE.findall(query)
    tokens += _PROTECTED_NUMBER_RE.findall(query)
    tokens += _PROTECTED_IDENTIFIER_RE.findall(query)
    return tokens


def _rewrite_fallback(query: str, reason: str) -> dict:
    return {
        "standalone_query": query,
        "preserved_entities": [],
        "document_scope": [],
        "temporal_scope": None,
        "language": "",
        "confidence": 0.0,
        "reason": reason,
    }


def _validate_rewrite(decision: object, original_query: str) -> dict:
    """Validate a structured rewrite decision before it is used.

    Rejects rewrites that drop quoted text, amounts, dates or identifiers that
    were present in the original query (RET-003). On any violation the original
    query is kept.
    """
    if not isinstance(decision, dict):
        return _rewrite_fallback(original_query, "invalid_decision")
    standalone = decision.get("standalone_query")
    if not isinstance(standalone, str) or not standalone.strip():
        return _rewrite_fallback(original_query, "empty_standalone_query")
    standalone = standalone.strip()
    for token in _protected_tokens(original_query):
        if token not in standalone:
            return _rewrite_fallback(original_query, "dropped_protected_token")
    result = _rewrite_fallback(original_query, "ok")
    result.update({
        "standalone_query": standalone,
        "preserved_entities": decision.get("preserved_entities") or [],
        "document_scope": decision.get("document_scope") or [],
        "temporal_scope": decision.get("temporal_scope"),
        "language": decision.get("language") or "",
        "confidence": decision.get("confidence") or 0.0,
        "reason": decision.get("reason") or "ok",
    })
    return result


def _needs_cross_lingual(query: str, has_devanagari_corpus: bool) -> bool:
    """Pipeline #3 gate: true when the query would benefit from a Hindi variant.

    Uses ``hindi.needs_cross_lingual_boost`` for the detection logic.
    Called AFTER ``_needs_rewrite`` so pronoun resolution happens first.
    """
    from services.common.retrieval.hindi import needs_cross_lingual_boost

    return needs_cross_lingual_boost(query, has_devanagari_corpus)


def _fuse_ranked(ranked_lists: List[List[Tuple[str, float]]]) -> List[Tuple[str, float]]:
    """Fuse two (or more) ranked lists with standard RRF."""
    if len(ranked_lists) > 2:
        return multi_ranked_fusion(ranked_lists)
    return reciprocal_rank_fusion(ranked_lists[0], ranked_lists[1])


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
        query_vector: Optional[List[float]] = None,
        query_text_for_sparse: Optional[str] = None,
    ) -> tuple[List[ScoredChunk], dict]:
        """Task 2.4a: Standard non-blocking async search path.

        Returns (results, trace) where trace carries HyDE + debug metadata.
        """
        t0 = time.perf_counter()
        original_query = query
        rewritten_query = None
        rewrite_meta = None
        pre_computed = query_vector is not None
        hyde_trace = {
            "eligible": False,
            "used": False,
            "bypass_reason": None,
            "baseline_top_score": 0.0,
            "latency_ms": 0.0,
            "estimated_cost": 0.0,
        }
        hyde_embedding = None
        hyde_text = ""
        hyde_keywords = ""
        hyde_latency_ms = 0.0
        rewrite_ms = 0.0
        # Cross-lingual variant legs remain disabled (regression note below).
        needs_xling = False
        xling_variant = None
        xling_variant_embedding = None

        if pre_computed:
            # Fast path: pre-computed vector from the decomposition pipeline.
            embedding = validate_embedding_vector(query_vector)
            sparse_text = query_text_for_sparse or query
            synonym_query = _expand_synonyms(sparse_text)
            translit_query = sparse_text
            needs_translit = False
        else:
            # ── Phase 1: rewrite ONLY context-dependent turns ────────────
            if _needs_rewrite(query, history):
                t_rw = time.perf_counter()
                decision = await asyncio.to_thread(
                    self.provider.rewrite_query_structured, query, history or []
                )
                rewrite_meta = _validate_rewrite(decision, original_query)
                query = rewrite_meta["standalone_query"]
                rewrite_ms = round((time.perf_counter() - t_rw) * 1000, 1)
                if query != original_query:
                    rewritten_query = query

            # ── Phase 2: Original-query embedding ───────────────────────
            embedding = validate_embedding_vector(
                await asyncio.to_thread(self.provider.embed_query, query)
            )
            synonym_query = _expand_synonyms(query)

            from services.common.retrieval.hindi import (
                is_romanized_hindi,
                transliterate_romanized_hindi,
            )

            translit_query = transliterate_romanized_hindi(query)
            needs_translit = (
                translit_query != query
                and self._has_devanagari_corpus(tenant_id)
                and is_romanized_hindi(query)
            )

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

        # ── Phase 3: baseline retrieval always runs (dense + sparse) ────────
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

        t_search = time.perf_counter()
        all_ranked = list(await asyncio.gather(*search_tasks))
        search_ms = round((time.perf_counter() - t_search) * 1000, 1)

        # ── Phase 4: baseline-first HyDE decision ───────────────────────────
        fused = _fuse_ranked(all_ranked)
        if not pre_computed:
            dense_scores = all_ranked[0]
            sparse_scores = all_ranked[1]
            reason = hyde_gating.bypass_reason(
                original_query, rewritten=rewritten_query is not None
            )
            eligible = reason is None
            dense_top = dense_scores[0][1] if dense_scores else 0.0
            weak = hyde_gating.baseline_is_weak(
                dense_scores, sparse_scores
            ) or (
                bool(dense_scores)
                and dense_top < 0.5
                and hyde_gating.low_agreement(dense_scores, sparse_scores)
            )
            hyde_trace["eligible"] = eligible
            hyde_trace["bypass_reason"] = reason
            hyde_trace["baseline_top_score"] = round(dense_top, 4)

            if eligible and weak:
                t_hyde = time.perf_counter()
                try:
                    raw = await asyncio.to_thread(self.provider.generate_hyde, query)
                    parsed = hyde_gating.validate_hyde_output(raw, query)
                    if parsed:
                        hyde_embedding = validate_embedding_vector(
                            await asyncio.to_thread(
                                self.provider.embed, hyde_gating.hyde_text_of(parsed)
                            )
                        )
                        hyde_text = parsed["hypothesis"]
                        hyde_keywords = " ".join(parsed["keywords"])
                        hyde_trace["used"] = True
                        hyde_trace["estimated_cost"] = hyde_gating.HYDE_ESTIMATED_COST_USD
                except Exception as exc:
                    logger.warning("hyde_failed: %s", exc)
                hyde_latency_ms = round((time.perf_counter() - t_hyde) * 1000, 1)
                hyde_trace["latency_ms"] = hyde_latency_ms
                if hyde_embedding is not None:
                    hyde_dense = list(
                        await asyncio.to_thread(
                            self.store.search_dense,
                            hyde_embedding,
                            tenant_id,
                            doc_ids,
                            limit=top_k * 4,
                        )
                    )
                    fused = weighted_ranked_fusion(
                        list(all_ranked) + [hyde_dense],
                        [1.0] * len(all_ranked) + [hyde_gating.HYDE_LEG_WEIGHT],
                    )

        # When cross-lingual is active, expand candidate pool for the
        # reranker to filter. Otherwise use the standard pool size.
        pool_size = top_k * 8 if xling_variant else top_k * 3
        scored = await asyncio.to_thread(
            self._resolve_chunks, fused, pool_size, tenant_id
        )

        # When reranker is active (rerank_blend set), skip diversity
        # BEFORE reranking — let the reranker see all candidates.
        # Diversity runs only when reranking is disabled (pure hybrid).
        rerank_ms = 0.0
        diversity_ms = 0.0
        if rerank_blend is not None and scored:
            t_rerank = time.perf_counter()
            scores = await asyncio.to_thread(
                self.provider.rerank, query, [c.text for c in scored]
            )
            rerank_ms = round((time.perf_counter() - t_rerank) * 1000, 1)
            blended = fuse_rerank_scores(
                [c.score for c in scored], scores, rerank_blend
            )
            for chunk, blended_score in zip(scored, blended):
                chunk.score = blended_score
            scored.sort(key=lambda c: c.score, reverse=True)
        elif not doc_ids:
            t_div = time.perf_counter()
            scored = diversity_penalty(scored, top_k=top_k)
            diversity_ms = round((time.perf_counter() - t_div) * 1000, 1)

        results = scored[:top_k]

        latency = round((time.perf_counter() - t0) * 1000, 2)

        # Build trace dict for debugging
        trace = {
            "hyde": hyde_trace,
            "rewritten_query": rewritten_query,
            "rewrite": rewrite_meta,
            "synonym_query": synonym_query,
            "latency": {
                "rewrite_ms": rewrite_ms if rewritten_query else 0.0,
                "hyde_ms": hyde_latency_ms,
                "search_ms": search_ms,
                "rerank_ms": rerank_ms,
                "diversity_ms": diversity_ms,
                "total_ms": latency,
            },
        }
        if hyde_trace["used"]:
            trace["hyde"]["text"] = hyde_text
            trace["hyde"]["keywords"] = hyde_keywords

        logger.info(
            "search_completed",
            extra={
                "mode": "standard",
                "rerank_blend": rerank_blend,
                "latency_ms": latency,
                "top_score": results[0].score if results else 0.0,
                "tenant_id": tenant_id,
                "num_results": len(results),
                "transliteration": needs_translit,
                "cross_lingual": bool(xling_variant),
                "hyde": hyde_trace["used"],
                "hyde_bypass_reason": hyde_trace["bypass_reason"],
            },
        )
        return results, trace

    async def deep_search(
        self,
        query: str,
        tenant_id: str,
        history: Optional[List[dict]] = None,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 10,
        trace: Optional[dict] = None,
    ) -> List[ScoredChunk]:
        """Deep Search with async SLM rewrite, HyDE generation, and fusion.

        Deep is an explicit opt-in expensive path, so HyDE is not
        baseline-gated — but it never *replaces* the original-query legs and
        the deterministic bypass (greetings/identifiers/…) still applies.
        """
        t0 = time.perf_counter()
        original_query = query

        if _needs_rewrite(query, history):
            decision = await asyncio.to_thread(
                self.provider.rewrite_query_structured, query, history or []
            )
            rewrite_meta = _validate_rewrite(decision, original_query)
            rewritten = rewrite_meta["standalone_query"]
        else:
            # Same context-dependence gate as standard mode: deep opts into
            # HyDE, not into rewriting every standalone query.
            rewrite_meta = _rewrite_fallback(original_query, "not_context_dependent")
            rewritten = original_query
        rewrite_ms = round((time.perf_counter() - t0) * 1000, 1)

        # ── Transliteration on the REWRITTEN query ────────────────────
        from services.common.retrieval.hindi import (
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

        # Original-query legs always run (dense uses the QUERY task type).
        base_embedding = validate_embedding_vector(
            await asyncio.to_thread(self.provider.embed_query, rewritten)
        )

        # ── HyDE leg (deep opt-in; deterministic bypass still applies) ──
        reason = hyde_gating.bypass_reason(original_query)
        hyde_embedding = None
        hyde_trace = {
            "eligible": reason is None,
            "used": False,
            "bypass_reason": reason,
            "baseline_top_score": 0.0,
            "latency_ms": 0.0,
            "estimated_cost": 0.0,
        }
        if reason is None:
            t_hyde = time.perf_counter()
            try:
                raw = await asyncio.to_thread(self.provider.generate_hyde, rewritten)
                parsed = hyde_gating.validate_hyde_output(raw, rewritten)
                if parsed:
                    hyde_embedding = validate_embedding_vector(
                        await asyncio.to_thread(
                            self.provider.embed, hyde_gating.hyde_text_of(parsed)
                        )
                    )
                    hyde_trace["used"] = True
                    hyde_trace["estimated_cost"] = hyde_gating.HYDE_ESTIMATED_COST_USD
            except Exception as exc:
                logger.warning("hyde_failed: %s", exc)
                try:
                    hyde_embedding = validate_embedding_vector(
                        await asyncio.to_thread(self.provider.embed, rewritten)
                    )
                except Exception as inner:  # pragma: no cover - defensive
                    logger.warning("hyde_fallback_failed: %s", inner)
            hyde_trace["latency_ms"] = round((time.perf_counter() - t_hyde) * 1000, 1)

        # ── All store searches in parallel ───────────────────────────
        search_tasks = [
            asyncio.to_thread(
                self.store.search_dense,
                base_embedding,
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
        hyde_index = None
        if hyde_embedding is not None:
            hyde_index = len(search_tasks)
            search_tasks.append(
                asyncio.to_thread(
                    self.store.search_dense,
                    hyde_embedding,
                    tenant_id,
                    doc_ids,
                    limit=top_k * 4,
                )
            )

        all_ranked = list(await asyncio.gather(*search_tasks))

        if hyde_index is not None:
            weights = [1.0] * len(all_ranked)
            weights[hyde_index] = hyde_gating.HYDE_LEG_WEIGHT
            fused = weighted_ranked_fusion(all_ranked, weights)
        else:
            fused = _fuse_ranked(all_ranked)

        scored = await asyncio.to_thread(
            self._resolve_chunks, fused, top_k * 4, tenant_id
        )
        if not doc_ids:
            scored = diversity_penalty(scored, top_k=top_k)
        results = scored[:top_k]

        latency = round((time.perf_counter() - t0) * 1000, 2)
        if trace is not None:
            trace["hyde"] = hyde_trace
            trace["rewrite"] = rewrite_meta
            trace["latency"] = {
                "rewrite_ms": rewrite_ms,
                "hyde_ms": hyde_trace["latency_ms"],
                "total_ms": latency,
            }
        logger.info(
            "search_completed",
            extra={
                "mode": "deep",
                "latency_ms": latency,
                "top_score": results[0].score if results else 0.0,
                "tenant_id": tenant_id,
                "num_results": len(results),
                "transliteration": needs_translit,
                "cross_lingual": bool(xling_variant),
                "hyde": hyde_trace["used"],
                "hyde_bypass_reason": hyde_trace["bypass_reason"],
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
