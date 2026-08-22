"""IRIS retrieval canary (measurement work, stage 2).

Cloud Scheduler hits this function every 15 minutes. It runs four
assertions against the live retrieval-api and logs structured results;
any failure logs at ERROR severity so a Cloud Monitoring alert on
severity>=ERROR pages a human. This exists because the reranker silently
no-op'd for weeks — the canary makes "component broken" look different
from "component off".

Assertions:
  1. livez       — the service answers and reports the Qdrant store.
  2. search      — a fixed golden query returns >=1 result, every bbox is
                   a valid normalized TOPLEFT box (top <= bottom, all in
                   0..1 — the bug class fixed in Stage 0), latency sane.
  3. rerank leg  — the same query with rerank_blend=0.3 succeeds; a
                   latency signature (>=150ms over baseline) confirms the
                   ranking call actually ran rather than silently
                   falling back. Failures inside the api log
                   rerank_failed; the latency delta catches it even if
                   logging breaks.
  4. bbox sanity — folded into (2).

Auth: the eval Firebase user (X-Firebase-Token), same as the harness.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request

RETRIEVAL_URL = os.environ.get(
    "RETRIEVAL_URL", "https://retrieval-api-zzdrfa3kqa-el.a.run.app"
)
FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "")
EVAL_EMAIL = os.environ.get("EVAL_USER_EMAIL", "eval@iris.local")
EVAL_PASSWORD = os.environ.get("EVAL_USER_PASSWORD", "")

CANARY_QUERY = "What term is used by Knudsen (2020) to describe the conversion of data from analogue to digital format?"

SEARCH_BUDGET_MS = 5_000
RERANK_DELTA_MIN_MS = 150

logger = logging.getLogger("iris-canary")
logging.basicConfig(level=logging.INFO)


def _firebase_token() -> str:
    body = json.dumps({
        "email": EVAL_EMAIL,
        "password": EVAL_PASSWORD,
        "returnSecureToken": True,
    }).encode()
    req = urllib.request.Request(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())["idToken"]


def _post(path: str, payload: dict, token: str, timeout: int = 60) -> tuple[int, dict, float]:
    t0 = time.time()
    req = urllib.request.Request(
        f"{RETRIEVAL_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Firebase-Token": token},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode()), (time.time() - t0) * 1000
    except urllib.error.HTTPError as exc:
        return exc.code, {}, (time.time() - t0) * 1000


def _valid_bbox(bbox) -> bool:
    return (
        isinstance(bbox, list)
        and len(bbox) == 4
        and all(isinstance(v, (int, float)) and 0.0 <= v <= 1.0 for v in bbox)
        and bbox[1] <= bbox[3]
        and bbox[0] <= bbox[2]
    )


def _probe_ranking_api() -> dict:
    """Call the Ranking API directly (function's own ADC): rank one relevant
    and one irrelevant record; a working ranker separates their scores."""
    import google.auth
    import google.auth.transport.requests as gauth_requests
    from urllib.error import HTTPError

    project = os.environ.get("GCP_PROJECT", "naturepivot-rag")
    location = os.environ.get("RERANK_LOCATION", "global")
    endpoint = (
        f"https://{location}-discoveryengine.googleapis.com/v1/projects/"
        f"{project}/locations/{location}/rankingConfigs/"
        "default_ranking_config:rank"
    )
    body = json.dumps({
        "model": os.environ.get("RERANK_MODEL", "semantic-ranker@latest"),
        "query": "What is the State Disaster Response Fund?",
        "records": [
            {"id": "rel", "content": "The State Disaster Response Fund provides financial assistance for disaster relief."},
            {"id": "irr", "content": "Cooking recipes for a weeknight dinner."},
        ],
    }).encode()
    try:
        creds, _ = google.auth.default()
        if not creds.valid:
            creds.refresh(gauth_requests.Request())
        req = urllib.request.Request(
            endpoint, data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {creds.token}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            records = json.loads(resp.read().decode()).get("records", [])
        scores = {r.get("id"): r.get("score", 0.0) for r in records}
        ok = scores.get("rel", 0.0) > scores.get("irr", 0.0)
        return {"ok": ok, "scores": scores}
    except HTTPError as exc:
        return {"ok": False, "error": f"HTTP {exc.code}: {exc.read()[:150]}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def run_canary(request) -> tuple[str, int]:
    results: dict[str, object] = {}
    failures: list[str] = []

    # 1. livez
    try:
        with urllib.request.urlopen(f"{RETRIEVAL_URL}/livez", timeout=30) as resp:
            body = json.loads(resp.read().decode())
            status = resp.status
        ok = status == 200 and str(body.get("store", "")).startswith("QdrantChunkStore")
        results["livez"] = {"ok": ok, "store": body.get("store")}
        if not ok:
            failures.append("livez failed")
    except Exception as exc:
        results["livez"] = {"ok": False, "error": str(exc)[:200]}
        failures.append("livez exception")

    if not FIREBASE_API_KEY or not EVAL_PASSWORD:
        results["auth"] = {"ok": False, "error": "missing FIREBASE_API_KEY/EVAL_USER_PASSWORD env"}
        failures.append("auth config missing")
        logger.error("iris_canary_failed %s", json.dumps(results))
        return "canary misconfigured", 500

    try:
        token = _firebase_token()

        # 2. search + bbox sanity
        status, body, latency_ms = _post(
            "/search", {"query": CANARY_QUERY, "mode": "standard", "top_k": 10}, token
        )
        results_json = body.get("results", [])
        bboxes_ok = all(_valid_bbox(r.get("bbox")) for r in results_json)
        search_ok = (
            status == 200
            and len(results_json) >= 1
            and bboxes_ok
            and latency_ms < SEARCH_BUDGET_MS
        )
        results["search"] = {
            "ok": search_ok,
            "status": status,
            "n_results": len(results_json),
            "bboxes_ok": bboxes_ok,
            "latency_ms": round(latency_ms),
        }
        if not search_ok:
            failures.append("search assertion failed")

        # 3. rerank leg (latency signature)
        status_r, _, latency_r_ms = _post(
            "/search",
            {"query": CANARY_QUERY, "mode": "standard", "top_k": 10, "rerank_blend": 0.3},
            token,
        )
        rerank_ok = status_r == 200 and (latency_r_ms - latency_ms) >= RERANK_DELTA_MIN_MS
        results["rerank_leg"] = {
            "ok": rerank_ok,
            "status": status_r,
            "delta_ms": round(latency_r_ms - latency_ms),
        }
        if not rerank_ok:
            failures.append("rerank leg did not run (no latency signature)")

        # 3b. direct Ranking API probe — independent engagement check of the
        # dependency itself. The latency signature catches fast-failure
        # inside retrieval-api; this catches the API being disabled,
        # permission revoked, or the model retired, even if retrieval-api
        # still adds latency for other reasons. (An order-difference
        # assertion would false-alarm: the ranker legitimately agrees with
        # hybrid ordering on many queries, including the canary query.)
        results["ranking_api"] = _probe_ranking_api()

        if not results["ranking_api"]["ok"]:
            failures.append("direct Ranking API probe failed")

    except Exception as exc:
        results["runtime"] = {"ok": False, "error": str(exc)[:200]}
        failures.append("runtime exception")

    if failures:
        logger.error("iris_canary_failed %s", json.dumps(results))
        return json.dumps({"ok": False, "failures": failures, "results": results}), 500
    logger.info("iris_canary_ok %s", json.dumps(results))
    return json.dumps({"ok": True, "results": results}), 200
