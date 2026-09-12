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
import concurrent.futures
import json
import logging
import os
import re
import tempfile
import threading
import time
import uuid
from collections import defaultdict

from flask import Flask, g, jsonify, request

from google.cloud import firestore, pubsub_v1

from services.common.errors import (
    REJECTION_MESSAGES,
    ErrorCode,
    RejectionCode,
    error_envelope,
)
from services.common.ingestion.cache import get_cached_chunks
from services.common.ingestion.main import (
    IngestionPipeline,
    RejectError,
    RetryError,
)
from services.common.ingestion.pdf_splitter import SplitTimeout, compute_sha256, split_pdf
from services.common.ingestion.preflight import MAX_PAGE_COUNT, PreflightError, check_pdf
from services.common.ingestion.qa_view import build_qa_response
from services.common.ingestion.store import get_chunk_store
from services.common.reliability import RetryPolicy, retry_call

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8080))
_pipeline = None

# Phase 0.1 hard limits (bounded fan-out / processing).
_PUBLISH_TIMEOUT_SECONDS = float(os.environ.get("PUBLISH_TIMEOUT_SECONDS", "30"))
_MAX_PROCESSING_SECONDS = float(os.environ.get("MAX_PROCESSING_SECONDS", "900"))
_STAGE_VERSION = "page-v1"
_MAX_DOWNLOAD_BYTES = int(os.environ.get("MAX_DOWNLOAD_BYTES", str(200 * 1024 * 1024)))

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@app.before_request
def _assign_request_id():
    """Accept a safe inbound X-Request-ID or generate one (never trust blindly)."""
    raw = request.headers.get("X-Request-ID", "")
    g.request_id = raw if _REQUEST_ID_PATTERN.match(raw) else uuid.uuid4().hex


@app.after_request
def _echo_request_id(response):
    response.headers["X-Request-ID"] = getattr(g, "request_id", "") or uuid.uuid4().hex
    return response


def _error_json(code: str, message: str, status_code: int):
    request_id = getattr(g, "request_id", "") if request else ""
    return jsonify(error_envelope(code, message, request_id)), status_code


@app.errorhandler(Exception)
def _handle_unexpected(exc):
    # Let Flask's HTTPException (404/405) keep its status.
    from werkzeug.exceptions import HTTPException

    if isinstance(exc, HTTPException):
        return _error_json(ErrorCode.NOT_FOUND, "Not found.", exc.code or 404)
    logger.exception("unhandled worker exception")
    return _error_json(
        ErrorCode.INTERNAL_ERROR, "An unexpected internal error occurred.", 500
    )


def _rejection_payload(exc) -> dict:
    """Map a rejection to an enumerated code + stable public message.

    Never returns exception text — an internal parser/path message must not
    reach the client.
    """
    code = getattr(exc, "code", None) or RejectionCode.INVALID_REQUEST
    return {
        "status": "rejected",
        "code": code,
        "message": REJECTION_MESSAGES.get(
            code, REJECTION_MESSAGES[RejectionCode.INVALID_REQUEST]
        ),
    }


def _firestore() -> firestore.Client:
    return firestore.Client()


