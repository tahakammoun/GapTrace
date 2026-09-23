"""Score findings against a hand-labelled gold matrix.

Applicability and status are scored separately rather than folded into one
number: getting a conditional requirement's applicability wrong (e.g. saying
a third-country transfer doesn't apply when it does) is a different failure
mode from misclassifying an applicable requirement's status, and CLAUDE.md's
rule -- a false "addressed" is far worse than a false "not_found" -- only
makes sense measured on requirements that actually apply.
"""

import json
from pathlib import Path

from src.db import connect

ROOT = Path(__file__).resolve().parent.parent.parent
STATUSES = ["addressed", "partial", "not_found"]


def load_gold(name: str) -> dict[str, dict]:
    path = ROOT / "eval" / "gold" / f"{name}.jsonl"
    gold = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        gold[row["requirement_key"]] = row
    return gold


def load_findings(filename: str) -> dict[str, dict]:
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT r.key, f.status, f.applicability, f.confidence "
            "FROM findings f "
            "JOIN requirements r ON r.id = f.requirement_id "
            "JOIN targets t ON t.id = f.target_id "
            "JOIN documents d ON d.id = t.document_id "
            "WHERE d.filename = %s",
            (filename,),
        )
        return {
            key: {"status": status, "applicability": applicability, "confidence": confidence}
            for key, status, applicability, confidence in cur.fetchall()
        }


def evaluate(gold_name: str, target_filename: str) -> dict:
    gold = load_gold(gold_name)
    found = load_findings(target_filename)

    checked = {k: v for k, v in gold.items() if k in found}
    unchecked = sorted(k for k in gold if k not in found)

    appl_total = 0
    appl_correct = 0
    appl_errors = []
    status_rows = []  # (key, gold_status, pred_status), only where gold says applicable

    for key, g in checked.items():
        f = found[key]
        appl_total += 1
        if f["applicability"] == g["gold_applicability"]:
            appl_correct += 1
        else:
            appl_errors.append((key, g["gold_applicability"], f["applicability"]))

        if g["gold_applicability"] == "applicable":
            status_rows.append((key, g["gold_status"], f["status"]))

    confusion = {g: {p: 0 for p in STATUSES} for g in STATUSES}
    for _, g_status, p_status in status_rows:
        confusion[g_status][p_status] += 1

    per_class = {}
    for cls in STATUSES:
        tp = confusion[cls][cls]
        fp = sum(confusion[g][cls] for g in STATUSES if g != cls)
        fn = sum(confusion[cls][p] for p in STATUSES if p != cls)
        per_class[cls] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": tp / (tp + fp) if (tp + fp) else None,
            "recall": tp / (tp + fn) if (tp + fn) else None,
        }

    non_addressed_gold = [r for r in status_rows if r[1] != "addressed"]
    false_addressed = [r for r in non_addressed_gold if r[2] == "addressed"]

    n_status = len(status_rows)
    return {
        "gold_total": len(gold),
        "checked": len(checked),
        "unchecked": unchecked,
        "applicability_total": appl_total,
        "applicability_correct": appl_correct,
        "applicability_accuracy": appl_correct / appl_total if appl_total else None,
        "applicability_errors": appl_errors,
        "status_n": n_status,
        "status_accuracy": (
            sum(1 for _, g, p in status_rows if g == p) / n_status if n_status else None
        ),
        "confusion": confusion,
        "per_class": per_class,
        "false_addressed_rate": (
            len(false_addressed) / len(non_addressed_gold) if non_addressed_gold else None
        ),
        "false_addressed_cases": [k for k, _, _ in false_addressed],
    }


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.0f}%"


def print_report(result: dict) -> None:
    print(f"gold requirements: {result['gold_total']}")
    print(f"checked by pipeline: {result['checked']} ({len(result['unchecked'])} not yet run)")
    print()
    print(f"applicability accuracy: {result['applicability_correct']}/"
          f"{result['applicability_total']} ({_pct(result['applicability_accuracy'])})")
    for key, gold_appl, pred_appl in result["applicability_errors"]:
        print(f"  MISS  {key:38s} gold={gold_appl:15s} pipeline={pred_appl}")
    print()
    print(f"status accuracy (on {result['status_n']} applicable requirements): "
          f"{_pct(result['status_accuracy'])}")
    print(f"false-addressed rate (the one CLAUDE.md says matters most): "
          f"{_pct(result['false_addressed_rate'])}")
    if result["false_addressed_cases"]:
        print(f"  cases: {', '.join(result['false_addressed_cases'])}")
    print()
    print(f"{'gold \\ pipeline':20s}" + "".join(f"{s:>12s}" for s in STATUSES))
    for g in STATUSES:
        print(f"{g:20s}" + "".join(f"{result['confusion'][g][p]:>12d}" for p in STATUSES))
    print()
    for cls in STATUSES:
        pc = result["per_class"][cls]
        print(f"{cls:12s} precision={_pct(pc['precision']):>5s}  recall={_pct(pc['recall']):>5s}"
              f"  (tp={pc['tp']} fp={pc['fp']} fn={pc['fn']})")


if __name__ == "__main__":
    result = evaluate("target1_bahn", "target1_bahn.html")
    print_report(result)
