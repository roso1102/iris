# IRIS — Critical Fixes Register

**Generated:** 2026-08-13  
**Scope:** All identified breaking issues in the ingestion pipeline, VLM routing engine, and deployment configuration as of Phase 2.0.  
**Source:** Live Cloud Run logs + `trueassort/document_routing.csv` ground-truth analysis (203 labeled pages, 8 documents).

---

## Priority 1 — Deployment & Infrastructure Breaks

---

### FIX-001 — `QDRANT_URL` Missing from `ingestion-worker` Cloud Run Service

**Status:** ❌ Patched reactively via CLI — NOT permanently fixed in `deploy.sh`

**Symptom:**  
Ingestion logs showed `Ingested doc_id=doc_001 chunks=10` but Qdrant `points_count` remained 0. Worker was silently using `MemoryChunkStore` (in-memory fallback) because `QDRANT_URL` was not set. All chunk data vanished after each Cloud Run request.

**Root Cause:**  
`scripts/deploy.sh` had `QDRANT_URL` set in the `retrieval-api` deploy block but NOT in the `ingestion-worker` deploy block. The worker's `get_chunk_store()` factory fell back to `MemoryChunkStore` when `QDRANT_URL` env var was absent.

**Impact:** All ingested chunks are permanently lost after each request. Qdrant is never written to.

**Fix — Add to `scripts/deploy.sh` ingestion-worker block permanently:**
```bash
gcloud run deploy ingestion-worker \
  --set-env-vars="MODEL_BACKEND=vertex,\
GCP_PROJECT=${PROJECT_ID},\
EMBEDDING_MODEL=text-embedding-004,\
SYNTHESIS_MODEL=gemini-2.5-flash,\
LITE_MODEL=gemini-2.5-flash-lite,\
VERTEX_VISION_LOCATION=us-central1,\
QDRANT_URL=http://10.0.0.5:6333,\
RETRIEVAL_COLLECTION=iris_chunks_v2"
```

---

### FIX-002 — Pub/Sub Push Subscription Detached by Billing Kill-Switch

**Status:** ⚠️ VERIFY BEFORE FIXING — delivery was observed working during the 2026-08-12 run

**Symptom:**  
Originally suspected: messages queued in Pub/Sub with no Cloud Run ingestion logs. **Correction:** live logs from the 2026-08-12 run showed `POST / HTTP/1.1 200` on the ingestion worker, so messages *were* being delivered and processed. This fix should not be applied blindly.

**Root Cause (verify first):**  
The billing kill-switch Cloud Function fires `pushConfig={}` on `iris-ingestion-sub` when the budget threshold is hit. If that happened, the push endpoint may have been detached and never re-attached. Before changing anything, inspect the live subscription.

**Verify current state:**
```bash
gcloud pubsub subscriptions describe iris-ingestion-sub \
  --project=naturepivot-rag \
  --format="yaml(name,pushConfig)"
```

If `pushConfig.pushEndpoint` is already `https://ingestion-worker-zzdrfa3kqa-el.a.run.app`, the subscription is healthy — do **not** re-attach.

**Fix A (Immediate CLI — only if endpoint is missing):**
```bash
gcloud pubsub subscriptions modify-push-config iris-ingestion-sub \
  --push-endpoint=https://ingestion-worker-zzdrfa3kqa-el.a.run.app \
  --project=naturepivot-rag
```

> **Important:** the push endpoint is the service **root** `/`, not `/ingest`. The Eventarc/worker delivery path invokes the root handler (`POST /`), which decodes the Pub/Sub envelope and dispatches page messages. Pointing at `/ingest` would send a Pub/Sub envelope into the document-level fan-out handler and produce a 400/double-fan-out.

**Fix B (Permanent code fix):**  
Add a restore handler to `billing-kill-switch/main.py` that re-attaches the push endpoint when the budget alert fires a "billing threshold cleared" notification, instead of requiring manual intervention every time the kill-switch triggers.

---

### FIX-003 — Qdrant Client 1.19.0 vs Server 1.13.0 Version Mismatch

**Status:** ⚠️ Warning — not fatal yet, but risks silent API compatibility failures

**Symptom:**  
Cloud Run logs show `qdrant-client 1.19.0` connecting to Qdrant server `1.13.0`. The client uses newer API request formats that the older server may not recognize, causing silent 422 errors or unexpected payloads on `upsert_batch()` and search calls.

