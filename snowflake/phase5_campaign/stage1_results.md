# Campaign stage 1 results (session 9a, 2026-10-06)

The 24 stage 1 questions (`generated/reference_questions.yaml`, held-out questions excluded) once on the six frozen
configurations, through `eval/campaign.py run --stage 1` as LINKML_SVC, budget `campaign`, `--streams 1`, seed
20261005, configuration order D′, D, B1, B2, A, C. Graded with `eval/grade.py`, rubric 3.2, no change during the stage.
Harness commits of the session: 42dd0a3 (D064 to D066), 1e29a07, de44d3a, d5d3024, f01a932, 7c07b8e (owner's harness
fixes after two token guard stops of D, below). No frozen object changed. Raw logs, events, traces and the state file
are outside the repository (`linkml-metrics-runs/campaign/`). Tags: **[measured]**, **[documented]**, **[inferred]**.

## 1. Validity before reading

| Check | Result | Tag |
|---|---|---|
| Manifest | 144 graded turns, the expected 24 x 6; no turn missing, none graded twice; every turn's summary exists | measured |
| Single provenance, agent | every one of the 180 graded REST calls was served by its frozen version, read per call from its own trace rows (`ai.observability.record_id`): A and C VERSION$6, B1, D and D′ VERSION$7, B2 VERSION$8. The declared default version, read before every block, was the frozen one each time | measured |
| Single provenance, instrument | rubric 3.2 and `eval/grade.py` unchanged since commit ff54f6f (2026-10-05), before the first campaign call; one orchestration model on every turn, `claude-sonnet-5-5` | measured |
| Traces | readable on the first try, 16 minutes after the last call; 2,238 rows for 144 turns, no turn without a row of its own, no call id without rows, no foreign row (D065) | measured |
| Statements failed on authorization | none: no `does not exist or not authorized` in any trace. The campaign measures the agents, not a grant gap | measured |
| SQL statements that failed (status 500 on the SQL tool span) | B2 38 in 17 of 24 turns (36 `invalid identifier`, 1 ambiguous column, 1 `Writing arbitrary SQL is blocked`); A 2 in 2 turns (both `Writing arbitrary SQL is blocked`); B1 1 (unsupported subquery); D 1 (invalid identifier); C and D′ none on that span | measured |

## 2. Verdicts (configuration by question)

| Question | A | B1 | B2 | C | D | D′ |
|---|---|---|---|---|---|---|
| T1 | correct | wrong | wrong | correct | correct | correct |
| T2 | manual | wrong | correct | correct | correct | manual |
| T3 | correct | correct | correct | correct | correct | correct |
| T4 | correct | manual | correct | correct | correct | correct |
| T5 | correct | correct | correct | correct | correct | correct |
| T6 | correct | correct | correct | correct | correct | correct |
| T7 | correct | wrong | wrong | correct | wrong | manual |
| T7_R1 | wrong | wrong | wrong | correct | wrong | correct |
| T8 | wrong | wrong | correct | correct | correct | correct |
| NO_DEMAND | wrong | wrong | wrong | correct | wrong | wrong |
| BEYOND_H | wrong | wrong | wrong | correct | correct | wrong |
| BULK_SCOPE | correct | correct | correct | correct | wrong | correct |
| DIM_MIX | correct | correct | correct | correct | correct | wrong |
| T9 | manual | wrong | wrong | correct | wrong | wrong |
| CS_LAST_MONTH_GAP | manual | manual | correct | correct | correct | correct |
| CS_MIDDLE_MONTH_GAP | correct | correct | correct | correct | correct | correct |
| CS_FAMILY | correct | correct | correct | correct | correct | correct |
| BULK_SCOPE_DRILL | wrong | wrong | correct | correct | correct | wrong |
| G1 | correct | correct | correct | correct | correct | correct |
| G2 | correct | correct | correct | correct | correct | correct |
| S_OWN_UNIT | correct | correct | correct | correct | correct | correct |
| S_STOCKOUT_COUNTRY | wrong | correct | wrong | correct | wrong | wrong |
| S_FIRST_WORLD | wrong | wrong | wrong | correct | wrong | wrong |
| S_DORMANT_VALUE | wrong | wrong | wrong | correct | correct | wrong |
| **correct / wrong / manual** | 13 / 8 / 3 | 11 / 11 / 2 | 15 / 9 / 0 | 24 / 0 / 0 | 17 / 7 / 0 | 14 / 8 / 2 |

One repetition per cell: a single turn, not a rate [measured]. Totals 94 correct, 43 wrong, 7 manual.

## 3. Per configuration

