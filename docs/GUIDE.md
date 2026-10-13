# How a metric contract works, and how to add one

This guide explains how a metric contract works through its one built metric, stock coverage, and says what it takes
to add another. `docs/CONTRACT.md` is the detailed reading guide of the contract; this guide links to it and does not
repeat it. Tags: **[measured]** (run, evidence in this repository), **[documented]** (the contract, the code or its
docstrings), **[inferred]** (reasoned, not run).

## 1. The idea

A metric is declared once, in a YAML contract on a LinkML metamodel (`contract/stock_coverage.yaml` on
`contract/metamodel.yaml`): its tables and grains, how each measure adds up, which attributes apply to which measure,
the algorithm, the parameters a caller may set, the refusals and warnings, the quality expectations and the known
ways to get it wrong. A compiler (`compiler/`) generates the Snowflake objects from it: a procedure that computes the
metric, semantic views for what native semantics can hold, data metric functions, and the agent's tool
specification. At question time the agent picks the parameters and calls the procedure; it never computes the
number. What the procedure cannot compute correctly, it refuses with a code and a reason; the refusals are part of
the contract, not of the agent's instructions [documented, the contract and `compiler/`].

## 2. Anatomy of a contract

Each excerpt below is quoted from `contract/stock_coverage.yaml` (version 0.5.1). The sections follow the file's
order. Every key is described in [reference/metamodel.md](reference/metamodel.md), generated from the metamodel, and
every failure mode, with its trap, in [reference/failure_modes.md](reference/failure_modes.md).

**Who answers for it, and which version.** Roles, never names; every release adds a version and a `changes` entry.

```yaml
version: 0.5.1
status: DRAFT
effective_date: "2026-10-05"
ownership:
  business_owner: Supply planning lead (role)
  technical_owner: Data platform engineer (role)
  data_steward: Master data steward (role)
```

**The physical model.** `tables` gives each table's columns, types and declared grain; uniqueness of a grain is a
quality expectation, never an assumption. `relationships` gives the join paths and their cardinality.

```yaml
  - id: FCT_FORECAST
    kind: FACT
    description: Monthly demand forecast per item and country. One forecast version (versioning is out of v1 scope).
    grain: [forecast_month, item_id, country_id]
```

**The measures.** A SNAPSHOT is a level at a point in time, a FLOW an amount per period. Additivity is declared once
per dimension class: the stock is selected at one month, never summed over months.

```yaml
  - id: stock_on_hand
    name: Stock on hand
    description: Closing stock of the month. A level, never summed over months.
    measure_type: SNAPSHOT
    table: FCT_STOCK_SNAPSHOT
    time_column: snapshot_month
    time_grain: MONTH
    additivity:
      - {dimension_class: TIME, aggregation: SELECT_PERIOD, note: "The analysis month selects the snapshot: read at exactly that month, absent = 0 (T9)."}
      - {dimension_class: PRODUCT, aggregation: SUM}
```

**The attributes.** Each attribute declares, per measure, whether it groups and filters it. A CONFORMED attribute
applies to stock and forecast alike; a SNAPSHOT_ONLY one restricts the stock and leaves the forecast at the conformed
grain. An attribute the contract does not declare cannot be used.

```yaml
  - id: batch_status
    table: DIM_BATCH
    column: batch_status
    dimension_class: BATCH
    applicability_class: SNAPSHOT_ONLY
    applicability: &snapshot_only
      - {measure: stock_on_hand, effect: GROUP_AND_FILTER}
      - {measure: demand_forecast, effect: IGNORED}
```

**The bases.** Where stock and forecast are measured before the ratio (the result is always in months), and where
each basis is valid. A basis that is not valid for the rows a call returns is refused, never switched.

```yaml
  - id: QTY_EQ
    kind: BASE_UNIT_EQUIVALENT
    unit_source: ITEM_BASE_UNIT
    valid_when: ONE_DIMENSION_PER_ROW
```

**The metric.** The depletion pattern: the snapshot at the anchor month against the flow of the following months,
aggregated to the requested grain before the algorithm runs; then the outcomes, evaluated in order, the
beyond-horizon rule, the stock-out month and the member selection.

