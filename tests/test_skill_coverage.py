"""
The linkml-coverage skill script (session 8, configurations D and D'), in its numbers-passed-in mode, on cases computed
by hand in docs/DEFINITION.md section 2 and data/traps.yaml (never data/coverage_ref.py, which the script must not
copy or import).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "snowflake" / "phase4_others" / "skill" / "linkml-coverage" / "coverage.py"
MONTHS = [f"{2026 + (6 + k - 1) // 12}-{(6 + k - 1) % 12 + 1:02d}-01" for k in range(1, 37)]   # 2026-07 onwards


def run(stock, series: dict[int, float]) -> dict:
    pairs = [[MONTHS[k - 1], q] for k, q in series.items()]
    args = [sys.executable, str(SCRIPT), "--as-of", "2026-06-01", "--forecast", json.dumps(pairs)]
    if stock is not None:
        args += ["--stock", str(stock)]
    r = subprocess.run(args, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def flat(v, ks=range(1, 37), missing=()):
    return {k: v for k in ks if k not in missing}


@pytest.mark.parametrize("name,stock,series,expected", [
    ("worked example (section 2)", 1000, {**dict(enumerate([120, 90, 150, 110, 130, 100, 140, 80, 160], 1)),
                                          **{k: 100 for k in range(10, 37)}}, 8.5),
    ("T1 family: 1,400 against 500 a month", 1400, flat(500), 2.8),
    ("T2: months 2 and 3 absent count as 0", 500, flat(100, missing=(2, 3)), 7.0),
    ("BEYOND_H: mean of the non-zero months of the horizon", 5000, {**flat(100, range(1, 25), (5, 6)),
                                                                     **flat(1000, range(25, 37))}, 50.0),
    ("zero stock (T8)", 0, flat(100), 0.0),
    ("null stock (T9: no row at the analysis month)", None, flat(100), 0.0),
    ("no forecast at all (NO_DEMAND)", 500, {}, None),
    ("exact depletion at month 3", 300, flat(100), 3.0),
    ("zero month before depletion counts as covered", 200, {1: 100, 2: 0, 3: 100}, 3.0),
])
def test_coverage_cases(name, stock, series, expected):
    out = run(stock, series)
    assert (out["coverage_months"] is None) if expected is None else out["coverage_months"] == pytest.approx(expected)


def test_months_outside_the_horizon_are_ignored_and_gaps_reported():
    out = run(500, flat(100, missing=(2, 3)))
    assert out["months_without_forecast_counted_as_0"] == 2 and len(out["forecast_by_month"]) == 24
    assert out["horizon"] == ["2026-07-01", "2028-06-01"]


def test_script_does_not_copy_or_import_the_reference():
    text = SCRIPT.read_text()
    assert "coverage_ref" not in text and "py_coverage" not in text and "cascade" not in text


def test_negative_stock_is_an_explicit_error():
    """The definition does not define a negative stock; with f(1) = 0 the formula would divide by zero."""
    pairs = [[MONTHS[0], 0], [MONTHS[1], 100]]
    r = subprocess.run([sys.executable, str(SCRIPT), "--as-of", "2026-06-01", "--stock", "-5", "--forecast",
                        json.dumps(pairs)], capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and "negative stock" in r.stderr and "ZeroDivision" not in r.stderr
