"""Task 5.0b unit tests — POST /documents/upload (retrieval-api).

Covers the full upload path with GCS/Firestore/ingestion patched:
  - auth (missing token -> 401, spoofed tenant ignored)
  - doc_id validation (422)
  - file validation (wrong type, empty, oversized -> 422)
  - duplicate rejection (409)
  - happy path (GCS write + Firestore record + /ingest trigger)
"""

import os
import unittest
from unittest.mock import MagicMock, patch

# Must set env vars before importing app (VertexAIProvider reads at init).
os.environ["GCP_PROJECT"] = "test-project"
os.environ["MODEL_BACKEND"] = "mock"

from fastapi.testclient import TestClient

from services.retrieval_api.app import app, _UPLOAD_MAX_BYTES, _trigger_ingestion

from tests.auth_testing import auth_headers, mock_auth


class TestUploadApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        # Local component tests must never touch real GCS/Firestore/ingestion.
        self._gcs_patcher = patch(
            "services.retrieval_api.app._get_gcs_client",
            return_value=MagicMock(),
        )
        # Firestore default: a doc-ref whose .get() returns a NON-existent
        # snapshot (so the duplicate check passes), overridable per-test.
        def _non_existent_snapshot():
            snap = MagicMock()
            snap.exists = False
            return snap

        self._firestore_patcher = patch(
            "services.retrieval_api.app._get_firestore_client",
            side_effect=lambda: MagicMock(
                document=lambda *a, **k: MagicMock(get=lambda: _non_existent_snapshot())
            ),
        )
        self._ingest_patcher = patch(
            "services.retrieval_api.app._trigger_ingestion",
            return_value={"status": "processing", "doc_id": "doc_new", "total_pages": 5},
        )
        self._gcs_patcher.start()
        self._firestore_patcher.start()
        self._ingest_patcher.start()

    def tearDown(self):
        self._gcs_patcher.stop()
        self._firestore_patcher.stop()
        self._ingest_patcher.stop()

    def _fake_pdf(self, size: int = 1024) -> bytes:
        # Not a real PDF — preflight runs downstream in ingestion-worker, so the
        # upload endpoint only checks type + size. Content is opaque here.
        return b"%PDF-1.4 fake pdf" + b"\x00" * (size - len(b"%PDF-1.4 fake pdf"))

    # ── Auth ────────────────────────────────────────────────────────────────

    def test_upload_missing_token(self):
        resp = self.client.post(
            "/documents/upload",
            data={"doc_id": "doc_new"},
            files={"file": ("test.pdf", self._fake_pdf(), "application/pdf")},
        )
        self.assertEqual(resp.status_code, 401)

    # ── Validation ──────────────────────────────────────────────────────────

    def test_upload_invalid_doc_id(self):
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/documents/upload",
                data={"doc_id": "../etc/passwd"},
                files={"file": ("test.pdf", self._fake_pdf(), "application/pdf")},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 422)

    def test_upload_wrong_content_type(self):
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/documents/upload",
                data={"doc_id": "doc_new"},
                files={"file": ("test.txt", b"hello", "text/plain")},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 422)

    def test_upload_empty_file(self):
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/documents/upload",
                data={"doc_id": "doc_new"},
                files={"file": ("test.pdf", b"", "application/pdf")},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 422)

    def test_upload_oversized_file(self):
        big = b"x" * (_UPLOAD_MAX_BYTES + 1)
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/documents/upload",
                data={"doc_id": "doc_new"},
                files={"file": ("test.pdf", big, "application/pdf")},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("MB limit", resp.json()["detail"])

    # ── Duplicate ───────────────────────────────────────────────────────────

    def test_upload_duplicate_doc_id_rejected(self):
        # Firestore already has the document -> 409.
        existing_snapshot = MagicMock()
        existing_snapshot.exists = True
        with mock_auth(tenant_id="tenant-a"):
            with patch(
                "services.retrieval_api.app._get_firestore_client",
                return_value=MagicMock(),
            ) as fs_mock:
                doc_ref = MagicMock()
                doc_ref.get.return_value = existing_snapshot
                fs_mock.return_value.document.return_value = doc_ref
                resp = self.client.post(
                    "/documents/upload",
                    data={"doc_id": "doc_dup"},
                    files={"file": ("test.pdf", self._fake_pdf(), "application/pdf")},
                    headers=auth_headers(),
                )
        self.assertEqual(resp.status_code, 409)

    # ── Happy path ──────────────────────────────────────────────────────────

    def test_upload_happy_path(self):
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/documents/upload",
                data={"doc_id": "doc_new"},
                files={"file": ("annual-report.pdf", self._fake_pdf(), "application/pdf")},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["doc_id"], "doc_new")
        self.assertEqual(body["status"], "processing")

    def test_upload_never_accepts_client_tenant(self):
        # Spoofed tenant-id in form data must be ignored (JWT is authoritative).
        gcs_mock = MagicMock()
        blob_mock = MagicMock()
        gcs_mock.bucket.return_value.blob.return_value = blob_mock
        with mock_auth(tenant_id="tenant-a"):
            with patch("services.retrieval_api.app._get_gcs_client", return_value=gcs_mock):
                resp = self.client.post(
                    "/documents/upload",
                    data={"doc_id": "doc_new", "tenant_id": "tenant-evil"},
                    files={"file": ("test.pdf", self._fake_pdf(), "application/pdf")},
                    headers=auth_headers(),
                )
        self.assertEqual(resp.status_code, 200)
        # The GCS path must use tenant-a, never tenant-evil.
        blob_path = gcs_mock.bucket.return_value.blob.call_args.args[0]
        self.assertEqual(blob_path, "tenant-a/doc_new.pdf")
        self.assertNotIn("tenant-evil", blob_path)

    # ── _trigger_ingestion (IAM generateIdToken path) ────────────────────────

    def test_trigger_ingestion_mints_id_token_and_posts(self):
        """The trigger must mint an ID token via IAM generateIdToken, not use
        impersonated_credentials.id_token (which doesn't exist)."""
        import services.retrieval_api.app as app_module

        creds = MagicMock()
        creds.token = "source-access-token"
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"token": "minted-id-token"}

        ingest_resp = MagicMock()
        ingest_resp.status_code = 200
        ingest_resp.json.return_value = {"status": "processing", "doc_id": "d1"}

        with patch.object(app_module, "_INGEST_URL", "https://ingest.example"), \
             patch.object(app_module, "_RAW_BUCKET", "iris-raw-pdfs"), \
             patch("google.auth.default", return_value=(creds, None)), \
             patch("requests.post") as post_mock:
            post_mock.side_effect = [fake_resp, ingest_resp]
            result = _trigger_ingestion("tenant-a", "d1")

        self.assertEqual(result["status"], "processing")
        # First call: IAM generateIdToken; second: /ingest with the minted token.
        iam_call, ingest_call = post_mock.call_args_list
        self.assertIn("generateIdToken", iam_call.args[0])
        self.assertIn("source-access-token", iam_call.kwargs["headers"]["Authorization"])
        self.assertEqual(ingest_call.kwargs["headers"]["Authorization"], "Bearer minted-id-token")
        self.assertEqual(ingest_call.kwargs["json"]["gcs_uri"], "gs://iris-raw-pdfs/tenant-a/d1.pdf")


if __name__ == "__main__":
    unittest.main()
