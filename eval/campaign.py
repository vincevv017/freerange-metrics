"""
Campaign runner, two stages (session 8c; coordination doc, Sessions tab, "Campagne en deux etapes"; eval/campaign.md).

    python eval/campaign.py plan  --stage 1                   # the call plan, counts and caps, no call
    python eval/campaign.py plan  --stage 2 [--cut 0|1|2|3]
    python eval/campaign.py run   --stage 1 [--streams 1] [--only C]
    python eval/campaign.py run   --stage 2 [--cut ...] [--streams 1]
    python eval/campaign.py grade --stage 1 [--rubric 3.2]    # grades of every completed turn, no call
    python eval/campaign.py traces --stage 1                  # after the campaign: one trace read per agent
    python eval/campaign.py versions --stage 1                # the served version check again, no call

Stage 1: the questions of generated/reference_questions.yaml that are not held out, once on every configuration; one
block per configuration (a warm-up call, not graded, then the questions back to back); configuration order and
question order shuffled with fixed seeds; BULK_SCOPE_DRILL right after BULK_SCOPE in its thread. Stage 1 is
repetition 1. Labels <CONFIG>_<QUESTION>_campaign-s1_r1.
Stage 2: the questions eval/gate.py selected (eval/stage2.yaml) plus the held-out questions; repetitions in all: 5 for
B2, C and D', 3 for B1 and D; A is not played in stage 2 (owner, 2026-10-06: the stage 1 "zero effort" reference
point). A selected question was asked once in stage 1, so stage 2 runs r2 to rN; a held-out question runs r1 to rN. All repetitions of
one configuration in one block, question order shuffled per repetition, configuration order shuffled. Labels
<CONFIG>_<QUESTION>_campaign-s2_r<n>. Cuts, in the owner's fixed order (--cut): 1, D' to 5; 2, B1 and D to 3 as well;
3, the questions of eval/stage2.yaml drop_order removed as well (never a held-out question).

Guards (eval/guards.py, run_call.py): a call cap per block counting every REST call (stage 1: 30, D' 100; stage 2: the
planned count plus 10 percent; stage 1 caps were 26 before session 9a), at most 3 REST calls per question, 4 for D' (D064), the runaway guard (owner, session 9a: a turn whose
cost estimate exceeds 2 USD is stopped and stops its block; the per-call token ceiling is recorded, no longer a stop), 3 consecutive errors stop the block, 2
stopped blocks stop the stage, and the cost estimate (AI Credits plus the warehouse hours elapsed) pauses the stage at
90 percent of its ceiling (stage 1: 40 USD; stage 2: --ceiling-usd, set at the cost read) until the owner resumes it. An agent's
behaviour never stops anything.

Every call goes through snowflake/probe_b/mount/run_call.py as LINKML_SVC, after agents.py warm, with --no-trace
(traces are read after the campaign).

Served version (pre-stage-1 fix): before each block, SHOW VERSIONS IN AGENT gives the agent's default version, stored
in the block state as declared_version; a version other than the frozen state of eval/campaign.md (or none read) stops
the block before its first turn and holds the stage. After the stage, traces writes into each turn's summary the
version name its trace rows carry (served_version) and checks every turn against the frozen state; a turn served by
another version is a harness event for the owner, never regraded silently.

Trace rows by request id (D065, session 9a): the time window bounds the read; a turn keeps only the rows whose
ai.observability.record_id is one of its calls' request ids; rows in its window from a request the harness did not make
(a concurrent Snowsight turn, session 8c-1) are counted as foreign and reported; a turn with no row of its own is
no_trace. Never thread_id (0 over REST), never a bare numeric value (ids collide across objects).

Skill pre-check (D066, session 9a): before a stage's first call, every STAGE skill path of the frozen specs is listed
and read back with GET as LINKML_SVC into a temporary directory; a repository file missing or 0 B on the stage, a file
with no repository counterpart, or a sha256 that differs halts the stage (kept on resume). LIST sizes and md5 are never
compared (stored sizes are encrypted, rounded up to 16 bytes). State: <run dir>/state_<stage>.json, written after every call. A resumed run
skips the completed turns and never overwrites a log: a failed turn is retried under the stage tag with an attempt
suffix (campaign-s1-a2), so its first log stays. A stopped block stays stopped on resume (the owner decides).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUN = Path.home() / "work" / "assets" / "linkml-metrics-runs" / os.environ.get("LINKML_RUN", "campaign")
QUESTIONS = yaml.safe_load((ROOT / "generated" / "reference_questions.yaml").read_text())["questions"]
STAGE2_FILE = ROOT / "eval" / "stage2.yaml"
REDUCED_FILE = ROOT / "eval" / "stage2_reduced.yaml"     # session 9b (owner, 2026-10-07): C and B2 only
CAMPAIGN_MD = ROOT / "eval" / "campaign.md"
VERSION_ATTR = "snow.ai.observability.object.version.name"     # the trace attribute (snowflake/phase4_others/records.py)
RECORD_ID_ATTR = "ai.observability.record_id"                  # the request id, on every trace row (session 8c-1, 66)
SKILLS_REPO = ROOT / "snowflake" / "phase4_others" / "skill"   # the repository copy of every staged skill
WARMUP = "How many countries does the dataset cover?"
CONFIGS = {   # agent, policy, extra flags, REST calls per question (D': approval and client-side resumes; 2.5 measured
    # in stage 1, 60 calls for 24 turns, owner 2026-10-07; was 1.85 from session 8)
    "A": ("LINKML_A", "deny-all", [], 1.0), "B1": ("LINKML_B1", "deny-all", [], 1.0),
    "B2": ("LINKML_B2", "deny-all", [], 1.0), "C": ("LINKML_C", "deny-all", [], 1.0),
    "D": ("LINKML_D", "dp", ["--client-sql"], 1.0), "DP": ("LINKML_DP", "dp", ["--client-sql"], 2.5),
}
STAGE_TAG = {1: "campaign-s1", 2: "campaign-s2"}
# Session 13 (owner, 2026-10-08): configuration C-raw played as an arm beside the campaign (--arm CR), on exactly C's
# questions in C's order (C's blocks and seeds), under its own stage tags, state, logs and grade files. CONFIGS keeps the
# six configurations, so their order, seeds, plans and records do not change. "as": the configuration whose guard
# values (token ceiling, turn cap) the arm takes.
ARMS = {"CR": {"agent": "LINKML_C_RAW", "policy": "deny-all", "extra": [], "rest_calls": 1.0, "as": "C",
               "tags": {1: "craw-s1", 2: "craw-s2"}}}
ARM: str | None = None


def use_arm(name: str) -> None:
    global ARM, STAGE_TAG
    ARM, STAGE_TAG = name, dict(ARMS[name]["tags"])


def config(cfg: str) -> tuple:
    """(agent, policy, extra flags, REST calls per question) of a configuration or of an arm."""
    if cfg in ARMS:
        a = ARMS[cfg]
        return a["agent"], a["policy"], a["extra"], a["rest_calls"]
    return CONFIGS[cfg]


def twin(cfg: str) -> str:
    return ARMS[cfg]["as"] if cfg in ARMS else cfg


def arm_plan(stage: int) -> list[dict]:
    """The arm's one block: its twin's block of stage 1 (gate plan) or of the reduced stage 2, same turns, same order."""
    t = ARMS[ARM]["as"]
    b = next(x for x in (plan(1) if stage == 1 else reduced_plan()) if x["config"] == t)
    return [{"config": ARM, "cap": b["cap"], "turns": [dict(x) for x in b["turns"]]}]
THREAD_PARENT = {"BULK_SCOPE_DRILL": "BULK_SCOPE"}   # a follow-up turn and the turn whose thread it continues
REWARM_AFTER_S = 300      # owner, session 9a: a resumed block warms up again when its last call is older than this
STAGE1_CAP = {"A": 30, "B1": 30, "B2": 30, "C": 30, "D": 30, "DP": 100}    # D064: D' 4 calls x 25 turns; owner,
# session 9a: 30 (was 26), a one-call margin covered neither the added warm-ups nor a retry after an error
STAGE2_REPS = {"A": 1, "B1": 3, "B2": 5, "C": 5, "D": 3, "DP": 5}     # in all, stage 1 included (owner, decision 3
# after step 5); cuts 1 (D' to 5) and 2 (B1 and D to 3) are kept in the fixed order and change nothing at these counts;
# A: stage 1 only (owner, 2026-10-06), no stage 2 block
CUTS = {0: {}, 1: {"DP": 5}, 2: {"DP": 5, "B1": 3, "D": 3}, 3: {"DP": 5, "B1": 3, "D": 3}}
SEED = 20261005

_g = importlib.util.spec_from_file_location("guards", ROOT / "eval" / "guards.py")
guards = importlib.util.module_from_spec(_g)
sys.modules["guards"] = guards
_g.loader.exec_module(guards)


def held_out() -> list[str]:
    return [q["id"] for q in QUESTIONS if q.get("held_out")]


def added_in_stage2() -> list[str]:
    """Session 9b (owner, 2026-10-07): questions added in stage 2, asked of C and B2 only, never in stage 1."""
    return [q["id"] for q in QUESTIONS if q.get("added_in_stage") == 2]


def stage1_questions() -> list[str]:
    return [q["id"] for q in QUESTIONS if not q.get("held_out") and not q.get("added_in_stage")]


def shuffled(ids: list[str], seed: int) -> list[str]:
    """A seeded shuffle; BULK_SCOPE_DRILL right after BULK_SCOPE (same thread)."""
    rest = [i for i in ids if i != "BULK_SCOPE_DRILL"]
    random.Random(seed).shuffle(rest)
    if "BULK_SCOPE_DRILL" in ids:
        if "BULK_SCOPE" in rest:
            i = rest.index("BULK_SCOPE")
            rest = rest[:i + 1] + ["BULK_SCOPE_DRILL"] + rest[i + 1:]
        else:
            raise ValueError("BULK_SCOPE_DRILL needs BULK_SCOPE in the same repetition")
    return rest


def config_order(stage: int) -> list[str]:
    order = list(CONFIGS)
    random.Random(SEED + stage).shuffle(order)
    return order


def label(cfg: str, qid: str, stage: int, rep: int, attempt: int = 1) -> str:
    tag = STAGE_TAG[stage] + (f"-a{attempt}" if attempt > 1 else "")
    return f"{cfg}_{qid}_{tag}_r{rep}"


def stage2_input() -> dict:
    s = yaml.safe_load(STAGE2_FILE.read_text()) if STAGE2_FILE.exists() else {}
    return {"discriminating": s.get("discriminating", []), "a_passed": s.get("a_passed", []),
            "drop_order": s.get("drop_order", [])}


def reduced_plan() -> list[dict]:
    """Session 9b (owner, 2026-10-07): eval/stage2_reduced.yaml, C and B2 only, the questions of each repetition named
    there. Configuration order and question seeds as in the gate's plan; repetition 1 first, then repetition 2."""
    r = yaml.safe_load(REDUCED_FILE.read_text())
    known = {q["id"] for q in QUESTIONS}
    unknown = sorted({q for qs in r["repetitions"].values() for q in qs} - known)
    if unknown:
        raise SystemExit(f"{REDUCED_FILE.name}: unknown questions {unknown}")
    blocks = []
    for i, cfg in enumerate(config_order(2)):
        if cfg not in r["configurations"]:
            continue
        turns = [{"qid": "WARMUP", "rep": 1}]
        for rep, qs in sorted(r["repetitions"].items()):
            turns += [{"qid": q, "rep": rep} for q in shuffled(list(qs), SEED + 1000 * i + rep)]
        planned = sum(1 if t["qid"] == "WARMUP" else CONFIGS[cfg][3] for t in turns)
        blocks.append({"config": cfg, "cap": math.ceil(planned * 1.1), "turns": turns})
    return blocks


