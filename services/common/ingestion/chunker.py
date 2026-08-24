"""Sentence-boundary chunking (ACTIONPLAN Task 1.6).

Text elements -> chunks at ~256 tokens (CHUNK_TARGET_TOKENS env; Stage 3a
small-to-big: fine units rank pages precisely, /query expands to parent
pages for synthesis context), split on sentence boundaries.
VLM tables split at ROW-GROUP boundaries with the header row (+ caption)
repeated in every sub-chunk (pipeline #2 — rows without their header lose
column meaning); full-page OCR and picture captions are prose and split at
sentence boundaries. Every VLM chunk keeps the source element's bbox.
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

_VLM_SINGLE_CHUNK = (RouteDecision.VLM_PICTURE,)

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
            if rr.decision == RouteDecision.VLM_TABLE:
                table_chunks = _chunk_vlm_table(
                    rr,
                    tenant_id,
                    doc_id,
                    target_tokens=target_tokens,
                    page_number_override=page_number_override,
                )
                if table_chunks:
                    chunks.extend(table_chunks)
                else:
                    empty_elements += 1
                    logger.warning(
                        "Empty VLM output dropped: doc=%s page=%s type=%s decision=%s",
                        doc_id, rr.element.page_number,
                        rr.element.element_type, rr.decision,
                    )
            elif rr.decision in _VLM_SINGLE_CHUNK:
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


# ── Pipeline #2: VLM table row-group splitting ──────────────────────────────

# Markdown table row: starts with an optional leading "|" ... trailing "|".
_MD_ROW = re.compile(r"^\s*\|.*\|\s*$")
# Separator row between header and body: | --- | :---: | --- |
_MD_SEP = re.compile(r"^\s*\|[\s:\-|]+\|\s*$")


def _split_markdown_table(text: str) -> tuple[list[str], list[str]]:
    """Split markdown table text into (header_lines, body_lines).

    header_lines = caption lines (before the table) + header row + separator
    row; body_lines = the data rows (plus any trailing non-table prose, kept
    adjacent to the rows it follows). Without a separator row the first
    table line is treated as the header.
    """
    lines = text.splitlines()
    header: list[str] = []
    body: list[str] = []
    in_table = False
    seen_sep = False
    for line in lines:
        if in_table and not seen_sep and _MD_SEP.match(line):
            header.append(line)
            seen_sep = True
        elif not seen_sep and _MD_ROW.match(line):
            in_table = True
            header.append(line)
        else:
            (body if seen_sep else header).append(line)
    if not seen_sep:
        # No separator row: treat the first table line as the header.
        table_idxs = [i for i, ln in enumerate(header) if _MD_ROW.match(ln)]
        if len(table_idxs) > 1:
            cut = table_idxs[0] + 1
            body = header[cut:] + body
            header = header[:cut]
    return header, body


def _chunk_vlm_table(
    rr: RoutingResult,
    tenant_id: str,
    doc_id: str,
    target_tokens: int,
    page_number_override: Optional[int] = None,
) -> List[Chunk]:
    """Split a VLM table at ROW-GROUP boundaries sized to the token budget.

    The header row + caption are repeated in every sub-chunk (settled spec:
    rows without their header lose column meaning). Rows are never split.
    A table that fits the budget stays a single chunk, byte-identical to
    the pre-pipeline-#2 output.
    """
    text = rr.text.strip()
    if not text:
        return []

    header_lines, body_rows = _split_markdown_table(text)
    header_text = "\n".join(header_lines).strip()
    header_len = len(header_text) + 1 if header_text else 0

    # Oversized header (pathological): emit as its own chunk, no body rows
    # would ever fit with it. Still better than dropping the table.
    if header_len > int(target_tokens * CHARS_PER_TOKEN):
        return [Chunk(
            tenant_id=tenant_id,
            doc_id=doc_id,
            page_number=page_number_override or rr.element.page_number,
            element_type=rr.element.element_type,
            text=header_text,
            bbox=rr.element.bbox,
            source=rr.decision,
            metadata=_chunk_metadata(rr),
        )]

    def make_chunk(rows: list[str]) -> Chunk:
        body_text = "\n".join(rows).strip()
        combined = f"{header_text}\n{body_text}" if header_text and body_text else (header_text or body_text)
        return Chunk(
            tenant_id=tenant_id,
            doc_id=doc_id,
            page_number=page_number_override or rr.element.page_number,
            element_type=rr.element.element_type,
            text=combined,
            bbox=rr.element.bbox,
            source=rr.decision,
            metadata=_chunk_metadata(rr),
        )

    groups: list[list[str]] = []
    current: list[str] = []
    current_len = header_len
    for row in body_rows:
        row_len = len(row) + 1
        if current_len + row_len > int(target_tokens * CHARS_PER_TOKEN) and current:
            groups.append(current)
            current = []
            current_len = header_len
        current.append(row)
        current_len += row_len
    if current:
        groups.append(current)

    if len(groups) <= 1:
        # Fits the budget: keep the original text byte-identical.
        return [Chunk(
            tenant_id=tenant_id,
            doc_id=doc_id,
            page_number=page_number_override or rr.element.page_number,
            element_type=rr.element.element_type,
            text=text,
            bbox=rr.element.bbox,
            source=rr.decision,
            metadata=_chunk_metadata(rr),
        )]

    return [make_chunk(rows) for rows in groups]
