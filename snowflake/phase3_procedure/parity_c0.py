"""
Parity of the generated STOCK_COVERAGE with probe C0 (STOCK_COVERAGE_PROBE) on the 25 checks of
snowflake/probe_c0/check_direct.py. The same argument strings go to both procedures (the generated one accepts a bare
month and a comma-separated grain, as C0 did). Prints a markdown table: values (coverage, flag, stock) or refusal
codes side by side, and the expected value from data/traps.yaml.

    python snowflake/phase3_procedure/parity_c0.py [--connection perso]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import connect  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TRAPS = {t["id"]: t for t in yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())["traps"]}
AS_OF = "2026-06-01"


def q(trap, **extra):
    t = TRAPS[trap]["query"]
    f = {a: [v] for a, v in t["filters"].items()}
    f.update({a: v if isinstance(v, list) else [v] for a, v in extra.items()})
    return list(t["grain"]), f


def cases():
    out = []
    g, f = q("T1")
    out += [("T1 family x country (QTY_EQ)", (AS_OF, "QTY_EQ", g, f), TRAPS["T1"]["expected"], None),
            ("T1 same, VALUE variant", (AS_OF, "VALUE", g, f), TRAPS["T1"]["expected"], None)]
    for sku, v in TRAPS["T1"]["children"].items():
        out.append((f"T1 child {sku}", (AS_OF, "QTY_EQ", ["sku_code", "country_code"], f), v, {"sku_code": sku}))
    out.append(("T2 sparse months", (AS_OF, "QTY_EQ", *q("T2")), TRAPS["T2"]["expected"], None))
    out.append(("T3 released lots", (AS_OF, "QTY_EQ", *q("T3")), TRAPS["T3"]["expected"], None))
    out.append(("T3 quality hold only", (AS_OF, "QTY_EQ", *q("T3", batch_status="QUALITY_HOLD")),
                TRAPS["T3"]["related"]["quality_hold_only"], None))
    g, f = q("T3")
    f.pop("batch_status")
    out.append(("T3 all statuses", (AS_OF, "QTY_EQ", g, f), TRAPS["T3"]["related"]["all_statuses"], None))
    out.append(("T3 by status: RELEASED row", (AS_OF, "QTY_EQ", g + ["batch_status"], f), TRAPS["T3"]["expected"],
                {"batch_status": "RELEASED"}))
    out.append(("T3 by status: QUALITY_HOLD row", (AS_OF, "QTY_EQ", g + ["batch_status"], f),
                TRAPS["T3"]["related"]["quality_hold_only"], {"batch_status": "QUALITY_HOLD"}))
    out.append(("T4 as-of month", (AS_OF, "QTY_EQ", *q("T4")), TRAPS["T4"]["expected"], None))
    out.append(("T7 duplicated master data", (AS_OF, "QTY_EQ", *q("T7")), TRAPS["T7"]["expected"], None))
    out.append(("T8 forecast, no stock", (AS_OF, "QTY_EQ", *q("T8")), TRAPS["T8"]["expected"], None))
    out.append(("NO_DEMAND", (AS_OF, "QTY_EQ", *q("NO_DEMAND")), None, None))
    out.append(("BEYOND_H", (AS_OF, "QTY_EQ", *q("BEYOND_H")), TRAPS["BEYOND_H"]["expected"], None))
    g, f = q("T1")
    out += [("T6 no as-of month (NULL)", (None, "QTY_EQ", g, f), "AS_OF_MISSING", None),
            ("T6 no as-of month (empty)", ("", "QTY_EQ", g, f), "AS_OF_MISSING", None),
            ("mid-month as-of", ("2026-06-15", "QTY_EQ", g, f), "AS_OF_NOT_MONTH_START", None),
            ("malformed as-of", ("June 2026", "QTY_EQ", g, f), "AS_OF_INVALID", None),
            ("as-of without snapshot", ("2026-07-01", "QTY_EQ", g, f), "AS_OF_NO_SNAPSHOT", None),
            ("raw unit", (AS_OF, "RAW", g, f), "UNIT_RAW_NOT_ADDITIVE", None),
            ("lifecycle_status in the grain", (AS_OF, "QTY_EQ", g + ["lifecycle_status"], f), "ATTRIBUTE_UNCLASSIFIED", None),
            ("unknown attribute", (AS_OF, "QTY_EQ", g, {**f, "brand": ["X"]}), "ATTRIBUTE_UNKNOWN", None),
            ("empty grain", (AS_OF, "QTY_EQ", [], f), "GRAIN_EMPTY", None),
            ("grain as a comma-separated list", (AS_OF, "QTY_EQ", "family_code, country_code", f),
             TRAPS["T1"]["expected"], None)]
    return out


def outcome(res, row):
    if res.get("status") == "refused":
        return ("refused", res.get("reason_code") or res["refusal"]["code"])
    rows = [r for r in res["rows"] if r.get("row_type", "DETAIL") == "DETAIL"
            and (row is None or all(r.get(k) == v for k, v in row.items()))]
    if len(rows) != 1:
        return ("rows", len(rows))
    r = rows[0]
    v = r["coverage_months"]
    return ("ok", None if v is None else round(v, 4), r["flag"], round(r["stock"], 4))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--connection", default="perso")
    a = p.parse_args()
    cur = connect(a.connection).cursor()
    enc = lambda v: v if v is None or isinstance(v, str) else json.dumps(v)  # noqa: E731
    print("| # | Case | Expected (traps.yaml) | C0 `STOCK_COVERAGE_PROBE` | Generated `STOCK_COVERAGE` | Same |")
    print("|---|---|---|---|---|---|")
    same = 0
    for i, (name, (as_of, unit, grain, filters), exp, row) in enumerate(cases(), 1):
        cur.execute("CALL LINKML_METRICS.RAW.STOCK_COVERAGE_PROBE(%s, %s, %s, %s)", (as_of, unit, enc(grain), enc(filters)))
        c0 = outcome(json.loads(cur.fetchone()[0]), row)
        cur.execute("CALL LINKML_METRICS.RAW.STOCK_COVERAGE(%s, %s, %s, %s)", (as_of, unit, enc(grain), enc(filters)))
        gen = outcome(json.loads(cur.fetchone()[0]), row)
        ok = c0 == gen
        same += ok
        print(f"| {i} | {name} | {exp if exp is not None else 'NULL, NO_DEMAND'} | {c0} | {gen} | {'yes' if ok else '**no**'} |")
    print(f"\n{same} / {len(cases())} identical")


if __name__ == "__main__":
    main()
