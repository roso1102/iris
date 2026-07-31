# CONTEXT.md — Living Project Context for IRIS

<!-- STRICT TEMPLATE v1 — This file has a fixed structure. -->
<!-- RULES FOR ALL AGENTS (Command Code, Antigravity, any other): -->
<!-- 1. Section headers (## 1. … ## 6.) are FIXED. Never rename, reorder, merge, or add sections. -->
<!-- 2. Sections 1 and 3 are FROZEN (derived from README.md / SRS.md / ACTIONPLAN.md). Only the user may authorize changes. -->
<!-- 3. Sections 2, 5, 6 are updated only when reality changes (work done, new gotcha, new open question). -->
<!-- 4. Section 4 (Session Log) is append-only. Add ONE bullet per session at the bottom. Never edit or delete old bullets. -->
<!-- 5. Keep this file under ~160 lines. Trim only the oldest Session Log bullets if it grows. -->
<!-- 6. Do not reformat the file (headings, bullets, bold markers, the divider). -->
<!-- If you believe the template itself must change, propose it to the user — do not change it unilaterally. -->

---

## 1. What IRIS Is

IRIS is a secure, multi-tenant, spatially-grounded document Q&A platform on GCP. Clients upload dense PDFs (legal filings, gazettes, scanned reports) and ask natural-language questions. Answers carry **pixel-accurate citations** — clickable highlights mapped to exact bounding boxes on source pages. Built serverless-first, CPU-only, cost-capped by a $300 GCP credit. Frontend on Vercel (Next.js); backend on Cloud Run + Qdrant + Firestore + GCS + Pub/Sub + Vertex AI.

## 2. Current State

- **Phase:** 0.0 Foundations (not started — repo is docs-only)
- **Implemented:** nothing yet. Repo contains `README.md`, `SRS.md`, `ACTIONPLAN.md`, `.agents/AGENTS.md`, `COMMANDCODE.md`, and this file.
- **Next up:** Phase 0.0 — GCP project setup, billing budget + kill-switch (Billing Alert → Pub/Sub → Cloud Function setting `max-instances=0`), least-privilege IAM, VPC/Private Service Connect, Secret Manager, Firebase Auth, repo scaffolding + CI, base Terraform. Then Phase 0.1 — `ModelProvider` abstraction scaffold.

## 3. Key Decisions (frozen — do not violate)

- **Serverless-first:** every compute component scales to zero; no idle billing.
- **CPU-only for MVP:** no GPU quota available. All model calls go through a `ModelProvider` interface so GPU swap-in later is a config change (`MODEL_BACKEND` env var), not a rewrite.
- **Tenant isolation at the engine level:** JWT `tenant_id` claim drives Qdrant filter rewriting server-side; never trust client-supplied tenant IDs. Firestore security rules enforce `request.auth.token.tenant_id == resource.data.tenant_id`.
- **Cost-capped by default:** billing circuit breaker + ingestion DLQ built in Phase 0.0, before any product code.
- **Page-wise VLM router:** Docling does layout extraction with bboxes; Gemini Vision is called ONLY for tables, figures, and low-text (<150 char) pages — never on clean text pages. Handles KrutiDev/DevLys legacy Hindi + scanned Devanagari without custom decoders.
- **Stack specifics:** Qdrant self-hosted on GCE VM (`is_tenant=True`, hybrid BM25 + cosine, RRF fusion, diversity/dedup pass); Vertex AI `text-embedding-004` (3072-d); Gemini Flash synthesis; Firestore for sessions/history/quotas; GCS tenant-prefixed buckets.
- **Two query modes:** Standard (fast/free) and user-toggled Deep Search (SLM rewrite + HyDE + Vertex AI Ranking rerank).
- **Licensing:** Docling (MIT) OK; **Marker is banned** (Open-RAIL-M revenue trap). Cohere Rerank v3.5 is deprecating — use `rerank-4-fast` or Vertex AI Ranking API.
- **Milestone checklist (working state, not a locked decision):**
  - [x] Initial specification and roadmap committed & pushed to GitHub.
  - [x] Auto-loaded `.agents/AGENTS.md` and `CONTEXT.md` initialized.
  - [ ] Implement `ModelProvider` abstract interface and `VertexAIProvider` implementation (Phase 0.1).

---

## 4. Session Log (append-only — one bullet per session)

<!-- Format: `- YYYY-MM-DD · tool · what was done | decisions made | next step` — max 3 lines per bullet -->

- 2026-07-31 · discussion · Set up shared-context files (`COMMANDCODE.md` → `CONTEXT.md` ← `AGENTS.md`). Updated `CONTEXT.md` with complete project state and rules structure. Next: decide whether to start Phase 0.0 GCP scaffolding.
- 2026-07-31 · Command Code · Verified the bridge end-to-end: `COMMANDCODE.md` (Command Code, auto-load) and `.agents/AGENTS.md` (Antigravity, auto-load) both resolve to `CONTEXT.md` as the single source of truth. Confirmed the other agent's rewrite of `CONTEXT.md` preserved all key decisions. Next: decide whether to start Phase 0.0 GCP scaffolding, or Phase 0.1 `ModelProvider` scaffold.
- 2026-07-31 · Antigravity · Created GCP service account `iris-backend-sa` (Application data). Identified roles needed: Vertex AI User, Storage Object Admin, Datastore User, Pub/Sub Editor. Next: proceed with Phase 0.1 ModelProvider scaffold.

---

## 5. Gotchas & Notes

- Service Account Creation: `iris-backend-sa` created under Application data. Granting project-level IAM roles (Vertex AI User, Storage Admin, Datastore User) requires `resourcemanager.projects.setIamPolicy` permission or can be assigned via GCP project IAM settings / local `gcloud auth application-default login`.
- Docling emits normalized `[left, top, right, bottom]` bbox per element — verify coordinate space against PDF.js rendering in Phase 5.0.
- Phase numbering in ACTIONPLAN has a known quirk: Phase 15.0 and 16.0 reuse task numbers (10.x / 11.x) — don't let that confuse references.
- Chunking target: ~512 tokens, sentence-boundary; VLM outputs become single chunks with the source element's bbox.
- Latency budgets that gate acceptance: `/search` < 500ms, `/query` < 2s, rewrite step < 300ms, HyDE < 400ms, graph traversal < 300ms.

## 6. Open Questions

- When to actually start Phase 0.0 (needs GCP account access + the $300 credit org).
- Trial/freemium credit model numbers (1 page ≈ 5 credits, 1 query ≈ 1 credit are placeholders).
- Whether Deep Search should be enabled at MVP or held for Phase 8.0+.
