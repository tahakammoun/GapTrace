import sys
from pathlib import Path

from bs4 import BeautifulSoup

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

JUNK = "script, style, nav, header, footer, aside, .screen-reader-text, .skip-link, .entry-meta"


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "dsgvo_art13.html"
    soup = BeautifulSoup((RAW / name).read_text(encoding="utf-8"), "html.parser")
    for tag in soup.select(JUNK):
        tag.decompose()
    for ol in soup.find_all("ol"):
        depth = len(ol.find_parents("ol"))
        items = ol.find_all("li", recursive=False)
        print(
            f"{'  ' * depth}<ol> depth={depth} items={len(items)} "
            f"parent={ol.parent.name}.{ol.parent.get('class')}"
        )


if __name__ == "__main__":
    main()
