"""Phase 0.1 tests — bbox validation and page-level citation provenance."""

import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ["MODEL_BACKEND"] = "mock"

from services.common.ingestion.chunker import chunk_routed
from services.common.ingestion.main import IngestionPipeline
from services.common.ingestion.models import (
    Chunk,
    ElementType,
    ParsedElement,
    RouteDecision,
    normalize_bbox,
)
from services.common.ingestion.vlm_router import RoutingResult
from services.common.models.base import Citation, StructuredAnswer
from services.common.retrieval.models import ScoredChunk
from services.common.retrieval.synthesis import validate_citations


def _rr(etype, text, decision, page=1, bbox=None, page_level=None,
        bbox_source=None, bbox_confidence=None) -> RoutingResult:
    element = ParsedElement(
        page_number=page,
        element_type=etype,
        text=text,
        bbox=bbox if bbox is not None else [0.0, 0.0, 1.0, 1.0],
        page_level=page_level,
        bbox_source=bbox_source,
        bbox_confidence=bbox_confidence,
    )
    return RoutingResult(element=element, decision=decision, text=text)


class TestNormalizeBbox(unittest.TestCase):

    def test_valid_box_preserved(self):
        bbox, page_level, source, confidence = normalize_bbox(
            [0.1, 0.2, 0.5, 0.6], source="element", confidence=0.9
        )
        self.assertEqual(bbox, [0.1, 0.2, 0.5, 0.6])
        self.assertFalse(page_level)
        self.assertEqual(source, "element")
        self.assertAlmostEqual(confidence, 0.9)

    def test_invalid_boxes_downgraded(self):
        invalid = [
            [0.0, 0.0, 1.0],                     # wrong length
            [0.5, 0.2, 0.5, 0.6],                # zero width
            [0.1, 0.6, 0.5, 0.2],                # inverted
            [-0.1, 0.0, 0.5, 0.5],               # out of range
            [0.1, 0.2, 1.5, 0.6],                # out of range
            [math.nan, 0.2, 0.5, 0.6],           # NaN
            [math.inf, 0.2, 0.5, 0.6],           # inf
            ["0.1", 0.2, 0.5, 0.6],              # non-numeric
            [0.1, True, 0.5, 0.6],               # bool
        ]
        for bad in invalid:
            bbox, page_level, source, confidence = normalize_bbox(bad)
            self.assertEqual(bbox, [0.0, 0.0, 1.0, 1.0], bad)
            self.assertTrue(page_level, bad)
            self.assertEqual(source, "invalid_downgraded", bad)
            self.assertEqual(confidence, 0.0, bad)


class TestChunkerProvenance(unittest.TestCase):

    def test_explicit_fallback_flag_survives(self):
        rr = _rr(
            ElementType.TEXT, "full page ocr text", RouteDecision.VLM_FULL_PAGE,
            page=6, bbox=[0.0, 0.0, 1.0, 1.0], page_level=True,
            bbox_source="page_ocr_fallback", bbox_confidence=0.0,
        )
        chunks = chunk_routed([rr], tenant_id="t1", doc_id="d1")
        self.assertEqual(chunks[0].page_level, True)
        self.assertEqual(chunks[0].bbox_source, "page_ocr_fallback")
        self.assertEqual(chunks[0].bbox_confidence, 0.0)
        self.assertIs(chunks[0].metadata.get("page_level"), True)

    def test_precise_element_stays_precise(self):
        rr = _rr(
            ElementType.TEXT, "Normal element.", RouteDecision.DOCLING_TEXT,
            bbox=[0.1, 0.1, 0.5, 0.4],
        )
        chunk = chunk_routed([rr], tenant_id="t1", doc_id="d1")[0]
        self.assertFalse(chunk.page_level)
        self.assertEqual(chunk.bbox_source, "element")
        self.assertEqual(chunk.bbox, [0.1, 0.1, 0.5, 0.4])
        self.assertNotIn("page_level", chunk.metadata)

    def test_page_area_heuristic_tags_page_level(self):
        rr = _rr(
            ElementType.TEXT, "big box text", RouteDecision.DOCLING_TEXT,
            bbox=[0.0, 0.0, 1.0, 1.0],
        )
        chunk = chunk_routed([rr], tenant_id="t1", doc_id="d1")[0]
        self.assertTrue(chunk.page_level)
        self.assertEqual(chunk.bbox_source, "page_area")

    def test_invalid_bbox_downgraded_in_chunk(self):
        rr = _rr(
            ElementType.TEXT, "bad geometry", RouteDecision.DOCLING_TEXT,
            bbox=[0.1, 0.1, 0.1, 0.4],
        )
        chunk = chunk_routed([rr], tenant_id="t1", doc_id="d1")[0]
        self.assertTrue(chunk.page_level)
        self.assertEqual(chunk.bbox_source, "invalid_downgraded")
        self.assertEqual(chunk.bbox, [0.0, 0.0, 1.0, 1.0])


