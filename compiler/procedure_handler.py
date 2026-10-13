"""
Handler template of the generated stock coverage procedure.

compiler/gen_procedure.py replaces the CONTRACT line below with the values it reads from contract/stock_coverage.yaml
and wraps this file into generated/stock_coverage_procedure.sql. Nothing in this file names a table, a column, an
attribute, a unit, a refusal reason or a warning message: they all come from CONTRACT. What lives here is the
mechanism: parsing, the checks in the contract's order, SQL assembly with bind variables, the JSON answer.

The pure part (parsing and parameter checks) runs without Snowflake, so tests/test_procedure_local.py exercises it
locally; the rest needs a Snowpark session.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import time

CONTRACT: dict = {}  # INJECTED BY compiler/gen_procedure.py


# ================================================================================================ helpers

class Refusal(Exception):
    def __init__(self, code: str, **values):
        super().__init__(code)
        self.code, self.values = code, values


class _Keep(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def message(template: str, **values) -> str:
    return template.format_map(_Keep({k: _show(v) for k, v in values.items()}))


def _show(v):
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".")
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    return v


def rank(a: str):
    """Order in which several attributes are named: the contract's declaration order; a name the contract does not
    declare comes after every declared one, such names in alphabetical order (session 8b, owner: never the JSON key
    order)."""
    order = list(CONTRACT["attributes"])
    return (order.index(a), "") if a in order else (len(order), a)


def compact(v) -> str:
    """A nested value (array or object) shown in a message: compact JSON (session 8b, owner)."""
    return json.dumps(v, separators=(",", ":"))


def month_add(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.month - 1 + n, 12)
    return dt.date(d.year + y, m + 1, 1)


def _json_or_list(raw, expect):
    """A JSON value of the expected type, or (lenient, as probe C0) a bare value or a comma-separated list."""
    s = raw.strip()
    if s[:1] in "[{":
        v = json.loads(s)
    elif expect is list:
        v = [x.strip() for x in s.split(",") if x.strip()]
    else:
        raise ValueError("not a JSON object")
    if not isinstance(v, expect):
        raise ValueError("wrong JSON type")
    return v


# ================================================================================================ parameter checks
# One function per refusal code. Each reads and writes the request state `st` and raises Refusal. They run in the
# contract's check_order (CONTRACT["refusal_order"]); the generator fails if a code has no check here or a check
# has no code in the contract.

def chk_as_of_missing(st):
    raw = st["raw"]["as_of_months"]
    if raw is None or str(raw).strip() in ("", "[]", "null"):
        raise Refusal("AS_OF_MISSING")


def chk_as_of_invalid(st):
    raw = str(st["raw"]["as_of_months"])
    try:
        values = _json_or_list(raw, list)
    except ValueError:
        raise Refusal("AS_OF_INVALID", value=raw)
    if not values:
        raise Refusal("AS_OF_MISSING")
    parsed = []
    for v in values:
        s = str(v).strip() if isinstance(v, (str, int)) else None
        if s is None:
            raise Refusal("AS_OF_INVALID", value=compact(v) if isinstance(v, (list, dict)) else v)
        if s.upper() == CONTRACT["latest_token"]:
            parsed.append(CONTRACT["latest_token"])
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            raise Refusal("AS_OF_INVALID", value=s)
        try:
            parsed.append(dt.date.fromisoformat(s))
        except ValueError:
            raise Refusal("AS_OF_INVALID", value=s)
    st["as_of"] = parsed


def chk_as_of_not_month_start(st):
    for d in st["as_of"]:
        if isinstance(d, dt.date) and d.day != 1:
            raise Refusal("AS_OF_NOT_MONTH_START", value=d.isoformat(), month_start=d.replace(day=1).isoformat())


def chk_as_of_too_many(st):
    seen = []
    for d in st["as_of"]:
        if d not in seen:
            seen.append(d)
    st["as_of"] = seen
    if len(seen) > CONTRACT["max_periods"]:
        raise Refusal("AS_OF_TOO_MANY", max_periods=CONTRACT["max_periods"])


def chk_as_of_no_snapshot(st):
    ctx = st["context"]()
    available, latest = ctx["available"], ctx["latest"]
    out = []
    for d in st["as_of"]:
        if d == CONTRACT["latest_token"]:
            if latest is None:
                raise Refusal("AS_OF_NO_SNAPSHOT", value=d, latest="none", available_months="none")
            d = latest
        if d not in ctx["snapshots"]:
            raise Refusal("AS_OF_NO_SNAPSHOT", value=d.isoformat(), latest=_iso(latest),
                          available_months=[m.isoformat() for m in available])
        if d not in out:
            out.append(d)
    st["months"] = out


def chk_horizon_not_loaded(st):
    ctx = st["context"]()
    for q in CONTRACT["quality"]:
        if q["refusal"] == "HORIZON_NOT_LOADED" and ctx["quality"].get(q["id"]):
            raise Refusal("HORIZON_NOT_LOADED", source=q["source"], horizon=CONTRACT["horizon"],
                          horizon_end=month_add(ctx["latest_snapshot"], CONTRACT["horizon"]).isoformat(),
                          latest=ctx["latest_snapshot"].isoformat())
    for d in st["months"]:
        if d not in ctx["available"]:
            raise Refusal("HORIZON_NOT_LOADED", source="calendar or forecast", horizon=CONTRACT["horizon"],
                          horizon_end=month_add(d, CONTRACT["horizon"]).isoformat(), latest=d.isoformat())


def _unit_key(raw) -> str:
    return re.sub(r"[\s-]+", "_", str(raw or "").strip().upper())


def chk_basis_unknown(st):
    """The basis named (an id or a synonym), the contract's default basis when none is named (contract 0.5.0)."""
    raw = st["raw"]["basis"]
    if raw is None or str(raw).strip() in ("", "null"):
        st["basis"] = CONTRACT["basis"]["default"]
        return
    u = _unit_key(raw)
    for bid, names in CONTRACT["basis"]["names"].items():
        if u in names:
            st["basis"] = bid
            return
    raise Refusal("BASIS_UNKNOWN", value=raw)


