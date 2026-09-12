"""Phase 0.1 hermetic benchmark harness.

Runs deterministic, network-free checks against the labeled routing table and
conversation fixture and writes a schema-shaped benchmark run directory. It is
NOT a substitute for the credentialed retrieval benchmarks (Recall@5/nDCG,
memory, live HyDE precision): those remain INCONCLUSIVE here because the
`retrieval-v1` / `hyde-router-v1` datasets and provider credentials are not
available.

Usage:
    python scripts/benchmark_phase01.py [--run-id hermetic-0.1]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("MODEL_BACKEND", "mock")
os.environ.setdefault("GCP_PROJECT", "test-project")

from services.common.retrieval import hyde  # noqa: E402
from services.common.retrieval.search import _needs_rewrite, _validate_rewrite  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
PARENT_SHA = "2c56312"
REQUIREMENTS = ["RET-003", "RET-004", "RET-005", "RET-006", "SEC-009", "REL-001"]
HYDE_PRECISION_GATE = 0.95
FOLLOWUP_GATE = 0.95


def _git_sha(ref: str = "HEAD") -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", ref], cwd=str(ROOT), text=True
        ).strip()
    except Exception:
        return "unknown"


def _load_jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def eval_hyde_routing(path: Path) -> dict:
    examples = []
    correct = bypass_total = bypass_correct = invoked = invoked_eligible = 0
    for case in _load_jsonl(path):
        label = case["label"]
        reason = hyde.bypass_reason(case["query"])
        predicted = "bypass" if reason else "eligible"
        ok = predicted == label
        correct += int(ok)
        if label == "bypass":
            bypass_total += 1
            bypass_correct += int(ok)
        if predicted == "eligible":
            invoked += 1
            invoked_eligible += int(label == "eligible")
        examples.append({
            "query": case["query"],
            "label": label,
            "predicted": predicted,
            "bypass_reason": reason,
            "correct": ok,
        })
    total = len(examples)
    return {
        "metric": "hyde_routing",
        "n": total,
        "routing_accuracy": round(correct / total, 4) if total else 0.0,
        "hyde_invocation_precision": round(invoked_eligible / invoked, 4) if invoked else 1.0,
        "bypass_accuracy": round(bypass_correct / bypass_total, 4) if bypass_total else 1.0,
        "invocations": invoked,
        "gate": HYDE_PRECISION_GATE,
        "pass": (invoked_eligible / invoked if invoked else 1.0) >= HYDE_PRECISION_GATE,
        "examples": examples,
    }


def eval_conversation(path: Path) -> dict:
    examples = []
    gate_correct = 0
    total = 0
    for case in _load_jsonl(path):
        query = case["query"]
        history = case["history"]
        expected = bool(case["needs_rewrite"])
        predicted = _needs_rewrite(query, history)
        gate_ok = predicted == expected
        # Simulate an over-eager rewrite that drops the first protected token;
        # _validate_rewrite must fall back to the original query.
        preserved = True
        tokens = case.get("protected_tokens") or []
        if tokens:
            damaged = query.replace(tokens[0], "")
            decision = {
                "standalone_query": damaged,
                "preserved_entities": [],
                "document_scope": [],
                "temporal_scope": None,
                "language": "en",
                "confidence": 0.9,
                "reason": "test",
            }
            validated = _validate_rewrite(decision, query)
            preserved = validated["standalone_query"] == query
        ok = gate_ok and preserved
        gate_correct += int(ok)
        total += 1
        examples.append({
            "query": query,
            "needs_rewrite": expected,
            "predicted": predicted,
            "protected_tokens_preserved": preserved,
            "correct": ok,
        })
    accuracy = gate_correct / total if total else 0.0
    return {
        "metric": "followup_routing",
        "n": total,
        "standalone_accuracy": round(accuracy, 4),
        "gate": FOLLOWUP_GATE,
        "pass": accuracy >= FOLLOWUP_GATE,
        "examples": examples,
    }


def eval_clocks(n: int = 10000) -> dict:
    negatives = 0
    t_start = time.perf_counter()
    for _ in range(n):
        a = time.perf_counter()
        b = time.perf_counter()
        if b - a < 0:
            negatives += 1
    return {
        "metric": "monotonic_clock",
        "samples": n,
        "negative_latencies": negatives,
        "pass": negatives == 0,
        "duration_ms": round((time.perf_counter() - t_start) * 1000, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="hermetic-0.1")
    parser.add_argument(
        "--out-root",
        default=str(ROOT / "production-plan" / "benchmarks" / "runs"),
    )
    args = parser.parse_args()

    hyde_result = eval_hyde_routing(FIXTURES / "hyde_routing_table.jsonl")
    conversation_result = eval_conversation(FIXTURES / "conversation_v1.jsonl")
    clock_result = eval_clocks()

    # The phase exit gate cannot pass hermetically: recall/nDCG/memory and
    # live-HyDE precision require credentialed runs with sealed datasets.
    measured_pass = (
        hyde_result["pass"] and conversation_result["pass"] and clock_result["pass"]
    )
    status = "INCONCLUSIVE"

    today = dt.date.today().isoformat()
    run_dir = Path(args.out_root) / today / "phase-0.1" / args.run_id
    (run_dir / "reports").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)

    per_example = []
    for example in hyde_result.pop("examples"):
        per_example.append({"suite": "hyde_routing", **example})
    for example in conversation_result.pop("examples"):
        per_example.append({"suite": "followup_routing", **example})

    results = {
        "phase": "0.1",
        "status": status,
        "measured_pass": measured_pass,
        "suites": {"hyde_routing": hyde_result, "followup_routing": conversation_result,
                   "monotonic_clock": clock_result},
        "not_measured": [
            "retrieval Recall@5 / nDCG before-after (needs retrieval-v1 + credentials)",
            "HyDE eligible-slice Recall@5 lift (needs hyde-router-v1 labels)",
            "peak memory for upload and ingestion",
            "temporary-file residue count under fault injection",
        ],
    }

    manifest = {
        "phase": "0.1",
        "status": status,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "parent_git_sha": PARENT_SHA,
        "candidate_git_sha": _git_sha(),
        "requirements": REQUIREMENTS,
        "datasets": {
            "hyde_routing_table": str(FIXTURES / "hyde_routing_table.jsonl"),
            "conversation_v1": str(FIXTURES / "conversation_v1.jsonl"),
        },
        "command": "python scripts/benchmark_phase01.py",
        "decision": "INCONCLUSIVE - hermetic suites pass; credentialed quality/latency "
                    "benchmarks still required for the Phase 0.1 exit gate.",
    }
    environment = {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "model_backend": os.environ.get("MODEL_BACKEND"),
        "network": "disabled (hermetic)",
    }
    config = {
        "hyde_top_score_threshold": hyde.top_score_threshold(),
        "hyde_margin_threshold": hyde.margin_threshold(),
        "hyde_agreement_threshold": hyde.agreement_threshold(),
        "hyde_leg_weight": hyde.HYDE_LEG_WEIGHT,
    }

    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (run_dir / "environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
    (run_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    with (run_dir / "per_example.jsonl").open("w", encoding="utf-8") as handle:
        for example in per_example:
            handle.write(json.dumps(example) + "\n")
    (run_dir / "CHANGE.md").write_text(
        "# CHANGE\n\n"
        "- Hypothesis: two-stage HyDE gating + strict input/embedding validation + "
        "stable error envelope remove the Phase 0.1 crash/leak/data-state defects "
        "without regressing retrieval routing.\n"
        f"- Parent SHA: {PARENT_SHA}\n"
        f"- Candidate SHA: {manifest['candidate_git_sha']}\n"
        "- Changed: retrieval_api app, retrieval search + hyde, vertex provider, "
        "auth validation, ingestion main/chunker/store/models, ingestion worker, "
        "new errors/reliability/embeddings modules.\n"
        "- Result: hermetic suites "
        f"(routing pass={hyde_result['pass']}, follow-up pass={conversation_result['pass']}, "
        f"clock pass={clock_result['pass']}).\n"
        "- Decision: INCONCLUSIVE - credentialed retrieval/latency/memory benchmarks "
        "must be run before claiming the Phase 0.1 exit gate.\n"
        "- Rollback: revert the phase commit; no schema or cloud-resource changes.\n",
        encoding="utf-8",
    )

    print(json.dumps(results, indent=2))
    print(f"\nRun written to: {run_dir}")
    return 0 if measured_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
