"""
Probe C0: call STOCK_COVERAGE_PROBE directly (no agent) and assert numbers against data/traps.yaml.

    python snowflake/probe_c0/check_direct.py            # as LINKML_SVC (connection linkml_svc)

Expected values are read from traps.yaml, never typed here, except the refusals, which have no value.
Asserts on numbers, refusal codes and the caller seen inside the procedure. Exits non-zero on any failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import snowflake.connector
import yaml

ROOT = Path(__file__).resolve().parents[2]
TRAPS = {t["id"]: t for t in yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())["traps"]}
AS_OF = "2026-06-01"
PROC = "LINKML_METRICS.RAW.STOCK_COVERAGE_PROBE"


def q(trap: str, **extra_filters) -> tuple[list[str], dict]:
    t = TRAPS[trap]["query"]
    f = {a: [v] for a, v in t["filters"].items()}
    f.update({a: v if isinstance(v, list) else [v] for a, v in extra_filters.items()})
    return list(t["grain"]), f


def main() -> None:
    con = snowflake.connector.connect(connection_name="linkml_svc")
    cur = con.cursor()
    cur.execute("USE SECONDARY ROLES NONE")

    def call(as_of, unit, grain, filters):
        cur.execute(f"CALL {PROC}(%s, %s, %s, %s)",
                    (as_of, unit, json.dumps(grain), None if filters is None else json.dumps(filters)))
        return json.loads(cur.fetchone()[0])

    results, failures = [], 0

    def check(name, res, expect_value=None, expect_flag=None, refused=None, row=None, expect_stock=None):
        nonlocal failures
        ok, got = True, None
        if refused:
            got = res.get("reason_code")
            ok = res.get("status") == "refused" and got == refused
        else:
            rows = res.get("rows", [])
            match = [r for r in rows if row is None or all(r.get(k) == v for k, v in row.items())]
            if res.get("status") != "ok" or len(match) != 1:
                ok, got = False, res.get("reason_code") or f"{len(match)} matching rows of {len(rows)}"
            else:
                r = match[0]
                got = (r["coverage_months"], r["flag"], r["stock"])
                if expect_value is None:
                    ok = r["coverage_months"] is None
                else:
                    ok = r["coverage_months"] is not None and abs(r["coverage_months"] - expect_value) < 1e-4
                ok = ok and (expect_flag is None or r["flag"] == expect_flag)
                ok = ok and (expect_stock is None or abs(r["stock"] - expect_stock) < 1e-6)
        caller = res.get("caller") or {}
        role_ok = caller.get("current_role") == "LINKML_METRICS_ROLE" and \
            json.loads(caller.get("current_secondary_roles") or "{}").get("roles", None) == ""
        ok = ok and role_ok
        failures += not ok
        exp = f"refused {refused}" if refused else (expect_value, expect_flag)
        results.append((name, exp, got, "PASS" if ok else "FAIL"))

    g, f = q("T1")
    check("T1 family x country (QTY_EQ)", call(AS_OF, "QTY_EQ", g, f), TRAPS["T1"]["expected"])
    check("T1 same, VALUE variant", call(AS_OF, "VALUE", g, f), TRAPS["T1"]["expected"])
    res = call(AS_OF, "QTY_EQ", ["sku_code", "country_code"], f)
    for sku, v in TRAPS["T1"]["children"].items():
        check(f"T1 child {sku}", res, v, row={"sku_code": sku})
    g, f = q("T2")
    check("T2 sparse months", call(AS_OF, "QTY_EQ", g, f), TRAPS["T2"]["expected"])
    g, f = q("T3")
    check("T3 released lots (stock-only filter)", call(AS_OF, "QTY_EQ", g, f), TRAPS["T3"]["expected"])
    g, f = q("T3", batch_status="QUALITY_HOLD")
    check("T3 quality hold only", call(AS_OF, "QTY_EQ", g, f), TRAPS["T3"]["related"]["quality_hold_only"])
    g, f = q("T3")
    f.pop("batch_status")
    check("T3 all statuses", call(AS_OF, "QTY_EQ", g, f), TRAPS["T3"]["related"]["all_statuses"])
    res = call(AS_OF, "QTY_EQ", g + ["batch_status"], f)
    check("T3 by status: RELEASED row", res, TRAPS["T3"]["expected"], row={"batch_status": "RELEASED"})
    check("T3 by status: QUALITY_HOLD row", res, TRAPS["T3"]["related"]["quality_hold_only"],
          row={"batch_status": "QUALITY_HOLD"})
    g, f = q("T4")
    check("T4 June 2026 = as-of month", call(AS_OF, "QTY_EQ", g, f), TRAPS["T4"]["expected"])
    g, f = q("T7")
    check("T7 duplicated master data", call(AS_OF, "QTY_EQ", g, f), TRAPS["T7"]["expected"],
          expect_stock=TRAPS["T7"]["expected_stock_qty_eq"])
    g, f = q("T8")
    check("T8 forecast, no stock: row kept", call(AS_OF, "QTY_EQ", g, f), TRAPS["T8"]["expected"])
    g, f = q("NO_DEMAND")
    check("NO_DEMAND", call(AS_OF, "QTY_EQ", g, f), None, expect_flag="NO_DEMAND")
    g, f = q("BEYOND_H")
    check("BEYOND_H", call(AS_OF, "QTY_EQ", g, f), TRAPS["BEYOND_H"]["expected"], expect_flag="BEYOND_HORIZON")

    g, f = q("T1")
    check("T6 no as-of month (NULL)", call(None, "QTY_EQ", g, f), refused="AS_OF_MISSING")
    check("T6 no as-of month (empty)", call("", "QTY_EQ", g, f), refused="AS_OF_MISSING")
    check("mid-month as-of", call("2026-06-15", "QTY_EQ", g, f), refused="AS_OF_NOT_MONTH_START")
    check("malformed as-of", call("June 2026", "QTY_EQ", g, f), refused="AS_OF_INVALID")
    check("as-of without snapshot", call("2026-07-01", "QTY_EQ", g, f), refused="AS_OF_NO_SNAPSHOT")
    check("raw unit", call(AS_OF, "RAW", g, f), refused="UNIT_RAW_NOT_ADDITIVE")
    check("unclassified attribute", call(AS_OF, "QTY_EQ", g + ["lifecycle_status"], f),
          refused="ATTRIBUTE_UNCLASSIFIED")
    check("unknown attribute", call(AS_OF, "QTY_EQ", g, {**f, "brand": ["X"]}), refused="ATTRIBUTE_UNKNOWN")
    check("empty grain", call(AS_OF, "QTY_EQ", [], f), refused="GRAIN_EMPTY")
    cur.execute(f"CALL {PROC}(%s, %s, %s, %s)", (AS_OF, "QTY_EQ", "family_code, country_code", json.dumps(f)))
    check("T1 grain as a comma-separated list", json.loads(cur.fetchone()[0]), TRAPS["T1"]["expected"])

    w = max(len(r[0]) for r in results)
    for name, exp, got, verdict in results:
        print(f"{verdict}  {name:<{w}}  expected {exp}  got {got}")
    res = call(AS_OF, "QTY_EQ", *q("T3"))
    print("\ncaller inside the procedure:", json.dumps(res["caller"]))
    print(f"\n{len(results) - failures} / {len(results)} pass")
    con.close()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
