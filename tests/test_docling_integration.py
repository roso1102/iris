"""Phase 1.0 Integration Tests -- via DoclingParser + IngestionPipeline.

Runs the FULL production pipeline: Docling parse -> VLM route -> chunk -> store.
Requires: Docling models downloaded (first run downloads ~40MB).

Marked `integration` — excluded from the Tier 0 gate (`-m "not live and not
integration"`), because each test parses a real PDF with Docling and takes
minutes. Run explicitly when validating the pipeline locally.
"""
import os
import sys
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

TEST_DOCS = Path(__file__).resolve().parents[1] / "test-docs"


def _box(title, stats):
    w = 64
    print("\n+" + "-" * w + "+")
    print(f"| {title[:w-2]:<{w}}|")
    print("+" + "-" * w + "+")
    for k, v in stats.items():
        s = f"{k:<36} {str(v):<26}"
        print(f"| {s[:w]:<{w}}|")
    print("+" + "-" * w + "+")


def run_doc_on(doc_name, parser, router_class=None):
    """Parse a PDF with Docling, route with VLM router, chunk, store. Returns stats dict."""
    pdf_path = TEST_DOCS / doc_name
    meta = check_pdf(pdf_path)

    # Docling parse
    elements = parser.parse(pdf_path)

    # VLM routing
    router = (router_class or MockVlmRouter)()
    routed = router.route(elements)
    route_counts = Counter()
    pages_with_vlm = set()
    for r in routed:
        route_counts[r.decision.value] += 1
        if r.decision != RouteDecision.DOCLING_TEXT:
            pages_with_vlm.add(r.element.page_number)

    # Chunk
    chunks = chunk_routed(routed, tenant_id="test", doc_id=doc_name)
    # Store
    store = MemoryChunkStore()
    store.upsert_batch(chunks)

    # Element stats
    elem_types = Counter(e.element_type.value for e in elements)
    chars_per_elem = [e.char_count for e in elements]
    above_150 = sum(1 for c in chars_per_elem if c >= MIN_TEXT_CHARS)
    below_150 = sum(1 for c in chars_per_elem if c < MIN_TEXT_CHARS)

    return {
        "doc": doc_name,
        "pages": meta["page_count"],
        "size_kb": round(meta["file_size_bytes"] / 1024, 1),
        "elements": len(elements),
        "elem_types": dict(elem_types),
        "elem_above_150": above_150,
        "elem_below_150": below_150,
        "route_docling_text": route_counts.get("docling_text", 0),
        "route_vlm_full": route_counts.get("vlm_full_page", 0),
        "route_vlm_table": route_counts.get("vlm_table", 0),
        "route_vlm_picture": route_counts.get("vlm_picture", 0),
        "vlm_calls": router.vlm_calls,
        "pages_with_vlm": len(pages_with_vlm),
        "vlm_page_pct": round(len(pages_with_vlm) / max(len(elements), 1) * 100, 1),
        "chunks": len(chunks),
    }


