"""
Session 13 (owner, 2026-10-08): the generated CLOSING_STOCK procedure of configuration C-raw. Closing stock at question
time from the raw snapshot, by the contract's period aggregation (LAST_PERIOD, member set ANY_SNAPSHOT_IN_PERIOD, a gap
in the last month closes at 0), with no densified data.

Offline (always run):
- the heroes (Q2 2026, SNACK_BARS x CH: SKU-H11 0, SKU-H12 450, family 450, detail equal to total) and
  CS_LAST_MONTH_GAP of data/traps.yaml, by both references of data/coverage_ref.py (pandas, DuckDB);
- the two references agree for every member at every grain of a sample of periods, on QTY_EQ and VALUE: the oracle
  the procedure is compared with on the account;
- the generated file: what it reads (the raw snapshot and the dimensions only), its conventions (VARCHAR parameters,
  EXECUTE AS CALLER, static SQL with bound values), its refusal codes (the contract's, in check order), its statements
  and lineage.

On the account (only with LINKML_CLOSING_LIVE=1, so that the offline suite never calls Snowflake): the same heroes,
the refusals and the sample, by CALL as LINKML_METRICS_ROLE with no secondary role.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "compiler"))
from data import coverage_ref as ref  # noqa: E402

CONTRACT = yaml.safe_load((ROOT / "contract" / "stock_coverage.yaml").read_text())
TRAPS = yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())
CS = {x["id"]: x for x in TRAPS["closing_stock"]}
GENERAL = {x["id"]: x for x in TRAPS["general_questions"]}
SQL_PATH = ROOT / "generated" / "closing_stock_procedure.sql"
AS_OF = dt.date(2026, 6, 1)
ATTRS = [a["id"] for a in CONTRACT["attributes"]]
GRAINS = [[a] for a in ATTRS] + [["family_code", "country_code"], ["sku_code", "country_code"],
                                 ["range_code", "batch_status"], ["region_code", "warehouse_type", "item_type"]]
# (label, last month, months back): a quarter, a year, ranges and one month, spread over the data
PERIODS = [("2026-Q2", AS_OF, 2), ("2025-Q3", dt.date(2025, 9, 1), 2), ("2024", dt.date(2024, 12, 1), 11),
           ("2025-11-01/2026-02-01", dt.date(2026, 2, 1), 3), ("2026-06-01", AS_OF, 0)]
COLUMNS = {"QTY_EQ": "stock_qty_eq", "VALUE": "stock_value_eur"}


@pytest.fixture(scope="module")
def tables():
    out = ROOT / "data" / "output"
    if not (out / "FCT_STOCK_SNAPSHOT.parquet").exists():
        pytest.skip("the published dataset is not in data/output/")
    return ref.load(out)


def both(t, grain, filters, last, back, column="stock_qty_eq"):
    a = ref.closing_stock(t, last, grain, filters, [-back, 0], column=column)
    b = ref.sql_closing_stock(t, last, grain, filters, [-back, 0], column=column)
    return a, b


# ------------------------------------------------------------------------------------------------ the heroes, offline

def test_heroes_by_both_references(tables):
    f = {"family_code": "SNACK_BARS", "country_code": "CH"}
    for got in both(tables, ["sku_code", "country_code"], f, AS_OF, 2):
        assert got == {("SKU-H11", "CH"): 0.0, ("SKU-H12", "CH"): 450.0}
    for got in both(tables, ["family_code", "country_code"], f, AS_OF, 2):
        assert got == {("SNACK_BARS", "CH"): CS["CS_FAMILY"]["expected"]} == {("SNACK_BARS", "CH"): 450.0}
    detail = ref.closing_stock(tables, AS_OF, ["sku_code", "country_code"], f, [-2, 0])
    assert sum(detail.values()) == 450.0                       # detail equal to total, both members kept


@pytest.mark.parametrize("cid", sorted(CS))
def test_closing_traps_by_both_references(tables, cid):
    q = CS[cid]["query"]
    for got in both(tables, q["grain"], q["filters"], AS_OF, -q["period_k"][0]):
        assert list(got.values()) == [CS[cid]["expected"]]


# ------------------------------------------------------------------------------------------------ the oracle sample

@pytest.mark.parametrize("label,last,back", PERIODS, ids=[p[0] for p in PERIODS])
@pytest.mark.parametrize("basis", sorted(COLUMNS))
def test_references_agree_every_member_every_grain(tables, label, last, back, basis):
    for grain in GRAINS:
        a, b = both(tables, grain, {}, last, back, COLUMNS[basis])
        assert a.keys() == b.keys() and a, (label, grain)
        assert all(a[k] == pytest.approx(b[k], abs=1e-6) for k in a), (label, grain)


# ------------------------------------------------------------------------------------------------ the generated file

def sql() -> str:
    return SQL_PATH.read_text()


def body() -> str:
    return sql().split("$$", 1)[1].rsplit("$$", 1)[0]


def test_reads_the_raw_snapshot_and_the_dimensions_only():
    names = set(re.findall(r"LINKML_METRICS\.RAW\.([A-Z0-9_]+)", body()))
    assert names == {"FCT_STOCK_SNAPSHOT", "DIM_ITEM", "DIM_GEO", "DIM_BATCH", "DIM_WAREHOUSE"}, names
    for banned in ("GAPFILLED", "B2_", "SPINE", "FCT_FORECAST", "DIM_CALENDAR", "SEMANTIC_VIEW", "EXECUTE IMMEDIATE"):
        assert banned not in body().upper(), banned


def test_conventions():
    s = sql()
    head = s[s.index("CREATE OR REPLACE PROCEDURE"):s.index("$$")]
    assert "LINKML_METRICS.RAW.CLOSING_STOCK(" in head
    args = re.findall(r"^\s+([A-Z_]+) VARCHAR(?: DEFAULT ([^,)\n]+))?", head, flags=re.M)
    assert args == [("PERIODS", ""), ("GRAIN", ""), ("FILTERS", ""), ("BASIS", "'QTY_EQ'"), ("TOTALS", "'[]'")]
    for clause in ("RETURNS VARIANT", "LANGUAGE SQL", "EXECUTE AS CALLER"):
        assert clause in head
    assert "USE SECONDARY ROLES NONE;" in s and "USE ROLE LINKML_METRICS_ROLE;" in s


def test_refusal_codes_are_the_contracts_in_check_order():
    import gen_closing_procedure as g
    order = [r["id"] for r in sorted(CONTRACT["refusal_codes"], key=lambda r: r["check_order"])]
    used = g.codes(CONTRACT)
    assert used == [c for c in order if c in used]
    assert {"HORIZON_NOT_LOADED", "SELECTION_INVALID"}.isdisjoint(used)     # coverage only
    contract_codes = {r["id"] for r in CONTRACT["refusal_codes"]} | {w["id"] for w in CONTRACT["warning_codes"]}
    named = set(re.findall(r"'([A-Z][A-Z_]{5,})'", body())) & (contract_codes | {"HORIZON_NOT_LOADED"})
    assert named <= set(used) | {w["id"] for w in CONTRACT["warning_codes"]}
    for code in used:
        assert f"'{code}'" in body(), code


def test_reworded_templates_are_the_contracts_with_a_closing_stock_wording():
    """A contract template that names coverage or as_of_months is reworded for closing stock; the generator holds the
    contract text it rewords and stops if the contract's wording changed."""
    import gen_closing_procedure as g
    templates = {r["id"]: r["reason_template"] for r in CONTRACT["refusal_codes"]}
    for code, (was, now) in g.REWORDED.items():
        assert templates[code] == was, code
        assert "coverage" not in now.lower() and "as_of_months" not in now, code
    for code in g.codes(CONTRACT):
        if code not in g.REWORDED:
            assert "coverage" not in templates[code].lower() and "as_of_months" not in templates[code], code


