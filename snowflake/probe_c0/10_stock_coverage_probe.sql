-- TEMPORARY probe, replaced by the generated procedure in Phase 3.
--
-- Probe C0 (session 3): stock coverage as a validated custom tool. Logic = docs/DEFINITION.md section 5 with the
-- member spine; applicability hard-coded from data/schema_v0.py (CONFORMED / STOCK_ONLY / UNIT_VARIANTS).
-- Language: Python, because validation, bind-parameter SQL assembly and a structured JSON answer take a few lines,
-- and the Phase 3 compiler that replaces it is Python too.
--
-- Run as LINKML_METRICS_ROLE with no secondary role:
--   snow sql -c linkml_svc -f snowflake/probe_c0/10_stock_coverage_probe.sql
--
-- Parameters
--   as_of_month   VARCHAR  required, 'YYYY-MM-01'; must have a stock snapshot. Kept VARCHAR so that a NULL, a
--                          mid-month or a malformed date returns a refusal, not a cast error or a number.
--   unit_variant  VARCHAR  QTY_EQ or VALUE. Raw units are refused: they do not add up across pack sizes.
--   grain         VARCHAR  attribute names (at least one), conformed or stock-only, as a JSON array or a
--                          comma-separated list. Not ARRAY: measured in session 3, an agent custom tool on a
--                          warehouse rejects an array argument ("argument type array which is not supported for
--                          execution environment type warehouse").
--   filters       VARCHAR  JSON object, attribute -> list of values. An object-typed parameter is not supported by
--                          agent custom tools, hence a JSON string. NULL or '' = no filter.
-- Returns a VARIANT: {"status": "ok", rows, flags, sql, binds, caller} or {"status": "refused", reason_code, reason}.
USE SECONDARY ROLES NONE;
USE ROLE LINKML_METRICS_ROLE;
DROP PROCEDURE IF EXISTS LINKML_METRICS.RAW.STOCK_COVERAGE_PROBE(VARCHAR, VARCHAR, ARRAY, VARCHAR);

CREATE OR REPLACE PROCEDURE LINKML_METRICS.RAW.STOCK_COVERAGE_PROBE(
    AS_OF_MONTH VARCHAR, UNIT_VARIANT VARCHAR, GRAIN VARCHAR, FILTERS VARCHAR)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.12'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
COMMENT = 'TEMPORARY probe, replaced by the generated procedure in Phase 3'
EXECUTE AS CALLER
AS
$$
import datetime as dt
import json
import re

HORIZON = 24
# data/schema_v0.py, section "Attribute applicability". attribute -> qualified column in the joined stock rows.
CONFORMED = {"sku_code": "i.sku_code", "family_code": "i.family_code", "range_code": "i.range_code",
             "country_code": "g.country_code", "region_code": "g.region_code"}
STOCK_ONLY = {"batch_status": "b.batch_status", "warehouse_code": "w.warehouse_code",
              "warehouse_type": "w.warehouse_type", "expiry_bucket": "s.expiry_bucket", "item_type": "i.item_type"}
UNCLASSIFIED = {"lifecycle_status"}
UNIT_VARIANTS = {"QTY_EQ": ("stock_qty_eq", "forecast_qty_eq"), "VALUE": ("stock_value_eur", "forecast_value_eur")}
RAW_UNITS = {"RAW", "QTY_RAW", "RAW_UNIT", "RAW_UNITS", "UNITS", "PACKS"}


def refuse(code, reason, **extra):
    return {"status": "refused", "reason_code": code, "reason": reason, **extra}


def run(session, as_of_month, unit_variant, grain, filters):
    caller = session.sql("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), CURRENT_USER(), "
                         "SYS_CONTEXT('SNOWFLAKE$CURRENT', 'IS_AGENT_ACTIVATED')::VARCHAR, "
                         "SYS_CONTEXT('SNOWFLAKE$SESSION', 'ACTIVE_RESTRICTED_SESSION_SCOPES')::VARCHAR").collect()[0]
    caller = {"current_role": caller[0], "current_secondary_roles": caller[1], "current_user": caller[2],
              "is_agent_activated": caller[3], "active_restricted_session_scopes": caller[4]}

    # ---- as-of month: required, a calendar month start, with a stock snapshot
    if as_of_month is None or str(as_of_month).strip() == "":
        return refuse("AS_OF_MISSING", "An analysis month is required. Coverage is a point-in-time measure: "
                      "give one month as YYYY-MM-01. It is never summed or averaged over several months.", caller=caller)
    s = str(as_of_month).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return refuse("AS_OF_INVALID", f"as_of_month '{s}' is not a date in YYYY-MM-01 form.", caller=caller)
    try:
        d = dt.date.fromisoformat(s)
    except ValueError:
        return refuse("AS_OF_INVALID", f"as_of_month '{s}' is not a valid date.", caller=caller)
    if d.day != 1:
        return refuse("AS_OF_NOT_MONTH_START", f"as_of_month '{s}' is not the first day of a month. Coverage is "
                      f"monthly: use {d.replace(day=1).isoformat()} for that month.", caller=caller)

    # ---- unit variant
    u = (unit_variant or "").strip().upper()
    if u in RAW_UNITS:
        return refuse("UNIT_RAW_NOT_ADDITIVE", "Raw units are pack counts of different sizes and do not add up. "
                      "Use QTY_EQ (equivalent kg or litres) or VALUE (EUR at standard cost).", caller=caller)
    if u not in UNIT_VARIANTS:
        return refuse("UNIT_UNKNOWN", f"unit_variant '{unit_variant}' is not one of QTY_EQ, VALUE.", caller=caller)
    s_col, f_col = UNIT_VARIANTS[u]

    # ---- grain and filters: every attribute must have a declared applicability class
    if isinstance(grain, str):
        gs = grain.strip()
        if gs.startswith("["):
            try:
                grain = json.loads(gs)
            except ValueError:
                return refuse("GRAIN_MALFORMED", "grain must be a JSON array or a comma-separated list of "
                              "attribute names.", caller=caller)
        else:
            grain = [x for x in gs.split(",") if x.strip()]
    if not isinstance(grain, list) and grain is not None:
        return refuse("GRAIN_MALFORMED", "grain must be a JSON array or a comma-separated list of attribute names.",
                      caller=caller)
    grain = [str(g).strip().lower() for g in (grain or [])]
    if not grain:
        return refuse("GRAIN_EMPTY", "grain must name at least one attribute (for example sku_code, country_code).",
                      caller=caller)
    if len(set(grain)) != len(grain):
        return refuse("GRAIN_DUPLICATE", f"grain lists an attribute twice: {grain}.", caller=caller)
    if filters is None or str(filters).strip() in ("", "{}", "null"):
        flt = {}
    else:
        try:
            flt = json.loads(filters) if isinstance(filters, str) else dict(filters)
        except (ValueError, TypeError):
            return refuse("FILTERS_MALFORMED", "filters must be a JSON object: attribute -> list of values.",
                          caller=caller)
        if not isinstance(flt, dict):
            return refuse("FILTERS_MALFORMED", "filters must be a JSON object: attribute -> list of values.",
                          caller=caller)
    flt = {str(k).strip().lower(): v for k, v in flt.items()}
    for a in grain + list(flt):
        if a in UNCLASSIFIED:
            return refuse("ATTRIBUTE_UNCLASSIFIED", f"'{a}' has no declared applicability class (conformed or "
                          "stock-only), so it cannot be used with coverage.", caller=caller)
        if a not in CONFORMED and a not in STOCK_ONLY:
            return refuse("ATTRIBUTE_UNKNOWN", f"'{a}' is not a coverage attribute. Conformed: "
                          f"{sorted(CONFORMED)}. Stock-only: {sorted(STOCK_ONLY)}.", caller=caller)
    for a, v in list(flt.items()):
        v = [v] if isinstance(v, (str, int, float)) else v
        if not isinstance(v, list) or not v or any(x is None or isinstance(x, (list, dict)) for x in v):
            return refuse("FILTER_VALUES_INVALID", f"filter '{a}' needs a non-empty list of values.", caller=caller)
        flt[a] = [str(x) for x in v]

    # ---- master data and snapshot checks (contract invariants, hard-coded here)
    chk = session.sql(
        "SELECT (SELECT COUNT(*) - COUNT(DISTINCT item_id) FROM (SELECT DISTINCT item_id, sku_code, family_code, "
        "range_code, item_type FROM LINKML_METRICS.RAW.DIM_ITEM)), "
        "(SELECT COUNT(*) FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT WHERE snapshot_month = ?::DATE), "
        "(SELECT MAX(month_start) FROM LINKML_METRICS.RAW.DIM_CALENDAR)", params=[d.isoformat()]).collect()[0]
    if chk[0]:
        return refuse("MASTER_DATA_FANOUT", "DIM_ITEM is not one row per item on the attributes coverage uses; "
                      "any number would be fanned out.", caller=caller)
    if not chk[1]:
        return refuse("AS_OF_NO_SNAPSHOT", f"There is no stock snapshot for {d.isoformat()}.", caller=caller)
    horizon_end = dt.date(d.year + (d.month - 1 + HORIZON) // 12, (d.month - 1 + HORIZON) % 12 + 1, 1)
    if chk[2] is None or chk[2] < horizon_end:
        return refuse("HORIZON_NOT_LOADED", f"The calendar does not reach {horizon_end.isoformat()}, the end of "
                      f"the {HORIZON}-month horizon.", caller=caller)

    # ---- SQL: DEFINITION.md section 5, member spine, dense calendar, no total
    conf_grain = [a for a in grain if a in CONFORMED]
    binds = []

    def where(attrs, cols):
        parts = []
        for a in attrs:
            parts.append(f"{cols[a]} IN ({', '.join('?' for _ in flt[a])})")
            binds.extend(flt[a])
        return " AND ".join(parts) or "TRUE"

    cols = {**CONFORMED, **STOCK_ONLY}
    g_sel = ", ".join(f"{cols[a]} AS {a}" for a in grain)
    gc_sel = "".join(f"{CONFORMED[a]} AS {a}, " for a in conf_grain)
    g = ", ".join(grain)
    items = ("(SELECT DISTINCT item_id, sku_code, family_code, range_code, item_type "
             "FROM LINKML_METRICS.RAW.DIM_ITEM)")

    binds.append(d.isoformat())
    stock_where = where(list(flt), cols)
    stock = (f"stock AS (\n    SELECT {g_sel}, SUM(s.{s_col}) AS stock_qty\n"
             f"    FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT s\n"
             f"    JOIN {items} i ON i.item_id = s.item_id\n"
             f"    JOIN LINKML_METRICS.RAW.DIM_GEO g ON g.country_id = s.country_id\n"
             f"    JOIN LINKML_METRICS.RAW.DIM_BATCH b ON b.batch_id = s.batch_id\n"
             f"    JOIN LINKML_METRICS.RAW.DIM_WAREHOUSE w ON w.warehouse_id = s.warehouse_id\n"
             f"    WHERE s.snapshot_month = ?::DATE AND {stock_where}\n    GROUP BY ALL\n)")
    binds.extend([d.isoformat(), d.isoformat(), d.isoformat()])
    fc_where = where([a for a in flt if a in CONFORMED], CONFORMED)   # stock-only filters never reach forecast
    fc = (f"fc AS (\n    SELECT {gc_sel}DATEDIFF(month, ?::DATE, f.forecast_month) AS k, SUM(f.{f_col}) AS fc_qty\n"
          f"    FROM LINKML_METRICS.RAW.FCT_FORECAST f\n"
          f"    JOIN {items} i ON i.item_id = f.item_id\n"
          f"    JOIN LINKML_METRICS.RAW.DIM_GEO g ON g.country_id = f.country_id\n"
          f"    WHERE f.forecast_month > ?::DATE AND f.forecast_month <= DATEADD(month, {HORIZON}, ?::DATE)\n"
          f"      AND {fc_where}\n    GROUP BY ALL\n)")
    members = f"SELECT {g} FROM stock"
    if not any(a in STOCK_ONLY for a in grain):     # forecast-only members exist on a conformed grain only (T8)
        members += f"\n    UNION\n    SELECT {g} FROM fc"
    on_s = " AND ".join(f"EQUAL_NULL(s.{a}, mb.{a})" for a in grain)
    on_f = "".join(f" AND EQUAL_NULL(f.{a}, mb.{a})" for a in conf_grain)
    sel_mb = ", ".join(f"mb.{a}" for a in grain)
    sql = (
        f"WITH months AS (\n    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS k FROM TABLE(GENERATOR(ROWCOUNT => {HORIZON}))\n),\n"
        f"{stock},\n{fc},\n"
        f"members AS (\n    {members}\n),\n"
        f"dense AS (\n    SELECT {sel_mb}, m.k, COALESCE(s.stock_qty, 0) AS stock_qty, COALESCE(f.fc_qty, 0) AS fc_qty\n"
        f"    FROM members mb CROSS JOIN months m\n    LEFT JOIN stock s ON {on_s}\n"
        f"    LEFT JOIN fc f ON f.k = m.k{on_f}\n),\n"
        f"cum AS (\n    SELECT *, SUM(fc_qty) OVER (PARTITION BY {g} ORDER BY k ROWS UNBOUNDED PRECEDING) AS cum_fc\n"
        f"    FROM dense\n)\n"
        f"SELECT {g},\n"
        f"       ANY_VALUE(stock_qty) AS stock,\n"
        f"       MAX(cum_fc) AS forecast_over_horizon,\n"
        f"       CASE\n"
        f"         WHEN ANY_VALUE(stock_qty) = 0 THEN 0\n"
        f"         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN\n"
        f"              SUM(CASE WHEN cum_fc - fc_qty >= stock_qty THEN 0\n"
        f"                       WHEN cum_fc <= stock_qty THEN 1\n"
        f"                       ELSE (stock_qty - (cum_fc - fc_qty)) / fc_qty END)\n"
        f"         ELSE ANY_VALUE(stock_qty) / AVG(NULLIF(fc_qty, 0))\n"
        f"       END AS coverage_months,\n"
        f"       CASE\n"
        f"         WHEN ANY_VALUE(stock_qty) = 0 THEN 'NO_STOCK'\n"
        f"         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN NULL\n"
        f"         WHEN MAX(cum_fc) = 0 THEN 'NO_DEMAND'\n"
        f"         ELSE 'BEYOND_HORIZON'\n"
        f"       END AS flag\n"
        f"FROM cum\nGROUP BY {g}\nORDER BY {g}"
    )
    rows = []
    for r in session.sql(sql, params=binds).collect():
        rd = r.as_dict()
        rows.append({**{a: rd[a.upper()] for a in grain},
                     "coverage_months": None if rd["COVERAGE_MONTHS"] is None else round(float(rd["COVERAGE_MONTHS"]), 4),
                     "stock": float(rd["STOCK"]), "forecast_over_horizon": float(rd["FORECAST_OVER_HORIZON"]),
                     "flag": rd["FLAG"]})
    flags = sorted({r["flag"] for r in rows if r["flag"]})
    return {
        "status": "ok",
        "as_of_month": d.isoformat(), "unit_variant": u, "grain": grain, "filters": flt,
        "applicability": {"stock_and_forecast": [a for a in list(grain) + list(flt) if a in CONFORMED],
                          "stock_only": [a for a in list(grain) + list(flt) if a in STOCK_ONLY]},
        "rows": rows, "row_count": len(rows), "flags": flags,
        "note": "Coverage in months of forward forecast. Each row is computed at its own grain: never sum or average "
                "rows to get a total; ask for the coarser grain instead.",
        "sql": sql, "binds": binds, "caller": caller,
    }
$$;

-- The owner role (LINKML_METRICS_ROLE) needs no USAGE grant; another caller role would.
