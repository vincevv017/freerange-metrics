-- GENERATED from contract/stock_coverage.yaml (contract stock_coverage, version 0.5.1)
-- by compiler/gen_dmf.py. Do not edit: change the contract and run `python compiler/gen_dmf.py`.
-- Ad hoc only: no DMF is attached to a table and no DATA_METRIC_SCHEDULE is set.

-- ============================================================================ 1. custom DMFs

-- QE_STOCK_GRAIN (GRAIN_UNIQUENESS, on_failure MONITOR, threshold 0): one row per snapshot_month x batch_id x warehouse_id
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_STOCK_GRAIN(t TABLE(snapshot_month DATE, batch_id NUMBER(8,0), warehouse_id NUMBER(6,0)))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_STOCK_GRAIN'
  AS
$$
SELECT COUNT(*) - COUNT(DISTINCT snapshot_month, batch_id, warehouse_id) FROM t
$$;

-- QE_FORECAST_GRAIN (GRAIN_UNIQUENESS, on_failure MONITOR, threshold 0): one row per forecast_month x item_id x country_id
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_FORECAST_GRAIN(t TABLE(forecast_month DATE, item_id NUMBER(6,0), country_id NUMBER(6,0)))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_FORECAST_GRAIN'
  AS
$$
SELECT COUNT(*) - COUNT(DISTINCT forecast_month, item_id, country_id) FROM t
$$;

-- QE_STOCK_ITEM_REF (REFERENTIAL, on_failure WARN, threshold 0): every stock item_id exists in DIM_ITEM
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_STOCK_ITEM_REF(t TABLE(item_id NUMBER(6,0)), r TABLE(item_id NUMBER(6,0)))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_STOCK_ITEM_REF'
  AS
$$
SELECT COUNT(*) FROM t WHERE NOT EXISTS (SELECT 1 FROM r WHERE r.item_id = t.item_id)
$$;

-- QE_STOCK_BATCH_REF (REFERENTIAL, on_failure WARN, threshold 0): every stock batch_id exists in DIM_BATCH
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_STOCK_BATCH_REF(t TABLE(batch_id NUMBER(8,0)), r TABLE(batch_id NUMBER(8,0)))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_STOCK_BATCH_REF'
  AS
$$
SELECT COUNT(*) FROM t WHERE NOT EXISTS (SELECT 1 FROM r WHERE r.batch_id = t.batch_id)
$$;

-- QE_STOCK_WAREHOUSE_REF (REFERENTIAL, on_failure WARN, threshold 0): every stock warehouse_id exists in DIM_WAREHOUSE
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_STOCK_WAREHOUSE_REF(t TABLE(warehouse_id NUMBER(6,0)), r TABLE(warehouse_id NUMBER(6,0)))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_STOCK_WAREHOUSE_REF'
  AS
$$
SELECT COUNT(*) FROM t WHERE NOT EXISTS (SELECT 1 FROM r WHERE r.warehouse_id = t.warehouse_id)
$$;

-- QE_STOCK_GEO_REF (REFERENTIAL, on_failure WARN, threshold 0): every stock country_id exists in DIM_GEO
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_STOCK_GEO_REF(t TABLE(country_id NUMBER(6,0)), r TABLE(country_id NUMBER(6,0)))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_STOCK_GEO_REF'
  AS
$$
SELECT COUNT(*) FROM t WHERE NOT EXISTS (SELECT 1 FROM r WHERE r.country_id = t.country_id)
$$;

-- QE_FORECAST_ITEM_REF (REFERENTIAL, on_failure WARN, threshold 0): every forecast item_id exists in DIM_ITEM
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_FORECAST_ITEM_REF(t TABLE(item_id NUMBER(6,0)), r TABLE(item_id NUMBER(6,0)))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_FORECAST_ITEM_REF'
  AS
$$
SELECT COUNT(*) FROM t WHERE NOT EXISTS (SELECT 1 FROM r WHERE r.item_id = t.item_id)
$$;

-- QE_FORECAST_GEO_REF (REFERENTIAL, on_failure WARN, threshold 0): every forecast country_id exists in DIM_GEO
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_FORECAST_GEO_REF(t TABLE(country_id NUMBER(6,0)), r TABLE(country_id NUMBER(6,0)))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_FORECAST_GEO_REF'
  AS
