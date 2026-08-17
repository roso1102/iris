"""Phase 1.0/2.5 integration tests — run against trueassort/ golden corpus.

Covers preflight rejection (oversized/corrupt) and per-document pipeline
roundtrips against the ground-truth corpus (doc_001..doc_008), cross-checking
against `trueassort/document_routing.csv`.

Marked `integration` — excluded from the Tier 0 gate (`-m "not live and not
integration"`) because it reads real PDF fixtures and takes minutes.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from collections import Counter

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))

from services.common.ingestion.preflight import (
    check_pdf,
    MAX_PAGE_COUNT,
    PreflightError,
)
from services.common.ingestion.models import Chunk, ElementType, ParsedElement, RouteDecision
from services.common.ingestion.vlm_router import MockVlmRouter, MIN_TEXT_CHARS
from services.common.ingestion.chunker import chunk_routed
from services.common.ingestion.store import MemoryChunkStore

TRUEASSORT = Path(__file__).resolve().parents[1] / "trueassort"
CSV_PATH = TRUEASSORT / "document_routing.csv"


def _gen_oversized_pdf(path: Path, pages: int) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as fh:
        writer.write(fh)


def _gen_corrupt_pdf(path: Path) -> None:
    path.write_bytes(b"%PDF-1.4\nbroken trailer junk bytes here")


def _load_labels() -> list[dict]:
    import csv
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.integration
class Test1B_OversizedRejection(unittest.TestCase):
    def test_rejects_600_page_pdf(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp = Path(f.name)
        try:
            _gen_oversized_pdf(tmp, 600)
            with self.assertRaisesRegex(PreflightError, "600 pages"):
                check_pdf(tmp)
        finally:
            tmp.unlink(missing_ok=True)


@pytest.mark.integration
class Test1C_CorruptRejection(unittest.TestCase):
    def test_rejects_corrupt_trailer(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp = Path(f.name)
        try:
            _gen_corrupt_pdf(tmp)
            with self.assertRaises(PreflightError):
                check_pdf(tmp)
        finally:
            tmp.unlink(missing_ok=True)


@pytest.mark.integration
class TestTrueassortCorpus(unittest.TestCase):
    """Every trueassort PDF passes preflight and matches CSV page counts."""

    def test_page_counts_match_csv(self):
        labels = _load_labels()
        expected = Counter(row["doc_id"] for row in labels)
        self.assertEqual(sum(expected.values()), 201)

        pdfs = sorted(TRUEASSORT.glob("doc_*.pdf"))
        self.assertEqual(len(pdfs), 8)

        for doc_id, count in sorted(expected.items()):
            pdf = TRUEASSORT / f"{doc_id}.pdf"
            meta = check_pdf(pdf)
            self.assertEqual(meta["page_count"], count, f"{doc_id} page mismatch")

    def test_all_docs_produce_chunks(self):
        from services.common.ingestion.parser import DoclingParser

        parser = DoclingParser(use_cpu=True)
        for pdf in sorted(TRUEASSORT.glob("doc_*.pdf")):
            doc_id = pdf.stem
            elements = parser.parse(pdf)
            router = MockVlmRouter()
            routed = router.route(elements)
            chunks = chunk_routed(routed, tenant_id="test", doc_id=doc_id)
            self.assertGreater(len(chunks), 0, f"{doc_id} produced no chunks")


if __name__ == "__main__":
    unittest.main(verbosity=2)
