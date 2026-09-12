# Step-by-Step Production Plan

Each phase follows: objective → changes → tests → benchmarks → stored evidence → exit gate → rollback. Estimates assume one experienced backend/RAG engineer plus part-time SRE/security support; parallel work may shorten calendar time but does not remove dependencies.

## Phase 0.0 — Baseline, governance, and containment

**Objective:** Establish trustworthy evidence and stop additional risk before changing behavior.  
**Estimated effort:** 3–5 days.  
**Requirements:** MNT-001, MNT-003, SEC-010, OBS-005.

### Changes

1. Create owners for ingestion, retrieval, security, data quality and SRE.
2. Assign stable IDs to known P0/P1 findings.
3. Capture current model, prompt, parser, dependency, Qdrant schema and infrastructure versions.
4. Make unit tests hermetic: remove the session-wide FastEmbed download; use deterministic sparse-vector fixtures/mocks and a separately marked provider-contract suite.
5. Pin development and CI dependencies with hashes; record Python/Node/Docker versions.
6. Add secret scanning and resolve `token.txt`: determine whether it is a credential without committing its content, rotate if necessary, then remove/ignore it according to policy.
7. Create versioned dataset manifests and seal held-out partitions.
8. Record the current benchmark as an immutable baseline; do not relabel historical targets as measured results.

### Unit/component tests

- Pure unit suite succeeds with network disabled and empty cloud credentials.
- A test fails deliberately if a unit fixture attempts DNS/network access.
- Benchmark schema validates required fields and rejects missing Git SHAs/dataset hashes.
- Secret scanner test fixture proves high-entropy and known token patterns are blocked.

### Benchmarks

- Full test duration, pass/fail/skip count and flaky rerun count.
- Existing retrieval metrics re-run only if the corpus and environment are reproducible; otherwise mark the legacy result as non-reproducible.
- Baseline API latency and process memory at idle and 1/10/25 concurrent requests.
- Baseline cost model from actual request/page/token counts; label estimates separately from billed values.

### Evidence and exit

Store `phase-0.0-baseline` run artifacts plus a completed phase record. Exit only when unit tests are hermetic, known failures are captured, datasets are immutable, and no suspected credential remains unhandled.

### Rollback

No production behavior change. Revert CI/test-fixture changes if they incorrectly exclude a required integration test, while retaining the provider suite under a separate marker.

---

## Phase 0.1 — Immediate correctness and security hotfixes

**Objective:** Eliminate current crash/data-state defects before architectural work.  
**Estimated effort:** 3–5 days.  
**Dependencies:** Phase 0.0.  
**Requirements:** ING-002, ING-006, RET-001, RET-008, SEC-009, REL-001.

### Changes

1. Initialize/structure query intent so standard `/query` works with and without `active_docs`.
2. Use a single monotonic clock for every latency measurement.
3. Validate non-empty query, history role/content/length, ID lists, active-document schema/count, and server-authorized document scope.
4. Replace public exception bodies with stable error codes and correlation IDs.
5. Verify the ingestion trigger response status before accepting its JSON.
6. Initialize ingestion progress before publishing and await every publish result.
7. Remove duplicate PDF download and guarantee bounded temporary-file cleanup.
8. Validate embedding response count/dimension before pairing with chunks or writing Qdrant points.
9. Fix known Hindi normalization/dictionary defects and delete unreachable duplicate cross-lingual assignments.
10. Add a temporary guard preventing page-level Gemini OCR output from being represented as a precise element bbox; return an explicitly coarse page-level citation until Phase 5.0.

### Tests

- Query matrix: mode × active_docs present/absent × doc_ids present/absent × session present/absent.
- Invalid/empty request property tests.
- Publisher partial-failure and timeout tests.
- Embedding response: empty, short, oversized, wrong dimension, NaN/Inf.
- Temporary-file cleanup on success, reject, timeout and exception.
- Public error response snapshot proving no internal exception/path/token leakage.

### Benchmarks

- Unit suite 100% pass; critical changed branches 100% covered.
- No negative or impossible latency values across 10,000 synthetic calls.
- Upload/query memory before and after; no full-file memory multiplier beyond the documented streaming buffer.
- No behavior/quality regression on the Phase 0.0 retrieval smoke set.

### Exit/rollback

