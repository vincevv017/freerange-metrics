# Phase 3 notes

Part 1 (session 6): native closing stock, contract 0.2.0, generated coverage procedure. Part 2 (session 7, at the
end): generated closing stock, trap T9, latency wins, QE_FORECAST_DENSE, contract 0.3.0.

## Part 1

> Session 6, 2026-10-03. Every choice this session made, tagged **[documented]** (DEFINITION.md, the plan, the
> contract, Snowflake docs), **[measured]** (run here, evidence in the repository), or **[inferred]** (reasoned, not
> run). The contract moved from 0.1.2 to 0.2.0: a rule was added (closing stock). No agent was called.

### Step 0: native closing stock (`snowflake/probe_closing/results.md`)

| # | Choice or finding | Why, evidence | Tag |
|---|---|---|---|
| 1 | The five probe semantic views in RAW all compile after the session 5 reloads and return the expected number (T1 2.8, or stock 1,400 on the B1 builds) | Phase 2 open question 4, closed | measured |
| 2 | The baseline build is a copy of `COVERAGE_SPINE_SV` (best native build, stock `NON ADDITIVE BY (stock.snapshot_month)`) with `cal.year`, `cal.quarter` and `cal.year_quarter` added: `COVERAGE_SPINE_CLOSING_PROBE_SV`. Nothing else changes | The brief: add a quarter dimension to a copy if needed | inferred |
| 3 | **SKU-H11 x Q2 2026 returns 350, expected 0: the last known value.** Same with a quarter filter and no time dimension | `NON ADDITIVE BY` keeps, per output row, the rows of the latest snapshot month present in that row's group, not the period's last month | measured |
| 4 | SKU-H12 (gap in May) 450 and SNACK_BARS (both gaps) 450 are right: no sum, no average appears | The family's group holds June rows, so only June is summed. Right by the group's composition: a family with no row in its last month would close at an earlier month, as SKU-H11 does | measured (values), inferred (the family case) |
| 5 | At the month grain, an absent snapshot is an absent row, never 0 | SKU-H11 June and SKU-H12 May: no row | measured |
| 6 | Decision 6 (where closing stock is answered), proposal: a **generated semantic view** whose stock table is densified over the period's members (one row per member and month, 0 where absent), so that `NON ADDITIVE BY` finds the last month in every group. The procedure stays coverage only | The native rule is right once every member has a row in every month; the densification is what the contract's `missing_value: "0"` and `ANY_SNAPSHOT_IN_PERIOD` say. Not built, so not measured | inferred |

### Step 1: contract 0.2.0

| # | Choice | Why, evidence | Tag |
|---|---|---|---|
| 7 | The metamodel (0.2.0) gains `PeriodAggregation` on `Measure`: `method` (LAST_PERIOD), `periods` (PERIOD_RANGE, QUARTER, YEAR), `member_set` (ANY_SNAPSHOT_IN_PERIOD), `missing_value` ("0"), `forbidden_methods` (SUM, AVERAGE, LAST_NON_EMPTY). Required for a SNAPSHOT measure, absent on a FLOW (tested) | Decision 1 of session 6; phase 2 note 21 | documented |
| 8 | The closing-stock traps become failure modes `CS_LAST_MONTH_GAP`, `CS_MIDDLE_MONTH_GAP`, `CS_FAMILY`, prevented by `stock_on_hand.period_aggregation` and by the invariant `INV_CLOSING_LAST_PERIOD`; they join the traceability test | No trap without a rule | measured (tests) |
| 9 | `tests/test_contract.py` recomputes 0, 450, 450 from the contract's rule, and each forbidden method reproduces a wrong value of traps.yaml (LAST_NON_EMPTY 350 and 800, SUM 750, 950, 1,700, AVERAGE 250, 316.67, 566.67) | Each choice is load-bearing | measured |
| 10 | `QualityExpectation.call_scope` (TABLE, REQUEST_MEMBERS, REQUEST_ROWS), required unless MONITOR. QE_ITEM_GRAIN and QE_FORECAST_DENSE: REQUEST_MEMBERS; the seven referential and consistency checks: REQUEST_ROWS (the fact rows of the requested months and horizons); dimension grains, hierarchies, freshness, horizon: TABLE | Decision 3. An orphan stock row has no item to filter on, so it is scoped by month, not by member | documented (decision), inferred (assignment) |
| 11 | **A data metric function takes at most two table arguments** (`510140`). The forecast reach of decision 4 cannot join QE_HORIZON_LOADED (calendar, snapshot, forecast); it is a new expectation `QE_FORECAST_REACH` on FCT_FORECAST, same refusal `HORIZON_NOT_LOADED` | `CREATE DATA METRIC FUNCTION` with three table arguments refused | measured |
| 12 | `QE_FORECAST_REACH` deployed and run ad hoc: 0, as pandas says (forecast reaches 2029-06, LATEST + 24 is 2028-06). `snowflake/phase2_dmf/results.md` was not rewritten: its 34 checks did not change | `run_dmf.py`, 35 checks, 0 failures | measured |
| 13 | Refusal `DATA_QUALITY_FAILED` (check_order 51) and warning `DATA_QUALITY_ROWS` added: six REFUSE expectations and seven WARN expectations had no code to raise | The procedure needs a code for every in-call outcome | inferred |
| 14 | `HORIZON_NOT_LOADED` reason now names its source (calendar or forecast) and LATEST | Two expectations raise it | inferred |

