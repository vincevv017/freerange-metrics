"""
Session 8b, step 1: the four Snowflake Scripting behaviours the parity checklist leaves open, each measured in a
throwaway anonymous block (no object created), as perso, LINKML_METRICS_ROLE, no secondary role.

    python snowflake/phase4_c_sql/probe_scripting.py

M1  ASYNC around EXECUTE IMMEDIATE ... USING, assigned to a RESULTSET, read back with a cursor.
M2  The query id of an ASYNC child: SQLID right after the assignment, checked from OUTSIDE the block against
    INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION (the check reads history; the block never does).
M3  CANCEL on a child that has already finished, and on one still running.
M4  PARSE_JSON / TRY_PARSE_JSON on the malformed and edge inputs of the checklist; number-to-text in a VARIANT.
Docs: snowflake-scripting/asynchronous-child-jobs, /query-id, /resultsets, /exceptions (cited in results.md).
"""

from __future__ import annotations

import json
import os
import time

import snowflake.connector


def connect():
    con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"))
    c = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH",
              "ALTER SESSION SET USE_CACHED_RESULT = FALSE"):
        c.execute(s)
    return con, c


def block(c, body: str):
    try:
        c.execute("EXECUTE IMMEDIATE $$\n" + body + "\n$$")
        v = c.fetchone()[0]
        return {"ok": True, "result": json.loads(v) if isinstance(v, str) and v[:1] in "{[" else v, "query_id": c.sfqid}
    except snowflake.connector.errors.ProgrammingError as e:
        return {"ok": False, "errno": e.errno, "msg": str(e.msg)[:300], "query_id": c.sfqid}


M1 = """
DECLARE
  res RESULTSET;
  q VARCHAR DEFAULT 'SELECT /* m1 */ PARSE_JSON(?):a::INT AS x, ARRAY_SIZE(PARSE_JSON(?):b) AS n';
  j VARCHAR DEFAULT '{"a": 5, "b": [1, 2, 3]}';
  x INT; n INT;
BEGIN
  res := ASYNC (EXECUTE IMMEDIATE :q USING (j, j));
  AWAIT res;
  LET c1 CURSOR FOR res;
  OPEN c1;
  FETCH c1 INTO x, n;
  CLOSE c1;
  RETURN OBJECT_CONSTRUCT('x', x, 'n', n);
END;
"""

M2 = """
DECLARE
  r1 RESULTSET; r2 RESULTSET; r3 RESULTSET;
  q1 VARCHAR DEFAULT 'SELECT /* m2-a */ COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST WHERE forecast_month >= ?::DATE';
  q2 VARCHAR DEFAULT 'SELECT /* m2-b */ COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT WHERE snapshot_month = ?::DATE';
  d VARCHAR DEFAULT '2026-06-01';
  id_before VARCHAR; id1 VARCHAR; id2 VARCHAR; id3 VARCHAR; id_after VARCHAR; last1 VARCHAR;
BEGIN
  id_before := SQLID;
  r1 := ASYNC (EXECUTE IMMEDIATE :q1 USING (d));
  id1 := SQLID;
  r2 := ASYNC (EXECUTE IMMEDIATE :q2 USING (d));
  id2 := SQLID;
  AWAIT r1;
  id_after := SQLID;
  AWAIT r2;
  r3 := (EXECUTE IMMEDIATE 'SELECT /* m2-c sync */ 1');
  id3 := SQLID;
  RETURN OBJECT_CONSTRUCT_KEEP_NULL('id_before', id_before, 'id1', id1, 'id2', id2, 'id_after_await', id_after,
                                    'id3_sync', id3);
END;
"""

M3_FINISHED = """
DECLARE
  r RESULTSET;
BEGIN
  r := ASYNC (SELECT /* m3-finished */ 1 AS x);
  AWAIT r;
  CANCEL r;
  RETURN 'cancelled a finished child without error';
END;
"""

