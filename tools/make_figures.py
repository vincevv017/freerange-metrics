"""
Session 16: the article's figures, from published files only. Offline: no Snowflake call.

Every number drawn is read from a published file: the README tables, data/traps.yaml, generated/reference_questions.yaml,
contract/stock_coverage.yaml, eval/fixtures/ or a results file; none is typed here. The labels (plain names for the
configurations, the words around the numbers) are the only text written here.

Output, in docs/figures/: per figure an SVG, a PNG 1600 px wide, a caption file naming its sources, and figures.json,
the data of every figure, which tests/test_figures.py recomputes from the sources. Figure 2 is also the README's
diagram: its PNG is copied to assets/docs/how-it-works.png (session 17c; before, that PNG had no vector source). The PNGs are rendered by headless Chrome (CHROME, or the macOS default path); without it, the SVGs,
captions and figures.json are still written and the PNGs are left as they are.
Session 17e: figure 5 is one bar per configuration; figure 6, the article's results table (stage 1, five columns),
is a PNG 1200 px wide;
figure 3 is five blocks, the answer's first sentence drawn, the whole answer and the refusal's reason kept in its data.

    python tools/make_figures.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"
FONT = ROOT / "assets" / "fonts" / "SpaceGrotesk-Variable.ttf"
DIAGRAM = ROOT / "assets" / "docs" / "how-it-works.png"
README = ROOT / "README.md"
TRAPS = ROOT / "data" / "traps.yaml"
QUESTIONS = ROOT / "generated" / "reference_questions.yaml"
CONTRACT = ROOT / "contract" / "stock_coverage.yaml"
GRADES_CRAW_S1 = ROOT / "eval" / "fixtures" / "grades_craw-s1.json"       # C-raw's stage 1 turns, session 13
AGENT_CRAW = ROOT / "generated" / "agent_c_raw.yaml"
DMF = ROOT / "generated" / "dmf.sql"
STAGE1 = ROOT / "snowflake" / "phase5_campaign" / "stage1_results.md"
PNG_WIDTH = 1600
W = 800                                           # every SVG is 800 units wide, rendered at 2x
W2 = 1280                                         # except figure 2, a landscape diagram, rendered at 1.25x
W6 = 1200                                         # and figure 6, a table rendered at 1x: 1200 px for Medium and LinkedIn
PNG_WIDTHS = {"06-results-table": 1200}

# The palette of assets/logo and assets/social-preview.svg.
INK, ORANGE, CREAM, MUTED = "#110C2A", "#F04A1E", "#FFF7E8", "#4B4470"
BG, LILAC, VIOLET, WHITE = "#F5F3FF", "#C9BEFF", "#9B7BFF", "#FFFFFF"
PANEL = "#E9E4FF"
FAMILY = "'Space Grotesk', 'Helvetica Neue', Arial, sans-serif"

# Plain names for the README's configuration rows (labels, not data).
PLAIN = {
    "C-raw": "Generated tools, raw tables",
    "C": "Generated tools, gap-filled view",
    "B2": "Generated semantic view",
    "B1": "Hand-written semantic view",
    "A": "Autopilot semantic view",
    "D": "Skill, script computes",
    "D′": "Skill, agent writes queries",
}
BASIS_PLAIN = {"QTY_EQ": "kg or L equivalent", "VALUE": "value (EUR)", "NATIVE": "the item's own unit"}
GRAIN_PLAIN = {"country_code": "country", "sku_code": "item", "family_code": "family"}


# ---------------------------------------------------------------- sources

def _yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def readme_table(header_start: str) -> list[dict[str, str]]:
    """The first README table whose header row starts with header_start, as dicts; bold marks removed."""
    lines = README.read_text(encoding="utf-8").splitlines()
    i = next(n for n, line in enumerate(lines) if line.startswith(header_start))
    cols = [c.strip() for c in lines[i].strip("|").split("|")]
    rows = []
    for line in lines[i + 2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip().replace("**", "") for c in line.strip("|").split("|")]
        rows.append(dict(zip(cols, cells)))
    return rows


def readme_match(pattern: str) -> re.Match:
    m = re.search(pattern, README.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"README: no match for {pattern!r}")
    return m


def month_name(iso: str) -> str:
    return ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
            "November", "December"][int(iso[5:7]) - 1]


def shift_month(iso: str, k: int) -> str:
    y, m = int(iso[:4]), int(iso[5:7]) - 1 + k
    return f"{y + m // 12:04d}-{m % 12 + 1:02d}-01"


def question(qid: str) -> dict:
    return next(q for q in _yaml(QUESTIONS)["questions"] if q["id"] == qid)


def data_fig1() -> dict:
    traps = _yaml(TRAPS)
    trap = next(t for t in traps["closing_stock"] if t["id"] == "CS_LAST_MONTH_GAP")
    sku = trap["query"]["filters"]["sku_code"]
    hero = next(h for h in traps["hero_items"] if h["sku"] == sku)
    as_of = _yaml(QUESTIONS)["as_of"]                                   # the analysis month, k = 0
    q = question("CS_LAST_MONTH_GAP")["question"]
    m = re.search(r" in (\w+) for (Q\d \d{4})\?$", q)
    k0, k1 = trap["query"]["period_k"]
    months = [{"month": shift_month(as_of, k), "stock": hero["stock_by_k"].get(k)} for k in range(k0, k1 + 1)]
    return {"sku": sku, "item": hero["name"], "country": m.group(1), "period": m.group(2), "months": months,
            "native_value": trap["wrong"]["last_known_value"], "contract_value": trap["expected"]}


def data_fig2() -> dict:
    agent = _yaml(AGENT_CRAW)
    res = agent["tool_resources"]
    procs = [res[t["tool_spec"]["name"]]["identifier"].split(".")[-1] for t in agent["tools"]
             if res[t["tool_spec"]["name"]].get("type") == "procedure"]
    views = [r["semantic_view"].split(".")[-1] for r in res.values() if "semantic_view" in r]
    return {"agent": AGENT_CRAW.relative_to(ROOT).as_posix(), "procedures": procs, "semantic_views": views,
            "tables": [t["id"] for t in _yaml(CONTRACT)["tables"]],
            "custom_dmfs": len(re.findall(r"^CREATE OR REPLACE DATA METRIC FUNCTION ", DMF.read_text(encoding="utf-8"),
                                          re.M)),
            "reference_questions": len(_yaml(QUESTIONS)["questions"])}


def data_fig3() -> dict:
    q = question("DIM_MIX")
    p, e = q["tool_parameters"], q["expected"]
    basis = next(b for b in _yaml(CONTRACT)["measure_bases"] if b["id"] == p["basis"])
    reason = e["reason_template"].format(basis=p["basis"], why=basis["not_comparable_reason"],
                                         allowed=", ".join(e["allowed_bases"]))
    turn = next(t for t in json.loads(GRADES_CRAW_S1.read_text(encoding="utf-8"))
                if t["config"] == "CR" and t["question_id"] == "DIM_MIX")
    contract = _yaml(CONTRACT)
    scope = next(x for x in contract["default_scopes"] if x["id"] == "SCOPE_ITEM_TYPE")
    return {"question": q["question"], "as_of_month": p["as_of_months"][0], "grain": p["grain"],
            "filters": p["filters"], "first_basis": p["basis"], "refusal": e["refusal"], "reason": reason,
            "second_basis": e["offer_instead"]["basis"], "value": e["offer_instead"]["value"],
            "answer_source": GRADES_CRAW_S1.relative_to(ROOT).as_posix(), "answer_config": turn["config"],
            "answer_label": turn["label"], "answer_verdict": turn["verdict"], "answer": turn["answer"],
            "answer_excerpt": re.split(r"(?<=[.!?])\s+", turn["answer"])[0],
            "units": [x["base_unit"] for x in contract["basis_model"]["dimensions"]],
            "scope": scope["included_values"]}


def data_fig4() -> dict:
    rows = readme_match(r"a view of ([\d,]+) rows over ([\d,]+) \(\+([\d.]+) percent\)")
    scans = readme_match(r"a one-quarter question scans ([\d.]+) times the snapshot table")
    members = readme_match(r"\*\*([\d,]+) of ([\d,]+) members equal\*\*")
    comp = readme_match(r"\*\*([\d.]+) s of compilation\*\* per procedure call")
    return {"view_rows": _num(rows.group(1)), "snapshot_rows": _num(rows.group(2)),
            "added_percent": float(rows.group(3)), "quarter_scan_times": float(scans.group(1)),
            "members_equal": _num(members.group(1)), "members_compared": _num(members.group(2)),
            "compilation_s": float(comp.group(1))}


RECORD = "Right figure, basis named, no unit on the coverage (rubric 3.2, of record)"     # README column headers
FIGURE_ONLY = "Right figure, basis named"


CREDITS = "Agent AI Credits per graded turn, billed, median"
GENERATED_TOOLS = ("C", "C-raw")                  # drawn in the accent colour


def half_up(text: str, places: str) -> str:
    """A README number rounded half up, as written (0.0195 is 0.020; a float would give 0.019)."""
    return str(Decimal(text).quantize(Decimal(places), rounding=ROUND_HALF_UP))


def stage1_rows() -> list[dict[str, str]]:
    return [r for r in readme_table(f"| Configuration | {RECORD}") if r["Configuration"] in PLAIN]


def data_fig5() -> dict:
    bars = [{"row": r["Configuration"], "name": PLAIN[r["Configuration"]], "figure_only": int(r[FIGURE_ONLY]),
             "credits": float(r[CREDITS]),
             "label": f"{int(r[FIGURE_ONLY])} of 24 · {half_up(r[CREDITS], '0.001')} credits per turn"}
            for r in stage1_rows()]
    return {"of": 24, "bars": sorted(bars, key=lambda b: (-b["figure_only"], b["credits"]))}


# Figure 6: rows in the article's order (layout); the raw-table row marked, its note in the footnote.
ROWS6 = ["C-raw", "C", "B2", "D", "D′", "A", "B1"]
MARKED6 = {"C-raw": "replayed the same questions after the campaign."}


def coded_refusals() -> set[str]:
    """Stage 1: only C returns coded refusals (stage1_results.md, section 3); C-raw, played after, has a refusal code
    of the contract in a recorded answer (eval/fixtures/grades_craw-s1.json)."""
    text = " ".join(STAGE1.read_text(encoding="utf-8").split())
    m = re.search(r"\*\*Codes:\*\* only ([\w-]+) returns coded refusals", text)
    if not m or "Every other configuration refuses in prose." not in text:
        raise SystemExit("stage1_results.md: the sentence on coded refusals changed")
    codes = [c["id"] for c in _yaml(CONTRACT)["refusal_codes"]]
    turns = json.loads(GRADES_CRAW_S1.read_text(encoding="utf-8"))
    return {m.group(1)} | ({"C-raw"} if any(c in t["answer"] for t in turns for c in codes) else set())


def data_fig6() -> dict:
    s1, coded = {r["Configuration"]: r for r in stage1_rows()}, coded_refusals()
    rows = [{"row": k, "name": PLAIN[k], "figure_only": int(s1[k][FIGURE_ONLY]), "record_s1": int(s1[k][RECORD]),
             "credits": float(s1[k][CREDITS]), "credits_shown": half_up(s1[k][CREDITS], "0.001"),
             "coded_refusal": k in coded, "highlight": k in GENERATED_TOOLS} for k in ROWS6]
    cols = [{"title": "Technique", "sub": ""}, {"title": FIGURE_ONLY, "sub": "of 24"},
            {"title": "Score of record", "sub": "of 24"}, {"title": "AI Credits per turn", "sub": "median"},
            {"title": "Refuses with a code", "sub": ""}]
    return {"of_s1": 24, "columns": cols, "rows": rows}


# ---------------------------------------------------------------- SVG helpers

_NARROW, _WIDE = set("il.,:;'!|ıfjtI()[] "), set("mwMWO@%")


def text_width(s: str, size: float, weight: int = 400) -> float:
    """An estimate of Space Grotesk's advance, enough to wrap lines; the PNGs are checked by eye."""
    w = 0.0
    for ch in s:
        w += 0.30 if ch in _NARROW else 0.86 if ch in _WIDE else 0.66 if ch.isupper() else 0.58
    return w * size * (1.05 if weight >= 600 else 1.0)


