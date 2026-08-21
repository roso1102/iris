"""Round A wipe + re-ingest for the golden docs (Stage 0 GCP gate).

For each doc_001..doc_008 under test-tenant:
  1. DELETE /documents/{doc_id}  — clears Qdrant points (the hash cache),
     the Firestore ownership record, and the GCS blob (cascading delete).
  2. POST /documents/upload with the local trueassort/{doc_id}.pdf —
     re-writes GCS, recreates the ownership record, and triggers the
     ingestion-worker (preflight + split + Pub/Sub fan-out).

The delete cascade removes the GCS blob, which is why the re-upload from
the local copies is required (the eval harness's plain /ingest trigger
would 404 on a missing blob).

Auth: eval Firebase user JWT (X-Firebase-Token) for retrieval-api; worker
warm-up via ingestion-worker-sa impersonation (cold start would exceed the
upload path's internal 120s trigger timeout).
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
    DOC_IDS,
    INGEST_SA,
    INGEST_URL,
    RETRIEVAL_URL,
    _id_token,
    _log,
    _retrieval_headers,
)


def warm_worker() -> None:
    token = _id_token(INGEST_SA, INGEST_URL)
    t0 = time.time()
    resp = requests.get(
        f"{INGEST_URL}/livez", headers={"Authorization": f"Bearer {token}"}, timeout=300
    )
    _log(f"worker warm-up: {resp.status_code} in {time.time() - t0:.0f}s")


def main() -> None:
    warm_worker()

    failures = []
    for doc_id in DOC_IDS:
        pdf = ROOT / "trueassort" / f"{doc_id}.pdf"
        if not pdf.exists():
            failures.append((doc_id, f"missing local pdf {pdf}"))
            continue

        t0 = time.time()
        dele = requests.delete(
            f"{RETRIEVAL_URL}/documents/{doc_id}",
            headers=_retrieval_headers(),
            timeout=120,
        )
        if dele.status_code not in (200, 404):
            failures.append((doc_id, f"delete HTTP {dele.status_code}: {dele.text[:120]}"))
            continue

        with pdf.open("rb") as fh:
            up = requests.post(
                f"{RETRIEVAL_URL}/documents/upload",
                headers=_retrieval_headers(),
                files={"file": (pdf.name, fh, "application/pdf")},
                data={"doc_id": doc_id},
                timeout=300,
            )
        try:
            body = up.json()
        except Exception:
            body = up.text[:120]
        ok = up.status_code == 200
        _log(
            f"{doc_id}: delete={dele.status_code} upload={up.status_code} "
            f"({time.time() - t0:.0f}s) {body if not ok else body.get('status')}"
        )
        if not ok:
            failures.append((doc_id, f"upload HTTP {up.status_code}: {body}"))

    if failures:
        print("\nFAILURES:")
        for doc_id, why in failures:
            print(f"  {doc_id}: {why}")
        sys.exit(1)
    print("\nAll 8 docs re-uploaded and ingestion triggered.")


if __name__ == "__main__":
    main()
