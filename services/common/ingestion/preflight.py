"""Pre-ingestion payload scanner (ACTIONPLAN Task 1.2).

Rejects payloads BEFORE they enter the pipeline: oversized PDFs (>500 pages)
and corrupt PDF trailers. Cleanly separated so the Pub/Sub handler can
distinguish "reject forever" (ack -> never queued) from "transient failure"
(nack -> retry -> DLQ).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

MAX_PAGE_COUNT = 500


class PreflightError(Exception):
    """Raised when a payload is rejected before processing."""


def check_pdf(path: Path, max_pages: int = MAX_PAGE_COUNT) -> dict:
    """Validate a PDF file before it enters the pipeline.

    Returns metadata dict: {"page_count": int, "file_size_bytes": int}.
    Raises PreflightError for oversized or corrupt payloads.
    """
    if not path.exists():
        raise PreflightError(f"File not found: {path}")

    size = path.stat().st_size
    if size == 0:
        raise PreflightError(f"Empty file (0 bytes): {path}")

    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(path), strict=False)
        page_count = len(reader.pages)  # forces trailer parse
    except (PdfReadError, ValueError, OSError) as exc:
        raise PreflightError(f"Corrupt PDF trailer: {exc}") from exc

    if page_count > max_pages:
        raise PreflightError(
            f"Document has {page_count} pages; max allowed is {max_pages}. Rejected pre-queue."
        )

    return {"page_count": page_count, "file_size_bytes": size}
