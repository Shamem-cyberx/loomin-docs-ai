"""One-off: print extractable text from a PDF (requires PyMuPDF)."""
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    print("ERROR: pip install PyMuPDF", file=sys.stderr)
    sys.exit(2)

path = Path(sys.argv[1] if len(sys.argv) > 1 else "Luna_the_Dream_Keeper.pdf")
doc = fitz.open(path)
parts = []
for i in range(min(len(doc), 5)):
    parts.append(doc[i].get_text("text") or "")
doc.close()
text = "\n".join(parts).strip()
print(text[:6000] if text else "(no extractable text — may be image-only PDF)")
print("\n---\nchars:", len(text))