NUMBER = re.compile(r"\s*[0-9]+(\.[0-9]+)?\s*")
INTEGER = re.compile(r"\s*[0-9]+\s*")


def chk_selection_invalid(st):
    """coverage_below and coverage_above: positive numbers; rank_first: a positive integer; a window must be open."""
    sel, raw = {}, {}
    for pid, kind in CONTRACT["selection"]["parameters"].items():
        v = st["raw"].get(pid)
        if v is None or str(v).strip() in ("", "null"):
            continue
        s = str(v)
        pattern, expected = (INTEGER, "a positive integer") if kind == "INTEGER" else (NUMBER, "a positive number of months")
        if not pattern.fullmatch(s) or float(s) <= 0:
            raise Refusal("SELECTION_INVALID", parameter=pid, expected=expected, value=s)
        sel[pid], raw[pid] = (int(s) if kind == "INTEGER" else float(s)), s.strip()
    below, above = CONTRACT["selection"]["below"], CONTRACT["selection"]["above"]
    if below in sel and above in sel and sel[above] >= sel[below]:
        raise Refusal("SELECTION_INVALID", parameter=above, expected=f"lower than {below} ({raw[below]})",
                      value=raw[above])
    st["selection"] = sel


def chk_basis_not_comparable(st):
    """Judged on the rows and totals the call returns (after the selection), once they are read; a no-op before."""
    rows = st.get("returned")
    if rows is None:
        return
    b = st["basis"]
    allowed = [x for x, rule in CONTRACT["basis"]["valid_when"].items()
               if rule == "ALWAYS" or all(r[{"ONE_ITEM_PER_ROW": "N_ITEMS", "ONE_DIMENSION_PER_ROW": "N_DIMS"}[rule]] <= 1
                                          for r in rows)]
    if b not in allowed:
        raise Refusal("BASIS_NOT_COMPARABLE", basis=b, why=CONTRACT["basis"]["why"][b], allowed=allowed)


def chk_grain_malformed(st):
    raw = st["raw"]["grain"]
    try:
        g = [] if raw is None or str(raw).strip() == "" else _json_or_list(str(raw), list)
    except ValueError:
        raise Refusal("GRAIN_MALFORMED")
    if any(not isinstance(x, str) for x in g):
        raise Refusal("GRAIN_MALFORMED")
    st["grain"] = [x.strip().lower() for x in g]


def chk_grain_empty(st):
    if not st["grain"]:
        raise Refusal("GRAIN_EMPTY")


def chk_grain_duplicate(st):
    dup = sorted({a for a in st["grain"] if st["grain"].count(a) > 1}, key=rank)
    if dup:
        raise Refusal("GRAIN_DUPLICATE", value=dup)


def chk_filters_malformed(st):
    raw = st["raw"]["filters"]
    if raw is None or str(raw).strip() in ("", "null"):
        raw = CONTRACT["filters_default"]
    try:
        f = _json_or_list(str(raw), dict)
    except ValueError:
        raise Refusal("FILTERS_MALFORMED")
    st["filters"] = {str(k).strip().lower(): v for k, v in f.items()}


def chk_filter_values_invalid(st):
    out = {}
    for a in sorted(st["filters"], key=rank):
        v = st["filters"][a]
        v = [v] if isinstance(v, (str, int, float)) and not isinstance(v, bool) else v
        if not isinstance(v, list) or not v or any(x is None or isinstance(x, (list, dict, bool)) for x in v):
            raise Refusal("FILTER_VALUES_INVALID", attribute=a)
        out[a] = [str(x) for x in v]
    st["filters"] = out


def _used(st):
    return list(dict.fromkeys(st["grain"] + list(st["filters"])))


def chk_attribute_unknown(st):
    for a in sorted(_used(st), key=rank):
        if a not in CONTRACT["attributes"] and a not in CONTRACT["unclassified"]:
            raise Refusal("ATTRIBUTE_UNKNOWN", attribute=a, conformed=CONTRACT["classes"]["CONFORMED"],
                          snapshot_only=CONTRACT["classes"]["SNAPSHOT_ONLY"])


def chk_attribute_unclassified(st):
    for a in sorted(_used(st), key=rank):
        if a in CONTRACT["unclassified"]:
            raise Refusal("ATTRIBUTE_UNCLASSIFIED", attribute=a)


