"""Cloud Run entrypoint for the Ingestion Worker (Phase 1.0).

Receives the Pub/Sub push envelope (via Eventarc) and dispatches the
ingestion pipeline. Returns 200 = ack, 500 = nack/retry.
"""

from __future__ import annotations

import base64
import json
import logging
import os

from flask import Flask, jsonify, request

from services.common.ingestion.main import (
    IngestionPipeline,
    RejectError,
    RetryError,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8080))
_pipeline = None


def _get_pipeline() -> IngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = IngestionPipeline()
    return _pipeline


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok", "service": "ingestion-worker", "phase": "1.0"}), 200


@app.post("/")
def ingest_message():
    envelope = request.get_json(silent=True) or {}
    message = envelope.get("message", {})

    try:
        data = json.loads(base64.b64decode(message.get("data", "")).decode("utf-8"))
    except Exception:  # noqa: BLE001
        logger.error("Malformed Pub/Sub payload: %r", message)
        return jsonify({"error": "malformed payload"}), 400

    gcs_uri = data.get("gcs_uri") or (message.get("attributes") or {}).get("gcs_uri")
    tenant_id = data.get("tenant_id") or (message.get("attributes") or {}).get("tenant_id")
    doc_id = data.get("doc_id") or (message.get("attributes") or {}).get("doc_id")

    try:
        result = _get_pipeline().ingest(gcs_uri=gcs_uri, tenant_id=tenant_id, doc_id=doc_id)
        logger.info(
            "Ingested doc_id=%s tenant=%s pages=%s chunks=%s vlm_calls=%s",
            result.doc_id, result.tenant_id, result.page_count,
            result.chunk_count, result.vlm_calls,
        )
        return jsonify({"status": "ok", "doc_id": doc_id}), 200
    except RejectError as exc:
        # Reject forever: ack so it never retries or hits the DLQ.
        logger.warning("Rejected %s: %s", doc_id, exc)
        return jsonify({"status": "rejected", "reason": str(exc)}), 200
    except RetryError as exc:
        logger.warning("Transient failure for %s: %s", doc_id, exc)
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed for doc_id=%s", doc_id)
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
