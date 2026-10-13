"""Client-side execution of an agent's snowflake_sql_execute tool use (session 8, configuration D').

Cortex Agents Run API (docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-run): a response.tool_use
carries client_side_execute ("whether the tool use is executed on the client side"), and a request message may carry a
tool_result content item (tool_use_id, type, name, content, status). Under code_toolset_all, the semantic view tool's
SQL came as a snowflake_sql_execute tool use with client_side_execute true (measured, session 8).

check_select() accepts exactly one SELECT or WITH ... SELECT statement (the project role can create and drop objects,
so nothing else is run); execute() runs it on the linkml_svc connection with USE SECONDARY ROLES NONE and a row limit;
result_text() returns the rows in the shape the sandbox's own snowflake_sql_execute returns them.
"""

from __future__ import annotations

import csv
import io
import re

ROW_LIMIT = 1000
FORBIDDEN = r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CALL|COPY|PUT|GET|REMOVE|USE|SET|" \
            r"UNSET|EXECUTE|BEGIN|COMMIT|ROLLBACK|UNDROP|DESCRIBE|SHOW|LIST)\b"


def _strip(sql: str) -> str:
    s = re.sub(r"'(?:[^']|'')*'", "''", sql)              # string literals
    s = re.sub(r'"(?:[^"]|"")*"', '""', s)                # quoted identifiers
    s = re.sub(r"--[^\n]*", " ", s)
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return s.strip()


def check_select(sql: str) -> str | None:
    """None if sql is exactly one SELECT (or WITH ... SELECT) statement; otherwise the reason it is refused."""
    s = _strip(sql or "")
    body = s[:-1].strip() if s.endswith(";") else s
    if not body:
        return "empty statement"
    if ";" in body:
        return "more than one statement"
    if not re.match(r"^(SELECT|WITH)\b", body, re.I):
        return "not a SELECT or WITH statement"
    m = re.search(FORBIDDEN, body, re.I)
    if m:
        return f"keyword {m.group(1).upper()} is not allowed"
    return None


def result_text(columns: list[str], rows: list, truncated: bool) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    for r in rows:
        w.writerow(["" if v is None else str(v) for v in r])
    note = f" (truncated at {ROW_LIMIT} rows)" if truncated else ""
    return f"{len(rows)} row(s) returned{note}.\n\n{','.join(columns)}\n\n{out.getvalue().rstrip()}"


def execute(cur, sql: str) -> tuple[str, str, str | None]:
    """(status, text, query_id). cur: a linkml_svc cursor on which USE SECONDARY ROLES NONE has run."""
    reason = check_select(sql)
    if reason:
        return "error", f"Refused by the client: {reason}. Only one read-only SELECT statement is executed.", None
    try:
        cur.execute(sql)
        rows = cur.fetchmany(ROW_LIMIT + 1)
        cols = [d[0] for d in cur.description]
        return "success", result_text(cols, rows[:ROW_LIMIT], len(rows) > ROW_LIMIT), cur.sfqid
    except Exception as e:   # the error goes back to the agent, as the server-side tool would return it
        return "error", f"SQL error: {getattr(e, 'msg', str(e))[:1000]}", getattr(e, "sfqid", None)