def chk_attribute_not_applicable(st):
    for a in sorted(_used(st), key=rank):
        if CONTRACT["attributes"][a]["class"] == "NOT_APPLICABLE":
            raise Refusal("ATTRIBUTE_NOT_APPLICABLE", attribute=a, reason=CONTRACT["attributes"][a]["description"])


def chk_totals_malformed(st):
    raw = st["raw"]["totals"]
    if raw is None or str(raw).strip() in ("", "null"):
        raw = CONTRACT["totals_default"]
    try:
        t = _json_or_list(str(raw), list) if str(raw).strip()[:1] == "[" else None
    except ValueError:
        t = None
    if t is None or any(not isinstance(x, list) or any(not isinstance(a, str) for a in x) for x in t):
        raise Refusal("TOTALS_MALFORMED")
    out = []
    for x in t:
        x = [a.strip().lower() for a in x]
        if x not in out:
            out.append(x)
    st["totals"] = out


def chk_totals_not_subset(st):
    for t in st["totals"]:
        if not set(t) < set(st["grain"]) or len(set(t)) != len(t):
            raise Refusal("TOTALS_NOT_SUBSET", value=t, grain=st["grain"])


def chk_master_data_fanout(st):
    q = st["quality"]()
    if q["fanout"]:
        raise Refusal("MASTER_DATA_FANOUT", count=q["fanout"], attributes=q["fanout_attributes"])


def chk_data_quality_failed(st):
    ctx = st["context"]()
    for q in CONTRACT["quality"]:
        if q["on_failure"] == "REFUSE" and q["refusal"] == "DATA_QUALITY_FAILED" and ctx["quality"].get(q["id"]):
            raise Refusal("DATA_QUALITY_FAILED", expectation=q["id"], count=ctx["quality"][q["id"]],
                          condition=q["condition"])


CHECKS = {name[4:].upper(): fn for name, fn in list(globals().items()) if name.startswith("chk_")}


# ================================================================================================ SQL assembly

class Sql:
    """Text with ? placeholders and their binds, appended in order."""

    def __init__(self):
        self.parts, self.binds = [], []

    def add(self, text: str, *binds):
        self.parts.append(text)
        self.binds.extend(binds)
        return self

    def text(self) -> str:
        return "".join(self.parts)


def _alias(table: str) -> str:
    return CONTRACT["aliases"][table]


def _col(a: str) -> str:
    at = CONTRACT["attributes"][a]
    return f"{_alias(at['table'])}.{at['column']}"


def _in(sql: Sql, expr: str, values: list[str]) -> str:
    sql.binds.extend(values)
    return f"{expr} IN ({', '.join('?' for _ in values)})"


def plan(st) -> dict:
    """Route every used attribute: grain and filters per measure, default scope, dimension joins."""
    attrs = CONTRACT["attributes"]
    conformed = [a for a in st["grain"] if attrs[a]["class"] == "CONFORMED"]
    scope = CONTRACT["default_scope"]
    scope_on = scope["attribute"] not in st["filters"]
    stock_filters = dict(st["filters"])
    flow_filters = {a: v for a, v in st["filters"].items() if attrs[a]["class"] == "CONFORMED"}
    used = _used(st) + [scope["attribute"]]
    return {"grain": st["grain"], "conformed": conformed, "stock_filters": stock_filters,
            "flow_filters": flow_filters, "scope_on": scope_on, "used": list(dict.fromkeys(used)),
            "grains": [st["grain"]] + st["totals"]}


def _joins(fact: dict, used: list[str]) -> str:
    """Joins from a fact table to the dimensions the used attributes live on. A dimension whose grain may be
    duplicated (REFUSE_IF_USED) is joined through a DISTINCT projection of its key and the used columns."""
    attrs, out = CONTRACT["attributes"], []
    tables = []
    for a in used:
        t = attrs[a]["table"]
        if t != fact["table"] and t in fact["joins"] and t not in tables:
            tables.append(t)
    for t in tables:
        frm, to = fact["joins"][t]
        al = _alias(t)
        if t in CONTRACT["dedup_tables"]:
            cols = list(dict.fromkeys(to + [attrs[a]["column"] for a in used if attrs[a]["table"] == t]))
            src = f"(SELECT DISTINCT {', '.join(cols)} FROM {CONTRACT['tables'][t]})"
        else:
            src = CONTRACT["tables"][t]
        on = " AND ".join(f"{al}.{c2} = {_alias(fact['table'])}.{c1}" for c1, c2 in zip(frm, to))
        out.append(f"\n    JOIN {src} {al} ON {on}")
    return "".join(out)


