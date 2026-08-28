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
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from services.common.auth.jwt import AuthContext, require_auth
from services.common.auth.rate_limit import limiter
from services.common.auth.validation import (
    MAX_HISTORY_TURNS,
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
    DocumentInfo,
    DocumentListResponse,
    QueryRequest,
    QueryResponse,
    ScoredChunk,
    SearchRequest,
    SearchResponse,
    SessionCreateRequest,
    SessionListResponse,
    SessionMessagesResponse,
    SessionResponse,
    UploadResponse,
    ViewUrlResponse,
)
from services.common.retrieval.search import SearchOrchestrator
from services.common.retrieval.synthesis import validate_citations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("retrieval-api")

_RAW_BUCKET = "iris-raw-pdfs"
_VIEW_URL_TTL_SECONDS = 900

# Upload guards (Task 5.0b): size cap before any GCS write; page cap enforced
# downstream by the ingestion-worker preflight. 50 MB is generous for scanned
# legal PDFs and far below Cloud Run request limits.
_UPLOAD_MAX_BYTES = 50 * 1024 * 1024

# Ingestion trigger (Task 5.0b): the ingestion-worker /ingest endpoint performs
# preflight + page split + Pub/Sub fan-out. It's secured by Cloud Run IAM, so we
# impersonate its service account to mint an ID token (same pattern as
# scripts/eval_phase2.py). Env overridable for local/emulator tests.
_INGEST_URL = os.environ.get("INGEST_URL", "")
_INGEST_SA = os.environ.get("INGEST_SA", "ingestion-worker-sa@naturepivot-rag.iam.gserviceaccount.com")
_GCP_PROJECT = os.environ.get("GCP_PROJECT", "naturepivot-rag")


def _env_rerank_blend() -> Optional[float]:
    """RERANK_BLEND env as a 0..1 float, or None (reranking off) when unset.

    Read per-request so tests can monkeypatch the env and deploys can change
    the value without a code change.
    """
    raw = os.environ.get("RERANK_BLEND", "").strip()
    if not raw:
        return None
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        logger.warning("Invalid RERANK_BLEND %r ignored; reranking stays off", raw)
        return None


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


def _create_firestore_session(tenant_id: str) -> str:
    """Create an empty session document and return the new session_id."""
    session_id = str(uuid.uuid4())
    client = _get_firestore_client()
    if client is None:
        logger.warning("Firestore unavailable; session not created")
        return session_id
    try:
        client.document(f"tenants/{tenant_id}/sessions/{session_id}").set({
            "session_id": session_id,
            "tenant_id": tenant_id,
            "name": "",
            "document_ids": [],
            "created_at": _server_timestamp(),
        })
    except Exception as exc:
        logger.warning("Firestore session create failed: %s", exc)
    return session_id


def _append_firestore_messages(
    tenant_id: str, session_id: str, messages: list[dict]
) -> None:
    """Write user + assistant messages to the session's messages sub-collection."""
    client = _get_firestore_client()
    if client is None:
        return
    path = f"tenants/{tenant_id}/sessions/{session_id}/messages"
    try:
        col = client.collection(path)
        for msg in messages:
            col.add({
                "role": msg["role"],
                "content": msg["content"],
                "created_at": _server_timestamp(),
            })
    except Exception as exc:
        logger.warning("Firestore messages append failed: %s", exc)


