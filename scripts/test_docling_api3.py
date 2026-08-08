"""Fix doc: test Docling v2.117 API with correct item access."""
from docling.document_converter import DocumentConverter
from collections import Counter

converter = DocumentConverter()
result = converter.convert("test-docs/testhindiwritten.pdf")
doc = result.document

# Check body.children -- they are RefItems, need doc[ref] lookup
children = doc.body.children
print(f"body.children: {len(children)} items")
print(f"First child: {type(children[0]).__qualname__}")
print(f"First child dir: {[a for a in dir(children[0]) if not a.startswith('_')][:10]}")
print()

# Resolve first child via doc[child]
first_ref = children[0]
resolved = doc[first_ref]
print(f"doc[first_ref] type: {type(resolved).__qualname__}")
print(f"resolved attrs: {[a for a in dir(resolved) if not a.startswith('_')][:15]}")
print()

# Check key fields
for attr in ["label", "text", "kind", "type", "page_no", "bbox"]:
    val = getattr(resolved, attr, None)
    if val is not None:
        print(f"  .{attr} = {str(val)[:100]!r}")

# Check prov for bbox
prov = getattr(resolved, "prov", None)
if prov:
    print(f"  .prov: {type(prov)}")
    if isinstance(prov, list) and prov:
        p0 = prov[0]
        bbox = getattr(p0, "bbox", None)
        print(f"  .prov[0].bbox: {bbox}")
        geo = getattr(p0, "geo", None)
        print(f"  .prov[0].geo: {geo}")

print()

# Now iterate all body children and check labels
labels = Counter()
text_lens = []
for child in children:
    item = doc[child]
    lbl = getattr(item, "label", None)
    lbl_str = str(lbl) if lbl is not None else "None"
    labels[lbl_str] += 1
    txt = getattr(item, "text", "") or ""
    text_lens.append(len(txt))

print(f"Label distribution: {dict(labels)}")
print(f"Text length range: min={min(text_lens)} max={max(text_lens)} avg={sum(text_lens)/len(text_lens):.0f}")

# Show first 8 resolved items
for i, child in enumerate(children[:8]):
    item = doc[child]
    lbl = getattr(item, "label", None)
    txt = getattr(item, "text", "") or ""
    page = getattr(item, "page_no", None)
    print(f"  [{i}] label={lbl} page={page} text_len={len(txt)} text={txt[:70]!r}")
