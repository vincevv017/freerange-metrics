# Phase 2: data metric functions generated from the contract (session 5)

Run 2026-10-03 by `run_dmf.py` as `LINKML_METRICS_ROLE` with no secondary role (connection perso), on RAW reloaded
from the Phase 2 dataset (contract 0.1.2, AS_OF 2026-06-01). `compiler/gen_dmf.py` writes
`generated/dmf.sql` from the contract's 25 quality expectations: 15 custom DMFs created in `LINKML_METRICS.RAW`, 34
ad hoc checks (a system DMF takes one column, so a multi-column expectation gives one check per column). **No DMF is
attached to a table and no `DATA_METRIC_SCHEDULE` is set**: `DATA_METRIC_FUNCTION_REFERENCES` returns 0 on the 7 tables.
Calling a DMF in a SELECT is not billed as Data Quality Monitoring (documented); warehouse time only.

## Privileges (measured)

| Need | Privilege | Account-level grant needed? |
|---|---|---|
| Call a system DMF ad hoc (`SELECT SNOWFLAKE.CORE.NULL_COUNT(SELECT c FROM t)`) | none beyond SELECT on the table: it worked as the project role, which holds neither `SNOWFLAKE.DATA_METRIC_USER` nor `EXECUTE DATA METRIC FUNCTION` | **No** |
| Create a custom DMF in RAW | `CREATE DATA METRIC FUNCTION` on the schema, implied by ownership of RAW | No |
| Attach a DMF and schedule it (Phase 3) | `EXECUTE DATA METRIC FUNCTION ON ACCOUNT` (documented, not exercised) | Yes, to show before running |

## System DMF names (phase1_notes item 27, checked)

`SHOW DATA METRIC FUNCTIONS IN SCHEMA SNOWFLAKE.CORE` lists 51 names, among them `DUPLICATE_COUNT`, `NULL_COUNT`,
`NEGATIVE_COUNT`, `ZERO_COUNT`, `FRESHNESS`, `ACCEPTED_VALUES`, `REFERENTIAL_INTEGRITY_COUNT`, `ROW_COUNT`,
`UNIQUE_COUNT`. The contract's names `SNOWFLAKE.CORE.DUPLICATE_COUNT` and `SNOWFLAKE.CORE.NULL_COUNT` exist.

What an ad hoc call accepts (measured):

- A system DMF with a one-column signature, called with a plain `SELECT col FROM table`.
- **Not** `ACCEPTED_VALUES` (its lambda argument is refused), the multi-column `DUPLICATE_COUNT()` or
  `REFERENTIAL_INTEGRITY_COUNT()`: their zero-argument signatures are for attaching to a table only. These checks
  are custom here.
- **Not** a subquery with a `WHERE` or an expression: it becomes a scalar argument (`Invalid argument types`).
- A custom DMF on **two tables**: only with each argument as a parenthesised subquery,
  `DMF((SELECT a FROM t1), (SELECT b FROM t2))`; the unparenthesised and `TABLE(t(col))` forms are syntax errors.
- A DMF body cannot call `CURRENT_DATE` (`510101`, non-deterministic), so stock freshness uses the system
  `FRESHNESS` (seconds), and the contract moved from CUSTOM to it (0.1.2), as did the two non-negativity checks
  (`NEGATIVE_COUNT`).

## Results

Every value is compared with a number computed by pandas from `data/output/`, not by SQL.

