"""Ingestion orchestrator (ACTIONPLAN Tasks 1.2-1.9).

Order: preflight -> download -> parse -> route -> chunk -> embed -> store.
Returns an ack/retry decision for the Pub/Sub handler.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from services.common.ingestion.chunker import chunk_routed
from services.common.ingestion.models import Chunk
from services.common.ingestion.parser import DoclingParser, MockDocParser
from services.common.ingestion.preflight import PreflightError, check_pdf
from services.common.ingestion.store import ChunkStore, get_chunk_store
from services.common.ingestion.vlm_router import FitzPageRenderer, MockVlmRouter, RouterVlmRouter
from services.common.models.base import ModelProvider
from services.common.models.factory import get_model_provider

logger = logging.getLogger(__name__)

_ALLOWED_URI_PATTERN = re.compile(r"^gs://[a-z0-9][a-z0-9._-]{2,61}/.+$")


class RejectError(Exception):
    """Payload must be rejected forever (never queued / straight to DLQ)."""


class RetryError(Exception):
    """Transient failure; Pub/Sub should redeliver (up to 3 attempts)."""


@dataclass
class IngestResult:
    doc_id: str
    tenant_id: str
    page_count: int
    chunk_count: int
    vlm_calls: int


class IngestionPipeline:
    def __init__(
        self,
        provider: Optional[ModelProvider] = None,
        store: Optional[ChunkStore] = None,
        parser=None,
        router=None,
        gcs_client=None,
        bucket: Optional[str] = None,
    ) -> None:
        self._provider = provider or get_model_provider()
        self._store = store or get_chunk_store()
        self._parser = parser or self._default_parser()
        self._router = router or self._default_router()
        self._gcs = gcs_client
        self._bucket = bucket or os.getenv("GCS_RAW_BUCKET", "iris-raw-pdfs")

    @staticmethod
    def _default_parser():
        backend = os.getenv("MODEL_BACKEND", "vertex").lower()
        if backend == "mock":
            return MockDocParser()
        return DoclingParser()

    def _default_router(self):
        backend = os.getenv("MODEL_BACKEND", "vertex").lower()
        if backend == "mock":
            return MockVlmRouter()
        return RouterVlmRouter(
            provider=self._provider,
            renderer=FitzPageRenderer(),
        )

    def ingest(
        self,
        gcs_uri: str,
        tenant_id: str,
        doc_id: str,
        page_number: Optional[int] = None,
    ) -> IngestResult:
        """Full pipeline for one uploaded document or single-page blob."""
        if not gcs_uri or not tenant_id or not doc_id:
            raise RejectError("Missing gcs_uri/tenant_id/doc_id in message")

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = self._download(gcs_uri, tmpdir, doc_id)

            try:
                meta = check_pdf(local_path)
            except PreflightError as exc:
                # Reject forever: oversized or corrupt payload never enters pipeline.
                raise RejectError(str(exc)) from exc

            vlm_calls_before = getattr(self._router, "vlm_calls", 0)

            elements = self._parser.parse(local_path)
            routed = self._router.route(elements, pdf_path=str(local_path))
            chunks = chunk_routed(
                routed,
                tenant_id=tenant_id,
                doc_id=doc_id,
                page_number_override=page_number,
            )

            self._embed(chunks)
            written = self._store.upsert_batch(chunks)

            return IngestResult(
                doc_id=doc_id,
                tenant_id=tenant_id,
                page_count=meta["page_count"],
                chunk_count=written,
                vlm_calls=getattr(self._router, "vlm_calls", 0) - vlm_calls_before,
            )

    def _download(self, gcs_uri: str, tmpdir: str, doc_id: str) -> Path:
        if os.getenv("IRIS_LOCAL_DEV", "0") == "1":
            path = Path(gcs_uri)
            if not path.is_absolute():
                raise RejectError(f"Local dev: path must be absolute: {gcs_uri}")
            resolved = path.resolve()
            allowed_root = Path(__file__).resolve().parents[3] / "trueassort"
            if not str(resolved).startswith(str(allowed_root)):
                raise RejectError(f"Local dev: path outside trueassort: {gcs_uri}")
            if not resolved.exists():
                raise RetryError(f"Local file not found: {resolved}")
            return resolved

        if not _ALLOWED_URI_PATTERN.match(gcs_uri):
            raise RejectError(f"Invalid GCS URI: {gcs_uri}")

        from google.cloud import storage

        bucket_name, blob_name = _split_gcs_uri(gcs_uri)
        client = self._gcs or storage.Client()
        blob = client.bucket(bucket_name).blob(blob_name)
        local = Path(tmpdir) / f"{doc_id}.pdf"
        blob.download_to_filename(str(local))
        return local

    def _embed(self, chunks: List[Chunk]) -> None:
        for chunk in chunks:
            try:
                chunk.embedding = self._provider.embed(chunk.text)
            except Exception:
                logger.warning("Embedding failed for chunk %s, using zero vector fallback", chunk.id, exc_info=True)
                chunk.embedding = [0.0] * 768


def _split_gcs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise RejectError(f"Not a GCS URI: {uri}")
    parts = uri[5:].split("/", 1)
    return parts[0], parts[1]
