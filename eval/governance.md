# Governance measures (session 8c, step 4): no agent call

What it costs to keep one complex indicator right in each configuration, beside whether the answer is right. Measured
on the repository and on recorded logs; no agent call, no deployment. Tags: **[measured]**, **[documented]**,
**[inferred]**. Configurations as in `docs/configurations.md` version 10.

## a. Where the rule lives

The coverage definition: algorithm (forward cascade over t+1..t+H, interpolation, beyond-horizon extrapolation),
applicability (stock-only attributes), default scope (BULK excluded), basis rule, grain rule, refusals (month,
basis, fan-out). Every place it is written that the configuration's model or engine reads, by grep of the rule's
fragments over the repository [measured]:

| Configuration | Generated from the contract | Written or kept by hand | Count of places |
|---|---|---|---|
| A | none | `docs/DEFINITION.md` sections 1, 7, 8, extracted into `a/agent_a.yaml` by `a/build_spec.py` (a script, but over hand-written prose); the Autopilot view `AP_LINKLM` carries none of it (no metric, no instruction) | 1 prose source, 1 spec |
| B1 | none | `b1/agent_b1.yaml` instructions (DEFINITION.md sections 1 to 3, 7, 8 paraphrased by hand, the grain rule and freshness line by hand); `b1/LINKML_B1_SV.yaml` and its enriched copy (window metrics `c01..c24`, descriptions, the basis rule in metric descriptions) | 3 hand files |
| B2 | `generated/agent_b2.yaml`, `generated/b2_native_sv.yaml`, `generated/b2_native_views.sql` (gen_native_sv.py); the enriched copy by `b2/apply_grounding.py` | none | 0 hand files |
| C | `generated/agent_c.yaml` (instructions, tool description, input schema), `generated/stock_coverage_procedure_sql.sql` (the engine, the refusals), and B2's view for its general tool | none | 0 hand files |
| D | B2's view (its extraction tool) | DEFINITION.md sections 1 to 3, 7, 8 extracted into `d/agent_d.yaml` by `d/build_specs.py`; the skill `linkml-coverage` (`SKILL.md`, `coverage.py`, written from DEFINITION.md section 2) | 1 prose source, 1 spec, 2 skill files |
| D′ | same as D | same as D, `d/agent_dp.yaml` | 1 prose source, 1 spec, 2 skill files |

Two findings. The grain rule (charter version 9) was in C's, A's, B1's, D's and D′'s instructions, not in B2's: the
charter applied it to C, DEFINITION.md (A, D, D′) and B1, and B2's instructions come from a generator the charter row
did not name (`compiler/gen_native_sv.py`); the identity test of session 8c-0 did not list B2 either [measured]. A rule
of the charter missed a generated target: generation keeps a rule consistent only inside the targets it is wired to.
Fixed by charter version 11 (conformity, no new rule) and checked from then on by `tests/test_charter_conformity.py`,
which reads the imposed sentences from the charter and fails if any of the six configurations lacks one.
The refusal BASIS_NOT_COMPARABLE is written only in the contract, C's instructions and the procedure: every other
configuration can only decline in prose [measured].

## b. Instruction weight

Characters of business rules the model reads per turn: orchestration and response instructions, tool descriptions
and input schemas, skill text; the semantic model the agent loads into planning is listed apart (its descriptions
and instructions, then the whole YAML) [measured on the files]. Input tokens per REST call from the smokes of
sessions 8, 8b and 8c-0 (`eval/fixtures/smoke_tokens.jsonl`) [measured].

| Configuration | Orchestration | Response | Tool descriptions + schemas | Skill (`SKILL.md`) | Business rules read, total | Semantic model: descriptions / YAML | Input tokens per call with a tool: median (range) | Without a tool |
|---|---|---|---|---|---|---|---|---|
| A | 6,022 | 390 | 403 | | 6,815 | 1,642 / 12,917 | 161,170 (160,209 to 188,241) | 33,987 |
| B1 | 3,799 | 390 | 493 | | 4,682 | 3,609 / 17,080 | 113,697 (112,273 to 176,488) | 33,503 |
| B2 | 3,023 (2,570 before charter 11) | 390 | 480 | | 3,893 | 6,307 / 44,740 | 228,908 (150,478 to 292,797) | 33,301 |
| C | 2,543 | 390 | 434 + 3,106 + 4,342 | | 10,815 | 6,307 / 44,740 (only when its view tool is used) | 60,205 (55,751 to 157,011) | 36,705 |
| D | 8,690 | 390 | 551 | 3,369 | 13,000 | 6,307 / 44,740 | 154,074 (149,071 to 205,886) | 33,013 |
| D′ | 8,690 | 390 | 436 | 3,369 | 12,885, plus the bundled catalogue of `code_toolset_all` (about 140,000 characters, phase 0) | 6,307 / 44,740 | 164,621 (138,278 to 235,917) | 96,722 to 99,574 |

