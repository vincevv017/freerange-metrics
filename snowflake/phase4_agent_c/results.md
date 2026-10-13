# Agent C raw results (session 7, steps 3 to 5)

Agent `LINKML_METRICS.RAW.LINKML_C`, permanent, created by `deploy_agent.py create` from `generated/agent_c.yaml`
(contract 0.3.0) as LINKML_METRICS_ROLE, its owner. `DESCRIBE AGENT` returns a spec equal to the generated file
(compared key by key). No grant was added: LINKML_SVC holds LINKML_METRICS_ROLE only, which owns the agent and the
procedure and has USAGE on the warehouse.

Calls: `ask_questions.py` through `snowflake/probe_b/mount/run_call.py`, as **LINKML_SVC** (key-pair JWT, no role or
warehouse header), budget `c` (cap 15), policy `c`. **15 calls used, 15 status 200, no permission request, no
`response.warning`.** Orchestration model `claude-sonnet-5-5`. Raw events, traces and summaries stay outside the
repository (they carry the account host).

**UTC window of the agent calls: 2026-10-03 14:56:40.5 (call 1 sent) to 15:15:56.3 (call 15 answered).** Script
window, trace polling included: 14:56:36 to 15:16:57.

Expected answers: `generated/reference_questions.yaml` (asserted against the procedure by `tests/test_procedure.py`).
Each question asked once, in file order; the drill was asked in the thread of BULK_SCOPE, after T9 (the drill comes
last in the file). Question 15 is not in the file: a closing-stock question the coverage tool cannot answer, asked
only because every earlier call succeeded.

## Answers

