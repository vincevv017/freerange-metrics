# The contract

Two files define stock coverage, and nothing else does. `contract/metamodel.yaml` is a LinkML schema of the
vocabulary: generic, nothing in it names stock. `contract/stock_coverage.yaml` is the stock coverage instance of that
vocabulary. It is the only hand-written source. Phase 3 compiles it into every runtime object. Phase 2 generates
from it the schema module that the loader and the checks import (`compiler/gen_schema.py` writes
`generated/schema.py`, which replaced the hand-written `data/schema_v0.py`).

Check it:

```bash
.venv/bin/linkml-validate -s contract/metamodel.yaml -C MetricContract contract/stock_coverage.yaml
.venv/bin/python compiler/gen_schema.py   # regenerate generated/schema.py after a contract change
.venv/bin/python compiler/gen_dmf.py      # regenerate generated/dmf.sql (data metric functions)
.venv/bin/python compiler/gen_procedure.py        # generated/stock_coverage_procedure.sql
.venv/bin/python compiler/gen_closing_sv.py       # generated/closing_stock_sv.sql
.venv/bin/python compiler/gen_questions.py        # generated/reference_questions.yaml
.venv/bin/python compiler/gen_agent.py            # generated/agent_c.yaml
.venv/bin/python -m pytest                 # validity, references, drift of generated/, trap traceability, numbers
```

`linkml-validate` checks shapes and enum values. It does not check references between elements (a `prevents: [T99]`
passes), so `tests/test_contract.py` resolves every reference.

## How to read it

Read the instance top-down. Each section answers one question. Every key is described in
[reference/metamodel.md](reference/metamodel.md), generated from the metamodel.

1. **Who and which version.** `ownership` names roles, never people. Each release adds a `version`, an
   `effective_date` and a `changes` entry.
2. **What the data is.** `tables` gives columns, types and the declared grain. Uniqueness of that grain is a quality
   expectation, never an assumption. `relationships` gives the join paths and their cardinality.
3. **What the numbers are.** `measures` are typed SNAPSHOT (a level, selected at one month, never summed over time) or
   FLOW (an amount per month, summed over a window). Additivity is declared once per dimension class. A SNAPSHOT
   measure also declares its `period_aggregation`: over a period (a month range, a quarter, a year) it is the
   snapshot of the period's last month; a member with a snapshot in the period and none in its last month closes at
   0 and keeps its row; summing, averaging and carrying a value forward are listed as forbidden methods (closing
   stock, contract 0.2.0).
4. **What a user can slice by.** Each entry in `attributes` declares an applicability class and, per measure, its
   effect. CONFORMED attributes group and filter stock and forecast alike. SNAPSHOT_ONLY attributes (called stock-only
   in DEFINITION.md) group and filter the stock only, and the forecast stays at the parent conformed grain. An
   undeclared attribute cannot be used.
5. **On which basis.** The result of the metric is always in months (`basis_model.result_unit`). `measure_bases`
   lists where stock and forecast are measured before the ratio: NATIVE (each item in its own unit, valid for one item
   per row), QTY_EQ (kg or L equivalent, valid for items of one dimension, the default) and VALUE (EUR, always valid).
   `basis_model` says where each item's dimension and units are read (DIM_ITEM: `dimension`, `base_unit`, `raw_unit`,
   `qty_eq_factor`) and that validity is judged on the rows and totals a call returns: a basis that is not comparable
   there is refused (`BASIS_NOT_COMPARABLE`, naming the bases allowed), never switched (contract 0.5.0).
6. **How the number is computed.** `metrics` holds the depletion pattern: anchor, window `t+1..t+24`, densification,
   aggregate-then-compute, outcomes evaluated in order, and the beyond-horizon rule. `exhaustion_period` gives each
   row's stockout month (t + ceil(coverage)); `member_selection` keeps detail rows by coverage (`coverage_below`,
   `coverage_above`, `rank_first`), sets NO_STOCK and NO_DEMAND members apart and sums the kept stock per unit.
7. **What an answer contains.** `totals_rules` sets totals by recomputation and forbids a total over time.
   `member_set_rules` sets the spine. `default_scopes` sets BULK excluded from coverage unless filtered (never from closing stock). `analysis_periods` sets
   which months exist and where they are shown.
