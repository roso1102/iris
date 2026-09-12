# Production Requirements

Requirement identifiers are stable. Implementations and benchmark manifests must reference them.

## 1. Functional requirements

### Ingestion

- **ING-001:** Uploads are streamed to object storage; the API must not buffer an entire maximum-size document in process memory.
- **ING-002:** Validate MIME by content, PDF structure, page count, file size, encryption, embedded attachments/scripts, decompression risk, and malware policy before parsing.
- **ING-003:** Create an immutable `DocumentVersion` containing tenant, document, version, SHA-256, source URI, size, MIME, ACL, sensitivity, language hints, uploader, timestamps, and pipeline version.
- **ING-004:** Each stage is independently retryable and idempotent under `(tenant_id, document_version_id, page_number, stage, stage_version)`.
- **ING-005:** Store immutable raw, rendered-page, OCR/layout JSON, normalized-document, chunk-manifest, and index-manifest artifacts.
- **ING-006:** Completion is determined by a durable barrier over expected page-stage records, never by the order in which pages finish.
- **ING-007:** Failed work enters a reason-coded DLQ and can be safely replayed without duplicate points or API calls.
- **ING-008:** Successful retry clears the corresponding failure state.
- **ING-009:** Document summaries run as durable queued work only after the completion barrier.
- **ING-010:** Activate a new document version atomically after validation; retain the previous version for rollback according to policy.
- **ING-011:** Deletion uses tombstone, asynchronous purge, reconciliation, and an auditable completion state.

### OCR, layout, and spatial provenance

- **OCR-001:** Every extracted span carries page number, original text offset, polygon, confidence, language/script, extraction engine/version, and coordinate-space identifier.
- **OCR-002:** Preserve page width, height, unit, crop box, rotation, render DPI, orientation, and any applied transform.
- **OCR-003:** Digital PDFs use native text spans where quality is acceptable; scanned/garbled pages use structured OCR with word/line geometry.
- **OCR-004:** A chunk citation maps to the union or list of polygons for the exact source spans, not the parser element or whole page unless explicitly marked `page_level_fallback`.
- **OCR-005:** Tables retain table, row, cell, header, and value span relationships and polygons.
- **OCR-006:** Preserve original text. Normalized, translated, and transliterated text are derivative search fields and must link back to the original spans.
- **OCR-007:** Support mixed scripts per page and at minimum Hindi/Devanagari plus the regional languages selected for the protected benchmark set.
- **OCR-008:** Low-confidence handwriting or geometry is routed to a higher-quality processor or human review; it must not be presented as precise evidence.

### Retrieval and conversation

- **RET-001:** Every retrieval operation enforces tenant, document ACL, active version, and optional authorized document scope inside the datastore query.
- **RET-002:** Original-query dense and sparse retrieval form the baseline path.
- **RET-003:** Query rewrite is used only for context-dependent turns and returns a strict object containing standalone query, preserved entities, temporal scope, document scope, language, confidence, and reason.
- **RET-004:** HyDE is optional. It runs only after deterministic/query-confidence gates or a weak baseline retrieval signal.
- **RET-005:** HyDE output cannot replace the original query legs and cannot introduce unverified named entities, amounts, identifiers, or dates.
- **RET-006:** Exact identifiers, quoted text, metadata requests, greetings, and navigation requests bypass HyDE.
- **RET-007:** Multi-hop decomposition is independently gated, bounded, schema-validated, and limited to authorized indexes/documents.
- **RET-008:** Route output is a strict enum with confidence and reason; all model-returned targets are intersected with the server-authorized target set.
- **RET-009:** Reranking consumes a bounded candidate set, returns real model scores, has a strict deadline, and falls back to stable hybrid ordering.
- **RET-010:** Diversity/MMR is applied after relevance reranking and is evaluated rather than hard-coded without evidence.
- **RET-011:** Every conversation turn is atomically persisted with turn ID, sequence, original query, standalone query, resolved entities, document scope, citations, and assistant output.
- **RET-012:** Concurrent turns use optimistic concurrency or serialized session execution.

### Synthesis

- **SYN-001:** Retrieved content, filenames, history, OCR output, and metadata are treated as untrusted evidence, never instructions.
- **SYN-002:** Every externally verifiable factual claim must be supported by one or more retrieved span IDs.
- **SYN-003:** Citations are resolved server-side from an evidence registry; model-supplied coordinates and document IDs are ignored.
- **SYN-004:** A claim/evidence entailment check and citation coverage policy run before release.
- **SYN-005:** The system abstains or requests clarification when evidence or routing confidence is below calibrated thresholds.
- **SYN-006:** Context construction uses an exact token budget and records which chunks were actually visible to the model.

## 2. Security and privacy requirements

- **SEC-001:** Tenant identity derives only from a verified token.
- **SEC-002:** Document access is enforced using server-derived user/group principals and sensitivity policy.
- **SEC-003:** Service accounts use least privilege; no runtime service has project-wide `datastore.owner` or all-secret access.
- **SEC-004:** Qdrant uses authenticated TLS/private connectivity and encryption/backup controls appropriate to the environment.
- **SEC-005:** Uploads pass malware and content-policy scanning before downstream services access them.
- **SEC-006:** PII/sensitivity classification, retention, deletion, residency, and redaction policies are tenant-configurable and auditable.
- **SEC-007:** Logs and traces exclude raw document/query text by default; sensitive payload capture requires explicit approved sampling.
- **SEC-008:** Direct and indirect prompt-injection suites must pass before release.
- **SEC-009:** Public errors use stable error codes and correlation IDs, not internal exception strings.
- **SEC-010:** CI enforces secret scanning, dependency/SAST checks, SBOM generation, signed images, provenance, and vulnerability policy.
- **SEC-011:** Security-relevant reads, writes, ACL changes, exports, deletes, replays, and administrative actions are immutably audited.

