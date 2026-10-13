"""
Session 13, step 1b: volume of the objects behind each configuration, and the bytes one question scans on each path.
Read only, as LINKML_METRICS_ROLE with no secondary role, result cache off; no agent call.

    python snowflake/session13_craw/volume.py --out ~/work/assets/linkml-metrics-runs/s13/volume.json

1. Row counts of FCT_STOCK_SNAPSHOT, FCT_STOCK_SNAPSHOT_GAPFILLED, FCT_FORECAST and B2_FORECAST_SPINE, with the counts
   that the growth formula uses (keys, months, pairs, analysis months, statuses), and INFORMATION_SCHEMA.TABLES
   (table type, stored bytes).
2. One closing stock question (CS_FAMILY: SNACK_BARS x CH, Q2 2026) and one coverage question (T1: PANTRY_FLOUR x FR,
   June 2026), each on the path B2 and C take (the SQL the agent wrote in the campaign, its logical tables replaced by
   their physical objects; and the qualified SEMANTIC_VIEW form) and on the raw path (the closing rule on
   FCT_STOCK_SNAPSHOT, as the CLOSING_STOCK procedure will read it; the STOCK_COVERAGE procedure).
3. Bytes scanned, partitions, rows and elapsed time of each statement, from INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION
   (this session's own queries; a procedure's statements are matched by its lineage query ids).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import snowflake.connector

S = "LINKML_METRICS.RAW"
COUNTS = {
    "FCT_STOCK_SNAPSHOT": f"SELECT COUNT(*) AS rows_, COUNT(DISTINCT batch_id, warehouse_id) AS keys_, "
                          f"COUNT(DISTINCT snapshot_month) AS months_, COUNT(DISTINCT item_id, country_id) AS pairs_ "
                          f"FROM {S}.FCT_STOCK_SNAPSHOT",
    "FCT_STOCK_SNAPSHOT_GAPFILLED": f"SELECT COUNT(*) AS rows_, COUNT_IF(gap_filled) AS filled_, "
                                    f"COUNT(DISTINCT batch_id, warehouse_id) AS keys_, COUNT(DISTINCT snapshot_month) AS months_ "
                                    f"FROM {S}.FCT_STOCK_SNAPSHOT_GAPFILLED",
    "FCT_FORECAST": f"SELECT COUNT(*) AS rows_, COUNT(DISTINCT item_id, country_id) AS pairs_, "
                    f"COUNT(DISTINCT forecast_month) AS months_ FROM {S}.FCT_FORECAST",
    "B2_FORECAST_SPINE": f"SELECT COUNT(*) AS rows_, COUNT(DISTINCT as_of_month) AS analysis_months_, "
                         f"COUNT(DISTINCT item_id, country_id) AS pairs_, COUNT(DISTINCT batch_status) AS statuses_ "
                         f"FROM {S}.B2_FORECAST_SPINE",
}
STORAGE = (f"SELECT table_name, table_type, row_count, bytes FROM LINKML_METRICS.INFORMATION_SCHEMA.TABLES "
           f"WHERE table_schema = 'RAW' AND table_name IN ('FCT_STOCK_SNAPSHOT', 'FCT_STOCK_SNAPSHOT_GAPFILLED', "
           f"'FCT_FORECAST', 'B2_FORECAST_SPINE', 'B2_ITEM', 'DIM_ITEM', 'DIM_GEO') ORDER BY table_name")
CS_AGENT = ("SELECT i.family_code, g.country_code, SUM(s.stock_qty_eq) AS closing_stock_qty_eq FROM {stock} AS s "
            f"JOIN {S}.B2_ITEM AS i ON s.item_id = i.item_id JOIN {S}.DIM_GEO AS g ON s.country_id = g.country_id "
            "WHERE i.family_code = 'SNACK_BARS' AND g.country_code = 'CH' AND s.snapshot_month = '2026-06-01' "
            "GROUP BY i.family_code, g.country_code")        # C's campaign SQL for CS_FAMILY (summary_c_cs_family_*)
QUESTIONS = {
    "closing_b2_agent_sql": CS_AGENT.format(stock=f"{S}.FCT_STOCK_SNAPSHOT_GAPFILLED"),
    "closing_b2_semantic_view": (f"SELECT * FROM SEMANTIC_VIEW({S}.LINKML_B2_SV DIMENSIONS item.family_code, "
                                 "geo.country_code, calendar.year_quarter METRICS stock.closing_stock_qty_eq "
                                 "WHERE item.family_code = 'SNACK_BARS' AND geo.country_code = 'CH' "
                                 "AND calendar.year_quarter = '2026-Q2')"),
    "closing_raw_last_month_sql": CS_AGENT.format(stock=f"{S}.FCT_STOCK_SNAPSHOT"),
    "closing_raw_rule": (   # the closing rule on the raw snapshot: members with a snapshot in the period, the last month only
        f"WITH r AS (SELECT s.item_id, s.country_id, s.snapshot_month, s.stock_qty_eq FROM {S}.FCT_STOCK_SNAPSHOT s "
        f"JOIN {S}.DIM_GEO g ON g.country_id = s.country_id "
        "WHERE g.country_code = 'CH' AND s.snapshot_month BETWEEN '2026-04-01' AND '2026-06-01'), "
        f"i AS (SELECT DISTINCT item_id, sku_code, family_code FROM {S}.DIM_ITEM WHERE family_code = 'SNACK_BARS') "
        "SELECT i.sku_code, SUM(IFF(r.snapshot_month = '2026-06-01', r.stock_qty_eq, 0)) AS closing_stock_qty_eq "
        "FROM r JOIN i ON i.item_id = r.item_id GROUP BY ROLLUP (i.sku_code) ORDER BY 1"),
    "coverage_b2_semantic_view": (f"SELECT * FROM SEMANTIC_VIEW({S}.LINKML_B2_SV DIMENSIONS item.family_code, "
                                  "geo.country_code, item.dimension METRICS coverage_months_qty_eq "
                                  "WHERE calendar.month_start = '2026-06-01' AND item.family_code = 'PANTRY_FLOUR' "
                                  "AND geo.country_code = 'FR' AND item.item_type = 'STANDARD')"),   # B2's campaign SQL, T1
}
COVERAGE_CALL = {"AS_OF_MONTHS": '["2026-06-01"]', "GRAIN": '["family_code", "country_code"]',
                 "FILTERS": '{"family_code": ["PANTRY_FLOUR"], "country_code": ["FR"]}', "BASIS": "QTY_EQ", "TOTALS": "[]"}
HISTORY_COLS = ("query_id", "bytes_scanned", "partitions_scanned", "partitions_total", "rows_produced",
                "total_elapsed_time", "compilation_time", "execution_time", "query_type")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"))
    cur = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH",
              "ALTER SESSION SET USE_CACHED_RESULT = FALSE", "ALTER SESSION SET QUERY_TAG = 'session13_volume'"):
        cur.execute(s)
    out: dict = {"caller": [str(x) for x in cur.execute(
        "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone()], "counts": {}, "questions": {}}
    assert out["caller"][1] == "LINKML_METRICS_ROLE", out["caller"]
    cur.execute("SELECT SUM(SEQ4()) FROM TABLE(GENERATOR(ROWCOUNT => 1000))")   # warm
    for name, q in COUNTS.items():
        cur.execute(q)
        out["counts"][name] = dict(zip([d[0].lower().rstrip("_") for d in cur.description], cur.fetchone()))
        out["counts"][name]["query_id"] = cur.sfqid
    cur.execute(STORAGE)
    out["storage"] = [dict(zip([d[0].lower() for d in cur.description], r)) for r in cur.fetchall()]
    for name, q in QUESTIONS.items():
        cur.execute(q)
        out["questions"][name] = {"sql": q, "query_ids": [cur.sfqid],
                                  "result": [[str(v) for v in r] for r in cur.fetchall()]}
    cur.execute("CALL LINKML_METRICS.RAW.STOCK_COVERAGE(" + ", ".join(f"{k} => %({k})s" for k in COVERAGE_CALL) + ")",
                COVERAGE_CALL)
    res = json.loads(cur.fetchone()[0])
    lineage = res.get("lineage", {}).get("query_ids", {})
    ids = [v for vs in lineage.values() for v in (vs if isinstance(vs, list) else [vs]) if v]
    out["questions"]["coverage_procedure"] = {"call": COVERAGE_CALL, "call_query_id": cur.sfqid, "query_ids": ids,
                                              "lineage": lineage, "status": res.get("status"),
                                              "result": res.get("rows")}
    time.sleep(10)
    cur.execute("SELECT * FROM TABLE(LINKML_METRICS.INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 10000))")
    cols = [d[0].lower() for d in cur.description]
    hist = {r["query_id"]: r for r in (dict(zip(cols, x)) for x in cur.fetchall())}
    for q in out["questions"].values():
        q["history"] = [{k: hist[i].get(k) for k in HISTORY_COLS} if i in hist else {"query_id": i, "missing": True}
                        for i in q["query_ids"]]
        q["bytes_scanned"] = sum(h.get("bytes_scanned") or 0 for h in q["history"])
    for c in out["counts"].values():
        h = hist.get(c["query_id"], {})
        c["bytes_scanned"] = h.get("bytes_scanned")
    con.close()
    a.out.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({"counts": out["counts"], "storage": out["storage"],
                      "bytes": {k: (v["bytes_scanned"], len(v["query_ids"])) for k, v in out["questions"].items()}},
                     indent=1, default=str))


if __name__ == "__main__":
    main()