8. **How a caller asks.** `parameters` gives the tool surface: lists and maps travel as JSON strings. `refusal_codes`
   lists refusals in check order, each tagged MEASURED (C0), IMPLEMENTED (C0, not exercised) or DECIDED (new).
9. **When to trust it.** `quality_expectations` sets on each failure whether to refuse, refuse only if the query uses
   the affected columns, warn in the answer, or only monitor. `call_scope` says which rows the procedure checks again
   at call time: the whole table, the members of the request, or the rows the request reads. A warning is raised
   only when the answer reads the faulty rows (377 forecast gaps on the table, 2 for the T2 question). `invariants` are properties every correct result
   satisfies. `alert_thresholds` are for article 2, with values TBD.
10. **Why each rule exists.** `failure_modes` holds the traps T1 to T8, NO_DEMAND, BEYOND_H and BULK_SCOPE, each with
    its source. An element's `prevents` names the traps it guards against. A trap that nothing prevents is a gap,
    and the tests fail on it. All 16 failure modes, with the elements that prevent each and its trap:
    [reference/failure_modes.md](reference/failure_modes.md).

`open_decisions` lists choices the contract had to make that the owner has not confirmed. `docs/phase1_notes.md`
gives their reasons.

## What Phase 2 generates

- `generated/schema.py` (`compiler/gen_schema.py`): tables, columns, declared grains, attribute classes, unit
  variants and refused units, imported by the loader and the checks.
- `generated/dmf.sql` (`compiler/gen_dmf.py`): one custom data metric function per CUSTOM quality expectation and one
  ad hoc check per expectation and column, run once by `snowflake/phase2_dmf/run_dmf.py`; nothing attached, no
  schedule. Results and the call forms the account accepts: `snowflake/phase2_dmf/results.md`.

`tests/test_generated.py` regenerates both into a temporary folder and fails on any byte of difference. The traps
in `data/traps.yaml` reference the contract (refusal codes, failure modes, attributes), the closing-stock traps of
step 1 included since 0.2.0: `CS_LAST_MONTH_GAP`, `CS_MIDDLE_MONTH_GAP` and `CS_FAMILY` are failure modes prevented by
the stock measure's `period_aggregation`, and `tests/test_contract.py` recomputes their values from that rule.

## What Phase 3 and Phase 4 generate

The contract is at version 0.5.0 (the basis model, the member selection and the stockout month, session 8c-0); 0.4.2 named the
conflicting values in `MASTER_DATA_FANOUT`; 0.4.1 is described here: 0.2.1 added failure mode T9 (stale stock in coverage), 0.3.0 changed the condition
of `QE_FORECAST_DENSE` to the horizon window of LATEST, 0.3.1 made the `MASTER_DATA_FANOUT` reason name only the
attributes that differ, 0.4.0 replaced the SQL text and the month list in the procedure answer by the query ids of
its statements and the first, last and LATEST valid months, 0.4.1 named the metric the default scope applies to
(coverage only, never closing stock; metamodel 0.3.0 adds `applies_to_metrics`). `changes` in the contract lists every version.

- `generated/stock_coverage_procedure.sql` (`compiler/gen_procedure.py`, handler template
  `compiler/procedure_handler.py`): `LINKML_METRICS.RAW.STOCK_COVERAGE`. Parameters from `parameters`; refusals run in
  `check_order` with their `reason_template`; attributes routed by applicability class; member spine; default scope;
  the set-based SQL of DEFINITION.md section 5 with totals recomputed per `totals_rules`; the in-call quality checks
  of every expectation that is not MONITOR, at its `call_scope`. The generator fails when the contract and the
  handler disagree (a code without a check, an order that breaks a prerequisite, an expectation without SQL). The
  answer carries `lineage.query_ids` (context, quality, coverage): the SQL of each is read back from query history.
  Checked on numbers by `tests/test_procedure.py`; evidence in `snowflake/phase3_procedure/results.md`.
