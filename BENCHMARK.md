# IRIS Technical Benchmark Suite & Evaluation Framework

This document outlines the formal technical benchmarks, evaluation metrics, test criteria, and comparison baselines used to evaluate the IRIS document Q&A platform against standard baseline systems.

---

## 1. Retrieval Quality Metrics

The retrieval pipeline consists of Hybrid Search (dense cosine + BM25 keyword), Reciprocal Rank Fusion (RRF), a Diversity/Dedup pass, and optional Vertex AI Ranking API cross-encoder reranking (Deep Search mode).

### 1.1 Hit Rate / Recall@K
- **Definition:** Given a test query with a known correct source chunk, does that chunk appear in the top-$K$ retrieved results?
- **Measurement Methodology:** Curate a "golden dataset" of 30–50 ground-truth `(question, target_chunk_id, target_bbox)` tuples from benchmark documents. Evaluate retrieval across $K \in \{1, 3, 5, 10\}$.
- **Target:** $\text{Recall@5} \ge 0.85$

### 1.2 Mean Reciprocal Rank (MRR)
- **Definition:** Measures the average rank of the first relevant chunk returned: $\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$
- **Target:** $\text{MRR} \ge 0.75$ (Standard Mode), $\text{MRR} \ge 0.85$ (Deep Search Mode).

### 1.3 Precision@K
- **Definition:** Fraction of top-$K$ retrieved chunks that are relevant to the query: $\text{Precision@K} = \frac{|\text{Relevant Chunks in Top K}|}{K}$
- **Target:** $\text{Precision@5} \ge 0.70$

### 1.4 Hybrid Search Lift (Dense vs. BM25 vs. Hybrid + RRF)
- **Definition:** Direct A/B comparison across 3 retrieval paths on the same golden dataset:
  1. Dense vector search only (`text-embedding-004`, 768-d)
  2. Full-text BM25 search only
  3. Hybrid parallel search + RRF fusion + Diversity pass (IRIS baseline)
- **Target:** Hybrid + RRF must match or exceed single-modality recall@5 by $\ge 5\%$.

---

## 2. Answer Quality & Generation Metrics

Answer quality is evaluated using the open-source **RAGAS** (`ragas`) and **DeepEval** (`deepeval`) evaluation frameworks.

### 2.1 Faithfulness Score (Hallucination Detection)
- **Definition:** Measures whether every factual assertion made in the generated answer is directly supported by the retrieved context.
- **Evaluation:** Evaluated using an LLM-as-a-judge prompt to parse answer claims and verify against source context snippets.
- **Target:** $\text{Faithfulness} \ge 0.90$

### 2.2 Answer Relevancy
- **Definition:** Measures how directly the synthesized answer addresses the user's explicit question without off-topic additions.
- **Target:** $\text{Answer Relevancy} \ge 0.85$

### 2.3 Context Recall
- **Definition:** Measures whether all required information needed to answer the question was successfully retrieved in the context block.
- **Target:** $\text{Context Recall} \ge 0.80$

### 2.4 Citation Accuracy & Bbox Grounding (IRIS Hard Gate)
- **Definition:** Validates that 100% of returned citations map to a valid, retrieved `chunk_id` and non-overlapping bounding-box location.
- **Target:** **100%** (0% hallucinated citations; any ungrounded citation fails the test suite).

---

## 3. Ingestion & VLM Router Metrics

### 3.1 Page-Wise VLM Router Accuracy
- **Definition:** Evaluates the classification accuracy of the page router (Docling layout signals + char count threshold) against manually labeled test pages (`Text`, `Table`, `Figure`, `Scanned`).
- **Target:** $\ge 95\%$ correct routing decisions.

### 3.2 Table & Figure Structure Extraction Accuracy
- **Definition:** Evaluates cell-level accuracy of Gemini Vision Markdown extraction on cropped table image regions compared to ground-truth CSV/Markdown data.
- **Target:** $\ge 90\%$ cell-level accuracy.

### 3.3 Devanagari / Legacy Hindi Font OCR Accuracy (Word Error Rate)
- **Definition:** Evaluates text extraction quality on legacy font encodings (KrutiDev / DevLys) and scanned Devanagari pages without custom font decoders.
- **Metric:** Word Error Rate: $\text{WER} = \frac{S + D + I}{N}$ (Substitutions, Deletions, Insertions over Total Words).
- **Target:** $\text{WER} \le 10\%$ on scanned Devanagari pages.

---

## 4. System Performance & Cost Benchmarks

