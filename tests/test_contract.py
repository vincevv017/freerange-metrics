"""
Phase 1 contract tests.

- validity: both files pass linkml-validate (the metamodel against the LinkML meta schema, the instance against the
  metamodel) and linkml-lint; references between contract elements resolve (linkml-validate does not check them).
- (i) parity with the hand-written schema v0 was checked here until Phase 2; generated/schema.py replaces it, and
  tests/test_generated.py checks that it does not drift from the contract.
- (ii) traceability: every trap of data/traps.yaml and of docs/DEFINITION.md section 4 maps to a failure mode that at
  least one rule, refusal, expectation or invariant prevents. A trap with none is reported as a gap.
- (iii) docs/check_coverage_formula.py still passes 7 of 7, asserted on its numbers.
- numbers: the contract's own algorithm parameters, applied by a minimal evaluator, give the DEFINITION.md worked
  example and the traps.yaml beyond-horizon values, and the rejected choice gives the documented wrong value.
"""

from __future__ import annotations

import datetime as dt
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contract"
BIN = Path(sys.executable).parent

C = yaml.safe_load((CONTRACT / "stock_coverage.yaml").read_text())
TRAPS = yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())


def by_id(section: str) -> dict[str, dict]:
    return {e["id"]: e for e in C.get(section, [])}


TABLES, MEASURES, ATTRS = by_id("tables"), by_id("measures"), by_id("attributes")
METRIC = C["metrics"][0]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=600)


# ================================================================================================ validity

def test_metamodel_is_a_valid_linkml_schema():
    import linkml_runtime
    meta = Path(linkml_runtime.__file__).parent / "linkml_model" / "model" / "schema" / "meta.yaml"
    r = run(str(BIN / "linkml-validate"), "-s", str(meta), "-C", "schema_definition", "contract/metamodel.yaml")
    assert r.returncode == 0 and "No issues found" in r.stdout, r.stdout + r.stderr


def test_metamodel_lint_clean():
    r = run(str(BIN / "linkml-lint"), "--config", "contract/.linkmllint.yaml", "contract/metamodel.yaml")
    assert r.returncode == 0 and "No problems found" in r.stdout, r.stdout + r.stderr


def test_instance_validates_against_metamodel():
    r = run(str(BIN / "linkml-validate"), "-s", "contract/metamodel.yaml", "-C", "MetricContract",
            "contract/stock_coverage.yaml")
    assert r.returncode == 0 and "No issues found" in r.stdout, r.stdout + r.stderr


