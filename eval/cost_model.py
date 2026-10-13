"""
Cost model of the campaign (session 8c, step 5): AI Credits per question and configuration, stage totals, cuts, the
overfitting drill, durations. No Snowflake call. Prints the tables of eval/campaign.md.

    python eval/cost_model.py

Per question, AI Credits [measured inputs, inferred for the campaign]: the smoke turns of sessions 8, 8b and 8c-0
(eval/fixtures/smoke_tokens.jsonl) priced with the credits per token of eval/guards.py, which reproduce the billed rows
of session 8 (A 0.059 to 0.080, B1 0.053 to 0.073, D 0.072 to 0.111 per tool turn). D' per question: 0.158 with its
resumes, from the session 8 billed read [measured]; its low and high are the smallest and largest smoke questions.
C: coverage turns and semantic view turns apart; its high for coverage is a DIM_MIX-like turn with two tool calls.
"""

from __future__ import annotations

import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
import guards  # noqa: E402
import yaml  # noqa: E402

QUESTIONS_BY_ID = {q["id"]: q for q in yaml.safe_load((ROOT / "generated" / "reference_questions.yaml").read_text())["questions"]}

AI_USD, PF_USD = guards.USD_PER_AI_CREDIT, guards.USD_PER_PLATFORM_CREDIT
CONFIGS = ("A", "B1", "B2", "C", "D", "DP")
NO_TOOL = 0.011             # a turn with no tool (T6), measured 0.0107 to 0.0114
WARMUP = {"DP": 0.17}       # a block's first call writes the whole prompt cache [inferred: about 33,000 tokens at the
WARMUP_OTHER = 0.054        # cache-write rate; D' 0.16 to 0.18 measured in session 8]
STAGE1_ROUTES = {"coverage": 18, "semantic_view": 5, "clarify": 1}
SQL_PER_TOOL_TURN = (0.004, 0.010, 0.016)           # Platform Credits attached to a tool turn [measured, session 8]
SECONDS = {"A": 29, "B1": 24, "B2": 36, "C": 23, "D": 27, "DP": 38}   # per question, client total + about 6 s of
# connection and warm guard [measured client totals of the smokes; overhead inferred]


def per_question() -> dict[str, tuple[float, float, float]]:
    rows = [json.loads(x) for x in (ROOT / "eval" / "fixtures" / "smoke_tokens.jsonl").read_text().splitlines()]
    lab = defaultdict(list)
    for r in rows:
        if r["cache_write"] is not None:
            lab[(r["config"], r["label"])].append(r)
    out = {}
    for cfg in CONFIGS:
        q = sorted(sum(guards.credits(c) for c in cs) for (c, _), cs in lab.items()
                   if c == cfg and any(x["tool_uses"] for x in cs) and not (cfg == "C" and cs[0]["input"] >= 120000))
        out[cfg] = (q[0], st.median(q), q[-1])
    out["DP"] = (0.10, 0.158, out["DP"][2])     # low: a smoke label can hold a resume alone (0.02); 0.10 [inferred]
    c_sv = sorted(sum(guards.credits(c) for c in cs) for (c, _), cs in lab.items()
                  if c == "C" and cs[0]["input"] >= 120000)
    out["C_SV"] = (c_sv[0], st.median(c_sv), c_sv[-1])
    out["C"] = (out["C"][0], out["C"][1], 0.045)
    return out


def stage1(pq) -> dict[str, list[float]]:
    out = {}
    for cfg in CONFIGS:
        warm = WARMUP.get(cfg, WARMUP_OTHER)
        if cfg == "C":
            vals = [18 * pq["C"][i] + 5 * pq["C_SV"][i] + NO_TOOL + warm for i in range(3)]
        else:
            vals = [23 * pq[cfg][i] + NO_TOOL + warm for i in range(3)]
        out[cfg] = vals
    return out


def stage2_turns(d: int) -> dict[str, int]:
    """Owner (decision 3 after step 5): repetitions in all, stage 1 included: 5 for B2, C and D', 3 for B1 and D; A is
    not played in stage 2 (owner, 2026-10-06). A discriminating question runs r2 to rN in stage 2, a held-out question
    r1 to rN."""
    reps = {"B1": 3, "B2": 5, "C": 5, "D": 3, "DP": 5}
    out = {cfg: (n - 1) * d + n * HELD_OUT for cfg, n in reps.items()}
    out["A"] = 0
    return out


