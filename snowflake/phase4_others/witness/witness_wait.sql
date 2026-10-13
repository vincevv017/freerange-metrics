-- Session 8, step 1: the session 8a SQL Scripting witness with SYSTEM$WAIT(2) before its RETURN, so that the CALL
-- lasts about 2 s and the tool span shows which step it waits for between 1.2 and 4.3 s.
-- Run as LINKML_METRICS_ROLE with no secondary role (witness_wait.py create). Dropped after the traces are extracted.
USE SECONDARY ROLES NONE;
USE ROLE LINKML_METRICS_ROLE;

CREATE PROCEDURE LINKML_METRICS.RAW.WITNESS_SQL(LABEL VARCHAR)
RETURNS VARIANT LANGUAGE SQL EXECUTE AS CALLER
AS $$
BEGIN
  SELECT SYSTEM$WAIT(2);
  RETURN OBJECT_CONSTRUCT('status', 'ok', 'witness', 'sql_wait_2s');
END;
$$;