$$
SELECT COUNT(*) FROM t WHERE NOT EXISTS (SELECT 1 FROM r WHERE r.country_id = t.country_id)
$$;

-- QE_STOCK_BATCH_ITEM (CARDINALITY, on_failure WARN, threshold 0): the denormalised item_id of a stock row equals the item_id of its batch
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_STOCK_BATCH_ITEM(t TABLE(batch_id NUMBER(8,0), item_id NUMBER(6,0)), r TABLE(batch_id NUMBER(8,0), item_id NUMBER(6,0)))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_STOCK_BATCH_ITEM'
  AS
$$
SELECT COUNT(*) FROM t WHERE NOT EXISTS (SELECT 1 FROM r WHERE r.batch_id = t.batch_id AND r.item_id = t.item_id)
$$;

-- QE_SKU_FAMILY (CARDINALITY, on_failure REFUSE, threshold 0): each sku_code maps to one family_code and each family_code to one range_code
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_SKU_FAMILY(t TABLE(sku_code VARCHAR, family_code VARCHAR, range_code VARCHAR))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_SKU_FAMILY'
  AS
$$
SELECT (SELECT COUNT(*) FROM (SELECT sku_code FROM t GROUP BY sku_code HAVING COUNT(DISTINCT family_code) > 1)) + (SELECT COUNT(*) FROM (SELECT family_code FROM t GROUP BY family_code HAVING COUNT(DISTINCT range_code) > 1))
$$;

-- QE_COUNTRY_REGION (CARDINALITY, on_failure REFUSE, threshold 0): each country_code maps to one region_code
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_COUNTRY_REGION(t TABLE(country_code VARCHAR, region_code VARCHAR))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_COUNTRY_REGION'
  AS
$$
SELECT (SELECT COUNT(*) FROM (SELECT country_code FROM t GROUP BY country_code HAVING COUNT(DISTINCT region_code) > 1))
$$;

-- QE_FORECAST_DENSE (COMPLETENESS, on_failure WARN, threshold 0): every item x country with a forecast row in the horizon of LATEST has a row for every month of that horizon
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_FORECAST_DENSE(t TABLE(forecast_month DATE, item_id NUMBER(6,0), country_id NUMBER(6,0)), r TABLE(snapshot_month DATE))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_FORECAST_DENSE'
  AS
$$
WITH b AS (SELECT MAX(snapshot_month) AS latest FROM r), p AS (SELECT DATEADD(month, k.column1, b.latest) AS period FROM (VALUES (1), (2), (3), (4), (5), (6), (7), (8), (9), (10), (11), (12), (13), (14), (15), (16), (17), (18), (19), (20), (21), (22), (23), (24)) k, b), m AS (SELECT DISTINCT item_id, country_id FROM t WHERE forecast_month IN (SELECT period FROM p)) SELECT COUNT(*) FROM m CROSS JOIN p WHERE NOT EXISTS (SELECT 1 FROM t f WHERE f.item_id = m.item_id AND f.country_id = m.country_id AND f.forecast_month = p.period)
$$;

-- QE_HORIZON_LOADED (FRESHNESS, on_failure REFUSE, threshold 0): the calendar reaches LATEST + 24 months
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_HORIZON_LOADED(t TABLE(month_start DATE), r TABLE(snapshot_month DATE))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_HORIZON_LOADED'
  AS
$$
SELECT GREATEST(0, DATEDIFF(month, (SELECT MAX(month_start) FROM t), DATEADD(month, 24, (SELECT MAX(snapshot_month) FROM r))))
$$;

-- QE_FORECAST_REACH (FRESHNESS, on_failure REFUSE, threshold 0): the forecast reaches LATEST + 24 months
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_FORECAST_REACH(t TABLE(forecast_month DATE), r TABLE(snapshot_month DATE))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_FORECAST_REACH'
  AS
$$
SELECT GREATEST(0, DATEDIFF(month, (SELECT MAX(forecast_month) FROM t), DATEADD(month, 24, (SELECT MAX(snapshot_month) FROM r))))
$$;