def route_groups(blocks: list[dict]) -> dict[str, str]:
    """Each planned question's report group (eval/grade.py route_group): the route agent C is expected to take."""
    group = {"coverage": "procedure", "semantic_view": "view only", "both": "both", "clarify": "no tool"}
    by_id = {q["id"]: q for q in QUESTIONS}
    return {t["qid"]: group[by_id[t["qid"]]["expected_route"]] for b in blocks for t in b["turns"]
            if t["qid"] != "WARMUP"}


def check_plan(st: "State", name: str) -> None:
    """A stage keeps the plan of its first run: a resume under another plan is refused (session 9b)."""
    if st.d.setdefault("plan", name) != name:
        raise SystemExit(f"{st.d['stage']} started with plan {st.d['plan']!r}, not {name!r}")
    st.save()


def plan(stage: int, cut: int = 0, reduced: bool = False) -> list[dict]:
    """Blocks in run order; each block: config, cap, and its turns (qid, rep) with the warm-up first."""
    if stage == 2 and reduced:
        return reduced_plan()
    blocks = []
    if stage == 1:
        qs = stage1_questions()
        for i, cfg in enumerate(config_order(1)):
            turns = [{"qid": "WARMUP", "rep": 1}] + [{"qid": q, "rep": 1} for q in shuffled(qs, SEED + 100 * i)]
            blocks.append({"config": cfg, "cap": STAGE1_CAP[cfg], "turns": turns})
        return blocks
    s2 = stage2_input()
    reps = {**STAGE2_REPS, **CUTS[cut]}
    disc = [q for q in s2["discriminating"] if not (cut >= 3 and q in s2["drop_order"])]
    for i, cfg in enumerate(config_order(2)):
        if cfg == "A":
            continue                              # owner, 2026-10-06: A is not repeated in stage 2
        per_rep: dict[int, list[str]] = {}
        for r in range(1, reps[cfg] + 1):
            per_rep[r] = ([q for q in disc] if r >= 2 else []) + held_out()
        turns = [{"qid": "WARMUP", "rep": 1}]
        for r, qs in per_rep.items():
            if "BULK_SCOPE_DRILL" in qs and "BULK_SCOPE" not in qs:
                qs = qs + ["BULK_SCOPE"]          # the drill needs its parent in the same thread
            turns += [{"qid": q, "rep": r} for q in shuffled(qs, SEED + 1000 * i + r)]
        if len(turns) == 1:
            continue
        planned = sum(1 if t["qid"] == "WARMUP" else CONFIGS[cfg][3] for t in turns)
        blocks.append({"config": cfg, "cap": math.ceil(planned * 1.1), "turns": turns})
    return blocks


