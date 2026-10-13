"""
Session 3 agent probes: one REST call to a permanent agent, as LINKML_SVC with a key-pair JWT.

    python snowflake/probe_b/mount/run_call.py --agent LINKML_SKILL_PROBE --question "Run the linkml echo." \
        --label "mount 1: no code tool" --budget mount --log-dir <scratch dir>

Default caller: LINKML_SVC. --connection perso --role-headers reproduces the session 2 caller (<ADMIN_USER>, no
default role or warehouse, both sent as headers). The agent object is created beforehand (CREATE AGENT from a reviewed spec); this script only calls it, answers
approval requests with a fixed policy, and reads the trace. No X-Snowflake-Role / X-Snowflake-Warehouse header is
sent: LINKML_SVC has a default role and warehouse, and the probe must run on them.

Call caps are per budget and persisted in <log-dir>/calls.json: mount = 6, c0 = 10, d = 3, c = 15,
s8a = 8 (session 8a: agent C and the latency witness together), s8 = 38 (session 8: 29 calls, plus 5 for the D'
approval resumes, plus 4 for D''s client-side SQL resumes), s8b = 14 (session 8b: smoke of C, 10, and a reserve of 4), s8c0 = 11 (session 8c-0: step 6, 7 calls of C and a reserve of 2; raised to 11 for step 7e, owner). Every REST call counts,
failed or denied, approval resumes included. The script refuses to start a call past the cap.

Approval policy:
- deny-all (default): every permission request is denied.
- c0, c (agent C, session 7): allow the custom tool stock_coverage only.
- w (latency witness, session 8a): allow the custom tool witness only.
- dp (configuration D', session 8): allow a bash command only when it is exactly a run of the linkml-coverage skill
  script: python3 <skill folder>/coverage.py (or coverage.py, after `cd <...linkml-coverage> &&`) with the script's
  own flags only (--as-of, --stock, --forecast, --stock-sql, --forecast-sql), no other command, operator or
  redirection. Anything else: Deny. Single-use option only; each resume is a counted call.
- probe: session 2 rules for the linkml-probe skill. bash: only `python3 probe.py; env | cut -d= -f1 | grep -i
  snowflake | sort`, exact, or preceded by `cd <skill folder> &&` / `;`, or with an absolute path to probe.py.
  SQL: only the step 2 statement, case and whitespace ignored. Anything else: Deny. Single-use options only.
- stop (probe D, session 4): no decision is taken. The call stops on the first permission request, writes it verbatim
  to <log-dir>/pending_<label>.json and saves the thread; the project owner decides. Resume with --thread <saved
  thread> --decisions <JSON list of {tool_use_id, decision}>, which sends the decisions instead of a new question.

--client-sql (session 8, D'): a tool use with client_side_execute true is executed by this client when it is a
snowflake_sql_execute holding exactly one SELECT or WITH statement (client_sql.py: linkml_svc connection, USE SECONDARY
ROLES NONE, row limit); anything else gets an error tool_result. The result goes back as a tool_result content item in
the next request, which is a counted call. Every statement, its status and query id go to <log-dir>/client_sql.jsonl.

Raw events and trace rows go to --log-dir (outside the repo: they carry the account host).
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import datetime as dt
import fcntl
import json
import re
import shlex
import sys
import time
from pathlib import Path

import requests
import snowflake.connector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_probe_b import conn_params, final_response, keypair_jwt, norm_sql, pending_permissions, strings  # noqa: E402
import client_sql  # noqa: E402

_g = importlib.util.spec_from_file_location("campaign_guards", Path(__file__).resolve().parents[3] / "eval" / "guards.py")
guards = importlib.util.module_from_spec(_g)
sys.modules["campaign_guards"] = guards
_g.loader.exec_module(guards)       # the rates of the runaway guard (session 9a)

DB, SCHEMA = "LINKML_METRICS", "RAW"
CAPS = {"mount": 6, "c0": 10, "d": 3, "c": 15, "s8a": 8, "s8": 38, "s8b": 14, "s8c0": 11,
        "campaign": None,   # session 8c: the campaign budget is per block, its cap given by --block-cap
        "manual": 20,       # session 8c (owner): the owner replays an exchange to cite, labels <CONFIG>_<QUESTION>_manual_r<n>
        "s13": 6}           # session 13, step 3: C-raw's smoke, 4 questions (beat 5 is the first)

STEP1 = "python3 probe.py; env | cut -d= -f1 | grep -i snowflake | sort"
STEP2 = "SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST"
_STEP1_CD = re.compile(r"^cd\s+(['\"]?)(\S*linkml-probe/?)\1\s*(&&|;)\s*" + re.escape(STEP1) + r"$")
_STEP1_ABS = re.compile(r"^python3\s+(['\"]?)/\S*/linkml-probe/probe\.py\1" + re.escape(STEP1[len("python3 probe.py"):]) + r"$")


DP_FLAGS = {"--as-of", "--stock", "--forecast", "--stock-sql", "--forecast-sql"}


def dp_allowed(cmd: str) -> bool:
    """policy dp: the linkml-coverage script, its own flags, nothing else."""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        return False
    if toks[:1] == ["cd"]:
        if len(toks) < 3 or not toks[1].rstrip("/").endswith("linkml-coverage") or toks[2] != "&&":
            return False
        toks = toks[3:]
    if any(re.fullmatch(r"[;&|<>()]+", x) for x in toks) or len(toks) < 4:
        return False
    if toks[0] not in ("python3", "python") or not (toks[1] == "coverage.py" or toks[1].endswith("/linkml-coverage/coverage.py")):
        return False
    rest = toks[2:]
    if len(rest) % 2 or rest[0::2].count("--as-of") != 1:
        return False
    return all(f in DP_FLAGS for f in rest[0::2]) and len(set(rest[0::2])) == len(rest[0::2])


def decide(tool: dict, policy: str) -> tuple[str, str]:
    label = f"{tool.get('type', '')} {tool.get('name', '')}".lower()
    texts = [t.strip() for t in strings(tool.get("input", {}))]
    if policy == "probe":
        if "bash" in label:
            for t in texts:
                if t == STEP1 or _STEP1_CD.match(t) or _STEP1_ABS.match(t):
                    return "Allow Once", "bash: linkml-probe step 1"
        if "sql" in label:
            for t in texts:
                if norm_sql(t) == norm_sql(STEP2):
                    return "Allow Once", "sql: linkml-probe step 2"
    if policy in ("c0", "c") and tool.get("name") == "stock_coverage":
        return "Allow Once", f"{policy}: the coverage tool"
    if policy == "w" and tool.get("name") == "witness":
        return "Allow Once", "w: the witness tool"
    if policy == "dp" and "bash" in label and texts and all(dp_allowed(x) for x in texts if x):
        return "Allow Once", "dp: the linkml-coverage script, its own flags only"
    return "Deny", f"policy {policy}: not an approved command"


@contextlib.contextmanager
def locked(log_dir: Path):
    """Session 8c (--streams): several run_call.py processes share one run folder; calls.json and the .jsonl logs are
    written under an exclusive lock."""
    with (log_dir / ".lock").open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def append_jsonl(path: Path, rec: dict) -> None:
    with locked(path.parent), path.open("a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


class Budget:
    """Calls per budget, persisted in <log-dir>/calls.json. Session 8c: the campaign budget counts per block (one
    configuration's calls of one stage); the block's cap is fixed at its first call and a different cap is refused."""

    def __init__(self, log_dir: Path, name: str, cap: int | None = None):
        self.path, self.name, self.log_dir = log_dir / "calls.json", name, log_dir
        with locked(log_dir):
            self.state = json.loads(self.path.read_text()) if self.path.exists() else {}
            self.state.setdefault(name, [])
            caps = self.state.setdefault("_caps", {}) if cap is not None else {}
            if cap is not None:
                if caps.setdefault(name, cap) != cap:
                    raise SystemExit(f"block {name} was started with cap {caps[name]}, not {cap}: refused")
                self.path.write_text(json.dumps(self.state, indent=2))
        self.cap = cap if cap is not None else CAPS[name]

    @property
    def used(self) -> int:
        return len(self.state[self.name])

    def spend(self, rec: dict) -> None:
        with locked(self.log_dir):
            state = json.loads(self.path.read_text()) if self.path.exists() else {}
            state.setdefault(self.name, []).append(rec)
            self.path.write_text(json.dumps(state, indent=2))
            self.state = state


def before_call(budget: "Budget", calls_in_turn: int, turn_cap: int | None) -> tuple[str, str] | None:
    """Session 8c guards checked before every REST call: the block's (or budget's) call cap, then the question's."""
    if budget.used >= budget.cap:
        return "block_cap", f"cap {budget.cap} reached for budget {budget.name}"
    if turn_cap and calls_in_turn >= turn_cap:
        return "turn_cap", f"turn cap {turn_cap} reached: the question used {turn_cap} REST calls"
    return None


