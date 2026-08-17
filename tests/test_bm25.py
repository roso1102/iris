"""Phase 3.0 Task 3.5 — FastEmbed BM25 sparse tokenizer tests.

Validates that the FastEmbed `Qdrant/bm25` model produces deterministic,
non-empty sparse vectors and that the Qdrant conversion helper is correct.
The specific index values are model-defined (not mmh3), so these tests assert
behavior (non-empty, deterministic, sorted), not exact hash values.
"""

import os
import unittest

from services.common.retrieval.bm25 import (
    text_to_sparse,
    tokenize,
    sparse_to_qdrant_indices_values,
)


class TestFastEmbedBM25(unittest.TestCase):

    def test_text_to_sparse_returns_nonempty_dict(self):
        sparse = text_to_sparse("The High Court dismissed the petition under Article 226")
        self.assertIsInstance(sparse, dict)
        self.assertGreater(len(sparse), 0)

    def test_text_to_sparse_empty_input(self):
        self.assertEqual(text_to_sparse(""), {})
        self.assertEqual(text_to_sparse("   "), {})

    def test_text_to_sparse_is_deterministic(self):
        text = "section five of the act"
        a = text_to_sparse(text)
        b = text_to_sparse(text)
        self.assertEqual(a, b)

    def test_tokenize_nonempty(self):
        tokens = tokenize("The committee shall provide necessary funds")
        self.assertGreater(len(tokens), 0)

    def test_sparse_to_qdrant_format(self):
        text = "section five of the act"
        sparse = text_to_sparse(text)
        indices, values = sparse_to_qdrant_indices_values(sparse)
        self.assertEqual(len(indices), len(values))
        self.assertEqual(indices, sorted(indices))
        for i in range(len(indices)):
            self.assertAlmostEqual(values[i], sparse[indices[i]])

    def test_sparse_to_qdrant_empty(self):
        indices, values = sparse_to_qdrant_indices_values({})
        self.assertEqual(indices, [])
        self.assertEqual(values, [])


class TestBakedCacheLayout(unittest.TestCase):
    """Verify the Docker-baked cache is in the HF layout fastembed expects."""

    def test_baked_cache_has_snapshot_layout(self):
        cache_dir = os.environ.get("FASTEMBED_CACHE_PATH")
        self.assertTrue(cache_dir, "FASTEMBED_CACHE_PATH should be set by conftest")
        storage = os.path.join(cache_dir, "models--Qdrant--bm25")
        self.assertTrue(os.path.isdir(storage), f"missing {storage}")
        # Either a snapshots/<hash> dir or refs/main pointing at one (or both).
        refs_main = os.path.join(storage, "refs", "main")
        snapshots = os.path.join(storage, "snapshots")
        self.assertTrue(
            (os.path.isfile(refs_main) and os.path.isdir(snapshots)),
            "expected refs/main + snapshots layout",
        )
        hash_dir = os.path.join(snapshots, os.listdir(snapshots)[0])
        self.assertTrue(os.path.isfile(os.path.join(hash_dir, "english.txt")))
        # fastembed 0.8.0 writes files_metadata.json at the repo-storage root.
        self.assertTrue(os.path.isfile(os.path.join(storage, "files_metadata.json")))


if __name__ == "__main__":
    unittest.main()