- `generated/closing_stock_sv.sql` (`compiler/gen_closing_sv.py`): closing stock, the stock measure's
  `period_aggregation`. A gap-filled snapshot view `FCT_STOCK_SNAPSHOT_GAPFILLED` (one row per key and month up to
  the month after its last snapshot, 0 where absent, the contract's `missing_value`) and the semantic view
  `CLOSING_STOCK_SV` (stock `NON ADDITIVE BY` the snapshot month, the `periods` as dimensions, one metric per allowed
  unit). Evidence: `snowflake/probe_closing/results.md`.
- `generated/reference_questions.yaml` (`compiler/gen_questions.py`): one question per `failure_modes` entry, the
  refusal questions of `data/traps.yaml` and a drill, in grocery wording, each with its expected answer and the tool
  parameters that produce it. `tests/test_procedure.py` asserts every expected answer against the procedure.
- `generated/agent_c.yaml` (`compiler/gen_agent.py`): the `CREATE AGENT` specification of agent C, one `generic`
  tool bound to the procedure. Its description, `input_schema` and instructions come from `metrics`,
  `totals_rules`, `flags`, `unit_variants`, `forbidden_units`, `default_scopes`, `parameters` and `attributes`; the
  valid months and the codes with their names come from the loaded dataset. Evidence:
  `snowflake/phase4_agent_c/results.md`.

`tests/test_generated.py` regenerates every file of `generated/` and fails on any byte of difference.

## What each contract section feeds

| Contract section | Registry | Semantic view B2 | Procedure | Data metric functions | Agent tool spec | Reference questions |
|---|---|---|---|---|---|---|
| `ownership`, `version`, `changes` | header rows, lineage | comment | header comment | n/a | n/a | n/a |
| `tables`, `relationships` | table and join registry | tables, relationships | FROM and JOIN clauses | grain and referential DMFs | n/a | n/a |
| `measures` (type, additivity, columns) | measure registry | facts and metrics, `NON ADDITIVE BY` the time dimension for the snapshot | stock and forecast CTEs, unit columns | completeness and range DMFs | unit wording | one question per unit variant |
| `attributes` (class, effect per measure) | applicability registry | dimensions; spine and bridge per snapshot-only attribute | grain and filter validation; filters routed to stock or forecast | accepted-values DMFs | `grain` and `filters` descriptions, known values | one question per snapshot-only attribute (T3 type) |
| `measure_bases`, `basis_model` | basis registry | one metric family per basis that a view can expose (QTY_EQ, VALUE), dimension and base unit as item dimensions | `basis` validation, per-row item and dimension counts, `BASIS_NOT_COMPARABLE` on the rows returned, stock unit of each row | `qty_eq_factor` range DMF, `QE_ITEM_DIMENSION` | allowed values, the basis rule | a raw-unit question (T5), a kg and L question (DIM_MIX), one item in its own unit |
| `metrics` (depletion pattern, outcomes, beyond horizon) | metric registry | 24 cumulative metrics and CASE (B2 only) | the set-based SQL of DEFINITION.md §5, flags | n/a | description of flags | hero questions T2, T4, T8, NO_DEMAND, BEYOND_H |
| `totals_rules`, `member_set_rules` | rule registry | spine view | `totals` parameter, recomputed total rows, spine | n/a | "never add rows, ask a coarser grain" | one total check per hierarchy level (T1) |
| `default_scopes` | scope registry | default filter | default filter on the coverage metric's stock, DEFAULT_SCOPE_EXCLUDED warning | n/a | default and how to lift it | a family with BULK stock |
| `analysis_periods` | list of valid months, LATEST | month variable (if kept) | `as_of_months` resolution, first, last and LATEST in each answer | freshness DMF | LATEST and first/last valid month | a no-month question (T6), a series |
| `parameters`, `refusal_codes` | refusal catalogue | n/a | parsing, validation order, refusal JSON | n/a | `input_schema`, descriptions, examples | one question per refusal reached through the agent |
| `quality_expectations`, `warning_codes` | expectation catalogue | n/a | in-call checks (REFUSE, REFUSE_IF_USED, WARN), warnings in JSON | one DMF per expectation (generated in Phase 2, ad hoc); attach and schedule | "relay warnings with the number" | T7 question |
| `invariants` | n/a | n/a | property and metamorphic tests in CI | n/a | n/a | n/a |
| `failure_modes` | trap catalogue | n/a | n/a | n/a | n/a | the reference question of each trap, its expected value from the generated data |
| `alert_thresholds` | thresholds (TBD) | n/a | n/a (article 2) | n/a | n/a | n/a |
