from src.db import connect

SQL = """
SELECT c.id, c.content, c.ordinal, 1 - (c.embedding <=> r.embedding) AS score
FROM chunks c, requirements r
WHERE c.document_id = %(doc)s AND r.id = %(req)s
ORDER BY c.embedding <=> r.embedding
LIMIT %(k)s
"""


def top_chunks(document_id: int, requirement_id: int, k: int = 5) -> list[dict]:
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(SQL, {"doc": document_id, "req": requirement_id, "k": k})
        return [
            {"id": i, "content": c, "ordinal": o, "score": s}
            for i, c, o, s in cur.fetchall()
        ]
