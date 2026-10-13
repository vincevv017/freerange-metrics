"""
Ninth generator (session 13, configuration C-raw): the snapshot measure's period aggregation ->
generated/closing_stock_procedure.sql, the procedure LINKML_METRICS.RAW.CLOSING_STOCK.

    python compiler/gen_closing_procedure.py                          # writes generated/closing_stock_procedure.sql
    python compiler/gen_closing_procedure.py --out /tmp/closing.sql   # writes elsewhere (the drift test uses this)

Closing stock at question time, from the raw snapshot and the dimensions only: no gap-filled snapshot, no spine. The
contract's period aggregation (CLOSING_STOCK: LAST_PERIOD, member set ANY_SNAPSHOT_IN_PERIOD, missing value 0) read at
call time: the members of a period are the groups of the grain asked that hold a snapshot row in any month of the
period; each closes at the sum of its rows in the period's last month, 0 when it has none (it keeps its row). A total
is the same computation at its coarser grain, from the stock rows, never a sum of the rows returned; several periods
give a series with no total across periods.

Same conventions as STOCK_COVERAGE (compiler/gen_procedure.py): SQL Scripting, EXECUTE AS CALLER, every parameter a
VARCHAR (lists and maps are JSON strings), the basis rule of the contract judged on the rows returned, the contract's
refusal codes in check order (a period with a month that has no snapshot is refused, never guessed), its warnings, the
query ids of the statements as lineage. Three statements, each SQL with bound values (no SQL text built at call time):
1. the parameters (reads no table) and the caller;
2. the context: the snapshot months, the period checks, the table-scope quality expectations;
3. the closing rows, with the request-scoped quality checks (fan-out of the item dimension, referential warnings).

The contract's refusal templates were written for coverage. A template that names coverage or the as_of_months
parameter is reworded here for closing stock (REWORDED holds the contract text it rewords, and the generator stops if
the contract's wording changed); every other template is the contract's, word for word.
The output is deterministic: same contract, same bytes.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

try:
    from compiler import supported
    from compiler.procedure_scripting import WS, case_map, q, render as tpl
    from compiler.gen_procedure import quality_sql
except ImportError:                       # run as a script: compiler/ is on sys.path
    import supported
    from procedure_scripting import WS, case_map, q, render as tpl
    from gen_procedure import quality_sql

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contract" / "stock_coverage.yaml"
DEFAULT_OUT = ROOT / "generated" / "closing_stock_procedure.sql"
SCHEMA = "LINKML_METRICS.RAW"
PROCEDURE = f"{SCHEMA}.CLOSING_STOCK"
ROLE = "LINKML_METRICS_ROLE"
GENERATOR = "gen_closing_procedure"
MAX_RANGE_MONTHS = 1200   # months listed per period when one is missing (a longer range is refused all the same)
PERIOD_KINDS = {          # contract period kinds this generator reads, and how a caller writes each
    "PERIOD_RANGE": "a month (YYYY-MM-01), a range of months (YYYY-MM-01/YYYY-MM-01)",
    "QUARTER": "a quarter (YYYY-Qn)",
    "YEAR": "a year (YYYY)",
}
FORMS = "a year (YYYY), a quarter (YYYY-Qn), a month (YYYY-MM-01), a range of months (YYYY-MM-01/YYYY-MM-01) or LATEST"
# code -> (the contract's template, the closing-stock wording)
REWORDED = {
    "AS_OF_MISSING": (
        "An analysis month is required. Coverage is a point-in-time measure: give one or more months as YYYY-MM-01. "
        "It is never summed or averaged over several months.",
        f"A period is required: {FORMS}. Closing stock is the snapshot of the period's last month; it is never summed "
        "or averaged over the months of the period."),
    "AS_OF_INVALID": (
        "as_of_months value '{value}' is not a date in YYYY-MM-01 form, nor LATEST.",
        f"period '{{value}}' is not {FORMS} (a range starts with its first month)."),
    "AS_OF_NOT_MONTH_START": (
        "'{value}' is not the first day of a month. Coverage is monthly: use {month_start} for that month.",
        "'{value}' is not the first day of a month. Closing stock is monthly: use {month_start} for that month."),
    "AS_OF_TOO_MANY": (
        "At most {max_periods} analysis months per call.",
        "At most {max_periods} periods per call."),
    "ATTRIBUTE_UNKNOWN": (
        "'{attribute}' is not a coverage attribute. Conformed: {conformed}. Stock-only: {snapshot_only}.",
        "'{attribute}' is not a closing stock attribute. Conformed: {conformed}. Stock-only: {snapshot_only}."),
    "ATTRIBUTE_UNCLASSIFIED": (
        "'{attribute}' has no declared applicability class, so it cannot be used with coverage.",
        "'{attribute}' has no declared applicability class, so it cannot be used with closing stock."),
    "ATTRIBUTE_NOT_APPLICABLE": (
        "'{attribute}' does not apply to stock coverage: {reason}.",
        "'{attribute}' does not apply to closing stock: {reason}."),
    "BASIS_NOT_COMPARABLE": (
        "Coverage is always in months, but on {basis} {why}, so stock and forecast cannot be summed for this request. "
        "Bases allowed for this request: {allowed}.",
        "On {basis} {why}, so the stock cannot be summed for this request. Bases allowed for this request: {allowed}."),
}
STAGES = {   # the statement after which each code is raised; their order must follow the contract's check_order
    "parameters": ["AS_OF_MISSING", "AS_OF_INVALID", "AS_OF_NOT_MONTH_START", "AS_OF_TOO_MANY"],
    "context": ["AS_OF_NO_SNAPSHOT"],
    "after_context": ["BASIS_UNKNOWN", "GRAIN_MALFORMED", "GRAIN_EMPTY", "GRAIN_DUPLICATE", "FILTERS_MALFORMED",
                      "FILTER_VALUES_INVALID", "ATTRIBUTE_UNKNOWN", "ATTRIBUTE_UNCLASSIFIED", "ATTRIBUTE_NOT_APPLICABLE",
                      "TOTALS_MALFORMED", "TOTALS_NOT_SUBSET"],
    "closing": ["MASTER_DATA_FANOUT", "DATA_QUALITY_FAILED", "BASIS_NOT_COMPARABLE"],
}


def codes(c: dict) -> list[str]:
    """The refusal codes CLOSING_STOCK raises, in the contract's check_order (the coverage-only ones left out)."""
    order = [r["id"] for r in sorted(c["refusal_codes"], key=lambda r: r["check_order"])]
    used = [x for stage in STAGES.values() for x in stage]
    missing = [x for x in used if x not in order]
    if missing:
        raise ValueError(f"refusal codes not in the contract: {missing}")
    if [x for x in order if x in used] != used:
        raise ValueError("the stages of CLOSING_STOCK break the contract's check_order")
    return used


def _alias(table_id: str) -> str:
    return re.sub(r"^(DIM|FCT)_", "", table_id).lower()


