"""
Phase 0, probe A, second build: native semantic view over a query-defined FORWARD SPINE.

    python snowflake/probe_a/gen_spine_sv.py > snowflake/probe_a/20_spine_sv.sql
    python snowflake/probe_a/gen_spine_sv.py --mode asof-variable > snowflake/probe_a/30_spine_asof_variable_PROBE.sql
    python snowflake/probe_a/gen_spine_sv.py --mode status-bridge > snowflake/probe_a/40_t3_status_bridge_PROBE.sql

The first build (gen_native_sv.py) cannot carry coverage as a metric: a derived metric may not reference
window metrics (010273). This build moves the forward window out of window metrics and into a logical table
defined by a query: one row per (as_of_month, item, country) with f01..f24 = forecast at as_of + k, missing
months already densified to 0. C1..C24 then become plain additive metrics, and coverage a derived metric.

It is still 100% native (a query-defined logical table is a documented semantic-view feature), but the
window semantics now live in hand-written SQL inside the view: T2 (densify) and T4 (window relative to
the analysis month) are solved by that SQL, not by the semantic layer.

Session 2 addendum modes (probe objects, suffix _PROBE):
- asof-variable -> COVERAGE_SPINE_ASOF_PROBE_SV: the same view plus a semantic-view variable `analysis_month DATE`
  with NO default, referenced by the stock metric and by every forward metric. Question: does a query that omits
  the analysis month (T6) fail instead of returning 0.0394?
- status-bridge -> COVERAGE_T3_BRIDGE_PROBE_SV: one honest attempt at T3 in a single call. The forward spine is
  replicated once per batch status and related to a `status` table that stock also reaches through `batch`, so a
  status filter reaches both facts. Each forward metric exists twice: `*_naive` = SUM (counts every replica) and
  the corrected form SUM / COUNT(DISTINCT batch_status), which divides the replication back out.
"""

from __future__ import annotations

import argparse

