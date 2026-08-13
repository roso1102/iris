"""Layer 2 — local full-pipeline wiring test (zero network, zero cost).

Exercises the exact production objects end to end:
  Pub/Sub envelope decode -> IngestionPipeline -> router -> chunker -> store

Uses MemoryChunkStore + MockModelProvider (deterministic 768-d vectors and
pre-written markdown/OCR strings). No Vertex, no Qdrant, no GCS.
"""

import base64
import json
import os
import unittest
from pathlib import Path

# Must be set before importing the worker (which builds a pipeline lazily).
os.environ["MODEL_BACKEND"] = "mock"
os.environ["GCP_PROJECT"] = "test-project"
os.environ.pop("QDRANT_URL", None)

from services.common.ingestion.models import ElementType, ParsedElement, RouteDecision
from services.common.ingestion.chunker import chunk_routed
from services.common.ingestion.store import MemoryChunkStore
from services.common.ingestion.vlm_router import MockVlmRouter
from services.common.models.mock import MockModelProvider

import importlib.util

_WORKER_PATH = Path(__file__).resolve().parents[1] / "services" / "ingestion-worker" / "app.py"


def _load_worker_module():
    spec = importlib.util.spec_from_file_location("ingestion_worker_app", _WORKER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPubSubEnvelopeDecode(unittest.TestCase):
    """FIX-005 — page_number must survive the Pub/Sub push envelope."""

    @classmethod
    def setUpClass(cls):
        cls.app = _load_worker_module()

    def _decode(self, envelope):
        data, attrs = self.app._decode_pubsub_payload(envelope)
        return data, attrs

    def test_message_data_base64_roundtrip(self):
        payload = {
            "gcs_uri": "gs://iris-raw-pdfs/t/doc_001/pages/page_3.pdf",
            "tenant_id": "t",
            "doc_id": "doc_001",
            "page_number": 3,
            "total_pages": 7,
        }
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        envelope = {"message": {"data": encoded, "attributes": {}}, "subscription": "s"}
        data, _ = self._decode(envelope)
        self.assertEqual(data["page_number"], 3)
        self.assertEqual(data["total_pages"], 7)
        self.assertEqual(data["gcs_uri"], payload["gcs_uri"])

    def test_attributes_fallback(self):
        envelope = {
            "message": {
                "data": "",
                "attributes": {
                    "gcs_uri": "gs://b/x/page_1.pdf",
                    "tenant_id": "t",
                    "doc_id": "d",
                    "page_number": "2",
                    "total_pages": "5",
                },
            }
        }
        data, attrs = self._decode(envelope)
        self.assertEqual(
            self.app._first_present(data, attrs, "page_number"), "2"
        )
        self.assertEqual(
            self.app._first_present(data, attrs, "total_pages"), "5"
        )

    def test_root_level_eventarc_attributes(self):
        envelope = {
            "message": {"data": base64.b64encode(b'{"doc_id":"d"}').decode()},
            "attributes": {"tenant_id": "t", "page_number": "4"},
        }
        data, attrs = self._decode(envelope)
        self.assertEqual(attrs["tenant_id"], "t")
        self.assertEqual(attrs["page_number"], "4")


class TestFullPipelineWiring(unittest.TestCase):
    """Parser -> router -> chunker -> embedder -> MemoryChunkStore."""

    def _run_pipeline(self, elements, page_override=None):
        provider = MockModelProvider(embed_dim=768)
        router = MockVlmRouter()
        routed = router.route(elements)
        chunks = chunk_routed(
            routed,
            tenant_id="tenant-a",
            doc_id="doc_001",
            page_number_override=page_override,
        )
        for c in chunks:
            c.embedding = provider.embed(c.text)
        store = MemoryChunkStore()
        written = store.upsert_batch(chunks)
        return store, chunks, written

    def test_page_number_override_persists_to_store(self):
        """FIX-005 wiring: page_number_override reaches every stored chunk."""
        elements = [
            ParsedElement(
                page_number=1,
                element_type=ElementType.TEXT,
                text="A " * 200,
                bbox=[0.0, 0.0, 1.0, 1.0],
            )
        ]
        store, chunks, written = self._run_pipeline(elements, page_override=3)
        self.assertEqual(written, len(chunks))
        self.assertGreater(len(chunks), 0)
        self.assertTrue(all(c.page_number == 3 for c in chunks))
        self.assertTrue(all(len(c.embedding) == 768 for c in chunks))

    def test_clean_text_produces_zero_vlm_and_stores_chunks(self):
        elements = [
            ParsedElement(
                page_number=1,
                element_type=ElementType.TEXT,
                text="Clean gazette paragraph. " * 40,
                bbox=[0.05, 0.05, 0.95, 0.5],
            )
        ]
        store, chunks, written = self._run_pipeline(elements)
        self.assertGreater(written, 0)
        self.assertEqual(
            {c.source for c in chunks}, {RouteDecision.DOCLING_TEXT}
        )


if __name__ == "__main__":
    unittest.main()
