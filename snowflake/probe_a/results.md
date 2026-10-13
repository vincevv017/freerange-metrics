# Probe A raw results

AS_OF = 2026-06-01. Session: `('LINKML_METRICS_ROLE', '{"roles":"","value":""}')`

## T2 sparse forecast months (SKU-H03 / DE, forecast rows absent for k = 2, 3; expected 7.0)

#### T2, ROWS frame, outer filter on the month

```sql
SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_ROWS_SV
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, fc.c01, fc.c02, fc.c03, fc.c04, fc.c05, fc.c06, fc.c07, fc.c08, fc.c09, fc.c10, fc.c11, fc.c12, fc.c13, fc.c14, fc.c15, fc.c16, fc.c17, fc.c18, fc.c19, fc.c20, fc.c21, fc.c22, fc.c23, fc.c24, fc.nz24
    WHERE item.sku_code = 'SKU-H03' AND geo.country_code = 'DE')
WHERE month_start = '2026-06-01'
```

query id `000002b6-0000-4000-8000-0000000002b6`, 1 row(s)

| SKU_CODE | COUNTRY_CODE | MONTH_START | MONTH_INDEX | STOCK_QTY | C01 | C02 | C03 | C04 | C05 | C06 | C07 | C08 | NZ24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SKU-H03 | DE | 2026-06-01 | 24318 | 500.0000 | 100.0000 | 200.0000 | 300.0000 | 400.0000 | 500.0000 | 600.0000 | 700.0000 | 800.0000 | 24 |

**T2 ROWS: coverage rebuilt from the view = 5.0 (None); expected 7.0 -> MISMATCH**

#### T2, RANGE frame, outer filter on the month

```sql
SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, fc.c01, fc.c02, fc.c03, fc.c04, fc.c05, fc.c06, fc.c07, fc.c08, fc.c09, fc.c10, fc.c11, fc.c12, fc.c13, fc.c14, fc.c15, fc.c16, fc.c17, fc.c18, fc.c19, fc.c20, fc.c21, fc.c22, fc.c23, fc.c24, fc.nz24
    WHERE item.sku_code = 'SKU-H03' AND geo.country_code = 'DE')
WHERE month_start = '2026-06-01'
```

query id `000002b7-0000-4000-8000-0000000002b7`, 1 row(s)

| SKU_CODE | COUNTRY_CODE | MONTH_START | MONTH_INDEX | STOCK_QTY | C01 | C02 | C03 | C04 | C05 | C06 | C07 | C08 | NZ24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SKU-H03 | DE | 2026-06-01 | 24318 | 500.0000 | 100.0000 | 100.0000 | 100.0000 | 200.0000 | 300.0000 | 400.0000 | 500.0000 | 600.0000 | 22 |

**T2 RANGE: coverage rebuilt from the view = 7.0 (None); expected 7.0 -> MATCH**

## T4 time filter (SKU-H05 / ES, expected 8.5)

#### T4, month filter INSIDE SEMANTIC_VIEW (the natural way to ask 'for June')

```sql
SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, fc.c01, fc.c02, fc.c03, fc.c04, fc.c05, fc.c06, fc.c07, fc.c08, fc.c09, fc.c10, fc.c11, fc.c12, fc.c13, fc.c14, fc.c15, fc.c16, fc.c17, fc.c18, fc.c19, fc.c20, fc.c21, fc.c22, fc.c23, fc.c24, fc.nz24
    WHERE item.sku_code = 'SKU-H05' AND geo.country_code = 'ES' AND cal.month_start = '2026-06-01')
```

query id `000002b8-0000-4000-8000-0000000002b8`, 1 row(s)

| SKU_CODE | COUNTRY_CODE | MONTH_START | MONTH_INDEX | STOCK_QTY | C01 | C02 | C03 | C04 | C05 | C06 | C07 | C08 | NZ24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SKU-H05 | ES | 2026-06-01 | 24318 | 1000.0000 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |

**T4 inner filter: coverage rebuilt from the view = None (C_k NULL); expected 8.5 -> MISMATCH**

#### T4, month filter OUTSIDE SEMANTIC_VIEW

```sql
SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, fc.c01, fc.c02, fc.c03, fc.c04, fc.c05, fc.c06, fc.c07, fc.c08, fc.c09, fc.c10, fc.c11, fc.c12, fc.c13, fc.c14, fc.c15, fc.c16, fc.c17, fc.c18, fc.c19, fc.c20, fc.c21, fc.c22, fc.c23, fc.c24, fc.nz24
    WHERE item.sku_code = 'SKU-H05' AND geo.country_code = 'ES')
WHERE month_start = '2026-06-01'
```