**Root Cause:**  
`requirements.txt` did not pin `qdrant-client` to a patch version. `pip install` auto-resolved to the latest (1.19.0) while the Qdrant VM runs the server pinned in `infra/qdrant.tf` at v1.13.0.

**Fix Option A — Pin client (quick, deploy today):**  
In both `services/ingestion-worker/requirements.txt` and `services/retrieval-api/requirements.txt`:
```
qdrant-client==1.13.0
```

**Fix Option B — Upgrade server (correct long-term fix):**  
In `infra/qdrant.tf`, change the Docker pull in the VM startup script:
```bash
docker pull qdrant/qdrant:v1.19.0
```
Run `terraform apply`. **Take a Qdrant data disk snapshot before doing this.**

---

### FIX-004 — No `.dockerignore` Causes 78 GB Artifact Registry Bloat

**Status:** ⚠️ Active cost bleed — ~$7.80/month in wasted storage

**Symptom:**  
`gcloud artifacts repositories describe iris --location=asia-south1` reports **78,313 MB (78.3 GB)** in Artifact Registry. Each `ingestion-worker` image is ~4.5 GB (PyTorch ~2.2 GB + Docling models ~800 MB + OpenCV ~500 MB). Without cleanup, old revisions stack up indefinitely.

**Root Cause:**  
No `.dockerignore` exists at the repo root. Every `docker build` sends the full repository context including `.git` history, `__pycache__`, test artifacts, and local caches. Additionally, no image lifecycle policy has been set to auto-delete old revisions.

**Fix A — Create `d:\iris\.dockerignore` (updated 2026-08-13):**
```
.gitignore
.venv
.git
__pycache__
*.pyc
*.pyo
.env
*.log
.DS_Store
test-docs/
trueassort/
*.egg-info
.pytest_cache
node_modules/
```
A minimal `.dockerignore` was already added on 2026-08-12; this expanded list should replace it so large local test fixtures (`test-docs/`, `trueassort/`) are never sent as Cloud Build context.

**Fix B — Delete old accumulated image revisions:**
```bash
gcloud artifacts docker images delete \
  asia-south1-docker.pkg.dev/naturepivot-rag/iris/ingestion-worker \
  --delete-tags --quiet --project=naturepivot-rag
```

**Fix C — Add lifecycle policy to auto-delete images older than 7 days:**
```bash
gcloud artifacts repositories set-cleanup-policies iris \
  --location=asia-south1 \
  --policy='[{"name":"delete-old","action":{"type":"Delete"},"condition":{"olderThan":"7d"}}]' \
  --project=naturepivot-rag
```

---

## Priority 2 — Ingestion Pipeline Code Breaks

---

### FIX-005 — Page Numbers Stored as `0/0` (Pub/Sub Envelope Parsing Mismatch)

**Status:** ❌ Active break — all chunks stored with `page_number=0`

**Symptom:**  
Ingestion logs show `Ingested doc_id=doc_001 page=0/0 chunks=10`. Every chunk in Qdrant has `page_number=0`, making page-level citation retrieval impossible.

**Root Cause:**  
GCP Pub/Sub push delivers messages in this exact envelope shape:
```json
{
  "message": {
    "data": "<base64-encoded-JSON-payload>",
    "attributes": { "some_attr": "..." },
    "messageId": "..."
  },
  "subscription": "projects/.../subscriptions/..."
}
```
The actual document payload (`gcs_uri`, `tenant_id`, `doc_id`) is base64-encoded inside `message.data`. If the handler reads from `message.attributes` or from the envelope root directly, it receives empty/None values. These propagate into Docling as null document metadata, causing the page counter to initialize at 0.

**Impact:**  
Page-level citation accuracy (`BENCHMARK.md` Hard Gate: 100% bbox grounding) fails entirely. Phase 3.0 synthesis will produce structurally incorrect citations for every document in the corpus.

**Diagnostic first — add raw body logging at top of the Flask handler:**
```python
logger.info(
    "raw_pubsub_envelope",
    extra={"body": str(request.get_json(silent=True) or {})[:2000]},
)
```
Deploy, send one test doc, inspect Cloud Logging to confirm the actual envelope shape.

