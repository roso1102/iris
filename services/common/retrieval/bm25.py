"""BM25 TF-IDF sparse vector tokenizer for hybrid search.

Uses rank_bm25 (pure Python, MIT licensed) for proper TF-IDF weighting
to penalize statutory boilerplate words across legal/gazette documents.
"""

from __future__ import annotations

import re
from typing import Dict, List

try:
    import mmh3  # pip install mmh3 — MurmurHash3, stable cross-process
    _USE_MMH3 = True
except ImportError:  # pragma: no cover — fallback for local envs lacking mmh3
    import hashlib
    _USE_MMH3 = False

_STOPWORDS = frozenset(
    {
        "the", "and", "for", "that", "this", "with", "from", "are", "was",
        "has", "not", "but", "all", "can", "had", "her", "his", "its",
        "may", "one", "out", "she", "some", "such", "than", "they", "this",
        "will", "about", "after", "also", "been", "being", "could", "each",
        "into", "more", "most", "only", "other", "over", "said", "same",
        "should", "their", "them", "then", "there", "these", "those", "under",
        "upon", "very", "were", "what", "when", "which", "while", "whom",
        "would", "section", "clause", "act", "rule", "order", "notification",
        "gazette", "government", "india", "state", "central", "shall",
        "provided", "hereby", "pursuant", "dated", "hereinafter", "aforesaid",
        "whereas", "hereof", "thereof",
    }
)

_MAX_TERM_HASH = 2 ** 24 - 1
_TOKEN_RE = re.compile(r"\w{3,}", re.UNICODE)


def _hash_term(term: str) -> int:
    """Deterministic, cross-process stable hash for a BM25 term index.

    Python's built-in hash() is randomized per process (hash randomization,
    PEP 456 / PYTHONHASHSEED). Using it means ingestion-worker and retrieval-
    api produce completely different sparse indices for the same word, so
    every sparse search silently returns zero matches.

    mmh3 (MurmurHash3) is fast, deterministic, and the industry standard for
    this use case. Falls back to md5 if mmh3 is not installed.
    """
    if _USE_MMH3:
        return mmh3.hash(term, signed=False) & _MAX_TERM_HASH
    hex_digest = __import__("hashlib").md5(term.encode("utf-8")).hexdigest()
    return int(hex_digest[:8], 16) & _MAX_TERM_HASH


def tokenize(text: str) -> List[str]:
    """Lowercase + split on word boundaries, filter short words and stopwords."""
    tokens = _TOKEN_RE.findall(text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


def text_to_sparse(text: str) -> Dict[int, float]:
    """Tokenize text into {term_hash: tf_idf_score} dict via rank_bm25.

    Uses a single-document BM25Okapi fit over the tokenized text
    to get TF-IDF scores that penalize terms occurring too frequently
    within the document (e.g., statutory boilerplate).
    """
    tokens = tokenize(text)
    if not tokens:
        return {}

    from rank_bm25 import BM25Okapi

    bm25 = BM25Okapi([tokens])
    doc_scores = bm25.get_scores(tokens)
    unique_terms: Dict[str, float] = {}
    for token, score in zip(tokens, doc_scores):
        unique_terms[token] = score
    return {_hash_term(t): float(score) for t, score in unique_terms.items()}


def sparse_to_qdrant_indices_values(sparse_dict: Dict[int, float]):
    """Convert to Qdrant SparseVector-compatible (indices, values) pair."""
    if not sparse_dict:
        return [], []
    indices = sorted(sparse_dict.keys())
    values = [sparse_dict[i] for i in indices]
    return indices, values
