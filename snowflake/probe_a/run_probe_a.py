"""
Phase 0, probe A: query the native semantic views and record what they return for traps T1-T4 and T7.

    python snowflake/probe_a/run_probe_a.py [--connection linkml] > snowflake/probe_a/results.md

Every query goes through SEMANTIC_VIEW() directly (no agent), so this measures what the native objects can
express, not what an LLM would write. The coverage itself cannot be a semantic-view metric (010273, see
09_native_sv_rows_with_coverage_REJECTED.sql), so the view returns stock and the forward cumulative
forecasts C1..C24, and the cascade runs here, outside the view, exactly as a consumer would have to write it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
from coverage_ref import cascade  # noqa: E402

AS_OF = "2026-06-01"
H = 24
C = ", ".join(f"fc.c{k:02d}" for k in range(1, H + 1))


def sv(frame: str) -> str:
    return f"LINKML_METRICS.RAW.COVERAGE_NATIVE_{frame.upper()}_SV"


def coverage_from_row(stock, cs, nz):
    """Rebuild f(k) from the cumulative metrics and run the reference cascade on it."""
    if any(c is None for c in cs):
        return None, "C_k NULL"
    f = [float(cs[0])] + [float(cs[k] - cs[k - 1]) for k in range(1, H)]
    r = cascade(float(stock or 0), f)
    return r.value, r.flag


def run(cur, label: str, sql: str, max_rows: int = 12) -> list[tuple] | None:
    print(f"\n#### {label}\n\n```sql\n{sql.strip()}\n```\n")
    try:
        rows = cur.execute(sql).fetchall()
        cols = [d[0] for d in cur.description]
    except snowflake.connector.errors.ProgrammingError as e:
        print(f"**Error** `{e.errno}`: `{str(e.msg).strip()}`  (query id `{e.sfqid}`)")
        return None
    print(f"query id `{cur.sfqid}`, {len(rows)} row(s)\n")
    show = [c for c in cols if not (c.startswith("C") and c[1:].isdigit() and int(c[1:]) > 8)]
    print("| " + " | ".join(show) + " |\n|" + "---|" * len(show))
    for r in rows[:max_rows]:
        d = dict(zip(cols, r))
        print("| " + " | ".join("" if d[c] is None else str(d[c]) for c in show) + " |")
    if len(rows) > max_rows:
        print(f"| ... {len(rows) - max_rows} more |")
    return [dict(zip(cols, r)) for r in rows]


def report_coverage(rows, label, expected):
    if not rows:
        print(f"\n**{label}: no row returned** (expected {expected}).")
        return
    for d in rows:
        if str(d.get("MONTH_START", AS_OF)) != AS_OF:
            continue
        cs = [d.get(f"C{k:02d}") for k in range(1, H + 1)]
        v, flag = coverage_from_row(d.get("STOCK_QTY"), cs, d.get("NZ24"))
        ok = (v is None and expected is None) or (v is not None and expected is not None and abs(v - expected) < 1e-9)
        print(f"\n**{label}: coverage rebuilt from the view = {v} ({flag}); expected {expected} -> "
              f"{'MATCH' if ok else 'MISMATCH'}**")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--connection", default="linkml")
    a = p.parse_args()
    con = snowflake.connector.connect(connection_name=a.connection, role="LINKML_METRICS_ROLE",
                                      warehouse="LINKML_METRICS_WH", database="LINKML_METRICS", schema="RAW")
    cur = con.cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    print(f"# Probe A raw results\n\nAS_OF = {AS_OF}. Session: `{cur.execute('SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()').fetchone()}`")

    # ---- T2: sparse months, ROWS vs RANGE frames ------------------------------------------------
    print("\n## T2 sparse forecast months (SKU-H03 / DE, forecast rows absent for k = 2, 3; expected 7.0)")
    for frame in ("rows", "range"):
        rows = run(cur, f"T2, {frame.upper()} frame, outer filter on the month", f"""
SELECT * FROM SEMANTIC_VIEW({sv(frame)}
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, {C}, fc.nz24
    WHERE item.sku_code = 'SKU-H03' AND geo.country_code = 'DE')
WHERE month_start = '{AS_OF}'""")
        report_coverage(rows, f"T2 {frame.upper()}", 7.0)

    # ---- T4: time filter inside vs outside SEMANTIC_VIEW ---------------------------------------
    print("\n## T4 time filter (SKU-H05 / ES, expected 8.5)")
    rows = run(cur, "T4, month filter INSIDE SEMANTIC_VIEW (the natural way to ask 'for June')", f"""
