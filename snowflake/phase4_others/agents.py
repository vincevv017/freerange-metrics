"""Session 8: create, publish or drop a configuration's permanent agent from its reviewed spec file.

    python snowflake/phase4_others/agents.py create   <AGENT> <spec.yaml>   # CREATE AGENT, then SHOW VERSIONS
    python snowflake/phase4_others/agents.py publish  <AGENT> <spec.yaml>   # the five-beat cycle on an existing agent
    python snowflake/phase4_others/agents.py versions <AGENT> <spec.yaml>   # each version's spec against the file
    python snowflake/phase4_others/agents.py warm                           # before each agent call
    python snowflake/phase4_others/agents.py drop     <AGENT>

Run as perso, USE SECONDARY ROLES NONE, LINKML_METRICS_ROLE (the agents' owner, the role LINKML_SVC calls them with).
The spec is the file without its comment header; beat 0 parses it and asserts the instructions are single strings and
the round trip is equal. The default version is read from SHOW VERSIONS, never computed. The fifth beat (one smoke
question) is the first call of the configuration's smoke run, through snowflake/probe_b/mount/run_call.py.
"""

import json
import sys
from pathlib import Path

import snowflake.connector
import yaml

con = snowflake.connector.connect(connection_name="perso")
cur = con.cursor()
cur.execute("USE SECONDARY ROLES NONE")
cur.execute("USE ROLE LINKML_METRICS_ROLE")


def spec(path: str) -> tuple[dict, str]:
    s = yaml.safe_load(Path(path).read_text())
    for k in ("orchestration", "response"):
        assert isinstance(s["instructions"][k], str), k
    text = yaml.safe_dump(s, sort_keys=False, allow_unicode=True, width=1000)
    assert yaml.safe_load(text) == s and "$$" not in text
    return s, text


def versions(fqn: str, want: dict) -> None:
    rows = cur.execute(f"SHOW VERSIONS IN AGENT {fqn}").fetchall()
    cols = [d[0] for d in cur.description]
    for r in map(lambda x: dict(zip(cols, x)), rows):
        print(r["name"] or "LIVE", "default" if r["is_default"] == "true" else "", r.get("aliases") or "",
              "spec equal to file:", json.loads(r["agent_spec"]) == want)
    d = dict(zip([c[0] for c in cur.execute(f"DESCRIBE AGENT {fqn}").description], cur.fetchone()))
    print("DESCRIBE (default version) equal to file:", json.loads(d["agent_spec"]) == want)


cmd = sys.argv[1]
if cmd == "warm":
    cur.execute("USE WAREHOUSE LINKML_METRICS_WH")
    cur.execute("SELECT SUM(SEQ4()) FROM TABLE(GENERATOR(ROWCOUNT => 1000))")
    q = cur.sfqid
    cur.execute("SHOW WAREHOUSES LIKE 'LINKML_METRICS_WH'")
    state = dict(zip([d[0] for d in cur.description], cur.fetchone()))["state"]
    print("warm", q, state)
    assert state == "STARTED", state
    sys.exit(0)
fqn = f"LINKML_METRICS.RAW.{sys.argv[2]}"
if cmd == "create":
    s, text = spec(sys.argv[3])
    session = __import__("os").environ.get("LINKML_SESSION", "8")      # session 13: LINKML_SESSION=13 for C-raw
    cur.execute(f"CREATE AGENT {fqn} COMMENT = 'Session {session} configuration, spec {Path(sys.argv[3]).name}' "
                f"FROM SPECIFICATION $${text}$$")
    print("create agent", cur.sfqid)
    versions(fqn, s)
    print(cur.execute(f"SHOW GRANTS ON AGENT {fqn}").fetchall())
elif cmd == "publish":
    s, text = spec(sys.argv[3])
    cur.execute(f"ALTER AGENT {fqn} MODIFY LIVE VERSION SET SPECIFICATION = $${text}$$")
    print("modify live", cur.sfqid)
    cur.execute(f"ALTER AGENT {fqn} COMMIT")
    print("commit", cur.sfqid)
    cur.execute(f"ALTER AGENT {fqn} ADD LIVE VERSION FROM LAST")
    print("add live from last", cur.sfqid)
    rows = cur.execute(f"SHOW VERSIONS IN AGENT {fqn}").fetchall()
    cols = [d[0] for d in cur.description]
    last = max((dict(zip(cols, r))["name"] for r in rows if dict(zip(cols, r))["name"]),
               key=lambda n: int(n.split("$")[1]))
    cur.execute(f"ALTER AGENT {fqn} SET DEFAULT_VERSION = '{last}'")
    print("default", last, cur.sfqid)
    versions(fqn, s)
elif cmd == "versions":
    versions(fqn, spec(sys.argv[3])[0])
elif cmd == "drop":
    cur.execute(f"DROP AGENT IF EXISTS {fqn}")
    print("drop agent", cur.sfqid)
print(cur.execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone())