```yaml
    snapshot_measure: stock_on_hand
    flow_measure: demand_forecast
    anchor_parameter: as_of_months
    time_grain: MONTH
    output_unit: months
    window_start_offset: 1
    horizon_periods: 24
    interpolation: LINEAR
    densify_missing_periods: true
    aggregate_before_compute: true
```

**The query rules.** A total is recomputed, never added; members are the union of stock and forecast members; a
default scope applies unless the caller lifts it explicitly, and the answer reports what it removed.

```yaml
    method: RECOMPUTE
    snapshot_aggregation: TOTAL_GRAIN
    flow_aggregation: CONFORMED_PROJECTION
    total_over_time: FORBIDDEN
```

**The tool surface.** `parameters` are what the agent may set (lists and maps travel as JSON strings), each with the
refusal codes it can raise; `refusal_codes` are checked in `check_order`, each with its reason template;
`warning_codes` are attached to an answer that is still given.

```yaml
  - {id: MASTER_DATA_FANOUT, check_order: 50, category: DATA_QUALITY, evidence: IMPLEMENTED, prevents: [T7],
     reason_template: "{count} item(s) have several rows in DIM_ITEM that differ on {attributes}; any number at this grain would be fanned out.",
```

**Trust.** Each quality expectation says what happens when it fails (refuse, refuse only if the query uses the
column, warn, or only monitor) and which rows the procedure checks again at call time (`call_scope`). Invariants
are properties every correct result satisfies.

```yaml
  - {id: QE_ITEM_GRAIN, kind: GRAIN_UNIQUENESS, table: DIM_ITEM, columns: [item_id],
     condition: "one row per item_id", threshold: "0", severity: ERROR, on_failure: REFUSE_IF_USED,
```

**Why each rule exists.** `failure_modes` are the traps: a known wrong behaviour, the correct one, its source and a
reference question. An element's `prevents` names the traps it guards against; a trap nothing prevents fails the
tests. The catalogue of the 16, with the elements that prevent each one: [reference/failure_modes.md](reference/failure_modes.md).

```yaml
  - {id: T1, name: "Ratio re-aggregation", source: "data/traps.yaml#T1",
     wrong_behaviour: "Sum or average of child coverages", correct_behaviour: "Recompute from aggregated S and f at each grain",
     reference_question: "Stock coverage of flour and baking in France at AS_OF"}
```

The contract holds 12 attributes, 3 bases, 8 parameters, 21 refusal codes, 5 warning codes, 28 quality expectations,
17 invariants and 16 failure modes [measured, counted in the file].

## 3. From contract to Snowflake

