# Observability, Security, Resilience, and Cost Plan

## 1. OpenTelemetry design

### Traces

Root operations:

- `http.query`, `http.search`, `http.upload`, `http.delete`
- `ingestion.document`, `ingestion.page`, `ingestion.stage`
- `workflow.reconcile`, `workflow.replay`, `workflow.activate`

Required child spans:

- `auth.verify`, `acl.resolve`, `session.load`, `query.classify`, `query.rewrite`, `query.hyde`, `query.decompose`, `query.route`
- `embedding.query`, `search.dense`, `search.sparse`, `search.fuse`, `search.rerank`, `search.diversify`, `context.build`
- `synthesis.generate`, `grounding.claims`, `grounding.citations`, `policy.output`
- `upload.validate`, `pdf.manifest`, `page.render`, `page.extract`, `ocr.process`, `layout.merge`, `chunk.build`, `embedding.document`, `index.upsert`, `qa.spatial`

Required attributes use bounded cardinality:

- service/version, environment, region, trace/request/stage ID
- hashed tenant ID; never raw user identity
- document-version/page/stage IDs where operationally safe
- model/prompt/parser/OCR/chunker/index schema versions
- route/mode/fallback/error class/retry number
- input/output token counts, OCR pages, candidates, chunks visible to model
- estimated cost and provider latency

Raw query, document text, OCR output, embeddings, tokens and filenames are prohibited by default.

### Metrics and SLOs

| SLI | Initial SLO |
|---|---|
| Authorized `/search` success | 99.9% monthly |
| Authorized `/query` success | 99.5% monthly, excluding valid abstentions |
| Warm `/search` latency | P95 <=500 ms, P99 <=1 s |
| Standard `/query` latency | P95 <=2.5 s |
| Ingestion terminal-state rate | >=99.9% reaches active/review/rejected within policy window |
| Lost/duplicate active pages | 0 |
| Grounded-answer rate | >=95% on monitored adjudicated sample |
| Cross-tenant/document authorization violation | 0 |

Use multi-window burn-rate alerts. Page on fast error-budget burn, tenant-isolation signals, data loss, unrecoverable backlog and security findings; ticket slower quality/cost drift.

### Dashboards

1. Query health and route mix.
2. Retrieval/grounding quality and protected slices.
3. Ingestion stages, backlog age, retries and DLQ.
4. OCR quality, lane selection and manual review.
5. Qdrant/Firestore/GCS/provider saturation.
6. Cost by tenant, document, stage, model and route.
7. Security policy, authorization denials and injection detection.

## 2. Retry, timeout, bulkhead, and circuit-breaker policy

Each adapter declares:

- connect timeout, per-attempt timeout and total deadline;
- retryable status/error set;
- maximum attempts and full-jitter backoff;
- idempotency guarantee;
- concurrency limit and queue capacity;
- circuit-open threshold/recovery probe;
- fallback and whether it is security/quality permissible.

Never retry malformed input, authentication/authorization denial, unsupported type, schema violation or deterministic provider rejection. Do not sleep for minutes inside an HTTP/queue request. Reschedule durable work with `not_before` and preserve the stage lease.

Fallback matrix:

| Failure | Permitted fallback |
|---|---|
| Dense query embedding/search | Sparse-only with explicit trace |
| Sparse search | Dense-only |
| Reranker | Stable RRF ordering |
| HyDE/rewrite/router | Original query and deterministic route |
| Synthesis | Evidence snippets or retryable error |
| OCR | Persist/retry/review; never fabricate coordinates |
| Authorization/policy | Deny, never fail open |

## 3. Security architecture

### Identity and authorization

- Verify issuer, audience, expiry and revocation policy.
- Resolve tenant/user/groups server-side.
- Store document ACL principals and sensitivity in the document ledger and vector payload.
- Apply ACL and active-version predicates inside every retrieval/list/view/delete operation.
- Signed source URLs require the same authorization and short expiry.

### Least privilege and network

- Replace `roles/datastore.owner` with narrowly scoped roles/custom permissions.
- Give service accounts access only to named secrets and required bucket prefixes/actions.
- Use authenticated TLS/private Qdrant; restrict network ingress/egress.
- Separate deploy, runtime, workflow and break-glass identities.
- Add CMEK/data-residency controls where tenant policy requires.

### Untrusted content and prompt injection

- Treat document text, OCR, metadata, filename, history and tool/model output as data.
- Use strict structured messages and delimiters, but do not rely on delimiters alone.
- Scan/classify suspicious instructions during ingestion and before synthesis.
- Do not expose tools, hidden context, unrelated documents or administrative actions to evidence-controlled prompts.
- Validate model output against authorized evidence and policy.
- Red-team direct, indirect, multilingual, encoded and image-based injection.

### Privacy and data lifecycle

- Classify PII/sensitivity at upload/ingestion.
- Record legal basis/tenant policy, region, retention and deletion deadline.
- Redact or tokenize where policy requires; preserve controlled original evidence separately.
- Audit views, queries, exports, ACL changes, reprocessing and deletion.
- Verify deletion across GCS versions, OCR artifacts, vector points, session history, caches, logs and backups according to policy.

### Secure delivery

- Secret scan, SAST, dependency license/vulnerability review, IaC scan and DAST.
- Generate SBOM and provenance; sign images and deploy by digest.
- Block critical/high exploitable findings unless explicitly risk-accepted with expiry.

## 4. Cost governance

### Cost ledger

Every stage emits:

- tenant and document/query ID in privacy-safe form;
- provider SKU/model/version/region;
- tokens, characters, images/pages, pixels, embeddings, reranked documents;
- cache hit/miss and retry count;
- estimated cost at request time and reconciled billed cost later.

### Controls

- Per-tenant monthly/daily budgets and anomaly detection.
- Admission control before expensive work.
- Distributed token bucket for queries, OCR pages, embedding tokens and reranker candidates.
- Concurrency caps aligned to provider quota.
- Budget-aware route: baseline retrieval before HyDE/decomposition/rerank.
- No hard “kill switch” that reports success while leaving another subscription/trigger consuming work.

### Optimization order

1. Eliminate duplicate work through deterministic IDs and content hashes.
2. Select cheap/native parser lane before OCR/VLM.
3. Batch embeddings/upserts and cache unchanged pages.
4. Gate query rewrite/HyDE/decomposition/reranking.
5. Reduce retrieved/context candidates using measured thresholds.
6. Right-size compute and storage after workload evidence.
7. Consider self-hosting models only when volume makes operational cost worthwhile.

Every optimization is an ablation with quality, latency, reliability and cost reported together.

## 5. Runbooks required before GA

- OCR/Vertex/reranker quota or regional outage.
- Qdrant node/index failure and restore.
- Firestore/GCS/Pub/Sub degradation.
- DLQ growth and safe replay.
- Stalled/corrupt document and manual review.
- Bad embedding/parser/chunker/prompt/model release.
- Cross-tenant security incident and credential exposure.
- PII deletion/export request.
- Budget anomaly and controlled workload shedding.
- Full regional recovery and rollback.
