import unittest
import os
import pytest
from services.common.models.vertex import VertexAIProvider

pytestmark = pytest.mark.live


@unittest.skipUnless(
    os.getenv("RUN_VERTEX_LIVE_TESTS") == "1",
    "Skipping live Vertex AI test (set RUN_VERTEX_LIVE_TESTS=1 to enable).",
)
class TestVertexAIIntegration(unittest.TestCase):

    def test_vertex_embedding(self):
        """Test live Vertex AI text-embedding-004 call using gcloud credentials."""
        provider = VertexAIProvider(project_id=os.getenv("GCP_PROJECT", "naturepivot-rag"))
        vec = provider.embed("Test embedding call for IRIS platform")
        self.assertEqual(len(vec), 768)
        print("\nSUCCESS: Vertex AI text-embedding-004 returned live 768-d vector!")

    def test_vertex_synthesis_2_5_flash(self):
        """Test live Gemini 2.5 Flash synthesis call."""
        provider = VertexAIProvider(project_id=os.getenv("GCP_PROJECT", "naturepivot-rag"))
        source_chunks = [
            {
                "chunk_id": "live-c1",
                "doc_id": "live-doc",
                "page_number": 1,
                "bbox": [0.1, 0.1, 0.9, 0.9],
                "text": "IRIS is a multi-tenant document RAG platform on GCP.",
            }
        ]
        res = provider.synthesize(
            "IRIS is a multi-tenant document RAG platform on GCP.",
            "What is IRIS?",
            source_chunks=source_chunks,
        )
        self.assertIsNotNone(res.answer)
        self.assertIn("IRIS", res.answer)
        print(f"\nSUCCESS: Gemini 2.5 Flash answered: {res.answer[:80]}...")

    def test_vertex_lite_2_5_flash_lite(self):
        """Test live Gemini 2.5 Flash Lite query rewrite call."""
        provider = VertexAIProvider(project_id=os.getenv("GCP_PROJECT", "naturepivot-rag"))
        rewritten = provider.rewrite_query("What are its main features?", [
            {"role": "user", "content": "Tell me about IRIS platform."},
            {"role": "assistant", "content": "IRIS is a multi-tenant RAG platform."}
        ])
        self.assertIsNotNone(rewritten)
        print(f"\nSUCCESS: Gemini 2.5 Flash Lite rewritten query: {rewritten}")

    def test_vertex_vision_crop_ocr(self):
        """Test live Gemini 2.5 Flash vision OCR call on sample image bytes."""
        from PIL import Image, ImageDraw
        import io
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((10, 40), "IRIS TEST 2.5 VISION", fill=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        provider = VertexAIProvider(project_id=os.getenv("GCP_PROJECT", "naturepivot-rag"))
        ocr_res = provider.ocr_page(buf.getvalue())
        self.assertIsNotNone(ocr_res)
        print(f"\nSUCCESS: Gemini 2.5 Flash Vision OCR returned: {ocr_res}")


if __name__ == "__main__":
    unittest.main()
