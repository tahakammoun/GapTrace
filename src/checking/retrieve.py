from src.db import connect

SQL = """
SELECT c.id, c.content, c.ordinal, 1 - (c.embedding <=> r.embedding) AS score
FROM chunks c, requirements r
WHERE c.document_id = %(doc)s AND r.id = %(req)s
ORDER BY c.embedding <=> r.embedding
LIMIT %(k)s
"""


# Default k, not a universal constant: measured against the eval gold matrix
# for target1_bahn.html (20 chunks total after the 2500-char chunk size), most
# of the remaining not_found errors had their real answer ranked 6-17th, not
# hopelessly buried. k=15 caught more of them but its ~35k-char prompt hit a
# 413 from Groq (too large), silently losing the fallback provider exactly
# when Gemini's quota runs out -- which it reliably does. k=10 trades some of
# that recall for keeping both providers actually usable. Re-check with
# src/eval/metrics.py on a larger target before assuming this k still makes
# sense there.
def top_chunks(document_id: int, requirement_id: int, k: int = 10) -> list[dict]:
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(SQL, {"doc": document_id, "req": requirement_id, "k": k})
        return [
            {"id": i, "content": c, "ordinal": o, "score": s}
            for i, c, o, s in cur.fetchall()
        ]