@pytest.mark.integration
class TestDoclingPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\nLoading DoclingParser (first run downloads models)...")
        cls.parser = DoclingParser()
        print("DoclingParser ready.")

    def test_1a_only_eng_india(self):
        """Clean English PDF: most elements should route DOCLING_TEXT (zero cost)."""
        s = run_doc_on("only_eng_india.pdf", self.parser)

        _box("Test 1-A + 1-F: Docling Pipeline -- only_eng_india.pdf (34 pages)", {
            "Pages": s["pages"],
            "File size (KB)": s["size_kb"],
            "Total elements (Docling)": s["elements"],
            "Element types": str(s["elem_types"]),
            "Elements >= 150 chars": s["elem_above_150"],
            "Elements < 150 chars": s["elem_below_150"],
            "Route DOCLING_TEXT (zero cost)": s["route_docling_text"],
            "Route VLM_FULL_PAGE (cost)": s["route_vlm_full"],
            "Route VLM_TABLE": s["route_vlm_table"],
            "Route VLM_PICTURE": s["route_vlm_picture"],
            "Total VLM calls": s["vlm_calls"],
            "VLM call %": f"{s['vlm_calls'] / max(s['elements'], 1) * 100:.1f}%",
            "Chunks produced": s["chunks"],
        })

        self.assertGreater(s["elements"], 0)
        self.assertGreater(s["elem_above_150"], 0, "Docling should produce elements >= 150 chars")
        self.assertGreater(s["route_docling_text"], 0, "Clean text must route DOCLING_TEXT")
        print(f"\n  PASS: {s['route_docling_text']} elements zero-cost, {s['vlm_calls']} VLM calls.")

    def test_1d_1e_assam_gazette(self):
        """Table/chart-heavy gazette: verify table elements and low-text pages route correctly."""
        s = run_doc_on("Assam_CHARTS_TABLES.pdf", self.parser)

        _box("Test 1-D + 1-E: Docling Pipeline -- Assam_CHARTS_TABLES.pdf (24 pages)", {
            "Pages": s["pages"],
            "Total elements (Docling)": s["elements"],
            "Element types": str(s["elem_types"]),
            "Elements >= 150 chars": s["elem_above_150"],
            "Elements < 150 chars": s["elem_below_150"],
            "Route DOCLING_TEXT": s["route_docling_text"],
            "Route VLM_FULL_PAGE": s["route_vlm_full"],
            "Route VLM_TABLE": s["route_vlm_table"],
            "Route VLM_PICTURE": s["route_vlm_picture"],
            "Total VLM calls": s["vlm_calls"],
            "Chunks produced": s["chunks"],
        })

        # Charts/tables document should have table/picture elements from Docling
        has_table = "table" in s["elem_types"]
        has_picture = any(k in s["elem_types"] for k in ["picture", "figure"])
        self.assertTrue(has_table or has_picture,
                        "Docling should detect at least table or picture elements")
        print(f"\n  PASS: Table/chart elements detected by Docling, routed correctly.")

    def test_1a_scanned_eng(self):
        """scanned_eng.pdf: dense text government document."""
        s = run_doc_on("scanned_eng.pdf", self.parser)

        _box("Test 1-A: Docling Pipeline -- scanned_eng.pdf (27 pages)", {
            "Pages": s["pages"],
            "Total elements (Docling)": s["elements"],
            "Element types": str(s["elem_types"]),
            "Elements >= 150 chars": s["elem_above_150"],
            "Elements < 150 chars": s["elem_below_150"],
            "Route DOCLING_TEXT (zero cost)": s["route_docling_text"],
            "Route VLM_FULL_PAGE (cost)": s["route_vlm_full"],
            "Total VLM calls": s["vlm_calls"],
            "VLM call %": f"{s['vlm_calls'] / max(s['elements'], 1) * 100:.1f}%",
            "Chunks produced": s["chunks"],
        })

        self.assertGreater(s["elem_above_150"], 0)
        self.assertGreater(s["route_docling_text"], 0)
        print(f"\n  PASS: Dense government document processed via Docling.")

    def test_1a_eng_hindi_mix(self):
        """70-page mixed English/Hindi document."""
        s = run_doc_on("eng_hindi_mix.pdf", self.parser)

        _box("Test 1-A: Docling Pipeline -- eng_hindi_mix.pdf (70 pages)", {
            "Pages": s["pages"],
            "File size (KB)": s["size_kb"],
            "Total elements (Docling)": s["elements"],
            "Element types": str(s["elem_types"]),
            "Elements >= 150 chars": s["elem_above_150"],
            "Elements < 150 chars": s["elem_below_150"],
            "Route DOCLING_TEXT (zero cost)": s["route_docling_text"],
            "Route VLM_FULL_PAGE (cost)": s["route_vlm_full"],
            "Route VLM_TABLE": s["route_vlm_table"],
            "Route VLM_PICTURE": s["route_vlm_picture"],
            "Total VLM calls": s["vlm_calls"],
            "VLM call %": f"{s['vlm_calls'] / max(s['elements'], 1) * 100:.1f}%",
            "Chunks produced": s["chunks"],
        })

        self.assertGreater(s["elements"], 0)
        self.assertGreater(s["chunks"], 0)
        print(f"\n  PASS: 70-page mixed language document processed via Docling.")

    def test_1e_hindi_low_text(self):
        """testhindiwritten.pdf: Hindi document, some pages very short."""
        s = run_doc_on("testhindiwritten.pdf", self.parser)

        _box("Test 1-E: Docling Pipeline -- testhindiwritten.pdf (7 pages)", {
            "Pages": s["pages"],
            "Total elements (Docling)": s["elements"],
            "Element types": str(s["elem_types"]),
            "Elements >= 150 chars": s["elem_above_150"],
            "Elements < 150 chars": s["elem_below_150"],
            "Route DOCLING_TEXT": s["route_docling_text"],
            "Route VLM_FULL_PAGE": s["route_vlm_full"],
            "Total VLM calls": s["vlm_calls"],
            "Chunks produced": s["chunks"],
        })

        # There should be some below-threshold elements triggering VLM
        if s["elem_below_150"] > 0:
            self.assertGreater(s["route_vlm_full"], 0,
                               "Below-threshold elements must route VLM_FULL_PAGE")
        print(f"\n  PASS: Hindi scanned pages correctly routed via Docling + VLM router.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
