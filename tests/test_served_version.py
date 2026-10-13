"""Pre-stage-1 harness fix: every call records the served agent version. No call.

- Before each block, eval/campaign.py reads the agent's default version (SHOW VERSIONS IN AGENT) into the block state
  ("declared_version"); a version other than the frozen state of eval/campaign.md stops the block before its first
  turn and holds the stage.
- run_call.py writes "model" (the orchestration model_name of the REST usage) and "served_version" (null at call time)
  into every summary.
- eval/campaign.py traces writes the served version found in each turn's trace rows into its summary, then checks every
  turn of the stage against the frozen state.

Fixtures: eval/fixtures/session8b_g2_events.json (C's G2 turn, session 8b smoke, REST events) and
eval/fixtures/session8b_g2_trace.json (the same turn's trace rows, reduced; VERSION$3 was C's default then; the record
id of each row added in session 9a for D065).
"""

from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "snowflake" / "probe_b" / "mount"))
sys.path.insert(0, str(ROOT / "snowflake" / "probe_b"))
from run_call import summarize, turn_model  # noqa: E402

_spec = importlib.util.spec_from_file_location("campaign", ROOT / "eval" / "campaign.py")
campaign = importlib.util.module_from_spec(_spec)
sys.modules["campaign"] = campaign
_spec.loader.exec_module(campaign)

G2 = json.loads((ROOT / "eval" / "fixtures" / "session8b_g2_events.json").read_text())
TRACE = json.loads((ROOT / "eval" / "fixtures" / "session8b_g2_trace.json").read_text())
FROZEN = {"LINKML_A": "VERSION$6", "LINKML_B1": "VERSION$7", "LINKML_B2": "VERSION$8", "LINKML_C": "VERSION$6",
          "LINKML_D": "VERSION$7", "LINKML_DP": "VERSION$7"}


# ------------------------------------------------------------------------------------------------ frozen state

def test_frozen_versions_are_read_from_campaign_md():
    assert campaign.frozen_versions() == FROZEN


def test_frozen_versions_refuse_a_table_without_every_agent(tmp_path):
    f = tmp_path / "campaign.md"
    f.write_text("## Frozen state (x)\n\n| Configuration | Agent | Served version | Spec |\n|---|---|---|---|\n"
                 "| A | LINKML_A | VERSION$6 | a.yaml |\n")
    with pytest.raises(SystemExit):
        campaign.frozen_versions(f)


# ------------------------------------------------------------------------------------------------ declared version

def show_rows(default: str) -> list[dict]:
    """SHOW VERSIONS IN AGENT rows as agents.py reads them: LIVE has no name; is_default is the string 'true'."""
    return [{"name": "", "is_default": "false"}, {"name": "VERSION$7", "is_default": "false"},
            {"name": default, "is_default": "true"}]


def test_default_version_from_show_versions():
    assert campaign.default_version(show_rows("VERSION$8")) == "VERSION$8"
    assert campaign.default_version([{"name": "VERSION$8", "is_default": "false"}]) is None


def block(cfg: str, n: int = 3) -> dict:
    b = next(b for b in campaign.plan(1) if b["config"] == cfg)
    return {**b, "turns": b["turns"][:n]}


def runner():
    seen = []

    def run_turn(cfg, qid, rep, stage, blk, st):
        rec = st.d["turns"].setdefault(f"{cfg}|{qid}|{rep}", {"attempts": []})
        lab = campaign.label(cfg, qid, stage, rep, len(rec["attempts"]) + 1)
        rec["attempts"].append({"label": lab, "ok": True})
        rec["done"] = lab
        st.save()
        seen.append(lab)
        return {"calls": [{"status": 200}], "tokens": {}}, 1, False
    return run_turn, seen


@pytest.fixture
def run_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    run_turn, seen = runner()
    monkeypatch.setattr(campaign, "run_turn", run_turn)
    return seen


def test_block_records_the_declared_version_and_runs_when_it_is_the_frozen_one(run_dir, monkeypatch):
    monkeypatch.setattr(campaign, "declared_version", lambda agent: FROZEN[agent])
    st = campaign.State(1)
    campaign.run_block(block("B2"), 1, st)
    b = st.d["blocks"]["campaign-s1_B2"]
    assert b["declared_version"] == "VERSION$8" and b["declared_read_utc"] and b["stopped"] is None
    assert len(run_dir) == 3


def test_a_declared_version_other_than_the_frozen_one_stops_the_block_and_the_stage(run_dir, monkeypatch):
    monkeypatch.setattr(campaign, "declared_version", lambda agent: "VERSION$9" if agent == "LINKML_C" else FROZEN[agent])
    st = campaign.State(1)
    campaign.run_block(block("C"), 1, st)
    b = st.d["blocks"]["campaign-s1_C"]
    assert run_dir == [] and b["declared_version"] == "VERSION$9"
    assert b["stopped"].startswith("version guard") and "VERSION$6" in b["stopped"]
    assert "version guard" in st.guard.check()
    campaign.run_block(block("B1"), 1, st)                       # the stage is held: no other block starts
    assert run_dir == []
    st2 = campaign.State(1)                                      # and it stays held on resume
    assert "version guard" in st2.guard.check()


