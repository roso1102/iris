"""Native-timeout + transient-only retry tests for Firestore/GCS/Pub/Sub.

Also asserts that every Vertex operation carries a configured deadline and that
retries re-issue byte-identical (idempotent) writes.
"""

import unittest
from unittest.mock import MagicMock

from services.common.cloud import (
    GCS_TIMEOUT_SECONDS,
    NATIVE_TIMEOUTS,
    PUBSUB_TIMEOUT_SECONDS,
    fs_get,
    fs_set,
    gcs_download,
    pubsub_publish,
)
from services.common.reliability import CallTimeout, PermanentError, TransientError


class TestConfiguredDeadlines(unittest.TestCase):

    def test_every_vertex_operation_has_a_bounded_deadline(self):
        from services.common.models.vertex import VERTEX_POLICIES

        required = {
            "embed", "synthesize", "rewrite", "hyde", "route", "rerank",
            "gemini_vision",
        }
        self.assertTrue(required.issubset(VERTEX_POLICIES))
        for name, policy in VERTEX_POLICIES.items():
            self.assertGreater(policy.per_attempt_timeout, 0, name)
            self.assertGreater(policy.overall_deadline, 0, name)
            self.assertGreaterEqual(
                policy.overall_deadline, policy.per_attempt_timeout, name
            )

    def test_cloud_dependencies_have_native_timeouts(self):
        for name in ("firestore", "gcs", "pubsub"):
            self.assertGreater(NATIVE_TIMEOUTS[name], 0, name)


class TestFirestoreTimeouts(unittest.TestCase):

    def test_read_passes_native_timeout(self):
        ref = MagicMock()
        ref.get.return_value = "snap"
        self.assertEqual(fs_get(ref), "snap")
        self.assertEqual(
            ref.get.call_args.kwargs["timeout"], NATIVE_TIMEOUTS["firestore"]
        )

    def test_transient_read_retries(self):
        ref = MagicMock()
        ref.get.side_effect = [TransientError("503"), "snap"]
        self.assertEqual(fs_get(ref), "snap")
        self.assertEqual(ref.get.call_count, 2)

    def test_permanent_read_does_not_retry(self):
        ref = MagicMock()
        ref.get.side_effect = PermanentError("invalid argument")
        with self.assertRaises(PermanentError):
            fs_get(ref)
        self.assertEqual(ref.get.call_count, 1)

    def test_retried_write_is_idempotent(self):
        ref = MagicMock()
        ref.set.side_effect = [TransientError("connection reset"), None]
        fs_set(ref, {"turn_seq": 1}, merge=True)
        self.assertEqual(ref.set.call_count, 2)
        first, second = ref.set.call_args_list
        # Byte-identical payload and merge mode on retry → no duplicated state.
        self.assertIs(first.args[0], second.args[0])
        self.assertEqual(first.kwargs["merge"], second.kwargs["merge"])
        self.assertEqual(first.kwargs["timeout"], second.kwargs["timeout"])


class TestGcsTimeouts(unittest.TestCase):

    def test_download_passes_timeout_and_retries_transient(self):
        blob = MagicMock()
        blob.download_to_filename.side_effect = [TransientError("reset"), None]
        gcs_download(blob, "f.pdf")
        self.assertEqual(blob.download_to_filename.call_count, 2)
        self.assertEqual(
            blob.download_to_filename.call_args.kwargs["timeout"], GCS_TIMEOUT_SECONDS
        )

    def test_download_permanent_does_not_retry(self):
        blob = MagicMock()
        blob.download_to_filename.side_effect = PermanentError("not found")
        with self.assertRaises(PermanentError):
            gcs_download(blob, "f.pdf")
        self.assertEqual(blob.download_to_filename.call_count, 1)


class TestPubSubTimeouts(unittest.TestCase):

    def test_publish_passes_timeout_and_retries_transient(self):
        future = MagicMock()
        future.result.return_value = "msg-1"
        publisher = MagicMock()
        publisher.publish.side_effect = [TransientError("unavailable"), future]
        result = pubsub_publish(publisher, "projects/p/topics/t", b"x", doc_id="d")
        self.assertEqual(result, "msg-1")
        self.assertEqual(publisher.publish.call_count, 2)
        self.assertEqual(
            publisher.publish.call_args.kwargs["timeout"], PUBSUB_TIMEOUT_SECONDS
        )

    def test_publish_result_timeout_is_bounded(self):
        future = MagicMock()
        future.result.side_effect = TimeoutError("slow")
        publisher = MagicMock()
        publisher.publish.return_value = future
        with self.assertRaises((CallTimeout, TimeoutError)):
            pubsub_publish(publisher, "t", b"x")


class TestQdrantWriteIdempotency(unittest.TestCase):

    def _store(self, client):
        from services.common.ingestion.store import QdrantChunkStore

        store = object.__new__(QdrantChunkStore)
        store._client = client
        store._collection = "test"
        return store

    def test_retried_upsert_reuses_deterministic_point_ids(self):
        from services.common.ingestion.models import Chunk, ElementType, RouteDecision

        client = MagicMock()
        store = self._store(client)
        chunk = Chunk(
            tenant_id="tenant-a",
            doc_id="d1",
            page_number=1,
            element_type=ElementType.TEXT,
            text="Some chunk text.",
            bbox=[0.1, 0.1, 0.5, 0.4],
            source=RouteDecision.DOCLING_TEXT,
        )
        chunk.embedding = [0.1] * 768
        store.upsert_batch([chunk])
        store.upsert_batch([chunk])  # simulated redelivery / retry
        ids = [c.kwargs["points"][0].id for c in client.upsert.call_args_list]
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(ids[0], chunk.id)


if __name__ == "__main__":
    unittest.main()
