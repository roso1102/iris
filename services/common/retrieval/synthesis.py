"""Server-side citation validation (Phase 3.0 Task 3.4 + Phase 9.0 D/E).

The LLM's structured output may reference chunk_ids that were never retrieved
(hallucinations). This module validates every citation against the actual
retrieved chunk set and overwrites the citation's spatial fields (doc_id,
page_number, bbox, text_snippet) from the trusted retrieved chunk — never
trusting the LLM's coordinates.

It also normalizes inline citation markers in the answer text: malformed arrays
like "[1, 2]" or "[1-3]" are split into separate "[1] [2] [3]" and any marker that
doesn't map to a real retrieved chunk is dropped (Phase 9.0-E).
"""

from __future__ import annotations

import re
from typing import Dict, List

from services.common.models.base import Citation, StructuredAnswer
from services.common.retrieval.models import ScoredChunk

# Matches any bracketed integer citation marker: [1], [2,3], [1-3], [2, 3, 4].
_MARKER_RE = re.compile(r"\[(\d+(?:\s*[,–—-]\s*\d+)*)\]")


def _expand_marker(group: str) -> List[int]:
    """Expand a marker body like "1", "2,3", or "1-3" into a sorted int list.

    Handles comma-separated lists (optionally with ranges) — never emits
    markers outside 1..len(refs) (collectively validated by the caller).
    """
    out: List[int] = []
    for part in re.split(r"[,\s]+", group.strip()):
        if not part:
            continue
        if "-" in part or "–" in part or "—" in part:
            dash = re.search(r"[\-–—]", part)
            if not dash:
                continue
            lo = part[: dash.start()].strip()
            hi = part[dash.start() + 1 :].strip()
            if not lo.isdigit() or not hi.isdigit():
                continue
            lo_i, hi_i = int(lo), int(hi)
            out.extend(range(min(lo_i, hi_i), max(lo_i, hi_i) + 1))
        elif part.isdigit():
            out.append(int(part))
    return out


def normalize_answer_markers(answer_text: str, refs: Dict[str, ScoredChunk]) -> str:
    """Split malformed citation markers and drop any ref not in `refs`.

    `refs` maps the integer marker `str(N)` to the ScoredChunk for position N in
    the retrieved list (1-based). Markers referencing positions outside the map
    are removed entirely, and `[2,3]` becomes `[2] [3]`.
    """
    if not answer_text:
        return answer_text

    def _repl(m: "re.Match[str]") -> str:
        nums = _expand_marker(m.group(1))
        kept = [n for n in sorted(set(nums)) if str(n) in refs]
        return " ".join(f"[{n}]" for n in kept) if kept else ""

    return _MARKER_RE.sub(_repl, answer_text)


def validate_citations(
    answer: StructuredAnswer,
    retrieved: List[ScoredChunk],
) -> StructuredAnswer:
    """Drop hallucinated citations, overwrite valid ones with real metadata,
    and normalize inline [N] markers in the answer text.

    A citation is valid only if its `chunk_id` appears in `retrieved`. For
    valid citations, doc_id/page_number/bbox/text_snippet are taken from the
    retrieved chunk, not the LLM's output.
    """
    if not retrieved:
        return StructuredAnswer(answer=answer.answer, citations=[])

    by_id = {c.chunk_id: c for c in retrieved}
    # 1-based ref map: marker "[N]" -> chunk at position N-1 in `retrieved`.
    refs = {str(i): c for i, c in enumerate(retrieved, start=1)}

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

    return StructuredAnswer(
        answer=normalize_answer_markers(answer.answer, refs),
        citations=valid,
    )
