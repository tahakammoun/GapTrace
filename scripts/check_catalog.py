import json
from collections import Counter
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "requirements" / "dsgvo_art12_14.jsonl"
REQUIRED = {"key", "ref", "legal_text", "text", "obligation", "category", "condition"}


def main():
    rows = []
    for n, line in enumerate(PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"line {n}: bad JSON: {e}")
            return

    keys = Counter(r.get("key") for r in rows)
    for k, c in keys.items():
        if c > 1:
            print(f"duplicate key: {k} ({c}x)")
    for r in rows:
        missing = REQUIRED - r.keys()
        if missing:
            print(f"{r.get('key')}: missing {missing}")
        if r.get("obligation") not in ("must", "should"):
            print(f"{r.get('key')}: bad obligation {r.get('obligation')!r}")
        if len(r.get("text", "")) < 20:
            print(f"{r.get('key')}: text suspiciously short")
        if len(r.get("legal_text", "")) < 20:
            print(f"{r.get('key')}: legal_text suspiciously short")

    conditional = [r for r in rows if r.get("condition")]
    print(f"\n{len(rows)} rows, {len(conditional)} conditional")
    for r in conditional:
        print(f"  {r['key']}: {r['condition']}")
    print("\nby article:", Counter(r["ref"].split("(")[0].strip() for r in rows))
    print("by category:", Counter(r.get("category") for r in rows))


if __name__ == "__main__":
    main()
