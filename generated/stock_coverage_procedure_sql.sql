-- GENERATED from contract/stock_coverage.yaml (contract stock_coverage, version 0.5.1)
-- by compiler/gen_procedure.py, SQL Scripting target compiler/procedure_scripting.py. Do not edit: change the contract and run
-- `python compiler/gen_procedure.py`. tests/test_generated.py regenerates this file and fails on any difference.
--
-- LINKML_METRICS.RAW.STOCK_COVERAGE: stock coverage, refusals, warnings and the query ids of its statements as one JSON answer.
-- Parameters (lists and maps are JSON strings):
--   as_of_months: Analysis months, as first days of month (YYYY-MM-01), or LATEST. One month gives one answer; several give a series with no total across months. If the user gives no month, or a period (a year, a quarter), ask which month: never pick one. One invalid month refuses the whole call. Example: ["2026-06-01"]
--   grain: Attributes to break the coverage down by, at least one. Conformed or snapshot-only attributes. Example: ["family_code", "country_code"]
--   filters: Attribute to list of values. "{}" for no filter. A filter on a snapshot-only attribute restricts the stock only. A filter on item_type lifts the default scope. Example: {"country_code": ["FR"], "batch_status": ["RELEASED"]}
--   basis: The basis on which stock and forecast are measured before the ratio; coverage is always in months. QTY_EQ (kg or L equivalent, the default) for items of one dimension; VALUE (EUR) when the user asks for value or when items of different dimensions are combined; NATIVE (the item's own unit) for one item. A basis the request cannot compare is refused with the bases allowed, never switched. Example: QTY_EQ
--   totals: Coarser grains to add as total rows, each a subset of grain; [] for none, [[]] for a grand total. Each total is recomputed, never summed. Example: [["country_code"], []]
--   coverage_below: Keep the members that stock out within this many months: 0 < coverage <= N, from the next month up to month N included. Members already out (coverage 0) and members with no demand come back apart. A positive number. Example: 3
--   coverage_above: Keep the members whose coverage is above this many months (stock that sleeps); with coverage_below, a window. A positive number. Example: 12
--   rank_first: Keep the first n members by coverage, lowest first, ties broken by the grain codes; with coverage_below or coverage_above, the first n of the members they keep. Members already out and members with no demand are not ranked: they come back apart. A positive integer. Example: 10
-- Refusal codes, in check order: AS_OF_MISSING, AS_OF_INVALID, AS_OF_NOT_MONTH_START, AS_OF_TOO_MANY, AS_OF_NO_SNAPSHOT, HORIZON_NOT_LOADED, BASIS_UNKNOWN, GRAIN_MALFORMED, GRAIN_EMPTY, GRAIN_DUPLICATE, FILTERS_MALFORMED, FILTER_VALUES_INVALID, ATTRIBUTE_UNKNOWN, ATTRIBUTE_UNCLASSIFIED, ATTRIBUTE_NOT_APPLICABLE, TOTALS_MALFORMED, TOTALS_NOT_SUBSET, SELECTION_INVALID, MASTER_DATA_FANOUT, DATA_QUALITY_FAILED, BASIS_NOT_COMPARABLE.
--
-- Run as LINKML_METRICS_ROLE with no secondary role:
--   snow sql -c <connection> -f <this file>
USE SECONDARY ROLES NONE;
USE ROLE LINKML_METRICS_ROLE;

CREATE OR REPLACE PROCEDURE LINKML_METRICS.RAW.STOCK_COVERAGE(
    AS_OF_MONTHS VARCHAR,
    GRAIN VARCHAR,
    FILTERS VARCHAR,
    BASIS VARCHAR DEFAULT 'QTY_EQ',
    TOTALS VARCHAR DEFAULT '[]',
    COVERAGE_BELOW VARCHAR DEFAULT NULL,
    COVERAGE_ABOVE VARCHAR DEFAULT NULL,
    RANK_FIRST VARCHAR DEFAULT NULL)
RETURNS VARIANT
LANGUAGE SQL
COMMENT = 'Generated from contract stock_coverage 0.5.1 by compiler/gen_procedure.py (SQL Scripting)'
EXECUTE AS CALLER
AS
$$
-- Generated from the contract by compiler/gen_procedure.py --target sql (compiler/procedure_scripting.py).
-- Cost rule (measured, session 8b): each distinct Scripting statement costs about 15 ms the first time it runs, so
-- the work is done by SQL statements started together (their compilation runs in parallel) and the Scripting part is
-- kept to a few statements.
DECLARE
  refused EXCEPTION (-20001, 'stock coverage request refused');
  t0 TIMESTAMP_LTZ;
  t1 TIMESTAMP_LTZ;
  t2 TIMESTAMP_LTZ;
  t3 TIMESTAMP_LTZ;
  t4 TIMESTAMP_LTZ;
  t5 TIMESTAMP_LTZ;
  rcode VARCHAR;
  reason VARCHAR;
  lineage OBJECT;
  pre VARIANT;
  plan VARIANT;
  par VARIANT;
  qv VARIANT;
  cv VARIANT;
  parsed_json VARCHAR;
  base VARCHAR;
  qsql VARCHAR;
  csql VARCHAR;
  req VARCHAR;
  rs_k RESULTSET;
  rs_p RESULTSET;
  rs_b RESULTSET;
  rs_tq RESULTSET;
  rs_tc RESULTSET;
  rs_q RESULTSET;
  rs_c RESULTSET;
  jobs_started BOOLEAN DEFAULT FALSE;
BEGIN
  t0 := CURRENT_TIMESTAMP();
  BEGIN
    -- ---- four statements that read no table, started first so that they compile in parallel with the rest: the
    -- parameter checks after the context with the normalised request, and the text of the data statements in three
    -- parts
    rs_p := ASYNC (SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) AS P FROM (
WITH b AS (
    SELECT :BASIS AS basis_raw, :COVERAGE_BELOW AS below_raw, :COVERAGE_ABOVE AS above_raw, :RANK_FIRST AS rank_raw,
           :GRAIN AS grain_raw, :FILTERS AS filters_raw, :TOTALS AS totals_raw
),
s1 AS (
    SELECT b.*,
           REGEXP_REPLACE(UPPER(TRIM(COALESCE(basis_raw, ''), ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), '[\\s-]+', '_') AS ukey,
           IFF(basis_raw IS NULL OR TRIM(basis_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), 'QTY_EQ',
               CASE ukey WHEN 'ITEM_UNIT' THEN 'NATIVE' WHEN 'NATIVE' THEN 'NATIVE' WHEN 'OWN_UNIT' THEN 'NATIVE' WHEN 'PACKS' THEN 'NATIVE' WHEN 'QTY_RAW' THEN 'NATIVE' WHEN 'RAW' THEN 'NATIVE' WHEN 'RAW_UNIT' THEN 'NATIVE' WHEN 'RAW_UNITS' THEN 'NATIVE' WHEN 'UNITS' THEN 'NATIVE' WHEN 'KG' THEN 'QTY_EQ' WHEN 'KILOS' THEN 'QTY_EQ' WHEN 'L' THEN 'QTY_EQ' WHEN 'LITRES' THEN 'QTY_EQ' WHEN 'QTY_EQ' THEN 'QTY_EQ' WHEN 'QUANTITY' THEN 'QTY_EQ' WHEN 'QUANTITY_EQUIVALENT' THEN 'QTY_EQ' WHEN 'VOLUME' THEN 'QTY_EQ' WHEN 'EUR' THEN 'VALUE' WHEN 'EUROS' THEN 'VALUE' WHEN 'MONEY' THEN 'VALUE' WHEN 'VALUE' THEN 'VALUE' ELSE NULL END) AS basis,
           IFF(below_raw IS NULL OR TRIM(below_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, below_raw) AS v_below,
           IFF(above_raw IS NULL OR TRIM(above_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, above_raw) AS v_above,
           IFF(rank_raw IS NULL OR TRIM(rank_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, rank_raw) AS v_rank,
           CASE WHEN v_below IS NOT NULL AND NOT (REGEXP_LIKE(v_below, '\\s*[0-9]+(\\.[0-9]+)?\\s*') AND TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'coverage_below', 'e', 'a positive number of months', 'v', v_below) WHEN v_above IS NOT NULL AND NOT (REGEXP_LIKE(v_above, '\\s*[0-9]+(\\.[0-9]+)?\\s*') AND TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'coverage_above', 'e', 'a positive number of months', 'v', v_above) WHEN v_rank IS NOT NULL AND NOT (REGEXP_LIKE(v_rank, '\\s*[0-9]+\\s*') AND TRY_TO_DOUBLE(TRIM(v_rank, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'rank_first', 'e', 'a positive integer', 'v', v_rank) WHEN v_below IS NOT NULL AND v_above IS NOT NULL AND TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) >= TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) THEN OBJECT_CONSTRUCT('p', 'coverage_above', 'e', 'lower than coverage_below (' || TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) || ')', 'v', TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) END AS sel_bad,
           IFF(sel_bad IS NULL, TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_below,
           IFF(sel_bad IS NULL, TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_above,
           IFF(sel_bad IS NULL, TRY_TO_NUMBER(TRIM(v_rank, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_rank,
           sel_bad IS NULL AND (v_below IS NOT NULL OR v_above IS NOT NULL OR v_rank IS NOT NULL) AS sel_on,
           TRIM(grain_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) AS g_s,
           grain_raw IS NOT NULL AND g_s <> '' AND LEFT(g_s, 1) IN ('[', '{') AND NOT COALESCE(IS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), FALSE) AS g_bad_json,
           CASE WHEN grain_raw IS NULL OR g_s = '' THEN ARRAY_CONSTRUCT()
                WHEN LEFT(g_s, 1) IN ('[', '{') THEN COALESCE(AS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), ARRAY_CONSTRUCT())
                ELSE FILTER(TRANSFORM(SPLIT(g_s, ','), x -> TRIM(x::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))::VARIANT), x -> x::VARCHAR <> '') END AS g_items,
           COALESCE(g_bad_json, FALSE) OR ARRAY_SIZE(FILTER(g_items, x -> TYPEOF(x) <> 'VARCHAR')) > 0 AS grain_malformed,
           TRANSFORM(FILTER(g_items, x -> TYPEOF(x) = 'VARCHAR'), x -> LOWER(TRIM(x::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)))::VARIANT) AS grain,
           ARRAY_DISTINCT(ARRAY_EXCEPT(grain, ARRAY_DISTINCT(grain))) AS g_dup_set,
           ARRAY_CAT(FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'), x -> ARRAY_CONTAINS(x, g_dup_set)), ARRAY_SORT(FILTER(g_dup_set, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'))))) AS grain_dups,
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
           ARRAY_DISTINCT(ARRAY_CAT(grain, fkeys)) AS names,
           ARRAY_CAT(FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'), x -> ARRAY_CONTAINS(x, names)), ARRAY_SORT(FILTER(names, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'))))) AS ranked,
           GET(FILTER(ranked, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type')) AND NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS unknown_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS unclassified_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS not_applicable_attribute,
           GET(FILTER(totals, t -> ARRAY_SIZE(ARRAY_DISTINCT(t::ARRAY)) <> ARRAY_SIZE(t::ARRAY)
                      OR ARRAY_SIZE(ARRAY_EXCEPT(t::ARRAY, grain)) > 0 OR ARRAY_SIZE(t::ARRAY) >= ARRAY_SIZE(grain)), 0)::ARRAY AS bad_total,
           NOT ARRAY_CONTAINS('item_type'::VARIANT, fkeys) AS scope_on,
           FILTER(grain, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code'))) AS conformed,
           ARRAY_DISTINCT(ARRAY_APPEND(ARRAY_CAT(grain, fkeys), 'item_type')) AS used,
           ARRAY_PREPEND(totals, grain) AS grains,
           FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'item_type'), x -> ARRAY_CONTAINS(x, used)) AS fanout_attrs
    FROM s1, fa
)
SELECT CASE WHEN basis IS NULL THEN 'BASIS_UNKNOWN' WHEN grain_malformed THEN 'GRAIN_MALFORMED' WHEN ARRAY_SIZE(grain) = 0 THEN 'GRAIN_EMPTY' WHEN ARRAY_SIZE(grain_dups) > 0 THEN 'GRAIN_DUPLICATE' WHEN filters_malformed THEN 'FILTERS_MALFORMED' WHEN bad_filter IS NOT NULL THEN 'FILTER_VALUES_INVALID' WHEN unknown_attribute IS NOT NULL THEN 'ATTRIBUTE_UNKNOWN' WHEN unclassified_attribute IS NOT NULL THEN 'ATTRIBUTE_UNCLASSIFIED' WHEN not_applicable_attribute IS NOT NULL THEN 'ATTRIBUTE_NOT_APPLICABLE' WHEN totals_malformed THEN 'TOTALS_MALFORMED' WHEN bad_total IS NOT NULL THEN 'TOTALS_NOT_SUBSET' WHEN sel_bad IS NOT NULL THEN 'SELECTION_INVALID' END AS RCODE, CASE WHEN basis IS NULL THEN 'basis ''' || (basis_raw) || ''' is not one of NATIVE, QTY_EQ, VALUE.' WHEN grain_malformed THEN 'grain must be a JSON array of attribute names.' WHEN ARRAY_SIZE(grain) = 0 THEN 'grain must name at least one attribute (for example sku_code, country_code).' WHEN ARRAY_SIZE(grain_dups) > 0 THEN 'grain lists an attribute twice: ' || (ARRAY_TO_STRING(grain_dups, ', ')) || '.' WHEN filters_malformed THEN 'filters must be a JSON object: attribute -> list of values.' WHEN bad_filter IS NOT NULL THEN 'filter ''' || (bad_filter) || ''' needs a non-empty list of values.' WHEN unknown_attribute IS NOT NULL THEN '''' || (unknown_attribute) || ''' is not a coverage attribute. Conformed: ' || ('sku_code, family_code, range_code, lifecycle_status, dimension, country_code, region_code') || '. Stock-only: ' || ('batch_status, expiry_bucket, warehouse_code, warehouse_type, item_type') || '.' WHEN unclassified_attribute IS NOT NULL THEN '''' || (unclassified_attribute) || ''' has no declared applicability class, so it cannot be used with coverage.' WHEN not_applicable_attribute IS NOT NULL THEN '''' || (not_applicable_attribute) || ''' does not apply to stock coverage: ' || (CASE not_applicable_attribute WHEN 'sku_code' THEN '' WHEN 'family_code' THEN '' WHEN 'range_code' THEN '' WHEN 'lifecycle_status' THEN 'An item attribute, so the forecast carries it too (decision 6, session 4). Trap T7 duplicates exactly this column: QE_ITEM_GRAIN refuses a query that uses it while an item has two values.' WHEN 'dimension' THEN 'The physical dimension in which the item is counted, with its base unit: MASS (kg) or VOLUME (L). Grouping or filtering by it keeps quantity-equivalent rows within one dimension.' WHEN 'country_code' THEN 'ISO 3166-1 alpha-2 code.' WHEN 'region_code' THEN '' WHEN 'batch_status' THEN '' WHEN 'expiry_bucket' THEN '' WHEN 'warehouse_code' THEN '' WHEN 'warehouse_type' THEN '' WHEN 'item_type' THEN 'Snapshot-only by decision: BULK items carry stock but never a forecast. Default scope STANDARD for stock coverage only (SCOPE_ITEM_TYPE, decision 5); closing stock counts every item type.' ELSE '' END) || '.' WHEN totals_malformed THEN 'totals must be a JSON array of attribute arrays, for example [["country_code"], []].' WHEN bad_total IS NOT NULL THEN 'Total ' || (ARRAY_TO_STRING(bad_total, ', ')) || ' is not a subset of the grain ' || (ARRAY_TO_STRING(grain, ', ')) || ': a total can only be coarser than the rows.' WHEN sel_bad IS NOT NULL THEN (sel_bad:p::VARCHAR) || ' must be ' || (sel_bad:e::VARCHAR) || '; got ''' || (sel_bad:v::VARCHAR) || '''.' END AS REASON,
       basis AS BASIS, grain AS GRAIN, filters AS FILTERS, totals AS TOTALS, scope_on AS SCOPE_ON,
       sel_below AS SEL_BELOW, sel_above AS SEL_ABOVE, sel_rank AS SEL_RANK, sel_on AS SEL_ON,
       FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code'))) AS STOCK_AND_FORECAST,
       FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'))) AS STOCK_ONLY
