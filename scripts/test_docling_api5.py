"""Figure out Docling v2.117 item access using RefItem.resolve()."""
from docling.document_converter import DocumentConverter
from collections import Counter

converter = DocumentConverter()
result = converter.convert("test-docs/testhindiwritten.pdf")
doc = result.document

children = doc.body.children
print(f"body.children: {len(children)}")

# RefItem has .resolve() method
ref = children[0]
resolved = ref.resolve(doc)
print(f"ref.cref={ref.cref}")
print(f"resolved type: {type(resolved).__qualname__}")
print(f"resolved attrs: {[a for a in dir(resolved) if not a.startswith('_')]}")

for attr in ["label", "text", "page_no", "bbox"]:
    val = getattr(resolved, attr, None)
    if val is not None:
        print(f"  .{attr} = {str(val)[:100]}")

# Now iterate and resolve all
labels = Counter()
text_lens = []
for child in children:
    item = child.resolve(doc)
    lbl = getattr(item, "label", None)
    lbl_str = str(lbl) if lbl is not None else "None"
    labels[lbl_str] += 1
    txt = getattr(item, "text", "") or ""
    text_lens.append(len(txt))

print(f"\nLabel distribution: {dict(labels)}")
print(f"Text lens: min={min(text_lens)} max={max(text_lens)} avg={sum(text_lens)/len(text_lens):.0f}")

# Show first 10
for i, child in enumerate(children[:10]):
    item = child.resolve(doc)
    lbl = getattr(item, "label", None)
    txt = getattr(item, "text", "") or ""
    pg = getattr(item, "page_no", None)
    print(f"  [{i}] label={lbl} page={pg} text_len={len(txt)} text={txt[:80]!r}")
