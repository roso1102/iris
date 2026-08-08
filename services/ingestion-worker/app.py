"""Cloud Run entrypoint for the Ingestion Worker (Phase 1.0).

Receives the Pub/Sub push envelope and dispatches the ingestion pipeline.
Supports parallel page-level dispatch: POST /ingest splits PDFs, fans out
per-page Pub/Sub messages, and POST / processes individual pages.
GET /status/{doc_id} reports live ingestion progress.
"""

from __future__ import annotations

import os
os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")

import base64
import json
import logging
import os
import threading
from collections import defaultdict

from flask import Flask, jsonify, request

from google.cloud import pubsub_v1

from services.common.ingestion.cache import get_cached_chunks
from services.common.ingestion.main import (
    IngestionPipeline,
    RejectError,
    RetryError,
)
from services.common.ingestion.pdf_splitter import compute_sha256, split_pdf
from services.common.ingestion.preflight import PreflightError, check_pdf
from services.common.ingestion.qa_view import build_qa_response
from services.common.ingestion.store import get_chunk_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8080))
_pipeline = None

_progress: dict[str, dict] = {}
_progress_lock = threading.Lock()


def _get_pipeline() -> IngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = IngestionPipeline()
    return _pipeline


def _pubsub() -> pubsub_v1.PublisherClient:
    return pubsub_v1.PublisherClient()


def _pubsub_topic() -> str:
    project = os.getenv("GCP_PROJECT", "naturepivot-rag")
    topic = os.getenv("INGESTION_TOPIC", "iris-ingestion")
    return f"projects/{project}/topics/{topic}"


# ── Core ingestion (per-page) ──────────────────────────────────────────────


@app.post("/")
def ingest_page():
    """Process a single page (delivered by Pub/Sub push)."""
    envelope = request.get_json(silent=True) or {}
    message = envelope.get("message", envelope)

    data = {}
    raw = message.get("data", "")
    if raw:
        try:
            data = json.loads(base64.b64decode(raw).decode("utf-8"))
        except Exception:
            data = {}

    gcs_uri = data.get("gcs_uri") or (message.get("attributes") or {}).get("gcs_uri")
    tenant_id = data.get("tenant_id") or (message.get("attributes") or {}).get("tenant_id")
    doc_id = data.get("doc_id") or (message.get("attributes") or {}).get("doc_id")
    page_number = data.get("page_number") or (message.get("attributes") or {}).get("page_number")
    total_pages = data.get("total_pages") or (message.get("attributes") or {}).get("total_pages")

    page_number = int(page_number) if page_number else 0
    total_pages = int(total_pages) if total_pages else 0

    try:
        result = _get_pipeline().ingest(gcs_uri=gcs_uri, tenant_id=tenant_id, doc_id=doc_id)
        _mark_page_done(doc_id, page_number)
        logger.info(
            "Ingested doc_id=%s page=%s/%s tenant=%s chunks=%s vlm_calls=%s",
            doc_id, page_number, total_pages, tenant_id, result.chunk_count, result.vlm_calls,
        )
        return jsonify({"status": "ok", "doc_id": doc_id, "page_number": page_number}), 200
    except RejectError as exc:
        _mark_page_failed(doc_id, page_number)
        logger.warning("Rejected %s page %s: %s", doc_id, page_number, exc)
        return jsonify({"status": "rejected", "reason": str(exc)}), 200
    except RetryError as exc:
        logger.warning("Transient failure for %s page %s: %s", doc_id, page_number, exc)
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        _mark_page_failed(doc_id, page_number)
        logger.exception("Pipeline failed for doc_id=%s page=%s", doc_id, page_number)
        return jsonify({"error": str(exc)}), 500


# ── Document-level ingest (fan-out) ────────────────────────────────────────