### Step 2: the procedure generator

| # | Choice | Why, evidence | Tag |
|---|---|---|---|
| 15 | `compiler/procedure_handler.py` is a real Python module holding the mechanism only; `compiler/gen_procedure.py` replaces its `CONTRACT` line with values read from the contract and wraps it in `CREATE PROCEDURE`. No table, physical column, attribute, unit, refusal reason or warning message is written in the handler (a grep finds none; its internal aliases follow DEFINITION.md section 5) | One source; the template stays lintable and testable | inferred |
| 16 | The generator fails when a refusal code has no check function or a check has no code, and when `check_order` breaks a check's prerequisite (for example `AS_OF_NO_SNAPSHOT` before `AS_OF_TOO_MANY`) | The contract's order is executed, so it must be executable | inferred |
| 17 | Language: Python, as probe C0 | Decision 5 | documented |
| 18 | Parameters are VARCHAR (lists and maps as JSON strings), `totals` defaults to `'[]'`. A bare month and a comma-separated grain are still accepted | Probe C0's array finding; the bare forms keep parity with C0's checks | measured (C0), inferred (leniency) |
| 19 | Valid analysis months: snapshot months whose month + 24 is reached by the calendar and by the forecast; LATEST is the latest of them; every answer and refusal carries the list | `analysis_periods.validity` plus decision 4 | documented |
| 20 | Three queries per call: context (caller, months, TABLE checks), quality (REQUEST checks, fan-out, default-scope exclusion) and coverage. The last two start together (`collect_nowait`) once every parameter check has passed; the coverage result is read only if no data check refuses | Fewer sequential round trips | measured (works), see 34 for the cost |
| 21 | The item dimension is joined through `SELECT DISTINCT item_id, <used columns>`; `MASTER_DATA_FANOUT` fires when an item the request reads has several values of a column it uses (the default-scope column included), `MASTER_DATA_DUPLICATES` warns when it has several rows that agree | OD_T7_RESOLUTION, scoped by decision 3 | inferred |
| 22 | `FORECAST_GAPS_FILLED` counts the item x country pairs with at least one forecast row in the horizon, times the horizon months with no row. A pair with no row in the horizon is NO_DEMAND, not a gap. The DMF counts pairs with a forecast anywhere | T2 gives 2, the table 377 | inferred |
| 23 | `DEFAULT_SCOPE_EXCLUDED`: one warning per analysis month with excluded stock, in the unit asked | A series must not add stock across months | inferred |
| 24 | A total must be a strict subset of the grain (equal is refused, `TOTALS_NOT_SUBSET`). On a total grain without a snapshot-only attribute, forecast-only members count; with one, they create no row | `MEMBERS_SPINE` | documented |
| 25 | Quantities are cast to FLOAT before the algorithm | Exact comparisons with traps.yaml (1e-6) | inferred |
| 26 | `STALE_SNAPSHOT` is never raised while its threshold is TBD | Nothing to compare with | inferred |
| 27 | `ASOF` cannot name a CTE (syntax error: it is the ASOF JOIN keyword); the CTE is `analysis_months` | First deployment | measured |
| 28 | `AsyncJob.cancel()` raises `000605` when the query has already finished; the handler ignores it | T7 lifecycle question, first run | measured |

### Step 3: checks (`snowflake/phase3_procedure/results.md`)

