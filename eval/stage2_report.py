"""
The tables of the reduced stage 2 (session 9b, owner 2026-10-07), from the grades and run summaries. No Snowflake call.

    python eval/stage2_report.py          # JSON: verdicts by route group and repetition, C over both stages, the
                                          # never-seen questions apart, latency per turn, the harness cost estimate

Route groups: eval/grade.py route_group (the route agent C is expected to take). Unseen questions: Q1 to Q4 (held out)
and N1 to N3 (added in stage 2), never seen by a frozen agent. The bound at zero failures is the exact one-sided 95
percent upper bound of the error rate, 1 - 0.05^(1/n) (eval/cost_model.py exact_upper_at_zero).
"""

from __future__ import annotations

import importlib.util
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_g = importlib.util.spec_from_file_location("grade", ROOT / "eval" / "grade.py")
grade = sys.modules.get("grade") or importlib.util.module_from_spec(_g)
if "grade" not in sys.modules:
    sys.modules["grade"] = grade
    _g.loader.exec_module(grade)
VERDICTS = ("correct", "wrong", "manual")


def repetition(label: str) -> int:
    return int(re.search(r"_r(\d+)$", label).group(1))


def unseen(qid: str) -> bool:
    q = grade.QUESTIONS[qid]
    return bool(q.get("held_out") or q.get("added_in_stage") == 2)


def by_route(grades: list[dict], key: str = "verdict") -> dict:
    """Configuration -> route group -> repetition -> verdict counts."""
    out: dict = {}
    for x in grades:
        grp = grade.route_group(grade.QUESTIONS[x["question_id"]])
        c = out.setdefault(x["config"], {}).setdefault(grp, {}).setdefault(repetition(x["label"]),
                                                                            dict.fromkeys(VERDICTS, 0))
        c[x[key]] += 1
    return out


def pooled(s1: list[dict], s2: list[dict], cfg: str, unseen: bool, key: str = "verdict") -> dict:
    """One configuration over both stages, on the questions it played in stage 2 (seen ones, or the unseen ones
    apart): trials, verdicts, and the exact bound when no trial failed or stayed manual."""
    played = {x["question_id"] for x in s2 if x["config"] == cfg and globals()["unseen"](x["question_id"]) == unseen}
    turns = [x for x in s1 + s2 if x["config"] == cfg and x["question_id"] in played]
    n = len(turns)
    counts = {v: sum(x[key] == v for x in turns) for v in VERDICTS}
    bound = 1 - 0.05 ** (1 / n) if n and counts["correct"] == n else None
    return {"questions": len(played), "trials": n, **counts, "upper_95": bound}


def latency(summaries: dict[str, dict]) -> dict:
    """Client seconds per turn: the sum of its REST calls."""
    secs = sorted(sum(c.get("seconds_total") or 0 for c in s["calls"]) for s in summaries.values())
    if not secs:
        return {"n": 0}
    q = statistics.quantiles(secs, n=10) if len(secs) > 1 else secs
    return {"n": len(secs), "median": statistics.median(secs), "p90": q[-1], "min": secs[0], "max": secs[-1]}


def main() -> None:
    run = Path.home() / "work" / "assets" / "linkml-metrics-runs" / "campaign"
    s1 = json.loads((run / "grades_campaign-s1.json").read_text())
    s2 = json.loads((run / "grades_campaign-s2.json").read_text())
    state = json.loads((run / "state_campaign-s2.json").read_text())
    _c = importlib.util.spec_from_file_location("guards", ROOT / "eval" / "guards.py")
    guards = importlib.util.module_from_spec(_c)
    sys.modules["guards"] = guards
    _c.loader.exec_module(guards)
    guard = guards.CampaignGuard.load(state["guard"])
    out = {"by_route": by_route(s2), "by_route_figure_only": by_route(s2, "verdict_figure_only"), "pooled": {},
           "latency": {}, "manual": [{k: x[k] for k in ("config", "question_id", "label", "request_id")}
                                     for x in s2 if x["verdict"] == "manual"]}
    for cfg in sorted({x["config"] for x in s2}):
        out["pooled"][cfg] = {"seen": pooled(s1, s2, cfg, False), "unseen": pooled(s1, s2, cfg, True),
                              "seen_figure_only": pooled(s1, s2, cfg, False, "verdict_figure_only")}
        sums = {x["label"]: json.loads((run / f"summary_{x['label'].lower().replace('-', '_')}.json").read_text())
                for x in s2 if x["config"] == cfg}
        out["latency"][cfg] = latency(sums)
    out["cost"] = {"ai_credits": round(guard.spent_credits, 4), "ai_usd": round(guard.spent_credits * 2.0, 2),
                   "warehouse_hours": round(guard.warehouse_hours(), 3), "estimate_usd": round(guard.spent_usd(), 2),
                   "ceiling_usd": guard.ceiling_usd, "paused": guard.paused, "segments": guard.segments}
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
