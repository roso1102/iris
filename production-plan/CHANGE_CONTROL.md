# Change Control and Evidence Rules

## 1. Pull request requirements

Every production-affecting pull request must include:

- Requirement IDs and phase.
- Problem statement and falsifiable hypothesis.
- Exact code/schema/infrastructure/model/prompt/parser/index change.
- Threat-model and privacy delta.
- Tests added/changed and coverage for critical branches.
- Baseline and candidate benchmark links, or an explicit reason why the PR is behavior-neutral.
- Migration, compatibility, feature flag, rollout and rollback plan.
- Cost impact and telemetry impact.
- Dataset and model versions.

Large phases should use small independently reversible PRs. Schema readers land before writers; dual-write/backfill before activation; cleanup only after the rollback window.

## 2. Architecture decision records

Create an ADR for:

- OCR/parser vendor and lane selection.
- Embedding and reranking model.
- Qdrant topology/version or search-platform migration.
- Workflow orchestrator/ledger.
- LangGraph/LlamaIndex/LangChain adoption.
- GCP/Azure/AWS migration.
- Any change that introduces a new persistent schema, vendor, public API or security boundary.

Each ADR records alternatives, benchmark evidence, security/privacy, cost, failure modes, exit strategy and date for reconsideration.

## 3. Model and prompt change policy

- Pin a concrete model/processor version where supported.
- Give prompts stable IDs and content hashes.
- Run full protected benchmark and adversarial suite before promotion.
- Shadow first; do not overwrite the old index or artifact.
- Track retirement dates at least quarterly and alert 120/90/60/30 days before retirement.
- Model output schema changes require contract/malformed-response tests.

## 4. Data and index migration

1. Add backward-compatible reader.
2. Create new artifact/index schema.
3. Dual-write or backfill deterministically.
4. Validate record counts, hashes, ACLs, sample content and retrieval quality.
5. Switch alias/active-version pointer atomically.
6. Observe the rollback window.
7. Delete old versions only through approved retention/deletion workflow.

## 5. Progressive delivery

- Local/component → staging → offline benchmark → shadow → 5% → 25% → 50% → 100%.
- Automated abort conditions include SLO burn, authorization/citation failure, protected-slice regression, cost anomaly, retry storm and memory saturation.
- Rollback must not require destructive migration or re-ingestion.
- Each phase includes at least one executed rollback drill.

## 6. Benchmark evidence review

A reviewer must be able to answer from committed artifacts:

1. What exactly changed?
2. What was the baseline?
3. Was the same dataset/environment used?
4. Which metrics improved/regressed and with what uncertainty?
5. Did any protected language/document/security slice regress?
6. What did it cost?
7. What happened under provider failure?
8. Can it be rolled back without data loss?

If any answer is unavailable, the phase is incomplete.

## 7. Exception policy

Emergency P0 fixes may precede a full benchmark only when exploitation/data loss/outage risk is active. They still require targeted tests, an owner, feature flag or reversible commit, and retrospective benchmark within two business days. No exception may weaken tenant/document authorization or evidence validation.
