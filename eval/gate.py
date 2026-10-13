"""
The gate between the two stages (session 8c, step 3; rule in eval/gate.md). No Snowflake call: it reads the grades of
stage 1 (eval/campaign.py grade --stage 1) and writes eval/stage2.yaml.

    python eval/gate.py <grades_campaign-s1.json> [--out eval/stage2.yaml] [--force QID ... --forced-by "<who, date>"]

A question discriminates if at least one configuration fails it, or if the answers differ across configurations:
- in value, beyond rounding to 0.05: the answer's figure (the candidate nearest to the expected value), per member;
- in the set of products a list answer gives;
- in parameters: the analysis month named, the basis named, the default scope stated;
- in the warnings relayed (yes, partial, no);
- in refusal (one refuses or asks, another gives a figure).
The governance measures (ROWS_COMMENTED, FRESHNESS_STATED) never count. A manual verdict must be decided by the owner
(eval/manual_decisions.yaml) before the gate runs. Held-out questions were not asked in stage 1 and are not selected
here: eval/campaign.py adds them to stage 2. The owner can force a stage 1 question into stage 2 (--force, with
--forced-by): it is selected with the reason "forced", beside any reason of its own, and never enters drop_order.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("grade", ROOT / "eval" / "grade.py")
grade = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("grade", grade)
_spec.loader.exec_module(grade)

TOL = 0.05
EUR_REL_TOL = 0.005    # owner, 2026-10-07: amounts of an EUR expected value are the same within 0.5 percent
MONTH_NAMED = re.compile(r"\b(january|february|march|april|may|june|july|august|september|october|november|december)"
                         r"\s+20\d\d\b|\b20\d\d-\d\d(?:-01)?\b", re.I)
BULK_STATED = re.compile(r"\bbulk\b", re.I)


def answer_text(t: dict) -> str:
    text = t.get("answer") or ""
    if t.get("tables"):
        text = text.rstrip() + "\n\n" + grade.table_text(t["tables"])
    return text


def figure(q: dict, text: str) -> dict[str, float] | None:
    """The answer's figure, per member: the candidate number nearest to the expected value among those the grader
    counts as candidates (months for coverage, every number on the member's line for rows). None for a list or a
    refusal question, where the products and the refusal are compared instead."""
    e = q["expected"]
    def near(cands, want):
        c = [float(n.value) for n in cands]
        return min(c, key=lambda x: abs(x - want)) if c and want is not None else None
    if "value" in e and "items" not in e and "summary" not in e:
        cands = grade.month_numbers(text) if q["metric"] == "stock_coverage" else grade.numbers(text)
        return {"": near(cands, e["value"])}
    if "rows" in e and e["rows"] and "country_code" in e["rows"][0] and "sku_code" not in e["rows"][0]:
        key = "value" if "value" in e["rows"][0] else "coverage_months"
        out = {}
        for r in e["rows"]:
            line = grade.line_numbers(text, r["country_code"])
            if q["metric"] == "stock_coverage":
                line = [n for n in line if n in grade.month_numbers(text)] or line
            out[r["country_code"]] = near(line, r[key])
        return out
    return None


def features(t: dict) -> dict:
    """What the gate compares for one graded turn (a grade of eval/grade.py with its answer and tables). Parameters are
    read from what the answer says it used (month, basis, default scope), the only surface common to every
    configuration; they are compared among the answers that give a figure."""
    q = grade.QUESTIONS[t["question_id"]]
    e = q["expected"]
    text = answer_text(t)
    fig = figure(q, text)
    gives = bool(grade.month_numbers(text) if q["metric"] == "stock_coverage" else grade.numbers(text)) or \
        bool(grade.SKU.findall(text) and ("summary" in e or "items" in e or "rows" in e))
    listing = ("rows" in e and e["rows"] and "sku_code" in e["rows"][0]) or "summary" in e or "items" in e
    refused = not gives and bool(grade.REFUSAL_WORDS.search(text) or grade.CLARIFY_WORDS.search(text))
    coverage = q["metric"] == "stock_coverage" and gives
    scoped = "DEFAULT_SCOPE_EXCLUDED" in (e.get("warnings") or {}) or "DEFAULT_SCOPE_EXCLUDED" in e.get("warnings_codes", [])
    return {
        "verdict": t["verdict"],
        "figure": fig,
        "products": sorted(set(grade.SKU.findall(text))) if listing else None,
        "month": bool(grade.AS_OF_WORDS.search(text)) if gives else None,
        "basis": sorted(b for b, rx in grade.BASIS_WORDS.items() if rx.search(text)) if coverage else None,
        "scope": bool(BULK_STATED.search(text)) if coverage and scoped else None,
        "warnings": t.get("warnings_relayed", "n/a"),
        "refused": refused,
    }


def same_figure(a: float, b: float, eur: bool = False) -> bool:
    """Months (and every non-EUR figure): 0.05 apart at most. EUR amounts: 0.5 percent of the larger, or 0.05."""
    tol = max(TOL, EUR_REL_TOL * max(abs(a), abs(b))) if eur else TOL
    return abs(a - b) <= tol + 1e-9


def differences(by_config: dict[str, dict], eur: bool = False) -> dict[str, list[str]]:
    """For each compared dimension, the configurations whose answer differs from the majority (or from the others).
    eur: the question's expected value is in EUR (relative tolerance). The basis named is not a difference when every
    configuration is correct (owner, 2026-10-07)."""
    out: dict[str, list[str]] = {}
    cfgs = sorted(by_config)
    all_correct = all(f["verdict"] == "correct" for f in by_config.values())
    for dim in ("products", "month", "basis", "scope", "warnings", "refused"):     # never a governance measure
        if dim == "basis" and all_correct:
            continue
        vals = {c: json.dumps(by_config[c][dim]) for c in cfgs if by_config[c][dim] is not None}
        if len(set(vals.values())) > 1:
            counts = {v: sum(1 for x in vals.values() if x == v) for v in set(vals.values())}
            top = max(counts.values())
            major = {v for v, n in counts.items() if n == top}
            out[dim] = sorted(c for c, v in vals.items() if v not in major) or sorted(vals)
    figs = {c: f["figure"] for c, f in by_config.items() if f["figure"] is not None}
    keys = {k for f in figs.values() for k in f}
    far = set()
    for k in keys:
        vals = {c: f.get(k) for c, f in figs.items()}
        for a in vals:
            for b in vals:
                if a < b and (vals[a] is None) != (vals[b] is None) or (
                        vals[a] is not None and vals[b] is not None and not same_figure(vals[a], vals[b], eur)):
                    far |= {a, b}
    if far:
        out["value"] = sorted(far)
    return out


def gate(grades: list[dict], forced: list[str] | None = None, forced_by: str | None = None) -> dict:
    manual = [f"{g['config']} {g['question_id']}" for g in grades if g["verdict"] == "manual"]
    if manual:
        raise SystemExit(f"manual verdicts to decide first (eval/manual_decisions.yaml): {manual}")
    forced = list(dict.fromkeys(forced or []))
    if forced and not forced_by:
        raise SystemExit("a forced question needs --forced-by (who decided it, and when)")
    bad = [q for q in forced if q not in grade.QUESTIONS or grade.QUESTIONS[q].get("held_out")
           or grade.QUESTIONS[q].get("added_in_stage")]          # session 9b: N1 to N3 were never asked in stage 1
    if bad:
        raise SystemExit(f"only stage 1 questions can be forced (held-out questions are always in stage 2): {bad}")
    by_q: dict[str, dict[str, dict]] = {}
    for g in grades:
        if grade.QUESTIONS[g["question_id"]].get("held_out"):
            continue
        by_q.setdefault(g["question_id"], {})[g["config"]] = features(g)
    selected, reasons, strength = [], {}, {}
    for qid, by_config in by_q.items():
        failed = sorted(c for c, f in by_config.items() if f["verdict"] == "wrong")
        diff = differences(by_config, eur=grade.QUESTIONS[qid]["expected"].get("unit") == "EUR")
        why = ({"failed": failed} if failed else {}) | diff
        if why:
            selected.append(qid)
            reasons[qid] = why
            touched = set(failed) | {c for v in diff.values() for c in v}
            only_warnings = not failed and set(diff) == {"warnings"}
            strength[qid] = (not only_warnings, len(touched), len(failed))
    for qid in forced:                                   # the owner's choice, beside any reason of the question's own
        if qid not in selected:
            selected.append(qid)
        reasons[qid] = reasons.get(qid, {}) | {"forced": forced_by}
    selected.sort(key=lambda q: [x["id"] for x in grade.QUESTIONS.values()].index(q))
    a_passed = [q for q in selected if by_q.get(q, {}).get("A", {}).get("verdict") == "correct"]
    drop_order = sorted((q for q in selected if q in strength and strength[q][1] == 1 and q not in forced),
                        key=lambda q: (strength[q], q))
    out = {"discriminating": selected, "a_passed": a_passed, "drop_order": drop_order, "reasons": reasons,
           "not_selected": sorted(set(by_q) - set(selected))}
    if forced:
        out |= {"forced": forced, "forced_by": forced_by}
    return out


def write(res: dict, out: Path) -> None:
    out.write_text("# Written by eval/gate.py from the stage 1 grades; the rule is eval/gate.md.\n"
                   + yaml.safe_dump(res, sort_keys=False, width=118))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("grades", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "eval" / "stage2.yaml")
    ap.add_argument("--force", action="append", default=[], metavar="QID", help="a stage 1 question the owner forces in")
    ap.add_argument("--forced-by", help='who forced the questions, and when ("owner, 2026-10-07")')
    a = ap.parse_args()
    res = gate(json.loads(a.grades.read_text()), a.force, a.forced_by)
    write(res, a.out)
    print(json.dumps({k: v for k, v in res.items() if k != "reasons"}, indent=1))


if __name__ == "__main__":
    main()
