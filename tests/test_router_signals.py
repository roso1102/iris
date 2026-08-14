"""Layer 1 unit tests — production VLM router signal logic.

These exercise `RouterVlmRouter._route_element` (the real signal decision table),
NOT `MockVlmRouter` (which deliberately short-circuits the signal logic for
other tests). No VLM, no rendering, no network — `_route_element` only computes
a RouteDecision from element metadata.
"""

import unittest

from services.common.ingestion.models import ElementType, ParsedElement, RouteDecision
from services.common.ingestion.vlm_router import RouterVlmRouter, FitzPageRenderer
from services.common.models.mock import MockModelProvider

CLEAN_TEXT = ("This is a clean English paragraph with many readable words. " * 12)
GARBLED_TEXT = "\ufffd\ufffd\ufffd\ufffd \u200b\u200b\u200b \u0378\u0378\u0378"


def _el(etype: ElementType, text: str, page: int = 1) -> ParsedElement:
    return ParsedElement(
        page_number=page,
        element_type=etype,
        text=text,
        bbox=[0.05, 0.05, 0.95, 0.95],
    )


class TestRouterSignals(unittest.TestCase):
    """Verify the production `_route_element` signal table directly."""

    @classmethod
    def setUpClass(cls):
        cls.router = RouterVlmRouter(
            provider=MockModelProvider(),
            renderer=FitzPageRenderer(),
        )

    def _decide(self, el, coverage=1.0, total_chars=9999):
        return self.router._route_element(
            el,
            pdf_path="unused.pdf",
            page_render=None,
            page_coverage=coverage,
            page_total_chars=total_chars,
        )[0]

    def test_clean_text_routes_docling(self):
        """fast_text tier: high word ratio + enough chars -> zero API cost."""
        el = _el(ElementType.TEXT, CLEAN_TEXT)
        self.assertEqual(self._decide(el), RouteDecision.DOCLING_TEXT)

    def test_table_routes_vlm_table(self):
        self.assertEqual(
            self._decide(_el(ElementType.TABLE, "some table text")),
            RouteDecision.VLM_TABLE,
        )

    def test_picture_routes_vlm_picture(self):
        self.assertEqual(
            self._decide(_el(ElementType.PICTURE, "")),
            RouteDecision.VLM_PICTURE,
        )

    def test_low_char_routes_vlm_full_page(self):
        """Signal 4: low-total-text page -> full-page OCR (page-level check)."""
        el = _el(ElementType.TEXT, "Short scanned header.")
        self.assertEqual(
            self._decide(el, coverage=1.0, total_chars=14),
            RouteDecision.VLM_FULL_PAGE,
        )

    def test_short_element_on_text_rich_page_stays_docling(self):
        """Signal 4 is page-level: a short footer/heading on a text-rich page
        must NOT trigger a full-page VLM call."""
        el = _el(ElementType.TEXT, "Page 1 of 41")
        self.assertEqual(
            self._decide(el, coverage=1.0, total_chars=2000),
            RouteDecision.DOCLING_TEXT,
        )

    def test_garbled_text_routes_vlm_full_page(self):
        """Signal 2: garbled OCR / unmapped encoding -> full-page OCR."""
        el = _el(ElementType.TEXT, GARBLED_TEXT)
        self.assertEqual(self._decide(el), RouteDecision.VLM_FULL_PAGE)

    def test_nearly_blank_page_routes_vlm_full_page(self):
        """Signal 3 case A: coverage < 0.15 and few chars."""
        el = _el(ElementType.TEXT, "caption only")
        self.assertEqual(
            self._decide(el, coverage=0.05, total_chars=12),
            RouteDecision.VLM_FULL_PAGE,
        )

    def test_sparse_valid_text_does_not_trigger_coverage_escalation(self):
        """A sparse but valid text page (coverage 0.20) stays fast_text today.

        This documents current behaviour; FIX-009/FIX-010 (Phase 2.5) will refine
        the coverage threshold without escalating 0.97+ valid_word_ratio pages.
        """
        el = _el(ElementType.TEXT, CLEAN_TEXT)
        self.assertEqual(
            self._decide(el, coverage=0.20, total_chars=600),
            RouteDecision.DOCLING_TEXT,
        )


if __name__ == "__main__":
    unittest.main()
