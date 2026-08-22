# Graph Report - iris  (2026-08-22)

## Corpus Check
- 132 files · ~143,232 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1599 nodes · 2753 edges · 135 communities (99 shown, 36 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 152 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `faadb009`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_rate_limit.py
- Citation
- retrieval_api/app.py
- package.json
- What You Must Do When Invoked
- DoclingParser
- validate_tenant_id
- get_model_provider
- kill_switch
- QdrantChunkStore
- create_iam_alert.sh
- deploy.sh
- setup_firebase.sh
- TestSignal5
- Phase 4.0 — Authentication & Multi-Tenant Security ✅ COMPLETE
- Phase 7.0 — Trial / Freemium & Rate Limiting
- SearchOrchestrator
- Phase 12.0 — Neural Reranking Upgrade & Precision Engineering
- MemoryChunkStore
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
- auth_headers
- IRIS
- upload_document
- eval_phase2.py
- IRIS — Phased Action Plan
- mock_auth
- Phase 0.0 — Foundations & Safety Nets
- Phase 1.0 — Core Ingestion Pipeline ✅ (complete)
- Phase 2.0 — Vector Store & Retrieval
- Phase 3.0 — LLM Synthesis Layer ✅ (complete)
- Phase 3.5 — Retrieval Precision & Citation Quality Hardening (Lite) ✅ (complete)
- Phase 5.0 — Frontend Integration (Vercel)
- Phase 0.1 — Model Provider Abstraction Scaffold
- ParsedElement
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
- ModelProvider
- rules.test.js
- TestDownloadLocalDevGate
- Chunk
- check_pdf
- run_pipeline
- Golden-set label audit — human adjudication sheet
- Phase 16.0 — Enterprise Hardening & Zero-Trust Infrastructure
- Chunk
- TestMemoryChunkStoreSearch
- validate_table_markdown
- provision_eval_user.py
- ChunkStore
- Phase 2.5 — Empirical Validation & Pipeline Hardening
- test_delete_cascade.py
- TestRouterSignals
- TestGroundTruthRouting
- ABC
- Path
- claims.py
- IRIS Roadmap: Phase 6+ Execution Plan with Citation/Bbox/Rerank Fixes
- diversity_penalty
- run_pipeline
- TestAuthDependency
- MockModelProvider
- get
- preprocess
- ABC
- ABC
- reciprocal_rank_fusion
- IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2)
- get
- post
- test_qdrant_live.py
- IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2)
- jwt.py
- FastAPI
- ScoredChunk
- chunk_routed
- BaseModel
- StructuredAnswer
- IRIS Retrieval Quality + Citation Correctness — Implementation Plan
- TestPubSubEnvelopeDecode
- Exception
- ingestion/models.py
- Chunk
- ingestion/main.py
- test_cors.py
- base.py
- RoutingResult
- TestHindiSparseWiring
- _needs_rewrite
- fix_golden_pages.py
- query
- create_session
- TestMemoryChunkStoreThreadSafety
- TestVertexAIIntegration
- TestDeepSearch
- RecordingProvider
- canary/main.py
- SelfHostedGPUProvider
- auth_testing.py
- TestVertexRerank
- Golden-Set Adjudication Guide
- .rerank
- TestBakedCacheLayout
- _synthetic_element

## God Nodes (most connected - your core abstractions)
1. `MemoryChunkStore` - 61 edges
2. `MockModelProvider` - 41 edges
3. `auth_headers()` - 40 edges
4. `mock_auth()` - 39 edges
5. `ModelProvider` - 35 edges
6. `ElementType` - 33 edges
7. `RouteDecision` - 32 edges
8. `ParsedElement` - 32 edges
9. `MockVlmRouter` - 32 edges
10. `VertexAIProvider` - 31 edges

## Surprising Connections (you probably didn't know these)
- `TestModelProviderScaffold` --uses--> `VertexAIProvider`  [INFERRED]
  tests/test_model_provider.py → services/common/models/vertex.py
- `TestVertexRerank` --uses--> `VertexAIProvider`  [INFERRED]
  tests/test_model_provider.py → services/common/models/vertex.py
- `TestVertexAIIntegration` --uses--> `VertexAIProvider`  [INFERRED]
  tests/test_vertex_live.py → services/common/models/vertex.py
