import json
from pathlib import Path

from src.ingest.parse_article import parse_article

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "requirements" / "_units.jsonl"


def main():
    rows = []
    for article in ("12", "13", "14"):
        rows.extend(parse_article(RAW / f"dsgvo_art{article}.html", article))
    with OUT.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(rows)} units -> {OUT}")


if __name__ == "__main__":
    main()
