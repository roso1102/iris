"""Page-Wise VLM Router (ACTIONPLAN Task 1.5).

Per page, per element, decide the cheapest correct processor:

  | Docling signal                          | Route                         |
  |-----------------------------------------|-------------------------------|
  | Table, any char count                   | Gemini Vision on table crop   |
  | Picture/Figure, any char count          | Gemini Vision on figure crop  |
  | Signal 2 — valid word ratio < 0.75      | Gemini Vision on full page    |
  | Signal 3 — coverage < 0.15 & chars < 300| Gemini Vision on full page    |
  | Signal 4 — char count < 150             | Gemini Vision on full page    |
  | All signals green                       | Docling text (zero API cost)  |

All VLM calls go through ModelProvider.extract_table()/ocr_page() (SRS FR-8).
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List

import fitz  # PyMuPDF
from PIL import Image

from services.common.ingestion.models import ElementType, ParsedElement, RouteDecision
from services.common.models.base import ModelProvider

logger = logging.getLogger(__name__)

MIN_TEXT_CHARS = 150


@dataclass
class RoutingResult:
    """A routed element: either Docling text or a VLM call output."""

    element: ParsedElement
    decision: RouteDecision
    text: str

    @property
    def vlm_called(self) -> bool:
        return self.decision in (RouteDecision.VLM_TABLE,
                                 RouteDecision.VLM_PICTURE,
                                 RouteDecision.VLM_FULL_PAGE)


class PageRenderer(ABC):
    """Renders PDF pages to images so the router can crop bbox regions."""

    @abstractmethod
    def render_page(self, pdf_path: str, page_number: int, scale: float = 2.0) -> Image.Image:
        """Return a PIL.Image of the given 1-based page at `scale`."""


class FitzPageRenderer(PageRenderer):
    """Production page renderer backed by PyMuPDF (fitz)."""

    def render_page(self, pdf_path: str, page_number: int, scale: float = 2.0) -> Image.Image:
        doc = fitz.open(pdf_path)
        try:
            page = doc[page_number - 1]  # 1-based → 0-based
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        finally:
            doc.close()


class VlmRouter(ABC):
    @abstractmethod
    def route(self, elements: List[ParsedElement], pdf_path: str = "") -> List[RoutingResult]:
        """Apply the routing table to a parsed document."""


def _valid_word_ratio(text: str) -> float:
    """Return fraction of characters from recognizable script categories.

    Characters in Unicode Letter (L*), Number (N*), Punctuation (P*), and
    Mark (M*) categories count as valid. Symbols (S*), Separators (Z* except
    space), and Other/Control (C*) characters do not — these signal garbled
    OCR output, unmapped font encodings (KrutiDev/DevLys), or binary noise.
    """
    if not text:
        return 1.0

    import unicodedata

    valid = 0
    total = 0
    for ch in text:
        if ch in (" ", "\n", "\t"):
            continue
        total += 1
        cat = unicodedata.category(ch)
        if cat[0] in ("L", "N", "P", "M"):
            valid += 1

    if total == 0:
        return 1.0
    return valid / total


def _page_text_stats(elements: List[ParsedElement]) -> tuple[float, int]:
    """Compute text area coverage ratio and total char count for TEXT elements."""

    coverage = 0.0
    total_chars = 0
    for el in elements:
        if el.element_type == ElementType.TEXT:
            w = el.bbox[2] - el.bbox[0]
            h = el.bbox[3] - el.bbox[1]
            coverage += w * h
            total_chars += el.char_count
    return coverage, total_chars


class RouterVlmRouter(VlmRouter):
    """Production router: crops bbox regions and calls the VLM via ModelProvider."""

    def __init__(
        self,
        provider: ModelProvider,
        renderer: PageRenderer,
        min_text_chars: int = MIN_TEXT_CHARS,
    ) -> None:
        self._provider = provider
        self._renderer = renderer
        self._min_text_chars = min_text_chars
        self._vlm_cache: Dict[str, str] = {}
        self.vlm_calls = 0

    def route(self, elements: List[ParsedElement], pdf_path: str = "") -> List[RoutingResult]:
        results: List[RoutingResult] = []
        # Group by page so full-page crops reuse one render.
        pages: dict[int, list[ParsedElement]] = {}
        for el in elements:
            pages.setdefault(el.page_number, []).append(el)

        for page_no in sorted(pages):
            page_elements = pages[page_no]
            page_coverage, page_total_chars = _page_text_stats(page_elements)
            page_render = None
            for el in page_elements:
                decision, text = self._route_element(
                    el, pdf_path, page_render,
                    page_coverage=page_coverage,
                    page_total_chars=page_total_chars,
                )
                if decision == RouteDecision.VLM_FULL_PAGE:
                    if page_render is None:
                        page_render = self._renderer.render_page(
                            pdf_path, page_no, scale=2.0
                        )
                    crop = page_render.crop((0, 0, page_render.width, page_render.height))
                    try:
                        text = self._cached_vlm_call(_to_png_bytes(crop), self._provider.ocr_page)
                    except Exception:
                        logger.warning("VLM_FULL_PAGE failed for %s page %s, falling back to Docling text",
                                       pdf_path, page_no, exc_info=True)
                        decision = RouteDecision.DOCLING_TEXT
                        text = el.text
                elif decision in (RouteDecision.VLM_TABLE, RouteDecision.VLM_PICTURE):
                    if page_render is None:
                        page_render = self._renderer.render_page(
                            pdf_path, page_no, scale=2.0
                        )
                    crop = _crop_bbox(page_render, el.bbox, pdf_path, page_no)
                    try:
                        text = self._cached_vlm_call(_to_png_bytes(crop), self._provider.extract_table)
                    except Exception:
                        logger.warning("VLM_TABLE/PICTURE failed for %s page %s, falling back to Docling text",
                                       pdf_path, page_no, exc_info=True)
                        decision = RouteDecision.DOCLING_TEXT
                        text = el.text
                results.append(RoutingResult(element=el, decision=decision, text=text))
        return results

    def _cached_vlm_call(self, image_bytes: bytes, extractor) -> str:
        img_hash = hashlib.sha256(image_bytes).hexdigest()
        if img_hash in self._vlm_cache:
            return self._vlm_cache[img_hash]
        text = extractor(image_bytes)
        self._vlm_cache[img_hash] = text
        self.vlm_calls += 1
        return text

    def _route_element(
        self, el: ParsedElement, pdf_path: str, page_render: object,
        page_coverage: float = 1.0,
        page_total_chars: int = 9999,
    ) -> tuple[RouteDecision, str]:
        # Signal 1 — structural elements always go to VLM (Docling text unreliable).
        if el.element_type == ElementType.TABLE:
            return RouteDecision.VLM_TABLE, ""
        if el.element_type == ElementType.PICTURE:
            return RouteDecision.VLM_PICTURE, ""
        # Signal 2 — valid word ratio (garbage OCR / unmapped font encoding).
        if _valid_word_ratio(el.text) < 0.75:
            return RouteDecision.VLM_FULL_PAGE, ""
        # Signal 3 — text area coverage (image-heavy / infographic pages).
        if page_coverage < 0.15 and page_total_chars < 300:
            return RouteDecision.VLM_FULL_PAGE, ""
        # Signal 4 — char count threshold (scanned / low-text elements).
        if el.char_count < self._min_text_chars:
            return RouteDecision.VLM_FULL_PAGE, ""
        return RouteDecision.DOCLING_TEXT, el.text


def _crop_bbox(page_render: object, bbox: List[float], pdf_path: str, page_no: int):
    """Crop a normalized bbox [l,t,r,b] from a rendered page."""
    if page_render is None:
        raise RuntimeError(f"Page {page_no} not rendered; cannot crop {bbox}")
    w, h = page_render.width, page_render.height
    l, t, r, b = bbox
    x1 = max(0, min(int(l * w), int(r * w)))
    y1 = max(0, min(int(t * h), int(b * h)))
    x2 = min(w, max(int(l * w), int(r * w)))
    y2 = min(h, max(int(t * h), int(b * h)))
    if x2 <= x1 or y2 <= y1:
        return page_render
    return page_render.crop((x1, y1, x2, y2))


def _to_png_bytes(img) -> bytes:
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class MockVlmRouter(VlmRouter):
    """Deterministic router for tests: routes but never calls a real VLM."""

    def __init__(self, min_text_chars: int = MIN_TEXT_CHARS) -> None:
        self._min_text_chars = min_text_chars
        self.vlm_calls = 0

    def route(self, elements: List[ParsedElement], pdf_path: str = "") -> List[RoutingResult]:
        results: List[RoutingResult] = []
        for el in elements:
            if el.element_type == ElementType.TABLE:
                decision, text = RouteDecision.VLM_TABLE, "| c1 | c2 |\n|---|\n| a | b |"
            elif el.element_type == ElementType.PICTURE:
                decision, text = RouteDecision.VLM_PICTURE, "[mock caption] figure"
            elif el.char_count < self._min_text_chars:
                decision, text = RouteDecision.VLM_FULL_PAGE, f"[mock ocr] {el.text}"
            else:
                decision, text = RouteDecision.DOCLING_TEXT, el.text
            if decision != RouteDecision.DOCLING_TEXT:
                self.vlm_calls += 1
            results.append(RoutingResult(element=el, decision=decision, text=text))
        return results
