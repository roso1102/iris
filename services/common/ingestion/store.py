"""Chunk store (ACTIONPLAN Task 1.9).

`ChunkStore` ABC with two implementations:
  * MemoryChunkStore — dict-backed; used in dev/tests when QDRANT_URL is unset.
  * QdrantChunkStore — real vector write path; used once Phase 2.0 provisions
    the Qdrant VM and sets QDRANT_URL.

Production Qdrant collection schema (Phase 2.0 builds retrieval on it):
  point id  = chunk.id (uuid string)
  vector    = dense 768-d (text-embedding-004)
  payload   = {tenant_id, doc_id, page_number, element_type, bbox, text}
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from services.common.ingestion.models import Chunk

logger = logging.getLogger(__name__)

COLLECTION_NAME = "iris_chunks"
EMBEDDING_DIM = 768


class ChunkStore(ABC):
    @abstractmethod
    def upsert_batch(self, chunks: List[Chunk]) -> int:
        """Persist chunks; returns the number written."""

    @abstractmethod
    def get_by_doc(self, doc_id: str, tenant_id: str) -> List[Chunk]:
        """Return all chunks for a document, enforcing tenant isolation."""


class MemoryChunkStore(ChunkStore):
    """In-memory store for dev/tests. Thread-safe."""

    def __init__(self) -> None:
        self._by_doc: Dict[str, List[Chunk]] = {}
        self._lock = threading.Lock()

    def upsert_batch(self, chunks: List[Chunk]) -> int:
        with self._lock:
            for chunk in chunks:
                self._by_doc.setdefault(chunk.doc_id, []).append(chunk)
        return len(chunks)

    def get_by_doc(self, doc_id: str, tenant_id: str) -> List[Chunk]:
        with self._lock:
            return [c for c in self._by_doc.get(doc_id, []) if c.tenant_id == tenant_id]


class QdrantChunkStore(ChunkStore):
    """Writes chunks to Qdrant. Requires qdrant-client and a reachable URL."""

    def __init__(self, url: str, collection: str = COLLECTION_NAME, api_key: Optional[str] = None) -> None:
        from qdrant_client import QdrantClient, models

        self._client = QdrantClient(url=url, api_key=api_key or os.getenv("QDRANT_API_KEY"))
        self._collection = collection
        try:
            self._client.get_collection(collection_name=collection)
        except Exception:
            self._client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIM,
                    distance=models.Distance.COSINE,
                ),
            )
        logger.info("Ensured Qdrant collection '%s' exists", collection)

    def upsert_batch(self, chunks: List[Chunk]) -> int:
        from qdrant_client import models

        if not chunks:
            return 0
        points = [
            models.PointStruct(
                id=chunk.id,
                vector=chunk.embedding or [],
                payload={
                    "tenant_id": chunk.tenant_id,
                    "doc_id": chunk.doc_id,
                    "page_number": chunk.page_number,
                    "element_type": chunk.element_type.value,
                    "bbox": chunk.bbox,
                    "text": chunk.text,
                },
            )
            for chunk in chunks
        ]
        self._client.upsert(collection_name=self._collection, points=points)
        return len(points)

    def get_by_doc(self, doc_id: str, tenant_id: str) -> List[Chunk]:
        from qdrant_client import models

        hits, _ = self._client.scroll(
            collection_name=self._collection,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="doc_id", match=models.MatchValue(value=doc_id)
                    ),
                    models.FieldCondition(
                        key="tenant_id", match=models.MatchValue(value=tenant_id)
                    ),
                ]
            ),
            with_payload=True,
            with_vectors=False,
        )
        return [Chunk(id=h.id, **{k: v for k, v in h.payload.items()}) for h in hits]


def get_chunk_store() -> ChunkStore:
    """Factory: QdrantChunkStore when QDRANT_URL is set, else MemoryChunkStore."""
    url = os.getenv("QDRANT_URL", "").strip()
    if url:
        return QdrantChunkStore(url=url)
    logger.info("QDRANT_URL unset; using MemoryChunkStore (dev/test mode)")
    return MemoryChunkStore()
