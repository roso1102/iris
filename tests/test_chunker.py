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


def _md_table(n_rows: int, row_text: str = "row", cols: int = 3) -> str:
    """Markdown table with a caption, header, separator, and n_rows data rows."""
    header = "| col A | col B | col C |"[: cols * 8].rstrip()
    if not header.endswith("|"):
        header += " |"
    sep = "|" + "---|" * cols
    rows = "\n".join(
        "| " + " | ".join([f"{row_text} {i}"] + ["x"] * (cols - 1)) + " |"
        for i in range(n_rows)
    )
    return f"Table caption here\n{header}\n{sep}\n{rows}"


class TestVlmTableSplitting(unittest.TestCase):
    """Pipeline #2: VLM tables split at row-group boundaries, header repeated."""

    def test_small_table_stays_single_byte_identical(self):
        md = _md_table(3)
        chunks = chunk_routed(
            [_rr(ElementType.TABLE, md, RouteDecision.VLM_TABLE)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, md)  # byte-identical, not rebuilt

    def test_large_table_splits_with_header_in_every_chunk(self):
        md = _md_table(60, row_text="appraisal record number")
        chunks = chunk_routed(
            [_rr(ElementType.TABLE, md, RouteDecision.VLM_TABLE)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertGreater(len(chunks), 1)
        header_row = "| col A | col B | col C |"
        for c in chunks:
            self.assertIn(header_row, c.text)  # header row carried forward
            self.assertIn("Table caption here", c.text)  # caption carried forward

    def test_rows_never_split_mid_row(self):
        row_text = "appraisal record number"
        md = _md_table(60, row_text=row_text)
        chunks = chunk_routed(
            [_rr(ElementType.TABLE, md, RouteDecision.VLM_TABLE)],
            tenant_id="t1", doc_id="d1",
        )
        prefix = f"| {row_text}"
        original_rows = [ln for ln in md.splitlines() if ln.startswith(prefix)]
        carried = [ln for c in chunks for ln in c.text.splitlines() if ln.startswith(prefix)]
        self.assertEqual(sorted(original_rows), sorted(carried))  # no row lost or split
        for c in chunks:
            lines = c.text.splitlines()
            self.assertTrue(len([ln for ln in lines if ln.startswith(prefix)]) >= 1)

    def test_no_row_duplication_across_chunks(self):
        md = _md_table(60)
        chunks = chunk_routed(
            [_rr(ElementType.TABLE, md, RouteDecision.VLM_TABLE)],
            tenant_id="t1", doc_id="d1",
        )
        carried = [ln for c in chunks for ln in c.text.splitlines() if ln.startswith("| row")]
        self.assertEqual(len(carried), len(set(carried)))  # each row appears once

    def test_chunk_sizes_respect_budget(self):
        md = _md_table(60, row_text="appraisal record number")
        chunks = chunk_routed(
            [_rr(ElementType.TABLE, md, RouteDecision.VLM_TABLE)],
            tenant_id="t1", doc_id="d1",
        )
        # Budget 1024 chars (256 tokens) + header/caption + one row of slack.
        for c in chunks:
            self.assertLessEqual(len(c.text), 1024 + 200)

    def test_full_page_ocr_is_prose_split_not_single_chunk(self):
        text = "Scanned page sentence. " * 120  # ~2760 chars > 1024 budget
        chunks = chunk_routed(
            [_rr(ElementType.PICTURE, text, RouteDecision.VLM_FULL_PAGE, page=7)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertIs(c.metadata.get("page_level"), True)  # bbox metadata kept

    def test_oversized_header_emitted_alone(self):
        # Pathological: header alone exceeds the budget. Must still emit.
        huge_header = "| " + "A" * 1200 + " |"
        md = f"{huge_header}\n|---|\n| r1 |"
        chunks = chunk_routed(
            [_rr(ElementType.TABLE, md, RouteDecision.VLM_TABLE)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertEqual(len(chunks), 1)
        self.assertIn("A" * 100, chunks[0].text)

    def test_table_without_caption(self):
        # 60 wide-enough rows (~1,100 chars total) to exceed the 1024 budget.
        md = "| h1 | h2 |\n|---|\n" + "\n".join(
            f"| r{i} | some data value in the cell |" for i in range(60)
        )
        chunks = chunk_routed(
            [_rr(ElementType.TABLE, md, RouteDecision.VLM_TABLE)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertIn("| h1 | h2 |", c.text)

    def test_empty_table_produces_no_chunk(self):
        chunks = chunk_routed(
            [_rr(ElementType.TABLE, "", RouteDecision.VLM_TABLE)],
            tenant_id="t1", doc_id="d1",
        )
        self.assertEqual(chunks, [])


if __name__ == "__main__":
    unittest.main()