def test_three_statements_and_their_lineage():
    b = body()
    assert len(re.findall(r"\bINTO :(par|ctx|cv)\b", b)) == 3
    assert "OBJECT_CONSTRUCT('context', " in b and "'closing', " in b


def test_an_unsupported_period_rule_fails_closed():
    import copy
    import gen_closing_procedure as g
    for path, value in ((("period_aggregation", "method"), "SUM"), (("period_aggregation", "periods"), ["WEEK"]),
                        (("period_aggregation", "missing_value"), "NULL")):
        c = copy.deepcopy(CONTRACT)
        m = next(x for x in c["measures"] if x.get("period_aggregation"))
        m[path[0]][path[1]] = value
        with pytest.raises(ValueError):
            g.render(c)
    c = copy.deepcopy(CONTRACT)
    c["default_scopes"][0].pop("applies_to_metrics")       # a scope on the measure itself is not supported
    with pytest.raises(ValueError):
        g.render(c)


# ------------------------------------------------------------------------------------------------ on the account

live = pytest.mark.skipif(os.environ.get("LINKML_CLOSING_LIVE") != "1", reason="set LINKML_CLOSING_LIVE=1 to CALL")


@pytest.fixture(scope="module")
def cur():
    import snowflake.connector
    con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"))
    c = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH",
              "ALTER SESSION SET USE_CACHED_RESULT = FALSE"):
        c.execute(s)
    yield c
    con.close()