| Expectation | DMF | Target | Value | Expected (pandas) | On failure | Verdict |
|---|---|---|---|---|---|---|
| QE_STOCK_GRAIN | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | MONITOR | PASS (clean) |
| QE_FORECAST_GRAIN | `CUSTOM` | FCT_FORECAST | 0 | 0 | MONITOR | PASS (clean) |
| QE_ITEM_GRAIN | `SNOWFLAKE.CORE.DUPLICATE_COUNT` | DIM_ITEM.item_id | 1 | 1 | REFUSE_IF_USED | PASS (fires) |
| QE_GEO_GRAIN | `SNOWFLAKE.CORE.DUPLICATE_COUNT` | DIM_GEO.country_id | 0 | 0 | REFUSE | PASS (clean) |
| QE_BATCH_GRAIN | `SNOWFLAKE.CORE.DUPLICATE_COUNT` | DIM_BATCH.batch_id | 0 | 0 | REFUSE | PASS (clean) |
| QE_WAREHOUSE_GRAIN | `SNOWFLAKE.CORE.DUPLICATE_COUNT` | DIM_WAREHOUSE.warehouse_id | 0 | 0 | REFUSE | PASS (clean) |
| QE_CALENDAR_GRAIN | `SNOWFLAKE.CORE.DUPLICATE_COUNT` | DIM_CALENDAR.month_start | 0 | 0 | REFUSE | PASS (clean) |
| QE_STOCK_ITEM_REF | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | WARN | PASS (clean) |
| QE_STOCK_BATCH_REF | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | WARN | PASS (clean) |
| QE_STOCK_WAREHOUSE_REF | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | WARN | PASS (clean) |
| QE_STOCK_GEO_REF | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | WARN | PASS (clean) |
| QE_FORECAST_ITEM_REF | `CUSTOM` | FCT_FORECAST | 0 | 0 | WARN | PASS (clean) |
| QE_FORECAST_GEO_REF | `CUSTOM` | FCT_FORECAST | 0 | 0 | WARN | PASS (clean) |
| QE_STOCK_BATCH_ITEM | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | WARN | PASS (clean) |
| QE_SKU_FAMILY | `CUSTOM` | DIM_ITEM | 0 | 0 | REFUSE | PASS (clean) |
| QE_COUNTRY_REGION | `CUSTOM` | DIM_GEO | 0 | 0 | REFUSE | PASS (clean) |
| QE_FORECAST_DENSE | `CUSTOM` | FCT_FORECAST | 377 | 377 | WARN | PASS (fires) |
| QE_MEASURES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | FCT_STOCK_SNAPSHOT.stock_qty_eq | 0 | 0 | MONITOR | PASS (clean) |
| QE_MEASURES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | FCT_STOCK_SNAPSHOT.stock_value_eur | 0 | 0 | MONITOR | PASS (clean) |
| QE_FORECAST_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | FCT_FORECAST.forecast_qty_eq | 0 | 0 | MONITOR | PASS (clean) |
| QE_FORECAST_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | FCT_FORECAST.forecast_value_eur | 0 | 0 | MONITOR | PASS (clean) |
| QE_ATTRIBUTES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | DIM_ITEM.sku_code | 0 | 0 | MONITOR | PASS (clean) |
| QE_ATTRIBUTES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | DIM_ITEM.family_code | 0 | 0 | MONITOR | PASS (clean) |
| QE_ATTRIBUTES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | DIM_ITEM.range_code | 0 | 0 | MONITOR | PASS (clean) |
| QE_ATTRIBUTES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | DIM_ITEM.item_type | 0 | 0 | MONITOR | PASS (clean) |
| QE_ATTRIBUTES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | DIM_ITEM.lifecycle_status | 0 | 0 | MONITOR | PASS (clean) |
| QE_STOCK_FRESHNESS | `SNOWFLAKE.CORE.FRESHNESS` | FCT_STOCK_SNAPSHOT.snapshot_month | 10728316 | 10728318 | WARN | PASS (age) |
| QE_HORIZON_LOADED | `CUSTOM` | DIM_CALENDAR | 0 | 0 | REFUSE | PASS (clean) |
| QE_NON_NEGATIVE | `SNOWFLAKE.CORE.NEGATIVE_COUNT` | FCT_STOCK_SNAPSHOT.stock_qty_eq | 0 | 0 | MONITOR | PASS (clean) |
| QE_NON_NEGATIVE | `SNOWFLAKE.CORE.NEGATIVE_COUNT` | FCT_STOCK_SNAPSHOT.stock_value_eur | 0 | 0 | MONITOR | PASS (clean) |
| QE_FORECAST_NON_NEGATIVE | `SNOWFLAKE.CORE.NEGATIVE_COUNT` | FCT_FORECAST.forecast_qty_eq | 0 | 0 | MONITOR | PASS (clean) |
| QE_FORECAST_NON_NEGATIVE | `SNOWFLAKE.CORE.NEGATIVE_COUNT` | FCT_FORECAST.forecast_value_eur | 0 | 0 | MONITOR | PASS (clean) |
| QE_ACCEPTED_VALUES | `CUSTOM` | DIM_BATCH | 0 | 0 | MONITOR | PASS (clean) |
| QE_EQ_FACTOR | `CUSTOM` | DIM_ITEM | 0 | 0 | MONITOR | PASS (clean) |