| Measure | A | B1 | B2 | C | D | D′ |
|---|---|---|---|---|---|---|
| Routing (pass of 24) | 24 | 24 | 24 | 24 | 24 | 24 |
| ROWS_COMMENTED | 1 of 24 | 0 of 24 | 1 of 24 | 1 of 24 | 1 of 24 | 0 of 24 |
| FRESHNESS_STATED present / latest | 21 / 21 | 24 / 24 | 23 / 23 | 23 / 23 | 24 / 23 | 0 / 0 |
| Warnings relayed, the 5 questions that carry warnings (yes / partial / no) | 1 / 1 / 3 | 0 / 2 / 3 | 0 / 0 / 5 | 5 / 0 / 0 | 1 / 1 / 3 | 0 / 1 / 4 |
| Input tokens per turn, median | 200,493 | 117,179 | 258,634 | 61,996 | 221,403 | 291,563 |
| Input tokens per turn, range | 36,551 to 276,296 | 34,996 to 184,348 | 34,749 to 454,998 | 39,844 to 164,734 | 37,399 to 1,520,769 | 143,026 to 651,698 |
| Largest REST call, input tokens | 276,296 | 184,348 | 454,998 | 164,734 | 1,520,769 | 243,490 |
| Estimated USD per turn, median (range) | 0.138 (0.022 to 0.179) | 0.109 (0.022 to 0.159) | 0.208 (0.022 to 0.368) | 0.039 (0.022 to 0.153) | 0.194 (0.024 to 0.857) | 0.163 (0.045 to 0.476) |
| Estimated USD, 24 graded turns | 3.29 | 2.64 | 4.88 | 1.52 | 5.91 | 4.19 |
| Warm-up attempts, estimated USD | 0.123 | 0.136, 0.137 | 0.186 | 0.181 | 0.192, 0.192, 0.191 | 0.399 |
| Latency per turn, client total, median (range), s | 27.5 (4.9 to 35.9) | 16.9 (5.0 to 29.4) | 30.4 (7.0 to 69.9) | 16.3 (4.7 to 22.8) | 28.4 (11.7 to 130.5) | 36.8 (13.8 to 119.7) |
| REST calls per question (turns) | 1: 24 | 1: 24 | 1: 24 | 1: 24 | 1: 24 | 1: 1; 2: 15; 3: 3; 4: 5 |
| REST calls of the 24 graded turns | 24 | 24 | 24 | 24 | 24 | 60 |

Tokens, USD and calls are measured (REST usage of each call, priced at the rates of `eval/guards.py`, so the USD is an
estimate until the billed read); latency is the client total of the turn's calls [measured].

Refusals and their codes [measured]:
- **T5** (packs not additive): all six answered with the quantity-equivalent coverage and said why packs do not add up
  (`model_refusal_with_qty_eq_answer`, correct, recorded as a deviation by the rubric). C's procedure returned no
  coded refusal on T5.
- **T6** (no month): all six asked for the month or refused with a reason, no figure.
- **T7_R1** (an item with two lifecycle statuses): C and D′ refused without a number and named the duplicate
  master data; A, B1, B2 and D gave the fanned-out figures (2.25 and 6.0).
- **DIM_MIX**: A relayed the refusal and offered value; B1, B2, C and D gave the value coverage with the reason;
  D′ gave 13.3, a figure the grader does not match.
- **Codes:** only C returns coded refusals and warnings, from its procedure: `MASTER_DATA_FANOUT` 1,
  `BASIS_NOT_COMPARABLE` 1, `DEFAULT_SCOPE_EXCLUDED` 2, `FORECAST_GAPS_FILLED` 6, `MASTER_DATA_DUPLICATES` 1, and the
  row statuses `NO_STOCK` 9, `NO_DEMAND` 7, `BEYOND_HORIZON` 8. Every other configuration refuses in prose.

Governance flags [measured]:
- **ROWS_COMMENTED:**
  - A on T7_R1 (the coverage of SKU-H07, a member not asked);
  - B2 and C on BULK_SCOPE_DRILL (a figure derived across countries);
  - D on S_DORMANT_VALUE ("the highest at 50.0 months").
- **FRESHNESS_STATED missing:**
  - A on S_FIRST_WORLD, T6 and DIM_MIX;
  - B2 on T6, C on T6;
  - D′ on all 24 turns.
- **FRESHNESS_STATED not the latest month:** D on S_FIRST_WORLD, where the time-limit sentence is glued to the line.

## 4. Per question: who failed and how

