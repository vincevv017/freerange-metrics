"""
Session 13, step 5: the billed read of session 13, as ACCOUNTADMIN, one read-only batch, after 18:02 UTC (3 hours
after the last agent call, 15:02 UTC). The statements are the ones shown to the owner, run as written; the output goes
outside the repository.

    python snowflake/session13_craw/cost_read.py --out ~/work/assets/linkml-metrics-runs/s13/cost_read.json

Windows (UTC, 2026-10-08): step 0 incident 12:48 to 13:01 (counted apart); step 1 reads 13:02 to 13:04; step 3 dry run
13:43 to 13:45; step 3 13:59 to 14:23 (smoke 14:15 to 14:21); step 4 arm 14:37 to 15:03.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import snowflake.connector

STATEMENTS = {
    "S0_session": "USE SECONDARY ROLES NONE",
    "S0_role": "USE ROLE ACCOUNTADMIN",
    # S1. Agent usage, one row per request: the 4 smoke calls and the 56 arm calls, matched by REQUEST_ID afterwards.
    "S1_agent_usage": """SELECT START_TIME, END_TIME, REQUEST_ID, AGENT_NAME, USER_NAME, TOKEN_CREDITS, TOKENS, CREDITS_GRANULAR
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY
WHERE USER_NAME = 'LINKML_SVC'
  AND START_TIME >= '2026-10-08 14:10:00 +00:00'::TIMESTAMP_TZ
  AND START_TIME <  '2026-10-08 15:10:00 +00:00'::TIMESTAMP_TZ
ORDER BY START_TIME""",
    # S2. The day's metering by service: CORTEX_AGENTS against S1, CORTEX_AI_GUARDRAILS, WAREHOUSE_METERING.
    "S2_daily": """SELECT SERVICE_TYPE, CREDITS_USED_COMPUTE, CREDITS_USED_CLOUD_SERVICES, CREDITS_USED, CREDITS_BILLED
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY
WHERE USAGE_DATE = '2026-10-08'
ORDER BY SERVICE_TYPE""",
    # S3. Warehouse metering, the hours that hold the incident, step 1, step 3 and step 4 (12:00 to 16:00 UTC).
    "S3_warehouse_hours": """SELECT START_TIME, END_TIME, CREDITS_USED_COMPUTE, CREDITS_USED_CLOUD_SERVICES, CREDITS_USED
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE WAREHOUSE_NAME = 'LINKML_METRICS_WH'
  AND START_TIME >= '2026-10-08 12:00:00 +00:00'::TIMESTAMP_TZ
  AND START_TIME <  '2026-10-08 16:00:00 +00:00'::TIMESTAMP_TZ
ORDER BY START_TIME""",
    # S4. Resume and suspend events in the same hours: the running seconds of each window.
    "S4_warehouse_events": """SELECT TIMESTAMP, EVENT_NAME, EVENT_REASON, EVENT_STATE, CLUSTER_NUMBER
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_EVENTS_HISTORY
WHERE WAREHOUSE_NAME = 'LINKML_METRICS_WH'
  AND TIMESTAMP >= '2026-10-08 12:00:00 +00:00'::TIMESTAMP_TZ
  AND TIMESTAMP <  '2026-10-08 16:00:00 +00:00'::TIMESTAMP_TZ
ORDER BY TIMESTAMP""",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"))
    cur = con.cursor()
    out: dict = {}
    for name, sql in STATEMENTS.items():
        cur.execute(sql)
        if name.startswith("S0"):
            continue
        cols = [d[0].lower() for d in cur.description]
        out[name] = {"query_id": cur.sfqid, "rows": [dict(zip(cols, r)) for r in cur.fetchall()]}
        print(name, cur.sfqid, len(out[name]["rows"]), "rows")
    out["caller"] = [str(x) for x in cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone()]
    con.close()
    a.out.write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
