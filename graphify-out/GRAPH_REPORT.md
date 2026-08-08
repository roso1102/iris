# Graph Report - iris  (2026-08-07)

## Corpus Check
- 74 files · ~72,405 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 688 nodes · 1297 edges · 64 communities (46 shown, 18 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 201 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `536a832f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MockVlmRouter
- MemoryChunkStore
- base.py
- run_doc_on
- What You Must Do When Invoked
- chunk_routed
- .parse
- ElementType
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
- ModelProvider
- .route
- IRIS
- MockModelProvider
- TestDownloadLocalDevGate
- IRIS — Phased Action Plan
- run_pipeline
- Phase 0.0 — Foundations & Safety Nets
- Phase 1.0 — Core Ingestion Pipeline
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

## God Nodes (most connected - your core abstractions)
1. `MockVlmRouter` - 46 edges
2. `MemoryChunkStore` - 45 edges
3. `ElementType` - 44 edges
4. `Chunk` - 43 edges
5. `RouteDecision` - 41 edges
6. `ParsedElement` - 41 edges
7. `ModelProvider` - 35 edges
8. `IngestionPipeline` - 26 edges
9. `MockModelProvider` - 25 edges
10. `DoclingParser` - 24 edges

## Surprising Connections (you probably didn't know these)
- `TestDownloadLocalDevGate` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestQAViewAuthGate` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestDownloadLocalDevGate` --uses--> `RetryError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestQAViewAuthGate` --uses--> `RetryError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestDownloadLocalDevGate` --uses--> `IngestionPipeline`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py

## Import Cycles
- None detected.

## Communities (64 total, 18 thin omitted)

### Community 0 - "MockVlmRouter"
Cohesion: 0.06
Nodes (44): ParsedElement, BaseModel, One element extracted by Docling, normalized for the router., check_pdf(), PreflightError, Exception, Path, Pre-ingestion payload scanner (ACTIONPLAN Task 1.2). Rejects payloads BEFORE… (+36 more)

### Community 1 - "MemoryChunkStore"
Cohesion: 0.11
Nodes (15): build_qa_response(), _enforce_auth(), _qa_secret(), Chunk Visualization / QA view (ACTIONPLAN Task 1.10). Admin-only overlay:…, Return chunk overlay data for one page of a document. Requires QA_VIEW_SECRET…, Render page -> PIL, draw bboxes, return base64 PNG. None if unavailable., _render_overlay(), MemoryChunkStore (+7 more)

### Community 2 - "base.py"
Cohesion: 0.24
Nodes (10): Citation, BaseModel, ModelProvider Abstract Base Class for IRIS. All model inference calls…, StructuredAnswer, get_model_provider(), ModelProvider Factory for IRIS. Reads MODEL_BACKEND env var from Secret Manager…, Factory function returning the active ModelProvider instance. MODEL_BACKEND…, Package initialization for services.common.models. (+2 more)

### Community 3 - "run_doc_on"
Cohesion: 0.21
Nodes (8): _box(), Table/chart-heavy gazette: verify table elements and low-text pages route…, scanned_eng.pdf: dense text government document., 70-page mixed English/Hindi document., testhindiwritten.pdf: Hindi document, some pages very short., Parse a PDF with Docling, route with VLM router, chunk, store. Returns stats…, Clean English PDF: most elements should route DOCLING_TEXT (zero cost)., run_doc_on()

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 5 - "chunk_routed"
Cohesion: 0.22
Nodes (9): chunk_routed(), _chunk_text(), Convert routed elements into embeddable Chunks., A routed element: either Docling text or a VLM call output., Apply the routing table to a parsed document., RoutingResult, Phase 1.0 unit tests — sentence-boundary chunking (Task 1.6)., _rr() (+1 more)

### Community 6 - ".parse"
Cohesion: 0.15
Nodes (8): _bbox_of(), _page_of(), _page_size(), Path, Extract 1-based page number from element provenance., Return (width, height) in points for a Docling PageItem., Extract normalized [left, top, right, bottom] bbox (0-1). Docling v2 provides…, Return all elements across all pages, in reading order.

### Community 7 - "ElementType"
Cohesion: 0.06
Nodes (62): Enum, get_cached_chunks(), Document hash cache for ingestion deduplication. If a PDF has been previously…, Check if doc SHA256 has been previously stored. Returns list of Chunks if…, Sentence-boundary chunking (ACTIONPLAN Task 1.6). Text elements -> chunks at…, IngestionPipeline, IngestResult, Exception (+54 more)

### Community 8 - "kill_switch"
Cohesion: 0.47
Nodes (5): cloud_event, _kill_ingestion(), kill_switch(), Set pushConfig to empty on the subscription (pull-only)., _should_kill()

### Community 21 - "VertexAIProvider"
Cohesion: 0.21
Nodes (6): Production Vertex AI implementation for GCP Cloud Run., _sanitize_context(), VertexAIProvider, skipUnless, Test live Vertex AI text-embedding-004 call using gcloud credentials., TestVertexAIIntegration

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

### Community 36 - "ModelProvider"
Cohesion: 0.13
Nodes (9): ModelProvider, ABC, Abstract Model Provider Interface., Generates a 768-dimensional vector embedding using the configured model…, Vision-Language Model (VLM) call on a cropped table/figure image region.…, Vision-Language Model (VLM) full-page call for scanned or low-text pages (<150…, Generates a grounded natural language answer with structured citations., SLM-tier query rewriter. Uses sliding window history (last N messages) to… (+1 more)

### Community 37 - ".route"
Cohesion: 0.14
Nodes (9): Image, _crop_bbox(), _page_text_stats(), Compute text area coverage ratio and total char count for TEXT elements., Crop a normalized bbox [l,t,r,b] from a rendered page., Return a PIL.Image of the given 1-based page at `scale`., Return fraction of characters from recognizable script categories. Characters…, _to_png_bytes() (+1 more)

### Community 38 - "IRIS"
Cohesion: 0.15
Nodes (12): 1. What This System Does, 2. Core Design Principles, 3. Technology Stack, 4. High-Level Architecture, 5. Getting Started (Once Implementation Begins), 6. Repository Structure (Target), 7. Key Documents, 8. Guiding Constraints (Do Not Violate) (+4 more)

### Community 39 - "MockModelProvider"
Cohesion: 0.19
Nodes (3): MockModelProvider, Mock implementation returning deterministic outputs for local testing., TestModelProviderScaffold

### Community 41 - "IRIS — Phased Action Plan"
Cohesion: 0.25
Nodes (7): Deployment & Containerization Strategy, How per-phase checkpointing still works without per-phase containers, IRIS — Phased Action Plan, 🏁 MVP LAUNCH BOUNDARY, Summary Timeline, The two containers, Why this doesn't delay stage-by-stage checking

### Community 42 - "run_pipeline"
Cohesion: 0.32
Nodes (5): _box(), Test 1-F: 27-page dense government document., Test 1-E: 7-page Hindi PDF with scanned/low-text pages., Test 1-D: 24-page chart/table-heavy gazette., run_pipeline()

### Community 43 - "Phase 0.0 — Foundations & Safety Nets"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 0.0 — Foundations & Safety Nets, Scope, Services Touched, Tasks

### Community 44 - "Phase 1.0 — Core Ingestion Pipeline"
Cohesion: 0.29
Nodes (7): Benchmarks & Testing, Deliverables, Exit Criteria, Phase 1.0 — Core Ingestion Pipeline, Scope, Services Touched, Tasks

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

## Knowledge Gaps
- **221 isolated node(s):** `create_iam_alert.sh script`, `deploy.sh script`, `setup_firebase.sh script`, `Key Binding Decisions`, `STRICT TEMPLATE RULES for CONTEXT.md (mandatory)` (+216 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ModelProvider` connect `ModelProvider` to `MockVlmRouter`, `MemoryChunkStore`, `base.py`, `chunk_routed`, `MockModelProvider`, `ElementType`, `TestDownloadLocalDevGate`, `VertexAIProvider`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `MockVlmRouter` connect `MockVlmRouter` to `MemoryChunkStore`, `run_pipeline`, `ModelProvider`, `ElementType`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `IRIS — Phased Action Plan` connect `IRIS — Phased Action Plan` to `Phase 0.0 — Foundations & Safety Nets`, `Phase 1.0 — Core Ingestion Pipeline`, `Phase 2.0 — Vector Store & Retrieval`, `Phase 3.0 — LLM Synthesis Layer`, `Phase 4.0 — Authentication & Multi-Tenant Security`, `Phase 5.0 — Frontend Integration (Vercel)`, `Phase 0.1 — Model Provider Abstraction Scaffold`, `Phase 6.0 — Conversational Memory + SLM-Based Query Rewrite ("Supermemory-Lite")`, `Phase 7.0 — Trial / Freemium & Rate Limiting`, `Phase 8.0 — Rephraser & Hypothesis Generator (HyDE)`, `Phase 9.0 — Citation & Bbox Management Layer`, `Phase 10.0 — Citation Map & Graph Node Network (Ingestion-Time)`, `Phase 11.0 — Graph-Aware Retrieval (Query the Graph & Semantic Relationships)`, `Phase 12.0 — Neural Reranking Upgrade`, `Phase 14.0 — Mixture of Agents (MoA) Synthesis`, `Phase 15.0 — GPU Swap-In (When Quota Available)`, `Phase 13.0 — Context Compression`, `Phase 16.0 — Enterprise Scale Hardening`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `MockVlmRouter` (e.g. with `IngestionPipeline` and `IngestResult`) actually correct?**
  _`MockVlmRouter` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `MemoryChunkStore` (e.g. with `Chunk` and `TestDoclingPipeline`) actually correct?**
  _`MemoryChunkStore` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `ElementType` (e.g. with `DoclingParser` and `DocParser`) actually correct?**
  _`ElementType` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `Chunk` (e.g. with `IngestionPipeline` and `IngestResult`) actually correct?**
  _`Chunk` has 21 INFERRED edges - model-reasoned connections that need verification._