def token_guard(call: dict, ceiling: int | None) -> tuple[str, str] | None:
    """Session 8c: a call whose orchestration input exceeds the configuration's ceiling (1.5 times its largest smoke
    call, eval/guards.py) aborts the turn and stops the block."""
    n = call_tokens(call)["input"]
    if ceiling and n > ceiling:
        return "token", f"token guard: {n} orchestration input tokens on one call, above {ceiling}"
    return None


def turn_cost_guard(calls: list[dict], cap_usd: float | None) -> tuple[str, str] | None:
    """Session 9a (owner): the runaway guard. After each REST call, the turn's summed tokens priced at the rates of
    eval/guards.py; above the cap the turn stops (exit code 4) and the campaign stops the block."""
    usd = guards.turn_usd(turn_tokens(calls))
    if cap_usd and usd > cap_usd:
        return "turn_cost", f"runaway guard: turn cost estimate {usd:.2f} USD, above {cap_usd:.2f} USD"
    return None


def post(host: str, path: str, headers: dict, body: dict) -> dict:
    t0 = time.monotonic()
    started = dt.datetime.now(dt.timezone.utc)
    r = requests.post(f"https://{host}{path}", headers={**headers, "Content-Type": "application/json",
                                                        "Accept": "text/event-stream"},
                      data=json.dumps(body), stream=True, timeout=900)
    rec = {"started_utc": started.isoformat(), "status": r.status_code,
           "request_id_header": r.headers.get("X-Snowflake-Request-Id")}
    events, first, ev = [], None, None
    if r.status_code >= 400:
        rec["error_body"] = r.text[:2000]
    else:
        r.encoding = "utf-8"          # the SSE stream is UTF-8; requests guesses Latin-1 without a charset
        for raw in r.iter_lines(decode_unicode=True):
            if first is None:
                first = time.monotonic() - t0
            if raw.startswith("event:"):
                ev = raw[6:].strip()
            elif raw.startswith("data:"):
                data = raw[5:].strip()
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    pass
                events.append({"event": ev, "data": data})
    rec["seconds_to_first_byte"] = None if first is None else round(first, 2)
    rec["seconds_total"] = round(time.monotonic() - t0, 2)
    rec["events"] = events
    return rec


