"""
Latency of direct calls (no agent): where does the time of a CALL go?

    python snowflake/phase3_procedure/latency.py [--connection perso] [--runs 5]

Three shapes, 5 calls each, on the generated STOCK_COVERAGE, and the single-member shape on probe C0 for reference:
a single member (T2), a family with totals, a 3-month series. Two empty witness procedures, created for the run and
dropped after it (EMPTY_PY_PROBE: Python 3.12 with snowflake-snowpark-python, returns 1 without SQL;
EMPTY_SQL_PROBE: Snowflake Scripting, returns 1), give the fixed cost of a CALL in each language. The session sets USE_CACHED_RESULT = FALSE (session
parameter only) so that repeated calls do not read the result cache. After the calls,
INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION gives each CALL's elapsed time and the child queries that ran inside
it (same session, inside the CALL's interval). Handler overhead = CALL elapsed - wall time covered by its children
(children may overlap: the generated procedure runs two of them concurrently).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import connect  # noqa: E402

AS_OF = "2026-06-01"
SHAPES = [
    ("single member (T2)", "STOCK_COVERAGE",
     ('["2026-06-01"]', "QTY_EQ", '["sku_code", "country_code"]', '{"sku_code": ["SKU-H03"], "country_code": ["DE"]}', "[]")),
    ("family with totals", "STOCK_COVERAGE",
     ('["2026-06-01"]', "QTY_EQ", '["sku_code", "country_code"]', '{"family_code": ["PANTRY_PASTA"]}', '[["country_code"], []]')),
    ("3-month series (T3 member)", "STOCK_COVERAGE",
     ('["2026-04-01", "2026-05-01", "2026-06-01"]', "QTY_EQ", '["sku_code", "country_code"]',
      '{"sku_code": ["SKU-H04"], "country_code": ["IT"]}', "[]")),
    ("single member (T2), probe C0", "STOCK_COVERAGE_PROBE",
     ("2026-06-01", "QTY_EQ", '["sku_code", "country_code"]', '{"sku_code": ["SKU-H03"], "country_code": ["DE"]}')),
    ("empty Python procedure (witness)", "EMPTY_PY_PROBE", ()),
    ("empty SQL Scripting procedure (witness)", "EMPTY_SQL_PROBE", ()),
]
WITNESSES = [
    "CREATE OR REPLACE PROCEDURE LINKML_METRICS.RAW.EMPTY_PY_PROBE() RETURNS VARIANT LANGUAGE PYTHON "
    "RUNTIME_VERSION = '3.12' PACKAGES = ('snowflake-snowpark-python') HANDLER = 'run' EXECUTE AS CALLER "
    "AS $$\ndef run(session):\n    return {\"status\": \"ok\"}\n$$",
    "CREATE OR REPLACE PROCEDURE LINKML_METRICS.RAW.EMPTY_SQL_PROBE() RETURNS VARIANT LANGUAGE SQL EXECUTE AS CALLER "
    "AS $$ BEGIN RETURN OBJECT_CONSTRUCT('status', 'ok'); END; $$",
]


def union_ms(intervals):
    total, end = 0.0, None
    for s, e in sorted(intervals):
        if end is None or s > end:
            total += e - s
            end = e
        elif e > end:
            total += e - end
            end = e
    return total


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--connection", default="perso")
    p.add_argument("--runs", type=int, default=5)
    a = p.parse_args()
    con = connect(a.connection)
    cur = con.cursor()
    cur.execute("ALTER SESSION SET USE_CACHED_RESULT = FALSE")
    for w in WITNESSES:
        cur.execute(w)
    calls = []
    for name, proc, args in SHAPES:
        ph = ", ".join(["%s"] * len(args))
        for i in range(a.runs):
            t = time.perf_counter()
            cur.execute(f"CALL LINKML_METRICS.RAW.{proc}({ph})", args)
            v = cur.fetchone()[0]
            res = json.loads(v) if isinstance(v, str) else v
            calls.append({"shape": name, "run": i + 1, "qid": cur.sfqid, "client_ms": (time.perf_counter() - t) * 1000,
                          "status": res["status"], "rows": res.get("row_count"), "handler": res.get("timing_ms", {})})
    for proc in ("EMPTY_PY_PROBE", "EMPTY_SQL_PROBE"):
        cur.execute(f"DROP PROCEDURE IF EXISTS LINKML_METRICS.RAW.{proc}()")
    time.sleep(2)
    hist = cur.execute(
        "SELECT query_id, query_type, start_time, end_time, total_elapsed_time, compilation_time, execution_time, "
        "queued_overload_time + queued_provisioning_time AS queued "
        "FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 1000)) ORDER BY start_time").fetchall()
    by_id = {h[0]: h for h in hist}
    out = []
    for c in calls:
        h = by_id.get(c["qid"])
        if not h:
            continue
        s, e = h[2], h[3]
        kids = [k for k in hist if k[0] != c["qid"] and k[2] >= s and s <= k[3] <= e]
        iv = [((k[2] - s).total_seconds() * 1000, (k[3] - s).total_seconds() * 1000) for k in kids]
        c.update({"call_ms": h[4], "children": len(kids), "children_wall_ms": union_ms(iv),
                  "children_sum_ms": sum(k[4] for k in kids),
                  "children_compile_ms": sum(k[5] for k in kids), "children_exec_ms": sum(k[6] for k in kids),
                  "first_child_ms": min((x[0] for x in iv), default=None),
                  "tail_ms": (e - max(k[3] for k in kids)).total_seconds() * 1000 if kids else None})
        c["overhead_ms"] = c["call_ms"] - c["children_wall_ms"]
        out.append(c)
    print("| Shape | Run | Status | Rows | Client ms | CALL elapsed ms | Before first child ms | Child queries | "
          "Children wall ms | Children sum ms (compile + exec) | After last child ms | Handler overhead ms | "
          "Handler timing (ms) | CALL query id |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    na = lambda v: "n/a" if v is None else f"{v:.0f}"  # noqa: E731
    for c in out:
        ht = ", ".join(f"{k.replace('_ms', '')} {v}" for k, v in c["handler"].items()) or "n/a"
        print(f"| {c['shape']} | {c['run']} | {c['status']} | {c['rows'] if c['rows'] is not None else 'n/a'} | "
              f"{c['client_ms']:.0f} | {c['call_ms']} | {na(c['first_child_ms'])} | {c['children']} | "
              f"{c['children_wall_ms']:.0f} | {c['children_sum_ms']} ({c['children_compile_ms']} + "
              f"{c['children_exec_ms']}) | {na(c['tail_ms'])} | {c['overhead_ms']:.0f} | {ht} | `{c['qid']}` |")
    print("\n| Shape | Median CALL ms | Median before first child ms | Median children wall ms | "
          "Median handler overhead ms | Overhead share |")
    print("|---|---|---|---|---|---|")
    for name, _, _ in SHAPES:
        cs = [c for c in out if c["shape"] == name]
        m = lambda k: statistics.median(c[k] for c in cs if c[k] is not None) if any(c[k] is not None for c in cs) else None  # noqa: E731
        print(f"| {name} | {m('call_ms'):.0f} | {na(m('first_child_ms'))} | {m('children_wall_ms'):.0f} | "
              f"{m('overhead_ms'):.0f} | {m('overhead_ms') / m('call_ms'):.0%} |")
    con.close()


if __name__ == "__main__":
    main()
