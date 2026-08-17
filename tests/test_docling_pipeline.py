"""Docling pipeline integration tests — parse/route/chunk/store against trueassort/.

Run via: .venv\\Scripts\\python -m pytest tests/test_docling_pipeline.py -v -s

Marked `integration` — excluded from the Tier 0 gate (`-m "not live and not
integration"`) because it parses real PDFs with Docling and takes minutes.
"""
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
    retrieved = store.get_by_doc(doc_id, "test")

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
        "retrieved": len(retrieved),
        "parse_time_s": round(parse_time, 1),
    }


@pytest.mark.integration
class TestDoclingPipelineTrueassort(unittest.TestCase):
    """Parse -> route -> chunk -> store roundtrip on the golden corpus."""

    @classmethod
    def setUpClass(cls):
        print("\nLoading DoclingParser...")
        cls.parser = DoclingParser()
        print("Ready.")

    def test_representative_docs(self):
        # Cover the four routing tiers via representative corpus docs.
        docs = ["doc_001", "doc_004", "doc_005", "doc_006"]
        for doc_id in docs:
            pdf = TRUEASSORT / f"{doc_id}.pdf"
            self.assertTrue(pdf.exists(), f"Missing {pdf}")
            s = run_pipeline(pdf, self.parser)
            self.assertGreater(s["elements"], 0, f"{doc_id} no elements")
            self.assertGreater(s["chunks"], 0, f"{doc_id} no chunks")
            self.assertEqual(s["chunks"], s["retrieved"], f"{doc_id} store mismatch")
            print(
                f"  {s['doc']}: pages={s['pages']} elements={s['elements']} "
                f"chunks={s['chunks']} vlm={s['vlm_calls']} parse={s['parse_time_s']}s"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
