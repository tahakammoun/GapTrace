import json
from pathlib import Path

from src.db import connect
from src.ingest.embed import embed_passages

ROOT = Path(__file__).resolve().parent.parent.parent

SOURCE_URL = "https://eur-lex.europa.eu/legal-content/DE/TXT/PDF/?uri=CELEX%3A02016R0679-20160504"
SOURCE_NOTE = "Struktur aus dsgvo-gesetz.de; refs und Wortlaut (legal_text) gegen EUR-Lex geprueft"


def load_catalog(name: str, title: str, version: str = "v1") -> int:
    path = ROOT / "requirements" / f"{name}.jsonl"
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    # embed the checkable paraphrase (requirement), not the raw legal wording
    vectors = embed_passages([r["requirement"] for r in rows])

    with connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO regulations (name, title, version, source_url, source_note) "
            "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (name) DO UPDATE SET "
            "title=EXCLUDED.title, version=EXCLUDED.version, "
            "source_url=EXCLUDED.source_url, source_note=EXCLUDED.source_note RETURNING id",
            (name, title, version, SOURCE_URL, SOURCE_NOTE),
        )
        regulation_id = cur.fetchone()[0]

        cur.execute("DELETE FROM requirements WHERE regulation_id = %s", (regulation_id,))
        for row, vec in zip(rows, vectors, strict=True):
            cur.execute(
                "INSERT INTO requirements (regulation_id, key, ref, legal_text, requirement, "
                "condition, obligation, category, ref_verified, embedding) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    regulation_id,
                    row["key"],
                    row["ref"],
                    row.get("legal_text"),
                    row["requirement"],
                    row.get("condition"),
                    row.get("obligation", "must"),
                    row.get("category"),
                    row.get("ref_verified", False),
                    vec,
                ),
            )
        conn.commit()
    return len(rows)


if __name__ == "__main__":
    n = load_catalog("dsgvo_art12_14", "DSGVO Art. 12-14 Informationspflichten")
    print(f"loaded {n} requirements")