| Generated file | Generator | What it is |
|---|---|---|
| `generated/schema.py` | `gen_schema.py` | tables, columns, grains, attribute classes and bases, imported by the loader, the checks and the tests |
| `generated/dmf.sql` | `gen_dmf.py` | one custom data metric function per custom quality expectation (17), and one ad hoc check per expectation and column (36) |
| `generated/closing_stock_sv.sql` | `gen_closing_sv.py` | the gap-filled snapshot view `FCT_STOCK_SNAPSHOT_GAPFILLED` and the native semantic view `CLOSING_STOCK_SV` |
| `generated/closing_stock_procedure.sql` | `gen_closing_procedure.py` | `CLOSING_STOCK`, the SQL Scripting procedure C-raw calls for closing stock: the period rule at question time on the raw snapshot, no densified data |
| `generated/c_raw_sv.yaml`, `generated/agent_c_raw.yaml` | `gen_craw.py` | configuration C-raw: its semantic view on the raw tables (stock on hand, forecast; value grounding copied from B2's enriched view) and its agent (three tools) |
| `generated/stock_coverage_procedure_sql.sql` | `gen_procedure.py --target sql` | `STOCK_COVERAGE`, the SQL Scripting procedure agents C and C-raw call |
| `generated/stock_coverage_procedure.sql` | `gen_procedure.py --target python` | the Python target of the same procedure (`STOCK_COVERAGE_PY`), kept beside it |
| `generated/agent_c.yaml` | `gen_agent.py` | agent C's specification: instructions, tool descriptions, procedure binding |
| `generated/b2_native_views.sql`, `generated/b2_native_sv.yaml`, `generated/agent_b2.yaml` | `gen_native_sv.py` | configuration B2, the generated native baseline: forward spine, status bridge, item projection, its semantic view and agent |
| `generated/reference_questions.yaml` | `gen_questions.py` | the campaign's questions and expected answers, from the failure modes, `data/traps.yaml` and the dataset |

<!-- counts: generated/dmf.sql, counted -->

What holds them [measured, the offline suite]:
- **Drift.** `tests/test_generated.py` regenerates every file into a temporary folder and fails on any byte of
  difference: nothing in `generated/` is edited by hand. It also checks that `dmf.sql` covers every expectation and
  attaches no function to a table, that agent C's input schema matches the contract's parameters, and that every
  failure mode has a reference question.
- **The contract itself.** `tests/test_contract.py` validates it against the metamodel and resolves every reference
  `linkml-validate` does not (a `prevents: [T99]` passes validation, not this test).
- **The generator against the procedure.** `gen_procedure.py` fails when a refusal code has no check in the handler, a
  check has no code, the order breaks a check's prerequisite, or an in-call expectation has no SQL template
  [documented, its docstring].
- **The instructions.** `tests/test_charter_conformity.py` checks every sentence the fairness charter imposes on the
  seven agent specifications.

## 4. What happens at question time

**The agent's tools.** C-raw, the recommended configuration, has three: `stock_coverage` for every coverage question,
`closing_stock`, a generic tool bound to `CLOSING_STOCK`, for closing stock over a month, a quarter, a year or a range
of months, and `c_raw_semantic_view`, a semantic view on the raw tables, for stock on hand at one month and forecast.
Its instructions are C's, with closing stock routed to `closing_stock` [documented, `generated/agent_c_raw.yaml`].
Agent C has two: `stock_coverage`, a generic tool bound to the procedure `STOCK_COVERAGE`, for
every coverage question; and `b2_semantic_view`, the generated semantic view, for stock on hand, closing stock and
forecast. Its instructions route coverage to the procedure and forbid adding, averaging or computing a coverage from
the view's figures [documented, `generated/agent_c.yaml`].

**The procedure's checks, in order** (the contract's `check_order`) [documented, the contract,
`compiler/procedure_scripting.py` and `generated/stock_coverage_procedure_sql.sql`]. Four statements that read no
table are started first, together, so that they compile while the rest runs: the parameter checks of step 2, with the
normalised request, and the text of the two data statements. Then:
1. The analysis months, in one statement that reads no table (it also reads the caller): `AS_OF_MISSING`,
   `AS_OF_INVALID`, `AS_OF_NOT_MONTH_START`, `AS_OF_TOO_MANY`.
2. One context statement: the snapshot months and the valid analysis months (`AS_OF_NO_SNAPSHOT`,
   `HORIZON_NOT_LOADED`), and the quality checks scoped to the whole table. Then the result of the parameter checks,
   already computed: `BASIS_UNKNOWN`, `GRAIN_MALFORMED`, `GRAIN_EMPTY`, `GRAIN_DUPLICATE`, `FILTERS_MALFORMED`,
   `FILTER_VALUES_INVALID`, `ATTRIBUTE_UNKNOWN`, `ATTRIBUTE_UNCLASSIFIED`, `ATTRIBUTE_NOT_APPLICABLE`,
   `TOTALS_MALFORMED`, `TOTALS_NOT_SUBSET`, `SELECTION_INVALID`.
3. The quality statement and the coverage statement, started together: `MASTER_DATA_FANOUT` (an item used by the
   query has duplicated rows that differ on a used attribute), then `DATA_QUALITY_FAILED` (a whole-table check of the
   context statement).
4. On the rows the coverage statement returns: `BASIS_NOT_COMPARABLE` (a returned row or total mixes kg and L on the
   quantity basis, or several items in their own units).

The first check that fails ends the call with `status: refused`, the code and the reason. Values travel as bind
variables; identifiers are literals compiled from the contract.

