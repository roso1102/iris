"""Deterministic HyDE gating + output validation (Phase 0.1).

Two-stage decision (RET-004/RET-005/RET-006):

1. A cheap deterministic bypass runs first — greetings, navigation, summary
   requests, quoted searches, exact identifiers, metadata requests, already
   rewritten follow-ups and (until benchmarked) Devanagari queries never reach
   the model.
2. Only when the query is eligible *and* the baseline dense/sparse retrieval is
   weak do we generate HyDE, and then only as a lower-weight additional leg.
"""

from __future__ import annotations

import os
import re
from typing import List, Optional, Sequence, Tuple

# Mirrors search._SPECIFIC_QUERY_RE so gating does not depend on import order.
SPECIFIC_QUERY_RE = re.compile(
    r"(?:\b(?:section|clause|article|schedule|annexure|chapter|part|rule|regulation|page|table|figure|paragraph|act)\s+\d"
    r"|\b(?:20\d{2}|19\d{2})\b"
    r"|\b(?:annual report|budget|gazette|notification|circular)\b)",
    re.IGNORECASE,
)

_GREETING_RE = re.compile(
    r"^\s*(hi|hello|hey|thanks|thank you|good\s+(?:morning|afternoon|evening)|namaste)\b",
    re.IGNORECASE,
)
_NAVIGATION_RE = re.compile(
    r"\b(go to|open|navigate|next page|previous page|scroll|jump to|show me the page)\b",
    re.IGNORECASE,
)
_SUMMARY_RE = re.compile(
    r"\b(summarize|summarise|summary|tl;?dr|overview|what is this (?:document|pdf|file) about)\b",
    re.IGNORECASE,
)
_METADATA_RE = re.compile(
    r"\b(file ?name|filename|page count|how many pages|upload status|file size|"
    r"when was .* (?:uploaded|added))\b",
    re.IGNORECASE,
)
_QUOTED_RE = re.compile(r"[\"'“”‘’][^\"'“”‘’]{1,}[\"'“”‘’]")

# Exact identifiers: ABC-123, INV/9931, 123/2020, case numbers, long digits.
_EXACT_ID_RE = re.compile(
    r"\b[A-Z]{2,}[-/]?\d+\b"
    r"|\b\d+/\d{2,4}\b"
    r"|\b\d{4,}\b"
    r"|\b(?:case|order|fir|invoice|reference|ref)\s*(?:no\.?|number|#)?\s*[A-Za-z0-9][A-Za-z0-9/-]*\d[A-Za-z0-9/-]*\b",
    re.IGNORECASE,
)

# Baseline weakness thresholds. These values are PLACEHOLDERS and must be
# calibrated against the staging retrieval dataset (`retrieval-v1`) before the
# gate is trusted in production — a raw Qdrant cosine score is not comparable
# across embedding models. Override with HYDE_* env vars during calibration.
DEFAULT_TOP_SCORE_THRESHOLD = 0.25
DEFAULT_MARGIN_THRESHOLD = 0.02
DEFAULT_AGREEMENT_THRESHOLD = 0.2
HYDE_LEG_WEIGHT = 0.3
HYDE_ESTIMATED_COST_USD = 0.00002


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def top_score_threshold() -> float:
    return _env_float("HYDE_TOP_SCORE_THRESHOLD", DEFAULT_TOP_SCORE_THRESHOLD)


def margin_threshold() -> float:
    return _env_float("HYDE_MARGIN_THRESHOLD", DEFAULT_MARGIN_THRESHOLD)


def agreement_threshold() -> float:
    return _env_float("HYDE_AGREEMENT_THRESHOLD", DEFAULT_AGREEMENT_THRESHOLD)


def bypass_reason(query: str, *, rewritten: bool = False) -> Optional[str]:
    """Return the deterministic bypass reason, or None if HyDE is eligible."""
    if rewritten:
        return "rewritten_followup"
    if not query or not query.strip():
        return "empty"
    if _GREETING_RE.search(query):
        return "greeting"
    if _NAVIGATION_RE.search(query):
        return "navigation"
    if _SUMMARY_RE.search(query):
        return "summary_request"
    if _METADATA_RE.search(query):
        return "metadata_request"
    if _QUOTED_RE.search(query):
        return "quoted_search"
    if SPECIFIC_QUERY_RE.search(query) or _EXACT_ID_RE.search(query):
        return "exact_identifier"
    from services.common.retrieval.hindi import contains_devanagari, is_romanized_hindi

    if contains_devanagari(query) or is_romanized_hindi(query):
        return "devanagari"
    return None


