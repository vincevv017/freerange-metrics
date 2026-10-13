"""Session 9b, step 2 (owner, 2026-10-07): grading the three questions added in stage 2.

- Route "both" for C: the procedure and the closing-stock view are each called at least once in the turn. For B2 the
  expected route stays the view. A turn that answers both halves from one tool is graded on its figures and fails the
  routing criterion.
- N1 and N2 carry two halves, closing stock and coverage, each graded on its own figures; N3 is graded on its exact item
  set, as the held-out list questions.
- No change for existing questions: tests/test_rubric_32.py keeps the recorded verdicts, and the stage 1 regrade is
  compared with the grades written before this change (snowflake/phase5_campaign/stage2_results.md).
Synthetic answers, no call.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("grade", ROOT / "eval" / "grade.py")
grade = importlib.util.module_from_spec(_spec)
sys.modules["grade"] = grade
_spec.loader.exec_module(grade)

SV = {"type": "cortex_analyst_text_to_sql", "name": "b2_semantic_view", "input": {}}
PROC = {"type": "generic", "name": "stock_coverage", "input": {"grain": "[\"sku_code\",\"country_code\"]"}}
SKILL = {"type": "code_execution", "name": "code_execution", "input": {}}
SVS = {"b2_semantic_view"}


def g(config, qid, text, uses=(SV, PROC)):
    return grade.grade_turn({"config": config, "question_id": qid, "answer": text, "tool_uses": list(uses),
                             "tool_results": [], "sql": []}, SVS, ("DIM_ITEM", "B2_ITEM"))


def crit(res, name):
    return res["criteria"][name]["result"]


N1_OK = ("SKU-H11 in Switzerland closed Q2 2026 at 0 kg: there is no stock snapshot in June 2026. As of June 2026 its "
         "coverage is 0 months (no stock), stock and forecast measured in kg.\nData freshness: June 2026")
N2_OK = ("Closing stock of SNACK_BARS in Switzerland, in kg:\n- April 2026: 900\n- May 2026: 350\n- June 2026: 450\n"
         "As of June 2026 the 450 kg cover 2.25 months of forecast, stock and forecast measured in kg.\n"
         "Data freshness: June 2026")
N3_ITEMS = ["SKU-H02", "SKU-0039", "SKU-0031", "SKU-0010", "SKU-0008", "SKU-0033", "SKU-0027", "SKU-0016", "SKU-0024",
            "SKU-0021"]


def n3(items):
    return ("As of June 2026, the ten products in France that run out first (stock and forecast in kg or L "
            "equivalent): " + ", ".join(items) + ". None is already out of stock and none has no demand.")


# ------------------------------------------------------------------------------------------------ routing

def test_c_both_tools_called_passes_routing():
    assert crit(g("C", "N1", N1_OK), "routing") == "pass"
    assert g("C", "N1", N1_OK)["verdict"] == "correct"


@pytest.mark.parametrize("uses", [(PROC,), (SV,), ()], ids=["procedure only", "view only", "no tool"])
def test_c_one_tool_for_both_halves_fails_routing_and_keeps_its_figures(uses):
    res = g("C", "N1", N1_OK, uses)
    assert crit(res, "routing") == "fail" and res["verdict"] == "wrong"
    assert crit(res, "closing_stock") == "pass" and crit(res, "coverage") == "pass"


def test_c_both_with_a_skill_call_fails_routing():
    assert crit(g("C", "N2", N2_OK, (SV, PROC, SKILL)), "routing") == "fail"


def test_b2_expected_route_stays_the_view():
    assert crit(g("B2", "N1", N1_OK, (SV,)), "routing") == "pass"
    assert g("B2", "N1", N1_OK, (SV,))["verdict"] == "correct"
    assert crit(g("B2", "N1", N1_OK, (SV, PROC)), "routing") == "fail"


def test_route_both_is_defined_for_c_and_b2_only():
    with pytest.raises(SystemExit):
        g("D", "N1", N1_OK)


def test_n3_routes_like_a_coverage_question():
    assert crit(g("C", "N3", n3(N3_ITEMS), (PROC,)), "routing") == "pass"
    assert crit(g("B2", "N3", n3(N3_ITEMS), (SV,)), "routing") == "pass"


# ------------------------------------------------------------------------------------------------ N1

def test_n1_correct():
    res = g("C", "N1", N1_OK)
    assert res["verdict"] == "correct", res["criteria"]
    assert {"closing_stock", "coverage", "basis_wording", "analysis_month_named", "no_aggregated_coverage",
            "routing"} <= set(res["criteria"])


def test_n1_zero_in_words_counts_for_the_closing_stock():
    text = N1_OK.replace("closed Q2 2026 at 0 kg", "had nothing in stock at the end of Q2 2026")
    assert crit(g("C", "N1", text), "closing_stock") == "pass"


def test_n1_may_carried_into_june_is_wrong():
    text = N1_OK.replace("closed Q2 2026 at 0 kg: there is no stock snapshot in June 2026",
                         "closed Q2 2026 at 350 kg")
    res = g("C", "N1", text)
    assert crit(res, "closing_stock") == "fail" and res["verdict"] == "wrong"


def test_n1_history_beside_the_answer_is_left_to_the_owner():
    text = N1_OK.replace("there is no stock snapshot in June 2026", "it held 400 kg in April and 350 kg in May")
    assert crit(g("C", "N1", text), "closing_stock") == "manual"


def test_n1_the_coverage_from_mays_stock_is_wrong():
    res = g("C", "N1", N1_OK.replace("coverage is 0 months (no stock)", "coverage is 3.5 months"))
    assert crit(res, "coverage") == "fail" and crit(res, "closing_stock") == "pass"


def test_n1_trap_figures_framed_as_history_are_left_to_the_owner():
    text = ("SKU-H11 in Switzerland closed Q2 2026 at 0 kg. As of June 2026 its coverage is 0 months, stock and "
            "forecast measured in kg. With May's 350 kg it would have been 3.5 months, but that stock is gone.")
    res = g("C", "N1", text)
    assert crit(res, "coverage") == "manual"                    # 3.5 framed as history: the owner's rule decides
    assert crit(res, "closing_stock") == "manual"               # 350 likewise
    assert "3.5" not in res["criteria"]["closing_stock"]["why"]  # a coverage in months is no closing stock candidate


# ------------------------------------------------------------------------------------------------ N2

def test_n2_correct():
    res = g("C", "N2", N2_OK)
    assert res["verdict"] == "correct", res["criteria"]


def test_n2_months_on_one_line_or_in_a_table():
    one_line = ("SNACK_BARS in Switzerland closed April 2026 at 900 kg, May 2026 at 350 kg and June 2026 at 450 kg. "
                "As of June 2026 the stock covers 2.25 months, stock and forecast measured in kg.")
    assert g("C", "N2", one_line)["verdict"] == "correct"
    table = grade.grade_turn({"config": "B2", "question_id": "N2", "tool_uses": [SV], "tool_results": [], "sql": [],
                              "answer": "As of June 2026 the stock covers 2.25 months, stock and forecast in kg.",
                              "tables": [{"title": "Closing stock", "columns": ["MONTH", "CLOSING_STOCK_QTY_EQ"],
                                          "rows": [["2026-04-01", "900"], ["2026-05-01", "350"],
                                                   ["2026-06-01", "450"]]}]}, SVS)
    assert table["verdict"] == "correct", table["criteria"]


def test_n2_may_carried_from_april_is_wrong():
    res = g("C", "N2", N2_OK.replace("May 2026: 350", "May 2026: 850"))
    assert crit(res, "closing_stock") == "fail"


def test_n2_a_month_not_given_is_left_to_the_owner():
    res = g("C", "N2", N2_OK.replace("- May 2026: 350\n", ""))
    assert crit(res, "closing_stock") == "manual"


def test_n2_the_months_added_is_wrong():
    res = g("C", "N2", N2_OK.replace("Data freshness", "Over Q2 2026 that is 1,700 kg in all.\nData freshness"))
    assert crit(res, "closing_stock") == "fail"


def test_n2_june_carried_coverage_is_wrong_and_a_cited_child_is_not():
    assert crit(g("C", "N2", N2_OK.replace("cover 2.25 months", "cover 4.0 months")), "coverage") == "fail"
    cited = N2_OK.replace("Data freshness", "SKU-H12 alone covers 4.5 months; SKU-H11 has none.\nData freshness")
    res = g("C", "N2", cited)
    assert crit(res, "coverage") == "pass" and crit(res, "no_aggregated_coverage") == "pass"


# ------------------------------------------------------------------------------------------------ N3

def test_n3_exact_set():
    res = g("C", "N3", n3(N3_ITEMS), (PROC,))
    assert res["verdict"] == "correct", res["criteria"]
    assert crit(res, "item_set") == "pass"


def test_n3_a_missing_or_an_extra_product_is_wrong():
    assert crit(g("C", "N3", n3(N3_ITEMS[:9]), (PROC,)), "item_set") == "fail"
    assert crit(g("C", "N3", n3(N3_ITEMS + ["SKU-0045"]), (PROC,)), "item_set") == "fail"


def test_n3_the_naive_mean_ratio_set_is_wrong():
    naive = grade.QUESTIONS["N3"]["expected"]["wrong_values"]["naive_mean_ratio"]
    assert crit(g("B2", "N3", n3(naive), (SV,)), "item_set") == "fail"


# ------------------------------------------------------------------------------------------------ groups for the report

def test_route_groups():
    assert grade.route_group(grade.QUESTIONS["N1"]) == grade.route_group(grade.QUESTIONS["N2"]) == "both"
    assert grade.route_group(grade.QUESTIONS["N3"]) == "procedure"
    assert grade.route_group(grade.QUESTIONS["CS_FAMILY"]) == grade.route_group(grade.QUESTIONS["G1"]) == "view only"
    assert grade.route_group(grade.QUESTIONS["T6"]) == "no tool"
    assert grade.route_group(grade.QUESTIONS["H_STOCKOUT_ES"]) == "procedure"
