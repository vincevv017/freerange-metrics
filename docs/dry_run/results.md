# Dry run: a second metric of the same pattern (session 11, 2026-10-07)

Question: how much of the compiler is generic? Every generator of `compiler/` was run on a second contract of the
depletion pattern (a snapshot drained by a forward flow), offline. Nothing was deployed, no Snowflake call was made,
and no file outside this folder changed. Tags: **[measured]** (run here, by `run_dry_run.py`), **[inferred]**
(reasoned from the generated text or the code, not run).

```bash
.venv/bin/python docs/dry_run/run_dry_run.py --out <a folder outside the repository>
```

The runner writes its outputs, a `report.json` and the toy dataset it needs into that folder (by default a new
temporary folder), never into the repository. The toy dataset (a few Parquet files: 36 calendar months, 6 balance
months, 36 plan months, three entities) exists because `gen_agent` and `gen_native_sv` read the loaded dataset to list
the valid months and the attribute labels; it is written under each variant's own table names.

Measured at commit 48bc2b2 (2026-10-07). Since commit 988a439 the generators fail closed on the keys they do not read (`compiler/supported.py`): rerun, variant A now stops `gen_procedure` and `gen_agent` with "metrics.cash_runway.anchor_parameter: only as_of_months is supported by this compiler" instead of the failures below; which generator runs or fails is unchanged, and the line numbers cited below are those of 48bc2b2 [measured].

## The second contract

`cash_runway.yaml`: if no cash comes in, how many months does the cash on hand at the balance month last against the
planned spend of the next 18 months? A cash balance per bank account and month (SNAPSHOT) drained by planned spend per
entity and month (FLOW); attributes `entity_code`, `segment_code` (conformed) and `account_type` (balance only;
restricted cash excluded by default); one basis, EUR; 21 refusal codes, 9 quality expectations, 7 failure modes; a
`CLOSING_BALANCE` period aggregation. No name is shared with stock coverage (variant A).

Variant B is A plus the fewest concessions that let the generators run, each tied below to the generator that needs it:

| Concession | What changes in the contract |
|---|---|
| B1 | the 8 parameter ids renamed to stock coverage's (`as_of_months`, `grain`, `filters`, `basis`, `totals`, `coverage_below`, `coverage_above`, `rank_first`) |
| B2 | the 21 refusal code ids renamed to stock coverage's (`AS_OF_MISSING` to `BASIS_NOT_COMPARABLE`) |
| B3 | three measure bases (native, base-unit equivalent as the default, monetary) instead of one |
| B4 | the calendar renamed `DIM_CALENDAR` with columns `month_start`, `year`, `quarter` |
| B5 | `member_selection.grain_rule` given (optional in the metamodel) |

Both variants, and every ablation below, pass `linkml-validate` against `contract/metamodel.yaml` [measured].

## Matrix [measured]

| Generator | A | B | Stock coverage names in the output (B) | Reads as cash runway? |
|---|---|---|---|---|
| `gen_schema` | runs | runs | header path, comments ("stock and forecast"), constant `ITEM_DIMENSIONS` | yes, apart from comments |
| `gen_dmf` | runs | runs | header path only; 6 custom DMFs and 9 checks for the 9 expectations | yes |
| `gen_closing_sv` | runs | runs | view `CLOSING_STOCK_SV`, metric `closing_stock_<basis>`, comments "Closing stock ... comparable across every item" | no |
| `gen_procedure` (both targets) | fails: `AssertionError` at `gen_procedure.py:103`, 21 codes have no check | runs | procedures `STOCK_COVERAGE`, `STOCK_COVERAGE_PY`; answer keys `coverage_months`, `stock`, `forecast_over_horizon`, `stock_unit`, `stockout_month`, `stock_and_forecast`, `stock_only` | no |
| `gen_agent` | fails: `FileNotFoundError` at `gen_agent.py:58` (reads `DIM_CALENDAR.parquet`) | fails inside `gen_native_sv.py:86`; runs with the B2 view tool stubbed | tool `stock_coverage` bound to `STOCK_COVERAGE`; fixed text "Stock coverage in months ... stock on hand ... demand forecast", "Germany is DE, flour and baking is PANTRY_FLOUR" | no: a mix of the contract's text and stock coverage's |
| `gen_native_sv` (B2) | fails: `StopIteration` at `gen_native_sv.py:86` (attribute `batch_status`) | fails | stock coverage by construction (`DIM_ITEM`, `DIM_GEO`, `DIM_BATCH`, grocery verified queries) | not applicable |
| `gen_questions` | fails: `KeyError 'reference_question'` at `gen_questions.py:111` | fails | the campaign's question set: no `--contract` option, reads `data/traps.yaml` and the dataset | not applicable |