def _doc_exists(tenant_id: str, doc_id: str) -> bool:
    """Verify the document is still owned by this tenant.

    Phase 0.1 (P0): fails CLOSED. If ownership cannot be verified the caller
    must not process or index the page — a retryable error lets Pub/Sub
    redeliver once Firestore is reachable again.
    """
    try:
        doc = _firestore().document(f"tenants/{tenant_id}/documents/{doc_id}").get()
        return bool(doc.exists)
    except Exception as exc:
        logger.warning("Ownership verification failed for doc_id=%s: %s", doc_id, exc)
        raise RetryError("Document ownership could not be verified") from exc


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
    project = os.getenv("GCP_PROJECT", "procambrian-iris-staging-2026")
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
        if not _doc_exists(tenant_id, doc_id):
            logger.info("Doc deleted during ingestion, skipping page %s/%s", doc_id, page_number)
            return jsonify({"status": "skipped", "doc_id": doc_id, "page_number": page_number}), 200
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
        # Trigger background summary generation when all pages are done
        if total_pages > 0 and page_number >= total_pages:
            if _check_all_pages_done(tenant_id, doc_id):
                _generate_doc_summary_background(tenant_id, doc_id)
        return jsonify({"status": "ok", "doc_id": doc_id, "page_number": page_number}), 200
    except RejectError as exc:
        _mark_page_failed(tenant_id, doc_id, page_number)
        logger.warning("Rejected %s page %s: %s", doc_id, page_number, exc)
        return jsonify(_rejection_payload(exc)), 200
    except RetryError as exc:
        logger.warning("Transient failure for %s page %s: %s", doc_id, page_number, exc)
        return _error_json(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            "Temporary failure processing the page; retry.",
            503,
        )
    except Exception as exc:
        _mark_page_failed(tenant_id, doc_id, page_number)
        logger.exception("Pipeline failed for doc_id=%s page=%s", doc_id, page_number)
        return _error_json(
            ErrorCode.INTERNAL_ERROR, "An unexpected internal error occurred.", 500
        )


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
        return _error_json(
            ErrorCode.INVALID_REQUEST,
            "gcs_uri, tenant_id, and doc_id are required.",
            400,
        )

    deadline = time.monotonic() + _MAX_PROCESSING_SECONDS

    # Download the source PDF exactly once into a request-scoped temp dir and
    # reuse it for the checksum, preflight and split stages.
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = _get_pipeline()._download(gcs_uri, tmpdir, doc_id)

            try:
                size = local_path.stat().st_size
            except OSError:
                size = 0
            if size > _MAX_DOWNLOAD_BYTES:
                return jsonify({
                    "status": "rejected",
                    "code": RejectionCode.PDF_TOO_LARGE,
                    "message": REJECTION_MESSAGES[RejectionCode.PDF_TOO_LARGE],
                }), 200
            if size == 0:
                return jsonify({
                    "status": "rejected",
                    "code": RejectionCode.PDF_EMPTY,
                    "message": REJECTION_MESSAGES[RejectionCode.PDF_EMPTY],
                }), 200

            # 1. Doc cache check (hash the already-downloaded bytes).
            sha = compute_sha256(gcs_uri, local_path=local_path)
            if sha:
                cached = get_cached_chunks(sha, tenant_id, doc_id)
                if cached:
                    return jsonify({
                        "status": "already_ingested",
                        "doc_id": doc_id,
                        "total_pages": len({c.page_number for c in cached}),
                        "chunks": len(cached),
                    }), 200

            # 2. Preflight the same local file.
            try:
                check_pdf(local_path)
            except (PreflightError, RejectError) as exc:
                return jsonify(_rejection_payload(exc)), 200

            if time.monotonic() > deadline:
                return _error_json(
                    ErrorCode.DEPENDENCY_TIMEOUT,
                    "Ingestion preprocessing timed out.",
                    504,
                )

            # 3. Split and upload page blobs, reusing the same local file.
            try:
                page_messages = split_pdf(
                    gcs_uri,
                    doc_id,
                    tenant_id,
                    local_path=local_path,
                    deadline=deadline,
                    max_pages=MAX_PAGE_COUNT,
                )
            except PreflightError as exc:
                return jsonify(_rejection_payload(exc)), 200
            except SplitTimeout:
                return _error_json(
                    ErrorCode.DEPENDENCY_TIMEOUT,
                    "Document processing timed out.",
                    504,
                )
            except Exception:
                logger.exception("Failed to split PDF doc_id=%s", doc_id)
                return _error_json(
                    ErrorCode.BAD_UPSTREAM_RESPONSE,
                    "Failed to process the document.",
                    502,
                )
    except RetryError:
        return _error_json(
            ErrorCode.DEPENDENCY_UNAVAILABLE, "Failed to fetch the document; retry.", 503
        )
    except RejectError as exc:
        return jsonify(_rejection_payload(exc)), 200
    except Exception:
        logger.exception("Preprocessing failed for doc_id=%s", doc_id)
        return _error_json(
            ErrorCode.INTERNAL_ERROR, "An unexpected internal error occurred.", 500
        )

    if not page_messages:
        return _error_json(ErrorCode.INVALID_REQUEST, "The PDF has no pages.", 422)

    # 4. Record expected pages BEFORE dispatching work (no completion race).
    total_pages = page_messages[0]["total_pages"]
    _init_progress(tenant_id, doc_id, total_pages)

    # 5. Publish every page event and await them under ONE overall deadline.
    # Publish creation and waiting both live inside the error handler so a
    # synchronous publish failure cannot bypass partial-failure handling.
    topic_path = _pubsub_topic()
    publisher = _pubsub()
    publish_deadline = max(0.001, min(_PUBLISH_TIMEOUT_SECONDS, deadline - time.monotonic()))
    futures = []
    try:
        for msg in page_messages:
            event_id = f"{tenant_id}:{doc_id}:{msg['page_number']}:{_STAGE_VERSION}"
            futures.append(
                publisher.publish(
                    topic_path,
                    json.dumps(msg).encode("utf-8"),
                    gcs_uri=msg["gcs_uri"],
                    tenant_id=msg["tenant_id"],
                    doc_id=msg["doc_id"],
                    page_number=str(msg["page_number"]),
                    total_pages=str(msg["total_pages"]),
                    event_id=event_id,
                )
            )
        done, not_done = concurrent.futures.wait(futures, timeout=publish_deadline)
        failed = [f for f in done if f.exception() is not None]
        if not_done or failed:
            raise RuntimeError(
                f"publish incomplete: {len(not_done)} pending, {len(failed)} failed"
            )
    except Exception:
        logger.exception(
            "Publish failed for doc_id=%s (published=%d/%d)",
            doc_id, len(futures), len(page_messages),
        )
        _mark_document_failed(tenant_id, doc_id)
        return _error_json(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            "Failed to dispatch ingestion work; retry.",
            503,
        )

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


