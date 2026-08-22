# Golden-Set Adjudication Guide

**Created:** 2026-08-22 · **Owner:** Rohit · **Status:** OPEN — items below need your eyes
**Rules attached to this sheet:**
1. Current corrected metrics are **floors, not finals**: Page-Recall@5 ≥ 0.539, MRR ≥ 0.455. Do not quote them as exact in any doc until this sheet is cleared.
2. **q_003 / q_010 (and q_020) are HELD OUT** of any "corrected" number — they are suspected label errors awaiting your verdict.
3. Never quote `scanned_lookup` 0.143 without the caveat: doc_001/doc_002 are partially un-indexed (see section C) — that number measures a broken index, not only retrieval.

---

## A. How to verify a label (method + worked example)

**Tools:** any PDF viewer (browser works) + `trueassort/doc_XXX.pdf` + the question/answer below.

**Steps:**
1. Open the doc's PDF, go to the LABELED page (PDF viewers are 1-based, same as our system).
2. Look for the expected answer on that page.
3. If not there, check the HINT page listed for that item (usually label ±1).
4. Tick ONE box per item in the table in section B/C, then tell the agent the verdicts (or edit `goldendataset.json` `relevant_page_numbers` yourself and re-run `python scripts/eval_phase2.py --skip-ingestion --skip-deep`).
   - Label wrong → correct the page number.
   - Label right → genuine retrieval failure; leave it, that is real signal.

**Worked example (q_001 — already resolved by evidence, do not redo):**
- Query: "What term is used by Knudsen (2020)…", expected answer "Digitisation", label: doc_006 page 1.
- Open `doc_006.pdf` page 1 → no "digitisation". Page 2 → the Knudsen paragraph containing "digitisation" is there.
- Verdict: **label wrong** (0-based authoring) → fixed to page 2. This same pattern (+1) was then PDF-verified for 9 more queries.

---

## B. Items needing your eyes (5 items, ~10 minutes)

| # | Query | Doc / labeled page | Hint | What to check |
|---|---|---|---|---|
| q_033 | max assistance for loss of an animal (revised SDRF norms) | doc_008 p5 | also look at p6 | Answer "Rs. 32,000/- per animal" — likely p6 (same +1 pattern as the 10 fixed ones) |
| q_045 | "How much for a dead cow?" | doc_008 p5 | also look at p6 | Answer "Rs. 37,500/- per animal (milch cow…)" — likely p6 |
| q_042 | Summarize the risks of plug-ins | doc_007 p31 | also look at p30 | ⚠ counter-evidence: retrieval hit p30 (= label−1). Read both pages; this one breaks the +1 pattern, look carefully |
| q_003 | markup language announced by JP Morgan & PwC | doc_007 p41 | evidence points to p43 | Answer "FpML". Also check p42. |
| q_010 | Ex-Gratia for grievous injury under revised NDRF norms (July 2023) | doc_008 p1 | evidence points to p3 (strong, 0.75 overlap) | Answer "Rs. 16,000/- per person" |

*q_020 ("Is XBRL based on a W3C standard?") also labels doc_007 p41 — same page as q_003. One look at p41/p42/p43 resolves both; record the verdict for q_020 too.*

## C. NOT label questions — explained by the un-indexed-pages bug (no action for you)

**Finding (verified 2026-08-22):** doc_001 (7 PDF pages) has only **1 page** in the index; doc_002 (7 pages) has **2**; doc_008 has 12 of 14. Cause: Docling detects **zero layout elements** on some scanned pages (confirmed visually: doc_002 p7 is a "FOR OFFICE USE" form with real content that Docling misses), and with `do_ocr=False` nothing reaches the VLM router — the page "ingests successfully" with `chunks=0 vlm_calls=0`. Silent data loss.

Affected queries — their labeled pages are simply **not in the index**, so retrieval could never find them:
q_009, q_034, q_038, q_041, q_048 (all doc_001), q_035 (doc_002 p7).

**Do not touch these labels.** The fix is engineering: a page-level fallback (if a page yields zero elements and has no text layer, render it and send the whole page to VLM OCR anyway). After that fix + re-ingest, re-run the audit before judging retrieval on these.

## D. Confirmed genuine retrieval failures (no action)

q_006, q_013, q_028 — answer verified ON the labeled page (doc_007 pages 9/42, 47), retrieval missed. Real signal, largely the VLM-mega-chunk problem already on the roadmap.

## E. Already fixed this round

10 off-by-one labels corrected (+1; 6 confirmed via PDF text layer = independent ground truth, 4 via VLM OCR text = one-source, visual spot-check pending — see `scripts/fix_golden_pages.py`).
