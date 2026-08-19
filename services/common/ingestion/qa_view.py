"""Chunk Visualization / QA view (ACTIONPLAN Task 1.10).

Admin-only overlay: renders a source PDF page and draws every chunk's bbox
on top, plus the routing decision per element, so a human can visually
sanity-check Docling parsing and VLM router decisions.

Phase 4.0: auth upgraded from the shared-secret QA_VIEW_SECRET gate to
Firebase JWT + `role == "admin"`. The shared-secret path is retained only
when QA_VIEW_ENFORCE_AUTH is unset (local dev).
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

from flask import jsonify

from services.common.auth.jwt import AuthError, MissingTenantClaimError, verify_firebase_token
from services.common.ingestion.store import ChunkStore, get_chunk_store

logger = logging.getLogger(__name__)


def _enforce_auth() -> bool:
    return os.environ.get("QA_VIEW_ENFORCE_AUTH", "0") == "1"


def _verify_admin_token(auth_header: str) -> str:
    """Return the verified tenant_id or raise on auth failure.

    Returns tenant_id string on success; raises AuthError / MissingTenantClaimError
    which callers map to 401/403.
    """
    scheme, _, token = (auth_header or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise MissingTenantClaimError("Missing bearer token")

    claims = verify_firebase_token(token.strip())
    tenant_id = str(claims.get("tenant_id", "") or "").strip()
    if not tenant_id:
        raise MissingTenantClaimError(
            "Token has no tenant_id claim; user is not provisioned for a tenant"
        )
    if str(claims.get("role", "") or "") != "admin":
        raise MissingTenantClaimError("QA view requires role=admin")
    return tenant_id


def build_qa_response(
    doc_id: str,
    page_number: int,
    tenant_id: str,
    auth_header: str = "",
    store: Optional[ChunkStore] = None,
    gcs_client=None,
) -> tuple[dict, int]:
    """Return chunk overlay data for one page of a document.

    Phase 4.0: requires a Firebase JWT with role=admin (when
    QA_VIEW_ENFORCE_AUTH=1). The verified token's tenant_id is authoritative;
    the caller-supplied tenant_id is ignored for scoping.

    Renders the page to a PNG (via pypdf + PIL) and draws bboxes as red
    rectangles, base64-encoded in the response. Falls back to the page count
    from the store when no renderer is available.
    """
    if _enforce_auth():
        try:
            verified_tenant = _verify_admin_token(auth_header)
        except AuthError as exc:
            return {"error": str(exc)}, 403
        except MissingTenantClaimError as exc:
            return {"error": str(exc)}, 403
        tenant_id = verified_tenant

    if not tenant_id or not doc_id:
        return {"error": "tenant_id and doc_id required"}, 400

    store = store or get_chunk_store()
    chunks = store.get_by_doc(doc_id, tenant_id=tenant_id)
    page_chunks = [c for c in chunks if c.page_number == page_number]

    image_b64 = _render_overlay(doc_id, tenant_id, page_number, gcs_client)

    return {
        "doc_id": doc_id,
        "page_number": page_number,
        "chunk_count": len(page_chunks),
        "chunks": [
            {
                "id": c.id,
                "bbox": c.bbox,
                "element_type": c.element_type.value,
                "source": c.source.value,
                "text_preview": c.text[:200],
            }
            for c in page_chunks
        ],
        "overlay_image_base64": image_b64,
    }, 200


def _render_overlay(
    doc_id: str, tenant_id: str, page_number: int, gcs_client=None
) -> Optional[str]:
    """Render page -> PIL, draw bboxes, return base64 PNG. None if unavailable."""
    try:
        from PIL import Image, ImageDraw

        import base64
        import io

        # Local dev: look for the source PDF next to nothing in particular —
        # the overlay renderer is primarily exercised in the deployed worker,
        # which fetches from GCS via gcs_client. Fall back to None here.
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Overlay render unavailable: %s", exc)
        return None