@app.get("/livez")
def livez():
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


def _check_all_pages_done(tenant_id: str, doc_id: str) -> bool:
    """Check if all pages for a document have been ingested."""
    if not tenant_id:
        return False
    snapshot = _firestore().document(_progress_doc_path(tenant_id, doc_id)).get()
    if not snapshot.exists:
        return False
    data = snapshot.to_dict() or {}
    total = int(data.get("total_pages", 0))
    if total <= 0:
        return False
    store = get_chunk_store()
    chunks = store.get_by_doc(doc_id, tenant_id=tenant_id)
    completed = len({c.page_number for c in chunks})
    return completed >= total


def _generate_doc_summary_background(tenant_id: str, doc_id: str):
    """Generate a document summary in the background after ingestion completes.

    Runs in a daemon thread so it doesn't block the ingestion pipeline.
    Falls back gracefully on any error.
    """
    def _worker():
        try:
            from services.common.models.vertex import VertexAIProvider
            from google.cloud import firestore as fs

            store = get_chunk_store()
            chunks = store.get_by_doc(doc_id, tenant_id=tenant_id)
            if not chunks:
                return

            # Combine all chunk texts (limit to avoid token overflow)
            full_text = "\n\n".join(c.text for c in chunks[:200])

            provider = VertexAIProvider()
            model_name = os.environ.get("LITE_MODEL", "gemini-2.5-flash-lite")
            from vertexai.generative_models import GenerativeModel
            model = GenerativeModel(model_name)

            prompt = (
                "Generate a comprehensive 1-paragraph executive summary of this "
                "document. Then list 3 key topics, one per line starting with "
                "'Topics:'. Be specific about the document's purpose, key findings, "
                "and domain.\n\n"
                f"DOCUMENT TEXT (excerpt):\n'''\n{full_text[:80000]}\n'''"
            )

            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.2, "max_output_tokens": 512},
            )

            summary_text = ""
            key_topics = []
            if response and response.text:
                raw = response.text.strip()
                if "\nTopics:" in raw:
                    parts = raw.split("\nTopics:", 1)
                    summary_text = parts[0].strip()
                    key_topics = [t.strip() for t in parts[1].split("\n") if t.strip()]
                else:
                    summary_text = raw

            # Save to Firestore document record
            client = fs.Client()
            doc_ref = client.document(f"tenants/{tenant_id}/documents/{doc_id}")
            doc_ref.set({
                "summary": summary_text,
                "key_topics": key_topics,
                "summary_generated_at": fs.SERVER_TIMESTAMP,
            }, merge=True)

            logger.info("Summary generated for doc_id=%s tenant=%s", doc_id, tenant_id)

        except Exception as exc:
            logger.warning("Summary generation failed for %s/%s: %s", tenant_id, doc_id, exc)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def _mark_page_failed(tenant_id: str, doc_id: str, page_number: int):
    _firestore().document(_progress_doc_path(tenant_id, doc_id)).set({
        "failed_pages": firestore.ArrayUnion([page_number]),
        "updated_at": firestore.SERVER_TIMESTAMP,
    }, merge=True)


def _mark_document_failed(tenant_id: str, doc_id: str):
    """Record a partial/failed fan-out so status reflects reality."""
    try:
        _firestore().document(_progress_doc_path(tenant_id, doc_id)).set({
            "status": "failed",
            "updated_at": firestore.SERVER_TIMESTAMP,
        }, merge=True)
    except Exception:
        logger.warning("Failed to mark document failed doc_id=%s", doc_id)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