def build(c: dict) -> dict:
    supported.check(c, GENERATOR)
    snap = next(m for m in c["measures"] if m.get("period_aggregation"))
    pa = snap["period_aggregation"]
    if pa["method"] != "LAST_PERIOD":
        raise ValueError(f"period_aggregation.method: only LAST_PERIOD is supported by {GENERATOR}")
    if not set(pa["periods"]) <= set(PERIOD_KINDS):
        raise ValueError(f"period_aggregation.periods: only {', '.join(PERIOD_KINDS)} are supported by {GENERATOR}")
    if str(pa["missing_value"]) != "0":
        raise ValueError(f"period_aggregation.missing_value: only 0 is supported by {GENERATOR}")
    if any(not s.get("applies_to_metrics") for s in c["default_scopes"]):
        raise ValueError(f"default_scopes: a scope on the measure itself is not supported by {GENERATOR}; a scope "
                         "restricted to metrics does not apply to closing stock")
    templates = {r["id"]: r["reason_template"] for r in c["refusal_codes"]}
    for code, (was, _) in REWORDED.items():
        if templates.get(code) != was:
            raise ValueError(f"{code}: the contract's template changed; review its closing-stock wording")
    used_codes = codes(c)
    tables = {t["id"]: t for t in c["tables"]}
    st = snap["table"]
    tcol = snap["time_column"]
    rels = [r for r in c["relationships"] if r["from_table"] == st and r["cardinality"] == "MANY_TO_ONE"
            and r["from_columns"] != [tcol]]
    attrs = []
    for a in c["attributes"]:
        eff = {x["measure"]: x["effect"] for x in a["applicability"]}.get(snap["id"])
        attrs.append({"id": a["id"], "table": a["table"], "column": a["column"], "class": a["applicability_class"],
                      "effect": eff, "description": " ".join((a.get("description") or "").split())})
    usable = [a for a in attrs if a["effect"] == "GROUP_AND_FILTER"]
    unjoined = [a["id"] for a in usable if a["table"] != st and a["table"] not in {r["to_table"] for r in rels}]
    if unjoined:
        raise ValueError(f"attributes on a table the snapshot does not join: {unjoined}")
    bm = c["basis_model"]
    dedup = {x["table"] for x in c["quality_expectations"] if x["on_failure"] == "REFUSE_IF_USED"}
    if dedup != {bm["item_table"]}:
        raise ValueError(f"the REFUSE_IF_USED quality expectations must all be on basis_model.item_table: {dedup}")
    read = {st} | {r["to_table"] for r in rels}
    qes = [x for x in c["quality_expectations"] if x["on_failure"] != "MONITOR" and x["table"] in read
           and x.get("references_table", st) in read and (x.get("refusal") is None or x["refusal"] in used_codes)]
    names = lambda e: sorted({re.sub(r"[\s-]+", "_", x.strip().upper()) for x in [e["id"]] + e.get("synonyms", [])})  # noqa: E731
    return {"c": c, "snap": snap, "pa": pa, "st": st, "tcol": tcol, "rels": rels, "tables": tables,
            "attrs": attrs, "usable": usable, "bm": bm, "item_table": bm["item_table"], "item_key": bm["item_key"],
            "bases": c["measure_bases"], "names": {b["id"]: names(b) for b in c["measure_bases"]},
            "columns": {x["basis"]: x["column"] for x in snap["columns"]},
            "templates": {**templates, **{k: v for k, (_, v) in REWORDED.items()}},
            "warnings": {w["id"]: w["message_template"] for w in c["warning_codes"]},
            "max_periods": c["analysis_periods"][0]["max_periods"], "latest_token": c["analysis_periods"][0]["latest_token"],
            "qes": qes, "codes": used_codes}


def fq(t: str) -> str:
    return f"{SCHEMA}.{t}"


def arr(xs) -> str:
    return "ARRAY_CONSTRUCT(" + ", ".join(q(x) for x in xs) + ")"


CALLER = ("CURRENT_ROLE() AS CALLER_ROLE, CURRENT_SECONDARY_ROLES() AS CALLER_SECONDARY_ROLES, CURRENT_USER() AS "
          "CALLER_USER, SYS_CONTEXT('SNOWFLAKE$CURRENT', 'IS_AGENT_ACTIVATED')::VARCHAR AS AGENT_ACTIVATED")


# ================================================================================================ 1. the parameters