No known P0 correctness defect, all matrix tests pass, and a stored comparison exists. Roll back individual flags/commits; schema remains unchanged in this phase.

---

## Phase 1.0 — Versioned contracts, domain boundaries, and feature flags

**Objective:** Make later changes safe, testable and reversible.  
**Estimated effort:** 1 week.  
**Dependencies:** Phase 0.1.  
**Requirements:** MNT-002, MNT-003, OCR-001–OCR-004, RET-003, RET-008.

### Changes

1. Define strict Pydantic/domain models: `DocumentVersion`, `PageArtifact`, `OcrPage`, `OcrSpan`, `PageGeometry`, `ChunkV2`, `RouteDecision`, `RewriteDecision`, `RetrievalTrace`, `EvidenceSpan`, `TurnState`, `StageEvent`, and `BenchmarkManifest`.
2. Replace provider-specific dictionaries at service boundaries with those contracts.
3. Add adapters/ports for OCR, layout parsing, object storage, workflow ledger, message queue, embeddings, reranking and vector storage.
4. Move direct Vertex imports out of ingestion summary code into the provider adapter.
5. Version API/event/chunk/index schemas; implement backward readers and forward writers.
6. Add flags for structured OCR, ingestion-v2, query-planner-v2, embedding-v2, reranker-v2 and grounding-v2.
7. Define deterministic IDs:
   - stage: hash of tenant/document-version/page/stage/version;
   - chunk: hash of document-version/page/span-range/chunker-version/content hash;
   - turn: server-generated ULID/UUID plus monotonic sequence.

### Tests and benchmarks

- JSON golden fixtures and malformed/future-version contract tests.
- Deterministic ID property tests across processes and retry order.
- Compatibility test: old chunks remain readable while v2 writes are disabled/enabled.
- Serialization latency and payload-size baseline; contract overhead must not add >5% API P95.

### Exit/rollback

All external boundaries use a versioned contract or have a documented exception. Flags default off. Rollback is flag-based with old readers retained.

---

## Phase 2.0 — OpenTelemetry, SLOs, and operational foundations

**Objective:** Make every subsequent change observable before increasing complexity.  
**Estimated effort:** 1 week.  
**Dependencies:** Phase 1.0.  
**Requirements:** OBS-001–OBS-005, REL-001–REL-003, SEC-007.

### Changes

1. Instrument FastAPI/Flask, HTTP/gRPC, Pub/Sub, Firestore, GCS, Qdrant and model/OCR adapters with OpenTelemetry.
2. Propagate W3C trace context through Pub/Sub attributes and preserve correlation through retries.
3. Add spans for classify, rewrite, baseline retrieval, HyDE, decomposition, fusion, rerank, context build, synthesis, citation validation, upload, parse, OCR, chunk, embed, index and activate.
4. Add metric cardinality rules; hash tenant/user IDs and prohibit raw evidence in telemetry.
5. Create dashboards for API SLO, ingestion SLO, queue/DLQ, providers, Qdrant, OCR quality, retrieval quality and cost.
6. Define alerts on symptoms: SLO burn, backlog age, stuck documents, retry storms, circuit-open rate, grounding failure and cost anomaly.
7. Add readiness checks and dependency-specific diagnostic endpoints protected by administrative authorization.

### Tests and benchmarks

- Trace propagation through upload → queue → page → index and query → answer.
- Span-error/status tests for 429, timeout, invalid response and fallback.
- PII/logging scan across captured test telemetry.
- Telemetry overhead at 1/10/50 concurrency: CPU, memory, payload volume and P95; target <5% latency overhead with sampling.
- Alert fire/recover tests and dashboard-as-code validation.

### Exit/rollback

>=95% of sampled requests contain required spans and version attributes. SLO alerts are tested. Rollback changes sampling/export, not instrumentation APIs.

---

## Phase 3.0 — Durable, idempotent ingestion control plane

**Objective:** Replace request-coupled fan-out with a replayable document state machine.  
**Estimated effort:** 2 weeks.  
**Dependencies:** Phases 1.0–2.0.  
**Requirements:** ING-001–ING-011, REL-001–REL-004, REL-008.

### Changes

