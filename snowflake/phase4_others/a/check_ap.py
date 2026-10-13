"""Session 8, A: AP_LINKLM must equal the Autopilot export, whitespace aside (never edited, enriched or redeployed)."""
import re
from pathlib import Path

import snowflake.connector
import yaml

EXPORT = Path(__file__).resolve().parents[1] / "AP_LINKLM_autopilot.yaml"
cur = snowflake.connector.connect(connection_name="perso").cursor()
for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE"):
    cur.execute(s)
live = cur.execute("SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('LINKML_METRICS.RAW.AP_LINKLM')").fetchone()[0]
qid = cur.sfqid
f = EXPORT.read_text()
norm = lambda s: re.sub(r"\s+", "", s)
print("query id", qid)
print("equal, whitespace aside:", norm(live) == norm(f), "| parsed equal:", yaml.safe_load(live) == yaml.safe_load(f))
print(cur.execute("SHOW SEMANTIC VIEWS LIKE 'AP_LINKLM' IN SCHEMA LINKML_METRICS.RAW").fetchall()[0][:6])