**Closing stock at question time (`CLOSING_STOCK`).** Three statements: the parameters (no table read), the context
(the snapshot months; a period with a month that has no snapshot is refused, `AS_OF_NO_SNAPSHOT`, its months named),
then the closing rows with the request's quality checks. The members of a period are the groups of the grain asked
that hold a snapshot row in any month of it; each closes at its rows of the last month, 0 when it has none, and keeps
its row (`closed_without_snapshot`). A total is recomputed at its coarser grain; the basis rule and the fan-out check
are the coverage procedure's. Of its refusal texts, 8 are reworded by the generator for closing stock, not declared in
the contract [documented, `compiler/gen_closing_procedure.py`]. On the account it matches the gap-filled view on
12,304 of 12,304 members, and a call takes 6.4 s, 5.2 s of it compiling the statements [measured,
`snowflake/session13_craw/results.md`, section 3].

**Totals by recomputation.** A total row (`totals`) or a coarser call aggregates stock and forecast to the coarser
grain and runs the algorithm again; it is never a sum or an average of child coverages. Several analysis months give
a series with no total across months [documented, `TOTALS_RECOMPUTE`]. The invariant `INV_RECOMPUTE_TOTAL` says a
total row equals a separate call at the total's grain.

**What an answer carries.** Each row: `coverage_months`, `stock` and `forecast_over_horizon` (in `stock_unit`),
`stockout_month` and `flag` (`NO_STOCK`, `NO_DEMAND`, `BEYOND_HORIZON`). The answer: the request as resolved (the month
actually used), the warnings with their numbers, the first, last and latest valid months, with a selection the kept
count, their stock per unit and the members set apart, and the query ids of its statements (lineage) [documented,
the handler].

**Warnings.** `DEFAULT_SCOPE_EXCLUDED` (bulk stock left out, with its amount per unit), `FORECAST_GAPS_FILLED`
(member-months with no forecast row, counted as 0), `MASTER_DATA_DUPLICATES` (duplicated items that agree on the
attributes used), `STALE_SNAPSHOT`, `DATA_QUALITY_ROWS`. A warning is raised only when the answer reads the faulty
rows: the call checks each expectation on its `call_scope`, the whole table, the request's members or the rows the
request reads [documented, the contract]. The T2 question reads 2 member-months with no forecast row and is warned
of those 2 [documented, `generated/reference_questions.yaml`].

**Quality expectations, twice.** As data metric functions, `generated/dmf.sql` creates the 17 custom ones and runs
every check ad hoc; nothing is attached to a table and no schedule is set [documented, `compiler/gen_dmf.py`]. In the
call, the 18 expectations that are not MONITOR are checked again at their `call_scope` and refuse or warn
[measured, counted in the contract].

## 5. Questions you can ask

Each example is a campaign question of `generated/reference_questions.yaml`, named by its id, with the outcome measured
for agent C (stage 1, and stage 2 where it was played; rubric 3.2, the score of record) and what the expected answer
holds. The analysis month of the campaign is June 2026. Two examples were never asked in the campaign; they are marked.
Sources: `snowflake/phase5_campaign/stage1_results.md` (section 9) and `stage2_results.md` (sections 2 to 4).

An imprecise question gets a clarifying question, not a guess: asked for a coverage "over the whole year 2026" (T6),
C asked which month, with no figure, in both stages [measured].

**One figure for an item and a country, or a family.**
- T2: "What is the stock coverage of salted almonds 1 kg (SKU-H03) in Germany as of June 2026?" Expected: 7.0 months,
  warning `FORECAST_GAPS_FILLED` (2 member-months with no forecast row, counted as 0). C: correct in both stages.
- T1: "What is the stock coverage of flour and baking in France as of June 2026?" Expected: 2.8 months, recomputed at
  the family and country grain. C: correct in both stages.

