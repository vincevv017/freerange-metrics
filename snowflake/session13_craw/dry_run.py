"""
Session 13, step 3 (owner): before any CREATE, the three statements of the generated CLOSING_STOCK run as plain
read-only SELECTs, with the bound values substituted as literals, in the order and with the checks the procedure's
Scripting applies. No object is created. As LINKML_METRICS_ROLE with no secondary role, result cache off.

    python snowflake/session13_craw/dry_run.py --out ~/work/assets/linkml-metrics-runs/s13/dry_run.json

Cases: the heroes (Q2 2026, SNACK_BARS x CH, at SKU grain with a country total, and at family grain) and
CS_LAST_MONTH_GAP of data/traps.yaml.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parents[2]
SQL = (ROOT / "generated" / "closing_stock_procedure.sql").read_text()
CASES = {
    "heroes_sku": {"PERIODS": '["2026-Q2"]', "GRAIN": '["sku_code", "country_code"]',
                   "FILTERS": '{"family_code": ["SNACK_BARS"], "country_code": ["CH"]}', "BASIS": "QTY_EQ",
                   "TOTALS": '[["country_code"]]'},
    "heroes_family": {"PERIODS": '["2026-Q2"]', "GRAIN": '["family_code", "country_code"]',
                      "FILTERS": '{"family_code": ["SNACK_BARS"], "country_code": ["CH"]}', "BASIS": "QTY_EQ",
                      "TOTALS": "[]"},
    "CS_LAST_MONTH_GAP": {"PERIODS": '["2026-Q2"]', "GRAIN": '["sku_code", "country_code"]',
                          "FILTERS": '{"sku_code": ["SKU-H11"], "country_code": ["CH"]}', "BASIS": "QTY_EQ",
                          "TOTALS": "[]"},
}


def lit(v: str) -> str:
    return "'" + v.replace("\\", "\\\\").replace("'", "''") + "'"


def statement(var: str) -> str:
    """The text of the SELECT ... INTO :<var> FROM ( ... ); statement's inner query."""
    m = re.search(r"INTO :" + var + r" FROM \(\n(.*?)\n    \);", SQL, flags=re.S)
    assert m, var
    return m.group(1)


def run(cur, sql: str, binds: dict[str, str], wrap: str) -> tuple[dict, str]:
    for k, v in binds.items():
        sql = re.sub(r":" + k + r"\b", lambda _: lit(v), sql)
    assert not re.search(r":(PERIODS|GRAIN|FILTERS|BASIS|TOTALS|periods_json|req)\b", sql)
    cur.execute(wrap.format(sql=sql))
    return json.loads(cur.fetchone()[0]), cur.sfqid


def emulate(cur, args: dict) -> dict:
    par, q1 = run(cur, statement("par"), args, "SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) FROM (\n{sql}\n)")
    out = {"query_ids": {"parameters": q1}}
    if par.get("P_RCODE"):
        return {**out, "status": "refused", "code": par["P_RCODE"], "reason": par["P_REASON"]}
    ctx, q2 = run(cur, statement("ctx"), {"periods_json": json.dumps(par["PERIODS"])},
                  "SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) FROM (\n{sql}\n)")
    out["query_ids"]["context"] = q2
    for code, why in ((ctx.get("RCODE"), ctx.get("REASON")), (par.get("Q_RCODE"), par.get("Q_REASON"))):
        if code:
            return {**out, "status": "refused", "code": code, "reason": why}
    req = json.dumps({"periods": ctx["PERIODS"], "basis": par["BASIS"], "grain": par["GRAIN"], "grains": par["GRAINS"],
                      "filters": par["FILTERS"], "used": par["USED"]})
    cv, q3 = run(cur, statement("cv"), {"req": req}, "SELECT CV FROM (\n{sql}\n)")
    out["query_ids"]["closing"] = q3
    for code, why in (("MASTER_DATA_FANOUT", cv.get("FANOUT_REASON")), ("DATA_QUALITY_FAILED", ctx.get("DQ_REASON")),
                      ("BASIS_NOT_COMPARABLE", cv.get("BASIS_REASON"))):
        if why:
            return {**out, "status": "refused", "code": code, "reason": why}
    return {**out, "status": "ok", "periods": ctx["PERIODS"], "rows": cv["ROWS"], "warnings": cv["WARNINGS"],
            "available": [ctx["AVAILABLE_FIRST"], ctx["AVAILABLE_LATEST"]]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"))
    cur = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH",
              "ALTER SESSION SET USE_CACHED_RESULT = FALSE", "ALTER SESSION SET QUERY_TAG = 'session13_dry_run'"):
        cur.execute(s)
    caller = [str(x) for x in cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone()]
    assert caller[1] == "LINKML_METRICS_ROLE", caller
    results = {"caller": caller}
    for name, args in CASES.items():
        try:
            results[name] = emulate(cur, args)
        except snowflake.connector.errors.ProgrammingError as e:
            results[name] = {"status": "error", "error": str(e)[:2000], "query_id": e.sfqid}
        print(name, json.dumps(results[name], indent=1, default=str)[:3000])
    con.close()
    a.out.write_text(json.dumps(results, indent=1, default=str))


if __name__ == "__main__":
    main()
