"""Credentialed Linux canary for every real Vertex operation.

Invokes each operation individually through the production provider and records,
per operation: latency, result validity, retry count, child exit state, memory
delta and a correlation id. It fails (non-zero exit) on any of:

  * an "unpicklable outcome" error crossing the isolation pipe;
  * a fork / gRPC warning;
  * a deadline overrun beyond the operation's configured overall deadline;
  * an orphan (surviving) child process;
  * an invalid embedding.

This is the only test that can establish that real Vertex calls (initialized
gRPC clients, auth state, cached models) behave safely under fork. It must run
inside a credentialed Linux container:

    GCP_PROJECT=... python scripts/canary_vertex_ops.py --pdf sample.pdf
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import math
import multiprocessing
import os
import sys
import time
import uuid
import warnings

try:
    import resource  # Unix-only; the canary targets Linux containers
except ImportError:  # pragma: no cover - Windows dev
    resource = None  # type: ignore[assignment]
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_DEADLINE_TOLERANCE = 1.15  # 15% headroom before a call counts as an overrun


@dataclass
class OpRecord:
    name: str
    correlation_id: str
    ok: bool = False
    skipped: bool = False
    latency_ms: float = 0.0
    deadline_s: float = 0.0
    retries: int = 0
    children_before: int = 0
    children_after: int = 0
    memory_delta_mb: float = 0.0
    detail: str = ""


class _RetryCounter(logging.Handler):
    """Counts reliability-layer retry warnings, attributed to the current op."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.counts: dict[str, int] = {}
        self.current: Optional[str] = None

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return
        if "retry operation=" in message and self.current:
            self.counts[self.current] = self.counts.get(self.current, 0) + 1


def _rss_mb() -> float:
    if resource is None:  # non-Unix: memory delta is not measurable
        return 0.0
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def _valid_vector(vec: Any, dim: int = 768) -> bool:
    if not vec or len(vec) != dim:
        return False
    try:
        floats = [float(x) for x in vec]
    except (TypeError, ValueError):
        return False
    return all(math.isfinite(x) for x in floats) and any(x != 0.0 for x in floats)


class _Canary:
    def __init__(self, allow_skip_vision: bool) -> None:
        self.allow_skip_vision = allow_skip_vision
        self.records: list[OpRecord] = []
        self.failures: list[str] = []
        self.counter = _RetryCounter()
        logging.getLogger("services.common.reliability").addHandler(self.counter)

    def run(
        self,
        name: str,
        deadline: float,
        fn: Callable[[], Any],
        validate: Callable[[Any], None],
        *,
        skipped: bool = False,
    ) -> None:
        record = OpRecord(name=name, correlation_id=uuid.uuid4().hex, deadline_s=deadline)
        if skipped:
            record.skipped = True
            record.detail = "no --pdf/--image supplied for vision"
            self.records.append(record)
            if not self.allow_skip_vision:
                self.failures.append(f"{name}: skipped (pass --pdf or --image)")
            return

        self.counter.current = name
        record.children_before = len(multiprocessing.active_children())
        mem0 = _rss_mb()
        started = time.monotonic()
        try:
            result = fn()
            record.latency_ms = (time.monotonic() - started) * 1000.0
            validate(result)
            record.ok = True
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            record.latency_ms = (time.monotonic() - started) * 1000.0
            record.detail = f"{type(exc).__name__}: {exc}"
            self.failures.append(f"{name}: {record.detail}")
        finally:
            self.counter.current = None
            record.children_after = len(multiprocessing.active_children())
            record.memory_delta_mb = max(0.0, _rss_mb() - mem0)
            record.retries = self.counter.counts.get(name, 0)

        if record.latency_ms > deadline * 1000.0 * _DEADLINE_TOLERANCE:
            self.failures.append(
                f"{name}: deadline overrun {record.latency_ms:.0f}ms > {deadline}s"
            )
        if record.children_after != record.children_before:
            self.failures.append(
                f"{name}: orphan children {record.children_before}->{record.children_after}"
            )
        if "unpicklable outcome" in record.detail:
            self.failures.append(f"{name}: unpicklable outcome across the process pipe")
        self.records.append(record)


def _render_png(pdf_path: str) -> bytes:
    import fitz  # PyMuPDF, already a runtime dependency

    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    return page.get_pixmap(dpi=200).tobytes("png")


def _summarize(text: str) -> str:
    """Use the worker's real summary path (model + retry policy)."""
    from services.common.reliability import retry_call
    from vertexai.generative_models import GenerativeModel

    worker_path = _REPO_ROOT / "services" / "ingestion-worker" / "app.py"
    spec = importlib.util.spec_from_file_location("ingestion_worker_app", worker_path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)

    model = GenerativeModel(os.getenv("LITE_MODEL", "gemini-2.5-flash-lite"))
    prompt = f"Summarize the following text in one sentence.\n\n{text[:4000]}"
    response = retry_call(
        lambda: model.generate_content(
            prompt, generation_config={"temperature": 0.2, "max_output_tokens": 256}
        ),
        worker._SUMMARY_RETRY_POLICY,
    )
    return (response.text or "").strip()


