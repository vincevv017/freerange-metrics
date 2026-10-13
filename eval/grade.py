"""
Grade agent turns with eval/rubric.yaml against generated/reference_questions.yaml (session 8, decision 2).

    python eval/grade.py --turns <turns.jsonl> [--out <grades.json>]

A turn is one JSON object:
    {"config": "A" | "B1" | "B2" | "C" | "D" | "DP", "question_id": "<id of reference_questions.yaml>",
     "answer": "<final answer text>",
     "tool_uses": [{"type": ..., "name": ..., "input": {...}}],        # as run_call.py summarises them
     "tool_results": [{"name": ..., "status": ..., "content": "..."}],
     "sql": ["<statement>", ...]}                                       # executed SQL read from the trace, if any
turns_from_log() builds these from run_call.py's summary_<label>.json and trace_<label>.json files.

Each grade carries a verdict (correct, wrong, manual) and the criteria behind it: numeric, analysis_month_named,
no_aggregated_coverage, refusal, t5_outcome, routing, warnings (recorded, not in the verdict). The script reads text,
tool calls and SQL only; it never calls Snowflake and never recomputes an expected value.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUBRIC = yaml.safe_load((ROOT / "eval" / "rubric.yaml").read_text())
QUESTIONS = {q["id"]: q for q in yaml.safe_load((ROOT / "generated" / "reference_questions.yaml").read_text())["questions"]}
DECISIONS = {d["request_id"]: d for d in
             (yaml.safe_load((ROOT / "eval" / "manual_decisions.yaml").read_text()) or {}).get("decisions", [])}
TOL = Decimal("0.05")
HORIZON = yaml.safe_load((ROOT / "contract" / "stock_coverage.yaml").read_text())["metrics"][0]["horizon_periods"]
# Rubric 3.3 is the current version; 3.2 stays selectable so that both scores can be reported (owner, 2026-10-07).
RUBRICS = ("3.2", "3.3")
# Rubric 3.3: the product names of DIM_ITEM that carry a pack size. DIM_ITEM.sku_name in the published dataset holds the hero
# items of data/traps.yaml; every other item is named "<family> <n>", with no unit (tests/test_rubric_33.py).
PRODUCT_NAMES = tuple(h["name"] for h in yaml.safe_load((ROOT / "data" / "traps.yaml").read_text())["hero_items"]
                      if re.search(r"\d\s*(?:kg|L)\b", h["name"]))
MONTHS = ("january|february|march|april|may|june|july|august|september|october|november|december|"
          "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec")
SCALES = {"thousand": 1_000, "k": 1_000, "million": 1_000_000, "m": 1_000_000, "mn": 1_000_000,
          "billion": 1_000_000_000, "bn": 1_000_000_000}
COUNTRY_NAMES = {"FR": "france", "BE": "belgium", "NL": "netherlands", "GB": "united kingdom", "DE": "germany",
                 "CH": "switzerland", "PL": "poland", "IT": "italy", "ES": "spain", "SE": "sweden"}
COUNTRY_ALIASES = {"GB": ("uk", "great britain", "britain")}

NUM = re.compile(
    r"(?<![\w.\-+])(?P<int>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<dec>\d+))?"
    r"(?:\s?(?P<scale>thousand|million|billion|mn|bn|k|m)\b)?(?P<after>\s?-?\s?\w*)", re.I)


@dataclass(frozen=True)
class Num:
    value: Decimal          # in plain units (scale applied)
    decimals: int
    scale: int
    start: int
    after: str


def numbers(text: str) -> list[Num]:
    """Every number of a text, without dates (years next to a month name or a quarter, ISO dates), codes (SKU-H11,
    Q2, t+1) or list markers."""
    out = []
    for m in NUM.finditer(text):
        raw = m.group("int").replace(",", "")
        dec = m.group("dec") or ""
        s, e = m.start(), m.end("dec") if dec else m.end("int")
        before = text[max(0, s - 12):s].lower()
        nxt = text[e:e + 3]
        if re.search(r"(\d-|-)$", before) and re.match(r"\d", raw):       # inside 2026-06-01 or a code
            if re.search(r"\d{4}-$|\d{4}-\d{2}-$", before) or re.search(r"[a-z]-$", before):
                continue
        if re.match(r"-\d", nxt):                                          # 2026-06
            continue
        if len(raw) == 4 and not dec and 1900 <= int(raw) <= 2100 and (
                re.search(rf"({MONTHS})\.?\s*$", before) or re.search(r"q[1-4]\s*$", before)
                or re.search(rf"^\s*[-/]", nxt)):
            continue
        if re.search(rf"({MONTHS})\.?\s+$", before) and int(raw) <= 31 and not dec:   # June 1
            continue
        scale_word = (m.group("scale") or "").lower()
        scale = SCALES.get(scale_word, 1)
        if scale_word in ("m",) and re.match(r"\s?m\s*(onth|o\b)", text[e:e + 8], re.I):
            scale = 1                                                      # "2 m" never a month abbreviation here
        value = Decimal(f"{raw}.{dec}" if dec else raw) * scale
        out.append(Num(value, len(dec), scale, s, (m.group("after") or "").lower()))
    return out


def month_numbers(text: str) -> list[Num]:
    """Numbers written as a number of months of coverage: '2.8 months', '0 months', '50.0 months'. Not the horizon's
    month count ('24-month', 'the next 24 months', 'the following 24 months'). Rubric 3.3 (finding 100): nor a count
    of elapsed forecast months, a whole number after "after" ('920 kg after 8 months'); "in month 9" is never one,
    since its number does not precede "months"."""
    out = []
    for n in numbers(text):
        tail = text[n.start:n.start + 40].lower()
        head = text[max(0, n.start - 30):n.start].lower()
        m = re.match(r"[\d,.]+\s+months?\b", tail)
        year = n.decimals == 0 and n.scale == 1 and 1900 <= n.value <= 2100      # "the 2026 months available"
        horizon = (n.value == HORIZON and n.decimals == 0 and not re.search(
            r"(coverage (?:is|of)|covers?|lasts?|last for)\s+(?:about |around |approximately |only )?$", head))
        elapsed = _CTX["rubric"] != "3.2" and n.decimals == 0 and re.search(r"\bafter\s+$", head)
        if m and not re.match(r"[\d,.]+-month", tail) and not re.search(r"\b(next|following)\s+$", head) \
                and not horizon and not year and not elapsed:
            out.append(n)
    return out


def matches(n: Num, expected: float) -> bool:
    e = Decimal(str(expected))
    if abs(n.value - e) <= TOL:
        return True
    q = Decimal(1).scaleb(-n.decimals)
    return (e / n.scale).quantize(q, rounding=ROUND_HALF_UP) == (n.value / n.scale).quantize(q, rounding=ROUND_HALF_UP)


# The turn being graded: its readable SQL and tool parameters, read by the indistinguishable-precision guard.
_CTX: dict = {"sql": [], "uses": [], "item_objects": ("DIM_ITEM",), "rubric": RUBRIC["version"]}


def set_rubric(version: str) -> None:
    """The rubric version the criteria apply (grade_turn sets it for each turn)."""
    if version not in RUBRICS:
        raise SystemExit(f"rubric {version} is not gradable; versions: {', '.join(RUBRICS)}")
    _CTX["rubric"] = version


def readable_statements() -> list[str]:
    """The turn's executed SQL, plus any SQL text a tool call carried (a skill script's extraction queries)."""
    out = list(_CTX["sql"])
    for u in _CTX["uses"]:
        out += [s for s in _strings(u.get("input", {})) if re.search(r"\bSELECT\b", s, re.I)]
    return out


def _strings(x) -> list[str]:
    if isinstance(x, str):
        return [x]
    if isinstance(x, dict):
        return [s for v in x.values() for s in _strings(v)]
    if isinstance(x, list):
        return [s for v in x for s in _strings(v)]
    return []


def _fanout(s: str) -> bool:
    objs = "|".join(re.escape(o) for o in _CTX["item_objects"])
    return bool(re.search(rf"\b({objs})\b", s, re.I)) and not re.search(
        r"\bDISTINCT\b|\bQUALIFY\b|\bROW_NUMBER\b|\bANY_VALUE\b", s, re.I)


SIGNATURES = {   # wrong value name pattern -> (signature on one SQL statement, signature on procedure parameters)
    r"item_join_fanout|naive_join": (_fanout, lambda p: False),
    r"raw_units_summed": (lambda s: bool(re.search(r"_qty_raw\b", s, re.I)),
                          lambda p: str(p.get("basis", p.get("unit_variant", ""))).upper() in ("RAW", "NATIVE", "PACKS")),
    r"default_scope_applied": (lambda s: bool(re.search(r"item_type\s*(=|IN\b)\s*\(?\s*'STANDARD'", s, re.I)),
                               lambda p: "item_type" not in str(p.get("filters", ""))),
}


# Session 13: the parameters of C-raw's closing_stock call, read by the same guard as stock_coverage's (a C-raw-only
# adaptation of rubric numeric.indistinguishable_precision, not a new rule). It reads one row per item (a REFUSE_IF_USED fan-out check
# refuses the call otherwise) and applies no default scope, so neither wrong method can come from it; the NATIVE basis
# sums raw units.
CLOSING_SIGNATURES = {
    r"item_join_fanout|naive_join": lambda p: False,
    r"raw_units_summed": lambda p: str(p.get("basis", "")).upper() in ("RAW", "NATIVE", "PACKS"),
    r"default_scope_applied": lambda p: False,
}


def guard(names: list[str]) -> tuple[str, str]:
    """A declared wrong value indistinguishable from the expected value at the answer's precision: decide on the SQL
    or the tool parameters of the turn (rubric, numeric.indistinguishable_precision)."""
    stmts = readable_statements()
    params = [u.get("input", {}) for u in _CTX["uses"] if u.get("name") == "stock_coverage"]
    closing = [u.get("input", {}) for u in _CTX["uses"] if u.get("name") == "closing_stock"]     # C-raw only
    if closing and not stmts:
        for n in names:
            sig = next((v for k, v in CLOSING_SIGNATURES.items() if re.search(k, n)), None)
            if sig is None:
                return "manual", f"{n} indistinguishable at the answer's precision and has no method signature"
            if any(sig(p) for p in closing):
                return "fail", f"{n}: indistinguishable by the number, method signature found in the parameters"
        return "pass", f"{sorted(names)} indistinguishable by the number; no method signature in the closing_stock parameters"
    if not stmts and not params:
        return "manual", f"{sorted(names)} indistinguishable at the answer's precision and no readable SQL or parameters"
    for n in names:
        sig = next((v for k, v in SIGNATURES.items() if re.search(k, n)), None)
        if sig is None:
            return "manual", f"{n} indistinguishable at the answer's precision and has no method signature"
        if any(sig[0](s) for s in stmts) or any(sig[1](p) for p in params):
            return "fail", f"{n}: indistinguishable by the number, method signature found in the SQL or parameters"
    return "pass", f"{sorted(names)} indistinguishable by the number; no method signature in the readable SQL or parameters"


def decide(cands: list[Num], expected: float, wrong: dict) -> tuple[str, str]:
    hit = [n for n in cands if matches(n, expected)]
    nums = {k: v for k, v in wrong.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    bad = {k: v for k, v in nums.items() if any(matches(n, v) and not matches(n, expected) for n in cands)}
    blind = [k for k, v in nums.items() if any(matches(n, v) and matches(n, expected) for n in hit)
             and not math.isclose(v, expected, abs_tol=1e-9)]
    # Session 8c: the same value also written at a precision that tells it from every wrong value (a table at full
    # precision beside a rounded sentence) decides on the number; the guard is for an answer that never does.
    if any(not any(matches(n, v) for v in nums.values()) for n in hit):
        blind = []
    if hit and not bad and blind:
        state, why = guard(blind)
        return state, f"expected {expected} given; " + why
    if hit and not bad:
        return "pass", f"expected {expected} given"
    if bad and not hit:
        return "fail", f"wrong value given: {sorted(bad)}"
    if hit and bad:
        return "manual", f"expected {expected} and wrong value(s) {sorted(bad)} both given"
    if not cands:
        return "manual", "no candidate number"
    return "fail", f"no candidate matches {expected}: {[str(n.value) for n in cands]}"


# ------------------------------------------------------------------------------------------------ criteria

ZERO_WORDS = re.compile(r"\b(zero|no stock|out of stock|nothing in stock|stock(?:ed)? out|stockout)\b", re.I)
NULL_WORDS = re.compile(r"\b(no demand|no forecast|undefined|not defined|cannot be (?:computed|calculated)|"
                        r"can't be (?:computed|calculated)|no coverage figure|not meaningful|NO_DEMAND)\b", re.I)
AS_OF_WORDS = re.compile(r"\b(june\s+2026|jun\.?\s+2026|2026-06(?:-01)?)\b", re.I)
REFUSAL_WORDS = re.compile(r"\b(can(?:no|')t|cannot|not possible|refus|do(?:es)? not add up|don't add up|"
                           r"not additive|meaningless|isn't meaningful|is not meaningful|unable|won't)\w*", re.I)
CLARIFY_WORDS = re.compile(r"(which (?:analysis )?month|what month|which month|specify (?:a|the) month|"
                           r"choose a month|pick a month|\?)", re.I)
FANOUT_WORDS = re.compile(r"(lifecycle|duplicat|conflict|more than one|two (?:rows|statuses|records)|"
                          r"recorded twice|fan(?:ned)?[- ]?out|master data)", re.I)
PACK_WORDS = re.compile(r"(pack|raw unit|different sizes|do not add up|don't add up|not additive)", re.I)
QTY_EQ_WORDS = re.compile(r"(equivalent|QTY_EQ|kg|litre|liter|\bL\b)", re.I)


def coverage_value(q: dict, text: str) -> tuple[str, str]:
    e = q["expected"]
    cands = month_numbers(text)
    if e["value"] is None:
        if cands:
            return "fail", f"a coverage number where none exists: {[str(n.value) for n in cands]}"
        return ("pass", "no number, reason given") if NULL_WORDS.search(text) else ("manual", "no number, no reason found")
    if e["value"] == 0 and not cands and ZERO_WORDS.search(text):
        return "pass", "zero stated in words"
    return decide(cands, e["value"], e.get("wrong_values", {}))


def aggregation(q: dict, text: str, sql: list[str]) -> tuple[str, str]:
    for s in sql:
        if re.search(r"\b(SUM|AVG)\s*\(\s*[\w.\"]*coverage", s, re.I):
            return "fail", "SQL adds or averages a coverage column across rows"
    e = q["expected"]
    cands = month_numbers(text)
    agg = {k: v for k, v in e.get("wrong_values", {}).items() if re.search(r"sum_of|average|weighted", k)}
    for k, v in agg.items():
        if any(matches(n, v) and not matches(n, e.get("value") or -1e9) for n in cands):
            return "fail", f"aggregated coverage given: {k}"
    if "rows" in e and e["rows"]:
        vals = [r["value"] for r in e["rows"] if r["value"] is not None]
        for name, v in (("sum of the rows", sum(vals)), ("mean of the rows", sum(vals) / len(vals))):
            if any(matches(n, v) for n in cands):
                return "fail", f"drill total equal to the {name}"
    return "pass", "no added or averaged coverage"


def line_numbers(text: str, code: str) -> list[Num]:
    names = [COUNTRY_NAMES[code]] + list(COUNTRY_ALIASES.get(code, ()))
    out = []
    for line in text.splitlines():
        low = line.lower()
        if re.search(rf"(?<![A-Za-z]){code}(?![A-Za-z])", line) or any(
                re.search(rf"(?<![a-z]){re.escape(n)}(?![a-z])", low) for n in names):
            out += numbers(line)
    return out


def rows_value(q: dict, text: str, key: str = "country_code") -> tuple[str, str]:
    e = q["expected"]
    fails, manual = [], []
    for r in e["rows"]:
        code = r[key]
        cands = line_numbers(text, code)
        if code == "SE" and q["id"] == "G2":
            wrong = {"item_join_fanout": e["wrong_values"]["item_join_fanout"]["SE"]}
        else:
            wrong = {k: w[code] for k, w in e.get("wrong_values", {}).items() if isinstance(w, dict) and code in w}
        if r["value"] is None:
            continue
        v, why = decide(cands, r["value"], wrong)
        if v == "fail":
            fails.append(f"{code}: {why}")
        elif v == "manual":
            manual.append(f"{code}: {why}")
    if fails:
        return "fail", "; ".join(fails)
    if manual:
        return "manual", "; ".join(manual)
    return "pass", f"{len(e['rows'])} rows match"


def refusal(q: dict, text: str, results: list[dict]) -> tuple[str, str]:
    code = q["expected"]["refusal"]
    cands = month_numbers(text)
    if code == "AS_OF_MISSING":
        if cands:
            return "fail", f"a coverage number for a period: {[str(n.value) for n in cands]}"
        if CLARIFY_WORDS.search(text) or REFUSAL_WORDS.search(text):
            return "pass", "no number; asks for the month or refuses with a reason"
        return "manual", "no number, no question or reason found"
    if code == "MASTER_DATA_FANOUT":
        if cands:
            return "fail", f"numbers given at a fanned-out grain: {[str(n.value) for n in cands]}"
        return ("pass", "no number, fan-out reason given") if FANOUT_WORDS.search(text) else (
            "manual", "no number, reason not recognised")
    return "manual", f"refusal {code} graded by its own criterion"


def t5_outcome(q: dict, text: str, results: list[dict]) -> tuple[str, str]:
    e = q["expected"]
    raw = e.get("wrong_values", {}).get("raw_units_summed")
    cands = month_numbers(text)
    if any(re.search(r"UNIT_RAW_NOT_ADDITIVE|BASIS_NOT_COMPARABLE", r.get("content") or "") for r in results) and not any(
            raw is not None and matches(n, raw) for n in cands):
        return "pass", "procedure_refusal"
    if raw is not None and any(matches(n, raw) for n in cands):
        return "fail", "raw_pack_number"
    alt = e.get("offer_instead", {}).get("value")
    if not cands and PACK_WORDS.search(text):
        return "pass", "model_refusal_without_number"
    if alt is not None and any(matches(n, alt) for n in cands) and PACK_WORDS.search(text) and QTY_EQ_WORDS.search(text):
        return "pass", "model_refusal_with_qty_eq_answer"
    return "manual", "t5 outcome not classified"


# ------------------------------------------------------------------------------------------------ rubric v3 (session 8c-0)

BASIS_WORDS = {   # the basis an answer names: what stock and forecast were measured on
    "QTY_EQ": re.compile(r"(\bkg\b|(?<![\w-])L(?![\w-])|\blit(?:re|er)s?\b|quantity[- ]equivalent|QTY_EQ|\bweight\b|"
                         r"\bvolume\b|\bkilo)", re.I),
    "VALUE": re.compile(r"(\bEUR\b|\beuros?\b|€|\bvalue\b|\bvalued\b)", re.I),
    "NATIVE": re.compile(r"(\bcases?\b|\bpacks?\b|own unit|CASE_10|PACK_\d+|native)", re.I),
}
UNIT_CLAIM = re.compile(r"\bin\s+(?:QTY_EQ|kg\b|kilo\w*|(?-i:L)(?![\w-])|lit(?:re|er)s?\b|EUR\b|euros?\b|packs?\b|"
                        r"quantity[- ]equivalent|(?:kg|L)[- ]equivalent)", re.I)
ABOUT_COVERAGE = re.compile(r"(coverage|\bmonths?\b|^\W*(?:this|these|the figures?|all (?:the )?figures|every figure|"
                            r"figures)\b)", re.I)
QUALIFIED = re.compile(r"(measured|\bbasis\b|stock and (?:the )?(?:demand )?forecast|stock and demand|numerator|"
                       r"denominator|in months|(?:can't|cannot|can not|never|not)\b[^.]{0,30}\bin\s|"
                       # rubric 3.1: naming the basis of the stock or the forecast is what v3 asks
                       r"\b(?:stock|forecast|demand)\s+(?:is |are |was |were )?(?:measured |given |expressed )?in\s)", re.I)
# rubric 3.1: a number of the coverage itself given in a unit ("coverage of 2.8 kg")
COVERAGE_NUMBER_UNIT = re.compile(r"\bcoverage\b[^.]{0,40}?\b\d[\d.,]*\s*(?:kg\b|(?-i:L)\b|lit\w*|EUR\b|QTY_EQ)", re.I)
MONTH_UNIT = re.compile(r"\bmonths?\s+(?:of|in)\s+(?:cases?|packs?|kg\b|(?-i:L)\b|lit\w*|EUR\b|euros?|QTY_EQ)", re.I)
SWITCH_WORDS = re.compile(r"(kg and (?:L|lit)|lit\w* and kg|weight and volume|mass and volume|different dimensions|"
                          r"\bmix|not comparable|cannot be (?:added|summed|compared)|can't be (?:added|summed)|"
                          r"do(?:es)? not add up|don't add up|BASIS_NOT_COMPARABLE)", re.I)
SKU = re.compile(r"\bSKU-[A-Z0-9]+\b")


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def expected_basis(q: dict) -> str:
    e = q["expected"]
    if e.get("offer_instead", {}).get("basis"):
        return e["offer_instead"]["basis"]           # T5, DIM_MIX: a figure is given on the basis offered instead
    return e.get("names_basis") or q["tool_parameters"]["basis"]


def _product_pattern(name: str) -> re.Pattern:
    stem = re.sub(r"\s*\([^)]*\)\s*$", "", name)                    # "(discontinued)" is not written by the answers
    words = [re.escape(w) for w in stem.split()]
    body = r"\s+".join(words[:-1]) + r"\s*" + words[-1]                 # "1 kg" or "1kg"
    return re.compile(rf"(?<![\w-]){body}(?![\w-])(?:\s*\([^)]*\))?", re.I)


PRODUCT_PATTERNS = [(_product_pattern(n), re.sub(r"\s*\d[\d.]*\s*(?:kg|L)\b.*$", "", n)) for n in PRODUCT_NAMES]


def unit_text(text: str) -> str:
    """The text the unit half of basis_wording reads. Rubric 3.3: a product name of DIM_ITEM is read without its pack
    size ("Oat cereal bar 1 kg" as "Oat cereal bar"), so the size never reads as a unit of the coverage."""
    if _CTX["rubric"] == "3.2":
        return text
    for pat, short in PRODUCT_PATTERNS:
        text = pat.sub(short, text)
    return text


def basis_wording(q: dict, text: str) -> tuple[str, str]:
    """Rubric v3: coverage is always in months; the answer names the basis stock and forecast were measured on, and
    never gives coverage in a unit ('coverage in kg', 'the figures are in QTY_EQ'). Rubric 3.3: read on unit_text."""
    for s in sentences(text):
        u = unit_text(s)
        if MONTH_UNIT.search(u) or COVERAGE_NUMBER_UNIT.search(u) or (
                ABOUT_COVERAGE.search(u) and UNIT_CLAIM.search(u) and not QUALIFIED.search(u)):
            return "fail", f"coverage given in a unit: {s.strip()[:120]!r}"
    return basis_named(q, text)


def basis_named(q: dict, text: str) -> tuple[str, str]:
    """The naming half of basis_wording, alone: the figure-only score keeps it (owner, 2026-10-07)."""
    b = expected_basis(q)
    if not BASIS_WORDS[b].search(text):
        return "fail", f"basis {b} not named"
    return "pass", f"months, basis {b} named"


def basis_switch(q: dict, text: str, results: list[dict]) -> tuple[str, str]:
    """DIM_MIX (question (b)): QTY_EQ is refused; the agent may answer on VALUE if it says that the basis changed and
    why. kg and L added (the wrong value) is wrong."""
    e = q["expected"]
    cands = month_numbers(text)
    wrong = e.get("wrong_values", {}).get("kg_and_l_added")
    alt = e["offer_instead"]["value"]
    if wrong is not None and any(matches(n, wrong) and not matches(n, alt) for n in cands):
        return "fail", "kg and L added (kg_and_l_added)"
    if any(matches(n, alt) for n in cands):
        if not BASIS_WORDS["VALUE"].search(text):
            return "fail", "value coverage given without naming the value basis"
        if not SWITCH_WORDS.search(text):
            return "fail", "basis changed to value without saying why"
        return "pass", "value coverage, basis change explained"
    if cands:
        return "fail", f"no candidate matches {alt}: {[str(n.value) for n in cands]}"
    refused = any("BASIS_NOT_COMPARABLE" in (r.get("content") or "") for r in results) or SWITCH_WORDS.search(text)
    if refused and BASIS_WORDS["VALUE"].search(text):
        return "pass", "refusal relayed, value offered"
    return "manual", "no number; refusal or value offer not recognised"


def selection_rows(q: dict, text: str) -> tuple[str, str]:
    """Questions (c) and (d): every kept product with its coverage on its line; no other product given as at risk;
    the members set apart named (already out, no demand)."""
    e = q["expected"]
    want = {r["sku_code"]: r["value"] for r in e["rows"]}
    apart = {m[0] for ms in e.get("set_apart", {}).values() for m in ms}
    fails = []
    for code, v in want.items():
        lines = [ln for ln in text.splitlines() if re.search(rf"(?<![\w-]){re.escape(code)}(?![\w-])", ln)]
        cands = [n for ln in lines for n in numbers(ln)]
        if not any(matches(n, v) for n in cands):
            fails.append(f"{code}: {v} not found")
    extra = sorted(set(SKU.findall(text)) - set(want) - apart)
    if extra:
        fails.append(f"products not in the expected list: {extra}")
    missing = sorted(a for a in apart if a not in text)
    if missing:
        fails.append(f"members set apart not named: {missing}")
    if not re.search(r"\bmonths?\b", text, re.I):
        fails.append("no months")
    return ("fail", "; ".join(fails)) if fails else ("pass", f"{len(want)} rows, {len(apart)} set apart")


def selection_summary(q: dict, text: str) -> tuple[str, str]:
    """Question (e): the count of kept pairs and the stock value they tie up (71.0 million EUR rounded is right);
    the listing of the 28 pairs is not graded."""
    s = q["expected"]["summary"]
    nums = numbers(text)
    count = any(n.value == s["count"] and n.decimals == 0 for n in nums)
    amount = s["stock"][0]["amount"]
    value = any(matches(n, amount) for n in nums if n.value >= 1_000_000)
    if count and value:
        return "pass", f"{s['count']} pairs, {amount} EUR"
    return "fail", ("count missing; " if not count else "") + ("stock value missing" if not value else "")


# ------------------------------------------------------------------------------------------------ rubric 3.2 (session 8c)

LOWEST_WORDS = re.compile(r"\b(lowest|least|shortest|smallest|first to (?:stock|run) out|runs? out first)\b", re.I)


def apart_codes(e: dict) -> set[str]:
    out = set()
    for ms in (e.get("set_apart") or {}).values():
        out |= {m[0] for m in ms}
    for c in e.get("calls", []):
        for ms in (c.get("apart") or {}).values():
            out |= {m[0] for m in ms}
    return out


def item_set(q: dict, text: str) -> tuple[str, str]:
    """Held-out Q1, Q3, Q4: the exact set of products the answer gives (text and tables). Members set apart (no stock,
    no demand) may be named. Q1: an intersection of the codes two calls returned is allowed (not a computation on
    coverages); two lists given without their intersection name products outside the set and are wrong."""
    e = q["expected"]
    want = set(e["items"])
    got = set(SKU.findall(text)) - (apart_codes(e) - want)
    missing, extra = sorted(want - got), sorted(got - want)
    if missing or extra:
        return "fail", "; ".join(x for x in (f"missing {missing}" if missing else "",
                                            f"extra {extra}" if extra else "") if x)
    return "pass", f"exact set of {len(want)} products"


def lowest_member(q: dict, text: str) -> tuple[str, str]:
    """Held-out Q2: the lowest member (PL) with its coverage (2.16 months) on its line; another member given as the
    lowest (CH, the naive mean ratio) is wrong."""
    e = q["expected"]
    row = e["rows"][0]
    code = row["country_code"]
    names = {code, COUNTRY_NAMES[code]}
    for s in sentences(text):
        low = s.lower()
        if LOWEST_WORDS.search(s) and not any(re.search(rf"(?<![A-Za-z]){re.escape(n)}(?![A-Za-z])", s if n == code
                                                        else low) for n in names):
            others = [c for c, n in COUNTRY_NAMES.items() if c != code and (
                re.search(rf"(?<![A-Za-z]){c}(?![A-Za-z])", s) or re.search(rf"(?<![a-z]){n}(?![a-z])", low))]
            if others:
                return "fail", f"{others} given as the lowest: {s.strip()[:120]!r}"
    cands = [n for ln in text.splitlines() for n in month_numbers(ln) if
             re.search(rf"(?<![A-Za-z]){code}(?![A-Za-z])", ln) or COUNTRY_NAMES[code] in ln.lower()]
    if not cands:
        return "fail", f"{code} not given with a coverage in months"
    return decide(cands, row["coverage_months"], {})


# ------------------------------------------------------------------------------------------------ stage 2 (session 9b)
# N1 and N2 ask a closing stock and a coverage in one question. Each half is graded on its own figures with the rules of
# rubric 3.2: the coverage half as a coverage question (numbers written as months), the closing-stock half as a closing
# stock question on the other numbers of the answer (a coverage in months is never a closing-stock candidate). N2 gives
# one closing stock per month of Q2 2026, read on the lines that name the month, as the rows of G2 are read on the
# lines that name the country; the months added or averaged anywhere is wrong.

CLOSING_WORDS = re.compile(r"(clos|end of (?:q[1-4]|the quarter|the period|june|the month)|quarter)", re.I)
MONTH_LINE = {   # a line that names the month of a row: its name (May capitalised, never the verb) or its ISO form
    "01": r"(?i:\bjan(?:uary)?\b)", "02": r"(?i:\bfeb(?:ruary)?\b)", "03": r"(?i:\bmar(?:ch)?\b)",
    "04": r"(?i:\bapr(?:il)?\b)", "05": r"\bMay\b", "06": r"(?i:\bjune?\b)", "07": r"(?i:\bjuly?\b)",
    "08": r"(?i:\baug(?:ust)?\b)", "09": r"(?i:\bsept?(?:ember)?\b)", "10": r"(?i:\boct(?:ober)?\b)",
    "11": r"(?i:\bnov(?:ember)?\b)", "12": r"(?i:\bdec(?:ember)?\b)"}


def closing_candidates(text: str) -> list[Num]:
    months = {n.start for n in month_numbers(text)}
    return [n for n in numbers(text) if n.start not in months]


def closing_half(q: dict, text: str) -> tuple[str, str]:
    e = q["expected"]["closing_stock"]
    cands = closing_candidates(text)
    if "rows" in e:
        return closing_months(e, text, cands)
    if e["value"] == 0 and not any(matches(n, 0) for n in cands) and any(
            ZERO_WORDS.search(s) and CLOSING_WORDS.search(s) and not month_numbers(s) for s in sentences(text)):
        cands = cands + [Num(Decimal(0), 0, 1, -1, "")]          # zero stated in words about the closing stock
    return decide(cands, e["value"], e.get("wrong_values", {}))


def closing_months(e: dict, text: str, cands: list[Num]) -> tuple[str, str]:
    for k, v in e.get("added_over_months", {}).items():
        if any(matches(n, v) for n in cands):
            return "fail", f"the months added or averaged: {k}"
    fails, manual = [], []
    for r in e["rows"]:
        y, m = r["month"][:4], r["month"][5:7]
        pat = re.compile(rf"{MONTH_LINE[m]}|{y}-{m}")
        got = [n for ln in text.splitlines() if pat.search(ln) for n in closing_candidates(ln)]
        wrong = {k: w[r["month"]] for k, w in e.get("wrong_values", {}).items() if r["month"] in w}
        v, why = decide(got, r["value"], wrong)
        if v == "fail":
            fails.append(f"{r['month']}: {why}")
        elif v == "manual":
            manual.append(f"{r['month']}: {why}")
    if fails:
        return "fail", "; ".join(fails)
    if manual:
        return "manual", "; ".join(manual)
    return "pass", f"{len(e['rows'])} months match"


def coverage_half(q: dict) -> dict:
    """The coverage half of N1 or N2 as a coverage question of its own."""
    return {**q, "metric": "stock_coverage", "expected": {**q["expected"]["coverage"], "names_as_of": True,
                                                          "names_basis": q["expected"]["names_basis"]}}


# ------------------------------------------------------------------------------------------------ governance (session 8c-0, step 7b)

DERIVE_WORDS = re.compile(r"\b(range|ranges|runs? from|lowest|highest|minimum|maximum|min|max|on average|"
                          r"average(?! (?:non-zero )?(?:monthly )?(?:forecast|demand))|"
                          r"median|ranked|ranking|top \d+|bottom \d+)\b", re.I)
MEMBER_WORDS = re.compile(r"\b(items?|products?|SKUs?|members?|countries|families|pairs)\b", re.I)


def rows_commented(q: dict, text: str) -> tuple[bool, str]:
    """Governance flag ROWS_COMMENTED, outside correctness: the answer cites the coverage of members the question did
    not ask for, or derives a figure across members (range, lowest, highest, average, rank). A list question asks for
    its members; only a derived figure counts there."""
    if q["metric"] != "stock_coverage":
        return False, "n/a"
    e = q["expected"]
    is_list = "rows" in e or "summary" in e or "items" in e
    asked = {v for vs in q.get("tool_parameters", {}).get("filters", {}).values() for v in vs}
    asked |= set(SKU.findall(q.get("question", "")))
    for s in sentences(text):
        if not month_numbers(s):
            continue
        codes = set(SKU.findall(s))
        if DERIVE_WORDS.search(s) and (MEMBER_WORDS.search(s) or codes):
            return True, f"figure derived across members: {s.strip()[:120]!r}"
        if not is_list and codes - asked:
            return True, f"coverage of members not asked {sorted(codes - asked)}: {s.strip()[:120]!r}"
    return False, "only the asked figures"


FRESHNESS_LINE = re.compile(r"^\W*data freshness\W*:\s*(?P<v>.+?)\s*$", re.I | re.M)
LATEST_MONTH = re.compile(r"\b(june\s+2026|jun\.?\s+2026|2026-06(?:-01)?)\b", re.I)   # the dataset's LATEST


def freshness_stated(text: str) -> dict:
    """Governance measure FRESHNESS_STATED (charter version 10), never a grade: the answer ends with a line
    'Data freshness: <the latest month with stock data>' (present), equal to the dataset's LATEST, June 2026 (latest)."""
    m = FRESHNESS_LINE.findall(text)
    if not m:
        return {"present": False, "latest": False, "value": None}
    return {"present": True, "latest": bool(LATEST_MONTH.search(m[-1])), "value": m[-1]}


