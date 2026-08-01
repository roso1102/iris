"""Phase 1.0 unit tests — sentence-boundary chunking (Task 1.6)."""

import unittest

from services.common.ingestion.chunker import chunk_routed
from services.common.ingestion.models import ElementType, ParsedElement, RouteDecision
from services.common.ingestion.vlm_router import RoutingResult


def _rr(etype: ElementType, text: str, decision: RouteDecision, page: int = 1) -> RoutingResult:
    return RoutingResult(
        element=ParsedElement(
            page_number=page, element_type=etype, text=text, bbox=[0.0, 0.0, 1.0, 1.0]
        ),
        decision=decision,
        text=text,
    )


class TestChunker(unittest.TestCase):

    def test_short_text_single_chunk(self):
        chunks = chunk_routed(
            [_rr(ElementType.TEXT, "Just one sentence.", RouteDecision.DOCLING_TEXT)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].page_number, 1)
        self.assertEqual(chunks[0].tenant_id, "t1")
        self.assertEqual(chunks[0].doc_id, "d1")
        self.assertEqual(chunks[0].bbox, [0.0, 0.0, 1.0, 1.0])

    def test_long_text_splits_at_sentence_boundary(self):
        # ~2400 chars > 2048-char budget (~512 tokens @ 4 chars/token).
        # Splits on sentence boundaries, never mid-sentence.
        text = "This is sentence number one. " * 80
        chunks = chunk_routed(
            [_rr(ElementType.TEXT, text, RouteDecision.DOCLING_TEXT)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertTrue(c.text.rstrip().endswith("."))

    def test_vlm_table_is_single_chunk_with_bbox(self):
        md = "| c1 | c2 |\n|---|\n| a | b |"
        chunks = chunk_routed(
            [_rr(ElementType.TABLE, md, RouteDecision.VLM_TABLE)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].source, RouteDecision.VLM_TABLE)
        self.assertEqual(chunks[0].text, md)
        self.assertEqual(chunks[0].element_type, ElementType.TABLE)

    def test_empty_vlm_output_produces_no_chunk(self):
        chunks = chunk_routed(
            [_rr(ElementType.TABLE, "", RouteDecision.VLM_TABLE)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertEqual(chunks, [])

    def test_empty_text_no_chunks(self):
        chunks = chunk_routed(
            [_rr(ElementType.TEXT, "", RouteDecision.DOCLING_TEXT)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertEqual(chunks, [])


if __name__ == "__main__":
    unittest.main()
