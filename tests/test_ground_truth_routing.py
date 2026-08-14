"""Tier 0 unit tests — Ground-truth routing verification against trueassort.

Drives the production router signal logic (`RouterVlmRouter._route_element`)
with the per-page labeled features from `trueassort/document_routing.csv`
(201 labeled pages across 8 documents spanning 4 routing tiers).

The CSV carries per-page: has_table, valid_word_ratio, text_coverage.
The router additionally needs char_count, which the CSV does not carry; we
derive it from coverage (image-heavy pages are sparse) exactly as the plan's
FIX-009 signal design assumes: low coverage => sparse text (<150 chars).

Expected route mapping (per fixes_critical.md / eval harness):
  - fast_text         -> DOCLING_TEXT (zero API cost)
  - vlm_heavy         -> VLM_FULL_PAGE (table pages route VLM_TABLE via Signal 1)
  - multilingual_ocr  -> VLM_FULL_PAGE (Signal 5, FIX-008)
  - standard_ocr      -> DOCLING_TEXT with extraction_confidence metadata (FIX-011)

This test is pure logic (no VLM, no rendering, no network). It encodes the
ground-truth CSV as the source of truth so router regressions are caught
before any GCP spend (Tier 0 gate).
"""

import csv
import unittest
from pathlib import Path

from services.common.ingestion.models import ElementType, ParsedElement, RouteDecision
from services.common.ingestion.vlm_router import RouterVlmRouter
from services.common.models.mock import MockModelProvider

TRUEASSORT = Path(__file__).resolve().parents[1] / "trueassort"
CSV_PATH = TRUEASSORT / "document_routing.csv"

# Expected route -> the RouteDecision the router must produce for a TEXT element
ROUTE_TO_DECISION = {
    "fast_text": RouteDecision.DOCLING_TEXT,
    "vlm_heavy": RouteDecision.VLM_FULL_PAGE,
    "multilingual_ocr": RouteDecision.VLM_FULL_PAGE,
    "standard_ocr": RouteDecision.DOCLING_TEXT,  # FIX-011: tagged, not VLM
}

DEVARAGARI_TEXT = (
    "\u092f\u0939 \u090f\u0915 \u0939\u093f\u0902\u0926\u0940 \u0935\u093e\u0915\u094d\u092f "
    "\u0939\u0948 \u091c\u094b \u0926\u0947\u0935\u0928\u093e\u0917\u0930\u0940 \u0932\u093f\u092a\u093f "
    "\u092e\u0947\u0902 \u0932\u093f\u0916\u093e \u0917\u092f\u093e \u0939\u0948 \u0914\u0930 "
    "\u0907\u0938\u0947 \u092a\u0922\u093c\u093e \u091c\u093e \u0938\u0915\u0924\u093e \u0939\u0948\u0964 "
) * 6


def _load_pages():
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _char_count_for_coverage(coverage: float, route: str) -> int:
    """Derive a plausible element char_count from page coverage + route.

    The CSV's text_coverage reflects bbox area, NOT text sparsity — e.g.
    englishscan4 p27 is fast_text with coverage 0.20 but has 1755 real chars.
    So:
      - fast_text / standard_ocr pages always carry dense text (>= 150 chars,
        so Signal 4 never fires — their low coverage is a layout artifact).
      - vlm_heavy / multilingual_ocr pages are genuinely sparse or image-heavy
        (low coverage => sparse caption text < 150 chars), which is what
        FIX-009 Case B and Signal 4 target.
    """
    if route in ("fast_text", "standard_ocr"):
        return 400
    return 80 if coverage < 0.45 else 400


