"""
eval/grade.py on recorded answers and on synthetic wrong ones.

- eval/fixtures/session7_agent_c.jsonl: the 14 reference questions agent C answered in session 7, rebuilt from
  snowflake/phase4_agent_c/results.md (tool parameters as sent, numbers and wording as recorded there; the raw events
  were kept outside the repository and are gone). Every one was judged correct in session 7; T5 is the recorded
  deviation (a refusal by the model with a QTY_EQ answer).
- synthetic turns: one per wrong behaviour the rubric names (an aggregated coverage, a skipped month, a stale stock, a
  raw-pack number, a picked month for T6, a fan-out number, a G2 item join, a wrong route) and one manual case.
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
sys.modules["grade"] = grade          # dataclasses resolve their module by name
_spec.loader.exec_module(grade)

SESSION7 = [json.loads(x) for x in (ROOT / "eval" / "fixtures" / "session7_agent_c.jsonl").read_text().splitlines()]
SV = {"b2_semantic_view"}


SESSION8B = [json.loads(x) for x in (ROOT / "eval" / "fixtures" / "session8b_agent_c.jsonl").read_text().splitlines()]
V3_BASIS_FAILS_S7 = {"T1", "T3", "T4", "T7"}      # rubric v3: 'in QTY_EQ' about coverage (T1), or no basis named


@pytest.mark.parametrize("turn", SESSION7, ids=lambda t: t["question_id"])
def test_session7_answers_grade_correct(turn):
    """Correct in session 7 (rubric v1). Under rubric v3 every criterion still holds except basis_wording, which fails
    where the answer gives coverage 'in QTY_EQ' or names no basis."""
    g = grade.grade_turn(turn)
    others = {k: c["result"] for k, c in g["criteria"].items() if k != "basis_wording"}
    assert set(others.values()) == {"pass"}, g
    bw = g["criteria"].get("basis_wording", {}).get("result")
    assert (bw == "fail") == (turn["question_id"] in V3_BASIS_FAILS_S7), g
    assert g["verdict"] == ("wrong" if turn["question_id"] in V3_BASIS_FAILS_S7 else "correct"), g


@pytest.mark.parametrize("turn", SESSION8B, ids=lambda t: t["question_id"])
def test_session8b_answers_fail_the_basis_wording_where_they_give_coverage_in_qty_eq(turn):
    """Session 8c-0, rubric v3, on the recorded 8b smoke answers of C (text only): 'The figures are in QTY_EQ', 'This
    is in QTY_EQ' or 'in QTY_EQ ... coverage is' about a coverage is wrong; T5 ('The figure is in months, not packs
    ... stock and forecast are measured in quantity-equivalent units') names its basis correctly."""
    g = grade.grade_turn({**turn, "tool_uses": []})
    bw = g["criteria"].get("basis_wording")
    want = {"T1": "fail", "T2": "fail", "T9": "fail", "BEYOND_H": "fail", "T5": "pass"}.get(turn["question_id"])
    assert (bw or {}).get("result") == want, g


def test_session7_t5_is_the_model_refusal_with_a_qty_eq_answer():
    g = grade.grade_turn(next(t for t in SESSION7 if t["question_id"] == "T5"))
    assert g["criteria"]["t5_outcome"]["why"] == "model_refusal_with_qty_eq_answer"


def test_session7_warnings_recorded():
    by = {t["question_id"]: grade.grade_turn(t)["warnings_relayed"] for t in SESSION7}
    assert by["T2"] == by["BULK_SCOPE"] == by["T7"] == by["BEYOND_H"] == "yes" and by["T1"] == "n/a"


def turn(qid, answer, config="B2", uses=None, results=None, sql=None):
    return {"config": config, "question_id": qid, "answer": answer, "tool_uses": uses if uses is not None else
            [{"type": "cortex_analyst_text_to_sql", "name": "b2_semantic_view", "input": {}}],
            "tool_results": results or [], "sql": sql or []}