| # | Id | Tool parameters (as sent) | Answer (numbers as given) | Correct? | Warnings relayed | As-of named |
|---|---|---|---|---|---|---|
| 1 | T1 | `["2026-06-01"]`, QTY_EQ, grain `family_code, country_code`, filters PANTRY_FLOUR, FR | 2.8 months, stock 1,400 against 12,000 | **yes** (2.8) | none returned, says none | yes |
| 2 | T2 | same shape, SKU-H03, DE | 7.0, stock 500 against 2,200 | **yes** (7.0) | FORECAST_GAPS_FILLED: "2 months … counted as zero demand" | yes |
| 3 | T3 | grain `sku_code`, filters SKU-H04, IT, batch_status RELEASED | 6.0, released stock 600 against 2,400 | **yes** (6.0) | none returned, says none | yes |
| 4 | T4 | SKU-H05, ES | 8.5, stock 1,000 against 2,580 | **yes** (8.5) | none returned, says none | yes |
| 5 | T5 | **QTY_EQ** (not RAW), PANTRY_PASTA, GB | "Coverage can't be given in packs … The tool used QTY_EQ instead": 2.4, stock 14,610.5 against 138,398.5 | **yes, with a deviation**: no number in packs and the reason given, but the refusal came from the LLM (the procedure's `UNIT_RAW_NOT_ADDITIVE` was not reached) and it answered in QTY_EQ instead of offering it. 2.4 is the expected alternative (2.37) | FORECAST_GAPS_FILLED: "5 member-months" | yes |
| 6 | T6 | **no tool call** | "Coverage is measured at one analysis month … Which month do you want? The latest available month is June 2026, and valid months run monthly from July 2023 to June 2026." | **yes** (clarifying question, no number; valid range given) | n/a | n/a |
| 7 | T7 | PANTRY_OIL, SE | 2.3 (rounded from 2.25 per the response instruction), stock 900 against 9,600 | **yes** (2.25, one decimal) | MASTER_DATA_DUPLICATES: "affecting 1 item … rows agree … figure not affected" | yes |
| 8 | T7_R1 | grain `lifecycle_status`, filters PANTRY_OIL, SE | Refusal relayed in business words, offers the SKU grain or the total | **yes** (`MASTER_DATA_FANOUT`), **but the reason it relays is wrong**: "recorded twice with conflicting lifecycle status, family and item type". Only `lifecycle_status` differs (ACTIVE / PHASE_OUT); the procedure's reason lists every column it checked (`{attributes}`), not the ones that differ | n/a | yes |
| 9 | T8 | SKU-H08, NL | 0.0, NO_STOCK, forecast 2,400 | **yes** | none returned, says none | yes |
| 10 | NO_DEMAND | SKU-H09, BE | no figure, NO_DEMAND, stock 500, forecast 0 | **yes** (null) | none returned, says none | yes |
| 11 | BEYOND_H | SKU-H10, PL | 50.0, BEYOND_HORIZON explained as an extrapolation | **yes** | FORECAST_GAPS_FILLED: "2 months" | yes |
| 12 | BULK_SCOPE | grain `family_code`, filters HOT_GROUND | 8.7, stock 55,238 against 147,906 | **yes** (8.67) | both: FORECAST_GAPS_FILLED "2 member-months"; DEFAULT_SCOPE_EXCLUDED "51,475.5 kg or L equivalent", with how to include it | yes |
| 13 | T9 | SKU-H11, CH | 0.0, NO_STOCK, forecast 2,400 | **yes** (not 3.5). Adds a stray sentence: "I couldn't check the product name … against the SKU code" | none returned, says none | yes |
| 14 | BULK_SCOPE_DRILL ("And by country?") | grain `country_code`, filters HOT_GROUND kept, **totals `[[]]`** | BE 11.4, DE 4.1, ES 1.9, FR 7.5, IT 8.7, SE 10.7; "The tool recomputed the all-country total at 8.7 months. It is not an average of the country rows." | **yes**: six rows equal to the reference (11.38, 4.12, 1.93, 7.49, 8.66, 10.72), no sum, total asked from the tool | both, with numbers | yes |
| 15 | CS_OUT_OF_SCOPE: "What was the closing stock of the oat cereal bar 1 kg (SKU-H11) in Switzerland for Q2 2026?" | **no tool call** | "The tool I have measures stock coverage … at one analysis month, not over a quarter. It doesn't return a plain closing stock number for a period." Offers June 2026 coverage for SKU-H11 x CH and asks which month | **yes**: no number, no tool call, the limit stated | n/a | n/a |

Every number the agent gave is a number the tool returned, rounded to one decimal; none was added or averaged.
The tool's answer carries the caller block: `LINKML_SVC`, `LINKML_METRICS_ROLE`, no secondary role, agent activated.

## Tokens and request ids

Orchestration input tokens are the sum of the LLM steps of the turn (planning and response on a tool turn, one
step otherwise). Guardrail model `cygnal-qwen3-8b-032026`, absent on turns without a tool call.

| # | Id | Started (UTC) | First byte s | Total s | Orchestration input (cache write / read) | Output | Guardrail input | Request id |
|---|---|---|---|---|---|---|---|---|
| 1 | T1 | 14:56:40.523 | 2.22 | 20.42 | 62,822 (25,307 / 37,505) | 497 | 4,967 | `00000237-0000-4000-8000-000000000237` |
| 2 | T2 | 14:58:06.184 | 0.89 | 16.95 | 63,152 (12,106 / 51,036) | 575 | 5,040 | `00000238-0000-4000-8000-000000000238` |
| 3 | T3 | 14:59:28.465 | 0.92 | 16.95 | 63,009 (12,014 / 50,985) | 563 | 4,979 | `00000239-0000-4000-8000-000000000239` |
| 4 | T4 | 15:00:50.819 | 0.84 | 17.29 | 62,896 (11,961 / 50,925) | 542 | 4,972 | `0000023a-0000-4000-8000-00000000023a` |
| 5 | T5 | 15:02:12.317 | 0.87 | 19.17 | 63,480 (12,311 / 51,159) | 781 | 5,041 | `0000023b-0000-4000-8000-00000000023b` |
| 6 | T6 | 15:03:37.032 | 0.82 | 4.73 | 31,468 (3,515 / 27,945) | 167 | n/a | `0000023c-0000-4000-8000-00000000023c` |
| 7 | T7 | 15:04:47.620 | 0.95 | 17.34 | 63,131 (12,105 / 51,016) | 567 | 5,039 | `0000023d-0000-4000-8000-00000000023d` |
| 8 | T7_R1 | 15:06:08.626 | 0.81 | 17.47 | 61,785 (11,407 / 50,368) | 514 | 4,511 | `0000023e-0000-4000-8000-00000000023e` |
| 9 | T8 | 15:07:30.723 | 1.76 | 20.15 | 63,064 (12,049 / 51,005) | 592 | 4,981 | `0000023f-0000-4000-8000-00000000023f` |
| 10 | NO_DEMAND | 15:08:56.539 | 0.94 | 17.50 | 62,931 (11,960 / 50,961) | 495 | 4,970 | `00000240-0000-4000-8000-000000000240` |
| 11 | BEYOND_H | 15:10:17.702 | 0.88 | 17.09 | 63,242 (12,159 / 51,073) | 581 | 5,064 | `00000241-0000-4000-8000-000000000241` |
| 12 | BULK_SCOPE | 15:11:40.887 | 0.72 | 18.30 | 62,457 (11,798 / 50,649) | 596 | 4,882 | `00000242-0000-4000-8000-000000000242` |
| 13 | T9 | 15:13:04.679 | 0.88 | 16.82 | 62,982 (12,015 / 50,957) | 559 | 4,987 | `00000243-0000-4000-8000-000000000243` |
| 14 | BULK_SCOPE_DRILL | 15:14:26.198 | 0.85 | 18.06 | 92,044 (22,379 / 69,655) | 670 | 6,345 | `00000244-0000-4000-8000-000000000244` |
| 15 | CS_OUT_OF_SCOPE | 15:15:50.248 | 0.81 | 6.06 | 31,571 (3,600 / 27,963) | 234 | n/a | `00000245-0000-4000-8000-000000000245` |

Probe C0, same model, hand-written spec: about 47,000 input tokens on a tool turn and 28,468 without. Agent C:
about 63,000 and 31,500. The tool's answer is about 12.7 KB, of which **10.8 KB (85%) is the `sql` block** (the
generated SQL text, returned for audit), and the 36-month list is another 0.6 KB.

