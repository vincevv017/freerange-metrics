"""Session 8: the agent specs of D and D' (charter version 5), written to d/agent_d.yaml and d/agent_dp.yaml.

    python snowflake/phase4_others/d/build_specs.py

Orchestration instructions: docs/DEFINITION.md sections 1, 2, 3, 7 and 8 as written there (verbatim, extracted, so
nothing is retyped); response: the common instruction; the semantic view tool on LINKML_B2_SV with B2's generated tool
description less its claim on coverage, routed to the skill; the skill linkml-coverage on the agent's own stage; D: code_execution, D': code_toolset_all (budget
160,000 tokens, charter). Both specs carry the same instructions and the same skill.
"""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from definition_text import extract  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SECTIONS = (1, 2, 3, 7, 8)


def definition() -> str:
    return extract(SECTIONS)


# The B2 tool description without its claim on coverage (which would compete with the skill), plus the routing to it.
SV_USE = {
    "code_execution": ("Use it for stock, closing stock and demand forecast questions, and to fetch the stock at the "
                       "analysis month and the monthly forecast that the linkml-coverage skill needs; coverage itself "
                       "is computed by the linkml-coverage skill, never here."),
    "code_toolset_all": ("Use it for stock, closing stock and demand forecast questions; coverage is computed by the "
                         "linkml-coverage skill, never here."),
}


def sv_description(b2_desc: str, code_tool: str) -> str:
    d = b2_desc.replace("; stock coverage in months (coverage_months_qty_eq, coverage_months_value) for one analysis "
                        "month", "")
    d = d.replace("Use it for every question on stock, closing stock, forecast or coverage.", SV_USE[code_tool])
    assert "coverage_months" not in d and SV_USE[code_tool] in d
    return d


def spec(code_tool: str, stage: str, tokens: int) -> dict:
    b2 = yaml.safe_load((ROOT / "generated" / "agent_b2.yaml").read_text())
    sv_tool = {"tool_spec": {**b2["tools"][0]["tool_spec"],
                             "description": sv_description(b2["tools"][0]["tool_spec"]["description"], code_tool)}}
    res = {sv_tool["tool_spec"]["name"]: b2["tool_resources"][sv_tool["tool_spec"]["name"]],
           code_tool: {"permission_policy": {"type": "always_ask"}}}
    return {
        "models": {"orchestration": b2["models"]["orchestration"]},
        "orchestration": {"budget": {"seconds": 120, "tokens": tokens}, "tool_not_accessible": "reject"},
        "instructions": {"orchestration": definition(), "response": b2["instructions"]["response"]},
        "skills": [{"name": "linkml-coverage",
                    "source": {"type": "STAGE", "path": f"@LINKML_METRICS.RAW.{stage}/skills/linkml-coverage"}}],
        "tools": [sv_tool, {"tool_spec": {"type": code_tool, "name": code_tool}}],
        "tool_resources": res,
    }


HEAD = ("# Configuration {c} (session 8): permanent agent LINKML_METRICS.RAW.{a}, created as LINKML_METRICS_ROLE and\n"
        "# called as LINKML_SVC. Written by snowflake/phase4_others/d/build_specs.py (charter version 5): instructions\n"
        "# DEFINITION.md sections 1, 2, 3, 7 and 8 verbatim less Provenance lines, skill linkml-coverage on stage {s}, the B2 semantic view tool.\n")
for name, c, a, tool, stage, tokens in (("agent_d.yaml", "D", "LINKML_D", "code_execution", "SKILLS_D", 40000),
                                         ("agent_dp.yaml", "D'", "LINKML_DP", "code_toolset_all", "SKILLS_DP", 160000)):
    (HERE / name).write_text(HEAD.format(c=c, a=a, s=stage)
                             + yaml.safe_dump(spec(tool, stage, tokens), sort_keys=False, allow_unicode=True, width=118))
    print("wrote", HERE / name)
