"""Quick test to understand Docling v2 API shape."""
import time
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
print("Converting testhindiwritten.pdf...")
t0 = time.time()
result = converter.convert("test-docs/testhindiwritten.pdf")
doc = result.document
t1 = time.time()
print(f"Done in {t1-t0:.1f}s")

print(f"doc type: {type(doc)}")
print(f"doc.pages keys: {list(doc.pages.keys())[:3] if hasattr(doc, 'pages') else 'N/A'}")

if hasattr(doc, "pages"):
    pg1 = doc.pages[1]
    print(f"page1 type: {type(pg1)}")
    attrs = [a for a in dir(pg1) if not a.startswith("_")]
    print(f"page1 attrs: {attrs[:15]}")

if hasattr(doc, "iterate_items"):
    items = list(doc.iterate_items())
    print(f"\niterate_items: {len(items)} items")
    from collections import Counter
    labels = Counter()
    for it in items:
        lbl = str(getattr(it, "label", "N/A"))
        labels[lbl] += 1
    print(f"Label distribution: {dict(labels)}")

    for i, it in enumerate(items[:5]):
        lbl = getattr(it, "label", "N/A")
        txt = getattr(it, "text", "") or ""
        print(f"  [{i}] label={lbl} text_len={len(txt)} text={txt[:80]!r}")
