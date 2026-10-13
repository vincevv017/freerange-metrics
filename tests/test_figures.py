"""
Session 16: the article's figures (docs/figures/, written by tools/make_figures.py) hold their sources' values. The data
of each figure is recomputed here from the published files, without the script's readers, and checked against
figures.json, the SVG's embedded data and the text it draws; where a second published file records the same value, it
is checked too. Pixels are not compared. Offline: no Snowflake call, no dataset needed.
Session 17c: figure 2 is drawn from the generated files (it was a copy of a raster) and is the README's diagram; figure
3 shows C-raw's turn (session 13), not C's. Where the run folder is here, C-raw's recorded calls are checked too.
Session 17d: figure 5 draws both stage 1 scores of the README, the score of record and right figure, basis named;
figure 2's evaluation box is the repository's harness (eval/), not Snowflake's agent evaluations.
Session 17e: figure 5 is one bar per configuration, right figure, basis named, with its billed credits; figure 6 is the
article's results table, every cell read from a published file. Figure 3 is five blocks: the answer's first sentence
only is drawn (the whole answer and the refusal's reason stay in the data), under 1100 units tall.
"""

from __future__ import annotations

import html
import json
import re
import struct
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
RUN = Path.home() / "work" / "assets" / "linkml-metrics-runs" / "campaign"
CRAW_SUMMARY = RUN / "summary_cr_dim_mix_craw_s1_r1.json"
NAMES = ["01-closing-stock-trap", "02-how-it-works", "03-one-question", "04-closing-rule-two-ways", "05-trade-off",
         "06-results-table"]
PNG_WIDTHS = {"06-results-table": 1200}                 # the others 1600
ACCENT, NEUTRAL = "#F04A1E", "#9B7BFF"


def _yaml(rel):
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


def _text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _png_size(p: Path) -> list[int]:
    return list(struct.unpack(">II", p.read_bytes()[16:24]))


def expected_fig1() -> dict:
    traps = _yaml("data/traps.yaml")
    trap = {t["id"]: t for t in traps["closing_stock"]}["CS_LAST_MONTH_GAP"]
    hero = {h["sku"]: h for h in traps["hero_items"]}["SKU-H11"]
    as_of = _yaml("generated/reference_questions.yaml")["as_of"]
    assert as_of == "2026-06-01" and trap["query"]["period_k"] == [-2, 0]
    stock = hero["stock_by_k"]
    return {"sku": "SKU-H11", "item": hero["name"], "country": "Switzerland", "period": "Q2 2026",
            "months": [{"month": "2026-04-01", "stock": stock.get(-2)}, {"month": "2026-05-01", "stock": stock.get(-1)},
                       {"month": "2026-06-01", "stock": stock.get(0)}],
            "native_value": trap["wrong"]["last_known_value"], "contract_value": trap["expected"]}


def expected_fig2() -> dict:
    agent = _yaml("generated/agent_c_raw.yaml")
    res = agent["tool_resources"]
    return {"agent": "generated/agent_c_raw.yaml",
            "procedures": [res[t["tool_spec"]["name"]]["identifier"].rsplit(".", 1)[1] for t in agent["tools"]
                           if t["tool_spec"]["type"] == "generic"],
            "semantic_views": [res[t["tool_spec"]["name"]]["semantic_view"].rsplit(".", 1)[1] for t in agent["tools"]
                               if t["tool_spec"]["type"] == "cortex_analyst_text_to_sql"],
            "tables": [t["id"] for t in _yaml("contract/stock_coverage.yaml")["tables"]],
            "custom_dmfs": _text("generated/dmf.sql").count("CREATE OR REPLACE DATA METRIC FUNCTION "),
            "reference_questions": len(_yaml("generated/reference_questions.yaml")["questions"])}


def _refusal(tool_result: dict) -> dict:
    return json.loads(json.loads(tool_result["content"])[0]["json"]["result"])["refusal"]


