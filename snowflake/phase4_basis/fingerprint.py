"""
Session 8c-0: fingerprint of the seven RAW tables on the account, before and after the DIM_ITEM reload.

    python snowflake/phase4_basis/fingerprint.py --out <run dir>/fingerprint_<label>.json

Per table: row count, HASH_AGG(*) (order-independent, over every column) and the table COMMENT (which carries the
first 16 hex of the CSV sha256 in the manifest of the dataset loaded). Run as perso with the project role and no
secondary role. A fact table whose count, HASH_AGG or comment changes is a stop condition of the session.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from generated.schema import TABLES  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--connection", default="perso")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    con = snowflake.connector.connect(connection_name=a.connection, role="LINKML_METRICS_ROLE",
                                      warehouse="LINKML_METRICS_WH", database="LINKML_METRICS", schema="RAW")
    cur = con.cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    out = {}
    for t in TABLES:
        n, h = cur.execute(f"SELECT COUNT(*), HASH_AGG(*) FROM LINKML_METRICS.RAW.{t}").fetchone()
        cur.execute(f"SHOW TABLES LIKE '{t}' IN SCHEMA LINKML_METRICS.RAW")
        cols = [d[0] for d in cur.description]
        comment = dict(zip(cols, cur.fetchone()))["comment"]
        out[t] = {"rows": n, "hash_agg": str(h), "comment": comment}
        print(f"{t:20s} {n:>7d} {h:>22} {comment}")
    con.close()
    a.out.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
