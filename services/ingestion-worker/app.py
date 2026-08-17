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

from google.cloud import firestore, pubsub_v1

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


def _firestore() -> firestore.Client:
    return firestore.Client()


def _progress_doc_path(tenant_id: str, doc_id: str) -> str:
    # Firestore paths must alternate collection/document (even number of
    # elements): ingestion_progress/{tenant_id}/documents/{doc_id}.
    return f"ingestion_progress/{tenant_id}/documents/{doc_id}"


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


def _decode_pubsub_payload(envelope: dict) -> tuple[dict, dict]:
    """Return (data_payload, attributes) from a Pub/Sub/Eventarc push envelope.

    Eventarc and raw Pub/Sub push can place attributes at either the top level
    or inside `message.attributes`. The actual document payload is the
    base64-encoded JSON inside `message.data`.
    """
    message = envelope.get("message", envelope) or {}
    attributes = dict(message.get("attributes") or {})
    # Some Eventarc delivery variants put attributes at the envelope root.
    root_attributes = envelope.get("attributes") or {}
    attributes.update({k: v for k, v in root_attributes.items() if v})

    data: dict = {}
    raw = message.get("data", "")
    if raw:
        try:
            decoded = json.loads(base64.b64decode(raw).decode("utf-8"))
            if isinstance(decoded, dict):
                data = decoded
        except Exception:
            data = {}

    return data, attributes


def _first_present(data: dict, attributes: dict, key: str) -> str:
    """Prefer the decoded message payload, fall back to Pub/Sub attributes."""
    value = data.get(key)
    if value not in (None, ""):
        return value
    return attributes.get(key, "")


@app.post("/")
def ingest_page():
    """Process a single page (delivered by Pub/Sub push)."""
    envelope = request.get_json(silent=True) or {}
    message = envelope.get("message", envelope) or {}
    logger.info(
        "pubsub_envelope_received",
        extra={
            "message_id": message.get("messageId", ""),
            "has_data": bool(message.get("data")),
            "subscription": str(envelope.get("subscription", ""))[:120],
        },
    )

    data, attributes = _decode_pubsub_payload(envelope)
    gcs_uri = _first_present(data, attributes, "gcs_uri")
    tenant_id = _first_present(data, attributes, "tenant_id")
    doc_id = _first_present(data, attributes, "doc_id")
    page_number = _first_present(data, attributes, "page_number")
    total_pages = _first_present(data, attributes, "total_pages")

    page_number = int(page_number) if str(page_number).isdigit() else 0
    total_pages = int(total_pages) if str(total_pages).isdigit() else 0

    try:
        result = _get_pipeline().ingest(
            gcs_uri=gcs_uri,
            tenant_id=tenant_id,
            doc_id=doc_id,
            page_number=page_number or None,
        )
        _mark_page_done(tenant_id, doc_id, page_number)
        logger.info(
            "Ingested doc_id=%s page=%s/%s tenant=%s chunks=%s vlm_calls=%s",
            doc_id, page_number, total_pages, tenant_id, result.chunk_count, result.vlm_calls,
        )
        return jsonify({"status": "ok", "doc_id": doc_id, "page_number": page_number}), 200
    except RejectError as exc:
        _mark_page_failed(tenant_id, doc_id, page_number)
        logger.warning("Rejected %s page %s: %s", doc_id, page_number, exc)
        return jsonify({"status": "rejected", "reason": str(exc)}), 200
    except RetryError as exc:
        logger.warning("Transient failure for %s page %s: %s", doc_id, page_number, exc)
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        _mark_page_failed(tenant_id, doc_id, page_number)
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
    _init_progress(tenant_id, doc_id, total_pages)

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
    tenant_id = request.args.get("tenant_id", "")
    store = get_chunk_store()
    chunks = store.get_by_doc(doc_id, tenant_id=tenant_id)
    completed = len({c.page_number for c in chunks})

    total = 0
    failed: list[int] = []
    if tenant_id:
        snapshot = _firestore().document(_progress_doc_path(tenant_id, doc_id)).get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            total = int(data.get("total_pages", 0))
            failed = [int(p) for p in data.get("failed_pages", [])]

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


# ── Firestore-backed progress tracking (survives cold starts / scale-out) ──


def _init_progress(tenant_id: str, doc_id: str, total_pages: int):
    _firestore().document(_progress_doc_path(tenant_id, doc_id)).set({
        "total_pages": total_pages,
        "failed_pages": [],
        "updated_at": firestore.SERVER_TIMESTAMP,
    })


def _mark_page_done(tenant_id: str, doc_id: str, page_number: int):
    _firestore().document(_progress_doc_path(tenant_id, doc_id)).set({
        "updated_at": firestore.SERVER_TIMESTAMP,
    }, merge=True)


def _mark_page_failed(tenant_id: str, doc_id: str, page_number: int):
    _firestore().document(_progress_doc_path(tenant_id, doc_id)).set({
        "failed_pages": firestore.ArrayUnion([page_number]),
        "updated_at": firestore.SERVER_TIMESTAMP,
    }, merge=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
