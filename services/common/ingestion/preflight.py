"""Pre-ingestion payload scanner (ACTIONPLAN Task 1.2).

Rejects payloads BEFORE they enter the pipeline: oversized PDFs (>500 pages)
and corrupt PDF trailers. Cleanly separated so the Pub/Sub handler can
distinguish "reject forever" (ack -> never queued) from "transient failure"
(nack -> retry -> DLQ).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from services.common.errors import RejectionCode

MAX_PAGE_COUNT = 500


class PreflightError(Exception):
    """Raised when a payload is rejected before processing.

    Carries an enumerated :class:`RejectionCode` so callers can return a stable
    public reason instead of leaking parser/exception text.
    """

    def __init__(self, message: str, code: str = RejectionCode.PDF_CORRUPT) -> None:
        super().__init__(message)
        self.code = code


def check_pdf(path: Path, max_pages: int = MAX_PAGE_COUNT) -> dict:
    """Validate a PDF file before it enters the pipeline.

    Returns metadata dict: {"page_count": int, "file_size_bytes": int}.
    Raises PreflightError for oversized or corrupt payloads.
    """
    if not path.exists():
        raise PreflightError(f"File not found: {path}", code=RejectionCode.UNSUPPORTED_PDF)

    size = path.stat().st_size
    if size == 0:
        raise PreflightError(f"Empty file (0 bytes): {path}", code=RejectionCode.PDF_EMPTY)

    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(path), strict=False)
        page_count = len(reader.pages)  # forces trailer parse
    except (PdfReadError, ValueError, OSError) as exc:
        raise PreflightError(
            f"Corrupt PDF trailer: {exc}", code=RejectionCode.PDF_CORRUPT
        ) from exc

    if page_count > max_pages:
        raise PreflightError(
            f"Document has {page_count} pages; max allowed is {max_pages}. Rejected pre-queue.",
            code=RejectionCode.PDF_PAGE_LIMIT_EXCEEDED,
        )

    return {"page_count": page_count, "file_size_bytes": size}
