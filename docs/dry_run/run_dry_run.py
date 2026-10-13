"""
Dry run of session 11: how generic is the compiler? Every generator of compiler/ on a second contract of the depletion
pattern, cash runway (docs/dry_run/cash_runway.yaml). Offline: nothing is deployed, no Snowflake call, no file of the
repository is written. Results: docs/dry_run/results.md.

    .venv/bin/python docs/dry_run/run_dry_run.py                 # writes to a new temporary folder
    .venv/bin/python docs/dry_run/run_dry_run.py --out <folder>  # a folder outside the repository

What it runs:
1. Variant A, cash_runway.yaml as written (no name shared with stock coverage), and variant B, A plus the five
   concessions of STEPS, each validated with linkml-validate against contract/metamodel.yaml; then B without each
   concession in turn (ablation). Each generator's render() is called in-process with the contract.
2. gen_agent and gen_native_sv read the loaded dataset; for them the runner writes a toy dataset into the output
   folder, one Parquet file per table of the contract under the contract's own table names (the calendar, the two
   facts, the dimensions with label columns). The only override is gen_agent.DATA, pointed at that folder. Variants
   "_stub_b2" also replace gen_agent.native_sv_tool (agent C embeds configuration B2's view tool) by a stub, to see
   the rest of agent C's specification.
3. The SQL the generated Python procedure of variant B would send for one request, assembled offline from the
   handler inside the generated file (never executed).
4. Two sections the metamodel marks optional, removed from B: the default scope, the refuse-if-used expectation.
5. A contract with the closing measure only (no depletion metric).

Not a test: never collected by pytest (testpaths = tests), never imported by the package or the tests.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "compiler"))
sys.path.insert(0, str(REPO))
METAMODEL = REPO / "contract" / "metamodel.yaml"
VALIDATE = Path(sys.executable).parent / "linkml-validate"

# ================================================================================================ variant B
PARAMS = {"balance_months": "as_of_months", "breakdown": "grain", "where": "filters", "currency_basis": "basis",
          "subtotals": "totals", "runway_below": "coverage_below", "runway_above": "coverage_above",
          "shortest_first": "rank_first"}
CODES = {"MONTH_REQUIRED": "AS_OF_MISSING", "MONTH_UNPARSEABLE": "AS_OF_INVALID",
         "MONTH_NOT_FIRST_DAY": "AS_OF_NOT_MONTH_START", "MONTHS_OVER_CAP": "AS_OF_TOO_MANY",
         "MONTH_WITHOUT_BALANCE": "AS_OF_NO_SNAPSHOT", "PLAN_TOO_SHORT": "HORIZON_NOT_LOADED",
         "CURRENCY_BASIS_UNKNOWN": "BASIS_UNKNOWN", "BREAKDOWN_NOT_LIST": "GRAIN_MALFORMED",
         "BREAKDOWN_EMPTY": "GRAIN_EMPTY", "BREAKDOWN_REPEATED": "GRAIN_DUPLICATE",
         "WHERE_NOT_OBJECT": "FILTERS_MALFORMED", "WHERE_VALUES_EMPTY": "FILTER_VALUES_INVALID",
         "FIELD_UNKNOWN": "ATTRIBUTE_UNKNOWN", "FIELD_UNCLASSIFIED": "ATTRIBUTE_UNCLASSIFIED",
         "FIELD_NOT_APPLICABLE": "ATTRIBUTE_NOT_APPLICABLE", "SUBTOTALS_NOT_LIST": "TOTALS_MALFORMED",
         "SUBTOTAL_NOT_COARSER": "TOTALS_NOT_SUBSET", "PICK_INVALID": "SELECTION_INVALID",
         "ENTITY_RECORD_SPLIT": "MASTER_DATA_FANOUT", "DQ_REFUSED": "DATA_QUALITY_FAILED",
         "CURRENCY_NOT_COMPARABLE": "BASIS_NOT_COMPARABLE"}


def _rename(c: dict, mapping: dict) -> dict:
    s = yaml.safe_dump(c, sort_keys=False)
    for old, new in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
        s = re.sub(rf"\b{old}\b", new, s)
    return yaml.safe_load(s)


def b1_parameter_ids(c: dict) -> dict:
    return _rename(c, PARAMS)


def b2_refusal_codes(c: dict) -> dict:
    return _rename(c, CODES)


def b3_three_bases(c: dict) -> dict:
    for t in c["tables"]:
        if t["id"] == "FCT_CASH_BALANCE":
            t["columns"].append({"name": "balance_local", "data_type": "NUMBER(18,2)"})
        if t["id"] == "FCT_SPEND_PLAN":
            t["columns"].append({"name": "spend_local", "data_type": "NUMBER(18,2)"})
    for m in c["measures"]:
        col = "balance_local" if m["id"] == "cash_on_hand" else "spend_local"
        m["columns"] += [{"basis": "LOCAL", "column": col}, {"basis": "ENTITY_LEDGER", "column": col}]
    c["measure_bases"] = [
        {"id": "ENTITY_LEDGER", "kind": "NATIVE_UNIT", "unit_source": "ITEM_NATIVE_UNIT", "valid_when": "ONE_ITEM_PER_ROW",
         "description": "One entity in its own ledger currency.", "not_comparable_reason": "a row adds several entities"},
        {"id": "LOCAL", "kind": "BASE_UNIT_EQUIVALENT", "unit_source": "ITEM_BASE_UNIT", "valid_when": "ONE_DIMENSION_PER_ROW",
         "description": "Local currency, for entities of one currency.", "not_comparable_reason": "a row adds EUR and GBP"},
    ] + c["measure_bases"]
    c["basis_model"]["default_basis"] = "LOCAL"
    for p in c["parameters"]:
        if p.get("default_value") == "REPORTING":
            p["default_value"], p["allowed_values"] = "LOCAL", ["ENTITY_LEDGER", "LOCAL", "REPORTING"]
    return c


def b4_calendar_names(c: dict) -> dict:
    s = yaml.safe_dump(c, sort_keys=False)
    s = (s.replace("CAL_MONTH", "DIM_CALENDAR").replace("period_start", "month_start")
          .replace("fiscal_year", "year").replace("fiscal_quarter", "quarter"))
    return yaml.safe_load(s)


def b5_grain_rule(c: dict) -> dict:
    c["metrics"][0]["member_selection"]["grain_rule"] = (
        "A list question takes entities as grain; a question for one figure for a segment takes the segment's grain.")
    return c


STEPS = [("B1", "parameter ids renamed to the stock coverage ids", b1_parameter_ids),
         ("B2", "refusal code ids renamed to the 21 stock coverage codes", b2_refusal_codes),
         ("B3", "three measure bases (native, base-unit equivalent as default, monetary)", b3_three_bases),
         ("B4", "calendar renamed DIM_CALENDAR with columns month_start, year, quarter", b4_calendar_names),
         ("B5", "member_selection.grain_rule given (optional in the metamodel)", b5_grain_rule)]


def variant_b(a: dict, skip: str | None = None) -> dict:
    c = copy.deepcopy(a)
    for name, _, fn in STEPS:
        if name != skip:
            c = fn(c)
    c["version"] = "0.0.1-b" + (f"-without-{skip}" if skip else "")
    return c


# ================================================================================================ toy dataset

def month_add(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.month - 1 + n, 12)
    return dt.date(d.year + y, m + 1, 1)


def toy_dataset(c: dict, folder: Path) -> None:
    """The columns gen_agent reads, under the contract's own table names: 36 calendar months, 6 balance months, 36
    plan months, three entities with labels."""
    folder.mkdir(parents=True, exist_ok=True)
    months = [month_add(dt.date(2026, 1, 1), k) for k in range(36)]
    measures = {m["id"]: m for m in c["measures"]}
    metric = c["metrics"][0]
    snap, flow = measures[metric["snapshot_measure"]], measures[metric["flow_measure"]]
    cal = next(r for r in c["relationships"] if r["from_table"] == snap["table"] and r["from_columns"] == [snap["time_column"]])
    pd.DataFrame({cal["to_columns"][0]: months}).to_parquet(folder / f"{cal['to_table']}.parquet")
    pd.DataFrame({snap["time_column"]: months[:6]}).to_parquet(folder / f"{snap['table']}.parquet")
    pd.DataFrame({flow["time_column"]: months}).to_parquet(folder / f"{flow['table']}.parquet")
    pd.DataFrame({"entity_code": ["E01", "E02", "E03"], "entity_name": ["North", "South", "Isles"],
                  "segment_code": ["RETAIL", "RETAIL", "WHOLESALE"],
                  "segment_name": ["Retail", "Retail", "Wholesale"]}).to_parquet(folder / "DIM_ENTITY.parquet")


# ================================================================================================ runs

LEAK = re.compile(r"\b(stock\w*|STOCK\w*|Stock\w*|coverage\w*|COVERAGE\w*|Coverage\w*|forecast\w*|FORECAST\w*|"
                  r"Forecast\w*|item\w*|ITEM\w*|Item\w*|SKU\w*|batch\w*|BATCH\w*|kg|grocery|PANTRY\w*|Germany|"
                  r"BULK|lifecycle\w*)\b")


def leaks(text: str) -> dict[str, int]:
    """Words of stock coverage in an output, counted. Internal identifiers (CTE and variable names) count too."""
    out: dict[str, int] = {}
    for m in LEAK.finditer(text):
        out[m.group(0)] = out.get(m.group(0), 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def failure(e: BaseException) -> str:
    tb = traceback.extract_tb(e.__traceback__)
    where = next((f"{Path(f.filename).name}:{f.lineno}" for f in reversed(tb) if "compiler" in Path(f.filename).parts),
                 "?")
    return f"{type(e).__name__} at {where}: {str(e)[:200]}"


def validate(path: Path) -> str:
    r = subprocess.run([str(VALIDATE), "-s", str(METAMODEL), "-C", "MetricContract", str(path)],
                       capture_output=True, text=True)
    return " ".join((r.stdout + r.stderr).split())[:300]


def generators(c: dict, traps: dict):
    import gen_agent, gen_closing_sv, gen_dmf, gen_native_sv, gen_procedure, gen_questions, gen_schema  # noqa: E401
    return [
        ("gen_schema", "schema.py", lambda: gen_schema.render(c)),
        ("gen_dmf", "dmf.sql", lambda: gen_dmf.render(c)),
        ("gen_procedure --target python", "procedure_py.sql", lambda: gen_procedure.render(c)),
        ("gen_procedure --target sql", "procedure_sql.sql", lambda: gen_procedure.render_sql(c)),
        ("gen_closing_sv", "closing_sv.sql", lambda: gen_closing_sv.render(c)),
        ("gen_agent", "agent.yaml", lambda: gen_agent.render(c)),
        ("gen_native_sv", "native.txt", lambda: "\n".join(f"### {k}\n{v}" for k, v in gen_native_sv.render(c).items())),
        ("gen_questions", "questions.yaml", lambda: gen_questions.render(c, traps)),
    ]


def run_variant(out: Path, name: str, c: dict, traps: dict, stub_b2: bool = False) -> list[dict]:
    import gen_agent
    folder = out / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "contract.yaml").write_text(yaml.safe_dump(c, sort_keys=False, width=118))
    valid = validate(folder / "contract.yaml")
    toy_dataset(c, folder / "toy_data")
    gen_agent.DATA = folder / "toy_data"
    saved = gen_agent.native_sv_tool
    if stub_b2:
        gen_agent.native_sv_tool = lambda c: ("b2_semantic_view", {"type": "cortex_analyst_text_to_sql",
                                                                    "name": "b2_semantic_view", "description": "STUB"},
                                              {"semantic_view": "STUB"})
    rows = []
    try:
        for gen, fname, fn in generators(c, traps):
            try:
                text = fn()
                (folder / fname).write_text(text)
                rows.append({"variant": name, "validate": valid, "generator": gen, "runs": True, "error": None,
                             "leaks": leaks(text)})
            except Exception as e:  # noqa: BLE001
                rows.append({"variant": name, "validate": valid, "generator": gen, "runs": False, "error": failure(e),
                             "leaks": {}})
    finally:
        gen_agent.native_sv_tool = saved
    return rows


def request_sql(out: Path) -> dict:
    """Variant B: the SQL its Python procedure would send for one request (June 2026, by entity, grand total)."""
    body = (out / "B" / "procedure_py.sql").read_text().split("$$")[1]
    ns: dict = {}
    exec(compile(body, "procedure_py", "exec"), ns)
    st = {"months": [dt.date(2026, 6, 1)], "basis": "REPORTING", "grain": ["entity_code"], "filters": {},
          "totals": [[]], "selection": {}}
    p = ns["plan"](st)
    cov = ns["coverage_sql"](st, p).text()
    qual = ns["quality_sql"](st, p)[0].text()
    (out / "B" / "request_coverage.sql").write_text(cov)
    (out / "B" / "request_quality.sql").write_text(qual)
    stock_rows = re.search(r"stock_rows AS \(\n\s*(SELECT[^\n]*)", cov).group(1)
    return {"stock_rows_select": stock_rows,
            "reads_item_id": [l.strip() for l in cov.splitlines() if "item_id" in l and "stock_rows" in l],
            "in_call_ids_kept_by_handler": "QE_ prefix only" if 'k.startswith("QE_")' in body else "any",
            "quality_columns": re.findall(r"AS (DQ_\w+|QE_\w+)", qual)}


def optional_sections(b: dict) -> dict:
    import gen_procedure
    out = {}
    no_scope = copy.deepcopy(b)
    no_scope["default_scopes"] = []
    no_scope["warning_codes"] = [w for w in no_scope["warning_codes"] if w["raised_by"] != "OPERATING_CASH_ONLY"]
    no_dedup = copy.deepcopy(b)
    for q in no_dedup["quality_expectations"]:
        if q["on_failure"] == "REFUSE_IF_USED":
            q.update(on_failure="WARN")
            q.pop("refusal")
    for name, c in (("no default scope", no_scope), ("no refuse-if-used expectation", no_dedup)):
        try:
            body = gen_procedure.render(c).split("$$")[1]
            ns: dict = {}
            exec(compile(body, "procedure_py", "exec"), ns)
            st = {"months": [dt.date(2026, 6, 1)], "basis": "REPORTING", "grain": ["entity_code"], "filters": {},
                  "totals": [], "selection": {}}
            q = ns["quality_sql"](st, ns["plan"](st))[0].text()
            out[name] = {"runs": True, "sql_lines_with_None": [l.strip() for l in q.splitlines() if "None" in l]}
        except Exception as e:  # noqa: BLE001
            out[name] = {"runs": False, "error": failure(e)}
    return out


def closing_only(a: dict, out: Path) -> dict:
    import gen_closing_sv
    keep = {"id", "name", "description", "version", "status", "effective_date", "ownership", "dimension_classes",
            "tables", "relationships", "measures", "attributes", "measure_bases", "basis_model", "failure_modes",
            "refusal_codes", "quality_expectations", "warning_codes"}
    c = {k: v for k, v in a.items() if k in keep}
    c["id"] = "closing_balance"
    c["measures"] = [m for m in c["measures"] if m["id"] == "cash_on_hand"]
    c["attributes"] = [dict(x, applicability=[e for e in x["applicability"] if e["measure"] == "cash_on_hand"])
                       for x in c["attributes"]]
    c["warning_codes"] = [w for w in c["warning_codes"] if w["raised_by"] != "OPERATING_CASH_ONLY"]
    p = out / "closing_balance_only.yaml"
    p.write_text(yaml.safe_dump(c, sort_keys=False))
    res = {"validate": validate(p)}
    try:
        text = gen_closing_sv.render(c)
        (out / "closing_balance_only.sql").write_text(text)
        res.update(runs=True, lines=len(text.splitlines()))
    except Exception as e:  # noqa: BLE001
        res.update(runs=False, error=failure(e))
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, help="output folder, outside the repository (default: a new temporary folder)")
    a = ap.parse_args()
    out = (a.out or Path(tempfile.mkdtemp(prefix="freerange-dry-run-"))).resolve()
    if out == REPO or REPO in out.parents:
        ap.error("--out must be outside the repository")
    out.mkdir(parents=True, exist_ok=True)
    contract_a = yaml.safe_load((HERE / "cash_runway.yaml").read_text())
    contract_b = variant_b(contract_a)
    traps = yaml.safe_load((REPO / "data" / "traps.yaml").read_text())
    rows = run_variant(out, "A", contract_a, traps) + run_variant(out, "B", contract_b, traps)
    rows += run_variant(out, "B_stub_b2", contract_b, traps, stub_b2=True)
    for name, _, _ in STEPS:
        rows += run_variant(out, f"B_stub_b2_without_{name}", variant_b(contract_a, skip=name), traps, stub_b2=True)
    report = {"steps": {n: d for n, d, _ in STEPS}, "matrix": rows, "request_sql": request_sql(out),
              "optional_sections": optional_sections(contract_b), "closing_only": closing_only(contract_a, out)}
    (out / "report.json").write_text(json.dumps(report, indent=1))
    validated = {}
    for r in rows:
        validated.setdefault(r["variant"], r["validate"])
    for v, msg in validated.items():
        print(f"{v:28} linkml-validate: {msg}")
    print()
    for r in rows:
        print(f"{r['variant']:28} {r['generator']:30} {'runs ' if r['runs'] else 'FAILS'} {r['error'] or ''}")
    print("\nrequest SQL (variant B):", json.dumps(report["request_sql"], indent=1))
    print("optional sections removed from B:", json.dumps(report["optional_sections"], indent=1))
    print("closing measure only:", json.dumps(report["closing_only"], indent=1))
    print(f"\noutputs and report.json: {out}")


if __name__ == "__main__":
    main()
