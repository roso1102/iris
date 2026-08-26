# IRIS — Phased Action Plan

**Format:** Every phase lists Scope → Tasks → Services Touched → Deliverables → Benchmarks & Testing → Exit Criteria.
A phase is not considered "done" until its Exit Criteria are met — not just its tasks completed.

**Total time to MVP (end of Phase 5.0): ~6–8 weeks.**
**MVP boundary is explicitly marked below.**

---

## Deployment & Containerization Strategy

**We containerize per *service*, not per *phase*.** Phases are development milestones; they don't map cleanly to standalone containers, and forcing that mapping would slow delivery down rather than help it.

### The two containers
| Container | Cloud Run Service | Grows across phases |
|---|---|---|
| `ingestion-worker` | Ingestion Worker | 1.0, 10.0 (graph extraction) |
| `retrieval-api` | Retrieval API | 2.0, 3.0, 6.0, 8.0, 9.0, 11.0, 12.0, 13.0, 14.0 |

### How per-phase checkpointing still works without per-phase containers
- Each phase's code lands inside the relevant service's codebase behind a feature flag.
- On completion of a phase, CI tags the commit (e.g., `v9.0-citation-registry`) and builds/deploys that image to a **staging Cloud Run revision**.
- Phase benchmarks (see each phase's "Benchmarks & Testing" section below) are run against that staging revision **before** merging to the `main`/production revision.
- Cloud Run's built-in traffic-splitting lets the new phase's revision run side-by-side with the last stable revision, so A/B benchmark comparisons (e.g., Phase 8.0's HyDE recall lift, Phase 12.0's rerank precision lift) are measured directly against a live baseline, not a guess.
- This gives a deployed, independently-testable artifact at every phase boundary — the goal of "per-phase Docker" — without fragmenting two logical services into dozens of containers.

### Why this doesn't delay stage-by-stage checking
Testing a phase in true isolation (e.g., testing Phase 9.0's citation validation without Phase 2.0's retrieval and Phase 3.0's synthesis running) would be artificial — Phase 9.0 exists to validate what those earlier phases produce. Tag-and-revision staging gives the same checkpoint discipline as separate containers would, without breaking the services apart in a way that makes integration testing harder later.

---

## Phase 0.0 — Foundations & Safety Nets

### Scope
Set up the GCP project, billing protection, identity scaffolding, and CI/CD — before any product code is written. This phase exists specifically to protect the $300 credit from day one.

### Tasks
- 0.1: Create GCP project, enable required APIs (Cloud Run, Pub/Sub, Firestore, Vertex AI, Secret Manager, GCS).
- 0.2: Set a GCP Billing Budget with alert thresholds (e.g., 50%, 80%, 100% of a $10–15/day cap).
- 0.3: Build the **Billing Budget Interceptor**: Billing Alert → Pub/Sub topic → Cloud Function that sets `max-instances=0` on the Ingestion Worker when the cap is breached.
- 0.4: Create least-privilege IAM service accounts: one for Ingestion Worker (write-only GCS + Qdrant), one for Retrieval API (read-only Qdrant, call Vertex AI).
- 0.5: Provision a VPC with Private Service Connect boundary for Qdrant and Firestore.
- 0.6: Set up Secret Manager for API keys and the `MODEL_BACKEND` config flag.
- 0.7: Initialize Firebase project and Firebase Authentication.
- 0.8: Scaffold the repository structure (see `README.md`) and CI pipeline (lint, test, deploy on merge).
- 0.9: Write base Terraform (or equivalent IaC) for all of the above, so environments are reproducible.

### Services Touched
GCP Billing, IAM, VPC, Secret Manager, Cloud Functions, Pub/Sub, Firebase Auth, GitHub Actions (or equivalent CI).

### Deliverables
- A GCP project where it is **provably impossible** to spend beyond the daily cap unnoticed.
- Empty but deployable Cloud Run services (hello-world level) for Ingestion Worker and Retrieval API.

### Benchmarks & Testing
- **Test 0-A (Kill Switch):** Manually trigger a simulated billing alert (or lower the cap temporarily) and confirm the Ingestion Worker's `max-instances` is forced to 0 within 5 minutes.
- **Test 0-B (IAM Boundary):** Attempt to call Vertex AI using the Ingestion Worker's service account credentials — this MUST fail (least-privilege verified).
- **Test 0-C (CI):** A trivial commit triggers the CI pipeline and successfully deploys a "hello world" container to Cloud Run.
- **Benchmark:** Cold-start empty Cloud Run service responds to a health check in < 3 seconds.

### Exit Criteria
✅ Kill switch demonstrably works. ✅ IAM least-privilege verified. ✅ CI/CD deploys successfully. ✅ No product code has been written yet without these protections in place.

**Est. Effort:** 1 week (15–20 hrs)

---

## Phase 0.1 — Model Provider Abstraction Scaffold

### Scope
Before building any real ingestion or retrieval logic, establish the `ModelProvider` interface that all future model calls must go through. This is what makes the later GPU swap-in (Phase 10.0) a config change instead of a rewrite.

### Tasks
- Define abstract interfaces: `embed(text) -> vector`, `extract_table(image) -> markdown`, `synthesize(context, query) -> structured_answer`, `ocr(pdf_page) -> text+bbox`.
- Implement `VertexAIProvider` (the only active implementation for MVP).
- Stub `SelfHostedGPUProvider` ✅ (unimplemented, dormant, but present in code with clear TODOs).
- Wire provider selection via `MODEL_BACKEND` env var read from Secret Manager.

### Services Touched
Vertex AI (Gemini), Secret Manager.

### Deliverables
A working, testable `ModelProvider` interface with one live backend (Vertex AI) and one dormant stub.

### Benchmarks & Testing
- **Test 0.1-A:** Swap `MODEL_BACKEND` env var between `vertex` and a mock provider in a test environment; confirm the calling code requires zero changes.
- **Test 0.1-B:** Unit tests cover all four interface methods against the Vertex AI provider with mocked API responses.

### Exit Criteria
✅ No code outside the provider module imports a model SDK directly. ✅ Provider swap verified via config only.

**Est. Effort:** 2–3 days

---

## Phase 1.0 — Core Ingestion Pipeline ✅ (complete)

### Scope
Build the document upload → parse → route → chunk → embed → store pipeline, with a page-wise VLM router that minimises Gemini Vision API calls to only the elements that genuinely require them. **Deployed and verified on Cloud Run (revision 00052-md6).**

### Tasks
- 1.1: Create tenant-prefixed GCS buckets (`gs://iris-raw-pdfs/{tenant_id}/...`) with IAM conditions. Scaffolding for `/documents/{doc_id}` cascading delete.
- 1.2: Build the pre-ingestion payload scanner (reject >500 pages, corrupt PDF trailers) before queuing.
- 1.3: Implement the Ingestion Worker on Cloud Run, triggered via Pub/Sub on new upload events.
- 1.4: Integrate Docling for layout-aware parsing — every element (text block, table, figure) comes out with its normalised `[left, top, right, bottom]` bounding-box coordinates and an element-type label (`Text`, `Table`, `Picture`, `Caption`, etc.).
- 1.5: Implement the **Page-Wise VLM Router** using a **4-signal composite decision tree** with **parallel page-level dispatch**. PDFs are split into single-page blobs, each published as a separate Pub/Sub message. Cloud Run auto-scales to max-instances=10, processing pages concurrently. A 35-page doc drops from ~8 min sequential to ~50s wall time.
  - Preflight runs once per document (page count, corruption check).
  - Per-page processing: Docling parse → 4-signal router → chunk → embed → write to Qdrant with `page_number`.
  - `GET /status/{doc_id}` returns live progress (`completed_pages: 12/35, chunks: 45`).
  - SHA256 doc cache skips re-ingestion of previously processed documents.
  - `gemini-flash-lite` used for table extraction (2× faster, negligible quality difference on structured tables).
  - Streaming writes: chunks land in Qdrant as each page finishes — no waiting for full doc.

  **Signal 1 — Structural Element Classification (Docling layout labels):**
  | Element Type | Route |
  |---|---|
  | `Table` | **Gemini Vision** on cropped table bbox region |
  | `Picture` / `Figure` | **Gemini Vision** on cropped figure bbox region |
  | `Text` / `Paragraph` / `Header` | Proceed to Signals 2–4 |

  **Signal 2 — Valid Word Ratio (Garbage OCR Detection):**
  Compute the fraction of extracted words that are valid (real dictionary words, numbers, standard punctuation). If < 75% of words are valid → garbled OCR / unmapped font encoding → route to full-page Gemini Vision. *Catches KrutiDev/DevLys pages that Docling partially attempts but produces gibberish on.*

  **Signal 3 — Text Area Coverage Ratio (Image-Heavy Page Detection):**
  Compute: `coverage = sum(bbox areas of all text blocks) / total page area`. If coverage < 0.15 AND extracted char count < 300 → page is visually dominated by an untagged image/diagram → route to full-page Gemini Vision. *Catches cover pages, infographic pages, and scanned-over-printed pages where Docling picks up a caption strip but misses the visual content.*

  **Signal 4 — OCR Confidence Score (Unreliable Extraction Gate):**
  If Docling exposes per-word/per-block confidence scores (or GCP Document AI Layout Parser is used as a fallback — see GCP Note below), and the page-level mean confidence is < 0.70 → route to full-page Gemini Vision.

  **All signals green → Docling text used directly — zero API cost.**

  ```python
  def route_page(page_layout) -> RouteDecision:
      # Signal 1 — structural elements
      if page_layout.has_tables or page_layout.has_figures:
          return RouteDecision.CROP_VLM
      # Signal 2 — valid word ratio
      if valid_word_ratio(page_layout.text) < 0.75:
          return RouteDecision.FULL_PAGE_VLM
      # Signal 3 — area coverage
      coverage = sum_bbox_areas(page_layout.bboxes) / page_layout.page_area
      if coverage < 0.15 and len(page_layout.text) < 300:
          return RouteDecision.FULL_PAGE_VLM
      # Signal 4 — OCR confidence (if available)
      if page_layout.mean_ocr_confidence < 0.70:
          return RouteDecision.FULL_PAGE_VLM
      # All clear — use Docling text directly
      return RouteDecision.DOCLING_DIRECT
  ```

  > **GCP Note — Document AI Layout Parser as Signal 4 Source:**
  > GCP's **Cloud Document AI** (`LAYOUT_PARSER_PROCESSOR`) natively returns per-block OCR confidence scores in its structured output. For pages where Docling signals are ambiguous (Signals 2 & 3 borderline), we can optionally route through Document AI as a higher-confidence arbiter before committing to a Gemini Vision call. This is a call-once-per-ambiguous-page pattern — not a default — to avoid double API costs on clean pages. Evaluate at Phase 5.0 production hardening.

  *Rationale: Gemini Vision reads rendered pixels, so KrutiDev/DevLys legacy Hindi font encoding and scanned Devanagari text are handled transparently — no custom font decoder or RapidOCR pipeline required. VLM is only invoked where the composite router signals indicate Docling's text extraction is absent, low-quality, or structurally insufficient.*

- 1.6: Chunk routed content. Text blocks: sentence-boundary chunking at ~512 tokens. VLM outputs: treated as single chunks with the source element’s bbox attached.
- 1.7: Embed each chunk via `ModelProvider.embed()` → **Vertex AI `text-embedding-004`** (768-d, multilingual). No local ONNX model required.
- 1.8: Configure the Pub/Sub subscription with max 3 delivery attempts, routing failures to a DLQ topic.
- 1.9: Write parsed, embedded chunks (with bbox + `tenant_id` + `page_number` + `element_type` metadata) to Qdrant.
- 1.10: Build an internal **Chunk Visualization / QA view** — an admin-only page that overlays every extracted chunk’s bounding box on the source PDF page, so a human can visually sanity-check Docling’s parsing and the VLM router’s decisions on a new or unusual document type before it goes live.

### Services Touched
GCS, Pub/Sub, Cloud Run, Docling, Vertex AI (Gemini Vision + `text-embedding-004` via ModelProvider), Qdrant (write path).

### Deliverables
A working pipeline: PDF in → page-wise routed, bbox-tagged, embedded chunks out.

### Benchmarks & Testing
- **Test 1-A (Happy Path):** Upload a 50-page sample gazette PDF; confirm all pages processed concurrently. Full doc completes in < 2 min wall time (NFR-1 target). Chunks stream into Qdrant incrementally.
- **Test 1-B (Oversized Rejection):** Upload a 600-page PDF; confirm it is rejected pre-queue with a clear error, never entering the pipeline.
- **Test 1-C (Corrupt File):** Upload a deliberately corrupted PDF; confirm it fails gracefully and lands in the DLQ after 3 attempts — not an infinite retry loop.
- **Test 1-D (VLM Router — Table):** Upload a document containing a known complex multi-column table; confirm the router triggers a Gemini Vision call for that element and the resulting chunk contains structured markdown, not scrambled text.
- **Test 1-E (VLM Router — Scanned/Garbled Page):** Upload a scanned-only page AND a KrutiDev-encoded page; confirm Signal 2 (valid word ratio < 0.75) or Signal 3 (area coverage < 0.15) triggers correctly and routes both to full-page Gemini Vision.
- **Test 1-F (VLM Router — Clean Text, No False Positives):** Upload a clean text page with 40 chars (e.g., a short title page) AND a full-text page with 200 chars; confirm the composite router sends the 200-char page to Docling direct and only escalates the 40-char title page if Signal 3 (area coverage) confirms it is image-heavy — verify via VLM call counter, no API call on pure-text title.
- **Test 1-G (Composite Router — All 4 Signals):** Build a synthetic 4-page test document: one clean text page, one garbled-OCR page (Signal 2), one image-heavy page (Signal 3), one low-confidence OCR page (Signal 4). Confirm all four route correctly.
- **Test 1-H (Bbox Accuracy):** Spot-check 10 randomly sampled chunks against the source PDF; bbox coordinates must visually align with the correct content when manually overlaid.
- **Test 1-I (Chunk Visualization QA):** Confirm the internal QA view correctly renders bbox overlays for a sample of 5 documents spanning different layouts (dense text, tables, scanned/rotated pages).
- **Benchmark:** VLM call count per 50-page document logged; typical gazette expected to trigger ≤ 20% of pages as VLM calls. Composite router must show ≤ 5% false-positive VLM escalations on clean-text pages. Ingestion cost per document tracked against daily budget cap.

### Exit Criteria
✅ Happy path works end-to-end. ✅ VLM router correctly classifies all four page types in tests. ✅ No VLM call triggered on clean text pages. ✅ Oversized and corrupt files handled safely. ✅ DLQ populated correctly on failure. ✅ Bbox accuracy manually verified.

**Est. Effort:** 2–2.5 weeks

---

## Phase 2.0 — Vector Store & Retrieval

### Scope
Stand up the production vector database and the core search + retrieval pipeline, implementing the full three-step post-retrieval processing sequence.

### Tasks
- 2.1: Provision a self-hosted Qdrant instance on a small GCE VM (e.g., `e2-small`/`e2-medium`) with Binary Quantization enabled.
- 2.2: Configure collections with `is_tenant=True` and appropriate `payload_m`/`m` settings for tenant-isolated HNSW sub-graphs.
- 2.3: Point the Ingestion Worker (Phase 1.0) at the production Qdrant instance.
- 2.4: Build the Retrieval API's `/search` endpoint supporting **hybrid search** (dense cosine vector search + BM25 full-text search) executed against the same Qdrant collection, filtered by `tenant_id` and the session's active document list.
- 2.4a: **Async Event-Loop Non-Negotiable:** Wrap all blocking `provider.embed()` gRPC network calls in `asyncio.to_thread()` inside `SearchOrchestrator` to prevent event-loop starvation under concurrent requests.
- 2.4b: **Structured Search Observability:** Emit structured JSON logs (`logger.info("search_completed", extra={...})`) capturing `latency_ms`, `mode`, `top_score`, `num_results`, and `tenant_id` to GCP Cloud Logging.
- 2.5: ✅ Implement **Reciprocal Rank Fusion (RRF)** to merge the dense and BM25 rank lists into a single coherent ordered list. RRF is rank-based and score-agnostic — it handles the incompatibility between cosine similarity scores and BM25 scores without normalisation hacks.
- 2.5a: ⚠️ **[DEFERRED to Phase 3] BM25 TF-IDF Upgrade:** Replace raw term-frequency with `rank_bm25` (pure Python) or Qdrant native sparse index to penalize statutory boilerplate words across large legal/gazette documents. (Currently using weak `hash(term)` logic).
- 2.6: ✅ Implement the **Diversity / Dedup pass** on top of the RRF-fused list. This step applies a `0.5×` score multiplier to any chunk whose `source_file` has already appeared in the current top-K window. This prevents a single highly-relevant source document from flooding all top-K slots and starving synthesis of breadth.
- 2.7: ✅ Wire the **Standard Mode** query path: embed query (Vertex AI `text-embedding-004`, 768-d) → hybrid search (filtered by tenant and active session documents) → RRF → diversity pass → return top-K chunks.
- 2.8: ⚠️ **[PARTIALLY DEFERRED] Deep Search Mode** query path (user-toggled): Fetch sliding window of recent conversation history (last N messages, default N=6) from Firestore (FR-5.3) → rewrite query with SLM → generate HyDE → hybrid search → RRF → diversity pass → Vertex AI Ranking API cross-encoder rerank → return. (Note: Reranker deferred to Phase 12.0).
- 2.9: Enforce a server-side tenant filter (app-layer for now; JWT-level enforcement lands in Phase 4.0).
- 2.10: Build cascading delete backend hooks: `DELETE /documents/{doc_id}` (purges raw GCS PDF + Qdrant points with `document_id` filter) and `DELETE /sessions/{session_id}` (purges Qdrant points with `session_id` filter).

### Services Touched
GCE (Qdrant host), Cloud Run (Retrieval API), Qdrant, Vertex AI (Ranking API, `text-embedding-004`), Cloud Logging.

### Deliverables
A working, non-blocking `/search` endpoint returning tenant-scoped results processed through the full RRF → diversity → [optional rerank] pipeline with structured Cloud Logging.

### Benchmarks & Testing
- **Test 2-A (Relevance):** Run a fixed set of 20 known question/answer pairs against a test corpus; measure retrieval precision (top-5 chunk relevance) manually or via a scoring rubric.
- **Test 2-B (Tenant Filter):** Seed two test tenants with distinct documents; confirm Tenant A’s search never returns Tenant B’s chunks.
- **Test 2-C (RRF vs. single-modality):** Compare top-5 retrieval precision of hybrid+RRF against dense-only and BM25-only; hybrid must match or exceed both on the 20-question test set.
- **Test 2-D (Diversity):** Upload a corpus where one document is strongly relevant to all 20 test questions; confirm the diversity pass prevents that document from occupying > 50% of top-10 slots in results.
- **Test 2-E (Deep Search rerank lift):** For 5 ambiguous queries, confirm Deep Search mode returns a measurably better top-1 result than Standard mode (manual review).
- **Test 2-F (Latency):** Standard mode `/search` responds in < 500ms for a corpus of 10,000+ chunks (excluding cold start).
- **Benchmark:** Qdrant VM memory/CPU usage stays within the provisioned instance size under a simulated 5-tenant load.

### Exit Criteria
✅ Standard Mode path operational. ✅ Non-blocking async event loop verified. ✅ Structured logs visible in GCP Cloud Logging. ✅ RRF correctly fuses both rank lists. ✅ Tenant filter holds under test. ✅ Cascading deletes function securely. ⚠️ Diversity pass requires tuning to prevent source flooding. ⚠️ Deep Search fully operational path blocked by Phase 12.0 reranker. ⚠️ Task 2.5a (BM25) deferred.

**Est. Effort:** 1–1.5 weeks

---

## Phase 2.5 — Empirical Validation & Pipeline Hardening

### Scope
Empirically validate heuristics, validate extracted Markdown table structures, and establish data-backed benchmarks separating retrieval quality from generation quality.

### Tasks
- 2.5.1: ⚠️ **[DEFERRED] VLM Table Markdown Validation:** Implement post-extraction row/column matrix validation (`validate_table_markdown()`). Tag structural anomalies or merged cells with `confidence: low` in Qdrant payload.
- 2.5.2: **Golden Dataset Creation:** Curate a golden dataset of 50 ground-truth Q/A pairs and a 150-page labeled PDF dataset (clean text, scanned Hindi, multi-column tables).
- 2.5.3: **RAGAS Evaluation Framework:** Integrate `ragas` to evaluate **Retrieval Quality** (`Recall@5`, `ContextPrecision`) separately from **Generation Quality** (`Faithfulness`, `AnswerRelevancy`).
- 2.5.4: **HyDE & Reranker A/B Benchmarks:** Benchmark Standard vs Deep Search (HyDE + Cross-Encoder) on latency vs recall lift to verify if HyDE justifies $+400\text{ms}$ query latency.
- 2.5.5: **VLM Signal Threshold Sweep:** Sweep word ratio ($0.75$) and area coverage ($0.15$) on the labeled dataset to minimize false-positive VLM API spend.
- 2.5.7: ✅ **[DONE — Emergency Fix] BM25 Hash Determinism:** Replace Python's built-in `hash(term)` (PEP 456 randomized per process) with `mmh3` (MurmurHash3). This was a silent production failure: ingestion-worker and retrieval-api generated different sparse indices for the same word, causing every sparse search to return zero matches. `mmh3==4.*` added to both service `requirements.txt`. This is a bug fix only — it makes sparse retrieval functional without improving its quality. Full quality upgrade is Task 3.5.
- 2.5.8: ✅ **[TOOLING DONE / AUTHORING DEFERRED — Pipeline #4] Eval-Set Growth & Held-Out Harness:** Tooling complete (`scripts/label_worksheet.py` authoring worksheet and `--split` flag in `scripts/eval_phase2.py` with `golden_heldout.json` support). Expansion to 100 queries is archived/deferred post-MVP. Full 50-query golden dataset adjudicated (Rounds 1–3) with Recall@5=0.980–1.000 / Page-Recall@5=0.812.

### Services Touched
RAGAS Framework, Vertex AI, Python Test Suite.

### Deliverables
- A RAGAS automated test suite running against a 50-question golden dataset.
- Data-backed empirical threshold values for VLM signals and diversity penalty.
- Markdown table validation layer preventing silent financial/data corruption.

### Exit Criteria
✅ BM25 hash determinism fixed (Task 2.5.7 — done). ⚠️ VLM table validation deferred (Task 2.5.1). ⚠️ RAGAS suite evaluates retrieval separate from generation. ⚠️ HyDE latency vs. recall lift empirically proven. ⚠️ VLM signal thresholds backed by 150-page dataset.

**Est. Effort:** 3–4 days

---

## Phase 3.0 — LLM Synthesis Layer ✅ (complete)

### Scope
Turn retrieved chunks into a final, cited, structured answer. **Also includes the production BM25 sparse retrieval upgrade (Task 3.5), which replaces the emergency mmh3/TF fix from Phase 2.5 with a proper pre-trained sparse model.**

### Tasks
- 3.1: ✅ **[DONE]** Implement `ModelProvider.synthesize()` using Gemini Flash/Flash-Lite via Vertex AI. Structured output (`response_mime_type="application/json"` + `response_schema`), real chunk-grounded citations, thinking mode off. Verified via live `test_vertex_live.py::test_vertex_synthesis_2_5_flash` (PASSED).
- 3.2: ✅ **[DONE]** Define a Pydantic schema for structured output: `QueryRequest`/`QueryResponse` (answer + citations mapped to `doc_id`, `page_number`, `bbox`, plus `chunks_used`).
- 3.3: ✅ **[DONE]** Wire the `/query` endpoint: retrieve → synthesize → return structured response. Uses `_build_synthesis_context`, `asyncio.to_thread` for the provider call, real `latency_ms` + `chunks_used`. Mock-path test in `test_retrieval_api.py`.
- 3.4: ✅ **[DONE]** Add server-side citation validation (hallucination guard). `validate_citations()` in `services/common/retrieval/synthesis.py` drops citations whose `chunk_id` is not in the retrieved set and overwrites spatial fields (doc_id/page/bbox/snippet) from the trusted chunk. Wired into `/query`. Unit tests in `tests/test_synthesis.py` (4 passed).
- 3.5: ✅ **[DONE]** **FastEmbed BM25 Sparse Retrieval Upgrade** (replaces Phase 2.5.7 emergency fix):
  - Install `fastembed` in both service `requirements.txt`.
  - Replace `services/common/retrieval/bm25.py` entirely with Qdrant's native `fastembed.sparse.BM25` model.
  - Use the **same pinned model version** in both `ingestion-worker` (encoding chunks at write time) and `retrieval-api` (encoding queries at search time). This is the guarantee of index/query alignment — not a hash function.
  - The FastEmbed BM25 model ships with pre-trained IDF values from a large real-world corpus (MSMARCO/BEIR). This penalizes common words (including legal boilerplate like "section", "act", "notification") without requiring any corpus state at runtime.
  - **Important:** After deploying the new model, the existing Qdrant `iris_chunks_v2` sparse vectors are stale (encoded with the old `mmh3+TF` approach). All documents must be **re-ingested** after this upgrade to rebuild sparse vectors under the new model. Plan for a re-ingest window. ✅ **Done** — wiped Qdrant, re-uploaded + re-ingested all 8 docs (doc_007: 882 chunks/84 pages).
  - **Latency cost:** ~3ms per query for BM25 encoding. Negligible vs. the 500ms budget.
  - **Memory cost:** FastEmbed BM25 IDF table is ~50–100MB loaded at startup. Acceptable within the `retrieval-api` 2GiB limit.
  - **Quality gain expected:** MRR improvement on exact-match queries (section numbers, dates, proper nouns) and reduction in boilerplate-driven false matches.

### Services Touched
Vertex AI (Gemini), Cloud Run (Retrieval API, Ingestion Worker), Qdrant (re-ingest required after Task 3.5).

### Deliverables
- A working `/query` endpoint returning a grounded, structured, cited answer.
- A production-grade sparse retrieval layer with pre-trained IDF, replacing the mmh3/TF emergency fix.

### Benchmarks & Testing
- **Test 3-A (Citation Validity):** For 30 sample questions, confirm 100% of returned citations map to a real, retrieved chunk (no hallucinated bbox references).
- **Test 3-B (Answer Quality):** Manual review of answer quality against the 20-question test set from Phase 2.0; target ≥ 90% judged "accurate and grounded."
- **Test 3-C (Latency):** End-to-end `/query` response time < 2 seconds (NFR-1), excluding cold start.
- **Test 3-D (BM25 Alignment):** After Task 3.5, verify that sparse search returns non-zero results for known exact-match queries (section numbers, named entities) — proving mmh3 hashes are no longer used.
- **Test 3-E (MRR Regression):** Re-run Tier 4 eval after Task 3.5 re-ingest. MRR must improve from Phase 2.0 baseline (0.278). Target ≥ 0.50 with FastEmbed BM25.
- **Benchmark:** Token cost per query logged; confirm Flash-Lite usage stays within projected cost matrix (see `SRS.md` §Cost).

### Exit Criteria
✅ Citation validity = 100% on test set. ✅ Answer quality ≥ 90% on manual review. ✅ Latency benchmark met. ✅ Sparse retrieval produces non-zero matches for exact-match queries (Task 3.5 verified). ✅ MRR baseline logged (0.251).

**Est. Effort:** 1–1.5 weeks

---

## Phase 3.5 — Retrieval Precision & Citation Quality Hardening (Lite) ✅ (complete)

### Scope
Execute high-leverage software fixes on chunking and evaluation instrumentation before entering Auth/Frontend. Strictly defers open-ended ML research (Cross-Encoders, Canonical Duplicate graphs) to Phase 12.0.

### Tasks
- 3.5.1: ✅ **[DONE]** **Page-Boundary Strict Chunking:** Update `ingestion-worker` chunking logic to strictly prevent chunks from crossing page boundaries. If text spans across pages, split the chunk at the boundary so every chunk has an unambiguous single `page_number`. Eliminates off-by-one citation jumping in the PDF viewer. Implemented via parser multi-page `prov` charspan split + page-first chunker (commit 6ce0693).
- 3.5.2: ✅ **[DONE]** **Evaluation Harness Latency Disambiguation:** Update `scripts/eval_phase2.py` to record server-reported `latency_ms` from the API response payload instead of client-side wall clock (which was inflated by 2-4s due to per-query `gcloud auth print-identity-token` subprocess execution). Implemented (server latency_ms + cached token, commits 4ca30bd/6ce0693).
- 3.5.3: ✅ **[DONE]** **Cloud Run Scaling Tuning:** Configure `ingestion-worker` `--min-instances=0` (saves ~₹6,000/mo, background cold starts do not affect user) and `retrieval-api` `--min-instances=1` (costs ~₹2,500/mo, eliminates 14.5s cold start on search/query path). Deployed live (retrieval-api minScale=1, ingestion-worker scale-to-zero).

### Services Touched
Cloud Run (Ingestion Worker, Retrieval API), Docling chunk parser, Eval harness.

### Deliverables
- Clean single-page chunk attribution for accurate PDF citation overlay.
- Unpolluted server latency telemetry in eval reports.
- Optimized Cloud Run scaling saving cost while eliminating user-facing cold starts.

### Benchmarks & Testing
- **Test 3.5-A (Page Attribution Purity):** 100% of generated chunks in test ingestion contain text belonging strictly to their assigned `page_number`.
- **Test 3.5-B (Server Latency Telemetry):** Eval harness logs server-side `latency_ms` directly without `gcloud` subprocess noise.

### Exit Criteria
✅ Zero cross-page chunk leakage. ✅ Clean eval metrics logged. ✅ Scaling configs deployed.

**Est. Effort:** 1 day

---

## Phase 4.0 — Authentication & Multi-Tenant Security ✅ COMPLETE

### Scope
Harden the system from "trusting app code" to "enforced at the engine level" using a strict zero-trust model. This phase introduces Firebase JWT verification for user routes, preserves Pub/Sub machine identities, and completely eliminates client-provided identity fields (IDOR protection).

### Tasks
- 4.1: ✅ **Route Auth Matrix & Firebase JWT Verification:**
  - `retrieval-api` (`/query`, `/search`, `/sessions`, `/documents`): Require Firebase User JWT on all routes. (Implemented via `services/common/auth/jwt.py` + `X-Firebase-Token` header; Cloud Run's platform rejects Firebase JWTs in `Authorization`, so the app reads the token from the custom header with `Authorization: Bearer` fallback.)
  - `ingestion-worker` (`/ingest`): **NO Firebase Auth**. Remains secured via Cloud Run IAM (Eventarc/PubSub machine-to-machine tokens).
  - `ingestion-worker` (`/memory` QA view): Firebase User JWT (Role: admin) via `qa_view.py` (replaced shared-secret gate).
- 4.2: ✅ **Strict Tenant Rewrite (Anti-IDOR):** API never accepts `tenant_id` from URL path, query params, headers, or body; `tenant_id` comes exclusively from the verified JWT `AuthContext`. Live Test 4-A passed: spoofed `tenant-id` header + body `tenant_id` ignored.
- 4.3: ✅ **ID Validation & Anti-NoSQL-Injection:** Strict regex validation (`^[a-zA-Z0-9_-]{1,128}$`) for `doc_id`/`session_id`, `^[a-zA-Z0-9_-]{1,64}$` for `tenant_id`, in `services/common/auth/validation.py`. Traversal/oversized inputs rejected 422.
- 4.4: ✅ **Session CRUD & Cascading Deletes:**
  - `POST /sessions`, `GET /sessions`, `DELETE /sessions/{session_id}` (no `tenant_id` in URL).
  - Session delete cascades to Qdrant points + Firestore messages. Document delete cascades to GCS + Qdrant + Firestore + session `document_ids` purge (FR-5.4).
- 4.5: ✅ **Signed GCS URL Hardening:** `GET /documents/{doc_id}/view-url`. Firestore ownership pre-check (`tenants/{tenant}/documents/{doc_id}` must exist), 15-minute V4 signed URL for exactly `{tenant_id}/{doc_id}.pdf`. IAM signer implemented (Cloud Run metadata creds have no private key; SA self-binds `roles/iam.serviceAccountTokenCreator`).
- 4.6: ✅ **Request Size & Cost Limits:** Max 4,000 chars/query, max 6 history turns, max 20 `top_k` (synthesis) / 50 (search) enforced in Pydantic models + `validation.py`.
- 4.7: ✅ **Local Rate Limiting:** In-memory fixed-window limiter per `tenant_id` on `/query` and `/search` (30 req/min default, `RATE_LIMIT_PER_MINUTE` overridable). Live Test 4-D passed (429 on burst).
- 4.8: ✅ **Firestore Security Rules:** `firestore.rules` enforcing `request.auth.token.tenant_id == resource.data.tenant_id`, deployed live via `infra/firestore_rules.tf` (ruleset `28cde4f4-…` released 2026-08-19). 10/10 emulator tests + live Test 4-B passed.

### Services Touched
Firebase Authentication, Cloud Run IAM, Qdrant, Firestore Rules, GCS Signed URLs.

### Deliverables
A fully authenticated, zero-trust backend that relies exclusively on verified JWT claims for tenant isolation, without breaking background asynchronous ingestion.

### Benchmarks & Testing
- ✅ **Test 4-A (Cross-Tenant Penetration Test):** Tenant A JWT + spoofed `tenant-id: tenant-b` header/body → only Tenant A data returned; cross-tenant DELETE scoped to JWT tenant, zero damage. PASSED live.
- ✅ **Test 4-B (Firestore Rules):** Direct Firestore reads/writes across tenant boundary with client SDK → denied (403). 5/5 live checks. PASSED live.
- ✅ **Test 4-C (Signed URL / IDOR):** Cross-tenant `view-url` → 404 (ownership check); signed URL TTL `X-Goog-Expires=900`; download verified 200. PASSED live.
- ✅ **Test 4-D (Cost Control & Rate Limit):** 40 concurrent requests → 1×429. Oversized query → 422 (unit-tested). PASSED.
- **Benchmark:** Zero cross-tenant data leaks across all penetration test cases. ✅

### Exit Criteria
✅ All tests pass with zero exceptions. ✅ Ingestion Pub/Sub delivery still works (no 401s). ✅ 186 local tests green. ✅ 10/10 Firestore emulator rules tests green. ✅ 4/4 live penetration tests pass.

**Est. Effort:** 1.5–2 weeks

---

## Phase 5.0 — Frontend Integration (Vercel)

### Scope
Build the client-facing Next.js app on the existing Vercel custom domain and connect it to the GCP backend over authenticated HTTPS, shipping the MVP journey: **login → upload → ask → pixel-accurate citation highlight**. The detailed UI/architecture specification (design system, folder structure, state management, Zod contracts, PDF.js/bbox UX flow) lives in `FRONTEND_PLAN.md` — this section is the build plan for it.

### Tasks

**Sequencing (decided 2026-08-20, post-frontend-review):** 1) CORS on `retrieval-api` **now** — the only true hard blocker, unblocks all frontend work; 2) walking-skeleton core loop (Firebase Auth → `/query` → PDF.js citation panel) — golden docs are already ingested under test-tenant, so the demo-critical journey works without upload; 3) `POST /documents/upload` deferred to after the core loop (upload UI ships disabled with a "docs coming soon" state); 4) polish items deferred — OpenAPI error schemas (401/403/404/429/500), typed `SessionList` schema, CI API-drift check (no CI in frontend repo yet), git `safe.directory` (one-time local config, not a repo issue).

