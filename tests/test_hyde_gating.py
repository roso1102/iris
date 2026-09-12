"""Phase 0.1 tests — deterministic HyDE gating and output validation."""

import asyncio
import json
import os
import unittest
from pathlib import Path

os.environ["MODEL_BACKEND"] = "mock"

from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from services.common.ingestion.store import MemoryChunkStore
from services.common.models.mock import MockModelProvider
from services.common.retrieval import hyde
from services.common.retrieval.rrf import weighted_ranked_fusion
from services.common.retrieval.search import SearchOrchestrator

FIXTURES = Path(__file__).parent / "fixtures"


def _chunk(text: str, tenant_id: str = "tenant-a", doc_id: str = "d1") -> Chunk:
    return Chunk(
        tenant_id=tenant_id,
        doc_id=doc_id,
        page_number=1,
        element_type=ElementType.TEXT,
        text=text,
        bbox=[0.1, 0.1, 0.5, 0.4],
        source=RouteDecision.DOCLING_TEXT,
        embedding=[0.1] * 768,
    )


class HyDETrackingProvider(MockModelProvider):
    def __init__(self, query_value=0.1, hyde_raises=False, hyde_output=None):
        super().__init__()
        self.query_value = query_value
        self.hyde_raises = hyde_raises
        self.hyde_output = hyde_output
        self.hyde_calls = 0
        self.doc_embeds = 0

    def embed_query(self, text):
        return [self.query_value] * 768

    def embed(self, text):
        self.doc_embeds += 1
        return [0.1] * 768

    def generate_hyde(self, query):
        self.hyde_calls += 1
        if self.hyde_raises:
            raise RuntimeError("provider down")
        if self.hyde_output is not None:
            return self.hyde_output
        return {"hypothesis": f"Hypothetical answer about {query}", "keywords": [query]}


class TestBypassTable(unittest.TestCase):

    def test_labeled_routing_table(self):
        lines = (FIXTURES / "hyde_routing_table.jsonl").read_text(encoding="utf-8").strip().splitlines()
        self.assertGreaterEqual(len(lines), 60)
        bypass = eligible = 0
        for line in lines:
            case = json.loads(line)
            reason = hyde.bypass_reason(case["query"])
            if case["label"] == "bypass":
                bypass += 1
                self.assertIsNotNone(reason, case)
                self.assertEqual(reason, case["reason"], case)
            else:
                eligible += 1
                self.assertIsNone(reason, case)
        self.assertGreaterEqual(bypass, 30)
        self.assertGreaterEqual(eligible, 30)

    def test_rewritten_followup_bypasses(self):
        self.assertEqual(
            hyde.bypass_reason("What about its limitations?", rewritten=True),
            "rewritten_followup",
        )


class TestBaselineWeakness(unittest.TestCase):

    def test_empty_is_weak(self):
        self.assertTrue(hyde.baseline_is_weak([], []))

    def test_low_top_score_is_weak(self):
        self.assertTrue(hyde.baseline_is_weak([("c1", 0.01)], []))

    def test_strong_baseline_is_not_weak(self):
        self.assertFalse(hyde.baseline_is_weak([("c1", 0.9)], [("c1", 2.0)]))


class TestOutputValidation(unittest.TestCase):

    def test_structured_output_ok(self):
        parsed = hyde.validate_hyde_output(
            {"hypothesis": "The policy caps emissions.", "keywords": ["caps", "emissions"]},
            "what are the emissions",
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["keywords"], ["caps", "emissions"])

    def test_legacy_string_rejected(self):
        # Legacy plain-text provider output cannot be validated to the strict
        # standard, so it is refused outright (provider must return JSON).
        self.assertIsNone(hyde.validate_hyde_output("A plain hypothesis.", "query"))

    def test_new_entity_in_hypothesis_rejected(self):
        self.assertIsNone(
            hyde.validate_hyde_output(
                {"hypothesis": "Acme Corporation paid the fee.", "keywords": []},
                "what is the fee",
            )
        )

    def test_new_alphabetic_identifier_rejected(self):
        self.assertIsNone(
            hyde.validate_hyde_output(
                {"hypothesis": "See the XYZ-9 policy.", "keywords": []},
                "what is the policy",
            )
        )

    def test_new_month_without_digits_rejected(self):
        self.assertIsNone(
            hyde.validate_hyde_output(
                {"hypothesis": "It was notified in March.", "keywords": []},
                "when was it notified",
            )
        )

    def test_new_content_in_keywords_rejected(self):
        self.assertIsNone(
            hyde.validate_hyde_output(
                {"hypothesis": "The policy applies.", "keywords": ["Acme Ltd"]},
                "what is the policy",
            )
        )

    def test_entity_present_in_query_allowed(self):
        parsed = hyde.validate_hyde_output(
            {"hypothesis": "Acme Corporation is mentioned.", "keywords": []},
            "what does the Acme Corporation report say",
        )
        self.assertIsNotNone(parsed)

    def test_empty_and_malformed_rejected(self):
        self.assertIsNone(hyde.validate_hyde_output("", "q"))
        self.assertIsNone(hyde.validate_hyde_output({"keywords": []}, "q"))
        self.assertIsNone(hyde.validate_hyde_output(12345, "q"))

    def test_hallucinated_number_rejected(self):
        self.assertIsNone(
            hyde.validate_hyde_output(
                {"hypothesis": "The fine was 1,068 crore.", "keywords": []},
                "what is the fine",
            )
        )
        self.assertIsNotNone(
            hyde.validate_hyde_output(
                {"hypothesis": "The fine was 1,068 crore.", "keywords": []},
                "what is the 1,068 crore fine",
            )
        )


