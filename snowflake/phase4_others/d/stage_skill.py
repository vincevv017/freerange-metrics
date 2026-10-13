"""Session 8: put the linkml-coverage skill on a configuration's own stage and prove name parity with the repository.

    python snowflake/phase4_others/d/stage_skill.py SKILLS_DP     # D'
    python snowflake/phase4_others/d/stage_skill.py SKILLS_D      # D

Perso, USE SECONDARY ROLES NONE, LINKML_METRICS_ROLE. CREATE STAGE IF NOT EXISTS (internal, as the probes' known-good
stage), PUT of the two files with AUTO_COMPRESS = FALSE (one folder level, files listed explicitly), then LIST and a
comparison of names (sizes may differ after transfer). One stage per agent: code_toolset_all mounts the whole stage.
"""
import sys
from pathlib import Path

import snowflake.connector

SKILL = Path(__file__).resolve().parents[1] / "skill" / "linkml-coverage"
FILES = ["SKILL.md", "coverage.py"]
stage = f"LINKML_METRICS.RAW.{sys.argv[1]}"
cur = snowflake.connector.connect(connection_name="perso").cursor()
for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH"):
    cur.execute(s)
cur.execute(f"CREATE STAGE IF NOT EXISTS {stage} COMMENT = 'Session 8: linkml-coverage skill, one agent only'")
print("stage", cur.fetchone(), cur.sfqid)
for f in FILES:
    cur.execute(f"PUT 'file://{SKILL / f}' @{stage}/skills/linkml-coverage/ AUTO_COMPRESS = FALSE OVERWRITE = TRUE")
    print("put", f, cur.fetchone()[:7], cur.sfqid)
rows = cur.execute(f"LIST @{stage}").fetchall()
staged = sorted(r[0].split("/skills/linkml-coverage/")[-1] for r in rows)
print("staged:", [(r[0].split("/", 1)[-1], r[1]) for r in rows])
print("parity (names):", staged == sorted(FILES), "repo:", sorted(FILES))
# Read the deposited files back and compare their bytes with the repository (sizes and md5 on the stage are not).
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    cur.execute(f"GET @{stage}/skills/linkml-coverage/ 'file://{tmp}/'")
    for f in FILES:
        got = (Path(tmp) / f).read_bytes()
        print("read back", f, len(got), "B, identical to the repository:", got == (SKILL / f).read_bytes())
print(cur.execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone())