**Backend prerequisites (deferred from Phase 4.0):**
- 5.0a: **CORS on `retrieval-api`** *(DO FIRST — hard blocker)* — FastAPI `CORSMiddleware` with the Vercel origin in `allow_origins` and `X-Firebase-Token` in `allow_headers` (custom header → preflight OPTIONS must pass). Without `Access-Control-Allow-Origin` the browser cannot call the API, so no frontend work is testable until this ships. ~10 min, isolated, low-risk. *(Open: final Vercel origin.)*
- 5.0b: **`POST /documents/upload` on `retrieval-api`** *(deferred from Phase 4.0; re-deferred to post-core-loop)* — Firebase JWT required, `tenant_id` from JWT only (anti-IDOR), `doc_id` regex-validated, stream PDF to `gs://iris-raw-pdfs/{tenant}/{doc_id}.pdf`, publish to the `iris-ingestion` topic, return `{doc_id, status}`. Progress is surfaced via the existing `GET /doc-status/{doc_id}` (polled by the frontend). *(The ingestion pipeline itself already exists — this endpoint is the user-facing trigger. Not on the demo-critical path.)*

**Frontend (per `FRONTEND_PLAN.md`):**
- 5.1: **Scaffold & Design System** — Next.js (App Router, TypeScript) + shadcn/ui + Radix Themes; emerald palette + Manrope (FRONTEND_PLAN §1); folder structure with page-level resource co-location (`app/(auth)/`, `app/(app)/chat/`, `app/(app)/documents/`, `lib/api/`, `lib/auth/` — FRONTEND_PLAN §2).
- 5.2: **Firebase Auth** — Firebase Client SDK (`lib/auth/firebase.ts` + `token.ts`): sign-in page, silent ID-token refresh, `X-Firebase-Token` header injection in `lib/api/client.ts`. **Never send `tenantId`** — query params carry UI state only (`sessionId`, `docId`, `page`, `citationId`, `panelWidth`); security state stays server-side from the JWT (FRONTEND_PLAN §3).
- 5.3: **Chat surface (`/chat`)** — split-screen `ChatPanel` + `PdfPanel` + `ResizableSplit`; `POST /query` integration with loading skeleton + latency telemetry; Zod runtime validation of `QueryResponse`/`Citation` so unexpected backend data never crashes the UI (FRONTEND_PLAN §5).
- 5.4: **Documents page** — `UploadDropzone` (calls `POST /documents/upload`) + `DocStatusTable` polling `/doc-status/{id}` via TanStack Query; server state in TanStack Query, UI state (active citation, PDF zoom, panel width) in Zustand (FRONTEND_PLAN §4).
- 5.5: **PDF.js citation side panel (Degradation Ladder)** — click citation pill → fetch signed URL (`GET /documents/{doc_id}/view-url`) → PDF.js renders target page → `BboxOverlay.tsx` attempts to map normalized `[left, top, right, bottom]` bbox to canvas pixels (ideal for digital docs). If `bbox` is missing (e.g. scanned VLM OCR docs) or fails, fallback to jumping to the page without a box. **Crucially:** always display a collapsible "Text Snippet" card in the chat UI containing the `page_number` and first ~150 chars of the retrieved chunk as a safety net, so users know exactly what to look for when visual highlights degrade (FRONTEND_PLAN §6).
- 5.6: **URL state pattern** — split-screen state lives in query params (`/chat?sessionId=s_123&docId=doc_456&page=14&citationId=c_789`) for instant state restoration on refresh/share (FRONTEND_PLAN §3.1).
- 5.7: **Playwright E2E** — automated test: login → ask → click citation → PDF navigates + highlights bbox (automates Test 5-A).
- 5.8: **Deploy to Vercel** — existing custom domain; env vars: Firebase web config (from the `FIREBASE_CONFIG` secret), `RETRIEVAL_URL`; enable CORS on `retrieval-api` for the Vercel origin if browser calls require it (the app already accepts `X-Firebase-Token`).

