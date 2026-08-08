"""Deep dive into Docling v2 API item structure."""
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("test-docs/testhindiwritten.pdf")
doc = result.document

print(f"Docling version: {__import__('docling').__version__}")
print()

# SAMPLE_ITEMS (use iterate_items for deep inspection)
items = list(doc.iterate_items())
print(f"Total items: {len(items)}")

# Check first non-empty item with all its attributes
for i, it in enumerate(items):
    # Get type and all public attributes
    cls = type(it)
    print(f"\n=== Item [{i}] === class: {cls.__module__}.{cls.__qualname__}")
    
    # Try common accessors
    for attr in ["text", "label", "caption", "type", "kind", "name", "category"]:
        val = getattr(it, attr, None)
        if val is not None:
            print(f"  .{attr} = {str(val)[:100]!r}")
    
    # Check for resolved_text
    val = getattr(it, "resolved_text", None)
    if val is not None:
        print(f"  .resolved_text = {str(val)[:100]!r}")
    
    # Check for prov (provenance with bbox)
    prov = getattr(it, "prov", None)
    if prov:
        print(f"  .prov exists, type={type(prov)}")
        if isinstance(prov, list) and prov:
            p0 = prov[0]
            bbox = getattr(p0, "bbox", None)
            if bbox:
                print(f"  .prov[0].bbox = {bbox}")
    
    if i >= 5:
        print(f"\n... (showing first 6 of {len(items)} items)")
        break

# Check body.children API
print(f"\n=== Body API ===")
body = doc.body
print(f"body type: {type(body)}")
for attr in ["children", "items", "elements"]:
    val = getattr(body, attr, None)
    if val is not None:
        print(f"body.{attr}: {type(val)} len={len(val) if hasattr(val, '__len__') else 'N/A'}")
        if hasattr(val, '__len__') and len(val) > 0:
            first = val[0] if hasattr(val, '__getitem__') else next(iter(val))
            print(f"  first type: {type(first).__qualname__}")
            for a in ["label", "text", "kind"]:
                v = getattr(first, a, None)
                if v is not None:
                    print(f"  first.{a} = {str(v)[:80]!r}")
