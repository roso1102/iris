# Graph Report - iris  (2026-08-22)

## Corpus Check
- 123 files · ~134,300 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1536 nodes · 2680 edges · 123 communities (91 shown, 32 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 155 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c6e7542b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_rate_limit.py
- Citation
- retrieval_api/app.py
- package.json
- What You Must Do When Invoked
- parser.py
- query
- test_docling_pipeline.py
- kill_switch
- QdrantChunkStore
- create_iam_alert.sh
- deploy.sh
- setup_firebase.sh
- TestSignal5
- Phase 4.0 — Authentication & Multi-Tenant Security ✅ COMPLETE
- Phase 7.0 — Trial / Freemium & Rate Limiting
- ingestion/main.py
- Phase 12.0 — Neural Reranking Upgrade & Precision Engineering
- MockVlmRouter
- bm25_cache
- VertexAIProvider
- graphify reference: extra exports and benchmark
- CONTEXT.md — Living Project Context for IRIS
- graphify reference: query, path, explain
- Command Code — project instructions (auto-loaded each session)
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- extraction-spec.md
- 3. Functional Requirements
- ingestion-worker/app.py
- IRIS Technical Benchmark Suite & Evaluation Framework
- IRIS Frontend Architecture & UI Specification (Phase 5.0 & Beyond)
- TestSessionsApi
- IRIS
- upload_document
- eval_phase2.py
- IRIS — Phased Action Plan
- auth_headers
- Phase 0.0 — Foundations & Safety Nets
- Phase 1.0 — Core Ingestion Pipeline ✅ (complete)
- Phase 2.0 — Vector Store & Retrieval
- Phase 3.0 — LLM Synthesis Layer ✅ (complete)
- Phase 3.5 — Retrieval Precision & Citation Quality Hardening (Lite) ✅ (complete)
- Phase 5.0 — Frontend Integration (Vercel)
- Phase 0.1 — Model Provider Abstraction Scaffold
- TestAuthDependency
- Phase 6.0 — Conversational Memory + SLM-Based Query Rewrite ("Supermemory-Lite")
- Phase 8.0 — Rephraser & Hypothesis Generator (HyDE)
- Phase 9.0 — Citation & Bbox Management Layer
- Phase 10.0 — Citation Map & Graph Node Network (Ingestion-Time)
- Phase 11.0 — Graph-Aware Retrieval (Query the Graph & Semantic Relationships)
- vlm_router.py
- Phase 14.0 — Mixture of Agents (MoA) Synthesis
- Phase 15.0 — GPU Swap-In (When Quota Available)
- Shared Context & Working Agreement
- test_4b_live.js
- Phase 16.0 — Enterprise Scale Hardening
- .commandcode/taste/taste.md
- taste/taste/taste.md
- text_to_sparse
- backfill_document_records.py
- TestIngestionPipelineWiring
- rules.test.js
- MockModelProvider
- mock_auth
- check_pdf
- test_docling_large.py
- ParsedElement
- Phase 16.0 — Enterprise Hardening & Zero-Trust Infrastructure
- ChunkStore
- TestMemoryChunkStoreSearch
- validate_table_markdown
- provision_eval_user.py
- TestPubSubEnvelopeDecode
- Phase 2.5 — Empirical Validation & Pipeline Hardening
- test_delete_cascade.py
- TestRouterSignals
- TestGroundTruthRouting
- ABC
- Path
- claims.py
- IRIS Roadmap: Phase 6+ Execution Plan with Citation/Bbox/Rerank Fixes
- IngestionPipeline
- MemoryChunkStore
- ModelProvider
- ingestion/models.py
- get
- ModelProvider
- ABC
- ABC
- SearchOrchestrator
- IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2)
- get
- post
- build_qa_response
- IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2)
- jwt.py
- FastAPI
- ScoredChunk
- chunk_routed
- BaseModel
- StructuredAnswer
- IRIS Retrieval Quality + Citation Correctness — Implementation Plan
- TestMemoryChunkStoreThreadSafety
- Exception
- TestDownloadLocalDevGate
- Chunk
- SelfHostedGPUProvider
- test_cors.py
- TestDeepSearch
- RoutingResult
- RecordingProvider
- PageRenderer
- auth_testing.py
- _build_synthesis_context
- .embed

## God Nodes (most connected - your core abstractions)
1. `MemoryChunkStore` - 61 edges
2. `MockModelProvider` - 41 edges
3. `auth_headers()` - 40 edges
4. `mock_auth()` - 39 edges
5. `ModelProvider` - 37 edges
6. `VertexAIProvider` - 33 edges
7. `ElementType` - 33 edges
8. `RouteDecision` - 32 edges
9. `ParsedElement` - 32 edges
10. `MockVlmRouter` - 32 edges

