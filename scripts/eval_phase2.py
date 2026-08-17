"""Phase 2.0/2.5 Evaluation Harness.

Usage:
    python scripts/eval_phase2.py [--skip-ingestion] [--report-only]

Uses service account impersonation for Cloud Run IAP auth:
  gcloud auth print-identity-token
    --impersonate-service-account=<sa>@naturepivot-rag.iam.gserviceaccount.com
    --audiences=<cloud-run-url>

Triggers ingestion for the 8 golden PDFs, waits for completion, then runs:
  - Test 2-A: Retrieval Recall@5 (all 50 queries)
  - Test 2-E: Deep Search lift on ambiguous queries
  - Test 2-D: Diversity / source dedup check
  - Phase 2.5: VLM router threshold sweep on labeled_pages.csv
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT = "naturepivot-rag"
REGION = "asia-south1"
TENANT_ID = "test-tenant"
RETRIEVAL_URL = "https://retrieval-api-zzdrfa3kqa-el.a.run.app"
INGEST_URL = "https://ingestion-worker-zzdrfa3kqa-el.a.run.app"

# Service accounts for impersonation
RETRIEVAL_SA = "retrieval-api-sa@naturepivot-rag.iam.gserviceaccount.com"
INGEST_SA = "ingestion-worker-sa@naturepivot-rag.iam.gserviceaccount.com"

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = ROOT / "goldendataset.json"
LABELED_PATH = ROOT / "trueassort" / "document_routing.csv"
REPORT_PATH = ROOT / "eval_report_phase2.json"

DOC_IDS = [f"doc_{i:03d}" for i in range(1, 9)]


# ── auth via SA impersonation ─────────────────────────────────────────────────

def _id_token(service_account: str, audience: str) -> str:
    """Get ID token via SA impersonation with correct audience."""
    cmd = (
        f'gcloud auth print-identity-token '
        f'--impersonate-service-account={service_account} '
        f'--audiences={audience} '
        f'--project={PROJECT}'
    )
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)
    # gcloud emits a warning line; the last line is the token
    lines = result.stdout.strip().splitlines()
    token = lines[-1].strip()
    if not token or len(token) < 100:
        raise RuntimeError(f"Failed to get ID token: {result.stdout[:200]}")
    return token


def _log(msg: str) -> None:
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")


# ── ingestion ─────────────────────────────────────────────────────────────────

def _token_ingest() -> str:
    return _id_token(INGEST_SA, INGEST_URL)


def _token_retrieval() -> str:
    return _id_token(RETRIEVAL_SA, RETRIEVAL_URL)


def _ingest(url_path: str, method: str = "GET", timeout: int = 60, json_body: Optional[dict] = None):
    import requests
    resp = requests.request(
        method, f"{INGEST_URL}{url_path}",
        headers={"Authorization": f"Bearer {_token_ingest()}"},
        json=json_body,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        _log(f"  INGEST {resp.status_code}: {resp.text[:150]}")
    return resp


def trigger_ingestion():
    """Call /ingest endpoint for all 8 docs with idempotent SHA256 cache skip."""
    for doc_id in DOC_IDS:
        gcs_uri = f"gs://iris-raw-pdfs/{TENANT_ID}/{doc_id}.pdf"
        resp = _ingest(
            "/ingest",
            method="POST",
            timeout=120,
            json_body={"gcs_uri": gcs_uri, "tenant_id": TENANT_ID, "doc_id": doc_id},
        )
        try:
            data = resp.json()
            status = data.get("status", data.get("error", str(resp.status_code)))
        except Exception:
            status = f"HTTP {resp.status_code}"
        _log(f"Triggered {doc_id}: {status}")


def _retrieval_status(doc_id: str, timeout: int = 30):
    import requests
    resp = requests.get(
        f"{RETRIEVAL_URL}/doc-status/{doc_id}",
        headers={
            "Authorization": f"Bearer {_token_retrieval()}",
            "tenant-id": TENANT_ID,
        },
        timeout=timeout,
    )
    if resp.status_code >= 400:
        _log(f"  STATUS {resp.status_code}: {resp.text[:150]}")
    return resp


def wait_for_ingestion(timeout_minutes: int = 45) -> bool:
    """Poll retrieval-api Qdrant point counts until all 8 docs have chunks."""
    _log(f"Waiting up to {timeout_minutes}min for all docs...")
    deadline = time.time() + timeout_minutes * 60

    while time.time() < deadline:
        all_ready = True
        for doc_id in DOC_IDS:
            try:
                resp = _retrieval_status(doc_id, timeout=30)
                if resp.status_code >= 400:
                    all_ready = False
                    break
                data = resp.json()
                if int(data.get("chunks", 0)) == 0:
                    all_ready = False
                    break
            except Exception:
                all_ready = False
                break

        if all_ready:
            _log("All 8 docs ingested!")
            return True

        time.sleep(30)

    _log("Timeout — not all docs finished")
    return False


# ── retrieval helpers ─────────────────────────────────────────────────────────

def _search(json_body: dict, timeout: int = 60) -> dict:
    import requests
    token = _token_retrieval()
    resp = requests.post(
        f"{RETRIEVAL_URL}/search",
        json=json_body,
        headers={
            "Authorization": f"Bearer {token}",
            "tenant-id": TENANT_ID,
        },
        timeout=timeout,
    )
    if resp.status_code >= 400:
        _log(f"  SEARCH {resp.status_code}: {resp.text[:150]}")
    resp.raise_for_status()
    return resp.json()


def run_search(query: str, mode: str = "standard",
               doc_ids: Optional[List[str]] = None,
               history: Optional[List[dict]] = None,
               top_k: int = 10) -> dict:
    body = {"query": query, "mode": mode, "top_k": top_k}
    if doc_ids:
        body["doc_ids"] = doc_ids
    if history and mode == "deep":
        body["history"] = history
    return _search(body)


# ── metrics ───────────────────────────────────────────────────────────────────

def compute_recall_at_k(results: List[dict], relevant_docs: List[str], k: int = 5) -> float:
    if not relevant_docs:
        return 0.0
    top_docs = {r.get("doc_id", "") for r in results[:k]}
    hits = len(top_docs & set(relevant_docs))
    return hits / len(relevant_docs)


def compute_page_recall_at_k(
    results: List[dict],
    relevant_docs: List[str],
    relevant_pages: List[int],
    k: int = 5,
) -> float:
    """Page-level recall: a hit requires both doc_id and page_number to match."""
    relevant_pairs = {
        (d, p) for d in relevant_docs for p in relevant_pages
    }
    if not relevant_pairs:
        return 0.0
    top_pairs = {
        (r.get("doc_id", ""), int(r.get("page_number", 0)))
        for r in results[:k]
    }
    return len(top_pairs & relevant_pairs) / len(relevant_pairs)


def compute_source_duplication(results: List[dict], top_k: int = 10) -> float:
    if not results:
        return 0.0
    doc_counts: Dict[str, int] = {}
    for r in results[:top_k]:
        d = r.get("doc_id", "")
        doc_counts[d] = doc_counts.get(d, 0) + 1
    return max(doc_counts.values()) / min(top_k, len(results)) if doc_counts else 0.0


def compute_mrr(
    results: List[dict],
    relevant_docs: List[str],
    relevant_pages: Optional[List[int]] = None,
    k: int = 10,
) -> float:
    """Mean Reciprocal Rank: 1/rank of first relevant hit, else 0.

    Page-level when `relevant_pages` is provided, otherwise doc-level.
    """
    if not relevant_docs:
        return 0.0

    if relevant_pages:
        relevant_pairs = {(d, p) for d in relevant_docs for p in relevant_pages}
        for rank, r in enumerate(results[:k], start=1):
            pair = (r.get("doc_id", ""), int(r.get("page_number", 0)))
            if pair in relevant_pairs:
                return 1.0 / rank
    else:
        relevant = set(relevant_docs)
        for rank, r in enumerate(results[:k], start=1):
            if r.get("doc_id", "") in relevant:
                return 1.0 / rank
    return 0.0


def percentile(values: List[float], p: float) -> float:
    """Linear-interpolation percentile (p in 0..100)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (p / 100.0) * (len(ordered) - 1)
    lower = int(rank)
    upper = lower + 1
    if upper >= len(ordered):
        return ordered[-1]
    frac = rank - lower
    return ordered[lower] * (1 - frac) + ordered[upper] * frac


