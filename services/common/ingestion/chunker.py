"""Sentence-boundary chunking (ACTIONPLAN Task 1.6).

Text elements -> chunks at ~512 tokens, split on sentence boundaries.
VLM outputs (tables, figures, scanned pages) -> single chunks carrying the
source element's bbox.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from services.common.ingestion.models import (
    Chunk,
    ElementType,
    ParsedElement,
    RouteDecision,
)
from services.common.ingestion.vlm_router import RoutingResult, _valid_word_ratio

logger = logging.getLogger(__name__)

# Rough English token estimate (~4 chars/token). Sentence-boundary split keeps
# each chunk near this budget without mid-sentence cuts.
TARGET_TOKENS = 512
CHARS_PER_TOKEN = 4.0
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

_VLM_SINGLE_CHUNK = (RouteDecision.VLM_TABLE, RouteDecision.VLM_PICTURE,
                     RouteDecision.VLM_FULL_PAGE)


def _standard_ocr_metadata(rr: RoutingResult) -> dict:
    """FIX-011: tag chunks whose extraction quality is mid-tier (standard_ocr).

    Pages with 0.75 <= valid_word_ratio < 0.97 are real but imperfect OCR text.
    Tag the chunk so synthesis can lower citation confidence without an extra
    VLM call. High-ratio clean digital text (>= 0.97) stays untagged.
    """
    ratio = _valid_word_ratio(rr.text)
    if 0.75 <= ratio < 0.97:
        return {
            "extraction_confidence": "standard_ocr",
            "ocr_confidence_score": round(ratio, 3),
        }
    return {}


def chunk_routed(
    routed: List[RoutingResult],
    tenant_id: str,
    doc_id: str,
    target_tokens: int = TARGET_TOKENS,
    page_number_override: Optional[int] = None,
) -> List[Chunk]:
    """Convert routed elements into embeddable Chunks.

    Phase 3.5 page-boundary strict chunking: elements are grouped by page and
    a chunk is flushed at every page transition, so no chunk ever carries text
    from two pages. Tables/figures stay single chunks with the element bbox.
    """
    chunks: List[Chunk] = []
    empty_elements = 0
    # Group routed elements by their (possibly overridden) page number, in
    # original reading order.
    by_page: dict[int, List[RoutingResult]] = {}
    for rr in routed:
        page = page_number_override or rr.element.page_number
        by_page.setdefault(page, []).append(rr)

    for page in sorted(by_page):
        page_elements = by_page[page]
        for rr in page_elements:
            if rr.decision in _VLM_SINGLE_CHUNK:
                if rr.text.strip():
                    chunks.append(
                        Chunk(
                            tenant_id=tenant_id,
                            doc_id=doc_id,
                            page_number=page_number_override or rr.element.page_number,
                            element_type=rr.element.element_type,
                            text=rr.text.strip(),
                            bbox=rr.element.bbox,
                            source=rr.decision,
                            metadata=_standard_ocr_metadata(rr),
                        )
                    )
                else:
                    empty_elements += 1
                    logger.warning(
                        "Empty VLM output dropped: doc=%s page=%s type=%s decision=%s",
                        doc_id, rr.element.page_number,
                        rr.element.element_type, rr.decision,
                    )
            else:
                chunks.extend(
                    _chunk_text(
                        rr,
                        tenant_id,
                        doc_id,
                        target_tokens=target_tokens,
                        page_number_override=page_number_override,
                    )
                )
    if empty_elements > 0:
        logger.warning(
            "doc=%s: %d elements produced no chunks (VLM fallback or empty text)",
            doc_id, empty_elements,
        )
    return chunks


def _chunk_text(
    rr: RoutingResult,
    tenant_id: str,
    doc_id: str,
    target_tokens: int,
    page_number_override: Optional[int] = None,
) -> List[Chunk]:
    text = rr.text.strip()
    if not text:
        return []

    char_budget = int(target_tokens * CHARS_PER_TOKEN)
    sentences = _SENTENCE_END.split(text)

    chunks: List[Chunk] = []
    current: List[str] = []
    current_len = 0

    def flush():
        nonlocal current, current_len
        if current:
            joined = " ".join(current).strip()
            chunks.append(
                Chunk(
                    tenant_id=tenant_id,
                    doc_id=doc_id,
                    page_number=page_number_override or rr.element.page_number,
                    element_type=rr.element.element_type,
                    text=joined,
                    bbox=rr.element.bbox,
                    source=rr.decision,
                    metadata=_standard_ocr_metadata(rr),
                )
            )
            current = []
            current_len = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if current_len + len(sentence) > char_budget and current:
            flush()
        current.append(sentence)
        current_len += len(sentence)

    flush()
    return chunks
