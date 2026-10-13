# Session 13: configuration C-raw, steps 1 and 2

> Owner, 2026-10-08. C-raw is the contract without any reshaped data: a semantic view on the raw tables,
> `STOCK_COVERAGE` unchanged, and a new generated procedure `CLOSING_STOCK` that applies the contract's closing rule at
> question time. Steps 1 (read only) and 2 (offline, nothing deployed). Snowflake reads as `LINKML_METRICS_ROLE`, no
> secondary role (the caller read back by the script). Run log:
> `~/work/assets/linkml-metrics-runs/s13/volume.json`. Tags: [measured], [documented], [inferred].

## 1a. Wiring: what each tool reads

| Configuration | Tool | Physical objects | Raw or generated |
|---|---|---|---|
| A | `AP_LINKLM` (Autopilot) | the 7 RAW tables | raw |
| B1 | `LINKML_B1_SV` (hand-written) | the 7 RAW tables | raw |
| B2 | `LINKML_B2_SV` | `B2_ITEM`, `B2_STATUS`, `B2_FORECAST_SPINE` (views, `compiler/gen_native_sv.py`), `FCT_STOCK_SNAPSHOT_GAPFILLED` (view, `compiler/gen_closing_sv.py`); `DIM_GEO`, `DIM_CALENDAR`, `DIM_BATCH`, `DIM_WAREHOUSE`, `FCT_FORECAST` | 4 generated views over RAW, 5 raw tables |
| C | `LINKML_B2_SV` | as B2 | as B2 |
| C | `STOCK_COVERAGE` | `FCT_STOCK_SNAPSHOT`, `FCT_FORECAST`, `DIM_ITEM`, `DIM_GEO`, `DIM_BATCH`, `DIM_WAREHOUSE`, `DIM_CALENDAR` | raw (`compiler/gen_procedure.py`) |
| D | `LINKML_B2_SV`; `code_execution` | as B2; the sandbox reads no table (probe D) | as B2 |
| D′ | `LINKML_B2_SV`; `code_toolset_all` | as B2; the script runs the SQL the agent writes, its tables recorded per turn | as B2; raw or generated per turn |
| C-raw | `LINKML_C_RAW_SV` | the 7 RAW tables | raw (`compiler/gen_craw.py`) |
| C-raw | `STOCK_COVERAGE` | as C | raw |
| C-raw | `CLOSING_STOCK` | `FCT_STOCK_SNAPSHOT`, `DIM_ITEM`, `DIM_GEO`, `DIM_BATCH`, `DIM_WAREHOUSE` | raw (`compiler/gen_closing_procedure.py`) |

- No statement of `STOCK_COVERAGE` reads `B2_FORECAST_SPINE` or `FCT_STOCK_SNAPSHOT_GAPFILLED`. Every table name in the
  generated SQL is a literal, and the dynamic SQL is assembled from those literals. The names found are
  `FCT_STOCK_SNAPSHOT` (9), `FCT_FORECAST` (6), `DIM_ITEM` (12), `DIM_GEO` (6), `DIM_BATCH` (4), `DIM_WAREHOUSE` (3) and
  `DIM_CALENDAR` (3). There is no `GAPFILLED`, `SPINE` or `B2_` [measured, `generated/stock_coverage_procedure_sql.sql`].
- A view tool reads only the logical tables that the model's SQL names. C's closing-stock turns read `__stock`, which is
  the gap-filled view. For example, C's CS_FAMILY of stage 1 filtered `snapshot_month = '2026-06-01'` on `__stock`
  [measured, `summary_c_cs_family_campaign_s1_r1.json`].
- So C's score mixes both mechanisms. Its coverage turns go through the procedure, which reads raw tables. Its
  closing-stock and general turns go through B2's view, which reads generated objects (section 1c).

## 1b. Volume

Row counts. `bytes` is the stored size from `INFORMATION_SCHEMA.TABLES`; a view stores nothing. "Scan" is the bytes
that a full `COUNT` of the object scanned [measured].