FROM s2
    ));
    rs_b := ASYNC (SELECT T FROM (
WITH b AS (
    SELECT :BASIS AS basis_raw, :COVERAGE_BELOW AS below_raw, :COVERAGE_ABOVE AS above_raw, :RANK_FIRST AS rank_raw,
           :GRAIN AS grain_raw, :FILTERS AS filters_raw, :TOTALS AS totals_raw
),
s1 AS (
    SELECT b.*,
           REGEXP_REPLACE(UPPER(TRIM(COALESCE(basis_raw, ''), ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), '[\\s-]+', '_') AS ukey,
           IFF(basis_raw IS NULL OR TRIM(basis_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), 'QTY_EQ',
               CASE ukey WHEN 'ITEM_UNIT' THEN 'NATIVE' WHEN 'NATIVE' THEN 'NATIVE' WHEN 'OWN_UNIT' THEN 'NATIVE' WHEN 'PACKS' THEN 'NATIVE' WHEN 'QTY_RAW' THEN 'NATIVE' WHEN 'RAW' THEN 'NATIVE' WHEN 'RAW_UNIT' THEN 'NATIVE' WHEN 'RAW_UNITS' THEN 'NATIVE' WHEN 'UNITS' THEN 'NATIVE' WHEN 'KG' THEN 'QTY_EQ' WHEN 'KILOS' THEN 'QTY_EQ' WHEN 'L' THEN 'QTY_EQ' WHEN 'LITRES' THEN 'QTY_EQ' WHEN 'QTY_EQ' THEN 'QTY_EQ' WHEN 'QUANTITY' THEN 'QTY_EQ' WHEN 'QUANTITY_EQUIVALENT' THEN 'QTY_EQ' WHEN 'VOLUME' THEN 'QTY_EQ' WHEN 'EUR' THEN 'VALUE' WHEN 'EUROS' THEN 'VALUE' WHEN 'MONEY' THEN 'VALUE' WHEN 'VALUE' THEN 'VALUE' ELSE NULL END) AS basis,
           IFF(below_raw IS NULL OR TRIM(below_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, below_raw) AS v_below,
           IFF(above_raw IS NULL OR TRIM(above_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, above_raw) AS v_above,
           IFF(rank_raw IS NULL OR TRIM(rank_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, rank_raw) AS v_rank,
           CASE WHEN v_below IS NOT NULL AND NOT (REGEXP_LIKE(v_below, '\\s*[0-9]+(\\.[0-9]+)?\\s*') AND TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'coverage_below', 'e', 'a positive number of months', 'v', v_below) WHEN v_above IS NOT NULL AND NOT (REGEXP_LIKE(v_above, '\\s*[0-9]+(\\.[0-9]+)?\\s*') AND TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'coverage_above', 'e', 'a positive number of months', 'v', v_above) WHEN v_rank IS NOT NULL AND NOT (REGEXP_LIKE(v_rank, '\\s*[0-9]+\\s*') AND TRY_TO_DOUBLE(TRIM(v_rank, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'rank_first', 'e', 'a positive integer', 'v', v_rank) WHEN v_below IS NOT NULL AND v_above IS NOT NULL AND TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) >= TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) THEN OBJECT_CONSTRUCT('p', 'coverage_above', 'e', 'lower than coverage_below (' || TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) || ')', 'v', TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) END AS sel_bad,
           IFF(sel_bad IS NULL, TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_below,
           IFF(sel_bad IS NULL, TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_above,
           IFF(sel_bad IS NULL, TRY_TO_NUMBER(TRIM(v_rank, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_rank,
           sel_bad IS NULL AND (v_below IS NOT NULL OR v_above IS NOT NULL OR v_rank IS NOT NULL) AS sel_on,
           TRIM(grain_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) AS g_s,
           grain_raw IS NOT NULL AND g_s <> '' AND LEFT(g_s, 1) IN ('[', '{') AND NOT COALESCE(IS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), FALSE) AS g_bad_json,
           CASE WHEN grain_raw IS NULL OR g_s = '' THEN ARRAY_CONSTRUCT()
                WHEN LEFT(g_s, 1) IN ('[', '{') THEN COALESCE(AS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), ARRAY_CONSTRUCT())
                ELSE FILTER(TRANSFORM(SPLIT(g_s, ','), x -> TRIM(x::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))::VARIANT), x -> x::VARCHAR <> '') END AS g_items,
           COALESCE(g_bad_json, FALSE) OR ARRAY_SIZE(FILTER(g_items, x -> TYPEOF(x) <> 'VARCHAR')) > 0 AS grain_malformed,
           TRANSFORM(FILTER(g_items, x -> TYPEOF(x) = 'VARCHAR'), x -> LOWER(TRIM(x::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)))::VARIANT) AS grain,
           ARRAY_DISTINCT(ARRAY_EXCEPT(grain, ARRAY_DISTINCT(grain))) AS g_dup_set,
           ARRAY_CAT(FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'), x -> ARRAY_CONTAINS(x, g_dup_set)), ARRAY_SORT(FILTER(g_dup_set, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'))))) AS grain_dups,
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
           ARRAY_DISTINCT(ARRAY_CAT(grain, fkeys)) AS names,
           ARRAY_CAT(FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'), x -> ARRAY_CONTAINS(x, names)), ARRAY_SORT(FILTER(names, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'))))) AS ranked,
           GET(FILTER(ranked, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type')) AND NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS unknown_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS unclassified_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS not_applicable_attribute,
           GET(FILTER(totals, t -> ARRAY_SIZE(ARRAY_DISTINCT(t::ARRAY)) <> ARRAY_SIZE(t::ARRAY)
                      OR ARRAY_SIZE(ARRAY_EXCEPT(t::ARRAY, grain)) > 0 OR ARRAY_SIZE(t::ARRAY) >= ARRAY_SIZE(grain)), 0)::ARRAY AS bad_total,
           NOT ARRAY_CONTAINS('item_type'::VARIANT, fkeys) AS scope_on,
           FILTER(grain, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code'))) AS conformed,
           ARRAY_DISTINCT(ARRAY_APPEND(ARRAY_CAT(grain, fkeys), 'item_type')) AS used,
           ARRAY_PREPEND(totals, grain) AS grains,
           FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'item_type'), x -> ARRAY_CONTAINS(x, used)) AS fanout_attrs
    FROM s1, fa
)
SELECT 'WITH req AS (SELECT PARSE_JSON(?) AS r),\nanalysis_months AS (\n    SELECT f.value::DATE AS as_of_month FROM req, TABLE(FLATTEN(INPUT => req.r:months)) f\n),\nmonths AS (\n    SELECT 0 + ROW_NUMBER() OVER (ORDER BY SEQ4()) AS k FROM TABLE(GENERATOR(ROWCOUNT => 24))\n),\nstock_rows AS (\n    SELECT a.as_of_month, stock_snapshot.item_id, stock_snapshot.country_id, ' || ARRAY_TO_STRING(TRANSFORM(grain, x -> CASE x::VARCHAR WHEN 'sku_code' THEN 'item.sku_code' WHEN 'family_code' THEN 'item.family_code' WHEN 'range_code' THEN 'item.range_code' WHEN 'lifecycle_status' THEN 'item.lifecycle_status' WHEN 'dimension' THEN 'item.dimension' WHEN 'country_code' THEN 'geo.country_code' WHEN 'region_code' THEN 'geo.region_code' WHEN 'batch_status' THEN 'batch.batch_status' WHEN 'expiry_bucket' THEN 'stock_snapshot.expiry_bucket' WHEN 'warehouse_code' THEN 'warehouse.warehouse_code' WHEN 'warehouse_type' THEN 'warehouse.warehouse_type' WHEN 'item_type' THEN 'item.item_type' ELSE NULL END || ' AS ' || x::VARCHAR), ', ') || ', ' || 'item.item_type AS scope_value, stock_snapshot.' || CASE basis WHEN 'NATIVE' THEN 'stock_qty_raw' WHEN 'QTY_EQ' THEN 'stock_qty_eq' WHEN 'VALUE' THEN 'stock_value_eur' ELSE NULL END || '::FLOAT AS qty, stock_snapshot.' || CASE basis WHEN 'NATIVE' THEN 'stock_qty_eq' WHEN 'QTY_EQ' THEN 'stock_qty_eq' WHEN 'VALUE' THEN 'stock_value_eur' ELSE NULL END || '::FLOAT AS scope_qty
    FROM analysis_months a
    JOIN LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT stock_snapshot ON stock_snapshot.snapshot_month = a.as_of_month' || IFF(ARRAY_SIZE(ARRAY_INTERSECTION(used, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'item_type'))) > 0, '
    JOIN ' || '(SELECT DISTINCT ' || ARRAY_TO_STRING(ARRAY_DISTINCT(ARRAY_CAT(ARRAY_CONSTRUCT('item_id'), TRANSFORM(ARRAY_INTERSECTION(used, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'item_type')), x -> CASE x::VARCHAR WHEN 'sku_code' THEN 'sku_code' WHEN 'family_code' THEN 'family_code' WHEN 'range_code' THEN 'range_code' WHEN 'lifecycle_status' THEN 'lifecycle_status' WHEN 'dimension' THEN 'dimension' WHEN 'country_code' THEN 'country_code' WHEN 'region_code' THEN 'region_code' WHEN 'batch_status' THEN 'batch_status' WHEN 'expiry_bucket' THEN 'expiry_bucket' WHEN 'warehouse_code' THEN 'warehouse_code' WHEN 'warehouse_type' THEN 'warehouse_type' WHEN 'item_type' THEN 'item_type' ELSE NULL END))), ', ') || ' FROM LINKML_METRICS.RAW.DIM_ITEM)' || ' item ON item.item_id = stock_snapshot.item_id', '') || IFF(ARRAY_SIZE(ARRAY_INTERSECTION(used, ARRAY_CONSTRUCT('country_code', 'region_code'))) > 0, '
    JOIN ' || 'LINKML_METRICS.RAW.DIM_GEO' || ' geo ON geo.country_id = stock_snapshot.country_id', '') || IFF(ARRAY_SIZE(ARRAY_INTERSECTION(used, ARRAY_CONSTRUCT('batch_status'))) > 0, '
    JOIN ' || 'LINKML_METRICS.RAW.DIM_BATCH' || ' batch ON batch.batch_id = stock_snapshot.batch_id', '') || IFF(ARRAY_SIZE(ARRAY_INTERSECTION(used, ARRAY_CONSTRUCT('warehouse_code', 'warehouse_type'))) > 0, '
    JOIN ' || 'LINKML_METRICS.RAW.DIM_WAREHOUSE' || ' warehouse ON warehouse.warehouse_id = stock_snapshot.warehouse_id', '') || '\n    WHERE ' || COALESCE(NULLIF(ARRAY_TO_STRING(TRANSFORM(fkeys, x -> CASE x::VARCHAR WHEN 'sku_code' THEN 'item.sku_code' WHEN 'family_code' THEN 'item.family_code' WHEN 'range_code' THEN 'item.range_code' WHEN 'lifecycle_status' THEN 'item.lifecycle_status' WHEN 'dimension' THEN 'item.dimension' WHEN 'country_code' THEN 'geo.country_code' WHEN 'region_code' THEN 'geo.region_code' WHEN 'batch_status' THEN 'batch.batch_status' WHEN 'expiry_bucket' THEN 'stock_snapshot.expiry_bucket' WHEN 'warehouse_code' THEN 'warehouse.warehouse_code' WHEN 'warehouse_type' THEN 'warehouse.warehouse_type' WHEN 'item_type' THEN 'item.item_type' ELSE NULL END || ' IN (SELECT f.value::VARCHAR FROM req, TABLE(FLATTEN(INPUT => req.r:filters:"' || x::VARCHAR || '")) f)'), ' AND '), ''), 'TRUE') || '\n),\nfc_rows AS (\n    SELECT a.as_of_month, forecast.item_id, forecast.country_id, ' || ARRAY_TO_STRING(TRANSFORM(conformed, x -> CASE x::VARCHAR WHEN 'sku_code' THEN 'item.sku_code' WHEN 'family_code' THEN 'item.family_code' WHEN 'range_code' THEN 'item.range_code' WHEN 'lifecycle_status' THEN 'item.lifecycle_status' WHEN 'dimension' THEN 'item.dimension' WHEN 'country_code' THEN 'geo.country_code' WHEN 'region_code' THEN 'geo.region_code' WHEN 'batch_status' THEN 'batch.batch_status' WHEN 'expiry_bucket' THEN 'stock_snapshot.expiry_bucket' WHEN 'warehouse_code' THEN 'warehouse.warehouse_code' WHEN 'warehouse_type' THEN 'warehouse.warehouse_type' WHEN 'item_type' THEN 'item.item_type' ELSE NULL END || ' AS ' || x::VARCHAR || ', '), '') || 'DATEDIFF(month, a.as_of_month, forecast.forecast_month) AS k, forecast.' || CASE basis WHEN 'NATIVE' THEN 'forecast_qty_raw' WHEN 'QTY_EQ' THEN 'forecast_qty_eq' WHEN 'VALUE' THEN 'forecast_value_eur' ELSE NULL END || '::FLOAT AS qty
    FROM analysis_months a
    JOIN LINKML_METRICS.RAW.FCT_FORECAST forecast
      ON forecast.forecast_month >= DATEADD(month, 1, a.as_of_month)
     AND forecast.forecast_month <= DATEADD(month, 24, a.as_of_month)' || IFF(ARRAY_SIZE(ARRAY_INTERSECTION(ARRAY_INTERSECTION(used, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code')), ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'item_type'))) > 0, '
    JOIN ' || '(SELECT DISTINCT ' || ARRAY_TO_STRING(ARRAY_DISTINCT(ARRAY_CAT(ARRAY_CONSTRUCT('item_id'), TRANSFORM(ARRAY_INTERSECTION(ARRAY_INTERSECTION(used, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code')), ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'item_type')), x -> CASE x::VARCHAR WHEN 'sku_code' THEN 'sku_code' WHEN 'family_code' THEN 'family_code' WHEN 'range_code' THEN 'range_code' WHEN 'lifecycle_status' THEN 'lifecycle_status' WHEN 'dimension' THEN 'dimension' WHEN 'country_code' THEN 'country_code' WHEN 'region_code' THEN 'region_code' WHEN 'batch_status' THEN 'batch_status' WHEN 'expiry_bucket' THEN 'expiry_bucket' WHEN 'warehouse_code' THEN 'warehouse_code' WHEN 'warehouse_type' THEN 'warehouse_type' WHEN 'item_type' THEN 'item_type' ELSE NULL END))), ', ') || ' FROM LINKML_METRICS.RAW.DIM_ITEM)' || ' item ON item.item_id = forecast.item_id', '') || IFF(ARRAY_SIZE(ARRAY_INTERSECTION(ARRAY_INTERSECTION(used, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code')), ARRAY_CONSTRUCT('country_code', 'region_code'))) > 0, '
    JOIN ' || 'LINKML_METRICS.RAW.DIM_GEO' || ' geo ON geo.country_id = forecast.country_id', '') || '\n    WHERE ' || COALESCE(NULLIF(ARRAY_TO_STRING(TRANSFORM(ARRAY_INTERSECTION(fkeys, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code')), x -> CASE x::VARCHAR WHEN 'sku_code' THEN 'item.sku_code' WHEN 'family_code' THEN 'item.family_code' WHEN 'range_code' THEN 'item.range_code' WHEN 'lifecycle_status' THEN 'item.lifecycle_status' WHEN 'dimension' THEN 'item.dimension' WHEN 'country_code' THEN 'geo.country_code' WHEN 'region_code' THEN 'geo.region_code' WHEN 'batch_status' THEN 'batch.batch_status' WHEN 'expiry_bucket' THEN 'stock_snapshot.expiry_bucket' WHEN 'warehouse_code' THEN 'warehouse.warehouse_code' WHEN 'warehouse_type' THEN 'warehouse.warehouse_type' WHEN 'item_type' THEN 'item.item_type' ELSE NULL END || ' IN (SELECT f.value::VARCHAR FROM req, TABLE(FLATTEN(INPUT => req.r:filters:"' || x::VARCHAR || '")) f)'), ' AND '), ''), 'TRUE') || '\n)' || ',
