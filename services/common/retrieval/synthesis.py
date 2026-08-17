"""Server-side citation validation (Phase 3.0 Task 3.4).

The LLM's structured output may reference chunk_ids that were never retrieved
(hallucinations). This module validates every citation against the actual
retrieved chunk set and overwrites the citation's spatial fields (doc_id,
page_number, bbox, text_snippet) from the trusted retrieved chunk — never
trusting the LLM's coordinates.
"""

from __future__ import annotations

from typing import List

from services.common.models.base import Citation, StructuredAnswer
from services.common.retrieval.models import ScoredChunk


def validate_citations(
    answer: StructuredAnswer,
    retrieved: List[ScoredChunk],
) -> StructuredAnswer:
    """Drop hallucinated citations and overwrite valid ones with real metadata.

    A citation is valid only if its `chunk_id` appears in `retrieved`. For
    valid citations, doc_id/page_number/bbox/text_snippet are taken from the
    retrieved chunk, not the LLM's output.
    """
    if not retrieved:
        return StructuredAnswer(answer=answer.answer, citations=[])

    by_id = {c.chunk_id: c for c in retrieved}
    valid: List[Citation] = []
    for citation in answer.citations:
        chunk = by_id.get(citation.chunk_id)
        if chunk is None:
            continue
        valid.append(
            Citation(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                page_number=chunk.page_number,
                bbox=list(chunk.bbox),
                text_snippet=chunk.text[:500],
            )
        )

    return StructuredAnswer(answer=answer.answer, citations=valid)
