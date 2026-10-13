"""Session 8, D': the queries the skill script reports (query ids in its JSON output) must have run as LINKML_SVC,
LINKML_METRICS_ROLE, on LINKML_METRICS_WH. Read as LINKML_SVC from INFORMATION_SCHEMA.QUERY_HISTORY_BY_USER; an id not
found under LINKML_SVC is reported as such (the sandbox would then have run under another identity).

    python snowflake/phase4_others/d/identity_check.py <label> [<label> ...]
"""
import json
import re
import sys
from pathlib import Path

import snowflake.connector

LOG = Path.home() / "work" / "assets" / "linkml-metrics-runs" / "s8"
ids = {}
for label in sys.argv[1:]:
    s = json.loads((LOG / f"summary_{label}.json").read_text())
    for c in s["calls"]:
        for r in c.get("tool_results", []):
            for q in re.findall(r'query_id\\\\?"\s*:\s*\\\\?"([0-9a-f-]{36})', r.get("content") or ""):
                ids[q] = label
cur = snowflake.connector.connect(connection_name="linkml_svc").cursor()
cur.execute("USE SECONDARY ROLES NONE")
print("| Label | Query id | User | Role | Secondary roles in session | Warehouse | Query (start) |\n|---|---|---|---|---|---|---|")
bad = 0
for q, label in ids.items():
    cur.execute("SELECT user_name, role_name, warehouse_name, LEFT(query_text, 60) FROM TABLE(INFORMATION_SCHEMA."
                "QUERY_HISTORY_BY_USER(USER_NAME => 'LINKML_SVC', RESULT_LIMIT => 10000)) WHERE query_id = %s", (q,))
    row = cur.fetchone()
    if not row:
        bad += 1
        print(f"| {label} | `{q}` | **not found under LINKML_SVC** | | | | |")
        continue
    ok = row[0] == "LINKML_SVC" and row[1] == "LINKML_METRICS_ROLE" and row[2] == "LINKML_METRICS_WH"
    bad += not ok
    print(f"| {label} | `{q}` | {row[0]} | {row[1]} | n/a | {row[2]} | {row[3]} |")
print(f"\n{len(ids)} script queries, {bad} not as LINKML_SVC / LINKML_METRICS_ROLE / LINKML_METRICS_WH")
