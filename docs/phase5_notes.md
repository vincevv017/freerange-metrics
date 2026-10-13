# Phase 5 notes, part 0: session 8c, campaign ready, hard questions held out, governance measured

> Session 8c, 2026-10-05. No agent call, no CREATE or ALTER, no change to a frozen object (agent spec, instruction,
> tool description, skill, procedure, view, contract, charter). Tags: **[documented]** (Snowflake docs, the contract,
> the owner's decisions), **[measured]** (run on this account or on recorded logs, evidence in the repository),
> **[inferred]**. Records: `eval/campaign.md`, `eval/gate.md`, `eval/governance.md`.

## Preconditions

| # | Finding | Tag |
|---|---|---|
| 1 | git clean, HEAD = origin/main = 655888d; identity Vincent Vikor, noreply address of vincevv017; gh active account vincevv017; venv Python 3.12.14 | measured |
| 2 | The six agents equal their files: LIVE, default version and DESCRIBE AGENT; C and A VERSION$6, B1, B2, D, D′ VERSION$7. STOCK_COVERAGE has the 8-argument signature only (STOCK_COVERAGE_PY kept beside it) | measured |

## Harness (step 1)

| # | Choice or finding | Tag |
|---|---|---|
| 3 | `run_call.py` already kept the REST usage of each call; it now keeps every table of the answer (title, columns, rows, query id) from the `response.table` events and the final response's table blocks, once each, and the turn's tokens summed over its calls | measured (tests) |
| 4 | G2 of the 8b smoke, regraded with its table (no new call): manual on the text, correct with the table (10 rows match at full precision). The text named SE at 14.5 million, which also matches the fan-out value; the table's full-precision value decides (rubric 3.2) | measured |
| 5 | **Incident: `pytest tests/` was run without excluding `tests/test_procedure.py`, which calls the procedure on the account: 117 CALLs of STOCK_COVERAGE (read only, no write, no agent call) from 10:05 to 10:15 UTC, about 585 s of the X-Small warehouse, about 0.16 credit (about 0.6 USD), as perso.** Stopped; since then every test that touches the account is announced before it runs (owner) and `tests/test_procedure.py` is excluded | measured (QUERY_HISTORY_BY_USER) |
| 6 | Token ceilings recomputed from the smokes: the largest call per configuration is B2 292,797 (T9, session 8) and C 157,011 (CS_LAST_MONTH_GAP, 8b, through the semantic view), not the 256,113 and 91,660 quoted; the 1.5 rule applies as coded (owner), values in `eval/campaign.md` | measured |
| 7 | Credits per token from the billed rows of sessions 3 and 5: cache write 1.625, cache read 0.13, output 6.5 AI Credits per million tokens; uncached input 1.3 | measured; uncached: inferred |
| 8 | A guard on the turn's summed tokens would stop every D′ coverage turn (two or three calls of about 100,000 to 236,000 each); the guard is per REST call, as the owner's "maximum per call" reads | inferred |
| 9 | The campaign runner does not poll traces per call (about 65 s a call in 8b); `campaign.py traces` reads them once per agent after a stage | documented (decision 4) |
| 10 | Several streams share one run folder: `calls.json` and the `.jsonl` logs are written under a file lock; a requests timeout is now a counted, failed call (status 0) instead of a crash | measured (tests) |

## Held-out questions (step 2)

| # | Choice or finding | Tag |
|---|---|---|
| 11 | Stage 1 questions, by arithmetic: trivial (one member, flat forecast or nothing to interpolate) T8, NO_DEMAND, G1, G2; hard: T1, T7, BULK_SCOPE_DRILL (totals and drill), T2, T4, S_OWN_UNIT (irregular or sparse forecast, interpolation), BEYOND_H, T3, BULK_SCOPE, T5, T6, T7_R1 (refusals), T9 and the three closing-stock questions (gaps), DIM_MIX (mixed dimensions), S_STOCKOUT_COUNTRY, S_FIRST_WORLD, S_DORMANT_VALUE (selection) | inferred (classification) |
| 12 | Four held-out questions, `held_out: true`, through `data/traps.yaml` and the generator: H_LOCAL_STOCKOUT (Q1, 14 items), H_LOWEST_COUNTRY (Q2, PL 2.16 months, kg basis), H_STOCKOUT_2027 (Q3, 35 items), H_STOCKOUT_ES (Q4, 3 products); values from both oracle references, which agree (`tests/test_reference_oracle.py`) | measured |
| 13 | Each separates by construction: Q1 needs two cascades at two grains and an intersection (12 items stock out locally but cover 6 months or less worldwide; SKU-0011 at 6.09 and SKU-0021 at 6.18 sit on the line); Q2's mean-ratio shortcut puts CH lowest (1.83); Q3's window has SKU-H06 at exactly 6.0 (December 2026, out) and SKU-H03 at exactly 7.0 (January 2027, in), "above 7" gives 25 items and no upper bound 36; Q4's mean-ratio shortcut keeps SKU-0001 and SKU-0025, one right of three | measured |
| 14 | C's frozen instructions and tool can express all four: Q1 as two calls (the pairs clause and the worldwide clause of the grain rule) and an intersection of codes, which sits against the letter of "never sort, filter or pick coverage rows yourself"; recorded as a finding, C unchanged; the rubric allows the intersection (not a computation on coverages). Q2 needs C to read "which country" as a list of countries (grain country_code, rank_first 1): the grain rule names lists of products and one figure for a scope, not a list of countries. Q3 needs the window derived from the stockout-month rule (coverage_above 6, coverage_below 18, a window the tool documents) | documented (instructions read) |
| 15 | Q2 names the family as the other questions do ("breakfast cereals"): C maps it through its tool description (BREAKFAST_CEREAL = Breakfast cereals); B1, B2, D and D′ through an enumerated FAMILY_NAME; A through the FAMILY_NAME column of its Autopilot view, whose three sample values do not include it | documented (view files read) |
| 16 | Rubric 3.2, tests first, before any graded turn: tables graded with the text, the precision rule of `decide()`, criteria item_set and lowest_member; on the 59 recorded turns of sessions 7, 8, 8b and 8c-0 only G2 of 8b moves (manual to correct) | measured (tests) |
| 17 | Budget `manual` in `run_call.py`, 20 calls, labels `<CONFIG>_<QUESTION>_manual_r<n>`, for the owner's replays; no call made by the session | documented |

## Gate (step 3)

| # | Choice or finding | Tag |
|---|---|---|
| 18 | The gate compares the answer's figure (the candidate nearest to the expected value), not every number of the answer: with every number, CS_LAST_MONTH_GAP was selected on A's and B1's history figures (400, 350), which the owner ruled correct | measured (tests) |
| 19 | Parameters are compared on what the answer says it used (month, basis, default scope), among answers that give a figure: on T6 every configuration asks for the month and nothing else is compared. Grain is not compared as such (no common surface); it shows in the figure, the products or the verdict | inferred |
| 20 | On the recorded smoke, the gate selects T1 and T9 and leaves T6 and CS_LAST_MONTH_GAP; T9 is wrong for every configuration under rubric 3.x (wording), so it is selected on failures, not on a difference of mechanism | measured |

## Governance (step 4, `eval/governance.md`)

| # | Choice or finding | Tag |
|---|---|---|
| 21 | B2's generated instructions do not carry the grain rule of charter version 9 (C, A, B1, D, D′ do) | measured |
| 22 | Business rules read per turn: 3,440 (B2; 3,893 after charter 11) to 13,000 characters (D), against 60,000 to 290,000 input tokens per call; C reads the most rule text after D and has the smallest turns | measured |
| 23 | Horizon drill (24 to 18, throwaway branch, deleted, main unchanged): 9 generated files plus B2's enriched YAML regenerated; hand edits in DEFINITION.md (A, D, D′), B1's instructions and two view files, the skill's two files, and the contract's own BEYOND_HORIZON text, which the generators copy into C's tool description and B2's view; 6 agents, 2 views, 1 procedure, 2 skill stages to redeploy | measured |
| 24 | No graded expected value of the 28 reference questions changes with H = 18; 9 of 220 item-country rows change on QTY_EQ (8 become BEYOND_HORIZON); the test suite does not detect the change except through one grader test on a recorded answer | measured |
| 25 | A generated file can be silently wrong: hand text inside the contract ("24-month horizon") passes every drift test | measured |
| 26 | Traceability: C and D′ trace the figure itself to query ids (procedure lineage; the script's output); A, B1, B2 and D trace the inputs only, the figure is the model's; `sql_execution.final_sql` was absent from every recorded trace | measured |
| 27 | Only C can return a coded refusal (21 codes); every other configuration declines in prose or answers | documented |

## Cost model and plan (step 5, `eval/campaign.md`, `eval/cost_model.py`)

| # | Choice or finding | Tag |
|---|---|---|
| 28 | The credits per token reproduce the billed per-turn ranges of session 8 for A, B1 and D | measured |
| 29 | Stage 1 expected: 12.1 AI Credits (24.2 USD) plus about 5.8 USD of warehouse, about 30 USD against a 25 USD ceiling; the 90 percent guard (22.5 USD on AI Credits) would stop the stage at about the end of A's block, before C, in the drawn order | inferred |
| 30 | Stage 2 at the decided repetitions does not fit 52 USD: 124 USD expected for 14 discriminating questions; after cuts 1 and 2 it fits only up to 4 discriminating questions; the 4 held-out questions alone cost about 22 USD after cut 2 | inferred |
| 31 | All together, about 90 USD expected against about 90 (71 low, 113 high), with stage 2 after cuts 1 and 2 and about 4 discriminating questions | inferred |
| 32 | Cache writes are most of every turn's credits: each planning step writes the previous tool result | measured |

## Charter version 11 and the owner's decisions after step 5

| # | Choice or finding | Tag |
|---|---|---|
| 33 | **A charter rule missed a generated target**: version 9's grain rule never reached B2, whose instructions are generated by `compiler/gen_native_sv.py`, a generator the charter row did not name; the identity test of session 8c-0 listed C, B1, A, D and D′, not B2. Fixed in the generator (the owner's text verbatim, 453 characters, nothing else in the spec), charter version 11 (conformity, no new rule); `tests/test_charter_conformity.py` reads every imposed sentence from the charter and checks the six configurations; it failed on B2 only, before the fix | measured |
| 34 | Open, after the campaign (owner, decision 5): the contract's hand-written "Stock outlasts the 24-month horizon" (BEYOND_HORIZON) and "whose 24-month forecast window" become a template on the horizon ({H}); the horizon drill is then run again | documented |
| 35 | Token guard per REST call confirmed (owner, decision 4) | documented |
| 36 | Owner's decisions after step 5: stage 1 ceiling 40 USD, pause at 36 USD, the estimate counting AI Credits and the warehouse hours elapsed; a pause holds until the owner resumes with a new ceiling. Stage 2 repetitions in all: B2, C, D′ 5; B1, D 3; A 3; its size is set at the cost read with what remains under about 90 USD; cuts 1 and 2 change nothing at these counts | documented |
| 37 | Stage 1, the guard's estimate: about 25 / 30 / 38 USD (low / expected / high); the expected run ends before the pause, the high one pauses during the last block (C) | inferred |
| 38 | Stage 2: about 46 USD remain at the expected stage 1 cost, about 7 discriminating questions plus the 4 held-out ones; at 35 / 40 / 45 USD, 4 / 5 / 6 discriminating questions at the expected cost | inferred |
| 39 | Power, one method: the exact (Clopper-Pearson) one-sided 95 percent upper bound of the failure rate at zero failures, 1 − 0.05^(1/n): 13.9 percent for 20 trials (5 repetitions on 4 discriminating questions), 7.2 percent for 40; differences smaller than that are not claims the campaign can make. Wilson's bound at zero failures (16.1 percent for 20) stays in a note of `eval/campaign.md` | documented (formula), inferred (trial counts) |
| 40 | B2 republished for charter version 11 by the five-beat cycle, no agent call: VERSION$8 served, LIVE, default and DESCRIBE equal to `generated/agent_b2.yaml`; C and A VERSION$6, B1, D, D′ VERSION$7 unchanged and equal to their files (2026-10-05, 11:08 UTC). Frozen state in `eval/campaign.md` | measured |
| 41 | Session 8c warehouse use, deduced (not readable with the project role): the 117 test CALLs of 10:05 to 10:15 UTC (about 585 s of query time), a few INFORMATION_SCHEMA reads for the account checks, each with the warehouse's minimum billing and auto-suspend tail; SHOW VERSIONS, DESCRIBE AGENT and the publish cycle need no warehouse. About 0.2 to 0.3 credit, about 1 USD at 3.90 USD a credit. No agent call, so no AI Credits | inferred |

## Pre-stage-1 harness fix: the served version on every call

| # | Choice or finding | Tag |
|---|---|---|
| 42 | Before the fix, each call recorded the answer text, every table, the turn's tokens, the model (in the raw REST usage only), the request id and the UTC window, not the served agent version: it is only in the trace (`snow.ai.observability.object.version.name`), the campaign runs `--no-trace`, and `campaign.py traces` saved the rows per label without extracting it | measured (code read) |
| 43 | `run_call.py` writes `model` (the orchestration `model_name` of the REST usage, not the guardrail's) and `served_version` (null at call time) into every summary | measured (tests) |
| 44 | Before each block, `campaign.py` reads the agent's default version with SHOW VERSIONS (perso, LINKML_METRICS_ROLE, as `agents.py`; no warehouse) into the block state (`declared_version`); a version other than the frozen state of `eval/campaign.md`, or no version read, stops the block before its first turn and holds the stage (`CampaignGuard.halted`, kept on resume) | measured (tests, no call) |
| 45 | `campaign.py traces` writes each turn's served version and trace row count into its summary, then checks the stage: equal, differ (a harness event for the owner, never regraded silently), no trace, no version. Tested on C's G2 trace of the 8b smoke (VERSION$3, C's default then; 10 rows in the turn's window) | measured (tests, recorded trace) |
| 46 | Still not recorded: the served version is known only after the trace read, which is best effort and late (a turn with no trace row has none); the declared version is read once per block, so a republish inside a block shows only in the trace; warm-up turns and failed attempts are not checked; the agent spec itself is not stored per call (the frozen state and SHOW VERSIONS stand for it) | inferred |

# Phase 5 notes, part 1: session 8c-1, D′ skill load

> Session 8c-1, 2026-10-05, 18:49 to 19:05 UTC. Troubleshoot only: no CREATE, ALTER or DROP, no PUT, nothing saved from
> the Snowsight agent screen; one question to LINKML_DP (budget `manual`, 3 REST calls), no other agent called. Every
> account read as LINKML_SVC, LINKML_METRICS_ROLE, `USE SECONDARY ROLES NONE`, warehouse woken first (D032). Tags:
> **[measured]**, **[documented]**, **[inferred]**. Raw logs outside the repository: `linkml-metrics-runs/s8c1/`
> (Snowsight traces), `linkml-metrics-runs/manual/` (the REST call, its events, trace and client-side SQL). The owner's
> person user is written `<OWNER_USER>` and another project's role `<OTHER_ROLE>`.

## Question and verdict

Does LINKML_DP load its skill and answer correctly over REST as LINKML_SVC, after the owner's Snowsight chat got
`Skill not found` (error 500) on it? **Over REST the skill loads** (VERSION$7, LINKML_SVC): the 500 happens from
Snowsight only. **No figure was produced**: the turn reached the per-question cap of 3 REST calls before the approved
script run was sent. Outcome 2 of the brief (the skill loads, the answer is not correct): reported, nothing fixed.

## Pre-flight (step 0)

| # | Finding | Tag |
|---|---|---|
| 47 | git clean; HEAD = local origin/main = 81e516d, one harness-only commit (served version) on top of 94f5217, the brief's base; no frozen object in it. `git fetch` failed (remote not reachable with the local credentials), so origin/main is the local ref | measured |
| 48 | DESCRIBE AGENT LINKML_DP equals `agent_dp.yaml` three ways: parsed (as `agents.py versions`), canonical JSON bytes (sha256 prefix 3098fde2686b4bb7 on both), and with whitespace-normalised instructions (as the conformity tests). Default VERSION$7; LIVE equal to the file; VERSION$1 to $6 differ (history) | measured |
| 49 | Stage SKILLS_DP, files read back with GET as LINKML_SVC into a temporary folder, then deleted: SKILL.md 3,369 B, sha256 c049ef44…; coverage.py 4,669 B, sha256 4bf0ce06…; both equal to `snowflake/phase4_others/skill/linkml-coverage/`. LIST shows 3,376 and 4,672 B, the next multiples of 16: the stored (encrypted) size, not a drift. LINKML_SVC reads the stage with its single role; the stage and the agent are owned by LINKML_METRICS_ROLE | measured (sizes, hashes); the padding reading inferred |
| 50 | Directory tables of SKILLS_DP and SKILLS_D: last refreshed 2026-10-04 21:40 and 21:41 UTC, AUTO_REFRESH false, so before the 08:21 UTC re-stage. Same on both stages; D loads from its stage in Snowsight and D′ from its stage over REST, so this does not separate failure from success | measured (state); not the cause, inferred |

## Oracle (step 1)

| # | Finding | Tag |
|---|---|---|
| 51 | SKU-0001 x IT, June 2026, default scope (STANDARD), QTY_EQ: the pandas cascade and the DuckDB set-based reference (`data/coverage_ref.py`) both give 4.452554744525547 = 4 + 248/548. S = 1,907 kg; forecast from July 2026 317, 422, 385, 535, 548 (C(4) = 1,659); stockout November 2026; one item of one dimension (kg); no BULK stock; latest stock month June 2026. Equal to the owner's hand check | measured |

## Snowsight traces (step 2, read with the project role)

| # | Finding | Tag |
|---|---|---|
| 52 | Three failed D′ turns from Snowsight: `00000008-0000-4000-8000-000000000008` (18:24:37 UTC), `00000009-0000-4000-8000-000000000009` (18:45:35), and `0000000a-0000-4000-8000-00000000000a` (18:52:33, after the brief's window). All: user `<OWNER_USER>`, served version **LIVE** (not VERSION$7), client type `reasoningagent_snowflakeintelligence`. Span `CodeExecutionTool_skill`, 5 to 7 ms: status ERROR, code 500, `ToolError type=internal_error code=TOOL_INTERNAL_ERROR message=Skill not found: linkml-coverage`. The first turn then ran `glob` (span SUCCESS; no match, per the owner) | measured |
| 53 | Primary role: `<OTHER_ROLE>` for the first two turns, not LINKML_METRICS_ROLE as the brief says; LINKML_METRICS_ROLE for the third, which fails the same way. The primary role does not separate failure from success | measured |
| 54 | The `skill` tool's catalog (`<available_skills>` in the turn's `CodingAgent.Step-0` span): in the three Snowsight turns it lists bundled and profile skills only, no linkml-coverage and no `stage` location; in the REST turn it lists linkml-coverage with location `stage`. The skill never reached the Snowsight sandbox; no skill file reached it. Same symptom as session 2 ("the stage skill is never in it") | measured |
| 55 | Mount statements: each REST call of D′ ran, as LINKML_SVC / LINKML_METRICS_ROLE on LINKML_METRICS_WH, `DESCRIBE STAGE LINKML_METRICS.RAW.SKILLS_DP`, `SELECT SYSTEM$ALLOWLIST()` and `SELECT SYSTEM$GET_CUSTOMER_STAGE_PREFIXES()` within 2 s of its start: the sandbox mounts the stage in the caller's session. `<OWNER_USER>`'s history (QUERY_HISTORY_BY_USER, as far as the project role sees it) has none of them between 18:10 and 18:56 UTC, though it shows that user's other queries on the project's objects (C's procedure call, D's SQL). From Snowsight the mount was not attempted; it did not fail on the stage | measured (within what the project role sees) |
| 56 | D in Snowsight (`0000000b-0000-4000-8000-00000000000b`, 18:24:31, LIVE, `<OTHER_ROLE>`): the skill loads through `ServerSkillTool_linkml-coverage` (source category agent, 294 ms, SUCCESS), the server-side loader that `code_execution` uses, not the sandbox `skill` tool of `code_toolset_all` (D′). Session 3 measured the same split | measured |

## The REST call (steps 3 to 5)

| # | Finding | Tag |
|---|---|---|
| 57 | `DP_SKU0001_IT_manual_r1`, budget `manual`, `--policy dp --client-sql --turn-cap 3 --token-ceiling 353875`: `0000000c-0000-4000-8000-00000000000c` (18:52:52 UTC), `0000000d-0000-4000-8000-00000000000d` (18:53:10), `0000000e-0000-4000-8000-00000000000e` (18:53:32), all 200; trace: VERSION$7, LINKML_SVC, LINKML_METRICS_ROLE, client type `cortex_code_api`; `CodeExecutionTool_skill` SUCCESS, the tool result is SKILL.md | measured |
| 58 | Call 1 loads the skill and asks to run `coverage.py --as-of 2026-06-01 --stock-sql … --forecast-sql …` followed by `2>&1 \| head -60`: denied by policy `dp` (a redirection and a pipe), as the policy is written. Call 2: semantic context, then two client-side SELECTs run as LINKML_SVC (`0000000f-0000-4000-8000-00000000000f`, the 24 forecast months from 317; `00000010-0000-4000-8000-000000000010`, STANDARD stock 1,907). Call 3: asks to run `coverage.py --as-of 2026-06-01 --stock 1907 --forecast [24 pairs]`, allowed by policy `dp`; the turn cap was reached before the decision was sent. coverage.py never ran (no script query in LINKML_SVC's history); no answer text, no table | measured |
| 59 | Tokens of the turn: 407,816 input (128,321 cache write, 279,483 cache read), 1,797 output, largest call 169,292 (ceiling 353,875). 0.257 AI Credits, about 0.51 USD (`eval/guards.py` `credits`), plus the warehouse woken at 18:51 for the reads and the call (about 0.1 to 0.2 credit with its auto-suspend tail) | measured (tokens); USD inferred |
| 60 | Grade, rubric 3.2: no figure, no basis named, no stockout month, no freshness line. Numeric: no candidate and no refusal, so *manual* by the rule's letter; routing: the skill family (a script run) is absent, only the semantic view family was used. Not correct. The stop is the harness's turn cap, not the agent's refusal | measured |
| 61 | The inputs the agent fetched equal the oracle's (S = 1,907; 317, 422, 385, 535, 548, …). `coverage.py` run locally on the agent's own call-3 arguments returns 4.4526, "depleted within the horizon". A check of the inputs, not a graded answer | measured (local) |

## Harness observations (no change made)

| # | Finding | Tag |
|---|---|---|
| 62 | A D′ turn whose first script command is denied needs a fourth REST call (denial, client-side SQL, approval request, approved run); the per-question cap of 3 ends it with no answer. In session 8 every D′ turn used 1 or 2 calls and no first command was denied; D′'s stage 1 block cap (75) is 3 x 25. Whether D′'s turn cap is raised to 4 (block cap 100) before stage 1 is the owner's decision: a harness parameter, not a frozen object | measured (session 8 counts); inferred (consequence) |
| 63 | `run_call.py` reads the trace by time (from the turn's start less 5 s), not by request id: this turn's 21 rows include 5 rows of `<OWNER_USER>`'s concurrent Snowsight request `00000011-0000-4000-8000-000000000011` (LIVE, a bash span). `campaign.py traces` reads by window too, so such a turn would show the served versions [LIVE, VERSION$7] and be reported as "differ". Either filter the rows by the turn's request ids, or keep the six agents out of Snowsight during a stage | measured (rows); consequence inferred |

## Cause (inferred: no trace names it)

| # | Finding | Tag |
|---|---|---|
| 64 | Between the Snowsight failures and the REST success, three things differ: the client (Snowflake Intelligence, `reasoningagent_snowflakeintelligence`, against REST, `cortex_code_api`), the served version (LIVE against VERSION$7), and the session (a person user with secondary roles ALL against LINKML_SVC with one role). The primary role is ruled out (53). The traces show that the stage was never mounted from Snowsight (54, 55), not that a read of it failed. Most likely, the Snowsight path does not mount stage skills for `code_toolset_all`, for the caller's session or for the LIVE version: a platform behaviour, seen first in session 2 (person user, secondary roles ALL, `code_toolset_all`). The open combination of session 3 (a person user, a permanent agent with `code_toolset_all`) now fails from Snowsight. One call per hypothesis would separate them (Snowsight with secondary roles NONE; a REST call to LIVE); not done here | inferred |
| 65 | For the campaign, which calls over REST as LINKML_SVC, the Snowsight failure does not apply: the skill loads as frozen. D′ is usable as frozen for the skill load; the turn cap (62) is open for the owner | inferred |

## Proposal, not implemented: skill pre-flight in `eval/campaign.py`

Before the first block of a stage, after the version guard:

1. For every frozen spec of `eval/campaign.md`, read each `skills[].source` of type STAGE (D: `@…SKILLS_D/skills/linkml-coverage`,
   D′: `@…SKILLS_DP/skills/linkml-coverage`).
2. As LINKML_SVC, `USE SECONDARY ROLES NONE` (the identity the mount runs under, finding 55): `LIST @<path>/`; fail on a
   missing SKILL.md, on a repository file missing from the stage, or on a 0 B file (the session 4 empty mount).
3. GET the folder into a temporary directory, compare each file's sha256 with `snowflake/phase4_others/skill/<name>/`,
   delete the copies. Do not compare LIST sizes or md5 (encrypted size, finding 49).
4. Any failure holds the stage like the version guard (`halted`, kept on resume); the result and the hashes go to the
   state file.

Limit: on 2026-10-05 this check would have passed. The stage and the spec were right; the Snowsight failure is in the
path that mounts the stage, which only a call shows (finding 54). A warm-up turn that checks the `skill` span would
catch that, but warm-up turns are not traced (`--no-trace`).

## Addendum: Snowsight thread 1000000001 (read-only, 19:10 to 19:20 UTC)

> No agent call, no budget used, no CREATE, ALTER or DROP. Read as LINKML_SVC, LINKML_METRICS_ROLE (checked with
> CURRENT_ROLE before each read), `USE SECONDARY ROLES NONE`. Raw rows: LINKML_DP events from 18:10 UTC,
> `linkml-metrics-runs/s8c1/trace_thread1000000001_linkml_dp_from1810.json` (41 rows, 7 request ids).

| # | Finding | Tag |
|---|---|---|
| 66 | The thread id is in `RECORD_ATTRIBUTES` under `snow.ai.observability.agent.thread_id` (an integer), with `snow.ai.observability.agent.message_id` and, on the `CORTEX_AGENT_REQUEST` row, `snow.ai.observability.agent.parent_message_id`. The request id is on every row as `ai.observability.record_id`. A search for the value alone is not enough: 1000000001 is also the `snow.ai.observability.database.id` of LINKML_METRICS (all 41 rows) and the user id of LINKML_SVC (`snow.user.id`, `snow.ai.observability.user.id`); only the 11 rows with that value under `agent.thread_id` belong to the thread | measured |
| 67 | Thread 1000000001 has two request ids, one turn as the owner sees it. `0000000a-0000-4000-8000-00000000000a`, 18:52:33.929 to 18:52:44.229 UTC, message 1000000002, parent 0: Step-0 selects `skill`; `CodeExecutionTool_skill` 18:52:40.802 to .808, ERROR 500, `ToolError type=internal_error code=TOOL_INTERNAL_ERROR message=Skill not found: linkml-coverage`; Step-1 selects `bash` (tool id `toolu_bdrk_01A4SWg6…`) and the request ends. `00000011-0000-4000-8000-000000000011`, 18:52:55.397 to 18:52:59.950 UTC, message 1000000003, parent 1000000002: `CodeExecutionTool_bash` with the same tool id, 30 ms, SUCCESS 200; Step-2 writes the answer, with no further tool. Both: `<OWNER_USER>`, primary role LINKML_METRICS_ROLE, session 100000000000004, served version LIVE, client type `reasoningagent_snowflakeintelligence`. No glob or find span in the thread; the `find` the owner saw is the bash command | measured |
| 68 | The command text is not in the trace: tool spans and planning spans record `argument.name = command` only, no argument value and no tool output. The owner's `/usr/bin/find -L /workspace/ ~/.snowflake ~/.cortex -iname "*linkml*" -maxdepth 5` is known from the screen only; that it found nothing, and the refusal that followed, are not readable from the trace | measured (absence) |
| 69 | Not a new failure: 0000000a is the third turn of finding 52. What is new is its second half, 00000011, which finding 63 listed as a concurrent Snowsight request: it is the same turn, resumed after the bash step (in Snowsight a bash call is a separate request, linked by `parent_message_id` and the tool id). The two other turns are separate threads: 00000008 on 1000000005, 00000009 on 1000000006, each a single request | measured |
| 70 | Against the three known turns: same 500 and error body, same served version (LIVE), same client type; the catalog of every Step span in the thread lists 93 skills, location `bundled` only, no linkml-coverage (the REST turn 0000000c lists 94, with linkml-coverage at location `stage`). No mount statement: `<OWNER_USER>`'s history (QUERY_HISTORY_BY_USER, as the project role sees it) shows 18 queries from 18:17:24 to 18:24:53 UTC under `<OTHER_ROLE>`, none after, so none during the thread, and no DESCRIBE STAGE, SYSTEM$ALLOWLIST or SYSTEM$GET_CUSTOMER_STAGE_PREFIXES at all. Differences: primary role LINKML_METRICS_ROLE (as 0000000a already, finding 53); the second tool is bash where 00000008 used glob and 00000009 answered after the 500; the bash call is the only thread step that ran in the sandbox and succeeded, which shows the sandbox ran while no skill path was in it | measured; the last clause inferred |
| 71 | The harness can read both keys from the rows it already fetches (`SELECT *`). REST calls of the harness carry `agent.thread_id = 0` and no message id: the harness keeps the conversation on the client (`--thread`, `--save-thread`), not in a server thread. So the thread id cannot tie a REST turn's rows together; the request id can, and each call's id is already in the summary (`calls[].request_id`, `eval/campaign.md` line 51). On the 8c-1 REST turn, filtering by its three request ids keeps exactly its 16 rows and drops the 5 rows of 00000011 | measured |

**Proposal, not implemented (input to the open point of finding 63).** In `campaign.py traces` and `run_call.py`, keep
the time window to bound the read, then keep only the rows whose `ai.observability.record_id` is one of the turn's
`calls[].request_id`; count rows with another id as foreign rows and record their number in the summary. A turn whose
rows are all foreign, or with a call whose id has no row, is reported as `no_trace` rather than read from its
neighbours. Thread id is not used: it is 0 over REST. It would only help for Snowsight checks like this one, where one
visible turn spans several request ids. With this filter the stage would not need the six agents kept out of Snowsight.

# Phase 5 notes, part 2: session 9a, campaign stage 1

> Session 9a, 2026-10-06. Stage 1 run, graded, traced; no frozen object changed (agent spec, instruction, tool
> description, skill, procedure, view, contract, charter). Every agent call through `eval/campaign.py run --stage 1` as
> LINKML_SVC, budget `campaign`; account reads read-only. Results: `snowflake/phase5_campaign/stage1_results.md`.
> Tags: **[documented]**, **[measured]**, **[inferred]**.

## Preconditions and harness settings (step 0)

| # | Choice or finding | Tag |
|---|---|---|
| 72 | gh's active account was not vincevv017 at the start (as on 2026-10-05); switched, then `git fetch` and HEAD = origin/main = 5fe6e61. Identity checked after every commit | measured |
| 73 | D064: per-question cap 4 REST calls for D′ (3 elsewhere), D′ stage 1 block cap 100; the rule holds in stage 2 | documented (owner) |
| 74 | D065: `campaign.py traces` keeps a turn's rows by `ai.observability.record_id` among its calls' request ids; the window only bounds the read; foreign rows are counted; never thread id nor a bare number. On the 8c-1 recorded turn: 16 rows kept, 5 foreign. The window read by START_TIMESTAMP alone also dropped the `CORTEX_AGENT_REQUEST` row (no start time); it is now kept | measured (tests) |
| 75 | D066: skill pre-check before each stage, as LINKML_SVC: LIST, then GET to a temporary directory and sha256 against the repository. Passed at every start: SKILL.md 3,369 B (listed 3,376), coverage.py 4,669 B (listed 4,672), equal on SKILLS_D and SKILLS_DP | measured |
| 76 | Owner's decision: A is played in stage 1 as the "zero effort" reference point and is not repeated in stage 2 (`eval/campaign.md`) | documented |

## Guard events and the owner's harness fixes

| # | Choice or finding | Tag |
|---|---|---|
| 77 | The per-call token guard stopped D twice: BULK_SCOPE_DRILL (357,493 input tokens; the follow-up resends its parent's exchange, which no smoke had) and S_STOCKOUT_COUNTRY (746,962 on one call). Both answers were complete (status 200); both turns kept and graded as is (owner) | measured |
| 78 | One REST call of D sums every internal planning step: S_STOCKOUT_COUNTRY had 10 planning steps, the largest 86,455 input tokens, 657,755 over the steps, against 746,962 in the call's REST usage. The per-call guard therefore measured the number of steps, an agent behaviour; it is no stop condition any more | measured (trace); the reading inferred |
| 79 | Owner's fixes (tests first): a follow-up turn's token ceiling adds its parent's largest call (recorded only); the warehouse term of the cost estimate counts the blocks' windows, not the time since the stage started (a pause costs nothing); block caps 30 outside D′ and a cap reached by a block's last turn is no stop; a runaway guard per turn at 2 USD for the six configurations (`run_call.py --turn-usd-cap`, exit 4); a resumed block warms up again after 5 minutes; the guard keeps the stops the owner lifted (`lifted_stops` was lost on save) | measured (tests) |
| 80 | After the fixes the stage ran to its end with no guard firing; the largest turn cost 0.857 USD (D S_DORMANT_VALUE, 1,520,769 input tokens in one call, 104 s) | measured |

## Stage 1 measures

| # | Finding | Tag |
|---|---|---|
| 81 | 144 graded turns, the full manifest; 94 correct, 43 wrong, 7 manual. C 24 / 0 / 0; D 17 / 7 / 0; B2 15 / 9 / 0; D′ 14 / 8 / 2; A 13 / 8 / 3; B1 11 / 11 / 2. One turn per cell: no rate | measured |
| 82 | Every one of the 180 graded REST calls was served by its frozen version, read per call from its own trace rows; traces readable 16 minutes after the last call; no foreign row, no turn without a trace | measured |
| 83 | No statement failed on authorization. B2 had 38 failed SQL statements in 17 of 24 turns, 36 of them `invalid identifier`, and recovered on most turns; `Writing arbitrary SQL is blocked` came back 3 times (A 2, B2 1) | measured |
| 84 | The largest failure family is the wording rule of rubric 3.x (`basis_wording`): a sentence gives the coverage "in kg equivalent" or "in litres". It fails correct figures (T1 of B1 and B2, T8 of A and B1, T9 and NO_DEMAND of most configurations). C never fails it | measured |
| 85 | T7_R1 (an item with two lifecycle statuses): C and D′ refuse and name the duplicate master data; A, B1, B2 and D give the fanned-out figures. T7: B1, B2 and D give the naive-join 3.0 | measured |
| 86 | D′ states no freshness line on any of its 24 turns, though its response instruction asks for it and the trace shows that instruction (`agent.planning.instruction`) in the context of every planning step; D, with the same response instruction and `code_execution` instead of `code_toolset_all`, states it on 24 of 24 | measured; the cause (the toolset's loop) inferred |
| 87 | 15 answers start with a fragment of the agent's planning glued to the first sentence ("Run separately.", "Try with the semantic model flag.", "Simpler to rewrite line."): A 8, B2 4, D 3; none for B1, C, D′. Graded as is | measured |
| 88 | D′: 60 REST calls for 24 turns (1: 1 turn, 2: 15, 3: 3, 4: 5); 36 permission requests, 14 denied by the `dp` policy (loops, heredocs, pipes or `--help \| head` around `coverage.py`); 11 client-side SELECTs; S_FIRST_WORLD and S_STOCKOUT_COUNTRY reached the cap of 4 with no final answer | measured |
| 89 | D's `orchestration.budget` (120 s, 40,000 tokens): the seconds budget fired once (S_FIRST_WORLD, 130.5 s; the answer ends "I've reached the time limit for this request"); the tokens budget did not stop steps of up to 86,455 input tokens | measured |
| 90 | Cost per turn, estimated: C median 0.039 USD; B1 0.109; A 0.138; D′ 0.163; D 0.194; B2 0.208. Stage estimate 29.86 USD (12.08 AI Credits, 1.46 warehouse hours) against 40 | measured (estimate) |

## Gate

| # | Finding | Tag |
|---|---|---|
| 91 | The gate refuses while 7 manual verdicts are open (A T2, T9, CS_LAST_MONTH_GAP; B1 T4, CS_LAST_MONTH_GAP; D′ T2, T7); `eval/stage2.yaml` is not written. Over every combination of their outcomes, 19 questions are selected and only CS_LAST_MONTH_GAP depends on them; CS_FAMILY, CS_MIDDLE_MONTH_GAP, T5 and T6 are never selected | measured |
| 92 | Three questions are selected with no failed configuration: G2 on `value` for all six (the gate's absolute 0.05 tolerance applied to EUR amounts makes any rounding a difference), S_OWN_UNIT on `basis` for all six, T3 on `basis` for A and B2. The gate rule was written for months; whether it should apply to amounts is the owner's question | measured; the reading inferred |
| 93 | With 19 or 20 discriminating questions, stage 2 at the decided repetitions is far above the budget of the cost model (d about 7 at the expected cost); `drop_order` holds only G1 and T4. The cost read decides the size | inferred |

## Cost read (closing, 2026-10-07; `stage1_results.md` section 8)

| # | Finding | Tag |
|---|---|---|
| 94 | Billed stage 1: 12.0816 agent AI Credits (24.16 USD), 0.2909 guardrail AI Credits (0.58 USD), 2.0275 warehouse credits (7.91 USD); 32.65 USD in all against the harness's 29.86 (+9.3 percent) | measured |
| 95 | The agent credits equal the harness estimate call by call: `RATES` of `eval/guards.py` are the billing rates. The 15 percent rule of `eval/campaign.md` does not trigger on `RATES` | measured |
| 96 | The warehouse bills 1.3506 credits per hour of running time, not 1.0, and runs a 60 s auto-suspend tail after each stop: +38.9 percent against the harness's warehouse term. The 1.35 matches a Gen2 standard X-Small on AWS; not confirmed (`SHOW WAREHOUSES` was not in the approved read) | measured; the cause inferred |
| 97 | `CORTEX_AI_GUARDRAILS` is billed apart from the agent rows (about 0.35 credits per million guardrail tokens), and Cortex Analyst inside an agent is not (`CORTEX_ANALYST_USAGE_HISTORY` empty) | measured; the per-token rate inferred |
| 98 | Proposed, not applied: `WAREHOUSE_CREDITS_PER_HOUR` 1.35, 60 s per warehouse stop, a guardrail term; on stage 1 this gives about 32.69 USD against 32.65 billed | inferred |

## Manual decisions and the regrade (closing, 2026-10-07)

| # | Finding | Tag |
|---|---|---|
| 99 | Owner's rule `EXPECTED_FIGURE_ASSERTED_TRAP_FRAMED` (2026-10-07), beside `WRONG_VALUE_CITED_AS_HISTORY`: A T2, A T9, A CS_LAST_MONTH_GAP, B1 T4, B1 CS_LAST_MONTH_GAP, D′ T2 correct; D′ T7 wrong. Regraded: 100 correct, 44 wrong, 0 manual; A 16 / 8, B1 13 / 11, B2 15 / 9, C 24 / 0, D 17 / 7, D′ 15 / 9 | measured |
| 100 | **Grader issue, to fix after the campaign (no grader change now):** `month_numbers` takes every "<n> months" as a coverage candidate, and `matches` rounds the expected or trap value to the candidate's precision. On B1 T4 the trap 7.714 (`window_starts_at_as_of`), rounded to 0 decimals, matched "after 8 months" in "The running forecast total is 920 kg after 8 months", a count of forecast months, not a coverage. A false manual; the fix would exclude counts of elapsed forecast months ("after n months", "in month n") from the candidates, with a test on this answer | measured |
| 101 | D′ T7 has no figure because the `dp` policy denied `coverage.py` wrapped in `2>&1 \| head -60`, then `--help \| head`; gate.md section 2 counts a call the policy rightly denied as no harness event | measured |

## Harness changes, gate and sizing (closing, 2026-10-07)

| # | Finding | Tag |
|---|---|---|
| 102 | Harness commits, tests first: A out of the stage 2 plan and cost model; owner-forced questions (`--force`, `--forced-by`); gate tolerance of 0.5 percent on EUR amounts and no basis difference among correct answers; the figure-only score beside the primary; D′ 2.5 REST calls per question. 512 tests pass | measured (tests) |
| 103 | Figure-only score on stage 1: A 19, B1 19, B2 19, C 24, D 20, D′ 19 correct of 24 (primary 16, 13, 15, 24, 17, 15). The unit wording costs B1 6 turns and C none | measured |
| 104 | Gate: 16 questions (CS_LAST_MONTH_GAP forced; T9 forced and selected on its own), drop_order G1; G2, S_OWN_UNIT, T3 and T4 leave. T4 left too because, with B1 T4 decided correct, its only reason was basis wording; the proposal had predicted 16 without forcing, the gate gives 15 | measured |
| 105 | Stage 2 at 16 questions and Q1 to Q4: about 70 (median), 75 (mean) or 88 USD (own costs, heavy held-out). After cut 3 (G1) no ceiling up to 60 USD fits; at the mean, 5 gate questions fit under 40 USD, 7 under 44.35 (D060), 11 under 60. A further cut order is the owner's | inferred |

# Phase 5 notes, part 3: session 9b, reduced stage 2 (C and B2), campaign closed

> Session 9b, 2026-10-07. Owner's change of plan (08:39): stage 2 plays C and B2 only, ceiling 15 USD, pause at 13.5;
> stage 1 stays the article's table. No frozen object changed (contract 0.5.1, charter 11, rubric 3.2, C VERSION$6, B2
> VERSION$8). Every agent call through `eval/campaign.py run --stage 2 --plan reduced` as LINKML_SVC. Results:
> `snowflake/phase5_campaign/stage2_results.md`.
> Tags: **[documented]**, **[measured]**, **[inferred]**.

## Questions added in stage 2 and the grader (steps 1 to 3)

| # | Finding | Tag |
|---|---|---|
| 106 | The owner's first N2 ("closing stock at the end of each quarter from Q3 2025 to Q2 2026") had no expected value for three of its four quarters: SNACK_BARS holds no stock in CH before April 2026, both references return no row, and DEFINITION.md section 7 closes at 0 only a member with a snapshot in the period. Reworded by the owner to the months of Q2 2026 (900, 350, 450) | measured |
| 107 | On N2 the re-aggregation traps cannot be told apart: the mean of the child coverages (0 and 4.5) equals the expected 2.25, and their sum and stock-weighted mean equal SKU-H12's own coverage (4.5), which an answer may cite. None is declared; the only coverage trap is June stock carried at its last known value (4.0). A trap is declared only when its wrong value is distinct from the right one and from every legitimate figure of the answer | measured |
| 108 | N3 in France has no member set apart under the default scope; without it a BULK item (SKU-0015) appears as NO_DEMAND. No tie at the tenth place (6.217 against 6.741) | measured |
| 109 | Route both is a grader rule for two questions and two configurations (`ROUTE_BOTH` in `eval/grade.py`); the routing table of rubric 3.2 is unchanged and any other configuration stops the grader. Stage 1 regraded with the new grader: identical, turn by turn | measured (tests, regrade) |
| 110 | A two-part answer needs its candidates split: a coverage in months is never a closing-stock candidate, and "no stock" in the coverage sentence must not count as a zero closing stock (zero in words counts only in a sentence about the closing) | measured (tests) |

## Stage 2 run and grades (steps 4 and 5)

| # | Finding | Tag |
|---|---|---|
| 111 | 60 graded turns, 62 REST calls, every call status 200, no retry, no guard fired; harness estimate 11.29 USD against 15 (projection 11.69); window 07:11:41 to 07:44:34 UTC | measured |
| 112 | Every turn served by its frozen version (C VERSION$6, B2 VERSION$8), read from its own trace rows 80 s after the last call; no foreign row, no request id without rows | measured |
| 113 | C 27 of 30 correct (figure only 29), B2 20 of 30 (figure only 25); no manual verdict. Routing 30 of 30 for both; C took route both on all 4 N1 and N2 turns | measured |
| 114 | C over both stages, the 20 seen questions it played: 39 of 40 (one wording-rule hit on NO_DEMAND), figure only 40 of 40, an exact one-sided 95 percent upper bound of 7.2 percent on its figure error rate. Never-seen questions: C 8 of 10, B2 8 of 10 | measured |
| 115 | C's only figure failure: H_STOCKOUT_2027 announces "The table lists each item" and emits no table (no `response.table` event, no table block); the count (35) and the months are right, no product is named | measured (events) |
| 116 | B2 keeps the fan-out on T7 (3.0) and T7_R1 (two lifecycle rows), relays no warning (0 of 5), and states on 18 of 30 answers that the view's coverage metric did not run and that it computed coverage itself (H-B2-6) | measured (answer text) |
| 117 | **Grader issue, after the campaign (no grader change now):** 7 of the 13 failures are the wording rule of rubric 3.x alone, on sentences that give the unit of the stock or of the stock value ("2.16 months of coverage, from 82,070 kg of stock"; "(stock value in EUR)"), a closing-stock sentence naming "each month" (N2), or a pack size in a product name within 40 characters of "coverage" ("iced tea summer edition 1 L", "Oat cereal bar 1 kg", "Arabica beans 1 kg"). The last class comes from `COVERAGE_NUMBER_UNIT` (rubric 3.1); whether it also failed stage 1 turns was not checked. The owner's question, beside finding 100 | measured; the reading inferred |
| 118 | Cost per graded turn, harness estimate: C 0.038 AI Credits (stage 1 billed 0.032), B2 0.109 (0.102). C's dearest turns are N1 and N2 (0.076 to 0.080: two tool calls). Latency per turn: C median 17.5 s (max 24.3), B2 30.1 s (max 87.2) | measured |
| 119 | 5 B2 answers start with a planning fragment glued to the first sentence ("Model-level metric; try it without table join."); none for C (stage 1: B2 4, C 0) | measured |
| 120 | The billed cost of stage 2 is read on the owner's go only, after 10:45 UTC (statements in `stage2_results.md` section 7); expected about 12.4 USD with the measured warehouse rate and the guardrail | inferred |

## Session 9c: rubric 3.3 and the regrade (no call; owner, 2026-10-07)

> No agent call, no Snowflake call for this part.

| # | Finding | Tag |
|---|---|---|
| 121 | Rubric 3.3: the unit half of `basis_wording` reads the product names of DIM_ITEM without their pack size; the names come from `data/traps.yaml` hero_items, which are the `DIM_ITEM.sku_name` values of the published dataset, and a test checks them against DIM_ITEM (12 names carry a pack size, every other item is "<family> <n>"). Answers write the names in lower case and drop "(discontinued)", so the match ignores case and the parenthesis | measured (tests) |
| 122 | A coverage given in kg or L still fails under 3.3: the rubric's own examples and the failing answers of sessions 7 and 8b (T1, T3, T4, T7; T1, T2, T9, BEYOND_H) still fail. On the 59 recorded turns of sessions 7 to 8c-0, 3.3 moves two, both wrong to correct: B1 T9 and D′ T9 of session 8 ("Oat cereal bar 1 kg") | measured (tests) |
| 123 | Finding 100 closed: a whole number after "after" is no coverage candidate under 3.3; "after 8.5 months" stays one, and "in month 9" never was. B1 T4 of stage 1 is now decided by the number (8.5) without the owner's decision | measured (tests, regrade) |
| 124 | Stage 1 under 3.3: 112 correct, 32 wrong (3.2: 100 / 44). Twelve verdicts move, all wrong to correct and all on the product-name pack size: NO_DEMAND of A, B1, B2, D, D′ ("Iced tea summer edition 1 L"), T8 of A and B1, T2 of B1, BEYOND_H of B2 and D′, T9 of B2 and D′. C stays 24 / 0 | measured |
| 125 | Stage 2 under 3.3: C 28 / 2, B2 22 / 8 (3.2: 27 / 3, 20 / 10). Three verdicts move, wrong to correct: C NO_DEMAND, B2 NO_DEMAND, B2 T9. C over both stages: 40 of 40 on the primary verdict for the seen questions, bound 7.2 percent on the score of record | measured |
| 126 | The figure-only score does not move in either stage: the product-name class is exactly the unit half the figure-only score leaves out. Of the 7 wording-only failures of stage 2 (finding 117), 3.3 clears 3; the 4 left give the unit of the stock or of the stock value beside the coverage, which (c) keeps failing (B2 BEYOND_H now fails on its stock sentence) | measured |
| 127 | NO_DEMAND under 3.2 failed on a turn with no coverage figure: `basis_wording` applied only because the product name's "1 L" fired the 3.1 number-and-unit pattern. Under 3.3 the criterion does not apply there, as the rubric text says (it applies to answers that give a coverage figure) | measured |
| 128 | **Owner's question, no change (c):** the naming half of `basis_wording` reads the "1 kg" of a product name as QTY_EQ named. Four turns pass it only that way (stage 1 A BEYOND_H, C T2; stage 2 C T2, C T8); they name the item's own unit (PACK_1000), which the rubric text accepts for one item and the grader does not read for a QTY_EQ question. No verdict depends on it under 3.2 or 3.3 today | measured; the reading inferred |
| 129 | Other counts of forecast months stay coverage candidates under 3.3, since the owner's rule names "after n months" only: "the first 8 months" (A and B1 BULK_SCOPE, B2 DIM_MIX), "within 3 months" (selection questions), "22 months that have demand" (B2 BEYOND_H). None decides a verdict in either stage | measured (answer text); "none decides" measured on the regrade |

## Session 9c: the billed cost of stage 2 and of the campaign (`stage2_results.md` section 7)

> Read on the owner's go at 11:11 UTC, ACCOUNTADMIN for one read-only batch, the statements of section 7 as written.
> Rubric 3.3 frozen by the owner; findings 128 and 129 stay documented limits.

| # | Finding | Tag |
|---|---|---|
| 130 | Stage 2 billed 12.28 USD against the harness's 11.29 (+8.7 percent): agent 4.5800 AI Credits (9.16 USD), guardrail 0.0846 (0.17 USD), warehouse 0.7571 credits (2.95 USD). C 3.59 USD (+10.2 percent), B2 8.69 (+8.1 percent). Under the 15 USD ceiling, and 1 percent under the expected 12.4 | measured |
| 131 | The 62 billed rows match the 62 calls by request id, one to one; each call's tokens at `RATES` give its `TOKEN_CREDITS` to within 3e-17 credit. The agent term of the harness is exact for a second stage running | measured |
| 132 | The guardrail costs 0.350 credits per million guardrail tokens: 0.084563 credits for 241,609 tokens on a day whose only agent use was the stage. Stage 1 had inferred the rate; it is now measured. No guardrail step on three calls: C's warm-up and T6 (no tool, a clarifying question) of C and B2 | measured |
| 133 | The warehouse bills 1.3505 credits per running hour (stage 1: 1.3506); the stage ran 2,018 s against 1,970 s of block windows, the difference being the 48 s auto-suspend tail after the last statement. Rate +0.75 USD, tail +0.07 USD, +38.4 percent on the warehouse term | measured |
| 134 | Cloud services: 0.0468 credits metered in the hour, 6.0 percent of its compute, under the daily 10 percent allowance; not counted as billed. The daily `WAREHOUSE_METERING` row of 2026-10-07 was not written at 11:11 UTC, so the adjustment itself is not read | measured; "not billed" inferred |
| 135 | The campaign billed 44.93 USD (stage 1 32.65, stage 2 12.28) against 41.15 estimated (+9.2 percent): agent 33.32 USD exact, guardrail 0.75, warehouse 10.86. The stage 1 correction proposal (1.35 per running hour, 60 s per stop, guardrail at 0.35 per million) would have estimated stage 2 at 12.30 USD | measured; the last figure inferred |
| 136 | Cache writes are 58.7 percent of stage 2's agent credits (stage 1: 56), cache reads 26.7, output 14.6. Per graded turn, billed: C median 0.0251, mean 0.0379, max 0.0802 (N1, two tools); B2 0.1093 / 0.1087 / 0.2327 (N3). B2 costs about 2.9 times C per turn | measured |
| 137 | `METERING_DAILY_HISTORY` shows `CORTEX_SEARCH` on 2026-10-07 (0.000072 credits); no harness object uses Cortex Search. Not read further | measured; the source unknown |

## Session 13: configuration C-raw, steps 1 and 2 (owner, 2026-10-08; `snowflake/session13_craw/results.md`)

> Read only on the account (`LINKML_METRICS_ROLE`, no secondary role), then offline. Nothing created, no agent call.

| # | Finding | Tag |
|---|---|---|
| 138 | `STOCK_COVERAGE` reads only RAW tables: no statement names `FCT_STOCK_SNAPSHOT_GAPFILLED` or `B2_FORECAST_SPINE`, every table name of its SQL being a literal. Agent C's closing-stock and general answers come from B2's view, whose `__stock` is the gap-filled view: C's score mixes both mechanisms | measured |
| 139 | The gap-filled view holds 63,428 rows for 60,915 snapshot rows (+4.1 percent) and scans 2.0 times the snapshot table for a one-quarter question (1.67 MB against 0.84 MB on the raw table, same answer 450); the forward spine holds 23,652 rows, 36 x 219 x 3, with 48 measure columns each, 24.7 times the forecast's measure cells. Neither is stored: both are views computed by each query | measured |
| 140 | Growth: the gap-filled view is the sum of each key's span from its first period to its last + 1, bounded by keys x periods, computed over the whole table whatever period is asked; the spine is analysis periods x item-location pairs x bridged statuses rows, times horizon x bases cells; at a daily grain both the analysis periods and the horizon grow about 30 times | inferred, from the generated SQL |
| 141 | On a coverage question, `STOCK_COVERAGE` scans 7.75 MB in 3 statements against 2.73 MB for B2's coverage metric (same 2.8): its context and in-call quality checks read whole dimensions and the forecast window. C-raw's gain is the absence of densified objects, not fewer bytes per coverage question at this scale | measured; cause inferred |
| 142 | By mechanism, every closing-stock and general turn of C is correct (stage 1 4 of 4 and 1 of 1, stage 2 8 of 8 and 1 of 1), all through B2's view; every coverage turn of C called the procedure. The classes sum to the published totals of every configuration, stage and rubric (`eval/mechanism_recount.py`) | measured |
| 143 | The contract's refusal templates name coverage or `as_of_months` in 8 of the 19 codes `CLOSING_STOCK` uses; the generator rewords those 8 for closing stock and stops if the contract's wording changes. The contract declares no period parameter and no closing-stock code of its own | measured, on the contract |
| 144 | Step 0: a plain `pytest` collected `tests/test_procedure.py`, the on-account suite (the offline suite is `--ignore=tests/test_procedure.py`, README), and ran it for 11 min 38 s as `LINKML_METRICS_ROLE` (read-only CALLs of `STOCK_COVERAGE`): 776 passed, 3 failed, 9 skipped. The 3 failures are N1 to N3 in `test_reference_question_expected_answer`, whose expected values have no `value` key (KeyError): the test predates the stage 2 shape. The offline suite then gave 663 passed, 9 skipped | measured |

## Session 13: C-raw created and checked (step 3, owner's go; `snowflake/session13_craw/results.md` section 3)

| # | Finding | Tag |
|---|---|---|
| 145 | `CLOSING_STOCK`, `LINKML_C_RAW_SV` and `LINKML_C_RAW` (`VERSION$2` default) are equal to their generated files; the six agents, both coverage procedures, the four generated views and the four semantic views read the same before and after | measured |
| 146 | Parity of `CLOSING_STOCK` with the gap-filled view summed under the closing rule: 12,304 members over 14 complete periods, 16 grains and 2 bases, 0 differences; the 12 refused calls are the basis rule (QTY_EQ where a row mixes kg and L) and the T7 fan-out (`lifecycle_status`); the partial years 2023 and 2026 are refused, their missing months named. The densified view and the question-time rule give the same closing stock on every member | measured |
| 147 | A `CLOSING_STOCK` call takes 6.4 s (median of 10 warm calls), 5.2 s of it compiling its three statements and 0.86 s executing them: at this data size its cost is compilation, not the absence of densified data | measured; the reading inferred |
| 148 | The smoke routed each question to the intended tool (closing stock to `closing_stock`, coverage to `stock_coverage`, the forecast to the view), with the right figures; a procedure turn reads 68,000 input tokens, the view turn 122,000 | measured |
| 149 | Two live tests were wrong, not the procedure: a QTY_EQ grand total over PANTRY is refused (flour in kg, oil in L), and a grand-total row entered a comparison of family totals; fixed in the tests | measured |

## Session 13: the C-raw arm (step 4, owner's go; `snowflake/session13_craw/results.md` section 4)

| # | Finding | Tag |
|---|---|---|
| 150 | C-raw played C's 24 and 30 questions: 21-3 and 26-4 under rubric 3.2 (C 24-0 and 27-3), 22-2 and 28-2 under 3.3 (C 24-0 and 28-2), figure-only 22-2 and 29-1 (C 24-0 and 29-1); every turn served `VERSION$2`, read from its trace | measured |
| 151 | Closing stock without any densified data: 11 of 12 closing-stock turns correct through `CLOSING_STOCK`, the gap questions (CS_LAST_MONTH_GAP, CS_FAMILY, N1, N2) all right; the twelfth, G2 of stage 1, gives the right figures in a table headed "EUR M", which the rubric's per-number scale reading does not match. No closing-stock question went to the view (H-CR-4 not observed) | measured |
| 152 | A closing-stock turn of C-raw reads 68,000 to 71,000 input tokens against 164,000 for C's view turn, and lasts 1.3 to 5.3 s longer (median per stage) | measured |
| 153 | Coverage, same procedure as C: equal under 3.3 in stage 2 (17-2), one turn apart in stage 1; every difference is the basis wording. C-raw passed NATIVE to `stock_coverage` in 13 of 46 calls, C in 7 of 45 | measured; the cause not established |
| 154 | The arm's harness estimate is 4.27 USD (0.024 to 0.025 AI Credits a call); steps 3 and 4 together 6.1 to 6.7 USD estimated, under the 9 USD pause; billed read pending | measured, the step 3 part inferred |
