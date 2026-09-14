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
import re
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.common.auth.jwt import AuthContext, require_auth
from services.common.cloud import (
    FIRESTORE_TIMEOUT_SECONDS,
    fs_delete,
    fs_get,
    fs_get_all,
    fs_set,
    fs_stream,
    fs_update,
    gcs_delete,
    gcs_upload,
)
from services.common.auth.rate_limit import limiter
from services.common.auth.validation import (
    MAX_HISTORY_TURNS,
    validate_doc_id,
    validate_doc_ids,
    validate_history,
    validate_query,
    validate_session_id,
    validate_tenant_id,
    validate_top_k,
)
from services.common.errors import (
    DEFAULT_MESSAGES,
    STATUS_TO_CODE,
    BadUpstreamResponse,
    Conflict,
    DependencyTimeout,
    DependencyUnavailable,
    ErrorCode,
    InvalidInput,
    NotFound,
    ServiceError,
    error_envelope,
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

_RAW_BUCKET = os.environ.get("GCS_RAW_BUCKET", "procambrian-iris-staging-raw")
_VIEW_URL_TTL_SECONDS = 900

# Upload guards (Task 5.0b): size cap before any GCS write; page cap enforced
# downstream by the ingestion-worker preflight. 50 MB is generous for scanned
# legal PDFs and far below Cloud Run request limits.
_UPLOAD_MAX_BYTES = 50 * 1024 * 1024
_UPLOAD_CHUNK_BYTES = 1024 * 1024

# Ingestion trigger (Task 5.0b): the ingestion-worker /ingest endpoint performs
# preflight + page split + Pub/Sub fan-out. It's secured by Cloud Run IAM, so we
# impersonate its service account to mint an ID token (same pattern as
# scripts/eval_phase2.py). Env overridable for local/emulator tests.
_INGEST_URL = os.environ.get("INGEST_URL", "")
_INGEST_SA = os.environ.get(
    "INGEST_SA", "ingestion-worker-sa@procambrian-iris-staging-2026.iam.gserviceaccount.com"
)
_GCP_PROJECT = os.environ.get("GCP_PROJECT", "procambrian-iris-staging-2026")


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
        gcs_delete(blob)
    except Exception as exc:
        logger.warning("GCS delete failed for %s/%s: %s", tenant_id, doc_id, exc)


def _delete_firestore_doc(doc_path: str) -> None:
    client = _get_firestore_client()
    if client is None:
        logger.warning("Firestore client unavailable; skipping delete: %s", doc_path)
        return
    try:
        fs_delete(client.document(doc_path))
    except Exception as exc:
        logger.warning("Firestore delete failed for %s: %s", doc_path, exc)


def _session_store_unavailable(cause: Exception | None = None) -> DependencyUnavailable:
    return DependencyUnavailable(
        "The session store is temporarily unavailable.",
        code=ErrorCode.SESSION_STORE_UNAVAILABLE,
    )


def _create_firestore_session(tenant_id: str) -> str:
    """Create an empty session document and return the new session_id.

    Phase 0.1: never returns an unpersisted id. If Firestore is unavailable or
    the write fails, raises a typed 503 so the caller cannot mint a phantom
    session that later fails open.
    """
    session_id = str(uuid.uuid4())
    client = _get_firestore_client()
    if client is None:
        raise _session_store_unavailable()
    try:
        fs_set(
            client.document(f"tenants/{tenant_id}/sessions/{session_id}"),
            {
                "session_id": session_id,
                "tenant_id": tenant_id,
                "name": "",
                "document_ids": [],
                "turn_seq": 0,
                "created_at": _server_timestamp(),
            },
        )
    except Exception as exc:
        logger.warning("Firestore session create failed: %s", exc)
        raise _session_store_unavailable(exc) from exc
    return session_id


def _session_doc_path(tenant_id: str, session_id: str) -> str:
    return f"tenants/{tenant_id}/sessions/{session_id}"


def _session_messages_path(tenant_id: str, session_id: str) -> str:
    return f"{_session_doc_path(tenant_id, session_id)}/messages"


def _append_firestore_messages(
    tenant_id: str,
    session_id: str,
    messages: list[dict],
    expected_turn_seq: Optional[int] = None,
) -> int:
    """Atomically append a complete turn (user + assistant) to the session.

    Phase 0.1 (P0): the turn sequence is allocated inside a Firestore
    transaction, so ordering is correct across independent Cloud Run instances
    — never from an in-process counter. Each message is stored with its
    ``turn_seq`` and ``message_index``.

    When ``expected_turn_seq`` is supplied (the value read before synthesis),
    the transaction raises :class:`Conflict` if the session advanced in the
    meantime. This is optimistic concurrency: a stale answer cannot be appended
    out of order behind a newer turn.
    """
    if not messages:
        return expected_turn_seq if expected_turn_seq is not None else 0
    client = _get_firestore_client()
    if client is None:
        raise _session_store_unavailable()

    from google.cloud import firestore

    session_ref = client.document(_session_doc_path(tenant_id, session_id))
    collection = client.collection(_session_messages_path(tenant_id, session_id))
    transaction = client.transaction()

    @firestore.transactional
    def _write(txn) -> int:
        snapshot = session_ref.get(
            transaction=txn, timeout=FIRESTORE_TIMEOUT_SECONDS
        )
        current = 0
        if snapshot.exists:
            current = int((snapshot.to_dict() or {}).get("turn_seq", 0) or 0)
        if expected_turn_seq is not None and current != expected_turn_seq:
            raise Conflict(
                "The conversation changed while this answer was generated; please retry."
            )
        turn_seq = current + 1
        for index, msg in enumerate(messages):
            # Deterministic message ids + a single valued turn_seq make the
            # retried transaction idempotent: re-running cannot duplicate state.
            txn.set(
                collection.document(f"{turn_seq:020d}-{index}"),
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "turn_seq": turn_seq,
                    "message_index": index,
                    "created_at": datetime.now(timezone.utc),
                },
            )
        txn.set(
            session_ref,
            {"turn_seq": turn_seq},
            merge=True,
        )
        return turn_seq

    try:
        return _write(transaction)
    except Conflict:
        raise
    except Exception as exc:
        logger.warning("Firestore messages append failed: %s", exc)
        raise _session_store_unavailable(exc) from exc


