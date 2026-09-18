from pathlib import Path

from bs4 import BeautifulSoup


def parse_html(path: str | Path) -> str:
    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8"), "html.parser")
    for tag in soup.select("script, style, nav, header, footer, aside, "
                           ".screen-reader-text, .skip-link, .entry-meta"):
        tag.decompose()
    return soup.get_text("\n", strip=True)
