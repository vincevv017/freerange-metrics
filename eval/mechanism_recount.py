"""
The recorded campaign grades recounted by mechanism class (session 13, step 1c). No Snowflake call, no regrade.

    python eval/mechanism_recount.py                 # the grade files of record in linkml-metrics-runs/campaign/
    python eval/mechanism_recount.py --run-dir <dir> # elsewhere (the files keep their names)

Classes: eval/mechanism_classes.yaml (the rule is in its header). Per configuration and stage: correct / wrong /
manual per class under rubric 3.2 (the score of record, grades_campaign-s<n>.json), under 3.3
(grades_campaign-s<n>.rubric-3.3.json) and the figure-only verdict of each, then a check that the classes sum to the
published totals (PUBLISHED). For C: the tools of each turn, read from the turn's run summary (tool_uses of its REST
calls), the coverage turns with no procedure call, and the closing-stock and general turns that used the view.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLASSES_PATH = ROOT / "eval" / "mechanism_classes.yaml"
RUN = Path.home() / "work" / "assets" / "linkml-metrics-runs" / "campaign"
CLASSES = ("COVERAGE", "CLOSING_STOCK", "GENERAL", "REFUSAL")
VERDICTS = ("correct", "wrong", "manual")
# Published correct / wrong, no manual verdict: stage 1 from snowflake/phase5_campaign/stage1_results.md section 12
# (3.2 as in section 9), stage 2 from snowflake/phase5_campaign/stage2_results.md section 8. Figure only is the same
# under 3.2 and 3.3 there.
PUBLISHED = {
    1: {"3.2": {"A": (16, 8), "B1": (13, 11), "B2": (15, 9), "C": (24, 0), "D": (17, 7), "DP": (15, 9)},
        "3.3": {"A": (18, 6), "B1": (16, 8), "B2": (18, 6), "C": (24, 0), "D": (18, 6), "DP": (18, 6)},
        "figure_only": {"A": (19, 5), "B1": (19, 5), "B2": (19, 5), "C": (24, 0), "D": (20, 4), "DP": (19, 5)}},
    2: {"3.2": {"C": (27, 3), "B2": (20, 10)},
        "3.3": {"C": (28, 2), "B2": (22, 8)},
        "figure_only": {"C": (29, 1), "B2": (25, 5)}},
}


def load_classes(path: Path = CLASSES_PATH) -> dict[str, dict]:
    return yaml.safe_load(path.read_text())["questions"]


def counts(grades: list[dict], classes: dict[str, dict], key: str = "verdict") -> dict:
    """Configuration -> class (and TOTAL) -> verdict counts."""
    out: dict = {}
    for g in grades:
        cfg = out.setdefault(g["config"], {c: dict.fromkeys(VERDICTS, 0) for c in CLASSES + ("TOTAL",)})
        cfg[classes[g["question_id"]]["class"]][g[key]] += 1
        cfg["TOTAL"][g[key]] += 1
    return out


def sums_match(table: dict) -> bool:
    """The classes of each configuration sum to its total."""
    return all(sum(t[c][v] for c in CLASSES) == t["TOTAL"][v] for t in table.values() for v in VERDICTS)


def tool_family(use: dict) -> str | None:
    t, n = (use.get("type") or "").lower(), use.get("name") or ""
    if n == "stock_coverage":
        return "procedure"
    if "cortex_analyst" in t or "system_execute_sql" in t or "semantic" in t or n.endswith("semantic_view"):
        return "view"
    return None if "chart" in t or "chart" in n else f"other:{t or n}"


def tools_of(run: Path, label: str) -> list[str] | None:
    p = run / f"summary_{label.lower().replace('-', '_')}.json"
    if not p.exists():
        return None
    s = json.loads(p.read_text())
    return [f for c in s["calls"] for u in c.get("tool_uses") or [] if (f := tool_family(u))]


def also(grades: list[dict], classes: dict[str, dict], key: str = "verdict") -> dict:
    """The questions counted under one class whose graded answer also carries another (N1, N2: closing stock and
    coverage): class -> configuration -> verdict counts, shown on a line of their own, never added to the classes."""
    out: dict = {}
    for g in grades:
        other = classes[g["question_id"]].get("also")
        if other:
            c = out.setdefault(other, {}).setdefault(g["config"], dict.fromkeys(VERDICTS, 0))
            c[g[key]] += 1
    return out


def fmt(t: dict) -> str:
    return " | ".join(f"{c} {t[c]['correct']}/{t[c]['wrong']}/{t[c]['manual']}" for c in CLASSES + ("TOTAL",))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--run-dir", type=Path, default=RUN)
    a = p.parse_args()
    classes = load_classes()
    ok = True
    for stage in (1, 2):
        g32 = json.loads((a.run_dir / f"grades_campaign-s{stage}.json").read_text())
        g33 = json.loads((a.run_dir / f"grades_campaign-s{stage}.rubric-3.3.json").read_text())
        tables = {"3.2": counts(g32, classes), "3.3": counts(g33, classes),
                  "figure_only_3.2": counts(g32, classes, "verdict_figure_only"),
                  "figure_only_3.3": counts(g33, classes, "verdict_figure_only")}
        extra = {"3.2": also(g32, classes), "3.3": also(g33, classes),
                 "figure_only_3.2": also(g32, classes, "verdict_figure_only"),
                 "figure_only_3.3": also(g33, classes, "verdict_figure_only")}
        print(f"\n## Stage {stage} (correct/wrong/manual per class)")
        for name, table in tables.items():
            print(f"\n{name}")
            for cfg in sorted(table):
                print(f"  {cfg:3} {fmt(table[cfg])}")
            for other, by_cfg in extra[name].items():
                qs = ", ".join(sorted(q for q, v in classes.items() if v.get("also") == other))
                print(f"  also {other} ({qs}, counted above under their own class): " + "; ".join(
                    f"{cfg} {c['correct']}/{c['wrong']}/{c['manual']}" for cfg, c in sorted(by_cfg.items())))
            pub = PUBLISHED[stage]["figure_only" if name.startswith("figure_only") else name]
            got = {cfg: (t["TOTAL"]["correct"], t["TOTAL"]["wrong"]) for cfg, t in table.items()
                   if t["TOTAL"]["manual"] == 0}
            good = sums_match(table) and got == pub
            ok &= good
            print(f"  check: classes sum to totals {sums_match(table)}; totals equal published {got == pub}")
        print(f"\nC, stage {stage}: tools per turn (run summaries)")
        for g in sorted((x for x in g32 if x["config"] == "C"), key=lambda x: x["label"]):
            tools = tools_of(a.run_dir, g["label"])
            cls = classes[g["question_id"]]["class"]
            flag = ""
            if tools is None:
                flag = "  NO SUMMARY"
            elif cls == "COVERAGE" and "procedure" not in tools:
                flag = "  COVERAGE WITHOUT PROCEDURE"
            print(f"  {g['question_id']:20} {cls:13} {dict(Counter(tools or []))}{flag}")
    print("\nall checks:", "pass" if ok else "FAIL")


if __name__ == "__main__":
    main()
