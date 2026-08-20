"""IRIS — Retrieval API (Cloud Run).

Phase 2.0: FastAPI service with /search (Standard + Deep), cascading delete
endpoints, and tenant isolation via header.

Phase 4.0: tenant isolation is enforced from a verified Firebase JWT at the
engine layer. Every user-facing route requires `require_auth` (per-route, not
global). `tenant_id` comes ONLY from AuthContext — client-supplied headers,
paths, or bodies are ignored. Pub/Sub machine endpoints are NOT on this
service.

Cascading delete removes from Qdrant immediately. GCS + Firestore cleanup
is attempted but failures are logged rather than failing the request — those
stores have their own lifecycle policies as a safety net.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException

from services.common.auth.jwt import AuthContext, require_auth
from services.common.auth.rate_limit import limiter
from services.common.auth.validation import (
    validate_doc_id,
    validate_history,
    validate_session_id,
    validate_tenant_id,
    validate_top_k,
)
from services.common.ingestion.store import get_chunk_store
from services.common.models.factory import get_model_provider
from services.common.retrieval.models import (
    DeleteResponse,
    DocStatusResponse,
    QueryRequest,
    QueryResponse,
    ScoredChunk,
    SearchRequest,
    SearchResponse,
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
    ViewUrlResponse,
)
from services.common.retrieval.search import SearchOrchestrator
from services.common.retrieval.synthesis import validate_citations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("retrieval-api")

_RAW_BUCKET = "iris-raw-pdfs"
_VIEW_URL_TTL_SECONDS = 900


def _get_gcs_client():
    """Lazy-initialize GCS client."""
    from google.cloud import storage

    return storage.Client()


def _get_firestore_client():
    """Lazy-initialize Firestore client."""
    from google.cloud import firestore

    return firestore.Client()


def _server_timestamp():
    from google.cloud.firestore import SERVER_TIMESTAMP

    return SERVER_TIMESTAMP


def _delete_gcs_blob(tenant_id: str, doc_id: str) -> None:
    gcs = _get_gcs_client()
    if gcs is None:
        logger.warning("GCS client unavailable; skipping blob delete: %s/%s", tenant_id, doc_id)
        return
    try:
        bucket = gcs.bucket(_RAW_BUCKET)
        blob = bucket.blob(f"{tenant_id}/{doc_id}.pdf")
        blob.delete()
    except Exception as exc:
        logger.warning("GCS delete failed for %s/%s: %s", tenant_id, doc_id, exc)


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


def _remove_doc_from_sessions(tenant_id: str, doc_id: str) -> None:
    """FR-5.4: purge doc_id from every session's document_ids array."""
    client = _get_firestore_client()
    if client is None:
        logger.warning("Firestore client unavailable; skipping session purge for %s", doc_id)
        return
    try:
        sessions = client.collection(f"tenants/{tenant_id}/sessions").stream()
        for session in sessions:
            data = session.to_dict() or {}
            doc_ids = list(data.get("document_ids") or [])
            if doc_id in doc_ids:
                doc_ids.remove(doc_id)
                session.reference.update({"document_ids": doc_ids})
    except Exception as exc:
        logger.warning("Session doc purge failed for %s: %s", doc_id, exc)


def _signed_view_url(tenant_id: str, doc_id: str) -> str:
    """Return a 15-minute V4 signed GET URL for {tenant}/{doc}.pdf.

    Uses the IAMCredentials signer when running on Cloud Run (compute-engine
    credentials have no private key; the SA self-binds
    roles/iam.serviceAccountTokenCreator to sign via the IAM API).
    """
    gcs = _get_gcs_client()
    if gcs is None:
        raise HTTPException(status_code=503, detail="Storage unavailable")
    bucket = gcs.bucket(_RAW_BUCKET)
    blob = bucket.blob(f"{tenant_id}/{doc_id}.pdf")
    credentials = _signing_credentials()
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(seconds=_VIEW_URL_TTL_SECONDS),
        method="GET",
        credentials=credentials,
    )