def call(cur, periods, grain, filters, basis="QTY_EQ", totals=None) -> dict:
    enc = lambda v: v if v is None or isinstance(v, str) else json.dumps(v)  # noqa: E731
    args = {"PERIODS": enc(periods), "GRAIN": enc(grain), "FILTERS": enc(filters), "BASIS": basis,
            "TOTALS": enc(totals or [])}
    cur.execute("CALL LINKML_METRICS.RAW.CLOSING_STOCK(" + ", ".join(f"{k} => %({k})s" for k in args) + ")", args)
    return json.loads(cur.fetchone()[0])


def rows(res, grain, row_type="DETAIL") -> dict:
    assert res["status"] == "ok", res
    return {tuple(r[a] for a in grain): float(r["closing_stock"]) for r in res["rows"] if r["row_type"] == row_type}


@live
def test_live_heroes(cur):
    f = {"family_code": ["SNACK_BARS"], "country_code": ["CH"]}
    res = call(cur, ["2026-Q2"], ["sku_code", "country_code"], f, totals=[["country_code"]])
    assert rows(res, ["sku_code", "country_code"]) == {("SKU-H11", "CH"): 0.0, ("SKU-H12", "CH"): 450.0}
    assert rows(res, ["country_code"], "TOTAL") == {("CH",): 450.0}
    fam = call(cur, ["2026-Q2"], ["family_code", "country_code"], f)
    assert rows(fam, ["family_code", "country_code"]) == {("SNACK_BARS", "CH"): 450.0}
    gap = call(cur, ["2026-Q2"], ["sku_code", "country_code"], {"sku_code": ["SKU-H11"], "country_code": ["CH"]})
    assert rows(gap, ["sku_code", "country_code"]) == {("SKU-H11", "CH"): CS["CS_LAST_MONTH_GAP"]["expected"]}
    assert [r["closed_without_snapshot"] for r in gap["rows"]] == [True]


@live
def test_live_g2_counts_no_fanout(cur):
    res = call(cur, ["2026-06-01"], ["country_code"], {}, basis="VALUE")
    want = GENERAL["G2"]["expected_rows"]
    assert rows(res, ["country_code"]) == pytest.approx({(k,): v for k, v in want.items()}, abs=1e-4)


