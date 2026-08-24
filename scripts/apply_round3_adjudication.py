"""Apply owner's Round-3 adjudication to goldendataset.json.

Owner decisions (2026-08-23/24) on the 11 answer-evidence page-placement
flags from label_adjudication_guide.md section F:
  q_009 4->5, q_010 3->[3,14], q_018 [3,3]->[1,3], q_043 drop p7,
  q_044 19->20, q_046 26->24, q_049 9->10, q_011 [3,2]->[2,1]
  (doc_001 p2 = S.2(g) definition; doc_002 p1 = Rule 3 rank mandate).
Dismissed (labels already correct): q_031, q_036, q_048.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "goldendataset.json"
BACKUP = ROOT / "goldendataset.pre-round3-backup.json"

# query_id -> new relevant_page_numbers (or None to leave unchanged)
RULINGS: dict[str, list[int] | None] = {
    "q_009": [5],
    "q_010": [3, 14],
    "q_011": [2, 1],
    "q_018": [1, 3],
    "q_043": [3, 4, 5, 6],
    "q_044": [20],
    "q_046": [24],
    "q_049": [10],
    "q_031": None,  # dismissed: label p4 already correct
    "q_036": None,  # dismissed: doc_004 p3 correct
    "q_048": None,  # dismissed: label p1 correct
}


def main() -> None:
    if not BACKUP.exists():
        shutil.copy(GOLDEN, BACKUP)
        print(f"backup -> {BACKUP.name}")

    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    changed = 0
    for item in golden:
        qid = item["query_id"]
        if qid in RULINGS and RULINGS[qid] is not None:
            old = list(item["relevant_page_numbers"])
            item["relevant_page_numbers"] = RULINGS[qid]
            changed += 1
            print(f"  {qid}: pages {old} -> {item['relevant_page_numbers']}")

    GOLDEN.write_text(json.dumps(golden, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nApplied {changed} rulings. Backup: {BACKUP.name}. Timestamp: {datetime.now().isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
