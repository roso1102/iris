# Phase 0.2 — latency and provider reliability changes

Status: PLANNED (implementation verified hermetically; live staging benchmark pending).

Changes in this candidate:

- Google Gen AI provider path with native HTTP deadlines; Vertex calls no longer
  use process isolation. Legacy SDK remains only as an explicit local fallback
  (`IRIS_USE_GOOGLE_GENAI=0`).
- Single-document routing bypass, deterministic summary intent, 60 KB context
  cap, 1,536 output-token default, and six-chunk standard synthesis cap.
- Route/embed/HyDE generation/HyDE embedding/rerank/synthesis timing fields and
  reliability attempt/timeout logs.
- Added `scripts/benchmark_warm_queries.py` for authenticated repeated warm
  queries. It records p50/p95/max/mean/first latency and stage traces.

Run against staging only after deployment:

```powershell
$env:FIREBASE_ID_TOKEN = "<short-lived-token>"
python scripts/benchmark_warm_queries.py `
  --url https://retrieval-api-<staging>.a.run.app `
  --query "what is this document about" --doc-id <doc-id> --runs 20 `
  --out production-plan/benchmarks/runs/2026-09-14/phase-0.2/staging-warm.json
```

Do not commit tokens, raw customer documents, or unredacted response text.