Basis wording means the rubric 3.x rule (`basis_wording`): a sentence gives the coverage in a unit ("in kg
equivalent", "in litres") or the basis is not named [measured, grader criteria].

| Question | Failed (wrong) | How |
|---|---|---|
| T1 | B1, B2 | basis wording (correct figure) |
| T2 | B1 | basis wording |
| T7 | B1, B2, D | the naive join on the duplicated item (3.0, `naive_join_on_duplicated_item`); D also basis wording |
| T7_R1 | A, B1, B2, D | figures at the fanned-out grain (2.25 and 6.0) instead of a refusal |
| T8 | A, B1 | basis wording |
| NO_DEMAND | A, B1, B2, D, D′ | no figure and the reason given (numeric passes), but a sentence words the coverage in a unit |
| BEYOND_H | A, B1, B2, D′ | A: 22, not 50.0; B1, B2, D′: basis wording |
| BULK_SCOPE | D | basis wording |
| DIM_MIX | D′ | 13.3, not 8.70 on value |
| T9 | B1, B2, D, D′ | basis wording |
| BULK_SCOPE_DRILL | A, B1, D′ | A and D′: basis wording; B1: Belgium 10.4, not 11.38 |
| S_STOCKOUT_COUNTRY | A, B2, D, D′ | A: basis not named; B2: coverages of three kept products not on their lines; D: SKU-0008 (3.13 months, outside the window) named as at risk; D′: no final answer (turn cap) |
| S_FIRST_WORLD | A, B1, B2, D, D′ | A: listed coverages not found, basis not named; B1, D: members set apart not named; B2: SKU-0017 missing, SKU-H03 added; D′: no final answer (turn cap) |
| S_DORMANT_VALUE | A, B1, B2, D′ | the count of kept pairs (28) and the stock value they tie up missing |

Manual verdicts, to be decided by the owner (`eval/manual_decisions.yaml`, by request id) before the gate runs:

| Configuration | Question | Request id (last call) | Why the grader cannot decide |
|---|---|---|---|
| A | T2 | `0000008d-0000-4000-8000-00000000008d` | 7.0 (expected) given, and 5.0 (`row_based_window`) given as a hypothetical ("if they were meant to be 100 each, coverage would be 5.0 months") |
| D′ | T2 | `00000027-0000-4000-8000-000000000027` | 7.0 given; 5 given as the cover without the zero-demand months ("stretch the cover from 5 months to 7") |
| B1 | T4 | `0000004d-0000-4000-8000-00000000004d` | "about 8.5 months" (expected); 7.71 (`window_starts_at_as_of`) matched by another number of the answer |
| A | CS_LAST_MONTH_GAP | `0000008e-0000-4000-8000-00000000008e` | 0 packs (expected) given; 350 (`last_known_value`) given as history |
| B1 | CS_LAST_MONTH_GAP | `0000005b-0000-4000-8000-00000000005b` | 0 (expected) and 350 both given |
| A | T9 | `00000091-0000-4000-8000-000000000091` | 0 months (expected); 3.5 given as what the May stock "would have lasted" |
| D′ | T7 | `0000001f-0000-4000-8000-00000000001f` | no coverage number in the final text (4 REST calls) |

## 5. Harness events (none regraded)

| # | Event | Outcome |
|---|---|---|
| 1 | D BULK_SCOPE_DRILL, 18:36 UTC: the per-call token guard fired (357,493 input tokens, ceiling 308,829), after a complete answer (status 200, `00000036-0000-4000-8000-000000000036`); the block stopped; the runner was stopped by hand before B1 | owner: a calibration fault (the smokes had no follow-up turn); stop lifted; the turn kept and graded as is; follow-up ceiling, then the runaway guard (below) |
| 2 | B1 warm-up `B1_WARMUP_campaign-s1_r1` made after the runner was stopped (status 200, 18:37:16 to 18:37:29); not in the state file | recorded as an orphan attempt (not a valid warm-up); a new warm-up `-a2` on resume |
| 3 | Resume 1, D S_STOCKOUT_COUNTRY, 18:57 UTC: the token guard fired again (746,962 input tokens on one call, 13 tool uses, `0000003f-0000-4000-8000-00000000003f`), answer complete with a leading fragment "Simpler to rewrite line."; the monitor stopped the runner | owner: the per-call token guard is no stop condition any more (one D call sums every internal planning step); replaced by a 2 USD per-turn runaway guard; the turn kept and graded as is |
| 4 | Block caps 26 left no margin for the added warm-ups | owner: 30 for D, B1, B2, A and C (D and B1 by override); a cap reached by a block's last turn is no stop |
| 5 | `lifted_stops` dropped from the guard state on the first resume (the runner rewrites the guard from its own fields) | fixed (7c07b8e); the first lift restored from the block record |
| 6 | D′ S_FIRST_WORLD and S_STOCKOUT_COUNTRY reached the per-question cap of 4 REST calls with no final answer | graded as the others (no answer, wrong); not replayed (owner) |
| 7 | D warm-ups: `-a2` and `-a3` on resumes (cold cache) | not graded |
| 8 | No version guard, skill pre-check, cost pause, error or block cap fired; the runaway guard never fired (largest turn 0.857 USD, D S_DORMANT_VALUE) | none |

## 6. Gate (eval/gate.md) and stage 2 input

The gate refuses to run while a manual verdict is open, so `eval/stage2.yaml` is not written yet. Sensitivity, every
combination of the 7 manual verdicts (correct or wrong), no file written [measured]:
- **19 questions are selected whatever the manual decisions are:** T1, T2, T3, T4, T7, T7_R1, T8, NO_DEMAND,
  BEYOND_H, BULK_SCOPE, DIM_MIX, T9, BULK_SCOPE_DRILL, G1, G2, S_OWN_UNIT, S_STOCKOUT_COUNTRY, S_FIRST_WORLD,
  S_DORMANT_VALUE.
- **CS_LAST_MONTH_GAP** is selected only if A's or B1's manual verdict is decided wrong.
- **Never selected:** CS_FAMILY, CS_MIDDLE_MONTH_GAP, T5 and T6 (every configuration correct, no difference).
- **With every manual verdict decided correct:**
  - `a_passed`: T1, T2, T3, T4, T7, BULK_SCOPE, DIM_MIX, T9, G1, G2, S_OWN_UNIT;
  - `drop_order`: G1, T4.
- **Selection reasons, three questions selected without any failure:**
  - G2: `value`, on all six. The gate compares amounts at an absolute 0.05, so the rounding of EUR amounts differs.
  - S_OWN_UNIT: `basis`, on all six. The basis words named differ.
  - T3: `basis`, on A and B2.

  These follow the gate rule as written [measured]. Whether the 0.05 tolerance should apply to amounts is an open
  question for the owner (section 7 of `docs/phase5_notes.md` part 2).

The stage 2 size is decided at the cost read, not here. A is not repeated in stage 2 (owner, session 9a,
`eval/campaign.md`); `eval/campaign.py plan --stage 2` still plans A's repetitions and changes after the owner's go.

## 7. UTC windows for the cost read

Warehouse segments of the stage (`guard.segments`, the blocks' runs; a pause is not counted) [measured]:

| Block | Segments (UTC, 2026-10-06) | REST calls (all attempts) |
|---|---|---|
| D′ | 18:11:12.9 to 18:33:08.8 | 63 |
| D | 18:33:11.3 to 18:37:10.6; 18:50:41.6 to 18:57:18.5; 19:08:07.3 to 19:16:17.5 | 27 |
| B1 | 18:37:16.7 to 18:37:29.0 (orphan warm-up); 19:16:19.8 to 19:25:39.5 | 26 |
| B2 | 19:25:41.2 to 19:40:24.7 | 25 |
| A | 19:40:28.0 to 19:53:58.3 | 25 |
| C | 19:54:01.8 to 20:03:09.8 | 25 |

Stage window: first call 18:11:12 UTC, last call 20:03:09 UTC; 191 REST calls in all (graded turns, warm-ups and the
orphan). Also in the account's history from LINKML_SVC on that day: the read-only checks (six skill pre-checks with LIST and
GET, one by the runner at each of its three starts and three by hand before them, the version reads, the trace read at
20:19) and the warm guard's
SELECTs [measured].

Running estimate of the harness (`eval/guards.py`): 12.08 AI Credits (24.16 USD) plus 1.46 warehouse hours
(5.70 USD) = **29.86 USD against the 40 USD ceiling** [measured estimate; the billed figures come from the cost read].

## 8. Cost read (billed, read 2026-10-07)

Read once, under ACCOUNTADMIN, as a single read-only batch: `USE SECONDARY ROLES NONE` and seven SELECTs on
`SNOWFLAKE.ACCOUNT_USAGE`, approved by the owner as shown
(`eval/campaign.md`, "Cost read between the stages"). The output is outside the repository
(`linkml-metrics-runs/campaign/cost_read_s1.json`).
- S1 `CORTEX_AGENT_USAGE_HISTORY`: every LINKML_SVC call of 2026-10-06, per request.
- S2 `CORTEX_ANALYST_USAGE_HISTORY`, 17:00 to 22:00 UTC.
- S3 `WAREHOUSE_METERING_HISTORY` and S4 `WAREHOUSE_EVENTS_HISTORY`, for LINKML_METRICS_WH, 17:00 to 22:00 UTC.
- S5 `QUERY_HISTORY` and S6 `QUERY_ATTRIBUTION_HISTORY`, the same warehouse and hours, by user, inside and outside
  the stage window.
- S7 `METERING_DAILY_HISTORY` for 2026-10-06.

Prices: AI Credit 2.00 USD, warehouse credit 3.90 USD (decision 3, `eval/campaign.md`).

### Validity of the read

| Check | Result | Tag |
|---|---|---|
| Billed rows against the runner's calls | 191 rows. Each one is matched by request id to one call of `calls.json`; no row and no call is left without a match | measured |
| Other agent use that day | `CORTEX_AGENTS` in `METERING_DAILY_HISTORY` for the whole day: 12.081630210 credits, equal to the sum of S1. The account had no other agent use on 2026-10-06 | measured |
| Cortex Analyst billed apart (S2) | no row: the semantic view tools of A, B1, B2, D and D′ are billed inside the agent rows | measured |
| Role on every row | `LINKML_METRICS_ROLE`; `SQL_QUERY_CREDITS` null on every row | measured |

### AI Credits, per configuration (billed, `TOKEN_CREDITS`)

| Configuration | REST calls | AI Credits, total | 24 graded turns | Warm-ups | Per graded turn, median / mean / max (question) | USD |
|---|---|---|---|---|---|---|
| D′ | 63 | 2.2927 | 2.0932 | 0.1995 | 0.0814 / 0.0872 / 0.2380 (S_STOCKOUT_COUNTRY) | 4.59 |
| D | 27 | 3.2422 | 2.9548 | 0.2875 (three: cold resumes) | 0.0972 / 0.1231 / 0.4284 (S_DORMANT_VALUE) | 6.48 |
| B1 | 26 | 1.4561 | 1.3194 | 0.0685, plus the orphan 0.0682 | 0.0547 / 0.0550 / 0.0794 (S_DORMANT_VALUE) | 2.91 |
| B2 | 25 | 2.5320 | 2.4391 | 0.0929 | 0.1042 / 0.1016 / 0.1842 (S_FIRST_WORLD) | 5.06 |
| A | 25 | 1.7066 | 1.6449 | 0.0617 | 0.0690 / 0.0685 / 0.0896 (T9) | 3.41 |
| C | 25 | 0.8519 | 0.7615 | 0.0904 | 0.0195 / 0.0317 / 0.0764 (CS_LAST_MONTH_GAP) | 1.70 |
| **Total** | **191** | **12.0816** | **11.2129** | **0.8687** | | **24.16** |

A graded turn's credits are the sum of its calls (D′: 1 to 4 calls). Split of the 12.08 credits (`CREDITS_GRANULAR`,
all `claude-sonnet-5-5`): cache write 6.72 (56 percent), cache read 3.78 (31 percent), output 1.58 (13 percent),
uncached input 0.003 [measured].

