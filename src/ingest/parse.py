from pathlib import Path

import fitz


def parse_pdf(path: str | Path) -> list[tuple[int, str]]:
    doc = fitz.open(path)
    try:
        return [(i, page.get_text("text")) for i, page in enumerate(doc, start=1)]
    finally:
        doc.close()