M3_RUNNING = """
DECLARE
  r RESULTSET;
  id VARCHAR;
BEGIN
  r := ASYNC (SELECT /* m3-running */ SYSTEM$WAIT(5) AS x);
  id := SQLID;
  CANCEL r;
  RETURN OBJECT_CONSTRUCT('id', id, 'status_after_cancel', SYSTEM$GET_RESULTSET_STATUS(r));
END;
"""

M3_PENDING_AT_RETURN = """
DECLARE
  r RESULTSET;
  id VARCHAR;
BEGIN
  r := ASYNC (SELECT /* m3-pending */ SYSTEM$WAIT(3) AS x);
  id := SQLID;
  RETURN id;
END;
"""

M4_CASES = ['["2026-06-01"', 'June 2026', '["2026-06-01"]', '[ ]', '{"a": 1, "a": 2}', '[NaN]', "['x']",
            '[1,]', '{"family_code": ["X"],}', '[1, 1.0, 2026.5, 1e16, true, null, [1, 2], {"k": "v"}]', '"str"']


def m4(c):
    out = []
    for s in M4_CASES:
        r = {"input": s}
        c.execute("SELECT TRY_PARSE_JSON(%s), TYPEOF(TRY_PARSE_JSON(%s))", (s, s))
        v, t = c.fetchone()
        r["try_parse"], r["typeof"] = v, t
        try:
            c.execute("SELECT TO_JSON(PARSE_JSON(%s))", (s,))
            r["parse_json"] = c.fetchone()[0]
        except snowflake.connector.errors.ProgrammingError as e:
            r["parse_json"] = f"error {e.errno}: {str(e.msg)[:120]}"
        try:
            c.execute("SELECT TO_JSON(PARSE_JSON(%s, 'd'))", (s,))
            r["parse_json_d"] = c.fetchone()[0]
        except snowflake.connector.errors.ProgrammingError as e:
            r["parse_json_d"] = f"error {e.errno}: {str(e.msg)[:120]}"
        out.append(r)
    c.execute("""SELECT f.index, TYPEOF(f.value), f.value::STRING, TO_JSON(f.value), IS_INTEGER(f.value),
                        IS_DECIMAL(f.value), IS_DOUBLE(f.value), IS_BOOLEAN(f.value)
                 FROM TABLE(FLATTEN(PARSE_JSON('[1, 1.0, 2026.5, 1e16, 0.1, 51475.5, true, null, "s"]'))) f ORDER BY 1""")
    numbers = [dict(zip(["index", "typeof", "as_string", "to_json", "is_integer", "is_decimal", "is_double",
                         "is_boolean"], row)) for row in c.fetchall()]
    c.execute("SELECT OBJECT_CONSTRUCT('a', NULL, 'b', 1), OBJECT_CONSTRUCT_KEEP_NULL('a', NULL, 'b', 1)")
    keep = c.fetchone()
    return {"cases": out, "numbers": numbers, "object_construct": keep[0], "object_construct_keep_null": keep[1]}


def history(c, marker_ids):
    time.sleep(2)
    c.execute("SELECT query_id, LEFT(query_text, 80), execution_status, total_elapsed_time FROM TABLE("
              "LINKML_METRICS.INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(SESSION_ID => CURRENT_SESSION()::NUMBER, "
              "RESULT_LIMIT => 200)) WHERE query_text ILIKE '%/* m%' ORDER BY start_time")
    return [dict(zip(["query_id", "text", "status", "elapsed_ms"], r)) for r in c.fetchall()]


def main():
    con, c = connect()
    out = {"M1": block(c, M1), "M2": block(c, M2), "M3_finished": block(c, M3_FINISHED),
           "M3_running": block(c, M3_RUNNING), "M3_pending_at_return": block(c, M3_PENDING_AT_RETURN)}
    out["history"] = history(c, None)
    out["M4"] = m4(c)
    con.close()
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
