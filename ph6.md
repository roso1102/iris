# IRIS Roadmap: Phase 6+ Execution Plan with Citation/Bbox/Rerank Fixes

## Goal

Produce a coherent, phase-aligned execution order from **Phase 6.0 onward** in `ACTIONPLAN.md`,
folding in the A–G fixes (bbox Y-flip, text-search fallback, zero-citation UX, regex citation
interceptor, tiny-refs mapper, cross-encoder reranker, CoT grounding prompt) and a concrete
**pull-forward** decision on Phases 9/10/12/16. The result is a single source-of-truth plan for
what to build next, in what phase, and why.

## Background (verified facts)

- **Phase 5.0** is the current MVP-launch gate; frontend is deployed to Vercel
  (`https://iris-frontend-steel-nine.vercel.app`), `iris.procambrian.ai` pending CNAME at Hostinger.
- Backend MMR is 0.262 / Page-Recall@5 0.320 — the driver of weak/zero citations (not a frontend bug).
- **bbox is ALREADY normalized to 0–1** in `parser.py::_bbox_of_items` (lines 244–254), but the Y-axis
  is **NOT flipped** — Docling v2 uses `coord_origin=BOTTOMLEFT` (line 215), frontend `BboxOverlay`
  assumes TOPLEFT. Result: highlights are vertically mirrored/off-target until re-ingested.
- `rewrite_query()` (SLM via Flash-Lite) **already exists** on `ModelProvider` and is wired into
  `deep_search` only; **not** in `standard_search` — the "what does it do?" follow-up fails because
  the raw pronoun query hits Qdrant.
- `validate_citations()` already drops hallucinated chunk_ids server-side; empty-citations is a
  legitimate signal the UI currently renders as if broken.

## Current ACTIONPLAN phase map (post-Phase 5)

| Phase | Title | Status |
|---|---|---|
| 6.0 | Conversational Memory + SLM Query Rewrite | Post-MVP / Optional |
| 7.0 | Trial/Freemium | Post-MVP |
| 8.0 | Rephraser & HyDE | Post-MVP |
| 9.0 | Citation & Bbox Management Layer | Post-MVP — **prereq for 10/11** |
| 10.0 | Citation Map & Graph (ingestion-time) | Post-MVP — **depends on 9.0** |
| 11.0 | Graph-Aware Retrieval | Post-MVP — **depends on 10.0** |
| 12.0 | Neural Reranking Upgrade | Post-MVP |
| 13.0 | Context Compression | Post-MVP |
| 14.0 | MoA Synthesis | Post-MVP |
| 15.0 | GPU Swap-In | Blocked on quota |
| 16.0 | Enterprise Hardening | Ongoing, 20+ clients |

## Pull-forward decision

- **PULL FORWARD Phase 9.0 → do immediately after Phase 5.0 finishes.** It is the direct fix for the
  live highlight/citation bugs and is the correctness layer 10/11 sit on. Medium effort, well-scoped.
- **PULL FORWARD Phase 12.0 → sequence immediately after 9.0** (not ahead of it). Reranking needs the
  clean bboxes from 9.0's re-ingest to measure the MRR lift without noise, and doing 9→12 together
  avoids a second re-ingest.
- **DO NOT pull forward Phase 10.0** — graph on top of incorrect citations would cement bad data. Gate it behind 9.0.
- **DO NOT pull forward Phase 16.0** — zero-trust ingress lockdown would block the public demo/testing
  path and is unrelated to citations/MRR. Leave at the end (20+ clients / hardening).

Recommended collapsed order: **Phase 5 (finish) → 9.0 → 12.0 → 6.0 → 10.0 → 11.0 → 13/14 → 16.0.**

## Execution plan (phase by phase)

### Phase 6.0 — Conversational Memory + SLM Query Rewrite (partial now, rest after 9/12)
- **6.0a (do now, small): wire `rewrite_query()` into `standard_search`** in
  `services/common/retrieval/search.py` when `history` is non-empty (mirror `deep_search`), so
  follow-ups like "what does it do?" become self-contained before Qdrant. Reuse existing
  `provider.rewrite_query` + Flash-Lite.
- **6.5 (do now): pronoun heuristic gate** — skip the rewriter when no `it/this/that/former/latter/above/previous`
  is present (zero-cost, saves ~150ms/call).
