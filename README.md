# IRIS

**A secure, multi-tenant, spatially-grounded document Q&A platform, built serverless-first on Google Cloud Platform.**

IRIS lets enterprise clients upload dense documents (legal filings, government gazettes, scanned reports) and ask natural-language questions about them. Every answer is grounded in a **pixel-accurate citation** — a clickable highlight that jumps straight to the exact location on the exact page the answer came from.

This repository/architecture is the result of synthesizing two independent architecture proposals (`GCP_PLAN.md` and `GCP_ALT_GEM_PLAN.md`) into one unified, execution-ready plan. See `SRS.md` for the full requirements spec and `ACTIONPLAN.md` for the phase-by-phase build plan.

---

## 1. What This System Does

1. A client uploads a PDF (scanned or digital).
2. The system reads the document's layout — text, tables, figures — and records **exactly where** every piece of content sits on the pa
ge (bounding-box coordinates).
3. The content is chunked, embedded, and stored in a vector database, tagged to that client only.
4. When a user asks a question, the system retrieves the most relevant chunks, reranks them, and asks an LLM to synthesize a grounded answer with citations.
5. The frontend renders the answer with a highlight overlay pointing to the exact source location.

### Ingestion Pipeline
```
Upload PDF to GCS
  │
  └─► Pub/Sub → Ingestion Worker (Cloud Run)
          │
          ├─ Docling Layout Analysis (extract text blocks + exact bbox coordinates per element)
          │
          ├─ Page-Wise VLM Router (runs per page, per element):
          │     ┌──────────────────────────────────────────────────────────┐
          │     │ Docling signals per page:                                │
          │     │  • Char count ≥ 150 + element type = Text               │
          │     │      → Docling text used directly  (zero API cost)       │
          │     │  • Element type = Table detected                         │
          │     │      → Gemini Vision on cropped table bbox               │
          │     │  • Element type = Picture/Figure detected                │
          │     │      → Gemini Vision on cropped figure bbox              │
          │     │  • Char count < 150 (scanned / image-only page)         │
          │     │      → Gemini Vision on full page crop                   │
          │     └──────────────────────────────────────────────────────────┘
          │
          ├─ Chunk + Embed via ModelProvider.embed()
          │     └─ Vertex AI text-embedding-004 (768-d, multilingual)
          │
          └─ Write to Qdrant (vectors + bbox + tenant_id + page metadata)
                                    │
                                    └──► Entity extraction → Knowledge Graph (Phase 10.0+)
```

### Retrieval Pipeline
```
User submits question
  │
  ├─ [Standard Mode]
  │     Embed query (Vertex AI 768-d)
  │       → Qdrant Dense Search (cosine)
  │       → Qdrant BM25 Full-Text Search
  │       → RRF Fusion  (merge both rank lists into one)
  │       → Diversity / Dedup Pass  (0.5× penalty per repeat source_file in top-K)
  │       → Gemini Flash Synthesis
  │
  └─ [Deep Search Mode  — user-toggled "Deep Search" option]
        SLM Query Rewrite (resolve follow-ups from chat history)
          → HyDE  (generate hypothetical answer chunk for richer query vector)
          → Qdrant Dense + BM25 Search
          → RRF Fusion
          → Diversity / Dedup Pass
          → Vertex AI Ranking API  (semantic cross-encoder rerank)
          → [optional] Knowledge Graph Expansion
          → Gemini Flash Synthesis

  Both modes → Citation Registry validation → Answer + bbox → UI highlight
```

> **Standard vs Deep Search:** Standard mode is fast, free, and suitable for direct factual queries. Deep Search is user-toggled — it adds SLM query rewriting, HyDE vector enrichment, and the Vertex AI semantic cross-encoder reranker for ambiguous or complex multi-hop questions. HyDE, graph expansion, and Mixture-of-Agents are advanced-tier capabilities (see `ACTIONPLAN.md` Phases 8.0–14.0), layered on top of the MVP pipeline (Phases 0.0–5.0) — not required for initial launch.

---

## 2. Core Design Principles

