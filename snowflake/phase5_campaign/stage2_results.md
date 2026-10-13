# Campaign stage 2 results, reduced (session 9b, 2026-10-07)

The owner's reduced stage 2 (`eval/stage2_reduced.yaml`, `eval/campaign.md` "Stage 2, reduced"): C and B2 only, 30
graded turns each, through `eval/campaign.py run --stage 2 --plan reduced --ceiling-usd 15` as LINKML_SVC, budget
`campaign`, `--streams 1`, blocks C then B2. Graded with `eval/grade.py`, rubric 3.2, plus the stage 2 grader of commit
2dff2d2 (route both, the two halves of N1 and N2), committed before the first call. Stage 1 stays the article's table for
the six configurations (`stage1_results.md`). Raw logs, events, traces, grades and the state file are outside the
repository (`linkml-metrics-runs/campaign/`, `run_stage2.log`, `grades_campaign-s2.json`, `report_s2.json`). Tables
from `python eval/stage2_report.py`. Tags: **[measured]**, **[documented]**, **[inferred]**.

## 1. Validity before reading

| Check | Result | Tag |
|---|---|---|
| Manifest | 60 graded turns, the planned 30 x 2; 62 REST calls (two warm-ups), every call status 200, no retry, no attempt beyond the first; no guard fired, the stage was never paused | measured |
| Window | client, 07:11:41 to 07:44:34 UTC; block C 07:11:41 to 07:24:03, block B2 07:24:05 to 07:44:34 | measured |
| Declared version | read before each block: C VERSION$6, B2 VERSION$8, the frozen state | measured |
| Served version | all 60 turns served by their frozen version, read per call from their own trace rows (`ai.observability.record_id`): C VERSION$6, B2 VERSION$8 | measured |
| Traces | read 80 s after the last call, readable at once: C 268 rows, B2 515; no foreign row, no turn without a row of its own, no request id without rows; rows per turn C 5 to 12, B2 5 to 31 | measured |
| Skill pre-check | passed (SKILLS_D, SKILLS_DP unchanged; D and D′ not played) | measured |
| Single provenance, instrument | rubric 3.2 and the grader unchanged from commit 2dff2d2 to the grades; stage 1 regraded with that grader is identical to its earlier grades, turn by turn | measured |
| Frozen objects | no change to an agent spec, instruction, tool, view, procedure, contract or charter during the session | measured (git) |

## 2. Verdicts by route group (route C is expected to take)

Primary verdict (rubric 3.2), correct / wrong / manual, per repetition. Figure only beside it (rubric 3.2 less the unit
half of `basis_wording`). No manual verdict in the stage [measured].

| Route group | C r1 | C r2 | B2 r1 | B2 r2 |
|---|---|---|---|---|
| procedure (coverage, Q1 to Q4, N3) | 3 / 2 / 0 | 14 / 1 / 0 | 5 / 0 / 0 | 6 / 9 / 0 |
| view only (CS_LAST_MONTH_GAP, CS_MIDDLE_MONTH_GAP, CS_FAMILY, G1, G2) | | 5 / 0 / 0 | | 5 / 0 / 0 |
| both (N1, N2) | 2 / 0 / 0 | 2 / 0 / 0 | 1 / 1 / 0 | 2 / 0 / 0 |
| no tool (T6) | | 1 / 0 / 0 | | 1 / 0 / 0 |
| **Total** | **5 / 2 / 0** | **22 / 1 / 0** | **6 / 1 / 0** | **14 / 9 / 0** |
| Figure only, total | 6 / 1 / 0 | 23 / 0 / 0 | 7 / 0 / 0 | 18 / 5 / 0 |

C 27 of 30 (figure only 29); B2 20 of 30 (figure only 25) [measured].

Routing: 30 of 30 for each configuration. C called the procedure and its semantic view in every N1 and N2 turn (route
both, 4 of 4); B2 answered both halves from its view [measured].

### The failed turns

