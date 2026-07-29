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
- Stub `SelfHostedGPUProvider` (unimplemented, dormant, but present in code with clear TODOs).
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

## Phase 1.0 — Core Ingestion Pipeline

### Scope
Build the document upload → parse → route → chunk → embed → store pipeline, with a page-wise VLM router that minimises Gemini Vision API calls to only the elements that genuinely require them.

### Tasks
- 1.1: Create tenant-prefixed GCS buckets (`gs://iris-raw-pdfs/{tenant_id}/...`) with IAM conditions.
- 1.2: Build the pre-ingestion payload scanner (reject >500 pages, corrupt PDF trailers) before queuing.
- 1.3: Implement the Ingestion Worker on Cloud Run, triggered via Pub/Sub on new upload events.
- 1.4: Integrate Docling for layout-aware parsing — every element (text block, table, figure) comes out with its normalised `[left, top, right, bottom]` bounding-box coordinates and an element-type label (`Text`, `Table`, `Picture`, `Caption`, etc.).
- 1.5: Implement the **Page-Wise VLM Router**. After Docling processes each page, the router inspects Docling's output and makes a routing decision per element:

  | Docling Signal | Condition | Route |
  |---|---|---|
  | Element type = `Text` / `Paragraph` | Char count ≥ 150 | **Docling text directly** — zero API cost |
  | Element type = `Table` | Any char count | **Gemini Vision** on cropped table bbox region |
  | Element type = `Picture` / `Figure` | Any char count | **Gemini Vision** on cropped figure bbox region for captioning |
  | Any element type | Char count < 150 (scanned / image-only page) | **Gemini Vision** on full page crop |

  *Rationale: Gemini Vision reads rendered pixels, so KrutiDev/DevLys legacy Hindi font encoding and scanned Devanagari text are handled transparently — no custom font decoder or RapidOCR pipeline required. VLM is only invoked where Docling’s text extraction is absent or structurally insufficient (tables, figures, scanned pages).*

- 1.6: Chunk routed content. Text blocks: sentence-boundary chunking at ~512 tokens. VLM outputs: treated as single chunks with the source element’s bbox attached.
- 1.7: Embed each chunk via `ModelProvider.embed()` → **Vertex AI `text-embedding-004`** (3072-d, multilingual). No local ONNX model required.
- 1.8: Configure the Pub/Sub subscription with max 3 delivery attempts, routing failures to a DLQ topic.
- 1.9: Write parsed, embedded chunks (with bbox + `tenant_id` + `page_number` + `element_type` metadata) to Qdrant.
- 1.10: Build an internal **Chunk Visualization / QA view** — an admin-only page that overlays every extracted chunk’s bounding box on the source PDF page, so a human can visually sanity-check Docling’s parsing and the VLM router’s decisions on a new or unusual document type before it goes live.

### Services Touched
GCS, Pub/Sub, Cloud Run, Docling, Vertex AI (Gemini Vision + `text-embedding-004` via ModelProvider), Qdrant (write path).

### Deliverables
A working pipeline: PDF in → page-wise routed, bbox-tagged, embedded chunks out.

### Benchmarks & Testing
- **Test 1-A (Happy Path):** Upload a 50-page sample gazette PDF; confirm it is fully parsed and chunks appear in Qdrant within 2 minutes (NFR-1 target).
- **Test 1-B (Oversized Rejection):** Upload a 600-page PDF; confirm it is rejected pre-queue with a clear error, never entering the pipeline.
- **Test 1-C (Corrupt File):** Upload a deliberately corrupted PDF; confirm it fails gracefully and lands in the DLQ after 3 attempts — not an infinite retry loop.
- **Test 1-D (VLM Router — Table):** Upload a document containing a known complex multi-column table; confirm the router triggers a Gemini Vision call for that element and the resulting chunk contains structured markdown, not scrambled text.
- **Test 1-E (VLM Router — Scanned Page):** Upload a scanned-only page (char count < 150 from Docling); confirm the router triggers a full-page Gemini Vision call and produces readable text output.
- **Test 1-F (VLM Router — Clean Text):** Upload a clean text page; confirm *no* Gemini Vision API call is made for it (verify via cost log / call counter).
- **Test 1-G (Bbox Accuracy):** Spot-check 10 randomly sampled chunks against the source PDF; bbox coordinates must visually align with the correct content when manually overlaid.
- **Test 1-H (Chunk Visualization QA):** Confirm the internal QA view correctly renders bbox overlays for a sample of 5 documents spanning different layouts (dense text, tables, scanned/rotated pages).
- **Benchmark:** VLM call count per 50-page document logged; typical gazette expected to trigger ≤ 20% of pages as VLM calls. Ingestion cost per document tracked against daily budget cap.

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
- 2.4: Build the Retrieval API's `/search` endpoint with **hybrid search**: dense cosine vector search + BM25 full-text search, both executed against the same Qdrant collection in parallel.
- 2.5: Implement **Reciprocal Rank Fusion (RRF)** to merge the dense and BM25 rank lists into a single coherent ordered list. RRF is rank-based and score-agnostic — it handles the incompatibility between cosine similarity scores and BM25 scores without normalisation hacks.
- 2.6: Implement the **Diversity / Dedup pass** on top of the RRF-fused list. This step applies a `0.5×` score multiplier to any chunk whose `source_file` has already appeared in the current top-K window. This prevents a single highly-relevant source document from flooding all top-K slots and starving synthesis of breadth. *This is a separate concern from reranking — RRF handles fusion, diversity handles source over-representation.*
- 2.7: Wire the **Standard Mode** query path: embed query (Vertex AI `text-embedding-004`, 3072-d) → hybrid search → RRF → diversity pass → return top-K chunks.
- 2.8: Wire the **Deep Search Mode** query path (user-toggled): same as Standard, but after the diversity pass, run the fused+diversified list through the **Vertex AI Ranking API** (cross-encoder semantic reranker) before returning. Deep Search mode also enables SLM query rewriting and HyDE (Phase 8.0).
- 2.9: Enforce a server-side tenant filter (app-layer for now; JWT-level enforcement lands in Phase 4.0).