## Latency per turn (`latency.py`, raw output)

Trace spans from `GET_AI_OBSERVABILITY_EVENTS`; CALL and child queries from `INFORMATION_SCHEMA.QUERY_HISTORY_BY_USER`
read as LINKML_SVC. Children: the queries of the CALL's session that start inside the CALL (Python start-up queries,
context, quality and coverage, two `RESULT_SCAN`).

| # | Id | Client s | Server s | Before planning s | Planning s | Tool span s | Response s | Suggested queries s | CALL elapsed ms (compile / queued) | Children: n, elapsed ms (compile) | Request id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | T1 | 20.42 | 18.93 | 1.32 | 2.35 | 8.7 | 4.39 | 2.15 | 8506 (640 / 80) | 10: 55 (53), 56 (54), 59 (58), 65 (63), 50 (48), 1041 (727), 1127 (1000), 818 (707), 68 (67), 74 (72) | `00000237-0000-4000-8000-000000000237` |
| 2 | T2 | 16.95 | 16.1 | 0.29 | 2.15 | 8.55 | 3.0 | 2.1 | 4732 (289 / 0) | 10: 50 (49), 49 (48), 48 (47), 80 (78), 48 (46), 285 (244), 976 (880), 678 (632), 75 (74), 75 (74) | `00000238-0000-4000-8000-000000000238` |
| 3 | T3 | 16.95 | 16.16 | 0.36 | 2.42 | 8.4 | 2.68 | 2.31 | 4574 (234 / 0) | 10: 49 (48), 48 (46), 46 (45), 56 (55), 45 (43), 290 (249), 1050 (949), 785 (725), 58 (57), 62 (60) | `00000239-0000-4000-8000-000000000239` |
| 4 | T4 | 17.29 | 16.5 | 0.32 | 2.15 | 8.72 | 2.83 | 2.46 | 5252 (284 / 0) | 10: 58 (57), 56 (55), 57 (56), 74 (73), 54 (52), 324 (280), 1420 (1322), 1080 (1031), 79 (77), 96 (94) | `0000023a-0000-4000-8000-00000000023a` |
| 5 | T5 | 19.17 | 18.31 | 0.29 | 4.1 | 8.56 | 3.46 | 1.89 | 6106 (241 / 0) | 10: 66 (64), 63 (61), 61 (59), 121 (119), 54 (52), 366 (322), 1285 (1178), 920 (856), 67 (66), 76 (75) | `0000023b-0000-4000-8000-00000000023b` |
| 6 | T6 | 4.73 | 4.01 | None | 0 | 0 | 2.16 | 1.54 | no CALL | n/a | `0000023c-0000-4000-8000-00000000023c` |
| 7 | T7 | 17.34 | 16.5 | 0.4 | 2.15 | 8.62 | 2.89 | 2.44 | 4836 (241 / 0) | 10: 51 (50), 51 (49), 54 (53), 72 (70), 63 (61), 305 (261), 886 (766), 724 (676), 61 (60), 64 (63) | `0000023d-0000-4000-8000-00000000023d` |
| 8 | T7_R1 | 17.47 | 16.63 | 0.27 | 2.71 | 8.61 | 3.33 | 1.71 | 4804 (358 / 0) | 9: 49 (47), 45 (44), 43 (42), 58 (56), 47 (46), 310 (266), 861 (741), 649 (599), 65 (64) | `0000023e-0000-4000-8000-00000000023e` |
| 9 | T8 | 20.15 | 19.37 | 1.26 | 3.58 | 9.14 | 3.12 | 2.26 | 5424 (876 / 0) | 10: 58 (57), 54 (52), 50 (49), 59 (58), 52 (50), 288 (245), 805 (699), 749 (691), 65 (64), 62 (61) | `0000023f-0000-4000-8000-00000000023f` |
| 10 | NO_DEMAND | 17.5 | 16.74 | 0.41 | 2.24 | 9.13 | 2.73 | 2.21 | 5204 (386 / 0) | 10: 77 (75), 57 (55), 67 (65), 84 (82), 55 (53), 321 (275), 890 (785), 805 (747), 75 (73), 65 (64) | `00000240-0000-4000-8000-000000000240` |
| 11 | BEYOND_H | 17.09 | 16.11 | 0.28 | 1.92 | 8.74 | 3.06 | 2.1 | 4956 (282 / 0) | 10: 55 (53), 47 (46), 63 (62), 82 (81), 57 (55), 247 (194), 829 (701), 639 (591), 81 (79), 68 (67) | `00000241-0000-4000-8000-000000000241` |
| 12 | BULK_SCOPE | 18.3 | 17.57 | 0.24 | 2.16 | 8.42 | 3.95 | 2.8 | 4691 (250 / 0) | 10: 46 (45), 48 (46), 47 (45), 69 (68), 52 (50), 225 (181), 722 (609), 512 (473), 59 (58), 71 (70) | `00000242-0000-4000-8000-000000000242` |
| 13 | T9 | 16.82 | 15.96 | 0.32 | 2.11 | 8.5 | 3.03 | 1.99 | 4724 (242 / 0) | 10: 56 (54), 48 (46), 54 (53), 71 (69), 51 (50), 240 (198), 707 (602), 639 (580), 69 (68), 65 (63) | `00000243-0000-4000-8000-000000000243` |
| 14 | BULK_SCOPE_DRILL | 18.06 | 17.23 | 0.29 | 2.36 | 8.52 | 3.5 | 2.54 | 5456 (228 / 0) | 10: 45 (44), 669 (667), 65 (63), 75 (74), 52 (51), 240 (188), 789 (686), 889 (809), 94 (93), 78 (76) | `00000244-0000-4000-8000-000000000244` |
| 15 | CS_OUT_OF_SCOPE | 6.06 | 5.32 | None | 0 | 0 | 3.5 | 1.54 | no CALL | n/a | `00000245-0000-4000-8000-000000000245` |

