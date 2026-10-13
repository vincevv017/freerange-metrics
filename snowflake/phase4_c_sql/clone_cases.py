"""
Session 8b, decision 4: HORIZON_NOT_LOADED and DATA_QUALITY_FAILED, exercised on zero-copy clones of RAW in a test
schema owned by the project role (RAW is never written), on both procedures. Owner's plan of 2026-10-04.

    python snowflake/phase4_c_sql/clone_cases.py [--out <run dir>/clone_cases.json]

1. CREATE SCHEMA LINKML_METRICS.S8B_DQ_TEST; one zero-copy clone per RAW table.
2. Both procedures generated with `compiler/gen_procedure.py --schema` into the run folder and created there.
3. Four defects, each on a fresh clone of the table it changes; for each, two requests on both procedures: one whose
   grain or filters use the columns of the faulty table, one that does not.
4. DROP SCHEMA ... CASCADE, also on failure.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parents[2]
TEST = "LINKML_METRICS.S8B_DQ_TEST"
RAW = "LINKML_METRICS.RAW"
TABLES = ["DIM_CALENDAR", "DIM_GEO", "DIM_ITEM", "DIM_WAREHOUSE", "DIM_BATCH", "FCT_STOCK_SNAPSHOT", "FCT_FORECAST"]
RUN = Path(os.path.expanduser("~/work/assets/linkml-metrics-runs/s8b"))
M = json.dumps(["2026-06-01"])
# request using the faulty table's columns, request that does not
GEO_USED = (M, "QTY_EQ", json.dumps(["family_code", "country_code"]), json.dumps({"family_code": ["PANTRY_FLOUR"], "country_code": ["FR"]}), "[]")
GEO_UNUSED = (M, "QTY_EQ", json.dumps(["family_code"]), json.dumps({"family_code": ["PANTRY_FLOUR"]}), "[]")
DEFECTS = [
    ("HORIZON_NOT_LOADED, calendar", "DIM_CALENDAR", [f"DELETE FROM {TEST}.DIM_CALENDAR WHERE month_start > '2028-05-01'"],
     # the calendar has no attribute of the contract: the "unused" request is any request
     GEO_USED, GEO_UNUSED),
    ("HORIZON_NOT_LOADED, forecast", "FCT_FORECAST", [f"DELETE FROM {TEST}.FCT_FORECAST WHERE forecast_month > '2028-05-01'"],
     GEO_USED, GEO_UNUSED),
    ("DATA_QUALITY_FAILED, QE_GEO_GRAIN", "DIM_GEO",
     [f"INSERT INTO {TEST}.DIM_GEO SELECT * FROM {TEST}.DIM_GEO WHERE country_code = 'FR'"], GEO_USED, GEO_UNUSED),
    ("DATA_QUALITY_FAILED, QE_COUNTRY_REGION", "DIM_GEO",
     [f"INSERT INTO {TEST}.DIM_GEO SELECT (SELECT MAX(country_id) + 1 FROM {TEST}.DIM_GEO), country_code, country_name, "
      f"'NORDIC', 'Nordics' FROM {TEST}.DIM_GEO WHERE country_code = 'FR'"], GEO_USED, GEO_UNUSED),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"))
    cur = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH"):
        cur.execute(s)
    log, results = [], []

    def run(sql, binds=None):
        cur.execute(sql, binds)
        log.append({"sql": sql[:200], "query_id": cur.sfqid})
        return cur

    try:
        run(f"CREATE SCHEMA {TEST} COMMENT = 'Session 8b, decision 4: zero-copy clones of RAW, dropped at the end'")
        for t in TABLES:
            run(f"CREATE TABLE {TEST}.{t} CLONE {RAW}.{t}")
        for target in ("python", "sql"):
            out = RUN / f"clone_procedure_{target}.sql"
            subprocess.run([sys.executable, "compiler/gen_procedure.py", "--target", target, "--schema", TEST, "--out", str(out)],
                           cwd=ROOT, check=True, capture_output=True)
            for c in con.execute_string(out.read_text()):
                log.append({"sql": f"deploy {target}", "query_id": c.sfqid})
        procs = {"python": f"{TEST}.STOCK_COVERAGE", "sql": f"{TEST}.STOCK_COVERAGE_SQL"}
        for name, table, changes, used, unused in DEFECTS:
            run(f"CREATE OR REPLACE TABLE {TEST}.{table} CLONE {RAW}.{table}")
            for s in changes:
                run(s)
            for label, args in (("uses the faulty columns", used), ("does not", unused)):
                answers = {}
                for p, proc in procs.items():
                    res = json.loads(run(f"CALL {proc}(%s, %s, %s, %s, %s)", args).fetchone()[0])
                    answers[p] = res
                same = all(answers["python"].get(k) == answers["sql"].get(k) for k in ("status", "refusal"))
                r = {"defect": name, "request": label, "args": args, "same_code_and_message": same,
                     "python": {k: answers["python"].get(k) for k in ("status", "refusal", "row_count")},
                     "sql": {k: answers["sql"].get(k) for k in ("status", "refusal", "row_count")},
                     "query_ids": {p: v["lineage"]["query_ids"] for p, v in answers.items()}}
                results.append(r)
                print(json.dumps({k: r[k] for k in ("defect", "request", "same_code_and_message", "python", "sql")}))
            run(f"CREATE OR REPLACE TABLE {TEST}.{table} CLONE {RAW}.{table}")
    finally:
        run(f"DROP SCHEMA IF EXISTS {TEST} CASCADE")
        cur.execute(f"SHOW SCHEMAS LIKE 'S8B_DQ_TEST' IN DATABASE LINKML_METRICS")
        print("schema left after DROP:", cur.fetchall())
        con.close()
    if a.out:
        a.out.write_text(json.dumps({"results": results, "statements": log}, indent=1, default=str))


if __name__ == "__main__":
    main()
