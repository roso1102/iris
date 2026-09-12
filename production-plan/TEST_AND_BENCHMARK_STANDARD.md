# Test and Benchmark Standard

## 1. Purpose

Every phase must produce reproducible evidence of what changed and whether quality, latency, reliability, security, and cost improved or regressed. Tests establish correctness; benchmarks establish measured behavior. Neither substitutes for the other.

## 2. Test pyramid

### Level 1 — Hermetic unit tests

- No network, cloud credentials, model downloads, clock dependence, or shared mutable state.
- Fake clock for retry/rate-limit/session-order tests.
- Contract fixtures for Vertex, Document AI, Qdrant, Firestore, Pub/Sub, GCS, rerankers, and authentication.
- Property tests for bbox transforms, deterministic IDs, chunk boundaries, filters, RRF, MMR, retry classification, and model-output parsing.
- Mutation testing for authorization, idempotency, completion barrier, citation validation, and route allowlisting.

### Level 2 — Component tests

- Run real service code against local/emulated dependencies.
- Firestore emulator, Qdrant container, fake GCS/Pub/Sub or approved emulators.
- Verify schema migrations, atomic turns, version activation, deletion saga and replay.

### Level 3 — Provider contract tests

- Small, budgeted live suite against pinned OCR/model/reranking versions.
- Redacted fixtures only.
- Record provider region, request options, response schema hash, rate-limit behavior, cost and latency.
- Scheduled nightly/weekly, not required for every developer unit run.

### Level 4 — Offline quality benchmarks

- Retrieval, follow-up, HyDE routing, OCR, bbox, table, answer grounding, multilingual and adversarial datasets.
- Candidate and baseline run on the exact same immutable dataset version.
- Store per-example results, not only aggregates.

### Level 5 — Load, soak, failure and recovery

- k6 or Locust for API load; a dedicated workload driver for 5,000-page ingestion.
- Fault injection for 429, 500, timeout, connection reset, partial embedding response, malformed provider output, duplicate delivery, out-of-order delivery and instance termination.
- Soak test checks memory growth, stale sessions, rate-limit state and connection/resource leakage.

### Level 6 — Security and privacy

- Tenant and document ACL matrix.
- Prompt-injection, poisoned metadata, malicious filenames, malformed JWT, object-path escape and citation forgery.
- PII logging, retention and deletion verification.
- SAST, dependency, image, IaC, secret and DAST scans.

## 3. Versioned benchmark datasets

| Dataset | Minimum composition | Purpose |
|---|---|---|
| `retrieval-v1` | >= 300 held-out queries across direct, quote, ID, multi-hop, table, summary, scan and multilingual | Recall, nDCG, MRR, diversity |
| `conversation-v1` | >= 200 conversations, 3–8 turns, ellipsis/coreference/entity/date/doc-switch cases | Follow-up resolution and routing |
| `hyde-router-v1` | >= 300 queries labeled `never`, `eligible`, `required`, with expected rationale | HyDE invocation precision and value |
| `ocr-spatial-v1` | >= 300 annotated pages: digital, printed scans, Hindi/regional, handwriting, rotated/skewed, tables | OCR, reading order and bbox |
| `grounding-v1` | >= 250 answer/evidence sets including insufficient/conflicting evidence | Faithfulness, citations, abstention |
| `security-v1` | >= 150 direct/indirect injection, ACL, PII and malformed-input cases | Security regression |
| `scale-v1` | 50 documents × >=100 pages with representative mixtures | Throughput, recovery, cost and capacity |

Datasets are split into development, validation and sealed held-out partitions. No prompt, threshold or model decision may be tuned on the sealed partition. Dataset manifests contain content hashes, license/data-usage status, language/document-type labels and adjudication history.

## 4. Metrics

### Retrieval

- Recall@1/3/5/10 at document, page and chunk levels.
- Precision@5, MRR and nDCG@10.
- Query coverage and top-1/top-2 score margin.
- Results-per-document distribution and duplicate-content rate.
- Metrics sliced by language, script, scan quality, table, query length, follow-up, document count and retrieval route.

### Conversation and routing