class TestWeightedFusion(unittest.TestCase):
    def test_lower_weight_cannot_outrank_strong_baseline(self):
        baseline = [("strong", 1.0)]
        hyde_leg = [("weak", 1.0)]
        fused = weighted_ranked_fusion(
            [baseline, hyde_leg], [1.0, hyde.HYDE_LEG_WEIGHT]
        )
        self.assertEqual(fused[0][0], "strong")


class TestStandardIntegration(unittest.TestCase):

    def _run(self, coro):
        return asyncio.run(coro)

    def test_strong_baseline_skips_hyde(self):
        store = MemoryChunkStore()
        store.upsert_batch([_chunk("government funds committee")])
        provider = HyDETrackingProvider(query_value=0.1)
        orch = SearchOrchestrator(store=store, provider=provider)
        results, trace = self._run(
            orch.standard_search("what are the environmental impacts", "tenant-a", top_k=5)
        )
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(provider.hyde_calls, 0)
        self.assertFalse(trace["hyde"]["used"])
        self.assertIsNone(trace["hyde"]["bypass_reason"])
        self.assertTrue(trace["hyde"]["eligible"])

    def test_weak_baseline_triggers_hyde(self):
        store = MemoryChunkStore()  # empty -> no baseline results
        provider = HyDETrackingProvider(query_value=0.1)
        orch = SearchOrchestrator(store=store, provider=provider)
        _results, trace = self._run(
            orch.standard_search("what are the environmental impacts", "tenant-a", top_k=5)
        )
        self.assertEqual(provider.hyde_calls, 1)
        self.assertTrue(trace["hyde"]["used"])
        self.assertGreater(trace["hyde"]["estimated_cost"], 0.0)

    def test_bypass_query_never_calls_hyde(self):
        store = MemoryChunkStore()
        provider = HyDETrackingProvider()
        orch = SearchOrchestrator(store=store, provider=provider)
        _results, trace = self._run(
            orch.standard_search("What is Section 17?", "tenant-a", top_k=5)
        )
        self.assertEqual(provider.hyde_calls, 0)
        self.assertFalse(trace["hyde"]["eligible"])
        self.assertEqual(trace["hyde"]["bypass_reason"], "exact_identifier")

    def test_hyde_failure_falls_back_to_baseline(self):
        store = MemoryChunkStore()
        store.upsert_batch([_chunk("government funds committee")])
        # Low query score -> weak baseline -> HyDE eligible; provider then fails.
        provider = HyDETrackingProvider(query_value=0.0005, hyde_raises=True)
        orch = SearchOrchestrator(store=store, provider=provider)
        results, trace = self._run(
            orch.standard_search("what are the environmental impacts", "tenant-a", top_k=5)
        )
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(provider.hyde_calls, 1)
        self.assertFalse(trace["hyde"]["used"])

    def test_greeting_deep_search_skips_hyde(self):
        store = MemoryChunkStore()
        provider = HyDETrackingProvider()
        orch = SearchOrchestrator(store=store, provider=provider)
        trace = {}
        self._run(
            orch.deep_search("hello", "tenant-a", top_k=5, trace=trace)
        )
        self.assertEqual(provider.hyde_calls, 0)
        self.assertEqual(trace["hyde"]["bypass_reason"], "greeting")


if __name__ == "__main__":
    unittest.main()