def table_of(d: dict) -> dict:
    """A response.table event or a final-response table block: title, column names, rows, query id."""
    rs = d.get("result_set") or {}
    cols = [c.get("name") for c in (rs.get("resultSetMetaData") or {}).get("rowType", [])]
    return {"title": d.get("title"), "columns": cols, "rows": rs.get("data") or [], "query_id": d.get("query_id")}


def summarize(events: list[dict]) -> dict:
    """Session 8c, step 1a: every table of the answer is kept (title, columns, rows), from the response.table events and
    the final response's table blocks, once each; it is part of the answer and graded (decision 4)."""
    out: dict = {"tool_uses": [], "tool_results": [], "warnings": [], "text": "", "tables": [], "metadata": None,
                 "request_id": None}
    seen = set()

    def keep(t: dict) -> None:
        key = (t["query_id"], t["title"], json.dumps(t["rows"]))
        if key not in seen:
            seen.add(key)
            out["tables"].append(t)
    for e in events:
        d = e["data"]
        if not isinstance(d, dict):
            continue
        if e["event"] == "response.tool_use":
            out["tool_uses"].append({k: d.get(k) for k in ("type", "name", "input", "tool_use_id")})
        elif e["event"] == "response.tool_result":
            content = json.dumps(d.get("content", ""), default=str)
            out["tool_results"].append({"type": d.get("type"), "name": d.get("name"), "status": d.get("status"),
                                        "content": content[:3000]})
        elif e["event"] == "response.warning":
            out["warnings"].append(d)
        elif e["event"] == "response.table":
            keep(table_of(d))
        elif e["event"] == "metadata":
            out["request_id"] = out["request_id"] or d.get("request_id") or (d.get("metadata") or {}).get("request_id")
    resp = final_response(events)
    if resp:
        out["text"] = "".join(c.get("text", "") for c in resp.get("content", []) if c.get("type") == "text")
        for c in resp.get("content", []):
            if c.get("type") == "table" and isinstance(c.get("table"), dict):
                keep(table_of(c["table"]))
        out["metadata"] = resp.get("metadata")
        out["usage"] = resp.get("usage") or (resp.get("metadata") or {}).get("usage")
        out["request_id"] = out["request_id"] or resp.get("request_id") or (resp.get("metadata") or {}).get("request_id")
    return out


