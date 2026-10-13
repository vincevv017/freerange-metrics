"""
The generated procedure LINKML_METRICS.RAW.STOCK_COVERAGE, called directly (no agent) as the project role with no
secondary role. Skipped unless LINKML_PROCEDURE_LIVE=1 (session 13: a plain `pytest` is the offline suite), and when no
Snowflake connection is available (LINKML_SF_CONNECTION, default "perso").

- heroes: every value of data/traps.yaml, in QTY_EQ and VALUE (heroes have the same value in both, BULK_SCOPE has
  one per unit), with its flag and the warnings the contract raises for it;
- refusals: every refusal of data/traps.yaml (T5, T6, the T7 lifecycle question) in both units, and every refusal
  code reachable on v0 data, with its code;
- totals (T1): one check per hierarchy level; a total row equals a separate call at the total's grain and differs
  from the sum, the mean and the stock-weighted mean of its children;
- invariants as properties on the 220 SKU x country members of LATEST (229 less 9 BULK-only, default scope): coverage >= 0, flags consistent, a
  snapshot-only filter never changes the forecast, more stock never lowers coverage, a series value equals the
  single-month call, the default scope equals the explicit STANDARD filter.

Expected values come from traps.yaml (hand-computed). Where a level has no hand value, the total is compared with a
separate call and, as an equivalence check only, with data/coverage_ref.py (pandas, no SQL).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TRAPS = yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())
TRAP = {t["id"]: t for t in TRAPS["traps"]}
CONTRACT = yaml.safe_load((ROOT / "contract" / "stock_coverage.yaml").read_text())
PROC = os.environ.get("LINKML_PROC", "LINKML_METRICS.RAW.STOCK_COVERAGE")   # SQL Scripting since session 8b; Python: STOCK_COVERAGE_PY
AS_OF = "2026-06-01"
UNITS = ["QTY_EQ", "VALUE"]
TOL = 1e-6
QUESTIONS = yaml.safe_load((ROOT / "generated" / "reference_questions.yaml").read_text())["questions"]
pytestmark = pytest.mark.skipif(os.environ.get("LINKML_PROCEDURE_LIVE") != "1",
                                reason="on the account: set LINKML_PROCEDURE_LIVE=1 to CALL the procedure")


@pytest.fixture(scope="module")
def cur():
    try:
        import snowflake.connector
        con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"))
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"no Snowflake connection: {e}")
    c = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH"):
        c.execute(s)
    yield c
    con.close()


def call(cur, as_of, unit, grain, filters, totals=None, **selection) -> dict:
    """Named arguments, as the agent calls the tool (contract 0.5.0: basis is optional and follows filters)."""
    enc = lambda v: v if v is None or isinstance(v, str) else json.dumps(v)  # noqa: E731
    args = {"AS_OF_MONTHS": enc(as_of), "GRAIN": enc(grain), "FILTERS": enc(filters), "BASIS": unit,
            "TOTALS": enc(totals or [])}
    args.update({k.upper(): (None if v is None else str(v)) for k, v in selection.items()})
    cur.execute(f"CALL {PROC}(" + ", ".join(f"{k} => %({k})s" for k in args) + ")", args)
    res = json.loads(cur.fetchone()[0])
    caller = res["caller"]
    assert caller["current_role"] == "LINKML_METRICS_ROLE"
    assert json.loads(caller["current_secondary_roles"])["roles"] == ""
    assert res["contract"] == {"id": CONTRACT["id"], "version": CONTRACT["version"]}
    return res


def q(tid: str, **extra) -> tuple[list[str], dict]:
    t = TRAP[tid]["query"]
    f = {a: v if isinstance(v, list) else [v] for a, v in t["filters"].items()}
    f.update(extra)
    return list(t["grain"]), f


def one(res: dict, **match) -> dict:
    assert res["status"] == "ok", res.get("refusal")
    rows = [r for r in res["rows"] if r["row_type"] == "DETAIL" and all(r.get(k) == v for k, v in match.items())]
    assert len(rows) == 1, rows
    return rows[0]


def approx(v):
    return pytest.approx(v, abs=TOL)


def codes(res) -> list[str]:
    return [w["code"] for w in res.get("warnings", [])]


# ================================================================================================ heroes

HEROES = [("T1", None), ("T2", None), ("T3", None), ("T4", None), ("T7", None), ("T8", "NO_STOCK"),
          ("NO_DEMAND", "NO_DEMAND"), ("BEYOND_H", "BEYOND_HORIZON"), ("T9", "NO_STOCK")]


@pytest.mark.parametrize("unit", UNITS)
@pytest.mark.parametrize("tid,flag", HEROES)
def test_hero_value(cur, tid, flag, unit):
    t = TRAP[tid]
    res = call(cur, [AS_OF], unit, *q(tid))
    r = one(res)
    if t["expected"] is None:
        assert r["coverage_months"] is None
    else:
        assert r["coverage_months"] == approx(t["expected"])
    assert r["flag"] == flag == t.get("expected_flag", flag)
    assert len(res["rows"]) == 1


def test_t1_children(cur):
    g, f = q("T1")
    res = call(cur, [AS_OF], "QTY_EQ", ["sku_code", "country_code"], f)
    for sku, v in TRAP["T1"]["children"].items():
        assert one(res, sku_code=sku)["coverage_months"] == approx(v)


@pytest.mark.parametrize("unit", UNITS)
def test_t3_related(cur, unit):
    g, f = q("T3")
    rel = TRAP["T3"]["related"]
    assert one(call(cur, [AS_OF], unit, g, {**f, "batch_status": ["QUALITY_HOLD"]}))["coverage_months"] == approx(rel["quality_hold_only"])
    f.pop("batch_status")
    assert one(call(cur, [AS_OF], unit, g, f))["coverage_months"] == approx(rel["all_statuses"])
    by_status = call(cur, [AS_OF], unit, g + ["batch_status"], f)
    assert one(by_status, batch_status="RELEASED")["coverage_months"] == approx(TRAP["T3"]["expected"])
    assert one(by_status, batch_status="QUALITY_HOLD")["coverage_months"] == approx(rel["quality_hold_only"])


def test_t2_warning_scoped_to_the_request(cur):
    """Decision 3: 2 missing months for this member, not the 377 of the table."""
    res = call(cur, [AS_OF], "QTY_EQ", *q("T2"))
    w = [x for x in res["warnings"] if x["code"] == "FORECAST_GAPS_FILLED"]
    assert len(w) == 1 and w[0]["count"] == 2 and w[0]["expectation"] == "QE_FORECAST_DENSE"


def test_t1_answer_carries_no_warning(cur):
    assert call(cur, [AS_OF], "QTY_EQ", *q("T1"))["warnings"] == []


def test_t7_stock_and_duplicate_warning(cur):
    res = call(cur, [AS_OF], "QTY_EQ", *q("T7"))
    assert one(res)["stock"] == approx(TRAP["T7"]["expected_stock_qty_eq"])
    w = [x for x in res["warnings"] if x["code"] == "MASTER_DATA_DUPLICATES"]
    assert len(w) == 1 and w[0]["count"] == 1


def test_t9_stale_stock_is_not_carried(cur):
    """Stock before the analysis month, none at it: 0 with NO_STOCK, never the last known stock over the forecast."""
    r = one(call(cur, [AS_OF], "QTY_EQ", *q("T9")))
    assert r["stock"] == 0 and r["forecast_over_horizon"] > 0
    assert abs(r["coverage_months"] - TRAP["T9"]["wrong"]["last_known_stock_over_forecast"]) > 1e-3
    may = one(call(cur, ["2026-05-01"], "QTY_EQ", *q("T9")))      # the month before: stock 350 is real there
    assert may["stock"] == approx(350) and may["flag"] is None


def test_t8_member_kept(cur):
    r = one(call(cur, [AS_OF], "QTY_EQ", *q("T8")))
    assert r["stock"] == 0 and r["forecast_over_horizon"] > 0


@pytest.mark.parametrize("unit", UNITS)
def test_bulk_scope_default_and_explicit(cur, unit):
    t = TRAP["BULK_SCOPE"]
    res = call(cur, [AS_OF], unit, *q("BULK_SCOPE"))
    assert one(res)["coverage_months"] == approx(t["expected_by_unit"][unit])
    w = [x for x in res["warnings"] if x["code"] == t["expected_warning"]]
    assert len(w) == 1
    assert w[0]["unit"] == {"QTY_EQ": "kg", "VALUE": "EUR"}[unit]          # per unit of the basis (0.5.0)
    if unit == "QTY_EQ":
        assert w[0]["excluded_amount"] == approx(t["expected_excluded_stock_qty_eq"])
        assert w[0]["message"].startswith("51,475.5 kg of BULK stock excluded"), w[0]["message"]
    ex = t["related"]["explicit_filter"]
    res2 = call(cur, [AS_OF], unit, t["query"]["grain"], ex["filters"] | {"family_code": ["HOT_GROUND"]})
    assert one(res2)["coverage_months"] == approx(ex["expected_by_unit"][unit])
    assert t["expected_warning"] not in codes(res2)


def test_t5_quantity_equivalent_offered_instead(cur):
    g, f = q("T5")
    assert one(call(cur, [AS_OF], "QTY_EQ", g, f))["coverage_months"] == approx(TRAP["T5"]["related"]["qty_eq"])


def test_latest_token_resolves_to_as_of(cur):
    res = call(cur, ["LATEST"], "QTY_EQ", *q("T1"))
    assert res["request"]["as_of_months"] == [AS_OF] and res["available_months"]["latest"] == AS_OF
    assert one(res)["coverage_months"] == approx(TRAP["T1"]["expected"])


# ================================================================================================ refusals

def refused(res, code):
    assert res["status"] == "refused", res.get("rows")
    assert res["refusal"]["code"] == code, res["refusal"]
    assert "rows" not in res
    return res["refusal"]["reason"]


@pytest.mark.parametrize("unit", UNITS)
def test_trap_refusals(cur, unit):
    g, f = q("T6")
    refused(call(cur, None, unit, g, f), TRAP["T6"]["expected_refusal"])
    lq = TRAP["T7"]["refusal_questions"][0]
    lf = {a: [v] for a, v in lq["query"]["filters"].items()}
    refused(call(cur, [AS_OF], unit, lq["query"]["grain"], lf), lq["expected_refusal"])
    for tid in ("T5", "DIM_MIX"):
        g5, f5 = q(tid)
        reason = refused(call(cur, [AS_OF], TRAP[tid]["query"]["basis"], g5, f5), TRAP[tid]["expected_refusal"])
        assert reason.endswith("Bases allowed for this request: " + ", ".join(TRAP[tid]["expected_allowed_bases"]) + "."), reason


G1, F1 = ["family_code", "country_code"], {"family_code": ["PANTRY_FLOUR"], "country_code": ["FR"]}
REFUSALS = [
    ("AS_OF_MISSING", "", "QTY_EQ", G1, F1, None),
    ("AS_OF_MISSING", "[]", "QTY_EQ", G1, F1, None),
    ("AS_OF_INVALID", "June 2026", "QTY_EQ", G1, F1, None),
    ("AS_OF_INVALID", '["2026-06-01"', "QTY_EQ", G1, F1, None),
    ("AS_OF_NOT_MONTH_START", ["2026-06-15"], "QTY_EQ", G1, F1, None),
    ("AS_OF_TOO_MANY", [f"{y}-{m:02d}-01" for y in (2024, 2025, 2026) for m in range(1, 13)][:25], "QTY_EQ", G1, F1, None),
    ("AS_OF_NO_SNAPSHOT", ["2026-07-01"], "QTY_EQ", G1, F1, None),
    ("AS_OF_NO_SNAPSHOT", ["2026-05-01", "2026-10-01"], "QTY_EQ", G1, F1, None),
    ("BASIS_NOT_COMPARABLE", [AS_OF], "packs", G1, F1, None),
    ("BASIS_UNKNOWN", [AS_OF], "TONNES", G1, F1, None),
    ("GRAIN_MALFORMED", [AS_OF], "QTY_EQ", '{"family_code": 1}', F1, None),
    ("GRAIN_EMPTY", [AS_OF], "QTY_EQ", [], F1, None),
    ("GRAIN_DUPLICATE", [AS_OF], "QTY_EQ", ["family_code", "family_code"], F1, None),
    ("FILTERS_MALFORMED", [AS_OF], "QTY_EQ", G1, '["FR"]', None),
    ("FILTER_VALUES_INVALID", [AS_OF], "QTY_EQ", G1, {"country_code": []}, None),
    ("ATTRIBUTE_UNKNOWN", [AS_OF], "QTY_EQ", G1, {**F1, "brand": ["X"]}, None),
    ("TOTALS_MALFORMED", [AS_OF], "QTY_EQ", G1, F1, '["country_code"]'),
    ("TOTALS_NOT_SUBSET", [AS_OF], "QTY_EQ", G1, F1, [["region_code"]]),
    ("TOTALS_NOT_SUBSET", [AS_OF], "QTY_EQ", G1, F1, [G1]),
    ("MASTER_DATA_FANOUT", [AS_OF], "QTY_EQ", G1, {"family_code": ["PANTRY_OIL"], "lifecycle_status": ["ACTIVE"]}, None),
]


@pytest.mark.parametrize("code,as_of,unit,grain,filters,totals", REFUSALS, ids=[r[0] for r in REFUSALS])
def test_refusal(cur, code, as_of, unit, grain, filters, totals):
    reason = refused(call(cur, as_of, unit, grain, filters, totals), code)
    assert "{" not in reason, reason      # every placeholder of the contract's template is filled


def test_faulty_attributes_named_in_declaration_order_whatever_the_key_order(cur):
    """Session 8b (owner, 2026-10-04): several faulty attributes are named in the contract's declaration order, never
    in the JSON key order; names the contract does not declare come after, in alphabetical order."""
    for filters in ('{"country_code": [], "family_code": []}', '{"family_code": [], "country_code": []}'):
        reason = refused(call(cur, [AS_OF], "QTY_EQ", G1, filters), "FILTER_VALUES_INVALID")
        assert reason == "filter 'family_code' needs a non-empty list of values.", reason
    for filters in ('{"brand": ["X"], "aisle": ["Y"]}', '{"aisle": ["Y"], "brand": ["X"]}'):
        reason = refused(call(cur, [AS_OF], "QTY_EQ", G1, filters), "ATTRIBUTE_UNKNOWN")
        assert reason.startswith("'aisle' is not a coverage attribute."), reason
    for grain in (["country_code", "family_code", "country_code", "family_code"],
                  ["family_code", "country_code", "family_code", "country_code"]):
        reason = refused(call(cur, [AS_OF], "QTY_EQ", grain, F1), "GRAIN_DUPLICATE")
        assert reason == "grain lists an attribute twice: family_code, country_code.", reason


def test_nested_value_in_a_message_is_compact_json(cur):
    """Session 8b (owner): a nested value in a message is rendered as compact JSON, in both procedures."""
    reason = refused(call(cur, '[["2026-06-01", {"m": 6}]]', "QTY_EQ", G1, F1), "AS_OF_INVALID")
    assert reason == "as_of_months value '[\"2026-06-01\",{\"m\":6}]' is not a date in YYYY-MM-01 form, nor LATEST.", reason


def test_refusal_order_follows_the_contract(cur):
    """Several faults at once: the earliest check_order wins (AS_OF before unit before grain)."""
    refused(call(cur, ["2026-06-15"], "TONNES", [], {"brand": ["X"]}), "AS_OF_NOT_MONTH_START")
    refused(call(cur, [AS_OF], "TONNES", [], {"brand": ["X"]}), "BASIS_UNKNOWN")
    refused(call(cur, [AS_OF], "RAW", [], {"brand": ["X"]}), "GRAIN_EMPTY")    # RAW is the NATIVE basis (0.5.0)
    refused(call(cur, [AS_OF], "QTY_EQ", [], {"brand": ["X"]}), "GRAIN_EMPTY")
    refused(call(cur, [AS_OF], "RAW", G1, F1, coverage_below="0"), "SELECTION_INVALID")   # before the data checks


def test_no_snapshot_refusal_lists_the_available_months(cur):
    reason = refused(call(cur, ["2026-07-01"], "QTY_EQ", G1, F1), "AS_OF_NO_SNAPSHOT")
    assert "2023-07-01" in reason and "LATEST = 2026-06-01" in reason


# ================================================================================================ totals (T1)

def _ref_total(as_of, grain, filters, unit="QTY_EQ"):
    from data.coverage_ref import load, py_coverage
    t = load(ROOT / "data" / "output")
    f = {a: v for a, v in filters.items()}
    f.setdefault("item_type", ["STANDARD"])          # the contract's default scope, on the stock only
    return py_coverage(t, dt.date.fromisoformat(as_of), grain, f, unit)


LEVELS = [   # (name, detail grain, total grain, filters)
    ("sku -> country (T1)", ["sku_code", "country_code"], ["country_code"], {"family_code": ["PANTRY_FLOUR"], "country_code": ["FR"]}),
    ("sku -> family", ["sku_code", "family_code"], ["family_code"], {"family_code": ["PANTRY_OIL"]}),
    ("family -> range", ["family_code", "range_code"], ["range_code"], {"range_code": ["PANTRY"], "country_code": ["FR", "GB"]}),
    ("country -> region", ["country_code", "region_code"], ["region_code"], {"region_code": ["WEST"], "family_code": ["PANTRY_PASTA"]}),
    ("region -> grand total", ["region_code"], [], {"family_code": ["PANTRY_RICE"]}),
]


@pytest.mark.parametrize("name,grain,total,filters", LEVELS, ids=[x[0] for x in LEVELS])
def test_total_is_recomputed_never_summed(cur, name, grain, total, filters):
    res = call(cur, [AS_OF], "QTY_EQ", grain, filters, [total])
    details = [r for r in res["rows"] if r["row_type"] == "DETAIL"]
    totals = [r for r in res["rows"] if r["row_type"] == "TOTAL"]
    sep = call(cur, [AS_OF], "QTY_EQ", total or grain[:1], filters, [[]] if not total else [])
    sep_rows = [r for r in sep["rows"] if (r["row_type"] == "TOTAL") == (not total)]
    assert len(totals) == len(sep_rows) >= 1
    for tr in totals:
        key = {a: tr[a] for a in total}
        sr = next(r for r in sep_rows if all(r[a] == v for a, v in key.items()))
        assert (tr["coverage_months"], tr["stock"], tr["forecast_over_horizon"]) == \
            (approx(sr["coverage_months"]), approx(sr["stock"]), approx(sr["forecast_over_horizon"]))
        kids = [r for r in details if all(r[a] == v for a, v in key.items()) and r["coverage_months"] is not None]
        if len(kids) > 1 and tr["coverage_months"] is not None:
            cov = [k["coverage_months"] for k in kids]
            assert abs(tr["coverage_months"] - sum(cov)) > 1e-3
            assert abs(tr["coverage_months"] - sum(cov) / len(cov)) > 1e-3
            w = sum(k["stock"] for k in kids)
            if w:
                assert abs(tr["coverage_months"] - sum(k["coverage_months"] * k["stock"] for k in kids) / w) > 1e-3
        ref = _ref_total(AS_OF, total or ["region_code"], filters) if total else None
        if ref:   # equivalence with the pandas reference, not a correctness proof
            rv = ref[tuple(tr[a] for a in total)]
            assert (tr["coverage_months"] is None and rv.value is None) or tr["coverage_months"] == approx(rv.value)
    if name.startswith("sku -> country"):
        tr = totals[0]
        assert tr["coverage_months"] == approx(TRAP["T1"]["expected"])
        for w in TRAP["T1"]["wrong"].values():
            assert abs(tr["coverage_months"] - w) > 1e-3


def test_no_total_across_months(cur):
    res = call(cur, ["2026-04-01", "2026-05-01", AS_OF], "QTY_EQ", *q("T1"), totals=[[]])
    months = sorted({r["as_of_month"] for r in res["rows"]})
    assert months == ["2026-04-01", "2026-05-01", AS_OF]
    assert all(r["as_of_month"] is not None for r in res["rows"])
    assert len([r for r in res["rows"] if r["row_type"] == "TOTAL"]) == 3      # one per month, none across


# ================================================================================================ invariants

@pytest.fixture(scope="module")
def members(cur):
    """Every SKU x country member at LATEST, all statuses and released stock only."""
    allm = call(cur, [AS_OF], "QTY_EQ", ["sku_code", "country_code"], {})
    rel = call(cur, [AS_OF], "QTY_EQ", ["sku_code", "country_code"], {"batch_status": ["RELEASED"]})
    key = lambda r: (r["sku_code"], r["country_code"])  # noqa: E731
    return {key(r): r for r in allm["rows"]}, {key(r): r for r in rel["rows"]}


def test_inv_non_negative_and_flags(members):
    allm, _ = members
    ref = _ref_total(AS_OF, ["sku_code", "country_code"], {})
    assert set(allm) == set(ref) and len(allm) == 220     # 229 members, minus 9 BULK-only ones (default scope)
    h = CONTRACT["metrics"][0]["horizon_periods"]
    for k, r in allm.items():
        s, c, v, f = r["stock"], r["forecast_over_horizon"], r["coverage_months"], r["flag"]
        assert v is None or v >= 0, k
        assert (v is None) == (f == "NO_DEMAND"), k
        assert (f == "NO_STOCK") == (s == 0), k
        assert (f == "NO_DEMAND") == (s > 0 and c == 0), k
        assert (f == "BEYOND_HORIZON") == (s > c > 0), k
        if f != "BEYOND_HORIZON" and v is not None:
            assert v <= h, k


def test_inv_snapshot_only_filter_keeps_flow_and_monotone_in_stock(members):
    """A snapshot-only filter never changes the forecast; less stock (released only) never raises coverage."""
    allm, rel = members
    assert set(rel) == set(allm)                  # conformed grain: forecast keeps every member (spine)
    for k, r in rel.items():
        a = allm[k]
        assert r["forecast_over_horizon"] == approx(a["forecast_over_horizon"]), k
        assert r["stock"] <= a["stock"] + TOL, k
        if r["coverage_months"] is not None and a["coverage_months"] is not None:
            assert r["coverage_months"] <= a["coverage_months"] + TOL, k


def test_inv_series_pointwise(cur):
    months = ["2026-04-01", "2026-05-01", AS_OF]
    grain, f = ["family_code", "country_code"], {"range_code": ["PANTRY"]}
    series = call(cur, months, "QTY_EQ", grain, f)
    assert series["request"]["as_of_months"] == months
    for m in months:
        single = {(r["family_code"], r["country_code"]): r for r in call(cur, [m], "QTY_EQ", grain, f)["rows"]}
        part = {(r["family_code"], r["country_code"]): r for r in series["rows"] if r["as_of_month"] == m}
        assert set(part) == set(single), m
        for k, r in part.items():
            assert (r["coverage_months"], r["flag"]) == (approx(single[k]["coverage_months"]) if single[k]["coverage_months"] is not None else None, single[k]["flag"]), (m, k)


def test_inv_t3_series(cur):
    """Probe A's series values for SKU-H04 / IT (April, May, June): 4.98, 7.5, 10.0 (all statuses)."""
    g, f = q("T3")
    f.pop("batch_status")
    res = call(cur, ["2026-04-01", "2026-05-01", AS_OF], "QTY_EQ", g, f)
    got = [r["coverage_months"] for r in res["rows"]]
    assert got[1:] == [approx(7.5), approx(10.0)] and round(got[0], 2) == 4.98


