# AGENTS.md — Instructions for AI Coding Agents (Auto-loaded)

## Shared Context & Working Agreement

Before starting work in this repository, read **`CONTEXT.md`** (or consult `README.md`, `SRS.md`, and `ACTIONPLAN.md`).

### Key Binding Decisions

- **Architecture:** IRIS is a serverless-first, multi-tenant document Q&A platform built on GCP (Cloud Run, GCS, Pub/Sub, Firestore, Vertex AI, Qdrant).
- **Model Interface:** All model calls (embedding, VLM/OCR, synthesis) MUST go through the `ModelProvider` abstraction (`MODEL_BACKEND` env config).
- **Embeddings:** Vertex AI `text-embedding-004` (768-d, multilingual).
- **Ingestion & Page Router:** Docling layout parsing + targeted Gemini Vision calls.
  - Text-rich pages (≥150 clean chars): Docling text directly (zero API cost).
  - Table / Figure elements: Gemini Vision on cropped element image.
  - Low-text / Scanned pages (<150 chars): Gemini Vision on full page crop.
  - RapidOCR is removed; pixel-based VLM handles KrutiDev/Devanagari text automatically.
- **Retrieval Pipeline (Sequential Order):**
  1. Hybrid Retrieve (Dense vector + BM25 full-text parallel search in Qdrant).
  2. Reciprocal Rank Fusion (RRF) to merge rank lists.
  3. Diversity / Dedup Pass (0.5× penalty for repeat `source_file` hits).
  4. (Deep Search Mode only) Vertex AI Ranking API cross-encoder rerank + SLM Query Rewrite + HyDE.
- **Sessions & Memory:** Named workspace sessions in Firestore (`/tenants/{tenant_id}/sessions/{session_id}`).
  - Deep Search rewriter uses a **sliding window** of the last N=6 messages from Firestore.
  - Deletions (`DELETE /documents/{id}` and `DELETE /sessions/{id}`) cascade across Firestore, GCS, and Qdrant.

### STRICT TEMPLATE RULES for CONTEXT.md (mandatory)

`CONTEXT.md` uses a numbered, frozen template. You MUST follow the rules embedded in its header comment block:
- **Section headers (## 1. … ## 6.) are FIXED.** Never rename, reorder, merge, or add sections.
- **Sections 1 and 3 are FROZEN** (derived from README/SRS/ACTIONPLAN). Only the user may authorize changes.
- **Section 4 (Session Log) is append-only:** add ONE bullet per session at the bottom, never edit or delete old bullets.
- **Do not reformat the file** (headings, bullets, bold markers, dividers, comment block).
- If you believe the template itself must change, propose it to the user — never change it unilaterally.

### Agent Workflow Discipline

- Update `CONTEXT.md` when completing key decisions or milestones — append to Section 4 (Session Log), 3 lines max.
- Do not alter `README.md`, `SRS.md`, or `ACTIONPLAN.md` core architecture without explicit user agreement.
