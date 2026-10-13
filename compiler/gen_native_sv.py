"""
Seventh generator: the contract -> configuration B2 of session 8, native objects and their agent.

    python compiler/gen_native_sv.py                       # writes the three files into generated/
    python compiler/gen_native_sv.py --out-dir /tmp/b2     # writes elsewhere (the drift test uses this)

Three files:
1. generated/b2_native_views.sql: physical views the semantic view reads, so that every logical table names a
   database.schema.table (the owner's enrich tool profiles nothing else):
   - B2_ITEM: one row per distinct combination of the item key and the item attributes of the contract with their
     label columns. A dimension whose grain a REFUSE_IF_USED expectation checks cannot refuse in a semantic view, so
     an item whose rows differ on an attribute (T7) still has two rows here, as in the generated closing view.
   - B2_STATUS: the distinct values of the bridged snapshot-only attribute (batch_status).
   - B2_FORECAST_SPINE: the forward spine of the depletion metric, one row per valid analysis month x item x country x
     bridged status, with the flow of months t+1..t+H as columns per unit variant (missing months at 0: densified,
     T2), the window relative to the analysis month (T4). Valid analysis months follow the contract's validity rule.
     The rows are replicated once per status (the status bridge, T3): every forward metric divides by the count of
     distinct statuses, so a status filter restricts the stock only and the forecast counts once (phase 0, probe A).
2. generated/b2_native_sv.yaml: the semantic view LINKML_B2_SV (model YAML, deployed with
   CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML after enrichment). Stock is read from the gap-filled snapshot
   (FCT_STOCK_SNAPSHOT_GAPFILLED, written by compiler/gen_closing_sv.py: absent = 0, T9 and closing stock), NON
   ADDITIVE BY the snapshot month; closing stock per unit variant; the flow as a plain additive measure (general
   questions); per unit variant 24 cumulative forward metrics and 24 monthly ones (private), and coverage as a derived
   metric (the outcomes of the contract in order, beyond-horizon average over the non-zero months of H). No month
   variable: T6 is handled by an instruction to ask for the month. Refused units are not exposed. At most three
   verified queries, on background members only.
3. generated/agent_b2.yaml: the CREATE AGENT specification of LINKML_B2: one cortex_analyst_text_to_sql tool on
   LINKML_B2_SV, orchestration instructions generated from the contract, the response instruction common to every
   configuration (docs/configurations.md).
The output is deterministic: same contract and dataset, same bytes.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

try:
    from compiler import supported
except ImportError:                       # run as a script: compiler/ is on sys.path
    import supported

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "compiler"))
from gen_agent import (MODEL, WAREHOUSE, bare, basis_rule_sentence, clean, lower_first, valid_months,  # noqa: E402
                       view_bases, view_metric_note)

CONTRACT_PATH = ROOT / "contract" / "stock_coverage.yaml"
OUT_DIR = ROOT / "generated"
SCHEMA = "LINKML_METRICS.RAW"
ROLE = "LINKML_METRICS_ROLE"
SV_NAME = "LINKML_B2_SV"
AGENT = "LINKML_B2"
TOOL = "b2_semantic_view"
BUDGET = {"seconds": 120, "tokens": 40000}
BRIDGED = "batch_status"     # one bridge: two bridged attributes would need the product of their values (phase 0)
GAPFILLED = f"{SCHEMA}.FCT_STOCK_SNAPSHOT_GAPFILLED"   # compiler/gen_closing_sv.py
RESPONSE = ("Answer in two to five sentences. Say which month or period, which basis and which filters the figures "
            "refer to. Give only figures that a tool returned. If a tool returns a warning, a flag or a refusal, relay "
            "it with its number and explain it in business words. When you give a figure, end with one line: "
            "'Data freshness: <the latest month with stock data>', taken from what a tool returned.")
# common to every configuration (charter v7; v8: basis, not unit; v10: the data freshness line)
UNIT_SUFFIX = {"QTY_EQ": "qty_eq", "VALUE": "value"}
VERIFIED = {   # background members only, never a hero of data/traps.yaml
    "family": "SNACK_CRISPS", "country": "DE", "quarter": (2026, 1), "forecast": ("PANTRY_RICE", "IT", "2026-08-01"),
}


def unit_cols(c: dict) -> dict[str, dict[str, str]]:
    """measure basis -> {measure id: column}, the bases a view can expose (contract 0.5.0: QTY_EQ and VALUE; the
    item's own unit is valid for one item only and is never exposed)."""
    allowed = [b["id"] for b in view_bases(c)]
    return {u: {m["id"]: next(x["column"] for x in m["columns"] if x["basis"] == u) for m in c["measures"]}
            for u in allowed}


def note(c: dict, u: str) -> str:
    return view_metric_note(c, next(b for b in c["measure_bases"] if b["id"] == u))


def build(c: dict) -> dict:
    supported.check(c, "gen_native_sv")
    metric = c["metrics"][0]
    measures = {m["id"]: m for m in c["measures"]}
    snap, flow = measures[metric["snapshot_measure"]], measures[metric["flow_measure"]]
    tables = {t["id"]: t for t in c["tables"]}
    item_attrs = [a for a in c["attributes"] if a["table"] == "DIM_ITEM"]
    bridged = next(a for a in c["attributes"] if a["id"] == BRIDGED)
    if bridged["applicability_class"] != "SNAPSHOT_ONLY":
        raise ValueError(f"{BRIDGED} must be SNAPSHOT_ONLY")
    if not any(q["table"] == "DIM_ITEM" and q["on_failure"] == "REFUSE_IF_USED" for q in c["quality_expectations"]):
        raise ValueError("no REFUSE_IF_USED quality expectation on DIM_ITEM")
    return {"c": c, "metric": metric, "snap": snap, "flow": flow, "tables": tables, "item_attrs": item_attrs,
            "bridged": bridged, "h": metric["horizon_periods"], "k0": metric["window_start_offset"],
            "units": unit_cols(c), "months": valid_months(c)}


# ------------------------------------------------------------------------------------------------ views

def views_sql(b: dict) -> str:
    c, h, k0 = b["c"], b["h"], b["k0"]
    flow, snap = b["flow"], b["snap"]
    cols = list(dict.fromkeys(["item_id"] + [x for a in b["item_attrs"] for x in (a["column"], a.get("label_column"))
                                              if x]))
    bt = b["tables"][b["bridged"]["table"]]
    fcols = []
    for u, m in b["units"].items():
        for k in range(k0, k0 + h):
            fcols.append(f"SUM(IFF(DATEDIFF(month, v.m, f.{flow['time_column']}) = {k}, f.{m[flow['id']]}, 0)) "
                         f"AS f{k:02d}_{UNIT_SUFFIX[u]}")
    fsel = ",\n       ".join(fcols)
    head = [
        f"-- GENERATED from contract/stock_coverage.yaml (contract {c['id']}, version {c['version']})",
        "-- by compiler/gen_native_sv.py. Do not edit: change the contract and run `python compiler/gen_native_sv.py`.",
        "-- tests/test_generated.py regenerates this file and fails on any difference.",
        "-- Configuration B2 (session 8): the physical views LINKML_B2_SV reads. Run as the project role with no",
        "-- secondary role. FCT_STOCK_SNAPSHOT_GAPFILLED comes from generated/closing_stock_sv.sql.",
        "USE SECONDARY ROLES NONE;",
        f"USE ROLE {ROLE};",
        "",
    ]
    item = (f"CREATE OR REPLACE VIEW {SCHEMA}.B2_ITEM\n"
            f"  COMMENT = 'Generated from contract {c['id']} {c['version']}: distinct item rows on the item attributes. "
            f"The declared grain item_id is checked by a REFUSE_IF_USED expectation, which a semantic view cannot "
            f"enforce: an item whose rows differ on an attribute keeps two rows.'\n"
            f"AS\nSELECT DISTINCT {', '.join(cols)}\nFROM {SCHEMA}.DIM_ITEM;\n")
    status = (f"CREATE OR REPLACE VIEW {SCHEMA}.B2_STATUS\n"
              f"  COMMENT = 'Generated from contract {c['id']} {c['version']}: the values of the bridged stock-only "
              f"attribute {b['bridged']['id']}.'\n"
              f"AS\nSELECT DISTINCT {b['bridged']['column']} FROM {SCHEMA}.{bt['id']};\n")
    period = c["analysis_periods"][0]
    spine = (
        f"CREATE OR REPLACE VIEW {SCHEMA}.B2_FORECAST_SPINE\n"
        f"  COMMENT = 'Generated from contract {c['id']} {c['version']}: forward spine of {b['metric']['id']}, one row per "
        f"valid analysis month x item x country x {b['bridged']['id']} (status bridge), flow of t+{k0}..t+{k0 + h - 1} as "
        f"columns, missing months 0.'\n"
        f"AS\nWITH snaps AS (SELECT DISTINCT {period['source_column']} AS m FROM {SCHEMA}.{period['source_table']}),\n"
        f"reach AS (SELECT (SELECT MAX(month_start) FROM {SCHEMA}.DIM_CALENDAR) AS cal_max,\n"
        f"                 (SELECT MAX({flow['time_column']}) FROM {SCHEMA}.{flow['table']}) AS fc_max),\n"
        f"v AS (SELECT m FROM snaps, reach WHERE cal_max >= DATEADD(month, {h}, m) AND fc_max >= DATEADD(month, {h}, m)),\n"
        f"st AS (SELECT DISTINCT {b['bridged']['column']} FROM {SCHEMA}.{bt['id']})\n"
        f"SELECT v.m AS as_of_month, f.item_id, f.country_id, st.{b['bridged']['column']},\n       {fsel}\n"
        f"FROM v\nJOIN {SCHEMA}.{flow['table']} f\n"
        f"  ON f.{flow['time_column']} >= DATEADD(month, {k0}, v.m) AND f.{flow['time_column']} <= DATEADD(month, {k0 + h - 1}, v.m)\n"
        f"CROSS JOIN st\nGROUP BY v.m, f.item_id, f.country_id, st.{b['bridged']['column']};\n")
    return "\n".join(head) + item + "\n" + status + "\n" + spine


# ------------------------------------------------------------------------------------------------ semantic view

def coverage_expr(b: dict, u: str) -> str:
    """The contract's outcomes in order over the cumulative forward metrics (DEFINITION.md section 2)."""
    s, k0, h = f"stock.closing_stock_{UNIT_SUFFIX[u]}", b["k0"], b["h"]
    cum = lambda n: f"fwd.cum_{UNIT_SUFFIX[u]}_{n:02d}"       # noqa: E731
    mon = lambda n: f"fwd.month_{UNIT_SUFFIX[u]}_{n:02d}"     # noqa: E731
    out = ["CASE",
           f"  WHEN {s} IS NULL OR {s} = 0 THEN 0",
           f"  WHEN {cum(h)} IS NULL OR {cum(h)} = 0 THEN NULL",
           f"  WHEN {s} <= {cum(1)} THEN {s} / {cum(1)}"]
    for n in range(2, h + 1):
        out.append(f"  WHEN {s} <= {cum(n)} THEN {n - 1} + ({s} - {cum(n - 1)}) / ({cum(n)} - {cum(n - 1)})")
    nz = " + ".join(f"IFF({mon(n)} > 0, 1, 0)" for n in range(1, h + 1))
    out.append(f"  ELSE {s} / ({cum(h)} / ({nz}))")
    out.append("END")
    return "\n".join(out)


def dim(name: str, expr: str, desc: str | None = None, data_type: str | None = None) -> dict:
    d = {"name": name, "expr": expr}
    if desc:
        d["description"] = clean(desc)
    if data_type:
        d["data_type"] = data_type
    return d


def sv(b: dict) -> dict:
    c, metric, snap, flow, h = b["c"], b["metric"], b["snap"], b["flow"], b["h"]

    def attr_dims(table_id: str) -> list[dict]:
        out = []
        for a in c["attributes"]:
            if a["table"] != table_id:
                continue
            cls = "conformed: applies to stock and forecast alike" if a["applicability_class"] == "CONFORMED" else \
                "stock-only: restricts the stock, never the forecast"
            extra = f" Known values: {', '.join(a['known_values'])}." if a.get("known_values") else ""
            out.append(dim(a["id"], a["column"], f"{a.get('description') or a['id']} ({cls}).{extra}"))
            if a.get("label_column"):
                out.append(dim(a["label_column"], a["label_column"], f"Name of {a['id']}."))
        return out

    item_t = {"name": "item", "description": clean(
        "Items: SKU, family, range, item type and lifecycle status. One row per distinct combination of the item key and "
        "its attributes; an item recorded twice with different attributes keeps two rows."),
        "base_table": {"database": "LINKML_METRICS", "schema": "RAW", "table": "B2_ITEM"},
        "primary_key": {"columns": ["item_id"]}, "dimensions": attr_dims("DIM_ITEM")}
    geo_t = {"name": "geo", "description": "Countries and regions.",
             "base_table": {"database": "LINKML_METRICS", "schema": "RAW", "table": "DIM_GEO"},
             "primary_key": {"columns": ["country_id"]}, "dimensions": attr_dims("DIM_GEO")}
    cal_t = {"name": "calendar", "description": clean(
        "Calendar months. For stock coverage, month_start is the analysis month: filter it on exactly one month. For "
        "closing stock over a period, filter or group by year_quarter, year or a range of month_start."),
        "base_table": {"database": "LINKML_METRICS", "schema": "RAW", "table": "DIM_CALENDAR"},
        "primary_key": {"columns": ["month_start"]},
        "dimensions": [dim("month_start", "month_start", "First day of the month (the analysis month for coverage).",
                           "DATE"),
                       dim("year_quarter", "year || '-Q' || quarter", "Calendar quarter, for example 2026-Q2."),
                       dim("year", "year", "Calendar year.")]}
    batch_t = {"name": "batch", "description": "Supplier lots (batches) of the stock.",
               "base_table": {"database": "LINKML_METRICS", "schema": "RAW", "table": "DIM_BATCH"},
               "primary_key": {"columns": ["batch_id"]}}
    status_t = {"name": "status", "description": clean(
        f"Values of {b['bridged']['id']}, reached by the stock through its lot and by the forward forecast through its "
        f"per-status replicas: a filter on it restricts the stock only."),
        "base_table": {"database": "LINKML_METRICS", "schema": "RAW", "table": "B2_STATUS"},
        "primary_key": {"columns": [b["bridged"]["column"]]}, "dimensions": attr_dims(b["bridged"]["table"])}
    wh_t = {"name": "warehouse", "description": "Warehouses holding the stock (stock-only attributes).",
            "base_table": {"database": "LINKML_METRICS", "schema": "RAW", "table": "DIM_WAREHOUSE"},
            "primary_key": {"columns": ["warehouse_id"]}, "dimensions": attr_dims("DIM_WAREHOUSE")}
    pa = snap["period_aggregation"]
    forbidden = ", ".join(x.lower() for x in pa["forbidden_methods"])
    stock_metrics = []
    for u, m in b["units"].items():
        stock_metrics.append({
            "name": f"closing_stock_{UNIT_SUFFIX[u]}",
            "description": clean(f"Stock on hand {note(c, u)}: "
                                 f"the snapshot of the latest month in the query, summed over items, countries, lots and "
                                 f"warehouses. {pa['description']} Never {forbidden} over time. For coverage it is the "
                                 f"stock at the analysis month."),
            "expr": f"SUM({m[snap['id']]})",
            "non_additive_dimensions": [{"table": "stock", "dimension": snap["time_column"],
                                         "sort_direction": "ascending", "null_order": "last"}]})
    stock_t = {"name": "stock", "description": clean(
        f"{snap['description']} Gap-filled: a lot and warehouse with no snapshot in a month of its span counts 0 that month."),
        "base_table": {"database": "LINKML_METRICS", "schema": "RAW", "table": "FCT_STOCK_SNAPSHOT_GAPFILLED"},
        "primary_key": {"columns": ["snapshot_month", "batch_id", "warehouse_id"]},
        "dimensions": attr_dims("FCT_STOCK_SNAPSHOT") + [
            dim(snap["time_column"], snap["time_column"], "Snapshot month of the stock.", "DATE"),
            dim("gap_filled", "gap_filled", "TRUE on a row added by the gap fill (stock 0).", "BOOLEAN")],
        "metrics": stock_metrics}
    flow_metrics = [{"name": f"forecast_{UNIT_SUFFIX[u]}",
                     "description": clean(f"{flow['description']} Summed over the months, items and countries of "
                                          f"the query, {note(c, u)}."), "expr": f"SUM({m[flow['id']]})"} for u, m in b["units"].items()]
    flow_t = {"name": "forecast", "description": clean(flow["description"]),
              "base_table": {"database": "LINKML_METRICS", "schema": "RAW", "table": flow["table"]},
              "primary_key": {"columns": b["tables"][flow["table"]]["grain"]},
              "dimensions": [dim(flow["time_column"], flow["time_column"], "Forecast month.", "DATE")],
              "metrics": flow_metrics}
    fwd_metrics = []
    for u in b["units"]:
        sfx = UNIT_SUFFIX[u]
        for n in range(1, h + 1):
            fwd_metrics.append({"name": f"cum_{sfx}_{n:02d}", "access_modifier": "private_access",
                                "expr": f"SUM({' + '.join(f'f{j:02d}_{sfx}' for j in range(1, n + 1))}) / "
                                        f"COUNT(DISTINCT {b['bridged']['column']})"})
        for n in range(1, h + 1):
            fwd_metrics.append({"name": f"month_{sfx}_{n:02d}", "access_modifier": "private_access",
                                "expr": f"SUM(f{n:02d}_{sfx}) / COUNT(DISTINCT {b['bridged']['column']})"})
    fwd_t = {"name": "fwd", "description": clean(
        f"Forward forecast spine: for each valid analysis month, the forecast of the {h} following months by item and "
        f"country, missing months 0, replicated once per {b['bridged']['id']} value (every metric divides the "
        f"replication back out). Used by the coverage metrics only."),
        "base_table": {"database": "LINKML_METRICS", "schema": "RAW", "table": "B2_FORECAST_SPINE"},
        "primary_key": {"columns": ["as_of_month", "item_id", "country_id", b["bridged"]["column"]]},
        "metrics": fwd_metrics}
    rels = [
        ("stock_item", "stock", "item", "item_id", "item_id"), ("stock_geo", "stock", "geo", "country_id", "country_id"),
        ("stock_calendar", "stock", "calendar", "snapshot_month", "month_start"),
        ("stock_batch", "stock", "batch", "batch_id", "batch_id"),
        ("stock_warehouse", "stock", "warehouse", "warehouse_id", "warehouse_id"),
        ("batch_status", "batch", "status", b["bridged"]["column"], b["bridged"]["column"]),
        ("forecast_item", "forecast", "item", "item_id", "item_id"),
        ("forecast_geo", "forecast", "geo", "country_id", "country_id"),
        ("forecast_calendar", "forecast", "calendar", flow["time_column"], "month_start"),
        ("fwd_item", "fwd", "item", "item_id", "item_id"), ("fwd_geo", "fwd", "geo", "country_id", "country_id"),
        ("fwd_calendar", "fwd", "calendar", "as_of_month", "month_start"),
        ("fwd_status", "fwd", "status", b["bridged"]["column"], b["bridged"]["column"]),
    ]
    flags = "; ".join(f"{f['id']}: {bare(f['description'])}, {lower_first(f['value_semantics'])}" for f in c["flags"])
    view_metrics = []
    for u in b["units"]:
        sfx = UNIT_SUFFIX[u]
        view_metrics.append({
            "name": f"coverage_months_{sfx}", "synonyms": [s for s in metric["synonyms"]] if u == "QTY_EQ" else [],
            "description": clean(
                f"Stock coverage, always in months; stock and forecast measured {note(c, u)}: "
                f"{lower_first(metric['description'])} Recomputed from the stock and the "
                f"forward forecast aggregated at the queried grain; never add or average it across rows. Filter "
                f"calendar.month_start on exactly one analysis month. Outcomes: {flags}."),
            "expr": coverage_expr(b, u)})
    return {"name": SV_NAME,
            "description": clean(f"Configuration B2, generated from contract {c['id']} {c['version']}: stock coverage, "
                                 f"closing stock and demand forecast of the grocery dataset."),
            "tables": [item_t, geo_t, cal_t, batch_t, status_t, wh_t, stock_t, flow_t, fwd_t],
            "relationships": [{"name": n, "left_table": lt, "right_table": rt,
                               "relationship_columns": [{"left_column": lc, "right_column": rc}]}
                              for n, lt, rt, lc, rc in rels],
            "metrics": view_metrics,
            "verified_queries": verified_queries(b)}


def verified_queries(b: dict) -> list[dict]:
    fam, cc = VERIFIED["family"], VERIFIED["country"]
    y, q = VERIFIED["quarter"]
    last = f"{y}-{3 * q:02d}-01"
    ffam, fcc, fmonth = VERIFIED["forecast"]
    return [
        {"name": "closing_stock_family_country_quarter",
         "question": f"What was the closing stock of family {fam} in {cc} for {y}-Q{q}, in kg equivalent?",   # MASS family
         "sql": (f"-- closing stock of a quarter = the snapshot of its last month ({last}), absent = 0 (gap-filled)\n"
                 f"SELECT i.family_code, g.country_code, SUM(s.stock_qty_eq) AS closing_stock_qty_eq\n"
                 f"FROM __stock AS s\nJOIN __item AS i ON s.item_id = i.item_id\n"
                 f"JOIN __geo AS g ON s.country_id = g.country_id\n"
                 f"WHERE i.family_code = '{fam}' AND g.country_code = '{cc}' AND s.snapshot_month = '{last}'\n"
                 f"GROUP BY i.family_code, g.country_code")},
        {"name": "forecast_family_country_month",
         "question": f"What is the demand forecast of family {ffam} in {fcc} for {fmonth[:7]}, in kg equivalent?",   # MASS
         "sql": (f"SELECT i.family_code, g.country_code, SUM(f.forecast_qty_eq) AS forecast_qty_eq\n"
                 f"FROM __forecast AS f\nJOIN __item AS i ON f.item_id = i.item_id\n"
                 f"JOIN __geo AS g ON f.country_id = g.country_id\n"
                 f"WHERE i.family_code = '{ffam}' AND g.country_code = '{fcc}' AND f.forecast_month = '{fmonth}'\n"
                 f"GROUP BY i.family_code, g.country_code")},
    ]


# ------------------------------------------------------------------------------------------------ agent

def tool_description(b: dict) -> str:
    months = b["months"]
    return clean(f"""
        Semantic view {SCHEMA}.{SV_NAME} of the grocery dataset: stock on hand and closing stock by item, family,
        range, country, region, lot status, expiry bucket and warehouse; monthly demand forecast by item and country;
        stock coverage in months (coverage_months_qty_eq, coverage_months_value) for one analysis month. Analysis months
        {months[0].isoformat()} to {months[-1].isoformat()}; the latest stock snapshot is {months[-1].strftime('%B %Y')}.
        Use it for every question on stock, closing stock, forecast or coverage.""")


def orchestration(b: dict) -> str:
    c, metric, months = b["c"], b["metric"], b["months"]
    totals = c["totals_rules"][0]
    scope = c["default_scopes"][0]
    pa = b["snap"]["period_aggregation"]
    snap_only = ", ".join(a["id"] for a in c["attributes"] if a["applicability_class"] == "SNAPSHOT_ONLY")
    # B2 has no warning mechanism: the scope's warning sentence is left out rather than promised.
    # Charter version 11 (session 8c): the grain rule of charter version 9 (member_selection.grain_rule), which this
    # generator had missed; tests/test_charter_conformity.py.
    scope_text = " ".join(s for s in re.split(r"(?<=\.)\s+", clean(scope["description"])) if "warning" not in s.lower())
    return clean(f"""
        Stock coverage ({', '.join(metric['synonyms'])}): {lower_first(metric['description'])} If nothing is replenished,
        how many months the stock on hand at the analysis month lasts against the demand forecast of the next
        {b['h']} months. Use the metric coverage_months_qty_eq, or coverage_months_value when the user asks for value
        or when the items of the question combine kg and L, with calendar.month_start filtered on exactly one analysis
        month. Coverage is measured at one analysis month: if
        the user gives no month, or gives a period (a year, a quarter, a range of months), do not choose one; ask which
        month, and say that the latest available month is {months[-1].strftime('%B %Y')}. Valid analysis months:
        {months[0].isoformat()} to {months[-1].isoformat()}. Coverage is not additive: {lower_first(totals['description'])}
        Never add or average coverage rows; query the coarser grain instead. {clean(metric['member_selection']['grain_rule'])}
        Raw pack counts are not exposed: the packs of different items never add up, and kg and L never add up.
        By default {scope_text} Filter item_type on STANDARD for coverage unless the user filters
        item_type. Stock-only attributes ({snap_only}) restrict the stock, never the forecast; {b['bridged']['id']} can
        be combined with coverage. {internal(pa['description'])} Use
        closing_stock_qty_eq or closing_stock_value with the period (calendar.year_quarter, calendar.year, or a range of
        calendar.month_start); closing stock counts every item type. Forecast questions use forecast_qty_eq or
        forecast_value. {basis_rule_sentence(c)} Use attribute codes in filters (Germany is DE).""")


def internal(text: str) -> str:
    """clean() without the contract's references to the article and to repository files."""
    return re.sub(r"\s*\((?:step \d of the article|[^)]*data/traps\.yaml[^)]*)[^)]*\)", "", clean(text))


def agent(b: dict) -> dict:
    return {
        "models": {"orchestration": MODEL},
        "orchestration": {"budget": dict(BUDGET), "tool_not_accessible": "reject"},
        "instructions": {"orchestration": orchestration(b), "response": RESPONSE},
        "tools": [{"tool_spec": {"type": "cortex_analyst_text_to_sql", "name": TOOL, "description": tool_description(b)}}],
        "tool_resources": {TOOL: {"semantic_view": f"{SCHEMA}.{SV_NAME}",
                                  "execution_environment": {"type": "warehouse", "warehouse": WAREHOUSE,
                                                            "query_timeout": 120}}},
    }


def header(c: dict, what: str) -> str:
    return (f"# GENERATED from contract/stock_coverage.yaml (contract {c['id']}, version {c['version']}) and data/output/\n"
            "# by compiler/gen_native_sv.py. Do not edit: change the contract and run `python compiler/gen_native_sv.py`.\n"
            "# tests/test_generated.py regenerates this file and fails on any difference.\n"
            f"# {what}\n")


def render(c: dict) -> dict[str, str]:
    b = build(c)
    dump = lambda d: yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=118)   # noqa: E731
    return {
        "b2_native_views.sql": views_sql(b),
        "b2_native_sv.yaml": header(c, f"Configuration B2: semantic view {SCHEMA}.{SV_NAME}, deployed after enrichment "
                                       "(snowflake/phase4_others/b2/).") + dump(sv(b)),
        "agent_b2.yaml": header(c, f"Configuration B2: permanent agent {SCHEMA}.{AGENT}, created as {ROLE} and called as "
                                   "LINKML_SVC.") + dump(agent(b)),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    a = p.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in render(yaml.safe_load(a.contract.read_text())).items():
        (a.out_dir / name).write_text(text)
        print(f"wrote {a.out_dir / name}")


if __name__ == "__main__":
    main()
