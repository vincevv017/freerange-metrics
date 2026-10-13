# Phase 2 notes: data and quality generated from the contract

> Session 5, 2026-10-03. Every choice this phase made, tagged **[documented]** (DEFINITION.md, the plan, Snowflake
> docs), **[measured]** (run here, evidence in the repository), or **[inferred]** (reasoned, not run). The contract
> moved from 0.1.0 to 0.1.2; no rule changed (its `changes` list says what did).

## Public scrub

| # | Choice | Why | Tag |
|---|---|---|---|
| 1 | Every hit of the scrub list was classified before rewriting. Two innocent hits stay: "Cashew nuts" (a product name) and a query id ending in `106`. No account identifier, host, local path or brand name was found | A blind rewrite would have changed a product name and a query id | measured |
| 2 | Legacy BI is named generically; metric counts, the year and the spreadsheet generator are gone. The structural counts that follow from H = 24 (24 cumulative sums, a 25-branch CASE) stay | They come from the definition, not from a past implementation | inferred |
| 3 | Other projects' roles become `<OTHER_ROLES>`, the admin user `<ADMIN_USER>` in docs and probe results; `00_setup.sql` takes `admin_user` as a variable | Plan decision of session 5 | documented |
| 4 | DEFINITION.md stays **draft**: the beyond-horizon and T8 markers are settled and point to the contract, but the contract still lists `open_decisions` and the plan marks the spine choice "by default, to confirm" | The status may drop "draft" only when nothing is open | inferred |
| 5 | The git history still holds the old wording | The plan's default: the public repository starts from a clean history (one initial commit) | documented |

## Generated schema module (2a)

| # | Choice | Why | Tag |
|---|---|---|---|
| 6 | `compiler/gen_schema.py` writes `generated/schema.py`: TABLES, declared GRAINS (DIM_ITEM included), ATTRIBUTES with their class, CONFORMED, SNAPSHOT_ONLY, NOT_APPLICABLE, UNIT_VARIANTS, FORBIDDEN_UNITS, HORIZON_MONTHS | The consumers needed exactly the v0 content, plus the declared DIM_ITEM grain and the refused unit's columns | inferred |
| 7 | Parity with `schema_v0.py` was green before the switch; after the switch the seven CSV digests were identical; `schema_v0.py` was deleted and the parity test became a drift test (regenerate to a temporary folder, compare bytes). A one-byte mutation of the generated file fails it | The order the brief set | measured |
| 8 | DIM_ITEM now has its declared grain, so DIM_ITEM in the published dataset is sorted by `item_id` only (same order as before: stable sort, ACTIVE row first) and `check_dataset.py` skips it in the uniqueness loop, keeping the explicit T7 check | The contract promises the grain; the data breaks it on purpose | measured (digests), inferred (rule) |
| 9 | The manifest's `schema_version` is now the contract version (0.0.1-temporary, then 0.1.0 to 0.1.2); the CSV digests, the fingerprint, did not move with it | The version names the source of the schema | measured |
| 10 | Consumers import `SNAPSHOT_ONLY`; no `STOCK_ONLY` alias is generated | One name per class; DEFINITION.md keeps "stock-only" in prose | inferred |

## Traps (2b)

