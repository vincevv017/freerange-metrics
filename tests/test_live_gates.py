"""
Session 13 (owner, 2026-10-08): a plain `pytest` is the offline suite. Each on-account test file skips every test
unless its own variable is set (LINKML_PROCEDURE_LIVE=1 for STOCK_COVERAGE, LINKML_CLOSING_LIVE=1 for CLOSING_STOCK),
so no test calls Snowflake because a connection happens to exist.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATES = {"tests/test_procedure.py": "LINKML_PROCEDURE_LIVE", "tests/test_closing_procedure.py": "LINKML_CLOSING_LIVE"}


@pytest.mark.parametrize("path,gate", GATES.items())
def test_the_account_tests_skip_without_their_gate(path, gate):
    env = {k: v for k, v in os.environ.items() if k not in GATES.values()}
    env["LINKML_SF_CONNECTION"] = "no_such_connection_session13"      # a connection attempt would fail, not skip
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs", path,
                        "-k", "live or not live"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    calls = [l for l in r.stdout.splitlines() if "SKIPPED" in l and gate not in l]
    if path == "tests/test_procedure.py":
        assert not re.search(r"\d+ passed", r.stdout), r.stdout[-1500:]      # nothing in it runs offline
        assert not calls, calls
    assert "failed" not in r.stdout and "error" not in r.stdout.lower(), r.stdout[-1500:]