1. Stream upload to GCS quarantine and create `DocumentVersion` plus an outbox event transactionally.
2. Implement stages: `QUARANTINED → VALIDATED → MANIFESTED → EXTRACTED → NORMALIZED → CHUNKED → EMBEDDED → INDEXED → QA_PASSED → ACTIVE`, with `RETRYABLE`, `FAILED`, `NEEDS_REVIEW`, `DELETING` terminal branches.
3. Select one queue path. Remove duplicate Eventarc/push ownership.
4. Use stage-specific queues or task types with explicit concurrency/quota budgets.
5. Persist expected pages before dispatch; use CAS leases and idempotency keys.
6. Await publication, store message IDs, and classify errors.
7. Implement retry with exponential full jitter, deadlines and DLQ.
8. Implement a completion barrier from ledger state, followed by queued summary and activation work.
9. Add a reconciler for stalled/missing/duplicate state and an authenticated replay operation.
10. Implement tombstone-first delete and orphan verification.

### Tests

- Duplicate and out-of-order delivery; crash before/after every external write.
- Lease expiry, competing workers, replay, poison page and partial provider response.
- Highest page completes first, last, or repeatedly.
- Delete races with active ingestion.
- Firestore/Qdrant/GCS unavailability and recovery.

### Benchmarks

- 10 × 100-page fault-injected corpus: zero lost pages and zero duplicate active chunks.
- 100 duplicate deliveries produce no extra OCR/embed calls and identical active manifests.
- Recovery time after worker termination and provider outage.
- Backlog drain rate and cost by stage.

### Exit/rollback

Every stage is demonstrably idempotent and replayable. Run old and new ingestion in shadow against separate version namespaces; rollback activation to the old version without deleting v2 evidence.

---

## Phase 4.0 — OCR, parser, layout, and bbox proof of capability

**Objective:** Choose the ingestion lanes using measured spatial and multilingual quality.  
**Estimated effort:** 2 weeks including annotation.  
**Dependencies:** Phases 1.0–3.0.  
**Requirements:** OCR-001–OCR-008, QUAL-005, COST-001.

### Candidates

- PyMuPDF native spans for clean digital PDFs.
- Google Enterprise Document OCR for scans, garbled fonts, handwriting and multilingual geometry.
- Docling with appropriate OCR for local/private or complex-layout processing.
- Optional Google Layout Parser for hierarchy/table/figure enrichment, never assumed to be the canonical geometry source.
- Azure Document Intelligence as a challenger only if organizational/cloud strategy justifies the integration cost.

### Changes

1. Build adapters that normalize every candidate into `OcrPage/OcrSpan/PageGeometry`.
2. Create `ocr-spatial-v1` with exact word/line polygons and adjudicated text.
3. Implement coordinate overlay tooling that renders the original PDF, candidate polygons and expected polygons at a fixed DPI.
4. Benchmark native, scanned, Hindi/regional, handwriting, skew, rotation, crop boxes, multi-column pages and tables.
5. Evaluate three routing policies: all-DocAI, digital-PyMuPDF/scan-DocAI, and PyMuPDF/Docling/DocAI hybrid.
6. Measure quality, latency, cold start, memory, API calls and billed cost.
7. Publish an ADR selecting the lanes, pinned processor/model versions and fallback.

### Tests and benchmark gates

- Geometry transform property/golden tests for 0/90/180/270° rotation and crop/media boxes.
- TextAnchor-to-span mapping and multi-polygon union tests.
- Scanned printed text: line median IoU >=0.90, word median IoU >=0.85, center containment >=0.95.
- Digital text: line median IoU >=0.95 and center containment >=0.99.
- Citation text-weighted coverage >=0.95 overall and >=0.90 per protected slice.
- Hindi printed scan WER <=10%; handwriting threshold is established from baseline but cannot exceed 20% for automatic precise citation.
- Reading-order Kendall tau >=0.95 digital and >=0.90 scanned.
- Report P50/P95 page latency, cost/page and manual-review rate.

### Exit/rollback

No vendor is selected on anecdote. Exit requires the ADR and immutable bake-off. All new adapters remain behind flags and write separate artifacts.

---

## Phase 5.0 — Production ingestion, multilingual normalization, and spatial citations

**Objective:** Implement the Phase 4.0 winner in the durable pipeline.  
**Estimated effort:** 2–3 weeks.  
**Dependencies:** Phase 4.0 decision.  
**Requirements:** OCR-001–OCR-008, ING-005, ING-010, COST-003.