@live
@pytest.mark.parametrize("periods,grain,filters,basis,code", [
    ([], ["sku_code"], {}, "QTY_EQ", "AS_OF_MISSING"),
    (["June 2026"], ["sku_code"], {}, "QTY_EQ", "AS_OF_INVALID"),
    (["2026-06-01/2026-04-01"], ["sku_code"], {}, "QTY_EQ", "AS_OF_INVALID"),
    (["2026-06-15"], ["sku_code"], {}, "QTY_EQ", "AS_OF_NOT_MONTH_START"),
    ([f"{y}-Q{q}" for y in range(2019, 2026) for q in range(1, 5)], ["sku_code"], {}, "QTY_EQ", "AS_OF_TOO_MANY"),
    (["2026-Q3"], ["sku_code"], {}, "QTY_EQ", "AS_OF_NO_SNAPSHOT"),
    (["2026"], ["sku_code"], {}, "QTY_EQ", "AS_OF_NO_SNAPSHOT"),           # partial: July to December not loaded
    (["2023"], ["sku_code"], {}, "QTY_EQ", "AS_OF_NO_SNAPSHOT"),           # partial: January to June not loaded
    (["2026-Q2"], ["sku_code"], {}, "KILOGRAMS PER CASE", "BASIS_UNKNOWN"),
    (["2026-Q2"], [], {}, "QTY_EQ", "GRAIN_EMPTY"),
    (["2026-Q2"], ["brand"], {}, "QTY_EQ", "ATTRIBUTE_UNKNOWN"),
    (["2026-Q2"], ["sku_code", "lifecycle_status"], {"family_code": ["PANTRY_OIL"], "country_code": ["SE"]}, "QTY_EQ",
     "MASTER_DATA_FANOUT"),
    (["2026-Q2"], ["family_code"], {"family_code": ["SNACK_BARS"]}, "NATIVE", "BASIS_NOT_COMPARABLE"),
    (["2026-Q2"], ["country_code"], {}, "QTY_EQ", "BASIS_NOT_COMPARABLE"),
])
def test_live_refusals(cur, periods, grain, filters, basis, code):
    res = call(cur, periods, grain, filters, basis)
    assert res["status"] == "refused" and res["refusal"]["code"] == code, res
    assert "coverage" not in res["refusal"]["reason"].lower()


@live
def test_live_total_is_a_recomputation(cur):
    # VALUE: PANTRY holds kg and L items, so its grand total on QTY_EQ is refused (BASIS_NOT_COMPARABLE, measured)
    res = call(cur, ["2025"], ["family_code", "country_code"], {"range_code": ["PANTRY"]}, basis="VALUE",
               totals=[["family_code"], []])
    coarse = call(cur, ["2025"], ["family_code"], {"range_code": ["PANTRY"]}, basis="VALUE", totals=[[]])
    assert rows(res, ["family_code"], "TOTAL") == rows(coarse, ["family_code"]) | rows(coarse, ["family_code"], "TOTAL")


@live
@pytest.mark.parametrize("basis", sorted(COLUMNS))
@pytest.mark.parametrize("grain", GRAINS, ids=["-".join(g) for g in GRAINS])
def test_live_sample_equals_the_reference(cur, tables, grain, basis):
    """One CALL per grain and basis carrying every sample period (a series, owner, step 3)."""
    res = call(cur, [p[0] for p in PERIODS], grain, {}, basis)
    if res["status"] == "refused":            # one row adds kg and L, or T7 on lifecycle_status: refused, never summed
        assert res["refusal"]["code"] in ("BASIS_NOT_COMPARABLE", "MASTER_DATA_FANOUT"), (grain, res)
        assert basis == "QTY_EQ" or res["refusal"]["code"] == "MASTER_DATA_FANOUT", (grain, res)
        return
    assert res["status"] == "ok", res
    for label, last, back in PERIODS:
        got = {tuple(r[a] for a in grain): float(r["closing_stock"]) for r in res["rows"]
               if r["row_type"] == "DETAIL" and r["period"] == label}
        want = ref.closing_stock(tables, last, grain, {}, [-back, 0], column=COLUMNS[basis])
        assert got == pytest.approx({k if isinstance(k, tuple) else (k,): v for k, v in want.items()}, abs=1e-4), \
            (label, grain, basis)
