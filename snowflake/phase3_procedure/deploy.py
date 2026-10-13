"""
Deploy a generated SQL file (default generated/stock_coverage_procedure.sql) as LINKML_METRICS_ROLE with no
secondary role.

    python snowflake/phase3_procedure/deploy.py [--connection perso] [--file generated/closing_stock_sv.sql]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parents[2]


def connect(name: str):
    con = snowflake.connector.connect(connection_name=name)
    cur = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH",
              "USE SCHEMA LINKML_METRICS.RAW"):
        cur.execute(s)
    return con


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--connection", default="perso")
    p.add_argument("--file", default="generated/stock_coverage_procedure.sql")
    a = p.parse_args()
    con = connect(a.connection)
    for cur in con.execute_string((ROOT / a.file).read_text()):
        print(cur.fetchone(), cur.sfqid)
    con.close()


if __name__ == "__main__":
    main()