### Medians over the 13 tool turns

| Part | Median | Range |
|---|---|---|
| Client total | 17.47 s | 16.82 to 20.42 |
| Before planning (request to first planning span) | 0.32 s | 0.24 to 1.32 |
| Planning (one step) | 2.24 s | 1.92 to 4.10 |
| **Tool span** | **8.61 s** | 8.40 to 9.14 |
| of which the CALL (query history) | 4.96 s | 4.57 to 8.51 (T1, first call) |
| **of which after the CALL ends** | **3.78 s** | 0.19 (T1) to 3.93 |
| Response generation | 3.06 s | 2.68 to 4.39 |
| Suggested queries (after the response, before the stream ends) | 2.21 s | 1.71 to 2.80 |
| Turns without a tool (T6, CS): client total | 4.73 and 6.06 s | n/a |

Inside the CALL (T2 as the example; the others match): the CALL starts at the tool span's start (09.175 / 09.176);
the first child query starts 2.35 s later (Python start-up), then five start-up queries (about 0.3 s), context
(0.29 s), quality and coverage together (0.98 s, compile 0.88 s), two `RESULT_SCAN` (0.15 s). The CALL ends at 13.908;
**the tool span ends at 17.728, 3.82 s later**, with no query of LINKML_SVC in between. On T1 the CALL took 8.5 s
(first call; compilation 0.64 s on the CALL itself, 1.0 s on each data query) and the span ended 0.19 s after it:
the tool span is about 8.5 s whether the CALL takes 4.6 or 8.5 s.

Each request also runs `LIST snow://workspace/USER$.PUBLIC.DEFAULT$/versions/live/.snowflake/si/skills` as the caller
(0.2 s, at the request's start, in the session that later runs the CALL), and the CALL is sent with named arguments
and binds: `CALL LINKML_METRICS.RAW.STOCK_COVERAGE(filters => ?, as_of_months => ?, unit_variant => ?, grain => ?)`.

### Against probe C0 (same model, hand-written procedure and spec, 10.4 to 13.5 s)

C0's traces cannot be read any more: `GET_AI_OBSERVABILITY_EVENTS` on the dropped agent returns `002003` (does not
exist or not authorized). Its CALLs are still in query history (LINKML_SVC, 2026-10-03 06:51 to 06:59 UTC, named
arguments): **3.71, 4.37, 3.76, 3.66 s**, for client totals of 11.6, 11.8, 13.5, 11.8 s.

| | C0 | C | Difference |
|---|---|---|---|
| Client total, tool turn (median) | 11.8 s | 17.5 s | +5.7 s |
| CALL (median) | 3.7 s | 5.0 s | +1.3 s |
| Client total minus CALL | 8.1 s | 12.5 s | +4.4 s |
| Orchestration input tokens, tool turn | about 47,000 | about 63,000 | +16,000 |
| Turn without a tool (T6) | 5.5 s | 4.7 s | -0.8 s |

## Objects

| Object | State |
|---|---|
| `LINKML_METRICS.RAW.LINKML_C` | created from `generated/agent_c.yaml`, permanent, kept |
| `LINKML_METRICS.RAW.STOCK_COVERAGE_PROBE` (probe C0) | dropped at the end of session 7, last of the session's actions |

# Session 8a: fixes to agent C, latency witness

Contract 0.3.0 at the start of the session (commit 6fa33c8). Setup as perso, `USE SECONDARY ROLES NONE`,
LINKML_METRICS_ROLE; agent calls as LINKML_SVC under budget `s8a` (cap 8; the 8th call is reserved for a justified
re-run).