SELECT * FROM SEMANTIC_VIEW({sv('range')}
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, {C}, fc.nz24
    WHERE item.sku_code = 'SKU-H05' AND geo.country_code = 'ES' AND cal.month_start = '{AS_OF}')""")
    report_coverage(rows, "T4 inner filter", 8.5)
    rows = run(cur, "T4, month filter OUTSIDE SEMANTIC_VIEW", f"""
SELECT * FROM SEMANTIC_VIEW({sv('range')}
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, {C}, fc.nz24
    WHERE item.sku_code = 'SKU-H05' AND geo.country_code = 'ES')
WHERE month_start = '{AS_OF}'""")
    report_coverage(rows, "T4 outer filter", 8.5)

    # ---- T3: stock-only attribute with forecast metrics -----------------------------------------
    print("\n## T3 stock-only filter (SKU-H04 / IT released lots, expected 6.0)")
    run(cur, "T3, batch_status as a DIMENSION with forecast metrics", f"""
SELECT * FROM SEMANTIC_VIEW({sv('range')}
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index, batch.batch_status
    METRICS stock.stock_qty, fc.c01
    WHERE item.sku_code = 'SKU-H04' AND geo.country_code = 'IT')
WHERE month_start = '{AS_OF}'""")
    rows = run(cur, "T3, batch_status as a FILTER with forecast metrics", f"""
SELECT * FROM SEMANTIC_VIEW({sv('range')}
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, {C}, fc.nz24
    WHERE item.sku_code = 'SKU-H04' AND geo.country_code = 'IT' AND batch.batch_status = 'RELEASED')
WHERE month_start = '{AS_OF}'""")
    report_coverage(rows, "T3 filter", 6.0)
    rows = run(cur, "T3, two SEMANTIC_VIEW calls joined by the consumer (stock filtered, forecast not)", f"""
WITH s AS (SELECT * FROM SEMANTIC_VIEW({sv('range')}
               DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
               METRICS stock.stock_qty
               WHERE item.sku_code = 'SKU-H04' AND geo.country_code = 'IT' AND batch.batch_status = 'RELEASED')),
     f AS (SELECT * FROM SEMANTIC_VIEW({sv('range')}
               DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
               METRICS {C}, fc.nz24
               WHERE item.sku_code = 'SKU-H04' AND geo.country_code = 'IT'))
SELECT f.*, s.stock_qty FROM f LEFT JOIN s USING (sku_code, country_code, month_start, month_index)
WHERE month_start = '{AS_OF}'""")
    report_coverage(rows, "T3 two calls", 6.0)

    # ---- T1: re-aggregation at family grain -----------------------------------------------------
    print("\n## T1 ratio re-aggregation (PANTRY_FLOUR / FR, expected 2.8)")
    rows = run(cur, "T1, family grain", f"""
SELECT * FROM SEMANTIC_VIEW({sv('range')}
    DIMENSIONS item.family_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, {C}, fc.nz24
    WHERE item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR')
WHERE month_start = '{AS_OF}'""")
    report_coverage(rows, "T1 family", 2.8)

    # ---- T7: fan-out on the duplicated item -----------------------------------------------------
    print("\n## T7 master-data fan-out (PANTRY_OIL / SE, expected stock 900, C1 400, coverage 2.25)")
    rows = run(cur, "T7, family grain over a dimension declared PRIMARY KEY but duplicated", f"""
SELECT * FROM SEMANTIC_VIEW({sv('range')}
    DIMENSIONS item.family_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, {C}, fc.nz24
    WHERE item.family_code = 'PANTRY_OIL' AND geo.country_code = 'SE')
WHERE month_start = '{AS_OF}'""")
    report_coverage(rows, "T7 family", 2.25)

    # ---- stock semi-additivity and T8 -----------------------------------------------------------
    print("\n## Semi-additive stock and T8")
    run(cur, "NON ADDITIVE BY: stock of SKU-H04 / IT without the month dimension (expected latest = 1000)", f"""
SELECT * FROM SEMANTIC_VIEW({sv('range')}
    DIMENSIONS item.sku_code, geo.country_code
    METRICS stock.stock_qty
    WHERE item.sku_code = 'SKU-H04' AND geo.country_code = 'IT')""")
    rows = run(cur, "T8: SKU-H08 / NL, forecast but no stock (expected 0, row kept)", f"""
SELECT * FROM SEMANTIC_VIEW({sv('range')}
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, {C}, fc.nz24
    WHERE item.sku_code = 'SKU-H08' AND geo.country_code = 'NL')
WHERE month_start = '{AS_OF}'""")
    report_coverage(rows, "T8", 0.0)
    con.close()


if __name__ == "__main__":
    main()