| # | Finding | Tag |
|---|---|---|
| 29 | `tests/test_procedure.py`: 63 tests pass: every hero in both units, BULK_SCOPE per unit with its warning, every refusal of traps.yaml in both units, 16 refusal codes, refusal order, one total per hierarchy level (T1), series, invariants on 220 members | measured |
| 30 | 220 members, not 229: the 9 others are BULK-only (stock, never forecast) and the default scope excludes them; the pandas reference with `item_type = STANDARD` gives the same keys | measured |
| 31 | Parity with probe C0: **24 / 25 identical**. The difference is intended: `lifecycle_status` is CONFORMED (C0 refused it as unclassified); the request reads no duplicated item, so 2.8 is right | measured |
| 32 | **A Python procedure spends about 2.2 s before its first query**, the empty one included; an empty Python procedure costs 2.65 s, an empty SQL Scripting one 0.12 s. About 2.5 s of the generated procedure's 4.4 to 4.7 s, and about 70% of C0's 3.5 s, is the Python runtime's fixed cost | measured |
| 33 | In the procedure's own SQL, compilation dominates: about 1.8 s compile against 0.2 s execution summed over the child queries of a single-member call | measured |
| 34 | Concurrency does not pay here: each async result is read back by a `RESULT_SCAN` child query, and the handler waits about 0.6 s beyond the queries themselves | measured |
| 35 | Single member, family with totals and 3-month series are within 0.3 s at the median: the cost is fixed, not proportional | measured |
| 36 | Language (decision 5), on these numbers: the Python fixed cost (about 2.5 s) is larger than all the SQL (1.3 to 2.2 s). A Snowflake Scripting procedure would remove it **[inferred]**; generating validation and the JSON answer in SQL Scripting is the price. Decide after session 7 measures the agent's tool span: if the tool span minus the CALL is small, the language is most of what can be won | measured (costs), inferred (gain) |

### Pre-publication tidy (decision 7)

No em dash is left in any tracked file; empty table cells now read `n/a` (`NULL` in probe A's raw query output,
where the cell is a SQL NULL). En dashes in ranges (T1 to T8, Phases 4 to 5) are not em dashes and stay. Query ids
stay in result files; they are stripped at publication.

### Part 1 open questions

1. Decision 6: closing stock in a generated semantic view with a densified snapshot (proposal, 6), or in the
   procedure? The densified view is not built yet.
2. Decision 5: switch the procedure to Snowflake Scripting (32, 36)? Two cheaper Python changes first: run the three
   queries synchronously (34), and merge quality and coverage into one statement to compile once (33).
3. `HORIZON_NOT_LOADED` and `DATA_QUALITY_FAILED` are implemented but not reachable on v0 data. Exercising them needs
   a broken copy of a table; the procedure reads fully qualified names, so a session TEMPORARY table cannot shadow
   them.
4. `QE_FORECAST_DENSE` counts differently in the DMF (pairs with a forecast anywhere) and in the procedure (pairs with
   a forecast in the horizon, 22). Align the DMF, or keep two readings named apart?
5. `STALE_SNAPSHOT` and the alert thresholds stay TBD (OD_THRESHOLDS).

### First step of session 7 (part 1)

Agent C on the generated procedure: an agent with one `generic` tool bound to `LINKML_METRICS.RAW.STOCK_COVERAGE`,
its `input_schema` and description generated from the contract (`parameters`, `refusal_codes`, `analysis_periods`),
called as `LINKML_SVC`. Then the latency breakdown through the agent: per turn, the `ToolCall` and `SqlExecution`
spans against the orchestration spans, and the CALL's own elapsed time from `QUERY_HISTORY`, to place the 4 to 7 s
the tool adds between Python start (2.5 s), SQL (1.3 to 2.2 s) and the agent's own handling.

## Part 2 (session 7)

> Session 7, 2026-10-03. Same tags: **[documented]**, **[measured]** (evidence in the repository), **[inferred]**.
> The contract moved from 0.2.0 to 0.2.1 (a failure mode, no rule changed), then to 0.3.0 (QE_FORECAST_DENSE's
> condition changed). Agent C, built on this part, is in [phase 4 notes](phase4_notes.md).

### Step 0: generated closing stock and trap T9 (`snowflake/probe_closing/results.md`, session 7 section)

