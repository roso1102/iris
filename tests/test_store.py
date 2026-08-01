"""Phase 1.0 unit tests — chunk store (Task 1.9).

Exercises the MemoryChunkStore round-trip and the store factory fallback
(QDRANT_URL unset -> memory store).
"""

import os
import unittest

from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from services.common.ingestion.store import MemoryChunkStore, get_chunk_store


def _chunk(doc_id: str, tenant_id: str = "tenant-a") -> Chunk:
    return Chunk(
        tenant_id=tenant_id,
        doc_id=doc_id,
        page_number=1,
        element_type=ElementType.TEXT,
        text="Some chunk text.",
        bbox=[0.1, 0.1, 0.5, 0.4],
        source=RouteDecision.DOCLING_TEXT,
    )


class TestMemoryChunkStore(unittest.TestCase):

    def test_upsert_and_get_by_doc(self):
        store = MemoryChunkStore()
        store.upsert_batch([_chunk("d1"), _chunk("d1"), _chunk("d2")])
        self.assertEqual(len(store.get_by_doc("d1")), 2)
        self.assertEqual(len(store.get_by_doc("d2")), 1)
        self.assertEqual(store.get_by_doc("nope"), [])

    def test_empty_batch(self):
        store = MemoryChunkStore()
        self.assertEqual(store.upsert_batch([]), 0)


class TestStoreFactory(unittest.TestCase):

    def test_falls_back_to_memory_when_no_url(self):
        old = os.environ.get("QDRANT_URL")
        try:
            os.environ.pop("QDRANT_URL", None)
            store = get_chunk_store()
            self.assertIsInstance(store, MemoryChunkStore)
        finally:
            if old is not None:
                os.environ["QDRANT_URL"] = old


if __name__ == "__main__":
    unittest.main()
