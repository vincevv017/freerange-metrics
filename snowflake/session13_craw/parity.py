"""
Session 13, step 3: parity of CLOSING_STOCK with FCT_STOCK_SNAPSHOT_GAPFILLED summed under the closing rule, every
member at every grain, for every quarter and year in the data, on QTY_EQ and VALUE. Then the median latency of 10 warm
CALLs. As LINKML_METRICS_ROLE with no secondary role, result cache off; read only (CALL of a procedure that reads).

    python snowflake/session13_craw/parity.py --out ~/work/assets/linkml-metrics-runs/s13/parity.json

One CALL per grain and basis carries all the complete periods (owner, step 3: at most 40 CALLs); the partial years
(2023, 2026) are each one more CALL, expected to be refused (AS_OF_NO_SNAPSHOT). The reference, per period and grain:
the members are the groups with a real snapshot row (gap_filled FALSE) in a month of the period; each closes at the sum
of the gap-filled view's rows in the period's last month (0 on a filled row). Items are joined through a DISTINCT
projection of the attributes the grain uses. The members that the gap-filled rows alone would add (a key's one
trailing filled month falling into the period, at 0) are counted apart.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import statistics
import sys
import time
from pathlib import Path

import snowflake.connector
import yaml

ROOT = Path(__file__).resolve().parents[2]
S = "LINKML_METRICS.RAW"
C = yaml.safe_load((ROOT / "contract" / "stock_coverage.yaml").read_text())
ATTRS = {a["id"]: (a["table"], a["column"]) for a in C["attributes"]}
GRAINS = [[a] for a in ATTRS] + [["family_code", "country_code"], ["sku_code", "country_code"],
                                 ["range_code", "batch_status"], ["region_code", "warehouse_type", "item_type"]]
COLUMNS = {"QTY_EQ": "stock_qty_eq", "VALUE": "stock_value_eur"}
ALIAS = {"DIM_ITEM": "i", "DIM_GEO": "g", "DIM_BATCH": "b", "DIM_WAREHOUSE": "w", "FCT_STOCK_SNAPSHOT": "s"}
KEY = {"DIM_ITEM": "item_id", "DIM_GEO": "country_id", "DIM_BATCH": "batch_id", "DIM_WAREHOUSE": "warehouse_id"}
MAX_CALLS = 40


def periods(first: dt.date, last: dt.date) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Complete quarters and years of the data (label, first month, last month), and the partial years."""
    out, partial = [], []
    for y in range(first.year, last.year + 1):
        for q in range(1, 5):
            a, b = dt.date(y, 3 * q - 2, 1), dt.date(y, 3 * q, 1)
            if a >= first and b <= last:
                out.append((f"{y}-Q{q}", a.isoformat(), b.isoformat()))
    for y in range(first.year, last.year + 1):
        a, b = dt.date(y, 1, 1), dt.date(y, 12, 1)
        (out.append((str(y), a.isoformat(), b.isoformat())) if a >= first and b <= last else partial.append(str(y)))
    return out, partial


def reference_sql(grain: list[str], basis: str, ps: list[tuple[str, str, str]]) -> str:
    tables = {ATTRS[a][0] for a in grain} - {"FCT_STOCK_SNAPSHOT"}
    item_cols = sorted({ATTRS[a][1] for a in grain if ATTRS[a][0] == "DIM_ITEM"})
    joins = []
    for t in sorted(tables):
        src = f"(SELECT DISTINCT item_id, {', '.join(item_cols)} FROM {S}.DIM_ITEM)" if t == "DIM_ITEM" else f"{S}.{t}"
        joins.append(f"JOIN {src} {ALIAS[t]} ON {ALIAS[t]}.{KEY[t]} = s.{KEY[t]}")
    sel = ", ".join(f"{ALIAS[ATTRS[a][0]]}.{ATTRS[a][1]} AS {a}" for a in grain)
    gl = ", ".join(grain)
    vals = ", ".join(f"('{l}', '{a}'::DATE, '{b}'::DATE)" for l, a, b in ps)
    on = " AND ".join(f"EQUAL_NULL(c.{a}, m.{a})" for a in grain)
    return f"""WITH p(label, first_month, last_month) AS (SELECT * FROM VALUES {vals}),
j AS (SELECT s.snapshot_month, s.gap_filled, s.{COLUMNS[basis]} AS qty, {sel}
      FROM {S}.FCT_STOCK_SNAPSHOT_GAPFILLED s {' '.join(joins)}),
members AS (SELECT p.label, {', '.join('j.' + a for a in grain)}, BOOLOR_AGG(NOT j.gap_filled) AS real
            FROM j JOIN p ON j.snapshot_month BETWEEN p.first_month AND p.last_month GROUP BY ALL),
closing AS (SELECT p.label, {', '.join('j.' + a for a in grain)}, SUM(j.qty) AS q
            FROM j JOIN p ON j.snapshot_month = p.last_month GROUP BY ALL)
SELECT m.label, {', '.join('m.' + a for a in grain)}, m.real, COALESCE(c.q, 0) AS q
FROM members m LEFT JOIN closing c ON c.label = m.label AND {on}"""