| # | Choice | Why | Tag |
|---|---|---|---|
| 11 | **T5 moved** to `PANTRY_PASTA` x GB (three SKUs in CASE_10, PACK_1000 and PACK_500): 2.3651 in QTY_EQ, 8.4966 with pack counts summed. The contract's reference question follows | The T1 heroes are all PACK_1000 (factor 1): raw equals QTY_EQ there, so the wrong behaviour would be invisible | measured |
| 12 | T5 and T6 carry `expected_refusal` and no value. T6 expects `AS_OF_MISSING`; through an agent, asking for the month is also correct | DEFINITION.md section 4: ask or refuse | documented |
| 13 | The `lifecycle_status` question is a `refusal_questions` entry of T7, not a new trap id. Expected `MASTER_DATA_FANOUT`; wrong: naive rows ACTIVE 2.25 and PHASE_OUT 6.0 (stock 1,500), or a silent dedupe that keeps ACTIVE only | It is the same failure mode; a new id would need a new failure mode for no new rule | inferred (shape), measured (values) |
| 14 | BULK_SCOPE on HOT_GROUND, grain `family_code` over all countries: **8.6735** by default (51,475.5 qty_eq of BULK excluded), **17.4424** with `item_type IN (STANDARD, BULK)`, matching 8.7 and 17.4. VALUE: 8.2821 and 22.1200 | Decision 6 of session 5; findings section 8 measured at family level | measured |
| 15 | T5 and BULK_SCOPE query background families, so their values were read once from the dataset with both reference implementations and frozen; the check recomputes them | Background values cannot be computed by hand from traps.yaml | inferred |
| 16 | `check_dataset.py` applies the contract's default scope to every trap value and asserts that it changes nothing on the earlier heroes | Decision 5 is the contract's rule; Phase 1 checked the heroes hold no BULK stock | measured |
| 17 | `coverage_ref.py` accepts a list as a filter value (IN) and a `raw_units` switch, the T5 wrong behaviour | Needed by BULK_SCOPE's explicit filter and T5's wrong value | inferred |
| 18 | **Closing-stock heroes** (step 1): new family `SNACK_BARS` x CH, quarter Q2 2026 = k -2..0. SKU-H11 has April 400 and May 350, no June: closes at **0** (wrong: sum 750, last known 350, average 250). SKU-H12 has April 500 and June 450, no May: closes at **450** (wrong: sum 950, average 316.67). The family closes at **450** (wrong: sum 1,700, carried forward 800, average 566.67). Python and DuckDB SQL agree | Decision 5 of session 5. A native "last non-empty" rule would presumably return 350 for H11, the trap the article is to measure | measured (values), inferred (native behaviour) |
| 19 | A period's members are those with any snapshot in the period; a member absent from the last month closes at 0 and keeps its row | Mirrors the coverage spine (decision 3) | inferred |
| 20 | New heroes use `stock_by_k`: every month pinned, rows only for the listed k. Appended at the end of `hero_items`. Per-hero digests of the ten earlier heroes, the background and the three non-item dimensions are byte-identical; only 2 items, 2 batches, 4 stock rows and 144 forecast rows were added | Append-only rule | measured |
| 21 | **Closing stock is not in the contract.** The traps live in a separate `closing_stock` section, outside the traceability test | The metamodel's `SELECT_PERIOD` selects one anchor month; it cannot say "last month of a period, gaps close at 0". Declaring it needs a metamodel change, out of this session's scope | inferred |

## Data metric functions (2c)

| # | Choice | Why | Tag |
|---|---|---|---|
| 22 | No account-level grant was needed: the project role calls system DMFs ad hoc without `SNOWFLAKE.DATA_METRIC_USER` or `EXECUTE DATA METRIC FUNCTION`, and creates custom DMFs in RAW as its owner | Run as the project role, no secondary role | measured |
| 23 | System DMF names checked: 51 in `SNOWFLAKE.CORE`; `DUPLICATE_COUNT` and `NULL_COUNT` exist (phase1_notes item 27 closed) | `SHOW DATA METRIC FUNCTIONS IN SCHEMA SNOWFLAKE.CORE` | measured |
| 24 | Ad hoc, a system DMF takes one plain column. `ACCEPTED_VALUES`, multi-column `DUPLICATE_COUNT` and `REFERENTIAL_INTEGRITY_COUNT` are attach-only; a filtered subquery becomes scalar. So multi-column, cross-table and accepted-values checks are custom | Six call forms tried | measured |
| 25 | A two-table custom DMF is called with parenthesised subqueries only | Three forms tried | measured |
| 26 | A DMF body cannot call `CURRENT_DATE` (510101); stock freshness uses the system `FRESHNESS` (seconds). The contract's `dmf` moved from CUSTOM to it, and to `NEGATIVE_COUNT` for the two non-negativity checks (0.1.2) | System where it fits | measured |
| 27 | Custom semantics: grain = rows beyond the first per key; referential = orphan rows (compound key for `QE_STOCK_BATCH_ITEM`); cardinality = keys mapping to more than one value of the next column; accepted values = values outside `known_values` (NULL counted by the completeness checks, not here); `QE_EQ_FACTOR` uses the contract's `condition` as its SQL predicate | One template per kind, driven by the contract | inferred |
| 28 | `QE_FORECAST_DENSE` takes its periods from the distinct forecast months inside the union of the horizons of all valid analysis months | A DMF takes at most the tables passed to it; the calendar would be a third argument. Correct while every month has some forecast row (true here) | inferred |
| 29 | `QE_HORIZON_LOADED` checks the calendar against the latest snapshot + 24; the forecast's reach is not checked | The contract's condition names both; a forecast-reach check is a Phase 3 addition | inferred |
| 30 | `DUPLICATE_COUNT` returns 1 for one item on two rows. Whether it counts duplicated values or rows beyond the first is not settled by this data; the custom grain checks count rows beyond the first | Both readings give 1 here | measured (value), inferred (semantics) |
| 31 | Every DMF value equals an independent pandas count. Attribution: without SKU-H06, `DUPLICATE_COUNT` is 0; without SKU-H03/DE, `QE_FORECAST_DENSE` drops from 377 to 375. Done on session TEMPORARY copies, since an ad hoc argument cannot carry a WHERE | Equivalence is not correctness: each detection is tied to its trap | measured |
| 32 | `QE_FORECAST_DENSE` is 377 on the whole table, mostly background gaps (3% by design). The procedure's `FORECAST_GAPS_FILLED` must count the gaps of the query's members only | A table-wide number would warn on every answer | inferred |