| Object | Type | Rows | Shape | Stored bytes | Scan of a full read |
|---|---|---|---|---|---|
| `FCT_STOCK_SNAPSHOT` | table | 60,915 | 4,194 keys (lot x warehouse), 36 months, 228 item x country pairs | 832,512 | 832,512 |
| `FCT_STOCK_SNAPSHOT_GAPFILLED` | view | 63,428 | the same 4,194 keys and 36 months; 2,513 filled rows (+4.1 percent) | 0 | 1,666,560 |
| `FCT_FORECAST` | table | 15,306 | 219 item x country pairs, 72 months | 170,496 | 170,496 |
| `B2_FORECAST_SPINE` | view | 23,652 | 36 analysis months x 219 pairs x 3 statuses, 48 measure columns per row | 0 | 1,055,744 |

Bytes scanned per question, with the result cache off [measured, `QUERY_HISTORY_BY_SESSION` of the script's own
queries]:

| Question | Path | Statements | Bytes scanned | Elapsed ms | Result |
|---|---|---|---|---|---|
| Closing stock, SNACK_BARS x CH, Q2 2026 (CS_FAMILY) | B2 and C: C's campaign SQL on the gap-filled view | 1 | 1,672,192 | 840 | 450 |
| same | B2 and C: `SEMANTIC_VIEW(LINKML_B2_SV ... closing_stock_qty_eq)`, quarter 2026-Q2 | 1 | 1,673,728 | 792 | 450 |
| same | raw: the same SQL on `FCT_STOCK_SNAPSHOT` | 1 | 838,144 | 240 | 450 |
| same | raw: the closing rule (period members, last month only) | 1 | 838,144 | 186 | SKU-H11 0, SKU-H12 450, total 450 |
| Coverage, PANTRY_FLOUR x FR, June 2026 (T1) | B2: `SEMANTIC_VIEW(... coverage_months_qty_eq)` | 1 | 2,732,544 | 3,281 | 2.8 |
| same | C and C-raw: `CALL STOCK_COVERAGE` (context, quality, coverage) | 3 | 7,752,192 (899,072; 1,018,368; 5,834,752) | 945; 2,551; 2,118 | 2.8 |

