"""
Session 11c (owner): keys of the metamodel that the compiler does not read fail closed. The generated objects are
written for one value of each (compiler/supported.py); a contract holding another value must make every generator that
writes the key's behaviour stop with "<key>: only <value> is supported by this compiler", never generate the same
objects silently. The current contract still generates byte-identical files (tests/test_generated.py).
"""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "compiler"))
sys.path.insert(0, str(ROOT))
CONTRACT = yaml.safe_load((ROOT / "contract" / "stock_coverage.yaml").read_text())
META = yaml.safe_load((ROOT / "contract" / "metamodel.yaml").read_text())

import supported  # noqa: E402


def _render(generator: str):
    import gen_agent, gen_closing_procedure, gen_closing_sv, gen_craw, gen_dmf, gen_native_sv, gen_procedure  # noqa: E401
    return {"gen_procedure": lambda c: (gen_procedure.render(c), gen_procedure.render_sql(c)),
            "gen_native_sv": gen_native_sv.render, "gen_closing_sv": gen_closing_sv.render,
            "gen_dmf": gen_dmf.render, "gen_agent": gen_agent.render,
            "gen_closing_procedure": gen_closing_procedure.render, "gen_craw": gen_craw.render}[generator]


def _other(v):
    """A value other than v, of a plausible type."""
    if isinstance(v, bool):
        return not v
    if isinstance(v, int):
        return v + 1
    if isinstance(v, str):
        return v + "_OTHER"
    if isinstance(v, list):
        return list(reversed(v)) if len(v) > 1 else v + ["OTHER"]
    if v is None:
        return "OTHER"
    raise TypeError(v)


CASES = [(e.key, g) for e in supported.FIXED for g in e.generators]


@pytest.mark.parametrize("key,generator", CASES, ids=[f"{k}-{g}" for k, g in CASES])
def test_another_value_fails_closed(key, generator):
    entry = next(e for e in supported.FIXED if e.key == key)
    c = copy.deepcopy(CONTRACT)
    where, value, setter = next(iter(entry.locate(c)))
    setter(_other(value))
    with pytest.raises(ValueError, match=re.escape(f"{where}: only {entry.shown(c)} is supported by this compiler")):
        _render(generator)(c)


@pytest.mark.parametrize("generator", sorted({g for e in supported.FIXED for g in e.generators}))
def test_the_current_contract_passes(generator):
    supported.check(CONTRACT, generator)


def test_every_key_described_as_not_read_is_classified():
    """Every metamodel attribute whose description says 'Declared, not read by the compiler' is either fixed (and
    checked) or documentation only."""
    declared = {f"{c}.{a}" for c, v in META["classes"].items() for a, d in (v.get("attributes") or {}).items()
                if "Declared, not read by the compiler" in (d or {}).get("description", "")}
    classified = {e.key for e in supported.FIXED} | set(supported.DOCUMENTATION_ONLY)
    assert declared <= classified, sorted(declared - classified)


def test_every_fixed_key_is_found_in_the_contract():
    for e in supported.FIXED:
        assert list(e.locate(CONTRACT)), e.key


def _run_optimised(tmp_path: Path, c: dict):
    """gen_procedure.py run as a script under python -O, which strips assert statements, on contract c."""
    import subprocess
    path, out = tmp_path / "contract.yaml", tmp_path / "out.sql"
    path.write_text(yaml.safe_dump(c, sort_keys=False))
    r = subprocess.run([sys.executable, "-O", str(ROOT / "compiler" / "gen_procedure.py"), "--contract", str(path),
                        "--target", "sql", "--out", str(out)], capture_output=True, text=True, cwd=ROOT)
    return r, out


def test_fail_closed_holds_under_python_O(tmp_path):
    """Session 15: the compiler validates with explicit exceptions, never with assert, so python -O (which strips
    asserts) still stops on an unsupported key and on a contract the handler cannot honour."""
    control = __import__("subprocess").run([sys.executable, "-O", "-c", "assert False"])
    assert control.returncode == 0                       # the control: -O does strip asserts in this interpreter
    c = copy.deepcopy(CONTRACT)
    c["metrics"][0]["interpolation"] = "STEP"
    r, out = _run_optimised(tmp_path, c)
    assert r.returncode != 0 and not out.exists()
    assert "metrics.stock_coverage.interpolation: only LINEAR is supported by this compiler" in r.stderr
    c = copy.deepcopy(CONTRACT)
    c["refusal_codes"] = [x for x in c["refusal_codes"] if x["id"] != "AS_OF_MISSING"]
    r, out = _run_optimised(tmp_path, c)
    assert r.returncode != 0 and not out.exists()
    assert "ValueError: contract codes without a check" in r.stderr and "AS_OF_MISSING" in r.stderr


def test_the_compiler_validates_without_assert():
    """Session 15: no assert statement in compiler/ or tools/ (tests keep theirs)."""
    import ast
    found = [f"{p.relative_to(ROOT)}:{n.lineno}" for d in ("compiler", "tools") for p in sorted((ROOT / d).glob("*.py"))
             for n in ast.walk(ast.parse(p.read_text())) if isinstance(n, ast.Assert)]
    assert found == []