def _refs() -> list[tuple[str, str, str]]:
    """(where, kind, id) for every cross-reference in the instance."""
    out = []
    for t in C["relationships"]:
        out += [(t["id"], "tables", t["from_table"]), (t["id"], "tables", t["to_table"])]
    for m in C["measures"]:
        out.append((m["id"], "tables", m["table"]))
        out += [(m["id"], "dimension_classes", a["dimension_class"]) for a in m["additivity"]]
        pa = m.get("period_aggregation")
        out += [(pa["id"], "failure_modes", fm) for fm in pa.get("prevents", [])] if pa else []
    for a in C["attributes"]:
        out += [(a["id"], "tables", a["table"]), (a["id"], "dimension_classes", a["dimension_class"])]
        out += [(a["id"], "measures", x["measure"]) for x in a["applicability"]]
    bm = C["basis_model"]
    out += [(bm["id"], "tables", bm["item_table"]), (bm["id"], "measure_bases", bm["default_basis"]),
            (bm["id"], "refusal_codes", bm["refusal"])]
    out += [(m["id"], "measure_bases", x["basis"]) for m in C["measures"] for x in m["columns"]]
    sel = METRIC["member_selection"]
    out += [(sel["id"], "parameters", sel[k]) for k in ("upper_bound_parameter", "lower_bound_parameter", "rank_parameter")]
    out += [(sel["id"], "flags", f) for f in sel["set_apart_flags"]]
    out += [(sel["id"], "failure_modes", fm) for fm in sel.get("prevents", [])]
    out += [(bm["id"], "failure_modes", fm) for fm in bm.get("prevents", [])]
    out += [(METRIC["exhaustion_period"]["id"], "flags", f) for f in METRIC["exhaustion_period"]["none_for_flags"]]
    out += [(METRIC["id"], "measures", METRIC["snapshot_measure"]), (METRIC["id"], "measures", METRIC["flow_measure"]),
            (METRIC["id"], "parameters", METRIC["anchor_parameter"]),
            (METRIC["id"], "flags", METRIC["beyond_horizon"]["flag"])]
    out += [(METRIC["id"], "flags", o["flag"]) for o in METRIC["outcomes"] if o.get("flag")]
    for t in C["totals_rules"]:
        out.append((t["id"], "parameters", t["parameter"]))
    for s in C["default_scopes"]:
        out += [(s["id"], "attributes", s["attribute"]), (s["id"], "warning_codes", s["warning"])]
        out += [(s["id"], "measures", m) for m in s["applies_to_measures"]]
        out += [(s["id"], "metrics", m) for m in s["applies_to_metrics"]]
    for p in C["analysis_periods"]:
        out.append((p["id"], "tables", p["source_table"]))
    for p in C["parameters"]:
        out += [(p["id"], "refusal_codes", r) for r in p.get("refusal_codes", [])]
    for q in C["quality_expectations"]:
        out.append((q["id"], "tables", q["table"]))
        if q.get("references_table"):
            out.append((q["id"], "tables", q["references_table"]))
        for k, sec in (("warning", "warning_codes"), ("refusal", "refusal_codes")):
            if q.get(k):
                out.append((q["id"], sec, q[k]))
    for a in C["alert_thresholds"]:
        out.append((a["id"], "metrics", a["metric"]))
    for sec in ("attributes", "measure_bases", "metrics", "totals_rules", "member_set_rules", "default_scopes",
                "analysis_periods", "refusal_codes", "quality_expectations", "invariants"):
        for e in C[sec]:
            out += [(e["id"], "failure_modes", fm) for fm in e.get("prevents", [])]
    for o in METRIC["outcomes"]:
        out += [(f"outcome {o['order']}", "failure_modes", fm) for fm in o.get("prevents", [])]
    out += [("beyond_horizon", "failure_modes", fm) for fm in METRIC["beyond_horizon"].get("prevents", [])]
    return out


def test_every_reference_resolves():
    missing = [(w, k, i) for w, k, i in _refs() if i not in by_id(k)]
    assert not missing, f"unresolved references: {missing}"


def test_warning_sources_resolve():
    rule_ids = set()
    for sec in ("default_scopes", "quality_expectations", "totals_rules", "member_set_rules"):
        rule_ids |= set(by_id(sec))
    bad = [w["id"] for w in C["warning_codes"] if w["raised_by"] not in rule_ids]
    assert not bad, f"warnings raised by an unknown rule: {bad}"


def test_columns_exist_in_their_tables():
    cols = {t: {c["name"] for c in v["columns"]} for t, v in TABLES.items()}
    bad = []
    for t, v in TABLES.items():
        bad += [(t, g) for g in v["grain"] if g not in cols[t]]
    for r in C["relationships"]:
        bad += [(r["id"], c) for c in r["from_columns"] if c not in cols[r["from_table"]]]
        bad += [(r["id"], c) for c in r["to_columns"] if c not in cols[r["to_table"]]]
    for m in C["measures"]:
        bad += [(m["id"], c) for c in [m["time_column"]] + [x["column"] for x in m["columns"]] if c not in cols[m["table"]]]
    for a in C["attributes"]:
        bad += [(a["id"], c) for c in [a["column"], a.get("label_column")] if c and c not in cols[a["table"]]]
    for q in C["quality_expectations"]:
        bad += [(q["id"], c) for c in q.get("columns", []) if c not in cols[q["table"]]]
        bad += [(q["id"], c) for c in q.get("references_columns", []) if c not in cols[q["references_table"]]]
    p = C["analysis_periods"][0]
    bad += [(p["id"], p["source_column"])] if p["source_column"] not in cols[p["source_table"]] else []
    assert not bad, f"columns not declared in their table: {bad}"