-- QE_ACCEPTED_VALUES (VALUE_RANGE, on_failure MONITOR, threshold 0): values are within the attribute's known_values
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_ACCEPTED_VALUES(t TABLE(batch_status VARCHAR))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_ACCEPTED_VALUES'
  AS
$$
SELECT COUNT(*) FROM t WHERE batch_status NOT IN ('RELEASED', 'QUALITY_HOLD', 'BLOCKED')
$$;

-- QE_EQ_FACTOR (VALUE_RANGE, on_failure MONITOR, threshold 0): qty_eq_factor > 0
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_EQ_FACTOR(t TABLE(qty_eq_factor NUMBER(10,4)))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_EQ_FACTOR'
  AS
$$
SELECT COUNT(*) FROM t WHERE NOT COALESCE((qty_eq_factor > 0), FALSE)
$$;

-- QE_ITEM_DIMENSION (VALUE_RANGE, on_failure MONITOR, threshold 0): dimension is a declared item dimension and base_unit is that dimension's base unit
CREATE OR REPLACE DATA METRIC FUNCTION LINKML_METRICS.RAW.DMF_QE_ITEM_DIMENSION(t TABLE(dimension VARCHAR, base_unit VARCHAR))
  RETURNS NUMBER
  COMMENT = 'Generated from contract stock_coverage 0.5.1, QE_ITEM_DIMENSION'
  AS
$$
SELECT COUNT(*) FROM t WHERE base_unit IS DISTINCT FROM CASE dimension WHEN 'MASS' THEN 'kg' WHEN 'VOLUME' THEN 'L' END OR dimension IS NULL
$$;

-- ============================================================================ 2. checks

-- QE_STOCK_GRAIN (GRAIN_UNIQUENESS, on_failure MONITOR, threshold 0): one row per snapshot_month x batch_id x warehouse_id
SELECT 'QE_STOCK_GRAIN' AS expectation, 'FCT_STOCK_SNAPSHOT' AS target, LINKML_METRICS.RAW.DMF_QE_STOCK_GRAIN(SELECT snapshot_month, batch_id, warehouse_id FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT) AS value;

-- QE_FORECAST_GRAIN (GRAIN_UNIQUENESS, on_failure MONITOR, threshold 0): one row per forecast_month x item_id x country_id
SELECT 'QE_FORECAST_GRAIN' AS expectation, 'FCT_FORECAST' AS target, LINKML_METRICS.RAW.DMF_QE_FORECAST_GRAIN(SELECT forecast_month, item_id, country_id FROM LINKML_METRICS.RAW.FCT_FORECAST) AS value;

-- QE_ITEM_GRAIN (GRAIN_UNIQUENESS, on_failure REFUSE_IF_USED, threshold 0): one row per item_id
SELECT 'QE_ITEM_GRAIN' AS expectation, 'DIM_ITEM.item_id' AS target, SNOWFLAKE.CORE.DUPLICATE_COUNT(SELECT item_id FROM LINKML_METRICS.RAW.DIM_ITEM) AS value;

-- QE_GEO_GRAIN (GRAIN_UNIQUENESS, on_failure REFUSE, threshold 0): one row per country_id
SELECT 'QE_GEO_GRAIN' AS expectation, 'DIM_GEO.country_id' AS target, SNOWFLAKE.CORE.DUPLICATE_COUNT(SELECT country_id FROM LINKML_METRICS.RAW.DIM_GEO) AS value;

-- QE_BATCH_GRAIN (GRAIN_UNIQUENESS, on_failure REFUSE, threshold 0): one row per batch_id
SELECT 'QE_BATCH_GRAIN' AS expectation, 'DIM_BATCH.batch_id' AS target, SNOWFLAKE.CORE.DUPLICATE_COUNT(SELECT batch_id FROM LINKML_METRICS.RAW.DIM_BATCH) AS value;

-- QE_WAREHOUSE_GRAIN (GRAIN_UNIQUENESS, on_failure REFUSE, threshold 0): one row per warehouse_id
SELECT 'QE_WAREHOUSE_GRAIN' AS expectation, 'DIM_WAREHOUSE.warehouse_id' AS target, SNOWFLAKE.CORE.DUPLICATE_COUNT(SELECT warehouse_id FROM LINKML_METRICS.RAW.DIM_WAREHOUSE) AS value;

