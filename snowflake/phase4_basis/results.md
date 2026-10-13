# Session 8c-0: coverage is a time measure on a governed basis

Contract 0.4.2 to 0.5.0, metamodel 0.3.0 to 0.4.0, rubric version 2 to 3. Owner decisions of 2026-10-05 (decisions 1
to 7, precisions of the same day). Tags: **[documented]** (Snowflake docs, the contract, DEFINITION.md, a skill
reference), **[measured]** (run on this account or locally, evidence here or in `~/work/assets/linkml-metrics-runs/s8c0/`,
outside the repository), **[inferred]**. Warehouse credit price used in every cost line: 3.90 USD (Enterprise, on
demand, AWS Paris; owner).

## Why

Coverage answers "how many months will the stock last". Its result is always in months. QTY_EQ and VALUE were the
bases stock and forecast are measured on before the ratio, but the generated sentence "Every figure, coverage,
closing stock and forecast alike, is given in QTY_EQ" (compiler/gen_agent.py, `default_unit_sentence`, read by B2 and
C), DEFINITION.md section 8 ("Coverage and closing stock are given in quantity equivalent") and the parameter name
`unit_variant` all said that coverage had a unit, and QTY_EQ added kilograms and litres together. Agent C answered
"2.8 months ... The figures are in QTY_EQ (kg or L equivalent)" in session 8b. [measured, 8b smoke answers]

## Step 0: inventory (no change)

| Place | What it said or did | Fate |
|---|---|---|
| `contract/metamodel.yaml` | `UnitVariant`, `ForbiddenUnit`, `MeasureColumn.unit` | replaced by `MeasureBasis`, `ItemDimension`, `BasisModel`, `MeasureColumn.basis`; `ExhaustionPeriodRule`, `MemberSelection` added |
| `contract/stock_coverage.yaml` | `unit_variants` QTY_EQ ("kg or L equivalent", default) and VALUE, `forbidden_units` RAW, refusals UNIT_RAW_NOT_ADDITIVE and UNIT_UNKNOWN, parameter `unit_variant` | `measure_bases` NATIVE, QTY_EQ, VALUE; `basis_model`; BASIS_NOT_COMPARABLE, BASIS_UNKNOWN, SELECTION_INVALID; parameters `basis`, `coverage_below`, `coverage_above`, `rank_first`; attribute `dimension`; QE_ITEM_DIMENSION; failure mode DIM_MIX |
| the published dataset | raw units "10 x 1 kg **or** 1 L": no item carried its dimension | each family declares its dimension; `dimension` and `base_unit` written to DIM_ITEM |
| `data/load_snowflake.py` | `--replace` of the seven tables only | `--tables` added; DIM_ITEM reloaded alone |
| `data/traps.yaml` | T5 `unit_variant: RAW`, UNIT_RAW_NOT_ADDITIVE | T5 `basis: NATIVE`, BASIS_NOT_COMPARABLE; DIM_MIX; `showcase_questions` |
| `data/coverage_ref.py`, `data/checks/check_dataset.py` | `UNIT_VARIANTS`, `FORBIDDEN_UNITS` | `BASES`; `py_rows`/`sql_rows`, `select`/`sql_select`, `summary`, `allowed_bases`, `stockout_month` |
| `compiler/gen_agent.py` | `default_unit_sentence` (the faulty sentence) | `basis_rule_sentence` (charter version 8, step 5), `view_bases`, `view_metric_note` |
| `compiler/gen_native_sv.py` (B2), `compiler/gen_closing_sv.py` | one metric family per unit variant; "Refuse coverage in raw units" | one per basis comparable across items; QTY_EQ metric descriptions say kg and L never add up; `dimension` dimension |
| `compiler/gen_dmf.py`, `generated/dmf.sql` | QE_EQ_FACTOR only | QE_ITEM_DIMENSION (custom: ACCEPTED_VALUES cannot be called ad hoc, its lambda argument is refused, `snowflake/phase2_dmf/results.md` [measured]) |
| `compiler/gen_procedure.py`, `procedure_handler.py`, `procedure_scripting.py` | unit checks, unit columns, warning "in the unit asked" | basis checks, per-row items and dimensions, stock unit, stockout month, selection, summary, set apart, warning per unit |
| `compiler/gen_questions.py`, `generated/reference_questions.yaml` | `unit_variant`; G1 "kg or L equivalent" | `basis`; G1 "L equivalent"; DIM_MIX and four showcase questions |
| B1 (`b1/LINKML_B1_SV*.yaml`, `agent_b1.yaml`) | "kg or litre equivalent" | edited by hand (below); agent text at step 5 |
| A (`AP_LINKLM_autopilot.yaml`, `agent_a.yaml`) | Autopilot view sees RAW_UNIT, QTY_EQ_FACTOR and the raw, qty_eq and value columns; DEFINITION sections 1, 7, 8 | view untouched; instructions at step 5 |
| D and D′ | DEFINITION sections 1, 2, 3, 7, 8 | instructions at step 5 |
| `docs/DEFINITION.md` | section 1 "Two variants ... same unit"; section 8 "given in quantity equivalent" | sections 1, 2, 8 rewritten, T5 row of section 4 |
| skill `linkml-coverage/SKILL.md` | "the unit (quantity, kg or litre equivalent ...)" | step 5 |
| `eval/rubric.yaml`, `eval/grade.py` | T5 expects UNIT_RAW_NOT_ADDITIVE; no basis rule | rubric version 3 |