Guardrail model: `CORTEX_AI_GUARDRAILS` in `METERING_DAILY_HISTORY`, 0.2909 credits (0.58 USD) on the day. This service
is billed apart from the agent rows and is not in the harness estimate. The REST usage of the stage shows 170 guardrail
calls (`cygnal-qwen3-8b-032026`), 829,252 tokens in all, which gives about 0.35 credits per million tokens [measured:
the day total and the tokens; inferred: that all of the day's guardrail credits are the stage's, since the day had no
other agent call].

### Warehouse (LINKML_METRICS_WH)

| Measure | Value | Tag |
|---|---|---|
| Metered compute, 18:00 to 21:00 UTC (S3) | 0.7706 + 1.2566 + 0.0251 = 2.0524 credits | measured |
| Running time (S4) | 5 runs within the stage: 18:11:14 to 18:25:31, 18:25:42 to 18:38:24, 18:50:44 to 18:57:58, 19:08:09 to 19:29:12, 19:29:17 to 20:04:04. In all 5,404 s, or 1.501 h. One more run after the stage, 20:19:15 to 20:20:21 (66 s, the trace read) | measured |
| Credits per hour of running time | 2.0524 / 1.5196 h = **1.3506**, not 1.0 | measured |
| **Stage share** | 1.501 h x 1.3506 = **2.0275 credits, 7.91 USD**. The trace read is excluded (0.025 credits) | measured; the split inferred |
| Cloud services | 0.0673 credits metered, not billed: the day's `CREDITS_BILLED` for `WAREHOUSE_METERING` equals its compute (2.1004) | measured |
| Credits attributed to queries (S6, stage window) | LINKML_SVC 1.0563 credits (485 queries); <admin user> 0.2670 (153 queries: the runner's version reads, skill pre-checks and warm guard). That is 1.32 of the 2.03 credits; the rest is the warehouse running idle between queries | measured |
| Auto-suspend fired twice inside a block | 18:25:31 (D′, down 11 s) and 19:29:12 (B2, down 5 s): the warm guard did not hold the warehouse; one cold resume each, no effect on cost | measured |

Per block, with each run split by the blocks' windows and the 60 s tail after a block's last call given to that block
[inferred]:

| | D′ | D | B1 | B2 | A | C |
|---|---|---|---|---|---|---|
| Running time, s | 1,306 | 1,171 | 629 | 882 | 814 | 603 |
| Warehouse credits | 0.490 | 0.439 | 0.236 | 0.331 | 0.305 | 0.226 |
| Warehouse USD | 1.91 | 1.71 | 0.92 | 1.29 | 1.19 | 0.88 |

### Stage 1 billed against the harness estimate

| Item | Harness estimate | Billed | Gap |
|---|---|---|---|
| Agent AI Credits | 12.0816 (24.16 USD) | 12.0816 (24.16 USD) | **0.0 percent** |
| Guardrail AI Credits | not counted | 0.2909 (0.58 USD) | not in the estimate |
| Warehouse | 1.460 h x 1.0 = 1.46 credits (5.70 USD) | 2.0275 credits (7.91 USD) | **+38.9 percent** |
| **Stage 1** | **29.86 USD** | **32.65 USD** | **+9.3 percent** |

Reading of the gaps:
- **Agent credits, 0.0 percent [measured].** For each of the 188 calls whose summary holds the REST usage, the
  orchestration tokens priced at `RATES` give the billed `TOKEN_CREDITS` to within 1e-16 credit. The input plus output
  tokens equal the billed `TOKENS`. The per-token rates of `eval/guards.py` are the billing rates, and the stage total
  agrees to 9 decimals.
- **Warehouse, +38.9 percent: two causes.**
  - **The rate, +35.1 percent.** The warehouse bills 1.3506 credits per hour of running time; the harness assumes 1.0
    (X-Small). `snowflake/00_setup.sql` creates the warehouse without naming a generation, and 1.35 is the documented
    rate of a Gen2 standard X-Small on AWS [the rate measured; the Gen2 cause inferred, not confirmed: confirming it
    needs `SHOW WAREHOUSES LIKE 'LINKML_METRICS_WH'`, which was not in the approved read].
  - **The running time, +2.8 percent.** The harness counts the blocks' windows (1.460 h). The warehouse also runs for
    the 60 s auto-suspend tail after each stop: 18:37:29 to 18:38:24, 18:57:18 to 18:57:58 and 20:03:09 to 20:04:04
    [measured].
- **The whole stage, +9.3 percent**, below the owner's 10 percent. The guardrail credits add 2.4 percent of the AI
  Credits.

Thresholds:
- **The owner's 10 percent:** passed for the stage (+9.3 percent) and for the agent credits (0.0 percent). Exceeded by
  the warehouse (+38.9 percent), explained above.
- **The 15 percent rule of `eval/campaign.md`** compares `guard.spent_credits` with the billed AI Credits: 0.0 percent,
  so `RATES` is not recalibrated. The warehouse term of the same guard is 38.9 percent off. The constant behind it,
  `WAREHOUSE_CREDITS_PER_HOUR`, is outside `RATES`.
- **Proposal, not applied:** `RATES` per token unchanged. `WAREHOUSE_CREDITS_PER_HOUR` 1.0 to 1.35, and 60 s added at each
  stop of the warehouse: the end of a segment followed by a gap longer than the 60 s auto-suspend, and the last segment.
  A guardrail term of about 0.35 credits per million guardrail tokens, read from each call's usage (`model_role`
  guardrail). On stage 1 these terms give 12.08 + 0.29 AI Credits (24.74 USD) and (1.460 + 3 x 60 s) h x 1.35 = 2.04
  warehouse credits (7.95 USD): about 32.69 USD, against the 32.65 billed. This is a harness change, applied only after
  the owner's go.