def base_ctes(st, p, sql: Sql) -> None:
    """analysis_months, months, stock_rows (every filter, default scope not yet applied), fc_rows (conformed filters)."""
    snap, flow = CONTRACT["snapshot"], CONTRACT["flow"]
    h, k0 = CONTRACT["horizon"], CONTRACT["window_start"]
    s_col, f_col = CONTRACT["basis"]["columns"][st["basis"]]
    scope_col = CONTRACT["basis"]["scope_column"][st["basis"]]
    sa, fa = _alias(snap["table"]), _alias(flow["table"])
    sql.add("WITH analysis_months AS (\n    SELECT column1::DATE AS as_of_month FROM VALUES "
            + ", ".join("(?)" for _ in st["months"]) + "\n),\n", *[d.isoformat() for d in st["months"]])
    sql.add(f"months AS (\n    SELECT {k0} - 1 + ROW_NUMBER() OVER (ORDER BY SEQ4()) AS k "
            f"FROM TABLE(GENERATOR(ROWCOUNT => {h}))\n),\n")
    used = p["used"]
    sel = "".join(f", {_col(a)} AS {a}" for a in p["grain"])
    scope = CONTRACT["default_scope"]
    stock_where = " AND ".join([_in(sql, _col(a), v) for a, v in p["stock_filters"].items()] or ["TRUE"])
    keys = "".join(f"{sa}.{k}, " for k in CONTRACT["member_keys"])
    sql.parts.append(
        f"stock_rows AS (\n    SELECT a.as_of_month, {keys}{sel[2:]}{', ' if sel else ''}"
        f"{_col(scope['attribute'])} AS scope_value, {sa}.{s_col}::FLOAT AS qty, {sa}.{scope_col}::FLOAT AS scope_qty\n"
        f"    FROM analysis_months a\n    JOIN {CONTRACT['tables'][snap['table']]} {sa} ON {sa}.{snap['time_column']} = a.as_of_month"
        f"{_joins(snap, used)}\n    WHERE {stock_where}\n),\n")
    flow_used = [a for a in used if CONTRACT["attributes"][a]["class"] == "CONFORMED"]
    fsel = "".join(f", {_col(a)} AS {a}" for a in p["conformed"])
    flow_where = " AND ".join([_in(sql, _col(a), v) for a, v in p["flow_filters"].items()] or ["TRUE"])
    sql.parts.append(
        f"fc_rows AS (\n    SELECT a.as_of_month, {''.join(f'{fa}.{k}, ' for k in CONTRACT['member_keys'])}{fsel[2:]}{', ' if fsel else ''}"
        f"DATEDIFF(month, a.as_of_month, {fa}.{flow['time_column']}) AS k, {fa}.{f_col}::FLOAT AS qty\n"
        f"    FROM analysis_months a\n    JOIN {CONTRACT['tables'][flow['table']]} {fa}\n"
        f"      ON {fa}.{flow['time_column']} >= DATEADD(month, {k0}, a.as_of_month)\n"
        f"     AND {fa}.{flow['time_column']} <= DATEADD(month, {k0 + h - 1}, a.as_of_month)"
        f"{_joins(flow, flow_used)}\n    WHERE {flow_where}\n)")
    ib = CONTRACT["basis"]["item"]
    sql.parts.append(f",\nitems AS (SELECT DISTINCT {ib['key']} AS item_id, {ib['dimension']} AS dimension, "
                     f"{ib['base_unit']} AS base_unit, {ib['native_unit']} AS native_unit FROM {ib['table']})")


def _scope_pred(p, sql: Sql) -> str:
    if not p["scope_on"]:
        return "TRUE"
    return _in(sql, "scope_value", CONTRACT["default_scope"]["included"])


