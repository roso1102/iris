"""Phase 0.1 tests — embedding validation (no partial or zero-vector writes)."""

import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ["MODEL_BACKEND"] = "mock"

from services.common.embeddings import (
    EMBEDDING_DIM,
    EmbeddingInvalidError,
    validate_embedding_batch,
    validate_embedding_vector,
)
from services.common.ingestion.main import IngestionPipeline, RejectError
from services.common.ingestion.models import Chunk, ElementType, RouteDecision


def _vec(value: float = 0.1):
    return [value] * EMBEDDING_DIM


def _chunk(text: str = "x") -> Chunk:
    return Chunk(
        tenant_id="tenant-a",
        doc_id="d1",
        page_number=1,
        element_type=ElementType.TEXT,
        text=text,
        bbox=[0.1, 0.1, 0.5, 0.4],
        source=RouteDecision.DOCLING_TEXT,
    )


class TestVectorValidation(unittest.TestCase):

    def test_ok(self):
        self.assertEqual(len(validate_embedding_vector(_vec())), EMBEDDING_DIM)

    def test_empty_and_wrong_dimension(self):
        for bad in ([], [0.1] * 10, [0.1] * (EMBEDDING_DIM + 1)):
            with self.assertRaises(EmbeddingInvalidError):
                validate_embedding_vector(bad)

    def test_non_numeric_and_bool(self):
        bad = _vec()
        bad[0] = "0.1"
        with self.assertRaises(EmbeddingInvalidError):
            validate_embedding_vector(bad)
        bad = _vec()
        bad[0] = True
        with self.assertRaises(EmbeddingInvalidError):
            validate_embedding_vector(bad)

    def test_nan_and_inf(self):
        for value in (math.nan, math.inf, -math.inf):
            bad = _vec()
            bad[3] = value
            with self.assertRaises(EmbeddingInvalidError):
                validate_embedding_vector(bad)

    def test_zero_vector_rejected(self):
        with self.assertRaises(EmbeddingInvalidError):
            validate_embedding_vector([0.0] * EMBEDDING_DIM)

    def test_not_a_list(self):
        with self.assertRaises(EmbeddingInvalidError):
            validate_embedding_vector("nope")


class TestBatchValidation(unittest.TestCase):

    def test_count_mismatch_short_and_extra(self):
        chunks = [_chunk("a"), _chunk("b")]
        with self.assertRaises(EmbeddingInvalidError):
            validate_embedding_batch(chunks, [_vec()])
        with self.assertRaises(EmbeddingInvalidError):
            validate_embedding_batch(chunks, [_vec(), _vec(), _vec()])

    def test_valid_batch(self):
        chunks = [_chunk("a"), _chunk("b")]
        out = validate_embedding_batch(chunks, [_vec(), _vec(0.2)])
        self.assertEqual(len(out), 2)

    def test_mid_batch_invalid_rejects_all(self):
        chunks = [_chunk("a"), _chunk("b"), _chunk("c")]
        bad = _vec()
        bad[0] = math.nan
        with self.assertRaises(EmbeddingInvalidError):
            validate_embedding_batch(chunks, [_vec(), bad, _vec()])


class _RecordingStore:
    def __init__(self):
        self.upsert_calls = 0

    def upsert_batch(self, chunks):
        self.upsert_calls += 1
        return len(chunks)


class _BadCountProvider:
    def embed_batch(self, texts):
        return [_vec()]  # not enough embeddings for >1 chunk


class _InvalidProvider:
    def embed_batch(self, texts):
        return [[0.0] * EMBEDDING_DIM for _ in texts]


class TestPipelineAtomicity(unittest.TestCase):

    def _pipeline(self, provider):
        store = _RecordingStore()
        pipeline = IngestionPipeline(
            provider=provider, store=store, parser=MagicMock(), router=MagicMock()
        )
        return pipeline, store

    def test_short_batch_rejects_and_writes_zero_points(self):
        pipeline, store = self._pipeline(_BadCountProvider())
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "doc-1.pdf"
            local.write_bytes(b"%PDF-1.4 fake")
            pipeline._download = lambda uri, tmpdir, doc_id: local
            with patch("services.common.ingestion.main.check_pdf", return_value={"page_count": 1}), \
                 patch("services.common.ingestion.main.chunk_routed", return_value=[_chunk("a"), _chunk("b")]):
                with self.assertRaises(RejectError):
                    pipeline.ingest("gs://bucket/doc-1.pdf", "tenant-a", "doc-1")
        # Invalid embeddings must abort before any Qdrant write.
        self.assertEqual(store.upsert_calls, 0)

    def test_short_batch_leaves_chunks_unembedded(self):
        pipeline, store = self._pipeline(_BadCountProvider())
        chunks = [_chunk("a"), _chunk("b")]
        with self.assertRaises(RejectError):
            pipeline._embed(chunks)
        self.assertEqual(store.upsert_calls, 0)
        self.assertTrue(all(c.embedding is None for c in chunks))

    def test_zero_vectors_rejected(self):
        pipeline, store = self._pipeline(_InvalidProvider())
        chunks = [_chunk("a")]
        with self.assertRaises(RejectError):
            pipeline._embed(chunks)
        self.assertEqual(store.upsert_calls, 0)
        self.assertIsNone(chunks[0].embedding)


if __name__ == "__main__":
    unittest.main()
