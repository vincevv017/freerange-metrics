"""Session 8c, step 1c: eval/campaign.py plans the two stages and resumes without overwriting a log. No call: the turn
runner is replaced by one that returns recorded-shape summaries."""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "snowflake" / "probe_b" / "mount"))
sys.path.insert(0, str(ROOT / "snowflake" / "probe_b"))
from run_call import LABEL  # noqa: E402

_spec = importlib.util.spec_from_file_location("campaign", ROOT / "eval" / "campaign.py")
campaign = importlib.util.module_from_spec(_spec)
sys.modules["campaign"] = campaign
_spec.loader.exec_module(campaign)


@pytest.fixture(autouse=True)
def frozen_default(monkeypatch):
    """No SHOW VERSIONS: every agent's default version is its frozen one (the version guard is in test_served_version)."""
    monkeypatch.setattr(campaign, "declared_version", lambda agent: campaign.frozen_versions()[agent])


def test_stage1_one_block_per_configuration_every_question_once():
    blocks = campaign.plan(1)
    assert sorted(b["config"] for b in blocks) == sorted(campaign.CONFIGS)
    qs = campaign.stage1_questions()
    for b in blocks:
        ids = [t["qid"] for t in b["turns"]]
        assert ids[0] == "WARMUP" and sorted(ids[1:]) == sorted(qs) and {t["rep"] for t in b["turns"]} == {1}
        assert ids.index("BULK_SCOPE_DRILL") == ids.index("BULK_SCOPE") + 1
        assert b["cap"] == (100 if b["config"] == "DP" else 30)        # D064: D' 4 x 25 turns; owner, 9a: 30
    assert len({tuple(t["qid"] for t in b["turns"]) for b in blocks}) > 1        # question order shuffled per block


def test_labels_carry_config_question_stage_and_repetition():
    for b in campaign.plan(1):
        for t in b["turns"]:
            lab = campaign.label(b["config"], t["qid"], 1, t["rep"])
            assert LABEL.match(lab) and lab.endswith("_campaign-s1_r1")
    assert campaign.label("C", "T1", 2, 7) == "C_T1_campaign-s2_r7"
    assert LABEL.match(campaign.label("C", "T1", 1, 1, attempt=2))           # a retry keeps its own log


def stage2(monkeypatch, tmp_path, held=("H1",)):
    f = tmp_path / "stage2.yaml"
    f.write_text(yaml.safe_dump({"discriminating": ["T2", "BULK_SCOPE_DRILL", "G2"], "a_passed": ["G2"],
                                 "drop_order": ["G2"]}))
    monkeypatch.setattr(campaign, "STAGE2_FILE", f)
    monkeypatch.setattr(campaign, "held_out", lambda: list(held))


def reps(blocks, cfg, qid):
    b = next((b for b in blocks if b["config"] == cfg), None)
    return sorted(t["rep"] for t in b["turns"] if t["qid"] == qid) if b else []