- A closing-stock question on the gap-filled view scans 2.0 times the snapshot table whatever period it asks
  [measured]. The view's key spans and its `LAST_VALUE` window run over every month of each key before the month filter
  applies, so the filter cannot prune [inferred, from the view's SQL].
- On a coverage question the procedure scans 2.8 times more than B2's view (7.75 MB against 2.73 MB). Its context and
  in-call quality checks read whole dimension tables and the forecast window [measured bytes; cause inferred]. At this
  scale C-raw does not scan less than B2 for coverage. Its gain is the absence of stored or densified objects, not fewer
  bytes per coverage question.

How each object grows [inferred: formulas from the generated SQL, not a client's size]:

- **Snapshot.** `R_s = sum over keys k of n_k`. A key is a lot x warehouse here, an item x store at retail. `n_k` is the
  number of periods in which key k has a row.
- **Gap-filled view.** `R_g = sum over keys k of (min(last_k + 1, LATEST) - first_k + 1)`. That is `R_s`, plus the
  interior gaps, plus one trailing row for each key that ends before LATEST. It is bounded by `K x T` (K keys, T
  periods).
  - It grows with each key's span, not with the rows the key holds.
  - It is computed by every query, over the whole table, whatever period the query asks.
  - At a daily grain T counts days.
- **Forward spine.** `R_sp = A x P x S` rows, and `A x P x S x H x B` measure cells:
  - A: analysis periods.
  - P: item x location pairs with a forecast in the window.
  - S: values of the bridged stock-only attribute.
  - H: horizon periods.
  - B: bases.

  Here the spine has 36 x 219 x 3 x 24 x 2 = 1,135,296 cells, against 15,306 x 3 = 45,918 measure cells in the
  forecast table (24.7 times). The same calendar span and horizon at a daily grain multiply both A and H by about 30,
  so the cells grow about 900 times for the same P, S and B.
- **Raw closing at question time.** `CLOSING_STOCK` reads the snapshot rows of the period's months only, with the period
  bounds in the join, and builds no densified row. Its cost follows `R_s` over the period asked.

## 1c. Recount by mechanism (offline, from the recorded grades; nothing regraded)

- **Rule and classes:** `eval/mechanism_classes.yaml`. The script is `eval/mechanism_recount.py` and the test
  `tests/test_mechanism_classes.py`.
- **REFUSAL** is used where the rubric's refusal criterion applies: T5, T6 and T7_R1.
- **Every other question** takes its class from its metric:
  - stock_coverage: COVERAGE;
  - closing_stock and stock_on_hand: CLOSING_STOCK;
  - demand_forecast: GENERAL.
- **Judgement calls:**
  - T6 is REFUSAL, because a clarification is expected.
  - DIM_MIX is COVERAGE, because it is graded on basis_switch.
  - N1 and N2 are CLOSING_STOCK. They use both mechanisms, and closing stock is the half that C-raw changes.
- **Gap-fill dependent for a view-based answer** [documented, `data/traps.yaml`]:
  - T9: 3.5 instead of 0;
  - CS_LAST_MONTH_GAP: 350 instead of 0;
  - CS_FAMILY: 800 instead of 450;
  - N1: 350 and 3.5;
  - N2: May 850 and June 800, coverage 4.0.

Correct / wrong per class (no manual verdict remains). Score of record 3.2, with 3.3 and figure-only beside it
[measured]:

| Stage | Configuration | Rubric | COVERAGE | CLOSING_STOCK | GENERAL | REFUSAL | Total |
|---|---|---|---|---|---|---|---|
| 1 | A | 3.2 / 3.3 / figure-only | 9-7 / 11-5 / 12-4 | 4-0 | 1-0 | 2-1 | 16-8 / 18-6 / 19-5 |
| 1 | B1 | 3.2 / 3.3 / figure-only | 6-10 / 9-7 / 12-4 | 4-0 | 1-0 | 2-1 | 13-11 / 16-8 / 19-5 |
| 1 | B2 | 3.2 / 3.3 / figure-only | 8-8 / 11-5 / 12-4 | 4-0 | 1-0 | 2-1 | 15-9 / 18-6 / 19-5 |
| 1 | C | all three | 16-0 | 4-0 | 1-0 | 3-0 | 24-0 |
| 1 | D | 3.2 / 3.3 / figure-only | 10-6 / 11-5 / 13-3 | 4-0 | 1-0 | 2-1 | 17-7 / 18-6 / 20-4 |
| 1 | D′ | 3.2 / 3.3 / figure-only | 7-9 / 10-6 / 11-5 | 4-0 | 1-0 | 3-0 | 15-9 / 18-6 / 19-5 |
| 2 | B2 | 3.2 / 3.3 / figure-only | 11-8 / 13-6 / 15-4 | 7-1 / 7-1 / 8-0 | 1-0 | 1-1 | 20-10 / 22-8 / 25-5 |
| 2 | C | 3.2 / 3.3 / figure-only | 16-3 / 17-2 / 18-1 | 8-0 | 1-0 | 2-0 | 27-3 / 28-2 / 29-1 |
| 1 | every configuration | also COVERAGE (N1, N2) | none asked in stage 1 | | | | |
| 2 | B2 | also COVERAGE (N1, N2, counted above under CLOSING_STOCK), 3.2 / 3.3 / figure-only | 3-1 / 3-1 / 4-0 | | | | |
| 2 | C | also COVERAGE (N1, N2, counted above under CLOSING_STOCK), all three | 4-0 | | | | |

- **Check:** the classes sum to each total, and the totals equal the published ones in all 16 configuration x score
  tables. The published sources are `snowflake/phase5_campaign/stage1_results.md` section 12 and `stage2_results.md`
  section 8. The fixtures `eval/fixtures/grades_campaign-s*.json` hold the same verdicts as the files of record
  [measured].
- **Outside COVERAGE and REFUSAL**, the only wrong answer is B2's N2 in stage 2, repetition 1 (correct on figure only).
  Every CLOSING_STOCK and GENERAL turn of C is correct in both stages (4 of 4, then 8 of 8) [measured].
- **C's tools per turn** (run summaries; one use of the view is two tool uses, context then SQL) [measured]:
  - Every COVERAGE turn and T5 and T7_R1 called `stock_coverage`, twice on DIM_MIX and H_LOCAL_STOCKOUT.
  - T6 called no tool.
  - CS_LAST_MONTH_GAP, CS_MIDDLE_MONTH_GAP, CS_FAMILY, G1 and G2 used only the view.
  - N1 and N2 used the procedure once and the view once.
  - Coverage turns with no procedure call: none.

## 2. C-raw built offline (nothing deployed)

- **`CLOSING_STOCK`** (`generated/closing_stock_procedure.sql`, 396 lines, from `compiler/gen_closing_procedure.py`).
  - SQL Scripting, `EXECUTE AS CALLER`, five VARCHAR parameters: `PERIODS`, `GRAIN`, `FILTERS`, `BASIS` (default
    `QTY_EQ`) and `TOTALS` (default `[]`).
  - **Three statements**, each SQL with bound values; no SQL text is built at call time:
    1. the parameters and the caller (no table read);
    2. the context: the snapshot months and the period checks, plus the table-scope quality expectations on
       `DIM_GEO`, `DIM_BATCH`, `DIM_WAREHOUSE` and `DIM_ITEM`;
    3. the closing rows, from `FCT_STOCK_SNAPSHOT` and the four dimensions, with the item fan-out check and the
       referential warnings.
  - **Lineage:** the query ids of statements 2 and 3.
  - **Refusals:** the contract's codes, in check order. A period with any month that has no snapshot is refused with
    `AS_OF_NO_SNAPSHOT` (for example 2026, 2023 and 2026-Q3).
  - **Reworded templates:** 8 of the contract's templates name coverage or `as_of_months`, and they are reworded for
    closing stock. The generator holds each contract text and stops if that text changes.
  - **Dry run before any CREATE** (`snowflake/session13_craw/dry_run.py`; owner, step 3): the three statements ran as plain
    read-only SELECTs with the values substituted, in the procedure's order and checks. The heroes came back exact
    (Q2 2026, SNACK_BARS x CH: SKU-H11 0 with `closed_without_snapshot` true, SKU-H12 450, the country total 450, the family
    450), and so did CS_LAST_MONTH_GAP (0). No generator change was needed [measured, `linkml-metrics-runs/s13/dry_run.json`].
  - **Limit:** 8 refusal texts of `CLOSING_STOCK` are written in the generator, not declared in the contract (owner, session 13 step 3: the contract stays 0.5.1).
  - **Not executed on the account yet.**
- **`LINKML_C_RAW_SV`** (`generated/c_raw_sv.yaml`).
  - The 7 RAW tables, joined fact to dimension. The raw `DIM_ITEM` is used, so its T7 duplicate is still there.
  - Stock on hand `NON ADDITIVE BY` the snapshot month, the forecast as a flow.
  - No view metric, no coverage or closing-stock metric, no verified query, no enrichment.
- **`LINKML_C_RAW`** (`generated/agent_c_raw.yaml`).
  - Three tools: the view, C's `stock_coverage` tool unchanged, and `closing_stock`.
  - Instructions: C's orchestration with one sentence replaced, plus one closing-stock rule. The response is the
    common one.

## 3. Created and checked (owner's go, 2026-10-08, 13:59 to 14:22 UTC)

As `perso`, `LINKML_METRICS_ROLE`, no secondary role; agent calls as LINKML_SVC. Logs in `linkml-metrics-runs/s13/`.

- **Created:** `CLOSING_STOCK` `0000032b-0000-4000-8000-00000000032b`; `LINKML_C_RAW_SV` (dry run `<query-id>`, create
  `<query-id>`); `LINKML_C_RAW` (CREATE `<query-id>`; MODIFY LIVE `<query-id>`, COMMIT `<query-id>`, ADD LIVE `<query-id>`, SET
  DEFAULT_VERSION = 'VERSION$2' `<query-id>`). No grant, no account-level change [measured].
- **Equal to the files:**
  - the procedure's DESCRIBE (body, signature, VARIANT, SQL, CALLER);
  - the view's YAML read back (27 members, the same `is_enum` and `sample_values`, no verified query);
  - every agent version and DESCRIBE.
- **Frozen objects unchanged** (`state.py frozen --compare`, before and after): the six agents' SHOW VERSIONS, both
  coverage procedures, the four generated views and the four semantic views [measured].
- **Direct CALLs: 103.** 58 for the live tests (two test fixes, below), 34 for parity and 11 for latency.
  - **Live tests:** 49 of 49 pass. Two tests were wrong and were fixed; the procedure was not changed.
    - QTY_EQ over PANTRY with a grand total is refused, BASIS_NOT_COMPARABLE, because flour (kg) and oil (L) mix. That
      is correct, so the totals test now uses VALUE.
    - The comparison had also picked up the grand-total row.
  - **Parity with the gap-filled view summed under the closing rule:** 14 complete periods (2023-Q3 to 2026-Q2, 2024,
    2025), 16 grains, 2 bases.
    - 20 CALLs answered, comparing 12,304 members with 0 differences.
    - 12 CALLs were refused as designed: 10 on QTY_EQ where a row adds kg and L, and 2 on `lifecycle_status`
      (MASTER_DATA_FANOUT, the T7 item).
    - 2023 and 2026 were refused (AS_OF_NO_SNAPSHOT, the months not loaded named).
    - No member exists only through a trailing filled row in these periods.
    - Every answered CALL warned MASTER_DATA_DUPLICATES (SKU-H06 is in scope) [measured].
  - **Latency** (the hero question, 10 warm CALLs): median 6.4 s inside the procedure (client 6.7 s). Compiling the
    three statements takes 5.2 s (parameters 1.5, context 0.4, closing 2.7); execution takes 0.86 s
    [measured, `QUERY_HISTORY_BY_USER`].
- **Smoke as LINKML_SVC** (budget `s13`; served `VERSION$2` on all four turns, read from the trace rows) [measured]:

| Question | Tool, from the trace | Answer | Input tokens | Seconds |
|---|---|---|---|---|
| CS_LAST_MONTH_GAP (fifth beat) | `closing_stock` (periods 2026-Q2, NATIVE) | 0, no snapshot in June | 68,097 | 18.9 |
| T1 | `stock_coverage` | 2.8 months | 68,149 | 18.5 |
| T9 | `stock_coverage` (NATIVE) | 0, NO_STOCK | 68,312 | 21.0 |
| G1 | `c_raw_semantic_view` | 6,416 L | 122,348 | 12.9 |

  No closing-stock question went to the view: H-CR-4 was not observed in the smoke.
- **Warehouse running time, step 3:** 1,435 s from the warehouse's query history, auto-suspend tails included (60 s
  suspend). That is 0.40 credits at XSMALL, or 0.54 at the 1.35 credits a running hour billed in the campaign.
  AI Credits for the smoke: 0.130 (tokens at `eval/guards.py` rates). The step 3 estimate is 1.8 to 2.4 USD; billed, 2.37
  USD (section 5).

## 4. The campaign arm (owner's go, 2026-10-08, 14:37 to 15:02 UTC)

`eval/campaign.py --arm CR`. C's blocks were played as they were: C's questions, C's order, C's seeds. Guard ceilings
were 3.7 USD for stage 1 and 5.23 USD for stage 2, so the pause would fall at 9 USD for steps 3 and 4 together, with
step 3 counted at 2.4. Neither stage paused.

- **Before the first call:** the tree was clean, and the model of LINKML_C_RAW's spec equals C's
  (`claude-sonnet-5-5`). The warm-up was served `claude-sonnet-5-5`, as all 56 of C's recorded calls were.
- **Calls and versions:** 25 + 31 calls, all HTTP 200. Every graded turn was served `VERSION$2` (24 + 30), read from its
  trace rows; no turn without a trace, no foreign row [measured].
- **Grades:** rubric 3.2 (record), 3.3 and figure-only, by class of step 1; C from the files of record, the same
  question and repetition [measured, `snowflake/session13_craw/compare.py`, `linkml-metrics-runs/s13/compare.json`;
  C-raw's grades, published since session 14: `eval/fixtures/grades_craw-s1.json`, `grades_craw-s2.json` (rubric 3.2)
  and `grades_craw-s1.rubric-3.3.json`, `grades_craw-s2.rubric-3.3.json`].

| Stage | Class | Turns | C 3.2 | C-raw 3.2 | C 3.3 | C-raw 3.3 | C fig. | C-raw fig. | Median s, C / C-raw | Median input tokens, C / C-raw |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | CLOSING_STOCK | 4 | 4-0 | 3-1 | 4-0 | 3-1 | 4-0 | 3-1 | 13.8 / 19.1 | 164,278 / 68,088 |
| 1 | COVERAGE | 16 | 16-0 | 14-2 | 16-0 | 15-1 | 16-0 | 15-1 | 17.0 / 19.2 | 61,822 / 68,483 |
| 1 | GENERAL | 1 | 1-0 | 1-0 | 1-0 | 1-0 | 1-0 | 1-0 | 11.6 / 12.7 | 163,780 / 122,338 |
| 1 | REFUSAL | 3 | 3-0 | 3-0 | 3-0 | 3-0 | 3-0 | 3-0 | 12.7 / 13.4 | 60,407 / 67,086 |
| 1 | total | 24 | 24-0 | 21-3 | 24-0 | 22-2 | 24-0 | 22-2 | | |
| 2 | CLOSING_STOCK | 8 | 8-0 | 8-0 | 8-0 | 8-0 | 8-0 | 8-0 | 17.4 / 18.7 | 164,112 / 71,153 |
| 2 | also COVERAGE (N1, N2, counted above) | 4 | 4-0 | 4-0 | | | | | | |
| 2 | COVERAGE | 19 | 16-3 | 15-4 | 17-2 | 17-2 | 18-1 | 18-1 | 17.8 / 18.7 | 63,468 / 70,562 |
| 2 | GENERAL | 1 | 1-0 | 1-0 | 1-0 | 1-0 | 1-0 | 1-0 | 13.2 / 12.8 | 163,813 / 122,324 |
| 2 | REFUSAL | 2 | 2-0 | 2-0 | 2-0 | 2-0 | 2-0 | 2-0 | 9.2 / 9.9 | 50,138 / 55,702 |
| 2 | total | 30 | 27-3 | 26-4 | 28-2 | 28-2 | 29-1 | 29-1 | | |

- **Closing stock, the mechanism under test.**
  - Every closing-stock turn of C-raw called `closing_stock`, and none used the view: H-CR-4 was not observed in 12
    turns.
  - The values of CS_LAST_MONTH_GAP, CS_MIDDLE_MONTH_GAP, CS_FAMILY, N1 and N2 are all right without the gap-filled
    snapshot. H-CR-1 is refuted as expected.
  - The one miss is G2 in stage 1. The figures are right (ES 48.5, ..., SE 14.5 million EUR, with no fan-out), but
    they sit in a markdown table whose header says "EUR M". The rubric reads a scale word next to each number, so no
    candidate matched [measured; the reading of the rubric, not regraded].
  - A C-raw closing-stock turn reads 68,000 to 71,000 input tokens, against C's 164,000 on the view (2.3 to 2.4 times
    fewer). It takes 1.3 to 5.3 s longer (median), which matches the procedure's compilation (finding 147) [measured;
    the link inferred].
