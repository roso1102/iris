"""Docling layout-aware parsing (ACTIONPLAN Task 1.4).

Wraps Docling v2 and normalizes its output into `ParsedElement`s with
normalized [left, top, right, bottom] bboxes and our ElementType labels,
so the VLM router and chunker never touch the Docling API directly.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from services.common.ingestion.models import ElementType, ParsedElement

logger = logging.getLogger(__name__)

# Docling element classes whose label is structurally significant to the
# Page-Wise VLM Router. Matched via isinstance so we survive v2 enum renames.
_TABLE_LABELS = {"table"}
_PICTURE_LABELS = {"picture", "figure", "chart"}
_TEXT_LABELS = {"text", "paragraph", "list_item", "title", "page_header",
                "page_footer", "caption"}


class DocParser(ABC):
    """Parses a PDF into page-ordered ParsedElements with bboxes."""

    @abstractmethod
    def parse(self, pdf_path: Path) -> List[ParsedElement]:
        """Return all elements across all pages, in reading order."""


class MockDocParser(DocParser):
    """Deterministic parser for local tests (MODEL_BACKEND=mock)."""

    def parse(self, pdf_path: Path) -> List[ParsedElement]:
        logger.info("MockDocParser: not really parsing %s", pdf_path)
        return [
            ParsedElement(
                page_number=1,
                element_type=ElementType.TEXT,
                text=("Sample gazette text. " * 40),  # >= 150 chars
                bbox=[0.05, 0.05, 0.95, 0.15],
            ),
            ParsedElement(
                page_number=1,
                element_type=ElementType.TABLE,
                text="",
                bbox=[0.05, 0.20, 0.95, 0.60],
            ),
            ParsedElement(
                page_number=2,
                element_type=ElementType.PICTURE,
                text="",
                bbox=[0.10, 0.10, 0.90, 0.50],
            ),
            ParsedElement(
                page_number=2,
                element_type=ElementType.TEXT,
                text="Scanned header.",
                bbox=[0.05, 0.55, 0.95, 0.60],
            ),
        ]


class DoclingParser(DocParser):
    """Production parser backed by Docling v2.

    Falls back to CPU mode for PDFs >30 pages when GPU VRAM is limited.
    """

    def __init__(self, use_cpu: bool = False, num_threads: int = 4) -> None:
        self._converter = None
        self._use_cpu = use_cpu
        self._num_threads = num_threads

    def _get_converter(self):
        if self._converter is None:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice

            pipeline_opts = PdfPipelineOptions()
            # OCR is handled exclusively by the VLM router (Gemini Vision).
            # Running Docling's RapidOCR here double-processes every page,
            # burns CPU/memory, and corrupts the router's signals by
            # substituting OCR text where it should detect "no embedded text".
            pipeline_opts.do_ocr = False
            pipeline_opts.do_table_structure = True
            pipeline_opts.accelerator_options = AcceleratorOptions(
                num_threads=self._num_threads,
            )
            if self._use_cpu:
                pipeline_opts.accelerator_options.device = AcceleratorDevice.CPU

            format_opts = {InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)}
            self._converter = DocumentConverter(format_options=format_opts)
        return self._converter

    def parse(self, pdf_path: Path) -> List[ParsedElement]:
        converter = self._get_converter()
        # Docling v2.117+ returns items via doc.body.children (RefItem list).
        result = converter.convert(str(pdf_path))
        doc = result.document

        # Build page dimension lookup for bbox normalization.
        page_dims: dict[int, tuple[float, float]] = {}
        for pno in sorted(doc.pages.keys()):
            pg = doc.pages[pno]
            w, h = _page_size(pg)
            if w and h:
                page_dims[pno] = (w, h)

        elements: list[ParsedElement] = []
        for child in doc.body.children:
            element = child.resolve(doc)
            self._extract_element(elements, element, page_dims)
        return elements

    @staticmethod
    def _extract_element(
        elements: list[ParsedElement],
        element,
        page_dims: dict[int, tuple[float, float]],
    ) -> None:
        label = getattr(element, "label", None)
        label_str = str(label).lower() if label is not None else ""

        # Map Docling v2 labels to our ElementType enum.
        if label_str in _TABLE_LABELS:
            element_type = ElementType.TABLE
        elif label_str in _PICTURE_LABELS:
            element_type = ElementType.PICTURE
        elif label_str in _TEXT_LABELS or label_str in ("section_header", "list",
                                                         "page_footer", "page_header",
                                                         "key_value_area", "text"):
            element_type = ElementType.TEXT
        else:
            element_type = ElementType.OTHER

        text = (getattr(element, "text", "") or "").strip()

        # A single logical element may span multiple pages (a paragraph that
        # starts near the bottom of page P and continues on page P+1). Each
        # Docling prov entry carries (page_no, bbox, charspan) so we can split
        # the text deterministically per page. This guarantees every chunk has
        # single-page provenance (Phase 3.5 page-boundary strict chunking).
        prov = getattr(element, "prov", None)
        if not prov or not isinstance(prov, list) or not prov:
            return

        pages = sorted({int(getattr(p, "page_no", 0)) for p in prov})
        if len(pages) > 1 and element_type in (ElementType.TEXT, ElementType.OTHER):
            for item in prov:
                pno = int(getattr(item, "page_no", 0))
                item_text = _text_for_prov(text, item)
                item_bbox = _bbox_of_single(item, page_dims.get(pno))
                if item_bbox is None or not item_text:
                    continue
                elements.append(
                    ParsedElement(
                        page_number=pno,
                        element_type=element_type,
                        text=item_text,
                        bbox=item_bbox,
                    )
                )
            return

        page_no = _page_of(element)
        page_dims_this = page_dims.get(page_no)

        # Single-page element with multiple prov items: split per prov so
        # each ParsedElement carries only its own bbox (not a union envelope
        # that may cover unrelated page regions like a figure placeholder).
        same_page_items = [
            p for p in prov if int(getattr(p, "page_no", 0)) == page_no
        ]
        if len(same_page_items) > 1 and element_type in (ElementType.TEXT, ElementType.OTHER):
            for item in same_page_items:
                item_text = _text_for_prov(text, item)
                item_bbox = _bbox_of_single(item, page_dims_this)
                if item_bbox is None or not item_text:
                    continue
                elements.append(
                    ParsedElement(
                        page_number=page_no,
                        element_type=element_type,
                        text=item_text,
                        bbox=item_bbox,
                    )
                )
            return

        bbox = _bbox_of(element, page_dims_this)
        if bbox is None:
            return

        elements.append(
            ParsedElement(
                page_number=page_no,
                element_type=element_type,
                text=text,
                bbox=bbox,
            )
        )


def _page_of(element) -> int:
    """Extract 1-based page number from element provenance."""
    prov = getattr(element, "prov", None)
    if prov and isinstance(prov, list) and prov:
        pno = getattr(prov[0], "page_no", None)
        if pno is not None:
            return int(pno)
    return 1


def _page_size(page) -> tuple[float | None, float | None]:
    """Return (width, height) in points for a Docling PageItem."""
    if hasattr(page, "size") and page.size:
        return (float(page.size.width), float(page.size.height))
    img = getattr(page, "image", None)
    if img and hasattr(img, "size"):
        return (float(img.size[0]), float(img.size[1]))
    if img and hasattr(img, "width") and hasattr(img, "height"):
        return (float(img.width), float(img.height))
    return (None, None)


def _text_for_prov(full_text: str, item) -> str:
    """Slice full_text to a single prov item's charspan."""
    cs = getattr(item, "charspan", None)
    if cs is not None and len(cs) == 2:
        s, e = int(cs[0]), int(cs[1])
        if e > s:
            return full_text[s:e].strip()
    return full_text.strip()


