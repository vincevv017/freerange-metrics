# Campaign plan (session 8c): two stages, not run

Harness: `eval/campaign.py` (runner), `eval/guards.py` (guards and cost estimate),
`snowflake/probe_b/mount/run_call.py` (one REST call as LINKML_SVC), `eval/grade.py` with `eval/rubric.yaml` version
3.2, `eval/gate.py` (the stage 2 selection rule, `eval/gate.md`). Charter `docs/configurations.md` version 10, contract
0.5.1. The configurations are frozen: any change to an agent spec, instruction, tool description, skill, procedure,
view, contract or charter restarts the campaign. Tags: **[measured]**, **[documented]**, **[inferred]**. The session 8b
plan this file held before is superseded (git history).

## Frozen state (2026-10-05, 11:08 UTC)

| Configuration | Agent | Served version (default, equal to its file: LIVE, SHOW VERSIONS, DESCRIBE AGENT) | Spec file |
|---|---|---|---|
| A | LINKML_A | VERSION$6 | `snowflake/phase4_others/a/agent_a.yaml` |
| B1 | LINKML_B1 | VERSION$7 | `snowflake/phase4_others/b1/agent_b1.yaml` |
| B2 | LINKML_B2 | **VERSION$8** (republished for charter version 11, grain rule; five-beat cycle, no agent call) | `generated/agent_b2.yaml` |
| C | LINKML_C | VERSION$6 | `generated/agent_c.yaml` |
| D | LINKML_D | VERSION$7 | `snowflake/phase4_others/d/agent_d.yaml` |
| D′ | LINKML_DP | VERSION$7 | `snowflake/phase4_others/d/agent_dp.yaml` |

Charter `docs/configurations.md` version 11, contract 0.5.1 (metamodel 0.4.1), rubric `eval/rubric.yaml` 3.2,
STOCK_COVERAGE with its 8-argument signature only. `tests/test_charter_conformity.py` checks every imposed sentence in
the six specs. From here, any change to a frozen object restarts the campaign. [measured]

## Frozen state, arm C-raw (session 13)

Owner, 2026-10-08: configuration C-raw played beside the campaign on exactly C's questions in C's order
(`eval/campaign.py --arm CR`: stage tags `craw-s1` and `craw-s2`, labels `CR_<QUESTION>_craw-s<n>_r<n>`). Charter
`docs/configurations.md` version 12; contract 0.5.1; rubric 3.2 (score of record) and 3.3, unchanged, with C-raw's
routing entry in `eval/grade.py` (`CR_ROUTING`). The indistinguishable-precision guard of G2 reads the parameters of
C-raw's `closing_stock` call as it reads those of `stock_coverage` (`CLOSING_SIGNATURES`): a C-raw-only adaptation of
the same rule (numeric.indistinguishable_precision), not a new rule. The six configurations above are not touched.

| Configuration | Agent | Served version (default, equal to its file: LIVE, SHOW VERSIONS, DESCRIBE AGENT) | Spec file |
|---|---|---|---|
| C-raw | LINKML_C_RAW | VERSION$2 | `generated/agent_c_raw.yaml` |

## Stages

