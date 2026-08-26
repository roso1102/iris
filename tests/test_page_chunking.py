"""Phase 3.5 unit tests — page-boundary strict chunking.

Covers the Docling parser splitting a multi-page element into per-page
ParsedElements (using prov charspans), and the chunker never emitting a
chunk that mixes pages.
"""

import unittest

from services.common.ingestion.chunker import chunk_routed
from services.common.ingestion.models import ElementType, ParsedElement, RouteDecision
from services.common.ingestion.parser import DoclingParser, _text_for_page
from services.common.ingestion.vlm_router import RoutingResult


class _FakeBBox:
    def __init__(self, l, t, r, b):
        self.l, self.t, self.r, self.b = l, t, r, b


class _FakeProv:
    def __init__(self, page_no, bbox, charspan):
        self.page_no = page_no
        self.bbox = bbox
        self.charspan = charspan


class _FakeElement:
    def __init__(self, label, text, prov):
        self.label = label
        self.text = text
        self.prov = prov


class TestParserPageSplit(unittest.TestCase):
    """DoclingParser._extract_element splits multi-page text elements."""

    def _split(self, label, text, prov, page_dims=None):
        elements = []
        DoclingParser._extract_element(elements, _FakeElement(label, text, prov), page_dims or {})
        return elements

    def test_multi_page_text_splits_into_two_elements(self):
        # A paragraph spanning pages 13->14: 100 chars on p13, 200 chars on p14.
        text = ("start of paragraph on page thirteen. " * 5)[:99] + \
               "CONTINUATION ON PAGE FOURTEEN. " * 10
        # charspans: [0, 99) on page 13, [99, len) on page 14
        span13 = (0, 99)
        span14 = (99, len(text))
        # BOTTOMLEFT origin: page 13 region near top (t=850,b=800 of 1000),
        # page 14 region lower on the page (t=180,b=100 of 1000).
        # In BOTTOMLEFT, y grows upward, so t (physical top) > b (physical
        # bottom) numerically.
        prov = [
            _FakeProv(13, _FakeBBox(0, 850, 500, 800), span13),
            _FakeProv(14, _FakeBBox(0, 180, 500, 100), span14),
        ]
        page_dims = {13: (500.0, 1000.0), 14: (500.0, 1000.0)}
        els = self._split("text", text, prov, page_dims)
        self.assertEqual(len(els), 2)
        self.assertEqual({e.page_number for e in els}, {13, 14})
        p13 = next(e for e in els if e.page_number == 13)
        p14 = next(e for e in els if e.page_number == 14)
        self.assertEqual(p13.text, text[0:99].strip())
        self.assertEqual(p14.text, text[99:].strip())
        # Each element carries its own page's bbox (normalized, Y-flipped).
        self.assertEqual(p13.bbox, [0.0, 0.15, 1.0, 0.2])  # top: 1-(850/1000)
        self.assertEqual(p14.bbox, [0.0, 0.82, 1.0, 0.9])  # top: 1-(180/1000)
        self.assertNotEqual(p13.bbox, p14.bbox)

    def test_single_page_element_y_flip(self):
        # Docling origin is BOTTOMLEFT. A bbox near the top edge of a 1000pt
        # page has t > b in BOTTOMLEFT (y grows upward): t=1000, b=900.
        text = "Just one page of content. " * 20
        prov = [_FakeProv(3, _FakeBBox(0, 1000, 500, 900), (0, len(text)))]
        els = self._split("text", text, prov, {3: (500.0, 1000.0)})
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].page_number, 3)
        self.assertEqual(els[0].text, text.strip())
        # BOTTOMLEFT -> TOPLEFT: top = 1 - (t/ph), bottom = 1 - (b/ph)
        # [l/pw, 1-(t/ph), r/pw, 1-(b/ph)] = [0, 0, 1, 0.1]
        self.assertEqual(els[0].bbox, [0.0, 0.0, 1.0, 0.1])

    def test_multi_prov_same_page_splits_per_prov(self):
        # A list with two items on page 5: BOTTOMLEFT boxes (10,900,200,700)
        # and (100,500,400,100) on a 500x1000 page. Each prov item gets its
        # own ParsedElement with its own bbox (not a union envelope that may
        # cover unrelated page regions).
        text = "item one. item two."
        prov = [
            _FakeProv(5, _FakeBBox(10, 900, 200, 700), (0, 9)),
            _FakeProv(5, _FakeBBox(100, 500, 400, 100), (10, len(text))),
        ]
        els = self._split("list_item", text, prov, {5: (500.0, 1000.0)})
        self.assertEqual(len(els), 2)
        # prov1: (10,900,200,700) -> [0.02, 0.1, 0.4, 0.3]
        self.assertEqual(els[0].bbox, [0.02, 0.1, 0.4, 0.3])
        self.assertEqual(els[0].text, "item one.")
        # prov2: (100,500,400,100) -> [0.2, 0.5, 0.8, 0.9]
        self.assertEqual(els[1].bbox, [0.2, 0.5, 0.8, 0.9])
        self.assertEqual(els[1].text, "item two.")

    def test_multi_page_split_per_prov(self):
        # Two provs on page 13, one on page 14: each prov item gets its own
        # ParsedElement with its own bbox (not a page-level union).
        text = "aaaa. bbbb. cccc."
        prov = [
            _FakeProv(13, _FakeBBox(10, 900, 200, 700), (0, 6)),
            _FakeProv(13, _FakeBBox(100, 500, 400, 100), (6, 12)),
            _FakeProv(14, _FakeBBox(0, 800, 500, 700), (12, len(text))),
        ]
        els = self._split(
            "text", text, prov, {13: (500.0, 1000.0), 14: (500.0, 1000.0)}
        )
        self.assertEqual(len(els), 3)
        self.assertEqual({e.page_number for e in els}, {13, 14})
        p13_els = [e for e in els if e.page_number == 13]
        self.assertEqual(len(p13_els), 2)
        # prov1 on p13: (10,900,200,700) -> [0.02, 0.1, 0.4, 0.3]
        self.assertEqual(p13_els[0].bbox, [0.02, 0.1, 0.4, 0.3])
        self.assertEqual(p13_els[0].text, "aaaa.")
        # prov2 on p13: (100,500,400,100) -> [0.2, 0.5, 0.8, 0.9]
        self.assertEqual(p13_els[1].bbox, [0.2, 0.5, 0.8, 0.9])
        self.assertEqual(p13_els[1].text, "bbbb.")
        # prov3 on p14: (0,800,500,700) -> [0.0, 0.2, 1.0, 0.3]
        p14 = next(e for e in els if e.page_number == 14)
        self.assertEqual(p14.bbox, [0.0, 0.2, 1.0, 0.3])
        self.assertEqual(p14.text, "cccc.")

    def test_bbox_missing_page_dims_skips_element(self):
        # Without page dims we cannot normalize — the element is skipped, never
        # stored as raw absolute points (which would break the 0-1 frontend map).
        text = "content"
        prov = [_FakeProv(3, _FakeBBox(0, 100, 500, 0), (0, len(text)))]
        els = self._split("text", text, prov, {})  # page_dims has no page 3
        self.assertEqual(els, [])

    def test_table_element_not_split(self):
        # Tables/figures stay single chunks even with multi-page prov.
        text = "big table content"
        prov = [
            _FakeProv(2, _FakeBBox(0, 300, 500, 0), (0, 10)),
            _FakeProv(3, _FakeBBox(0, 300, 500, 0), (10, len(text))),
        ]
        els = self._split("table", text, prov, {2: (500.0, 1000.0)})
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].element_type, ElementType.TABLE)

    def test_text_for_page_falls_back_to_full_text_without_charspan(self):
        text = "some text"
        prov = [_FakeProv(1, _FakeBBox(0, 0, 10, 10), None)]
        self.assertEqual(_text_for_page(_FakeElement("text", text, prov), text, prov), text)


