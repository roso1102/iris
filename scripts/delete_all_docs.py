"""Delete all documents for a tenant via the API.

Usage:
    python scripts/delete_all_docs.py [--dry-run]

Cascades: Qdrant chunks → GCS blob → Firestore ownership record.
"""

import os
import sys
import time
import urllib.request
import json

os.environ.setdefault("EVAL_USER_PASSWORD", "EvalPass!2026x")
os.environ.setdefault("FIREBASE_CONFIG", "naturepivot-rag")

API_URL = os.environ.get("RETRIEVAL_URL", "https://retrieval-api-zzdrfa3kqa-el.a.run.app")


def _firebase_id_token():
    """Mint a Firebase ID token for the eval user."""
    api_key = os.environ.get("FIREBASE_API_KEY")
    if not api_key:
        # Read from gcloud secret
        import subprocess
        try:
            result = subprocess.run(
                ["gcloud", "secrets", "versions", "access", "latest",
                 "--secret=FIREBASE_CONFIG", "--project=naturepivot-rag"],
                capture_output=True, text=True, timeout=10
            )
            config = json.loads(result.stdout)
            api_key = config.get("apiKey", "")
        except Exception:
            pass

    email = os.environ.get("EVAL_USER_EMAIL", "rohit.soni@naturepivot.com")
    password = os.environ.get("EVAL_USER_PASSWORD", "RohitPC2026")

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())["idToken"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Auth failed: {e.code} {body[:200]}")
        sys.exit(1)


def _api_get(path, token):
    url = f"{API_URL}{path}"
    req = urllib.request.Request(url, headers={"X-Firebase-Token": token})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def _api_delete(path, token):
    url = f"{API_URL}{path}"
    req = urllib.request.Request(url, method="DELETE", headers={"X-Firebase-Token": token})
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}


def main():
    dry_run = "--dry-run" in sys.argv

    print("Minting Firebase ID token...")
    token = _firebase_id_token()
    print("Token obtained.\n")

    print("Fetching document list...")
    data = _api_get("/documents", token)
    docs = data.get("documents", [])
    print(f"Found {len(docs)} documents.\n")

    if not docs:
        print("Nothing to delete.")
        return

    for doc in docs:
        doc_id = doc["doc_id"]
        chunks = doc.get("chunk_count", 0)
        pages = doc.get("page_count", 0)
        print(f"  {doc_id}: {pages} pages, {chunks} chunks", end="")

        if dry_run:
            print(" [DRY RUN]")
            continue

        result = _api_delete(f"/documents/{doc_id}", token)
        if "error" in result:
            print(f" → FAILED: {result['error'][:80]}")
        else:
            deleted = result.get("deleted_chunks", 0)
            print(f" → deleted {deleted} chunks")
        time.sleep(0.5)  # rate limit courtesy

    print(f"\nDone. {'[DRY RUN - nothing deleted]' if dry_run else 'All documents deleted.'}")


if __name__ == "__main__":
    main()