Ablation, B without one concession (B2's view tool stubbed) [measured]:

| Without | Fails |
|---|---|
| B1 | `gen_procedure` (`KeyError 'filters'`, `gen_procedure.py:178`); `gen_agent` (`KeyError 'as_of_months'`, `gen_agent.py:190`) |
| B2 | `gen_procedure` (`AssertionError`, `gen_procedure.py:103`: the handler's checks are named after the codes) |
| B3 | `gen_procedure` (`StopIteration`, `gen_procedure.py:192`); `gen_agent` (`StopIteration`, `gen_agent.py:103`) |
| B4 | `gen_agent` (`FileNotFoundError`, `gen_agent.py:58`) |
| B5 | `gen_agent` (`KeyError 'grain_rule'`, `gen_agent.py:230`) |

Optional sections removed from B [measured]: with no `default_scopes`, `gen_procedure` fails (`IndexError`,
`gen_procedure.py:152`); with no refuse-if-used grain expectation, it runs and writes
`scope_items AS (SELECT None FROM stock_rows ...)` into the request SQL.

Closing measure alone (the cash balance and its `CLOSING_BALANCE`, no depletion metric) [measured]: the contract does
not validate (`metrics` and `parameters` are required by the metamodel); `gen_closing_sv` runs on it (59 lines).

## The SQL the procedure would send

The runner assembles, without running it, the SQL of variant B's Python procedure for one request (June 2026, by
entity, with a grand total). `stock_rows` selects `cash_balance.entity_id`; two later steps read `item_id` from
`stock_rows` [measured, the text]. The query would fail at run time on an unknown column [inferred, not run]. The
handler keeps the in-call quality counts of columns whose name starts with `QE_` only (`procedure_handler.py:771`);
the cash runway expectations are named `DQ_...`, so their warnings would be dropped silently [inferred, not run].

## Classification

**Instance leaks: the code must change before a second metric can be deployed.**
1. Fixed object names: `STOCK_COVERAGE`, `STOCK_COVERAGE_PY`, `CLOSING_STOCK_SV`, the tool `stock_coverage`. A second
   metric deployed in `LINKML_METRICS.RAW` would replace stock coverage's own objects [inferred].
2. `item_id` in the procedure's SQL (`procedure_handler.py`, `procedure_scripting.py`): the member key must be named
   `item_id` or the query fails [measured text, failure inferred].
3. Answer keys named after stock: `coverage_months`, `stock`, `forecast_over_horizon`, `stock_unit`, `stockout_month`,
   `stock_and_forecast`, `stock_only`.
4. Calendar names: `gen_agent` reads `DIM_CALENDAR`/`month_start` from the dataset whatever the contract declares
   [measured]; `gen_closing_sv` writes `year || '-Q' || quarter`, so with variant A's `fiscal_year` and
   `fiscal_quarter` its view would name missing columns [inferred].
5. Fixed text in `gen_agent` (tool description, orchestration, the filter example), in `gen_closing_sv` (metric names
   and comments) and in the SQL target's exception message.
6. In-call expectation ids must start with `QE_` (Python target) [inferred].
7. `gen_native_sv` (configuration B2) and `gen_questions` (the campaign's questions) are stock coverage by construction.
8. Cosmetic: every output's header names `contract/stock_coverage.yaml`.

**Vocabulary a second contract must reuse (no code change, but its tool then speaks stock coverage's words):** the 8
parameter ids; the 21 refusal codes; the three-basis shape with the equivalent basis as default; a non-empty default
scope; one refuse-if-used grain expectation on the table of the basis model; `exhaustion_period`, `member_selection`
and its `grain_rule`; one metric per contract (`metrics[0]`, `totals_rules[0]` and the like).

**Pattern logic (expected):** the depletion outcomes in order, the window relative to the anchor, densification, the
member spine, totals by recomputation, the order of the checks. The SQL is monthly only (`DATEDIFF(month, ...)`),
although the metamodel's `TimeGrain` lists DAY to YEAR.

**Metamodel findings [measured unless tagged]:** `metrics` accepts `DepletionMetric` only, and `metrics` and
`parameters` are required, so a closing measure alone does not validate; `basis_model` requires item-dimension columns
(dimension, base unit, native unit, factor) even for one monetary basis, and cash runway fills them with
`local_currency` three times; a negative level (an overdraft) is not an outcome, and the generated SQL returns 0 with
no flag for it [inferred from the generated SQL].

## What can be built today

- **Built and evaluated:** one metric pattern, one instance: stock coverage, with closing stock.
- **Same pattern, second instance:** the contract declares and validates; the schema, the data metric functions and
  the closing view generate. The procedure and the agent specification are not deployable until leaks 1 to 6 are
  fixed (a later decision).
- **A closing measure alone:** not supported today.
- **Other shapes (ratio, rate, cohort):** not built; what is missing is in `docs/GUIDE.md` [inferred].
