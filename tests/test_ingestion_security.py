"""Security hardening tests — Findings 1-10 risk verification."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.common.ingestion.main import (
    IngestionPipeline, RejectError, RetryError, _ALLOWED_URI_PATTERN,
)
from services.common.ingestion.store import MemoryChunkStore
from services.common.models.mock import MockModelProvider
from services.common.models.base import ModelProvider


# ---------------------------------------------------------------------------
# Risk 2(a): _download local dev gate
# ---------------------------------------------------------------------------

class TestDownloadLocalDevGate(unittest.TestCase):

    def setUp(self):
        os.environ["GCP_PROJECT"] = "test-project"
        os.environ["MODEL_BACKEND"] = "mock"
        store = MemoryChunkStore()
        provider = MockModelProvider()
        self.pipe = IngestionPipeline(provider=provider, store=store)
        self.test_docs = (Path(__file__).resolve().parents[1] / "trueassort").resolve()

    def tearDown(self):
        os.environ.pop("IRIS_LOCAL_DEV", None)

    def test_local_dev_allows_trueassort_path(self):
        os.environ["IRIS_LOCAL_DEV"] = "1"
        self.test_docs.mkdir(parents=True, exist_ok=True)
        pdf = self.test_docs / "dummy_local_dev.pdf"
        pdf.write_bytes(b"%PDF-1.4\n% dummy pdf for testing\n")
        try:
            result = self.pipe._download(str(pdf), tempfile.mkdtemp(), "test")
            self.assertEqual(result, pdf.resolve())
        finally:
            if pdf.exists():
                pdf.unlink()

    def test_local_dev_blocks_path_outside_trueassort(self):
        os.environ["IRIS_LOCAL_DEV"] = "1"
        with self.assertRaises(RejectError):
            self.pipe._download(
                str(Path("/etc/passwd").resolve()),
                tempfile.mkdtemp(), "test",
            )

    def test_local_dev_blocks_parent_traversal(self):
        os.environ["IRIS_LOCAL_DEV"] = "1"
        traversal = self.test_docs / ".." / ".." / "etc" / "passwd"
        with self.assertRaises(RejectError):
            self.pipe._download(str(traversal), tempfile.mkdtemp(), "test")

    def test_local_dev_blocks_relative_path(self):
        os.environ["IRIS_LOCAL_DEV"] = "1"
        with self.assertRaises(RejectError):
            self.pipe._download("relative/path.pdf", tempfile.mkdtemp(), "test")

    def test_production_rejects_local_path(self):
        """Without IRIS_LOCAL_DEV, local paths must be rejected."""
        os.environ.pop("IRIS_LOCAL_DEV", None)
        with self.assertRaises(RejectError):
            self.pipe._download("/tmp/test.pdf", tempfile.mkdtemp(), "test")

    def test_production_accepts_valid_gcs_uri(self):
        os.environ.pop("IRIS_LOCAL_DEV", None)
        # GCS client is None; download will fail at the network layer, but
        # we are testing that the URI _format_ is accepted (no RejectError).
        result = _ALLOWED_URI_PATTERN.match("gs://iris-raw-pdfs/tenant/doc.pdf")
        self.assertIsNotNone(result)

    def test_production_rejects_invalid_gcs_uri(self):
        self.assertIsNone(_ALLOWED_URI_PATTERN.match("gs://///bad"))
        self.assertIsNone(_ALLOWED_URI_PATTERN.match("file:///etc/passwd"))
        self.assertIsNone(_ALLOWED_URI_PATTERN.match("/etc/passwd"))


# ---------------------------------------------------------------------------
# Risk 2(b): IngestionPipeline constructor requires GCP_PROJECT for vertex
# ---------------------------------------------------------------------------

class TestIngestionPipelineConstructor(unittest.TestCase):

    def setUp(self):
        self._saved_project = os.environ.pop("GCP_PROJECT", None)

    def tearDown(self):
        if self._saved_project:
            os.environ["GCP_PROJECT"] = self._saved_project
        else:
            os.environ.pop("GCP_PROJECT", None)
        os.environ.pop("MODEL_BACKEND", None)

    def test_mock_backend_works_without_gcp_project(self):
        os.environ["MODEL_BACKEND"] = "mock"
        pipe = IngestionPipeline()
        self.assertIsNotNone(pipe)

    def test_vertex_backend_requires_gcp_project(self):
        os.environ["MODEL_BACKEND"] = "vertex"
        with patch.dict(os.environ, {"GCP_PROJECT": ""}, clear=False):
            os.environ.pop("GCP_PROJECT", None)
            with self.assertRaises(ValueError) as ctx:
                IngestionPipeline()
            self.assertIn("GCP_PROJECT", str(ctx.exception))


# ---------------------------------------------------------------------------
# Risk 1: QA view auth gate
# ---------------------------------------------------------------------------

from services.common.ingestion.qa_view import build_qa_response
from services.common.ingestion.store import MemoryChunkStore


class TestQAViewAuthGate(unittest.TestCase):

    def setUp(self):
        os.environ["GCP_PROJECT"] = "test-project"
        os.environ.pop("QA_VIEW_SECRET", None)
        os.environ.pop("QA_VIEW_ENFORCE_AUTH", None)

    def test_auth_bypassed_when_enforce_off(self):
        os.environ.pop("QA_VIEW_ENFORCE_AUTH", None)
        store = MemoryChunkStore()
        result, status = build_qa_response(
            doc_id="d1", page_number=1, tenant_id="t1",
            store=store,
        )
        self.assertEqual(status, 200)

    def test_auth_blocked_when_enforce_on_and_no_secret(self):
        os.environ["QA_VIEW_ENFORCE_AUTH"] = "1"
        os.environ.pop("QA_VIEW_SECRET", None)
        store = MemoryChunkStore()
        result, status = build_qa_response(
            doc_id="d1", page_number=1, tenant_id="t1",
            store=store,
        )
        self.assertEqual(status, 403)

    def test_auth_blocked_with_wrong_secret(self):
        os.environ["QA_VIEW_ENFORCE_AUTH"] = "1"
        os.environ["QA_VIEW_SECRET"] = "correct-secret"
        store = MemoryChunkStore()
        result, status = build_qa_response(
            doc_id="d1", page_number=1, tenant_id="t1",
            auth_header="Bearer wrong-secret",
            store=store,
        )
        self.assertEqual(status, 403)

    def test_auth_passes_with_correct_secret(self):
        os.environ["QA_VIEW_ENFORCE_AUTH"] = "1"
        os.environ["QA_VIEW_SECRET"] = "correct-secret"
        store = MemoryChunkStore()
        result, status = build_qa_response(
            doc_id="d1", page_number=1, tenant_id="t1",
            auth_header="Bearer correct-secret",
            store=store,
        )
        self.assertEqual(status, 200)

    def test_returns_400_without_tenant_id(self):
        os.environ["QA_VIEW_ENFORCE_AUTH"] = "1"
        os.environ["QA_VIEW_SECRET"] = "s"
        store = MemoryChunkStore()
        result, status = build_qa_response(
            doc_id="", page_number=1, tenant_id="",
            auth_header="Bearer s",
            store=store,
        )
        self.assertEqual(status, 400)


# ---------------------------------------------------------------------------
# MemoryChunkStore: thread safety + tenant isolation
# ---------------------------------------------------------------------------

from services.common.ingestion.models import Chunk, ElementType, RouteDecision


class TestMemoryChunkStoreThreadSafety(unittest.TestCase):

    def setUp(self):
        self.store = MemoryChunkStore()

    def test_concurrent_batch_writes(self):
        import threading
        errors = []

        def writer(doc_id):
            try:
                chunks = [
                    Chunk(
                        tenant_id="t1", doc_id=doc_id,
                        page_number=1, element_type=ElementType.TEXT,
                        text="chunk", bbox=[0, 0, 1, 1],
                        source=RouteDecision.DOCLING_TEXT,
                    )
                    for _ in range(100)
                ]
                self.store.upsert_batch(chunks)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(f"doc-{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent writes raised: {errors}")

    def test_tenant_isolation(self):
        c_a = Chunk(
            tenant_id="tenant-a", doc_id="d1",
            page_number=1, element_type=ElementType.TEXT,
            text="tenant A chunk", bbox=[0, 0, 1, 1],
            source=RouteDecision.DOCLING_TEXT,
        )
        c_b = Chunk(
            tenant_id="tenant-b", doc_id="d1",
            page_number=1, element_type=ElementType.TEXT,
            text="tenant B chunk", bbox=[0, 0, 1, 1],
            source=RouteDecision.DOCLING_TEXT,
        )
        self.store.upsert_batch([c_a, c_b])
        self.assertEqual(len(self.store.get_by_doc("d1", "tenant-a")), 1)
        self.assertEqual(len(self.store.get_by_doc("d1", "tenant-b")), 1)
        self.assertEqual(len(self.store.get_by_doc("d1", "tenant-c")), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
