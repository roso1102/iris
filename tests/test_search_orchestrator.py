"""Phase 2.0 unit tests — SearchOrchestrator (Standard + Deep)."""

import asyncio
import unittest
from unittest.mock import patch

from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from services.common.ingestion.store import MemoryChunkStore
from services.common.models.mock import MockModelProvider
from services.common.retrieval.search import SearchOrchestrator, _needs_rewrite


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

    def test_rerank_blend_pure_reorders_results(self):
        # Mock rerank scores passages in REVERSE order. Pure rerank (blend=1.0)
        # must invert the hybrid ranking so the mock's top-scored chunk lands
        # first — proving the reranker leg is wired into standard_search.
        hybrid = self._run(
            self.orchestrator.standard_search(
                "committee funding", "tenant-a", top_k=3, rerank_blend=0.0
            )
        )
        reranked = self._run(
            self.orchestrator.standard_search(
                "committee funding", "tenant-a", top_k=3, rerank_blend=1.0
            )
        )
        self.assertGreaterEqual(len(hybrid), 1)
        self.assertGreaterEqual(len(reranked), 1)
        # With blend=1.0 the mock top-scored chunk (first candidate) becomes #1.
        # Assert the top-ranked chunk_id differs between the two legs.
        self.assertNotEqual(hybrid[0].chunk_id, reranked[0].chunk_id)

    # ── Stage 1a/1b: query-task embedding + diversity placement ────────────

    def test_standard_uses_embed_query_deep_uses_embed(self):
        # Standard search embeds the query with the QUERY task type; deep
        # search embeds the HyDE hypothetical DOCUMENT with the doc task.
        class TrackProvider(MockModelProvider):
            def __init__(self):
                super().__init__()
                self.query_embeds = []
                self.doc_embeds = []

            def embed_query(self, text):
                # Do NOT delegate to embed() — the base-class delegation
                # would record a phantom doc-side call.
                self.query_embeds.append(text)
                return [0.1] * 768

            def embed(self, text):
                self.doc_embeds.append(text)
                return super().embed(text)

        provider = TrackProvider()
        orch = SearchOrchestrator(store=MemoryChunkStore(), provider=provider)
        orch.store.upsert_batch([_chunk("d1", tenant_id="tenant-a", text="doc text")])

        self._run(orch.standard_search("plain query", "tenant-a", top_k=3))
        self.assertEqual(provider.query_embeds, ["plain query"])
        self.assertEqual(provider.doc_embeds, [])

        self._run(orch.deep_search("deep query", "tenant-a", top_k=3))
        self.assertEqual(len(provider.doc_embeds), 1)
        self.assertIn("Hypothetical", provider.doc_embeds[0])
        self.assertEqual(provider.query_embeds, ["plain query"])

    def test_doc_scoped_search_skips_diversity(self):
        # Doc-scoped sessions (doc_ids set) bypass the diversity pass; every
        # result is same-doc by construction and page-level dedup would only
        # distort intra-document ranking.
        import services.common.retrieval.search as search_mod

        with patch.object(
            search_mod, "diversity_penalty", wraps=search_mod.diversity_penalty
        ) as dp:
            self._run(
                self.orchestrator.standard_search(
                    "committee funding", "tenant-a", doc_ids=["d1"], top_k=5
                )
            )
            dp.assert_not_called()

            self._run(
                self.orchestrator.standard_search(
                    "committee funding", "tenant-a", top_k=5
                )
            )
            dp.assert_called_once()

    # ── Phase 6.0a / 6.5: SLM rewrite wiring + pronoun gate ────────────────

    def test_needs_rewrite_requires_history_and_pronoun(self):
        self.assertFalse(_needs_rewrite("What is SDRF?", []))            # no history
        self.assertFalse(_needs_rewrite("What is SDRF?", [{"role": "user", "content": "hi"}]))  # no pronoun
        self.assertFalse(_needs_rewrite("what does it do?", []))          # pronoun, but no history

    def test_needs_rewrite_true_for_ambiguous_followup(self):
        history = [{"role": "user", "content": "Explain the SDRF."},
                   {"role": "assistant", "content": "The SDRF is..."}]
        self.assertTrue(_needs_rewrite("what does it do?", history))
        self.assertTrue(_needs_rewrite("How about that clause?", history))

    def test_standard_search_rewrites_ambiguous_followup(self):
        # Track whether the rewriter ran. The mock embed is constant, so we
        # assert on invocation (via a spy provider) rather than result deltas.
        class RecordingProvider(MockModelProvider):
            def __init__(self):
                super().__init__(embed_dim=768)
                self.rewrite_calls = []

            def rewrite_query(self, query, history):
                self.rewrite_calls.append((query, history))
                return f"Resolved: {query}"

        provider = RecordingProvider()
        orch = SearchOrchestrator(store=MemoryChunkStore(), provider=provider)
        orch.store.upsert_batch([_chunk("d1", tenant_id="tenant-a", text="doc text")])

        history = [{"role": "user", "content": "Explain the SDRF."}]
        self._run(orch.standard_search("what does it do?", "tenant-a", top_k=5, history=history))
        self.assertEqual(len(provider.rewrite_calls), 1)

    def test_standard_search_skips_rewrite_without_history(self):
        provider = MockModelProvider(embed_dim=768)
        orig_rewrite = provider.rewrite_query
        calls = []

        def spy(query, history):
            calls.append(query)
            return orig_rewrite(query, history)

        provider.rewrite_query = spy
        orch = SearchOrchestrator(store=MemoryChunkStore(), provider=provider)
        orch.store.upsert_batch([_chunk("d1", tenant_id="tenant-a", text="doc text")])

        self._run(orch.standard_search("what does it do?", "tenant-a", top_k=5))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