def test_stage2_repetitions_and_cuts(monkeypatch, tmp_path):
    """Owner (decision 3 after step 5): 5 in all for B2, C and D', 3 for B1 and D; stage 1 is repetition 1. A is not
    played in stage 2 (owner, 2026-10-06). Cuts 1 and 2 change nothing at these counts; cut 3 drops discriminating
    questions only."""
    stage2(monkeypatch, tmp_path)
    b = campaign.plan(2)
    assert reps(b, "C", "T2") == [2, 3, 4, 5] and reps(b, "C", "H1") == [1, 2, 3, 4, 5]
    assert reps(b, "DP", "T2") == [2, 3, 4, 5] and reps(b, "B2", "H1") == [1, 2, 3, 4, 5]
    assert reps(b, "B1", "T2") == [2, 3] and reps(b, "D", "H1") == [1, 2, 3]
    assert reps(b, "A", "G2") == [] and reps(b, "A", "T2") == [] and reps(b, "A", "H1") == []
    assert reps(b, "B2", "BULK_SCOPE") == [2, 3, 4, 5]                      # the drill's parent, same thread
    for blk in b:
        planned = sum(1 if t["qid"] == "WARMUP" else campaign.CONFIGS[blk["config"]][3] for t in blk["turns"])
        assert blk["cap"] == -(-planned * 1.1 // 1)
    for cut in (1, 2):
        assert campaign.plan(2, cut=cut) == b
    c3 = campaign.plan(2, cut=3)
    assert reps(c3, "C", "G2") == [] and reps(c3, "C", "H1") == [1, 2, 3, 4, 5] and reps(c3, "A", "G2") == []
    assert all(x["turns"][0]["qid"] == "WARMUP" for x in c3)


def test_a_has_no_stage2_block_at_any_cut(monkeypatch, tmp_path):
    """Owner, 2026-10-06 (session 9a): A is the stage 1 "zero effort" reference point and is not repeated in stage 2,
    whatever it passed; the other five blocks are unchanged by its removal."""
    stage2(monkeypatch, tmp_path)
    for cut in (0, 1, 2, 3):
        blocks = campaign.plan(2, cut=cut)
        assert "A" not in {b["config"] for b in blocks}
        assert sorted(b["config"] for b in blocks) == ["B1", "B2", "C", "D", "DP"]
    assert campaign.STAGE2_REPS["A"] == 1                                      # stage 1 only


def test_the_cost_model_counts_no_a_turn_in_stage2():
    spec = importlib.util.spec_from_file_location("cost_model", ROOT / "eval" / "cost_model.py")
    cm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cm)
    for d in (0, 4, 19):
        t = cm.stage2_turns(d)
        assert t["A"] == 0 and t["C"] == 4 * d + 5 * cm.HELD_OUT and t["B1"] == 2 * d + 3 * cm.HELD_OUT
        assert cm.stage2(cm.per_question(), d)["A"] == [0, 0, 0]               # no turn, no warm-up
        assert cm.trials(d)["A"] == (d, 0)                                   # stage 1 only


def fake_runner(results):
    """Replaces run_turn: pops a status per turn, records the attempt as run_turn does."""
    seen = []

    def run_turn(cfg, qid, rep, stage, block, st):
        key = f"{cfg}|{qid}|{rep}"
        rec = st.d["turns"].setdefault(key, {"attempts": []})
        lab = campaign.label(cfg, qid, stage, rep, len(rec["attempts"]) + 1)
        status = results.pop(0) if results else 200
        summary = {"calls": [{"status": status}], "tokens": {"input": 60000, "cache_read": 55000, "output": 500}}
        rec["attempts"].append({"label": lab, "ok": status == 200})
        if status == 200:
            rec["done"] = lab
        st.guard.add_turn(summary["tokens"])
        st.save()
        seen.append(lab)
        return summary, 1, False
    return run_turn, seen


def test_resume_skips_done_turns_and_retries_under_a_new_label(monkeypatch, tmp_path):
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    block = next(b for b in campaign.plan(1) if b["config"] == "C")
    block = {**block, "turns": block["turns"][:5]}
    run_turn, seen = fake_runner([200, 200, 500])
    monkeypatch.setattr(campaign, "run_turn", run_turn)
    st = campaign.State(1)
    campaign.run_block(block, 1, st)
    first = list(seen)
    assert len(first) == 5
    failed = first[2]
    seen.clear()
    st2 = campaign.State(1)                                      # resumed from the state file
    campaign.run_block(block, 1, st2)
    assert seen == [failed.replace("campaign-s1_", "campaign-s1-a2_")]
    assert st2.d["blocks"]["campaign-s1_C"]["window_utc"][0] is not None


def test_three_consecutive_errors_stop_the_block_and_it_stays_stopped(monkeypatch, tmp_path):
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    block = next(b for b in campaign.plan(1) if b["config"] == "B1")
    run_turn, seen = fake_runner([200, 500, 500, 500])
    monkeypatch.setattr(campaign, "run_turn", run_turn)
    st = campaign.State(1)
    campaign.run_block(block, 1, st)
    assert len(seen) == 4 and st.d["blocks"]["campaign-s1_B1"]["stopped"] == "3 consecutive errors"
    assert st.guard.stopped_blocks == ["campaign-s1_B1"]
    seen.clear()
    campaign.run_block(block, 1, campaign.State(1))
    assert seen == []