def family(use: dict, sv_tools: set[str]) -> str | None:
    t, n = (use.get("type") or "").lower(), (use.get("name") or "")
    if n in ("data_to_chart", "chart_instructions") or "chart" in t:
        return None
    if n == "stock_coverage":
        return "procedure"
    if n == "closing_stock":
        return "closing_procedure"      # session 13: C-raw's closing-stock procedure; no other configuration has it
    if "cortex_analyst" in t or "system_execute_sql" in t or n in sv_tools:
        return "semantic_view"
    if t in ("skill", "server_skill") or n in ("skill", "server_skill"):
        return None          # rubric v2: loading a skill's instructions reads no data and is not a tool
    if n in ("bash", "code_execution") or "code_execution" in t or t == "bash" \
            or "linkml-coverage" in json.dumps(use.get("input", {})):
        return "skill"
    if "sql" in t or "sql" in n.lower():
        return "sandbox_sql"
    return f"other:{t or n}"


# Session 9b (owner, 2026-10-07), stage 2 only, for the questions added in stage 2 (N1, N2): route "both". Agent C is
# expected to call the procedure and the closing-stock view (its semantic view tool) each at least once in the turn;
# for B2 the expected route stays the view. A turn that answers both halves from one tool is graded on its figures and
# fails this criterion. The routing table of rubric 3.2 is unchanged; no other configuration plays these questions.
ROUTE_BOTH = {"C": ("procedure", "semantic_view"), "B2": ("semantic_view",), "CR": ("procedure", "closing_procedure")}

