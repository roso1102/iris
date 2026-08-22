"""Golden-set label audit (measurement work, stage 1).

For each of the 50 golden queries, run a live /search and produce a
human-adjudication sheet flagging suspicious labels:

  OFF_BY_ONE  - the right DOC is retrieved on a page adjacent (+/-1) to the
                labeled page (the known Knudsen-style labeling bug)
  DOC_MISS    - labeled doc never appears in top-10; possible wrong doc label
  PAGE_MISS   - labeled doc retrieved but labeled page never in top-10
  OK          - a labeled (doc, page) pair appears in top-10

The sheet is a CSV + markdown review file. Retrieval results are EVIDENCE
for the human, never the verdict: a flagged query is a question ("is the
label right or is retrieval wrong?"), not an auto-correction.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("EVAL_USER_PASSWORD", "EvalPass!2026x")

import requests  # noqa: E402

from scripts.eval_phase2 import (  # noqa: E402
    RETRIEVAL_URL,
    _retrieval_headers,
    _search,
    load_golden,
)

SHEET_CSV = ROOT / "label_audit_sheet.csv"
SHEET_MD = ROOT / "label_audit_sheet.md"


def audit_query(item: dict) -> dict:
    resp = _search({"query": item["query"], "mode": "standard", "top_k": 10})
    results = resp.get("results", [])
    label_docs = set(item["relevant_doc_ids"])
    label_pages = {int(p) for p in item.get("relevant_page_numbers", [])}

    top10_pairs = [(r["doc_id"], int(r["page_number"])) for r in results]
    top10_docs = {d for d, _ in top10_pairs}
    top10_pages_of_label_docs = {p for d, p in top10_pairs if d in label_docs}

    flag, detail = "OK", ""
    if label_docs & top10_docs:
        if not (label_pages & top10_pages_of_label_docs):
            adjacent = {p + 1 for p in label_pages} | {p - 1 for p in label_pages}
            if adjacent & top10_pages_of_label_docs:
                flag = "OFF_BY_ONE"
                found = sorted(adjacent & top10_pages_of_label_docs)
                labeled = sorted(label_pages)
                detail = f"labeled page {labeled}, retrieval hits {found} (adjacent)"
            else:
                flag = "PAGE_MISS"
                detail = (
                    f"labeled pages {sorted(label_pages)}, retrieval pages of "
                    f"labeled docs: {sorted(top10_pages_of_label_docs)}"
                )
    else:
        flag = "DOC_MISS"
        detail = f"labeled docs {sorted(label_docs)}, top-10 docs {sorted(top10_docs)}"

    return {
        "query_id": item["query_id"],
        "type": item["type"],
        "query": item["query"],
        "label_docs": ";".join(sorted(label_docs)),
        "label_pages": ";".join(str(p) for p in sorted(label_pages)),
        "flag": flag,
        "detail": detail,
        "expected_answer": str(item.get("answer", ""))[:120],
        "top5": " | ".join(f"{d}@p{p}" for d, p in top10_pairs[:5]),
        "top5_snippet": (results[0]["text"][:200] if results else "").replace("\n", " "),
    }


def main() -> None:
    golden = load_golden()
    rows = []
    for i, item in enumerate(golden, 1):
        rows.append(audit_query(item))
        if i % 10 == 0:
            print(f"  {i}/{len(golden)} audited")

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["flag"]] = counts.get(r["flag"], 0) + 1
    print("Flag counts:", counts)

    with SHEET_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    flagged = [r for r in rows if r["flag"] != "OK"]
    with SHEET_MD.open("w", encoding="utf-8") as f:
        f.write("# Golden-set label audit — human adjudication sheet\n\n")
        f.write(
            "For each flagged query decide: label wrong (fix the JSON) or "
            "retrieval wrong (leave label; it's a real failure).\n\n"
            f"**{len(flagged)} of {len(rows)} queries flagged** "
            f"({counts}).\n\n---\n\n"
        )
        for r in flagged:
            f.write(
                f"## {r['query_id']} [{r['flag']}] ({r['type']})\n\n"
                f"- **Query:** {r['query']}\n"
                f"- **Label:** docs `{r['label_docs']}`, pages `{r['label_pages']}`\n"
                f"- **Expected answer:** {r['expected_answer']}\n"
                f"- **Evidence:** {r['detail']}\n"
                f"- **Top-5 retrieved:** {r['top5']}\n"
                f"- **Top snippet:** {r['top5_snippet']}...\n\n"
                f"- [ ] label wrong -> fix goldendataset.json\n"
                f"- [ ] label right -> genuine retrieval failure\n\n"
            )
    print(f"Sheet -> {SHEET_MD}")
    print(f"CSV  -> {SHEET_CSV}")


if __name__ == "__main__":
    main()