def wrap(s: str, size: float, width: float, weight: int = 400) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        nxt = f"{cur} {word}".strip()
        if cur and text_width(nxt, size, weight) > width:
            lines.append(cur)
            cur = word
        else:
            cur = nxt
    return lines + [cur] if cur else lines


def T(x, y, s, size=24, weight=400, fill=INK, anchor="start", spacing=None) -> str:
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x:g}" y="{y:g}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}"{ls}>{escape(s)}</text>')


def lines(x, y, rows, size=24, weight=400, fill=INK, lead=1.3, anchor="start") -> tuple[str, float]:
    out = [T(x, y + n * size * lead, r, size, weight, fill, anchor) for n, r in enumerate(rows)]
    return "".join(out), y + (len(rows) - 1) * size * lead


def R(x, y, w, h, fill=WHITE, stroke=None, sw=2, rx=14, dash=None) -> str:
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" fill="{fill}"{st}{da}/>'


def L(x1, y1, x2, y2, stroke=MUTED, sw=2, dash=None) -> str:
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="{stroke}" stroke-width="{sw}"{da}/>'


def arrow_down(x, y1, y2, color=VIOLET) -> str:
    return L(x, y1, x, y2 - 10, color, 3) + f'<path d="M{x - 9:g} {y2 - 12:g} L{x + 9:g} {y2 - 12:g} L{x:g} {y2:g} Z" fill="{color}"/>'


def arrow_right(x1, x2, y, color=VIOLET) -> str:
    return L(x1, y, x2 - 10, y, color, 3) + f'<path d="M{x2 - 12:g} {y - 9:g} L{x2 - 12:g} {y + 9:g} L{x2:g} {y:g} Z" fill="{color}"/>'


def arrow_up(x, y1, y2, color=VIOLET) -> str:
    """From y1 up to y2 (y2 < y1)."""
    return L(x, y1, x, y2 + 10, color, 3) + f'<path d="M{x - 9:g} {y2 + 12:g} L{x + 9:g} {y2 + 12:g} L{x:g} {y2:g} Z" fill="{color}"/>'


