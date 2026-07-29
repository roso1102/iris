# Software Requirements Specification (SRS)
## NaturePivot-RAG — Multi-Tenant Spatial Document Q&A Platform

**Version:** 1.0
**Status:** Draft — derived from the Grand Unified Architecture Plan
**Owner:** NaturePivot Engineering

---

## 1. Introduction

### 1.1 Purpose
This document specifies the functional and non-functional requirements for NaturePivot-RAG, a SaaS platform that allows enterprise clients to upload documents and receive spatially-grounded, cited answers to natural-language questions about their content.

### 1.2 Scope
The system covers: document ingestion and parsing, vector storage and retrieval, LLM-based answer synthesis, multi-tenant authentication and data isolation, conversational memory, trial/freemium usage controls, and hosting/deployment across Vercel (frontend) and GCP (backend).

Out of scope for MVP: GPU-based self-hosted inference (designed for, not required), advanced analytics dashboards, and non-PDF document formats (e.g., native DOCX, HTML) unless explicitly added later.

### 1.3 Definitions

| Term | Meaning |
|---|---|
| Tenant | A client enterprise account; the unit of data isolation |
| Bbox | Bounding box — pixel/coordinate location of content on a page |
| RAG | Retrieval-Augmented Generation |
| DLQ | Dead-Letter Queue |
| MVP | Minimum Viable Product — defined boundary in `ACTIONPLAN.md` Phase 5.0 |
| JWT | JSON Web Token, used for authenticated session claims |

### 1.4 Constraints Provided by the Business

1. Available infrastructure budget: **$300 GCP promotional credit**.
2. **No GPU quota** currently available on GCP; system must run entirely on CPU/serverless/API endpoints at launch.
3. An existing custom domain is hosted on **Vercel**.
4. Authentication-based access control, secure multi-tenant isolation, and session isolation are **non-negotiable**.

---

## 2. Overall Description

### 2.1 Product Perspective
IRIS is a new, cloud-native SaaS product. The frontend is a Next.js application deployed on Vercel; the backend is a set of independently-scaling Cloud Run services on GCP, backed by a vector database (Qdrant), a document store (GCS), and an operational database (Firestore).

### 2.2 User Classes

| User Class | Description | Key Needs |
|---|---|---|
| **Client Admin** | The primary account holder for an enterprise tenant | Manage users, view usage, manage documents |
| **Client Member** | An end user within a tenant, asking questions | Fast, accurate, cited answers |
| **Trial User** | A prospect testing the product before purchase | Free, capped access without needing an invite |
| **Platform Operator (Internal)** | IRIS staff | Monitor cost, security, and system health |

### 2.3 Operating Environment
- Frontend: Vercel Edge Network (global CDN), Next.js runtime.
- Backend: Google Cloud Platform, primarily `us-central1` (or nearest low-cost region), Cloud Run (Linux containers).
- Client access: modern web browsers over HTTPS.

### 2.4 Assumptions and Dependencies
- Google Cloud APIs (Vertex AI, Cloud Run, Firestore, GCS, Pub/Sub) remain available and priced as documented at plan time.
- Docling remains MIT-licensed and CPU-compatible.
- Cohere Rerank v3.5 is deprecating (July–Aug 2026); if used, must default to `rerank-4-fast` or the Vertex AI Ranking API instead.
- Marker (an alternative OCR/parsing library) must **not** be used due to its Open-RAIL-M commercial licensing trap above $2M revenue.

---

## 3. Functional Requirements

### FR-1: Document Ingestion
- FR-1.1: The system SHALL accept PDF uploads (scanned or digital) via an authenticated API endpoint.
- FR-1.2: The system SHALL reject files exceeding a configurable page/size limit (default: 500 pages) before queuing them for processing.
- FR-1.3: The system SHALL parse uploaded documents using Docling to extract text, tables, and figures with bounding-box coordinates.
- FR-1.4: The system SHALL route cropped table/figure regions to a Vision-Language Model (Gemini via Vertex AI) for content extraction.
- FR-1.5: The system SHALL chunk parsed content, generate embeddings, and store both content and bbox metadata in the vector database, tagged with the uploading tenant's `tenant_id`.
- FR-1.6: Failed ingestion jobs SHALL be retried up to 3 times, then routed to a Dead-Letter Queue for manual review — never retried indefinitely.

