"""
First generator: contract/stock_coverage.yaml -> generated/schema.py.

    python compiler/gen_schema.py                       # writes generated/schema.py
    python compiler/gen_schema.py --out /tmp/schema.py  # writes elsewhere (the drift test uses this)

The schema module names tables, columns, types, declared grains, attribute applicability classes and unit
variants for the loader and the checks. It replaces the hand-written data/schema_v0.py.
The output is deterministic: same contract, same bytes. tests/test_generated.py regenerates it and compares.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contract" / "stock_coverage.yaml"
DEFAULT_OUT = ROOT / "generated" / "schema.py"


def _tuple(items) -> str:
    items = list(items)
    if not items:
        return "()"
    return "(" + ", ".join(repr(i) for i in items) + ("," if len(items) == 1 else "") + ")"


def render(contract: dict) -> str:
    tables, attributes = contract["tables"], contract["attributes"]
    measures = {m["id"]: m for m in contract["measures"]}
    metric = contract["metrics"][0]
    snap, flow = measures[metric["snapshot_measure"]], measures[metric["flow_measure"]]
    basis_col = {m: {c["basis"]: c["column"] for c in measures[m]["columns"]} for m in measures}
    bm = contract["basis_model"]

    def by_class(cls: str) -> list[str]:
        return [a["id"] for a in attributes if a["applicability_class"] == cls]

    out = [
        '"""',
        f"GENERATED from contract/stock_coverage.yaml (contract {contract['id']}, version {contract['version']})",
        "by compiler/gen_schema.py. Do not edit: change the contract and run `python compiler/gen_schema.py`.",
        "tests/test_generated.py regenerates this file and fails on any difference.",
        "",
        "Column order is the load order. Types are Snowflake types; pandas columns are lower case and",
        "write_pandas(quote_identifiers=False) maps them to upper-case Snowflake identifiers.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        f"__schema_version__ = {contract['version']!r}",
        f"CONTRACT_ID = {contract['id']!r}",
        "",
        "TABLES: dict[str, dict[str, str]] = {",
    ]
    for t in tables:
        out.append(f"    {t['id']!r}: {{")
        out += [f"        {c['name']!r}: {c['data_type']!r}," for c in t["columns"]]
        out.append("    },")
    out += ["}", "", "# Declared grains. A declared grain is a promise checked by a quality expectation, not an assumption.",
            "GRAINS: dict[str, tuple[str, ...]] = {"]
    out += [f"    {t['id']!r}: {_tuple(t['grain'])}," for t in tables]
    out += ["}", "", "# attribute -> (table, column, applicability class)", "ATTRIBUTES: dict[str, tuple[str, str, str]] = {"]
    out += [f"    {a['id']!r}: ({a['table']!r}, {a['column']!r}, {a['applicability_class']!r})," for a in attributes]
    out += ["}", "",
            "# CONFORMED: groups and filters the snapshot and the flow alike.",
            "# SNAPSHOT_ONLY (stock-only): groups and filters the snapshot; the flow stays at the parent conformed grain.",
            f"CONFORMED: tuple[str, ...] = {_tuple(by_class('CONFORMED'))}",
            f"SNAPSHOT_ONLY: tuple[str, ...] = {_tuple(by_class('SNAPSHOT_ONLY'))}",
            f"NOT_APPLICABLE: tuple[str, ...] = {_tuple(by_class('NOT_APPLICABLE'))}",
            "",
            f"# measure basis -> ({snap['id']} column, {flow['id']} column). The result of the metric is always in "
            f"{bm['result_unit']};",
            "# a basis is where stock and forecast are measured before the ratio.",
            "BASES: dict[str, tuple[str, str]] = {"]
    out += [f"    {b['id']!r}: ({basis_col[snap['id']][b['id']]!r}, {basis_col[flow['id']][b['id']]!r}),"
            for b in contract["measure_bases"]]
    out += ["}", "# measure basis -> where it is valid (the rows and totals the call returns)",
            "BASIS_VALID_WHEN: dict[str, str] = {"]
    out += [f"    {b['id']!r}: {b['valid_when']!r}," for b in contract["measure_bases"]]
    out += ["}", f"DEFAULT_BASIS = {bm['default_basis']!r}",
            "# item dimension -> base unit; each item's dimension and base unit are columns of the item table",
            "ITEM_DIMENSIONS: dict[str, str] = {"]
    out += [f"    {d['id']!r}: {d['base_unit']!r}," for d in bm["dimensions"]]
    out += ["}",
            f"ITEM_BASIS_COLUMNS = {{'table': {bm['item_table']!r}, 'key': {bm['item_key']!r}, "
            f"'dimension': {bm['dimension_column']!r}, 'base_unit': {bm['base_unit_column']!r}, "
            f"'native_unit': {bm['native_unit_column']!r}, 'factor': {bm['equivalence_factor_column']!r}}}",
            "", f"HORIZON_MONTHS = {metric['horizon_periods']}", ""]
    return "\n".join(out)


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
