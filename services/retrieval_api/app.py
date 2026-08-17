"""IRIS — Retrieval API (Cloud Run).

Phase 2.0: FastAPI service with /search (Standard + Deep), cascading delete
endpoints, and tenant isolation via header.

Cascading delete removes from Qdrant immediately. GCS + Firestore cleanup
is attempted but failures are logged rather than failing the request — those
stores have their own lifecycle policies as a safety net.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time

from fastapi import FastAPI, Header, HTTPException

from services.common.ingestion.store import get_chunk_store
from services.common.models.factory import get_model_provider
from services.common.retrieval.models import (
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    ScoredChunk,
    SearchRequest,
    SearchResponse,
)
from services.common.retrieval.search import SearchOrchestrator
from services.common.retrieval.synthesis import validate_citations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("retrieval-api")

_RAW_BUCKET = "iris-raw-pdfs"


def _get_gcs_client():
    """Lazy-initialize GCS client."""
    from google.cloud import storage

    return storage.Client()


def _get_firestore_client():
    """Lazy-initialize Firestore client."""
    from google.cloud import firestore

    return firestore.Client()


def _delete_gcs_blob(blob_path: str) -> None:
    gcs = _get_gcs_client()
    if gcs is None:
        logger.warning("GCS client unavailable; skipping blob delete: %s", blob_path)
        return
    try:
        bucket = gcs.bucket(_RAW_BUCKET)
        blob = bucket.blob(blob_path)
        blob.delete()
    except Exception as exc:
        logger.warning("GCS delete failed for %s: %s", blob_path, exc)


def _delete_firestore_doc(doc_path: str) -> None:
    client = _get_firestore_client()
    if client is None:
        logger.warning("Firestore client unavailable; skipping delete: %s", doc_path)
        return
    try:
        client.document(doc_path).delete()
    except Exception as exc:
        logger.warning("Firestore delete failed for %s: %s", doc_path, exc)


def _delete_firestore_session(tenant_id: str, session_id: str) -> None:
    _delete_firestore_doc(f"tenants/{tenant_id}/sessions/{session_id}")
    client = _get_firestore_client()
    if client is not None:
        try:
            messages = client.collection(
                f"tenants/{tenant_id}/sessions/{session_id}/messages"
            ).stream()
            for msg in messages:
                msg.reference.delete()
        except Exception as exc:
            logger.warning("Firestore messages delete failed: %s", exc)


# --- App --------------------------------------------------------------------------
PORT = int(os.environ.get("PORT", 8080))
app = FastAPI(title="IRIS Retrieval API", version="2.0")

store = get_chunk_store()
provider = get_model_provider()
orchestrator = SearchOrchestrator(store=store, provider=provider)


@app.get("/healthz")
async def healthz():
    collection = os.environ.get("RETRIEVAL_COLLECTION", "iris_chunks_v2")
    store_url = os.environ.get("QDRANT_URL", "memory").split(":")[0]
    return {
        "status": "ok",
        "service": "retrieval-api",
        "phase": "2.0",
        "store": f"{type(store).__name__}@{store_url}",
        "collection": collection,
    }


@app.get("/doc-status/{doc_id}")
async def doc_status(doc_id: str, tenant_id: str = Header(...)):
    """Return Qdrant chunk count for a document without touching ingestion-worker."""
    chunks = store.get_by_doc(doc_id, tenant_id=tenant_id)
    return {
        "doc_id": doc_id,
        "tenant_id": tenant_id,
        "chunks": len(chunks),
        "pages": len({c.page_number for c in chunks}),
    }


@app.post("/search")
async def search(request: SearchRequest, tenant_id: str = Header(...)):
    if not tenant_id.strip():
        raise HTTPException(status_code=400, detail="Missing tenant_id header")
    try:
        t0 = time.perf_counter()
        if request.mode == "deep":
            results = await orchestrator.deep_search(
                query=request.query,
                tenant_id=tenant_id,
                history=request.history,
                doc_ids=request.doc_ids,
                top_k=request.top_k,
            )
        else:
            results = await orchestrator.standard_search(
                query=request.query,
                tenant_id=tenant_id,
                doc_ids=request.doc_ids,
                top_k=request.top_k,
            )
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return SearchResponse(
            results=results,
            mode=request.mode,
            latency_ms=latency,
        )
    except Exception as exc:
        logger.exception("Search failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/query")
async def query(request: QueryRequest, tenant_id: str = Header(...)):
    """Retrieve -> synthesize -> grounded structured answer."""
    if not tenant_id.strip():
        raise HTTPException(status_code=400, detail="Missing tenant_id header")
    try:
        t0 = time.perf_counter()
        if request.mode == "deep":
            retrieved = await orchestrator.deep_search(
                query=request.query,
                tenant_id=tenant_id,
                history=request.history,
                doc_ids=request.doc_ids,
                top_k=request.top_k,
            )
        else:
            retrieved = await orchestrator.standard_search(
                query=request.query,
                tenant_id=tenant_id,
                doc_ids=request.doc_ids,
                top_k=request.top_k,
            )

        context, source_chunks = _build_synthesis_context(retrieved)
        answer = await asyncio.to_thread(
            provider.synthesize, context, request.query, source_chunks
        )
        answer = validate_citations(answer, retrieved)
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return QueryResponse(
            answer=answer.answer,
            citations=answer.citations,
            mode=request.mode,
            latency_ms=latency,
            chunks_used=len(retrieved),
        )
    except Exception as exc:
        logger.exception("Query failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail=str(exc))


def _build_synthesis_context(
    retrieved: list[ScoredChunk],
) -> tuple[str, list[dict]]:
    """Build the [CHUNK i] context and the source_chunks list for grounding."""
    source_chunks: list[dict] = []
    parts: list[str] = []
    for i, chunk in enumerate(retrieved):
        parts.append(
            f"[CHUNK {i}] doc_id={chunk.doc_id} page={chunk.page_number}\n"
            f"{chunk.text}"
        )
        source_chunks.append({
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "page_number": chunk.page_number,
            "bbox": list(chunk.bbox),
            "text": chunk.text,
        })
    return "\n\n".join(parts), source_chunks


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, tenant_id: str = Header(...)):
    if not tenant_id.strip() or not doc_id.strip():
        raise HTTPException(status_code=400, detail="Missing tenant_id header or doc_id")
    deleted = store.delete_by_doc(doc_id, tenant_id)
    _delete_gcs_blob(f"{tenant_id}/{doc_id}.pdf")
    _delete_firestore_doc(f"tenants/{tenant_id}/documents/{doc_id}")
    return DeleteResponse(deleted_chunks=deleted, resource_id=doc_id)


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, tenant_id: str = Header(...)):
    if not tenant_id.strip() or not session_id.strip():
        raise HTTPException(status_code=400, detail="Missing tenant_id header or session_id")
    deleted = store.delete_by_session(session_id, tenant_id)
    _delete_firestore_session(tenant_id, session_id)
    return DeleteResponse(deleted_chunks=deleted, resource_id=session_id)