Reading [inferred]: business rules are 3,900 to 13,000 characters, a few thousand tokens, against 60,000 to 290,000
input tokens per call. The cost of a turn follows the semantic model in context and the number of planning steps,
not the rule text: C reads the most rule text and has the smallest turns, because its coverage turns never load the
semantic model.

## c. Rule changes, as real cases

### Measured in session 8c-0 (charter versions 8, 9, 10) [measured, `docs/configurations.md`, `docs/phase4_notes.md` part 5]

| Change | Generated | Edited by hand | Redeployed |
|---|---|---|---|
| Basis rule (contract 0.5.0, charter 8) | contract and metamodel; B2 instructions and view descriptions, C instructions, tool description and input schema (`basis` replaces `unit_variant`), both procedures, the closing view, the reference questions | DEFINITION.md section 8 (A, D, D′ by extraction); B1: 7 lines changed or added and 5 removed in each of its two YAML files, plus 3 sentences of its agent text; the skill text (D, D′), which stated a unit | B2 view, closing view, STOCK_COVERAGE (old signature dropped first, finding 90), every agent by a five-beat cycle (C, A VERSION$4; B1, B2, D, D′ VERSION$5) |
| Grain rule (contract 0.5.1, charter 9) | contract (`member_selection.grain_rule`), C's instructions | DEFINITION.md section 1 (A, D, D′ by extraction); B1: 4 lines added | B2 view and closing view (contract version text), every agent (C, A VERSION$5; B1, B2, D, D′ VERSION$6) |
| Freshness line (charter 10) | B2 and C (`gen_native_sv.py` RESPONSE) | A, D, D′ take B2's response through their build scripts; B1: 2 lines changed, 1 added | every agent (C, A VERSION$6; B1, B2, D, D′ VERSION$7) |

### Drill: forecast horizon 24 to 18 months (throwaway branch `drill/horizon-18`, never merged, nothing deployed)

One line changed in the contract (`horizon_periods: 18`); every compiler generator run and the dataset rebuilt; the offline tests
run (`tests/test_procedure.py` excluded: it calls the account); the branch deleted; main unchanged at a3cb672, tree
clean [measured].

Regenerated, per configuration (`git diff --numstat`):

| File | Lines added / removed | Configurations |
|---|---|---|
| `generated/schema.py` (HORIZON_MONTHS) | 1 / 1 | the oracle, the grader, every generator |
| `generated/stock_coverage_procedure_sql.sql`, `generated/stock_coverage_procedure.sql` | 7 / 7, 5 / 5 | C |
| `generated/agent_c.yaml` (tool description "next 18 months") | 1 / 1 | C |
| `generated/agent_b2.yaml` (instructions "next 18 months") | 1 / 1 | B2 |
| `generated/b2_native_sv.yaml`, `b2/LINKML_B2_SV_enriched.yaml` (grounding carried by script) | 18 / 133 each | B2, C, D, D′ (their view tool) |
| `generated/b2_native_views.sql` (forward spine f19..f24 dropped) | 4 / 16 | B2, C, D, D′ |
| `generated/dmf.sql` | 3 / 3 | shared (data metric functions) |
| unchanged: `generated/reference_questions.yaml`, `generated/closing_stock_sv.sql`, `a/agent_a.yaml`, `d/agent_d.yaml`, `d/agent_dp.yaml` | | |

To edit by hand (lines quoted from the files):

