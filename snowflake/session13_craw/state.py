"""
Session 13, step 3: read-only checks around the creation of C-raw, as LINKML_METRICS_ROLE with no secondary role.

    python snowflake/session13_craw/state.py frozen --out <run dir>/frozen_before.json     # before any CREATE
    python snowflake/session13_craw/state.py frozen --out <run dir>/frozen_after.json --compare <run dir>/frozen_before.json
    python snowflake/session13_craw/state.py procedure                                      # CLOSING_STOCK against its file

frozen: the six agents' SHOW VERSIONS (name, default, created_on, sha256 of the spec), and the sha256 of the frozen
procedures' DESCRIBE body, of the generated views' DDL and of the semantic views' YAML. --compare fails on any change.
procedure: DESCRIBE PROCEDURE CLOSING_STOCK; its body, arguments, return type, language and execute-as against
generated/closing_stock_procedure.sql.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parents[2]
S = "LINKML_METRICS.RAW"
AGENTS = ["LINKML_A", "LINKML_B1", "LINKML_B2", "LINKML_C", "LINKML_D", "LINKML_DP"]
PROCEDURES = {"STOCK_COVERAGE": 8, "STOCK_COVERAGE_PY": 8}
VIEWS = ["FCT_STOCK_SNAPSHOT_GAPFILLED", "B2_ITEM", "B2_STATUS", "B2_FORECAST_SPINE"]
SEMANTIC_VIEWS = ["LINKML_B2_SV", "LINKML_B1_SV", "AP_LINKLM", "CLOSING_STOCK_SV"]


def sha(x) -> str:
    return hashlib.sha256(str(x).encode()).hexdigest()


def rows(cur, sql: str) -> list[dict]:
    cur.execute(sql)
    cols = [d[0].lower() for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def describe_procedure(cur, name: str, n: int) -> dict:
    return {r["property"]: r["value"] for r in rows(cur, f"DESCRIBE PROCEDURE {S}.{name}({', '.join(['VARCHAR'] * n)})")}


def frozen(cur) -> dict:
    out: dict = {"agents": {}, "procedures": {}, "views": {}, "semantic_views": {}}
    for a in AGENTS:
        out["agents"][a] = [{"name": r["name"], "is_default": r["is_default"], "created_on": str(r["created_on"]),
                             "spec_sha256": sha(r["agent_spec"])} for r in rows(cur, f"SHOW VERSIONS IN AGENT {S}.{a}")]
    for p, n in PROCEDURES.items():
        d = describe_procedure(cur, p, n)
        out["procedures"][p] = {"body_sha256": sha(d.get("body")), "signature": d.get("signature")}
    for v in VIEWS:
        out["views"][v] = sha(cur.execute(f"SELECT GET_DDL('VIEW', '{S}.{v}')").fetchone()[0])
    for v in SEMANTIC_VIEWS:
        out["semantic_views"][v] = sha(cur.execute(f"SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('{S}.{v}')").fetchone()[0])
    return out


def procedure(cur) -> dict:
    text = (ROOT / "generated" / "closing_stock_procedure.sql").read_text()
    body = text.split("$$", 1)[1].rsplit("$$", 1)[0]
    d = describe_procedure(cur, "CLOSING_STOCK", 5)
    want_sig = "(" + ", ".join(f"{a} VARCHAR" for a in ("PERIODS", "GRAIN", "FILTERS", "BASIS", "TOTALS")) + ")"
    checks = {
        "body": d.get("body", "").strip() == body.strip(),
        "signature": re.sub(r"\s+", " ", d.get("signature", "")) == want_sig,
        "returns": d.get("returns") == "VARIANT",
        "language": d.get("language") == "SQL",
        "execute_as": d.get("execute as") == "CALLER",
    }
    return {"checks": checks, "described": {k: v for k, v in d.items() if k != "body"}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["frozen", "procedure"])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--compare", type=Path)
    a = ap.parse_args()
    con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"))
    cur = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE"):
        cur.execute(s)
    res = frozen(cur) if a.cmd == "frozen" else procedure(cur)
    res["caller"] = [str(x) for x in cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone()]
    con.close()
    if a.out:
        a.out.write_text(json.dumps(res, indent=1, default=str))
    if a.cmd == "procedure":
        print(json.dumps(res, indent=1, default=str))
        sys.exit(0 if all(res["checks"].values()) else 1)
    print({k: len(v) for k, v in res.items() if isinstance(v, dict)}, res["caller"])
    print({a_: [(v["name"], v["is_default"]) for v in vs] for a_, vs in res["agents"].items()})
    if a.compare:
        before = json.loads(a.compare.read_text())
        diff = [k for k in ("agents", "procedures", "views", "semantic_views") if before[k] != res[k]]
        print("unchanged:", not diff, "changed:", diff)
        sys.exit(1 if diff else 0)


if __name__ == "__main__":
    main()