### Services Touched
Vercel (Next.js), Firebase Auth (client SDK), Cloud Run (Retrieval API), GCS signed URLs, Pub/Sub (upload trigger), PDF.js.

### Deliverables
A live, working product on the existing domain: a user can sign up/log in, upload a document, watch ingestion progress, ask questions, and see pixel-accurate citation highlights — with zero manual intervention.

### Benchmarks & Testing
- **Test 5-A (E2E Journey):** A new user can sign up/log in, upload a document, ask a question, and see a correctly-positioned highlight — zero manual intervention (automated via Playwright, Task 5.7).
- **Test 5-B (Cross-Browser):** Verify the above journey on Chrome, Safari, and Firefox.
- **Test 5-C (Load Test):** Simulate 20 concurrent tenant sessions; confirm no cross-tenant leakage and latency stays within NFR-1 bounds.
- **Test 5-D (Citation Side Panel):** Clicking any citation in a test set of 15 sample answers correctly opens the source PDF, navigates to the right page, and highlights the right region within 1 second; the text-search fallback triggers correctly when bbox data is intentionally withheld for one test case.
- **Test 5-E (Auth & Token Lifecycle):** Unauthenticated visit → login redirect; expired ID token → silent refresh → request retried successfully; signed-URL expiry (403) → auto-refetch.
- **Benchmark:** Full user journey completes in a single session without errors, timeouts, or visual bbox misalignment greater than a few pixels.