**Closing stock over a period** (C answers it from the semantic view over the gap-filled snapshot; C-raw from the
procedure `CLOSING_STOCK`, correct on both questions below in every play [measured, `snowflake/session13_craw/results.md`, section 4]).
- CS_LAST_MONTH_GAP: "What was the closing stock of oat cereal bar 1 kg (SKU-H11) in Switzerland for Q2 2026?"
  Expected: 0 (no June snapshot; May's 350 is not carried to the close). C: correct in both stages.
- N2: "For the SNACK_BARS family in Switzerland, what was the closing stock at the end of each month of Q2 2026, and
  how many months of coverage does the June 2026 stock give?" Expected: 900, 350 and 450, each month its own snapshot,
  never added; coverage 2.25 months. C: correct in both repetitions (added in stage 2).

**A series of months.** Never asked in the campaign. Example: "What was the stock coverage of flour and baking in
France in April, May and June 2026?" Several months in `as_of_months` (at most 24) give one set of rows per month and
no total across months; the invariant `INV_SERIES_POINTWISE` (each month equals the single-month call) is asserted by
`tests/test_procedure.py` on the account [documented].

**A total at a coarser grain, and a drill.**
- BULK_SCOPE, then BULK_SCOPE_DRILL: "What is the stock coverage of ground coffee as of June 2026?" then "And by
  country?" Expected: 8.67 months for the family, warnings `DEFAULT_SCOPE_EXCLUDED` (51,475.5 kg of bulk stock left
  out) and `FORECAST_GAPS_FILLED` (2); then six country rows (from 1.93 months in Spain to 11.38 in Belgium), never
  added or averaged back to the family figure. C: correct on both, in both stages; in stage 1 the governance flag ROWS_COMMENTED marked
  a figure C derived across countries on the drill (not part of the verdict).
- Never asked in the campaign: "What is the stock coverage of flour and baking by country as of June 2026, with the
  family total?" A total row through `totals`, recomputed.

**Lists and selections.**
- S_FIRST_WORLD: "Worldwide, which 10 products will stock out first from June 2026, not counting those already out?"
  Expected: ten products from SKU-H02 (0.5 months, stock-out July 2026), each with its stock-out month; SKU-H08 and
  SKU-H11 set apart as already out (`NO_STOCK`), SKU-H09 as without demand (`NO_DEMAND`). C: correct in both stages.
- S_STOCKOUT_COUNTRY: "Which products will stock out within the next 3 months in France, from June 2026?" Expected:
  four products, stock-out months July to September 2026, a summary of 4 kept rows holding 11,030 L and 1,030 kg,
  never one sum across units. C: correct in both stages.
- H_STOCKOUT_2027: "As of June 2026, which items will stock out during 2027?" (a window: above 6, at most 18 months).
  Expected: 35 items. C: wrong in stage 2, its only play: it gave the count and the stock-out months but named no
  product (the table it announced was not emitted).

**Stock that sleeps, and its value.**
- S_DORMANT_VALUE: "Across all countries, which item and country pairs have more than 12 months of coverage in June
  2026, and how much stock value does that tie up?" Expected: 28 pairs tying up 70,987,982.99 EUR (71.0 million), on
  the value basis: a stock value identified, not a saving. C: correct in both stages.

**A basis choice.**
- S_OWN_UNIT: "What is the stock coverage of SKU-0046 in its own unit (cases) in June 2026?" Expected: 3.06 months,
  stock in CASE_10, stock-out October 2026. C: correct (stage 1 only).
- DIM_MIX: "What is the stock coverage in France in June 2026?" France holds kg and L items: the quantity basis is
  refused with `BASIS_NOT_COMPARABLE`, value allowed; on value, 8.70 months. C: correct in both stages, relaying the
  refusal and switching to value with the reason.

**Questions refused, or answered with a flag.**
- No month (T6): see above.
- Packs of different sizes (T5): "What is the stock coverage of dry pasta in the United Kingdom in number of packs as
  of June 2026?" Expected: `BASIS_NOT_COMPARABLE` on the item's own unit, kg equivalent or value allowed. C: correct
  (stage 1 only), but not through the code: it answered on the kg equivalent and said why packs do not add up; the
  procedure returned no coded refusal [measured].
- A duplicated item (T7_R1): "What is the stock coverage of cooking oils in Sweden by lifecycle status as of June
  2026?" Expected: `MASTER_DATA_FANOUT`, no figure. C: correct in both stages; A, B1, B2 and D gave the
  fanned-out 2.25 and 6.0 in stage 1.
- kg and L mixed on the quantity basis (DIM_MIX): see above.
- Beyond the horizon (BEYOND_H): "What is the stock coverage of arabica beans 1 kg (SKU-H10) in Poland as of June
  2026?" Not refused: 50.0 months flagged `BEYOND_HORIZON` (extrapolated from the mean non-zero monthly forecast).
  C: correct in both stages.
- No demand (NO_DEMAND): "What is the stock coverage of iced tea summer edition 1 L (discontinued) (SKU-H09) in
  Belgium as of June 2026?" No figure, flag `NO_DEMAND`. C: correct in stage 1; wrong in stage 2 on the wording rule
  alone (the "1 L" of the product name read as the unit of a coverage), correct on the figure-only score.