def coverage_sql(st, p) -> Sql:
    sql = Sql()
    base_ctes(st, p, sql)
    stock_pred = _scope_pred(p, sql)
    attrs = CONTRACT["attributes"]
    g = p["grain"]
    sql.parts.append(f",\nstock AS (\n    SELECT as_of_month{''.join(', ' + a for a in g)}, SUM(qty) AS stock_qty\n"
                     f"    FROM stock_rows WHERE {stock_pred}\n    GROUP BY ALL\n)")
    sql.parts.append(f",\nfc AS (\n    SELECT as_of_month{''.join(', ' + a for a in p['conformed'])}, k, SUM(qty) AS fc_qty\n"
                     f"    FROM fc_rows\n    GROUP BY ALL\n)")
    selects = []
    for n, gs in enumerate(p["grains"]):
        cg = [a for a in gs if attrs[a]["class"] == "CONFORMED"]
        snapshot_only = len(cg) != len(gs)
        key = "".join(", " + a for a in gs)
        ckey = "".join(", " + a for a in cg)
        members = f"SELECT as_of_month{key} FROM s{n}"
        if not snapshot_only or CONTRACT["flow_members"] == "ALWAYS":
            members += f"\n        UNION\n        SELECT as_of_month{key} FROM f{n}"
        on_s = "".join(f" AND EQUAL_NULL(s.{a}, mb.{a})" for a in gs)
        on_f = "".join(f" AND EQUAL_NULL(f.{a}, mb.{a})" for a in cg)
        on_i = "".join(f" AND EQUAL_NULL(i.{a}, mb.{a})" for a in gs)
        on_x = "".join(f" AND EQUAL_NULL(x.{a}, mb.{a})" for a in cg)
        xkey = "".join(", x." + a for a in gs)
        sql.parts.append(
            f",\ns{n} AS (SELECT as_of_month{key}, SUM(stock_qty) AS stock_qty FROM stock GROUP BY ALL),\n"
            f"f{n} AS (SELECT as_of_month{ckey}, k, SUM(fc_qty) AS fc_qty FROM fc GROUP BY ALL),\n"
            f"m{n} AS (\n        {members}\n),\n"
            # session 8c-0: the items of each member (its stock items, the forecast items of its conformed key) and
            # their dimensions, which decide the bases the row can be measured on
            f"i{n} AS (\n    SELECT x.as_of_month{xkey}, COUNT(DISTINCT x.item_id) AS n_items, COUNT(DISTINCT it.dimension) AS n_dims,\n"
            f"           MIN(it.base_unit) AS base_unit, MIN(it.native_unit) AS native_unit\n"
            f"    FROM (SELECT as_of_month{key}, item_id FROM stock_rows WHERE {_scope_pred(p, sql)}\n"
            f"          UNION\n"
            f"          SELECT mb.as_of_month{''.join(', mb.' + a for a in gs)}, x.item_id FROM m{n} mb JOIN fc_rows x "
            f"ON x.as_of_month = mb.as_of_month{on_x}) x\n"
            f"    JOIN items it ON it.item_id = x.item_id\n    GROUP BY ALL\n),\n"
            f"d{n} AS (\n    SELECT mb.*, m.k, COALESCE(s.stock_qty, 0) AS stock_qty, COALESCE(f.fc_qty, 0) AS fc_qty\n"
            f"    FROM (SELECT m0.*, i.n_items, i.n_dims, i.base_unit, i.native_unit FROM m{n} m0 LEFT JOIN i{n} i\n"
            f"          ON i.as_of_month = m0.as_of_month{''.join(f' AND EQUAL_NULL(i.{a}, m0.{a})' for a in gs)}) mb\n"
            f"    CROSS JOIN months m\n"
            f"    LEFT JOIN s{n} s ON s.as_of_month = mb.as_of_month{on_s}\n"
            f"    LEFT JOIN f{n} f ON f.as_of_month = mb.as_of_month AND f.k = m.k{on_f}\n),\n"
            f"c{n} AS (\n    SELECT *, SUM(fc_qty) OVER (PARTITION BY as_of_month{key} ORDER BY k "
            f"ROWS UNBOUNDED PRECEDING) AS cum_fc\n    FROM d{n}\n)")
        cols = ", ".join(f"{a}" if a in gs else f"NULL AS {a}" for a in g)
        row_type = "DETAIL" if n == 0 else "TOTAL"
        selects.append(
            f"SELECT '{row_type}' AS row_type, {n} AS grain_set, as_of_month, {cols},\n"
            f"       ANY_VALUE(stock_qty) AS stock, MAX(cum_fc) AS forecast_over_horizon,\n"
            f"       CASE\n"
            f"         WHEN ANY_VALUE(stock_qty) = 0 THEN 0\n"
            f"         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN\n"
            f"              SUM(CASE WHEN cum_fc - fc_qty >= stock_qty THEN 0\n"
            f"                       WHEN cum_fc <= stock_qty THEN 1\n"
            f"                       ELSE (stock_qty - (cum_fc - fc_qty)) / fc_qty END)\n"
            f"         WHEN MAX(cum_fc) = 0 THEN NULL\n"
            f"         ELSE ANY_VALUE(stock_qty) / AVG(NULLIF(fc_qty, 0))\n"
            f"       END AS coverage_months,\n"
            f"       CASE\n"
            f"         WHEN ANY_VALUE(stock_qty) = 0 THEN '{CONTRACT['flags']['SNAPSHOT_NULL_OR_ZERO']}'\n"
            f"         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN NULL\n"
            f"         WHEN MAX(cum_fc) = 0 THEN '{CONTRACT['flags']['NO_FLOW_IN_WINDOW']}'\n"
            f"         ELSE '{CONTRACT['flags']['BEYOND_HORIZON']}'\n"
            f"       END AS flag,\n"
            f"       ANY_VALUE(n_items) AS n_items, ANY_VALUE(n_dims) AS n_dims, ANY_VALUE(base_unit) AS base_unit,\n"
            f"       ANY_VALUE(native_unit) AS native_unit\n"
            f"FROM c{n} GROUP BY as_of_month{key}")
    sql.parts.append(",\ncr AS (\n" + "\nUNION ALL\n".join(selects) + "\n)" + post_sql(st, g)
                     + "\nORDER BY as_of_month, grain_set, rk NULLS LAST" + "".join(f", {a} NULLS LAST" for a in g))
    return sql


