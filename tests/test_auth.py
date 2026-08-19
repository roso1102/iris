"""Phase 4.0 unit tests — auth dependency, tenant rewrite, ID validation."""

import os
import unittest
from unittest.mock import patch

# Must set env vars before importing app (VertexAIProvider reads at init).
os.environ["GCP_PROJECT"] = "test-project"
os.environ["MODEL_BACKEND"] = "mock"

from fastapi.testclient import TestClient

from tests.auth_testing import auth_headers, mock_auth

from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from services.common.retrieval.models import QueryRequest, SearchRequest, SessionCreateRequest
from services.retrieval_api.app import app, store


class TestAuthDependency(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self._gcs = patch(
            "services.retrieval_api.app._get_gcs_client", return_value=None
        )
        self._fs = patch(
            "services.retrieval_api.app._get_firestore_client", return_value=None
        )
        self._gcs.start()
        self._fs.start()
        store._by_doc.clear()

    def tearDown(self):
        self._gcs.stop()
        self._fs.stop()

    def _chunk(self, tenant_id: str, doc_id: str, text: str) -> Chunk:
        return Chunk(
            tenant_id=tenant_id,
            doc_id=doc_id,
            page_number=1,
            element_type=ElementType.TEXT,
            text=text,
            bbox=[0.1, 0.1, 0.5, 0.4],
            source=RouteDecision.DOCLING_TEXT,
            embedding=[0.1] * 768,
        )

    def test_query_without_token_401(self):
        resp = self.client.post("/query", json={"query": "funds", "mode": "standard"})
        self.assertEqual(resp.status_code, 401)

    def test_query_malformed_token_401(self):
        resp = self.client.post(
            "/query",
            json={"query": "funds", "mode": "standard"},
            headers={"Authorization": "NotABearer abc"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_token_without_tenant_claim_403(self):
        with patch(
            "services.common.auth.jwt.verify_firebase_token",
            return_value={"uid": "u1", "role": "member"},
        ):
            resp = self.client.post(
                "/query",
                json={"query": "funds", "mode": "standard"},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 403)

    def test_valid_token_returns_200(self):
        store.upsert_batch([self._chunk("tenant-a", "d1", "government funds committee provides funding")])
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/query",
                json={"query": "government funds committee funding", "mode": "standard"},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 200)

    def test_cross_tenant_rewrite_ignores_spoofed_header(self):
        """Test 4-A local analog: spoofed tenant-id header must be ignored."""
        store.upsert_batch([
            self._chunk("tenant-a", "d1", "tenant A committee funding"),
            self._chunk("tenant-b", "d2", "tenant B high court petition"),
        ])
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/search",
                json={"query": "committee funding", "mode": "standard"},
                headers={"tenant-id": "tenant-b", **auth_headers()},
            )
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get("results", [])
        doc_ids = {r["doc_id"] for r in results}
        self.assertNotIn("d2", doc_ids)
        self.assertNotIn("tenant-b", {r["tenant_id"] for r in results})

    def test_cross_tenant_rewrite_ignores_body_tenant(self):
        store.upsert_batch([
            self._chunk("tenant-a", "d1", "tenant A committee funding"),
            self._chunk("tenant-b", "d2", "tenant B high court petition"),
        ])
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/search",
                json={"query": "committee funding", "mode": "standard", "tenant_id": "tenant-b"},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 200)
        doc_ids = {r["doc_id"] for r in resp.json().get("results", [])}
        self.assertNotIn("d2", doc_ids)

    def test_id_validation_rejects_traversal(self):
        # Encoded slash in a path segment is normalized by the router before
        # reaching our handler, so it can't smuggle a traversal (404, not 422).
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.delete(
                "/documents/../tenant-b/secret",
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 404)
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.delete(
                "/documents/d1%2F..%2F..",
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 404)
        # A decoded traversal value is rejected at the handler with 422.
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.delete(
                "/documents/%2e%2e/..%2f..%2fetc",
                headers=auth_headers(),
            )
        self.assertIn(resp.status_code, [404, 422])

    def test_query_oversized_rejected(self):
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/query",
                json={"query": "x" * 5000, "mode": "standard"},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 422)

    def test_top_k_capped_for_synthesis(self):
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/query",
                json={"query": "funds", "mode": "standard", "top_k": 100},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 422)

    def test_livez_unauthenticated(self):
        resp = self.client.get("/livez")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
