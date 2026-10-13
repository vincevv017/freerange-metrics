"""
Phase 0, probe A, second build: query COVERAGE_SPINE_SV, where coverage IS a semantic-view metric.

    python snowflake/probe_a/run_probe_a_spine.py [--connection linkml] > snowflake/probe_a/results_spine.md

Expected values come from data/traps.yaml (hand-computed, re-asserted by data/checks/check_dataset.py).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import snowflake.connector
import yaml

ROOT = Path(__file__).resolve().parents[2]
SV = "LINKML_METRICS.RAW.COVERAGE_SPINE_SV"
AS_OF = "2026-06-01"
DIM = {"sku_code": "item.sku_code", "family_code": "item.family_code", "country_code": "geo.country_code",
       "batch_status": "batch.batch_status"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--connection", default="linkml")
    a = p.parse_args()
    traps = yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())["traps"]
    con = snowflake.connector.connect(connection_name=a.connection, role="LINKML_METRICS_ROLE",
                                      warehouse="LINKML_METRICS_WH", database="LINKML_METRICS", schema="RAW")
    cur = con.cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    print(f"# Probe A, second build ({SV})\n\nAS_OF = {AS_OF}. Month filter INSIDE SEMANTIC_VIEW.\n")
    print("| Trap | Query | Coverage returned | Expected | Result | Query id |\n|---|---|---|---|---|---|")

    def q(label, dims, where, expected, extra=""):
        sql = (f"SELECT * FROM SEMANTIC_VIEW({SV} DIMENSIONS {', '.join(dims)} "
               f"METRICS coverage_months, stock.stock_qty, fwd.c01 WHERE {where}){extra}")
        try:
            rows = cur.execute(sql).fetchall()
            cols = [d[0] for d in cur.description]
            vals = [dict(zip(cols, r))["COVERAGE_MONTHS"] for r in rows]
            got = "; ".join("NULL" if v is None else f"{float(v):.4f}" for v in vals) or "no row"
            ok = (len(vals) == 1 and ((vals[0] is None and expected is None) or
                  (vals[0] is not None and expected is not None and abs(float(vals[0]) - expected) < 1e-6)))
            res = "MATCH" if ok else "MISMATCH"
        except snowflake.connector.errors.ProgrammingError as e:
            got, res = f"error {e.errno}: {str(e.msg).splitlines()[-1].strip()}", "FAIL"
        print(f"| {label} | `{where}` | {got} | {expected} | {res} | `{cur.sfqid}` |")

    for t in traps:
        g, f = t["query"]["grain"], t["query"]["filters"]
        dims = [DIM[x] for x in g] + ["cal.month_start"]
        where = " AND ".join([f"{DIM[k]} = '{v}'" for k, v in f.items()] + [f"cal.month_start = '{AS_OF}'"])
        q(t["id"], dims, where, t["expected"])

    # T4 variant: time filter as the only month handle, no month dimension requested
    q("T4, month as filter only", ["item.sku_code", "geo.country_code"],
      f"item.sku_code = 'SKU-H05' AND geo.country_code = 'ES' AND cal.month_start = '{AS_OF}'", 8.5)
    # T6: no analysis month at all -> the view should refuse; does it return a number?
    q("T6, no analysis month", ["item.family_code", "geo.country_code"],
      "item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR'", None)
    # Series: several analysis months, one row each, no total across months
    q("Series, 3 months (expect 3 rows)", ["item.sku_code", "geo.country_code", "cal.month_start"],
      "item.sku_code = 'SKU-H04' AND geo.country_code = 'IT' AND cal.month_start BETWEEN '2026-04-01' AND '2026-06-01'",
      None)
    con.close()


if __name__ == "__main__":
    main()
