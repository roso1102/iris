# OCR, Layout, and Bounding-Box Decision Plan

## Decision summary

**Yes—Google Enterprise Document OCR can provide correctly mapped bounding boxes for scanned PDFs**, because its response includes word/line layout polygons, normalized vertices in `[0,1]`, page dimensions, orientation and text anchors. Google defines the coordinate origin as the top-left of the original image/page. It also supports printed text, handwriting, language detection, rotation correction and document-quality signals.

Correct overlay is conditional on IRIS preserving the page geometry contract and mapping the exact OCR spans used by a chunk. The vendor output alone does not fix current behavior: assigning full-page OCR text to a Docling element bbox will remain wrong regardless of OCR quality.

Official references checked on 2026-09-07:

- [Document AI `Document` and `BoundingPoly` reference](https://docs.cloud.google.com/document-ai/docs/reference/rest/v1/Document) — normalized vertices are relative to the original image, range 0–1, and use top-left `y` origin.
- [Enterprise Document OCR](https://docs.cloud.google.com/document-ai/docs/enterprise-document-ocr) — words/lines/blocks, handwriting, deskew/rotation, languages, confidence and quality analysis.
- [Processor list](https://docs.cloud.google.com/document-ai/docs/processors-list) — Enterprise OCR supports 200+ languages, `asia-south1`, 15 synchronous pages and up to 500 asynchronous pages per document.
- [Document AI limits](https://docs.cloud.google.com/document-ai/limits) — 40 MB synchronous, 1 GB batch, and processor-specific page limits.
- [Layout Parser quickstart](https://docs.cloud.google.com/document-ai/docs/layout-parse-quickstart) — bbox support is documented only for `pretrained-layout-parser-v1.0-2024-06-03`; this is why Layout Parser must not automatically become the canonical geometry source.

## Why the current scanned bbox cannot work

1. Docling OCR is disabled.
2. Full-page Gemini OCR returns only text, not word/line polygons.
3. That full-page text is attached to the original low-quality element bbox or `[0,0,1,1]`.
4. Every split chunk reuses the same coarse box.
5. Numerical range validation only proves a box is on-page, not that it covers the cited text.

This is an information-loss problem. No frontend transform can recover coordinates that the OCR response never produced.

## Canonical spatial model

```text
PageGeometry
  source_page_number
  width, height, unit
  media_box, crop_box
  pdf_rotation
  render_dpi
  source_to_view_matrix
  coordinate_space_id

OcrSpan
  span_id
  text_anchor_start/end
  original_text
  normalized_text
  page_number
  polygon: [{x,y}, ...]
  confidence
  language, script, is_handwritten
  engine, engine_version
  coordinate_space_id

ChunkV2
  chunk_id
  source_span_ids[]
  source_polygons[]
  derived_bounding_rectangle
  geometry_confidence
  fallback_level: exact | line | block | page
```

Polygons, not a single rectangle, are canonical. One citation can cover disjoint lines or table cells.

## Mapping Google coordinates to the viewer

Document AI normalized vertices are top-left relative coordinates. If the frontend renders the same original PDF page with its visible crop and rotation correctly applied, a normalized overlay is:

```text
left_percent   = 100 × min(x_normalized)
top_percent    = 100 × min(y_normalized)
width_percent  = 100 × (max(x_normalized) - min(x_normalized))
height_percent = 100 × (max(y_normalized) - min(y_normalized))
```

For pixel rendering of an unrotated viewport:

```text
x_px = x_normalized × viewport_width
y_px = y_normalized × viewport_height
```

For PDF-point storage with a top-left application convention:

```text
x_pt = crop_left + x_normalized × crop_width
y_pt = crop_top  + y_normalized × crop_height
```

Do not add the current unconditional bottom-left Y flip to Google normalized vertices. Rotation/crop transforms must be applied exactly once by a shared geometry library. The test suite must cover viewer rotations 0/90/180/270 degrees, non-default CropBox/MediaBox, skewed scans, landscape pages and split-page preservation.

### Required integration method

1. Submit the original PDF or a losslessly split page retaining page boxes/rotation.
2. Store the returned `Document.Page.pageNumber`, dimensions and orientation.
3. Build spans from `textAnchor` offsets and word/line layouts.
4. Chunk the canonical `Document.text` by ranges that align to spans.
5. Attach all overlapping source span IDs and polygons to the chunk.
6. Render the original PDF, not a differently cropped/rescaled derivative.
7. When geometry confidence fails, downgrade the citation to line/block/page level and expose that state.

## Recommended three-lane parser architecture

### Lane A — Clean digital PDF

- PyMuPDF native spans and font/layout metadata.
- Fast and cheap; strongest coordinate alignment for embedded text.
- Route to another lane when text coverage, encoding quality or reading-order confidence is poor.

### Lane B — Scanned, garbled, mixed-language, or handwritten page

- Google Enterprise Document OCR with pinned processor version.
- Enable native PDF parsing only when the bake-off demonstrates benefit for the selected lane.
- Preserve word/line polygons, confidence, detected language, handwriting/style and quality defects.
- Use asynchronous batch for large documents when latency requirements allow, or page/shard online requests under quota for interactive ingestion.

### Lane C — Complex layout, tables, and private/local processing

- Benchmark Docling for hierarchy/tables and environments that cannot send data to managed OCR.
- If Docling remains, read and honor its actual coordinate-origin value; do not assume bottom-left.
- Enable a structured OCR engine for scanned pages if this lane must handle scans.
- Optionally merge Google Layout Parser hierarchy with Enterprise OCR geometry through text-anchor alignment, but never accept mismatched hierarchy/geometry silently.

## Docling decision

Docling is **not required as the universal parser**. Keep it only if Phase 4.0 proves measurable value on table structure, reading order, cost, privacy or offline operation. Delete it from the default clean/scan path if PyMuPDF + Enterprise OCR meets all gates.

Decision criteria:

| Criterion | Weight |
|---|---:|
| OCR/CER/WER and spatial accuracy | 30% |
| Tables/reading order/layout hierarchy | 20% |
| Multilingual/handwriting protected slices | 15% |
| Latency/throughput/cold start | 10% |
| Cost per page | 10% |
| Privacy/residency/offline requirement | 10% |
| Operational complexity/version stability | 5% |

No weighted average may override a hard security or bbox threshold.

## Phase 4.0 bake-off design

### Dataset

At least 300 annotated pages:

- 60 clean digital PDFs with varying crop/rotation/font/layout.
- 60 English printed scans across DPI/blur/skew/noise.
- 75 Hindi/Devanagari and selected regional-language scans.
- 30 mixed-script pages.
- 30 handwritten or hand-annotated pages.
- 30 table/form pages.
- 15 adversarial geometry pages: landscape, unusual CropBox, rotated, clipped and multi-column.

### Ground truth

- Human-adjudicated transcription.
- Word/line polygons on the rendered original page.
- Reading order.
- Table cell grid, values and header associations.
- Two annotators for at least 20%; resolve disagreements and report inter-annotator agreement.

### Gates

| Metric | Digital | Scanned print | Hindi/regional | Handwriting automatic path |
|---|---:|---:|---:|---:|
| Line median IoU | >=0.95 | >=0.90 | >=0.88 | >=0.80 |
| Word median IoU | >=0.90 | >=0.85 | >=0.82 | baseline + approved threshold |
| Center containment | >=0.99 | >=0.95 | >=0.93 | >=0.90 |
| Text-weighted citation coverage | >=0.98 | >=0.95 | >=0.90 | >=0.85 |
| WER | <=2% | <=5% | <=10% | <=20% or manual review |
| Reading-order Kendall tau | >=0.95 | >=0.90 | >=0.90 | >=0.85 |

Tables additionally require >=0.90 cell-value F1 and >=0.90 row/header association F1 for automatic structured use.

### Cost and reliability measurements

- Billed and estimated cost/page by lane and document type.
- P50/P95 processing latency and pages/minute.
- Cold-start memory and CPU.
- Quota behavior and retry rate.
- Percentage routed to managed OCR, Docling, and manual review.
- Repeat-run cache effectiveness.

## Failure policy

- Missing geometry: never label precise; use page fallback or review.
- Low OCR confidence: retain raw artifact and route/review.
- Text/polygon offset mismatch: fail the page stage, do not zip or guess.
- Unsupported/encrypted/corrupt document: terminal reason code and user-visible remediation.
- Provider quota/outage: retry under budget, retain stage artifact, then DLQ without losing document state.