**Fix (after confirming envelope shape) — Flask, not FastAPI/async:**
```python
import base64
import json

# The ingestion worker is Flask. `request.get_json()` returns the parsed
# envelope; do NOT use `await request.body()` here.
envelope = request.get_json(silent=True) or {}
message = envelope.get("message", envelope)

data = {}
raw = message.get("data", "")
if raw:
    try:
        data = json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception:
        data = {}

gcs_uri     = data.get("gcs_uri") or (message.get("attributes") or {}).get("gcs_uri")
tenant_id   = data.get("tenant_id") or (message.get("attributes") or {}).get("tenant_id")
doc_id      = data.get("doc_id") or (message.get("attributes") or {}).get("doc_id")
page_number = data.get("page_number") or (message.get("attributes") or {}).get("page_number")
total_pages = data.get("total_pages") or (message.get("attributes") or {}).get("total_pages")
```

---

### FIX-006 — VLM Rate Limiting: 140–197 Gemini Vision Calls Per Document

**Status:** ❌ Active break — all VLM calls fail with 429 on large scanned documents

**Symptom:**  
Ingestion logs show `vlm_calls=140-197` per document followed by:
- `429 RESOURCE_EXHAUSTED / Rate exceeded`
- `Gemini Vision failed after 3 attempts`
- `Vertex AI returned empty content`
- `499 The operation was cancelled`

Router correctly identifies pages as needing VLM but exhausts the 15 RPM quota immediately, then retries too fast to recover.

**Root Cause (three compounding factors):**  
1. Test corpus is primarily scanned PDFs — Signal 4 (`chars < 150`) fires on nearly every page, sending ~100% of pages to VLM.
2. Parallel page dispatch fires all VLM calls simultaneously — 140 concurrent calls against a 15 RPM hard cap is a 9× overrun.
3. Retry backoff uses `2^attempt` seconds (2s, 4s), which is far too short for API rate limit recovery. The quota needs 60–90 seconds to replenish.

**Fix A — Raise Vertex AI Quota (highest leverage, do first):**  
GCP Console → APIs & Services → Vertex AI API → Quotas → search `generate_content_requests_per_minute` → Request increase from 15 to 60.  
*(Only available now that billing is upgraded from PROMOTION to ACTIVE.)*

**Fix B — Add concurrency semaphore in VLM router:**
```python
import asyncio

_VLM_SEMAPHORE = asyncio.Semaphore(10)  # Max 10 concurrent VLM calls

async def _call_vlm_rate_limited(self, image_bytes: bytes, prompt: str) -> str:
    async with _VLM_SEMAPHORE:
        return await asyncio.to_thread(
            self._call_gemini_vision, image_bytes, prompt
        )
```

**Fix C — Differentiate 429 retry backoff from other errors in `vertex.py`:**
```python
for attempt in range(_MAX_RETRIES):
    try:
        return self._safe_generate(model, prompt, image_part)
    except google.api_core.exceptions.ResourceExhausted:
        # Rate limit: wait much longer — quota replenishes per minute
        time.sleep(60 * (attempt + 1))   # 60s, 120s, 180s
    except Exception:
        time.sleep(2 ** attempt)          # 2s, 4s for other transient errors
raise RuntimeError("VLM call failed after all retries")
```

---

### FIX-007 — `/status` Returns 429 During Processing (`concurrency=1` Conflict)

**Status:** ❌ Active break — eval harness cannot poll progress during ingestion

**Symptom:**  
While a 15-page scanned document is being processed (5–15 min), HTTP calls to `/status` on the ingestion worker return 503/429. The single Cloud Run concurrency slot is occupied by the active ingestion request.

**Root Cause:**  
`concurrency=1` is correct — two simultaneous Docling + PyTorch runs would OOM the 4 CPU / 8 GiB container. But it means there is no free slot to serve any other HTTP request, including lightweight status checks.

**Fix — avoid polling the busy worker, but do NOT query Qdrant from the laptop:**
Qdrant is private (`http://10.0.0.5:6333`) and not reachable from the local eval machine without an IAP/SSH tunnel. The proposed direct Qdrant poll below is therefore not usable as-is.

Options that actually work:

