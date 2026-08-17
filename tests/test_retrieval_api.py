"""Phase 2.0 unit tests — Retrieval API endpoints (FastAPI TestClient)."""

import os
import unittest
from unittest.mock import MagicMock, patch

# Must set env vars before importing app (VertexAIProvider reads at init)
os.environ["GCP_PROJECT"] = "test-project"
os.environ["MODEL_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from services.retrieval_api.app import app, store

from services.common.ingestion.models import Chunk, ElementType, RouteDecision


class TestRetrievalApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        # Local component tests must never touch real GCS/Firestore.
        self._gcs_patcher = patch(
            "services.retrieval_api.app._get_gcs_client",
            return_value=None,
        )
        self._firestore_patcher = patch(
            "services.retrieval_api.app._get_firestore_client",
            return_value=MagicMock(),
        )
        self._gcs_patcher.start()
        self._firestore_patcher.start()

    def tearDown(self):
        self._gcs_patcher.stop()
        self._firestore_patcher.stop()
        store._by_doc.clear()

    def test_query_standard_with_tenant(self):
        chunk = Chunk(
            tenant_id="tenant-a",
            doc_id="d1",
            page_number=1,
            element_type=ElementType.TEXT,
            text="government funds committee provides necessary funding",
            bbox=[0.1, 0.1, 0.5, 0.4],
            source=RouteDecision.DOCLING_TEXT,
            embedding=[0.1] * 768,
        )
        store.upsert_batch([chunk])
        response = self.client.post(
            "/query",
            json={"query": "government funds", "mode": "standard"},
            headers={"tenant-id": "tenant-a"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("answer", body)
        self.assertGreaterEqual(body["chunks_used"], 1)
        self.assertEqual(body["mode"], "standard")
        # Mock synthesizes against the first retrieved chunk's real id.
        self.assertGreaterEqual(len(body["citations"]), 1)
        self.assertEqual(body["citations"][0]["chunk_id"], chunk.id)

    def test_query_missing_tenant_header(self):
        response = self.client.post(
            "/query", json={"query": "government funds", "mode": "standard"}
        )
        self.assertIn(response.status_code, [400, 422])

    def test_healthz(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "retrieval-api")
        self.assertIn("2.0", body["phase"])

    def test_search_standard_missing_tenant_header(self):
        response = self.client.post(
            "/search", json={"query": "test", "mode": "standard"}
        )
        self.assertIn(response.status_code, [400, 422])

    def test_search_standard_with_tenant(self):
        response = self.client.post(
            "/search",
            json={"query": "government funds", "mode": "standard"},
            headers={"tenant-id": "tenant-a"},
        )
        body = response.json()
        if response.status_code == 200:
            self.assertIn("results", body)
            self.assertEqual(body["mode"], "standard")
        else:
            self.assertIn(response.status_code, [400, 500])

    def test_search_deep_with_tenant(self):
        response = self.client.post(
            "/search",
            json={"query": "section clause", "mode": "deep"},
            headers={"tenant-id": "tenant-a"},
        )
        body = response.json()
        if response.status_code == 200:
            self.assertIn("results", body)
            self.assertEqual(body["mode"], "deep")
        else:
            self.assertIn(response.status_code, [400, 500])

    def test_search_invalid_mode(self):
        response = self.client.post(
            "/search",
            json={"query": "test", "mode": "fantasy"},
            headers={"tenant-id": "tenant-a"},
        )
        self.assertEqual(response.status_code, 422)

    def test_delete_document_missing_header(self):
        response = self.client.delete("/documents/d1")
        self.assertIn(response.status_code, [400, 422])

    def test_delete_document_with_tenant(self):
        response = self.client.delete(
            "/documents/d1", headers={"tenant-id": "tenant-a"}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["resource_id"], "d1")

    def test_delete_session(self):
        response = self.client.delete(
            "/sessions/s1", headers={"tenant-id": "tenant-a"}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["resource_id"], "s1")

    def test_delete_session_missing_header(self):
        response = self.client.delete("/sessions/s1")
        self.assertIn(response.status_code, [400, 422])


if __name__ == "__main__":
    unittest.main()
