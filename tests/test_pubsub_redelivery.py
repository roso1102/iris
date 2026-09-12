"""Pub/Sub fan-out future failure and redelivery (Phase 0.1 reliability).

Covers the documented contract: ``pubsub_publish_future`` retries only the
synchronous ``publish()`` call; failures that surface later on the returned
future are detected by the worker, which returns 503 so the caller / Pub/Sub
delivers the whole (idempotent) operation again. Redelivery must not duplicate
pages or vectors.
"""

import concurrent.futures
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from services.common.reliability import TransientError

os.environ.setdefault("GCP_PROJECT", "test-project")

_WORKER_PATH = (
    Path(__file__).resolve().parents[1] / "services" / "ingestion-worker" / "app.py"
)


def _load_worker_module():
    spec = importlib.util.spec_from_file_location("ingestion_worker_app", _WORKER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _RecordingPublisher:
    """publish() always succeeds synchronously; the future may fail later."""

    def __init__(self, future_fails: bool):
        self.future_fails = future_fails
        self.event_ids = []

    def publish(self, topic, data, **attrs):
        self.event_ids.append(attrs.get("event_id"))
        fut = concurrent.futures.Future()
        if self.future_fails:
            fut.set_exception(TransientError("pubsub unavailable"))
        else:
            fut.set_result("msg-id")
        return fut


def _page_messages():
    return [
        {
            "gcs_uri": f"gs://b/t/d/pages/page_{n}.pdf",
            "tenant_id": "t",
            "doc_id": "d",
            "page_number": n,
            "total_pages": 3,
        }
        for n in (1, 2, 3)
    ]


class TestPubSubFutureFailureRedelivery(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.worker = _load_worker_module()

    def _post(self, publisher):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"%PDF-1.4 fake pdf bytes")
            local = Path(tmp.name)
        pipeline = MagicMock()
        pipeline._download.return_value = local
        try:
            with patch.object(self.worker, "_get_pipeline", return_value=pipeline), \
                    patch.object(self.worker, "compute_sha256", return_value=None), \
                    patch.object(self.worker, "check_pdf", return_value=None), \
                    patch.object(self.worker, "split_pdf", return_value=_page_messages()), \
                    patch.object(self.worker, "_init_progress"), \
                    patch.object(self.worker, "_mark_document_failed") as mark_failed, \
                    patch.object(self.worker, "_pubsub", return_value=publisher):
                client = self.worker.app.test_client()
                resp = client.post(
                    "/ingest",
                    json={"gcs_uri": "gs://b/t/d.pdf", "tenant_id": "t", "doc_id": "d"},
                )
            return resp, mark_failed
        finally:
            local.unlink(missing_ok=True)

    def test_late_future_failure_returns_503(self):
        publisher = _RecordingPublisher(future_fails=True)
        resp, mark_failed = self._post(publisher)
        # publish() returned a future for every page (no synchronous failure)…
        self.assertEqual(len(publisher.event_ids), 3)
        # …but the late failure makes the whole request retryable.
        self.assertEqual(resp.status_code, 503)
        mark_failed.assert_called_once()

    def test_redelivery_does_not_duplicate_pages_or_vectors(self):
        failing = _RecordingPublisher(future_fails=True)
        self._post(failing)

        healthy = _RecordingPublisher(future_fails=False)
        resp, _ = self._post(healthy)
        self.assertEqual(resp.status_code, 200)

        # Identical, unique, deterministic page ids on redelivery → the consumer
        # can dedupe, and no page is emitted twice.
        self.assertEqual(healthy.event_ids, failing.event_ids)
        self.assertEqual(len(set(healthy.event_ids)), 3)

        # Vector idempotency: identical content keeps the same deterministic id,
        # so a redelivered page overwrites rather than duplicates.
        from services.common.ingestion.models import (
            Chunk,
            ElementType,
            RouteDecision,
        )
        from services.common.ingestion.store import MemoryChunkStore

        def _chunk():
            return Chunk(
                tenant_id="t",
                doc_id="d",
                page_number=1,
                element_type=ElementType.TEXT,
                text="same page content",
                bbox=[0.1, 0.1, 0.5, 0.4],
                source=RouteDecision.DOCLING_TEXT,
            )

        store = MemoryChunkStore()
        store.upsert_batch([_chunk()])
        store.upsert_batch([_chunk()])  # redelivery
        self.assertEqual(len(store.get_by_doc("d", "t")), 1)
        self.assertEqual(_chunk().id, _chunk().id)


if __name__ == "__main__":
    unittest.main()