### FR-2: Retrieval & Question Answering
- FR-2.1: The system SHALL accept a natural-language question from an authenticated user, scoped to their tenant.
- FR-2.2: The system SHALL retrieve the most relevant document chunks using hybrid (semantic + keyword) search, filtered strictly to the requesting user's `tenant_id`.
- FR-2.3: The system SHALL rerank retrieved candidates before synthesis (via Vertex AI Ranking API or an equivalent non-deprecated reranker).
- FR-2.4: The system SHALL synthesize a final answer using an LLM (Gemini Flash/Flash-Lite), returning structured output that includes citation references mapped to source bbox locations.
- FR-2.5: The frontend SHALL render citations as clickable highlights that navigate to the exact page/location referenced.

### FR-3: Authentication & Authorization
- FR-3.1: The system SHALL require authentication (Firebase Authentication) for all document upload and query operations.
- FR-3.2: Every issued session token SHALL carry a server-set `tenant_id` and `role` claim; these claims SHALL NOT be client-writable.
- FR-3.3: The system SHALL support at least two roles per tenant: Admin and Member.

### FR-4: Multi-Tenant Data Isolation
- FR-4.1: All object storage SHALL be tenant-prefixed, with IAM conditions preventing cross-tenant access at the storage layer.
- FR-4.2: All vector database queries SHALL have their tenant filter enforced/rewritten server-side from the JWT claim, not solely from client-supplied request parameters.
- FR-4.3: All conversational state SHALL be stored under a tenant-scoped path and protected by security rules validating the requester's `tenant_id` claim on every read/write.
- FR-4.4: No API response SHALL ever return data belonging to a `tenant_id` other than the requester's.

### FR-5: Conversational Memory
- FR-5.1: The system SHALL persist chat history per session, scoped to tenant and session ID.
- FR-5.2: The system SHALL support follow-up questions by rewriting queries using prior conversational context.

### FR-6: Trial & Freemium Controls
- FR-6.1: The system SHALL support a trial tier with capped usage (pages ingested, queries per period, or credit balance).
- FR-6.2: The system SHALL reject requests exceeding trial caps with a clear, actionable error (HTTP 429), never a silent failure or unbounded charge.
- FR-6.3: Trial tenants SHALL be isolated using the exact same mechanisms as paying tenants (no shared trial pool).

### FR-7: Cost & Operational Safety
- FR-7.1: The system SHALL enforce a configurable daily spend cap; exceeding it SHALL automatically disable further ingestion compute (`max-instances=0`) until manually reset.
- FR-7.2: The system SHALL rate-limit upload endpoints (default: 10 requests/minute/IP) at the edge layer.
- FR-7.3: The system SHALL log and alert on billing anomalies via GCP Billing Alerts.

### FR-8: GPU/Model Provider Abstraction
- FR-8.1: All model inference calls (embedding, OCR/VLM extraction, synthesis) SHALL be made through a `ModelProvider` interface, not direct provider SDK calls scattered through the codebase.
- FR-8.2: The active backend implementation SHALL be selected via environment configuration (e.g., `MODEL_BACKEND=vertex` vs `MODEL_BACKEND=self_hosted_gpu`), stored in Secret Manager.
- FR-8.3: Switching backends SHALL require no changes to database schema, frontend code, or API contracts.

### FR-9: Hosting
- FR-9.1: The frontend SHALL be deployed on Vercel, using the existing custom domain.
- FR-9.2: The frontend SHALL communicate with the backend exclusively via authenticated HTTPS calls to the GCP-hosted Retrieval API.

