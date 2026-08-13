"""Phase 2.0 unit tests — SearchOrchestrator (Standard + Deep)."""

import asyncio
import unittest

from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from services.common.ingestion.store import MemoryChunkStore
from services.common.models.mock import MockModelProvider
from services.common.retrieval.search import SearchOrchestrator


def _chunk(
    doc_id: str,
    tenant_id: str = "tenant-a",
    text: str = "Some chunk text.",
) -> Chunk:
    return Chunk(
        tenant_id=tenant_id,
        doc_id=doc_id,
        session_id="sess-1",
        page_number=1,
        element_type=ElementType.TEXT,
        text=text,
        bbox=[0.1, 0.1, 0.5, 0.4],
        source=RouteDecision.DOCLING_TEXT,
        embedding=[0.1] * 768,
    )


class TestSearchOrchestrator(unittest.TestCase):

    def setUp(self):
        self.store = MemoryChunkStore()
        self.provider = MockModelProvider(embed_dim=768)
        self.orchestrator = SearchOrchestrator(
            store=self.store, provider=self.provider
        )
        self.store.upsert_batch(
            [
                _chunk("d1", tenant_id="tenant-a", text="committee provides necessary funding"),
                _chunk("d1", tenant_id="tenant-a", text="section five notification"),
                _chunk("d2", tenant_id="tenant-a", text="high court dismissed petition"),
                _chunk("d3", tenant_id="tenant-b", text="tenant b private data"),
            ]
        )

    def _run(self, coro):
        return asyncio.run(coro)

    def test_standard_search_returns_results(self):
        results = self._run(
            self.orchestrator.standard_search(
                "committee funding", "tenant-a", top_k=5
            )
        )
        self.assertGreaterEqual(len(results), 1)

    def test_standard_search_tenant_isolation(self):
        results = self._run(
            self.orchestrator.standard_search(
                "private data", "tenant-a", top_k=10
            )
        )
        for r in results:
            self.assertEqual(r.tenant_id, "tenant-a")
            self.assertNotEqual(r.doc_id, "d3")

    def test_standard_search_doc_filter(self):
        results = self._run(
            self.orchestrator.standard_search(
                "petition", "tenant-a", doc_ids=["d2"], top_k=5
            )
        )
        self.assertGreaterEqual(len(results), 0)
        for r in results:
            self.assertEqual(r.doc_id, "d2")

    def test_deep_search_returns_results(self):
        results = self._run(
            self.orchestrator.deep_search(
                "section clause", "tenant-a", top_k=5
            )
        )
        self.assertGreaterEqual(len(results), 1)

    def test_deep_search_respects_tenant(self):
        results = self._run(
            self.orchestrator.deep_search(
                "data", "tenant-a", top_k=5
            )
        )
        for r in results:
            self.assertEqual(r.tenant_id, "tenant-a")


if __name__ == "__main__":
    unittest.main()
