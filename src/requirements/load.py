import json
from pathlib import Path

from src.db import connect
from src.ingest.embed import embed_queries

ROOT = Path(__file__).resolve().parent.parent.parent

SOURCE_URL = "https://eur-lex.europa.eu/legal-content/DE/TXT/PDF/?uri=CELEX%3A02016R0679-20160504"
SOURCE_NOTE = "Struktur aus dsgvo-gesetz.de; refs und Wortlaut (legal_text) gegen EUR-Lex geprueft"


def load_catalog(name: str, title: str, version: str = "v1") -> int:
    path = ROOT / "requirements" / f"{name}.jsonl"
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    # embed the checkable paraphrase (requirement) as a QUERY: at check time we're
    # asking "which chunks satisfy this requirement", a query->passage retrieval,
    # not passage->passage -- e5 models are trained on that asymmetry specifically.
    vectors = embed_queries([r["requirement"] for r in rows])

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

        # Upsert by (regulation_id, key) rather than delete-then-insert: findings
        # reference requirements.id with ON DELETE CASCADE, so a blanket delete
        # here would silently wipe every finding ever recorded against this
        # catalog. Reloading (e.g. to refresh embeddings) must preserve ids.
        for row, vec in zip(rows, vectors, strict=True):
            cur.execute(
                "INSERT INTO requirements (regulation_id, key, ref, legal_text, requirement, "
                "condition, obligation, category, ref_verified, embedding) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (regulation_id, key) DO UPDATE SET "
                "ref=EXCLUDED.ref, legal_text=EXCLUDED.legal_text, "
                "requirement=EXCLUDED.requirement, "
                "condition=EXCLUDED.condition, obligation=EXCLUDED.obligation, "
                "category=EXCLUDED.category, ref_verified=EXCLUDED.ref_verified, "
                "embedding=EXCLUDED.embedding",
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