### FR-10: Advanced Retrieval Intelligence

**Rephraser & Hypothesis Generation (HyDE)**
- FR-10.1: The system SHALL support generating a hypothetical answer and/or alternate phrasings for a user query, and embedding these for retrieval in place of (or alongside) the raw query, to improve recall on short/ambiguous questions.
- FR-10.2: If hypothesis generation fails or exceeds its latency budget, the system SHALL fall back to raw-query embedding without failing the request.

**SLM-Based Query Rewrite**
- FR-10.3: The system SHALL rewrite follow-up questions into self-contained queries using prior conversational turns, via a dedicated low-cost/low-latency model tier, before retrieval.

**Citation & Bbox Management**
- FR-10.4: Every citation returned to a user SHALL be validated against the actual retrieved chunk set before being returned; citations that do not map to a real, retrieved `chunk_id` SHALL be rejected, never surfaced.
- FR-10.5: Overlapping or adjacent bounding boxes on the same page SHALL be merged into a single clean highlight rather than rendered as stacked duplicates.
- FR-10.6: Citations spanning multiple pages SHALL render correctly on each relevant page.
- FR-10.7: When a document is re-ingested/updated, prior citations referencing the earlier version SHALL remain valid and correctly versioned, never silently broken or misattributed to the new version.

**Citation Map & Graph Node Network**
- FR-10.8: The system SHALL extract entities (e.g., sections, clauses, named parties, dates) and relationships (e.g., amends, references, supersedes, defines) from ingested documents and represent them as a graph of nodes and edges.
- FR-10.9: Every graph edge SHALL be traceable back to a validated citation (per FR-10.4) — the graph SHALL NOT contain relationships that are not backed by a real source chunk.
- FR-10.10: Entities referenced across multiple documents SHALL resolve to a single graph node (entity resolution/deduplication), not duplicate nodes per mention.

**Graph Query & Semantic Relationships**
- FR-10.11: The retrieval pipeline SHALL support expanding an initial vector-search result set by traversing graph relationship edges (1–2 hops) to surface related clauses/documents that pure semantic search would miss.
- FR-10.12: When a graph-expanded result contributes to an answer, the response SHALL explain the relationship path (e.g., "amended by Section 4 of Notification X"), not just the content.
- FR-10.13: Graph expansion SHALL be toggleable per query for cost control and evaluation purposes.

**Mixture of Agents (MoA)**
- FR-10.14: The system SHALL support an opt-in "high-assurance" synthesis mode using multiple specialized agent passes (e.g., extraction, interpretation, verification) whose outputs are reconciled by an aggregation step.
- FR-10.15: MoA mode SHALL NOT be invoked by default for standard queries; it SHALL require explicit user selection or a defined complexity-triggered heuristic.
- FR-10.16: Disagreement between agent outputs SHALL be surfaced to the user or logged, not silently resolved by picking one output arbitrarily.
- FR-10.17: MoA mode SHALL be subject to a hard per-query cost ceiling, enforced through the same billing-safety mechanism as FR-7.1.

---

## 4. Non-Functional Requirements

### NFR-1: Performance
- Search/chat responses SHALL return within **2 seconds** end-to-end under normal load (excluding first-call cold starts).
- Document ingestion for a typical 50-page document SHALL complete within **2 minutes**.

### NFR-2: Scalability
- The Retrieval API and Ingestion Worker SHALL scale independently and automatically (Cloud Run autoscaling), supporting at minimum 20 concurrent tenants without manual intervention.

### NFR-3: Availability
- Target uptime for MVP: **99% monthly** (allowing for scale-to-zero cold starts, which are acceptable and expected).
- Post-MVP (Phase 11.0): target **99.9%** with multi-region redundancy.

