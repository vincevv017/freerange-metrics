# Probe closing stock (session 6, step 0): the native baseline of step 1

Run 2026-10-03 by `run_probe_closing.py`, connection perso, `USE SECONDARY ROLES NONE`, `LINKML_METRICS_ROLE`,
every query through `SEMANTIC_VIEW()` (no agent, no LLM). RAW as reloaded in session 5 (AS_OF 2026-06-01). Nothing
was fixed: this measures what the best native build returns.

Build: `COVERAGE_SPINE_CLOSING_PROBE_SV` (`10_spine_closing_PROBE.sql`), a copy of `COVERAGE_SPINE_SV` (probe A,
second build) with three dimensions added from `DIM_CALENDAR`: `cal.year`, `cal.quarter`, `cal.year_quarter`
(`year || '-Q' || quarter`). The stock metric is unchanged:
`stock.stock_qty NON ADDITIVE BY (stock.snapshot_month ASC NULLS LAST) AS SUM(stock_qty_eq)`.

## Summary

| Question (Q2 2026, CH) | Returned | Expected | Wrong behaviour it matches |
|---|---|---|---|
| SKU-H11 x quarter (no June snapshot) | **350** | 0 | **last known value** (May carried into the quarter's close) |
| SKU-H12 x quarter (gap in May) | 450 | 450 | none |
| SNACK_BARS x quarter | 450 | 450 | none |
| SNACK_BARS x country, quarter filter, no time dimension | 450 | 450 | none |
| SKU-H11 / SKU-H12 x country, quarter filter, no time dimension | 350 / 450 | 0 / 450 | last known value (H11) |
| SKU x month, June of SKU-H11 | no row | 0 | member month lost (no row instead of 0) |
| SKU x month, May of SKU-H12 | no row | 0 | member month lost (no row instead of 0) |

What it shows **[measured]**:

1. `NON ADDITIVE BY (snapshot_month)` keeps, **per output row**, the rows of the latest snapshot month present in
   that row's group. It is not "the last month of the period": a member whose last snapshot is before the period's
   last month closes at its last known value (SKU-H11: 350, expected 0).
2. The family is right (450) because the latest month in the family's group is June, so only June rows are summed
   (0 for H11, 450 for H12). It is right by the composition of the group, not by rule: a family whose members all
   lack the last month would close at an earlier month, as SKU-H11 does **[inferred]**, not run, no such family in v0.
3. Neither sum (750, 950, 1,700) nor average (250, 316.67, 566.67) appears: `NON ADDITIVE BY` does prevent summing
   over time. The failure is the carried-forward value, the trap the article was to measure.
4. A month without a snapshot has no row at the month grain; nothing makes it 0.

## a. Probe views after the reloads (phase 2 open question 4)

All five probe semantic views compile and return the expected number (T1 2.8, or stock 1,400 for the B1 builds that
cannot carry coverage). Details in the raw output below.

## Raw output (query ids kept; stripped at publication)

Session: `('LINKML_METRICS_ROLE', '{"roles":"","value":""}')`

## a. Probe semantic views in RAW after the session 5 reloads

| View | Query | Returned | Expected | Status | Query id |
|---|---|---|---|---|---|
| `COVERAGE_NATIVE_RANGE_SV` | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV DIMENSIONS item.family_code, geo.country_code METRICS stock.stock_qty WHERE item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR')` | 1400 | 1400 | COMPILES, value ok | `00000307-0000-4000-8000-000000000307` |
| `COVERAGE_NATIVE_ROWS_SV` | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_ROWS_SV DIMENSIONS item.family_code, geo.country_code METRICS stock.stock_qty WHERE item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR')` | 1400 | 1400 | COMPILES, value ok | `00000308-0000-4000-8000-000000000308` |
| `COVERAGE_SPINE_ASOF_PROBE_SV` | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_ASOF_PROBE_SV DIMENSIONS item.family_code, geo.country_code METRICS coverage_months WHERE item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR' VARIABLES analysis_month => DATE '2026-06-01')` | 2.8 | 2.8 | COMPILES, value ok | `00000309-0000-4000-8000-000000000309` |
| `COVERAGE_SPINE_SV` | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_SV DIMENSIONS item.family_code, geo.country_code, cal.month_start METRICS coverage_months WHERE item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR' AND cal.month_start = '2026-06-01')` | 2.8 | 2.8 | COMPILES, value ok | `0000030a-0000-4000-8000-00000000030a` |
| `COVERAGE_T3_BRIDGE_PROBE_SV` | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_T3_BRIDGE_PROBE_SV DIMENSIONS item.family_code, geo.country_code, cal.month_start METRICS coverage_months WHERE item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR' AND cal.month_start = '2026-06-01')` | 2.8 | 2.8 | COMPILES, value ok | `0000030b-0000-4000-8000-00000000030b` |

## b. Closing stock heroes, 2026-Q2, through `LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV`

| Case | Query | Row | Returned | Expected | Matches | Query id |
|---|---|---|---|---|---|---|
| 1. SKU x quarter | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.sku_code, cal.year_quarter METRICS stock.stock_qty WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2')` | SKU-H11 | 350 | 0 | last_known_value | `0000030c-0000-4000-8000-00000000030c` |
| 1. SKU x quarter | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.sku_code, cal.year_quarter METRICS stock.stock_qty WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2')` | SKU-H12 | 450 | 450 | expected | `0000030c-0000-4000-8000-00000000030c` |
| 2. family x quarter | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.family_code, cal.year_quarter METRICS stock.stock_qty WHERE item.family_code = 'SNACK_BARS' AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2')` | SNACK_BARS | 450 | 450 | expected | `0000030d-0000-4000-8000-00000000030d` |
| 3. family x country, quarter filter, no time dimension | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.family_code, geo.country_code METRICS stock.stock_qty WHERE item.family_code = 'SNACK_BARS' AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2')` | SNACK_BARS | 450 | 450 | expected | `0000030e-0000-4000-8000-00000000030e` |
| 3b. SKU x country, quarter filter, no time dimension | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.sku_code, geo.country_code METRICS stock.stock_qty WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2')` | SKU-H11 | 350 | 0 | last_known_value | `0000030f-0000-4000-8000-00000000030f` |
| 3b. SKU x country, quarter filter, no time dimension | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.sku_code, geo.country_code METRICS stock.stock_qty WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2')` | SKU-H12 | 450 | 450 | expected | `0000030f-0000-4000-8000-00000000030f` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.sku_code, cal.month_start METRICS stock.stock_qty WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H11 2026-04-01 | 400 | 400 | expected | `00000310-0000-4000-8000-000000000310` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.sku_code, cal.month_start METRICS stock.stock_qty WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H11 2026-05-01 | 350 | 350 | expected | `00000310-0000-4000-8000-000000000310` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.sku_code, cal.month_start METRICS stock.stock_qty WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H11 2026-06-01 | no row | 0 | no row | `00000310-0000-4000-8000-000000000310` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.sku_code, cal.month_start METRICS stock.stock_qty WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H12 2026-04-01 | 500 | 500 | expected | `00000310-0000-4000-8000-000000000310` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.sku_code, cal.month_start METRICS stock.stock_qty WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H12 2026-05-01 | no row | 0 | no row | `00000310-0000-4000-8000-000000000310` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_SPINE_CLOSING_PROBE_SV DIMENSIONS item.sku_code, cal.month_start METRICS stock.stock_qty WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H12 2026-06-01 | 450 | 450 | expected | `00000310-0000-4000-8000-000000000310` |

# Session 7, step 0: generated closing stock, and trap T9

Run 2026-10-03 by `run_closing_generated.py` and `run_t9.py`, connection perso, `USE SECONDARY ROLES NONE`,
`LINKML_METRICS_ROLE`, every query through `SEMANTIC_VIEW()` with `USE_CACHED_RESULT = FALSE` (no agent, no LLM).
Contract 0.2.1. `compiler/gen_closing_sv.py` writes `generated/closing_stock_sv.sql`: the view
`FCT_STOCK_SNAPSHOT_GAPFILLED` (every batch x warehouse key, one row per month from its first snapshot month to its
last snapshot month + 1, capped at the latest snapshot month, measures 0 where absent, other columns carried from the
key's last row) and the semantic view `CLOSING_STOCK_SV` (stock `NON ADDITIVE BY` the snapshot month, month, quarter
and year dimensions from the contract's `periods`, one metric per allowed unit).

## Summary, next to the native baseline

| Question (Q2 2026, CH) | Native (session 6) | Generated | Expected |
|---|---|---|---|
| SKU-H11 x quarter (no June snapshot) | 350 (last known value) | **0** | 0 |
| SKU-H12 x quarter (gap in May) | 450 | 450 | 450 |
| SNACK_BARS x quarter | 450 | 450 | 450 |
| SNACK_BARS x country, quarter filter, no time dimension | 450 | 450 | 450 |
| SKU-H11 / SKU-H12 x country, quarter filter, no time dimension | 350 / 450 | **0** / 450 | 0 / 450 |
| SKU x month, June of SKU-H11 / May of SKU-H12 | no row / no row | **0 / 0** | 0 / 0 |
| SKU rows add up to the family row (H11 + H12 = SNACK_BARS) | 800 against 450: no | 450 = 450: **yes** | yes |

| Sweep (every group of the data, QTY_EQ) | Groups | Native failures | Generated failures |
|---|---|---|---|
| family x country x quarter = sum of its SKU rows | 1,261 | n/a | 0 |
| family x country x quarter = pandas reference of the contract's rule | 1,261 | 12 | 12 |
| SKU x country x quarter = pandas reference (SKU-H06 left out, T7) | 2,702 | 1 (SKU-H11, Q2 2026) | 0 |

What it shows **[measured]**:

1. The gap-filled snapshot makes `NON ADDITIVE BY` right: every hero is right, at every grain, with and without a
   time dimension, and the detail now adds up to the total. One extra 0 row after a key's last snapshot is enough.
2. Cost: **2,513 rows added to 60,915 (+4.13 %)**: 2,512 keys that end before the latest month get one 0 row, plus
   the one inner gap (SKU-H12, May). The stock summed over all rows is unchanged.
3. The 12 family failures are the same in both views and are all **T7**: PANTRY_OIL x SE in every quarter, SKU-H06
   counted twice (Q2 2026: 1,500 against 900, the `naive_join_stock_qty_eq` of traps.yaml). The generated view reads
   DIM_ITEM through a `SELECT DISTINCT` of its key and attribute columns, `lifecycle_status` included; the duplicate
   differs on that column, so it still fans out. A semantic view cannot refuse at query time (QE_ITEM_GRAIN is
   REFUSE_IF_USED in the contract): the native path has no answer to T7 short of dropping the column.
4. On v0 the native carry-forward touches **one** SKU x country x quarter group, the hero: background keys that end
   early belong to SKUs with other keys still live at the quarter's end. The defect is real but rare in this data;
   the heroes are what exposes it.
5. No group appears in the generated view without a member in the reference (a key's 0 row opening a quarter would
   create one; none on v0) **[measured]**; in general it would add a row at 0, not a wrong number **[inferred]**.

## T9: stale stock in coverage (`run_t9.py`)

SKU-H11 x CH at AS_OF (June 2026): stock 400 in April, 350 in May, none in June, forecast 100 a month. Expected 0
(NO_STOCK); the wrong value of traps.yaml is 3.5 (350 over 100). The generated procedure returns 0 with NO_STOCK in
both units (`tests/test_procedure.py`, T9 hero and `test_t9_stale_stock_is_not_carried`).

| View | month = AS_OF | April to June (range or quarter) | no month |
|---|---|---|---|
| `COVERAGE_SPINE_SV` (B2) | 0 | **1.1667** (stock 350, forecast 3 x 2,400) | **0.0493** (stock 350, forecast of every analysis month) |
| `COVERAGE_SPINE_CLOSING_PROBE_SV` (B2 + quarter) | 0 | **1.1667** (range and quarter dimension) | **0.0493** |
| `COVERAGE_NATIVE_RANGE_SV` (B1, no coverage metric) | no stock row | stock **350** (May carried) | stock **350** |
| `COVERAGE_SPINE_GAPFILLED_PROBE_SV` (B2 + quarter, gap-filled stock) | 0 | 0 | 0 |

What it shows **[measured]**:

1. With a month filter equal to AS_OF, the native view is right: the filter leaves no stock row, so stock is NULL and
   the CASE returns 0.
2. With a range, a quarter or no month, `NON ADDITIVE BY` picks May's 350: the stockout is hidden behind a positive
   coverage. The value is not 3.5 but lower, because the forecast spine is also summed over every analysis month the
   filter keeps (7,200 = 3 x 2,400): two errors stack, and the number looks plausible.
3. Reading stock from the gap-filled snapshot removes the stale stock in every form (0 each time). It does not fix
   the forecast summed over several analysis months (still 7,200 on the range): for a member that does hold stock,
   a range query on that view stays wrong **[inferred]** from the forecast column, not run on such a member. The
   procedure has neither problem: it refuses a period and reads the stock at exactly the analysis month.

Probe object created: `COVERAGE_SPINE_GAPFILLED_PROBE_SV` (`20_spine_gapfilled_PROBE.sql`). Nothing in the earlier
probe views was changed.

## Raw output: generated closing stock (query ids kept; stripped at publication)



### a. Gap-filled view

| Base rows | Gap-filled rows | Added rows | Growth | Keys | Query id |
|---|---|---|---|---|---|
| 60,915 | 63,428 | 2,513 | 4.13% | 4,194 | `00000311-0000-4000-8000-000000000311` |

Stock preserved (sum over all rows equal, every added row 0): **yes** (2.07617e+08 vs 2.07617e+08, `00000312-0000-4000-8000-000000000312`)

### b. Closing stock heroes, 2026-Q2, through `LINKML_METRICS.RAW.CLOSING_STOCK_SV`

| Case | Query | Row | Returned | Expected | Result | Query id |
|---|---|---|---|---|---|---|
| 1. SKU x quarter | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.sku_code, calendar.year_quarter METRICS stock_snapshot.closing_stock_qty_eq WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2')` | SKU-H11 | 0 | 0 | expected | `00000313-0000-4000-8000-000000000313` |
| 1. SKU x quarter | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.sku_code, calendar.year_quarter METRICS stock_snapshot.closing_stock_qty_eq WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2')` | SKU-H12 | 450 | 450 | expected | `00000313-0000-4000-8000-000000000313` |
| 2. family x quarter | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.family_code, calendar.year_quarter METRICS stock_snapshot.closing_stock_qty_eq WHERE item.family_code = 'SNACK_BARS' AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2')` | SNACK_BARS | 450 | 450 | expected | `00000314-0000-4000-8000-000000000314` |
| 3. family x country, quarter filter, no time dimension | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.family_code, geo.country_code METRICS stock_snapshot.closing_stock_qty_eq WHERE item.family_code = 'SNACK_BARS' AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2')` | SNACK_BARS | 450 | 450 | expected | `00000315-0000-4000-8000-000000000315` |
| 3b. SKU x country, quarter filter, no time dimension | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.sku_code, geo.country_code METRICS stock_snapshot.closing_stock_qty_eq WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2')` | SKU-H11 | 0 | 0 | expected | `00000316-0000-4000-8000-000000000316` |
| 3b. SKU x country, quarter filter, no time dimension | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.sku_code, geo.country_code METRICS stock_snapshot.closing_stock_qty_eq WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2')` | SKU-H12 | 450 | 450 | expected | `00000316-0000-4000-8000-000000000316` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.sku_code, calendar.month_start METRICS stock_snapshot.closing_stock_qty_eq WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H11 2026-04-01 | 400 | 400 | expected | `00000317-0000-4000-8000-000000000317` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.sku_code, calendar.month_start METRICS stock_snapshot.closing_stock_qty_eq WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H11 2026-05-01 | 350 | 350 | expected | `00000317-0000-4000-8000-000000000317` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.sku_code, calendar.month_start METRICS stock_snapshot.closing_stock_qty_eq WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H11 2026-06-01 | 0 | 0 | expected | `00000317-0000-4000-8000-000000000317` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.sku_code, calendar.month_start METRICS stock_snapshot.closing_stock_qty_eq WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H12 2026-04-01 | 500 | 500 | expected | `00000317-0000-4000-8000-000000000317` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.sku_code, calendar.month_start METRICS stock_snapshot.closing_stock_qty_eq WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H12 2026-05-01 | 0 | 0 | expected | `00000317-0000-4000-8000-000000000317` |
| 4. SKU x month | `SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.CLOSING_STOCK_SV DIMENSIONS item.sku_code, calendar.month_start METRICS stock_snapshot.closing_stock_qty_eq WHERE item.sku_code IN ('SKU-H11', 'SKU-H12') AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2') ORDER BY sku_code, month_start` | SKU-H12 2026-06-01 | 450 | 450 | expected | `00000317-0000-4000-8000-000000000317` |

SKU rows add up to the family row: SKU-H11 + SKU-H12 = 450, family = 450: **yes**

### c. Sweep: every family x country x quarter

| Check | Groups | Failures | Query id |
|---|---|---|---|
| generated: family row = sum of its SKU rows | 1261 | 0 | `00000318-0000-4000-8000-000000000318`, `00000319-0000-4000-8000-000000000319` |
| generated: family row = pandas reference (contract rule) | 1261 | 12 | `00000318-0000-4000-8000-000000000318` |
| generated: rows with no reference member (a key's 0 row starting the quarter) | 0 | 0 non-zero | `00000318-0000-4000-8000-000000000318` |
| native baseline (session 6 view): family row = pandas reference | 1261 | 12 | `0000031a-0000-4000-8000-00000000031a` |
| generated: SKU x country x quarter = pandas reference (SKU-H06 left out, T7) | 2702 | 0 (0 where the reference is 0 and a positive value is returned) | `00000319-0000-4000-8000-000000000319` |
| native baseline (session 6 view): SKU x country x quarter = pandas reference (SKU-H06 left out, T7) | 2702 | 1 (1 where the reference is 0 and a positive value is returned) | `0000031b-0000-4000-8000-00000000031b` |

generated, family != reference (12):

| Family | Country | Quarter | Generated | Native | SKU sum | Reference |
|---|---|---|---|---|---|---|
| PANTRY_OIL | SE | 2023-Q3 | 1382 | 1382 | 1382 | 844 |
| PANTRY_OIL | SE | 2023-Q4 | 1443 | 1443 | 1443 | 927 |
| PANTRY_OIL | SE | 2024-Q1 | 1487 | 1487 | 1487 | 921 |
| PANTRY_OIL | SE | 2024-Q2 | 1304 | 1304 | 1304 | 843 |
| PANTRY_OIL | SE | 2024-Q3 | 1453 | 1453 | 1453 | 887 |
| PANTRY_OIL | SE | 2024-Q4 | 1202 | 1202 | 1202 | 777 |
| PANTRY_OIL | SE | 2025-Q1 | 1326 | 1326 | 1326 | 815 |
| PANTRY_OIL | SE | 2025-Q2 | 1446 | 1446 | 1446 | 835 |
| PANTRY_OIL | SE | 2025-Q3 | 1693 | 1693 | 1693 | 969 |
| PANTRY_OIL | SE | 2025-Q4 | 1262 | 1262 | 1262 | 818 |
| PANTRY_OIL | SE | 2026-Q1 | 1412 | 1412 | 1412 | 870 |
| PANTRY_OIL | SE | 2026-Q2 | 1500 | 1500 | 1500 | 900 |

native, family != reference (12):

| Family | Country | Quarter | Generated | Native | SKU sum | Reference |
|---|---|---|---|---|---|---|
| PANTRY_OIL | SE | 2023-Q3 | 1382 | 1382 | 1382 | 844 |
| PANTRY_OIL | SE | 2023-Q4 | 1443 | 1443 | 1443 | 927 |
| PANTRY_OIL | SE | 2024-Q1 | 1487 | 1487 | 1487 | 921 |
| PANTRY_OIL | SE | 2024-Q2 | 1304 | 1304 | 1304 | 843 |
| PANTRY_OIL | SE | 2024-Q3 | 1453 | 1453 | 1453 | 887 |
| PANTRY_OIL | SE | 2024-Q4 | 1202 | 1202 | 1202 | 777 |
| PANTRY_OIL | SE | 2025-Q1 | 1326 | 1326 | 1326 | 815 |
| PANTRY_OIL | SE | 2025-Q2 | 1446 | 1446 | 1446 | 835 |
| PANTRY_OIL | SE | 2025-Q3 | 1693 | 1693 | 1693 | 969 |
| PANTRY_OIL | SE | 2025-Q4 | 1262 | 1262 | 1262 | 818 |
| PANTRY_OIL | SE | 2026-Q1 | 1412 | 1412 | 1412 | 870 |
| PANTRY_OIL | SE | 2026-Q2 | 1500 | 1500 | 1500 | 900 |

## Raw output: T9



Expected coverage 0 (NO_STOCK); wrong value 3.5 (350 over 100 a month).

| View | Time filter | Coverage | Stock picked | Forecast c24 | Verdict | Query id |
|---|---|---|---|---|---|---|
| COVERAGE_SPINE_SV (B2) | month = AS_OF | 0 | NULL | 2400 | expected (0) | `0000031c-0000-4000-8000-00000000031c` |
| COVERAGE_SPINE_SV (B2) | month range April to June | 1.16667 | 350 | 7200 | **wrong, other value** | `0000031d-0000-4000-8000-00000000031d` |
| COVERAGE_SPINE_SV (B2) | no month | 0.0492958 | 350 | 142800 | **wrong, other value** | `0000031e-0000-4000-8000-00000000031e` |
| COVERAGE_SPINE_CLOSING_PROBE_SV (B2 + quarter) | month = AS_OF | 0 | NULL | 2400 | expected (0) | `0000031f-0000-4000-8000-00000000031f` |
| COVERAGE_SPINE_CLOSING_PROBE_SV (B2 + quarter) | month range April to June | 1.16667 | 350 | 7200 | **wrong, other value** | `00000320-0000-4000-8000-000000000320` |
| COVERAGE_SPINE_CLOSING_PROBE_SV (B2 + quarter) | quarter dimension = 2026-Q2 | 1.16667 | 350 | 7200 | **wrong, other value** | `00000321-0000-4000-8000-000000000321` |
| COVERAGE_SPINE_CLOSING_PROBE_SV (B2 + quarter) | no month | 0.0492958 | 350 | 142800 | **wrong, other value** | `00000322-0000-4000-8000-000000000322` |
| COVERAGE_SPINE_GAPFILLED_PROBE_SV (B2 + quarter, gap-filled stock) | month = AS_OF | 0 | 0 | 2400 | expected (0) | `00000323-0000-4000-8000-000000000323` |
| COVERAGE_SPINE_GAPFILLED_PROBE_SV (B2 + quarter, gap-filled stock) | month range April to June | 0 | 0 | 7200 | expected (0) | `00000324-0000-4000-8000-000000000324` |
| COVERAGE_SPINE_GAPFILLED_PROBE_SV (B2 + quarter, gap-filled stock) | quarter dimension = 2026-Q2 | 0 | 0 | 7200 | expected (0) | `00000325-0000-4000-8000-000000000325` |
| COVERAGE_SPINE_GAPFILLED_PROBE_SV (B2 + quarter, gap-filled stock) | no month | 0 | 0 | 142800 | expected (0) | `00000326-0000-4000-8000-000000000326` |
| COVERAGE_NATIVE_RANGE_SV (B1) | month = AS_OF | n/a (no coverage metric, 010273) | no row | n/a | no stale stock | `00000327-0000-4000-8000-000000000327` |
| COVERAGE_NATIVE_RANGE_SV (B1) | month range April to June | n/a (no coverage metric, 010273) | 350 (May carried) | n/a | stock 350 would give the wrong value | `00000328-0000-4000-8000-000000000328` |
| COVERAGE_NATIVE_RANGE_SV (B1) | no month | n/a (no coverage metric, 010273) | 350 (May carried) | n/a | stock 350 would give the wrong value | `00000329-0000-4000-8000-000000000329` |