H = 24
NAMES = {
    "base": "LINKML_METRICS.RAW.COVERAGE_SPINE_SV",
    "asof-variable": "LINKML_METRICS.RAW.COVERAGE_SPINE_ASOF_PROBE_SV",
    "status-bridge": "LINKML_METRICS.RAW.COVERAGE_T3_BRIDGE_PROBE_SV",
}
HEADERS = {
    "base": "Phase 0 probe A, config B (second build)",
    "asof-variable": "Phase 0 probe A addendum: required as-of variable (T6)",
    "status-bridge": "Phase 0 probe A addendum: batch-status bridge (T3)",
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=list(NAMES), default="base")
    mode = p.parse_args().mode
    var, bridge = mode == "asof-variable", mode == "status-bridge"

    def fwd(expr: str) -> str:
        """A forward-spine aggregate: restricted to the analysis month (variable), or de-replicated (bridge)."""
        if var:
            return f"SUM(IFF(as_of_month = analysis_month, {expr}, NULL))"
        if bridge:
            return f"SUM({expr}) / COUNT(DISTINCT batch_status)"
        return f"SUM({expr})"

    f_cols = ",\n          ".join(
        f"SUM(IFF(DATEDIFF(month, a.month_start, f.forecast_month) = {k}, f.forecast_qty_eq, 0)) AS f{k:02d}"
        for k in range(1, H + 1))
    c_metrics = ",\n    ".join(
        f"fwd.c{k:02d} AS {fwd(' + '.join(f'f{j:02d}' for j in range(1, k + 1)))}" for k in range(1, H + 1))
    m_metrics = ",\n    ".join(f"fwd.m{k:02d} AS {fwd(f'f{k:02d}')}" for k in range(1, H + 1))
    stock_metric = "stock.stock_qty NON ADDITIVE BY (stock.snapshot_month ASC NULLS LAST) AS SUM(stock_qty_eq)"
    variables = ""
    fwd_select, fwd_from, fwd_group, fwd_pk = "a.month_start AS as_of_month, f.item_id, f.country_id", "", \
        "a.month_start, f.item_id, f.country_id", "as_of_month, item_id, country_id"
    status_table = status_rel = ""
    status_dim = "batch.batch_status AS batch_status COMMENT = 'Stock-only attribute: the forecast has no batch.'"
    if var:
        stock_metric = "stock.stock_qty AS SUM(IFF(snapshot_month = analysis_month, stock_qty_eq, NULL))"
        variables = ("\n  VARIABLES (\n    analysis_month DATE\n  )"
                     "\n  -- no DEFAULT: the probe asks whether omitting it makes the query fail")
    if bridge:
        fwd_select += ", st.batch_status"
        fwd_from = "\n        CROSS JOIN (SELECT DISTINCT batch_status FROM LINKML_METRICS.RAW.DIM_BATCH) st"
        fwd_group += ", st.batch_status"
        fwd_pk += ", batch_status"
        status_table = ("\n    status AS (SELECT DISTINCT batch_status FROM LINKML_METRICS.RAW.DIM_BATCH)"
                        " PRIMARY KEY (batch_status),")
        status_rel = ("\n    batch_status_rel AS batch (batch_status) REFERENCES status,"
                      "\n    fwd_status  AS fwd (batch_status)     REFERENCES status,")
        status_dim = ("status.batch_status AS batch_status COMMENT = 'Reached by stock through batch, and by the "
                      "forward spine through its per-status replicas.'")
        c_metrics += ",\n    " + ",\n    ".join(
            f"fwd.c{k:02d}_naive AS SUM({' + '.join(f'f{j:02d}' for j in range(1, k + 1))})" for k in (1, 24))
    nz = " + ".join(f"IFF(fwd.m{k:02d} > 0, 1, 0)" for k in range(1, H + 1))
    branches = ["      WHEN stock.stock_qty IS NULL OR stock.stock_qty = 0 THEN 0",
                "      WHEN fwd.c24 IS NULL OR fwd.c24 = 0 THEN NULL",
                "      WHEN stock.stock_qty <= fwd.c01 THEN stock.stock_qty / fwd.c01"]
    for n in range(2, H + 1):
        branches.append(f"      WHEN stock.stock_qty <= fwd.c{n:02d} THEN {n - 1} + "
                        f"(stock.stock_qty - fwd.c{n - 1:02d}) / (fwd.c{n:02d} - fwd.c{n - 1:02d})")
    branches.append(f"      ELSE stock.stock_qty / (fwd.c{H} / ({nz}))")

    print(f"""-- GENERATED by snowflake/probe_a/gen_spine_sv.py. {HEADERS[mode]}. Do not edit.
USE SECONDARY ROLES NONE;
USE ROLE LINKML_METRICS_ROLE;

CREATE OR REPLACE SEMANTIC VIEW {NAMES[mode]}
  TABLES (
    item  AS LINKML_METRICS.RAW.DIM_ITEM      PRIMARY KEY (item_id),
    geo   AS LINKML_METRICS.RAW.DIM_GEO       PRIMARY KEY (country_id),
    cal   AS LINKML_METRICS.RAW.DIM_CALENDAR  PRIMARY KEY (month_start),
    batch AS LINKML_METRICS.RAW.DIM_BATCH     PRIMARY KEY (batch_id),{status_table}
    stock AS LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT PRIMARY KEY (snapshot_month, batch_id, warehouse_id),
    fwd AS (
        SELECT {fwd_select},
          {f_cols}
        FROM LINKML_METRICS.RAW.DIM_CALENDAR a
        JOIN LINKML_METRICS.RAW.FCT_FORECAST f
          ON f.forecast_month > a.month_start AND f.forecast_month <= DATEADD(month, {H}, a.month_start){fwd_from}
        GROUP BY {fwd_group}
    ) PRIMARY KEY ({fwd_pk})
      COMMENT = 'Forward forecast spine: f01..f24 = forecast at analysis month + k, missing months = 0.'
  )
  RELATIONSHIPS (
    stock_item  AS stock (item_id)        REFERENCES item,
    stock_geo   AS stock (country_id)     REFERENCES geo,
    stock_cal   AS stock (snapshot_month) REFERENCES cal,
    stock_batch AS stock (batch_id)       REFERENCES batch,{status_rel}
    fwd_item    AS fwd (item_id)          REFERENCES item,
    fwd_geo     AS fwd (country_id)       REFERENCES geo,
    fwd_cal     AS fwd (as_of_month)      REFERENCES cal
  ){variables}
  DIMENSIONS (
    item.sku_code      AS sku_code,
    item.family_code   AS family_code,
    item.range_code    AS range_code,
    geo.country_code   AS country_code,
    geo.region_code    AS region_code,
    cal.month_start    AS month_start COMMENT = 'Analysis month (as-of). The forecast window is the 24 months after it.',
    {status_dim},
    stock.snapshot_month AS snapshot_month
  )
  METRICS (
    {stock_metric},
    {c_metrics},
    {m_metrics},
    coverage_months AS CASE
{chr(10).join(branches)}
    END
      COMMENT = 'Forward stock coverage in months (H = 24), recomputed from aggregated stock and forecast at the queried grain.'
  )
  COMMENT = 'Phase 0 probe A (config B, second build): forward spine as a query-defined logical table.';
""")


if __name__ == "__main__":
    main()