## Surprising Connections (you probably didn't know these)
- `RecordingProvider` --uses--> `MemoryChunkStore`  [INFERRED]
  tests/test_deep_search.py → services/common/ingestion/store.py
- `TestDeepSearch` --uses--> `MemoryChunkStore`  [INFERRED]
  tests/test_deep_search.py → services/common/ingestion/store.py
- `TestDoclingTrueassortCorpus` --uses--> `MemoryChunkStore`  [INFERRED]
  tests/test_docling_integration.py → services/common/ingestion/store.py
- `TestDoclingLargeCPU` --uses--> `MemoryChunkStore`  [INFERRED]
  tests/test_docling_large.py → services/common/ingestion/store.py
- `TestDoclingPipelineTrueassort` --uses--> `MemoryChunkStore`  [INFERRED]
  tests/test_docling_pipeline.py → services/common/ingestion/store.py

## Import Cycles
- None detected.

## Communities (123 total, 32 thin omitted)

### Community 0 - "test_rate_limit.py"
Cohesion: 0.11
Nodes (8): FixedWindowRateLimiter, Per-tenant in-memory rate limiting (Phase 4.0 interim). Fixed-window limiter…, Thread-safe fixed-window limiter keyed by tenant_id., Raise 429 if `key` has exceeded the window budget., _chunk(), Phase 4.0 tests — per-tenant rate limiting., TestFixedWindowRateLimiter, TestRateLimitEndpoint

### Community 1 - "Citation"
Cohesion: 0.10
Nodes (31): BaseModel, Citation, DeleteResponse, DocStatusResponse, BaseModel, QueryRequest, QueryResponse, Phase 2.0 retrieval data models (Phase 4.0: request-size guards). (+23 more)

### Community 2 - "retrieval_api/app.py"
Cohesion: 0.18
Nodes (19): delete, delete_document(), _delete_firestore_doc(), _delete_firestore_session(), _delete_gcs_blob(), delete_session(), _get_firestore_client(), _get_gcs_client() (+11 more)

### Community 3 - "package.json"
Cohesion: 0.12
Nodes (15): firebase, @firebase/rules-unit-testing, firebase-tools, description, devDependencies, firebase, @firebase/rules-unit-testing, firebase-tools (+7 more)

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 5 - "parser.py"
Cohesion: 0.09
Nodes (25): ABC, ParsedElement, Path, _bbox_of(), _bbox_of_items(), DoclingParser, DocParser, _page_of() (+17 more)

### Community 6 - "query"
Cohesion: 0.17
Nodes (19): AuthContext, QueryRequest, SearchRequest, ID validation + request-size guards (Phase 4.0). Prevents path traversal, NoSQL…, Truncate history to the sliding window instead of rejecting it., _reject(), validate_doc_id(), validate_history() (+11 more)

### Community 7 - "test_docling_pipeline.py"
Cohesion: 0.24
Nodes (7): DoclingParser, integration, Path, Docling pipeline integration tests — parse/route/chunk/store against…, Parse -> route -> chunk -> store roundtrip on the golden corpus., run_pipeline(), TestDoclingPipelineTrueassort

### Community 8 - "kill_switch"
Cohesion: 0.47
Nodes (5): cloud_event, _kill_ingestion(), kill_switch(), Set pushConfig to empty on the subscription (pull-only)., _should_kill()

### Community 9 - "QdrantChunkStore"
Cohesion: 0.12
Nodes (9): Chunk, QdrantChunkStore, Phase 2.0 Qdrant store — v2 named-vector collection, hybrid search, cascading…, Return all chunks of a document on the given pages, tenant-scoped. Stage 3c…, _chunk(), Tier 2 live smoke tests — Qdrant connectivity and read/write path. Run only…, _store(), test_collection_health() (+1 more)

### Community 13 - "TestSignal5"
Cohesion: 0.12
Nodes (9): Verify FIX-008 Signal 5 non-Latin detection fires on Hindi, not English., Hindi page (valid_word_ratio ~0.82–0.87) must trigger Signal 5., Clean English text must never trigger Signal 5., English text with numerals/punctuation stays Latin-dominant., A short Hindi clause still exceeds the 30% letter threshold., Empty and ASCII-only inputs never trigger Signal 5., A page that is exactly 30% non-Latin does NOT trigger (strict >)., Punctuation-only (no letters) never triggers Signal 5. (+1 more)

