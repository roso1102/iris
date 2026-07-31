# Active Context & Project State — IRIS

## Active Phase
- **Phase 0.0 & Phase 0.1 Setup** (Foundations, Safety Nets & Model Provider Abstraction)

## Binding Architectural Decisions

1. **Model Abstraction:** All model calls (embedding, VLM extraction, synthesis) go through the `ModelProvider` abstract class. Active backend controlled by `MODEL_BACKEND` env var (`vertex` default).
2. **Embeddings:** Vertex AI `text-embedding-004` (3072 dimensions, multilingual).
3. **Ingestion & VLM Router:**
   - Docling extracts text + normalized bounding boxes `[left, top, right, bottom]`.
   - Router evaluates Docling output per element:
     - Clean text (≥150 chars, Text element): Docling text directly ($0 cost).
     - Table element: Gemini Vision on cropped table bbox image.
     - Figure/Picture element: Gemini Vision on cropped figure bbox image.
     - Scanned / low-text page (<150 chars): Gemini Vision on full-page crop.
   - RapidOCR removed; Gemini Vision handles KrutiDev / legacy Hindi font encodings via pixel reading.
4. **Retrieval Pipeline (Strict Sequential Order):**
   - Hybrid Search (Qdrant Cosine + BM25 full-text parallel search).
   - Reciprocal Rank Fusion (RRF) to merge rank lists.
   - Diversity / Dedup Pass (0.5× penalty to recurring `source_file` hits in top-K).
   - [Deep Search Mode only] Vertex AI Ranking API cross-encoder rerank + SLM query rewrite + HyDE.
5. **Sessions & Memory:**
   - Workspace sessions stored in Firestore `/tenants/{tenant_id}/sessions/{session_id}`.
   - Deep Search mode fetches a **sliding window** of the last N=6 messages from Firestore.
   - Deletion of documents/sessions triggers a clean cascading purge across Firestore, GCS, and Qdrant.

## Current Milestone & Next Steps
- [x] Initial specification and roadmap committed & pushed to GitHub.
- [x] Auto-loaded `.agents/AGENTS.md` and `CONTEXT.md` initialized.
- [ ] Implement `ModelProvider` abstract interface and `VertexAIProvider` implementation (Phase 0.1).
