# Phase 4 notes, part 1: agent C on the generated procedure

> Session 7, 2026-10-03. Every choice tagged **[documented]** (DEFINITION.md, the plan, the contract, Snowflake
> docs), **[measured]** (run here, evidence in the repository), or **[inferred]** (reasoned, not run). Evidence:
> `snowflake/phase4_agent_c/results.md`. Contract 0.3.0. 15 agent calls, all as LINKML_SVC.

## Step 3: the agent and the question set

| # | Choice or finding | Why, evidence | Tag |
|---|---|---|---|
| 1 | Agent C's spec is **generated**: `compiler/gen_agent.py` writes `generated/agent_c.yaml` from the contract (metric, totals rule, flags, units, refusal behaviour, parameters, attribute classes) and the dataset (valid months, LATEST, codes with their names for attributes of at most 30 codes). One `generic` tool, `stock_coverage`, bound to `LINKML_METRICS.RAW.STOCK_COVERAGE` on the project warehouse. A drift test regenerates it | Decision 4 of session 7 | documented |
| 2 | Instructions: never add or average coverage rows, ask the tool for a coarser grain or a total instead; always name the analysis month used; relay every warning with its number; explain a refusal in business words; ask for a month when given none or a period | Decision 4 | documented |
| 3 | Every parameter is a `string` in `input_schema`; lists and maps travel as JSON strings | An `array` argument is rejected on a warehouse execution environment (probe C0) | measured (C0) |
| 4 | `totals` is optional in the schema (default `[]`), the other four are required | The contract's `is_required` | documented |
| 5 | Internal references ("decision N", DEFINITION.md sections) are stripped from every text the model reads; punctuation fixed at the owner's review (lower case after a colon, no full stop inside a list) | They mean nothing to the model | inferred |
| 6 | Model `claude-sonnet-5-5`, budget 120 s and 40,000 tokens, as C0 | Comparability with C0 | documented |
| 7 | Reference questions are **generated**: `compiler/gen_questions.py` writes `generated/reference_questions.yaml`, one per failure mode plus the refusal questions of `data/traps.yaml` plus one drill, in grocery wording, each with its expected value, flag, warnings or refusal and the tool parameters that produce it. `tests/test_procedure.py` asserts every expected answer against the procedure | Decision 5 | documented (decision), measured (tests) |
| 8 | Closing-stock questions are in the set but marked `asked_to_agent_c: false`: the coverage tool does not compute closing stock | Decision 1 (closing stock lives in `CLOSING_STOCK_SV`) | inferred |
| 9 | `LINKML_C` created as LINKML_METRICS_ROLE; `DESCRIBE AGENT` returns a spec equal to the generated file. **No grant added**: LINKML_SVC holds that role only, and the role owns the agent and the procedure and uses the warehouse | `deploy_agent.py`, `SHOW GRANTS` | measured |

## Step 4: the questions, each asked once

| # | Finding | Tag |
|---|---|---|
| 10 | **Every number the agent gave is right**: T1 2.8, T2 7.0, T3 6.0, T4 8.5, T7 2.25 (said 2.3 by the one-decimal rule), T8 0, NO_DEMAND null, BEYOND_H 50.0, BULK_SCOPE 8.67, T9 0 (not 3.5), and the six drill rows. None added or averaged | measured |
| 11 | The analysis month is named in every answer that ran the tool (13 of 13); every warning the tool returned is relayed with its number (T2, T5, T7, BEYOND_H, BULK_SCOPE twice, the drill twice), and "no warnings" is said when there are none | measured |
| 12 | Tool parameters are the expected ones, with two equivalent forms: T3 grain `sku_code` with the country as a filter; the drill drops `family_code` from the grain, keeps the family filter and **asks for the total itself** (`totals [[]]`), then says the 8.7 total "is not an average of the country rows" | measured |
| 13 | T6 (a year) and the closing-stock question: **no tool call, no number**. T6 asks which month and gives the valid range; the closing-stock question says the tool measures coverage at one month, not closing stock over a quarter, and offers the June coverage | measured |
| 14 | **T5 (packs) never reaches the procedure**: the model refuses raw packs itself, explains why, and answers in QTY_EQ (2.4, the expected alternative) instead of offering it. Right number, but the procedure's `UNIT_RAW_NOT_ADDITIVE` is untested through the agent, and the user got an answer to a question they did not ask | measured |
| 15 | **T7_R1: the refusal is right but its reason is wrong.** The procedure's `MASTER_DATA_FANOUT` reason lists every column it checked ("lifecycle_status, family_code, item_type"), not the one that differs (lifecycle_status only); the agent relays it faithfully as "conflicting lifecycle status, family and item type". A procedure defect, not a model one | measured |
| 16 | Two stray remarks, no wrong number: T9 says it "couldn't check the product name against the SKU code"; T1 mentions the BULK exclusion although nothing was excluded | measured |
| 17 | The procedure's caller block, inside each agent call: LINKML_SVC, LINKML_METRICS_ROLE, no secondary role, agent activated | measured |

## Step 5: latency per turn

