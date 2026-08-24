"""Tests for the answer-evidence pass hardening.

Verifies that evidence-fetch failures are TALLIED and cause a non-zero
exit (previously failures printed a warning but were silently swallowed
into empty page dicts — a failed doc could masquerade as page-placement
flags). No network is touched: the script's api_pages/pdf_pages are
monkeypatched so the failure-path logic is exercised in isolation.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "answer_evidence_pass.py"


def _load_pass(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Load answer_evidence_pass with a fake requests module, offline-safe."""
    fake_requests = types.ModuleType("requests")
    fake_requests.post = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("network call attempted in test")
    )
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setenv("EVAL_USER_PASSWORD", "EvalPass!2026x")

    spec = importlib.util.spec_from_file_location("answer_evidence_pass", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["answer_evidence_pass"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_api_failure_is_tallied_and_exits_nonzero(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    mod = _load_pass(monkeypatch)

    # api_pages: simulate the real function's failure path — record + return {}.
    def boom(doc: str) -> dict:
        mod._failures.append(("api", doc, "RuntimeError(simulated outage)"))
        return {}

    monkeypatch.setattr(mod, "api_pages", boom)
    monkeypatch.setattr(mod, "pdf_pages", lambda doc: {})  # not the path under test

    golden = [
        {"query_id": "q_xxx", "type": "t", "query": "q", "answer": "some answer text",
         "relevant_doc_ids": ["doc_001"], "relevant_page_numbers": [1]}
    ]
    monkeypatch.setattr(mod, "load_golden", lambda: golden)

    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "FETCH_FAILED" in out
    assert "simulated outage" in out


def test_pdf_failure_is_tallied(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    mod = _load_pass(monkeypatch)

    # pdf_pages failure (file missing) must be recorded, not swallowed.
    def missing(doc: str) -> dict:
        mod._failures.append(("pdf", doc, "FileNotFoundError"))
        return {}

    monkeypatch.setattr(mod, "pdf_pages", missing)
    monkeypatch.setattr(mod, "api_pages", lambda doc: {1: "page text"})

    golden = [
        {"query_id": "q_yyy", "type": "t", "query": "q", "answer": "distinctive needle text",
         "relevant_doc_ids": ["doc_999"], "relevant_page_numbers": [1]}
    ]
    monkeypatch.setattr(mod, "load_golden", lambda: golden)

    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "FETCH_FAILED" in out


def test_clean_run_exits_zero(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    mod = _load_pass(monkeypatch)

    monkeypatch.setattr(mod, "pdf_pages", lambda doc: {1: "some answer text here"})
    monkeypatch.setattr(mod, "api_pages", lambda doc: {1: "some answer text here"})

    golden = [
        {"query_id": "q_zzz", "type": "t", "query": "q", "answer": "some answer text",
         "relevant_doc_ids": ["doc_001"], "relevant_page_numbers": [1]}
    ]
    monkeypatch.setattr(mod, "load_golden", lambda: golden)

    mod.main()  # should NOT raise SystemExit
    out = capsys.readouterr().out
    assert "0 fetch failures" in out
    assert "Counts:" in out