def block(x, y, w, h, title, body, fill=WHITE, stroke=None, ink=INK, body_ink=MUTED, tsize=20, bsize=16, sw=2,
          dash=None, note=None, note_ink=VIOLET) -> str:
    """A box with a centred title and a wrapped body (a string, or a list of paragraphs), and an optional smaller note,
    centred vertically."""
    rows = [r for para in ([body] if isinstance(body, str) else body or []) for r in wrap(para, bsize, w - 32)]
    nrows = wrap(note, bsize - 2, w - 32) if note else []
    lead_b, lead_n = bsize * 1.35, (bsize - 2) * 1.35
    total = tsize + (10 + len(rows) * lead_b if rows else 0) + (8 + len(nrows) * lead_n if nrows else 0)
    cx, ty = x + w / 2, y + (h - total) / 2 + tsize * 0.8
    out = [R(x, y, w, h, fill, stroke, sw, dash=dash), T(cx, ty, title, tsize, 700, ink, "middle")]
    yy = ty + 10 + bsize * 0.95
    for r in rows:
        out.append(T(cx, yy, r, bsize, 400, body_ink, "middle"))
        yy += lead_b
    yy += 8 - lead_b + lead_n if rows else 8
    for r in nrows:
        out.append(T(cx, yy, r, bsize - 2, 500, note_ink, "middle"))
        yy += lead_n
    return "".join(out)


def tag(x, y, s, fill=ORANGE) -> str:
    return T(x, y, s.upper(), 18, 700, fill, spacing="1.6")


def pill(x, y, kind) -> str:
    """A measured / inferred marker: filled for measured, outlined for inferred."""
    w = text_width(kind.upper(), 15, 700) + 22 + len(kind) * 1.2
    if kind == "measured":
        return R(x, y - 17, w, 24, INK, rx=12) + T(x + w / 2, y, kind.upper(), 15, 700, CREAM, "middle", "1.2")
    return R(x, y - 17, w, 24, WHITE, ORANGE, 2, rx=12, dash="4 3") + T(x + w / 2, y, kind.upper(), 15, 700, ORANGE,
                                                                       "middle", "1.2")


def svg(h: float, title: str, desc: str, body: str, data: dict, w: int = W) -> str:
    meta = escape(json.dumps(data, ensure_ascii=False, sort_keys=True))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h:g}" viewBox="0 0 {w} {h:g}" role="img" '
            f'aria-labelledby="t d">\n<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n'
            f'<metadata id="figure-data">{meta}</metadata>\n'
            f"<style>@font-face{{font-family:'Space Grotesk';font-weight:300 700;"
            f"src:url('../../assets/fonts/SpaceGrotesk-Variable.ttf')}}text{{font-family:{FAMILY}}}</style>\n"
            f'{R(0, 0, w, h, BG, rx=0)}\n{body}\n</svg>\n')


def footer(y, s) -> str:
    return lines(40, y, wrap(s, 18, W - 80), 18, 400, MUTED)[0]


# ---------------------------------------------------------------- figures

def fig1(d: dict) -> tuple[str, list[str]]:
    b = [T(40, 62, "One missing month, two answers", 36, 700),
         T(40, 100, f"{d['item']}, {d['country']}: stock per month", 24, 400, MUTED)]
    base, top, scale = 480, 210, 260 / max(m["stock"] or 0 for m in d["months"])
    for n, m in enumerate(d["months"]):
        x = 60 + n * 120
        if m["stock"] is None:
            b.append(R(x, base - 70, 80, 70, "none", ORANGE, 2.5, rx=6, dash="7 6"))
            b.append(lines(x + 40, base - 118, ["no", "snapshot"], 20, 700, ORANGE, 1.15, "middle")[0])
        else:
            h = m["stock"] * scale
            b.append(R(x, base - h, 80, h, LILAC, rx=6))
            b.append(T(x + 40, base - h - 12, f"{m['stock']:g}", 26, 700, INK, "middle"))
        b.append(T(x + 40, base + 34, month_name(m["month"]), 24, 400, INK, "middle"))
    b.append(L(44, base, 396, base, MUTED, 2))
    b.append(T(40, top - 40, "Stock on hand, kg equivalent", 20, 400, MUTED))
    x0 = 430
    b.append(T(x0, 160, f"Closing stock for {d['period']}", 24, 700))
    b.append(R(x0, 182, 330, 150, WHITE, ORANGE, 3))
    b.append(T(x0 + 22, 216, "Native semantic view", 22, 700))
    b.append(T(x0 + 22, 244, "NON ADDITIVE BY", 18, 500, MUTED, spacing="1"))
    b.append(T(x0 + 308, 290, f"{d['native_value']:g}", 56, 700, ORANGE, "end"))
    b.append(T(x0 + 22, 314, "May carried into the close", 18, 400, ORANGE))
    b.append(R(x0, 352, 330, 150, INK, rx=14))
    b.append(T(x0 + 22, 386, "The contract's rule", 22, 700, CREAM))
    b.append(T(x0 + 22, 414, "NO SNAPSHOT IN THE LAST MONTH", 15, 500, LILAC, spacing="1"))
    b.append(T(x0 + 308, 460, f"{d['contract_value']:g}", 56, 700, CREAM, "end"))
    b.append(T(x0 + 22, 484, "closes at 0", 18, 400, CREAM))
    b.append(footer(570, "The native view raises no error. Measured on the account; values from data/traps.yaml, "
                         "trap CS_LAST_MONTH_GAP."))
    shown = [f"{m['stock']:g}" for m in d["months"] if m["stock"] is not None] + [f"{d['native_value']:g}",
                                                                                  f"{d['contract_value']:g}"]
    return svg(620, "One missing month, two answers",
               f"{d['item']} in {d['country']}: {', '.join(f'''{month_name(m['month'])} {m['stock'] if m['stock'] is not None else 'no snapshot'}''' for m in d['months'])}. "
               f"Closing stock for {d['period']}: a native semantic view returns {d['native_value']:g}; the contract's "
               f"rule gives {d['contract_value']:g}.", "".join(b), d), shown

NUMBER = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine"}
PROC_PLAIN = {"STOCK_COVERAGE": "coverage", "CLOSING_STOCK": "closing stock"}     # labels, not data
GENERATED = ["two procedures", "semantic views, and the views they read", "data metric functions",
             "the agent's definition: instructions, tool descriptions", "reference questions"]