## Step 0: answer size before any change (`answer_size.py`, direct CALLs, no agent)

Bytes as the connector returns the VARIANT's JSON text, then compacted; tokens approximated as compact bytes / 4
(a rule of thumb, not a tokenizer).

| Id | Status | As returned | Compact | About tokens | `sql` block | `available_months` | Everything else |
|---|---|---|---|---|---|---|---|
| T1 | ok | 13,510 B | 12,609 B | 3,152 | 10,885 B (86%) | 541 B | 1,183 B |
| T7_R1 | refused | 13,101 B | 12,525 B | 3,131 | 11,464 B (92%) | 541 B | 520 B |
| T9 | ok | 13,399 B | 12,486 B | 3,121 | 10,772 B (86%) | 541 B | 1,173 B |

T7_R1 reason, as returned: "DIM_ITEM holds several rows for 1 items with different values of family_code,
lifecycle_status, item_type; any number would be fanned out." (only `lifecycle_status` differs).

## Step 1: `MASTER_DATA_FANOUT` names only the attributes that differ (contract 0.3.1)

The quality statement now returns, beside `FANOUT` (items whose rows differ on any used item attribute), one count
`FANOUT__<ATTRIBUTE>` per used item attribute; the reason names the attributes whose count is above 0. Procedure
redeployed (`CREATE PROCEDURE` query id `00000246-0000-4000-8000-000000000246`).

- T7_R1 reason, direct CALL: "1 item(s) have several rows in DIM_ITEM that differ on lifecycle_status; any number at
  this grain would be fanned out." (`test_t7_r1_fanout_names_only_the_differing_attribute`: no other attribute id
  appears in it).
- Two attributes differing (`test_fanout_two_differing_attributes`): the quality statement generated locally is first
  asserted equal, character for character, to the one the deployed procedure ran for T7_R1; it is then run as is,
  with only `LINKML_METRICS.RAW.DIM_ITEM` replaced by a TEMPORARY copy in which one row of the duplicated item also
  carries another `family_code`. Counts: FANOUT 1, FANOUT__FAMILY_CODE 1, FANOUT__LIFECYCLE_STATUS 1,
  FANOUT__ITEM_TYPE 0; reason "... differ on family_code, lifecycle_status; ...".
- Full suite: 127 passed.

## Step 2: the answer carries query ids, not SQL (contract 0.4.0)

The answer drops the `sql` block and the 36-month list. It carries `lineage.query_ids` (context, quality, coverage:
the statements the call started) and `available_months` as `first`, `last`, `latest`. The context query id is read
with Snowpark's `session.query_history()` (no extra query); quality and coverage are asynchronous jobs, whose
`query_id` is read from the job. Procedure redeployed (`CREATE PROCEDURE` query id
`00000247-0000-4000-8000-000000000247`).

| Id | Compact before | Compact after | About tokens before / after | `lineage` | `available_months` |
|---|---|---|---|---|---|
| T1 | 12,609 B | 1,415 B (-89%) | 3,152 / 353 | 163 B | 64 B |
| T7_R1 | 12,525 B | 731 B (-94%) | 3,131 / 182 | 163 B | 64 B |
| T9 | 12,486 B | 1,404 B (-89%) | 3,121 / 351 | 163 B | 64 B |

Tests: `test_answer_carries_query_ids_not_sql` (T1: no `sql` key; first 2023-07-01, last and LATEST 2026-06-01;
three distinct query ids, each found in `INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION` of the calling session, whose
text names the fact tables, DIM_CALENDAR for the context, DIM_ITEM and DIM_GEO for quality and coverage);
`test_refusal_before_the_data_checks_carries_the_context_query_id_only` (a parameter refusal carries no query id, a
month refusal the context id only). `test_fanout_two_differing_attributes` now reads the procedure's quality
statement back from query history by its id. Full suite: 129 passed.

## Step 3: regeneration and redeployment