- **Coverage (H-CR-2, same procedure and tool spec as C).**
  - Under 3.3 the two configurations are equal in stage 2 (17-2) and one apart in stage 1 (16-0 against 15-1).
  - Every coverage difference is in `basis_wording`; the figures agree, except C-raw's T3 and T9 r2, which are also
    wrong on figure only because no QTY_EQ was named. In detail:
    - **Basis named as NATIVE:** C-raw's stage 1 T3 and stage 2 T9 r2 named the basis as NATIVE (the item's packs), where
      the grader expects QTY_EQ named.
    - **Unit word:** NO_DEMAND (stage 1) and T8 r2 (stage 2) were read under 3.2 as giving a unit ("1 L", "1 kg" in a
      product name), which 3.3 corrects.
    - **QTY_EQ wording:** S_STOCKOUT_COUNTRY r2 said "in kg or L equivalent" about the coverage figures.
    - **C's own misses:** C's two stage 2 misses (H_LOWEST_COUNTRY, H_STOCKOUT_2027 r1) are correct for C-raw.
  - **Basis passed to `stock_coverage`:** C-raw passed NATIVE in 13 of its 46 calls, against 7 of 45 for C [measured].
    H-CR-2 is not refuted on the figures, but the basis chosen differs between the two agents. Why C-raw picks NATIVE
    more often is not established; its context has one more tool, whose basis text puts NATIVE first [inferred].
