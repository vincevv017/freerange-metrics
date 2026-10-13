"""
SQL Scripting target of the generated stock coverage procedure (session 8b, decision 1), used by
compiler/gen_procedure.py --target sql. Written from the parity checklist (snowflake/phase4_c_sql/parity_checklist.md)
and the contract, not from any Python or pandas implementation of the metric.

Shape of a call, in the order of the generated body (measured costs: session 8b, snowflake/phase4_c_sql/results.md):
- four statements that read no table, started first as asynchronous child jobs so that they compile in parallel with
  the rest: in pure SQL over the bound parameters, every parameter check that follows the context in check_order, with
  its reason and the normalised request; and the text of the quality and the coverage statements, in three parts. A
  Scripting statement costs a few milliseconds and grows with the number of variables holding a value (about 8 ms
  each inside a 900-line body), so the work moved from Scripting loops into these SQL statements;
- the as_of_months checks (missing, invalid, not a month start, too many): one statement that reads no table, which
  also reads the caller;
- the context statement: the snapshot months, the valid analysis months and the horizon, and the quality
  expectations scoped to the whole table. Its codes (AS_OF_NO_SNAPSHOT, HORIZON_NOT_LOADED) are raised first, then
  the codes of the parameter checks;
- the quality and the coverage statements, started together (ASYNC, AWAIT); the quality statement also returns the
  MASTER_DATA_FANOUT reason and the warnings, rendered. DATA_QUALITY_FAILED, from the context statement's whole-table
  checks, is raised after MASTER_DATA_FANOUT;
- BASIS_NOT_COMPARABLE, judged on the rows the coverage statement returns.
Values travel as bind variables (one JSON request for the two data statements); identifiers are literals written here
from the contract. Each check is one entry of pre_checks, plan_checks, post_checks or final_checks; the generator
fails when a contract code has no entry, an entry has no code, or the stages break the contract's check_order.
"""

from __future__ import annotations

import re

WS = "' ' || CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13)"
FMT = "RTRIM(RTRIM(TO_VARCHAR({x}, 'FM999,999,999,999,999,999,990.0000'), '0'), '.')"


def q(s: str) -> str:
    """A SQL string literal (Snowflake reads backslash escapes in single-quoted strings)."""
    return "'" + str(s).replace("\\", "\\\\").replace("'", "''") + "'"


def arr(xs) -> str:
    return "ARRAY_CONSTRUCT(" + ", ".join(q(x) for x in xs) + ")"


def render(template: str, values: dict[str, str]) -> str:
    """A message template as one SQL concatenation, in one pass: a placeholder with a value becomes its expression
    (a VARCHAR), one without stays as written."""
    out = []
    for part in re.split(r"(\{[A-Za-z_][A-Za-z0-9_]*\})", template):
        m = re.fullmatch(r"\{(\w+)\}", part)
        if m and m.group(1) in values:
            out.append(f"({values[m.group(1)]})")
        elif part:
            out.append(q(part))
    return " || ".join(out) or "''"


def case_map(expr: str, mapping: dict, default: str = "NULL") -> str:
    return "CASE " + expr + "".join(f" WHEN {q(k)} THEN {q(v)}" for k, v in mapping.items()) + f" ELSE {default} END"


def first_occurrences(col: str) -> str:
    """The distinct values of an array column, first occurrence kept, in order (not left to ARRAY_DISTINCT, whose order
    is not documented). `col` must be a column: a lambda may read a column, not another lambda's parameter."""
    return (f"TRANSFORM(FILTER(ARRAY_GENERATE_RANGE(0, ARRAY_SIZE({col})), i -> ARRAY_POSITION(GET({col}, i::INT), {col}) = i::INT), "
            f"i -> GET({col}, i::INT))")


def joined(xs) -> str:
    return ", ".join(xs)


# ================================================================================================ stage 1: as_of_months
# The checks that precede the context, as one statement that reads no table (so the context never runs for these
# refusals, as in the contract's order). It also returns the caller block, so no caller-only statement is needed.
# Each entry: (condition, reason) over the columns of pre_sql's last CTE, combined in check_order by one CASE.

def pre_checks(c: dict) -> dict[str, tuple[str, str]]:
    R = c["refusals"]
    return {
        "AS_OF_MISSING": ("missing", render(R["AS_OF_MISSING"], {})),
        "AS_OF_INVALID": ("invalid IS NOT NULL", render(R["AS_OF_INVALID"], {"value": "invalid"})),
        "AS_OF_NOT_MONTH_START": ("not_month_start IS NOT NULL", render(R["AS_OF_NOT_MONTH_START"], {
            "value": "not_month_start", "month_start": "LEFT(not_month_start, 8) || '01'"})),
        "AS_OF_TOO_MANY": (f"ARRAY_SIZE(parsed) > {c['max_periods']}", render(R["AS_OF_TOO_MANY"], {"max_periods": q(c["max_periods"])})),
    }


def pre_sql(c: dict, caller_sql: str) -> str:
    """as_of_months: a JSON array, or (lenient, as probe C0) a comma-separated list. PARSE_JSON(..., 'd') is as
    strict as the reference parser: no single quotes, no trailing comma (measured). An item is a string (stripped),
    an integer (its digits) or a boolean (True, False); anything else is invalid, shown as compact JSON (array,
    object), None (null) or a formatted number. Duplicates are dropped, first occurrence kept, in order."""
    ws, tok = WS, q(c["latest_token"])
    checks = pre_checks(c)
    codes = [k for k in c["refusal_order"] if k in checks]
    rcode = "CASE " + " ".join(f"WHEN {checks[k][0]} THEN {q(k)}" for k in codes) + " END"
    reason = "CASE " + " ".join(f"WHEN {checks[k][0]} THEN {checks[k][1]}" for k in codes) + " END"
    fmt = FMT.format(x="it::FLOAT")
    return f"""WITH a AS (
    SELECT :AS_OF_MONTHS AS raw, TRIM(raw, {ws}) AS s, LEFT(s, 1) IN ('[', '{{') AS is_json,
           IFF(is_json, TRY_PARSE_JSON(s, 'd'), NULL) AS j,
           raw IS NULL OR s IN ('', '[]', 'null') AS missing0,
           is_json AND NOT COALESCE(IS_ARRAY(j), FALSE) AS bad_json,
           CASE WHEN missing0 OR bad_json THEN ARRAY_CONSTRUCT()
                WHEN is_json THEN j::ARRAY
                ELSE FILTER(TRANSFORM(SPLIT(s, ','), x -> TRIM(x::VARCHAR, {ws})::VARIANT), x -> x::VARCHAR <> '') END AS items,
           TRANSFORM(items, it -> CASE TYPEOF(it)
                 WHEN 'VARCHAR' THEN TRIM(it::VARCHAR, {ws})::VARIANT
                 WHEN 'INTEGER' THEN it::VARCHAR::VARIANT
                 WHEN 'BOOLEAN' THEN IFF(it::BOOLEAN, 'True', 'False')::VARIANT
                 ELSE OBJECT_CONSTRUCT('bad', CASE WHEN TYPEOF(it) IN ('ARRAY', 'OBJECT') THEN TO_JSON(it)
                                                   WHEN TYPEOF(it) = 'NULL_VALUE' THEN 'None' ELSE {fmt} END)::VARIANT END) AS texts,
           TRANSFORM(texts, x -> CASE WHEN IS_OBJECT(x) THEN x
                 WHEN UPPER(x::VARCHAR) = {tok} THEN {tok}::VARIANT
                 WHEN REGEXP_LIKE(x::VARCHAR, '\\\\d{{4}}-\\\\d{{2}}-\\\\d{{2}}') AND TRY_TO_DATE(x::VARCHAR, 'YYYY-MM-DD') IS NOT NULL THEN x
                 ELSE OBJECT_CONSTRUCT('bad', x)::VARIANT END) AS checked,
           missing0 OR (NOT bad_json AND ARRAY_SIZE(items) = 0) AS missing,
           IFF(bad_json, raw, GET(GET(FILTER(checked, x -> IS_OBJECT(x)), 0), 'bad')::VARCHAR) AS invalid,
           {first_occurrences('checked')} AS parsed,
           GET(FILTER(checked, x -> NOT IS_OBJECT(x) AND x::VARCHAR <> {tok} AND RIGHT(x::VARCHAR, 2) <> '01'), 0)::VARCHAR AS not_month_start
),
caller AS (
{caller_sql}
)
SELECT caller.*, {rcode} AS RCODE, {reason} AS REASON, parsed AS PARSED
FROM a, caller"""