| Principle | What It Means Here |
|---|---|
| **Serverless-first** | Every compute component scales to zero. No idle billing. |
| **CPU-only today, GPU-ready tomorrow** | No GCP GPU quota is required to launch. A `ModelProvider` abstraction lets us swap to self-hosted GPU inference later with a config change, not a rewrite. |
| **Security by construction, not by convention** | Tenant isolation is enforced at the database engine level (JWT-driven filter rewrite), not just trusted to application code. |
| **Cost-capped by default** | A billing circuit breaker and ingestion Dead-Letter Queue exist *before* any other feature is built, protecting the $300 starting credit from runaway spend. |
| **Decoupled ingestion vs. retrieval** | Slow document parsing never blocks fast chat responses — they are two independently-scaling services connected by a queue. |

---

## 3. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Next.js on **Vercel** | Client-facing chat UI + bounding-box highlight overlay |
| API / Compute | **Google Cloud Run** (Ingestion Worker + Retrieval API) | Scales to zero; hosts all backend logic |
| Messaging | **Google Pub/Sub** | Decouples ingestion from retrieval; drives the Dead-Letter Queue |
| Document Parsing | **Docling** (MIT license, open-source) | Layout-aware extraction — text, tables, figures + per-element bbox coordinates |
| Page-Wise VLM Router | **4-signal composite decision tree** (Docling element labels + valid word ratio + text area coverage + OCR confidence) | Routes each page to the cheapest correct processor — zero API cost on clean text (see §1 flow) |
| Table / Figure / Scanned / Garbled Pages | **Gemini Vision (Vertex AI)** on cropped bbox regions or full-page crop | Called only when composite router signals a Table, Figure, low-coverage, or low-quality-OCR page — never on clean text |
| Embeddings | **Vertex AI `text-embedding-004`** (768-d, multilingual) | Unified English + Hindi/Devanagari vector space; no local ONNX model required |
| LLM Synthesis | **Gemini Flash (Vertex AI)** | Generates the final grounded answer with structured citations |
| Retrieval — Fusion | **Reciprocal Rank Fusion (RRF)** | Merges BM25 and dense cosine rank lists into one coherent ordered list |
| Retrieval — Diversity | **Custom diversity/dedup pass** | Applies 0.5× penalty to repeated `source_file` hits after RRF, preventing source over-representation |
| Retrieval — Semantic Rerank | **Vertex AI Ranking API** *(Deep Search mode only)* | Cross-encoder reranks fused + diversified list by actual query-chunk relevance |
| Query Rewrite / HyDE | **Gemini Flash-Lite via `ModelProvider`** *(Deep Search mode only)* | Resolves follow-up questions and generates hypothetical answer chunks to enrich query vectors |
| Vector Database | **Qdrant** (self-hosted on GCE VM → Qdrant Cloud at scale) | Hybrid BM25 + cosine search, tenant-isolated via `is_tenant=True` |
| Conversational State | **Google Firestore** | Chat history, session state, usage quotas |
| Authentication | **Firebase Authentication** | Login, JWT issuance with `tenant_id` / `role` claims |
| Object Storage | **Google Cloud Storage (GCS)** | Raw uploaded documents, tenant-prefixed buckets |
| Secrets | **GCP Secret Manager** | API keys, model backend config |
| Edge / Rate Limiting | **Cloud Armor / API Gateway** | Upload rate limiting, trial quota enforcement |
| Citation Registry | Custom service (Retrieval API + Firestore) | Validates every citation against real retrieved chunks; manages bbox merging, multi-page spans, and document versioning |
| Knowledge Graph | Firestore/GCS-backed embedded graph (upgradeable to a managed graph DB at scale) | Represents cross-document relationships (amends/references/supersedes) for graph-aware retrieval |
| Mixture of Agents | Multiple `ModelProvider.synthesize()` passes + aggregator | Opt-in high-assurance synthesis mode for complex queries |

---

## 4. High-Level Architecture