def fig2(d: dict) -> tuple[str, list[str]]:
    procs, tables = d["procedures"], NUMBER[len(d["tables"])]
    answer = "a figure, a warning or a coded refusal"
    b = [T(40, 66, "How it works", 40, 700),
         T(40, 104, "Declared once, compiled into files, deployed by a script, called by the agent.", 22, 400, MUTED)]
    top, ax, bx, cx, px = 196, 40, 270, 510, 770            # columns: declare, compile, deploy, Snowflake
    cw, pw = 200, 1240 - px
    # 1. declare
    b.append(tag(ax, 176, "1 · Declare"))
    b.append(block(ax, top, 190, 240, "Metric contract", "YAML, on a LinkML schema: grains, additivity, the gap "
                   "rule, refusals, quality", stroke=VIOLET, sw=3, tsize=21))
    b.append(lines(ax, top + 276, wrap("The only hand-written source of the generated files. Git is their system of "
                                       "record.", 15, 190), 15, 400, MUTED, 1.35)[0])
    # 2. compile: the compiler writes files, it calls nothing
    b.append(tag(bx, 176, "2 · Compile"))
    b.append(block(bx, top, cw, 150, "Compiler", "validates the contract, writes the files", INK, ink=CREAM,
                   body_ink=CREAM, tsize=24, note="no Snowflake call", note_ink=LILAC))
    b.append(arrow_right(ax + 190, bx, top + 75))
    fy, fh = top + 204, 268
    b.append(arrow_down(bx + cw / 2, top + 150, fy))
    b.append(T(bx + cw / 2 + 12, top + 182, "writes", 15, 400, MUTED))
    b.append(R(bx, fy, cw, fh, CREAM, None))
    b.append(T(bx + cw / 2, fy + 34, "Files in generated/", 19, 700, INK, "middle"))
    yy = fy + 66
    for item in GENERATED:
        rows = wrap(item, 15, cw - 32)
        b.append(T(bx + 16, yy, "·", 15, 700, ORANGE))
        b.append(lines(bx + 28, yy, rows, 15, 400, INK, 1.3)[0])
        yy += len(rows) * 19.5 + 12
    # the evaluation reads the reference questions; 3. a script deploys the rest
    # Session 17d: the repository's own harness (eval/), not Snowflake's agent evaluations.
    eh = 200
    b.append(tag(cx, 176, "Evaluation"))
    b.append(block(cx, top, cw, eh, "Evaluation harness", ["eval/ in the repository: asks the agent each reference "
                   "question and grades the answer.", "Not Snowflake's agent evaluations."], stroke=LILAC, tsize=18,
                   bsize=15))
    b.append(f'<polyline points="{bx + cw},{fy + 40} {cx + 100},{fy + 40} {cx + 100},{top + eh + 12}" fill="none" '
             f'stroke="{VIOLET}" stroke-width="3"/><path d="M{cx + 91} {top + eh + 12} L{cx + 109} {top + eh + 12} '
             f'L{cx + 100} {top + eh} Z" fill="{VIOLET}"/>')
    b.append(T(cx + 112, fy + 30, "read by", 15, 400, MUTED))
    dy0 = fy + 110
    b.append(tag(cx, dy0 - 20, "3 · Deploy"))
    b.append(block(cx, dy0, cw, 120, "Deploy script", "runs the generated files in Snowflake, as the project role",
                   stroke=VIOLET, tsize=18, bsize=15))
    b.append(arrow_right(bx + cw, cx, dy0 + 60))
    # 4. in Snowflake
    ix, iw = px + 20, pw - 40
    b.append(R(px, 150, pw, 630, PANEL, None, rx=22))
    b.append(tag(ix, 182, "4 · In Snowflake"))
    b.append(block(ix, top, iw, 120, "Cortex Agent", f"picks the parameters, gets back {answer}", INK, ink=CREAM,
                   body_ink=CREAM, tsize=24, bsize=17, note="its definition is generated", note_ink=LILAC))
    b.append(arrow_right(cx + cw, ix, top + 65))
    b.append(T(cx + cw + 10, top + 54, "asks", 15, 400, MUTED))
    b.append(arrow_right(cx + cw, px, dy0 + 60))
    b.append(T(cx + cw + 8, dy0 + 84, "creates", 15, 400, MUTED))
    ty, th, sw_ = top + 176, 150, 145
    pr_w = iw - sw_ - 15
    b.append(block(ix, ty, pr_w, th, f"{NUMBER[len(procs)]} procedures",
                   [f"{p}: {PROC_PLAIN[p]}" for p in procs] + ["compute and warn,", "or refuse with a code"],
                   stroke=ORANGE, sw=3, tsize=19, bsize=15))
    b.append(block(ix + pr_w + 15, ty, sw_, th, "Semantic view", "stock on hand and forecast, on the raw tables",
                   stroke=LILAC, tsize=17, bsize=15))
    cols = (ix + pr_w / 2, ix + pr_w + 15 + sw_ / 2)
    for x in cols:
        b.append(arrow_down(x, top + 120, ty))
    b.append(T(cols[0] + 12, top + 152, "calls", 15, 400, MUTED))
    tby = ty + th + 44
    for x in cols:
        b.append(arrow_down(x, ty + th, tby))
    b.append(T(cols[0] + 12, ty + th + 28, "read", 15, 400, MUTED))
    b.append(block(ix, tby, iw, 64, f"{tables} tables", "loaded from the published dataset, not generated",
                   "none", MUTED, sw=2, dash="7 6", tsize=18, bsize=15))
    dmy = tby + 108
    b.append(block(ix, dmy, iw, 90, "Data metric functions", "check the tables when a script runs them; in no "
                   "answer's path", stroke=LILAC, tsize=18, bsize=15))
    b.append(arrow_up(ix + iw / 2, dmy, tby + 64))
    b.append(T(ix + iw / 2 + 12, dmy - 16, "check", 15, 400, MUTED))
    b.append(T(40, 840, "The LLM picks parameters. It never computes the metric.", 30, 700))
    b.append(lines(40, 878, wrap(f"Not generated: the {tables.lower()} data tables, loaded from the published "
                                 "dataset, and the database, role and warehouse, created once by a setup script. "
                                 "Worked example: retail stock coverage.", 16, W2 - 80), 16, 400, MUTED, 1.35)[0])
    shown = procs + [answer, f"{tables} tables", "in no answer's path", "Files in generated/", "Deploy script",
                     "Evaluation harness", "Not Snowflake's agent evaluations.", "Not generated", "no Snowflake call"]
    return svg(930, "How it works",
               "Four steps. 1, declare: the metric contract, the only hand-written source. 2, compile: the compiler "
               "validates the contract and writes files into generated/ (" + ", ".join(GENERATED) + "); it makes no "
               "Snowflake call. 3, deploy: a script runs the generated files in Snowflake. 4, in Snowflake: the Cortex "
               f"Agent picks the parameters and calls {' and '.join(procs)} or the semantic view, which read the "
               f"{tables.lower()} data tables (loaded from the published dataset, not generated); it gets back {answer}. "
               "Data metric functions check the tables, in no answer's path. The evaluation harness, eval/ in the "
               "repository, asks the agent each reference question and grades the answer; it is not Snowflake's agent "
               "evaluations.", "".join(b), d, W2), shown