# Session 13 (owner, 2026-10-08): configuration C-raw (CR), graded under rubric 3.2 and 3.3 unchanged. Its routing
# entry lives here, not in eval/rubric.yaml (whose table keeps the six configurations): closing stock to closing_stock,
# coverage to stock_coverage, the rest to its semantic view; a turn routed to the view for closing stock fails (H-CR-4).
CR_ROUTING = {"coverage": "procedure", "closing_stock": "closing_procedure", "semantic_view": "semantic_view",
              "clarify": "none"}
CR_ALLOWED = {"clarify": {"procedure", "closing_procedure"}}     # as C: a call refused for the missing month
CR_FORBIDDEN = {"closing_stock": {"procedure", "skill"}, "semantic_view": {"procedure", "skill", "closing_procedure"}}


def cr_route(q: dict) -> str:
    """C-raw's route: the rubric's route, with the questions on closing stock or stock on hand split from the view."""
    route = q["expected_route"]
    if route == "semantic_view" and q.get("metric") in ("closing_stock", "stock_on_hand"):
        return "closing_stock"
    return route
ROUTE_GROUP = {"coverage": "procedure", "semantic_view": "view only", "both": "both", "clarify": "no tool"}


def route_group(q: dict) -> str:
    """The group a question is reported in (session 9b): the route agent C is expected to take."""
    return ROUTE_GROUP[q["expected_route"]]


