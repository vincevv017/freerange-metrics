"""
Generated artefacts against the contract.

- drift: each generator (compiler/gen_schema.py, gen_dmf.py, gen_procedure.py with both targets, gen_closing_sv.py,
  gen_closing_procedure.py, gen_agent.py, gen_questions.py, and gen_native_sv.py for its three files) regenerates into
  a temporary folder; the committed file in generated/ must be byte-identical. gen_craw.py is held by
  tests/test_c_raw.py, gen_reference.py by tests/test_reference.py.
- DMF coverage: generated/dmf.sql checks every quality expectation, creates a function for each CUSTOM one, and
  never attaches a DMF to a table or sets a schedule.
- consumers: no Python file imports the deleted hand-written schema v0 any more. Parity with it was checked before
  its deletion (Phase 2): same tables, columns, types and order, grains (plus the declared DIM_ITEM grain), classes
  (plus lifecycle_status, CONFORMED) and unit variants; the dataset fingerprints did not change.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Session 15: the generators that list the valid months and the attribute labels read the published dataset; the
# private repository does not hold it (git-ignored), so a clone of it, and its CI, skip these with the reason.
DATASET = pytest.mark.skipif(not (ROOT / "data" / "output" / "manifest.json").exists(),
                             reason="the published dataset is not in data/output/")


@pytest.mark.parametrize("generator,name", [("gen_schema.py", "schema.py"), ("gen_dmf.py", "dmf.sql"),
                                            ("gen_procedure.py --target python", "stock_coverage_procedure.sql"),
                                            ("gen_procedure.py --target sql", "stock_coverage_procedure_sql.sql"),
                                            ("gen_closing_sv.py", "closing_stock_sv.sql"),
                                            ("gen_closing_procedure.py", "closing_stock_procedure.sql"),
                                            pytest.param("gen_agent.py", "agent_c.yaml", marks=DATASET),
                                            pytest.param("gen_questions.py", "reference_questions.yaml",
                                                         marks=DATASET)])
def test_generated_file_does_not_drift(tmp_path, generator, name):
    out = tmp_path / name
    script, *flags = generator.split()
    r = subprocess.run([sys.executable, f"compiler/{script}", *flags, "--out", str(out)], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.read_bytes() == (ROOT / "generated" / name).read_bytes(), \
        f"generated/{name} differs from the contract: run python compiler/{script}"


def test_dmf_sql_covers_every_quality_expectation_and_attaches_nothing():
    contract = yaml.safe_load((ROOT / "contract" / "stock_coverage.yaml").read_text())
    sql = (ROOT / "generated" / "dmf.sql").read_text()
    checked = set(re.findall(r"^SELECT '(QE_[A-Z_]+)' AS expectation", sql, flags=re.M))
    assert checked == {q["id"] for q in contract["quality_expectations"]}
    custom = set(re.findall(r"^CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS\.RAW\.DMF_(QE_[A-Z_]+)\(", sql, flags=re.M))
    assert custom == {q["id"] for q in contract["quality_expectations"] if q["dmf"] == "CUSTOM"}
    body = "\n".join(l for l in sql.splitlines() if not l.startswith("--"))
    assert "ADD DATA METRIC FUNCTION" not in body and "DATA_METRIC_SCHEDULE" not in body


def test_no_consumer_imports_schema_v0():
    pattern = re.compile(r"^\s*(from|import)\s+schema_" + "v0", re.M)
    tracked = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    offenders = [f for f in tracked if pattern.search((ROOT / f).read_text())]
    assert not offenders, offenders


def test_agent_spec_matches_the_contract_surface():
    """Session 8b: two tools, B2's semantic view (no claim on coverage) and one generic tool on the generated procedure;
    one string property per contract parameter; required as declared; reject on a missing grant."""
    contract = yaml.safe_load((ROOT / "contract" / "stock_coverage.yaml").read_text())
    spec = yaml.safe_load((ROOT / "generated" / "agent_c.yaml").read_text())
    sv, tool = spec["tools"]
    assert sv["tool_spec"]["type"] == "cortex_analyst_text_to_sql" and "coverage_months" not in sv["tool_spec"]["description"]
    assert spec["tool_resources"][sv["tool_spec"]["name"]]["semantic_view"] == "LINKML_METRICS.RAW.LINKML_B2_SV"
    assert spec["orchestration"]["tool_not_accessible"] == "reject"
    b2 = yaml.safe_load((ROOT / "generated" / "agent_b2.yaml").read_text())
    assert spec["instructions"]["response"] == b2["instructions"]["response"]      # charter: common response
    schema = tool["tool_spec"]["input_schema"]
    assert tool["tool_spec"]["type"] == "generic"
    assert set(schema["properties"]) == {p["id"] for p in contract["parameters"]}
    assert all(v["type"] == "string" for v in schema["properties"].values())
    assert set(schema["required"]) == {p["id"] for p in contract["parameters"] if p["is_required"]}
    assert spec["tool_resources"][tool["tool_spec"]["name"]]["identifier"] == "LINKML_METRICS.RAW.STOCK_COVERAGE"
    text = yaml.safe_dump(spec)
    assert "decision" not in text and "DEFINITION.md" not in text and "\u2014" not in text


def test_every_failure_mode_has_a_reference_question():
    contract = yaml.safe_load((ROOT / "contract" / "stock_coverage.yaml").read_text())
    qs = yaml.safe_load((ROOT / "generated" / "reference_questions.yaml").read_text())["questions"]
    assert {fm["id"] for fm in contract["failure_modes"]} <= {q["failure_mode"] for q in qs}
    assert all("AS_OF" not in q["question"] for q in qs)


@DATASET
def test_native_b2_files_do_not_drift(tmp_path):
    """compiler/gen_native_sv.py (session 8, configuration B2) writes three files; each must equal generated/."""
    r = subprocess.run([sys.executable, "compiler/gen_native_sv.py", "--out-dir", str(tmp_path)], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    for name in ("b2_native_views.sql", "b2_native_sv.yaml", "agent_b2.yaml"):
        assert (tmp_path / name).read_bytes() == (ROOT / "generated" / name).read_bytes(), \
            f"generated/{name} differs from the contract: run python compiler/gen_native_sv.py"


def test_native_b2_enriched_yaml_differs_only_by_grounding():
    """The deployed B2 YAML is the generated one plus is_enum and sample_values set by the enrich tool, nothing else."""
    def strip(d):
        if isinstance(d, dict):
            return {k: strip(v) for k, v in d.items() if k not in ("is_enum", "sample_values")}
        return [strip(x) for x in d] if isinstance(d, list) else d
    gen = yaml.safe_load((ROOT / "generated" / "b2_native_sv.yaml").read_text())
    enr = yaml.safe_load((ROOT / "snowflake" / "phase4_others" / "b2" / "LINKML_B2_SV_enriched.yaml").read_text())
    assert strip(gen) == strip(enr)
    assert len(gen["verified_queries"]) <= 3
    heroes = {h["sku"] for h in yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())["hero_items"]}
    heroes |= {h["family"]["code"] for h in yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())["hero_items"]}
    assert not any(h in v["sql"] for v in gen["verified_queries"] for h in heroes)


def test_b1_enriched_yaml_differs_only_by_grounding_and_avoids_heroes():
    """B1 (hand-written, session 8): the deployed YAML is the hand-written one plus is_enum and sample_values only."""
    def strip(d):
        if isinstance(d, dict):
            return {k: strip(v) for k, v in d.items() if k not in ("is_enum", "sample_values")}
        return [strip(x) for x in d] if isinstance(d, list) else d
    b1 = ROOT / "snowflake" / "phase4_others" / "b1"
    src = yaml.safe_load((b1 / "LINKML_B1_SV.yaml").read_text())
    assert strip(src) == strip(yaml.safe_load((b1 / "LINKML_B1_SV_enriched.yaml").read_text()))
    traps = yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())
    heroes = {h["sku"] for h in traps["hero_items"]} | {h["family"]["code"] for h in traps["hero_items"]}
    assert len(src["verified_queries"]) <= 3
    assert not any(h in v["sql"] for v in src["verified_queries"] for h in heroes)


REFERENCE_IMPLEMENTATIONS = ["data/coverage_ref.py", "data/checks/check_dataset.py", "docs/check_coverage_formula.py",
                             "snowflake/phase4_others/skill/linkml-coverage/coverage.py"]


BOILERPLATE = {'if __name__ == "__main__":'}


def _code_lines(path: Path) -> set[str]:
    """Normalised non-trivial code lines: whitespace collapsed, case folded; comments, imports and short lines dropped."""
    out = set()
    for line in path.read_text().splitlines():
        t = " ".join(line.split()).lower()
        if len(t) >= 25 and not t.startswith(("#", "--", '"""', "from ", "import ")) and t not in BOILERPLATE:
            out.add(t)
    return out


def test_sql_procedure_shares_no_code_with_the_reference_implementations():
    """Session 8b, decision 1: the SQL Scripting procedure is generated from the contract, never derived from the
    pandas or DuckDB references or the skill's coverage.py. Its template, its generator and the generated file import
    none of them and share no code line with them."""
    ours = [ROOT / "compiler" / "procedure_scripting.py", ROOT / "compiler" / "gen_procedure.py",
            ROOT / "generated" / "stock_coverage_procedure_sql.sql"]
    gen = (ROOT / "compiler" / "gen_procedure.py").read_text()
    assert not re.search(r"^\s*(from|import)\s+(data|docs)\b|coverage_ref|check_dataset|check_coverage_formula|duckdb|pandas",
                         gen, flags=re.M)
    for ref in REFERENCE_IMPLEMENTATIONS:
        theirs = _code_lines(ROOT / ref)
        for f in ours:
            shared = _code_lines(f) & theirs
            assert not shared, (f.name, ref, sorted(shared)[:5])
