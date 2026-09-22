import sys
from pathlib import Path

from src.checking import applicability as appl
from src.checking.classify import build, parse, verify_evidence
from src.checking.retrieve import top_chunks
from src.db import connect
from src.ingest.pipeline import ingest
from src.llm.client import complete

REGULATION = "dsgvo_art12_14"


def get_ids(filename: str) -> tuple[int, int, int]:
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM documents WHERE filename = %s", (filename,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"{filename} not ingested")
        document_id = row[0]
        cur.execute("SELECT id FROM regulations WHERE name = %s", (REGULATION,))
        regulation_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO targets (document_id, regulation_id) VALUES (%s, %s) "
            "ON CONFLICT (document_id, regulation_id) DO UPDATE SET created_at = now() "
            "RETURNING id",
            (document_id, regulation_id),
        )
        target_id = cur.fetchone()[0]
        conn.commit()
    return document_id, regulation_id, target_id


def check_applicability(document_id: int, req: dict) -> tuple[str, str]:
    if not req["condition"]:
        return "applicable", ""
    chunks = top_chunks(document_id, req["id"], k=8)
    result = appl.parse(complete(appl.build(req["condition"], chunks)))
    return result.get("applicability", "unknown"), result.get("rationale", "")


def run(filename: str):
    document_id, regulation_id, target_id = get_ids(filename)

    with connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, key, ref, requirement, condition FROM requirements "
            "WHERE regulation_id = %s ORDER BY id",
            (regulation_id,),
        )
        reqs = [
            {"id": i, "key": k, "ref": r, "text": t, "condition": c}
            for i, k, r, t, c in cur.fetchall()
        ]

    counts = {"addressed": 0, "partial": 0, "not_found": 0, "not_applicable": 0}
    invalid = 0

    for req in reqs:
        applicability, appl_reason = check_applicability(document_id, req)

        if applicability == "not_applicable":
            counts["not_applicable"] += 1
            result = {"status": "not_found", "confidence": None, "evidence": None,
                       "rationale": f"Bedingung nicht erfuellt: {appl_reason}"}
            chunk_id = None
        else:
            chunks = top_chunks(document_id, req["id"])
            result = parse(complete(build(req, chunks)))
            ok, chunk_id = verify_evidence(result, chunks)
            if not ok:
                invalid += 1
                result["status"] = "partial"
                result["confidence"] = min(result.get("confidence", 0.5), 0.3)
                prefix = "Beleg nicht woertlich auffindbar. "
                result["rationale"] = prefix + result.get("rationale", "")
                chunk_id = None
            counts[result["status"]] += 1

        with connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO findings (target_id, requirement_id, status, applicability, "
                "evidence_chunk, evidence_quote, rationale, confidence) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (target_id, requirement_id) DO UPDATE SET "
                "status=EXCLUDED.status, applicability=EXCLUDED.applicability, "
                "evidence_chunk=EXCLUDED.evidence_chunk, evidence_quote=EXCLUDED.evidence_quote, "
                "rationale=EXCLUDED.rationale, confidence=EXCLUDED.confidence",
                (target_id, req["id"], result["status"], applicability, chunk_id,
                 result.get("evidence"), result.get("rationale"), result.get("confidence")),
            )
            conn.commit()

        mark = {"addressed": "OK ", "partial": "~~ ", "not_found": "XX ",
                "not_applicable": "-- "}[
            "not_applicable" if applicability == "not_applicable" else result["status"]
        ]
        print(f"{mark} {req['ref']:20s} {req['text'][:50]}")

    print(f"\n{counts}   invalid evidence: {invalid}")


if __name__ == "__main__":
    path = Path(sys.argv[1])
    ingest(path)
    run(path.name)
