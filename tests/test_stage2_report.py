"""Session 9b, step 5: the tables of snowflake/phase5_campaign/stage2_results.md, from the grades and summaries. No call."""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("stage2_report", ROOT / "eval" / "stage2_report.py")
rep = importlib.util.module_from_spec(_spec)
sys.modules["stage2_report"] = rep
_spec.loader.exec_module(rep)


def g(cfg, qid, verdict, stage=2, r=2):
    return {"config": cfg, "question_id": qid, "verdict": verdict, "verdict_figure_only": verdict,
            "label": f"{cfg}_{qid}_campaign-s{stage}_r{r}"}


def test_repetition_from_the_label():
    assert rep.repetition("C_T1_campaign-s2_r2") == 2 and rep.repetition("B2_N1_campaign-s2-a2_r1") == 1


def test_table_by_route_group_and_repetition():
    t = rep.by_route([g("C", "T1", "correct"), g("C", "N1", "wrong", r=1), g("C", "N1", "correct"),
                      g("C", "CS_FAMILY", "manual"), g("C", "T6", "correct"), g("B2", "N1", "correct", r=1)])
    assert t["C"]["procedure"][2] == {"correct": 1, "wrong": 0, "manual": 0}
    assert t["C"]["both"][1] == {"correct": 0, "wrong": 1, "manual": 0} and t["C"]["both"][2]["correct"] == 1
    assert t["C"]["view only"][2]["manual"] == 1 and t["C"]["no tool"][2]["correct"] == 1
    assert t["B2"]["both"][1]["correct"] == 1


def test_c_over_both_stages_on_the_questions_it_played_seen_and_unseen_apart():
    s1 = [g("C", "T1", "correct", 1, 1), g("C", "T2", "correct", 1, 1), g("C", "S_OWN_UNIT", "correct", 1, 1)]
    s2 = [g("C", "T1", "correct"), g("C", "T2", "correct"), g("C", "N1", "correct", r=1), g("C", "N1", "correct"),
          g("C", "H_STOCKOUT_ES", "correct", r=1)]
    seen = rep.pooled(s1, s2, "C", unseen=False)
    assert seen["questions"] == 2 and seen["trials"] == 4 and seen["correct"] == 4       # S_OWN_UNIT not played in s2
    assert math.isclose(seen["upper_95"], 1 - 0.05 ** (1 / 4))
    unseen = rep.pooled(s1, s2, "C", unseen=True)
    assert unseen["questions"] == 2 and unseen["trials"] == 3 and unseen["correct"] == 3
    s2.append(g("C", "T2", "wrong", r=3))
    assert rep.pooled(s1, s2, "C", unseen=False)["upper_95"] is None                     # a failure: no zero bound


def test_latency_per_turn_sums_its_calls():
    summaries = {"a": {"calls": [{"seconds_total": 10.0}, {"seconds_total": 5.0}]},
                 "b": {"calls": [{"seconds_total": 20.0}]}, "c": {"calls": [{"seconds_total": 30.0}]}}
    lat = rep.latency(summaries)
    assert lat["n"] == 3 and lat["median"] == 20.0 and lat["min"] == 15.0 and lat["max"] == 30.0
