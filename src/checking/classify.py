import json

PROMPT = """Du prüfst, ob ein Dokument eine konkrete Rechtspflicht erfüllt.

ANFORDERUNG ({ref}):
{requirement}

AUSZÜGE AUS DEM DOKUMENT:
{passages}

Entscheide:
- "addressed": Die Anforderung ist vollstaendig erfuellt.
- "partial": Das Thema wird angesprochen, aber unvollstaendig oder unklar.
- "not_found": In den Auszuegen steht nichts dazu.

Regeln:
- evidence muss ein WOERTLICHES Zitat aus genau einem Auszug sein. Nichts umformulieren.
- Bei "not_found": evidence = "" und passage = null.
- rationale: ein Satz.
- confidence: 0.0 bis 1.0.

Antworte NUR mit JSON:
{{"status": "...", "passage": 1, "evidence": "...", "rationale": "...", "confidence": 0.0}}
"""


def build(requirement: dict, chunks: list[dict]) -> str:
    passages = "\n\n".join(
        f"[{i}]\n{c['content']}" for i, c in enumerate(chunks, start=1)
    )
    return PROMPT.format(
        ref=requirement["ref"], requirement=requirement["text"], passages=passages
    )


def parse(raw: str) -> dict:
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    return json.loads(cleaned.strip())


def verify_evidence(result: dict, chunks: list[dict]) -> tuple[bool, int | None]:
    if result["status"] == "not_found":
        return True, None
    quote = (result.get("evidence") or "").strip()
    idx = result.get("passage")
    if not quote or not isinstance(idx, int) or not 1 <= idx <= len(chunks):
        return False, None
    chunk = chunks[idx - 1]
    return (quote in chunk["content"]), chunk["id"]