def _load_session_history(
    tenant_id: str, session_id: str, limit: int = 6
) -> tuple[list[dict], int]:
    """Load the last N messages and the current turn version.

    Returns ``(messages_oldest_first, turn_seq)``. Ordering uses the
    transaction-allocated ``turn_seq`` (+ ``message_index``), not wall-clock
    timestamps.
    """
    client = _get_firestore_client()
    if client is None:
        raise _session_store_unavailable()
    try:
        session_snap = fs_get(client.document(_session_doc_path(tenant_id, session_id)))
        version = 0
        if session_snap.exists:
            version = int((session_snap.to_dict() or {}).get("turn_seq", 0) or 0)
        docs = fs_stream(
            client.collection(_session_messages_path(tenant_id, session_id))
            .order_by("turn_seq", direction="DESCENDING")
            .order_by("message_index", direction="DESCENDING")
            .limit(limit)
        )
        docs.reverse()  # newest-first → chronological
        # ``Query.stream`` yields DocumentSnapshot objects in production (the
        # unit suite historically supplied plain dictionaries).  Normalize at
        # the boundary so missing fields remain safe without calling
        # ``DocumentSnapshot.get`` with a dict-style default argument.
        messages = []
        for snapshot in docs:
            data = snapshot.to_dict() if hasattr(snapshot, "to_dict") else snapshot
            data = data or {}
            messages.append(
                {"role": data.get("role", ""), "content": data.get("content", "")}
            )
        return messages, version
    except Exception as exc:
        logger.warning("Firestore messages load failed: %s", exc)
        raise _session_store_unavailable(exc) from exc


def _load_firestore_messages(
    tenant_id: str, session_id: str, limit: int = 6
) -> list[dict]:
    """Load the last N messages in chronological order (messages only)."""
    messages, _version = _load_session_history(tenant_id, session_id, limit)
    return messages


def _session_exists(tenant_id: str, session_id: str) -> bool:
    """Check whether a session document belongs to this tenant.

    Phase 0.1: fails closed. A missing client or a query error raises a typed
    503 rather than reporting that an unverified session exists.
    """
    client = _get_firestore_client()
    if client is None:
        raise _session_store_unavailable()
    try:
        doc = fs_get(client.document(f"tenants/{tenant_id}/sessions/{session_id}"))
        return bool(doc.exists)
    except Exception as exc:
        logger.warning("Firestore session existence check failed: %s", exc)
        raise _session_store_unavailable(exc) from exc