**Which parameters each type sets** [documented, the tool parameters of `generated/reference_questions.yaml`]:

| Type | `as_of_months` | `grain` | `filters` | `basis` | `totals` | `coverage_below` / `coverage_above` / `rank_first` |
|---|---|---|---|---|---|---|
| One figure | one month | the scope's grain (`sku_code, country_code`; `family_code, country_code`) | the scope | default `QTY_EQ` | | |
| Closing stock | C: the view, by quarter, year or a range of months. C-raw: `closing_stock`, `periods` (a year, a quarter, a month, a range, several for a series) | as asked | as asked | as asked | `[[...]]` or `[[]]` | |
| Series | several months | as asked | as asked | as asked | never across months | |
| Coarser total, drill | one month | the drill adds an attribute and keeps the filters | kept | as asked | `[[...]]` or `[[]]` for a grand total | |
| Lists and selections | one month | `sku_code` (or `sku_code, country_code`) | the country, if named | `QTY_EQ` | | below N, above N, first N |
| Dormant stock | one month | `sku_code, country_code` | | `VALUE` | | `coverage_above` |
| Basis choice | one month | as asked | as asked | `NATIVE`, `QTY_EQ` or `VALUE` | | |
| No month | none: ask | | | | | |

## 6. Adding a metric

What can be built today was measured by a dry run on a second metric, cash runway (`docs/dry_run/`, results in
`docs/dry_run/results.md`) [measured, offline].

Whatever the case, the keys the compiler does not read are fixed: a contract holding another value than the one supported (a monthly grain, LINEAR interpolation, the four outcomes in order) is refused by the generators; `compiler/supported.py` lists them and [reference/metamodel.md](reference/metamodel.md) marks them.

### Same pattern as stock coverage

A snapshot drained by a forward flow: cash runway (cash balance against planned spend), days of supply, order
backlog coverage. The steps, as the code stands:
1. Copy `contract/stock_coverage.yaml` and rewrite the physical model (`tables`, `relationships`), the two measures
   with their columns per basis, the attributes with their applicability, the metric's horizon and outcomes, the
   analysis periods, the quality expectations and the failure modes.
2. Keep the vocabulary the code keys on: the 8 parameter ids, the 21 refusal codes, three bases (a native one valid
   for one item per row, a base-unit equivalent one valid for one dimension per row and used as the default, a
   monetary one), a calendar named `DIM_CALENDAR` with `month_start`, `year` and `quarter`, a `grain_rule`, a
   non-empty default scope, one refuse-if-used grain expectation on the basis model's table. Without each of these a
   generator fails; the dry run's ablation names which one and where.
3. Validate: `.venv/bin/linkml-validate -s contract/metamodel.yaml -C MetricContract <your contract>`.
4. Generate: each generator but `gen_questions` takes `--contract`.

What the dry run measured: cash runway as written, with no name shared, validates, and the schema, the data metric
functions and the closing view generate from it; the procedure and the agent specification generate only with the
vocabulary of step 2, and their output is not deployable yet. It still carries stock coverage's object names
(`STOCK_COVERAGE`, `CLOSING_STOCK_SV`, the tool `stock_coverage`), so a second metric would replace the first in the
same schema [inferred]; its answer keys are named after stock; the agent's tool description mixes the contract's text
with fixed stock coverage sentences; and the procedure's SQL reads a column `item_id` that a cash contract does not
have, so the query would fail at run time [measured text, failure inferred]. Fixing these leaks is a later decision;
the list is in `docs/dry_run/results.md`.

### A semi-additive closing measure