-- QE_CALENDAR_GRAIN (GRAIN_UNIQUENESS, on_failure REFUSE, threshold 0): one row per month_start
SELECT 'QE_CALENDAR_GRAIN' AS expectation, 'DIM_CALENDAR.month_start' AS target, SNOWFLAKE.CORE.DUPLICATE_COUNT(SELECT month_start FROM LINKML_METRICS.RAW.DIM_CALENDAR) AS value;

-- QE_STOCK_ITEM_REF (REFERENTIAL, on_failure WARN, threshold 0): every stock item_id exists in DIM_ITEM
SELECT 'QE_STOCK_ITEM_REF' AS expectation, 'FCT_STOCK_SNAPSHOT' AS target, LINKML_METRICS.RAW.DMF_QE_STOCK_ITEM_REF((SELECT item_id FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT), (SELECT item_id FROM LINKML_METRICS.RAW.DIM_ITEM)) AS value;

-- QE_STOCK_BATCH_REF (REFERENTIAL, on_failure WARN, threshold 0): every stock batch_id exists in DIM_BATCH
SELECT 'QE_STOCK_BATCH_REF' AS expectation, 'FCT_STOCK_SNAPSHOT' AS target, LINKML_METRICS.RAW.DMF_QE_STOCK_BATCH_REF((SELECT batch_id FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT), (SELECT batch_id FROM LINKML_METRICS.RAW.DIM_BATCH)) AS value;

-- QE_STOCK_WAREHOUSE_REF (REFERENTIAL, on_failure WARN, threshold 0): every stock warehouse_id exists in DIM_WAREHOUSE
SELECT 'QE_STOCK_WAREHOUSE_REF' AS expectation, 'FCT_STOCK_SNAPSHOT' AS target, LINKML_METRICS.RAW.DMF_QE_STOCK_WAREHOUSE_REF((SELECT warehouse_id FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT), (SELECT warehouse_id FROM LINKML_METRICS.RAW.DIM_WAREHOUSE)) AS value;

-- QE_STOCK_GEO_REF (REFERENTIAL, on_failure WARN, threshold 0): every stock country_id exists in DIM_GEO
SELECT 'QE_STOCK_GEO_REF' AS expectation, 'FCT_STOCK_SNAPSHOT' AS target, LINKML_METRICS.RAW.DMF_QE_STOCK_GEO_REF((SELECT country_id FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT), (SELECT country_id FROM LINKML_METRICS.RAW.DIM_GEO)) AS value;

-- QE_FORECAST_ITEM_REF (REFERENTIAL, on_failure WARN, threshold 0): every forecast item_id exists in DIM_ITEM
SELECT 'QE_FORECAST_ITEM_REF' AS expectation, 'FCT_FORECAST' AS target, LINKML_METRICS.RAW.DMF_QE_FORECAST_ITEM_REF((SELECT item_id FROM LINKML_METRICS.RAW.FCT_FORECAST), (SELECT item_id FROM LINKML_METRICS.RAW.DIM_ITEM)) AS value;

-- QE_FORECAST_GEO_REF (REFERENTIAL, on_failure WARN, threshold 0): every forecast country_id exists in DIM_GEO
SELECT 'QE_FORECAST_GEO_REF' AS expectation, 'FCT_FORECAST' AS target, LINKML_METRICS.RAW.DMF_QE_FORECAST_GEO_REF((SELECT country_id FROM LINKML_METRICS.RAW.FCT_FORECAST), (SELECT country_id FROM LINKML_METRICS.RAW.DIM_GEO)) AS value;

-- QE_STOCK_BATCH_ITEM (CARDINALITY, on_failure WARN, threshold 0): the denormalised item_id of a stock row equals the item_id of its batch
SELECT 'QE_STOCK_BATCH_ITEM' AS expectation, 'FCT_STOCK_SNAPSHOT' AS target, LINKML_METRICS.RAW.DMF_QE_STOCK_BATCH_ITEM((SELECT batch_id, item_id FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT), (SELECT batch_id, item_id FROM LINKML_METRICS.RAW.DIM_BATCH)) AS value;