def _delete_firestore_session(tenant_id: str, session_id: str) -> None:
    _delete_firestore_doc(f"tenants/{tenant_id}/sessions/{session_id}")
    client = _get_firestore_client()
    if client is not None:
        try:
            messages = fs_get_all(
                client.collection(f"tenants/{tenant_id}/sessions/{session_id}/messages")
            )
            for msg in messages:
                fs_delete(msg.reference)
        except Exception as exc:
            logger.warning("Firestore messages delete failed: %s", exc)


def _remove_doc_from_sessions(tenant_id: str, doc_id: str) -> None:
    """FR-5.4: purge doc_id from every session's document_ids array."""
    client = _get_firestore_client()
    if client is None:
        logger.warning("Firestore client unavailable; skipping session purge for %s", doc_id)
        return
    try:
        sessions = fs_get_all(client.collection(f"tenants/{tenant_id}/sessions"))
        for session in sessions:
            data = session.to_dict() or {}
            doc_ids = list(data.get("document_ids") or [])
            if doc_id in doc_ids:
                doc_ids.remove(doc_id)
                fs_update(session.reference, {"document_ids": doc_ids})
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
    try:
        snapshot = fs_get(client.document(f"tenants/{tenant_id}/documents/{doc_id}"))
    except Exception as exc:  # noqa: BLE001 - provider text must not reach clients
        logger.warning("firestore document ownership lookup failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Firestore unavailable") from exc
    if not snapshot.exists:
        raise HTTPException(status_code=404, detail="Document not found")


def _authorized_doc_ids(tenant_id: str, requested: list[str] | None) -> list[str]:
    """Resolve requested doc ids against tenant ownership.

    Client-supplied ``doc_ids``/``active_docs`` are requests, not proof of
    access. Every id must resolve to a document under this tenant or the
    request is rejected. Returns the authorized, de-duplicated ids.
    """
    if not requested:
        return []
    authorized: list[str] = []
    for doc_id in requested:
        _document_exists(tenant_id, doc_id)
        if doc_id not in authorized:
            authorized.append(doc_id)
    return authorized