def fig3(d: dict) -> tuple[str, list[str]]:
    """Five blocks, one or two lines each: question, parameters, refusal, the computed figure, the answer's first
    sentence. The refusal's reason and the whole answer stay in the data and the description."""
    b = [T(40, 62, "One question, two calls", 36, 700),
         T(40, 100, "The agent picks the parameters. The generated", 24, 400, MUTED),
         T(40, 131, "procedure computes the number or refuses.", 24, 400, MUTED)]
    x, w, y, pad, gap = 40, 720, 168, 24, 50
    month = f"{month_name(d['as_of_month'])} {d['as_of_month'][:4]}"
    country = re.search(r" in (\w+) in ", d["question"]).group(1)
    units = " and ".join(d["units"])
    scope = " and ".join(v.lower() for v in d["scope"])
    figure = f"{d['value']:.1f} months, on {BASIS_PLAIN[d['second_basis']]}"
    summed = f"Stock and forecast of {country}'s {scope} items summed, coverage computed once."
    mixes = f"{country} mixes {units}, which can't be added."
    source = f"Source: graded turn of the raw-table version, {d['answer_source']}."

    def arrow():
        nonlocal y
        b.append(arrow_down(400, y + 4, y + gap - 16))
        y += gap

    # 1. the question
    b.append(tag(x, y + 6, "Question"))
    q_lines = wrap(f"“{d['question']}”", 26, w - 2 * pad, 500)
    h = 30 + len(q_lines) * 34
    b.append(R(x, y + 18, w, h, CREAM, None))
    b.append(lines(x + pad, y + 18 + 42, q_lines, 26, 500, INK, 1.3)[0])
    y += 18 + h
    arrow()
    # 2. the agent picks the parameters: one row of chips
    b.append(tag(x, y + 6, "Agent picks"))
    b.append(R(x, y + 18, w, 76, WHITE, VIOLET, 2.5))
    cx = x + pad
    for c in (month, country, BASIS_PLAIN[d["first_basis"]]):
        cw = text_width(c, 20, 500) + 32
        b.append(R(cx, y + 36, cw, 40, BG, None, rx=20))
        b.append(T(cx + 16, y + 63, c, 20, 500, INK))
        cx += cw + 14
    y += 94
    arrow()
    # 3. the procedure refuses
    b.append(tag(x, y + 6, "Procedure refuses"))
    b.append(R(x, y + 18, w, 96, INK, ORANGE, 3))
    b.append(T(x + pad, y + 58, d["refusal"], 26, 700, ORANGE, spacing="0.5"))
    b.append(T(x + pad, y + 94, mixes, 20, 400, CREAM))
    y += 114
    arrow()
    # 4. the agent retries on value, the procedure computes
    b.append(tag(x, y + 6, "Agent retries in euros → procedure computes"))
    b.append(R(x, y + 18, w, 104, INK, None))
    b.append(T(x + pad, y + 64, figure, 32, 700, LILAC))
    b.append(T(x + pad, y + 100, summed, 17, 400, CREAM))
    y += 122
    arrow()
    # 5. the answer's first sentence, verbatim
    b.append(tag(x, y + 6, "Answer (excerpt)"))
    a_lines = wrap(d["answer_excerpt"], 22, w - 2 * pad, 700)
    h = 32 + len(a_lines) * 30
    b.append(R(x, y + 18, w, h, WHITE, VIOLET, 2.5))
    b.append(lines(x + pad, y + 18 + 44, a_lines, 22, 700, INK, 1.36)[0])
    y += 18 + h
    b.append(T(40, y + 44, source, 16, 400, MUTED))
    shown = [month, country, BASIS_PLAIN[d["first_basis"]], d["refusal"], mixes, figure, summed, d["answer_excerpt"],
             source]
    return svg(y + 76, "One question, two calls",
               f"Question: {d['question']} The agent picks month {month}, filter {country}, basis "
               f"{BASIS_PLAIN[d['first_basis']]}. STOCK_COVERAGE refuses with {d['refusal']}: {d['reason']} The agent "
               f"calls again on {BASIS_PLAIN[d['second_basis']]}; the procedure sums the stock and forecast of "
               f"{country}'s {scope} items and computes the coverage once: {d['value']:.1f} months. The agent's answer "
               f"begins: {d['answer_excerpt']}", "".join(b), d), shown


def _grid(x, y, cells, read_cols, filled_color) -> str:
    """An illustration: 6 members x 6 months; cells: per row a string, '#' a raw row, '+' a filled row, '.' none."""
    out, cw, ch = [], 46, 22
    for c in read_cols:
        out.append(R(x + c * (cw + 6) - 4, y - 6, cw + 8, len(cells) * (ch + 6) + 6, "none", ORANGE, 2.5, rx=6))
    for r, row in enumerate(cells):
        for c, v in enumerate(row):
            cx, cy = x + c * (cw + 6), y + r * (ch + 6)
            if v == "#":
                out.append(R(cx, cy, cw, ch, LILAC, rx=4))
            elif v == "+":
                out.append(R(cx, cy, cw, ch, filled_color, rx=4))
            else:
                out.append(R(cx, cy, cw, ch, "none", LILAC, 1.5, rx=4, dash="3 3"))
    return "".join(out)


def fig4(d: dict) -> tuple[str, list[str]]:
    b = [T(40, 62, "Two ways to apply the closing rule", 36, 700),
         T(40, 100, "A member with no snapshot in the period's last", 24, 400, MUTED),
         T(40, 131, "month closes at 0. Where is that applied?", 24, 400, MUTED)]
    cols = [(40, "Gap-filled view", "recomputed at every query"), (420, "Procedure", "at question time")]
    for x, h1, h2 in cols:
        b.append(T(x, 192, h1, 26, 700))
        b.append(T(x, 222, h2, 22, 400, MUTED))
    raw = ["###...", "##.###", "######", "#####.", ".#####", "###.##"]
    filled = ["###+..", "##+###", "######", "#####+", ".#####", "###+##"]   # each span, first to last + 1
    b.append(_grid(46, 256, filled, range(6), INK))
    b.append(_grid(426, 256, raw, (3, 4, 5), INK))
    b.append(T(40, 448, "gaps filled in each member's span", 18, 400, MUTED))
    b.append(T(420, 448, "only the raw rows of the quarter", 18, 400, MUTED))
    pct = f"{d['added_percent']:g}%"
    left = [("measured", [f"{pct} more rows: {d['view_rows']:,.0f}", f"for {d['snapshot_rows']:,.0f}"]),
            ("measured", ["A quarter question scans", f"the table {d['quarter_scan_times']:.1f} times"]),
            ("inferred", ["Grows with each member's span,", "whatever period is asked"])]
    right = [("measured", ["Same closing stock on", f"{d['members_equal']:,.0f} of {d['members_compared']:,.0f} members"]),
             ("measured", [f"About {d['compilation_s']:.0f} s of compilation", f"per call ({d['compilation_s']:g} s)"]),
             ("inferred", ["Grows with the rows of", "the period asked"])]
    for x, facts in ((40, left), (420, right)):
        y = 500
        for kind, rows in facts:
            b.append(pill(x, y, kind))
            b.append(lines(x, y + 36, rows, 22, 500, INK, 1.3)[0])
            y += 122
    b.append(L(400, 176, 400, 840, LILAC, 2))
    b.append(R(40, 872, 22, 14, LILAC, rx=3) + T(70, 886, "raw row", 18, 400, MUTED))
    b.append(R(160, 872, 22, 14, INK, rx=3) + T(190, 886, "row added by the fill", 18, 400, MUTED))
    b.append(R(392, 868, 22, 22, "none", ORANGE, 2.5, rx=4) + T(422, 886, "read by a quarter question", 18, 400, MUTED))
    b.append(footer(926, "Grids: an illustration, not to scale. Measured on the published dataset; growth is a "
                         "reading of the SQL, no larger dataset was run."))
    shown = [pct, f"{d['view_rows']:,.0f}", f"{d['snapshot_rows']:,.0f}", f"{d['quarter_scan_times']:.1f} times",
             f"{d['members_equal']:,.0f} of {d['members_compared']:,.0f}", f"({d['compilation_s']:g} s)"]
    return svg(980, "Two ways to apply the closing rule",
               f"Left, a gap-filled view recomputed at every query: {pct} more rows ({d['view_rows']:,.0f} for "
               f"{d['snapshot_rows']:,.0f}), a quarter question scans the table {d['quarter_scan_times']:.1f} times "
               f"(measured); it grows with each member's span (inferred). Right, a procedure at question time: the "
               f"same closing stock on {d['members_equal']:,.0f} of {d['members_compared']:,.0f} members, about "
               f"{d['compilation_s']:.0f} s of compilation per call (measured); it grows with the rows of the period "
               f"asked (inferred).", "".join(b), d), shown


