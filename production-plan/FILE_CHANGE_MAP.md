# Planned File and Module Change Map

This is a planning map, not a commitment to a big-bang directory rewrite. New modules land incrementally behind interfaces and flags. Existing behavior is removed only after migration and rollback windows pass.

## Current files to change

| Current path | Phase | Planned action |
|---|---:|---|
| `services/retrieval_api/app.py` | 0.1, 1.0, 9.0 | Fix uninitialized intent; enforce strict validation/ACLs; stop leaking exceptions; stream uploads; split the god module into routers/application services/repositories. |
| `services/common/retrieval/search.py` | 0.1, 7.0, 8.0 | Fix clocks; replace short-query HyDE predicate; add adaptive planner, independent fallback, validated routing, original-query HyDE leg, rerank/MMR and trace contracts. |
| `services/common/retrieval/models.py` | 1.0 | Replace loose `dict`/list request fields with strict versioned models and bounded validators. |
| `services/common/models/base.py` | 1.0 | Expand ports for structured OCR, strict route/rewrite/rerank results and provider telemetry. |
| `services/common/models/vertex.py` | 0.1, 1.0, 7.0–9.0 | Task-specific deadlines/retries/output limits; strict parsing; constrained HyDE; no plain-text OCR geometry; use real rerank scores; remove direct policy leakage. |
| `services/ingestion-worker/app.py` | 0.1, 3.0 | Await publish, initialize first, remove daemon summary, use durable stage handlers, validate event scope, remove direct SDK/model work and run under production server. |
| `services/common/ingestion/main.py` | 0.1, 3.0, 5.0 | Validate embedding cardinality/dimensions; accept versioned artifacts/stages; remove misleading precise fallback geometry. |
| `services/common/ingestion/parser.py` | 4.0–5.0 | Honor coordinate origin; implement/consume normalized parser adapter; become only the Docling adapter if Docling survives the bake-off. |
| `services/common/ingestion/vlm_router.py` | 4.0–5.0 | Replace per-element full-page OCR with one page extraction; route among native/managed/local lanes; emit structured span artifacts. |
| `services/common/ingestion/chunker.py` | 5.0 | Actual tokenizer, multilingual punctuation, layout/heading/table boundaries, parent-child IDs, exact span/polygon provenance. |
| `services/common/ingestion/cache.py` | 3.0, 5.0 | Replace fake doc-ID cache with content/stage/model-version cache and deletion-safe invalidation. |
| `services/common/ingestion/store.py` | 0.1, 6.0 | Typed missing-collection handling, tenant/ACL indexes, bounded retry/upsert, deterministic IDs, schema/alias lifecycle and health telemetry. |
| `services/common/retrieval/bm25.py` and Hindi helpers | 0.1, 6.0 | Fix known normalization errors; benchmark and replace English-only/manual sparse strategy. |
| `services/common/auth/rate_limit.py` | 10.0 | Replace per-instance fixed window with distributed token buckets and stage/provider quotas. |
| `services/common/auth/validation.py` | 0.1, 1.0 | Make all endpoints use strict ID/query/history/document validation consistently. |
| `infra/iam.tf` | 9.0 | Remove project-wide datastore owner and all-secret runtime permissions; add least-privilege identities. |
| `infra/gcs.tf` | 3.0, 9.0 | Quarantine/artifact/benchmark buckets, retention/version policy and scoped IAM. |
| `infra/pubsub.tf` | 3.0 | One delivery topology, stage/DLQ policies, service-agent IAM, replay and quota configuration. |
| `infra/qdrant.tf` | 6.0 | Replace single VM with supported HA topology/managed service, TLS/auth, snapshots, monitoring and restore controls. |
| `scripts/deploy.sh` | 3.0, 11.0 | Stop creating resources already owned by Terraform; eventually replace mutable shell deployment with digest-based promotion tooling. |
| `.github/workflows/ci.yml` | 0.0, 2.0, 9.0, 11.0 | Hermetic tests, benchmark schema/gates, security scans, SBOM/signing, provider schedules and progressive deployment. |
| `services/*/Dockerfile` | 0.0, 6.0, 11.0 | Locked dependencies, non-root runtime, health/startup configuration, production server and digest/provenance. |
| `tests/conftest.py` | 0.0 | Remove unconditional model download; separate hermetic and live-provider fixtures. |
| `BENCHMARK.md` | 0.0 | Retain as historical target document or add a pointer to the new canonical benchmark standard; do not overwrite measured history. |
| `ACTIONPLAN.md` | 0.0 | Retain as historical roadmap and point readers to `PRODUCTION_PLAN.md`; do not reuse old completion marks as evidence. |

## Proposed modules

Names may adjust to project packaging conventions, but boundaries are required.

```text
services/common/contracts/
  document.py          # DocumentVersion, page/stage state
  geometry.py          # PageGeometry, Polygon, transforms
  ocr.py               # OcrPage/OcrSpan
  retrieval.py         # Route/Rewrite/RetrievalTrace/Evidence
  conversation.py      # TurnState and concurrency version
  events.py            # versioned ingestion events

services/common/ports/
  ocr_provider.py
  layout_provider.py
  workflow_ledger.py
  object_store.py
  message_bus.py
  embedding_provider.py
  reranker.py
  vector_store.py

services/common/adapters/
  google_document_ai.py
  pymupdf_native.py
  docling_layout.py
  vertex_models.py
  qdrant.py
  firestore_ledger.py
  gcs.py
  pubsub.py

services/common/workflows/
  ingestion.py
  stages.py
  completion.py
  reconciliation.py
  deletion.py

services/common/query/
  planner.py
  followup.py
  hyde.py
  routing.py
  retrieval.py
  reranking.py
  context.py
  grounding.py

services/retrieval_api/routers/
services/retrieval_api/application/
services/retrieval_api/repositories/

tests/unit/
tests/component/
tests/contracts/
tests/provider/
tests/quality/
tests/security/
tests/load/
tests/chaos/
tests/datasets/manifests/
```

## Planned deletions after proof/migration

- Short-query-is-HyDE heuristic and dead cross-lingual branches.
- Plain-string page OCR as a spatial evidence path.
- Random chunk IDs.
- Daemon-thread summary generation.
- Document cache that ignores its SHA argument.
- Per-instance production rate limiter.
- Direct model SDK imports outside adapters.
- Duplicate Eventarc/push subscription creation.
- Mutable `latest` production deployments.
- Single-node unauthenticated Qdrant production topology.
- Docling in lanes where Phase 4.0 shows no measurable benefit.
- Dormant provider boilerplate with no owner or conformance tests.

Deletion happens only after the replacement is active, rollback evidence exists, and the retention window closes.