def test_an_unreadable_declared_version_stops_the_block(run_dir, monkeypatch):
    def fail(agent):
        raise RuntimeError("002003: SQL compilation error")
    monkeypatch.setattr(campaign, "declared_version", fail)
    st = campaign.State(1)
    campaign.run_block(block("A"), 1, st)
    b = st.d["blocks"]["campaign-s1_A"]
    assert run_dir == [] and b["declared_version"] is None and "002003" in b["stopped"]


# ------------------------------------------------------------------------------------------------ model, served version

def test_model_is_the_orchestration_model_name_of_the_rest_usage():
    s = summarize(G2["events"])
    assert turn_model([s]) == "claude-sonnet-5-5"            # not the guardrail model of the same usage
    assert turn_model([s, s]) == "claude-sonnet-5-5"
    assert turn_model([{"status": 0}]) is None and turn_model([]) is None


def test_served_version_from_the_recorded_trace():
    assert campaign.served_version(TRACE["rows"]) == "VERSION$3"
    assert campaign.served_version([]) is None
    other = copy.deepcopy(TRACE["rows"][:2])
    other[1]["RECORD_ATTRIBUTES"][campaign.VERSION_ATTR] = "VERSION$4"
    assert campaign.served_version(other) == ["VERSION$3", "VERSION$4"]
    assert campaign.served_version([{"RECORD_ATTRIBUTES": json.dumps({"x": 1})}]) is None


class FakeCursor:
    """GET_AI_OBSERVABILITY_EVENTS per agent: the recorded rows, as the connector returns them (tuples)."""

    def __init__(self, rows_by_agent: dict[str, list[dict]]):
        self.rows, self.cols, self.out = rows_by_agent, ["START_TIMESTAMP", "TIMESTAMP", "RECORD", "RECORD_ATTRIBUTES"], []

    def execute(self, sql, params=None):
        if params:
            self.out = [tuple(r.get(c) for c in self.cols) for r in self.rows.get(params[0], [])]
            self.description = [(c,) for c in self.cols]
        return self

    def fetchall(self):
        return self.out


def shifted(rows: list[dict], hours: int, version: str | None = "keep") -> list[dict]:
    out = []
    for r in copy.deepcopy(rows):
        for k in ("START_TIMESTAMP", "TIMESTAMP"):
            if r[k]:
                r[k] = str(dt.datetime.fromisoformat(r[k]) + dt.timedelta(hours=hours))
        if version != "keep":
            r["RECORD_ATTRIBUTES"].pop(campaign.VERSION_ATTR)
            if version:
                r["RECORD_ATTRIBUTES"][campaign.VERSION_ATTR] = version
        out.append(r)
    return out


def test_traces_write_the_served_version_into_each_summary_and_check_the_stage(monkeypatch, tmp_path, capsys):
    """Four turns on the recorded G2 trace: C served the frozen version; B2 served another one (reported, never
    regraded); B1 has trace rows without a version; D has no trace row in its window."""
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    frozen = {**FROZEN, "LINKML_C": "VERSION$3"}
    monkeypatch.setattr(campaign, "frozen_versions", lambda path=None: frozen)
    start = dt.datetime.fromisoformat(TRACE["started_utc"])
    turns = {"C": 0, "B2": 1, "B1": 2, "D": 3}
    st = campaign.State(1)
    for cfg, h in turns.items():
        lab = campaign.label(cfg, "G2", 1, 1)
        st.d["turns"][f"{cfg}|G2|1"] = {"attempts": [{"label": lab, "ok": True}], "done": lab}
        a = start + dt.timedelta(hours=h)
        w = [a.isoformat(), (a + dt.timedelta(seconds=TRACE["seconds_total"])).isoformat()]
        campaign.summary_path(lab).write_text(json.dumps(
            {"label": lab, "window_utc": w, "calls": [{"request_id": TRACE["request_id"], "status": 200}],
             "model": "claude-sonnet-5-5", "served_version": None, "trace_rows": None}))
    st.save()
    cur = FakeCursor({"LINKML_C": shifted(TRACE["rows"], 0), "LINKML_B2": shifted(TRACE["rows"], 1, "VERSION$7"),
                      "LINKML_B1": shifted(TRACE["rows"], 2, None), "LINKML_D": shifted(TRACE["rows"], 5)})
    report = campaign.traces(1, cur=cur)
    got = {cfg: json.loads(campaign.summary_path(campaign.label(cfg, "G2", 1, 1)).read_text()) for cfg in turns}
    # D065: rows kept by request id; the CORTEX_AGENT_REQUEST row (no START_TIMESTAMP) is now kept: 11, not 10
    assert got["C"]["served_version"] == "VERSION$3" and got["C"]["trace_rows"] == 11
    assert got["B2"]["served_version"] == "VERSION$7"
    assert got["B1"]["served_version"] is None and got["B1"]["trace_rows"] == 11
    assert got["D"]["served_version"] is None and got["D"]["trace_rows"] == 0
    assert got["C"]["model"] == "claude-sonnet-5-5"                     # the rest of the summary is kept
    assert report["equal"] == ["C_G2_campaign-s1_r1"]
    assert report["differ"] == [{"label": "B2_G2_campaign-s1_r1", "served": "VERSION$7", "frozen": "VERSION$8"}]
    assert report["no_version"] == ["B1_G2_campaign-s1_r1"] and report["no_trace"] == ["D_G2_campaign-s1_r1"]
    assert json.loads((tmp_path / "versions_campaign-s1.json").read_text()) == report
    out = capsys.readouterr().out
    assert "B2_G2_campaign-s1_r1" in out and "harness event" in out