def test_applicability_class_agrees_with_per_measure_effects():
    measure_type = {m["id"]: m["measure_type"] for m in C["measures"]}
    expected = {
        "CONFORMED": lambda t: "GROUP_AND_FILTER",
        "SNAPSHOT_ONLY": lambda t: "GROUP_AND_FILTER" if t == "SNAPSHOT" else "IGNORED",
        "NOT_APPLICABLE": lambda t: "REFUSED",
    }
    for a in C["attributes"]:
        effects = {x["measure"]: x["effect"] for x in a["applicability"]}
        assert set(effects) == set(measure_type), f"{a['id']} must declare every measure"
        for m, e in effects.items():
            assert e == expected[a["applicability_class"]](measure_type[m]), (a["id"], m, e)


def test_additivity_matches_measure_type():
    time = next(d["id"] for d in C["dimension_classes"] if d.get("is_time"))
    for m in C["measures"]:
        t = {a["dimension_class"]: a["aggregation"] for a in m["additivity"]}
        assert t[time] == {"SNAPSHOT": "SELECT_PERIOD", "FLOW": "SUM_OVER_WINDOW"}[m["measure_type"]], m["id"]


def test_measure_columns_cover_every_basis():
    bases = set(by_id("measure_bases"))
    for m in C["measures"]:
        assert {c["basis"] for c in m["columns"]} == bases, m["id"]


def test_basis_model_session_8c0():
    """Decisions 1 to 4 of session 8c-0: the result is in months on every basis; each basis is valid only where its
    sums stay comparable, judged on the rows returned; QTY_EQ by default, refused (never switched) elsewhere."""
    bm, bases = C["basis_model"], by_id("measure_bases")
    assert bm["result_unit"] == METRIC["output_unit"] == "months"
    assert {d["id"]: d["base_unit"] for d in bm["dimensions"]} == {"MASS": "kg", "VOLUME": "L"}
    assert {k: v["valid_when"] for k, v in bases.items()} == {
        "NATIVE": "ONE_ITEM_PER_ROW", "QTY_EQ": "ONE_DIMENSION_PER_ROW", "VALUE": "ALWAYS"}
    assert bm["default_basis"] == "QTY_EQ" and bm["validity_scope"] == "RETURNED_ROWS"
    assert bm["refusal"] == "BASIS_NOT_COMPARABLE"
    item = {c["name"] for c in next(t for t in C["tables"] if t["id"] == bm["item_table"])["columns"]}
    assert {bm[k] for k in ("item_key", "dimension_column", "base_unit_column", "native_unit_column",
                            "equivalence_factor_column")} <= item
    p = {x["id"]: x for x in C["parameters"]}
    assert "unit_variant" not in p and p["basis"]["allowed_values"] == list(bases)
    assert (p["basis"]["is_required"], p["basis"]["default_value"]) == (False, "QTY_EQ")
    r = by_id("refusal_codes")
    assert "UNIT_RAW_NOT_ADDITIVE" not in r and "UNIT_UNKNOWN" not in r and "BASIS_UNKNOWN" in r
    assert "always in months" in r["BASIS_NOT_COMPARABLE"]["reason_template"]
    assert {"{basis}", "{why}", "{allowed}"} <= set(re.findall(r"\{\w+\}", r["BASIS_NOT_COMPARABLE"]["reason_template"]))


def test_member_selection_session_8c0():
    """Decision 6 of session 8c-0: the procedure filters and ranks; NO_STOCK and NO_DEMAND come back apart."""
    sel = METRIC["member_selection"]
    p = {x["id"]: x for x in C["parameters"]}
    assert (sel["upper_bound_parameter"], sel["lower_bound_parameter"], sel["rank_parameter"]) == (
        "coverage_below", "coverage_above", "rank_first")
    assert (p["coverage_below"]["data_type"], p["coverage_above"]["data_type"], p["rank_first"]["data_type"]) == (
        "NUMBER", "NUMBER", "INTEGER")
    assert all(p[k]["exclusive_minimum"] == 0 and not p[k]["is_required"]
               for k in ("coverage_below", "coverage_above", "rank_first"))
    assert sel["set_apart_flags"] == ["NO_STOCK", "NO_DEMAND"]
    assert "0 < coverage_months <= coverage_below" in sel["upper_bound_rule"]
    assert "never summed or averaged" in sel["summary_rule"]


def stockout_month(as_of: dt.date, coverage, flag):
    """The contract's exhaustion_period, read literally: t + ceil(coverage) months, none for its flags."""
    ep = METRIC["exhaustion_period"]
    assert ep["formula"] == "t + ceil(coverage_months) months"
    if coverage is None or flag in ep["none_for_flags"]:
        return None
    n = math.ceil(coverage)
    y, m = divmod(as_of.month - 1 + n, 12)
    return dt.date(as_of.year + y, m + 1, 1)


