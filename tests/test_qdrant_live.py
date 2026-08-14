"""Tier 2 live smoke tests — Qdrant connectivity and read/write path.

Run only with a reachable Qdrant URL. The production Qdrant VM is private
(10.0.0.5:6333), so open an IAP SSH tunnel from the local machine first:

    gcloud compute ssh qdrant-1 \
      --zone=asia-south1-b --project=naturepivot-rag \
      --tunnel-through-iap -- -L 6333:localhost:6333 -N

Then set QDRANT_URL=http://localhost:6333 when running these tests.
"""

import os
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))

from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from services.common.ingestion.store import QdrantChunkStore

_RUN = os.getenv("RUN_QDRANT_LIVE_TESTS") == "1"
_URL = os.getenv("QDRANT_URL", "").strip()

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not (_RUN and _URL),
        reason="Set RUN_QDRANT_LIVE_TESTS=1 and QDRANT_URL to run Qdrant live smoke tests.",
    ),
]


def _store() -> QdrantChunkStore:
    return QdrantChunkStore(url=_URL)


def _chunk(doc_id: str) -> Chunk:
    return Chunk(
        tenant_id="tier2_smoke_tenant",
        doc_id=doc_id,
        page_number=1,
        element_type=ElementType.TEXT,
        text="Tier 2 Qdrant live smoke test chunk.",
        bbox=[0.1, 0.1, 0.5, 0.4],
        source=RouteDecision.DOCLING_TEXT,
        embedding=[0.1] * 768,
    )


def test_collection_health():
    store = _store()
    collection = store._client.get_collection(collection_name=store._collection)
    status = str(getattr(collection, "status", "")).lower()
    assert status == "green", f"Qdrant collection not green: {status}"


def test_roundtrip_upsert_search_delete():
    doc_id = f"tier2_smoke_{uuid.uuid4().hex[:12]}"
    store = _store()
    chunk = _chunk(doc_id)
    try:
        written = store.upsert_batch([chunk])
        assert written == 1

        results = store.search_dense(
            chunk.embedding or [],
            tenant_id=chunk.tenant_id,
            doc_ids=[doc_id],
            limit=1,
        )
        assert len(results) == 1
        assert results[0][0] == chunk.id
    finally:
        deleted = store.delete_by_doc(doc_id, tenant_id=chunk.tenant_id)
        assert deleted >= 1
