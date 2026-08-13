"""Phase 2.0 unit tests — diversity / dedup pass."""

import unittest

from services.common.retrieval.diversity import diversity_penalty
from services.common.retrieval.models import ScoredChunk


def _scored(doc_id: str, score: float) -> ScoredChunk:
    return ScoredChunk(
        chunk_id=f"{doc_id}-chunk",
        doc_id=doc_id,
        tenant_id="tenant-a",
        text="some text",
        bbox=[0.1, 0.1, 0.5, 0.4],
        page_number=1,
        element_type="Text",
        score=score,
    )


class TestDiversity(unittest.TestCase):

    def test_one_doc_flooding(self):
        chunks = [
            _scored("doc-a", 0.9),
            _scored("doc-a", 0.85),
            _scored("doc-a", 0.8),
            _scored("doc-a", 0.75),
            _scored("doc-b", 0.7),
        ]
        result = diversity_penalty(chunks, top_k=4, penalty=0.5)
        scores = {c.chunk_id: c.score for c in result}
        self.assertLess(scores["doc-a-chunk"], 0.5)

    def test_no_duplicates(self):
        chunks = [
            _scored("doc-a", 0.9),
            _scored("doc-b", 0.85),
            _scored("doc-c", 0.8),
        ]
        result = diversity_penalty(chunks, top_k=5)
        self.assertEqual(result[0].score, 0.9)
        self.assertEqual(result[1].score, 0.85)
        self.assertEqual(result[2].score, 0.8)

    def test_penalty_reorders(self):
        chunks = [
            _scored("doc-a", 0.9),
            _scored("doc-a", 0.6),
            _scored("doc-b", 0.75),
        ]
        result = diversity_penalty(chunks, top_k=3, penalty=0.5)
        self.assertEqual(result[0].doc_id, "doc-a")
        self.assertEqual(result[1].doc_id, "doc-b")

    def test_empty_input(self):
        result = diversity_penalty([], top_k=10)
        self.assertEqual(result, [])

    def test_penalty_below_top_k_not_applied(self):
        chunks = [
            _scored("doc-a", 0.9),
            _scored("doc-b", 0.8),
            _scored("doc-b", 0.7),
        ]
        result = diversity_penalty(chunks, top_k=2, penalty=0.5)
        self.assertEqual(result[0].score, 0.9)
        self.assertEqual(result[1].score, 0.8)
        self.assertEqual(result[2].score, 0.7)


if __name__ == "__main__":
    unittest.main()
