import unittest
from services.common.models.factory import get_model_provider
from services.common.models.mock import MockModelProvider
from services.common.models.base import StructuredAnswer


class TestModelProviderScaffold(unittest.TestCase):

    def test_mock_provider_factory(self):
        import os
        os.environ["MODEL_BACKEND"] = "mock"
        provider = get_model_provider()
        self.assertIsInstance(provider, MockModelProvider)

    def test_mock_embed(self):
        provider = MockModelProvider(embed_dim=768)
        vec = provider.embed("Sample text for embedding")
        self.assertEqual(len(vec), 768)

    def test_mock_synthesize(self):
        provider = MockModelProvider()
        source_chunks = [
            {"chunk_id": "c1", "doc_id": "d1", "page_number": 1, "bbox": [0, 0, 1, 1], "text": "x"},
        ]
        res = provider.synthesize(context="Some doc content", query="What is this?", source_chunks=source_chunks)
        self.assertIsInstance(res, StructuredAnswer)
        self.assertIn("Mock synthesis answer", res.answer)
        self.assertEqual(res.citations[0].chunk_id, "c1")

    def test_mock_vlm_extract_table(self):
        provider = MockModelProvider()
        markdown = provider.extract_table(b"dummy_image_bytes")
        self.assertIn("| Column 1 |", markdown)


if __name__ == "__main__":
    unittest.main()