class TestChunkerPageFirst(unittest.TestCase):
    """chunk_routed never emits a chunk mixing page numbers."""

    def _rr(self, etype, text, page):
        return RoutingResult(
            element=ParsedElement(
                page_number=page, element_type=etype, text=text, bbox=[0.0, 0.0, 1.0, 1.0]
            ),
            decision=RouteDecision.DOCLING_TEXT,
            text=text,
        )

    def test_chunks_have_single_page_each(self):
        routed = [
            self._rr(ElementType.TEXT, "Page one sentence. " * 200, 1),
            self._rr(ElementType.TEXT, "Page two sentence. " * 200, 2),
            self._rr(ElementType.TEXT, "Page three sentence. " * 200, 3),
        ]
        chunks = chunk_routed(routed, tenant_id="t1", doc_id="d1")
        self.assertGreater(len(chunks), 3)
        for c in chunks:
            self.assertIn(c.page_number, {1, 2, 3})
        # No chunk contains text from two pages: verify by checking the text
        # of any page-1 chunk never contains page-2 sentences, etc.
        for c in chunks:
            if c.page_number == 1:
                self.assertNotIn("Page two", c.text)
                self.assertNotIn("Page three", c.text)

    def test_page_override_keeps_single_page(self):
        routed = [
            self._rr(ElementType.TEXT, "Some text. " * 300, 5),
            self._rr(ElementType.TEXT, "More text. " * 300, 6),
        ]
        chunks = chunk_routed(
            routed, tenant_id="t1", doc_id="d1", page_number_override=10
        )
        for c in chunks:
            self.assertEqual(c.page_number, 10)


if __name__ == "__main__":
    unittest.main()
