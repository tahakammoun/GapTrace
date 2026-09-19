import copy
import re
from pathlib import Path

from bs4 import BeautifulSoup

JUNK = "script, style, nav, header, footer, aside, .screen-reader-text, .skip-link, .entry-meta"


def _clean(tag) -> str:
    clone = copy.copy(tag)
    for sub in clone.find_all(["ol", "ul"]):
        sub.decompose()
    return re.sub(r"\s+", " ", clone.get_text(" ", strip=True)).strip()


def _item_list(para):
    """Find the <ol> holding this paragraph's lettered items, drilling
    through any empty wrapper <ol> (e.g. Art. 12(5) double-wraps its
    sublist with no <li> at the outer level)."""
    ol = para.find("ol", recursive=False)
    while ol is not None and not ol.find_all("li", recursive=False):
        inner = ol.find("ol", recursive=False)
        if inner is None:
            raise ValueError(f"<ol> with no <li> and no nested <ol> under: {para}")
        ol = inner
    return ol


def parse_article(path: str | Path, article: str) -> list[dict]:
    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8"), "html.parser")
    for tag in soup.select(JUNK):
        tag.decompose()

    root = soup.find("article") or soup.find("main") or soup.body
    tops = [ol for ol in root.find_all("ol") if not ol.find_parents("ol")]
    if not tops:
        raise ValueError("no top-level <ol> found; check dump_structure output")

    out = []
    for top in tops:
        base = int(top.get("start", 1))
        for offset, para in enumerate(top.find_all("li", recursive=False)):
            i = base + offset
            lead = _clean(para)
            nested = _item_list(para)
            if nested:
                nbase = int(nested.get("start", 1))
                for noff, item in enumerate(nested.find_all("li", recursive=False)):
                    j = nbase + noff
                    out.append(
                        {
                            "ref": f"Art. {article}({i})({chr(96 + j)})",
                            "lead": lead,
                            "text": _clean(item),
                        }
                    )
            else:
                out.append({"ref": f"Art. {article}({i})", "lead": "", "text": lead})
    return out
