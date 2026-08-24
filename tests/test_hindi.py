"""Pipeline #3: Cross-lingual detection unit tests."""

import unittest

from services.common.retrieval.hindi import (
    contains_devanagari,
    is_romanized_hindi,
    needs_cross_lingual_boost,
)


class TestDevanagariDetection(unittest.TestCase):
    def test_devanagari_detected(self):
        self.assertTrue(contains_devanagari("समिति कोष"))
        self.assertTrue(contains_devanagari("Hello समिति"))

    def test_no_devanagari(self):
        self.assertFalse(contains_devanagari("committee funding"))
        self.assertFalse(contains_devanagari("pashupalan kanoon"))
        self.assertFalse(contains_devanagari(""))


class TestRomanizedHindi(unittest.TestCase):
    def test_known_words(self):
        self.assertTrue(is_romanized_hindi("pashupalan kanoon"))
        self.assertTrue(is_romanized_hindi("samvidhan"))
        self.assertTrue(is_romanized_hindi("krishi nyayalaya"))
        self.assertTrue(is_romanized_hindi("PASHUPALAN policy"))

    def test_english_not_detected(self):
        self.assertFalse(is_romanized_hindi("committee funding"))
        self.assertFalse(is_romanized_hindi("tax audit"))
        self.assertFalse(is_romanized_hindi("high court petition"))


class TestNeedsCrossLingualBoost(unittest.TestCase):
    def test_no_corpus_no_boost(self):
        self.assertFalse(needs_cross_lingual_boost("hello", False))

    def test_devanagari_query_no_boost(self):
        self.assertFalse(needs_cross_lingual_boost("समिति कोष", True))

    def test_latin_query_with_corpus(self):
        self.assertTrue(needs_cross_lingual_boost("committee funding", True))
        self.assertTrue(needs_cross_lingual_boost("pashupalan", True))
        self.assertTrue(needs_cross_lingual_boost("pashupalan funding", True))


if __name__ == "__main__":
    unittest.main()