- `RecordingProvider` --uses--> `MemoryChunkStore`  [INFERRED]
  tests/test_deep_search.py → services/common/ingestion/store.py
- `TestDeepSearch` --uses--> `MemoryChunkStore`  [INFERRED]
  tests/test_deep_search.py → services/common/ingestion/store.py

## Import Cycles
- None detected.

## Communities (135 total, 36 thin omitted)

### Community 0 - "test_rate_limit.py"
Cohesion: 0.11
Nodes (8): FixedWindowRateLimiter, Per-tenant in-memory rate limiting (Phase 4.0 interim). Fixed-window limiter…, Thread-safe fixed-window limiter keyed by tenant_id., Raise 429 if `key` has exceeded the window budget., _chunk(), Phase 4.0 tests — per-tenant rate limiting., TestFixedWindowRateLimiter, TestRateLimitEndpoint

### Community 1 - "Citation"
Cohesion: 0.10
Nodes (33): BaseModel, Citation, Generates a grounded natural language answer with structured citations.…, StructuredAnswer, DeleteResponse, DocStatusResponse, BaseModel, QueryRequest (+25 more)

### Community 2 - "retrieval_api/app.py"
Cohesion: 0.23
Nodes (15): delete, delete_document(), _delete_firestore_doc(), _delete_firestore_session(), _delete_gcs_blob(), delete_session(), _get_gcs_client(), IRIS — Retrieval API (Cloud Run). Phase 2.0: FastAPI service with /search… (+7 more)

### Community 3 - "package.json"
Cohesion: 0.12
Nodes (15): firebase, @firebase/rules-unit-testing, firebase-tools, description, devDependencies, firebase, @firebase/rules-unit-testing, firebase-tools (+7 more)

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 5 - "DoclingParser"
Cohesion: 0.10
Nodes (21): ParsedElement, Path, _bbox_of(), _bbox_of_items(), DoclingParser, _page_of(), _page_size(), Extract 1-based page number from element provenance. (+13 more)

### Community 6 - "validate_tenant_id"
Cohesion: 0.23
Nodes (13): SearchRequest, ID validation + request-size guards (Phase 4.0). Prevents path traversal, NoSQL…, Truncate history to the sliding window instead of rejecting it., _reject(), validate_doc_id(), validate_history(), validate_query(), validate_session_id() (+5 more)

### Community 7 - "get_model_provider"
Cohesion: 0.25
Nodes (3): get_model_provider(), Factory function returning the active ModelProvider instance. MODEL_BACKEND…, TestModelProviderScaffold

### Community 8 - "kill_switch"
Cohesion: 0.47
Nodes (5): cloud_event, _kill_ingestion(), kill_switch(), Set pushConfig to empty on the subscription (pull-only)., _should_kill()

### Community 13 - "TestSignal5"
Cohesion: 0.12
Nodes (9): Verify FIX-008 Signal 5 non-Latin detection fires on Hindi, not English., Hindi page (valid_word_ratio ~0.82–0.87) must trigger Signal 5., Clean English text must never trigger Signal 5., English text with numerals/punctuation stays Latin-dominant., A short Hindi clause still exceeds the 30% letter threshold., Empty and ASCII-only inputs never trigger Signal 5., A page that is exactly 30% non-Latin does NOT trigger (strict >)., Punctuation-only (no letters) never triggers Signal 5. (+1 more)

### Community 14 - "Phase 4.0 — Authentication & Multi-Tenant Security ✅ COMPLETE"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 4.0 — Authentication & Multi-Tenant Security ✅ COMPLETE, Scope, Services Touched, Tasks

### Community 15 - "Phase 7.0 — Trial / Freemium & Rate Limiting"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 7.0 — Trial / Freemium & Rate Limiting, Scope, Services Touched, Tasks

### Community 16 - "SearchOrchestrator"
Cohesion: 0.27
Nodes (4): Orchestrates Standard + Deep search over the chunk store., SearchOrchestrator, _chunk(), TestSearchOrchestrator

### Community 17 - "Phase 12.0 — Neural Reranking Upgrade & Precision Engineering"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 12.0 — Neural Reranking Upgrade & Precision Engineering, Scope, Services Touched, Tasks