| # | Choice or finding | Why, evidence | Tag |
|---|---|---|---|
| 37 | Closing stock is answered by a **generated semantic view** `CLOSING_STOCK_SV` over a **gap-filled snapshot view** `FCT_STOCK_SNAPSHOT_GAPFILLED`, both written by `compiler/gen_closing_sv.py` into `generated/closing_stock_sv.sql`. The procedure stays coverage only | Decision 1 of session 7 (open question 1 of part 1) | documented |
| 38 | Gap filling: every batch x warehouse key gets one row per month from its first snapshot month to its last + 1, capped at the latest snapshot month; measures 0 where absent, other columns carried from the key's last row (`LAST_VALUE ... IGNORE NULLS`), a `gap_filled` flag | One 0 row after a key's last month is what `NON ADDITIVE BY` needs to find the period's last month in every group (finding 6) | inferred (design), measured (result) |
| 39 | **The last-known-value trap is gone**: SKU-H11 x Q2 2026 is 0 (native 350); SKU-H12 450, SNACK_BARS 450; month grain shows 0 rows where native showed none; SKU rows add up to the family row | Four probe queries, both views | measured |
| 40 | Cost: 2,513 rows added to 60,915 (+4.13 %), stock total unchanged | `run_closing_generated.py` | measured |
| 41 | Sweep: SKU x country x quarter, generated 0 failures of 2,702 (native 1, the hero); family x country x quarter, 12 failures in both views, all T7 (SKU-H06 counted twice, Q2 2026 1,500 against 900) | A semantic view cannot refuse at query time; the `SELECT DISTINCT` projection still holds `lifecycle_status`, on which the duplicate differs | measured |
| 42 | The default scope (`item_type = STANDARD`) is **not** applied to closing stock: it is a coverage rule (BULK has no forecast); stock on hand is stock on hand | Not stated by the contract for the snapshot measure alone | inferred |
| 43 | New trap **T9 (stale stock in coverage)**, failure mode in contract 0.2.1, on the SKU-H11 x CH hero: expected 0 (NO_STOCK), wrong 3.5 (May's 350 over 100 a month). `check_dataset.py` recomputes the wrong value through the legacy cascade; `tests/test_contract.py` and `tests/test_procedure.py` assert both | No trap without a rule; the rule is the NO_STOCK outcome (stock read at exactly the analysis month) | measured |
| 44 | Native coverage views get T9 right only with a month filter equal to AS_OF. With a range, a quarter or no month they pick May's 350 **and** sum the forecast over every analysis month kept: 1.1667 or 0.0493, a plausible wrong number. Reading stock from the gap-filled view removes the stale stock (0 in every form) but not the summed forecast | `run_t9.py` on B1, B2, B2 + quarter and a gap-filled probe copy | measured |

### Step 1: cheap latency wins (`snowflake/phase3_procedure/results.md`, session 7 section)

| # | Choice or finding | Why, evidence | Tag |
|---|---|---|---|
| 45 | Two cheaper changes before any language switch: **sync** (quality then coverage, no `RESULT_SCAN`) and **single** (one statement). Keep one only if every test is green and the median drops | Decision 2 of session 7 | documented |
| 46 | **Neither kept.** Median CALL, single member: async 3,855 ms, sync 4,433, single 4,174; family with totals 4,418 / 5,012 / 4,787; series 4,479 / 4,582 / 4,293 | Compilation dominates and the two async queries compile in parallel (about 0.75 s and 0.88 s overlapping, against 1.2 s for the single statement) | measured |
| 47 | The fixed cost stays about 2.2 s before the first query, in every Python procedure; compile time of a same statement varies by about 0.6 s between calls, so gains below that need more than 5 calls per shape | Witnesses (empty Python procedure, C0) in the same runs | measured |

### Step 2: QE_FORECAST_DENSE aligned (`snowflake/phase2_dmf/results.md`, session 7 section)

| # | Choice or finding | Why, evidence | Tag |
|---|---|---|---|
| 48 | Contract **0.3.0**: the DMF counts the missing months of the **horizon window of LATEST** for the item x country pairs with a forecast row in that window, as the procedure does for a request. A condition changed, hence a minor version | Decision 3 of session 7 (open question 4 of part 1) | documented |
| 49 | 169 on v0 (was 377), **equal to the procedure's `FORECAST_GAPS_FILLED`** for a call on every SKU x country at LATEST (169), a new must-check of `run_dmf.py`; T2 still contributes 2; 35 checks, 0 failures | `run_dmf.py` | measured |
| 50 | **A DMF body refuses `SEQ4`** (510101, non-deterministic function); the 24 horizon periods are a literal `VALUES (1), ..., (24)` list and LATEST is `MAX(snapshot_month)` of the table argument | First deployment | measured |
| 51 | The DMF reads LATEST as the table's latest snapshot month, not the validity rule's LATEST (whose horizon must be loaded). Equal on v0 | A DMF takes at most two tables (finding 11); the forecast reach is a separate expectation | inferred |

### Part 2 open questions

1. T7 in the closing view: the family x country sweep fails on PANTRY_OIL x SE (finding 41). Drop
   `lifecycle_status` from the closing view's item projection, or accept that a semantic view cannot refuse?
2. Default scope on closing stock (42): confirm that closing stock includes BULK.
3. `expiry_bucket` and the other batch columns are carried onto the filled 0 rows; harmless for the stock (0) but a
   0 row can appear in a bucket the batch has left. Acceptable?
4. The gap-filling cap is the latest snapshot month, equal to LATEST on v0 (51): one definition or two?
