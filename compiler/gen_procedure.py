"""
Third generator: contract/stock_coverage.yaml -> generated/stock_coverage_procedure.sql (Python target) and
generated/stock_coverage_procedure_sql.sql (SQL Scripting target, session 8b).

    python compiler/gen_procedure.py                              # writes both files
    python compiler/gen_procedure.py --target python --out /tmp/proc.sql      # one target elsewhere (drift test)
    python compiler/gen_procedure.py --target sql --out /tmp/proc_sql.sql

SQL Scripting target (session 8b, decision 1): compiler/procedure_scripting.py writes the body from the contract values
(scripting_contract: the values of the Python target plus flat attribute maps, the join clauses and the in-call
quality expectations sorted by use), with each refusal code's check in one of three stages; it fails when a code has
no check, a check has no code, or the stages break the contract's check_order. Names
(decision 2): during parity the SQL procedure is STOCK_COVERAGE_SQL beside the Python STOCK_COVERAGE; once SWAPPED,
the SQL procedure is STOCK_COVERAGE and the Python one STOCK_COVERAGE_PY.

The file creates LINKML_METRICS.RAW.STOCK_COVERAGE, a Python procedure, EXECUTE AS CALLER. Its handler is
compiler/procedure_handler.py with one line replaced: CONTRACT, the values read here from the contract (attributes
and their classes, joins, unit columns and names, refusal codes in check order with their reasons, warnings, default
scope, horizon, flags, the in-call quality checks as SQL). Every list or map parameter is a VARCHAR holding JSON
(an ARRAY argument is rejected by an agent custom tool on a warehouse, measured in probe C0).

The generator fails when the contract and the handler disagree: a refusal code with no check in the handler, a check
with no code in the contract, a refusal order that breaks a check's prerequisites, an in-call quality expectation
whose kind and scope have no SQL template here. The output is deterministic: same contract, same bytes.
"""

from __future__ import annotations

import argparse
import ast
import json
import pprint
import re
from pathlib import Path

import yaml

try:
    from compiler import supported
except ImportError:                       # run as a script: compiler/ is on sys.path
    import supported

try:
    from compiler import procedure_scripting
except ImportError:                       # run as a script: compiler/ is on sys.path
    import procedure_scripting

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contract" / "stock_coverage.yaml"
HANDLER_PATH = ROOT / "compiler" / "procedure_handler.py"
DEFAULT_OUT = {"python": ROOT / "generated" / "stock_coverage_procedure.sql",
               "sql": ROOT / "generated" / "stock_coverage_procedure_sql.sql"}
SCHEMA = "LINKML_METRICS.RAW"
SWAPPED = True       # decision 2 of session 8b: parity held (134/134, clone cases 8/8), swap pre-approved 2026-10-04
PROCEDURES = {"python": f"{SCHEMA}.STOCK_COVERAGE_PY" if SWAPPED else f"{SCHEMA}.STOCK_COVERAGE",
              "sql": f"{SCHEMA}.STOCK_COVERAGE" if SWAPPED else f"{SCHEMA}.STOCK_COVERAGE_SQL"}
PROCEDURE = PROCEDURES["python"]
MAX_VALUES = 5       # conflicting values named per column in MASTER_DATA_FANOUT (decision 3 of session 8b)
WAREHOUSE_ROLE = "LINKML_METRICS_ROLE"

# A check may read state that an earlier check writes. The contract's check_order must respect it.
PREREQUISITES = {
    "AS_OF_INVALID": ["AS_OF_MISSING"], "AS_OF_NOT_MONTH_START": ["AS_OF_INVALID"],
    "AS_OF_TOO_MANY": ["AS_OF_INVALID"], "AS_OF_NO_SNAPSHOT": ["AS_OF_TOO_MANY", "AS_OF_NOT_MONTH_START"],
    "HORIZON_NOT_LOADED": ["AS_OF_NO_SNAPSHOT"],
    "GRAIN_EMPTY": ["GRAIN_MALFORMED"], "GRAIN_DUPLICATE": ["GRAIN_MALFORMED"],
    "FILTER_VALUES_INVALID": ["FILTERS_MALFORMED"],
    "ATTRIBUTE_UNKNOWN": ["GRAIN_MALFORMED", "FILTER_VALUES_INVALID"],
    "ATTRIBUTE_UNCLASSIFIED": ["ATTRIBUTE_UNKNOWN"], "ATTRIBUTE_NOT_APPLICABLE": ["ATTRIBUTE_UNKNOWN"],
    "TOTALS_NOT_SUBSET": ["TOTALS_MALFORMED", "GRAIN_DUPLICATE"],
    "MASTER_DATA_FANOUT": ["HORIZON_NOT_LOADED", "BASIS_UNKNOWN", "ATTRIBUTE_NOT_APPLICABLE", "TOTALS_NOT_SUBSET",
                           "GRAIN_EMPTY", "SELECTION_INVALID"],
    # session 8c-0: judged on the rows the call returns, so after every data check that can refuse the call
    "BASIS_NOT_COMPARABLE": ["MASTER_DATA_FANOUT", "DATA_QUALITY_FAILED", "SELECTION_INVALID", "BASIS_UNKNOWN"],
}


