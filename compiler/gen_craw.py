"""
Tenth generator (session 13, owner 2026-10-08): configuration C-raw, the contract without any reshaped data.

    python compiler/gen_craw.py                       # writes the two files into generated/
    python compiler/gen_craw.py --out-dir /tmp/craw   # writes elsewhere (the drift test uses this)

Two files:
1. generated/c_raw_sv.yaml: the semantic view LINKML_C_RAW_SV (model YAML, deployed with
   CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML). The raw fact and dimension tables only, each fact joined to the
   dimensions it references: no gap-filled snapshot, no forward spine, no projection of the item dimension. Stock on
   hand per comparable basis NON ADDITIVE BY the snapshot month (one month's stock); the forecast as a flow. No
   coverage metric and no closing-stock metric: the descriptions route both to the procedures. No verified query.
   Value grounding (is_enum, sample_values) equal to C's: each dimension shared with B2's enriched view, as deployed
   (snowflake/phase4_others/b2/LINKML_B2_SV_enriched.yaml), takes its grounding from that file.
2. generated/agent_c_raw.yaml: the CREATE AGENT specification of LINKML_C_RAW. Three tools: the view, the
   stock_coverage tool of agent C unchanged (procedure STOCK_COVERAGE), and closing_stock (procedure CLOSING_STOCK,
   compiler/gen_closing_procedure.py). Orchestration: agent C's generated instructions with the view's name, its
   routing sentence for stock and closing stock replaced by the closing-stock routing rule; response: the instruction
   common to every configuration.
The output is deterministic: same contract and dataset, same bytes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "compiler"))
import gen_agent as ga  # noqa: E402
import gen_closing_procedure as gcp  # noqa: E402
import gen_native_sv as nsv  # noqa: E402
import supported  # noqa: E402

CONTRACT_PATH = ROOT / "contract" / "stock_coverage.yaml"
OUT_DIR = ROOT / "generated"
SCHEMA = "LINKML_METRICS.RAW"
SV_NAME = "LINKML_C_RAW_SV"
AGENT = "LINKML_C_RAW"
TOOL = "c_raw_semantic_view"
CLOSING_TOOL = "closing_stock"
GENERATOR = "gen_craw"
# Owner, session 13 step 3: equal grounding with C, which reads B2's view as deployed (enriched, decision 5 of session 8)
B2_ENRICHED = ROOT / "snowflake" / "phase4_others" / "b2" / "LINKML_B2_SV_enriched.yaml"
GROUNDING = ("is_enum", "sample_values")
LOGICAL = {"FCT_STOCK_SNAPSHOT": "stock", "FCT_FORECAST": "forecast", "DIM_ITEM": "item", "DIM_GEO": "geo",
           "DIM_BATCH": "batch", "DIM_WAREHOUSE": "warehouse", "DIM_CALENDAR": "calendar"}
ROUTE_C = "Route questions on stock on hand, closing stock and demand forecast to {view}."
ROUTE_CLOSING = (f"Route every closing stock question (the stock at the end of a month, a quarter, a year or a range of "
                 f"months, at any grain), including a follow-up on closing stock, to {CLOSING_TOOL}. Route questions on "
                 f"stock on hand at one month and on demand forecast to {TOOL}.")


def snapshot_months(c: dict) -> list[dt.date]:
    snap = next(m for m in c["measures"] if m.get("period_aggregation"))
    col = snap["time_column"]
    return sorted({pd.Timestamp(x).date() for x in pd.read_parquet(ga.DATA / f"{snap['table']}.parquet", columns=[col])[col]})


# ------------------------------------------------------------------------------------------------ the view

def sv(c: dict) -> dict:
    supported.check(c, GENERATOR)
    measures = {m["id"]: m for m in c["measures"]}
    snap = next(m for m in c["measures"] if m.get("period_aggregation"))
    flow = next(m for m in c["measures"] if m["measure_type"] == "FLOW")
    tables = {t["id"]: t for t in c["tables"]}
    bases = [b["id"] for b in ga.view_bases(c)]
    col = lambda m, u: next(x["column"] for x in m["columns"] if x["basis"] == u)   # noqa: E731
    sfx = nsv.UNIT_SUFFIX

    def attr_dims(table_id: str) -> list[dict]:
        out = []
        for a in c["attributes"]:
            if a["table"] != table_id:
                continue
            cls = "conformed: applies to stock and forecast alike" if a["applicability_class"] == "CONFORMED" else \
                "stock-only: restricts the stock, never the forecast"
            extra = f" Known values: {', '.join(a['known_values'])}." if a.get("known_values") else ""
            out.append(nsv.dim(a["id"], a["column"], f"{a.get('description') or a['id']} ({cls}).{extra}"))
            if a.get("label_column"):
                out.append(nsv.dim(a["label_column"], a["label_column"], f"Name of {a['id']}."))
        return out

    routed = (f"Closing stock over a period is computed by the {CLOSING_TOOL} tool and coverage by the stock_coverage "
              f"tool, never here.")
    out_tables = []
    for tid in ("DIM_ITEM", "DIM_GEO", "DIM_CALENDAR", "DIM_BATCH", "DIM_WAREHOUSE", snap["table"], flow["table"]):
        t = {"name": LOGICAL[tid], "base_table": {"database": "LINKML_METRICS", "schema": "RAW", "table": tid},
             "primary_key": {"columns": tables[tid]["grain"]}}
        if tid == "DIM_ITEM":
            t["description"] = "Items: SKU, family, range, item type, lifecycle status and dimension (kg or L)."
        elif tid == "DIM_GEO":
            t["description"] = "Countries and regions."
        elif tid == "DIM_CALENDAR":
            t["description"] = ga.clean("Calendar months. For stock on hand, filter month_start or the snapshot month on "
                                        "exactly one month.")
        elif tid == "DIM_BATCH":
            t["description"] = "Supplier lots (batches) of the stock."
        elif tid == "DIM_WAREHOUSE":
            t["description"] = "Warehouses holding the stock (stock-only attributes)."
        if tid == "DIM_CALENDAR":
            t["dimensions"] = [nsv.dim("month_start", "month_start", "First day of the month.", "DATE"),
                               nsv.dim("year_quarter", "year || '-Q' || quarter", "Calendar quarter, for example 2026-Q2."),
                               nsv.dim("year", "year", "Calendar year.")]
        elif tid == snap["table"]:
            t["description"] = ga.clean(f"{snap['description']} One row per snapshot month, lot and warehouse; a month "
                                        f"with no row has no stock. {routed}")
            t["dimensions"] = attr_dims(tid) + [nsv.dim(snap["time_column"], snap["time_column"],
                                                        "Snapshot month of the stock.", "DATE")]
            t["metrics"] = [{
                "name": f"stock_on_hand_{sfx[u]}",
                "description": ga.clean(f"Stock on hand {nsv.note(c, u)}: the snapshot of one month, summed over items, "
                                        f"countries, lots and warehouses; filter {snap['time_column']} on exactly one "
                                        f"month. A level, never summed over months. {routed}"),
                "expr": f"SUM({col(snap, u)})",
                "non_additive_dimensions": [{"table": LOGICAL[tid], "dimension": snap["time_column"],
                                             "sort_direction": "ascending", "null_order": "last"}]} for u in bases]
        elif tid == flow["table"]:
            t["description"] = ga.clean(flow["description"])
            t["dimensions"] = [nsv.dim(flow["time_column"], flow["time_column"], "Forecast month.", "DATE")]
            t["metrics"] = [{"name": f"forecast_{sfx[u]}",
                             "description": ga.clean(f"{flow['description']} Summed over the months, items and countries "
                                                     f"of the query, {nsv.note(c, u)}."),
                             "expr": f"SUM({col(flow, u)})"} for u in bases]
        else:
            dims = attr_dims(tid)
            if dims:
                t["dimensions"] = dims
        out_tables.append(t)
    ground = {d["name"]: {k: d[k] for k in GROUNDING if k in d}
              for t in yaml.safe_load(B2_ENRICHED.read_text())["tables"] for d in t.get("dimensions", [])}
    for t in out_tables:
        for d in t.get("dimensions", []):
            d.update(ground.get(d["name"], {}))
    rels = [r for r in c["relationships"] if r["from_table"] in (snap["table"], flow["table"])
            and r["cardinality"] == "MANY_TO_ONE"]
    del measures
    return {"name": SV_NAME,
            "description": ga.clean(f"Configuration C-raw, generated from contract {c['id']} {c['version']}: stock on "
                                    f"hand at one month and demand forecast of the grocery dataset, on its raw tables. "
                                    f"{routed}"),
            "tables": out_tables,
            "relationships": [{"name": f"{LOGICAL[r['from_table']]}_{LOGICAL[r['to_table']]}",
                               "left_table": LOGICAL[r["from_table"]], "right_table": LOGICAL[r["to_table"]],
                               "relationship_columns": [{"left_column": lc, "right_column": rc}
                                                        for lc, rc in zip(r["from_columns"], r["to_columns"])]}
                              for r in rels]}


# ------------------------------------------------------------------------------------------------ the agent

def closing_tool(c: dict) -> dict:
    b = gcp.build(c)
    months = snapshot_months(c)
    bm = c["basis_model"]
    valid = {"ONE_ITEM_PER_ROW": "valid when each row holds one item",
             "ONE_DIMENSION_PER_ROW": "valid when each row and total holds items of one dimension",
             "ALWAYS": "always valid"}
    basis_text = "; ".join(f"{x['id']} = {ga.bare(x['description'])}, {valid[x['valid_when']]}"
                           + (", default" if x["id"] == bm["default_basis"] else "") for x in c["measure_bases"])
    latest = b["latest_token"]
    description = ga.clean(f"""
        {gcp.note(b)} This tool computes every number; you never add, average or carry a closing stock yourself: for a
        coarser group, call the tool again with that coarser grain, or ask for it in totals. Periods: {gcp.FORMS}. A
        period with a month that has no stock snapshot is refused, never guessed. Snapshot months:
        {months[0].isoformat()} to {months[-1].isoformat()}, monthly; {latest} = {months[-1].isoformat()}. Bases (the
        unit of the stock): {basis_text}. A basis the rows returned cannot sum is refused with {bm['refusal']}, which
        names the bases allowed. Closing stock counts every item type. Each result row carries period, first_month,
        last_month (the month read), row_type (DETAIL or TOTAL), the grain attributes, closing_stock (in stock_unit),
        stock_unit and closed_without_snapshot (true when the member has no snapshot in the last month, so it closes at
        0). The answer also carries request.periods (the months actually used), warnings (each with its number), the
        first and last available months with {latest}, and the query ids of its statements (lineage, not for the
        user). A result with status "refused" carries a refusal code and a reason: relay the reason, do not work
        around it.""")
    conformed, snapshot_only = ga.attribute_lists(c)
    params = {p["id"]: p for p in c["parameters"]}
    grain_ex, filters_ex = params["grain"]["example"], params["filters"]["example"]
    props = {
        "periods": {"type": "string", "description": ga.clean(
            f"Required, passed as a string. {gcp.PARAMS[0][2].format(forms=gcp.FORMS)} 'Q2 2026' "
            f"is [\"2026-Q2\"], 'end of June 2026' is [\"2026-06-01\"], 'each month of Q2 2026' is [\"2026-04-01\", "
            f"\"2026-05-01\", \"2026-06-01\"]. Example: [\"2026-Q2\"]")},
        "grain": {"type": "string", "description": ga.clean(
            f"Required, passed as a string. {gcp.PARAMS[1][2]} Conformed attributes: {conformed}. Stock-only attributes: {snapshot_only}. "
            f"Example: {grain_ex}")},
        "filters": {"type": "string", "description": ga.clean(
            f"Required, passed as a string. {gcp.PARAMS[2][2].format()} Same attributes and codes as grain: codes, never names (Germany is "
            f"DE, cereal bars is SNACK_BARS). Example: {filters_ex}")},
        "basis": {"type": "string", "description": ga.clean(
            f"Optional, default {bm['default_basis']}. {gcp.PARAMS[3][2]} Example: {bm['default_basis']}")},
        "totals": {"type": "string", "description": ga.clean(
            f"Optional, default [], passed as a string. {gcp.PARAMS[4][2]} Example: [[\"country_code\"], []]")},
    }
    return {"type": "generic", "name": CLOSING_TOOL, "description": description,
            "input_schema": {"type": "object", "properties": props, "required": ["periods", "grain", "filters"]}}


def agent(c: dict) -> dict:
    supported.check(c, GENERATOR)
    base = ga.build(c)                                       # agent C, as compiler/gen_agent.py generates it
    view_c, cov = base["tools"][0]["tool_spec"], base["tools"][1]["tool_spec"]
    months = snapshot_months(c)
    orch = " ".join(base["instructions"]["orchestration"].split())
    route_c = ROUTE_C.format(view=view_c["name"])
    if orch.count(route_c) != 1:
        raise RuntimeError("agent C's routing sentence changed")
    orch = orch.replace(route_c, ROUTE_CLOSING).replace(view_c["name"], TOOL)
    orch += (" Closing stock over a period is the stock of its last month, 0 for a member with no snapshot that month: "
             f"never sum, average or carry it over months yourself, and never add closing stock rows; for a coarser "
             f"group call {CLOSING_TOOL} again at that grain, or ask for the total in totals. Pass the period the user "
             f"names (a year, a quarter, a month or a range of months); if {CLOSING_TOOL} refuses a period whose months "
             f"are not all loaded, relay the refusal and never pick another period.")
    view_tool = {"type": "cortex_analyst_text_to_sql", "name": TOOL, "description": ga.clean(f"""
        Semantic view {SCHEMA}.{SV_NAME} of the grocery dataset, on its raw tables: stock on hand at one month by item,
        family, range, country, region, lot status, expiry bucket and warehouse; monthly demand forecast by item and
        country. Snapshot months {months[0].isoformat()} to {months[-1].isoformat()}; the latest stock snapshot is
        {months[-1].strftime('%B %Y')}. Use it for stock on hand at one month and demand forecast questions; closing
        stock over a period is computed by the {CLOSING_TOOL} tool and coverage by the stock_coverage tool, never
        here.""")}
    res = base["tool_resources"]
    return {
        "models": base["models"],
        "orchestration": base["orchestration"],
        "instructions": {"orchestration": orch, "response": base["instructions"]["response"]},
        "tools": [{"tool_spec": view_tool}, {"tool_spec": cov}, {"tool_spec": closing_tool(c)}],
        "tool_resources": {TOOL: {"semantic_view": f"{SCHEMA}.{SV_NAME}",
                                  "execution_environment": dict(res[view_c["name"]]["execution_environment"])},
                           cov["name"]: res[cov["name"]],
                           CLOSING_TOOL: {"type": "procedure", "identifier": gcp.PROCEDURE,
                                          "execution_environment": dict(res[cov["name"]]["execution_environment"])}},
    }


def header(c: dict, what: str) -> str:
    return (f"# GENERATED from contract/stock_coverage.yaml (contract {c['id']}, version {c['version']}) and data/output/\n"
            "# by compiler/gen_craw.py. Do not edit: change the contract and run `python compiler/gen_craw.py`.\n"
            "# tests/test_c_raw.py regenerates this file and fails on any difference.\n"
            f"# {what}\n")


def render(c: dict) -> dict[str, str]:
    dump = lambda d: yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=118)   # noqa: E731
    return {
        "c_raw_sv.yaml": header(c, f"Configuration C-raw: semantic view {SCHEMA}.{SV_NAME} on the raw tables, deployed "
                                   "with CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML.") + dump(sv(c)),
        "agent_c_raw.yaml": header(c, f"Configuration C-raw: permanent agent {SCHEMA}.{AGENT}, created as "
                                      f"{nsv.ROLE} and called as LINKML_SVC. Three tools: the raw view, stock_coverage "
                                      f"({ga.PROCEDURE}) and {CLOSING_TOOL} ({gcp.PROCEDURE}).") + dump(agent(c)),
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
