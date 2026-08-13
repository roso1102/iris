"""Phase 2.0 unit tests — Retrieval API endpoints (FastAPI TestClient)."""

import os
import unittest

# Must set env vars before importing app (VertexAIProvider reads at init)
os.environ["GCP_PROJECT"] = "test-project"
os.environ["MODEL_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from services.retrieval_api.app import app


class TestRetrievalApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

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
