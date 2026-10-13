-- GENERATED from contract/stock_coverage.yaml (contract stock_coverage, version 0.5.1)
-- by compiler/gen_closing_procedure.py. Do not edit: change the contract and run
-- `python compiler/gen_closing_procedure.py`. tests/test_generated.py regenerates this file and fails on any difference.
--
-- LINKML_METRICS.RAW.CLOSING_STOCK: closing stock (CLOSING_STOCK, LAST_PERIOD, member set ANY_SNAPSHOT_IN_PERIOD, missing value 0) at question time,
-- from FCT_STOCK_SNAPSHOT and its dimensions only; refusals, warnings and the query ids of its statements as one JSON answer.
-- Parameters (lists and maps are JSON strings):
--   periods: JSON array of periods, each a year (YYYY), a quarter (YYYY-Qn), a month (YYYY-MM-01), a range of months (YYYY-MM-01/YYYY-MM-01) or LATEST. Several periods give a series, never a total across periods.
--   grain: JSON array of attributes to break the closing stock down by, at least one.
--   filters: JSON object, attribute to list of values. "{}" for no filter.
--   basis: NATIVE (one item per row), QTY_EQ (kg or L equivalent, one dimension per row, the default) or VALUE (EUR). A basis the rows returned cannot sum is refused with the bases allowed.
--   totals: JSON array of coarser grains, each a subset of grain; [] for none, [[]] for a grand total. Each total is recomputed from the stock rows, never added from the rows returned.
-- Refusal codes, in check order: AS_OF_MISSING, AS_OF_INVALID, AS_OF_NOT_MONTH_START, AS_OF_TOO_MANY, AS_OF_NO_SNAPSHOT, BASIS_UNKNOWN, GRAIN_MALFORMED, GRAIN_EMPTY, GRAIN_DUPLICATE, FILTERS_MALFORMED, FILTER_VALUES_INVALID, ATTRIBUTE_UNKNOWN, ATTRIBUTE_UNCLASSIFIED, ATTRIBUTE_NOT_APPLICABLE, TOTALS_MALFORMED, TOTALS_NOT_SUBSET, MASTER_DATA_FANOUT, DATA_QUALITY_FAILED, BASIS_NOT_COMPARABLE.
--
-- Run as LINKML_METRICS_ROLE with no secondary role:
--   snow sql -c <connection> -f <this file>
USE SECONDARY ROLES NONE;
USE ROLE LINKML_METRICS_ROLE;

CREATE OR REPLACE PROCEDURE LINKML_METRICS.RAW.CLOSING_STOCK(
    PERIODS VARCHAR,
    GRAIN VARCHAR,
    FILTERS VARCHAR,
    BASIS VARCHAR DEFAULT 'QTY_EQ',
    TOTALS VARCHAR DEFAULT '[]')
RETURNS VARIANT
LANGUAGE SQL
COMMENT = 'Generated from contract stock_coverage 0.5.1 by compiler/gen_closing_procedure.py (SQL Scripting)'
EXECUTE AS CALLER
AS
$$
-- Generated from the contract by compiler/gen_closing_procedure.py. Three statements: the parameters (no table read),
-- the context, the closing rows; values are bound, no SQL text is built at call time.
DECLARE
  refused EXCEPTION (-20001, 'closing stock request refused');
  t0 TIMESTAMP_LTZ;
  t1 TIMESTAMP_LTZ;
  t2 TIMESTAMP_LTZ;
  t3 TIMESTAMP_LTZ;
  rcode VARCHAR;
  reason VARCHAR;
  lineage OBJECT;
  par VARIANT;
  ctx VARIANT;
  cv VARIANT;
  periods_json VARCHAR;
  req VARCHAR;
