"""Phase 2.5 unit tests — table markdown validator."""

import unittest

from services.common.retrieval.validator import validate_table_markdown


class TestTableValidator(unittest.TestCase):

    def test_valid_simple_table(self):
        md = "| Col1 | Col2 |\n|------|------|\n| a    | b    |\n| c    | d    |"
        self.assertTrue(validate_table_markdown(md))

    def test_invalid_row_mismatch(self):
        md = "| Col1 | Col2 |\n| a | b | c |"
        self.assertFalse(validate_table_markdown(md))

    def test_single_row(self):
        md = "| Col1 | Col2 | Col3 |"
        self.assertFalse(validate_table_markdown(md))

    def test_empty_input(self):
        self.assertFalse(validate_table_markdown(""))
        self.assertFalse(validate_table_markdown("just text, no pipes"))

    def test_valid_multi_aligned(self):
        md = (
            "| Name | Value |\n"
            "|:-----|:------|\n"
            "| foo  | 42    |\n"
            "| bar  | 99    |\n"
        )
        self.assertTrue(validate_table_markdown(md))


if __name__ == "__main__":
    unittest.main()
