import numpy as np

from src.config import EMBEDDING_DIM
from src.db import connect


def main():
    vec = np.random.rand(EMBEDDING_DIM).astype(np.float32)
    vec /= np.linalg.norm(vec)

    with connect() as conn:
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO collections (name, title) VALUES (%s, %s) "
            "ON CONFLICT (name) DO UPDATE SET title = EXCLUDED.title RETURNING id",
            ("_smoke", "Smoke test"),
        )
        collection_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO documents (collection_id, filename) VALUES (%s, %s) "
            "ON CONFLICT (collection_id, filename) DO UPDATE SET title = NULL RETURNING id",
            (collection_id, "_smoke.pdf"),
        )
        document_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO chunks (document_id, ordinal, page, content, embedding) "
            "VALUES (%s, %s, %s, %s, %s)",
            (document_id, 0, 1, "smoke test chunk", vec),
        )

        cur.execute(
            "SELECT content, 1 - (embedding <=> %s) AS score "
            "FROM chunks ORDER BY embedding <=> %s LIMIT 1",
            (vec, vec),
        )
        content, score = cur.fetchone()
        print(f"retrieved: {content!r}  score: {score:.4f}")

        cur.execute("DELETE FROM collections WHERE name = %s", ("_smoke",))
        conn.commit()
        print("cleaned up")


if __name__ == "__main__":
    main()
