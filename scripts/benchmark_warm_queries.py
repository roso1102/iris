"""Measure warm authenticated query latency and persist a reproducible report.

Usage (staging only):
  $env:FIREBASE_ID_TOKEN = "..."
  python scripts/benchmark_warm_queries.py --url https://... --query "..." \
      --doc-id doc_001 --runs 20 --out production-plan/benchmarks/runs/...
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import requests


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p / 100.0
    lo, hi = int(rank), min(int(rank) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (rank - lo)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="retrieval-api base URL")
    ap.add_argument("--query", required=True)
    ap.add_argument("--doc-id", action="append", dest="doc_ids", default=[])
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()
    token = os.getenv("FIREBASE_ID_TOKEN")
    if not token:
        ap.error("FIREBASE_ID_TOKEN is required")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = args.url.rstrip("/") + "/query"
    latencies: list[float] = []
    traces: list[dict] = []
    errors: list[dict] = []
    for i in range(max(1, args.runs)):
        payload = {"query": args.query, "doc_ids": args.doc_ids or None, "trace": True}
        started = time.perf_counter()
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=args.timeout)
            elapsed = (time.perf_counter() - started) * 1000.0
            if response.ok:
                latencies.append(elapsed)
                body = response.json()
                traces.append(body.get("trace") or {})
            else:
                errors.append({"run": i + 1, "status": response.status_code, "body": response.text[:500]})
        except Exception as exc:  # noqa: BLE001
            errors.append({"run": i + 1, "error": type(exc).__name__})
    report = {
        "description": "Repeated warm-query latency benchmark; first run is retained separately.",
        "url": args.url,
        "query": args.query,
        "runs_requested": args.runs,
        "runs_succeeded": len(latencies),
        "runs_failed": len(errors),
        "latency_ms": {
            "p50": round(percentile(latencies, 50), 1),
            "p95": round(percentile(latencies, 95), 1),
            "max": round(max(latencies), 1) if latencies else 0.0,
            "mean": round(statistics.mean(latencies), 1) if latencies else 0.0,
            "first": round(latencies[0], 1) if latencies else 0.0,
        },
        "stage_traces": traces,
        "errors": errors,
        "generated_at_epoch": time.time(),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["latency_ms"], indent=2))
    return 0 if latencies else 1


if __name__ == "__main__":
    raise SystemExit(main())
