"""Render visual page evidence for the 11 Round-3 adjudication items.

For each flagged golden query, renders the LABELED page(s) and the
BEST-EVIDENCE page(s) from the source PDF into adjudication/<qid>/,
highlighting where the answer's needle terms occur on digital (text-layer)
pages. Scanned pages get a higher-DPI plain render for visual reading.

Local adjudication artifact only (gitignored) - regenerate anytime:
    .venv\\Scripts\\python.exe scripts\\render_page_evidence.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz  # PyMuPDF

try:  # cp1252 consoles choke on Devanagari paths in listings
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "adjudication"

# qid -> (best_evidence_pages, extra_pages_to_render)
# Labels come from goldendataset.json; extras are context the owner asked
# about in the Round-3 notes (e.g. q_045's p7 twin content for q_049).
SPEC: dict[str, tuple[list[int], list[int]]] = {
    "q_009": ([5], []),
    "q_010": ([14], []),
    "q_011": ([1], []),
    "q_018": ([1], []),
    "q_031": ([3], []),
    "q_036": ([1], []),
    "q_043": ([1], []),
    "q_044": ([20], []),
    "q_046": ([24], []),
    "q_048": ([5], []),
    "q_049": ([10], [7]),  # p7 = where q_045 (same cattle-compensation content) was verified
}

DIGITAL_DPI = 150
SCANNED_DPI = 200


def needles(answer: str) -> set[str]:
    """Same needle logic as answer_evidence_pass.py."""
    import re

    words = set(re.findall(r"[a-zA-Z\u0900-\u097F]{4,}", answer.lower()))
    nums = {
        n.replace(",", "").strip(".")
        for n in re.findall(r"\d[\d,\.]*", answer)
        if len(n.replace(",", "").replace(".", "")) >= 3
    }
    return words | nums


def grouped_variants(term: str) -> list[str]:
    """'2577.60' -> also try '2,577.60'-style groupings for literal search."""
    if not any(c.isdigit() for c in term):
        return [term]
    out = [term]
    try:
        val = float(term)
        if val >= 1000:
            out.append(f"{val:,.2f}")
            out.append(f"{int(val):,}")
    except ValueError:
        pass
    return out


def highlight(page: fitz.Page, terms: set[str]) -> int:
    """Draw yellow rects behind needle-term occurrences. Returns hit count."""
    rects: list[fitz.Rect] = []
    for t in sorted(terms):
        if len(t) < 5:
            continue
        for variant in grouped_variants(t):
            hits = page.search_for(variant, quads=False)
            if hits:
                rects.extend(hits)
                break
    drawn = 0
    seen: set[tuple[float, float, float, float]] = set()
    for r in rects:
        key = (round(r.x0), round(r.y0), round(r.x1), round(r.y1))
        if key in seen:
            continue
        seen.add(key)
        page.draw_rect(r, color=(1, 0.8, 0), fill=(1, 0.95, 0.6), fill_opacity=0.55)
        drawn += 1
        if drawn >= 60:
            break
    return drawn


def render(pdf_path: Path, pno: int, dest: Path, terms: set[str]) -> str:
    doc = fitz.open(pdf_path)
    if pno < 1 or pno > len(doc):
        doc.close()
        return f"p{pno}: OUT OF RANGE ({len(doc)} pages)"
    page = doc.load_page(pno - 1)  # viewer 1-based == physical 1-based
    n_hits = highlight(page, terms)
    zoom = SCANNED_DPI / 72 if not page.get_text().strip() else DIGITAL_DPI / 72
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    pix.save(dest)
    doc.close()
    return f"p{pno}{'  [' + str(n_hits) + ' needle hits]' if n_hits else ''}"


def main() -> None:
    raw = json.loads((ROOT / "goldendataset.json").read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else raw["queries"]
    golden = {g["query_id"]: g for g in items if isinstance(g, dict)}
    OUT.mkdir(exist_ok=True)

    for qid, (best_pages, extra_pages) in SPEC.items():
        g = golden[qid]
        labels = sorted({p for p in g["relevant_page_numbers"]})
        terms = needles(str(g.get("answer", "")))
        qdir = OUT / qid
        qdir.mkdir(exist_ok=True)

        lines = [
            f"# {qid} - {g['type']}",
            "",
            f"Query: {g['query']}",
            f"Answer: {g['answer']}",
            f"Labeled pages: {labels}",
            f"Best-evidence pages (Round 3): {best_pages}",
            "",
            "## What to decide",
            "- Does the ANSWER content sit on the labeled page, the",
            "  best-evidence page, or both?",
            "- If both: keep the substantive page as the label",
            "  (p1-summary hits are correct-but-not-preferred).",
            "- If only best-evidence: correct the label here and in",
            "  goldendataset.json (viewer 1-based numbering).",
            "",
            "## Rendered files",
        ]
        status = []
        for doc_id in g["relevant_doc_ids"]:
            pdf_path = ROOT / "trueassort" / f"{doc_id}.pdf"
            if not pdf_path.exists():
                status.append(f"{doc_id}: MISSING PDF")
                continue
            for tag, pages in (("label", labels), ("best", best_pages), ("extra", extra_pages)):
                for pno in pages:
                    dest = qdir / f"{doc_id}_{tag}_p{pno}.png"
                    note = render(pdf_path, pno, dest, terms)
                    rel = str(dest.relative_to(ROOT)).replace("\\", "/")
                    status.append(f"- [{rel}] - {doc_id} {tag} {note}")

        lines.extend(status)
        (qdir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{qid}: {len(status)} renders")

    print(f"\nDone. Open {OUT}\\<qid>\\README.md per query.")


if __name__ == "__main__":
    main()