A closing balance or a headcount: a SNAPSHOT measure with a `period_aggregation` (LAST_PERIOD: the snapshot of the
period's last month, 0 for a member with no row that month, summing, averaging and carrying forward forbidden).
`gen_closing_sv.py` turns it into a gap-filled view and a semantic view with `NON ADDITIVE BY` the snapshot month;
`gen_closing_procedure.py` turns it into a procedure that applies the rule at question time with no densified data
(C-raw). The two agree on every member measured (section 4).

```yaml
    period_aggregation:
      id: CLOSING_STOCK
      description: >-
        Closing stock over a period: the snapshot of the period's last month, for every member of the period. A
        member with a snapshot in any month of the period and none in its last month closes at 0 and keeps its row.
        Never summed, averaged or carried forward over time (step 1 of the article; data/traps.yaml closing_stock).
      method: LAST_PERIOD
      periods: [PERIOD_RANGE, QUARTER, YEAR]
      member_set: ANY_SNAPSHOT_IN_PERIOD
      missing_value: "0"
      forbidden_methods: [SUM, AVERAGE, LAST_NON_EMPTY]
```

What the dry run measured: on the cash balance, the generator runs, but the view is still named `CLOSING_STOCK_SV`
and its metrics `closing_stock_<basis>`; its quarter dimension is written `year || '-Q' || quarter` whatever the
calendar's columns [measured text]. A contract that holds only a closing measure does not validate: the metamodel
requires a depletion metric and parameters. Not supported alone today.

### Another shape: a ratio, a rate, a cohort

Not built [inferred]. The metamodel's `metrics` accepts `DepletionMetric` only, and the procedure template computes
depletion only. What each shape would need:
- **A ratio** (fill rate, margin): a `RatioMetric` class (numerator and denominator measures, aggregate before
  dividing, a zero-denominator outcome) and a template; a semantic view's derived metric may suffice where no refusal
  is needed.
- **A rate over a period** (stock turnover: a flow over the average level of a snapshot): a class that names both, and
  AVERAGE allowed as a period aggregation for that use (today it is listed among the forbidden methods).
- **A cohort** (retention by first period): a `CohortMetric` class, a cohort-defining event, a member-level fact, an
  offset window and a denominator fixed at the cohort's start, with a template for each.

## 7. Testing a new metric

- **Traps that declare the right value and each wrong one.** In `data/traps.yaml`, each trap pins a member that forces
  one behaviour and declares the correct value and the value each named wrong behaviour returns (T1: the sum or the
  average of child coverages), so that a wrong answer is recognisable. Each trap is a `failure_modes` entry; a trap
  nothing prevents fails `tests/test_contract.py`.
- **Two independent references.** Every expected value is recomputed from the dataset alone by a procedural pandas
  implementation (`data/coverage_ref.py`) and a set-based DuckDB one (`data/checks/check_dataset.py`), asserted by
  `tests/test_reference_oracle.py`; none comes from the procedure under test. Their agreement is an equivalence check;
  correctness comes from the hand-computed trap values. `docs/check_coverage_formula.py` pins the formula on worked
  cases [measured, the offline suite].
- **Drift tests.** `tests/test_generated.py`, as in section 3.
- **The procedures on the account.** `tests/test_closing_procedure.py` (with `LINKML_CLOSING_LIVE=1`) asserts the
  closing-stock heroes, the refusals and a sample against the references; `snowflake/session13_craw/parity.py`
  compares `CLOSING_STOCK` with the gap-filled view on every member. `tests/test_procedure.py` (with
  `LINKML_PROCEDURE_LIVE=1`) asserts every expected value, flag, warning and refusal
  of the reference questions, and the invariants, against the deployed procedure.
- **The evaluation harness (optional, billed).** `eval/` runs the question set on Cortex Agents and grades the
  answers; it calls the agents and costs money. See the cost warning in the README's section on reproducing the
  campaign before running it.

## 8. Limits

- **One metric pattern, built and evaluated, on one instance:** stock coverage, with closing stock, on one account and
  synthetic data [measured, the campaign].
- **What the dry run left unproven:** no second metric was deployed or called; the run-time failures it points to are
  read from the generated SQL, not run [inferred]; the overdraft case (a negative level) is not an outcome of the
  pattern, and the generated SQL would return 0 with no flag [inferred]; the closing view's behaviour on a calendar
  with other column names was read, not deployed; the shapes of section 6 are designs, not code.
- **The procedures are monthly only** (`DATEDIFF(month, ...)`, months as periods), although the metamodel's time
  grains go from DAY to YEAR [documented, the code].
- **8 refusal texts of `CLOSING_STOCK` are written in the generator**, not declared in the contract, whose templates
  were written for coverage [documented, `compiler/gen_closing_procedure.py`].
