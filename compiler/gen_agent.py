"""
Sixth generator: the contract's tool surface -> generated/agent_c.yaml (the CREATE AGENT specification of agent C).

    python compiler/gen_agent.py                         # writes generated/agent_c.yaml
    python compiler/gen_agent.py --out /tmp/agent.yaml   # writes elsewhere (the drift test uses this)

Two tools (session 8b): the B2 semantic view tool, with B2's generated description less its claim on coverage and
coverage routed to stock_coverage, for stock, closing stock and forecast; and one `generic` tool, stock_coverage, bound
to the generated procedure LINKML_METRICS.RAW.STOCK_COVERAGE (SQL Scripting since session 8b) on the project
warehouse. Orchestration: routing, the coverage rules and the contract's default unit; response: the instruction
common to every configuration (charter version 7); tool_not_accessible: reject. Everything the model reads comes from the contract: the tool description (the metric, the totals rule,
the flags, the refusal behaviour), the input_schema (one string property per parameter: lists and maps are JSON
strings, an array argument is rejected on a warehouse, probe C0), its examples, the attributes by applicability class
with their known values, and the instructions (never add or average coverage rows, ask for a coarser grain instead,
always name the analysis month used, relay every warning with its number, explain a refusal in business words).

The valid analysis months (LATEST, the first and the last) are compiled at generation from the loaded dataset
(data/output/), with the contract's validity rule: snapshot months whose horizon the calendar and the forecast reach.
The procedure reads the same list at call time and returns it in every answer.
The output is deterministic: same contract and dataset, same bytes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

import pandas as pd
import yaml

try:
    from compiler import supported
except ImportError:                       # run as a script: compiler/ is on sys.path
    import supported

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contract" / "stock_coverage.yaml"
DATA = ROOT / "data" / "output"
DEFAULT_OUT = ROOT / "generated" / "agent_c.yaml"
PROCEDURE = "LINKML_METRICS.RAW.STOCK_COVERAGE"
WAREHOUSE = "LINKML_METRICS_WH"
MODEL = "claude-sonnet-5-5"
BUDGET = {"seconds": 120, "tokens": 40000}      # probe C0's budget, kept for comparability
TOOL = "stock_coverage"
MAX_LABELLED = 30        # an attribute with a label column and at most this many codes lists them as code (name)


def month_add(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.month - 1 + n, 12)
    return dt.date(d.year + y, m + 1, 1)


def valid_months(c: dict) -> list[dt.date]:
    period = c["analysis_periods"][0]
    metric = c["metrics"][0]
    h = metric["horizon_periods"]
    measures = {m["id"]: m for m in c["measures"]}
    flow = measures[metric["flow_measure"]]

    def months(table, col):
        return sorted({pd.Timestamp(x).date() for x in pd.read_parquet(DATA / f"{table}.parquet", columns=[col])[col]})
    snaps = months(period["source_table"], period["source_column"])
    cal_max = months("DIM_CALENDAR", "month_start")[-1]
    fc_max = months(flow["table"], flow["time_column"])[-1]
    return [m for m in snaps if month_add(m, h) <= cal_max and month_add(m, h) <= fc_max]


def clean(text: str) -> str:
    """One line, without the contract's internal references (decisions, document sections), which mean nothing to
    the model."""
    t = " ".join(str(text).split())
    t = re.sub(r"\s*\((?:decision \d+|DEFINITION\.md[^)]*|SCOPE_ITEM_TYPE[^)]*)\)", "", t)
    return re.sub(r"\.\.", ".", t)


def bare(text: str) -> str:
    """clean() without the closing full stop, for a text followed by a comma or a semicolon in a list."""
    return clean(text).rstrip(".")


def lower_first(text: str) -> str:
    """A sentence continued after a colon starts in lower case."""
    t = clean(text)
    return t[:1].lower() + t[1:]


def view_bases(c: dict) -> list[dict]:
    """The measure bases a semantic view can expose: those comparable across items (an item's own unit is valid for
    one item only, so no view sums it). Contract 0.5.0."""
    return [b for b in c["measure_bases"] if b["valid_when"] != "ONE_ITEM_PER_ROW"]


def basis_units(c: dict, basis: dict) -> str:
    """The units a figure on this basis is given in: 'kg or L' for the base-unit equivalent, 'EUR' for a value."""
    if basis["unit_source"] == "FIXED":
        return basis["unit_symbol"]
    if basis["unit_source"] == "ITEM_BASE_UNIT":
        return " or ".join(d["base_unit"] for d in c["basis_model"]["dimensions"])
    return "the item's own unit"


def basis_rule_sentence(c: dict) -> str:
    """Charter version 8 (session 8c-0): the basis rule, one sentence for every configuration, generated from the
    contract's basis_model and measure_bases. It replaces the session 8 sentence that gave coverage in QTY_EQ."""
    bm, bases = c["basis_model"], {b["id"]: b for b in c["measure_bases"]}
    native = next(b for b in bases.values() if b["valid_when"] == "ONE_ITEM_PER_ROW")
    eq = next(b for b in bases.values() if b["valid_when"] == "ONE_DIMENSION_PER_ROW")
    val = next(b for b in bases.values() if b["valid_when"] == "ALWAYS")
    if bm["default_basis"] != eq["id"] or native["unit_source"] != "ITEM_NATIVE_UNIT":
        raise ValueError("basis_model.default_basis must be the ONE_DIMENSION_PER_ROW basis and the ONE_ITEM_PER_ROW "
                         "basis must take its unit from ITEM_NATIVE_UNIT")
    return (f"Coverage is always in {bm['result_unit']}. Stock and forecast are measured on one basis before the "
            f"ratio: the item's own unit for a single item; {basis_units(c, eq)} equivalent for items of the same "
            f"dimension, unless the question asks for value ({basis_units(c, val)}); value only when items of "
            f"different dimensions are combined. Closing stock and forecast follow the same basis rule.")


