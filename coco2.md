# IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2)

Baseline to beat (eval 2026-08-17): **Recall@5 0.83 · Page-Recall@5 0.32 · MRR 0.262 · P95 2.9s**.
Re-checked the working tree before this revision — it matches the analyzed state (in-flight 6.0a/6.5, 9.0-C/D/E, rerank plumbing, all uncommitted).

**Issue → fix → metric mapping:**

| Problem | Fix (stage) | Metrics hit |
|---|---|---|
| Queries embedded with `RETRIEVAL_DOCUMENT` task type | `embed_query()` w/ `RETRIEVAL_QUERY` (S1) | MRR, Recall@5, Page-Recall |
| Reranker is a silent no-op (`GenerativeModel("semantic-ranker")` always throws) + `/query` never reranks | Real Vertex AI Ranking API + weighted RRF fusion + `/query` wiring (S2) | **MRR (main lever)**, Page-Recall |
| Diversity pass penalizes same-doc-different-page and runs after rerank | Page-level key, skip when doc-scoped, move before rerank (S1) | Page-Recall, MRR |
| 512-token chunks too coarse to rank pages | Small-to-big: 256-token units + parent-page expansion (S3) | Page-Recall (main), MRR |
| English-only BM25 over Devanagari corpus | Hindi preprocessing layer (S5) | hindi_lookup page-recall (0.33) |
| bbox: prov[0]-only for multi-prov elements; full-page boxes render as giant frames | prov-union fix (S0), `page_level` tagging + frontend ladder (S3/S4) | citation UX |
| `/query` ignores `session_id`; history is client-trusted | Phase 6.1–6.4 (S6) | multi-turn accuracy |

**Verification discipline (per your instruction):** every stage = implement → **local unit tests (`pytest`, mock providers, MemoryChunkStore)** → local integration where possible (Docling parser tests run locally against `trueassort/` PDFs; frontend via `npm build` + Playwright) → **STOP and ask you before any GCP action** (deploy, re-ingest, live eval, live Vertex calls). No gcloud runs without an explicit go-ahead per stage.

---

## Stage 0 — Land the in-flight Phase 6/9 work + one bbox fix

1. **`_bbox_of` prov-union fix** (`services/common/ingestion/parser.py:212-222`): single-page elements with multiple provs (lists) currently get only the first item's box. Group provs by `page_no`, union via `_bbox_of_items` — same as the multi-page path already does.
2. **Unit tests:** new cases in `tests/test_page_chunking.py`: multi-prov same-page element → union bbox; multi-prov multi-page → unchanged behavior (guard).
3. **Local verify:** full `pytest` (~190 tests) + the Docling integration tests against `trueassort/` PDFs (runs locally, no GCP).
4. Commit the in-flight work as logical commits (retrieval fixes / parser bbox / tests); delete or `.gitignore` the stray root `ERROR` file.
5. 🛑 **ASK → GCP:** deploy both services, wipe + re-ingest the 8 golden docs, eyeball one highlight per doc on the live frontend, run `eval_phase2.py --skip-ingestion` → new baseline recorded.

## Stage 1 — Free retrieval wins (fully local, no re-ingest)

**1a. Query-side embedding task type** — `base.py` gets concrete `embed_query(text)` defaulting to `self.embed(text)` (mock/gpu untouched); `VertexAIProvider` overrides with `task_type="RETRIEVAL_QUERY"` and caches the `TextEmbeddingModel` instance; `standard_search` uses it (`search.py:90`), `deep_search` keeps `embed` for HyDE (document task is correct there).
**1b. Diversity reorder** — key becomes `(doc_id, page_number)`; skip the pass when `doc_ids` is scoped; move it **before** the rerank leg so the reranker always has final say.
**Unit tests:** `test_search_orchestrator.py` — spy asserting standard path calls `embed_query` and deep path calls `embed`; `test_diversity.py` — same-doc-different-page not penalized, same page still deduped, doc-scoped skip, diversity-then-rerank ordering; `test_model_provider.py` — default delegation.

🛑 **ASK → GCP (optional):** deploy retrieval-api only, run eval to record the free delta. (No deploy needed if you prefer to batch with Stage 2.)