### Services Touched
GCE (Qdrant host), Cloud Run (Retrieval API), Qdrant, Vertex AI (Ranking API, `text-embedding-004`).

### Deliverables
A working `/search` endpoint returning tenant-scoped results processed through the full RRF → diversity → [optional rerank] pipeline.

### Benchmarks & Testing
- **Test 2-A (Relevance):** Run a fixed set of 20 known question/answer pairs against a test corpus; measure retrieval precision (top-5 chunk relevance) manually or via a scoring rubric.
- **Test 2-B (Tenant Filter):** Seed two test tenants with distinct documents; confirm Tenant A’s search never returns Tenant B’s chunks.
- **Test 2-C (RRF vs. single-modality):** Compare top-5 retrieval precision of hybrid+RRF against dense-only and BM25-only; hybrid must match or exceed both on the 20-question test set.
- **Test 2-D (Diversity):** Upload a corpus where one document is strongly relevant to all 20 test questions; confirm the diversity pass prevents that document from occupying > 50% of top-10 slots in results.
- **Test 2-E (Deep Search rerank lift):** For 5 ambiguous queries, confirm Deep Search mode returns a measurably better top-1 result than Standard mode (manual review).
- **Test 2-F (Latency):** Standard mode `/search` responds in < 500ms for a corpus of 10,000+ chunks (excluding cold start).
- **Benchmark:** Qdrant VM memory/CPU usage stays within the provisioned instance size under a simulated 5-tenant load.

### Exit Criteria
✅ Standard and Deep Search paths both operational. ✅ RRF correctly fuses both rank lists. ✅ Diversity pass demonstrably prevents source flooding. ✅ Tenant filter holds under test. ✅ Latency benchmark met.

**Est. Effort:** 1–1.5 weeks

---

## Phase 3.0 — LLM Synthesis Layer

### Scope
Turn retrieved chunks into a final, cited, structured answer.

