"""Document hash cache for ingestion deduplication.

If a PDF has been previously ingested (same SHA256 + tenant), return
cached chunk references from Qdrant instead of re-processing.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from services.common.ingestion.models import Chunk
from services.common.ingestion.store import ChunkStore, get_chunk_store

logger = logging.getLogger(__name__)


def get_cached_chunks(
    doc_sha256: str,
    tenant_id: str,
    doc_id: str,
    store: Optional[ChunkStore] = None,
) -> Optional[List[Chunk]]:
    """Check if doc SHA256 has been previously stored.

    Returns list of Chunks if found, None otherwise.
    Uses Qdrant store (scoped by tenant_id) to find existing chunks.
    """
    if not doc_sha256:
        return None

    store = store or get_chunk_store()
    try:
        chunks = store.get_by_doc(doc_id, tenant_id)
        if chunks:
            logger.info(
                "Cache hit: doc_id=%s sha256=%s has %d existing chunks",
                doc_id, doc_sha256[:12], len(chunks),
            )
            return chunks
    except Exception:
        logger.warning("Cache lookup failed for doc_id=%s", doc_id, exc_info=True)

    return None
