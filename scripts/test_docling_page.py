"""Check page dimensions in Docling v2."""
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("test-docs/testhindiwritten.pdf")
doc = result.document

print(f"Pages: {list(doc.pages.keys())}")
pg1 = doc.pages[1]
print(f"Page 1 attrs: {[a for a in dir(pg1) if not a.startswith('_')]}")

# Check page dimensions
img = pg1.image
if img is not None:
    print(f"Page 1 image type: {type(img)}")
    print(f"Page 1 image attrs: {[a for a in dir(img) if not a.startswith('_')]}")

# Check page size from document
if hasattr(doc, "pages"):
    for pno in list(doc.pages.keys())[:1]:
        pg = doc.pages[pno]
        print(f"\nPage {pno} size: {pg.size if hasattr(pg, 'size') else 'N/A'}")

# Check only_eng page dimensions (last page)
result2 = converter.convert("test-docs/only_eng_india.pdf")
doc2 = result2.document
pg = list(doc2.pages.values())[0]
if hasattr(pg, 'size'):
    print(f"only_eng pg1 size: {pg.size}")
if hasattr(pg, 'image') and pg.image:
    print(f"only_eng pg1 image: {type(pg.image)}, size: {pg.image.size if hasattr(pg.image, 'size') else 'N/A'}")