def test_inv_default_scope(cur):
    g, f = q("BULK_SCOPE")
    d = call(cur, [AS_OF], "QTY_EQ", g, f)
    e = call(cur, [AS_OF], "QTY_EQ", g, {**f, "item_type": ["STANDARD"]})
    assert [(r["coverage_months"], r["stock"]) for r in d["rows"]] == [(r["coverage_months"], r["stock"]) for r in e["rows"]]
    assert "DEFAULT_SCOPE_EXCLUDED" in codes(d) and "DEFAULT_SCOPE_EXCLUDED" not in codes(e)


def test_inv_deterministic(cur):
    a = call(cur, [AS_OF], "VALUE", *q("T1"), totals=[[]])
    b = call(cur, [AS_OF], "VALUE", *q("T1"), totals=[[]])
    assert a["rows"] == b["rows"] and a["warnings"] == b["warnings"]


# ================================================================================================ reference questions

def warning_numbers(res) -> dict:
    return {w["code"]: w.get("count", w.get("excluded_amount")) for w in res.get("warnings", [])}


@pytest.mark.parametrize("rq", [q for q in QUESTIONS if q["asked_to_agent_c"] and not q["id"].startswith("S_") and not q.get("held_out")],
                         ids=lambda q: q["id"])
def test_reference_question_expected_answer(cur, rq):
    """The showcase questions of session 8c-0 (S_*) have their own tests below (rows, order, summary, apart)."""
    """generated/reference_questions.yaml: the expected answer of each question, through the procedure."""
    p, e = rq["tool_parameters"], rq["expected"]
    res = call(cur, p["as_of_months"], p["basis"], p["grain"], p["filters"], **p.get("selection", {}))
    if "refusal" in e:
        refused(res, e["refusal"])
        return
    if "rows" in e:          # a drill: every row, never added up
        got = {tuple(r[a] for a in p["grain"]): (r["coverage_months"], r["flag"]) for r in res["rows"]}
        want = {tuple(r[a] for a in p["grain"]): (r["value"], r["flag"]) for r in e["rows"]}
        assert set(got) == set(want)
        for k, (v, f) in want.items():
            assert got[k][1] == f and (got[k][0] is None if v is None else got[k][0] == approx(v)), k
        assert sorted(warning_numbers(res)) == e["warnings_codes"]
        return
    r = one(res)
    assert (r["coverage_months"] is None) if e["value"] is None else (r["coverage_months"] == approx(e["value"]))
    assert r["flag"] == e["flag"]
    got = warning_numbers(res)
    assert set(got) == set(e["warnings"])
    for code, n in e["warnings"].items():
        assert got[code] == approx(n), code


