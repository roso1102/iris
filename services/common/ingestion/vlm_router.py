"""Page-Wise VLM Router (ACTIONPLAN Task 1.5).

Per page, per element, decide the cheapest correct processor:

  | Docling signal                          | Route                         |
  |-----------------------------------------|-------------------------------|
  | Text/Paragraph, char count >= 150       | Docling text (zero API cost)  |
  | Table, any char count                   | Gemini Vision on table crop   |
  | Picture/Figure, any char count          | Gemini Vision on figure crop  |
  | Any element, char count < 150           | Gemini Vision on full page    |

All VLM calls go through ModelProvider.extract_table()/ocr_page() (SRS FR-8).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

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
    def render_page(self, pdf_path: str, page_number: int, scale: float = 2.0) -> "object":
        """Return a PIL.Image of the given 1-based page at `scale`."""


class VlmRouter(ABC):
    @abstractmethod
    def route(self, elements: List[ParsedElement]) -> List[RoutingResult]:
        """Apply the routing table to a parsed document."""


class NoopPageRenderer(PageRenderer):
    """Used when VLM routing is disabled (tests / cost control)."""

    def render_page(self, pdf_path: str, page_number: int, scale: float = 2.0):
        raise RuntimeError("Page rendering unavailable (NoopPageRenderer)")


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
        self.vlm_calls = 0

    def route(self, elements: List[ParsedElement], pdf_path: str = "") -> List[RoutingResult]:
        results: List[RoutingResult] = []
        # Group by page so full-page crops reuse one render.
        pages: dict[int, list[ParsedElement]] = {}
        for el in elements:
            pages.setdefault(el.page_number, []).append(el)

        for page_no in sorted(pages):
            page_elements = pages[page_no]
            page_render = None
            for el in page_elements:
                decision, text = self._route_element(el, pdf_path, page_render)
                if decision == RouteDecision.VLM_FULL_PAGE:
                    # A full-page crop serves every low-text element on the page.
                    if page_render is None:
                        page_render = self._renderer.render_page(
                            pdf_path, page_no, scale=2.0
                        )
                    crop = page_render.crop((0, 0, page_render.width, page_render.height))
                    text = self._provider.ocr_page(_to_png_bytes(crop))
                    self.vlm_calls += 1
                elif decision in (RouteDecision.VLM_TABLE, RouteDecision.VLM_PICTURE):
                    crop = _crop_bbox(page_render, el.bbox, pdf_path, page_no)
                    text = self._provider.extract_table(_to_png_bytes(crop))
                    self.vlm_calls += 1
                results.append(RoutingResult(element=el, decision=decision, text=text))
        return results

    def _route_element(
        self, el: ParsedElement, pdf_path: str, page_render: object
    ) -> tuple[RouteDecision, str]:
        # Structural elements (Table/Picture) always go to VLM regardless of
        # char count (ACTIONPLAN 1.5): Docling's text for these is unreliable.
        if el.element_type == ElementType.TABLE:
            return RouteDecision.VLM_TABLE, ""
        if el.element_type == ElementType.PICTURE:
            return RouteDecision.VLM_PICTURE, ""
        if el.char_count < self._min_text_chars:
            # Scanned / image-only element -> full page VLM.
            return RouteDecision.VLM_FULL_PAGE, ""
        return RouteDecision.DOCLING_TEXT, el.text


def _crop_bbox(page_render: object, bbox: List[float], pdf_path: str, page_no: int):
    """Crop a normalized bbox [l,t,r,b] from a rendered page."""
    if page_render is None:
        raise RuntimeError(f"Page {page_no} not rendered; cannot crop {bbox}")
    w, h = page_render.width, page_render.height
    l, t, r, b = bbox
    return page_render.crop((int(l * w), int(t * h), int(r * w), int(b * h)))


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