What D060 leaves for stage 2: about 90 USD, less the stage 1 bill (32.65), the drill (8) and the reserve (5), gives
**44.35 USD**. If the spending since the freeze is also taken off, as `eval/campaign.md` does (the pytest incident,
about 0.6 USD), it is 43.75 USD [inferred: arithmetic on measured bills].

## 9. Owner's manual decisions and the regrade (2026-10-07)

`eval/manual_decisions.yaml` adds the owner's rule `EXPECTED_FIGURE_ASSERTED_TRAP_FRAMED`: correct when the answer
asserts the expected figure as its answer and frames any trap figure explicitly as history, a hypothesis or a rejected
alternative; wrong when two figures are offered as candidate answers or no figure is given.
`WRONG_VALUE_CITED_AS_HISTORY` is kept. Decisions, by the request id of each turn's last call:

| Configuration | Question | Verdict | Rule | The sentence |
|---|---|---|---|---|
| A | T2 | correct | trap framed | "If they were meant to be 100 each, coverage would be 5.0 months" (hypothesis) |
| A | T9 | correct | trap framed | "the 350 packs held in May would have lasted 3.5 months, but that stock is no longer on hand in June" (rejected) |
| A | CS_LAST_MONTH_GAP | correct | history | "April and May are not added or carried forward." |
| B1 | T4 | correct | trap framed | grader false positive: 7.714 rounded to 0 decimals matched "after 8 months", a count of forecast months; 8.5 is the only coverage given |
| B1 | CS_LAST_MONTH_GAP | correct | history | "It did hold stock earlier in the quarter: 400 kg at the end of April and 350 kg at the end of May." |
| D′ | T2 | correct | trap framed | "The two zero-demand months stretch the cover from 5 months to 7." (rejected alternative) |
| D′ | T7 | wrong | trap framed | no figure: "I can't give you the coverage figure, because I couldn't run the coverage script." |

