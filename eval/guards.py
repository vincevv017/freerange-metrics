"""
Harness guards of the campaign (session 8c, step 1b). No Snowflake call: everything here reads recorded summaries.

- Runaway guard (owner, session 9a), the same for the six configurations: a turn whose estimated cost (AI Credits at
  the rates below, turn_usd) exceeds 2 USD is stopped (run_call.py --turn-usd-cap, checked after each REST call, exit
  code 4) and so is its block. It replaces the per-call token guard as a stop condition: for D and D', one REST call
  sums every internal planning step, so that guard measured the agent's behaviour (its number of steps), and a
  behaviour never stops a block; it also cut the measurement of the costliest configuration.
- Token ceiling per configuration, recorded only (no stop since session 9a): 1.5 times the largest orchestration input
  of one REST call over the smokes of sessions 8, 8b and 8c-0 (eval/fixtures/smoke_tokens.jsonl). A turn that
  continues a thread (--thread: BULK_SCOPE_DRILL) carries its parent's exchange, which no smoke had: its ceiling is the
  configuration's plus the parent turn's largest call. Each attempt records its ceiling and whether a call went above.
- Call caps (stage 1: 30 per block, 100 for D'; owner, session 9a): per block, every REST call counted, approval and client-side resumes included (run_call.py --block,
  --block-cap); per question, at most 3 REST calls, 4 for D' (--turn-cap; D064, owner, session 9a: a D' turn whose first
  script command the dp policy denies needs a fourth call, session 8c-1 finding 62).
- Errors: 3 consecutive failed calls (non-200, timeout, no summary) stop the block; 2 stopped blocks stop the campaign.
- Version (pre-stage-1 fix): a block whose agent's default version is not the frozen one holds the stage (halt(),
  eval/campaign.py); it does not lift on resume.
- Cost: a running estimate in USD, AI Credits from each turn's REST usage tokens and the measured credits per token,
  plus the warehouse: the sum of the UTC windows of the blocks already played plus the current block since its start
  (owner, session 9a; a pause costs nothing), 1 credit an hour (X-Small), 3.90 USD a credit (owner, decision 2 after
  step 5). At 90 percent of the stage ceiling the stage pauses; it resumes only on the owner's
  decision (eval/campaign.py run --resume-paused --ceiling-usd <new ceiling>). Stage 1: 40 USD, so 36 USD. Stage 2:
  set at the cost read between the stages (--ceiling-usd, required).

Credits per token [measured, CORTEX_AGENT_USAGE_HISTORY, sessions 3 and 5, claude-sonnet-5-5]:
cache write 0.1074 credit for 66,105 tokens (snowflake/probe_b/results.md, call 2): 1.625 per million;
cache read 0.0172 for about 132,300 tokens (calls 3 to 5): 0.13 per million;
output 0.0273 for 4,198 tokens (snowflake/probe_d/results.md): 6.5 per million.
Uncached input: 1.3 per million [inferred: the cache write is 1.25 times it, the cache read a tenth; a few tokens a turn].
"""

from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "eval" / "fixtures" / "smoke_tokens.jsonl"

RATES = {"cache_write": 1.625e-6, "cache_read": 0.13e-6, "uncached": 1.3e-6, "output": 6.5e-6}   # credits per token
USD_PER_AI_CREDIT = 2.00          # decision 3: AI Credits (Cortex Agents tokens), global routing
USD_PER_PLATFORM_CREDIT = 3.90    # decision 3: warehouse and attached SQL, on-demand Enterprise, AWS EU Paris
STAGE_CEILING_USD = {"campaign-s1": 40.0, "drill": 8.0}     # campaign-s2: set at the cost read (--ceiling-usd)
WAREHOUSE_CREDITS_PER_HOUR = 1.0
STOP_SHARE = 0.90
TOKEN_FACTOR = 1.5
MAX_CONSECUTIVE_ERRORS = 3
MAX_STOPPED_BLOCKS = 2
TURN_CAP = 3
RUNAWAY_TURN_USD = 2.0            # owner, session 9a: the runaway guard, per turn, every configuration
TURN_CAP_BY_CONFIG = {"DP": 4}    # D064 (owner, session 9a), both stages


def turn_cap(config: str) -> int:
    return TURN_CAP_BY_CONFIG.get(config, TURN_CAP)


