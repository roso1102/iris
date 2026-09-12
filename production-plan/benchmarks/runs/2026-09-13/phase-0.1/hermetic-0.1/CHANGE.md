# CHANGE

- Hypothesis: two-stage HyDE gating + strict input/embedding validation + stable error envelope remove the Phase 0.1 crash/leak/data-state defects without regressing retrieval routing.
- Parent SHA: 2c56312
- Candidate SHA: 2c56312158fee030cfcd4b7a3fad207597a463cc
- Changed: retrieval_api app, retrieval search + hyde, vertex provider, auth validation, ingestion main/chunker/store/models, ingestion worker, new errors/reliability/embeddings modules.
- Result: hermetic suites (routing pass=True, follow-up pass=True, clock pass=True).
- Decision: INCONCLUSIVE - credentialed retrieval/latency/memory benchmarks must be run before claiming the Phase 0.1 exit gate.
- Rollback: revert the phase commit; no schema or cloud-resource changes.
