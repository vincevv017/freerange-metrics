"""Session 8, step 2: object check of LINKML_B2_SV through SEMANTIC_VIEW() (direct SQL, no agent, no grading): the
hero values the generated objects should carry, and the fan-out they cannot refuse. Run as perso, no secondary role."""
import snowflake.connector

SV = "LINKML_METRICS.RAW.LINKML_B2_SV"
M = "calendar.month_start = '2026-06-01'"
CASES = [  # (label, dimensions, metric, where, expected)
    ("T1 PANTRY_FLOUR x FR", "item.family_code, geo.country_code", "coverage_months_qty_eq",
     f"item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR' AND {M} AND item.item_type = 'STANDARD'", 2.8),
    ("T2 SKU-H03 x DE", "item.sku_code, geo.country_code", "coverage_months_qty_eq",
     f"item.sku_code = 'SKU-H03' AND geo.country_code = 'DE' AND {M}", 7.0),
    ("T3 SKU-H04 x IT released", "item.sku_code", "coverage_months_qty_eq",
     f"item.sku_code = 'SKU-H04' AND geo.country_code = 'IT' AND status.batch_status = 'RELEASED' AND {M}", 6.0),
    ("T4 SKU-H05 x ES", "item.sku_code", "coverage_months_qty_eq", f"item.sku_code = 'SKU-H05' AND {M}", 8.5),
    ("T7 PANTRY_OIL x SE", "item.family_code", "coverage_months_qty_eq",
     f"item.family_code = 'PANTRY_OIL' AND geo.country_code = 'SE' AND {M}", 2.25),
    ("T8 SKU-H08 x NL", "item.sku_code", "coverage_months_qty_eq", f"item.sku_code = 'SKU-H08' AND {M}", 0.0),
    ("NO_DEMAND SKU-H09 x BE", "item.sku_code", "coverage_months_qty_eq", f"item.sku_code = 'SKU-H09' AND {M}", None),
    ("BEYOND_H SKU-H10 x PL", "item.sku_code", "coverage_months_qty_eq", f"item.sku_code = 'SKU-H10' AND {M}", 50.0),
    ("BULK_SCOPE HOT_GROUND, STANDARD", "item.family_code", "coverage_months_qty_eq",
     f"item.family_code = 'HOT_GROUND' AND item.item_type = 'STANDARD' AND {M}", 8.67354124748491),
    ("T9 SKU-H11 x CH", "item.sku_code", "coverage_months_qty_eq", f"item.sku_code = 'SKU-H11' AND {M}", 0.0),
    ("CS_LAST_MONTH_GAP SKU-H11 x CH Q2", "item.sku_code", "closing_stock_qty_eq",
     "item.sku_code = 'SKU-H11' AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2'", 0.0),
    ("CS_FAMILY SNACK_BARS x CH Q2", "item.family_code", "closing_stock_qty_eq",
     "item.family_code = 'SNACK_BARS' AND geo.country_code = 'CH' AND calendar.year_quarter = '2026-Q2'", 450.0),
    ("G1 BEV_JUICE x FR 2026-09", "item.family_code", "forecast_qty_eq",
     "item.family_code = 'BEV_JUICE' AND geo.country_code = 'FR' AND calendar.month_start = '2026-09-01'", 6416.0),
    ("G2 SE closing value 2026-06", "geo.country_code", "closing_stock_value",
     f"geo.country_code = 'SE' AND {M}", 14476855.4803),
]

con = snowflake.connector.connect(connection_name="perso")
cur = con.cursor()
for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH",
          "ALTER SESSION SET USE_CACHED_RESULT = FALSE"):
    cur.execute(s)
print("| Case | Returned | Expected | Match | Query id |\n|---|---|---|---|---|")
for label, dims, metric, where, exp in CASES:
    q = f"SELECT * FROM SEMANTIC_VIEW({SV} DIMENSIONS {dims} METRICS {metric} WHERE {where})"
    try:
        rows = cur.execute(q).fetchall()
        got = [r[-1] for r in rows]
        ok = len(got) == 1 and ((got[0] is None and exp is None) or (got[0] is not None and exp is not None
                                                                     and abs(float(got[0]) - exp) < 1e-6))
        print(f"| {label} | {got} | {exp} | {'yes' if ok else '**no**'} | `{cur.sfqid}` |")
    except snowflake.connector.errors.ProgrammingError as e:
        print(f"| {label} | error {e.errno}: {e.msg[:90]} | {exp} | **no** | `{e.sfqid}` |")