def smoke_calls(path: Path = SMOKE) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def max_call_input(calls: list[dict] | None = None) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in calls if calls is not None else smoke_calls():
        if c["status"] == 200 and c.get("input"):
            out[c["config"]] = max(out.get(c["config"], 0), c["input"])
    return out


def token_ceilings(calls: list[dict] | None = None) -> dict[str, int]:
    return {k: math.floor(v * TOKEN_FACTOR) for k, v in max_call_input(calls).items()}


def thread_token_ceiling(config: str, parent_max_call_input: int) -> int:
    """A follow-up turn's ceiling: the configuration's plus the largest call of the parent turn (owner, session 9a)."""
    return token_ceilings()[config] + int(parent_max_call_input)


def turn_usd(tokens: dict) -> float:
    """A turn's estimated cost in USD: its AI Credits at the rates above, 2.00 USD a credit."""
    return credits(tokens) * USD_PER_AI_CREDIT


def runaway(tokens: dict, cap: float = RUNAWAY_TURN_USD) -> bool:
    return turn_usd(tokens) > cap


def credits(tokens: dict) -> float:
    """AI Credits of a call or a turn from its orchestration tokens (run_call.call_tokens or turn_tokens). Uncached input
    is what the total leaves after the cache write and the cache read."""
    w, r = tokens.get("cache_write") or 0, tokens.get("cache_read") or 0
    unc = max((tokens.get("input") or 0) - w - r, 0)
    return w * RATES["cache_write"] + r * RATES["cache_read"] + unc * RATES["uncached"] + (tokens.get("output") or 0) * RATES["output"]


def call_ok(summary: dict | None) -> bool:
    """A turn is an error when it left no summary, or any of its REST calls was not a 200."""
    return bool(summary) and bool(summary.get("calls")) and all(c.get("status") == 200 for c in summary["calls"])


@dataclass
class BlockGuard:
    """One block: one configuration's calls of one stage. Stops on the call cap, on the runaway guard, or on 3
    consecutive errors. A cap reached after the block's last turn is not a stop: no turn was prevented (owner,
    session 9a)."""
    config: str
    cap: int
    used: int = 0
    errors: int = 0
    stopped: str | None = None

    def record(self, summary: dict | None, rest_calls: int, runaway: bool = False, last: bool = False) -> None:
        self.used += rest_calls
        self.errors = 0 if call_ok(summary) else self.errors + 1
        if runaway:
            self.stopped = f"runaway guard: a turn's cost estimate above {RUNAWAY_TURN_USD:.0f} USD"
        elif self.errors >= MAX_CONSECUTIVE_ERRORS:
            self.stopped = f"{MAX_CONSECUTIVE_ERRORS} consecutive errors"
        elif self.used >= self.cap and not last:
            self.stopped = f"block cap {self.cap} reached"

    def room(self, need: int = 1) -> bool:
        return self.stopped is None and self.used + need <= self.cap