def _load_firestore_messages(
    tenant_id: str, session_id: str, limit: int = 6
) -> list[dict]:
    """Load the last N messages from Firestore, returned in chronological order."""
    client = _get_firestore_client()
    if client is None:
        return []
    path = f"tenants/{tenant_id}/sessions/{session_id}/messages"
    try:
        docs = list(
            client.collection(path)
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        docs.reverse()  # newest-first → chronological (oldest-first)
        return [{"role": d.get("role", ""), "content": d.get("content", "")} for d in docs]
    except Exception as exc:
        logger.warning("Firestore messages load failed: %s", exc)
        return []


def _session_exists(tenant_id: str, session_id: str) -> bool:
    """Check if a session document belongs to this tenant."""
    client = _get_firestore_client()
    if client is None:
        return True  # if Firestore is down, don't block the request
    try:
        doc = client.document(f"tenants/{tenant_id}/sessions/{session_id}").get()
        return doc.exists
    except Exception:
        return True


def _delete_firestore_session(tenant_id: str, session_id: str) -> None:
    _delete_firestore_doc(f"tenants/{tenant_id}/sessions/{session_id}")
    client = _get_firestore_client()
    if client is not None:
        try:
            messages = client.collection(
                f"tenants/{tenant_id}/sessions/{session_id}/messages"
            ).get()
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
        sessions = client.collection(f"tenants/{tenant_id}/sessions").get()
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


def _upload_pdf_to_gcs(tenant_id: str, doc_id: str, content: bytes) -> None:
    """Stream the uploaded PDF to gs://iris-raw-pdfs/{tenant}/{doc_id}.pdf."""
    gcs = _get_gcs_client()
    if gcs is None:
        raise HTTPException(status_code=503, detail="Storage unavailable")
    bucket = gcs.bucket(_RAW_BUCKET)
    blob = bucket.blob(f"{tenant_id}/{doc_id}.pdf")
    blob.upload_from_string(content, content_type="application/pdf")


def _create_document_record(tenant_id: str, doc_id: str, filename: str) -> None:
    """Create the Firestore ownership record so view-url/delete work.

    The record also carries processing state so the frontend documents table
    can display it without a separate store.
    """
    client = _get_firestore_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Firestore unavailable")
    client.document(f"tenants/{tenant_id}/documents/{doc_id}").set({
        "doc_id": doc_id,
        "tenant_id": tenant_id,
        "status": "processing",
        "filename": filename,
        "created_at": _server_timestamp(),
    })


def _trigger_ingestion(tenant_id: str, doc_id: str) -> dict:
    """Call ingestion-worker /ingest to preflight + split + fan out to Pub/Sub.

    Returns the worker's response JSON. On failure raises HTTPException so the
    upload can report a clear error (the raw PDF is already in GCS; a retry of
    the upload with the same doc_id must be handled, so this does NOT delete).
    """
    if not _INGEST_URL:
        raise HTTPException(status_code=503, detail="Ingestion service not configured")

    import requests
    from google.auth import default
    from google.auth.transport import requests as gauth_requests

    # Mint an ID token as the ingestion-worker SA (Cloud Run IAM) via the
    # IAM Credentials generateIdToken API — impersonated_credentials only
    # yields access tokens, not ID tokens.
    creds, _ = default()
    auth_req = gauth_requests.Request()
    creds.refresh(auth_req)
    token_endpoint = (
        "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
        f"{_INGEST_SA}:generateIdToken"
    )
    resp = requests.post(
        token_endpoint,
        headers={"Authorization": f"Bearer {creds.token}"},
        json={"audience": _INGEST_URL, "includeEmail": True},
        timeout=30,
    )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Ingestion auth failed (HTTP {resp.status_code})",
        )
    id_token = resp.json()["token"]

    resp = requests.post(
        f"{_INGEST_URL}/ingest",
        json={"gcs_uri": f"gs://{_RAW_BUCKET}/{tenant_id}/{doc_id}.pdf", "tenant_id": tenant_id, "doc_id": doc_id},
        headers={"Authorization": f"Bearer {id_token}"},
        timeout=120,
    )
    try:
        return resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail=f"Ingestion trigger failed (HTTP {resp.status_code})") from None


# --- App --------------------------------------------------------------------------
PORT = int(os.environ.get("PORT", 8080))
app = FastAPI(title="IRIS Retrieval API", version="4.0")


def _cors_origins() -> list[str]:
    """Comma-separated browser origins from CORS_ALLOWED_ORIGINS (trimmed)."""
    return [
        o.strip()
        for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    ]


def add_cors_middleware(application: FastAPI) -> None:
    """Register CORSMiddleware for the configured browser origins.

    No-op when CORS_ALLOWED_ORIGINS is unset/empty. allow_headers="*" covers
    the custom X-Firebase-Token header in the preflight OPTIONS.
    """
    origins = _cors_origins()
    if origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )


add_cors_middleware(app)

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


