import os
import unittest
from unittest.mock import MagicMock, call, patch

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

    def test_embed_query_default_delegates_to_embed(self):
        # Providers without asymmetric embeddings (mock/gpu) inherit the
        # embed() delegation from ModelProvider.
        provider = MockModelProvider(embed_dim=768)
        self.assertEqual(provider.embed_query("q"), provider.embed("q"))


class TestVertexRerank(unittest.TestCase):
    """Phase 12.1 reranker against the Discovery Engine Ranking API."""

    def _provider(self):
        from services.common.models.vertex import VertexAIProvider

        return VertexAIProvider(project_id="test-project")

    @staticmethod
    def _fake_response(records):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"records": records}
        return resp

    def test_rerank_maps_returned_order_to_scores(self):
        provider = self._provider()
        # API returns records reordered by relevance: id 2 > 0 > 1.
        with patch.object(provider, "_ranking_token", return_value="tok"), \
                patch("requests.post", return_value=self._fake_response(
                    [{"id": "2"}, {"id": "0"}, {"id": "1"}])) as post:
            scores = provider.rerank("q", ["a", "b", "c"])
        # Input-order scores: idx2 rank1 -> 3.0, idx0 rank2 -> 2.0, idx1 rank3 -> 1.0.
        self.assertEqual(scores, [2.0, 1.0, 3.0])
        call = post.call_args
        self.assertIn("discoveryengine.googleapis.com", call.args[0])
        self.assertIn("default_ranking_config:rank", call.args[0])
        body = call.kwargs["json"]
        self.assertEqual(body["model"], "semantic-ranker@latest")
        self.assertEqual([r["id"] for r in body["records"]], ["0", "1", "2"])
        self.assertEqual([r["content"] for r in body["records"]], ["a", "b", "c"])

    def test_rerank_respects_location_env(self):
        provider = self._provider()
        with patch.object(provider, "_ranking_token", return_value="tok"), \
                patch.dict(os.environ, {"RERANK_LOCATION": "us-central1"}), \
                patch("requests.post", return_value=self._fake_response([])) as post:
            provider.rerank("q", ["a"])
        self.assertIn("https://us-central1-discoveryengine", post.call_args.args[0])

    def test_rerank_caps_at_40_passages_and_500_chars(self):
        provider = self._provider()
        with patch.object(provider, "_ranking_token", return_value="tok"), \
                patch("requests.post", return_value=self._fake_response([])) as post:
            scores = provider.rerank("q", ["p" * 2000] + [f"p{i}" for i in range(49)])
        self.assertEqual(len(scores), 40)
        body = post.call_args.kwargs["json"]
        self.assertEqual(len(body["records"]), 40)
        self.assertTrue(all(len(r["content"]) <= 500 for r in body["records"]))

    def test_rerank_failure_neutral_and_logged(self):
        provider = self._provider()
        with patch.object(provider, "_ranking_token", return_value="tok"), \
                patch("requests.post", side_effect=RuntimeError("boom")):
            with self.assertLogs("services.common.models.vertex", level="WARNING") as logs:
                scores = provider.rerank("q", ["a", "b"])
        self.assertEqual(scores, [1.0, 1.0])
        self.assertTrue(any("rerank_failed" in line for line in logs.output))

    def test_embed_task_split_query_vs_document(self):
        provider = self._provider()
        with patch.object(provider, "_embed_task", return_value=[0.0]) as task:
            provider.embed_query("the question")
            provider.embed("the document")
        task.assert_has_calls(
            [call("the question", "RETRIEVAL_QUERY"), call("the document", "RETRIEVAL_DOCUMENT")]
        )


if __name__ == "__main__":
    unittest.main()