def handler_checks() -> set[str]:
    tree = ast.parse(HANDLER_PATH.read_text())
    return {n.name[4:].upper() for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("chk_")}


def _alias(table_id: str) -> str:
    return re.sub(r"^(DIM|FCT)_", "", table_id).lower()


def build(c: dict) -> dict:
    supported.check(c, "gen_procedure")
    tables = {t["id"]: t for t in c["tables"]}
    fq = {t: f"{SCHEMA}.{t}" for t in tables}
    measures = {m["id"]: m for m in c["measures"]}
    metric = c["metrics"][0]
    snap, flow = measures[metric["snapshot_measure"]], measures[metric["flow_measure"]]
    h, k0 = metric["horizon_periods"], metric["window_start_offset"]

    def fact(m):
        joins = {r["to_table"]: (r["from_columns"], r["to_columns"]) for r in c["relationships"]
                 if r["from_table"] == m["table"] and r["cardinality"] == "MANY_TO_ONE"}
        return {"table": m["table"], "time_column": m["time_column"], "joins": joins}

    member_keys = [k for k in tables[flow["table"]]["grain"] if k != flow["time_column"]]
    snap_cols = {col["name"] for col in tables[snap["table"]]["columns"]}
    if not set(member_keys) <= snap_cols:
        raise ValueError(f"the snapshot table must carry the flow's member keys: {sorted(set(member_keys) - snap_cols)}")

    # ---- refusals, in check order, against the handler's checks
    refusals = sorted(c["refusal_codes"], key=lambda r: r["check_order"])
    order = [r["id"] for r in refusals]
    checks = handler_checks()
    if set(order) != checks:
        raise ValueError(f"contract codes without a check: {set(order) - checks}; "
                         f"checks without a code: {checks - set(order)}")
    for code, pre in PREREQUISITES.items():
        for p in pre:
            if not order.index(p) < order.index(code):
                raise ValueError(f"check_order: {p} must run before {code}")

    # ---- in-call quality checks
    qes = [q for q in c["quality_expectations"] if q["on_failure"] != "MONITOR"]
    dedup = {q["table"] for q in qes if q["on_failure"] == "REFUSE_IF_USED"}
    if len(dedup) > 1:
        raise ValueError(f"REFUSE_IF_USED quality expectations on more than one table: {sorted(dedup)}")
    dedup_table = next(iter(dedup), None)
    dedup_key = tables[dedup_table]["grain"][0] if dedup_table else None
    time_col = {m["table"]: m["time_column"] for m in c["measures"]}
    quality, context_cols = [], []
    for q in qes:
        sql = quality_sql(q, tables, fq, time_col, snap, h, k0)
        entry = {"id": q["id"], "on_failure": q["on_failure"], "scope": q["call_scope"],
                 "refusal": q.get("refusal"), "warning": q.get("warning"), "condition": q["condition"],
                 "table": q["table"], "source": _alias(q["table"])}
        if q["call_scope"] == "TABLE":
            if sql is not None:
                context_cols.append(f"{sql} AS {q['id']}")
        else:
            entry["sql"] = sql
        quality.append(entry)

    # ---- context: caller, snapshot months, valid analysis months, table-scope checks
    period = c["analysis_periods"][0]
    p_t, p_c = fq[period["source_table"]], period["source_column"]
    cal_ref = next(r for r in c["relationships"] if r["from_table"] == period["source_table"]
                   and r["to_table"] != period["source_table"] and r["from_columns"] == [p_c])
    cal_t, cal_c = fq[cal_ref["to_table"]], cal_ref["to_columns"][0]
    f_t, f_c = fq[flow["table"]], flow["time_column"]
    caller = ("CURRENT_ROLE() AS CALLER_ROLE, CURRENT_SECONDARY_ROLES() AS CALLER_SECONDARY_ROLES, "
              "CURRENT_USER() AS CALLER_USER, SYS_CONTEXT('SNOWFLAKE$CURRENT', 'IS_AGENT_ACTIVATED')::VARCHAR AS AGENT_ACTIVATED")
    context = (
        f"WITH snaps AS (SELECT DISTINCT {p_c} AS m FROM {p_t}),\n"
        f"reach AS (SELECT (SELECT MAX({cal_c}) FROM {cal_t}) AS cal_max, (SELECT MAX({f_c}) FROM {f_t}) AS fc_max)\n"
        f"SELECT {caller},\n"
        f"       (SELECT ARRAY_AGG(TO_VARCHAR(m)) FROM snaps) AS SNAPSHOTS,\n"
        f"       (SELECT ARRAY_AGG(TO_VARCHAR(m)) FROM snaps, reach WHERE reach.cal_max >= DATEADD(month, {h}, m)\n"
        f"           AND reach.fc_max >= DATEADD(month, {h}, m)) AS AVAILABLE"
        + "".join(f",\n       {x}" for x in context_cols))

    def names(e):
        return sorted({re.sub(r"[\s-]+", "_", x.strip().upper()) for x in [e["id"]] + e.get("synonyms", [])})

    params = {p["id"]: p for p in c["parameters"]}
    sel = metric["member_selection"]
    scope = c["default_scopes"][0]
    attrs = {a["id"]: {"table": a["table"], "column": a["column"], "class": a["applicability_class"],
                       "description": a.get("description", "")} for a in c["attributes"]}
    classes = {k: [a for a, v in attrs.items() if v["class"] == k] for k in ("CONFORMED", "SNAPSHOT_ONLY", "NOT_APPLICABLE")}
    outcomes = {o["condition"]: o.get("flag") for o in metric["outcomes"]}
    outcomes["BEYOND_HORIZON"] = metric["beyond_horizon"]["flag"]
    return {
        "id": c["id"], "version": c["version"], "horizon": h, "window_start": k0,
        "latest_token": period["latest_token"], "max_periods": period["max_periods"],
        "tables": fq, "aliases": {t: _alias(t) for t in tables},
        "attributes": attrs, "classes": classes, "unclassified": [],
        "snapshot": fact(snap), "flow": fact(flow), "member_keys": member_keys,
        "dedup_tables": sorted(dedup), "dedup_key": dedup_key,
        "basis": basis_contract(c, fq, snap, flow, names),
        "selection": {"parameters": {p["id"]: p["data_type"] for p in c["parameters"] if p["id"] in (
                          sel["upper_bound_parameter"], sel["lower_bound_parameter"], sel["rank_parameter"])},
                      "below": sel["upper_bound_parameter"], "above": sel["lower_bound_parameter"],
                      "rank": sel["rank_parameter"], "apart_flags": sel["set_apart_flags"],
                      "no_sum_bases": [b["id"] for b in c["measure_bases"] if b["valid_when"] == "ONE_ITEM_PER_ROW"]},
        "stockout_none_flags": metric["exhaustion_period"]["none_for_flags"],
        "refusal_order": order, "refusals": {r["id"]: r["reason_template"] for r in refusals},
        "warnings": {w["id"]: w["message_template"] for w in c["warning_codes"]},
        "default_scope": {"attribute": scope["attribute"], "included": scope["included_values"],
                          "warning": scope["warning"]},
        "flow_members": c["member_set_rules"][0]["flow_members"],
        "flags": outcomes,
        "filters_default": params["filters"].get("default_value", "{}"),
        "totals_default": params["totals"].get("default_value", "[]"),
        "quality": quality, "context_sql": context, "caller_sql": f"SELECT {caller}",
        "note": " ".join(c["totals_rules"][0]["description"].split()),
        "attribute_order": list(attrs), "max_values": MAX_VALUES,
    }