| Configuration | Question | Rep | Criterion | Reading | Tag |
|---|---|---|---|---|---|
| C | H_STOCKOUT_2027 | 1 | item_set | Gives the count (35), the stock-out months and the members set apart, and says "The table lists each item"; no table was emitted (no `response.table` event, no table block in the final response), so no product is named. Agent behaviour, not a harness event | measured (events) |
| C | H_LOWEST_COUNTRY | 1 | basis_wording | "It has about 2.16 months of coverage, from 82,070 kg of stock." PL and 2.16 right; the wording rule reads the kg of the stock as a unit of the coverage | measured; the reading inferred |
| C | NO_DEMAND | 2 | basis_wording | "Stock coverage for SKU-H09 (iced tea summer edition 1 L) in Belgium as of June 2026 is undefined." The pack size in the product name, within 40 characters of "coverage", fires the 3.1 number-and-unit pattern | measured; the reading inferred |
| B2 | N2 | 1 | basis_wording | "Closing stock for SNACK_BARS in Switzerland (CH) at the end of each month of Q2 2026, in kg:" A closing-stock sentence; "month" makes it read as a sentence about coverage. All figures right | measured; the reading inferred |
| B2 | BEYOND_H | 2 | basis_wording | "...The stock coverage of Arabica beans 1 kg (SKU-H10) in Poland is about 50 months..." The product name's pack size, as C NO_DEMAND; the answer also starts with a planning fragment ("Use aliases with the __ prefix.") | measured; the reading inferred |
| B2 | T9 | 2 | basis_wording | "Stock coverage for Oat cereal bar 1 kg (SKU-H11) in Switzerland at the June 2026 analysis month is 0 months." The same pattern | measured; the reading inferred |
| B2 | NO_DEMAND | 2 | basis_wording | "Stock coverage for iced tea summer edition 1 L (SKU-H09) in Belgium cannot be calculated for June 2026." The same pattern | measured; the reading inferred |
| B2 | S_DORMANT_VALUE | 2 | basis_wording | "Item–country pairs with >12 months coverage, June 2026 (stock value in EUR)". Names the unit of the stock value | measured; the reading inferred |
| B2 | S_FIRST_WORLD | 2 | selection_rows, basis_wording | The members set apart (SKU-H08, SKU-H11 out of stock; SKU-H09 no demand) not named; "Coverage here is in kg or L equivalent", a coverage stated in a unit | measured |
| B2 | S_STOCKOUT_COUNTRY | 2 | selection_rows | The right four products, in a table of stock and three-month forecast with no coverage figure; the answer warns that items with no June stock "may be missing" | measured |
| B2 | T7 | 2 | numeric, basis_wording | 3.0, the naive join on the duplicated item (H-B2-1 class) | measured |
| B2 | T7_R1 | 2 | refusal | Rows by lifecycle status, 2.25 and 6.0: the fan-out persists | measured |
| B2 | N3 | 2 | item_set | Five products instead of ten, with a sixth named as "next" | measured |

Seven of the thirteen failures are the wording rule alone (C 2, B2 5); the figure-only score keeps them correct. Each of
the seven sentences either states the unit of the stock or of the stock value rather than of the coverage, or carries
a pack size in a product name next to the word coverage. S_FIRST_WORLD's "Coverage here is in kg or L equivalent" is
the rule's own case, and that turn fails on its rows as well. The rule is rubric 3.2 as written; no grader change, the owner's question after the campaign
(`docs/phase5_notes.md` part 3) [the reading inferred].

## 3. C over both stages

Correct of trials on the questions C played in stage 2, stage 1 (r1) and stage 2 (r2) together [measured]:

| | Questions | Trials | Correct | Wrong | Exact one-sided 95 percent upper bound of the error rate |
|---|---|---|---|---|---|
| Seen questions (the 16 gate questions and G2, CS_FAMILY, CS_MIDDLE_MONTH_GAP, T6), primary | 20 | 40 | 39 | 1 (NO_DEMAND r2, wording) | none: one failure |
| The same, figure only | 20 | 40 | 40 | 0 | **7.2 percent** (1 − 0.05^(1/40)) |
| Never seen (Q1 to Q4, N1 to N3), primary | 7 | 10 | 8 | 2 | none |
| The same, figure only | 7 | 10 | 9 | 1 (H_STOCKOUT_2027) | none |

B2 for comparison: seen 23 of 40 (figure only 31), never seen 8 of 10 [measured]. Reading: on the figures, C did not
fail a seen question in 40 trials, which bounds its failure rate on them below 7.2 percent at 95 percent; the primary
score of record has one failure, a wording-rule hit on a correct answer [inferred from the measured counts].

## 4. The never-seen questions, reported apart

