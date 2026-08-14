"""Phase 1.0 Docling Integration Tests - uses DoclingParser + VLM router.

Run via: .venv\Scripts\python -m pytest tests/test_docling_pipeline.py -v -s

Marked `integration` — excluded from the Tier 0 gate (`-m "not live and not
integration"`) because each test parses a real PDF with Docling and takes
minutes.
"""
import os, sys, time, unittest
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

TEST_DOCS = Path(__file__).resolve().parents[1] / "test-docs"


def _box(title, stats):
    w = 64
    print("\n+" + "-" * w + "+")
    print(f"| {title[:w-2]:<{w}}|")
    print("+" + "-" * w + "+")
    for k, v in stats.items():
        s = f"{k:<38} {str(v):<24}"
        print(f"| {s[:w]:<{w}}|")
    print("+" + "-" * w + "+")


def run_pipeline(doc_name, parser):
    pdf_path = TEST_DOCS / doc_name
    meta = check_pdf(pdf_path)

    t0 = time.time()
    elements = parser.parse(pdf_path)
    parse_time = time.time() - t0

    router = MockVlmRouter()
    routed = router.route(elements)
    route_counts = Counter()
    for r in routed:
        route_counts[r.decision.value] += 1

    chunks = chunk_routed(routed, tenant_id="test", doc_id=doc_name)
    store = MemoryChunkStore()
    store.upsert_batch(chunks)

    elem_types = Counter(e.element_type.value for e in elements)
    chars = [e.char_count for e in elements]
    above = sum(1 for c in chars if c >= MIN_TEXT_CHARS)
    below = sum(1 for c in chars if c < MIN_TEXT_CHARS)

    return {
        "doc": doc_name, "pages": meta["page_count"],
        "size_kb": round(meta["file_size_bytes"] / 1024, 1),
        "elements": len(elements), "elem_types": dict(elem_types),
        ">=150 chars": above, "<150 chars": below,
        "route_docling_text": route_counts.get("docling_text", 0),
        "route_vlm_full": route_counts.get("vlm_full_page", 0),
        "route_vlm_table": route_counts.get("vlm_table", 0),
        "route_vlm_picture": route_counts.get("vlm_picture", 0),
        "vlm_calls": router.vlm_calls, "chunks": len(chunks),
        "parse_time_s": round(parse_time, 1),
    }


@pytest.mark.integration
class TestDoclingPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\nLoading DoclingParser...")
        cls.parser = DoclingParser()
        print("Ready.")

    def test_a_hindi_written(self):
        """Test 1-E: 7-page Hindi PDF with scanned/low-text pages."""
        s = run_pipeline("testhindiwritten.pdf", self.parser)
        _box("Test 1-E: Docling -- testhindiwritten.pdf (7 pages)", {
            "Pages": s["pages"], "Docling elements": s["elements"],
            "Element types": str(s["elem_types"]),
            "Elements >= 150 chars": s[">=150 chars"],
            "Elements < 150 chars": s["<150 chars"],
            "Route DOCLING_TEXT (zero cost)": s["route_docling_text"],
            "Route VLM_FULL_PAGE (cost)": s["route_vlm_full"],
            "Route VLM_TABLE": s["route_vlm_table"],
            "Route VLM_PICTURE": s["route_vlm_picture"],
            "Total VLM calls": s["vlm_calls"],
            "VLM %": f"{s['vlm_calls'] / max(s['elements'], 1) * 100:.1f}%",
            "Chunks": s["chunks"], "Parse time (s)": s["parse_time_s"],
        })
        self.assertGreater(s["elements"], 0)
        self.assertGreater(s["route_vlm_full"], 0, "Low-text pages must trigger VLM")
        print(f"\n  PASS: 7-page Hindi doc, {s['elements']} elements via Docling, {s['vlm_calls']} VLM calls.")

    def test_b_assam_gazette(self):
        """Test 1-D: 24-page chart/table-heavy gazette."""
        s = run_pipeline("Assam_CHARTS_TABLES.pdf", self.parser)
        _box("Test 1-D: Docling -- Assam_CHARTS_TABLES.pdf (24 pages)", {
            "Pages": s["pages"], "Docling elements": s["elements"],
            "Element types": str(s["elem_types"]),
            "Elements >= 150 chars": s[">=150 chars"],
            "Elements < 150 chars": s["<150 chars"],
            "Route DOCLING_TEXT (zero cost)": s["route_docling_text"],
            "Route VLM_FULL_PAGE (cost)": s["route_vlm_full"],
            "Route VLM_TABLE": s["route_vlm_table"],
            "Route VLM_PICTURE": s["route_vlm_picture"],
            "Total VLM calls": s["vlm_calls"],
            "VLM %": f"{s['vlm_calls'] / max(s['elements'], 1) * 100:.1f}%",
            "Chunks": s["chunks"], "Parse time (s)": s["parse_time_s"],
        })
        self.assertGreater(s["elements"], 0)
        print(f"\n  PASS: Assam gazette via Docling, {s['elements']} elements, {s['chunks']} chunks.")

    def test_c_scanned_eng(self):
        """Test 1-F: 27-page dense government document."""
        s = run_pipeline("scanned_eng.pdf", self.parser)
        _box("Test 1-A+1-F: Docling -- scanned_eng.pdf (27 pages)", {
            "Pages": s["pages"], "Docling elements": s["elements"],
            "Element types": str(s["elem_types"]),
            "Elements >= 150 chars": s[">=150 chars"],
            "Elements < 150 chars": s["<150 chars"],
            "Route DOCLING_TEXT (zero cost)": s["route_docling_text"],
            "Route VLM_FULL_PAGE (cost)": s["route_vlm_full"],
            "Route VLM_TABLE": s["route_vlm_table"],
            "Route VLM_PICTURE": s["route_vlm_picture"],
            "Total VLM calls": s["vlm_calls"],
            "VLM %": f"{s['vlm_calls'] / max(s['elements'], 1) * 100:.1f}%",
            "Chunks": s["chunks"], "Parse time (s)": s["parse_time_s"],
        })
        self.assertGreater(s["route_docling_text"], 0, "Must have zero-cost DOCLING_TEXT routes")
        print(f"\n  PASS: {s['route_docling_text']} elements zero-cost, {s['vlm_calls']} VLM calls.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
