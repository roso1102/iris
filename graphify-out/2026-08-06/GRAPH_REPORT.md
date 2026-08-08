# Graph Report - .  (2026-08-06)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 368 nodes · 952 edges · 21 communities (9 shown, 12 thin omitted)
- Extraction: 78% EXTRACTED · 22% INFERRED · 0% AMBIGUOUS · INFERRED: 205 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cd73cae9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MockVlmRouter
- MemoryChunkStore
- ModelProvider
- DoclingParser
- check_pdf
- chunk_routed
- RouterVlmRouter
- TestDownloadLocalDevGate
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

## God Nodes (most connected - your core abstractions)
1. `MockVlmRouter` - 47 edges
2. `MemoryChunkStore` - 45 edges
3. `ElementType` - 44 edges
4. `Chunk` - 42 edges
5. `RouteDecision` - 41 edges
6. `ParsedElement` - 40 edges
7. `ModelProvider` - 36 edges
8. `IngestionPipeline` - 25 edges
9. `DoclingParser` - 25 edges
10. `MockModelProvider` - 25 edges

## Surprising Connections (you probably didn't know these)
- `TestDownloadLocalDevGate` --uses--> `RejectError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestDownloadLocalDevGate` --uses--> `RetryError`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestDownloadLocalDevGate` --uses--> `IngestionPipeline`  [INFERRED]
  tests/test_ingestion_security.py → services/common/ingestion/main.py
- `TestChunker` --uses--> `ElementType`  [INFERRED]
  tests/test_chunker.py → services/common/ingestion/models.py
- `TestDoclingPipeline` --uses--> `ElementType`  [INFERRED]
  tests/test_docling_integration.py → services/common/ingestion/models.py

## Import Cycles
- None detected.

## Communities (21 total, 12 thin omitted)

### Community 0 - "MockVlmRouter"
Cohesion: 0.07
Nodes (53): Enum, Sentence-boundary chunking (ACTIONPLAN Task 1.6). Text elements -> chunks at…, ElementType, ParsedElement, Shared data model for the IRIS ingestion pipeline. A `Chunk` is the unit…, Docling element labels, normalized for the pipeline., Page-Wise VLM Router outcome for a single element., One element extracted by Docling, normalized for the router. (+45 more)

### Community 1 - "MemoryChunkStore"
Cohesion: 0.06
Nodes (44): post, IngestionPipeline, IngestResult, Exception, Path, Ingestion orchestrator (ACTIONPLAN Tasks 1.2-1.9). Order: preflight -> download…, Payload must be rejected forever (never queued / straight to DLQ)., Transient failure; Pub/Sub should redeliver (up to 3 attempts). (+36 more)

### Community 2 - "ModelProvider"
Cohesion: 0.06
Nodes (27): Citation, ModelProvider, ABC, BaseModel, ModelProvider Abstract Base Class for IRIS. All model inference calls…, Abstract Model Provider Interface., Generates a 768-dimensional vector embedding using the configured model…, Vision-Language Model (VLM) call on a cropped table/figure image region.… (+19 more)

### Community 3 - "DoclingParser"
Cohesion: 0.06
Nodes (33): NoopPageRendererIfNoVlm, Placeholder renderer; RouterVlmRouter overrides per-page rendering. The full…, _bbox_of(), DoclingParser, DocParser, MockDocParser, _page_of(), _page_size() (+25 more)

### Community 4 - "check_pdf"
Cohesion: 0.14
Nodes (11): check_pdf(), Path, Validate a PDF file before it enters the pipeline. Returns metadata dict:…, _box(), Test 1-A: 70-page mixed language PDF - full happy path., Test 1-F: 34-page English PDF - verify Docling produces rich text elements., run_pipeline(), TestDoclingLargeCPU (+3 more)

### Community 5 - "chunk_routed"
Cohesion: 0.22
Nodes (9): chunk_routed(), _chunk_text(), Convert routed elements into embeddable Chunks., A routed element: either Docling text or a VLM call output., Apply the routing table to a parsed document., RoutingResult, Phase 1.0 unit tests — sentence-boundary chunking (Task 1.6)., _rr() (+1 more)

### Community 6 - "RouterVlmRouter"
Cohesion: 0.15
Nodes (10): _crop_bbox(), NoopPageRenderer, PageRenderer, Crop a normalized bbox [l,t,r,b] from a rendered page., Renders PDF pages to images so the router can crop bbox regions., Return a PIL.Image of the given 1-based page at `scale`., Used when VLM routing is disabled (tests / cost control)., Production router: crops bbox regions and calls the VLM via ModelProvider. (+2 more)

### Community 8 - "kill_switch"
Cohesion: 0.47
Nodes (5): cloud_event, _kill_ingestion(), kill_switch(), Set pushConfig to empty on the subscription (pull-only)., _should_kill()

## Knowledge Gaps
- **3 isolated node(s):** `create_iam_alert.sh script`, `deploy.sh script`, `setup_firebase.sh script`
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ModelProvider` connect `ModelProvider` to `MockVlmRouter`, `MemoryChunkStore`, `DoclingParser`, `chunk_routed`, `RouterVlmRouter`, `TestDownloadLocalDevGate`?**
  _High betweenness centrality (0.181) - this node is a cross-community bridge._
- **Why does `MockVlmRouter` connect `MockVlmRouter` to `MemoryChunkStore`, `ModelProvider`, `DoclingParser`, `check_pdf`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Why does `MemoryChunkStore` connect `MemoryChunkStore` to `MockVlmRouter`, `DoclingParser`, `check_pdf`, `TestDownloadLocalDevGate`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `MockVlmRouter` (e.g. with `IngestionPipeline` and `IngestResult`) actually correct?**
  _`MockVlmRouter` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `MemoryChunkStore` (e.g. with `Chunk` and `TestDoclingPipeline`) actually correct?**
  _`MemoryChunkStore` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `ElementType` (e.g. with `DoclingParser` and `DocParser`) actually correct?**
  _`ElementType` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `Chunk` (e.g. with `IngestionPipeline` and `IngestResult`) actually correct?**
  _`Chunk` has 22 INFERRED edges - model-reasoned connections that need verification._