def _get_doc_total_pages(client, tenant_id: str, doc_id: str) -> Optional[int]:
    """Retrieve total_pages from document record or progress tracker."""
    if client is None:
        return None
    try:
        doc_snap = client.document(f"tenants/{tenant_id}/documents/{doc_id}").get()
        if doc_snap.exists:
            data = doc_snap.to_dict() or {}
            if "total_pages" in data and data["total_pages"]:
                return int(data["total_pages"])
        tracker_snap = client.document(f"tenants/{tenant_id}/documents/{doc_id}/progress/tracker").get()
        if tracker_snap.exists:
            tdata = tracker_snap.to_dict() or {}
            if "total_pages" in tdata and tdata["total_pages"]:
                return int(tdata["total_pages"])
    except Exception as exc:
        logger.debug("Failed reading total_pages for %s/%s: %s", tenant_id, doc_id, exc)
    return None


@app.get("/doc-status/{doc_id}", response_model=DocStatusResponse)
async def doc_status(
    doc_id: str,
    auth: AuthContext = Depends(require_auth),
):
    """Return Qdrant chunk count and processing status for a document."""
    validate_tenant_id(auth.tenant_id)
    validate_doc_id(doc_id)
    client = _get_firestore_client()
    total_pages = _get_doc_total_pages(client, auth.tenant_id, doc_id) if client else None
    chunks = store.get_by_doc(doc_id, tenant_id=auth.tenant_id)
    page_count = len({c.page_number for c in chunks})
    if total_pages and total_pages > 0:
        status = "completed" if page_count >= total_pages else "processing"
    else:
        status = "completed" if len(chunks) > 0 else "processing"

    return {
        "doc_id": doc_id,
        "tenant_id": auth.tenant_id,
        "chunks": len(chunks),
        "pages": page_count,
        "total_pages": total_pages,
        "status": status,
    }


