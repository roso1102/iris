"""Page-level PDF splitter for parallel ingestion dispatch.

Downloads a PDF from GCS, splits into single-page blobs, uploads each
back to GCS, and returns per-page Pub/Sub attributes for fan-out.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def split_pdf(
    gcs_uri: str,
    doc_id: str,
    tenant_id: str,
    gcs_client=None,
) -> List[dict]:
    """Split PDF into single-page blobs and upload to GCS.

    Returns list of dicts with per-page Pub/Sub attributes:
    {"gcs_uri": "gs://.../page_N.pdf", "tenant_id": ..., "doc_id": ..., "page_number": N, "total_pages": T}
    """
    from pypdf import PdfReader, PdfWriter

    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = _download_pdf(gcs_uri, tmpdir, doc_id, gcs_client)
        reader = PdfReader(str(local_path))
        total_pages = len(reader.pages)

        if total_pages == 0:
            return []

        bucket_name, prefix = _split_gcs_uri(gcs_uri)
        base_dir = f"{tenant_id}/{doc_id}/pages"

        messages = []
        for page_idx in range(total_pages):
            writer = PdfWriter()
            writer.add_page(reader.pages[page_idx])

            page_no = page_idx + 1
            page_path = Path(tmpdir) / f"page_{page_no}.pdf"
            with open(page_path, "wb") as f:
                writer.write(f)

            page_gcs_uri = f"gs://{bucket_name}/{base_dir}/page_{page_no}.pdf"
            _upload_blob(page_path, bucket_name, f"{base_dir}/page_{page_no}.pdf", gcs_client)

            messages.append({
                "gcs_uri": page_gcs_uri,
                "tenant_id": tenant_id,
                "doc_id": doc_id,
                "page_number": page_no,
                "total_pages": total_pages,
            })

        logger.info("Split %s into %d page blobs for doc_id=%s", gcs_uri, total_pages, doc_id)
        return messages


def compute_sha256(gcs_uri: str, gcs_client=None) -> Optional[str]:
    """Compute SHA256 of a GCS blob for doc dedup."""
    try:
        from google.cloud import storage

        bucket_name, blob_name = _split_gcs_uri(gcs_uri)
        client = gcs_client or storage.Client()
        blob = client.bucket(bucket_name).blob(blob_name)
        if not blob.exists():
            return None

        sha = hashlib.sha256()
        with tempfile.TemporaryDirectory() as tmpdir:
            local = Path(tmpdir) / "doc.pdf"
            blob.download_to_filename(str(local))
            with open(local, "rb") as f:
                while chunk := f.read(8192):
                    sha.update(chunk)
        return sha.hexdigest()
    except Exception:
        logger.warning("Failed to compute SHA256 for %s", gcs_uri, exc_info=True)
        return None


def _download_pdf(gcs_uri: str, tmpdir: str, doc_id: str, gcs_client=None) -> Path:
    """Download a PDF from GCS. Supports local dev path."""
    if os.getenv("IRIS_LOCAL_DEV", "0") == "1":
        path = Path(gcs_uri)
        resolved = path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Local file not found: {resolved}")
        return resolved

    from google.cloud import storage

    bucket_name, blob_name = _split_gcs_uri(gcs_uri)
    client = gcs_client or storage.Client()
    blob = client.bucket(bucket_name).blob(blob_name)
    local = Path(tmpdir) / f"{doc_id}.pdf"
    blob.download_to_filename(str(local))
    return local


def _upload_blob(local_path: Path, bucket_name: str, blob_name: str, gcs_client=None):
    """Upload a file to GCS."""
    if os.getenv("IRIS_LOCAL_DEV", "0") == "1":
        return

    from google.cloud import storage

    client = gcs_client or storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path))


def _split_gcs_uri(uri: str) -> tuple[str, str]:
    """Split gs://bucket/path into (bucket, path)."""
    if not uri.startswith("gs://"):
        raise ValueError(f"Not a GCS URI: {uri}")
    parts = uri[5:].split("/", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""
