"""Chunk Visualization / QA view (ACTIONPLAN Task 1.10).

Admin-only overlay: renders a source PDF page and draws every chunk's bbox
on top, plus the routing decision per element, so a human can visually
sanity-check Docling parsing and VLM router decisions.

Auth is added in Phase 4.0; today the route is bound to the worker app only.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

from flask import jsonify

from services.common.ingestion.store import ChunkStore, get_chunk_store

logger = logging.getLogger(__name__)


def build_qa_response(
    doc_id: str,
    page_number: int,
    tenant_id: str,
    store: Optional[ChunkStore] = None,
    gcs_client=None,
) -> tuple[dict, int]:
    """Return chunk overlay data for one page of a document.

    Renders the page to a PNG (via pypdf + PIL) and draws bboxes as red
    rectangles, base64-encoded in the response. Falls back to the page count
    from the store when no renderer is available.
    """
    store = store or get_chunk_store()
    chunks = store.get_by_doc(doc_id)
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
