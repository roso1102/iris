"""Pipeline 6 tests — session memory (auto-create, message persistence, history loading)."""

import os
import unittest
from unittest.mock import MagicMock, patch, call

os.environ["GCP_PROJECT"] = "test-project"
os.environ["MODEL_BACKEND"] = "mock"

from fastapi.testclient import TestClient

from services.retrieval_api.app import (
    app,
    store,
    _create_firestore_session,
    _append_firestore_messages,
    _load_firestore_messages,
    _session_exists,
)
from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from tests.auth_testing import auth_headers, mock_auth


def _fake_firestore():
    """Firestore mock with configurable document/collection behavior."""
    fake = MagicMock()
    fake.document.return_value.get.return_value.exists = False
    fake.document.return_value.set.return_value = None
    fake.document.return_value.delete.return_value = None
    fake.collection.return_value.stream.return_value = []
    return fake


# ── Helper unit tests ───────────────────────────────────────────────


class TestFirestoreHelpers(unittest.TestCase):
    """Direct tests for the Firestore session helper functions."""

    def setUp(self):
        self._patcher = patch(
            "services.retrieval_api.app._get_firestore_client",
            return_value=MagicMock(),
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_create_firestore_session_returns_uuid(self):
        fake = _fake_firestore()
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ):
            sid = _create_firestore_session("tenant-a")
        self.assertIsInstance(sid, str)
        self.assertGreater(len(sid), 0)
        fake.document.return_value.set.assert_called_once()
        written = fake.document.return_value.set.call_args.args[0]
        self.assertEqual(written["tenant_id"], "tenant-a")
        self.assertEqual(written["session_id"], sid)

    def test_create_firestore_session_survives_write_failure(self):
        fake = _fake_firestore()
        fake.document.return_value.set.side_effect = Exception("write failed")
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ):
            sid = _create_firestore_session("tenant-a")
        self.assertIsInstance(sid, str)

    def test_append_firestore_messages_writes_two_docs(self):
        fake = _fake_firestore()
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ):
            _append_firestore_messages("tenant-a", "s1", [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi there"},
            ])
        col = fake.collection.return_value
        self.assertEqual(col.add.call_count, 2)
        first_msg = col.add.call_args_list[0].args[0]
        self.assertEqual(first_msg["role"], "user")
        self.assertEqual(first_msg["content"], "hello")
        second_msg = col.add.call_args_list[1].args[0]
        self.assertEqual(second_msg["role"], "assistant")

    def test_append_firestore_messages_survives_failure(self):
        fake = _fake_firestore()
        fake.collection.return_value.add.side_effect = Exception("write failed")
        # Should not raise
        _append_firestore_messages("tenant-a", "s1", [
            {"role": "user", "content": "hello"},
        ])

    def test_load_firestore_messages_returns_chronological(self):
        fake = _fake_firestore()
        # Simulate Firestore returning newest-first (as ORDER BY desc does)
        # DocumentSnapshot.get(field) returns the field value
        def _make_doc(data):
            m = MagicMock()
            m.get.side_effect = lambda field, *a: data.get(field, *a[0:]) if a else data[field]
            return m

        msg_newest = _make_doc({"role": "assistant", "content": "B"})
        msg_oldest = _make_doc({"role": "user", "content": "A"})
        fake.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = [
            msg_newest,
            msg_oldest,
        ]
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ):
            result = _load_firestore_messages("tenant-a", "s1", limit=6)
        # Must be reversed to chronological (oldest first)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["role"], "user")
        self.assertEqual(result[0]["content"], "A")
        self.assertEqual(result[1]["role"], "assistant")
        self.assertEqual(result[1]["content"], "B")

    def test_load_firestore_messages_empty_on_query_failure(self):
        fake = _fake_firestore()
        fake.collection.return_value.order_by.return_value.limit.return_value.stream.side_effect = Exception("query failed")
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ):
            result = _load_firestore_messages("tenant-a", "s1")
        self.assertEqual(result, [])

    def test_load_firestore_messages_empty_when_no_docs(self):
        fake = _fake_firestore()
        fake.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = []
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ):
            result = _load_firestore_messages("tenant-a", "s1")
        self.assertEqual(result, [])

    def test_session_exists_returns_true_when_doc_found(self):
        fake = _fake_firestore()
        fake.document.return_value.get.return_value.exists = True
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ):
            self.assertTrue(_session_exists("tenant-a", "s1"))

    def test_session_exists_returns_false_when_doc_missing(self):
        fake = _fake_firestore()
        fake.document.return_value.get.return_value.exists = False
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ):
            self.assertFalse(_session_exists("tenant-a", "s1"))

    def test_session_exists_returns_true_when_query_fails(self):
        fake = _fake_firestore()
        fake.document.return_value.get.side_effect = Exception("query failed")
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ):
            # Graceful: don't block the request
            self.assertTrue(_session_exists("tenant-a", "s1"))


