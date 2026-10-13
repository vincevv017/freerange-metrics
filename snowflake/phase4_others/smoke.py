"""Session 8: smoke run of one configuration, then its grades.

    python snowflake/phase4_others/smoke.py run   <CONFIG> <AGENT> <QID> [<QID> ...] [--policy deny-all|dp]
    python snowflake/phase4_others/smoke.py grade <CONFIG> <QID> [<QID> ...]

run: for each question of generated/reference_questions.yaml, keep the warehouse running (agents.py warm: a GENERATOR
sum, state STARTED), then one call through snowflake/probe_b/mount/run_call.py as LINKML_SVC, budget s8, label
<config>_<qid>, logs in ~/work/assets/linkml-metrics-runs/s8/ (persistent, outside the repository).
grade: builds each turn from the run_call summary and trace (eval/grade.py turns_from_log) and grades it; the grades
are written to the same folder and printed with their justification.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = __import__("os").environ.get("LINKML_RUN", "s8")       # session 8b: LINKML_RUN=s8b (run folder and budget)
LOG = Path.home() / "work" / "assets" / "linkml-metrics-runs" / RUN
QUESTIONS = {q["id"]: q for q in yaml.safe_load((ROOT / "generated" / "reference_questions.yaml").read_text())["questions"]}
SV_TOOLS = {"b2_semantic_view", "b1_semantic_view", "a_semantic_view"}
ITEM_OBJECTS = ("DIM_ITEM", "B2_ITEM")
PY = sys.executable


STAGE, REP = "", 1      # session 8c-0, step 8: --stage and --rep


def label(config: str, qid: str) -> str:
    """<CONFIG>_<QUESTION>_<stage>_r<n> when a stage is given (session 8c-0, step 8: run_call.py refuses any other label
    for budget s8c0 and the campaign budgets, and any label that already has a log); the older lower-case form
    otherwise."""
    if STAGE:
        return f"{config}_{qid}_{STAGE}_r{REP}"
    return f"{config}_{qid}".lower()


def run(config: str, agent: str, qids: list[str], policy: str, client_sql: bool = False, suffix: str = "") -> None:
    for qid in qids:
        subprocess.run([PY, str(ROOT / "snowflake/phase4_others/agents.py"), "warm"], check=True)
        r = subprocess.run([PY, str(ROOT / "snowflake/probe_b/mount/run_call.py"), "--agent", agent,
                            "--question", QUESTIONS[qid]["question"], "--label", label(config, qid) + suffix,
                            "--budget", RUN, "--policy", policy, "--log-dir", str(LOG)]
                           + (["--client-sql"] if client_sql else []), capture_output=True, text=True)
        tag = re.sub(r"[^a-z0-9]+", "_", (label(config, qid) + suffix).lower()).strip("_")
        if not (LOG / f"summary_{tag}.json").exists():
            print(qid, "no log:", r.stdout[-300:], r.stderr[-300:])
            continue
        s = json.loads((LOG / f"summary_{tag}.json").read_text())
        for c in s["calls"]:
            print(qid, c["n"], c["status"], c["started_utc"], c["seconds_total"], c["request_id"],
                  [u.get("name") for u in c.get("tool_uses", [])], flush=True)
        if "stopped" in s:
            print(qid, "STOPPED:", s["stopped"])
        if r.returncode:
            print(qid, "run_call exit", r.returncode, r.stderr[-500:])


def grade(config: str, qids: list[str], suffix: str = "") -> None:
    spec = importlib.util.spec_from_file_location("grade", ROOT / "eval" / "grade.py")
    g = importlib.util.module_from_spec(spec)
    sys.modules["grade"] = g
    spec.loader.exec_module(g)
    turns = g.turns_from_log(LOG, {label(config, q) + suffix: (config, q) for q in qids})
    out = []
    for t in turns:
        res = g.grade_turn(t, SV_TOOLS, ITEM_OBJECTS)
        out.append({**res, "answer": t["answer"], "tool_uses": t["tool_uses"], "sql": t["sql"]})
        print(f"\n=== {config} {t['question_id']}: {res['verdict'].upper()}")
        print("answer:", t["answer"])
        print("tools:", [(u.get("type"), u.get("name")) for u in t["tool_uses"]])
        for s in t["sql"]:
            print("sql:", s)
        for k, c in res["criteria"].items():
            print(f"  {k}: {c['result']} ({c['why']})")
        print("  warnings relayed:", res["warnings_relayed"])
        print("  governance ROWS_COMMENTED:", res["governance"]["ROWS_COMMENTED"])     # session 8c-0, step 7b
        print("  governance FRESHNESS_STATED:", res["governance"]["FRESHNESS_STATED"])   # session 8c-0, step 8
    (LOG / f"grades_{config.lower()}{suffix}.json").write_text(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    a = sys.argv[1:]
    policy, csql, suffix = "deny-all", "--client-sql" in a, ""
    a = [x for x in a if x != "--client-sql"]
    if "--suffix" in a:
        i = a.index("--suffix")
        suffix = a[i + 1]
        a = a[:i] + a[i + 2:]
    if "--stage" in a:
        i = a.index("--stage")
        STAGE = a[i + 1]
        a = a[:i] + a[i + 2:]
    if "--rep" in a:
        i = a.index("--rep")
        REP = int(a[i + 1])
        a = a[:i] + a[i + 2:]
    if "--policy" in a:
        i = a.index("--policy")
        policy = a[i + 1]
        a = a[:i] + a[i + 2:]
    if a[0] == "run":
        run(a[1], a[2], a[3:], policy, csql, suffix)
    else:
        grade(a[1], a[2:], suffix)
