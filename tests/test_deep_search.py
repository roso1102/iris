"""Tier 1 integration tests — Deep Search HyDE/rewrite path.

Verifies that `SearchOrchestrator.deep_search`:
  1. calls rewrite_query(query, history) -> self-contained query
  2. calls generate_hyde(rewritten) -> hypothetical answer
  3. embeds the HyDE text (NOT the raw query) for the dense search
  4. returns results from the seeded store, respecting tenant isolation

Uses a call-recording MockModelProvider subclass because the stock mock returns
a constant embedding vector that cannot distinguish "embedded the HyDE" from
"embedded the raw query".
"""

import asyncio
import unittest

from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from services.common.ingestion.store import MemoryChunkStore
from services.common.models.mock import MockModelProvider
from services.common.retrieval.search import SearchOrchestrator


class RecordingProvider(MockModelProvider):
    """MockModelProvider that records every embed/rewrite/HyDE call."""

    def __init__(self, embed_dim: int = 768):
        super().__init__(embed_dim=embed_dim)
        self.embed_calls: list[str] = []
        self.rewrite_calls: list[tuple[str, list]] = []
        self.hyde_calls: list[str] = []

    def embed(self, text: str):
        self.embed_calls.append(text)
        return [0.1] * self.embed_dim

    def rewrite_query(self, query: str, history: list):
        self.rewrite_calls.append((query, history))
        return f"REWRITTEN: {query}"

    def generate_hyde(self, query: str):
        self.hyde_calls.append(query)
        return f"HYDE ANSWER about {query}"


def _chunk(doc_id: str, text: str, tenant_id: str = "tenant-a") -> Chunk:
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


class TestDeepSearch(unittest.TestCase):

    def setUp(self):
        self.store = MemoryChunkStore()
        self.store.upsert_batch(
            [
                _chunk("d1", "committee provides necessary funding"),
                _chunk("d1", "section five notification"),
                _chunk("d2", "high court dismissed petition"),
                _chunk("d3", "tenant b private data", tenant_id="tenant-b"),
            ]
        )
        self.provider = RecordingProvider()
        self.orchestrator = SearchOrchestrator(
            store=self.store, provider=self.provider
        )

    def _run(self, coro):
        return asyncio.run(coro)

    def test_rewrite_query_called_with_query_and_history(self):
        history = [{"role": "user", "content": "earlier question"}]
        self._run(
            self.orchestrator.deep_search(
                "what is the funding", "tenant-a", history=history, top_k=5
            )
        )
        self.assertEqual(len(self.provider.rewrite_calls), 1)
        query, h = self.provider.rewrite_calls[0]
        self.assertEqual(query, "what is the funding")
        self.assertEqual(h, history)

    def test_generate_hyde_called_with_rewritten_query(self):
        self._run(
            self.orchestrator.deep_search("funding rules", "tenant-a", top_k=5)
        )
        self.assertEqual(len(self.provider.hyde_calls), 1)
        self.assertEqual(self.provider.hyde_calls[0], "REWRITTEN: funding rules")

    def test_embed_uses_hyde_not_raw_query(self):
        self._run(
            self.orchestrator.deep_search("funding rules", "tenant-a", top_k=5)
        )
        # embed must have been called with the HyDE answer, not the raw query
        self.assertEqual(len(self.provider.embed_calls), 1)
        embedded = self.provider.embed_calls[0]
        self.assertIn("HYDE ANSWER", embedded)
        self.assertNotEqual(embedded, "funding rules")

    def test_deep_search_returns_results_from_store(self):
        results = self._run(
            self.orchestrator.deep_search("funding rules", "tenant-a", top_k=5)
        )
        self.assertGreaterEqual(len(results), 1)

    def test_deep_search_tenant_isolation(self):
        results = self._run(
            self.orchestrator.deep_search("private data", "tenant-a", top_k=10)
        )
        for r in results:
            self.assertEqual(r.tenant_id, "tenant-a")
            self.assertNotEqual(r.doc_id, "d3")

    def test_hyde_failure_falls_back_to_rewritten_query(self):
        """If generate_hyde throws, deep_search must fall back to the rewrite."""
        def boom(query):
            raise RuntimeError("provider down")

        self.provider.generate_hyde = boom
        results = self._run(
            self.orchestrator.deep_search("funding rules", "tenant-a", top_k=5)
        )
        # embed fallback: it should embed the rewritten query
        self.assertEqual(len(self.provider.embed_calls), 1)
        self.assertEqual(self.provider.embed_calls[0], "REWRITTEN: funding rules")
        self.assertGreaterEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