@dataclass
class CampaignGuard:
    """One stage: stops after 2 stopped blocks; pauses at 90 percent of the stage ceiling in USD (AI Credits estimate
    plus the warehouse hours elapsed since the stage started). A pause holds until the owner resumes with a new
    ceiling (resume())."""
    stage: str
    spent_credits: float = 0.0
    stopped_blocks: list[str] = field(default_factory=list)
    started_utc: str | None = None
    ceiling: float | None = None
    paused: str | None = None
    resumes: list[dict] = field(default_factory=list)
    halted: str | None = None         # a harness guard (the served version), never resumed: the owner decides
    segments: list = field(default_factory=list)   # [start, end] UTC of each block run: the warehouse term
    lifted_stops: list = field(default_factory=list)   # stops the owner lifted, with their reasons (session 9a)
    running: bool = field(default=False, compare=False)   # a block runs in this process (never persisted); one
    # warehouse, one block at a time (--streams 1): with parallel blocks the segments would overlap

    @property
    def ceiling_usd(self) -> float:
        if self.ceiling is not None:
            return self.ceiling
        if self.stage not in STAGE_CEILING_USD:
            raise SystemExit(f"stage {self.stage}: no ceiling; give --ceiling-usd (set at the cost read)")
        return STAGE_CEILING_USD[self.stage]

    def start(self, now: dt.datetime) -> None:
        self.started_utc = self.started_utc or now.isoformat()

    def add_turn(self, tokens: dict) -> None:
        self.spent_credits += credits(tokens)

    def block_stopped(self, name: str) -> None:
        self.stopped_blocks.append(name)

    def lift(self, block: str, reason: str, why: str) -> None:
        """The owner lifts a block's stop: it leaves the stopped blocks; the reason and the decision are kept."""
        self.stopped_blocks = [b for b in self.stopped_blocks if b != block]
        self.lifted_stops.append({"block": block, "reason": reason, "lifted": why})

    def halt(self, reason: str) -> None:
        self.halted = self.halted or reason

    def block_begin(self, now: dt.datetime) -> None:
        self.segments.append([now.isoformat(), now.isoformat()])
        self.running = True

    def block_touch(self, now: dt.datetime) -> None:
        if self.segments:
            self.segments[-1][1] = now.isoformat()

    def block_end(self, now: dt.datetime) -> None:
        self.block_touch(now)
        self.running = False

    def warehouse_hours(self, now: dt.datetime | None = None) -> float:
        """The blocks' UTC windows, the current block until now. A segment left by a stopped process ends at its last
        turn: the time until a resume is not counted."""
        now = now or dt.datetime.now(dt.timezone.utc)
        out = 0.0
        for i, (a, b) in enumerate(self.segments):
            end = now if self.running and i == len(self.segments) - 1 else dt.datetime.fromisoformat(b)
            out += max((end - dt.datetime.fromisoformat(a)).total_seconds(), 0) / 3600
        return out

    def warehouse_usd(self, now: dt.datetime | None = None) -> float:
        return self.warehouse_hours(now) * WAREHOUSE_CREDITS_PER_HOUR * USD_PER_PLATFORM_CREDIT

    def spent_usd(self, now: dt.datetime | None = None) -> float:
        return self.spent_credits * USD_PER_AI_CREDIT + self.warehouse_usd(now)

    def check(self, now: dt.datetime | None = None) -> str | None:
        """Stopped or paused; sets the pause when the estimate reaches 90 percent of the ceiling."""
        if self.halted:
            return self.halted
        if len(self.stopped_blocks) >= MAX_STOPPED_BLOCKS:
            return f"{MAX_STOPPED_BLOCKS} stopped blocks: {self.stopped_blocks}"
        if self.paused:
            return self.paused
        usd = self.spent_usd(now)
        if usd >= STOP_SHARE * self.ceiling_usd:
            self.paused = (f"paused: cost estimate {usd:.2f} USD at or above 90 percent of the {self.ceiling_usd:.0f} "
                           f"USD ceiling; resumes on the owner's decision")
            return self.paused
        return None

    def resume(self, new_ceiling: float, now: dt.datetime | None = None) -> None:
        if not self.paused:
            raise SystemExit("the stage is not paused")
        if new_ceiling <= self.ceiling_usd:
            raise SystemExit(f"a resume needs a ceiling above {self.ceiling_usd:.0f} USD")
        now = now or dt.datetime.now(dt.timezone.utc)
        self.resumes.append({"at": now.isoformat(), "from": self.ceiling_usd, "to": new_ceiling,
                             "spent_usd": round(self.spent_usd(now), 2)})
        self.ceiling, self.paused = new_ceiling, None

    def state(self) -> dict:
        return {"stage": self.stage, "spent_credits": self.spent_credits, "stopped_blocks": self.stopped_blocks,
                "started_utc": self.started_utc, "ceiling": self.ceiling, "paused": self.paused,
                "resumes": self.resumes, "halted": self.halted, "segments": self.segments,
                "lifted_stops": self.lifted_stops}

    @classmethod
    def load(cls, d: dict) -> "CampaignGuard":
        return cls(d["stage"], d.get("spent_credits", 0.0), list(d.get("stopped_blocks", [])), d.get("started_utc"),
                   d.get("ceiling"), d.get("paused"), list(d.get("resumes", [])), d.get("halted"),
                   [list(x) for x in d.get("segments", [])], list(d.get("lifted_stops", [])))


if __name__ == "__main__":
    print(json.dumps({"max_call_input": max_call_input(), "token_ceilings": token_ceilings()}, indent=1))