@pytest.mark.parametrize("qid,answer,criterion", [
    ("T1", "As of June 2026 flour and baking in France covers 6.25 months (average of its SKUs).", "numeric"),
    ("T1", "As of June 2026 the SKUs cover 12.0 months and 0.5 months, so the family covers 12.5 months.", "numeric"),
    ("T2", "SKU-H03 in Germany covers 5.0 months as of June 2026.", "numeric"),
    ("T9", "SKU-H11 in Switzerland covers 3.5 months as of June 2026.", "numeric"),
    ("T1", "Flour and baking in France covers 2.8 months.", "analysis_month_named"),
    ("T5", "Dry pasta in the United Kingdom covers 8.5 months of packs as of June 2026.", "t5_outcome"),
    ("T6", "For June 2026, flour and baking in France covers 2.8 months.", "refusal"),
    ("T7_R1", "As of June 2026: ACTIVE 2.25 months, PHASE_OUT 6.0 months.", "refusal"),
    ("CS_LAST_MONTH_GAP", "The closing stock of SKU-H11 in Switzerland for Q2 2026 was 350 kg (May).", "numeric"),
    ("G1", "The forecast for fruit juice in France in September 2026 is 764 units.", "numeric"),
])
def test_wrong_behaviours_grade_wrong(qid, answer, criterion):
    g = grade.grade_turn(turn(qid, answer), SV)
    assert g["verdict"] == "wrong" and g["criteria"][criterion]["result"] == "fail", g


def test_drill_total_equal_to_the_mean_of_rows_is_an_aggregation():
    rows = "\n".join(["- BE: 11.4 months", "- DE: 4.1 months", "- ES: 1.9 months", "- FR: 7.5 months",
                      "- IT: 8.7 months", "- SE: 10.7 months"])
    g = grade.grade_turn(turn("BULK_SCOPE_DRILL", f"As of June 2026:\n{rows}\nAverage across countries: 7.4 months."), SV)
    assert g["criteria"]["no_aggregated_coverage"]["result"] == "fail"


G2_ROWS = {"FR": "43,879,032.93", "BE": "14,764,495.40", "NL": "20,232,037.47", "GB": "24,672,306.06",
           "DE": "24,697,602.43", "CH": "28,912,589.50", "PL": "15,096,357.34", "IT": "14,978,427.85",
           "ES": "48,525,033.13", "SE": "14,476,855.48"}


def g2_text(over=None):
    rows = {**G2_ROWS, **(over or {})}
    return "Closing stock value at June 2026, EUR:\n" + "\n".join(f"| {c} | {v} |" for c, v in rows.items())


def test_g2_full_precision_correct_and_fanout_wrong():
    assert grade.grade_turn(turn("G2", g2_text()), SV)["verdict"] == "correct"
    g = grade.grade_turn(turn("G2", g2_text({"SE": "14,481,655.48"})), SV)
    assert g["verdict"] == "wrong" and "SE" in g["criteria"]["numeric"]["why"]


def test_g2_in_millions_is_decided_on_the_sql():
    """The indistinguishable-precision guard: SE's fan-out (+4,800 EUR) is invisible at 0.1 million."""
    millions = {c: f"{float(v.replace(',', '')) / 1e6:.1f} million" for c, v in G2_ROWS.items()}
    join = ["SELECT g.country_code, SUM(s.stock_value_eur) FROM FCT_STOCK_SNAPSHOT s JOIN DIM_ITEM i "
            "ON s.item_id = i.item_id JOIN DIM_GEO g ON s.country_id = g.country_id GROUP BY 1"]
    plain = ["SELECT g.country_code, SUM(s.stock_value_eur) FROM FCT_STOCK_SNAPSHOT s "
             "JOIN DIM_GEO g ON s.country_id = g.country_id WHERE s.snapshot_month = '2026-06-01' GROUP BY 1"]
    dedup = ["SELECT g.country_code, SUM(s.stock_value_eur) FROM FCT_STOCK_SNAPSHOT s JOIN (SELECT DISTINCT item_id, "
             "item_type FROM DIM_ITEM) i ON s.item_id = i.item_id JOIN DIM_GEO g USING (country_id) GROUP BY 1"]
    assert grade.grade_turn(turn("G2", g2_text(millions), sql=join), SV)["verdict"] == "wrong"
    assert grade.grade_turn(turn("G2", g2_text(millions), sql=plain), SV)["verdict"] == "correct"
    assert grade.grade_turn(turn("G2", g2_text(millions), sql=dedup), SV)["verdict"] == "correct"
    assert grade.grade_turn(turn("G2", g2_text(millions)), SV)["verdict"] == "manual"
    view = ["SELECT g.country_code, SUM(s.stock_value_eur) FROM FCT_STOCK_SNAPSHOT_GAPFILLED s JOIN B2_ITEM i "
            "ON s.item_id = i.item_id JOIN DIM_GEO g ON s.country_id = g.country_id GROUP BY 1"]
    assert grade.grade_turn(turn("G2", g2_text(millions), sql=view), SV, ("DIM_ITEM", "B2_ITEM"))["verdict"] == "wrong"


