import re
from pathlib import Path

from bs4 import BeautifulSoup

JUNK = "script, style, nav, header, footer, aside, .screen-reader-text, .skip-link, .entry-meta"
BLOCK_TAGS = ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "td", "th"]


def parse_html(path: str | Path) -> str:
    """Extract text with real paragraph breaks between block elements.

    A single get_text(sep) over the whole tree can't tell inline elements
    (<a>, <span>, ...) from block ones (<p>, <li>, ...), so one separator
    either glues paragraphs together or fragments sentences at every link.
    Extracting block-by-block and joining inline content with " " keeps
    cross-reference links inside their sentence; joining blocks with "\n\n"
    gives chunk_text real paragraph boundaries to split on.
    """
    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8"), "html.parser")
    for tag in soup.select(JUNK):
        tag.decompose()

    blocks = [b for b in soup.find_all(BLOCK_TAGS) if not b.find_parent(BLOCK_TAGS)]
    if not blocks:
        blocks = [soup]

    paras = []
    for block in blocks:
        text = re.sub(r"\s+", " ", block.get_text(" ", strip=True)).strip()
        if text:
            paras.append(text)
    return "\n\n".join(paras)