# ================================================================================================ fan-out reason (session 8a)

ITEM_ATTRIBUTES = [a["id"] for a in CONTRACT["attributes"] if a["table"] == "DIM_ITEM"]


def t7_r1():
    rq = next(x for x in QUESTIONS if x["id"] == "T7_R1")
    return rq["tool_parameters"]


def test_t7_r1_fanout_names_only_the_differing_attribute(cur):
    """T7_R1: the duplicated item differs on lifecycle_status only; the reason names it with its two values (session
    8b, decision 3) and no other attribute."""
    p = t7_r1()
    reason = refused(call(cur, p["as_of_months"], p["basis"], p["grain"], p["filters"]), "MASTER_DATA_FANOUT")
    assert reason.startswith("1 item(s) have several rows in DIM_ITEM that differ on lifecycle_status (ACTIVE, "
                             "PHASE_OUT);"), reason
    for a in ITEM_ATTRIBUTES + [a["id"] for a in CONTRACT["attributes"]]:
        if a != "lifecycle_status":
            assert a not in reason, (a, reason)


def generated_quality_sql(p):
    """The quality statement the procedure builds for these parameters: the generated handler and contract, run
    locally (no Snowflake), as the procedure runs them."""
    import importlib
    from compiler import gen_procedure, procedure_handler
    h = importlib.reload(procedure_handler)
    h.CONTRACT = gen_procedure.build(CONTRACT)
    st = {"grain": [a.lower() for a in p["grain"]], "filters": {a.lower(): v for a, v in p["filters"].items()},
          "totals": [], "months": [dt.date.fromisoformat(m) for m in p["as_of_months"]], "basis": p["basis"],
          "selection": {}}
    sql, fanout_attrs = h.quality_sql(st, h.plan(st))
    return h, sql, fanout_attrs


