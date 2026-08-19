"""BM25 sparse vector tokenizer backed by FastEmbed's Qdrant/bm25 model.

Replaces the old mmh3/TF emergency implementation (Phase 2.5.7) with a
production pre-trained sparse model. The model ships pre-trained IDF values
from a large real-world corpus, so common words (including legal boilerplate)
are penalized without requiring corpus state at runtime.

The Qdrant collection MUST use `modifier="idf"` on its sparse vector config
(FastEmbed's Qdrant/bm25 model emits raw term counts; Qdrant applies the
pre-trained IDF on its side).
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Dict, List, Optional

_MODEL_NAME = "Qdrant/bm25"
_LANGUAGE = "english"
_TOKEN_MAX_LENGTH = 40

# Model weights are baked into the image at build time (see the Dockerfiles):
#   /app/models/<HF cache layout: models--Qdrant--bm25/{refs, snapshots/<hash>}>
# The path is overridable via FASTEMBED_CACHE_PATH (e.g. tests), and defaults
# to the baked dir. Read lazily so env overrides (tests) take effect.
_DEFAULT_CACHE_DIR = "/app/models"

_lock = threading.Lock()
_model: Optional[object] = None


def _resolve_cache_dir() -> str:
    """Return the model cache dir, preferring the explicitly-set path.

    Resolution order (first that yields a usable cache):
      1. FASTEMBED_CACHE_PATH (explicit; tests + CI set this).
      2. The baked /app/models dir (production images).
      3. The user-level Hugging Face cache (~/.cache/huggingface) so local
         `unittest` runs work offline without the Docker bake.
    """
    explicit = os.environ.get("FASTEMBED_CACHE_PATH", "").strip()
    if explicit:
        return explicit
    home_cache = str(Path.home() / ".cache" / "huggingface")
    for candidate in (_DEFAULT_CACHE_DIR, home_cache):
        if Path(candidate, "models--Qdrant--bm25").exists():
            return candidate
    return home_cache


def _get_model():
    """Lazily initialize the singleton FastEmbed Bm25 model (thread-safe).

    Loads strictly from the local cache (local_files_only=True) so cold
    starts never reach out to Hugging Face; if the cache is missing this
    raises a clear error instead of silently downloading.
    """
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed.sparse.bm25 import Bm25

                cache_dir = _resolve_cache_dir()
                local_only = Path(cache_dir, "models--Qdrant--bm25").exists()
                _model = Bm25(
                    model_name=_MODEL_NAME,
                    language=_LANGUAGE,
                    token_max_length=_TOKEN_MAX_LENGTH,
                    cache_dir=cache_dir,
                    local_files_only=local_only,
                )
    return _model


def text_to_sparse(text: str) -> Dict[int, float]:
    """Encode text into {term_index: raw_term_count} via Qdrant/bm25.

    Returns an empty dict for empty/whitespace text. The values are raw term
    counts (not IDF-weighted); Qdrant applies IDF via `modifier="idf"`.
    """
    if not text or not text.strip():
        return {}

    model = _get_model()
    result = next(iter(model.query_embed(text)))
    return result.as_dict()


def sparse_to_qdrant_indices_values(sparse_dict: Dict[int, float]):
    """Convert to Qdrant SparseVector-compatible (indices, values) pair."""
    if not sparse_dict:
        return [], []
    indices = sorted(sparse_dict.keys())
    values = [sparse_dict[i] for i in indices]
    return indices, values


def tokenize(text: str) -> List[str]:
    """Return the term indices encoded for `text` (for tests/debugging).

    FastEmbed's Bm25 does tokenization + stemming + stopword filtering
    internally, so the observable "tokens" are the sparse term indices.
    """
    return [str(i) for i in sorted(text_to_sparse(text).keys())]
