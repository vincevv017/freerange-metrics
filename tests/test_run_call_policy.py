"""run_call.py policy dp (session 8, configuration D'): only the exact linkml-coverage script command is approved."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "snowflake" / "probe_b" / "mount"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "snowflake" / "probe_b"))
from run_call import decide, dp_allowed  # noqa: E402

D = "/mnt/skills/stage/linkml_metrics_raw_skills_dp/skills/linkml-coverage"


@pytest.mark.parametrize("cmd", [
    f"python3 {D}/coverage.py --as-of 2026-06-01 --stock-sql \"SELECT SUM(stock_qty_eq) FROM t\" --forecast-sql \"SELECT m, q FROM f\"",
    f"cd {D} && python3 coverage.py --as-of 2026-06-01 --stock 1400 --forecast '[[\"2026-07-01\", 500]]'",
    f"cd {D}/ && python3 coverage.py --as-of 2026-06-01 --stock-sql 'SELECT 1; ' --forecast-sql 'SELECT 1'",
])
def test_allowed(cmd):
    assert dp_allowed(cmd)
    assert decide({"type": "bash", "name": "bash", "input": {"command": cmd}}, "dp")[0] == "Allow Once"


@pytest.mark.parametrize("cmd", [
    f"python3 {D}/coverage.py --as-of 2026-06-01 --stock 1 --forecast '[]'; env",
    f"python3 {D}/coverage.py --as-of 2026-06-01 --stock 1 --forecast '[]' > /tmp/x",
    f"cd /tmp && python3 coverage.py --as-of 2026-06-01 --stock 1 --forecast '[]'",
    f"python3 /tmp/coverage.py --as-of 2026-06-01 --stock 1 --forecast '[]'",
    f"python3 {D}/coverage.py --stock 1 --forecast '[]'",
    f"python3 {D}/coverage.py --as-of 2026-06-01 --as-of 2026-05-01 --stock 1 --forecast '[]'",
    f"python3 {D}/coverage.py --as-of 2026-06-01 --eval 1",
    "ls /mnt/skills",
    f"cat {D}/SKILL.md",
])
def test_denied(cmd):
    assert not dp_allowed(cmd)
    assert decide({"type": "bash", "name": "bash", "input": {"command": cmd}}, "dp")[0] == "Deny"


# ---- session 8c-0, step 8, decision 4: labels carry configuration, question, stage and repetition; no overwrite

from run_call import check_label  # noqa: E402


@pytest.mark.parametrize("label", ["C_T1_s8c0-step8_r1", "B2_T1_s8c0-step8_r1", "DP_S_FIRST_WORLD_campaign_r3"])
def test_label_with_the_four_parts_is_accepted(tmp_path, label):
    assert check_label(label, "s8c0", tmp_path) == label


@pytest.mark.parametrize("label", ["c_t1", "C_T1_s7", "C_T1_r1", "C T1 step8 r1", "C_T1_s8c0-step8_rx"])
def test_label_without_the_four_parts_is_refused(tmp_path, label):
    with pytest.raises(SystemExit):
        check_label(label, "s8c0", tmp_path)


def test_label_with_a_log_is_refused(tmp_path):
    (tmp_path / "summary_c_t1_s8c0_step8_r1.json").write_text("{}")
    with pytest.raises(SystemExit):
        check_label("C_T1_s8c0-step8_r1", "s8c0", tmp_path)


def test_earlier_budgets_keep_their_free_labels(tmp_path):
    assert check_label("mount 1: no code tool", "mount", tmp_path) == "mount 1: no code tool"


@pytest.mark.parametrize("label", ["C_T1_manual_r1", "B2_H_STOCKOUT_ES_manual_r12"])
def test_manual_budget_accepts_manual_labels(tmp_path, label):
    """Session 8c (owner): budget manual, 20 calls, for the owner's replays of an exchange to cite."""
    from run_call import CAPS
    assert CAPS["manual"] == 20
    assert check_label(label, "manual", tmp_path) == label


@pytest.mark.parametrize("label", ["C_T1_campaign-s1_r1", "C_T1_manual", "c_t1_manual_r1"])
def test_manual_budget_refuses_other_labels(tmp_path, label):
    with pytest.raises(SystemExit):
        check_label(label, "manual", tmp_path)