def history_text(cur, query_id: str) -> str:
    """The SQL text of one query of this session, from INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION (the procedure runs
    as caller, so its statements belong to the caller's session)."""
    import time
    for _ in range(20):
        rows = cur.execute(
            "SELECT query_text FROM TABLE(LINKML_METRICS.INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION("
            "SESSION_ID => CURRENT_SESSION()::NUMBER, RESULT_LIMIT => 1000)) WHERE query_id = %s", (query_id,)).fetchall()
        if rows:
            return rows[0][0]
        time.sleep(1)
    raise AssertionError(f"{query_id} not in this session's query history")


def executed_quality_text(cur, p) -> str:
    """The text of the quality statement the deployed procedure ran for these parameters, read back by query id."""
    res = call(cur, p["as_of_months"], p["basis"], p["grain"], p["filters"])
    return history_text(cur, res["lineage"]["query_ids"]["quality"])


def test_fanout_two_differing_attributes(cur):
    """The fan-out SQL the procedure ran, read back by query id and run as is with DIM_ITEM replaced by a TEMPORARY copy
    in which the duplicated item of T7 also differs on family_code: both attributes are named with their values,
    item_type (equal) is not. For the Python procedure the statement is first asserted equal to the locally generated
    one; the SQL Scripting procedure binds one JSON request, rebuilt here from the same parameters."""
    import snowflake.connector
    p = t7_r1()
    h, sql, fanout_attrs = generated_quality_sql(p)
    executed = executed_quality_text(cur, p)
    if not PROC.endswith("_PY"):                  # the SQL Scripting procedure (STOCK_COVERAGE since the swap)
        binds = [json.dumps({"months": p["as_of_months"], "filters": {a.lower(): v for a, v in p["filters"].items()},
                             "scope": h.CONTRACT["default_scope"]["included"]})]
        text = executed
    else:
        assert sql.text() == executed          # the statement the procedure runs, not a rewrite
        text, binds = sql.text(), sql.binds
    real, temp = CONTRACT_TABLE("DIM_ITEM"), "LINKML_METRICS.RAW.DIM_ITEM_FANOUT_TEST"
    assert text.count(real) >= 1
    con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"), paramstyle="qmark")
    try:
        c = con.cursor()
        for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH"):
            c.execute(s)
        c.execute(f"CREATE TEMPORARY TABLE {temp} AS SELECT * FROM {real}")
        dup = c.execute(f"SELECT item_id FROM {temp} GROUP BY item_id HAVING COUNT(*) > 1").fetchall()
        assert len(dup) == 1, dup
        item = dup[0][0]
        before = c.execute(f"SELECT COUNT(DISTINCT lifecycle_status), COUNT(DISTINCT family_code), COUNT(DISTINCT item_type) "
                           f"FROM {temp} WHERE item_id = ?", (item,)).fetchone()
        assert before == (2, 1, 1), before                      # v0: only lifecycle_status differs
        n = c.execute(f"UPDATE {temp} SET family_code = 'PANTRY_FLOUR' WHERE item_id = ? AND lifecycle_status = "
                      f"(SELECT MAX(lifecycle_status) FROM {temp} WHERE item_id = ?)", (item, item)).fetchone()[0]
        assert n == 1
        row = c.execute(text.replace(real, temp), binds).fetchone()
        r = dict(zip([d[0] for d in c.description], row))
    finally:
        con.close()
    if "Q" in r and len(r) == 1:      # the SQL procedure returns one object: Q (the counts), FANOUT_REASON, WARNINGS
        r = json.loads(r["Q"])["Q"]
    assert r["FANOUT"] == 1
    assert {a: r[f"FANOUT__{a.upper()}"] for a in fanout_attrs} == \
        {"family_code": 1, "lifecycle_status": 1, "item_type": 0}
    groups = h.differing_attributes(r, fanout_attrs)
    assert groups == ["family_code (PANTRY_FLOUR, PANTRY_OIL)", "lifecycle_status (ACTIVE, PHASE_OUT)"]
    reason = h.message(h.CONTRACT["refusals"]["MASTER_DATA_FANOUT"], count=r["FANOUT"], attributes=groups)
    assert "differ on family_code (PANTRY_FLOUR, PANTRY_OIL), lifecycle_status (ACTIVE, PHASE_OUT);" in reason
    assert "item_type" not in reason


