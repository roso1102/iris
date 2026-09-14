# Benchmark Result Registry

This directory is the Git-resident index of immutable IRIS benchmark evidence. Do not overwrite or “refresh” an existing run.

## Run path

```text
runs/YYYY-MM-DD/phase-X.Y/<run-id>/
```

Every run contains:

- `manifest.json` — machine-readable identity, versions, requirements, metrics and decision.
- `CHANGE.md` — human-readable description of exactly what changed and why.
- `results.json` — aggregates and confidence intervals.
- `per_example.jsonl` — redacted per-case result with fixture IDs/hashes.
- `config.json` — runtime flags, thresholds, prompt IDs and index/search settings.
- `environment.json` — container digests, machine sizes, regions and dependency versions.
- `reports/` — rendered comparison and failure analysis.
- `logs/` — sanitized benchmark logs.
- `artifacts/` — small approved visual overlays or pointers/checksums for large GCS artifacts.

## Warm-query latency runs

Use `scripts/benchmark_warm_queries.py` for a lightweight staging benchmark. It
executes authenticated `/query` calls repeatedly and records p50, p95, max,
mean, first-request latency, per-stage traces, failures, and the exact query in
the generated JSON. Store the JSON under the date/phase run directory together
with a `CHANGE.md` describing code/config changes; never include ID tokens or
raw customer document content.

Large/customer-sensitive artifacts remain in a dedicated versioned GCS benchmark bucket. The manifest stores exact object generation, checksum, classification and retention policy. Never commit tokens, raw production queries or customer documents.

## Status values

- `PLANNED`: hypothesis registered, no result.
- `RUNNING`: active run; final files not yet immutable.
- `PASS`: all hard gates and protected slices passed.
- `FAIL`: one or more hard gates failed.
- `INCONCLUSIVE`: evidence or sample size insufficient.
- `SUPERSEDED`: retained historical result; a newer run exists.

## Minimum comparison

Every behavior-changing run must name a baseline Git SHA and candidate Git SHA and include quality, latency, reliability and cost. Average-only reports are invalid.