def post_sql(st, g: list[str]) -> str:
    """Session 8c-0, in SQL so that both targets share it: each row's stock unit and stockout month; the member
    selection (detail rows only, per analysis month; NO_STOCK and NO_DEMAND set apart); the summary of the kept rows
    (their count, their stock per unit) as window columns. Literals only: the basis and the selection are validated."""
    b, sel = CONTRACT["basis"], CONTRACT["selection"]
    s = st["selection"]
    on = "TRUE" if s else "FALSE"
    unit = (f"CASE '{st['basis']}'" + "".join(
        f" WHEN '{x}' THEN " + {"FIXED": f"'{b['fixed_unit'].get(x)}'", "ITEM_BASE_UNIT": "IFF(n_dims = 1, base_unit, NULL)",
                                "ITEM_NATIVE_UNIT": "IFF(n_items = 1, native_unit, NULL)"}[src]
        for x, src in b["unit_source"].items()) + " END")
    none = ", ".join(f"'{f}'" for f in CONTRACT["stockout_none_flags"])
    apart = ", ".join(f"'{f}'" for f in sel["apart_flags"])
    cond = "".join([f" AND coverage_months > 0 AND coverage_months <= {s[sel['below']]!r}" if sel["below"] in s else "",
                    f" AND coverage_months > {s[sel['above']]!r}" if sel["above"] in s else ""])
    rank = f"rk <= {s[sel['rank']]}" if sel["rank"] in s else "TRUE"
    order = "".join(f", {a} ASC NULLS LAST" for a in g)
    return (
        f",\nr1 AS (\n    SELECT cr.*, {unit} AS stock_unit,\n"
        f"           IFF(coverage_months IS NULL OR flag IN ({none}), NULL, "
        f"DATEADD(month, CEIL(coverage_months)::INT, as_of_month)) AS stockout_month,\n"
        f"           {on} AND row_type = 'DETAIL' AND COALESCE(flag IN ({apart}), FALSE) AS apart,\n"
        f"           {on} AND row_type = 'DETAIL' AND NOT COALESCE(flag IN ({apart}), FALSE){cond} AS candidate\n"
        f"    FROM cr\n),\n"
        f"r2 AS (\n    SELECT r1.*, IFF(candidate, ROW_NUMBER() OVER (PARTITION BY as_of_month, candidate "
        f"ORDER BY coverage_months ASC{order}), NULL) AS rk\n    FROM r1\n),\n"
        f"r3 AS (\n    SELECT r2.*, candidate AND {rank} AS kept FROM r2\n    WHERE NOT {on} OR row_type <> 'DETAIL' OR apart OR (candidate AND {rank})\n)\n"
        f"SELECT r3.*, COUNT_IF(kept) OVER (PARTITION BY as_of_month) AS kept_count,\n"
        f"       SUM(IFF(kept, stock, NULL)) OVER (PARTITION BY as_of_month, stock_unit) AS kept_stock\nFROM r3")


def quality_sql(st, p) -> tuple[Sql, list[str]]:
    """One row: every in-call check scoped to the request, the fan-out check, the default-scope exclusion."""
    sql = Sql()
    base_ctes(st, p, sql)
    attrs = CONTRACT["attributes"]
    item_key = CONTRACT["dedup_key"]
    keys = ", ".join(CONTRACT["member_keys"])
    sql.parts.append(f",\nscope_items AS (SELECT {item_key} FROM stock_rows UNION SELECT {item_key} FROM fc_rows),\n"
                     f"scope_pairs AS (SELECT DISTINCT as_of_month, {keys} FROM fc_rows)")
    used_dim = {}
    for a in p["used"]:
        t = attrs[a]["table"]
        if t in CONTRACT["dedup_tables"]:
            used_dim.setdefault(t, []).append(a)
    cols, fanout_attrs = [], []
    for q in CONTRACT["quality"]:
        if q["scope"] == "TABLE":
            continue
        if q["on_failure"] == "REFUSE_IF_USED":
            # FANOUT counts the items whose rows differ on any used attribute; FANOUT__<A> those that differ on A,
            # so that the refusal names only the attributes that actually differ.
            fanout_attrs = sorted(used_dim.get(q["table"], []), key=rank)
            having = " OR ".join(f"COUNT(DISTINCT {attrs[a]['column']}) > 1" for a in fanout_attrs) or "FALSE"
            cols.append(q["sql"].replace("{having}", "COUNT(*) > 1") + f" AS {q['id']}")
            cols.append(q["sql"].replace("{having}", having) + " AS FANOUT")
            for a in fanout_attrs:
                col = attrs[a]["column"]
                cols.append(q["sql"].replace("{having}", f"COUNT(DISTINCT {col}) > 1") + f" AS FANOUT__{a.upper()}")
                # Decision 3 of session 8b: the conflicting values, distinct, sorted, NULL excluded.
                cols.append(f"(SELECT ARRAY_AGG(DISTINCT {col}) WITHIN GROUP (ORDER BY {col}) FROM "
                            f"{CONTRACT['tables'][q['table']]} WHERE {item_key} IN (SELECT {item_key} FROM "
                            f"{CONTRACT['tables'][q['table']]} WHERE {item_key} IN (SELECT {item_key} FROM scope_items) "
                            f"GROUP BY {item_key} HAVING COUNT(DISTINCT {col}) > 1)) AS FANOUT_VALUES__{a.upper()}")
        else:
            cols.append(q["sql"] + f" AS {q['id']}")
    scope = CONTRACT["default_scope"]
    if p["scope_on"]:
        # per analysis month and unit of the basis (session 8c-0): EUR on a fixed-unit basis, else the base unit
        pred = _in(sql, "scope_value", scope["included"])
        fixed = CONTRACT["basis"]["fixed_unit"].get(st["basis"])
        u = f"'{fixed}'" if fixed else "it.base_unit"
        cols.append(f"(SELECT ARRAY_AGG(OBJECT_CONSTRUCT('m', TO_VARCHAR(m), 'unit', u, 'amt', amt)) WITHIN GROUP "
                    f"(ORDER BY m, u) FROM (SELECT s.as_of_month AS m, {u} AS u, SUM(s.scope_qty) AS amt "
                    f"FROM stock_rows s JOIN items it ON it.item_id = s.item_id WHERE NOT ({pred}) OR s.scope_value IS NULL "
                    f"GROUP BY 1, 2)) AS SCOPE_EXCLUDED")
    sql.parts.append("\nSELECT " + ",\n       ".join(cols))
    return sql, fanout_attrs