def test_fanout_values_capped_at_five_per_column():
    """Decision 3 (session 8b): at most 5 values per column, then "and <n> more"; columns in declaration order. Local,
    no Snowflake: the same rendering function the procedure uses."""
    import importlib
    from compiler import gen_procedure, procedure_handler
    h = importlib.reload(procedure_handler)
    h.CONTRACT = gen_procedure.build(CONTRACT)
    row = {"FANOUT__LIFECYCLE_STATUS": 1, "FANOUT_VALUES__LIFECYCLE_STATUS": '["ACTIVE", "PHASE_OUT"]',
           "FANOUT__FAMILY_CODE": 3, "FANOUT_VALUES__FAMILY_CODE": json.dumps([f"F{i}" for i in range(1, 8)]),
           "FANOUT__ITEM_TYPE": 0, "FANOUT_VALUES__ITEM_TYPE": "[]"}
    assert h.differing_attributes(row, ["family_code", "lifecycle_status", "item_type"]) == \
        ["family_code (F1, F2, F3, F4, F5 and 2 more)", "lifecycle_status (ACTIVE, PHASE_OUT)"]


def CONTRACT_TABLE(t: str) -> str:
    return f"LINKML_METRICS.RAW.{t}"


# ================================================================================================ answer shape and lineage (session 8a)