Every generator rerun (`compiler/gen_*.py`); `tests/test_generated.py` (drift) green; full suite 129 passed;
STOCK_COVERAGE redeployed from `generated/stock_coverage_procedure.sql` at contract 0.4.0 (step 2's query id).
`generated/agent_c.yaml` differs from commit 6fa33c8 in the header's contract version and one sentence of the tool
description (step 4).

## Step 4: agent C republished (five-beat cycle), then three reference questions

### Versions before the cycle (measured)

- **`CREATE AGENT` (session 7) created two versions**: `live` and `VERSION$1`, both with the same `created_on`
  (07:56:02 PDT), `VERSION$1` default. Their specs and `DESCRIBE AGENT` were all equal to `generated/agent_c.yaml` of
  commit 6fa33c8 before this step. **[measured]**
- **The 15 calls of session 7 were served by `live`**: on every trace, `snow.ai.observability.object.version.name`
  = `LIVE` (version id `100000000000007`, no alias). Observation, no rule drawn: **session 7, `LIVE` served while
  `VERSION$1` was the default** (bare-name REST call `agents/LINKML_C:run`, no version). **[measured]**

### The cycle (`deploy_agent.py publish`, as LINKML_METRICS_ROLE)

| Beat | Statement | Query id |
|---|---|---|
| 0 | spec parsed, `instructions.orchestration` and `.response` single strings, round trip equal | n/a |
| 1 | `ALTER AGENT ... MODIFY LIVE VERSION SET SPECIFICATION = $$...$$` | `00000248-0000-4000-8000-000000000248` |
| 2 | `ALTER AGENT ... COMMIT` | `00000249-0000-4000-8000-000000000249` |
| 3 | `ALTER AGENT ... ADD LIVE VERSION FROM LAST` | `0000024a-0000-4000-8000-00000000024a` |
| 4 | `ALTER AGENT ... SET DEFAULT_VERSION = 'VERSION$2'` (name read from SHOW VERSIONS) | `0000024b-0000-4000-8000-00000000024b` |

Certification: SHOW VERSIONS gives `LIVE` and `VERSION$2` (default) equal to the regenerated `agent_c.yaml`,
`VERSION$1` not; `DESCRIBE AGENT` equal to it. Key-by-key diff of the live spec against `agent_c.yaml` at 6fa33c8: one
key, `tools[0].tool_spec.description` (2,082 to 2,163 characters): " and the list of available months" became ", the
first and last available months with LATEST, and the query ids of its statements (lineage, not for the user)". No
other key differs (instructions, input_schema, model, budget, tool_resources).

### Three questions, each asked once (calls 1 to 3 of budget `s8a`)

`run_call.py --budget s8a --policy c`, as **LINKML_SVC** (key-pair JWT, no role or warehouse header). 3 calls, 3
status 200, no `response.warning`. **UTC window: 2026-10-03 18:31:31.7 (call 1 sent) to 18:34:34.7 (call 3
answered).**

| # | Id | Tool parameters | Answer | Correct? | Request id |
|---|---|---|---|---|---|
| 1 | T1 | `["2026-06-01"]`, QTY_EQ, grain `family_code, country_code`, filters PANTRY_FLOUR, FR | 2.8 months, stock 1,400 against 12,000; month, unit, default scope named; "no flags and no warnings" | **yes** (2.8) | `00000001-0000-4000-8000-000000000001` |
| 2 | T7_R1 | grain `lifecycle_status`, filters PANTRY_OIL, SE | Refusal relayed: "One item ... is recorded with more than one lifecycle status, both ACTIVE and PHASE_OUT"; offers the total without the split or the SKU grain | **yes** (`MASTER_DATA_FANOUT`), **reason now right**: the tool's reason names `lifecycle_status` only, and the agent names no other column. "ACTIVE and PHASE_OUT" is not in the tool's answer: they are the two known values the tool description lists for `lifecycle_status`; true here, but stated as if the tool had said it | `00000002-0000-4000-8000-000000000002` |
| 3 | T9 | grain `sku_code, country_code`, filters SKU-H11, CH | 0.0, NO_STOCK, forecast 2,400; "no warnings"; adds "I can't confirm the product name ... from the tool's output" (as in session 7) | **yes** (not 3.5) | `00000003-0000-4000-8000-000000000003` |

**Version served [measured]:** `snow.ai.observability.object.version.name` = **`VERSION$2`** on every span of the
three turns. Observation, no rule drawn: **session 8a, `VERSION$2` served while it was the default** (same
bare-name REST call as in session 7). `LIVE` and `VERSION$2` carry the same spec, so the answers come from the
regenerated spec either way.

### Tokens, same three questions, session 7 against 8a

REST `usage` (orchestration model) is the sum of three LLM steps: planning, response generation and **suggested
queries** (session 7's table called it "planning and response"; its totals already included the suggested-queries
step: T1 14,563 + 22,948 + 25,311 = 62,822). Per step, from the trace (`*.token_count.input`):

| Id | Planning S7 / 8a | Response S7 / 8a | Suggested queries S7 / 8a | Total S7 / 8a | Difference |
|---|---|---|---|---|---|
| T1 | 14,563 / 14,587 | 22,948 / 15,962 | 25,311 / 18,273 | 62,822 / 48,822 | -14,000 (-22%) |
| T7_R1 | 14,573 / 14,597 | 22,417 / 15,436 | 24,795 / 17,821 | 61,785 / 47,854 | -13,931 (-23%) |
| T9 | 14,582 / 14,606 | 22,997 / 16,003 | 25,403 / 18,392 | 62,982 / 49,001 | -13,981 (-22%) |

Every spec difference between the two runs: one sentence of the tool description, +81 characters (key-by-key diff
above); instructions, `input_schema`, model and budget identical. Attribution:
- planning step (reads the spec, not the tool result): **+24 tokens** on each question, the description's 81
  characters; **[measured]**
- response and suggested-queries steps (both read the tool result): **-6,970 to -6,986 and -6,974 to -7,038**, about
  7,000 each, so about 14,000 per turn. The tool result as returned shrank by 11,604 B (T1), about 1.66 bytes per
  token: the result reaches the model as a JSON string escaped inside the tool content (`\\n`, `\\\"`), so the
  bytes / 4 estimate of step 0 understated the old answer's cost by about 2.4 times. **[measured]** (token counts),
  **[inferred]** (the escaping as the reason for the ratio)
- The guardrail model's input fell too (4,967 to 1,293 on T1): it reads the tool result. **[measured]**

### Latency (`latency.py --budget s8a`, raw output)

| # | Id | Client s | Server s | Before planning s | Planning s | Tool span s | Response s | Suggested queries s | CALL elapsed ms (compile / queued) | Children: n, elapsed ms (compile) | Request id | Span end - CALL end s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | T1 | 17.15 | 16.16 | 1.25 | 2.34 | 8.37 | 2.19 | 2.0 | 7801 (483 / 73) | 10: 47 (45), 48 (46), 49 (47), 66 (65), 47 (46), 527 (231), 922 (763), 687 (531), 67 (64), 65 (63) | `00000001-0000-4000-8000-000000000001` | 0.57 |
| 2 | T7_R1 | 17.57 | 16.41 | 0.34 | 2.23 | 8.64 | 3.14 | 2.05 | 4550 (254 / 0) | 9: 46 (44), 48 (47), 60 (59), 58 (57), 43 (42), 227 (185), 811 (677), 593 (549), 66 (65) | `00000002-0000-4000-8000-000000000002` | 4.09 |
| 3 | T9 | 17.06 | 15.64 | 0.28 | 1.79 | 8.62 | 2.78 | 2.16 | 4778 (241 / 0) | 10: 61 (59), 47 (46), 61 (59), 88 (86), 117 (115), 269 (229), 876 (768), 636 (593), 77 (75), 65 (64) | `00000003-0000-4000-8000-000000000003` | 3.84 |

Against session 7 on the same questions (client s, response s, suggested queries s): T1 20.42 / 4.39 / 2.15 to
17.15 / 2.19 / 2.00; T7_R1 17.47 / 3.33 / 1.71 to 17.57 / 3.14 / 2.05; T9 16.82 / 3.03 / 1.99 to 17.06 / 2.78 /
2.16. One call per question: no latency change can be told apart from turn-to-turn spread; the tool span (8.4 to
8.6 s) is unchanged, and again the first CALL of the session took longer (7.8 s, span end 0.57 s after it) while the
others took 4.6 to 4.8 s with the span ending 3.8 to 4.1 s after the CALL.

Traces of the three turns are saved per turn outside the repository by `run_call.py` (they carry the account host);
LINKML_C is kept, so `GET_AI_OBSERVABILITY_EVENTS` still reads them.

## Step 5: latency witness `LINKML_WITNESS_PROBE` (calls 4 to 7 of budget `s8a`)

Files: `witness/witness.sql` (two procedures, `EXECUTE AS CALLER`, a fixed JSON and no query: `WITNESS_SQL` in SQL
Scripting, `WITNESS_PY` in Python 3.12 with Snowpark), `witness/witness_agent.yaml` (the reviewed spec: same model,
budget and warehouse as agent C, one `generic` tool `witness` with one string argument), `witness/witness.py`.
Created as LINKML_METRICS_ROLE (`CREATE AGENT` query id `0000024c-0000-4000-8000-00000000024c`): SHOW VERSIONS
again gave `live` and `VERSION$1` (default), both bound to `WITNESS_SQL`. After two calls, rebound by the five-beat
cycle (`0000024d-0000-4000-8000-00000000024d` / `...b66` / `...b6a` / `...b72`): `LIVE` and `VERSION$2` (default) on
`WITNESS_PY`, `VERSION$1` on `WITNESS_SQL`. Each question: "Call the witness with label wN.", policy `w`, as
LINKML_SVC. **UTC window: 2026-10-03 18:42:56 (call 4 sent) to 18:47:34 (call 7 answered).** 4 calls, 4 status 200,
each with one tool call `{"label": "wN"}` and a one-sentence answer.

**Warehouse guard.** Before each call, as perso on LINKML_METRICS_WH (auto-suspend 60 s, no parameter changed):
`SELECT 1` then `SELECT SUM(SEQ4()) FROM TABLE(GENERATOR(ROWCOUNT => 1000))`, then SHOW WAREHOUSES: STARTED before
each of the four calls. `SELECT 1` alone **does not resume a suspended warehouse**: the state was still SUSPENDED
right after it (query id `0000024e-0000-4000-8000-00000000024e`); the GENERATOR sum did (`<query-id>`).
**[measured]**

| # | Binding | Request id | Version served | Client s | Tool span s | CALL elapsed ms (compile / execution) | Queued provisioning / overload ms | Span end - CALL end s | Span start to CALL start s |
|---|---|---|---|---|---|---|---|---|---|
| 4 | SQL (w1) | `00000004-0000-4000-8000-000000000004` | LIVE | 7.95 | 1.23 | 396 (237 / 159) | 0 / 0 | 0.59 | 0.25 |
| 5 | SQL (w2) | `00000005-0000-4000-8000-000000000005` | LIVE | 5.77 | 0.49 | 353 (278 / 75) | 0 / 0 | 0.14 | 0.00 |
| 6 | Python (w3) | `00000006-0000-4000-8000-000000000006` | VERSION$2 | 14.46 | 8.51 | 4976 (252 / 4724) | 0 / 0 | 3.53 | 0.00 |
| 7 | Python (w4) | `00000007-0000-4000-8000-000000000007` | VERSION$2 | 9.71 | 4.32 | 2807 (213 / 2594) | 0 / 0 | 1.51 | 0.00 |

The agent C CALLs of step 4 had queued provisioning 73 ms (T1) and 0 (T7_R1, T9), overload 0. **No CALL of this
session waited for a warehouse resume** (the largest queue time is T1's 73 ms of provisioning). The Python CALLs
ran 5 child queries each (Snowpark start-up, 45 to 64 ms each), the SQL CALLs none.

Version resolution, two more observations, no rule drawn: the SQL binding (live and `VERSION$1` default) was served
by `LIVE`; after the rebind (`VERSION$2` default) the Python binding was served by `VERSION$2`.

Raw output of `latency.py --budget s8a` for these rows:

| # | Id | Client s | Server s | Before planning s | Planning s | Tool span s | Response s | Suggested queries s | CALL elapsed ms (compile / queued) | Children: n, elapsed ms (compile) | Request id | Span end - CALL end s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | witness_sql_w1 | 7.95 | 7.22 | 1.25 | 1.69 | 1.23 | 1.39 | 1.66 | 396 (237 / 0) | 0 | `00000004-0000-4000-8000-000000000004` | 0.59 |
| 5 | witness_sql_w2 | 5.77 | 5.03 | 0.26 | 1.47 | 0.49 | 1.21 | 1.59 | 353 (278 / 0) | 0 | `00000005-0000-4000-8000-000000000005` | 0.14 |
| 6 | witness_py_w3 | 14.46 | 13.62 | 0.3 | 1.5 | 8.51 | 1.46 | 1.85 | 4976 (252 / 0) | 5: 55 (53), 55 (53), 45 (44), 61 (60), 53 (51) | `00000006-0000-4000-8000-000000000006` | 3.53 |
| 7 | witness_py_w4 | 9.71 | 8.98 | 0.27 | 1.47 | 4.32 | 1.37 | 1.54 | 2807 (213 / 0) | 5: 52 (51), 48 (47), 51 (50), 64 (63), 58 (57) | `00000007-0000-4000-8000-000000000007` | 1.51 |

### Reading: steps, not a floor

Tool spans observed this session, with the CALL they waited for: 0.49 (CALL 0.35), 1.23 (0.40), 4.32 (2.81), 8.37
(7.80), 8.51 (4.98), 8.62 (4.78), 8.64 (4.55). Session 7: 8.40 to 9.14 for CALLs of 4.57 to 8.51. **The span ends at
the first of a few fixed points after the CALL ends: about 0.5, 1.2, 4.3 and 8.5 s after the span starts**, and
nothing between 1.23 and 4.32 or between 4.32 and 8.37 was seen. **[measured]** (the values). A polling interval that
roughly doubles is the likely mechanism; where the step between 1.2 and 4.3 s lies (about 2.2 s if it doubles) was
not observed. **[inferred]**

- The floor is about 0.5 s (an empty SQL Scripting CALL of 0.35 s).
- A CALL that ends after the 4.3 s point waits for the 8.5 s point: agent C's 4.6 to 4.8 s CALLs lose 3.8 to 4.1 s.
- An empty Python procedure took 2.8 and 5.0 s inside the agent (execution 2.6 and 4.7 s, before any handler query),
  so a Python tool cannot reliably end before the 4.3 s point; an empty SQL Scripting one took 0.35 and 0.40 s.

Objects: `LINKML_WITNESS_PROBE`, `WITNESS_SQL(VARCHAR)` and `WITNESS_PY(VARCHAR)` dropped
(`0000024f-0000-4000-8000-00000000024f` / `...c5e` / `...c62`) after the traces were extracted: one file per turn
(`run_call.py`) and the whole `GET_AI_OBSERVABILITY_EVENTS` output (36 rows, the 4 record ids), outside the
repository. SHOW AGENTS in RAW lists only LINKML_C; SHOW PROCEDURES LIKE 'WITNESS%' is empty.

Budget `s8a`: 7 calls used of 8; the reserved 8th call was not used.
