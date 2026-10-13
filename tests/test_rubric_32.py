"""Rubric 3.2 (session 8c, owner's decisions 3 and 5), written before any graded turn of the campaign.

1. The change to decide() (a value also written at a precision that tells it from every wrong value decides on the
   number) and the tables graded with the text move no recorded verdict of sessions 7, 8, 8b and 8c-0, except G2 of 8b,
   manual to correct. eval/fixtures/recorded_turns.jsonl: every graded turn of those sessions (run folders' summaries
   and traces, the session 7 fixture, the step 6 DIM_MIX answer whose log was overwritten); recorded_verdicts.json:
   the verdict of the grader at 655888d (rubric 3.1, text only) and of this one.
2. The held-out questions: Q1 and Q3 and Q4 on the exact set of products, Q2 on PL and 2.16 months; the wording rule of
   rubric 3.1 applies to all.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("grade", ROOT / "eval" / "grade.py")
grade = importlib.util.module_from_spec(_spec)
sys.modules["grade"] = grade
_spec.loader.exec_module(grade)

TURNS = [json.loads(x) for x in (ROOT / "eval" / "fixtures" / "recorded_turns.jsonl").read_text().splitlines()]
VERDICTS = json.loads((ROOT / "eval" / "fixtures" / "recorded_verdicts.json").read_text())
SV = {"b2_semantic_view", "b1_semantic_view", "a_semantic_view"}
IO = ("DIM_ITEM", "B2_ITEM")
Q = grade.QUESTIONS


def test_rubric_version():
    assert "3.2" in grade.RUBRICS          # rubric 3.3 (session 9c) is current; 3.2 stays selectable


@pytest.mark.parametrize("t", TURNS, ids=lambda t: f"{t['run']}|{t['label']}")
def test_recorded_verdicts_do_not_move_except_g2_of_8b(t):
    v = VERDICTS[f"{t['run']}|{t['label']}"]
    now = grade.grade_turn(t, SV, IO, rubric="3.2")["verdict"]
    assert now == v["rubric_3_2"]
    if (t["run"], t["label"]) == ("s8b", "c_g2"):
        assert (v["rubric_3_1"], now) == ("manual", "correct")
    else:
        assert v["rubric_3_1"] == now


def test_every_recorded_session_is_covered():
    assert {t["run"] for t in TURNS} == {"s7", "s8", "s8b", "s8c0", "s8c0-step6"} and len(TURNS) == 59


def turn(qid, answer, tables=None):
    return {"config": "C", "question_id": qid, "answer": answer, "tables": tables or [],
            "tool_uses": [{"type": "generic", "name": "stock_coverage", "input": {}}], "tool_results": [], "sql": []}


BASIS = " Stock and forecast are measured in kg or L equivalent, as of June 2026, standard items only."
Q1 = Q["H_LOCAL_STOCKOUT"]["expected"]["items"]
Q3 = Q["H_STOCKOUT_2027"]["expected"]["items"]


def listing(codes):
    return "\n".join(f"- {c}" for c in codes)


def test_q1_exact_set_is_correct_and_an_intersection_is_allowed():
    a = ("These 14 items stock out within 3 months in at least one country while covering more than 6 months across "
         "all countries." + BASIS + "\n" + listing(Q1))
    g = grade.grade_turn(turn("H_LOCAL_STOCKOUT", a))
    assert g["verdict"] == "correct", g
    apart = a + "\nSKU-H08 in the Netherlands and SKU-H11 in Switzerland have no stock; SKU-H09 has no demand."
    assert grade.grade_turn(turn("H_LOCAL_STOCKOUT", apart))["verdict"] == "correct"


def test_q1_two_lists_without_intersection_are_wrong():
    p = Q["H_LOCAL_STOCKOUT"]
    local = Q1 + ["SKU-0009", "SKU-0017", "SKU-H02", "SKU-0039"]
    a = "Items at risk within 3 months:" + BASIS + "\n" + listing(local) + "\nItems with more than 6 months:\n" + listing(Q1 + ["SKU-0032"])
    g = grade.grade_turn(turn("H_LOCAL_STOCKOUT", a))
    assert g["verdict"] == "wrong" and "extra" in g["criteria"]["item_set"]["why"], g
    assert p["tool_parameters"]["combine"].startswith("intersection")


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_q1_set_must_be_exact(change):
    codes = Q1[1:] if change == "missing" else Q1 + ["SKU-0039"]
    assert grade.grade_turn(turn("H_LOCAL_STOCKOUT", "Items:" + BASIS + "\n" + listing(codes)))["verdict"] == "wrong"


def test_q1_codes_in_a_table_count():
    t = [{"title": "Items", "columns": ["SKU_CODE"], "rows": [[c] for c in Q1]}]
    assert grade.grade_turn(turn("H_LOCAL_STOCKOUT", "14 items." + BASIS, t))["verdict"] == "correct"


def test_q1_wording_rule_of_31_applies():
    a = "14 items, each with a coverage of 2.5 kg in one country." + BASIS + "\n" + listing(Q1)
    g = grade.grade_turn(turn("H_LOCAL_STOCKOUT", a))
    assert g["criteria"]["basis_wording"]["result"] == "fail"
    assert grade.grade_turn(turn("H_LOCAL_STOCKOUT", "14 items, June 2026.\n" + listing(Q1)))["verdict"] == "wrong"


def test_q2_poland_at_216_months_is_correct():
    a = ("Poland (PL) has the lowest stock coverage of breakfast cereals as of June 2026: 2.16 months, with stock and "
         "forecast measured in kg equivalent. It stocks out in September 2026.")
    assert grade.grade_turn(turn("H_LOWEST_COUNTRY", a))["verdict"] == "correct"
    second = a + " Switzerland (CH) is second at 2.82 months."
    assert grade.grade_turn(turn("H_LOWEST_COUNTRY", second))["verdict"] == "correct"


def test_q2_switzerland_as_lowest_is_wrong():
    a = ("Switzerland has the lowest stock coverage of breakfast cereals as of June 2026, about 1.8 months, with stock "
         "and forecast in kg equivalent.")
    assert grade.grade_turn(turn("H_LOWEST_COUNTRY", a))["verdict"] == "wrong"


def test_q2_poland_with_a_wrong_figure_is_wrong():
    a = "Poland (PL) has the lowest coverage of breakfast cereals as of June 2026, 2.8 months, measured in kg equivalent."
    assert grade.grade_turn(turn("H_LOWEST_COUNTRY", a))["verdict"] == "wrong"


def test_q3_exact_set_h06_out_h03_in():
    ok = "These items stock out during 2027." + BASIS + "\n" + listing(Q3)
    assert grade.grade_turn(turn("H_STOCKOUT_2027", ok))["verdict"] == "correct"
    assert "SKU-H06" not in Q3 and "SKU-H03" in Q3 and len(Q3) == 35
    with_h06 = ok + "\n- SKU-H06"
    assert grade.grade_turn(turn("H_STOCKOUT_2027", with_h06))["verdict"] == "wrong"
    without_h03 = "These items stock out during 2027." + BASIS + "\n" + listing([c for c in Q3 if c != "SKU-H03"])
    assert grade.grade_turn(turn("H_STOCKOUT_2027", without_h03))["verdict"] == "wrong"


def test_q4_exact_set_of_three():
    a = ("Three products stock out within 3 months in Spain from June 2026, stock and forecast in kg or L equivalent:\n"
         "- SKU-0001: 1.93 months (August 2026)\n- SKU-0028: 2.73 months (September 2026)\n"
         "- SKU-0024: 2.92 months (September 2026)")
    assert grade.grade_turn(turn("H_STOCKOUT_ES", a))["verdict"] == "correct"
    naive = a.replace("SKU-0028: 2.73 months (September 2026)\n- SKU-0024", "SKU-0025")
    assert grade.grade_turn(turn("H_STOCKOUT_ES", naive))["verdict"] == "wrong"