| # | Finding | Tag |
|---|---|---|
| 18 | Tool turn, median of 13: **17.5 s** client total = 0.3 s before planning + 2.2 s planning + **8.6 s tool span** + 3.1 s response + 2.2 s suggested queries (+ about 0.8 s transport). Turns without a tool: 4.7 and 6.1 s | measured |
| 19 | **The tool span is about 8.5 s whatever the CALL takes**: CALL 4.6 to 6.1 s on 12 turns, with the span ending 3.1 to 3.9 s after the CALL and no query of LINKML_SVC in between; on the first turn the CALL took 8.5 s and the span ended 0.19 s after it | measured |
| 20 | Reading of 19: the agent waits for the CALL by polling, with a step that rounds a 5 s CALL up to about 8.5 s. A faster procedure (a SQL Scripting rewrite, part 1 finding 36) would gain nothing unless it crosses a lower step; how low the steps go is not measured | inferred |
| 21 | Inside the CALL (median 5.0 s, about 1 s above the direct calls of step 1): 2.35 s of Python start-up, five start-up queries (0.3 s), context (0.3 s), quality and coverage in parallel (about 1 s, compile-bound), two `RESULT_SCAN` (0.15 s). The agent sends `CALL ... (filters => ?, as_of_months => ?, ...)` with binds | measured |
| 22 | Each request also lists the caller's workspace skills (`LIST snow://workspace/USER$.PUBLIC.DEFAULT$/versions/live/.snowflake/si/skills`, 0.2 s) in the session that later runs the CALL | measured |
| 23 | **Against C0** (same model, hand-written spec and procedure): client total 11.8 s against 17.5 s; CALL 3.7 s against 5.0 s; the rest 8.1 s against 12.5 s. C0's spans cannot be read any more (`002003` on the dropped agent), so the split of C0's 8.1 s is unknown; finding 19 accounts for about 3.8 s of the 4.4 s difference if C0's tool span was close to its CALL | measured (totals, CALLs), inferred (attribution) |
| 24 | **Tokens: about 63,000 input per tool turn against C0's 47,000**; 31,500 without a tool against 28,500. 85% of each tool answer (10.8 of 12.7 KB) is the `sql` block returned for audit; the drill, which carries two tool answers, reaches 92,000 | measured |
| 25 | Credits not read; the UTC window (14:56:40 to 15:15:56) and the 15 request ids are in the results file for a later read | documented |

## Open questions

1. `MASTER_DATA_FANOUT` reason (15): name only the columns that actually differ. A handler change and a test.
2. T5 (14): should the agent pass RAW and let the procedure refuse, so the refusal is the contract's? That means
   removing "never raw pack counts" from the orchestration instruction and the input description.
3. Tool answer size (24): drop the `sql` block from the agent's answer (keep the query ids) and the 36-month list
   (keep first, last, LATEST)? Fewer tokens; does it change the response time?
4. Tool span floor (19, 20): measure it with a procedure that returns at once (a witness tool), before deciding on
   the language (part 1 finding 36).
5. Closing stock through an agent: agent C has one tool by decision 4; the closing questions go to the
   configurations that read `CLOSING_STOCK_SV`.
6. Whether `totals` may be omitted by the model on every turn (4): it omitted it on 12 tool turns and passed it once, correctly.

## First step of session 8

The other configurations on the same reference questions (`generated/reference_questions.yaml`, asked once each,
same budget rules): **A** (Autopilot), **B1** (hand-written native semantic view), **B2** (generated native
semantic view), **D** (skill with `code_execution`) and **D′** (skill with `code_toolset_all`, one bash approval per run),
recording the same columns as agent C (tool, parameters, answer, correct, warnings, as-of month, latency, tokens).
The closing-stock questions go to the configurations that can read `CLOSING_STOCK_SV`.

# Phase 4 notes, part 2: session 8a, fixes to agent C and the latency witness

> Session 8a, 2026-10-03. Tags as in part 1: **[documented]**, **[measured]**, **[inferred]**. Evidence:
> `snowflake/phase4_agent_c/results.md` (session 8a section). Contract 0.3.0 to 0.4.0. 7 agent calls of a budget of 8,
> all as LINKML_SVC. Agent call windows (UTC, 2026-10-03): agent C 18:31:31.7 to 18:34:34.7 (request ids
> `00000001-0000-4000-8000-000000000001`, `00000002-0000-4000-8000-000000000002`,
> `00000003-0000-4000-8000-000000000003`); witness 18:42:56 to 18:47:34 (`00000004-0000-4000-8000-000000000004`,
> `00000005-0000-4000-8000-000000000005`, `00000006-0000-4000-8000-000000000006`,
> `00000007-0000-4000-8000-000000000007`).

## Fixes (steps 0 to 3)