- Standalone-query exact semantic accuracy.
- Entity, temporal-scope and document-scope preservation F1.
- Route macro-F1 and expected calibration error.
- HyDE invocation precision/recall and invocation rate.
- HyDE eligible-slice retrieval lift and hallucinated-entity rate.
- Decomposition correctness and unnecessary-decomposition rate.

### OCR and layout

- Character Error Rate and Word Error Rate per language/script.
- Word and line polygon IoU, center-point containment and text-weighted coverage.
- Reading-order Kendall tau.
- Table cell value F1, row/column association F1 and header-link accuracy.
- Rotation/skew/crop transform error in pixels at the standard render DPI.

### Generation

- Claim-level faithfulness and answer correctness.
- Citation precision, coverage, entailment and invalid-ID count.
- Abstention precision/recall.
- Unsupported numeric/date/entity claim rate.
- Ragas/TruLens results may supplement, but cannot replace deterministic and human-adjudicated metrics.

### Performance/reliability/cost

- P50/P95/P99 latency and time-to-first-byte.
- Throughput, saturation, queue age, retries, fallback rate and error rate.
- Duplicate active chunks, lost pages, terminal failures and recovery time.
- Peak/steady memory and CPU.
- Tokens, embedding inputs, OCR pages, reranker documents and billed/estimated cost by stage.

## 5. Statistical decision rules

- Compare candidate and baseline on identical samples and configuration except the named change.
- Use paired bootstrap 95% confidence intervals for retrieval/generation deltas.
- Use Wilson intervals for rates such as route accuracy and bbox containment.
- Report median plus P95/P99; never publish only the mean.
- A release passes only if hard gates pass and the confidence interval excludes an unacceptable regression.
- Protected slices require minimum sample sizes. If a slice is too small, the conclusion is “insufficient evidence,” not “pass.”
- Any flaky test is a defect. Quarantine requires owner, reason, issue and expiry date.

## 6. Immutable artifact layout

Each run is stored at:

```text
production-plan/benchmarks/runs/
  YYYY-MM-DD/
    phase-X.Y/
      <run-id>/
        manifest.json
        CHANGE.md
        results.json
        environment.json
        config.json
        per_example.jsonl
        reports/
        logs/
        artifacts/
```

Required fields appear in `templates/benchmark-manifest.json`. `CHANGE.md` states the hypothesis, exact change, files/components affected, before/after SHAs, feature flags, expected trade-off, risks, result, decision and rollback procedure.

Large raw artifacts go to a versioned benchmark GCS bucket with retention lock where appropriate. Git stores the manifest, redacted aggregate/per-example measurements, report, and immutable GCS object generation/checksum. Do not commit customer documents or secrets.

## 7. Phase benchmark workflow

1. Register hypothesis and acceptance criteria before implementation.
2. Run and store the baseline against the parent SHA.
3. Implement behind a flag with unit/component coverage.
4. Run candidate against the same dataset and environment.
5. Generate a paired comparison and cost delta.
6. Review protected slices and failure examples.
7. Record `PASS`, `FAIL`, or `INCONCLUSIVE`—never edit the result later.
8. Deploy to staging, then shadow/canary if permitted.
9. Run rollback drill.
10. Commit the phase result and update the program index.

## 8. CI gates

- Pull request: format/lint/type/unit/component/schema/secret/SAST/dependency/IaC tests and a small deterministic quality smoke set.
- Main/staging: full offline benchmark, container scan, SBOM/signing, integration and migration tests.
- Nightly: provider contracts, larger quality set and adversarial suite.
- Weekly: load/soak, cost comparison and restore verification.
- Before model/parser/index promotion: full sealed held-out, security and rollback suite.

## 9. Benchmark description example

```markdown
# CHANGE

- Hypothesis: confidence-gated HyDE reduces HyDE calls by 70% without lowering Recall@5.
- Baseline SHA: abc123
- Candidate SHA: def456
- Dataset: hyde-router-v1@sha256:...
- Changed: query classifier, baseline-confidence gate, HyDE structured output parser.
- Expected risk: short conceptual questions may no longer expand.
- Result: invocation 82% → 19%; eligible Recall@5 +3.8pp; overall nDCG +0.4pp; P95 -410ms.
- Decision: PASS; promote at 10%, 50%, 100% with rollback on protected-slice regression.
```
