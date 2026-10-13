"""Probe D setup and teardown, run as perso with the project role and no secondary role.

    python snowflake/probe_d/setup.py create     # stage, skill files, permanent agent
    python snowflake/probe_d/setup.py drop
"""

import sys
from pathlib import Path

import snowflake.connector
import yaml

HERE = Path(__file__).resolve().parent
STAGE, AGENT = "LINKML_METRICS.RAW.SKILLS_D_PROBE", "LINKML_METRICS.RAW.LINKML_D_PROBE"

con = snowflake.connector.connect(connection_name="perso")
cur = con.cursor()
cur.execute("USE SECONDARY ROLES NONE")
cur.execute("USE ROLE LINKML_METRICS_ROLE")
if sys.argv[1] == "create":
    cur.execute(f"CREATE STAGE {STAGE}")
    for f in ("SKILL.md", "probe.py"):
        cur.execute(f"PUT file://{HERE / 'skills/linkml-probe-py' / f} @{STAGE}/skills/linkml-probe-py "
                    "AUTO_COMPRESS = FALSE OVERWRITE = TRUE")
    spec = yaml.safe_dump(yaml.safe_load((HERE / "spec_d_probe.yaml").read_text()), sort_keys=False)
    cur.execute(f"CREATE AGENT {AGENT} FROM SPECIFICATION $${spec}$$")
    print(cur.execute(f"LIST @{STAGE}").fetchall())
    print(cur.execute(f"SHOW AGENTS LIKE 'LINKML_D_PROBE' IN SCHEMA LINKML_METRICS.RAW").fetchall()[0][:6])
elif sys.argv[1] == "drop":
    cur.execute(f"DROP AGENT IF EXISTS {AGENT}")
    cur.execute(f"DROP STAGE IF EXISTS {STAGE}")
    print("dropped")
print(cur.execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone())