- **General and refusal:** equal to C on every turn.
- **Cost:** the harness estimate is 4.27 USD (stage 1 1.89, stage 2 2.38).
  - AI Credits 0.604 + 0.771: 0.024 and 0.025 credits per call, against C's billed mean of 0.038 per turn in stage 2.
  - Warehouse: 0.388 h.
  - With step 3 at 1.8 to 2.4 USD, steps 3 and 4 come to 6.1 to 6.7 USD by the harness, under the 9 USD pause.
  - Billed: 5.02 USD, 17.5 percent above the estimate, the gap in the warehouse (section 5).
- **T3 (stage 1) and T9 r2 (stage 2), figure or wording** (owner, step 5): both are wording errors, not figure
  errors.
  - The figures are the expected ones: T3 gave 6.0 months (expected 6.0), and T9 r2 gave 0 with NO_STOCK (expected 0,
    NO_STOCK). The `numeric` criterion passes on both.
  - Both fail `basis_wording` alone ("basis QTY_EQ not named"). C-raw passed `NATIVE` and named the item's own unit;
    the rubric expects the kg-equivalent basis named. Its figure-only score keeps the basis-named half, so they are
    wrong there too [measured, `eval/fixtures/grades_craw-s1.json`, `eval/fixtures/grades_craw-s2.json`].
  - **Questions (owner, step 5):** T3 asks "What is the stock coverage of released lots of green tea loose-leaf 1 kg
    (SKU-H04) in Italy as of June 2026?"; T9 asks "What is the stock coverage of oat cereal bar 1 kg (SKU-H11) in
    Switzerland as of June 2026?". Neither names a basis ("1 kg" is part of the product name); each is about one item.
    Two sentences of every C and C-raw spec point to different bases for such a question: the basis rule, "Stock and
    forecast are measured on one basis before the ratio: the item's own unit for a single item; kg or L equivalent for
    items of the same dimension, unless the question asks for value (EUR); value only when items of different
    dimensions are combined.", and the default parameter, "Pass basis QTY_EQ unless the question asks for value or for
    one item in its own unit (NATIVE)." [documented, `generated/agent_c_raw.yaml`, `generated/agent_c.yaml`]. C-raw
    followed the basis rule and passed `NATIVE`; C (`QTY_EQ` on the same turns), the reference parameters and the
    rubric follow the default-parameter sentence [measured]. The figure is the same on either basis [measured]; the
    two turns are counted wrong, not regraded. C-raw passed `NATIVE` in 13 of its 46 coverage calls, C in 7 of 45
    [measured]; this ambiguity may explain it [inferred].
  - **Limit:** the generated instructions are ambiguous for a single item asked without a basis; a point for the
    contract after the article (contract 0.5.1 and the generated files unchanged).

