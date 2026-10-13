# Session 8b: agent C rebuilt on a SQL Scripting procedure (raw results)

Contract 0.4.2 (0.4.1 at the start), charter `docs/configurations.md` version 6 at the start. Setup as perso,
`USE SECONDARY ROLES NONE`, `LINKML_METRICS_ROLE`. Tags: **[documented]** (Snowflake documentation, cited by page),
**[measured]** (run on this account, evidence here or in `~/work/assets/linkml-metrics-runs/s8b/`, outside the
repository), **[inferred]**.

## Step 0: parity checklist

`parity_checklist.md`, with the owner's answers of 2026-10-04 folded in (section 0). Committed before any code.

## Step 1: the four open behaviours, measured in throwaway anonymous blocks (`probe_scripting.py`)

Run log: `probe_scripting.json` (run folder). No object created.

| # | Behaviour | Result | Documentation |
|---|---|---|---|
| M1 | `ASYNC (EXECUTE IMMEDIATE :q USING (j, j))` assigned to a RESULTSET, `AWAIT`, read with a cursor | works; two binds read from one JSON string | asynchronous child jobs page documents `ASYNC` on a RESULTSET; `EXECUTE IMMEDIATE` inside `ASYNC` is not mentioned [documented: https://docs.snowflake.com/en/developer-guide/snowflake-scripting/asynchronous-child-jobs, https://docs.snowflake.com/en/developer-guide/snowflake-scripting/resultsets] |
| M2 | Query id of an `ASYNC` child | `SQLID` read right after the `ASYNC` assignment is the child's query id (two children, each id checked from outside the block in `QUERY_HISTORY_BY_SESSION` against its text); after `AWAIT`, `SQLID` keeps the last assigned child's id | the query-id page documents `SQLID` for the last query, not for asynchronous children; the async page calls `LAST_QUERY_ID` non-deterministic with children [documented: https://docs.snowflake.com/en/developer-guide/snowflake-scripting/query-id] [measured] |
| M3 | `CANCEL` | on a finished child: no error; on a running child (`SYSTEM$WAIT(5)`): returns at once, the status read right after is still `RUNNING`, the child ends `FAILED_WITH_ERROR` about 1 s later; a child still running when the block returns is cancelled too (the block returned in 153 ms, its 3 s child failed after about 1 s) | `CANCEL` documented for children running for a RESULTSET; behaviour at return not documented [documented, async page] [measured] |
| M4 | `PARSE_JSON` / `TRY_PARSE_JSON` | default mode is lenient: single quotes accepted, a trailing comma becomes `undefined`, `NaN` accepted, duplicate keys rejected; with the `'d'` parameter the parser is strict like the reference (rejects single quotes and trailing commas, keeps the last duplicate key), `NaN` still accepted. A JSON `1.0` parses as INTEGER 1 (the integer/float distinction is lost; `2026.5` is DECIMAL, `1e16` DOUBLE). `OBJECT_CONSTRUCT` drops NULL values, `OBJECT_CONSTRUCT_KEEP_NULL` keeps them | [measured] |

Owner's rule applied: no read of QUERY_HISTORY, INFORMATION_SCHEMA or ACCOUNT_USAGE inside the procedure; the
query id of each asynchronous child comes from `SQLID` (M2).

Exceptions: custom exception declared in DECLARE, `RAISE`, `WHEN <exception> THEN`, variables of DECLARE readable in
the handler, `RETURN` allowed in a handler [documented: https://docs.snowflake.com/en/developer-guide/snowflake-scripting/exceptions];
a handler of a nested block sees the outer block's variables [measured].

## Step 1: what a Snowflake Scripting procedure costs (measured, anonymous blocks and the procedure itself)

The first two versions of the generated procedure (a generic Scripting body over one JSON literal of the contract,
then the same with fewer variables) returned the right numbers in 8.6 to 10.2 s per CALL against 4 to 5 s for the
Python procedure. What the measurements found, in order:

| # | Finding | Evidence |
|---|---|---|
| S1 | Most Scripting expressions run in the block with no child query: `TRY_PARSE_JSON`, `REGEXP_LIKE`, `OBJECT_CONSTRUCT_KEEP_NULL`, `ARRAY_*`, `CURRENT_TIMESTAMP`. `SYSTIMESTAMP()` and `SYSDATE()` each run as a child query (`SELECT CAST ((SYSTIMESTAMP()) AS TIMESTAMP_LTZ(9))`, about 45 ms). `CURRENT_TIMESTAMP()` advances between statements of one block (1,170 ms across a 1 s wait) | probes m5, m11, m12; CALL breakdown of version 1 |
| S2 | **Each distinct Scripting statement costs about 15 ms the first time it runs**; the same statement repeated in a loop costs about 1 ms. 100 distinct trivial assignments: 1.5 s; 100 distinct IF: 1.9 s; one loop of 100 iterations of one statement: 0.12 s | probe m26 |
| S3 | Hence the cost of a Scripting body is the number of distinct statements it executes, not the size of its data: a 13 KB VARIANT variable, 40 more declared variables (NULL or filled, ARRAY, OBJECT or VARCHAR), or a handler block change a looped statement's cost by at most 0.1 ms | probes m14, m21, m25 |
| S4 | SQL lambdas (`TRANSFORM`, `FILTER`, `REDUCE`) are rejected in Scripting expressions (`invalid identifier`), accepted in SQL statements; inside a statement a lambda may read a column of the query, and lambdas may nest, but an inner lambda cannot read the outer lambda's parameter (`invalid identifier 'N'`) | probes m10, lambda checks; first deploy of version 3 |
| S5 | `ARRAY_EXCEPT` has multiset semantics (`[a,b,b,b,c] - [b,c] = [a,b,b]`); `ARRAY_SORT` sorts strings in code-point order (`B, _x, a, b`), as Python does. **`ARRAY_INTERSECTION` does not keep the order of its first argument**: it did on a 5 x 4 probe, and returned `[sku_code, country_code, family_code]` for the 13-name declaration order intersected with `[sku_code, country_code, family_code]` (12 parity cases and 1 test failed on it, parity run 2). The procedure orders with `FILTER(order, x -> ARRAY_CONTAINS(x, names))` instead, and deduplicates with `ARRAY_POSITION` (first occurrence kept) instead of `ARRAY_DISTINCT`, whose order is not documented either. Inside a lambda over `ARRAY_GENERATE_RANGE`, the index is a VARIANT: `GET(a, i)` and `ARRAY_POSITION(...) = i` need `i::INT`, or the filter silently keeps nothing (parity run 3, stopped after two cases) | probes m6, m11, lambda checks; parity runs 2 and 3 |
| S6 | A SQL statement that does the parsing, the checks and the text assembly in one piece compiles in 2.2 to 3.1 s (40 KB, execution 0.1 s). Split into one context statement and four statements that read no table, started together with `ASYNC`, each compiles in 0.3 to 0.5 s and they overlap | probes m24, m27; CALL breakdowns |
| S7 | Version 3 (the shape kept): one statement that reads no table for the as_of_months checks (and the caller block), the context statement, four statements that read no table (the other parameter checks with the normalised request, the text of the data statements in three parts), then the quality and coverage statements; about 40 distinct Scripting statements on the happy path. Single member (T2), 5 calls: 2.85 to 3.61 s inside the procedure (`total_ms`), CALL 3.1 to 3.9 s from the client; a refusal on a parameter after the context: 1.1 to 1.5 s | split.py runs |

Breakdown of one version-3 CALL (T2, 3.24 s): block start and compilation 0.23 s; the four statements that read no
table from 0.23 to 0.89 s (compile 0.28 to 0.47 s each, overlapping); the as_of statement 0.44 to 0.84 s; the
context statement 0.91 to 1.32 s; cursor reads 1.32 to 1.64 s; quality and coverage 1.64 to 3.05 s (compile 1.27
and 1.17 s, overlapping); answer 3.05 to 3.24 s. [measured]

Lineage: the answer's `lineage.query_ids` names the statements that read data (context, quality, coverage), as the
Python procedure's did. The statements that read no table (the as_of checks, the parameter checks, the three text
parts) are not in it, as the Python procedure's Snowpark start-up queries and caller-only statement were not.
[decision for the owner, see the step 2 stop]

## Step 1: generator, tests, deployment

- `compiler/gen_procedure.py` gains `--target sql` (`compiler/procedure_scripting.py`); both targets written by
  default; `generated/stock_coverage_procedure_sql.sql` creates `LINKML_METRICS.RAW.STOCK_COVERAGE_SQL` (decision 2,
  `SWAPPED = False`). `--schema` retargets a test deployment (decision 4), never the committed files.
- The checks are in three stages, each code in exactly one (as_of statement: 10 to 13; context statement: 14, 15;
  parameter statement: 20 to 39; data: 50, 51); the generator asserts that every contract code has a check, every
  check a code, and that the stages follow check_order.
- Owner's answers applied to the Python handler first (tests first, 5 failing before the change):
  `MASTER_DATA_FANOUT` with values (contract 0.4.2), declaration order for several faulty attributes, compact JSON for
  a nested value. Python procedure redeployed (`00000251-0000-4000-8000-000000000251`).
- Tests: drift test covers both generated files; `test_sql_procedure_shares_no_code_with_the_reference_implementations`
  (no import of, and no shared code line with, `data/coverage_ref.py`, `data/checks/check_dataset.py`,
  `docs/check_coverage_formula.py`, the skill's `coverage.py`); `tests/test_procedure.py` runs against either
  procedure (`LINKML_PROC`); the two-attribute fan-out test replays the statement each procedure ran.
- `tests/test_procedure.py`: **87 passed on STOCK_COVERAGE (Python)** (8 min) and **87 passed on STOCK_COVERAGE_SQL**
  (6 min). Rest of the suite: 157 passed, **1 failed**: `test_native_b2_enriched_yaml_differs_only_by_grounding`,
  because contract 0.4.2 changes the version string in the generated B2 view description ("generated from contract
  stock_coverage 0.4.2") while the deployed and committed enriched YAML says 0.4.1. B2 not redeployed (owner's
  decision, step 2 stop).
- Last deployment of STOCK_COVERAGE_SQL: `00000252-0000-4000-8000-000000000252`.

## Step 2: parity by direct CALL (`parity.py`, run 4)

Same argument strings to both procedures, 134 cases: the cases of `tests/test_procedure.py` (heroes in both units,
related and refusal cases, totals at every level with their separate calls, series, the invariant member sets,
default scope), the 13 coverage questions of `generated/reference_questions.yaml`, and the extra parsing cases of the
checklist. Compared as parsed JSON, query id values and `timing_ms` removed, numbers within 1e-9.
**134 / 134 identical** [measured]. Run log `parity_run4.json` (both answers per case), run folder.

Earlier runs, kept: run 2, 122 / 134 (12 differences, all one defect: `ARRAY_INTERSECTION` order, finding S5);
run 3 stopped after two cases (index type in a lambda, finding S5); run 1 (first architecture) stopped for latency.

| Case | Status | Code | Coverage (single DETAIL row) or rows | Identical |
|---|---|---|---|---|
| hero T1 QTY_EQ | ok |  | 2.8 | yes |
| hero T2 QTY_EQ | ok |  | 7.0 | yes |
| hero T3 QTY_EQ | ok |  | 6.0 | yes |
| hero T4 QTY_EQ | ok |  | 8.5 | yes |
| hero T7 QTY_EQ | ok |  | 2.25 | yes |
| hero T8 QTY_EQ | ok |  | 0.0 | yes |
| hero NO_DEMAND QTY_EQ | ok |  | null | yes |
| hero BEYOND_H QTY_EQ | ok |  | 50.0 | yes |
| hero T9 QTY_EQ | ok |  | 0.0 | yes |
| hero BULK_SCOPE QTY_EQ | ok |  | 8.67354124748491 | yes |
| T3 hold QTY_EQ | ok |  | 4.0 | yes |
| T3 all QTY_EQ | ok |  | 10.0 | yes |
| T3 by status QTY_EQ | ok |  | 2 rows | yes |
| BULK explicit QTY_EQ | ok |  | 17.44238782051282 | yes |
| T6 refusal QTY_EQ | refused | AS_OF_MISSING |  | yes |
| T7 lifecycle refusal QTY_EQ | refused | MASTER_DATA_FANOUT |  | yes |
| T5 raw refusal QTY_EQ | refused | UNIT_RAW_NOT_ADDITIVE |  | yes |
| hero T1 VALUE | ok |  | 2.8 | yes |
| hero T2 VALUE | ok |  | 7.0 | yes |
| hero T3 VALUE | ok |  | 6.0 | yes |
| hero T4 VALUE | ok |  | 8.5 | yes |
| hero T7 VALUE | ok |  | 2.25 | yes |
| hero T8 VALUE | ok |  | 0.0 | yes |
| hero NO_DEMAND VALUE | ok |  | null | yes |
| hero BEYOND_H VALUE | ok |  | 50.0 | yes |
| hero T9 VALUE | ok |  | 0.0 | yes |
| hero BULK_SCOPE VALUE | ok |  | 8.282089597433156 | yes |
| T3 hold VALUE | ok |  | 4.0 | yes |
| T3 all VALUE | ok |  | 10.0 | yes |
| T3 by status VALUE | ok |  | 2 rows | yes |
| BULK explicit VALUE | ok |  | 22.11995161601408 | yes |
| T6 refusal VALUE | refused | AS_OF_MISSING |  | yes |
| T7 lifecycle refusal VALUE | refused | MASTER_DATA_FANOUT |  | yes |
| T5 raw refusal VALUE | refused | UNIT_RAW_NOT_ADDITIVE |  | yes |
| T1 children | ok |  | 2 rows | yes |
| T9 May | ok |  | 3.5 | yes |
| T5 QTY_EQ | ok |  | 2.365055456661646 | yes |
| LATEST | ok |  | 2.8 | yes |
| AS_OF_MISSING empty | refused | AS_OF_MISSING |  | yes |
| AS_OF_MISSING [] | refused | AS_OF_MISSING |  | yes |
| AS_OF_INVALID text | refused | AS_OF_INVALID |  | yes |
| AS_OF_INVALID unclosed | refused | AS_OF_INVALID |  | yes |
| AS_OF_NOT_MONTH_START | refused | AS_OF_NOT_MONTH_START |  | yes |
| AS_OF_TOO_MANY | refused | AS_OF_TOO_MANY |  | yes |
| AS_OF_NO_SNAPSHOT | refused | AS_OF_NO_SNAPSHOT |  | yes |
| AS_OF_NO_SNAPSHOT two | refused | AS_OF_NO_SNAPSHOT |  | yes |
| UNIT_RAW_NOT_ADDITIVE | refused | UNIT_RAW_NOT_ADDITIVE |  | yes |
| UNIT_UNKNOWN | refused | UNIT_UNKNOWN |  | yes |
| GRAIN_MALFORMED | refused | GRAIN_MALFORMED |  | yes |
| GRAIN_EMPTY | refused | GRAIN_EMPTY |  | yes |
| GRAIN_DUPLICATE | refused | GRAIN_DUPLICATE |  | yes |
| FILTERS_MALFORMED | refused | FILTERS_MALFORMED |  | yes |
| FILTER_VALUES_INVALID | refused | FILTER_VALUES_INVALID |  | yes |
| ATTRIBUTE_UNKNOWN | refused | ATTRIBUTE_UNKNOWN |  | yes |
| TOTALS_MALFORMED | refused | TOTALS_MALFORMED |  | yes |
| TOTALS_NOT_SUBSET region | refused | TOTALS_NOT_SUBSET |  | yes |
| TOTALS_NOT_SUBSET grain | refused | TOTALS_NOT_SUBSET |  | yes |
| MASTER_DATA_FANOUT | refused | MASTER_DATA_FANOUT |  | yes |
| order 1 | refused | AS_OF_NOT_MONTH_START |  | yes |
| order 2 | refused | UNIT_RAW_NOT_ADDITIVE |  | yes |
| order 3 | refused | GRAIN_EMPTY |  | yes |
| key order 1 | refused | FILTER_VALUES_INVALID |  | yes |
| key order 2 | refused | FILTER_VALUES_INVALID |  | yes |
| key order 3 | refused | ATTRIBUTE_UNKNOWN |  | yes |
| key order 4 | refused | ATTRIBUTE_UNKNOWN |  | yes |
| dup order 1 | refused | GRAIN_DUPLICATE |  | yes |
| dup order 2 | refused | GRAIN_DUPLICATE |  | yes |
| nested as_of | refused | AS_OF_INVALID |  | yes |
| as_of integer item | refused | AS_OF_INVALID |  | yes |
| as_of bool item | refused | AS_OF_INVALID |  | yes |
| as_of float item | refused | AS_OF_INVALID |  | yes |
| as_of null item | refused | AS_OF_INVALID |  | yes |
| as_of blank list | refused | AS_OF_MISSING |  | yes |
| as_of object | refused | AS_OF_INVALID |  | yes |
| as_of comma list | ok |  | 2 rows | yes |
| as_of latest lower | ok |  | 2.8 | yes |
| as_of bad day | refused | AS_OF_INVALID |  | yes |
| as_of single quotes | refused | AS_OF_INVALID |  | yes |
| as_of trailing comma | refused | AS_OF_INVALID |  | yes |
| unit lower hyphen | ok |  | 2.8 | yes |
| unit synonym | ok |  | 2.8 | yes |
| unit raw spaced | refused | UNIT_RAW_NOT_ADDITIVE |  | yes |
| unit null | refused | UNIT_UNKNOWN |  | yes |
| grain comma list | ok |  | 2.8 | yes |
| grain null | refused | GRAIN_EMPTY |  | yes |
| grain number item | refused | GRAIN_MALFORMED |  | yes |
| filters null | ok |  | 4 rows | yes |
| filters scalar value | ok |  | 2.8 | yes |
| filters numeric value | ok |  |  | yes |
| filters null value | refused | FILTER_VALUES_INVALID |  | yes |
| filters bool item | refused | FILTER_VALUES_INVALID |  | yes |
| filters duplicate key | ok |  | 2.8 | yes |
| filters upper key | ok |  | 2.8 | yes |
| filters text | refused | FILTERS_MALFORMED |  | yes |
| totals text | refused | TOTALS_MALFORMED |  | yes |
| totals duplicate | ok |  | 2.8 | yes |
| totals bad item | refused | TOTALS_MALFORMED |  | yes |
| totals repeated name | refused | TOTALS_NOT_SUBSET |  | yes |
| totals null | ok |  | 2.8 | yes |
| totals ['sku_code', 'country_code'] -> ['country_code'] | ok |  | 3 rows | yes |
| separate ['country_code'] | ok |  | 2.8 | yes |
| totals ['sku_code', 'family_code'] -> ['family_code'] | ok |  | 3 rows | yes |
| separate ['family_code'] | ok |  | 2.25 | yes |
| totals ['family_code', 'range_code'] -> ['range_code'] | ok |  | 4 rows | yes |
| separate ['range_code'] | ok |  | 9.659779188417396 | yes |
| totals ['country_code', 'region_code'] -> ['region_code'] | ok |  | 5 rows | yes |
| separate ['region_code'] | ok |  | 8.886141345237498 | yes |
| totals ['region_code'] -> [] | ok |  | 5 rows | yes |
| separate grand | ok |  | 5 rows | yes |
| no total across months | ok |  | 6 rows | yes |
| members all | ok |  | 220 rows | yes |
| members released | ok |  | 220 rows | yes |
| series ['2026-04-01', '2026-05-01', '2026-06-01'] | ok |  | 63 rows | yes |
| series ['2026-04-01'] | ok |  | 21 rows | yes |
| series ['2026-05-01'] | ok |  | 21 rows | yes |
| series ['2026-06-01'] | ok |  | 21 rows | yes |
| T3 series | ok |  | 3 rows | yes |
| default scope explicit STANDARD | ok |  | 8.67354124748491 | yes |
| by item_type no filter | ok |  | 8.67354124748491 | yes |
| VALUE T1 grand total | ok |  | 2.8 | yes |
| question T1 | ok |  | 2.8 | yes |
| question T2 | ok |  | 7.0 | yes |
| question T3 | ok |  | 6.0 | yes |
| question T4 | ok |  | 8.5 | yes |
| question T5 | refused | UNIT_RAW_NOT_ADDITIVE |  | yes |
| question T6 | refused | AS_OF_MISSING |  | yes |
| question T7 | ok |  | 2.25 | yes |
| question T7_R1 | refused | MASTER_DATA_FANOUT |  | yes |
| question T8 | ok |  | 0.0 | yes |
| question NO_DEMAND | ok |  | null | yes |
| question BEYOND_H | ok |  | 50.0 | yes |
| question BULK_SCOPE | ok |  | 8.67354124748491 | yes |
| question T9 | ok |  | 0.0 | yes |
| question BULK_SCOPE_DRILL | ok |  | 6 rows | yes |
Not reachable on v0 data, so not in this table: `HORIZON_NOT_LOADED`, `DATA_QUALITY_FAILED` (decision 4, clone plan
at the step 2 stop), `ATTRIBUTE_UNCLASSIFIED`, `ATTRIBUTE_NOT_APPLICABLE` (no such attribute in the contract).
Known divergence kept: none found on the 134 cases. Not exercised: an integral float inside `as_of_months` written
with 4 digits or more (Python shows 2026.0 as "2,026", the SQL procedure reads it as the integer 2026: finding M4),
and an integral float filter value (Python "1.0", SQL "1"). Rounding ties at the fifth decimal: none met.

## Step 2: direct latency (`latency.py`), warm warehouse, 5 calls per hero case and procedure, alternating

| Case | Python median CALL ms (min / max) | SQL median CALL ms (min / max) |
|---|---|---|
| T1 | 4,361 (4,264 / 4,690) | 3,482 (3,436 / 3,632) |
| T2 | 4,581 (4,370 / 6,048) | 3,334 (3,273 / 4,046) |
| T3 | 4,559 (4,449 / 4,683) | 3,710 (3,513 / 4,024) |
| T4 | 4,555 (4,422 / 4,579) | 3,545 (3,415 / 4,036) |
| T7 | 4,598 (4,467 / 6,133) | 3,547 (3,305 / 3,952) |
| T8 | 4,480 (4,440 / 4,789) | 3,574 (3,411 / 4,092) |
| NO_DEMAND | 4,641 (4,433 / 4,649) | 3,539 (3,387 / 4,334) |
| BEYOND_H | 4,494 (4,440 / 5,716) | 3,322 (3,236 / 3,457) |
| BULK_SCOPE | 4,537 (4,488 / 4,667) | 2,993 (2,973 / 3,036) |
| T9 | 4,671 (4,563 / 5,238) | 3,494 (3,301 / 4,284) |
| **All, n = 50 each** | **4,550 (4,264 / 6,133)** | **3,476 (2,973 / 4,334)** |

Child queries per CALL (median): Python 10 (five Snowpark start-up queries, context, quality, coverage, two
`RESULT_SCAN`), SQL 8 (four statements that read no table, the as_of statement, context, quality, coverage).
[measured; `latency_direct.json` in the run folder]

Reading against the agent's tool-span points (0.5, 1.2, 2.6, 4.3, 8.5 s, phase 4 notes findings 43 and 52): every
SQL CALL ended before 4.34 s and the median is 3.5 s, so the tool span should end at the 4.3 s point, and not at
2.6 s, against 8.5 s for the Python procedure (all its CALLs are above 4.26 s). The slowest SQL CALL (4.33 s) is at
the edge of the 4.3 s point. [inferred from measured CALL times; to measure at the smoke]

## Step 2: decision 4 on zero-copy clones (`clone_cases.py`), owner's plan of 2026-10-04

Schema `LINKML_METRICS.S8B_DQ_TEST` (created and owned by LINKML_METRICS_ROLE, which owns the database: no grant
added), one zero-copy clone per RAW table, both procedures generated with `--schema` and created there. RAW never
written. Each defect on a fresh clone of the table it changes, two requests per defect on both procedures: T1's
(grain `family_code, country_code`, filters PANTRY_FLOUR and FR: uses DIM_GEO's columns) and one with grain and
filter `family_code` only (no DIM_GEO column; the calendar and the forecast have no attribute of the contract).
Run log `clone_cases.json` (run folder). `DROP SCHEMA ... CASCADE` at the end; `SHOW SCHEMAS LIKE 'S8B_DQ_TEST'`
then empty. [measured]

| Defect (change on the clone) | Request | Python | SQL | Same code and message |
|---|---|---|---|---|
| Calendar cut after 2028-05-01 | uses DIM_GEO | HORIZON_NOT_LOADED: "The calendar does not reach 2028-06-01, the end of the 24-month horizon of 2026-06-01." | same | yes |
| same | does not | same refusal | same | yes |
| Forecast cut after 2028-05-01 | uses DIM_GEO | HORIZON_NOT_LOADED: "The forecast does not reach 2028-06-01, the end of the 24-month horizon of 2026-06-01." | same | yes |
| same | does not | same refusal | same | yes |
| DIM_GEO row of FR duplicated | uses DIM_GEO | DATA_QUALITY_FAILED: "Quality expectation QE_GEO_GRAIN fails (1 violations): one row per country_id. No number is returned until it is fixed." | same | yes |
| same | does not | same refusal | same | yes |
| New country_id with code FR in region NORDIC | uses DIM_GEO | DATA_QUALITY_FAILED: "Quality expectation QE_COUNTRY_REGION fails (1 violations): each country_code maps to one region_code. No number is returned until it is fixed." | same | yes |
| same | does not | same refusal | same | yes |

**8 / 8 same code and message.** Finding [measured, against the owner's expectation]: the requests that do not use
the faulty columns are refused too, by both procedures. These expectations are declared `call_scope: TABLE` with
`on_failure: REFUSE` (and `REFUSE` for the horizon) in the contract: they refuse every call while the table fails,
whatever the query uses. Only `QE_ITEM_GRAIN` (`REFUSE_IF_USED`, call scope `REQUEST_MEMBERS`) depends on the columns
a query uses. Not a parity defect; a contract rule for the owner.

The third branch of HORIZON_NOT_LOADED ("calendar or forecast", an analysis month that has a snapshot but is not
available) is **unreachable by construction**: it is checked only after the two table-scope checks pass, that is
after the calendar and the forecast both reach LATEST + 24; every snapshot month is then at most LATEST, so its
horizon is loaded and it is available. [inferred from the contract's rules and the procedure's order]

## Step 2: swap (decision 2, pre-approved)

Every clone case gave the same code and message: `SWAPPED = True` in `compiler/gen_procedure.py`;
`LINKML_METRICS.RAW.STOCK_COVERAGE_PY` (Python) created `00000253-0000-4000-8000-000000000253`;
`LINKML_METRICS.RAW.STOCK_COVERAGE` (SQL Scripting, `LANGUAGE SQL`, `EXECUTE AS CALLER`) created
`00000254-0000-4000-8000-000000000254`; `STOCK_COVERAGE_SQL` dropped `00000255-0000-4000-8000-000000000255`.
`tests/test_procedure.py` now runs against `STOCK_COVERAGE` (SQL) by default, `LINKML_PROC` for the Python one;
`parity.py` and `latency.py` name the two procedures after the swap. No procedure changed after parity run 4.

## Step 3: B2 semantic view redeployed (owner's answer 5), no agent call

`b2/apply_grounding.py` copied `is_enum` and `sample_values` of the deployed enriched YAML onto the regenerated
`generated/b2_native_sv.yaml` (18 members, as before); the only other difference is the contract version in the
view's description (0.4.1 to 0.4.2). `deploy_sv.py`: dry run `00000256-0000-4000-8000-000000000256`, create
`00000257-0000-4000-8000-000000000257`; read back: 124 members, same names, `is_enum` and `sample_values` equal to the
file, the 2 verified queries. [measured]

Full suite once after the swap (`pytest_full_after_swap.log`): 244 passed, 1 failed,
`test_native_b2_enriched_yaml_differs_only_by_grounding` (B2's view not yet redeployed when it ran). After the B2
redeployment, `tests/test_generated.py` and `tests/test_extracted_instructions.py`: 22 passed. [measured]

## Step 3: charter version 7 and the C spec, prepared, not published

Shown to the owner before any CREATE or ALTER (step 3 stop). Files changed: `compiler/gen_native_sv.py` (common
response), `generated/agent_b2.yaml`, `snowflake/phase4_others/{a/agent_a,b1/agent_b1,d/agent_d,d/agent_dp}.yaml`
(response only), `compiler/gen_agent.py` and `generated/agent_c.yaml` (decision 5), `docs/configurations.md`
(version 7).

## Step 3: publication (owner's go, 2026-10-04 22:20), no agent call

`snowflake/phase4_others/agents.py publish` (five-beat cycle: MODIFY LIVE, COMMIT, ADD LIVE VERSION FROM LAST, SET
DEFAULT_VERSION read from SHOW VERSIONS; the fifth beat is the first smoke call for C, none for the others).
Log `publish.log` (run folder). [measured]

| Agent | Spec file | MODIFY LIVE | COMMIT | ADD LIVE | SET DEFAULT | Default | LIVE and default equal to file | DESCRIBE equal to file |
|---|---|---|---|---|---|---|---|---|
| LINKML_C | `generated/agent_c.yaml` | `00000258-0000-4000-8000-000000000258` | `<query-id>` | `00000259-0000-4000-8000-000000000259` | `0000025a-0000-4000-8000-00000000025a` | VERSION$3 | yes | yes |
| LINKML_A | `a/agent_a.yaml` | `0000025b-0000-4000-8000-00000000025b` | `0000025c-0000-4000-8000-00000000025c` | `<query-id>` | `0000025d-0000-4000-8000-00000000025d` | VERSION$3 | yes | yes |
| LINKML_B1 | `b1/agent_b1.yaml` | `0000025e-0000-4000-8000-00000000025e` | `<query-id>` | `0000025f-0000-4000-8000-00000000025f` | `00000260-0000-4000-8000-000000000260` | VERSION$4 | yes | yes |
| LINKML_B2 | `generated/agent_b2.yaml` | `00000261-0000-4000-8000-000000000261` | `00000262-0000-4000-8000-000000000262` | `00000263-0000-4000-8000-000000000263` | `00000264-0000-4000-8000-000000000264` | VERSION$4 | yes | yes |
| LINKML_D | `d/agent_d.yaml` | `00000265-0000-4000-8000-000000000265` | `00000266-0000-4000-8000-000000000266` | `00000267-0000-4000-8000-000000000267` | `00000268-0000-4000-8000-000000000268` | VERSION$4 | yes | yes |
| LINKML_DP | `d/agent_dp.yaml` | `00000269-0000-4000-8000-000000000269` | `<query-id>` | `<query-id>` | `0000026a-0000-4000-8000-00000000026a` | VERSION$4 | yes | yes |

Every earlier version differs from its file (the response sentence of charter version 7; for C, the rebuild).
Role LINKML_METRICS_ROLE, no secondary role. STOCK_COVERAGE_PY kept (owner).

## Step 4: smoke of C (calls 1 to 10 of budget s8b)

`smoke.py run C LINKML_C ... --policy deny-all` with `LINKML_RUN=s8b`, as LINKML_SVC (key-pair JWT, no role header),
warehouse warm before each call (GENERATOR sum, STARTED: 10 of 10). **UTC window: 2026-10-04 20:19:18.9 (call 1
sent) to 20:31:44.2 (call 10 answered).** 10 calls, 10 status 200, no `response.warning`, no approval. Version served:
`VERSION$3` (the default) on every turn. Reserve (4 calls): not used. Logs, summaries, traces, grades and records in
the run folder (`smoke_run.log`, `smoke_grades.txt`, `smoke_records.md`). [measured]

| # | Id | Expected route | Tools called (parameters) | Grade (rubric v2) | Warnings, flags, refusal relayed | Computed by | Request id |
|---|---|---|---|---|---|---|---|
| 1 | T1 | stock_coverage | stock_coverage (`["2026-06-01"]`, QTY_EQ, grain family_code, country_code; PANTRY_FLOUR, FR) | **correct**: 2.8, month named, no aggregation, routing | none returned; "no flags or warnings" | tool | `0000016e-0000-4000-8000-00000000016e` |
| 2 | T2 | stock_coverage | stock_coverage (SKU-H03, DE) | **correct**: 7.0 | FORECAST_GAPS_FILLED with its count 2, explained | tool | `00000173-0000-4000-8000-000000000173` |
| 3 | T5 | stock_coverage | stock_coverage with **QTY_EQ** (PANTRY_PASTA, GB) | **correct**, class `model_refusal_with_qty_eq_answer` (deviation, decision 7): packs refused by the model, 2.37 answered in QTY_EQ | FORECAST_GAPS_FILLED with 5 | tool | `00000178-0000-4000-8000-000000000178` |
| 4 | T6 | none | none | **correct**: asks for the month, latest June 2026, series offered | n/a | n/a (no tool) | `0000017d-0000-4000-8000-00000000017d` |
| 5 | T7_R1 | stock_coverage | stock_coverage (grain lifecycle_status; PANTRY_OIL, SE) | **correct**: refusal relayed, two lifecycle statuses | MASTER_DATA_FANOUT with its code; "rows marked both ACTIVE and PHASE_OUT", values now in the tool's reason (decision 3) | n/a (refusal) | `0000017e-0000-4000-8000-00000000017e` |
| 6 | T9 | stock_coverage | stock_coverage (SKU-H11, CH) | **correct**: 0 | NO_STOCK explained; "no warnings" | tool | `00000183-0000-4000-8000-000000000183` |
| 7 | BEYOND_H | stock_coverage | stock_coverage (SKU-H10, PL) | **correct**: 50 | BEYOND_HORIZON explained; FORECAST_GAPS_FILLED with 2 | tool | `00000164-0000-4000-8000-000000000164` |
| 8 | CS_LAST_MONTH_GAP | b2_semantic_view | b2_semantic_view (context), system_execute_sql (June 2026 snapshot, gap-filled) | **correct**: 0 | none | n/a | `00000015-0000-4000-8000-000000000015` |
| 9 | G1 | b2_semantic_view | b2_semantic_view, system_execute_sql | **correct**: 6,416 | none | n/a | `0000016a-0000-4000-8000-00000000016a` |
| 10 | G2 | b2_semantic_view | b2_semantic_view, system_execute_sql (stock value by the snapshot's own country, no item join) | **manual**: the text gives ES, FR, CH and SE only (each right at 0.1 million); the ten rows came as a `response.table` event ("Closing stock value (EUR) by country, June 2026", the ten exact values), which `run_call.py` does not put in the answer text | n/a | n/a | `0000016d-0000-4000-8000-00000000016d` |

Routing: 10 of 10 as expected (stock_coverage for the six coverage turns, b2_semantic_view for CS_LAST_MONTH_GAP, G1
and G2, no tool for T6). No coverage computed from the semantic view's figures; no added or averaged coverage.
The procedure's caller block, inside each call: LINKML_SVC, LINKML_METRICS_ROLE, no secondary role, agent activated.

Verbatim answers:
- **T1**: Flour and baking (PANTRY_FLOUR) in France had **2.8 months** of stock coverage as of June 2026. The figures are in QTY_EQ (kg or L equivalent) and cover standard items only, because bulk stock is excluded by default. Stock on hand was 1,400 against a 24-month forecast of 12,000. The tool returned no flags or warnings.
- **T2**: As of June 2026, SKU-H03 (salted almonds 1 kg) in Germany has a stock coverage of 7.0 months. This is in QTY_EQ (kg equivalent), for standard items with no other filters. It comes from 500 of stock against a 24-month forecast of 2,200. The tool returned one warning, FORECAST_GAPS_FILLED (count 2). Two months in the 24-month forecast window had no forecast row, so they were counted as zero demand. If real demand exists in those months, the true coverage would be somewhat shorter than 7.0 months.
- **T5**: Dry pasta in the United Kingdom had a stock coverage of about 2.37 months as of June 2026. That is how long the stock on hand would last against the next 24 months of forecast demand, if nothing is replenished. The figure is in months, not packs. Raw pack counts aren't supported because pack sizes differ, so stock and forecast are measured in quantity-equivalent units (kg or L). On that basis the stock was about 14,611 and the 24-month forecast about 138,399. The scope is standard items only, because bulk stock is excluded by default. **Warning (FORECAST_GAPS_FILLED, 5 months):** Five months of the 24-month forecast window have no forecast row and were counted as zero demand. If those months have real demand, the true coverage could be somewhat lower.
- **T6**: Coverage is measured at one analysis month, so I can't give a single figure for the whole of 2026. Which month do you want for flour and baking (PANTRY_FLOUR) in France? The latest available month is June 2026, and 2026 months run from January to June. I can also give a series of several months, with one coverage figure per month. Those figures can't be totalled or averaged into a yearly number.
- **T7_R1**: I can't give you coverage by lifecycle status for this slice. The coverage tool refused the request (refusal code MASTER_DATA_FANOUT). At least one item in the item master data has rows marked both ACTIVE and PHASE_OUT. Any coverage figure split by lifecycle status would therefore count that item's stock or forecast more than once, so the tool returned no numbers. The request was cooking oils (PANTRY_OIL) in Sweden (SE), June 2026, in quantity-equivalent units. The item's lifecycle status needs correcting in the item master data before this breakdown can be reliable. If it helps, I can give coverage for cooking oils in Sweden without the lifecycle split, or split it by another attribute such as warehouse or batch status.
- **T9**: For SKU-H11 in Switzerland (CH) at June 2026, in QTY_EQ (kg or L equivalent) and the default STANDARD item scope, coverage is 0 months. The tool flagged this row NO_STOCK, which means there is forecast demand but no stock on hand at that month. Forecast demand over the next 24 months is 2,400 QTY_EQ against stock of 0. With no replenishment, the item is out of stock. The tool returned no warnings.
- **BEYOND_H**: As of June 2026, SKU-H10 (arabica beans 1 kg) in Poland has a stock coverage of 50 months. This is in QTY_EQ (kg equivalent), on standard stock only. The stock is 5,000 against a 24-month forecast of 2,200. - **Flag BEYOND_HORIZON:** The stock lasts longer than the 24-month forecast window. The 50 months is therefore an extrapolation: stock divided by the mean non-zero monthly forecast. - **Warning FORECAST_GAPS_FILLED (2 months):** Two months in the forecast horizon have no forecast row. They were counted as zero demand.
- **CS_LAST_MONTH_GAP**: The closing stock of Oat cereal bar 1 kg (SKU-H11) in Switzerland (CH) at the end of Q2 2026 was 0 kg-equivalent. I took the June 2026 snapshot, the last month of the quarter, and the figure is in QTY_EQ (kg or L equivalent). The gap-filled snapshot data shows no stock for this SKU in Switzerland at that point. The query returned no warnings or flags.
- **G1**: The demand forecast for fruit juice (family BEV_JUICE) in France for September 2026 is 6,416 kg or L equivalent (QTY_EQ). This is the forecast for that one month, with no other filters applied.
- **G2**: Closing stock at the June 2026 snapshot, valued in EUR, covers all item types and all lot statuses. Spain holds the most (about €48.5M), followed by France (€43.9M) and Switzerland (€28.9M). Sweden holds the least (€14.5M).

### Tokens and latency per turn (`records.py` and the trace spans)

| Id | Client s | Before planning s | Planning s (steps) | Tool span s (ToolCall) | CALL elapsed ms (in the agent) | Span end - CALL end s | Response s | Suggested s | Orchestration input (cache write / read), output |
|---|---|---|---|---|---|---|---|---|---|
| T1 | 13.21 | 1.24 | 2.44 (1) | 4.17 | 3,948 | 0.22 | 2.17 | 1.82 | 56,646 (20,875 / 35,761), 435 |
| T2 | 13.50 | 0.23 | 2.00 (1) | 4.73 | 3,920 | 0.81 | 3.10 | 2.06 | 56,977 (4,912 / 52,055), 529 |
| T5 | 14.52 | 0.25 | 3.88 (1) | 4.23 | 3,513 | 0.72 | 3.09 | 1.88 | 57,281 (5,100 / 52,171), 711 |
| T6 | 5.50 | n/a | 0 | n/a | n/a | n/a | 2.50 | 1.50 | 36,705 (3,348 / 33,349), 136 |
| T7_R1 | 13.12 | 0.23 | 1.97 (1) | 4.35 | 4,137 | 0.21 | 3.31 | 1.84 | 55,751 (4,332 / 51,409), 578 |
| T9 | 12.86 | 0.24 | 2.37 (1) | 4.18 | 3,442 | 0.74 | 2.67 | 2.39 | 56,787 (4,798 / 51,979), 486 |
| BEYOND_H | 12.49 | 0.23 | 2.29 (1) | 4.12 | 3,449 | 0.67 | 2.73 | 1.98 | 57,082 (4,979 / 52,093), 544 |
| CS_LAST_MONTH_GAP | 14.25 | 0.20 | 6.26 (2) | context 0.66, SQL 1.09 | n/a | n/a | 2.42 | 2.59 | 157,011 (32,421 / 124,578), 756 |
| G1 | 13.03 | 1.28 | 5.46 (2) | context 0.44, SQL 0.36 | n/a | n/a | 2.06 | 2.30 | 156,521 (32,151 / 124,358), 564 |
| G2 | 17.65 | 0.59 | 4.46 (2) | context 0.11, SQL 2.90 | n/a | n/a | 2.91 | 2.13 | 156,233 (32,064 / 124,157), 560 |

Every query of the ten turns: queued provisioning 0, overload 0. The CALL's eight child queries match the direct
runs (four statements that read no table, the as_of statement, context, quality, coverage).

Reading [measured unless tagged]:
- **Tool span 4.12 to 4.73 s (median 4.20) on the six procedure turns, against 8.4 to 9.1 s in session 7 and 8.4 to
  8.6 s in session 8a: the 4.3 s projection holds** (one turn, T2, at 4.73 s). The CALL took 3.44 to 4.14 s inside
  the agent (direct median 3.48 s); the span ended 0.21 to 0.81 s after it.
- **Client total of a coverage turn: median 13.17 s (12.49 to 14.52), against 17.5 s in session 7 and 17.1 to 17.6 s
  in session 8a: about 4.3 s less per turn**, the difference of the tool spans. Planning, response and suggested
  queries are unchanged (2.0 to 2.4 s, 2.2 to 3.3 s, 1.8 to 2.4 s).
- **Input tokens: 55,751 to 57,281 per coverage turn, against 47,854 to 49,001 in session 8a (+about 8,000)**: the
  planning, response and suggested-queries steps each carry the second tool's description and the longer
  orchestration instruction [inferred: the tool result is unchanged in size]. **Semantic view turns: 156,233 to
  157,011**, the range of B2's own CS turn (150,478); the semantic model sits in the planning context once the view
  tool is chosen. Turn without a tool (T6): 36,705 against 31,500 in session 7.
- Token credits: not readable with the project role (ACCOUNT_USAGE); for the owner's read, the UTC window above and
  the ten request ids. Projection from session 8a's measured 0.016 to 0.017 credit for about 49,000 tokens (warm):
  about 0.019 to 0.020 per coverage turn, and B2's range (0.074 to 0.115) for the three semantic view turns
  [inferred].
- Version served: VERSION$3 on every turn (bare-name REST call, default version).