HELD_OUT = 4


def stage2(pq, d: int) -> dict[str, list[float]]:
    turns = stage2_turns(d)
    c_mix = [0.8 * pq["C"][i] + 0.2 * pq["C_SV"][i] for i in range(3)]     # a fifth of C's turns on its view [inferred]
    out = {}
    for cfg in CONFIGS:
        unit = c_mix if cfg == "C" else pq[cfg]
        out[cfg] = [turns[cfg] * unit[i] + (WARMUP.get(cfg, WARMUP_OTHER) if turns[cfg] else 0) for i in range(3)]
    return out


def stage2_usd(pq, d: int) -> list[float]:
    """AI Credits plus the warehouse over the stage's hours (plus a quarter hour of warm-ups and gaps), in USD."""
    ai = [sum(v[i] for v in stage2(pq, d).values()) * AI_USD for i in range(3)]
    return [x + (hours(stage2_turns(d)) + 0.25) * PF_USD for x in ai]


def max_d(pq, budget: float, i: int = 1) -> int | None:
    """The largest number of discriminating questions whose stage 2 fits the budget (USD), at low, expected or high
    (i = 0, 1, 2); None if the held-out questions alone do not fit."""
    best = None
    for d in range(0, 25):
        if stage2_usd(pq, d)[i] <= budget:
            best = d
    return best


def exact_upper_at_zero(n: int) -> float:
    """Exact (Clopper-Pearson) one-sided 95 percent upper bound of a failure rate when 0 failures are seen in n trials:
    1 - 0.05^(1/n). (Wilson's two-sided bound at zero failures, z^2 / (n + z^2), is higher: 16.1 percent for n = 20.)"""
    return 1 - 0.05 ** (1 / n)


def trials(d: int) -> dict[str, int]:
    """Pooled trials per configuration on the discriminating questions (stage 1 and 2) and on the held-out ones; A has
    stage 1 only (owner, 2026-10-06)."""
    reps = {"A": 1, "B1": 3, "B2": 5, "C": 5, "D": 3, "DP": 5}
    out = {c: (n * d, n * HELD_OUT) for c, n in reps.items()}
    out["A"] = (d, 0)
    return out


def tool_turns_stage1() -> int:
    return 6 * 23


def hours(turns: dict[str, int]) -> float:
    return sum(turns[c] * SECONDS[c] for c in turns) / 3600


# Session 9b (owner, 2026-10-07): the reduced stage 2, C and B2 only, estimated from the BILLED costs of stage 1
# (snowflake/phase5_campaign/stage1_results.md, sections 8 and 11) [measured inputs, inferred for stage 2].
# Per graded turn, USD, all costs included: the billed AI Credits of the stage 1 turns, the guardrail (0.2909 credits over
# 188 calls) and the warehouse per turn of its stage 1 block at 1.35 credits an hour.
MEAN_TURN_USD = {"C": 0.102, "B2": 0.258}
SELECTION_TURN_USD = {"C": 0.093, "B2": 0.328}       # the mean of the three selection questions (S_*), the heavy case
WARMUP_CREDITS = {"C": 0.0904, "B2": 0.0929}         # billed, stage 1
GAP_HOURS = 0.1                                      # two blocks: two fifths of the quarter hour section 11 gave five
WAREHOUSE_BILLED_PER_HOUR = 1.3506                   # measured (section 8); the guard counts 1.0
# What the harness guard will count (its pause reads this): billed AI Credits per turn, no guardrail, the warehouse at
# 1.0 credit an hour over the running seconds per call of each stage 1 block (C 603 s, B2 882 s for 25 calls).
AI_CREDITS_PER_TURN = {"C": 0.7615 / 24, "B2": 2.4391 / 24}
SECONDS_PER_CALL = {"C": 603 / 25, "B2": 882 / 25}


def is_list_question(qid: str) -> bool:
    q = QUESTIONS_BY_ID[qid]
    return qid.startswith("S_") or q.get("expected", {}).get("graded_on") == "item_set"


