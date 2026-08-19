# Graph Report - iris  (2026-08-19)

## Corpus Check
- 115 files · ~126,149 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1337 nodes · 2386 edges · 91 communities (73 shown, 18 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 159 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `96df8df1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_rate_limit.py
- build_qa_response
- StructuredAnswer
- package.json
- What You Must Do When Invoked
- DoclingParser
- retrieval_api/app.py
- TestDeepSearch
- kill_switch
- diversity_penalty
- create_iam_alert.sh
- deploy.sh
- setup_firebase.sh
- TestSignal5
- Phase 4.0 — Authentication & Multi-Tenant Security ✅ COMPLETE
- Phase 7.0 — Trial / Freemium & Rate Limiting
- ModelProvider
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
- 👁️ IRIS — Intelligent Retrieval & Ingestion System
- auth_headers
- IRIS
- MemoryChunkStore
- eval_phase2.py
- IRIS — Phased Action Plan
- Chunk
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
- auth_testing.py
- Phase 14.0 — Mixture of Agents (MoA) Synthesis
- Phase 15.0 — GPU Swap-In (When Quota Available)
- Shared Context & Working Agreement
- test_4b_live.js
- Phase 16.0 — Enterprise Scale Hardening
- .commandcode/taste/taste.md
- taste/taste/taste.md
- QdrantChunkStore
- ingestion/models.py
- ingestion/main.py
- rules.test.js
- chunk_routed
- mock_auth
- check_pdf
- SelfHostedGPUProvider
- IRIS — Critical Fixes Register
- Phase 16.0 — Enterprise Hardening & Zero-Trust Infrastructure
- ElementType
- TestMemoryChunkStoreSearch
- validate_table_markdown
- provision_eval_user.py
- TestPubSubEnvelopeDecode
- Phase 2.5 — Empirical Validation & Pipeline Hardening
- test_delete_cascade.py
- MockModelProvider
- vertex.py
- ABC
- Path
- claims.py
- .synthesize
- BaseModel

## God Nodes (most connected - your core abstractions)
1. `MemoryChunkStore` - 59 edges
2. `MockModelProvider` - 42 edges
3. `ElementType` - 42 edges
4. `RouteDecision` - 41 edges
5. `ModelProvider` - 35 edges
6. `ParsedElement` - 34 edges
7. `MockVlmRouter` - 32 edges
8. `auth_headers()` - 31 edges
9. `mock_auth()` - 30 edges
10. `Chunk` - 28 edges

## Surprising Connections (you probably didn't know these)
- `TestAuthDependency` --uses--> `SearchRequest`  [INFERRED]
  tests/test_auth.py → services/common/retrieval/models.py
- `TestAuthDependency` --uses--> `QueryRequest`  [INFERRED]
  tests/test_auth.py → services/common/retrieval/models.py
- `TestAuthDependency` --uses--> `SessionCreateRequest`  [INFERRED]
  tests/test_auth.py → services/common/retrieval/models.py
- `TestChunkerPageFirst` --uses--> `DoclingParser`  [INFERRED]
  tests/test_page_chunking.py → services/common/ingestion/parser.py
- `RecordingProvider` --uses--> `MemoryChunkStore`  [INFERRED]
  tests/test_deep_search.py → services/common/ingestion/store.py

## Import Cycles
- None detected.

## Communities (91 total, 18 thin omitted)

### Community 0 - "test_rate_limit.py"
Cohesion: 0.11
Nodes (8): FixedWindowRateLimiter, Per-tenant in-memory rate limiting (Phase 4.0 interim). Fixed-window limiter…, Thread-safe fixed-window limiter keyed by tenant_id., Raise 429 if `key` has exceeded the window budget., _chunk(), Phase 4.0 tests — per-tenant rate limiting., TestFixedWindowRateLimiter, TestRateLimitEndpoint

### Community 1 - "build_qa_response"
Cohesion: 0.06
Nodes (29): ChunkStore, Exception, AuthError, _get_app(), InvalidTokenError, MissingTenantClaimError, MissingTokenError, Firebase JWT verification + FastAPI auth dependency (Phase 4.0). The verified… (+21 more)

### Community 2 - "StructuredAnswer"
Cohesion: 0.24
Nodes (12): Citation, BaseModel, StructuredAnswer, A retrieved chunk with its fusion score., ScoredChunk, Resolve RRF-fused (chunk_id, score) into full ScoredChunk objects., Server-side citation validation (Phase 3.0 Task 3.4). The LLM's structured…, Drop hallucinated citations and overwrite valid ones with real metadata. A… (+4 more)

### Community 3 - "package.json"
Cohesion: 0.12
Nodes (15): firebase, @firebase/rules-unit-testing, firebase-tools, description, devDependencies, firebase, @firebase/rules-unit-testing, firebase-tools (+7 more)

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 5 - "DoclingParser"
Cohesion: 0.09
Nodes (24): ABC, ParsedElement, Path, _bbox_of(), _bbox_of_items(), DoclingParser, DocParser, _page_of() (+16 more)

### Community 6 - "retrieval_api/app.py"
Cohesion: 0.08
Nodes (59): BaseModel, delete, AuthContext, Verified caller identity, extracted from the Firebase JWT., ID validation + request-size guards (Phase 4.0). Prevents path traversal, NoSQL…, Truncate history to the sliding window instead of rejecting it., _reject(), validate_doc_id() (+51 more)

### Community 8 - "kill_switch"
Cohesion: 0.47
Nodes (5): cloud_event, _kill_ingestion(), kill_switch(), Set pushConfig to empty on the subscription (pull-only)., _should_kill()

### Community 9 - "diversity_penalty"
Cohesion: 0.11
Nodes (13): diversity_penalty(), Diversity / dedup pass — prevents source-document flooding. Applies a…, Apply penalty to duplicate source docs in the top-K window. For each chunk in…, Reciprocal Rank Fusion — merges two score-incompatible ranked lists. RRF is…, Merge dense and sparse ranked lists via RRF. Args: dense_results: [(chunk_id,…, reciprocal_rank_fusion(), Task 2.4a: Standard non-blocking async search path., Deep Search with async SLM rewrite, HyDE generation, and fusion. (+5 more)

### Community 13 - "TestSignal5"
Cohesion: 0.12
Nodes (9): Verify FIX-008 Signal 5 non-Latin detection fires on Hindi, not English., Hindi page (valid_word_ratio ~0.82–0.87) must trigger Signal 5., Clean English text must never trigger Signal 5., English text with numerals/punctuation stays Latin-dominant., A short Hindi clause still exceeds the 30% letter threshold., Empty and ASCII-only inputs never trigger Signal 5., A page that is exactly 30% non-Latin does NOT trigger (strict >)., Punctuation-only (no letters) never triggers Signal 5. (+1 more)

### Community 14 - "Phase 4.0 — Authentication & Multi-Tenant Security ✅ COMPLETE"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 4.0 — Authentication & Multi-Tenant Security ✅ COMPLETE, Scope, Services Touched, Tasks

### Community 15 - "Phase 7.0 — Trial / Freemium & Rate Limiting"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 7.0 — Trial / Freemium & Rate Limiting, Scope, Services Touched, Tasks

### Community 16 - "ModelProvider"
Cohesion: 0.11
Nodes (15): ModelProvider, ABC, ModelProvider Abstract Base Class for IRIS. All model inference calls…, Abstract Model Provider Interface., Generates a 768-dimensional vector embedding using the configured model…, Vision-Language Model (VLM) call on a cropped table/figure image region.…, Vision-Language Model (VLM) full-page call for scanned or low-text pages (<150…, SLM-tier query rewriter. Uses sliding window history (last N messages) to… (+7 more)

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
Cohesion: 0.15
Nodes (8): Production Vertex AI implementation for GCP Cloud Run. Embeddings run in-region…, _sanitize_context(), VertexAIProvider, Test live Vertex AI text-embedding-004 call using gcloud credentials., Test live Gemini 2.5 Flash synthesis call., Test live Gemini 2.5 Flash Lite query rewrite call., Test live Gemini 2.5 Flash vision OCR call on sample image bytes., TestVertexAIIntegration

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

### Community 36 - "👁️ IRIS — Intelligent Retrieval & Ingestion System"
Cohesion: 0.22
Nodes (8): 🔬 4-Signal Composite Decision Engine, 🥊 Competitive Advantage: Traditional Systems vs. IRIS, ⚡ End-to-End Pipeline Workflow, 📌 Executive Summary, 👁️ IRIS — Intelligent Retrieval & Ingestion System, 📊 Performance Benchmarks & Targets, 🎯 Production Engineering Challenges Solved, 🛠️ Technology Stack & Architectural Rationale

### Community 37 - "auth_headers"
Cohesion: 0.20
Nodes (5): auth_headers(), Headers for a request whose token maps to the given claims (mock-active)., _fake_firestore(), Firestore mock: document().get/set/update/delete tracked, collection stream…, TestSessionsApi

### Community 38 - "IRIS"
Cohesion: 0.15
Nodes (12): 1. What This System Does, 2. Core Design Principles, 3. Technology Stack, 4. High-Level Architecture, 5. Getting Started (Once Implementation Begins), 6. Repository Structure (Target), 7. Key Documents, 8. Guiding Constraints (Do Not Violate) (+4 more)

### Community 39 - "MemoryChunkStore"
Cohesion: 0.08
Nodes (19): Sentence-boundary chunking (ACTIONPLAN Task 1.6). Text elements -> chunks at…, Pre-ingestion payload scanner (ACTIONPLAN Task 1.2). Rejects payloads BEFORE…, MemoryChunkStore, In-memory store for dev/tests. Thread-safe., Docling pipeline integration tests — run against trueassort/ golden corpus.…, Docling CPU pipeline tests — run the full trueassort/ corpus on CPU. Run:…, Docling pipeline integration tests — parse/route/chunk/store against…, _load_labels() (+11 more)

### Community 40 - "eval_phase2.py"
Cohesion: 0.08
Nodes (48): check_tenant_isolation(), compute_mrr(), compute_page_recall_at_k(), compute_recall_at_k(), compute_source_duplication(), _firebase_id_token(), _get_firebase_api_key(), _id_token() (+40 more)

### Community 41 - "IRIS — Phased Action Plan"
Cohesion: 0.15
Nodes (12): Benchmarks & Testing, Deployment & Containerization Strategy, Exit Criteria, How per-phase checkpointing still works without per-phase containers, IRIS — Phased Action Plan, 🏁 MVP LAUNCH BOUNDARY, Phase 13.0 — Context Compression, Scope (+4 more)

### Community 42 - "Chunk"
Cohesion: 0.17
Nodes (4): Chunk, Persist chunks; returns the number written., Return all chunks for a document, enforcing tenant isolation., Return chunks by their IDs, scoped to the given tenant. Missing IDs and cross-…

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

### Community 56 - "auth_testing.py"
Cohesion: 0.20
Nodes (3): Shared test helper for Phase 4.0 auth (local component tests). Patches…, Phase 4.0 tests — session CRUD endpoints + signed view URL., TestViewUrl

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

### Community 64 - "QdrantChunkStore"
Cohesion: 0.08
Nodes (23): QdrantChunkStore, Phase 2.0 Qdrant store — v2 named-vector collection, hybrid search, cascading…, _get_model(), BM25 sparse vector tokenizer backed by FastEmbed's Qdrant/bm25 model. Replaces…, Return the term indices encoded for `text` (for tests/debugging). FastEmbed's…, Return the model cache dir, preferring the explicitly-set path. Resolution…, Lazily initialize the singleton FastEmbed Bm25 model (thread-safe). Loads…, Encode text into {term_index: raw_term_count} via Qdrant/bm25. Returns an empty… (+15 more)

### Community 65 - "ingestion/models.py"
Cohesion: 0.07
Nodes (31): get_cached_chunks(), Document hash cache for ingestion deduplication. If a PDF has been previously…, Check if doc SHA256 has been previously stored. Returns list of Chunks if…, Chunk, BaseModel, Shared data model for the IRIS ingestion pipeline. A `Chunk` is the unit…, A content unit ready to embed + store., ChunkStore (+23 more)

### Community 66 - "ingestion/main.py"
Cohesion: 0.09
Nodes (23): IngestionPipeline, IngestResult, Chunk, Exception, Path, Ingestion orchestrator (ACTIONPLAN Tasks 1.2-1.9). Order: preflight -> download…, Payload must be rejected forever (never queued / straight to DLQ)., Transient failure; Pub/Sub should redeliver (up to 3 attempts). (+15 more)

### Community 67 - "rules.test.js"
Cohesion: 0.25
Nodes (4): fs, { initializeTestEnvironment, assertFails, assertSucceeds }, path, RULES_PATH

### Community 68 - "chunk_routed"
Cohesion: 0.09
Nodes (20): Chunk, RoutingResult, chunk_routed(), _chunk_text(), FIX-011: tag chunks whose extraction quality is mid-tier (standard_ocr). Pages…, Convert routed elements into embeddable Chunks. Phase 3.5 page-boundary strict…, _standard_ocr_metadata(), _rr() (+12 more)

### Community 69 - "mock_auth"
Cohesion: 0.14
Nodes (4): mock_auth(), Patch the JWT verifier to return a fixed AuthContext. The token string itself…, Phase 2.0 unit tests — Retrieval API endpoints (FastAPI TestClient). Phase 4.0:…, TestRetrievalApi

### Community 70 - "check_pdf"
Cohesion: 0.07
Nodes (24): check_pdf(), PreflightError, Exception, Path, Raised when a payload is rejected before processing., Validate a PDF file before it enters the pipeline. Returns metadata dict:…, _load_labels(), integration (+16 more)

### Community 72 - "IRIS — Critical Fixes Register"
Cohesion: 0.07
Nodes (26): FIX-001 — `QDRANT_URL` Missing from `ingestion-worker` Cloud Run Service, FIX-002 — Pub/Sub Push Subscription Detached by Billing Kill-Switch, FIX-003 — Qdrant Client 1.19.0 vs Server 1.13.0 Version Mismatch, FIX-004 — No `.dockerignore` Causes 78 GB Artifact Registry Bloat, FIX-005 — Page Numbers Stored as `0/0` (Pub/Sub Envelope Parsing Mismatch), FIX-006 — VLM Rate Limiting: 140–197 Gemini Vision Calls Per Document, FIX-007 — `/status` Returns 429 During Processing (`concurrency=1` Conflict), FIX-008 — No `multilingual_ocr` Routing Tier (Hindi / Devanagari Pages Silently Garbled) (+18 more)

### Community 73 - "Phase 16.0 — Enterprise Hardening & Zero-Trust Infrastructure"
Cohesion: 0.33
Nodes (6): Deliverables, Exit Criteria, Phase 16.0 — Enterprise Hardening & Zero-Trust Infrastructure, Scope, Services Touched, Tasks

### Community 74 - "ElementType"
Cohesion: 0.07
Nodes (45): Enum, Image, ElementType, ParsedElement, Docling element labels, normalized for the pipeline., Page-Wise VLM Router outcome for a single element., One element extracted by Docling, normalized for the router., RouteDecision (+37 more)

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

### Community 81 - "MockModelProvider"
Cohesion: 0.06
Nodes (21): MockModelProvider, Mock implementation returning deterministic outputs for local testing., _load_pages(), 127 pages: high ratio + high coverage -> zero VLM cost., 58 pages: tables (Signal 1) or low-coverage sparse -> VLM., 5 pages (Hindi/Devanagari): Signal 5 must fire despite high ratio., 11 pages: 0.75-0.88 ratio -> DOCLING_TEXT (or VLM_TABLE if has_table)., Aggregate: every labeled page matches ground truth (no regressions). (+13 more)

### Community 83 - "vertex.py"
Cohesion: 0.40
Nodes (4): _is_resource_exhausted(), Exception, VertexAIProvider wrapping Google Cloud Vertex AI SDK. Uses text-embedding-004…, Return True if the exception is a Vertex/API rate-limit condition.

## Knowledge Gaps
- **284 isolated node(s):** `The two containers`, `How per-phase checkpointing still works without per-phase containers`, `Why this doesn't delay stage-by-stage checking`, `Scope`, `Tasks` (+279 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MemoryChunkStore` connect `MemoryChunkStore` to `QdrantChunkStore`, `ingestion/models.py`, `ingestion/main.py`, `build_qa_response`, `chunk_routed`, `check_pdf`, `TestDeepSearch`, `Chunk`, `TestMemoryChunkStoreSearch`, `TestPubSubEnvelopeDecode`, `test_delete_cascade.py`, `MockModelProvider`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `ModelProvider` connect `ModelProvider` to `ingestion/models.py`, `ingestion/main.py`, `SelfHostedGPUProvider`, `ElementType`, `MockModelProvider`, `MockVlmRouter`, `vertex.py`, `VertexAIProvider`, `.synthesize`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `MockModelProvider` connect `MockModelProvider` to `ingestion/models.py`, `StructuredAnswer`, `ingestion/main.py`, `build_qa_response`, `TestDeepSearch`, `MemoryChunkStore`, `ElementType`, `TestPubSubEnvelopeDecode`, `ModelProvider`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `MemoryChunkStore` (e.g. with `RecordingProvider` and `TestDeepSearch`) actually correct?**
  _`MemoryChunkStore` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `MockModelProvider` (e.g. with `Citation` and `ModelProvider`) actually correct?**
  _`MockModelProvider` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ElementType` (e.g. with `FitzPageRenderer` and `MockVlmRouter`) actually correct?**
  _`ElementType` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `RouteDecision` (e.g. with `FitzPageRenderer` and `MockVlmRouter`) actually correct?**
  _`RouteDecision` has 21 INFERRED edges - model-reasoned connections that need verification._