def routing_both(config: str, used: set[str]) -> tuple[str, str]:
    if config not in ROUTE_BOTH:
        raise SystemExit(f"route both is defined for {sorted(ROUTE_BOTH)} only, not {config}")
    need = set(ROUTE_BOTH[config])
    forbidden = {"skill", "procedure"} - need
    missing = sorted(need - used)
    if missing:
        return "fail", f"expected {sorted(need)} each at least once, missing {missing} (used {sorted(used) or 'no tool'})"
    if used & forbidden:
        return "fail", f"forbidden for this route: {sorted(used & forbidden)}"
    return "pass", " and ".join(sorted(need)) + (f" (with {sorted(used - need)})" if used - need else "")


def routing(q: dict, config: str, uses: list[dict], results: list[dict], sv_tools: set[str]) -> tuple[str, str]:
    r = RUBRIC["criteria"]["routing"]
    route = q["expected_route"]
    if route == "both":
        return routing_both(config, {f for f in (family(u, sv_tools) for u in uses) if f})
    if config == "CR":
        route = cr_route(q)
        want, allowed, forbidden = CR_ROUTING[route], CR_ALLOWED.get(route, set()), CR_FORBIDDEN.get(route, set())
        used = {f for f in (family(u, sv_tools) for u in uses) if f}
        if want == "none":
            if not used:
                return "pass", "no tool call"
            if used <= allowed and all("AS_OF_MISSING" in (x.get("content") or "") for x in results):
                return "pass", f"{sorted(used)} refused for the missing month"
            return "fail", f"tool(s) used where none was expected: {sorted(used)}"
        if want not in used:
            return "fail", f"expected {want}, used {sorted(used) or 'no tool'}"
        if used & forbidden:
            return "fail", f"forbidden for this route: {sorted(used & forbidden)}"
        return "pass", f"{want}" + (f" (with {sorted(used - {want})})" if used - {want} else "")
    want = r["expected"][route][config]
    used = {f for f in (family(u, sv_tools) for u in uses) if f}
    allowed = set(r.get("allowed_with", {}).get(route, {}).get(config, []))
    forbidden = set(r.get("forbidden", {}).get(route, []))
    if want == "none":
        extra = used - allowed
        if not used:
            return "pass", "no tool call"
        if not extra and all("AS_OF_MISSING" in (x.get("content") or "") for x in results):
            return "pass", f"{sorted(used)} refused for the missing month"
        return "fail", f"tool(s) used where none was expected: {sorted(used)}"
    if want not in used:
        return "fail", f"expected {want}, used {sorted(used) or 'no tool'}"
    if used & forbidden:
        return "fail", f"forbidden for this route: {sorted(used & forbidden)}"
    return "pass", f"{want}" + (f" (with {sorted(used - {want})})" if used - {want} else "")