# ================================================================================================ stage 2: the plan
# Checks evaluated in SQL inside the context statement. Each entry: (condition, reason), SQL over the columns of the
# plan's last CTE. They are combined in check_order by one CASE; every expression is safe on any input (AS_ARRAY,
# TRY_PARSE_JSON), since SQL does not promise to skip the expressions of later branches.

def plan_checks(c: dict) -> dict[str, tuple[str, str]]:
    R = c["refusals"]
    h = c["horizon"]
    horizon = [(f"COALESCE({x['id']}, 0) <> 0", render(R["HORIZON_NOT_LOADED"], {
        "source": q(x["source"]), "horizon": q(h),
        "horizon_end": f"TO_VARCHAR(DATE_TRUNC('month', DATEADD('month', {h}, latest_snapshot::DATE)), 'YYYY-MM-DD')",
        "latest": "latest_snapshot"})) for x in c["q_horizon"]]
    horizon.append(("month_out_of_horizon IS NOT NULL", render(R["HORIZON_NOT_LOADED"], {
        "source": q("calendar or forecast"), "horizon": q(h),
        "horizon_end": f"TO_VARCHAR(DATE_TRUNC('month', DATEADD('month', {h}, month_out_of_horizon::DATE)), 'YYYY-MM-DD')",
        "latest": "month_out_of_horizon"})))
    hz_cond = " OR ".join(f"({cond})" for cond, _ in horizon)
    hz_reason = "CASE " + " ".join(f"WHEN {cond} THEN {rsn}" for cond, rsn in horizon) + " END"
    cl = c["classes"]
    sel = c["selection"]
    sel_reason = render(R["SELECTION_INVALID"], {"parameter": "sel_bad:p::VARCHAR", "expected": "sel_bad:e::VARCHAR",
                                                 "value": "sel_bad:v::VARCHAR"})
    return {
        "AS_OF_NO_SNAPSHOT": ("bad_month IS NOT NULL", render(R["AS_OF_NO_SNAPSHOT"], {
            "value": "bad_month:value::VARCHAR", "latest": "bad_month:latest::VARCHAR",
            "available_months": "bad_month:available::VARCHAR"})),
        "HORIZON_NOT_LOADED": (hz_cond, hz_reason),
        "BASIS_UNKNOWN": ("basis IS NULL", render(R["BASIS_UNKNOWN"], {"value": "basis_raw"})),
        "GRAIN_MALFORMED": ("grain_malformed", render(R["GRAIN_MALFORMED"], {})),
        "GRAIN_EMPTY": ("ARRAY_SIZE(grain) = 0", render(R["GRAIN_EMPTY"], {})),
        "GRAIN_DUPLICATE": ("ARRAY_SIZE(grain_dups) > 0", render(R["GRAIN_DUPLICATE"], {"value": "ARRAY_TO_STRING(grain_dups, ', ')"})),
        "FILTERS_MALFORMED": ("filters_malformed", render(R["FILTERS_MALFORMED"], {})),
        "FILTER_VALUES_INVALID": ("bad_filter IS NOT NULL", render(R["FILTER_VALUES_INVALID"], {"attribute": "bad_filter"})),
        "ATTRIBUTE_UNKNOWN": ("unknown_attribute IS NOT NULL", render(R["ATTRIBUTE_UNKNOWN"], {
            "attribute": "unknown_attribute", "conformed": q(", ".join(cl["CONFORMED"])),
            "snapshot_only": q(", ".join(cl["SNAPSHOT_ONLY"]))})),
        "ATTRIBUTE_UNCLASSIFIED": ("unclassified_attribute IS NOT NULL", render(R["ATTRIBUTE_UNCLASSIFIED"], {
            "attribute": "unclassified_attribute"})),
        "ATTRIBUTE_NOT_APPLICABLE": ("not_applicable_attribute IS NOT NULL", render(R["ATTRIBUTE_NOT_APPLICABLE"], {
            "attribute": "not_applicable_attribute",
            "reason": case_map("not_applicable_attribute", c["attr_description"], "''")})),
        "TOTALS_MALFORMED": ("totals_malformed", render(R["TOTALS_MALFORMED"], {})),
        "TOTALS_NOT_SUBSET": ("bad_total IS NOT NULL", render(R["TOTALS_NOT_SUBSET"], {
            "value": "ARRAY_TO_STRING(bad_total, ', ')", "grain": "ARRAY_TO_STRING(grain, ', ')"})),
        "SELECTION_INVALID": ("sel_bad IS NOT NULL", sel_reason),
    }


# ================================================================================================ stage 3: data checks

def post_checks(c: dict) -> dict[str, str]:
    """Scripting code run after the quality statement; qv holds its row (FANOUT_REASON) and plan the DQ reason."""
    return {
        "MASTER_DATA_FANOUT": """
    IF (qv:FANOUT_REASON::VARCHAR IS NOT NULL) THEN
      rcode := 'MASTER_DATA_FANOUT';
      reason := qv:FANOUT_REASON::VARCHAR;
      RAISE refused;
    END IF;""",
        "DATA_QUALITY_FAILED": """
    IF (plan:DQ_REASON::VARCHAR IS NOT NULL) THEN
      rcode := 'DATA_QUALITY_FAILED';
      reason := plan:DQ_REASON::VARCHAR;
      RAISE refused;
    END IF;""",
    }


def final_checks(c: dict) -> dict[str, str]:
    """Scripting code run after the coverage statement (session 8c-0): the basis is judged on the rows it returns."""
    return {
        "BASIS_NOT_COMPARABLE": """
    IF (cv:BASIS_REASON::VARCHAR IS NOT NULL) THEN
      rcode := 'BASIS_NOT_COMPARABLE';
      reason := cv:BASIS_REASON::VARCHAR;
      RAISE refused;
    END IF;""",
    }


# ================================================================================================ the plan statement