## 3. Reliability and operability requirements

- **REL-001:** External calls have connect, per-attempt, and overall deadlines; retry policies distinguish transient from permanent failures.
- **REL-002:** Retries use exponential backoff with full jitter and honor server retry hints.
- **REL-003:** Provider dependencies have bulkheads, concurrency limits, circuit breakers, and observable fallback behavior.
- **REL-004:** Dense failure may degrade to sparse, sparse to dense, reranker to fused order, but authorization and citation checks never degrade.
- **REL-005:** Qdrant production storage is replicated and has automated snapshots plus tested restore.
- **REL-006:** Readiness checks verify critical dependencies; liveness checks only verify the process.
- **REL-007:** Deployment uses immutable image digests, staged promotion, health-based canary, and automated rollback.
- **REL-008:** Infrastructure is declarative and drift-detected; shell deployment must not create resources duplicating Terraform resources.
- **REL-009:** Runbooks exist for provider outage, quota exhaustion, DLQ growth, bad model rollout, index corruption, security incident, and restore.

## 4. Observability requirements

- **OBS-001:** OpenTelemetry traces propagate through API, queue message, page stages, provider calls, Qdrant, Firestore, and synthesis.
- **OBS-002:** Every request has `trace_id`, `request_id`, and stable stage IDs; tenant identifiers in telemetry are hashed or tokenized.
- **OBS-003:** Metrics include latency distributions, error type, retry count, fallback rate, queue age, DLQ size, throughput, OCR quality, retrieval quality, grounding, tokens, pages, and estimated/actual cost.
- **OBS-004:** Dashboards and alerts are tied to explicit SLIs/SLOs and error budgets.
- **OBS-005:** Model, prompt, parser, chunker, OCR processor, index, and dataset versions appear in traces and benchmark records.

## 5. Performance, quality, and cost requirements

- **PERF-001:** `/search` warm P95 <= 500 ms and P99 <= 1,000 ms at the agreed concurrency profile, excluding optional HyDE/rerank paths.
- **PERF-002:** Standard `/query` warm P95 <= 2.5 seconds; enhanced/deep P95 <= 5 seconds, with time-to-first-byte tracked separately when streaming is added.
- **PERF-003:** A 5,000-page workload completes with zero lost pages, zero duplicate active chunks, and >= 99.5% automatically completed pages; remaining pages have explicit terminal/review states.
- **PERF-004:** No single corrupt document or provider quota event can exhaust all request capacity.
- **QUAL-001:** Held-out document Recall@5 >= 0.95, page Recall@5 >= 0.90, chunk nDCG@10 >= 0.80, subject to protected-slice minimums.
- **QUAL-002:** Follow-up standalone-query accuracy >= 0.95 overall and >= 0.90 for every protected language slice.
- **QUAL-003:** HyDE precision: >= 95% of HyDE invocations must belong to the labeled “beneficial/uncertain” class; HyDE must improve its eligible-slice Recall@5 by >= 3 absolute points without reducing overall nDCG.
- **QUAL-004:** Faithfulness >= 0.95, citation precision >= 0.98, citation coverage >= 0.95, and zero fabricated citation identifiers.
- **QUAL-005:** OCR and bbox thresholds are defined in `OCR_BBOX_DECISION.md` and are release gates.
- **COST-001:** Record cost per uploaded page, completed document, standard query, enhanced query, tenant, model and stage.
- **COST-002:** A phase cannot increase median cost by >10% without an approved, statistically demonstrated quality or reliability gain.
- **COST-003:** Repeated ingestion of an unchanged document must make zero OCR and embedding calls after cache validation.
- **COST-004:** Routing, rewrite, HyDE, decomposition and reranking invocation rates are measured and budgeted.

## 6. Maintainability and portability requirements

- **MNT-001:** Unit tests are hermetic and never download models or require cloud credentials.
- **MNT-002:** Provider and datastore SDK imports remain behind ports/adapters.
- **MNT-003:** API, event, OCR, chunk, route and benchmark schemas are versioned and compatibility-tested.
- **MNT-004:** Dependency versions are locked with reproducible hashes and scheduled update automation.
- **MNT-005:** A cloud migration requires a measured business case and port conformance suite; application code must not depend on provider-specific response dictionaries.

## 7. Global release gates

- Unit and component tests: 100% pass.
- Changed code branch coverage: >= 90%; critical authorization/idempotency/state-machine branches: 100%.
- No open P0/P1 defects or critical/high exploitable vulnerabilities.
- All phase-specific protected slices pass; averages cannot hide a language/document regression.
- Benchmark artifacts are committed and schema-valid.
- Staging canary and rollback drill pass.
- Operations, security, privacy, and product owners sign the phase record where their requirements are touched.