def warnings(q: dict, text: str) -> str:
    w = q["expected"].get("warnings") or {c: None for c in q["expected"].get("warnings_codes", [])}
    if not w:
        return "n/a"
    got = 0
    low = text.lower()
    for code, n in w.items():
        if code == "FORECAST_GAPS_FILLED":
            ok = re.search(r"(missing|no forecast|gap|absent|counted as (?:0|zero)|filled)", low) and (
                n is None or any(matches(x, n) for x in numbers(text)))
        elif code == "DEFAULT_SCOPE_EXCLUDED":
            ok = "bulk" in low and (n is None or any(matches(x, n) for x in numbers(text)))
        elif code == "MASTER_DATA_DUPLICATES":
            ok = re.search(r"duplicat|several rows|two rows|recorded twice", low)
        else:
            ok = False
        got += bool(ok)
    return "yes" if got == len(w) else ("partial" if got else "no")


COVERAGE_COLUMN = re.compile(r"coverage|months", re.I)


def table_text(tables: list[dict]) -> str:
    """Session 8c, decision 4: the tables of the answer are part of it. Each table is read as text after the answer's
    text: its title, its header, then one line per row with its cells separated by '|'. A number in a column whose name
    says coverage or months is written with 'months', so that the coverage criteria read it as a coverage; any other
    cell is a plain number (closing stock, value, forecast)."""
    out = []
    for t in tables or []:
        cols = [str(c or "") for c in t.get("columns") or []]
        out.append(str(t.get("title") or ""))
        out.append("| " + " | ".join(cols) + " |")
        for row in t.get("rows") or []:
            cells = []
            for i, v in enumerate(row):
                s = "" if v is None else str(v)
                if i < len(cols) and COVERAGE_COLUMN.search(cols[i]) and re.fullmatch(r"-?\d+(?:\.\d+)?", s):
                    s += " months"
                cells.append(s)
            out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def grade_turn(turn: dict, sv_tools: set[str] | None = None, item_objects: tuple = ("DIM_ITEM",),
               rubric: str | None = None) -> dict:
    """item_objects: the item tables or views that hold two rows for the T7 item (DIM_ITEM, and a projection that keeps
    lifecycle_status), read by the fan-out signature. turn["tables"] (session 8c): the answer's tables, graded with
    its text. rubric: the version applied, the current one (eval/rubric.yaml) unless given."""
    set_rubric(rubric or RUBRIC["version"])
    q = QUESTIONS[turn["question_id"]]
    text = turn.get("answer") or ""
    if turn.get("tables"):
        text = text.rstrip() + "\n\n" + table_text(turn["tables"])
    uses, results, sql = turn.get("tool_uses", []), turn.get("tool_results", []), turn.get("sql", [])
    _CTX.update(sql=sql, uses=uses, item_objects=tuple(item_objects))
    sv_tools = sv_tools or set()
    e = q["expected"]
    crit: dict[str, tuple[str, str]] = {}
    if q["metric"] == "closing_stock_and_coverage":                    # session 9b: N1, N2
        cq = coverage_half(q)
        crit["closing_stock"] = closing_half(q, text)
        crit["coverage"] = coverage_value(cq, text)
        if month_numbers(text) or COVERAGE_NUMBER_UNIT.search(unit_text(text)):
            crit["basis_wording"] = basis_wording(cq, text)
        crit["analysis_month_named"] = ("pass", "named") if AS_OF_WORDS.search(text) else ("fail", "not named")
        crit["no_aggregated_coverage"] = aggregation(cq, text, sql)
    elif q["metric"] == "stock_coverage" and (q.get("held_out") or q.get("added_in_stage") == 2):   # rubric 3.2; N3
        crit["item_set" if e["graded_on"] == "item_set" else "lowest_member"] = (
            item_set(q, text) if e["graded_on"] == "item_set" else lowest_member(q, text))
        crit["basis_wording"] = basis_wording(q, text)
        crit["analysis_month_named"] = ("pass", "named") if AS_OF_WORDS.search(text) else ("fail", "not named")
        crit["no_aggregated_coverage"] = aggregation({**q, "expected": {}}, text, sql)
    elif q["metric"] == "stock_coverage":
        if q["id"] == "T5":
            crit["t5_outcome"] = t5_outcome(q, text, results)
        elif q["id"] == "DIM_MIX":
            crit["basis_switch"] = basis_switch(q, text, results)
        elif "refusal" in e:
            crit["refusal"] = refusal(q, text, results)
        elif "summary" in e and "rows" not in e:
            crit["summary"] = selection_summary(q, text)
        elif "rows" in e and "sku_code" in e["rows"][0] and "follows" not in q:
            crit["selection_rows"] = selection_rows(q, text)
        elif "rows" in e:
            crit["numeric"] = rows_value(q, text)
        else:
            crit["numeric"] = coverage_value(q, text)
        if month_numbers(text) or "summary" in e or "rows" in e or COVERAGE_NUMBER_UNIT.search(unit_text(text)):
            crit["basis_wording"] = basis_wording(q, text)
        if e.get("names_as_of"):
            crit["analysis_month_named"] = ("pass", "named") if AS_OF_WORDS.search(text) else ("fail", "not named")
        crit["no_aggregated_coverage"] = aggregation(q, text, sql)
    elif q["metric"] == "closing_stock":
        crit["numeric"] = decide(numbers(text), e["value"], e.get("wrong_values", {})) if not (
            e["value"] == 0 and ZERO_WORDS.search(text) and not [n for n in numbers(text) if n.value != 0
                                                                and not matches(n, 0)]) else ("pass", "zero stated")
    elif q["id"] == "G1":
        crit["numeric"] = decide(numbers(text), e["value"], e["wrong_values"])
    elif q["id"] == "G2":
        crit["numeric"] = rows_value(q, text)
    crit["routing"] = routing(q, turn["config"], uses, results, sv_tools)
    states = [v for v, _ in crit.values()]
    verdict = "wrong" if "fail" in states else ("manual" if "manual" in states else "correct")
    # The figure-only score (owner, 2026-10-07): the same criteria without the unit half of basis_wording.
    fig_states = [v for k, (v, _) in crit.items() if k != "basis_wording"]
    if "basis_wording" in crit:
        fig_states.append(basis_named(q, text)[0])
    figure_only = "wrong" if "fail" in fig_states else ("manual" if "manual" in fig_states else "correct")
    decision = DECISIONS.get(turn.get("request_id"))
    decided = decision and decision["question_id"] == q["id"] and decision["configuration"] == turn["config"]
    if figure_only == "manual" and decided:
        figure_only = decision["verdict"]
    if verdict == "manual" and decided:
        verdict = decision["verdict"]
        crit["manual_decision"] = ("pass" if verdict == "correct" else "fail",
                                   f"owner, {decision['date']}, rule {decision['rule']}: {' '.join(decision['reason'].split())}")
    return {"config": turn["config"], "question_id": q["id"], "verdict": verdict, "verdict_figure_only": figure_only,
            "rubric": _CTX["rubric"], "request_id": turn.get("request_id"),
            "criteria": {k: {"result": v, "why": w} for k, (v, w) in crit.items()},
            "warnings_relayed": warnings(q, text) if q["metric"] == "stock_coverage" else "n/a",
            "governance": {"ROWS_COMMENTED": dict(zip(("flag", "why"), rows_commented(q, text))),
                           "FRESHNESS_STATED": freshness_stated(text)}}