def fig5(d: dict) -> tuple[str, list[str]]:
    """One bar per configuration, right figure, basis named, on a track of 24; its label gives the billed credits."""
    b = [T(40, 62, "More right answers for fewer credits", 36, 700),
         T(40, 100, "Right figure, basis named, out of 24 questions", 24, 400, MUTED)]
    lsize = 17
    room = max(text_width(x["label"], lsize, 600) for x in d["bars"]) + 16
    x0, full, y, pitch = 40, W - 80 - room, 150, 78
    for bar in d["bars"]:
        color = ORANGE if bar["row"] in GENERATED_TOOLS else VIOLET
        w = bar["figure_only"] / d["of"] * full
        b.append(T(x0, y + 20, bar["name"], 20, 700, INK))
        b.append(R(x0, y + 32, full, 28, PANEL, rx=6))
        b.append(f'<rect data-row="{bar["row"]}" data-series="bar" x="{x0}" y="{y + 32}" width="{w:.1f}" height="28" '
                 f'rx="6" fill="{color}"/>')
        b.append(T(x0 + full + 14, y + 53, bar["label"], lsize, 700 if bar["row"] in GENERATED_TOOLS else 400,
                   INK))
        y += pitch
    b.append(footer(y + 24, "One run per question: counts, not rates. The raw-table version replayed the same "
                            "questions after the campaign. Credits: the agent's AI Credits, billed, median per turn; "
                            "the warehouse is billed apart."))
    shown = [x["label"] for x in d["bars"]]
    return svg(y + 110, "More right answers for fewer credits",
               "Right figure, basis named, out of 24 questions, one bar per configuration, best first: " + "; ".join(
                   f"{x['name']}: {x['label']}" for x in d["bars"]) + ". The two with generated tools are highlighted.",
               "".join(b), d), shown


def fig6(d: dict) -> tuple[str, list[str]]:
    """The article's results table, stage 1: one row per configuration, the two with generated tools highlighted."""
    widths, anchors = [350, 225, 170, 180, 195], ["start", "middle", "middle", "middle", "middle"]
    b = [T(40, 58, "Seven ways to give an agent the same metric", 32, 700),
         T(40, 92, f"The same {d['of_s1']} questions, the same model", 20, 400, MUTED)]
    pad, top, hh = 16, 122, 70
    xs = [40]
    for w in widths[:-1]:
        xs.append(xs[-1] + w)
    b.append(R(40, top, W6 - 80, hh, INK, rx=8))
    for c, x, w, anchor in zip(d["columns"], xs, widths, anchors):
        tx = x + pad if anchor == "start" else x + w / 2
        b.append(T(tx, top + (31 if c["sub"] else 42), c["title"], 17, 700, CREAM, anchor))
        if c["sub"]:
            b.append(T(tx, top + 54, c["sub"], 15, 400, LILAC, anchor))
    y, rh = top + hh, 52
    shown = [c["title"] for c in d["columns"]]
    for r in d["rows"]:
        cells = [r["name"] + ("*" if r["row"] in MARKED6 else ""), str(r["figure_only"]), str(r["record_s1"]),
                 r["credits_shown"], "yes" if r["coded_refusal"] else "no, in prose"]
        shown += cells
        if r["highlight"]:
            b.append(f'<g data-highlight="{r["row"]}">{R(40, y, W6 - 80, rh, CREAM, rx=0)}'
                     f'{R(40, y, 6, rh, ORANGE, rx=0)}</g>')
        for n, (c, x, w, anchor) in enumerate(zip(cells, xs, widths, anchors)):
            tx = x + pad + 6 if anchor == "start" else x + w / 2
            b.append(T(tx, y + 33, c, 19, 700 if n == 0 or r["highlight"] else 400, INK, anchor))
        y += rh
        b.append(L(40, y, W6 - 40, y, LILAC, 1))
    marks = " ".join(f"* {v}" for v in MARKED6.values())
    note = [f"{marks} One run per question: counts, not rates.",
            "Score of record: right figure, basis named, and no unit on the coverage (rubric 3.2). Credits: the agent's, "
            "billed; the warehouse is billed apart."]
    for n, line in enumerate(note):
        b.append(T(40, y + 40 + n * 24, line, 16, 400, MUTED).replace("<text ", '<text data-footnote="1" ', 1))
    shown.append(f"* {MARKED6['C-raw']}")
    h = y + 40 + 24 + 32
    return svg(h, "Seven ways to give an agent the same metric",
               f"Results table, stage 1, the same {d['of_s1']} questions. Columns: " +
               ", ".join(f"{c['title']} ({c['sub']})" if c["sub"] else c["title"] for c in d["columns"]) +
               ". Rows: " + "; ".join(
                   f"{r['name']}: {r['figure_only']}, {r['record_s1']}, {r['credits_shown']} credits, "
                   f"{'refuses with a code' if r['coded_refusal'] else 'refuses in prose'}" for r in d["rows"]) +
               ". The two with generated tools are highlighted. " + " ".join(note), "".join(b), d, W6), shown


# ---------------------------------------------------------------- captions

def caption(name: str, title: str, text: str, alt: str, sources: list[str]) -> str:
    src = "\n".join(f"- {s}" for s in sources)
    return f"# Figure {name}: {title}\n\n**Caption.** {text}\n\n**Alt text.** {alt}\n\n## Sources\n\n{src}\n"


