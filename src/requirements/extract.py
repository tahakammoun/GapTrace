import json
from pathlib import Path

from src.llm.client import AllProvidersExhausted, complete

SYSTEM = """Du extrahierst einzelne, pruefbare Anforderungen aus einem Rechtstext.

Regeln:
- Eine Anforderung = eine Sache, die ein Pruefer unabhaengig abhaken kann.
- Gib den Normtext sinngemaess, aber praezise wieder. Keine Interpretation.
- Formuliere jede Anforderung so, dass sie ohne Kontext verstaendlich ist.
- Bedingte Pflichten ("gegebenenfalls") bleiben eine Anforderung; die Bedingung
  gehoert in den Text.
- obligation: "must" oder "should".
- category: "information", "process" oder "technical".
- Uebernimm die vorgegebene Zitatstelle unveraendert in "ref". Erfinde niemals eine.

Antworte NUR mit einem JSON-Array. Kein Markdown.
Element: {"ref": "<vorgegeben>", "text": "...", "obligation": "must",
"category": "information"}
"""


def build_prompt(unit: dict) -> str:
    lead = f"Einleitender Satz:\n{unit['lead']}\n\n" if unit.get("lead") else ""
    return f"Zitatstelle: {unit['ref']}\n\n{lead}Normtext:\n{unit['text']}"


def parse_response(raw: str) -> list[dict]:
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    return json.loads(cleaned.strip())


def get_completed_refs(output_path: Path) -> set[str]:
    """Read already processed refs from the existing output file."""
    completed = set()

    if not output_path.exists():
        return completed

    with output_path.open("r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if not line:
                continue

            try:
                requirement = json.loads(line)
                if "ref" in requirement:
                    completed.add(requirement["ref"])
            except json.JSONDecodeError:
                print("Warning: Could not parse an existing output line.")

    return completed


def main():
    input_path = Path("requirements/_units.jsonl")
    output_path = Path("requirements/_raw_extracted.jsonl")

    # IMPORTANT: read existing results instead of deleting/overwriting them
    completed_refs = get_completed_refs(output_path)

    print(f"Already completed: {len(completed_refs)} refs")

    with (
        input_path.open("r", encoding="utf-8") as infile,
        output_path.open("a", encoding="utf-8") as outfile,
    ):
        for line_number, line in enumerate(infile, start=1):
            unit = json.loads(line)
            ref = unit["ref"]

            # Skip units that are already in the output file
            if ref in completed_refs:
                print(f"Skipping {ref} (already completed)")
                continue

            print(f"Processing unit {line_number}: {ref}")

            prompt = build_prompt(unit)

            try:
                raw = complete(prompt, system=SYSTEM)
            except AllProvidersExhausted as e:
                print(f"All providers exhausted: {e}")
                print("Stopping. Run the script again once a provider is available.")
                break

            extracted = parse_response(raw)

            for requirement in extracted:
                outfile.write(json.dumps(requirement, ensure_ascii=False) + "\n")

            # Make sure results are physically written immediately
            outfile.flush()

            completed_refs.add(ref)

            print(f"Completed {ref}")


if __name__ == "__main__":
    main()