### Community 18 - "MemoryChunkStore"
Cohesion: 0.14
Nodes (7): ChunkStore, build_qa_response(), Return chunk overlay data for one page of a document. Phase 4.0: requires a…, MemoryChunkStore, In-memory store for dev/tests. Thread-safe., JWT tenant is authoritative — caller-supplied tenant is ignored., TestQAViewAuthGate

### Community 19 - "bm25_cache"
Cohesion: 0.40
Nodes (4): fixture, bm25_cache(), Shared pytest fixtures. Bakes the FastEmbed Qdrant/bm25 model into a temp cache…, Download Qdrant/bm25 into a session-scoped temp HF cache and wire it up.…

### Community 21 - "VertexAIProvider"
Cohesion: 0.18
Nodes (6): ModelProvider, Cached TextEmbeddingModel — from_pretrained per call re-resolves the endpoint…, Production Vertex AI implementation for GCP Cloud Run. Embeddings run in-region…, _sanitize_context(), VertexAIProvider, StructuredAnswer

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

### Community 37 - "auth_headers"
Cohesion: 0.13
Nodes (7): auth_headers(), Headers for a request whose token maps to the given claims (mock-active)., _fake_firestore(), Phase 4.0 tests — session CRUD endpoints + signed view URL., Firestore mock: document().get/set/update/delete tracked, collection stream…, TestSessionsApi, TestViewUrl

### Community 38 - "IRIS"
Cohesion: 0.15
Nodes (12): 1. What This System Does, 2. Core Design Principles, 3. Technology Stack, 4. High-Level Architecture, 5. Getting Started (Once Implementation Begins), 6. Repository Structure (Target), 7. Key Documents, 8. Guiding Constraints (Do Not Violate) (+4 more)

### Community 39 - "upload_document"
Cohesion: 0.22
Nodes (8): post, Call ingestion-worker /ingest to preflight + split + fan out to Pub/Sub.…, Upload a PDF and trigger ingestion (Task 5.0b). Flow: validate doc_id + file ->…, _trigger_ingestion(), upload_document(), Task 5.0b unit tests — POST /documents/upload (retrieval-api). Covers the full…, The trigger must mint an ID token via IAM generateIdToken, not use…, UploadFile

### Community 40 - "eval_phase2.py"
Cohesion: 0.06
Nodes (63): check_tenant_isolation(), compute_mrr(), compute_page_recall_at_k(), compute_recall_at_k(), compute_source_duplication(), _firebase_id_token(), _get_firebase_api_key(), _id_token() (+55 more)

### Community 41 - "IRIS — Phased Action Plan"
Cohesion: 0.15
Nodes (12): Benchmarks & Testing, Deployment & Containerization Strategy, Exit Criteria, How per-phase checkpointing still works without per-phase containers, IRIS — Phased Action Plan, 🏁 MVP LAUNCH BOUNDARY, Phase 13.0 — Context Compression, Scope (+4 more)

### Community 42 - "mock_auth"
Cohesion: 0.22
Nodes (3): mock_auth(), Patch the JWT verifier to return a fixed AuthContext. The token string itself…, TestUploadApi

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

### Community 50 - "ParsedElement"
Cohesion: 0.12
Nodes (16): ParsedElement, One element extracted by Docling, normalized for the router., MockVlmRouter, Apply the routing table to a parsed document., Deterministic router for tests: routes but never calls a real VLM., A routed element: either Docling text or a VLM call output., RoutingResult, FIX-005 wiring: page_number_override reaches every stored chunk. (+8 more)

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
Cohesion: 0.11
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
Cohesion: 0.14
Nodes (13): _get_model(), BM25 sparse vector tokenizer backed by FastEmbed's Qdrant/bm25 model. Replaces…, Convert to Qdrant SparseVector-compatible (indices, values) pair., Return the term indices encoded for `text` (for tests/debugging). FastEmbed's…, Return the model cache dir, preferring the explicitly-set path. Resolution…, Lazily initialize the singleton FastEmbed Bm25 model (thread-safe). Loads…, Encode text into {term_index: raw_term_count} via Qdrant/bm25. When…, _resolve_cache_dir() (+5 more)

