"""Phase 2.0 unit tests — BM25 sparse tokenizer."""

import unittest

from services.common.retrieval.bm25 import (
    text_to_sparse,
    tokenize,
    sparse_to_qdrant_indices_values,
)


class TestBM25Tokenizer(unittest.TestCase):

    def test_tokenize_basic_english(self):
        tokens = tokenize("The committee shall provide necessary funds")
        expected = {"committee", "provide", "necessary", "funds"}
        self.assertEqual(set(tokens), expected)

    def test_tokenize_filters_stopwords(self):
        tokens = tokenize("the and for that this with from are was has not")
        self.assertEqual(tokens, [])

    def test_tokenize_filters_short_words(self):
        tokens = tokenize("an is of at be by my he")
        self.assertEqual(tokens, [])

    def test_tokenize_statutory_language(self):
        text = (
            "Whereas the authority hereby notifies the following "
            "rules pursuant to Section 5 of the said Act"
        )
        tokens = tokenize(text)
        self.assertIn("authority", tokens)
        self.assertIn("notifies", tokens)

    def test_text_to_sparse_returns_dict(self):
        text = "The High Court dismissed the petition under Article 226"
        sparse = text_to_sparse(text)
        self.assertIsInstance(sparse, dict)
        self.assertGreater(len(sparse), 0)

    def test_text_to_sparse_empty_input(self):
        self.assertEqual(text_to_sparse(""), {})
        self.assertEqual(text_to_sparse("   "), {})
        self.assertEqual(text_to_sparse("the and for"), {})

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


if __name__ == "__main__":
    unittest.main()
