"""Charter version 5: no instruction given to an agent carries the repository's internal references: the word
"session", "traps", a trap or failure-mode id of the contract, or the contract's internal names. The specs built
from DEFINITION.md are also rebuilt here and compared with the committed files (drift)."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = yaml.safe_load((ROOT / "contract" / "stock_coverage.yaml").read_text())
TRAP_IDS = sorted({f["id"] for f in CONTRACT["failure_modes"]} | {"T7_R1", "G1", "G2"}, key=len, reverse=True)
INTERNAL = ["CLOSING_STOCK", "LAST_PERIOD", "LAST_NON_EMPTY", "beyond_horizon", "Provenance"]
SPECS = ["snowflake/phase4_others/a/agent_a.yaml", "snowflake/phase4_others/d/agent_d.yaml",
         "snowflake/phase4_others/d/agent_dp.yaml", "snowflake/phase4_others/b1/agent_b1.yaml", "generated/agent_b2.yaml"]


def leaks(text: str) -> list[str]:
    found = [w for w in ("session", "traps") if re.search(rf"\b{w}\b", text, re.I)]
    found += [t for t in TRAP_IDS if re.search(rf"(?<![\w-]){re.escape(t)}(?![\w-])", text)]
    found += [w for w in INTERNAL if w in text]
    return found


@pytest.mark.parametrize("spec", SPECS)
def test_no_internal_reference_in_instructions(spec):
    s = yaml.safe_load((ROOT / spec).read_text())
    for k, v in s["instructions"].items():
        assert not leaks(v), (spec, k, leaks(v))


def test_extracted_specs_do_not_drift(tmp_path):
    before = {p: (ROOT / p).read_bytes() for p in SPECS[:3]}
    for script in ("snowflake/phase4_others/a/build_spec.py", "snowflake/phase4_others/d/build_specs.py"):
        r = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
    assert all((ROOT / p).read_bytes() == b for p, b in before.items())


def test_provenance_lines_exist_in_the_definition_and_are_dropped():
    text = (ROOT / "docs" / "DEFINITION.md").read_text()
    assert sum(1 for line in text.splitlines() if line.startswith("Provenance:")) >= 5
    sys.path.insert(0, str(ROOT / "snowflake" / "phase4_others"))
    from definition_text import extract
    assert "Provenance" not in extract((1, 2, 3, 7, 8)) and "session 4" not in extract((1, 2, 3, 7, 8))