### Community 66 - "ModelProvider"
Cohesion: 0.09
Nodes (15): Image, FitzPageRenderer, PageRenderer, Renders PDF pages to images so the router can crop bbox regions., Return a PIL.Image of the given 1-based page at `scale`., Production page renderer backed by PyMuPDF (fitz)., ModelProvider, Abstract Model Provider Interface. (+7 more)

### Community 67 - "rules.test.js"
Cohesion: 0.25
Nodes (4): fs, { initializeTestEnvironment, assertFails, assertSucceeds }, path, RULES_PATH

### Community 69 - "Chunk"
Cohesion: 0.11
Nodes (4): Chunk, BaseModel, A content unit ready to embed + store., TestRetrievalApi

### Community 70 - "check_pdf"
Cohesion: 0.08
Nodes (26): check_pdf(), PreflightError, Exception, Path, Pre-ingestion payload scanner (ACTIONPLAN Task 1.2). Rejects payloads BEFORE…, Raised when a payload is rejected before processing., Validate a PDF file before it enters the pipeline. Returns metadata dict:…, _load_labels() (+18 more)

### Community 71 - "run_pipeline"
Cohesion: 0.29
Nodes (6): DoclingParser, integration, Path, Parse the full 8-doc corpus on CPU and verify no doc is empty., run_pipeline(), TestDoclingLargeCPU

### Community 72 - "Golden-set label audit — human adjudication sheet"
Cohesion: 0.07
Nodes (26): Golden-set label audit — human adjudication sheet, q_001 [OFF_BY_ONE] (direct_factual), q_002 [OFF_BY_ONE] (direct_factual), q_003 [PAGE_MISS] (direct_factual), q_005 [OFF_BY_ONE] (direct_factual), q_006 [PAGE_MISS] (direct_factual), q_009 [DOC_MISS] (direct_factual), q_010 [PAGE_MISS] (direct_factual) (+18 more)

### Community 73 - "Phase 16.0 — Enterprise Hardening & Zero-Trust Infrastructure"
Cohesion: 0.33
Nodes (6): Deliverables, Exit Criteria, Phase 16.0 — Enterprise Hardening & Zero-Trust Infrastructure, Scope, Services Touched, Tasks

### Community 74 - "Chunk"
Cohesion: 0.15
Nodes (5): Chunk, Persist chunks; returns the number written., Return all chunks for a document, enforcing tenant isolation., Return chunks by their IDs, scoped to the given tenant. Missing IDs and cross-…, Return all chunks of a document on the given pages, tenant-scoped. Stage 3c…

### Community 76 - "validate_table_markdown"
Cohesion: 0.26
Nodes (5): Phase 2.5 — VLM table markdown validation. Validates that VLM-extracted…, Validate VLM-extracted Markdown table structure. Returns True if row/column…, validate_table_markdown(), Phase 2.5 unit tests — table markdown validator., TestTableValidator

### Community 77 - "provision_eval_user.py"
Cohesion: 0.47
Nodes (5): _create_user_if_missing(), _credentials(), main(), Build Firebase Admin credentials from a token, or fall back to ADC., Return the user UID, creating the account first if needed.

### Community 78 - "ChunkStore"
Cohesion: 0.08
Nodes (15): get_cached_chunks(), Document hash cache for ingestion deduplication. If a PDF has been previously…, Check if doc SHA256 has been previously stored. Returns list of Chunks if…, IngestionPipeline, Chunk, ChunkStore, get_chunk_store(), Dense cosine vector search with tenant + optional doc filters. Returns… (+7 more)

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
Cohesion: 0.20
Nodes (7): 127 pages: high ratio + high coverage -> zero VLM cost., 58 pages: tables (Signal 1) or low-coverage sparse -> VLM., 5 pages (Hindi/Devanagari): Signal 5 must fire despite high ratio., 11 pages: 0.75-0.88 ratio -> DOCLING_TEXT (or VLM_TABLE if has_table)., Aggregate: every labeled page matches ground truth (no regressions)., Every labeled page in the CSV must route as the ground truth says., TestGroundTruthRouting

