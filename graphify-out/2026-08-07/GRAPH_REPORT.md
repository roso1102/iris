# Graph Report - iris  (2026-08-06)

## Corpus Check
- 71 files · ~77,256 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 454 nodes · 932 edges · 36 communities (18 shown, 18 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 140 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c40fdd30`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MockVlmRouter
- MemoryChunkStore
- ModelProvider
- check_pdf
- What You Must Do When Invoked
- chunk_routed
- DoclingParser
- ingestion/main.py
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
- Exception
- Path
- ABC

## God Nodes (most connected - your core abstractions)
1. `MemoryChunkStore` - 44 edges
2. `MockVlmRouter` - 41 edges
3. `ParsedElement` - 40 edges
4. `ElementType` - 36 edges
5. `RouteDecision` - 33 edges
6. `ModelProvider` - 22 edges
7. `chunk_routed()` - 21 edges
8. `check_pdf()` - 21 edges
9. `MockModelProvider` - 20 edges
10. `DoclingParser` - 19 edges

## Surprising Connections (you probably didn't know these)
- `TestQAViewAuthGate` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestQAViewAuthGate` --uses--> `RetryError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestQAViewAuthGate` --uses--> `IngestionPipeline`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestDoclingPipeline` --uses--> `MemoryChunkStore`  [INFERRED]
  tests/test_docling_integration.py → services/common/ingestion/store.py
- `TestDoclingLargeCPU` --uses--> `MemoryChunkStore`  [INFERRED]
  tests/test_docling_large.py → services/common/ingestion/store.py

## Import Cycles
- None detected.

## Communities (36 total, 18 thin omitted)

### Community 0 - "MockVlmRouter"
Cohesion: 0.06
Nodes (60): Enum, Chunk, ElementType, ParsedElement, BaseModel, Shared data model for the IRIS ingestion pipeline. A `Chunk` is the unit…, Docling element labels, normalized for the pipeline., Page-Wise VLM Router outcome for a single element. (+52 more)

### Community 1 - "MemoryChunkStore"
Cohesion: 0.08
Nodes (25): ABC, ModelProvider, build_qa_response(), _enforce_auth(), _qa_secret(), Chunk Visualization / QA view (ACTIONPLAN Task 1.10). Admin-only overlay:…, Return chunk overlay data for one page of a document. Requires QA_VIEW_SECRET…, Render page -> PIL, draw bboxes, return base64 PNG. None if unavailable. (+17 more)

### Community 2 - "ModelProvider"
Cohesion: 0.08
Nodes (22): Citation, ModelProvider, ABC, BaseModel, ModelProvider Abstract Base Class for IRIS. All model inference calls…, Abstract Model Provider Interface., Generates a 768-dimensional vector embedding using the configured model…, Vision-Language Model (VLM) call on a cropped table/figure image region.… (+14 more)

### Community 3 - "check_pdf"
Cohesion: 0.06
Nodes (30): check_pdf(), Path, Pre-ingestion payload scanner (ACTIONPLAN Task 1.2). Rejects payloads BEFORE…, Validate a PDF file before it enters the pipeline. Returns metadata dict:…, _box(), Phase 1.0 Integration Tests -- via DoclingParser + IngestionPipeline. Runs the…, Table/chart-heavy gazette: verify table elements and low-text pages route…, scanned_eng.pdf: dense text government document. (+22 more)

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 5 - "chunk_routed"
Cohesion: 0.24
Nodes (9): chunk_routed(), _chunk_text(), Sentence-boundary chunking (ACTIONPLAN Task 1.6). Text elements -> chunks at…, Convert routed elements into embeddable Chunks., A routed element: either Docling text or a VLM call output., RoutingResult, Phase 1.0 unit tests — sentence-boundary chunking (Task 1.6)., _rr() (+1 more)

### Community 6 - "DoclingParser"
Cohesion: 0.12
Nodes (16): _bbox_of(), DoclingParser, DocParser, MockDocParser, _page_of(), _page_size(), ABC, Path (+8 more)

### Community 7 - "ingestion/main.py"
Cohesion: 0.07
Nodes (25): Exception, Path, post, IngestionPipeline, IngestResult, NoopPageRendererIfNoVlm, Chunk, Ingestion orchestrator (ACTIONPLAN Tasks 1.2-1.9). Order: preflight -> download… (+17 more)

### Community 8 - "kill_switch"
Cohesion: 0.47
Nodes (5): cloud_event, _kill_ingestion(), kill_switch(), Set pushConfig to empty on the subscription (pull-only)., _should_kill()

### Community 21 - "VertexAIProvider"
Cohesion: 0.19
Nodes (7): ModelProvider, Production Vertex AI implementation for GCP Cloud Run., _sanitize_context(), VertexAIProvider, StructuredAnswer, Test live Vertex AI text-embedding-004 call using gcloud credentials., TestVertexAIIntegration

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

## Knowledge Gaps
- **56 isolated node(s):** `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)`, `Step 1 - Ensure graphify is installed` (+51 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MemoryChunkStore` connect `MemoryChunkStore` to `MockVlmRouter`, `check_pdf`, `ingestion/main.py`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Why does `ModelProvider` connect `ModelProvider` to `MockVlmRouter`, `chunk_routed`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `MockVlmRouter` connect `MockVlmRouter` to `ModelProvider`, `check_pdf`, `ingestion/main.py`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `MemoryChunkStore` (e.g. with `TestDoclingPipeline` and `TestDoclingLargeCPU`) actually correct?**
  _`MemoryChunkStore` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `MockVlmRouter` (e.g. with `ElementType` and `ParsedElement`) actually correct?**
  _`MockVlmRouter` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `ParsedElement` (e.g. with `DoclingParser` and `DocParser`) actually correct?**
  _`ParsedElement` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ElementType` (e.g. with `DoclingParser` and `DocParser`) actually correct?**
  _`ElementType` has 21 INFERRED edges - model-reasoned connections that need verification._