def basis_contract(c: dict, fq: dict, snap: dict, flow: dict, names) -> dict:
    """Contract 0.5.0: the measure bases (columns per measure, names, validity, the reason a basis is not comparable,
    the unit of a row), the basis of the default-scope warning amount and where each item's units are read."""
    bm = c["basis_model"]
    col = lambda m, b: next(x["column"] for x in m["columns"] if x["basis"] == b)   # noqa: E731
    bases = c["measure_bases"]
    eq = next(b["id"] for b in bases if b["valid_when"] == "ONE_DIMENSION_PER_ROW")
    return {
        "default": bm["default_basis"],
        "columns": {b["id"]: (col(snap, b["id"]), col(flow, b["id"])) for b in bases},
        "names": {b["id"]: names(b) for b in bases},
        "valid_when": {b["id"]: b["valid_when"] for b in bases},
        "why": {b["id"]: b["not_comparable_reason"] for b in bases},
        "unit_source": {b["id"]: b["unit_source"] for b in bases},
        "fixed_unit": {b["id"]: b["unit_symbol"] for b in bases if b["unit_source"] == "FIXED"},
        # the excluded BULK amount: on a fixed-unit basis its own column, otherwise the base-unit equivalent (an
        # item's own unit never adds up across the excluded items)
        "scope_column": {b["id"]: col(snap, b["id"] if b["unit_source"] == "FIXED" else eq) for b in bases},
        "item": {"table": fq[bm["item_table"]], "key": bm["item_key"], "dimension": bm["dimension_column"],
                 "base_unit": bm["base_unit_column"], "native_unit": bm["native_unit_column"]},
    }