**Where each item's dimension comes from.** No column carried it: `raw_unit` is a pack size common to kg and L items.
It derives without a new fact from the family, which is homogeneous: VOLUME for BEV_ICED, BEV_JUICE and PANTRY_OIL
(12 items, 13 rows with the T7 duplicate), MASS for every other family (48 items). The hero names agree ("Sunflower oil
1 L", "Iced tea ... 1 L"). [measured, local] **Path 1 taken** (owner, 2026-10-05): dimension declared per family in
`traps.yaml` and the published dataset, `dimension` and `base_unit` written to DIM_ITEM; no
1 L = 1 kg convention.

## Step 1: contract 0.5.0

- **Basis model.** `measure_bases`: NATIVE (each item in its own unit, valid when every returned row holds one item),
  QTY_EQ (kg or L equivalent, valid when every returned row and total holds items of one dimension, the default),
  VALUE (EUR, always valid). `basis_model.validity_scope: RETURNED_ROWS`: judged on the rows and totals the call
  returns, after member selection; a summary of kept rows is split by unit or omitted, it never refuses the call
  (owner's precision). The default basis is refused like any other where not comparable, never switched.
  [documented, contract]
- **Totals today.** `totals` defaults to `[]`: no total row is returned unless asked, so a selection call never
  returns a total by default and nothing had to be dropped. [documented, contract `parameters.totals`]
- **Stockout month.** `t + ceil(coverage)` months: the forecast window starts at t+1 (`window_start_offset: 1`,
  DEFINITION.md section 1), so a coverage in (n - 1, n] runs out in month t+n; 0.5 and 1.0 from June 2026 both give
  July 2026, a coverage 0 gives June 2026; none with NO_DEMAND or BEYOND_HORIZON. DEFINITION.md says nothing
  otherwise. [documented]
- **Member selection.** `coverage_below` (0 < coverage <= N), `coverage_above` (coverage > N; with
  `coverage_below`, a window), `rank_first` (lowest first, ties by the grain codes in grain order), per analysis month,
  on detail rows only; NO_STOCK and NO_DEMAND members set apart, counted and named; summary per month: the count of
  kept rows and their stock per unit (one sum per base unit on QTY_EQ, EUR on VALUE, none on NATIVE across items).
- `tests/test_contract.py`: 43 passed, including the owner's two stockout tests at contract level. [measured]

## Step 2: data and objects

**Fingerprints.** `snowflake/phase4_basis/fingerprint.py` reads, per RAW table, the row count, `HASH_AGG(*)` and the
table comment (which carries the first 16 hex of the dataset's CSV sha256), before and after the reload
(`fingerprint_before.json`, `fingerprint_after.json` in the run folder). [measured]

| Table | Locally (sha256 of the CSV, before / after) | On the account (count, HASH_AGG, comment) |
|---|---|---|
| FCT_STOCK_SNAPSHOT | b951eba10e8a0922 / same | 60,915 rows, 5398764743214736073, same |
| FCT_FORECAST | 8f41375fdd3b745b / same | 15,306 rows, 4411698385816863199, same |
| DIM_CALENDAR, DIM_GEO, DIM_WAREHOUSE, DIM_BATCH | same | same |
| DIM_ITEM | b3032ff2d01c478c / 366ce5ee4af0cb6c | 61 rows; HASH_AGG and comment changed (schema 0.5.0) |

DIM_ITEM differs only by its two new columns: the old file equals the new one with `dimension` and `base_unit` dropped
(pandas `equals`). The loader replaced DIM_ITEM alone (`--tables DIM_ITEM`); no fact table was touched. [measured]

**Objects regenerated and redeployed** (perso, project role, no secondary role). [measured]

| Object | How | Check |
|---|---|---|
| Custom DMFs, ad hoc checks | `run_dmf.py` (generated/dmf.sql) | 36 checks, 0 failure; QE_ITEM_DIMENSION = 0; no DMF attached |
| FCT_STOCK_SNAPSHOT_GAPFILLED, CLOSING_STOCK_SV | `deploy.py --file generated/closing_stock_sv.sql` | created; `dimension` dimension, metric comments per basis |
| B2_ITEM, B2_STATUS, B2_FORECAST_SPINE | `deploy.py --file generated/b2_native_views.sql` | B2_ITEM carries `dimension`, `base_unit` |
| LINKML_B2_SV | `apply_grounding.py` (18 grounded members carried over), `deploy_sv.py` | 126 members, same names as the file, no grounding difference; object check values as in session 8 |
| LINKML_B1_SV | edited by hand, `deploy_sv.py` | 54 members; object check values as in session 8 (T7 and CS_LAST_MONTH_GAP keep their known native defects) |

**B1, by hand (a governance cost).** In each of its two YAML files (`LINKML_B1_SV.yaml`, `LINKML_B1_SV_enriched.yaml`):
the item table description (dimension named), two dimension lines added (`dimension`, `base_unit`; in the enriched
file with `is_enum` and sample values), the descriptions of `stock_qty` and `forecast_qty` (kg and L never add up:
group or filter by `item.dimension`, or use the value metric), and the two verified-query questions ("in kg
equivalent": both families are MASS). 7 lines added or changed, 5 removed, per file. [measured, git diff]

**A's Autopilot view stays as it is.** It sees RAW_UNIT, QTY_EQ_FACTOR and the raw, qty_eq and value columns of stock
and forecast; it cannot see `dimension` or `base_unit` (its YAML lists DIM_ITEM's columns as of session 8). What A
knows of the basis rule comes only from DEFINITION.md sections 1 and 8 in its instructions (step 5). [documented, the
view's YAML]

**Side effect to record.** B2, C, D and D′ read LINKML_B2_SV by name, so their semantic view tool sees the new
descriptions from step 2 on, before any republication. The procedures' signature changed (step 3), so the published
LINKML_C (charter version 7, which sends `unit_variant`) cannot call its tool until step 5 republishes it. No agent
call was made in between. [inferred]

## Step 3: procedures

Both targets generated from the contract, tests first (`tests/test_procedure.py`: 28 tests added for the basis, the
stockout month and the selection, the existing ones moved to named arguments). Signature, both procedures:
`(AS_OF_MONTHS, GRAIN, FILTERS, BASIS DEFAULT 'QTY_EQ', TOTALS DEFAULT '[]', COVERAGE_BELOW DEFAULT NULL,
COVERAGE_ABOVE DEFAULT NULL, RANK_FIRST DEFAULT NULL)`, all VARCHAR: optional arguments come last, so `basis` moved
after `filters`. The 5-argument overloads were dropped first (`DROP PROCEDURE ... (VARCHAR x 5)`): a new signature
creates an overload beside the old one. [measured]

How the basis is judged: each grain set gets one more CTE, the items of each member (its stock items after the default
scope, and the forecast items of its conformed key) with their count, their dimension count, the base unit and the
native unit; the coverage statement carries them to its rows. A shared post-processing block (the same SQL in both
targets) gives each row its `stock_unit` and `stockout_month`, keeps the selection (ROW_NUMBER per analysis month,
NO_STOCK and NO_DEMAND set apart), and computes the summary as window sums over the kept rows. BASIS_NOT_COMPARABLE is
then decided on the rows returned (stage 4 of the Scripting body, after the coverage statement). No new statement:
the quality and coverage statements still run together. [measured]

| Check | Result |
|---|---|
| `tests/test_procedure.py`, SQL Scripting (STOCK_COVERAGE) | **113 passed** (9 min 58 s) [measured] |
| `tests/test_procedure.py`, Python (STOCK_COVERAGE_PY) | **113 passed** (11 min 35 s, both suites ran at the same time) [measured] |
| Parity by direct CALL, `snowflake/phase4_c_sql/parity.py` | **181 / 181 identical** at the first run (the 134 cases of 8b moved to named arguments and the new codes, plus 47: the basis, its synonyms and default, the grouping by dimension, NATIVE on one item and on several, the stockout heroes, the five new questions, windows, empty selections, a series, a snapshot-only grain, selection with totals, the refused grand total, SELECTION_INVALID cases). Tolerance 1e-9 absolute or 1e-12 relative (the summary sums tens of millions of EUR) [measured, `parity_run1.log`] |

**Direct latency, SQL Scripting (the procedure C calls).** Three hero calls (T1, T2, T9) right after the deployment,
then three more of each, warm warehouse, no cached result (`latency_direct.json`, `latency_direct_warm.json`).
[measured]

| Run | CALL ms | Children compilation (sum) | `coverage_ms` | `quality_ms` |
|---|---|---|---|---|
| First calls after deploy (T1, T2, T9) | 15,776 / 8,831 / 5,935 | 13.2 s / 12.5 s / 8.4 s | 2.8 / 3.1 / 2.4 s | 2.4 / 2.1 / 1.8 s |
| Warm, 9 calls | **median 5,485** (4,157 to 16,258) | 5.9 to 25.5 s | 1.9 to 3.7 s | 1.5 to 3.1 s |
| Session 8b, 50 hero calls | **median 3,480** (2,970 to 4,330) | | | |

**A regression of about 2 s on the median, with one 16 s outlier.** Execution of the child queries is unchanged
(0.5 to 1.2 s); the time goes to compiling them. The coverage statement now carries one items CTE per grain set and
the post-processing block (stock unit, stockout month, selection, summary, refusal reason), and the statements that
build its text carry ten nested REPLACE calls; in 8b the quality and coverage statements took 1.4 s together, here the
coverage statement alone takes 1.9 to 3.7 s. [measured; the attribution to compilation is measured, the attribution
to the post-processing block is inferred] Not optimised in this session (stop rather than widen). Options for the
owner: accept it; generate the light block when no selection is asked (no selection CTEs, no summary); or move the
basis check into the quality statement and keep the coverage statement as in 8b for calls without selection.

## Step 4: oracle and questions

- **Expected values, never from the procedure.** `data/coverage_ref.py` gains `py_rows` (pandas) and `sql_rows`
  (DuckDB), each giving per row its coverage, stock, forecast, item count, dimension count, base unit and native unit,
  and `select` / `sql_select` (Python sort against SQL `QUALIFY ROW_NUMBER()`), `summary`, `allowed_bases`,
  `stockout_month`. The two paths agree on every row, order, unit, stockout month, set-apart member and summary of the
  five questions. `data/checks/check_dataset.py` (sections 2-3 and 6b) recomputes them: no failure.
  `tests/test_reference_oracle.py`: 27 passed (4 skipped by design: the showcase questions have their own test).
  [measured]
- **T5** expects BASIS_NOT_COMPARABLE with QTY_EQ and VALUE allowed; the quantity-equivalent value to offer (2.3651)
  and the raw-pack wrong value (8.4966) are unchanged. [measured]
- **The five questions** (June 2026), in `data/traps.yaml` (DIM_MIX and `showcase_questions`) and
  `generated/reference_questions.yaml`, played in stage 1 by `tests/test_procedure.py` on both procedures:

| Id | Question | Expected |
|---|---|---|
| (a) S_OWN_UNIT | What is the stock coverage of SKU-0046 in its own unit (cases) in June 2026? | 3.0626 months, stock unit CASE_10, stockout 2026-10-01; equal on QTY_EQ (kg) |
| (b) DIM_MIX | What is the stock coverage in France in June 2026? | QTY_EQ refused, BASIS_NOT_COMPARABLE, VALUE allowed; 8.7009 months on VALUE; 10.2080 (kg and L added) wrong |
| (c) S_STOCKOUT_COUNTRY | Which products will stock out within the next 3 months in France, from June 2026? | SKU-H02 0.5 (kg, July), SKU-0039 1.0124 (kg, August), SKU-0031 1.8433 (L, August), SKU-0010 2.2095 (kg, September); summary 4 rows, 11,030 L and 1,030 kg; nothing set apart |
| (d) S_FIRST_WORLD | Worldwide, which 10 products will stock out first from June 2026, not counting those already out? | SKU-H02, SKU-H07, SKU-0046, SKU-0043, SKU-0036, SKU-H12, SKU-0025, SKU-0009, SKU-0041, SKU-0017 (0.5 to 5.684 months); summary 95,030 L and 829,667 kg; set apart NO_STOCK SKU-H08, SKU-H11, NO_DEMAND SKU-H09 |
| (e) S_DORMANT_VALUE | Across all countries, which item and country pairs have more than 12 months of coverage in June 2026, and how much stock value does that tie up? | 28 pairs, 70,987,982.99 EUR; set apart NO_STOCK (SKU-H08, NL), (SKU-H11, CH), NO_DEMAND (SKU-H09, BE) |

  (e) in proportion: the 28 pairs (12.7 % of the 220 STANDARD item and country rows) hold 31.05 % of the STANDARD
  stock value at June 2026 (228,619,582.07 EUR): in the dataset, long-coverage pairs hold more stock. Not out of proportion. Worldwide (grain
  sku_code) the same question keeps 1 row, SKU-H10, 50 months (BEYOND_HORIZON), 20,000 EUR: aggregating across
  countries hides almost all of the dormant stock. [measured, both references]
- **Rubric version 3** (`eval/rubric.yaml`, `eval/grade.py`, tests first in `tests/test_grade.py`, 64 passed): a
  coverage answer is correct only if it gives months and names its basis; "coverage in kg", "the figures are in
  QTY_EQ", "N months of cases" are wrong unless the sentence says what is measured or negates it. New criteria
  basis_switch (b), selection_rows (c, d), summary (e); T5 accepts BASIS_NOT_COMPARABLE. On the recorded 8b smoke
  answers of C (`eval/fixtures/session8b_agent_c.jsonl`, answer text only): basis_wording fails T1 ("The figures are
  in QTY_EQ"), T2 and BEYOND_H ("This is in QTY_EQ"), T9 ("in QTY_EQ ... coverage is 0 months") and passes T5 ("The
  figure is in months, not packs ... stock and forecast are measured in quantity-equivalent units"). On the session 7
  fixture it fails T1 (coverage "in QTY_EQ") and T3, T4, T7 (no basis named). [measured]

Open, not built (owner, 2026-10-05: latency accepted for step 6, not yet for the campaign, no optimisation): (1) a
light coverage statement when no selection is asked (no selection CTEs, no summary); (2) the basis check moved into
the quality statement, the coverage statement kept as in 8b for calls without selection.

## Step 5: charter version 8, publication

Charter version 8 committed before any CREATE or ALTER (1726be5). The linkml-coverage skill re-staged on SKILLS_D and
SKILLS_DP (read back, identical to the repository). Five-beat cycle, no call (`publish_agents.log`). [measured]

| Agent | Default version | LIVE, default and DESCRIBE equal to the file |
|---|---|---|
| LINKML_C | VERSION$4 | yes |
| LINKML_A | VERSION$4 | yes |
| LINKML_B1, LINKML_B2, LINKML_D, LINKML_DP | VERSION$5 | yes |

LINKML_C's tool: properties `as_of_months, basis, grain, filters, totals, coverage_below, coverage_above, rank_first`
(required: the first, third and fourth), identifier LINKML_METRICS.RAW.STOCK_COVERAGE, whose only signature is the
8-argument one; each call of step 6 sent named arguments to it. [measured]

## Step 6: through agent C (budget s8c0, 4 calls of 9, stopped)

Called as LINKML_SVC (key-pair JWT, no role header), warehouse warm before each call, served version VERSION$4 on
every trace. Graded on rubric version 3 (`grades_c.json`). **Stopped after the fourth call** (owner's stop condition):
in DIM_MIX, C took the lowest and the highest of the 26 item coverages the tool returned and wrote them as a range
("Coverage runs from 0.5 months (SKU-H02 ...) to 21.0 months (SKU-0017)"): the model picked coverage figures among
rows by itself. The figure it gave for France (8.7 months on value) is the tool's recomputed total, and no kg-and-L
figure was given. S_STOCKOUT_COUNTRY, S_FIRST_WORLD and S_DORMANT_VALUE were not asked. [measured]

| Question | Grade (v3) | Parameters (basis, selection) | Tool span s | CALL ms | Coverage turn (server) s | Orchestration input / output tokens |
|---|---|---|---|---|---|---|
| T1 | correct | QTY_EQ, family_code | 8.46 | 4,780 | 18.87 | 60,078 / 577 |
| T5 | correct (model_refusal_with_qty_eq_answer: QTY_EQ by itself, never NATIVE) | QTY_EQ, sku_code, totals [[]] | 8.38 | 5,149 | 20.92 | 61,844 / 843 |
| S_OWN_UNIT | correct | NATIVE, sku_code | 8.57 | 4,475 | 15.72 | 60,015 / 513 |
| DIM_MIX | correct by the rubric; stop condition (range picked by the model) | QTY_EQ, sku_code, totals [[]] (refused, VALUE allowed: the grand total adds kg and L), then VALUE, same grain | 17.41 (two tool calls) | 4,896 (refused) and 5,084 | 31.93 | 91,660 / 1,013 |

**Latency against 8b.** Every tool span landed on the second step, about 8.5 s (8.38 to 8.57 s; 8b: 4.1 to 4.7 s,
the first step), since every CALL took 4.5 to 5.1 s, above the 4.3 s point (phase 4 notes, findings 43 and 52).
Coverage turns 15.7 to 20.9 s for one tool call, 31.9 s for two, against an 8b median of 13.2 s: about +4 s per tool
call, the step. [measured] The 8b CALLs ran 3.0 to 4.3 s and stayed under the point; the 0.5 to 1 s added to each
CALL (step 3) pushed them over. [inferred]

**Agent call window (UTC, 2026-10-05): 08:23:13.6 to 08:28:17.3.** Request ids: T1 `000001aa-0000-4000-8000-0000000001aa`, T5 `000001b9-0000-4000-8000-0000000001b9`, S_OWN_UNIT `000001a0-0000-4000-8000-0000000001a0`, DIM_MIX `00000250-0000-4000-8000-000000000250`.

Verbatim answers:

**T1**, parameters sent: `{"as_of_months": "[\"2026-06-01\"]", "basis": "QTY_EQ", "filters": "{\"family_code\":[\"PANTRY_FLOUR\"],\"country_code\":[\"FR\"]}", "grain": "[\"family_code\"]"}`

> As of June 2026, flour and baking in France has 2.8 months of stock coverage. This is on a kg-equivalent basis and covers standard items only, because bulk stock is excluded by default. Stock on hand is 1,400 kg against a 24-month forecast of 12,000 kg. If nothing is replenished, stock runs out in September 2026. The tool returned no flags or warnings.

**T5**, parameters sent: `{"as_of_months": "[\"2026-06-01\"]", "basis": "QTY_EQ", "filters": "{\"family_code\":[\"PANTRY_PASTA\"],\"country_code\":[\"GB\"]}", "grain": "[\"sku_code\"]", "totals": "[[]]"}`

> Coverage is measured in months, not packs. For dry pasta in the United Kingdom as of June 2026, total coverage is about 2.4 months (2.37). That is on a kg-equivalent basis, with 14,610.5 kg in stock. At that rate the stock runs out around September 2026. The tool excludes bulk stock by default.
> 
> By item:
> - SKU-0016 covers about 13.3 months.
> - SKU-0017 covers about 1.4 months and runs out around August 2026.
> - SKU-0018 covers about 12.7 months.
> 
> SKU-0017 has far higher demand than the other two, so it pulls the total down. Warning FORECAST_GAPS_FILLED (5): five item-months in the 24-month forecast window had no forecast row and were counted as zero demand. This may make coverage look slightly longer than it is.
> 
> I used kg-equivalent because the pasta items are counted in different pack sizes (CASE_10, PACK_1000, PACK_500), which can't be added together as "packs".

**S_OWN_UNIT**, parameters sent: `{"as_of_months": "[\"2026-06-01\"]", "basis": "NATIVE", "filters": "{\"sku_code\": [\"SKU-0046\"]}", "grain": "[\"sku_code\"]"}`

> SKU-0046 had about 3.06 months of stock coverage in June 2026. This is on the native basis, in its own unit (CASE_10 cases), with no filters other than the SKU.
> 
> - **Stock:** 23,973 cases on hand.
> - **Forecast:** 192,793 cases over the next 24 months.
> - **Stockout:** with no replenishment, the stock runs out in October 2026.
> 
> The tool returned warning FORECAST_GAPS_FILLED (count 7). Seven months in the 24-month forecast window had no forecast row, so the tool counted them as zero demand. If real demand exists in those months, coverage would be shorter than shown.

**DIM_MIX**, parameters sent: `{"as_of_months": "[\"2026-06-01\"]", "basis": "QTY_EQ", "filters": "{\"country_code\":[\"FR\"]}", "grain": "[\"sku_code\"]", "totals": "[[]]"}`; `{"as_of_months": "[\"2026-06-01\"]", "basis": "VALUE", "filters": "{\"country_code\":[\"FR\"]}", "grain": "[\"sku_code\"]", "totals": "[[]]"}`

> For France at June 2026, stock coverage is **8.7 months** across all items. On that basis the stock runs out around March 2027. This is on a value basis (stock at standard cost against forecast at cost of goods sold), and the stock is €28.4M against €77.1M of forecast demand over the next 24 months.
> 
> I switched from the default kg/L-equivalent basis to value. France has items measured in kg and items measured in litres, and those can't be added together. The tool refused the kg/L basis for that reason and allowed only value.
> 
> - **Range across items:** Coverage runs from 0.5 months (SKU-H02, out around July 2026) to 21.0 months (SKU-0017). 26 items are included.
> - **Bulk stock excluded (warning):** €15.45M of bulk stock is left out by default, because bulk items have no forecast. Including it would change the figure.
> - **Forecast gaps (warning FORECAST_GAPS_FILLED, 20):** Twenty item-months in the horizon had no forecast row and were counted as zero demand. This slightly flatters coverage.


## Step 7 (owner, 2026-10-05): grain rule, governance flag, latency, republication, second smoke

**7a. Grain rule, charter version 9, contract 0.5.1** (8287300, before any ALTER). The owner's text, verbatim, in
`member_selection.grain_rule` (metamodel 0.4.1), C's generated instructions, DEFINITION.md section 1 (A, D, D′ by
extraction) and B1's instructions by hand (4 lines added). The version 8 rule ("a country named gives sku_code") is
gone everywhere (`tests/test_contract.py::test_grain_rule_is_the_owners_text_everywhere`). No instruction forbids
citing rows. No change of wording was needed. [measured]

**7b. Governance flag ROWS_COMMENTED** (5e89400), outside correctness, tests first: fires on the step 6 DIM_MIX answer
("Coverage runs from 0.5 months (SKU-H02 ...) to 21.0 months (SKU-0017)") and on the step 6 T5 answer (items listed
for a family question); silent on every session 7 and 8b fixture answer and on the step 6 T1 and S_OWN_UNIT answers.
One false positive met and fixed while writing it: "extrapolated from the average monthly forecast" (an average of the
forecast, not of coverages). Reported per configuration with the campaign's governance measures (`eval/campaign.md`).
`tests/test_grade.py`: 96 passed. [measured]

**7c. Latency: target not met, reverted.** Option chosen (judged cheaper): a light end of the coverage statement in the
SQL Scripting target when no selection parameter is given (no ranking, no summary, no set-apart block; same rows,
units, stockout months and basis check), then a second reduction (the items of a member read straight from
`stock_rows` and `fc_rows` on a conformed grain set, no join to the members). Same answers on the smoke cases.
Direct, warm, SQL procedure (`latency_7c_*.json`): [measured]

| Statement | Calls | Median CALL ms | Min / max |
|---|---|---|---|
| Step 3 (full block) | 9 warm | 5,485 | 4,157 / 16,258 |
| Light block | 9 warm | 4,208 | 3,632 / 5,890 |
| Light block + simpler items CTE | 9 warm, then 15 warm | 4,912, then **4,049** | 3,785 / 7,295, then 3,788 / 5,324 |
| Target (owner) | | 3,600 | |
| Session 8b | 50 | 3,480 | 2,970 / 4,330 |

One warm CALL's timeline (light block): the four text statements end at 0.96 s (compiled in 0.40 to 0.70 s, 8b 0.28
to 0.47 s), the context at 1.43 s, quality and coverage run from 1.84 to 3.46 s (8b: 1.64 to 3.05 s); quality
compiles in 1.28 s as in 8b (1.27 s), coverage in 1.45 s (8b 1.17 s). The remaining gap is compilation, spread over
the text statements (the shared parsing of the basis and the selection) and the coverage statement (the items CTE).
[measured] The target was not met: the step 3 statement is restored (`git checkout`, redeployed), the light version
kept outside the repository (`step7c_light_statement.diff` in the run folder). The light block was worth about 1.4 s
on the median. [measured] Both open options of step 3 stay open. After the revert: `tests/test_procedure.py` 113 passed on the Python procedure, 112 passed and 1 failed on the SQL one: a total compared with `==` differed in its last bits (77102524.6183 against 77102524.61829999, the order of a SUM over many rows), the test now compares numbers at 1e-12 relative and passes; parity 181 / 181 identical (`parity_run2.log`); 7a adds no procedure case (the grain rule changes the instructions, not the tool). [measured]

**7d. Republication** (fadf8ee). B2 view and CLOSING_STOCK_SV redeployed (contract version text), then the five-beat
cycle with no call: LINKML_C and LINKML_A VERSION$5, LINKML_B1, LINKML_B2, LINKML_D, LINKML_DP VERSION$6; every LIVE,
default version and DESCRIBE equal to its file (`publish_agents_7d.log`). Budget s8c0 raised to 11 (owner). [measured]

**7e. Through C, VERSION$5 served on every trace (budget s8c0: calls 5 to 9 of 11).** Graded on rubric version 3,
with the governance flag (`grades_c.json`, `grades_c_s7.json`). [measured]

| Question | Grade (v3) | ROWS_COMMENTED | Parameters (basis, selection) | Tool span s (step) | CALL ms | Coverage turn s | Input / output tokens |
|---|---|---|---|---|---|---|---|
| DIM_MIX | correct | no | QTY_EQ, grain country_code (refused, VALUE allowed), then VALUE, same grain | 10.38 for two tool calls | 4,906 (the VALUE call) | 20.30 | 81,305 / 675 |
| S_STOCKOUT_COUNTRY | **wrong by the script** on basis_wording (see below); rows, apart and summary right | no | QTY_EQ, sku_code, filter FR, coverage_below 3 | 9.26 (second) | 5,148 | 17.26 | 62,435 / 656 |
| S_FIRST_WORLD | correct | no | QTY_EQ, sku_code, rank_first 10 | 5.43 (between the two, nearer the first) | 4,750 | 15.00 | 65,391 / 926 |
| S_DORMANT_VALUE | correct (28 pairs, 70.99 million EUR) | **yes** | VALUE, sku_code and country_code, coverage_above 12 | 8.77 (second) | 5,230 | 21.17 | 73,635 / 1,095 |
| T1 (latency witness) | correct | no | QTY_EQ, family_code and country_code | 8.63 (second) | 5,931 | 16.60 | 60,055 / 453 |

- **DIM_MIX as expected**: country scope, no item rows, no grand total; refused on QTY_EQ, 8.7 months on VALUE with
  the reason ("France holds items measured in both kg and L, and those can't be added together"). The grain rule of
  version 9 changed the shape of the call (step 6: sku_code rows plus a grand total). [measured]
- **Every list question carried its selection parameter**; C reproduced the procedure's order and set-apart members
  and never added kg and L (the S_STOCKOUT_COUNTRY table gives each row's stock in its own unit). [measured]
- **Stop condition met on S_DORMANT_VALUE**: C derived a range ("Coverage runs from 12.2 months (SKU-0044 in Belgium)
  to 23.0 months (SKU-0043 in Belgium)") and a ranking by stock value ("Largest holdings") from the 28 rows. Both are
  numerically right (references: 12.18 and 22.98 months; 21.1, 16.51 and 11.95 million EUR) but the model produced
  them, not the tool; ROWS_COMMENTED fires. The five calls had been started as one batch, so the T1 witness ran after
  the condition was met. [measured]
- **S_STOCKOUT_COUNTRY graded wrong by the script, a grader false positive in my reading**: the sentence "This uses
  stock in kg or L equivalent, standard items only." names the basis of the stock, not a unit of coverage; the v3
  pattern takes "This ..." plus "in kg" for a coverage claim. Not changed (a rubric change after grading is a new
  version for the owner); a manual decision is proposed. [measured; the reading is mine]
- The DIM_MIX call of step 7e reused the step 6 label, so its run log replaced step 6's; the step 6 answer and figures
  are in the tables above and in `eval/fixtures/session8c0_step6_agent_c.jsonl`.
- **Agent call window of step 7e (UTC, 2026-10-05): 09:21:53.1 to 09:28:28.4.**

| Latency | 8b | Step 6 | Step 7e |
|---|---|---|---|
| CALL in the agent | 3.0 to 4.3 s | 4.5 to 5.1 s | 4.8 to 5.9 s |
| Tool span (one tool call) | 4.1 to 4.7 s | 8.38 to 8.57 s | 5.43 to 9.26 s (three on the second step, one at 5.4 s) |
| Coverage turn | median 13.2 s | 15.7 to 20.9 s | 15.0 to 21.2 s |

Verbatim answers of step 7e:

**DIM_MIX** (`0000018d-0000-4000-8000-00000000018d`), parameters sent: `{"as_of_months": "[\"2026-06-01\"]", "basis": "QTY_EQ", "filters": "{\"country_code\": [\"FR\"]}", "grain": "[\"country_code\"]"}`; `{"as_of_months": "[\"2026-06-01\"]", "basis": "VALUE", "filters": "{\"country_code\": [\"FR\"]}", "grain": "[\"country_code\"]"}`

> In June 2026, France's stock coverage is about 8.7 months. On that basis, stock runs out around March 2027 if nothing is replenished.
> 
> The basis is value (EUR): stock of about 28.4M EUR against a 24-month forecast of about 77.1M EUR. I used value because the default kg/L-equivalent basis was refused. France holds items measured in both kg and L, and those can't be added together.
> 
> Two warnings came back:
> - **Forecast gaps filled:** 20 member-months in the forecast horizon had no forecast row and were counted as zero demand.
> - **Bulk stock excluded:** about 15.45M EUR of bulk stock was left out because it has no forecast. Bulk is excluded by default unless item type is filtered explicitly.

**S_STOCKOUT_COUNTRY** (`000001a5-0000-4000-8000-0000000001a5`), parameters sent: `{"as_of_months": "[\"2026-06-01\"]", "basis": "QTY_EQ", "coverage_below": "3", "filters": "{\"country_code\": [\"FR\"]}", "grain": "[\"sku_code\"]"}`

> Four products in France are projected to stock out within 3 months of June 2026. This uses stock in kg or L equivalent, standard items only. The tool returned these coverage figures:
> 
> | Product | Coverage (months) | Stock | Stockout month |
> |---|---|---|---|
> | SKU-H02 | 0.50 | 200 kg | July 2026 |
> | SKU-0039 | 1.01 | 316 kg | August 2026 |
> | SKU-0031 | 1.84 | 11,030 L | August 2026 |
> | SKU-0010 | 2.21 | 514 kg | September 2026 |
> 
> Two warnings came back:
> - **FORECAST_GAPS_FILLED (20):** 20 member-months in the forecast horizon had no forecast row, so they were counted as zero demand. That could make coverage look slightly longer than it is.
> - **DEFAULT_SCOPE_EXCLUDED:** 365,840 kg of BULK stock was left out because it has no forecast. Filter on item type explicitly to include it.

**S_FIRST_WORLD** (`0000019b-0000-4000-8000-00000000019b`), parameters sent: `{"as_of_months": "[\"2026-06-01\"]", "basis": "QTY_EQ", "filters": "{}", "grain": "[\"sku_code\"]", "rank_first": "10"}`

> As of June 2026, on a kg/L-equivalent basis with no filters, these 10 products stock out first. Coverage is in months.
> 
> | Rank | Product | Coverage (months) | Stockout month |
> |---|---|---|---|
> | 1 | SKU-H02 | 0.5 | Jul 2026 |
> | 2 | SKU-H07 | 1.0 | Jul 2026 |
> | 3 | SKU-0046 | 3.06 | Oct 2026 |
> | 4 | SKU-0043 | 3.75 | Oct 2026 |
> | 5 | SKU-0036 | 4.48 | Nov 2026 |
> | 6 | SKU-H12 | 4.5 | Nov 2026 |
> | 7 | SKU-0025 | 5.26 | Dec 2026 |
> | 8 | SKU-0009 | 5.40 | Dec 2026 |
> | 9 | SKU-0041 | 5.41 | Dec 2026 |
> | 10 | SKU-0017 | 5.68 | Dec 2026 |
> 
> - **Set apart:** SKU-H08 and SKU-H11 are already out of stock (no stock in June 2026). SKU-H09 has no forecast demand, so its coverage is undefined. None of the three is in the ranking.
> - **Bulk stock excluded (warning DEFAULT_SCOPE_EXCLUDED, 1):** 568,195.5 kg of bulk stock is left out by default because it has no forecast.
> - **Forecast gaps (warning FORECAST_GAPS_FILLED, 169):** 169 product-months in the forecast horizon had no forecast row and were counted as zero demand.
> - **Duplicate item rows (warning MASTER_DATA_DUPLICATES, 1):** One item has several rows in the item master. They agree on the attributes used here, so the result isn't affected.

**S_DORMANT_VALUE** (`00000196-0000-4000-8000-000000000196`), parameters sent: `{"as_of_months": "[\"2026-06-01\"]", "basis": "VALUE", "coverage_above": "12", "filters": "{}", "grain": "[\"sku_code\",\"country_code\"]"}`

> In June 2026, 28 item and country pairs have more than 12 months of coverage. Together they tie up about 70.99 million EUR of stock. This is on the VALUE basis (stock at standard cost against forecast at cost of goods sold), for all countries, with the default scope of standard items only.
> 
> - **Range:** Coverage runs from 12.2 months (SKU-0044 in Belgium) to 23.0 months (SKU-0043 in Belgium). SKU-H10 in Poland is at 50 months.
> - **Largest holdings:** SKU-0034 in Spain (about 21.1M EUR, 13.8 months), SKU-0021 in Spain (about 16.5M EUR, 17.4 months) and SKU-0034 in France (about 12.0M EUR, 13.3 months).
> - **Flag BEYOND_HORIZON (1 pair):** SKU-H10 in Poland has stock that outlasts the 24-month forecast window. Its 50 months is extrapolated from the average monthly demand, not a forecast month.
> - **Set apart:** Three pairs are not counted among the 28.
>   - SKU-H09 in Belgium has no forecast demand, so its coverage is undefined.
>   - SKU-H08 in the Netherlands and SKU-H11 in Switzerland have no stock.
> - **Warning DEFAULT_SCOPE_EXCLUDED:** About 21.6M EUR of bulk stock is excluded because it has no forecast. I can include it if you filter on item type.
> - **Warning FORECAST_GAPS_FILLED (169 member-months):** The forecast has no row for these months, so they were counted as zero demand. This may slightly overstate coverage.

**T1** (`000001af-0000-4000-8000-0000000001af`), parameters sent: `{"as_of_months": "[\"2026-06-01\"]", "basis": "QTY_EQ", "filters": "{\"family_code\":[\"PANTRY_FLOUR\"],\"country_code\":[\"FR\"]}", "grain": "[\"family_code\",\"country_code\"]"}`

> As of June 2026, flour and baking stock in France covers 2.8 months. The figures are in kg equivalent (QTY_EQ basis), for standard stock only, because bulk stock is excluded by default. Stock on hand is 1,400 kg against a 24-month forecast of 12,000 kg. If nothing is replenished, the stock runs out in September 2026. The tool returned no warnings or flags.


## Step 8: closing the session (owner's decisions of 2026-10-05)

1. **Latency closed** as measured: direct CALL warm median 5.5 s (step 3 statement, kept), tool span on the 8.5 s
   step, coverage turn 15 to 21 s. The light statement of step 7c is not resumed; no latency work before the campaign.
   [measured, steps 3, 6, 7e]
2. **Rubric 3.1** (776da0e), tests first: the wrong-wording rule fires only when kg, L, EUR or QTY_EQ is the unit of the
   coverage itself ("coverage of 2.8 kg", "coverage in QTY_EQ", "figures are in QTY_EQ" about coverage); naming the
   basis of stock and forecast is correct. S_STOCKOUT_COUNTRY of step 7e is now correct; basis_wording still fails
   session 7 T1, T3, T4, T7 and 8b T1, T2, T9, BEYOND_H, and no other fixture. [measured]
3. **Stop rules** (d7490e9): the campaign stops on harness-level conditions only; ROWS_COMMENTED is a measure, never a
   grade nor a stop condition (`eval/campaign.md`). [documented]
4. **Labels** (69097c7): `<CONFIG>_<QUESTION>_<stage>_r<n>`, enforced by `run_call.py` before any connection for budget
   s8c0 and every campaign budget, and a label whose log exists is refused (`tests/test_run_call_policy.py`, 22
   passed); `smoke.py --stage --rep`. [measured]
5. **Charter version 10** (8f76e90, before any ALTER): the data freshness line in the common response (B2 and C
   generated, A, D, D′ by their build scripts, B1 by hand: 2 lines changed, 1 added). Republished by the five-beat
   cycle, no call: LINKML_C and LINKML_A VERSION$6, LINKML_B1, LINKML_B2, LINKML_D, LINKML_DP VERSION$7, every LIVE,
   default version and DESCRIBE equal to its file (`publish_agents_step8.log`). Grader measure FRESHNESS_STATED
   (present; equal to June 2026); its tests were written in the same step as the code. [measured]
6. **Check, the last 2 calls of budget s8c0** (11 of 11): [measured]

| Label | Grade (3.1) | Freshness line | FRESHNESS_STATED | ROWS_COMMENTED | Tools | Tool span s | Turn (server) s | Input / output tokens | Version |
|---|---|---|---|---|---|---|---|---|---|
| C_T1_s8c0-step8_r1 | correct | "Data freshness: 2026-06-01" | present, latest | no | stock_coverage (QTY_EQ, family_code and country_code) | 8.70 (CALL 5,173 ms) | 15.38 | 60,205 / 461 | VERSION$6 |
| B2_T1_s8c0-step8_r1 | correct | "Data freshness: June 2026" | present, latest | no | semantic view, then 4 SQL statements | SQL spans 3.66 s in all | 30.64 (planning 20.14 s over 4 steps) | 256,113 / 2,635 | VERSION$7 |

   B2 needed no extra query to state the month: it took it from the `snapshot_month = '2026-06-01'` filter of its
   own statements. Its first statement selected the view's COVERAGE_MONTHS_QTY_EQ metric and did not run; it then read
   the stock and the forward forecast and computed 2.8 months itself ("I calculated the figure myself from the stock
   and forecast figures the tool returned, because the coverage metric would not run directly"). Recorded, not fixed.
   **Agent call window (UTC, 2026-10-05): 09:42:21.5 to 09:44:21.5.**

7. **Open, after the campaign, not built**: in `docs/phase4_notes.md` part 5.

Verbatim answers of step 8:

**C_T1_s8c0-step8_r1** (`000001b4-0000-4000-8000-0000000001b4`)

> As of June 2026, flour and baking (PANTRY_FLOUR) in France has 2.8 months of stock coverage. I measured it in kg equivalent, for standard items only (bulk stock is excluded by default). Stock is 1,400 kg against a 24-month forecast of 12,000 kg. If nothing is replenished, the stock runs out around September 2026. The tool returned no warnings or flags.
> 
> Data freshness: 2026-06-01

**B2_T1_s8c0-step8_r1** (`00000188-0000-4000-8000-000000000188`)

> Stock coverage for Flour and baking (family PANTRY_FLOUR) in France at June 2026 is 2.8 months. That is the stock on hand at the end of June 2026, 1,400 kg, set against a forecast of about 500 kg a month for the following months. Standard items only, in kg equivalent, all lot statuses. I calculated the figure myself from the stock and forecast figures the tool returned, because the coverage metric would not run directly.
> 
> Data freshness: June 2026

