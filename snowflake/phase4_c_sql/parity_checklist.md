# Parity checklist: Python handler to SQL Scripting (session 8b, step 0)

Owner's answers of 2026-10-04 are folded in (section 0); where a row below conflicts with section 0, section 0 wins.

Source: `compiler/procedure_handler.py` and `compiler/gen_procedure.py` at commit 4b4aa7e (contract 0.4.1). Every item
below is a behaviour of the Python procedure that the SQL Scripting procedure must reproduce, in this order. Written
before any code. Tags: **[read]** read in the handler, **[to measure]** a Snowflake Scripting behaviour that the
documentation read so far does not settle and that step 1 measures before relying on it.

Documentation read for the SQL Scripting side (2026-10-04):
- Asynchronous child jobs: https://docs.snowflake.com/en/developer-guide/snowflake-scripting/asynchronous-child-jobs
  (`ASYNC (...)`, `AWAIT <resultset>`, `AWAIT ALL`, `CANCEL`, up to 4,000 concurrent children; "Using the
  LAST_QUERY_ID function with asynchronous child jobs is non-deterministic").
- Query id: https://docs.snowflake.com/en/developer-guide/snowflake-scripting/query-id (global variable `SQLID`,
  NULL when no query ran).
- RESULTSET: https://docs.snowflake.com/en/developer-guide/snowflake-scripting/resultsets (`res := (EXECUTE
  IMMEDIATE :sql USING (...))`, `ASYNC` on a RESULTSET, cursor over a RESULTSET).
- Still to read before step 1 code: exception handling, `OBJECT_CONSTRUCT_KEEP_NULL`, `PARSE_JSON` and
  `TRY_PARSE_JSON`, `ARRAY_AGG ... WITHIN GROUP`.

## 0. Owner's answers (2026-10-04)

1. Decision 3 accepted, contract 0.4.2: values distinct, sorted, NULL excluded, at most 5 per column then "and <n>
   more"; one "<column> (<values>)" group per column, in contract declaration order. Test first, both procedures. The
   fan-out detection rule with NULL is unchanged in 8b (open, register D034).
2. Key order is not reconstructed from the raw text. When several grain or filter attributes are at fault, both
   procedures name them in the contract's declaration order. The Python handler changes the same way, with a test that
   sends the keys in two orders and expects the same message. Applied as: attributes are ordered by their declaration
   index; a name the contract does not declare comes after every declared one, names among themselves in
   alphabetical order. The `applicability` lists follow the same order.
3. A nested value (array or object) in a message is rendered as compact JSON in both procedures (Python fixed, parity
   exact). Rounding ties at the 5th decimal: no change unless a real case appears, then documented in the parity table.
4. The four open behaviours are measured first, each in a throwaway anonymous block, recorded with the doc page. No
   read of QUERY_HISTORY, INFORMATION_SCHEMA or ACCOUNT_USAGE inside the procedure (the marker-comment fallback is
   rejected). If the query id of an async child cannot be obtained: stop and report the options (synchronous statements
   with SQLID, or a correlation marker resolved by the caller) with their measured cost.
5. One JSON string bound with USING, values read inside the statement. The generator writes the allowed identifiers
   (columns, grain and filter attribute codes) as literals into the procedure body; no runtime read of a registry
   table.
6. Decision 4: the zero-copy clone plan (names, grants, change per clone, DROP at the end) is shown at step 2.

## 1. Entry point and state

| # | Python behaviour | SQL Scripting counterpart |
|---|---|---|
| E1 | Signature `(AS_OF_MONTHS VARCHAR, UNIT_VARIANT VARCHAR, GRAIN VARCHAR, FILTERS VARCHAR DEFAULT '{}', TOTALS VARCHAR DEFAULT '[]')`, `RETURNS VARIANT`, `EXECUTE AS CALLER`; the agent calls it with named arguments and binds | Same signature and defaults, `LANGUAGE SQL`, `EXECUTE AS CALLER` [read] |
| E2 | Checks run in the contract's `check_order` (`refusal_order`); the generator fails if a code has no check or a check no code, and if `PREREQUISITES` is broken | The generator emits one block per code in `check_order`, from the same contract list and the same `PREREQUISITES` assertion; a code with no SQL template fails generation |
| E3 | The context query runs lazily, at the first check that needs it (`AS_OF_NO_SNAPSHOT`); a refusal before it runs no data query | Same: no context query before `AS_OF_NO_SNAPSHOT` |
| E4 | Before `MASTER_DATA_FANOUT`, the quality and the coverage statements start together (async); quality is read first; coverage is read only if no data check refuses, and is cancelled otherwise (cancel error `000605` ignored) | `ASYNC` for both, `AWAIT` quality first, `CANCEL` coverage on a data refusal [to measure: `ASYNC` around `EXECUTE IMMEDIATE ... USING`, `CANCEL` of a finished job] |
| E5 | If no check refuses and the jobs were not started (cannot happen with the current order, kept as a guard), they start after the loop | Same guard |

## 2. Parameter parsing rules shared by several checks

| # | Rule |
|---|---|
| P1 | `_json_or_list(raw, expect)`: `raw.strip()`; text starting with `[` or `{` is parsed as JSON; otherwise, for a list, a comma-separated list (items stripped, empty items dropped); otherwise (a map) an error. A parsed value of the wrong type (object for a list, array for a map) is an error |
| P2 | Python `json.loads` is strict JSON plus `NaN`, `Infinity`; duplicate keys keep the last value at the first key's position. [to measure: what `PARSE_JSON` / `TRY_PARSE_JSON` accept or reject on the malformed cases of the tests; duplicate keys need `PARSE_JSON(..., 'd')`] |
| P3 | Superseded by section 0, item 2: attributes in contract declaration order, never JSON key order |
| P4 | Message formatting `message()`: a float is shown `{:,.4f}` with trailing zeros and the point stripped (51,475.5); a list or tuple is joined with ", "; an int, a string and None are shown with Python `str()` (None as "None", True as "True"); a placeholder with no value stays literal (`{x}`) |
| P5 | Attribute names in grain, filters and totals are stripped and lower-cased; unit names are upper-cased with every run of whitespace or hyphens replaced by `_` |

## 3. Checks, in contract order

| Order | Code | Condition (Python) | Message values |
|---|---|---|---|
| 10 | AS_OF_MISSING | `as_of_months` is NULL, or stripped equals "", "[]" or "null"; also, at order 11, a parsed list that is empty (for example "[ ]") | none |
| 11 | AS_OF_INVALID | Not parseable by P1 as a list: `value` = the raw text. Then per item in order: an item that is neither a string nor an integer (JSON bool counts as an integer: "True"; float, null, array, object): `value` = the item as Python shows it (P4; a nested array or object as compact JSON, section 0 item 3); a string or integer, stripped, equal to LATEST in any case is the LATEST token; otherwise it must match `\d{4}-\d{2}-\d{2}` exactly and be a real date (2026-02-30 is invalid): `value` = the stripped text | `value` |
| 12 | AS_OF_NOT_MONTH_START | First date in list order whose day is not 1 (LATEST skipped) | `value` ISO, `month_start` ISO |
| 13 | AS_OF_TOO_MANY | Deduplicate in order (LATEST once, each date once); more than `max_periods` (24) | `max_periods` |
| 14 | AS_OF_NO_SNAPSHOT | Context read. LATEST resolves to the last **available** month; if none: `value` "LATEST", `latest` "none", `available_months` "none". A month not in the **snapshot** months: `value` ISO, `latest` ISO or None, `available_months` the full list of available months joined. Resolved months deduplicated in order | as stated |
| 15 | HORIZON_NOT_LOADED | First, for each TABLE expectation with refusal HORIZON_NOT_LOADED in contract order (QE_HORIZON_LOADED then QE_FORECAST_REACH) with a non-zero context count: `source` its table alias (calendar, forecast), `horizon` 24, `horizon_end` = latest snapshot + 24 months, `latest` = latest snapshot. Then, for each resolved month not in the available months: `source` "calendar or forecast", `horizon_end` = month + 24, `latest` = the month | as stated |
| 20 | UNIT_RAW_NOT_ADDITIVE | Unit key (P5) in a forbidden unit's names (RAW, QTY_RAW, RAW_UNIT, RAW_UNITS, UNITS, PACKS) | `value` = the raw `unit_variant` as passed |
| 21 | UNIT_UNKNOWN | Unit key in no unit's names (QTY_EQ: QTY_EQ, QUANTITY, VOLUME, KILOS, LITRES; VALUE: VALUE, EUROS, MONEY); NULL gives `value` "None" | `value` raw |
| 30 | GRAIN_MALFORMED | NULL or blank is an empty list; otherwise P1 as a list; any non-string item | none |
| 31 | GRAIN_EMPTY | Empty grain | none |
| 32 | GRAIN_DUPLICATE | Names appearing twice, sorted, distinct | `value` joined |
| 33 | FILTERS_MALFORMED | NULL, "" or "null" is the default "{}"; otherwise P1 as a map | none |
| 34 | FILTER_VALUES_INVALID | Per key in section 0, item 2 order: a scalar string or number (not bool) becomes a one-item list; otherwise a non-empty list with no null, bool, array or object; values kept as Python `str()` (1.0 stays "1.0") [to measure: number to text in VARIANT] | `attribute` |
| 35 | ATTRIBUTE_UNKNOWN | First used attribute (section 0, item 2 order) not in the contract's attributes nor unclassified | `attribute`, `conformed`, `snapshot_only` (contract order) |
| 36 | ATTRIBUTE_UNCLASSIFIED | Used attribute in `unclassified` (empty in the contract: never fires) | `attribute` |
| 37 | ATTRIBUTE_NOT_APPLICABLE | Used attribute of class NOT_APPLICABLE (none in the contract: never fires) | `attribute`, `reason` = its description |
| 38 | TOTALS_MALFORMED | NULL, "" or "null" is "[]"; must start with `[` (no comma list); JSON error, or an item not a list of strings | none |
| (38) | normalisation | Each total stripped and lower-cased, duplicates removed in order | |
| 39 | TOTALS_NOT_SUBSET | A total that is not a strict subset of the grain, or lists a name twice | `value` (the total joined, "" for []), `grain` joined |
| 50 | MASTER_DATA_FANOUT | Quality statement: FANOUT > 0, the count of in-scope items whose DIM_ITEM rows differ on any used item attribute (`COUNT(DISTINCT col) > 1`, NULL ignored, as today) | `count`, `attributes` = the used item attributes whose FANOUT__A > 0, in used order |
| 51 | DATA_QUALITY_FAILED | First REFUSE expectation with refusal DATA_QUALITY_FAILED, in contract order (QE_GEO_GRAIN, QE_BATCH_GRAIN, QE_WAREHOUSE_GRAIN, QE_CALENDAR_GRAIN, QE_SKU_FAMILY, QE_COUNTRY_REGION), with a non-zero context count | `expectation`, `count`, `condition` |

Reachable on v0 data (already tested): every code except HORIZON_NOT_LOADED, DATA_QUALITY_FAILED (decision 4),
ATTRIBUTE_UNCLASSIFIED and ATTRIBUTE_NOT_APPLICABLE (no such attribute in the contract; generated as no-op checks, as
in Python, and not exercisable without a contract change).

## 4. Decision 3: MASTER_DATA_FANOUT names the conflicting values

Proposed, in both procedures and the contract (0.4.2, reason template only, no rule changed): `{attributes}` becomes
each differing attribute followed by its distinct non-null values on the in-scope duplicated items, sorted, in
parentheses. T7_R1: "1 item(s) have several rows in DIM_ITEM that differ on lifecycle_status (ACTIVE, PHASE_OUT); any
number at this grain would be fanned out." Two attributes: "... differ on family_code (PANTRY_FLOUR, PANTRY_OIL),
lifecycle_status (ACTIVE, PHASE_OUT); ...". The quality statement gains one `FANOUT_VALUES__<A>` array per used item
attribute. Test first: the T7_R1 test and the two-attribute test assert the values.

## 5. Data statements (one plan, two statements, plus the context)

| # | Item |
|---|---|
| D1 | Context statement: caller block, snapshot months, available months (snapshot month + 24 within both the calendar's and the forecast's maximum), one column per TABLE expectation that has SQL (QE_STOCK_FRESHNESS has none: threshold TBD) |
| D2 | Plan: conformed part of the grain; stock filters = every filter; flow filters = conformed filters only; default scope on unless item_type is filtered; used attributes = grain, filter keys, then the scope attribute; grain sets = the grain then each total |
| D3 | Joins: a fact joins only the dimensions of the attributes it uses (inner joins); DIM_ITEM, the dedup table, through `SELECT DISTINCT item_id, <used item columns>`; the forecast joins only conformed attributes |
| D4 | Stock rows at exactly each analysis month (absent = 0); forecast rows for t+1 to t+24 relative to each month; values bound, never inlined. The SQL procedure binds one JSON request and reads values from it inside the statement (a fixed bind count); identifiers are literals the generator writes into the body from the contract |
| D5 | Coverage: aggregate first, members = stock members union forecast members (forecast members only when the grain set is conformed), dense 24-month calendar, cumulative forecast, the four outcomes and their flags in contract order; each total recomputed at its grain set, never across months; rows ordered by month, grain set, then each grain attribute NULLS LAST |
| D6 | Quality statement: QE_ITEM_GRAIN count (COUNT(*) > 1), FANOUT, FANOUT__A per used item attribute (and, decision 3, FANOUT_VALUES__A), the REQUEST_ROWS referential and consistency counts, QE_FORECAST_DENSE, and SCOPE_EXCLUDED (stock outside the default scope or with a NULL scope value, per month) when the default scope is on |

## 6. Answer

| # | Key | Rule |
|---|---|---|
| A1 | `status` | "ok" or "refused" |
| A2 | `contract` | `{id, version}` |
| A3 | `refusal` | refused only: `{code, reason}` |
| A4 | `available_months` | only once the context ran: `{first, last, latest}` (ISO or null) |
| A5 | `caller` | `{current_role, current_secondary_roles, current_user, is_agent_activated}`, from the context, or from a caller-only statement (not in lineage) when the context did not run |
| A6 | `lineage.query_ids` | the statements run: `{}` before the context, `{context}` after it, `{context, quality, coverage}` once the jobs started (a cancelled coverage keeps its id). [to measure: the id of an `ASYNC` child; no query history read inside the procedure] |
| A7 | `timing_ms` | `context_ms`, `quality_ms`, `coverage_ms`, `total_ms` when they ran (excluded from parity) |
| A8 | `request` | ok only: resolved months (ISO, deduplicated), unit id, grain, filters (values as text), totals |
| A9 | `applicability` | `stock_and_forecast` and `stock_only` in used order, `default_scope` `{item_type: [STANDARD]}` or null |
| A10 | `rows` | per row: `row_type` (DETAIL, TOTAL), `as_of_month`, `total_grain` on totals only, every grain attribute (null where the total drops it: needs `OBJECT_CONSTRUCT_KEEP_NULL`), `coverage_months` (number or null), `stock`, `forecast_over_horizon`, `flag` (null when none) |
| A11 | `row_count`, `flags` | count; sorted distinct non-null flags |
| A12 | `warnings` | first, per in-call expectation in contract order with WARN or REFUSE_IF_USED and a non-zero count: `{code, expectation, count, message}` (count shown without separators); then per month in ISO order with a non-zero excluded amount: `{code DEFAULT_SCOPE_EXCLUDED, as_of_month, excluded_amount, unit (the unit id), message}`, the message being the template with the amount (P4) and the unit symbol, then " (as of <month>)" |
| A13 | `note` | the totals rule, one line |

## 7. Parity method (step 2)

- Same argument strings to both procedures, every case of `tests/test_procedure.py` and the parameters of every
  coverage question of `generated/reference_questions.yaml`.
- Compared on the parsed JSON: equal after removing `lineage.query_ids` values (keys compared) and `timing_ms`;
  numbers within 1e-9; then asserted on the numbers of `data/traps.yaml` (equivalence is not correctness).
- Extra parsing cases the tests do not cover, run on both: an integer, a bool, a float and a null item in
  `as_of_months`, "[ ]", duplicate filter keys, two unknown filter keys, a numeric filter value, a lower-case unit
  with a hyphen.
- Known possible divergence, to be reported, not hidden: float rounding ties at the fifth decimal in messages.

## 8. What the SQL procedure must not do

No Python, no Snowpark; nothing derived from `data/coverage_ref.py`, the pandas or DuckDB references of the tests or
the skill's `coverage.py` (a test asserts no shared code: no import of, and no shared text with, those files).

## As built (session 8b, step 1)

The SQL Scripting counterparts of sections 1 and 5 changed with the cost measurements of `results.md` (findings S1
to S7): the as_of checks (10 to 13) are one statement that reads no table; checks 14 and 15 are in the context
statement; checks 20 to 39 are one statement that reads no table; the data statements' text is written by three
statements that read no table; the warnings and the fan-out reason are rendered by the quality statement. Order,
conditions, codes and messages are those of sections 0 and 3; parity run 4: 134 / 134 identical.