async def _stream_upload_to_gcs(tenant_id: str, doc_id: str, file: UploadFile) -> int:
    """Stream an upload to a temp file, then upload to GCS under a real deadline.

    Phase 0.1 (ING-001): the whole document is never buffered in memory. GCS's
    ``blob.open()`` exposes no per-operation transport timeout, so the bytes are
    spooled to a request-scoped temporary file (bounded by the size cap) and sent
    with ``upload_from_filename(..., timeout=...)``. The temporary file is always
    removed, and a partial GCS object is deleted on any failure so a retry of the
    whole operation starts clean.
    """
    gcs = _get_gcs_client()
    if gcs is None:
        raise DependencyUnavailable("Storage is unavailable.")
    blob = gcs.bucket(_RAW_BUCKET).blob(f"{tenant_id}/{doc_id}.pdf")
    total = 0
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = Path(tmp.name)
    try:
        try:
            with tmp:
                while True:
                    chunk = await file.read(_UPLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > _UPLOAD_MAX_BYTES:
                        raise InvalidInput(
                            f"File exceeds {_UPLOAD_MAX_BYTES // (1024 * 1024)} MB limit"
                        )
                    tmp.write(chunk)
            if total == 0:
                raise InvalidInput("Empty file")
            gcs_upload(blob, str(tmp_path), content_type="application/pdf")
        except ServiceError:
            _safe_delete_blob(blob)
            raise
        except Exception as exc:
            _safe_delete_blob(blob)
            logger.exception(
                "GCS upload failed for tenant %s doc %s", tenant_id, doc_id
            )
            raise BadUpstreamResponse("Storage write failed.") from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    return total


def _safe_delete_blob(blob) -> None:
    try:
        gcs_delete(blob)
    except Exception:
        pass


def _create_document_record(tenant_id: str, doc_id: str, filename: str) -> None:
    """Create the Firestore ownership record so view-url/delete work.

    The record also carries processing state so the frontend documents table
    can display it without a separate store.
    """
    client = _get_firestore_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Firestore unavailable")
    fs_set(
        client.document(f"tenants/{tenant_id}/documents/{doc_id}"),
        {
            "doc_id": doc_id,
            "tenant_id": tenant_id,
            "status": "processing",
            "filename": filename,
            "created_at": _server_timestamp(),
        },
    )


def _trigger_ingestion(tenant_id: str, doc_id: str) -> dict:
    """Call ingestion-worker /ingest to preflight + split + fan out to Pub/Sub.

    Phase 0.1: the upstream HTTP status is checked *before* its body is
    accepted, the success payload is schema-validated, and timeouts/auth/
    rejection/server failures are distinguished with typed errors. Raises
    ``ServiceError`` so the upload path can report a stable code.
    """
    if not _INGEST_URL:
        raise DependencyUnavailable("The ingestion service is not configured.")

    import requests
    from google.auth import default
    from google.auth.transport import requests as gauth_requests

    # Mint an ID token as the ingestion-worker SA (Cloud Run IAM) via the
    # IAM Credentials generateIdToken API — impersonated_credentials only
    # yields access tokens, not ID tokens.
    try:
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
            timeout=(5, 30),
        )
    except requests.Timeout as exc:
        raise DependencyTimeout("Timed out authenticating to the ingestion service.") from exc
    except requests.RequestException as exc:
        raise DependencyUnavailable("Could not reach the ingestion service.") from exc

    if resp.status_code != 200:
        raise BadUpstreamResponse("The ingestion service authentication failed.")
    try:
        payload = resp.json()
        id_token = payload["token"]
    except Exception as exc:
        raise BadUpstreamResponse(
            "The ingestion service authentication returned an invalid response."
        ) from exc
    if not isinstance(id_token, str) or not id_token:
        raise BadUpstreamResponse("The ingestion service authentication returned no token.")

    try:
        resp = requests.post(
            f"{_INGEST_URL}/ingest",
            json={
                "gcs_uri": f"gs://{_RAW_BUCKET}/{tenant_id}/{doc_id}.pdf",
                "tenant_id": tenant_id,
                "doc_id": doc_id,
            },
            headers={"Authorization": f"Bearer {id_token}"},
            timeout=(5, 120),
        )
    except requests.Timeout as exc:
        raise DependencyTimeout("The ingestion service timed out.") from exc
    except requests.RequestException as exc:
        raise DependencyUnavailable("The ingestion service is unavailable.") from exc

    if resp.status_code in (401, 403):
        raise DependencyUnavailable("The ingestion service rejected our credentials.")
    if resp.status_code == 429:
        raise DependencyUnavailable("The ingestion service is rate limited.")
    if resp.status_code >= 500:
        raise DependencyUnavailable("The ingestion service is temporarily unavailable.")
    if resp.status_code >= 400:
        raise BadUpstreamResponse("The ingestion service rejected the request.")

    try:
        data = resp.json()
    except Exception as exc:
        raise BadUpstreamResponse("The ingestion service returned an invalid response.") from exc
    if not isinstance(data, dict):
        raise BadUpstreamResponse("The ingestion service returned an invalid response.")
    if "total_pages" in data and data["total_pages"] is not None:
        if not isinstance(data["total_pages"], int) or isinstance(data["total_pages"], bool):
            raise BadUpstreamResponse("The ingestion service returned an invalid response.")
    if "status" in data and not isinstance(data["status"], str):
        raise BadUpstreamResponse("The ingestion service returned an invalid response.")
    return data


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

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "") or ""


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Attach a validated/generated correlation ID to every request + response."""
    raw = request.headers.get("X-Request-ID", "")
    request.state.request_id = raw if _REQUEST_ID_PATTERN.match(raw) else uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


def _error_response(request, code, message, status_code, headers=None):
    return JSONResponse(
        status_code=status_code,
        content=error_envelope(code, message, _request_id(request)),
        headers=headers,
    )


@app.exception_handler(ServiceError)
async def _handle_service_error(request: Request, exc: ServiceError):
    logger.warning(
        "service_error code=%s status=%s request_id=%s",
        exc.code, exc.status_code, _request_id(request),
    )
    headers = {"Retry-After": "1"} if exc.code == ErrorCode.RATE_LIMITED else None
    return _error_response(request, exc.code, exc.public_message, exc.status_code, headers)


@app.exception_handler(RequestValidationError)
async def _handle_validation_error(request: Request, exc: RequestValidationError):
    return _error_response(
        request,
        ErrorCode.INVALID_REQUEST,
        DEFAULT_MESSAGES[ErrorCode.INVALID_REQUEST],
        422,
    )


@app.exception_handler(HTTPException)
async def _handle_http_exception(request: Request, exc: HTTPException):
    code = STATUS_TO_CODE.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    if exc.status_code < 500 and isinstance(exc.detail, str) and exc.detail:
        message = exc.detail
    else:
        message = DEFAULT_MESSAGES[code]
    return _error_response(
        request, code, message, exc.status_code, headers=getattr(exc, "headers", None)
    )


@app.exception_handler(Exception)
async def _handle_unexpected_exception(request: Request, exc: Exception):
    logger.exception("unhandled_exception request_id=%s", _request_id(request))
    return _error_response(
        request,
        ErrorCode.INTERNAL_ERROR,
        DEFAULT_MESSAGES[ErrorCode.INTERNAL_ERROR],
        500,
    )


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
        doc_snap = fs_get(client.document(f"tenants/{tenant_id}/documents/{doc_id}"))
        if doc_snap.exists:
            data = doc_snap.to_dict() or {}
            if "total_pages" in data and data["total_pages"]:
                return int(data["total_pages"])
        tracker_snap = fs_get(
            client.document(f"tenants/{tenant_id}/documents/{doc_id}/progress/tracker")
        )
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
        docs = fs_get_all(client.collection(f"tenants/{auth.tenant_id}/documents"))
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
    validate_query(request.query)
    limiter.check(f"tenant:{auth.tenant_id}")
    top_k = validate_top_k(request.top_k, for_synthesis=False)
    history = validate_history(request.history)
    doc_ids = _authorized_doc_ids(auth.tenant_id, request.doc_ids)
    try:
        t0 = time.perf_counter()
        trace = None
        if request.trace:
            trace = {}
        if request.mode == "deep":
            results = await orchestrator.deep_search(
                query=request.query,
                tenant_id=auth.tenant_id,
                history=history,
                doc_ids=doc_ids or None,
                top_k=top_k,
                trace=trace,
            )
        else:
            results, trace = await orchestrator.standard_search(
                query=request.query,
                tenant_id=auth.tenant_id,
                doc_ids=doc_ids or None,
                top_k=top_k,
                rerank_blend=request.rerank_blend,
                history=history,
            )
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return SearchResponse(
            results=results,
            mode=request.mode,
            latency_ms=latency,
            trace=trace,
        )
    except ServiceError:
        raise
    except Exception as exc:
        logger.exception("Search failed for tenant %s", auth.tenant_id)
        raise ServiceError() from exc


@app.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Retrieve -> synthesize -> grounded structured answer."""
    validate_tenant_id(auth.tenant_id)
    validate_query(request.query)
    # Rate limit BEFORE any session creation or Firestore document reads so an
    # over-limit caller cannot generate database cost.
    limiter.check(f"tenant:{auth.tenant_id}")
    active_docs = (
        [d.model_dump() for d in request.active_docs] if request.active_docs else []
    )
    authorized_active_ids = _authorized_doc_ids(
        auth.tenant_id, [d["doc_id"] for d in active_docs]
    )
    authorized_doc_ids = _authorized_doc_ids(
        auth.tenant_id, validate_doc_ids(request.doc_ids)
    )
    authorized_scope = set(authorized_active_ids) | set(authorized_doc_ids)
    if request.session_id:
        validate_session_id(request.session_id)
        if not await asyncio.to_thread(_session_exists, auth.tenant_id, request.session_id):
            raise NotFound("Session not found")
        # Server history is authoritative for a session: client-supplied turns
        # are ignored entirely (never merged). The version read here is used
        # as an optimistic-concurrency guard when appending the answer.
        history, session_version = await asyncio.to_thread(
            _load_session_history, auth.tenant_id, request.session_id, MAX_HISTORY_TURNS
        )
    else:
        request.session_id = await asyncio.to_thread(
            _create_firestore_session, auth.tenant_id
        )
        # Client history is only honored for a stateless request.
        history = validate_history(request.history)
        session_version = 0
    top_k = validate_top_k(request.top_k, for_synthesis=True)
    try:
        t0 = time.perf_counter()
        trace = None
        if request.trace:
            trace = {}

        # Intent defaults are initialized on every path so standard/deep
        # requests without active_docs never dereference an unbound name.
        intent = {
            "intent": "GENERAL_SEARCH",
            "target_doc_ids": [],
            "needs_decomposition": False,
            "search_queries": [],
            "rewritten_query": request.query,
        }
        query_to_use = request.query
        doc_ids_filter = authorized_doc_ids or None

        # Fallback: if active_docs is empty but query references a specific document,
        # warn the user instead of searching blindly across all docs
        if not request.active_docs and not request.doc_ids:
            if re.search(r'\b(first|second|third|doc_\d|document\s*\d)\b', request.query, re.IGNORECASE):
                if trace is not None:
                    trace["warning"] = "Document reference detected but no active_docs provided. Upload documents first."

        if request.active_docs and request.mode != "deep":
            try:
                intent = await asyncio.to_thread(
                    provider.route_query, request.query, active_docs
                )
                # The router may only target documents the server authorized.
                intent["target_doc_ids"] = [
                    d for d in intent.get("target_doc_ids", []) if d in authorized_scope
                ]
                if trace is not None:
                    trace["intent"] = intent

                if intent["intent"] == "DOCUMENT_SUMMARY" and intent["target_doc_ids"]:
                    # Fetch pre-computed summaries, skip Qdrant
                    summaries = await asyncio.to_thread(
                        _get_summaries, auth.tenant_id, intent["target_doc_ids"]
                    )
                    if summaries:
                        # Build context from summaries directly
                        fname_map = await asyncio.to_thread(
                            _get_filenames, auth.tenant_id, intent["target_doc_ids"]
                        )
                        summary_parts = []
                        source_chunks = []
                        for i, doc_id in enumerate(intent["target_doc_ids"], start=1):
                            fname = fname_map.get(doc_id, doc_id)
                            summary_text = summaries.get(doc_id, "Summary not available.")
                            summary_parts.append(
                                f"Document [{i}] ({fname}):\n{summary_text}"
                            )
                            source_chunks.append({
                                "chunk_id": f"summary_{doc_id}",
                                "doc_id": doc_id,
                                "page_number": 0,
                                "bbox": [],
                                "text": summary_text,
                                "score": 1.0,
                                "element_type": "summary",
                                "source": "pre_computed",
                                "metadata": {},
                            })
                        context = "\n\n".join(summary_parts)
                        t_synth = time.perf_counter()
                        answer = await asyncio.to_thread(
                            provider.synthesize, context, request.query, source_chunks
                        )
                        synthesis_ms = round((time.perf_counter() - t_synth) * 1000, 1)
                        answer = validate_citations(answer, [])
                        if request.session_id:
                            await asyncio.to_thread(
                                _append_firestore_messages, auth.tenant_id, request.session_id,
                                [
                                    {"role": "user", "content": request.query},
                                    {"role": "assistant", "content": answer.answer},
                                ],
                                session_version,
                            )
                        latency = round((time.perf_counter() - t0) * 1000, 2)
                        if trace is not None:
                            trace["synthesis_ms"] = synthesis_ms
                            trace["chunks"] = source_chunks
                        return QueryResponse(
                            answer=answer.answer,
                            citations=answer.citations,
                            mode=request.mode,
                            latency_ms=latency,
                            chunks_used=len(source_chunks),
                            session_id=request.session_id,
                            trace=trace,
                        )
                    # Fallback: summaries not ready, do normal search

                elif intent["intent"] == "SPECIFIC_SEARCH" and intent["target_doc_ids"]:
                    doc_ids_filter = intent["target_doc_ids"]
                    query_to_use = intent.get("rewritten_query", request.query)

            except Exception as exc:
                logger.warning("Intent routing failed, falling back: %s", exc)

        if request.mode == "deep":
            retrieved = await orchestrator.deep_search(
                query=query_to_use,
                tenant_id=auth.tenant_id,
                history=history,
                doc_ids=doc_ids_filter,
                top_k=top_k,
                trace=trace,
            )
        elif intent.get("needs_decomposition") and intent.get("search_queries"):
            # Multi-query decomposition: batch-embed + parallel fan-out + dedup
            sub_queries = intent["search_queries"]
            sub_texts = [sq["query"] for sq in sub_queries]

            # Batch-embed all sub-queries in one HTTP call (~80ms vs ~240ms sequential)
            sub_vectors = await asyncio.to_thread(
                provider.embed_query_batch, sub_texts
            )

            # Fan out parallel searches — each gets pre-computed vector + text for BM25
            search_tasks = [
                orchestrator.standard_search(
                    query=sub_texts[i],
                    tenant_id=auth.tenant_id,
                    doc_ids=doc_ids_filter,
                    top_k=top_k,
                    rerank_blend=_env_rerank_blend(),
                    query_vector=sub_vectors[i],
                    query_text_for_sparse=sub_texts[i],
                )
                for i in range(len(sub_texts))
            ]

            # Collect parallel results
            sub_results = await asyncio.gather(*search_tasks)

            # Merge: flatten all scored chunks, dedup by chunk_id, keep highest score
            all_chunks: dict = {}
            for results, _sub_trace in sub_results:
                for chunk in results:
                    cid = chunk.id
                    if cid not in all_chunks or chunk.score > all_chunks[cid].score:
                        all_chunks[cid] = chunk

            retrieved = sorted(all_chunks.values(), key=lambda c: c.score, reverse=True)
            retrieved = retrieved[:top_k]  # cap before parent expansion
        else:
            # RERANK_BLEND (Phase 12.1): server-side default rerank weight for
            # production answers — /query has no request-level blend param, so
            # the env picked by the eval sweep applies automatically. Unset/0
            # keeps the hybrid-only ranking.
            retrieved, trace = await orchestrator.standard_search(
                query=query_to_use,
                tenant_id=auth.tenant_id,
                doc_ids=doc_ids_filter,
                top_k=top_k,
                rerank_blend=_env_rerank_blend(),
                history=history,
            )

        expanded = await asyncio.to_thread(
            _expand_to_parent_pages, retrieved, auth.tenant_id
        )
        context, source_chunks = _build_synthesis_context(expanded, auth.tenant_id)
        t_synth = time.perf_counter()
        answer = await asyncio.to_thread(
            provider.synthesize, context, request.query, source_chunks
        )
        synthesis_ms = round((time.perf_counter() - t_synth) * 1000, 1)
        answer = validate_citations(answer, expanded)
        if request.session_id:
            await asyncio.to_thread(
                _append_firestore_messages, auth.tenant_id, request.session_id,
                [
                    {"role": "user", "content": request.query},
                    {"role": "assistant", "content": answer.answer},
                ],
                session_version,
            )
        latency = round((time.perf_counter() - t0) * 1000, 2)

        # Add synthesis timing and chunk provenance to trace
        if trace is not None:
            trace["synthesis_ms"] = synthesis_ms
            trace["chunks"] = [
                {
                    "chunk_id": sc["chunk_id"],
                    "doc_id": sc["doc_id"],
                    "page": sc["page_number"],
                    "source": sc.get("source", "unknown"),
                    "element_type": sc.get("element_type", "unknown"),
                    "score": round(sc.get("score", 0.0), 3),
                }
                for sc in source_chunks
            ]

        return QueryResponse(
            answer=answer.answer,
            citations=answer.citations,
            mode=request.mode,
            latency_ms=latency,
            chunks_used=len(retrieved),
            session_id=request.session_id,
            trace=trace,
        )
    except ServiceError:
        raise
    except Exception as exc:
        logger.exception("Query failed for tenant %s", auth.tenant_id)
        raise ServiceError() from exc


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