Regraded with `eval/campaign.py grade --stage 1`, no grader change. 144 turns: 100 correct, 44 wrong, 0 manual
[measured]:

| | A | B1 | B2 | C | D | D′ |
|---|---|---|---|---|---|---|
| correct / wrong | 16 / 8 | 13 / 11 | 15 / 9 | 24 / 0 | 17 / 7 | 15 / 9 |
| Figure only (owner, 2026-10-07), correct / wrong | 19 / 5 | 19 / 5 | 19 / 5 | 24 / 0 | 20 / 4 | 19 / 5 |

The figure-only score is the same grader without the unit half of `basis_wording`; "basis not named" still fails
(A S_STOCKOUT_COUNTRY stays wrong). The primary verdict is the score of record and the gate reads it alone
[measured, `eval/campaign.py grade --stage 1`].

## 10. Gate (2026-10-07)

`python eval/gate.py <grades> --force CS_LAST_MONTH_GAP --force T9 --forced-by "owner, 2026-10-07"`. It ran on the
regraded stage 1, with the gate fixes of the owner: 0.5 percent on EUR amounts, and no basis difference when every
configuration is correct. It wrote `eval/stage2.yaml` [measured]:
- **discriminating (16):** T1, T2, T7, T7_R1, T8, NO_DEMAND, BEYOND_H, BULK_SCOPE, DIM_MIX, T9, CS_LAST_MONTH_GAP
  (forced, no reason of its own), BULK_SCOPE_DRILL, G1, S_STOCKOUT_COUNTRY, S_FIRST_WORLD, S_DORMANT_VALUE. T9 is
  forced and also selected on its own failures (B1, B2, D, D′).