| Configuration | Where | Lines |
|---|---|---|
| A, D, D′ | `docs/DEFINITION.md` (then `a/build_spec.py`, `d/build_specs.py`) | line 11 "- **Horizon** *H* = **24 months**."; lines 102, 105, 124 of the section 5 SQL (`horizon H = 24`, `GENERATOR(ROWCOUNT => 24)`, `DATEADD(month, 24, :as_of_month)`); lines 166 and 167 ("24 windowed cumulative sums", "24 candidate coverages", section 6, not extracted) |
| B1 | `b1/agent_b1.yaml` | lines 13, 17, 18, 20, 21, 26 ("the 24 months that follow", "each of the 24 following months", "up to 24", "outlasts the 24 months", "those 24", "24 months after it") and line 59 ("c01 to c24") |
| B1 | `b1/LINKML_B1_SV.yaml` and `LINKML_B1_SV_enriched.yaml` | the window metrics `c19` to `c24` (6 metrics each, lines 103 to 108; `c24` described as "the coverage horizon") and the non-zero month counter over them |
| D, D′ | skill `SKILL.md` | lines 9, 20, 51 ("the 24 following months", "to 24 months after it", "`forecast_by_month` (24 ...") |
| D, D′ | skill `coverage.py` | line 22 `H = 24`; docstrings lines 13, 39, 56 |
| C, B2, D, D′ (generated, yet wrong) | `contract/stock_coverage.yaml`, hand text inside the contract | line 421 "Stock outlasts the 24-month horizon." (BEYOND_HORIZON), copied by the generators into C's tool description (`agent_c.yaml` line 72) and B2's metric descriptions (`b2_native_sv.yaml` lines 565, 604); line 464 "whose 24-month forecast window" |
| Harness | `tests/test_reference_oracle.py` (this session's held-out test divides by 24), the grader's horizon read (`grade.py` HORIZON) | see below |

Objects to redeploy: C: STOCK_COVERAGE (and STOCK_COVERAGE_PY while kept) and LINKML_C; B2: the B2 views, LINKML_B2_SV,
LINKML_B2; B1: LINKML_B1_SV, LINKML_B1; A: LINKML_A (view untouched); D and D′: the skill on SKILLS_D and SKILLS_DP,
LINKML_D, LINKML_DP; shared: the data metric functions. Six agents published, two views, one procedure, two skill
stages [measured on the diff; inferred for the deploy list].

Expected values that change, recomputed by the oracle (pandas reference, all rows at June 2026, default scope)
[measured]: by item 0 of 54 rows (both bases); by item and country 9 of 220 on QTY_EQ (8 become BEYOND_HORIZON, for
example SKU-0013 in CH 20.11 to 18.90) and 4 of 220 on VALUE (SKU-0017 in FR 20.98 to 18.23); by family and country 2
of 105 (HOT_TEA in CH, PANTRY_PASTA in FR); by country 0. **No graded expected value of the 28 reference questions
changes**: the frozen values of `data/traps.yaml` all pass with H = 18 (BEYOND_H stays 50.0, S_DORMANT_VALUE keeps 28
pairs and 70.99 million EUR, the drill rows are below 18). Offline tests: 365 passed, 5 failed: the grader moves one
recorded verdict (B1's T6 answer says "24-month" and that count is no longer the horizon, so it reads as a coverage:
correct to wrong), which also moves two gate tests and the rubric 3.2 test; and this session's held-out test hard-codes
24 in its mean-ratio check.

What stays silently wrong if one hand edit is forgotten [inferred from the diff and the oracle]:
- DEFINITION.md not edited: A, D and D′ keep cascading over 24 months; on the 9 item-country rows above, A's and D's
  figures stay at the 24-month values (SKU-0013 in CH 20.11 instead of 18.90, no BEYOND_HORIZON flag); no test fails.
- The skill's `coverage.py` not edited: D and D′ compute with H = 24 whatever their instructions say; the script is
  "the tool computes", so its figures are trusted.
- B1's metrics not dropped: `c19..c24` stay in the view, and its instructions keep "24": B1 keeps the old window.
- The contract's BEYOND_HORIZON text not edited: C's tool description and B2's view keep telling the model "24-month
  horizon" while the procedure uses 18; the generated files pass their drift test, since the wrong text is in their
  source.
- The test suite: no reference question detects the change; only a grader test on a recorded answer did, by accident.

Open (owner, decision 5 of session 8c): the contract's hand text "24-month horizon" becomes a template on {H} after the
campaign, and this drill is run again.

## d. Traceability: from the figure to the queries that produced it

One recorded smoke answer per configuration (T1; traces of the run folders) [measured]:

| Configuration | Turn | What a reader has | Can the figure be traced to the queries? |
|---|---|---|---|
| A | session 8, `a_t1` | 5 SQL tool calls with their statements in the tool input; 4 query ids in the trace (`sql_execution.query_id`) | yes to the inputs; the coverage arithmetic is the model's, not in any query |
| B1 | session 8, `b1_t1` | 2 SQL statements, 2 query ids | the same |
| B2 | 8c-0 step 8, `b2_t1_s8c0_step8_r1` | 4 SQL statements, 4 query ids; the view's coverage metric did not run; the model says it computed 2.8 itself | yes to the inputs; the figure itself is the model's |
| C | 8c-0 step 8, `c_t1_s8c0_step8_r1` | the tool result carries the CALL's query id and the procedure's lineage (the query ids of its context, quality and coverage statements, contract 0.4.2), the parameters in the tool input | yes, figure included: the figure is a column of a query |
| D | session 8, `d_t1` | 2 extraction statements and their query ids; the numbers passed to the script as literals in the bash command (`--stock`, `--forecast`) | to the extraction queries, not to the figure: the numbers went through the model between the queries and the script |
| D′ | session 8, `dp_t1` | the extraction SQL in the bash command; the script's output names the query id of each statement it ran (`queries.stock.query_id`, `queries.forecast.query_id`); no SQL span in the trace (the script's own connection) | yes, figure included, from the script output; not from the trace |