def _build_ops(provider, args):
    from services.common.models.vertex import VERTEX_POLICIES

    query = args.text
    history = [{"role": "user", "content": "What did the report say about adoption?"}]
    active_docs = [{"ui_index": 1, "doc_id": "doc_001", "filename": "report.pdf"}]
    chunk = {
        "chunk_id": "c1",
        "doc_id": "doc_001",
        "page_number": 1,
        "bbox": [0.1, 0.1, 0.5, 0.4],
        "text": "The report describes adoption of the scheme across districts.",
    }
    context = (
        "[1] (report.pdf, page 1) The report describes adoption of the scheme "
        "across districts and notes early uptake."
    )

    def _validate_embed(result):
        if not _valid_vector(result):
            raise AssertionError("invalid embedding")

    def _validate_batch(result):
        if len(result) != 3 or not all(_valid_vector(v) for v in result):
            raise AssertionError("batch embeddings invalid")

    def _validate_synthesis(result):
        if not getattr(result, "answer", "").strip():
            raise AssertionError("empty synthesis answer")
        allowed = {chunk["chunk_id"]}
        for citation in getattr(result, "citations", []):
            if citation.chunk_id not in allowed:
                raise AssertionError(f"citation outside source scope: {citation.chunk_id}")

    def _validate_rewrite(result):
        if not result.get("standalone_query"):
            raise AssertionError("rewrite missing standalone_query")

    def _validate_hyde(result):
        if not result.get("hypothesis"):
            raise AssertionError("HyDE missing hypothesis")
        if not isinstance(result.get("keywords"), list):
            raise AssertionError("HyDE keywords not a list")

    def _validate_route(result):
        if result.get("intent") not in (
            "SPECIFIC_SEARCH",
            "DOCUMENT_SUMMARY",
            "GLOBAL_SEARCH",
        ):
            raise AssertionError(f"bad intent: {result.get('intent')}")

    def _validate_rerank(result):
        if len(result) != 2 or not all(math.isfinite(float(x)) for x in result):
            raise AssertionError("rerank scores invalid")

    def _validate_text(result):
        if not isinstance(result, str) or not result.strip():
            raise AssertionError("empty text result")

    vision_skipped = not (args.pdf or args.image)

    def _vision():
        image = Path(args.image).read_bytes() if args.image else _render_png(args.pdf)
        return provider.ocr_page(image)

    return [
        ("embedding", VERTEX_POLICIES["embed"].overall_deadline,
         lambda: provider.embed("retrieval augmented generation reliability"),
         _validate_embed),
        ("batch_embedding", VERTEX_POLICIES["embed"].overall_deadline,
         lambda: provider.embed_batch(["alpha text", "beta text", "gamma text"]),
         _validate_batch),
        ("synthesis", VERTEX_POLICIES["synthesize"].overall_deadline,
         lambda: provider.synthesize(context, query, [chunk]),
         _validate_synthesis),
        ("rewrite", VERTEX_POLICIES["rewrite"].overall_deadline,
         lambda: provider.rewrite_query_structured("What about it?", history),
         _validate_rewrite),
        ("hyde", VERTEX_POLICIES["hyde"].overall_deadline,
         lambda: provider.generate_hyde(query),
         _validate_hyde),
        ("router", VERTEX_POLICIES["route"].overall_deadline,
         lambda: provider.route_query(query, active_docs),
         _validate_route),
        ("reranker", VERTEX_POLICIES["rerank"].overall_deadline,
         lambda: provider.rerank(query, ["first passage", "second passage"]),
         _validate_rerank),
        ("vision_ocr", VERTEX_POLICIES["gemini_vision"].overall_deadline,
         _vision, _validate_text, vision_skipped),
        ("document_summary", 120.0,
         lambda: _summarize("The report describes adoption of the scheme."),
         _validate_text),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GCP_PROJECT"))
    parser.add_argument("--pdf", default=None, help="sample PDF for the vision/OCR op")
    parser.add_argument("--image", default=None, help="sample PNG for the vision/OCR op")
    parser.add_argument("--text", default="What does the report say about adoption?")
    parser.add_argument("--out", default=None, help="write the JSON report here")
    parser.add_argument("--allow-skip-vision", action="store_true")
    args = parser.parse_args()

    if not args.project:
        parser.error("--project or GCP_PROJECT is required (credentialed run)")

    os.environ["MODEL_BACKEND"] = "vertex"
    os.environ["GCP_PROJECT"] = args.project

    from services.common.models.vertex import VertexAIProvider

    canary = _Canary(args.allow_skip_vision)
    provider = VertexAIProvider(project_id=args.project)

    captured: list[warnings.WarningMessage] = []
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        for name, deadline, fn, validate, *rest in _build_ops(provider, args):
            canary.run(name, deadline, fn, validate, skipped=bool(rest and rest[0]))

    for warning in captured:
        text = str(warning.message).lower()
        if "fork" in text or "grpc" in text:
            canary.failures.append(f"fork/gRPC warning: {warning.message}")

    survivors = len(multiprocessing.active_children())
    if survivors:
        canary.failures.append(f"{survivors} child process(es) survived the canary")

    report = {
        "project": args.project,
        "operations": [asdict(r) for r in canary.records],
        "failures": canary.failures,
        "passed": not canary.failures,
    }
    print(json.dumps(report, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if not canary.failures else 1


if __name__ == "__main__":
    sys.exit(main())
