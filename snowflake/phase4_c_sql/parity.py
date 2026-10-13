"""
Session 8b, step 2: parity of the SQL Scripting procedure with the Python one, by direct CALL (no agent).
Session 8c-0 (contract 0.5.0): named arguments (basis follows filters and is optional), the basis and selection cases
below, and a relative tolerance of 1e-12 on top of the absolute 1e-9 (the summary sums tens of millions of EUR).

    python snowflake/phase4_c_sql/parity.py [--out <run dir>/parity.json]

The same argument strings go to both procedures, for every case of tests/test_procedure.py (heroes in both units,
refusals, totals, series, invariant members, default scope), the parameters of every coverage question of
generated/reference_questions.yaml, and the extra parsing cases of the parity checklist (section 7). Answers are
compared as parsed JSON after removing the query id values (their keys are compared) and timing_ms; numbers within
1e-9. Equivalence only: correctness is asserted on numbers by tests/test_procedure.py, run against both procedures.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import snowflake.connector
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TRAPS = yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())
TRAP = {t["id"]: t for t in TRAPS["traps"]}
QUESTIONS = yaml.safe_load((ROOT / "generated" / "reference_questions.yaml").read_text())["questions"]
PY, SQL = "LINKML_METRICS.RAW.STOCK_COVERAGE_PY", "LINKML_METRICS.RAW.STOCK_COVERAGE"   # after the swap (decision 2)
AS_OF = "2026-06-01"
TOL = 1e-9


def enc(v):
    return v if v is None or isinstance(v, str) else json.dumps(v)


def q(tid, **extra):
    t = TRAP[tid]["query"]
    f = {a: v if isinstance(v, list) else [v] for a, v in t["filters"].items()}
    f.update(extra)
    return list(t["grain"]), f


def cases() -> list[tuple[str, tuple]]:
    out = []
    add = lambda name, *a: out.append((name, tuple(enc(x) for x in a)))  # noqa: E731
    G1, F1 = ["family_code", "country_code"], {"family_code": ["PANTRY_FLOUR"], "country_code": ["FR"]}
    for unit in ("QTY_EQ", "VALUE"):
        for tid in ("T1", "T2", "T3", "T4", "T7", "T8", "NO_DEMAND", "BEYOND_H", "T9", "BULK_SCOPE"):
            add(f"hero {tid} {unit}", [AS_OF], unit, *q(tid), [])
        g, f = q("T3")
        add(f"T3 hold {unit}", [AS_OF], unit, g, {**f, "batch_status": ["QUALITY_HOLD"]}, [])
        f2 = dict(f); f2.pop("batch_status")
        add(f"T3 all {unit}", [AS_OF], unit, g, f2, [])
        add(f"T3 by status {unit}", [AS_OF], unit, g + ["batch_status"], f2, [])
        ex = TRAP["BULK_SCOPE"]["related"]["explicit_filter"]
        add(f"BULK explicit {unit}", [AS_OF], unit, TRAP["BULK_SCOPE"]["query"]["grain"], ex["filters"] | {"family_code": ["HOT_GROUND"]}, [])
        add(f"T6 refusal {unit}", None, unit, *q("T6"), [])
        lq = TRAP["T7"]["refusal_questions"][0]
        add(f"T7 lifecycle refusal {unit}", [AS_OF], unit, lq["query"]["grain"], {a: [v] for a, v in lq["query"]["filters"].items()}, [])
        add(f"T5 raw refusal {unit}", [AS_OF], TRAP["T5"]["query"]["basis"], *q("T5"), [])
        add(f"DIM_MIX {unit}", [AS_OF], unit, *q("DIM_MIX"), [])
    add("T1 children", [AS_OF], "QTY_EQ", ["sku_code", "country_code"], q("T1")[1], [])
    add("T9 May", ["2026-05-01"], "QTY_EQ", *q("T9"), [])
    add("T5 QTY_EQ", [AS_OF], "QTY_EQ", *q("T5"), [])
    add("LATEST", ["LATEST"], "QTY_EQ", *q("T1"), [])
    refusals = [
        ("AS_OF_MISSING empty", "", "QTY_EQ", G1, F1, None), ("AS_OF_MISSING []", "[]", "QTY_EQ", G1, F1, None),
        ("AS_OF_INVALID text", "June 2026", "QTY_EQ", G1, F1, None),
        ("AS_OF_INVALID unclosed", '["2026-06-01"', "QTY_EQ", G1, F1, None),
        ("AS_OF_NOT_MONTH_START", ["2026-06-15"], "QTY_EQ", G1, F1, None),
        ("AS_OF_TOO_MANY", [f"{y}-{m:02d}-01" for y in (2024, 2025, 2026) for m in range(1, 13)][:25], "QTY_EQ", G1, F1, None),
        ("AS_OF_NO_SNAPSHOT", ["2026-07-01"], "QTY_EQ", G1, F1, None),
        ("AS_OF_NO_SNAPSHOT two", ["2026-05-01", "2026-10-01"], "QTY_EQ", G1, F1, None),
        ("BASIS_NOT_COMPARABLE packs", [AS_OF], "packs", G1, F1, None), ("BASIS_UNKNOWN", [AS_OF], "TONNES", G1, F1, None),
        ("GRAIN_MALFORMED", [AS_OF], "QTY_EQ", '{"family_code": 1}', F1, None),
        ("GRAIN_EMPTY", [AS_OF], "QTY_EQ", [], F1, None),
        ("GRAIN_DUPLICATE", [AS_OF], "QTY_EQ", ["family_code", "family_code"], F1, None),
        ("FILTERS_MALFORMED", [AS_OF], "QTY_EQ", G1, '["FR"]', None),
        ("FILTER_VALUES_INVALID", [AS_OF], "QTY_EQ", G1, {"country_code": []}, None),
        ("ATTRIBUTE_UNKNOWN", [AS_OF], "QTY_EQ", G1, {**F1, "brand": ["X"]}, None),
        ("TOTALS_MALFORMED", [AS_OF], "QTY_EQ", G1, F1, '["country_code"]'),
        ("TOTALS_NOT_SUBSET region", [AS_OF], "QTY_EQ", G1, F1, [["region_code"]]),
        ("TOTALS_NOT_SUBSET grain", [AS_OF], "QTY_EQ", G1, F1, [G1]),
        ("MASTER_DATA_FANOUT", [AS_OF], "QTY_EQ", G1, {"family_code": ["PANTRY_OIL"], "lifecycle_status": ["ACTIVE"]}, None),
        ("order 1", ["2026-06-15"], "TONNES", [], {"brand": ["X"]}, None), ("order 2", [AS_OF], "TONNES", [], {"brand": ["X"]}, None),
        ("order 2b", [AS_OF], "RAW", [], {"brand": ["X"]}, None),
        ("order 3", [AS_OF], "QTY_EQ", [], {"brand": ["X"]}, None),
        ("key order 1", [AS_OF], "QTY_EQ", G1, '{"country_code": [], "family_code": []}', None),
        ("key order 2", [AS_OF], "QTY_EQ", G1, '{"family_code": [], "country_code": []}', None),
        ("key order 3", [AS_OF], "QTY_EQ", G1, '{"brand": ["X"], "aisle": ["Y"]}', None),
        ("key order 4", [AS_OF], "QTY_EQ", G1, '{"aisle": ["Y"], "brand": ["X"]}', None),
        ("dup order 1", [AS_OF], "QTY_EQ", ["country_code", "family_code", "country_code", "family_code"], F1, None),
        ("dup order 2", [AS_OF], "QTY_EQ", ["family_code", "country_code", "family_code", "country_code"], F1, None),
        ("nested as_of", '[["2026-06-01", {"m": 6}]]', "QTY_EQ", G1, F1, None),
        # extra parsing cases (checklist section 7)
        ("as_of integer item", "[2026]", "QTY_EQ", G1, F1, None),
        ("as_of bool item", "[true]", "QTY_EQ", G1, F1, None),
        ("as_of float item", "[2026.5]", "QTY_EQ", G1, F1, None),
        ("as_of null item", "[null]", "QTY_EQ", G1, F1, None),
        ("as_of blank list", "[ ]", "QTY_EQ", G1, F1, None),
        ("as_of object", '{"m": "2026-06-01"}', "QTY_EQ", G1, F1, None),
        ("as_of comma list", "2026-05-01, LATEST", "QTY_EQ", G1, F1, None),
        ("as_of latest lower", '["latest", "2026-06-01"]', "QTY_EQ", G1, F1, None),
        ("as_of bad day", '["2026-02-30"]', "QTY_EQ", G1, F1, None),
        ("as_of single quotes", "['2026-06-01']", "QTY_EQ", G1, F1, None),
        ("as_of trailing comma", '["2026-06-01",]', "QTY_EQ", G1, F1, None),
        ("unit lower hyphen", [AS_OF], "qty-eq", G1, F1, None),
        ("unit synonym", [AS_OF], " Euros ", G1, F1, None),
        ("unit raw spaced", [AS_OF], "raw units", G1, F1, None),
        ("unit null", [AS_OF], None, G1, F1, None),
        ("grain comma list", [AS_OF], "QTY_EQ", "family_code, Country_Code", F1, None),
        ("grain null", [AS_OF], "QTY_EQ", None, F1, None),
        ("grain number item", [AS_OF], "QTY_EQ", '["family_code", 3]', F1, None),
        ("filters null", [AS_OF], "QTY_EQ", ["region_code"], None, None),
        ("filters scalar value", [AS_OF], "QTY_EQ", G1, '{"family_code": "PANTRY_FLOUR", "country_code": "FR"}', None),
        ("filters numeric value", [AS_OF], "QTY_EQ", G1, '{"family_code": ["PANTRY_FLOUR"], "country_code": [7]}', None),
        ("filters null value", [AS_OF], "QTY_EQ", G1, '{"country_code": null}', None),
        ("filters bool item", [AS_OF], "QTY_EQ", G1, '{"country_code": [true]}', None),
        ("filters duplicate key", [AS_OF], "QTY_EQ", G1, '{"country_code": ["DE"], "country_code": ["FR"], "family_code": ["PANTRY_FLOUR"]}', None),
        ("filters upper key", [AS_OF], "QTY_EQ", G1, '{" Family_Code ": ["PANTRY_FLOUR"], "COUNTRY_CODE": ["FR"]}', None),
        ("filters text", [AS_OF], "QTY_EQ", G1, "country_code=FR", None),
        ("totals text", [AS_OF], "QTY_EQ", G1, F1, "country_code"),
        ("totals duplicate", [AS_OF], "QTY_EQ", G1, F1, '[["country_code"], ["COUNTRY_CODE"], []]'),
        ("totals bad item", [AS_OF], "QTY_EQ", G1, F1, '[["country_code", 1]]'),
        ("totals repeated name", [AS_OF], "QTY_EQ", G1, F1, '[["family_code", "family_code"]]'),
        ("totals null", [AS_OF], "QTY_EQ", G1, F1, "null"),
    ]
    for name, *args in refusals:
        add(name, *args)
    levels = [(["sku_code", "country_code"], ["country_code"], {"family_code": ["PANTRY_FLOUR"], "country_code": ["FR"]}),
              (["sku_code", "family_code"], ["family_code"], {"family_code": ["PANTRY_OIL"]}),
              (["family_code", "range_code"], ["range_code"], {"range_code": ["PANTRY"], "country_code": ["FR", "GB"]}),
              (["country_code", "region_code"], ["region_code"], {"region_code": ["WEST"], "family_code": ["PANTRY_PASTA"]}),
              (["region_code"], [], {"family_code": ["PANTRY_RICE"]})]
    for g, t, f in levels:
        add(f"totals {g} -> {t}", [AS_OF], "QTY_EQ", g, f, [t])
        add(f"separate {t or 'grand'}", [AS_OF], "QTY_EQ", t or g[:1], f, [[]] if not t else [])
    add("no total across months", ["2026-04-01", "2026-05-01", AS_OF], "QTY_EQ", *q("T1"), [[]])
    add("members all", [AS_OF], "QTY_EQ", ["sku_code", "country_code"], {}, [])
    add("members released", [AS_OF], "QTY_EQ", ["sku_code", "country_code"], {"batch_status": ["RELEASED"]}, [])
    for m in (["2026-04-01", "2026-05-01", AS_OF], ["2026-04-01"], ["2026-05-01"], [AS_OF]):
        add(f"series {m}", m, "QTY_EQ", ["family_code", "country_code"], {"range_code": ["PANTRY"]}, [])
    g, f = q("T3"); f.pop("batch_status")
    add("T3 series", ["2026-04-01", "2026-05-01", AS_OF], "QTY_EQ", g, f, [])
    g, f = q("BULK_SCOPE")
    add("default scope explicit STANDARD", [AS_OF], "QTY_EQ", g, {**f, "item_type": ["STANDARD"]}, [])
    add("by item_type no filter", [AS_OF], "QTY_EQ", g + ["item_type"], f, [])
    add("VALUE T1 grand total", [AS_OF], "VALUE", *q("T1"), [[]])
    for rq in QUESTIONS:
        if rq["asked_to_agent_c"]:
            p = rq["tool_parameters"]
            add(f"question {rq['id']}", p["as_of_months"], p["basis"], p["grain"], p["filters"], p.get("totals", []),
                p.get("selection") or None)
    # ---- session 8c-0: basis and selection
    FR, SKU, SKC = {"country_code": ["FR"]}, ["sku_code"], ["sku_code", "country_code"]
    extra = [
        ("basis default (None) on DIM_MIX", [AS_OF], None, *q("DIM_MIX"), []),
        ("basis kg synonym", [AS_OF], "kg", *q("T1"), []), ("basis euros synonym", [AS_OF], " euros ", *q("T1"), []),
        ("basis null text", [AS_OF], "null", *q("T1"), []),
        ("DIM_MIX by dimension", [AS_OF], "QTY_EQ", ["country_code", "dimension"], FR, []),
        ("DIM_MIX by dimension NATIVE", [AS_OF], "NATIVE", ["country_code", "dimension"], FR, []),
        ("own unit NATIVE", [AS_OF], "NATIVE", SKU, {"sku_code": ["SKU-0046"]}, []),
        ("own unit NATIVE by batch status", [AS_OF], "NATIVE", SKU + ["batch_status"], {"sku_code": ["SKU-0046"]}, []),
        ("NATIVE family refused", [AS_OF], "NATIVE", *q("T1"), []),
        ("NATIVE sku x country T1", [AS_OF], "NATIVE", SKC, q("T1")[1], []),
        ("NATIVE sku x country total refused", [AS_OF], "NATIVE", SKC, q("T1")[1], [["country_code"]]),
        ("stockout heroes", [AS_OF], "QTY_EQ", SKC, {"sku_code": ["SKU-H01", "SKU-H02", "SKU-H07", "SKU-H08", "SKU-H09", "SKU-H10"]}, []),
        ("(c) FR below 3", [AS_OF], "QTY_EQ", SKU, FR, [], {"coverage_below": "3"}),
        ("(d) world first 10", [AS_OF], "QTY_EQ", SKU, {}, [], {"rank_first": "10"}),
        ("(e) pairs above 12 VALUE", [AS_OF], "VALUE", SKC, {}, [], {"coverage_above": "12"}),
        ("(e) world above 12 VALUE", [AS_OF], "VALUE", SKU, {}, [], {"coverage_above": "12"}),
        ("window 3..6 first 5", [AS_OF], "QTY_EQ", SKC, {}, [], {"coverage_below": "6", "coverage_above": "3", "rank_first": "5"}),
        ("selection keeps nothing", [AS_OF], "QTY_EQ", SKU, FR, [], {"coverage_below": "0.1"}),
        ("selection NATIVE several items", [AS_OF], "NATIVE", SKU, FR, [], {"coverage_below": "3"}),
        ("selection NATIVE one item", [AS_OF], "NATIVE", SKU, FR, [], {"rank_first": "1"}),
        ("selection series", ["2026-04-01", "2026-05-01", AS_OF], "QTY_EQ", SKU, FR, [], {"rank_first": "3"}),
        ("selection snapshot-only grain", [AS_OF], "QTY_EQ", SKU + ["batch_status"], FR, [], {"coverage_below": "2"}),
        ("selection with totals VALUE", [AS_OF], "VALUE", SKC, FR, [["country_code"]], {"coverage_below": "3", "rank_first": "2"}),
        ("selection grand total QTY_EQ refused", [AS_OF], "QTY_EQ", SKU, {}, [[]], {"rank_first": "10"}),
        ("selection explicit BULK", [AS_OF], "QTY_EQ", SKU, {"item_type": ["STANDARD", "BULK"]}, [], {"coverage_above": "12"}),
        ("scope warning VALUE", [AS_OF], "VALUE", *q("BULK_SCOPE"), []),
        ("scope warning NATIVE refused", [AS_OF], "NATIVE", *q("BULK_SCOPE"), []),
        ("scope warning NATIVE one sku", [AS_OF], "NATIVE", SKU, {"family_code": ["HOT_GROUND"], "sku_code": ["SKU-0001"]}, []),
        ("region grand total VALUE", [AS_OF], "VALUE", ["region_code"], {}, [[]]),
        ("SELECTION_INVALID below 0", [AS_OF], "QTY_EQ", SKU, {}, [], {"coverage_below": "0"}),
        ("SELECTION_INVALID below text", [AS_OF], "QTY_EQ", SKU, {}, [], {"coverage_below": "soon"}),
        ("SELECTION_INVALID below negative", [AS_OF], "QTY_EQ", SKU, {}, [], {"coverage_below": "-1"}),
        ("SELECTION_INVALID rank decimal", [AS_OF], "QTY_EQ", SKU, {}, [], {"rank_first": "2.5"}),
        ("SELECTION_INVALID rank zero", [AS_OF], "QTY_EQ", SKU, {}, [], {"rank_first": "0"}),
        ("SELECTION_INVALID above zero", [AS_OF], "QTY_EQ", SKU, {}, [], {"coverage_above": "0"}),
        ("SELECTION_INVALID window", [AS_OF], "QTY_EQ", SKU, {}, [], {"coverage_below": " 3 ", "coverage_above": "5"}),
        ("selection spaced numbers", [AS_OF], "QTY_EQ", SKU, FR, [], {"coverage_below": " 3.0 ", "rank_first": " 2 "}),
        ("selection null text", [AS_OF], "QTY_EQ", SKU, FR, [], {"coverage_below": "null"}),
        ("selection after a parameter fault", [AS_OF], "TONNES", SKU, {}, [], {"coverage_below": "0"}),
    ]
    for name, *args in extra:
        add(name, *args)
    return out


def connect():
    con = snowflake.connector.connect(connection_name=os.environ.get("LINKML_SF_CONNECTION", "perso"))
    cur = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH"):
        cur.execute(s)
    return con, cur


NAMES = ("AS_OF_MONTHS", "BASIS", "GRAIN", "FILTERS", "TOTALS")


def call(cur, proc, args):
    """args: (as_of, basis, grain, filters, totals[, selection JSON]) as strings; named arguments, as the agent calls."""
    named = dict(zip(NAMES, args[:5]))
    if len(args) > 5 and args[5]:
        named.update({k.upper(): v for k, v in json.loads(args[5]).items()})
    cur.execute(f"CALL {proc}(" + ", ".join(f"{k} => %({k})s" for k in named) + ")", named)
    return json.loads(cur.fetchone()[0])


def normalise(a):
    a = json.loads(json.dumps(a))
    a.pop("timing_ms", None)
    a["lineage"]["query_ids"] = sorted(a["lineage"]["query_ids"])
    return a


def diff(x, y, path="") -> list[str]:
    if isinstance(x, bool) or isinstance(y, bool) or x is None or y is None:
        return [] if x == y else [f"{path}: {x!r} != {y!r}"]
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        return [] if math.isclose(x, y, rel_tol=1e-12, abs_tol=TOL) else [f"{path}: {x!r} != {y!r}"]
    if isinstance(x, dict) and isinstance(y, dict):
        out = [f"{path}: keys {sorted(set(x) ^ set(y))}"] if set(x) != set(y) else []
        return out + [d for k in sorted(set(x) & set(y)) for d in diff(x[k], y[k], f"{path}.{k}")]
    if isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            return [f"{path}: length {len(x)} != {len(y)}"]
        return [d for i, (a, b) in enumerate(zip(x, y)) for d in diff(a, b, f"{path}[{i}]")]
    return [] if x == y else [f"{path}: {x!r} != {y!r}"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    con, cur = connect()
    rows, failed = [], 0
    for name, args in cases():
        r = {"case": name, "args": args}
        try:
            py, sq = call(cur, PY, args), call(cur, SQL, args)
            d = diff(normalise(py), normalise(sq))
            r.update(status=py["status"], code=(py.get("refusal") or {}).get("code"), rows=py.get("row_count"),
                     identical=not d, diffs=d[:10], python=py, sql=sq)
        except snowflake.connector.errors.ProgrammingError as e:
            r.update(identical=False, diffs=[f"error {e.errno}: {e.msg}"])
        failed += not r["identical"]
        rows.append(r)
        print(f"{'ok ' if r['identical'] else 'DIFF'} {name}: {r.get('status')} {r.get('code') or ''} {r['diffs'][:2] if not r['identical'] else ''}",
              flush=True)
    con.close()
    print(f"{len(rows) - failed} / {len(rows)} identical")
    if a.out:
        a.out.write_text(json.dumps(rows, indent=1, default=str))


if __name__ == "__main__":
    main()
