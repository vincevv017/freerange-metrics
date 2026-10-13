# Configurations: fairness charter

> **Version 12, 2026-10-08** (version 1 on 2026-10-04, before any build; version 2 before LINKML_B1 was created;
> version 3 before LINKML_DP was created; version 4 before LINKML_D was created; version 5 before LINKML_A was
> created; version 6 after the smoke runs, before the campaign; version 7 before LINKML_C was rebuilt (session 8b); version 8 before LINKML_C is republished on contract 0.5.0
> (session 8c-0); version 9 after the step 6 smoke of C (grain rule, contract 0.5.1); version 10 at the close of session 8c-0
> (data freshness line); version 11 before the campaign (B2 brought into conformity); version 12 before C-raw is created (session 13); see
> "Charter versions"). **Frozen**: any
> later change is a new version of this charter, added below with its date and its reason, and shown to the project
> owner before it applies. Contract 0.5.1. Decisions 1 to 6 of session 8 (owner-confirmed 2026-10-03, precisions of
> 2026-10-04). Tags: **[documented]** (Snowflake docs, the contract, DEFINITION.md), **[measured]** (run on this
> account, evidence in the repository), **[inferred]**.

The campaign asks the same questions to six configurations of one agent, and grades every answer with the same
rubric. This page fixes, for each configuration, what it may use, so that a difference in the answers is a
difference of mechanism and not of effort.

## 1. Common to every configuration