class TestPipelineFallbackTag(unittest.TestCase):

    def test_zero_element_page_is_tagged_page_ocr_fallback(self):
        captured = {}

        def route(elements, pdf_path=None):
            captured["element"] = elements[0]
            return [RoutingResult(
                element=elements[0], decision=RouteDecision.VLM_FULL_PAGE,
                text="scanned page ocr",
            )]

        class _Provider:
            def embed_batch(self, texts):
                return [[0.1] * 768 for _ in texts]

        class _Store:
            def upsert_batch(self, chunks):
                return len(chunks)

        router = MagicMock()
        router.route.side_effect = route
        pipeline = IngestionPipeline(
            provider=_Provider(), store=_Store(),
            parser=MagicMock(parse=MagicMock(return_value=[])),
            router=router,
        )
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "doc-1.pdf"
            local.write_bytes(b"%PDF-1.4 fake")
            pipeline._download = lambda uri, tmpdir, doc_id: local
            with patch("services.common.ingestion.main.check_pdf", return_value={"page_count": 1}):
                result = pipeline.ingest("gs://bucket/doc-1.pdf", "tenant-a", "doc-1",
                                         page_number=6)
        element = captured["element"]
        self.assertTrue(element.page_level)
        self.assertEqual(element.bbox_source, "page_ocr_fallback")
        self.assertEqual(result.chunk_count, 1)


class TestCitationProvenance(unittest.TestCase):

    def _scored(self, metadata):
        return ScoredChunk(
            chunk_id="c1", doc_id="d1", tenant_id="t1", text="evidence text",
            bbox=[0.1, 0.1, 0.5, 0.4], page_number=3, element_type="Text",
            source="docling_text", score=1.0, metadata=metadata,
        )

    def test_page_level_citation_cannot_claim_precise_box(self):
        answer = StructuredAnswer(
            answer="[1] The policy applies.",
            citations=[Citation(chunk_id="c1", doc_id="d1", page_number=3,
                                bbox=[0.1, 0.1, 0.5, 0.4], text_snippet="x")],
        )
        out = validate_citations(answer, [self._scored({"page_level": True,
                                                        "bbox_source": "page_ocr_fallback",
                                                        "bbox_confidence": 0.0})])
        citation = out.citations[0]
        self.assertTrue(citation.page_level)
        self.assertEqual(citation.bbox, [0.0, 0.0, 1.0, 1.0])
        self.assertEqual(citation.bbox_confidence, 0.0)
        self.assertEqual(citation.bbox_source, "page_ocr_fallback")

    def test_precise_citation_kept(self):
        answer = StructuredAnswer(
            answer="[1] The policy applies.",
            citations=[Citation(chunk_id="c1", doc_id="d1", page_number=3,
                                bbox=[0.1, 0.1, 0.5, 0.4], text_snippet="x")],
        )
        out = validate_citations(answer, [self._scored({"bbox_source": "element"})])
        citation = out.citations[0]
        self.assertFalse(citation.page_level)
        self.assertEqual(citation.bbox, [0.1, 0.1, 0.5, 0.4])


if __name__ == "__main__":
    unittest.main()