def test_each_turn_gets_its_configurations_turn_cap(monkeypatch, tmp_path):
    """D064: run_call.py is called with --turn-cap 4 for D', 3 for the others, in both stages."""
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    calls = []

    class Done:
        returncode, stderr = 0, ""

    def fake_run(args, **kw):
        calls.append(args)
        return Done()
    monkeypatch.setattr(campaign.subprocess, "run", fake_run)
    st = campaign.State(1)
    for cfg in campaign.CONFIGS:
        blk = next(b for b in campaign.plan(1) if b["config"] == cfg)
        campaign.run_turn(cfg, "T1", 1, 1, blk, st)
    caps = {a[a.index("--agent") + 1]: a[a.index("--turn-cap") + 1] for a in calls if "--turn-cap" in a}
    assert caps == {"LINKML_A": "3", "LINKML_B1": "3", "LINKML_B2": "3", "LINKML_C": "3", "LINKML_D": "3",
                    "LINKML_DP": "4"}
    blocks = {a[a.index("--agent") + 1]: a[a.index("--block-cap") + 1] for a in calls if "--block-cap" in a}
    assert blocks["LINKML_DP"] == "100" and blocks["LINKML_C"] == "30"


def test_plan_prints_the_turn_caps():
    c = campaign.counts(campaign.plan(1))
    assert c["DP"]["turn_cap"] == 4 and c["DP"]["block_cap"] == 100 and c["C"]["turn_cap"] == 3


def test_the_token_ceiling_is_recorded_not_passed_and_the_runaway_cap_is(monkeypatch, tmp_path):
    """Owner, session 9a: the token ceiling (the thread ceiling of BULK_SCOPE_DRILL included) is computed and recorded
    in the attempt, never passed to run_call.py; every turn gets --turn-usd-cap 2.0, and a turn above it (exit 4, or
    its recorded tokens) stops the block."""
    import json
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    calls = []

    class Done:
        returncode, stderr = 0, ""
    monkeypatch.setattr(campaign.subprocess, "run", lambda args, **kw: calls.append(args) or Done())
    st = campaign.State(1)
    blk = next(b for b in campaign.plan(1) if b["config"] == "D")
    parent = campaign.label("D", "BULK_SCOPE", 1, 1)
    st.d["turns"]["D|BULK_SCOPE|1"] = {"attempts": [{"label": parent, "ok": True}], "done": parent}
    campaign.summary_path(parent).write_text(json.dumps({"tokens": {"max_call_input": 218689}}))
    drill = campaign.label("D", "BULK_SCOPE_DRILL", 1, 1)
    campaign.summary_path(drill).write_text(json.dumps({"calls": [{"status": 200}], "tokens": {
        "input": 357493, "cache_write": 49870, "cache_read": 307607, "output": 2949, "max_call_input": 357493}}))
    _, _, runaway = campaign.run_turn("D", "BULK_SCOPE_DRILL", 1, 1, blk, st)
    _, _, runaway_t1 = campaign.run_turn("D", "T1", 1, 1, blk, st)
    runs = [a for a in calls if "--label" in a]
    assert all("--token-ceiling" not in a for a in runs)
    assert all(a[a.index("--turn-usd-cap") + 1] == "2.0" for a in runs)
    att = st.d["turns"]["D|BULK_SCOPE_DRILL|1"]["attempts"][0]
    assert att["token_ceiling"] == 527518 and att["above_token_ceiling"] is False and runaway is False
    assert st.d["turns"]["D|T1|1"]["attempts"][0]["token_ceiling"] == 308829 and runaway_t1 is False
    fict = campaign.label("C", "T1", 1, 1)
    campaign.summary_path(fict).write_text(json.dumps({"calls": [{"status": 200}], "tokens": {
        "input": 646154, "cache_write": 646154, "cache_read": 0, "output": 0, "max_call_input": 646154}}))
    _, _, runaway_c = campaign.run_turn("C", "T1", 1, 1, next(b for b in campaign.plan(1) if b["config"] == "C"), st)
    assert runaway_c is True and st.d["turns"]["C|T1|1"]["attempts"][0]["turn_usd"] == 2.1