## Stage 2 — Real reranker, wired into `/query`

**2a. Replace broken `rerank()`** (`vertex.py:320-377`) with the Vertex AI Ranking API (plain REST + google-auth, no new SDK):
`POST https://{RERANK_LOCATION}-discoveryengine.googleapis.com/v1/projects/{project}/locations/{RERANK_LOCATION}/rankingConfigs/default_ranking_config:rank` with `{"model": "semantic-ranker@latest", "query", "records": [{"id", "content"}]}` (≤40 records × 500 chars). Response is reordered records → derive scores from rank position. On failure: neutral fallback + **loud `logger.warning("rerank_failed")`** (the silent fallback is how the no-op went unnoticed). Env: `RERANK_LOCATION` (default `global`).
**2b. Weighted RRF fusion** (`rrf.py`): ranker contributes a third ranked list, `w/(k+rank)` — scale-free, replaces the broken `(1-b)*rrf + b*score` blend. Existing `rerank_blend` request contract preserved so the eval sweep works unchanged.
**2c. `/query` wiring** (`app.py`): server env `RERANK_BLEND` (default 0.0=off) passed to `standard_search` — production answers get reranking without API changes.

**Unit tests:** `test_rrf.py` — fusion math (weight 0 = hybrid order, 1 = pure ranker, ties); `test_model_provider.py` — mocked HTTP: happy path maps order→scores, 40 cap, 500-char cap, failure → neutral + logged warning; `test_retrieval_api.py` — env wiring on/off; `test_search_orchestrator.py` — end-to-end reorder with mock provider.

🛑 **ASK → GCP:** deploy, run `eval_phase2.py --skip-ingestion --skip-deep --rerank-sweep`, pick best-MRR blend within <400ms overhead, redeploy with `RERANK_BLEND` set, final eval. (Also gate the optional `RUN_VERTEX_LIVE_TESTS` ranking smoke test.)

## Stage 3 — Re-ingest batch: small-to-big chunking + page-level citations

**3a.** `CHUNK_TARGET_TOKENS` env (default 256) in `chunker.py`; sentence packing + page-strict boundaries unchanged.
**3b.** Tag `metadata["page_level"]=True` when normalized bbox area > 0.7 (VLM full-page OCR chunks).
**3c. Parent-page expansion** (no re-ingest dependency, code alongside): `get_by_doc_pages()` on both stores; in `/query` only (`/search` untouched → eval honesty), fetch same-page siblings of top chunks, append to synthesis context; `validate_citations` runs against retrieved ∪ siblings.

**Unit tests:** `test_chunker.py` — env override, ~256-token budget, area-threshold tagging (full-page vs normal); `test_retrieval_store.py` — filter construction (mocked Qdrant client) + MemoryChunkStore equivalent; `test_retrieval_api.py` — `/query` context includes same-page chunks, citations validate against expanded set; `test_synthesis.py` — neighbor-chunk citations survive validation.

🛑 **ASK → GCP:** deploy worker + api, wipe + re-ingest #2 (chunk count ~2×), eyeball highlights (incl. one rotated/scanned doc), full eval.

*Note: re-ingest #1 (Stage 0, Y-flip) and #2 (Stage 3, chunk size) are deliberately separate for clean metric attribution. If you'd rather re-ingest once, Stages 0–3's ingest-affecting changes can be batched — say so and I'll merge them.*

## Stage 4 — Frontend highlight degradation ladder (`D:\iris-frontend`)

**4a.** `bboxToViewportRect()` in `lib/pdf/`: denormalize against `page.view` (CropBox) → `viewport.convertToViewportRectangle()` → CSS pixels. Fixes rotated pages and CropBox drift in one util, replacing naive `bbox × canvas` math in `BboxOverlay.tsx`.
**4b. Ladder** (`PdfPanel.tsx` + new `findTextQuads()` using `getTextContent()` item transforms): (1) `page_level` → page jump only; (2) bbox **and** text-quads intersect → bbox overlay (verified); (3) bbox misses text → render text quads instead (never a confidently-wrong box); (4) no match → page jump + existing "not found" note. Zero-citation footer (9.0-B) in `ChatPanel`/`MessageBubble`.