Primary / figure only [measured]:

| Question | C r1 | C r2 | B2 r1 | B2 r2 |
|---|---|---|---|---|
| Q1 H_LOCAL_STOCKOUT | correct / correct | | correct / correct | |
| Q2 H_LOWEST_COUNTRY | wrong / correct | | correct / correct | |
| Q3 H_STOCKOUT_2027 | wrong / wrong | | correct / correct | |
| Q4 H_STOCKOUT_ES | correct / correct | | correct / correct | |
| N1 (both) | correct / correct | correct / correct | correct / correct | correct / correct |
| N2 (both) | correct / correct | correct / correct | wrong / correct | correct / correct |
| N3 | correct / correct | correct / correct | correct / correct | wrong / wrong |

B2 states on 18 of its 30 answers that the view's coverage metric did not run and that it computed the coverage itself
(N2, N3, Q2, Q4, T2, T8, T9, BULK_SCOPE and its drill among them), and gets most of those figures right [measured on the
answer text; the SQL itself not inspected for this count]. This is H-B2-6 of the charter (the model rewrites coverage
instead of selecting the metric), observed in the answers.

## 5. Governance measures (never part of the verdict)

| Measure | C | B2 | Tag |
|---|---|---|---|
| Warnings relayed, the 5 turns that carry warnings (T2, T7, BEYOND_H, BULK_SCOPE, its drill) | 5 yes | 5 no | measured |
| FRESHNESS_STATED present / latest | 29 / 29 of 30 | 30 / 30 | measured |
| ROWS_COMMENTED | 0 | 0 | measured |
| Answers starting with a planning fragment glued to the first sentence | 0 | 5 | measured |

## 6. Latency and cost

Client seconds per graded turn (the sum of its REST calls) [measured]:

| | Median | p90 | Min | Max |
|---|---|---|---|---|
| C | 17.5 | 23.7 | 4.9 | 24.3 |
| B2 | 30.1 | 50.8 | 6.8 | 87.2 |