query id `000002b9-0000-4000-8000-0000000002b9`, 1 row(s)

| SKU_CODE | COUNTRY_CODE | MONTH_START | MONTH_INDEX | STOCK_QTY | C01 | C02 | C03 | C04 | C05 | C06 | C07 | C08 | NZ24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SKU-H05 | ES | 2026-06-01 | 24318 | 1000.0000 | 120.0000 | 210.0000 | 360.0000 | 470.0000 | 600.0000 | 700.0000 | 840.0000 | 920.0000 | 24 |

**T4 outer filter: coverage rebuilt from the view = 8.5 (None); expected 8.5 -> MATCH**

## T3 stock-only filter (SKU-H04 / IT released lots, expected 6.0)

#### T3, batch_status as a DIMENSION with forecast metrics

```sql
SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index, batch.batch_status
    METRICS stock.stock_qty, fc.c01
    WHERE item.sku_code = 'SKU-H04' AND geo.country_code = 'IT')
WHERE month_start = '2026-06-01'
```

**Error** `10959`: `010959 (42601): SQL compilation error:
The entities 'BATCH' and 'FC' are not related. Consider selecting calculations from entities that are related and have appropriate levels of granularity.`  (query id `000002ba-0000-4000-8000-0000000002ba`)

#### T3, batch_status as a FILTER with forecast metrics

```sql
SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, fc.c01, fc.c02, fc.c03, fc.c04, fc.c05, fc.c06, fc.c07, fc.c08, fc.c09, fc.c10, fc.c11, fc.c12, fc.c13, fc.c14, fc.c15, fc.c16, fc.c17, fc.c18, fc.c19, fc.c20, fc.c21, fc.c22, fc.c23, fc.c24, fc.nz24
    WHERE item.sku_code = 'SKU-H04' AND geo.country_code = 'IT' AND batch.batch_status = 'RELEASED')
WHERE month_start = '2026-06-01'
```

**Error** `10959`: `010959 (42601): SQL compilation error:
The entities 'BATCH' and 'FC' are not related. Consider selecting calculations from entities that are related and have appropriate levels of granularity.`  (query id `000002bb-0000-4000-8000-0000000002bb`)

**T3 filter: no row returned** (expected 6.0).

#### T3, two SEMANTIC_VIEW calls joined by the consumer (stock filtered, forecast not)

```sql
WITH s AS (SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV
               DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
               METRICS stock.stock_qty
               WHERE item.sku_code = 'SKU-H04' AND geo.country_code = 'IT' AND batch.batch_status = 'RELEASED')),
     f AS (SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV
               DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
               METRICS fc.c01, fc.c02, fc.c03, fc.c04, fc.c05, fc.c06, fc.c07, fc.c08, fc.c09, fc.c10, fc.c11, fc.c12, fc.c13, fc.c14, fc.c15, fc.c16, fc.c17, fc.c18, fc.c19, fc.c20, fc.c21, fc.c22, fc.c23, fc.c24, fc.nz24
               WHERE item.sku_code = 'SKU-H04' AND geo.country_code = 'IT'))
SELECT f.*, s.stock_qty FROM f LEFT JOIN s USING (sku_code, country_code, month_start, month_index)
WHERE month_start = '2026-06-01'
```

query id `000002bc-0000-4000-8000-0000000002bc`, 1 row(s)

| SKU_CODE | COUNTRY_CODE | MONTH_START | MONTH_INDEX | C01 | C02 | C03 | C04 | C05 | C06 | C07 | C08 | NZ24 | STOCK_QTY |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SKU-H04 | IT | 2026-06-01 | 24318 | 100.0000 | 200.0000 | 300.0000 | 400.0000 | 500.0000 | 600.0000 | 700.0000 | 800.0000 | 24 | 600.0000 |

**T3 two calls: coverage rebuilt from the view = 6.0 (None); expected 6.0 -> MATCH**

## T1 ratio re-aggregation (PANTRY_FLOUR / FR, expected 2.8)

#### T1, family grain

```sql
SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV
    DIMENSIONS item.family_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, fc.c01, fc.c02, fc.c03, fc.c04, fc.c05, fc.c06, fc.c07, fc.c08, fc.c09, fc.c10, fc.c11, fc.c12, fc.c13, fc.c14, fc.c15, fc.c16, fc.c17, fc.c18, fc.c19, fc.c20, fc.c21, fc.c22, fc.c23, fc.c24, fc.nz24
    WHERE item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR')
WHERE month_start = '2026-06-01'
```

