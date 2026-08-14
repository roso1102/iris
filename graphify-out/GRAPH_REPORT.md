# Graph Report - iris  (2026-08-15)

## Corpus Check
- 106 files · ~154,609 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1139 nodes · 2235 edges · 93 communities (69 shown, 24 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 297 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `beeffee6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- check_pdf
- IngestionPipeline
- TestRouterSignals
- TestDoclingPipeline
- What You Must Do When Invoked
- TestVlmRouter
- Chunk
- SearchOrchestrator
- kill_switch
- retrieval_api/app.py
- create_iam_alert.sh
- deploy.sh
- setup_firebase.sh
- test_docling_api.py
- test_docling_api2.py
- test_docling_api3.py
- test_docling_api4.py
- test_docling_api5.py
- test_docling_api6.py
- test_docling_page.py
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
- ParsedElement
- IRIS
- eval_phase2.py
- IRIS — Phased Action Plan
- TestDoclingPipeline
- Phase 0.0 — Foundations & Safety Nets
- Phase 1.0 — Core Ingestion Pipeline ✅ (complete)
- Phase 2.0 — Vector Store & Retrieval
- Phase 3.0 — LLM Synthesis Layer
- Phase 4.0 — Authentication & Multi-Tenant Security
- Phase 5.0 — Frontend Integration (Vercel)
- Phase 0.1 — Model Provider Abstraction Scaffold
- Phase 6.0 — Conversational Memory + SLM-Based Query Rewrite ("Supermemory-Lite")
- Phase 7.0 — Trial / Freemium & Rate Limiting
- Phase 8.0 — Rephraser & Hypothesis Generator (HyDE)
- Phase 9.0 — Citation & Bbox Management Layer
- Phase 10.0 — Citation Map & Graph Node Network (Ingestion-Time)
- Phase 11.0 — Graph-Aware Retrieval (Query the Graph & Semantic Relationships)
- Phase 12.0 — Neural Reranking Upgrade
- Phase 14.0 — Mixture of Agents (MoA) Synthesis
- Phase 15.0 — GPU Swap-In (When Quota Available)
- Shared Context & Working Agreement
- Phase 13.0 — Context Compression
- Phase 16.0 — Enterprise Scale Hardening
- .commandcode/taste/taste.md
- taste/taste/taste.md
- QdrantChunkStore
- .search_dense
- MemoryChunkStore
- DoclingParser
- chunk_routed
- TestRetrievalApi
- ElementType
- base.py
- IRIS — Critical Fixes Register
- TestQAViewAuthGate
- TestSignal5
- TestMemoryChunkStoreSearch
- validate_table_markdown
- TestGroundTruthRouting
- TestPubSubEnvelopeDecode
- Phase 2.5 — Empirical Validation & Pipeline Hardening
- TestApiDeleteCascade
- MockModelProvider
- ModelProvider
- .parse
- TestVertexAIIntegration
- TestDownloadLocalDevGate
- SelfHostedGPUProvider
- ._cached_vlm_call
- _is_resource_exhausted
- .delete_by_doc
- .delete_by_session
- .search_sparse

## God Nodes (most connected - your core abstractions)
1. `MemoryChunkStore` - 76 edges
2. `ElementType` - 74 edges
3. `RouteDecision` - 70 edges
4. `Chunk` - 65 edges
5. `MockVlmRouter` - 56 edges
6. `ParsedElement` - 53 edges
7. `MockModelProvider` - 47 edges
8. `ModelProvider` - 40 edges
9. `IngestionPipeline` - 33 edges
10. `chunk_routed()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `TestIngestEntryPoint` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_pipeline.py → services/common/ingestion/main.py
- `TestIngestionPipelineWiring` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_pipeline.py → services/common/ingestion/main.py
- `TestDownloadLocalDevGate` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestQAViewAuthGate` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestDownloadLocalDevGate` --uses--> `RetryError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py

## Import Cycles
- None detected.

## Communities (93 total, 24 thin omitted)

### Community 0 - "check_pdf"
Cohesion: 0.09
Nodes (20): check_pdf(), Path, Validate a PDF file before it enters the pipeline. Returns metadata dict:…, _box(), _extract_page_elements(), _gen_corrupt_pdf(), _gen_oversized_pdf(), Path (+12 more)

### Community 1 - "IngestionPipeline"
Cohesion: 0.13
Nodes (13): IngestionPipeline, Exception, Path, Payload must be rejected forever (never queued / straight to DLQ)., Transient failure; Pub/Sub should redeliver (up to 3 attempts)., Full pipeline for one uploaded document or single-page blob., RejectError, RetryError (+5 more)

### Community 2 - "TestRouterSignals"
Cohesion: 0.21
Nodes (9): _el(), Verify the production `_route_element` signal table directly., fast_text tier: high word ratio + enough chars -> zero API cost., Signal 4: low-total-text page -> full-page OCR (page-level check)., Signal 4 is page-level: a short footer/heading on a text-rich page must NOT…, Signal 2: garbled OCR / unmapped encoding -> full-page OCR., Signal 3 case A: coverage < 0.15 and few chars., A sparse but valid text page (coverage 0.20) stays fast_text today. This… (+1 more)

### Community 3 - "TestDoclingPipeline"
Cohesion: 0.19
Nodes (10): _box(), integration, Clean English PDF: most elements should route DOCLING_TEXT (zero cost)., Table/chart-heavy gazette: verify table elements and low-text pages route…, scanned_eng.pdf: dense text government document., 70-page mixed English/Hindi document., testhindiwritten.pdf: Hindi document, some pages very short., Parse a PDF with Docling, route with VLM router, chunk, store. Returns stats… (+2 more)

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 5 - "TestVlmRouter"
Cohesion: 0.27
Nodes (5): _el(), Test 1-F: clean text pages never trigger a VLM call., Test 1-D: table element -> VLM table route, markdown output., Test 1-E: low-text element (<150 chars) -> full-page VLM., TestVlmRouter

### Community 6 - "Chunk"
Cohesion: 0.08
Nodes (29): get_cached_chunks(), Document hash cache for ingestion deduplication. If a PDF has been previously…, Check if doc SHA256 has been previously stored. Returns list of Chunks if…, Ingestion orchestrator (ACTIONPLAN Tasks 1.2-1.9). Order: preflight -> download…, Chunk, Shared data model for the IRIS ingestion pipeline. A `Chunk` is the unit…, A content unit ready to embed + store., ChunkStore (+21 more)

### Community 7 - "SearchOrchestrator"
Cohesion: 0.10
Nodes (8): Resolve RRF-fused (chunk_id, score) into full ScoredChunk objects., Orchestrates Standard + Deep search over the chunk store., SearchOrchestrator, If generate_hyde throws, deep_search must fall back to the rewrite., MockModelProvider that records every embed/rewrite/HyDE call., RecordingProvider, TestDeepSearch, TestSearchOrchestrator

### Community 8 - "kill_switch"
Cohesion: 0.47
Nodes (5): cloud_event, _kill_ingestion(), kill_switch(), Set pushConfig to empty on the subscription (pull-only)., _should_kill()

### Community 9 - "retrieval_api/app.py"
Cohesion: 0.07
Nodes (38): delete, diversity_penalty(), Diversity / dedup pass — prevents source-document flooding. Applies a…, Apply penalty to duplicate source docs in the top-K window. For each chunk in…, DeleteResponse, BaseModel, Phase 2.0 retrieval data models., A retrieved chunk with its fusion score. (+30 more)

### Community 21 - "VertexAIProvider"
Cohesion: 0.29
Nodes (3): Production Vertex AI implementation for GCP Cloud Run. Embeddings run in-region…, _sanitize_context(), VertexAIProvider

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

### Community 37 - "ParsedElement"
Cohesion: 0.08
Nodes (31): Image, Local integration test — runs full pipeline with mocks. No network calls., _chunk_text(), Sentence-boundary chunking (ACTIONPLAN Task 1.6). Text elements -> chunks at…, FIX-011: tag chunks whose extraction quality is mid-tier (standard_ocr). Pages…, _standard_ocr_metadata(), ParsedElement, BaseModel (+23 more)

### Community 38 - "IRIS"
Cohesion: 0.15
Nodes (12): 1. What This System Does, 2. Core Design Principles, 3. Technology Stack, 4. High-Level Architecture, 5. Getting Started (Once Implementation Begins), 6. Repository Structure (Target), 7. Key Documents, 8. Guiding Constraints (Do Not Violate) (+4 more)

### Community 40 - "eval_phase2.py"
Cohesion: 0.10
Nodes (43): check_tenant_isolation(), compute_mrr(), compute_page_recall_at_k(), compute_recall_at_k(), compute_source_duplication(), _id_token(), _ingest(), load_golden() (+35 more)

### Community 41 - "IRIS — Phased Action Plan"
Cohesion: 0.25
Nodes (7): Deployment & Containerization Strategy, How per-phase checkpointing still works without per-phase containers, IRIS — Phased Action Plan, 🏁 MVP LAUNCH BOUNDARY, Summary Timeline, The two containers, Why this doesn't delay stage-by-stage checking

### Community 42 - "TestDoclingPipeline"
Cohesion: 0.25
Nodes (7): _box(), integration, Test 1-D: 24-page chart/table-heavy gazette., Test 1-F: 27-page dense government document., Test 1-E: 7-page Hindi PDF with scanned/low-text pages., run_pipeline(), TestDoclingPipeline

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

### Community 47 - "Phase 4.0 — Authentication & Multi-Tenant Security"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 4.0 — Authentication & Multi-Tenant Security, Scope, Services Touched, Tasks

### Community 48 - "Phase 5.0 — Frontend Integration (Vercel)"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 5.0 — Frontend Integration (Vercel), Scope, Services Touched, Tasks

### Community 49 - "Phase 0.1 — Model Provider Abstraction Scaffold"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 0.1 — Model Provider Abstraction Scaffold, Scope, Services Touched, Tasks

### Community 50 - "Phase 6.0 — Conversational Memory + SLM-Based Query Rewrite ("Supermemory-Lite")"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 6.0 — Conversational Memory + SLM-Based Query Rewrite ("Supermemory-Lite"), Scope, Services Touched, Tasks

### Community 51 - "Phase 7.0 — Trial / Freemium & Rate Limiting"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 7.0 — Trial / Freemium & Rate Limiting, Scope, Services Touched, Tasks

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

### Community 56 - "Phase 12.0 — Neural Reranking Upgrade"
Cohesion: 0.33
Nodes (6): Benchmarks & Testing, Exit Criteria, Phase 12.0 — Neural Reranking Upgrade, Scope, Services Touched, Tasks

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
Cohesion: 0.10
Nodes (14): QdrantChunkStore, Phase 2.0 Qdrant store — v2 named-vector collection, hybrid search, cascading…, _hash_term(), BM25 TF-IDF sparse vector tokenizer for hybrid search. Uses rank_bm25 (pure…, Lowercase + split on word boundaries, filter short words and stopwords., Tokenize text into {term_hash: tf_idf_score} dict via rank_bm25. Uses a single-…, Convert to Qdrant SparseVector-compatible (indices, values) pair., sparse_to_qdrant_indices_values() (+6 more)

### Community 66 - "MemoryChunkStore"
Cohesion: 0.13
Nodes (12): IngestResult, MockDocParser, Deterministic parser for local tests (MODEL_BACKEND=mock)., MemoryChunkStore, In-memory store for dev/tests. Thread-safe., Tier 1 integration tests — IngestionPipeline wiring with fakes. Composes the…, Parse -> route -> chunk -> store, driven through the production objects., Full IngestionPipeline.ingest() with _download mocked to a real PDF. (+4 more)

### Community 67 - "DoclingParser"
Cohesion: 0.18
Nodes (10): DoclingParser, DocParser, ABC, Docling layout-aware parsing (ACTIONPLAN Task 1.4). Wraps Docling v2 and…, Parses a PDF into page-ordered ParsedElements with bboxes., Production parser backed by Docling v2. Falls back to CPU mode for PDFs >30…, Pre-ingestion payload scanner (ACTIONPLAN Task 1.2). Rejects payloads BEFORE…, Phase 1.0 Integration Tests -- via DoclingParser + IngestionPipeline. Runs the… (+2 more)

### Community 68 - "chunk_routed"
Cohesion: 0.09
Nodes (18): chunk_routed(), Convert routed elements into embeddable Chunks., _rr(), TestChunker, _box(), integration, Test 1-A: 70-page mixed language PDF - full happy path., Test 1-F: 34-page English PDF - verify Docling produces rich text elements. (+10 more)

### Community 70 - "ElementType"
Cohesion: 0.22
Nodes (22): Enum, ElementType, Docling element labels, normalized for the pipeline., Page-Wise VLM Router outcome for a single element., RouteDecision, PreflightError, Exception, Raised when a payload is rejected before processing. (+14 more)

### Community 71 - "base.py"
Cohesion: 0.24
Nodes (9): Citation, BaseModel, ModelProvider Abstract Base Class for IRIS. All model inference calls…, StructuredAnswer, ModelProvider Factory for IRIS. Reads MODEL_BACKEND env var from Secret Manager…, Self-hosted GPU model provider (Phase 10.0). Provides local GPU inference for…, Package initialization for services.common.models., Mock ModelProvider implementation for zero-cost local testing and unit tests. (+1 more)

### Community 72 - "IRIS — Critical Fixes Register"
Cohesion: 0.07
Nodes (26): FIX-001 — `QDRANT_URL` Missing from `ingestion-worker` Cloud Run Service, FIX-002 — Pub/Sub Push Subscription Detached by Billing Kill-Switch, FIX-003 — Qdrant Client 1.19.0 vs Server 1.13.0 Version Mismatch, FIX-004 — No `.dockerignore` Causes 78 GB Artifact Registry Bloat, FIX-005 — Page Numbers Stored as `0/0` (Pub/Sub Envelope Parsing Mismatch), FIX-006 — VLM Rate Limiting: 140–197 Gemini Vision Calls Per Document, FIX-007 — `/status` Returns 429 During Processing (`concurrency=1` Conflict), FIX-008 — No `multilingual_ocr` Routing Tier (Hindi / Devanagari Pages Silently Garbled) (+18 more)

### Community 73 - "TestQAViewAuthGate"
Cohesion: 0.20
Nodes (8): build_qa_response(), _enforce_auth(), _qa_secret(), Chunk Visualization / QA view (ACTIONPLAN Task 1.10). Admin-only overlay:…, Return chunk overlay data for one page of a document. Requires QA_VIEW_SECRET…, Render page -> PIL, draw bboxes, return base64 PNG. None if unavailable., _render_overlay(), TestQAViewAuthGate

### Community 74 - "TestSignal5"
Cohesion: 0.09
Nodes (14): _is_non_latin_dominant(), Signal 5 (FIX-008): True if >30% of letter chars are outside Latin/Extended-…, Tier 0 unit tests — Signal 5: Non-Latin Script Dominant Detection (FIX-008).…, Return True if >30% of letter characters are outside Latin/Extended-Latin., Verify FIX-008 Signal 5 non-Latin detection fires on Hindi, not English., Hindi page (valid_word_ratio ~0.82–0.87) must trigger Signal 5., Clean English text must never trigger Signal 5., English text with numerals/punctuation stays Latin-dominant. (+6 more)

### Community 76 - "validate_table_markdown"
Cohesion: 0.26
Nodes (5): Phase 2.5 — VLM table markdown validation. Validates that VLM-extracted…, Validate VLM-extracted Markdown table structure. Returns True if row/column…, validate_table_markdown(), Phase 2.5 unit tests — table markdown validator., TestTableValidator

### Community 77 - "TestGroundTruthRouting"
Cohesion: 0.13
Nodes (12): _char_count_for_coverage(), _load_pages(), 127 pages: high ratio + high coverage -> zero VLM cost., 58 pages: tables (Signal 1) or low-coverage sparse -> VLM., 5 pages (Hindi/Devanagari): Signal 5 must fire despite high ratio., 11 pages: 0.75-0.88 ratio -> DOCLING_TEXT (or VLM_TABLE if has_table)., Aggregate: every labeled page matches ground truth (no regressions)., Derive a plausible element char_count from page coverage + route. The CSV's… (+4 more)

### Community 78 - "TestPubSubEnvelopeDecode"
Cohesion: 0.36
Nodes (3): _load_worker_module(), FIX-005 — page_number must survive the Pub/Sub push envelope., TestPubSubEnvelopeDecode

### Community 79 - "Phase 2.5 — Empirical Validation & Pipeline Hardening"
Cohesion: 0.33
Nodes (6): Deliverables, Exit Criteria, Phase 2.5 — Empirical Validation & Pipeline Hardening, Scope, Services Touched, Tasks

### Community 80 - "TestApiDeleteCascade"
Cohesion: 0.14
Nodes (6): _chunk(), MemoryChunkStore.delete_by_doc cascade semantics., DELETE endpoints remove store chunks AND cascade to Firestore/GCS mocks., Return a firestore-mock whose .document(path).delete() is tracked., TestApiDeleteCascade, TestStoreDeleteCascade

### Community 81 - "MockModelProvider"
Cohesion: 0.16
Nodes (5): get_model_provider(), Factory function returning the active ModelProvider instance. MODEL_BACKEND…, MockModelProvider, Mock implementation returning deterministic outputs for local testing., TestModelProviderScaffold

### Community 83 - "ModelProvider"
Cohesion: 0.13
Nodes (9): ModelProvider, ABC, Abstract Model Provider Interface., Generates a 768-dimensional vector embedding using the configured model…, Vision-Language Model (VLM) call on a cropped table/figure image region.…, Vision-Language Model (VLM) full-page call for scanned or low-text pages (<150…, Generates a grounded natural language answer with structured citations., SLM-tier query rewriter. Uses sliding window history (last N messages) to… (+1 more)

### Community 84 - ".parse"
Cohesion: 0.17
Nodes (8): _bbox_of(), _page_of(), _page_size(), Path, Extract 1-based page number from element provenance., Return (width, height) in points for a Docling PageItem., Extract normalized [left, top, right, bottom] bbox (0-1). Docling v2 provides…, Return all elements across all pages, in reading order.

### Community 85 - "TestVertexAIIntegration"
Cohesion: 0.18
Nodes (6): skipUnless, Test live Vertex AI text-embedding-004 call using gcloud credentials., Test live Gemini 2.5 Flash synthesis call., Test live Gemini 2.5 Flash Lite query rewrite call., Test live Gemini 2.5 Flash vision OCR call on sample image bytes., TestVertexAIIntegration

### Community 88 - "._cached_vlm_call"
Cohesion: 0.50
Nodes (4): _load_cached_vlm(), Path, _store_cached_vlm(), _vlm_cache_dir()

### Community 89 - "_is_resource_exhausted"
Cohesion: 0.67
Nodes (3): _is_resource_exhausted(), Exception, Return True if the exception is a Vertex/API rate-limit condition.

## Knowledge Gaps
- **255 isolated node(s):** `create_iam_alert.sh script`, `deploy.sh script`, `setup_firebase.sh script`, `Key Binding Decisions`, `STRICT TEMPLATE RULES for CONTEXT.md (mandatory)` (+250 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MemoryChunkStore` connect `MemoryChunkStore` to `QdrantChunkStore`, `IngestionPipeline`, `check_pdf`, `DoclingParser`, `TestDoclingPipeline`, `chunk_routed`, `ElementType`, `Chunk`, `SearchOrchestrator`, `TestQAViewAuthGate`, `TestDoclingPipeline`, `ParsedElement`, `TestMemoryChunkStoreSearch`, `TestPubSubEnvelopeDecode`, `TestApiDeleteCascade`, `TestDownloadLocalDevGate`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Why does `Chunk` connect `Chunk` to `QdrantChunkStore`, `IngestionPipeline`, `MemoryChunkStore`, `chunk_routed`, `ParsedElement`, `ElementType`, `SearchOrchestrator`, `retrieval_api/app.py`, `TestQAViewAuthGate`, `TestMemoryChunkStoreSearch`, `TestApiDeleteCascade`, `TestDownloadLocalDevGate`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `ElementType` connect `ElementType` to `check_pdf`, `IngestionPipeline`, `TestRouterSignals`, `TestDoclingPipeline`, `TestVlmRouter`, `Chunk`, `SearchOrchestrator`, `ParsedElement`, `TestDoclingPipeline`, `QdrantChunkStore`, `MemoryChunkStore`, `DoclingParser`, `chunk_routed`, `TestQAViewAuthGate`, `TestMemoryChunkStoreSearch`, `TestGroundTruthRouting`, `TestPubSubEnvelopeDecode`, `TestApiDeleteCascade`, `TestDownloadLocalDevGate`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `MemoryChunkStore` (e.g. with `Chunk` and `ElementType`) actually correct?**
  _`MemoryChunkStore` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 43 inferred relationships involving `ElementType` (e.g. with `DoclingParser` and `DocParser`) actually correct?**
  _`ElementType` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `RouteDecision` (e.g. with `ChunkStore` and `MemoryChunkStore`) actually correct?**
  _`RouteDecision` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `Chunk` (e.g. with `IngestionPipeline` and `IngestResult`) actually correct?**
  _`Chunk` has 29 INFERRED edges - model-reasoned connections that need verification._