def test_g2_full_precision_needs_no_sql():
    assert grade.grade_turn(turn("G2", g2_text()), SV)["criteria"]["numeric"]["why"] == "10 rows match"


def test_routing():
    sv_use = [{"type": "cortex_analyst_text_to_sql", "name": "b2_semantic_view", "input": {}}]
    skill_use = [{"type": "server_skill", "name": "server_skill", "input": {"skill_name": "linkml-coverage"}},
                 {"type": "code_execution", "name": "bash", "input": {"command": "python3 coverage.py"}}]
    t1 = "Flour and baking in France covers 2.8 months as of June 2026."
    assert grade.grade_turn(turn("T1", t1, "D", sv_use + skill_use), SV)["criteria"]["routing"]["result"] == "pass"
    assert grade.grade_turn(turn("T1", t1, "D", sv_use), SV)["criteria"]["routing"]["result"] == "fail"
    assert grade.grade_turn(turn("T1", t1, "DP", sv_use + skill_use), SV)["criteria"]["routing"]["result"] == "pass"
    g1 = "The forecast for fruit juice in France for September 2026 is 6,416 kg or L equivalent."
    assert grade.grade_turn(turn("G1", g1, "DP", sv_use), SV)["verdict"] == "correct"
    assert grade.grade_turn(turn("G1", g1, "DP", skill_use + sv_use), SV)["criteria"]["routing"]["result"] == "fail"
    t6 = "Which month do you want? The latest is June 2026."
    assert grade.grade_turn(turn("T6", t6, "B1", []), SV)["verdict"] == "correct"
    assert grade.grade_turn(turn("T6", t6, "B1", sv_use), SV)["criteria"]["routing"]["result"] == "fail"


def test_unclassifiable_answer_is_manual():
    g = grade.grade_turn(turn("NO_DEMAND", "Iced tea summer edition in Belgium, June 2026: see the table."), SV)
    assert g["verdict"] == "manual"


def test_country_codes_are_case_sensitive():
    rows = "\n".join(["- BE: 11.4 months", "- DE: 4.1 months", "- ES: 1.9 months", "- FR: 7.5 months",
                      "- IT: 8.7 months", "- SE: 10.7 months"])
    text = f"As of June 2026:\n{rows}\nIt is 3.0 months lower than last year, and it is not an average."
    assert grade.grade_turn(turn("BULK_SCOPE_DRILL", text), SV)["criteria"]["numeric"]["result"] == "pass"


def test_t6_real_b2_answer_horizon_count_is_not_a_coverage():
    """Session 8, B2 smoke: 'the next 24 months of forecast demand' is the horizon, not a coverage figure."""
    text = ("Which month do you want the coverage for? Stock coverage is measured at a single analysis month, so I "
            "can't give one figure for the whole of 2026. It also can't be summed or averaged across months.\n\nYou "
            "could pick one month between January and June 2026. June 2026 is the latest available month. I can also "
            "give you a month-by-month series for 2026 if you'd like that.\n\nOnce you choose, I'll calculate coverage "
            "for Flour and Baking in France (FR) on standard items. Coverage will be the number of months the stock on "
            "hand lasts against the next 24 months of forecast demand.")
    g = grade.grade_turn(turn("T6", text, "B2", []), SV)
    assert g["verdict"] == "correct", g


def test_t6_real_b1_answer_horizon_count_is_not_a_coverage():
    """Session 8, B1 smoke: 'the French forecast for the 24 months that follow it' is the horizon."""
    text = ("Coverage is measured at one analysis month, so I can't compute it for a whole year. Please tell me which "
            "month you mean.\n\nStock snapshots run monthly from July 2023 to June 2026. For 2026, the months available "
            "are January to June 2026.\n\nI can give coverage for one of those months, for example June 2026, which is "
            "the latest. I can also give a series with one value per month from January to June. Each value would be "
            "the closing stock of flour and baking in France for that month, measured against the French forecast for "
            "the 24 months that follow it. Only STANDARD stock counts toward coverage, and I'd tell you how much BULK "
            "stock was left out.\n\nWhich would you like?")
    assert grade.grade_turn(turn("T6", text, "B1", []), SV)["verdict"] == "correct"