query id `000002bd-0000-4000-8000-0000000002bd`, 1 row(s)

| FAMILY_CODE | COUNTRY_CODE | MONTH_START | MONTH_INDEX | STOCK_QTY | C01 | C02 | C03 | C04 | C05 | C06 | C07 | C08 | NZ24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PANTRY_FLOUR | FR | 2026-06-01 | 24318 | 1400.0000 | 500.0000 | 1000.0000 | 1500.0000 | 2000.0000 | 2500.0000 | 3000.0000 | 3500.0000 | 4000.0000 | 24 |

**T1 family: coverage rebuilt from the view = 2.8 (None); expected 2.8 -> MATCH**

## T7 master-data fan-out (PANTRY_OIL / SE, expected stock 900, C1 400, coverage 2.25)

#### T7, family grain over a dimension declared PRIMARY KEY but duplicated

```sql
SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV
    DIMENSIONS item.family_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, fc.c01, fc.c02, fc.c03, fc.c04, fc.c05, fc.c06, fc.c07, fc.c08, fc.c09, fc.c10, fc.c11, fc.c12, fc.c13, fc.c14, fc.c15, fc.c16, fc.c17, fc.c18, fc.c19, fc.c20, fc.c21, fc.c22, fc.c23, fc.c24, fc.nz24
    WHERE item.family_code = 'PANTRY_OIL' AND geo.country_code = 'SE')
WHERE month_start = '2026-06-01'
```

query id `000002be-0000-4000-8000-0000000002be`, 1 row(s)

| FAMILY_CODE | COUNTRY_CODE | MONTH_START | MONTH_INDEX | STOCK_QTY | C01 | C02 | C03 | C04 | C05 | C06 | C07 | C08 | NZ24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PANTRY_OIL | SE | 2026-06-01 | 24318 | 1500.0000 | 500.0000 | 1000.0000 | 1500.0000 | 2000.0000 | 2500.0000 | 3000.0000 | 3500.0000 | 4000.0000 | 24 |

**T7 family: coverage rebuilt from the view = 3.0 (None); expected 2.25 -> MISMATCH**

## Semi-additive stock and T8

#### NON ADDITIVE BY: stock of SKU-H04 / IT without the month dimension (expected latest = 1000)

```sql
SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV
    DIMENSIONS item.sku_code, geo.country_code
    METRICS stock.stock_qty
    WHERE item.sku_code = 'SKU-H04' AND geo.country_code = 'IT')
```

query id `000002bf-0000-4000-8000-0000000002bf`, 1 row(s)

| SKU_CODE | COUNTRY_CODE | STOCK_QTY |
|---|---|---|
| SKU-H04 | IT | 1000.0000 |

#### T8: SKU-H08 / NL, forecast but no stock (expected 0, row kept)

```sql
SELECT * FROM SEMANTIC_VIEW(LINKML_METRICS.RAW.COVERAGE_NATIVE_RANGE_SV
    DIMENSIONS item.sku_code, geo.country_code, cal.month_start, cal.month_index
    METRICS stock.stock_qty, fc.c01, fc.c02, fc.c03, fc.c04, fc.c05, fc.c06, fc.c07, fc.c08, fc.c09, fc.c10, fc.c11, fc.c12, fc.c13, fc.c14, fc.c15, fc.c16, fc.c17, fc.c18, fc.c19, fc.c20, fc.c21, fc.c22, fc.c23, fc.c24, fc.nz24
    WHERE item.sku_code = 'SKU-H08' AND geo.country_code = 'NL')
WHERE month_start = '2026-06-01'
```

query id `000002c0-0000-4000-8000-0000000002c0`, 1 row(s)

| SKU_CODE | COUNTRY_CODE | MONTH_START | MONTH_INDEX | STOCK_QTY | C01 | C02 | C03 | C04 | C05 | C06 | C07 | C08 | NZ24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SKU-H08 | NL | 2026-06-01 | 24318 | NULL | 100.0000 | 200.0000 | 300.0000 | 400.0000 | 500.0000 | 600.0000 | 700.0000 | 800.0000 | 24 |

**T8: coverage rebuilt from the view = 0.0 (NO_STOCK); expected 0.0 -> MATCH**