1. **Preferred for eval:** add a dedicated lightweight status endpoint on a service that is not contention-bound (e.g. retrieval-api can count Qdrant points via the shared store), and have the eval harness poll that instead of the ingestion worker.

2. **Evaluation-only convenience:** temporarily raise ingestion-worker `--concurrency=2` during the benchmark run so `/status` can be served while one page is processing. Revert to `1` for production.

3. **If no code changes are desired:** poll through the existing private route:
```bash
gcloud compute ssh qdrant-1 --zone=asia-south1-b --project=naturepivot-rag -- \
  "curl -s -X POST http://localhost:6333/collections/iris_chunks_v2/points/count \
   -H 'Content-Type: application/json' \
   -d '{\"filter\":{\"must\":[{\"key\":\"doc_id\",\"match\":{\"value\":\"doc_001\"}}]}}'"
```

For reference only (requires a reachable Qdrant URL):
```python
import requests, time

def check_doc_ingested(
    doc_id: str,
    qdrant_url: str,
    collection: str = "iris_chunks_v2"
) -> int:
    """Returns chunk count for doc_id. 0 = not yet ingested."""
    resp = requests.post(
        f"{qdrant_url}/collections/{collection}/points/count",
        json={"filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]}},
        timeout=10,
    )
    return resp.json().get("result", {}).get("count", 0)
```

---

## Priority 3 — VLM Router Signal Logic Breaks

*Ground-truth source: `trueassort/document_routing.csv`*  
*203 labeled pages across 8 documents spanning 4 routing tiers.*

---

### FIX-008 — No `multilingual_ocr` Routing Tier (Hindi / Devanagari Pages Silently Garbled)

**Status:** ❌ Active data corruption — all Hindi pages stored as garbage text

**Symptom:**  
`hindi.pdf` (doc_004, 4 pages) is labeled `multilingual_ocr` in ground truth. These pages have `valid_word_ratio` 0.82–0.87 — above Signal 2's 0.75 threshold — so they pass all 4 signals and route to `DOCLING_TEXT`. Docling extracts them as garbled or empty strings because it cannot render Devanagari script.

**Root Cause:**  
Devanagari Unicode characters (U+0900–U+097F) are valid Unicode letters. A page of properly-encoded Hindi text scores 0.82–0.87 on `valid_word_ratio` — passing Signal 2 — even though Docling has no Devanagari rendering capability. Signal 2 was designed to catch garbled Latin OCR, not non-Latin scripts.

**Impact:**  
All Hindi pages produce empty or meaningless text, which gets embedded and stored in Qdrant. These chunks will score near-zero on any semantic query because their vector representation is meaningless. The data corruption is silent — no error is raised.

**Fix — Add Signal 5: Non-Latin Script Dominant Detection (before Signal 2):**
```python
import unicodedata

def _is_non_latin_dominant(text: str, threshold: float = 0.30) -> bool:
    """Return True if >30% of letter characters are outside the Latin/Extended-Latin range."""
    letters = [c for c in text if unicodedata.category(c).startswith('L')]
    if not letters:
        return False
    non_latin = [c for c in letters if ord(c) > 0x024F]  # U+024F = end of Extended Latin
    return (len(non_latin) / len(letters)) > threshold

# In vlm_router.py _decide() method, add BEFORE Signal 2:
# Signal 5 — Non-Latin dominant script
if _is_non_latin_dominant(element.text):
    return RouteDecision.VLM_FULL_PAGE  # Gemini Vision handles multilingual OCR
```

Also add `page_1` of `englishheavyscan03.pdf` (mixed-language first page) to the router's per-element check to verify Signal 5 fires on that page but not pages 2–7.

---

### FIX-009 — Signal 3 Coverage Threshold Too Tight (0.15 Misses Image-Heavy Pages at 0.20–0.45)

**Status:** ❌ Active false negative — image-heavy pages routed as clean text

**Symptom:**  
`mixcolorbgf.pdf` pages 20–24 are labeled `vlm_heavy` in ground truth. They have:
- `has_table=false` (no Docling Table element → Signal 1 does not fire)
- `valid_word_ratio` 0.90–0.95 (passes Signal 2)
- `text_coverage` 0.15–0.42

Signal 3 only fires at `coverage < 0.15`. Pages at 0.20–0.42 coverage fall through all 4 signals and get routed to `DOCLING_TEXT` despite being image-heavy infographic pages with minimal extractable text.

