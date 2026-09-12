"""Phase 0.1 tests — stable error envelope, correlation IDs, no leaks."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["GCP_PROJECT"] = "test-project"
os.environ["MODEL_BACKEND"] = "mock"

from fastapi.testclient import TestClient

from services.retrieval_api.app import app, orchestrator
from tests.auth_testing import auth_headers, mock_auth


class TestCorrelationId(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_generated_when_absent(self):
        resp = self.client.get("/livez")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.headers.get("X-Request-ID"))

    def test_valid_request_id_echoed(self):
        resp = self.client.get("/livez", headers={"X-Request-ID": "abc-123_XYZ"})
        self.assertEqual(resp.headers["X-Request-ID"], "abc-123_XYZ")

    def test_malformed_request_id_replaced(self):
        resp = self.client.get("/livez", headers={"X-Request-ID": "bad id!<>"})
        self.assertNotEqual(resp.headers["X-Request-ID"], "bad id!<>")
        self.assertTrue(resp.headers["X-Request-ID"])


class TestErrorEnvelope(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def _assert_envelope(self, body):
        self.assertIn("error", body)
        self.assertIn("code", body["error"])
        self.assertIn("message", body["error"])
        self.assertIn("correlation_id", body["error"])

    def test_missing_token_401_envelope(self):
        resp = self.client.post("/query", json={"query": "funds", "mode": "standard"})
        self.assertEqual(resp.status_code, 401)
        self._assert_envelope(resp.json())
        self.assertEqual(resp.json()["error"]["code"], "UNAUTHENTICATED")

    def test_validation_error_422_envelope(self):
        with mock_auth():
            resp = self.client.post(
                "/query",
                json={"query": "x" * 5000, "mode": "standard"},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 422)
        self._assert_envelope(resp.json())
        self.assertEqual(resp.json()["error"]["code"], "INVALID_REQUEST")

    def test_session_store_down_returns_503_envelope(self):
        with patch("services.retrieval_api.app._get_firestore_client", return_value=None), mock_auth():
            resp = self.client.post(
                "/query",
                json={"query": "government funds", "mode": "standard"},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 503)
        body = resp.json()
        self._assert_envelope(body)
        self.assertEqual(body["error"]["code"], "SESSION_STORE_UNAVAILABLE")

    def test_internal_exception_is_not_leaked(self):
        secret = "/home/app/secret.py token=ABC123 project=my-proj bucket=raw-secret"
        with patch.object(
            orchestrator, "standard_search",
            new=AsyncMock(side_effect=RuntimeError(secret)),
        ), mock_auth():
            resp = self.client.post(
                "/search",
                json={"query": "government funds", "mode": "standard"},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 500)
        raw = resp.text
        body = resp.json()
        self._assert_envelope(body)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        for forbidden in ("secret.py", "ABC123", "my-proj", "raw-secret", "RuntimeError"):
            self.assertNotIn(forbidden, raw)

    def test_document_ownership_read_failure_is_stable(self):
        fake = MagicMock()
        fake.document.return_value.get.side_effect = RuntimeError("provider secret")
        with patch("services.retrieval_api.app._get_firestore_client", return_value=fake), mock_auth():
            resp = self.client.post(
                "/search",
                json={"query": "funds", "doc_ids": ["doc-1"]},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 503)
        self._assert_envelope(resp.json())
        self.assertEqual(resp.json()["error"]["code"], "DEPENDENCY_UNAVAILABLE")
        self.assertNotIn("provider secret", resp.text)


if __name__ == "__main__":
    unittest.main()
