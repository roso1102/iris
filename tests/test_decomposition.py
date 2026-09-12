"""Tests for multi-query decomposition pipeline (Step 1-6)."""

import json
import os
import unittest
from unittest.mock import MagicMock, patch


class TestRouteQuerySchema(unittest.TestCase):
    """Verify route_query() returns the new decomposition fields."""

    def _provider(self):
        from services.common.models.vertex import VertexAIProvider
        return VertexAIProvider(project_id="test-project")

    def test_schema_has_decomposition_fields(self):
        """Schema includes needs_decomposition and search_queries."""
        provider = self._provider()
        active_docs = [{"ui_index": 1, "doc_id": "d1", "filename": "a.pdf"}]

        fake_response = MagicMock()
        fake_response.text = json.dumps({
            "intent": "GLOBAL_SEARCH",
            "target_doc_ids": [],
            "rewritten_query": "what is this",
            "needs_decomposition": False,
            "search_queries": [],
        })

        with patch.object(provider, "_ensure_init"), \
             patch("vertexai.generative_models.GenerativeModel") as MockModel:
            MockModel.return_value.generate_content.return_value = fake_response
            result = provider.route_query("what is this", active_docs)

        self.assertIn("needs_decomposition", result)
        self.assertIn("search_queries", result)
        self.assertFalse(result["needs_decomposition"])
        self.assertEqual(result["search_queries"], [])

    def test_token_limit_512(self):
        """max_output_tokens is 512, not 256."""
        provider = self._provider()
        active_docs = [{"ui_index": 1, "doc_id": "d1", "filename": "a.pdf"}]

        fake_response = MagicMock()
        fake_response.text = json.dumps({
            "intent": "GLOBAL_SEARCH",
            "target_doc_ids": [],
            "rewritten_query": "test",
            "needs_decomposition": False,
            "search_queries": [],
        })

        with patch.object(provider, "_ensure_init"), \
             patch("vertexai.generative_models.GenerativeModel") as MockModel:
            MockModel.return_value.generate_content.return_value = fake_response
            provider.route_query("test", active_docs)
            gen_config = MockModel.return_value.generate_content.call_args.kwargs["generation_config"]

        self.assertEqual(gen_config["max_output_tokens"], 512)


class TestPostProcessOrdering(unittest.TestCase):
    """Verify decomposition beats step-back when cap hits 3."""

    def _provider(self):
        from services.common.models.vertex import VertexAIProvider
        return VertexAIProvider(project_id="test-project")

    def test_decomposition_beats_stepback(self):
        """When LLM emits 2 decomp + 2 step-back, post-process keeps 2 decomp + 1 step-back."""
        provider = self._provider()
        active_docs = [{"ui_index": 1, "doc_id": "d1", "filename": "a.pdf"}]

        # Simulate LLM returning 4 queries (2 decomp + 2 step-back)
        fake_response = MagicMock()
        fake_response.text = json.dumps({
            "intent": "GLOBAL_SEARCH",
            "target_doc_ids": [],
            "rewritten_query": "complex query",
            "needs_decomposition": True,
            "search_queries": [
                {"query": "compliance deadlines", "type": "decomposition"},
                {"query": "penalty amounts", "type": "decomposition"},
                {"query": "regulatory framework overview", "type": "step_back"},
                {"query": "general context", "type": "step_back"},
            ],
        })

        with patch.object(provider, "_ensure_init"), \
             patch("vertexai.generative_models.GenerativeModel") as MockModel:
            MockModel.return_value.generate_content.return_value = fake_response
            result = provider.route_query("complex query", active_docs)

        # Should keep 2 decomposition + 1 step-back = 3 total
        self.assertEqual(len(result["search_queries"]), 3)
        self.assertTrue(result["needs_decomposition"])
        # All decomposition queries come first
        types = [q["type"] for q in result["search_queries"]]
        self.assertEqual(types[:2], ["decomposition", "decomposition"])
        self.assertEqual(types[2], "step_back")

    def test_simple_query_no_decomposition(self):
        """Simple query returns empty search_queries."""
        provider = self._provider()
        active_docs = [{"ui_index": 1, "doc_id": "d1", "filename": "a.pdf"}]

        fake_response = MagicMock()
        fake_response.text = json.dumps({
            "intent": "GLOBAL_SEARCH",
            "target_doc_ids": [],
            "rewritten_query": "what is this",
            "needs_decomposition": False,
            "search_queries": [],
        })

        with patch.object(provider, "_ensure_init"), \
             patch("vertexai.generative_models.GenerativeModel") as MockModel:
            MockModel.return_value.generate_content.return_value = fake_response
            result = provider.route_query("what is this", active_docs)

        self.assertFalse(result["needs_decomposition"])
        self.assertEqual(result["search_queries"], [])

    def test_fallback_includes_decomposition_fields(self):
        """Fallback path returns consistent schema with decomposition fields."""
        provider = self._provider()
        active_docs = [{"ui_index": 1, "doc_id": "d1", "filename": "a.pdf"}]

        # Simulate LLM failure
        with patch.object(provider, "_ensure_init"), \
             patch("vertexai.generative_models.GenerativeModel") as MockModel:
            MockModel.return_value.generate_content.side_effect = RuntimeError("boom")
            result = provider.route_query("test query", active_docs)

        self.assertIn("needs_decomposition", result)
        self.assertIn("search_queries", result)
        self.assertFalse(result["needs_decomposition"])
        self.assertEqual(result["search_queries"], [])