def parameters_sql(b: dict) -> str:
    R = b["templates"]
    order = [a["id"] for a in b["attrs"]]
    usable = [a["id"] for a in b["usable"]]
    conformed = [a["id"] for a in b["usable"] if a["class"] == "CONFORMED"]
    snapshot_only = [a["id"] for a in b["usable"] if a["class"] == "SNAPSHOT_ONLY"]
    unclassified = [a["id"] for a in b["attrs"] if a["effect"] is None]
    not_applicable = [a["id"] for a in b["attrs"] if a["effect"] not in (None, "GROUP_AND_FILTER")]
    known = order
    rank = "CASE k" + "".join(f" WHEN {q(a)} THEN {i}" for i, a in enumerate(order)) + f" ELSE {len(order)} END"
    basis_case = ("CASE ukey" + "".join(f" WHEN {q(n)} THEN {q(bid)}" for bid, ns in b["names"].items() for n in ns)
                  + " ELSE NULL END")
    default_basis = b["bm"]["default_basis"]
    ranked = (f"ARRAY_CAT(FILTER({arr(known)}, x -> ARRAY_CONTAINS(x, names)), "
              f"ARRAY_SORT(FILTER(names, x -> NOT ARRAY_CONTAINS(x, {arr(known)}))))")
    checks = {
        "AS_OF_MISSING": ("p_missing", tpl(R["AS_OF_MISSING"], {})),
        "AS_OF_INVALID": ("p_invalid IS NOT NULL", tpl(R["AS_OF_INVALID"], {"value": "p_invalid"})),
        "AS_OF_NOT_MONTH_START": ("p_not_start IS NOT NULL", tpl(R["AS_OF_NOT_MONTH_START"], {
            "value": "p_not_start", "month_start": "TO_VARCHAR(DATE_TRUNC('month', TO_DATE(p_not_start)))"})),
        "AS_OF_TOO_MANY": (f"p_count > {b['max_periods']}", tpl(R["AS_OF_TOO_MANY"], {"max_periods": q(b["max_periods"])})),
        "BASIS_UNKNOWN": ("basis IS NULL", tpl(R["BASIS_UNKNOWN"], {"value": "basis_raw"})),
        "GRAIN_MALFORMED": ("grain_malformed", tpl(R["GRAIN_MALFORMED"], {})),
        "GRAIN_EMPTY": ("ARRAY_SIZE(grain) = 0", tpl(R["GRAIN_EMPTY"], {})),
        "GRAIN_DUPLICATE": ("ARRAY_SIZE(grain_dups) > 0", tpl(R["GRAIN_DUPLICATE"], {"value": "ARRAY_TO_STRING(grain_dups, ', ')"})),
        "FILTERS_MALFORMED": ("filters_malformed", tpl(R["FILTERS_MALFORMED"], {})),
        "FILTER_VALUES_INVALID": ("bad_filter IS NOT NULL", tpl(R["FILTER_VALUES_INVALID"], {"attribute": "bad_filter"})),
        "ATTRIBUTE_UNKNOWN": ("unknown_attribute IS NOT NULL", tpl(R["ATTRIBUTE_UNKNOWN"], {
            "attribute": "unknown_attribute", "conformed": q(", ".join(conformed)),
            "snapshot_only": q(", ".join(snapshot_only))})),
        "ATTRIBUTE_UNCLASSIFIED": ("unclassified_attribute IS NOT NULL", tpl(R["ATTRIBUTE_UNCLASSIFIED"], {
            "attribute": "unclassified_attribute"})),
        "ATTRIBUTE_NOT_APPLICABLE": ("not_applicable_attribute IS NOT NULL", tpl(R["ATTRIBUTE_NOT_APPLICABLE"], {
            "attribute": "not_applicable_attribute",
            "reason": case_map("not_applicable_attribute", {a["id"]: a["description"] for a in b["attrs"]}, "''")})),
        "TOTALS_MALFORMED": ("totals_malformed", tpl(R["TOTALS_MALFORMED"], {})),
        "TOTALS_NOT_SUBSET": ("bad_total IS NOT NULL", tpl(R["TOTALS_NOT_SUBSET"], {
            "value": "ARRAY_TO_STRING(bad_total, ', ')", "grain": "ARRAY_TO_STRING(grain, ', ')"})),
    }

    def case(stage: str, what: int) -> str:
        return "CASE" + "".join(f" WHEN {checks[k][0]} THEN {q(k) if what == 0 else checks[k][1]}"
                                for k in STAGES[stage]) + " END"
    t = lambda x: f"TRIM({x}, {WS})"   # noqa: E731
    return rf"""WITH b AS (
    SELECT :PERIODS AS periods_raw, :GRAIN AS grain_raw, :FILTERS AS filters_raw, :BASIS AS basis_raw,
           :TOTALS AS totals_raw
),
s1 AS (
    SELECT b.*,
           {t("COALESCE(periods_raw, '')")} AS p_s,
           p_s IN ('', '[]', 'null') AS p_missing0,
           LEFT(p_s, 1) IN ('[', '{{') AS p_is_json,
           IFF(p_is_json, TRY_PARSE_JSON(p_s, 'd'), NULL) AS p_j,
           p_is_json AND NOT COALESCE(IS_ARRAY(p_j), FALSE) AS p_bad_json,
           CASE WHEN p_missing0 OR p_bad_json THEN ARRAY_CONSTRUCT()
                WHEN p_is_json THEN p_j::ARRAY
                ELSE SPLIT(p_s, ',') END AS p_items,
           REGEXP_REPLACE(UPPER({t("COALESCE(basis_raw, '')")}), '[\\s-]+', '_') AS ukey,
           IFF(basis_raw IS NULL OR {t("basis_raw")} IN ('', 'null'), {q(default_basis)}, {basis_case}) AS basis,
           {t("grain_raw")} AS g_s,
           grain_raw IS NOT NULL AND g_s <> '' AND LEFT(g_s, 1) IN ('[', '{{') AND NOT COALESCE(IS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), FALSE) AS g_bad_json,
           CASE WHEN grain_raw IS NULL OR g_s = '' THEN ARRAY_CONSTRUCT()
                WHEN LEFT(g_s, 1) IN ('[', '{{') THEN COALESCE(AS_ARRAY(TRY_PARSE_JSON(g_s, 'd')), ARRAY_CONSTRUCT())
                ELSE FILTER(TRANSFORM(SPLIT(g_s, ','), x -> {t("x::VARCHAR")}::VARIANT), x -> x::VARCHAR <> '') END AS g_items,
           COALESCE(g_bad_json, FALSE) OR ARRAY_SIZE(FILTER(g_items, x -> TYPEOF(x) <> 'VARCHAR')) > 0 AS grain_malformed,
           TRANSFORM(FILTER(g_items, x -> TYPEOF(x) = 'VARCHAR'), x -> LOWER({t("x::VARCHAR")})::VARIANT) AS grain,
           ARRAY_DISTINCT(ARRAY_EXCEPT(grain, ARRAY_DISTINCT(grain))) AS grain_dups,
           {t(f"IFF(filters_raw IS NULL OR {t('filters_raw')} IN ('', 'null'), '{{}}', filters_raw)")} AS f_s,
           IFF(LEFT(f_s, 1) IN ('[', '{{'), TRY_PARSE_JSON(f_s, 'd'), NULL) AS f_json,
           f_json IS NULL OR NOT IS_OBJECT(f_json) AS filters_malformed,
           {t(f"IFF(totals_raw IS NULL OR {t('totals_raw')} IN ('', 'null'), '[]', totals_raw)")} AS t_s,
           IFF(LEFT(t_s, 1) = '[', TRY_PARSE_JSON(t_s, 'd'), NULL) AS t_json,
           t_json IS NULL OR NOT IS_ARRAY(t_json)
             OR ARRAY_SIZE(FILTER(COALESCE(AS_ARRAY(t_json), ARRAY_CONSTRUCT()), e -> NOT IS_ARRAY(e)
                  OR ARRAY_SIZE(FILTER(COALESCE(AS_ARRAY(e), ARRAY_CONSTRUCT()), z -> TYPEOF(z) <> 'VARCHAR')) > 0)) > 0 AS totals_malformed,
           TRANSFORM(COALESCE(AS_ARRAY(t_json), ARRAY_CONSTRUCT()),
                     e -> TRANSFORM(COALESCE(AS_ARRAY(e), ARRAY_CONSTRUCT()), z -> LOWER({t("z::VARCHAR")})::VARIANT)::VARIANT) AS totals_all,
           TRANSFORM(FILTER(ARRAY_GENERATE_RANGE(0, ARRAY_SIZE(totals_all)), i -> ARRAY_POSITION(GET(totals_all, i::INT), totals_all) = i::INT), i -> GET(totals_all, i::INT)) AS totals
    FROM b
),
pr AS (
    SELECT f.index AS i, TYPEOF(f.value) AS ty,
           IFF(ty IN ('VARCHAR', 'INTEGER'), {t("f.value::VARCHAR")}, TO_JSON(f.value)) AS shown,
           IFF(ty IN ('VARCHAR', 'INTEGER'), REGEXP_REPLACE(UPPER(shown), '\\s+', ''), NULL) AS tok,
           CASE WHEN tok = {q(b['latest_token'])} THEN 'LATEST'
                WHEN REGEXP_LIKE(tok, '\\d{{4}}') THEN 'YEAR'
                WHEN REGEXP_LIKE(tok, '(\\d{{4}}-?Q[1-4]|Q[1-4]-?\\d{{4}})') THEN 'QUARTER'
                WHEN REGEXP_LIKE(tok, '\\d{{4}}-\\d{{2}}-\\d{{2}}(/\\d{{4}}-\\d{{2}}-\\d{{2}})?') THEN 'PERIOD_RANGE' END AS kind,
           TRY_TO_DATE(SPLIT_PART(tok, '/', 1), 'YYYY-MM-DD') AS d1,
           TRY_TO_DATE(IFF(CONTAINS(tok, '/'), SPLIT_PART(tok, '/', 2), tok), 'YYYY-MM-DD') AS d2,
           TRY_TO_NUMBER(COALESCE(REGEXP_SUBSTR(tok, '^(\\d{{4}})-?Q', 1, 1, 'e', 1), REGEXP_SUBSTR(tok, 'Q[1-4]-?(\\d{{4}})$', 1, 1, 'e', 1),
                                  REGEXP_SUBSTR(tok, '^\\d{{4}}'))) AS y,
           TRY_TO_NUMBER(REGEXP_SUBSTR(tok, 'Q([1-4])', 1, 1, 'e', 1)) AS qn,
           kind IS NULL OR (kind = 'PERIOD_RANGE' AND (d1 IS NULL OR d2 IS NULL OR d1 > d2)) AS invalid,
           NOT invalid AND kind = 'PERIOD_RANGE' AND (DAY(d1) <> 1 OR DAY(d2) <> 1) AS not_start,
           IFF(DAY(d1) <> 1, TO_VARCHAR(d1), TO_VARCHAR(d2)) AS bad_day,
           CASE kind WHEN 'YEAR' THEN DATE_FROM_PARTS(y, 1, 1) WHEN 'QUARTER' THEN DATE_FROM_PARTS(y, 3 * qn - 2, 1)
                     WHEN 'PERIOD_RANGE' THEN d1 END AS first_month,
           CASE kind WHEN 'YEAR' THEN DATE_FROM_PARTS(y, 12, 1) WHEN 'QUARTER' THEN DATE_FROM_PARTS(y, 3 * qn, 1)
                     WHEN 'PERIOD_RANGE' THEN d2 END AS last_month,
           CASE kind WHEN 'YEAR' THEN y::VARCHAR WHEN 'QUARTER' THEN y::VARCHAR || '-Q' || qn::VARCHAR
                     WHEN 'PERIOD_RANGE' THEN IFF(d1 = d2, TO_VARCHAR(d1), TO_VARCHAR(d1) || '/' || TO_VARCHAR(d2))
                     ELSE kind END AS label
    FROM s1, TABLE(FLATTEN(INPUT => s1.p_items)) f
),
pv AS (SELECT * FROM pr WHERE NOT invalid AND NOT not_start QUALIFY ROW_NUMBER() OVER (PARTITION BY label ORDER BY i) = 1),
fl AS (
    SELECT LOWER({t("f.key")}) AS k, f.value AS v,
           IFF(TYPEOF(v) IN ('VARCHAR', 'INTEGER', 'DECIMAL', 'DOUBLE'), ARRAY_CONSTRUCT(v), AS_ARRAY(v)) AS vv,
           vv IS NULL OR ARRAY_SIZE(vv) = 0
             OR ARRAY_SIZE(FILTER(vv, e -> TYPEOF(e) IN ('NULL_VALUE', 'ARRAY', 'OBJECT', 'BOOLEAN'))) > 0 AS bad,
           {rank} AS rk
    FROM s1, TABLE(FLATTEN(INPUT => IFF(IS_OBJECT(s1.f_json), s1.f_json, OBJECT_CONSTRUCT()))) f
    QUALIFY ROW_NUMBER() OVER (PARTITION BY LOWER({t("f.key")}) ORDER BY f.key DESC) = 1
),
fa AS (
    SELECT COALESCE(ARRAY_AGG(k) WITHIN GROUP (ORDER BY rk, k), ARRAY_CONSTRUCT()) AS fkeys,
           GET(ARRAY_AGG(IFF(bad, k, NULL)) WITHIN GROUP (ORDER BY rk, k), 0)::VARCHAR AS bad_filter,
           COALESCE(OBJECT_AGG(k, IFF(bad, NULL, TRANSFORM(vv, e -> e::VARCHAR::VARIANT))::VARIANT), OBJECT_CONSTRUCT()) AS filters
    FROM fl
),
s2 AS (
    SELECT s1.*, fa.*,
           p_missing0 OR (NOT p_bad_json AND ARRAY_SIZE(p_items) = 0) AS p_missing,
           IFF(p_bad_json, periods_raw, (SELECT MIN_BY(shown, i) FROM pr WHERE invalid)) AS p_invalid,
           (SELECT MIN_BY(bad_day, i) FROM pr WHERE not_start) AS p_not_start,
           (SELECT COUNT(*) FROM pv) AS p_count,
           ARRAY_DISTINCT(ARRAY_CAT(grain, fkeys)) AS names,
           {ranked} AS ranked,
           GET(FILTER(ranked, x -> NOT ARRAY_CONTAINS(x, {arr(known)})), 0)::VARCHAR AS unknown_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, {arr(unclassified)})), 0)::VARCHAR AS unclassified_attribute,
           GET(FILTER(ranked, x -> ARRAY_CONTAINS(x, {arr(not_applicable)})), 0)::VARCHAR AS not_applicable_attribute,
           GET(FILTER(totals, x -> ARRAY_SIZE(ARRAY_DISTINCT(x::ARRAY)) <> ARRAY_SIZE(x::ARRAY)
                      OR ARRAY_SIZE(ARRAY_EXCEPT(x::ARRAY, grain)) > 0 OR ARRAY_SIZE(x::ARRAY) >= ARRAY_SIZE(grain)), 0)::ARRAY AS bad_total
    FROM s1, fa
)
SELECT {CALLER},
       {case("parameters", 0)} AS P_RCODE,
       {case("parameters", 1)} AS P_REASON,
       {case("after_context", 0)} AS Q_RCODE,
       {case("after_context", 1)} AS Q_REASON,
       (SELECT ARRAY_AGG(OBJECT_CONSTRUCT('period', label, 'kind', kind, 'first_month', TO_VARCHAR(first_month),
                                          'last_month', TO_VARCHAR(last_month))) WITHIN GROUP (ORDER BY i) FROM pv) AS PERIODS,
       basis AS BASIS, grain AS GRAIN, filters AS FILTERS, totals AS TOTALS,
       ARRAY_PREPEND(totals, grain) AS GRAINS,
       FILTER({arr(usable)}, x -> ARRAY_CONTAINS(x, names)) AS USED
FROM s2"""


