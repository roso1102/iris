# HANDOFF.md — IRIS Retrieval-Quality Workstream (full session handoff)

**Written:** 2026-08-23 · **Branch:** `main` @ `f0a5a6c` · **Working tree:** clean (everything pushed)
**Scope of this handoff:** the entire ZCode session that began with "analyse the codebase, suggest ideas for better MRR/recall/page-recall and bbox handling" and ended with the fully-indexed corpus and Recall@5 = 1.000. Read this top to bottom before touching anything.

---

## 1. What IRIS is (one paragraph)

IRIS is a multi-tenant, spatially-grounded document Q&A platform on GCP (`naturepivot-rag`, region `asia-south1`). Dense legal/scanned PDFs are ingested (Docling layout parse → 4-signal VLM router → sentence chunker → Qdrant hybrid BM25+dense, RRF fusion), queried via `/search` and `/query` (Gemini Flash synthesis with validated structured citations + bbox highlights), frontend on Vercel. Stack specifics, frozen decisions (768-d embeddings, CPU-only, Marker banned, Cohere deprecated) live in `CONTEXT.md` §3 — treat that file as the canonical project memory; I append a session-log bullet there per session.

## 2. Ground rules the user has set (NEVER violate)

1. **Local-first verification:** every change = implement → local `pytest` → only then GCP. **Always ask before any GCP action** (deploy, re-ingest, live eval, live API calls). The user answers promptly; don't assume.
2. **Report at every stage** what was done — the user reads everything.
3. **Discussion honesty:** push back with reasons when the user or an external reviewer is wrong (they explicitly value this); never silently comply.
4. **Metrics discipline:** corrected numbers are **floors-not-finals** until every label question is adjudicated (now done — labels are final as of 2026-08-23). Never quote a metric without its caveat (e.g. per-type n sizes: hindi_lookup n=3, scanned_lookup n=7).
5. **Eval-set authoring:** new golden queries are written by the human from the raw PDFs, NOT by the agent (selection bias). The agent builds tooling and verifies labels against ground truth (PDF text layer / vision), never against retrieval output ("don't grade your own homework").
6. **Page-number convention (settled):** everything uses **PDF physical sequence, 1-based** ("viewer" numbering) — pipeline, citations, frontend, golden labels. The documents' *printed* page numbers differ per-doc and NON-uniformly (doc_008: printed = viewer + 2; doc_006: +1; doc_007: MIXED, not a constant offset) — this caused the entire label corruption saga.

## 3. Chronological record of this session (what happened and why)

### Phase A — Analysis (discussion only)
Diagnosed the weak metrics (MRR 0.262 / Page-Recall 0.320 / Recall 0.830 / P95 2.9s, eval of 2026-08-17). Found: (a) queries embedded with `task_type=RETRIEVAL_DOCUMENT`; (b) the reranker was a **silent no-op** (`GenerativeModel("semantic-ranker@latest").generate_content` always throws → broad except → neutral scores); (c) diversity pass penalized same-doc-different-page and ran after rerank; (d) 512-token chunks too coarse; (e) bbox bugs (union direction, prov[0]-only, full-page boxes); (f) BM25 English-only over Devanagari corpus. Also assessed architecture (strong: provider abstraction, engine-level tenancy, citation validator; weak: single Qdrant VM, per-instance rate limiter, observability) and recommended the highlight **degradation ladder** (bbox → text-quad → page jump) instead of page-only citations.