def view_metric_note(c: dict, basis: dict) -> str:
    """What a semantic view metric on this basis says about comparability (a view sums without complaint)."""
    if basis["valid_when"] == "ALWAYS":
        return f"in {basis_units(c, basis)}, comparable across every item"
    return (f"in {basis_units(c, basis)} equivalent; kg and L never add up: group or filter by dimension when items "
            f"of both dimensions are combined, or use the value metric")


def labels(c: dict) -> dict[str, list[tuple[str, str]]]:
    """attribute -> [(code, name)] from the dataset, for attributes with a label column and a small set of codes."""
    out = {}
    for a in c["attributes"]:
        if not a.get("label_column"):
            continue
        df = pd.read_parquet(DATA / f"{a['table']}.parquet", columns=[a["column"], a["label_column"]]).drop_duplicates()
        if df[a["column"]].nunique() <= MAX_LABELLED:
            out[a["id"]] = sorted(map(tuple, df.values.tolist()))
    return out


def attribute_lists(c: dict) -> tuple[str, str]:
    """The conformed and the snapshot-only attributes, each with its known values or its codes and names, as the
    tools' grain descriptions list them (session 13: shared with compiler/gen_craw.py)."""
    lab = labels(c)

    def attr_list(cls):
        out = []
        for a in c["attributes"]:
            if a["applicability_class"] != cls:
                continue
            kv = f" ({', '.join(a['known_values'])})" if a.get("known_values") else ""
            if a["id"] in lab:
                kv = " (" + ", ".join(f"{code} = {name}" for code, name in lab[a["id"]]) + ")"
            out.append(f"{a['id']}{kv}")
        return ", ".join(out)
    return attr_list("CONFORMED"), attr_list("SNAPSHOT_ONLY")