items AS (SELECT DISTINCT item_id AS item_id, dimension AS dimension, base_unit AS base_unit, raw_unit AS native_unit FROM LINKML_METRICS.RAW.DIM_ITEM)' AS T FROM s2
    ));
    rs_tq := ASYNC (SELECT T FROM (
WITH b AS (
    SELECT :BASIS AS basis_raw, :COVERAGE_BELOW AS below_raw, :COVERAGE_ABOVE AS above_raw, :RANK_FIRST AS rank_raw,
           :GRAIN AS grain_raw, :FILTERS AS filters_raw, :TOTALS AS totals_raw
),
s1 AS (
    SELECT b.*,
           REGEXP_REPLACE(UPPER(TRIM(COALESCE(basis_raw, ''), ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), '[\\s-]+', '_') AS ukey,
           IFF(basis_raw IS NULL OR TRIM(basis_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), 'QTY_EQ',
               CASE ukey WHEN 'ITEM_UNIT' THEN 'NATIVE' WHEN 'NATIVE' THEN 'NATIVE' WHEN 'OWN_UNIT' THEN 'NATIVE' WHEN 'PACKS' THEN 'NATIVE' WHEN 'QTY_RAW' THEN 'NATIVE' WHEN 'RAW' THEN 'NATIVE' WHEN 'RAW_UNIT' THEN 'NATIVE' WHEN 'RAW_UNITS' THEN 'NATIVE' WHEN 'UNITS' THEN 'NATIVE' WHEN 'KG' THEN 'QTY_EQ' WHEN 'KILOS' THEN 'QTY_EQ' WHEN 'L' THEN 'QTY_EQ' WHEN 'LITRES' THEN 'QTY_EQ' WHEN 'QTY_EQ' THEN 'QTY_EQ' WHEN 'QUANTITY' THEN 'QTY_EQ' WHEN 'QUANTITY_EQUIVALENT' THEN 'QTY_EQ' WHEN 'VOLUME' THEN 'QTY_EQ' WHEN 'EUR' THEN 'VALUE' WHEN 'EUROS' THEN 'VALUE' WHEN 'MONEY' THEN 'VALUE' WHEN 'VALUE' THEN 'VALUE' ELSE NULL END) AS basis,
           IFF(below_raw IS NULL OR TRIM(below_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, below_raw) AS v_below,
           IFF(above_raw IS NULL OR TRIM(above_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, above_raw) AS v_above,
           IFF(rank_raw IS NULL OR TRIM(rank_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, rank_raw) AS v_rank,
           CASE WHEN v_below IS NOT NULL AND NOT (REGEXP_LIKE(v_below, '\\s*[0-9]+(\\.[0-9]+)?\\s*') AND TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'coverage_below', 'e', 'a positive number of months', 'v', v_below) WHEN v_above IS NOT NULL AND NOT (REGEXP_LIKE(v_above, '\\s*[0-9]+(\\.[0-9]+)?\\s*') AND TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'coverage_above', 'e', 'a positive number of months', 'v', v_above) WHEN v_rank IS NOT NULL AND NOT (REGEXP_LIKE(v_rank, '\\s*[0-9]+\\s*') AND TRY_TO_DOUBLE(TRIM(v_rank, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'rank_first', 'e', 'a positive integer', 'v', v_rank) WHEN v_below IS NOT NULL AND v_above IS NOT NULL AND TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) >= TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) THEN OBJECT_CONSTRUCT('p', 'coverage_above', 'e', 'lower than coverage_below (' || TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) || ')', 'v', TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) END AS sel_bad,
           IFF(sel_bad IS NULL, TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_below,
           IFF(sel_bad IS NULL, TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_above,
           IFF(sel_bad IS NULL, TRY_TO_NUMBER(TRIM(v_rank, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_rank,
           sel_bad IS NULL AND (v_below IS NOT NULL OR v_above IS NOT NULL OR v_rank IS NOT NULL) AS sel_on,
           TRIM(grain_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) AS g_s,
           grain_raw IS NOT NULL AND g_s <> '' AND LEFT(g_s, 1) IN ('[', '{') AND NOT COALESCE(IS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), FALSE) AS g_bad_json,
           CASE WHEN grain_raw IS NULL OR g_s = '' THEN ARRAY_CONSTRUCT()
                WHEN LEFT(g_s, 1) IN ('[', '{') THEN COALESCE(AS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), ARRAY_CONSTRUCT())
                ELSE FILTER(TRANSFORM(SPLIT(g_s, ','), x -> TRIM(x::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))::VARIANT), x -> x::VARCHAR <> '') END AS g_items,
           COALESCE(g_bad_json, FALSE) OR ARRAY_SIZE(FILTER(g_items, x -> TYPEOF(x) <> 'VARCHAR')) > 0 AS grain_malformed,
           TRANSFORM(FILTER(g_items, x -> TYPEOF(x) = 'VARCHAR'), x -> LOWER(TRIM(x::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)))::VARIANT) AS grain,
           ARRAY_DISTINCT(ARRAY_EXCEPT(grain, ARRAY_DISTINCT(grain))) AS g_dup_set,
           ARRAY_CAT(FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'), x -> ARRAY_CONTAINS(x, g_dup_set)), ARRAY_SORT(FILTER(g_dup_set, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'))))) AS grain_dups,
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
           ARRAY_DISTINCT(ARRAY_CAT(grain, fkeys)) AS names,
           ARRAY_CAT(FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'), x -> ARRAY_CONTAINS(x, names)), ARRAY_SORT(FILTER(names, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'))))) AS ranked,
           GET(FILTER(ranked, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type')) AND NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS unknown_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS unclassified_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS not_applicable_attribute,
           GET(FILTER(totals, t -> ARRAY_SIZE(ARRAY_DISTINCT(t::ARRAY)) <> ARRAY_SIZE(t::ARRAY)
                      OR ARRAY_SIZE(ARRAY_EXCEPT(t::ARRAY, grain)) > 0 OR ARRAY_SIZE(t::ARRAY) >= ARRAY_SIZE(grain)), 0)::ARRAY AS bad_total,
           NOT ARRAY_CONTAINS('item_type'::VARIANT, fkeys) AS scope_on,
           FILTER(grain, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code'))) AS conformed,
           ARRAY_DISTINCT(ARRAY_APPEND(ARRAY_CAT(grain, fkeys), 'item_type')) AS used,
           ARRAY_PREPEND(totals, grain) AS grains,
           FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'item_type'), x -> ARRAY_CONTAINS(x, used)) AS fanout_attrs
    FROM s1, fa
)
SELECT ',
scope_items AS (SELECT item_id FROM stock_rows UNION SELECT item_id FROM fc_rows),
scope_pairs AS (SELECT DISTINCT as_of_month, item_id, country_id FROM fc_rows),
quality_row AS (
SELECT ' || REPLACE('(SELECT COUNT(*) FROM (SELECT item_id FROM LINKML_METRICS.RAW.DIM_ITEM WHERE item_id IN (SELECT item_id FROM scope_items) GROUP BY item_id HAVING COUNT(*) > 1)) AS QE_ITEM_GRAIN,
       (SELECT COUNT(*) FROM (SELECT item_id FROM LINKML_METRICS.RAW.DIM_ITEM WHERE item_id IN (SELECT item_id FROM scope_items) GROUP BY item_id HAVING <<HAVING>>)) AS FANOUT' || ARRAY_TO_STRING(TRANSFORM(fanout_attrs, a -> REPLACE(REPLACE(REPLACE(',
       (SELECT COUNT(*) FROM (SELECT item_id FROM LINKML_METRICS.RAW.DIM_ITEM WHERE item_id IN (SELECT item_id FROM scope_items) GROUP BY item_id HAVING COUNT(DISTINCT <<C>>) > 1)) AS FANOUT__<<AU>>,
       (SELECT ARRAY_AGG(DISTINCT <<C>>) WITHIN GROUP (ORDER BY <<C>>) FROM LINKML_METRICS.RAW.DIM_ITEM WHERE item_id IN (SELECT item_id FROM LINKML_METRICS.RAW.DIM_ITEM WHERE item_id IN (SELECT item_id FROM scope_items) GROUP BY item_id HAVING COUNT(DISTINCT <<C>>) > 1)) AS FANOUT_VALUES__<<AU>>', '<<AU>>', UPPER(a::VARCHAR)), '<<A>>', a::VARCHAR), '<<C>>', CASE a::VARCHAR WHEN 'sku_code' THEN 'sku_code' WHEN 'family_code' THEN 'family_code' WHEN 'range_code' THEN 'range_code' WHEN 'lifecycle_status' THEN 'lifecycle_status' WHEN 'dimension' THEN 'dimension' WHEN 'country_code' THEN 'country_code' WHEN 'region_code' THEN 'region_code' WHEN 'batch_status' THEN 'batch_status' WHEN 'expiry_bucket' THEN 'expiry_bucket' WHEN 'warehouse_code' THEN 'warehouse_code' WHEN 'warehouse_type' THEN 'warehouse_type' WHEN 'item_type' THEN 'item_type' ELSE NULL END)), ''), '<<HAVING>>', COALESCE(NULLIF(ARRAY_TO_STRING(TRANSFORM(fanout_attrs, a -> 'COUNT(DISTINCT ' || CASE a::VARCHAR WHEN 'sku_code' THEN 'sku_code' WHEN 'family_code' THEN 'family_code' WHEN 'range_code' THEN 'range_code' WHEN 'lifecycle_status' THEN 'lifecycle_status' WHEN 'dimension' THEN 'dimension' WHEN 'country_code' THEN 'country_code' WHEN 'region_code' THEN 'region_code' WHEN 'batch_status' THEN 'batch_status' WHEN 'expiry_bucket' THEN 'expiry_bucket' WHEN 'warehouse_code' THEN 'warehouse_code' WHEN 'warehouse_type' THEN 'warehouse_type' WHEN 'item_type' THEN 'item_type' ELSE NULL END || ') > 1'), ' OR '), ''), 'FALSE')) || ',
       (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT t WHERE EXISTS (SELECT 1 FROM analysis_months a WHERE a.as_of_month = t.snapshot_month)
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_ITEM r WHERE r.item_id = t.item_id)) AS QE_STOCK_ITEM_REF,
       (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT t WHERE EXISTS (SELECT 1 FROM analysis_months a WHERE a.as_of_month = t.snapshot_month)
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_BATCH r WHERE r.batch_id = t.batch_id)) AS QE_STOCK_BATCH_REF,
       (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT t WHERE EXISTS (SELECT 1 FROM analysis_months a WHERE a.as_of_month = t.snapshot_month)
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_WAREHOUSE r WHERE r.warehouse_id = t.warehouse_id)) AS QE_STOCK_WAREHOUSE_REF,
       (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT t WHERE EXISTS (SELECT 1 FROM analysis_months a WHERE a.as_of_month = t.snapshot_month)
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_GEO r WHERE r.country_id = t.country_id)) AS QE_STOCK_GEO_REF,
       (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST t WHERE EXISTS (SELECT 1 FROM analysis_months a JOIN months m ON t.forecast_month = DATEADD(month, m.k, a.as_of_month))
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_ITEM r WHERE r.item_id = t.item_id)) AS QE_FORECAST_ITEM_REF,
       (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST t WHERE EXISTS (SELECT 1 FROM analysis_months a JOIN months m ON t.forecast_month = DATEADD(month, m.k, a.as_of_month))
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_GEO r WHERE r.country_id = t.country_id)) AS QE_FORECAST_GEO_REF,
       (SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT t WHERE EXISTS (SELECT 1 FROM analysis_months a WHERE a.as_of_month = t.snapshot_month)
           AND NOT EXISTS (SELECT 1 FROM LINKML_METRICS.RAW.DIM_BATCH r WHERE r.batch_id = t.batch_id AND r.item_id = t.item_id)) AS QE_STOCK_BATCH_ITEM,
       (SELECT COUNT(*) FROM scope_pairs p CROSS JOIN months m WHERE NOT EXISTS
           (SELECT 1 FROM LINKML_METRICS.RAW.FCT_FORECAST x WHERE x.item_id = p.item_id AND x.country_id = p.country_id AND x.forecast_month = DATEADD(month, m.k, p.as_of_month))) AS QE_FORECAST_DENSE' || IFF(scope_on, REPLACE(',
       (SELECT ARRAY_AGG(OBJECT_CONSTRUCT(''code'', ''DEFAULT_SCOPE_EXCLUDED'', ''as_of_month'', m, ''excluded_amount'', amt, ''unit'', u, ''message'', (RTRIM(RTRIM(TO_VARCHAR(amt, ''FM999,999,999,999,999,999,990.0000''), ''0''), ''.'')) || '' '' || (u) || '' of BULK stock excluded by default (no forecast). Filter item_type explicitly to include it.'' || '' (as of '' || m || '')'')) WITHIN GROUP (ORDER BY m, u) FROM (SELECT TO_VARCHAR(s.as_of_month) AS m, <<U>> AS u, SUM(s.scope_qty) AS amt FROM stock_rows s JOIN items it ON it.item_id = s.item_id WHERE NOT (scope_value IN (SELECT f.value::VARCHAR FROM req, TABLE(FLATTEN(INPUT => req.r:scope)) f)) OR s.scope_value IS NULL GROUP BY 1, 2 HAVING SUM(s.scope_qty) <> 0)) AS SCOPE_WARNINGS', '<<U>>', CASE basis WHEN 'VALUE' THEN '''EUR''' ELSE 'it.base_unit' END), '') || '
)
SELECT OBJECT_CONSTRUCT(''Q'', q, ''FANOUT_REASON'', fanout_reason, ''WARNINGS'', warnings) AS Q FROM (
SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) AS q, ' || 'IFF(FANOUT > 0, ' || REPLACE('(FANOUT::VARCHAR) || '' item(s) have several rows in DIM_ITEM that differ on '' || (ARRAY_TO_STRING(ARRAY_CONSTRUCT_COMPACT(<<GROUPS>>), '', '')) || ''; any number at this grain would be fanned out.''', '<<GROUPS>>', ARRAY_TO_STRING(TRANSFORM(fanout_attrs, a -> REPLACE(REPLACE(REPLACE('IFF(FANOUT__<<AU>> > 0, ''<<A>> ('' || ARRAY_TO_STRING(ARRAY_SLICE(FANOUT_VALUES__<<AU>>, 0, 5), '', '') || IFF(ARRAY_SIZE(FANOUT_VALUES__<<AU>>) > 5, '' and '' || (ARRAY_SIZE(FANOUT_VALUES__<<AU>>) - 5)::VARCHAR || '' more'', '''') || '')'', NULL)', '<<AU>>', UPPER(a::VARCHAR)), '<<A>>', a::VARCHAR), '<<C>>', CASE a::VARCHAR WHEN 'sku_code' THEN 'sku_code' WHEN 'family_code' THEN 'family_code' WHEN 'range_code' THEN 'range_code' WHEN 'lifecycle_status' THEN 'lifecycle_status' WHEN 'dimension' THEN 'dimension' WHEN 'country_code' THEN 'country_code' WHEN 'region_code' THEN 'region_code' WHEN 'batch_status' THEN 'batch_status' WHEN 'expiry_bucket' THEN 'expiry_bucket' WHEN 'warehouse_code' THEN 'warehouse_code' WHEN 'warehouse_type' THEN 'warehouse_type' WHEN 'item_type' THEN 'item_type' ELSE NULL END)), ', ')) || ', NULL)' || ' AS fanout_reason, ARRAY_CAT(ARRAY_CONSTRUCT_COMPACT(IFF(COALESCE(QE_ITEM_GRAIN, 0) <> 0, OBJECT_CONSTRUCT(''code'', ''MASTER_DATA_DUPLICATES'', ''expectation'', ''QE_ITEM_GRAIN'', ''count'', QE_ITEM_GRAIN, ''message'', (QE_ITEM_GRAIN::VARCHAR) || '' items have several rows in DIM_ITEM; they agree on the attributes this query uses, so the answer is not affected.''), NULL), IFF(COALESCE(QE_STOCK_ITEM_REF, 0) <> 0, OBJECT_CONSTRUCT(''code'', ''DATA_QUALITY_ROWS'', ''expectation'', ''QE_STOCK_ITEM_REF'', ''count'', QE_STOCK_ITEM_REF, ''message'', (''QE_STOCK_ITEM_REF'') || '': '' || (QE_STOCK_ITEM_REF::VARCHAR) || '' rows read by this answer break the expectation ('' || (''every stock item_id exists in DIM_ITEM'') || '').''), NULL), IFF(COALESCE(QE_STOCK_BATCH_REF, 0) <> 0, OBJECT_CONSTRUCT(''code'', ''DATA_QUALITY_ROWS'', ''expectation'', ''QE_STOCK_BATCH_REF'', ''count'', QE_STOCK_BATCH_REF, ''message'', (''QE_STOCK_BATCH_REF'') || '': '' || (QE_STOCK_BATCH_REF::VARCHAR) || '' rows read by this answer break the expectation ('' || (''every stock batch_id exists in DIM_BATCH'') || '').''), NULL), IFF(COALESCE(QE_STOCK_WAREHOUSE_REF, 0) <> 0, OBJECT_CONSTRUCT(''code'', ''DATA_QUALITY_ROWS'', ''expectation'', ''QE_STOCK_WAREHOUSE_REF'', ''count'', QE_STOCK_WAREHOUSE_REF, ''message'', (''QE_STOCK_WAREHOUSE_REF'') || '': '' || (QE_STOCK_WAREHOUSE_REF::VARCHAR) || '' rows read by this answer break the expectation ('' || (''every stock warehouse_id exists in DIM_WAREHOUSE'') || '').''), NULL), IFF(COALESCE(QE_STOCK_GEO_REF, 0) <> 0, OBJECT_CONSTRUCT(''code'', ''DATA_QUALITY_ROWS'', ''expectation'', ''QE_STOCK_GEO_REF'', ''count'', QE_STOCK_GEO_REF, ''message'', (''QE_STOCK_GEO_REF'') || '': '' || (QE_STOCK_GEO_REF::VARCHAR) || '' rows read by this answer break the expectation ('' || (''every stock country_id exists in DIM_GEO'') || '').''), NULL), IFF(COALESCE(QE_FORECAST_ITEM_REF, 0) <> 0, OBJECT_CONSTRUCT(''code'', ''DATA_QUALITY_ROWS'', ''expectation'', ''QE_FORECAST_ITEM_REF'', ''count'', QE_FORECAST_ITEM_REF, ''message'', (''QE_FORECAST_ITEM_REF'') || '': '' || (QE_FORECAST_ITEM_REF::VARCHAR) || '' rows read by this answer break the expectation ('' || (''every forecast item_id exists in DIM_ITEM'') || '').''), NULL), IFF(COALESCE(QE_FORECAST_GEO_REF, 0) <> 0, OBJECT_CONSTRUCT(''code'', ''DATA_QUALITY_ROWS'', ''expectation'', ''QE_FORECAST_GEO_REF'', ''count'', QE_FORECAST_GEO_REF, ''message'', (''QE_FORECAST_GEO_REF'') || '': '' || (QE_FORECAST_GEO_REF::VARCHAR) || '' rows read by this answer break the expectation ('' || (''every forecast country_id exists in DIM_GEO'') || '').''), NULL), IFF(COALESCE(QE_STOCK_BATCH_ITEM, 0) <> 0, OBJECT_CONSTRUCT(''code'', ''DATA_QUALITY_ROWS'', ''expectation'', ''QE_STOCK_BATCH_ITEM'', ''count'', QE_STOCK_BATCH_ITEM, ''message'', (''QE_STOCK_BATCH_ITEM'') || '': '' || (QE_STOCK_BATCH_ITEM::VARCHAR) || '' rows read by this answer break the expectation ('' || (''the denormalised item_id of a stock row equals the item_id of its batch'') || '').''), NULL), IFF(COALESCE(QE_FORECAST_DENSE, 0) <> 0, OBJECT_CONSTRUCT(''code'', ''FORECAST_GAPS_FILLED'', ''expectation'', ''QE_FORECAST_DENSE'', ''count'', QE_FORECAST_DENSE, ''message'', (QE_FORECAST_DENSE::VARCHAR) || '' member-months of the horizon have no forecast row and were counted as 0.''), NULL)), ' || IFF(scope_on, 'COALESCE(SCOPE_WARNINGS, ARRAY_CONSTRUCT())', 'ARRAY_CONSTRUCT()') || ') AS warnings FROM quality_row)' AS T FROM s2
    ));
    rs_tc := ASYNC (SELECT T FROM (
WITH b AS (
    SELECT :BASIS AS basis_raw, :COVERAGE_BELOW AS below_raw, :COVERAGE_ABOVE AS above_raw, :RANK_FIRST AS rank_raw,
           :GRAIN AS grain_raw, :FILTERS AS filters_raw, :TOTALS AS totals_raw
),
s1 AS (
    SELECT b.*,
           REGEXP_REPLACE(UPPER(TRIM(COALESCE(basis_raw, ''), ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), '[\\s-]+', '_') AS ukey,
           IFF(basis_raw IS NULL OR TRIM(basis_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), 'QTY_EQ',
               CASE ukey WHEN 'ITEM_UNIT' THEN 'NATIVE' WHEN 'NATIVE' THEN 'NATIVE' WHEN 'OWN_UNIT' THEN 'NATIVE' WHEN 'PACKS' THEN 'NATIVE' WHEN 'QTY_RAW' THEN 'NATIVE' WHEN 'RAW' THEN 'NATIVE' WHEN 'RAW_UNIT' THEN 'NATIVE' WHEN 'RAW_UNITS' THEN 'NATIVE' WHEN 'UNITS' THEN 'NATIVE' WHEN 'KG' THEN 'QTY_EQ' WHEN 'KILOS' THEN 'QTY_EQ' WHEN 'L' THEN 'QTY_EQ' WHEN 'LITRES' THEN 'QTY_EQ' WHEN 'QTY_EQ' THEN 'QTY_EQ' WHEN 'QUANTITY' THEN 'QTY_EQ' WHEN 'QUANTITY_EQUIVALENT' THEN 'QTY_EQ' WHEN 'VOLUME' THEN 'QTY_EQ' WHEN 'EUR' THEN 'VALUE' WHEN 'EUROS' THEN 'VALUE' WHEN 'MONEY' THEN 'VALUE' WHEN 'VALUE' THEN 'VALUE' ELSE NULL END) AS basis,
           IFF(below_raw IS NULL OR TRIM(below_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, below_raw) AS v_below,
           IFF(above_raw IS NULL OR TRIM(above_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, above_raw) AS v_above,
           IFF(rank_raw IS NULL OR TRIM(rank_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) IN ('', 'null'), NULL, rank_raw) AS v_rank,
           CASE WHEN v_below IS NOT NULL AND NOT (REGEXP_LIKE(v_below, '\\s*[0-9]+(\\.[0-9]+)?\\s*') AND TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'coverage_below', 'e', 'a positive number of months', 'v', v_below) WHEN v_above IS NOT NULL AND NOT (REGEXP_LIKE(v_above, '\\s*[0-9]+(\\.[0-9]+)?\\s*') AND TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'coverage_above', 'e', 'a positive number of months', 'v', v_above) WHEN v_rank IS NOT NULL AND NOT (REGEXP_LIKE(v_rank, '\\s*[0-9]+\\s*') AND TRY_TO_DOUBLE(TRIM(v_rank, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) > 0) THEN OBJECT_CONSTRUCT('p', 'rank_first', 'e', 'a positive integer', 'v', v_rank) WHEN v_below IS NOT NULL AND v_above IS NOT NULL AND TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) >= TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) THEN OBJECT_CONSTRUCT('p', 'coverage_above', 'e', 'lower than coverage_below (' || TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) || ')', 'v', TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))) END AS sel_bad,
           IFF(sel_bad IS NULL, TRY_TO_DOUBLE(TRIM(v_below, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_below,
           IFF(sel_bad IS NULL, TRY_TO_DOUBLE(TRIM(v_above, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_above,
           IFF(sel_bad IS NULL, TRY_TO_NUMBER(TRIM(v_rank, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))), NULL) AS sel_rank,
           sel_bad IS NULL AND (v_below IS NOT NULL OR v_above IS NOT NULL OR v_rank IS NOT NULL) AS sel_on,
           TRIM(grain_raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) AS g_s,
           grain_raw IS NOT NULL AND g_s <> '' AND LEFT(g_s, 1) IN ('[', '{') AND NOT COALESCE(IS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), FALSE) AS g_bad_json,
           CASE WHEN grain_raw IS NULL OR g_s = '' THEN ARRAY_CONSTRUCT()
                WHEN LEFT(g_s, 1) IN ('[', '{') THEN COALESCE(AS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), ARRAY_CONSTRUCT())
                ELSE FILTER(TRANSFORM(SPLIT(g_s, ','), x -> TRIM(x::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))::VARIANT), x -> x::VARCHAR <> '') END AS g_items,
           COALESCE(g_bad_json, FALSE) OR ARRAY_SIZE(FILTER(g_items, x -> TYPEOF(x) <> 'VARCHAR')) > 0 AS grain_malformed,
           TRANSFORM(FILTER(g_items, x -> TYPEOF(x) = 'VARCHAR'), x -> LOWER(TRIM(x::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)))::VARIANT) AS grain,
           ARRAY_DISTINCT(ARRAY_EXCEPT(grain, ARRAY_DISTINCT(grain))) AS g_dup_set,
           ARRAY_CAT(FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'), x -> ARRAY_CONTAINS(x, g_dup_set)), ARRAY_SORT(FILTER(g_dup_set, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'))))) AS grain_dups,
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
           ARRAY_DISTINCT(ARRAY_CAT(grain, fkeys)) AS names,
           ARRAY_CAT(FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'), x -> ARRAY_CONTAINS(x, names)), ARRAY_SORT(FILTER(names, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type'))))) AS ranked,
           GET(FILTER(ranked, x -> NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code', 'batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type')) AND NOT ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS unknown_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS unclassified_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT())), 0)::VARCHAR AS not_applicable_attribute,
           GET(FILTER(totals, t -> ARRAY_SIZE(ARRAY_DISTINCT(t::ARRAY)) <> ARRAY_SIZE(t::ARRAY)
                      OR ARRAY_SIZE(ARRAY_EXCEPT(t::ARRAY, grain)) > 0 OR ARRAY_SIZE(t::ARRAY) >= ARRAY_SIZE(grain)), 0)::ARRAY AS bad_total,
           NOT ARRAY_CONTAINS('item_type'::VARIANT, fkeys) AS scope_on,
           FILTER(grain, x -> ARRAY_CONTAINS(x, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code'))) AS conformed,
           ARRAY_DISTINCT(ARRAY_APPEND(ARRAY_CAT(grain, fkeys), 'item_type')) AS used,
           ARRAY_PREPEND(totals, grain) AS grains,
           FILTER(ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'item_type'), x -> ARRAY_CONTAINS(x, used)) AS fanout_attrs
    FROM s1, fa
),
gx AS (
    SELECT f.index AS n, f.value::ARRAY AS gs, s2.grain AS grain, s2.scope_on AS scope_on
    FROM s2, TABLE(FLATTEN(INPUT => s2.grains)) f
),
gt AS (
    SELECT LISTAGG(cte_text, '') WITHIN GROUP (ORDER BY n) AS g_ctes,
           LISTAGG(sel_text, '\nUNION ALL\n') WITHIN GROUP (ORDER BY n) AS g_selects,
           LISTAGG(tg_text, '') WITHIN GROUP (ORDER BY n) AS g_tg
    FROM (SELECT n, ',\ns' || n::VARCHAR || ' AS (SELECT as_of_month' || ARRAY_TO_STRING(TRANSFORM(gs, x -> ', ' || x::VARCHAR), '') || ', SUM(stock_qty) AS stock_qty FROM stock GROUP BY ALL),\n' || 'f' || n::VARCHAR || ' AS (SELECT as_of_month' || ARRAY_TO_STRING(TRANSFORM(ARRAY_INTERSECTION(gs, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code')), x -> ', ' || x::VARCHAR), '') || ', k, SUM(fc_qty) AS fc_qty FROM fc GROUP BY ALL),\n' || 'm' || n::VARCHAR || ' AS (\n        SELECT as_of_month' || ARRAY_TO_STRING(TRANSFORM(gs, x -> ', ' || x::VARCHAR), '') || ' FROM s' || n::VARCHAR || IFF(FALSE OR ARRAY_SIZE(ARRAY_INTERSECTION(gs, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code'))) = ARRAY_SIZE(gs), '\n        UNION\n        SELECT as_of_month' || ARRAY_TO_STRING(TRANSFORM(gs, x -> ', ' || x::VARCHAR), '') || ' FROM f' || n::VARCHAR, '') || '\n),\n' || 'i' || n::VARCHAR || ' AS (
    SELECT x.as_of_month' || ARRAY_TO_STRING(TRANSFORM(gs, x -> ', x.' || x::VARCHAR), '') || ', COUNT(DISTINCT x.item_id) AS n_items, COUNT(DISTINCT it.dimension) AS n_dims,
           MIN(it.base_unit) AS base_unit, MIN(it.native_unit) AS native_unit
    FROM (SELECT as_of_month' || ARRAY_TO_STRING(TRANSFORM(gs, x -> ', ' || x::VARCHAR), '') || ', item_id FROM stock_rows WHERE ' || IFF(scope_on, 'scope_value IN (SELECT f.value::VARCHAR FROM req, TABLE(FLATTEN(INPUT => req.r:scope)) f)', 'TRUE') || '
          UNION
          SELECT mb.as_of_month' || ARRAY_TO_STRING(TRANSFORM(gs, x -> ', mb.' || x::VARCHAR), '') || ', x.item_id FROM m' || n::VARCHAR || ' mb JOIN fc_rows x ON x.as_of_month = mb.as_of_month' || ARRAY_TO_STRING(TRANSFORM(ARRAY_INTERSECTION(gs, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code')), x -> ' AND EQUAL_NULL(x.' || x::VARCHAR || ', mb.' || x::VARCHAR || ')'), '') || ') x
    JOIN items it ON it.item_id = x.item_id
    GROUP BY ALL
),
' || 'd' || n::VARCHAR || ' AS (\n    SELECT mb.*, m.k, COALESCE(s.stock_qty, 0) AS stock_qty, COALESCE(f.fc_qty, 0) AS fc_qty\n' || '    FROM (SELECT m0.*, i.n_items, i.n_dims, i.base_unit, i.native_unit FROM m' || n::VARCHAR || ' m0 LEFT JOIN i' || n::VARCHAR || ' i ON i.as_of_month = m0.as_of_month' || ARRAY_TO_STRING(TRANSFORM(gs, x -> ' AND EQUAL_NULL(i.' || x::VARCHAR || ', m0.' || x::VARCHAR || ')'), '') || ') mb CROSS JOIN months m
' || '    LEFT JOIN s' || n::VARCHAR || ' s ON s.as_of_month = mb.as_of_month' || ARRAY_TO_STRING(TRANSFORM(gs, x -> ' AND EQUAL_NULL(s.' || x::VARCHAR || ', mb.' || x::VARCHAR || ')'), '') || '\n' || '    LEFT JOIN f' || n::VARCHAR || ' f ON f.as_of_month = mb.as_of_month AND f.k = m.k' || ARRAY_TO_STRING(TRANSFORM(ARRAY_INTERSECTION(gs, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code')), x -> ' AND EQUAL_NULL(f.' || x::VARCHAR || ', mb.' || x::VARCHAR || ')'), '') || '\n),\n' || 'c' || n::VARCHAR || ' AS (\n    SELECT *, SUM(fc_qty) OVER (PARTITION BY as_of_month' || ARRAY_TO_STRING(TRANSFORM(gs, x -> ', ' || x::VARCHAR), '') || ' ORDER BY k ROWS UNBOUNDED PRECEDING) AS cum_fc\n    FROM d' || n::VARCHAR || '\n)' AS cte_text, 'SELECT ''' || IFF(n = 0, 'DETAIL', 'TOTAL') || ''' AS row_type, ' || n::VARCHAR || ' AS grain_set, as_of_month' || ARRAY_TO_STRING(TRANSFORM(grain, x -> ', ' || IFF(ARRAY_CONTAINS(x, gs), '', 'NULL AS ') || x::VARCHAR), '') || ',\n' || '       ANY_VALUE(stock_qty) AS stock, MAX(cum_fc) AS forecast_over_horizon,\n       CASE\n         WHEN ANY_VALUE(stock_qty) = 0 THEN 0\n         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN\n              SUM(CASE WHEN cum_fc - fc_qty >= stock_qty THEN 0\n                       WHEN cum_fc <= stock_qty THEN 1\n                       ELSE (stock_qty - (cum_fc - fc_qty)) / fc_qty END)\n         WHEN MAX(cum_fc) = 0 THEN NULL\n         ELSE ANY_VALUE(stock_qty) / AVG(NULLIF(fc_qty, 0))\n       END AS coverage_months,\n       CASE\n         WHEN ANY_VALUE(stock_qty) = 0 THEN ''NO_STOCK''\n         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN NULL\n         WHEN MAX(cum_fc) = 0 THEN ''NO_DEMAND''\n         ELSE ''BEYOND_HORIZON''\n       END AS flag,\n       ANY_VALUE(n_items) AS n_items, ANY_VALUE(n_dims) AS n_dims, ANY_VALUE(base_unit) AS base_unit,\n       ANY_VALUE(native_unit) AS native_unit\n' || 'FROM c' || n::VARCHAR || ' GROUP BY as_of_month' || ARRAY_TO_STRING(TRANSFORM(gs, x -> ', ' || x::VARCHAR), '') AS sel_text, IFF(n = 0, '', ' WHEN ' || n::VARCHAR || ' THEN ARRAY_CONSTRUCT(' || ARRAY_TO_STRING(TRANSFORM(gs, x -> '''' || x::VARCHAR || ''''), ', ') || ')') AS tg_text FROM gx)
)
SELECT ',\nstock AS (\n    SELECT as_of_month' || ARRAY_TO_STRING(TRANSFORM(grain, x -> ', ' || x::VARCHAR), '') || ', SUM(qty) AS stock_qty\n    FROM stock_rows WHERE ' || IFF(scope_on, 'scope_value IN (SELECT f.value::VARCHAR FROM req, TABLE(FLATTEN(INPUT => req.r:scope)) f)', 'TRUE') || '\n    GROUP BY ALL\n),\nfc AS (\n    SELECT as_of_month' || ARRAY_TO_STRING(TRANSFORM(ARRAY_INTERSECTION(grain, ARRAY_CONSTRUCT('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code')), x -> ', ' || x::VARCHAR), '') || ', k, SUM(qty) AS fc_qty\n    FROM fc_rows\n    GROUP BY ALL\n)' || g_ctes || ',\ncr AS (\n' || g_selects || '\n)' || REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(',
r1 AS (
    SELECT cr.*, CASE ''<<BASIS>>'' WHEN ''NATIVE'' THEN IFF(n_items = 1, native_unit, NULL) WHEN ''QTY_EQ'' THEN IFF(n_dims = 1, base_unit, NULL) WHEN ''VALUE'' THEN ''EUR'' END AS stock_unit,
           IFF(coverage_months IS NULL OR flag IN (''NO_DEMAND'', ''BEYOND_HORIZON''), NULL, DATEADD(month, CEIL(coverage_months)::INT, as_of_month)) AS stockout_month,
           <<ON>> AND row_type = ''DETAIL'' AND COALESCE(flag IN (''NO_STOCK'', ''NO_DEMAND''), FALSE) AS apart,
           <<ON>> AND row_type = ''DETAIL'' AND NOT COALESCE(flag IN (''NO_STOCK'', ''NO_DEMAND''), FALSE)<<COND>> AS candidate
    FROM cr
),
r2 AS (
    SELECT r1.*, IFF(candidate, ROW_NUMBER() OVER (PARTITION BY as_of_month, candidate ORDER BY coverage_months ASC<<ORDER>>), NULL) AS rk
    FROM r1
),
r3 AS (
    SELECT r2.*, candidate AND <<RANK>> AS kept FROM r2
    WHERE NOT <<ON>> OR row_type <> ''DETAIL'' OR apart OR (candidate AND <<RANK>>)
),
r4 AS (
    SELECT r3.*, COUNT_IF(kept) OVER (PARTITION BY as_of_month) AS kept_count,
           SUM(IFF(kept, stock, NULL)) OVER (PARTITION BY as_of_month, stock_unit) AS kept_stock
    FROM r3
),
ret AS (SELECT * FROM r4 WHERE NOT apart),
val AS (SELECT COALESCE(MAX(n_items), 0) AS mi, COALESCE(MAX(n_dims), 0) AS md FROM ret),
km AS (SELECT as_of_month, COUNT_IF(kept) AS kept FROM r4 GROUP BY as_of_month),
ku AS (
    SELECT as_of_month, ARRAY_AGG(OBJECT_CONSTRUCT(''unit'', stock_unit, ''amount'', kept_stock)) WITHIN GROUP (ORDER BY stock_unit) AS stock
    FROM (SELECT DISTINCT as_of_month, stock_unit, kept_stock FROM r4 WHERE kept) GROUP BY as_of_month
),
ka AS (
    SELECT as_of_month, flag, COUNT(*) AS n, ARRAY_AGG(<<MEMBER>>) WITHIN GROUP (ORDER BY <<GORDER>>) AS members
    FROM r4 WHERE apart GROUP BY as_of_month, flag
),
sel AS (
    SELECT ARRAY_AGG(OBJECT_CONSTRUCT_KEEP_NULL(''as_of_month'', TO_VARCHAR(am.as_of_month, ''YYYY-MM-DD''), ''kept'', COALESCE(km.kept, 0),
               ''stock'', IFF(<<NOSUM>> AND COALESCE(km.kept, 0) > 1, NULL, COALESCE(ku.stock, ARRAY_CONSTRUCT())),
               ''set_apart'', OBJECT_CONSTRUCT(''NO_STOCK'', OBJECT_CONSTRUCT(''count'', COALESCE(a0.n, 0), ''members'', COALESCE(a0.members, ARRAY_CONSTRUCT())), ''NO_DEMAND'', OBJECT_CONSTRUCT(''count'', COALESCE(a1.n, 0), ''members'', COALESCE(a1.members, ARRAY_CONSTRUCT()))))) WITHIN GROUP (ORDER BY am.as_of_month) AS by_month
    FROM analysis_months am
    LEFT JOIN km ON km.as_of_month = am.as_of_month
    LEFT JOIN ku ON ku.as_of_month = am.as_of_month
    LEFT JOIN ka a0 ON a0.as_of_month = am.as_of_month AND a0.flag = ''NO_STOCK''
    LEFT JOIN ka a1 ON a1.as_of_month = am.as_of_month AND a1.flag = ''NO_DEMAND''
)
SELECT OBJECT_CONSTRUCT(
           ''COVERAGE_ROWS'', COALESCE((SELECT ARRAY_AGG(<<ROWOBJ>>) WITHIN GROUP (ORDER BY as_of_month, grain_set, rk NULLS LAST<<ROWORDER>>) FROM ret), ARRAY_CONSTRUCT()),
           ''ROW_COUNT'', (SELECT COUNT(*) FROM ret),
           ''FLAGS'', COALESCE((SELECT ARRAY_AGG(DISTINCT flag) WITHIN GROUP (ORDER BY flag) FROM ret), ARRAY_CONSTRUCT()),
           ''SELECTION'', IFF(<<ON>>, OBJECT_CONSTRUCT(''by_month'', sel.by_month), NULL),
           ''BASIS_REASON'', IFF(CASE ''<<BASIS>>'' WHEN ''NATIVE'' THEN val.mi <= 1 WHEN ''QTY_EQ'' THEN val.md <= 1 WHEN ''VALUE'' THEN TRUE END, NULL, ''Coverage is always in months, but on '' || (''<<BASIS>>'') || '' '' || (CASE ''<<BASIS>>'' WHEN ''NATIVE'' THEN ''at least one row or total adds several items, each counted in its own unit (packs of different sizes)'' WHEN ''QTY_EQ'' THEN ''at least one row or total adds kg and L (items of different dimensions)'' WHEN ''VALUE'' THEN ''never (a value adds up across every item)'' ELSE NULL END) || '', so stock and forecast cannot be summed for this request. Bases allowed for this request: '' || (ARRAY_TO_STRING(ARRAY_CONSTRUCT_COMPACT(IFF(val.mi <= 1, ''NATIVE'', NULL), IFF(val.md <= 1, ''QTY_EQ'', NULL), ''VALUE''), '', '')) || ''.'')) AS CV
FROM sel, val', '<<BASIS>>', basis), '<<ON>>', IFF(sel_on, 'TRUE', 'FALSE')), '<<COND>>', IFF(sel_below IS NULL, '', ' AND coverage_months > 0 AND coverage_months <= ' || TO_VARCHAR(sel_below)) || IFF(sel_above IS NULL, '', ' AND coverage_months > ' || TO_VARCHAR(sel_above))), '<<RANK>>', IFF(sel_rank IS NULL, 'TRUE', 'rk <= ' || TO_VARCHAR(sel_rank))), '<<ORDER>>', ARRAY_TO_STRING(TRANSFORM(grain, x -> ', ' || x::VARCHAR || ' ASC NULLS LAST'), '')), '<<GORDER>>', ARRAY_TO_STRING(TRANSFORM(grain, x -> x::VARCHAR || ' ASC NULLS LAST'), ', ')), '<<MEMBER>>', 'OBJECT_CONSTRUCT_KEEP_NULL(' || ARRAY_TO_STRING(TRANSFORM(grain, x -> '''' || x::VARCHAR || ''', ' || x::VARCHAR), ', ') || ')'), '<<ROWORDER>>', ARRAY_TO_STRING(TRANSFORM(grain, x -> ', ' || x::VARCHAR || ' NULLS LAST'), '')), '<<NOSUM>>', IFF(ARRAY_CONTAINS(basis::VARIANT, ARRAY_CONSTRUCT('NATIVE')), 'TRUE', 'FALSE')), '<<ROWOBJ>>', IFF(ARRAY_SIZE(grains) > 1, 'IFF(grain_set = 0, ' || 'OBJECT_CONSTRUCT_KEEP_NULL(''row_type'', row_type, ''as_of_month'', TO_VARCHAR(as_of_month, ''YYYY-MM-DD'')' || ARRAY_TO_STRING(TRANSFORM(grain, x -> ', ''' || x::VARCHAR || ''', ' || x::VARCHAR), '') || ', ''coverage_months'', coverage_months, ''stock'', stock, ''forecast_over_horizon'', forecast_over_horizon, ''stock_unit'', stock_unit, ''stockout_month'', TO_VARCHAR(stockout_month, ''YYYY-MM-DD''), ''flag'', flag)' || ', OBJECT_INSERT(' || 'OBJECT_CONSTRUCT_KEEP_NULL(''row_type'', row_type, ''as_of_month'', TO_VARCHAR(as_of_month, ''YYYY-MM-DD'')' || ARRAY_TO_STRING(TRANSFORM(grain, x -> ', ''' || x::VARCHAR || ''', ' || x::VARCHAR), '') || ', ''coverage_months'', coverage_months, ''stock'', stock, ''forecast_over_horizon'', forecast_over_horizon, ''stock_unit'', stock_unit, ''stockout_month'', TO_VARCHAR(stockout_month, ''YYYY-MM-DD''), ''flag'', flag)' || ', ''total_grain'', CASE grain_set' || g_tg || ' END))', 'OBJECT_CONSTRUCT_KEEP_NULL(''row_type'', row_type, ''as_of_month'', TO_VARCHAR(as_of_month, ''YYYY-MM-DD'')' || ARRAY_TO_STRING(TRANSFORM(grain, x -> ', ''' || x::VARCHAR || ''', ' || x::VARCHAR), '') || ', ''coverage_months'', coverage_months, ''stock'', stock, ''forecast_over_horizon'', forecast_over_horizon, ''stock_unit'', stock_unit, ''stockout_month'', TO_VARCHAR(stockout_month, ''YYYY-MM-DD''), ''flag'', flag)')) AS T FROM s2, gt
    ));
    -- ---- the as_of_months checks, one statement that reads no table (also the caller block)
    SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) INTO :pre FROM (
WITH a AS (
    SELECT :AS_OF_MONTHS AS raw, TRIM(raw, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)) AS s, LEFT(s, 1) IN ('[', '{') AS is_json,
           IFF(is_json, TRY_PARSE_JSON(s, 'd'), NULL) AS j,
           raw IS NULL OR s IN ('', '[]', 'null') AS missing0,
           is_json AND NOT COALESCE(IS_ARRAY(j), FALSE) AS bad_json,
           CASE WHEN missing0 OR bad_json THEN ARRAY_CONSTRUCT()
                WHEN is_json THEN j::ARRAY
                ELSE FILTER(TRANSFORM(SPLIT(s, ','), x -> TRIM(x::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))::VARIANT), x -> x::VARCHAR <> '') END AS items,
           TRANSFORM(items, it -> CASE TYPEOF(it)
                 WHEN 'VARCHAR' THEN TRIM(it::VARCHAR, ' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13))::VARIANT
                 WHEN 'INTEGER' THEN it::VARCHAR::VARIANT
                 WHEN 'BOOLEAN' THEN IFF(it::BOOLEAN, 'True', 'False')::VARIANT
                 ELSE OBJECT_CONSTRUCT('bad', CASE WHEN TYPEOF(it) IN ('ARRAY', 'OBJECT') THEN TO_JSON(it)
                                                   WHEN TYPEOF(it) = 'NULL_VALUE' THEN 'None' ELSE RTRIM(RTRIM(TO_VARCHAR(it::FLOAT, 'FM999,999,999,999,999,999,990.0000'), '0'), '.') END)::VARIANT END) AS texts,
           TRANSFORM(texts, x -> CASE WHEN IS_OBJECT(x) THEN x
                 WHEN UPPER(x::VARCHAR) = 'LATEST' THEN 'LATEST'::VARIANT
                 WHEN REGEXP_LIKE(x::VARCHAR, '\\d{4}-\\d{2}-\\d{2}') AND TRY_TO_DATE(x::VARCHAR, 'YYYY-MM-DD') IS NOT NULL THEN x
                 ELSE OBJECT_CONSTRUCT('bad', x)::VARIANT END) AS checked,
           missing0 OR (NOT bad_json AND ARRAY_SIZE(items) = 0) AS missing,
           IFF(bad_json, raw, GET(GET(FILTER(checked, x -> IS_OBJECT(x)), 0), 'bad')::VARCHAR) AS invalid,
           TRANSFORM(FILTER(ARRAY_GENERATE_RANGE(0, ARRAY_SIZE(checked)), i -> ARRAY_POSITION(GET(checked, i::INT), checked) = i::INT), i -> GET(checked, i::INT)) AS parsed,
           GET(FILTER(checked, x -> NOT IS_OBJECT(x) AND x::VARCHAR <> 'LATEST' AND RIGHT(x::VARCHAR, 2) <> '01'), 0)::VARCHAR AS not_month_start
),
caller AS (
SELECT CURRENT_ROLE() AS CALLER_ROLE, CURRENT_SECONDARY_ROLES() AS CALLER_SECONDARY_ROLES, CURRENT_USER() AS CALLER_USER, SYS_CONTEXT('SNOWFLAKE$CURRENT', 'IS_AGENT_ACTIVATED')::VARCHAR AS AGENT_ACTIVATED
)
SELECT caller.*, CASE WHEN missing THEN 'AS_OF_MISSING' WHEN invalid IS NOT NULL THEN 'AS_OF_INVALID' WHEN not_month_start IS NOT NULL THEN 'AS_OF_NOT_MONTH_START' WHEN ARRAY_SIZE(parsed) > 24 THEN 'AS_OF_TOO_MANY' END AS RCODE, CASE WHEN missing THEN 'An analysis month is required. Coverage is a point-in-time measure: give one or more months as YYYY-MM-01. It is never summed or averaged over several months.' WHEN invalid IS NOT NULL THEN 'as_of_months value ''' || (invalid) || ''' is not a date in YYYY-MM-01 form, nor LATEST.' WHEN not_month_start IS NOT NULL THEN '''' || (not_month_start) || ''' is not the first day of a month. Coverage is monthly: use ' || (LEFT(not_month_start, 8) || '01') || ' for that month.' WHEN ARRAY_SIZE(parsed) > 24 THEN 'At most ' || ('24') || ' analysis months per call.' END AS REASON, parsed AS PARSED
FROM a, caller
    );
    IF (pre:RCODE::VARCHAR IS NOT NULL) THEN
      rcode := pre:RCODE::VARCHAR;
      reason := pre:REASON::VARCHAR;
      RAISE refused;
    END IF;
    -- ---- the context statement: context, analysis months, horizon
    parsed_json := TO_JSON(pre:PARSED);
    t1 := CURRENT_TIMESTAMP();
    rs_k := ASYNC (SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) AS K FROM (
WITH ctx AS (
WITH snaps AS (SELECT DISTINCT snapshot_month AS m FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT),
reach AS (SELECT (SELECT MAX(month_start) FROM LINKML_METRICS.RAW.DIM_CALENDAR) AS cal_max, (SELECT MAX(forecast_month) FROM LINKML_METRICS.RAW.FCT_FORECAST) AS fc_max)
SELECT CURRENT_ROLE() AS CALLER_ROLE, CURRENT_SECONDARY_ROLES() AS CALLER_SECONDARY_ROLES, CURRENT_USER() AS CALLER_USER, SYS_CONTEXT('SNOWFLAKE$CURRENT', 'IS_AGENT_ACTIVATED')::VARCHAR AS AGENT_ACTIVATED,
       (SELECT ARRAY_AGG(TO_VARCHAR(m)) FROM snaps) AS SNAPSHOTS,
       (SELECT ARRAY_AGG(TO_VARCHAR(m)) FROM snaps, reach WHERE reach.cal_max >= DATEADD(month, 24, m)
           AND reach.fc_max >= DATEADD(month, 24, m)) AS AVAILABLE,
       (SELECT COUNT(*) - COUNT(DISTINCT country_id) FROM LINKML_METRICS.RAW.DIM_GEO) AS QE_GEO_GRAIN,
       (SELECT COUNT(*) - COUNT(DISTINCT batch_id) FROM LINKML_METRICS.RAW.DIM_BATCH) AS QE_BATCH_GRAIN,
       (SELECT COUNT(*) - COUNT(DISTINCT warehouse_id) FROM LINKML_METRICS.RAW.DIM_WAREHOUSE) AS QE_WAREHOUSE_GRAIN,
       (SELECT COUNT(*) - COUNT(DISTINCT month_start) FROM LINKML_METRICS.RAW.DIM_CALENDAR) AS QE_CALENDAR_GRAIN,
       ((SELECT COUNT(*) FROM (SELECT sku_code FROM LINKML_METRICS.RAW.DIM_ITEM GROUP BY sku_code HAVING COUNT(DISTINCT family_code) > 1)) + (SELECT COUNT(*) FROM (SELECT family_code FROM LINKML_METRICS.RAW.DIM_ITEM GROUP BY family_code HAVING COUNT(DISTINCT range_code) > 1))) AS QE_SKU_FAMILY,
       ((SELECT COUNT(*) FROM (SELECT country_code FROM LINKML_METRICS.RAW.DIM_GEO GROUP BY country_code HAVING COUNT(DISTINCT region_code) > 1))) AS QE_COUNTRY_REGION,
       GREATEST(0, DATEDIFF(month, (SELECT MAX(month_start) FROM LINKML_METRICS.RAW.DIM_CALENDAR), DATEADD(month, 24, (SELECT MAX(snapshot_month) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT)))) AS QE_HORIZON_LOADED,
       GREATEST(0, DATEDIFF(month, (SELECT MAX(forecast_month) FROM LINKML_METRICS.RAW.FCT_FORECAST), DATEADD(month, 24, (SELECT MAX(snapshot_month) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT)))) AS QE_FORECAST_REACH
),
b AS (
    SELECT ctx.*, PARSE_JSON(:parsed_json) AS parsed, :BASIS AS basis_raw, :COVERAGE_BELOW AS below_raw,
           :COVERAGE_ABOVE AS above_raw, :RANK_FIRST AS rank_raw, :GRAIN AS grain_raw, :FILTERS AS filters_raw,
           :TOTALS AS totals_raw,
           ARRAY_SORT(COALESCE(ctx.SNAPSHOTS, ARRAY_CONSTRUCT())) AS snaps,
           ARRAY_SORT(COALESCE(ctx.AVAILABLE, ARRAY_CONSTRUCT())) AS avail,
           GET(avail, ARRAY_SIZE(avail) - 1)::VARCHAR AS latest,
           GET(snaps, ARRAY_SIZE(snaps) - 1)::VARCHAR AS latest_snapshot
    FROM ctx
),
mm AS (
    SELECT f.index AS i, f.value::VARCHAR AS tok, IFF(tok = 'LATEST', b.latest, tok) AS d,
           CASE WHEN tok = 'LATEST' AND b.latest IS NULL
                  THEN OBJECT_CONSTRUCT('value', tok, 'latest', 'none', 'available', 'none')
                WHEN NOT ARRAY_CONTAINS(d::VARIANT, b.snaps)
                  THEN OBJECT_CONSTRUCT('value', d, 'latest', COALESCE(b.latest, 'None'), 'available', ARRAY_TO_STRING(b.avail, ', '))
           END AS bad
    FROM b, TABLE(FLATTEN(INPUT => b.parsed)) f
),
mfirst AS (SELECT d, MIN(i) AS i FROM mm GROUP BY d),
mres AS (
    SELECT (SELECT MIN_BY(bad, i) FROM mm WHERE bad IS NOT NULL) AS bad_month,
           (SELECT ARRAY_AGG(d) WITHIN GROUP (ORDER BY i) FROM mfirst WHERE d IS NOT NULL) AS months,
           (SELECT MIN_BY(mfirst.d, mfirst.i) FROM mfirst, b WHERE mfirst.d IS NOT NULL
                AND NOT ARRAY_CONTAINS(mfirst.d::VARIANT, b.avail)) AS month_out_of_horizon
)
SELECT CALLER_ROLE, CALLER_SECONDARY_ROLES, CALLER_USER, AGENT_ACTIVATED,
       GET(avail, 0)::VARCHAR AS AVAILABLE_FIRST, latest AS AVAILABLE_LATEST,
       CASE WHEN bad_month IS NOT NULL THEN 'AS_OF_NO_SNAPSHOT' WHEN (COALESCE(QE_HORIZON_LOADED, 0) <> 0) OR (COALESCE(QE_FORECAST_REACH, 0) <> 0) OR (month_out_of_horizon IS NOT NULL) THEN 'HORIZON_NOT_LOADED' END AS RCODE, CASE WHEN bad_month IS NOT NULL THEN 'There is no stock snapshot for ' || (bad_month:value::VARCHAR) || '. Available months: ' || (bad_month:available::VARCHAR) || ' (LATEST = ' || (bad_month:latest::VARCHAR) || ').' WHEN (COALESCE(QE_HORIZON_LOADED, 0) <> 0) OR (COALESCE(QE_FORECAST_REACH, 0) <> 0) OR (month_out_of_horizon IS NOT NULL) THEN CASE WHEN COALESCE(QE_HORIZON_LOADED, 0) <> 0 THEN 'The ' || ('calendar') || ' does not reach ' || (TO_VARCHAR(DATE_TRUNC('month', DATEADD('month', 24, latest_snapshot::DATE)), 'YYYY-MM-DD')) || ', the end of the ' || ('24') || '-month horizon of ' || (latest_snapshot) || '.' WHEN COALESCE(QE_FORECAST_REACH, 0) <> 0 THEN 'The ' || ('forecast') || ' does not reach ' || (TO_VARCHAR(DATE_TRUNC('month', DATEADD('month', 24, latest_snapshot::DATE)), 'YYYY-MM-DD')) || ', the end of the ' || ('24') || '-month horizon of ' || (latest_snapshot) || '.' WHEN month_out_of_horizon IS NOT NULL THEN 'The ' || ('calendar or forecast') || ' does not reach ' || (TO_VARCHAR(DATE_TRUNC('month', DATEADD('month', 24, month_out_of_horizon::DATE)), 'YYYY-MM-DD')) || ', the end of the ' || ('24') || '-month horizon of ' || (month_out_of_horizon) || '.' END END AS REASON, CASE WHEN COALESCE(QE_GEO_GRAIN, 0) <> 0 THEN 'Quality expectation ' || ('QE_GEO_GRAIN') || ' fails (' || (QE_GEO_GRAIN::VARCHAR) || ' violations): ' || ('one row per country_id') || '. No number is returned until it is fixed.' WHEN COALESCE(QE_BATCH_GRAIN, 0) <> 0 THEN 'Quality expectation ' || ('QE_BATCH_GRAIN') || ' fails (' || (QE_BATCH_GRAIN::VARCHAR) || ' violations): ' || ('one row per batch_id') || '. No number is returned until it is fixed.' WHEN COALESCE(QE_WAREHOUSE_GRAIN, 0) <> 0 THEN 'Quality expectation ' || ('QE_WAREHOUSE_GRAIN') || ' fails (' || (QE_WAREHOUSE_GRAIN::VARCHAR) || ' violations): ' || ('one row per warehouse_id') || '. No number is returned until it is fixed.' WHEN COALESCE(QE_CALENDAR_GRAIN, 0) <> 0 THEN 'Quality expectation ' || ('QE_CALENDAR_GRAIN') || ' fails (' || (QE_CALENDAR_GRAIN::VARCHAR) || ' violations): ' || ('one row per month_start') || '. No number is returned until it is fixed.' WHEN COALESCE(QE_SKU_FAMILY, 0) <> 0 THEN 'Quality expectation ' || ('QE_SKU_FAMILY') || ' fails (' || (QE_SKU_FAMILY::VARCHAR) || ' violations): ' || ('each sku_code maps to one family_code and each family_code to one range_code') || '. No number is returned until it is fixed.' WHEN COALESCE(QE_COUNTRY_REGION, 0) <> 0 THEN 'Quality expectation ' || ('QE_COUNTRY_REGION') || ' fails (' || (QE_COUNTRY_REGION::VARCHAR) || ' violations): ' || ('each country_code maps to one region_code') || '. No number is returned until it is fixed.' END AS DQ_REASON, months AS MONTHS
FROM b, mres
    ));
    lineage := OBJECT_CONSTRUCT('context', SQLID);
    AWAIT rs_k;
    LET cur_k CURSOR FOR rs_k;
    OPEN cur_k;
    FETCH cur_k INTO plan;
    t2 := CURRENT_TIMESTAMP();
    IF (plan:RCODE::VARCHAR IS NOT NULL) THEN
      rcode := plan:RCODE::VARCHAR;
      reason := plan:REASON::VARCHAR;
      RAISE refused;
    END IF;
    AWAIT rs_p;
    LET cur_p CURSOR FOR rs_p;
    OPEN cur_p;
    FETCH cur_p INTO par;
    IF (par:RCODE::VARCHAR IS NOT NULL) THEN
      rcode := par:RCODE::VARCHAR;
      reason := par:REASON::VARCHAR;
      RAISE refused;
    END IF;
    AWAIT ALL;
    LET cur_b CURSOR FOR rs_b;
    OPEN cur_b;
    FETCH cur_b INTO base;
    LET cur_tq CURSOR FOR rs_tq;
    OPEN cur_tq;
    FETCH cur_tq INTO qsql;
    LET cur_tc CURSOR FOR rs_tc;
    OPEN cur_tc;
    FETCH cur_tc INTO csql;
    qsql := base || qsql;
    csql := base || csql;
    req := TO_JSON(OBJECT_CONSTRUCT('months', plan:MONTHS, 'filters', par:FILTERS, 'scope', ARRAY_CONSTRUCT('STANDARD')));
    -- ---- the quality and the coverage statements, started together
    t3 := CURRENT_TIMESTAMP();
    rs_q := ASYNC (EXECUTE IMMEDIATE :qsql USING (req));
    lineage := OBJECT_INSERT(lineage, 'quality', SQLID);
    rs_c := ASYNC (EXECUTE IMMEDIATE :csql USING (req));
    lineage := OBJECT_INSERT(lineage, 'coverage', SQLID);
    jobs_started := TRUE;
    AWAIT rs_q;
    LET cur_q CURSOR FOR rs_q;
    OPEN cur_q;
    FETCH cur_q INTO qv;
    t4 := CURRENT_TIMESTAMP();
    -- ---- data checks, in check_order
    IF (qv:FANOUT_REASON::VARCHAR IS NOT NULL) THEN
      rcode := 'MASTER_DATA_FANOUT';
      reason := qv:FANOUT_REASON::VARCHAR;
      RAISE refused;
    END IF;
    IF (plan:DQ_REASON::VARCHAR IS NOT NULL) THEN
      rcode := 'DATA_QUALITY_FAILED';
      reason := plan:DQ_REASON::VARCHAR;
      RAISE refused;
    END IF;
    AWAIT rs_c;
    LET cur_c CURSOR FOR rs_c;
    OPEN cur_c;
    FETCH cur_c INTO cv;
    t5 := CURRENT_TIMESTAMP();
    -- ---- the basis, judged on the rows the coverage statement returns
    IF (cv:BASIS_REASON::VARCHAR IS NOT NULL) THEN
      rcode := 'BASIS_NOT_COMPARABLE';
      reason := cv:BASIS_REASON::VARCHAR;
      RAISE refused;
    END IF;
  EXCEPTION
    WHEN refused THEN
      IF (jobs_started) THEN
        CANCEL rs_c;
      END IF;
      RETURN OBJECT_CONSTRUCT('status', 'refused', 'contract', OBJECT_CONSTRUCT('id', 'stock_coverage', 'version', '0.5.1'),
               'refusal', OBJECT_CONSTRUCT('code', rcode, 'reason', reason), 'available_months', IFF(plan IS NULL, NULL, OBJECT_CONSTRUCT_KEEP_NULL('first', plan:AVAILABLE_FIRST, 'last', plan:AVAILABLE_LATEST, 'latest', plan:AVAILABLE_LATEST)),
               'caller', OBJECT_CONSTRUCT_KEEP_NULL('current_role', pre:CALLER_ROLE, 'current_secondary_roles', pre:CALLER_SECONDARY_ROLES, 'current_user', pre:CALLER_USER, 'is_agent_activated', pre:AGENT_ACTIVATED), 'lineage', OBJECT_CONSTRUCT('query_ids', COALESCE(lineage, OBJECT_CONSTRUCT())),
               'timing_ms', OBJECT_CONSTRUCT_KEEP_NULL('context_ms', DATEDIFF('millisecond', t1, t2), 'quality_ms', DATEDIFF('millisecond', t3, t4),
                                                      'total_ms', DATEDIFF('millisecond', t0, CURRENT_TIMESTAMP())));
  END;
  RETURN OBJECT_CONSTRUCT('status', 'ok', 'contract', OBJECT_CONSTRUCT('id', 'stock_coverage', 'version', '0.5.1'),
           'request', OBJECT_CONSTRUCT_KEEP_NULL('as_of_months', plan:MONTHS, 'basis', par:BASIS, 'grain', par:GRAIN,
                                       'filters', par:FILTERS, 'totals', par:TOTALS, 'coverage_below', par:SEL_BELOW,
                                       'coverage_above', par:SEL_ABOVE, 'rank_first', par:SEL_RANK),
           'applicability', OBJECT_CONSTRUCT_KEEP_NULL('stock_and_forecast', par:STOCK_AND_FORECAST, 'stock_only', par:STOCK_ONLY,
                                                       'default_scope', IFF(par:SCOPE_ON::BOOLEAN,
                                                         OBJECT_CONSTRUCT('item_type', ARRAY_CONSTRUCT('STANDARD')), NULL)),
           'rows', COALESCE(cv:COVERAGE_ROWS, ARRAY_CONSTRUCT()), 'row_count', cv:ROW_COUNT,
           'flags', COALESCE(cv:FLAGS, ARRAY_CONSTRUCT()), 'warnings', COALESCE(qv:WARNINGS, ARRAY_CONSTRUCT()),
           'selection', cv:SELECTION,
           'note', 'A total is the metric recomputed at the coarser grain, never a sum or average of child coverages. The stock is aggregated to the total''s grain, the forecast to that grain projected onto its conformed attributes. Several analysis months give a series with no total across months (decision 4).', 'available_months', IFF(plan IS NULL, NULL, OBJECT_CONSTRUCT_KEEP_NULL('first', plan:AVAILABLE_FIRST, 'last', plan:AVAILABLE_LATEST, 'latest', plan:AVAILABLE_LATEST)), 'caller', OBJECT_CONSTRUCT_KEEP_NULL('current_role', pre:CALLER_ROLE, 'current_secondary_roles', pre:CALLER_SECONDARY_ROLES, 'current_user', pre:CALLER_USER, 'is_agent_activated', pre:AGENT_ACTIVATED),
           'lineage', OBJECT_CONSTRUCT('query_ids', lineage), 'timing_ms', OBJECT_CONSTRUCT('context_ms', DATEDIFF('millisecond', t1, t2), 'quality_ms', DATEDIFF('millisecond', t3, t4), 'coverage_ms', DATEDIFF('millisecond', t3, t5), 'total_ms', DATEDIFF('millisecond', t0, CURRENT_TIMESTAMP())));
END;
$$;
