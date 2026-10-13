"""Session 8: the agent spec of A (charter version 5), written to a/agent_a.yaml.

    python snowflake/phase4_others/a/build_spec.py

Orchestration instructions: docs/DEFINITION.md sections 1, 7 and 8 as written there (verbatim, extracted, without
the Provenance lines); response:
the common instruction; one semantic view tool on the untouched Autopilot view AP_LINKLM, with a description written
for A (factual, like B1's).
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from definition_text import extract  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
SECTIONS = (1, 7, 8)
b2 = yaml.safe_load((ROOT / "generated" / "agent_b2.yaml").read_text())
spec = {
    "models": {"orchestration": b2["models"]["orchestration"]},
    "orchestration": {"budget": {"seconds": 120, "tokens": 40000}, "tool_not_accessible": "reject"},
    "instructions": {"orchestration": extract(SECTIONS), "response": b2["instructions"]["response"]},
    "tools": [{"tool_spec": {"type": "cortex_analyst_text_to_sql", "name": "a_semantic_view", "description": (
        "Semantic view LINKML_METRICS.RAW.AP_LINKLM of the grocery retailer, built with Semantic View Autopilot on the "
        "seven RAW tables: monthly stock snapshots per lot and warehouse, monthly demand forecast per item and country, "
        "items, countries, lots, warehouses and the calendar. Stock snapshots run monthly from July 2023 to June 2026. "
        "Use it for every question on stock, closing stock, forecast or coverage.")}}],
    "tool_resources": {"a_semantic_view": {"semantic_view": "LINKML_METRICS.RAW.AP_LINKLM",
                                           "execution_environment": b2["tool_resources"]["b2_semantic_view"]["execution_environment"]}},
}
out = Path(__file__).resolve().parent / "agent_a.yaml"
out.write_text("# Configuration A (session 8): permanent agent LINKML_METRICS.RAW.LINKML_A, created as LINKML_METRICS_ROLE and\n"
               "# called as LINKML_SVC. Written by snowflake/phase4_others/a/build_spec.py (charter version 5).\n"
               + yaml.safe_dump(spec, sort_keys=False, allow_unicode=True, width=118))
print("wrote", out, len(spec["instructions"]["orchestration"]), "characters of instructions")
