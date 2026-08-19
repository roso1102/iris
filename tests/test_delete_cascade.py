"""Tier 1 integration tests — cascading delete (store + API level).

Store level: seed MemoryChunkStore, delete_by_doc -> count drops to 0,
other tenants/docs untouched.

API level: FastAPI TestClient on retrieval_api/app with `_get_firestore_client`
patched to a mock, verifying the Firestore doc delete is invoked as part of the
cascade. Zero GCP, zero network.

Phase 4.0: endpoints require Firebase JWT auth (patched verifier); no
`tenant-id` header is accepted.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["MODEL_BACKEND"] = "mock"
os.environ["GCP_PROJECT"] = "test-project"

from fastapi.testclient import TestClient

from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from services.common.ingestion.store import MemoryChunkStore
from services.retrieval_api.app import app, store
from tests.auth_testing import auth_headers, mock_auth


def _chunk(
    doc_id: str,
    tenant_id: str,
    text: str = "Some chunk text.",
    session_id: str = "sess-1",
) -> Chunk:
    return Chunk(
        tenant_id=tenant_id,
        doc_id=doc_id,
        session_id=session_id,
        page_number=1,
        element_type=ElementType.TEXT,
        text=text,
        bbox=[0.1, 0.1, 0.5, 0.4],
        source=RouteDecision.DOCLING_TEXT,
        embedding=[0.1] * 768,
    )


class TestStoreDeleteCascade(unittest.TestCase):
    """MemoryChunkStore.delete_by_doc cascade semantics."""

    def setUp(self):
        self.store = MemoryChunkStore()
        self.store.upsert_batch(
            [
                _chunk("d1", "tenant-a", "committee funding"),
                _chunk("d1", "tenant-a", "section five"),
                _chunk("d2", "tenant-a", "high court petition"),
                _chunk("d1", "tenant-b", "tenant b private"),
            ]
        )

    def test_delete_by_doc_removes_all_tenant_chunks(self):
        deleted = self.store.delete_by_doc("d1", "tenant-a")
        self.assertEqual(deleted, 2)
        self.assertEqual(self.store.get_by_doc("d1", "tenant-a"), [])

    def test_delete_does_not_touch_other_tenant_or_doc(self):
        self.store.delete_by_doc("d1", "tenant-a")
        self.assertEqual(len(self.store.get_by_doc("d2", "tenant-a")), 1)
        self.assertEqual(len(self.store.get_by_doc("d1", "tenant-b")), 1)

    def test_delete_missing_doc_returns_zero(self):
        self.assertEqual(self.store.delete_by_doc("ghost", "tenant-a"), 0)


class TestApiDeleteCascade(unittest.TestCase):
    """DELETE endpoints remove store chunks AND cascade to Firestore/GCS mocks."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        # Reset the shared store so each test starts clean.
        store._by_doc.clear()

    def _fake_firestore(self):
        """Return a firestore-mock whose .document(path).delete() is tracked."""
        fake = MagicMock()
        fake.document.return_value.delete.return_value = None
        fake.collection.return_value.stream.return_value = []
        return fake

    def test_delete_document_cascades_to_store_and_firestore(self):
        store.upsert_batch([_chunk("d1", "tenant-a"), _chunk("d1", "tenant-a")])
        fake = self._fake_firestore()

        with patch("services.retrieval_api.app._get_firestore_client", return_value=fake), mock_auth(tenant_id="tenant-a"):
            resp = self.client.delete(
                "/documents/d1", headers=auth_headers()
            )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["resource_id"], "d1")
        self.assertEqual(body["deleted_chunks"], 2)
        self.assertEqual(store.get_by_doc("d1", "tenant-a"), [])
        # Firestore cascade: tenants/tenant-a/documents/d1
        fake.document.assert_called_with("tenants/tenant-a/documents/d1")
        fake.document("tenants/tenant-a/documents/d1").delete.assert_called_once()

    def test_delete_session_cascades_to_firestore(self):
        store.upsert_batch([_chunk("d1", "tenant-a", session_id="s1")])
        fake = self._fake_firestore()

        with patch("services.retrieval_api.app._get_firestore_client", return_value=fake), mock_auth(tenant_id="tenant-a"):
            resp = self.client.delete(
                "/sessions/s1", headers=auth_headers()
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["resource_id"], "s1")
        self.assertEqual(store.get_by_doc("d1", "tenant-a"), [])
        # Firestore cascade: tenants/tenant-a/sessions/s1
        fake.document.assert_called_with("tenants/tenant-a/sessions/s1")
        fake.document("tenants/tenant-a/sessions/s1").delete.assert_called_once()

    def test_delete_document_missing_token(self):
        resp = self.client.delete("/documents/d1")
        self.assertEqual(resp.status_code, 401)

    def test_delete_session_missing_token(self):
        resp = self.client.delete("/sessions/s1")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