### Community 14 - "Phase 4.0 — Authentication & Multi-Tenant Security ✅ COMPLETE"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 4.0 — Authentication & Multi-Tenant Security ✅ COMPLETE, Scope, Services Touched, Tasks

### Community 15 - "Phase 7.0 — Trial / Freemium & Rate Limiting"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 7.0 — Trial / Freemium & Rate Limiting, Scope, Services Touched, Tasks

### Community 16 - "ingestion/main.py"
Cohesion: 0.21
Nodes (11): IngestResult, Exception, Path, Ingestion orchestrator (ACTIONPLAN Tasks 1.2-1.9). Order: preflight -> download…, Payload must be rejected forever (never queued / straight to DLQ)., Transient failure; Pub/Sub should redeliver (up to 3 attempts)., Full pipeline for one uploaded document or single-page blob., RejectError (+3 more)

### Community 17 - "Phase 12.0 — Neural Reranking Upgrade & Precision Engineering"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 12.0 — Neural Reranking Upgrade & Precision Engineering, Scope, Services Touched, Tasks

### Community 18 - "MockVlmRouter"
Cohesion: 0.23
Nodes (8): MockVlmRouter, Deterministic router for tests: routes but never calls a real VLM., _el(), Phase 1.0 unit tests — Page-Wise VLM Router (Task 1.5). Covers Test 1-D (table…, Test 1-F: clean text pages never trigger a VLM call., Test 1-D: table element -> VLM table route, markdown output., Test 1-E: low-text element (<150 chars) -> full-page VLM., TestVlmRouter

### Community 19 - "bm25_cache"
Cohesion: 0.40
Nodes (4): fixture, bm25_cache(), Shared pytest fixtures. Bakes the FastEmbed Qdrant/bm25 model into a temp cache…, Download Qdrant/bm25 into a session-scoped temp HF cache and wire it up.…

### Community 21 - "VertexAIProvider"
Cohesion: 0.08
Nodes (16): Exception, _is_resource_exhausted(), Cached TextEmbeddingModel — from_pretrained per call re-resolves the endpoint…, Cross-encoder reranking via the Vertex AI Ranking API (Phase 12.1). POST…, Return True if the exception is a Vertex/API rate-limit condition., Valid ADC access token for the discoveryengine endpoint, cached., Production Vertex AI implementation for GCP Cloud Run. Embeddings run in-region…, _sanitize_context() (+8 more)

### Community 22 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 23 - "CONTEXT.md — Living Project Context for IRIS"
Cohesion: 0.25
Nodes (7): 1. What IRIS Is, 2. Current State, 3. Key Decisions (frozen — do not violate), 4. Session Log (append-only — one bullet per session), 5. Gotchas & Notes, 6. Open Questions, CONTEXT.md — Living Project Context for IRIS

### Community 24 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 25 - "Command Code — project instructions (auto-loaded each session)"
Cohesion: 0.33
Nodes (5): Command Code — project instructions (auto-loaded each session), First, read the shared context, graphify, STRICT TEMPLATE RULES for CONTEXT.md (mandatory), Working agreement

### Community 26 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 27 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 28 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 33 - "3. Functional Requirements"
Cohesion: 0.05
Nodes (40): 1.1 Purpose, 1.2 Scope, 1.3 Definitions, 1.4 Constraints Provided by the Business, 1. Introduction, 2.1 Product Perspective, 2.2 User Classes, 2.3 Operating Environment (+32 more)

### Community 34 - "ingestion-worker/app.py"
Cohesion: 0.06
Nodes (48): Client, IngestionPipeline, PublisherClient, compute_sha256(), _download_pdf(), Path, Page-level PDF splitter for parallel ingestion dispatch. Downloads a PDF from…, Upload a file to GCS. (+40 more)

### Community 35 - "IRIS Technical Benchmark Suite & Evaluation Framework"
Cohesion: 0.08
Nodes (23): 1.1 Hit Rate / Recall@K, 1.2 Mean Reciprocal Rank (MRR), 1.3 Precision@K, 1.4 Hybrid Search Lift (Dense vs. BM25 vs. Hybrid + RRF), 1. Retrieval Quality Metrics, 2.1 Faithfulness Score (Hallucination Detection), 2.2 Answer Relevancy, 2.3 Context Recall (+15 more)

### Community 36 - "IRIS Frontend Architecture & UI Specification (Phase 5.0 & Beyond)"
Cohesion: 0.09
Nodes (21): 1.1 Typography & Fonts, 1.2 Theme Configuration (Radix UI / Tailwind / shadcn), 1.3 Exact Color Palettes (Custom Emerald Scale — Base: `#047857`), 1.4 Mode-Specific Modality Palettes, 🎨 1. Design System, Typography & Color Palette, 🏛️ 2. Core Architecture & Folder Structure, 3.1 Flat Routing with Query Parameters, 3.2 Strict Anti-IDOR Rule (Security Boundary) (+13 more)

### Community 37 - "TestSessionsApi"
Cohesion: 0.12
Nodes (5): _fake_firestore(), Phase 4.0 tests — session CRUD endpoints + signed view URL., Firestore mock: document().get/set/update/delete tracked, collection stream…, TestSessionsApi, TestViewUrl

### Community 38 - "IRIS"
Cohesion: 0.15
Nodes (12): 1. What This System Does, 2. Core Design Principles, 3. Technology Stack, 4. High-Level Architecture, 5. Getting Started (Once Implementation Begins), 6. Repository Structure (Target), 7. Key Documents, 8. Guiding Constraints (Do Not Violate) (+4 more)

### Community 39 - "upload_document"
Cohesion: 0.16
Nodes (13): post, _create_document_record(), create_session(), Create the Firestore ownership record so view-url/delete work. The record also…, Call ingestion-worker /ingest to preflight + split + fan out to Pub/Sub.…, Create a named workspace session scoped to the verified tenant., Upload a PDF and trigger ingestion (Task 5.0b). Flow: validate doc_id + file ->…, _server_timestamp() (+5 more)

### Community 40 - "eval_phase2.py"
Cohesion: 0.08
Nodes (50): check_tenant_isolation(), compute_mrr(), compute_page_recall_at_k(), compute_recall_at_k(), compute_source_duplication(), _firebase_id_token(), _get_firebase_api_key(), _id_token() (+42 more)

### Community 41 - "IRIS — Phased Action Plan"
Cohesion: 0.15
Nodes (12): Benchmarks & Testing, Deployment & Containerization Strategy, Exit Criteria, How per-phase checkpointing still works without per-phase containers, IRIS — Phased Action Plan, 🏁 MVP LAUNCH BOUNDARY, Phase 13.0 — Context Compression, Scope (+4 more)

### Community 42 - "auth_headers"
Cohesion: 0.24
Nodes (3): auth_headers(), Headers for a request whose token maps to the given claims (mock-active)., TestUploadApi

### Community 43 - "Phase 0.0 — Foundations & Safety Nets"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 0.0 — Foundations & Safety Nets, Scope, Services Touched, Tasks

### Community 44 - "Phase 1.0 — Core Ingestion Pipeline ✅ (complete)"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 1.0 — Core Ingestion Pipeline ✅ (complete), Scope, Services Touched, Tasks

### Community 45 - "Phase 2.0 — Vector Store & Retrieval"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 2.0 — Vector Store & Retrieval, Scope, Services Touched, Tasks

### Community 46 - "Phase 3.0 — LLM Synthesis Layer ✅ (complete)"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 3.0 — LLM Synthesis Layer ✅ (complete), Scope, Services Touched, Tasks

### Community 47 - "Phase 3.5 — Retrieval Precision & Citation Quality Hardening (Lite) ✅ (complete)"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 3.5 — Retrieval Precision & Citation Quality Hardening (Lite) ✅ (complete), Scope, Services Touched, Tasks

### Community 48 - "Phase 5.0 — Frontend Integration (Vercel)"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 5.0 — Frontend Integration (Vercel), Scope, Services Touched, Tasks

### Community 49 - "Phase 0.1 — Model Provider Abstraction Scaffold"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 0.1 — Model Provider Abstraction Scaffold, Scope, Services Touched, Tasks

### Community 51 - "Phase 6.0 — Conversational Memory + SLM-Based Query Rewrite ("Supermemory-Lite")"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 6.0 — Conversational Memory + SLM-Based Query Rewrite ("Supermemory-Lite"), Scope, Services Touched, Tasks

### Community 52 - "Phase 8.0 — Rephraser & Hypothesis Generator (HyDE)"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 8.0 — Rephraser & Hypothesis Generator (HyDE), Scope, Services Touched, Tasks

### Community 53 - "Phase 9.0 — Citation & Bbox Management Layer"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 9.0 — Citation & Bbox Management Layer, Scope, Services Touched, Tasks

### Community 54 - "Phase 10.0 — Citation Map & Graph Node Network (Ingestion-Time)"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 10.0 — Citation Map & Graph Node Network (Ingestion-Time), Scope, Services Touched, Tasks

### Community 55 - "Phase 11.0 — Graph-Aware Retrieval (Query the Graph & Semantic Relationships)"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 11.0 — Graph-Aware Retrieval (Query the Graph & Semantic Relationships), Scope, Services Touched, Tasks

### Community 56 - "vlm_router.py"
Cohesion: 0.12
Nodes (21): _crop_bbox(), _is_non_latin_dominant(), _load_cached_vlm(), _page_text_stats(), ABC, Path, Page-Wise VLM Router (ACTIONPLAN Task 1.5). Per page, per element, decide the…, Return fraction of characters from recognizable script categories. Characters… (+13 more)

### Community 57 - "Phase 14.0 — Mixture of Agents (MoA) Synthesis"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 14.0 — Mixture of Agents (MoA) Synthesis, Scope, Services Touched, Tasks

### Community 58 - "Phase 15.0 — GPU Swap-In (When Quota Available)"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 15.0 — GPU Swap-In (When Quota Available), Scope, Services Touched, Tasks

### Community 59 - "Shared Context & Working Agreement"
Cohesion: 0.33
Nodes (5): Agent Workflow Discipline, AGENTS.md — Instructions for AI Coding Agents (Auto-loaded), Key Binding Decisions, Shared Context & Working Agreement, STRICT TEMPLATE RULES for CONTEXT.md (mandatory)

### Community 60 - "test_4b_live.js"
Cohesion: 0.28
Nodes (8): fs, fsGet(), fsWrite(), { getFirestore, doc, getDoc, setDoc, collection, getDocs }, { initializeApp }, main(), tokenA, tokenB

### Community 61 - "Phase 16.0 — Enterprise Scale Hardening"
Cohesion: 0.40
Nodes (5): Benchmarks & Testing, Exit Criteria, Phase 16.0 — Enterprise Scale Hardening, Scope, Tasks

### Community 64 - "text_to_sparse"
Cohesion: 0.07
Nodes (25): _get_model(), BM25 sparse vector tokenizer backed by FastEmbed's Qdrant/bm25 model. Replaces…, Convert to Qdrant SparseVector-compatible (indices, values) pair., Return the term indices encoded for `text` (for tests/debugging). FastEmbed's…, Return the model cache dir, preferring the explicitly-set path. Resolution…, Lazily initialize the singleton FastEmbed Bm25 model (thread-safe). Loads…, Encode text into {term_index: raw_term_count} via Qdrant/bm25. When…, _resolve_cache_dir() (+17 more)

### Community 66 - "TestIngestionPipelineWiring"
Cohesion: 0.15
Nodes (11): MockDocParser, Deterministic parser for local tests (MODEL_BACKEND=mock)., Path, Parse -> route -> chunk -> store, driven through the production objects., MockDocParser's 4 elements flow through router -> chunker -> store., Elements land on pages 1 and 2 as MockDocParser emits them., Table -> VLM_TABLE, Picture -> VLM_PICTURE, short text -> VLM_FULL_PAGE., Chunks stored under tenant-a never leak to tenant-b. (+3 more)

### Community 67 - "rules.test.js"
Cohesion: 0.25
Nodes (4): fs, { initializeTestEnvironment, assertFails, assertSucceeds }, path, RULES_PATH

### Community 68 - "MockModelProvider"
Cohesion: 0.13
Nodes (5): get_model_provider(), Factory function returning the active ModelProvider instance. MODEL_BACKEND…, MockModelProvider, Mock implementation returning deterministic outputs for local testing., TestModelProviderScaffold

### Community 69 - "mock_auth"
Cohesion: 0.13
Nodes (5): Chunk, A content unit ready to embed + store., mock_auth(), Patch the JWT verifier to return a fixed AuthContext. The token string itself…, TestRetrievalApi

### Community 70 - "check_pdf"
Cohesion: 0.08
Nodes (26): check_pdf(), PreflightError, Exception, Path, Pre-ingestion payload scanner (ACTIONPLAN Task 1.2). Rejects payloads BEFORE…, Raised when a payload is rejected before processing., Validate a PDF file before it enters the pipeline. Returns metadata dict:…, _load_labels() (+18 more)

### Community 71 - "test_docling_large.py"
Cohesion: 0.24
Nodes (7): DoclingParser, integration, Path, Docling CPU pipeline tests — run the full trueassort/ corpus on CPU. Run:…, Parse the full 8-doc corpus on CPU and verify no doc is empty., run_pipeline(), TestDoclingLargeCPU

### Community 72 - "ParsedElement"
Cohesion: 0.17
Nodes (9): ParsedElement, BaseModel, One element extracted by Docling, normalized for the router., Apply the routing table to a parsed document., A routed element: either Docling text or a VLM call output., RoutingResult, FIX-005 wiring: page_number_override reaches every stored chunk., Parser -> router -> chunker -> embedder -> MemoryChunkStore. (+1 more)

### Community 73 - "Phase 16.0 — Enterprise Hardening & Zero-Trust Infrastructure"
Cohesion: 0.33
Nodes (6): Deliverables, Exit Criteria, Phase 16.0 — Enterprise Hardening & Zero-Trust Infrastructure, Scope, Services Touched, Tasks

### Community 74 - "ChunkStore"
Cohesion: 0.11
Nodes (11): get_cached_chunks(), Document hash cache for ingestion deduplication. If a PDF has been previously…, Check if doc SHA256 has been previously stored. Returns list of Chunks if…, ChunkStore, Persist chunks; returns the number written., Return all chunks for a document, enforcing tenant isolation., Dense cosine vector search with tenant + optional doc filters. Returns…, BM25 sparse vector search with tenant + optional doc filters. Returns… (+3 more)

### Community 76 - "validate_table_markdown"
Cohesion: 0.26
Nodes (5): Phase 2.5 — VLM table markdown validation. Validates that VLM-extracted…, Validate VLM-extracted Markdown table structure. Returns True if row/column…, validate_table_markdown(), Phase 2.5 unit tests — table markdown validator., TestTableValidator

### Community 77 - "provision_eval_user.py"
Cohesion: 0.47
Nodes (5): _create_user_if_missing(), _credentials(), main(), Build Firebase Admin credentials from a token, or fall back to ADC., Return the user UID, creating the account first if needed.

### Community 78 - "TestPubSubEnvelopeDecode"
Cohesion: 0.36
Nodes (3): _load_worker_module(), FIX-005 — page_number must survive the Pub/Sub push envelope., TestPubSubEnvelopeDecode

### Community 79 - "Phase 2.5 — Empirical Validation & Pipeline Hardening"
Cohesion: 0.33
Nodes (6): Deliverables, Exit Criteria, Phase 2.5 — Empirical Validation & Pipeline Hardening, Scope, Services Touched, Tasks

### Community 80 - "test_delete_cascade.py"
Cohesion: 0.13
Nodes (7): _chunk(), Tier 1 integration tests — cascading delete (store + API level). Store level:…, MemoryChunkStore.delete_by_doc cascade semantics., DELETE endpoints remove store chunks AND cascade to Firestore/GCS mocks., Return a firestore-mock whose .document(path).delete() is tracked., TestApiDeleteCascade, TestStoreDeleteCascade

### Community 81 - "TestRouterSignals"
Cohesion: 0.21
Nodes (9): _el(), Verify the production `_route_element` signal table directly., fast_text tier: high word ratio + enough chars -> zero API cost., Signal 4: low-total-text page -> full-page OCR (page-level check)., Signal 4 is page-level: a short footer/heading on a text-rich page must NOT…, Signal 2: garbled OCR / unmapped encoding -> full-page OCR., Signal 3 case A: coverage < 0.15 and few chars., A sparse but valid text page (coverage 0.20) stays fast_text today. This… (+1 more)

### Community 83 - "TestGroundTruthRouting"
Cohesion: 0.17
Nodes (8): _load_pages(), 127 pages: high ratio + high coverage -> zero VLM cost., 58 pages: tables (Signal 1) or low-coverage sparse -> VLM., 5 pages (Hindi/Devanagari): Signal 5 must fire despite high ratio., 11 pages: 0.75-0.88 ratio -> DOCLING_TEXT (or VLM_TABLE if has_table)., Aggregate: every labeled page matches ground truth (no regressions)., Every labeled page in the CSV must route as the ground truth says., TestGroundTruthRouting

### Community 87 - "IRIS Roadmap: Phase 6+ Execution Plan with Citation/Bbox/Rerank Fixes"
Cohesion: 0.13
Nodes (14): Background (verified facts), Current ACTIONPLAN phase map (post-Phase 5), Execution plan (phase by phase), Files to touch, Goal, IRIS Roadmap: Phase 6+ Execution Plan with Citation/Bbox/Rerank Fixes, Open decision, Phase 10.0 → 11.0 — Graph layers (stay in place, after 9.0) (+6 more)

### Community 88 - "IngestionPipeline"
Cohesion: 0.24
Nodes (3): IngestionPipeline, Chunk, TestIngestionPipelineConstructor

### Community 90 - "MemoryChunkStore"
Cohesion: 0.13
Nodes (12): get_chunk_store(), MemoryChunkStore, Chunk store (ACTIONPLAN Task 1.9 + Phase 2.0 retrieval). `ChunkStore` ABC with…, Factory: QdrantChunkStore when QDRANT_URL is set, else MemoryChunkStore., In-memory store for dev/tests. Thread-safe., Docling pipeline integration tests — run against trueassort/ golden corpus.…, Phase 2.0 unit tests — ChunkStore search/delete methods (MemoryChunkStore)., TestRetrievalStoreFactory (+4 more)

### Community 92 - "ingestion/models.py"
Cohesion: 0.14
Nodes (18): Enum, ElementType, Shared data model for the IRIS ingestion pipeline. A `Chunk` is the unit…, Docling element labels, normalized for the pipeline., Page-Wise VLM Router outcome for a single element., RouteDecision, FitzPageRenderer, Production page renderer backed by PyMuPDF (fitz). (+10 more)

### Community 93 - "get"
Cohesion: 0.22
Nodes (10): get, _cors_origins(), _document_exists(), _env_rerank_blend(), livez(), Ownership pre-check before signing a GCS URL (prevents arbitrary signing)., Comma-separated browser origins from CORS_ALLOWED_ORIGINS (trimmed)., Return a short-lived signed GCS URL for PDF rendering (15-min TTL). (+2 more)

### Community 94 - "ModelProvider"
Cohesion: 0.12
Nodes (14): ModelProvider, ModelProvider Abstract Base Class for IRIS. All model inference calls…, Abstract Model Provider Interface., Vision-Language Model (VLM) call on a cropped table/figure image region.…, Vision-Language Model (VLM) full-page call for scanned or low-text pages (<150…, Generates a grounded natural language answer with structured citations.…, SLM-tier query rewriter. Uses sliding window history (last N messages) to…, HyDE (Hypothetical Document Embeddings) generator for Deep Search mode. (+6 more)

### Community 97 - "SearchOrchestrator"
Cohesion: 0.05
Nodes (30): ChunkStore, diversity_penalty(), ScoredChunk, Diversity / dedup pass — prevents single-page flooding. Applies a configurable…, Apply penalty to duplicate (doc, page) sources in the top-K window. For each…, fuse_rerank_scores(), Reciprocal Rank Fusion — merges two score-incompatible ranked lists. RRF is…, Merge dense and sparse ranked lists via RRF. Args: dense_results: [(chunk_id,… (+22 more)

### Community 98 - "IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2)"
Cohesion: 0.17
Nodes (11): Deferred (post-MVP, unchanged), IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2), Key risks, Stage 0 — Land the in-flight Phase 6/9 work + one bbox fix, Stage 1 — Free retrieval wins (fully local, no re-ingest), Stage 2 — Real reranker, wired into `/query`, Stage 3 — Re-ingest batch: small-to-big chunking + page-level citations, Stage 4 — Frontend highlight degradation ladder (`D:\iris-frontend`) (+3 more)

### Community 101 - "build_qa_response"
Cohesion: 0.18
Nodes (7): build_qa_response(), Render page -> PIL, draw bboxes, return base64 PNG. None if unavailable., Return chunk overlay data for one page of a document. Phase 4.0: requires a…, _render_overlay(), Security hardening tests — Findings 1-10 risk verification., JWT tenant is authoritative — caller-supplied tenant is ignored., TestQAViewAuthGate

### Community 102 - "IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2)"
Cohesion: 0.17
Nodes (11): Deferred (post-MVP, unchanged), IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2), Key risks, Stage 0 — Land the in-flight Phase 6/9 work + one bbox fix, Stage 1 — Free retrieval wins (fully local, no re-ingest), Stage 2 — Real reranker, wired into `/query`, Stage 3 — Re-ingest batch: small-to-big chunking + page-level citations, Stage 4 — Frontend highlight degradation ladder (`D:\iris-frontend`) (+3 more)

### Community 103 - "jwt.py"
Cohesion: 0.16
Nodes (20): AuthContext, AuthError, _get_app(), InvalidTokenError, MissingTenantClaimError, MissingTokenError, Exception, Firebase JWT verification + FastAPI auth dependency (Phase 4.0). The verified… (+12 more)

### Community 106 - "chunk_routed"
Cohesion: 0.12
Nodes (19): ElementType, RouteDecision, _chunk_metadata(), chunk_routed(), _chunk_text(), _env_target_tokens(), _page_level_metadata(), RoutingResult (+11 more)

### Community 109 - "IRIS Retrieval Quality + Citation Correctness — Implementation Plan"
Cohesion: 0.33
Nodes (5): IRIS Retrieval Quality + Citation Correctness — Implementation Plan, Stage 0 — Land the in-flight Phase 6/9 work (housekeeping, unblocks everything), Stage 1 — Free retrieval wins (no re-ingest), Stage 2 — Real reranker, wired into `/query`, Stage 3 — One deliberate re-ingest: small-to-big (the structural page-recall fix)

### Community 115 - "test_cors.py"
Cohesion: 0.18
Nodes (9): FastAPI, add_cors_middleware(), Register CORSMiddleware for the configured browser origins. No-op when…, _cors_app(), FastAPI, Phase 5.0a tests — CORS middleware on retrieval_api/app. Tests build a…, CORS header on a real authenticated request through the shared app., TestCorsMiddleware (+1 more)

### Community 118 - "RecordingProvider"
Cohesion: 0.25
Nodes (3): _chunk(), MockModelProvider that records every embed/rewrite/HyDE call., RecordingProvider

### Community 119 - "PageRenderer"
Cohesion: 0.29
Nodes (4): Image, PageRenderer, Renders PDF pages to images so the router can crop bbox regions., Return a PIL.Image of the given 1-based page at `scale`.

### Community 120 - "auth_testing.py"
Cohesion: 0.33
Nodes (3): Shared test helper for Phase 4.0 auth (local component tests). Patches…, Phase 2.0 unit tests — Retrieval API endpoints (FastAPI TestClient). Phase 4.0:…, Task 5.0b unit tests — POST /documents/upload (retrieval-api). Covers the full…

### Community 121 - "_build_synthesis_context"
Cohesion: 0.40
Nodes (5): ScoredChunk, _build_synthesis_context(), _expand_to_parent_pages(), Small-to-big (Stage 3c): append same-page siblings of the top chunks. Retrieval…, Build the source-chunk context and the source_chunks list for grounding.…

## Knowledge Gaps
- **305 isolated node(s):** `Stage 0 — Land the in-flight Phase 6/9 work + one bbox fix`, `Stage 1 — Free retrieval wins (fully local, no re-ingest)`, `Stage 2 — Real reranker, wired into `/query``, `Stage 3 — Re-ingest batch: small-to-big chunking + page-level citations`, `Stage 4 — Frontend highlight degradation ladder (`D:\iris-frontend`)` (+300 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MemoryChunkStore` connect `MemoryChunkStore` to `test_docling_pipeline.py`, `QdrantChunkStore`, `ingestion/main.py`, `text_to_sparse`, `TestIngestionPipelineWiring`, `check_pdf`, `test_docling_large.py`, `ParsedElement`, `ChunkStore`, `TestMemoryChunkStoreSearch`, `TestPubSubEnvelopeDecode`, `test_delete_cascade.py`, `ingestion/models.py`, `SearchOrchestrator`, `build_qa_response`, `TestMemoryChunkStoreThreadSafety`, `TestDownloadLocalDevGate`, `TestDeepSearch`, `RecordingProvider`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `ModelProvider` connect `ModelProvider` to `SearchOrchestrator`, `MockModelProvider`, `parser.py`, `ParsedElement`, `ingestion/main.py`, `MockVlmRouter`, `SelfHostedGPUProvider`, `VertexAIProvider`, `PageRenderer`, `vlm_router.py`, `.embed`, `IngestionPipeline`, `ingestion/models.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `MockModelProvider` connect `MockModelProvider` to `Citation`, `TestIngestionPipelineWiring`, `SearchOrchestrator`, `ParsedElement`, `TestPubSubEnvelopeDecode`, `ingestion/main.py`, `TestDownloadLocalDevGate`, `TestRouterSignals`, `TestGroundTruthRouting`, `TestDeepSearch`, `RecordingProvider`, `ingestion/models.py`, `ModelProvider`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `MemoryChunkStore` (e.g. with `RecordingProvider` and `TestDeepSearch`) actually correct?**
  _`MemoryChunkStore` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `MockModelProvider` (e.g. with `Citation` and `ModelProvider`) actually correct?**
  _`MockModelProvider` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ModelProvider` (e.g. with `IngestionPipeline` and `IngestResult`) actually correct?**
  _`ModelProvider` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Stage 0 — Land the in-flight Phase 6/9 work + one bbox fix`, `Stage 1 — Free retrieval wins (fully local, no re-ingest)`, `Stage 2 — Real reranker, wired into `/query`` to the rest of the system?**
  _305 weakly-connected nodes found - possible documentation gaps or missing edges._