# Staging canary — 2026-09-13

## Context

- Project: `procambrian-iris-staging-2026`
- Input: `trueassort/doc_001.pdf`
- Commit under test: `4b0c436a12234c3376eca79a6d6ba847e7dd8254`
- Runner: Windows developer environment (not the authoritative Linux fork gate)

## Results

Embedding, batch embedding, synthesis, rewrite, router, reranker, vision/OCR,
and document summary completed successfully. Observed latencies were 12.77s,
0.45s, 2.42s, 2.20s, 0s, 7.53s (2 retries), 7.36s, and 3.17s respectively.
No orphan children or invalid embeddings were reported.

The first report exposed an incompatible Vertex response-schema keyword,
`maxItems`, in the HyDE and router schemas. The keyword has been removed and
the focused HyDE/provider suite passes (30/30). A fresh authoritative canary
must be rerun on Ubuntu after the follow-up commit is built.

## Status

`INCONCLUSIVE — staging deployment and end-to-end smoke test not run.`

The GitHub deployment environment currently has no configured Workload
Identity secrets, so no Cloud Run deployment was attempted. This report must
not be treated as production approval.