def plan_sql(c: dict, context_sql: str, part: str) -> str:
    """The context statement, extended: context, every plan check with its reason, the normalised request and the
    text of the two data statements. Binds: :parsed (the resolved as_of tokens, JSON), and the raw parameters."""
    ws = WS
    tok = q(c["latest_token"])
    order = c["attribute_order"]
    attr_expr = lambda x: case_map(x, c["attr_expr"])          # noqa: E731
    attr_col = lambda x: case_map(x, c["attr_column"])         # noqa: E731
    conformed_all = arr(c["classes"]["CONFORMED"])
    rank = "CASE {x}" + "".join(f" WHEN {q(a)} THEN {i}" for i, a in enumerate(order)) + f" ELSE {len(order)} END"
    checks = plan_checks(c)
    codes = [k for k in c["refusal_order"] if k in checks]
    rcode = "CASE " + " ".join(f"WHEN {checks[k][0]} THEN {q(k)}" for k in codes) + " END"
    reason = "CASE " + " ".join(f"WHEN {checks[k][0]} THEN {checks[k][1]}" for k in codes) + " END"
    dq = c["q_dq"]
    dq_reason = ("CASE " + " ".join(
        f"WHEN COALESCE({x['id']}, 0) <> 0 THEN " + render(c["refusals"]["DATA_QUALITY_FAILED"], {
            "expectation": q(x["id"]), "count": f"{x['id']}::VARCHAR", "condition": q(x["condition"])}) for x in dq)
                 + " END") if dq else "NULL"
    scope_attr = c["default_scope"]["attribute"]
    bases = c["basis"]
    filt = ("{e} || ' IN (SELECT f.value::VARCHAR FROM req, TABLE(FLATTEN(INPUT => req.r:filters:\"' || {x} || '\")) f)'")

    def joins_expr(fact_joins: dict, fact_alias: str, used: str) -> str:
        parts = []
        for t, j in fact_joins.items():
            t_attrs = [a for a in order if c["attr_table"][a] == t]
            if not t_attrs:
                continue
            hit = f"ARRAY_INTERSECTION({used}, {arr(t_attrs)})"
            if t in c["dedup_tables"]:
                src = (f"'(SELECT DISTINCT ' || ARRAY_TO_STRING(ARRAY_DISTINCT(ARRAY_CAT({arr(j['keys'])}, "
                       f"TRANSFORM({hit}, x -> {attr_col('x::VARCHAR')}))), ', ') || ' FROM {j['table']})'")
            else:
                src = q(j["table"])
            pre, post = j["clause"].split("{src}")
            parts.append(f"IFF(ARRAY_SIZE({hit}) > 0, {q(pre)} || {src} || {q(post)}, '')")
        return " || ".join(parts) or "''"

    sa = c["aliases"][c["stock_table"]]
    fa = c["aliases"][c["flow_table"]]
    k0, h = c["window_start"], c["horizon"]
    keys_s = ", ".join(f"{sa}.{k}" for k in c["member_keys"])
    keys_f = ", ".join(f"{fa}.{k}" for k in c["member_keys"])
    stock_col = case_map("basis", {u: v[0] for u, v in bases["columns"].items()})
    flow_col = case_map("basis", {u: v[1] for u, v in bases["columns"].items()})
    scope_qty_col = case_map("basis", bases["scope_column"])
    ib = bases["item"]
    items_cte = (f",{chr(10)}items AS (SELECT DISTINCT {ib['key']} AS item_id, {ib['dimension']} AS dimension, "
                 f"{ib['base_unit']} AS base_unit, {ib['native_unit']} AS native_unit FROM {ib['table']})")
    scope_in = "scope_value IN (SELECT f.value::VARCHAR FROM req, TABLE(FLATTEN(INPUT => req.r:scope)) f)"
    base = (
        "'WITH req AS (SELECT PARSE_JSON(?) AS r),\\nanalysis_months AS (\\n    SELECT f.value::DATE AS as_of_month "
        "FROM req, TABLE(FLATTEN(INPUT => req.r:months)) f\\n),\\nmonths AS (\\n    SELECT "
        f"{k0 - 1} + ROW_NUMBER() OVER (ORDER BY SEQ4()) AS k FROM TABLE(GENERATOR(ROWCOUNT => {h}))\\n),\\n"
        f"stock_rows AS (\\n    SELECT a.as_of_month, {keys_s}, ' || "
        f"ARRAY_TO_STRING(TRANSFORM(grain, x -> {attr_expr('x::VARCHAR')} || ' AS ' || x::VARCHAR), ', ') || ', ' || "
        f"{q(c['attr_expr'][scope_attr] + ' AS scope_value, ' + sa + '.')} || {stock_col} || "
        f"{q('::FLOAT AS qty, ' + sa + '.')} || {scope_qty_col} || "
        f"{q('::FLOAT AS scope_qty' + chr(10) + '    FROM analysis_months a' + chr(10) + '    JOIN ' + c['tables'][c['stock_table']] + ' ' + sa + ' ON ' + sa + '.' + c['stock_time'] + ' = a.as_of_month')} || "
        f"{joins_expr(c['stock_joins'], sa, 'used')} || '\\n    WHERE ' || "
        f"COALESCE(NULLIF(ARRAY_TO_STRING(TRANSFORM(fkeys, x -> {filt.format(e=attr_expr('x::VARCHAR'), x='x::VARCHAR')}), ' AND '), ''), 'TRUE') || "
        f"'\\n),\\nfc_rows AS (\\n    SELECT a.as_of_month, {keys_f}, ' || "
        f"ARRAY_TO_STRING(TRANSFORM(conformed, x -> {attr_expr('x::VARCHAR')} || ' AS ' || x::VARCHAR || ', '), '') || "
        f"{q('DATEDIFF(month, a.as_of_month, ' + fa + '.' + c['flow_time'] + ') AS k, ' + fa + '.')} || {flow_col} || "
        f"{q('::FLOAT AS qty' + chr(10) + '    FROM analysis_months a' + chr(10) + '    JOIN ' + c['tables'][c['flow_table']] + ' ' + fa + chr(10) + '      ON ' + fa + '.' + c['flow_time'] + ' >= DATEADD(month, ' + str(k0) + ', a.as_of_month)' + chr(10) + '     AND ' + fa + '.' + c['flow_time'] + ' <= DATEADD(month, ' + str(k0 + h - 1) + ', a.as_of_month)')} || "
        f"{joins_expr(c['flow_joins'], fa, 'ARRAY_INTERSECTION(used, ' + conformed_all + ')')} || '\\n    WHERE ' || "
        f"COALESCE(NULLIF(ARRAY_TO_STRING(TRANSFORM(ARRAY_INTERSECTION(fkeys, {conformed_all}), x -> {filt.format(e=attr_expr('x::VARCHAR'), x='x::VARCHAR')}), ' AND '), ''), 'TRUE') || "
        "'\\n)' || " + q(items_cte))

    # quality statement: the request-scoped checks, the fan-out counts and values, the warnings rendered
    fan = c["q_fanout"]
    cap = c["max_values"]
    if fan:
        f0 = fan[0]
        fan_attrs = [a for a in order if c["attr_table"][a] == f0["table"]]
        dk = c["dedup_key"]
        ft = c["tables"][f0["table"]]
        col_tpl = (f",\n       {f0['sql'].replace('{having}', 'COUNT(DISTINCT <<C>>) > 1')} AS FANOUT__<<AU>>"
                   f",\n       (SELECT ARRAY_AGG(DISTINCT <<C>>) WITHIN GROUP (ORDER BY <<C>>) FROM {ft} WHERE {dk} IN "
                   f"(SELECT {dk} FROM {ft} WHERE {dk} IN (SELECT {dk} FROM scope_items) GROUP BY {dk} HAVING "
                   f"COUNT(DISTINCT <<C>>) > 1)) AS FANOUT_VALUES__<<AU>>")
        group_tpl = (f"IFF(FANOUT__<<AU>> > 0, '<<A>> (' || ARRAY_TO_STRING(ARRAY_SLICE(FANOUT_VALUES__<<AU>>, 0, {cap}), ', ') "
                     f"|| IFF(ARRAY_SIZE(FANOUT_VALUES__<<AU>>) > {cap}, ' and ' || (ARRAY_SIZE(FANOUT_VALUES__<<AU>>) - {cap})::VARCHAR "
                     f"|| ' more', '') || ')', NULL)")
        fan_reason = render(c["refusals"]["MASTER_DATA_FANOUT"], {
            "count": "FANOUT::VARCHAR", "attributes": "ARRAY_TO_STRING(ARRAY_CONSTRUCT_COMPACT(<<GROUPS>>), ', ')"})
        each = lambda tpl: (f"TRANSFORM(fanout_attrs, a -> REPLACE(REPLACE(REPLACE({q(tpl)}, '<<AU>>', UPPER(a::VARCHAR)), "  # noqa: E731
                            f"'<<A>>', a::VARCHAR), '<<C>>', {attr_col('a::VARCHAR')}))")
        fan_cols = (f"{q(f0['sql'].replace('{having}', 'COUNT(*) > 1') + ' AS ' + f0['id'] + ',' + chr(10) + '       ' + f0['sql'].replace('{having}', '<<HAVING>>') + ' AS FANOUT')} "
                    f"|| ARRAY_TO_STRING({each(col_tpl)}, '')")
        fan_cols = (f"REPLACE({fan_cols}, '<<HAVING>>', COALESCE(NULLIF(ARRAY_TO_STRING(TRANSFORM(fanout_attrs, a -> "
                    f"'COUNT(DISTINCT ' || {attr_col('a::VARCHAR')} || ') > 1'), ' OR '), ''), 'FALSE'))")
        fan_reason_sql = (f"'IFF(FANOUT > 0, ' || REPLACE({q(fan_reason)}, '<<GROUPS>>', "
                          f"ARRAY_TO_STRING({each(group_tpl)}, ', ')) || ', NULL)'")
        fanout_attrs = f"FILTER({arr(fan_attrs)}, x -> ARRAY_CONTAINS(x, used))"
    else:
        fan_cols, fan_reason_sql, fanout_attrs = "''", "'NULL'", "ARRAY_CONSTRUCT()"
    W = c["warnings"]
    warn_static = ", ".join(
        f"IFF(COALESCE({x['id']}, 0) <> 0, OBJECT_CONSTRUCT('code', {q(x['warning'])}, 'expectation', {q(x['id'])}, "
        f"'count', {x['id']}, 'message', "
        + render(W[x["warning"]], {"count": f"{x['id']}::VARCHAR", "expectation": q(x["id"]), "condition": q(x["condition"])})
        + "), NULL)" for x in c["q_warn"])
    sw = c["default_scope"]["warning"]
    # per analysis month and unit of the basis (session 8c-0): EUR on a fixed-unit basis, else the item's base unit
    scope_col = (",\n       (SELECT ARRAY_AGG(OBJECT_CONSTRUCT('code', " + q(sw) + ", 'as_of_month', m, 'excluded_amount', amt, "
                 "'unit', u, 'message', "
                 + render(W[sw], {"excluded_amount": FMT.format(x="amt"), "unit": "u"})
                 + " || ' (as of ' || m || ')')) WITHIN GROUP (ORDER BY m, u) FROM (SELECT TO_VARCHAR(s.as_of_month) AS m, "
                 "<<U>> AS u, SUM(s.scope_qty) AS amt FROM stock_rows s JOIN items it ON it.item_id = s.item_id "
                 f"WHERE NOT ({scope_in}) OR s.scope_value IS NULL GROUP BY 1, 2 HAVING SUM(s.scope_qty) <> 0)) AS SCOPE_WARNINGS")
    scope_unit = case_map("basis", {b: q(u) for b, u in bases["fixed_unit"].items()}, q("it.base_unit"))
    qsql = (
        f"base || {q(',' + chr(10) + 'scope_items AS (SELECT ' + c['dedup_key'] + ' FROM stock_rows UNION SELECT ' + c['dedup_key'] + ' FROM fc_rows),' + chr(10) + 'scope_pairs AS (SELECT DISTINCT as_of_month, ' + ', '.join(c['member_keys']) + ' FROM fc_rows),' + chr(10) + 'quality_row AS (' + chr(10) + 'SELECT ')} || "
        f"{fan_cols} || {q(',' + chr(10) + '       ' + c['q_static_cols'])} || "
        f"IFF(scope_on, REPLACE({q(scope_col)}, '<<U>>', {scope_unit}), '') || "
        f"{q(chr(10) + ')' + chr(10) + 'SELECT OBJECT_CONSTRUCT(' + chr(39) + 'Q' + chr(39) + ', q, ' + chr(39) + 'FANOUT_REASON' + chr(39) + ', fanout_reason, ' + chr(39) + 'WARNINGS' + chr(39) + ', warnings) AS Q FROM (' + chr(10) + 'SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) AS q, ')} || {fan_reason_sql} || "
        f"{q(' AS fanout_reason, ARRAY_CAT(ARRAY_CONSTRUCT_COMPACT(' + warn_static + '), ')} || "
        f"IFF(scope_on, 'COALESCE(SCOPE_WARNINGS, ARRAY_CONSTRUCT())', 'ARRAY_CONSTRUCT()') || "
        f"{q(') AS warnings FROM quality_row)')}")

    # coverage statement: one row, the rows as an ordered array of objects, the row count and the flags
    fl = c["flags"]
    gsel = lambda acc: (f"ARRAY_TO_STRING(TRANSFORM(grain, x -> ', ' || IFF(ARRAY_CONTAINS(x, {acc}), '', 'NULL AS ') "  # noqa: E731
                        f"|| x::VARCHAR), '')")
    key = lambda acc: f"ARRAY_TO_STRING(TRANSFORM({acc}, x -> ', ' || x::VARCHAR), '')"      # noqa: E731
    ckey = lambda acc: key(f"ARRAY_INTERSECTION({acc}, {conformed_all})")                 # noqa: E731
    on = lambda acc, s: f"ARRAY_TO_STRING(TRANSFORM({acc}, x -> ' AND EQUAL_NULL({s}.' || x::VARCHAR || ', mb.' || x::VARCHAR || ')'), '')"  # noqa: E731
    gs = "gs"
    n_ = "n::VARCHAR"
    flow_members_always = c["flow_members"] == "ALWAYS"
    union = (f"IFF({'TRUE' if flow_members_always else 'FALSE'} OR ARRAY_SIZE(ARRAY_INTERSECTION({gs}, {conformed_all})) = ARRAY_SIZE({gs}), "
             f"'\\n        UNION\\n        SELECT as_of_month' || {key(gs)} || ' FROM f' || {n_}, '')")
    # one row per grain set (gx: n, gs, grain), its CTEs, its SELECT and its total_grain branch, aggregated in gt
    nl = chr(10)
    on_t = lambda acc, s, t: f"ARRAY_TO_STRING(TRANSFORM({acc}, x -> ' AND EQUAL_NULL({s}.' || x::VARCHAR || ', {t}.' || x::VARCHAR || ')'), '')"  # noqa: E731
    pref = lambda acc, a: f"ARRAY_TO_STRING(TRANSFORM({acc}, x -> ', {a}.' || x::VARCHAR), '')"   # noqa: E731
    cgs = f"ARRAY_INTERSECTION({gs}, {conformed_all})"
    # session 8c-0: i<n>, the items of each member (its stock items, the forecast items of its conformed key) and
    # their dimensions, which decide the bases the row can be measured on; d<n> carries them to every row
    i_text = (
        f" || 'i' || {n_} || {q(' AS (' + nl + '    SELECT x.as_of_month')} || {pref(gs, 'x')} || "
        f"{q(', COUNT(DISTINCT x.item_id) AS n_items, COUNT(DISTINCT it.dimension) AS n_dims,' + nl + '           MIN(it.base_unit) AS base_unit, MIN(it.native_unit) AS native_unit' + nl + '    FROM (SELECT as_of_month')} || "
        f"{key(gs)} || {q(', item_id FROM stock_rows WHERE ')} || IFF(scope_on, {q(scope_in)}, 'TRUE') || "
        f"{q(nl + '          UNION' + nl + '          SELECT mb.as_of_month')} || {pref(gs, 'mb')} || {q(', x.item_id FROM m')} || {n_} || "
        f"{q(' mb JOIN fc_rows x ON x.as_of_month = mb.as_of_month')} || {on_t(cgs, 'x', 'mb')} || "
        f"{q(') x' + nl + '    JOIN items it ON it.item_id = x.item_id' + nl + '    GROUP BY ALL' + nl + '),' + nl)}")
    cte_text = (
        f"',\\ns' || {n_} || ' AS (SELECT as_of_month' || {key(gs)} || ', SUM(stock_qty) AS stock_qty FROM stock GROUP BY ALL),\\n'"
        f" || 'f' || {n_} || ' AS (SELECT as_of_month' || {ckey(gs)} || ', k, SUM(fc_qty) AS fc_qty FROM fc GROUP BY ALL),\\n'"
        f" || 'm' || {n_} || ' AS (\\n        SELECT as_of_month' || {key(gs)} || ' FROM s' || {n_} || {union} || '\\n),\\n'"
        f"{i_text}"
        f" || 'd' || {n_} || ' AS (\\n    SELECT mb.*, m.k, COALESCE(s.stock_qty, 0) AS stock_qty, COALESCE(f.fc_qty, 0) AS fc_qty\\n'"
        f" || {q('    FROM (SELECT m0.*, i.n_items, i.n_dims, i.base_unit, i.native_unit FROM m')} || {n_} || {q(' m0 LEFT JOIN i')} || {n_}"
        f" || {q(' i ON i.as_of_month = m0.as_of_month')} || {on_t(gs, 'i', 'm0')} || {q(') mb CROSS JOIN months m' + nl)}"
        f" || '    LEFT JOIN s' || {n_} || ' s ON s.as_of_month = mb.as_of_month' || {on(gs, 's')} || '\\n'"
        f" || '    LEFT JOIN f' || {n_} || ' f ON f.as_of_month = mb.as_of_month AND f.k = m.k' || {on(f'ARRAY_INTERSECTION({gs}, {conformed_all})', 'f')} || '\\n),\\n'"
        f" || 'c' || {n_} || ' AS (\\n    SELECT *, SUM(fc_qty) OVER (PARTITION BY as_of_month' || {key(gs)} || ' ORDER BY k ROWS UNBOUNDED PRECEDING) AS cum_fc\\n    FROM d' || {n_} || '\\n)'")
    sel_body = ("'       ANY_VALUE(stock_qty) AS stock, MAX(cum_fc) AS forecast_over_horizon,\\n"
                "       CASE\\n         WHEN ANY_VALUE(stock_qty) = 0 THEN 0\\n"
                "         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN\\n"
                "              SUM(CASE WHEN cum_fc - fc_qty >= stock_qty THEN 0\\n"
                "                       WHEN cum_fc <= stock_qty THEN 1\\n"
                "                       ELSE (stock_qty - (cum_fc - fc_qty)) / fc_qty END)\\n"
                "         WHEN MAX(cum_fc) = 0 THEN NULL\\n"
                "         ELSE ANY_VALUE(stock_qty) / AVG(NULLIF(fc_qty, 0))\\n       END AS coverage_months,\\n"
                f"       CASE\\n         WHEN ANY_VALUE(stock_qty) = 0 THEN ''{fl['SNAPSHOT_NULL_OR_ZERO']}''\\n"
                "         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN NULL\\n"
                f"         WHEN MAX(cum_fc) = 0 THEN ''{fl['NO_FLOW_IN_WINDOW']}''\\n"
                f"         ELSE ''{fl['BEYOND_HORIZON']}''\\n       END AS flag,\\n"
                "       ANY_VALUE(n_items) AS n_items, ANY_VALUE(n_dims) AS n_dims, ANY_VALUE(base_unit) AS base_unit,\\n"
                "       ANY_VALUE(native_unit) AS native_unit\\n'")
    sel_text = (f"'SELECT ''' || IFF(n = 0, 'DETAIL', 'TOTAL') || ''' AS row_type, ' || {n_} || ' AS grain_set, as_of_month' || {gsel(gs)} || ',\\n' || "
                f"{sel_body} || 'FROM c' || {n_} || ' GROUP BY as_of_month' || {key(gs)}")
    tg_text = (f"IFF(n = 0, '', ' WHEN ' || {n_} || ' THEN ARRAY_CONSTRUCT(' || "
               f"ARRAY_TO_STRING(TRANSFORM({gs}, x -> '''' || x::VARCHAR || ''''), ', ') || ')')")
    rowobj = ("'OBJECT_CONSTRUCT_KEEP_NULL(''row_type'', row_type, ''as_of_month'', TO_VARCHAR(as_of_month, ''YYYY-MM-DD'')' || "
              "ARRAY_TO_STRING(TRANSFORM(grain, x -> ', ''' || x::VARCHAR || ''', ' || x::VARCHAR), '') || "
              "', ''coverage_months'', coverage_months, ''stock'', stock, ''forecast_over_horizon'', forecast_over_horizon, "
              "''stock_unit'', stock_unit, ''stockout_month'', TO_VARCHAR(stockout_month, ''YYYY-MM-DD''), ''flag'', flag)'")
    rowobj_full = (f"IFF(ARRAY_SIZE(grains) > 1, 'IFF(grain_set = 0, ' || {rowobj} || ', OBJECT_INSERT(' || {rowobj} || "
                   f"', ''total_grain'', CASE grain_set' || g_tg || ' END))', {rowobj})")
    post = post_template(c)
    post_expr = q(post)
    for ph, expr in (
            ("<<BASIS>>", "basis"),
            ("<<ON>>", "IFF(sel_on, 'TRUE', 'FALSE')"),
            ("<<COND>>", "IFF(sel_below IS NULL, '', ' AND coverage_months > 0 AND coverage_months <= ' || TO_VARCHAR(sel_below)) || "
                         "IFF(sel_above IS NULL, '', ' AND coverage_months > ' || TO_VARCHAR(sel_above))"),
            ("<<RANK>>", "IFF(sel_rank IS NULL, 'TRUE', 'rk <= ' || TO_VARCHAR(sel_rank))"),
            ("<<ORDER>>", "ARRAY_TO_STRING(TRANSFORM(grain, x -> ', ' || x::VARCHAR || ' ASC NULLS LAST'), '')"),
            ("<<GORDER>>", "ARRAY_TO_STRING(TRANSFORM(grain, x -> x::VARCHAR || ' ASC NULLS LAST'), ', ')"),
            ("<<MEMBER>>", "'OBJECT_CONSTRUCT_KEEP_NULL(' || ARRAY_TO_STRING(TRANSFORM(grain, x -> '''' || x::VARCHAR || ''', ' || x::VARCHAR), ', ') || ')'"),
            ("<<ROWORDER>>", "ARRAY_TO_STRING(TRANSFORM(grain, x -> ', ' || x::VARCHAR || ' NULLS LAST'), '')"),
            ("<<NOSUM>>", f"IFF(ARRAY_CONTAINS(basis::VARIANT, {arr(c['selection']['no_sum_bases'])}), 'TRUE', 'FALSE')"),
            ("<<ROWOBJ>>", rowobj_full)):
        post_expr = f"REPLACE({post_expr}, {q(ph)}, {expr})"
    csql = (
        f"base || ',\\nstock AS (\\n    SELECT as_of_month' || {key('grain')} || ', SUM(qty) AS stock_qty\\n    FROM stock_rows WHERE ' || "
        f"IFF(scope_on, {q(scope_in)}, 'TRUE') || '\\n    GROUP BY ALL\\n),\\nfc AS (\\n    SELECT as_of_month' || {ckey('grain')} || "
        f"', k, SUM(qty) AS fc_qty\\n    FROM fc_rows\\n    GROUP BY ALL\\n)' || g_ctes || ',\\ncr AS (\\n' || g_selects || '\\n)' || {post_expr}")

    rnk = rank.format(x="k")
    # ---- CTEs shared by the four parts: the raw parameters parsed and normalised (no validation stops here: every
    # expression is safe on any input; the checks part decides, the three text parts are used only when it passes)
    with_ctx = part == "context"
    b_cte = (f"""ctx AS (
{context_sql}
),
b AS (
    SELECT ctx.*, PARSE_JSON(:parsed) AS parsed, :BASIS AS basis_raw, :COVERAGE_BELOW AS below_raw,
           :COVERAGE_ABOVE AS above_raw, :RANK_FIRST AS rank_raw, :GRAIN AS grain_raw, :FILTERS AS filters_raw,
           :TOTALS AS totals_raw,
           ARRAY_SORT(COALESCE(ctx.SNAPSHOTS, ARRAY_CONSTRUCT())) AS snaps,
           ARRAY_SORT(COALESCE(ctx.AVAILABLE, ARRAY_CONSTRUCT())) AS avail,
           GET(avail, ARRAY_SIZE(avail) - 1)::VARCHAR AS latest,
           GET(snaps, ARRAY_SIZE(snaps) - 1)::VARCHAR AS latest_snapshot
    FROM ctx
),
mm AS (
    SELECT f.index AS i, f.value::VARCHAR AS tok, IFF(tok = {tok}, b.latest, tok) AS d,
           CASE WHEN tok = {tok} AND b.latest IS NULL
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
),""" if with_ctx else """b AS (
    SELECT :BASIS AS basis_raw, :COVERAGE_BELOW AS below_raw, :COVERAGE_ABOVE AS above_raw, :RANK_FIRST AS rank_raw,
           :GRAIN AS grain_raw, :FILTERS AS filters_raw, :TOTALS AS totals_raw
),""")
    s1_from = "FROM b, mres" if with_ctx else "FROM b"
    s1_star = "b.*, mres.*" if with_ctx else "b.*"
    parse = f"""{b_cte}
s1 AS (
    SELECT {s1_star},
           REGEXP_REPLACE(UPPER(TRIM(COALESCE(basis_raw, ''), {ws})), '[\\\\s-]+', '_') AS ukey,
           IFF(basis_raw IS NULL OR TRIM(basis_raw, {ws}) IN ('', 'null'), {q(c['basis']['default'])},
               {case_map('ukey', {n: u for u, names in c['basis']['names'].items() for n in names})}) AS basis,
           {selection_sql(c)},
           TRIM(grain_raw, {ws}) AS g_s,
           grain_raw IS NOT NULL AND g_s <> '' AND LEFT(g_s, 1) IN ('[', '{{') AND NOT COALESCE(IS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), FALSE) AS g_bad_json,
           CASE WHEN grain_raw IS NULL OR g_s = '' THEN ARRAY_CONSTRUCT()
                WHEN LEFT(g_s, 1) IN ('[', '{{') THEN COALESCE(AS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), ARRAY_CONSTRUCT())
                ELSE FILTER(TRANSFORM(SPLIT(g_s, ','), x -> TRIM(x::VARCHAR, {ws})::VARIANT), x -> x::VARCHAR <> '') END AS g_items,
           COALESCE(g_bad_json, FALSE) OR ARRAY_SIZE(FILTER(g_items, x -> TYPEOF(x) <> 'VARCHAR')) > 0 AS grain_malformed,
           TRANSFORM(FILTER(g_items, x -> TYPEOF(x) = 'VARCHAR'), x -> LOWER(TRIM(x::VARCHAR, {ws}))::VARIANT) AS grain,
           ARRAY_DISTINCT(ARRAY_EXCEPT(grain, ARRAY_DISTINCT(grain))) AS g_dup_set,
           ARRAY_CAT(FILTER({arr(order)}, x -> ARRAY_CONTAINS(x, g_dup_set)), ARRAY_SORT(FILTER(g_dup_set, x -> NOT ARRAY_CONTAINS(x, {arr(order)})))) AS grain_dups,
           TRIM(IFF(filters_raw IS NULL OR TRIM(filters_raw, {ws}) IN ('', 'null'), {q(c['filters_default'])}, filters_raw), {ws}) AS f_s,
           IFF(LEFT(f_s, 1) IN ('[', '{{'), TRY_PARSE_JSON(f_s, 'd'), NULL) AS f_json,
           f_json IS NULL OR NOT IS_OBJECT(f_json) AS filters_malformed,
           TRIM(IFF(totals_raw IS NULL OR TRIM(totals_raw, {ws}) IN ('', 'null'), {q(c['totals_default'])}, totals_raw), {ws}) AS t_s,
           IFF(LEFT(t_s, 1) = '[', TRY_PARSE_JSON(t_s, 'd'), NULL) AS t_json,
           t_json IS NULL OR NOT IS_ARRAY(t_json)
             OR ARRAY_SIZE(FILTER(COALESCE(AS_ARRAY(t_json), ARRAY_CONSTRUCT()), e -> NOT IS_ARRAY(e)
                  OR ARRAY_SIZE(FILTER(COALESCE(AS_ARRAY(e), ARRAY_CONSTRUCT()), z -> TYPEOF(z) <> 'VARCHAR')) > 0)) > 0 AS totals_malformed,
           TRANSFORM(COALESCE(AS_ARRAY(t_json), ARRAY_CONSTRUCT()),
                     e -> TRANSFORM(COALESCE(AS_ARRAY(e), ARRAY_CONSTRUCT()), z -> LOWER(TRIM(z::VARCHAR, {ws}))::VARIANT)::VARIANT) AS totals_all,
           {first_occurrences('totals_all')} AS totals
    {s1_from}
),
fl AS (
    SELECT LOWER(TRIM(f.key, {ws})) AS k, f.value AS v,
           IFF(TYPEOF(v) IN ('VARCHAR', 'INTEGER', 'DECIMAL', 'DOUBLE'), ARRAY_CONSTRUCT(v), AS_ARRAY(v)) AS vv,
           vv IS NULL OR ARRAY_SIZE(vv) = 0
             OR ARRAY_SIZE(FILTER(vv, e -> TYPEOF(e) IN ('NULL_VALUE', 'ARRAY', 'OBJECT', 'BOOLEAN'))) > 0 AS bad,
           {rnk} AS rk
    FROM s1, TABLE(FLATTEN(INPUT => IFF(IS_OBJECT(s1.f_json), s1.f_json, OBJECT_CONSTRUCT()))) f
    QUALIFY ROW_NUMBER() OVER (PARTITION BY LOWER(TRIM(f.key, {ws})) ORDER BY f.key DESC) = 1
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
           ARRAY_CAT(FILTER({arr(order)}, x -> ARRAY_CONTAINS(x, names)), ARRAY_SORT(FILTER(names, x -> NOT ARRAY_CONTAINS(x, {arr(order)})))) AS ranked,
           GET(FILTER(ranked, x -> NOT ARRAY_CONTAINS(x, {arr(order)}) AND NOT ARRAY_CONTAINS(x, {arr(c['unclassified'])})), 0)::VARCHAR AS unknown_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, {arr(c['unclassified'])})), 0)::VARCHAR AS unclassified_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, {arr(c['classes']['NOT_APPLICABLE'])})), 0)::VARCHAR AS not_applicable_attribute,
           GET(FILTER(totals, t -> ARRAY_SIZE(ARRAY_DISTINCT(t::ARRAY)) <> ARRAY_SIZE(t::ARRAY)
                      OR ARRAY_SIZE(ARRAY_EXCEPT(t::ARRAY, grain)) > 0 OR ARRAY_SIZE(t::ARRAY) >= ARRAY_SIZE(grain)), 0)::ARRAY AS bad_total,
           NOT ARRAY_CONTAINS({q(scope_attr)}::VARIANT, fkeys) AS scope_on,
           FILTER(grain, x -> ARRAY_CONTAINS(x, {conformed_all})) AS conformed,
           ARRAY_DISTINCT(ARRAY_APPEND(ARRAY_CAT(grain, fkeys), {q(scope_attr)})) AS used,
           ARRAY_PREPEND(totals, grain) AS grains,
           {fanout_attrs} AS fanout_attrs
    FROM s1, fa
)"""
    if part == "context":
        ctx_codes = [k for k in codes if k in CONTEXT_CODES]
        r_code = "CASE " + " ".join(f"WHEN {checks[k][0]} THEN {q(k)}" for k in ctx_codes) + " END"
        r_reason = "CASE " + " ".join(f"WHEN {checks[k][0]} THEN {checks[k][1]}" for k in ctx_codes) + " END"
        return f"""WITH {b_cte.rstrip(',')}
SELECT CALLER_ROLE, CALLER_SECONDARY_ROLES, CALLER_USER, AGENT_ACTIVATED,
       GET(avail, 0)::VARCHAR AS AVAILABLE_FIRST, latest AS AVAILABLE_LATEST,
       {r_code} AS RCODE, {r_reason} AS REASON, {dq_reason} AS DQ_REASON, months AS MONTHS
FROM b, mres"""
    if part == "params":
        par_codes = [k for k in codes if k not in CONTEXT_CODES]
        r_code = "CASE " + " ".join(f"WHEN {checks[k][0]} THEN {q(k)}" for k in par_codes) + " END"
        r_reason = "CASE " + " ".join(f"WHEN {checks[k][0]} THEN {checks[k][1]}" for k in par_codes) + " END"
        return f"""WITH {parse}
SELECT {r_code} AS RCODE, {r_reason} AS REASON,
       basis AS BASIS, grain AS GRAIN, filters AS FILTERS, totals AS TOTALS, scope_on AS SCOPE_ON,
       sel_below AS SEL_BELOW, sel_above AS SEL_ABOVE, sel_rank AS SEL_RANK, sel_on AS SEL_ON,
       FILTER(ranked, x -> ARRAY_CONTAINS(x, {conformed_all})) AS STOCK_AND_FORECAST,
       FILTER(ranked, x -> ARRAY_CONTAINS(x, {arr(c['classes']['SNAPSHOT_ONLY'])})) AS STOCK_ONLY
FROM s2"""
    if part == "base":
        return f"WITH {parse}\nSELECT {base} AS T FROM s2"
    if part == "quality":
        return f"WITH {parse}\nSELECT {qsql[len('base || '):]} AS T FROM s2"
    if part != "coverage":
        raise ValueError(f"unknown part {part!r}")
    return f"""WITH {parse},
gx AS (
    SELECT f.index AS n, f.value::ARRAY AS gs, s2.grain AS grain, s2.scope_on AS scope_on
    FROM s2, TABLE(FLATTEN(INPUT => s2.grains)) f
),
gt AS (
    SELECT LISTAGG(cte_text, '') WITHIN GROUP (ORDER BY n) AS g_ctes,
           LISTAGG(sel_text, '\\nUNION ALL\\n') WITHIN GROUP (ORDER BY n) AS g_selects,
           LISTAGG(tg_text, '') WITHIN GROUP (ORDER BY n) AS g_tg
    FROM (SELECT n, {cte_text} AS cte_text, {sel_text} AS sel_text, {tg_text} AS tg_text FROM gx)
)
SELECT {csql[len('base || '):]} AS T FROM s2, gt"""


