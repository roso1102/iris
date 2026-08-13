# Graph Report - iris  (2026-08-09)

## Corpus Check
- 78 files · ~75,548 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 718 nodes · 1355 edges · 74 communities (55 shown, 19 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 203 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b854f533`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- check_pdf
- test_ingestion_security.py
- ModelProvider
- run_doc_on
- What You Must Do When Invoked
- MockVlmRouter
- MemoryChunkStore
- IngestionPipeline
- kill_switch
- healthz
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
- ingestion/main.py
- IRIS
- TestVertexAIIntegration
- IRIS — Phased Action Plan
- run_pipeline
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
- ParsedElement
- ElementType
- Chunk
- DoclingParser
- chunk_routed
- MockModelProvider
- StructuredAnswer
- TestDownloadLocalDevGate
- SelfHostedGPUProvider
- run_pipeline

## God Nodes (most connected - your core abstractions)
1. `MockVlmRouter` - 46 edges
2. `ElementType` - 45 edges
3. `MemoryChunkStore` - 45 edges
4. `Chunk` - 43 edges
5. `RouteDecision` - 42 edges
6. `ParsedElement` - 42 edges
7. `ModelProvider` - 37 edges
8. `IngestionPipeline` - 27 edges
9. `MockModelProvider` - 25 edges
10. `DoclingParser` - 24 edges

## Surprising Connections (you probably didn't know these)
- `TestDownloadLocalDevGate` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestMemoryChunkStoreThreadSafety` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestQAViewAuthGate` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestDownloadLocalDevGate` --uses--> `RetryError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestMemoryChunkStoreThreadSafety` --uses--> `RetryError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py

## Import Cycles
- None detected.

## Communities (74 total, 19 thin omitted)

### Community 0 - "check_pdf"
Cohesion: 0.09
Nodes (20): check_pdf(), Path, Validate a PDF file before it enters the pipeline. Returns metadata dict:…, _box(), _extract_page_elements(), _gen_corrupt_pdf(), _gen_oversized_pdf(), Path (+12 more)

### Community 1 - "test_ingestion_security.py"
Cohesion: 0.18
Nodes (9): build_qa_response(), _enforce_auth(), _qa_secret(), Chunk Visualization / QA view (ACTIONPLAN Task 1.10). Admin-only overlay:…, Return chunk overlay data for one page of a document. Requires QA_VIEW_SECRET…, Render page -> PIL, draw bboxes, return base64 PNG. None if unavailable., _render_overlay(), Security hardening tests — Findings 1-10 risk verification. (+1 more)

### Community 2 - "ModelProvider"
Cohesion: 0.13
Nodes (9): ModelProvider, ABC, Abstract Model Provider Interface., Generates a 768-dimensional vector embedding using the configured model…, Vision-Language Model (VLM) call on a cropped table/figure image region.…, Vision-Language Model (VLM) full-page call for scanned or low-text pages (<150…, Generates a grounded natural language answer with structured citations., SLM-tier query rewriter. Uses sliding window history (last N messages) to… (+1 more)

### Community 3 - "run_doc_on"
Cohesion: 0.21
Nodes (8): _box(), Table/chart-heavy gazette: verify table elements and low-text pages route…, scanned_eng.pdf: dense text government document., 70-page mixed English/Hindi document., testhindiwritten.pdf: Hindi document, some pages very short., Parse a PDF with Docling, route with VLM router, chunk, store. Returns stats…, Clean English PDF: most elements should route DOCLING_TEXT (zero cost)., run_doc_on()

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 5 - "MockVlmRouter"
Cohesion: 0.23
Nodes (8): MockVlmRouter, Deterministic router for tests: routes but never calls a real VLM., _el(), Phase 1.0 unit tests — Page-Wise VLM Router (Task 1.5). Covers Test 1-D (table…, Test 1-F: clean text pages never trigger a VLM call., Test 1-D: table element -> VLM table route, markdown output., Test 1-E: low-text element (<150 chars) -> full-page VLM., TestVlmRouter

### Community 6 - "MemoryChunkStore"
Cohesion: 0.19
Nodes (5): MemoryChunkStore, In-memory store for dev/tests. Thread-safe., TestMemoryChunkStoreThreadSafety, _chunk(), TestMemoryChunkStore

### Community 7 - "IngestionPipeline"
Cohesion: 0.16
Nodes (10): IngestionPipeline, Exception, Path, Payload must be rejected forever (never queued / straight to DLQ)., Transient failure; Pub/Sub should redeliver (up to 3 attempts)., Full pipeline for one uploaded document., RejectError, RetryError (+2 more)

### Community 8 - "kill_switch"
Cohesion: 0.47
Nodes (5): cloud_event, _kill_ingestion(), kill_switch(), Set pushConfig to empty on the subscription (pull-only)., _should_kill()

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
Cohesion: 0.11
Nodes (30): post, PublisherClient, compute_sha256(), _download_pdf(), Path, Page-level PDF splitter for parallel ingestion dispatch. Downloads a PDF from…, Upload a file to GCS., Split gs://bucket/path into (bucket, path). (+22 more)

### Community 35 - "IRIS Technical Benchmark Suite & Evaluation Framework"
Cohesion: 0.08
Nodes (23): 1.1 Hit Rate / Recall@K, 1.2 Mean Reciprocal Rank (MRR), 1.3 Precision@K, 1.4 Hybrid Search Lift (Dense vs. BM25 vs. Hybrid + RRF), 1. Retrieval Quality Metrics, 2.1 Faithfulness Score (Hallucination Detection), 2.2 Answer Relevancy, 2.3 Context Recall (+15 more)

### Community 36 - "👁️ IRIS — Intelligent Retrieval & Ingestion System"
Cohesion: 0.22
Nodes (8): 🔬 4-Signal Composite Decision Engine, 🥊 Competitive Advantage: Traditional Systems vs. IRIS, ⚡ End-to-End Pipeline Workflow, 📌 Executive Summary, 👁️ IRIS — Intelligent Retrieval & Ingestion System, 📊 Performance Benchmarks & Targets, 🎯 Production Engineering Challenges Solved, 🛠️ Technology Stack & Architectural Rationale

### Community 37 - "ingestion/main.py"
Cohesion: 0.10
Nodes (23): Image, Local integration test — runs full pipeline with mocks. No network calls., IngestResult, Ingestion orchestrator (ACTIONPLAN Tasks 1.2-1.9). Order: preflight -> download…, MockDocParser, Deterministic parser for local tests (MODEL_BACKEND=mock)., _crop_bbox(), FitzPageRenderer (+15 more)

### Community 38 - "IRIS"
Cohesion: 0.15
Nodes (12): 1. What This System Does, 2. Core Design Principles, 3. Technology Stack, 4. High-Level Architecture, 5. Getting Started (Once Implementation Begins), 6. Repository Structure (Target), 7. Key Documents, 8. Guiding Constraints (Do Not Violate) (+4 more)

### Community 40 - "TestVertexAIIntegration"
Cohesion: 0.18
Nodes (6): skipUnless, Test live Vertex AI text-embedding-004 call using gcloud credentials., Test live Gemini 2.5 Flash synthesis call., Test live Gemini 2.5 Flash Lite query rewrite call., Test live Gemini 2.5 Flash vision OCR call on sample image bytes., TestVertexAIIntegration

### Community 41 - "IRIS — Phased Action Plan"
Cohesion: 0.25
Nodes (7): Deployment & Containerization Strategy, How per-phase checkpointing still works without per-phase containers, IRIS — Phased Action Plan, 🏁 MVP LAUNCH BOUNDARY, Summary Timeline, The two containers, Why this doesn't delay stage-by-stage checking

### Community 42 - "run_pipeline"
Cohesion: 0.32
Nodes (5): _box(), Test 1-F: 27-page dense government document., Test 1-E: 7-page Hindi PDF with scanned/low-text pages., Test 1-D: 24-page chart/table-heavy gazette., run_pipeline()

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

### Community 64 - "ParsedElement"
Cohesion: 0.22
Nodes (5): ParsedElement, One element extracted by Docling, normalized for the router., Path, Return all elements across all pages, in reading order., Apply the routing table to a parsed document.

### Community 65 - "ElementType"
Cohesion: 0.26
Nodes (18): Enum, ElementType, Docling element labels, normalized for the pipeline., Page-Wise VLM Router outcome for a single element., RouteDecision, PreflightError, Exception, Raised when a payload is rejected before processing. (+10 more)

### Community 66 - "Chunk"
Cohesion: 0.14
Nodes (17): get_cached_chunks(), Document hash cache for ingestion deduplication. If a PDF has been previously…, Check if doc SHA256 has been previously stored. Returns list of Chunks if…, Chunk, BaseModel, A content unit ready to embed + store., ChunkStore, get_chunk_store() (+9 more)

### Community 67 - "DoclingParser"
Cohesion: 0.13
Nodes (15): _bbox_of(), DoclingParser, DocParser, _page_of(), _page_size(), ABC, Docling layout-aware parsing (ACTIONPLAN Task 1.4). Wraps Docling v2 and…, Extract 1-based page number from element provenance. (+7 more)

### Community 68 - "chunk_routed"
Cohesion: 0.15
Nodes (14): chunk_routed(), _chunk_text(), Sentence-boundary chunking (ACTIONPLAN Task 1.6). Text elements -> chunks at…, Convert routed elements into embeddable Chunks., Shared data model for the IRIS ingestion pipeline. A `Chunk` is the unit…, Pre-ingestion payload scanner (ACTIONPLAN Task 1.2). Rejects payloads BEFORE…, A routed element: either Docling text or a VLM call output., RoutingResult (+6 more)

### Community 70 - "MockModelProvider"
Cohesion: 0.17
Nodes (5): get_model_provider(), Factory function returning the active ModelProvider instance. MODEL_BACKEND…, MockModelProvider, Mock implementation returning deterministic outputs for local testing., TestModelProviderScaffold

### Community 71 - "StructuredAnswer"
Cohesion: 0.24
Nodes (9): Citation, BaseModel, ModelProvider Abstract Base Class for IRIS. All model inference calls…, StructuredAnswer, ModelProvider Factory for IRIS. Reads MODEL_BACKEND env var from Secret Manager…, Self-hosted GPU model provider (Phase 10.0). Provides local GPU inference for…, Package initialization for services.common.models., Mock ModelProvider implementation for zero-cost local testing and unit tests. (+1 more)

### Community 74 - "run_pipeline"
Cohesion: 0.40
Nodes (4): _box(), Test 1-A: 70-page mixed language PDF - full happy path., Test 1-F: 34-page English PDF - verify Docling produces rich text elements., run_pipeline()

## Knowledge Gaps
- **228 isolated node(s):** `create_iam_alert.sh script`, `deploy.sh script`, `setup_firebase.sh script`, `Key Binding Decisions`, `STRICT TEMPLATE RULES for CONTEXT.md (mandatory)` (+223 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ModelProvider` connect `ModelProvider` to `test_ingestion_security.py`, `chunk_routed`, `MockVlmRouter`, `ingestion/main.py`, `StructuredAnswer`, `IngestionPipeline`, `MockModelProvider`, `SelfHostedGPUProvider`, `TestDownloadLocalDevGate`, `MemoryChunkStore`, `VertexAIProvider`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `MockVlmRouter` connect `MockVlmRouter` to `ParsedElement`, `ElementType`, `ModelProvider`, `DoclingParser`, `chunk_routed`, `ingestion/main.py`, `check_pdf`, `IngestionPipeline`, `run_pipeline`, `run_pipeline`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `VertexAIProvider` connect `VertexAIProvider` to `TestVertexAIIntegration`, `ModelProvider`, `MockModelProvider`, `StructuredAnswer`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `MockVlmRouter` (e.g. with `IngestionPipeline` and `IngestResult`) actually correct?**
  _`MockVlmRouter` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `ElementType` (e.g. with `DoclingParser` and `DocParser`) actually correct?**
  _`ElementType` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `MemoryChunkStore` (e.g. with `Chunk` and `TestDoclingPipeline`) actually correct?**
  _`MemoryChunkStore` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `Chunk` (e.g. with `IngestionPipeline` and `IngestResult`) actually correct?**
  _`Chunk` has 21 INFERRED edges - model-reasoned connections that need verification._