"""Stage 1.5 — examine the 12 unexplained audit flags (PAGE_MISS / DOC_MISS).

For each flagged query, locate the expected answer INDEPENDENTLY of
retrieval ranking, using two page-anchored evidence sources:
  (a) the source PDF's text layer (fully independent), and
  (b) the ingestion store's per-page text (VLM OCR for scanned pages;
      one-source evidence, disclosed as such).

Classification per query:
  REAL_MISS        - answer IS on the labeled (doc, page); retrieval ranked
                     it out of top-10 -> genuine retrieval failure, keep label.
  LABEL_SUSPECT    - best evidence places the answer on a different page
                     than labeled -> second labeling bug candidate (human call).
  DOC_LABEL_SUSPECT- best page is in a DIFFERENT doc than labeled.
  UNVERIFIABLE     - no text layer and no VLM text for the candidate pages.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EVAL_USER_PASSWORD", "EvalPass!2026x")

import requests  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from scripts.eval_phase2 import _retrieval_headers, load_golden, RETRIEVAL_URL  # noqa: E402

SHEET = ROOT / "label_audit_sheet.csv"


def tokens(s: str) -> set:
    return {w for w in re.findall(r"[a-zA-Z\u0900-\u097F]{4,}", s.lower())}


_pdf_cache: dict = {}


def pdf_page_text(doc: str, page: int) -> str:
    if doc not in _pdf_cache:
        _pdf_cache[doc] = PdfReader(str(ROOT / "trueassort" / f"{doc}.pdf"))
    r = _pdf_cache[doc]
    if not (1 <= page <= len(r.pages)):
        return ""
    return r.pages[page - 1].extract_text() or ""


_api_cache: dict = {}


def api_page_text(doc: str, page: int) -> str:
    if doc not in _api_cache:
        r = requests.post(
            f"{RETRIEVAL_URL}/search",
            json={"query": "the of and section act page court", "mode": "standard",
                  "top_k": 30, "doc_ids": [doc]},
            headers=_retrieval_headers(), timeout=60,
        )
        by_page: dict[int, list[str]] = {}
        for x in r.json().get("results", []):
            by_page.setdefault(int(x["page_number"]), []).append(x["text"])
        _api_cache[doc] = by_page
    return " ".join(_api_cache[doc].get(page, []))


def main() -> None:
    golden = {g["query_id"]: g for g in load_golden()}
    rows = [r for r in csv.DictReader(SHEET.open(encoding="utf-8"))
            if r["flag"] in ("PAGE_MISS", "DOC_MISS")]

    out = []
    for r in rows:
        g = golden[r["query_id"]]
        at = tokens(str(g.get("answer", "")) + " " + g["query"])
        if not at:
            continue
        label_docs = r["label_docs"].split(";")
        label_pages = [int(x) for x in r["label_pages"].split(";")]

        # Score every page within +/-3 of each labeled page (both sources),
        # plus top-10 retrieved docs' best pages for DOC_MISS context.
        best = (0.0, None, None, None)  # (overlap, doc, page, source)
        label_page_scores = []
        for d in label_docs:
            for p in label_pages:
                for delta in (-2, -1, 0, 1, 2):
                    page = p + delta
                    for source, getter in (("pdf", pdf_page_text), ("qdrant", api_page_text)):
                        text = getter(d, page)
                        if len(text.strip()) < 40:
                            continue
                        ov = len(at & tokens(text)) / len(at)
                        if ov > best[0]:
                            best = (ov, d, page, source)
                        if delta == 0:
                            label_page_scores.append((d, p, round(ov, 2), source))

        best_label = max((s for _, _, s, _ in label_page_scores), default=0.0)
        if best[0] < 0.25:
            verdict = "UNVERIFIABLE"
        elif best_label >= 0.25:
            verdict = "REAL_MISS"
        elif best[1] in label_docs:
            verdict = f"LABEL_SUSPECT (evidence: {best[1]}@p{best[2]} via {best[3]}, overlap {best[0]:.2f})"
        else:
            verdict = f"DOC_LABEL_SUSPECT (evidence: {best[1]}@p{best[2]} via {best[3]}, overlap {best[0]:.2f})"
        out.append((r["query_id"], r["flag"], r["type"], verdict,
                    f"label pages scored <= {best_label:.2f}"))

    for qid, flag, qtype, verdict, extra in out:
        print(f"{qid:6s} {flag:9s} {qtype:18s} {verdict}  [{extra}]")
    counts: dict[str, int] = {}
    for _, _, _, v, _ in out:
        key = v.split(" ")[0]
        counts[key] = counts.get(key, 0) + 1
    print("\nCounts:", counts)


if __name__ == "__main__":
    main()
