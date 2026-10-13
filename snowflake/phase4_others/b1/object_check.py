"""Session 8, step 3: object check of LINKML_B1_SV through SEMANTIC_VIEW() (direct SQL, no agent, no grading): the
inputs the view returns for heroes (it cannot carry coverage: 010273), and the native defects it keeps. Perso, no
secondary role."""
import snowflake.connector

SV = "LINKML_METRICS.RAW.LINKML_B1_SV"
CASES = [  # (label, query body, expected)
    ("T1 stock PANTRY_FLOUR x FR, June 2026", "DIMENSIONS item.family_code, geo.country_code METRICS stock.stock_qty "
     "WHERE item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR' AND cal.month_start = '2026-06-01'", 1400),
    ("T1 c03 PANTRY_FLOUR x FR at June 2026 (filter outside)", "DIMENSIONS item.family_code, geo.country_code, "
     "cal.month_start, cal.month_index METRICS fc.c03 WHERE item.family_code = 'PANTRY_FLOUR' AND geo.country_code = 'FR'",
     1500),
    ("T7 stock PANTRY_OIL x SE, June 2026", "DIMENSIONS item.family_code METRICS stock.stock_qty WHERE "
     "item.family_code = 'PANTRY_OIL' AND geo.country_code = 'SE' AND cal.month_start = '2026-06-01'", 900),
    ("CS_LAST_MONTH_GAP SKU-H11 x CH, 2026-Q2", "DIMENSIONS item.sku_code METRICS stock.stock_qty WHERE "
     "item.sku_code = 'SKU-H11' AND geo.country_code = 'CH' AND cal.year_quarter = '2026-Q2'", 0),
    ("G1 forecast BEV_JUICE x FR, 2026-09", "DIMENSIONS item.family_code METRICS fc.forecast_qty WHERE "
     "item.family_code = 'BEV_JUICE' AND geo.country_code = 'FR' AND cal.month_start = '2026-09-01'", 6416),
]
con = snowflake.connector.connect(connection_name="perso")
cur = con.cursor()
for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH",
          "ALTER SESSION SET USE_CACHED_RESULT = FALSE"):
    cur.execute(s)
print("| Case | Returned | Expected | Match | Query id |\n|---|---|---|---|---|")
for label, body, exp in CASES:
    q = f"SELECT * FROM SEMANTIC_VIEW({SV} {body})"
    if "c03" in body:
        q = f"SELECT * FROM ({q}) WHERE month_start = '2026-06-01'"
    try:
        got = [r[-1] for r in cur.execute(q).fetchall()]
        ok = len(got) == 1 and got[0] is not None and abs(float(got[0]) - exp) < 1e-6
        print(f"| {label} | {got} | {exp} | {'yes' if ok else '**no**'} | `{cur.sfqid}` |")
    except snowflake.connector.errors.ProgrammingError as e:
        print(f"| {label} | error {e.errno}: {e.msg[:90]} | {exp} | **no** | `{e.sfqid}` |")
