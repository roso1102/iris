"""Chunk store (ACTIONPLAN Task 1.9 + Phase 2.0 retrieval).

`ChunkStore` ABC with two implementations:
  * MemoryChunkStore — dict-backed; used in dev/tests when QDRANT_URL is unset.
  * QdrantChunkStore — real vector write + search/delete; used once Phase 2.0
    provisions the Qdrant VM and sets QDRANT_URL.

Phase 2.0 collection schema (iris_chunks_v2):
  named vectors:
    dense       — 768-d float, COSINE, binary quantized, on_disk
    bm25_sparse — sparse TF-IDF vector
  payload indexes: tenant_id, doc_id, session_id (keyword)
  hnsw: payload_m=16
"""

from __future__ import annotations

import logging
import math
import os
import threading
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from services.common.retrieval.bm25 import sparse_to_qdrant_indices_values, text_to_sparse

logger = logging.getLogger(__name__)

COLLECTION_NAME = "iris_chunks_v2"
EMBEDDING_DIM = 768


class ChunkStore(ABC):
    @abstractmethod
    def upsert_batch(self, chunks: List[Chunk]) -> int:
        """Persist chunks; returns the number written."""

    @abstractmethod
    def get_by_doc(self, doc_id: str, tenant_id: str) -> List[Chunk]:
        """Return all chunks for a document, enforcing tenant isolation."""

    @abstractmethod
    def search_dense(
        self,
        embedding: List[float],
        tenant_id: str,
        doc_ids: Optional[List[str]] = None,
        limit: int = 30,
    ) -> List[Tuple[str, float]]:
        """Dense cosine vector search with tenant + optional doc filters.

        Returns [(chunk_id, similarity_score), ...] sorted descending.
        """

    @abstractmethod
    def search_sparse(
        self,
        query_text: str,
        tenant_id: str,
        doc_ids: Optional[List[str]] = None,
        limit: int = 30,
    ) -> List[Tuple[str, float]]:
        """BM25 sparse vector search with tenant + optional doc filters.

        Returns [(chunk_id, bm25_score), ...] sorted descending.
        """

    @abstractmethod
    def get_by_ids(self, chunk_ids: List[str], tenant_id: str) -> List[Chunk]:
        """Return chunks by their IDs, scoped to the given tenant.

        Missing IDs and cross-tenant IDs are silently skipped.
        """

    @abstractmethod
    def get_by_doc_pages(
        self, doc_id: str, page_numbers: List[int], tenant_id: str
    ) -> List[Chunk]:
        """Return all chunks of a document on the given pages, tenant-scoped.

        Stage 3c small-to-big: /query expands top chunks to their parent
        pages with this fetch (synthesis context only — /search never uses
        it, so eval numbers keep measuring retrieval itself).
        """

    @abstractmethod
    def delete_by_doc(self, doc_id: str, tenant_id: str) -> int:
        """Delete all chunks for a document. Returns count deleted."""

    @abstractmethod
    def delete_by_session(self, session_id: str, tenant_id: str) -> int:
        """Delete all chunks for a session. Returns count deleted."""


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

    def search_dense(
        self,
        embedding: List[float],
        tenant_id: str,
        doc_ids: Optional[List[str]] = None,
        limit: int = 30,
    ) -> List[Tuple[str, float]]:
        with self._lock:
            all_chunks: List[Chunk] = []
            for chunks in self._by_doc.values():
                all_chunks.extend(chunks)
            filtered = [c for c in all_chunks if c.tenant_id == tenant_id]
            if doc_ids:
                filtered = [c for c in filtered if c.doc_id in doc_ids]
            scored: List[Tuple[Chunk, float]] = []
            for chunk in filtered:
                if chunk.embedding and len(chunk.embedding) == len(embedding):
                    dot = sum(a * b for a, b in zip(embedding, chunk.embedding))
                    scored.append((chunk, dot))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [(c.id, s) for c, s in scored[:limit]]

    def search_sparse(
        self,
        query_text: str,
        tenant_id: str,
        doc_ids: Optional[List[str]] = None,
        limit: int = 30,
    ) -> List[Tuple[str, float]]:
        q_sparse = text_to_sparse(query_text)
        if not q_sparse:
            return []

        with self._lock:
            all_chunks: List[Chunk] = []
            for chunks in self._by_doc.values():
                all_chunks.extend(chunks)
            filtered = [c for c in all_chunks if c.tenant_id == tenant_id]
            if doc_ids:
                filtered = [c for c in filtered if c.doc_id in doc_ids]

            scored: List[Tuple[Chunk, float]] = []
            for chunk in filtered:
                c_sparse = text_to_sparse(chunk.text)
                score = sum(
                    q_sparse.get(t, 0.0) * c_sparse.get(t, 0.0)
                    for t in set(q_sparse) | set(c_sparse)
                )
                if score > 0:
                    scored.append((chunk, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [(c.id, s) for c, s in scored[:limit]]

    def delete_by_doc(self, doc_id: str, tenant_id: str) -> int:
        with self._lock:
            if doc_id not in self._by_doc:
                return 0
            before = len(self._by_doc[doc_id])
            self._by_doc[doc_id] = [
                c for c in self._by_doc[doc_id] if c.tenant_id != tenant_id
            ]
            deleted = before - len(self._by_doc[doc_id])
            if not self._by_doc[doc_id]:
                del self._by_doc[doc_id]
            return deleted

    def get_by_ids(self, chunk_ids: List[str], tenant_id: str) -> List[Chunk]:
        id_set = {str(cid) for cid in chunk_ids}
        with self._lock:
            results: List[Chunk] = []
            for chunks in self._by_doc.values():
                for c in chunks:
                    if str(c.id) in id_set and c.tenant_id == tenant_id:
                        results.append(c)
            return results

    def get_by_doc_pages(
        self, doc_id: str, page_numbers: List[int], tenant_id: str
    ) -> List[Chunk]:
        pages = set(page_numbers)
        with self._lock:
            return [
                c for c in self._by_doc.get(doc_id, [])
                if c.tenant_id == tenant_id and c.page_number in pages
            ]

    def delete_by_session(self, session_id: str, tenant_id: str) -> int:
        deleted = 0
        with self._lock:
            for doc_id, chunks in list(self._by_doc.items()):
                keep = [
                    c
                    for c in chunks
                    if not (c.session_id == session_id and c.tenant_id == tenant_id)
                ]
                deleted += len(chunks) - len(keep)
                if keep:
                    self._by_doc[doc_id] = keep
                else:
                    del self._by_doc[doc_id]
        return deleted


class QdrantChunkStore(ChunkStore):
    """Phase 2.0 Qdrant store — v2 named-vector collection, hybrid search, cascading delete."""

    def __init__(
        self,
        url: str,
        collection: str = COLLECTION_NAME,
        api_key: Optional[str] = None,
    ) -> None:
        from qdrant_client import QdrantClient, models

        self._client = QdrantClient(url=url, api_key=api_key or os.getenv("QDRANT_API_KEY"))
        self._collection = collection
        try:
            self._client.get_collection(collection_name=collection)
        except Exception:
            self._client.create_collection(
                collection_name=collection,
                vectors_config={
                    "dense": models.VectorParams(
                        size=EMBEDDING_DIM,
                        distance=models.Distance.COSINE,
                        on_disk=True,
                        quantization_config=models.BinaryQuantization(
                            binary=models.BinaryQuantizationConfig(always_ram=True)
                        ),
                        hnsw_config=models.HnswConfigDiff(payload_m=16),
                    ),
                },
                sparse_vectors_config={
                    "bm25_sparse": models.SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=False),
                        modifier=models.Modifier.IDF,
                    ),
                },
            )
            for field_name in ("tenant_id", "doc_id", "session_id"):
                try:
                    self._client.create_payload_index(
                        collection_name=collection,
                        field_name=field_name,
                        field_schema=models.PayloadSchemaType.KEYWORD,
                    )
                except Exception:
                    pass
        logger.info("Ensured Qdrant collection '%s' exists", collection)

    def _tenant_doc_filter(
        self, tenant_id: str, doc_ids: Optional[List[str]]
    ) -> Optional[object]:
        from qdrant_client import models

        conditions = [
            models.FieldCondition(key="tenant_id", match=models.MatchValue(value=tenant_id)),
        ]
        if doc_ids:
            conditions.append(
                models.FieldCondition(
                    key="doc_id", match=models.MatchAny(any=doc_ids)
                )
            )
        return models.Filter(must=conditions)

    def upsert_batch(self, chunks: List[Chunk]) -> int:
        from qdrant_client import models

        if not chunks:
            return 0
        points = []
        for chunk in chunks:
            sparse = text_to_sparse(chunk.text)
            sp_indices, sp_values = sparse_to_qdrant_indices_values(sparse)
            point = models.PointStruct(
                id=chunk.id,
                vector={
                    "dense": chunk.embedding or [],
                    "bm25_sparse": models.SparseVector(
                        indices=sp_indices, values=sp_values
                    ),
                },
                payload={
                    "tenant_id": chunk.tenant_id,
                    "doc_id": chunk.doc_id,
                    "session_id": chunk.session_id,
                    "page_number": chunk.page_number,
                    "element_type": chunk.element_type.value,
                    "bbox": chunk.bbox,
                    "text": chunk.text,
                    "source": chunk.source.value,
                    "metadata": chunk.metadata,
                },
            )
            points.append(point)
        self._client.upsert(collection_name=self._collection, points=points)
        return len(points)

    @staticmethod
    def _payload_to_chunk(point_id, p: dict) -> Chunk:
        element_type_raw = p.get("element_type", "Text")
        try:
            element_type = ElementType(element_type_raw)
        except ValueError:
            element_type = ElementType.TEXT
        source_raw = p.get("source", "docling_text")
        try:
            source = RouteDecision(source_raw)
        except ValueError:
            source = RouteDecision.DOCLING_TEXT
        return Chunk(
            id=str(point_id),
            tenant_id=str(p.get("tenant_id", "")),
            doc_id=str(p.get("doc_id", "")),
            session_id=p.get("session_id"),
            page_number=int(p.get("page_number", 1)),
            element_type=element_type,
            text=str(p.get("text", "")),
            bbox=list(p.get("bbox", [])),
            source=source,
            metadata=dict(p.get("metadata") or {}),
        )

    def get_by_doc(self, doc_id: str, tenant_id: str) -> List[Chunk]:
        from qdrant_client import models

        doc_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="doc_id", match=models.MatchValue(value=doc_id)
                ),
                models.FieldCondition(
                    key="tenant_id", match=models.MatchValue(value=tenant_id)
                ),
            ]
        )

        all_hits = []
        offset = None
        while True:
            hits, next_offset = self._client.scroll(
                collection_name=self._collection,
                scroll_filter=doc_filter,
                offset=offset,
                limit=100,
                with_payload=True,
                with_vectors=False,
            )
            all_hits.extend(hits)
            if next_offset is None:
                break
            offset = next_offset

        return [self._payload_to_chunk(h.id, h.payload or {}) for h in all_hits]

    def get_by_doc_pages(
        self, doc_id: str, page_numbers: List[int], tenant_id: str
    ) -> List[Chunk]:
        from qdrant_client import models

        if not page_numbers:
            return []
        page_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="doc_id", match=models.MatchValue(value=doc_id)
                ),
                models.FieldCondition(
                    key="tenant_id", match=models.MatchValue(value=tenant_id)
                ),
                models.FieldCondition(
                    # page_number is an integer payload; MatchAny works on
                    # both keyword and integer payload types.
                    key="page_number", match=models.MatchAny(any=list(page_numbers))
                ),
            ]
        )

        all_hits = []
        offset = None
        while True:
            hits, next_offset = self._client.scroll(
                collection_name=self._collection,
                scroll_filter=page_filter,
                offset=offset,
                limit=100,
                with_payload=True,
                with_vectors=False,
            )
            all_hits.extend(hits)
            if next_offset is None:
                break
            offset = next_offset

        return [self._payload_to_chunk(h.id, h.payload or {}) for h in all_hits]

    def search_dense(
        self,
        embedding: List[float],
        tenant_id: str,
        doc_ids: Optional[List[str]] = None,
        limit: int = 30,
    ) -> List[Tuple[str, float]]:
        from qdrant_client import models

        q_filter = self._tenant_doc_filter(tenant_id, doc_ids)
        results = self._client.search(
            collection_name=self._collection,
            query_vector=models.NamedVector(name="dense", vector=embedding),
            query_filter=q_filter,
            limit=limit,
            with_payload=False,
            with_vectors=False,
        )
        return [(str(r.id), r.score) for r in results]

    def search_sparse(
        self,
        query_text: str,
        tenant_id: str,
        doc_ids: Optional[List[str]] = None,
        limit: int = 30,
    ) -> List[Tuple[str, float]]:
        from qdrant_client import models

        sparse_dict = text_to_sparse(query_text)
        if not sparse_dict:
            return []

        indices, values = sparse_to_qdrant_indices_values(sparse_dict)
        q_filter = self._tenant_doc_filter(tenant_id, doc_ids)
        results = self._client.search(
            collection_name=self._collection,
            query_vector=models.NamedSparseVector(
                name="bm25_sparse",
                vector=models.SparseVector(indices=indices, values=values),
            ),
            query_filter=q_filter,
            limit=limit,
            with_payload=False,
            with_vectors=False,
        )
        return [(str(r.id), r.score) for r in results]

    def get_by_ids(self, chunk_ids: List[str], tenant_id: str) -> List[Chunk]:
        from qdrant_client import models

        if not chunk_ids:
            return []
        results: List[Chunk] = []
        records = self._client.retrieve(
            collection_name=self._collection,
            ids=chunk_ids,
            with_payload=True,
            with_vectors=False,
        )
        for h in records:
            p = h.payload or {}
            if str(p.get("tenant_id", "")) != tenant_id:
                continue
            results.append(self._payload_to_chunk(h.id, p))
        return results

    def delete_by_doc(self, doc_id: str, tenant_id: str) -> int:
        from qdrant_client import models

        try:
            result = self._client.delete(
                collection_name=self._collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="doc_id", match=models.MatchValue(value=doc_id)
                            ),
                            models.FieldCondition(
                                key="tenant_id", match=models.MatchValue(value=tenant_id)
                            ),
                        ]
                    )
                ),
                wait=True,
            )
            return getattr(result, "points_count", 0) or 0
        except Exception:
            return 0

    def delete_by_session(self, session_id: str, tenant_id: str) -> int:
        from qdrant_client import models

        if not session_id:
            return 0
        try:
            result = self._client.delete(
                collection_name=self._collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="session_id",
                                match=models.MatchValue(value=session_id),
                            ),
                            models.FieldCondition(
                                key="tenant_id", match=models.MatchValue(value=tenant_id)
                            ),
                        ]
                    )
                ),
                wait=True,
            )
            return getattr(result, "points_count", 0) or 0
        except Exception:
            return 0


def get_chunk_store() -> ChunkStore:
    """Factory: QdrantChunkStore when QDRANT_URL is set, else MemoryChunkStore."""
    url = os.getenv("QDRANT_URL", "").strip()
    collection = os.getenv("RETRIEVAL_COLLECTION", COLLECTION_NAME).strip()
    if url:
        return QdrantChunkStore(url=url, collection=collection)
    logger.info("QDRANT_URL unset; using MemoryChunkStore (dev/test mode)")
    return MemoryChunkStore()
