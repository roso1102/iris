"""Phase 2.0 unit tests — ChunkStore search/delete methods (MemoryChunkStore)."""

import unittest

from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from services.common.ingestion.store import MemoryChunkStore, get_chunk_store


def _chunk(
    doc_id: str,
    tenant_id: str = "tenant-a",
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


class TestMemoryChunkStoreSearch(unittest.TestCase):

    def setUp(self):
        self.store = MemoryChunkStore()
        self.c1 = _chunk("d1", "tenant-a", "committee provides necessary funding")
        self.c2 = _chunk("d1", "tenant-a", "section five of the act")
        self.c3 = _chunk("d2", "tenant-a", "high court dismissed petition")
        self.c4 = _chunk("d3", "tenant-b", "tenant b document")
        self.store.upsert_batch([self.c1, self.c2, self.c3, self.c4])

    def test_search_dense_tenant_filter(self):
        query_embedding = [0.1] * 768
        results = self.store.search_dense(query_embedding, "tenant-a", limit=10)
        ids = {r[0] for r in results}
        self.assertEqual(len(ids), 3)
        for cid in ids:
            self.assertNotEqual(cid, self.c4.id)

    def test_search_dense_doc_filter(self):
        query_embedding = [0.1] * 768
        results = self.store.search_dense(
            query_embedding, "tenant-a", doc_ids=["d2"], limit=10
        )
        ids = {r[0] for r in results}
        self.assertEqual(ids, {self.c3.id})

    def test_search_sparse(self):
        results = self.store.search_sparse(
            "committee funding", "tenant-a", limit=10
        )
        ids = [r[0] for r in results]
        self.assertEqual(len(ids), 1)
        self.assertIn(self.c1.id, ids)

    def test_search_sparse_empty_query(self):
        results = self.store.search_sparse("", "tenant-a")
        self.assertEqual(results, [])

    def test_delete_by_doc(self):
        deleted = self.store.delete_by_doc("d1", "tenant-a")
        self.assertEqual(deleted, 2)
        results = self.store.get_by_doc("d1", "tenant-a")
        self.assertEqual(results, [])

    def test_delete_by_doc_tenant_b(self):
        deleted = self.store.delete_by_doc("d3", "tenant-b")
        self.assertEqual(deleted, 1)

    def test_delete_by_doc_not_affected_other_tenant(self):
        self.store.delete_by_doc("d1", "tenant-b")
        results = self.store.get_by_doc("d1", "tenant-a")
        self.assertEqual(len(results), 2)

    def test_delete_by_session(self):
        deleted = self.store.delete_by_session("sess-1", "tenant-a")
        self.assertEqual(deleted, 3)
        self.assertEqual(self.store.get_by_doc("d1", "tenant-a"), [])

    def test_delete_by_session_tenant_b_not_affected(self):
        deleted = self.store.delete_by_session("sess-1", "tenant-b")
        self.assertEqual(deleted, 1)
        results = self.store.get_by_doc("d1", "tenant-a")
        self.assertEqual(len(results), 2)

    def test_get_by_ids(self):
        chunks = self.store.get_by_ids([self.c1.id, self.c2.id], "tenant-a")
        ids = {c.id for c in chunks}
        self.assertEqual(ids, {self.c1.id, self.c2.id})

    def test_get_by_ids_cross_tenant_excluded(self):
        chunks = self.store.get_by_ids([self.c1.id, self.c4.id], "tenant-a")
        ids = {c.id for c in chunks}
        self.assertEqual(ids, {self.c1.id})

    def test_get_by_ids_missing(self):
        chunks = self.store.get_by_ids([self.c1.id, "nonexistent"], "tenant-a")
        ids = {c.id for c in chunks}
        self.assertEqual(ids, {self.c1.id})

    def test_get_by_ids_empty(self):
        self.assertEqual(self.store.get_by_ids([], "tenant-a"), [])


class TestRetrievalStoreFactory(unittest.TestCase):
    def test_falls_back_to_memory_when_no_url(self):
        import os
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
