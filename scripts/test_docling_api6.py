"""Figure out Docling v2 page_no and bbox access."""
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("test-docs/testhindiwritten.pdf")
doc = result.document

for child in doc.body.children:
    item = child.resolve(doc)
    lbl = getattr(item, "label", None)
    if str(lbl) == "text":
        # Check prov
        prov = item.prov
        if prov:
            print(f"label={lbl} text={item.text[:50]!r}")
            print(f"  prov type={type(prov)}")
            for p in prov[:1]:
                print(f"  prov[0] attrs: {[a for a in dir(p) if not a.startswith('_')]}")
                for a in ["page_no", "page", "bbox", "geo"]:
                    v = getattr(p, a, None)
                    if v is not None:
                        print(f"  prov[0].{a} = {v}")
        break

# Also check only_eng_india.pdf
print("\n--- only_eng_india.pdf ---")
result2 = converter.convert("test-docs/only_eng_india.pdf")
doc2 = result2.document
from collections import Counter
labels2 = Counter()
above_150 = 0
below_150 = 0
for child in doc2.body.children:
    item = child.resolve(doc2)
    lbl = str(getattr(item, "label", None))
    labels2[lbl] += 1
    txt = getattr(item, "text", "") or ""
    if len(txt) >= 150:
        above_150 += 1
    else:
        below_150 += 1

print(f"Labels: {dict(labels2)}")
print(f">=150 chars: {above_150}, <150 chars: {below_150}")
print(f"Total items: {len(doc2.body.children)}")
