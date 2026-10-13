"""
Session 13 (owner, 2026-10-08): the harness for C-raw's campaign arm. Conditions: rubric 3.2 and 3.3 unchanged; a C-raw
entry only (closing stock to closing_stock, coverage to stock_coverage, the rest to the view); the recorded grades of
the six configurations regraded identical, byte for byte.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
RUN = Path.home() / "work" / "assets" / "linkml-metrics-runs" / "campaign"
RUBRIC_SHA = "671ae66220e89a8a3c0e021550799fc795daa5782a3b7f7f5ca90b28f663f9fb"      # eval/rubric.yaml as committed before session 13 (e3973d1)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


cp = load("campaign", ROOT / "eval" / "campaign.py")
g = cp.load_grader()
Q = {q["id"]: q for q in g.QUESTIONS.values()} if isinstance(g.QUESTIONS, dict) else {q["id"]: q for q in g.QUESTIONS}
SV = {"b2_semantic_view", "b1_semantic_view", "a_semantic_view", "c_raw_semantic_view"}


def test_the_rubric_file_is_unchanged():
    assert hashlib.sha256((ROOT / "eval" / "rubric.yaml").read_bytes()).hexdigest() == RUBRIC_SHA


# Session 15: in the public tree the owner's decisions (eval/manual_decisions.yaml) carry the numbered pseudonyms of
# tools/make_public_snapshot.py, not the run folder's request ids, so they match no recorded turn and the regrade
# cannot reproduce the record there. The test then skips; in the private tree it runs as before.
PSEUDONYM = re.compile(r"[0-9a-f]{8}-0000-4000-8000-[0-9a-f]{12}")
PSEUDONYMISED = any(PSEUDONYM.fullmatch(str(d["request_id"])) for d in yaml.safe_load(
    (ROOT / "eval" / "manual_decisions.yaml").read_text())["decisions"])


@pytest.mark.skipif(not (RUN / "grades_campaign-s1.json").exists(), reason="the campaign's run folder is not here")
@pytest.mark.skipif(PSEUDONYMISED, reason="the fixtures carry pseudonymised request ids (public tree)")
@pytest.mark.parametrize("stage", [1, 2])
@pytest.mark.parametrize("rubric", ["3.2", "3.3"])
def test_the_six_configurations_regrade_byte_for_byte(stage, rubric):
    labels = cp.done_labels(stage)
    out = []
    for lab, t in zip(labels, g.turns_from_log(cp.RUN, labels)):
        res = g.grade_turn(t, SV, ("DIM_ITEM", "B2_ITEM"), rubric=rubric)
        out.append({**res, "label": lab, "answer": t["answer"], "tables": t["tables"]})
    assert json.dumps(out, indent=1, default=str) == cp.grades_file(stage, rubric).read_text()


def test_the_arm_plays_cs_questions_in_cs_order_under_its_own_tags():
    try:
        cp.use_arm("CR")
        for stage in (1, 2):
            (arm,) = cp.arm_plan(stage)
            twin = next(b for b in (cp.plan(1) if stage == 1 else cp.reduced_plan()) if b["config"] == "C")
            assert arm["config"] == "CR" and arm["turns"] == twin["turns"] and arm["cap"] == twin["cap"]
            assert cp.label("CR", "T1", stage, 1) == f"CR_T1_craw-s{stage}_r1"
        assert sum(t["qid"] != "WARMUP" for t in cp.arm_plan(1)[0]["turns"]) == 24
        assert sum(t["qid"] != "WARMUP" for t in cp.arm_plan(2)[0]["turns"]) == 30
        assert cp.frozen_versions()["LINKML_C_RAW"] == "VERSION$2"
    finally:
        cp.ARM, cp.STAGE_TAG = None, {1: "campaign-s1", 2: "campaign-s2"}
    assert list(cp.CONFIGS) == ["A", "B1", "B2", "C", "D", "DP"]     # the six seeds and orders unchanged


def test_run_call_accepts_cr_labels():
    rc = (ROOT / "snowflake" / "probe_b" / "mount" / "run_call.py").read_text()
    pat = re.compile(re.search(r'LABEL = re\.compile\(r"([^"]+)"\)', rc).group(1))
    assert pat.match("CR_CS_LAST_MONTH_GAP_craw-s1_r1") and pat.match("C_T1_campaign-s1_r1")


def use(name, **inp):
    return {"type": "generic", "name": name, "input": inp}


VIEW = [{"type": "system_agentic_semantic_context", "name": "c_raw_semantic_view"},
        {"type": "system_execute_sql", "name": "system_execute_sql"}]


@pytest.mark.parametrize("qid,uses,verdict", [
    ("CS_LAST_MONTH_GAP", [use("closing_stock")], "pass"),
    ("CS_LAST_MONTH_GAP", VIEW, "fail"),                      # H-CR-4: closing stock through the view
    ("G2", [use("closing_stock")], "pass"),
    ("T1", [use("stock_coverage")], "pass"),
    ("T1", [use("closing_stock")], "fail"),
    ("G1", VIEW, "pass"),
    ("G1", [use("closing_stock")], "fail"),
    ("T6", [], "pass"),
    ("N1", [use("stock_coverage"), use("closing_stock")], "pass"),
    ("N1", [use("stock_coverage")] + VIEW, "fail"),
])
def test_cr_routing(qid, uses, verdict):
    assert g.routing(Q[qid], "CR", uses, [], SV)[0] == verdict


def test_cr_g2_guard_reads_the_closing_stock_parameters():
    g._CTX.update(sql=[], uses=[use("closing_stock", basis="VALUE", grain='["country_code"]')])
    assert g.guard(["item_join_fanout"])[0] == "pass"
    g._CTX.update(sql=[], uses=[])
    assert g.guard(["item_join_fanout"])[0] == "manual"          # unchanged without the closing_stock call
