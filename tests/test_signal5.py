"""Tier 0 unit tests — Signal 5: Non-Latin Script Dominant Detection (FIX-008).

The reference implementation from fixes_critical.md FIX-008 is kept inline here
so this test is pure-logic (stdlib `unicodedata` only, zero external deps) and
can run before the production router change lands.

Once FIX-008 is implemented in `services/common/ingestion/vlm_router.py`, this
module should import `_is_non_latin_dominant` from there and drop the local copy
(delete `_REFERENCE_IS_NON_LATIN_DOMINANT` below).

Behavior under test (from FIX-008):
  * Devanagari (Hindi) text -> True  (route to VLM_FULL_PAGE for multilingual OCR)
  * Clean English/Latin text -> False (stays DOCLING_TEXT)
  * Threshold: >30% of letter characters outside Latin/Extended-Latin (U+024F).
"""

import unittest

import unicodedata


def _REFERENCE_IS_NON_LATIN_DOMINANT(text: str, threshold: float = 0.30) -> bool:
    """Return True if >30% of letter characters are outside Latin/Extended-Latin."""
    letters = [c for c in text if unicodedata.category(c).startswith("L")]
    if not letters:
        return False
    non_latin = [c for c in letters if ord(c) > 0x024F]  # U+024F = end of Extended Latin
    return (len(non_latin) / len(letters)) > threshold


try:
    from services.common.ingestion.vlm_router import _is_non_latin_dominant as _prod
except ImportError:
    _prod = _REFERENCE_IS_NON_LATIN_DOMINANT


HINDI = "यह एक हिंदी वाक्य है जो देवनागरी लिपि में लिखा गया है।"
ENGLISH = "This is a clean English sentence with only Latin characters."
MIXED_LIGHT = "Invoice #1234 dated 2026-08-13, total amount Rs. 500/-"
DEVANAGARI_PUNCT = "।"


class TestSignal5(unittest.TestCase):
    """Verify FIX-008 Signal 5 non-Latin detection fires on Hindi, not English."""

    def test_hindi_devanagari_detected(self):
        """Hindi page (valid_word_ratio ~0.82–0.87) must trigger Signal 5."""
        self.assertTrue(_prod(HINDI))

    def test_clean_english_not_detected(self):
        """Clean English text must never trigger Signal 5."""
        self.assertFalse(_prod(ENGLISH))

    def test_mixed_english_digits_not_detected(self):
        """English text with numerals/punctuation stays Latin-dominant."""
        self.assertFalse(_prod(MIXED_LIGHT))

    def test_short_hindi_clause_still_detected(self):
        """A short Hindi clause still exceeds the 30% letter threshold."""
        self.assertTrue(_prod("निर्णय पत्र"))

    def test_empty_and_ascii_text(self):
        """Empty and ASCII-only inputs never trigger Signal 5."""
        self.assertFalse(_prod(""))
        self.assertFalse(_prod("hello world 123"))
        self.assertFalse(_prod("   "))

    def test_threshold_boundary(self):
        """A page that is exactly 30% non-Latin does NOT trigger (strict >)."""
        # 7 Latin letters + 3 Devanagari letters = exactly 30% non-Latin.
        text = "abcdefg" + "कखग"
        self.assertFalse(_prod(text, threshold=0.30))

    def test_pure_devanagari_punctuation_only(self):
        """Punctuation-only (no letters) never triggers Signal 5."""
        self.assertFalse(_prod(DEVANAGARI_PUNCT))


if __name__ == "__main__":
    unittest.main()