def test_a_coverage_of_24_months_stated_as_coverage_still_counts():
    g = grade.grade_turn(turn("T6", "For June 2026, coverage is 24 months.", "B1", []), SV)
    assert g["criteria"]["refusal"]["result"] == "fail"


def test_manual_decision_applies_by_request_id_only():
    text = ("Closing stock of Oat cereal bar 1 kg (SKU-H11) in Switzerland for Q2 2026 is 0 kg equivalent. It did hold "
            "stock earlier in the quarter: 400 kg equivalent in April and 350 kg equivalent in May.")
    t = {**turn("CS_LAST_MONTH_GAP", text, "B1"), "request_id": "00000013-0000-4000-8000-000000000013"}
    g = grade.grade_turn(t, SV)
    assert g["verdict"] == "correct" and g["criteria"]["numeric"]["result"] == "manual"
    assert "WRONG_VALUE_CITED_AS_HISTORY" in g["criteria"]["manual_decision"]["why"]
    assert grade.grade_turn({**t, "request_id": "another"}, SV)["verdict"] == "manual"


def test_rubric_v2_skill_load_is_not_a_tool():
    """Rubric v2: D' T6 loaded the skill, read 'ask which month', and asked: no tool used."""
    load = [{"type": "skill", "name": "skill", "input": {"command": "linkml-coverage"}}]
    t6 = "Which month do you want as the analysis month? The latest stock snapshot is June 2026."
    assert grade.grade_turn(turn("T6", t6, "DP", load), SV)["verdict"] == "correct"
    t1 = "Flour and baking in France covers 2.8 months as of June 2026."
    sv_use = [{"type": "cortex_analyst_text_to_sql", "name": "b2_semantic_view", "input": {}}]
    assert grade.grade_turn(turn("T1", t1, "DP", load + sv_use), SV)["criteria"]["routing"]["result"] == "fail"


def test_t6_real_d_answer_year_before_months_is_not_a_coverage():
    """Session 8, D smoke: 'the 2026 months available are January to June' names a year, not a coverage."""
    text = ("Coverage needs one analysis month, and \"the whole year 2026\" is a period, so I can't pick a month for "
            "you.\n\nWhich month of 2026 do you mean? The latest stock snapshot is June 2026. The analysis months run "
            "from July 2023 to June 2026, so the 2026 months available are January to June.\n\nI can also give a "
            "series with one coverage value per month, for example January to June 2026. Coverage can't be totalled "
            "or averaged across months. I'll use flour and baking in France, STANDARD items only, in quantity "
            "equivalent unless you want value.")
    assert grade.grade_turn(turn("T6", text, "D", []), SV)["verdict"] == "correct"


# ================================================================================================ rubric v3 (session 8c-0)

def c_turn(qid, answer, results=None):
    return {"config": "C", "question_id": qid, "answer": answer, "tool_results": results or [],
            "tool_uses": [{"type": "generic", "name": "stock_coverage", "input": {}}]}


@pytest.mark.parametrize("answer,result", [
    ("As of June 2026, flour and baking in France covers 2.8 months, with stock and forecast measured in kg equivalent.", "pass"),
    ("As of June 2026, flour and baking in France covers 2.8 months on a kg-equivalent basis.", "pass"),
    ("As of June 2026, the coverage of flour and baking in France is 2.8 months in kg.", "fail"),
    ("As of June 2026, flour and baking in France covers 2.8 months. Every figure is in QTY_EQ (kg or L equivalent).", "fail"),
    ("As of June 2026, flour and baking in France covers 2.8 months.", "fail"),            # no basis named
])
def test_v3_coverage_is_in_months_and_names_its_basis(answer, result):
    g = grade.grade_turn(c_turn("T1", answer))
    assert g["criteria"]["basis_wording"]["result"] == result, g


@pytest.mark.parametrize("answer,result", [
    ("The coverage in France in June 2026 is 10.2 months, in kg and L equivalent.", "fail"),
    ("In June 2026 France covers 8.7 months on value (EUR).", "fail"),                     # basis changed, no reason
    ("Quantity equivalent would add kg and L, which are not comparable, so I measured stock and forecast in value "
     "(EUR): France covers 8.7 months as of June 2026.", "pass"),
    ("The tool refused quantity equivalent for France in June 2026 because the country mixes kg and L "
     "(BASIS_NOT_COMPARABLE); it can be measured in value (EUR) instead.", "pass"),
])
def test_v3_dim_mix_basis_switch(answer, result):
    g = grade.grade_turn(c_turn("DIM_MIX", answer))
    assert g["criteria"]["basis_switch"]["result"] == result, g