- **6.1/6.2/6.3/6.4/6.6 (defer to after 9/12):** full Firestore history persistence, sub-300ms budget
  measurement, 15-turn topic-summary compression. These belong after the retrieval/citation quality
  layers are stable so rewrite context is worth persisting.

### Phase 9.0 — Citation & Bbox Management (PULL FORWARD; the correctness gate)
Covers fixes **C, A, B, E, D, G** — all citation/bbox work.
- **9.0-C (bbox Y-flip):** in `services/common/ingestion/parser.py::_bbox_of_items`, after normalizing
  to 0–1, apply `top_norm = 1 - bottom_orig/~`, `bottom_norm = 1 - top_orig`, since Docling origin is
  BOTTOMLEFT. Store `[left, top, right, bottom]` in TOPLEFT 0–1 coords. **Re-ingest all golden docs**,
  then re-verify highlights land on the correct text.
- **9.0-A (text-search fallback):** in `lib/pdf/client.ts` / `PdfPanel.tsx`, normalize the search
  target (strip `\s+`→space, trim), take a short prefix (~40–60 chars) from `text_snippet` before
  `findTextInPage`. Prevents newline/hyphen/500-char breakage.
- **9.0-B (zero-citations state):** in `MessageBubble`/`ChatPanel`, when `citations.length === 0`, hide
  pills and render a subtle gray footer: *"Answer synthesized from general knowledge (no direct
  document citations found)."*
- **9.0-E (regex citation interceptor):** in `validate_citations`, normalize malformed arrays
  (`[1, 2]`→`[1] [2]`, also ranges), drop out-of-map refs silently.
- **9.0-D (tiny-refs consistency):** in `_build_synthesis_context`, the injected source labels
  (`[CHUNK i]`) are fine, but ensure the model's structured `chunk_id` output maps 1:1 back through
  `source_chunks`. Add a unit test asserting no valid citation is dropped due to mapping mismatch.
- **9.0-G (CoT grounding prompt) — optional, A/B after 9.0-C:** add a `<scratchpad>` of verbatim
  quotes + refs before the final answer. Watch latency/cost and structured-output compatibility.

### Phase 12.0 — Neural Reranking Upgrade (PULL FORWARD after 9.0; the MRR lever)
Covers fix **F**.
- **12.1 (reranker):** in the search orchestrator, fetch `limit*3` RRF candidates, run Vertex AI
  Ranking API (or `rerank-4-fast`), blend `final = 0.3*orig + 0.7*rerank` — **validate the ratio** on
  the golden eval, don't hardcode blindly.
- Re-run golden eval; assert MRR ≥ 0.65, Page-Recall@5 ≥ 0.80, latency overhead < 400ms (Test 12-A/B/C).

### Phase 10.0 → 11.0 — Graph layers (stay in place, after 9.0)
- No pull-forward. Build only after the Citation Registry (9.0) and clean bboxes exist.

### Phase 13/14/15/16 — stay in place
- 13 (context compression), 14 (MoA) remain post-MVP; 15 (GPU) blocked; 16 (enterprise) stays last.

## Files to touch
- `services/common/ingestion/parser.py` — bbox Y-flip (9.0-C)
- `services/common/retrieval/search.py` — standard_search rewrite wiring (6.0a)
- `services/common/models/vertex.py` — prompt consistency (9.0-D/G), Flash-Lite already present
- `services/retrieval_api/app.py` — `_build_synthesis_context` (9.0-D)
- `services/common/retrieval/synthesis.py` — regex interceptor (9.0-E)
- `services/common/retrieval/**` — reranker integration (12.1/F)
- `D:\iris-frontend\lib\pdf\client.ts` — search fallback normalization (9.0-A)
- `D:\iris-frontend\app\(app)\chat\components\ChatPanel.tsx` — zero-citation UX (9.0-B)

## Verification
- bbox: after 9.0-C re-ingest, click a citation → highlight sits on the exact source text.
- rewrite: "what does it do?" after an SDRF answer resolves to SDRF context (Test 6-A style).
- citations: malformed `[1,2]` no longer crashes validator; zero-citation answers render the gray footer.
- MRR: golden eval ≥ 0.65 after 12.1 (Test 12-A) with < 400ms overhead (Test 12-C).

## Open decision
- Confirm the exact `final = 0.3*orig + 0.7*rerank` ratio (12.1) empirically vs. a sweep; align to
  Plan-vs-ACTIONPLAN note that reranking was originally deferred to 12.0 — this plan intentionally pulls it
  forward, which is a deliberate deviation to be approved.