def selection_sql(c: dict) -> str:
    """The selection parameters of the s1 CTE (session 8c-0): each one absent, or checked as the Python target checks
    it (a positive number, a positive integer, an open window), the first fault in the contract's parameter order."""
    ws, sel = WS, c["selection"]
    raw = {sel["below"]: "below_raw", sel["above"]: "above_raw", sel["rank"]: "rank_raw"}
    num, intg = q(r"\s*[0-9]+(\.[0-9]+)?\s*"), q(r"\s*[0-9]+\s*")
    cols = [f"IFF({r} IS NULL OR TRIM({r}, {ws}) IN ('', 'null'), NULL, {r}) AS v_{r[:-4]}" for r in raw.values()]
    cases = []
    for pid, kind in sel["parameters"].items():
        v = f"v_{raw[pid][:-4]}"
        pattern, expected = (intg, "a positive integer") if kind == "INTEGER" else (num, "a positive number of months")
        cases.append(f"WHEN {v} IS NOT NULL AND NOT (REGEXP_LIKE({v}, {pattern}) AND TRY_TO_DOUBLE(TRIM({v}, {ws})) > 0) "
                     f"THEN OBJECT_CONSTRUCT('p', {q(pid)}, 'e', {q(expected)}, 'v', {v})")
    b, a = f"v_{raw[sel['below']][:-4]}", f"v_{raw[sel['above']][:-4]}"
    cases.append(f"WHEN {b} IS NOT NULL AND {a} IS NOT NULL AND TRY_TO_DOUBLE(TRIM({a}, {ws})) >= TRY_TO_DOUBLE(TRIM({b}, {ws})) "
                 f"THEN OBJECT_CONSTRUCT('p', {q(sel['above'])}, 'e', {q('lower than ' + sel['below'] + ' (')} || TRIM({b}, {ws}) || ')', "
                 f"'v', TRIM({a}, {ws}))")
    cols.append("CASE " + " ".join(cases) + " END AS sel_bad")
    cols.append(f"IFF(sel_bad IS NULL, TRY_TO_DOUBLE(TRIM(v_below, {ws})), NULL) AS sel_below")
    cols.append(f"IFF(sel_bad IS NULL, TRY_TO_DOUBLE(TRIM(v_above, {ws})), NULL) AS sel_above")
    cols.append(f"IFF(sel_bad IS NULL, TRY_TO_NUMBER(TRIM(v_rank, {ws})), NULL) AS sel_rank")
    cols.append("sel_bad IS NULL AND (v_below IS NOT NULL OR v_above IS NOT NULL OR v_rank IS NOT NULL) AS sel_on")
    return ",\n           ".join(cols)