| Item | Value |
|---|---|
| Agent object | Permanent agent in `LINKML_METRICS.RAW`, created as `LINKML_METRICS_ROLE`, published by the five-beat cycle (MODIFY LIVE, COMMIT, ADD LIVE VERSION FROM LAST, SET DEFAULT_VERSION read from SHOW VERSIONS); served version read from each trace |
| Caller | `LINKML_SVC` (service user, project role only, no secondary role), key-pair JWT, no role header, REST `agent:run` |
| Model | `claude-sonnet-5-5` |
| Budget | 120 s / 40,000 tokens; **D′ 120 s / 160,000 tokens**, because the `code_toolset_all` bundled skill catalogue alone puts about 133,000 input tokens in each turn, about 66,000 per planning step [measured, phase 0 section 5]; `budget.tokens` is not enforced: D's largest call took 1,520,769 input tokens against 40,000, and D′'s 243,490 against 160,000 (651,698 over one turn of several calls) [measured, `snowflake/phase5_campaign/stage1_results.md` section 3]; `budget.seconds` was enforced on one turn, whose answer ends "I've reached the time limit for this request" [measured, one turn, `docs/phase5_notes.md` finding 89]; the budget is kept equal elsewhere for comparability |
| `orchestration.tool_not_accessible` | `reject`, set in every spec. From September 2, 2026 the default of `orchestration.tool_not_accessible` is `accept` (the run proceeds with HTTP 200 and warning 399569); `reject` and `legacy` are the other values [documented, https://docs.snowflake.com/en/release-notes/bcr-bundles/un-bundled/bcr-2425] |
| Agent shape | One semantic view tool (`cortex_analyst_text_to_sql`) for general questions, plus at most one coverage mechanism; C-raw also has one closing-stock procedure (version 12) |
| Response instruction (identical) | "Answer in two to five sentences. Say which month or period, which basis and which filters the figures refer to. Give only figures that a tool returned. If a tool returns a warning, a flag or a refusal, relay it with its number and explain it in business words. When you give a figure, end with one line: 'Data freshness: <the latest month with stock data>', taken from what a tool returned." (version 7: last sentence added for every configuration) |
| Warehouse | `LINKML_METRICS_WH` (XSMALL), kept running before each call (a GENERATOR sum, state STARTED); queued provisioning and overload recorded for every query of the turn |
| Questions | The 17 questions of `generated/reference_questions.yaml` (12 failure modes, T7_R1, 3 closing-stock questions, the BULK_SCOPE drill) plus G1 and G2: **19** (owner, 2026-10-04: decision 4's "18" was a count error, no 18th question). Smoke runs of session 8: T1, T6, T9, CS_LAST_MONTH_GAP, plus G1 for D and D′ |
| Run logs | `run_call.py` logs, call budgets and extracted traces go to `~/work/assets/linkml-metrics-runs/s8/`, a persistent folder outside the repository (they carry the account host); never a session scratchpad, whose cleaning lost the raw events of sessions 7 and 8a |
| Rubric | `eval/rubric.yaml` version 1, applied by `eval/grade.py`; routing graded on every turn |
| Expected values | `generated/reference_questions.yaml`, every value recomputed in pandas from the dataset alone (`tests/test_reference_oracle.py`); none comes from the procedure |
| Verified queries | B1 and B2 only, at most 3 each, on background members only (never a hero of `data/traps.yaml`); none elsewhere |

### Execution path, the same for every semantic view tool

Cortex Agents generate SQL directly instead of delegating SQL generation to Cortex Analyst, and their usage is
reported under `cortex_agents` [documented, https://docs.snowflake.com/release-notes/2026/other/2026-04-13-cortex-agents-agentic-analyst, Apr 13, 2026]. Measured here: the SQL
the model writes runs over logical-table CTEs that expose dimensions and facts, never metrics; a view-level metric is
reachable only through the qualified `SEMANTIC_VIEW()` form, which the model wrote in none of the 8 statements of
session 8 (`docs/phase4_notes.md` finding 54, `snowflake/phase4_others/results.md`) [measured]. A semantic view
therefore informs the SQL; it does not compute it [inferred]. Every hypothesis below about a semantic view reads with
this in mind.

### Data the configurations read

| Data | Read by |
|---|---|
| RAW base tables (`FCT_STOCK_SNAPSHOT`, `FCT_FORECAST`, `DIM_ITEM`, `DIM_GEO`, `DIM_BATCH`, `DIM_WAREHOUSE`, `DIM_CALENDAR`), with the T7 duplicate item and the stock gaps of SKU-H11 and SKU-H12 | A, B1, the D′ skill script; C's procedure `STOCK_COVERAGE` (version 12: it read RAW from session 8b, the row named only the semantic views and the skill) [measured, generated SQL, session 13 step 1a]; C-raw, its view and both procedures |
| Generated objects on top of RAW: the gap-filled snapshot view `FCT_STOCK_SNAPSHOT_GAPFILLED` (contract `CLOSING_STOCK`), the forward spine, the status bridge and a one-row-per-item projection of `DIM_ITEM` | B2, and D and D′ through their B2 semantic view tool |

## 2. Per configuration

| | A | B1 | B2 | C (session 8b) | D | D′ | C-raw (session 13) |
|---|---|---|---|---|---|---|---|
| Agent | `LINKML_A` | `LINKML_B1` | `LINKML_B2` | `LINKML_C` (rebuilt) | `LINKML_D` | `LINKML_DP` | `LINKML_C_RAW` |
| Semantic view tool | `AP_LINKLM` (Autopilot) | `LINKML_B1_SV` | `LINKML_B2_SV` | `LINKML_B2_SV` | `LINKML_B2_SV` | `LINKML_B2_SV` | `LINKML_C_RAW_SV` |
| Semantic view tool description | written for A | written for B1 | generated (B2) | B2's, less its claim on coverage, routing coverage to the procedure (session 8b) | B2's, less its claim on coverage, routing coverage to the skill | same as D | generated (`compiler/gen_craw.py`): stock on hand at one month and forecast; closing stock and coverage routed to the procedures |
| Tables behind it | RAW | RAW | gap-filled snapshot, spine, bridge, item projection | as B2 | as B2 | as B2 | RAW only (the raw `DIM_ITEM`, its T7 duplicate included); stock `NON ADDITIVE BY` the snapshot month; no coverage or closing-stock metric |
| Coverage mechanism | none | none | none | generated procedure `STOCK_COVERAGE` (SQL Scripting rewrite, session 8b) | skill `linkml-coverage` with `code_execution`: the agent extracts the inputs with its B2 tool and passes them to the script | skill `linkml-coverage` with `code_toolset_all`: the skill lists the RAW base tables, the agent writes the two extraction queries, the script runs them with its own connection and computes; the tables actually read are recorded on every turn (version 4) | `STOCK_COVERAGE`, as C (same tool spec); closing stock: generated procedure `CLOSING_STOCK` (`compiler/gen_closing_procedure.py`, SQL Scripting): the contract's period aggregation at question time on the raw snapshot, no densified data |
| Orchestration instructions | DEFINITION.md section 1, section 7 (closing stock) and section 8 (default scope and analysis month), as written there, without the lines that start with "Provenance:" (version 5) | DEFINITION.md sections 1 to 3, 7 and 8, in prose written by hand | generated from the contract (already carries the two rules of section 8) | generated from the contract (`compiler/gen_agent.py`) | DEFINITION.md sections 1 to 3, 7 and 8, as written there, without the "Provenance:" lines (version 5) | same as D | C's generated instructions, its routing sentence for stock and closing stock replaced by the closing-stock routing rule, plus the closing-stock rule (`compiler/gen_craw.py`) |
| Verified queries | none | at most 3, background members | at most 3, background members | none (B2's, through its view) | none (B2's) | none (B2's) | none |
| Value grounding (`is_enum`, `sample_values`) | none: Autopilot's own, untouched | enrich tool | enrich tool | B2's | B2's | B2's | B2's: the generator copies `is_enum` and `sample_values` of every dimension shared with B2's enriched view as deployed (`snowflake/phase4_others/b2/LINKML_B2_SV_enriched.yaml`); a test checks the equality (owner, session 13 step 3) |
| Generated by the compiler | no | no | yes, with a drift test | yes | B2 part only | B2 part only | yes: view, agent spec and `CLOSING_STOCK`, each with a drift test |
| Approvals | none | none | none | none | none expected (`code_execution` asked none in probe D) | one bash approval per script run, policy `dp`: only the exact script command is allowed | none |

Session 8 builds and smoke-tests A, B1, B2, D and D′. C is not touched; session 8b rebuilds it as B2's semantic view
plus the generated procedure, so that **B2 to C isolates the procedure** and **C to D or D′ isolates the computing
mechanism**.

### A: Autopilot, the untouched baseline

The semantic view the project owner built in Snowsight with Semantic View Autopilot on the seven RAW tables,
`LINKML_METRICS.RAW.AP_LINKLM`, exported as `snowflake/phase4_others/AP_LINKLM_autopilot.yaml`. It is never edited,
enriched or redeployed. Before the agent is built, `SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW` must equal the export,
whitespace aside; if not, A stops. Checked once on 2026-10-04: equal, as text without whitespace and as parsed YAML
[measured].

What Autopilot produced, read from the export [measured]:
- 7 logical tables, one per RAW table, each with a generated description;
- primary keys on `DIM_BATCH`, `DIM_GEO`, `DIM_ITEM` and `DIM_WAREHOUSE`, none on the calendar or the facts;
- **no relationship, no metric, no `NON ADDITIVE BY`, no instruction** (`module_custom_instructions` absent), no
  verified query; stock, forecast and cost columns are facts;
- sample values on every column, up to three each; **date sample values are exported as day numbers** (`19539` is
  2023-07-01), and ID columns are dimensions with sample values.

### B1: hand-written native view on the RAW tables

What a competent practitioner writes without a generator, on the probe A shape (`B1-RANGE`): the RAW tables with
their relationships; stock `NON ADDITIVE BY` the snapshot month; the forecast as a flow; the 24 forward window metrics
`C01..C24` with `RANGE BETWEEN 1 FOLLOWING AND k FOLLOWING` over a numeric month index, and the non-zero month counter;
descriptions on tables, dimensions and metrics. Written in YAML and deployed with
`CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML`: a YAML view with window metrics, `non_additive_dimensions` and `is_enum`
together passed a dry run on 2026-10-04 [measured]. Coverage itself cannot be a metric of this view: a derived metric
over window metrics is rejected (`010273`, phase 0 section 2) [measured], so the agent has to compute the cascade.

### B2: native objects generated from the contract

A new generator, `compiler/gen_native_sv.py`, with a drift test, writes the objects and the agent spec from the
contract: the forward spine (one row per analysis month x item x country with `f01..f24` densified, the window
relative to the analysis month), replicated once per batch status as the status bridge for T3 (forward metrics
divided by the count of distinct statuses), stock read from the gap-filled snapshot, closing stock `NON ADDITIVE BY`
the snapshot month, coverage as a derived metric over plain metrics, **no month variable** (T6 is handled by an
instruction to ask for the month). Every logical table points at a physical view, not at a query, so that the enrich
tool can profile it (it reads `database.schema.table` only) [measured on the tool's code]. Instructions generated
from the contract.

### D and D′: the coverage skill

One skill, `linkml-coverage`, written for this session: a `SKILL.md` (the algorithm of DEFINITION.md section 2 as a
procedure, with its routing description) and `coverage.py`, written from DEFINITION.md section 2, never copied from
or importing `data/coverage_ref.py`. Each agent has its own stage (`SKILLS_D`, `SKILLS_DP`): `code_toolset_all` mounts
the whole stage [measured, phase 0 section 5]. Both files are shown to the project owner before upload.
- **D**: `code_execution`. The sandbox cannot query data (restricted session scope, probe D) [measured]: the agent
  extracts the stock at the analysis month and the forecast of t+1..t+24 with its B2 tool and passes the numbers to
  the script.
- **D′**: `code_toolset_all`. The skill lists the RAW base tables; the agent writes the two extraction queries; the
  script runs them itself under the caller's role [measured, phase 0 section 5] and computes, so no number goes
  through the model. The tables are not constrained: the tables actually read (base, or generated from the contract)
  are recorded on every turn (version 4). General questions go to the B2 tool.

### Value grounding for B1 and B2 (decision 5)

The project owner's value-grounding tool (not published) profiles every dimension of a model YAML against the live
data and sets `is_enum` and `sample_values` only, both read from the data. It is run to a file, never with `--deploy` (its deploy path
calls the creation procedure with `SELECT`, where this account needs `CALL`, and `--replace` drops the object and its
grants): threshold 30, ID and date dimensions excluded, the CSV report kept. It runs as LINKML_SVC (project role only,
no secondary role; the tool itself never clears secondary roles), with its `.env` in the session scratchpad, outside
the repository, and its two packages in the `tools` extra of `pyproject.toml`. The enriched YAML is deployed through
this project's own path; the enriched YAML and the report are committed; the tool's code is never copied here. A is
not enriched.

## 3. Hypotheses to falsify (expected failures)

Each line is a hypothesis about the full campaign. Session 8 tests the smoke questions only; the others stay
"not yet tested" until the campaign. A hypothesis is refuted by one correct answer on its question, confirmed by
the predicted wrong answer.

| Id | Configuration | Question | Expected failure (hypothesis) | Why |
|---|---|---|---|---|
| H-A1 | A | T1, T4, BEYOND_H | Coverage not computed by the algorithm (no interpolation, no 24-month window, or a ratio of totals) | A's instructions carry the definition (section 1), not the algorithm (section 2); the view has no metric |
| H-A2 | A | T2 | 5.0 (missing months skipped) | Nothing densifies the calendar |
| H-A3 | A | T3 | Status filter applied to the forecast (no number) or ignored (10.0) | No relationship, no applicability rule in section 1 |
| H-A4 | A | T7, T7_R1, G2 | Fan-out: 3.0, two lifecycle rows, SE +4,800 EUR | Joins to the raw `DIM_ITEM`, which holds SKU-H06 twice |
| H-A5 | A | T9 | A positive coverage from May's stock, or "no data" instead of 0 | No rule makes an absent snapshot 0 |
| H-A6 | A | T6 | A month picked, or a coverage over the year | Section 1 names the analysis month but no instruction asks for it (version 2: section 8 now asks for it in the instructions; nothing in the view enforces it) |
| H-A7 | A | CS_LAST_MONTH_GAP | "No data for June" instead of 0, or May's 350 | Section 7 states the rule, but nothing in the view keeps the member |
| H-A8 | A | BULK_SCOPE, T5 | 17.4 (BULK counted); a number in packs | Neither the default scope nor the forbidden unit is in A's instructions (version 2: the default scope is, through section 8; version 3 correction: the forbidden unit is too, since section 1 says raw units are never added across products; nothing in the view enforces either) |
| H-B1-1 | B1 | T1, T2, T4, T8 | Right only when the model writes the cascade over the forward sums itself; wrong when it filters the analysis month before the window (T4: no forward forecast) | Coverage cannot be a metric (`010273`); a month filter inside the query kills the forward window (phase 0) |
| H-B1-2 | B1 | T3 | `010959`-type failure or the filter pushed to the forecast | No path from batch to forecast (phase 0) |
| H-B1-3 | B1 | T7, T7_R1, G2 | Fan-out as H-A4 | RAW `DIM_ITEM` |
| H-B1-4 | B1 | T9, CS_LAST_MONTH_GAP | May's 350 carried (3.5 or a positive coverage; closing 350) | `NON ADDITIVE BY` on the RAW snapshot carries the last known value (probe closing, session 6) |
| H-B1-5 | B1 | BULK_SCOPE | 17.4 | Sections 1 to 3 declare item type stock-only, not the default scope (version 2: section 8 states it in the instructions; the view does not apply it) |
| H-B1-6 | B1 | T6 | Plausible wrong number over the year, or a month picked | No variable, no instruction to ask (version 2: section 8 asks for the month; no variable) |
| H-B2-1 | B2 | T7_R1, G2 | Fan-out persists (two lifecycle rows; SE +4,800 EUR through the projection when lifecycle is kept) | A semantic view cannot refuse at query time (phase 3, finding 41) |
| H-B2-2 | B2 | T2, BEYOND_H, BULK_SCOPE, T7 | Right number, warnings not relayed | No warning mechanism outside the procedure |
| H-B2-3 | B2 | T6 | Refuted expected: asks for the month | Generated instruction |
| H-B2-4 | B2 | T9, CS_LAST_MONTH_GAP | Refuted expected: 0 | Gap-filled snapshot |
| H-B2-5 | B2 | T5 | Refuted expected: refusal by the model | Generated instruction, forbidden unit |
| H-B2-6 | B2 | any coverage question | The model rewrites coverage from the description instead of selecting the metric, and departs from it | Execution path: metrics resolve only in the qualified semantic form |
| H-D-1 | D | coverage questions | The algorithm is right, the inputs are wrong where the extraction is (T3 filter, T7 fan-out, BULK scope, a skipped month in the 24 values) | The model moves numbers between tools |
| H-D-2 | D | any | More planning steps, more tokens and a longer turn than B2 | Extraction, skill load and script are extra steps |
| H-D-3 | D | G1, CS | Routed to the B2 tool, not to the skill | Skill description with negative scope |
| H-DP-1 | D′ | coverage questions | The algorithm is right, the extraction SQL the model writes against RAW repeats A's and B1's join errors (T2, T3, T7, BULK) | The script computes, the model still writes the extraction |
| H-DP-2 | D′ | any | About 130,000 input tokens per turn, one approval per run, the longest turns | Bundled skill catalogue (phase 0) |
| H-DP-3 | D′ | G1 | Routed to the B2 tool | As H-D-3 |
| H-ALL-1 | A, B1, B2, D, D′ | T2, T7, BULK_SCOPE | No warning relayed with its number | Only the procedure returns warnings |
| H-CR-1 | C-raw | CS_LAST_MONTH_GAP, CS_FAMILY, N1 and N2 (closing half) | Refuted expected: 0, 450, May 350 and June 450, through `CLOSING_STOCK` with no gap-filled snapshot | The period aggregation of the contract at question time (version 12) |
| H-CR-2 | C-raw | coverage questions | The same answers as C, turn for turn, up to the model's variance | Same procedure, same tool spec, same instructions for coverage |
| H-CR-3 | C-raw | G2 | Refuted expected through `CLOSING_STOCK` (one item row per item); if routed to the view instead, SE +4,800 EUR | The view reads the raw `DIM_ITEM`, which holds SKU-H06 twice |
| H-CR-4 | C-raw | any closing-stock question | Routed to the view when worded as stock on hand; on a period, the last known value of a gap (as H-B1-4) | Routing by the instructions only |
| H-CR-5 | C-raw | G1 | Right, as C | Same grounding as C's view, on the raw tables |

## 4. Out of scope by configuration

No question of the set is out of scope for any configuration in session 8: every configuration has a semantic view
tool that can reach stock, forecast and closing stock. An answer that declines a question is therefore graded on the
refusal criterion only where the question expects a refusal (T5, T6, T7_R1), and wrong elsewhere.

## 5. Open questions of this charter

1. Closed 2026-10-04: the campaign set is 19 questions (17 of the file plus G1 and G2); the "18" of decision 4 was a
   count error.
2. Closed 2026-10-04 (version 7): agent C takes the common response instruction; its longer session 7 instruction is
   dropped, and the common one gains one sentence on warnings, flags and refusals, for every configuration.

## Charter versions

| Version | Date | Change | Shown to the owner |
|---|---|---|---|
| 1 | 2026-10-04 | First version, before any build. Amended the same day before any build or graded turn, at the owner's request: question count 19 confirmed, run-log folder added; rubric version 1 gains the indistinguishable-precision guard | at commit |
| 2 | 2026-10-04 | DEFINITION.md section 8 (default scope and analysis month: BULK stock excluded from coverage unless item_type is filtered explicitly, the excluded stock announced; coverage measured at one month, ask when the question gives none or a period) added to the orchestration instructions of A, B1, D and D′. B2 unchanged: its generated instructions carry both rules. Reason: the two rules were in the contract only, so only B2 and C received them; BULK_SCOPE and T6 must measure each configuration's capacity, not a gap in its documentation. Applied before LINKML_B1 was created; B2's smoke (version 1) is unaffected. Hypotheses H-A6, H-A8, H-B1-5 and H-B1-6 keep their predicted failures, their reasons are annotated | owner's request, diff shown before B1's CREATE |
| 3 | 2026-10-04 | (a) The semantic view tool of D and D′ carries B2's generated description less its claim on coverage, with coverage routed to the linkml-coverage skill (otherwise the two tools compete for coverage questions); session 8b applies the same rule to C (generated description, routed to the procedure). (b) DEFINITION.md section 8 gains "Coverage is given in quantity equivalent unless the question asks for value." (the default unit was declared in the contract only: `unit_variants`, QTY_EQ `is_default`); A, D and D′ receive it at their CREATE, B1 by one publish cycle with no agent call just before the campaign; B2's generated instructions already carry it. (c) H-A8's annotation corrected: section 1, which A receives, already rules out adding raw units across products. Applied before LINKML_DP was created; no graded turn changes | owner's request, diff shown before D′'s upload |
| 4 | 2026-10-04 | (a) DEFINITION.md section 8's unit sentence extended to closing stock: "Coverage and closing stock are given in quantity equivalent unless the question asks for value." The contract declares one default unit variant for the whole contract (`unit_variants`: QTY_EQ `is_default: true`), not per measure, so it applies to closing stock as well; the three closing-stock questions give no unit. D and A receive it at their CREATE; B1 and D′ (created before version 4) by one publish cycle each, with no agent call, just before the campaign; B2's generated instructions name both closing-stock metrics with no default between them, unchanged (generated from the contract, whose closing view exposes both units). (b) D′'s tables are not constrained: the skill lists the base tables, the agent writes the queries, the tables the script actually reads are recorded per turn (`records.py`, "tables read by the script") | owner's request, before LINKML_D was created |
| 5 | 2026-10-04 | (a) DEFINITION.md: the internal references of the sections given to agents (session decisions, `data/traps.yaml` and trap names, the contract's internal names such as `CLOSING_STOCK`, `LAST_PERIOD`, `beyond_horizon`) moved to lines that start with "Provenance:", which the extraction drops (`snowflake/phase4_others/definition_text.py`, used by `a/build_spec.py` and `d/build_specs.py`); `tests/test_extracted_instructions.py` asserts no instruction of A, B1, B2, D or D′ carries "session", "traps", a trap id or those names. A is created with the version 5 text; D and D′ are republished by one cycle each, no agent call, before the campaign. (b) The compiler states the contract's default unit for every figure (`gen_agent.default_unit_sentence`: "Every figure, coverage, closing stock and forecast alike, is given in QTY_EQ (kg or L equivalent) unless the user asks for VALUE (EUR)."): B2's generated instructions carry it, B2 is republished by one cycle before the campaign, C takes it in session 8b | owner's request, before LINKML_A was created |
| 6 | 2026-10-04 | The linkml-coverage skill (D and D′) gains one line in its fast path: "`coverage.py` is in this skill's folder, even if a listing shows it at 0 B: run it, and never do the computation yourself." Reason: the server-side skill load lists the script at 0 B (probe D, session 8 D T9), and D once skipped the script and computed by hand. Re-uploaded to SKILLS_D and SKILLS_DP (content read back); a skill body is read live, no spec change. D's T9 of the smoke stays recorded as it was; no new smoke | owner's request, after the smoke runs |
| 7 | 2026-10-04 | (a) The common response instruction gains one sentence for every configuration: "If a tool returns a warning, a flag or a refusal, relay it with its number and explain it in business words." Agent C takes the common response (its session 7 response, which asked for one decimal, named the month, unit and filters and relayed warnings, is dropped). A, B1, B2, D and D′ are republished by one five-beat cycle each, with no agent call. (b) Agent C rebuilt (decision 5 of session 8b): B2's semantic view tool with B2's generated description less its claim on coverage, routed to stock_coverage (the version 3 rule, generated by `compiler/gen_agent.py`), plus the generic tool on the generated procedure, now SQL Scripting (`STOCK_COVERAGE`; the Python one kept as `STOCK_COVERAGE_PY` until the campaign is over); orchestration generated: routing, the coverage rules, the contract's default unit; `tool_not_accessible: reject`. The raw-pack refusal stays in the generated instructions (decision 7) | owner's request, diff shown before LINKML_C was rebuilt |
| 8 | 2026-10-05 | Contract 0.5.0 (session 8c-0): coverage is a time measure on a governed basis. (a) One basis sentence for every configuration, replacing "Coverage and closing stock are given in quantity equivalent unless the question asks for value" (DEFINITION.md section 8, A, B1, D, D′) and the generated "Every figure, coverage, closing stock and forecast alike, is given in QTY_EQ (kg or L equivalent) unless the user asks for VALUE (EUR)" (B2, C): "Coverage is always in months. Stock and forecast are measured on one basis before the ratio: the item's own unit for a single item; kg or L equivalent for items of the same dimension, unless the question asks for value (EUR); value only when items of different dimensions are combined. Closing stock and forecast follow the same basis rule." Generated for B2 and C (`compiler/gen_agent.py`, `basis_rule_sentence`), copied into DEFINITION.md section 8 for A, D and D′ (extracted), by hand into B1's instructions, and into the linkml-coverage skill text (D, D′), which stated a unit. (b) DEFINITION.md section 1 (given to A, B1 by paraphrase, D, D′) gains the basis, the stockout month and the questions on stock-outs and dormant stock (decision 6). (c) The common response instruction says "which basis" instead of "which unit": a coverage has no unit other than months, and rubric version 3 grades the basis named. (d) C's tool: parameter `basis` (was `unit_variant`, optional, default QTY_EQ), `coverage_below`, `coverage_above`, `rank_first`; its instructions say to re-call with an allowed basis after BASIS_NOT_COMPARABLE only saying that the basis changed and why, and never to sort or filter coverage rows. (e) The semantic views: QTY_EQ metric descriptions say kg and L never add up (B2 generated, B1 by hand), `dimension` exposed; A's Autopilot view unchanged. | before publication (step 5) |
| 9 | 2026-10-05 | Contract 0.5.1, owner's text verbatim (session 8c-0, step 7a). The grain rule of version 8 ("a country named gives sku_code filtered on that country", written for list questions) was applied by C to every question: asked for the coverage of France, C requested item rows and a grand total, then picked the lowest and highest item coverage itself (step 6, DIM_MIX). Replaced for every configuration by: "The grain follows the question. A question that asks for a list of products or items takes items as grain: with a country named, sku_code filtered on that country; worldwide or with no country, sku_code; for item and country pairs, sku_code and country_code. A question that asks for one figure for a scope (a country, a family, a region) takes that scope's grain and its filters, with no item rows and no grand total unless the question asks for them." In the contract (`member_selection.grain_rule`, metamodel 0.4.1), C's generated instructions, DEFINITION.md section 1 (A, D, D′ by extraction), B1's instructions by hand (4 lines added). No instruction forbids citing rows: the shape of the call is fixed, not the model. The grader gains the governance flag ROWS_COMMENTED, outside correctness. | owner's text, before publication (step 7d) |
| 10 | 2026-10-05 | Owner, session 8c-0 step 8 (decision 5): the common response instruction of every configuration gains, verbatim: "When you give a figure, end with one line: 'Data freshness: <the latest month with stock data>', taken from what a tool returned." Generated for B2 and C (`compiler/gen_native_sv.py`, RESPONSE), copied into A, D and D′ by their build scripts (they take B2's response), by hand for B1 (one sentence over 2 changed lines and 1 added). Reason: an answer says how recent its data is. The grader records FRESHNESS_STATED (present; equal to June 2026, the dataset's LATEST), a measure, never a grade. | owner's text, before publication |
| 11 | 2026-10-05 | Conformity, no new rule (owner, session 8c, decision 1). Version 9's grain rule had missed a generated target: B2's instructions are generated by `compiler/gen_native_sv.py`, which did not carry `member_selection.grain_rule`, and the identity test of session 8c-0 (`tests/test_contract.py::test_grain_rule_is_the_owners_text_everywhere`) listed C, B1, A, D and D′, not B2. The generator now inserts the owner's text verbatim after "Never add or average coverage rows; query the coarser grain instead." (453 characters; nothing else in B2's spec changes, its view is unchanged). `tests/test_charter_conformity.py` reads every sentence the charter imposes on every configuration (the common response with its warnings and data freshness sentences, the basis sentence, the grain rule) from this file and asserts each is in the six configurations' instructions word for word, where the charter places it; it failed on B2's grain rule before the fix. B2 is republished by the five-beat cycle, no agent call; the other five agents do not change | owner's decision, diff shown before B2's ALTER |
| 12 | 2026-10-08 | Configuration C-raw (owner, session 13): the contract without any reshaped data. Agent `LINKML_C_RAW`, three tools: the semantic view `LINKML_C_RAW_SV` on the raw fact and dimension tables only (stock `NON ADDITIVE BY` the snapshot month for stock on hand, the forecast; no coverage and no closing-stock metric, both routed to the procedures by the descriptions), `STOCK_COVERAGE` unchanged (C's tool spec), and the new generated procedure `CLOSING_STOCK` (the contract's period aggregation `CLOSING_STOCK`, `LAST_PERIOD`, member set `ANY_SNAPSHOT_IN_PERIOD`, a gap in the last month closes at 0; parameters as JSON strings, the basis rule judged on the rows returned, the contract's refusal codes in check order, a period with a month not loaded refused, totals recomputed, lineage by query ids; the eight contract templates that name coverage or `as_of_months` reworded for closing stock, the generator holding the contract text it rewords). Value grounding: B2's, copied by the generator from B2's enriched file for every shared dimension. Orchestration: C's generated instructions, its sentence "Route questions on stock on hand, closing stock and demand forecast to b2_semantic_view." replaced by the closing-stock routing rule, plus one closing-stock rule; response: the common one. The six existing agents, their views and `STOCK_COVERAGE` do not change. Correction of section 1, "Data the configurations read": C's procedure has read RAW since session 8b; the row named only the semantic views and the skill. `tests/test_charter_conformity.py` covers seven configurations | before `CLOSING_STOCK`, `LINKML_C_RAW_SV` and `LINKML_C_RAW` are created (session 13 STOP 1) |
