"""
Fourth generator: the snapshot measure's period_aggregation -> generated/closing_stock_sv.sql (closing stock, natively).

    python compiler/gen_closing_sv.py                            # writes generated/closing_stock_sv.sql
    python compiler/gen_closing_sv.py --out /tmp/closing.sql     # writes elsewhere (the drift test uses this)

Step 1 of the article: closing stock over a period is the snapshot of the period's last month, for every member of
the period, 0 for a member with no row that month (period_aggregation LAST_PERIOD, missing_value "0"). Snowflake's
NON ADDITIVE BY keeps, per output row, the latest snapshot month present in that row's group (measured, session 6):
right on dense snapshots, the last known value on a gap. The file has two objects:

1. A gap-filled view of the snapshot table. Every snapshot key (the table's grain without its time column) gets one
   row per month from its first snapshot month to its last snapshot month + 1, capped at the latest snapshot month
   of the table, with every measure column at the contract's missing_value where the key has no row. Other columns
   carry the key's last known value. One extra row after a key's last snapshot is enough: NON ADDITIVE BY then finds,
   in any group that held stock in the period, either the period's last month or a later-ended month whose rows are
   all 0. A boolean column marks the filled rows.
2. A semantic view over it: the dimension tables the snapshot measure's attributes live on, the calendar with one
   dimension per period kind (month, quarter, year), and one metric per measure basis comparable across items (QTY_EQ,
   VALUE; contract 0.5.0), NON ADDITIVE BY the snapshot's time column. The item's own unit is not exposed. A dimension table whose grain may be duplicated (a REFUSE_IF_USED
   expectation) is read through a DISTINCT projection of its key and attribute columns: a semantic view cannot
   refuse at query time, so rows that still differ fan out (measured in the sweep).

Nothing is attached to the coverage procedure: it reads the snapshot at exactly the analysis month (T9).
The output is deterministic: same contract, same bytes.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

try:
    from compiler import supported
except ImportError:                       # run as a script: compiler/ is on sys.path
    import supported

try:
    from compiler.gen_agent import view_bases, view_metric_note
except ImportError:                       # run as a script: compiler/ is on sys.path
    from gen_agent import view_bases, view_metric_note

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contract" / "stock_coverage.yaml"
DEFAULT_OUT = ROOT / "generated" / "closing_stock_sv.sql"
SCHEMA = "LINKML_METRICS.RAW"
ROLE = "LINKML_METRICS_ROLE"
PERIOD_DIMENSIONS = {   # period kind -> calendar dimension (name, expression); PERIOD_RANGE is a filter on the month
    "PERIOD_RANGE": ("month_start", "month_start"),
    "QUARTER": ("year_quarter", "year || '-Q' || quarter"),
    "YEAR": ("year", "year"),
}


def _alias(table_id: str) -> str:
    return re.sub(r"^(DIM|FCT)_", "", table_id).lower()


def build(c: dict) -> dict:
    supported.check(c, "gen_closing_sv")
    tables = {t["id"]: t for t in c["tables"]}
    snap = next(m for m in c["measures"] if m.get("period_aggregation"))
    pa = snap["period_aggregation"]
    if pa["method"] != "LAST_PERIOD":
        raise ValueError(f"no native template for {pa['method']}")
    st = tables[snap["table"]]
    tcol = snap["time_column"]
    keys = [k for k in st["grain"] if k != tcol]
    bases = {b["id"]: b for b in view_bases(c)}
    measure_cols = [dict(x, unit=x["basis"], note=view_metric_note(c, bases[x["basis"]])) for x in snap["columns"]
                    if x["basis"] in bases]
    all_measure_cols = {x["column"] for x in snap["columns"]}
    others = [col["name"] for col in st["columns"] if col["name"] not in keys + [tcol] and col["name"] not in all_measure_cols]
    rels = [r for r in c["relationships"] if r["from_table"] == snap["table"] and r["cardinality"] == "MANY_TO_ONE"]
    cal_rel = next(r for r in rels if r["from_columns"] == [tcol])
    attrs = [a for a in c["attributes"]
             if any(x["measure"] == snap["id"] and x["effect"] == "GROUP_AND_FILTER" for x in a["applicability"])]
    dedup = {q["table"] for q in c["quality_expectations"] if q["on_failure"] == "REFUSE_IF_USED"}
    return {"c": c, "tables": tables, "snap": snap, "pa": pa, "keys": keys, "tcol": tcol, "others": others,
            "measure_cols": measure_cols, "all_measure_cols": [x["column"] for x in snap["columns"]],
            "rels": rels, "cal_rel": cal_rel, "attrs": attrs, "dedup": dedup}


def view_sql(b: dict, view: str) -> str:
    snap, keys, tcol = b["snap"], b["keys"], b["tcol"]
    src = f"{SCHEMA}.{snap['table']}"
    cal_t, cal_c = f"{SCHEMA}.{b['cal_rel']['to_table']}", b["cal_rel"]["to_columns"][0]
    k = ", ".join(keys)
    on = " AND ".join(f"s.{x} = g.{x}" for x in keys + [tcol])
    part = ", ".join(f"g.{x}" for x in keys)
    measure = ",\n       ".join(f"COALESCE(s.{m}, {b['pa']['missing_value']}) AS {m}" for m in b["all_measure_cols"])
    carried = ",\n       ".join(
        f"LAST_VALUE(s.{o}) IGNORE NULLS OVER (PARTITION BY {part} ORDER BY g.{tcol}\n"
        f"           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS {o}" for o in b["others"])
    return (
        f"CREATE OR REPLACE VIEW {view}\n"
        f"  COMMENT = 'Generated from contract {b['c']['id']} {b['c']['version']} ({b['pa']['id']}): {snap['table']} with every "
        f"key filled from its first month to its last month + 1 (capped at the latest snapshot), measures {b['pa']['missing_value']} where absent.'\n"
        f"AS\nWITH bounds AS (SELECT MAX({tcol}) AS latest FROM {src}),\n"
        f"key_span AS (\n    SELECT {k}, MIN({tcol}) AS first_month, MAX({tcol}) AS last_month\n"
        f"    FROM {src} GROUP BY {k}\n),\n"
        f"grid AS (\n    SELECT {', '.join('k.' + x for x in keys)}, cal.{cal_c} AS {tcol}\n"
        f"    FROM key_span k CROSS JOIN bounds b\n"
        f"    JOIN {cal_t} cal ON cal.{cal_c} >= k.first_month\n"
        f"     AND cal.{cal_c} <= LEAST(DATEADD(month, 1, k.last_month), b.latest)\n)\n"
        f"SELECT g.{tcol}, {', '.join('g.' + x for x in keys)},\n       {carried},\n       {measure},\n"
        f"       s.{tcol} IS NULL AS gap_filled\n"
        f"FROM grid g\nLEFT JOIN {src} s ON {on}")


def semantic_view_sql(b: dict, view: str, sv: str) -> str:
    c, tables, snap = b["c"], b["tables"], b["snap"]
    sa = _alias(snap["table"])
    used = {}
    for a in b["attrs"]:
        used.setdefault(a["table"], []).append(a)
    lines = []
    for r in b["rels"]:
        t = r["to_table"]
        if t not in used and r is not b["cal_rel"]:
            continue
        al, pk = _alias(t), ", ".join(r["to_columns"])
        if t in b["dedup"]:
            cols = list(dict.fromkeys(r["to_columns"] + [a["column"] for a in used[t]]))
            lines.append(f"    {al} AS (SELECT DISTINCT {', '.join(cols)} FROM {SCHEMA}.{t}) PRIMARY KEY ({pk})\n"
                         f"      COMMENT = 'Distinct projection: the declared grain {', '.join(tables[t]['grain'])} is checked by a "
                         f"REFUSE_IF_USED expectation, which a semantic view cannot enforce.'")
        else:
            lines.append(f"    {al} AS {SCHEMA}.{t} PRIMARY KEY ({pk})")
    lines.append(f"    {sa} AS {view} PRIMARY KEY ({', '.join(tables[snap['table']]['grain'])})\n"
                 f"      COMMENT = '{snap['description']} Gap-filled: a key with no row in a month of its span counts {b['pa']['missing_value']}.'")
    rels = []
    for r in b["rels"]:
        if r["to_table"] in used or r is b["cal_rel"]:
            rels.append(f"    {sa}_{_alias(r['to_table'])} AS {sa} ({', '.join(r['from_columns'])}) "
                        f"REFERENCES {_alias(r['to_table'])}")
    dims = []
    for a in b["attrs"]:
        cm = " ".join((a.get("description") or "").split()).replace("'", "''")
        extra = f" COMMENT = '{cm}'" if cm else ""
        dims.append(f"    {_alias(a['table'])}.{a['id']} AS {a['column']}{extra}")
    cal = _alias(b["cal_rel"]["to_table"])
    for kind in b["pa"]["periods"]:
        name, expr = PERIOD_DIMENSIONS[kind]
        dims.append(f"    {cal}.{name} AS {expr}")
    dims.append(f"    {sa}.{b['tcol']} AS {b['tcol']}")
    dims.append(f"    {sa}.gap_filled AS gap_filled COMMENT = 'TRUE on a row added by the gap fill (measures {b['pa']['missing_value']}).'")
    forbidden = ", ".join(m.lower() for m in b["pa"]["forbidden_methods"])
    metrics = []
    for mc in b["measure_cols"]:
        metrics.append(
            f"    {sa}.closing_stock_{mc['unit'].lower()} NON ADDITIVE BY ({sa}.{b['tcol']} ASC NULLS LAST) AS SUM({mc['column']})\n"
            f"      COMMENT = 'Closing stock {mc['note']}: the snapshot of the period''s last month; never {forbidden} over time.'")
    return (
        f"CREATE OR REPLACE SEMANTIC VIEW {sv}\n  TABLES (\n" + ",\n".join(lines) + "\n  )\n"
        "  RELATIONSHIPS (\n" + ",\n".join(rels) + "\n  )\n"
        "  DIMENSIONS (\n" + ",\n".join(dims) + "\n  )\n"
        "  METRICS (\n" + ",\n".join(metrics) + "\n  )\n"
        f"  COMMENT = 'Generated from contract {c['id']} {c['version']} by compiler/gen_closing_sv.py: closing stock "
        f"({b['pa']['id']}, {b['pa']['method']}).'")


def render(c: dict) -> str:
    b = build(c)
    view = f"{SCHEMA}.{b['snap']['table']}_GAPFILLED"
    sv = f"{SCHEMA}.CLOSING_STOCK_SV"
    head = [
        f"-- GENERATED from contract/stock_coverage.yaml (contract {c['id']}, version {c['version']})",
        "-- by compiler/gen_closing_sv.py. Do not edit: change the contract and run `python compiler/gen_closing_sv.py`.",
        "-- tests/test_generated.py regenerates this file and fails on any difference.",
        "--",
        f"-- {view}: the snapshot table, gap-filled per key. {sv}: closing stock over a month range, a",
        "-- quarter or a year, NON ADDITIVE BY the snapshot month. Run as the project role with no secondary role.",
        "USE SECONDARY ROLES NONE;",
        f"USE ROLE {ROLE};",
        "",
    ]
    return "\n".join(head) + view_sql(b, view) + ";\n\n" + semantic_view_sql(b, view, sv) + ";\n"


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