# ================================================================================================ session 8c-0: basis and selection

def post_template(c: dict) -> str:
    """The end of the coverage statement, as SQL with placeholders filled at call time from the checked request:
    <<BASIS>>, <<ON>> (a selection is asked), <<COND>> and <<RANK>> (its criteria), <<ORDER>>, <<GORDER>>,
    <<ROWORDER>>, <<MEMBER>> (the grain), <<NOSUM>>, <<ROWOBJ>>. Each row's stock unit and stockout month; the member
    selection on detail rows, per analysis month (NO_STOCK and NO_DEMAND set apart); the summary of the kept rows (their
    count, their stock per unit); the BASIS_NOT_COMPARABLE reason, judged on the rows the call returns."""
    b, sel = c["basis"], c["selection"]
    unit = ("CASE '<<BASIS>>'" + "".join(
        f" WHEN {q(x)} THEN " + {"FIXED": q(b["fixed_unit"].get(x, "")), "ITEM_BASE_UNIT": "IFF(n_dims = 1, base_unit, NULL)",
                                 "ITEM_NATIVE_UNIT": "IFF(n_items = 1, native_unit, NULL)"}[src]
        for x, src in b["unit_source"].items()) + " END")
    none = ", ".join(q(f) for f in c["stockout_none_flags"])
    apart = ", ".join(q(f) for f in sel["apart_flags"])
    rule = {"ONE_ITEM_PER_ROW": "val.mi <= 1", "ONE_DIMENSION_PER_ROW": "val.md <= 1", "ALWAYS": "TRUE"}
    valid = "CASE '<<BASIS>>'" + "".join(f" WHEN {q(x)} THEN {rule[r]}" for x, r in b["valid_when"].items()) + " END"
    allowed = ("ARRAY_TO_STRING(ARRAY_CONSTRUCT_COMPACT(" + ", ".join(
        q(x) if r == "ALWAYS" else f"IFF({rule[r]}, {q(x)}, NULL)" for x, r in b["valid_when"].items()) + "), ', ')")
    reason = render(c["refusals"]["BASIS_NOT_COMPARABLE"], {"basis": "'<<BASIS>>'", "why": case_map("'<<BASIS>>'", b["why"]),
                                                             "allowed": allowed})
    aliases = [(f, f"a{i}") for i, f in enumerate(sel["apart_flags"])]
    apart_obj = ", ".join(f"{q(f)}, OBJECT_CONSTRUCT('count', COALESCE({a}.n, 0), 'members', COALESCE({a}.members, ARRAY_CONSTRUCT()))"
                          for f, a in aliases)
    apart_joins = "".join(f"\n    LEFT JOIN ka {a} ON {a}.as_of_month = am.as_of_month AND {a}.flag = {q(f)}" for f, a in aliases)
    return f""",
r1 AS (
    SELECT cr.*, {unit} AS stock_unit,
           IFF(coverage_months IS NULL OR flag IN ({none}), NULL, DATEADD(month, CEIL(coverage_months)::INT, as_of_month)) AS stockout_month,
           <<ON>> AND row_type = 'DETAIL' AND COALESCE(flag IN ({apart}), FALSE) AS apart,
           <<ON>> AND row_type = 'DETAIL' AND NOT COALESCE(flag IN ({apart}), FALSE)<<COND>> AS candidate
    FROM cr
),
r2 AS (
    SELECT r1.*, IFF(candidate, ROW_NUMBER() OVER (PARTITION BY as_of_month, candidate ORDER BY coverage_months ASC<<ORDER>>), NULL) AS rk
    FROM r1
),
r3 AS (
    SELECT r2.*, candidate AND <<RANK>> AS kept FROM r2
    WHERE NOT <<ON>> OR row_type <> 'DETAIL' OR apart OR (candidate AND <<RANK>>)
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
    SELECT as_of_month, ARRAY_AGG(OBJECT_CONSTRUCT('unit', stock_unit, 'amount', kept_stock)) WITHIN GROUP (ORDER BY stock_unit) AS stock
    FROM (SELECT DISTINCT as_of_month, stock_unit, kept_stock FROM r4 WHERE kept) GROUP BY as_of_month
),
ka AS (
    SELECT as_of_month, flag, COUNT(*) AS n, ARRAY_AGG(<<MEMBER>>) WITHIN GROUP (ORDER BY <<GORDER>>) AS members
    FROM r4 WHERE apart GROUP BY as_of_month, flag
),
sel AS (
    SELECT ARRAY_AGG(OBJECT_CONSTRUCT_KEEP_NULL('as_of_month', TO_VARCHAR(am.as_of_month, 'YYYY-MM-DD'), 'kept', COALESCE(km.kept, 0),
               'stock', IFF(<<NOSUM>> AND COALESCE(km.kept, 0) > 1, NULL, COALESCE(ku.stock, ARRAY_CONSTRUCT())),
               'set_apart', OBJECT_CONSTRUCT({apart_obj}))) WITHIN GROUP (ORDER BY am.as_of_month) AS by_month
    FROM analysis_months am
    LEFT JOIN km ON km.as_of_month = am.as_of_month
    LEFT JOIN ku ON ku.as_of_month = am.as_of_month{apart_joins}
)
SELECT OBJECT_CONSTRUCT(
           'COVERAGE_ROWS', COALESCE((SELECT ARRAY_AGG(<<ROWOBJ>>) WITHIN GROUP (ORDER BY as_of_month, grain_set, rk NULLS LAST<<ROWORDER>>) FROM ret), ARRAY_CONSTRUCT()),
           'ROW_COUNT', (SELECT COUNT(*) FROM ret),
           'FLAGS', COALESCE((SELECT ARRAY_AGG(DISTINCT flag) WITHIN GROUP (ORDER BY flag) FROM ret), ARRAY_CONSTRUCT()),
           'SELECTION', IFF(<<ON>>, OBJECT_CONSTRUCT('by_month', sel.by_month), NULL),
           'BASIS_REASON', IFF({valid}, NULL, {reason})) AS CV
FROM sel, val"""