# ================================================================================================ 2. the context

def context_sql(b: dict) -> str:
    st, tcol = fq(b["st"]), b["tcol"]
    R, W = b["templates"], b["warnings"]
    dq = [x for x in b["qes"] if x["call_scope"] == "TABLE" and x["on_failure"] == "REFUSE"
          and x["refusal"] == "DATA_QUALITY_FAILED"]
    cols = []
    for x in dq:
        s = quality_sql(x, b["tables"], {t: fq(t) for t in b["tables"]}, {}, None, None, None)
        if s is not None:
            cols.append((x, s))
    dq_cols = "".join(f",\n           {s} AS {x['id']}" for x, s in cols)
    dq_reason = ("CASE" + "".join(
        f" WHEN COALESCE(cx.{x['id']}, 0) <> 0 THEN "
        + tpl(R["DATA_QUALITY_FAILED"], {"expectation": q(x["id"]), "count": f"cx.{x['id']}::VARCHAR",
                                            "condition": q(x["condition"])}) for x, _ in cols) + " END") if cols else "NULL"
    no_snap = tpl(R["AS_OF_NO_SNAPSHOT"], {
        "value": "ARRAY_TO_STRING(bad.months, ', ') || ' (period ' || bad.label || ')'",
        "available_months": "ARRAY_TO_STRING(COALESCE(cx.SNAPSHOTS, ARRAY_CONSTRUCT()), ', ')",
        "latest": "COALESCE(cx.LATEST, 'none')"})
    del W
    return f"""WITH snaps AS (SELECT DISTINCT {tcol} AS m FROM {st}),
cx AS (
    SELECT (SELECT ARRAY_AGG(TO_VARCHAR(m)) WITHIN GROUP (ORDER BY m) FROM snaps) AS SNAPSHOTS,
           (SELECT TO_VARCHAR(MAX(m)) FROM snaps) AS LATEST{dq_cols}
),
pp AS (
    SELECT f.index AS i, f.value:period::VARCHAR AS label, f.value:kind::VARCHAR AS kind,
           IFF(kind = 'LATEST', TO_DATE(cx.LATEST), f.value:first_month::DATE) AS first_month,
           IFF(kind = 'LATEST', TO_DATE(cx.LATEST), f.value:last_month::DATE) AS last_month
    FROM cx, TABLE(FLATTEN(INPUT => PARSE_JSON(:periods_json))) f
),
mm AS (
    SELECT pp.i, pp.label, IFF(pp.first_month IS NULL, NULL, DATEADD(month, g.k, pp.first_month)) AS m
    FROM pp JOIN (SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1 AS k FROM TABLE(GENERATOR(ROWCOUNT => {MAX_RANGE_MONTHS}))) g
      ON g.k <= COALESCE(DATEDIFF(month, pp.first_month, pp.last_month), 0)
),
miss AS (
    SELECT mm.i, ANY_VALUE(mm.label) AS label,
           ARRAY_AGG(COALESCE(TO_VARCHAR(mm.m), mm.label)) WITHIN GROUP (ORDER BY mm.m) AS months
    FROM mm, cx
    WHERE mm.m IS NULL OR NOT ARRAY_CONTAINS(TO_VARCHAR(mm.m)::VARIANT, COALESCE(cx.SNAPSHOTS, ARRAY_CONSTRUCT()))
    GROUP BY mm.i
),
bad AS (SELECT * FROM miss ORDER BY i LIMIT 1)
SELECT GET(cx.SNAPSHOTS, 0)::VARCHAR AS AVAILABLE_FIRST, cx.LATEST AS AVAILABLE_LATEST,
       IFF(bad.i IS NOT NULL, 'AS_OF_NO_SNAPSHOT', NULL) AS RCODE,
       IFF(bad.i IS NOT NULL, {no_snap}, NULL) AS REASON,
       {dq_reason} AS DQ_REASON,
       (SELECT ARRAY_AGG(OBJECT_CONSTRUCT('period', label, 'kind', kind, 'first_month', TO_VARCHAR(first_month),
                                          'last_month', TO_VARCHAR(last_month))) WITHIN GROUP (ORDER BY i) FROM pp) AS PERIODS
FROM cx LEFT JOIN bad ON TRUE"""