class TestEmbedQueryBatch(unittest.TestCase):
    """Verify embed_query_batch uses RETRIEVAL_QUERY task_type."""

    def _provider(self):
        from services.common.models.vertex import VertexAIProvider
        return VertexAIProvider(project_id="test-project")

    def test_uses_retrieval_query_task_type(self):
        """All items in batch use RETRIEVAL_QUERY, not RETRIEVAL_DOCUMENT."""
        provider = self._provider()
        with patch.object(provider, "embed_batch", return_value=[[0.1], [0.2]]) as mock_batch:
            result = provider.embed_query_batch(["query1", "query2"])

        mock_batch.assert_called_once_with(["query1", "query2"], task_type="RETRIEVAL_QUERY")
        self.assertEqual(result, [[0.1], [0.2]])

    def test_empty_input(self):
        """Empty list returns empty list."""
        provider = self._provider()
        with patch.object(provider, "embed_batch", return_value=[]) as mock_batch:
            result = provider.embed_query_batch([])

        self.assertEqual(result, [])

    def test_base_class_default(self):
        """MockModelProvider inherits base class embed_query_batch."""
        from services.common.models.mock import MockModelProvider
        provider = MockModelProvider(embed_dim=768)
        result = provider.embed_query_batch(["q1", "q2"])
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 768)


class TestSynthesizeSchema(unittest.TestCase):
    """Verify synthesize() schema has citations before answer."""

    def _provider(self):
        from services.common.models.vertex import VertexAIProvider
        return VertexAIProvider(project_id="test-project")

    def test_citations_before_answer(self):
        """Schema properties list citations before answer."""
        provider = self._provider()
        source_chunks = [
            {"chunk_id": "c1", "doc_id": "d1", "page_number": 1, "bbox": [0, 0, 1, 1], "text": "x"},
        ]

        fake_response_text = json.dumps({"citations": [{"ref": 1}], "answer": "test answer"})

        with patch.object(provider, "_ensure_init"), \
             patch("vertexai.generative_models.GenerativeModel") as MockModel:
            MockModel.return_value.generate_content.return_value = MagicMock(text=fake_response_text)
            result = provider.synthesize("context", "query", source_chunks)

        # Verify the schema passed to generate_content has citations first
        call_kwargs = MockModel.return_value.generate_content.call_args.kwargs
        gen_config = call_kwargs["generation_config"]
        prop_keys = list(gen_config["response_schema"]["properties"].keys())
        self.assertEqual(prop_keys, ["citations", "answer"])
        self.assertEqual(gen_config["response_schema"]["required"], ["citations", "answer"])

    def test_prompt_mentions_citations_first(self):
        """Synthesis prompt instructs to list citations before writing answer."""
        provider = self._provider()
        source_chunks = [
            {"chunk_id": "c1", "doc_id": "d1", "page_number": 1, "bbox": [0, 0, 1, 1], "text": "x"},
        ]

        fake_response_text = json.dumps({"citations": [], "answer": "test"})

        with patch.object(provider, "_ensure_init"), \
             patch("vertexai.generative_models.GenerativeModel") as MockModel:
            MockModel.return_value.generate_content.return_value = MagicMock(text=fake_response_text)
            provider.synthesize("context", "query", source_chunks)

        prompt = MockModel.return_value.generate_content.call_args.args[0]
        # Prompt may be a list of strings from f-string concatenation
        prompt_text = "".join(prompt) if isinstance(prompt, list) else prompt
        self.assertIn("FIRST: Identify which source numbers", prompt_text)
        self.assertIn("LIST those numbers in the", prompt_text)
        self.assertIn("THEN: Write the", prompt_text)


if __name__ == "__main__":
    unittest.main()
