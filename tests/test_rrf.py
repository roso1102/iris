"""Phase 2.0 unit tests — RRF fusion."""

import unittest

from services.common.retrieval.rrf import reciprocal_rank_fusion


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


if __name__ == "__main__":
    unittest.main()
