# Graph Report - iris  (2026-08-17)

## Corpus Check
- 98 files · ~119,240 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1157 nodes · 2090 edges · 82 communities (66 shown, 16 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 192 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `eecd7396`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ElementType
- TestMemoryChunkStoreThreadSafety
- TestRouterSignals
- FitzPageRenderer
- What You Must Do When Invoked
- DoclingParser
- retrieval_api/app.py
- TestDeepSearch
- kill_switch
- reciprocal_rank_fusion
- create_iam_alert.sh
- deploy.sh
- setup_firebase.sh
- TestSignal5
- Phase 4.0 — Authentication & Multi-Tenant Security
- Phase 7.0 — Trial / Freemium & Rate Limiting
- ModelProvider
- Phase 12.0 — Neural Reranking Upgrade & Precision Engineering
- run_pipeline
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
- qa_view.py
- IRIS
- ingestion/models.py
- eval_phase2.py
- IRIS — Phased Action Plan
- Chunk
- Phase 0.0 — Foundations & Safety Nets
- Phase 1.0 — Core Ingestion Pipeline ✅ (complete)
- Phase 2.0 — Vector Store & Retrieval
- Phase 3.0 — LLM Synthesis Layer
- Phase 3.5 — Retrieval Precision & Citation Quality Hardening (Lite)
- Phase 5.0 — Frontend Integration (Vercel)
- Phase 0.1 — Model Provider Abstraction Scaffold
- TestStoreDeleteCascade
- Phase 6.0 — Conversational Memory + SLM-Based Query Rewrite ("Supermemory-Lite")
- Phase 8.0 — Rephraser & Hypothesis Generator (HyDE)
- Phase 9.0 — Citation & Bbox Management Layer
- Phase 10.0 — Citation Map & Graph Node Network (Ingestion-Time)
- Phase 11.0 — Graph-Aware Retrieval (Query the Graph & Semantic Relationships)
- Phase 14.0 — Mixture of Agents (MoA) Synthesis
- Phase 15.0 — GPU Swap-In (When Quota Available)
- Shared Context & Working Agreement
- Phase 13.0 — Context Compression
- Phase 16.0 — Enterprise Scale Hardening
- .commandcode/taste/taste.md
- taste/taste/taste.md
- QdrantChunkStore
- Chunk
- MockVlmRouter
- chunk_routed
- TestRetrievalApi
- check_pdf
- IRIS — Critical Fixes Register
- MemoryChunkStore
- vlm_router.py
- TestMemoryChunkStoreSearch
- validate_table_markdown
- TestGroundTruthRouting
- TestPubSubEnvelopeDecode
- Phase 2.5 — Empirical Validation & Pipeline Hardening
- TestApiDeleteCascade
- MockModelProvider
- ABC
- Path

## God Nodes (most connected - your core abstractions)
1. `MemoryChunkStore` - 65 edges
2. `MockModelProvider` - 47 edges
3. `ElementType` - 45 edges
4. `RouteDecision` - 44 edges
5. `ModelProvider` - 40 edges
6. `ParsedElement` - 34 edges
7. `MockVlmRouter` - 32 edges
8. `Chunk` - 30 edges
9. `chunk_routed()` - 26 edges
10. `IngestionPipeline` - 25 edges

## Surprising Connections (you probably didn't know these)
- `TestChunkerPageFirst` --uses--> `DoclingParser`  [INFERRED]
  tests/test_page_chunking.py → services/common/ingestion/parser.py
- `TestMemoryChunkStoreThreadSafety` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestQAViewAuthGate` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestMemoryChunkStoreThreadSafety` --uses--> `RetryError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestQAViewAuthGate` --uses--> `RetryError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py

## Import Cycles
- None detected.

## Communities (82 total, 16 thin omitted)

### Community 0 - "ElementType"
Cohesion: 0.17
Nodes (12): Enum, ElementType, Docling element labels, normalized for the pipeline., Page-Wise VLM Router outcome for a single element., RouteDecision, str, Phase 1.0 unit tests — sentence-boundary chunking (Task 1.6)., Tier 1 integration tests — cascading delete (store + API level). Store level:… (+4 more)

### Community 2 - "TestRouterSignals"
Cohesion: 0.21
Nodes (9): _el(), Verify the production `_route_element` signal table directly., fast_text tier: high word ratio + enough chars -> zero API cost., Signal 4: low-total-text page -> full-page OCR (page-level check)., Signal 4 is page-level: a short footer/heading on a text-rich page must NOT…, Signal 2: garbled OCR / unmapped encoding -> full-page OCR., Signal 3 case A: coverage < 0.15 and few chars., A sparse but valid text page (coverage 0.20) stays fast_text today. This… (+1 more)

### Community 3 - "FitzPageRenderer"
Cohesion: 0.22
Nodes (6): Image, FitzPageRenderer, PageRenderer, Renders PDF pages to images so the router can crop bbox regions., Return a PIL.Image of the given 1-based page at `scale`., Production page renderer backed by PyMuPDF (fitz).

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 5 - "DoclingParser"
Cohesion: 0.09
Nodes (24): ABC, ParsedElement, Path, _bbox_of(), _bbox_of_items(), DoclingParser, DocParser, _page_of() (+16 more)

### Community 6 - "retrieval_api/app.py"
Cohesion: 0.06
Nodes (50): delete, Citation, BaseModel, Generates a grounded natural language answer with structured citations.…, StructuredAnswer, Package initialization for services.common.models., diversity_penalty(), Diversity / dedup pass — prevents source-document flooding. Applies a… (+42 more)

### Community 8 - "kill_switch"
Cohesion: 0.47
Nodes (5): cloud_event, _kill_ingestion(), kill_switch(), Set pushConfig to empty on the subscription (pull-only)., _should_kill()

### Community 9 - "reciprocal_rank_fusion"
Cohesion: 0.26
Nodes (5): Reciprocal Rank Fusion — merges two score-incompatible ranked lists. RRF is…, Merge dense and sparse ranked lists via RRF. Args: dense_results: [(chunk_id,…, reciprocal_rank_fusion(), Phase 2.0 unit tests — RRF fusion., TestRRF

### Community 13 - "TestSignal5"
Cohesion: 0.12
Nodes (9): Verify FIX-008 Signal 5 non-Latin detection fires on Hindi, not English., Hindi page (valid_word_ratio ~0.82–0.87) must trigger Signal 5., Clean English text must never trigger Signal 5., English text with numerals/punctuation stays Latin-dominant., A short Hindi clause still exceeds the 30% letter threshold., Empty and ASCII-only inputs never trigger Signal 5., A page that is exactly 30% non-Latin does NOT trigger (strict >)., Punctuation-only (no letters) never triggers Signal 5. (+1 more)

### Community 14 - "Phase 4.0 — Authentication & Multi-Tenant Security"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 4.0 — Authentication & Multi-Tenant Security, Scope, Services Touched, Tasks

### Community 15 - "Phase 7.0 — Trial / Freemium & Rate Limiting"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 7.0 — Trial / Freemium & Rate Limiting, Scope, Services Touched, Tasks

### Community 16 - "ModelProvider"
Cohesion: 0.12
Nodes (13): ModelProvider, ABC, ModelProvider Abstract Base Class for IRIS. All model inference calls…, Abstract Model Provider Interface., Generates a 768-dimensional vector embedding using the configured model…, Vision-Language Model (VLM) call on a cropped table/figure image region.…, Vision-Language Model (VLM) full-page call for scanned or low-text pages (<150…, SLM-tier query rewriter. Uses sliding window history (last N messages) to… (+5 more)

### Community 17 - "Phase 12.0 — Neural Reranking Upgrade & Precision Engineering"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 12.0 — Neural Reranking Upgrade & Precision Engineering, Scope, Services Touched, Tasks

### Community 18 - "run_pipeline"
Cohesion: 0.29
Nodes (6): DoclingParser, integration, Path, Parse -> route -> chunk -> store roundtrip on the golden corpus., run_pipeline(), TestDoclingPipelineTrueassort

### Community 19 - "bm25_cache"
Cohesion: 0.40
Nodes (4): fixture, bm25_cache(), Shared pytest fixtures. Bakes the FastEmbed Qdrant/bm25 model into a temp cache…, Download Qdrant/bm25 into a session-scoped temp HF cache and wire it up.…

### Community 21 - "VertexAIProvider"
Cohesion: 0.11
Nodes (13): _is_resource_exhausted(), Exception, VertexAIProvider wrapping Google Cloud Vertex AI SDK. Uses text-embedding-004…, Return True if the exception is a Vertex/API rate-limit condition., Production Vertex AI implementation for GCP Cloud Run. Embeddings run in-region…, _sanitize_context(), VertexAIProvider, skipUnless (+5 more)

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
Nodes (47): Client, PublisherClient, compute_sha256(), _download_pdf(), Path, Page-level PDF splitter for parallel ingestion dispatch. Downloads a PDF from…, Upload a file to GCS., Split gs://bucket/path into (bucket, path). (+39 more)

### Community 35 - "IRIS Technical Benchmark Suite & Evaluation Framework"
Cohesion: 0.08
Nodes (23): 1.1 Hit Rate / Recall@K, 1.2 Mean Reciprocal Rank (MRR), 1.3 Precision@K, 1.4 Hybrid Search Lift (Dense vs. BM25 vs. Hybrid + RRF), 1. Retrieval Quality Metrics, 2.1 Faithfulness Score (Hallucination Detection), 2.2 Answer Relevancy, 2.3 Context Recall (+15 more)

### Community 36 - "👁️ IRIS — Intelligent Retrieval & Ingestion System"
Cohesion: 0.22
Nodes (8): 🔬 4-Signal Composite Decision Engine, 🥊 Competitive Advantage: Traditional Systems vs. IRIS, ⚡ End-to-End Pipeline Workflow, 📌 Executive Summary, 👁️ IRIS — Intelligent Retrieval & Ingestion System, 📊 Performance Benchmarks & Targets, 🎯 Production Engineering Challenges Solved, 🛠️ Technology Stack & Architectural Rationale

### Community 37 - "qa_view.py"
Cohesion: 0.33
Nodes (5): _enforce_auth(), _qa_secret(), Chunk Visualization / QA view (ACTIONPLAN Task 1.10). Admin-only overlay:…, Render page -> PIL, draw bboxes, return base64 PNG. None if unavailable., _render_overlay()

### Community 38 - "IRIS"
Cohesion: 0.15
Nodes (12): 1. What This System Does, 2. Core Design Principles, 3. Technology Stack, 4. High-Level Architecture, 5. Getting Started (Once Implementation Begins), 6. Repository Structure (Target), 7. Key Documents, 8. Guiding Constraints (Do Not Violate) (+4 more)

### Community 39 - "ingestion/models.py"
Cohesion: 0.18
Nodes (10): Sentence-boundary chunking (ACTIONPLAN Task 1.6). Text elements -> chunks at…, IngestResult, Ingestion orchestrator (ACTIONPLAN Tasks 1.2-1.9). Order: preflight -> download…, Shared data model for the IRIS ingestion pipeline. A `Chunk` is the unit…, Docling layout-aware parsing (ACTIONPLAN Task 1.4). Wraps Docling v2 and…, Docling pipeline integration tests — run against trueassort/ golden corpus.…, Docling CPU pipeline tests — run the full trueassort/ corpus on CPU. Run:…, Docling pipeline integration tests — parse/route/chunk/store against… (+2 more)

### Community 40 - "eval_phase2.py"
Cohesion: 0.10
Nodes (43): check_tenant_isolation(), compute_mrr(), compute_page_recall_at_k(), compute_recall_at_k(), compute_source_duplication(), _id_token(), _ingest(), load_golden() (+35 more)

### Community 41 - "IRIS — Phased Action Plan"
Cohesion: 0.25
Nodes (7): Deployment & Containerization Strategy, How per-phase checkpointing still works without per-phase containers, IRIS — Phased Action Plan, 🏁 MVP LAUNCH BOUNDARY, Summary Timeline, The two containers, Why this doesn't delay stage-by-stage checking

### Community 42 - "Chunk"
Cohesion: 0.20
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

### Community 46 - "Phase 3.0 — LLM Synthesis Layer"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 3.0 — LLM Synthesis Layer, Scope, Services Touched, Tasks

### Community 47 - "Phase 3.5 — Retrieval Precision & Citation Quality Hardening (Lite)"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 3.5 — Retrieval Precision & Citation Quality Hardening (Lite), Scope, Services Touched, Tasks

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

### Community 57 - "Phase 14.0 — Mixture of Agents (MoA) Synthesis"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 14.0 — Mixture of Agents (MoA) Synthesis, Scope, Services Touched, Tasks

### Community 58 - "Phase 15.0 — GPU Swap-In (When Quota Available)"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 15.0 — GPU Swap-In (When Quota Available), Scope, Services Touched, Tasks

### Community 59 - "Shared Context & Working Agreement"
Cohesion: 0.33
Nodes (5): Agent Workflow Discipline, AGENTS.md — Instructions for AI Coding Agents (Auto-loaded), Key Binding Decisions, Shared Context & Working Agreement, STRICT TEMPLATE RULES for CONTEXT.md (mandatory)

### Community 60 - "Phase 13.0 — Context Compression"
Cohesion: 0.40
Nodes (5): Benchmarks & Testing, Exit Criteria, Phase 13.0 — Context Compression, Scope, Tasks

### Community 61 - "Phase 16.0 — Enterprise Scale Hardening"
Cohesion: 0.40
Nodes (5): Benchmarks & Testing, Exit Criteria, Phase 16.0 — Enterprise Scale Hardening, Scope, Tasks

### Community 64 - "QdrantChunkStore"
Cohesion: 0.08
Nodes (20): QdrantChunkStore, Phase 2.0 Qdrant store — v2 named-vector collection, hybrid search, cascading…, _get_model(), BM25 sparse vector tokenizer backed by FastEmbed's Qdrant/bm25 model. Replaces…, Lazily initialize the singleton FastEmbed Bm25 model (thread-safe). Loads…, Encode text into {term_index: raw_term_count} via Qdrant/bm25. Returns an empty…, Convert to Qdrant SparseVector-compatible (indices, values) pair., Return the term indices encoded for `text` (for tests/debugging). FastEmbed's… (+12 more)

### Community 65 - "Chunk"
Cohesion: 0.08
Nodes (27): get_cached_chunks(), Document hash cache for ingestion deduplication. If a PDF has been previously…, Check if doc SHA256 has been previously stored. Returns list of Chunks if…, Chunk, BaseModel, A content unit ready to embed + store., ChunkStore, get_chunk_store() (+19 more)

### Community 66 - "MockVlmRouter"
Cohesion: 0.05
Nodes (31): IngestionPipeline, Chunk, Exception, Path, Payload must be rejected forever (never queued / straight to DLQ)., Transient failure; Pub/Sub should redeliver (up to 3 attempts)., Full pipeline for one uploaded document or single-page blob., RejectError (+23 more)

### Community 68 - "chunk_routed"
Cohesion: 0.12
Nodes (17): Chunk, RoutingResult, chunk_routed(), _chunk_text(), FIX-011: tag chunks whose extraction quality is mid-tier (standard_ocr). Pages…, Convert routed elements into embeddable Chunks. Phase 3.5 page-boundary strict…, _standard_ocr_metadata(), _rr() (+9 more)

### Community 70 - "check_pdf"
Cohesion: 0.08
Nodes (26): check_pdf(), PreflightError, Exception, Path, Pre-ingestion payload scanner (ACTIONPLAN Task 1.2). Rejects payloads BEFORE…, Raised when a payload is rejected before processing., Validate a PDF file before it enters the pipeline. Returns metadata dict:…, _load_labels() (+18 more)

### Community 72 - "IRIS — Critical Fixes Register"
Cohesion: 0.07
Nodes (26): FIX-001 — `QDRANT_URL` Missing from `ingestion-worker` Cloud Run Service, FIX-002 — Pub/Sub Push Subscription Detached by Billing Kill-Switch, FIX-003 — Qdrant Client 1.19.0 vs Server 1.13.0 Version Mismatch, FIX-004 — No `.dockerignore` Causes 78 GB Artifact Registry Bloat, FIX-005 — Page Numbers Stored as `0/0` (Pub/Sub Envelope Parsing Mismatch), FIX-006 — VLM Rate Limiting: 140–197 Gemini Vision Calls Per Document, FIX-007 — `/status` Returns 429 During Processing (`concurrency=1` Conflict), FIX-008 — No `multilingual_ocr` Routing Tier (Hindi / Devanagari Pages Silently Garbled) (+18 more)

### Community 73 - "MemoryChunkStore"
Cohesion: 0.20
Nodes (5): build_qa_response(), Return chunk overlay data for one page of a document. Requires QA_VIEW_SECRET…, MemoryChunkStore, In-memory store for dev/tests. Thread-safe., TestQAViewAuthGate

### Community 74 - "vlm_router.py"
Cohesion: 0.08
Nodes (33): ParsedElement, One element extracted by Docling, normalized for the router., _crop_bbox(), _is_non_latin_dominant(), _load_cached_vlm(), _page_text_stats(), ABC, Path (+25 more)

### Community 76 - "validate_table_markdown"
Cohesion: 0.26
Nodes (5): Phase 2.5 — VLM table markdown validation. Validates that VLM-extracted…, Validate VLM-extracted Markdown table structure. Returns True if row/column…, validate_table_markdown(), Phase 2.5 unit tests — table markdown validator., TestTableValidator

### Community 77 - "TestGroundTruthRouting"
Cohesion: 0.17
Nodes (8): _load_pages(), 127 pages: high ratio + high coverage -> zero VLM cost., 58 pages: tables (Signal 1) or low-coverage sparse -> VLM., 5 pages (Hindi/Devanagari): Signal 5 must fire despite high ratio., 11 pages: 0.75-0.88 ratio -> DOCLING_TEXT (or VLM_TABLE if has_table)., Aggregate: every labeled page matches ground truth (no regressions)., Every labeled page in the CSV must route as the ground truth says., TestGroundTruthRouting

### Community 78 - "TestPubSubEnvelopeDecode"
Cohesion: 0.36
Nodes (3): _load_worker_module(), FIX-005 — page_number must survive the Pub/Sub push envelope., TestPubSubEnvelopeDecode

### Community 79 - "Phase 2.5 — Empirical Validation & Pipeline Hardening"
Cohesion: 0.33
Nodes (6): Deliverables, Exit Criteria, Phase 2.5 — Empirical Validation & Pipeline Hardening, Scope, Services Touched, Tasks

### Community 80 - "TestApiDeleteCascade"
Cohesion: 0.21
Nodes (4): _chunk(), DELETE endpoints remove store chunks AND cascade to Firestore/GCS mocks., Return a firestore-mock whose .document(path).delete() is tracked., TestApiDeleteCascade

### Community 81 - "MockModelProvider"
Cohesion: 0.07
Nodes (11): get_model_provider(), Factory function returning the active ModelProvider instance. MODEL_BACKEND…, Dormant GPU provider stub. Implemented in Phase 10.0., SelfHostedGPUProvider, MockModelProvider, Mock implementation returning deterministic outputs for local testing., TestModelProviderScaffold, FIX-005 wiring: page_number_override reaches every stored chunk. (+3 more)

## Knowledge Gaps
- **261 isolated node(s):** `The two containers`, `How per-phase checkpointing still works without per-phase containers`, `Why this doesn't delay stage-by-stage checking`, `Scope`, `Tasks` (+256 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ModelProvider` connect `ModelProvider` to `Chunk`, `MockVlmRouter`, `FitzPageRenderer`, `TestMemoryChunkStoreThreadSafety`, `retrieval_api/app.py`, `ingestion/models.py`, `MemoryChunkStore`, `vlm_router.py`, `MockModelProvider`, `VertexAIProvider`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `MemoryChunkStore` connect `MemoryChunkStore` to `QdrantChunkStore`, `Chunk`, `ElementType`, `MockVlmRouter`, `chunk_routed`, `TestMemoryChunkStoreThreadSafety`, `check_pdf`, `TestDeepSearch`, `ingestion/models.py`, `Chunk`, `TestMemoryChunkStoreSearch`, `TestPubSubEnvelopeDecode`, `TestApiDeleteCascade`, `ModelProvider`, `TestStoreDeleteCascade`, `run_pipeline`, `MockModelProvider`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `MockModelProvider` connect `MockModelProvider` to `Chunk`, `MockVlmRouter`, `TestMemoryChunkStoreThreadSafety`, `TestRouterSignals`, `FitzPageRenderer`, `retrieval_api/app.py`, `TestDeepSearch`, `ingestion/models.py`, `MemoryChunkStore`, `vlm_router.py`, `TestGroundTruthRouting`, `TestPubSubEnvelopeDecode`, `ModelProvider`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `MemoryChunkStore` (e.g. with `RecordingProvider` and `TestDeepSearch`) actually correct?**
  _`MemoryChunkStore` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `MockModelProvider` (e.g. with `Citation` and `ModelProvider`) actually correct?**
  _`MockModelProvider` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `ElementType` (e.g. with `FitzPageRenderer` and `MockVlmRouter`) actually correct?**
  _`ElementType` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `RouteDecision` (e.g. with `FitzPageRenderer` and `MockVlmRouter`) actually correct?**
  _`RouteDecision` has 23 INFERRED edges - model-reasoned connections that need verification._