-- QE_SKU_FAMILY (CARDINALITY, on_failure REFUSE, threshold 0): each sku_code maps to one family_code and each family_code to one range_code
SELECT 'QE_SKU_FAMILY' AS expectation, 'DIM_ITEM' AS target, LINKML_METRICS.RAW.DMF_QE_SKU_FAMILY(SELECT sku_code, family_code, range_code FROM LINKML_METRICS.RAW.DIM_ITEM) AS value;

-- QE_COUNTRY_REGION (CARDINALITY, on_failure REFUSE, threshold 0): each country_code maps to one region_code
SELECT 'QE_COUNTRY_REGION' AS expectation, 'DIM_GEO' AS target, LINKML_METRICS.RAW.DMF_QE_COUNTRY_REGION(SELECT country_code, region_code FROM LINKML_METRICS.RAW.DIM_GEO) AS value;

-- QE_FORECAST_DENSE (COMPLETENESS, on_failure WARN, threshold 0): every item x country with a forecast row in the horizon of LATEST has a row for every month of that horizon
SELECT 'QE_FORECAST_DENSE' AS expectation, 'FCT_FORECAST' AS target, LINKML_METRICS.RAW.DMF_QE_FORECAST_DENSE((SELECT forecast_month, item_id, country_id FROM LINKML_METRICS.RAW.FCT_FORECAST), (SELECT snapshot_month FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT)) AS value;

-- QE_MEASURES_NOT_NULL (COMPLETENESS, on_failure MONITOR, threshold 0): measure columns are not null
SELECT 'QE_MEASURES_NOT_NULL' AS expectation, 'FCT_STOCK_SNAPSHOT.stock_qty_eq' AS target, SNOWFLAKE.CORE.NULL_COUNT(SELECT stock_qty_eq FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT) AS value;
SELECT 'QE_MEASURES_NOT_NULL' AS expectation, 'FCT_STOCK_SNAPSHOT.stock_value_eur' AS target, SNOWFLAKE.CORE.NULL_COUNT(SELECT stock_value_eur FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT) AS value;

-- QE_FORECAST_NOT_NULL (COMPLETENESS, on_failure MONITOR, threshold 0): measure columns are not null
SELECT 'QE_FORECAST_NOT_NULL' AS expectation, 'FCT_FORECAST.forecast_qty_eq' AS target, SNOWFLAKE.CORE.NULL_COUNT(SELECT forecast_qty_eq FROM LINKML_METRICS.RAW.FCT_FORECAST) AS value;
SELECT 'QE_FORECAST_NOT_NULL' AS expectation, 'FCT_FORECAST.forecast_value_eur' AS target, SNOWFLAKE.CORE.NULL_COUNT(SELECT forecast_value_eur FROM LINKML_METRICS.RAW.FCT_FORECAST) AS value;

-- QE_ATTRIBUTES_NOT_NULL (COMPLETENESS, on_failure MONITOR, threshold 0): conformed and snapshot-only item attributes are not null
SELECT 'QE_ATTRIBUTES_NOT_NULL' AS expectation, 'DIM_ITEM.sku_code' AS target, SNOWFLAKE.CORE.NULL_COUNT(SELECT sku_code FROM LINKML_METRICS.RAW.DIM_ITEM) AS value;
SELECT 'QE_ATTRIBUTES_NOT_NULL' AS expectation, 'DIM_ITEM.family_code' AS target, SNOWFLAKE.CORE.NULL_COUNT(SELECT family_code FROM LINKML_METRICS.RAW.DIM_ITEM) AS value;
SELECT 'QE_ATTRIBUTES_NOT_NULL' AS expectation, 'DIM_ITEM.range_code' AS target, SNOWFLAKE.CORE.NULL_COUNT(SELECT range_code FROM LINKML_METRICS.RAW.DIM_ITEM) AS value;
SELECT 'QE_ATTRIBUTES_NOT_NULL' AS expectation, 'DIM_ITEM.item_type' AS target, SNOWFLAKE.CORE.NULL_COUNT(SELECT item_type FROM LINKML_METRICS.RAW.DIM_ITEM) AS value;
SELECT 'QE_ATTRIBUTES_NOT_NULL' AS expectation, 'DIM_ITEM.lifecycle_status' AS target, SNOWFLAKE.CORE.NULL_COUNT(SELECT lifecycle_status FROM LINKML_METRICS.RAW.DIM_ITEM) AS value;

