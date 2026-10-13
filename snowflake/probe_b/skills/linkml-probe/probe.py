import snowflake.connector as sc; print(sc.connect().cursor().execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST").fetchall())
