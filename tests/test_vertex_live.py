import unittest
import os
from services.common.models.vertex import VertexAIProvider


@unittest.skipUnless(
    os.getenv("RUN_VERTEX_LIVE_TESTS") == "1",
    "Skipping live Vertex AI test (set RUN_VERTEX_LIVE_TESTS=1 to enable).",
)
class TestVertexAIIntegration(unittest.TestCase):

    def test_vertex_embedding(self):
        """Test live Vertex AI text-embedding-004 call using gcloud credentials."""
        provider = VertexAIProvider(project_id="naturepivot-rag")
        vec = provider.embed("Test embedding call for IRIS platform")
        self.assertEqual(len(vec), 768)
        print("\nSUCCESS: Vertex AI text-embedding-004 returned live 768-d vector!")


if __name__ == "__main__":
    unittest.main()
