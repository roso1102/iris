"""Full-corpus answer-evidence pass over ALL 50 golden queries (reviewer Q1).

The mechanical label audit only compared labels vs retrieval pages; answer
TEXTS were only scrutinized on flagged queries (q_005/q_029's wrong answers
were caught by the human, not by process). This pass checks every query's
answer against two page-anchored evidence sources:
  (a) the source PDF's text layer (independent), and
  (b) the index's per-page text (VLM OCR post-fallback; one-source).

Verdicts (evidence for the human, never auto-corrections):
  OK              - best evidence page is one of the labeled pages
  FOUND_ELSEWHERE - strong evidence on a page outside the labels
  ANSWER_WEAK     - no page in the labeled doc(s) shows distinctive overlap
                    (answer text wrong, or neither source can see it)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EVAL_USER_PASSWORD", "EvalPass!2026x")

import requests  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from scripts.eval_phase2 import _retrieval_headers, load_golden, RETRIEVAL_URL  # noqa: E402

STRONG = 0.45  # overlap needed to call a page "evidence"


def needles(answer: str) -> set:
    words = {w for w in re.findall(r"[a-zA-Z\u0900-\u097F]{4,}", answer.lower())}
    # Numbers are high-value needles: strip commas so "2,577.60" matches text
    # that renders it with or without grouping.
    nums = {n.replace(",", "").strip(".") for n in re.findall(r"\d[\d,\.]*", answer)
            if len(n.replace(",", "").replace(".", "")) >= 3}
    return words | nums


def text_tokens(text: str) -> set:
    toks = {w for w in re.findall(r"[a-zA-Z\u0900-\u097F]{4,}", text.lower())}
    flat = text.replace(",", "").replace("\n", " ")
    toks |= {n for n in re.findall(r"\d[\d\.]*", flat)}
    return toks


_pdf: dict = {}
_api: dict = {}


def pdf_pages(doc: str) -> dict:
    if doc not in _pdf:
        try:
            r = PdfReader(str(ROOT / "trueassort" / f"{doc}.pdf"))
            _pdf[doc] = {i: (p.extract_text() or "") for i, p in enumerate(r.pages, 1)}
        except Exception:
            _pdf[doc] = {}
    return _pdf[doc]


def api_pages(doc: str) -> dict:
    if doc not in _api:
        by_page: dict[int, list[str]] = {}
        for attempt in range(2):
            try:
                r = requests.post(
                    f"{RETRIEVAL_URL}/search",
                    json={"query": "the of and section act page court table fund", "mode": "standard",
                          "top_k": 30, "doc_ids": [doc]},
                    headers=_retrieval_headers(), timeout=60,
                )
                if r.status_code == 429:
                    print(f"  [rate-limited fetching {doc}; waiting out window]")
                    time.sleep(65)
                    continue
                for x in r.json().get("results", []):
                    by_page.setdefault(int(x["page_number"]), []).append(x["text"])
                break
            except Exception as exc:
                print(f"  [evidence fetch failed for {doc}: {exc}]")
        _api[doc] = {p: " ".join(t) for p, t in by_page.items()}
    return _api[doc]


def main() -> None:
    golden = load_golden()
    counts = {"OK": 0, "FOUND_ELSEWHERE": 0, "ANSWER_WEAK": 0}
    flagged = []
    for g in golden:
        nz = needles(str(g.get("answer", "")))
        if not nz:
            counts["ANSWER_WEAK"] += 1
            flagged.append((g["query_id"], g["type"], "ANSWER_WEAK", "empty answer"))
            continue
        labels = set(g["relevant_page_numbers"])
        best = (0.0, None)  # (overlap, page)
        label_best = 0.0
        for doc in g["relevant_doc_ids"]:
            # Concatenate both sources per page — the text layer is empty on
            # scanned pages and must not CLOBBER the VLM text (merge-order
            # bug in v1 made every scanned page look blank to this pass).
            merged: dict[int, str] = {}
            for src in (api_pages(doc), pdf_pages(doc)):
                for pno, text in src.items():
                    merged[pno] = (merged.get(pno, "") + " " + text).strip()
            for pno, text in merged.items():
                if len(text.strip()) < 30:
                    continue
                tt = text_tokens(text)
                ov = len(nz & tt) / len(nz)
                if ov > best[0]:
                    best = (ov, pno)
                if pno in labels and ov > label_best:
                    label_best = ov
        if label_best >= STRONG or (best[1] in labels and best[0] >= STRONG):
            counts["OK"] += 1
        elif best[0] >= STRONG:
            counts["FOUND_ELSEWHERE"] += 1
            flagged.append((g["query_id"], g["type"], "FOUND_ELSEWHERE",
                            f"best evidence p{best[1]} overlap {best[0]:.2f}, labels {sorted(labels)}, label-page best {label_best:.2f}"))
        else:
            counts["ANSWER_WEAK"] += 1
            flagged.append((g["query_id"], g["type"], "ANSWER_WEAK",
                            f"best overlap anywhere {best[0]:.2f} @p{best[1]}, labels {sorted(labels)}"))

    print("Counts:", counts, "of", len(golden))
    for qid, qtype, verdict, detail in flagged:
        print(f"  {qid:6s} [{qtype:20s}] {verdict:16s} {detail}")


if __name__ == "__main__":
    main()
