"""
Phase 0, probe A addendum (session 2): is config B a straw man?

    python snowflake/probe_a/run_probe_a_addendum.py [--connection linkml] > snowflake/probe_a/results_addendum.md

Part a: COVERAGE_SPINE_ASOF_PROBE_SV (30_spine_asof_variable_PROBE.sql) declares a semantic-view variable
`analysis_month DATE` with no default. Can a query that omits it (T6) fail instead of returning 0.0394?
Part b: COVERAGE_T3_BRIDGE_PROBE_SV (40_t3_status_bridge_PROBE.sql), one honest attempt at T3 in a single
SEMANTIC_VIEW() call: the forward spine replicated per batch status, de-replicated by COUNT(DISTINCT batch_status).

Every query goes through SEMANTIC_VIEW() directly (no agent, no LLM). Expected values come from data/traps.yaml.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import snowflake.connector
import yaml

ROOT = Path(__file__).resolve().parents[2]
AS_OF = "2026-06-01"
ASOF_SV = "LINKML_METRICS.RAW.COVERAGE_SPINE_ASOF_PROBE_SV"
BRIDGE_SV = "LINKML_METRICS.RAW.COVERAGE_T3_BRIDGE_PROBE_SV"
DIM = {"sku_code": "item.sku_code", "family_code": "item.family_code", "country_code": "geo.country_code",
       "batch_status": "batch.batch_status"}


class Runner:
    def __init__(self, cur):
        self.cur = cur
        print("| Case | Query | Returned | Expected | Result | Query id |\n|---|---|---|---|---|---|")

    def q(self, label: str, sql: str, expected, col: str = "COVERAGE_MONTHS", show: str | None = None) -> list[dict]:
        """expected: a number or None (one row), 'error' (must fail), or a list of numbers (several rows)."""
        try:
            rows = self.cur.execute(sql).fetchall()
            cols = [d[0] for d in self.cur.description]
            rows = [dict(zip(cols, r)) for r in rows]
            vals = [r.get(col) for r in rows]
            got = "; ".join("NULL" if v is None else v if isinstance(v, str) else f"{float(v):.4f}"
                            for v in vals) or "no row"
            if show:
                got += "  (" + "; ".join(str(r.get(show)) for r in rows) + ")"
            if expected == "error":
                ok = False
            elif isinstance(expected, list):
                ok = sorted(float(v) for v in vals if v is not None) == sorted(expected) and None not in vals
            else:
                ok = len(vals) == 1 and ((vals[0] is None and expected is None) or
                                         (vals[0] is not None and expected is not None
                                          and abs(float(vals[0]) - expected) < 1e-6))
        except snowflake.connector.errors.ProgrammingError as e:
            rows, got = [], f"error {e.errno}: {str(e.msg).splitlines()[-1].strip()}"
            ok = expected == "error"
        flat = " ".join(sql.split())
        print(f"| {label} | `{flat}` | {got} | {expected} | {'MATCH' if ok else 'MISMATCH'} | `{self.cur.sfqid}` |")
        return rows


def part_a(r: Runner, traps: list[dict]) -> None:
    def sv(dims, where, variables=None, metrics="coverage_months, stock.stock_qty, fwd.c01"):
        v = f" VARIABLES {variables}" if variables else ""
        w = f" WHERE {where}" if where else ""
        return f"SELECT * FROM SEMANTIC_VIEW({ASOF_SV} DIMENSIONS {', '.join(dims)} METRICS {metrics}{w}{v})"

    fam_fr = "item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR'"
    fam_dims = ["item.family_code", "geo.country_code"]
    r.q("a1. T6, no analysis month, variable omitted", sv(fam_dims, fam_fr), "error")
    r.q("a2. T6 question with the variable set, no month dimension", sv(fam_dims, fam_fr, f"analysis_month => DATE '{AS_OF}'"), 2.8)
    r.q("a3. One dimension, no metric (nothing references the variable), variable omitted",
        sv(["item.family_code"], "item.family_code = 'PANTRY_FLOUR'", metrics="").replace(" METRICS ", " "),
        "error", col="FAMILY_CODE")
    r.q("a3b. Variable passed as a string literal, not a DATE", sv(fam_dims, fam_fr, f"analysis_month => '{AS_OF}'"),
        "error")
    for t in traps:
        g, f = t["query"]["grain"], t["query"]["filters"]
        where = " AND ".join(f"{DIM[k]} = '{v}'" for k, v in f.items())
        r.q(f"a4. {t['id']} with the variable, no month dimension", sv([DIM[x] for x in g], where,
                                                                        f"analysis_month => DATE '{AS_OF}'"), t["expected"])
    h04 = "item.sku_code = 'SKU-H04' AND geo.country_code = 'IT'"
    r.q("a5. Series request: month dimension over 3 months, variable set to June",
        sv(["item.sku_code", "geo.country_code", "cal.month_start"],
           f"{h04} AND cal.month_start BETWEEN '2026-04-01' AND '2026-06-01'", f"analysis_month => DATE '{AS_OF}'"),
        [4.98, 7.5, 10.0], show="MONTH_START")
    r.q("a6. Variable set to a mid-month date (2026-06-15)", sv(fam_dims, fam_fr, "analysis_month => DATE '2026-06-15'"), "error")
    r.q("a7. Variable set to NULL", sv(fam_dims, fam_fr, "analysis_month => NULL"), "error")


def part_b(r: Runner, traps: list[dict]) -> None:
    def sv(dims, where, metrics="coverage_months, stock.stock_qty, fwd.c01, fwd.c01_naive"):
        return (f"SELECT * FROM SEMANTIC_VIEW({BRIDGE_SV} DIMENSIONS {', '.join(dims + ['cal.month_start'])} "
                f"METRICS {metrics} WHERE {where} AND cal.month_start = '{AS_OF}')")

    h04 = "item.sku_code = 'SKU-H04' AND geo.country_code = 'IT'"
    sku = ["item.sku_code", "geo.country_code"]
    # expected: (coverage, C01 de-replicated, C01_NAIVE = 100 x number of status replicas kept by the filter)
    for label, extra, exp in (("b1. T3: RELEASED filter", " AND status.batch_status = 'RELEASED'", (6.0, 100.0, 100.0)),
                              ("b2. T3 related: QUALITY_HOLD filter", " AND status.batch_status = 'QUALITY_HOLD'",
                               (4.0, 100.0, 100.0)),
                              ("b3. Two statuses: IN (RELEASED, QUALITY_HOLD)",
                               " AND status.batch_status IN ('RELEASED', 'QUALITY_HOLD')", (10.0, 100.0, 200.0)),
                              ("b4. No status filter", "", (10.0, 100.0, 300.0)),
                              ("b5. BLOCKED filter: no stock in that status, forecast exists",
                               " AND status.batch_status = 'BLOCKED'", (0.0, 100.0, 100.0))):
        for col, e in zip(("COVERAGE_MONTHS", "C01", "C01_NAIVE"), exp):
            r.q(f"{label} [{col}]", sv(sku, h04 + extra), e, col=col)
    # Reference (data/coverage_ref.py, both implementations): two rows, RELEASED 6.0 and QUALITY_HOLD 4.0. On a
    # stock-only grain, forecast-only members are not created, so there is no BLOCKED row.
    r.q("b6. Status as a dimension (reference: 2 rows)", sv(sku + ["status.batch_status"], h04),
        [6.0, 4.0], show="BATCH_STATUS")
    for t in traps:
        if t["id"] == "T3":
            continue
        g, f = t["query"]["grain"], t["query"]["filters"]
        where = " AND ".join(f"{DIM[k]} = '{v}'" for k, v in f.items())
        r.q(f"b7. {t['id']} on the bridge view", sv([DIM[x] for x in g], where), t["expected"])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--connection", default="linkml")
    p.add_argument("--part", choices=["a", "b", "all"], default="all")
    a = p.parse_args()
    traps = yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())["traps"]
    con = snowflake.connector.connect(connection_name=a.connection, role="LINKML_METRICS_ROLE",
                                      warehouse="LINKML_METRICS_WH", database="LINKML_METRICS", schema="RAW")
    cur = con.cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    print(f"# Probe A addendum\n\nAS_OF = {AS_OF}. Session: `{cur.execute('SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()').fetchone()}`")
    print("\n'error' as expected value means the correct behaviour is a refusal. A series expects one value per month.\n")
    if a.part in ("a", "all"):
        print(f"## a. Required as-of variable ({ASOF_SV})\n")
        part_a(Runner(cur), traps)
    if a.part in ("b", "all"):
        print(f"\n## b. T3 in one call: batch-status bridge ({BRIDGE_SV})\n")
        part_b(Runner(cur), traps)
    con.close()


if __name__ == "__main__":
    main()