def captions(f1, f2, f3, f4, f5, f6) -> dict[str, str]:
    procs = " and ".join(f"{p} ({PROC_PLAIN[p]})" for p in f2["procedures"])
    months = ", ".join(f"{month_name(m['month'])} {m['stock'] if m['stock'] is not None else 'none'}" for m in f1["months"])
    pts = "; ".join(f"{p['name']} = README row {p['row']}" for p in f5["bars"])
    return {
        "01-closing-stock-trap": caption(
            "1", "One missing month, two answers",
            f"The {f1['item'].lower()} has no snapshot in {f1['country']} in June. Asked for its {f1['period']} "
            f"closing stock, a native semantic view with NON ADDITIVE BY returns {f1['native_value']:g}, May's stock "
            f"carried into the close, and raises no error. The contract's rule gives {f1['contract_value']:g}.",
            f"Bar chart of stock per month ({months}); beside it, the quarter's closing stock: "
            f"{f1['native_value']:g} from the native view, {f1['contract_value']:g} under the contract's rule.",
            ["Stock per month: `data/traps.yaml`, hero_items, " + f1["sku"] + ", stock_by_k (k = -2, -1; no row "
             "at k = 0) [documented].",
             "Months: k counted from the analysis month, as_of of `generated/reference_questions.yaml`; "
             "item, country and quarter from the question of CS_LAST_MONTH_GAP there [documented].",
             f"Native value {f1['native_value']:g}: `data/traps.yaml`, closing_stock, CS_LAST_MONTH_GAP, "
             "wrong.last_known_value; measured on the account in session 6 (`snowflake/probe_closing/results.md`, "
             "session 6 summary; README section 3) [measured].",
             f"Contract value {f1['contract_value']:g}: the same trap, expected; the rule is "
             "`contract/stock_coverage.yaml`, invariant INV_CLOSING_LAST_PERIOD [documented]."]),
        "02-how-it-works": caption(
            "2", "How it works",
            "A metric contract is the only hand-written source. The compiler validates it and writes files into "
            "generated/: two procedures, semantic views, data metric functions, the agent's definition and the "
            "reference questions. A script deploys those files in Snowflake; the compiler calls nothing. The agent "
            "picks the parameters and gets back a figure, a warning or a coded refusal; it never computes the "
            "metric. Data metric functions check the tables and are in no answer's path. The evaluation harness "
            "in eval/ asks the agent each reference question and grades the answer; it is not Snowflake's agent "
            "evaluations. The data tables are loaded from the published dataset, not generated.",
            "Diagram in four steps. Declare: the metric contract. Compile: the compiler writes files into generated/ "
            "(" + ", ".join(GENERATED) + "). Deploy: a script runs them in Snowflake. In Snowflake: the Cortex Agent "
            f"calls {' and '.join(f2['procedures'])} or the semantic view, which read the "
            f"{NUMBER[len(f2['tables'])].lower()} data tables, not generated; data metric functions check those "
            "tables apart from any answer. Beside it, the evaluation harness (eval/ in the repository, not "
            "Snowflake's agent evaluations) asks the agent each reference question and grades the answer.",
            [f"Procedures and semantic view, as the agent binds them: `{f2['agent']}`, tool_resources: {procs}, "
             f"{', '.join(f2['semantic_views'])} [documented].",
             "What the compiler writes: README section 2, the table of generated files; each generator's docstring "
             "in `compiler/` (gen_procedure, gen_closing_procedure, gen_closing_sv, gen_native_sv, gen_craw, gen_dmf, "
             "gen_agent, gen_questions). No module of `compiler/` imports the Snowflake connector [documented].",
             "The agent's definition is generated: `generated/agent_c.yaml` and `generated/agent_c_raw.yaml` "
             "(instructions, tool descriptions, procedure bindings) [documented].",
             f"Data metric functions: `generated/dmf.sql`, {f2['custom_dmfs']} custom functions and ad hoc checks; "
             "nothing attached to a table, no schedule (`compiler/gen_dmf.py`); run by "
             "`snowflake/phase2_dmf/run_dmf.py`. No procedure calls them: the procedures run their own in-call "
             "checks [documented].",
             f"Reference questions: `generated/reference_questions.yaml`, {f2['reference_questions']} questions, the "
             "evaluation's question set (`compiler/gen_questions.py`) [documented].",
             "Evaluation harness: `eval/campaign.py` asks the agents over Snowflake's REST API through "
             "`snowflake/probe_b/mount/run_call.py`; `eval/grade.py` grades each answer with the deterministic rubric "
             "`eval/rubric.yaml` against the expected values of `generated/reference_questions.yaml`. No Snowflake "
             "agent evaluation is used [documented].",
             "Deployment: the scripts `snowflake/phase3_procedure/deploy.py` (SQL files), "
             "`snowflake/phase4_others/deploy_sv.py` (semantic view YAML), `snowflake/phase4_agent_c/deploy_agent.py` "
             "(agent C) read the generated files [documented].",
             f"Not generated: the {len(f2['tables'])} tables of `contract/stock_coverage.yaml`, loaded by "
             "`data/load_snowflake.py` from the published dataset; the database, role and warehouse, "
             "`snowflake/00_setup.sql` [documented].",
             "Drawn by `tools/make_figures.py` since session 17c; `assets/docs/how-it-works.png`, the README's "
             "diagram, is a copy of this PNG."]),
        "03-one-question": caption(
            "3", "One question, two calls",
            "Asked for France's stock coverage, the agent with generated tools on raw tables picks the parameters and "
            "calls the generated procedure. The procedure refuses the kg or L equivalent basis with "
            f"{f3['refusal']}: France mixes {' and '.join(f3['units'])}. The agent calls again on value; the procedure "
            "sums the stock and forecast of France's standard items and computes the coverage once, "
            f"{f3['value']:.1f} months, which the agent relays. Every number comes from the procedure.",
            f"Five blocks: the question; the agent picks June 2026, France, kg or L equivalent; the procedure refuses "
            f"with {f3['refusal']}, France mixes {' and '.join(f3['units'])}; the agent retries on value and the "
            f"procedure computes {f3['value']:.1f} months; the answer's first sentence, quoted: "
            f"{f3['answer_excerpt']}",
            ["Question and parameters (month, grain, filter, basis): `generated/reference_questions.yaml`, DIM_MIX, "
             "question and tool_parameters [documented].",
             "Refusal code, bases allowed and the second call's basis: the same entry, expected.refusal, "
             "allowed_bases, offer_instead.basis [documented].",
             "Refusal reason: expected.reason_template filled with the QTY_EQ not_comparable_reason of "
             "`contract/stock_coverage.yaml` [documented]. The turn's two calls (QTY_EQ, then VALUE), its refusal code "
             "and this reason text are those of summary_cr_dim_mix_craw_s1_r1.json in ../linkml-metrics-runs/campaign/ "
             "(session 13) [measured, run folder, not published]; the same procedure returned the same text and calls "
             "in the recorded turn c_dim_mix of `eval/fixtures/recorded_turns.jsonl` (session 8) [measured].",
             f"Value {f3['value']:.2f}: offer_instead.value, recomputed from the dataset by two oracle references "
             "[measured, the offline suite].",
             "Summed, then computed once: `generated/stock_coverage_procedure_sql.sql`, the coverage statement "
             "(CTEs stock and fc sum stock and monthly forecast at the grain asked; the coverage is computed on those "
             "sums); the default scope keeps STANDARD items only, BULK stock is left out unless item_type is filtered: "
             "`contract/stock_coverage.yaml`, default_scopes, SCOPE_ITEM_TYPE [documented].",
             f"Answer: `{f3['answer_source']}`, {f3['answer_label']}, verdict {f3['answer_verdict']} (rubric 3.2); "
             "the first sentence quoted verbatim, the whole answer in figures.json [measured]."]),
        "04-closing-rule-two-ways": caption(
            "4", "Two ways to apply the closing rule",
            f"Left, a gap-filled view fills the missing months of each member's span, then is recomputed over the whole table "
            f"at every query: {f4['added_percent']:g}% more rows, and a quarter question scans the table "
            f"{f4['quarter_scan_times']:.1f} times. Right, a procedure applies the rule at question time to the raw rows "
            f"of the period only: the same closing stock on {f4['members_equal']:,.0f} of "
            f"{f4['members_compared']:,.0f} members, for about {f4['compilation_s']:.0f} s of compilation per call. "
            "How each grows at scale is inferred, not measured.",
            "Two columns. Left: a grid with the gaps of each member's span filled and all of it read. Right: a grid with gaps and only the "
            "quarter's columns read. Under each, the measured figures and the inferred growth.",
            [f"Rows {f4['view_rows']:,.0f} for {f4['snapshot_rows']:,.0f} (+{f4['added_percent']:g} percent) and the "
             f"quarter scan ({f4['quarter_scan_times']:.1f} times): README section 3, the closing-stock trade-off "
             "table; `snowflake/session13_craw/results.md`, section 1b [measured].",
             f"{f4['members_equal']:,.0f} of {f4['members_compared']:,.0f} members equal and "
             f"{f4['compilation_s']:g} s of compilation: README section 3; `snowflake/session13_craw/results.md`, "
             "section 3 [measured].",
             "Growth of each: README section 3, the Growth row, a reading of the SQL [inferred].",
             "The grids are an illustration, not data."]),
        "05-trade-off": caption(
            "5", "More right answers for fewer credits",
            "Right figure, basis named, out of 24 questions, for seven ways to give an agent the same metric, best "
            "first, then cheapest first. Each label adds the agent's billed AI Credits per turn (median). The two "
            "versions with generated tools are in orange. One run per question, so the counts are counts, not rates. "
            "The raw-table version replayed the same questions after the campaign. The warehouse is billed apart.",
            "Seven horizontal bars, out of 24: " + "; ".join(f"{p['name']}, {p['label']}" for p in f5["bars"]) + ".",
            [f"README section 4, stage 1 table: columns {FIGURE_ONLY} and {CREDITS}; C-raw row included [measured].",
             "Credits rounded half up to three decimals from the README's four (0.0195 is 0.020).",
             "Underlying records: `snowflake/phase5_campaign/stage1_results.md`, sections 8 and 9; "
             "`snowflake/session13_craw/results.md`, sections 4 and 5 [measured].",
             "The score: `eval/grade.py`, grade_turn (verdict_figure_only), basis_named [documented].",
             f"Plain names: {pts}."]),
        "06-results-table": caption(
            "6", "Seven ways to give an agent the same metric",
            "The article's results table, stage 1: the same 24 questions, the same model. Per configuration: right "
            "figure, basis named; the score of record, which also forbids a unit on the coverage; the agent's billed "
            "AI Credits per turn (median); whether it refuses with a code. The two versions with generated tools are "
            "highlighted; the raw-table version replayed the same questions after the campaign. One run per question: "
            "counts, not rates. Stage 2, latency and the data each configuration needs prepared are in the README.",
            "Table of seven rows and five columns. " + "; ".join(
                f"{r['name']}: {r['figure_only']} of 24, score of record {r['record_s1']} of 24, "
                f"{r['credits_shown']} credits, refuses " + ("with a code" if r["coded_refusal"] else "in prose")
                for r in f6["rows"]) + ".",
            [f"Scores and credits: README section 4, stage 1 table, columns {FIGURE_ONLY}, {RECORD} and {CREDITS} "
             "[measured]. Credits rounded half up to three decimals from the README's four.",
             "Refuses with a code: `snowflake/phase5_campaign/stage1_results.md`, section 3 (only C returns coded "
             "refusals; every other configuration refuses in prose); C-raw: a refusal code of "
             "`contract/stock_coverage.yaml` in its recorded answers, `eval/fixtures/grades_craw-s1.json` (T7_R1, "
             "MASTER_DATA_FANOUT) [measured].",
             "Replayed after the campaign: README section 4 (C-raw, built in session 13, played C's 24 questions in "
             "C's order; it is not in the 144).",
             "Plain names: " + "; ".join(f"{r['name']} = README row {r['row']}" for r in f6["rows"]) + "."]),
    }