@app.post("/ingest")
def ingest_document():
    """Preflight + split + fan out per-page messages.

    Request body (JSON):
        {"gcs_uri": "...", "tenant_id": "...", "doc_id": "..."}

    Returns 200 immediately with total_pages — client polls /status/{doc_id}.
    """
    body = request.get_json(silent=True) or {}
    gcs_uri = body.get("gcs_uri", "")
    tenant_id = body.get("tenant_id", "")
    doc_id = body.get("doc_id", "")

    if not gcs_uri or not tenant_id or not doc_id:
        return jsonify({"error": "gcs_uri, tenant_id, and doc_id are required"}), 400

    # 1. Doc cache check
    sha = compute_sha256(gcs_uri)
    if sha:
        cached = get_cached_chunks(sha, tenant_id, doc_id)
        if cached:
            return jsonify({
                "status": "already_ingested",
                "doc_id": doc_id,
                "total_pages": len({c.page_number for c in cached}),
                "chunks": len(cached),
            }), 200

    # 2. Preflight
    try:
        _get_pipeline()._download(gcs_uri, os.environ.get("TMPDIR", "/tmp"), doc_id)
        check_pdf(_get_pipeline()._download(gcs_uri, os.environ.get("TMPDIR", "/tmp"), doc_id))
    except (PreflightError, RejectError) as exc:
        return jsonify({"status": "rejected", "reason": str(exc)}), 200

    # 3. Split and fan out
    try:
        page_messages = split_pdf(gcs_uri, doc_id, tenant_id)
    except Exception as exc:
        logger.exception("Failed to split PDF %s", gcs_uri)
        return jsonify({"error": str(exc)}), 500

    if not page_messages:
        return jsonify({"error": "PDF has no pages"}), 400

    # 4. Publish per-page Pub/Sub messages
    topic_path = _pubsub_topic()
    publisher = _pubsub()
    for msg in page_messages:
        publisher.publish(
            topic_path,
            json.dumps(msg).encode("utf-8"),
            gcs_uri=msg["gcs_uri"],
            tenant_id=msg["tenant_id"],
            doc_id=msg["doc_id"],
            page_number=str(msg["page_number"]),
            total_pages=str(msg["total_pages"]),
        )

    total_pages = page_messages[0]["total_pages"]
    _init_progress(doc_id, total_pages)

    logger.info("Fanned out %d pages for doc_id=%s", total_pages, doc_id)
    return jsonify({
        "status": "processing",
        "doc_id": doc_id,
        "total_pages": total_pages,
        "completed_pages": 0,
    }), 200


# ── Status endpoint ────────────────────────────────────────────────────────


@app.get("/status/<doc_id>")
def ingestion_status(doc_id: str):
    """Return live per-document ingestion progress.

    Returns: {"doc_id": ..., "total_pages": N, "completed_pages": M,
              "chunks": C, "failed_pages": [p1, p2]}
    """
    store = get_chunk_store()
    chunks = store.get_by_doc(doc_id, tenant_id="")
    completed = len({c.page_number for c in chunks})

    with _progress_lock:
        prog = _progress.get(doc_id, {})
        total = prog.get("total_pages", 0)
        failed = prog.get("failed_pages", [])

    return jsonify({
        "doc_id": doc_id,
        "total_pages": total,
        "completed_pages": completed,
        "failed_pages": failed,
        "chunks": len(chunks),
    }), 200


# ── Health / QA ────────────────────────────────────────────────────────────


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok", "service": "ingestion-worker", "phase": "1.0"}), 200


@app.get("/memory")
def memory_view():
    doc_id = request.args.get("doc_id", "")
    tenant_id = request.args.get("tenant_id", "")
    page_number = int(request.args.get("page_number", 0))
    auth_header = request.headers.get("Authorization", "")
    result, status = build_qa_response(
        doc_id=doc_id,
        page_number=page_number,
        tenant_id=tenant_id,
        auth_header=auth_header,
    )
    return jsonify(result), status


# ── In-memory progress tracking (reset on cold start) ──────────────────────


def _init_progress(doc_id: str, total_pages: int):
    with _progress_lock:
        _progress[doc_id] = {
            "total_pages": total_pages,
            "completed_pages": set(),
            "failed_pages": [],
        }


def _mark_page_done(doc_id: str, page_number: int):
    with _progress_lock:
        if doc_id in _progress:
            _progress[doc_id]["completed_pages"].add(page_number)


def _mark_page_failed(doc_id: str, page_number: int):
    with _progress_lock:
        if doc_id in _progress:
            _progress[doc_id]["failed_pages"].append(page_number)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
