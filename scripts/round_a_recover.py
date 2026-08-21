"""Round A recovery: retrigger /ingest for docs whose upload-trigger 429'd.

The PDFs are already in GCS (the upload wrote them before the trigger
failed), so this calls the ingestion-worker /ingest endpoint directly with
SA impersonation, retrying on 429 (Vertex per-minute quota on the trial
account) with a 75s backoff.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("EVAL_USER_PASSWORD", "EvalPass!2026x")

import requests  # noqa: E402

from scripts.eval_phase2 import (  # noqa: E402
    INGEST_SA,
    INGEST_URL,
    TENANT_ID,
    _id_token,
    _log,
)

DOCS = sys.argv[1:] or ["doc_003", "doc_004", "doc_005", "doc_007"]

MAX_ATTEMPTS = 5
BACKOFF_S = 75


def main() -> None:
    failed = []
    for doc_id in DOCS:
        gcs_uri = f"gs://iris-raw-pdfs/{TENANT_ID}/{doc_id}.pdf"
        done = False
        for attempt in range(1, MAX_ATTEMPTS + 1):
            token = _id_token(INGEST_SA, INGEST_URL)
            resp = requests.post(
                f"{INGEST_URL}/ingest",
                headers={"Authorization": f"Bearer {token}"},
                json={"gcs_uri": gcs_uri, "tenant_id": TENANT_ID, "doc_id": doc_id},
                timeout=300,
            )
            if resp.status_code == 200:
                _log(f"{doc_id}: ingest ok -> {resp.json().get('status', resp.text[:80])}")
                done = True
                break
            _log(
                f"{doc_id}: attempt {attempt} HTTP {resp.status_code}: {resp.text[:100]}"
            )
            if resp.status_code == 429 and attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_S)
        if not done:
            failed.append(doc_id)

    if failed:
        print(f"STILL FAILED: {failed}")
        sys.exit(1)
    print("All recovered docs triggered.")


if __name__ == "__main__":
    main()