def scores(grades: list[dict]) -> dict[str, dict[str, dict[str, int]]]:
    """Per configuration, the counts of the primary verdict (rubric 3.2) and of the figure-only score beside it."""
    out: dict[str, dict[str, dict[str, int]]] = {}
    for g in grades:
        c = out.setdefault(g["config"], {k: dict.fromkeys(("correct", "wrong", "manual"), 0)
                                         for k in ("primary", "figure_only")})
        c["primary"][g["verdict"]] += 1
        c["figure_only"][g["verdict_figure_only"]] += 1
    return dict(sorted(out.items()))


# ------------------------------------------------------------------------------------------------ run_call.py logs

def _table(d: dict) -> dict:
    rs = d.get("result_set") or {}
    cols = [c.get("name") for c in (rs.get("resultSetMetaData") or {}).get("rowType", [])]
    return {"title": d.get("title"), "columns": cols, "rows": rs.get("data") or [], "query_id": d.get("query_id")}


def tables_from_events(log_dir: Path, label: str, n: int | None) -> list[dict]:
    """The tables of one recorded call (events.jsonl of the run folder), as run_call.summarize keeps them since
    session 8c: the response.table events and the final response's table blocks, once each."""
    f = log_dir / "events.jsonl"
    if not f.exists():
        return []
    out, seen = [], set()
    for line in f.read_text().splitlines():
        r = json.loads(line)
        if r.get("label", "").lower() != label.lower() or (n is not None and r.get("n") != n):
            continue
        blocks = [e["data"] for e in r["events"] if e["event"] == "response.table" and isinstance(e["data"], dict)]
        for e in r["events"]:
            if e["event"] == "response" and isinstance(e["data"], dict):
                blocks += [c["table"] for c in e["data"].get("content", []) if c.get("type") == "table"]
        for b in blocks:
            t = _table(b)
            key = (t["query_id"], t["title"], json.dumps(t["rows"]))
            if key not in seen:
                seen.add(key)
                out.append(t)
    return out


