"""run_call.py client-side tool execution (session 8, D'): only one SELECT or WITH statement is run; everything else
is refused and the error is returned to the agent. No Snowflake connection is needed for these checks."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "snowflake" / "probe_b" / "mount"))
from client_sql import check_select, result_text  # noqa: E402


@pytest.mark.parametrize("sql", [
    "SELECT 1",
    "  select a, b from t where x = 'DROP TABLE y; --'  ",
    "WITH __stock AS (SELECT snapshot_month FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT_GAPFILLED) SELECT * FROM __stock",
    "SELECT 1;",
    "-- comment\nSELECT 1 /* trailing */",
])
def test_single_select_accepted(sql):
    assert check_select(sql) is None


@pytest.mark.parametrize("sql", [
    "DROP TABLE LINKML_METRICS.RAW.DIM_ITEM",
    "CREATE TABLE t AS SELECT 1",
    "SELECT 1; DROP TABLE t",
    "WITH x AS (SELECT 1) INSERT INTO t SELECT * FROM x",
    "UPDATE t SET a = 1",
    "CALL LINKML_METRICS.RAW.STOCK_COVERAGE('[]')",
    "SHOW TABLES",
    "USE ROLE ACCOUNTADMIN",
    "SELECT 1; SELECT 2",
    "",
])
def test_everything_else_refused(sql):
    assert check_select(sql) is not None


def test_result_text_matches_the_server_side_shape():
    text = result_text(["SNAPSHOT_MONTH", "Q"], [("2026-05-01", 350), ("2026-06-01", 0)], truncated=False)
    assert text.startswith("2 row(s) returned.\n\nSNAPSHOT_MONTH,Q\n\n") and "2026-06-01,0" in text