def baseline_is_weak(
    dense_results: Sequence[Tuple[str, float]],
    sparse_results: Sequence[Tuple[str, float]],
) -> bool:
    """True when baseline retrieval is missing or the top dense score is low."""
    if not dense_results and not sparse_results:
        return True
    top = dense_results[0][1] if dense_results else 0.0
    return top < top_score_threshold()


def low_agreement(
    dense_results: Sequence[Tuple[str, float]],
    sparse_results: Sequence[Tuple[str, float]],
    k: int = 5,
) -> bool:
    """True when dense and sparse top-k share little (uncertain retrieval)."""
    dense_ids = {cid for cid, _ in list(dense_results)[:k]}
    sparse_ids = {cid for cid, _ in list(sparse_results)[:k]}
    union = dense_ids | sparse_ids
    if not union:
        return True
    return (len(dense_ids & sparse_ids) / len(union)) < agreement_threshold()


_NUMBER_RE = re.compile(r"\d[\d,./:-]*")
_MONTH_RE = re.compile(
    r"\b(?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\b",
    re.IGNORECASE,
)
_CAPS_TOKEN_RE = re.compile(r"\b[A-Z][A-Za-z0-9]{2,}\b")

# Common sentence-starters / function words that are capitalized but are not
# entities. Anything else capitalized and absent from the query is treated as a
# newly introduced entity/identifier.
_ENTITY_STOPWORDS = frozenset({
    "the", "this", "that", "these", "those", "a", "an", "it", "its", "in", "on",
    "at", "for", "and", "or", "but", "if", "when", "while", "after", "before",
    "however", "therefore", "according", "based", "document", "question",
    "answer", "hypothetical", "snippet", "query", "summary", "policy", "report",
    "section", "first", "second", "third", "also", "there", "their", "they",
    "he", "she", "his", "her", "we", "our", "you", "your", "may", "can", "not",
})


def _introduces_new_content(text: str, query: str) -> bool:
    """True when ``text`` introduces content absent from the query.

    Checks numbers/amounts, month names, ALL-CAPS/alphabetic identifiers and
    capitalized entity tokens. Used on the hypothesis AND the keywords together.
    """
    if not isinstance(text, str):
        return True
    query_numbers = set(_NUMBER_RE.findall(query))
    if any(number not in query_numbers for number in _NUMBER_RE.findall(text)):
        return True

    query_lower = query.lower()
    if any(month.lower() not in query_lower for month in _MONTH_RE.findall(text)):
        return True

    for token in _CAPS_TOKEN_RE.findall(text):
        lowered = token.lower()
        if lowered in _ENTITY_STOPWORDS:
            continue
        if token in query or lowered in query_lower:
            continue
        return True
    return False


def validate_hyde_output(raw, query: str) -> Optional[dict]:
    """Normalize and validate HyDE output; return None when unusable.

    Provider output MUST be the structured ``{"hypothesis", "keywords"}`` object.
    Legacy plain-string output is rejected outright — it cannot be validated to
    the same standard. The hypothesis and keywords are validated together for
    newly introduced numbers, dates, identifiers and named entities; any new
    content causes HyDE to be skipped and baseline retrieval to continue.
    """
    if not isinstance(raw, dict):
        return None
    hypothesis = raw.get("hypothesis")
    if not isinstance(hypothesis, str) or not hypothesis.strip():
        return None
    hypothesis = hypothesis.strip()
    keywords = raw.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = []
    cleaned = [k.strip() for k in keywords if isinstance(k, str) and k.strip()]

    if _introduces_new_content(hypothesis, query):
        return None
    if _introduces_new_content(" ".join(cleaned), query):
        return None
    return {"hypothesis": hypothesis, "keywords": cleaned}


def hyde_text_of(parsed: dict) -> str:
    """Combine hypothesis + keywords into the text to embed."""
    hypothesis = parsed.get("hypothesis", "")
    keywords: List[str] = parsed.get("keywords", []) or []
    if keywords:
        return f"{hypothesis} {' '.join(keywords)}"
    return hypothesis
