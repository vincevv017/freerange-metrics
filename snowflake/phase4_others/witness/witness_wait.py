"""Session 8, step 1: latency witness with a 2 s CALL. LINKML_METRICS.RAW.LINKML_WITNESS_PROBE, one generic tool on
WITNESS_SQL (SQL Scripting, SYSTEM$WAIT(2) before RETURN).

    python snowflake/phase4_others/witness/witness_wait.py create             # procedure, then the agent (8a spec)
    python snowflake/phase4_others/witness/witness_wait.py versions
    python snowflake/phase4_others/witness/witness_wait.py warm               # before each agent call
    python snowflake/phase4_others/witness/witness_wait.py extract <out.json> # whole trace, outside the repository
    python snowflake/phase4_others/witness/witness_wait.py drop               # the agent, then the procedure

Run as perso, USE SECONDARY ROLES NONE, LINKML_METRICS_ROLE. The agent spec is the reviewed session 8a file
snowflake/phase4_agent_c/witness/witness_agent.yaml, unchanged (bound to WITNESS_SQL), so that the only difference
with session 8a is the procedure's 2 s wait. Agent calls go through snowflake/probe_b/mount/run_call.py (budget s8,
policy w) as LINKML_SVC.
"""

import json
import sys
from pathlib import Path

import snowflake.connector
import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
AGENT = "LINKML_METRICS.RAW.LINKML_WITNESS_PROBE"
SPEC = ROOT / "snowflake" / "phase4_agent_c" / "witness" / "witness_agent.yaml"

con = snowflake.connector.connect(connection_name="perso")
cur = con.cursor()
cur.execute("USE SECONDARY ROLES NONE")
cur.execute("USE ROLE LINKML_METRICS_ROLE")


def spec() -> tuple[dict, str]:
    s = yaml.safe_load(SPEC.read_text())
    for k in ("orchestration", "response"):
        assert isinstance(s["instructions"][k], str)
    assert s["tool_resources"]["witness"]["identifier"] == "LINKML_METRICS.RAW.WITNESS_SQL"
    text = yaml.safe_dump(s, sort_keys=False, allow_unicode=True, width=1000)
    assert yaml.safe_load(text) == s
    return s, text


def versions(want: dict) -> None:
    rows = cur.execute(f"SHOW VERSIONS IN AGENT {AGENT}").fetchall()
    cols = [d[0] for d in cur.description]
    for r in map(lambda x: dict(zip(cols, x)), rows):
        print(r["name"] or "LIVE", "default" if r["is_default"] == "true" else "", "spec equal:",
              json.loads(r["agent_spec"]) == want)


cmd = sys.argv[1]
if cmd == "create":
    for c in con.execute_string((HERE / "witness_wait.sql").read_text()):
        print(c.sfqid, c.fetchall())
    s, text = spec()
    cur.execute(f"CREATE AGENT {AGENT} COMMENT = 'Session 8 latency witness (2 s CALL), dropped after its traces' "
                f"FROM SPECIFICATION $${text}$$")
    print("create agent", cur.sfqid)
    versions(s)
elif cmd == "versions":
    versions(spec()[0])
elif cmd == "warm":
    cur.execute("USE WAREHOUSE LINKML_METRICS_WH")
    cur.execute("SELECT SUM(SEQ4()) FROM TABLE(GENERATOR(ROWCOUNT => 1000))")
    q = cur.sfqid
    cur.execute("SHOW WAREHOUSES LIKE 'LINKML_METRICS_WH'")
    state = dict(zip([d[0] for d in cur.description], cur.fetchone()))["state"]
    print("warm", q, state)
    assert state == "STARTED", state
elif cmd == "extract":
    cur.execute("SELECT * FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS('LINKML_METRICS', 'RAW', "
                "'LINKML_WITNESS_PROBE', 'CORTEX AGENT'))")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    Path(sys.argv[2]).write_text(json.dumps(rows, default=str))
    print("extracted", len(rows), "rows,", len({json.loads(r["RECORD_ATTRIBUTES"]).get("ai.observability.record_id")
                                                 if isinstance(r["RECORD_ATTRIBUTES"], str)
                                                 else (r["RECORD_ATTRIBUTES"] or {}).get("ai.observability.record_id")
                                                 for r in rows}), "records")
elif cmd == "drop":
    cur.execute(f"DROP AGENT IF EXISTS {AGENT}")
    print("drop agent", cur.sfqid)
    cur.execute("DROP PROCEDURE IF EXISTS LINKML_METRICS.RAW.WITNESS_SQL(VARCHAR)")
    print("drop procedure", cur.sfqid)
print(cur.execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone())