-- QE_STOCK_FRESHNESS (FRESHNESS, on_failure WARN, threshold TBD): the latest snapshot month is at most TBD months before the current month
SELECT 'QE_STOCK_FRESHNESS' AS expectation, 'FCT_STOCK_SNAPSHOT.snapshot_month' AS target, SNOWFLAKE.CORE.FRESHNESS(SELECT snapshot_month FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT) AS value;

-- QE_HORIZON_LOADED (FRESHNESS, on_failure REFUSE, threshold 0): the calendar reaches LATEST + 24 months
SELECT 'QE_HORIZON_LOADED' AS expectation, 'DIM_CALENDAR' AS target, LINKML_METRICS.RAW.DMF_QE_HORIZON_LOADED((SELECT month_start FROM LINKML_METRICS.RAW.DIM_CALENDAR), (SELECT snapshot_month FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT)) AS value;

-- QE_FORECAST_REACH (FRESHNESS, on_failure REFUSE, threshold 0): the forecast reaches LATEST + 24 months
SELECT 'QE_FORECAST_REACH' AS expectation, 'FCT_FORECAST' AS target, LINKML_METRICS.RAW.DMF_QE_FORECAST_REACH((SELECT forecast_month FROM LINKML_METRICS.RAW.FCT_FORECAST), (SELECT snapshot_month FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT)) AS value;

-- QE_NON_NEGATIVE (VALUE_RANGE, on_failure MONITOR, threshold 0): stock is >= 0
SELECT 'QE_NON_NEGATIVE' AS expectation, 'FCT_STOCK_SNAPSHOT.stock_qty_eq' AS target, SNOWFLAKE.CORE.NEGATIVE_COUNT(SELECT stock_qty_eq FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT) AS value;
SELECT 'QE_NON_NEGATIVE' AS expectation, 'FCT_STOCK_SNAPSHOT.stock_value_eur' AS target, SNOWFLAKE.CORE.NEGATIVE_COUNT(SELECT stock_value_eur FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT) AS value;

-- QE_FORECAST_NON_NEGATIVE (VALUE_RANGE, on_failure MONITOR, threshold 0): forecast is >= 0
SELECT 'QE_FORECAST_NON_NEGATIVE' AS expectation, 'FCT_FORECAST.forecast_qty_eq' AS target, SNOWFLAKE.CORE.NEGATIVE_COUNT(SELECT forecast_qty_eq FROM LINKML_METRICS.RAW.FCT_FORECAST) AS value;
SELECT 'QE_FORECAST_NON_NEGATIVE' AS expectation, 'FCT_FORECAST.forecast_value_eur' AS target, SNOWFLAKE.CORE.NEGATIVE_COUNT(SELECT forecast_value_eur FROM LINKML_METRICS.RAW.FCT_FORECAST) AS value;

-- QE_ACCEPTED_VALUES (VALUE_RANGE, on_failure MONITOR, threshold 0): values are within the attribute's known_values
SELECT 'QE_ACCEPTED_VALUES' AS expectation, 'DIM_BATCH' AS target, LINKML_METRICS.RAW.DMF_QE_ACCEPTED_VALUES(SELECT batch_status FROM LINKML_METRICS.RAW.DIM_BATCH) AS value;

-- QE_EQ_FACTOR (VALUE_RANGE, on_failure MONITOR, threshold 0): qty_eq_factor > 0
SELECT 'QE_EQ_FACTOR' AS expectation, 'DIM_ITEM' AS target, LINKML_METRICS.RAW.DMF_QE_EQ_FACTOR(SELECT qty_eq_factor FROM LINKML_METRICS.RAW.DIM_ITEM) AS value;

-- QE_ITEM_DIMENSION (VALUE_RANGE, on_failure MONITOR, threshold 0): dimension is a declared item dimension and base_unit is that dimension's base unit
SELECT 'QE_ITEM_DIMENSION' AS expectation, 'DIM_ITEM' AS target, LINKML_METRICS.RAW.DMF_QE_ITEM_DIMENSION(SELECT dimension, base_unit FROM LINKML_METRICS.RAW.DIM_ITEM) AS value;
