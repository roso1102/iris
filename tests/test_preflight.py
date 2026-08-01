"""Phase 1.0 unit tests — preflight scanner (Task 1.2).

Covers Test 1-B (oversized rejection) and the corrupt-trailer path (Test 1-C)
without touching GCP: builds real PDFs with pypdf.
"""

import unittest
from pathlib import Path

from services.common.ingestion.preflight import PreflightError, check_pdf


class TestPreflight(unittest.TestCase):

    def _write_pdf(self, path: Path, pages: int) -> None:
        from pypdf import PdfWriter

        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(width=612, height=792)
        with open(path, "wb") as fh:
            writer.write(fh)

    def test_accepts_normal_pdf(self):
        with self._tmp_pdf(50) as path:
            meta = check_pdf(path)
        self.assertEqual(meta["page_count"], 50)

    def test_rejects_oversized_pdf(self):
        with self._tmp_pdf(600) as path:
            with self.assertRaisesRegex(PreflightError, "600 pages"):
                check_pdf(path)

    def test_rejects_empty_file(self):
        with self._tmp_pdf(0, empty=True) as path:
            with self.assertRaises(PreflightError):
                check_pdf(path)

    def test_rejects_corrupt_trailer(self):
        with self._tmp_pdf(0, corrupt=True) as path:
            with self.assertRaises(PreflightError):
                check_pdf(path)

    def _tmp_pdf(self, pages: int, empty: bool = False, corrupt: bool = False):
        import tempfile
        import contextlib

        @contextlib.contextmanager
        def _ctx():
            fd, name = tempfile.mkstemp(suffix=".pdf")
            os_close = lambda: None
            try:
                if empty:
                    Path(name).write_bytes(b"")
                elif corrupt:
                    Path(name).write_bytes(b"%PDF-1.4\nbroken trailer no xref")
                else:
                    self._write_pdf(Path(name), pages)
                yield Path(name)
            finally:
                try:
                    Path(name).unlink()
                except OSError:
                    pass

        return _ctx()


if __name__ == "__main__":
    unittest.main()