**Root Cause:**  
Signal 3's 0.15 threshold was calibrated only on nearly-blank pages. Image-heavy pages with scattered caption text (coverage 0.20–0.42) were not in the original calibration dataset.

**Fix — Raise Signal 3 with a dual-condition guard (see FIX-010 for the guard rationale):**
```python
# Signal 3 — Area coverage check (REVISED)
coverage   = sum_bbox_areas(elements) / page_area
char_count = len(element.text.strip())

# Case A: Nearly blank pages (original behaviour preserved)
if coverage < 0.15 and char_count < 300:
    return RouteDecision.VLM_FULL_PAGE

# Case B: Image-heavy infographic with moderate coverage and sparse text
# Guard conditions prevent false positives on sparse-but-valid text pages:
#   - coverage < 0.45  (moderate, not dense)
#   - char_count < 150 (very few characters despite high coverage area)
#   - valid_word_ratio NOT extremely high (< 0.97 excludes clean digital text pages)
if coverage < 0.45 and char_count < 150 and valid_word_ratio < 0.97:
    return RouteDecision.VLM_FULL_PAGE
```

---

### FIX-010 — Raising Signal 3 Risks False Positives on Sparse Valid Text Pages

**Status:** ⚠️ Risk introduced by FIX-009 — requires the guard to be correct

**Symptom:**  
`englishscan4.pdf` page 27 has `text_coverage=0.20` but is correctly labeled `fast_text` because it is a sparse-but-genuine text page (e.g., a bibliography). A naive raise of Signal 3 to 0.40 would incorrectly route this page to VLM.

**Root Cause:**  
Coverage alone cannot distinguish between:
- An image-heavy infographic with a caption (should → VLM)
- A sparse valid text page like a title/bibliography (should → fast_text)

**Discriminating feature:**  
Sparse valid text pages have `valid_word_ratio` of 0.97–0.99 (near-perfect clean text). Image-heavy caption pages have `valid_word_ratio` of 0.88–0.95 (moderate).

The `valid_word_ratio < 0.97` guard in FIX-009's Case B ensures sparse clean text pages (0.97–0.99 ratio) are never escalated by the coverage check, regardless of how low their coverage percentage is.

---

### FIX-011 — `standard_ocr` Tier Has No Implementation (Quality Gap)

**Status:** ⚠️ Quality gap — deferred to Phase 2.5 (not a data corruption issue today)

**Symptom:**  
Ground truth labels 9 pages as `standard_ocr` (mid-quality scanned English text, `valid_word_ratio` 0.80–0.88). These pages are currently routed identically to 0.99-ratio clean digital text (`fast_text`), despite being lower OCR quality.

**Root Cause:**  
The router is binary: Docling direct OR VLM. There is no intermediate tier that represents "Docling text accepted but with reduced confidence."

**Impact for Phase 2.0:** Acceptable. Text is extracted, just at lower accuracy.  
**Impact for Phase 3.0:** Citations from `standard_ocr` pages will be less reliable and the synthesis layer has no signal to lower confidence appropriately.

**Fix (Phase 2.5 — after Phase 2.0 is stable):**  
Do NOT add a VLM call for `standard_ocr` pages (cost/quality tradeoff is poor). Instead, tag chunks with a confidence metadata field:
```python
# In chunker — when 0.75 <= valid_word_ratio < 0.97:
chunk.metadata["extraction_confidence"] = "standard_ocr"
chunk.metadata["ocr_confidence_score"]  = round(valid_word_ratio, 3)
```
Expose this field in `ScoredChunk` so synthesis can note lower confidence on citations from `standard_ocr` pages without any additional API cost.

---

### FIX-012 — Document-Level Routing Logic Breaks Mixed-Language Documents

**Status:** ❌ Active break on any document containing pages in multiple languages/scripts

**Symptom:**  
`englishheavyscan03.pdf` has page 1 labeled `multilingual_ocr` and pages 2–7 labeled `standard_ocr`. If any routing signal (especially the proposed Signal 5 from FIX-008) is evaluated at the document level and cached, page 1 would receive the same route as pages 2–7 — incorrectly routing a Hindi page as `standard_ocr`.