BEGIN
  t0 := CURRENT_TIMESTAMP();
  BEGIN
    -- ---- 1. the parameters and the caller, reading no table
    SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) INTO :par FROM (
WITH b AS (
    SELECT :PERIODS AS periods_raw, :GRAIN AS grain_raw, :FILTERS AS filters_raw, :BASIS AS basis_raw,
           :TOTALS AS totals_raw
),
s1 AS (
    SELECT b.*,
           TRIM(COALESCE(periods_raw, ''), ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) AS p_s,
           p_s IN ('', '[]', 'null') AS p_missing0,
           LEFT(p_s, 1) IN ('[', '{') AS p_is_json,
           IFF(p_is_json, TRY_PARSE_JSON(p_s, 'd'), NULL) AS p_j,
           p_is_json AND NOT COALESCE(IS_ARRAY(p_j), FALSE) AS p_bad_json,
           CASE WHEN p_missing0 OR p_bad_json THEN ARRAY_CONSTRUCT()
                WHEN p_is_json THEN p_j::ARRAY
                ELSE SPLIT(p_s, ',') END AS p_items,
           REGEXP_REPLACE(UPPER(TRIM(COALESCE(basis_raw, ''), ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), '[\\s-]+', '_') AS ukey,
           IFF(basis_raw IS NULL OR TRIM(basis_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), 'QTY_EQ', CASE ukey WHEN 'ITEM_UNIT' THEN 'NATIVE' WHEN 'NATIVE' THEN 'NATIVE' WHEN 'OWN_UNIT' THEN 'NATIVE' WHEN 'PACKS' THEN 'NATIVE' WHEN 'QTY_RAW' THEN 'NATIVE' WHEN 'RAW' THEN 'NATIVE' WHEN 'RAW_UNIT' THEN 'NATIVE' WHEN 'RAW_UNITS' THEN 'NATIVE' WHEN 'UNITS' THEN 'NATIVE' WHEN 'KG' THEN 'QTY_EQ' WHEN 'KILOS' THEN 'QTY_EQ' WHEN 'L' THEN 'QTY_EQ' WHEN 'LITRES' THEN 'QTY_EQ' WHEN 'QTY_EQ' THEN 'QTY_EQ' WHEN 'QUANTITY' THEN 'QTY_EQ' WHEN 'QUANTITY_EQUIVALENT' THEN 'QTY_EQ' WHEN 'VOLUME' THEN 'QTY_EQ' WHEN 'EUR' THEN 'VALUE' WHEN 'EUROS' THEN 'VALUE' WHEN 'MONEY' THEN 'VALUE' WHEN 'VALUE' THEN 'VALUE' ELSE NULL END) AS basis,
           TRIM(grain_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) AS g_s,
           grain_raw IS NOT NULL AND g_s <> '' AND LEFT(g_s, 1) IN ('[', '{') AND NOT COALESCE(IS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), FALSE) AS g_bad_json,
           CASE WHEN grain_raw IS NULL OR g_s = '' THEN ARRAY_CONSTRUCT()
                WHEN LEFT(g_s, 1) IN ('[', '{') THEN COALESCE(AS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), ARRAY_CONSTRUCT())
                ELSE FILTER(TRANSFORM(SPLIT(g_s, ','), x -> TRIM(x::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))::VARIANT), x -> x::VARCHAR <> '') END AS g_items,
           COALESCE(g_bad_json, FALSE) OR ARRAY_SIZE(FILTER(g_items, x -> TYPEOF(x) <> 'VARCHAR')) > 0 AS grain_malformed,
           TRANSFORM(FILTER(g_items, x -> TYPEOF(x) = 'VARCHAR'), x -> LOWER(TRIM(x::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)))::VARIANT) AS grain,
           ARRAY_DISTINCT(ARRAY_EXCEPT(grain, ARRAY_DISTINCT(grain))) AS grain_dups,
           TRIM(IFF(filters_raw IS NULL OR TRIM(filters_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), '{}', filters_raw), ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) AS f_s,
           IFF(LEFT(f_s, 1) IN ('[', '{'), TRY_PARSE_JSON(f_s, 'd'), NULL) AS f_json,
           f_json IS NULL OR NOT IS_OBJECT(f_json) AS filters_malformed,
           TRIM(IFF(totals_raw IS NULL OR TRIM(totals_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), '[]', totals_raw), ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) AS t_s,
           IFF(LEFT(t_s, 1) = '[', TRY_PARSE_JSON(t_s, 'd'), NULL) AS t_json,
           t_json IS NULL OR NOT IS_ARRAY(t_json)
             OR ARRAY_SIZE(FILTER(COALESCE(AS_ARRAY(t_json), ARRAY_CONSTRUCT()), e -> NOT IS_ARRAY(e)
                  OR ARRAY_SIZE(FILTER(COALESCE(AS_ARRAY(e), ARRAY_CONSTRUCT()), z -> TYPEOF(z) <> 'VARCHAR')) > 0)) > 0 AS totals_malformed,
           TRANSFORM(COALESCE(AS_ARRAY(t_json), ARRAY_CONSTRUCT()),
                     e -> TRANSFORM(COALESCE(AS_ARRAY(e), ARRAY_CONSTRUCT()), z -> LOWER(TRIM(z::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)))::VARIANT)::VARIANT) AS totals_all,
           TRANSFORM(FILTER(ARRAY_GENERATE_RANGE(0, ARRAY_SIZE(totals_all)), i -> ARRAY_POSITION(GET(totals_all, i::INT), totals_all) = i::INT), i -> GET(totals_all, i::INT)) AS totals
    FROM b
),
pr AS (
    SELECT f.index AS i, TYPEOF(f.value) AS ty,
           IFF(ty IN ('VARCHAR', 'INTEGER'), TRIM(f.value::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)), TO_JSON(f.value)) AS shown,
           IFF(ty IN ('VARCHAR', 'INTEGER'), REGEXP_REPLACE(UPPER(shown), '\\s+', ''), NULL) AS tok,
           CASE WHEN tok = 'LATEST' THEN 'LATEST'
                WHEN REGEXP_LIKE(tok, '\\d{4}') THEN 'YEAR'
                WHEN REGEXP_LIKE(tok, '(\\d{4}-?Q[1-4]|Q[1-4]-?\\d{4})') THEN 'QUARTER'
                WHEN REGEXP_LIKE(tok, '\\d{4}-\\d{2}-\\d{2}(/\\d{4}-\\d{2}-\\d{2})?') THEN 'PERIOD_RANGE' END AS kind,
           TRY_TO_DATE(SPLIT_PART(tok, '/', 1), 'YYYY-MM-DD') AS d1,
           TRY_TO_DATE(IFF(CONTAINS(tok, '/'), SPLIT_PART(tok, '/', 2), tok), 'YYYY-MM-DD') AS d2,
           TRY_TO_NUMBER(COALESCE(REGEXP_SUBSTR(tok, '^(\\d{4})-?Q', 1, 1, 'e', 1), REGEXP_SUBSTR(tok, 'Q[1-4]-?(\\d{4})$', 1, 1, 'e', 1),
                                  REGEXP_SUBSTR(tok, '^\\d{4}'))) AS y,
           TRY_TO_NUMBER(REGEXP_SUBSTR(tok, 'Q([1-4])', 1, 1, 'e', 1)) AS qn,
           kind IS NULL OR (kind = 'PERIOD_RANGE' AND (d1 IS NULL OR d2 IS NULL OR d1 > d2)) AS invalid,
           NOT invalid AND kind = 'PERIOD_RANGE' AND (DAY(d1) <> 1 OR DAY(d2) <> 1) AS not_start,
           IFF(DAY(d1) <> 1, TO_VARCHAR(d1), TO_VARCHAR(d2)) AS bad_day,
           CASE kind WHEN 'YEAR' THEN DATE_FROM_PARTS(y, 1, 1) WHEN 'QUARTER' THEN DATE_FROM_PARTS(y, 3 * qn - 2, 1)
                     WHEN 'PERIOD_RANGE' THEN d1 END AS first_month,
           CASE kind WHEN 'YEAR' THEN DATE_FROM_PARTS(y, 12, 1) WHEN 'QUARTER' THEN DATE_FROM_PARTS(y, 3 * qn, 1)
                     WHEN 'PERIOD_RANGE' THEN d2 END AS last_month,
           CASE kind WHEN 'YEAR' THEN y::VARCHAR WHEN 'QUARTER' THEN y::VARCHAR || '-Q' || qn::VARCHAR
                     WHEN 'PERIOD_RANGE' THEN IFF(d1 = d2, TO_VARCHAR(d1), TO_VARCHAR(d1) || '/' || TO_VARCHAR(d2))
                     ELSE kind END AS label
    FROM s1, TABLE(FLATTEN(INPUT => s1.p_items)) f
),
pv AS (SELECT * FROM pr WHERE NOT invalid AND NOT not_start QUALIFY ROW_NUMBER() OVER (PARTITION BY label ORDER BY i) = 1),
fl AS (
    SELECT LOWER(TRIM(f.key, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) AS k, f.value AS v,
           IFF(TYPEOF(v) IN ('VARCHAR', 'INTEGER', 'DECIMAL', 'DOUBLE'), ARRAY_CONSTRUCT(v), AS_ARRAY(v)) AS vv,
           vv IS NULL OR ARRAY_SIZE(vv) = 0
             OR ARRAY_SIZE(FILTER(vv, e -> TYPEOF(e) IN ('NULL_VALUE', 'ARRAY', 'OBJECT', 'BOOLEAN'))) > 0 AS bad,
           CASE k WHEN 'sku_code' THEN 0 WHEN 'family_code' THEN 1 WHEN 'range_code' THEN 2 WHEN 'lifecycle_status' THEN 3 WHEN 'dimension' THEN 4 WHEN 'country_code' THEN 5 WHEN 'region_code' THEN 6 WHEN 'batch_status' THEN 7 WHEN 'expiry_bucket' THEN 8 WHEN 'warehouse_code' THEN 9 WHEN 'warehouse_type' THEN 10 WHEN 'item_type' THEN 11 ELSE 12 END AS rk
    FROM s1, TABLE(FLATTEN(INPUT => IFF(IS_OBJECT(s1.f_json), s1.f_json, OBJECT_CONSTRUCT()))) f
    QUALIFY ROW_NUMBER() OVER (PARTITION BY LOWER(TRIM(f.key, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) ORDER BY f.key DESC) = 1
),
fa AS (
    SELECT COALESCE(ARRAY_AGG(k) WITHIN GROUP (ORDER BY rk, k), ARRAY_CONSTRUCT()) AS fkeys,
           GET(ARRAY_AGG(IFF(bad, k, NULL)) WITHIN GROUP (ORDER BY rk, k), 0)::VARCHAR AS bad_filter,
           COALESCE(OBJECT_AGG(k, IFF(bad, NULL, TRANSFORM(vv, e -> e::VARCHAR::VARIANT))::VARIANT), OBJECT_CONSTRUCT()) AS filters
    FROM fl
),
s2 AS (
    SELECT s1.*, fa.*,
           p_missing0 OR (NOT p_bad_json AND ARRAY_SIZE(p_items) = 0) AS p_missing,
           IFF(p_bad_json, periods_raw, (SELECT MIN_BY(shown, i) FROM pr WHERE invalid)) AS p_invalid,
           (SELECT MIN_BY(bad_day, i) FROM pr WHERE not_start) AS p_not_start,
           (SELECT COUNT(*) FROM pv) AS p_count,
           ARRAY_DISTINCT(ARRAY_CAT(grain, fkeys)) AS names,
           ARRAY_CAT(FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'), x -> ARRAY_CONTAINS(x, names)), ARRAY_SORT(FILTER(names, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'))))) AS ranked,
           GET(FILTER(ranked, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'))), 0)::VARCHAR AS unknown_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS unclassified_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS not_applicable_attribute,
           GET(FILTER(totals, x -> ARRAY_SIZE(ARRAY_DISTINCT(x::ARRAY)) <> ARRAY_SIZE(x::ARRAY)
                      OR ARRAY_SIZE(ARRAY_EXCEPT(x::ARRAY, grain)) > 0 OR ARRAY_SIZE(x::ARRAY) >= ARRAY_SIZE(grain)), 0)::ARRAY AS bad_total
    FROM s1, fa
)
SELECT CURRENT_ROLE() AS CALLER_ROLE, CURRENT_SECONDARY_ROLES() AS CALLER_SECONDARY_ROLES, CURRENT_USER() AS CALLER_USER, SYS_CONTEXT('SNOWFLAKE$CURRENT', 'IS_AGENT_ACTIVATED')::VARCHAR AS AGENT_ACTIVATED,
       CASE WHEN p_missing THEN 'AS_OF_MISSING' WHEN p_invalid IS NOT NULL THEN 'AS_OF_INVALID' WHEN p_not_start IS NOT NULL THEN 'AS_OF_NOT_MONTH_START' WHEN p_count > 24 THEN 'AS_OF_TOO_MANY' END AS P_RCODE,
       CASE WHEN p_missing THEN 'A period is required: a year (YYYY), a quarter (YYYY-Qn), a month (YYYY-MM-01), a range of months (YYYY-MM-01/YYYY-MM-01) or LATEST. Closing stock is the snapshot of the period''s last month; it is never summed or averaged over the months of the period.' WHEN p_invalid IS NOT NULL THEN 'period ''' || (p_invalid) || ''' is not a year (YYYY), a quarter (YYYY-Qn), a month (YYYY-MM-01), a range of months (YYYY-MM-01/YYYY-MM-01) or LATEST (a range starts with its first month).' WHEN p_not_start IS NOT NULL THEN '''' || (p_not_start) || ''' is not the first day of a month. Closing stock is monthly: use ' || (TO_VARCHAR(DATE_TRUNC('month', TO_DATE(p_not_start)))) || ' for that month.' WHEN p_count > 24 THEN 'At most ' || ('24') || ' periods per call.' END AS P_REASON,
       CASE WHEN basis IS NULL THEN 'BASIS_UNKNOWN' WHEN grain_malformed THEN 'GRAIN_MALFORMED' WHEN ARRAY_SIZE(grain) = 0 THEN 'GRAIN_EMPTY' WHEN ARRAY_SIZE(grain_dups) > 0 THEN 'GRAIN_DUPLICATE' WHEN filters_malformed THEN 'FILTERS_MALFORMED' WHEN bad_filter IS NOT NULL THEN 'FILTER_VALUES_INVALID' WHEN unknown_attribute IS NOT NULL THEN 'ATTRIBUTE_UNKNOWN' WHEN unclassified_attribute IS NOT NULL THEN 'ATTRIBUTE_UNCLASSIFIED' WHEN not_applicable_attribute IS NOT NULL THEN 'ATTRIBUTE_NOT_APPLICABLE' WHEN totals_malformed THEN 'TOTALS_MALFORMED' WHEN bad_total IS NOT NULL THEN 'TOTALS_NOT_SUBSET' END AS Q_RCODE,
       CASE WHEN basis IS NULL THEN 'basis ''' || (basis_raw) || ''' is not one of NATIVE, QTY_EQ, VALUE.' WHEN grain_malformed THEN 'grain must be a JSON array of attribute names.' WHEN ARRAY_SIZE(grain) = 0 THEN 'grain must name at least one attribute (for example sku_code, country_code).' WHEN ARRAY_SIZE(grain_dups) > 0 THEN 'grain lists an attribute twice: ' || (ARRAY_TO_STRING(grain_dups, ', ')) || '.' WHEN filters_malformed THEN 'filters must be a JSON object: attribute -> list of values.' WHEN bad_filter IS NOT NULL THEN 'filter ''' || (bad_filter) || ''' needs a non-empty list of values.' WHEN unknown_attribute IS NOT NULL THEN '''' || (unknown_attribute) || ''' is not a closing stock attribute. Conformed: ' || ('sku_code, family_code, range_code, lifecycle_status, dimension, country_code, region_code') || '. Stock-only: ' || ('batch_status, expiry_bucket, warehouse_code, warehouse_type, item_type') || '.' WHEN unclassified_attribute IS NOT NULL THEN '''' || (unclassified_attribute) || ''' has no declared applicability class, so it cannot be used with closing stock.' WHEN not_applicable_attribute IS NOT NULL THEN '''' || (not_applicable_attribute) || ''' does not apply to closing stock: ' || (CASE not_applicable_attribute WHEN 'sku_code' THEN '' WHEN 'family_code' THEN '' WHEN 'range_code' THEN '' WHEN 'lifecycle_status' THEN 'An item attribute, so the forecast carries it too (decision 6, session 4). Trap T7 duplicates exactly this column: QE_ITEM_GRAIN refuses a query that uses it while an item has two values.' WHEN 'dimension' THEN 'The physical dimension in which the item is counted, with its base unit: MASS (kg) or VOLUME (L). Grouping or filtering by it keeps quantity-equivalent rows within one dimension.' WHEN 'country_code' THEN 'ISO 3166-1 alpha-2 code.' WHEN 'region_code' THEN '' WHEN 'batch_status' THEN '' WHEN 'expiry_bucket' THEN '' WHEN 'warehouse_code' THEN '' WHEN 'warehouse_type' THEN '' WHEN 'item_type' THEN 'Snapshot-only by decision: BULK items carry stock but never a forecast. Default scope STANDARD for stock coverage only (SCOPE_ITEM_TYPE, decision 5); closing stock counts every item type.' ELSE '' END) || '.' WHEN totals_malformed THEN 'totals must be a JSON array of attribute arrays, for example [["country_code"], []].' WHEN bad_total IS NOT NULL THEN 'Total ' || (ARRAY_TO_STRING(bad_total, ', ')) || ' is not a subset of the grain ' || (ARRAY_TO_STRING(grain, ', ')) || ': a total can only be coarser than the rows.' END AS Q_REASON,
       (SELECT ARRAY_AGG(OBJECT_CONSTRUCT('period', label, 'kind', kind, 'first_month', TO_VARCHAR(first_month),
                                          'last_month', TO_VARCHAR(last_month))) WITHIN GROUP (ORDER BY i) FROM pv) AS PERIODS,
       basis AS BASIS, grain AS GRAIN, filters AS FILTERS, totals AS TOTALS,
       ARRAY_PREPEND(totals, grain) AS GRAINS,
       FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'), x -> ARRAY_CONTAINS(x, names)) AS USED
FROM s2
    );
    IF (par:P_RCODE::VARCHAR IS NOT NULL) THEN
      rcode := par:P_RCODE::VARCHAR;
      reason := par:P_REASON::VARCHAR;
      RAISE refused;
    END IF;
    periods_json := TO_JSON(par:PERIODS);
    -- ---- 2. the context: snapshot months, every month of every period, table-scope quality expectations
    t1 := CURRENT_TIMESTAMP();
    SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) INTO :ctx FROM (
WITH snaps AS (SELECT DISTINCT snapshot_month AS m FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT),
cx AS (
    SELECT (SELECT ARRAY_AGG(TO_VARCHAR(m)) WITHIN GROUP (ORDER BY m) FROM snaps) AS SNAPSHOTS,
           (SELECT TO_VARCHAR(MAX(m)) FROM snaps) AS LATEST,
           (SELECT COUNT(*) - COUNT(DISTINCT country_id) FROM LINKML_METRICS.RAW.DIM_GEO) AS QE_GEO_GRAIN,
           (SELECT COUNT(*) - COUNT(DISTINCT batch_id) FROM LINKML_METRICS.RAW.DIM_BATCH) AS QE_BATCH_GRAIN,
           (SELECT COUNT(*) - COUNT(DISTINCT warehouse_id) FROM LINKML_METRICS.RAW.DIM_WAREHOUSE) AS QE_WAREHOUSE_GRAIN,
           ((SELECT COUNT(*) FROM (SELECT sku_code FROM LINKML_METRICS.RAW.DIM_ITEM GROUP BY sku_code HAVING COUNT(DISTINCT family_code) > 1)) + (SELECT COUNT(*) FROM (SELECT family_code FROM LINKML_METRICS.RAW.DIM_ITEM GROUP BY family_code HAVING COUNT(DISTINCT range_code) > 1))) AS QE_SKU_FAMILY,
           ((SELECT COUNT(*) FROM (SELECT country_code FROM LINKML_METRICS.RAW.DIM_GEO GROUP BY country_code HAVING COUNT(DISTINCT region_code) > 1))) AS QE_COUNTRY_REGION
),
pp AS (
    SELECT f.index AS i, f.value:period::VARCHAR AS label, f.value:kind::VARCHAR AS kind,
           IFF(kind = 'LATEST', TO_DATE(cx.LATEST), f.value:first_month::DATE) AS first_month,
           IFF(kind = 'LATEST', TO_DATE(cx.LATEST), f.value:last_month::DATE) AS last_month
    FROM cx, TABLE(FLATTEN(INPUT => PARSE_JSON(:periods_json))) f
),
mm AS (
    SELECT pp.i, pp.label, IFF(pp.first_month IS NULL, NULL, DATEADD(month, g.k, pp.first_month)) AS m
    FROM pp JOIN (SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1 AS k FROM TABLE(GENERATOR(ROWCOUNT => 1200))) g
      ON g.k <= COALESCE(DATEDIFF(month, pp.first_month, pp.last_month), 0)
),
miss AS (
    SELECT mm.i, ANY_VALUE(mm.label) AS label,
           ARRAY_AGG(COALESCE(TO_VARCHAR(mm.m), mm.label)) WITHIN GROUP (ORDER BY mm.m) AS months
    FROM mm, cx
    WHERE mm.m IS NULL OR NOT ARRAY_CONTAINS(TO_VARCHAR(mm.m)::VARIANT, COALESCE(cx.SNAPSHOTS, ARRAY_CONSTRUCT()))
    GROUP BY mm.i
),
bad AS (SELECT * FROM miss ORDER BY i LIMIT 1)
SELECT GET(cx.SNAPSHOTS, 0)::VARCHAR AS AVAILABLE_FIRST, cx.LATEST AS AVAILABLE_LATEST,
       IFF(bad.i IS NOT NULL, 'AS_OF_NO_SNAPSHOT', NULL) AS RCODE,
       IFF(bad.i IS NOT NULL, 'There is no stock snapshot for ' || (ARRAY_TO_STRING(bad.months, ', ') || ' (period ' || bad.label || ')') || '. Available months: ' || (ARRAY_TO_STRING(COALESCE(cx.SNAPSHOTS, ARRAY_CONSTRUCT()), ', ')) || ' (LATEST = ' || (COALESCE(cx.LATEST, 'none')) || ').', NULL) AS REASON,
       CASE WHEN COALESCE(cx.QE_GEO_GRAIN, 0) <> 0 THEN 'Quality expectation ' || ('QE_GEO_GRAIN') || ' fails (' || (cx.QE_GEO_GRAIN::VARCHAR) || ' violations): ' || ('one row per country_id') || '. No number is returned until it is fixed.' WHEN COALESCE(cx.QE_BATCH_GRAIN, 0) <> 0 THEN 'Quality expectation ' || ('QE_BATCH_GRAIN') || ' fails (' || (cx.QE_BATCH_GRAIN::VARCHAR) || ' violations): ' || ('one row per batch_id') || '. No number is returned until it is fixed.' WHEN COALESCE(cx.QE_WAREHOUSE_GRAIN, 0) <> 0 THEN 'Quality expectation ' || ('QE_WAREHOUSE_GRAIN') || ' fails (' || (cx.QE_WAREHOUSE_GRAIN::VARCHAR) || ' violations): ' || ('one row per warehouse_id') || '. No number is returned until it is fixed.' WHEN COALESCE(cx.QE_SKU_FAMILY, 0) <> 0 THEN 'Quality expectation ' || ('QE_SKU_FAMILY') || ' fails (' || (cx.QE_SKU_FAMILY::VARCHAR) || ' violations): ' || ('each sku_code maps to one family_code and each family_code to one range_code') || '. No number is returned until it is fixed.' WHEN COALESCE(cx.QE_COUNTRY_REGION, 0) <> 0 THEN 'Quality expectation ' || ('QE_COUNTRY_REGION') || ' fails (' || (cx.QE_COUNTRY_REGION::VARCHAR) || ' violations): ' || ('each country_code maps to one region_code') || '. No number is returned until it is fixed.' END AS DQ_REASON,
       (SELECT ARRAY_AGG(OBJECT_CONSTRUCT('period', label, 'kind', kind, 'first_month', TO_VARCHAR(first_month),
                                          'last_month', TO_VARCHAR(last_month))) WITHIN GROUP (ORDER BY i) FROM pp) AS PERIODS
FROM cx LEFT JOIN bad ON TRUE
    );
    lineage := OBJECT_CONSTRUCT('context', SQLID);
    t2 := CURRENT_TIMESTAMP();
    IF (ctx:RCODE::VARCHAR IS NOT NULL) THEN
      rcode := ctx:RCODE::VARCHAR;
      reason := ctx:REASON::VARCHAR;
      RAISE refused;
    END IF;
    IF (par:Q_RCODE::VARCHAR IS NOT NULL) THEN
      rcode := par:Q_RCODE::VARCHAR;
      reason := par:Q_REASON::VARCHAR;
      RAISE refused;
    END IF;
    req := TO_JSON(OBJECT_CONSTRUCT('periods', ctx:PERIODS, 'basis', par:BASIS, 'grain', par:GRAIN, 'grains', par:GRAINS,
                                    'filters', par:FILTERS, 'used', par:USED));
    -- ---- 3. the closing rows and the request-scoped quality checks
    SELECT CV INTO :cv FROM (
WITH rq AS (SELECT PARSE_JSON(:req) AS r),
periods AS (
    SELECT f.index AS p_idx, f.value:period::VARCHAR AS period, f.value:kind::VARCHAR AS kind,
           f.value:first_month::DATE AS first_month, f.value:last_month::DATE AS last_month
    FROM rq, TABLE(FLATTEN(INPUT => rq.r:periods)) f
),
grain_sets AS (SELECT f.index AS g_idx, f.value::ARRAY AS gs FROM rq, TABLE(FLATTEN(INPUT => rq.r:grains)) f),
analysis_months AS (
    SELECT DISTINCT DATEADD(month, g.k, p.first_month) AS as_of_month
    FROM periods p JOIN (SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1 AS k FROM TABLE(GENERATOR(ROWCOUNT => 1200))) g
      ON g.k <= DATEDIFF(month, p.first_month, p.last_month)
),
item AS (
    SELECT item_id,
           MIN(sku_code) AS sku_code,
           MIN(family_code) AS family_code,
           MIN(range_code) AS range_code,
           MIN(lifecycle_status) AS lifecycle_status,
           MIN(dimension) AS dimension,
           MIN(item_type) AS item_type,
           MIN(base_unit) AS base_unit,
           MIN(raw_unit) AS raw_unit
    FROM LINKML_METRICS.RAW.DIM_ITEM GROUP BY item_id
),
base AS (
    SELECT p.p_idx, p.last_month, s.snapshot_month, s.item_id, (CASE rq.r:basis::VARCHAR WHEN 'QTY_EQ' THEN s.stock_qty_eq WHEN 'VALUE' THEN s.stock_value_eur WHEN 'NATIVE' THEN s.stock_qty_raw END) AS qty,
           geo.country_code AS country_code,
           geo.region_code AS region_code,
           batch.batch_status AS batch_status,
           s.expiry_bucket AS expiry_bucket,
           warehouse.warehouse_code AS warehouse_code,
           warehouse.warehouse_type AS warehouse_type
    FROM rq
    JOIN periods p ON TRUE
    JOIN LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT s ON s.snapshot_month BETWEEN p.first_month AND p.last_month
    LEFT JOIN LINKML_METRICS.RAW.DIM_GEO geo ON geo.country_id = s.country_id
    LEFT JOIN LINKML_METRICS.RAW.DIM_BATCH batch ON batch.batch_id = s.batch_id
    LEFT JOIN LINKML_METRICS.RAW.DIM_WAREHOUSE warehouse ON warehouse.warehouse_id = s.warehouse_id
    WHERE (NOT (ARRAY_CONTAINS('country_code'::VARIANT, rq.r:used::ARRAY) OR ARRAY_CONTAINS('region_code'::VARIANT, rq.r:used::ARRAY)) OR geo.country_id IS NOT NULL)
      AND (NOT (ARRAY_CONTAINS('batch_status'::VARIANT, rq.r:used::ARRAY)) OR batch.batch_id IS NOT NULL)
      AND (NOT (ARRAY_CONTAINS('warehouse_code'::VARIANT, rq.r:used::ARRAY) OR ARRAY_CONTAINS('warehouse_type'::VARIANT, rq.r:used::ARRAY)) OR warehouse.warehouse_id IS NOT NULL)
      AND (rq.r:filters:"country_code" IS NULL OR ARRAY_CONTAINS((geo.country_code)::VARIANT, rq.r:filters:"country_code"::ARRAY))
      AND (rq.r:filters:"region_code" IS NULL OR ARRAY_CONTAINS((geo.region_code)::VARIANT, rq.r:filters:"region_code"::ARRAY))
      AND (rq.r:filters:"batch_status" IS NULL OR ARRAY_CONTAINS((batch.batch_status)::VARIANT, rq.r:filters:"batch_status"::ARRAY))
      AND (rq.r:filters:"expiry_bucket" IS NULL OR ARRAY_CONTAINS((s.expiry_bucket)::VARIANT, rq.r:filters:"expiry_bucket"::ARRAY))
      AND (rq.r:filters:"warehouse_code" IS NULL OR ARRAY_CONTAINS((warehouse.warehouse_code)::VARIANT, rq.r:filters:"warehouse_code"::ARRAY))
      AND (rq.r:filters:"warehouse_type" IS NULL OR ARRAY_CONTAINS((warehouse.warehouse_type)::VARIANT, rq.r:filters:"warehouse_type"::ARRAY))
),
scope_items AS (
    SELECT DISTINCT base.item_id FROM base
    WHERE base.item_id IN (SELECT d.item_id FROM LINKML_METRICS.RAW.DIM_ITEM d, rq WHERE (rq.r:filters:"sku_code" IS NULL OR ARRAY_CONTAINS((d.sku_code)::VARIANT, rq.r:filters:"sku_code"::ARRAY)) AND (rq.r:filters:"family_code" IS NULL OR ARRAY_CONTAINS((d.family_code)::VARIANT, rq.r:filters:"family_code"::ARRAY)) AND (rq.r:filters:"range_code" IS NULL OR ARRAY_CONTAINS((d.range_code)::VARIANT, rq.r:filters:"range_code"::ARRAY)) AND (rq.r:filters:"lifecycle_status" IS NULL OR ARRAY_CONTAINS((d.lifecycle_status)::VARIANT, rq.r:filters:"lifecycle_status"::ARRAY)) AND (rq.r:filters:"dimension" IS NULL OR ARRAY_CONTAINS((d.dimension)::VARIANT, rq.r:filters:"dimension"::ARRAY)) AND (rq.r:filters:"item_type" IS NULL OR ARRAY_CONTAINS((d.item_type)::VARIANT, rq.r:filters:"item_type"::ARRAY)))
),
stock_rows AS (
    SELECT base.*, item.sku_code AS sku_code, item.family_code AS family_code, item.range_code AS range_code, item.lifecycle_status AS lifecycle_status, item.dimension AS dimension, item.item_type AS item_type,
           item.dimension AS u_dimension, item.base_unit AS u_base_unit, item.raw_unit AS u_native_unit
    FROM base JOIN rq ON TRUE
    LEFT JOIN item ON item.item_id = base.item_id
    WHERE (NOT (ARRAY_CONTAINS('sku_code'::VARIANT, rq.r:used::ARRAY) OR ARRAY_CONTAINS('family_code'::VARIANT, rq.r:used::ARRAY) OR ARRAY_CONTAINS('range_code'::VARIANT, rq.r:used::ARRAY) OR ARRAY_CONTAINS('lifecycle_status'::VARIANT, rq.r:used::ARRAY) OR ARRAY_CONTAINS('dimension'::VARIANT, rq.r:used::ARRAY) OR ARRAY_CONTAINS('item_type'::VARIANT, rq.r:used::ARRAY)) OR item.item_id IS NOT NULL)
      AND (rq.r:filters:"sku_code" IS NULL OR ARRAY_CONTAINS((item.sku_code)::VARIANT, rq.r:filters:"sku_code"::ARRAY)) AND (rq.r:filters:"family_code" IS NULL OR ARRAY_CONTAINS((item.family_code)::VARIANT, rq.r:filters:"family_code"::ARRAY)) AND (rq.r:filters:"range_code" IS NULL OR ARRAY_CONTAINS((item.range_code)::VARIANT, rq.r:filters:"range_code"::ARRAY)) AND (rq.r:filters:"lifecycle_status" IS NULL OR ARRAY_CONTAINS((item.lifecycle_status)::VARIANT, rq.r:filters:"lifecycle_status"::ARRAY)) AND (rq.r:filters:"dimension" IS NULL OR ARRAY_CONTAINS((item.dimension)::VARIANT, rq.r:filters:"dimension"::ARRAY)) AND (rq.r:filters:"item_type" IS NULL OR ARRAY_CONTAINS((item.item_type)::VARIANT, rq.r:filters:"item_type"::ARRAY))
),
grouped AS (
    SELECT r.p_idx, g.g_idx,
           IFF(ARRAY_CONTAINS('sku_code'::VARIANT, g.gs), r.sku_code, NULL) AS sku_code,
           IFF(ARRAY_CONTAINS('family_code'::VARIANT, g.gs), r.family_code, NULL) AS family_code,
           IFF(ARRAY_CONTAINS('range_code'::VARIANT, g.gs), r.range_code, NULL) AS range_code,
           IFF(ARRAY_CONTAINS('lifecycle_status'::VARIANT, g.gs), r.lifecycle_status, NULL) AS lifecycle_status,
           IFF(ARRAY_CONTAINS('dimension'::VARIANT, g.gs), r.dimension, NULL) AS dimension,
           IFF(ARRAY_CONTAINS('country_code'::VARIANT, g.gs), r.country_code, NULL) AS country_code,
           IFF(ARRAY_CONTAINS('region_code'::VARIANT, g.gs), r.region_code, NULL) AS region_code,
           IFF(ARRAY_CONTAINS('batch_status'::VARIANT, g.gs), r.batch_status, NULL) AS batch_status,
           IFF(ARRAY_CONTAINS('expiry_bucket'::VARIANT, g.gs), r.expiry_bucket, NULL) AS expiry_bucket,
           IFF(ARRAY_CONTAINS('warehouse_code'::VARIANT, g.gs), r.warehouse_code, NULL) AS warehouse_code,
           IFF(ARRAY_CONTAINS('warehouse_type'::VARIANT, g.gs), r.warehouse_type, NULL) AS warehouse_type,
           IFF(ARRAY_CONTAINS('item_type'::VARIANT, g.gs), r.item_type, NULL) AS item_type,
           SUM(IFF(r.snapshot_month = r.last_month, r.qty, 0)) AS closing_stock,
           COUNT_IF(r.snapshot_month = r.last_month) AS last_month_rows,
           COUNT(DISTINCT r.item_id) AS n_items, COUNT(DISTINCT r.u_dimension) AS n_dims,
           MIN(r.u_base_unit) AS base_unit, MIN(r.u_native_unit) AS native_unit
    FROM stock_rows r JOIN grain_sets g ON TRUE
    GROUP BY ALL
),
out0 AS (
    SELECT g.*, p.period, p.first_month, p.last_month, OBJECT_CONSTRUCT_KEEP_NULL('sku_code', sku_code, 'family_code', family_code, 'range_code', range_code, 'lifecycle_status', lifecycle_status, 'dimension', dimension, 'country_code', country_code, 'region_code', region_code, 'batch_status', batch_status, 'expiry_bucket', expiry_bucket, 'warehouse_code', warehouse_code, 'warehouse_type', warehouse_type, 'item_type', item_type) AS attrs,
           IFF(g.g_idx = 0, 'DETAIL', 'TOTAL') AS row_type,
           CASE rq.r:basis::VARCHAR WHEN 'NATIVE' THEN IFF(n_items = 1, native_unit, NULL) WHEN 'QTY_EQ' THEN IFF(n_dims = 1, base_unit, NULL) WHEN 'VALUE' THEN 'EUR' END AS stock_unit
    FROM grouped g JOIN periods p ON p.p_idx = g.p_idx JOIN rq ON TRUE
),
out AS (
    SELECT out0.*, ARRAY_TO_STRING(TRANSFORM(rq.r:grain::ARRAY, a -> COALESCE(GET(out0.attrs, a::VARCHAR)::VARCHAR, '')), '|') AS sort_key
    FROM out0 JOIN rq ON TRUE
),
agg AS (SELECT MAX(n_items) AS max_items, MAX(n_dims) AS max_dims FROM out),
dup AS (
    SELECT d.item_id, COUNT(*) AS n_rows,
           COUNT(DISTINCT d.sku_code) AS c_sku_code,
           COUNT(DISTINCT d.family_code) AS c_family_code,
           COUNT(DISTINCT d.range_code) AS c_range_code,
           COUNT(DISTINCT d.lifecycle_status) AS c_lifecycle_status,
           COUNT(DISTINCT d.dimension) AS c_dimension,
           COUNT(DISTINCT d.item_type) AS c_item_type
    FROM LINKML_METRICS.RAW.DIM_ITEM d WHERE d.item_id IN (SELECT item_id FROM scope_items) GROUP BY d.item_id HAVING COUNT(*) > 1
),
fan AS (SELECT dup.item_id, ARRAY_CONSTRUCT_COMPACT(IFF(ARRAY_CONTAINS('sku_code'::VARIANT, rq.r:used::ARRAY) AND dup.c_sku_code > 1, 'sku_code', NULL), IFF(ARRAY_CONTAINS('family_code'::VARIANT, rq.r:used::ARRAY) AND dup.c_family_code > 1, 'family_code', NULL), IFF(ARRAY_CONTAINS('range_code'::VARIANT, rq.r:used::ARRAY) AND dup.c_range_code > 1, 'range_code', NULL), IFF(ARRAY_CONTAINS('lifecycle_status'::VARIANT, rq.r:used::ARRAY) AND dup.c_lifecycle_status > 1, 'lifecycle_status', NULL), IFF(ARRAY_CONTAINS('dimension'::VARIANT, rq.r:used::ARRAY) AND dup.c_dimension > 1, 'dimension', NULL), IFF(ARRAY_CONTAINS('item_type'::VARIANT, rq.r:used::ARRAY) AND dup.c_item_type > 1, 'item_type', NULL)) AS differ FROM dup JOIN rq ON TRUE),
fan_q AS (
    SELECT (SELECT COUNT(*) FROM fan WHERE ARRAY_SIZE(differ) > 0) AS n_fan, (SELECT COUNT(*) FROM dup) AS n_dup,
           (SELECT ARRAY_AGG(DISTINCT d.sku_code) WITHIN GROUP (ORDER BY d.sku_code) FROM LINKML_METRICS.RAW.DIM_ITEM d WHERE d.item_id IN (SELECT item_id FROM fan WHERE ARRAY_CONTAINS('sku_code'::VARIANT, differ))) AS v_sku_code,
           (SELECT ARRAY_AGG(DISTINCT d.family_code) WITHIN GROUP (ORDER BY d.family_code) FROM LINKML_METRICS.RAW.DIM_ITEM d WHERE d.item_id IN (SELECT item_id FROM fan WHERE ARRAY_CONTAINS('family_code'::VARIANT, differ))) AS v_family_code,
           (SELECT ARRAY_AGG(DISTINCT d.range_code) WITHIN GROUP (ORDER BY d.range_code) FROM LINKML_METRICS.RAW.DIM_ITEM d WHERE d.item_id IN (SELECT item_id FROM fan WHERE ARRAY_CONTAINS('range_code'::VARIANT, differ))) AS v_range_code,
           (SELECT ARRAY_AGG(DISTINCT d.lifecycle_status) WITHIN GROUP (ORDER BY d.lifecycle_status) FROM LINKML_METRICS.RAW.DIM_ITEM d WHERE d.item_id IN (SELECT item_id FROM fan WHERE ARRAY_CONTAINS('lifecycle_status'::VARIANT, differ))) AS v_lifecycle_status,
           (SELECT ARRAY_AGG(DISTINCT d.dimension) WITHIN GROUP (ORDER BY d.dimension) FROM LINKML_METRICS.RAW.DIM_ITEM d WHERE d.item_id IN (SELECT item_id FROM fan WHERE ARRAY_CONTAINS('dimension'::VARIANT, differ))) AS v_dimension,
           (SELECT ARRAY_AGG(DISTINCT d.item_type) WITHIN GROUP (ORDER BY d.item_type) FROM LINKML_METRICS.RAW.DIM_ITEM d WHERE d.item_id IN (SELECT item_id FROM fan WHERE ARRAY_CONTAINS('item_type'::VARIANT, differ))) AS v_item_type
),
qr AS (
    SELECT (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT t WHERE EXISTS (SELECT 1 FROM analysis_months a WHERE a.as_of_month = t.snapshot_month)
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_ITEM r WHERE r.item_id = t.item_id)) AS QE_STOCK_ITEM_REF,
           (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT t WHERE EXISTS (SELECT 1 FROM analysis_months a WHERE a.as_of_month = t.snapshot_month)
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_BATCH r WHERE r.batch_id = t.batch_id)) AS QE_STOCK_BATCH_REF,
           (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT t WHERE EXISTS (SELECT 1 FROM analysis_months a WHERE a.as_of_month = t.snapshot_month)
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_WAREHOUSE r WHERE r.warehouse_id = t.warehouse_id)) AS QE_STOCK_WAREHOUSE_REF,
           (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT t WHERE EXISTS (SELECT 1 FROM analysis_months a WHERE a.as_of_month = t.snapshot_month)
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_GEO r WHERE r.country_id = t.country_id)) AS QE_STOCK_GEO_REF,
           (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT t WHERE EXISTS (SELECT 1 FROM analysis_months a WHERE a.as_of_month = t.snapshot_month)
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_BATCH r WHERE r.batch_id = t.batch_id AND r.item_id = t.item_id)) AS QE_STOCK_BATCH_ITEM
)
SELECT OBJECT_CONSTRUCT_KEEP_NULL(
    'ROWS', (SELECT COALESCE(ARRAY_AGG(OBJECT_PICK(OBJECT_CONSTRUCT_KEEP_NULL(
                 'period', period, 'first_month', TO_VARCHAR(first_month), 'last_month', TO_VARCHAR(last_month),
                 'row_type', row_type, 'closing_stock', closing_stock, 'stock_unit', stock_unit,
                 'closed_without_snapshot', last_month_rows = 0, 'sku_code', sku_code, 'family_code', family_code, 'range_code', range_code, 'lifecycle_status', lifecycle_status, 'dimension', dimension, 'country_code', country_code, 'region_code', region_code, 'batch_status', batch_status, 'expiry_bucket', expiry_bucket, 'warehouse_code', warehouse_code, 'warehouse_type', warehouse_type, 'item_type', item_type),
                 ARRAY_CAT(ARRAY_CONSTRUCT('period', 'first_month', 'last_month', 'row_type', 'closing_stock', 'stock_unit',
                                           'closed_without_snapshot'), rq.r:grain::ARRAY)))
                 WITHIN GROUP (ORDER BY p_idx, g_idx, sort_key), ARRAY_CONSTRUCT()) FROM out JOIN rq ON TRUE),
    'ROW_COUNT', (SELECT COUNT(*) FROM out),
    'BASIS_REASON', (SELECT IFF((rq.r:basis::VARCHAR = 'NATIVE' AND NOT (COALESCE(agg.max_items, 0) <= 1)) OR (rq.r:basis::VARCHAR = 'QTY_EQ' AND NOT (COALESCE(agg.max_dims, 0) <= 1)), 'On ' || (rq.r:basis::VARCHAR) || ' ' || (CASE rq.r:basis::VARCHAR WHEN 'NATIVE' THEN 'at least one row or total adds several items, each counted in its own unit (packs of different sizes)' WHEN 'QTY_EQ' THEN 'at least one row or total adds kg and L (items of different dimensions)' WHEN 'VALUE' THEN 'never (a value adds up across every item)' ELSE '' END) || ', so the stock cannot be summed for this request. Bases allowed for this request: ' || (ARRAY_TO_STRING(ARRAY_CONSTRUCT_COMPACT(IFF(COALESCE(agg.max_items, 0) <= 1, 'NATIVE', NULL), IFF(COALESCE(agg.max_dims, 0) <= 1, 'QTY_EQ', NULL), IFF(TRUE, 'VALUE', NULL)), ', ')) || '.', NULL) FROM agg JOIN rq ON TRUE),
    'FANOUT_REASON', IFF(fan_q.n_fan > 0, (n_fan::VARCHAR) || ' item(s) have several rows in DIM_ITEM that differ on ' || (ARRAY_TO_STRING(ARRAY_CONSTRUCT_COMPACT(IFF(ARRAY_SIZE(v_sku_code) > 0, 'sku_code (' || ARRAY_TO_STRING(ARRAY_SLICE(v_sku_code, 0, 5), ', ') || IFF(ARRAY_SIZE(v_sku_code) > 5, ' and ' || (ARRAY_SIZE(v_sku_code) - 5)::VARCHAR || ' more', '') || ')', NULL), IFF(ARRAY_SIZE(v_family_code) > 0, 'family_code (' || ARRAY_TO_STRING(ARRAY_SLICE(v_family_code, 0, 5), ', ') || IFF(ARRAY_SIZE(v_family_code) > 5, ' and ' || (ARRAY_SIZE(v_family_code) - 5)::VARCHAR || ' more', '') || ')', NULL), IFF(ARRAY_SIZE(v_range_code) > 0, 'range_code (' || ARRAY_TO_STRING(ARRAY_SLICE(v_range_code, 0, 5), ', ') || IFF(ARRAY_SIZE(v_range_code) > 5, ' and ' || (ARRAY_SIZE(v_range_code) - 5)::VARCHAR || ' more', '') || ')', NULL), IFF(ARRAY_SIZE(v_lifecycle_status) > 0, 'lifecycle_status (' || ARRAY_TO_STRING(ARRAY_SLICE(v_lifecycle_status, 0, 5), ', ') || IFF(ARRAY_SIZE(v_lifecycle_status) > 5, ' and ' || (ARRAY_SIZE(v_lifecycle_status) - 5)::VARCHAR || ' more', '') || ')', NULL), IFF(ARRAY_SIZE(v_dimension) > 0, 'dimension (' || ARRAY_TO_STRING(ARRAY_SLICE(v_dimension, 0, 5), ', ') || IFF(ARRAY_SIZE(v_dimension) > 5, ' and ' || (ARRAY_SIZE(v_dimension) - 5)::VARCHAR || ' more', '') || ')', NULL), IFF(ARRAY_SIZE(v_item_type) > 0, 'item_type (' || ARRAY_TO_STRING(ARRAY_SLICE(v_item_type, 0, 5), ', ') || IFF(ARRAY_SIZE(v_item_type) > 5, ' and ' || (ARRAY_SIZE(v_item_type) - 5)::VARCHAR || ' more', '') || ')', NULL)), ', ')) || '; any number at this grain would be fanned out.', NULL),
    'WARNINGS', ARRAY_CONSTRUCT_COMPACT(IFF(n_fan = 0 AND n_dup > 0, OBJECT_CONSTRUCT('code', 'MASTER_DATA_DUPLICATES', 'expectation', 'QE_ITEM_GRAIN', 'count', n_dup, 'message', (n_dup::VARCHAR) || ' items have several rows in DIM_ITEM; they agree on the attributes this query uses, so the answer is not affected.'), NULL), IFF(COALESCE(qr.QE_STOCK_ITEM_REF, 0) <> 0, OBJECT_CONSTRUCT('code', 'DATA_QUALITY_ROWS', 'expectation', 'QE_STOCK_ITEM_REF', 'count', qr.QE_STOCK_ITEM_REF, 'message', ('QE_STOCK_ITEM_REF') || ': ' || (qr.QE_STOCK_ITEM_REF::VARCHAR) || ' rows read by this answer break the expectation (' || ('every stock item_id exists in DIM_ITEM') || ').'), NULL), IFF(COALESCE(qr.QE_STOCK_BATCH_REF, 0) <> 0, OBJECT_CONSTRUCT('code', 'DATA_QUALITY_ROWS', 'expectation', 'QE_STOCK_BATCH_REF', 'count', qr.QE_STOCK_BATCH_REF, 'message', ('QE_STOCK_BATCH_REF') || ': ' || (qr.QE_STOCK_BATCH_REF::VARCHAR) || ' rows read by this answer break the expectation (' || ('every stock batch_id exists in DIM_BATCH') || ').'), NULL), IFF(COALESCE(qr.QE_STOCK_WAREHOUSE_REF, 0) <> 0, OBJECT_CONSTRUCT('code', 'DATA_QUALITY_ROWS', 'expectation', 'QE_STOCK_WAREHOUSE_REF', 'count', qr.QE_STOCK_WAREHOUSE_REF, 'message', ('QE_STOCK_WAREHOUSE_REF') || ': ' || (qr.QE_STOCK_WAREHOUSE_REF::VARCHAR) || ' rows read by this answer break the expectation (' || ('every stock warehouse_id exists in DIM_WAREHOUSE') || ').'), NULL), IFF(COALESCE(qr.QE_STOCK_GEO_REF, 0) <> 0, OBJECT_CONSTRUCT('code', 'DATA_QUALITY_ROWS', 'expectation', 'QE_STOCK_GEO_REF', 'count', qr.QE_STOCK_GEO_REF, 'message', ('QE_STOCK_GEO_REF') || ': ' || (qr.QE_STOCK_GEO_REF::VARCHAR) || ' rows read by this answer break the expectation (' || ('every stock country_id exists in DIM_GEO') || ').'), NULL), IFF(COALESCE(qr.QE_STOCK_BATCH_ITEM, 0) <> 0, OBJECT_CONSTRUCT('code', 'DATA_QUALITY_ROWS', 'expectation', 'QE_STOCK_BATCH_ITEM', 'count', qr.QE_STOCK_BATCH_ITEM, 'message', ('QE_STOCK_BATCH_ITEM') || ': ' || (qr.QE_STOCK_BATCH_ITEM::VARCHAR) || ' rows read by this answer break the expectation (' || ('the denormalised item_id of a stock row equals the item_id of its batch') || ').'), NULL))
) AS CV
FROM fan_q, qr
    );
    lineage := OBJECT_INSERT(lineage, 'closing', SQLID);
    t3 := CURRENT_TIMESTAMP();
    -- ---- data checks, in check_order
    IF (cv:FANOUT_REASON::VARCHAR IS NOT NULL) THEN
      rcode := 'MASTER_DATA_FANOUT';
      reason := cv:FANOUT_REASON::VARCHAR;
      RAISE refused;
    END IF;
    IF (ctx:DQ_REASON::VARCHAR IS NOT NULL) THEN
      rcode := 'DATA_QUALITY_FAILED';
      reason := ctx:DQ_REASON::VARCHAR;
      RAISE refused;
    END IF;
    IF (cv:BASIS_REASON::VARCHAR IS NOT NULL) THEN
      rcode := 'BASIS_NOT_COMPARABLE';
      reason := cv:BASIS_REASON::VARCHAR;
      RAISE refused;
    END IF;
  EXCEPTION
    WHEN refused THEN
      RETURN OBJECT_CONSTRUCT('status', 'refused', 'contract', OBJECT_CONSTRUCT('id', 'stock_coverage', 'version', '0.5.1'), 'measure', OBJECT_CONSTRUCT('measure', 'stock_on_hand', 'period_aggregation', 'CLOSING_STOCK', 'method', 'LAST_PERIOD'),
               'refusal', OBJECT_CONSTRUCT('code', rcode, 'reason', reason), 'available_months', IFF(ctx IS NULL, NULL, OBJECT_CONSTRUCT_KEEP_NULL('first', ctx:AVAILABLE_FIRST, 'last', ctx:AVAILABLE_LATEST, 'latest', ctx:AVAILABLE_LATEST)),
               'caller', OBJECT_CONSTRUCT_KEEP_NULL('current_role', par:CALLER_ROLE, 'current_secondary_roles', par:CALLER_SECONDARY_ROLES, 'current_user', par:CALLER_USER, 'is_agent_activated', par:AGENT_ACTIVATED), 'lineage', OBJECT_CONSTRUCT('query_ids', COALESCE(lineage, OBJECT_CONSTRUCT())),
               'timing_ms', OBJECT_CONSTRUCT_KEEP_NULL('context_ms', DATEDIFF('millisecond', t1, t2),
                                                      'total_ms', DATEDIFF('millisecond', t0, CURRENT_TIMESTAMP())));
  END;
  RETURN OBJECT_CONSTRUCT('status', 'ok', 'contract', OBJECT_CONSTRUCT('id', 'stock_coverage', 'version', '0.5.1'), 'measure', OBJECT_CONSTRUCT('measure', 'stock_on_hand', 'period_aggregation', 'CLOSING_STOCK', 'method', 'LAST_PERIOD'),
           'request', OBJECT_CONSTRUCT_KEEP_NULL('periods', ctx:PERIODS, 'basis', par:BASIS, 'grain', par:GRAIN,
                                                 'filters', par:FILTERS, 'totals', par:TOTALS),
           'rows', COALESCE(cv:ROWS, ARRAY_CONSTRUCT()), 'row_count', cv:ROW_COUNT,
           'warnings', COALESCE(cv:WARNINGS, ARRAY_CONSTRUCT()),
           'note', 'Closing stock over a period: the snapshot of the period''s last month, for every member of the period. A member with a snapshot in any month of the period and none in its last month closes at 0 and keeps its row. Never summed, averaged or carried forward over time. A total is recomputed at its coarser grain from the stock rows, never added from the rows returned. Several periods give a series with no total across periods.',
           'available_months', IFF(ctx IS NULL, NULL, OBJECT_CONSTRUCT_KEEP_NULL('first', ctx:AVAILABLE_FIRST, 'last', ctx:AVAILABLE_LATEST, 'latest', ctx:AVAILABLE_LATEST)), 'caller', OBJECT_CONSTRUCT_KEEP_NULL('current_role', par:CALLER_ROLE, 'current_secondary_roles', par:CALLER_SECONDARY_ROLES, 'current_user', par:CALLER_USER, 'is_agent_activated', par:AGENT_ACTIVATED),
           'lineage', OBJECT_CONSTRUCT('query_ids', lineage),
           'timing_ms', OBJECT_CONSTRUCT('context_ms', DATEDIFF('millisecond', t1, t2), 'closing_ms',
                                         DATEDIFF('millisecond', t2, t3), 'total_ms', DATEDIFF('millisecond', t0, CURRENT_TIMESTAMP())));
END;
$$;
