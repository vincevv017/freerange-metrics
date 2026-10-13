"""Session 8: per-call records of a configuration's turns, from run_call.py logs and traces, plus query history.

    python snowflake/phase4_others/records.py <label> [<label> ...]

Per call: request id, start (UTC), client seconds, first byte, version served (trace attribute
snow.ai.observability.object.version.name), orchestration input tokens (REST usage), and the latency split from the
spans: before planning, planning steps, semantic context reads, SQL tool spans, skill and code spans, response,
suggested queries, server total. Then every query of LINKML_SVC inside the turn's window
(INFORMATION_SCHEMA.QUERY_HISTORY_BY_USER, read as LINKML_SVC): elapsed, queued provisioning and queued overload.
"Computed by" (an observation, not graded), coverage questions only: tool when a tool returned the coverage (the
procedure, the skill's script, or a successful SQL statement that selects the coverage metric or computes the cascade),
model when the tools returned only the inputs and the model did the arithmetic; n/a otherwise.
"Tables read by the script" (an observation, D and D'): the LINKML_METRICS.RAW objects named by the queries passed to
the skill script, each marked base (a table of the contract) or generated (a view the compiler writes from it).
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import re

import snowflake.connector
import yaml

RUN = __import__("os").environ.get("LINKML_RUN", "s8")       # session 8b: LINKML_RUN=s8b (run folder and budget)
LOG = Path.home() / "work" / "assets" / "linkml-metrics-runs" / RUN
GROUPS = {"plan": ("ReasoningAgentStepPlanning",), "context": ("SemanticContextTool",),
          "sql": ("SystemExecuteSQLTool",), "skill": ("ServerSkillTool", "CodeExecutionTool", "CodingAgent"),
          "tool": ("ToolCall-",), "resp": ("ReasoningAgentStepResponseGeneration",), "sugg": ("LLM Suggested Queries",),
          "req": ("AgentV2RequestResponseInfo",)}


QUESTIONS = {q["id"].lower(): q for q in yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "generated" / "reference_questions.yaml").read_text())["questions"]}


def computed_by(label: str, calls: list) -> str:
    qid = label.split("_", 1)[1]
    if QUESTIONS.get(qid, {}).get("metric") != "stock_coverage":
        return "n/a"
    uses = [u for c in calls for u in c.get("tool_uses", [])]
    res = [r for c in calls for r in c.get("tool_results", [])]
    if not uses:
        return "n/a (no tool)"
    for u, r in zip(uses, res):
        ok = r.get("status") == "success"
        text = json.dumps(u.get("input", {}))
        if u.get("name") == "stock_coverage" and ok:
            return "tool"
        if "coverage.py" in text and ok:
            return "tool (skill script)"
        if "sql" in (u.get("type") or "") and ok and re.search(r"coverage_months|CASE\b.{0,400}<=", text, re.I | re.S):
            return "tool"
    return "model"


BASE_TABLES = {t["id"] for t in yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "contract" / "stock_coverage.yaml").read_text())["tables"]}


def tables_read(calls: list) -> str:
    names = set()
    for c in calls:
        for u in c.get("tool_uses", []):
            text = json.dumps(u.get("input", {}))
            if "coverage.py" in text:
                names |= {n.upper() for n in re.findall(r"LINKML_METRICS\.RAW\.(\w+)", text, re.I)}
    return ", ".join(f"{n} ({'base' if n in BASE_TABLES else 'generated'})" for n in sorted(names)) or "n/a"


def ts(x):
    return None if x in (None, "None") else dt.datetime.fromisoformat(str(x)).replace(tzinfo=None)


def obj(x):
    return x if isinstance(x, dict) else (json.loads(x) if x else {})


def main() -> None:
    cur = snowflake.connector.connect(connection_name="linkml_svc").cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    rows = []
    for label in sys.argv[1:]:
        tag = label.lower()
        s = json.loads((LOG / f"summary_{tag}.json").read_text())
        trace = json.loads((LOG / f"trace_{tag}.json").read_text())
        spans = {k: [] for k in GROUPS}
        versions, qids = set(), []
        for r in trace:
            rec, a = obj(r["RECORD"]), obj(r["RECORD_ATTRIBUTES"])
            name = rec.get("name") or ""
            v = a.get("snow.ai.observability.object.version.name")
            if v:
                versions.add(v)
            q = a.get("snow.ai.observability.agent.tool.sql_execution.query_id")
            if q and name.startswith("SqlExecution"):
                qids.append(q)
            for k, prefixes in GROUPS.items():
                if name.startswith(prefixes) and r.get("START_TIMESTAMP") and r.get("TIMESTAMP"):
                    spans[k].append((ts(r["START_TIMESTAMP"]), ts(r["TIMESTAMP"])))
        sec = {k: round(sum((e - b).total_seconds() for b, e in v), 2) for k, v in spans.items()}
        req = spans["req"][0] if spans["req"] else None
        before = round((min(b for b, _ in spans["plan"]) - req[0]).total_seconds(), 2) if req and spans["plan"] else None
        for c in s["calls"]:
            usage = c.get("usage") or {}
            orch = next((x for x in usage.get("tokens_consumed", []) if x.get("model_role") == "orchestration"), {})
            it = orch.get("input_tokens", {})
            tokens = (f"{it.get('total', 0):,} ({it.get('cache_write', 0):,} / {it.get('cache_read', 0):,}), "
                      f"out {orch.get('output_tokens', {}).get('total', 0):,}") if orch else "n/a"
            rows.append((label, c, versions, tokens, before, sec, qids, len(spans["plan"]), computed_by(label, s["calls"]), tables_read(s["calls"])))
    first = min(dt.datetime.fromisoformat(r[1]["started_utc"]) for r in rows) - dt.timedelta(minutes=2)
    cur.execute("SELECT query_id, start_time, end_time, total_elapsed_time, queued_provisioning_time, "
                "queued_overload_time, LEFT(query_text, 50) FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_USER("
                "USER_NAME => 'LINKML_SVC', END_TIME_RANGE_START => %s::TIMESTAMP_LTZ, RESULT_LIMIT => 10000)) "
                "ORDER BY start_time", (first.isoformat(),))
    qh = cur.fetchall()
    print("| Label | Request id | Started (UTC) | Client s | First byte s | Version served | Orchestration input (cache write / read), output | Server s | "
          "Before planning s | Planning s (steps) | Context s | SQL tool s | Skill/code s | Response s | "
          "Suggested s | Computed by | Tables read by the script | Queries of the turn: elapsed ms (queued provisioning / overload ms) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for label, c, versions, tokens, before, sec, qids, nplan, cby, tread in rows:
        start = dt.datetime.fromisoformat(c["started_utc"])
        end = start + dt.timedelta(seconds=c["seconds_total"])
        turn_q = [q for q in qh if start <= q[1].astimezone(dt.timezone.utc) <= end]
        qtxt = "; ".join(f"{q[3]} ({q[4]} / {q[5]}){' agent SQL' if q[0] in qids else ''}" for q in turn_q
                         if not q[6].startswith(("LIST snow://", "USE SECONDARY"))) or "none"
        print(f"| {label} | `{c['request_id']}` | {c['started_utc'][11:23]} | {c['seconds_total']} | "
              f"{c.get('seconds_to_first_byte')} | {', '.join(sorted(versions))} | {tokens} | {sec['req']} | {before} | "
              f"{sec['plan']} ({nplan}) | {sec['context']} | {sec['sql']} | {sec['skill']} | {sec['resp']} | {sec['sugg']} "
              f"| {cby} | {tread} | {qtxt} |")


if __name__ == "__main__":
    main()