### Exit Criteria
✅ E2E journey passes on all three browsers. ✅ Load test shows no security or performance regression. ✅ Citation side panel and its text-search fallback both verified. ✅ Upload → ingestion → doc-status progress → query → citation works end-to-end. ✅ `FRONTEND_PLAN.md` checklist fully implemented.

**Est. Effort:** 1.5–2 weeks

---

## 🏁 MVP LAUNCH BOUNDARY

**At this point (end of Phase 5.0), IRIS is a secure, working, cost-protected product ready for real (manually onboarded) clients.**

MVP includes: secure multi-tenant auth & isolation, full ingestion → retrieval → synthesis → citation pipeline, billing/ingestion kill switches, and a live frontend on the existing domain.

MVP excludes (by design, added post-launch): conversational memory persistence across sessions, self-serve trial signup, GPU-based inference, advanced reranking, and multi-region redundancy.

**Total time to MVP: ~6–8 weeks.**

---

## Phase 6.0 — Conversational Memory + SLM-Based Query Rewrite ("Supermemory-Lite")

### Scope
Allow multi-turn conversations that retain context, using a dedicated **Small Language Model (SLM)** for the rewrite step so it stays fast and cheap on every single turn.

### Tasks
- 6.1: Persist full chat history per session in Firestore.
- 6.2: Add a `rewrite_query()` method to the `ModelProvider` interface, backed by the smallest/cheapest available model (e.g., Gemini Flash-Lite at minimum `thinking`/token budget, or a self-hosted SLM such as Gemma once GPU is available in Phase 15.0 — selected via the same `MODEL_BACKEND` config pattern as every other provider call).
- 6.3: On each turn, prior conversation turns + the new question are passed to `rewrite_query()`, which resolves pronouns/ambiguous references ("what about that clause?") into a fully self-contained query before retrieval.
- 6.5: **Heuristic Rewrite Gate (Latency & Cost Optimization):** Run a fast zero-cost code check before triggering `rewrite_query()`. Trigger rewriter when:
  1. Ambiguous pronouns/references are present with chat history (`it`, `this`, `that`, `these`, `those`, `former`, `latter`, `above`, `the previous`).
  2. Word count threshold (`len(query.split()) > 15`) or storytelling punctuation (`.` or `;`) or conversational openers (`can you`, `i want to`) are detected, stripping narrative filler from verbose questions before retrieval.
  If neither condition is met (e.g. short standalone queries like *"What is Section 5?"*), skip the LLM rewriter completely to save ~150ms and 100% of rewriter API cost.