# ================================================================================================ the procedure body

CONTEXT_CODES = {"AS_OF_NO_SNAPSHOT", "HORIZON_NOT_LOADED"}      # plan checks that read the context statement


def body(c: dict, context_sql: str, caller_sql: str) -> str:
    pre, post, final = pre_checks(c), post_checks(c), final_checks(c)
    plan = plan_checks(c)
    order = c["refusal_order"]
    covered = set(pre) | set(plan) | set(post) | set(final)
    if covered != set(order):
        raise ValueError(f"codes without a check: {set(order) - covered}; checks without a code: {covered - set(order)}")
    if not CONTEXT_CODES <= set(plan):
        raise ValueError(f"context codes not planned: {sorted(CONTEXT_CODES - set(plan))}")
    stage = ({k: 0 for k in pre} | {k: (1 if k in CONTEXT_CODES else 2) for k in plan} | {k: 3 for k in post}
             | {k: 4 for k in final})
    if [stage[k] for k in order] != sorted(stage[k] for k in order):
        raise ValueError("stages break check_order")
    post_code = "".join(post[k] for k in order if k in post)
    final_code = "".join(final[k] for k in order if k in final)
    scope = c["default_scope"]
    contract = f"OBJECT_CONSTRUCT('id', {q(c['id'])}, 'version', {q(c['version'])})"
    caller = ("OBJECT_CONSTRUCT_KEEP_NULL('current_role', pre:CALLER_ROLE, 'current_secondary_roles', pre:CALLER_SECONDARY_ROLES, "
              "'current_user', pre:CALLER_USER, 'is_agent_activated', pre:AGENT_ACTIVATED)")
    available = ("IFF(plan IS NULL, NULL, OBJECT_CONSTRUCT_KEEP_NULL('first', plan:AVAILABLE_FIRST, 'last', plan:AVAILABLE_LATEST, "
                 "'latest', plan:AVAILABLE_LATEST))")
    timing = ("OBJECT_CONSTRUCT('context_ms', DATEDIFF('millisecond', t1, t2), 'quality_ms', DATEDIFF('millisecond', t3, t4), "
              "'coverage_ms', DATEDIFF('millisecond', t3, t5), 'total_ms', DATEDIFF('millisecond', t0, CURRENT_TIMESTAMP()))")
    return f"""
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
{plan_sql(c, context_sql, 'params')}
    ));
    rs_b := ASYNC (SELECT T FROM (
{plan_sql(c, context_sql, 'base')}
    ));
    rs_tq := ASYNC (SELECT T FROM (
{plan_sql(c, context_sql, 'quality')}
    ));
    rs_tc := ASYNC (SELECT T FROM (
{plan_sql(c, context_sql, 'coverage')}
    ));
    -- ---- the as_of_months checks, one statement that reads no table (also the caller block)
    SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) INTO :pre FROM (
{pre_sql(c, caller_sql)}
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
{plan_sql(c, context_sql, 'context').replace(':parsed', ':parsed_json')}
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
    req := TO_JSON(OBJECT_CONSTRUCT('months', plan:MONTHS, 'filters', par:FILTERS, 'scope', {arr(scope['included'])}));
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
    -- ---- data checks, in check_order{post_code}
    AWAIT rs_c;
    LET cur_c CURSOR FOR rs_c;
    OPEN cur_c;
    FETCH cur_c INTO cv;
    t5 := CURRENT_TIMESTAMP();
    -- ---- the basis, judged on the rows the coverage statement returns{final_code}
  EXCEPTION
    WHEN refused THEN
      IF (jobs_started) THEN
        CANCEL rs_c;
      END IF;
      RETURN OBJECT_CONSTRUCT('status', 'refused', 'contract', {contract},
               'refusal', OBJECT_CONSTRUCT('code', rcode, 'reason', reason), 'available_months', {available},
               'caller', {caller}, 'lineage', OBJECT_CONSTRUCT('query_ids', COALESCE(lineage, OBJECT_CONSTRUCT())),
               'timing_ms', OBJECT_CONSTRUCT_KEEP_NULL('context_ms', DATEDIFF('millisecond', t1, t2), 'quality_ms', DATEDIFF('millisecond', t3, t4),
                                                      'total_ms', DATEDIFF('millisecond', t0, CURRENT_TIMESTAMP())));
  END;
  RETURN OBJECT_CONSTRUCT('status', 'ok', 'contract', {contract},
           'request', OBJECT_CONSTRUCT_KEEP_NULL('as_of_months', plan:MONTHS, 'basis', par:BASIS, 'grain', par:GRAIN,
                                       'filters', par:FILTERS, 'totals', par:TOTALS, {q(c['selection']['below'])}, par:SEL_BELOW,
                                       {q(c['selection']['above'])}, par:SEL_ABOVE, {q(c['selection']['rank'])}, par:SEL_RANK),
           'applicability', OBJECT_CONSTRUCT_KEEP_NULL('stock_and_forecast', par:STOCK_AND_FORECAST, 'stock_only', par:STOCK_ONLY,
                                                       'default_scope', IFF(par:SCOPE_ON::BOOLEAN,
                                                         OBJECT_CONSTRUCT({q(scope['attribute'])}, {arr(scope['included'])}), NULL)),
           'rows', COALESCE(cv:COVERAGE_ROWS, ARRAY_CONSTRUCT()), 'row_count', cv:ROW_COUNT,
           'flags', COALESCE(cv:FLAGS, ARRAY_CONSTRUCT()), 'warnings', COALESCE(qv:WARNINGS, ARRAY_CONSTRUCT()),
           'selection', cv:SELECTION,
           'note', {q(c['note'])}, 'available_months', {available}, 'caller', {caller},
           'lineage', OBJECT_CONSTRUCT('query_ids', lineage), 'timing_ms', {timing});
END;
"""