def _signing_credentials():
    """Return credentials that can sign V4 URLs.

    On Cloud Run the metadata credentials have no private key; build a
    Signing credential backed by the IAM signBlob API (the retrieval-api SA
    self-binds roles/iam.serviceAccountTokenCreator). Locally, default ADC
    (a service-account key) already signs directly.
    """
    from google.auth import compute_engine, default
    from google.auth.transport import requests as gauth_requests
    from google.oauth2 import service_account
    from google.auth import iam

    credentials, _ = default()
    if isinstance(credentials, compute_engine.Credentials):
        try:
            request = gauth_requests.Request()
            credentials.refresh(request)
            signer = iam.Signer(
                request,
                credentials,
                credentials.service_account_email,
            )
            return service_account.Credentials(
                signer=signer,
                service_account_email=credentials.service_account_email,
                token_uri="https://oauth2.googleapis.com/token",
                scopes=credentials.scopes,
            )
        except Exception as exc:  # noqa: BLE001 — fall through to default signing
            logger.warning("IAM signer unavailable (%s); using raw credentials", exc)
    return credentials


def _document_exists(tenant_id: str, doc_id: str) -> bool:
    """Ownership pre-check before signing a GCS URL (prevents arbitrary signing)."""
    client = _get_firestore_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Firestore unavailable")
    snapshot = client.document(f"tenants/{tenant_id}/documents/{doc_id}").get()
    if not snapshot.exists:
        raise HTTPException(status_code=404, detail="Document not found")


# --- App --------------------------------------------------------------------------
PORT = int(os.environ.get("PORT", 8080))
app = FastAPI(title="IRIS Retrieval API", version="4.0")

store = get_chunk_store()
provider = get_model_provider()
orchestrator = SearchOrchestrator(store=store, provider=provider)


@app.get("/livez")
async def livez():
    collection = os.environ.get("RETRIEVAL_COLLECTION", "iris_chunks_v2")
    store_url = os.environ.get("QDRANT_URL", "memory").split(":")[0]
    return {
        "status": "ok",
        "service": "retrieval-api",
        "phase": "4.0",
        "store": f"{type(store).__name__}@{store_url}",
        "collection": collection,
    }


@app.get("/doc-status/{doc_id}", response_model=DocStatusResponse)
async def doc_status(
    doc_id: str,
    auth: AuthContext = Depends(require_auth),
):
    """Return Qdrant chunk count for a document without touching ingestion-worker."""
    validate_tenant_id(auth.tenant_id)
    validate_doc_id(doc_id)
    chunks = store.get_by_doc(doc_id, tenant_id=auth.tenant_id)
    return {
        "doc_id": doc_id,
        "tenant_id": auth.tenant_id,
        "chunks": len(chunks),
        "pages": len({c.page_number for c in chunks}),
    }