Harness estimate (the guard's, `state_campaign-s2.json`) [measured estimate]:

| Item | Value |
|---|---|
| AI Credits (orchestration tokens at `RATES`, which matched the billed credits to 0.0 percent in stage 1) | 4.58 credits, 9.16 USD: C 1.137 graded + 0.091 warm-up; B2 3.260 graded + 0.093 warm-up |
| Per graded turn | C 0.038 credits (stage 1 billed mean 0.032); B2 0.109 (stage 1 0.102). C's largest turns are N1 and N2 (0.076 to 0.080), two tool calls each |
| Warehouse (blocks' windows at 1.0 credit an hour) | 0.547 h, 2.13 USD |
| **Estimate** | **11.29 USD against the 15 USD ceiling** (pause at 13.5 never reached); the reduced plan's mean projection was 11.69, the guard projection 10.36 |
| Billed, expected | about 12.4 USD: the warehouse at the measured 1.35 credits an hour plus two 60 s auto-suspend tails (about 3.1 USD) and the guardrail (about 0.2 USD) [inferred from stage 1's measured gaps] |

Billed: 12.28 USD, read on 2026-10-07 (section 7).

## 7. Cost read for the stage 2 window (billed, read 2026-10-07)

Run on the owner's go (session 9c), at 11:11 UTC, more than 3 hours after the last call (07:44:34 UTC). ACCOUNTADMIN for
this read-only batch only, the statements below exactly as written before the read (extracted from this file and run
with `snow sql -f`), output outside the repository (`linkml-metrics-runs/campaign/cost_read_s2.json`, the join in
`cost_join_s2.json`). The 62 request ids are in `calls.json` and the summaries; the rows are matched by request id
after the read. Prices: AI Credit 2.00 USD, warehouse credit 3.90 USD (decision 3, `eval/campaign.md`).

```sql
USE ROLE ACCOUNTADMIN;
USE SECONDARY ROLES NONE;

-- S1. Agent usage of the stage 2 window, one row per request (matched by REQUEST_ID to the 62 calls after the read).
SELECT START_TIME, END_TIME, REQUEST_ID, AGENT_NAME, USER_NAME, TOKEN_CREDITS, TOKENS, CREDITS_GRANULAR
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY
WHERE USER_NAME = 'LINKML_SVC'
  AND START_TIME >= '2026-10-07 07:05:00 +00:00'::TIMESTAMP_TZ
  AND START_TIME <  '2026-10-07 07:50:00 +00:00'::TIMESTAMP_TZ
ORDER BY START_TIME;

-- S2. The day's metering by service (USAGE_DATE in UTC): CORTEX_AGENTS against S1, CORTEX_AI_GUARDRAILS, WAREHOUSE_METERING.
SELECT SERVICE_TYPE, CREDITS_USED_COMPUTE, CREDITS_USED_CLOUD_SERVICES, CREDITS_USED, CREDITS_BILLED
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY
WHERE USAGE_DATE = '2026-10-07'
ORDER BY SERVICE_TYPE;

-- S3. Warehouse metering, the hour that holds the window (07:00 to 08:00 UTC; it also holds the trace read at 07:45:55).
SELECT START_TIME, END_TIME, CREDITS_USED_COMPUTE, CREDITS_USED_CLOUD_SERVICES, CREDITS_USED
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE WAREHOUSE_NAME = 'LINKML_METRICS_WH'
  AND START_TIME >= '2026-10-07 07:00:00 +00:00'::TIMESTAMP_TZ
  AND START_TIME <  '2026-10-07 08:00:00 +00:00'::TIMESTAMP_TZ
ORDER BY START_TIME;

-- S4. Warehouse running time in the same hour (resume and suspend events: the running seconds of the stage).
SELECT TIMESTAMP, EVENT_NAME, EVENT_REASON, EVENT_STATE, CLUSTER_NUMBER
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_EVENTS_HISTORY
WHERE WAREHOUSE_NAME = 'LINKML_METRICS_WH'
  AND TIMESTAMP >= '2026-10-07 07:00:00 +00:00'::TIMESTAMP_TZ
  AND TIMESTAMP <  '2026-10-07 08:00:00 +00:00'::TIMESTAMP_TZ
ORDER BY TIMESTAMP;
```

What the read decides: the billed AI Credits against the harness's 4.58 (S1, by request id), whether 2026-10-07 had
agent use outside the stage (S2 `CORTEX_AGENTS` against the sum of S1), the guardrail credits of the day (S2), and the
warehouse share of the stage (S3 and S4, the running seconds inside the window at the measured rate). The stage 1
read of 2026-10-07 and this session's account reads also fall on that day, on the warehouse and cloud services only.

### Validity of the read

| Check | Result | Tag |
|---|---|---|
| Billed rows against the runner's calls | S1: 62 rows, agents LINKML_C and LINKML_B2 only. Each row matched by request id to one call of `calls.json`; no row and no call left without a match | measured |
| Other agent use that day | `CORTEX_AGENTS` for 2026-10-07 (S2): 4.579960255 credits, equal to the sum of S1. The day had no other agent use, so the day's guardrail credits are the stage's | measured |
| The harness's pricing | each call's orchestration tokens at `RATES` (`eval/guards.py`) give its billed `TOKEN_CREDITS` to within 3e-17 credit, and its input plus output tokens equal the billed `TOKENS`, on all 62 calls | measured |
| Warehouse rows | S3: one hourly row, 07:00 to 08:00 UTC. S4: two runs, 07:11:44 to 07:45:22 (the stage) and 07:45:59 to 07:47:01 (the trace read, excluded) | measured |
| Daily warehouse row | `METERING_DAILY_HISTORY` has no `WAREHOUSE_METERING` row for 2026-10-07 yet (the day is not over), so the daily cloud-services adjustment cannot be read. S2 also shows `CORTEX_SEARCH`, 0.000072 credits, which no harness object uses (not read further) | measured |

### Billed against the estimate, per configuration

| | C | B2 | Stage 2 |
|---|---|---|---|
| REST calls (graded turns + warm-up) | 31 (30 + 1) | 31 (30 + 1) | 62 |
| Agent AI Credits, billed = estimated | 1.2274 (2.45 USD) | 3.3525 (6.71 USD) | 4.5800 (9.16 USD) |
| Of which graded turns / warm-up | 1.1368 / 0.0906 | 3.2598 / 0.0927 | 4.3967 / 0.1833 |
| Per graded turn, median / mean / max | 0.0251 / 0.0379 / 0.0802 (N1 r1) | 0.1093 / 0.1087 / 0.2327 (N3 r1) | |
| Guardrail AI Credits, billed (not estimated) | 0.0275 (0.06 USD), 78,659 tokens | 0.0570 (0.11 USD), 162,950 tokens | 0.0846 (0.17 USD) |
| Warehouse, estimated (block window x 1.0) | 0.2059 credits (0.80 USD) | 0.3413 (1.33 USD) | 0.5472 (2.13 USD) |
| Warehouse, billed (running seconds x 1.3505) | 739 s, 0.2773 credits (1.08 USD) | 1,279 s, 0.4798 (1.87 USD) | 2,018 s, 0.7571 (2.95 USD) |
| **Estimated** | **3.26 USD** | **8.04 USD** | **11.29 USD** |
| **Billed** | **3.59 USD** | **8.69 USD** | **12.28 USD** |
| Gap | +10.2 percent | +8.1 percent | **+8.7 percent** |

Measured, except the warehouse split between the blocks [inferred]: the run is cut at the end of block C (07:24:03); the
2.6 s between the blocks and the tail after the last call go to B2. Split of the agent credits (`CREDITS_GRANULAR`,
all `claude-sonnet-5-5`): cache write 2.69 (58.7 percent), cache read 1.22 (26.7 percent), output 0.67 (14.6 percent),
uncached input 0.001 [measured].

### Billed against the estimate, per component

| Component | Estimated | Billed | Gap |
|---|---|---|---|
| Agent AI Credits | 4.5800 (9.16 USD) | 4.5800 (9.16 USD) | **0.0 percent** |
| Guardrail AI Credits | not counted | 0.0846 (0.17 USD) | +0.17 USD |
| Warehouse | 0.547 h x 1.0 = 0.5472 credits (2.13 USD) | 0.5606 h x 1.3505 = 0.7571 credits (2.95 USD) | **+38.4 percent**, +0.82 USD |
| **Stage 2** | **11.29 USD** | **12.28 USD** | **+8.7 percent**, +0.99 USD |

The gap explained, +0.99 USD in all [measured]:
- **Agent credits, 0.0 percent.** `RATES` are the billing rates, as in stage 1.
- **Guardrail, +0.17 USD.** Billed apart from the agent rows (`CORTEX_AI_GUARDRAILS`) and outside the harness: 59 of the
  62 calls carried a guardrail step (none on C's warm-up and on T6 of C and B2), 241,609 tokens, which the day total
  prices at exactly 0.350 credits per million tokens. Stage 1 inferred that rate from a day total; here the day holds
  only the stage, so it is measured.
- **Warehouse rate, +0.75 USD.** The warehouse bills 1.3505 credits per running hour (0.780375 compute credits over
  2,080 s of running time in the hour), against the 1.0 the harness assumes; stage 1 read 1.3506.
- **Warehouse time, +0.07 USD.** The warehouse ran 48 s longer than the blocks' windows: the 60 s auto-suspend tail
  after the last statement (the run stops at 07:45:22, the last call ended at 07:44:34). It resumed 2 s after the block
  started, so nothing ran before the window.
- **Cloud services: 0.0468 credits metered in the hour, not counted.** That is 6.0 percent of the hour's compute, under
  the 10 percent daily allowance; stage 1's daily row billed no cloud services at 3.2 percent. Not billed, expected
  [inferred: the daily row of 2026-10-07 was not written yet].

Against the expectation of section 6 (about 12.4 USD): 12.28, 1 percent under. The expectation added two 60 s tails
and a guardrail term of about 0.2 USD; one tail fell inside the stage (between the blocks the warehouse did not stop)
and the guardrail was 0.17 [measured against the inferred expectation].

### The campaign, both stages billed

| | Stage 1 (six configurations, 144 graded turns) | Stage 2 (C and B2, 60 graded turns) | Campaign |
|---|---|---|---|
| Agent AI Credits | 12.0816 (24.16 USD) | 4.5800 (9.16 USD) | 16.6616 (33.32 USD) |
| Guardrail AI Credits | 0.2909 (0.58 USD) | 0.0846 (0.17 USD) | 0.3755 (0.75 USD) |
| Warehouse credits | 2.0275 (7.91 USD) | 0.7571 (2.95 USD) | 2.7846 (10.86 USD) |
| **Billed** | **32.65 USD** | **12.28 USD** | **44.93 USD** |
| Harness estimate | 29.86 USD | 11.29 USD | 41.15 USD |
| Gap | +9.3 percent | +8.7 percent | +9.2 percent |

Stage 2 stayed under its 15 USD ceiling billed as well as estimated [measured]. The whole gap of the campaign is the
warehouse rate and tails and the guardrail, none of them in the harness; the agent credits match to the call. The
correction proposed after stage 1 (1.35 credits per running hour, 60 s per stop, a guardrail term at 0.35 credits per
million tokens) would have estimated stage 2 at 12.30 USD, 0.1 percent over the bill [inferred: the stage 1 proposal applied to stage 2's
measured windows and tokens].

## 8. Regrade under rubric 3.3 (session 9c, 2026-10-07)

Rubric 3.3 as in `stage1_results.md` section 12 (product-name pack sizes, elapsed month counts, nothing else).
Regraded with `eval/campaign.py grade --stage 2 --rubric 3.3`, no call, on the same 60 turns; the grader under 3.2
reproduces the record of section 2 turn by turn [measured].

| Configuration | Primary 3.2 | Primary 3.3 | Figure only (3.2 and 3.3) |
|---|---|---|---|
| C | 27 / 3 | 28 / 2 | 29 / 1 |
| B2 | 20 / 10 | 22 / 8 | 25 / 5 |

Correct / wrong; no manual verdict [measured].

By route group under 3.3, correct / wrong / manual; only the procedure group moves (section 2 for 3.2) [measured]:

| Route group | C r1 | C r2 | B2 r1 | B2 r2 |
|---|---|---|---|---|
| procedure | 3 / 2 / 0 | 15 / 0 / 0 | 5 / 0 / 0 | 8 / 7 / 0 |
| view only | | 5 / 0 / 0 | | 5 / 0 / 0 |
| both | 2 / 0 / 0 | 2 / 0 / 0 | 1 / 1 / 0 | 2 / 0 / 0 |
| no tool | | 1 / 0 / 0 | | 1 / 0 / 0 |

Every verdict that changes, wrong to correct, all on (a) [measured]:

| Configuration | Question | Rep | The sentence 3.2 failed | Under 3.3 |
|---|---|---|---|---|
| C | NO_DEMAND | 2 | "Stock coverage for SKU-H09 (iced tea summer edition 1 L) in Belgium as of June 2026 is undefined." | no coverage figure: `basis_wording` does not apply |
| B2 | NO_DEMAND | 2 | "Stock coverage for iced tea summer edition 1 L (SKU-H09) in Belgium cannot be calculated for June 2026." | does not apply |
| B2 | T9 | 2 | "Stock coverage for Oat cereal bar 1 kg (SKU-H11) in Switzerland at the June 2026 analysis month is 0 months." | basis named, pass |

Still failing on the wording rule, by (c) [measured]:
- C H_LOWEST_COUNTRY r1: "It has about 2.16 months of coverage, from 82,070 kg of stock."
- B2 N2 r1: "Closing stock for SNACK_BARS in Switzerland (CH) at the end of each month of Q2 2026, in kg:"
- B2 S_DORMANT_VALUE r2: "Item–country pairs with >12 months coverage, June 2026 (stock value in EUR)".
- B2 BEYOND_H r2: its product-name sentence now passes; the next fails, "The stock outlasts the 24-month horizon, so
  the coverage is extrapolated: 5,000 kg divided by the average non-zero month ...".

C over both stages under 3.3, the 20 seen questions it played in stage 2: **40 of 40 on the primary verdict**, as on
the figure-only score, so the exact one-sided 95 percent upper bound of 7.2 percent now holds on the score of record
too. Never seen: C 8 of 10 (H_LOWEST_COUNTRY on (c), H_STOCKOUT_2027 on its missing table), B2 8 of 10. B2 seen: 28
of 40 (3.2: 23), figure only 31 [measured].

Documented limits of rubric 3.3, frozen by the owner (2026-10-07), no change:
- Finding 128: the naming half of `basis_wording` reads a product name's "1 kg" as the basis named (C T2 r2, C T8 r2
  pass only that way); no verdict depends on it.
- Finding 129: counts of forecast months other than "after n months" ("the first 8 months", "within 3 months") stay
  coverage candidates; excluding them moves no verdict in either stage.