### Changes

1. Implement a cheap digital/scan/complex-layout classifier with confidence and explainable signals.
2. Use PyMuPDF native spans for accepted digital pages; route scans/garbled/low-confidence pages to structured OCR.
3. Run full-page OCR once per page, not once per deficient element.
4. Preserve original and normalized Unicode; add language/script detection, transliteration and optional translation fields.
5. Chunk by heading/layout/paragraph/table boundaries using an actual tokenizer and Hindi/regional punctuation.
6. Map chunks to exact span lists/polygons. Store bounding rectangle only as a convenience derived field.
7. Store cell/row/header geometry for tables and figure/caption links.
8. Route low-confidence spans/pages to `NEEDS_REVIEW` or page-level citation fallback.
9. Deduplicate by content hash and stage/model version.

### Tests and benchmarks

- Unit tests for Unicode, Hindi danda, mixed scripts, transliteration linkage and tokenizer budgets.
- Visual regression snapshots for all protected geometry fixtures.
- OCR/bbox Phase 4.0 gates repeat on the production adapter.
- Compare chunk count, retrieval Recall@5, bbox coverage and storage per page against baseline.
- Unchanged re-ingestion produces zero OCR/embed calls.

### Exit/rollback

Canary by document version; old documents remain served until candidate version passes per-document QA. Roll back the active-version pointer.

---

## Phase 6.0 — Index lifecycle, multilingual retrieval storage, and Qdrant resilience

**Objective:** Make the retrieval store correct, versioned and recoverable.  
**Estimated effort:** 1–2 weeks.  
**Dependencies:** Phase 5.0 chunk schema.  
**Requirements:** RET-001, REL-005, COST-003, MNT-003.

### Changes

1. Select embedding model via multilingual bake-off; create a new named/versioned vector schema.
2. Validate every embedding count, dimension and finite value.
3. Add payload indexes for tenant, ACL principals/groups, document/version, language, element type and stage status; configure Qdrant tenant optimization where supported.
4. Upgrade Qdrant to a supported version after compatibility tests; evaluate per-tenant IDF and multilingual sparse retrieval.
5. Replace manual English-only BM25 preprocessing with benchmarked multilingual sparse strategy.
6. Use bounded bulk upsert with deterministic IDs and retries.
7. Provision replicated managed Qdrant or >=3-node production cluster, authenticated TLS, monitoring and snapshot lifecycle.
8. Implement dual-write/backfill, atomic alias/version switch and rollback.
9. Replace Qdrant scans for document status/listing with ledger counters.

### Tests and benchmarks

- Cross-tenant and cross-ACL negative tests at every store method.
- Re-embedding resume, partial batch, duplicate upsert and schema migration tests.
- Exact vs quantized/rescored recall/latency/memory comparison.
- Node loss, snapshot restore and corrupted-index recovery.
- Restore-point and restore-time objectives verified with checksums.

### Exit/rollback

Restore drill passes twice, protected retrieval slices meet targets, and old index alias can be restored without re-ingestion.

---

## Phase 7.0 — Conversation memory and adaptive query planning

**Objective:** Fix follow-ups and stop unconditional HyDE/decomposition.  
**Estimated effort:** 2 weeks.  
**Dependencies:** Phases 1.0, 2.0 and 6.0.  
**Requirements:** RET-002–RET-008, RET-011–RET-012, QUAL-002–QUAL-003.

### Changes

1. Persist an atomic `TurnState` with monotonic sequence and optimistic concurrency.
2. Add deterministic detectors for greeting/navigation, exact identifiers, quotations, metadata, summary, explicit document references and obvious ellipsis.
3. Add a structured context-dependence classifier only for unresolved cases.
4. Structured rewrite must preserve entities, dates, negation, language and authorized document scope.
5. Run baseline dense+sparse retrieval first for standalone queries.
6. Build a calibrated confidence gate using result margin, query coverage and route confidence.
7. Invoke HyDE only for labeled eligible/low-confidence conceptual queries.
8. Constrain HyDE to short, low-temperature structured output; reject new named entities/numbers/dates and low-similarity hypotheses.
9. Keep original dense and sparse legs and add HyDE as a lower-weight third leg.
10. Gate multi-hop decomposition separately and cap subqueries.
11. Evaluate LangGraph behind an interface for query state/checkpointing only. Adopt it only if it reduces orchestration defects without unacceptable latency, dependency or migration cost.