def test_a_runaway_turn_stops_its_block(monkeypatch, tmp_path):
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    block = next(b for b in campaign.plan(1) if b["config"] == "A")
    block = {**block, "turns": block["turns"][:4]}
    seen = []

    def run_turn(cfg, qid, rep, stage, blk, st):
        rec = st.d["turns"].setdefault(f"{cfg}|{qid}|{rep}", {"attempts": []})
        lab = campaign.label(cfg, qid, stage, rep, len(rec["attempts"]) + 1)
        rec["attempts"].append({"label": lab, "ok": True})
        rec["done"] = lab
        seen.append(lab)
        return {"calls": [{"status": 200}]}, 1, len(seen) == 2
    monkeypatch.setattr(campaign, "run_turn", run_turn)
    st = campaign.State(1)
    campaign.run_block(block, 1, st)
    assert len(seen) == 2 and st.d["blocks"]["campaign-s1_A"]["stopped"].startswith("runaway guard")
    assert st.guard.stopped_blocks == ["campaign-s1_A"]


def test_a_resumed_block_rewarms_only_after_5_minutes(monkeypatch, tmp_path):
    """Owner, session 9a: a block resumed with its warm-up done and turns left runs a new warm-up attempt (not graded)
    when its last call ended more than 5 minutes ago; otherwise it goes on with its turns."""
    import datetime as dt
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    block = next(b for b in campaign.plan(1) if b["config"] == "D")
    block = {**block, "turns": block["turns"][:4]}
    for minutes, want in ((6, ["WARMUP", "a3"]), (4, [])):
        st = campaign.State(1)
        st.d["turns"] = {"D|WARMUP|1": {"attempts": [{"label": "D_WARMUP_campaign-s1_r1", "ok": True},
                                                      {"label": "D_WARMUP_campaign-s1-a2_r1", "ok": True}],
                                        "done": "D_WARMUP_campaign-s1-a2_r1"}}
        t1 = block["turns"][1]["qid"]
        st.d["turns"][f"D|{t1}|1"] = {"attempts": [{"label": f"D_{t1}_campaign-s1_r1", "ok": True}],
                                       "done": f"D_{t1}_campaign-s1_r1"}
        end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes)).isoformat()
        st.d["blocks"]["campaign-s1_D"] = {"window_utc": ["2026-10-06T18:33:11+00:00", end], "stopped": None, "used": 17}
        run_turn, seen = fake_runner([200] * 5)
        monkeypatch.setattr(campaign, "run_turn", run_turn)
        campaign.run_block(block, 1, st)
        warm = [x for x in seen if "_WARMUP_" in x]
        assert (warm == ["D_WARMUP_campaign-s1-a3_r1"]) == bool(want) and len(seen) == 2 + bool(want)
        (tmp_path / "state_campaign-s1.json").unlink()


def test_a_block_records_its_window_in_the_cost_estimate(monkeypatch, tmp_path):
    """Owner, session 9a: the block's run is a warehouse segment, opened before its first turn, extended after each
    turn and closed at its end."""
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    block = next(b for b in campaign.plan(1) if b["config"] == "C")
    block = {**block, "turns": block["turns"][:3]}
    run_turn, seen = fake_runner([200, 200, 200])
    monkeypatch.setattr(campaign, "run_turn", run_turn)
    st = campaign.State(1)
    campaign.run_block(block, 1, st)
    seg = st.guard.segments
    assert len(seg) == 1 and seg[0][0] <= seg[0][1] and not st.guard.running
    assert campaign.State(1).d["guard"]["segments"] == seg


def test_stage1_caps_are_30_except_dp():
    """Owner, session 9a: a one-call margin covered neither the added warm-ups nor a retry after an error; the cost
    protection is the pause at 36 USD. Stage 1 caps: 30 for D, B1, B2, A and C; D' keeps 100."""
    assert {b["config"]: b["cap"] for b in campaign.plan(1)} == {"DP": 100, "D": 30, "B1": 30, "B2": 30, "A": 30,
                                                                 "C": 30}