### Tasks
- 3.1: Implement `ModelProvider.synthesize()` using Gemini Flash/Flash-Lite via Vertex AI.
- 3.2: Define a Pydantic schema for structured output: answer text + list of citations (each mapped to `doc_id`, `page_number`, `bbox`).
- 3.3: Wire the `/query` endpoint: retrieve → rerank → synthesize → return structured response.
- 3.4: Add basic prompt-engineering safeguards against hallucinated citations (e.g., reject/re-ask if a citation doesn't map to a real retrieved chunk).

### Services Touched
Vertex AI (Gemini), Cloud Run (Retrieval API).

### Deliverables
A working `/query` endpoint returning a grounded, structured, cited answer.

### Benchmarks & Testing
- **Test 3-A (Citation Validity):** For 30 sample questions, confirm 100% of returned citations map to a real, retrieved chunk (no hallucinated bbox references).
- **Test 3-B (Answer Quality):** Manual review of answer quality against the 20-question test set from Phase 2.0; target ≥ 90% judged "accurate and grounded."
- **Test 3-C (Latency):** End-to-end `/query` response time < 2 seconds (NFR-1), excluding cold start.
- **Benchmark:** Token cost per query logged; confirm Flash-Lite usage stays within projected cost matrix (see `SRS.md` §Cost).

### Exit Criteria
✅ Citation validity = 100% on test set. ✅ Answer quality ≥ 90% on manual review. ✅ Latency benchmark met.

**Est. Effort:** 1 week

---

## Phase 4.0 — Authentication & Multi-Tenant Security

### Scope
Harden the system from "trusting app code" to "enforced at the engine level" — this is the most safety-critical phase.

### Tasks
- 4.1: Wire Firebase Authentication into the frontend and backend; issue JWTs with server-set `tenant_id`/`role` claims.
- 4.2: Update the Retrieval API to extract `tenant_id` from the validated JWT and **rewrite** (not merely check) the Qdrant query filter server-side.
- 4.3: Write Firestore Security Rules enforcing `request.auth.token.tenant_id == resource.data.tenant_id` on all reads/writes.
- 4.4: Implement session isolation: `session_id` scoped under `/{tenant_id}/sessions/{session_id}`.
- 4.5: Implement short-lived (15-minute) signed GCS URLs for document viewing.
- 4.6: Add Cloud Armor / API Gateway rate limiting on upload and query endpoints.

### Services Touched
Firebase Authentication, Cloud Run, Qdrant, Firestore, GCS, Cloud Armor.

### Deliverables
A fully authenticated, tenant-isolated system with no app-layer-only trust boundaries remaining.

### Benchmarks & Testing
- **Test 4-A (Cross-Tenant Penetration Test):** Using Tenant A's valid JWT, attempt to manually craft a request specifying Tenant B's `tenant_id` in the request body. The server-side filter rewrite MUST ignore the client-supplied value and use only the JWT claim — confirm zero leakage.
- **Test 4-B (Firestore Rules):** Attempt direct Firestore reads/writes across tenant boundaries using the client SDK with a mismatched token; MUST be denied by security rules.
- **Test 4-C (Signed URL Expiry):** Confirm a signed GCS URL is inaccessible after its 15-minute TTL expires.
- **Test 4-D (Rate Limiting):** Exceed the configured requests/minute threshold from a single IP; confirm subsequent requests are throttled.
- **Benchmark:** Zero cross-tenant data leaks across all penetration test cases — this is a hard pass/fail gate, not a percentage.

### Exit Criteria
✅ All four tests pass with zero exceptions. This phase cannot be marked complete on partial results — it is the platform's core trust guarantee.

**Est. Effort:** 1–1.5 weeks

---

## Phase 5.0 — Frontend Integration (Vercel)

### Scope
Connect the existing Next.js frontend to the new GCP backend and ship the MVP.

### Tasks
- 5.1: Wire the existing `BboxOverlay.tsx` component to the Retrieval API's `/query` response shape.
- 5.2: Implement the Firebase Auth login flow in the frontend.
- 5.3: Build the session/chat UI, calling the tenant-scoped `/query` endpoint.
- 5.4: Deploy to Vercel on the existing custom domain, pointing API calls at the GCP Retrieval API over authenticated HTTPS.
- 5.5: Build a **PDF.js-based citation side panel**: clicking a citation opens the source PDF in a side pane next to the chat, auto-navigates to the cited page using bbox/page metadata from Docling (Phase 1.0), and highlights the exact bbox region. Fall back to text-search-and-highlight within the page if bbox rendering isn't available for a given citation. *(Note: at MVP this reads bbox metadata directly from Qdrant chunk payloads; once Phase 9.0's Citation Registry lands post-MVP, the panel switches to consuming its validated `GET /citations/{citation_id}` endpoint instead — a backend swap only, no frontend rework needed.)*
- 5.6: End-to-end manual QA across the full user journey: login → upload → ask → see highlighted citation.

### Services Touched
Vercel, Firebase Auth (client SDK), Cloud Run (Retrieval API), PDF.js.

### Deliverables
A live, working product on the existing domain.

### Benchmarks & Testing
- **Test 5-A (E2E Journey):** A new user can sign up/log in, upload a document, ask a question, and see a correctly-positioned highlight — with zero manual intervention.
- **Test 5-B (Cross-Browser):** Verify the above journey on Chrome, Safari, and Firefox.
- **Test 5-C (Load Test):** Simulate 20 concurrent tenant sessions; confirm no cross-tenant leakage and latency stays within NFR-1 bounds.
- **Test 5-D (Citation Side Panel):** Clicking any citation in a test set of 15 sample answers correctly opens the source PDF, navigates to the right page, and highlights the right region within 1 second; the text-search fallback triggers correctly when bbox data is intentionally withheld for one test case.
- **Benchmark:** Full user journey completes in a single session without errors, timeouts, or visual bbox misalignment greater than a few pixels.

### Exit Criteria
✅ E2E journey passes on all three browsers. ✅ Load test shows no security or performance regression. ✅ Citation side panel and its fallback both verified.

**Est. Effort:** 1–1.5 weeks

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
- 6.4: Cap rewrite latency and token budget tightly (this runs on every turn) — target sub-300ms, a few hundred tokens max.

### Services Touched
Firestore, Vertex AI (SLM query rewriting via `ModelProvider`).

