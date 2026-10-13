# Probe A, second build (LINKML_METRICS.RAW.COVERAGE_SPINE_SV)

AS_OF = 2026-06-01. Month filter INSIDE SEMANTIC_VIEW.

| Trap | Query | Coverage returned | Expected | Result | Query id |
|---|---|---|---|---|---|
| T1 | `item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR' AND cal.month_start = '2026-06-01'` | 2.8000 | 2.8 | MATCH | `000002e7-0000-4000-8000-0000000002e7` |
| T2 | `item.sku_code = 'SKU-H03' AND geo.country_code = 'DE' AND cal.month_start = '2026-06-01'` | 7.0000 | 7.0 | MATCH | `000002e8-0000-4000-8000-0000000002e8` |
| T3 | `item.sku_code = 'SKU-H04' AND geo.country_code = 'IT' AND batch.batch_status = 'RELEASED' AND cal.month_start = '2026-06-01'` | error 10959: The entities 'BATCH' and 'FWD' are not related. Consider selecting calculations from entities that are related and have appropriate levels of granularity. | 6.0 | FAIL | `000002e9-0000-4000-8000-0000000002e9` |
| T4 | `item.sku_code = 'SKU-H05' AND geo.country_code = 'ES' AND cal.month_start = '2026-06-01'` | 8.5000 | 8.5 | MATCH | `000002ea-0000-4000-8000-0000000002ea` |
| T7 | `item.family_code = 'PANTRY_OIL' AND geo.country_code = 'SE' AND cal.month_start = '2026-06-01'` | 3.0000 | 2.25 | MISMATCH | `000002eb-0000-4000-8000-0000000002eb` |
| T8 | `item.sku_code = 'SKU-H08' AND geo.country_code = 'NL' AND cal.month_start = '2026-06-01'` | 0.0000 | 0.0 | MATCH | `000002ec-0000-4000-8000-0000000002ec` |
| NO_DEMAND | `item.sku_code = 'SKU-H09' AND geo.country_code = 'BE' AND cal.month_start = '2026-06-01'` | NULL | None | MATCH | `000002ed-0000-4000-8000-0000000002ed` |
| BEYOND_H | `item.sku_code = 'SKU-H10' AND geo.country_code = 'PL' AND cal.month_start = '2026-06-01'` | 50.0000 | 50.0 | MATCH | `000002ee-0000-4000-8000-0000000002ee` |
| T4, month as filter only | `item.sku_code = 'SKU-H05' AND geo.country_code = 'ES' AND cal.month_start = '2026-06-01'` | 8.5000 | 8.5 | MATCH | `000002ef-0000-4000-8000-0000000002ef` |
| T6, no analysis month | `item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR'` | 0.0394 | None | MISMATCH | `000002f0-0000-4000-8000-0000000002f0` |
| Series, 3 months (expect 3 rows) | `item.sku_code = 'SKU-H04' AND geo.country_code = 'IT' AND cal.month_start BETWEEN '2026-04-01' AND '2026-06-01'` | 10.0000; 4.9800; 7.5000 | None | MISMATCH | `000002f1-0000-4000-8000-0000000002f1` |

Note on the last two rows: the runner expects exactly one row, so it prints MISMATCH for both.
- Series: the three values are correct. Against `data/coverage_ref.py`: 2026-04 = 4.98, 2026-05 = 7.5, 2026-06 = 10.0 (all statuses), identical in both reference implementations. The rows come back unordered (no ORDER BY), so their order varies between runs.
- T6: a number is returned where a refusal is required. `stock_qty` = 1400 (latest snapshot, NON ADDITIVE BY) but `fwd.c01` = 35500 = 500 summed over the 71 analysis months of the calendar, so 1400 / 35500 = 0.0394.