**Root Cause:**  
If any pre-pass language detection result is computed once per document and reused across all elements, mixed-language documents will have all pages classified by whichever language was detected first (or dominates the document overall).

**Fix — Verify routing is strictly per-element in `vlm_router.py`:**
```python
# This is the correct pattern — decision is per-element, not per-document:
for element in docling_output.elements:
    decision = self._decide(element)   # Each call is independent
    routed.append(RoutedElement(element=element, decision=decision))

# The WRONG pattern (do not use):
# document_language = detect_language(full_text)  # cached at doc level
# for element in elements:
#     decision = self._decide(element, language=document_language)  # reuse → wrong
```

Audit `vlm_router.py` for any variable that is set once before the element loop and read inside `_decide()`. Signal 5 (`_is_non_latin_dominant()`) must be called with `element.text` (element scope), not with the concatenated document text.

---

## Summary Table

| Fix ID | Category | Severity | Status | Est. Effort |
|---|---|---|---|---|
| FIX-001 | Deployment | 🔴 Critical | Patched — not permanent | 5 min |
| FIX-002 | Deployment | 🔴 Critical | Active break | 5 min |
| FIX-003 | Deployment | 🟡 Warning | Active risk | 10 min |
| FIX-004 | Deployment | 🟡 Warning | Active cost bleed | 15 min |
| FIX-005 | Pipeline | 🔴 Critical | Active break | 30 min |
| FIX-006 | Pipeline | 🔴 Critical | Active break | 1–2 hours |
| FIX-007 | Pipeline | 🔴 Critical | Active break | 30 min |
| FIX-008 | VLM Router | 🔴 Critical | Active data corruption | 1 hour |
| FIX-009 | VLM Router | 🟡 Important | False negative routing | 1 hour |
| FIX-010 | VLM Router | 🟡 Important | False positive guard | 30 min |
| FIX-011 | VLM Router | 🟢 Quality gap | Phase 2.5 scope | 2 hours |
| FIX-012 | VLM Router | 🔴 Critical | Active break on mixed docs | 1 hour |

---

## Recommended Execution Order

```
STEP 0 — Unblock tooling:
  Reauthenticate gcloud (`gcloud auth login`) — currently failing non-interactively.
  This blocks all live verification.

STEP 1 — Today (infrastructure, no redeploy needed):
  FIX-001  Add permanent QDRANT_URL to deploy.sh ingestion-worker block
  FIX-004  Replace .dockerignore with the expanded list (done) + cleanup policy
  FIX-002  VERIFY subscription first; re-attach only if push endpoint is empty

STEP 2 — Before next ingestion run (requires redeploy):
  FIX-003  Pin qdrant-client==1.13.0 in both requirements.txt files
  FIX-005  Fix Pub/Sub envelope parsing (Flask handler) + raw body logging
  FIX-006  Vertex AI quota request + semaphore + differentiated 429 backoff
  FIX-007  Poll status via a non-contending route (or eval-only concurrency=2)

STEP 3 — Phase 2.5 router hardening sprint:
  FIX-008  Add Signal 5 non-Latin script detection
  FIX-009  Revise Signal 3 coverage threshold with dual-condition guard
  FIX-010  Verify false positive guard is correct
  FIX-012  Audit vlm_router.py for per-element vs document-level routing scope
  FIX-011  Add extraction_confidence metadata tagging for standard_ocr pages
```

**TESTING PLAN**

Here is the exact testing structure for IRIS — when to test where, and what to run at each level.

---

## The Core Principle

**Every GCP API call costs money. Test everything possible locally first. Only move to GCP when you have exhausted what you can test locally.**

The rule of thumb: if a bug can be caught locally, catching it on GCP costs 50–100× more in time and money.

---

## Tier 0 — Pure Logic Tests (Local, Zero Cost, <10 Seconds)

**When to run:** Every single code change, before anything else. Run these even before looking at the output of your change.

**What they test:** Mathematical/algorithmic correctness with zero external dependencies. These use only Python stdlib and your own c ode.