## 5. Billed (owner's go, read at 18:03 UTC, 3 hours after the last agent call)

`snowflake/session13_craw/cost_read.py`, run as written: one read-only batch as ACCOUNTADMIN with no secondary role,
4 statements, output outside the repository. Prices as in `eval/guards.py`: 2.00 USD an AI Credit, 3.90 USD a
platform credit.

- **Agent credits, matched by request id:** the 60 rows of `CORTEX_AGENT_USAGE_HISTORY` (LINKML_SVC, 14:10 to 15:10
  UTC, all on LINKML_C_RAW) are the 60 calls of the harness, one each; no row is unmatched and no call is missing
  [measured].

  | Calls | Requests matched | Billed (AI Credits) | Harness estimate | Billed USD |
  |---|---|---|---|---|
  | Smoke (step 3) | 4 of 4 | 0.1301 | 0.1301 | 0.26 |
  | Arm, stage 1 | 25 of 25 | 0.6039 | 0.6039 | 1.21 |
  | Arm, stage 2 | 31 of 31 | 0.7711 | 0.7711 | 1.54 |

  The billed token credits equal the estimate from the REST usage tokens to the fourth decimal [measured].
- **Per graded turn** (session 15, offline, computed afterwards): each graded turn is one call; the warm-ups (0.0657
  and 0.0413 credits) and the guardrail are excluded. The credits are the billed `TOKEN_CREDITS` of the turn's request id.
  The latency is the client seconds of the turn, as in `stage1_results.md`, section 3, and `stage2_results.md`,
  section 6. The same computation gives C's and B2's published medians and means in both stages [measured,
  `linkml-metrics-runs/s13/cost_read.json` and `linkml-metrics-runs/campaign/calls.json`]:

  | Stage | Graded turns | AI Credits, graded turns | Per graded turn, median / mean | Latency per turn, median (s) |
  |---|---|---|---|---|
  | 1 | 24 | 0.5382 | 0.0195 / 0.0224 | 19.0 |
  | 2 | 30 | 0.7298 | 0.0223 / 0.0243 | 18.3 |