# ================================================================================================ 3. the closing rows

def closing_sql(b: dict) -> str:
    st, tcol, ik = fq(b["st"]), b["tcol"], b["item_key"]
    R, W = b["templates"], b["warnings"]
    it = b["item_table"]
    al = {r["to_table"]: _alias(r["to_table"]) for r in b["rels"]}
    sa = "s"
    expr = {a["id"]: (f"{sa}.{a['column']}" if a["table"] == b["st"] else f"{al[a['table']]}.{a['column']}")
            for a in b["usable"]}
    filt = lambda a, e: f"(rq.r:filters:\"{a}\" IS NULL OR ARRAY_CONTAINS(({e})::VARIANT, rq.r:filters:\"{a}\"::ARRAY))"  # noqa: E731
    used = lambda ids: " OR ".join(f"ARRAY_CONTAINS({q(x)}::VARIANT, rq.r:used::ARRAY)" for x in ids) or "FALSE"  # noqa: E731
    by_table: dict[str, list[str]] = {}
    for a in b["usable"]:
        by_table.setdefault(a["table"], []).append(a["id"])
    item_attrs = by_table.get(it, [])
    item_cols = [a["column"] for a in b["usable"] if a["table"] == it]
    bm = b["bm"]
    unit_cols = {"u_dimension": bm["dimension_column"], "u_base_unit": bm["base_unit_column"],
                 "u_native_unit": bm["native_unit_column"]}
    proj_cols = list(dict.fromkeys(item_cols + list(unit_cols.values())))
    proj = ",\n           ".join(f"MIN({x}) AS {x}" for x in proj_cols)
    other_joins, other_gate, other_filters, other_sel = [], [], [], []
    for r in b["rels"]:
        t = r["to_table"]
        if t == it:
            continue
        on = " AND ".join(f"{al[t]}.{tc} = {sa}.{fc}" for fc, tc in zip(r["from_columns"], r["to_columns"]))
        other_joins.append(f"\n    LEFT JOIN {fq(t)} {al[t]} ON {on}")
        other_gate.append(f"(NOT ({used(by_table.get(t, []))}) OR {al[t]}.{r['to_columns'][0]} IS NOT NULL)")
    for a in b["usable"]:
        if a["table"] != it:
            other_filters.append(filt(a["id"], expr[a["id"]]))
            other_sel.append(f"{expr[a['id']]} AS {a['id']}")
    item_rel = next(r for r in b["rels"] if r["to_table"] == it)
    item_on = " AND ".join(f"item.{tc} = base.{fc}" for fc, tc in zip(item_rel["from_columns"], item_rel["to_columns"]))
    raw_item_filters = " AND ".join(filt(x, f"d.{next(a['column'] for a in b['usable'] if a['id'] == x)}")
                                    for x in item_attrs) or "TRUE"
    item_filters = " AND ".join(filt(x, f"item.{next(a['column'] for a in b['usable'] if a['id'] == x)}")
                                for x in item_attrs) or "TRUE"
    qty = ("CASE rq.r:basis::VARCHAR" + "".join(f" WHEN {q(bid)} THEN {sa}.{col}" for bid, col in b["columns"].items())
           + " END")
    keys = [a["id"] for a in b["usable"]]
    grouped_attrs = ",\n           ".join(f"IFF(ARRAY_CONTAINS({q(a)}::VARIANT, g.gs), r.{a}, NULL) AS {a}" for a in keys)
    attrs_obj = "OBJECT_CONSTRUCT_KEEP_NULL(" + ", ".join(f"{q(a)}, {a}" for a in keys) + ")"
    bases = b["bases"]
    unit = ("CASE rq.r:basis::VARCHAR" + "".join(
        f" WHEN {q(x['id'])} THEN " + {"ONE_ITEM_PER_ROW": "IFF(n_items = 1, native_unit, NULL)",
                                       "ONE_DIMENSION_PER_ROW": "IFF(n_dims = 1, base_unit, NULL)",
                                       "ALWAYS": q(x.get("unit_symbol"))}[x["valid_when"]] for x in bases) + " END")
    valid = {"ONE_ITEM_PER_ROW": "COALESCE(agg.max_items, 0) <= 1", "ONE_DIMENSION_PER_ROW": "COALESCE(agg.max_dims, 0) <= 1",
             "ALWAYS": "TRUE"}
    invalid = " OR ".join(f"(rq.r:basis::VARCHAR = {q(x['id'])} AND NOT ({valid[x['valid_when']]}))" for x in bases
                          if x["valid_when"] != "ALWAYS")
    allowed = ("ARRAY_TO_STRING(ARRAY_CONSTRUCT_COMPACT(" + ", ".join(
        f"IFF({valid[x['valid_when']]}, {q(x['id'])}, NULL)" for x in bases) + "), ', ')")
    basis_reason = tpl(R["BASIS_NOT_COMPARABLE"], {
        "basis": "rq.r:basis::VARCHAR",
        "why": case_map("rq.r:basis::VARCHAR", {x["id"]: x["not_comparable_reason"] for x in bases}, "''"),
        "allowed": allowed})
    # request-scoped quality: the fan-out of the item dimension on the attributes used, and the warnings
    cap = 5
    fan_counts = ",\n           ".join(f"COUNT(DISTINCT d.{a['column']}) AS c_{a['id']}" for a in b["usable"]
                                       if a["table"] == it)
    differ = ("ARRAY_CONSTRUCT_COMPACT(" + ", ".join(
        f"IFF(ARRAY_CONTAINS({q(x)}::VARIANT, rq.r:used::ARRAY) AND dup.c_{x} > 1, {q(x)}, NULL)" for x in item_attrs) + ")")
    fan_values = ",\n           ".join(
        f"(SELECT ARRAY_AGG(DISTINCT d.{next(a['column'] for a in b['usable'] if a['id'] == x)}) WITHIN GROUP (ORDER BY "
        f"d.{next(a['column'] for a in b['usable'] if a['id'] == x)}) FROM {fq(it)} d WHERE d.{ik} IN "
        f"(SELECT {ik} FROM fan WHERE ARRAY_CONTAINS({q(x)}::VARIANT, differ))) AS v_{x}" for x in item_attrs)
    groups = ", ".join(
        f"IFF(ARRAY_SIZE(v_{x}) > 0, {q(x + ' (')} || ARRAY_TO_STRING(ARRAY_SLICE(v_{x}, 0, {cap}), ', ') || "
        f"IFF(ARRAY_SIZE(v_{x}) > {cap}, ' and ' || (ARRAY_SIZE(v_{x}) - {cap})::VARCHAR || ' more', '') || ')', NULL)"
        for x in item_attrs)
    fan_reason = tpl(R["MASTER_DATA_FANOUT"], {"count": "n_fan::VARCHAR",
                                                  "attributes": f"ARRAY_TO_STRING(ARRAY_CONSTRUCT_COMPACT({groups}), ', ')"})
    dup_q = next(x for x in b["qes"] if x["on_failure"] == "REFUSE_IF_USED")
    dup_warning = (f"IFF(n_fan = 0 AND n_dup > 0, OBJECT_CONSTRUCT('code', {q(dup_q['warning'])}, 'expectation', "
                   f"{q(dup_q['id'])}, 'count', n_dup, 'message', "
                   + tpl(W[dup_q["warning"]], {"count": "n_dup::VARCHAR"}) + "), NULL)")
    rows_q = [x for x in b["qes"] if x["call_scope"] == "REQUEST_ROWS" and x["on_failure"] == "WARN"]
    tables = {t: fq(t) for t in b["tables"]}
    q_cols = ",\n           ".join(f"{quality_sql(x, b['tables'], tables, {b['st']: tcol}, b['snap'], None, None)} AS {x['id']}"
                                   for x in rows_q)
    warn_rows = ", ".join(
        f"IFF(COALESCE(qr.{x['id']}, 0) <> 0, OBJECT_CONSTRUCT('code', {q(x['warning'])}, 'expectation', {q(x['id'])}, "
        f"'count', qr.{x['id']}, 'message', "
        + tpl(W[x["warning"]], {"count": f"qr.{x['id']}::VARCHAR", "expectation": q(x["id"]), "condition": q(x["condition"])})
        + "), NULL)" for x in rows_q)
    closing_cond = f"r.{tcol} = r.last_month"
    return f"""WITH rq AS (SELECT PARSE_JSON(:req) AS r),
periods AS (
    SELECT f.index AS p_idx, f.value:period::VARCHAR AS period, f.value:kind::VARCHAR AS kind,
           f.value:first_month::DATE AS first_month, f.value:last_month::DATE AS last_month
    FROM rq, TABLE(FLATTEN(INPUT => rq.r:periods)) f
),
grain_sets AS (SELECT f.index AS g_idx, f.value::ARRAY AS gs FROM rq, TABLE(FLATTEN(INPUT => rq.r:grains)) f),
analysis_months AS (
    SELECT DISTINCT DATEADD(month, g.k, p.first_month) AS as_of_month
    FROM periods p JOIN (SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1 AS k FROM TABLE(GENERATOR(ROWCOUNT => {MAX_RANGE_MONTHS}))) g
      ON g.k <= DATEDIFF(month, p.first_month, p.last_month)
),
item AS (
    SELECT {ik},
           {proj}
    FROM {fq(it)} GROUP BY {ik}
),
base AS (
    SELECT p.p_idx, p.last_month, {sa}.{tcol}, {sa}.{ik}, ({qty}) AS qty,
           {(',' + chr(10) + '           ').join(other_sel)}
    FROM rq
    JOIN periods p ON TRUE
    JOIN {st} {sa} ON {sa}.{tcol} BETWEEN p.first_month AND p.last_month{''.join(other_joins)}
    WHERE {(chr(10) + '      AND ').join(other_gate + other_filters)}
),
scope_items AS (
    SELECT DISTINCT base.{ik} FROM base
    WHERE base.{ik} IN (SELECT d.{ik} FROM {fq(it)} d, rq WHERE {raw_item_filters})
),
stock_rows AS (
    SELECT base.*, {', '.join(f'item.{x} AS {x}' for x in item_attrs)},
           {', '.join(f'item.{c} AS {k}' for k, c in unit_cols.items())}
    FROM base JOIN rq ON TRUE
    LEFT JOIN item ON {item_on}
    WHERE (NOT ({used(item_attrs)}) OR item.{ik} IS NOT NULL)
      AND {item_filters}
),
grouped AS (
    SELECT r.p_idx, g.g_idx,
           {grouped_attrs},
           SUM(IFF({closing_cond}, r.qty, {b['pa']['missing_value']})) AS closing_stock,
           COUNT_IF({closing_cond}) AS last_month_rows,
           COUNT(DISTINCT r.{ik}) AS n_items, COUNT(DISTINCT r.u_dimension) AS n_dims,
           MIN(r.u_base_unit) AS base_unit, MIN(r.u_native_unit) AS native_unit
    FROM stock_rows r JOIN grain_sets g ON TRUE
    GROUP BY ALL
),
out0 AS (
    SELECT g.*, p.period, p.first_month, p.last_month, {attrs_obj} AS attrs,
           IFF(g.g_idx = 0, 'DETAIL', 'TOTAL') AS row_type,
           {unit} AS stock_unit
    FROM grouped g JOIN periods p ON p.p_idx = g.p_idx JOIN rq ON TRUE
),
out AS (
    SELECT out0.*, ARRAY_TO_STRING(TRANSFORM(rq.r:grain::ARRAY, a -> COALESCE(GET(out0.attrs, a::VARCHAR)::VARCHAR, '')), '|') AS sort_key
    FROM out0 JOIN rq ON TRUE
),
agg AS (SELECT MAX(n_items) AS max_items, MAX(n_dims) AS max_dims FROM out),
dup AS (
    SELECT d.{ik}, COUNT(*) AS n_rows,
           {fan_counts}
    FROM {fq(it)} d WHERE d.{ik} IN (SELECT {ik} FROM scope_items) GROUP BY d.{ik} HAVING COUNT(*) > 1
),
fan AS (SELECT dup.{ik}, {differ} AS differ FROM dup JOIN rq ON TRUE),
fan_q AS (
    SELECT (SELECT COUNT(*) FROM fan WHERE ARRAY_SIZE(differ) > 0) AS n_fan, (SELECT COUNT(*) FROM dup) AS n_dup,
           {fan_values}
),
qr AS (
    SELECT {q_cols}
)
SELECT OBJECT_CONSTRUCT_KEEP_NULL(
    'ROWS', (SELECT COALESCE(ARRAY_AGG(OBJECT_PICK(OBJECT_CONSTRUCT_KEEP_NULL(
                 'period', period, 'first_month', TO_VARCHAR(first_month), 'last_month', TO_VARCHAR(last_month),
                 'row_type', row_type, 'closing_stock', closing_stock, 'stock_unit', stock_unit,
                 'closed_without_snapshot', last_month_rows = 0, {", ".join(f"{q(a)}, {a}" for a in keys)}),
                 ARRAY_CAT(ARRAY_CONSTRUCT('period', 'first_month', 'last_month', 'row_type', 'closing_stock', 'stock_unit',
                                           'closed_without_snapshot'), rq.r:grain::ARRAY)))
                 WITHIN GROUP (ORDER BY p_idx, g_idx, sort_key), ARRAY_CONSTRUCT()) FROM out JOIN rq ON TRUE),
    'ROW_COUNT', (SELECT COUNT(*) FROM out),
    'BASIS_REASON', (SELECT IFF({invalid}, {basis_reason}, NULL) FROM agg JOIN rq ON TRUE),
    'FANOUT_REASON', IFF(fan_q.n_fan > 0, {fan_reason}, NULL),
    'WARNINGS', ARRAY_CONSTRUCT_COMPACT({dup_warning}, {warn_rows})
) AS CV
FROM fan_q, qr"""