def _bbox_of_single(item, page_dims: tuple[float, float] | None) -> list[float] | None:
    """Normalized [left, top, right, bottom] for a single prov item."""
    bbox = getattr(item, "bbox", None)
    if bbox is None or not page_dims:
        return None
    pw, ph = page_dims
    if pw <= 0 or ph <= 0:
        return None
    l, t, r, b = float(bbox.l), float(bbox.t), float(bbox.r), float(bbox.b)
    return [
        max(0.0, min(1.0, round(l / pw, 4))),
        max(0.0, min(1.0, round(1.0 - (t / ph), 4))),
        max(0.0, min(1.0, round(r / pw, 4))),
        max(0.0, min(1.0, round(1.0 - (b / ph), 4))),
    ]


def _bbox_of(element, page_dims: tuple[float, float] | None) -> list[float] | None:
    """Extract normalized [left, top, right, bottom] bbox (0-1, top-left origin).

    Docling v2 provides bbox in absolute points with coord_origin=BOTTOMLEFT.
    We normalize against the page dimensions from the page lookup and flip the
    Y-axis to top-left origin (Phase 9.0-C).

    Elements with several provs on the SAME page (lists, multi-cell tables)
    union every box on that page — prov[0] alone would highlight only the
    first item. Provs on other pages (cross-page tables) are ignored; the
    element's page is prov[0]'s, matching _page_of.
    """
    prov = getattr(element, "prov", None)
    if not prov or not isinstance(prov, list) or not prov:
        return None
    page_no = int(getattr(prov[0], "page_no", 0) or 0)
    same_page = [
        p for p in prov if int(getattr(p, "page_no", 0) or 0) == page_no
    ]
    return _bbox_of_items(same_page or [prov[0]], page_dims)