def check_tenant_isolation(query: str, wrong_tenant: str = "tier4-wrong-tenant") -> bool:
    """Cross-tenant search must return zero results."""
    import requests

    token = _token_retrieval()
    resp = requests.post(
        f"{RETRIEVAL_URL}/search",
        json={"query": query, "mode": "standard", "top_k": 10},
        headers={"Authorization": f"Bearer {token}", "tenant-id": wrong_tenant},
        timeout=60,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"tenant-isolation search returned {resp.status_code}: {resp.text[:200]}")
    results = resp.json().get("results", [])
    return len(results) == 0


# ── main benchmarks ───────────────────────────────────────────────────────────

def load_golden() -> List[dict]:
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)


def run_benchmarks(skip_ingestion: bool = False, skip_deep: bool = False):
    print("\n" + "=" * 60)
    print("  IRIS Phase 2.0/2.5 - Evaluation Harness")
    print("=" * 60)

    # ── step 1: ingestion ────────────────────────────────────────────────
    if not skip_ingestion:
        print("\n── Step 1: Trigger Ingestion ──")
        trigger_ingestion()
        if not wait_for_ingestion():
            print("ERROR: Ingestion incomplete. Retry with --skip-ingestion later.")
            return

    # ── step 2: load golden ─────────────────────────────────────────────
    golden = load_golden()
    print(f"\n── Step 2: Loaded {len(golden)} golden queries ──")

    # ── test 2-A: recall@5 ──────────────────────────────────────────────
    print("\n── Test 2-A: Standard Mode Recall@5 ──")
    results_2a = []
    for item in golden:
        resp = run_search(item["query"], mode="standard", top_k=10)
        latency = resp.get("latency_ms", 0)

        result_docs = resp.get("results", [])
        recall = compute_recall_at_k(result_docs, item["relevant_doc_ids"], k=5)
        page_recall = compute_page_recall_at_k(
            result_docs,
            item["relevant_doc_ids"],
            item.get("relevant_page_numbers", []),
            k=5,
        )
        mrr = compute_mrr(
            result_docs,
            item["relevant_doc_ids"],
            item.get("relevant_page_numbers", []),
            k=10,
        )
        dup = compute_source_duplication(result_docs, top_k=10)

        results_2a.append({
            "query_id": item["query_id"],
            "type": item["type"],
            "recall_at_5": round(recall, 3),
            "recall_page_at_5": round(page_recall, 3),
            "mrr": round(mrr, 3),
            "source_dup_pct": round(dup, 3),
            "latency_ms": latency,
            "num_results": len(result_docs),
        })

        if len(results_2a) % 10 == 0:
            _log(f"  {len(results_2a)}/{len(golden)}  recall_5={recall:.2f}")

    avg_recall = sum(r["recall_at_5"] for r in results_2a) / len(results_2a)
    avg_page_recall = sum(r["recall_page_at_5"] for r in results_2a) / len(results_2a)
    avg_mrr = sum(r["mrr"] for r in results_2a) / len(results_2a)
    avg_lat = sum(r["latency_ms"] for r in results_2a) / len(results_2a)
    lat_p95 = percentile([r["latency_ms"] for r in results_2a], 95)
    print(f"\n  Avg Recall@5      : {avg_recall:.3f}")
    print(f"  Avg Page Recall@5 : {avg_page_recall:.3f}")
    print(f"  Avg MRR           : {avg_mrr:.3f}")
    print(f"  Avg Latency       : {avg_lat:.1f}ms")
    print(f"  Latency P95       : {lat_p95:.1f}ms")

    print("\n  Recall by query type:")
    by_type: Dict[str, List[float]] = {}
    for r in results_2a:
        by_type.setdefault(r["type"], []).append(r["recall_at_5"])
    for t in sorted(by_type):
        vals = by_type[t]
        print(f"    {t:25s}: {sum(vals)/len(vals):.3f}  (n={len(vals)})")

    print("\n  Page Recall by query type:")
    by_type_page: Dict[str, List[float]] = {}
    for r in results_2a:
        by_type_page.setdefault(r["type"], []).append(r["recall_page_at_5"])
    for t in sorted(by_type_page):
        vals = by_type_page[t]
        print(f"    {t:25s}: {sum(vals)/len(vals):.3f}  (n={len(vals)})")

    # ── test 2-E: deep search lift ──────────────────────────────────────
    ambiguous = [q for q in golden if q["type"] == "short_ambiguous"]
    win_rate = 0.0
    if skip_deep:
        print("\n── Test 2-E: Deep Search Lift on Ambiguous Queries ──")
        print("  SKIPPED (--skip-deep)")
    else:
        print("\n── Test 2-E: Deep Search Lift on Ambiguous Queries ──")
        deep_better = 0
        for item in ambiguous:
            std = run_search(item["query"], mode="standard", top_k=5)
            deep = run_search(item["query"], mode="deep", top_k=5)
            s_r = compute_recall_at_k(std.get("results", []), item["relevant_doc_ids"], k=5)
            d_r = compute_recall_at_k(deep.get("results", []), item["relevant_doc_ids"], k=5)
            if d_r > s_r:
                deep_better += 1
            elif d_r == s_r:
                deep_better += 0.5
        win_rate = deep_better / len(ambiguous) if ambiguous else 0
        print(f"  Deep beats Standard on {win_rate:.0%} of {len(ambiguous)} ambiguous queries")

    # ── test 2-D: diversity ─────────────────────────────────────────────
    print("\n── Test 2-D: Diversity / Source Deduplication ──")
    max_dups = [r["source_dup_pct"] for r in results_2a]
    over_half = sum(1 for d in max_dups if d > 0.5)
    print(f"  >50% single-source queries : {over_half}/{len(max_dups)}")
    print(f"  Max duplication            : {max(max_dups):.0%}")

    # ── test 2-B: tenant isolation ──────────────────────────────────────
    print("\n── Test 2-B: Tenant Isolation ──")
    isolation_ok = check_tenant_isolation(golden[0]["query"])
    print(f"  Cross-tenant search empty : {isolation_ok}")

    # ── test 2-F: search latency ────────────────────────────────────────
    print("\n── Test 2-F: Search Latency ──")
    print(f"  P95 latency : {lat_p95:.1f}ms  (target < 500ms)")
    print(f"  Pass        : {lat_p95 < 500.0}")

    # ── phase 2.5: threshold sweep ──────────────────────────────────────
    print("\n── Phase 2.5: VLM Router Threshold Sweep ──")
    run_threshold_sweep()

    # ── write report ────────────────────────────────────────────────────
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_2a_recall": {
            "avg_recall_at_5": round(avg_recall, 3),
            "avg_page_recall_at_5": round(avg_page_recall, 3),
            "avg_mrr": round(avg_mrr, 3),
            "avg_latency_ms": round(avg_lat, 1),
            "latency_p95_ms": round(lat_p95, 1),
            "by_type": {t: round(sum(v)/len(v), 3) for t, v in by_type.items()},
            "by_type_page": {t: round(sum(v)/len(v), 3) for t, v in by_type_page.items()},
            "per_query": results_2a,
        },
        "test_2b_tenant_isolation": {
            "cross_tenant_empty": isolation_ok,
        },
        "test_2e_deep_lift": {
            "deep_win_rate": round(win_rate, 2),
            "n_ambiguous": len(ambiguous),
            "skipped": skip_deep,
        },
        "test_2d_diversity": {
            "queries_over_half_single_source": over_half,
            "max_dup_pct": round(max(max_dups), 2) if max_dups else 0,
        },
        "test_2f_latency": {
            "p95_ms": round(lat_p95, 1),
            "pass": lat_p95 < 500.0,
        },
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport → {REPORT_PATH}")


