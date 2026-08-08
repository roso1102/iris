"""Figure out Docling v2.117 item access."""
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("test-docs/testhindiwritten.pdf")
doc = result.document

children = doc.body.children
print(f"body.children: {len(children)}")

# Check RefItem
ref = children[0]
print(f"\nRefItem: {ref}")
print(f"RefItem attrs: {[a for a in dir(ref) if not a.startswith('_')]}")
print(f"cref: {ref.cref}")

# Try doc lookup methods
for method in ["get", "get_by_path", "get_by_cref", "find", "resolve", "lookup"]:
    fn = getattr(doc, method, None)
    if fn and callable(fn):
        print(f"\ndoc.{method} exists, trying with {ref.cref}...")
        try:
            r = fn(ref.cref)
            print(f"  result type: {type(r).__qualname__}")
            for a in ["label", "text", "page_no"]:
                v = getattr(r, a, None)
                if v is not None:
                    print(f"  .{a} = {str(v)[:80]}")
            break
        except Exception as e:
            print(f"  failed: {e}")

# Also try on first non-empty child
for child in children[:10]:
    ref_path = child.cref
    print(f"\nTrying to resolve: {ref_path}")
    try:
        r = doc.get(ref_path)
        if r is not None:
            lbl = getattr(r, "label", "N/A")
            txt = getattr(r, "text", "")
            print(f"  RESOLVED -> {type(r).__qualname__} label={lbl} text_len={len(txt or '')}")
    except Exception as e:
        print(f"  doc.get: {e}")
        break
