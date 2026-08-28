"""Phase 2.0 unit tests — diversity / dedup pass (token-overlap based)."""

import unittest

from services.common.retrieval.diversity import diversity_penalty
from services.common.retrieval.models import ScoredChunk


def _scored(doc_id: str, score: float, page: int = 1, text: str = "some text") -> ScoredChunk:
    return ScoredChunk(
        chunk_id=f"{doc_id}-p{page}",
        doc_id=doc_id,
        tenant_id="tenant-a",
        text=text,
        bbox=[0.1, 0.1, 0.5, 0.4],
        page_number=page,
        element_type="Text",
        score=score,
    )


class TestDiversity(unittest.TestCase):

    def test_one_doc_flooding(self):
        chunks = [
            _scored("doc-a", 0.9, text="section about forests and wildlife"),
            _scored("doc-a", 0.85, text="section about forests and wildlife"),
            _scored("doc-a", 0.8, text="section about forests and wildlife"),
            _scored("doc-a", 0.75, text="section about water resources"),
            _scored("doc-b", 0.7, text="section about pollution control"),
        ]
        result = diversity_penalty(chunks, top_k=4, penalty=0.5)
        # First 3 chunks have high overlap (>80%), so 2nd and 3rd get penalized
        scores = {c.chunk_id: c.score for c in result}
        self.assertLess(scores["doc-a-p1"], 0.9)  # penalized (overlap with doc-a-p1)
        self.assertLess(scores["doc-a-p1"], 0.9)  # penalized (overlap with doc-a-p1)

    def test_diverse_chunks_same_page_not_penalized(self):
        # Key insight: chunks from the same page with DIFFERENT text should
        # NOT be penalized — this is the "Forms 3, 4, 5" fix.
        chunks = [
            _scored("doc-a", 0.9, page=1, text="Form 3: Application for tree clearance permit"),
            _scored("doc-a", 0.85, page=1, text="Form 4: Environmental impact assessment report"),
            _scored("doc-a", 0.8, page=1, text="Form 5: Compliance monitoring checklist"),
            _scored("doc-b", 0.7, page=1, text="Section about pollution standards"),
        ]
        result = diversity_penalty(chunks, top_k=4, penalty=0.5)
        # All chunks have distinct text, so NO penalties applied
        self.assertEqual([c.score for c in result], [0.9, 0.85, 0.8, 0.7])

    def test_near_duplicates_penalized(self):
        # Chunks with >80% token overlap should be penalized
        chunks = [
            _scored("doc-a", 0.9, page=1, text="The environmental impact assessment must be submitted before construction begins"),
            _scored("doc-a", 0.6, page=2, text="The environmental impact assessment must be submitted before construction begins"),
            _scored("doc-b", 0.75, page=1, text="Pollution control board monitors compliance"),
        ]
        result = diversity_penalty(chunks, top_k=3, penalty=0.5)
        # First chunk keeps its score, second chunk gets penalized (overlap with first)
        self.assertEqual(result[0].doc_id, "doc-a")
        self.assertEqual(result[0].score, 0.9)  # first chunk unaffected
        self.assertEqual(result[1].doc_id, "doc-b")
        self.assertEqual(result[1].score, 0.75)  # doc-b unaffected
        # The penalized chunk (doc-a-p2) should be last
        self.assertEqual(result[2].doc_id, "doc-a")
        self.assertLess(result[2].score, 0.6)  # penalized

    def test_no_duplicates(self):
        chunks = [
            _scored("doc-a", 0.9, text="Forestry regulations and permits"),
            _scored("doc-b", 0.85, text="Water resource management"),
            _scored("doc-c", 0.8, text="Air quality standards"),
        ]
        result = diversity_penalty(chunks, top_k=5)
        self.assertEqual(result[0].score, 0.9)
        self.assertEqual(result[1].score, 0.85)
        self.assertEqual(result[2].score, 0.8)

    def test_penalty_reorders(self):
        chunks = [
            _scored("doc-a", 0.9, text="Environmental clearance process"),
            _scored("doc-a", 0.6, text="Environmental clearance process"),
            _scored("doc-b", 0.75, text="Forest conservation rules"),
        ]
        result = diversity_penalty(chunks, top_k=3, penalty=0.5)
        # doc-a-p2 gets penalized (overlap with doc-a-p1), so doc-b moves up
        self.assertEqual(result[0].doc_id, "doc-a")
        self.assertEqual(result[1].doc_id, "doc-b")

    def test_empty_input(self):
        result = diversity_penalty([], top_k=10)
        self.assertEqual(result, [])

    def test_penalty_below_top_k_not_applied(self):
        chunks = [
            _scored("doc-a", 0.9, text="Unique text for doc-a"),
            _scored("doc-b", 0.8, text="Unique text for doc-b"),
            _scored("doc-b", 0.7, text="Another unique text for doc-b"),
        ]
        result = diversity_penalty(chunks, top_k=2, penalty=0.5)
        # All texts are unique, no penalties applied
        self.assertEqual(result[0].score, 0.9)
        self.assertEqual(result[1].score, 0.8)
        self.assertEqual(result[2].score, 0.7)


if __name__ == "__main__":
    unittest.main()