@pytest.mark.parametrize("coverage,flag,want", [
    (0.5, None, dt.date(2026, 7, 1)), (1.0, None, dt.date(2026, 7, 1)), (2.8, None, dt.date(2026, 9, 1)),
    (0.0, "NO_STOCK", dt.date(2026, 6, 1)), (50.0, "BEYOND_HORIZON", None), (None, "NO_DEMAND", None)])
def test_stockout_month_counts_from_the_month_after_the_analysis_month(coverage, flag, want):
    """The forecast window starts at t+1 (window_start_offset 1, DEFINITION.md section 1), so a coverage in
    (n - 1, n] runs out in month t+n: 0.5 and 1.0 from June 2026 both give July 2026."""
    assert METRIC["window_start_offset"] == 1
    assert stockout_month(dt.date(2026, 6, 1), coverage, flag) == want


def test_outcomes_are_ordered_and_codes_unique():
    orders = [o["order"] for o in METRIC["outcomes"]]
    assert orders == sorted(orders) and len(set(orders)) == len(orders)
    assert [o["condition"] for o in METRIC["outcomes"]] == [
        "SNAPSHOT_NULL_OR_ZERO", "DEPLETED_WITHIN_HORIZON", "NO_FLOW_IN_WINDOW", "BEYOND_HORIZON"]
    for sec in ("refusal_codes", "warning_codes", "flags", "quality_expectations", "invariants", "parameters"):
        ids = [e["id"] for e in C[sec]]
        assert len(ids) == len(set(ids)), sec
    orders = [r["check_order"] for r in C["refusal_codes"]]
    assert len(orders) == len(set(orders)), "two refusals share a check_order"


def test_list_and_map_parameters_travel_as_json_strings():
    """Decision 7: an ARRAY argument is rejected on a warehouse custom tool (measured in C0)."""
    for p in C["parameters"]:
        if p["data_type"] in ("PERIOD_LIST", "ATTRIBUTE_LIST", "FILTER_MAP", "GRAIN_LIST"):
            assert p["encoding"] == "JSON_STRING", p["id"]


def test_c0_measured_refusals_are_in_the_contract():
    measured = {"AS_OF_MISSING", "AS_OF_NOT_MONTH_START", "AS_OF_INVALID", "AS_OF_NO_SNAPSHOT",
                "UNIT_RAW_NOT_ADDITIVE", "ATTRIBUTE_UNCLASSIFIED", "ATTRIBUTE_UNKNOWN", "GRAIN_EMPTY"}
    implemented = {"UNIT_UNKNOWN", "GRAIN_MALFORMED", "GRAIN_DUPLICATE", "FILTERS_MALFORMED", "FILTER_VALUES_INVALID",
                   "MASTER_DATA_FANOUT", "HORIZON_NOT_LOADED"}
    src = (ROOT / "snowflake" / "probe_c0" / "10_stock_coverage_probe.sql").read_text()
    assert implemented | measured == set(re.findall(r'refuse\("([A-Z_]+)"', src)), "C0 code set changed"
    # Contract 0.5.0 (session 8c-0): the two unit codes of C0 are gone: raw units are the NATIVE basis, judged on the
    # rows returned (BASIS_NOT_COMPARABLE), and UNIT_UNKNOWN is BASIS_UNKNOWN.
    retired = {"UNIT_RAW_NOT_ADDITIVE", "UNIT_UNKNOWN"}
    r = by_id("refusal_codes")
    assert not retired & set(r)
    assert {k for k, v in r.items() if v["evidence"] == "MEASURED"} == measured - retired
    assert {k for k, v in r.items() if v["evidence"] == "IMPLEMENTED"} == implemented - retired


