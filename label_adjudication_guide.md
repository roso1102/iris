# Golden-Set Adjudication Guide

**Created:** 2026-08-22 · **Owner:** Rohit · **Status:** ✅ RESOLVED (rounds 1–3; last adjudication 2026-08-24 — Round-3 section F fully applied to goldendataset.json via `scripts/apply_round3_adjudication.py`; all 11 items decided)
**Page-number convention (settled):** the pipeline, citations, frontend viewer, and this golden set all use **PDF physical sequence, 1-based** ("viewer" numbering). The ORIGINAL labels were authored against the documents' PRINTED page numbers, whose offset from physical sequence varies per document (doc_007: printed = viewer + 9; most others: printed = viewer − 1) — that is the root cause of the original off-by-one plague. Any future label must be read off the PDF viewer, not the printed page.
**Metrics snapshot (historical — pre-final-eval):** Recall@5 0.880 · Page-Recall@5 0.626 · MRR 0.555 (as of 2026-08-22). The 2026-08-23 final eval with the full corpus measured 1.000 / 0.740 / 0.667; labels changed again 2026-08-24 (Round 3), so re-run the eval to re-derive authoritative numbers.
**Rules attached to this sheet:**
1. Current corrected metrics are **floors, not finals** — historical as of 2026-08-22 (Page-Recall@5 ≥ 0.539, MRR ≥ 0.455). Superseded by the 2026-08-23 final eval (1.000/0.740/0.667) and the 2026-08-24 Round-3 label application; re-run the eval for authoritative numbers.
2. ~~q_003 / q_010 / q_020 held out~~ — RESOLVED: q_010 adjudicated [3,14] this round; q_003/q_020 (doc_007 p32) were NOT re-flagged by the Round-3 answer-evidence pass (not in the 11), so they stand as labeled. All 11 Round-3 flags now adjudicated (2026-08-24).
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

## F. Round 3 (2026-08-23): answer-evidence pass — 11 page-placement items

`scripts/answer_evidence_pass.py` verified every answer text against ground truth (PDF text layer + VLM OCR concatenated per page). **39/50 verified OK — no additional wrong answers (the q_005/q_029 class is cleared).** 11 queries show strongest evidence on a page OUTSIDE the current labels. These are evidence flags, not verdicts — several adjacent-page cases may be both-pages-referenced; your call.

| # | Query (short) | Label | Best evidence | Note |
|---|---|---|---|---|
| q_009 | S.9 penalty term | 4 | **p5** (0.77 vs 0.31) | ✅ **ADJUDICATED: label 4→5** (owner; renders show S.9 verbatim on p5; p4 has S.7 only) |
| q_010 | Ex-Gratia grievous injury | 3 | **p14** (0.50, label 0.00) | ✅ **ADJUDICATED: both pages correct; label [3,14]** — combined answer must cite both separately |
| q_011 | records officer alignment | [2,3] | **p1** (0.61) | ✅ **ADJUDICATED: label [2,1]** (doc_001 p2 = S.2(g) definition; doc_002 p1 = Rule 3 rank mandate; owner cited both) |
| q_018 | 'public records' definition | [3,3] | **p1** (0.50) | ✅ **ADJUDICATED: p1 AND p3 relevant in BOTH doc_001 and doc_002; label [1,3]** |
| q_031 | scanned: SDRF item | 4 | **p3** (1.00, label 0.00) | ✅ **ADJUDICATED: p3 wrong, p4 correct — label already right; dismissed** |
| q_036 | Hindi: कृषि उत्पाद विपणन नीति | 3 | **p1** (1.00, label 0.00) | ✅ **ADJUDICATED: doc_004 p3 correct (owner, typo corrected); dismissed** |
| q_043 | short_ambiguous | [3–7] | **p1** (0.55) | ✅ **ADJUDICATED: Forms 1–9 live on p3–p6; label [3,4,5,6]** (p7 dropped) |
| q_044 | short_ambiguous | 19 | **p20** (0.89 vs 0.39) | ✅ **ADJUDICATED: label 19→20** |
| q_046 | short_ambiguous | 26 | **p24** (0.79 vs 0.43) | ✅ **ADJUDICATED: label 26→24** |
| q_048 | "when does the act come into force" | 1 | **p5** (0.64, label 0.00) | ✅ **ADJUDICATED: label p1 correct; dismissed** |
| q_049 | cattle compensation (dead cow) | 9 | **p10** (0.93 vs 0.21) | ✅ **ADJUDICATED: label 9→10** (note q_045 same content = p7) |

*Pattern worth noting: five "best evidence p1" flags (q_011/q_018/q_036/q_043 + others) — first pages of gazettes are often summary/notification pages that quote the same content; decide whether the summary page or the substantive page is the "right" citation target (recommendation: substantive page; treat p1-summary hits as correct-but-not-preferred).*

*Render evidence (2026-08-23, `scripts/render_page_evidence.py` → `adjudication/<qid>/`, gitignored): q_009's renders show Section 9 verbatim on viewer **p5** ("penal for contravention", 5 years / 10,000 rupees) while labeled p4 carries Section 7 with no S.9 — the earlier "S.9 ON p4" vision call looks like a page slip; label likely 4→5, owner's call. All 11 items have label+best-evidence page renders with needle highlights on digital pages.*

## G. Standing integrity (2026-08-23)

- `scripts/answer_evidence_pass.py` — rerunnable full-corpus answer verification.
- Worker logs `page_coverage_gap` when chunks miss PDF pages (**NOT yet deployed** — code landed in `56b818a` but the live worker is still rev `00080-h5l`, which predates it; ships with the next deploy).
- Canary assertion 6: sum of `/doc-status` pages across the 8 golden docs vs `EXPECTED_TOTAL_PAGES` (default **201**; the earlier "185" was our own mis-sum, caught by this very check on its first run).

## E. Already fixed (round 1)

10 off-by-one labels corrected (+1; 6 confirmed via PDF text layer = independent ground truth, 4 via VLM OCR text = one-source, visual spot-check pending — see `scripts/fix_golden_pages.py`).