# ================================================================================================ the procedure

def note(b: dict) -> str:
    """The period rule, as the contract states it (without its references to the article and to repository files),
    and the totals rule of the contract read for closing stock."""
    pa = " ".join(b["pa"]["description"].split())
    pa = re.sub(r"\s*\((?:step \d of the article|[^)]*data/traps\.yaml[^)]*)[^)]*\)", "", pa)
    tr = b["c"]["totals_rules"][0]
    out = [pa]
    if tr["method"] == "RECOMPUTE":
        out.append("A total is recomputed at its coarser grain from the stock rows, never added from the rows returned.")
    if tr["total_over_time"] == "FORBIDDEN":
        out.append("Several periods give a series with no total across periods.")
    return " ".join(out)


def body(b: dict) -> str:
    c = b["c"]
    contract = f"OBJECT_CONSTRUCT('id', {q(c['id'])}, 'version', {q(c['version'])})"
    caller = ("OBJECT_CONSTRUCT_KEEP_NULL('current_role', par:CALLER_ROLE, 'current_secondary_roles', "
              "par:CALLER_SECONDARY_ROLES, 'current_user', par:CALLER_USER, 'is_agent_activated', par:AGENT_ACTIVATED)")
    available = ("IFF(ctx IS NULL, NULL, OBJECT_CONSTRUCT_KEEP_NULL('first', ctx:AVAILABLE_FIRST, 'last', "
                 "ctx:AVAILABLE_LATEST, 'latest', ctx:AVAILABLE_LATEST))")
    measure = (f"OBJECT_CONSTRUCT('measure', {q(b['snap']['id'])}, 'period_aggregation', {q(b['pa']['id'])}, "
               f"'method', {q(b['pa']['method'])})")

    def raise_if(cond: str, code: str, why: str) -> str:
        return (f"    IF ({cond} IS NOT NULL) THEN\n      rcode := {code};\n      reason := {why};\n"
                f"      RAISE refused;\n    END IF;\n")
    return f"""-- Generated from the contract by compiler/gen_closing_procedure.py. Three statements: the parameters (no table read),
-- the context, the closing rows; values are bound, no SQL text is built at call time.
DECLARE
  refused EXCEPTION (-20001, 'closing stock request refused');
  t0 TIMESTAMP_LTZ;
  t1 TIMESTAMP_LTZ;
  t2 TIMESTAMP_LTZ;
  t3 TIMESTAMP_LTZ;
  rcode VARCHAR;
  reason VARCHAR;
  lineage OBJECT;
  par VARIANT;
  ctx VARIANT;
  cv VARIANT;
  periods_json VARCHAR;
  req VARCHAR;
BEGIN
  t0 := CURRENT_TIMESTAMP();
  BEGIN
    -- ---- 1. the parameters and the caller, reading no table
    SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) INTO :par FROM (
{parameters_sql(b)}
    );
{raise_if("par:P_RCODE::VARCHAR", "par:P_RCODE::VARCHAR", "par:P_REASON::VARCHAR")}    periods_json := TO_JSON(par:PERIODS);
    -- ---- 2. the context: snapshot months, every month of every period, table-scope quality expectations
    t1 := CURRENT_TIMESTAMP();
    SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) INTO :ctx FROM (
{context_sql(b)}
    );
    lineage := OBJECT_CONSTRUCT('context', SQLID);
    t2 := CURRENT_TIMESTAMP();
{raise_if("ctx:RCODE::VARCHAR", "ctx:RCODE::VARCHAR", "ctx:REASON::VARCHAR")}{raise_if("par:Q_RCODE::VARCHAR", "par:Q_RCODE::VARCHAR", "par:Q_REASON::VARCHAR")}    req := TO_JSON(OBJECT_CONSTRUCT('periods', ctx:PERIODS, 'basis', par:BASIS, 'grain', par:GRAIN, 'grains', par:GRAINS,
                                    'filters', par:FILTERS, 'used', par:USED));
    -- ---- 3. the closing rows and the request-scoped quality checks
    SELECT CV INTO :cv FROM (
{closing_sql(b)}
    );
    lineage := OBJECT_INSERT(lineage, 'closing', SQLID);
    t3 := CURRENT_TIMESTAMP();
    -- ---- data checks, in check_order
{raise_if("cv:FANOUT_REASON::VARCHAR", "'MASTER_DATA_FANOUT'", "cv:FANOUT_REASON::VARCHAR")}{raise_if("ctx:DQ_REASON::VARCHAR", "'DATA_QUALITY_FAILED'", "ctx:DQ_REASON::VARCHAR")}{raise_if("cv:BASIS_REASON::VARCHAR", "'BASIS_NOT_COMPARABLE'", "cv:BASIS_REASON::VARCHAR")}  EXCEPTION
    WHEN refused THEN
      RETURN OBJECT_CONSTRUCT('status', 'refused', 'contract', {contract}, 'measure', {measure},
               'refusal', OBJECT_CONSTRUCT('code', rcode, 'reason', reason), 'available_months', {available},
               'caller', {caller}, 'lineage', OBJECT_CONSTRUCT('query_ids', COALESCE(lineage, OBJECT_CONSTRUCT())),
               'timing_ms', OBJECT_CONSTRUCT_KEEP_NULL('context_ms', DATEDIFF('millisecond', t1, t2),
                                                      'total_ms', DATEDIFF('millisecond', t0, CURRENT_TIMESTAMP())));
  END;
  RETURN OBJECT_CONSTRUCT('status', 'ok', 'contract', {contract}, 'measure', {measure},
           'request', OBJECT_CONSTRUCT_KEEP_NULL('periods', ctx:PERIODS, 'basis', par:BASIS, 'grain', par:GRAIN,
                                                 'filters', par:FILTERS, 'totals', par:TOTALS),
           'rows', COALESCE(cv:ROWS, ARRAY_CONSTRUCT()), 'row_count', cv:ROW_COUNT,
           'warnings', COALESCE(cv:WARNINGS, ARRAY_CONSTRUCT()),
           'note', {q(note(b))},
           'available_months', {available}, 'caller', {caller},
           'lineage', OBJECT_CONSTRUCT('query_ids', lineage),
           'timing_ms', OBJECT_CONSTRUCT('context_ms', DATEDIFF('millisecond', t1, t2), 'closing_ms',
                                         DATEDIFF('millisecond', t2, t3), 'total_ms', DATEDIFF('millisecond', t0, CURRENT_TIMESTAMP())));
END;"""