def scripting_contract(c: dict) -> dict:
    """The values of build(), plus what the SQL Scripting target reads directly instead of computing at call time
    (each Scripting statement costs in proportion to the number of variables holding a value, measured in session
    8b): flat attribute maps, the join clause of each dimension from each fact (a {src} slot for the table or its
    DISTINCT projection), and the in-call quality expectations sorted by use."""
    b = build(c)
    attrs = b["attributes"]
    al = b["aliases"]
    def join_map(fact):
        out = {}
        for t, (frm, to) in fact["joins"].items():
            on = " AND ".join(f"{al[t]}.{c2} = {al[fact['table']]}.{c1}" for c1, c2 in zip(frm, to))
            out[t] = {"clause": f"\n    JOIN {{src}} {al[t]} ON {on}", "keys": list(to), "table": b["tables"][t]}
        return out
    q = b["quality"]
    fan = [x for x in q if x["scope"] != "TABLE" and x["on_failure"] == "REFUSE_IF_USED"]
    b.update({
        "attr_expr": {a: f"{al[v['table']]}.{v['column']}" for a, v in attrs.items()},
        "attr_column": {a: v["column"] for a, v in attrs.items()},
        "attr_table": {a: v["table"] for a, v in attrs.items()},
        "attr_class": {a: v["class"] for a, v in attrs.items()},
        "stock_joins": join_map(b["snapshot"]), "flow_joins": join_map(b["flow"]),
        "q_horizon": [{"id": x["id"], "source": x["source"]} for x in q
                      if x["scope"] == "TABLE" and x["refusal"] == "HORIZON_NOT_LOADED"],
        "q_dq": [{"id": x["id"], "condition": x["condition"]} for x in q
                 if x["scope"] == "TABLE" and x["on_failure"] == "REFUSE" and x["refusal"] == "DATA_QUALITY_FAILED"],
        "q_warn": [{"id": x["id"], "warning": x["warning"], "condition": x["condition"]} for x in q
                   if x["scope"] != "TABLE" and x["on_failure"] in ("WARN", "REFUSE_IF_USED")],
        "q_static_cols": ",\n       ".join(f"{x['sql']} AS {x['id']}" for x in q
                                           if x["scope"] != "TABLE" and x["on_failure"] != "REFUSE_IF_USED"),
        "q_fanout": [{"id": x["id"], "table": x["table"], "sql": x["sql"]} for x in fan],
        "stock_table": b["snapshot"]["table"], "flow_table": b["flow"]["table"],
        "stock_time": b["snapshot"]["time_column"], "flow_time": b["flow"]["time_column"],
        "attr_description": {a: v["description"] for a, v in attrs.items()},
    })
    for k in ("quality", "context_sql", "caller_sql", "attributes", "snapshot", "flow"):
        b.pop(k)
    return b