def test_a_block_that_ends_exactly_at_its_cap_is_not_stopped(monkeypatch, tmp_path):
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    block = next(b for b in campaign.plan(1) if b["config"] == "C")
    block = {**block, "cap": 3, "turns": block["turns"][:3]}
    run_turn, seen = fake_runner([200, 200, 200])
    monkeypatch.setattr(campaign, "run_turn", run_turn)
    st = campaign.State(1)
    campaign.run_block(block, 1, st)
    assert len(seen) == 3 and st.d["blocks"]["campaign-s1_C"]["stopped"] is None and st.guard.stopped_blocks == []
    short = {**block, "config": "B1", "turns": next(b for b in campaign.plan(1) if b["config"] == "B1")["turns"][:4]}
    run_turn, seen = fake_runner([200, 200, 200, 200])
    monkeypatch.setattr(campaign, "run_turn", run_turn)
    campaign.run_block(short, 1, st)                          # three calls for four turns: a stop, one turn prevented
    assert len(seen) == 3 and st.d["blocks"]["campaign-s1_B1"]["stopped"] == "block cap 3 reached"
    assert st.guard.stopped_blocks == ["campaign-s1_B1"]


def test_the_last_turn_is_the_last_one_not_yet_done(monkeypatch, tmp_path):
    """The last turn is the last one not yet done in the block's order; a resumed block skips the done ones."""
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    block = next(b for b in campaign.plan(1) if b["config"] == "C")
    block = {**block, "cap": 2, "turns": block["turns"][:3]}
    st = campaign.State(1)
    first = campaign.label("C", block["turns"][0]["qid"], 1, 1)
    st.d["turns"][f"C|{block['turns'][0]['qid']}|1"] = {"attempts": [{"label": first, "ok": True}], "done": first}
    run_turn, seen = fake_runner([200, 200])
    monkeypatch.setattr(campaign, "run_turn", run_turn)
    campaign.run_block(block, 1, st)
    assert len(seen) == 2 and st.d["blocks"]["campaign-s1_C"]["stopped"] is None


def test_dp_block_cap_uses_the_measured_calls_per_question(monkeypatch, tmp_path):
    """Stage 1 measured 2.5 REST calls per D' question (60 calls, 24 turns; owner, 2026-10-07), not 1.85: the stage 2
    cap is (warm-up + 2.5 per turn) x 1.1. The per-question cap stays 4 (D064)."""
    assert campaign.CONFIGS["DP"][3] == 2.5
    stage2(monkeypatch, tmp_path)                 # 3 discriminating (BULK_SCOPE added as the drill's parent) + 1 held out
    b = next(x for x in campaign.plan(2) if x["config"] == "DP")
    turns = len(b["turns"]) - 1
    assert turns == 4 * 4 + 5 * 1 and b["cap"] == math.ceil((1 + 2.5 * turns) * 1.1)


def test_questions_added_in_stage_2_are_never_in_stage_1():
    """Session 9b (owner, 2026-10-07): N1 to N3 are asked in stage 2 only; stage 1 keeps its 24 questions."""
    qs = campaign.stage1_questions()
    assert len(qs) == 24 and not {"N1", "N2", "N3"} & set(qs)
    assert campaign.added_in_stage2() == ["N1", "N2", "N3"]
    assert not {"N1", "N2", "N3"} & set(campaign.held_out())


# Session 9b (owner, 2026-10-07): the reduced stage 2, C and B2 only, its own file beside the gate's eval/stage2.yaml.

GATE16 = ["T1", "T2", "T7", "T7_R1", "T8", "NO_DEMAND", "BEYOND_H", "BULK_SCOPE", "BULK_SCOPE_DRILL", "DIM_MIX", "T9",
          "CS_LAST_MONTH_GAP", "G1", "S_STOCKOUT_COUNTRY", "S_FIRST_WORLD", "S_DORMANT_VALUE"]
Q1_Q4 = ["H_LOCAL_STOCKOUT", "H_LOWEST_COUNTRY", "H_STOCKOUT_2027", "H_STOCKOUT_ES"]
NEW = ["N1", "N2", "N3"]


