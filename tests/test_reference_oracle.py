"""
Oracle independence (session 8, decision 3): no expected value of generated/reference_questions.yaml comes from the
procedure or from any Snowflake object.

Every expected value, flag, warning count or amount, drill row, closing stock and general-question value is recomputed
here from data/output/ in pandas (data/coverage_ref.py for coverage, data/checks/check_dataset.py for warnings and the
general questions), with no Snowflake connection, and compared with the file. The sources that produce the file
(compiler/gen_questions.py, data/checks/check_dataset.py, data/coverage_ref.py) import no Snowflake module, and
data/traps.yaml names no value as read from the procedure.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

from coverage_ref import (allowed_bases, load, month_add, py_coverage, py_rows, select, sql_rows,  # noqa: E402
                          sql_select, stock_unit, stockout_month, stock_view, summary)

_spec = importlib.util.spec_from_file_location("check_dataset", ROOT / "data" / "checks" / "check_dataset.py")
check_dataset = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_dataset)

DATA = ROOT / "data" / "output"
if not (DATA / "manifest.json").exists():         # session 15: a clone of the private repository, and its CI
    pytest.skip("the published dataset is not in data/output/", allow_module_level=True)
QUESTIONS = yaml.safe_load((ROOT / "generated" / "reference_questions.yaml").read_text())["questions"]
CONTRACT = yaml.safe_load((ROOT / "contract" / "stock_coverage.yaml").read_text())
SCOPE = CONTRACT["default_scopes"][0]
AS_OF = dt.date.fromisoformat(json.loads((DATA / "manifest.json").read_text())["as_of"])
TOL = 1e-9


@pytest.fixture(scope="module")
def t():
    return load(DATA)


def scoped(filters: dict) -> dict:
    return filters if SCOPE["attribute"] in filters else {**filters, SCOPE["attribute"]: SCOPE["included_values"]}


def same(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, rel_tol=0, abs_tol=TOL)


def test_sources_import_no_snowflake_module():
    for f in ("compiler/gen_questions.py", "data/checks/check_dataset.py", "data/coverage_ref.py"):
        text = (ROOT / f).read_text()
        assert not re.search(r"^\s*(import|from)\s+snowflake", text, re.M), f


def test_traps_name_no_value_as_read_from_the_procedure():
    text = (ROOT / "data" / "traps.yaml").read_text()
    assert not re.search(r"read (once )?from the procedure", text, re.I)


def test_every_question_has_an_expected_route():
    assert all(q["expected_route"] in ("coverage", "semantic_view", "clarify", "both") for q in QUESTIONS)
    assert {q["id"] for q in QUESTIONS if q["expected_route"] == "semantic_view"} == {
        "CS_LAST_MONTH_GAP", "CS_MIDDLE_MONTH_GAP", "CS_FAMILY", "G1", "G2"}
    assert {q["id"] for q in QUESTIONS if q["expected_route"] == "both"} == {"N1", "N2"}


@pytest.mark.parametrize("q", [q for q in QUESTIONS if q["metric"] == "stock_coverage"], ids=lambda q: q["id"])
def test_coverage_expected_values_from_pandas(t, q):
    p, e = q["tool_parameters"], q["expected"]
    if q["id"].startswith("S_"):
        pytest.skip("showcase question: test_showcase_from_both_references")
    if q.get("held_out"):
        pytest.skip("held-out question: test_held_out_from_both_references")
    if q.get("added_in_stage") == 2:
        pytest.skip("question added in stage 2: its own tests below")
    if "refusal" in e:
        assert e["refusal"] in {r["id"] for r in CONTRACT["refusal_codes"]}
        if "offer_instead" in e:
            r = py_coverage(t, AS_OF, p["grain"], scoped(p["filters"]), e["offer_instead"]["basis"])
            assert len(r) == 1 and same(next(iter(r.values())).value, e["offer_instead"]["value"])
        if "allowed_bases" in e:         # session 8c-0: the bases the refusal names, from both references
            for rows in (py_rows(t, AS_OF, p["grain"], scoped(p["filters"]), p["basis"]),
                         sql_rows(t, AS_OF, p["grain"], scoped(p["filters"]), p["basis"])):
                assert allowed_bases(rows.values()) == e["allowed_bases"] and p["basis"] not in e["allowed_bases"]
        return
    res = py_coverage(t, AS_OF, p["grain"], scoped(p["filters"]), p["basis"])
    if "rows" in e:
        got = {k: (r.value, r.flag) for k, r in res.items()}
        want = {tuple(r[a] for a in p["grain"]): (r["value"], r["flag"]) for r in e["rows"]}
        assert got.keys() == want.keys()
        assert all(same(got[k][0], v) and got[k][1] == f for k, (v, f) in want.items())
        parent_q = next(x for x in QUESTIONS if x["id"] == q["follows"])
        w = check_dataset.pandas_warnings(t, AS_OF, {"grain": p["grain"], "filters": parent_q["tool_parameters"]["filters"]},
                                          SCOPE)
        assert sorted(w) == e["warnings_codes"]
        return
    assert len(res) == 1
    r = next(iter(res.values()))
    assert same(r.value, e["value"]) and r.flag == e["flag"]
    w = check_dataset.pandas_warnings(t, AS_OF, {"grain": p["grain"], "filters": p["filters"]}, SCOPE)
    assert w.keys() == e["warnings"].keys()
    assert all(same(float(w[c]), float(v)) for c, v in e["warnings"].items())


@pytest.mark.parametrize("q", [q for q in QUESTIONS if q["id"].startswith("S_")], ids=lambda q: q["id"])
def test_showcase_from_both_references(t, q):
    """Session 8c-0, questions (a), (c), (d), (e): rows, order, stock unit, stockout month, summary and the members
    set apart, from pandas (py_rows, select) and DuckDB (sql_rows, sql_select), never from the procedure."""
    p, e = q["tool_parameters"], q["expected"]
    names = {"coverage_below": "below", "coverage_above": "above", "rank_first": "rank_first"}
    sel = {names[k]: v for k, v in p.get("selection", {}).items()}
    f = scoped(p["filters"])
    for rows, pick in ((py_rows(t, AS_OF, p["grain"], f, p["basis"]), lambda r: select(r, **sel)),
                       (sql_rows(t, AS_OF, p["grain"], f, p["basis"]), lambda r: sql_select(r, p["grain"], **sel))):
        kept, apart = pick(rows)
        assert allowed_bases(r for _, r in kept).count(p["basis"]) == 1          # the basis is valid where it is asked
        if "value" in e:
            (k, r), = kept
            assert same(r.value, e["value"]) and stock_unit(p["basis"], r) == e["stock_unit"]
            assert stockout_month(AS_OF, r).isoformat() == e["stockout_month"]
            other = py_rows(t, AS_OF, p["grain"], f, "QTY_EQ")[k]
            assert same(other.value, e["related"]["qty_eq"]) and same(other.value, r.value)
        if "rows" in e:
            assert [k[0] for k, _ in kept] == [x["sku_code"] for x in e["rows"]]
            for (k, r), x in zip(kept, e["rows"]):
                assert same(r.value, x["value"]) and stock_unit(p["basis"], r) == x["stock_unit"]
                m = stockout_month(AS_OF, r)
                assert (m.isoformat() if m else None) == x["stockout_month"]
        if "summary" in e:
            s = summary(kept, p["basis"])
            assert s["count"] == e["summary"]["count"]
            assert [(x["unit"], round(x["amount"], 4)) for x in s["stock"]] == \
                [(x["unit"], round(x["amount"], 4)) for x in e["summary"]["stock"]]
            assert {fl: [list(k) for k in ks] for fl, ks in apart.items()} == e["set_apart"]
    if q["id"] == "S_DORMANT_VALUE":           # the share of the dormant stock value, reported to the owner
        allr = py_rows(t, AS_OF, p["grain"], f, "VALUE")
        assert math.isclose(sum(r.stock for r in allr.values()), e["total_stock_value"], abs_tol=1e-3)


@pytest.mark.parametrize("q", [q for q in QUESTIONS if q["metric"] == "closing_stock"], ids=lambda q: q["id"])
def test_closing_stock_from_pandas(t, q):
    """Last month of the period, a member of the period with no row that month closes at 0; no default scope."""
    qq = q["query"]
    months = [month_add(AS_OF, k) for k in range(qq["period_k"][0], qq["period_k"][1] + 1)]
    sv = stock_view(t)
    rows = sv[sv.snapshot_month.isin(months)]
    for a, v in qq["filters"].items():
        rows = rows[rows[a].isin(v if isinstance(v, list) else [v])]
    last = rows[rows.snapshot_month == months[-1]].groupby(qq["grain"]).stock_qty_eq.sum()
    members = rows.groupby(qq["grain"]).size().index
    vals = [float(last.get(m, 0.0)) for m in members]
    assert len(vals) == 1 and same(vals[0], q["expected"]["value"])


def test_g1_from_pandas(t):
    q = next(x for x in QUESTIONS if x["id"] == "G1")
    assert same(check_dataset.g1_forecast(t, AS_OF, q["query"]), q["expected"]["value"])


def test_g2_from_pandas_without_item_join(t):
    q = next(x for x in QUESTIONS if x["id"] == "G2")
    got = check_dataset.g2_closing_value_by_country(t, AS_OF)
    want = {r["country_code"]: r["value"] for r in q["expected"]["rows"]}
    assert got.keys() == want.keys() and all(math.isclose(got[c], v, abs_tol=1e-4) for c, v in want.items())
    fan = check_dataset.g2_closing_value_by_country(t, AS_OF, join_items=True)
    assert {c for c in fan if not math.isclose(fan[c], want[c], abs_tol=1e-4)} == {"SE"}


HELD_OUT = [q for q in QUESTIONS if q.get("held_out")]
SEL = {"coverage_below": "below", "coverage_above": "above", "rank_first": "rank_first"}


def both_references(t, p):
    """The selection of one call, from pandas (py_rows, select) and DuckDB (sql_rows, sql_select); they must agree."""
    sel = {SEL[k]: v for k, v in p.get("selection", {}).items()}
    f = scoped(p["filters"])
    out = []
    for rows, pick in ((py_rows(t, AS_OF, p["grain"], f, p["basis"]), lambda r: select(r, **sel)),
                       (sql_rows(t, AS_OF, p["grain"], f, p["basis"]), lambda r: sql_select(r, p["grain"], **sel))):
        kept, apart = pick(rows)
        out.append((kept, {fl: [list(k) for k in ks] for fl, ks in apart.items()}, summary(kept, p["basis"])))
    (k1, a1, s1), (k2, a2, s2) = out
    assert [k for k, _ in k1] == [k for k, _ in k2] and all(same(x.value, y.value) for (_, x), (_, y) in zip(k1, k2))
    assert a1 == a2 and s1["count"] == s2["count"]
    return out[0]


def test_four_held_out_questions():
    assert [q["id"] for q in HELD_OUT] == ["H_LOCAL_STOCKOUT", "H_LOWEST_COUNTRY", "H_STOCKOUT_2027", "H_STOCKOUT_ES"]
    assert all(q["expected_route"] == "coverage" and q["expected"]["names_basis"] == "QTY_EQ" for q in HELD_OUT)


@pytest.mark.parametrize("q", HELD_OUT, ids=lambda q: q["id"])
def test_held_out_from_both_references(t, q):
    """Session 8c, step 2: rows, order, coverage in months, the unit stock and forecast are measured in, stockout month,
    summary, members set apart, and the intersection of Q1, from both references, never from the procedure."""
    p, e = q["tool_parameters"], q["expected"]
    if "calls" in p:                                   # Q1: two calls, then an intersection of the returned codes
        sets = []
        for c, want in zip(p["calls"], e["calls"]):
            kept, apart, s = both_references(t, c)
            assert s["count"] == want["count"] and apart == want["apart"]
            assert [(x["unit"], round(x["amount"], 4)) for x in s["stock"]] == \
                [(x["unit"], round(x["amount"], 4)) for x in want["stock"]]
            sets.append({k[0] for k, _ in kept})
        assert sorted(sets[0] & sets[1]) == e["items"] and len(e["items"]) == 14
        assert len(sets[0] | sets[1]) == e["wrong_values"]["two_lists_without_intersection"]
        return
    kept, apart, s = both_references(t, p)
    assert [list(k) for k, _ in kept] == [[r[g] for g in p["grain"]] for r in e["rows"]]
    for (_, r), x in zip(kept, e["rows"]):
        assert same(r.value, x["coverage_months"]) and stock_unit(p["basis"], r) == x["measured_in"]
        assert stockout_month(AS_OF, r).isoformat() == x["stockout_month"]
    assert apart == e["set_apart"]
    if "summary" in e:
        assert s["count"] == e["summary"]["count"] == len(e["items"])
        assert [(x["unit"], round(x["amount"], 4)) for x in s["stock"]] == \
            [(x["unit"], round(x["amount"], 4)) for x in e["summary"]["stock"]]
    if q["id"] == "H_STOCKOUT_2027":
        assert "SKU-H06" not in e["items"] and "SKU-H03" in e["items"] and len(e["items"]) == 35
        h = py_rows(t, AS_OF, ["sku_code"], scoped({}), "QTY_EQ")
        assert same(h[("SKU-H06",)].value, 6.0) and stockout_month(AS_OF, h[("SKU-H06",)]).isoformat() == "2026-12-01"
        assert same(h[("SKU-H03",)].value, 7.0) and stockout_month(AS_OF, h[("SKU-H03",)]).isoformat() == "2027-01-01"
        assert {stockout_month(AS_OF, r).year for _, r in kept} == {2027}
    if q["id"] == "H_LOWEST_COUNTRY":
        rows = py_rows(t, AS_OF, p["grain"], scoped(p["filters"]), p["basis"])
        naive = min((r.stock / (r.forecast / 24), k[0]) for k, r in rows.items() if r.forecast and r.stock)
        assert naive[1] == e["wrong_values"]["naive_mean_ratio_lowest"] == "CH" and kept[0][0] == ("PL",)
    if q["id"] == "H_STOCKOUT_ES":
        rows = py_rows(t, AS_OF, p["grain"], scoped(p["filters"]), p["basis"])
        naive = sorted(k[0] for k, r in rows.items() if r.forecast and r.stock and r.stock / (r.forecast / 24) <= 3)
        assert naive == e["wrong_values"]["naive_mean_ratio"] and e["items"] == ["SKU-0001", "SKU-0028", "SKU-0024"]


# Session 9b (owner, 2026-10-07): three questions added in stage 2, asked of C and B2 only. Expected values from the two
# references, never from the procedure (D040): closing stock from pandas (closing_stock) and DuckDB (sql_closing_stock),
# coverage from py_rows + select and sql_rows + sql_select. Every declared wrong value is recomputed and differs from
# the expected one beyond the 0.05 tolerance of the grader, so each trap is detectable.

from coverage_ref import closing_stock, sql_closing_stock  # noqa: E402

ADDED = [q for q in QUESTIONS if q.get("added_in_stage") == 2]
TRAPS = yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())
BY_ID = {q["id"]: q for q in QUESTIONS}
WORDING = {
    "N1": "What was the closing stock of SKU-H11 in Switzerland at the end of Q2 2026, and how many months of stock "
          "coverage does it have as of June 2026?",
    "N2": "For the SNACK_BARS family in Switzerland, what was the closing stock at the end of each month of Q2 2026, "
          "and how many months of coverage does the June 2026 stock give?",       # owner's rewording, 2026-10-07
    "N3": "Which products will run out of stock first in France, as of June 2026?",
}


def test_three_questions_added_in_stage_2_with_the_owners_wording():
    assert [q["id"] for q in ADDED] == ["N1", "N2", "N3"]
    assert {q["id"]: q["question"] for q in ADDED} == WORDING
    assert all(q["source_question"] == q["question"] and not q.get("held_out") and q["asked_to_agent_c"] for q in ADDED)
    assert [q["expected_route"] for q in ADDED] == ["both", "both", "coverage"]
    assert all(q["expected"]["names_as_of"] and q["expected"]["names_basis"] == "QTY_EQ" for q in ADDED)


def months_of(period_k):
    return [month_add(AS_OF, k) for k in range(period_k[0], period_k[1] + 1)]


@pytest.mark.parametrize("q", [q for q in QUESTIONS if q["metric"] in ("closing_stock", "closing_stock_and_coverage")],
                         ids=lambda q: q["id"])
def test_closing_stock_from_both_references(t, q):
    """DEFINITION.md section 7: the last month of the period, 0 for a member with a snapshot earlier in the period and
    none in its last month, every item type. pandas and DuckDB agree, on the three closing-stock questions and on the
    closing-stock half of N1 and N2 (one value per month of Q2 2026 for N2)."""
    qq = q["query"]
    e = q["expected"].get("closing_stock", q["expected"])
    periods = ([(qq["period_k"], e["value"])] if "value" in e else
               [((k, k), r["value"]) for k, r in zip(qq["months_k"], e["rows"])])
    if "rows" in e:
        assert [r["month"] for r in e["rows"]] == [month_add(AS_OF, k).isoformat() for k in qq["months_k"]]
    for period, want in periods:
        for ref in (closing_stock, sql_closing_stock):
            got = ref(t, AS_OF, qq["grain"], qq["filters"], period)
            assert len(got) == 1 and same(next(iter(got.values())), want), (ref.__name__, period)


def test_n1_traps_are_those_of_cs_last_month_gap_and_t9(t):
    e = BY_ID["N1"]["expected"]
    assert e["closing_stock"]["wrong_values"] == BY_ID["CS_LAST_MONTH_GAP"]["expected"]["wrong_values"]
    assert e["coverage"]["wrong_values"] == BY_ID["T9"]["expected"]["wrong_values"]
    assert e["coverage"]["value"] == 0.0 and e["coverage"]["flag"] == "NO_STOCK"
    assert BY_ID["N1"]["query"] == BY_ID["CS_LAST_MONTH_GAP"]["query"]
    assert BY_ID["N1"]["tool_parameters"] == BY_ID["T9"]["tool_parameters"]


def test_n2_wrong_values_are_recomputed_and_detectable(t):
    q = BY_ID["N2"]
    qq, e = q["query"], q["expected"]
    carried = e["closing_stock"]["wrong_values"]["last_known_value_per_sku"]
    for k in qq["months_k"]:
        m = month_add(AS_OF, k).isoformat()
        got = next(iter(closing_stock(t, AS_OF, qq["grain"], qq["filters"], (k, k), last_known=True).values()))
        want = next(r["value"] for r in e["closing_stock"]["rows"] if r["month"] == m)
        assert same(got, carried[m]) if m in carried else same(got, want)        # April: both items have a snapshot
        assert m not in carried or abs(carried[m] - want) > 0.05
    vals = [r["value"] for r in e["closing_stock"]["rows"]]
    over = e["closing_stock"]["added_over_months"]
    assert same(over["sum_over_period"], sum(vals)) and same(over["average_over_period"], sum(vals) / len(vals))
    # The coverage half: per-item children (H11 no stock, H12 4.5), the June stock carried at the last known value.
    p = q["tool_parameters"]
    kids = py_rows(t, AS_OF, ["sku_code"], scoped(p["filters"]), "QTY_EQ")
    child = {k[0]: r.value for k, r in kids.items()}
    assert child == {"SKU-H11": 0.0, "SKU-H12": 4.5}
    w = e["coverage"]["wrong_values"]
    stock = {k[0]: r.stock for k, r in kids.items()}
    june_carried = carried[month_add(AS_OF, 0).isoformat()]
    fam = py_rows(t, AS_OF, p["grain"], scoped(p["filters"]), "QTY_EQ")
    (_, r), = fam.items()
    monthly = r.forecast / 24                                                 # flat 200 a month over the horizon
    from coverage_ref import cascade
    assert w == {"last_known_stock_over_forecast": cascade(june_carried, [monthly] * 24).value} == \
        {"last_known_stock_over_forecast": 4.0}
    # The re-aggregation traps cannot be told apart on N2, so none is declared: the mean of the children equals the
    # expected value, and their sum and stock-weighted mean equal SKU-H12's own coverage, which an answer may cite.
    assert same(sum(child.values()) / 2, e["coverage"]["value"])
    assert same(sum(child.values()), child["SKU-H12"])
    assert same(sum(child[s] * stock[s] for s in child) / sum(stock.values()), child["SKU-H12"])
    assert all(abs(v - e["coverage"]["value"]) > 0.05 for v in w.values())


@pytest.mark.parametrize("qid", ["N1", "N2"])
def test_added_coverage_half_from_both_references(t, qid):
    q = BY_ID[qid]
    p, e = q["tool_parameters"], q["expected"]["coverage"]
    for rows in (py_rows(t, AS_OF, p["grain"], scoped(p["filters"]), p["basis"]),
                 sql_rows(t, AS_OF, p["grain"], scoped(p["filters"]), p["basis"])):
        (_, r), = rows.items()
        assert same(r.value, e["value"]) and r.flag == e["flag"] and stock_unit(p["basis"], r) == "kg"
    w = check_dataset.pandas_warnings(t, AS_OF, {"grain": p["grain"], "filters": p["filters"]}, SCOPE)
    assert w == e["warnings"] == {}


def test_n3_the_ten_lowest_coverages_in_france_from_both_references(t):
    """D051: the 10 lowest coverages above 0 at item grain within France; items already out of stock and items with no
    demand set apart and counted (none in France under the default scope), graded on the exact item set."""
    q = BY_ID["N3"]
    p, e = q["tool_parameters"], q["expected"]
    assert p["grain"] == ["sku_code"] and p["filters"] == {"country_code": ["FR"]} and p["selection"] == {"rank_first": 10}
    kept, apart, s = both_references(t, p)
    assert [k[0] for k, _ in kept] == e["items"] == [r["sku_code"] for r in e["rows"]] and len(e["items"]) == 10
    for (_, r), x in zip(kept, e["rows"]):
        assert same(r.value, x["coverage_months"]) and r.value > 0 and stock_unit(p["basis"], r) == x["measured_in"]
        assert stockout_month(AS_OF, r).isoformat() == x["stockout_month"]
    assert apart == e["set_apart"] == {"NO_STOCK": [], "NO_DEMAND": []}
    assert s["count"] == e["summary"]["count"] == 10
    assert [(x["unit"], round(x["amount"], 4)) for x in s["stock"]] == \
        [(x["unit"], round(x["amount"], 4)) for x in e["summary"]["stock"]]
    rows = py_rows(t, AS_OF, p["grain"], scoped(p["filters"]), p["basis"])
    ranked = sorted((r.value, k) for k, r in rows.items() if r.value and r.flag not in ("NO_STOCK", "NO_DEMAND"))
    assert ranked[9][0] < ranked[10][0]                                       # no tie at the tenth place
    naive = sorted((r.stock / (r.forecast / 24), k[0]) for k, r in rows.items() if r.forecast and r.stock)[:10]
    assert sorted(x for _, x in naive) == sorted(e["wrong_values"]["naive_mean_ratio"]) != sorted(e["items"])
    three, _ = select(rows, below=3)
    assert [k[0] for k, _ in three] == e["wrong_values"]["stockout_within_3_months"]
    noscope = py_rows(t, AS_OF, p["grain"], p["filters"], p["basis"])         # the default scope not applied
    _, apart_all = select(noscope, rank_first=10)
    assert [k[0] for k in apart_all["NO_DEMAND"]] == [e["wrong_values"]["bulk_counted_apart"]]