def test_answer_carries_query_ids_not_sql(cur):
    """T1: no SQL text in the answer; the three query ids resolve in this session's query history to statements that
    read the expected tables; valid months as first, last and LATEST."""
    p = next(x for x in QUESTIONS if x["id"] == "T1")["tool_parameters"]
    res = call(cur, p["as_of_months"], p["basis"], p["grain"], p["filters"])
    assert "sql" not in res
    assert res["available_months"] == {"first": "2023-07-01", "last": AS_OF, "latest": AS_OF}
    ids = res["lineage"]["query_ids"]
    assert sorted(ids) == ["context", "coverage", "quality"] and len(set(ids.values())) == 3
    facts = [CONTRACT_TABLE("FCT_STOCK_SNAPSHOT"), CONTRACT_TABLE("FCT_FORECAST")]
    dims = [CONTRACT_TABLE("DIM_ITEM"), CONTRACT_TABLE("DIM_GEO")]       # family_code, item_type; country_code
    expected = {"context": facts + [CONTRACT_TABLE("DIM_CALENDAR")], "quality": facts + dims, "coverage": facts + dims}
    for name, qid in ids.items():
        text = history_text(cur, qid)
        for t in expected[name]:
            assert t in text, (name, qid, t)
    assert "QE_FORECAST_DENSE" in history_text(cur, ids["quality"])
    assert "coverage_months" in history_text(cur, ids["coverage"])


