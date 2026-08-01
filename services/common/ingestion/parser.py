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
    """Production parser backed by Docling v2 (CPU-only, runs in Cloud Run)."""

    def __init__(self) -> None:
        self._converter = None

    def _get_converter(self):
        if self._converter is None:
            from docling.document_converter import DocumentConverter

            self._converter = DocumentConverter()
        return self._converter

    def parse(self, pdf_path: Path) -> List[ParsedElement]:
        converter = self._get_converter()
        result = converter.convert(str(pdf_path))
        doc = result.document

        elements: List[ParsedElement] = []
        # doc.pages is keyed by 1-based page number.
        for page_no in sorted(doc.pages.keys()):
            page = doc.pages[page_no]
            for ref in page.elements:
                element = doc[ref] if hasattr(doc, "__getitem__") else ref
                self._extract_element(elements, element, page_no)
        return elements

    @staticmethod
    def _extract_element(elements: List[ParsedElement], element, page_no: int) -> None:
        label = getattr(element, "label", None)
        label_str = str(getattr(label, "value", label)).lower()

        if label_str in _TABLE_LABELS:
            element_type = ElementType.TABLE
        elif label_str in _PICTURE_LABELS:
            element_type = ElementType.PICTURE
        elif label_str in _TEXT_LABELS:
            element_type = ElementType.TEXT
        else:
            element_type = ElementType.OTHER

        text = (getattr(element, "text", "") or "").strip()
        bbox = _bbox_of(element)
        if bbox is None:
            logger.debug("page %s element has no bbox; skipping", page_no)
            return

        elements.append(
            ParsedElement(
                page_number=page_no,
                element_type=element_type,
                text=text,
                bbox=bbox,
            )
        )


def _bbox_of(element) -> List[float] | None:
    """Extract the normalized [left, top, right, bottom] bbox.

    Prefers element.prov[0].bbox (normalized 0-1). Falls back to a raw
    .bbox attribute if present. Returns None when unavailable.
    """
    prov = getattr(element, "prov", None)
    if prov:
        bbox = getattr(prov[0], "bbox", None)
        if bbox is not None:
            b = getattr(bbox, "as_tuple", None)
            if callable(b):
                return list(b())
            return [bbox.l, bbox.t, bbox.r, bbox.b]

    raw = getattr(element, "bbox", None)
    if raw is not None:
        b = getattr(raw, "as_tuple", None)
        if callable(b):
            return list(b())
        return [raw.l, raw.t, raw.r, raw.b]

    return None