def _get_filenames(tenant_id: str, doc_ids: list[str]) -> dict[str, str]:
    """Batch-fetch filenames from Firestore for a set of doc_ids."""
    if not doc_ids:
        return {}
    client = _get_firestore_client()
    if client is None:
        return {}
    filenames: dict[str, str] = {}
    for doc_id in doc_ids:
        try:
            snap = fs_get(client.document(f"tenants/{tenant_id}/documents/{doc_id}"))
            if snap.exists:
                data = snap.to_dict() or {}
                filenames[doc_id] = data.get("filename", doc_id)
        except Exception:
            filenames[doc_id] = doc_id
    return filenames


def _get_summaries(tenant_id: str, doc_ids: list[str]) -> dict[str, str]:
    """Batch-fetch pre-computed document summaries from Firestore."""
    if not doc_ids:
        return {}
    client = _get_firestore_client()
    if client is None:
        return {}
    summaries: dict[str, str] = {}
    for doc_id in doc_ids:
        try:
            snap = fs_get(client.document(f"tenants/{tenant_id}/documents/{doc_id}"))
            if snap.exists:
                data = snap.to_dict() or {}
                summary = data.get("summary", "")
                if summary:
                    summaries[doc_id] = summary
        except Exception:
            pass
    return summaries


def _build_synthesis_context(
    retrieved: list[ScoredChunk],
    tenant_id: str = "",
) -> tuple[str, list[dict]]:
    """Build the source-chunk context and the source_chunks list for grounding.

    Sources are labeled with simple integer refs [1], [2], ... (Phase 9.0-D) so
    the model cites via short, stable markers that map 1:1 back to chunk_ids in
    `source_chunks` (position i -> source_chunks[i]).
    """
    # Batch-fetch filenames for document provenance
    doc_ids = list({c.doc_id for c in retrieved})
    filenames = _get_filenames(tenant_id, doc_ids) if tenant_id else {}

    source_chunks: list[dict] = []
    parts: list[str] = []
    for i, chunk in enumerate(retrieved, start=1):
        fname = filenames.get(chunk.doc_id, chunk.doc_id)
        parts.append(
            f"Source [{i}] (Document: {fname}, Page {chunk.page_number}):\n"
            f"{chunk.text}"
        )
        source_chunks.append({
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "page_number": chunk.page_number,
            "bbox": list(chunk.bbox),
            "text": chunk.text,
            "score": chunk.score,
            "element_type": chunk.element_type,
            "source": chunk.source,
            "metadata": chunk.metadata,
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
            docs = fs_get_all(client.collection(f"tenants/{auth.tenant_id}/documents"))
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
    fs_set(
        client.document(doc_path),
        {
            "session_id": session_id,
            "tenant_id": auth.tenant_id,
            "name": request.name or "",
            "document_ids": document_ids,
            "created_at": _server_timestamp(),
        },
    )
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
        docs = fs_get_all(client.collection(f"tenants/{auth.tenant_id}/sessions"))
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
        raise InvalidInput("Only PDF files are accepted")

    # Reject duplicates before writing anything (409 keeps re-upload idempotent
    # without clobbering an existing ingestion in flight).
    client = _get_firestore_client()
    if client is None:
        raise DependencyUnavailable("Firestore is unavailable.")
    existing = fs_get(
        client.document(f"tenants/{auth.tenant_id}/documents/{doc_id}")
    )
    if existing.exists:
        raise Conflict("A document with this id already exists; delete it before re-uploading.")

    filename = file.filename or f"{doc_id}.pdf"
    await _stream_upload_to_gcs(auth.tenant_id, doc_id, file)

    _create_document_record(auth.tenant_id, doc_id, filename)

    try:
        worker_resp = _trigger_ingestion(auth.tenant_id, doc_id)
    except ServiceError as exc:
        # The PDF + record are persisted; report the trigger failure but don't
        # delete them — a retry of /ingest (or manual trigger) can recover.
        logger.warning(
            "Ingestion trigger failed for %s/%s: %s", auth.tenant_id, doc_id, exc.public_code
        )
        raise

    if "total_pages" in worker_resp and worker_resp["total_pages"]:
        try:
            fs_set(
                client.document(f"tenants/{auth.tenant_id}/documents/{doc_id}"),
                {"total_pages": int(worker_resp["total_pages"])},
                merge=True,
            )
        except Exception as exc:
            logger.debug("Failed saving total_pages to doc record: %s", exc)

    status = worker_resp.get("status", "processing")
    if status == "rejected":
        # Enumerated rejection message only — never worker exception text.
        raise InvalidInput(worker_resp.get("message") or "Ingestion rejected the file")

    return UploadResponse(doc_id=doc_id, status=status)


@app.post("/documents/{doc_id}/retry", response_model=UploadResponse)
async def retry_document(
    doc_id: str,
    auth: AuthContext = Depends(require_auth),
):
    """Retry ingestion for an already-owned document.

    Upload persists ownership before dispatching work. If the upstream worker
    or Pub/Sub is temporarily unavailable, clients must be able to retry the
    dispatch without re-uploading the PDF or receiving a permanent 409.
    Deterministic page event IDs and idempotent stores make a retry safe.
    """
    validate_tenant_id(auth.tenant_id)
    validate_doc_id(doc_id)
    client = _get_firestore_client()
    if client is None:
        raise DependencyUnavailable("Firestore is unavailable.")
    snapshot = fs_get(client.document(f"tenants/{auth.tenant_id}/documents/{doc_id}"))
    if not snapshot.exists:
        raise NotFound("Document not found")

    worker_resp = _trigger_ingestion(auth.tenant_id, doc_id)
    total_pages = worker_resp.get("total_pages")
    if total_pages:
        fs_set(
            client.document(f"tenants/{auth.tenant_id}/documents/{doc_id}"),
            {"total_pages": int(total_pages), "status": "processing"},
            merge=True,
        )
    return UploadResponse(doc_id=doc_id, status=worker_resp.get("status", "processing"))