# ── /query endpoint integration tests ───────────────────────────────


class TestQuerySessionMemory(unittest.TestCase):
    """Test /query endpoint with session_id scenarios."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self._gcs = patch(
            "services.retrieval_api.app._get_gcs_client", return_value=None
        )
        self._fs = patch(
            "services.retrieval_api.app._get_firestore_client",
            return_value=MagicMock(),
        )
        self._gcs.start()
        self._fs.start()
        store._by_doc.clear()

    def tearDown(self):
        self._gcs.stop()
        self._fs.stop()

    def _seed_chunk(self, tenant="tenant-a"):
        chunk = Chunk(
            tenant_id=tenant,
            doc_id="d1",
            page_number=1,
            element_type=ElementType.TEXT,
            text="government funds committee provides necessary funding",
            bbox=[0.1, 0.1, 0.5, 0.4],
            source=RouteDecision.DOCLING_TEXT,
            embedding=[0.1] * 768,
        )
        store.upsert_batch([chunk])

    def test_query_auto_creates_session_when_none_provided(self):
        self._seed_chunk()
        fake = _fake_firestore()
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ), mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/query",
                json={"query": "government funds", "mode": "standard"},
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("session_id", body)
        self.assertIsNotNone(body["session_id"])
        self.assertGreater(len(body["session_id"]), 0)
        # Session document was created
        fake.document.return_value.set.assert_called()

    def test_query_returns_provided_session_id(self):
        self._seed_chunk()
        fake = _fake_firestore()
        fake.document.return_value.get.return_value.exists = True
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ), mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/query",
                json={
                    "query": "government funds",
                    "mode": "standard",
                    "session_id": "existing-session",
                },
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["session_id"], "existing-session")

    def test_query_404_for_nonexistent_session(self):
        self._seed_chunk()
        fake = _fake_firestore()
        fake.document.return_value.get.return_value.exists = False
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ), mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/query",
                json={
                    "query": "government funds",
                    "mode": "standard",
                    "session_id": "ghost-session",
                },
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 404)

    def test_query_writes_messages_after_synthesis(self):
        self._seed_chunk()
        fake = _fake_firestore()
        fake.document.return_value.get.return_value.exists = True
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ), mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/query",
                json={
                    "query": "government funds",
                    "mode": "standard",
                    "session_id": "s1",
                },
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 200)
        # Messages sub-collection should have 2 writes (user + assistant)
        col = fake.collection.return_value
        self.assertEqual(col.add.call_count, 2)
        first_msg = col.add.call_args_list[0].args[0]
        self.assertEqual(first_msg["role"], "user")
        self.assertEqual(first_msg["content"], "government funds")
        second_msg = col.add.call_args_list[1].args[0]
        self.assertEqual(second_msg["role"], "assistant")
        self.assertIn("content", second_msg)

    def test_query_loads_server_history_when_session_provided(self):
        self._seed_chunk()
        fake = _fake_firestore()
        fake.document.return_value.get.return_value.exists = True
        # Simulate 2 messages in Firestore (newest-first as Firestore returns them)
        msg1 = MagicMock()
        msg1.get.return_value = {"role": "user", "content": "previous question"}
        msg2 = MagicMock()
        msg2.get.return_value = {"role": "assistant", "content": "previous answer"}
        fake.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = [
            msg2,
            msg1,
        ]
        with patch(
            "services.retrieval_api.app._get_firestore_client", return_value=fake
        ), mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/query",
                json={
                    "query": "what about that?",
                    "mode": "standard",
                    "session_id": "s1",
                },
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 200)
        # Verify the history was loaded (reversed to chronological)
        stream_call = fake.collection.return_value.order_by.return_value.limit.return_value.stream
        stream_call.assert_called_once()

    def test_query_validates_session_id_format(self):
        self._seed_chunk()
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/query",
                json={
                    "query": "test",
                    "mode": "standard",
                    "session_id": "../evil",
                },
                headers=auth_headers(),
            )
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
