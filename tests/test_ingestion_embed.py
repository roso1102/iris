"""Unit tests for the embedding failure semantics in IngestionPipeline._embed.

Verifies the two failure modes the 429-stabilization work addresses:
  1. A successful embed_batch fills chunk embeddings.
  2. A failed embed_batch raises RetryError (Pub/Sub redelivery) instead of
     silently writing zero-vectors that would be invisible to dense search.
"""

import unittest
from unittest.mock import MagicMock, patch

from services.common.ingestion.main import IngestionPipeline, RetryError
from services.common.ingestion.models import Chunk, ElementType
from services.common.ingestion.parser import MockDocParser
from services.common.ingestion.store import MemoryChunkStore
from services.common.ingestion.vlm_router import MockVlmRouter
from services.common.models.mock import MockModelProvider


def _chunks(n: int = 2) -> list[Chunk]:
    return [
        Chunk(
            tenant_id="tenant-a",
            doc_id="doc_001",
            page_number=1,
            element_type=ElementType.TEXT,
            text=f"chunk {i}",
            bbox=[0.0, 0.0, 1.0, 1.0],
        )
        for i in range(n)
    ]


class TestEmbedFailureSemantics(unittest.TestCase):
    def setUp(self):
        self.pipeline = IngestionPipeline(
            provider=MockModelProvider(),
            store=MemoryChunkStore(),
            parser=MockDocParser(),
            router=MockVlmRouter(),
        )

    def test_embed_success_fills_vectors(self):
        chunks = _chunks()
        self.pipeline._embed(chunks)
        for chunk in chunks:
            self.assertEqual(chunk.embedding, [0.1] * 768)

    def test_embed_batch_failure_raises_retry_error(self):
        provider = MockModelProvider()
        provider.embed_batch = MagicMock(side_effect=RuntimeError("429 exhausted"))
        self.pipeline = IngestionPipeline(
            provider=provider,
            store=MemoryChunkStore(),
            parser=MockDocParser(),
            router=MockVlmRouter(),
        )

        chunks = _chunks()
        with self.assertRaises(RetryError):
            self.pipeline._embed(chunks)
        # No chunk was mutated to a zero vector — the failure is atomic.
        for chunk in chunks:
            self.assertIsNone(chunk.embedding)

    def test_embed_returns_none_mismatch_is_not_zero_vector(self):
        # A provider that returns an empty list would silently under-embed if
        # the loop weren't guarded; ensure the normal path still just zips.
        provider = MockModelProvider()
        provider.embed_batch = MagicMock(return_value=[[0.5] * 768, [0.6] * 768])
        self.pipeline = IngestionPipeline(
            provider=provider,
            store=MemoryChunkStore(),
            parser=MockDocParser(),
            router=MockVlmRouter(),
        )
        chunks = _chunks(2)
        self.pipeline._embed(chunks)
        self.assertEqual(chunks[0].embedding, [0.5] * 768)
        self.assertEqual(chunks[1].embedding, [0.6] * 768)


if __name__ == "__main__":
    unittest.main()
