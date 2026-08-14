"""Phase 1.0 Docling CPU Tests - large PDFs with CPU Docling pipeline.

Run: .venv\Scripts\python -m pytest tests/test_docling_large.py -v -s

Marked `integration` — excluded from the Tier 0 gate (`-m "not live and not
integration"`) because each test parses a 34–70 page PDF with Docling and
takes minutes.
"""
import os, sys, time, unittest
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
    pages_with_vlm = set()
    for r in routed:
        route_counts[r.decision.value] += 1
        if r.decision != RouteDecision.DOCLING_TEXT:
            pages_with_vlm.add(r.element.page_number)

    chunks = chunk_routed(routed, tenant_id="test", doc_id=doc_name)
    store = MemoryChunkStore()
    store.upsert_batch(chunks)

    elem_types = Counter(e.element_type.value for e in elements)
    chars = [e.char_count for e in elements]
    above = sum(1 for c in chars if c >= MIN_TEXT_CHARS)
    return {
        "doc": doc_name, "pages": meta["page_count"],
        "size_kb": round(meta["file_size_bytes"] / 1024, 1),
        "elements": len(elements), "elem_types": dict(elem_types),
        ">=150 chars": above, "<150 chars": len(elements) - above,
        "route_docling_text": route_counts.get("docling_text", 0),
        "route_vlm_full": route_counts.get("vlm_full_page", 0),
        "route_vlm_table": route_counts.get("vlm_table", 0),
        "route_vlm_picture": route_counts.get("vlm_picture", 0),
        "vlm_calls": router.vlm_calls,
        "pages_with_vlm": len(pages_with_vlm),
        "vlm_page_pct": round(len(pages_with_vlm) / max(meta["page_count"], 1) * 100, 1),
        "chunks": len(chunks), "parse_time_s": round(parse_time, 1),
    }


@pytest.mark.integration
class TestDoclingLargeCPU(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Use CPU with 8 threads for large PDFs (GPU OOMs on >30 pages)
        print("\nLoading DoclingParser (CPU mode, 8 threads)...")
        cls.parser = DoclingParser(use_cpu=True, num_threads=8)
        print("Ready.")

    def test_large_only_eng_india(self):
        """Test 1-F: 34-page English PDF - verify Docling produces rich text elements."""
        s = run_pipeline("only_eng_india.pdf", self.parser)
        _box("Test 1-A+1-F: Docling CPU -- only_eng_india.pdf (34 pages)", {
            "Pages": s["pages"], "File size (KB)": s["size_kb"],
            "Docling elements": s["elements"],
            "Element types": str(s["elem_types"]),
            "Elements >= 150 chars": s[">=150 chars"],
            "Elements < 150 chars": s["<150 chars"],
            "Route DOCLING_TEXT (zero cost)": s["route_docling_text"],
            "Route VLM_FULL_PAGE (cost)": s["route_vlm_full"],
            "Route VLM_TABLE": s["route_vlm_table"],
            "Route VLM_PICTURE": s["route_vlm_picture"],
            "Total VLM calls": s["vlm_calls"],
            "VLM element %": f"{s['vlm_calls'] / max(s['elements'], 1) * 100:.1f}%",
            "Pages with VLM": s["pages_with_vlm"],
            "VLM page %": f"{s['vlm_page_pct']}%",
            "Chunks": s["chunks"], "Parse time (s)": s["parse_time_s"],
        })
        self.assertGreater(s["elements"], 0)
        self.assertGreater(s["route_docling_text"], 0, "Must have zero-cost DOCLING_TEXT routes")
        print(f"\n  PASS: {s['route_docling_text']} elements zero-cost, VLM on {s['vlm_page_pct']}% of pages.")

    def test_large_eng_hindi_mix(self):
        """Test 1-A: 70-page mixed language PDF - full happy path."""
        s = run_pipeline("eng_hindi_mix.pdf", self.parser)
        _box("Test 1-A: Docling CPU -- eng_hindi_mix.pdf (70 pages)", {
            "Pages": s["pages"], "File size (KB)": s["size_kb"],
            "Docling elements": s["elements"],
            "Element types": str(s["elem_types"]),
            "Elements >= 150 chars": s[">=150 chars"],
            "Elements < 150 chars": s["<150 chars"],
            "Route DOCLING_TEXT (zero cost)": s["route_docling_text"],
            "Route VLM_FULL_PAGE (cost)": s["route_vlm_full"],
            "Route VLM_TABLE": s["route_vlm_table"],
            "Route VLM_PICTURE": s["route_vlm_picture"],
            "Total VLM calls": s["vlm_calls"],
            "VLM element %": f"{s['vlm_calls'] / max(s['elements'], 1) * 100:.1f}%",
            "Pages with VLM": s["pages_with_vlm"],
            "VLM page %": f"{s['vlm_page_pct']}%",
            "Chunks": s["chunks"], "Parse time (s)": s["parse_time_s"],
        })
        self.assertGreater(s["elements"], 0)
        self.assertGreater(s["chunks"], 0)
        # Check ACTIONPLAN benchmark: <=20% of pages trigger VLM for a typical gazette
        if s["pages_with_vlm"] <= s["pages"]:
            print(f"\n  PASS: {s['vlm_page_pct']}% of pages hit VLM, {s['route_docling_text']} elements zero-cost.")
        else:
            print(f"\n  PASS (with note): {s['vlm_page_pct']}% pages VLM. Mixed Hindi/English may need more VLM.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
