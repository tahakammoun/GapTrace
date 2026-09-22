import hashlib
from pathlib import Path

from src.config import DEFAULT_COLLECTION
from src.db import connect
from src.ingest.chunk import chunk_text
from src.ingest.embed import embed_passages
from src.ingest.parse import parse_pdf
from src.ingest.parse_html import parse_html


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return "\n\n".join(t for _, t in parse_pdf(path))
    return parse_html(path)


def ingest(path: str | Path, collection: str = DEFAULT_COLLECTION) -> int:
    path = Path(path)
    text = extract_text(path)
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError(f"no text extracted from {path.name}")
    vectors = embed_passages(chunks)
    checksum = hashlib.sha256(text.encode()).hexdigest()[:16]

    with connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO collections (name, title) VALUES (%s, %s) "
            "ON CONFLICT (name) DO UPDATE SET title = EXCLUDED.title RETURNING id",
            (collection, "Target documents"),
        )
        collection_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO documents (collection_id, filename, checksum) VALUES (%s, %s, %s) "
            "ON CONFLICT (collection_id, filename) DO UPDATE SET checksum = EXCLUDED.checksum "
            "RETURNING id",
            (collection_id, path.name, checksum),
        )
        document_id = cur.fetchone()[0]

        cur.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
        for ordinal, (content, vec) in enumerate(zip(chunks, vectors, strict=True)):
            cur.execute(
                "INSERT INTO chunks (document_id, ordinal, content, embedding) "
                "VALUES (%s, %s, %s, %s)",
                (document_id, ordinal, content, vec),
            )
        conn.commit()
    return len(chunks)


if __name__ == "__main__":
    import sys

    n = ingest(sys.argv[1])
    print(f"{n} chunks")