- **Guardrail model:** 0.0417 credits (0.08 USD) in the day's `CORTEX_AI_GUARDRAILS` row, not in the estimate; the
  day's `CORTEX_AGENTS` row (1.5051) equals the 60 matched rows, so the guardrail credits are these calls'
  [measured; the attribution inferred].
- **Warehouse, per window:** the running intervals come from the resume and suspend events; the four metered hours
  (12:00 to 16:00 UTC) bill 1.4783 compute credits for 3,938 running seconds, 1.351 credits a running hour [measured].
  Each window's credits are its running seconds at that rate [inferred: the hourly rows do not follow the windows].

  | Window (UTC) | Running seconds | Compute credits | USD | Harness estimate |
  |---|---|---|---|---|
  | Step 1 reads, 13:02 to 13:04 | 86 | 0.032 | 0.13 | |
  | Step 3 dry run, 13:44 to 13:45 | 80 | 0.030 | 0.12 | |
  | Step 3, 13:59 to 14:23 | 1,442 | 0.541 | 2.11 | 1,435 s; 0.40 to 0.54 credits |
  | Step 4 arm, 14:37 to 15:03 | 1,548 | 0.581 | 2.27 | 0.388 h at 1 credit an hour: 0.388 credits |

- **Step 3 billed 2.37 USD** (agent 0.26, warehouse 2.11), inside its estimate of 1.8 to 2.4 USD [measured].
- **Step 4 billed 5.02 USD** (agent 2.75, warehouse 2.27), 17.5 percent above the harness estimate of 4.27 USD
  [measured]. The agent credits match; the gap is the warehouse: billed at 1.35 credits a running hour where the
  harness counts 1, and 1,548 running seconds against the 1,397 it counted, the auto-suspend tails included [measured].
- **Steps 3 and 4 billed 7.39 USD**, 7.47 with the guardrail model, under the 9 USD pause [measured].
- **Step 0 incident, apart:** 12:49:00 to 13:02:03 UTC, 783 running seconds, 0.294 compute credits (1.15 USD); the
  12:00 hour row bills 0.294 compute credits and holds no other window [measured].
- **Context, not the session's total:** the day's `METERING_DAILY_HISTORY` rows are partial at 18:03 UTC.
  `WAREHOUSE_METERING` 1.4783 compute and 0.3382 cloud services credits, 1.6686 billed after the daily cloud services
  adjustment; `CORTEX_AGENTS` 1.5051; `CORTEX_AI_GUARDRAILS` 0.0417; `SERVERLESS_TASK` 0.0042; `CORTEX_SEARCH`,
  `TELEMETRY_DATA_INGEST` and `PIPE` below 0.001 [measured]. The cloud services credits of the four hours (0.336) are
  not split by window.
