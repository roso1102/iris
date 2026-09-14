# Staging smoke benchmark — 2026-09-14

## Change under test

- Deployment workflow: `34839464912` (merged `main`, revision includes PR #19).
- Terraform apply added the Firestore `messages` composite index and restored
  the two required least-privilege bindings (worker topic publisher and
  retrieval-to-worker service-account token creator).
- PR #19 normalizes Firestore `DocumentSnapshot` values with `to_dict()` before
  reading session messages. This fixes real follow-up queries that previously
  returned `SESSION_STORE_UNAVAILABLE`.

## Results

| Check | Result | Evidence |
|---|---|---|
| Retrieval `/livez` | PASS | HTTP 200 |
| Unauthenticated `/query` | PASS | HTTP 401 |
| Authenticated upload | PASS | `smoke_20260913`, 4 pages, 29 chunks |
| Pub/Sub fan-out / worker | PASS | ingestion completed; Qdrant accepted UUID point IDs |
| Initial authenticated query | PASS | 5 citations; standard mode; ~15.5 s client latency |
| Follow-up with same session | PASS | session history loaded; answer returned; same session ID |
| HyDE normal query | PASS | baseline weak, `used=false` for smoke follow-up; no extra HyDE cost |
| HyDE exact-identifier query | PASS | `eligible=false`, `used=false`, `bypass_reason=exact_identifier`, 0 ms / $0 estimated HyDE cost |
| Citations / bbox schema | PASS | normalized `[x0,y0,x1,y1]` values in range; page numbers present |
| Firebase auth isolation | PASS | unauthenticated request rejected |

## Observed timings

- Follow-up query: `latency_ms=77,751.85`; synthesis dominated at `65,078.1 ms`.
- Exact-identifier query: `latency_ms=130,296.43`; HyDE itself was bypassed.
- Search legs remained fast (~228 ms), so current latency bottleneck is model
  synthesis, not Qdrant or Firestore reads.

## Limitations and follow-ups

- This smoke confirms bbox validity and propagation, not visual pixel-level
  accuracy. Several citations are page/vision-derived and cluster on page 1;
  a manual bbox overlay review is still required for scanned PDFs.
- The temporary Domain Restricted Sharing “Allow all” override remains active;
  remove it after confirming the billing/Pub/Sub policy exception path and then
  rerun the Pub/Sub health check.
- Add a latency budget/circuit breaker for synthesis before production; the
  observed 65–130 s synthesis times are too high for interactive SLOs.
