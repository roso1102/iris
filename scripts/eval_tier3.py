"""Tier 3 — Single Document Cloud Run Smoke Test (~₹10 per run).

Deployment verification gate: prove the live ingestion -> Qdrant -> retrieval
path works for one clean English PDF (doc_006 / pages50eng.pdf) without firing
the expensive VLM-heavy corpus.

Reuses the auth + HTTP helpers in eval_phase2.py and leaves that 8-doc harness
untouched.

Run:
    .venv\\Scripts\\python scripts/eval_tier3.py [--verify-logs]

Exit code 0 only when every check passes.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_phase2 import (  # noqa: E402
    INGEST_URL,
    RETRIEVAL_URL,
    TENANT_ID,
    _retrieval_status,
    _token_ingest,
    _token_retrieval,
)

DOC_ID = "doc_006"
GCS_URI = f"gs://iris-raw-pdfs/{TENANT_ID}/{DOC_ID}.pdf"
WRONG_TENANT = "tier3-wrong-tenant"
QUERY = (
    "Who are the authors of Digital corporate reporting research developments "
    "and implications?"
)

CHUNK_TIMEOUT_SEC = 300
CHUNK_POLL_INTERVAL_SEC = 15
# doc_006 has one table page (page 34) plus pages 28-33, which are the
# article's reference/bibliography pages. Those pages have a near-empty
# embedded text layer (Docling extracts only "Page N of 41" footers), so
# Signal 4 (page_total_chars < 150) legitimately routes them to VLM OCR.
# 7 sparse pages + 1 table page + safety margin = 12.
MAX_VLM_CALLS = 12

_results: list[tuple[str, bool, str]] = []
_run_started_utc = datetime.now(timezone.utc)
_run_ingest_fresh = False


def _record(name: str, ok: bool, detail: str = "") -> None:
    _results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")


def _post_ingest() -> tuple[int, dict]:
    import requests

    token = _token_ingest()
    resp = requests.post(
        f"{INGEST_URL}/ingest",
        json={"gcs_uri": GCS_URI, "tenant_id": TENANT_ID, "doc_id": DOC_ID},
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


def _search_for_tenant(tenant_id: str, doc_ids=None, top_k: int = 10) -> dict:
    import requests

    token = _token_retrieval()
    resp = requests.post(
        f"{RETRIEVAL_URL}/search",
        json={"query": QUERY, "mode": "standard", "doc_ids": doc_ids, "top_k": top_k},
        headers={"Authorization": f"Bearer {token}", "tenant-id": tenant_id},
        timeout=60,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"search returned {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def _gcloud_cmd() -> str:
    gcloud = shutil.which("gcloud")
    if gcloud:
        return gcloud
    candidates = [
        r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    ]
    for cand in candidates:
        if Path(cand).exists():
            return cand
    return "gcloud"


def _parse_log_ts(ts: str):
    if not ts:
        return None
    try:
        # GCP gives 6- or 9-digit fractional seconds; normalize to microseconds.
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _verify_vlm_calls() -> int:
    """Sum VLM calls only for log lines produced by THIS run.

    A fresh ingestion (`status=processing`) publishes fresh page logs with
    per-page `vlm_calls=N`. A cached rerun (`already_ingested`) publishes
    nothing, so the correct result is 0 — not the sum of all historical runs.
    """
    if not _run_ingest_fresh:
        return 0

    env = dict(os.environ)
    cmd = _gcloud_cmd()
    # Filter by service_name only; the doc_006 match and the time window are
    # applied in Python below (avoids cmd.exe quoting issues on Windows).
    filter_expr = 'resource.labels.service_name="ingestion-worker"'
    if cmd.lower().endswith(".cmd"):
        # .cmd wrappers can only be spawned reliably through a shell on Windows.
        # All arguments here are constants, so shell=True is safe.
        command = f'"{cmd}" logging read {filter_expr} --limit=200 --format=json'
        out = subprocess.run(command, capture_output=True, text=True, check=True, shell=True, env=env)
    else:
        argv = [cmd, "logging", "read", filter_expr,
                "--limit=200", "--format=json"]
        out = subprocess.run(argv, capture_output=True, text=True, check=True, env=env)

    entries = json.loads(out.stdout or "[]")
    total = 0
    for e in entries:
        raw = e.get("textPayload", "") or (e.get("jsonPayload") or {}).get("message", "")
        if "doc_id=doc_006" not in raw:
            continue
        ts = _parse_log_ts(e.get("timestamp", ""))
        if ts is not None and ts < _run_started_utc:
            continue
        m = re.search(r"vlm_calls=(\d+)", raw)
        if m:
            total += int(m.group(1))
    return total


def _check_vlm_calls() -> None:
    try:
        total = _verify_vlm_calls()
    except Exception as exc:
        _record(f"vlm_calls<={MAX_VLM_CALLS}", False, f"log read failed: {exc}")
        return
    if not _run_ingest_fresh:
        # Cached rerun publishes no ingestion logs; the fresh-run cost guard
        # has already been validated on the original processing run.
        _record(f"vlm_calls<={MAX_VLM_CALLS}", True, "cache hit — no fresh VLM calls to measure")
        return
    ok = total <= MAX_VLM_CALLS
    _record(f"vlm_calls<={MAX_VLM_CALLS}", ok, f"vlm_calls={total} (expected <= {MAX_VLM_CALLS})")


def _check_ingest() -> None:
    global _run_ingest_fresh
    status_code, body = _post_ingest()
    ingest_status = body.get("status", "")
    if status_code >= 400:
        _record("trigger_ingestion", False, f"HTTP {status_code}: {body}")
        return
    if ingest_status == "processing":
        _run_ingest_fresh = True
        _record("trigger_ingestion", True, "status=processing (fresh Pub/Sub fan-out)")
    elif ingest_status == "already_ingested":
        _record("trigger_ingestion", True, "status=already_ingested (cache hit)")
    else:
        _record("trigger_ingestion", False, f"status={ingest_status or body}")


def _check_chunks() -> None:
    deadline = time.time() + CHUNK_TIMEOUT_SEC
    while time.time() < deadline:
        try:
            resp = _retrieval_status(DOC_ID, timeout=30)
            if resp.status_code < 400:
                data = resp.json()
                chunks = int(data.get("chunks", 0))
                if chunks > 0:
                    _record("chunks_present", True, f"chunks={chunks}")
                    return
        except Exception:
            pass
        time.sleep(CHUNK_POLL_INTERVAL_SEC)

    _record(
        "chunks_present",
        False,
        "doc_006 not ingested after 5 min — check Cloud Logging for errors",
    )


def _check_search() -> tuple[list[dict], bool]:
    try:
        resp = _search_for_tenant(TENANT_ID, doc_ids=[DOC_ID], top_k=10)
    except Exception as exc:
        _record("search_doc006", False, str(exc))
        return [], False

    results = resp.get("results", [])
    if not results:
        _record("search_doc006", False, "no results")
        return [], False

    all_doc006 = all(r.get("doc_id") == DOC_ID for r in results)
    if not all_doc006:
        bad = {r.get("doc_id") for r in results}
        _record("search_doc006", False, f"non-doc_006 results: {bad}")
        return results, False

    _record("search_doc006", True, f"results={len(results)}")
    return results, True


def _check_page_numbers(results: list[dict]) -> None:
    if not results:
        _record("page_numbers", False, "no results to sample")
        return

    pages = {int(r.get("page_number", 0)) for r in results}
    if 0 in pages:
        _record("page_numbers", False, f"found page_number=0 in {sorted(pages)}")
        return
    if len(pages) < 1:
        _record("page_numbers", False, "no page numbers")
        return
    _record("page_numbers", True, f"distinct_pages={sorted(pages)}")


def _check_tenant_isolation() -> None:
    try:
        resp = _search_for_tenant(WRONG_TENANT, doc_ids=[DOC_ID], top_k=10)
    except Exception as exc:
        _record("tenant_isolation", False, str(exc))
        return
    results = resp.get("results", [])
    _record("tenant_isolation", len(results) == 0, f"wrong_tenant_results={len(results)}")


def main() -> int:
    verify_logs = "--verify-logs" in sys.argv

    print("IRIS Tier 3 — Single Document Cloud Run Smoke Test")
    print(f"  doc_id={DOC_ID}  tenant={TENANT_ID}")
    print()

    _check_ingest()
    _check_chunks()

    results, _ = _check_search()
    _check_page_numbers(results)
    _check_tenant_isolation()

    if verify_logs:
        _check_vlm_calls()

    print()
    failed = [name for name, ok, _ in _results if not ok]
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("All Tier 3 checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