def quality_sql(q, tables, fq, time_col, snap, h, k0) -> str | None:
    """SQL of one in-call check: a scalar subquery returning the violation count."""
    kind, scope, t = q["kind"], q["call_scope"], q["table"]
    cols, ref, rcols = q.get("columns", []), q.get("references_table"), q.get("references_columns", [])
    if scope == "TABLE":
        if kind == "GRAIN_UNIQUENESS":
            return f"(SELECT COUNT(*) - COUNT(DISTINCT {', '.join(cols)}) FROM {fq[t]})"
        if kind == "CARDINALITY" and not ref:
            parts = [f"(SELECT COUNT(*) FROM (SELECT {a} FROM {fq[t]} GROUP BY {a} HAVING COUNT(DISTINCT {b}) > 1))"
                     for a, b in zip(cols, cols[1:])]
            return "(" + " + ".join(parts) + ")"
        if kind == "FRESHNESS" and q["threshold"] == "TBD":
            return None                       # no threshold yet: nothing to compare, nothing raised
        if kind == "FRESHNESS":               # months missing between the table's reach and LATEST + H
            s_t, s_c = snap["table"], snap["time_column"]
            return (f"GREATEST(0, DATEDIFF(month, (SELECT MAX({cols[0]}) FROM {fq[t]}), "
                    f"DATEADD(month, {h}, (SELECT MAX({s_c}) FROM {fq[s_t]}))))")
    if scope == "REQUEST_ROWS" and ref:       # referential or consistency: rows read by the request, no match
        tc = time_col[t]
        if t == snap["table"]:
            where = f"EXISTS (SELECT 1 FROM analysis_months a WHERE a.as_of_month = t.{tc})"
        else:
            where = (f"EXISTS (SELECT 1 FROM analysis_months a JOIN months m ON t.{tc} = DATEADD(month, m.k, a.as_of_month))")
        match = " AND ".join(f"r.{rc} = t.{c}" for c, rc in zip(cols, rcols))
        return (f"(SELECT COUNT(*) FROM {fq[t]} t WHERE {where}\n"
                f"           AND NOT EXISTS (SELECT 1 FROM {fq[ref]} r WHERE {match}))")
    if scope == "REQUEST_MEMBERS" and kind == "GRAIN_UNIQUENESS":
        key = ", ".join(cols)
        return (f"(SELECT COUNT(*) FROM (SELECT {key} FROM {fq[t]} WHERE {key} IN (SELECT {key} FROM scope_items) "
                f"GROUP BY {key} HAVING {{having}}))")
    if scope == "REQUEST_MEMBERS" and kind == "COMPLETENESS":
        tc, keys = cols[0], cols[1:]
        on = " AND ".join(f"x.{k} = p.{k}" for k in keys)
        return (f"(SELECT COUNT(*) FROM scope_pairs p CROSS JOIN months m WHERE NOT EXISTS\n"
                f"           (SELECT 1 FROM {fq[t]} x WHERE {on} AND x.{tc} = DATEADD(month, m.k, p.as_of_month)))")
    raise ValueError(f"{q['id']}: no in-call SQL for kind {kind} with call_scope {scope}")


def _signature(c: dict) -> tuple[list, str]:
    # required first, then optional ones with their default (a procedure's optional arguments come last); every
    # argument is a VARCHAR (lists and maps are JSON strings, numbers are parsed and checked by the procedure)
    order = ["as_of_months", "grain", "filters", "basis", "totals", "coverage_below", "coverage_above", "rank_first"]
    params = sorted(c["parameters"], key=lambda p: order.index(p["id"]))
    if [p["is_required"] for p in params] != sorted([p["is_required"] for p in params], reverse=True):
        raise ValueError("a required parameter comes after an optional one in the procedure's argument order")
    sig = ",\n    ".join(f"{p['id'].upper()} VARCHAR" + ("" if p["is_required"] else (
        f" DEFAULT '{p['default_value']}'" if p.get("default_value") is not None else " DEFAULT NULL")) for p in params)
    return params, sig


