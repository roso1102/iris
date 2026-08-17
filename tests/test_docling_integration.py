"""Docling pipeline integration tests — run against trueassort/ golden corpus.

Validates the production Docling parse -> VLM route -> chunk pipeline against
the ground-truth labels in `trueassort/document_routing.csv` (201 labeled pages
across doc_001..doc_008).

Marked `integration` — excluded from the Tier 0 gate (`-m "not live and not
integration"`) because each test parses real PDFs with Docling and takes
minutes. Run explicitly when validating the pipeline locally.
"""
import os
import sys
import csv
import unittest
from pathlib import Path
from collections import Counter

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))

from services.common.ingestion.parser import DoclingParser
from services.common.ingestion.models import ElementType, RouteDecision
from services.common.ingestion.vlm_router import MockVlmRouter, MIN_TEXT_CHARS
from services.common.ingestion.chunker import chunk_routed
from services.common.ingestion.store import MemoryChunkStore
from services.common.ingestion.preflight import check_pdf

TRUEASSORT = Path(__file__).resolve().parents[1] / "trueassort"
CSV_PATH = TRUEASSORT / "document_routing.csv"


def _load_labels() -> list[dict]:
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.integration
class TestDoclingTrueassortCorpus(unittest.TestCase):
    """Every trueassort PDF parses, routes, chunks, and matches page counts."""

    @classmethod
    def setUpClass(cls):
        print("\nLoading DoclingParser (first run downloads models)...")
        cls.parser = DoclingParser()
        cls.labels = _load_labels()
        print("DoclingParser ready.")

    def test_all_docs_parse_and_chunk(self):
        """Each doc_00X.pdf yields elements, and pipeline produces chunks."""
        pdfs = sorted(TRUEASSORT.glob("doc_*.pdf"))
        self.assertEqual(len(pdfs), 8, f"Expected 8 corpus docs, got {len(pdfs)}")

        for pdf in pdfs:
            doc_id = pdf.stem
            meta = check_pdf(pdf)
            elements = self.parser.parse(pdf)
            router = MockVlmRouter()
            routed = router.route(elements)
            chunks = chunk_routed(routed, tenant_id="test", doc_id=doc_id)

            self.assertGreater(len(elements), 0, f"{doc_id} produced no elements")
            self.assertGreater(len(chunks), 0, f"{doc_id} produced no chunks")
            print(f"  {doc_id}: pages={meta['page_count']} elements={len(elements)} chunks={len(chunks)}")

    def test_page_counts_match_csv(self):
        """Each PDF's physical page count must equal the CSV's per-doc page count."""
        from collections import defaultdict
        expected_pages = defaultdict(int)
        for row in self.labels:
            expected_pages[row["doc_id"]] += 1

        for doc_id, expected in sorted(expected_pages.items()):
            pdf = TRUEASSORT / f"{doc_id}.pdf"
            meta = check_pdf(pdf)
            self.assertEqual(
                meta["page_count"], expected,
                f"{doc_id}: PDF has {meta['page_count']} pages, CSV says {expected}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
