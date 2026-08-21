"""Phase 3.0 Task 3.4 — citation validation hallucination guard tests."""

import unittest

from services.common.models.base import Citation, StructuredAnswer
from services.common.retrieval.models import ScoredChunk
from services.common.retrieval.synthesis import normalize_answer_markers, validate_citations


def _chunk(chunk_id: str, doc_id: str = "d1") -> ScoredChunk:
    return ScoredChunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        tenant_id="tenant-a",
        text="chunk text for " + chunk_id,
        bbox=[0.1, 0.2, 0.5, 0.4],
        page_number=3,
        element_type="Text",
        source="docling_text",
        score=0.9,
    )


class TestValidateCitations(unittest.TestCase):

    def test_drops_hallucinated_chunk_ids(self):
        retrieved = [_chunk("c1"), _chunk("c2")]
        answer = StructuredAnswer(
            answer="grounded answer",
            citations=[
                Citation(chunk_id="c1", doc_id="d1", page_number=3, bbox=[0, 0, 1, 1], text_snippet="x"),
                Citation(chunk_id="ghost", doc_id="d1", page_number=3, bbox=[0, 0, 1, 1], text_snippet="y"),
            ],
        )
        result = validate_citations(answer, retrieved)
        self.assertEqual([c.chunk_id for c in result.citations], ["c1"])

    def test_overwrites_llm_coordinates_with_real_chunk(self):
        retrieved = [_chunk("c1", doc_id="real-doc")]
        answer = StructuredAnswer(
            answer="grounded answer",
            citations=[
                Citation(chunk_id="c1", doc_id="fake-doc", page_number=99, bbox=[0, 0, 0, 0], text_snippet="fake"),
            ],
        )
        result = validate_citations(answer, retrieved)
        self.assertEqual(len(result.citations), 1)
        c = result.citations[0]
        self.assertEqual(c.doc_id, "real-doc")
        self.assertEqual(c.page_number, 3)
        self.assertEqual(c.bbox, [0.1, 0.2, 0.5, 0.4])
        self.assertEqual(c.text_snippet, "chunk text for c1")

    def test_empty_retrieved_drops_all(self):
        answer = StructuredAnswer(
            answer="no context",
            citations=[
                Citation(chunk_id="c1", doc_id="d1", page_number=1, bbox=[0, 0, 1, 1], text_snippet="x"),
            ],
        )
        result = validate_citations(answer, [])
        self.assertEqual(result.citations, [])

    def test_no_citations_returns_unchanged_answer(self):
        answer = StructuredAnswer(answer="no citations", citations=[])
        result = validate_citations(answer, [_chunk("c1")])
        self.assertEqual(result.answer, "no citations")
        self.assertEqual(result.citations, [])

    def test_normalize_answer_markers_splits_arrays(self):
        refs = {str(i): _chunk("c" + str(i)) for i in (1, 2)}
        text = "The fund [1, 2] and also [1,2,3] apply."
        # Only refs 1..2 exist; 3 is dropped.
        self.assertEqual(
            normalize_answer_markers(text, refs),
            "The fund [1] [2] and also [1] [2] apply.",
        )

    def test_normalize_answer_markers_expands_ranges(self):
        refs = {str(i): _chunk("c" + str(i)) for i in range(1, 6)}
        self.assertEqual(
            normalize_answer_markers("See [1-3].", refs),
            "See [1] [2] [3].",
        )

    def test_normalize_answer_markers_drops_unknown_refs(self):
        refs = {str(i): _chunk("c" + str(i)) for i in (1, 2)}
        self.assertEqual(
            normalize_answer_markers("Bad [9] and [1].", refs),
            "Bad  and [1].",
        )


if __name__ == "__main__":
    unittest.main()
