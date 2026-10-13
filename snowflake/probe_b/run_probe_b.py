"""
Phase 0, probe B (config D'): a TEMPORARY agent with code_toolset_all and one stage skill, run over REST.

    python snowflake/probe_b/run_probe_b.py --connection perso --log-dir <scratch dir>

One process keeps the creating session open for the whole run, because a temporary agent is bound to the
creating user, role and session (per docs). The run:
1. stages skills/linkml-probe/ to @LINKML_METRICS.RAW.SKILLS_PROBE (a permanent stage, dropped at session end);
2. creates TEMPORARY AGENT LINKML_METRICS.RAW.LINKML_PROBE_B_TMP_PROBE from agent_spec.yaml;
3. calls agent:run with a key-pair JWT; on a 4xx, with the creating session's token; on a 4xx again, the
   objectless endpoint with the same spec inline. If the objectless call rejects or ignores the skill, it stops;
4. answers every approval request with the policy below, and resends the conversation until no request is left;
5. reads the trace (GET_AI_OBSERVABILITY_EVENTS) from the creating session.

Approval policy (decided by the project owner, applied mechanically by `decide`):
- bash: allow only the step 1 command of SKILL.md, exactly, or preceded by `cd <skill folder> &&` / `;`,
  or with an absolute path to linkml-probe/probe.py. Leading and trailing whitespace is ignored.
- SQL: allow only the step 2 statement, ignoring case and whitespace.
- Anything else: Deny. Every REST call, failed or denied, counts against the cap of 10.

Raw events go to --log-dir (outside the repo: they carry the account host). The summary is printed as JSON.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import re
import time
import tomllib
from pathlib import Path

import jwt
import requests
import snowflake.connector
import yaml
from cryptography.hazmat.primitives import serialization

HERE = Path(__file__).resolve().parent
DB, SCHEMA, ROLE, WH = "LINKML_METRICS", "RAW", "LINKML_METRICS_ROLE", "LINKML_METRICS_WH"
STAGE = f"{DB}.{SCHEMA}.SKILLS_PROBE"
STAGE_DDL = ""
AGENT = "LINKML_PROBE_B_TMP_PROBE"
QUESTION = "Run the linkml probe."
CAP = 10

STEP1 = "python3 probe.py; env | cut -d= -f1 | grep -i snowflake | sort"
STEP2 = "SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST"
# Run C (session 2, after the stage skill failed to mount on every path): no skill; sandbox code asked directly.
STEP1_C = ('python3 -c "import snowflake.connector as sc; print(sc.connect().cursor().execute(\'SELECT CURRENT_ROLE(), '
           'CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST\').fetchall())"; '
           'env | cut -d= -f1 | grep -i snowflake | sort')
QUESTION_C = ("Run these two steps exactly once each, in order, and report each raw output verbatim in a fenced block, "
              "errors included. Do not retry, do not fix errors, do not use any other tool.\n"
              f"1. With bash, run exactly: {STEP1_C}\n"
              f"2. With the Snowflake SQL tool, run exactly: {STEP2}")
RUN_C = False
_STEP1_CD = re.compile(r"^cd\s+(['\"]?)(\S*linkml-probe/?)\1\s*(&&|;)\s*" + re.escape(STEP1) + r"$")
_STEP1_ABS = re.compile(r"^python3\s+(['\"]?)/\S*/linkml-probe/probe\.py\1" + re.escape(STEP1[len("python3 probe.py"):]) + r"$")


def norm_sql(s: str) -> str:
    return " ".join(s.split()).upper()


def strings(obj) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in strings(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in strings(v)]
    return []


def decide(tool: dict) -> tuple[str, str]:
    """Return (decision, rule) for one tool_use event carrying permission options."""
    label = f"{tool.get('type', '')} {tool.get('name', '')}".lower()
    texts = [t.strip() for t in strings(tool.get("input", {}))]
    if "bash" in label and RUN_C:
        if STEP1_C in texts:
            return "Allow Once", "run C bash: exact"
    elif "bash" in label:
        for t in texts:
            if t == STEP1:
                return "Allow Once", "bash: step 1 exact"
            if _STEP1_CD.match(t):
                return "Allow Once", "bash: step 1 preceded by cd to the skill folder"
            if _STEP1_ABS.match(t):
                return "Allow Once", "bash: step 1 with an absolute path to probe.py"
    if "sql" in label:
        for t in texts:
            if norm_sql(t) == norm_sql(STEP2):
                return "Allow Once", "sql: step 2, case and whitespace ignored"
    return "Deny", "not one of the two approved commands"


# ------------------------------------------------------------------------------------------------ auth

def conn_params(name: str) -> dict:
    return tomllib.loads((Path.home() / ".snowflake" / "connections.toml").read_text())[name]


def keypair_jwt(p: dict) -> str:
    key = serialization.load_pem_private_key(Path(p["private_key_file"]).read_bytes(), password=None)
    pub = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    fp = "SHA256:" + base64.b64encode(hashlib.sha256(pub).digest()).decode()
    acct, user = p["account"].upper().replace(".", "-"), p["user"].upper()
    now = int(time.time())
    return jwt.encode({"iss": f"{acct}.{user}.{fp}", "sub": f"{acct}.{user}", "iat": now, "exp": now + 3000},
                      key, algorithm="RS256")


# ------------------------------------------------------------------------------------------------ REST

class Calls:
    def __init__(self, host: str, log: Path):
        self.host, self.log, self.n, self.summary = host, log, 0, []

    def run(self, path: str, headers: dict, body: dict, label: str) -> dict:
        if self.n >= CAP:
            raise SystemExit(f"call cap {CAP} reached")
        self.n += 1
        t0 = time.monotonic()
        rec = {"call": self.n, "label": label, "endpoint": path, "auth": headers.get("Authorization", "")[:16] + "...",
               "started_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
        r = requests.post(f"https://{self.host}{path}", headers={**headers, "Content-Type": "application/json",
                                                                  "Accept": "text/event-stream"},
                          data=json.dumps(body), stream=True, timeout=900)
        rec["status"] = r.status_code
        rec["request_id_header"] = r.headers.get("X-Snowflake-Request-Id") or r.headers.get("x-snowflake-request-id")
        events, first = [], None
        if r.status_code >= 400:
            rec["error_body"] = r.text[:2000]
        else:
            ev = None
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
        rec["event_counts"] = {}
        for e in events:
            rec["event_counts"][e["event"]] = rec["event_counts"].get(e["event"], 0) + 1
        with self.log.open("a") as f:
            f.write(json.dumps({"call": self.n, "label": label, "status": r.status_code, "events": events},
                               default=str) + "\n")
        rec["events"] = events
        self.summary.append(rec)
        return rec


def final_response(events: list[dict]) -> dict | None:
    for e in reversed(events):
        if e["event"] == "response" and isinstance(e["data"], dict):
            return e["data"]
    return None


def pending_permissions(events: list[dict]) -> list[dict]:
    out = []
    for e in events:
        if e["event"] == "response.tool_use" and isinstance(e["data"], dict):
            if (e["data"].get("permission") or {}).get("options"):
                out.append(e["data"])
    return out


def skill_loaded(events: list[dict]) -> bool:
    """A skill tool_result without error. Invoking the name alone is not a load (run 1 to 4: 'Skill not found')."""
    return any(e["event"] == "response.tool_result" and isinstance(e["data"], dict) and e["data"].get("type") == "skill"
               and e["data"].get("status") != "error" for e in events)


def converse(calls: Calls, path: str, headers: dict, base: dict, label: str, resume: dict | None = None) -> dict:
    """First call, then one call per round of approvals, until no permission request is left.
    resume = a logged call ({"call", "events"}) whose approval request was not answered: continue from it."""
    messages = [{"role": "user", "content": [{"type": "text", "text": QUESTION_C if RUN_C else QUESTION}]}]
    if resume:
        rec = {"call": resume["call"], "status": 200, "events": resume["events"]}
        calls.summary.append({"call": resume["call"], "label": label + " (resumed from log)", "status": 200})
    else:
        rec = calls.run(path, headers, {**base, "messages": messages}, label)
    if rec["status"] >= 400:
        return rec
    rec["approvals"] = []
    while True:
        asks = pending_permissions(rec["events"])
        if not asks:
            return rec
        resp = final_response(rec["events"])
        if resp is None:
            raise SystemExit("permission request without a final response event; stopping")
        blocks = []
        for a in asks:
            decision, rule = decide(a)
            opts = a["permission"]["options"]
            if decision == "Allow Once" and decision not in opts and "Allow this command" in opts:
                # Measured run C: options were ['Allow this command', 'Allow all bash for this session', 'Deny'], not
                # the documented ['Allow Once', 'Deny']. The single-use option is the policy's "Allow Once"; a
                # session-wide option is never chosen.
                decision, rule = "Allow this command", rule + " (single-use option of this tool)"
            if decision not in opts:
                raise SystemExit(f"unexpected permission options {a['permission']['options']}; stopping")
            entry = {"call": calls.n, "tool_use_id": a.get("tool_use_id"), "type": a.get("type"),
                     "name": a.get("name"), "input": a.get("input"), "options": a["permission"]["options"],
                     "decision": decision, "rule": rule}
            calls.summary[-1].setdefault("permission_requests", []).append(entry)
            d = {"tool_use_id": a.get("tool_use_id"), "decision": decision}
            if decision == "Deny":
                d["reason"] = "Denied by the probe policy: only the two commands of the linkml-probe skill are approved."
            blocks.append({"type": "permission_decision", "permission_decision": d})
        messages = messages + [{"role": "assistant", "content": resp.get("content", [])},
                               {"role": "user", "content": blocks}]
        if calls.n >= CAP:
            calls.summary[-1]["unanswered"] = "call cap reached: approval request recorded, no decision sent"
            return rec
        rec = calls.run(path, headers, {**base, "messages": messages}, label + " (after decision)")
        if rec["status"] >= 400:
            return rec


# ------------------------------------------------------------------------------------------------ main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--connection", default="perso")
    ap.add_argument("--log-dir", type=Path, required=True)
    ap.add_argument("--start", choices=["jwt", "session-token", "objectless", "run-c"], default="jwt",
                    help="session-token skips the JWT call (measured 401 / 399513 on run 1)")
    ap.add_argument("--calls-already-used", type=int, default=0, help="calls spent by earlier runs (the cap is per probe)")
    ap.add_argument("--resume-log", type=Path, help="events log whose last call holds an unanswered approval request")
    ap.add_argument("--sse-stage", action="store_true",
                    help="run B: skill on a new SNOWFLAKE_SSE stage with a directory table; one call, no decision sent")
    a = ap.parse_args()
    global RUN_C, STAGE, STAGE_DDL, CAP
    RUN_C = a.start == "run-c"
    if a.sse_stage:
        STAGE = f"{DB}.{SCHEMA}.SKILLS_SSE_PROBE"
        STAGE_DDL = " ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE') DIRECTORY = (ENABLE = TRUE)"
        CAP = a.calls_already_used + 1          # one call, and no approval is answered
    if RUN_C:
        a.start = "objectless"
    a.log_dir.mkdir(parents=True, exist_ok=True)
    log = a.log_dir / "probe_b_events.jsonl"
    p = conn_params(a.connection)
    spec_text = (HERE / "agent_spec.yaml").read_text()
    spec = yaml.safe_load(spec_text)
    out: dict = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat()}

    con = snowflake.connector.connect(connection_name=a.connection, role=ROLE, warehouse=WH, database=DB, schema=SCHEMA)
    cur = con.cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    out["creating_session"] = cur.execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), CURRENT_SESSION()").fetchone()
    cur.execute(f"CREATE STAGE IF NOT EXISTS {STAGE}{STAGE_DDL} "
                f"COMMENT = 'linkml-metrics probe B skill source; drop at session end'")
    for f in sorted((HERE / "skills" / "linkml-probe").iterdir()):
        cur.execute(f"PUT 'file://{f}' @{STAGE}/skills/linkml-probe/ AUTO_COMPRESS = FALSE OVERWRITE = TRUE")
    cur.execute(f"ALTER STAGE {STAGE} REFRESH")
    out["stage_ls"] = [(r[0], r[1]) for r in cur.execute(f"LS @{STAGE}").fetchall()]
    cur.execute(f"CREATE OR REPLACE TEMPORARY AGENT {DB}.{SCHEMA}.{AGENT} FROM SPECIFICATION $${spec_text}$$")
    out["show_agents"] = [r[1] for r in cur.execute(f"SHOW AGENTS IN SCHEMA {DB}.{SCHEMA}").fetchall()]

    host = con.host
    calls = Calls(host, log)
    calls.n = a.calls_already_used
    common = {"X-Snowflake-Role": ROLE, "X-Snowflake-Warehouse": WH}
    jwt_h = {**common, "Authorization": f"Bearer {keypair_jwt(p)}", "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT"}
    named = f"/api/v2/databases/{DB}/schemas/{SCHEMA}/agents/{AGENT}:run"
    # Preflight, not an agent call (outside the cap): does the JWT authenticate, and does a JWT session list the
    # temporary agent?
    pre = requests.get(f"https://{host}/api/v2/databases/{DB}/schemas/{SCHEMA}/agents",
                       headers={**jwt_h, "Accept": "application/json"}, timeout=60)
    out["preflight_list_agents_jwt"] = {"status": pre.status_code, "body": pre.text[:1500]}
    first = calls.n + 1
    rec = {"status": 401, "call": first}
    if a.start == "jwt":
        rec = converse(calls, named, jwt_h, {}, "named temporary agent, key-pair JWT")
    if a.start == "objectless":
        rec = {"status": 401, "call": first - 1}
    elif rec["status"] >= 400 and rec["call"] == first:
        tok_h = {**common, "Authorization": f'Snowflake Token="{con.rest.token}"'}
        rec = converse(calls, named, tok_h, {}, "named temporary agent, creating session token")
    if rec["status"] >= 400 and rec["call"] <= first + 1 or a.start == "objectless":
        keys = ("models", "instructions", "orchestration", "tools", "tool_resources") + (() if RUN_C else ("skills",))
        inline = {k: spec[k] for k in keys}
        if "skills" in inline:
            inline["skills"] = [{**sk, "source": {**sk["source"], "path": f"@{STAGE}/skills/linkml-probe"}}
                                for sk in inline["skills"]]
        if RUN_C:
            inline["instructions"] = {"response": "Report raw tool outputs verbatim."}
        resume = None
        if a.resume_log:
            resume = json.loads(a.resume_log.read_text().splitlines()[-1])
        rec = converse(calls, "/api/v2/cortex/agent:run", jwt_h, inline, "objectless, key-pair JWT, spec inline", resume)
        events = [e for c in calls.summary if c["label"].startswith("objectless") for e in c.get("events", [])]
        if not RUN_C and (rec["status"] >= 400 or not skill_loaded(events)):
            out["stopped"] = "objectless call rejected or ignored the skill: propose a permanent agent"

    out["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    # Telemetry is best-effort and can arrive late (per docs): poll until the row count is stable, up to 6 minutes.
    last, rows, cols = -1, [], []
    for _ in range(12):
        try:
            rows = cur.execute(f"SELECT * FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS("
                               f"'{DB}', '{SCHEMA}', '{AGENT}', 'CORTEX AGENT'))").fetchall()
            cols = [d[0] for d in cur.description]
        except snowflake.connector.errors.ProgrammingError as e:
            out["trace_error"] = f"{e.errno}: {e.msg}"
            break
        if rows and len(rows) == last:
            break
        last = len(rows)
        time.sleep(30)
    out["trace_rows"] = len(rows)
    (a.log_dir / "probe_b_trace.json").write_text(json.dumps([dict(zip(cols, r)) for r in rows], default=str))
    out["calls"] = [{k: v for k, v in c.items() if k != "events"} for c in calls.summary]
    out["calls_used"] = calls.n
    (a.log_dir / "probe_b_summary.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str).replace(host, "<host>"))
    con.close()


if __name__ == "__main__":
    main()
