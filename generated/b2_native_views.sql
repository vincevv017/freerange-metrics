-- GENERATED from contract/stock_coverage.yaml (contract stock_coverage, version 0.5.1)
-- by compiler/gen_native_sv.py. Do not edit: change the contract and run `python compiler/gen_native_sv.py`.
-- tests/test_generated.py regenerates this file and fails on any difference.
-- Configuration B2 (session 8): the physical views LINKML_B2_SV reads. Run as the project role with no
-- secondary role. FCT_STOCK_SNAPSHOT_GAPFILLED comes from generated/closing_stock_sv.sql.
USE SECONDARY ROLES NONE;
USE ROLE LINKML_METRICS_ROLE;
CREATE OR REPLACE VIEW LINKML_METRICS.RAW.B2_ITEM
  COMMENT = 'Generated from contract stock_coverage 0.5.1: distinct item rows on the item attributes. The declared grain item_id is checked by a REFUSE_IF_USED expectation, which a semantic view cannot enforce: an item whose rows differ on an attribute keeps two rows.'
AS
SELECT DISTINCT item_id, sku_code, sku_name, family_code, family_name, range_code, range_name, lifecycle_status, dimension, base_unit, item_type
FROM LINKML_METRICS.RAW.DIM_ITEM;

CREATE OR REPLACE VIEW LINKML_METRICS.RAW.B2_STATUS
  COMMENT = 'Generated from contract stock_coverage 0.5.1: the values of the bridged stock-only attribute batch_status.'
AS
SELECT DISTINCT batch_status FROM LINKML_METRICS.RAW.DIM_BATCH;

CREATE OR REPLACE VIEW LINKML_METRICS.RAW.B2_FORECAST_SPINE
  COMMENT = 'Generated from contract stock_coverage 0.5.1: forward spine of stock_coverage, one row per valid analysis month x item x country x batch_status (status bridge), flow of t+1..t+24 as columns, missing months 0.'
AS
WITH snaps AS (SELECT DISTINCT snapshot_month AS m FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT),
reach AS (SELECT (SELECT MAX(month_start) FROM LINKML_METRICS.RAW.DIM_CALENDAR) AS cal_max,
                 (SELECT MAX(forecast_month) FROM LINKML_METRICS.RAW.FCT_FORECAST) AS fc_max),
v AS (SELECT m FROM snaps, reach WHERE cal_max >= DATEADD(month, 24, m) AND fc_max >= DATEADD(month, 24, m)),
st AS (SELECT DISTINCT batch_status FROM LINKML_METRICS.RAW.DIM_BATCH)
SELECT v.m AS as_of_month, f.item_id, f.country_id, st.batch_status,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 1, f.forecast_qty_eq, 0)) AS f01_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 2, f.forecast_qty_eq, 0)) AS f02_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 3, f.forecast_qty_eq, 0)) AS f03_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 4, f.forecast_qty_eq, 0)) AS f04_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 5, f.forecast_qty_eq, 0)) AS f05_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 6, f.forecast_qty_eq, 0)) AS f06_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 7, f.forecast_qty_eq, 0)) AS f07_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 8, f.forecast_qty_eq, 0)) AS f08_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 9, f.forecast_qty_eq, 0)) AS f09_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 10, f.forecast_qty_eq, 0)) AS f10_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 11, f.forecast_qty_eq, 0)) AS f11_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 12, f.forecast_qty_eq, 0)) AS f12_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 13, f.forecast_qty_eq, 0)) AS f13_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 14, f.forecast_qty_eq, 0)) AS f14_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 15, f.forecast_qty_eq, 0)) AS f15_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 16, f.forecast_qty_eq, 0)) AS f16_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 17, f.forecast_qty_eq, 0)) AS f17_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 18, f.forecast_qty_eq, 0)) AS f18_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 19, f.forecast_qty_eq, 0)) AS f19_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 20, f.forecast_qty_eq, 0)) AS f20_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 21, f.forecast_qty_eq, 0)) AS f21_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 22, f.forecast_qty_eq, 0)) AS f22_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 23, f.forecast_qty_eq, 0)) AS f23_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 24, f.forecast_qty_eq, 0)) AS f24_qty_eq,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 1, f.forecast_value_eur, 0)) AS f01_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 2, f.forecast_value_eur, 0)) AS f02_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 3, f.forecast_value_eur, 0)) AS f03_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 4, f.forecast_value_eur, 0)) AS f04_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 5, f.forecast_value_eur, 0)) AS f05_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 6, f.forecast_value_eur, 0)) AS f06_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 7, f.forecast_value_eur, 0)) AS f07_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 8, f.forecast_value_eur, 0)) AS f08_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 9, f.forecast_value_eur, 0)) AS f09_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 10, f.forecast_value_eur, 0)) AS f10_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 11, f.forecast_value_eur, 0)) AS f11_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 12, f.forecast_value_eur, 0)) AS f12_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 13, f.forecast_value_eur, 0)) AS f13_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 14, f.forecast_value_eur, 0)) AS f14_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 15, f.forecast_value_eur, 0)) AS f15_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 16, f.forecast_value_eur, 0)) AS f16_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 17, f.forecast_value_eur, 0)) AS f17_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 18, f.forecast_value_eur, 0)) AS f18_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 19, f.forecast_value_eur, 0)) AS f19_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 20, f.forecast_value_eur, 0)) AS f20_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 21, f.forecast_value_eur, 0)) AS f21_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 22, f.forecast_value_eur, 0)) AS f22_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 23, f.forecast_value_eur, 0)) AS f23_value,
       SUM(IFF(DATEDIFF(month, v.m, f.forecast_month) = 24, f.forecast_value_eur, 0)) AS f24_value
FROM v
JOIN LINKML_METRICS.RAW.FCT_FORECAST f
  ON f.forecast_month >= DATEADD(month, 1, v.m) AND f.forecast_month <= DATEADD(month, 24, v.m)
CROSS JOIN st
GROUP BY v.m, f.item_id, f.country_id, st.batch_status;
