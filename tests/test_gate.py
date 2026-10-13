"""Session 8c, step 3: the stage 2 selection rule (eval/gate.py, eval/gate.md), on recorded smoke answers and synthetic
ones. No call."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("gate", ROOT / "eval" / "gate.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)
grade = gate.grade

SV = {"b2_semantic_view", "b1_semantic_view", "a_semantic_view"}
TURNS = [json.loads(x) for x in (ROOT / "eval" / "fixtures" / "recorded_turns.jsonl").read_text().splitlines()]


def graded(t: dict) -> dict:     # the recorded smoke was graded under rubric 3.2
    return {**grade.grade_turn(t, SV, ("DIM_ITEM", "B2_ITEM"), rubric="3.2"), "answer": t["answer"],
            "tables": t.get("tables", [])}


def smoke() -> list[dict]:
    """Sessions 8 and 8b: T1, T6, T9 and CS_LAST_MONTH_GAP on the six configurations (D′'s CS re-run, its first turn
    is manual)."""
    return [graded(t) for t in TURNS if t["run"] in ("s8", "s8b") and t["question_id"] in
            ("T1", "T6", "T9", "CS_LAST_MONTH_GAP") and t["label"] != "dp_cs_last_month_gap"]


def test_recorded_smoke_selects_t1_and_t9_only():
    res = gate.gate(smoke())
    assert res["discriminating"] == ["T1", "T9"]
    assert res["reasons"]["T1"] == {"failed": ["C", "D"]}
    assert res["reasons"]["T9"]["failed"] == ["A", "B1", "B2", "C", "D", "DP"]
    assert res["not_selected"] == ["CS_LAST_MONTH_GAP", "T6"]
    assert res["a_passed"] == ["T1"]


def test_t6_every_configuration_asks_for_the_month_not_selected():
    """No figure, every answer asks or refuses: basis and scope are not compared."""
    by = {g["config"]: gate.features(g) for g in smoke() if g["question_id"] == "T6"}
    assert all(f["refused"] and f["basis"] is None for f in by.values())


def test_cs_history_figures_are_not_a_difference_in_value():
    """A and B1 cite 400 (April) and 350 (May) as history beside 0 (owner's rule): the answer's figure is 0 everywhere."""
    by = {g["config"]: gate.features(g) for g in smoke() if g["question_id"] == "CS_LAST_MONTH_GAP"}
    assert {c: f["figure"] for c, f in by.items()} == {c: {"": 0.0} for c in by}


def test_a_manual_verdict_must_be_decided_first():
    first = [graded(t) for t in TURNS if t["label"] == "dp_cs_last_month_gap"]
    assert first[0]["verdict"] == "manual"
    with pytest.raises(SystemExit):
        gate.gate(smoke() + first)


def turn(cfg, qid, answer, verdict="correct", warnings="n/a", rows_commented=False, tables=None):
    return {"config": cfg, "question_id": qid, "verdict": verdict, "answer": answer, "tables": tables or [],
            "warnings_relayed": warnings,
            "governance": {"ROWS_COMMENTED": {"flag": rows_commented}, "FRESHNESS_STATED": {"present": False}}}


T4 = "SKU-H05 in Spain covers {} months as of June 2026, stock and forecast in kg equivalent."


def test_rounding_to_005_is_not_a_difference_but_a_rounded_integer_is():
    same = [turn("A", "T4", T4.format("8.5")), turn("B1", "T4", T4.format("8.50")), turn("C", "T4", T4.format("8.45"))]
    assert gate.gate(same)["discriminating"] == []
    far = same + [turn("D", "T4", T4.format("9"))]           # correct by the precision rule, 0.5 away
    assert gate.gate(far)["reasons"]["T4"] == {"value": ["A", "B1", "C", "D"]}


def test_governance_measures_never_count():
    a = turn("A", "T4", T4.format("8.5"))
    b = turn("C", "T4", T4.format("8.5") + "\n\nData freshness: June 2026", rows_commented=True)
    assert gate.gate([a, b])["discriminating"] == []


def test_basis_month_and_refusal_differences():
    a = turn("A", "T4", T4.format("8.5"))
    b = turn("B2", "T4", "SKU-H05 in Spain covers 8.5 months as of June 2026, on value in EUR.")
    assert gate.gate([a, b])["discriminating"] == []             # every configuration correct: basis wording ignored
    assert gate.gate([a, b | {"verdict": "wrong"}])["reasons"]["T4"] == {"failed": ["B2"], "basis": ["A", "B2"]}
    c = turn("C", "T4", "SKU-H05 in Spain covers 8.5 months, stock and forecast in kg equivalent.")
    assert "month" in gate.gate([a, a | {"config": "B1"}, c])["reasons"]["T4"]
    r = turn("D", "T5", "I can't give a coverage in packs: pack sizes don't add up.")
    n = turn("C", "T5", "Dry pasta in the United Kingdom covers 2.37 months as of June 2026, in kg equivalent; packs "
                        "can't be added.")
    assert gate.gate([r, n])["reasons"]["T5"]["refused"] == ["C", "D"]


def test_warnings_only_difference_is_selected_and_dropped_first():
    t2 = "SKU-H03 in Germany covers 7.0 months as of June 2026, stock and forecast in kg equivalent."
    w = [turn("C", "T2", t2 + " Two forecast months were missing and counted as zero.", warnings="yes"),
         turn("B2", "T2", t2, warnings="no"), turn("A", "T2", t2, warnings="yes"),
         turn("B1", "T4", T4.format("8.5"), verdict="wrong"), turn("A", "T4", T4.format("8.5"))]
    res = gate.gate(w)
    assert res["discriminating"] == ["T2", "T4"]
    assert res["reasons"]["T2"] == {"warnings": ["B2"]}
    assert res["drop_order"] == ["T2", "T4"]          # one configuration each; warnings only first


def test_list_answers_compare_their_products():
    base = ("Four products in France stock out within 3 months of June 2026, stock in kg or L equivalent: "
            "SKU-H02 0.5 months, SKU-0039 1.01 months, SKU-0031 1.84 months, SKU-0010 2.21 months.")
    other = base.replace(", SKU-0010 2.21 months", "")
    res = gate.gate([turn("C", "S_STOCKOUT_COUNTRY", base), turn("B2", "S_STOCKOUT_COUNTRY", other, verdict="wrong")])
    assert res["reasons"]["S_STOCKOUT_COUNTRY"]["failed"] == ["B2"]


def test_held_out_questions_are_not_selected_by_the_gate():
    t = turn("C", "H_STOCKOUT_ES", "SKU-0001", verdict="wrong")
    assert gate.gate([t])["discriminating"] == []


# Session 9a closing (owner, 2026-10-07): questions the owner forces into stage 2.

BY = "owner, 2026-10-07"
CS = "The Q2 2026 closing stock of SKU-H11 in Switzerland is 0 packs."


def test_a_forced_question_not_otherwise_selected_is_added_with_the_owners_reason():
    w = [turn("C", "CS_LAST_MONTH_GAP", CS), turn("B2", "CS_LAST_MONTH_GAP", CS)]
    assert gate.gate(w)["discriminating"] == []
    res = gate.gate(w, forced=["CS_LAST_MONTH_GAP"], forced_by=BY)
    assert res["discriminating"] == ["CS_LAST_MONTH_GAP"]
    assert res["reasons"]["CS_LAST_MONTH_GAP"] == {"forced": BY}
    assert res["forced"] == ["CS_LAST_MONTH_GAP"] and res["forced_by"] == BY
    assert res["not_selected"] == [] and res["drop_order"] == []


def test_a_forced_question_already_selected_keeps_its_reasons_and_is_never_dropped():
    w = [turn("B1", "T4", T4.format("8.5"), verdict="wrong"), turn("A", "T4", T4.format("8.5")),
         turn("C", "CS_LAST_MONTH_GAP", CS)]
    assert gate.gate(w)["drop_order"] == ["T4"]                  # one configuration differs
    res = gate.gate(w, forced=["T4", "CS_LAST_MONTH_GAP"], forced_by=BY)
    assert res["reasons"]["T4"] == {"failed": ["B1"], "forced": BY}
    assert res["drop_order"] == []
    assert res["discriminating"] == ["T4", "CS_LAST_MONTH_GAP"]          # the order of the reference file


def test_forcing_a_held_out_or_unknown_question_or_without_its_author_is_refused():
    w = [turn("C", "T4", T4.format("8.5"))]
    for bad in (["H_STOCKOUT_ES"], ["NOT_A_QUESTION"], ["N1"]):      # N1: added in stage 2 (session 9b)
        with pytest.raises(SystemExit):
            gate.gate(w, forced=bad, forced_by=BY)
    with pytest.raises(SystemExit):
        gate.gate(w, forced=["T4"])


def test_without_forced_questions_the_output_has_no_forced_key():
    assert "forced" not in gate.gate([turn("C", "T4", T4.format("8.5"))])


def test_the_plan_runs_a_forced_question_from_r2(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("campaign", ROOT / "eval" / "campaign.py")
    campaign = importlib.util.module_from_spec(spec)
    sys.modules["campaign"] = campaign
    spec.loader.exec_module(campaign)
    res = gate.gate([turn("C", "CS_LAST_MONTH_GAP", CS)], forced=["CS_LAST_MONTH_GAP"], forced_by=BY)
    out = tmp_path / "stage2.yaml"
    gate.write(res, out)
    monkeypatch.setattr(campaign, "STAGE2_FILE", out)
    monkeypatch.setattr(campaign, "held_out", lambda: [])
    blocks = {b["config"]: b for b in campaign.plan(2)}
    assert sorted(t["rep"] for t in blocks["C"]["turns"] if t["qid"] == "CS_LAST_MONTH_GAP") == [2, 3, 4, 5]
    assert sorted(t["rep"] for t in blocks["D"]["turns"] if t["qid"] == "CS_LAST_MONTH_GAP") == [2, 3]


# Session 9a closing (owner, 2026-10-07): relative tolerance on EUR amounts; basis wording ignored when all are correct.

def g2(line: str) -> str:
    return f"Stock on hand by country at June 2026, in EUR:\n- {line}"


def test_eur_amounts_within_half_a_percent_are_the_same_figure():
    exact = turn("C", "G2", g2("SE: 14,476,855.48 EUR"))
    for same in ("SE: 14.5 million EUR", "SE: 14,476,855 EUR", "SE: 14,512,345 EUR"):     # 0.16, 0.00, 0.25 percent
        assert gate.gate([exact, turn("A", "G2", g2(same))])["discriminating"] == [], same
    far = gate.gate([exact, turn("A", "G2", g2("SE: 14.0 million EUR"))])               # 3.3 percent
    assert far["reasons"]["G2"] == {"value": ["A", "C"]}


def test_months_keep_the_absolute_tolerance():
    """BEYOND_H: 50.0 against 50.2 months is 0.4 percent apart, but months are compared at 0.05, not relatively."""
    t = "SKU-H10 in Poland covers {} months as of June 2026, stock and forecast in kg equivalent."
    res = gate.gate([turn("C", "BEYOND_H", t.format("50.0")), turn("D", "BEYOND_H", t.format("50.2"))])
    assert res["reasons"]["BEYOND_H"] == {"value": ["C", "D"]}


def test_basis_wording_alone_among_correct_answers_selects_nothing():
    """S_OWN_UNIT and T3 of stage 1: every configuration correct, the basis words named differ."""
    own = "SKU-H03 in Germany covers 3.06 months as of June 2026, measured in its own unit (packs){}."
    w = [turn("C", "S_OWN_UNIT", own.format("")), turn("B1", "S_OWN_UNIT", own.format(", i.e. kg equivalent"))]
    assert gate.features(w[1])["basis"] != gate.features(w[0])["basis"]
    assert gate.gate(w)["discriminating"] == []
    t3 = "covers 6.0 months as of June 2026, stock and forecast in kg equivalent{}."
    w3 = [turn("C", "T3", t3.format("")), turn("A", "T3", t3.format(", in its own unit"))]
    assert gate.gate(w3)["discriminating"] == []
    assert gate.gate(w3 + [turn("D", "T3", t3.format(""), verdict="wrong")])["reasons"]["T3"] == {
        "failed": ["D"], "basis": ["A"]}


STAGE1 = json.loads((ROOT / "eval" / "fixtures" / "grades_campaign-s1.json").read_text())   # rubric 3.2, 2026-10-07


def test_stage1_grades_select_15_questions_after_the_owners_decisions():
    """G2 (EUR rounding), S_OWN_UNIT, T3 and T4 (basis words among correct answers) are no longer selected."""
    res = gate.gate(STAGE1)
    assert res["discriminating"] == ["T1", "T2", "T7", "T7_R1", "T8", "NO_DEMAND", "BEYOND_H", "BULK_SCOPE", "DIM_MIX",
                                     "T9", "BULK_SCOPE_DRILL", "G1", "S_STOCKOUT_COUNTRY", "S_FIRST_WORLD",
                                     "S_DORMANT_VALUE"]
    assert {"G2", "S_OWN_UNIT", "T3", "T4", "CS_LAST_MONTH_GAP"} <= set(res["not_selected"])
    assert res["drop_order"] == ["G1"]
    forced = gate.gate(STAGE1, forced=["CS_LAST_MONTH_GAP", "T9"], forced_by=BY)
    assert len(forced["discriminating"]) == 16 and forced["reasons"]["CS_LAST_MONTH_GAP"] == {"forced": BY}
    assert forced["reasons"]["T9"]["forced"] == BY and "failed" in forced["reasons"]["T9"]