PARAMS = [   # name, description; every parameter is a VARCHAR, lists and maps are JSON strings
    ("periods", None, "JSON array of periods, each {forms}. Several periods give a series, never a total across periods."),
    ("grain", None, "JSON array of attributes to break the closing stock down by, at least one."),
    ("filters", None, "JSON object, attribute to list of values. \"{{}}\" for no filter."),
    ("basis", "'{default}'", "NATIVE (one item per row), QTY_EQ (kg or L equivalent, one dimension per row, the default) "
                             "or VALUE (EUR). A basis the rows returned cannot sum is refused with the bases allowed."),
    ("totals", "'[]'", "JSON array of coarser grains, each a subset of grain; [] for none, [[]] for a grand total. Each "
                       "total is recomputed from the stock rows, never added from the rows returned."),
]


def render_sql(c: dict) -> str:
    b = build(c)
    text = body(b)
    if "$$" in text:
        raise ValueError("the procedure body holds $$, which would end its dollar-quoted text")
    sig = ",\n    ".join(f"{n.upper()} VARCHAR" + (f" DEFAULT {d.format(default=b['bm']['default_basis'])}" if d else "")
                         for n, d, _ in PARAMS)
    head = [
        f"-- GENERATED from contract/stock_coverage.yaml (contract {c['id']}, version {c['version']})",
        "-- by compiler/gen_closing_procedure.py. Do not edit: change the contract and run",
        "-- `python compiler/gen_closing_procedure.py`. tests/test_generated.py regenerates this file and fails on any difference.",
        "--",
        f"-- {PROCEDURE}: closing stock ({b['pa']['id']}, {b['pa']['method']}, member set {b['pa']['member_set']}, missing "
        f"value {b['pa']['missing_value']}) at question time,",
        f"-- from {b['st']} and its dimensions only; refusals, warnings and the query ids of its statements as one JSON answer.",
        "-- Parameters (lists and maps are JSON strings):",
    ]
    for n, _, d in PARAMS:
        head.append(f"--   {n}: {d.format(forms=FORMS)}")
    head += [
        "-- Refusal codes, in check order: " + ", ".join(b["codes"]) + ".",
        "--",
        f"-- Run as {ROLE} with no secondary role:",
        "--   snow sql -c <connection> -f <this file>",
        "USE SECONDARY ROLES NONE;",
        f"USE ROLE {ROLE};",
        "",
        f"CREATE OR REPLACE PROCEDURE {PROCEDURE}(\n    {sig})",
        "RETURNS VARIANT",
        "LANGUAGE SQL",
        f"COMMENT = 'Generated from contract {c['id']} {c['version']} by compiler/gen_closing_procedure.py (SQL Scripting)'",
        "EXECUTE AS CALLER",
        "AS",
        "$$",
    ]
    return "\n".join(head) + "\n" + text + "\n$$;\n"


render = render_sql


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = p.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(render_sql(yaml.safe_load(a.contract.read_text())))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