## Traps T1 to T8 and the check that fires

| Trap | Data check that fires on v0 | Value | Otherwise: why it is not a data check, and what covers it |
|---|---|---|---|
| T1 Ratio re-aggregation | none | - | Calculation trap: the data is correct, the error is summing ratios. `TOTALS_RECOMPUTE`, `INV_RECOMPUTE_TOTAL` |
| T2 Sparse forecast months | **QE_FORECAST_DENSE** | 377 (2 from SKU-H03/DE) | Also `INV_DENSIFY`: the engine densifies, the expectation only warns |
| T3 Stock-only filter pushed to forecast | none | - | Calculation trap: legitimate data. Applicability classes, `INV_SNAPSHOT_ONLY_FILTER_KEEPS_FLOW` |
| T4 Time filter pushed to forecast | none | - | Calculation trap. `time_filter_on_flow: SELECTS_ANCHOR_ONLY`, `INV_WINDOW_EXCLUDES_ANCHOR` |
| T5 Heterogeneous units | none (`QE_EQ_FACTOR` clean, 0) | 0 | Mixed pack sizes are legitimate data; summing them is the error. Refusal `UNIT_RAW_NOT_ADDITIVE`, `INV_UNIT_SCALE`. `QE_EQ_FACTOR` guards the conversion the QTY_EQ variant relies on |
| T6 Missing analysis month | none (`QE_HORIZON_LOADED` clean, 0) | 0 | A question defect, not a data defect. Refusal `AS_OF_MISSING`, `AS_OF_MONTHS`, `INV_SERIES_POINTWISE` |
| T7 Master-data fan-out | **QE_ITEM_GRAIN** | 1 (0 without SKU-H06) | Refused only when the query uses `lifecycle_status` (`MASTER_DATA_FANOUT`) |
| T8 Forecast but no stock | none (referential checks clean, 0) | 0 | Calculation trap: the member spine keeps the row. `MEMBERS_SPINE`, `INV_FLAG_CONSISTENT`. An orphan stock row would be another way to lose a member: `QE_STOCK_ITEM_REF` |
| NO_DEMAND, BEYOND_H | none | - | Legitimate data, handled by the outcomes and `INV_FLAG_CONSISTENT`; BEYOND_H's absent months add 2 to `QE_FORECAST_DENSE` |
| BULK_SCOPE | none | - | A scope rule on legitimate data: `SCOPE_ITEM_TYPE`, `INV_DEFAULT_SCOPE` |
| Closing-stock gaps | none | - | Gaps are legitimate data; the period rule is not in the contract yet (21) |

## Probe D credits

| # | Finding | Tag |
|---|---|---|
| 33 | One turn, 88,111 billed tokens, **0.0696** token credits, `SQL_QUERY_CREDITS` null; read with the single approved ACCOUNTADMIN SELECT. Details in `snowflake/probe_d/results.md` | measured |

## Carried to Phase 3

- Generate the procedure from the contract, with the warnings scoped to the query's members (32), the refusal order,
  the default scope and `as_of_months` series; measure latency as tool span against orchestration.
- Declare closing stock in the contract (21): a period aggregation for snapshot measures in the metamodel.
- Attaching and scheduling DMFs needs `EXECUTE DATA METRIC FUNCTION ON ACCOUNT`: show the statement first.
- `RAW` was reloaded with `CREATE OR REPLACE TABLE`; the session 1 and 2 probe semantic views in RAW were not
  re-checked after it.
