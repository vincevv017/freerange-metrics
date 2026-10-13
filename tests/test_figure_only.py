"""Session 9a closing (owner, 2026-10-07): the "figure only" score, reported next to the primary verdict of rubric 3.2.
Same grader, same criteria, except the unit half of basis_wording (a sentence gives the coverage in a unit); "basis
not named" still fails it. The primary verdict, the gate and the text of rubric 3.2 do not change. No call."""

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

SV = {"b2_semantic_view", "b1_semantic_view", "a_semantic_view"}
IO = ("DIM_ITEM", "B2_ITEM")
TURNS = [json.loads(x) for x in (ROOT / "eval" / "fixtures" / "recorded_turns.jsonl").read_text().splitlines()]
STAGE1 = json.loads((ROOT / "eval" / "fixtures" / "grades_campaign-s1.json").read_text())


def turn(qid, answer, request_id=None):
    return {"config": "C", "question_id": qid, "answer": answer, "tables": [], "request_id": request_id,
            "tool_uses": [{"type": "generic", "name": "stock_coverage", "input": {}}], "tool_results": [], "sql": []}


def test_a_coverage_worded_in_a_unit_fails_the_primary_only():
    g = grade.grade_turn(turn("T4", "SKU-H05 in Spain has 8.5 months of coverage in kg equivalent as of June 2026."),
                         SV, IO)
    assert g["criteria"]["basis_wording"]["why"].startswith("coverage given in a unit")
    assert (g["verdict"], g["verdict_figure_only"]) == ("wrong", "correct")


def test_a_basis_not_named_fails_both():
    g = grade.grade_turn(turn("T4", "SKU-H05 in Spain covers 8.5 months as of June 2026."), SV, IO)
    assert g["criteria"]["basis_wording"]["why"] == "basis QTY_EQ not named"
    assert (g["verdict"], g["verdict_figure_only"]) == ("wrong", "wrong")


def test_a_unit_wording_that_hides_an_unnamed_basis_fails_both():
    """The primary stops at the unit sentence; the figure-only score still reads whether the basis is named."""
    g = grade.grade_turn(turn("T4", "SKU-H05 in Spain has 8.5 months of coverage in packs as of June 2026."), SV, IO)
    assert g["criteria"]["basis_wording"]["why"].startswith("coverage given in a unit")
    assert (g["verdict"], g["verdict_figure_only"]) == ("wrong", "wrong")


def test_a_wrong_figure_fails_both():
    g = grade.grade_turn(turn("T4", "SKU-H05 in Spain has 7.71 months of coverage in kg equivalent as of June 2026."),
                         SV, IO)
    assert (g["verdict"], g["verdict_figure_only"]) == ("wrong", "wrong")


def test_an_owners_decision_applies_to_both(monkeypatch):
    text = ("SKU-H05 in Spain covers 8.5 months as of June 2026, stock and forecast in kg equivalent. If the window "
            "started in June it would cover 7.71 months.")
    assert grade.grade_turn(turn("T4", text), SV, IO)["verdict"] == "manual"
    dec = {"request_id": "r-1", "configuration": "C", "question_id": "T4", "verdict": "correct", "rule": "R",
           "reason": "x", "date": "2026-10-07"}
    monkeypatch.setitem(grade.DECISIONS, "r-1", dec)
    g = grade.grade_turn(turn("T4", text, request_id="r-1"), SV, IO)
    assert (g["verdict"], g["verdict_figure_only"]) == ("correct", "correct")
    g = grade.grade_turn(turn("T4", text, request_id="r-2"), SV, IO)
    assert (g["verdict"], g["verdict_figure_only"]) == ("manual", "manual")


@pytest.mark.parametrize("t", TURNS, ids=lambda t: f"{t['run']}|{t['label']}")
def test_recorded_turns_differ_only_on_the_unit_half(t):
    g = grade.grade_turn(t, SV, IO)
    if g["verdict_figure_only"] != g["verdict"]:
        assert g["verdict"] == "wrong" and g["verdict_figure_only"] == "correct"
        assert g["criteria"]["basis_wording"]["why"].startswith("coverage given in a unit")


def test_scores_are_counted_per_configuration_for_both():
    s = grade.scores(STAGE1)
    assert s["C"] == {"primary": {"correct": 24, "wrong": 0, "manual": 0},
                      "figure_only": {"correct": 24, "wrong": 0, "manual": 0}}
    assert {c: v["primary"]["correct"] for c, v in s.items()} == {"A": 16, "B1": 13, "B2": 15, "C": 24, "D": 17,
                                                                  "DP": 15}
    assert {c: v["figure_only"]["correct"] for c, v in s.items()} == {"A": 19, "B1": 19, "B2": 19, "C": 24, "D": 20,
                                                                      "DP": 19}


def test_the_gate_reads_the_primary_verdict_only():
    spec = importlib.util.spec_from_file_location("gate", ROOT / "eval" / "gate.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    flipped = [{**g, "verdict_figure_only": "correct"} for g in STAGE1]
    assert gate.gate(flipped) == gate.gate(STAGE1)
