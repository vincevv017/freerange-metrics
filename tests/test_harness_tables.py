"""Session 8c, step 1a: the harness keeps every response.table event and the turn's REST usage tokens; the grader grades
the numbers of the text and of the tables (a value in a table counts as given; decision 4 of session 8c).

Fixture: eval/fixtures/session8b_g2_events.json, the response.table event and the final response (text and table blocks)
of C's G2 turn in the session 8b smoke, as recorded. The text names four countries; the ten values were in the table
only, so G2 was graded manual in session 8b (docs/phase4_notes.md, finding 74).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "snowflake" / "probe_b" / "mount"))
sys.path.insert(0, str(ROOT / "snowflake" / "probe_b"))
from run_call import summarize, turn_tokens  # noqa: E402

_spec = importlib.util.spec_from_file_location("grade", ROOT / "eval" / "grade.py")
grade = importlib.util.module_from_spec(_spec)
sys.modules["grade"] = grade
_spec.loader.exec_module(grade)

G2 = json.loads((ROOT / "eval" / "fixtures" / "session8b_g2_events.json").read_text())
SV = {"b2_semantic_view"}


def test_summarize_keeps_the_table_title_columns_and_rows():
    s = summarize(G2["events"])
    assert len(s["tables"]) == 1
    t = s["tables"][0]
    assert t["title"] == "Closing stock value (EUR) by country, June 2026"
    assert t["columns"] == ["COUNTRY_CODE", "CLOSING_STOCK_VALUE"]
    assert len(t["rows"]) == 10 and ["SE", "14476855.4803"] in t["rows"]
    assert t["query_id"] == "0000016c-0000-4000-8000-00000000016c"


def test_a_table_in_the_event_and_in_the_final_response_is_kept_once():
    only_event = [e for e in G2["events"] if e["event"] == "response.table"]
    only_block = [e for e in G2["events"] if e["event"] == "response"]
    assert summarize(only_event)["tables"] == summarize(only_block)["tables"] == summarize(G2["events"])["tables"]


def test_turn_tokens_from_the_rest_usage():
    s = summarize(G2["events"])
    assert turn_tokens([s]) == {"input": 156233, "cache_write": 32064, "cache_read": 124157, "output": 560,
                                "max_call_input": 156233, "calls": 1}


def test_turn_tokens_add_the_calls_of_a_turn():
    s = summarize(G2["events"])
    t = turn_tokens([s, s])
    assert t["input"] == 2 * 156233 and t["max_call_input"] == 156233 and t["calls"] == 2


def g2_turn(tables: bool) -> dict:
    s = summarize(G2["events"])
    return {"config": "C", "question_id": "G2", "answer": s["text"], "request_id": G2["request_id"],
            "tool_uses": G2["tool_uses"], "tool_results": [], "sql": [], "tables": s["tables"] if tables else []}


def test_g2_text_alone_stays_manual_as_in_session_8b():
    g = grade.grade_turn(g2_turn(False), SV)
    assert g["verdict"] == "manual", g


def test_g2_regraded_with_its_table_is_correct():
    """Decision 4 (session 8c): a value in a table counts as given. The ten values at full precision match; the
    fan-out guard needs no SQL at that precision."""
    g = grade.grade_turn(g2_turn(True), SV)
    assert g["verdict"] == "correct", g
    assert g["criteria"]["numeric"]["why"] == "10 rows match"


def test_a_coverage_column_counts_as_months():
    t = {"config": "B2", "question_id": "T1", "tool_uses": [], "tool_results": [], "sql": [],
         "answer": "Flour and baking in France, June 2026, stock and forecast measured in kg equivalent.",
         "tables": [{"title": "Coverage", "columns": ["FAMILY_CODE", "COVERAGE_MONTHS"], "rows": [["PANTRY_FLOUR", "2.8000"]]}]}
    g = grade.grade_turn(t)
    assert g["criteria"]["numeric"]["result"] == "pass", g
    wrong = {**t, "tables": [{"title": "Coverage", "columns": ["FAMILY_CODE", "COVERAGE_MONTHS"],
                              "rows": [["PANTRY_FLOUR", "6.25"]]}]}
    assert grade.grade_turn(wrong)["verdict"] == "wrong"


def test_a_table_value_outside_a_coverage_column_is_not_a_coverage():
    t = {"config": "B2", "question_id": "T1", "tool_uses": [], "tool_results": [], "sql": [],
         "answer": "Flour and baking in France covers 2.8 months as of June 2026, stock and forecast in kg equivalent.",
         "tables": [{"title": "Inputs", "columns": ["STOCK_QTY_EQ", "FORECAST_QTY_EQ"], "rows": [["1400", "12000"]]}]}
    g = grade.grade_turn(t)
    assert g["criteria"]["numeric"]["result"] == "pass", g


def test_turns_from_log_reads_tables_from_the_summary_or_from_the_events(tmp_path):
    s = summarize(G2["events"])
    call = {"n": G2["n"], "status": 200, "request_id": G2["request_id"], **s, "tool_uses": G2["tool_uses"]}
    (tmp_path / "summary_c_g2.json").write_text(json.dumps({"calls": [call]}))
    (t1,) = grade.turns_from_log(tmp_path, {"c_g2": ("C", "G2")})
    assert t1["tables"] == s["tables"]
    old = {k: v for k, v in call.items() if k != "tables"}          # a session 8b summary: no tables kept
    (tmp_path / "summary_c_g2.json").write_text(json.dumps({"calls": [old]}))
    (tmp_path / "events.jsonl").write_text(json.dumps({"n": G2["n"], "label": "c_g2", "events": G2["events"]}) + "\n")
    (t2,) = grade.turns_from_log(tmp_path, {"c_g2": ("C", "G2")})
    assert t2["tables"] == s["tables"]
    assert grade.grade_turn(t2, SV)["verdict"] == "correct"
