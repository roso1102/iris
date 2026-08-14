"""Tier 1 integration tests — IngestionPipeline wiring with fakes.

Composes the real production objects with zero-cost fakes:
  MockDocParser -> VLM router -> chunker -> MemoryChunkStore

No real Docling, no VLM API, no GCS, no Qdrant. Verifies that the components
connect correctly: chunk count, page_numbers, tenant isolation, and that the
router produces the expected VLM decisions for table/picture/short-text
elements.

Second class exercises the full `IngestionPipeline.ingest()` entry point with
`_download` mocked to a real tiny PDF so `check_pdf` passes.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.common.ingestion.chunker import chunk_routed
from services.common.ingestion.main import IngestionPipeline, IngestResult
from services.common.ingestion.models import ElementType, RouteDecision
from services.common.ingestion.parser import MockDocParser
from services.common.ingestion.store import MemoryChunkStore
from services.common.ingestion.vlm_router import MockVlmRouter
from services.common.models.mock import MockModelProvider


class TestIngestionPipelineWiring(unittest.TestCase):
    """Parse -> route -> chunk -> store, driven through the production objects."""

    def setUp(self):
        self.store = MemoryChunkStore()
        self.parser = MockDocParser()
        self.router = MockVlmRouter()
        self.pipeline = IngestionPipeline(
            provider=MockModelProvider(),
            store=self.store,
            parser=self.parser,
            router=self.router,
        )

    def test_full_wiring_produces_chunks_with_metadata(self):
        """MockDocParser's 4 elements flow through router -> chunker -> store."""
        elements = self.parser.parse(Path("unused.pdf"))
        self.assertEqual(len(elements), 4)

        routed = self.router.route(elements)
        chunks = chunk_routed(routed, tenant_id="tenant-a", doc_id="doc_001")
        self.assertGreater(len(chunks), 0)

        written = self.store.upsert_batch(chunks)
        self.assertEqual(written, len(chunks))
        stored = self.store.get_by_doc("doc_001", "tenant-a")
        self.assertEqual(len(stored), len(chunks))

    def test_page_numbers_from_parser(self):
        """Elements land on pages 1 and 2 as MockDocParser emits them."""
        elements = self.parser.parse(Path("unused.pdf"))
        routed = self.router.route(elements)
        chunks = chunk_routed(routed, tenant_id="tenant-a", doc_id="doc_001")
        pages = {c.page_number for c in chunks}
        self.assertEqual(pages, {1, 2})

    def test_router_produces_expected_vlm_decisions(self):
        """Table -> VLM_TABLE, Picture -> VLM_PICTURE, short text -> VLM_FULL_PAGE."""
        elements = self.parser.parse(Path("unused.pdf"))
        routed = self.router.route(elements)
        by_element = {r.element.element_type: r.decision for r in routed}
        self.assertEqual(by_element[ElementType.TABLE], RouteDecision.VLM_TABLE)
        self.assertEqual(by_element[ElementType.PICTURE], RouteDecision.VLM_PICTURE)
        # "Scanned header." is < 150 chars -> Signal 4 -> full-page VLM
        self.assertEqual(by_element[ElementType.TEXT], RouteDecision.VLM_FULL_PAGE)

    def test_tenant_isolation(self):
        """Chunks stored under tenant-a never leak to tenant-b."""
        elements = self.parser.parse(Path("unused.pdf"))
        routed = self.router.route(elements)
        chunks = chunk_routed(routed, tenant_id="tenant-a", doc_id="doc_001")
        self.store.upsert_batch(chunks)

        self.assertGreater(len(self.store.get_by_doc("doc_001", "tenant-a")), 0)
        self.assertEqual(self.store.get_by_doc("doc_001", "tenant-b"), [])
        self.assertEqual(self.store.get_by_doc("doc_002", "tenant-a"), [])


class TestIngestEntryPoint(unittest.TestCase):
    """Full IngestionPipeline.ingest() with _download mocked to a real PDF."""

    def setUp(self):
        self.store = MemoryChunkStore()

    def _write_tiny_pdf(self, path: Path) -> None:
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with open(path, "wb") as fh:
            writer.write(fh)

    def test_ingest_returns_result_and_stores_chunks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = Path(tmpdir) / "doc.pdf"
            self._write_tiny_pdf(pdf)

            pipeline = IngestionPipeline(
                provider=MockModelProvider(),
                store=self.store,
                parser=MockDocParser(),
                router=MockVlmRouter(),
            )

            with patch.object(pipeline, "_download", return_value=pdf) as mock_dl:
                result = pipeline.ingest(
                    gcs_uri="gs://bucket/doc.pdf",
                    tenant_id="tenant-a",
                    doc_id="doc_001",
                )
            mock_dl.assert_called_once()

            self.assertIsInstance(result, IngestResult)
            self.assertEqual(result.doc_id, "doc_001")
            self.assertGreater(result.chunk_count, 0)
            self.assertGreaterEqual(result.vlm_calls, 1)  # table + picture + short text
            self.assertGreater(
                len(self.store.get_by_doc("doc_001", "tenant-a")), 0
            )

    def test_ingest_rejects_missing_fields(self):
        pipeline = IngestionPipeline(
            provider=MockModelProvider(),
            store=self.store,
            parser=MockDocParser(),
            router=MockVlmRouter(),
        )
        with self.assertRaises(Exception) as ctx:
            pipeline.ingest("", "", "")
        from services.common.ingestion.main import RejectError

        self.assertIsInstance(ctx.exception, RejectError)


if __name__ == "__main__":
    unittest.main()