def call(cur, args: dict) -> tuple[dict, float, str]:
    t = time.perf_counter()
    cur.execute(f"CALL {S}.CLOSING_STOCK(" + ", ".join(f"{k} => %({k})s" for k in args) + ")", args)
    res = json.loads(cur.fetchone()[0])
    return res, time.perf_counter() - t, cur.sfqid


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"))
    cur = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH",
              "ALTER SESSION SET USE_CACHED_RESULT = FALSE", "ALTER SESSION SET QUERY_TAG = 'session13_parity'"):
        cur.execute(s)
    caller = [str(x) for x in cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone()]
    assert caller[1] == "LINKML_METRICS_ROLE", caller
    first, last = cur.execute(f"SELECT MIN(snapshot_month), MAX(snapshot_month) FROM {S}.FCT_STOCK_SNAPSHOT").fetchone()
    ps, partial = periods(first, last)
    max_periods = C["analysis_periods"][0]["max_periods"]
    chunks = [ps[i:i + max_periods] for i in range(0, len(ps), max_periods)]
    planned = len(GRAINS) * len(COLUMNS) * len(chunks) + len(partial)
    print(f"periods {len(ps)} ({ps[0][0]} to {ps[-1][0]}), partial {partial}; planned CALLs {planned}")
    if planned > MAX_CALLS:
        raise SystemExit(f"{planned} CALLs planned, above {MAX_CALLS}: stopped before any CALL")
    out: dict = {"caller": caller, "periods": [p[0] for p in ps], "partial": {}, "grains": [], "calls": 0}
    for y in partial:
        res, secs, qid = call(cur, {"PERIODS": json.dumps([y]), "GRAIN": '["family_code"]', "FILTERS": "{}",
                                    "BASIS": "VALUE", "TOTALS": "[]"})
        out["calls"] += 1
        out["partial"][y] = {"status": res["status"], "code": (res.get("refusal") or {}).get("code"),
                             "reason": (res.get("refusal") or {}).get("reason", "")[:200], "query_id": qid}
    for grain in GRAINS:
        for basis in COLUMNS:
            for chunk in chunks:
                res, secs, qid = call(cur, {"PERIODS": json.dumps([p[0] for p in chunk]), "GRAIN": json.dumps(grain),
                                            "FILTERS": "{}", "BASIS": basis, "TOTALS": "[]"})
                out["calls"] += 1
                cur.execute(reference_sql(grain, basis, chunk))
                ref_real, ref_trailing = {}, 0
                for r in cur.fetchall():
                    key = (r[0],) + tuple(r[1:1 + len(grain)])
                    if r[1 + len(grain)]:
                        ref_real[key] = float(r[2 + len(grain)])
                    else:
                        ref_trailing += 1
                entry = {"grain": grain, "basis": basis, "periods": len(chunk), "call_query_id": qid,
                         "status": res["status"], "seconds": round(secs, 3), "reference_members": len(ref_real),
                         "trailing_filled_members_not_counted": ref_trailing}
                if res["status"] != "ok":
                    entry["refusal"] = res["refusal"]
                else:
                    got = {(r["period"],) + tuple(r[x] for x in grain): float(r["closing_stock"]) for r in res["rows"]}
                    diff = sorted(set(got) ^ set(ref_real)) + sorted(k for k in set(got) & set(ref_real)
                                                                      if abs(got[k] - ref_real[k]) > 1e-4)
                    entry.update(members=len(got), differences=len(diff),
                                 first_differences=[[list(k), got.get(k), ref_real.get(k)] for k in diff[:10]],
                                 warnings=[w["code"] for w in res.get("warnings", [])])
                out["grains"].append(entry)
                print(grain, basis, entry["status"], entry.get("members"), entry.get("differences"),
                      (entry.get("refusal") or {}).get("code", ""), flush=True)
    # latency: the hero question, 10 warm CALLs after one discarded
    hero = {"PERIODS": '["2026-Q2"]', "GRAIN": '["sku_code", "country_code"]',
            "FILTERS": '{"family_code": ["SNACK_BARS"], "country_code": ["CH"]}', "BASIS": "QTY_EQ", "TOTALS": "[]"}
    call(cur, hero)
    lat = []
    for _ in range(10):
        res, secs, qid = call(cur, hero)
        lat.append({"client_s": round(secs, 3), "total_ms": res["timing_ms"]["total_ms"], "query_id": qid})
    out["latency"] = {"calls": lat, "median_client_s": statistics.median(x["client_s"] for x in lat),
                      "median_total_ms": statistics.median(x["total_ms"] for x in lat)}
    out["calls"] += 11
    ok = [g for g in out["grains"] if g["status"] == "ok"]
    out["summary"] = {"parity_calls": len(out["grains"]) + len(partial), "ok_calls": len(ok),
                      "members_compared": sum(g["members"] for g in ok),
                      "differences": sum(g["differences"] for g in ok),
                      "refused": [(g["grain"], g["basis"], g["refusal"]["code"]) for g in out["grains"] if g["status"] != "ok"],
                      "partial_years": {y: v["code"] for y, v in out["partial"].items()}}
    con.close()
    a.out.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({"summary": out["summary"], "latency": {k: v for k, v in out["latency"].items() if k != "calls"}},
                     indent=1, default=str))
    sys.exit(0 if out["summary"]["differences"] == 0 else 1)


if __name__ == "__main__":
    main()