- 6.6: **Hybrid Topic Summary Memory (Long-Chat Optimization):** When session history exceeds 15 turns, compress older messages into a 2-sentence running topic summary and append only the last $N=2$ raw messages. This keeps rewrite context under 200 tokens regardless of conversation length.

#### 6.6 Detailed Spec

**Problem:** The sliding window (N=6) truncates early context in long conversations. After 15+ turns, the rewrite gate loses track of the original topic.

**Design:**
1. **Trigger:** After every `/query` call, count messages in the session. If ≥15, run summary compression.
2. **Summary generation:** Flash-Lite call with prompt: "Summarize this conversation in 2 sentences, preserving the main topic and any document references." Input = all messages except the last 2. Output ≤100 tokens.
3. **Storage:** Write summary to the session document field `topic_summary` (not in the messages sub-collection — it replaces history, not appends to it).
4. **Loading:** In `_load_firestore_messages`, if the session doc has a `topic_summary`, prepend it as a system-style message before the last 2 raw messages. This gives the rewriter: `[summary, msg_N-1, msg_N, new_query]`.
5. **Cost:** One Flash-Lite call per query after turn 15 (~$0.0001, <200ms). Bounded: summary is always ≤100 tokens regardless of conversation length.

**Files:** `services/retrieval_api/app.py` (summary generation + storage), `_load_firestore_messages` (summary loading).

