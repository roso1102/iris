"""Phase 2.0 unit tests — RRF fusion."""

import unittest

from services.common.retrieval.rrf import fuse_rerank_scores, reciprocal_rank_fusion


class TestRRF(unittest.TestCase):

    def test_overlapping_results(self):
        dense = [("a", 0.95), ("b", 0.8), ("c", 0.6)]
        sparse = [("a", 1.2), ("d", 0.9), ("b", 0.3)]
        result = reciprocal_rank_fusion(dense, sparse, k=60)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0][0], "a")

    def test_disjoint_results(self):
        dense = [("a", 0.9), ("b", 0.8)]
        sparse = [("c", 1.0), ("d", 0.7)]
        result = reciprocal_rank_fusion(dense, sparse, k=60)
        self.assertEqual(len(result), 4)

    def test_single_source(self):
        dense = [("x", 0.9)]
        sparse = []
        result = reciprocal_rank_fusion(dense, sparse)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "x")

    def test_k_affects_score(self):
        dense = [("a", 0.9)]
        sparse = [("b", 1.0)]
        result_k60 = reciprocal_rank_fusion(dense, sparse, k=60)
        result_k1 = reciprocal_rank_fusion(dense, sparse, k=1)
        self.assertNotEqual(result_k60[0][1], result_k1[0][1])

    def test_empty_inputs(self):
        result = reciprocal_rank_fusion([], [])
        self.assertEqual(result, [])


class TestFuseRerankScores(unittest.TestCase):
    """Phase 12.1 weighted rank fusion — scale-free reranker blending."""

    def test_blend_zero_preserves_hybrid_order_exactly(self):
        hybrid = [0.03, 0.02, 0.01]
        out = fuse_rerank_scores(hybrid, [0.1, 0.9, 0.5], 0.0)
        self.assertEqual(out, hybrid)

    def test_blend_one_is_pure_ranker_order(self):
        hybrid = [0.03, 0.02, 0.01]
        # Ranker prefers passage 2 > 1 > 0 (reverse of input order).
        out = fuse_rerank_scores(hybrid, [0.1, 0.5, 0.9], 1.0)
        self.assertEqual(out.index(max(out)), 2)
        self.assertEqual(out.index(min(out)), 0)

    def test_equal_rerank_scores_preserve_hybrid_order(self):
        # Neutral fallback path (reranker failed): all-equal scores must
        # never reorder the hybrid ranking.
        hybrid = [0.01, 0.03, 0.02]
        out = fuse_rerank_scores(hybrid, [1.0, 1.0, 1.0], 0.7)
        self.assertEqual(out.index(max(out)), 1)
        self.assertEqual(out.index(min(out)), 0)

    def test_scale_free_huge_rerank_scores_dont_dominate(self):
        # Ranker scores 1000x apart: at blend=0.5 the strong hybrid leader
        # still outranks the ranker's pick whose raw score is enormous —
        # the raw-blend failure mode this fusion replaces.
        hybrid = [0.03, 0.001]
        out = fuse_rerank_scores(hybrid, [5.0, 5000.0], 0.5)
        self.assertGreater(out[0], out[1])

    def test_uneven_lengths_use_min(self):
        out = fuse_rerank_scores([0.03, 0.02, 0.01], [0.9], 1.0)
        self.assertEqual(len(out), 3)
        # The unranked tail keeps a hybrid-only (zero at blend=1) score.
        self.assertEqual(out[1], 0.0)
        self.assertEqual(out[2], 0.0)


if __name__ == "__main__":
    unittest.main()