- **drop_order:** G1 only (selected on D′'s month alone).
- **not selected:** CS_FAMILY, CS_MIDDLE_MONTH_GAP, G2, S_OWN_UNIT, T3, T4, T5, T6.
  - G2 left on the EUR tolerance (the largest rounding gap was A's, 0.24 percent).
  - S_OWN_UNIT, T3 and T4 left on the basis rule. T4's only remaining reason was basis wording once B1 T4 was decided
    correct.

`eval/campaign.py plan --stage 2` has no A block. Order D, C, D′, B2, B1; 340 graded turns, 471 REST calls expected.

| Block | Graded turns | REST calls expected | Block cap |
|---|---|---|---|
| D | 44 | 45 | 50 |
| C | 84 | 85 | 94 |
| D′ | 84 | 211 (2.5 per question) | 233 |
| B2 | 84 | 85 | 94 |
| B1 | 44 | 45 | 50 |

D′ worst case at 4 calls on every turn: 337 calls, above its cap of 233. The cap stops the block before that.

## 11. Stage 2 sizing from the billed costs (2026-10-07) [inferred from measured costs]

Basis of the estimates:
- **Per turn:** the billed AI Credits of the stage 1 graded turns of each configuration, plus the guardrail (0.2909
  credits over 188 calls) and the warehouse per turn of its stage 1 block at 1.35 credits an hour.
- **Turns:** a gate question adds 4 turns on B2, C and D′ and 2 on B1 and D. A held-out question has 5 and 3.
- **Fixed cost:** five warm-ups and a quarter hour of gaps, 2.46 USD.
- **No A.**

Per turn, USD, all costs included:

| | B2 | C | D′ | B1 | D |
|---|---|---|---|---|---|
| Median turn | 0.263 | 0.077 | 0.247 | 0.148 | 0.261 |
| Mean turn | 0.258 | 0.102 | 0.259 | 0.148 | 0.313 |
| Mean of the three selection questions (S_*) | 0.328 | 0.093 | 0.406 | 0.172 | 0.748 |

The tail is in D (mean 0.313 against median 0.261, and 0.748 on the selection questions) and in D′ on the selection
questions.

Per gate question in stage 2, USD. Its own stage 1 costs, or every turn at the configuration's median or mean:

| Question | Own | Median | Mean |
|---|---|---|---|
| T1 | 3.11 | 3.17 | 3.40 |
| T2 | 2.96 | 3.17 | 3.40 |
| T7 | 3.69 | 3.17 | 3.40 |
| T7_R1 | 3.56 | 3.17 | 3.40 |
| T8 | 3.09 | 3.17 | 3.40 |
| NO_DEMAND | 3.02 | 3.17 | 3.40 |
| BEYOND_H | 3.13 | 3.17 | 3.40 |
| BULK_SCOPE | 3.25 | 3.17 | 3.40 |
| DIM_MIX | 3.08 | 3.17 | 3.40 |
| T9 (forced) | 3.07 | 3.17 | 3.40 |
| CS_LAST_MONTH_GAP (forced) | 3.35 | 3.17 | 3.40 |
| BULK_SCOPE_DRILL | 3.63 | 3.17 | 3.40 |
| G1 (drop_order) | 3.25 | 3.17 | 3.40 |
| S_STOCKOUT_COUNTRY | 5.02 | 3.17 | 3.40 |
| S_FIRST_WORLD | 5.80 | 3.17 | 3.40 |
| S_DORMANT_VALUE | 4.62 | 3.17 | 3.40 |
| **16 questions** | **57.6** | **50.7** | **54.4** |

The held-out questions Q1 to Q4 were never asked, so they have no cost of their own:

| Held-out questions, USD | Median turns | Mean turns | Selection-question turns |
|---|---|---|---|
| Per question | 4.16 | 4.48 | 6.89 |
| **Q1 to Q4** | **16.65** | **17.90** | **27.57** |

Stage 2 in all, the 16 gate questions, Q1 to Q4 and the fixed cost: **69.8 USD** (median), **74.7 USD** (mean), **87.7
USD** (own costs, with the held-out questions at the selection-question cost).

How many gate questions fit. Cut 3 removes `drop_order` (G1 only). Cuts 1 and 2 change nothing at these repetitions:

| Ceiling | Q1 to Q4 + fixed (median / mean / heavy) | 15 questions after cut 3 (median / mean / own) | Gate questions that fit, at the average question cost (median / mean / heavy) |
|---|---|---|---|
| 40 USD | 19.1 / 20.4 / 30.0 | 66.6 / 71.3 / 84.4: does not fit | 6 / 5 / 2 |
| 44.35 USD (D060: 90 − 32.65 − 8 − 5) | 19.1 / 20.4 / 30.0 | does not fit | 7 / 7 / 3 |
| 60 USD | 19.1 / 20.4 / 30.0 | does not fit | 12 / 11 / 8 |

Reading:
- No ceiling up to 60 USD holds the 15 questions left after cut 3.
- `drop_order` is exhausted after G1, so a further cut needs an order from the owner. The table gives each question's
  cost to choose one.
- The held-out questions fit under each ceiling at every cost assumption: about 17 to 28 USD.

D′ block:
- 84 turns. Cap (1 + 2.5 x 84) x 1.1 = 233 calls.
- Measured 0.0349 AI Credits per call: 0.087 per turn at 2.5 calls, 0.140 at 4.
- The D′ block costs about 21.7 USD at 2.5 calls a turn and 34.8 USD at 4 calls a turn (worst case). The cap of 233
  calls stops it at about 2.8 calls a turn on average.

## 12. Regrade under rubric 3.3 (session 9c, 2026-10-07)

Rubric 3.3 (owner, 2026-10-07, after the campaign; `eval/rubric.yaml`, commit 6449786): (a) the unit half of
`basis_wording` reads a product name of DIM_ITEM without its pack size, so "Oat cereal bar 1 kg" next to the word
coverage is no unit of the coverage; (b) a count of elapsed forecast months ("after 8 months") is no coverage
candidate (finding 100); (c) nothing else changes, so the unit of the stock or of the stock value beside the coverage
still fails. `eval/manual_decisions.yaml` applies unchanged. Regraded with `eval/campaign.py grade --stage 1 --rubric
3.3`, no call, on the same 144 turns; the grader under 3.2 reproduces the record of section 9 turn by turn, verdicts
and criteria. Compared with `eval/rubric_compare.py` [measured].

| Configuration | Primary 3.2 | Primary 3.3 | Figure only (3.2 and 3.3) |
|---|---|---|---|
| A | 16 / 8 | 18 / 6 | 19 / 5 |
| B1 | 13 / 11 | 16 / 8 | 19 / 5 |
| B2 | 15 / 9 | 18 / 6 | 19 / 5 |
| C | 24 / 0 | 24 / 0 | 24 / 0 |
| D | 17 / 7 | 18 / 6 | 20 / 4 |
| D′ | 15 / 9 | 18 / 6 | 19 / 5 |
| **All** | **100 / 44** | **112 / 32** | **120 / 24** |

Correct / wrong; no manual verdict under either rubric. The figure-only score does not move: 3.3 changes only the unit
half of `basis_wording`, which that score leaves out, and B1 T4, the only turn (b) touches, was already correct
[measured].

Every verdict that changes, wrong to correct, all on (a); 3.2 failed the sentence quoted, 3.3 passes the turn [measured]:

| Configuration | Question | The sentence 3.2 failed | Under 3.3 |
|---|---|---|---|
| A | NO_DEMAND | "Stock coverage for SKU-H09 (Iced tea summer edition 1 L, discontinued) in Belgium at June 2026 can't ..." | no coverage figure: `basis_wording` does not apply |
| A | T8 | "The stock coverage of Cashew nuts 1 kg (SKU-H08, a STANDARD item) in the Netherlands as of June 2026 is **0 months**." | basis named, pass |
| B1 | NO_DEMAND | "The stock coverage of Iced tea summer edition 1 L (SKU-H09) in Belgium as of June 2026 is undefined." | does not apply |
| B1 | T2 | "As of June 2026, the stock coverage of Salted almonds 1 kg (SKU-H03) in Germany is 7.0 months." | pass |
| B1 | T8 | "The stock coverage of Cashew nuts 1 kg (SKU-H08) in the Netherlands as of June 2026 is 0 months." | pass |
| B2 | BEYOND_H | "The stock coverage of Arabica beans 1 kg (SKU-H10) in Poland at the June 2026 analysis ..." (after the glued fragment "Try with the semantic model flag.") | pass |
| B2 | NO_DEMAND | "For Belgium (BE) in June 2026, stock coverage for SKU-H09 (Iced tea summer edition 1 L, discontinued) is **undefined**." | does not apply |
| B2 | T9 | "Stock coverage for oat cereal bar 1 kg (SKU-H11) in Switzerland at June 2026 is 0 months." | pass |
| D | NO_DEMAND | "Stock coverage for Iced tea summer edition 1 L (discontinued) (SKU-H09) in Belgium as of June 2026 is undefined." | does not apply |
| D′ | BEYOND_H | "Stock coverage for arabica beans 1 kg (SKU-H10) in Poland as of June 2026 is **50.0 months**." | pass |
| D′ | NO_DEMAND | "Stock coverage for SKU-H09 (iced tea summer edition 1 L, discontinued) in Belgium as of June 2026 is undefined." | does not apply |
| D′ | T9 | "The stock coverage of oat cereal bar 1 kg (SKU-H11) in Switzerland as of June 2026 is **0.0 months**." | pass |

Criteria that move without moving a verdict [measured]:
- B1 T4: `numeric` was manual (the trap 7.714 rounded to 0 decimals matched "after 8 months") and correct by the
  owner's decision; under 3.3 the number decides it ("expected 8.5 given") and no decision is applied.
- B1 T9 stays wrong: its product-name sentence passes, and the next one fails as in 3.2, "The figures are in kg, for
  the whole of Switzerland with no lot or warehouse filter."

What 3.3 leaves as it was, by (c) [measured; the reading inferred]: A BEYOND_H and C T2 pass the naming half of
`basis_wording` (QTY_EQ named) only through the "1 kg" of the product name; the answers name the item's own unit
(PACK_1000, "packs"). The rubric text accepts the item's own unit for one item, the grader reads the question's basis
only. Neither verdict moves under either rubric; whether the naming half should also read the name without its pack
size is the owner's question.