def counts(blocks: list[dict]) -> dict:
    out = {}
    for b in blocks:
        q = sum(1 for t in b["turns"] if t["qid"] != "WARMUP")
        out[b["config"]] = {"graded_turns": q, "warmups": len(b["turns"]) - q,
                            "rest_calls_expected": round(q * CONFIGS[b["config"]][3]) + len(b["turns"]) - q,
                            "block_cap": b["cap"], "turn_cap": guards.turn_cap(b["config"])}
    out["total_rest_calls_expected"] = sum(v["rest_calls_expected"] for v in out.values())
    return out


# ------------------------------------------------------------------------------------------------ versions

def frozen_rows(path: Path = CAMPAIGN_MD) -> list[list[str]]:
    """The agent rows of the table under "## Frozen state" in eval/campaign.md, as cells."""
    out, inside = [], False
    for line in path.read_text().splitlines():
        if line.startswith("## "):          # session 13: an arm's frozen section is read only while the arm plays
            inside = line.startswith("## Frozen state") and (ARM is not None or ", arm " not in line)
        elif inside and line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) > 2 and re.fullmatch(r"LINKML_\w+", cells[1]):
                out.append(cells)
    return out


def frozen_versions(path: Path = CAMPAIGN_MD) -> dict[str, str]:
    """Agent name to version name, from the table under "## Frozen state" in eval/campaign.md."""
    out = {}
    for cells in frozen_rows(path):
        v = re.search(r"VERSION\$\d+", cells[2])
        if v:
            out[cells[1]] = v.group(0)
    missing = sorted({a for a, *_ in (list(CONFIGS.values()) + ([config(ARM)] if ARM else []))} - set(out))
    if missing:
        raise SystemExit(f"{path.name}: no frozen version for {missing}")
    return out


