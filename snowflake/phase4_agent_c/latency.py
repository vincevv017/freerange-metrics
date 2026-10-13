"""Agent C latency per turn (session 7, step 5): trace spans and query history, no LLM call.

    python snowflake/phase4_agent_c/latency.py --log-dir <the ask_questions.py log dir>   (raw output into results.md)
    python snowflake/phase4_agent_c/latency.py --log-dir <dir> --budget s8a              (session 8a: agent C, witness)

From each trace (GET_AI_OBSERVABILITY_EVENTS, saved by run_call.py): server time (AgentV2RequestResponseInfo), the
time before planning, planning, the tool span, response generation and the suggested-queries span, in seconds. From
INFORMATION_SCHEMA.QUERY_HISTORY, read as LINKML_SVC (its own queries): the CALL named by the SqlExecution span's
query id (elapsed, compilation, queued) and its child queries (same session, inside the CALL's window). Client
seconds come from run_call.py. Credits are not read. The last column (session 8a) is the end of the tool span minus the
end of the CALL, in seconds (server clocks: span TIMESTAMP against query history END_TIME).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import snowflake.connector

SPAN_PREFIX = {"plan": "ReasoningAgentStepPlanning", "resp": "ReasoningAgentStepResponseGeneration",
               "tool": "ToolCall-", "sugg": "LLM Suggested Queries", "req": "AgentV2RequestResponseInfo"}


def ts(x) -> dt.datetime | None:
    return None if x in (None, "None") else dt.datetime.fromisoformat(str(x))


def spans(trace: list[dict]) -> dict:
    out: dict = {"plan": [], "resp": [], "tool": [], "sugg": [], "req": [], "query_ids": []}
    for r in trace:
        rec = json.loads(r["RECORD"]) if isinstance(r["RECORD"], str) else (r["RECORD"] or {})
        attrs = json.loads(r["RECORD_ATTRIBUTES"]) if isinstance(r["RECORD_ATTRIBUTES"], str) else (r["RECORD_ATTRIBUTES"] or {})
        name, start, end = rec.get("name") or "", ts(r.get("START_TIMESTAMP")), ts(r.get("TIMESTAMP"))
        if name == "SqlExecution":
            out["query_ids"].append(attrs.get("snow.ai.observability.agent.tool.sql_execution.query_id"))
        for k, p in SPAN_PREFIX.items():
            if name.startswith(p) and start and end:
                out[k].append((start, end))
    return out


def secs(pairs) -> float:
    return round(sum((e - s).total_seconds() for s, e in pairs), 2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-dir", type=Path, required=True)
    ap.add_argument("--connection", default="linkml_svc")
    ap.add_argument("--budget", default="c")
    a = ap.parse_args()
    calls = json.loads((a.log_dir / "calls.json").read_text())[a.budget]
    cur = snowflake.connector.connect(connection_name=a.connection).cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    first = min(dt.datetime.fromisoformat(c["started_utc"]) for c in calls) - dt.timedelta(minutes=2)
    cur.execute("SELECT query_id, session_id, start_time, end_time, total_elapsed_time, compilation_time, "
                "execution_time, queued_provisioning_time + queued_overload_time + queued_repair_time AS queued, "
                "LEFT(query_text, 60) FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_USER(USER_NAME => 'LINKML_SVC', "
                "END_TIME_RANGE_START => %s::TIMESTAMP_LTZ, RESULT_LIMIT => 10000)) ORDER BY start_time",
                (first.isoformat(),))
    qh = [dict(zip([d[0].lower() for d in cur.description], r)) for r in cur.fetchall()]
    by_id = {q["query_id"]: q for q in qh}
    print("| # | Id | Client s | Server s | Before planning s | Planning s | Tool span s | Response s | Suggested queries s "
          "| CALL elapsed ms (compile / queued) | Children: n, elapsed ms (compile) | Request id | Span end - CALL end s |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in calls:
        tag = "".join(ch if ch.isalnum() else "_" for ch in c["label"].lower()).strip("_")
        f = a.log_dir / f"trace_{tag}.json"
        trace = json.loads(f.read_text()) if f.exists() else []
        s = spans(trace)
        req = s["req"][0] if s["req"] else None
        before = round((min(p[0] for p in s["plan"]) - req[0]).total_seconds(), 2) if req and s["plan"] else None
        call_txt, child_txt, gap = "no CALL", "n/a", "n/a"
        for qid in s["query_ids"]:
            q = by_id.get(qid)
            if not q:
                call_txt = f"{qid} not in history"
                continue
            call_txt = f"{q['total_elapsed_time']} ({q['compilation_time']} / {q['queued']})"
            if s["tool"]:
                end = q["end_time"].astimezone(dt.timezone.utc).replace(tzinfo=None)
                span_end = max(e for _, e in s["tool"])
                span_end = span_end.replace(tzinfo=None) if span_end.tzinfo is None else \
                    span_end.astimezone(dt.timezone.utc).replace(tzinfo=None)
                gap = round((span_end - end).total_seconds(), 2)
            kids = [k for k in qh if k["session_id"] == q["session_id"] and k["query_id"] != qid
                    and q["start_time"] <= k["start_time"] <= q["end_time"]]
            child_txt = (f"{len(kids)}: " + ", ".join(f"{k['total_elapsed_time']} ({k['compilation_time']})"
                                                       for k in kids)) if kids else "0"
        print(f"| {c['n']} | {c['label']} | {c['seconds_total']} | {secs(s['req'])} | {before} | {secs(s['plan'])} "
              f"| {secs(s['tool'])} | {secs(s['resp'])} | {secs(s['sugg'])} | {call_txt} | {child_txt} "
              f"| `{c['request_id']}` | {gap} |")


if __name__ == "__main__":
    main()