def call_tokens(call: dict) -> dict:
    """Orchestration tokens of one REST call, from the REST usage of its final response (guardrail tokens apart)."""
    usage = call.get("usage") or (call.get("metadata") or {}).get("usage") or {}
    o = next((x for x in usage.get("tokens_consumed", []) if x.get("model_role") == "orchestration"), {})
    it = o.get("input_tokens") or {}
    return {"input": it.get("total", 0), "cache_write": it.get("cache_write", 0), "cache_read": it.get("cache_read", 0),
            "output": (o.get("output_tokens") or {}).get("total", 0)}


def turn_tokens(calls: list[dict]) -> dict:
    """Session 8c, step 1a: the turn's REST usage tokens, summed over its calls (approval and client-side resumes
    included), with the largest call."""
    per = [call_tokens(c) for c in calls]
    out = {k: sum(p[k] for p in per) for k in ("input", "cache_write", "cache_read", "output")}
    return {**out, "max_call_input": max((p["input"] for p in per), default=0), "calls": len(per)}


def turn_model(calls: list[dict]) -> str | list[str] | None:
    """Pre-stage-1 fix: the orchestration model_name of the turn's REST usage (usage.tokens_consumed[], role
    orchestration), None when no call carries it; a list if the calls of one turn name several models."""
    names = sorted({x["model_name"] for c in calls
                    for x in ((c.get("usage") or (c.get("metadata") or {}).get("usage") or {}).get("tokens_consumed") or [])
                    if x.get("model_role") == "orchestration" and x.get("model_name")})
    return None if not names else names[0] if len(names) == 1 else names


# Session 8c-0, step 8 (decision 4): from budget s8c0 on, and for every campaign budget, a label carries the
# configuration, the question, the stage and the repetition (<CONFIG>_<QUESTION>_<stage>_r<n>), and a label whose
# log already exists is refused before any call (the DIM_MIX log of step 6 was overwritten by step 7e).
STRICT_LABELS = ("s8c0", "campaign", "manual")
LABEL = re.compile(r"^(A|B1|B2|C|CR|D|DP)_[A-Z][A-Z0-9_]*?_[a-z0-9][a-z0-9-]*_r[1-9][0-9]*$")   # CR: C-raw, session 13