| # | Choice or finding | Why, evidence | Tag |
|---|---|---|---|
| 26 | Before any change, the answer was about 12.6 KB compact for T1, T7_R1 and T9, of which the `sql` block was 86 to 92% and the month list 541 B | `answer_size.py`, step 0 | measured |
| 27 | `MASTER_DATA_FANOUT` names only the used item attributes on which the duplicated rows differ: one count per used attribute (`FANOUT__<A>`) in the quality statement. T7_R1 now reads "... differ on lifecycle_status ..." | Part 1 open question 1; tests on T7_R1 and on a two-attribute case | measured |
| 28 | The two-attribute test runs the quality statement the procedure ran (read back by query id and compared character for character with the locally generated one), with only DIM_ITEM replaced by a TEMPORARY copy where the duplicated item also differs on `family_code` | Owner's precision: the generated SQL as is, not a rewrite | measured |
| 29 | Contract 0.3.1 for the reason (no rule changed), 0.4.0 for the answer shape (no rule changed); the tool description changes by one sentence | Decision 3 of session 8a | documented |
| 30 | The answer carries `lineage.query_ids` (context, quality, coverage) and `available_months` as first, last, LATEST; the full list stays in the `AS_OF_NO_SNAPSHOT` reason only. The context id comes from Snowpark's `session.query_history()` (no extra query), the two others from the async jobs | Decision 2; owner's go on point b | documented (choice), measured (works) |
| 31 | Lineage test: the three ids of a T1 call resolve in `INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION` of the calling session (the procedure runs as caller) to statements naming the expected tables; a parameter refusal carries no id, a month refusal the context id only | `tests/test_procedure.py` | measured |
| 32 | Answer after the change: T1 1,415 B, T7_R1 731 B, T9 1,404 B compact (-89 to -94%) | `answer_size.py`, step 2 | measured |
| 33 | The answer shape (keys of the JSON) is declared in the handler only; the contract describes what `analysis_periods` exposes but has no slot for the answer's keys or for lineage | Read while making decision 2 | inferred |

## Agent C republished and asked again (step 4)

| # | Finding | Tag |
|---|---|---|
| 34 | `CREATE AGENT` creates two versions, `live` and `VERSION$1` (default), with the same spec; the witness agent showed the same | measured |
| 35 | Version served, as observations only: session 7, `LIVE` served while `VERSION$1` was the default; session 8a after the cycle, `VERSION$2` (default) served. The witness repeated both: `LIVE` with `VERSION$1` default, `VERSION$2` once it was the default after a rebind | measured |
| 36 | Five-beat cycle (MODIFY LIVE, COMMIT, ADD LIVE VERSION FROM LAST, SET DEFAULT_VERSION read from SHOW VERSIONS): live and default equal to the regenerated file, `DESCRIBE` too; key-by-key diff against 6fa33c8: the tool description only (+81 characters) | measured |
| 37 | T1 2.8, T7_R1 refused with the right reason, T9 0 with NO_STOCK: all correct. T7_R1's answer adds "both ACTIVE and PHASE_OUT", values not in the tool result but listed as the attribute's known values in the tool description: true here, stated as if the tool had said it | measured |
| 38 | Input tokens fell by about 14,000 per turn (-22%: 62,822 to 48,822 on T1). The planning step rose by 24 tokens (the description's 81 characters); the response step and the suggested-queries step each fell by about 7,000, because **both read the tool result**. The REST `usage` total includes the suggested-queries step; part 1's "planning and response" was a mislabel of the same total | measured |
| 39 | About 1.66 bytes per token on the old result: the result reaches the model as a JSON string escaped inside the tool content, so a bytes / 4 estimate understates a JSON tool result's cost by more than twice | measured (ratio), inferred (cause) |
| 40 | No latency change visible on one call per question (client 17.1 to 17.6 s); the tool span stayed at 8.4 to 8.6 s | measured |

## Latency witness (step 5)

| # | Finding | Tag |
|---|---|---|
| 41 | Empty SQL Scripting procedure through the agent: CALL 0.35 and 0.40 s, tool span 0.49 and 1.23 s, span ending 0.14 and 0.59 s after the CALL | measured |
| 42 | Empty Python 3.12 procedure through the agent: CALL 4.98 and 2.81 s (execution 4.7 and 2.6 s, five Snowpark start-up child queries), tool span 8.51 and 4.32 s, span ending 3.53 and 1.51 s after the CALL | measured |
| 43 | **The tool span has steps, not a floor**: across this session and session 7 it ended near 0.5, 1.2, 4.3 or 8.5 s after it started, never in between; the lowest value is about 0.5 s | measured (values) |
| 44 | Mechanism: the agent polls the CALL with an interval that roughly doubles; the step between 1.2 and 4.3 s (about 2.2 s if it doubles) was not observed | inferred |
| 45 | No CALL of the session waited for a warehouse resume: queued provisioning 0 except T1's 73 ms, overload 0. The guard ran `SELECT 1` and a GENERATOR sum before each call: `SELECT 1` alone left a suspended warehouse suspended | measured |
| 46 | Agent C's CALL (4.6 to 4.8 s) ends just after the 4.3 s point and waits for the 8.5 s point: about 3.8 to 4.1 s lost per turn, a quarter of the 17 s turn | measured (gap), inferred (attribution to the step) |

## Should the procedure move to SQL Scripting?

**Yes, on the witness's numbers** [inferred from measured costs]. An empty Python procedure already costs 2.8 to
5.0 s inside the agent, so the Python tool cannot reliably end before the 4.3 s point and pays the 8.5 s step. An
empty SQL Scripting one costs 0.35 to 0.40 s; with agent C's three statements (about 1.3 to 2.2 s summed, part 1
finding 33) a SQL Scripting CALL should end before the 4.3 s point and possibly near 2 s, for a tool span of 4.3 s
or less instead of 8.5 s: about 4 s or more saved on a 17 s turn. Not measured until the rewrite exists. The price is
the one part 1 named: validation, refusal order and the JSON answer generated in SQL Scripting, with the same tests.
A cheaper Python step (part 1 open question 2: synchronous statements, one merged statement) cannot remove the
2.6 to 4.7 s runtime start, so it does not cross the 4.3 s point.

