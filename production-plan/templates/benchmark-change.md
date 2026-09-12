# Benchmark Change Description

## Identity

- Run ID:
- Phase and requirements:
- Owner:
- Baseline Git SHA:
- Candidate Git SHA:
- Dataset name/version/hash/partition:
- Related PR/ADR:

## Hypothesis

State one falsifiable prediction, including the expected quality, latency, resilience or cost delta.

## Exactly what changed

List code paths, schemas, feature flags, prompts, models/processors, index configuration, infrastructure and dependencies. Include previous and candidate values for every tuned threshold.

## What did not change

List controlled variables so the comparison can be interpreted.

## Expected benefit and risk

Describe protected slices and likely failure modes before viewing results.

## Test and benchmark procedure

Commands, environment, workload shape, warm-up, repetitions, statistical method and artifact locations.

## Results

Include baseline/candidate/delta/confidence interval for quality, latency, reliability, resource use and cost. Link per-example failures and overlays.

## Protected-slice review

Language, document type, scan/handwriting, query type, tenant size and security/adversarial results.

## Decision

`PASS | FAIL | INCONCLUSIVE`, rationale, approvers, rollout stages and automated abort conditions.

## Rollback

Flag/alias/deployment action, data compatibility, expected recovery time and rollback-drill evidence.
