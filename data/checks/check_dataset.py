"""
Checks on the PRODUCED dataset (data/output/), without regenerating it.

    python data/checks/check_dataset.py [--out data/output]

Three kinds of assertion, all on numbers:
1. Structure: fact grains unique, keys resolve, and each trap's raw shape is present in the data
   (missing forecast rows for T2, two batch statuses for T3, a forecast row at AS_OF for T4,
   a duplicated item for T7, no stock row for T8...).
2. Expected values: every trap query in traps.yaml returns its hand-computed value, through BOTH
   reference implementations (pandas + cascade, DuckDB set-based SQL), in BOTH unit variants.
3. Detectability: every declared wrong behaviour returns its declared wrong value, which differs from
   the expected one. A trap whose wrong answer equals the right answer tests nothing.
Refusal traps (T5, T6, the T7 lifecycle question) carry a contract refusal code instead of a value; their data
shape and, where one exists, the wrong number are asserted. Values follow the contract's default scope.
4. Closing stock over a period (step 1 of the article): last-month snapshot, gaps close at 0, two implementations.
6. Warnings (session 8): every warning count or amount a trap declares is recomputed in pandas from the dataset
   alone (FORECAST_GAPS_FILLED, DEFAULT_SCOPE_EXCLUDED, MASTER_DATA_DUPLICATES), and a trap that declares none gets 0.
7. General questions G1, G2 (session 8): forecast of a family x country x month, closing stock value by country,
   computed in pandas with no Snowflake object, with their wrong values.
Plus an equivalence sweep (python vs SQL on every SKU x country member at AS_OF), which is reported
separately because agreement between two implementations is not correctness.

Exit code 1 on any failure.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DATA_DIR))
sys.path.insert(0, str(DATA_DIR.parent))

import duckdb  # noqa: E402

from coverage_ref import (allowed_bases, cascade, forecast_view, load, month_add, py_coverage, py_rows,  # noqa: E402
                          select, sql_coverage, sql_rows, sql_select, stock_unit, stockout_month, stock_view, summary)
from generated.schema import GRAINS, HORIZON_MONTHS  # noqa: E402

TOL = 1e-9
failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{('  ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)


def same(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, rel_tol=0, abs_tol=TOL)


def k_of(as_of: dt.date, months) -> list[int]:
    return [(m.year - as_of.year) * 12 + m.month - as_of.month for m in months]


def pandas_warnings(t: dict, as_of: dt.date, query: dict, scope: dict) -> dict:
    """Every warning of a QTY_EQ coverage answer, from the dataset alone (no procedure, no Snowflake object).

    FORECAST_GAPS_FILLED: months of t+1..t+H with no forecast row, over the item x country pairs of the query's
    conformed filters that have a forecast row in that window. DEFAULT_SCOPE_EXCLUDED: stock at AS_OF of the query
    outside the default scope (QTY_EQ), unless the query filters the scope attribute. MASTER_DATA_DUPLICATES: items of
    the query's stock or forecast with several DIM_ITEM rows, when the query uses no attribute on which they differ.
    Codes with a zero count are left out, as the contract raises them only when non-zero."""
    from generated.schema import CONFORMED
    filters = query["filters"]
    vals = {a: (v if isinstance(v, list) else [v]) for a, v in filters.items()}
    out: dict = {}
    f = forecast_view(t)
    f = f.assign(k=k_of(as_of, f.forecast_month))
    f = f[(f.k >= 1) & (f.k <= HORIZON_MONTHS)]
    for a, v in vals.items():
        if a in CONFORMED:
            f = f[f[a].isin(v)]
    per = f.groupby(["item_id", "country_id"]).k.nunique()
    gaps = int((HORIZON_MONTHS - per).sum())
    if gaps:
        out["FORECAST_GAPS_FILLED"] = gaps
    s = stock_view(t)
    s = s[s.snapshot_month == as_of]
    for a, v in vals.items():
        s = s[s[a].isin(v)]
    if scope["attribute"] not in vals:
        excluded = float(s[~s[scope["attribute"]].isin(scope["included_values"])].stock_qty_eq.sum())
        if excluded:
            out["DEFAULT_SCOPE_EXCLUDED"] = excluded
        s = s[s[scope["attribute"]].isin(scope["included_values"])]
    items = t["DIM_ITEM"]
    dup = items[items.duplicated("item_id", keep=False)]
    used = set(query.get("grain", [])) | set(vals)
    differing = {c for c in dup.columns if dup.groupby("item_id")[c].nunique().max() > 1}
    in_scope = set(dup.item_id) & (set(s.item_id) | set(f.item_id))
    if in_scope and not (differing & used):
        out["MASTER_DATA_DUPLICATES"] = len(in_scope)
    return out


def g1_forecast(t: dict, as_of: dt.date, query: dict, column: str = "forecast_qty_eq", k: int | None = None,
                k_range: tuple | None = None) -> float:
    """G1: a forecast column summed over the items (one row per item_id) of the filters, for one month offset."""
    f = forecast_view(t)
    f = f.assign(k=k_of(as_of, f.forecast_month))
    for a, v in query["filters"].items():
        f = f[f[a].isin(v if isinstance(v, list) else [v])]
    lo, hi = k_range or ((query["month_k"],) * 2 if k is None else (k, k))
    return float(f[(f.k >= lo) & (f.k <= hi)][column].sum())


def g2_closing_value_by_country(t: dict, as_of: dt.date, join_items: bool = False, scope: dict | None = None) -> dict:
    """G2: stock_value_eur of FCT_STOCK_SNAPSHOT at AS_OF by its own country_id, every item type and batch status, no
    join to DIM_ITEM. join_items=True is the wrong behaviour (a raw join to DIM_ITEM fans out the duplicated item);
    scope applies the coverage default scope, the other wrong behaviour."""
    s = t["FCT_STOCK_SNAPSHOT"]
    s = s[s.snapshot_month == as_of]
    if join_items or scope:
        items = t["DIM_ITEM"] if join_items else t["DIM_ITEM"].drop_duplicates("item_id")
        s = s.merge(items[["item_id", "item_type"]], on="item_id")
        if scope:
            s = s[s[scope["attribute"]].isin(scope["included_values"])]
    by_id = s.groupby("country_id").stock_value_eur.sum()
    codes = t["DIM_GEO"].set_index("country_id").country_code
    return {codes[i]: round(float(v), 4) for i, v in by_id.items()}


def one(results: dict, label: str):
    """The single member a filtered trap query must return."""
    if len(results) != 1:
        check(f"{label}: exactly one member returned", False, f"got {len(results)}")
        return None
    return next(iter(results.values()))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=DATA_DIR / "output")
    out = p.parse_args().out
    manifest = json.loads((out / "manifest.json").read_text())
    as_of = dt.date.fromisoformat(manifest["as_of"])
    t = load(out)
    traps = yaml.safe_load((DATA_DIR / "traps.yaml").read_text())
    contract = yaml.safe_load((DATA_DIR.parent / "contract" / "stock_coverage.yaml").read_text())
    refusals = {r["id"] for r in contract["refusal_codes"]}
    scope = contract["default_scopes"][0]

    def scoped(filters: dict) -> dict:
        """The contract's default scope, lifted only by an explicit filter on its attribute (decision 5)."""
        return filters if scope["attribute"] in filters else {**filters, scope["attribute"]: scope["included_values"]}
    heroes = {h["sku"]: h for h in traps["hero_items"]}
    item_id = t["DIM_ITEM"].drop_duplicates("sku_code").set_index("sku_code").item_id
    country_id = t["DIM_GEO"].set_index("country_code").country_id
    print(f"dataset AS_OF={as_of} seed={manifest['seed']} schema={manifest['schema_version']}")

    # ------------------------------------------------------------------ 1. structure
    print("\n1. Structure")
    for name, grain in GRAINS.items():
        if name == "DIM_ITEM":   # declared grain, broken on purpose by T7 (QE_ITEM_GRAIN): checked just below
            continue
        df = t[name]
        check(f"{name} unique on {grain}", not df.duplicated(list(grain)).any(), f"{len(df)} rows")
    items = t["DIM_ITEM"]
    dup = items[items.duplicated("item_id", keep=False)]
    check("DIM_ITEM: exactly one duplicated item_id (T7), and it is SKU-H06",
          dup.item_id.nunique() == 1 and set(dup.sku_code) == {"SKU-H06"},
          f"duplicated skus={sorted(set(dup.sku_code))}")
    check("T7 duplicate differs only by lifecycle_status",
          dup.drop(columns="lifecycle_status").drop_duplicates().shape[0] == 1
          and set(dup.lifecycle_status) == {"ACTIVE", "PHASE_OUT"})
    for fact, keys in (("FCT_STOCK_SNAPSHOT", ("item_id", "country_id", "batch_id", "warehouse_id")),
                       ("FCT_FORECAST", ("item_id", "country_id"))):
        for k in keys:
            dim = {"item_id": "DIM_ITEM", "country_id": "DIM_GEO", "batch_id": "DIM_BATCH",
                   "warehouse_id": "DIM_WAREHOUSE"}[k]
            check(f"{fact}.{k} resolves in {dim}", t[fact][k].isin(t[dim][k]).all())
    wh = t["FCT_STOCK_SNAPSHOT"].merge(t["DIM_WAREHOUSE"], on="warehouse_id", suffixes=("", "_wh"))
    check("stock country_id = warehouse country_id", (wh.country_id == wh.country_id_wh).all())
    check("no negative quantity", (t["FCT_STOCK_SNAPSHOT"].stock_qty_eq >= 0).all()
          and (t["FCT_FORECAST"].forecast_qty_eq >= 0).all())

    fc = t["FCT_FORECAST"]
    def fc_months(sku, cc):
        f = fc[(fc.item_id == item_id[sku]) & (fc.country_id == country_id[cc])]
        return {(m.year - as_of.year) * 12 + m.month - as_of.month for m in f.forecast_month}
    st = t["FCT_STOCK_SNAPSHOT"]
    def stock_rows(sku, cc):
        return st[(st.item_id == item_id[sku]) & (st.country_id == country_id[cc]) & (st.snapshot_month == as_of)]

    k_h03 = fc_months("SKU-H03", "DE")
    check("T2: SKU-H03/DE forecast rows absent (not zero) for k = 2, 3", not ({2, 3} & k_h03) and {1, 4} <= k_h03)
    combos = fc.groupby(["item_id", "country_id"]).forecast_month.nunique()
    span = fc.forecast_month.nunique()
    check("T2 in the background: some combos have missing forecast months", int((combos < span).sum()) > 5,
          f"{int((combos < span).sum())} of {len(combos)} combos")
    h04 = stock_rows("SKU-H04", "IT").merge(t["DIM_BATCH"], on="batch_id")
    check("T3: SKU-H04/IT stock at AS_OF in RELEASED and QUALITY_HOLD lots",
          h04.groupby("batch_status").stock_qty_eq.sum().to_dict() == {"QUALITY_HOLD": 400.0, "RELEASED": 600.0})
    check("T3: forecast carries no batch attribute", "batch_status" not in fc.columns and "batch_id" not in fc.columns)
    check("T4: SKU-H05/ES has a forecast row AT the analysis month (k = 0)", 0 in fc_months("SKU-H05", "ES"))
    check("T8: SKU-H08/NL has forecast and no stock row at AS_OF",
          len(stock_rows("SKU-H08", "NL")) == 0 and 1 in fc_months("SKU-H08", "NL"))
    check("NO_DEMAND: SKU-H09/BE has stock and no forecast row at all",
          len(stock_rows("SKU-H09", "BE")) > 0 and not fc_months("SKU-H09", "BE"))
    check("BEYOND_H: SKU-H10/PL has forecast beyond k = 24", max(fc_months("SKU-H10", "PL")) >= 36)

    # ------------------------------------------------------------------ 2 + 3. expected and wrong values
    print("\n2-3. Expected values (both implementations, both variants) and detectability")
    for trap in traps["traps"]:
        q = trap["query"]
        grain, filters = q["grain"], q["filters"]
        tid = trap["id"]
        wrong = trap.get("wrong", {})
        if "expected_refusal" in trap:
            check(f"{tid}: refusal trap, expected refusal {trap['expected_refusal']} is a contract code, no value",
                  trap["expected_refusal"] in refusals and "expected" not in trap)
        else:
            exp = trap["expected"]
            if "expected_by_unit" in trap:
                check(f"{tid}: expected = expected_by_unit QTY_EQ", same(exp, trap["expected_by_unit"]["QTY_EQ"]))
            for variant in ("QTY_EQ", "VALUE"):
                e = trap.get("expected_by_unit", {}).get(variant, exp)
                rp = one(py_coverage(t, as_of, grain, scoped(filters), variant), f"{tid} py {variant}")
                rs = one(sql_coverage(t, as_of, grain, scoped(filters), variant), f"{tid} sql {variant}")
                if rp is None or rs is None:
                    continue
                check(f"{tid} {variant}: python = {e}", same(rp.value, e), f"got {rp.value}")
                check(f"{tid} {variant}: SQL    = {e}", same(rs.value, e), f"got {rs.value}")
                if "expected_flag" in trap:
                    check(f"{tid} {variant}: flag {trap['expected_flag']}",
                          rp.flag == trap["expected_flag"] == rs.flag, f"py={rp.flag} sql={rs.flag}")
            if tid != "BULK_SCOPE":
                r = one(py_coverage(t, as_of, grain, filters), f"{tid} unscoped")
                check(f"{tid}: default scope changes nothing (no BULK stock in scope)", same(r.value, exp),
                      f"got {r.value}")

        if tid == "T1":
            kids = py_coverage(t, as_of, ["sku_code", "country_code"], filters)
            vals = {k[0]: r.value for k, r in kids.items()}
            check("T1 children coverages", all(same(vals[s], v) for s, v in trap["children"].items()), str(vals))
            st_kids = stock_rows("SKU-H01", "FR").stock_qty_eq.sum(), stock_rows("SKU-H02", "FR").stock_qty_eq.sum()
            v = list(trap["children"].values())
            got = {"sum_of_children": sum(v), "average_of_children": sum(v) / len(v),
                   "stock_weighted_average_of_children": (v[0] * st_kids[0] + v[1] * st_kids[1]) / sum(st_kids)}
            for name, val in wrong.items():
                check(f"T1 wrong {name} = {val} != {exp}", same(got[name], val) and not same(val, exp), f"got {got[name]}")
        elif tid == "T2":
            r = one(py_coverage(t, as_of, grain, filters, dense=False), "T2 row-based")
            check(f"T2 wrong row_based_window = {wrong['row_based_window']}",
                  r is not None and same(r.value, wrong["row_based_window"]), f"got {r and r.value}")
        elif tid == "T3":
            for name, f2 in (("all_statuses", {k: v for k, v in filters.items() if k != "batch_status"}),
                             ("quality_hold_only", {**filters, "batch_status": "QUALITY_HOLD"})):
                r = one(py_coverage(t, as_of, grain, f2), f"T3 {name}")
                check(f"T3 related {name} = {trap['related'][name]}", same(r.value, trap["related"][name]),
                      f"got {r.value}")
            r = one(py_coverage(t, as_of, grain, filters, push_filters_to_forecast=True), "T3 pushed")
            check("T3 wrong filter_pushed_to_forecast = null (NO_DEMAND)", r.value is None and r.flag == "NO_DEMAND",
                  f"got {r.value} {r.flag}")
        elif tid == "T4":
            r = one(py_coverage(t, as_of, grain, filters, forecast_time_filter=True), "T4 time filter")
            check("T4 wrong filter_pushed_to_forecast = null", r.value is None, f"got {r.value} {r.flag}")
            r = one(py_coverage(t, as_of, grain, filters, window_start_k=0), "T4 window at t")
            check(f"T4 wrong window_starts_at_as_of = {wrong['window_starts_at_as_of']:.4f}",
                  same(r.value, wrong["window_starts_at_as_of"]), f"got {r.value}")
        elif tid == "T7":
            r = one(py_coverage(t, as_of, grain, filters, dedupe_items=False), "T7 naive")
            check(f"T7 wrong naive_join_on_duplicated_item = {wrong['naive_join_on_duplicated_item']}",
                  same(r.value, wrong["naive_join_on_duplicated_item"]), f"got {r.value}")
            s_ok = stock_rows("SKU-H06", "SE").stock_qty_eq.sum() + stock_rows("SKU-H07", "SE").stock_qty_eq.sum()
            check(f"T7 family stock = {trap['expected_stock_qty_eq']} (fanned-out would be "
                  f"{wrong['naive_join_stock_qty_eq']})", same(float(s_ok), trap["expected_stock_qty_eq"]))
        elif tid == "T8":
            r = sql_coverage(t, as_of, grain, filters, spine=False)
            check("T8 wrong: stock-driven SQL (section 5 without its member spine) loses the member", len(r) == 0,
                  f"got {len(r)} rows")
        elif tid == "T9":
            sku, cc = filters["sku_code"], filters["country_code"]
            past = st[(st.item_id == item_id[sku]) & (st.country_id == country_id[cc]) & (st.snapshot_month < as_of)]
            last = past[past.snapshot_month == past.snapshot_month.max()].stock_qty_eq.sum()
            fc_k = fc[(fc.item_id == item_id[sku]) & (fc.country_id == country_id[cc])]
            by_k = {(m.year - as_of.year) * 12 + m.month - as_of.month: v
                    for m, v in zip(fc_k.forecast_month, fc_k.forecast_qty_eq)}
            r = cascade(float(last), [float(by_k.get(k, 0.0)) for k in range(1, HORIZON_MONTHS + 1)])
            check(f"T9: no stock row at AS_OF, a stock row before it (last known {last:g})",
                  len(stock_rows(sku, cc)) == 0 and last > 0)
            check(f"T9 wrong last_known_stock_over_forecast = {wrong['last_known_stock_over_forecast']}",
                  same(r.value, wrong["last_known_stock_over_forecast"]) and not same(r.value, exp), f"got {r.value}")
        elif tid == "BEYOND_H":
            r = one(py_coverage(t, as_of, grain, filters, avg_full_range=True), "BEYOND full range")
            check(f"BEYOND_H wrong average_over_full_forecast_range = "
                  f"{wrong['average_over_full_forecast_range']:.4f}",
                  same(r.value, wrong["average_over_full_forecast_range"]), f"got {r.value}")

        elif tid == "DIM_MIX":
            # session 8c-0: kg and L in one row; QTY_EQ refused (VALUE allowed), VALUE the answer to give
            basis = q["basis"]
            for name, rows in (("python", py_rows(t, as_of, grain, scoped(filters), basis)),
                               ("SQL", sql_rows(t, as_of, grain, scoped(filters), basis))):
                (r,) = rows.values()
                check(f"DIM_MIX {name}: the row holds {r.n_dims} dimensions, allowed bases {trap['expected_allowed_bases']}",
                      r.n_dims == 2 and allowed_bases([r]) == trap["expected_allowed_bases"], f"got {allowed_bases([r])}")
            rp = one(py_coverage(t, as_of, grain, scoped(filters), "VALUE"), "DIM_MIX value py")
            rs = one(sql_coverage(t, as_of, grain, scoped(filters), "VALUE"), "DIM_MIX value sql")
            check(f"DIM_MIX related value = {trap['related']['value']:.4f} (python and SQL)",
                  same(rp.value, trap["related"]["value"]) and same(rs.value, trap["related"]["value"]))
            r = one(py_coverage(t, as_of, grain, scoped(filters), basis), "DIM_MIX kg and L")
            check(f"DIM_MIX wrong kg_and_l_added = {wrong['kg_and_l_added']:.4f} != value",
                  same(r.value, wrong["kg_and_l_added"]) and not same(r.value, trap["related"]["value"]), f"got {r.value}")
        elif tid == "T5":
            unit = q["basis"]
            check(f"T5: basis {unit} is the item's own unit (valid for one item per row only)",
                  next(b for b in contract["measure_bases"] if b["id"] == unit)["valid_when"] == "ONE_ITEM_PER_ROW")
            for name, rows in (("python", py_rows(t, as_of, grain, scoped(filters), unit)),
                               ("SQL", sql_rows(t, as_of, grain, scoped(filters), unit))):
                check(f"T5 {name}: allowed bases {trap['expected_allowed_bases']}",
                      allowed_bases(rows.values()) == trap["expected_allowed_bases"], f"got {allowed_bases(rows.values())}")
            sv = stock_view(t)
            sv = sv[sv.snapshot_month == as_of]
            for a, v in filters.items():
                sv = sv[sv[a] == v]
            check("T5: the member holds several pack sizes at AS_OF", sv.raw_unit.nunique() >= 2,
                  f"units={sorted(sv.raw_unit.unique())}")
            rp = one(py_coverage(t, as_of, grain, scoped(filters)), "T5 qty_eq py")
            rs = one(sql_coverage(t, as_of, grain, scoped(filters)), "T5 qty_eq sql")
            check(f"T5 related qty_eq = {trap['related']['qty_eq']:.4f} (python and SQL)",
                  same(rp.value, trap["related"]["qty_eq"]) and same(rs.value, trap["related"]["qty_eq"]),
                  f"got {rp.value} / {rs.value}")
            r = one(py_coverage(t, as_of, grain, scoped(filters), unit, raw_units=True), "T5 raw")
            check(f"T5 wrong raw_units_summed = {wrong['raw_units_summed']:.4f} != qty_eq",
                  same(r.value, wrong["raw_units_summed"]) and not same(r.value, trap["related"]["qty_eq"]),
                  f"got {r.value}")
        elif tid == "T6":
            check("T6: no analysis month in the query", q.get("as_of_months", "absent") is None)
            sv = stock_view(t)
            for a, v in filters.items():
                sv = sv[sv[a] == v]
            year = sv[[m.year == as_of.year and m <= as_of for m in sv.snapshot_month]]
            by_month = year.groupby("snapshot_month").stock_qty_eq.sum()
            check(f"T6: the member has {as_of.month} snapshots in {as_of.year}, with different levels",
                  len(by_month) == as_of.month and by_month.nunique() > 1, f"{len(by_month)} months, "
                  f"{by_month.nunique()} distinct levels")
        elif tid == "BULK_SCOPE":
            sv = stock_view(t)
            sv = sv[sv.snapshot_month == as_of]
            for a, v in filters.items():
                sv = sv[sv[a] == v]
            excluded = float(sv[~sv[scope["attribute"]].isin(scope["included_values"])].stock_qty_eq.sum())
            check(f"BULK_SCOPE: excluded stock = {trap['expected_excluded_stock_qty_eq']} > 0, so "
                  f"{trap['expected_warning']} is raised",
                  same(excluded, trap["expected_excluded_stock_qty_eq"]) and excluded > 0, f"got {excluded}")
            ex = trap["related"]["explicit_filter"]
            for variant, e in ex["expected_by_unit"].items():
                rp = one(py_coverage(t, as_of, grain, scoped(ex["filters"]), variant), "BULK explicit py")
                rs = one(sql_coverage(t, as_of, grain, scoped(ex["filters"]), variant), "BULK explicit sql")
                check(f"BULK_SCOPE explicit item_type filter {variant}: python = SQL = {e:.4f}",
                      same(rp.value, e) and same(rs.value, e), f"got {rp.value} / {rs.value}")
            r = one(py_coverage(t, as_of, grain, filters), "BULK unscoped")
            check(f"BULK_SCOPE wrong bulk_counted_by_default = {wrong['bulk_counted_by_default']:.4f} != expected",
                  same(r.value, wrong["bulk_counted_by_default"]) and not same(r.value, trap["expected"]),
                  f"got {r.value}")
            check("BULK_SCOPE: decision 6 numbers, 8.7 by default and 17.4 with the explicit filter (QTY_EQ)",
                  round(trap["expected"], 1) == 8.7 and round(ex["expected_by_unit"]["QTY_EQ"], 1) == 17.4)

        for rq in trap.get("refusal_questions", []):
            rg, rf = rq["query"]["grain"], rq["query"]["filters"]
            dup_items = t["DIM_ITEM"][t["DIM_ITEM"].duplicated("item_id", keep=False)]
            conflicting = {c for c in dup_items.columns if dup_items.groupby("item_id")[c].nunique().max() > 1}
            check(f"{tid} refusal question: {rq['expected_refusal']} is a contract code, and the query uses the "
                  f"conflicting column(s) {sorted(conflicting)}",
                  rq["expected_refusal"] in refusals and bool(conflicting & (set(rg) | set(rf))))
            rw = rq["wrong"]
            naive = py_coverage(t, as_of, rg, scoped(rf), dedupe_items=False)
            got = {k[-1]: r.value for k, r in naive.items()}
            check(f"{tid} refusal question wrong naive_join_rows = {rw['naive_join_rows']}",
                  got.keys() == rw["naive_join_rows"].keys()
                  and all(same(got[k], v) for k, v in rw["naive_join_rows"].items()), str(got))
            sv = stock_view(t, dedupe_items=False)
            sv = sv[sv.snapshot_month == as_of]
            for a, v in rf.items():
                sv = sv[sv[a] == v]
            check(f"{tid} refusal question wrong naive_join_stock_qty_eq = {rw['naive_join_stock_qty_eq']}",
                  same(float(sv.stock_qty_eq.sum()), rw["naive_join_stock_qty_eq"]), f"got {sv.stock_qty_eq.sum()}")
            first = {k[-1]: r.value for k, r in py_coverage(t, as_of, rg, scoped(rf)).items()}
            check(f"{tid} refusal question wrong first_row_wins = {rw['first_row_wins']}",
                  first.keys() == rw["first_row_wins"].keys()
                  and all(same(first[k], v) for k, v in rw["first_row_wins"].items()), str(first))

    # ------------------------------------------------------------------ closing stock
    print("\n4. Closing stock over a period (step 1): python and SQL, expected and wrong values")
    sv_all = stock_view(t)
    for cs in traps["closing_stock"]:
        q, cid, wrong = cs["query"], cs["id"], cs["wrong"]
        grain, filters = q["grain"], q["filters"]     # no default scope: a coverage rule only (contract 0.4.1)
        months = [month_add(as_of, k) for k in range(q["period_k"][0], q["period_k"][1] + 1)]
        rows = sv_all[sv_all.snapshot_month.isin(months)]
        for a, v in filters.items():
            rows = rows[rows[a].isin(v if isinstance(v, list) else [v])]
        # python: members = any snapshot in the period; value = last-month snapshot, absent = 0
        last = rows[rows.snapshot_month == months[-1]].groupby(grain).stock_qty_eq.sum()
        py = {m: float(last.get(m, 0.0)) for m in rows.groupby(grain).size().index}
        # SQL: member spine over the period, LEFT JOIN the last month
        con = duckdb.connect()
        con.register("p", rows)
        g = ", ".join(grain)
        sql = (f"WITH m AS (SELECT DISTINCT {g} FROM p), "
               f"l AS (SELECT {g}, SUM(stock_qty_eq) AS q FROM p WHERE snapshot_month = DATE '{months[-1]}' GROUP BY ALL) "
               f"SELECT {g}, COALESCE(l.q, 0) FROM m LEFT JOIN l USING ({g})")
        sq = {tuple(r[:-1]) if len(grain) > 1 else r[0]: float(r[-1]) for r in con.sql(sql).fetchall()}
        check(f"{cid}: one member, python = SQL = {cs['expected']}",
              len(py) == len(sq) == 1 and same(next(iter(py.values())), cs["expected"])
              and same(next(iter(sq.values())), cs["expected"]), f"py={py} sql={sq}")
        total = float(rows.stock_qty_eq.sum())
        per_month = rows.groupby(["sku_code", "snapshot_month"], as_index=False).stock_qty_eq.sum()
        latest = per_month.sort_values("snapshot_month").groupby("sku_code").tail(1)   # carried forward per SKU
        got = {"sum_over_period": total, "average_over_period": total / len(months),
               "last_known_value": float(latest.stock_qty_eq.sum()),
               "last_known_value_per_sku": float(latest.stock_qty_eq.sum())}
        for name, val in wrong.items():
            check(f"{cid} wrong {name} = {val:g} != {cs['expected']}",
                  same(got[name], val) and not same(val, cs["expected"]), f"got {got[name]}")

    # ------------------------------------------------------------------ equivalence sweep
    print("\n5. Equivalence sweep: python vs SQL, every SKU x country member at AS_OF, both variants")
    for variant in ("QTY_EQ", "VALUE"):
        a = py_coverage(t, as_of, ["sku_code", "country_code"], {}, variant)
        b = sql_coverage(t, as_of, ["sku_code", "country_code"], {}, variant)
        diff = [k for k in a.keys() | b.keys()
                if k not in a or k not in b or not math.isclose(a[k].value or 0, b[k].value or 0, abs_tol=1e-6)
                or (a[k].value is None) != (b[k].value is None) or a[k].flag != b[k].flag]
        flags = {}
        for r in a.values():
            flags[r.flag] = flags.get(r.flag, 0) + 1
        check(f"{variant}: {len(a)} members, python = SQL", not diff, f"diffs={diff[:3]} flags={flags}")
        check(f"{variant}: coverage >= 0 everywhere", all(r.value is None or r.value >= 0 for r in a.values()))

    # ------------------------------------------------------------------ 6. warnings from the dataset alone
    print("\n6. Warnings recomputed in pandas (no procedure): every declared count or amount, and none where none is declared")
    for trap in traps["traps"]:
        if "expected_refusal" in trap:
            continue
        got = pandas_warnings(t, as_of, trap["query"], scope)
        want = trap.get("expected_warnings", {})
        check(f"{trap['id']}: warnings {want or 'none'}",
              got.keys() == want.keys() and all(same(float(got[c]), float(v)) for c, v in want.items()), f"got {got}")

    # ------------------------------------------------------------------ 6b. showcase questions (session 8c-0)
    print("\n6b. Showcase questions (a), (c), (d), (e): both references, rows, order, summary, members set apart")
    names = {"coverage_below": "below", "coverage_above": "above", "rank_first": "rank_first"}
    for s in traps.get("showcase_questions", []):
        qy = s["query"]
        f = scoped({a: v if isinstance(v, list) else [v] for a, v in qy["filters"].items()})
        sel = {names[k]: qy[k] for k in names if k in qy}
        kp, ap = select(py_rows(t, as_of, qy["grain"], f, qy["basis"]), **sel)
        ks, as_ = sql_select(sql_rows(t, as_of, qy["grain"], f, qy["basis"]), qy["grain"], **sel)
        check(f"{s['id']}: python = SQL (rows, order, set apart)",
              [k for k, _ in kp] == [k for k, _ in ks] and ap == as_ and all(same(a.value, b.value) for (_, a), (_, b) in zip(kp, ks)))
        if "expected_rows" in s:
            check(f"{s['id']}: rows as frozen", [[k[0], round(r.value, 12), stock_unit(qy['basis'], r),
                                                  (stockout_month(as_of, r) or dt.date.min).isoformat()] for k, r in kp]
                  == [[k, round(v, 12), u, m or dt.date.min.isoformat()] for k, v, u, m in s["expected_rows"]])
        if "expected_summary" in s:
            sm = summary(kp, qy["basis"])
            check(f"{s['id']}: summary {s['expected_summary']}", sm["count"] == s["expected_summary"]["count"] and
                  [(x["unit"], round(x["amount"], 4)) for x in sm["stock"]] ==
                  [(x["unit"], round(x["amount"], 4)) for x in s["expected_summary"]["stock"]], f"got {sm}")
            check(f"{s['id']}: set apart {s['expected_apart']}",
                  {fl: [list(k) for k in ks_] for fl, ks_ in ap.items()} == s["expected_apart"])
        if "expected" in s:
            ((_, r),) = kp
            check(f"{s['id']}: {s['expected']} in {s['expected_stock_unit']}, equal on QTY_EQ",
                  same(r.value, s["expected"]) and stock_unit(qy["basis"], r) == s["expected_stock_unit"]
                  and same(one(py_coverage(t, as_of, qy["grain"], f, "QTY_EQ"), "qty_eq").value, s["related"]["qty_eq"]))

    # ------------------------------------------------------------------ 7. general questions (session 8)
    print("\n7. General questions G1, G2: pandas, no Snowflake object, expected and wrong values")
    gq = {g["id"]: g for g in traps["general_questions"]}
    g1 = gq["G1"]
    v = g1_forecast(t, as_of, g1["query"])
    check(f"G1 forecast QTY_EQ = {g1['expected']}", same(v, g1["expected"]), f"got {v}")
    w = {"raw_units_summed": g1_forecast(t, as_of, g1["query"], "forecast_qty_raw"),
         "month_of_as_of": g1_forecast(t, as_of, g1["query"], k=0),
         "cumulative_to_month": g1_forecast(t, as_of, g1["query"], k_range=(1, g1["query"]["month_k"]))}
    for name, val in g1["wrong"].items():
        check(f"G1 wrong {name} = {val} != {g1['expected']}", same(w[name], val) and not same(val, g1["expected"]),
              f"got {w[name]}")
    g2 = gq["G2"]
    rows = g2_closing_value_by_country(t, as_of)
    check(f"G2: {len(g2['expected_rows'])} countries, value by country = expected_rows",
          rows.keys() == g2["expected_rows"].keys()
          and all(math.isclose(rows[c], v, abs_tol=1e-4) for c, v in g2["expected_rows"].items()), str(rows))
    check("G2: every item type and batch status at AS_OF (sum = all stock value of the month)",
          math.isclose(sum(rows.values()), float(st[st.snapshot_month == as_of].stock_value_eur.sum()), abs_tol=1e-3))
    for name, kw in (("item_join_fanout", {"join_items": True}), ("default_scope_applied", {"scope": scope})):
        wr = g2_closing_value_by_country(t, as_of, **kw)
        diff = {c: v for c, v in wr.items() if not math.isclose(v, g2["expected_rows"][c], abs_tol=1e-4)}
        check(f"G2 wrong {name}: rows {sorted(g2['wrong'][name])} differ, with the declared values",
              diff.keys() == g2["wrong"][name].keys()
              and all(math.isclose(diff[c], v, abs_tol=1e-4) for c, v in g2["wrong"][name].items()), str(diff))

    print(f"\n{'ALL CHECKS PASSED' if not failures else f'{len(failures)} FAILURE(S)'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
