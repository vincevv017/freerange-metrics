# Documentation index

One line per notes or results file: what it covers, its sessions, and its finding numbers. Numbered findings are
per file (each phase notes file starts again at 1). The notes are kept as written at the time, scrubbed for
publication, not rewritten. Tags in every file: [measured], [documented], [inferred].

## Definition, contract and charter

| File | Covers | Sessions | Findings |
|---|---|---|---|
| [DEFINITION.md](DEFINITION.md) | stock coverage and closing stock defined: the algorithm, edge cases and traps T1 to T9, default scope, analysis month, basis | 1 to 8c-0 | none (definition) |
| [CONTRACT.md](CONTRACT.md) | how to read `contract/stock_coverage.yaml` and what the compiler generates from it | 4 to 8c-0 | none (guide) |
| [TOUR.md](TOUR.md) | a guided tour of the repository: six questions end to end on C-raw, each generator, what is fixed, a reading order | 14 | none (guide) |
| [dry_run/results.md](dry_run/results.md) | the dry run of a second metric (cash runway): which generators run, the five concessions, the instance leaks | 11 | none (record) |
| [configurations.md](configurations.md) | the fairness charter of the seven configurations (version 12; versions 1 to 11 frozen before the campaign, version 12 adds C-raw) and the hypotheses to falsify | 8 to 13 | none (charter) |
| [check_coverage_formula.py](check_coverage_formula.py) | the formula checked against the legacy cascade | 1, 2 | none (script) |

## Phase notes

| File | Covers | Sessions | Findings |
|---|---|---|---|
| [phase0_findings.md](phase0_findings.md) | account state, the synthetic dataset, probes A (native view), B (`code_toolset_all`), C0 (hand-written tool) and D (`code_execution`), the service user, go / no-go | 1 to 4 | unnumbered, by section |
| [phase1_notes.md](phase1_notes.md) | the decisions writing the contract forced | 4 | 1 to 33 |
| [phase2_notes.md](phase2_notes.md) | the schema module, traps and data metric functions generated from the contract | 5 | 1 to 33 |
| [phase3_notes.md](phase3_notes.md) | part 1: native closing stock, contract 0.2.0, the procedure generator and its checks; part 2: generated closing stock and trap T9 | 6, 7 | 1 to 36 (part 1), 37 to 51 (part 2) |
| [phase4_notes.md](phase4_notes.md) | part 1: agent C on the generated procedure; part 2: fixes to C and the latency witness; part 3: configurations A, B1, B2, D and D′; part 4: C rebuilt on SQL Scripting; part 5: coverage on a governed basis | 7, 8a, 8, 8b, 8c-0 | 1 to 25, 26 to 46, 47 to 62, 63 to 79, 80 to 112 |
| [phase5_notes.md](phase5_notes.md) | part 0: campaign ready, held-out questions, governance; part 1: D′ skill load; part 2: stage 1; part 3: reduced stage 2, rubric 3.3 and the billed cost of the campaign | 8c, 8c-1, 9a, 9b, 9c | 1 to 46, 47 to 71, 72 to 105, 106 to 137 |

## Results (`snowflake/`)

| File | Covers | Sessions | Findings |
|---|---|---|---|
| [probe_a/results.md](../snowflake/probe_a/results.md) | probe A: native semantic view builds per trap | 1 | none (raw results) |
| [probe_a/results_spine.md](../snowflake/probe_a/results_spine.md) | probe A, second build: the forward spine view | 1 | none |
| [probe_a/results_addendum.md](../snowflake/probe_a/results_addendum.md) | probe A addendum: a required analysis-month variable (T6) and the status bridge (T3) | 2 | none |
| [probe_b/results.md](../snowflake/probe_b/results.md) | probe B: `code_toolset_all` and a stage skill (D′) | 2, 3 | numbered rows 1 to 9 |
| [probe_b/mount/results.md](../snowflake/probe_b/mount/results.md) | skill mount diagnosis | 3 | numbered rows 1 to 6 |
| [probe_c0/results.md](../snowflake/probe_c0/results.md) | probe C0: a hand-written custom tool (C) | 3 | numbered rows 1 to 6 |
| [probe_d/results.md](../snowflake/probe_d/results.md) | probe D: a skill script under `code_execution` | 4 | numbered row 1 |
| [phase2_dmf/results.md](../snowflake/phase2_dmf/results.md) | the generated data metric functions, run once | 5 | none |
| [phase3_procedure/results.md](../snowflake/phase3_procedure/results.md) | the generated procedure called directly: numbers, parity with C0, latency | 6, 7 | numbered rows 1 to 25 |
| [probe_closing/results.md](../snowflake/probe_closing/results.md) | closing stock, native baseline (session 6) and generated (session 7), and trap T9 on the view | 6, 7 | none |
| [phase4_agent_c/results.md](../snowflake/phase4_agent_c/results.md) | agent C asked every question, latency per turn, the 8a fixes | 7, 8a | numbered rows 0 to 15 |
| [phase4_others/results.md](../snowflake/phase4_others/results.md) | configurations A, B1, B2, D and D′ built and smoke-tested | 8 | numbered rows 1 to 20 |
| [phase4_c_sql/results.md](../snowflake/phase4_c_sql/results.md) | C rebuilt on the SQL Scripting procedure: parity, deployment, latency | 8b | numbered rows 1 to 10 |
| [phase4_c_sql/parity_checklist.md](../snowflake/phase4_c_sql/parity_checklist.md) | the Python to SQL Scripting parity checklist | 8b | numbered rows 10 to 51 |
| [phase4_basis/results.md](../snowflake/phase4_basis/results.md) | coverage as a time measure on a governed basis (contract 0.5.0), reloads and redeploys | 8c-0 | none |
| [phase5_campaign/stage1_results.md](../snowflake/phase5_campaign/stage1_results.md) | campaign stage 1: six configurations, 24 questions, verdicts, gate, billed cost, rubric 3.3 regrade | 9a, 9c | none (record) |
| [phase5_campaign/stage2_results.md](../snowflake/phase5_campaign/stage2_results.md) | campaign stage 2, reduced: C against B2, C over both stages, billed cost of the campaign, rubric 3.3 regrade | 9b, 9c | none (record) |
| [session13_craw/results.md](../snowflake/session13_craw/results.md) | configuration C-raw: the raw tables only, `CLOSING_STOCK` against the gap-filled view on every member, the campaign arm on C's questions, billed cost | 13 | none (record) |

## Campaign harness (`eval/`)

| File | Covers | Sessions | Findings |
|---|---|---|---|
| [campaign.md](../eval/campaign.md) | the campaign plan: frozen state, stages, guards, cost model | 8c to 9b | none (plan) |
| [gate.md](../eval/gate.md) | the rule that selects stage 2 questions | 8c, 9a | none (rule) |
| [governance.md](../eval/governance.md) | governance measures, no agent call | 8c | none (measures) |
