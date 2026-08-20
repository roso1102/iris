#!/usr/bin/env python
"""Backfill Firestore ownership records via REST (no ADC required).

Uses a gcloud user access token (passed via GCLOUD_ACCESS_TOKEN or the
--token arg) against the Firestore REST API:
    PATCH /v1/projects/{project}/databases/(default)/documents/tenants/{t}/documents/{d}

Creates missing records only — never overwrites existing documents.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

PROJECT = "naturepivot-rag"
BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"
DEFAULT_DOCS = [f"doc_{i:03d}" for i in range(1, 9)]


def _request(method: str, url: str, token: str, body: dict | None = None):
    req = urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body).encode() if body else None,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default="test-tenant")
    parser.add_argument("--docs", nargs="*", default=DEFAULT_DOCS)
    parser.add_argument("--token", default=os.environ.get("GCLOUD_ACCESS_TOKEN", ""))
    args = parser.parse_args()

    if not args.token:
        print("ERROR: --token (or GCLOUD_ACCESS_TOKEN) is required", file=sys.stderr)
        return 1

    created = 0
    existing = 0
    failed = []

    for doc_id in args.docs:
        # Read first (REST document GET) to avoid overwriting.
        path = f"tenants/{args.tenant}/documents/{doc_id}"
        url = f"{BASE}/{path}"
        try:
            _request("GET", url, args.token)
            existing += 1
            print(f"  exists (skip): {doc_id}")
            continue
        except Exception:
            pass  # not found -> create below

        payload = {
            "fields": {
                "doc_id": {"stringValue": doc_id},
                "tenant_id": {"stringValue": args.tenant},
                "status": {"stringValue": "ready"},
                "filename": {"stringValue": f"{doc_id}.pdf"},
            }
        }
        fields = ["doc_id", "tenant_id", "status", "filename"]
        mask = "&".join(f"updateMask.fieldPaths={f}" for f in fields)
        try:
            _request("PATCH", f"{url}?{mask}", args.token, payload)
            created += 1
            print(f"  created: {doc_id}")
        except Exception as exc:
            failed.append((doc_id, str(exc)))
            print(f"  FAILED: {doc_id}: {exc}")

    print(f"Done: {created} created, {existing} existing, {len(failed)} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