def turns_from_log(log_dir: Path, labels: dict[str, tuple[str, str]]) -> list[dict]:
    """labels: run_call label -> (config, question_id). Reads summary_<tag>.json and trace_<tag>.json."""
    out = []
    for label, (config, qid) in labels.items():
        tag = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        s = json.loads((log_dir / f"summary_{tag}.json").read_text())
        calls = s["calls"]
        trace_f = log_dir / f"trace_{tag}.json"
        sql = []                      # executed SQL: the trace's final_sql when readable, else each SQL tool call's input
        if trace_f.exists():
            for r in json.loads(trace_f.read_text()):
                attrs = r.get("RECORD_ATTRIBUTES")
                attrs = json.loads(attrs) if isinstance(attrs, str) else (attrs or {})
                x = attrs.get("snow.ai.observability.agent.tool.sql_execution.final_sql")
                if x:
                    sql.append(x)
        if not sql:
            sql = [u["input"]["sql"] for c in calls for u in c.get("tool_uses", [])
                   if "sql" in (u.get("type") or "") and isinstance(u.get("input"), dict) and u["input"].get("sql")]
        tables = calls[-1].get("tables") if calls else []
        if calls and "tables" not in calls[-1]:     # a summary written before session 8c: read the recorded events
            tables = tables_from_events(log_dir, label, calls[-1].get("n"))
        out.append({"config": config, "question_id": qid, "answer": calls[-1].get("text", "") if calls else "",
                    "tables": tables or [],
                    "request_id": calls[-1].get("request_id") if calls else None,
                    "tool_uses": [u for c in calls for u in c.get("tool_uses", [])],
                    "tool_results": [r for c in calls for r in c.get("tool_results", [])], "sql": sql})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--turns", type=Path, required=True)
    ap.add_argument("--sv-tools", default="", help="comma-separated names of semantic view tools in the specs")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    sv = {x for x in a.sv_tools.split(",") if x}
    grades = [grade_turn(json.loads(line), sv) for line in a.turns.read_text().splitlines() if line.strip()]
    text = json.dumps(grades, indent=2)
    (a.out.write_text(text) if a.out else print(text))
    manual = [g for g in grades if g["verdict"] == "manual"]
    print(f"{len(grades)} turns: " + ", ".join(f"{v} {sum(g['verdict'] == v for g in grades)}"
                                              for v in ("correct", "wrong", "manual")), file=sys.stderr)
    for g in manual:
        print(f"MANUAL {g['config']} {g['question_id']}: " + "; ".join(
            f"{k}: {c['why']}" for k, c in g["criteria"].items() if c["result"] == "manual"), file=sys.stderr)


if __name__ == "__main__":
    main()