| Item | Stage 1 | Stage 2 |
|---|---|---|
| Questions | the 24 of `generated/reference_questions.yaml` that are not held out | the questions `eval/gate.py` selects from stage 1 (`eval/stage2.yaml`), plus the 4 held-out questions (`held_out: true`) |
| Repetitions | 1 (it is repetition 1) | in all, stage 1 included (owner, decision 3 after step 5): B2, C, D′ 5; B1, D 3. **A: none in stage 2** (owner, session 9a: A is played in stage 1 as the "zero effort" reference point and is not repeated; this replaces A's 3 repetitions on its passed questions). A selected question runs r2 to rN in stage 2; a held-out question r1 to rN |
| Block | one per configuration: a warm-up call (not graded), then the questions back to back | one per configuration: a warm-up call, then all its repetitions back to back, question order shuffled per repetition |
| Order | configuration order and question order shuffled with fixed seeds (`SEED` in `eval/campaign.py`); BULK_SCOPE_DRILL right after BULK_SCOPE in its thread | the same; the drill's parent is added to any repetition that holds the drill |
| Labels | `<CONFIG>_<QUESTION>_campaign-s1_r1` | `<CONFIG>_<QUESTION>_campaign-s2_r<n>` |
| Cuts | none | fixed order (`--cut`): 1, D′ to 5; 2, B1 and D to 3 as well (both change nothing at the decided repetitions); 3, the least discriminating questions of `eval/stage2.yaml` `drop_order` removed (only one configuration differs, and only by warnings relayed, first), never a held-out question. The size of stage 2 is decided at the cost read |
| Streams | `--streams 1` (default; more only on the owner's go) | the same |

A turn that fails is retried under `campaign-s<k>-a<m>` (attempt m), so no log is overwritten; the state file
(`state_campaign-s<k>.json` in the run folder) records every attempt and the UTC window of every block. Traces are not
polled during the campaign (`--no-trace`): `eval/campaign.py traces --stage <k>` reads them once per agent after the
stage (decision 4), bounded by the stage's window, and keeps each turn's rows by request id (D065, owner, session 9a):
never by thread id (0 over REST) nor by a bare numeric value (ids collide across objects, `docs/phase5_notes.md`
finding 66). A manual call in Snowsight during a stage therefore stays out of the turns' traces; it shows as foreign
rows.

## Stage 2, reduced (owner, 2026-10-07, session 9b)

Change of plan: stage 2 is low cost. Stage 1 stays the article's table for the six configurations. Stage 2 plays **C and
B2 only**, on the same questions, reported by the route C is expected to take. A, B1, D and D′ are not played again.
`eval/stage2.yaml` stays as the gate wrote it in session 9a (evidence); the plan that runs is
`eval/stage2_reduced.yaml`, run with `eval/campaign.py run --stage 2 --plan reduced --ceiling-usd 15`. The state file
records the plan of the stage's first run and refuses a resume under the other one. Frozen as above (contract 0.5.1,
charter 11, rubric 3.2, C VERSION$6, B2 VERSION$8); the warehouse estimate fix proposed in session 9a is not applied.

| Item | Value |
|---|---|
| Turns per configuration | 30: repetition 1, Q1 to Q4 (the held-out questions) and N1 to N3; repetition 2, the 16 gate questions (BULK_SCOPE_DRILL in BULK_SCOPE's thread), G2, CS_FAMILY, CS_MIDDLE_MONTH_GAP, T6, and N1 to N3 |
| Questions added in stage 2 | N1, N2, N3 (`data/traps.yaml` `stage2_questions`, `added_in_stage: 2`); never in stage 1, never forceable by the gate |
| Blocks | C then B2 (the seeded stage 2 order), one warm-up each, question order shuffled per repetition with fixed seeds (SEED + 1000 x the configuration's index in the stage 2 order + the repetition) |
| Labels, caps | `<CONFIG>_<QUESTION>_campaign-s2_r<n>`; block cap (1 + 30) x 1.1 = 35; 3 REST calls per question; runaway guard 2 USD per turn |
| Calls | 60 graded turns, 62 REST calls expected |
| Ceiling | 15 USD, pause at 13.5 USD (90 percent) |
| Report groups | `eval/grade.py` `route_group`, by C's expected route: procedure (coverage questions, Q1 to Q4, N3), view only (closing stock, G1, G2), both (N1, N2), no tool (T6) |

**Route both (N1, N2).** C is expected to call the procedure and the closing-stock view (its semantic view tool) each
at least once in the turn; for B2 the expected route stays the view. A turn that answers both halves from one tool is
graded on its figures and fails the routing criterion. The rule lives in `eval/grade.py` (`ROUTE_BOTH`); the routing
table of rubric 3.2 is unchanged and no other configuration plays these questions. Each half of N1 and N2 is graded on
its own figures (closing stock: the numbers that are not a coverage in months; N2 per month; coverage: as a coverage
question). Stage 1 regraded with this grader: identical, turn by turn.

**Cost estimate** (`eval/campaign.py plan --stage 2 --plan reduced`, `eval/cost_model.py` `reduced_stage2`), from the
billed per-turn means of stage 1 (`snowflake/phase5_campaign/stage1_results.md` section 11: C 0.102 USD, B2 0.258 USD
a turn, all costs included) [inferred from measured costs]:

| | C | B2 | Total |
|---|---|---|---|
| 30 turns at the billed mean | 3.06 | 7.74 | 10.80 |
| Heavy case: the 8 list turns at the selection-question mean (C 0.093, B2 0.328) | 2.99 | 8.30 | 11.29 |
| Warm-ups (billed, C 0.0904 and B2 0.0929 credits) and 0.1 h of gaps at 1.35 credits an hour | | | 0.89 |
| **Stage 2** | | | **11.69 (mean), 12.18 (heavy)** against the 13.5 USD pause |
| What the harness guard will show (no guardrail, warehouse at 1.0 credit an hour) | | | 10.36 |

## What each call records (pre-stage-1 harness fix)

| Field | Source | Where |
|---|---|---|
| Answer text | final `response` event, text blocks | `summary_<label>.json`, `calls[].text` |
| Tables (title, columns, rows, query id) | every `response.table` event and the final response's table blocks, once each | `calls[].tables` |
| Tool uses, tool results (3,000 characters), warnings, permission requests and decisions, client-side SQL | the SSE events; `client_sql.py` | `calls[]`; `client_sql.jsonl` |
| Tokens of the turn (input, cache write, cache read, output, largest call) | REST usage, `usage.tokens_consumed[]`, role orchestration, summed over the turn's calls | `tokens` |
| Model | REST usage, `usage.tokens_consumed[].model_name` of the orchestration role (null if absent) | `model` |
| Request id | `metadata` event or final response, else the `X-Snowflake-Request-Id` header | `calls[].request_id` |
| UTC window, start and seconds of every call, time to first byte, HTTP status | the client | `window_utc`, `calls[]`; `calls.json` |
| Raw events | the SSE stream | `events.jsonl` |
| Declared version (the agent's default before the block) | `SHOW VERSIONS IN AGENT`, row `is_default` true, as perso with LINKML_METRICS_ROLE (as `agents.py`), no warehouse | state file, `blocks.<block>.declared_version`, `declared_read_utc` |
| Served version | trace attribute `snow.ai.observability.object.version.name` of the turn's own trace rows (as `snowflake/phase4_others/records.py` reads it); null at call time (`--no-trace`), written by `campaign.py traces` | `served_version` (a list if the rows carry several), `trace_rows`; `trace_<label>.json` |
| Own and foreign trace rows (D065, session 9a) | the turn's rows are those whose `ai.observability.record_id` is one of its `calls[].request_id`; rows in its window with a request id the harness never received are foreign, counted, not kept | `trace_rows`, `trace_foreign_rows`, `trace_foreign_ids`, `trace_ids_without_rows`; `versions_campaign-s<k>.json` `foreign` |

Version rule. Before each block, the declared version must equal this file's frozen state (the table above, read by
`campaign.py`); otherwise, or when it cannot be read, the block does not start and the stage is held (harness guard,
`version guard` in the state file; it does not lift on resume: the owner decides). After the stage, `campaign.py traces
--stage <k>` writes each turn's served version into its summary and prints the check (`campaign.py versions --stage <k>`
prints it again, no call; `versions_campaign-s<k>.json`): turns equal to the frozen version, turns that differ (listed),
turns with no trace row of their own or rows without a version name (listed), turns with foreign rows in their window
(listed). A turn served by another version is a harness event
reported to the owner, never regraded silently. The warm-up turns and the failed attempts are not checked (not graded).

## Guards (harness only; an agent's behaviour never stops anything)

| Guard | Value | Where |
|---|---|---|
| Calls per block, every REST call counted (approval and client-side resumes included) | stage 1: 30 per configuration, 100 for D′ (D064: 4 x 25 turns; 75 before session 9a); stage 2: the planned count plus 10 percent. Owner, 2026-10-06 (session 9a): 26 became 30 outside D′, because a one-call margin covered neither the warm-ups added on resume nor a retry after an error, and the cost protection is the pause at 36 USD; D and B1, started at 26, carry the override in their block state and in `calls.json` `_caps`; B2, A and C get 30 before their first call. A cap reached after the block's last turn does not count as a stopped block (no turn was prevented) | `run_call.py --block --block-cap`, cap fixed at the block's first call (an owner's override is written in `calls.json` `_caps` with its reason in the block state) |
| Calls per question | 3; 4 for D′ (D064, owner, session 9a, both stages: a D′ turn whose first script command the dp policy denies needs a fourth call, `docs/phase5_notes.md` finding 62) | `run_call.py --turn-cap`, `eval/guards.py` `turn_cap` |
| Skills (D066, owner, session 9a) | before a stage's first call (and on every resume), each STAGE skill path of the frozen specs (`@…SKILLS_D/skills/linkml-coverage`, `@…SKILLS_DP/skills/linkml-coverage`) is listed, then read back with GET as LINKML_SVC (`USE SECONDARY ROLES NONE`) into a temporary directory that is deleted after the check; a repository file missing or 0 B on the stage, a staged file with no repository counterpart, or a sha256 that differs from `snowflake/phase4_others/skill/<name>/` holds the stage (`halted`, kept on resume). LIST sizes and md5 are recorded, never compared (encrypted sizes, rounded up to 16 bytes) | `eval/campaign.py` `skill_precheck`; state file `skill_checks` |
| Runaway (owner, 2026-10-06, session 9a) | a turn whose estimated cost (AI Credits at the rates of `eval/guards.py`, `turn_usd`) exceeds 2 USD is stopped and stops its block; the same rule for the six configurations. It replaces the per-call token guard as a stop condition. Reason: for D and D′ one REST call sums every internal planning step (D's S_STOCKOUT_COUNTRY in stage 1: one call, 13 tool uses, 746,962 input tokens, about 0.48 USD), so the token guard measured the agent's behaviour (its number of steps), and a behaviour never stops a block (rule of session 8c-0); it also cut the measurement of the costliest configuration. The stage's cost protection stays the pause at 36 USD | `run_call.py --turn-usd-cap 2.0`, checked after each REST call, exit code 4; `eval/campaign.py` also checks the turn's recorded tokens; `turn_usd` in each attempt |
| Tokens (recorded, no stop since session 9a) | the ceiling of each turn is still computed and written in its attempt (`token_ceiling`, `above_token_ceiling`): 1.5 times the configuration's largest smoke call; for a turn that continues a thread (BULK_SCOPE_DRILL), plus its parent turn's largest call (the smokes had no follow-up turn; commit de44d3a). The tokens of every call and turn stay in the summaries; the maximum per configuration is reported as a measure | `eval/guards.py` `token_ceilings`, `thread_token_ceiling` |
| Warm-up on resume (owner, session 9a) | a block resumed with its warm-up done and turns left runs a new warm-up attempt (`-a<m>`, not graded) when its last call ended more than 5 minutes ago | `eval/campaign.py` `REWARM_AFTER_S` |
| Errors | 3 consecutive (non-200, timeout, no summary) stop the block; 2 stopped blocks stop the stage | `eval/guards.py` |
| Version | the agent's default version (SHOW VERSIONS, before each block) differs from the frozen state, or is not read: the block does not start and the stage is held until the owner decides | `eval/campaign.py`, `eval/guards.py` (`halted`) |
| Cost | an estimate in USD: AI Credits from each turn's REST usage tokens, plus the warehouse over the sum of the UTC windows of the blocks already played and the current block since its start (1 credit an hour, 3.90 USD a credit; owner, session 9a: a pause costs nothing, so a resume hours later adds no warehouse time; before, the hours elapsed since the stage started counted, pauses included; state file `guard.segments`). At 90 percent of the ceiling the stage **pauses** and resumes only on the owner's decision (`run --resume-paused --ceiling-usd <new>`). Stage 1: 40 USD, pause at 36 USD (owner, decision 2 after step 5); stage 2: `--ceiling-usd`, set at the cost read | `eval/guards.py`, `eval/campaign.py` |

Token ceilings (owner, decision 2 of session 8c): 1.5 times the largest orchestration input of one REST call over the
smokes of sessions 8, 8b and 8c-0, recomputed from the run summaries (`eval/fixtures/smoke_tokens.jsonl`,
`tests/test_guards.py`) [measured]. The figures quoted before the session (B2 256,113 on T1 of 8c-0, C 91,660 on
DIM_MIX) are not the largest: B2's T9 of session 8 and C's CS_LAST_MONTH_GAP of 8b (through the semantic view) are.

| Configuration | Largest call (input tokens) | Call | Request id | Ceiling |
|---|---|---|---|---|
| A | 188,241 | session 8, CS_LAST_MONTH_GAP (call 30 of s8) | `00000012-0000-4000-8000-000000000012` | 282,361 |
| B1 | 176,488 | session 8, CS_LAST_MONTH_GAP (call 10) | `00000013-0000-4000-8000-000000000013` | 264,732 |
| B2 | 292,797 | session 8, T9 (call 5) | `00000014-0000-4000-8000-000000000014` | 439,195 |
| C | 157,011 | session 8b, CS_LAST_MONTH_GAP (call 8 of s8b) | `00000015-0000-4000-8000-000000000015` | 235,516 |
| D | 205,886 | session 8, T1 (call 22) | `00000016-0000-4000-8000-000000000016` | 308,829 |
| D′ | 235,917 | session 8, T1, first call (call 11) | `00000017-0000-4000-8000-000000000017` | 353,875 |

## Manual replays (owner only)

Budget `manual` of `run_call.py`, 20 calls, labels `<CONFIG>_<QUESTION>_manual_r<n>`, for the owner to replay under
LINKML_SVC an exchange to cite. Never used by the campaign runner. Example (the owner runs it; no call is made by the
session):

    python snowflake/probe_b/mount/run_call.py --agent LINKML_C \
        --question "Which country has the lowest stock coverage of breakfast cereals as of June 2026?" \
        --label C_H_LOWEST_COUNTRY_manual_r1 --budget manual --log-dir ~/work/assets/linkml-metrics-runs/manual

Add `--policy dp --client-sql` for D and D′.

## Cost model (step 5, not run)

Reproduced by `python eval/cost_model.py` (no call). Prices (decision 3): AI Credits 2.00 USD, Platform Credits 3.90
USD. Ceiling for everything left: about 90 USD. Owner (after step 5): stage 1 40 USD; stage 2 is what remains under
about 90 USD after the spending since the freeze, stage 1 as billed, the drill (8 USD) and a reserve (5 USD).

### Inputs

| Input | Value | Tag |
|---|---|---|
| Credits per token | cache write 1.625, cache read 0.13, output 6.5 AI Credits per million; uncached input 1.3 | measured (billed rows, sessions 3 and 5); uncached inferred |
| Check against billing | priced smoke turns give A 0.059 to 0.080, B1 0.053 to 0.073, D 0.072 to 0.111 per tool turn: the session 8 billed read (CORTEX_AGENT_USAGE_HISTORY) gave the same ranges | measured |
| Tokens per turn | `eval/fixtures/smoke_tokens.jsonl` (sessions 8, 8b, 8c-0): C about 60,000 input per coverage turn, about 92,000 with two tool calls, about 157,000 through its view; A, B1, B2, D, D′ 113,000 to 293,000 per call | measured |
| D′ per question | 0.158 with its approval and client-side resumes (session 8 billed read); low 0.10 | measured; low inferred |
| Warm-up call | a block's first call writes the whole prompt cache: about 0.054 (D′ 0.17) | D′ measured (0.16 to 0.18); others inferred (about 33,000 tokens written) |
| Attached SQL | 0.004 to 0.016 Platform Credits per tool turn | measured (session 8 read) |
| Warehouse | X-Small, 1 credit an hour while up, kept running by the warm guard; attached SQL is part of it, the rest is idle or overhead | documented (rate), inferred (hours) |
| D′ SQL | the script's two statements and the client-side statements run on the same warehouse under LINKML_SVC; read from QUERY_HISTORY after the stage, inside the warehouse hours | inferred |

### Per question, AI Credits (low / expected / high) [inferred from the measured inputs]

| A | B1 | B2 | C coverage | C through its view | D | D′ |
|---|---|---|---|---|---|---|
| 0.059 / 0.062 / 0.080 | 0.053 / 0.062 / 0.073 | 0.074 / 0.110 / 0.130 | 0.018 / 0.022 / 0.045 | 0.072 / 0.072 / 0.074 | 0.072 / 0.079 / 0.111 | 0.10 / 0.158 / 0.240 |

Split of a median turn into cache write, cache read and output (AI Credits) [measured on the smokes]: A 0.029 /
0.022 / 0.010; B1 0.034 / 0.020 / 0.008; B2 0.082 / 0.020 / 0.014; C coverage 0.010 / 0.007 / 0.004; C view 0.052 /
0.016 / 0.004; D 0.060 / 0.016 / 0.009; D′ 0.045 / 0.018 / 0.003 per call. Cache writes are most of every turn: each
planning step writes what the previous tool returned.

### Stage 1 (24 questions and one warm-up per configuration, 170 REST calls expected)

| Configuration | AI Credits low / expected / high |
|---|---|
| A | 1.42 / 1.48 / 1.91 |
| B1 | 1.29 / 1.49 / 1.74 |
| B2 | 1.76 / 2.60 / 3.05 |
| C | 0.74 / 0.81 / 1.24 |
| D | 1.72 / 1.88 / 2.62 |
| D′ | 2.48 / 3.81 / 5.71 |
| **AI Credits** | **9.41 / 12.08 / 16.28 (18.8 / 24.2 / 32.6 USD)** |
| Warehouse (about 1.25 h of calls, about 1.5 h with warm-ups and gaps; attached SQL 0.55 / 1.38 / 2.21 credits of it) | about 5.8 USD |
| **Stage 1, the guard's estimate** | **about 25 / 30 / 38 USD** against the 36 USD pause and the 40 USD ceiling [inferred] |

At the expected cost stage 1 runs to its end in the drawn order (D′, D, B1, B2, A, C); at the high cost the guard
pauses it during the last block (C), and the owner decides.

### Stage 2 (repetitions in all: B2, C, D′ 5; B1, D 3; A 3 on its passed share)

Owner, session 9a: A is not repeated in stage 2. The table below was computed before that decision and still counts
A's r2 and r3 on half of d. Since session 9a closing, `eval/campaign.py plan --stage 2` has no A block and
`eval/cost_model.py` counts no A turn in stage 2 (A's trials are its stage 1 turns); the sizing from the billed costs
is in `snowflake/phase5_campaign/stage1_results.md`.

d, the number of discriminating questions, is known after the gate. The 4 held-out questions are always in (B2, C, D′
r1 to r5; B1, D r1 to r3; A none); A runs r2 and r3 on half of d (its passed share, assumed). USD with the warehouse
over the stage's hours [inferred]:

| d | REST turns | AI Credits low / expected / high | USD low / expected / high | Hours |
|---|---|---|---|---|
| 0 (held-out only) | 84 | | 15.6 / 19.9 / 25.8 | 0.7 |
| 4 | 152 | 10.5 / 14.3 / 19.6 | 26.9 / 34.6 / 45.2 | 1.3 |
| 8 | 220 | 14.9 / 20.5 / 28.1 | 38.1 / 49.2 / 64.5 | 1.9 |
| 14 | 322 | 21.6 / 29.7 / 40.9 | 54.9 / 71.1 / 93.5 | 2.7 |
| 20 | 424 | 28.3 / 39.0 / 53.7 | 71.7 / 93.0 / 122.4 | 3.6 |

Largest d that fits a stage 2 budget (`eval/cost_model.py`, at low / expected / high cost):

| Stage 2 budget | Largest d |
|---|---|
| 35 USD | 6 / 4 / 1 |
| 40 USD | 8 / 5 / 2 |
| 45 USD | 10 / 6 / 3 |

### Power of the pooled pass rate

Method: the exact (Clopper-Pearson) one-sided 95 percent upper bound of the failure rate when no failure is seen in n
trials, 1 − 0.05^(1/n). Trials per configuration, stage 1 and stage 2 together; discriminating questions, held-out
questions apart (their n does not depend on d) [documented formula, inferred trial counts]:

| d | A | B1, D | B2, C, D′ |
|---|---|---|---|
| 4 | 6 trials, 39.3 % | 12, 22.1 % | 20, 13.9 % |
| 8 | 12, 22.1 % | 24, 11.7 % | 40, 7.2 % |
| 12 | 18, 15.3 % | 36, 8.0 % | 60, 4.9 % |
| Held-out (4 questions) | none | 12, 22.1 % | 20, 13.9 % |

Reading: with 5 repetitions on 4 discriminating questions (20 trials), a configuration that never fails can be said to
fail less than 13.9 percent of the time, at 95 percent; 40 trials give 7.2 percent; a single failure widens it.
Differences between configurations smaller than that are not claims the campaign can make [inferred]. Note: the
article's interval on an observed pass rate is the Wilson score interval (two-sided 95 percent); at zero failures its
upper bound is z² / (n + z²), 16.1 percent for 20 trials, a different method from the bound above.

### Overfitting drill and totals

| Item | AI Credits low / expected / high | USD (with warehouse) |
|---|---|---|
| Drill: B2's spec plus one instruction, 28 questions once plus about 15 re-runs, one warm-up | 3.2 / 4.8 / 5.6 | about 8 / 11 / 13 |
| Stage 1 | 9.4 / 12.1 / 16.3 | about 25 / 30 / 38 |
| Spent since the freeze (the pytest incident, 0.16 credit) | | about 0.6 |
| Reserve | | 5 |
| **Stage 2, what remains under about 90 USD** | | **about 51 / 46 / 38** (stage 1 low / expected / high): d up to about 12 / 7 / 2 at the matching cost |

### Cost read between the stages

1. Wait 3 hours after the last stage 1 call: CORTEX_AGENT_USAGE_HISTORY lags up to an hour or more [measured in
   session 3: up to an hour; 3 hours is the owner's margin].
2. Owner's queries (ACCOUNTADMIN; the project role reads no ACCOUNT_USAGE view [measured, finding 94 of part 5]), over
   the UTC windows of `state_campaign-s1.json`:
   - `SELECT AGENT_NAME, COUNT(*), SUM(TOKENS), SUM(TOKEN_CREDITS) FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY
     WHERE USER_NAME = 'LINKML_SVC' AND START_TIME BETWEEN <first> AND <last> GROUP BY 1` (and `CREDITS_GRANULAR` for
     the split into cache write, cache read and output);
   - `SELECT SUM(CREDITS_USED_COMPUTE) FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY WHERE WAREHOUSE_NAME =
     'LINKML_METRICS_WH' AND START_TIME BETWEEN <first> AND <last>`;
   - `SELECT SUM(CREDITS_ATTRIBUTED_COMPUTE) FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY WHERE USER_NAME =
     'LINKML_SVC' AND START_TIME BETWEEN <first> AND <last>` (the SQL attached to turns, D′'s script statements
     included).
3. Stage 2 budget: about 90 USD less the spending since the freeze, stage 1 as billed (AI Credits and warehouse), the
   drill (8 USD) and the reserve (5 USD). Go or no-go: the measured AI Credits per turn of each configuration in stage 1,
   times the stage 2 turns the gate plans (`eval/campaign.py plan --stage 2`), plus the warehouse hours at the measured
   rate. Go if the projection is within the budget; otherwise apply cut 3 one question of `drop_order` at a time (cuts 1
   and 2 change nothing at the decided repetitions), never a held-out question, until it is; no-go, and the owner
   decides, if the 4 held-out questions alone do not fit. Stage 2 then runs with `--ceiling-usd <budget>`. The runner's own estimate (`state_campaign-s1.json`, `guard.spent_credits`) is compared with the
   billed figure; a gap above 15 percent recalibrates `eval/guards.py` RATES before stage 2 (a harness change).

### Figure-only score (owner, 2026-10-07)

Reported next to the primary verdict for both stages (`eval/campaign.py grade`, `verdict_figure_only` in the grades):
the same grader and criteria of rubric 3.2, except the unit half of `basis_wording` (a sentence gives the coverage in a
unit). "Basis not named" still fails it, and an owner's decision applies to it as to the primary. The primary verdict
stays the score of record and the gate reads it alone; the text of rubric 3.2 is unchanged.

### Expected duration (streams 1, no trace polling) [inferred]

Per question, client total plus about 6 s of connection and warm guard: A 29 s, B1 24 s, B2 36 s, C 23 s, D 27 s, D′
38 s. Stage 1: about 1.25 hours of calls, about 1.5 hours with the warm-ups and gaps. Stage 2: 0.9 to 3.6 hours by d
(table above); the cost read adds 3 hours between the stages. The drill: about half an hour.

### The article's cost table (shell)

One row per configuration. S1: stage 1 fills the cell; S2: it needs stage 2's repetitions; S1+S2: stage 1 gives a
first value, stage 2 the interval.

| Column | Filled by |
|---|---|
| AI Credits per question, median and range | S1 (one point per question), S2 (range across repetitions) |
| Input tokens per turn, median and range | S1 |
| Latency per turn (client total, server split from the traces) | S1, S2 for the spread |
| Cold against warm cache (the warm-up call against the rest of the block) | S1 (one cold call per block), S2 (one per block) |
| Cost per correct answer (credits over correct turns) | S1+S2 |
| Pooled pass rate on the discriminating questions, with its 95 percent interval (Wilson; at zero failures, the exact bound 1 − 0.05^(1/n)) | S2 (n = repetitions x questions; S1 alone gives n = d per configuration) |
| Refusals: coded (C), in prose, none | S1+S2 |
| Lineage: figure traceable to query ids, inputs only, nothing | S1 (by construction, `eval/governance.md` d) |
| ROWS_COMMENTED rate | S1+S2 |
| FRESHNESS_STATED rate (present; June 2026) | S1+S2 |
| Held-out questions: pass rate per configuration | S2 only |
| Overfitting drill: fixed, unchanged, newly broken; tokens per turn before and after | the drill (session 9) |