### Tests and benchmarks

- `conversation-v1`: follow-up standalone accuracy, entity/date/doc-scope F1 and concurrency ordering.
- `hyde-router-v1`: route macro-F1, HyDE invocation precision/recall, unnecessary-call rate and hallucinated-entity rate.
- A/B original hybrid vs conditional HyDE vs always-HyDE on identical queries.
- Required gates: follow-up accuracy >=0.95, HyDE call reduction target >=60% from current behavior, eligible Recall@5 lift >=3pp, overall nDCG non-inferior, standard P95 improvement recorded.
- Cost/query and provider-call counts by route.

### Exit/rollback

Shadow planner decisions first, then 5/25/50/100% canary. One flag restores the previous planner and memory reader.

---

## Phase 8.0 — Retrieval fusion, routing, reranking, and context selection

**Objective:** Improve page/chunk precision without unnecessary model cost.  
**Estimated effort:** 2 weeks.  
**Dependencies:** Phase 7.0.  
**Requirements:** RET-001–RET-010, QUAL-001, COST-002.

### Changes

1. Make dense and sparse dependency failures independent (`return_exceptions` plus typed fallback).
2. Add logical routes for document metadata, exact text, content, tables, figures, summaries and multi-document comparison using filters/named vectors rather than hallucinated raw index names.
3. Validate route targets and fan out to at most two routes when confidence is ambiguous.
4. Retrieve 50–100 candidates, content-deduplicate, rerank 30–50, then select 8–12 evidence units.
5. Benchmark managed reranker against multilingual BGE reranker; use actual scores, batching, deadline, cache and stable fallback.
6. Apply MMR/diversity after reranking and tune against held-out data.
7. Replace page-wide parent expansion with heading/section-based parent-child retrieval.
8. Add thresholded no-answer behavior when evidence quality is inadequate.

### Tests and benchmarks

- Fusion invariants, dependency-failure fallback, reranker timeout and stable-order tests.
- Authorized route target property tests.
- Full `retrieval-v1` with document/page/chunk metrics and protected slices.
- Reranker must improve nDCG@10 or page MRR by >=3pp on eligible queries, without >300 ms P95 increase unless approved.
- Overall page Recall@5 >=0.90 and chunk nDCG@10 >=0.80.

### Exit/rollback

Candidate index/router/reranker remains independently flaggable. Promotion requires measured lift and no security/filter regression.

---

## Phase 9.0 — Grounded synthesis, prompt-injection resistance, PII and authorization

**Objective:** Make answers evidence-bound and safe for enterprise data.  
**Estimated effort:** 2–3 weeks.  
**Dependencies:** Phase 8.0.  
**Requirements:** SYN-001–SYN-006, SEC-001–SEC-011.

### Changes

1. Enforce user/group/document ACLs in retrieval filters and signed source access.
2. Add ingestion-time sensitivity/PII classification and tenant policies for redaction, retention, residency and model eligibility.
3. Separate trusted instructions from untrusted evidence using typed prompt construction.
4. Add direct/indirect prompt-injection detection and policy responses; never allow evidence to change system actions or authorization.
5. Build exact token-budgeted context and record model-visible span IDs.
6. Parse structured claims/citations, resolve against the evidence registry, and run claim-level entailment/citation coverage.
7. Calibrate abstention and clarification behavior.
8. Reduce IAM permissions, restrict named secrets, authenticate/encrypt Qdrant and remove internal-error disclosure.
9. Add immutable audit events and approved privacy-safe telemetry.
10. Add SBOM, image signing/provenance and vulnerability gates.

### Tests and benchmarks

- Full ACL matrix and attempted filter bypass across every endpoint.
- `security-v1`: malicious documents, filenames, history and retrieved chunks.
- `grounding-v1`: faithfulness, citation entailment/coverage, conflicting/insufficient evidence and abstention.
- PII leakage scan over responses, logs, traces and benchmark artifacts.
- Gates: zero cross-tenant/document leaks, zero fabricated citation IDs, faithfulness >=0.95, citation precision >=0.98 and coverage >=0.95.

### Exit/rollback

