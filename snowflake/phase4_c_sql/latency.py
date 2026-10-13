"""
Session 8b, step 2: direct latency of both procedures on the hero cases, warm warehouse, 5 calls each, no agent.

    python snowflake/phase4_c_sql/latency.py [--out <run dir>/latency.json]

Per CALL: client time, the CALL's elapsed and compilation time, and its child queries (same session, starting inside
the CALL) with their compilation and execution times, read from INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION after the
calls (outside the procedures). USE_CACHED_RESULT = FALSE. The two procedures alternate call by call.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import snowflake.connector
import yaml

ROOT = Path(__file__).resolve().parents[2]
TRAPS = {t["id"]: t for t in yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())["traps"]}
PROCS = {"python": "LINKML_METRICS.RAW.STOCK_COVERAGE_PY", "sql": "LINKML_METRICS.RAW.STOCK_COVERAGE"}   # after the swap
HEROES = ["T1", "T2", "T3", "T4", "T7", "T8", "NO_DEMAND", "BEYOND_H", "BULK_SCOPE", "T9"]


def args_for(tid, unit="QTY_EQ"):
    """Named arguments (contract 0.5.0: basis follows filters and is optional), as the agent calls the tool."""
    t = TRAPS[tid]["query"]
    f = {a: v if isinstance(v, list) else [v] for a, v in t["filters"].items()}
    return {"AS_OF_MONTHS": json.dumps(["2026-06-01"]), "GRAIN": json.dumps(t["grain"]), "FILTERS": json.dumps(f),
            "BASIS": unit, "TOTALS": "[]"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    ap.add_argument("--calls", type=int, default=5)
    ap.add_argument("--procs", default="python,sql")
    ap.add_argument("--cases", default=",".join(HEROES), help="session 8c-0: a subset of the heroes")
    a = ap.parse_args()
    procs = {k: PROCS[k] for k in a.procs.split(",")}
    con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"))
    cur = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH",
              "ALTER SESSION SET USE_CACHED_RESULT = FALSE"):
        cur.execute(s)
    cur.execute("SELECT SUM(SEQ4()) FROM TABLE(GENERATOR(ROWCOUNT => 1000))")          # warm the warehouse
    runs = []
    heroes = [h for h in a.cases.split(",") if h]
    for tid in heroes:
        for n in range(a.calls):
            for name, proc in procs.items():
                t = time.perf_counter()
                args = args_for(tid)
                cur.execute(f"CALL {proc}(" + ", ".join(f"{k} => %({k})s" for k in args) + ")", args)
                res = json.loads(cur.fetchone()[0])
                runs.append({"case": tid, "proc": name, "n": n + 1, "client_ms": round((time.perf_counter() - t) * 1000),
                             "query_id": cur.sfqid, "status": res["status"], "timing_ms": res.get("timing_ms")})
    time.sleep(5)
    cur.execute("SELECT query_id, session_id, start_time, end_time, total_elapsed_time, compilation_time, execution_time, "
                "queued_provisioning_time, queued_overload_time, LEFT(query_text, 60) FROM TABLE("
                "LINKML_METRICS.INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 10000))")
    cols = [d[0].lower() for d in cur.description]
    hist = [dict(zip(cols, r)) for r in cur.fetchall()]
    by_id = {h["query_id"]: h for h in hist}
    for r in runs:
        k = by_id[r["query_id"]]
        kids = [h for h in hist if h["query_id"] != k["query_id"] and k["start_time"] <= h["start_time"] <= k["end_time"]]
        r.update(call_ms=k["total_elapsed_time"], call_compile_ms=k["compilation_time"],
                 queued_ms=k["queued_provisioning_time"] + k["queued_overload_time"], children=len(kids),
                 children_compile_ms=sum(h["compilation_time"] for h in kids),
                 children_exec_ms=sum(h["execution_time"] for h in kids))
    con.close()
    print("| Case | Procedure | Median CALL ms | Min / max | Median children | Median client ms |")
    print("|---|---|---|---|---|---|")
    for tid in heroes:
        for name in procs:
            rs = [r for r in runs if r["case"] == tid and r["proc"] == name]
            calls = [r["call_ms"] for r in rs]
            print(f"| {tid} | {name} | {statistics.median(calls):.0f} | {min(calls)} / {max(calls)} | "
                  f"{statistics.median(r['children'] for r in rs):.0f} | {statistics.median(r['client_ms'] for r in rs):.0f} |")
    for name in procs:
        calls = [r["call_ms"] for r in runs if r["proc"] == name]
        print(f"all heroes, {name}: median CALL {statistics.median(calls):.0f} ms, min {min(calls)}, max {max(calls)}, n {len(calls)}")
    if a.out:
        a.out.write_text(json.dumps(runs, indent=1, default=str))


if __name__ == "__main__":
    main()