# ---------------------------------------------------------------- PNG

def chrome() -> str | None:
    for c in (os.environ.get("CHROME"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser")):
        if c and Path(c).exists():
            return c
    return None


def render_png(exe: str, inner: str, w: int, h: int, out: Path, width: int = PNG_WIDTH) -> None:
    """Screenshot of an HTML page holding the figure at w x h CSS pixels, at the scale that makes it width px wide."""
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "figure.html"
        page.write_text(
            "<!doctype html><html><head><meta charset='utf-8'><style>"
            f"@font-face{{font-family:'Space Grotesk';font-weight:300 700;src:url('{FONT.as_uri()}')}}"
            "html,body{margin:0;padding:0;overflow:hidden}svg,img{display:block}</style></head>"
            f"<body>{inner}</body></html>", encoding="utf-8")
        subprocess.run([exe, "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                        f"--force-device-scale-factor={width / w:g}", f"--window-size={w},{h}",
                        "--virtual-time-budget=3000", f"--screenshot={out}", page.as_uri()],
                       check=True, capture_output=True)
    pw, ph = struct.unpack(">II", out.read_bytes()[16:24])
    if pw != width:
        raise SystemExit(f"{out.name}: {pw} px wide, expected {width}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = {"01-closing-stock-trap": data_fig1(), "02-how-it-works": data_fig2(), "03-one-question": data_fig3(),
            "04-closing-rule-two-ways": data_fig4(), "05-trade-off": data_fig5(), "06-results-table": data_fig6()}
    builders = {"01-closing-stock-trap": fig1, "02-how-it-works": fig2, "03-one-question": fig3,
                "04-closing-rule-two-ways": fig4, "05-trade-off": fig5, "06-results-table": fig6}
    shown, svgs = {}, {}
    for name, fn in builders.items():
        svgs[name], shown[name] = fn(data[name])
        (OUT / f"{name}.svg").write_text(svgs[name], encoding="utf-8")
    for name, text in captions(*data.values()).items():
        (OUT / f"{name}.md").write_text(text, encoding="utf-8")
    manifest = {n: {"data": d, "shown": shown[n]} for n, d in data.items()}
    (OUT / "figures.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                                      encoding="utf-8")
    exe = chrome()
    if not exe:
        print("no Chrome found (set CHROME): SVGs, captions and figures.json written, PNGs left as they are")
        return
    for name, s in svgs.items():
        w, h = (int(float(v)) for v in re.search(r'width="([\d.]+)" height="([\d.]+)"', s).groups())
        inner = s.replace("url('../../assets/fonts/SpaceGrotesk-Variable.ttf')", f"url('{FONT.as_uri()}')")
        render_png(exe, inner, w, h, OUT / f"{name}.png", PNG_WIDTHS.get(name, PNG_WIDTH))
    shutil.copyfile(OUT / "02-how-it-works.png", DIAGRAM)
    print(f"wrote {len(builders)} SVGs, {len(builders)} PNGs, {len(builders)} captions and figures.json to {OUT.relative_to(ROOT)}; "
          f"copied figure 2 to {DIAGRAM.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
