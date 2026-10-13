"""Session 8c, step 1b: the harness guards, tested on recorded summaries, no call.

eval/fixtures/smoke_tokens.jsonl holds the orchestration tokens of every REST call of the smokes of sessions 8, 8b and
8c-0 (extracted from the run folders' summaries; C's DIM_MIX of step 6, whose log was overwritten, from
snowflake/phase4_basis/results.md).
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "snowflake" / "probe_b" / "mount"))
sys.path.insert(0, str(ROOT / "snowflake" / "probe_b"))
from run_call import Budget, before_call, token_guard, turn_cost_guard  # noqa: E402

_spec = importlib.util.spec_from_file_location("guards", ROOT / "eval" / "guards.py")
guards = importlib.util.module_from_spec(_spec)
sys.modules["guards"] = guards
_spec.loader.exec_module(guards)

SMOKE = guards.smoke_calls()


def usage(c: dict) -> dict:
    """A recorded call as run_call.py summarises it (REST usage only)."""
    it = {"total": c["input"], "cache_write": c["cache_write"] or 0, "cache_read": c["cache_read"] or 0}
    return {"status": c["status"], "usage": {"tokens_consumed": [
        {"model_role": "orchestration", "input_tokens": it, "output_tokens": {"total": c["output"]}}]}}


def test_largest_smoke_call_per_configuration_recomputed_from_the_records():
    """The owner's figures were B2 256,113 (T1, 8c-0 step 8) and C 91,660 (DIM_MIX, step 6). The records hold larger
    ones: B2 292,797 (T9, session 8) and C 157,011 (CS_LAST_MONTH_GAP, 8b, through the semantic view)."""
    assert guards.max_call_input() == {"A": 188241, "B1": 176488, "B2": 292797, "C": 157011, "D": 205886,
                                       "DP": 235917}
    assert guards.token_ceilings() == {"A": 282361, "B1": 264732, "B2": 439195, "C": 235516, "D": 308829,
                                       "DP": 353875}


def test_token_guard_passes_every_recorded_call():
    ceil = guards.token_ceilings()
    assert all(token_guard(usage(c), ceil[c["config"]]) is None for c in SMOKE)


def test_token_guard_fires_above_the_ceiling():
    b2 = next(c for c in SMOKE if c["label"] == "b2_t1_s8c0_step8_r1")
    assert b2["input"] == 256113
    ceil = guards.token_ceilings()["B2"]
    big = {**b2, "input": ceil + 1}
    assert token_guard(usage(big), ceil)[0] == "token"
    assert token_guard(usage(b2), None) is None


def test_block_cap_counts_every_rest_call_and_is_fixed_at_the_first_call(tmp_path):
    b = Budget(tmp_path, "campaign_campaign-s1_DP", 100)
    for c in [c for c in SMOKE if c["config"] == "DP"][:5]:          # recorded D' calls, resumes included
        assert before_call(b, 0, 3) is None
        b.spend({"n": c["n"], "label": c["label"], "status": c["status"]})
    assert b.used == 5
    b2 = Budget(tmp_path, "campaign_campaign-s1_DP", 100)              # a resumed run reads the same count
    assert b2.used == 5
    with pytest.raises(SystemExit):
        Budget(tmp_path, "campaign_campaign-s1_DP", 110)              # a cap cannot be raised mid-block
    small = Budget(tmp_path, "campaign_campaign-s1_C", 2)
    small.spend({"n": 1})
    small.spend({"n": 2})
    assert before_call(small, 0, 3)[0] == "block_cap"


def test_turn_cap_three_calls_per_question(tmp_path):
    b = Budget(tmp_path, "campaign_campaign-s1_DP", 100)
    dp_t1 = [c for c in SMOKE if c["label"] == "dp_t1"]                # two calls: the question and its approval
    assert len(dp_t1) == 2
    assert before_call(b, len(dp_t1), 3) is None
    assert before_call(b, 3, 3)[0] == "turn_cap"


def test_turn_cap_is_four_for_dp_and_three_elsewhere(tmp_path):
    """D064 (owner, session 9a): a D' turn whose first script command is denied needs 4 REST calls (denial, client-side
    SQL, approval request, approved run; session 8c-1, finding 62). The other configurations keep 3."""
    assert guards.turn_cap("DP") == 4
    assert {c: guards.turn_cap(c) for c in ("A", "B1", "B2", "C", "D")} == dict.fromkeys(("A", "B1", "B2", "C", "D"), 3)
    b = Budget(tmp_path, "campaign_campaign-s1_DP", 100)
    assert before_call(b, 3, guards.turn_cap("DP")) is None
    assert before_call(b, 4, guards.turn_cap("DP"))[0] == "turn_cap"


def summary(status: int) -> dict:
    return {"calls": [{"status": status}]}


def test_block_stops_after_three_consecutive_errors_only():
    g = guards.BlockGuard("A", cap=26)
    for s in (summary(200), summary(500), None, summary(200), summary(429), summary(0)):
        g.record(s, 1)
        assert g.stopped is None
    g.record({"calls": [{"status": 200}, {"status": 503}]}, 2)       # one failed call in a turn is an error
    assert g.stopped == "3 consecutive errors"


def test_block_stops_on_its_cap_and_on_the_runaway_guard():
    g = guards.BlockGuard("C", cap=26)
    for c in [c for c in SMOKE if c["config"] == "C"][:12]:
        g.record({"calls": [usage(c)]}, 1)
    assert g.used == 12 and g.stopped is None and g.room(14) and not g.room(15)
    g.record(summary(200), 14)
    assert g.stopped == "block cap 26 reached"
    t = guards.BlockGuard("B2", cap=26)
    t.record(summary(200), 1, runaway=True)
    assert t.stopped.startswith("runaway guard")


def test_a_cap_reached_by_the_blocks_last_turn_is_not_a_stop():
    """Owner, session 9a: a block cap reached after the block's last turn does not count as a stopped block (no turn
    was prevented); reached with turns left, it stops the block as before."""
    g = guards.BlockGuard("C", cap=3)
    g.record(summary(200), 2)
    g.record(summary(200), 1, last=True)
    assert g.used == 3 and g.stopped is None
    h = guards.BlockGuard("C", cap=3)
    h.record(summary(200), 3)
    assert h.stopped == "block cap 3 reached"
    t = guards.BlockGuard("C", cap=30)
    t.record(summary(200), 1, runaway=True, last=True)                    # the last turn's other guards still stop
    assert t.stopped.startswith("runaway guard")


def test_credits_per_token_match_the_billed_rows():
    """probe_b call 2 (cache write 66,105, about 66,200 read): 0.1172 billed; probe_d (cache write 0.0341, read
    0.0082, output 4,198 tokens 0.0273): 0.0696 billed."""
    assert guards.credits({"input": 132320, "cache_write": 66105, "cache_read": 66030, "output": 185}) == \
        pytest.approx(0.1172, abs=0.002)
    assert guards.credits({"output": 4198}) == pytest.approx(0.0273, abs=0.0005)


def test_campaign_stops_after_two_stopped_blocks():
    g = guards.CampaignGuard("campaign-s1")
    g.block_stopped("campaign-s1_D")
    assert g.check() is None
    g.block_stopped("campaign-s1_A")
    assert g.check().startswith("2 stopped blocks")


T0 = dt.datetime(2026, 10, 6, 8, 0, tzinfo=dt.timezone.utc)


def test_stage1_pauses_at_36_usd_counting_ai_credits_and_the_warehouse():
    """Owner (decision 2 after step 5): stage 1 ceiling 40 USD, pause at 90 percent; the estimate is AI Credits at 2.00
    USD plus the warehouse at 1 credit an hour, 3.90 USD a credit, over the blocks' UTC windows (session 9a)."""
    b2 = next(c for c in SMOKE if c["label"] == "b2_t1_s8c0_step8_r1")
    g = guards.CampaignGuard("campaign-s1")
    assert g.ceiling_usd == 40.0
    g.start(T0)
    g.block_begin(T0)
    two_hours = T0 + dt.timedelta(hours=2)
    assert g.warehouse_usd(two_hours) == pytest.approx(7.80)
    n = 0
    while g.check(two_hours) is None:
        g.add_turn(b2)
        n += 1
    one = guards.credits(b2) * 2.00
    assert n == int((36.0 - 7.80) // one) + 1
    assert g.paused.startswith("paused") and g.check(two_hours) == g.paused       # held until the owner decides
    again = guards.CampaignGuard.load(json.loads(json.dumps(g.state())))
    assert again.check(two_hours) == g.paused and again.started_utc == T0.isoformat()


def test_warehouse_counts_the_block_windows_not_the_time_since_the_stage_started():
    """Owner, session 9a: the warehouse term is the sum of the UTC windows of the blocks already played, plus the
    current block since its start. A pause costs nothing: a resume 12 hours later does not add 12 hours."""
    g = guards.CampaignGuard("campaign-s1")
    g.start(T0)
    h = lambda x: T0 + dt.timedelta(hours=x)                                    # noqa: E731
    g.block_begin(h(0))
    g.block_touch(h(0.25))
    g.block_end(h(0.5))                                                         # block 1: 0.5 h
    g.block_begin(h(0.6))                                                       # the 0.1 h between blocks: not counted
    assert g.warehouse_hours(h(0.6)) == pytest.approx(0.5)
    g.block_touch(h(0.7))
    assert g.warehouse_hours(h(0.8)) == pytest.approx(0.7)                       # the current block since its start
    died = guards.CampaignGuard.load(json.loads(json.dumps(g.state())))         # the runner stopped after h(0.7)
    assert died.warehouse_hours(h(12.7)) == pytest.approx(0.6)                   # the pause costs nothing
    died.block_begin(h(12.7))                                                    # resumed 12 hours later
    assert died.warehouse_hours(h(13.2)) == pytest.approx(1.1)
    assert died.warehouse_usd(h(13.2)) == pytest.approx(1.1 * 3.90)
    assert died.started_utc == T0.isoformat() and len(died.segments) == 3


def test_a_follow_up_turn_gets_its_parents_largest_call_on_top_of_the_ceiling():
    """Owner, session 9a: the smokes had no follow-up turn, so the ceiling did not fit one. For a turn that continues a
    thread (--thread: BULK_SCOPE_DRILL), the ceiling is the configuration's plus the parent turn's largest call. The
    recorded D drill of stage 1 (00000036-0000-4000-8000-000000000036, 357,493 input tokens; parent BULK_SCOPE,
    218,689) stopped D's block under the old ceiling (308,829); under 527,518 it passes."""
    drill = {"status": 200, "input": 357493, "cache_write": 49870, "cache_read": 307607, "output": 2949}
    assert token_guard(usage(drill), guards.token_ceilings()["D"])[0] == "token"
    assert guards.thread_token_ceiling("D", 218689) == 527518
    assert token_guard(usage(drill), guards.thread_token_ceiling("D", 218689)) is None
    assert token_guard(usage({**drill, "input": 527519}), 527518)[0] == "token"


def test_a_pause_resumes_only_with_a_higher_ceiling():
    g = guards.CampaignGuard("campaign-s1", spent_credits=18.5)
    g.start(T0)
    assert g.check(T0).startswith("paused")
    with pytest.raises(SystemExit):
        g.resume(40.0, T0)
    g.resume(45.0, T0)
    assert g.check(T0) is None and g.resumes[0]["from"] == 40.0 and g.resumes[0]["to"] == 45.0


def test_stage2_has_no_ceiling_until_the_cost_read():
    g = guards.CampaignGuard("campaign-s2")
    with pytest.raises(SystemExit):
        g.ceiling_usd
    g.ceiling = 38.0
    assert g.ceiling_usd == 38.0


# ------------------------------------------------------------------------------------------------ runaway guard (9a)

DRILL_D = {"input": 357493, "cache_write": 49870, "cache_read": 307607, "output": 2949, "max_call_input": 357493,
           "calls": 1}                                   # D_BULK_SCOPE_DRILL_campaign-s1_r1, <query-id>
STOCKOUT_D = {"input": 746962, "cache_write": 73306, "cache_read": 673630, "output": 4945, "max_call_input": 746962,
              "calls": 1}                                # D_S_STOCKOUT_COUNTRY_campaign-s1_r1, <query-id>
FICTIVE = {"input": 646154, "cache_write": 646154, "cache_read": 0, "output": 0}          # 1.05 credits, 2.10 USD


def test_the_runaway_guard_is_a_turn_cost_of_2_usd_for_every_configuration():
    """Owner, session 9a: the per-call token guard is no stop condition any more (for D and D', one REST call sums every
    internal planning step, so it measured the agent's behaviour). A turn whose estimated cost (AI Credits at the rates
    of this file) exceeds 2 USD is stopped, and so is its block; the same for the six configurations."""
    assert guards.RUNAWAY_TURN_USD == 2.0
    assert guards.turn_usd(DRILL_D) == pytest.approx(0.28, abs=0.01) and not guards.runaway(DRILL_D)
    assert guards.turn_usd(STOCKOUT_D) == pytest.approx(0.48, abs=0.01) and not guards.runaway(STOCKOUT_D)
    assert guards.turn_usd(FICTIVE) == pytest.approx(2.10) and guards.runaway(FICTIVE)
    g = guards.BlockGuard("D", cap=30)
    g.record({"calls": [{"status": 200}], "tokens": STOCKOUT_D}, 1, runaway=guards.runaway(STOCKOUT_D))
    assert g.stopped is None
    g.record({"calls": [{"status": 200}], "tokens": FICTIVE}, 1, runaway=guards.runaway(FICTIVE))
    assert g.stopped.startswith("runaway guard")


def call_with(tokens: dict) -> dict:
    it = {"total": tokens["input"], "cache_write": tokens["cache_write"], "cache_read": tokens["cache_read"]}
    return {"status": 200, "usage": {"tokens_consumed": [
        {"model_role": "orchestration", "input_tokens": it, "output_tokens": {"total": tokens["output"]}}]}}


def test_run_call_stops_a_turn_once_its_running_cost_exceeds_the_cap():
    """run_call.py --turn-usd-cap: checked after each REST call on the turn's summed tokens (exit code 4)."""
    assert turn_cost_guard([call_with(STOCKOUT_D)], 2.0) is None
    assert turn_cost_guard([call_with(DRILL_D)] * 7, 2.0) is None                 # 1.97 USD
    assert turn_cost_guard([call_with(DRILL_D)] * 8, 2.0)[0] == "turn_cost"         # 2.25 USD
    assert turn_cost_guard([call_with(FICTIVE)], 2.0)[0] == "turn_cost"
    assert turn_cost_guard([call_with(FICTIVE)], None) is None


def test_a_lifted_stop_is_kept_by_the_guards_state():
    """Owner, session 9a: a stop lifted by the owner leaves the stopped blocks, and its reason stays in the state (the
    runner rewrites the guard from state() on every save; an unknown key was lost at the first resume)."""
    g = guards.CampaignGuard("campaign-s1")
    g.block_stopped("campaign-s1_D")
    g.lift("campaign-s1_D", "token guard: x", "owner: harness calibration fault")
    assert g.stopped_blocks == [] and g.check() is None
    again = guards.CampaignGuard.load(json.loads(json.dumps(g.state())))
    assert again.lifted_stops == [{"block": "campaign-s1_D", "reason": "token guard: x",
                                   "lifted": "owner: harness calibration fault"}]