### Benchmarks & Testing
- **Test 6-A:** A 5-turn conversation with pronoun references ("what about that clause?") correctly resolves to the right document context in ≥ 90% of test cases.
- **Test 6-B:** Chat history persists correctly across a session reload.
- **Test 6-C (SLM Cost/Latency):** Rewrite step adds < 300ms and < $0.001/call on average — confirm it doesn't become the bottleneck or the dominant cost line of a query.

### Exit Criteria
✅ Multi-turn accuracy ≥ 90% on test conversation set. ✅ History persists reliably. ✅ Rewrite step meets its own latency/cost budget independent of the main synthesis call.

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

### Services Touched
Vertex AI (via `ModelProvider`), Retrieval API.

### Benchmarks & Testing
- **Test 8-A (Recall Lift):** Re-run the Phase 2.0 test question set with HyDE enabled vs. disabled; require a measurable improvement in top-5 retrieval recall, especially on short/vague questions.
- **Test 8-B (Latency Budget):** Hypothesis generation adds < 400ms to end-to-end query time; if it exceeds budget, the system falls back to raw-query embedding automatically.
- **Test 8-C (Failure Fallback):** Simulate a hypothesis-generation failure (timeout/error); confirm the query still completes using the raw-query embedding path.

### Exit Criteria
✅ Measurable recall improvement confirmed on test set. ✅ Latency fallback verified under simulated failure.

**Est. Effort:** 3–5 days

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

## Phase 12.0 — Neural Reranking Upgrade

### Scope
Improve retrieval relevance with a dedicated reranking model.

### Tasks
- 12.1: Integrate the Vertex AI Ranking API (or Cohere `rerank-4-fast` — **not** the deprecating v3.5) on top-40 retrieved candidates (now including graph-expanded candidates from Phase 11.0).

### Services Touched
Vertex AI Ranking API (or Cohere Rerank v4).

### Benchmarks & Testing
- **Test 12-A:** A/B comparison of pre- and post-rerank relevance on the Phase 2.0 test question set; require a measurable precision improvement.

### Exit Criteria
✅ Reranking shows measurable relevance improvement over baseline.

**Est. Effort:** 3–5 days

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

## Summary Timeline

| Phase | Weeks (Cumulative, indicative) | MVP? |
|---|---|---|
| 0.0 Foundations | Week 1 | Required |
| 0.1 Model Provider Scaffold | Week 1–1.5 | Required |
| 1.0 Ingestion Pipeline | Week 1.5–3.5 | Required |
| 2.0 Vector Store & Retrieval | Week 3.5–5 | Required |
| 3.0 LLM Synthesis | Week 5–6 | Required |
| 4.0 Auth & Security | Week 6–7.5 | Required |
| 5.0 Frontend Integration | Week 7.5–8.5 | Required — **MVP Launch** |
| 6.0 Conversational Memory + SLM Query Rewrite | Post-MVP | Optional for v1 |
| 7.0 Trial/Freemium | Post-MVP | Optional for v1 |
| 8.0 Rephraser & Hypothesis Generator (HyDE) | Post-MVP | Optional for v1 |
| 9.0 Citation & Bbox Management Layer | Post-MVP | Optional for v1 — **prerequisite for 10.0/11.0** |
| 10.0 Citation Map & Graph Node Network | Post-MVP | Optional for v1 — depends on 9.0 |
| 11.0 Graph-Aware Retrieval | Post-MVP | Optional for v1 — depends on 10.0 |
| 12.0 Reranking Upgrade | Post-MVP | Optional for v1 |
| 13.0 Context Compression | Post-MVP | Optional for v1 |
| 14.0 Mixture of Agents (opt-in mode) | Post-MVP | Optional for v1 |
| 15.0 GPU Swap-In | Blocked on quota | Optional for v1 |
| 16.0 Enterprise Hardening | Ongoing, 20+ clients | Optional for v1 |

**Dependency note:** Phases 9.0 → 10.0 → 11.0 form a strict chain (bbox trust layer → graph build → graph query) and must be built in that order. Phases 6.0, 7.0, 8.0, 12.0, 13.0, and 14.0 are independent of each other and of the graph chain, and can be resequenced or parallelized across team members if capacity allows.

**End-to-end flow recap (start to finish):**
`0.0 Foundations` (safety nets) → `0.1 Model abstraction` → `1.0 Ingest` → `2.0 Store & Search` → `3.0 Synthesize` → `4.0 Secure` → `5.0 Ship Frontend` → **MVP live** → `6.0 Memory/Rewrite` → `7.0 Trial` → `8.0 HyDE` → `9.0 Citation Trust Layer` → `10.0 Build Graph` → `11.0 Query Graph` → `12.0 Rerank` → `13.0 Compress` → `14.0 Mixture of Agents (opt-in)` → `15.0 GPU when ready` → `16.0 Scale to enterprise`.
