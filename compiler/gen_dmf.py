"""
Second generator: the contract's quality_expectations -> generated/dmf.sql (data metric functions).

    python compiler/gen_dmf.py                        # writes generated/dmf.sql
    python compiler/gen_dmf.py --out /tmp/dmf.sql     # writes elsewhere (the drift test uses this)

The file has two parts:
1. CREATE OR REPLACE DATA METRIC FUNCTION for every expectation whose `dmf` is CUSTOM, in LINKML_METRICS.RAW.
2. One ad hoc SELECT per check, returning (expectation, target, value). A system DMF takes one column, so an
   expectation on several columns gives one row per column. A custom DMF on two tables is called with each table
   argument as a parenthesised subquery, the only ad hoc form the account accepts (measured, session 5).

Nothing is attached to a table and no DATA_METRIC_SCHEDULE is set: each check runs once, when the SELECT runs.
Each value is a violation count, except system FRESHNESS (seconds), compared with the expectation's threshold.
A DMF body cannot call CURRENT_DATE (error 510101, measured), so an age is left to the system FRESHNESS DMF.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

try:
    from compiler import supported
except ImportError:                       # run as a script: compiler/ is on sys.path
    import supported

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contract" / "stock_coverage.yaml"
DEFAULT_OUT = ROOT / "generated" / "dmf.sql"
TARGET = "LINKML_METRICS.RAW"


def _cols(contract: dict) -> dict[str, dict[str, str]]:
    return {t["id"]: {c["name"]: c["data_type"] for c in t["columns"]} for t in contract["tables"]}


def _arg(name: str, table: str, columns: list[str], types: dict) -> str:
    return f"{name} TABLE({', '.join(f'{c} {types[table][c]}' for c in columns)})"


def _custom(qe: dict, contract: dict) -> tuple[list[tuple[str, list[str]]], str]:
    """([(table, columns) per table argument], body) for a CUSTOM expectation."""
    t, cols, kind = qe["table"], qe["columns"], qe["kind"]
    ref, rcols = qe.get("references_table"), qe.get("references_columns", [])
    metric = contract["metrics"][0]
    period = contract["analysis_periods"][0]
    snap_t, snap_c = period["source_table"], period["source_column"]
    h = metric["horizon_periods"]

    if kind == "GRAIN_UNIQUENESS":
        return [(t, cols)], f"SELECT COUNT(*) - COUNT(DISTINCT {', '.join(cols)}) FROM t"   # rows beyond the first

    if ref:   # REFERENTIAL, or CARDINALITY against another table: rows whose key has no match
        match = " AND ".join(f"r.{rc} = t.{c}" for c, rc in zip(cols, rcols))
        return [(t, cols), (ref, rcols)], f"SELECT COUNT(*) FROM t WHERE NOT EXISTS (SELECT 1 FROM r WHERE {match})"

    if kind == "CARDINALITY":   # functional dependency chain: each column determines the next one
        parts = [f"(SELECT COUNT(*) FROM (SELECT {a} FROM t GROUP BY {a} HAVING COUNT(DISTINCT {b}) > 1))"
                 for a, b in zip(cols, cols[1:])]
        return [(t, cols)], "SELECT " + " + ".join(parts)

    if kind == "COMPLETENESS":   # dense flow: the horizon window of LATEST, as the procedure counts it
        time_c, keys = cols[0], cols[1:]
        k0 = metric["window_start_offset"]
        on = " AND ".join(f"f.{k} = m.{k}" for k in keys)
        body = (f"WITH b AS (SELECT MAX({snap_c}) AS latest FROM r), "
                f"p AS (SELECT DATEADD(month, k.column1, b.latest) AS period FROM (VALUES "
                f"{', '.join(f'({k})' for k in range(k0, k0 + h))}) k, b), "   # SEQ4 is refused in a DMF (510101)
                f"m AS (SELECT DISTINCT {', '.join(keys)} FROM t WHERE {time_c} IN (SELECT period FROM p)) "
                f"SELECT COUNT(*) FROM m CROSS JOIN p WHERE NOT EXISTS "
                f"(SELECT 1 FROM t f WHERE {on} AND f.{time_c} = p.period)")
        return [(t, cols), (snap_t, [snap_c])], body

    if kind == "FRESHNESS":   # the time dimension reaches the latest snapshot + H: months missing
        body = (f"SELECT GREATEST(0, DATEDIFF(month, (SELECT MAX({cols[0]}) FROM t), "
                f"DATEADD(month, {h}, (SELECT MAX({snap_c}) FROM r))))")
        return [(t, cols), (snap_t, [snap_c])], body

    bm = contract.get("basis_model")
    if kind == "VALUE_RANGE" and bm and t == bm["item_table"] and cols == [bm["dimension_column"], bm["base_unit_column"]]:
        # session 8c-0: the item's dimension is declared and its base unit is that dimension's (NULL counts as wrong)
        case = " ".join(f"WHEN '{d['id']}' THEN '{d['base_unit']}'" for d in bm["dimensions"])
        return [(t, cols)], (f"SELECT COUNT(*) FROM t WHERE {cols[1]} IS DISTINCT FROM CASE {cols[0]} {case} END "
                             f"OR {cols[0]} IS NULL")

    if kind == "VALUE_RANGE":
        known = [a.get("known_values") for a in contract["attributes"]
                 if a["table"] == t and a["column"] == cols[0] and a.get("known_values")]
        if known:   # accepted values: the attribute's known_values
            values = ", ".join("'" + v.replace("'", "''") + "'" for v in known[0])
            return [(t, cols)], f"SELECT COUNT(*) FROM t WHERE {cols[0]} NOT IN ({values})"
        return [(t, cols)], f"SELECT COUNT(*) FROM t WHERE NOT COALESCE(({qe['condition']}), FALSE)"

    raise ValueError(f"{qe['id']}: no custom DMF template for kind {kind}")


def render(contract: dict) -> str:
    supported.check(contract, "gen_dmf")
    types = _cols(contract)
    creates, checks = [], []
    for qe in contract["quality_expectations"]:
        qid = qe["id"]
        head = f"-- {qid} ({qe['kind']}, on_failure {qe['on_failure']}, threshold {qe['threshold']}): {qe['condition']}"
        if qe["dmf"] == "CUSTOM":
            args, body = _custom(qe, contract)
            names = ["t", "r"][:len(args)]
            fn = f"{TARGET}.DMF_{qid}"
            sig = ", ".join(_arg(n, tb, cs, types) for n, (tb, cs) in zip(names, args))
            creates += [head, f"CREATE OR REPLACE DATA METRIC FUNCTION {fn}({sig})\n"
                              f"  RETURNS NUMBER\n  COMMENT = 'Generated from contract {contract['id']} "
                              f"{contract['version']}, {qid}'\n  AS\n$$\n{body}\n$$;", ""]
            if len(args) == 1:
                call = f"{fn}(SELECT {', '.join(args[0][1])} FROM {TARGET}.{args[0][0]})"
            else:
                call = f"{fn}(" + ", ".join(f"(SELECT {', '.join(cs)} FROM {TARGET}.{tb})" for tb, cs in args) + ")"
            checks += [head, f"SELECT '{qid}' AS expectation, '{qe['table']}' AS target, {call} AS value;", ""]
        else:
            checks.append(head)
            for c in qe["columns"]:
                checks.append(f"SELECT '{qid}' AS expectation, '{qe['table']}.{c}' AS target, "
                              f"{qe['dmf']}(SELECT {c} FROM {TARGET}.{qe['table']}) AS value;")
            checks.append("")
    header = [
        f"-- GENERATED from contract/stock_coverage.yaml (contract {contract['id']}, version {contract['version']})",
        "-- by compiler/gen_dmf.py. Do not edit: change the contract and run `python compiler/gen_dmf.py`.",
        "-- Ad hoc only: no DMF is attached to a table and no DATA_METRIC_SCHEDULE is set.",
        "",
        "-- ============================================================================ 1. custom DMFs",
        "",
    ]
    return "\n".join(header + creates +
                     ["-- ============================================================================ 2. checks", ""]
                     + checks).rstrip("\n") + "\n"


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
