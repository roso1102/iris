# IRIS Production Engineering Program

**Status:** Proposed implementation plan  
**Baseline date:** 2026-09-07  
**Scope:** Current working tree, ingestion, retrieval, security, reliability, observability, cost, OCR, spatial citations, deployment, and continuous evaluation.

This plan supersedes `ACTIONPLAN.md` for production-remediation sequencing. `ACTIONPLAN.md` remains useful historical context, but its completion markers must not be treated as current production evidence. A phase in this program is complete only when its code, tests, benchmark run, change description, security review, rollback evidence, and exit criteria have all been committed.

## Plan files

- [`production-plan/REQUIREMENTS.md`](production-plan/REQUIREMENTS.md) — functional, non-functional, security, data, cost, and acceptance requirements.
- [`production-plan/PHASES.md`](production-plan/PHASES.md) — executable Phase 0.0 through 12.0 implementation sequence.
- [`production-plan/TEST_AND_BENCHMARK_STANDARD.md`](production-plan/TEST_AND_BENCHMARK_STANDARD.md) — mandatory test pyramid, datasets, metrics, statistical rules, and artifact retention.
- [`production-plan/OCR_BBOX_DECISION.md`](production-plan/OCR_BBOX_DECISION.md) — verified Google Document AI geometry design and Docling/PyMuPDF decision gate.
- [`production-plan/OBSERVABILITY_SECURITY_COST.md`](production-plan/OBSERVABILITY_SECURITY_COST.md) — OpenTelemetry, SLOs, security controls, privacy, rate limits, resilience, and cost governance.
- [`production-plan/CHANGE_CONTROL.md`](production-plan/CHANGE_CONTROL.md) — pull-request, benchmark, rollout, rollback, and architectural-decision rules.
- [`production-plan/FILE_CHANGE_MAP.md`](production-plan/FILE_CHANGE_MAP.md) — current files to modify/delete and proposed production modules.
- [`production-plan/benchmarks/README.md`](production-plan/benchmarks/README.md) — benchmark result directory convention.
- [`production-plan/benchmarks/baseline-2026-09-07.md`](production-plan/benchmarks/baseline-2026-09-07.md) — evidence available before implementation begins.
- [`production-plan/templates/phase-result.md`](production-plan/templates/phase-result.md) — phase completion record.
- [`production-plan/templates/benchmark-change.md`](production-plan/templates/benchmark-change.md) — required human-readable explanation for each benchmark.
- [`production-plan/templates/benchmark-manifest.json`](production-plan/templates/benchmark-manifest.json) — machine-readable run manifest.

## Non-negotiable execution rules

1. Complete phases in order unless an emergency P0 security or availability defect requires a separately documented exception.
2. Every behavior change is behind a feature flag until its phase benchmark passes in staging.
3. Every benchmark stores the changed behavior, before/after Git SHAs, dataset version, configuration, model versions, infrastructure, raw measurements, aggregate results, cost, conclusion, and rollback decision.
4. Never overwrite benchmark results. Runs are immutable and append-only.
5. No claim such as “bbox fixed,” “multilingual supported,” or “production-ready” is valid without a committed benchmark artifact.
6. All model, parser, chunker, schema, prompt, OCR processor, and index changes are versioned. Existing document versions remain readable until migration is verified.
7. No phase may improve average quality by silently regressing tenant isolation, P95/P99 latency, cost ceilings, failure recovery, or a protected language/document slice.
8. Benchmark credentials and document contents must not be stored in run artifacts. Store hashes, redacted samples, metrics, and approved test fixtures only.

## Program outcomes

At completion, IRIS will provide:

- Durable, idempotent, replayable, versioned document ingestion.
- Correct word/line/polygon provenance for digital and scanned PDFs.
- Printed and handwritten multilingual OCR, including Hindi and selected regional scripts.
- Adaptive retrieval where HyDE, decomposition, rewrite, and reranking are invoked only when justified.
- Reliable multi-turn entity/document/time resolution.
- Document-level authorization, PII policy enforcement, prompt-injection defenses, and auditable access.
- OpenTelemetry traces, actionable SLOs, dependency health, cost attribution, and tested disaster recovery.
- Reproducible unit, integration, quality, load, security, chaos, and cost benchmarks at every phase.

## Phase summary

| Phase | Outcome | Hard gate |
|---|---|---|
| 0.0 | Baseline, governance, secrets, reproducible tests | Known failures captured; unit suite hermetic |
| 0.1 | Immediate correctness and security hotfixes | Query crash and state/validation P0s eliminated |
| 1.0 | Contracts, versioning, feature flags | Strict schemas and compatibility tests pass |
| 2.0 | OpenTelemetry and SRE foundations | Trace completeness and SLO dashboards verified |
| 3.0 | Durable ingestion control plane | Idempotency, retry, DLQ, and completion chaos tests pass |
| 4.0 | OCR/layout/bbox proof of capability | Vendor bake-off meets spatial and multilingual gates |
| 5.0 | Production ingestion implementation | 5,000-page workload completes without loss/duplication |
| 6.0 | Vector/index resilience and data lifecycle | HA, backup/restore, version switch, delete reconciliation pass |
| 7.0 | Follow-up memory and adaptive query planning | Multi-turn and HyDE-routing gates pass |
| 8.0 | Retrieval, routing, and reranking | Held-out retrieval lift with bounded latency/cost |
| 9.0 | Grounded synthesis and application security | Claim-level grounding and adversarial isolation gates pass |
| 10.0 | Cost and performance optimization | Cost ceilings met with no protected-slice regression |
| 11.0 | Scale, resilience, DR, and rollout | Load, fault, restore, canary, and rollback drills pass |
| 12.0 | GA governance and continuous improvement | Error budget, audit, runbooks, and release evidence accepted |

## Immediate decisions

- **Do not perform a big-bang LangChain/LlamaIndex rewrite.** Preserve the existing provider and store boundaries. LangGraph may be evaluated in Phase 7.0 for query orchestration only.
- **Do not use Gemini plain-text OCR as a bbox source.** It has no span geometry contract.
- **Use a dual ingestion lane.** PyMuPDF is the default for clean digital PDFs; Google Enterprise Document OCR is the leading candidate for scans/handwriting; Docling remains an optional complex-layout/table or private-processing lane until Phase 4.0 data decides.
- **Do not use Google Layout Parser chunks as the canonical spatial source without a pinned supported processor version and successful geometry benchmark.** Use Enterprise OCR word/line polygons for canonical scan geometry and optionally merge Layout Parser hierarchy.
- **Stay on GCP during remediation.** Cloud migration is not a fix for the current correctness problems. Introduce cloud ports before reconsidering Azure or AWS.

## Definition of production-ready

Production-ready means every Phase 0.0–11.0 exit criterion has passed, there are no unresolved P0/P1 findings, model retirement has been addressed, two restore drills have succeeded, tenant/document isolation has been penetration-tested, the protected evaluation slices meet their thresholds, and the production release has a tested automated rollback.