### Community 87 - "IRIS Roadmap: Phase 6+ Execution Plan with Citation/Bbox/Rerank Fixes"
Cohesion: 0.13
Nodes (14): Background (verified facts), Current ACTIONPLAN phase map (post-Phase 5), Execution plan (phase by phase), Files to touch, Goal, IRIS Roadmap: Phase 6+ Execution Plan with Citation/Bbox/Rerank Fixes, Open decision, Phase 10.0 → 11.0 — Graph layers (stay in place, after 9.0) (+6 more)

### Community 88 - "diversity_penalty"
Cohesion: 0.22
Nodes (8): diversity_penalty(), ScoredChunk, Diversity / dedup pass — prevents single-page flooding. Applies a configurable…, Apply penalty to duplicate (doc, page) sources in the top-K window. For each…, ScoredChunk, Phase 2.0 unit tests — diversity / dedup pass., _scored(), TestDiversity

### Community 90 - "run_pipeline"
Cohesion: 0.29
Nodes (6): DoclingParser, integration, Path, Parse -> route -> chunk -> store roundtrip on the golden corpus., run_pipeline(), TestDoclingPipelineTrueassort

### Community 92 - "MockModelProvider"
Cohesion: 0.09
Nodes (14): MockDocParser, Deterministic parser for local tests (MODEL_BACKEND=mock)., MockModelProvider, Mock implementation returning deterministic outputs for local testing., _load_pages(), Path, Parse -> route -> chunk -> store, driven through the production objects., MockDocParser's 4 elements flow through router -> chunker -> store. (+6 more)

### Community 93 - "get"
Cohesion: 0.18
Nodes (12): get, _cors_origins(), _document_exists(), _env_rerank_blend(), livez(), FR-5.4: purge doc_id from every session's document_ids array., Ownership pre-check before signing a GCS URL (prevents arbitrary signing)., Comma-separated browser origins from CORS_ALLOWED_ORIGINS (trimmed). (+4 more)

### Community 94 - "preprocess"
Cohesion: 0.22
Nodes (7): contains_devanagari(), preprocess(), Hindi-aware preprocessing for the BM25 sparse encoder (Stage 5). FastEmbed's…, Drop Hindi stopwords and lightly stem Devanagari tokens. Non-Devanagari tokens…, _stem(), Stage 5 — Devanagari stopword/stemming preprocessing (pure logic)., TestHindiPreprocess