def build(c: dict) -> dict:
    supported.check(c, "gen_agent")
    metric = c["metrics"][0]
    period = c["analysis_periods"][0]
    params = {p["id"]: p for p in c["parameters"]}
    months = valid_months(c)
    latest, first = months[-1], months[0]
    h = metric["horizon_periods"]
    bm = c["basis_model"]
    sel = metric["member_selection"]

    global COMMON_RESPONSE
    COMMON_RESPONSE = common_response()
    conformed, snapshot_only = attribute_lists(c)
    flags = "; ".join(f"{f['id']} = {clean(f['description'])} {bare(f['value_semantics'])}" for f in c["flags"])
    totals = c["totals_rules"][0]
    scope = c["default_scopes"][0]
    valid = {"ONE_ITEM_PER_ROW": "valid when each row holds one item",
             "ONE_DIMENSION_PER_ROW": "valid when each row and total holds items of one dimension",
             "ALWAYS": "always valid"}
    basis_text = "; ".join(f"{b['id']} = {bare(b['description'])}, {valid[b['valid_when']]}"
                           + (", default" if b["id"] == bm["default_basis"] else "") for b in c["measure_bases"])
    apart = " and ".join(sel["set_apart_flags"])
    months_text = (f"Valid analysis months: {first.isoformat()} to {latest.isoformat()}, monthly; "
                   f"{period['latest_token']} = {latest.isoformat()}.")

    description = clean(f"""
        {clean(metric['description'])} Stock coverage in months ({', '.join(metric['synonyms'])}): if nothing is
        replenished, how many months the stock on hand at the analysis month lasts against the demand forecast of the
        next {h} months. This tool computes every number; you never compute, add, average or adjust a coverage
        yourself. Coverage is not additive: {lower_first(totals['description'])} For a coarser group, call the tool again
        with that coarser grain, or ask for it in totals; never add or average rows. {months_text} The result is always in {bm['result_unit']}. Bases (where stock and
        forecast are measured before the ratio): {basis_text}. A basis the request cannot compare is refused with
        {bm['refusal']}, which names the bases allowed. By default {clean(scope['description'])}
        Each result row carries coverage_months (in {bm['result_unit']} on every basis), stock and forecast_over_horizon
        (in stock_unit), stock_unit, stockout_month (the month the stock runs out: analysis month plus coverage rounded
        up; none beyond the horizon or without demand) and flag. Flags: {flags}. With {sel['upper_bound_parameter']},
        {sel['lower_bound_parameter']} or {sel['rank_parameter']}, the tool keeps, orders and counts the rows itself and
        the answer also carries selection: per analysis month, the count of kept rows, their stock per unit, and the
        members set apart ({apart}), counted and named; never sort, filter or pick coverage rows yourself. The answer also
        carries request.as_of_months (the month actually used), warnings (each with its number), the first and last
        available months with LATEST, and the query ids of its statements (lineage, not for the user). A result with status "refused" carries a refusal code and a reason: relay the reason, do not
        work around it.""")

    def prop(pid, extra=""):
        p = params[pid]
        ex = f" Example: {p['example']}" if p.get("example") else ""
        req = "Required." if p["is_required"] else (f"Optional, default {p['default_value']}."
                                                     if p.get("default_value") is not None else "Optional.")
        shape = f" A JSON {p['json_shape']}, passed as a string." if p["encoding"] == "JSON_STRING" else ""
        return {"type": "string", "description": clean(f"{req}{shape} {clean(p['description'])} {extra}{ex}")}

    properties = {
        "as_of_months": prop("as_of_months", f"{months_text} 'June 2026' is [\"2026-06-01\"]. "
                                             f"Use [\"{period['latest_token']}\"] when the user asks for now, the current or the latest month."),
        "basis": prop("basis"),
        "grain": prop("grain", f"Conformed attributes (stock and forecast): {conformed}. Stock-only attributes "
                               f"(the forecast stays at the conformed grain): {snapshot_only}."),
        "filters": prop("filters", "Same attributes and codes as grain: codes, never names (Germany is DE, "
                                   "flour and baking is PANTRY_FLOUR)."),
        "totals": prop("totals"),
        "coverage_below": prop("coverage_below", "'Within the next 3 months' is \"3\"."),
        "coverage_above": prop("coverage_above", "'More than 12 months of coverage' is \"12\"."),
        "rank_first": prop("rank_first", "'Which 10 products first' is \"10\"; 'first' with no number is \"10\"."),
    }
    required = [pid for pid in properties if params[pid]["is_required"]]

    # Session 8b (decision 5): two tools. The B2 semantic view tool, with B2's generated description less its claim
    # on coverage and coverage routed to stock_coverage (charter version 3, the rule applied to D and D'), for stock,
    # closing stock and forecast; the generic tool on the generated procedure for coverage.
    sv_name, sv_tool, sv_res = native_sv_tool(c)
    orchestration = clean(f"""
        Route every stock coverage question, including a follow-up on coverage, to {TOOL}. Route questions on stock
        on hand, closing stock and demand forecast to {sv_name}. Never compute, add, average or adjust a coverage
        from figures {sv_name} returned, and never compute, add, average or adjust a coverage figure yourself; never
        add or average coverage rows: for a coarser group (a family, a country, a region, the whole range) call
        {TOOL} again at that coarser grain, or ask for the total in totals. Coverage is measured at one analysis month:
        if the user gives no month, or gives a period (a year, a quarter, a range of months), do not choose one; ask
        which month, and say that the latest available month is {latest.strftime('%B %Y')}. {months_text} By default
        {clean(scope['description'])} {basis_rule_sentence(c)} Pass basis {bm['default_basis']} unless the question
        asks for value or for one item in its own unit (NATIVE). If {TOOL} refuses with {bm['refusal']}, you may call it
        again with a basis the refusal allows, and say that the basis changed and why; never add kg and L yourself. For
        questions on what stocks out within N months, what stocks out first or what has more than N months of
        coverage, pass {sel['upper_bound_parameter']}, {sel['rank_parameter']} or {sel['lower_bound_parameter']}: the
        tool filters and ranks, and reports apart the members already out and those with no demand.
        {sel['grain_rule']} Use attribute codes in grain and filters. A follow-up such as "and by country?" keeps the filters of the previous question and adds the
        attribute to the grain.""")
    return {
        "models": {"orchestration": MODEL},
        "orchestration": {"budget": dict(BUDGET), "tool_not_accessible": "reject"},
        "instructions": {"orchestration": orchestration, "response": COMMON_RESPONSE},
        "tools": [{"tool_spec": sv_tool},
                  {"tool_spec": {"type": "generic", "name": TOOL, "description": description,
                                 "input_schema": {"type": "object", "properties": properties, "required": required}}}],
        "tool_resources": {sv_name: sv_res,
                           TOOL: {"type": "procedure", "identifier": PROCEDURE,
                                  "execution_environment": {"type": "warehouse", "warehouse": WAREHOUSE,
                                                            "query_timeout": 120}}},
    }