### Phase B — Approved plan (v2) and Stages 0–5
Plan approved after one rejection (user added: unit tests per stage, local-then-GCP-ask, Hindi BM25, Phase 6.1–6.4, two attributed re-ingests). Executed:
- **S0** parser bbox: found the union min/max used TOPLEFT conventions on BOTTOMLEFT boxes (inverts multi-box pages — caught by actually running the math); `_bbox_of` now unions all same-page provs. Committed the in-flight 6.0a/6.5/9.0-C/D/E work in 4 logical commits.
- **S1** `embed_query()` (default delegates to `embed`; Vertex override uses `RETRIEVAL_QUERY`; HyDE keeps document task) + cached `TextEmbeddingModel` + diversity → `(doc_id, page_number)` key, skip when `doc_ids` scoped, moved before rerank.
- **S2** real reranker: Discovery Engine REST (`POST https://{loc}-discoveryengine.googleapis.com/v1/projects/{p}/locations/{loc}/rankingConfigs/default_ranking_config:rank`, model `semantic-ranker@latest`, ≤40 records); scores derived from returned order; loud `rerank_failed_fallback_to_hybrid` warning; ADC token cached. `fuse_rerank_scores()` = **weighted rank fusion** `(1-blend)*hybrid + 2*blend/(k+rank)` (raw score blending mixes incompatible scales — blend 0=hybrid, 1=pure ranker; a test caught a zip-truncation bug in v1). `/query` reads `RERANK_BLEND` env (default off; invalid → warn + off).
- **S3** `CHUNK_TARGET_TOKENS` env (code default 256, clamp 64..2048); `page_level` metadata tag when bbox area ≥ 0.7; `ChunkStore.get_by_doc_pages()` (ABC+Memory+Qdrant, `_payload_to_chunk` refactor); `/query` `_expand_to_parent_pages()` (synthesis context + citation validation widened; `/search` untouched for eval honesty).
- **S5** `retrieval/hindi.py`: Devanagari detection, ~90 stopwords, single-pass longest-suffix stemmer (min stem 4 codepoints — 3 over-stemmed "क्यों"→"क्य", a test caught it); wired symmetrically in `text_to_sparse` behind `BM25_HINDI_ENABLED` (default OFF — enable only with re-ingest).

### Phase C — GCP Rounds A/B/C (live)
- **Round A** (bbox attribution, worker pinned `CHUNK_TARGET_TOKENS=512`): captured live env via `gcloud run services describe` BEFORE deploy (env flags REPLACE everything); doc hash-cache is Qdrant-based so wipe = delete points (we used cascading `DELETE /documents` + re-upload local PDFs via `/documents/upload`); Vertex 429 storms on upload-triggers (trial quota) → `scripts/round_a_recover.py` (direct worker `/ingest`, 75s backoff); `wait_for_ingestion` passes at chunks>0 prematurely — poll for stable counts instead. Result: MRR 0.313 / PageRec 0.354 / P95 541ms; bbox sanity 100/100; live `/query` citation carried a sane line-shaped box.
- **Round B** (reranker): three failures fixed in sequence — Discovery Engine API not enabled (enabled it); retrieval-api SA lacked permission (granted `roles/discoveryengine.viewer` — even viewer contains `discoveryengine.rankingConfigs.rank`); records capped at 500 chars while chunks are ~2000 (semantic-ranker v004 accepts 1024 tokens/record ≈ 3500 chars; fixed, `RERANK_MAX_CHARS` env). **Two honest sweeps on both chunk sizes: the ranker adds nothing on this corpus** (best +0.003 MRR at ~700ms; pure-reranker strictly worse). `RERANK_BLEND` stays OFF. It remains built, IAM-wired and canaried.
- **Round C** (256 + Hindi): deployed both; chunk counts barely moved → **key discovery: the corpus is VLM-chunk dominated** (`docling_text` ≤996 chars proving 256 works; `vlm_full_page` ≤3.8K, `vlm_table` ≤131K chars in ONE chunk — VLM outputs are single chunks by frozen design and bypass the token budget). Result: Recall 0.880 / PageRec 0.384 / MRR 0.299 / P95 426ms.

### Phase D — External-review exchanges (user relayed a reviewer; three rounds)
Key outcomes adopted: observability as a prerequisite (canary), eval-set validity as the core problem (n=50, reused, author-biased), **table-chunk header carry-forward** requirement (splitting markdown tables without repeating headers makes pieces semantically useless), reranker verdict recorded as "untested under fair conditions" not "doesn't work", the 4 VLM-OCR-verified labels downgraded to "high-confidence, one source". I pushed back where warranted: order-difference canary assertion would false-alarm (ranker legitimately agrees with hybrid on many queries) → direct Ranking-API probe instead; dedup-isolation A/B is pointless at n=50 (grow eval set first).

### Phase E — Measurement overhaul
- `scripts/label_audit.py`: 25/50 queries flagged; 13 off-by-ones ALL same direction (label+1 = retrieval hit). Verified against **source PDF text layer** (6) and **VLM OCR text** (4, one-source, disclosed): labels were authored against printed page numbers. `scripts/fix_golden_pages.py` applied +1 to the 10 verified (original backed up to `goldendataset.pre-audit-backup.json`).
- `scripts/examine_flags.py` classified the rest: 3 REAL_MISS, 2 LABEL_SUSPECT, 7 unverifiable (scanned).
- **User adjudicated everything** in two rounds (see `label_adjudication_guide.md`): caught wrong ANSWER texts too (q_005 was a different question's answer, real answer on p24; q_009 Section 9 penalizes contravention of S.4/S.8, page 4; q_029 Maharashtra Central Share is 2,577.60 cr not Madhya Pradesh's 1,456). I verified what's verifiable (text-layer needles; rendered pages + vision for scanned: Form-8 on doc_002 viewer p5, Section 9 penalty on doc_001 viewer p4, "FOR OFFICE USE" form on doc_002 p7). ~30 total corrections committed.