def test_decisions_are_encoded():
    bh = METRIC["beyond_horizon"]                                                    # decision 1
    assert (bh["method"], bh["average_window"], bh["exclude_zero_periods"], bh["flag"]) == (
        "SNAPSHOT_OVER_MEAN_FLOW", "HORIZON", True, "BEYOND_HORIZON")
    o = {x["condition"]: x for x in METRIC["outcomes"]}                              # decision 2
    assert (o["SNAPSHOT_NULL_OR_ZERO"]["result"], o["SNAPSHOT_NULL_OR_ZERO"]["keeps_member"]) == ("0", True)
    assert (o["NO_FLOW_IN_WINDOW"]["result"], o["NO_FLOW_IN_WINDOW"]["flag"]) == ("null", "NO_DEMAND")
    m = C["member_set_rules"][0]                                                     # decision 3
    assert (m["method"], m["snapshot_members"], m["flow_members"]) == ("SPINE", "ALWAYS", "ONLY_ON_CONFORMED_GRAIN")
    assert C["totals_rules"][0]["total_over_time"] == "FORBIDDEN"                    # decision 4
    assert C["analysis_periods"][0]["series_allowed"] is True
    s = C["default_scopes"][0]                                                       # decision 5
    assert (s["attribute"], s["included_values"], s["lifted_by"]) == ("item_type", ["STANDARD"], "EXPLICIT_FILTER")
    assert s["applies_to_metrics"] == ["stock_coverage"]                             # a coverage rule (0.4.1):
    assert all(m.get("period_aggregation") is None or m["id"] in s["applies_to_measures"]  # not closing stock
               for m in C["measures"]) and not any(x["id"] == "closing_stock" for x in C["metrics"])
    assert ATTRS["lifecycle_status"]["applicability_class"] == "CONFORMED"           # decision 6
    p = C["analysis_periods"][0]                                                     # decision 8
    assert p["latest_token"] == "LATEST" and {"TOOL_DESCRIPTION", "PROCEDURE_RESPONSE"} <= set(p["exposed_in"])


def test_snapshot_measures_declare_a_period_aggregation():
    """Decision 1 of session 6: a snapshot over a period is its last month, never a sum, an average or a carry."""
    for m in C["measures"]:
        pa = m.get("period_aggregation")
        if m["measure_type"] == "SNAPSHOT":
            assert pa and pa["method"] == "LAST_PERIOD" and pa["missing_value"] == "0", m["id"]
            assert pa["member_set"] == "ANY_SNAPSHOT_IN_PERIOD"
            assert {"SUM", "AVERAGE", "LAST_NON_EMPTY"} <= set(pa["forbidden_methods"])
            assert pa["method"] not in pa["forbidden_methods"]
        else:
            assert pa is None, m["id"]


def test_in_call_quality_checks_are_scoped_and_coded():
    """Every expectation the procedure checks has a call scope and the code it raises (decision 3 of session 6)."""
    for q in C["quality_expectations"]:
        if q["on_failure"] == "MONITOR":
            continue
        assert q.get("call_scope"), q["id"]
        if q["on_failure"] in ("REFUSE", "REFUSE_IF_USED"):
            assert q.get("refusal"), q["id"]
        if q["on_failure"] in ("WARN", "REFUSE_IF_USED"):
            assert q.get("warning"), q["id"]
    qe = by_id("quality_expectations")
    assert qe["QE_FORECAST_DENSE"]["call_scope"] == "REQUEST_MEMBERS"
    assert qe["QE_HORIZON_LOADED"]["table"] == "DIM_CALENDAR" and qe["QE_FORECAST_REACH"]["table"] == "FCT_FORECAST"
    assert qe["QE_HORIZON_LOADED"]["refusal"] == qe["QE_FORECAST_REACH"]["refusal"] == "HORIZON_NOT_LOADED"


def test_alert_thresholds_are_tbd():
    assert {a["id"]: a["value"] for a in C["alert_thresholds"]} == {"ALERT_STOCKOUT": "TBD", "ALERT_EXPIRY": "TBD"}


# ================================================================================================ (ii) traceability

def _definition_traps() -> dict[str, str]:
    text = (ROOT / "docs" / "DEFINITION.md").read_text()
    sec = text[text.index("## 4."):text.index("## 5.")]
    return dict(re.findall(r"^\| (T\d) \| ([^|]+?) \|", sec, flags=re.M))


def _trap_ids() -> dict[str, str]:
    """trap id -> provenance. traps.yaml first, DEFINITION.md section 4 for the ones it lacks."""
    ids = {t["id"]: "data/traps.yaml" for t in TRAPS["traps"] + TRAPS["closing_stock"]}
    for t in _definition_traps():
        ids.setdefault(t, "docs/DEFINITION.md")
    return ids


