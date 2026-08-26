"""Phase 4.0 tests — session CRUD endpoints + signed view URL."""

import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["GCP_PROJECT"] = "test-project"
os.environ["MODEL_BACKEND"] = "mock"

from fastapi.testclient import TestClient

from tests.auth_testing import auth_headers, mock_auth

from services.retrieval_api.app import app, store


def _fake_firestore():
    """Firestore mock: document().get/set/update/delete tracked, collection stream configurable."""
    fake = MagicMock()
    fake.document.return_value.get.return_value.exists = False
    fake.document.return_value.set.return_value = None
    fake.document.return_value.delete.return_value = None
    fake.collection.return_value.stream.return_value = []
    return fake


class TestSessionsApi(unittest.TestCase):

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

    def test_create_session_requires_auth(self):
        resp = self.client.post("/sessions", json={"name": "S1"})
        self.assertEqual(resp.status_code, 401)

    def test_create_session_uses_jwt_tenant(self):
        fake = _fake_firestore()
        fake.document.return_value.get.return_value.exists = False
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ), mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/sessions",
                json={"name": "Budget review", "document_ids": ["d1", "d2"]},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["tenant_id"], "tenant-a")
        self.assertTrue(body["session_id"])
        # Firestore path is prefixed with the JWT tenant, never a body tenant.
        written_path = fake.document.call_args.args[0]
        self.assertTrue(written_path.startswith("tenants/tenant-a/sessions/"))
        written = fake.document.return_value.set.call_args.args[0]
        self.assertEqual(written["tenant_id"], "tenant-a")
        self.assertEqual(written["document_ids"], ["d1", "d2"])

    def test_create_session_rejects_traversal_doc_ids(self):
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=None
        ), mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/sessions",
                json={"name": "S", "document_ids": ["../evil"]},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 422)

    def test_delete_session_cascades(self):
        fake = _fake_firestore()
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ), mock_auth(tenant_id="tenant-a"):
            resp = self.client.delete("/sessions/s1", headers=auth_headers())
        self.assertEqual(resp.status_code, 200)
        fake.document.assert_called_with("tenants/tenant-a/sessions/s1")



class TestViewUrl(unittest.TestCase):

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

    def test_view_url_requires_auth(self):
        resp = self.client.get("/documents/d1/view-url")
        self.assertEqual(resp.status_code, 401)

    def test_view_url_ownership_check_404(self):
        fake = _fake_firestore()
        fake.document.return_value.get.return_value.exists = False
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ), mock_auth(tenant_id="tenant-a"):
            resp = self.client.get("/documents/d1/view-url", headers=auth_headers())
        self.assertEqual(resp.status_code, 404)

    def test_view_url_signed_with_jwt_tenant_path(self):
        fake = _fake_firestore()
        fake.document.return_value.get.return_value.exists = True
        blob = MagicMock()
        blob.generate_signed_url.return_value = "https://signed.example/d1.pdf"
        gcs = MagicMock()
        gcs.bucket.return_value.blob.return_value = blob
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ), patch(
            "services.retrieval_api.app._get_gcs_client", return_value=gcs
        ), mock_auth(tenant_id="tenant-a"):
            resp = self.client.get("/documents/d1/view-url", headers=auth_headers())
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["url"], "https://signed.example/d1.pdf")
        self.assertEqual(body["expires_in_seconds"], 900)
        # Blob path is the JWT tenant prefix.
        blob_path = gcs.bucket.return_value.blob.call_args.args[0]
        self.assertEqual(blob_path, "tenant-a/d1.pdf")
        blob.generate_signed_url.assert_called_once()
        kwargs = blob.generate_signed_url.call_args.kwargs
        self.assertEqual(kwargs["version"], "v4")
        self.assertEqual(kwargs["method"], "GET")

    def test_view_url_rejects_traversal(self):
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.get("/documents/..%2F..%2Fetc%2Fpasswd/view-url", headers=auth_headers())
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
