"""
Session 7, step 0: the GENERATED closing stock (generated/closing_stock_sv.sql) against the native baseline of session 6.

    python snowflake/probe_closing/run_closing_generated.py (raw output pasted into results.md)

a. Deploys the gap-filled view and CLOSING_STOCK_SV as the project role, and records the row-count growth.
b. Reruns the four queries of run_probe_closing.py on the generated view (Q2 2026, CH): SKU x quarter, family x
   quarter, family x country with a quarter filter and no time dimension, SKU x month. Expected 0, 450, 450, and the
   SKU rows add up to the family row.
c. Sweep: every family x country x quarter of the data. The family row must equal the sum of its SKU rows (same
   view) and the pandas reference of the contract's rule, computed here from data/output/ (closing stock = snapshot
   of the quarter's last month, 0 for a member with no row that month; members = any snapshot in the quarter;
   DIM_ITEM read one row per item). Mismatches are listed, not hidden.

Connection "perso", USE SECONDARY ROLES NONE, LINKML_METRICS_ROLE. No agent, no LLM.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "snowflake" / "phase3_procedure"))
sys.path.insert(0, str(ROOT / "snowflake" / "probe_closing"))
from deploy import connect  # noqa: E402
from run_probe_closing import fmt, run, statements  # noqa: E402

TRAPS = yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())
CS = {c["id"]: c for c in TRAPS["closing_stock"]}
SV = "LINKML_METRICS.RAW.CLOSING_STOCK_SV"
VIEW = "LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT_GAPFILLED"
QUARTER = "2026-Q2"
TOL = 1e-6


def reference(out: Path, member: str = "family_code") -> dict[tuple[str, str, str], float]:
    """(family or sku, country, year_quarter) -> closing stock QTY_EQ by the contract's rule, pandas only."""
    st = pd.read_parquet(out / "FCT_STOCK_SNAPSHOT.parquet")
    items = pd.read_parquet(out / "DIM_ITEM.parquet").drop_duplicates("item_id")[["item_id", "family_code", "sku_code"]]
    geo = pd.read_parquet(out / "DIM_GEO.parquet")[["country_id", "country_code"]]
    st = st.merge(items, on="item_id").merge(geo, on="country_id")
    m = pd.to_datetime(st.snapshot_month)
    st["yq"] = m.dt.year.astype(str) + "-Q" + m.dt.quarter.astype(str)
    st["last"] = (m.dt.to_period("Q").dt.end_time.dt.to_period("M").dt.start_time).dt.date
    st["is_last"] = pd.to_datetime(st.snapshot_month).dt.date == st["last"]
    out_ = {}
    for key, g in st.groupby([member, "country_code", "yq"]):
        out_[key] = float(g.loc[g.is_last, "stock_qty_eq"].sum())   # members without a row that month add 0
    return out_


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--connection", default="perso")
    a = p.parse_args()
    con = connect(a.connection)
    cur = con.cursor()
    cur.execute("ALTER SESSION SET USE_CACHED_RESULT = FALSE")
    print("# Generated closing stock: raw output\n")

    # ---------------------------------------------------------------- a. deploy, growth
    for s in statements((ROOT / "generated" / "closing_stock_sv.sql").read_text()):
        cur.execute(s)
    rows, _, qid = run(cur, f"SELECT (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT) AS base_rows, "
                            f"COUNT(*) AS filled_rows, COUNT_IF(gap_filled) AS added_rows, "
                            f"COUNT_IF(gap_filled AND snapshot_month < (SELECT MAX(snapshot_month) FROM {VIEW})) AS added_before_latest, "
                            f"COUNT(DISTINCT batch_id, warehouse_id) AS keys FROM {VIEW}")
    r = rows[0]
    print("## a. Gap-filled view\n")
    print("| Base rows | Gap-filled rows | Added rows | Growth | Keys | Query id |\n|---|---|---|---|---|---|")
    print(f"| {r['BASE_ROWS']:,} | {r['FILLED_ROWS']:,} | {r['ADDED_ROWS']:,} | "
          f"{r['ADDED_ROWS'] / r['BASE_ROWS']:.2%} | {r['KEYS']:,} | `{qid}` |")
    rows, _, qid = run(cur, f"SELECT (SELECT SUM(stock_qty_eq) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT) AS base, "
                            f"SUM(stock_qty_eq) AS filled, COUNT_IF(gap_filled AND stock_qty_eq <> 0) AS nonzero_fill FROM {VIEW}")
    r = rows[0]
    ok = abs(float(r["BASE"]) - float(r["FILLED"])) < TOL and r["NONZERO_FILL"] == 0
    print(f"\nStock preserved (sum over all rows equal, every added row 0): **{'yes' if ok else 'NO'}** "
          f"({fmt(r['BASE'])} vs {fmt(r['FILLED'])}, `{qid}`)\n")

    # ---------------------------------------------------------------- b. the four probe queries
    print(f"## b. Closing stock heroes, {QUARTER}, through `{SV}`\n")
    print("| Case | Query | Row | Returned | Expected | Result | Query id |\n|---|---|---|---|---|---|---|")
    skus = "('SKU-H11', 'SKU-H12')"
    flt = f"geo.country_code = 'CH' AND calendar.year_quarter = '{QUARTER}'"
    cases = [
        ("1. SKU x quarter", f"DIMENSIONS item.sku_code, calendar.year_quarter METRICS stock_snapshot.closing_stock_qty_eq "
                             f"WHERE item.sku_code IN {skus} AND {flt}", "SKU_CODE",
         {"SKU-H11": "CS_LAST_MONTH_GAP", "SKU-H12": "CS_MIDDLE_MONTH_GAP"}),
        ("2. family x quarter", f"DIMENSIONS item.family_code, calendar.year_quarter METRICS stock_snapshot.closing_stock_qty_eq "
                                f"WHERE item.family_code = 'SNACK_BARS' AND {flt}", "FAMILY_CODE", {"SNACK_BARS": "CS_FAMILY"}),
        ("3. family x country, quarter filter, no time dimension",
         f"DIMENSIONS item.family_code, geo.country_code METRICS stock_snapshot.closing_stock_qty_eq "
         f"WHERE item.family_code = 'SNACK_BARS' AND {flt}", "FAMILY_CODE", {"SNACK_BARS": "CS_FAMILY"}),
        ("3b. SKU x country, quarter filter, no time dimension",
         f"DIMENSIONS item.sku_code, geo.country_code METRICS stock_snapshot.closing_stock_qty_eq "
         f"WHERE item.sku_code IN {skus} AND {flt}", "SKU_CODE",
         {"SKU-H11": "CS_LAST_MONTH_GAP", "SKU-H12": "CS_MIDDLE_MONTH_GAP"}),
    ]
    got_all = {}
    for label, body, key, expect in cases:
        sql = f"SELECT * FROM SEMANTIC_VIEW({SV} {body})"
        rows, err, qid = run(cur, sql)
        got = {} if err else {r_[key]: r_["CLOSING_STOCK_QTY_EQ"] for r_ in rows}
        got_all[label] = got
        for member, cid in expect.items():
            g = got.get(member)
            e = CS[cid]["expected"]
            res = "no row" if member not in got else ("expected" if g is not None and abs(float(g) - e) < TOL else
                                                       ", ".join(k for k, v in CS[cid]["wrong"].items() if g is not None and abs(float(g) - v) < TOL) or "differs")
            print(f"| {label} | `{sql}` | {member} | {err or (fmt(g) if member in got else 'no row')} | {e:g} | {res} | `{qid}` |")
    sql = (f"SELECT * FROM SEMANTIC_VIEW({SV} DIMENSIONS item.sku_code, calendar.month_start METRICS "
           f"stock_snapshot.closing_stock_qty_eq WHERE item.sku_code IN {skus} AND {flt}) ORDER BY sku_code, month_start")
    rows, err, qid = run(cur, sql)
    expected = {("SKU-H11", "2026-04-01"): 400, ("SKU-H11", "2026-05-01"): 350, ("SKU-H11", "2026-06-01"): 0,
                ("SKU-H12", "2026-04-01"): 500, ("SKU-H12", "2026-05-01"): 0, ("SKU-H12", "2026-06-01"): 450}
    got = {} if err else {(r_["SKU_CODE"], str(r_["MONTH_START"])): r_["CLOSING_STOCK_QTY_EQ"] for r_ in rows}
    for (sku, m), e in expected.items():
        g = got.get((sku, m))
        res = "no row" if (sku, m) not in got else ("expected" if abs(float(g) - e) < TOL else "differs")
        print(f"| 4. SKU x month | `{sql}` | {sku} {m} | {err or ('no row' if (sku, m) not in got else fmt(g))} | {e} | {res} | `{qid}` |")
    skus_sum = sum(float(v) for v in got_all["1. SKU x quarter"].values())
    fam = float(got_all["2. family x quarter"]["SNACK_BARS"])
    print(f"\nSKU rows add up to the family row: SKU-H11 + SKU-H12 = {skus_sum:g}, family = {fam:g}: "
          f"**{'yes' if abs(skus_sum - fam) < TOL else 'NO'}**\n")

    # ---------------------------------------------------------------- c. sweep
    print("## c. Sweep: every family x country x quarter\n")
    fam_sql = (f"SELECT * FROM SEMANTIC_VIEW({SV} DIMENSIONS item.family_code, geo.country_code, calendar.year_quarter "
               f"METRICS stock_snapshot.closing_stock_qty_eq)")
    sku_sql = (f"SELECT * FROM SEMANTIC_VIEW({SV} DIMENSIONS item.family_code, item.sku_code, geo.country_code, "
               f"calendar.year_quarter METRICS stock_snapshot.closing_stock_qty_eq)")
    nat_sql = (f"SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS "
               f"item.family_code, geo.country_code, cal.year_quarter METRICS stock.stock_qty)")
    frows, ferr, fqid = run(cur, fam_sql)
    srows, serr, sqid = run(cur, sku_sql)
    nrows, nerr, nqid = run(cur, nat_sql)
    assert not (ferr or serr or nerr), (ferr, serr, nerr)
    fam_v = {(r_["FAMILY_CODE"], r_["COUNTRY_CODE"], r_["YEAR_QUARTER"]): float(r_["CLOSING_STOCK_QTY_EQ"]) for r_ in frows}
    sku_sum = defaultdict(float)
    for r_ in srows:
        sku_sum[(r_["FAMILY_CODE"], r_["COUNTRY_CODE"], r_["YEAR_QUARTER"])] += float(r_["CLOSING_STOCK_QTY_EQ"])
    nat_v = {(r_["FAMILY_CODE"], r_["COUNTRY_CODE"], r_["YEAR_QUARTER"]): float(r_["STOCK_QTY"]) for r_ in nrows}
    ref = reference(ROOT / "data" / "output")
    keys = sorted(set(fam_v) | set(ref))
    sum_bad = [k for k in fam_v if abs(fam_v[k] - sku_sum.get(k, 0.0)) > TOL]
    ref_bad = [k for k in keys if k in ref and (k not in fam_v or abs(fam_v[k] - ref[k]) > TOL)]
    extra = [k for k in fam_v if k not in ref]
    extra_nonzero = [k for k in extra if abs(fam_v[k]) > TOL]
    nat_bad = [k for k in ref if k not in nat_v or abs(nat_v[k] - ref[k]) > TOL]
    print("| Check | Groups | Failures | Query id |\n|---|---|---|---|")
    print(f"| generated: family row = sum of its SKU rows | {len(fam_v)} | {len(sum_bad)} | `{fqid}`, `{sqid}` |")
    print(f"| generated: family row = pandas reference (contract rule) | {len(ref)} | {len(ref_bad)} | `{fqid}` |")
    print(f"| generated: rows with no reference member (a key's 0 row starting the quarter) | {len(extra)} | "
          f"{len(extra_nonzero)} non-zero | `{fqid}` |")
    print(f"| native baseline (session 6 view): family row = pandas reference | {len(ref)} | {len(nat_bad)} | `{nqid}` |")
    # SKU x country x quarter: where a member's last snapshot is before the quarter's last month
    sref = reference(ROOT / "data" / "output", "sku_code")
    gen_s = {(r_["SKU_CODE"], r_["COUNTRY_CODE"], r_["YEAR_QUARTER"]): float(r_["CLOSING_STOCK_QTY_EQ"]) for r_ in srows}
    nsql = (f"SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS "
            f"item.sku_code, geo.country_code, cal.year_quarter METRICS stock.stock_qty)")
    nsrows, nserr, nsqid = run(cur, nsql)
    assert not nserr, nserr
    nat_s = {(r_["SKU_CODE"], r_["COUNTRY_CODE"], r_["YEAR_QUARTER"]): float(r_["STOCK_QTY"]) for r_ in nsrows}
    t7 = lambda k: k[0] == "SKU-H06"  # noqa: E731  T7 fan-out, reported above
    for name, got, qid_ in (("generated", gen_s, sqid), ("native baseline (session 6 view)", nat_s, nsqid)):
        bad = [k for k in sref if not t7(k) and (k not in got or abs(got[k] - sref[k]) > TOL)]
        carried = [k for k in bad if sref[k] == 0 and k in got and got[k] > 0]
        print(f"| {name}: SKU x country x quarter = pandas reference (SKU-H06 left out, T7) | "
              f"{sum(1 for k in sref if not t7(k))} | {len(bad)} ({len(carried)} where the reference is 0 and a "
              f"positive value is returned) | `{qid_}` |")
    for title, bad, got in (("generated, family != SKU sum", sum_bad, sku_sum), ("generated, family != reference", ref_bad, ref),
                            ("native, family != reference", nat_bad, ref)):
        if bad:
            print(f"\n{title} ({len(bad)}):\n")
            print("| Family | Country | Quarter | Generated | Native | SKU sum | Reference |\n|---|---|---|---|---|---|---|")
            for k in bad[:40]:
                print(f"| {k[0]} | {k[1]} | {k[2]} | {fmt(fam_v.get(k))} | {fmt(nat_v.get(k))} | "
                      f"{fmt(sku_sum.get(k))} | {fmt(ref.get(k))} |")
            if len(bad) > 40:
                print(f"| ... {len(bad) - 40} more | n/a | n/a | n/a | n/a | n/a | n/a |")
    con.close()


if __name__ == "__main__":
    main()
