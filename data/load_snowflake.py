"""
Load data/output/ into LINKML_METRICS.RAW with write_pandas (quote_identifiers=False).

    python data/load_snowflake.py                      # connection "linkml" from ~/.snowflake/connections.toml
    python data/load_snowflake.py --connection perso   # role / warehouse / database are forced below either way
    python data/load_snowflake.py --replace            # CREATE OR REPLACE the seven tables (a reload)
    python data/load_snowflake.py --replace --tables DIM_ITEM   # reload these tables only (session 8c-0)

Without --replace, CREATE TABLE fails if a table already exists: replacing loaded data is an explicit choice.
Every session starts with USE SECONDARY ROLES NONE so nothing runs on privileges the project role lacks.
After the load, row counts and column sums are compared with the local files; any mismatch exits 1.
Each table's COMMENT carries the manifest digest, so the loaded data can be traced to the dataset's manifest.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

DATA_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_DIR.parent))

from generated.schema import TABLES  # noqa: E402

ROLE, WAREHOUSE, DATABASE, SCHEMA = "LINKML_METRICS_ROLE", "LINKML_METRICS_WH", "LINKML_METRICS", "RAW"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--connection", default="linkml")
    p.add_argument("--out", type=Path, default=DATA_DIR / "output")
    p.add_argument("--replace", action="store_true")
    p.add_argument("--tables", nargs="+", choices=list(TABLES), help="load only these tables (default: all seven)")
    a = p.parse_args()
    manifest = json.loads((a.out / "manifest.json").read_text())

    con = snowflake.connector.connect(connection_name=a.connection, role=ROLE, warehouse=WAREHOUSE,
                                      database=DATABASE, schema=SCHEMA)
    cur = con.cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    role, secondary = cur.execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone()
    if role != ROLE or json.loads(secondary)["roles"] != "":
        raise SystemExit(f"refusing to load: role={role} secondary={secondary}")
    print(f"session role={role} secondary roles={secondary}")

    failures = 0
    for name, cols in TABLES.items():
        if a.tables and name not in a.tables:
            continue
        df = pd.read_parquet(a.out / f"{name}.parquet")
        for c, t in cols.items():
            if t == "DATE":
                df[c] = pd.to_datetime(df[c]).dt.date
        fq = f"{DATABASE}.{SCHEMA}.{name}"
        comment = (f"linkml-metrics data; schema {manifest['schema_version']}; as_of={manifest['as_of']} "
                   f"seed={manifest['seed']} sha256={manifest['tables'][name]['sha256'][:16]}")
        ddl = ",\n  ".join(f"{c.upper()} {t}" for c, t in cols.items())
        create = "CREATE OR REPLACE TABLE" if a.replace else "CREATE TABLE"
        cur.execute(f"{create} {fq} (\n  {ddl}\n) COMMENT = '{comment}'")
        ok, _, nrows, _ = write_pandas(con, df, name, database=DATABASE, schema=SCHEMA,
                                       quote_identifiers=False, auto_create_table=False)

        # verify: row count + sum of every numeric column, against the local frame
        num = [c for c, t in cols.items() if t.startswith("NUMBER")]
        sums = ", ".join(f"SUM({c})" for c in num)
        remote = cur.execute(f"SELECT COUNT(*), {sums} FROM {fq}").fetchone()
        local = [len(df)] + [float(df[c].sum()) for c in num]
        same = remote[0] == local[0] and all(abs(float(r) - l) <= 1e-3 * max(1.0, abs(l))
                                             for r, l in zip(remote[1:], local[1:]))
        failures += not (ok and same)
        print(f"{'OK  ' if ok and same else 'FAIL'} {fq:40s} {remote[0]:>7d} rows (local {local[0]})")
    con.close()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