def log_tag(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def check_label(label: str, budget_name: str, log_dir: Path) -> str:
    if budget_name.startswith(STRICT_LABELS):
        if not LABEL.match(label):
            raise SystemExit(f"label {label!r} must be <CONFIG>_<QUESTION>_<stage>_r<n> (budget {budget_name})")
        if budget_name == "manual" and not re.search(r"_manual_r[1-9][0-9]*$", label):
            raise SystemExit(f"label {label!r} must be <CONFIG>_<QUESTION>_manual_r<n> (budget manual)")
        for f in (f"summary_{log_tag(label)}.json", f"trace_{log_tag(label)}.json"):
            if (log_dir / f).exists():
                raise SystemExit(f"label {label!r} already has a log ({f}): refused, nothing overwritten")
    return label


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--connection", default="linkml_svc")
    ap.add_argument("--agent", required=True)
    ap.add_argument("--question", default="")
    ap.add_argument("--label", required=True)
    ap.add_argument("--budget", choices=sorted(CAPS), required=True)
    ap.add_argument("--block", help="campaign budget: the block's name (<stage>_<CONFIG>), one call count per block")
    ap.add_argument("--block-cap", type=int, help="campaign budget: REST calls allowed in the block, resumes included")
    ap.add_argument("--turn-cap", type=int, help="REST calls allowed for this question, resumes included (campaign: 3)")
    ap.add_argument("--token-ceiling", type=int,
                    help="abort the turn when one call's orchestration input tokens exceed this (exit code 3)")
    ap.add_argument("--turn-usd-cap", type=float,
                    help="stop the turn once its estimated cost exceeds this many USD (exit code 4; session 9a)")
    ap.add_argument("--no-trace", action="store_true", help="do not poll the trace; it is read after the campaign")
    ap.add_argument("--policy", choices=["deny-all", "probe", "c0", "c", "w", "dp", "stop"], default="deny-all")
    ap.add_argument("--thread", type=Path, help="JSON file with prior messages of the same thread (drill question)")
    ap.add_argument("--decisions", type=Path, help="resume: JSON list of {tool_use_id, decision[, reason]}")
    ap.add_argument("--save-thread", type=Path, help="write the conversation after this call, for a follow-up")
    ap.add_argument("--role-headers", action="store_true",
                    help="send X-Snowflake-Role / X-Snowflake-Warehouse (session 2 caller shape, for <ADMIN_USER>)")
    ap.add_argument("--log-dir", type=Path, required=True)
    ap.add_argument("--client-sql", action="store_true",
                    help="execute client-side snowflake_sql_execute tool uses (one SELECT only) and return the result")
    a = ap.parse_args()
    a.log_dir.mkdir(parents=True, exist_ok=True)
    check_label(a.label, a.budget, a.log_dir)          # before any connection or call
    if a.budget == "campaign":
        if not a.block or not a.block_cap:
            raise SystemExit("budget campaign needs --block and --block-cap")
        budget = Budget(a.log_dir, f"campaign_{a.block}", a.block_cap)
    else:
        budget = Budget(a.log_dir, a.budget)
    p = conn_params(a.connection)

    if a.role_headers:      # session 2 caller shape: no default role or warehouse, both sent as headers
        con = snowflake.connector.connect(connection_name=a.connection, role="LINKML_METRICS_ROLE",
                                          warehouse="LINKML_METRICS_WH")
    else:
        con = snowflake.connector.connect(connection_name=a.connection)
    cur = con.cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    host = con.host
    headers = {"Authorization": f"Bearer {keypair_jwt(p)}", "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT"}
    if a.role_headers:
        headers.update({"X-Snowflake-Role": "LINKML_METRICS_ROLE", "X-Snowflake-Warehouse": "LINKML_METRICS_WH"})
    path = f"/api/v2/databases/{DB}/schemas/{SCHEMA}/agents/{a.agent}:run"

    messages = json.loads(a.thread.read_text()) if a.thread else []
    if a.decisions:
        messages = messages + [{"role": "user", "content": [{"type": "permission_decision", "permission_decision": d}
                                                            for d in json.loads(a.decisions.read_text())]}]
    else:
        messages = messages + [{"role": "user", "content": [{"type": "text", "text": a.question}]}]
    out = {"label": a.label, "agent": a.agent, "question": a.question, "calls": []}
    t_start = dt.datetime.now(dt.timezone.utc)
    while True:
        stop = before_call(budget, len(out["calls"]), a.turn_cap)
        if stop:
            out["guard"], out["stopped"] = stop
            break
        try:
            rec = post(host, path, headers, {"messages": messages})
        except requests.RequestException as e:     # session 8c: a timeout or a dropped stream is a counted, failed call
            rec = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "status": 0, "request_id_header": None,
                   "error_body": f"{type(e).__name__}: {e}"[:2000], "seconds_to_first_byte": None, "seconds_total": None,
                   "events": []}
        s = summarize(rec["events"])
        call = {"n": budget.used + 1, "label": a.label, **{k: v for k, v in rec.items() if k != "events"}, **s}
        call["request_id"] = call["request_id"] or call["request_id_header"]
        budget.spend({k: call[k] for k in ("n", "label", "status", "started_utc", "seconds_total", "request_id")})
        append_jsonl(a.log_dir / "events.jsonl", {"n": call["n"], "label": a.label, "events": rec["events"]})
        out["calls"].append(call)
        if rec["status"] >= 400 or rec["status"] == 0:
            break
        stop = token_guard(call, a.token_ceiling) or turn_cost_guard(out["calls"], a.turn_usd_cap)
        if stop:
            out["guard"], out["stopped"] = stop
            break
        asks = pending_permissions(rec["events"])
        resp = final_response(rec["events"])
        if resp:
            messages = messages + [{"role": "assistant", "content": resp.get("content", [])}]
        client = []
        if resp and a.client_sql and not asks:
            done = {b["tool_result"].get("tool_use_id") for b in resp.get("content", []) if b.get("type") == "tool_result"}
            client = [b["tool_use"] for b in resp.get("content", []) if b.get("type") == "tool_use"
                      and b["tool_use"].get("client_side_execute") and b["tool_use"].get("tool_use_id") not in done]
        if client:
            if "csql" not in locals():
                ccon = snowflake.connector.connect(connection_name="linkml_svc")
                csql = ccon.cursor()
                csql.execute("USE SECONDARY ROLES NONE")
            blocks = []
            for u in client:
                sql = (u.get("input") or {}).get("sql", "")
                if u.get("name") == "snowflake_sql_execute":
                    status, text, qid = client_sql.execute(csql, sql)
                else:
                    status, text, qid = "error", f"Tool {u.get('name')} is not executed by this client.", None
                rec_c = {"n": call["n"], "label": a.label, "tool_use_id": u.get("tool_use_id"), "name": u.get("name"),
                         "sql": sql, "status": status, "query_id": qid, "result": text[:2000]}
                append_jsonl(a.log_dir / "client_sql.jsonl", rec_c)
                call.setdefault("client_executions", []).append(rec_c)
                blocks.append({"type": "tool_result", "tool_result": {
                    "tool_use_id": u.get("tool_use_id"), "type": u.get("type"), "name": u.get("name"),
                    "content": [{"type": "text", "text": text}], "status": status}})
            messages = messages + [{"role": "user", "content": blocks}]
            continue
        if not asks:
            break
        if a.policy == "stop":
            call["permission_requests"] = asks
            tag_ = re.sub(r"[^a-z0-9]+", "_", a.label.lower()).strip("_")
            (a.log_dir / f"pending_{tag_}.json").write_text(json.dumps(asks, indent=2, default=str))
            out["stopped"] = "permission request: decision left to the project owner"
            break
        blocks = []
        for ask in asks:
            decision, rule = decide(ask, a.policy)
            opts = ask["permission"]["options"]
            if decision == "Allow Once" and decision not in opts and "Allow this command" in opts:
                decision = "Allow this command"     # measured single-use option name (session 2)
            if decision not in opts:
                raise SystemExit(f"unexpected permission options {opts}; stopping")
            call.setdefault("permission_requests", []).append(
                {"type": ask.get("type"), "name": ask.get("name"), "input": ask.get("input"), "options": opts,
                 "risk": ask.get("permission"), "decision": decision, "rule": rule})
            d = {"tool_use_id": ask.get("tool_use_id"), "decision": decision}
            if decision == "Deny":
                d["reason"] = "Denied by the probe policy."
            blocks.append({"type": "permission_decision", "permission_decision": d})
        messages = messages + [{"role": "user", "content": blocks}]
    if a.save_thread:
        a.save_thread.write_text(json.dumps(messages, default=str))

    t_end = dt.datetime.now(dt.timezone.utc)
    out["window_utc"] = [t_start.isoformat(), t_end.isoformat()]
    out["tokens"] = turn_tokens(out["calls"])          # session 8c: the turn's REST usage tokens
    out["model"] = turn_model(out["calls"])            # pre-stage-1 fix: the orchestration model of the REST usage
    out["served_version"] = None                       # the trace's version name, filled by eval/campaign.py traces
    tag = re.sub(r"[^a-z0-9]+", "_", a.label.lower()).strip("_")
    if a.no_trace:                                     # session 8c: traces are read after the campaign (decision 4)
        out["trace_rows"] = None
    else:
        # Trace: best-effort and late (per docs). Poll until the row count after t_start is stable, up to 5 minutes.
        last, rows, cols = -1, [], []
        q = (f"SELECT * FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS('{DB}', '{SCHEMA}', '{a.agent}', "
             f"'CORTEX AGENT')) WHERE TIMESTAMP >= '{(t_start - dt.timedelta(seconds=5)).strftime('%Y-%m-%d %H:%M:%S')}'"
             f"::TIMESTAMP_NTZ")
        for _ in range(10):
            try:
                rows = cur.execute(q).fetchall()
                cols = [d[0] for d in cur.description]
            except snowflake.connector.errors.ProgrammingError as e:
                out["trace_error"] = f"{e.errno}: {e.msg}"
                break
            if rows and len(rows) == last:
                break
            last = len(rows)
            time.sleep(30)
        trace = [dict(zip(cols, r)) for r in rows]
        (a.log_dir / f"trace_{tag}.json").write_text(json.dumps(trace, default=str))
        spans = []
        for t in trace:
            rec_ = t.get("RECORD")
            rec_ = json.loads(rec_) if isinstance(rec_, str) else (rec_ or {})
            attrs = t.get("RECORD_ATTRIBUTES")
            attrs = json.loads(attrs) if isinstance(attrs, str) else (attrs or {})
            spans.append({"name": rec_.get("name"), "status": rec_.get("status"),
                          "keys": sorted(k for k in attrs if any(w in k for w in ("skill", "status", "error", "role", "tool")))[:25]})
        out["trace_rows"] = len(trace)
        out["trace_spans"] = spans
    out["calls_used"] = {b: len(v) for b, v in budget.state.items() if not b.startswith("_")}
    (a.log_dir / f"summary_{tag}.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str).replace(host, "<host>"))
    con.close()
    sys.exit({"block_cap": 2, "token": 3, "turn_cost": 4}.get(out.get("guard"), 0))


if __name__ == "__main__":
    main()
