import json

PROMPT = """Du prüfst, ob eine Bedingung für ein Dokument zutrifft.

BEDINGUNG: {condition}

AUSZÜGE AUS DEM DOKUMENT:
{passages}

Trifft die Bedingung auf dieses Dokument zu, basierend auf den Auszügen?
- "applicable": Ja, die Bedingung trifft klar zu (z.B. das Dokument erwaehnt
  Einwilligung als Rechtsgrundlage).
- "not_applicable": Nein, die Bedingung trifft klar nicht zu.
- "unknown": Aus den Auszügen laesst sich das nicht sicher entscheiden.

Antworte NUR mit JSON: {{"applicability": "...", "rationale": "ein Satz"}}
"""


def build(condition: str, chunks: list[dict]) -> str:
    passages = "\n\n".join(f"[{i}] {c['content']}" for i, c in enumerate(chunks, 1))
    return PROMPT.format(condition=condition, passages=passages)


def parse(raw: str) -> dict:
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    return json.loads(cleaned.strip())
