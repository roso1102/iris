"""Sentence-boundary chunking (ACTIONPLAN Task 1.6).

Text elements -> chunks at ~256 tokens (CHUNK_TARGET_TOKENS env; Stage 3a
small-to-big: fine units rank pages precisely, /query expands to parent
pages for synthesis context), split on sentence boundaries.
VLM outputs (tables, figures, scanned pages) -> single chunks carrying the
source element's bbox.
"""

from __future__ import annotations

import logging
import os
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

# Small-to-big retrieval units (Stage 3a): ~256 tokens ≈ 1024 chars. Finer
# chunks make page ranking (Page-Recall/MRR) sharper and bbox highlights
# tighter; the synthesis context is expanded to parent pages at query time.
TARGET_TOKENS = 256
CHARS_PER_TOKEN = 4.0
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

_VLM_SINGLE_CHUNK = (RouteDecision.VLM_TABLE, RouteDecision.VLM_PICTURE,
                     RouteDecision.VLM_FULL_PAGE)

# A bbox covering >=70% of the page (VLM full-page OCR chunks) is a
# page-level citation: the frontend jumps to the page instead of drawing a
# giant frame that carries no information.
_PAGE_LEVEL_AREA = 0.7


def _env_target_tokens() -> int:
    """CHUNK_TARGET_TOKENS env, clamped to a sane 64..2048 range."""
    raw = os.environ.get("CHUNK_TARGET_TOKENS", "").strip()
    if not raw:
        return TARGET_TOKENS
    try:
        return max(64, min(2048, int(raw)))
    except ValueError:
        logger.warning("Invalid CHUNK_TARGET_TOKENS %r; using %d", raw, TARGET_TOKENS)
        return TARGET_TOKENS


def _page_level_metadata(bbox: list[float]) -> dict:
    if len(bbox) == 4:
        left, top, right, bottom = bbox
        if (right - left) * (bottom - top) >= _PAGE_LEVEL_AREA:
            return {"page_level": True}
    return {}


def _chunk_metadata(rr: RoutingResult) -> dict:
    meta = _standard_ocr_metadata(rr)
    meta.update(_page_level_metadata(rr.element.bbox))
    return meta


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
    target_tokens: Optional[int] = None,
    page_number_override: Optional[int] = None,
) -> List[Chunk]:
    """Convert routed elements into embeddable Chunks.

    Phase 3.5 page-boundary strict chunking: elements are grouped by page and
    a chunk is flushed at every page transition, so no chunk ever carries text
    from two pages. Tables/figures stay single chunks with the element bbox.
    """
    if target_tokens is None:
        target_tokens = _env_target_tokens()
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
                            metadata=_chunk_metadata(rr),
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
                    metadata=_chunk_metadata(rr),
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
