"""Pipeline #4: Golden-set labeling worksheet.

CLI tool for authoring new golden queries into the held-out set.

Usage:
  python scripts/label_worksheet.py --show doc_008 3      # render page + text
  python scripts/label_worksheet.py --progress            # stratification counts
  python scripts/label_worksheet.py --add \\
    --query "pashupalan yojana kya hai" \\
    --answer "Pashupalan yojana ek sarkari hai" \\
    --doc doc_004 --page 5 --type hindi_lookup \\
    --relevant-docs doc_004 --relevant-pages 5
  python scripts/label_worksheet.py --verify q_054       # needle-check
  python scripts/label_worksheet.py --list                # all entries
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HELDOUT = ROOT / "golden_heldout.json"
TUNE = ROOT / "goldendataset.json"

# ── Schema ─────────────────────────────────────────────────────────

def _load(path: Path) -> list[dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save(path: Path, data: list[dict]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _next_id(data: list[dict]) -> str:
    ids = [int(g["query_id"].split("_")[1]) for g in data if g["query_id"].startswith("q_")]
    return f"q_{(max(ids) + 1) if ids else 54:03d}"


# ── Commands ───────────────────────────────────────────────────────

def cmd_show(args):
    """Render a page and print its text."""
    doc_id, page = args.doc, args.page
    try:
        import fitz
        pdf = fitz.open(ROOT / "trueassort" / f"{doc_id}.pdf")
        if page < 1 or page > len(pdf):
            print(f"Error: {doc_id} has {len(pdf)} pages, got {page}")
            return
        pg = pdf.load_page(page - 1)
        text = pg.get_text()
        # render PNG
        out_dir = ROOT / "adjudication" / "_worksheet"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{doc_id}_p{page}.png"
        zoom = 200 / 72 if not text.strip() else 150 / 72
        pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        pix.save(out_path)
        print(f"Page rendered: {out_path}")
        print(f"--- Text ({len(text)} chars) ---")
        print(text[:3000])
        if len(text) > 3000:
            print(f"... ({len(text) - 3000} more chars)")
    except Exception as e:
        print(f"Error: {e}")


def cmd_progress(args):
    """Show stratification counts across tune + heldout."""
    tune = _load(TUNE)
    heldout = _load(HELDOUT)

    type_counts: dict[str, list[int]] = {}
    for g in tune + heldout:
        t = g.get("type", "unknown")
        if t not in type_counts:
            type_counts[t] = [0, 0]
        idx = 1 if g in heldout else 0
        type_counts[t][idx] += 1

    print(f"{'Type':<25} {'Tune':>5} {'Held':>5} {'Total':>6}")
    print("-" * 45)
    for t in sorted(type_counts):
        tune_c, held_c = type_counts[t]
        print(f"{t:<25} {tune_c:>5} {held_c:>5} {tune_c+held_c:>6}")
    print("-" * 45)
    total_tune = sum(v[0] for v in type_counts.values())
    total_held = sum(v[1] for v in type_counts.values())
    print(f"{'TOTAL':<25} {total_tune:>5} {total_held:>5} {total_tune+total_held:>6}")
    print(f"\nNext ID: {_next_id(tune + heldout)}")


def cmd_add(args):
    """Add a new query to golden_heldout.json."""
    data = _load(HELDOUT)
    qid = _next_id(data + _load(TUNE))

    entry = {
        "query_id": qid,
        "type": args.type,
        "query": args.query,
        "answer": args.answer,
        "relevant_doc_ids": [d.strip() for d in args.relevant_docs.split(",")],
        "relevant_page_numbers": [int(p.strip()) for p in args.relevant_pages.split(",")],
    }

    data.append(entry)
    _save(HELDOUT, data)
    print(f"Added {qid}: {args.type} — {args.query[:60]}")
    print(f"  Docs: {entry['relevant_doc_ids']}  Pages: {entry['relevant_page_numbers']}")
    print(f"  Total heldout: {len(data)}")


def cmd_verify(args):
    """Needle-check an entry against its labeled page."""
    data = _load(HELDOUT)
    entry = next((g for g in data if g["query_id"] == args.query_id), None)
    if not entry:
        print(f"Error: {args.query_id} not found in heldout set")
        return

    answer = entry.get("answer", "")
    needles = set(re.findall(r"[a-zA-Z\u0900-\u097F]{4,}", answer.lower()))
    nums = {
        n.replace(",", "").strip(".")
        for n in re.findall(r"\d[\d,\.]*", answer)
        if len(n.replace(",", "").replace(".", "")) >= 3
    }
    needles |= nums

    if not needles:
        print(f"  WARNING: no distinctive needles in answer '{answer[:60]}'")
        return

    try:
        import fitz
        for doc_id in entry["relevant_doc_ids"]:
            for page in entry["relevant_page_numbers"]:
                pdf = ROOT / "trueassort" / f"{doc_id}.pdf"
                if not pdf.exists():
                    print(f"  {doc_id}: PDF not found")
                    continue
                doc = fitz.open(pdf)
                pg = doc.load_page(page - 1)
                text = pg.get_text().lower()
                hits = {n for n in needles if n in text}
                ratio = len(hits) / len(needles) if needles else 0
                status = "OK" if ratio >= 0.4 else "WEAK"
                print(f"  {doc_id} p{page}: {status} — {len(hits)}/{len(needles)} needles matched ({ratio:.0%})")
                if hits:
                    print(f"    matched: {', '.join(sorted(hits)[:10])}")
                if ratio < 0.4:
                    missing = needles - hits
                    print(f"    missing: {', '.join(sorted(missing)[:10])}")
    except Exception as e:
        print(f"Error: {e}")


def cmd_list(args):
    """List all heldout entries."""
    data = _load(HELDOUT)
    if not data:
        print("No entries in golden_heldout.json")
        return
    for g in data:
        print(f"  {g['query_id']:6s} [{g['type']:20s}] {g['query'][:60]}")


# ── Main ───────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Golden-set labeling worksheet (pipeline #4)")
    sub = parser.add_subparsers(dest="command")

    p_show = sub.add_parser("show", help="Show page text + render PNG")
    p_show.add_argument("doc", help="doc_00X")
    p_show.add_argument("page", type=int, help="1-based page number")

    sub.add_parser("progress", help="Stratification counts")

    p_add = sub.add_parser("add", help="Add a new query")
    p_add.add_argument("--query", required=True, help="Search query text")
    p_add.add_argument("--answer", required=True, help="Expected answer")
    p_add.add_argument("--relevant-docs", required=True, help="Relevant doc IDs, comma-separated")
    p_add.add_argument("--relevant-pages", required=True, help="Relevant page(s), comma-separated")
    p_add.add_argument("--type", required=True, help="Query type")

    p_verify = sub.add_parser("verify", help="Needle-check an entry")
    p_verify.add_argument("query_id", help="e.g. q_054")

    sub.add_parser("list", help="List all heldout entries")

    args = parser.parse_args()
    if args.command == "show":
        cmd_show(args)
    elif args.command == "progress":
        cmd_progress(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
