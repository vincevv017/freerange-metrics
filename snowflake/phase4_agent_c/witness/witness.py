"""Session 8a latency witness: LINKML_METRICS.RAW.LINKML_WITNESS_PROBE, one generic tool on an empty procedure.

    python snowflake/phase4_agent_c/witness/witness.py create     # both procedures, the agent bound to WITNESS_SQL
    python snowflake/phase4_agent_c/witness/witness.py rebind     # five-beat cycle, bound to WITNESS_PY
    python snowflake/phase4_agent_c/witness/witness.py versions   # SHOW VERSIONS: identifier of each version
    python snowflake/phase4_agent_c/witness/witness.py warm       # before each agent call: keep the warehouse running
    python snowflake/phase4_agent_c/witness/witness.py drop       # the agent, then both procedures

Run as perso, USE SECONDARY ROLES NONE, LINKML_METRICS_ROLE. Agent calls go through snowflake/probe_b/mount/run_call.py
(budget s8a, policy w) as LINKML_SVC. `warm` runs SELECT 1 and, because SELECT 1 does not resume a suspended
warehouse (measured: state still SUSPENDED after it), a GENERATOR sum that does; it then asserts the state is STARTED.
No warehouse parameter is changed.
"""

import json
import sys
from pathlib import Path

import snowflake.connector
import yaml

HERE = Path(__file__).resolve().parent
AGENT = "LINKML_METRICS.RAW.LINKML_WITNESS_PROBE"
PY = "LINKML_METRICS.RAW.WITNESS_PY"

con = snowflake.connector.connect(connection_name="perso")
cur = con.cursor()
cur.execute("USE SECONDARY ROLES NONE")
cur.execute("USE ROLE LINKML_METRICS_ROLE")


def spec(identifier=None) -> tuple[dict, str]:
    s = yaml.safe_load((HERE / "witness_agent.yaml").read_text())
    if identifier:
        s["tool_resources"]["witness"]["identifier"] = identifier
    for k in ("orchestration", "response"):
        assert isinstance(s["instructions"][k], str)
    text = yaml.safe_dump(s, sort_keys=False, allow_unicode=True, width=1000)
    assert yaml.safe_load(text) == s
    return s, text


def versions(want: dict) -> None:
    rows = cur.execute(f"SHOW VERSIONS IN AGENT {AGENT}").fetchall()
    cols = [d[0] for d in cur.description]
    for r in map(lambda x: dict(zip(cols, x)), rows):
        sp = json.loads(r["agent_spec"])
        print(r["name"] or "LIVE", "default" if r["is_default"] == "true" else "",
              sp["tool_resources"]["witness"]["identifier"], "spec equal:", sp == want)


cmd = sys.argv[1]
if cmd == "create":
    for c in con.execute_string((HERE / "witness.sql").read_text()):
        print(c.sfqid, c.fetchall())
    s, text = spec()
    cur.execute(f"CREATE AGENT {AGENT} COMMENT = 'Session 8a latency witness, dropped at the end of the session' "
                f"FROM SPECIFICATION $${text}$$")
    print("create agent", cur.sfqid)
    versions(s)
elif cmd == "rebind":
    s, text = spec(PY)
    cur.execute(f"ALTER AGENT {AGENT} MODIFY LIVE VERSION SET SPECIFICATION = $${text}$$")
    print("modify live", cur.sfqid)
    cur.execute(f"ALTER AGENT {AGENT} COMMIT")
    print("commit", cur.sfqid)
    cur.execute(f"ALTER AGENT {AGENT} ADD LIVE VERSION FROM LAST")
    print("add live from last", cur.sfqid)
    rows = cur.execute(f"SHOW VERSIONS IN AGENT {AGENT}").fetchall()
    cols = [d[0] for d in cur.description]
    last = max((dict(zip(cols, r))["name"] for r in rows if dict(zip(cols, r))["name"]),
               key=lambda n: int(n.split("$")[1]))
    cur.execute(f"ALTER AGENT {AGENT} SET DEFAULT_VERSION = '{last}'")
    print("default", last, cur.sfqid)
    versions(s)
elif cmd == "versions":
    versions(spec(PY if len(sys.argv) > 2 and sys.argv[2] == "py" else None)[0])
elif cmd == "warm":
    cur.execute("USE WAREHOUSE LINKML_METRICS_WH")
    cur.execute("SELECT 1")
    q1 = cur.sfqid
    cur.execute("SELECT SUM(SEQ4()) FROM TABLE(GENERATOR(ROWCOUNT => 1000))")
    q2 = cur.sfqid
    cur.execute("SHOW WAREHOUSES LIKE 'LINKML_METRICS_WH'")
    state = dict(zip([d[0] for d in cur.description], cur.fetchone()))["state"]
    print("warm", q1, q2, state)
    assert state == "STARTED", state
elif cmd == "drop":
    cur.execute(f"DROP AGENT IF EXISTS {AGENT}")
    print("drop agent", cur.sfqid)
    for p in ("WITNESS_SQL(VARCHAR)", "WITNESS_PY(VARCHAR)"):
        cur.execute(f"DROP PROCEDURE IF EXISTS LINKML_METRICS.RAW.{p}")
        print("drop", p, cur.sfqid)
print(cur.execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone())
