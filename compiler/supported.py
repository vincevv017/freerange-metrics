"""
Keys of the metamodel that the compiler does not read (session 11c, owner). The generated SQL and specifications are
written for one value of each; a contract holding another value would get the same objects silently. Each generator
that writes a key's behaviour calls check(contract, "<generator>") before anything else and fails closed:
"<key>: only <value> is supported by this compiler".

FIXED lists those keys, the value supported and the generators that write their behaviour. DOCUMENTATION_ONLY lists
the keys that carry no behaviour (a table's kind, a column's nullability, an invariant's statement) or that describe
the fixed SQL in the instance's own words (the member selection's rules, the stock-out formula): they are not checked.
compiler/gen_reference.py marks both in docs/reference/metamodel.md; tests/test_supported.py holds the list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

PROCEDURE, NATIVE, CLOSING, DMF, AGENT = "gen_procedure", "gen_native_sv", "gen_closing_sv", "gen_dmf", "gen_agent"
CLOSING_PROC, CRAW = "gen_closing_procedure", "gen_craw"     # session 13, configuration C-raw
DEPLETION = (PROCEDURE, NATIVE)


def _outcomes(raw: list[dict]) -> list[dict]:
    return [{"order": o.get("order"), "condition": o.get("condition"), "result": o.get("result"),
             "keeps_member": o.get("keeps_member")} for o in raw]


@dataclass(frozen=True)
class Fixed:
    key: str                                  # Class.attribute of the metamodel
    path: tuple[str, ...]                     # contract path; "*" walks a list, naming each element by its id
    value: Any                                # the value supported, or a function of the contract
    generators: tuple[str, ...]
    text: str | None = None                   # how the value reads in the error, when not the value itself
    project: Callable | None = field(default=None, compare=False)   # the part of a raw value compared
    absent: bool = False                      # True: a missing key is located too (its value is None)

    def expected(self, c: dict) -> Any:
        return self.value(c) if callable(self.value) else self.value

    def shown(self, c: dict) -> str:
        if self.text:
            return self.text
        v = self.expected(c)
        if isinstance(v, bool):
            return str(v).lower()
        if isinstance(v, list):
            return ", ".join(map(str, v))
        return str(v)

    def locate(self, c: dict) -> Iterator[tuple[str, Any, Callable[[Any], None]]]:
        """(where, value, setter) for each place of the contract that holds the key."""
        def walk(node, path, where):
            head, rest = path[0], path[1:]
            if head == "*":
                for e in node or []:
                    yield from walk(e, rest, f"{where}.{e.get('id')}")
                return
            if not isinstance(node, dict):
                return
            if not rest:
                if head in node or self.absent:
                    raw = node.get(head)
                    value = self.project(raw) if self.project and raw is not None else raw

                    def setter(v, node=node, head=head):
                        node[head] = v
                    yield f"{where}.{head}".lstrip("."), value, setter
                return
            if head in node:
                yield from walk(node[head], rest, f"{where}.{head}")
        yield from walk(c, self.path, "")


FIXED: list[Fixed] = [
    Fixed("Measure.time_grain", ("measures", "*", "time_grain"), "MONTH", (PROCEDURE, CLOSING, NATIVE, DMF, CLOSING_PROC, CRAW)),
    Fixed("PeriodAggregation.member_set", ("measures", "*", "period_aggregation", "member_set"),
          "ANY_SNAPSHOT_IN_PERIOD", (CLOSING, NATIVE, CLOSING_PROC)),
    Fixed("BasisModel.validity_scope", ("basis_model", "validity_scope"), "RETURNED_ROWS", (PROCEDURE, CLOSING_PROC)),
    Fixed("DepletionMetric.time_grain", ("metrics", "*", "time_grain"), "MONTH", (PROCEDURE, NATIVE, DMF)),
    Fixed("DepletionMetric.output_unit", ("metrics", "*", "output_unit"), "months", DEPLETION),
    Fixed("DepletionMetric.anchor_parameter", ("metrics", "*", "anchor_parameter"), "as_of_months", (PROCEDURE, AGENT)),
    Fixed("DepletionMetric.interpolation", ("metrics", "*", "interpolation"), "LINEAR", DEPLETION),
    Fixed("DepletionMetric.densify_missing_periods", ("metrics", "*", "densify_missing_periods"), True, DEPLETION),
    Fixed("DepletionMetric.aggregate_before_compute", ("metrics", "*", "aggregate_before_compute"), True, DEPLETION),
    Fixed("DepletionMetric.time_filter_on_flow", ("metrics", "*", "time_filter_on_flow"), "SELECTS_ANCHOR_ONLY", DEPLETION),
    Fixed("DepletionMetric.outcomes", ("metrics", "*", "outcomes"), [
        {"order": 1, "condition": "SNAPSHOT_NULL_OR_ZERO", "result": "0", "keeps_member": True},
        {"order": 2, "condition": "DEPLETED_WITHIN_HORIZON",
         "result": "(n - 1) + (S - C(n-1)) / f(n), n = first period in 1..H with S <= C(n)", "keeps_member": None},
        {"order": 3, "condition": "NO_FLOW_IN_WINDOW", "result": "null", "keeps_member": True},
        {"order": 4, "condition": "BEYOND_HORIZON", "result": "S / mean(f(i) for i in 1..H if f(i) > 0)",
         "keeps_member": None},
    ], DEPLETION, text="the four outcomes SNAPSHOT_NULL_OR_ZERO (0, member kept), DEPLETED_WITHIN_HORIZON (linear), "
                       "NO_FLOW_IN_WINDOW (null, member kept), BEYOND_HORIZON (mean non-zero flow), in this order",
          project=_outcomes),
    Fixed("BeyondHorizonRule.method", ("metrics", "*", "beyond_horizon", "method"), "SNAPSHOT_OVER_MEAN_FLOW", DEPLETION),
    Fixed("BeyondHorizonRule.average_window", ("metrics", "*", "beyond_horizon", "average_window"), "HORIZON", DEPLETION),
    Fixed("BeyondHorizonRule.exclude_zero_periods", ("metrics", "*", "beyond_horizon", "exclude_zero_periods"), True,
          DEPLETION),
    Fixed("TotalsRule.method", ("totals_rules", "*", "method"), "RECOMPUTE", (PROCEDURE, CLOSING_PROC)),
    Fixed("TotalsRule.snapshot_aggregation", ("totals_rules", "*", "snapshot_aggregation"), "TOTAL_GRAIN", (PROCEDURE, CLOSING_PROC)),
    Fixed("TotalsRule.flow_aggregation", ("totals_rules", "*", "flow_aggregation"), "CONFORMED_PROJECTION", (PROCEDURE,)),
    Fixed("TotalsRule.total_over_time", ("totals_rules", "*", "total_over_time"), "FORBIDDEN", (PROCEDURE, CLOSING_PROC)),
    Fixed("MemberSetRule.method", ("member_set_rules", "*", "method"), "SPINE", (PROCEDURE,)),
    Fixed("MemberSetRule.snapshot_members", ("member_set_rules", "*", "snapshot_members"), "ALWAYS", (PROCEDURE,)),
    Fixed("DefaultScope.lifted_by", ("default_scopes", "*", "lifted_by"), "EXPLICIT_FILTER", (PROCEDURE,)),
    Fixed("AnalysisPeriods.series_allowed", ("analysis_periods", "*", "series_allowed"), True, (PROCEDURE, CLOSING_PROC)),
    Fixed("Parameter.min_items", ("parameters", "*", "min_items"), 1, (PROCEDURE,)),
    Fixed("Parameter.max_items", ("parameters", "*", "max_items"), lambda c: c["analysis_periods"][0]["max_periods"],
          (PROCEDURE,), text="the analysis periods' max_periods"),
    Fixed("Parameter.allowed_values", ("parameters", "*", "allowed_values"),
          lambda c: [b["id"] for b in c["measure_bases"]], (PROCEDURE,), text="the ids of measure_bases, in order"),
    Fixed("QualityExpectation.schedule", ("quality_expectations", "*", "schedule"), None, (DMF,),
          text="no schedule", absent=True),
]

DOCUMENTATION_ONLY: dict[str, str] = {
    "OpenDecision.blocking": "documentation: no release gate is implemented",
    "Table.kind": "documentation",
    "Column.nullable": "documentation: missing values are checked by quality expectations",
    "MeasureBasis.kind": "documentation: the procedure reads valid_when and unit_source",
    "AnalysisPeriods.exposed_in": "documentation: the agent's specification and every answer carry the valid months",
    "CalculationInvariant.statement": "documentation: tests/test_procedure.py checks several invariants",
    "AlertThreshold.raises_flag": "documentation: alert thresholds are not compiled",
    "ExhaustionPeriodRule.formula": "documentation of the procedure's SQL (t + ceil(coverage) months)",
    "MemberSelection.upper_bound_rule": "documentation of the procedure's SQL",
    "MemberSelection.lower_bound_rule": "documentation of the procedure's SQL",
    "MemberSelection.rank_rule": "documentation of the procedure's SQL",
    "MemberSelection.summary_rule": "documentation of the procedure's SQL",
}


def check(contract: dict, generator: str) -> None:
    """Fail closed: raise ValueError on the first fixed key, written by this generator, that holds another value."""
    for e in FIXED:
        if generator not in e.generators:
            continue
        expected = e.expected(contract)
        for where, value, _ in e.locate(contract):
            if value != expected:
                raise ValueError(f"{where}: only {e.shown(contract)} is supported by this compiler")
