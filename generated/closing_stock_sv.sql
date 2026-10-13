-- GENERATED from contract/stock_coverage.yaml (contract stock_coverage, version 0.5.1)
-- by compiler/gen_closing_sv.py. Do not edit: change the contract and run `python compiler/gen_closing_sv.py`.
-- tests/test_generated.py regenerates this file and fails on any difference.
--
-- LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT_GAPFILLED: the snapshot table, gap-filled per key. LINKML_METRICS.RAW.CLOSING_STOCK_SV: closing stock over a month range, a
-- quarter or a year, NON ADDITIVE BY the snapshot month. Run as the project role with no secondary role.
USE SECONDARY ROLES NONE;
USE ROLE LINKML_METRICS_ROLE;
CREATE OR REPLACE VIEW LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT_GAPFILLED
  COMMENT = 'Generated from contract stock_coverage 0.5.1 (CLOSING_STOCK): FCT_STOCK_SNAPSHOT with every key filled from its first month to its last month + 1 (capped at the latest snapshot), measures 0 where absent.'
AS
WITH bounds AS (SELECT MAX(snapshot_month) AS latest FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT),
key_span AS (
    SELECT batch_id, warehouse_id, MIN(snapshot_month) AS first_month, MAX(snapshot_month) AS last_month
    FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT GROUP BY batch_id, warehouse_id
),
grid AS (
    SELECT k.batch_id, k.warehouse_id, cal.month_start AS snapshot_month
    FROM key_span k CROSS JOIN bounds b
    JOIN LINKML_METRICS.RAW.DIM_CALENDAR cal ON cal.month_start >= k.first_month
     AND cal.month_start <= LEAST(DATEADD(month, 1, k.last_month), b.latest)
)
SELECT g.snapshot_month, g.batch_id, g.warehouse_id,
       LAST_VALUE(s.item_id) IGNORE NULLS OVER (PARTITION BY g.batch_id, g.warehouse_id ORDER BY g.snapshot_month
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS item_id,
       LAST_VALUE(s.country_id) IGNORE NULLS OVER (PARTITION BY g.batch_id, g.warehouse_id ORDER BY g.snapshot_month
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS country_id,
       LAST_VALUE(s.expiry_bucket) IGNORE NULLS OVER (PARTITION BY g.batch_id, g.warehouse_id ORDER BY g.snapshot_month
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS expiry_bucket,
       COALESCE(s.stock_qty_eq, 0) AS stock_qty_eq,
       COALESCE(s.stock_value_eur, 0) AS stock_value_eur,
       COALESCE(s.stock_qty_raw, 0) AS stock_qty_raw,
       s.snapshot_month IS NULL AS gap_filled
FROM grid g
LEFT JOIN LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT s ON s.batch_id = g.batch_id AND s.warehouse_id = g.warehouse_id AND s.snapshot_month = g.snapshot_month;

CREATE OR REPLACE SEMANTIC VIEW LINKML_METRICS.RAW.CLOSING_STOCK_SV
  TABLES (
    item AS (SELECT DISTINCT item_id, sku_code, family_code, range_code, lifecycle_status, dimension, item_type FROM LINKML_METRICS.RAW.DIM_ITEM) PRIMARY KEY (item_id)
      COMMENT = 'Distinct projection: the declared grain item_id is checked by a REFUSE_IF_USED expectation, which a semantic view cannot enforce.',
    geo AS LINKML_METRICS.RAW.DIM_GEO PRIMARY KEY (country_id),
    batch AS LINKML_METRICS.RAW.DIM_BATCH PRIMARY KEY (batch_id),
    warehouse AS LINKML_METRICS.RAW.DIM_WAREHOUSE PRIMARY KEY (warehouse_id),
    calendar AS LINKML_METRICS.RAW.DIM_CALENDAR PRIMARY KEY (month_start),
    stock_snapshot AS LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT_GAPFILLED PRIMARY KEY (snapshot_month, batch_id, warehouse_id)
      COMMENT = 'Closing stock of the month. A level, never summed over months. Gap-filled: a key with no row in a month of its span counts 0.'
  )
  RELATIONSHIPS (
    stock_snapshot_item AS stock_snapshot (item_id) REFERENCES item,
    stock_snapshot_geo AS stock_snapshot (country_id) REFERENCES geo,
    stock_snapshot_batch AS stock_snapshot (batch_id) REFERENCES batch,
    stock_snapshot_warehouse AS stock_snapshot (warehouse_id) REFERENCES warehouse,
    stock_snapshot_calendar AS stock_snapshot (snapshot_month) REFERENCES calendar
  )
  DIMENSIONS (
    item.sku_code AS sku_code,
    item.family_code AS family_code,
    item.range_code AS range_code,
    item.lifecycle_status AS lifecycle_status COMMENT = 'An item attribute, so the forecast carries it too (decision 6, session 4). Trap T7 duplicates exactly this column: QE_ITEM_GRAIN refuses a query that uses it while an item has two values.',
    item.dimension AS dimension COMMENT = 'The physical dimension in which the item is counted, with its base unit: MASS (kg) or VOLUME (L). Grouping or filtering by it keeps quantity-equivalent rows within one dimension.',
    geo.country_code AS country_code COMMENT = 'ISO 3166-1 alpha-2 code.',
    geo.region_code AS region_code,
    batch.batch_status AS batch_status,
    stock_snapshot.expiry_bucket AS expiry_bucket,
    warehouse.warehouse_code AS warehouse_code,
    warehouse.warehouse_type AS warehouse_type,
    item.item_type AS item_type COMMENT = 'Snapshot-only by decision: BULK items carry stock but never a forecast. Default scope STANDARD for stock coverage only (SCOPE_ITEM_TYPE, decision 5); closing stock counts every item type.',
    calendar.month_start AS month_start,
    calendar.year_quarter AS year || '-Q' || quarter,
    calendar.year AS year,
    stock_snapshot.snapshot_month AS snapshot_month,
    stock_snapshot.gap_filled AS gap_filled COMMENT = 'TRUE on a row added by the gap fill (measures 0).'
  )
  METRICS (
    stock_snapshot.closing_stock_qty_eq NON ADDITIVE BY (stock_snapshot.snapshot_month ASC NULLS LAST) AS SUM(stock_qty_eq)
      COMMENT = 'Closing stock in kg or L equivalent; kg and L never add up: group or filter by dimension when items of both dimensions are combined, or use the value metric: the snapshot of the period''s last month; never sum, average, last_non_empty over time.',
    stock_snapshot.closing_stock_value NON ADDITIVE BY (stock_snapshot.snapshot_month ASC NULLS LAST) AS SUM(stock_value_eur)
      COMMENT = 'Closing stock in EUR, comparable across every item: the snapshot of the period''s last month; never sum, average, last_non_empty over time.'
  )
  COMMENT = 'Generated from contract stock_coverage 0.5.1 by compiler/gen_closing_sv.py: closing stock (CLOSING_STOCK, LAST_PERIOD).';