- PASS: QE_ITEM_GRAIN fires on T7
- PASS: QE_FORECAST_DENSE fires on T2 (SKU-H03/DE: 2 missing months)
- PASS: only those two fire
- PASS: attribution T7: DUPLICATE_COUNT without SKU-H06 = 0 (got 0)
- PASS: attribution T2: QE_FORECAST_DENSE without SKU-H03/DE = 377 - 2 (got 375)
- PASS: no DMF attached to any of the 7 tables

- QE_ITEM_GRAIN: duplicated item: ['SKU-H06'], lifecycle_status ['ACTIVE', 'PHASE_OUT']
- QE_FORECAST_DENSE: 377 member-months missing over 59 months (2023-08-01 to 2028-06-01), 185 of 219 members; heroes: {'SKU-H03/DE': 2, 'SKU-H10/PL': 2}
- QE_STOCK_FRESHNESS: latest snapshot 2026-06-01: 10728318 s, about 4.1 months (threshold TBD)

Attribution uses session-scoped TEMPORARY copies of the table without the trap's rows, since an ad hoc argument
cannot carry a WHERE. `QE_FORECAST_DENSE` counts every member-month of the union of the horizons of the 36 valid
analysis months (59 months) with no forecast row: the background is sparse by design (`missing_month_rate` 3%),
so the value is 377, of which T2 contributes 2 and BEYOND_H 2. Expected, by `on_failure`: the procedure warns
(`FORECAST_GAPS_FILLED`) and still densifies.

## Session 7: QE_FORECAST_DENSE aligned with the procedure (contract 0.3.0)