@app.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    auth: AuthContext = Depends(require_auth),
):
    """List all documents for the verified tenant with chunk/page counts and accurate status."""
    validate_tenant_id(auth.tenant_id)
    client = _get_firestore_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Firestore unavailable")
    documents = []
    try:
        docs = client.collection(f"tenants/{auth.tenant_id}/documents").get()
        for doc in docs:
            doc_id = doc.id
            data = doc.to_dict() or {}
            total_pages = data.get("total_pages")
            if total_pages is None:
                total_pages = _get_doc_total_pages(client, auth.tenant_id, doc_id)
            chunks = store.get_by_doc(doc_id, tenant_id=auth.tenant_id)
            page_count = len({c.page_number for c in chunks})
            if total_pages and total_pages > 0:
                status = "completed" if page_count >= total_pages else "processing"
            else:
                status = "completed" if len(chunks) > 0 else "processing"

            documents.append(DocumentInfo(
                doc_id=doc_id,
                chunk_count=len(chunks),
                page_count=page_count,
                total_pages=total_pages,
                status=status,
            ))
    except Exception as exc:
        logger.warning("Firestore collection listing failed for %s: %s", auth.tenant_id, exc)
    return DocumentListResponse(documents=documents)


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
                rerank_blend=request.rerank_blend,
                history=history,
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
        if not await asyncio.to_thread(_session_exists, auth.tenant_id, request.session_id):
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        request.session_id = await asyncio.to_thread(
            _create_firestore_session, auth.tenant_id
        )
    limiter.check(f"tenant:{auth.tenant_id}")
    top_k = validate_top_k(request.top_k, for_synthesis=True)
    history = validate_history(request.history)
    if request.session_id:
        server_history = await asyncio.to_thread(
            _load_firestore_messages, auth.tenant_id, request.session_id, MAX_HISTORY_TURNS
        )
        if server_history:
            history = server_history
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
            # RERANK_BLEND (Phase 12.1): server-side default rerank weight for
            # production answers — /query has no request-level blend param, so
            # the env picked by the eval sweep applies automatically. Unset/0
            # keeps the hybrid-only ranking.
            retrieved = await orchestrator.standard_search(
                query=request.query,
                tenant_id=auth.tenant_id,
                doc_ids=request.doc_ids,
                top_k=top_k,
                rerank_blend=_env_rerank_blend(),
                history=history,
            )

        expanded = await asyncio.to_thread(
            _expand_to_parent_pages, retrieved, auth.tenant_id
        )
        context, source_chunks = _build_synthesis_context(expanded)
        answer = await asyncio.to_thread(
            provider.synthesize, context, request.query, source_chunks
        )
        answer = validate_citations(answer, expanded)
        if request.session_id:
            await asyncio.to_thread(
                _append_firestore_messages, auth.tenant_id, request.session_id,
                [
                    {"role": "user", "content": request.query},
                    {"role": "assistant", "content": answer.answer},
                ],
            )
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return QueryResponse(
            answer=answer.answer,
            citations=answer.citations,
            mode=request.mode,
            latency_ms=latency,
            chunks_used=len(retrieved),
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.exception("Query failed for tenant %s", auth.tenant_id)
        raise HTTPException(status_code=500, detail=str(exc))


def _expand_to_parent_pages(
    retrieved: list[ScoredChunk], tenant_id: str
) -> list[ScoredChunk]:
    """Small-to-big (Stage 3c): append bbox-proximate siblings of the top chunks.

    Instead of feeding ALL chunks on a page (which dilutes synthesis with noise),
    only include chunks whose vertical bbox overlaps with the ranked chunk's
    bbox ± a proximity window. This keeps paragraph context without pulling
    unrelated sections from the same page.
    """
    PROXIMITY_WINDOW = 0.10  # 10% of page height in normalized coords

    ranked_bboxes: list[tuple[str, int, list[float]]] = []
    for c in retrieved:
        if len(c.bbox) == 4:
            ranked_bboxes.append((c.doc_id, c.page_number, c.bbox))

    pages_by_doc: dict[str, set[int]] = {}
    for doc_id, page_num, _ in ranked_bboxes:
        pages_by_doc.setdefault(doc_id, set()).add(page_num)

    seen = {c.chunk_id for c in retrieved}
    expanded = list(retrieved)

    for doc_id in sorted(pages_by_doc):
        pages = sorted(pages_by_doc[doc_id])
        # Collect ranked bboxes for this doc to compute proximity
        doc_ranked = [
            (pg, bb) for did, pg, bb in ranked_bboxes if did == doc_id
        ]

        for ch in store.get_by_doc_pages(doc_id, pages, tenant_id):
            if ch.id in seen:
                continue
            # Include if any ranked chunk's bbox is vertically proximate
            if len(ch.bbox) == 4 and doc_ranked:
                chunk_top = ch.bbox[1]
                chunk_bottom = ch.bbox[3]
                is_proximate = False
                for ranked_page, ranked_bb in doc_ranked:
                    if ranked_page != ch.page_number:
                        continue
                    ranked_top = ranked_bb[1]
                    ranked_bottom = ranked_bb[3]
                    # Check vertical overlap with proximity window
                    if not (chunk_bottom + PROXIMITY_WINDOW < ranked_top or
                            chunk_top - PROXIMITY_WINDOW > ranked_bottom):
                        is_proximate = True
                        break
                if not is_proximate:
                    continue

            seen.add(ch.id)
            expanded.append(
                ScoredChunk(
                    chunk_id=ch.id,
                    doc_id=ch.doc_id,
                    tenant_id=ch.tenant_id,
                    session_id=ch.session_id,
                    text=ch.text,
                    bbox=list(ch.bbox),
                    page_number=ch.page_number,
                    element_type=ch.element_type.value,
                    source=ch.source.value,
                    score=0.0,
                    metadata=dict(ch.metadata or {}),
                )
            )
    return expanded


def _build_synthesis_context(
    retrieved: list[ScoredChunk],
) -> tuple[str, list[dict]]:
    """Build the source-chunk context and the source_chunks list for grounding.

    Sources are labeled with simple integer refs [1], [2], ... (Phase 9.0-D) so
    the model cites via short, stable markers that map 1:1 back to chunk_ids in
    `source_chunks` (position i -> source_chunks[i]).
    """
    source_chunks: list[dict] = []
    parts: list[str] = []
    for i, chunk in enumerate(retrieved, start=1):
        parts.append(
            f"Source [{i}]: doc_id={chunk.doc_id} page={chunk.page_number}\n"
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


@app.delete("/documents", response_model=DeleteResponse)
async def delete_all_documents(
    auth: AuthContext = Depends(require_auth),
):
    """Cascade-delete ALL documents for the tenant.

    Wipes Qdrant chunks, GCS blobs, and Firestore ownership records.
    Use with caution — this is irreversible.
    """
    validate_tenant_id(auth.tenant_id)

    # 1. List all doc_ids from Firestore before deleting
    client = _get_firestore_client()
    doc_ids = []
    if client:
        try:
            docs = client.collection(f"tenants/{auth.tenant_id}/documents").get()
            doc_ids = [d.id for d in docs]
        except Exception as exc:
            logger.warning("Failed to list docs for bulk delete: %s", exc)

    # 2. Delete all Qdrant chunks for this tenant at once
    deleted = store.delete_all_by_tenant(auth.tenant_id)

    # 3. Delete GCS blobs and Firestore records for each doc
    for doc_id in doc_ids:
        _delete_gcs_blob(auth.tenant_id, doc_id)
        _delete_firestore_doc(f"tenants/{auth.tenant_id}/documents/{doc_id}")

    logger.info("Bulk delete tenant=%s docs=%d chunks=%d", auth.tenant_id, len(doc_ids), deleted)
    return DeleteResponse(deleted_chunks=deleted, resource_id=auth.tenant_id)


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
    try:
        docs = client.collection(f"tenants/{auth.tenant_id}/sessions").get()
        for doc in docs:
            data = doc.to_dict() or {}
            sessions.append({
                "session_id": data.get("session_id") or doc.id,
                "name": data.get("name", ""),
                "document_ids": data.get("document_ids", []),
                "created_at": data.get("created_at"),
            })
    except Exception as exc:
        logger.warning("Firestore session listing failed for %s: %s", auth.tenant_id, exc)
    return SessionListResponse(sessions=sessions)


@app.get("/sessions/{session_id}/messages", response_model=SessionMessagesResponse)
async def get_session_messages(
    session_id: str,
    auth: AuthContext = Depends(require_auth),
):
    """Return chat history for a session, in chronological order."""
    validate_tenant_id(auth.tenant_id)
    validate_session_id(session_id)
    if not await asyncio.to_thread(_session_exists, auth.tenant_id, session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await asyncio.to_thread(
        _load_firestore_messages, auth.tenant_id, session_id, limit=100
    )
    return SessionMessagesResponse(messages=messages)


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


@app.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile,
    doc_id: str = Form(...),
    auth: AuthContext = Depends(require_auth),
):
    """Upload a PDF and trigger ingestion (Task 5.0b).

    Flow: validate doc_id + file -> stream to GCS -> write the Firestore
    ownership record -> call ingestion-worker /ingest (preflight + split +
    Pub/Sub fan-out). The frontend then polls /doc-status/{doc_id} for progress.

    The client never supplies `tenant_id` — it comes exclusively from the
    verified JWT (anti-IDOR, Phase 4.0).
    """
    validate_tenant_id(auth.tenant_id)
    validate_doc_id(doc_id)

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted")

    content = await file.read(_UPLOAD_MAX_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Empty file")
    if len(content) > _UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"File exceeds {_UPLOAD_MAX_BYTES // (1024 * 1024)} MB limit",
        )

    # Reject duplicates before writing anything (409 keeps re-upload idempotent
    # without clobbering an existing ingestion in flight).
    client = _get_firestore_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Firestore unavailable")
    existing = client.document(f"tenants/{auth.tenant_id}/documents/{doc_id}").get()
    if existing.exists:
        raise HTTPException(
            status_code=409,
            detail=f"doc_id '{doc_id}' already exists; use DELETE first to re-upload",
        )

    filename = file.filename or f"{doc_id}.pdf"
    try:
        _upload_pdf_to_gcs(auth.tenant_id, doc_id, content)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("GCS upload failed for tenant %s doc %s", auth.tenant_id, doc_id)
        raise HTTPException(status_code=502, detail=f"Storage write failed: {exc}") from exc

    _create_document_record(auth.tenant_id, doc_id, filename)

    try:
        worker_resp = _trigger_ingestion(auth.tenant_id, doc_id)
    except HTTPException as exc:
        # The PDF + record are persisted; report the trigger failure but don't
        # delete them — a retry of /ingest (or manual trigger) can recover.
        logger.warning("Ingestion trigger failed for %s/%s: %s", auth.tenant_id, doc_id, exc.detail)
        raise exc

    if "total_pages" in worker_resp and worker_resp["total_pages"]:
        try:
            client.document(f"tenants/{auth.tenant_id}/documents/{doc_id}").set({
                "total_pages": int(worker_resp["total_pages"]),
            }, merge=True)
        except Exception as exc:
            logger.debug("Failed saving total_pages to doc record: %s", exc)

    status = worker_resp.get("status", "processing")
    if status == "rejected":
        raise HTTPException(status_code=422, detail=worker_resp.get("reason", "Ingestion rejected file"))

    return UploadResponse(doc_id=doc_id, status=status)
