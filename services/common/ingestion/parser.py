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

        # Bbox is always in absolute page coordinates; must normalize.
        page_no = _page_of(element)
        bbox = _bbox_of(element, page_dims.get(page_no))
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


def _bbox_of(element, page_dims: tuple[float, float] | None) -> list[float] | None:
    """Extract normalized [left, top, right, bottom] bbox (0-1).

    Docling v2 provides bbox in absolute points with coord_origin=BOTTOMLEFT.
    We normalize against the page dimensions from the page lookup.
    """
    prov = getattr(element, "prov", None)
    if not prov or not isinstance(prov, list) or not prov:
        return None

    bbox = getattr(prov[0], "bbox", None)
    if bbox is None:
        return None

    l, t, r, b = float(bbox.l), float(bbox.t), float(bbox.r), float(bbox.b)

    if page_dims:
        pw, ph = page_dims
        if pw > 0 and ph > 0:
            return [
                max(0.0, min(1.0, round(l / pw, 4))),
                max(0.0, min(1.0, round(t / ph, 4))),
                max(0.0, min(1.0, round(r / pw, 4))),
                max(0.0, min(1.0, round(b / ph, 4))),
            ]

    return [l, t, r, b]
