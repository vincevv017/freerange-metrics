"""Session 9a, decision D065: eval/campaign.py traces keeps a turn's trace rows by request id. No call.

The time window bounds the read; only the rows whose ai.observability.record_id is one of the turn's request ids
(calls[].request_id) are kept; rows in the turn's window from a request the harness did not make are counted as foreign
and reported; a turn with no row of its own is no_trace. Thread id is never used (0 over REST), nor a bare numeric value
(1000000001 is the thread id of the owner's Snowsight request and the database id of every row).

Fixture: eval/fixtures/session8c1_dp_trace.json, the session 8c-1 D' REST turn (3 calls) as run_call.py read it by time:
21 rows, of which 5 belong to the owner's concurrent Snowsight request 00000011 (LIVE).
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("campaign", ROOT / "eval" / "campaign.py")
campaign = importlib.util.module_from_spec(_spec)
sys.modules["campaign"] = campaign
_spec.loader.exec_module(campaign)

FIX = json.loads((ROOT / "eval" / "fixtures" / "session8c1_dp_trace.json").read_text())
IDS = [c["request_id"] for c in FIX["calls"]]
SNOWSIGHT = "00000011-0000-4000-8000-000000000011"
FROZEN = {"LINKML_A": "VERSION$6", "LINKML_B1": "VERSION$7", "LINKML_B2": "VERSION$8", "LINKML_C": "VERSION$6",
          "LINKML_D": "VERSION$7", "LINKML_DP": "VERSION$7"}


def rid(r: dict) -> str:
    return r["RECORD_ATTRIBUTES"]["ai.observability.record_id"]


# ------------------------------------------------------------------------------------------------ the row split

def test_the_recorded_8c1_turn_keeps_its_16_rows_and_counts_the_5_snowsight_rows_as_foreign():
    kept, foreign = campaign.own_rows(FIX["rows"], IDS, set(IDS), FIX["window_utc"])
    assert len(FIX["rows"]) == 21 and len(kept) == 16 and len(foreign) == 5
    assert {rid(r) for r in kept} == set(IDS) and {rid(r) for r in foreign} == {SNOWSIGHT}
    assert campaign.served_version(FIX["rows"]) == ["LIVE", "VERSION$7"]      # the window read alone: "differ"
    assert campaign.served_version(kept) == "VERSION$7"


def test_the_request_rows_without_a_start_timestamp_are_kept():
    """CORTEX_AGENT_REQUEST rows carry no START_TIMESTAMP; the window read by START_TIMESTAMP alone dropped them."""
    kept, _ = campaign.own_rows(FIX["rows"], IDS, set(IDS), FIX["window_utc"])
    assert sum(r["RECORD"]["name"] == "CORTEX_AGENT_REQUEST" for r in kept) == 3


def test_thread_id_and_bare_numbers_never_select_a_row():
    attrs = [r["RECORD_ATTRIBUTES"] for r in FIX["rows"]]
    assert {a.get("snow.ai.observability.agent.thread_id") for a in attrs} == {0, None, 1000000001}
    assert {a["snow.ai.observability.database.id"] for a in attrs} == {1000000001}
    for ids in (["1000000001"], [1000000001], ["0"], [0]):
        kept, foreign = campaign.own_rows(FIX["rows"], ids, set(ids), FIX["window_utc"])
        assert kept == [] and len(foreign) == 21


def test_rows_of_another_harness_turn_are_neither_kept_nor_foreign():
    """Two turns cut from the recorded calls: the first call alone, then calls 2 and 3 with a window that starts while
    the first call's rows still run. The first call's rows sit in the second window but are the harness's own."""
    a = [FIX["window_utc"][0], FIX["calls"][1]["started_utc"]]
    b = ["2026-10-05T18:52:58+00:00", FIX["window_utc"][1]]
    known = set(IDS)
    k1, f1 = campaign.own_rows(FIX["rows"], IDS[:1], known, a)
    k2, f2 = campaign.own_rows(FIX["rows"], IDS[1:], known, b)
    assert (len(k1), len(f1), len(k2), len(f2)) == (6, 5, 10, 0)
    assert any(rid(r) == IDS[0] and campaign.row_time(r) >= campaign.utc_naive(b[0]) for r in FIX["rows"])


