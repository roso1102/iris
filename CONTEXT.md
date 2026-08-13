# CONTEXT.md — Living Project Context for IRIS

<!-- STRICT TEMPLATE v1 — This file has a fixed structure. -->
<!-- RULES FOR ALL AGENTS (Command Code, Antigravity, any other): -->
<!-- 1. Section headers (## 1. … ## 6.) are FIXED. Never rename, reorder, merge, or add sections. -->
<!-- 2. Sections 1 and 3 are FROZEN (derived from README.md / SRS.md / ACTIONPLAN.md). Only the user may authorize changes. -->
<!-- 3. Sections 2, 5, 6 are updated only when reality changes (work done, new gotcha, new open question). -->
<!-- 4. Section 4 (Session Log) is append-only. Add ONE bullet per session at the bottom. Never edit or delete old bullets. -->
<!-- 5. Keep this file under ~160 lines. Trim only the oldest Session Log bullets if it grows. -->
<!-- 6. Do not reformat the file (headings, bullets, bold markers, the divider). -->
<!-- If you believe the template itself must change, propose it to the user — do not change it unilaterally. -->

---

## 1. What IRIS Is

IRIS is a secure, multi-tenant, spatially-grounded document Q&A platform on GCP. Clients upload dense PDFs (legal filings, gazettes, scanned reports) and ask natural-language questions. Answers carry **pixel-accurate citations** — clickable highlights mapped to exact bounding boxes on source pages. Built serverless-first, CPU-only, cost-capped by a $300 GCP credit. Frontend on Vercel (Next.js); backend on Cloud Run + Qdrant + Firestore + GCS + Pub/Sub + Vertex AI.

## 2. Current State

- **Phase:** Phase 0.0 **complete**. Phase 1.0 deployed and verified on Cloud Run (revision `00052-md6`). **Phase 2.0 implemented** — full retrieval pipeline: BM25 sparse tokenizer, RRF fusion, diversity dedup, async SearchOrchestrator (Standard + Deep), FastAPI retrieval_api (`/search`, cascading delete), v2 Qdrant collection (`iris_chunks_v2` w/ named vectors, binary quant, payload_m=16, keyword indexes). 72/72 unit tests green. Next: deploy to Cloud Run, run Phase 2.0 integration benchmarks (Tests 2-A through 2-F).
- **Implemented:** `ModelProvider` abstract class, `VertexAIProvider` (incl. `rewrite_query()`, `generate_hyde()`, `synthesize()`), `MockModelProvider`, `factory.py` (768-d Vertex AI verified live). Phase 0.0: 56 Terraform resources (VPC, subnet, connector, Cloud NAT, Firestore peering, Qdrant PSC, firewall, qdrant-1 e2-small asia-south1-b). Phase 1.0: Ingestion pipeline (preflight, Docling parser, 4-signal VLM Router, chunker, QdrantChunkStore, PDF splitter, doc hash cache), worker on Cloud Run (2 CPU, 8 GiB, 900s timeout, max-instances=10, concurrency=1). Billing kill switch at ₹500 cap. **Phase 2.0:** `services/common/retrieval/` (bm25 rank_bm25 tokenizer, RRF fusion, diversity dedup, table validator, async SearchOrchestrator). `services/common/ingestion/store.py` upgraded to `iris_chunks_v2` (named vectors dense+bm25_sparse, binary quant, payload_m=16, keyword indexes, search_dense/search_sparse/delete_by_doc/delete_by_session/get_by_ids). `services/retrieval_api/app.py` rewritten as FastAPI (`POST /search` standard+deep, `DELETE /documents/{id}`, `DELETE /sessions/{id}`, `/healthz`). `Chunk` model adds `session_id` + `source` to Qdrant payload. Deploy configs updated (requirements.txt, Dockerfile, deploy.sh env vars). 72/72 unit tests green across 12 test files.
- **Next up:** Run Phase 1.0 cloud integration tests (1-A through 1-I) per `.commandcode/plans/phase-1-cloud-integration-tests.md`.

## 3. Key Decisions (frozen — do not violate)

- **Serverless-first:** every compute component scales to zero; no idle billing.
- **CPU-only for MVP:** no GPU quota available. All model calls go through a `ModelProvider` interface so GPU swap-in later is a config change (`MODEL_BACKEND` env var), not a rewrite.
- **Tenant isolation at the engine level:** JWT `tenant_id` claim drives Qdrant filter rewriting server-side; never trust client-supplied tenant IDs. Firestore security rules enforce `request.auth.token.tenant_id == resource.data.tenant_id`.
- **Cost-capped by default:** billing circuit breaker + ingestion DLQ built in Phase 0.0, before any product code.
- **Page-wise VLM router:** Docling does layout extraction with bboxes; Gemini Vision is called ONLY for tables, figures, and low-text (<150 char) pages — never on clean text pages. Handles KrutiDev/DevLys legacy Hindi + scanned Devanagari without custom decoders.
- **Stack specifics:** Qdrant self-hosted on GCE VM (`is_tenant=True`, hybrid BM25 + cosine, RRF fusion, diversity/dedup pass); Vertex AI `text-embedding-004` (768-d); Gemini Flash synthesis; Firestore for sessions/history/quotas; GCS tenant-prefixed buckets.
- **Embeddings locked at 768-d for MVP:** `text-embedding-004` @ 768-d is the MVP standard (multilingual, verified live). The 3072-d `gemini-embedding-001` upgrade is explicitly **post-MVP** — it requires a full re-embed + Qdrant collection migration, not a config swap. Documented in `SRS.md` §5.2. Do not plan MVP work around 3072-d vectors.
- **Two query modes:** Standard (fast/free) and user-toggled Deep Search (SLM rewrite + HyDE + Vertex AI Ranking rerank).
- **Licensing:** Docling (MIT) OK; **Marker is banned** (Open-RAIL-M revenue trap). Cohere Rerank v3.5 is deprecating — use `rerank-4-fast` or Vertex AI Ranking API.
- **Milestone checklist (working state, not a locked decision):**
  - [x] Initial specification and roadmap committed & pushed to GitHub.
  - [x] Auto-loaded `.agents/AGENTS.md` and `CONTEXT.md` initialized.
  - [x] Implement `ModelProvider` abstract interface, `VertexAIProvider`, and `MockModelProvider` scaffold (Phase 0.1).
  - [x] Authenticate local gcloud CLI & verify live Vertex AI `text-embedding-004` 768-d embedding call.

---

## 4. Session Log (append-only — one bullet per session)

<!-- Format: `- YYYY-MM-DD · tool · what was done | decisions made | next step` — max 3 lines per bullet -->

- 2026-07-31 · discussion · Set up shared-context files (`COMMANDCODE.md` → `CONTEXT.md` ← `AGENTS.md`). Updated `CONTEXT.md` with complete project state and rules structure. Next: decide whether to start Phase 0.0 GCP scaffolding.
- 2026-07-31 · Command Code · Verified the bridge end-to-end: `COMMANDCODE.md` (Command Code, auto-load) and `.agents/AGENTS.md` (Antigravity, auto-load) both resolve to `CONTEXT.md` as the single source of truth. Confirmed the other agent's rewrite of `CONTEXT.md` preserved all key decisions. Next: decide whether to start Phase 0.0 GCP scaffolding, or Phase 0.1 `ModelProvider` scaffold.
- 2026-07-31 · Antigravity · Authenticated local `gcloud` CLI with GCP project `naturepivot-rag`. Successfully executed live Vertex AI `text-embedding-004` integration test returning 768-d vector. Next: proceed to Phase 1.0 Core Ingestion Worker.
- 2026-07-31 · Command Code · Locked embeddings at 768-d for MVP (`text-embedding-004`, multilingual) and documented the 3072-d `gemini-embedding-001` upgrade as explicitly post-MVP (re-embed + Qdrant migration required) in `SRS.md` §5.2. Updated `CONTEXT.md` §3 with the decision. Next: Phase 1.0 Core Ingestion Worker — Task 1.1 tenant-prefixed GCS buckets.
- 2026-07-31 · Antigravity · Created `BENCHMARK.md` containing the technical RAG evaluation suite (Recall@5, MRR, RAGAS Faithfulness, WER, Latency P95, and comparison baselines). Next: Phase 1.0 Core Ingestion Worker.
- 2026-07-31 · Command Code · Wrote Phase 0.0 (Terraform infra, billing kill-switch function, hello-world services, CI, Firebase script) + Phase 1.0 core (preflight, Docling parser, VLM Router, chunker, ChunkStore memory/Qdrant, worker Pub/Sub app) + 4 unit-test files. 23 tests green; live Vertex AI 768-d test still passes. Folded in corrections: `is_tenant` is not a real Qdrant param, and table/picture elements route to VLM **before** the low-text check. Next: **human handoff** — terraform apply, setup_firebase.sh, deploy.sh, then Phase 1.0 integration tests 1-A…1-H.
- 2026-08-01 · Command Code · Phase 0.0 infra APPLIED: fixed label regex (GCP disallows dots), `aiplatform` API name (not `vertexai`), `roles/aiplatform.user`, VPC connector /28 subnet, Pub/Sub `max_delivery_attempts=5` (min raised), Cloud Run services moved to deploy.sh (images must exist first). 53 resources live incl. VPC/peering/PSC, secrets, bucket, topics, SAs. Billing budget deferred (`enable_billing_budget=false`) — requires Billing Account Administrator/Costs Manager which rohit lacks (manoj has owner). Next: setup_firebase.sh, deploy.sh, Test 0-A.
- 2026-08-01 · Command Code · Phase 0.0 COMPLETE: Firebase linked (org-policy permission fix required `roles/firebase.admin`+`roles/orgpolicy.policyAdmin` granted by manoj), budget connected to `billing-alerts` topic (Console-only step — `billing-<ID>@...` SA never exists; real SA is `billing-budget-alert@system.gserviceaccount.com`), both services built + deployed + healthy, kill-switch function deployed + verified (pushConfig detach via Pub/Sub Python client, 15 iterations to fix runtime deps/proto field names/Cloud Run v2 PATCH failures; Test 0-A passes). 45+ IAM bindings across project/org/billing/run/pubsub/artifact-registry/storage. Known quirks: `max-instances=0` rejected by Cloud Run (Knative requires positive integer), `gcloud` CLI absent from Cloud Functions gen2 Python runtime, `iam.allowedPolicyMemberDomains` org policy required project-level ALLOW override for billing SA. Next: Phase 1.0 integration tests 1-A…1-H.
- 2026-08-04 · Command Code · Security hardening pass: fixed 10 findings across 5 source files — prompt injection sanitization (vertex.py), cross-tenant Qdrant filter (store.py), QA view auth gate (qa_view.py), local dev path traversal (main.py), billing kill-switch fail-fast (billing-kill-switch/main.py), threading.Lock on MemoryChunkStore, image size validation + retry on Gemini Vision, exact model name map, hardcoded GCP_PROJECT removal, empty response crash protection. Added `tests/test_ingestion_security.py` (16 new tests, 28 total green). Installed graphify (368 nodes, 952 edges, 21 communities) with git hooks for auto-rebuild on commit. Moved graphify instructions from `CLAUDE.md` to `COMMANDCODE.md`. Next: Phase 2.0 Vector Store & Retrieval.
- 2026-08-06 · Antigravity · Fixed CI build: resolved test_local_dev_allows_test_docs_path failure with dynamic dummy PDF creation and gated test_vertex_embedding behind RUN_VERTEX_LIVE_TESTS variable. Swapped default region from us-central1 to asia-south1 throughout (models, terraform config, setup script, SRS.md). Next: Phase 2.0 implementation.
- 2026-08-06 · Command Code · Reviewed and updated Phase 1.0 cloud integration test plan: wired GET /memory QA endpoint in app.py, added DLQ pull subscription in pubsub.tf, made QdrantChunkStore collection creation idempotent, corrected preflight DLQ expectations. Ran live Vertex AI 768-d embedding test (PASSED). Next: deploy updated worker to Cloud Run.
- 2026-08-08 · Command Code · Phase 1.0 complete: deployed ingestion-worker v00052-md6 with full pipeline verified end-to-end. Fixed 14 issues across 5 rebuild cycles — Pub/Sub parsing, OpenCV deps (libgl1/libxcb1/g++), TORCH_COMPILE_DISABLE (4× cold start speedup), Qdrant collection idempotency, _crop_bbox bbox clamping, VLM fallback on failure, vertexai SDK, Cloud NAT for Qdrant VM egress, split-routing to us-central1, model names (gemini-2.5-flash). Benchmarked: 121s cold start (2 pages, 10 chunks, 2 VLM calls). Parallel dispatch verified: 2 pages concurrent, 5× projected for 35-page docs. Billing kill switch at ₹500 cap. Next: run 1-A through 1-I integration tests.
- 2026-08-09 · Command Code · Phase 2.0 retrieval pipeline implemented: `services/common/retrieval/` (bm25, rrf, diversity, validator, search orchestrator, models), v2 Qdrant collection schema (iris_chunks_v2 w/ named vectors, binary quant, payload_m=16, keyword indexes), FastAPI retrieval-api (POST /search standard+deep, DELETE /documents, DELETE /sessions), cascading delete, deploy configs updated. `retrieval-api` renamed to `retrieval_api` for Python import. 72/72 unit tests green. Graphify: 878 nodes, 1670 edges, 83 communities. Next: deploy to Cloud Run, run Phase 2.0 integration benchmarks.
- 2026-08-09 · Antigravity · Updated ACTIONPLAN.md with Phase 2.0 non-negotiables (async non-blocking event loop, Cloud Logging search observability, rank_bm25 TF-IDF upgrade) and added Phase 2.5 Empirical Validation & Hardening (RAGAS evaluation, VLM table validation, HyDE/Reranker A/B benchmarks). Next: Phase 2.0 implementation.


---

## 5. Gotchas & Notes

- Service Account Creation: `iris-backend-sa` created under Application data. Granting project-level IAM roles (Vertex AI User, Storage Admin, Datastore User) requires `resourcemanager.projects.setIamPolicy` permission or can be assigned via GCP project IAM settings / local `gcloud auth application-default login`.
- Docling emits normalized `[left, top, right, bottom]` bbox per element — verify coordinate space against PDF.js rendering in Phase 5.0.
- Phase numbering in ACTIONPLAN has a known quirk: Phase 15.0 and 16.0 reuse task numbers (10.x / 11.x) — don't let that confuse references.
- Chunking target: ~512 tokens, sentence-boundary; VLM outputs become single chunks with the source element's bbox.
- `is_tenant=True` (ACTIONPLAN Task 2.2) is **not a real Qdrant parameter**. Real tenant-filter performance comes from `payload_m` in HNSW config + a `tenant_id` keyword payload index + mandatory tenant filter on every query. Phase 2.0 must use these instead.
- VLM Router ordering: Table/Picture elements route to Gemini Vision **before** the <150-char low-text check — structural elements always go to VLM regardless of char count (fixed in `vlm_router.py`; tests enforce it).
- Docling runs **inside the ingestion-worker Cloud Run container** (CPU + onnxruntime), not on the laptop; the Dockerfile must warm the model cache at build time so cold starts don't re-download weights.
- Latency budgets that gate acceptance: `/search` < 500ms, `/query` < 2s, rewrite step < 300ms, HyDE < 400ms, graph traversal < 300ms.
- Kill switch does NOT set `max-instances=0` — Cloud Run rejects it (Knative requires positive integer). Instead, detaches the push endpoint from the ingestion subscription (`pushConfig={}`) to halt new deliveries while preserving existing chunks.
- `gcloud` CLI is NOT available in the Cloud Functions gen2 Python runtime. The kill switch uses `google-cloud-pubsub` Python client instead (`google.pubsub_v1.types.PushConfig` + `google.protobuf.field_mask_pb2.FieldMask`).
- Billing budget→topic connection is Console-only: `billing-<ID>@billing.gserviceaccount.com` SA never exists to bind programmatically; the real SA is `billing-budget-alert@system.gserviceaccount.com`, auto-created by the Console flow.
- Org policy `iam.allowedPolicyMemberDomains` required a project-level ALLOW override on `naturepivot-rag` (to allow the Google billing SA). The clean org-level fix (appending `gserviceaccount.com`) was rejected — the policy uses encoded customer IDs (`C02t34gra` format), not domain strings.
- Vertex AI API quota caps (to be set once billing account is upgraded from free trial to pay-as-you-go): `generate_content_requests_per_minute` = 15, `online_prediction_requests_per_minute` = 60. Free trial / promotional credit accounts cannot manually adjust API quotas — the Console sliders are locked until the billing account is upgraded. Once upgraded, set these in Console at APIs & Services → Vertex AI API → Quotas. If ingestion starts returning `429 RESOURCE_EXHAUSTED` before the caps are set, it means Vertex AI is being called faster than the default trial limits allow.

## 6. Open Questions

- When to actually start Phase 0.0 (needs GCP account access + the $300 credit org).
- Trial/freemium credit model numbers (1 page ≈ 5 credits, 1 query ≈ 1 credit are placeholders).
- Whether Deep Search should be enabled at MVP or held for Phase 8.0+.