def test_refusal_before_the_data_checks_carries_the_context_query_id_only(cur):
    res = call(cur, ["2026-06-15"], "QTY_EQ", G1, F1)
    assert res["status"] == "refused" and list(res["lineage"]["query_ids"]) == []
    res = call(cur, ["2026-07-01"], "QTY_EQ", G1, F1)
    assert res["status"] == "refused" and list(res["lineage"]["query_ids"]) == ["context"]


# ================================================================================================ basis model (session 8c-0)

SHOW = {s["id"]: s for s in TRAPS["showcase_questions"]}


def sq(sid: str) -> dict:
    """A showcase query as call() keywords: grain, filters (lists), basis and the selection."""
    qy = SHOW[sid]["query"]
    f = {a: v if isinstance(v, list) else [v] for a, v in qy["filters"].items()}
    sel = {k: qy[k] for k in ("coverage_below", "coverage_above", "rank_first") if k in qy}
    return {"unit": qy["basis"], "grain": list(qy["grain"]), "filters": f, **sel}


def detail(res: dict) -> list[dict]:
    assert res["status"] == "ok", res.get("refusal")
    return [r for r in res["rows"] if r["row_type"] == "DETAIL"]


def test_dim_mix_reason_names_the_basis_and_value(cur):
    """Question (b): QTY_EQ adds kg and L in the France row: refused, VALUE allowed; on VALUE the answer to give."""
    g, f = q("DIM_MIX")
    reason = refused(call(cur, [AS_OF], "QTY_EQ", g, f), "BASIS_NOT_COMPARABLE")
    assert reason == ("Coverage is always in months, but on QTY_EQ at least one row or total adds kg and L (items of "
                      "different dimensions), so stock and forecast cannot be summed for this request. Bases allowed "
                      "for this request: VALUE."), reason
    assert one(call(cur, [AS_OF], "VALUE", g, f))["coverage_months"] == approx(TRAP["DIM_MIX"]["related"]["value"])
    refused(call(cur, [AS_OF], None, g, f), "BASIS_NOT_COMPARABLE")          # the default basis is refused too


def test_grouping_by_dimension_keeps_qty_eq_comparable(cur):
    g, f = q("DIM_MIX")
    rows = detail(call(cur, [AS_OF], "QTY_EQ", g + ["dimension"], f))
    assert {(r["dimension"], r["stock_unit"]) for r in rows} == {("MASS", "kg"), ("VOLUME", "L")}


def test_own_unit_of_one_item_equals_qty_eq(cur):
    """Question (a): one item in its own unit (CASE_10): the same months as on QTY_EQ (INV_NATIVE_EQUALS_QTY_EQ)."""
    s = SHOW["S_OWN_UNIT"]
    a = one(call(cur, [AS_OF], **sq("S_OWN_UNIT")))
    b = one(call(cur, [AS_OF], **{**sq("S_OWN_UNIT"), "unit": "QTY_EQ"}))
    assert a["coverage_months"] == approx(s["expected"]) == approx(b["coverage_months"])
    assert (a["stock_unit"], b["stock_unit"], a["stockout_month"]) == (s["expected_stock_unit"], "kg",
                                                                       s["expected_stockout_month"])
    assert a["stock"] * 10 == approx(b["stock"])                   # qty_eq_factor 10


@pytest.mark.parametrize("tid,unit,want", [("T1", "QTY_EQ", "kg"), ("T7", "QTY_EQ", "L"), ("T7", "VALUE", "EUR"),
                                           ("T1", "NATIVE", None)])
def test_stock_unit_of_each_row(cur, tid, unit, want):
    res = call(cur, [AS_OF], unit, *q(tid))
    if want is None:                                   # a family holds several items: its own unit is refused
        assert refused(res, "BASIS_NOT_COMPARABLE").endswith("Bases allowed for this request: QTY_EQ, VALUE.")
    else:
        assert one(res)["stock_unit"] == want


@pytest.mark.parametrize("sku,cc,coverage,month", [
    ("SKU-H02", "FR", 0.5, "2026-07-01"),     # owner's test: 0.5 from June 2026 runs out in July 2026
    ("SKU-H07", "SE", 1.0, "2026-07-01"),     # owner's test: 1.0 from June 2026 runs out in July 2026
    ("SKU-H01", "FR", 12.0, "2027-06-01"),
    ("SKU-H08", "NL", 0.0, "2026-06-01"),     # NO_STOCK: already out at the analysis month
    ("SKU-H10", "PL", 50.0, None),            # BEYOND_HORIZON: no stockout month
    ("SKU-H09", "BE", None, None)])           # NO_DEMAND
def test_stockout_month(cur, sku, cc, coverage, month):
    r = one(call(cur, [AS_OF], "QTY_EQ", ["sku_code", "country_code"], {"sku_code": [sku], "country_code": [cc]}))
    assert (r["coverage_months"] is None) if coverage is None else r["coverage_months"] == approx(coverage)
    assert r["stockout_month"] == month