def test_definition_lists_t1_to_t8():
    assert sorted(_definition_traps()) == [f"T{i}" for i in range(1, 9)]


def test_every_trap_is_prevented_by_a_contract_element():
    prevented: dict[str, list[str]] = {}
    for where, kind, fm in _refs():
        if kind == "failure_modes":
            prevented.setdefault(fm, []).append(where)
    gaps = {t: src for t, src in _trap_ids().items() if not prevented.get(t)}
    if gaps:
        print("TRACEABILITY GAPS:", gaps)
    assert not gaps, f"traps with no contract rule or quality expectation: {gaps}"


def test_failure_modes_record_their_provenance():
    fm = by_id("failure_modes")
    for t, src in _trap_ids().items():
        assert t in fm, f"{t} has no failure mode"
        assert fm[t]["source"].startswith(src), (t, fm[t]["source"], src)


def test_trap_flags_exist_in_the_contract():
    flags = set(by_id("flags"))
    assert {t["expected_flag"] for t in TRAPS["traps"] if t.get("expected_flag")} <= flags


def _questions() -> list[tuple[str, dict]]:
    out = [(t["id"], t) for t in TRAPS["traps"]]
    out += [(f"{t['id']} refusal question", q) for t in TRAPS["traps"] for q in t.get("refusal_questions", [])]
    return out + [(c["id"], c) for c in TRAPS.get("closing_stock", [])]


def test_trap_query_attributes_are_contract_attributes():
    for tid, t in _questions():
        used = set(t["query"]["grain"]) | set(t["query"]["filters"])
        assert used <= set(ATTRS), (tid, used - set(ATTRS))


def test_refusal_traps_expect_contract_refusal_codes():
    """Refusal traps carry a code, never a value; the code exists. T5 asks for the item's own unit across items and
    DIM_MIX for kg and L added: both are refused by the basis model, with the bases allowed."""
    refusing = [(tid, t) for tid, t in _questions() if "expected_refusal" in t]
    assert {tid for tid, _ in refusing} == {"T5", "T6", "T7 refusal question", "DIM_MIX"}
    for tid, t in refusing:
        assert t["expected_refusal"] in by_id("refusal_codes") and "expected" not in t, tid
    for tid, basis in (("T5", "NATIVE"), ("DIM_MIX", "QTY_EQ")):
        t = trap(tid)
        assert t["query"]["basis"] == basis and t["expected_refusal"] == C["basis_model"]["refusal"], tid
        assert basis not in t["expected_allowed_bases"] and "VALUE" in t["expected_allowed_bases"], tid


# ================================================================================================ (iii) formula check

def test_check_coverage_formula_still_passes_7_of_7():
    r = run(sys.executable, "docs/check_coverage_formula.py")
    assert r.returncode == 0, r.stdout + r.stderr
    rows = dict(re.findall(r"^(\w+)\s+LEGACY=\s*(\S+)\s+SQL=\s*\S+\s+OK$", r.stdout, flags=re.M))
    assert rows == {"worked_example": "8.5", "exact_depletion": "3.0", "zero_month_before": "3.5",
                    "zero_stock": "0.0", "beyond_horizon": "100.0", "no_demand": "None",
                    "forecast_no_stock": "0.0"}, r.stdout
    assert "T8 member lost, as expected" in r.stdout and r.stdout.strip().endswith("ALL OK")


# ================================================================================================ numbers

def coverage_from_contract(stock: float | None, fc_by_k: dict[int, float]) -> tuple[float | None, str | None]:
    """Minimal evaluator driven only by the contract's parameters. fc_by_k: month offset k -> forecast (sparse)."""
    h, k0 = METRIC["horizon_periods"], METRIC["window_start_offset"]
    window = [fc_by_k.get(k, 0.0) for k in range(k0, k0 + h)]          # densify: a missing month is 0
    for o in METRIC["outcomes"]:
        cond = o["condition"]
        if cond == "SNAPSHOT_NULL_OR_ZERO" and not stock:
            return 0.0, o["flag"]
        if cond == "DEPLETED_WITHIN_HORIZON":
            cum = 0.0
            for n, f in enumerate(window, start=1):
                if stock <= cum + f:
                    return (n - 1) + (stock - cum) / f, None
                cum += f
        if cond == "NO_FLOW_IN_WINDOW" and sum(window) == 0:
            return None, o["flag"]
        if cond == "BEYOND_HORIZON":
            bh = METRIC["beyond_horizon"]
            scope = window if bh["average_window"] == "HORIZON" else [v for k, v in sorted(fc_by_k.items()) if k >= k0]
            nz = [v for v in scope if v != 0] if bh["exclude_zero_periods"] else scope
            return stock / (sum(nz) / len(nz)), bh["flag"]
    raise AssertionError("no outcome matched")