### Phase F — Canary (observability)
`services/canary/main.py`, gen2 Cloud Function `iris-canary` (asia-south1, SA `retrieval-api-sa`, secrets `canary-firebase-api-key`/`canary-eval-password`), Cloud Scheduler `iris-canary-job` every 15 min, log metric `iris_canary_failures`. Five assertions: livez+store; fixed golden query returns results with **valid normalized TOPLEFT bboxes** (Stage-0 bug class); search latency budget; **rerank-leg latency signature** (≥150ms delta, warm-up request first + two attempts — cold-start warm-up produced negative deltas otherwise); **direct Ranking API probe** (rank relevant-vs-irrelevant, assert score separation — verified working in production with the SA's fresh creds). Production debugging earned its keep: caught missing `requests` dep, warm-up poisoning, and my stale local ADC. Function needed BOTH `roles/cloudfunctions.invoker` AND `roles/run.invoker` for the Scheduler's OIDC. **User set up the alert policy on the metric (done).**

### Phase G — Corpus completion (pipeline #1)
- Corpus scan: **16 un-indexed pages** (doc_001 6, doc_002 5, doc_008 2 scanned; doc_003 p27 DIGITAL with 1,751 chars; doc_004/005 trailing blanks). Root cause reproduced locally: **Docling detects ZERO layout elements on some pages**; with `do_ocr=False` nothing reaches the router; pages "ingest successfully" with `chunks=0 vlm_calls=0` — silent data loss.
- **Fix** (`services/common/ingestion/main.py` ingest()): zero elements → synthesize one empty-text full-page `ParsedElement` → rides the router's existing low-text path (Signal 2, `_valid_word_ratio("")=0 < 0.75`) into `VLM_FULL_PAGE` OCR. Zero router changes. Chunker tags the `[0,0,1,1]` bbox `page_level`. Logs `zero_element_page_fallback`.
- **CI STALLED** (see gotchas) → manual build+deploy of worker rev `00080-h5l`; re-ingested all 8 docs (3 quota-429 recoveries) → **100% page coverage (185/185, 1,379 chunks)**.
- **Final eval: Recall@5 1.000 · Page-Recall@5 0.740 · MRR 0.667 · P95 561ms** (avg 478). scanned_lookup page-recall 0.143 → **0.857**.

### Phase H — Language findings (empirical, live-tested)
Hindi query → Hindi doc: **works** (top-3). English query → Hindi doc: **fails** (doc_004 absent from top-5, even though the doc contains English glosses). Hinglish with English keywords: partial (rank 3, carried by English tokens). Pure romanized Hindi ("pashupalan…"): **fails**. Cause: BM25 can't cross scripts; text-embedding-004 empirically doesn't bridge; romanized matches neither script. Synthesis (Gemini) is fine cross-lingually — retrieval is the bottleneck. Fix queued: dual-query generation.

## 4. Latest benchmark (the number to beat)

| Metric | Value | Notes |
|---|---|---|
| Recall@5 | **1.000** | perfect, all types |
| Page-Recall@5 | **0.740** | per-type: direct 0.80 · hindi 0.667 · multi_hop 0.625 · scanned 0.857 · short_ambiguous 0.473 · table 1.000 |
| MRR | **0.667** | page-level |
| Latency | P95 561ms / avg 478ms | budget 500ms P95; slightly over on last run |
| Corpus | 185/185 pages indexed, 1,379 chunks | first full-coverage state |

Journey from session start (broken instrument): PageRec 0.320→0.740, MRR 0.262→0.667, P95 2,934→~500ms. History of every intermediate state is in the CONTEXT.md session log and git log.

**Weak cells now = page-level precision**: short_ambiguous 0.47, hindi 0.67, multi_hop 0.63 — all three point at VLM mega-chunks (pipeline #2) as the next lever.

## 5. Stage ledger

**Original 8-stage plan:** S0 ✅ · S1 ✅ · S2 ✅ (built+swept; production-off by data) · S3 ✅ · S5 ✅ · S7 🔶 (CONTEXT.md current; ph6.md checkboxes not updated) · **S4 ❌ frontend ladder** · **S6 ❌ Phase 6.1–6.4**.
**Measurement/observability workstream:** ✅ complete.
**Current 6-item pipeline:** #1 page-level VLM fallback ✅ · #2 VLM chunking ❌ · #3 cross-lingual dual-query ❌ · #4 eval-set growth ❌ · #5 S4 frontend ❌ · #6 S6 memory ❌.
**Parked:** reranker re-sweep after chunking lands; Qdrant VM snapshots/backup; distributed (Firestore) rate limiter; 3072-d `gemini-embedding-001` (explicitly post-MVP, needs full re-embed); line-level bboxes.

## 6. Remaining pipeline — exactly what to do

### #2 VLM chunking (next; the page-precision lever)
Split VLM single-chunks (the 131K table, multi-K full-page OCRs) at sensible boundaries. **Spec settled with the user:** table markdown splits at ROW-GROUP boundaries sized to the token budget, with the **header row + caption repeated in every sub-chunk** (else rows lose column meaning); keep bbox/page/citation metadata; interacts with `page_level` (only the full-page bbox case stays page_level). Files: `services/common/ingestion/chunker.py` (`chunk_routed`'s `_VLM_SINGLE_CHUNK` branch), tests in `tests/test_chunker.py`. Acceptance: `scanned_lookup`/`vlm_table` page-recall + MRR on the fixed golden set; needs one re-ingest (ask first). After it ships: **reranker re-sweep** (`RERANK_BLEND` candidates 0.3/0.5) — first fair test.

### #3 Cross-lingual dual-query
Gate: detect script mismatch (Latin query + Devanagari-dominant corpus, and romanized-Hindi detection). Flash-Lite emits Hindi + English variants; run 2–3 searches; merge via existing RRF. Files: `services/common/retrieval/search.py` (next to `_needs_rewrite`), new method on `ModelProvider` mirroring `rewrite_query` (`models/base.py`, `vertex.py`, `mock.py`), `retrieval/hindi.py` (`contains_devanagari`). Cheap; can precede #2 if desired.

### #4 Eval-set growth (stratified new 50; 50 tune / 50 held-out)
Targets: scanned_lookup 7→20, hindi_lookup 3→15, multi_hop 10→20, strong cells 10–15 each; **stratify the split too**. Rules in `label_adjudication_guide.md` (human authors from raw PDFs; labels read off the PDF viewer; LLM may VERIFY answers but never AUTHOR queries; `golden_heldout.json` kept out of repo until validation milestone; harness gets `--split` flag so held-out is never glanced at). Tooling to build: labeling worksheet (show page text, record query+labels). Existing verification tools: `scripts/label_audit.py`, `scripts/examine_flags.py`. Deliberately LAST among retrieval items so queries are authored against a settled corpus.

### #5 S4 frontend highlight ladder (repo `D:\iris-frontend`)
`bboxToViewportRect()` in `lib/pdf/client.ts` (denormalize against `page.view` CropBox → `viewport.convertToViewportRectangle()` — fixes rotation + CropBox drift in one util; replaces the naive `bbox × canvas` math in `BboxOverlay.tsx`); `findTextQuads()` from `getTextContent()` item transforms; ladder in `PdfPanel.tsx`: (1) `page_level` metadata → page jump only, (2) bbox AND text-quads intersect → bbox overlay, (3) bbox misses text → render text quads instead, (4) no match → page jump + note; zero-citation footer in ChatPanel/MessageBubble; `page_level` in `lib/api/schemas.ts` Citation type. Local: vitest (add if absent) + Playwright. NOTE: `page_level` is already emitted by the backend for full-page chunks — the frontend just doesn't consume it yet.

### #6 S6 Phase 6.1–6.4 (ACTIONPLAN.md ~lines 425–450)
6.1 persist per-session history in Firestore (`tenants/{t}/sessions/{id}/messages`), write on `/query`; 6.2 ✅ exists (`rewrite_query`); 6.3 `/query` loads sliding window (N=6) server-side when `session_id` present (server-wins over client history); 6.4 `rewrite_ms` logging + `max_output_tokens≈256` on the Flash-Lite rewrite (target <300ms, <$0.001); 6.6 >15 turns → 2-sentence running `summary` on the session doc + last 2 raw messages (<200 tokens). Acceptance: Tests 6-A (≥90% resolution/5-turn), 6-B (persist across reload), 6-C (latency/cost), 6-D (gate bypass precision).

## 7. Gotchas & caveats (hard-won — read twice)

**Tooling/environment (this Windows machine):**
- Python venv: `D:/iris/.venv/Scripts/python.exe`. Tests: `./.venv/Scripts/python.exe -m pytest tests/ -q` excluding `test_qdrant_live.py`, `test_vertex_live.py`, `test_docling_integration.py`, `test_docling_large.py`, `test_docling_pipeline.py` (slow/live-gated). Full suite ≈ 242 pass in ~4.5 min; Docling integration +16 in ~3.5 min.
- **The Read tool's "file unchanged" cache LIED once** (parser.py had changed) — verify current file state with `sed -n`/`grep` before editing anything the user may have touched.
- `scripts/deploy.sh` bash is unreliable on Windows — use manual `gcloud builds submit --config=services/<svc>/cloudbuild.yaml --project=naturepivot-rag --region=asia-south1 --substitutions=_REPO=asia-south1-docker.pkg.dev/naturepivot-rag/iris .` then `gcloud run deploy …` (copy flags from ci.yml/deploy.sh). Worker build ≈ 10–11 min; api ≈ 2 min.
- Heredoc `python - <<EOF` is denied by the harness; use a script file or `python -c`.
- Windows grep emits `\r` artifacts that corrupt args piped into scripts (broke one recovery run — quote/clean args).
- Eval harness needs `EVAL_USER_PASSWORD='EvalPass!2026x'` in the SHELL env (read at import). Firebase API key comes from secret `FIREBASE_CONFIG`.
- **GitHub Actions CI HAS STALLED** (as of 2026-08-23): last 3 pushes produced no builds; worker deployed manually (rev `00080-h5l`). User is checking the Actions tab (suspect WIF auth/quota). Until fixed: deploy manually, and note CI would redeploy with `ci.yml` envs on next working push (they now match live).
- A graphify hook auto-rebuilds `graphify-out/` on every commit (harmless; commit the artifacts).
- `eval_report_phase2.json` is regenerated by every eval run (not committed).
- A 3-day reminder automation for the adjudication queue exists in THIS ZCode session's workspace (`automation-9a502496`) — it does NOT transfer to a new agent; the queue it watched is now resolved, so it's moot.

**GCP:**
- `--set-env-vars` / `--env-vars-file` **REPLACE the entire env set** — always `gcloud run services describe <svc> --format="value(spec.template.spec.containers[0].env)"` first and merge. Live env now includes `CORS_ALLOWED_ORIGINS` (currently only the vercel origin — user intends the 4-origin list once the `iris.procambrian.ai` CNAME lands; set the GitHub repo var, don't bake the fallback), `INGEST_URL`, `INGEST_SA`, `RERANK_LOCATION=global`, `CHUNK_TARGET_TOKENS=256`, `BM25_HINDI_ENABLED=1`.
- ingestion-worker is `--no-allow-unauthenticated`; call it with `gcloud auth print-identity-token --impersonate-service-account=ingestion-worker-sa@… --audiences=<url>` (a plain user token 401s).
- Both URL styles work: `…-zzdrfa3kqa-el.a.run.app` (legacy) and `…734211820392.asia-south1.run.app` — env vars point at the legacy one.
- Vertex trial quota: re-ingest upload-triggers hit 429 storms — recover with `scripts/round_a_recover.py <doc_ids>` (direct worker /ingest, 75s backoff). Tenant rate limit 30/min fixed window (per instance) — the eval harness already waits it out; don't remove that retry.
- Ranking API: needs `discoveryengine.googleapis.com` enabled + **any** Discovery Engine role (even viewer) on the calling SA. Returns records WITH scores. Per-record limit 1024 tokens (v004); we cap at `RERANK_MAX_CHARS=3500`.
- Cloud Logging quirks: python `logger` output lands in `textPayload` with an `LEVEL:name:message` prefix and **`extra={}` fields are NOT rendered**; prefer `--freshness=` over timestamp filters; log queries sample/limit aggressively — for canary results read via scheduler response or the metric.
- Canary function IAM needs BOTH `roles/cloudfunctions.invoker` AND `roles/run.invoker` on the caller SA.
- `wait_for_ingestion` (eval harness) returns as soon as every doc has >0 chunks — poll doc-status for STABLE counts (3 identical samples) before evaluating.
- Docling parses per-page single-page PDFs in the worker (page split before Pub/Sub fan-out); the doc hash-cache is Qdrant-based (`get_cached_chunks`) so re-ingest requires deleting the doc's points (cascading `DELETE /documents/{id}` also deletes the GCS blob — always re-upload the local `trueassort/doc_XXX.pdf` after, via `/documents/upload`).

**Domain knowledge:**
- VLM outputs (tables/pictures/full-page OCR) are **single chunks by frozen design** and bypass `CHUNK_TARGET_TOKENS` — that's why 256-token chunking barely moved corpus stats and why VLM chunking is pipeline #2.
- Chunk-length reality (live): `docling_text` ≤996 chars; `vlm_full_page` ≤3,831 (median 1,614); `vlm_table` ≤131K (median 1,909); `vlm_picture` ≤1,505.
- Corpus: 8 golden docs in `trueassort/` (doc_001/002/008 + parts of others are scanned; doc_003/006/007 digital with text layers; doc_007 is the 84-page XBRL gazette with non-uniform printed page numbers).
- Golden set history: pre-audit backup at `goldendataset.pre-audit-backup.json`; conventions + the printed-vs-viewer saga in `label_adjudication_guide.md` (STATUS: RESOLVED; the guide stays as the rulebook for authoring the new 50).
- Cross-lingual: see Phase H — dense doesn't bridge English↔Hindi here, BM25 can't cross scripts.

## 8. Key files map (for the next agent)

| Area | Files |
|---|---|
| Retrieval core | `services/common/retrieval/search.py` (orchestrator), `rrf.py` (+`fuse_rerank_scores`), `diversity.py`, `bm25.py`, `hindi.py`, `models.py`, `synthesis.py` |
| Ingestion | `services/common/ingestion/main.py` (page handler + zero-element fallback), `parser.py` (bbox), `chunker.py` (token budget, page_level, VLM single-chunks), `vlm_router.py` (signals, VLM calls), `store.py` (Qdrant/Memory), `pdf_splitter.py`, `preflight.py` |
| Models | `services/common/models/base.py` (ModelProvider, embed_query, rerank), `vertex.py` (Ranking API rerank, embed task types), `mock.py`, `gpu.py` |
| API | `services/retrieval_api/app.py` (/search, /query + parent-page expansion + RERANK_BLEND env, sessions, upload, view-url) |
| Canary | `services/canary/main.py`, scheduler job `iris-canary-job`, metric `iris_canary_failures` |
| Eval & measurement | `scripts/eval_phase2.py` (+`--rerank-sweep`), `label_audit.py`, `examine_flags.py`, `fix_golden_pages.py`, `round_a_reingest.py`, `round_a_recover.py`, `goldendataset.json`, `eval_report_phase2.json`, `label_adjudication_guide.md` |
| Deploy/CI | `.github/workflows/ci.yml` (STALLED — see gotchas), `scripts/deploy.sh`, `ingestion-worker-env.yaml` (deploy env reference) |
| Frontend (separate repo) | `D:\iris-frontend`: `lib/pdf/client.ts`, `app/(app)/chat/components/{BboxOverlay,PdfPanel,ChatPanel}.tsx`, `lib/api/schemas.ts` |
| Docs | `CONTEXT.md` (living memory — append session bullets), `ph6.md` (original plan), `ACTIONPLAN.md` (Phase 6 defs), `SRS.md`, `BENCHMARK.md` |

## 9. Live state right now

- **Worker** `ingestion-worker-00080-h5l` (fallback code, `CHUNK_TARGET_TOKENS=256`, `BM25_HINDI_ENABLED=1`); **api** `retrieval-api-00025-42s` (`RERANK_LOCATION=global`, `RERANK_BLEND` unset, Hindi on). Canary live every 15 min, alert armed (user configured).
- Corpus fully re-ingested 2026-08-23: 185/185 pages, 1,379 chunks, `test-tenant`.
- Git `main` = `f0a5a6c`, clean, pushed. ~30 commits this session.
- User's outstanding personal items: check the stalled GitHub Actions; CORS repo var before the CNAME lands; occasional frontend highlight eyeball.

## 10. Suggested first moves for the receiving agent

1. Read `CONTEXT.md`, this file, `label_adjudication_guide.md`.
2. Run the local suite (command in §7) to confirm 242-pass baseline.
3. Start pipeline #2 (VLM chunking) — spec in §6. Local tests first; the one re-ingest + eval needs the user's explicit go-ahead (they always answer).
4. When in doubt on intent, re-read §2 (the user's rules) — they were set explicitly and the user enforces them.
