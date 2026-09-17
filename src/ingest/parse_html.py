from pathlib import Path

from bs4 import BeautifulSoup


def parse_html(path: str | Path) -> str:
    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8"), "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)