## Open questions (session 8a)

1. Decision 5 (language): rewrite the generated procedure in SQL Scripting (above). Keep the Python handler as the
   reference until the SQL Scripting one passes the same 129 tests.
2. The step between 1.2 and 4.3 s: one witness CALL lasting about 1.5 to 2 s (a `SYSTEM$WAIT` in the SQL Scripting
   witness) would place it, and tell whether a 2 s SQL Scripting coverage CALL lands on a 2.2 s or a 4.3 s step.
3. Should the tool description stop listing known values that the model then presents as facts (finding 37), or is
   that acceptable when they are the full list?
4. `FANOUT__<A>` uses `COUNT(DISTINCT col) > 1`, which ignores NULL: an item with one NULL row and one valued row on
   a used attribute is not counted as a fan-out. Pre-existing; not observed on v0 data.
5. The answer's keys are not in the contract (finding 33): a slot for the answer shape and lineage, or keep it in the
   handler?
6. Part 1 open questions 2 (T5 refused by the model, not by the procedure), 5 and 6 stand.

# Phase 4 notes, part 3: session 8, the other configurations (A, B1, B2, D, D′)

> Session 8, 2026-10-04. Tags as in parts 1 and 2: **[documented]**, **[measured]**, **[inferred]**. Evidence:
> `snowflake/phase4_others/results.md`. Contract 0.4.1, charter `docs/configurations.md` version 5, rubric
> `eval/rubric.yaml` version 2. 30 agent calls of a budget of 38, all as LINKML_SVC; raw logs and traces in
> `~/work/assets/linkml-metrics-runs/s8/`, outside the repository. Agent call windows (UTC, 2026-10-04): witness
> 06:44:08 to 06:45:38; B2 07:04:12 to 07:09:08; B1 07:35:00 to 07:39:23; D′ 08:05:15 to 08:12:48 and 08:23:19 to
> 08:25:31; D 08:28:05 to 08:34:27; A 08:50:02 to 08:54:43.

## Before any build (step 0)

| # | Choice or finding | Why, evidence | Tag |
|---|---|---|---|
| 47 | Contract 0.4.1: the default scope applies to the coverage metric only (`applies_to_metrics`, metamodel 0.3.0), never to closing stock; procedure and closing view redeployed, `LINKML_C` untouched | Owner's precision; phase 3 finding 42 | documented |
| 48 | Fairness charter written before any build, then five versions, each before the next CREATE: section 8 (default scope, analysis month, unit) given to A, B1, D, D′; D and D′'s view tool routed to the skill; Provenance lines kept out of instructions | `docs/configurations.md`, "Charter versions" | documented |
| 49 | Every expected value, warning count and general-question value recomputed in pandas; BULK_SCOPE's FORECAST_GAPS_FILLED 2 now from its source; a test forbids any expected value from the procedure | `tests/test_reference_oracle.py` | measured |
| 50 | The campaign set is 19 questions (17 of the file, G1, G2); G1 6,416 (forecast, no hero), G2 by country with the DIM_ITEM fan-out trap (SE +4,800 EUR) | `data/traps.yaml` general_questions | measured |
| 51 | Grader corrections came only from real answers and never changed the rubric: SQL read from tool calls; the horizon's month count in three wordings and a year are not coverages; owner decisions applied by request id (`eval/manual_decisions.yaml`) | `tests/test_grade.py` (39) | measured |

## Platform behaviour

