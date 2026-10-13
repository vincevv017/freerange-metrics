"""Rubric 3.3 (owner, 2026-10-07, session 9c), after the campaign. No call.

a. The unit half of basis_wording does not fire on a pack size that belongs to a product name of DIM_ITEM ("iced tea
   summer edition 1 L", "Oat cereal bar 1 kg", "Arabica beans 1 kg") next to the word coverage. The names are those of
   the dataset (data/traps.yaml hero_items, the DIM_ITEM.sku_name values of the dataset), never guessed. The rule
   still fires when the coverage itself is given in kg or L: every failing example of rubrics 3.1 and 3.2 stays failing.
b. Finding 100: a count of elapsed forecast months ("after n months", "in month n") is never a coverage candidate; on
   the recorded B1 T4 answer of stage 1.
c. Nothing else changes: a sentence that gives the unit of the stock or of the stock value beside the coverage still
   fails as in 3.2.
d. Rubric 3.2 stays selectable (grade_turn(..., rubric="3.2")), so both scores can be reported; the owner's manual
   decisions apply unchanged.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("grade", ROOT / "eval" / "grade.py")
grade = importlib.util.module_from_spec(_spec)
sys.modules["grade"] = grade
_spec.loader.exec_module(grade)

SV = {"b2_semantic_view", "b1_semantic_view", "a_semantic_view"}
IO = ("DIM_ITEM", "B2_ITEM")
Q = grade.QUESTIONS
TURNS = [json.loads(x) for x in (ROOT / "eval" / "fixtures" / "recorded_turns.jsonl").read_text().splitlines()]
STAGE1 = json.loads((ROOT / "eval" / "fixtures" / "grades_campaign-s1.json").read_text())   # rubric 3.2 record
STAGE2 = json.loads((ROOT / "eval" / "fixtures" / "grades_campaign-s2.json").read_text())   # rubric 3.2 record
SESSION7 = [json.loads(x) for x in (ROOT / "eval" / "fixtures" / "session7_agent_c.jsonl").read_text().splitlines()]
SESSION8B = [json.loads(x) for x in (ROOT / "eval" / "fixtures" / "session8b_agent_c.jsonl").read_text().splitlines()]


def recorded(stage: list[dict], cfg: str, qid: str, rep: str = "") -> dict:
    return next(x for x in stage if x["config"] == cfg and x["question_id"] == qid and x["label"].endswith(rep))


def full_text(g: dict) -> str:
    return (g["answer"] or "").rstrip() + ("\n\n" + grade.table_text(g["tables"]) if g.get("tables") else "")


def wording(qid: str, text: str, rubric: str) -> tuple[str, str]:
    grade.set_rubric(rubric)
    try:
        return grade.basis_wording(Q[qid], text)
    finally:
        grade.set_rubric(grade.RUBRIC["version"])


def c_turn(qid, answer, request_id=None):
    return {"config": "C", "question_id": qid, "answer": answer, "tables": [], "request_id": request_id,
            "tool_uses": [{"type": "generic", "name": "stock_coverage", "input": {}}], "tool_results": [], "sql": []}


# ------------------------------------------------------------------------------------------------ the rubric file

def test_rubric_is_33_with_a_changelog_line_and_32_stays_selectable():
    assert grade.RUBRIC["version"] == "3.3"
    assert [c for c in grade.RUBRIC["changes"] if str(c["version"]) == "3.3"]
    assert set(grade.RUBRICS) == {"3.2", "3.3"}
    with pytest.raises(SystemExit):
        grade.set_rubric("3.1")


def test_a_grade_records_its_rubric():
    t = c_turn("T4", "SKU-H05 in Spain covers 8.5 months as of June 2026, stock and forecast in kg.")
    assert grade.grade_turn(t, SV, IO)["rubric"] == "3.3"
    assert grade.grade_turn(t, SV, IO, rubric="3.2")["rubric"] == "3.2"
    assert grade.grade_turn(t, SV, IO)["rubric"] == "3.3"          # the choice does not leak to the next turn


# ------------------------------------------------------------------------------------------------ a. product names

def test_product_names_are_dims_names_that_carry_a_pack_size():
    heroes = yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())["hero_items"]
    assert set(grade.PRODUCT_NAMES) == {h["name"] for h in heroes if re.search(r"\d\s*(?:kg|L)\b", h["name"])}
    assert "Iced tea summer edition 1 L (discontinued)" in grade.PRODUCT_NAMES


def test_product_names_match_dim_item_when_the_dataset_is_built():
    f = ROOT / "data" / "output" / "DIM_ITEM.csv"
    if not f.exists():
        pytest.skip("data/output missing (the published dataset)")
    names = {r["sku_name"] for r in csv.DictReader(f.open())}
    assert {n for n in names if re.search(r"\d\s*(?:kg|L|g|ml|cl)\b", n, re.I)} == set(grade.PRODUCT_NAMES)


@pytest.mark.parametrize("cfg,qid,rep,sentence", [
    ("C", "NO_DEMAND", "r2", "Stock coverage for SKU-H09 (iced tea summer edition 1 L) in Belgium"),
    ("B2", "NO_DEMAND", "r2", "Stock coverage for iced tea summer edition 1 L (SKU-H09) in Belgium"),
    ("B2", "T9", "r2", "Stock coverage for Oat cereal bar 1 kg (SKU-H11) in Switzerland"),
    ("B2", "BEYOND_H", "r2", "The stock coverage of Arabica beans 1 kg (SKU-H10) in Poland"),
])
def test_a_pack_size_in_a_product_name_next_to_coverage_no_longer_fails(cfg, qid, rep, sentence):
    g = recorded(STAGE2, cfg, qid, rep)
    text = full_text(g)
    assert sentence in text
    assert g["criteria"]["basis_wording"]["result"] == "fail"                  # the 3.2 record
    v32, why32 = wording(qid, text, "3.2")
    v33, why33 = wording(qid, text, "3.3")
    assert v32 == "fail" and why32.startswith("coverage given in a unit") and sentence[:40] in why32
    assert not (v33 == "fail" and sentence[:40] in why33), why33
    if qid == "BEYOND_H":   # c: the answer's next sentence gives the stock's unit beside the coverage, and still fails
        assert v33 == "fail" and "the coverage is extrapolated: 5,000 kg" in why33


def test_no_demand_with_a_product_name_is_correct_under_33_and_wrong_under_32():
    """No coverage figure: 3.2 applied basis_wording only because the product name fired the number-and-unit pattern."""
    text = "Stock coverage for SKU-H09 (iced tea summer edition 1 L) in Belgium as of June 2026 is undefined: no demand."
    assert grade.grade_turn(c_turn("NO_DEMAND", text), SV, IO, rubric="3.2")["verdict"] == "wrong"
    g = grade.grade_turn(c_turn("NO_DEMAND", text), SV, IO)
    assert g["verdict"] == "correct" and "basis_wording" not in g["criteria"]


@pytest.mark.parametrize("text", [
    "The coverage of Arabica beans 1 kg (SKU-H10) in Poland is 2.8 kg as of June 2026.",
    "Coverage of Oat cereal bar 1 kg (SKU-H11) is 0 months of kg.",
    "Stock coverage for iced tea summer edition 1 L (SKU-H09) is given in L.",
    "SKU-H10 (Arabica beans 1 kg) has a coverage of 50 months. The figures are in QTY_EQ.",
    "The coverage of Sunflower oil 1 L is 2.25 L.",
])
def test_the_rule_still_fires_when_the_coverage_itself_is_in_a_unit(text):
    v, why = wording("BEYOND_H", text, "3.3")
    assert v == "fail" and why.startswith("coverage given in a unit"), why


@pytest.mark.parametrize("text", [   # the examples rubric 3, 3.1 and 3.2 give of a coverage in a unit
    "SKU-H05 in Spain has 8.5 months of coverage in kg equivalent as of June 2026.",
    "SKU-H05 in Spain has 8.5 months of coverage in packs as of June 2026.",
    "Coverage is 8.5 months. The figures are in QTY_EQ.",
    "SKU-H05 has 8.5 months of cases.",
    "SKU-H05 has a coverage of 2.8 kg.",
    "SKU-H05 coverage in QTY_EQ is 8.5 months.",
])
def test_rubric_examples_of_a_coverage_in_a_unit_still_fail(text):
    assert wording("T4", text, "3.3")[0] == "fail"


@pytest.mark.parametrize("turn", SESSION8B, ids=lambda t: t["question_id"])
def test_session8b_failing_examples_still_fail(turn):
    """Rubric 3 failed T1, T2, T9 and BEYOND_H of the recorded 8b answers of C on the wording; 3.3 too (BEYOND_H names
    'arabica beans 1 kg' and also says 'This is in QTY_EQ')."""
    g = grade.grade_turn({**turn, "tables": []}, SV, IO)
    want = {"T1": "fail", "T2": "fail", "T9": "fail", "BEYOND_H": "fail", "T5": "pass"}.get(turn["question_id"])
    if want:
        assert g["criteria"]["basis_wording"]["result"] == want


@pytest.mark.parametrize("turn", [t for t in SESSION7 if t["question_id"] in {"T1", "T3", "T4", "T7"}],
                         ids=lambda t: t["question_id"])
def test_session7_failing_examples_still_fail(turn):
    g = grade.grade_turn({**turn, "tables": []}, SV, IO)
    assert g["criteria"]["basis_wording"]["result"] == "fail"


# ------------------------------------------------------------------------------------------------ c. stock units

@pytest.mark.parametrize("cfg,qid,rep,sentence", [
    ("C", "H_LOWEST_COUNTRY", "r1", "It has about 2.16 months of coverage, from 82,070 kg of stock."),
    ("B2", "N2", "r1", "at the end of each month of Q2 2026, in kg:"),
    ("B2", "S_DORMANT_VALUE", "r2", "(stock value in EUR)"),
])
def test_the_unit_of_the_stock_beside_the_coverage_still_fails(cfg, qid, rep, sentence):
    g = recorded(STAGE2, cfg, qid, rep)
    text = full_text(g)
    assert sentence in text
    q = grade.coverage_half(Q[qid]) if Q[qid]["metric"] == "closing_stock_and_coverage" else Q[qid]
    grade.set_rubric("3.3")
    try:
        v, why = grade.basis_wording(q, text)
    finally:
        grade.set_rubric(grade.RUBRIC["version"])
    assert v == "fail" and why.startswith("coverage given in a unit"), why


# ------------------------------------------------------------------------------------------------ b. elapsed months

def test_after_n_months_is_never_a_coverage_candidate():
    grade.set_rubric("3.3")
    try:
        s = "The running forecast total is 920 kg after 8 months and passes 1,000 kg in month 9."
        assert grade.month_numbers(s) == []
        assert [str(n.value) for n in grade.month_numbers("It covers about 8.5 months. 920 kg after 8 months.")] == ["8.5"]
        assert [str(n.value) for n in grade.month_numbers("The stock runs out after 8.5 months.")] == ["8.5"]
        assert grade.month_numbers("Demand passes the stock in month 9.") == []
    finally:
        grade.set_rubric(grade.RUBRIC["version"])
    grade.set_rubric("3.2")
    try:
        assert [str(n.value) for n in grade.month_numbers(s)] == ["8"]               # the 3.2 behaviour, kept
    finally:
        grade.set_rubric(grade.RUBRIC["version"])


CRAW = {f: json.loads((ROOT / "eval" / "fixtures" / f).read_text()) for f in (
    "grades_craw-s1.json", "grades_craw-s1.rubric-3.3.json", "grades_craw-s2.json", "grades_craw-s2.rubric-3.3.json")}
# Finding 129 (docs/phase5_notes.md): the counts of forecast months the rubric leaves as coverage candidates, "the
# first 8 months", "within 3 months", "22 months that have demand".
COUNT_HEAD = re.compile(r"\b(?:first|within)\s+(?:the\s+)?$", re.I)
COUNT_TAIL = re.compile(r"[\d,.]+\s+months?\s+(?:that|with)\b", re.I)


def test_no_craw_verdict_depends_on_finding_129(monkeypatch):
    """Session 15: each published C-raw turn graded again from its fixture (answer and tables), once as the grader
    reads it and once with the counts of finding 129 removed from the coverage candidates; every criterion is the
    same. The tool calls are not published, so both gradings read none: routing is equal on both sides by
    construction, the verdicts of record stay those of the fixtures."""
    original = grade.month_numbers

    def without_counts(text):
        return [n for n in original(text) if not (n.decimals == 0 and (
            COUNT_HEAD.search(text[max(0, n.start - 30):n.start]) or COUNT_TAIL.match(text[n.start:n.start + 40])))]

    def regrade(g):
        turn = {k: g[k] for k in ("config", "question_id", "answer", "tables", "request_id")}
        return grade.grade_turn(turn, rubric=g["rubric"])["criteria"]

    hits = set()
    for f, grades in CRAW.items():
        for g in grades:
            text = full_text(g)
            grade.set_rubric(g["rubric"])
            if len(without_counts(text)) != len(original(text)):
                hits.add(g["label"])
            before = regrade(g)
            monkeypatch.setattr(grade, "month_numbers", without_counts)
            after = regrade(g)
            monkeypatch.setattr(grade, "month_numbers", original)
            assert after == before, (f, g["label"])
    grade.set_rubric(grade.RUBRIC["version"])
    # The forms occur, so the test is not empty: "within 3 months", in these selection turns only.
    assert hits == {"CR_S_STOCKOUT_COUNTRY_craw-s1_r1", "CR_S_STOCKOUT_COUNTRY_craw-s2_r2",
                    "CR_H_LOCAL_STOCKOUT_craw-s2_r1", "CR_H_STOCKOUT_ES_craw-s2_r1"}


def b1_t4_turn(request_id):
    g = recorded(STAGE1, "B1", "T4")
    assert "920 kg after 8 months" in g["answer"]
    return {"config": "B1", "question_id": "T4", "answer": g["answer"], "tables": g["tables"], "request_id": request_id,
            "tool_uses": [{"type": "cortex_analyst_text_to_sql", "name": "b1_semantic_view", "input": {}}],
            "tool_results": [], "sql": []}


def test_b1_t4_of_stage_1_is_decided_by_the_number_under_33():
    """Finding 100: the trap 7.714 rounded to 0 decimals matched "after 8 months". 3.2 leaves it manual (the owner
    decided it correct); 3.3 reads 8.5 as the only coverage and passes it without the decision."""
    assert grade.grade_turn(b1_t4_turn(None), SV, IO, rubric="3.2")["verdict"] == "manual"
    g = grade.grade_turn(b1_t4_turn(None), SV, IO)
    assert g["criteria"]["numeric"]["result"] == "pass", g["criteria"]["numeric"]
    assert g["verdict"] == "correct"


def test_manual_decisions_apply_unchanged():
    rid = recorded(STAGE1, "B1", "T4")["request_id"]
    g32 = grade.grade_turn(b1_t4_turn(rid), SV, IO, rubric="3.2")
    assert g32["verdict"] == "correct" and "manual_decision" in g32["criteria"]
    g33 = grade.grade_turn(b1_t4_turn(rid), SV, IO)
    assert g33["verdict"] == "correct" and "manual_decision" not in g33["criteria"]     # nothing left to decide


# ------------------------------------------------------------------------------------------------ recorded sessions

def test_recorded_sessions_move_only_two_t9_turns_of_session_8():
    """Sessions 7 to 8c-0 (59 turns): 3.3 moves B1 T9 and D′ T9 of session 8, wrong to correct, on "The stock coverage
    of Oat cereal bar 1 kg (SKU-H11) ... is **0 months**."; the figure-only score moves nowhere."""
    moved = {}
    for t in TURNS:
        a, b = grade.grade_turn(t, SV, IO, rubric="3.2"), grade.grade_turn(t, SV, IO)
        assert a["verdict_figure_only"] == b["verdict_figure_only"]
        if a["verdict"] != b["verdict"]:
            moved[(t["run"], t["label"])] = (a["verdict"], b["verdict"])
            assert "Oat cereal bar 1 kg" in a["criteria"]["basis_wording"]["why"].replace("oat", "Oat")
    assert moved == {("s8", "b1_t9"): ("wrong", "correct"), ("s8", "dp_t9"): ("wrong", "correct")}
