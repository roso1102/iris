# IRIS Retrieval Quality + Citation Correctness — Implementation Plan

Fixes, in dependency order, everything identified in the analysis: query-embed task type, the no-op reranker, the diversity/rerank conflict, page-recall granularity (small-to-big + parent-page expansion), bbox correctness (`_bbox_of` prov-union, page-level citations), and the frontend highlight degradation ladder. Each stage ends with a verification gate; the single expensive re-ingest happens once, in Stage 3.

**Baseline to beat (eval 2026-08-17):** Recall@5 0.83 · Page-Recall@5 0.32 · MRR 0.262 · P95 2.9s.

---

## Stage 0 — Land the in-flight Phase 6/9 work (housekeeping, unblocks everything)

The working tree already contains uncommitted implementations of ph6.md items 6.0a/6.5 (rewrite gate in `search.py`), 9.0-C (bbox Y-flip in `parser.py`), 9.0-D (`ref`-based citations in `vertex.py`), 9.0-E (marker normalization in `synthesis.py`), and the `rerank_blend` plumbing — but none of it is deployed, and the golden docs were never re-ingested with the Y-flip.

1. Fold in one small parser fix while we're here: `_bbox_of` (`services/common/ingestion/parser.py:212-222`) uses only `prov[0]` for single-page elements, so multi-prov same-page elements (lists) get the first item's box instead of the union. Reuse `_bbox_of_items(prov, page_dims)` on all same-page provs (group by `page_no`, take the element's page).
2. Run local tests (`pytest`), commit the in-flight work as logical commits (retrieval fixes / parser bbox / tests), delete or `.gitignore` the stray root `ERROR` file.
3. Deploy `retrieval-api` + `ingestion-worker` (manual `gcloud builds submit` + `gcloud run deploy`, the established Windows path).
4. Wipe and re-ingest the 8 golden docs; eyeball one citation highlight per doc on the live frontend (this validates the Y-flip before anything is built on top of it).
5. Run `python scripts/eval_phase2.py --skip-ingestion` → record the new baseline (expect `short_ambiguous` to improve from the rewrite gate).

**Gate:** highlights land on correct text on digital-PDF docs; eval report committed.

## Stage 1 — Free retrieval wins (no re-ingest)

**1a. Query-side embedding task type** (`services/common/models/base.py`, `vertex.py`, `search.py`)
- Add a concrete `embed_query(text)` to `ModelProvider` defaulting to `return self.embed(text)` (so `mock.py`/`gpu.py` need no changes); override in `VertexAIProvider` with `task_type="RETRIEVAL_QUERY"` (mirroring `embed()` at `vertex.py:168-183`, caching the `TextEmbeddingModel` instance while there).
- `standard_search` uses `provider.embed_query` for the query (`search.py:90`); `deep_search` keeps `embed` for the HyDE passage (hypothetical document → document task type, already correct).
- No re-ingest: document-side embeddings are unchanged.

**1b. Stop diversity from fighting page-recall and rerank** (`services/common/retrieval/diversity.py`, `search.py`)
- Change the dedup key from `doc_id` to `(doc_id, page_number)` — same-doc-different-page chunks are exactly the multi-page evidence page-recall grades.
- Skip the pass entirely when `doc_ids` is scoped (single-doc sessions: it's a no-op today anyway, and wrong in spirit).
- Move the diversity pass **before** the rerank leg so the reranker (the precision stage) always has final say on ordering; keep one code path (no conditional removal).
- Update `tests/test_search_orchestrator.py` accordingly.

**Gate:** `pytest` green; eval re-run shows MRR/Page-Recall deltas recorded in `eval_report_phase2.json`.

## Stage 2 — Real reranker, wired into `/query`

**2a. Replace the broken `rerank()`** (`services/common/models/vertex.py:320-377`)
- Current code calls `GenerativeModel("semantic-ranker@latest").generate_content(...)` — that model is not served as a generative model, so every call throws and silently returns `[1.0]*n` (order-preserving no-op). Replace with the Vertex AI Ranking API (Discovery Engine REST):
  - `POST https://{RERANK_LOCATION}-discoveryengine.googleapis.com/v1/projects/{project}/locations/{RERANK_LOCATION}/rankingConfigs/default_ranking_config:rank`
  - Body: `{"model": "semantic-ranker@latest", "query": ..., "records": [{"id": str(i), "content": chunk.text} for top candidates]}` (2048-token context model; cap ~40 records × 500 chars as today).
  - Auth via `google.auth.default()` + `google.auth.transport.requests.Request` (same pattern as `_signing_credentials`). Env: `RERANK_LOCATION` (default `global` — confirm latency vs `us-central1` in the sweep).
  - Response records come back **reordered by relevance**; derive per-passage scores from rank position (robust whether or not scores are returned).
- On failure: fall back to neutral order as today, but `logger.warning("rerank_failed", ...)` with the exception — the silent fallback is exactly how the no-op went unnoticed. Add a Cloud Logging counter/metric.

**2b. Scale-free fusion instead of score blending** (`services/common/retrieval/rrf.py`, `search.py`)
- The current `(1-b)*rrf + b*rerank` mixes incompatible scales (RRF ≈ 0.001–0.03 vs unbounded ranker scores) — at any blend it's effectively pure-reranker or nonsense. Replace with **weighted RRF**: the ranker contributes a third ranked list at weight `w` (mapped from the existing `rerank_blend` 0–1 param), each list contributing `w_i / (k_i + rank)`. Keep the `rerank_blend` request contract intact so the existing eval sweep works unchanged.
- New order in `standard_search`: fuse → resolve → diversity (1b) → weighted-RRF rerank fusion → sort → `top_k`.

**2c. Wire into `/query`** (`services/retrieval_api/app.py`)
- `/query` never passes `rerank_blend` today — production answers are never reranked. Add server-side env `RERANK_BLEND` (default `0.0` = off) read in `app.py` and passed to `standard_search`, so the frontend benefits without API changes.

**2d. Sweep and ship**
- Run `python scripts/eval_phase2.py --skip-ingestion --skip-deep --rerank-sweep` live; pick the best-MRR blend within the <400ms overhead budget; set it as the deployed `RERANK_BLEND`; deploy; final eval.
- Tests: mock-provider rerank already returns ascending scores (order-flipping) — add cases for weighted-RRF fusion math, failure→neutral+log, and `/query` env wiring.

**Gate:** rerank sweep present in `eval_report_phase2.json` with real deltas; MRR target ≥ 0.5 (aspirational — report honestly whatever comes out); rerank failures observable in logs.

## Stage 3 — One deliberate re-ingest: small-to-big (the structural page-recall fix)

**3a. Smaller retrieval units** (`services/common/ingestion/chunker.py`)
- `TARGET_TOKENS` 512 → 256, env-tunable (`CHUNK_TARGET_TOKENS`). Keep sentence packing and strict page boundaries. Finer units rank pages more precisely and tighten highlight boxes.

**3b. Tag page-level citations at ingest** (`chunker.py`)
- When a chunk's normalized bbox covers > ~70% of the page (VLM full-page OCR chunks), set `metadata["page_level"] = True` so the frontend skips the giant-frame overlay and just jumps to the page.

**3c. Re-ingest + verify**
- Deploy worker, wipe + re-ingest all 8 golden docs (chunk count roughly doubles — expected), eyeball highlights again (incl. one rotated/scanned doc), run full eval.

**3d. Parent-page expansion at synthesis time (no re-ingest dependency)** (`store.py`, `app.py`, `synthesis.py`)