The trace attribute `sql_execution.final_sql` was absent from every one of these traces; the SQL is read from the
tool inputs [measured].

## e. Refusals by construction

| Configuration | Refusal codes it can return | Where they live |
|---|---|---|
| C | the 21 codes of the contract: AS_OF_MISSING, AS_OF_INVALID, AS_OF_NOT_MONTH_START, AS_OF_TOO_MANY, AS_OF_NO_SNAPSHOT, HORIZON_NOT_LOADED, BASIS_UNKNOWN, GRAIN_MALFORMED, GRAIN_EMPTY, GRAIN_DUPLICATE, FILTERS_MALFORMED, FILTER_VALUES_INVALID, ATTRIBUTE_UNKNOWN, ATTRIBUTE_UNCLASSIFIED, ATTRIBUTE_NOT_APPLICABLE, TOTALS_MALFORMED, TOTALS_NOT_SUBSET, SELECTION_INVALID, MASTER_DATA_FANOUT, DATA_QUALITY_FAILED, BASIS_NOT_COMPARABLE | the procedure (generated); its instructions add "ask which month" |
| B2 | none coded; asking for the month and declining packs in prose | generated instructions |
| A, B1 | none coded; asking for the month (DEFINITION.md section 8) and the raw-unit rule (section 1) in prose | instructions |
| D, D′ | none coded for the business rules; the script stops on a negative stock, a statement that is not one SELECT, a month that is not a first day; asking for the month in prose | `coverage.py` (input checks only), instructions and `SKILL.md` |

Only C can return MASTER_DATA_FANOUT, BASIS_NOT_COMPARABLE or DATA_QUALITY_FAILED: every other configuration either
answers or declines in its own words. Whether the model reaches the coded refusal is measured in the campaign (C
refused packs itself in T5 in sessions 7, 8b and 8c-0, never reaching the procedure's refusal).

## f. The overfitting drill (session 9, after stage 2; design only, not run)

As decided (decision 6):
- A throwaway agent `LINKML_B2_DRILL`: B2's spec plus one targeted instruction, written from the trace of one question
  B2 fails in stage 1 (else B1, then A). The instruction's text is recorded in the register, and in
  `docs/phase5_notes.md` part 1, before the agent is created.
- Run: the stage 1 question set and the four held-out questions once; every question whose verdict changed against
  B2's stage 1 answer, 3 more times.
- Report: fixed, unchanged and newly broken questions; input tokens per turn before and after; B2's stage 2
  repetitions are the noise baseline (a change inside B2's own flapping rate is not counted as an effect).
- Budget: 8 USD (decision 3); the agent is dropped after its traces are saved (a dropped agent's traces can no
  longer be read: `GET_AI_OBSERVABILITY_EVENTS` returned `002003` on the dropped C0 agent,
  `snowflake/phase4_agent_c/results.md` [measured]).
- Where the result lands: `snowflake/phase5_drill/results.md` (raw), `docs/phase5_notes.md` part 1 (findings), and one
  line per question in the article's cost table (section "Overfitting").