def hero(sku: str) -> dict:
    return next(h for h in TRAPS["hero_items"] if h["sku"] == sku)


def hero_forecast(h: dict) -> dict[int, float]:
    f = h["forecast"]
    if f.get("none"):
        return {}
    if "series" in f:
        out = {0: f["k0"]} | {k: v for k, v in enumerate(f["series"], start=1)}
        out |= {k: f["then_flat"] for k in range(len(f["series"]) + 1, 40)}
        return out
    out = {k: f["flat"] for k in range(0, 25) if k not in f.get("missing_k", [])}
    out |= {k: f["beyond_h_flat"] for k in range(25, 37)} if "beyond_h_flat" in f else {}
    return out


def trap(tid: str) -> dict:
    return next(t for t in TRAPS["traps"] if t["id"] == tid)


@pytest.mark.parametrize("tid,sku,flag", [("T2", "SKU-H03", None), ("T4", "SKU-H05", None), ("T8", "SKU-H08", "NO_STOCK"),
                                          ("NO_DEMAND", "SKU-H09", "NO_DEMAND"), ("BEYOND_H", "SKU-H10", "BEYOND_HORIZON")])
def test_contract_parameters_give_the_trap_values(tid, sku, flag):
    """Single-SKU heroes: the value follows from traps.yaml numbers and the contract's parameters alone."""
    h = hero(sku)
    stock = sum(s["qty_eq"] for s in h["stock_at_as_of"]) or None
    value, got_flag = coverage_from_contract(stock, hero_forecast(h))
    expected = trap(tid)["expected"]
    if expected is None:
        assert value is None
    else:
        assert value == pytest.approx(expected)
    assert got_flag == flag == trap(tid).get("expected_flag", flag)


def test_t9_stock_is_read_at_the_analysis_month():
    """T9: the snapshot at exactly k = 0 (absent = 0) gives 0 NO_STOCK; carrying k = -1 forward gives the wrong value."""
    h = hero("SKU-H11")
    by_k = {int(k): v for k, v in h["stock_by_k"].items()}
    value, flag = coverage_from_contract(by_k.get(0) or None, hero_forecast(h))
    assert value == pytest.approx(trap("T9")["expected"]) and flag == trap("T9")["expected_flag"]
    last_known = by_k[max(k for k in by_k if k < 0)]
    wrong, _ = coverage_from_contract(last_known, hero_forecast(h))
    assert wrong == pytest.approx(trap("T9")["wrong"]["last_known_stock_over_forecast"])


def test_contract_parameters_give_the_definition_worked_example():
    fc = {k: v for k, v in enumerate([120, 90, 150, 110, 130, 100, 140, 80, 160], start=1)}
    assert coverage_from_contract(1000, fc) == (pytest.approx(8.5), None)


def test_rejected_choices_give_the_documented_wrong_values():
    """Flipping one contract choice reproduces the wrong value traps.yaml documents, so each choice is load-bearing."""
    global METRIC
    saved = METRIC
    try:
        METRIC = {**saved, "beyond_horizon": {**saved["beyond_horizon"], "average_window": "FULL_RANGE"}}
        v, _ = coverage_from_contract(5000, hero_forecast(hero("SKU-H10")))
        assert v == pytest.approx(trap("BEYOND_H")["wrong"]["average_over_full_forecast_range"])
        METRIC = {**saved, "window_start_offset": 0}
        v, _ = coverage_from_contract(1000, hero_forecast(hero("SKU-H05")))
        assert v == pytest.approx(trap("T4")["wrong"]["window_starts_at_as_of"])
    finally:
        METRIC = saved


# ================================================================================================ closing stock

PERIOD_RULE = MEASURES["stock_on_hand"]["period_aggregation"]


