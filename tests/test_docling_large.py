"""Docling CPU pipeline tests — run the full trueassort/ corpus on CPU.

Run: .venv\\Scripts\\python -m pytest tests/test_docling_large.py -v -s

Marked `integration` — excluded from the Tier 0 gate (`-m "not live and not
integration"`) because it parses 8 real PDFs with Docling and takes minutes.
"""
import os
import sys
import time
import unittest
from pathlib import Path
from collections import Counter

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))

from services.common.ingestion.parser import DoclingParser
from services.common.ingestion.models import RouteDecision
from services.common.ingestion.vlm_router import MockVlmRouter, MIN_TEXT_CHARS
from services.common.ingestion.chunker import chunk_routed
from services.common.ingestion.store import MemoryChunkStore
from services.common.ingestion.preflight import check_pdf

TRUEASSORT = Path(__file__).resolve().parents[1] / "trueassort"


def run_pipeline(pdf: Path, parser: DoclingParser) -> dict:
    doc_id = pdf.stem
    meta = check_pdf(pdf)

    t0 = time.time()
    elements = parser.parse(pdf)
    parse_time = time.time() - t0

    router = MockVlmRouter()
    routed = router.route(elements)
    route_counts = Counter(r.decision.value for r in routed)

    chunks = chunk_routed(routed, tenant_id="test", doc_id=doc_id)
    store = MemoryChunkStore()
    store.upsert_batch(chunks)

    chars = [e.char_count for e in elements]
    above = sum(1 for c in chars if c >= MIN_TEXT_CHARS)

    return {
        "doc": doc_id,
        "pages": meta["page_count"],
        "elements": len(elements),
        ">=150 chars": above,
        "<150 chars": len(elements) - above,
        "route_docling_text": route_counts.get("docling_text", 0),
        "route_vlm_full": route_counts.get("vlm_full_page", 0),
        "route_vlm_table": route_counts.get("vlm_table", 0),
        "route_vlm_picture": route_counts.get("vlm_picture", 0),
        "vlm_calls": router.vlm_calls,
        "chunks": len(chunks),
        "parse_time_s": round(parse_time, 1),
    }


@pytest.mark.integration
class TestDoclingLargeCPU(unittest.TestCase):
    """Parse the full 8-doc corpus on CPU and verify no doc is empty."""

    @classmethod
    def setUpClass(cls):
        print("\nLoading DoclingParser (CPU mode, 8 threads)...")
        cls.parser = DoclingParser(use_cpu=True, num_threads=8)
        print("Ready.")

    def test_all_trueassort_docs(self):
        pdfs = sorted(TRUEASSORT.glob("doc_*.pdf"))
        self.assertEqual(len(pdfs), 8)

        for pdf in pdfs:
            s = run_pipeline(pdf, self.parser)
            self.assertGreater(s["elements"], 0, f"{s['doc']} produced no elements")
            self.assertGreater(s["chunks"], 0, f"{s['doc']} produced no chunks")
            print(
                f"  {s['doc']}: pages={s['pages']} elements={s['elements']} "
                f"chunks={s['chunks']} vlm={s['vlm_calls']} parse={s['parse_time_s']}s"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