# ================================================================================================ entry point

def run(session, as_of_months, grain, filters, basis=None, totals=None, coverage_below=None, coverage_above=None,
        rank_first=None):
    t0 = time.perf_counter()
    timing, lineage = {}, {}
    st = {"raw": {"as_of_months": as_of_months, "basis": basis, "grain": grain, "filters": filters,
                  "totals": totals, "coverage_below": coverage_below, "coverage_above": coverage_above,
                  "rank_first": rank_first}, "selection": {}}
    cache = {}

    def context():
        if "context" not in cache:
            t = time.perf_counter()
            with session.query_history() as h:
                r = session.sql(CONTRACT["context_sql"]).collect()[0].as_dict()
            timing["context_ms"] = round((time.perf_counter() - t) * 1000)
            lineage["context"] = h.queries[-1].query_id
            snaps = sorted(dt.date.fromisoformat(x) for x in json.loads(r["SNAPSHOTS"] or "[]"))
            available = sorted(dt.date.fromisoformat(x) for x in json.loads(r["AVAILABLE"] or "[]"))
            cache["context"] = {
                "caller": _caller(r),
                "snapshots": snaps, "available": available,
                "latest": available[-1] if available else None,
                "latest_snapshot": snaps[-1] if snaps else None,
                "quality": {q["id"]: int(r[q["id"]] or 0) for q in CONTRACT["quality"] if q["scope"] == "TABLE"
                            and q["id"] in r},
            }
        return cache["context"]

    def quality():
        if "quality" not in cache:
            cache["quality"] = cache.pop("quality_job")()
        return cache["quality"]

    st["context"], st["quality"] = context, quality
    warnings = []

    def answer(status, **body):
        ctx = cache.get("context")
        out = {"status": status, "contract": {"id": CONTRACT["id"], "version": CONTRACT["version"]}}
        out.update(body)
        if ctx:
            out["available_months"] = {"first": _iso(ctx["available"][0] if ctx["available"] else None),
                                       "last": _iso(ctx["available"][-1] if ctx["available"] else None),
                                       "latest": _iso(ctx["latest"])}
            out["caller"] = ctx["caller"]
        else:
            out["caller"] = caller_only(session)
        # Lineage: the query id of each statement this call ran; its SQL text is read back from query history.
        out["lineage"] = {"query_ids": dict(lineage)}
        timing["total_ms"] = round((time.perf_counter() - t0) * 1000)
        out["timing_ms"] = timing
        return out

    try:
        for code in CONTRACT["refusal_order"]:
            if code == "MASTER_DATA_FANOUT" and "quality_job" not in cache and "quality" not in cache:
                start_jobs(session, st, cache, timing, lineage)
            CHECKS[code](st)
        if "quality_job" not in cache and "quality" not in cache:
            start_jobs(session, st, cache, timing, lineage)
    except Refusal as r:
        if "coverage_job" in cache:
            try:
                cache["coverage_job"].cancel()
            except Exception:  # noqa: BLE001  000605 when the query has already finished (measured)
                pass
        return answer("refused", refusal={"code": r.code, "reason": message(CONTRACT["refusals"][r.code], **r.values)})

    q = quality()
    for qe in CONTRACT["quality"]:
        if qe["scope"] == "TABLE" or qe["on_failure"] not in ("WARN", "REFUSE_IF_USED"):
            continue
        n = q["counts"].get(qe["id"], 0)
        if n:
            warnings.append({"code": qe["warning"], "expectation": qe["id"], "count": n,
                             "message": message(CONTRACT["warnings"][qe["warning"]], count=n, expectation=qe["id"],
                                                condition=qe["condition"])})
    scope = CONTRACT["default_scope"]
    for x in q["scope_excluded"] or []:          # per analysis month and unit (session 8c-0)
        if x["amt"]:
            warnings.append({"code": scope["warning"], "as_of_month": x["m"], "excluded_amount": float(x["amt"]),
                             "unit": x["unit"],
                             "message": message(CONTRACT["warnings"][scope["warning"]], excluded_amount=float(x["amt"]),
                                                unit=x["unit"]) + f" (as of {x['m']})"})
    rows = [r.as_dict() for r in cache.pop("coverage_job")()]
    p = st["plan"]
    sel = CONTRACT["selection"]
    returned = [d for d in rows if not d["APART"]]
    st["returned"] = returned
    try:
        CHECKS["BASIS_NOT_COMPARABLE"](st)
    except Refusal as r:
        return answer("refused", refusal={"code": r.code, "reason": message(CONTRACT["refusals"][r.code], **r.values)})
    out_rows = []
    for d in returned:
        n = d["GRAIN_SET"]
        row = {"row_type": d["ROW_TYPE"], "as_of_month": _iso(d["AS_OF_MONTH"])}
        if n:
            row["total_grain"] = p["grains"][n]
        row.update({a: d[a.upper()] for a in p["grain"]})
        row.update({"coverage_months": _num(d["COVERAGE_MONTHS"]), "stock": _num(d["STOCK"]),
                    "forecast_over_horizon": _num(d["FORECAST_OVER_HORIZON"]), "stock_unit": d["STOCK_UNIT"],
                    "stockout_month": _iso(d["STOCKOUT_MONTH"]), "flag": d["FLAG"]})
        out_rows.append(row)
    selection = None
    if st["selection"]:
        by_month = []
        for m in sorted(st["months"]):
            mrows = [d for d in rows if _iso(d["AS_OF_MONTH"]) == m.isoformat() and d["ROW_TYPE"] == "DETAIL"]
            kept = [d for d in mrows if d["KEPT"]]
            stock = {}
            for d in kept:
                stock.setdefault(d["STOCK_UNIT"], _num(d["KEPT_STOCK"]))
            by_month.append({
                "as_of_month": m.isoformat(), "kept": len(kept),
                "stock": None if st["basis"] in sel["no_sum_bases"] and len(kept) > 1
                else [{"unit": u, "amount": stock[u]} for u in sorted(stock)],
                "set_apart": {f: {"count": len(ms), "members": ms} for f in sel["apart_flags"]
                              for ms in [[{a: d[a.upper()] for a in p["grain"]} for d in mrows
                                          if d["APART"] and d["FLAG"] == f]]}})
        selection = {"by_month": by_month}
    attrs = CONTRACT["attributes"]
    used = _used(st)
    extra = {"selection": selection} if selection is not None else {}
    return answer(
        "ok",
        request={"as_of_months": [d.isoformat() for d in st["months"]], "basis": st["basis"],
                 "grain": st["grain"], "filters": st["filters"], "totals": st["totals"],
                 **{k: st["selection"].get(k) for k in sel["parameters"]}},
        applicability={"stock_and_forecast": [a for a in sorted(used, key=rank) if attrs[a]["class"] == "CONFORMED"],
                       "stock_only": [a for a in sorted(used, key=rank) if attrs[a]["class"] == "SNAPSHOT_ONLY"],
                       "default_scope": ({scope["attribute"]: scope["included"]} if p["scope_on"] else None)},
        rows=out_rows, row_count=len(out_rows), flags=sorted({r["flag"] for r in out_rows if r["flag"]}),
        warnings=warnings, note=CONTRACT["note"], **extra)