```
┌────────────┐        HTTPS         ┌─────────────────────────┐
│  Frontend  │ ───────────────────► │   API Gateway / Auth      │
│  (Vercel)  │ ◄─────────────────── │   (JWT validation)         │
└────────────┘                      └─────────────┬────────────┘
                                                    │
                       ┌────────────────────────────┼───────────────────────────┐
                       ▼                                                        ▼
             ┌───────────────────┐                                  ┌────────────────────┐
             │  Ingestion Worker  │──Pub/Sub──►  DLQ (on failure)    │   Retrieval API      │
             │  (Cloud Run)        │                                  │   (Cloud Run)         │
             │  Docling + Gemini   │                                  │   Qdrant search +     │
             │  VLM extraction     │                                  │   Gemini synthesis     │
             └─────────┬───────────┘                                  └──────────┬────────────┘
                       │                                                          │
                       ▼                                                          ▼
             ┌───────────────────┐                                  ┌────────────────────┐
             │  GCS (raw files,   │                                  │  Qdrant (vectors,    │
             │  tenant-prefixed)  │                                  │  tenant-isolated)     │
             └─────────────────────┘                                  └────────────────────┘
                                                                                  │
                                                                                  ▼
                                                                        ┌────────────────────┐
                                                                        │  Firestore           │
                                                                        │  (sessions, quotas)   │
                                                                        └────────────────────┘
```

---

## 5. Getting Started (Once Implementation Begins)

> This section is a placeholder to be filled in as Phase 0.0 completes. Structure below shows the intended shape.

```bash
# Clone
git clone <repo-url>
cd iris

# Backend (Ingestion Worker + Retrieval API)
cd services/ingestion-worker && pip install -r requirements.txt --break-system-packages
cd ../retrieval_api && pip install -r requirements.txt --break-system-packages

# Frontend
cd ../../frontend && npm install

# Environment
cp .env.example .env   # fill in GCP project ID, Firebase config, Qdrant endpoint

# Local run
docker compose up      # spins up local Qdrant + emulated Firestore for dev
```

---

## 6. Repository Structure (Target)

```
iris/
├── services/
│   ├── ingestion-worker/     # Cloud Run service: Docling parsing, chunking, embedding, chunk QA view
│   └── retrieval_api/         # Cloud Run service: search, rerank, synthesis, citation registry
├── frontend/                 # Next.js app (deployed on Vercel), incl. PDF.js citation side panel
├── infra/                    # Terraform / deployment scripts (IAM, Pub/Sub, budgets)
├── docs/
│   ├── SRS.md
│   ├── ACTIONPLAN.md
│   └── IRIS_Grand_Architecture_Plan.md
└── README.md
```

### Containerization approach
We containerize **per service, not per development phase** — one Docker image for `ingestion-worker`, one for `retrieval_api`. Each completed phase is git-tagged (e.g., `v9.0-citation-registry`) and deployed to a staging Cloud Run revision for benchmark testing before merging to production, giving phase-level checkpoints without fragmenting the system into dozens of containers. Full rationale in `ACTIONPLAN.md` → "Deployment & Containerization Strategy."

---

## 7. Key Documents

| Document | Purpose |
|---|---|
| `SRS.md` | Full Software Requirements Specification — functional, non-functional, security, and data requirements |
| `ACTIONPLAN.md` | Phase-by-phase build plan (Phase 0.0 → 11.0) with benchmarks and test criteria for each phase |
| `IRIS_Grand_Architecture_Plan.md` | The original deep-dive architecture rationale, cost analysis, and hosting strategy |

---

## 8. Guiding Constraints (Do Not Violate)

- ❌ No GPU-dependent code path may be required for the system to function at MVP.
- ❌ No cross-tenant data access, ever — enforced at the database layer, not just the API layer.
- ❌ No unbounded billing risk — every ingestion path must be protected by the Dead-Letter Queue and daily spend cap.
- ✅ Every model call (embedding, OCR, synthesis) must go through the `ModelProvider` interface.
- ✅ Frontend stays on Vercel; backend stays on GCP, connected via authenticated HTTPS.