# ── Phase 2.5: VLM threshold sweep ────────────────────────────────────────────

def run_threshold_sweep():
    if not LABELED_PATH.exists():
        _log(f"Missing: {LABELED_PATH}")
        return

    with open(LABELED_PATH, encoding="utf-8") as f:
        pages = list(csv.DictReader(f))
    print(f"  Labeled pages: {len(pages)}")

    RATIO_DEFAULT, COV_DEFAULT = 0.75, 0.15

    def predicted_vlm(has_table: bool, ratio: float, r_thresh: float, cov: float, c_thresh: float) -> bool:
        if has_table:
            return True
        if ratio < r_thresh:
            return True
        if cov < c_thresh:
            return True
        return False

    def accuracy(r_thresh: float, c_thresh: float) -> float:
        correct = 0
        for p in pages:
            expected_vlm = p["expected_route"] == "vlm_heavy"
            actual_vlm = predicted_vlm(
                p["has_table"].lower() == "true",
                float(p["valid_word_ratio"]),
                r_thresh,
                float(p["text_coverage"]),
                c_thresh,
            )
            if actual_vlm == expected_vlm:
                correct += 1
        return correct / len(pages)

    baseline = accuracy(RATIO_DEFAULT, COV_DEFAULT)
    print(f"  Baseline (ratio={RATIO_DEFAULT}, cov={COV_DEFAULT}): {baseline:.1%}")

    # Sweep word ratio
    best_r, best_ra = RATIO_DEFAULT, baseline
    for r in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
        acc = accuracy(r, COV_DEFAULT)
        marker = " ←" if acc > best_ra else ""
        print(f"    ratio={r:.2f}  acc={acc:.1%}{marker}")
        if acc > best_ra:
            best_ra, best_r = acc, r
    print(f"  Best ratio: {best_r:.2f} (acc={best_ra:.1%})")

    # Sweep coverage
    best_c, best_ca = COV_DEFAULT, baseline
    for c in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]:
        acc = accuracy(RATIO_DEFAULT, c)
        marker = " ←" if acc > best_ca else ""
        print(f"    cov={c:.2f}  acc={acc:.1%}{marker}")
        if acc > best_ca:
            best_ca, best_c = acc, c
    print(f"  Best coverage: {best_c:.2f} (acc={best_ca:.1%})")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    skip_ingestion = "--skip-ingestion" in sys.argv
    skip_deep = "--skip-deep" in sys.argv
    run_benchmarks(skip_ingestion=skip_ingestion, skip_deep=skip_deep)


if __name__ == "__main__":
    main()
