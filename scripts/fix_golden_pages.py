"""Apply the audited +1 page-label correction to goldendataset.json.

The audit (scripts/label_audit.py + PDF/VLM verification) proved the golden
page labels were authored against a 0-based page view while the pipeline
(and the PDF itself, and the frontend viewer) is 1-based: retrieval hit
label+1 for 13/13 flagged queries, and 10 of those were independently
verified against the source PDFs' text layer or the VLM OCR text.

This script:
  - backs up the original to goldendataset.pre-audit-backup.json
  - adds +1 to every relevant_page_number of the VERIFIED queries only
  - leaves q_033, q_045 (weak signal, same direction) and q_042 (mild
    counter-evidence) untouched for human adjudication
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "goldendataset.json"
BACKUP = ROOT / "goldendataset.pre-audit-backup.json"

# Off-by-one queries with ground-truth verification (PDF text layer or
# VLM-OCR overlap on label+1, absent on label).
VERIFIED = [
    "q_001", "q_002", "q_005", "q_011", "q_017", "q_018",
    "q_021", "q_029", "q_030", "q_049",
]
# Same direction but unverified — human decides.
UNVERIFIED = ["q_033", "q_045", "q_042"]


def main() -> None:
    if not BACKUP.exists():
        shutil.copy(GOLDEN, BACKUP)
        print(f"backup -> {BACKUP.name}")

    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    fixed = 0
    for item in golden:
        if item["query_id"] in VERIFIED:
            old = list(item["relevant_page_numbers"])
            item["relevant_page_numbers"] = [p + 1 for p in old]
            fixed += 1
            print(f"  {item['query_id']}: pages {old} -> {item['relevant_page_numbers']}")
        elif item["query_id"] in UNVERIFIED:
            print(f"  {item['query_id']}: LEFT for human adjudication")

    GOLDEN.write_text(json.dumps(golden, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nFixed {fixed}/{len(VERIFIED)} verified queries. Unverified: {UNVERIFIED}")


if __name__ == "__main__":
    main()