def test_the_gates_stage2_file_is_kept_as_evidence():
    s = yaml.safe_load(campaign.STAGE2_FILE.read_text())
    assert sorted(s["discriminating"]) == sorted(GATE16) and s["drop_order"] == ["G1"]
    assert campaign.REDUCED_FILE != campaign.STAGE2_FILE and campaign.REDUCED_FILE.exists()


def test_reduced_plan_c_and_b2_thirty_turns_each():
    blocks = campaign.plan(2, reduced=True)
    assert [b["config"] for b in blocks] == ["C", "B2"]           # the seeded configuration order of stage 2
    for b in blocks:
        t = b["turns"]
        assert t[0] == {"qid": "WARMUP", "rep": 1} and len(t) == 31 and b["cap"] == math.ceil(31 * 1.1) == 35
        r1 = [x["qid"] for x in t[1:] if x["rep"] == 1]
        r2 = [x["qid"] for x in t[1:] if x["rep"] == 2]
        assert sorted(r1) == sorted(Q1_Q4 + NEW) and sorted(r2) == sorted(GATE16 + ["G2", "CS_FAMILY",
                                                                                   "CS_MIDDLE_MONTH_GAP", "T6"] + NEW)
        assert t.index({"qid": "BULK_SCOPE_DRILL", "rep": 2}) == t.index({"qid": "BULK_SCOPE", "rep": 2}) + 1
        assert t[1:len(r1) + 1] == [x for x in t[1:] if x["rep"] == 1]          # repetition 1, then repetition 2
    assert campaign.plan(2, reduced=True) == blocks                              # fixed seeds
    c, b2 = blocks
    assert [x["qid"] for x in c["turns"]] != [x["qid"] for x in b2["turns"]]     # shuffled per block and repetition
    n = campaign.counts(blocks)
    assert n["C"]["graded_turns"] == n["B2"]["graded_turns"] == 30 and n["total_rest_calls_expected"] == 62


def test_reduced_plan_labels():
    for b in campaign.plan(2, reduced=True):
        for t in b["turns"][1:]:
            lab = campaign.label(b["config"], t["qid"], 2, t["rep"])
            assert LABEL.match(lab) and lab == f"{b['config']}_{t['qid']}_campaign-s2_r{t['rep']}"


def test_reduced_plan_route_groups():
    groups = campaign.route_groups(campaign.plan(2, reduced=True))
    assert groups["N1"] == groups["N2"] == "both" and groups["N3"] == "procedure"
    assert groups["CS_FAMILY"] == groups["G1"] == groups["G2"] == "view only" and groups["T6"] == "no tool"
    assert {g for q, g in groups.items() if q in Q1_Q4} == {"procedure"}
    assert set(groups.values()) == {"procedure", "view only", "both", "no tool"}


def test_a_stage_keeps_the_plan_it_started_with(monkeypatch, tmp_path):
    """The state file records the plan of the stage's first run; a resume with another plan is refused."""
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    st = campaign.State(2)
    campaign.check_plan(st, "reduced")
    assert st.d["plan"] == "reduced"
    campaign.check_plan(campaign.State(2), "reduced")
    with pytest.raises(SystemExit):
        campaign.check_plan(campaign.State(2), "gate")


def test_reduced_cost_estimate_from_the_billed_means_of_stage_1():
    spec = importlib.util.spec_from_file_location("cost_model", ROOT / "eval" / "cost_model.py")
    cm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cm)
    est = cm.reduced_stage2(campaign.plan(2, reduced=True))
    assert est["turns"] == {"C": 30, "B2": 30}
    assert math.isclose(est["mean"]["C"], 30 * 0.102) and math.isclose(est["mean"]["B2"], 30 * 0.258)
    assert est["list_turns"] == {"C": 8, "B2": 8}            # S_ x 3 (r2), Q1, Q3, Q4 (r1), N3 (r1, r2)
    assert math.isclose(est["heavy"]["B2"], 8 * 0.328 + 22 * 0.258)
    assert est["total_mean_usd"] < est["total_heavy_usd"] < 13.5 < 15
    assert est["guard_usd"] < est["total_mean_usd"]           # the guard counts 1.0 credit an hour and no guardrail