| # | Finding | Tag |
|---|---|---|
| 52 | The agent tool span also stops near 2.6 s: a 2.44 s SQL Scripting CALL ended at 2.57 s once and at 4.24 s once; points seen across sessions 7 to 8: 0.5, 1.2, 2.6, 4.3, 8.5 s | measured |
| 53 | A YAML semantic view carries window metrics (`OVER (PARTITION BY EXCLUDING ...)`), `non_additive_dimensions` and `is_enum`/`sample_values` together, and the read-back YAML keeps the grounding fields | measured |
| 54 | **Inside an agent, a view-level metric is never selected**: the model writes SQL over logical tables, which run as CTEs exposing dimensions and facts only; `SELECT coverage_months_qty_eq` fails `invalid identifier`, and the model computes from the inputs. No `SEMANTIC_VIEW()` call in any statement of the session | measured; that Cortex Agents generate SQL directly is documented (https://docs.snowflake.com/release-notes/2026/other/2026-04-13-cortex-agents-agentic-analyst, Apr 13, 2026) |
| 55 | Under `code_toolset_all`, the semantic view tool's SQL comes as a `snowflake_sql_execute` tool use with `client_side_execute: true`: a REST client must run it and return a `tool_result`, or the turn ends without an answer ("Waiting for client action"); the sandbox's own SQL tool runs server-side | measured; the field and the content type documented (Cortex Agents Run API), the loop not |
| 56 | Under `code_execution` no approval is asked and the semantic view SQL runs server-side; the server-side skill load lists the script at 0 B although it runs (T1), and once the model believed it and skipped it (T9) | measured |
| 57 | Under `code_toolset_all`, the skill script's own queries run as the caller: LINKML_SVC, LINKML_METRICS_ROLE, LINKML_METRICS_WH (4 of 4) | measured |
| 58 | Orchestration input per tool turn: B2 150k to 293k, B1 112k to 176k, A 160k to 188k, D 149k to 206k, D′ 99k to 236k per call; about 33k without a tool everywhere (agent C: about 49k). The 40,000-token budget is never enforced | measured |

## Configurations on the smoke questions (T1, T6, T9, CS_LAST_MONTH_GAP, plus G1 for D and D′)

| # | Finding | Tag |
|---|---|---|
| 59 | B2 4 of 4, B1 4 of 4 (CS by the owner's decision), A 3 of 4 plus CS manual, D′ 5 of 5 (CS and G1 on re-runs with client-side execution), D 4 of 5 (T9 wrong by routing) | measured |
| 60 | On A, B1 and B2 the tools returned only inputs and the model computed coverage ("computed by: model"); on D and D′ the skill script computed it (T1, and T9 for D′) | measured |
| 61 | The native defects of B1's view (carried last value, fan-out) were bypassed rather than met: the model writes the month as an equality and never selects the semi-additive or window metrics | measured |
| 62 | The smoke questions do not test the model's arithmetic (T1 flat over 3 months, T9 a zero stock); the campaign's T2, T4, BEYOND_H, BULK_SCOPE and drill do | measured |

## Hypotheses of the charter, after the smoke

| Id | Status | Evidence |
|---|---|---|
| H-A1 | refuted on T1; T4, BEYOND_H not yet tested | A computed 2.8 from section 1 only |
| H-A2, H-A3, H-A4, H-A8 | not yet tested | campaign questions |
| H-A5 | refuted on the smoke | T9 0 |
| H-A6 | refuted on the smoke | T6 asks for the month |
| H-A7 | refuted on the smoke (verdict manual, owner) | CS 0, May's 350 cited |
| H-B1-1 | holds in its first branch on T1 (the model writes the cascade) | T1 2.8 |
| H-B1-2, H-B1-3, H-B1-5 | not yet tested | |
| H-B1-4 | refuted on the smoke | T9 0, CS 0 |
| H-B1-6 | refuted on the smoke | T6 asks |
| H-B2-1, H-B2-2, H-B2-5 | not yet tested; H-B2-2 cannot hold for T7 (object check 3.0) | |
| H-B2-3, H-B2-4 | expectation held | T6 asks; T9 and CS 0 |
| H-B2-6 | confirmed | the metric never selected, coverage computed by the model |
| H-D-1 | not yet tested (T1's inputs right) | |
| H-D-2 | not confirmed on T1 (206k tokens and 25.3 s against B2's 202k and 27.7 s) | |
| H-D-3 | confirmed | CS and G1 to the B2 tool |
| H-DP-1 | not yet tested | |
| H-DP-2 | confirmed on tokens and approvals (one per script run); T1 43 s over two calls | |
| H-DP-3 | confirmed | G1 to the B2 tool |
| H-ALL-1 | not yet tested | no smoke question carries a warning |

## Open questions (session 8)

1. A CS_LAST_MONTH_GAP: manual, for the owner (same shape as B1's, decided correct).
2. D's script listed at 0 B by the server-side skill load: keep D as is (a result), or state in the skill that the
   listing size is not the file? The owner decides; the skill and D's instructions are unchanged.
3. Republications before the campaign (no agent call): B1 (unit sentence), D and D′ (charter version 5), B2 (unit
   sentence) - `results.md`, "Republications before the campaign".
4. The campaign harness must keep `--client-sql` for D′ (finding 55) and count its resumes.
5. Closing-stock unit in B2: the generated instructions name both metrics; version 5's compiler sentence now states
   QTY_EQ by default (B2 republish).
6. Release note of 13/04/2026: closed (owner, 2026-10-07): read by the owner, cited by its URL (https://docs.snowflake.com/release-notes/2026/other/2026-04-13-cortex-agents-agentic-analyst).

# Phase 4 notes, part 4: session 8b, agent C rebuilt on a SQL Scripting procedure

> Session 8b, 2026-10-04. Tags as in parts 1 to 3: **[documented]**, **[measured]**, **[inferred]**. Evidence:
> `snowflake/phase4_c_sql/results.md`, `parity_checklist.md`; run folder `~/work/assets/linkml-metrics-runs/s8b/`,
> outside the repository. Contract 0.4.1 to 0.4.2, charter version 6 to 7. 10 agent calls of a budget of 14, all as
> LINKML_SVC; the reserve of 4 not used. **Agent call window (UTC, 2026-10-04): 20:19:18.9 to 20:31:44.2**, request ids
> in the results file.

## The procedure

| # | Choice or finding | Tag |
|---|---|---|
| 63 | `compiler/gen_procedure.py --target sql` generates the SQL Scripting procedure from the contract (`compiler/procedure_scripting.py`); same signature, answer keys, check order, codes, messages, warnings, flags, totals, default scope; no Python, no Snowpark; a test asserts no code shared with the pandas, DuckDB and skill references | measured (tests) |
| 64 | Owner's answers applied to both procedures, tests first: MASTER_DATA_FANOUT names the conflicting values (at most 5 per column), several faulty attributes in declaration order whatever the JSON key order, nested values as compact JSON (contract 0.4.2, no rule changed) | measured |
| 65 | **A Snowflake Scripting statement costs about 15 ms the first time it runs, about 1 ms when repeated in a loop**; the first two versions (a generic body over the contract as JSON) took 8.6 to 10.2 s per CALL. The kept shape runs the work as SQL statements started together with ASYNC (their compilation overlaps) and keeps about 40 distinct Scripting statements | measured |
| 66 | `SQLID` right after an `ASYNC` assignment is the child's query id; `CANCEL` on a finished child raises nothing; a child still running at `RETURN` is cancelled; `PARSE_JSON(..., 'd')` is as strict as Python's parser; `SYSTIMESTAMP()` runs a child query, `CURRENT_TIMESTAMP()` does not; SQL lambdas are refused in Scripting expressions and an inner lambda cannot read an outer lambda's parameter; `ARRAY_INTERSECTION` does not keep its first argument's order | measured |
| 67 | Parity by direct CALL: **134 / 134 identical** (tests' cases, the 13 coverage questions, extra parsing cases); `tests/test_procedure.py` 87 / 87 on each procedure | measured |
| 68 | Direct latency, 50 hero calls each: **SQL median 3.48 s (2.97 to 4.33), Python 4.55 s (4.26 to 6.13)** | measured |
| 69 | Decision 4 on zero-copy clones: HORIZON_NOT_LOADED (calendar, forecast) and DATA_QUALITY_FAILED (QE_GEO_GRAIN, QE_COUNTRY_REGION), 8 / 8 same code and message on both procedures; **both refuse the request that does not use the faulty columns too**: these expectations are TABLE-scoped REFUSE in the contract, only QE_ITEM_GRAIN depends on the columns used. The third HORIZON_NOT_LOADED branch is unreachable by construction | measured; unreachable: inferred |
| 70 | Swap: `STOCK_COVERAGE` is the SQL Scripting procedure, `STOCK_COVERAGE_PY` the Python one (kept until the campaign is over); lineage names the statements that read data (context, quality, coverage) | measured; lineage: owner's decision |

## Agent C and the other republications

| # | Finding | Tag |
|---|---|---|
| 71 | LINKML_C rebuilt from `compiler/gen_agent.py`: B2's semantic view tool (description less its claim on coverage, routed to stock_coverage) plus the generic tool; routing, coverage rules and the default unit in the generated orchestration; the common response (charter version 7); `tool_not_accessible: reject`. Published VERSION$3; A VERSION$3, B1, B2, D, D′ VERSION$4 (response sentence only); every LIVE, default and DESCRIBE equal to its file | measured |
| 72 | LINKML_B2_SV redeployed from the regenerated YAML with the same value grounding (contract version in the description only) | measured |

## Smoke of C (10 calls)

| # | Finding | Tag |
|---|---|---|
| 73 | **9 correct, 1 manual (G2)**; routing 10 / 10 (stock_coverage for the six coverage turns, b2_semantic_view for CS_LAST_MONTH_GAP, G1, G2, none for T6); every warning relayed with its number (T2 2, T5 5, BEYOND_H 2), flags explained, the fan-out refusal with its values from the tool | measured |
| 74 | G2: the ten country values came as a `response.table` event that `run_call.py` does not keep in the answer text; the text names four countries (right at 0.1 million); SQL without any item join. Manual, for the owner | measured |
| 75 | T5: the model refused packs itself and answered in QTY_EQ (2.37), as in session 7 (`model_refusal_with_qty_eq_answer`): the procedure's raw-unit refusal is still not reached (decision 7's rule for the campaign) | measured |
| 76 | **Tool span 4.12 to 4.73 s (median 4.20) against about 8.5 s in sessions 7 and 8a: the 4.3 s projection holds**; the CALL takes 3.44 to 4.14 s inside the agent, the span ends 0.21 to 0.81 s after it | measured |
| 77 | **Coverage turn, client total: median 13.2 s (12.5 to 14.5) against 17.5 s (session 7) and 17.1 to 17.6 s (session 8a)**; planning, response and suggested queries unchanged | measured |
| 78 | Input tokens: about 56,000 to 57,000 per coverage turn (session 8a about 49,000: the second tool's description and the longer orchestration in each of the three steps), about 156,000 per semantic view turn (B2's size), 36,705 without a tool. Token credits not readable with the project role: about 0.019 to 0.020 per coverage turn projected from session 8a | measured (tokens); credits: inferred |
| 79 | Version served: VERSION$3 (the default) on every turn | measured |

## Hypotheses of the charter for C

The charter (section 3) states no hypothesis for C; H-ALL-1 names A, B1, B2, D and D′ only. Not applicable. What the
smoke shows for the campaign's comparison B2 to C (the procedure) and C to D or D′ (the computing mechanism) is
recorded above (73 to 78) and will be read across repetitions.

## Open questions (session 8b)

1. Contract rule (69): should DATA_QUALITY_FAILED and HORIZON_NOT_LOADED refuse only the requests that use the faulty
   table's columns (as the owner expected), or every request (the contract's TABLE scope today)?
2. G2 (74): grade the `response.table` content as part of the answer (a harness change before the campaign), or not.
3. The B2 enriched-YAML test now passes after the redeployment; the B2 view's description carries the contract
   version, so every contract version bump changes B2's semantic model text: keep it, or drop the version from the
   generated description.
4. The campaign plan (`eval/campaign.md`): which option, and the per-call trace polling (warehouse 12 against 3.5
   credits).
5. Register D034 (fan-out with NULL) stays open (owner's answer, 8b).

# Phase 4 notes, part 5: session 8c-0, coverage is a time measure on a governed basis

> Session 8c-0, 2026-10-05. Tags as in parts 1 to 4: **[documented]**, **[measured]**, **[inferred]**. Evidence:
> `snowflake/phase4_basis/results.md`; run folder `~/work/assets/linkml-metrics-runs/s8c0/`, outside the repository.
> Contract 0.4.2 to 0.5.0, metamodel 0.3.0 to 0.4.0, rubric version 2 to 3; charter version 8 prepared, not published
> (step 5 waits for the owner). Agent calls: none so far (budget s8c0: 9).

The five questions are those of a stock manager and a finance controller: what runs out, what first, what sleeps and
what it costs, and on which basis the figure is comparable.

| # | Choice or finding | Tag |
|---|---|---|
| 80 | The result of coverage is always in months; QTY_EQ and VALUE are bases on which stock and forecast are measured, not units of the result. The 0.4.2 artifacts said otherwise in three places (the generated default-unit sentence read by B2 and C, DEFINITION.md section 8, the parameter name `unit_variant`), and QTY_EQ added kg and L | documented |
| 81 | No item carried its dimension (`raw_unit` is a pack size shared by kg and L items); the family carries it without a new fact: 3 VOLUME families (12 items), 11 MASS. Path 1 (owner): declared per family and written to DIM_ITEM in the published dataset; no 1 L = 1 kg convention | measured |
| 82 | Both fact tables (and the four other dimensions) byte-identical, locally (sha256) and on the account (count, HASH_AGG, comment), after a DIM_ITEM-only reload (`load_snowflake.py --tables`) | measured |
| 83 | Validity of a basis judged on the rows and totals a call returns, after selection: NATIVE one item per row, QTY_EQ one dimension per row, VALUE always; the default basis is refused like any other (BASIS_NOT_COMPARABLE names the bases allowed), never switched. `totals` defaults to `[]`, so a selection call returns no total unless asked | documented |
| 84 | Grouping by the new `dimension` attribute makes QTY_EQ comparable where a group mixes kg and L (France x dimension: kg and L rows) | measured |
| 85 | France on QTY_EQ adds kg and L: 10.21 months; on VALUE 8.70. Pantry in Sweden: 6.49 against 10.84. The mix moves the number in both directions | measured |
| 86 | Stockout month = analysis month + ceil(coverage), coverage counting from the month after the analysis month: 0.5 and 1.0 from June 2026 both give July 2026 (owner's tests, at contract level and on both procedures) | measured |
| 87 | (e) at item x country: 28 of 220 rows (12.7 %) hold 31.05 % of the STANDARD stock value (70,987,982.99 of 228,619,582.07 EUR); worldwide the same question keeps 1 row and 20,000 EUR | measured |
| 88 | B1 is hand-written: exposing the dimension and the basis rule cost 7 changed or added lines and 5 removed in each of its two YAML files, plus 3 sentences of its agent text; B2, the closing view and C took it from the generators | measured |
| 89 | A semantic view keeps summing kg and L without complaint; the contract refuses. The gap is measured in the campaign, never asserted (owner) | documented |
| 90 | A procedure with a new argument list is created as an overload beside the old one: the old signature is dropped first | measured |
| 91 | Parity 181 / 181 at the first run; `tests/test_procedure.py` 113 / 113 on each procedure | measured |
| 92 | **Direct latency of the SQL procedure regresses: warm median 5.5 s (4.2 to 6.5, one 16.3 s outlier) against 3.48 s in 8b.** Child execution unchanged; the coverage statement compiles in 1.9 to 3.7 s (its CTEs per grain set and the post-processing block) | measured (cause partly inferred) |
| 93 | Rubric v3 on recorded answers: the 8b smoke answers of C fail the basis wording on T1, T2, T9, BEYOND_H; the session 7 fixture on T1, T3, T4, T7 (no basis named, or coverage "in QTY_EQ") | measured |
| 94 | Warehouse use of the session so far: about 65 minutes of an X-Small warehouse active, about 1.1 credits, about 4.3 USD at 3.90 USD a credit; not readable with the project role (WAREHOUSE_METERING_HISTORY returns no row) | inferred |
| 95 | Charter version 8 published: C VERSION$4, A VERSION$4, B1, B2, D, D′ VERSION$5; every LIVE, default version and DESCRIBE equal to its file; C's tool calls the 8-argument procedure with named arguments | measured |
| 96 | Through C (4 calls of 9): T1, T5, S_OWN_UNIT, DIM_MIX correct on rubric v3; every answer gives months and names its basis; DIM_MIX re-called on VALUE after BASIS_NOT_COMPARABLE and said why (kg and litres cannot be added). T5: C chose QTY_EQ by itself and never sent NATIVE | measured |
| 97 | **Stop condition hit on DIM_MIX**: C wrote a range of item coverages (lowest and highest of 26 rows) that it picked itself. Asked at a country grain, it requested sku_code rows plus a grand total, so the rows invited it | measured |
| 98 | **Every tool span landed on the 8.5 s step** (8.38 to 8.57 s; 8b: 4.1 to 4.7 s), CALLs 4.5 to 5.1 s above the 4.3 s point; coverage turns 15.7 to 20.9 s (one tool call) against an 8b median of 13.2 s | measured |
| 99 | Agent call window (UTC, 2026-10-05): 08:23:13.6 to 08:28:17.3 | measured |
| 100 | Charter version 9 (owner's grain rule, contract 0.5.1): asked for France, C called at country grain with no item rows and got the expected refusal, then 8.70 months on VALUE; ROWS_COMMENTED silent | measured |
| 101 | ROWS_COMMENTED (governance, outside correctness) fires on the step 6 DIM_MIX and T5 answers and on the step 7e S_DORMANT_VALUE answer (a range of coverages and a ranking by stock value derived by the model from the 28 rows, numerically right) | measured |
| 102 | Every list question carried its selection parameter (coverage_below 3, rank_first 10, coverage_above 12) | measured |
| 103 | Light coverage statement without selection: warm median 4.05 s (15 calls) against the 3.6 s target, about 1.4 s better than the step 3 statement; reverted (owner's rule), diff kept outside the repository | measured |
| 104 | Step 7e tool spans: 9.26, 8.77, 8.63 s on the 8.5 s step, 5.43 s once; coverage turns 15.0 to 21.2 s | measured |
| 105 | Rubric v3 false positive: "This uses stock in kg or L equivalent" read as a unit of coverage (S_STOCKOUT_COUNTRY) | measured |
| 106 | Agent call window of step 7e (UTC, 2026-10-05): 09:21:53.1 to 09:28:28.4 | measured |
| 107 | Latency closed (owner): direct CALL warm median 5.5 s, tool span on the 8.5 s step, coverage turn 15 to 21 s; no more latency work before the campaign | measured |
| 108 | Rubric 3.1: only a unit given to the coverage itself is wrong; naming the basis of stock and forecast is correct | documented |
| 109 | Campaign stop rules are harness-level only; ROWS_COMMENTED and FRESHNESS_STATED are measures. Labels `<CONFIG>_<QUESTION>_<stage>_r<n>`, a label with a log refused before any call | documented |
| 110 | Charter version 10 (data freshness line): C and B2 each ended T1 with "Data freshness" naming June 2026; B2 took the month from its own query filter, no extra query | measured |
| 111 | B2 on T1: the view's coverage metric did not run; the model computed 2.8 months from the stock and the cumulative forecast it read (256,113 input tokens, 30.6 s) | measured |
| 112 | Session 8c-0 totals: 11 agent calls of budget s8c0 (11), all as LINKML_SVC (UTC windows 08:23:13.6 to 08:28:17.3, 09:21:53.1 to 09:28:28.4, 09:42:21.5 to 09:44:21.5); warehouse about 2 h of an X-Small active from about 06:55 to 09:45 UTC, about 2 credits, about 7.8 USD at 3.90 USD a credit (not readable with the project role) | measured (calls), inferred (warehouse) |

## Open after the campaign (not built)

1. Declared list statistics (owner, decision 7 of step 8). The contract could declare the statistics a list answer may
   carry: the count, the stock sum per unit, and the lowest and highest coverage of the kept members, which are valid
   on a non-additive measure, unlike a sum or a mean of coverages. The procedure would return them in the selection
   summary, so the model reads them instead of deriving them (the range C derived in steps 6 and 7e, numerically right
   but produced by the model).