**Deferred because:** Requires a second LLM call per query, incremental summary update design, and testing with real long conversations. The current N=6 sliding window handles MVP conversations adequately.

### Services Touched
Firestore, Vertex AI (SLM query rewriting via `ModelProvider`).

### Benchmarks & Testing
- **Test 6-A:** A 5-turn conversation with pronoun references ("what about that clause?") correctly resolves to the right document context in ≥ 90% of test cases.
- **Test 6-B:** Chat history persists correctly across a session reload.
- **Test 6-C (SLM Cost/Latency):** Rewrite step adds < 300ms and < $0.001/call on average — confirm it doesn't become the bottleneck or the dominant cost line of a query.
- **Test 6-D (Heuristic Bypass Rate):** Verify that standalone queries without pronouns bypass `rewrite_query()` with 100% precision, achieving 0ms rewriter overhead.

### Exit Criteria
✅ Multi-turn accuracy ≥ 90% on test conversation set. ✅ History persists reliably. ✅ Rewrite step meets its own latency/cost budget independent of the main synthesis call. ✅ Heuristic gate successfully skips rewriter on direct queries.

**Est. Effort:** 1 week

---

## Phase 7.0 — Trial / Freemium & Rate Limiting

### Scope
Let prospects self-serve a capped trial without risking the budget.

### Tasks
- 7.1: Build the Firestore `usage_quotas` collection (pages ingested, queries used, credit balance, reset period).
- 7.2: Enforce hard caps at the API Gateway layer, before compute is invoked.
- 7.3: Implement the credit-balance debit model (e.g., 1 page ≈ 5 credits, 1 query ≈ 1 credit).
- 7.4: Return clear HTTP 429 "upgrade to continue" responses on cap breach.

### Services Touched
Firestore, API Gateway / Cloud Armor.

### Benchmarks & Testing
- **Test 7-A:** A trial account exhausts its credit balance and is correctly blocked with a 429 — not a silent failure or unbounded charge.
- **Test 7-B:** Trial tenants are provably isolated using the same mechanisms validated in Phase 4.0 (rerun the Phase 4.0 penetration tests against a trial account).

### Exit Criteria
✅ Cap enforcement verified. ✅ Trial isolation confirmed via re-run security tests.

**Est. Effort:** 3–5 days

---

## Phase 8.0 — Rephraser & Hypothesis Generator (HyDE)

### Scope
Improve retrieval recall for short or ambiguously-phrased questions by generating alternate phrasings and a hypothetical answer, then embedding those instead of (or alongside) the raw query.

