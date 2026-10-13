"""Size of the procedure's answer for reference questions (session 8a, steps 0 and 2): no agent call.

    python snowflake/phase4_agent_c/answer_size.py [T1 T7_R1 ...]

Calls LINKML_METRICS.RAW.STOCK_COVERAGE directly with the tool parameters of generated/reference_questions.yaml, as
perso, USE SECONDARY ROLES NONE, LINKML_METRICS_ROLE. Prints, per question: the bytes of the answer as the connector
returns it (the VARIANT's JSON text), the bytes of the same JSON compacted, an approximate token count (compact bytes
/ 4, a rule of thumb, not a tokenizer), and the compact bytes of each top-level key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import snowflake.connector
import yaml

ROOT = Path(__file__).resolve().parents[2]
PROC = "LINKML_METRICS.RAW.STOCK_COVERAGE"


def main() -> None:
    ids = sys.argv[1:] or ["T1", "T7_R1"]
    qs = {q["id"]: q for q in yaml.safe_load((ROOT / "generated" / "reference_questions.yaml").read_text())["questions"]}
    con = snowflake.connector.connect(connection_name="perso")
    cur = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH"):
        cur.execute(s)
    for qid in ids:
        p = qs[qid]["tool_parameters"]
        cur.execute(f"CALL {PROC}(%s, %s, %s, %s)",
                    (json.dumps(p["as_of_months"]), p["unit_variant"], json.dumps(p["grain"]), json.dumps(p["filters"])))
        raw = cur.fetchone()[0]
        ans = json.loads(raw)
        compact = json.dumps(ans, separators=(",", ":"), ensure_ascii=False)
        print(f"{qid}: status {ans['status']}, as returned {len(raw.encode())} B, compact {len(compact.encode())} B, "
              f"about {len(compact.encode()) // 4} tokens (bytes / 4)")
        for k, v in ans.items():
            print(f"    {k}: {len(json.dumps(v, separators=(',', ':'), ensure_ascii=False).encode())} B")
        if ans["status"] == "refused":
            print(f"    reason: {ans['refusal']['reason']}")
    con.close()


if __name__ == "__main__":
    main()