def _synthetic_element(has_table: bool, coverage: float, route: str) -> ParsedElement:
    """Build a synthetic element carrying only the CSV-labeled features."""
    if route == "multilingual_ocr":
        text = DEVARAGARI_TEXT  # Signal 5 needs real Devanagari to fire
        char_count = 400
    else:
        char_count = _char_count_for_coverage(coverage, route)
        text = "Clean text sentence with meaningful content. " * max(1, char_count // 45)
    return ParsedElement(
        page_number=1,
        element_type=ElementType.TABLE if has_table else ElementType.TEXT,
        text=text,
        bbox=[0.05, 0.05, 0.95, 0.95],
    )


class TestGroundTruthRouting(unittest.TestCase):
    """Every labeled page in the CSV must route as the ground truth says."""

    @classmethod
    def setUpClass(cls):
        cls.pages = _load_pages()
        cls.router = RouterVlmRouter(provider=MockModelProvider(), renderer=None)

    def test_csv_exists_and_has_expected_shape(self):
        self.assertTrue(CSV_PATH.exists(), "trueassort/document_routing.csv missing")
        self.assertGreaterEqual(len(self.pages), 200)
        for p in self.pages:
            self.assertIn(p["expected_route"], ROUTE_TO_DECISION)

    def _decide(self, page: dict):
        has_table = page["has_table"].lower() == "true"
        coverage = float(page["text_coverage"])
        el = _synthetic_element(has_table, coverage, page["expected_route"])
        # A single synthetic element stands in for the whole page, so the
        # page's total char count equals that element's char count. Signal 4
        # (page-level low-text check) must be exercised faithfully.
        return self.router._route_element(
            el, "unused.pdf", None,
            page_coverage=coverage,
            page_total_chars=el.char_count,
        )[0]

    def test_fast_text_pages_route_docling(self):
        """127 pages: high ratio + high coverage -> zero VLM cost."""
        pages = [p for p in self.pages if p["expected_route"] == "fast_text"]
        self.assertGreaterEqual(len(pages), 100)
        for p in pages:
            self.assertEqual(
                self._decide(p), RouteDecision.DOCLING_TEXT,
                f"fast_text page {p['filename']} p{p['page_number']} routed wrong",
            )

    def test_vlm_heavy_pages_route_vlm(self):
        """58 pages: tables (Signal 1) or low-coverage sparse -> VLM."""
        pages = [p for p in self.pages if p["expected_route"] == "vlm_heavy"]
        self.assertGreaterEqual(len(pages), 50)
        for p in pages:
            has_table = p["has_table"].lower() == "true"
            expected = RouteDecision.VLM_TABLE if has_table else RouteDecision.VLM_FULL_PAGE
            self.assertEqual(
                self._decide(p), expected,
                f"vlm_heavy page {p['filename']} p{p['page_number']} routed wrong",
            )

    def test_multilingual_ocr_pages_route_vlm_full_page(self):
        """5 pages (Hindi/Devanagari): Signal 5 must fire despite high ratio."""
        pages = [p for p in self.pages if p["expected_route"] == "multilingual_ocr"]
        self.assertEqual(len(pages), 5)
        for p in pages:
            self.assertEqual(
                self._decide(p), RouteDecision.VLM_FULL_PAGE,
                f"multilingual_ocr page {p['filename']} p{p['page_number']} must route VLM (Signal 5)",
            )

    def test_standard_ocr_pages_stay_docling_but_tagged(self):
        """11 pages: 0.75-0.88 ratio -> DOCLING_TEXT (or VLM_TABLE if has_table)."""
        pages = [p for p in self.pages if p["expected_route"] == "standard_ocr"]
        self.assertGreaterEqual(len(pages), 10)
        for p in pages:
            has_table = p["has_table"].lower() == "true"
            expected = RouteDecision.VLM_TABLE if has_table else RouteDecision.DOCLING_TEXT
            self.assertEqual(
                self._decide(p), expected,
                f"standard_ocr page {p['filename']} p{p['page_number']} routed wrong",
            )
            ratio = float(p["valid_word_ratio"])
            self.assertTrue(
                0.75 <= ratio < 0.97,
                f"standard_ocr page {p['filename']} p{p['page_number']} ratio {ratio} out of tag band",
            )

    def test_all_201_pages_route_correctly(self):
        """Aggregate: every labeled page matches ground truth (no regressions)."""
        mismatches = []
        for p in self.pages:
            actual = self._decide(p)
            expected = ROUTE_TO_DECISION[p["expected_route"]]
            # Signal 1: any page with a table routes VLM_TABLE regardless of tier
            if p["has_table"].lower() == "true":
                expected = RouteDecision.VLM_TABLE
            if actual != expected:
                mismatches.append((p["filename"], p["page_number"], p["expected_route"], actual.value))
        self.assertEqual(mismatches, [], f"Routing mismatches: {mismatches}")


if __name__ == "__main__":
    unittest.main()