| Test File | What It Covers |
|---|---|
| `tests/test_rrf.py` | Given two ranked lists with known values, verify fused order is correct |
| `tests/test_diversity.py` | Given 10 chunks from 2 doc_ids, verify 0.5× penalty applied to repeated doc |
| `tests/test_bm25.py` | Given legal boilerplate text, verify common words get low TF-IDF scores |
| `tests/test_vlm_router.py` | Given synthetic element metadata (char_count, ratio, coverage, has_table), verify correct route decision |
| `tests/test_signal5.py` | Given Hindi Devanagari text, verify non-Latin detection fires; English text does not |
| `tests/test_table_validator.py` | Valid markdown table → True; merged rows → False |
| `tests/test_pubsub_parser.py` | Given mock Pub/Sub envelope JSON, verify base64 decode extracts correct doc_id/gcs_uri |
| `tests/test_chunker.py` | Given synthetic Docling element output, verify session_id, page_number, source fields populated |

Run command: `python -m pytest tests/ -m "not live and not integration" -v`

**If any of these fail, do not proceed to the next tier.**

---

## Tier 1 — Component Integration Tests with Fakes (Local, Zero Cost, <60 Seconds)

**When to run:** After any structural code change — new file, new class, wiring two components together.

**What they test:** That components connect to each other correctly, using `MemoryChunkStore` and `MockModelProvider` (both already in your codebase). No real Qdrant, no real Vertex AI.

| Test File | What It Covers |
|---|---|
| `tests/test_ingestion_pipeline.py` | MockPDF → MockDoclingParser → VLM router → chunker → MemoryChunkStore → verify chunk count, page_numbers, tenant isolation |
| `tests/test_search_orchestrator.py` | Seed MemoryChunkStore → run `standard_search` → verify RRF output → verify diversity applied |
| `tests/test_delete_cascade.py` | Seed MemoryChunkStore → `delete_by_doc` → verify count drops to 0; verify Firestore mock called |
| `tests/test_retrieval_api.py` | FastAPI TestClient: POST /search → 200 with results; missing tenant_id header → 422; DELETE /documents → 200 |
| `tests/test_deep_search.py` | MockProvider.rewrite_query() + MockProvider.generate_hyde() → verify orchestrator uses HyDE embedding |

Run command: `python -m pytest tests/ -m "not live" -v`

**What `MockModelProvider` returns:**
- `embed(text)` → deterministic fake 768-d vector seeded from hash of text (so same input always returns same vector, meaning search is testable)
- `generate_text(prompt)` → a pre-written string from a fixture file
- `call_gemini_vision(image)` → cached text from `trueassort/vlm_cache/{page}.txt`

---

## Tier 2 — Live API Connection Smoke Test (Local Machine, ~₹0.50 Per Run)

**When to run:** After any authentication change, provider config change, or after `gcloud auth application-default login`. Roughly once a week, not every code change.

**What they test:** That your local machine can actually reach the live APIs. Not data quality — just connectivity and auth.

| Test | What It Checks | Cost |
|---|---|---|
| `provider.embed("hello world")` → assert `len(vector) == 768` | Vertex AI auth + embedding endpoint alive | ~₹0.01 |
| `provider.generate_text("say hi", model=LITE_MODEL)` → assert `len(response) > 0` | Flash Lite endpoint alive, thinking mode OFF | ~₹0.05 |
| `GET http://10.0.0.5:6333/collections/iris_chunks_v2` → assert `status == "green"` | Qdrant VM reachable, collection exists | ₹0 |
| `store.upsert_batch([one_chunk])` then `store.search_dense(embed, limit=1)` → assert 1 result | Full Qdrant read/write path works | ₹0 |

Qdrant is private (`10.0.0.5:6333`), so open an IAP SSH tunnel before the Qdrant half:

```bash
gcloud compute ssh qdrant-1 \
  --zone=asia-south1-b --project=naturepivot-rag \
  --tunnel-through-iap -- -L 6333:localhost:6333 -N
```

Run command (bash):

```bash
RUN_VERTEX_LIVE_TESTS=1 RUN_QDRANT_LIVE_TESTS=1 QDRANT_URL=http://localhost:6333 \
python -m pytest tests/test_vertex_live.py tests/test_qdrant_live.py -m live -v
```

PowerShell:

```powershell
$env:RUN_VERTEX_LIVE_TESTS="1"
$env:RUN_QDRANT_LIVE_TESTS="1"
$env:QDRANT_URL="http://localhost:6333"
python -m pytest tests/test_vertex_live.py tests/test_qdrant_live.py -m live -v
```

