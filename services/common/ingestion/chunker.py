"""Sentence-boundary chunking (ACTIONPLAN Task 1.6).

Text elements -> chunks at ~512 tokens, split on sentence boundaries.
VLM outputs (tables, figures, scanned pages) -> single chunks carrying the
source element's bbox.
"""

from __future__ import annotations

import re
from typing import List, Optional

from services.common.ingestion.models import (
    Chunk,
    ElementType,
    ParsedElement,
    RouteDecision,
)
from services.common.ingestion.vlm_router import RoutingResult

# Rough English token estimate (~4 chars/token). Sentence-boundary split keeps
# each chunk near this budget without mid-sentence cuts.
TARGET_TOKENS = 512
CHARS_PER_TOKEN = 4.0
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

_VLM_SINGLE_CHUNK = (RouteDecision.VLM_TABLE, RouteDecision.VLM_PICTURE,
                     RouteDecision.VLM_FULL_PAGE)


def chunk_routed(
    routed: List[RoutingResult],
    tenant_id: str,
    doc_id: str,
    target_tokens: int = TARGET_TOKENS,
    page_number_override: Optional[int] = None,
) -> List[Chunk]:
    """Convert routed elements into embeddable Chunks."""
    chunks: List[Chunk] = []
    for rr in routed:
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
                    )
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
