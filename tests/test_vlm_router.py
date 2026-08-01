"""Phase 1.0 unit tests — Page-Wise VLM Router (Task 1.5).

Covers Test 1-D (table -> VLM), 1-E (scanned/low-text -> full-page VLM),
and 1-F (clean text -> ZERO VLM calls). Uses MockVlmRouter so no network.
"""

import unittest

from services.common.ingestion.models import ElementType, ParsedElement, RouteDecision
from services.common.ingestion.vlm_router import MIN_TEXT_CHARS, MockVlmRouter


def _el(page: int, etype: ElementType, text: str) -> ParsedElement:
    return ParsedElement(
        page_number=page,
        element_type=etype,
        text=text,
        bbox=[0.05, 0.05, 0.95, 0.95],
    )


CLEAN_TEXT = "Sentence one. " * 40  # >= 150 chars


class TestVlmRouter(unittest.TestCase):

    def test_clean_text_no_vlm_call(self):
        """Test 1-F: clean text pages never trigger a VLM call."""
        router = MockVlmRouter()
        routed = router.route([_el(1, ElementType.TEXT, CLEAN_TEXT)])
        self.assertEqual(routed[0].decision, RouteDecision.DOCLING_TEXT)
        self.assertEqual(router.vlm_calls, 0)

    def test_table_triggers_vlm(self):
        """Test 1-D: table element -> VLM table route, markdown output."""
        router = MockVlmRouter()
        routed = router.route([_el(1, ElementType.TABLE, "row data")])
        self.assertEqual(routed[0].decision, RouteDecision.VLM_TABLE)
        self.assertIn("|", routed[0].text)
        self.assertEqual(router.vlm_calls, 1)

    def test_scanned_page_triggers_full_page_vlm(self):
        """Test 1-E: low-text element (<150 chars) -> full-page VLM."""
        router = MockVlmRouter()
        routed = router.route([_el(2, ElementType.TEXT, "Scanned header.")])
        self.assertEqual(routed[0].decision, RouteDecision.VLM_FULL_PAGE)
        self.assertEqual(router.vlm_calls, 1)

    def test_picture_triggers_vlm(self):
        router = MockVlmRouter()
        routed = router.route([_el(1, ElementType.PICTURE, "")])
        self.assertEqual(routed[0].decision, RouteDecision.VLM_PICTURE)
        self.assertEqual(router.vlm_calls, 1)

    def test_mixed_page_counts_correctly(self):
        router = MockVlmRouter()
        elements = [
            _el(1, ElementType.TEXT, CLEAN_TEXT),   # no call
            _el(1, ElementType.TABLE, "data"),      # call
            _el(1, ElementType.TEXT, "short"),      # call
        ]
        routed = router.route(elements)
        self.assertEqual(router.vlm_calls, 2)
        decisions = [r.decision for r in routed]
        self.assertEqual(decisions.count(RouteDecision.DOCLING_TEXT), 1)

    def test_configured_threshold(self):
        router = MockVlmRouter(min_text_chars=20)
        routed = router.route([_el(1, ElementType.TEXT, "A short but non-empty text body.")])
        self.assertEqual(routed[0].decision, RouteDecision.DOCLING_TEXT)


if __name__ == "__main__":
    unittest.main()