@app.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    auth: AuthContext = Depends(require_auth),
):
    validate_tenant_id(auth.tenant_id)
    limiter.check(f"tenant:{auth.tenant_id}")
    top_k = validate_top_k(request.top_k, for_synthesis=False)
    history = validate_history(request.history)
    try:
        t0 = time.perf_counter()
        if request.mode == "deep":
            results = await orchestrator.deep_search(
                query=request.query,
                tenant_id=auth.tenant_id,
                history=history,
                doc_ids=request.doc_ids,
                top_k=top_k,
            )
        else:
            results = await orchestrator.standard_search(
                query=request.query,
                tenant_id=auth.tenant_id,
                doc_ids=request.doc_ids,
                top_k=top_k,
            )
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return SearchResponse(
            results=results,
            mode=request.mode,
            latency_ms=latency,
        )
    except Exception as exc:
        logger.exception("Search failed for tenant %s", auth.tenant_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Retrieve -> synthesize -> grounded structured answer."""
    validate_tenant_id(auth.tenant_id)
    if request.session_id:
        validate_session_id(request.session_id)
    limiter.check(f"tenant:{auth.tenant_id}")
    top_k = validate_top_k(request.top_k, for_synthesis=True)
    history = validate_history(request.history)
    try:
        t0 = time.perf_counter()
        if request.mode == "deep":
            retrieved = await orchestrator.deep_search(
                query=request.query,
                tenant_id=auth.tenant_id,
                history=history,
                doc_ids=request.doc_ids,
                top_k=top_k,
            )
        else:
            retrieved = await orchestrator.standard_search(
                query=request.query,
                tenant_id=auth.tenant_id,
                doc_ids=request.doc_ids,
                top_k=top_k,
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
        logger.exception("Query failed for tenant %s", auth.tenant_id)
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


@app.delete("/documents/{doc_id}", response_model=DeleteResponse)
async def delete_document(
    doc_id: str,
    auth: AuthContext = Depends(require_auth),
):
    validate_tenant_id(auth.tenant_id)
    validate_doc_id(doc_id)
    deleted = store.delete_by_doc(doc_id, auth.tenant_id)
    _delete_gcs_blob(auth.tenant_id, doc_id)
    _delete_firestore_doc(f"tenants/{auth.tenant_id}/documents/{doc_id}")
    _remove_doc_from_sessions(auth.tenant_id, doc_id)
    return DeleteResponse(deleted_chunks=deleted, resource_id=doc_id)


@app.delete("/sessions/{session_id}", response_model=DeleteResponse)
async def delete_session(
    session_id: str,
    auth: AuthContext = Depends(require_auth),
):
    validate_tenant_id(auth.tenant_id)
    validate_session_id(session_id)
    deleted = store.delete_by_session(session_id, auth.tenant_id)
    _delete_firestore_session(auth.tenant_id, session_id)
    return DeleteResponse(deleted_chunks=deleted, resource_id=session_id)


@app.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Create a named workspace session scoped to the verified tenant."""
    validate_tenant_id(auth.tenant_id)
    session_id = str(uuid.uuid4())
    document_ids = [validate_doc_id(d) for d in (request.document_ids or [])]
    doc_path = f"tenants/{auth.tenant_id}/sessions/{session_id}"
    client = _get_firestore_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Firestore unavailable")
    client.document(doc_path).set({
        "session_id": session_id,
        "tenant_id": auth.tenant_id,
        "name": request.name or "",
        "document_ids": document_ids,
        "created_at": _server_timestamp(),
    })
    return SessionResponse(session_id=session_id, tenant_id=auth.tenant_id, name=request.name)


@app.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    auth: AuthContext = Depends(require_auth),
):
    """List session documents for the verified tenant only."""
    validate_tenant_id(auth.tenant_id)
    client = _get_firestore_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Firestore unavailable")
    sessions = []
    for doc in client.collection(f"tenants/{auth.tenant_id}/sessions").stream():
        data = doc.to_dict() or {}
        sessions.append({
            "session_id": data.get("session_id") or doc.id,
            "name": data.get("name", ""),
            "document_ids": data.get("document_ids", []),
            "created_at": data.get("created_at"),
        })
    return SessionListResponse(sessions=sessions)


@app.get("/documents/{doc_id}/view-url", response_model=ViewUrlResponse)
async def view_url(
    doc_id: str,
    auth: AuthContext = Depends(require_auth),
):
    """Return a short-lived signed GCS URL for PDF rendering (15-min TTL)."""
    validate_tenant_id(auth.tenant_id)
    validate_doc_id(doc_id)
    _document_exists(auth.tenant_id, doc_id)
    url = _signed_view_url(auth.tenant_id, doc_id)
    return ViewUrlResponse(url=url, expires_in_seconds=_VIEW_URL_TTL_SECONDS)