SV_USE = ("Use it for stock, closing stock and demand forecast questions; coverage is computed by the stock_coverage "
          "tool, never here.")


def native_sv_tool(c: dict) -> tuple[str, dict, dict]:
    """B2's semantic view tool as compiler/gen_native_sv.py generates it, its description less its claim on coverage,
    coverage routed to the stock_coverage tool. Imported here, not at module level: gen_native_sv imports this module."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gen_native_sv as nsv
    b2 = nsv.agent(nsv.build(c))
    tool = dict(b2["tools"][0]["tool_spec"])
    d = tool["description"]
    d = d.replace("; stock coverage in months (coverage_months_qty_eq, coverage_months_value) for one analysis month", "")
    d = d.replace("Use it for every question on stock, closing stock, forecast or coverage.", SV_USE)
    if "coverage_months" in d or SV_USE not in d:
        raise RuntimeError(f"B2's view tool description changed; its coverage claim was not removed: {d}")
    tool["description"] = d
    return tool["name"], tool, b2["tool_resources"][tool["name"]]


def common_response() -> str:
    """The response instruction common to every configuration (charter version 7), as gen_native_sv writes it."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gen_native_sv as nsv
    return nsv.RESPONSE


def render(c: dict) -> str:
    head = (f"# GENERATED from contract/stock_coverage.yaml (contract {c['id']}, version {c['version']}) and data/output/\n"
            "# by compiler/gen_agent.py. Do not edit: change the contract and run `python compiler/gen_agent.py`.\n"
            "# tests/test_generated.py regenerates this file and fails on any difference.\n"
            "# Agent C: permanent agent LINKML_METRICS.RAW.LINKML_C, created from this spec as LINKML_METRICS_ROLE and\n"
            f"# called as LINKML_SVC. Two tools: the B2 semantic view (stock, closing stock, forecast) and a generic tool\n"
            f"# bound to {PROCEDURE} (coverage; SQL Scripting since session 8b).\n")
    return head + yaml.safe_dump(build(c), sort_keys=False, allow_unicode=True, width=118)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = p.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(render(yaml.safe_load(a.contract.read_text())))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