@pytest.mark.parametrize("sid", ["S_STOCKOUT_COUNTRY", "S_FIRST_WORLD"])
def test_showcase_selection_rows_summary_and_apart(cur, sid):
    """Questions (c) and (d): rows in coverage order, the summary per unit, the members set apart."""
    s = SHOW[sid]
    res = call(cur, [AS_OF], **sq(sid))
    rows = detail(res)
    assert [[r["sku_code"], r["coverage_months"], r["stock_unit"], r["stockout_month"]] for r in rows] == \
        [[k, approx(v), u, m] for k, v, u, m in s["expected_rows"]]
    (m,) = res["selection"]["by_month"]
    assert m["as_of_month"] == AS_OF and m["kept"] == s["expected_summary"]["count"] == len(rows)
    assert [(x["unit"], x["amount"]) for x in m["stock"]] == \
        [(x["unit"], approx(x["amount"])) for x in s["expected_summary"]["stock"]]
    for flag, members in s["expected_apart"].items():
        got = m["set_apart"][flag]
        assert got["count"] == len(members) and [[x["sku_code"]] for x in got["members"]] == members, flag
    assert not any(r["flag"] in ("NO_STOCK", "NO_DEMAND") for r in rows)


def test_showcase_dormant_value_matches_both_references(cur):
    """Question (e): item x country on VALUE above 12 months; every row against the two references (pandas and
    DuckDB, never the procedure), the summary and the apart block against traps.yaml; and the worldwide reading."""
    from data import coverage_ref as ref
    s = SHOW["S_DORMANT_VALUE"]
    res = call(cur, [AS_OF], **sq("S_DORMANT_VALUE"))
    t = ref.load(ROOT / "data" / "output")
    f = {"item_type": ["STANDARD"]}
    kept_py, _ = ref.select(ref.py_rows(t, dt.date(2026, 6, 1), ["sku_code", "country_code"], f, "VALUE"), above=12)
    kept_sql, _ = ref.sql_select(ref.sql_rows(t, dt.date(2026, 6, 1), ["sku_code", "country_code"], f, "VALUE"),
                                 ["sku_code", "country_code"], above=12)
    assert [k for k, _ in kept_py] == [k for k, _ in kept_sql]
    rows = detail(res)
    assert [(r["sku_code"], r["country_code"]) for r in rows] == [k for k, _ in kept_py]
    for r, (_, w) in zip(rows, kept_py):
        assert r["coverage_months"] == approx(w.value) and r["stock"] == approx(w.stock) and r["stock_unit"] == "EUR"
    (m,) = res["selection"]["by_month"]
    assert m["kept"] == s["expected_summary"]["count"] == 28
    assert [(x["unit"], x["amount"]) for x in m["stock"]] == [("EUR", pytest.approx(70987982.9948, abs=1e-3))]
    for flag, members in s["expected_apart"].items():
        assert [[x["sku_code"], x["country_code"]] for x in m["set_apart"][flag]["members"]] == members
    w = s["related"]["worldwide"]
    wres = call(cur, [AS_OF], "VALUE", list(w["query"]["grain"]), {}, coverage_above=12)
    assert [[r["sku_code"], r["coverage_months"], r["stock_unit"], r["stockout_month"]] for r in detail(wres)] == \
        [[k, approx(v), u, mo] for k, v, u, mo in w["expected_rows"]]
    assert wres["selection"]["by_month"][0]["stock"] == [{"unit": "EUR", "amount": approx(20000.0)}]


def same_row(r: dict) -> dict:
    return {k: pytest.approx(v, rel=1e-12) if isinstance(v, float) else v for k, v in r.items()}


def test_selection_is_a_subset_and_leaves_totals_alone(cur):
    """INV_SELECTION_SUBSET: kept rows are rows of the plain call with the same values; total rows unchanged."""
    g, f = ["sku_code", "country_code"], {"country_code": ["FR"]}
    refused(call(cur, [AS_OF], "QTY_EQ", g, f, [["country_code"]]), "BASIS_NOT_COMPARABLE")   # FR total: kg and L
    plain = call(cur, [AS_OF], "VALUE", g, f, [["country_code"]])
    sel = call(cur, [AS_OF], "VALUE", g, f, [["country_code"]], coverage_below=3, rank_first=2)
    by_key = {(r["sku_code"], r["country_code"]): r for r in detail(plain)}
    kept = detail(sel)
    assert 0 < len(kept) <= 2
    for r in kept:
        assert r == same_row(by_key[(r["sku_code"], r["country_code"])])
    # a SUM over many rows can differ in its last bits from one run to the next (step 7c run 2: 77102524.6183 against
    # 77102524.61829999): numbers compared at 1e-12 relative
    assert [r for r in sel["rows"] if r["row_type"] == "TOTAL"] == \
        [same_row(r) for r in plain["rows"] if r["row_type"] == "TOTAL"]
    assert "selection" not in plain


def test_selection_without_total_is_judged_on_the_rows_it_returns(cur):
    """Owner's precision (2026-10-05): a worldwide selection at grain sku_code on QTY_EQ is not refused for a total
    nobody asked for; asking for the grand total on QTY_EQ is refused, since that total adds kg and L."""
    assert len(detail(call(cur, [AS_OF], "QTY_EQ", ["sku_code"], {}, rank_first=10))) == 10
    reason = refused(call(cur, [AS_OF], "QTY_EQ", ["sku_code"], {}, [[]], rank_first=10), "BASIS_NOT_COMPARABLE")
    assert reason.endswith("Bases allowed for this request: VALUE."), reason


@pytest.mark.parametrize("kw,value", [("coverage_below", "0"), ("coverage_below", "-1"), ("coverage_below", "soon"),
                                      ("coverage_above", "0"), ("rank_first", "2.5"), ("rank_first", "0")])
def test_selection_invalid(cur, kw, value):
    reason = refused(call(cur, [AS_OF], "QTY_EQ", ["sku_code"], {}, **{kw: value}), "SELECTION_INVALID")
    assert reason.startswith(kw) and f"'{value}'" in reason, reason


def test_selection_window_must_be_open(cur):
    reason = refused(call(cur, [AS_OF], "QTY_EQ", ["sku_code"], {}, coverage_below=3, coverage_above=5),
                     "SELECTION_INVALID")
    assert reason == "coverage_above must be lower than coverage_below (3); got '5'.", reason