def test_v3_own_unit_question_names_cases():
    ok = grade.grade_turn(c_turn("S_OWN_UNIT", "SKU-0046 covers 3.1 months as of June 2026, with stock and forecast "
                                               "measured in its own unit, cases of 10."))
    assert ok["verdict"] == "correct", ok
    bad = grade.grade_turn(c_turn("S_OWN_UNIT", "SKU-0046 covers 3.1 months of cases as of June 2026."))
    assert bad["criteria"]["basis_wording"]["result"] == "fail"


def test_v3_stockout_rows_and_apart_block():
    good = ("From June 2026, on a kg or L equivalent basis, four products stock out within 3 months in France:\n"
            "- SKU-H02: 0.5 months (July 2026)\n- SKU-0039: 1.0 months\n- SKU-0031: 1.8 months\n- SKU-0010: 2.2 months")
    assert grade.grade_turn(c_turn("S_STOCKOUT_COUNTRY", good))["verdict"] == "correct"
    missing = good.replace("- SKU-0010: 2.2 months", "")
    assert grade.grade_turn(c_turn("S_STOCKOUT_COUNTRY", missing))["criteria"]["selection_rows"]["result"] == "fail"
    extra = good + "\n- SKU-0046: 3.1 months"
    assert grade.grade_turn(c_turn("S_STOCKOUT_COUNTRY", extra))["criteria"]["selection_rows"]["result"] == "fail"
    first = ("Worldwide from June 2026, on a kg or L equivalent basis, the first 10 to stock out:\n" + "\n".join(
        f"- {r['sku_code']}: {r['value']:.1f} months" for r in grade.QUESTIONS["S_FIRST_WORLD"]["expected"]["rows"]))
    assert grade.grade_turn(c_turn("S_FIRST_WORLD", first))["criteria"]["selection_rows"]["result"] == "fail"   # apart not named
    first += "\nAlready out: SKU-H08 and SKU-H11. No demand: SKU-H09."
    assert grade.grade_turn(c_turn("S_FIRST_WORLD", first))["verdict"] == "correct"


@pytest.mark.parametrize("answer,result", [
    ("In June 2026, 28 item and country pairs have more than 12 months of coverage; they tie up 71.0 million EUR of stock.", "pass"),
    ("In June 2026, 28 item and country pairs have more than 12 months of coverage; they tie up EUR 70,987,983.", "pass"),
    ("In June 2026, several pairs have more than 12 months of coverage; they tie up 71.0 million EUR of stock.", "fail"),
    ("In June 2026, 28 item and country pairs have more than 12 months of coverage, worth 20,000 EUR.", "fail"),
])
def test_v3_dormant_value_count_and_amount(answer, result):
    g = grade.grade_turn(c_turn("S_DORMANT_VALUE", answer))
    assert g["criteria"]["summary"]["result"] == result, g


# ================================================================================================ ROWS_COMMENTED (session 8c-0, step 7b)

STEP6 = [json.loads(x) for x in (ROOT / "eval" / "fixtures" / "session8c0_step6_agent_c.jsonl").read_text().splitlines()]


def test_rows_commented_fires_on_the_step6_dim_mix_answer():
    """Governance flag, outside correctness: C picked the lowest and highest item coverage of France itself."""
    g = grade.grade_turn({**next(t for t in STEP6 if t["question_id"] == "DIM_MIX"), "tool_uses": []})
    assert g["governance"]["ROWS_COMMENTED"]["flag"] is True, g["governance"]
    assert g["verdict"] != "manual"             # the flag never changes the verdict


def test_rows_commented_on_the_step6_t5_answer_that_lists_items():
    g = grade.grade_turn({**next(t for t in STEP6 if t["question_id"] == "T5"), "tool_uses": []})
    assert g["governance"]["ROWS_COMMENTED"]["flag"] is True, g["governance"]


@pytest.mark.parametrize("turn", SESSION7 + SESSION8B + [t for t in STEP6 if t["question_id"] in ("T1", "S_OWN_UNIT")],
                         ids=lambda t: t["question_id"])