def closing_from_contract(stock_by_k: dict[int, float], period: list[int], method: str | None = None) -> float | None:
    """One member's value over the period [first k, last k], by the contract's rule. None: not a member."""
    method = method or PERIOD_RULE["method"]
    ks = range(period[0], period[1] + 1)
    present = {k: stock_by_k[k] for k in ks if k in stock_by_k}
    if not present:
        return None                                           # ANY_SNAPSHOT_IN_PERIOD: no snapshot, no member
    if method == "LAST_PERIOD":
        return float(stock_by_k.get(period[1], float(PERIOD_RULE["missing_value"])))
    if method == "LAST_NON_EMPTY":
        return float(present[max(present)])
    if method == "SUM":
        return float(sum(present.values()))
    if method == "AVERAGE":
        return sum(present.values()) / len(ks)
    raise AssertionError(method)


def _closing(cid: str, method: str | None = None) -> float:
    c = next(x for x in TRAPS["closing_stock"] if x["id"] == cid)
    f = c["query"]["filters"]
    members = [h for h in TRAPS["hero_items"] if "stock_by_k" in h and h["country"] == f["country_code"]
               and (h["sku"] == f.get("sku_code") or h["family"]["code"] == f.get("family_code"))]
    vals = [closing_from_contract({int(k): v for k, v in h["stock_by_k"].items()}, c["query"]["period_k"], method)
            for h in members]
    return sum(v for v in vals if v is not None)


@pytest.mark.parametrize("cid", ["CS_LAST_MONTH_GAP", "CS_MIDDLE_MONTH_GAP", "CS_FAMILY"])
def test_contract_period_rule_gives_the_closing_stock_values(cid):
    c = next(x for x in TRAPS["closing_stock"] if x["id"] == cid)
    assert _closing(cid) == pytest.approx(c["expected"])


def test_forbidden_period_methods_give_the_documented_wrong_values():
    """Each forbidden method reproduces a wrong value of traps.yaml, so the rule is load-bearing."""
    wrong = {x["id"]: x["wrong"] for x in TRAPS["closing_stock"]}
    assert _closing("CS_LAST_MONTH_GAP", "LAST_NON_EMPTY") == pytest.approx(wrong["CS_LAST_MONTH_GAP"]["last_known_value"])
    assert _closing("CS_FAMILY", "LAST_NON_EMPTY") == pytest.approx(wrong["CS_FAMILY"]["last_known_value_per_sku"])
    for cid, w in wrong.items():
        assert _closing(cid, "SUM") == pytest.approx(w["sum_over_period"])
        assert _closing(cid, "AVERAGE") == pytest.approx(w["average_over_period"])


GRAIN_RULE = ("The grain follows the question. A question that asks for a list of products or items takes items as grain: "
              "with a country named, sku_code filtered on that country; worldwide or with no country, sku_code; for item "
              "and country pairs, sku_code and country_code. A question that asks for one figure for a scope (a country, a "
              "family, a region) takes that scope's grain and its filters, with no item rows and no grand total unless the "
              "question asks for them.")


def test_grain_rule_is_the_owners_text_everywhere():
    """Session 8c-0 step 7a, contract 0.5.1 (owner's text, verbatim): in the contract, C's generated instructions,
    DEFINITION.md section 1 (A, D, D' by extraction) and B1's hand-written instructions."""
    assert " ".join(METRIC["member_selection"]["grain_rule"].split()) == GRAIN_RULE
    flat = lambda p: " ".join((ROOT / p).read_text().split())   # noqa: E731
    for p in ("docs/DEFINITION.md",):
        assert GRAIN_RULE in flat(p), p
    # Session 8c (charter version 11): B2's generated instructions, which this list missed
    for p in ("generated/agent_c.yaml", "generated/agent_b2.yaml", "snowflake/phase4_others/b1/agent_b1.yaml",
              "snowflake/phase4_others/a/agent_a.yaml",
              "snowflake/phase4_others/d/agent_d.yaml", "snowflake/phase4_others/d/agent_dp.yaml"):
        s = yaml.safe_load((ROOT / p).read_text())
        assert GRAIN_RULE in " ".join(s["instructions"]["orchestration"].split()), p
        assert "a country named gives sku_code" not in s["instructions"]["orchestration"], p