### NFR-4: Security
- All data in transit SHALL be encrypted via HTTPS/TLS.
- All data at rest (GCS, Qdrant, Firestore) SHALL use provider-managed encryption at minimum.
- No public, unauthenticated access SHALL exist to Qdrant or Firestore (VPC / Private Service Connect boundary required).
- Signed URLs for document access SHALL expire within 15 minutes.

### NFR-5: Cost Efficiency
- Idle-period infrastructure cost SHALL approach $0 (serverless scale-to-zero requirement).
- The system SHALL be operable within the $300 starting credit for a minimum of 3 months of active development and testing.

### NFR-6: Maintainability
- All model-provider-specific code SHALL be isolated behind the `ModelProvider` interface (see FR-8).
- Infrastructure SHALL be defined as code (Terraform or equivalent) to enable reproducible environments.

### NFR-7: Portability / Vendor Risk
- Licensing SHALL be reviewed for every third-party component before adoption (e.g., Marker's Open-RAIL-M revenue trigger must be avoided; Docling's MIT license is acceptable).

### NFR-8: Observability
- All ingestion failures SHALL be visible in a Dead-Letter Queue with enough metadata to diagnose the failure without re-running the job.
- Billing and usage anomalies SHALL trigger alerts, not silent accrual.

---

## 5. Data Requirements

### 5.1 Core Entities

| Entity | Store | Key Fields |
|---|---|---|
| Tenant | Firestore / IAM | `tenant_id`, name, plan tier, created_at |
| User | Firebase Auth + Firestore | `user_id`, `tenant_id`, `role`, email |
| Document | GCS + Firestore metadata | `doc_id`, `tenant_id`, filename, page_count, status |
| Chunk (vector point) | Qdrant | `chunk_id`, `tenant_id`, `doc_id`, embedding, bbox, page_number, text |
| Session | Firestore | `session_id`, `tenant_id`, `user_id`, chat history |
| Usage Quota | Firestore | `tenant_id`/`trial_id`, pages_ingested, queries_used, credit_balance, period_reset_at |

### 5.2 Data Isolation Rule (applies to every entity above)
Every read or write MUST be scoped by `tenant_id`, validated against the requester's JWT claim — never trusted from client-supplied input alone.

---

## 6. External Interface Requirements

### 6.1 APIs
- `POST /documents/upload` — authenticated, tenant-scoped, triggers ingestion pipeline.
- `POST /query` — authenticated, tenant-scoped, returns synthesized answer + citations.
- `GET /documents/{doc_id}/view-url` — returns a short-lived signed GCS URL.
- `GET /usage` — returns current usage/quota status for the caller's tenant.

### 6.2 Third-Party Services
Google Cloud Run, Google Cloud Storage, Google Pub/Sub, Google Firestore, Firebase Authentication, Vertex AI (Gemini models, Ranking API), Qdrant (self-hosted then Qdrant Cloud), Vercel, Docling (library, not a hosted service).

Graph storage for FR-10.8–10.13 SHALL start as a lightweight embedded structure (Firestore records or a serialized graph object in GCS, loaded in-memory by the Retrieval API) rather than a dedicated managed graph database, to avoid adding new fixed infrastructure cost during MVP/early growth. A dedicated graph database (e.g., Neo4j AuraDB) MAY be introduced later if graph size/query complexity exceeds what the embedded approach can serve within NFR-1 latency targets — this is a Phase 16.0 (Enterprise Scale Hardening) consideration, not an MVP one.

---

## 7. Acceptance Criteria Summary

A build is considered MVP-acceptable when:
1. Two distinct test tenants can each upload documents and query them, and neither can access the other's data under any tested condition (see `ACTIONPLAN.md` Phase 4.0 benchmarks).
2. A billing spend cap demonstrably halts ingestion compute when breached in a controlled test.
3. End-to-end query latency meets NFR-1 under a defined load test.
4. The frontend, hosted on the existing Vercel domain, successfully authenticates, queries, and renders citation highlights against the GCP backend.

Detailed phase-by-phase testing and benchmarks are defined in `ACTIONPLAN.md`.
