"""Embedding vector validation (Phase 0.1).

Single source of truth for the expected vector shape. Validation runs over the
*entire* batch before any vector is assigned to a chunk or used for a search,
so a partial/malformed provider response can never reach Qdrant or silently
drop chunks.
"""

from __future__ import annotations

import math
from typing import List, Sequence

from services.common.errors import ErrorCode
from services.common.reliability import PermanentError

# text-embedding-004 produces 768-dimensional vectors; the Qdrant collection
# is created with the same dimension. Kept here so ingestion and retrieval
# validate against one constant.
EMBEDDING_DIM = 768


class EmbeddingInvalidError(PermanentError):
    """A provider embedding response failed validation."""

    code = ErrorCode.EMBEDDING_INVALID

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"invalid embedding: {reason}")


def validate_embedding_vector(vec: Sequence[float]) -> List[float]:
    """Validate one vector, returning a float copy. Raises EmbeddingInvalidError."""
    if isinstance(vec, (str, bytes)) or not isinstance(vec, (list, tuple)):
        raise EmbeddingInvalidError("not_a_list")
    if len(vec) != EMBEDDING_DIM:
        raise EmbeddingInvalidError(f"wrong_dimension:{len(vec)}")

    out: List[float] = []
    all_zero = True
    for value in vec:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EmbeddingInvalidError("non_numeric")
        number = float(value)
        if not math.isfinite(number):
            raise EmbeddingInvalidError("non_finite")
        if number != 0.0:
            all_zero = False
        out.append(number)

    if all_zero:
        raise EmbeddingInvalidError("zero_vector")
    return out


def validate_embedding_batch(
    chunks: Sequence[object], embeddings: object
) -> List[List[float]]:
    """Validate a full embedding batch against its chunks.

    Returns the validated float vectors. Raises before any caller mutation when
    the response is not a list, is the wrong length, or contains an invalid
    vector.
    """
    if isinstance(embeddings, (str, bytes)) or not isinstance(embeddings, (list, tuple)):
        raise EmbeddingInvalidError("not_a_list")
    if len(embeddings) != len(chunks):
        raise EmbeddingInvalidError(f"count_mismatch:{len(embeddings)}!={len(chunks)}")

    validated: List[List[float]] = []
    for raw in embeddings:
        validated.append(validate_embedding_vector(raw))
    return validated
