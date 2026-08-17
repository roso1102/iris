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
        prov = [
            _FakeProv(13, _FakeBBox(0, 800, 500, 850), span13),
            _FakeProv(14, _FakeBBox(0, 100, 500, 180), span14),
        ]
        els = self._split("text", text, prov)
        self.assertEqual(len(els), 2)
        self.assertEqual({e.page_number for e in els}, {13, 14})
        p13 = next(e for e in els if e.page_number == 13)
        p14 = next(e for e in els if e.page_number == 14)
        self.assertEqual(p13.text, text[0:99].strip())
        self.assertEqual(p14.text, text[99:].strip())
        # Each element carries its own page's bbox (normalized coords).
        self.assertEqual(len(p13.bbox), 4)
        self.assertEqual(len(p14.bbox), 4)
        self.assertNotEqual(p13.bbox, p14.bbox)

    def test_single_page_element_unchanged(self):
        text = "Just one page of content. " * 20
        prov = [_FakeProv(3, _FakeBBox(0, 0, 500, 100), (0, len(text)))]
        els = self._split("text", text, prov, {3: (500.0, 1000.0)})
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].page_number, 3)
        self.assertEqual(els[0].text, text.strip())
        # normalized: bbox / page dims
        self.assertEqual(els[0].bbox, [0.0, 0.0, 1.0, 0.1])

    def test_table_element_not_split(self):
        # Tables/figures stay single chunks even with multi-page prov.
        text = "big table content"
        prov = [
            _FakeProv(2, _FakeBBox(0, 0, 500, 300), (0, 10)),
            _FakeProv(3, _FakeBBox(0, 0, 500, 300), (10, len(text))),
        ]
        els = self._split("table", text, prov)
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
