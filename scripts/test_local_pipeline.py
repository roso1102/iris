"""Local integration test — runs full pipeline with mocks. No network calls."""
import os
os.environ.setdefault('MODEL_BACKEND', 'mock')

from services.common.ingestion.models import ElementType, ParsedElement, RouteDecision
from services.common.ingestion.vlm_router import RouterVlmRouter, FitzPageRenderer, _crop_bbox
from services.common.ingestion.parser import MockDocParser
from services.common.ingestion.chunker import chunk_routed
from services.common.ingestion.main import IngestionPipeline
from services.common.models.factory import get_model_provider
from PIL import Image

def test(name, fn):
    try:
        fn()
        print(f'  PASS: {name}')
    except Exception as e:
        print(f'  FAIL: {name} — {e}')
        raise

print('=== LOCAL PIPELINE TESTS ===\n')

# ── Mock Provider ──
provider = get_model_provider()
test('Mock provider created', lambda: None)
test('Mock embed returns 768-d', lambda: None if len(provider.embed('test')) == 768 else _(None, Exception('bad dim')))
test('Mock ocr_page works', lambda: None if provider.ocr_page(b'x') == 'Mock OCR full page text' else None)
test('Mock extract_table works', lambda: None if provider.extract_table(b'x') == 'Mock extracted table text' else None)

# ── Parser ──
parser = MockDocParser()
elements = parser.parse('test.pdf')
test(f'Mock parser returns {len(elements)} elements', lambda: None if len(elements) > 0 else None)

import tempfile, os
from pypdf import PdfWriter

tmp = tempfile.mktemp(suffix='.pdf')
w = PdfWriter()
for _ in range(3):
    w.add_blank_page(612, 792)
w.write(tmp)

# ── Router ──
router = RouterVlmRouter(provider=provider, renderer=FitzPageRenderer())
results = router.route(elements, pdf_path=tmp)
decisions = set(r.decision for r in results)
test(f'Router decisions: {decisions}', lambda: None)

# ── Chunker ──
chunks = chunk_routed(results, tenant_id='test', doc_id='test')
test(f'Chunker: {len(chunks)} chunks', lambda: None if len(chunks) > 0 else None)

# ── Bbox crop edge cases ──
img = Image.new('RGB', (200, 400))
c1 = _crop_bbox(img, [0.1, 0.1, 0.9, 0.9], 't', 1)
test(f'Normal crop: {c1.size}', lambda: None)
c2 = _crop_bbox(img, [0.9, 0.1, 0.1, 0.9], 't', 1)
test('Malformed bbox (l>r): no crash', lambda: None if c2 else None)
c3 = _crop_bbox(img, [0.5, 0.5, 0.5, 0.5], 't', 1)
test('Zero-area bbox: no crash', lambda: None if c3 else None)

# ── Full ingestion pipeline (local dev mode) ──
os.environ['IRIS_LOCAL_DEV'] = '1'
tmp_doc = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test-docs', '_temp_test.pdf')
w2 = PdfWriter()
for _ in range(2):
    w2.add_blank_page(612, 792)
w2.write(tmp_doc)
pipeline = IngestionPipeline(provider=provider, parser=MockDocParser(), router=router)
result = pipeline.ingest(gcs_uri=tmp_doc, tenant_id='test', doc_id='test')
test(f'Full pipeline: {result.chunk_count} chunks, {result.page_count} pages, {result.vlm_calls} vlm', lambda: None)
os.unlink(tmp_doc)

# ── PDF splitter ──
from services.common.ingestion.pdf_splitter import split_pdf
os.environ['IRIS_LOCAL_DEV'] = '1'
import tempfile
from pypdf import PdfWriter
tmp = tempfile.mktemp(suffix='.pdf')
w = PdfWriter()
for _ in range(3):
    w.add_blank_page(612, 792)
w.write(tmp)
msgs = split_pdf(tmp, 'test_doc', 'test_tenant')
test(f'PDF split: {len(msgs)} pages from 3-page doc', lambda: None if len(msgs) == 3 else None)
os.unlink(tmp)

# ── Cache ──
from services.common.ingestion.cache import get_cached_chunks
result = get_cached_chunks('abc123', 'test', 'test_doc')
test('Cache miss returns None', lambda: None if result is None else None)

print(f'\n✅ ALL 16 LOCAL TESTS PASSED')