def expected_fig3() -> dict:
    q = {x["id"]: x for x in _yaml("generated/reference_questions.yaml")["questions"]}["DIM_MIX"]
    turn = [json.loads(x) for x in _text("eval/fixtures/recorded_turns.jsonl").splitlines()]
    rec = next(t for t in turn if t["label"] == "c_dim_mix" and t["tool_uses"])   # session 8, the same procedure
    first = _refusal(rec["tool_results"][0])                                      # the refused call
    graded = next(t for t in json.loads(_text("eval/fixtures/grades_craw-s1.json"))
                  if t["config"] == "CR" and t["question_id"] == "DIM_MIX")
    assert [u["input"]["basis"] for u in rec["tool_uses"]] == [q["tool_parameters"]["basis"],
                                                              q["expected"]["offer_instead"]["basis"]]
    return {"question": q["question"], "as_of_month": q["tool_parameters"]["as_of_months"][0],
            "grain": q["tool_parameters"]["grain"], "filters": q["tool_parameters"]["filters"],
            "first_basis": q["tool_parameters"]["basis"], "refusal": first["code"],
            "reason": first["reason"], "second_basis": q["expected"]["offer_instead"]["basis"],
            "value": q["expected"]["offer_instead"]["value"], "answer_source": "eval/fixtures/grades_craw-s1.json",
            "answer_config": "CR", "answer_label": graded["label"], "answer_verdict": graded["verdict"],
            "answer_text": graded["answer"], "basis_switch": graded["criteria"]["basis_switch"]["result"],
            "units": [x["base_unit"] for x in _yaml("contract/stock_coverage.yaml")["basis_model"]["dimensions"]],
            "scope": next(x for x in _yaml("contract/stock_coverage.yaml")["default_scopes"]
                          if x["id"] == "SCOPE_ITEM_TYPE")["included_values"]}


def expected_fig4() -> dict:
    s13 = _text("snowflake/session13_craw/results.md")
    gap = re.search(r"\| `FCT_STOCK_SNAPSHOT_GAPFILLED` \| view \| ([\d,]+) \| .*?([\d,]+) filled rows \(\+([\d.]+) "
                    r"percent\)", s13)
    view_rows, filled = int(gap.group(1).replace(",", "")), int(gap.group(2).replace(",", ""))
    scans = re.search(r"scans ([\d.]+) times the snapshot table", s13)
    members = re.search(r"comparing ([\d,]+) members with 0 differences", s13)
    comp = re.search(r"three statements takes ([\d.]+) s", s13)
    n = int(members.group(1).replace(",", ""))
    return {"view_rows": view_rows, "snapshot_rows": view_rows - filled,
            "added_percent": round(filled / (view_rows - filled) * 100, 1), "quarter_scan_times": float(scans.group(1)),
            "members_equal": n, "members_compared": n, "compilation_s": float(comp.group(1)),
            "_percent_written": float(gap.group(3))}


STAGE1_HEADER = "| Configuration | Right figure, basis named, no unit on the coverage (rubric 3.2, of record)"


def expected_fig5() -> list[dict]:
    readme = _text("README.md")
    table = readme[readme.index(STAGE1_HEADER):]
    table = table[:table.index("\n\n")]
    out = []
    b = r"(?:\*\*)?"
    for row in ("A", "B1", "B2", "C", "C-raw", "D", "D′"):
        m = re.search(rf"^\| {b}{re.escape(row)}{b} \| {b}(\d+){b} \| {b}\d+{b} \| {b}(\d+){b} \| {b}([\d.]+){b} \| "
                      rf"{b}([\d.]+){b} \|$", table, re.M)
        out.append({"row": row, "correct": int(m.group(1)), "figure_only": int(m.group(2)),
                    "latency_s": float(m.group(3)), "credits": float(m.group(4)), "_credits_text": m.group(4)})
    return out