def default_version(rows: list[dict]) -> str | None:
    """The default version of SHOW VERSIONS IN AGENT rows (is_default 'true'), read, never computed."""
    return next((r["name"] for r in rows if str(r.get("is_default")).lower() == "true" and r.get("name")), None)


def declared_version(agent: str) -> str | None:
    """SHOW VERSIONS IN AGENT as agents.py reads it (perso, LINKML_METRICS_ROLE, the agents' owner); no warehouse."""
    import snowflake.connector
    con = snowflake.connector.connect(connection_name="perso")
    try:
        cur = con.cursor()
        cur.execute("USE SECONDARY ROLES NONE")
        cur.execute("USE ROLE LINKML_METRICS_ROLE")
        rows = cur.execute(f"SHOW VERSIONS IN AGENT LINKML_METRICS.RAW.{agent}").fetchall()
        cols = [d[0] for d in cur.description]
        return default_version([dict(zip(cols, r)) for r in rows])
    finally:
        con.close()


def check_declared(cfg: str, name: str, b: dict, st: "State") -> bool:
    """Before a block: the agent's default version, stored in the block state; another version than the frozen one, or
    none read, stops the block and holds the stage (harness guard)."""
    agent = config(cfg)[0]
    frozen = frozen_versions()[agent]
    try:
        v, err = declared_version(agent), ""
    except Exception as e:                     # an unread version is not the frozen one
        v, err = None, f" ({type(e).__name__}: {e})"[:300]
    with st.lock:
        b["declared_version"] = v
        b["declared_read_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        if v != frozen:
            b["stopped"] = f"version guard: {agent} default version {v}, frozen {frozen}{err}"
            st.guard.halt(f"{name} {b['stopped']}")
        st.save()
    if v != frozen:
        print(name, "STOPPED:", b["stopped"], flush=True)
    return v == frozen


def frozen_specs(path: Path = CAMPAIGN_MD) -> dict[str, Path]:
    """Agent name to its frozen spec file (the table's last column)."""
    out = {}
    for cells in frozen_rows(path):
        f = re.search(r"`([^`]+\.yaml)`", cells[3]) if len(cells) > 3 else None
        if f:
            out[cells[1]] = ROOT / f.group(1)
    return out


# ------------------------------------------------------------------------------------------------ skill pre-check (D066)

def skill_sources() -> dict[str, list[tuple[str, str]]]:
    """Agent name to its STAGE skills (name, stage path), read from the frozen spec files."""
    out: dict[str, list[tuple[str, str]]] = {}
    for agent, spec in frozen_specs().items():
        for sk in yaml.safe_load(spec.read_text()).get("skills") or []:
            src = sk.get("source") or {}
            if str(src.get("type", "")).upper() == "STAGE":
                out.setdefault(agent, []).append((sk["name"], src["path"].rstrip("/")))
    return out


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def skill_precheck(cur=None) -> dict:
    """Before a stage: as LINKML_SVC (USE SECONDARY ROLES NONE, the identity the sandbox mounts the stage with, session
    8c-1 finding 55), LIST each skill path of the frozen specs; a repository file missing or 0 B, or a staged file with
    no repository counterpart, fails without a GET. Then GET the folder into a temporary directory, compare each file's
    sha256 with snowflake/phase4_others/skill/<name>/, and delete the copies. LIST sizes and md5 are recorded, never
    compared (encrypted sizes, rounded up to 16 bytes)."""
    con = None
    if cur is None:
        import snowflake.connector
        con = snowflake.connector.connect(connection_name="linkml_svc")
        cur = con.cursor()
    res: dict = {"at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "ok": False, "caller": None, "skills": {},
                 "problems": []}
    bad = res["problems"]
    try:
        cur.execute("USE SECONDARY ROLES NONE")
        res["caller"] = [str(x) for x in cur.execute(
            "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone()]
        if res["caller"][0] != "LINKML_SVC":
            bad.append(f"caller {res['caller'][0]}, not LINKML_SVC")
        for agent, skills in skill_sources().items():
            for name, path in skills:
                key, sub = f"{agent} {name}", path.split("/", 1)[1]
                want = {p.name: p.read_bytes() for p in (SKILLS_REPO / name).iterdir()
                        if p.is_file() and not p.name.startswith(".")}
                listed = {}
                for r in cur.execute(f"LIST {path}/").fetchall():
                    rel = str(r[0]).split("/", 1)[1]
                    listed[rel[len(sub) + 1:] if rel.startswith(sub + "/") else rel] = int(r[1])
                rec = {"path": path, "listed": listed, "files": []}
                res["skills"][key] = rec
                here = [f"{key}: missing on the stage: {n}" for n in sorted(want) if n not in listed]
                here += [f"{key}: 0 B on the stage: {n}" for n in sorted(want) if listed.get(n) == 0]
                here += [f"{key}: no repository file: {n}" for n in sorted(set(listed) - set(want))]
                if here:
                    bad += here
                    continue
                with tempfile.TemporaryDirectory(prefix="skill_precheck_") as tmp:
                    cur.execute(f"GET {path}/ 'file://{tmp}/'")
                    got = {p.name: p for p in Path(tmp).rglob("*") if p.is_file()}
                    for n in sorted(want):
                        b = got[n].read_bytes() if n in got else None
                        f = {"name": n, "list_size": listed[n], "size": None if b is None else len(b),
                             "sha256": None if b is None else sha256(b), "repo_sha256": sha256(want[n])}
                        f["equal"] = f["sha256"] == f["repo_sha256"]
                        rec["files"].append(f)
                        if b is None:
                            bad.append(f"{key}: not read back by GET: {n}")
                        elif not f["equal"]:
                            bad.append(f"{key}: sha256 differs: {n}")
    except Exception as e:                     # an unread stage is not a checked one
        bad.append(f"{type(e).__name__}: {e}"[:300])
    finally:
        if con is not None:
            con.close()
    res["ok"] = not bad
    return res


def served_version(rows: list[dict]) -> str | list[str] | None:
    """The version name the trace rows of one turn carry; a list if they carry several."""
    names = set()
    for r in rows:
        a = r.get("RECORD_ATTRIBUTES")
        a = json.loads(a) if isinstance(a, str) else (a or {})
        if a.get(VERSION_ATTR):
            names.add(a[VERSION_ATTR])
    names = sorted(names)
    return None if not names else names[0] if len(names) == 1 else names


# ------------------------------------------------------------------------------------------------ run

class State:
    def __init__(self, stage: int):
        self.path = RUN / f"state_{STAGE_TAG[stage]}.json"
        self.lock = threading.Lock()
        self.d = json.loads(self.path.read_text()) if self.path.exists() else {
            "stage": STAGE_TAG[stage], "turns": {}, "blocks": {}, "guard": {"stage": STAGE_TAG[stage]}}
        self.guard = guards.CampaignGuard.load(self.d["guard"])

    def save(self) -> None:
        self.d["guard"] = self.guard.state()
        self.path.write_text(json.dumps(self.d, indent=1))


def run_turn(cfg: str, qid: str, rep: int, stage: int, block: dict, st: State) -> tuple[dict | None, int, bool]:
    key = f"{cfg}|{qid}|{rep}"
    with st.lock:
        rec = st.d["turns"].setdefault(key, {"attempts": []})
    attempt = len(rec["attempts"]) + 1
    lab = label(cfg, qid, stage, rep, attempt)
    agent, policy, extra, _ = config(cfg)
    thread = []
    if qid == "BULK_SCOPE":
        thread = ["--save-thread", str(RUN / f"thread_{cfg}_{STAGE_TAG[stage]}_r{rep}.json")]
    if qid == "BULK_SCOPE_DRILL":
        thread = ["--thread", str(RUN / f"thread_{cfg}_{STAGE_TAG[stage]}_r{rep}.json")]
    text = WARMUP if qid == "WARMUP" else next(q["question"] for q in QUESTIONS if q["id"] == qid)
    ceiling = guards.token_ceilings()[twin(cfg)]
    if qid in THREAD_PARENT:                   # owner, session 9a: the parent's exchange rides on the follow-up's calls
        with st.lock:
            p = st.d["turns"].get(f"{cfg}|{THREAD_PARENT[qid]}|{rep}", {}).get("done")
        if p and summary_path(p).exists():
            ceiling = guards.thread_token_ceiling(twin(cfg), json.loads(summary_path(p).read_text())["tokens"]["max_call_input"])
    subprocess.run([sys.executable, str(ROOT / "snowflake/phase4_others/agents.py"), "warm"], check=True,
                   capture_output=True)
    r = subprocess.run([sys.executable, str(ROOT / "snowflake/probe_b/mount/run_call.py"), "--agent", agent,
                        "--question", text, "--label", lab, "--budget", "campaign",
                        "--block", f"{STAGE_TAG[stage]}_{cfg}", "--block-cap", str(block["cap"]),
                        "--turn-cap", str(guards.turn_cap(twin(cfg))), "--turn-usd-cap", str(guards.RUNAWAY_TURN_USD),
                        "--no-trace", "--policy", policy, "--log-dir", str(RUN)] + extra + thread,
                       capture_output=True, text=True)
    tag = lab.lower().replace("-", "_")
    f = RUN / f"summary_{tag}.json"
    summary = json.loads(f.read_text()) if f.exists() else None
    rest_calls = len(summary["calls"]) if summary else 1
    ok = guards.call_ok(summary) and r.returncode == 0
    tokens = (summary or {}).get("tokens") or {}
    usd = guards.turn_usd(tokens) if tokens else 0.0
    runaway = r.returncode == 4 or usd > guards.RUNAWAY_TURN_USD
    with st.lock:
        rec["attempts"].append({"label": lab, "ok": ok, "exit": r.returncode, "turn_usd": round(usd, 4),
                                "token_ceiling": ceiling,       # recorded, no stop (session 9a)
                                "above_token_ceiling": (tokens.get("max_call_input") or 0) > ceiling if tokens else None,
                                "stopped": (summary or {}).get("stopped"), "stderr": r.stderr[-300:] if not ok else ""})
        if ok:
            rec["done"] = lab
        if summary:
            st.guard.add_turn(summary.get("tokens") or {})
        st.save()
    return summary, rest_calls, runaway


def run_block(block: dict, stage: int, st: State) -> None:
    cfg = block["config"]
    name = f"{STAGE_TAG[stage]}_{cfg}"
    with st.lock:
        b = st.d["blocks"].setdefault(name, {"window_utc": [None, None], "stopped": None, "used": 0})
    if b["stopped"]:
        print(name, "stopped earlier:", b["stopped"], flush=True)
        return
    if st.guard.check() or not check_declared(cfg, name, b, st):
        return
    g = guards.BlockGuard(cfg, block["cap"], used=b["used"])
    with st.lock:
        st.guard.block_begin(dt.datetime.now(dt.timezone.utc))     # the warehouse term counts this block's window
        st.save()
    try:
        _block_turns(block, stage, st, cfg, name, b, g)
    finally:
        with st.lock:
            st.guard.block_end(dt.datetime.now(dt.timezone.utc))
            st.save()


def _block_turns(block: dict, stage: int, st: State, cfg: str, name: str, b: dict, g: "guards.BlockGuard") -> None:
    todo = [t for t in block["turns"] if not st.d["turns"].get(f"{cfg}|{t['qid']}|{t['rep']}", {}).get("done")]
    last_end = b["window_utc"][1]
    if (todo and st.d["turns"].get(f"{cfg}|WARMUP|1", {}).get("done") and last_end and
            (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(last_end)).total_seconds() > REWARM_AFTER_S):
        todo = [{"qid": "WARMUP", "rep": 1}] + todo           # a resumed block on a cold cache: a new warm-up attempt
    for i, t in enumerate(todo):
        if st.guard.check() or not g.room():
            break
        start = dt.datetime.now(dt.timezone.utc).isoformat()
        summary, n, runaway = run_turn(cfg, t["qid"], t["rep"], stage, block, st)
        g.record(summary, n, runaway=runaway, last=i == len(todo) - 1)  # a cap reached by the last turn is no stop
        with st.lock:
            b["window_utc"][0] = b["window_utc"][0] or start
            b["window_utc"][1] = dt.datetime.now(dt.timezone.utc).isoformat()
            b["used"] = g.used
            st.guard.block_touch(dt.datetime.now(dt.timezone.utc))
            if g.stopped:
                b["stopped"] = g.stopped
                st.guard.block_stopped(name)
            st.save()
        print(name, t["qid"], f"r{t['rep']}", "ok" if guards.call_ok(summary) else "FAILED",
              f"calls {g.used}/{g.cap}", f"est {st.guard.spent_usd():.2f} USD", flush=True)
        if g.stopped:
            print(name, "STOPPED:", g.stopped, flush=True)
            return


def run(stage: int, cut: int, streams: int, only: str | None, ceiling: float | None = None,
        resume_paused: bool = False, reduced: bool = False) -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    st = State(stage)
    check_plan(st, f"arm-{ARM}" if ARM else "reduced" if reduced else "gate")
    if resume_paused:                          # the owner's decision after a pause, with a new ceiling
        if ceiling is None:
            raise SystemExit("--resume-paused needs --ceiling-usd")
        st.guard.resume(ceiling)
    elif ceiling is not None and st.guard.ceiling is None:
        st.guard.ceiling = ceiling             # stage 2: the ceiling set at the cost read
    st.guard.ceiling_usd                       # refuses a stage with no ceiling
    if st.guard.check():
        print("stage held:", st.guard.check(), flush=True)
        return
    pre = skill_precheck()                     # D066: before the stage's first call, every run (resume included)
    st.d.setdefault("skill_checks", []).append(pre)
    if not pre["ok"]:
        st.guard.halt(f"skill pre-check: {'; '.join(pre['problems'])}"[:500])
        st.save()
        print("stage held: skill pre-check failed:", pre["problems"], flush=True)
        return
    print("skill pre-check passed:", {k: [(f["name"], f["sha256"][:16]) for f in v["files"]]
                                      for k, v in pre.get("skills", {}).items()}, flush=True)
    st.guard.start(dt.datetime.now(dt.timezone.utc))
    st.save()
    blocks = [b for b in (arm_plan(stage) if ARM else plan(stage, cut, reduced=True) if reduced else plan(stage, cut))
              if not only or b["config"] == only]
    with ThreadPoolExecutor(max_workers=streams) as ex:
        for f in [ex.submit(run_block, b, stage, st) for b in blocks]:
            f.result()
    held = st.guard.check()
    st.save()
    print("stage held:" if held else "stage ended:", held or "", flush=True)


# ------------------------------------------------------------------------------------------------ after the stage

def done_labels(stage: int) -> dict[str, tuple[str, str]]:
    st = State(stage)
    out = {}
    for key, rec in st.d["turns"].items():
        cfg, qid, _ = key.split("|")
        if rec.get("done") and qid != "WARMUP":
            out[rec["done"]] = (cfg, qid)
    return out


def load_grader():
    spec = importlib.util.spec_from_file_location("grade", ROOT / "eval" / "grade.py")
    g = importlib.util.module_from_spec(spec)
    sys.modules["grade"] = g
    spec.loader.exec_module(g)
    return g


def grades_file(stage: int, rubric: str) -> Path:
    """The grades of a stage under a rubric. Rubric 3.2, under which both stages were run and graded, keeps the file of
    record; any other version writes its own beside it (session 9c), so both scores can be reported."""
    tag = STAGE_TAG[stage]
    return RUN / (f"grades_{tag}.json" if rubric == "3.2" else f"grades_{tag}.rubric-{rubric}.json")


def grade(stage: int, rubric: str | None = None) -> None:
    g = load_grader()
    rubric = rubric or g.RUBRIC["version"]
    sv = {"b2_semantic_view", "b1_semantic_view", "a_semantic_view", "c_raw_semantic_view"}
    labels = done_labels(stage)
    out = []
    for lab, t in zip(labels, g.turns_from_log(RUN, labels)):
        res = g.grade_turn(t, sv, ("DIM_ITEM", "B2_ITEM"), rubric=rubric)
        out.append({**res, "label": lab, "answer": t["answer"], "tables": t["tables"]})
    f = grades_file(stage, rubric)
    f.write_text(json.dumps(out, indent=1, default=str))
    print(len(out), f"turns graded, rubric {rubric}, {f.name}:",
          {v: sum(x["verdict"] == v for x in out) for v in ("correct", "wrong", "manual")})
    for cfg, s in g.scores(out).items():          # owner, 2026-10-07: the figure-only score beside the primary
        print(f"  {cfg}: primary {s['primary']}, figure only {s['figure_only']}")


def summary_path(lab: str) -> Path:
    return RUN / f"summary_{lab.lower().replace('-', '_')}.json"


def utc_naive(x) -> dt.datetime:
    """A timestamp as naive UTC: an ISO string of the client (with its offset) or a trace TIMESTAMP (UTC, no offset)."""
    t = x if isinstance(x, dt.datetime) else dt.datetime.fromisoformat(str(x))
    return t.astimezone(dt.timezone.utc).replace(tzinfo=None) if t.tzinfo else t


def row_time(r: dict) -> dt.datetime | None:
    """A trace row's start, or its end when it has no start (the CORTEX_AGENT_REQUEST row)."""
    t = r.get("START_TIMESTAMP") or r.get("TIMESTAMP")
    return utc_naive(t) if t else None


def record_id(r: dict) -> str | None:
    a = r.get("RECORD_ATTRIBUTES")
    a = json.loads(a) if isinstance(a, str) else (a or {})
    return a.get(RECORD_ID_ATTR)


def own_rows(rows: list[dict], ids, known: set, window: list[str], margin: float = 2.0) -> tuple[list, list]:
    """D065: a turn's rows are those whose record id is one of its calls' request ids (a failed call without an id
    selects nothing). Foreign rows: inside the turn's window (2 s margin) with a record id the harness never received
    (known: every request id of the agent's turns in the stage, warm-ups and failed attempts included), such as a
    concurrent Snowsight request. Never the thread id, never a bare numeric value."""
    ids = {i for i in ids if isinstance(i, str) and i}
    a = utc_naive(window[0]) - dt.timedelta(seconds=margin)
    b = utc_naive(window[1]) + dt.timedelta(seconds=margin)
    kept, foreign = [], []
    for r in rows:
        rid = record_id(r)
        if rid in ids:
            kept.append(r)
        elif rid not in known and (t := row_time(r)) is not None and a <= t <= b:
            foreign.append(r)
    return kept, foreign


def request_ids(summary: dict) -> list[str]:
    return [c.get("request_id") for c in summary.get("calls") or [] if c.get("request_id")]


def harness_ids(st: State, cfg: str) -> set[str]:
    """Every request id the harness received for one configuration in the stage: all attempts, warm-up included."""
    out = set()
    for key, rec in st.d["turns"].items():
        if key.split("|")[0] == cfg:
            for att in rec.get("attempts", []):
                f = summary_path(att["label"])
                if f.exists():
                    out |= set(request_ids(json.loads(f.read_text())))
    return out


READ_AFTER_S = 300      # the read's upper bound: the last turn's end plus 5 minutes (trace times are event times)


def traces(stage: int, cur=None) -> dict:
    """After the stage (decision 4): one GET_AI_OBSERVABILITY_EVENTS read per agent, bounded by the stage's window (first
    turn's start less 5 s, last turn's end plus 5 minutes), as LINKML_SVC. D065: each turn keeps the rows whose record id
    is one of its request ids (trace_<label>.json), counts the foreign rows in its window, and lists the request ids
    with no row. Each turn's summary gets the version name of its own rows (served_version), their count (trace_rows),
    the foreign rows (trace_foreign_rows, trace_foreign_ids) and trace_ids_without_rows; then the version check."""
    if cur is None:
        import snowflake.connector
        cur = snowflake.connector.connect(connection_name="linkml_svc").cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    st = State(stage)
    labels = done_labels(stage)
    for cfg, (agent, *_rest) in ({ARM: config(ARM)} if ARM else CONFIGS).items():
        mine = {lab: json.loads(summary_path(lab).read_text()) for lab, (c, _) in labels.items() if c == cfg}
        if not mine:
            continue
        known = harness_ids(st, cfg) | {i for s in mine.values() for i in request_ids(s)}
        lo = min(s["window_utc"][0] for s in mine.values())
        hi = max(s["window_utc"][1] for s in mine.values())
        rows = cur.execute(
            "SELECT * FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS('LINKML_METRICS', 'RAW', %s, 'CORTEX AGENT')) "
            "WHERE TIMESTAMP >= DATEADD('second', -5, %s::TIMESTAMP_TZ)::TIMESTAMP_NTZ "
            f"AND TIMESTAMP <= DATEADD('second', {READ_AFTER_S}, %s::TIMESTAMP_TZ)::TIMESTAMP_NTZ",
            (agent, lo, hi)).fetchall()
        cols = [d[0] for d in cur.description]
        a_, b_ = utc_naive(lo) - dt.timedelta(seconds=5), utc_naive(hi) + dt.timedelta(seconds=READ_AFTER_S)
        recs = [r for r in (dict(zip(cols, x)) for x in rows)
                if r.get("TIMESTAMP") and a_ <= utc_naive(r["TIMESTAMP"]) <= b_]      # the same bound, client side
        n_foreign = 0
        for lab, s in mine.items():
            ids = request_ids(s)
            kept, foreign = own_rows(recs, ids, known, s["window_utc"])
            (RUN / f"trace_{lab.lower().replace('-', '_')}.json").write_text(json.dumps(kept, default=str))
            have = {record_id(r) for r in kept}
            s.update(trace_rows=len(kept), served_version=served_version(kept), trace_foreign_rows=len(foreign),
                     trace_foreign_ids=sorted({record_id(r) or "" for r in foreign}),
                     trace_ids_without_rows=[i for i in ids if i not in have])
            summary_path(lab).write_text(json.dumps(s, indent=2, default=str))
            n_foreign += len(foreign)
        print(cfg, len(recs), "trace rows read for", len(mine), "turns;", n_foreign, "foreign rows in their windows")
    return version_check(stage)


def version_check(stage: int) -> dict:
    """Every completed turn of the stage: served version equal to the frozen one, another one (a harness event for the
    owner, never regraded silently), or none (no trace row, or rows without a version name). No call."""
    frozen = frozen_versions()
    out: dict = {"equal": [], "differ": [], "no_trace": [], "no_version": [], "foreign": []}
    for lab, (cfg, _) in sorted(done_labels(stage).items()):
        s = json.loads(summary_path(lab).read_text())
        want, got = frozen[config(cfg)[0]], s.get("served_version")
        if got == want:
            out["equal"].append(lab)
        elif not s.get("trace_rows"):
            out["no_trace"].append(lab)
        elif got is None:
            out["no_version"].append(lab)
        else:
            out["differ"].append({"label": lab, "served": got, "frozen": want})
        if s.get("trace_foreign_rows"):
            out["foreign"].append({"label": lab, "rows": s["trace_foreign_rows"], "request_ids": s["trace_foreign_ids"]})
    (RUN / f"versions_{STAGE_TAG[stage]}.json").write_text(json.dumps(out, indent=1))
    print(f"served version, {STAGE_TAG[stage]}: {len(out['equal'])} turns equal to the frozen state, "
          f"{len(out['differ'])} differ, {len(out['no_trace'])} with no trace, {len(out['no_version'])} with no version")
    for d in out["differ"]:
        print("  harness event, served", d["served"], "frozen", d["frozen"], ":", d["label"])
    for k in ("no_trace", "no_version"):
        for lab in out[k]:
            print(f"  {k.replace('_', ' ')}:", lab)
    for f in out["foreign"]:
        print(f"  foreign rows in the window (not kept): {f['rows']} of {f['request_ids']}:", f["label"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "run", "grade", "traces", "versions"])
    ap.add_argument("--stage", type=int, choices=[1, 2], required=True)
    ap.add_argument("--cut", type=int, choices=sorted(CUTS), default=0)
    ap.add_argument("--streams", type=int, default=1, help="configurations run in parallel (default 1; owner's go to change)")
    ap.add_argument("--only")
    ap.add_argument("--ceiling-usd", type=float, help="stage 2: the ceiling set at the cost read; with --resume-paused, "
                    "the new ceiling the owner decided")
    ap.add_argument("--resume-paused", action="store_true", help="resume a paused stage (owner's decision)")
    ap.add_argument("--rubric", help="grade: the rubric version (default the current one, eval/rubric.yaml)")
    ap.add_argument("--plan", choices=["gate", "reduced"], default="gate",
                    help="stage 2: gate (eval/stage2.yaml) or reduced (eval/stage2_reduced.yaml, owner, session 9b)")
    ap.add_argument("--arm", choices=sorted(ARMS), help="session 13: play an arm beside the campaign (CR: C-raw)")
    a = ap.parse_args()
    if a.arm:
        use_arm(a.arm)
    reduced = a.plan == "reduced"
    if reduced and a.stage != 2:
        raise SystemExit("--plan reduced is a stage 2 plan")
    if a.cmd == "plan" and a.arm:
        for b in arm_plan(a.stage):
            print(f"arm {b['config']}, {STAGE_TAG[a.stage]}, cap {b['cap']}, twin {ARMS[a.arm]['as']}:")
            for t in b["turns"]:
                print(f"  r{t['rep']} {t['qid']}")
    elif a.cmd == "plan":
        blocks = plan(a.stage, a.cut, reduced)
        print(json.dumps(counts(blocks), indent=1))
        print("configuration order:", [b["config"] for b in blocks])
        if reduced:
            groups = route_groups(blocks)
            for b in blocks:
                print(f"block {b['config']} (cap {b['cap']}):")
                for t in b["turns"]:
                    print(f"  r{t['rep']} {t['qid']}" + (f"  [{groups[t['qid']]}]" if t["qid"] != "WARMUP" else ""))
            _c = importlib.util.spec_from_file_location("cost_model", ROOT / "eval" / "cost_model.py")
            cm = importlib.util.module_from_spec(_c)
            _c.loader.exec_module(cm)
            print(json.dumps(cm.reduced_stage2(blocks), indent=1))
        else:
            print("first block:", [(t["qid"], t["rep"]) for t in blocks[0]["turns"]][:30] if blocks else [])
    elif a.cmd == "run":
        run(a.stage, a.cut, a.streams, a.only, a.ceiling_usd, a.resume_paused, reduced)
    elif a.cmd == "grade":
        grade(a.stage, a.rubric)
    elif a.cmd == "traces":
        traces(a.stage)
    else:
        version_check(a.stage)


if __name__ == "__main__":
    main()
