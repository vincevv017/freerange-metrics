"""
Session 13, step 4: C-raw against C, turn by turn (same question, same repetition index), by the mechanism classes of
step 1 (eval/mechanism_classes.yaml). Offline: the grade files and run summaries of the campaign's run folder. No call.

    python snowflake/session13_craw/compare.py [--out <run dir>/../s13/compare.json]

Per stage and class: correct / wrong / manual for C and C-raw under rubric 3.2 (score of record), 3.3 and figure-only;
the turns whose verdict differs; the tools of each C-raw turn (H-CR-4: a closing-stock turn on the view); the median
client seconds and input tokens per turn of each class, C beside C-raw; the served version of every C-raw turn.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = Path.home() / "work" / "assets" / "linkml-metrics-runs" / "campaign"
CLASSES = yaml.safe_load((ROOT / "eval" / "mechanism_classes.yaml").read_text())["questions"]
TAGS = {1: ("campaign-s1", "craw-s1"), 2: ("campaign-s2", "craw-s2")}
FAMILY = {"stock_coverage": "procedure", "closing_stock": "closing_stock", "system_execute_sql": "view",
          "system_agentic_semantic_context": "view"}


def grades(tag: str, rubric: str) -> list[dict]:
    f = RUN / (f"grades_{tag}.json" if rubric == "3.2" else f"grades_{tag}.rubric-{rubric}.json")
    return json.loads(f.read_text()) if f.exists() else []


def key(g: dict) -> tuple[str, int]:
    return g["question_id"], int(re.search(r"_r(\d+)$", g["label"]).group(1))


def summary(label: str) -> dict:
    p = RUN / f"summary_{label.lower().replace('-', '_')}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def tools(s: dict) -> list[str]:
    out = []
    for c in s.get("calls", []):
        for u in c.get("tool_uses") or []:
            n, t = u.get("name") or "", u.get("type") or ""
            out.append(FAMILY.get(n) or ("view" if n.endswith("semantic_view") or "semantic" in t else n or t))
    return out


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    report: dict = {}
    for stage, (ctag, rtag) in TAGS.items():
        st: dict = {"classes": {}, "differences": [], "turns": []}
        by = {r: ({key(g): g for g in grades(ctag, r) if g["config"] == "C"},
                  {key(g): g for g in grades(rtag, r) if g["config"] == "CR"}) for r in ("3.2", "3.3")}
        c32, r32 = by["3.2"]
        if not r32:
            continue
        for k in sorted(r32):
            qid = k[0]
            cls = CLASSES[qid]["class"]
            cg, rg = c32.get(k), r32[k]
            cs, rs = summary(cg["label"]) if cg else {}, summary(rg["label"])
            row = {"question": qid, "rep": k[1], "class": cls, "also": CLASSES[qid].get("also"),
                   "C": cg and cg["verdict"], "CR": rg["verdict"],
                   "C_3.3": (by["3.3"][0].get(k) or {}).get("verdict"), "CR_3.3": (by["3.3"][1].get(k) or {}).get("verdict"),
                   "C_figure_only": cg and cg["verdict_figure_only"], "CR_figure_only": rg["verdict_figure_only"],
                   "C_tools": dict(Counter(tools(cs))), "CR_tools": dict(Counter(tools(rs))),
                   "C_seconds": sum(c.get("seconds_total") or 0 for c in cs.get("calls", [])) if cs else None,
                   "CR_seconds": sum(c.get("seconds_total") or 0 for c in rs.get("calls", [])),
                   "C_input": (cs.get("tokens") or {}).get("input"), "CR_input": (rs.get("tokens") or {}).get("input"),
                   "CR_served_version": rs.get("served_version"),
                   "CR_routing": rg["criteria"].get("routing", {}).get("result"),
                   "CR_why": {c: v["why"] for c, v in rg["criteria"].items() if v["result"] != "pass"}}
            if cls == "CLOSING_STOCK" and "view" in row["CR_tools"]:
                row["H_CR_4"] = True
            st["turns"].append(row)
            if (row["C"], row["C_figure_only"]) != (row["CR"], row["CR_figure_only"]):
                st["differences"].append({k2: row[k2] for k2 in ("question", "rep", "class", "C", "CR", "C_figure_only",
                                                                 "CR_figure_only", "CR_tools", "C_tools", "CR_why")})
        for cls in ("COVERAGE", "CLOSING_STOCK", "GENERAL", "REFUSAL"):
            rows = [t for t in st["turns"] if t["class"] == cls]
            cnt = lambda f: dict(Counter(t[f] for t in rows))   # noqa: E731
            st["classes"][cls] = {"turns": len(rows), "C": cnt("C"), "CR": cnt("CR"), "C_3.3": cnt("C_3.3"),
                                  "CR_3.3": cnt("CR_3.3"), "C_figure_only": cnt("C_figure_only"),
                                  "CR_figure_only": cnt("CR_figure_only"),
                                  "median_seconds": {"C": med([t["C_seconds"] for t in rows]),
                                                     "CR": med([t["CR_seconds"] for t in rows])},
                                  "median_input_tokens": {"C": med([t["C_input"] for t in rows]),
                                                          "CR": med([t["CR_input"] for t in rows])}}
        also = [t for t in st["turns"] if t["also"]]
        st["also_COVERAGE"] = {"turns": len(also), "C": dict(Counter(t["C"] for t in also)),
                               "CR": dict(Counter(t["CR"] for t in also))}
        st["H_CR_4"] = [(t["question"], t["rep"], t["CR_tools"]) for t in st["turns"] if t.get("H_CR_4")]
        st["served_versions"] = dict(Counter(str(t["CR_served_version"]) for t in st["turns"]))
        report[f"stage{stage}"] = st
    text = json.dumps(report, indent=1, default=str)
    if a.out:
        a.out.write_text(text)
    for s, st in report.items():
        print(f"== {s}")
        for cls, v in st["classes"].items():
            print(f"  {cls:13} n={v['turns']:2}  C {v['C']}  CR {v['CR']}  | 3.3 C {v['C_3.3']} CR {v['CR_3.3']}  | fig C "
                  f"{v['C_figure_only']} CR {v['CR_figure_only']}  | s {v['median_seconds']}  tok {v['median_input_tokens']}")
        print("  also COVERAGE (N1, N2):", st["also_COVERAGE"])
        print("  differences:", json.dumps(st["differences"], default=str)[:3000])
        print("  H-CR-4:", st["H_CR_4"], " served:", st["served_versions"])


if __name__ == "__main__":
    main()