Vertex-only (no tunnel needed):

```powershell
$env:RUN_VERTEX_LIVE_TESTS="1"
python -m pytest tests/test_vertex_live.py -m live -v
```

These tests are fast and cheap. They exist to catch "your gcloud session expired" or "the Qdrant VM rebooted" problems before you waste a full Cloud Run deploy.

---

## Tier 3 — Single Document Cloud Run Smoke Test (~₹10 Per Run)

**When to run:** After any Cloud Run service code change that passed Tiers 0 and 1. Specifically: after changing `app.py`, `store.py`, environment variable configuration, or Dockerfile. NOT after every code change.

**The key rule: use only a clean English text document for this test.**

`pages50eng.pdf` (doc_006, 34 pages, all `fast_text` route) triggers **0 VLM calls**. Zero Gemini Vision API calls. Only embedding calls. Cost is negligible.

**What to verify:**
1. Worker receives the Pub/Sub message (logs show `Ingested doc_id=doc_006`)
2. Chunks appear in Qdrant: `GET /doc-status/doc_006` → `chunks > 0`
3. `page_number` is correct on at least 3 sampled chunks (not 0)
4. `tenant_id` filter works: search from a different tenant returns 0 results
5. `retrieval-api /search` with a query returns results from doc_006 chunks

This is your **deployment verification gate.** If this passes, your deployment is correct. If it fails, something in the wiring broke.

**Never use scanned PDFs for Tier 3.** `hindi.pdf`, `mixcolorbgf.pdf`, `scannedenglish.pdf` — all of these trigger VLM calls and cost 20–50× more. They belong only in Tier 4.

---

## Tier 4 — Full E2E Acceptance Test (~₹100–200 Per Run)

**When to run:** ONCE per phase milestone, after ALL of Tiers 0–3 pass cleanly. This is Phase 2.0's final acceptance gate, not a development tool.

**Checklist before running Tier 4:**
- [ ] Thinking mode explicitly disabled (`thinking_budget=0`) in `vertex.py`
- [ ] VLM calls use Flash Lite (not Flash)
- [ ] VLM cache populated from a previous run (so pages already processed don't re-hit the API)
- [ ] Billing budget alert set at ₹200 specifically for this run
- [ ] All 8 documents confirmed pre-uploaded to GCS
- [ ] Pub/Sub subscription confirmed attached

**What it measures:** The Phase 2.0 exit criteria — Recall@5, tenant isolation, RRF vs single-modality, diversity flooding prevention, latency <500ms.

After the first run, populate `trueassort/vlm_cache/` with the extracted text for every page. Every subsequent Tier 4 run then costs only embedding + search API calls, not VLM calls. Cost drops from ₹200 to ~₹20.

---

## The Decision Flowchart

```
Made a code change
       │
       ▼
Run Tier 0 (pure logic tests)
  FAIL → fix locally
  PASS ↓
       │
       ▼
Did you change component wiring?
  YES → Run Tier 1 (integration with fakes)
         FAIL → fix locally
         PASS ↓
  NO  ↓
       │
       ▼
Did you change auth/provider/env config?
  YES → Run Tier 2 (live API connection check, ~₹0.50)
         FAIL → fix auth/config
         PASS ↓
  NO  ↓
       │
       ▼
Did you change Cloud Run service code or Dockerfile?
  YES → Deploy + Run Tier 3 (single clean PDF, ~₹10)
         FAIL → fix deployment config
         PASS ↓
  NO  ↓
       │
       ▼
Are you at a phase milestone (Phase 2.0 complete)?
  YES → Run Tier 4 (full E2E, ~₹100–200, once)
  NO  → You are done testing this change
```

---

## What Caused the ₹7,503 Bill

You ran what is effectively Tier 4 tests repeatedly during what should have been Tier 0/1 development iterations. Specifically:

- Each failed deployment cycle cost ~₹500–800 in Gemini Vision calls
- Thinking mode was enabled, multiplying each call's cost by 5–8×
- 8 scanned PDFs were used every time instead of 1 clean PDF
- No VLM cache existed, so every run re-processed every page

The fixes going forward: disable thinking mode, add VLM cache, use clean PDF for Tier 3, and reserve the full 8-document corpus strictly for Tier 4 milestone gates.