def test_a_failed_call_without_a_request_id_selects_nothing():
    kept, _ = campaign.own_rows(FIX["rows"], [None, IDS[2]], set(IDS), FIX["window_utc"])
    assert {rid(r) for r in kept} == {IDS[2]} and len(kept) == 4


# ------------------------------------------------------------------------------------------------ campaign.py traces

class FakeCursor:
    def __init__(self, rows_by_agent):
        self.rows, self.cols, self.out, self.sql = rows_by_agent, ["START_TIMESTAMP", "TIMESTAMP", "RECORD",
                                                                    "RECORD_ATTRIBUTES"], [], []

    def execute(self, sql, params=None):
        self.sql.append((sql, params))
        if params:
            self.out = [tuple(r.get(c) for c in self.cols) for r in self.rows.get(params[0], [])]
            self.description = [(c,) for c in self.cols]
        return self

    def fetchall(self):
        return self.out


def stage_with(tmp_path, monkeypatch, turns: dict[str, list[str]]):
    """turns: label suffix -> request ids, every turn on D' with the recorded window."""
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    monkeypatch.setattr(campaign, "frozen_versions", lambda path=None: FROZEN)
    st = campaign.State(1)
    labs = {}
    for qid, ids in turns.items():
        lab = campaign.label("DP", qid, 1, 1)
        st.d["turns"][f"DP|{qid}|1"] = {"attempts": [{"label": lab, "ok": True}], "done": lab}
        campaign.summary_path(lab).write_text(json.dumps(
            {"label": lab, "window_utc": FIX["window_utc"], "calls": [{"request_id": i, "status": 200} for i in ids],
             "served_version": None, "trace_rows": None}))
        labs[qid] = lab
    st.save()
    return labs


def test_traces_keep_the_turns_own_rows_and_report_the_foreign_ones(tmp_path, monkeypatch, capsys):
    labs = stage_with(tmp_path, monkeypatch, {"SKU0001_IT": IDS})
    cur = FakeCursor({"LINKML_DP": FIX["rows"]})
    report = campaign.traces(1, cur=cur)
    s = json.loads(campaign.summary_path(labs["SKU0001_IT"]).read_text())
    assert s["trace_rows"] == 16 and s["trace_foreign_rows"] == 5 and s["served_version"] == "VERSION$7"
    assert s["trace_ids_without_rows"] == []
    saved = json.loads((tmp_path / "trace_dp_sku0001_it_campaign_s1_r1.json").read_text())
    assert len(saved) == 16 and {rid(r) for r in saved} == set(IDS)
    assert report["equal"] == [labs["SKU0001_IT"]] and report["differ"] == [] and report["no_trace"] == []
    assert report["foreign"] == [{"label": labs["SKU0001_IT"], "rows": 5, "request_ids": [SNOWSIGHT]}]
    out = capsys.readouterr().out
    assert "foreign" in out and SNOWSIGHT in out
    sql, params = cur.sql[-1]
    assert "TIMESTAMP >=" in sql and "TIMESTAMP <=" in sql and params[0] == "LINKML_DP"   # the window bounds the read
    assert "thread_id" not in sql


def test_a_turn_whose_window_holds_only_foreign_rows_is_no_trace(tmp_path, monkeypatch):
    labs = stage_with(tmp_path, monkeypatch, {"T1": ["0000032c-0000-4000-8000-00000000032c"]})
    report = campaign.traces(1, cur=FakeCursor({"LINKML_DP": FIX["rows"]}))
    s = json.loads(campaign.summary_path(labs["T1"]).read_text())
    assert s["trace_rows"] == 0 and s["served_version"] is None and s["trace_foreign_rows"] == 21
    assert report["no_trace"] == [labs["T1"]] and report["equal"] == []


def test_a_call_whose_id_has_no_row_is_listed(tmp_path, monkeypatch):
    rows = [r for r in copy.deepcopy(FIX["rows"]) if rid(r) != IDS[2]]
    labs = stage_with(tmp_path, monkeypatch, {"T2": IDS})
    campaign.traces(1, cur=FakeCursor({"LINKML_DP": rows}))
    s = json.loads(campaign.summary_path(labs["T2"]).read_text())
    assert s["trace_rows"] == 12 and s["trace_ids_without_rows"] == [IDS[2]]
