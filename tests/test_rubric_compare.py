"""Session 9c, step 1e: grading a stage under a chosen rubric (eval/campaign.py grade --rubric) and the table of the
regrade, rubric 3.2 against 3.3 (eval/rubric_compare.py). No call."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "snowflake" / "probe_b" / "mount"))
sys.path.insert(0, str(ROOT / "snowflake" / "probe_b"))


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "eval" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


campaign = load("campaign")
rc = load("rubric_compare")


def test_the_grades_of_record_keep_their_file_and_any_other_rubric_has_its_own():
    assert campaign.grades_file(1, "3.2").name == "grades_campaign-s1.json"           # the run's record, rubric 3.2
    assert campaign.grades_file(2, "3.3").name == "grades_campaign-s2.rubric-3.3.json"


def test_grade_writes_under_the_rubric_asked(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    monkeypatch.setattr(campaign, "done_labels", lambda stage: {"C_T1_campaign-s1_r1": ("C", "T1")})

    class G:
        @staticmethod
        def turns_from_log(run, labels):
            return [{"answer": "a", "tables": []}]

        @staticmethod
        def grade_turn(t, sv, io, rubric=None):
            seen.append(rubric)
            return {"config": "C", "question_id": "T1", "verdict": "correct", "verdict_figure_only": "correct",
                    "rubric": rubric}

        @staticmethod
        def scores(out):
            return {}

    monkeypatch.setattr(campaign, "load_grader", lambda: G)
    campaign.grade(1, "3.2")
    campaign.grade(1, "3.3")
    assert seen == ["3.2", "3.3"]
    assert json.loads((tmp_path / "grades_campaign-s1.json").read_text())[0]["rubric"] == "3.2"
    assert json.loads((tmp_path / "grades_campaign-s1.rubric-3.3.json").read_text())[0]["rubric"] == "3.3"


def g(cfg, qid, label, verdict, fig, crit=None):
    return {"config": cfg, "question_id": qid, "label": label, "verdict": verdict, "verdict_figure_only": fig,
            "criteria": crit or {}}


def test_compare_counts_per_configuration_and_lists_every_changed_verdict():
    old = [g("C", "T1", "a", "correct", "correct"),
           g("C", "T9", "b", "wrong", "correct",
             {"basis_wording": {"result": "fail", "why": "coverage given in a unit: 'Oat cereal bar 1 kg ...'"}}),
           g("B1", "T4", "c", "manual", "manual", {"numeric": {"result": "manual", "why": "both given"}})]
    new = [g("C", "T1", "a", "correct", "correct"),
           g("C", "T9", "b", "correct", "correct", {"basis_wording": {"result": "pass", "why": "months"}}),
           g("B1", "T4", "c", "correct", "correct", {"numeric": {"result": "pass", "why": "expected given"}})]
    out = rc.compare(old, new)
    assert out["by_config"]["C"] == {"turns": 2, "primary_3.2": {"correct": 1, "wrong": 1, "manual": 0},
                                     "primary_3.3": {"correct": 2, "wrong": 0, "manual": 0},
                                     "figure_only_3.2": {"correct": 2, "wrong": 0, "manual": 0},
                                     "figure_only_3.3": {"correct": 2, "wrong": 0, "manual": 0}}
    assert [c["label"] for c in out["changed"]] == ["c", "b"]                        # by configuration, then label
    t9 = out["changed"][1]
    assert (t9["primary"], t9["figure_only"]) == (("wrong", "correct"), ("correct", "correct"))
    assert t9["criteria"] == {"basis_wording": {"3.2": "fail: coverage given in a unit: 'Oat cereal bar 1 kg ...'",
                                                "3.3": "pass: months"}}


def test_compare_refuses_two_files_of_different_turns():
    import pytest
    with pytest.raises(SystemExit):
        rc.compare([g("C", "T1", "a", "correct", "correct")], [g("C", "T1", "z", "correct", "correct")])