Run 2026-10-03, `run_dmf.py`, same role and conditions. `QE_FORECAST_DENSE` now counts the missing months of the
horizon window of LATEST (2026-07 to 2028-06) for the item x country pairs with a forecast row in that window, as the
procedure counts them for a request: **169** (was 377 over the union of every valid month's horizon), equal to the
procedure's `FORECAST_GAPS_FILLED` for a call on every SKU x country at LATEST (169). T2 still contributes 2.
The periods come from a literal `VALUES (1), ..., (24)` list: a DMF body refuses `SEQ4` (510101, non-deterministic
function), measured on the first deployment. 35 checks, 0 failures.

| Expectation | DMF | Target | Value | Expected (pandas) | On failure | Verdict |
|---|---|---|---|---|---|---|
| QE_STOCK_GRAIN | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | MONITOR | PASS (clean) |
| QE_FORECAST_GRAIN | `CUSTOM` | FCT_FORECAST | 0 | 0 | MONITOR | PASS (clean) |
| QE_ITEM_GRAIN | `SNOWFLAKE.CORE.DUPLICATE_COUNT` | DIM_ITEM.item_id | 1 | 1 | REFUSE_IF_USED | PASS (fires) |
| QE_GEO_GRAIN | `SNOWFLAKE.CORE.DUPLICATE_COUNT` | DIM_GEO.country_id | 0 | 0 | REFUSE | PASS (clean) |
| QE_BATCH_GRAIN | `SNOWFLAKE.CORE.DUPLICATE_COUNT` | DIM_BATCH.batch_id | 0 | 0 | REFUSE | PASS (clean) |
| QE_WAREHOUSE_GRAIN | `SNOWFLAKE.CORE.DUPLICATE_COUNT` | DIM_WAREHOUSE.warehouse_id | 0 | 0 | REFUSE | PASS (clean) |
| QE_CALENDAR_GRAIN | `SNOWFLAKE.CORE.DUPLICATE_COUNT` | DIM_CALENDAR.month_start | 0 | 0 | REFUSE | PASS (clean) |
| QE_STOCK_ITEM_REF | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | WARN | PASS (clean) |
| QE_STOCK_BATCH_REF | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | WARN | PASS (clean) |
| QE_STOCK_WAREHOUSE_REF | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | WARN | PASS (clean) |
| QE_STOCK_GEO_REF | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | WARN | PASS (clean) |
| QE_FORECAST_ITEM_REF | `CUSTOM` | FCT_FORECAST | 0 | 0 | WARN | PASS (clean) |
| QE_FORECAST_GEO_REF | `CUSTOM` | FCT_FORECAST | 0 | 0 | WARN | PASS (clean) |
| QE_STOCK_BATCH_ITEM | `CUSTOM` | FCT_STOCK_SNAPSHOT | 0 | 0 | WARN | PASS (clean) |
| QE_SKU_FAMILY | `CUSTOM` | DIM_ITEM | 0 | 0 | REFUSE | PASS (clean) |
| QE_COUNTRY_REGION | `CUSTOM` | DIM_GEO | 0 | 0 | REFUSE | PASS (clean) |
| QE_FORECAST_DENSE | `CUSTOM` | FCT_FORECAST | 169 | 169 | WARN | PASS (fires) |
| QE_MEASURES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | FCT_STOCK_SNAPSHOT.stock_qty_eq | 0 | 0 | MONITOR | PASS (clean) |
| QE_MEASURES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | FCT_STOCK_SNAPSHOT.stock_value_eur | 0 | 0 | MONITOR | PASS (clean) |
| QE_FORECAST_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | FCT_FORECAST.forecast_qty_eq | 0 | 0 | MONITOR | PASS (clean) |
| QE_FORECAST_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | FCT_FORECAST.forecast_value_eur | 0 | 0 | MONITOR | PASS (clean) |
| QE_ATTRIBUTES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | DIM_ITEM.sku_code | 0 | 0 | MONITOR | PASS (clean) |
| QE_ATTRIBUTES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | DIM_ITEM.family_code | 0 | 0 | MONITOR | PASS (clean) |
| QE_ATTRIBUTES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | DIM_ITEM.range_code | 0 | 0 | MONITOR | PASS (clean) |
| QE_ATTRIBUTES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | DIM_ITEM.item_type | 0 | 0 | MONITOR | PASS (clean) |
| QE_ATTRIBUTES_NOT_NULL | `SNOWFLAKE.CORE.NULL_COUNT` | DIM_ITEM.lifecycle_status | 0 | 0 | MONITOR | PASS (clean) |
| QE_STOCK_FRESHNESS | `SNOWFLAKE.CORE.FRESHNESS` | FCT_STOCK_SNAPSHOT.snapshot_month | 10734171 | 10734173 | WARN | PASS (age) |
| QE_HORIZON_LOADED | `CUSTOM` | DIM_CALENDAR | 0 | 0 | REFUSE | PASS (clean) |
| QE_FORECAST_REACH | `CUSTOM` | FCT_FORECAST | 0 | 0 | REFUSE | PASS (clean) |
| QE_NON_NEGATIVE | `SNOWFLAKE.CORE.NEGATIVE_COUNT` | FCT_STOCK_SNAPSHOT.stock_qty_eq | 0 | 0 | MONITOR | PASS (clean) |
| QE_NON_NEGATIVE | `SNOWFLAKE.CORE.NEGATIVE_COUNT` | FCT_STOCK_SNAPSHOT.stock_value_eur | 0 | 0 | MONITOR | PASS (clean) |
| QE_FORECAST_NON_NEGATIVE | `SNOWFLAKE.CORE.NEGATIVE_COUNT` | FCT_FORECAST.forecast_qty_eq | 0 | 0 | MONITOR | PASS (clean) |
| QE_FORECAST_NON_NEGATIVE | `SNOWFLAKE.CORE.NEGATIVE_COUNT` | FCT_FORECAST.forecast_value_eur | 0 | 0 | MONITOR | PASS (clean) |
| QE_ACCEPTED_VALUES | `CUSTOM` | DIM_BATCH | 0 | 0 | MONITOR | PASS (clean) |
| QE_EQ_FACTOR | `CUSTOM` | DIM_ITEM | 0 | 0 | MONITOR | PASS (clean) |

- PASS: QE_ITEM_GRAIN fires on T7
- PASS: QE_FORECAST_DENSE fires on T2 (SKU-H03/DE: 2 missing months)
- PASS: only those two fire
- PASS: attribution T7: DUPLICATE_COUNT without SKU-H06 = 0 (got 0)
- PASS: attribution T2: QE_FORECAST_DENSE without SKU-H03/DE = 169 - 2 (got 167)
- PASS: no DMF attached to any of the 7 tables
- PASS: QE_FORECAST_DENSE = the procedure's FORECAST_GAPS_FILLED for every member at LATEST (169 vs 169)

- QE_ITEM_GRAIN: duplicated item: ['SKU-H06'], lifecycle_status ['ACTIVE', 'PHASE_OUT']
- QE_FORECAST_DENSE: 169 member-months missing over 24 months (2026-07-01 to 2028-06-01), 113 of 219 members; heroes: {'SKU-H03/DE': 2, 'SKU-H10/PL': 2}
- QE_STOCK_FRESHNESS: latest snapshot 2026-06-01: 10734173 s, about 4.1 months (threshold TBD)