def _header(c: dict, contract: dict, procedure: str, source: str, params: list) -> list[str]:
    head = [
        f"-- GENERATED from contract/stock_coverage.yaml (contract {c['id']}, version {c['version']})",
        f"-- by compiler/gen_procedure.py, {source}. Do not edit: change the contract and run",
        "-- `python compiler/gen_procedure.py`. tests/test_generated.py regenerates this file and fails on any difference.",
        "--",
        f"-- {procedure}: stock coverage, refusals, warnings and the query ids of its statements as one JSON answer.",
        "-- Parameters (lists and maps are JSON strings):",
    ]
    for p in params:
        desc = " ".join(p["description"].split())
        head.append(f"--   {p['id']}: {desc} Example: {p.get('example', 'n/a')}")
    return head + [
        "-- Refusal codes, in check order: " + ", ".join(contract["refusal_order"]) + ".",
        "--",
        f"-- Run as {WAREHOUSE_ROLE} with no secondary role:",
        "--   snow sql -c <connection> -f <this file>",
        "USE SECONDARY ROLES NONE;",
        f"USE ROLE {WAREHOUSE_ROLE};",
        "",
    ]


def render_sql(c: dict) -> str:
    contract = build(c)
    sc = scripting_contract(c)
    body = procedure_scripting.body(sc, contract["context_sql"], contract["caller_sql"])
    if "$$" in body:
        raise ValueError("the procedure body holds $$, which would end its dollar-quoted text")
    params, sig = _signature(c)
    head = _header(c, contract, PROCEDURES["sql"], "SQL Scripting target compiler/procedure_scripting.py", params)
    head += [
        f"CREATE OR REPLACE PROCEDURE {PROCEDURES['sql']}(\n    {sig})",
        "RETURNS VARIANT",
        "LANGUAGE SQL",
        f"COMMENT = 'Generated from contract {c['id']} {c['version']} by compiler/gen_procedure.py (SQL Scripting)'",
        "EXECUTE AS CALLER",
        "AS",
        "$$",
    ]
    return "\n".join(head) + "\n" + body.strip("\n") + "\n$$;\n"


def render(c: dict) -> str:
    contract = build(c)
    handler = HANDLER_PATH.read_text()
    line = "CONTRACT: dict = {}  # INJECTED BY compiler/gen_procedure.py"
    if handler.count(line) != 1:
        raise RuntimeError(f"compiler/procedure_handler.py must hold the line {line!r} once")
    literal = pprint.pformat(contract, width=118, sort_dicts=False)
    body = handler.replace(line, f"CONTRACT: dict = {literal}")
    if "$$" in body:
        raise ValueError("the procedure body holds $$, which would end its dollar-quoted text")
    params, sig = _signature(c)
    head = _header(c, contract, PROCEDURE, "handler compiler/procedure_handler.py", params)
    head += [
        f"CREATE OR REPLACE PROCEDURE {PROCEDURE}(\n    {sig})",
        "RETURNS VARIANT",
        "LANGUAGE PYTHON",
        "RUNTIME_VERSION = '3.12'",
        "PACKAGES = ('snowflake-snowpark-python')",
        "HANDLER = 'run'",
        f"COMMENT = 'Generated from contract {c['id']} {c['version']} by compiler/gen_procedure.py'",
        "EXECUTE AS CALLER",
        "AS",
        "$$",
    ]
    return "\n".join(head) + "\n" + body.rstrip("\n") + "\n$$;\n"


def retarget(schema: str) -> None:
    """Point the generated procedures at another schema (zero-copy clones of RAW, decision 4 of session 8b)."""
    global SCHEMA, PROCEDURES, PROCEDURE
    SCHEMA = schema
    PROCEDURES = {k: f"{schema}.{v.rsplit('.', 1)[1]}" for k, v in PROCEDURES.items()}
    PROCEDURE = PROCEDURES["python"]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    p.add_argument("--target", choices=["python", "sql"])
    p.add_argument("--out", type=Path)
    p.add_argument("--schema", help="test deployments only (session 8b, decision 4): read the tables of this schema and "
                                    "create the procedures there; the committed files always use " + SCHEMA)
    a = p.parse_args()
    if a.schema:
        if not a.out:
            p.error("--schema needs --out: the committed files always use " + SCHEMA)
        retarget(a.schema)
    c = yaml.safe_load(a.contract.read_text())
    if a.out and not a.target:
        p.error("--out needs --target")
    for target in [a.target] if a.target else ["python", "sql"]:
        out = a.out or DEFAULT_OUT[target]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(c) if target == "python" else render_sql(c))
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