def reduced_stage2(blocks: list[dict]) -> dict:
    """The reduced plan's cost (eval/stage2_reduced.yaml): every turn at its configuration's billed mean, and a heavy case
    with the list questions at the mean of the selection questions; plus the warm-ups and the gaps. guard_usd is what the
    harness estimate will show, against the pause at 13.5 USD (90 percent of 15)."""
    turns = {b["config"]: [t["qid"] for t in b["turns"] if t["qid"] != "WARMUP"] for b in blocks}
    lists = {c: sum(is_list_question(q) for q in qs) for c, qs in turns.items()}
    mean = {c: len(qs) * MEAN_TURN_USD[c] for c, qs in turns.items()}
    heavy = {c: lists[c] * SELECTION_TURN_USD[c] + (len(qs) - lists[c]) * MEAN_TURN_USD[c] for c, qs in turns.items()}
    fixed = sum(WARMUP_CREDITS[c] for c in turns) * AI_USD + GAP_HOURS * WAREHOUSE_BILLED_PER_HOUR * PF_USD
    guard_ai = sum(len(qs) * AI_CREDITS_PER_TURN[c] + WARMUP_CREDITS[c] for c, qs in turns.items()) * AI_USD
    guard_wh = sum((len(qs) + 1) * SECONDS_PER_CALL[c] for c, qs in turns.items()) / 3600 * PF_USD
    return {"turns": {c: len(qs) for c, qs in turns.items()}, "list_turns": lists, "mean": mean, "heavy": heavy,
            "fixed_usd": round(fixed, 3), "total_mean_usd": round(sum(mean.values()) + fixed, 2),
            "total_heavy_usd": round(sum(heavy.values()) + fixed, 2), "guard_usd": round(guard_ai + guard_wh, 2),
            "pause_usd": 13.5, "ceiling_usd": 15.0}


def fmt(v: list[float]) -> str:
    return " / ".join(f"{x:.2f}" for x in v)


def main() -> None:
    pq = per_question()
    print("per question (AI Credits, low / expected / high):")
    for k, v in pq.items():
        print(f"  {k}: {fmt(list(v))}")
    s1 = stage1(pq)
    tot1 = [sum(s1[c][i] for c in CONFIGS) for i in range(3)]
    print("stage 1 per configuration:", {c: fmt(v) for c, v in s1.items()})
    print("stage 1 AI Credits:", fmt(tot1), "USD:", fmt([x * AI_USD for x in tot1]))
    print("stage 1 guard estimate (AI Credits plus 1.5 warehouse hours), USD:",
          fmt([x * AI_USD + 1.5 * PF_USD for x in tot1]), "against the 36 USD pause (40 USD ceiling)")
    t1 = {c: 25 for c in CONFIGS}
    h1 = hours(t1)
    sql1 = [x * tool_turns_stage1() for x in SQL_PER_TOOL_TURN]
    print(f"stage 1 hours {h1:.2f}; attached SQL credits {fmt(sql1)}; warehouse credits about {h1 + 0.25:.2f}")
    for d in (4, 8, 14, 20):
        s2 = stage2(pq, d)
        tot = [sum(s2[c][i] for c in CONFIGS) for i in range(3)]
        turns = stage2_turns(d)
        print(f"stage 2 d={d}: turns {sum(turns.values())} {turns}; AI Credits {fmt(tot)}; "
              f"USD with warehouse {fmt(stage2_usd(pq, d))}; hours {hours(turns):.2f}")
    print("stage 2, held-out questions alone (d = 0): USD with warehouse", fmt(stage2_usd(pq, 0)))
    for budget in (35, 40, 45):
        print(f"stage 2 budget {budget} USD: largest d low / expected / high cost:",
              " / ".join(str(max_d(pq, budget, i)) for i in range(3)))
    print("power of the pooled rate (exact one-sided 95 percent upper bound of the failure rate at 0 failures):")
    for d in (4, 8, 12):
        t = trials(d)
        print(f"  d={d}: " + "; ".join(f"{c} {n} trials, {exact_upper_at_zero(n):.1%}"
                                       + (f" (held-out {h}, {exact_upper_at_zero(h):.1%})" if h else "")
                                       for c, (n, h) in t.items()))
    drill = [43 * pq["B2"][i] + WARMUP_OTHER for i in range(3)]
    print("drill AI Credits:", fmt(drill), "USD:", fmt([x * AI_USD for x in drill]), f"hours {43 * SECONDS['B2'] / 3600:.2f}")
    print("per configuration, per question, USD (expected):", {c: round(pq[c][1] * AI_USD, 3) for c in CONFIGS})


if __name__ == "__main__":
    main()