def _iso(d):
    return None if d is None else (d.isoformat() if hasattr(d, "isoformat") else str(d))


def _num(v):
    return None if v is None else float(v)


def differing_attributes(row: dict, attributes: list[str]) -> list[str]:
    """The used attributes on which at least one in-scope item has rows that differ (FANOUT__<A> > 0), each followed
    by its conflicting values (FANOUT_VALUES__<A>): "<column> (<v1>, <v2>)", at most MAX_VALUES values then
    "and <n> more" (session 8b, decision 3; the cap is CONTRACT["max_values"]). `attributes` is already in declaration
    order."""
    cap = CONTRACT["max_values"]
    out = []
    for a in attributes:
        if int(row.get(f"FANOUT__{a.upper()}") or 0) > 0:
            vals = row.get(f"FANOUT_VALUES__{a.upper()}") or []
            vals = [str(x) for x in (json.loads(vals) if isinstance(vals, str) else vals)]
            shown = ", ".join(vals[:cap]) + (f" and {len(vals) - cap} more" if len(vals) > cap else "")
            out.append(f"{a} ({shown})")
    return out


def caller_only(session):
    return _caller(session.sql(CONTRACT["caller_sql"]).collect()[0].as_dict())


def _caller(r):
    return {"current_role": r["CALLER_ROLE"], "current_secondary_roles": r["CALLER_SECONDARY_ROLES"],
            "current_user": r["CALLER_USER"], "is_agent_activated": r["AGENT_ACTIVATED"]}


def start_jobs(session, st, cache, timing, lineage):
    """Every parameter check has passed: start the quality query and the coverage query at once (asynchronous),
    then collect the quality result first. The coverage result is read only if no data check refuses."""
    p = st["plan"] = plan(st)
    qsql, fanout_attrs = quality_sql(st, p)
    csql = coverage_sql(st, p)
    t = time.perf_counter()
    qjob = session.sql(qsql.text(), params=qsql.binds).collect_nowait()
    cjob = session.sql(csql.text(), params=csql.binds).collect_nowait()
    lineage["quality"], lineage["coverage"] = qjob.query_id, cjob.query_id

    def read_quality():
        r = qjob.result()[0].as_dict()
        timing["quality_ms"] = round((time.perf_counter() - t) * 1000)
        counts = {k: int(v or 0) for k, v in r.items() if k.startswith("QE_")}
        excl = r.get("SCOPE_EXCLUDED")
        return {"counts": counts, "fanout": int(r.get("FANOUT") or 0),
                "fanout_attributes": differing_attributes(r, fanout_attrs),
                "scope_excluded": json.loads(excl) if isinstance(excl, str) else excl}

    def read_coverage():
        rows = cjob.result()
        timing["coverage_ms"] = round((time.perf_counter() - t) * 1000)
        return rows

    read_coverage.cancel = cjob.cancel
    cache["quality_job"], cache["coverage_job"] = read_quality, read_coverage