### Tasks
- 8.1: Add `generate_hypothesis(query) -> hypothetical_answer_text` and `rephrase(query) -> [alt_phrasings]` methods to the `ModelProvider` interface, backed by the same SLM tier used for query rewrite (Phase 6.0).
- 8.2: On retrieval, embed the hypothetical answer (and/or a fused multi-phrasing embedding) instead of the raw question; fall back to raw-query embedding if hypothesis generation fails or times out.
- 8.3: Add a config flag to toggle HyDE per query type (e.g., always on for short queries under N words, optional for long/specific queries where raw embedding already performs well).
- 8.4: ⚠️ **[DEFERRED from retrieval-quality pipeline #3]** **Cross-Lingual Dual-Query:** Detect script mismatch (Latin query + Devanagari-dominant corpus, romanized-Hindi detection) and generate Hindi + English query variants via SLM; run parallel searches and merge via RRF. Transliteration gate was deployed live (`ingestion-worker-00030-h9l`) but the Flash-Lite dual-query path was disabled after eval showed negligible retrieval improvement (+0.003 MRR) and unacceptable latency regression (+5.3s). Reranker confirmed multilingual — may be re-activated as a cheaper alternative once cross-encoder reranking is live. Files: `services/common/retrieval/search.py` (next to `_needs_rewrite`), `retrieval/hindi.py` (`contains_devanagari`), new `ModelProvider` method mirroring `rewrite_query`.

### Services Touched
Vertex AI (via `ModelProvider`), Retrieval API.

### Benchmarks & Testing
- **Test 8-A (Recall Lift):** Re-run the Phase 2.0 test question set with HyDE enabled vs. disabled; require a measurable improvement in top-5 retrieval recall, especially on short/vague questions.
- **Test 8-B (Latency Budget):** Hypothesis generation adds < 400ms to end-to-end query time; if it exceeds budget, the system falls back to raw-query embedding automatically.
- **Test 8-C (Failure Fallback):** Simulate a hypothesis-generation failure (timeout/error); confirm the query still completes using the raw-query embedding path.

### Exit Criteria
✅ Measurable recall improvement confirmed on test set. ✅ Latency fallback verified under simulated failure. ⚠️ Task 8.4 (cross-lingual dual-query) deferred pending cross-encoder reranker activation — transliteration gate is live but dual-query disabled (negligible lift, +5.3s latency).

**Est. Effort:** 3–5 days (excluding deferred Task 8.4)

---

## Phase 9.0 — Citation & Bbox Management Layer

### Scope
Turn "citations" from an LLM-output convention into a validated, versioned registry — this is the trust layer the graph phases (10.0–11.0) will be built on top of.

### Tasks
- 9.1: Build a Citation Registry service: every citation returned by the synthesis step (Phase 3.0) is checked against the actual retrieved chunk set before being returned to the frontend — reject/re-ask on any citation that doesn't map to a real `chunk_id`.
- 9.2: Implement bbox deduplication and merging: when multiple chunks reference overlapping/adjacent regions on the same page, merge them into a single clean highlight instead of stacking overlapping boxes.
- 9.3: Support multi-page citation spans (a single cited fact spanning a table that continues onto the next page).
- 9.4: Handle document re-ingestion/versioning: when a document is re-uploaded or updated, old `chunk_id`/bbox references are versioned (not silently overwritten), so historical chat citations don't silently point to the wrong content.
- 9.5: Expose a `GET /citations/{citation_id}` endpoint returning the validated bbox + page + source snippet, decoupling the frontend from needing to know Qdrant's internal schema.

### Services Touched
Retrieval API, Qdrant, Firestore (citation/version metadata), GCS.

### Benchmarks & Testing
- **Test 9-A (Validity Gate):** Feed the registry a deliberately hallucinated citation (fake `chunk_id`); confirm it is rejected before reaching the user, 100% of the time across a 50-case adversarial test set.
- **Test 9-B (Bbox Merge Quality):** Visually verify on 20 sample documents that overlapping/adjacent citations render as clean merged highlights, not stacked duplicates.
- **Test 9-C (Multi-Page Spans):** Confirm a citation spanning a table across two pages renders correctly on both pages.
- **Test 9-D (Re-ingestion Safety):** Re-upload a modified version of a previously-cited document; confirm old chat sessions' citations remain valid and correctly labeled as referring to the prior version, not silently broken or misattributed.

### Exit Criteria
✅ 100% hallucinated-citation rejection on adversarial set. ✅ Bbox merge and multi-page rendering verified. ✅ Re-ingestion versioning confirmed safe.

**Est. Effort:** 1–1.5 weeks

---

## Phase 10.0 — Citation Map & Graph Node Network (Ingestion-Time)

### Scope
Build the actual knowledge graph: nodes for documents/sections/clauses/entities, edges for relationships like "amends," "references," and "supersedes" — critical for legal/gazette documents that constantly cross-reference each other.

### Tasks
- 10.1: During ingestion (extending Phase 1.0), run an entity/relationship extraction pass over each parsed document using the `ModelProvider.synthesize()` call with a structured extraction schema (entities: sections, clause numbers, named parties, dates; relationships: amends, references, supersedes, defines).
- 10.2: Choose the graph storage approach deliberately for cost reasons: **start with a lightweight embedded graph** — edges stored as structured records in Firestore (or a serialized graph object in GCS, loaded into memory by the Retrieval API) — rather than standing up a paid managed graph database. Re-evaluate a dedicated graph DB (e.g., Neo4j AuraDB) only once graph size/query complexity justifies the added cost (see Phase 16.0).
- 10.3: Link every graph node back to its source `chunk_id`/citation via the Phase 9.0 Citation Registry, so graph traversal results are always backed by a validated, cited source.
- 10.4: Build an ingestion-time dedup/merge pass so the same entity mentioned across documents (e.g., the same Act referenced in five different gazettes) resolves to one graph node, not five duplicates.

### Services Touched
Firestore or GCS (graph storage), Vertex AI (extraction), Citation Registry (Phase 9.0).

### Benchmarks & Testing
- **Test 10-A (Extraction Accuracy):** On a 20-document sample, manually verify ≥ 85% precision on extracted relationships (no invented cross-references).
- **Test 10-B (Entity Resolution):** Confirm a known entity/Act referenced across multiple test documents resolves to a single graph node, not duplicates.
- **Test 10-C (Citation Backing):** Every graph edge traces back to a valid citation via the Phase 9.0 registry — spot-check 30 edges.
- **Benchmark:** Ingestion time increase from adding the extraction pass stays within 25% of the Phase 1.0 baseline per-document ingestion time.

### Exit Criteria
✅ Extraction precision ≥ 85%. ✅ Entity resolution confirmed. ✅ Every edge is citation-backed. ✅ Ingestion time overhead within budget.

**Est. Effort:** 1.5–2 weeks

---

## Phase 11.0 — Graph-Aware Retrieval (Query the Graph & Semantic Relationships)

### Scope
Use the graph built in Phase 10.0 at query time: given an initial vector-search hit, traverse relationship edges to pull in related clauses/documents that pure semantic search would miss.

### Tasks
- 11.1: Extend the `/query` pipeline: after initial vector retrieval (Phase 2.0), look up graph neighbors (1–2 hops) of the top-matched chunks/entities and include relevant neighbors as additional retrieval candidates.
- 11.2: Add relationship-type-aware ranking: an "amends" edge to a highly relevant clause should be weighted differently than a loose "references" edge.
- 11.3: Surface the relationship path in the response (e.g., "this clause was later amended by Section 4 of Notification X") so the answer explains *why* a related document was pulled in, not just what it says.
- 11.4: Add a query-time toggle to enable/disable graph expansion (useful for cost control and for A/B testing its impact).

### Services Touched
Retrieval API, Graph store (Phase 10.0), `ModelProvider.synthesize()`.

### Benchmarks & Testing
- **Test 11-A (Relevance Lift on Cross-Reference Questions):** Build a test set of 20 questions that specifically require following a cross-reference (e.g., "has this clause been amended?"); confirm graph-aware retrieval answers these correctly significantly more often than vector-only retrieval.
- **Test 11-B (No Regression on Simple Questions):** Confirm graph expansion does not degrade latency or accuracy on the existing Phase 2.0/3.0 test sets when the cross-reference isn't relevant.
- **Test 11-C (Latency):** Graph traversal adds < 300ms to end-to-end query time for a 2-hop expansion.

### Exit Criteria
✅ Measurable accuracy improvement on cross-reference test set. ✅ No regression on baseline test set. ✅ Latency budget met.

**Est. Effort:** 1–1.5 weeks

---

## Phase 12.0 — Neural Reranking Upgrade & Precision Engineering

### Scope
Elevate retrieval precision (targeting MRR ≥ 0.65+ and Page-Recall@5 ≥ 0.80+) using cross-encoders, canonical document resolution, and domain-adapted retrieval strategies.

### Tasks
- 12.1: **Neural Cross-Encoder Reranker:** Integrate Vertex AI Ranking API (or Cohere `rerank-4-fast`) on top-40 RRF candidates before final synthesis context assembly.
- 12.2: **Canonical & Duplicate Document Resolution:** Add metadata weighting (`canonical_doc_id`, `version_type`, `publication_date`) to prefer primary/published statutory versions over draft manuscripts when identical facts appear across multiple documents.
- 12.3: **Dynamic Query-Type Retrieval Routing:** Implement lightweight query classification (e.g. section/clause lookup → BM25 boost; semantic conceptual inquiry → Dense vector boost; tabular lookup → table chunk metadata filter).

### Services Touched
Vertex AI Ranking API (or Cohere Rerank v4), Search Orchestrator, Qdrant payload filters.

### Benchmarks & Testing
- **Test 12-A (MRR Lift):** Re-run golden evaluation suite; assert MRR improves from MVP baseline (0.251) to ≥ 0.65.
- **Test 12-B (Canonical Preference):** For queries whose answer text exists across multiple documents (e.g. doc_006 and doc_007), verify the canonical source is ranked #1.
- **Test 12-C (Latency Overhead):** Cross-encoder rerank adds < 400ms to the warm retrieval pipeline.

### Exit Criteria
✅ MRR ≥ 0.65 on golden test set. ✅ Canonical documents prioritized in multi-source answers. ✅ Latency budget met.

**Est. Effort:** 1–1.5 weeks

---

## Phase 13.0 — Context Compression

### Scope
Reduce token costs at scale via SLM-based context compression before final synthesis.

### Tasks
- 13.1: Introduce a small-language-model compression step between retrieval and synthesis.

### Benchmarks & Testing
- **Test 13-A:** Confirm ~80% token cost reduction on large-document queries without a measurable drop in answer quality (re-run Phase 3.0's answer-quality test set).

### Exit Criteria
✅ Cost reduction target met. ✅ Answer quality unchanged within tolerance.

**Est. Effort:** 1 week

---

## Phase 14.0 — Mixture of Agents (MoA) Synthesis

### Scope
For complex/high-stakes queries, replace the single synthesis call with multiple specialized agent passes whose outputs are cross-checked and aggregated — opt-in, not default, due to cost multiplication.

### Tasks
- 14.1: Define specialized agent roles as distinct prompts/calls through `ModelProvider.synthesize()`: e.g., an **Extraction Agent** (pulls raw facts from retrieved chunks), an **Interpretation Agent** (reasons about implications, especially for legal/gazette content), and a **Verification Agent** (checks the draft answer's claims against the Citation Registry from Phase 9.0).
- 14.2: Build an Aggregator step that reconciles the agents' outputs into one final answer, flagging any disagreement between agents rather than silently picking one.
- 14.3: Gate this entire pipeline behind an explicit trigger: a "high-assurance mode" toggle (user-selected, or auto-triggered for queries matching complexity heuristics), never the default path for simple questions.
- 14.4: Add hard per-query cost ceilings for MoA mode, enforced by the same billing-safety pattern from Phase 0.0.

### Services Touched
Vertex AI (multiple calls via `ModelProvider`), Citation Registry (Phase 9.0).

### Benchmarks & Testing
- **Test 14-A (Quality Lift):** On a set of 20 deliberately complex/ambiguous test questions, MoA-mode answers are judged higher quality/more reliable than single-agent answers in blind comparison.
- **Test 14-B (Cost Control):** Confirm MoA mode is never invoked without explicit trigger, and that its per-query cost stays within the configured ceiling — test by attempting to exceed it.
- **Test 14-C (Disagreement Handling):** Construct a test case where agents would plausibly disagree; confirm the aggregator surfaces the disagreement rather than masking it.

### Exit Criteria
✅ Quality lift confirmed via blind comparison. ✅ Cost ceiling enforced under test. ✅ Disagreement is surfaced, not hidden.

**Est. Effort:** 1.5–2 weeks

---

## Phase 15.0 — GPU Swap-In (When Quota Available)

### Scope
Activate the dormant `SelfHostedGPUProvider` once GCP GPU quota is approved.

### Tasks
- 10.1: Provision an L4 (or similar) GPU instance.
- 10.2: Implement `SelfHostedGPUProvider` (e.g., vLLM, Baidu Unlimited-OCR).
- 10.3: Run the new provider in shadow mode — comparing outputs against the live Vertex AI provider on sampled real traffic — for at least one week.
- 10.4: Flip the `MODEL_BACKEND` flag to cut over, with zero frontend or database changes.

### Services Touched
GCE (GPU VM), self-hosted inference stack.

### Benchmarks & Testing
- **Test 10-A (Shadow Mode Parity):** Self-hosted outputs match Vertex AI outputs within an acceptable quality tolerance on ≥ 95% of shadow-mode samples.
- **Test 10-B (Zero-Downtime Cutover):** Flip the flag in a staging environment; confirm no frontend/DB changes were required and no downtime occurred.

### Exit Criteria
✅ Shadow mode parity confirmed. ✅ Cutover requires only a config change, verified live.

**Est. Effort:** 1–2 weeks (blocked on GCP GPU quota approval)

---

## Phase 16.0 — Enterprise Scale Hardening

### Scope
Prepare the system for 20+ clients and production SLA guarantees.

### Tasks
- 11.1: Migrate Qdrant to Qdrant Cloud Managed.
- 11.2: Add automated snapshot/disaster-recovery for all data stores.
- 11.3: Deploy the Retrieval API across multiple Cloud Run regions behind a Global External HTTPS Load Balancer.
- 11.4: Formalize on-call/monitoring and SLA tracking.

### Benchmarks & Testing
- **Test 11-A (DR Drill):** Simulate a regional outage; confirm recovery within the defined RTO/RPO targets.
- **Test 11-B (Multi-Region Latency):** Confirm NFR-1 latency targets are met from at least two geographically distant test locations.

### Exit Criteria
✅ DR drill succeeds. ✅ Multi-region latency targets met. ✅ 99.9% uptime target achievable per architecture review.

**Est. Effort:** Ongoing

---

## Phase 16.0 — Enterprise Hardening & Zero-Trust Infrastructure

### Scope
Prepare the system for rigorous enterprise security audits, production SLAs, and B2B SaaS isolation guarantees, migrating from MVP security to full perimeter defense.

### Tasks
- 16.1: **External HTTPS Load Balancer & WAF:** Deploy a Global External HTTPS Load Balancer. Attach Cloud Armor policies to enforce strict IP rate limiting, geo-blocking, and WAF rules (SQLi, XSS) before traffic hits the backend.
- 16.2: **Cloud Run Ingress Lockdown:** Update `retrieval-api` and `ingestion-worker` to `ingress = internal-and-cloud-load-balancing` so they cannot be accessed via direct `.run.app` URLs.
- 16.3: **Least-Privilege IAM Custom Roles:** Remove MVP roles (`roles/datastore.owner`, `roles/storage.objectAdmin`) and replace with custom Terraform roles enforcing minimal permissions (e.g. read-only, strict token-creator).
- 16.4: **Granular Document Authorization (ACLs):** If required by the business model, implement `owner_uid` on sessions/documents to prevent users within the same tenant from accessing each other's data (per-user isolation).
- 16.5: **Audit Logging & Incident Response:** Enable GCP Data Access Audit Logs for all PII/sensitive data access. Write DR and security incident runbooks.

### Services Touched
Cloud Armor, Cloud Load Balancing, IAM, Cloud Audit Logs, Firestore.

### Deliverables
A SOC2-ready perimeter and interior zero-trust architecture.

### Exit Criteria
✅ Penetration testing verifies Cloud Run direct URLs are inaccessible. ✅ Cloud Armor successfully blocks simulated WAF attacks and rate-limits properly. ✅ IAM audit confirms zero overly-broad permissions.

**Est. Effort:** Ongoing

---

## Summary Timeline

| Phase | Weeks (Cumulative, indicative) | MVP? |
|---|---|---|
| 0.0 Foundations | Week 1 | Required |
| 0.1 Model Provider Scaffold | Week 1–1.5 | Required |
| 1.0 Ingestion Pipeline | Week 1.5–3.5 | Required |
| 2.0 Vector Store & Retrieval | Week 3.5–5 | Required |
| 3.0 LLM Synthesis | Week 5–6 | Required |
| 3.5 Retrieval Hardening (Lite) | Week 6 | Required |
| 4.0 Auth & Security | Week 6–7.5 | Required |
| 5.0 Frontend Integration | Week 7.5–8.5 | Required — **MVP Launch** |
| 6.0 Conversational Memory + SLM Query Rewrite | Post-MVP | Optional for v1 |
| 7.0 Trial/Freemium | Post-MVP | Optional for v1 |
| 8.0 Rephraser & Hypothesis Generator (HyDE) | Post-MVP | Optional for v1 |
| 9.0 Citation & Bbox Management Layer | Post-MVP | Optional for v1 — **prerequisite for 10.0/11.0** |
| 10.0 Citation Map & Graph Node Network | Post-MVP | Optional for v1 — depends on 9.0 |
| 11.0 Graph-Aware Retrieval | Post-MVP | Optional for v1 — depends on 10.0 |
| 12.0 Reranking Upgrade & Precision Engineering | Post-MVP | Optional for v1 |
| 13.0 Context Compression | Post-MVP | Optional for v1 |
| 14.0 Mixture of Agents (opt-in mode) | Post-MVP | Optional for v1 |
| 15.0 GPU Swap-In | Blocked on quota | Optional for v1 |
| 16.0 Enterprise Hardening | Ongoing, 20+ clients | Optional for v1 |

**Dependency note:** Phases 9.0 → 10.0 → 11.0 form a strict chain (bbox trust layer → graph build → graph query) and must be built in that order. Phases 6.0, 7.0, 8.0, 12.0, 13.0, and 14.0 are independent of each other and of the graph chain, and can be resequenced or parallelized across team members if capacity allows.

**End-to-end flow recap (start to finish):**
`0.0 Foundations` (safety nets) → `0.1 Model abstraction` → `1.0 Ingest` → `2.0 Store & Search` → `3.0 Synthesize` → `3.5 Retrieval Hardening` → `4.0 Secure` → `5.0 Ship Frontend` → **MVP live** → `6.0 Memory/Rewrite` → `7.0 Trial` → `8.0 HyDE` → `9.0 Citation Trust Layer` → `10.0 Build Graph` → `11.0 Query Graph` → `12.0 Rerank & Precision` → `13.0 Compress` → `14.0 Mixture of Agents (opt-in)` → `15.0 GPU when ready` → `16.0 Scale to enterprise`.