def _bbox_of_items(
    items: list, page_dims: tuple[float, float] | None
) -> list[float] | None:
    """Union of bboxes across prov items, normalized to top-left 0-1 page coords.

    Docling v2 emits bboxes in absolute points with coord_origin=BOTTOMLEFT.
    We normalize against the element's OWN page dimensions (never a global/A4
    constant, or letter/cropped pages would drift) and flip the Y-axis so the
    stored bbox uses top-left 0-1 coordinates — the convention the frontend
    BboxOverlay and Citation.bbox expect (Phase 9.0-C).

    If page_dims is missing for this page we return None so the caller skips the
    element rather than emitting raw absolute points, which would render as
    off-screen/oversized highlights.
    """
    boxes: list[tuple[float, float, float, float]] = []
    for item in items:
        bbox = getattr(item, "bbox", None)
        if bbox is None:
            continue
        boxes.append(
            (float(bbox.l), float(bbox.t), float(bbox.r), float(bbox.b))
        )
    if not boxes:
        return None

    l = min(b[0] for b in boxes)
    r = max(b[2] for b in boxes)
    # BOTTOMLEFT boxes carry t > b per box (y grows upward), so the union's
    # top edge is the LARGEST t and its bottom edge the SMALLEST b — min/max
    # flipped relative to a TOPLEFT frame. Getting this backwards inverts the
    # box (top > bottom) whenever one page has 2+ prov items.
    t = max(b[1] for b in boxes)
    b = min(b[3] for b in boxes)

    # Without the page dimension lookup we cannot normalize — skip rather than
    # storing raw absolute points (which break the 0-1 frontend mapping).
    if not page_dims:
        return None
    pw, ph = page_dims
    if pw <= 0 or ph <= 0:
        return None

    # BOTTOMLEFT -> TOPLEFT: in BOTTOMLEFT coords `t` is the physical TOP
    # edge (larger numeric y) and `b` the physical BOTTOM (smaller y), so the
    # flip is top = 1 - t/ph, bottom = 1 - b/ph (docling_core BoundingBox
    # semantics: t=top, b=bottom, origin just sets which y is larger).
    left = max(0.0, min(1.0, round(l / pw, 4)))
    top = max(0.0, min(1.0, round(1.0 - (t / ph), 4)))
    right = max(0.0, min(1.0, round(r / pw, 4)))
    bottom = max(0.0, min(1.0, round(1.0 - (b / ph), 4)))
    return [left, top, right, bottom]


def _text_for_page(element, full_text: str, page_items: list) -> str:
    """Slice `full_text` to the charspan of the prov items on one page.

    Falls back to the full text when charspans are absent (defensive), so
    page splitting never drops content silently.
    """
    spans = []
    for item in page_items:
        cs = getattr(item, "charspan", None)
        if cs is not None and len(cs) == 2:
            spans.append((int(cs[0]), int(cs[1])))
    if not spans:
        return full_text
    spans.sort()
    # Merge overlapping/adjacent spans, then join the covered slices.
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    parts = [full_text[s:e].strip() for s, e in merged if e > s]
    return " ".join(parts).strip()
