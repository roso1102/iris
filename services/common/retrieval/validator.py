"""Phase 2.5 — VLM table markdown validation.

Validates that VLM-extracted Markdown tables have consistent column counts
across all rows. Corrupted tables (merged cells, hallucinated rows) are
flagged with confidence: low.
"""

from __future__ import annotations


def validate_table_markdown(md_text: str) -> bool:
    """Validate VLM-extracted Markdown table structure.

    Returns True if row/column counts are aligned; False if corrupted/merged.
    """
    rows = [r for r in md_text.split("\n") if r.strip().startswith("|")]
    if len(rows) < 2:
        return False
    col_counts = [r.count("|") for r in rows]
    return len(set(col_counts)) == 1
