"""Phase 1.0 unit tests — sentence-boundary chunking (Task 1.6)."""

import os
import unittest
import unittest.mock

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

    # ── Stage 3a/3b: small-to-big target + page-level citation tagging ────

    def test_default_target_is_256_tokens(self):
        # ~2200 chars > 1024-char budget (256 tokens @ 4 chars/token) but
        # < the old 2048-char budget — must split under the NEW default.
        text = "This is sentence number one. " * 78
        chunks = chunk_routed(
            [_rr(ElementType.TEXT, text, RouteDecision.DOCLING_TEXT)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            # Budget + one sentence of slack (packing never splits a sentence).
            self.assertLessEqual(len(c.text), 1024 + len("This is sentence number one. "))

    def test_env_target_tokens_override(self):
        text = "This is sentence number one. " * 78
        with unittest.mock.patch.dict(
            os.environ, {"CHUNK_TARGET_TOKENS": "128"}
        ):
            small = chunk_routed(
                [_rr(ElementType.TEXT, text, RouteDecision.DOCLING_TEXT)],
                tenant_id="t1", doc_id="d1",
            )
        big = chunk_routed(
            [_rr(ElementType.TEXT, text, RouteDecision.DOCLING_TEXT)],
            tenant_id="t1", doc_id="d1", target_tokens=512,
        )
        self.assertGreater(len(small), len(big))

    def test_full_page_bbox_tagged_page_level(self):
        # VLM full-page OCR chunks carry a near-page bbox — a giant frame
        # carries no highlight information, so the frontend jumps to the page.
        chunks = chunk_routed(
            [_rr(ElementType.PICTURE, "OCR text of the whole page",
                 RouteDecision.VLM_FULL_PAGE, page=7)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertEqual(len(chunks), 1)
        self.assertIs(chunks[0].metadata.get("page_level"), True)

    def test_normal_bbox_not_page_level(self):
        rr = _rr(ElementType.TEXT, "Normal element.", RouteDecision.DOCLING_TEXT)
        rr.element.bbox = [0.1, 0.1, 0.5, 0.4]
        chunks = chunk_routed([rr], tenant_id="t1", doc_id="d1")
        self.assertEqual(len(chunks), 1)
        self.assertNotIn("page_level", chunks[0].metadata)


if __name__ == "__main__":
    unittest.main()