def test_rows_commented_silent_when_only_the_asked_figure_is_given(turn):
    g = grade.grade_turn({**turn, "tool_uses": turn.get("tool_uses", [])})
    assert g["governance"]["ROWS_COMMENTED"]["flag"] is False, (turn["answer"], g["governance"])


@pytest.mark.parametrize("qid,answer,flag", [
    ("T1", "Flour and baking in France covers 2.8 months as of June 2026, kg equivalent. The average item covers 6.25 months.", True),
    ("T1", "Flour and baking in France covers 2.8 months as of June 2026, kg equivalent; SKU-H01 alone covers 12.0 months.", True),
    ("S_STOCKOUT_COUNTRY", "From June 2026 in France, kg or L equivalent: SKU-H02 0.5 months, SKU-0039 1.0 months, "
                           "SKU-0031 1.8 months, SKU-0010 2.2 months.", False),
    ("S_STOCKOUT_COUNTRY", "From June 2026 in France: SKU-H02 0.5 months, SKU-0039 1.0, SKU-0031 1.8, SKU-0010 2.2 months; "
                           "on average they cover 1.4 months.", True),
])
def test_rows_commented_synthetic(qid, answer, flag):
    g = grade.grade_turn(c_turn(qid, answer))
    assert g["governance"]["ROWS_COMMENTED"]["flag"] is flag, g["governance"]


# ================================================================================================ rubric 3.1 (session 8c-0, step 8)

STEP7E = [json.loads(x) for x in (ROOT / "eval" / "fixtures" / "session8c0_step7e_agent_c.jsonl").read_text().splitlines()]


def test_v31_naming_the_basis_of_stock_is_correct():
    """Owner, 2026-10-05: "This uses stock in kg or L equivalent" names the basis of the stock, which v3 asks for."""
    g = grade.grade_turn({**next(t for t in STEP7E if t["question_id"] == "S_STOCKOUT_COUNTRY"),
                          "tool_uses": [{"type": "generic", "name": "stock_coverage", "input": {}}]})
    assert g["criteria"]["basis_wording"]["result"] == "pass", g
    assert g["verdict"] == "correct", g


@pytest.mark.parametrize("turn", STEP7E, ids=lambda t: t["question_id"])
def test_v31_step7e_answers_are_correct(turn):
    g = grade.grade_turn({**turn, "tool_uses": [{"type": "generic", "name": "stock_coverage", "input": {}}]})
    assert g["verdict"] == "correct", g


@pytest.mark.parametrize("answer,result", [
    ("As of June 2026 flour and baking in France has a coverage of 2.8 kg.", "fail"),
    ("As of June 2026 flour and baking in France covers 2.8 months; the coverage is in QTY_EQ.", "fail"),
    ("As of June 2026 flour and baking in France covers 2.8 months, with stock and forecast in kg equivalent.", "pass"),
    ("As of June 2026 flour and baking in France covers 2.8 months. This uses stock in kg equivalent.", "pass"),
])
def test_v31_unit_of_the_coverage_itself(answer, result):
    assert grade.grade_turn(c_turn("T1", answer))["criteria"]["basis_wording"]["result"] == result


# ================================================================================================ FRESHNESS_STATED (session 8c-0, step 8, decision 5)

@pytest.mark.parametrize("answer,present,latest", [
    ("Flour and baking in France covers 2.8 months as of June 2026, kg equivalent.\nData freshness: June 2026", True, True),
    ("Flour and baking in France covers 2.8 months as of June 2026, kg equivalent.\n\nData freshness: 2026-06", True, True),
    ("Flour and baking in France covers 2.8 months as of June 2026, kg equivalent.\nData freshness: May 2026", True, False),
    ("Flour and baking in France covers 2.8 months as of June 2026, kg equivalent.", False, False),
])
def test_freshness_stated_is_a_measure(answer, present, latest):
    g = grade.grade_turn(c_turn("T1", answer))
    f = g["governance"]["FRESHNESS_STATED"]
    assert (f["present"], f["latest"]) == (present, latest), f
    assert g["criteria"]["numeric"]["result"] == "pass"          # never part of the verdict


def test_freshness_absent_on_the_recorded_answers():
    for t in SESSION8B + STEP7E:
        assert grade.grade_turn({**t, "tool_uses": []})["governance"]["FRESHNESS_STATED"]["present"] is False
