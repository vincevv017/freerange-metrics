"""
Fifth generator: the contract's failure modes and the traps' refusal questions -> generated/reference_questions.yaml.

    python compiler/gen_questions.py                          # writes generated/reference_questions.yaml
    python compiler/gen_questions.py --out /tmp/q.yaml        # writes elsewhere (the drift test uses this)

The question set of the evaluation campaign: one question per failure mode (its `reference_question`), plus every
`refusal_questions` entry of data/traps.yaml, plus the drill questions below (a follow-up in the same thread). Each
question is put in grocery wording (a SKU code gets its product name, AS_OF becomes the month in words) and carries
what a correct answer is: the value, flag, warnings or refusal code, and the tool parameters that produce it, all read
from data/traps.yaml (hand-computed or frozen there, asserted by tests/test_procedure.py). A drill's expected rows come
from data/coverage_ref.py (pandas, an equivalence reference) and are asserted against the procedure by the same test.

Closing-stock questions (metric closing_stock) are in the set for the configurations that read the generated closing
view; the coverage procedure does not answer them, so agent C is not asked them.
Session 8: the two general questions of data/traps.yaml (G1 forecast, G2 closing stock value by country), not about
coverage, with their pandas-computed values. Every question carries expected_route, the tool family a correct agent
uses: coverage (the configuration's coverage mechanism: the procedure, the skill, or the semantic view where there is
nothing else), semantic_view (closing stock and the general questions), or clarify (no tool: ask for the month).
No expected value is read from the procedure: tests/test_reference_oracle.py recomputes every one in pandas.
The output is deterministic: same contract, traps and dataset, same bytes.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTRACT_PATH = ROOT / "contract" / "stock_coverage.yaml"
TRAPS_PATH = ROOT / "data" / "traps.yaml"
DATA = ROOT / "data" / "output"
DEFAULT_OUT = ROOT / "generated" / "reference_questions.yaml"
DRILLS = [   # (asked after, follow-up, attribute added to the grain)
    ("BULK_SCOPE", "And by country?", "country_code"),
]


def month_words(d: dt.date) -> str:
    return d.strftime("%B %Y")


def wording(text: str, heroes: dict, as_of: dt.date) -> str:
    t = text.strip()
    t = re.sub(r"^Stock coverage (of|in) ", r"What is the stock coverage \1 ", t)
    t = re.sub(r"^Closing stock of ", "What was the closing stock of ", t)
    t = re.sub(r"SKU-H\d\d", lambda m: f"{heroes[m.group(0)][0].lower()}{heroes[m.group(0)][1:]} ({m.group(0)})", t)
    t = t.replace(" for the AS_OF month", f" for {month_words(as_of)}").replace(" at AS_OF", f" as of {month_words(as_of)}")
    t = t.replace(" in AS_OF", f" in {month_words(as_of)}")      # session 8c-0, question (b) as the owner words it
    return t.rstrip(".") + "?"


def params(q: dict, as_of: dt.date) -> dict:
    f = {a: v if isinstance(v, list) else [v] for a, v in q["filters"].items()}
    months = None if "as_of_months" in q and q["as_of_months"] is None else [as_of.isoformat()]
    out = {"as_of_months": months, "basis": q.get("basis", "QTY_EQ"), "grain": q["grain"], "filters": f}
    sel = {k: q[k] for k in SELECTION if k in q}     # session 8c-0: the member selection, when the question asks one
    if sel:
        out["selection"] = sel
    return out


SELECTION = ("coverage_below", "coverage_above", "rank_first")


def expected(t: dict, contract: dict) -> dict:
    out: dict = {}
    if "expected_refusal" in t:
        code = t["expected_refusal"]
        out["refusal"] = code
        rc = next(r for r in contract["refusal_codes"] if r["id"] == code)
        if code == "AS_OF_MISSING":
            out["also_correct"] = "a clarifying question asking for the analysis month, with no number"
        out["reason_template"] = rc["reason_template"]
        if "expected_allowed_bases" in t:            # session 8c-0: the bases the refusal names
            out["allowed_bases"] = t["expected_allowed_bases"]
        for basis, key in (("QTY_EQ", "qty_eq"), ("VALUE", "value")):
            if t.get("related", {}).get(key) is not None:
                out["offer_instead"] = {"basis": basis, "value": t["related"][key]}
        wrong = {k: v for k, v in t.get("wrong", {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        if wrong:
            out["wrong_values"] = wrong
        return out
    out["value"] = t["expected"]
    out["flag"] = t.get("expected_flag")
    out["warnings"] = t.get("expected_warnings", {})
    out["names_as_of"] = True
    wrong = {k: v for k, v in t.get("wrong", {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    if wrong:
        out["wrong_values"] = wrong
    return out


def build(contract: dict, traps: dict) -> dict:
    manifest = json.loads((DATA / "manifest.json").read_text())
    as_of = dt.date.fromisoformat(manifest["as_of"])
    heroes = {h["sku"]: h["name"] for h in traps["hero_items"]}
    trap = {t["id"]: t for t in traps["traps"]}
    closing = {c["id"]: c for c in traps.get("closing_stock", [])}
    qs = []
    for fm in contract["failure_modes"]:
        tid = fm["id"]
        base = {"id": tid, "failure_mode": tid, "source_question": fm["reference_question"],
                "question": wording(fm["reference_question"], heroes, as_of)}
        if tid in trap:
            t = trap[tid]
            route = "clarify" if t.get("expected_refusal") == "AS_OF_MISSING" else "coverage"
            qs.append({**base, "metric": contract["metrics"][0]["id"], "asked_to_agent_c": True, "expected_route": route,
                       "tool_parameters": params(t["query"], as_of), "expected": expected(t, contract)})
            for n, rq in enumerate(t.get("refusal_questions", []), start=1):
                qs.append({"id": f"{tid}_R{n}", "failure_mode": tid, "source_question": rq["question"],
                           "question": wording(rq["question"], heroes, as_of), "metric": contract["metrics"][0]["id"],
                           "asked_to_agent_c": True, "expected_route": "coverage",
                           "tool_parameters": params(rq["query"], as_of),
                           "expected": expected(rq, contract)})
        elif tid in closing:
            c = closing[tid]
            qs.append({**base, "metric": "closing_stock", "asked_to_agent_c": False, "expected_route": "semantic_view",
                       "answered_by": "LINKML_METRICS.RAW.CLOSING_STOCK_SV (generated/closing_stock_sv.sql)",
                       "query": c["query"], "expected": {"value": c["expected"], "wrong_values": c["wrong"]}})
        else:
            raise ValueError(f"failure mode {tid} has no trap in data/traps.yaml")
    from data.coverage_ref import load, py_coverage   # pandas reference, equivalence only
    tables = load(DATA)
    scope = contract["default_scopes"][0]
    for after, text, attr in DRILLS:
        parent = next(q for q in qs if q["id"] == after)
        p = copy.deepcopy(parent["tool_parameters"])
        p["grain"] = parent["tool_parameters"]["grain"] + [attr]
        f = copy.deepcopy(p["filters"])
        f.setdefault(scope["attribute"], scope["included_values"])
        ref = py_coverage(tables, as_of, p["grain"], f, p["basis"])
        rows = [{**dict(zip(p["grain"], k)), "value": r.value, "flag": r.flag} for k, r in sorted(ref.items())]
        warnings = dict(parent["expected"]["warnings"])
        qs.append({"id": f"{after}_DRILL", "failure_mode": parent["failure_mode"], "follows": after,
                   "question": text, "metric": parent["metric"], "asked_to_agent_c": True,
                   "expected_route": "coverage", "tool_parameters": p,
                   "expected": {"rows": rows, "warnings_codes": sorted(warnings), "names_as_of": True,
                                "never": "add or average the country rows; the family total is the parent answer"}})
    for g in traps["general_questions"]:
        q = {"id": g["id"], "failure_mode": None, "source_question": g["question"], "question": g["question"],
             "metric": g["query"]["measure"], "asked_to_agent_c": False, "expected_route": "semantic_view",
             "query": g["query"]}
        if "expected_rows" in g:
            q["expected"] = {"rows": [{"country_code": c, "value": v} for c, v in g["expected_rows"].items()],
                             "unit": "EUR", "wrong_values": g["wrong"],
                             "never": "join the snapshot to DIM_ITEM without one row per item: SKU-H06 counts twice in SE"}
        else:
            fam = g["query"]["filters"].get("family_code")
            units = sorted(set(tables["DIM_ITEM"].loc[tables["DIM_ITEM"].family_code == fam, "base_unit"]))
            if len(units) != 1:                             # one dimension: a quantity equivalent is comparable
                raise ValueError(f"{g['id']}: family {fam} mixes base units {units}")
            q["expected"] = {"value": g["expected"], "unit": f"{units[0]} equivalent (QTY_EQ)", "wrong_values": g["wrong"]}
        qs.append(q)
    for s in traps.get("showcase_questions", []):     # session 8c-0: questions (a), (c), (d), (e); (b) is DIM_MIX
        qy = s["query"]
        e = {"names_as_of": True, "names_basis": qy["basis"]}
        if "expected" in s:
            e.update({"value": s["expected"], "flag": None, "stock_unit": s["expected_stock_unit"],
                      "stockout_month": s["expected_stockout_month"], "related": s.get("related", {})})
        if "expected_rows" in s:
            e["rows"] = [{"sku_code": k, "value": v, "stock_unit": u, "stockout_month": m} for k, v, u, m in s["expected_rows"]]
        if "expected_summary" in s:
            e["summary"] = s["expected_summary"]
            e["set_apart"] = s["expected_apart"]
        if s["id"] == "S_DORMANT_VALUE":
            e["graded_on"] = "the count of pairs and the stock value they tie up (71.0 million EUR rounded is right), not the listing"
            e["total_stock_value"] = s["total_stock_value"]
            e["related"] = s["related"]
        qs.append({"id": s["id"], "label": s["label"], "failure_mode": None, "source_question": s["question"],
                   "question": s["question"], "metric": contract["metrics"][0]["id"], "asked_to_agent_c": True,
                   "expected_route": "coverage", "tool_parameters": params(qy, as_of), "expected": e})
    for h in traps.get("held_out_questions", []):     # session 8c: held out of stage 1, asked in stage 2 only
        qs.append(list_question(h, {"held_out": True}, contract, as_of))
    for n in traps.get("stage2_questions", []):       # session 9b (owner, 2026-10-07): added in stage 2
        flag = {"added_in_stage": 2}
        if "closing_stock" not in n:
            qs.append(list_question(n, flag, contract, as_of, route=n["expected_route"]))
            continue
        cs, cv = n["closing_stock"], n["coverage"]
        if "expected" in cs:
            e_cs = {"value": cs["expected"], "wrong_values": cs["wrong"]}
        else:                                         # one closing stock per month, each month its own period
            e_cs = {"rows": [{"month": m, "value": v} for m, v in cs["expected_by_month"].items()],
                    "wrong_values": cs["wrong_by_month"], "added_over_months": cs["wrong_over_months"],
                    "never": "add or average the months: the closing stock of a month is its own snapshot"}
        e_cv = {"value": cv["expected"], "flag": cv.get("expected_flag"), "warnings": cv.get("expected_warnings", {}),
                "wrong_values": cv["wrong"]}
        qs.append({"id": n["id"], **flag, "failure_mode": None, "source_question": n["question"],
                   "question": n["question"], "metric": "closing_stock_and_coverage", "asked_to_agent_c": True,
                   "expected_route": n["expected_route"],
                   "answered_by": "the closing-stock view for the closing stock, the coverage mechanism for coverage",
                   "query": cs["query"], "tool_parameters": params(cv["query"], as_of),
                   "expected": {"names_as_of": True, "names_basis": "QTY_EQ", "closing_stock": e_cs, "coverage": e_cv}})
    return {"contract": {"id": contract["id"], "version": contract["version"]}, "as_of": as_of.isoformat(),
            "questions": qs}


def list_question(h: dict, flag: dict, contract: dict, as_of: dt.date, route: str = "coverage") -> dict:
    """A list question of data/traps.yaml (held out in session 8c, or added in stage 2 in session 9b): its tool
    parameters and the expected rows, items, summary and members set apart."""
    e = {"names_as_of": True, "names_basis": "QTY_EQ", "graded_on": h["graded_on"]}
    queries = h.get("queries") or [h["query"]]
    grain = queries[-1]["grain"]
    if "expected_items" in h:
        e["items"] = h["expected_items"]
        e["calls"] = h["expected_calls"]
    if "expected_rows" in h:     # the coverage is in months; measured_in is the unit of stock and forecast
        e["rows"] = [{**dict(zip(grain, r[:len(grain)])), "coverage_months": r[len(grain)],
                      "measured_in": r[len(grain) + 1], "stockout_month": r[len(grain) + 2]} for r in h["expected_rows"]]
        if h["graded_on"] == "item_set":
            e["items"] = [r[0] for r in h["expected_rows"]]
    if "expected_summary" in h:
        e["summary"] = h["expected_summary"]
    if "expected_apart" in h:
        e["set_apart"] = h["expected_apart"]
    e["wrong_values"] = h.get("wrong", {})
    tp = ({"calls": [params(x, as_of) for x in queries],
           "combine": "intersection of the sku_code values the calls return"} if len(queries) > 1
          else params(queries[0], as_of))
    return {"id": h["id"], **flag, "failure_mode": None, "source_question": h["question"],
            "question": h["question"], "metric": contract["metrics"][0]["id"], "asked_to_agent_c": True,
            "expected_route": route, "tool_parameters": tp, "expected": e}


def render(contract: dict, traps: dict) -> str:
    head = (f"# GENERATED from contract/stock_coverage.yaml (contract {contract['id']}, version {contract['version']}),\n"
            "# data/traps.yaml and data/output/ by compiler/gen_questions.py. Do not edit: run `python compiler/gen_questions.py`.\n"
            "# tests/test_generated.py regenerates this file and fails on any difference; tests/test_procedure.py asserts every\n"
            "# expected value, flag, warning and refusal against the procedure.\n")
    return head + yaml.safe_dump(build(contract, traps), sort_keys=False, allow_unicode=True, width=118)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = p.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(render(yaml.safe_load(CONTRACT_PATH.read_text()), yaml.safe_load(TRAPS_PATH.read_text())))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