### 4.1 End-to-End Response Latency (P50 / P95 / P99)
- **Standard Mode Query (`/query`):** P95 $< 2.0\text{ seconds}$ (per SRS NFR-1)
- **Vector Search (`/search`):** P95 $< 500\text{ ms}$
- **Deep Search Mode Query:** P95 $< 4.0\text{ seconds}$ (includes SLM rewrite + HyDE + cross-encoder rerank)

### 4.2 Ingestion Throughput
- **Clean Text Pages (Docling Direct):** $\ge 10\text{ pages/minute}$
- **VLM Pages (Gemini Vision Cropped):** $\ge 3\text{ pages/minute}$
- **50-Page Sample Document:** $< 2\text{ minutes}$ total processing time.

### 4.3 Cost Efficiency Metrics
- **Cost per Standard Query:** $< \$0.01$
- **Cost per Ingested Page:** $< \$0.05$ average
- **Idle System Cost:** $\$0.00/\text{hr}$ (Scales to zero on Cloud Run)

---

## 5. System Benchmark Comparison Baseline

| Metric / Benchmark | Legacy / Standard Local RAG | IRIS Platform Target | Verification Tool / Method |
|---|---|---|---|
| **Retrieval Recall@5** | ~65–70% (Dense only) | **$\ge 85\%$** | Golden Dataset / pytest |
| **Mean Reciprocal Rank (MRR)** | ~0.55 | **$\ge 0.75$ (Std) / $\ge 0.85$ (Deep)** | Custom Retrieval Eval Suite |
| **Faithfulness Score** | ~0.75 | **$\ge 0.90$** | RAGAS Framework |
| **Hindi / Devanagari WER** | > 30% (tesseract/rapidocr failure) | **$\le 10\%$** | Manual Ground-Truth Scoring |
| **Citation Bbox Accuracy** | N/A (Text-only or whole doc) | **100% Pixel-Accurate** | Automated Citation Validation |
| **Query Latency P95** | Varies / GPU-dependent | **$< 2.0\text{s}$ (CPU-only)** | Locust / k6 load tests |
| **Idle Infrastructure Cost** | Fixed VM cost | **$0.00/mo (Scale to Zero)** | GCP Billing Dashboard |

---

## 6. Running the Benchmark Suite

```bash
# Run unit & retrieval benchmark tests
python -m unittest discover -s tests

# Run RAGAS evaluation (requires golden dataset)
python -m tests.eval_ragas --dataset tests/datasets/golden_dataset.json

# Run latency load test
locust -f tests/load_test.py --host=http://localhost:8080
```

---

## 7. Phase Execution Schedule (per ACTIONPLAN.md)

| Phase | Benchmark / Test Focus | Success Criteria |
|---|---|---|
| **Phase 1.0 (Ingestion)** | • Test 1-A: VLM Router Accuracy<br>• Test 1-B: Scanned/Devanagari Page Routing<br>• Test 1-C: Dead-Letter Queue Recovery | • Clean text incurs $0$ VLM cost<br>• Scanned Hindi routed to VLM<br>• Corrupt PDF routed to DLQ after 3 retries |
| **Phase 2.0 (Retrieval)** | • Test 2-A: Retrieval Recall@5 & MRR<br>• Test 2-B: Tenant Isolation Filter<br>• Test 2-C: Hybrid vs. Single-Modality Lift<br>• Test 2-D: Diversity Pass Flooding Prevention<br>• Test 2-E: Deep Search Rerank Lift<br>• Test 2-F: Search Latency | • Recall@5 $\ge 0.85$<br>• 0% cross-tenant data leaks<br>• Hybrid+RRF beats single-modality by $\ge 5\%$<br>• No single doc $>50\%$ of top-10<br>• Search P95 $< 500\text{ms}$ |
| **Phase 3.0 (Synthesis)** | • Test 3-A: Citation Bbox Accuracy<br>• Test 3-B: RAGAS Faithfulness & Answer Quality<br>• Test 3-C: End-to-End Query Latency | • **100%** valid bbox citations<br>• Faithfulness $\ge 0.90$<br>• Query P95 $< 2.0\text{s}$ |
| **Phase 4.0 (Security)** | • Test 4-A: Cross-Tenant Penetration Test<br>• Test 4-C: Signed URL Expiry | • **0** cross-tenant leaks (JWT claim override)<br>• 15-min signed GCS URL expiration |
| **Phase 5.0 (MVP Gate)** | • Full System Benchmark Suite | • All Phase 1–4 criteria met concurrently |
| **Phase 6.0+ (Post-MVP)** | • Test 6.0: SLM Query Rewrite & HyDE<br>• Test 7.0: Citation Bbox Overlay Merging<br>• Test 10.0: Graph Traversal Latency | • Rewrite latency $< 300\text{ms}$<br>• Merged overlapping highlights<br>• Graph traversal $< 300\text{ms}$ |