def _half_up(text: str, places: str) -> str:
    return str(Decimal(text).quantize(Decimal(places), rounding=ROUND_HALF_UP))


COLUMNS6 = ["Technique", "Right figure, basis named", "Score of record", "AI Credits per turn", "Refuses with a code"]


def expected_fig6() -> dict:
    """Per README row, stage 1 only: the two scores and the billed credits; coded refusals (stage1_results.md section 3,
    and C-raw's recorded answers)."""
    st1 = " ".join(_text("snowflake/phase5_campaign/stage1_results.md").split())
    assert "**Codes:** only C returns coded refusals" in st1 and "Every other configuration refuses in prose." in st1
    codes = [c["id"] for c in _yaml("contract/stock_coverage.yaml")["refusal_codes"]]
    craw = json.loads(_text("eval/fixtures/grades_craw-s1.json"))
    craw_coded = any(c in t["answer"] for t in craw for c in codes)
    rows = [{"row": r["row"], "figure_only": r["figure_only"], "record_s1": r["correct"], "credits": r["credits"],
             "credits_shown": _half_up(r["_credits_text"], "0.001"),
             "coded_refusal": r["row"] == "C" or (r["row"] == "C-raw" and craw_coded)} for r in expected_fig5()]
    return {"rows": rows}


def test_figures_match_their_sources():
    manifest = json.loads((FIG / "figures.json").read_text(encoding="utf-8"))
    bad: list[str] = []

    def check(name, what, got, want):
        if got != want:
            bad.append(f"{name}: {what}: figure {got!r}, source {want!r}")

    # 1. the closing-stock trap; the native 350 is also the value measured in session 6, as the README states
    d, e = manifest[NAMES[0]]["data"], expected_fig1()
    for k, v in e.items():
        check(NAMES[0], k, d[k], v)
    check(NAMES[0], "probe result", bool(re.search(r"\| SKU-H11 x quarter \(no June snapshot\) \| \*\*350\*\* \| 0 \|",
                                                   _text("snowflake/probe_closing/results.md"))), True)
    check(NAMES[0], "README", "returns **350** (May's stock carried into the quarter's close) instead of **0**"
          in _text("README.md"), True)

    # 2. how it works: the names from the generated files; the README's diagram is the same PNG
    d, e = manifest[NAMES[1]]["data"], expected_fig2()
    for k, v in e.items():
        check(NAMES[1], k, d[k], v)
    check(NAMES[1], "two procedures", d["procedures"], ["STOCK_COVERAGE", "CLOSING_STOCK"])
    check(NAMES[1], "README png", (ROOT / "assets" / "docs" / "how-it-works.png").read_bytes(),
          (FIG / f"{NAMES[1]}.png").read_bytes())
    drawn2 = " ".join(html.unescape(t) for t in re.findall(r"<text[^>]*>(.*?)</text>",
                                                           (FIG / f"{NAMES[1]}.svg").read_text(encoding="utf-8")))
    for s in ("Two procedures", "STOCK_COVERAGE: coverage", "CLOSING_STOCK: closing stock",
              "gets back a figure, a", "warning or a coded refusal", "in no", "answer's path", "Files in generated/",
              "Deploy script", "no Snowflake call", "Evaluation harness", "eval/ in the repository:",
              "grades the answer.", "Not Snowflake's agent evaluations.", "read by", "Seven tables",
              "not generated", "its definition is generated", "Not generated: the seven data tables"):
        check(NAMES[1], f"drawn {s!r}", s in drawn2, True)
    for s in ("Metric procedure", "correct number", "configures", "every Snowflake object", "every object",
              "Reference questions"):
        check(NAMES[1], f"not drawn {s!r}", s in drawn2, False)
    svg2 = (FIG / f"{NAMES[1]}.svg").read_text(encoding="utf-8")
    desc2 = html.unescape(re.search(r'<desc id="d">(.*?)</desc>', svg2, re.S).group(1))
    check(NAMES[1], "desc names the harness", "The evaluation harness, eval/ in the repository, asks the agent each "
          "reference question and grades the answer; it is not Snowflake's agent evaluations." in desc2, True)
    readme = _text("README.md")
    alt = re.search(r'<img alt="(How it works[^"]*)" src="assets/docs/how-it-works.png"', readme).group(1)
    check(NAMES[1], "README alt", ("two procedures" in alt, "a metric procedure" in alt), (True, False))

    # 3. the France turn of C-raw (session 13): the reason as the same procedure returned it, the answer as graded
    d, e = manifest[NAMES[2]]["data"], expected_fig3()
    for k in ("question", "as_of_month", "grain", "filters", "first_basis", "refusal", "reason", "second_basis",
              "value", "answer_source", "answer_config", "answer_label", "answer_verdict", "units", "scope"):
        check(NAMES[2], k, d[k], e[k])
    check(NAMES[2], "C-raw label", d["answer_label"].startswith("CR_DIM_MIX_craw-s1"), True)
    check(NAMES[2], "basis switch graded", e["basis_switch"], "pass")
    check(NAMES[2], "whole answer in the data", d["answer"], e["answer_text"])
    first = re.split(r"(?<=[.!?])\s+", e["answer_text"])[0]
    check(NAMES[2], "excerpt is the first sentence, verbatim", d["answer_excerpt"], first)
    check(NAMES[2], "excerpt", first, "France's stock coverage in June 2026 is about 8.7 months.")
    check(NAMES[2], "8.7 in the answer", f"{e['value']:.1f} months" in e["answer_text"], True)
    svg3 = (FIG / f"{NAMES[2]}.svg").read_text(encoding="utf-8")
    drawn3 = " ".join(html.unescape(t) for t in re.findall(r"<text[^>]*>(.*?)</text>", svg3))
    for s in ("One question, two calls", "June 2026", "France", "kg or L equivalent", "BASIS_NOT_COMPARABLE",
              "France mixes kg and L, which can't be added.", "8.7 months, on value (EUR)",
              "Stock and forecast of France's standard items summed, coverage computed once.", first,
              "Source: graded turn of the raw-table version, eval/fixtures/grades_craw-s1.json."):
        check(NAMES[2], f"drawn {s!r}", s in drawn3, True)
    for s in ("The agent never computes the number.", "grain", e["reason"][:40], "8.70",
              re.split(r"(?<=[.!?])\s+", e["answer_text"])[1]):
        check(NAMES[2], f"not drawn {s!r}", s in drawn3, False)
    desc3 = html.unescape(re.search(r'<desc id="d">(.*?)</desc>', svg3, re.S).group(1))
    check(NAMES[2], "reason in the desc", e["reason"] in desc3, True)
    check(NAMES[2], "height under 1100", float(re.search(r'height="([\d.]+)"', svg3).group(1)) < 1100, True)
    check(NAMES[2], "C-raw source in the caption", "`eval/fixtures/grades_craw-s1.json`"
          in (FIG / f"{NAMES[2]}.md").read_text(encoding="utf-8"), True)

    # 4. the two ways: session 13's records, and the README's figures
    d, e = manifest[NAMES[3]]["data"], expected_fig4()
    check(NAMES[3], "percent as written", e.pop("_percent_written"), e["added_percent"])
    for k, v in e.items():
        check(NAMES[3], k, d[k], v)

    # 5. the trade-off (session 17e): one bar per README row, right figure, basis named, of 24; sorted by score down,
    # then credits up; the label gives the score and the billed credits; the two generated-tool rows in the accent.
    e5 = expected_fig5()
    bars = manifest[NAMES[4]]["data"]["bars"]
    want = sorted(e5, key=lambda r: (-r["figure_only"], r["credits"]))
    check(NAMES[4], "order", [b["row"] for b in bars], [r["row"] for r in want])
    for got, r in zip(bars, want):
        check(NAMES[4], f"{r['row']} score", got["figure_only"], r["figure_only"])
        check(NAMES[4], f"{r['row']} credits", got["credits"], r["credits"])
        check(NAMES[4], f"{r['row']} label", got["label"],
              f"{r['figure_only']} of 24 · {_half_up(r['_credits_text'], '0.001')} credits per turn")
    svg5 = (FIG / f"{NAMES[4]}.svg").read_text(encoding="utf-8")
    rects = [(m["row"], float(m["w"]), m["fill"]) for m in re.finditer(
        r'<rect data-row="(?P<row>[^"]+)" data-series="bar" x="[\d.]+" y="[\d.]+" width="(?P<w>[\d.]+)" '
        r'height="[\d.]+" rx="\d+" fill="(?P<fill>[^"]+)"', svg5)]
    check(NAMES[4], "bars drawn, in order", [r for r, _, _ in rects], [r["row"] for r in want])
    scale = [w / r["figure_only"] for (_, w, _), r in zip(rects, want)]
    check(NAMES[4], "one scale", max(scale) - min(scale) < 0.01, True)
    check(NAMES[4], "accent", {r: f for r, _, f in rects},
          {r["row"]: ACCENT if r["row"] in ("C", "C-raw") else NEUTRAL for r in want})
    drawn5 = " ".join(html.unescape(t) for t in re.findall(r"<text[^>]*>(.*?)</text>", svg5))
    for s in ("More right answers for fewer credits", "Right figure, basis named, out of 24 questions",
              "One run per question", "replayed the same questions after the campaign",
              "the warehouse is billed apart", *[b["label"] for b in bars]):
        check(NAMES[4], f"drawn {s!r}", s in drawn5, True)
    for s in ("filled:", "hollow:", "latency", " s median", "Answers out of 24"):
        check(NAMES[4], f"not drawn {s!r}", s in drawn5, False)
    check(NAMES[4], "no dots", "<circle" in svg5, False)

    # 6. the results table (session 17e): five columns, stage 1 only, every cell from a published file; the
    # generated-tool rows highlighted; the raw-table row marked by an asterisk explained in the footnote.
    e6 = expected_fig6()
    d6 = manifest[NAMES[5]]["data"]
    check(NAMES[5], "five columns", [c["title"] for c in d6["columns"]], COLUMNS6)
    rows6 = {r["row"]: r for r in d6["rows"]}
    check(NAMES[5], "rows", sorted(rows6), sorted(r["row"] for r in e6["rows"]))
    for r in e6["rows"]:
        for k, v in r.items():
            check(NAMES[5], f"{r['row']} {k}", rows6.get(r["row"], {}).get(k), v)
        check(NAMES[5], f"{r['row']} highlighted", rows6.get(r["row"], {}).get("highlight"), r["row"] in ("C", "C-raw"))
        check(NAMES[5], f"{r['row']} no stage 2", {"record_s2", "latency_shown", "prepare"} & set(rows6[r["row"]]),
              set())
    svg6 = (FIG / f"{NAMES[5]}.svg").read_text(encoding="utf-8")
    check(NAMES[5], "highlight drawn", sorted(re.findall(r'data-highlight="([^"]+)"', svg6)), ["C", "C-raw"])
    texts6 = [html.unescape(t) for t in re.findall(r"<text[^>]*>(.*?)</text>", svg6)]
    drawn6 = " ".join(texts6)
    for s in (*COLUMNS6, "Seven ways to give an agent the same metric", "The same 24 questions, the same model",
              "Generated tools, raw tables*", "* replayed the same questions after the campaign.",
              "One run per question", "counts, not rates", "no unit on the coverage", "warehouse"):
        check(NAMES[5], f"drawn {s!r}", s in drawn6, True)
    for s in ("Typical turn", "Data to prepare", "stage 2", "of 30", " / ", "added after the campaign"):
        check(NAMES[5], f"not drawn {s!r}", s in drawn6, False)
    for r in rows6.values():
        name = r["name"] + ("*" if r["row"] == "C-raw" else "")
        check(NAMES[5], f"{r['row']} name on one line", name in texts6, True)
    foot = re.findall(r'<text[^>]*data-footnote="1"[^>]*>', svg6)
    check(NAMES[5], "footnote at most two lines", 1 <= len(foot) <= 2, True)
    w6, h6 = (float(v) for v in re.search(r'<svg[^>]* width="([\d.]+)" height="([\d.]+)"', svg6).groups())
    check(NAMES[5], "about 1200 x 650", (w6, 600 <= h6 <= 700), (1200, True))

    # The README's sentence under the stage 1 table says what the table holds.
    e5 = {r["row"]: r for r in expected_fig5()}
    others = [e5[k]["figure_only"] for k in ("A", "B1", "B2", "D", "D′")]
    check("README", "C unchanged by wording", (e5["C"]["correct"], e5["C"]["figure_only"]), (24, 24))
    check("README", "wording costs the others", all(r["correct"] < r["figure_only"] for k, r in e5.items() if k != "C"),
          True)
    check("README", "sentence", f"Wording costs every setup except C, at {e5['C']['correct']} either way; on figures "
          f"alone, the generated tools score {e5['C']['figure_only']} and {e5['C-raw']['figure_only']}, the others "
          f"{min(others)} to {max(others)}" in " ".join(_text("README.md").split()), True)

    # Every figure: the SVG embeds the same data and draws its numbers; plain words only; a caption naming sources.
    for name in NAMES:
        cap = (FIG / f"{name}.md").read_text(encoding="utf-8")
        for rel in re.findall(r"`([\w./-]+\.(?:yaml|md|json|jsonl|png))`", cap):
            check(name, f"caption source {rel}", (ROOT / rel).exists(), True)
        check(name, "caption has sources", "## Sources" in cap, True)
        check(name, "png width", _png_size(FIG / f"{name}.png")[0], PNG_WIDTHS.get(name, 1600))
        svg = (FIG / f"{name}.svg").read_text(encoding="utf-8")
        meta = re.search(r'<metadata id="figure-data">(.*?)</metadata>', svg, re.S).group(1)
        check(name, "svg data", json.loads(html.unescape(meta)), manifest[name]["data"])
        drawn = " ".join(html.unescape(t) for t in re.findall(r"<text[^>]*>(.*?)</text>", svg))
        for s in manifest[name]["shown"]:
            check(name, f"drawn {s!r}", s in drawn, True)
        check(name, "configuration letters", re.findall(r"\b(?:C-raw|B1|B2)\b|D′|D'", drawn), [])
        for text in (svg, cap):
            check(name, "em dash", chr(0x2014) in text, False)

    assert not bad, "\n".join(bad)


@pytest.mark.skipif(not CRAW_SUMMARY.exists(), reason="the campaign's run folder is not here")
def test_figure3_matches_craw_recorded_calls():
    """C-raw's recorded turn (run folder, not published): two calls, QTY_EQ then VALUE, the figure's code and reason."""
    d = json.loads((FIG / "figures.json").read_text(encoding="utf-8"))[NAMES[2]]["data"]
    call = json.loads(CRAW_SUMMARY.read_text(encoding="utf-8"))["calls"][-1]
    assert call["label"] == d["answer_label"]
    assert [(u["name"], u["input"]["basis"]) for u in call["tool_uses"]] == [
        ("stock_coverage", d["first_basis"]), ("stock_coverage", d["second_basis"])]
    assert _refusal(call["tool_results"][0]) == {"code": d["refusal"], "reason": d["reason"]}
    second = json.loads(json.loads(call["tool_results"][1]["content"])[0]["json"]["result"])
    assert round(second["rows"][0]["coverage_months"], 2) == round(d["value"], 2)