**Unit tests (local):** pure-function tests for `bboxToViewportRect` (0°/90°/270° rotation, CropBox offset) and `findTextQuads` (fragmented text items, hyphenation) — via vitest (add if absent; repo has Playwright only). Playwright e2e: citation-click flows on a fixture PDF covering all four ladder rungs. `npm run build` + e2e locally.

🛑 **ASK → GCP:** verify the ladder against the live demo (digital doc, scanned doc, rotated doc) after Stage 3 is deployed.

## Stage 5 — Hindi-aware BM25 (before re-ingest #2 if you merge stages; otherwise piggybacks on the next one)

Fastembed 0.8.0 `Bm25` has **no Hindi** (18 languages, Tamil is the only Indic) — so this is a preprocessing layer, not a config flag:
1. New `services/common/retrieval/hindi.py`: Devanagari range detection (`\u0900-\u097F`), curated Hindi stopword list (~60 common function words), light suffix-stripping stemmer for common inflections (ों/ओं/े/ी/यों/यें/स/ो/ा).
2. Applied **symmetrically** in `text_to_sparse()` (queries) and `upsert_batch()` (passages) — consistency matters more than the stemmer itself. Env-gated `BM25_HINDI_ENABLED` (default on after tests).
3. Effective for stored passages only after re-ingest — batched with Stage 3's re-ingest (or a dedicated one, your call at the gate).

**Unit tests:** `test_bm25.py` — Devanagari detection, stopword removal, stemmer suffix cases, symmetric query/passage encoding, mixed-script text, English path untouched when disabled, disabled-by-default path.

🛑 **ASK → GCP:** deploy + re-ingest (batched with Stage 3 if merged), eval — watch `hindi_lookup` page-recall (0.333 today).

## Stage 6 — Phase 6.1–6.4 conversational memory (per ACTIONPLAN)

- **6.1 Firestore history:** `/query` writes each turn (user question + answer + citation refs) to `tenants/{tenant}/sessions/{session_id}/messages`; new `GET /sessions/{session_id}/messages` (tenant-scoped).
- **6.2** `rewrite_query()` — already exists; verification only.
- **6.3 Server-side history:** when `session_id` is present, `/query` loads the sliding window (last N=6, FR-5.3) from Firestore — server becomes source of truth; client-sent `history` is ignored/merged-only-when-no-session. Feeds the existing `_needs_rewrite` gate (6.5, done).
- **6.4 Budget:** `rewrite_ms` timing in logs; `max_output_tokens≈256` on the Flash-Lite rewrite call (thinking_budget already 0). Target sub-300ms, <$0.001/call.
- **6.6 Topic-summary compression:** >15 turns → 2-sentence running `summary` field on the session doc (updated incrementally by Flash-Lite); rewrite context = summary + last 2 raw messages, <200 tokens.
- Frontend: chat panel stops sending history once sessions carry it (server-wins).

**Unit tests (local):** `test_sessions_api.py` — write-on-query, message list ordering + N=6 window, tenant scoping, 15-turn compression trigger, summary+2-raw context shape, char-budget assertion; `test_search_orchestrator.py` — session-loaded history drives the rewrite gate.

🛑 **ASK → GCP:** deploy, then live Tests 6-A (≥90% resolution over 5-turn convo), 6-B (history persists across reload), 6-C (sub-300ms/$0.001), 6-D (gate bypass precision).

## Stage 7 — Close the loop

Commit per-stage eval reports; update `CONTEXT.md` §2/§4/§5 (new metrics, gotchas: Ranking API region, weighted-RRF, rotation mapping, Hindi tokenizer) and `ph6.md` checkboxes.

## Deferred (post-MVP, unchanged)
Qdrant VM snapshots · Firestore-backed distributed rate limiter · 3072-d embeddings · line-level bboxes.

## Key risks
- **Ranking API latency/region** — sweep measures; failure degrades to hybrid (logged).
- **256-token chunks vs multi_hop recall** — parent-page expansion compensates; per-type eval table will show it.
- **Custom Hindi stemmer quality** — it's a recall aid on top of dense (which already carries hindi_lookup at doc-recall 1.0); worst case is neutral.
- **Two re-ingests** — deliberate for attribution; mergeable on request.