### Community 97 - "reciprocal_rank_fusion"
Cohesion: 0.15
Nodes (9): fuse_rerank_scores(), Reciprocal Rank Fusion — merges two score-incompatible ranked lists. RRF is…, Merge dense and sparse ranked lists via RRF. Args: dense_results: [(chunk_id,…, Fuse hybrid RRF scores with cross-encoder reranker scores, rank-based. The…, reciprocal_rank_fusion(), Phase 2.0 unit tests — RRF fusion., Phase 12.1 weighted rank fusion — scale-free reranker blending., TestFuseRerankScores (+1 more)

### Community 98 - "IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2)"
Cohesion: 0.17
Nodes (11): Deferred (post-MVP, unchanged), IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2), Key risks, Stage 0 — Land the in-flight Phase 6/9 work + one bbox fix, Stage 1 — Free retrieval wins (fully local, no re-ingest), Stage 2 — Real reranker, wired into `/query`, Stage 3 — Re-ingest batch: small-to-big chunking + page-level citations, Stage 4 — Frontend highlight degradation ladder (`D:\iris-frontend`) (+3 more)

### Community 101 - "test_qdrant_live.py"
Cohesion: 0.53
Nodes (5): _chunk(), Tier 2 live smoke tests — Qdrant connectivity and read/write path. Run only…, _store(), test_collection_health(), test_roundtrip_upsert_search_delete()

### Community 102 - "IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2)"
Cohesion: 0.17
Nodes (11): Deferred (post-MVP, unchanged), IRIS Retrieval Quality + Citation Correctness — Implementation Plan (v2), Key risks, Stage 0 — Land the in-flight Phase 6/9 work + one bbox fix, Stage 1 — Free retrieval wins (fully local, no re-ingest), Stage 2 — Real reranker, wired into `/query`, Stage 3 — Re-ingest batch: small-to-big chunking + page-level citations, Stage 4 — Frontend highlight degradation ladder (`D:\iris-frontend`) (+3 more)

### Community 103 - "jwt.py"
Cohesion: 0.14
Nodes (22): AuthContext, AuthError, _get_app(), InvalidTokenError, MissingTenantClaimError, MissingTokenError, Exception, Firebase JWT verification + FastAPI auth dependency (Phase 4.0). The verified… (+14 more)

### Community 106 - "chunk_routed"
Cohesion: 0.12
Nodes (19): ElementType, RouteDecision, _chunk_metadata(), chunk_routed(), _chunk_text(), _env_target_tokens(), _page_level_metadata(), RoutingResult (+11 more)

### Community 109 - "IRIS Retrieval Quality + Citation Correctness — Implementation Plan"
Cohesion: 0.33
Nodes (5): IRIS Retrieval Quality + Citation Correctness — Implementation Plan, Stage 0 — Land the in-flight Phase 6/9 work (housekeeping, unblocks everything), Stage 1 — Free retrieval wins (no re-ingest), Stage 2 — Real reranker, wired into `/query`, Stage 3 — One deliberate re-ingest: small-to-big (the structural page-recall fix)

### Community 110 - "TestPubSubEnvelopeDecode"
Cohesion: 0.36
Nodes (3): _load_worker_module(), FIX-005 — page_number must survive the Pub/Sub push envelope., TestPubSubEnvelopeDecode

### Community 112 - "ingestion/models.py"
Cohesion: 0.10
Nodes (23): Enum, ElementType, Shared data model for the IRIS ingestion pipeline. A `Chunk` is the unit…, Docling element labels, normalized for the pipeline., Page-Wise VLM Router outcome for a single element., RouteDecision, Chunk store (ACTIONPLAN Task 1.9 + Phase 2.0 retrieval). `ChunkStore` ABC with…, Mock ModelProvider implementation for zero-cost local testing and unit tests. (+15 more)

### Community 114 - "ingestion/main.py"
Cohesion: 0.15
Nodes (15): ABC, IngestResult, Exception, Path, Ingestion orchestrator (ACTIONPLAN Tasks 1.2-1.9). Order: preflight -> download…, Payload must be rejected forever (never queued / straight to DLQ)., Transient failure; Pub/Sub should redeliver (up to 3 attempts)., Full pipeline for one uploaded document or single-page blob. (+7 more)

### Community 115 - "test_cors.py"
Cohesion: 0.18
Nodes (9): FastAPI, add_cors_middleware(), Register CORSMiddleware for the configured browser origins. No-op when…, _cors_app(), FastAPI, Phase 5.0a tests — CORS middleware on retrieval_api/app. Tests build a…, CORS header on a real authenticated request through the shared app., TestCorsMiddleware (+1 more)

### Community 116 - "base.py"
Cohesion: 0.19
Nodes (8): Exception, ModelProvider Abstract Base Class for IRIS. All model inference calls…, ModelProvider Factory for IRIS. Reads MODEL_BACKEND env var from Secret Manager…, Self-hosted GPU model provider (Phase 10.0). Provides local GPU inference for…, Package initialization for services.common.models., _is_resource_exhausted(), VertexAIProvider wrapping Google Cloud Vertex AI SDK. Uses text-embedding-004…, Return True if the exception is a Vertex/API rate-limit condition.

### Community 119 - "_needs_rewrite"
Cohesion: 0.18
Nodes (6): _needs_rewrite(), ScoredChunk, Deep Search with async SLM rewrite, HyDE generation, and fusion., Resolve RRF-fused (chunk_id, score) into full ScoredChunk objects., Phase 6.5 gate: true only when there is history AND an ambiguous reference.…, Task 2.4a: Standard non-blocking async search path. `rerank_blend` (Phase…

### Community 121 - "query"
Cohesion: 0.29
Nodes (8): QueryRequest, ScoredChunk, _build_synthesis_context(), _expand_to_parent_pages(), query(), Retrieve -> synthesize -> grounded structured answer., Small-to-big (Stage 3c): append same-page siblings of the top chunks. Retrieval…, Build the source-chunk context and the source_chunks list for grounding.…

### Community 122 - "create_session"
Cohesion: 0.22
Nodes (11): AuthContext, _create_document_record(), create_session(), _get_firestore_client(), list_sessions(), Lazy-initialize Firestore client., Create the Firestore ownership record so view-url/delete work. The record also…, Create a named workspace session scoped to the verified tenant. (+3 more)

### Community 124 - "TestVertexAIIntegration"
Cohesion: 0.20
Nodes (5): Test live Vertex AI text-embedding-004 call using gcloud credentials., Test live Gemini 2.5 Flash synthesis call., Test live Gemini 2.5 Flash Lite query rewrite call., Test live Gemini 2.5 Flash vision OCR call on sample image bytes., TestVertexAIIntegration

### Community 126 - "RecordingProvider"
Cohesion: 0.25
Nodes (3): _chunk(), MockModelProvider that records every embed/rewrite/HyDE call., RecordingProvider

### Community 127 - "canary/main.py"
Cohesion: 0.39
Nodes (7): _firebase_token(), _post(), _probe_ranking_api(), IRIS retrieval canary (measurement work, stage 2). Cloud Scheduler hits this…, Call the Ranking API directly (function's own ADC): rank one relevant and one…, run_canary(), _valid_bbox()

### Community 131 - "Golden-Set Adjudication Guide"
Cohesion: 0.29
Nodes (6): A. How to verify a label (method + worked example), B. Items needing your eyes (5 items, ~10 minutes), C. NOT label questions — explained by the un-indexed-pages bug (no action for you), D. Confirmed genuine retrieval failures (no action), E. Already fixed this round, Golden-Set Adjudication Guide

### Community 133 - "TestBakedCacheLayout"
Cohesion: 0.50
Nodes (3): skipUnless, Verify the Docker-baked cache is in the HF layout fastembed expects. This is…, TestBakedCacheLayout

### Community 134 - "_synthetic_element"
Cohesion: 0.50
Nodes (4): _char_count_for_coverage(), Derive a plausible element char_count from page coverage + route. The CSV's…, Build a synthetic element carrying only the CSV-labeled features., _synthetic_element()

## Knowledge Gaps
- **335 isolated node(s):** `A. How to verify a label (method + worked example)`, `B. Items needing your eyes (5 items, ~10 minutes)`, `C. NOT label questions — explained by the un-indexed-pages bug (no action for you)`, `D. Confirmed genuine retrieval failures (no action)`, `E. Already fixed this round` (+330 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MemoryChunkStore` connect `MemoryChunkStore` to `text_to_sparse`, `TestDownloadLocalDevGate`, `check_pdf`, `run_pipeline`, `Chunk`, `TestMemoryChunkStoreSearch`, `ChunkStore`, `TestPubSubEnvelopeDecode`, `ingestion/models.py`, `test_delete_cascade.py`, `ingestion/main.py`, `ParsedElement`, `SearchOrchestrator`, `run_pipeline`, `TestMemoryChunkStoreThreadSafety`, `MockModelProvider`, `TestDeepSearch`, `RecordingProvider`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `MockModelProvider` connect `MockModelProvider` to `Citation`, `ModelProvider`, `TestDownloadLocalDevGate`, `get_model_provider`, `TestPubSubEnvelopeDecode`, `ingestion/models.py`, `TestRouterSignals`, `ingestion/main.py`, `TestGroundTruthRouting`, `base.py`, `ParsedElement`, `SearchOrchestrator`, `vlm_router.py`, `TestDeepSearch`, `RecordingProvider`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `ModelProvider` connect `ModelProvider` to `SelfHostedGPUProvider`, `Citation`, `get_model_provider`, `ChunkStore`, `ingestion/models.py`, `SearchOrchestrator`, `ingestion/main.py`, `ParsedElement`, `base.py`, `MemoryChunkStore`, `vlm_router.py`, `MockModelProvider`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `MemoryChunkStore` (e.g. with `RecordingProvider` and `TestDeepSearch`) actually correct?**
  _`MemoryChunkStore` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `MockModelProvider` (e.g. with `Citation` and `ModelProvider`) actually correct?**
  _`MockModelProvider` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `ModelProvider` (e.g. with `IngestionPipeline` and `IngestResult`) actually correct?**
  _`ModelProvider` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `A. How to verify a label (method + worked example)`, `B. Items needing your eyes (5 items, ~10 minutes)`, `C. NOT label questions — explained by the un-indexed-pages bug (no action for you)` to the rest of the system?**
  _335 weakly-connected nodes found - possible documentation gaps or missing edges._