Authorization and citation validation cannot be disabled as degradation paths. Model/policy variants are flaggable, but failure defaults to deny/abstain.

---

## Phase 10.0 — Cost and performance optimization

**Objective:** Meet budget and latency targets without protected-slice regression.  
**Estimated effort:** 1–2 weeks.  
**Dependencies:** Stable Phases 5.0–9.0.  
**Requirements:** COST-001–COST-004, PERF-001–PERF-004.

### Changes

1. Implement content/stage/model-version caches for OCR, chunks and embeddings.
2. Add query embedding, rewrite/route and rerank caches with privacy-safe tenant scope and bounded TTL.
3. Use cheaper model tiers for router/rewrite and exact/extractive paths for simple metadata/identifier answers.
4. Tune candidate counts, context tokens, embedding batch size, OCR routing thresholds and image resolution.
5. Remove repeated heavy Docling initialization by lane/shard design; right-size Cloud Run CPU/memory/concurrency.
6. Attribute estimated and billed cost per tenant/document/query/stage and implement budgets/anomaly alerts.
7. Add admission control, distributed token-bucket rate limiting and per-tenant quotas.

### Tests and benchmarks

- Cache isolation, invalidation, model-version and deletion tests.
- Cold/warm latency and cost at 1/10/50 concurrency.
- Ablations for every optimization; quality confidence intervals must remain within non-inferiority bounds.
- Unchanged document makes zero OCR/embed calls.
- Hard gates from PERF/COST requirements and no >1pp protected-slice quality regression.

### Exit/rollback

Each optimization has an independent flag and a stored ablation. Budget enforcement fails predictably without cross-tenant impact.

---

## Phase 11.0 — Enterprise scale, resilience, disaster recovery, and release engineering

**Objective:** Prove operation at and above the stated workload under faults.  
**Estimated effort:** 2 weeks.  
**Dependencies:** Phases 3.0–10.0.  
**Requirements:** PERF-003–PERF-004, REL-001–REL-009.

### Changes

1. Define capacity model for pages/minute, chunks/page, embed tokens, OCR quota, Qdrant points/storage and concurrent queries.
2. Configure adaptive queue concurrency and provider quota budgets.
3. Add circuit breakers, bulkheads, overload rejection and fair per-tenant scheduling.
4. Use immutable image digests and a single declarative deployment owner.
5. Implement progressive delivery: staging → shadow → 5% → 25% → 50% → 100%, with automated abort conditions.
6. Complete backup, restore, regional recovery and data-integrity runbooks.
7. Exercise DLQ replay, index rollback, model rollback and active-document-version rollback.

### Tests and benchmarks

- `scale-v1`: 50 documents × 100+ pages, heterogeneous mix, concurrent uploads and queries.
- Kill workers and Qdrant nodes; inject OCR/Vertex/Qdrant/Firestore/GCS 429/500/timeouts.
- 24-hour soak and memory/connection leak analysis.
- Gates: zero lost pages, zero duplicate active chunks, >=99.5% automatic completion, bounded backlog recovery, SLO compliance, successful restore and rollback.
- Report actual total cost and per-stage cost for the full workload.

### Exit/rollback

Two successful restore drills, one full rollback drill and approved capacity/error-budget review are mandatory.

---

## Phase 12.0 — General availability and continuous quality

**Objective:** Convert the project into an operated product rather than a completed migration.  
**Estimated effort:** ongoing.  
**Dependencies:** Phase 11.0.

### Changes

1. Establish release train, ownership rotation, incident process, postmortems and error-budget policy.
2. Run nightly protected quality/security suites, weekly load/restore checks and monthly red-team/model-lifecycle reviews.
3. Monitor language/document/query drift and sample low-confidence cases for adjudication.
4. Track model/processor retirement and execute versioned migrations before deadlines.
5. Add user feedback linked to evidence and trace IDs, with privacy controls.
6. Reconsider Azure/AWS, LangGraph, self-hosted reranking or Docling removal only through ADR plus benchmark evidence.

### GA gate

- Phases 0.0–11.0 accepted.
- No unresolved P0/P1 issue.
- SLO and security evidence covers at least one representative production-like observation window.
- On-call, incident, restore, replay, deletion and model-rollout runbooks exercised.
- Production release and rollback artifacts committed.
