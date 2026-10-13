-- Session 8a, latency witness: two empty procedures returning a fixed small JSON, no query.
-- Run as LINKML_METRICS_ROLE with no secondary role (witness.py create). Dropped at the end of the session.
USE SECONDARY ROLES NONE;
USE ROLE LINKML_METRICS_ROLE;

CREATE PROCEDURE LINKML_METRICS.RAW.WITNESS_SQL(LABEL VARCHAR)
RETURNS VARIANT LANGUAGE SQL EXECUTE AS CALLER
AS $$ BEGIN RETURN OBJECT_CONSTRUCT('status', 'ok', 'witness', 'sql'); END; $$;

CREATE PROCEDURE LINKML_METRICS.RAW.WITNESS_PY(LABEL VARCHAR)
RETURNS VARIANT LANGUAGE PYTHON RUNTIME_VERSION = '3.12'
PACKAGES = ('snowflake-snowpark-python') HANDLER = 'run' EXECUTE AS CALLER
AS $$
def run(session, label):
    return {"status": "ok", "witness": "python"}
$$;
