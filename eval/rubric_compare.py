"""
The regrade of a stage under two rubrics, turn by turn (session 9c, owner 2026-10-07). No Snowflake call.

    python eval/rubric_compare.py <grades under 3.2> <grades under 3.3>   # JSON: counts per configuration, changed turns

Both files come from eval/campaign.py grade on the same completed turns (the file of record is rubric 3.2,
eval/campaign.py grades_file). Per configuration: the primary verdict and the figure-only score under each rubric.
Every turn whose primary or figure-only verdict differs is listed with the criteria that differ, each with its result
and its reason under both rubrics (the reason quotes the sentence a wording criterion read).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

VERDICTS = ("correct", "wrong", "manual")


def _counts(grades: list[dict], key: str) -> dict:
    return {v: sum(x[key] == v for x in grades) for v in VERDICTS}


def compare(old: list[dict], new: list[dict], a: str = "3.2", b: str = "3.3") -> dict:
    by_old, by_new = {x["label"]: x for x in old}, {x["label"]: x for x in new}
    if set(by_old) != set(by_new) or len(by_old) != len(old) or len(by_new) != len(new):
        raise SystemExit("the two files do not grade the same turns")
    out: dict = {"by_config": {}, "changed": []}
    for cfg in sorted({x["config"] for x in old}):
        o = [x for x in old if x["config"] == cfg]
        n = [by_new[x["label"]] for x in o]
        out["by_config"][cfg] = {"turns": len(o), f"primary_{a}": _counts(o, "verdict"), f"primary_{b}": _counts(n, "verdict"),
                                 f"figure_only_{a}": _counts(o, "verdict_figure_only"),
                                 f"figure_only_{b}": _counts(n, "verdict_figure_only")}
    for label in sorted(by_old, key=lambda k: (by_old[k]["config"], k)):
        x, y = by_old[label], by_new[label]
        if (x["verdict"], x["verdict_figure_only"]) == (y["verdict"], y["verdict_figure_only"]):
            continue
        crit = {}
        for k in sorted(set(x["criteria"]) | set(y["criteria"])):
            cx, cy = x["criteria"].get(k), y["criteria"].get(k)
            if cx != cy:
                crit[k] = {r: (f"{c['result']}: {c['why']}" if c else "not applied") for r, c in ((a, cx), (b, cy))}
        out["changed"].append({"config": x["config"], "question_id": x["question_id"], "label": label,
                               "primary": (x["verdict"], y["verdict"]),
                               "figure_only": (x["verdict_figure_only"], y["verdict_figure_only"]), "criteria": crit})
    return out


def main() -> None:
    old, new = (json.loads(Path(f).read_text()) for f in sys.argv[1:3])
    print(json.dumps(compare(old, new), indent=1))


if __name__ == "__main__":
    main()
