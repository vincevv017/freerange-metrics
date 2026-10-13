# Session 8: configurations A, B1, B2, D and D′ (raw results)

Contract 0.4.1, charter `docs/configurations.md` version 1, rubric `eval/rubric.yaml` version 1. Setup as perso,
`USE SECONDARY ROLES NONE`, `LINKML_METRICS_ROLE`; every agent call as `LINKML_SVC` under budget `s8` (cap 34: 29
calls, plus 5 for the D′ approval resumes). Tags: **[documented]**, **[measured]**, **[inferred]**.

**Run logs.** From step 1 on, `run_call.py` logs (`calls.json` with the `s8` budget, raw events, summaries, threads)
and the extracted traces go to `~/work/assets/linkml-metrics-runs/s8/`, a persistent folder outside the repository
(they carry the account host). Never a session scratchpad: its cleaning lost the raw events of sessions 7 and 8a.

## Step 0: no agent call

### Contract 0.4.1 (owner's precision 4, 2026-10-04)

- `SCOPE_ITEM_TYPE` names the metric it applies to: `applies_to_metrics: [stock_coverage]` (metamodel 0.3.0 adds the
  slot, required, with `applies_to_measures` restricted to those metrics). The default scope is a coverage rule; it
  does not apply to closing stock (decision of 2026-10-03, phase 3 notes finding 42). The `item_type` description,
  read by the closing view's comment and the procedure, says so. No coverage rule changed. [documented]
- `check_dataset.py` computes closing stock with no default scope; the three closing heroes keep their values (0,
  450, 450). [measured]
- Everything regenerated. `generated/agent_c.yaml` differs in its header comment only, so the spec of `LINKML_C` is
  unchanged and the agent was not touched. [measured]
- Redeployed as LINKML_METRICS_ROLE: `STOCK_COVERAGE` (`0000026b-0000-4000-8000-00000000026b`),
  `FCT_STOCK_SNAPSHOT_GAPFILLED` (`0000026c-0000-4000-8000-00000000026c`), `CLOSING_STOCK_SV`
  (`0000026d-0000-4000-8000-00000000026d`). Full suite 129 passed. [measured]

### Read-only checks before the charter

- `AP_LINKLM` exists in `LINKML_METRICS.RAW`, owned by `LINKML_METRICS_ROLE`, created 2026-10-03 13:16 PDT, extension
  `["CA","AI"]`. `SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('LINKML_METRICS.RAW.AP_LINKLM')` equals
  `AP_LINKLM_autopilot.yaml` as text with whitespace removed and as parsed YAML. [measured]
- The YAML export of `COVERAGE_NATIVE_RANGE_SV` (probe A, DDL) carries the 24 RANGE window metrics as `expr` with
  `OVER (PARTITION BY EXCLUDING ...)` and the stock metric with `non_additive_dimensions`. The same YAML with
  `is_enum` and `sample_values` added on one dimension passed `CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(..., TRUE)`
  ("YAML file is valid for creating a semantic view. No object has been created yet.", query id
  `0000026e-0000-4000-8000-00000000026e`). On this account a YAML view carries window metrics and
  `is_enum` together. [measured]
- The enrich tool profiles a dimension with `SELECT DISTINCT` on `database.schema.table` of its logical table; a
  logical table defined by a query has no such triplet and the tool stops on it (`fqn()`), hence B2's physical views.
  [measured on the code, not run]

### Oracle independence (decision 3)

`pandas_warnings()` in `data/checks/check_dataset.py` recomputes every warning a trap declares from the dataset alone.
FORECAST_GAPS_FILLED counts the months of t+1..t+24 with no forecast row over the item x country pairs of the query
that have a forecast row in that window: T2 2, BEYOND_H 2, **BULK_SCOPE 2** (the value frozen from the procedure in
session 7, now from its source), T5 5 (a refusal, not declared). DEFAULT_SCOPE_EXCLUDED 51,475.5 and
MASTER_DATA_DUPLICATES 1 (T7) likewise; every other trap 0. `tests/test_reference_oracle.py` recomputes every expected
value of `generated/reference_questions.yaml` in pandas with no Snowflake connection, and asserts that the generating
sources import no Snowflake module and that `traps.yaml` names no value as read from the procedure. [measured]

### General questions (decision 6)

| Id | Question | Expected (pandas) | Wrong values asserted |
|---|---|---|---|
| G1 | Demand forecast of fruit juice (BEV_JUICE, no hero) in France for September 2026 (LATEST + 3), QTY_EQ | 6,416 | raw packs summed 764; June 5,899; July to September 20,721 |
| G2 | Closing stock value in EUR by country at June 2026: every item type and batch status, by the snapshot's own `country_id`, no join to `DIM_ITEM` | 10 rows, FR 43,879,032.93 to SE 14,476,855.48 (sum = all stock value of the month) | join to `DIM_ITEM`: SE 14,481,655.48 (+4,800, SKU-H06 twice); coverage default scope applied: FR, BE, NL, ES, SE lower |

Both carry `expected_route: semantic_view`; every question now carries `expected_route` (coverage, semantic_view or
clarify). The reference set holds **19** questions: the 17 of the file plus G1 and G2 (decision 4 counted 18 in the
file). [measured]

### Rubric and grader (decision 2)

`eval/rubric.yaml` version 1; `eval/grade.py` grades a turn from its answer text, tool calls and SQL. Tests
(`tests/test_grade.py`, 32): the 14 answers agent C gave in session 7, **rebuilt from the session 7 table of
`snowflake/phase4_agent_c/results.md`** (the raw events were kept outside the repository and no longer exist), all
graded correct, T5 classified `model_refusal_with_qty_eq_answer`; one synthetic wrong answer per named wrong
behaviour; G2 at full precision and with the fan-out; a G2 answer in millions whose SQL joins `DIM_ITEM` graded
manual; routing per configuration; an unclassifiable answer graded manual. [measured]

Interpretation written into the rubric before any call: "within 0.05" also accepts a number equal to the expected
value rounded half-up to the precision the answer writes it at, so that 2.25 written 2.3 and 43,879,032.93 written
43.9 million are correct, and an amount written in full is compared in full. [inferred, owner to confirm]

Owner's precisions before any graded turn (rubric still version 1): the campaign set is 19 questions (decision 4's
"18" was a count error); and the **indistinguishable-precision guard**, for every trap: when the precision an answer
writes a number at makes a declared wrong value indistinguishable from the expected value, the criterion is decided
on the turn's SQL or tool parameters: a method signature (a join to an item object holding SKU-H06 twice with no
deduplication, raw-unit columns, the coverage default scope applied) is wrong, readable SQL or parameters without it
is correct, none readable is manual. `tests/test_grade.py` (33): G2 in millions is wrong with a raw `DIM_ITEM` join,
correct without a join or with a `DISTINCT` projection, manual with no SQL. [documented]

### Suite

`check_dataset.py`: all checks passed (sections 6 and 7 added). Full suite: **183 passed**.

## Step 1: latency witness with a 2 s CALL (calls 1 and 2 of budget s8)

`witness/witness_wait.sql`: the session 8a SQL Scripting witness with `SELECT SYSTEM$WAIT(2);` before its `RETURN`;
the agent `LINKML_WITNESS_PROBE` from the reviewed session 8a spec, unchanged (`CREATE PROCEDURE`
`0000026f-0000-4000-8000-00000000026f`, `CREATE AGENT` `00000270-0000-4000-8000-000000000270`; SHOW VERSIONS: `live`
and `VERSION$1` default, both equal to the spec). Warehouse warm before each call (GENERATOR sum, STARTED:
`00000271-0000-4000-8000-000000000271`, `00000272-0000-4000-8000-000000000272`). Question "Call the witness with label
wN.", policy `w`, as LINKML_SVC. **UTC window: 2026-10-04 06:44:08.6 (call 1 sent) to 06:45:38.0 (call 2 answered).**
2 calls, 2 status 200, one tool call `{"label": "wN"}` each, one-sentence answer, no approval asked.

| # | Label | Request id | Version served | Client s | Tool span s | CALL elapsed ms (compile) | `SYSTEM$WAIT` child ms | Queued provisioning / overload ms (CALL, child) | Span end - CALL end s |
|---|---|---|---|---|---|---|---|---|---|
| 1 | w5 | `00000273-0000-4000-8000-000000000273` | LIVE | 11.11 | 4.24 | 2,439 (212) | 2,063 | 0 / 0, 0 / 0 | 1.80 |
| 2 | w6 | `00000274-0000-4000-8000-000000000274` | LIVE | 7.97 | 2.57 | 2,441 (242) | 2,053 | 0 / 0, 0 / 0 | 0.13 |

Raw `latency.py --budget s8` rows: w5 server 10.05 s, before planning 1.28, planning 1.66, response 1.42, suggested
queries 1.46; w6 server 7.19, before planning 0.26, planning 1.47, response 1.38, suggested queries 1.52. The CALL
starts at the tool span's start on both turns (`SqlExecution` span start = CALL start to the millisecond).

Reading:
- **A step exists between 1.2 and 4.3 s**: w6's span ended 2.57 s after it started, 0.13 s after a 2.44 s CALL.
  [measured, one observation]
- **It is not reliable**: the same 2.44 s CALL on w5 waited for the 4.3 s point (span 4.24 s, 1.80 s after the CALL).
  Points observed across sessions 7, 8a and 8: about 0.5, 1.2, 2.6, 4.3 and 8.5 s. [measured]
- A doubling interval (0.5, 1.2, 2.6, 4.3?, 8.5) fits 0.5 to 2.6 but not 4.3; the poll phase relative to the CALL may
  decide which point a CALL catches, so a 2.4 s CALL lands on 2.6 or 4.3. [inferred]
- For agent C's rewrite (session 8b): a SQL Scripting coverage CALL of about 2 s would end the tool span at about
  2.6 s at best and 4.3 s otherwise, against 8.5 s today. [inferred]
- Version served: `LIVE` on every span while `VERSION$1` was the default, as for session 8a's first witness binding.
  [measured]

Objects: the whole `GET_AI_OBSERVABILITY_EVENTS` output (18 rows, 2 records) and the per-turn traces saved in
`~/work/assets/linkml-metrics-runs/s8/`, then `LINKML_WITNESS_PROBE` and `WITNESS_SQL(VARCHAR)` dropped
(`00000275-0000-4000-8000-000000000275`, `00000276-0000-4000-8000-000000000276`). SHOW AGENTS in RAW lists only
`LINKML_C`; SHOW PROCEDURES LIKE 'WITNESS%' is empty.

Budget s8: 2 of 34 used.

## Step 2: B2, built from the contract

`compiler/gen_native_sv.py` (drift test in `tests/test_generated.py`) writes `generated/b2_native_views.sql`,
`generated/b2_native_sv.yaml` and `generated/agent_b2.yaml` from contract 0.4.1 and the dataset.

| Object | Statement or query id | Notes |
|---|---|---|
| `B2_ITEM` (view) | `00000277-0000-4000-8000-000000000277` | 61 rows for 60 items: SKU-H06 keeps its two rows (lifecycle ACTIVE and PHASE_OUT) |
| `B2_STATUS` (view) | `00000278-0000-4000-8000-000000000278` | 3 statuses |
| `B2_FORECAST_SPINE` (view) | `00000279-0000-4000-8000-000000000279` | 23,652 rows, 36 valid analysis months (2023-07-01 to 2026-06-01) |
| `LINKML_B2_SV` dry run, generated YAML | `0000027a-0000-4000-8000-00000000027a` | valid |
| Enrichment (owner's tool, commit `9add908`, as LINKML_SVC, threshold 30, `month_start`, `snapshot_month`, `forecast_month` excluded) | `b2/enrich_report.csv` | 18 dimensions set (16 `is_enum: true`, 2 false with 3 hint values), 4 skipped (3 dates excluded, 1 boolean), no NULL; the enriched YAML differs from the generated one by `is_enum` and `sample_values` only (test) |
| `LINKML_B2_SV`, enriched YAML (`deploy_sv.py`: dry run then CALL) | `0000027b-0000-4000-8000-00000000027b` / `0000027c-0000-4000-8000-00000000027c` | read back: 124 members, the same names, `is_enum` and `sample_values` equal to the file; 2 verified queries (background members SNACK_CRISPS x DE, PANTRY_RICE x IT) |

Measured on the way: the YAML read back from the deployed view carries `is_enum` and `sample_values` (on the YAML path they
survive the round trip). The tool's two `is_enum: false` hint lists are its alphabetical first three: `sku_name` hints include two hero
names (Arabica beans 1 kg, Bread flour 1 kg); the verified-query rule (no hero) does not cover the tool's hints, and
the tool's output is kept as it is. [measured]

### Object check, direct `SEMANTIC_VIEW()` (no agent, no grading): `b2/object_check.py`

| Case | Returned | Expected | Match | Query id |
|---|---|---|---|---|
| T1 PANTRY_FLOUR x FR, STANDARD | 2.8 | 2.8 | yes | `0000027d-0000-4000-8000-00000000027d` |
| T2 SKU-H03 x DE | 7.0 | 7.0 | yes | `0000027e-0000-4000-8000-00000000027e` |
| T3 SKU-H04 x IT, RELEASED | 6.0 | 6.0 | yes | `0000027f-0000-4000-8000-00000000027f` |
| T4 SKU-H05 | 8.5 | 8.5 | yes | `00000280-0000-4000-8000-000000000280` |
| T7 PANTRY_OIL x SE | **3.0** | 2.25 | **no** | `00000281-0000-4000-8000-000000000281` |
| T8 SKU-H08 | 0 | 0 | yes | `00000282-0000-4000-8000-000000000282` |
| NO_DEMAND SKU-H09 | NULL | NULL | yes | `00000283-0000-4000-8000-000000000283` |
| BEYOND_H SKU-H10 | 50.0 | 50.0 | yes | `00000284-0000-4000-8000-000000000284` |
| BULK_SCOPE HOT_GROUND, STANDARD | 8.6735 | 8.6735 | yes | `00000285-0000-4000-8000-000000000285` |
| T9 SKU-H11 at June 2026 | 0 | 0 | yes | `00000286-0000-4000-8000-000000000286` |
| CS_LAST_MONTH_GAP SKU-H11 x CH, 2026-Q2 | 0 | 0 | yes | `00000287-0000-4000-8000-000000000287` |
| CS_FAMILY SNACK_BARS x CH, 2026-Q2 | 450 | 450 | yes | `00000288-0000-4000-8000-000000000288` |
| G1 BEV_JUICE x FR, 2026-09 | 6,416 | 6,416 | yes | `00000289-0000-4000-8000-000000000289` |
| G2 SE closing value, June 2026 (no item dimension) | 14,476,855.48 | 14,476,855.48 | yes | `0000028a-0000-4000-8000-00000000028a` |

T7: the item projection keeps `lifecycle_status`, on which SKU-H06's two rows differ, so any query reaching the
item table counts its stock twice (1,500 against 900): the objects carry the fan-out the charter names for T7_R1
and G2 (H-B2-1) on T7 as well, so hypothesis H-B2-2 (right number) cannot hold for T7 whatever the agent does. The
charter is frozen; recorded here, read with H-B2-1 at the campaign. [measured]

T7 arbitrage (owner, 2026-10-04): B2 stays as generated. The native alternative, an item projection that takes
`ANY_VALUE(lifecycle_status)` per item, would make T7 right (2.25) but T7_R1 silently wrong: one lifecycle row for
SKU-H06, picked arbitrarily, where the contract refuses (`MASTER_DATA_FANOUT`). It is a trade-off, not a fix: a
semantic view can carry either the fanned-out number or a silently chosen attribute, never the refusal. To take up in
the article. The tool's `sku_name` hints that name heroes are accepted as they are: they are data values.

### Agent LINKML_B2

`snowflake/phase4_others/agents.py` as LINKML_METRICS_ROLE: `CREATE AGENT` `0000028b-0000-4000-8000-00000000028b`
(live and `VERSION$1` default, both equal to `generated/agent_b2.yaml`), then the five-beat cycle: MODIFY LIVE
`0000028c-0000-4000-8000-00000000028c`, COMMIT `<query-id>`, ADD LIVE VERSION FROM LAST `<query-id>`, SET
DEFAULT_VERSION = 'VERSION$2' (read from SHOW VERSIONS) `<query-id>`. SHOW VERSIONS: LIVE, `VERSION$2` (default) and
`VERSION$1` equal to the file; DESCRIBE equal. Grants: OWNERSHIP to LINKML_METRICS_ROLE only. Beat 5 is call 3
(T1), which returned a figure.

### Smoke: T1, T6, T9, CS_LAST_MONTH_GAP (calls 3 to 6 of budget s8)

`smoke.py run B2 LINKML_B2 ...` as LINKML_SVC, policy deny-all (no approval asked), warehouse warm before each call.
**UTC window: 2026-10-04 07:04:12.1 (call 3 sent) to 07:09:08.1 (call 6 answered).** 4 calls, 4 status 200, no
`response.warning`.

| Id | Tool calls | Answer (verbatim) | Grade | Criteria (eval/grade.py) |
|---|---|---|---|---|
| T1 | system_agentic_semantic_context, system_execute_sql, system_execute_sql, system_execute_sql | Flour and baking in France had about 2.8 months of stock coverage in June 2026. That figure is in kg or L equivalent quantity, for STANDARD items only (bulk stock is excluded by default). The analysis month is June 2026, so the demand forecast window is July 2026 onward.  Stock on hand was 1,400 and the forecast demand is a steady 500 per month. The stock covers two full months and 400 of the third month's 500, which gives 2.8 months.  I couldn't run the built-in coverage metric directly, so I calculated it from the stock and forecast figures the model returned, using the model's own formula. | **correct** | numeric pass (expected 2.8 given); analysis_month_named pass (named); no_aggregated_coverage pass (no added or averaged coverage); routing pass (semantic_view) |
| T6 | none | Which month do you want the coverage for? Stock coverage is measured at a single analysis month, so I can't give one figure for the whole of 2026. It also can't be summed or averaged across months.  You could pick one month between January and June 2026. June 2026 is the latest available month. I can also give you a month-by-month series for 2026 if you'd like that.  Once you choose, I'll calculate coverage for Flour and Baking in France (FR) on standard items. Coverage will be the number of months the stock on hand lasts against the next 24 months of forecast demand. | **correct** | refusal pass (no number; asks for the month or refuses with a reason); no_aggregated_coverage pass (no added or averaged coverage); routing pass (no tool call) |
| T9 | system_agentic_semantic_context, system_execute_sql, system_execute_sql, system_execute_sql, system_execute_sql | Stock coverage for Oat cereal bar 1 kg (SKU-H11) in Switzerland as of the June 2026 analysis month is **0 months**. The STANDARD item had zero stock on hand at the June 2026 snapshot. Demand is still forecast, at about 100 kg-equivalent in July 2026 and 200 in the first two months combined. With nothing in stock, the stock covers none of that demand. The figure uses quantity in kg/L equivalent, over the 24-month forecast window.  I computed this by hand from the stock and forecast data, because the coverage metric wouldn't run as a single query. | **correct** | numeric pass (expected 0.0 given); analysis_month_named pass (named); no_aggregated_coverage pass (no added or averaged coverage); routing pass (semantic_view) |
| CS_LAST_MONTH_GAP | system_agentic_semantic_context, system_execute_sql | The closing stock of Oat cereal bar 1 kg (SKU-H11) in Switzerland for Q2 2026 was 0 kg equivalent, and its stock value was also 0 EUR. Closing stock for a quarter is the snapshot of its last month, June 2026. The item is a STANDARD, ACTIVE item, and the gap-filled stock data has it at zero in that month. | **correct** | numeric pass (expected 0.0 given); routing pass (semantic_view) |

Grader corrections made on these real answers before the grades above (shown to the owner with the grades): the
executed SQL is read from the SQL tool calls' `input.sql` (the trace read as LINKML_SVC carries no `final_sql`);
and a number preceded by "next" or "following" is the horizon's month count, which the rubric already excludes,
not a coverage (T6 was first graded wrong on "the next 24 months of forecast demand"). Neither changes the rubric.
`tests/test_grade.py`: 34, including T6's real text.

Per call (`records.py`):

| Label | Request id | Started (UTC) | Client s | First byte s | Version served | Orchestration input (cache write / read), output | Server s | Before planning s | Planning s (steps) | Context s | SQL tool s | Skill/code s | Response s | Suggested s | Computed by | Queries of the turn: elapsed ms (queued provisioning / overload ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b2_t1 | `00000146-0000-4000-8000-000000000146` | 07:04:12.083 | 27.7 | 3.05 | VERSION$2 | 201,703 (50,594 / 151,095), out 2,067 | 25.81 | 1.72 | 14.76 (3) | 0.4 | 3.29 | 0 | 4.3 | 2.4 | model | 404 (0 / 0) agent SQL; 883 (0 / 0) agent SQL; 820 (0 / 0) agent SQL |
| b2_t6 | `0000014a-0000-4000-8000-00000000014a` | 07:05:58.128 | 6.27 | 1.52 | VERSION$2 | 33,301 (3,542 / 29,751), out 190 | 4.94 | None | 0 (0) | 0 | 0 | 0 | 3.05 | 1.54 | n/a (no tool) | none |
| b2_t9 | `00000014-0000-4000-8000-000000000014` | 07:07:14.805 | 32.41 | 1.33 | VERSION$2 | 292,797 (36,266 / 256,513), out 2,020 | 31.13 | 0.34 | 18.66 (5) | 0.11 | 5.03 | 0 | 4.5 | 2.46 | model | 189 (0 / 0) agent SQL; 489 (0 / 0) agent SQL; 308 (0 / 0) agent SQL; 1435 (0 / 0) agent SQL |
| b2_cs_last_month_gap | `00000144-0000-4000-8000-000000000144` | 07:08:53.169 | 14.91 | 1.16 | VERSION$2 | 150,478 (32,768 / 117,698), out 781 | 13.72 | 0.23 | 5.92 (2) | 0.42 | 1.05 | 0 | 3.52 | 2.56 | n/a | 540 (0 / 0) agent SQL |

SQL the agent wrote (from the tool calls):

**T1 statement 1**

```sql
SELECT i.family_code, g.country_code, c.month_start, coverage_months_qty_eq FROM __stock s JOIN __item i ON s.item_id=i.item_id JOIN __geo g ON s.country_id=g.country_id JOIN __calendar c ON s.snapshot_month=c.month_start WHERE i.family_code='PANTRY_FLOUR' AND g.country_code='FR' AND c.month_start='2026-06-01' AND i.item_type='STANDARD' GROUP BY i.family_code, g.country_code, c.month_start
```

**T1 statement 2**

```sql
SELECT SUM(s.stock_qty_eq) AS stock FROM __stock s JOIN __item i ON s.item_id=i.item_id JOIN __geo g ON s.country_id=g.country_id WHERE i.family_code='PANTRY_FLOUR' AND g.country_code='FR' AND s.snapshot_month='2026-06-01' AND i.item_type='STANDARD'
```

**T1 statement 3**

```sql
SELECT SUM(f.f01_qty_eq)/COUNT(DISTINCT f.batch_status) m01, SUM(f.f02_qty_eq)/COUNT(DISTINCT f.batch_status) m02, SUM(f.f03_qty_eq)/COUNT(DISTINCT f.batch_status) m03, SUM(f.f04_qty_eq)/COUNT(DISTINCT f.batch_status) m04, SUM(f.f05_qty_eq)/COUNT(DISTINCT f.batch_status) m05, SUM(f.f06_qty_eq)/COUNT(DISTINCT f.batch_status) m06, SUM(f.f07_qty_eq)/COUNT(DISTINCT f.batch_status) m07, SUM(f.f08_qty_eq)/COUNT(DISTINCT f.batch_status) m08, SUM(f.f09_qty_eq)/COUNT(DISTINCT f.batch_status) m09, SUM(f.f10_qty_eq)/COUNT(DISTINCT f.batch_status) m10, SUM(f.f11_qty_eq)/COUNT(DISTINCT f.batch_status) m11, SUM(f.f12_qty_eq)/COUNT(DISTINCT f.batch_status) m12 FROM __fwd f JOIN __item i ON f.item_id=i.item_id JOIN __geo g ON f.country_id=g.country_id WHERE i.family_code='PANTRY_FLOUR' AND g.country_code='FR' AND f.as_of_month='2026-06-01'
```

**T9 statement 1**

```sql
SELECT sku_code, sku_name, item_type, COUNT(*) FROM __item GROUP BY sku_code, sku_name, item_type HAVING sku_name ILIKE '%oat%' OR sku_code ILIKE '%H11%'
```

**T9 statement 2**

```sql
SELECT i.sku_code, g.country_code, c.month_start, coverage_months_qty_eq FROM __stock s JOIN __item i ON s.item_id=i.item_id JOIN __geo g ON s.country_id=g.country_id JOIN __calendar c ON s.snapshot_month=c.month_start WHERE i.sku_code='SKU-H11' AND g.country_code='CH' AND c.month_start='2026-06-01' AND i.item_type='STANDARD' GROUP BY i.sku_code, g.country_code, c.month_start
```

**T9 statement 3**

```sql
SELECT item.sku_code, geo.country_code, calendar.month_start, coverage_months_qty_eq FROM __stock, __item AS item, __geo AS geo, __calendar AS calendar WHERE item.sku_code='SKU-H11' AND geo.country_code='CH' AND calendar.month_start='2026-06-01' AND item.item_type='STANDARD' GROUP BY item.sku_code, geo.country_code, calendar.month_start
```

**T9 statement 4**

```sql
WITH st AS (SELECT SUM(s.stock_qty_eq) AS stock FROM __stock s JOIN __item i ON s.item_id=i.item_id JOIN __geo g ON s.country_id=g.country_id WHERE i.sku_code='SKU-H11' AND g.country_code='CH' AND i.item_type='STANDARD' AND s.snapshot_month='2026-06-01'),
fw AS (SELECT SUM(f.f01_qty_eq)/COUNT(DISTINCT f.batch_status) m1, SUM(f.f01_qty_eq+f.f02_qty_eq)/COUNT(DISTINCT f.batch_status) c2, SUM(f.f01_qty_eq+f.f02_qty_eq+f.f03_qty_eq)/COUNT(DISTINCT f.batch_status) c3 FROM __fwd f JOIN __item i ON f.item_id=i.item_id JOIN __geo g ON f.country_id=g.country_id WHERE i.sku_code='SKU-H11' AND g.country_code='CH' AND f.as_of_month='2026-06-01')
SELECT * FROM st, fw
```

**CS_LAST_MONTH_GAP statement 1**

```sql
SELECT i.item_id, i.sku_code, i.sku_name, i.item_type, i.lifecycle_status, SUM(s.stock_qty_eq) AS q, SUM(s.stock_value_eur) AS v FROM __stock AS s JOIN __item AS i ON s.item_id = i.item_id JOIN __geo AS g ON s.country_id = g.country_id WHERE (i.sku_name ILIKE '%oat%bar%' OR i.sku_code ILIKE '%H11%') AND g.country_code = 'CH' AND s.snapshot_month = '2026-06-01' GROUP BY ALL
```

Reading [measured]:
- **The metric is not used; the model computes coverage itself.** On T1 the first statement selects
  `coverage_months_qty_eq` as a column against the logical tables and fails (`invalid identifier
  'COVERAGE_MONTHS_QTY_EQ'`); the model then reads the stock and the 24 monthly forward sums and computes 2.8 in its
  answer, and says so ("I calculated it ... using the model's own formula"). T9 likewise ("I computed this by hand").
  H-B2-6 confirmed on the smoke. The right numbers come from the model's arithmetic on right inputs.
- T6: no tool call, asks for the month, gives the latest month: H-B2-3 refuted as expected (asks).
- T9 and CS_LAST_MONTH_GAP: 0, read from the gap-filled snapshot: H-B2-4 refuted as expected.
- Orchestration input tokens 150,000 to 293,000 per tool turn (agent C: about 49,000), 33,000 without a tool: the
  semantic model (124 members, two 26-branch coverage expressions) sits in every planning step. The 40,000-token
  budget was not enforced (as documented). Turn 14.9 to 32.4 s with a tool (agent C: about 17 s), 6.3 s without.
- Every query of the four turns: queued provisioning 0, overload 0.
- Version served: `VERSION$2` (the default) on every span, through the bare-name REST call.

Budget s8: 6 of 34 used.

### Why the agent does not use `coverage_months_qty_eq` (diagnosis, no agent call)

What the agent wrote (T1, first statement; T9 the same twice, once with the tables listed in `FROM`):

```sql
SELECT i.family_code, g.country_code, c.month_start, coverage_months_qty_eq
FROM __stock s JOIN __item i ON s.item_id=i.item_id JOIN __geo g ON s.country_id=g.country_id
JOIN __calendar c ON s.snapshot_month=c.month_start
WHERE i.family_code='PANTRY_FLOUR' AND g.country_code='FR' AND c.month_start='2026-06-01' AND i.item_type='STANDARD'
GROUP BY i.family_code, g.country_code, c.month_start
```

What ran (the tool's error payload, query `00000147-0000-4000-8000-000000000147`): each logical table the statement
names becomes a CTE over its base object projecting only the columns the statement uses (`WITH __stock AS (SELECT
snapshot_month, country_id, item_id FROM LINKML_METRICS.RAW.FCT_STOCK_SNAPSHOT_GAPFILLED), __item AS (...)`), then the
statement runs as written over those CTEs. A metric is not a column of any logical table, so
`coverage_months_qty_eq` cannot resolve: `invalid identifier 'COVERAGE_MONTHS_QTY_EQ'` (T1 once, T9 twice). The model
then read the stock and the monthly forward sums from the same logical tables (`SUM(f.f01_qty_eq)/COUNT(DISTINCT
f.batch_status)` and so on, the bridge division copied from the metric definitions) and did the cascade in its answer.

The metric (YAML, view level, deployed): `coverage_months_qty_eq`, expression `CASE WHEN stock.closing_stock_qty_eq IS
NULL OR ... = 0 THEN 0 WHEN fwd.cum_qty_eq_24 IS NULL OR ... = 0 THEN NULL WHEN stock.closing_stock_qty_eq <=
fwd.cum_qty_eq_01 THEN ... ELSE stock.closing_stock_qty_eq / (fwd.cum_qty_eq_24 / (IFF(fwd.month_qty_eq_01 > 0, 1, 0)
+ ...)) END`, over private metrics `cum_qty_eq_NN` and `month_qty_eq_NN`. Through `SEMANTIC_VIEW(... METRICS
coverage_months_qty_eq ...)` it returns the trap values (object check above). The two verified queries do not use it:
they are plain SQL over `__stock` and `__forecast` (closing stock, forecast).

Conclusion: **a platform limit, not a construction defect.**
- Documented: Cortex Agents generate SQL directly instead of delegating SQL generation to Cortex Analyst, and their
  usage is reported under `cortex_agents` (https://docs.snowflake.com/release-notes/2026/other/2026-04-13-cortex-agents-agentic-analyst, Apr 13, 2026).
  [documented]
- Measured here: that SQL is run over logical-table CTEs that expose dimensions and facts, never metrics; a view-level
  metric is reachable only through the `SEMANTIC_VIEW()` clause (or the `AGG()` form), which the model did not write
  in any of the 8 statements of the four turns. [measured]
- B2 stays as generated: the metric exists and returns the right values, the agent computes coverage by hand from
  the right inputs. That is a result of the configuration. One construction note, not applied (the charter is frozen
  and one fix per configuration would go to a documented mechanism, which this is not): B2's generated instruction
  names the metric ("Use the metric coverage_months_qty_eq ..."), which is what the model tried to select as a column.
  [measured]

## Step 3: B1, the hand-written native view

`b1/LINKML_B1_SV.yaml`, written by hand on probe A's B1-RANGE shape: the seven RAW tables with their eight
relationships, stock `NON ADDITIVE BY` the snapshot month (quantity and value), the forecast as a flow (quantity,
value, non-zero month flag), the 24 forward window metrics `c01..c24` (`RANGE BETWEEN 1 FOLLOWING AND k FOLLOWING`
over `month_index`, `PARTITION BY EXCLUDING cal.month_start, cal.month_index`) and `nz24`, descriptions; two verified
queries on the same background members as B2 (closing stock SNACK_CRISPS x DE 2026-Q1, forecast PANTRY_RICE x IT
2026-08). No coverage metric: a derived metric over window metrics is rejected (`010273`, phase 0).

| Object | Statement or query id | Notes |
|---|---|---|
| Dry run, hand-written YAML | `0000028d-0000-4000-8000-00000000028d` | valid: a YAML view carries the window metrics |
| Enrichment (same tool, commit, user and settings as B2; `month_index` excluded with the dates) | `b1/enrich_report.csv` | 18 dimensions set (16 `is_enum: true`, 2 false), 4 skipped, no NULL; only `is_enum` and `sample_values` differ (test) |
| `LINKML_B1_SV`, enriched YAML (`deploy_sv.py`) | `0000028e-0000-4000-8000-00000000028e` / `0000028f-0000-4000-8000-00000000028f` | read back: 52 members, same names, grounding equal to the file, 2 verified queries |

Object check, direct `SEMANTIC_VIEW()` (`b1/object_check.py`, no agent, no grading):

| Case | Returned | Expected | Match | Query id |
|---|---|---|---|---|
| T1 stock PANTRY_FLOUR x FR, June 2026 | 1,400 | 1,400 | yes | `00000290-0000-4000-8000-000000000290` |
| T1 `c03` at June 2026 (month filter outside the call) | 1,500 | 1,500 | yes | `00000291-0000-4000-8000-000000000291` |
| T7 stock PANTRY_OIL x SE, June 2026 | **1,500** | 900 | **no** | `00000292-0000-4000-8000-000000000292` |
| CS_LAST_MONTH_GAP SKU-H11 x CH, 2026-Q2 | **350** | 0 | **no** | `00000293-0000-4000-8000-000000000293` |
| G1 forecast BEV_JUICE x FR, 2026-09 | 6,416 | 6,416 | yes | `00000294-0000-4000-8000-000000000294` |

The view carries the native defects the charter names: the raw `DIM_ITEM` join counts SKU-H06 twice (H-B1-3), and
`NON ADDITIVE BY` on the raw snapshot closes SKU-H11 at May's 350 (H-B1-4). [measured, object level]

Agent spec `b1/agent_b1.yaml` (hand-written): one `cortex_analyst_text_to_sql` tool on `LINKML_B1_SV`, orchestration
instructions DEFINITION.md sections 1 to 3 and 7 in hand-written prose (2,305 characters), the common response
instruction, `tool_not_accessible: reject`, 120 s / 40,000 tokens. Shown to the owner before CREATE.

Charter version 2 (owner, before LINKML_B1's CREATE): DEFINITION.md section 8 (default scope and analysis month)
added; the orchestration instructions of A, B1, D and D′ include it. LINKML_B1's spec gains section 8 rewritten by
hand (instructions 2,305 to 2,973 characters). B2 unchanged (its generated instructions carry both rules).

### Agent LINKML_B1

`agents.py`: `CREATE AGENT` `00000295-0000-4000-8000-000000000295` (live and `VERSION$1` default equal to
`b1/agent_b1.yaml`), five-beat cycle: MODIFY LIVE `00000296-0000-4000-8000-000000000296`, COMMIT
`00000297-0000-4000-8000-000000000297`, ADD LIVE `<query-id>`, SET DEFAULT_VERSION = 'VERSION$2'
`00000298-0000-4000-8000-000000000298`. SHOW VERSIONS: LIVE, `VERSION$2` (default), `VERSION$1` equal to the file.
Grants: OWNERSHIP to LINKML_METRICS_ROLE only. Beat 5 is call 7 (T1), which returned a figure.

### Smoke: T1, T6, T9, CS_LAST_MONTH_GAP (calls 7 to 10 of budget s8)

As LINKML_SVC, policy deny-all (no approval asked), warehouse warm before each call. **UTC window: 2026-10-04
07:35:00.1 (call 7 sent) to 07:39:23.2 (call 10 answered).** 4 calls, 4 status 200.

| Id | Tool calls | Answer (verbatim) | Grade | Criteria (eval/grade.py) |
|---|---|---|---|---|
| T1 | system_agentic_semantic_context, system_execute_sql, system_execute_sql | Coverage is 2.8 months for Flour and baking (family PANTRY_FLOUR) in France, measured on the June 2026 closing stock. That stock is 1,400 kg or litre equivalent, and the forecast for the 24 months from July 2026 to June 2028 is a flat 500 per month. The stock runs out during the third month: 2 full months use 1,000, and the remaining 400 covers 0.8 of September 2026.  This counts STANDARD stock only. No BULK stock was held for this family in France in June 2026, so none was left out. | **correct** | numeric pass (expected 2.8 given); analysis_month_named pass (named); no_aggregated_coverage pass (no added or averaged coverage); routing pass (semantic_view) |
| T6 | none | Coverage is measured at one analysis month, so I can't compute it for a whole year. Please tell me which month you mean.  Stock snapshots run monthly from July 2023 to June 2026. For 2026, the months available are January to June 2026.  I can give coverage for one of those months, for example June 2026, which is the latest. I can also give a series with one value per month from January to June. Each value would be the closing stock of flour and baking in France for that month, measured against the French forecast for the 24 months that follow it. Only STANDARD stock counts toward coverage, and I'd tell you how much BULK stock was left out.  Which would you like? | **correct** | refusal pass (no number; asks for the month or refuses with a reason); no_aggregated_coverage pass (no added or averaged coverage); routing pass (no tool call) |
| T9 | system_agentic_semantic_context, system_execute_sql, system_execute_sql | The stock coverage of Oat cereal bar 1 kg (SKU-H11) in Switzerland as of June 2026 is **0 months**. There is no closing stock for this SKU in Switzerland in the June 2026 snapshot, so nothing is left to cover demand. The forecast exists: 100 kg-equivalent per month for each of the 24 months from July 2026 to June 2028. The item is STANDARD type, so no BULK stock was left out. Coverage is in months and is measured in quantity (kg-equivalent). | **correct** | numeric pass (expected 0.0 given); analysis_month_named pass (named); no_aggregated_coverage pass (no added or averaged coverage); routing pass (semantic_view) |
| CS_LAST_MONTH_GAP | system_agentic_semantic_context, system_execute_sql, system_execute_sql, system_execute_sql | Closing stock of Oat cereal bar 1 kg (SKU-H11) in Switzerland for Q2 2026 is 0 kg equivalent. Closing stock for a quarter is the stock of its last month, June 2026, and this SKU has no stock row for Switzerland in June 2026. It did hold stock earlier in the quarter: 400 kg equivalent in April and 350 kg equivalent in May. So it had stock during Q2 and none at the end, which closes at 0. | **manual** | numeric manual (expected 0.0 and wrong value(s) ['last_known_value'] both given); routing pass (semantic_view) |

**CS_LAST_MONTH_GAP is manual, for the owner**: the answer gives 0 as the closing stock and cites May's 350 as the
history ("400 kg equivalent in April and 350 kg equivalent in May ... none at the end, which closes at 0"); the
rubric makes an answer carrying both the expected value and a declared wrong value manual.

Grader correction made on these real answers (no rubric change): the horizon's month count is also excluded when
written "the 24 months that follow it" (an integer equal to the horizon, unless introduced by "coverage is", "covers"
or "lasts"). T6 was first graded wrong on it, like B2's T6. `tests/test_grade.py`: 36. B2's four grades are unchanged
after the correction.

Per call (`records.py`):

| Label | Request id | Started (UTC) | Client s | First byte s | Version served | Orchestration input (cache write / read), output | Server s | Before planning s | Planning s (steps) | Context s | SQL tool s | Skill/code s | Response s | Suggested s | Computed by | Queries of the turn: elapsed ms (queued provisioning / overload ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b1_t1 | `0000013d-0000-4000-8000-00000000013d` | 07:35:00.075 | 15.84 | 2.21 | VERSION$2 | 112,273 (34,633 / 77,628), out 1,007 | 14.55 | 1.28 | 6.89 (2) | 0.19 | 2.01 | 0 | 3.06 | 2.11 | model | 380 (0 / 0) agent SQL; 451 (0 / 0) agent SQL; 185 (0 / 0) |
| b1_t6 | `00000140-0000-4000-8000-000000000140` | 07:36:23.673 | 5.75 | 1.03 | VERSION$2 | 33,503 (3,566 / 29,929), out 243 | 4.79 | None | 0 (0) | 0 | 0 | 0 | 2.8 | 1.76 | n/a (no tool) | none |
| b1_t9 | `00000141-0000-4000-8000-000000000141` | 07:37:39.418 | 15.23 | 1.02 | VERSION$2 | 113,697 (20,985 / 92,700), out 1,104 | 14.19 | 0.22 | 7.01 (2) | 0.06 | 1.43 | 0 | 3.46 | 2.46 | model | 227 (0 / 0) agent SQL; 281 (0 / 0) agent SQL; 185 (0 / 0) |
| b1_cs_last_month_gap | `00000013-0000-4000-8000-000000000013` | 07:39:01.703 | 21.48 | 1.07 | VERSION$2 | 176,488 (20,924 / 155,548), out 1,154 | 20.39 | 0.28 | 12.59 (4) | 0.06 | 2.64 | 0 | 2.55 | 2.25 | n/a | 257 (0 / 0) agent SQL; 127 (0 / 0) agent SQL; 269 (0 / 0) agent SQL |

SQL the agent wrote (from the tool calls):

**T1 statement 1**

```sql
SELECT f.forecast_month, SUM(f.forecast_qty_eq) AS fq FROM __fc f JOIN __item i ON f.item_id=i.item_id JOIN __geo g ON f.country_id=g.country_id WHERE i.family_code='PANTRY_FLOUR' AND g.country_code='FR' AND f.forecast_month>'2026-06-01' AND f.forecast_month<='2028-06-01' GROUP BY f.forecast_month ORDER BY f.forecast_month
```

**T1 statement 2**

```sql
SELECT i.item_type, SUM(s.stock_qty_eq) AS stock FROM __stock s JOIN __item i ON s.item_id=i.item_id JOIN __geo g ON s.country_id=g.country_id WHERE i.family_code='PANTRY_FLOUR' AND g.country_code='FR' AND s.snapshot_month='2026-06-01' GROUP BY i.item_type
```

**T9 statement 1**

```sql
SELECT f.forecast_month, i.sku_name, i.item_type, SUM(f.forecast_qty_eq) AS q FROM __fc AS f JOIN __item AS i ON f.item_id=i.item_id JOIN __geo AS g ON f.country_id=g.country_id WHERE i.sku_code='SKU-H11' AND g.country_code='CH' AND f.forecast_month > '2026-06-01' AND f.forecast_month <= '2028-06-01' GROUP BY 1,2,3 ORDER BY 1
```

**T9 statement 2**

```sql
SELECT i.sku_name, i.item_type, SUM(s.stock_qty_eq) AS stock FROM __stock AS s JOIN __item AS i ON s.item_id=i.item_id JOIN __geo AS g ON s.country_id=g.country_id WHERE i.sku_code='SKU-H11' AND g.country_code='CH' AND s.snapshot_month='2026-06-01' GROUP BY 1,2
```

**CS_LAST_MONTH_GAP statement 1**

```sql
SELECT i.sku_code, i.sku_name, g.country_code, SUM(s.stock_qty_eq) AS q, SUM(s.stock_value_eur) AS v FROM __stock s JOIN __item i ON s.item_id=i.item_id JOIN __geo g ON s.country_id=g.country_id WHERE i.sku_code ILIKE '%H11' AND g.country_code='CH' AND s.snapshot_month='2026-06-01' GROUP BY 1,2,3
```

**CS_LAST_MONTH_GAP statement 2**

```sql
SELECT DISTINCT sku_code, sku_name, family_code, item_type FROM __item WHERE sku_name ILIKE '%oat%' OR sku_name ILIKE '%bar%' OR sku_code ILIKE '%H11%'
```

**CS_LAST_MONTH_GAP statement 3**

```sql
SELECT s.snapshot_month, g.country_code, SUM(s.stock_qty_eq) AS q FROM __stock s JOIN __item i ON s.item_id=i.item_id JOIN __geo g ON s.country_id=g.country_id WHERE i.sku_code='SKU-H11' AND g.country_code='CH' AND s.snapshot_month>='2026-01-01' GROUP BY 1,2 ORDER BY 1
```

Reading [measured]:
- **The view's native defects are bypassed, not met.** The agent never selected `stock_qty` (NON ADDITIVE BY) nor
  `c01..c24`: every statement filters `snapshot_month = '2026-06-01'` on the stock rows and lists the monthly forecast
  of July 2026 to June 2028, then the model computes the cascade in its answer. With the month written as an equality,
  the carried last value of `NON ADDITIVE BY` (350 at the object level) never arises: T9 0, CS_LAST_MONTH_GAP 0 (with
  May's 350 cited as history). H-B1-1 holds in its first branch (right when the model writes the cascade itself);
  H-B1-4 refuted on the smoke for both questions.
- T6: no tool call, asks for the month, lists the available months and offers a series with BULK excluded: section 8
  (charter version 2) is followed. H-B1-6 refuted on the smoke.
- T1 states the default scope ("STANDARD stock only ... no BULK stock ... so none was left out"), as section 8 asks.
- Orchestration input 112,000 to 176,000 tokens per tool turn, 33,500 without (B2: 150,000 to 293,000); turns 15.2 to
  21.5 s with a tool (B2: 14.9 to 32.4), 5.8 s without. Queued provisioning and overload 0 on every query.
- Version served: `VERSION$2` on every span.

Budget s8: 10 of 34 used.

## Step 4 preparation: the linkml-coverage skill and the D and D′ specs (not uploaded, no agent)

- `skill/linkml-coverage/coverage.py`: the algorithm of DEFINITION.md section 2, written from the definition (no copy
  or import of `data/coverage_ref.py`, asserted by a test); horizon t+1..t+24, a month with no forecast counted as 0;
  inputs either passed as numbers (D) or read by the script with the sandbox's connection from two SELECT statements
  (D′). `tests/test_skill_coverage.py` (11): the worked example 8.5, T1 2.8, T2 7.0, BEYOND_H 50.0, zero and null stock
  0, no forecast null, exact depletion 3.0, a zero month before depletion counted as covered, all computed by hand.
- `skill/linkml-coverage/SKILL.md`: description with negative scope (not for closing stock, stock levels or forecast);
  a fast path (decide the month, unit and level first; fetch the two inputs once; run the script once); the two input
  modes by toolset; the RAW tables and their columns (schema facts only, no rule); the script's output.
- `d/build_specs.py` writes `d/agent_d.yaml` and `d/agent_dp.yaml`: instructions DEFINITION.md sections 1, 2, 3, 7 and
  8 verbatim (6,156 characters), the common response, the skill on the agent's own stage, the B2 semantic view tool
  with B2's description less its claim on coverage and routed to the skill (otherwise the two would compete), D
  `code_execution` (40,000 tokens), D′ `code_toolset_all` (160,000 tokens), `permission_policy: always_ask` on both.
- `run_call.py` policy `dp`: a bash command is approved only when it is exactly a run of the skill's `coverage.py`
  with its own flags; any other command, operator or redirection is denied (`tests/test_run_call_policy.py`, 12).

## Step 4: D′ (LINKML_DP), stopped after its smoke

- Stage `SKILLS_DP` (`d/stage_skill.py`): `CREATE STAGE` `00000299-0000-4000-8000-000000000299`; PUT `SKILL.md`
  (`<query-id>`) and `coverage.py` (`0000029a-0000-4000-8000-00000000029a`), `AUTO_COMPRESS = FALSE`; LIST: the two
  names, parity with the repository true.
- `CREATE AGENT LINKML_DP` `0000029b-0000-4000-8000-00000000029b`, five-beat cycle (MODIFY LIVE `<query-id>`, COMMIT
  `<query-id>`, ADD LIVE `<query-id>`, SET DEFAULT_VERSION = 'VERSION$2' `0000029c-0000-4000-8000-00000000029c`); every
  version equal to `d/agent_dp.yaml`; OWNERSHIP to LINKML_METRICS_ROLE only. Beat 5 is call 11 (T1).
- Smoke, policy `dp`, as LINKML_SVC, warehouse warm before each question. **UTC window: 2026-10-04 08:05:15.2 (call
  11 sent) to 08:12:47.8 (call 17 answered).** 7 calls (11 to 17), all status 200: 5 questions and **2 approval
  resumes** (T1 call 12, T9 call 14 then 15), each the exact script command approved by rule `dp` ("Allow this
  command"); no command denied, no other approval asked.

| Id | Tool calls | Answer (verbatim) | Grade | Criteria (eval/grade.py) |
|---|---|---|---|---|
| T1 | skill, system_agentic_semantic_context, bash | The stock coverage of Flour and baking in France as of June 2026 is **2.8 months**.  - **Stock:** 1,400 kg/L equivalent on hand in June 2026. - **Forecast:** 500 kg/L equivalent per month over July 2026 to June 2028. With no replenishment, the stock runs out within the horizon. - **Scope:** STANDARD items only, which is the default for coverage. BULK items carry stock but have no forecast, so I left them out. All lot statuses are included. | **correct** | numeric pass (expected 2.8 given); analysis_month_named pass (named); no_aggregated_coverage pass (no added or averaged coverage); routing pass (skill (with ['semantic_view'])) |
| T6 | skill | Stock coverage is calculated from the stock at one analysis month, so I need a single month. "The whole year 2026" is a period, and I can't average or add coverages across months.  Which month do you want as the analysis month? The latest stock snapshot is June 2026 (2026-06-01). You could also pick another month in 2026, such as January or December. I can also give you one coverage figure per month of 2026 if you'd like.  For flour and baking in France, I'll use quantity in kg or litre equivalents unless you tell me you want value instead. | **wrong** | refusal pass (no number; asks for the month or refuses with a reason); no_aggregated_coverage pass (no added or averaged coverage); routing fail (tool(s) used where none was expected: ['skill']) |
| T9 | skill, bash, snowflake_sql_execute | The stock coverage of oat cereal bar 1 kg (SKU-H11) in Switzerland as of June 2026 is **0 months**.  - **Stock:** the June 2026 snapshot shows 0 units. It was 350 in May and 400 in April. - **Demand:** the forecast is 100 units a month for each of the 24 months from July 2026 to June 2028, with no months missing. - **Unit:** quantity equivalent, not value.  With no stock on hand, nothing covers the forecast demand. | **correct** | numeric pass (expected 0.0 given); analysis_month_named pass (named); no_aggregated_coverage pass (no added or averaged coverage); routing pass (skill (with ['sandbox_sql'])) |
| CS_LAST_MONTH_GAP | system_agentic_semantic_context, snowflake_sql_execute | (no answer: the turn ended waiting for client action) | **manual** | numeric manual (no candidate number); routing pass (semantic_view (with ['sandbox_sql'])) |
| G1 | system_agentic_semantic_context, snowflake_sql_execute | (no answer: the turn ended waiting for client action) | **manual** | numeric manual (no candidate number); routing pass (semantic_view (with ['sandbox_sql'])) |

Approvals (verbatim command, decision): call 11 `cd /mnt/skills/stage/linkml_metrics_raw_skills_dp/skills/linkml-coverage/
&& python3 coverage.py --as-of 2026-06-01 --stock-sql "SELECT SUM(s.stock_qty_eq) FROM ...FCT_STOCK_SNAPSHOT_GAPFILLED s
JOIN ...DIM_ITEM i ... WHERE s.snapshot_month='2026-06-01' AND i.family_name='Flour and baking' AND g.country_code='FR'
AND i.item_type='STANDARD'" --forecast-sql "SELECT f.forecast_month, SUM(f.forecast_qty_eq) FROM ...FCT_FORECAST f ...
WHERE f.forecast_month BETWEEN '2026-07-01' AND '2028-06-01' ... GROUP BY 1 ORDER BY 1"`, Allow this command (resume =
call 12); call 14 the same shape for SKU-H11 x Switzerland, Allow this command (resume = call 15). The platform
classified the bash command `RISK_LEVEL_MEDIUM` ("Command not on cortex-managed allow or high-risk list"); the skill
load and `snowflake_sql_execute` `RISK_LEVEL_NONE`, no approval.

Identity of the script's queries (`d/identity_check.py`, QUERY_HISTORY_BY_USER read as LINKML_SVC):

| Label | Query id | User | Role | Secondary roles in session | Warehouse | Query (start) |
|---|---|---|---|---|---|---|
| dp_t1 | `0000015e-0000-4000-8000-00000000015e` | LINKML_SVC | LINKML_METRICS_ROLE | n/a | LINKML_METRICS_WH | SELECT SUM(s.stock_qty_eq) FROM LINKML_METRICS.RAW.FCT_STOCK |
| dp_t1 | `0000015f-0000-4000-8000-00000000015f` | LINKML_SVC | LINKML_METRICS_ROLE | n/a | LINKML_METRICS_WH | SELECT f.forecast_month, SUM(f.forecast_qty_eq) FROM LINKML_ |
| dp_t9 | `00000162-0000-4000-8000-000000000162` | LINKML_SVC | LINKML_METRICS_ROLE | n/a | LINKML_METRICS_WH | select sum(s.stock_qty_eq) from LINKML_METRICS.RAW.FCT_STOCK |
| dp_t9 | `00000163-0000-4000-8000-000000000163` | LINKML_SVC | LINKML_METRICS_ROLE | n/a | LINKML_METRICS_WH | select f.forecast_month, sum(f.forecast_qty_eq) from LINKML_ |

4 script queries, 0 not as LINKML_SVC / LINKML_METRICS_ROLE / LINKML_METRICS_WH

Per call (`records.py`; the span split is empty under `code_toolset_all`, whose spans are named differently, and the
two calls of T1 and of T9 share one trace file):

| Label | Request id | Started (UTC) | Client s | First byte s | Version served | Orchestration input (cache write / read), output | Server s | Before planning s | Planning s (steps) | Context s | SQL tool s | Skill/code s | Response s | Suggested s | Computed by | Queries of the turn: elapsed ms (queued provisioning / overload ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dp_t1 | `00000017-0000-4000-8000-000000000017` | 08:05:15.247 | 24.08 | 2.1 | VERSION$2 | 235,917 (97,641 / 138,268), out 835 | 0 | None | 0 (0) | 0.7 | 0 | 41.84 | 0 | 0 | tool (skill script) | 124 (0 / 0); 257 (0 / 0); 150 (0 / 0) |
| dp_t1 | `0000015d-0000-4000-8000-00000000015d` | 08:05:39.321 | 19.01 | 1.89 | VERSION$2 | 99,574 (29,602 / 69,970), out 171 | 0 | None | 0 (0) | 0.7 | 0 | 41.84 | 0 | 0 | tool (skill script) | 116 (0 / 0); 102 (0 / 0); 282 (0 / 0); 766 (0 / 0); 288 (0 / 0) |
| dp_t6 | `00000160-0000-4000-8000-000000000160` | 08:07:42.048 | 14.73 | 1.88 | VERSION$2 | 138,278 (1,526 / 136,746), out 257 | 0 | None | 0 (0) | 0 | 0 | 13.83 | 0 | 0 | model | 125 (0 / 0); 114 (0 / 0); 215 (0 / 0) |
| dp_t9 | `0000029d-0000-4000-8000-00000000029d` | 08:09:08.232 | 16.85 | 2.52 | VERSION$2 | 138,312 (1,543 / 136,763), out 685 | 0 | None | 0 (0) | 0 | 0 | 38.85 | 0 | 0 | tool (skill script) | 126 (0 / 0); 225 (0 / 0); 258 (0 / 0) |
| dp_t9 | `00000161-0000-4000-8000-000000000161` | 08:09:25.146 | 23.51 | 2.43 | VERSION$2 | 143,769 (2,238 / 141,527), out 514 | 0 | None | 0 (0) | 0 | 0 | 38.85 | 0 | 0 | tool (skill script) | 272 (0 / 0); 345 (0 / 0); 241 (0 / 0); 336 (0 / 0); 158 (0 / 0); 40 (0 / 0); 62 (0 / 0); 532 (0 / 0) |
| dp_cs_last_month_gap | `00000159-0000-4000-8000-000000000159` | 08:11:05.657 | 17.04 | 1.88 | VERSION$2 | 164,633 (27,864 / 136,763), out 459 | 0 | None | 0 (0) | 0.12 | 0 | 17.9 | 0 | 0 | n/a | 98 (0 / 0); 122 (0 / 0); 212 (0 / 0) |
| dp_g1 | `0000015b-0000-4000-8000-00000000015b` | 08:12:32.779 | 14.97 | 1.88 | VERSION$2 | 164,621 (27,862 / 136,753), out 360 | 0 | None | 0 (0) | 0.14 | 0 | 14.41 | 0 | 0 | n/a | 117 (0 / 0); 126 (0 / 0); 215 (0 / 0) |

**Why D′ stopped [measured]:** on CS_LAST_MONTH_GAP and G1 the agent read the B2 semantic context, then sent the
semantic view's SQL as a `snowflake_sql_execute` tool use with **`client_side_execute: true`** (description
"Executing SQL query from semantic model b2_semantic_view"); the stream ended on status `client_tool_use_request`
("Waiting for client action") with no text. Under `code_toolset_all`, the semantic view tool's SQL is a client-side
tool: the caller must run it and return the result. `run_call.py` handles permission requests, not client-side tool
execution, so both turns ended without an answer. Two smoke calls without an answer: the configuration's stop
condition. No re-run. By contrast the sandbox's own `snowflake_sql_execute` on T9 ran server-side
(`client_side_execute: false`). [measured]

Other observations [measured]:
- Coverage computed by the skill script on T1 (2.8) and T9 (0): the script read the data itself, under LINKML_SVC,
  LINKML_METRICS_ROLE, LINKML_METRICS_WH (4 queries of 4).
- The extraction queries the model wrote read `FCT_STOCK_SNAPSHOT_GAPFILLED` (seen in B2's semantic context) rather
  than the base `FCT_STOCK_SNAPSHOT` the skill lists: the charter's "the script reads the RAW base tables" holds for
  the schema, not for the table; on T9 that view gives 0 either way.
- T6: the model loaded the skill, read "ask which month and stop", and asked, with no data tool; the rubric counts the
  skill load as a tool on a clarify question: **wrong by rule (routing)**, the answer itself passes the refusal
  criterion. For the owner.
- Orchestration input about 99,000 to 236,000 tokens per call (the bundled catalogue), within the 160,000 budget per
  step as far as the totals show; 14.7 to 24.1 s per call, a sandbox provisioned on every call.

Budget s8: 17 of 34 used (D′ 7: 5 questions, 2 resumes, within its share of 10).

### D′ after the owner's decisions (2026-10-04)

**Client-side execution, documentation.** The Cortex Agents Run API page
(https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-run) documents the `client_side_execute`
field of `response.tool_use` ("Whether the tool use is executed on the client side") and `tool_result` among the
`MessageContentItem` types a request may carry (`ToolResult`: `tool_use_id`, `type`, `name`, `content`, `status`).
It does not narrate the client-side loop, nor the status `client_tool_use_request` ("Waiting for client action"); the
Coding Agent page names `snowflake_sql_execute` (read-only SELECT and SHOW) and the `permission_decision` resume, not
client-side execution. [documented, partly: the field and the content type; the loop is measured]

**Why T9's `snowflake_sql_execute` did not block.** Two different uses of the same tool name [measured]: on T9 the
model called the sandbox's own SQL tool for a check of its own (input `description` + `sql`, `client_side_execute:
false`): it ran server-side in the sandbox and returned rows. On CS_LAST_MONTH_GAP and G1 the call carried the
semantic view tool's SQL (input `semantic_model: b2_semantic_view`, description "Executing SQL query from semantic model
b2_semantic_view", `client_side_execute: true`): under `code_toolset_all`, the semantic view tool's statement is handed
to the client.

**The client** (`snowflake/probe_b/mount/client_sql.py`, `run_call.py --client-sql`, tests first: 16): executes a
client-side `snowflake_sql_execute` only if it is exactly one SELECT or WITH statement, on the `linkml_svc` connection
after `USE SECONDARY ROLES NONE`, at most 1,000 rows; everything else is refused and the error returned to the agent;
the result goes back as a `tool_result` in the shape the sandbox's tool returns (text: row count, header, CSV rows);
every statement, status and query id logged (`client_sql.jsonl`). Budget s8 raised from 34 to 38.

Re-runs (calls 18 to 21; UTC 2026-10-04 08:23:19.0 to 08:25:30.8; each question then one client resume):

| # | Label | Tool | Status | Query id | Result returned |
|---|---|---|---|---|---|
| 18 | dp_cs_last_month_gap_r | snowflake_sql_execute | success | `0000029e-0000-4000-8000-00000000029e` | 1 row(s) returned. /  / SKU_CODE,SKU_NAME,LIFECYCLE_STATUS,COUNTRY_CODE,CLOSING_STOCK_QTY_EQ,CLOSING_STOCK_VALUE /  / SKU-H11,Oa |
| 20 | dp_g1_r | snowflake_sql_execute | success | `0000029f-0000-4000-8000-00000000029f` | 1 row(s) returned. /  / FAMILY_CODE,COUNTRY_CODE,FORECAST_QTY_EQ /  / BEV_JUICE,FR,6416.0000 |

| Id | Tool calls | Answer (verbatim) | Grade | Criteria |
|---|---|---|---|---|
| CS_LAST_MONTH_GAP | system_agentic_semantic_context, snowflake_sql_execute | The closing stock of Oat cereal bar 1 kg (SKU-H11) in Switzerland for Q2 2026 was **0 kg**, with a stock value of €0.  I took the June 2026 snapshot, since closing stock for a quarter is the snapshot of its last month. The item's lifecycle status is ACTIVE.  The stock table is gap-filled, so a zero means either that there was no stock in June or that no snapshot was recorded for that month. I didn't check which. | **correct** | numeric pass (expected 0.0 given); routing pass (semantic_view (with ['sandbox_sql'])) |
| G1 | system_agentic_semantic_context, snowflake_sql_execute | The demand forecast for fruit juice (family BEV_JUICE) in France for September 2026 is **6,416 kg or L equivalent**.  I ran this query directly against the underlying tables rather than through the semantic view tool. It used the same logic as the view's verified forecast query: forecast quantity summed for the family, country FR and month 2026-09-01. | **correct** | numeric pass (expected 6416.0 given); routing pass (semantic_view (with ['sandbox_sql'])) |

| Label | Request id | Started (UTC) | Client s | First byte s | Version served | Orchestration input (cache write / read), output | Server s | Before planning s | Planning s (steps) | Context s | SQL tool s | Skill/code s | Response s | Suggested s | Computed by | Tables read by the script | Queries of the turn: elapsed ms (queued provisioning / overload ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dp_cs_last_month_gap_r | `000002a0-0000-4000-8000-0000000002a0` | 08:23:19.027 | 16.86 | 1.86 | VERSION$2 | 164,639 (96,195 / 68,438), out 471 | 0 | None | 0 (0) | 0.12 | 0 | 28.41 | 0 | 0 | n/a | n/a | 115 (0 / 0); 110 (0 / 0); 227 (0 / 0) |
| dp_cs_last_month_gap_r | `0000015a-0000-4000-8000-00000000015a` | 08:23:36.921 | 12.69 | 1.75 | VERSION$2 | 96,983 (28,457 / 68,524), out 160 | 0 | None | 0 (0) | 0.12 | 0 | 28.41 | 0 | 0 | n/a | n/a | 109 (0 / 0); 202 (0 / 0); 229 (0 / 0) |
| dp_g1_r | `000002a1-0000-4000-8000-0000000002a1` | 08:25:00.137 | 14.97 | 2.32 | VERSION$2 | 164,621 (27,862 / 136,753), out 360 | 0 | None | 0 (0) | 0.12 | 0 | 26.47 | 0 | 0 | n/a | n/a | 119 (0 / 0); 114 (0 / 0); 286 (0 / 0) |
| dp_g1_r | `0000015c-0000-4000-8000-00000000015c` | 08:25:16.894 | 13.88 | 1.74 | VERSION$2 | 96,722 (28,204 / 68,516), out 179 | 0 | None | 0 (0) | 0.12 | 0 | 26.47 | 0 | 0 | n/a | n/a | 105 (0 / 0); 98 (0 / 0); 229 (0 / 0) |

Both re-runs keep the first runs (calls 16 and 17, no answer) in the record. Both statements ran as LINKML_SVC (the
client's own connection). G1's answer says "I ran this query directly against the underlying tables rather than
through the semantic view tool": the statement is the semantic view tool's expansion over the base objects and
`B2_ITEM`, run by the client. CS's answer adds a caveat ("a zero means either that there was no stock in June or that
no snapshot was recorded ... I didn't check which"). [measured]

**Rubric version 2** (owner): a skill-type tool call (loading instructions, no data) is not a tool in the routing
criterion. Regrade: D′ T6 wrong to **correct**; B2 and B1 unchanged (8 of 8 correct, B1 CS by the manual decision).
Not graded, recorded: D′ T6 offers "another month in 2026, such as January or December"; December 2026 has no stock
snapshot (the latest is June 2026).

**D′ smoke, final**: T1 correct (skill script), T6 correct (rubric v2), T9 correct (skill script), CS_LAST_MONTH_GAP
and G1 correct on the re-runs with client-side execution (no answer on the first runs). Calls 11 to 21: 11 calls
(5 questions, 2 approval resumes, 2 re-runs, 2 client resumes).

Budget s8: 21 of 38 used.

## Step 5: D (LINKML_D, code_execution)

- Spec `d/agent_d.yaml` regenerated at charter version 4 (DEFINITION.md sections 1, 2, 3, 7 and 8 verbatim, unit
  sentence on coverage and closing stock); `d/agent_dp.yaml` regenerated too, while LINKML_DP still serves the version
  3 text (republished by one cycle, no call, before the campaign, with B1).
- Stage `SKILLS_D`: CREATE `000002a2-0000-4000-8000-0000000002a2`, PUT `SKILL.md` `<query-id>` and `coverage.py`
  `000002a3-0000-4000-8000-0000000002a3`, name parity true.
- `CREATE AGENT LINKML_D` `000002a4-0000-4000-8000-0000000002a4`; five-beat cycle: MODIFY LIVE `<query-id>`, COMMIT
  `000002a5-0000-4000-8000-0000000002a5`, ADD LIVE `<query-id>`, SET DEFAULT_VERSION = 'VERSION$2' `<query-id>`;
  every version equal to the file. Beat 5 is call 22 (T1).
- Smoke, policy `dp` with `--client-sql` available, as LINKML_SVC, warehouse warm before each question. **UTC
  window: 2026-10-04 08:28:05.0 (call 22 sent) to 08:34:26.5 (call 26 answered).** 5 calls (22 to 26), all status
  200; **no approval asked** (`code_execution`, as probe D), **no client-side tool use** (the semantic view's SQL ran
  server-side through `system_execute_sql`, unlike D′).

| Id | Tool calls | Answer (verbatim) | Grade | Criteria (eval/grade.py, rubric v2) |
|---|---|---|---|---|
| T1 | system_agentic_semantic_context, server_skill, system_execute_sql, system_execute_sql, bash | Flour and baking in France had **2.8 months** of stock coverage as of June 2026. The figure is in quantity-equivalent units (kg or L equivalent) and uses STANDARD items only. It compares 1,400 of stock at the end of June 2026 with a forecast of 500 a month for July 2026 to June 2028. The stock runs out within that 24-month window. There was no BULK stock for this family in France in June 2026, so none was excluded. | **correct** | numeric pass (expected 2.8 given); analysis_month_named pass (named); no_aggregated_coverage pass (no added or averaged coverage); routing pass (skill (with ['semantic_view'])) |
| T6 | none | Coverage needs one analysis month, and "the whole year 2026" is a period, so I can't pick a month for you.  Which month of 2026 do you mean? The latest stock snapshot is June 2026. The analysis months run from July 2023 to June 2026, so the 2026 months available are January to June.  I can also give a series with one coverage value per month, for example January to June 2026. Coverage can't be totalled or averaged across months. I'll use flour and baking in France, STANDARD items only, in quantity equivalent unless you want value. | **correct** | refusal pass (no number; asks for the month or refuses with a reason); no_aggregated_coverage pass (no added or averaged coverage); routing pass (no tool call) |
| T9 | system_agentic_semantic_context, server_skill, system_execute_sql, system_execute_sql | The stock coverage of Oat cereal bar 1 kg (SKU-H11) in Switzerland as of June 2026 is 0 months. The unit is quantity equivalent (kg or L). The item has no stock on hand at the June 2026 snapshot (0), and the coverage rule sets coverage to 0 when stock is 0. The forecast for July 2026 to June 2028 is 100 per month, so it is not a case of missing demand. The coverage script in the skill file is empty, so I applied the rule directly instead of running it. The item is STANDARD, so no BULK stock was excluded. | **wrong** | numeric pass (expected 0.0 given); analysis_month_named pass (named); no_aggregated_coverage pass (no added or averaged coverage); routing fail (expected skill, used ['semantic_view']) |
| CS_LAST_MONTH_GAP | system_agentic_semantic_context, system_execute_sql | The closing stock of Oat cereal bar 1 kg (SKU-H11) in Switzerland for Q2 2026 was 0 kg equivalent, and its value was 0 EUR. I read it from the June 2026 snapshot, the last month of the quarter. The figure counts every item type and all batches and warehouses in Switzerland. A SKU with no snapshot in a quarter's last month closes at 0, so the SKU had no stock at the end of June. | **correct** | numeric pass (expected 0.0 given); routing pass (semantic_view) |
| G1 | system_agentic_semantic_context, system_execute_sql | The demand forecast for fruit juice (family BEV_JUICE) in France for September 2026 is 6,416 kg or L equivalent. That figure is the total quantity-equivalent forecast across all fruit juice items in France for that month. | **correct** | numeric pass (expected 6416.0 given); routing pass (semantic_view) |

Grader correction on these real answers (no rubric change): a year followed by "months" ("the 2026 months available
are January to June") is not a coverage; T6 was first graded wrong on it. `tests/test_grade.py`: 39. Every earlier
grade is unchanged.

Per call (`records.py`):

| Label | Request id | Started (UTC) | Client s | First byte s | Version served | Orchestration input (cache write / read), output | Server s | Before planning s | Planning s (steps) | Context s | SQL tool s | Skill/code s | Response s | Suggested s | Computed by | Tables read by the script | Queries of the turn: elapsed ms (queued provisioning / overload ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| d_t1 | `00000016-0000-4000-8000-000000000016` | 08:28:05.024 | 25.27 | 2.3 | VERSION$2 | 205,886 (50,410 / 155,462), out 1,394 | 19.07 | 1.41 | 10.88 (3) | 0.1 | 2.02 | 0.64 | 2.88 | 2.23 | tool (skill script) | n/a | 95 (0 / 0); 184 (0 / 0); 109 (0 / 0); 252 (0 / 0); 100 (0 / 0); 295 (0 / 0) agent SQL; 438 (0 / 0) agent SQL |
| d_t6 | `00000155-0000-4000-8000-000000000155` | 08:29:50.716 | 10.59 | 1.24 | VERSION$2 | 33,013 (3,961 / 29,044), out 184 | 4.54 | None | 0 (0) | 0 | 0 | 0 | 2.56 | 1.61 | n/a (no tool) | n/a | 105 (0 / 0); 563 (0 / 0); 119 (0 / 0); 268 (0 / 0) |
| d_t9 | `00000156-0000-4000-8000-000000000156` | 08:31:07.853 | 24.8 | 1.27 | VERSION$2 | 158,401 (36,651 / 121,738), out 1,371 | 18.53 | 0.38 | 8.26 (2) | 0.12 | 3.85 | 0.32 | 4.96 | 2.67 | model | n/a | 106 (0 / 0); 182 (0 / 0); 253 (0 / 0); 113 (0 / 0); 97 (0 / 0); 460 (0 / 0) agent SQL; 292 (0 / 0) agent SQL |
| d_cs_last_month_gap | `0000014f-0000-4000-8000-00000000014f` | 08:32:43.054 | 19.17 | 1.62 | VERSION$2 | 149,748 (33,099 / 116,637), out 747 | 12.67 | 0.4 | 5.77 (2) | 0.11 | 1.07 | 0 | 2.94 | 2.37 | n/a | n/a | 102 (0 / 0); 118 (0 / 0); 269 (0 / 0); 405 (0 / 0) agent SQL |
| d_g1 | `00000151-0000-4000-8000-000000000151` | 08:34:09.447 | 17.06 | 1.32 | VERSION$2 | 149,071 (32,727 / 116,332), out 584 | 10.91 | 0.4 | 4.82 (2) | 0.65 | 1.05 | 0 | 1.77 | 2.2 | n/a | n/a | 103 (0 / 0); 140 (0 / 0); 282 (0 / 0); 287 (0 / 0) agent SQL |

Reading [measured]:
- **T1, D works as designed, with the model typing the inputs**: the agent fetched the stock (1,400) and the 24 monthly
  forecasts through B2's tool, then ran the script with the forecast list built by a nested `python3 -c` that writes
  500 for each of 24 months: the numbers went through the model, as D's design says. Under `code_execution` the bash
  command was not the exact script command, and none was asked for approval, so the `dp` rule was never applied.
- **T9, the script did not run**: the server-side skill load listed `coverage.py` with size **0 B**, the model
  concluded "The coverage script in the skill file is empty, so I applied the rule directly instead of running it"
  (its reasoning: "rather than pretend to execute an empty script"), and gave 0 by the rule. Right number, wrong route
  by the rubric (the skill's script never ran). Probe D recorded the same 0 B listing for a script that ran; on T1 the
  same listing did not stop the model. H-D-1 open; a routing failure H-D did not name.
- T6: no tool, asks for the month, lists January to June 2026, offers a series, states QTY_EQ by default (section 8).
- CS_LAST_MONTH_GAP and G1 routed to B2's tool: H-D-3 confirmed on the smoke.
- Orchestration input 149,000 to 206,000 tokens per tool turn, 33,000 without; 17.1 to 25.3 s per tool turn.

Budget s8: 26 of 38 used.

## Owner's checks before A (2026-10-04, no agent call)

- **Charter version 5.** DEFINITION.md's internal references (session decisions, `data/traps.yaml` and trap names,
  `CLOSING_STOCK`, `LAST_PERIOD`, `beyond_horizon`) moved to "Provenance:" lines that the extraction drops
  (`definition_text.py`); `tests/test_extracted_instructions.py` (7): no instruction of A, B1, B2, D or D′ carries
  "session", "traps", a trap id or those names, and the extracted specs do not drift. A's instructions: 3,448
  characters (3,794 before). The compiler states the default unit for every figure; B2's generated sentence: "Every
  figure, coverage, closing stock and forecast alike, is given in QTY_EQ (kg or L equivalent) unless the user asks for
  VALUE (EUR)." (`gen_agent.default_unit_sentence`; `agent_c.yaml` unchanged until session 8b).
- **D's stage** (`LIST @SKILLS_D`, `000002a6-0000-4000-8000-0000000002a6`): `SKILL.md` 3,136 B and `coverage.py`
  4,672 B, the repository's 3,121 B and 4,669 B; the PUT itself reported source 3,121 to target 3,136 and 4,669 to
  4,672, so the difference is made at upload; the LIST md5 values are those of the encrypted stage files and do not
  compare with the repository's. The server-side skill load nevertheless listed `coverage.py` at 0 B (T9). [measured]
- **D, T1: `coverage.py` ran.** Command: `cd /mnt/skills/stage/linkml_metrics_raw_skills_d/skills/linkml-coverage &&
  python3 coverage.py --as-of 2026-06-01 --stock 1400 --forecast "$(python3 -c "...for i in range(24):
  out.append([f'{y}-{mo:02d}-01',500]) ...")"`. Output: `{"analysis_month": "2026-06-01", "horizon": ["2026-07-01",
  "2028-06-01"], "stock": 1400.0, "forecast_by_month": [500.0, ... 24 values], "months_without_forecast_counted_as_0":
  0, "coverage_months": 2.8, "case": "depleted within the horizon", "queries": null}`: the script's own keys. The model
  wrote only the generator of the `--forecast` argument (24 times 500, the values it had read). "Computed by: tool
  (skill script)" stands. No change to D's skill or instructions (owner decides).
- **D′, G1 re-run**: the answer says it queried the tables "rather than through the semantic view tool". The tool call
  was `snowflake_sql_execute` with `semantic_model: b2_semantic_view` and description "Executing SQL query from semantic
  model b2_semantic_view", `client_side_execute: true`: the semantic view tool's own SQL (its expansion over
  `FCT_FORECAST`, `B2_ITEM` and `DIM_GEO`), run by the client. The answer's account of its route is inaccurate; the
  grade is unchanged. [measured]

### Republications before the campaign (one publish cycle each, no agent call), kept up to date

| Agent | Why | Status |
|---|---|---|
| LINKML_B1 | charter version 4: section 8's unit sentence (hand-written B1 prose gains it); version 5 has no effect on B1 (no internal reference in its prose) | **done**: `VERSION$3` default, MODIFY LIVE `000002a7-0000-4000-8000-0000000002a7`, COMMIT `<query-id>`, ADD LIVE `000002a8-0000-4000-8000-0000000002a8`, SET DEFAULT `<query-id>`; LIVE and `VERSION$3` equal to `b1/agent_b1.yaml` |
| LINKML_D | charter versions 5 and 6: instructions without the Provenance lines (`d/agent_d.yaml` regenerated); version 6 is the skill body, read live | **done**: `VERSION$3` default, MODIFY LIVE `000002a9-0000-4000-8000-0000000002a9`, COMMIT `000002aa-0000-4000-8000-0000000002aa`, ADD LIVE `<query-id>`, SET DEFAULT `<query-id>`; LIVE and `VERSION$3` equal to the file |
| LINKML_DP | charter versions 4, 5 and 6: unit sentence, no Provenance lines (`d/agent_dp.yaml` regenerated); version 6 is the skill body, read live | **done**: `VERSION$3` default, MODIFY LIVE `000002ab-0000-4000-8000-0000000002ab`, COMMIT `<query-id>`, ADD LIVE `000002ac-0000-4000-8000-0000000002ac`, SET DEFAULT `000002ad-0000-4000-8000-0000000002ad`; LIVE and `VERSION$3` equal to the file |
| LINKML_B2 | compiler: the default unit sentence (`generated/agent_b2.yaml` regenerated) | **done**: `VERSION$3` default, MODIFY LIVE `000002ae-0000-4000-8000-0000000002ae`, COMMIT `<query-id>`, ADD LIVE `000002af-0000-4000-8000-0000000002af`, SET DEFAULT `<query-id>`; LIVE and `VERSION$3` equal to the file |
| LINKML_A | created at version 5 | n/a |

## Step 6: A (LINKML_A on the untouched Autopilot view)

- `a/check_ap.py` just before the build: `SYSTEM('LINKML_METRICS.RAW.AP_LINKLM')` equals
  the export, whitespace aside and parsed (`000002b0-0000-4000-8000-0000000002b0`, rechecked before CREATE).
- Spec `a/agent_a.yaml` (`a/build_spec.py`, charter version 5): DEFINITION.md sections 1, 7 and 8 without the
  Provenance lines (3,448 characters), the common response, one semantic view tool `a_semantic_view` on AP_LINKLM,
  120 s / 40,000 tokens, `tool_not_accessible: reject`.
- `CREATE AGENT LINKML_A` `000002b1-0000-4000-8000-0000000002b1`; five-beat cycle: MODIFY LIVE `<query-id>`, COMMIT
  `<query-id>`, ADD LIVE `<query-id>`, SET DEFAULT_VERSION = 'VERSION$2' `<query-id>`; every version equal to the file. Beat 5
  is call 27 (T1).
- Smoke as LINKML_SVC, policy deny-all, warehouse warm before each call. **UTC window: 2026-10-04 08:50:01.7 (call 27
  sent) to 08:54:43.1 (call 30 answered).** 4 calls (27 to 30), all status 200, no approval.

| Id | Tool calls | Answer (verbatim) | Grade | Criteria (eval/grade.py, rubric v2) |
|---|---|---|---|---|
| T1 | system_agentic_semantic_context, system_execute_sql, system_execute_sql, system_execute_sql, system_execute_sql, system_execute_sql | Flour and baking in France had a stock coverage of **2.8 months** as of June 2026, measured in quantity-equivalent units. Closing stock at the end of June 2026 was 1,400. The forecast for the following months (July 2026 onward) is a flat 500 a month, so the stock runs out in the third month, during September 2026.  The figure covers STANDARD items only, which is the default scope. The family has no BULK items, so no BULK stock was excluded. | **correct** | numeric pass (expected 2.8 given); analysis_month_named pass (named); no_aggregated_coverage pass (no added or averaged coverage); routing pass (semantic_view) |
| T6 | none | Which month of 2026 do you mean? Coverage is a point-in-time measure. It compares the stock of one analysis month with the forecast for the following 24 months. I can't sum or average it over a year, so "the whole year 2026" has no single value.  Stock snapshots run monthly from July 2023 to June 2026. That means the 2026 months with snapshots are January through June 2026.  Pick one month, for example June 2026, which is the latest. I can also give a series with one value per month from January to June 2026. I'll report it for Flour and Baking in France, in quantity-equivalent months, using STANDARD items only. I'll also say how much BULK stock was left out. | **correct** | refusal pass (no number; asks for the month or refuses with a reason); no_aggregated_coverage pass (no added or averaged coverage); routing pass (no tool call) |
| T9 | system_agentic_semantic_context, system_execute_sql, system_execute_sql, system_execute_sql, system_execute_sql, system_execute_sql | The stock coverage of Oat cereal bar 1 kg (SKU-H11) in Switzerland as of June 2026 is **0 months**, in quantity-equivalent units. The SKU has no stock snapshot for June 2026, so its closing stock is 0. Its last snapshot was May 2026, at 350. The forecast for July 2026 onward is 100 a month, but with no stock there is nothing for it to cover. SKU-H11 is a STANDARD item, so no BULK stock was left out. | **correct** | numeric pass (expected 0.0 given); analysis_month_named pass (named); no_aggregated_coverage pass (no added or averaged coverage); routing pass (semantic_view) |
| CS_LAST_MONTH_GAP | system_agentic_semantic_context, system_execute_sql, system_execute_sql, system_execute_sql, system_execute_sql, system_execute_sql | The closing stock of Oat cereal bar 1 kg (SKU-H11) in Switzerland for Q2 2026 is **0** quantity-equivalent units, or €0 in value. Closing stock is the June 2026 snapshot, the last month of the quarter. The SKU has no June snapshot, so it closes at 0. It held 400 units in April and 350 in May, and the May figure is not carried forward. The figure covers all item types, and this SKU is a STANDARD item. | **manual** | numeric manual (expected 0.0 and wrong value(s) ['last_known_value'] both given); routing pass (semantic_view) |

**CS_LAST_MONTH_GAP is manual, for the owner** (new case; the rule of `eval/manual_decisions.yaml` is applied by the
owner, not by the script): the answer gives 0 and says "It held 400 units in April and 350 in May, and the May figure
is not carried forward."

Per call (`records.py`):

| Label | Request id | Started (UTC) | Client s | First byte s | Version served | Orchestration input (cache write / read), output | Server s | Before planning s | Planning s (steps) | Context s | SQL tool s | Skill/code s | Response s | Suggested s | Computed by | Tables read by the script | Queries of the turn: elapsed ms (queued provisioning / overload ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a_t1 | `0000012f-0000-4000-8000-00000000012f` | 08:50:01.685 | 24.27 | 2.73 | VERSION$2 | 160,209 (32,861 / 127,332), out 1,600 | 22.67 | 1.41 | 14.52 (4) | 0.1 | 2.05 | 0 | 3.04 | 2.08 | model | n/a | 127 (0 / 0); 159 (0 / 0) agent SQL; 174 (0 / 0) agent SQL; 193 (0 / 0) agent SQL; 265 (0 / 0) agent SQL |
| a_t6 | `00000134-0000-4000-8000-000000000134` | 08:51:31.511 | 6.05 | 1.07 | VERSION$2 | 33,987 (3,576 / 30,403), out 255 | 4.87 | None | 0 (0) | 0 | 0 | 0 | 2.93 | 1.72 | n/a (no tool) | n/a | none |
| a_t9 | `00000135-0000-4000-8000-000000000135` | 08:52:47.089 | 21.33 | 0.94 | VERSION$2 | 161,170 (18,429 / 142,725), out 1,585 | 20.31 | 0.21 | 13.14 (4) | 0.04 | 1.31 | 0 | 3.6 | 2.49 | model | n/a | 119 (0 / 0); 131 (0 / 0) agent SQL; 136 (0 / 0) agent SQL; 136 (0 / 0) agent SQL; 136 (0 / 0) agent SQL |
| a_cs_last_month_gap | `00000012-0000-4000-8000-000000000012` | 08:54:18.535 | 24.57 | 1.05 | VERSION$2 | 188,241 (17,906 / 170,317), out 1,586 | 23.54 | 0.21 | 17.38 (5) | 0.05 | 1.32 | 0 | 2.52 | 2.3 | n/a | n/a | 113 (0 / 0); 223 (0 / 0); 135 (0 / 0) agent SQL; 141 (0 / 0) agent SQL; 192 (0 / 0) agent SQL |

SQL the agent wrote (from the tool calls):

**T1 statement 1**

```sql
SELECT i.family_code, i.family_name, i.item_type, SUM(s.stock_qty_eq) q FROM __fct_stock_snapshot s JOIN __dim_item i ON s.item_id=i.item_id JOIN __dim_geo g ON s.country_id=g.country_id WHERE g.country_name='France' AND s.snapshot_month='2026-06-01' AND i.family_name ILIKE '%flour%' GROUP BY 1,2,3
```

**T1 statement 2**

```sql
SELECT country_id, country_name FROM __dim_geo WHERE country_name='France'
```

**T1 statement 3**

```sql
SELECT family_code, family_name, item_type, COUNT(*) n, MIN(item_id) mn, MAX(item_id) mx FROM __dim_item WHERE family_name ILIKE '%flour%' OR family_name ILIKE '%bak%' GROUP BY 1,2,3
```

**T1 statement 4**

```sql
SELECT forecast_month, SUM(forecast_qty_eq) f FROM __fct_forecast WHERE country_id=1 AND item_id IN (49,50) AND forecast_month>'2026-06-01' GROUP BY 1 ORDER BY 1
```

**T1 statement 5**

```sql
SELECT snapshot_month, SUM(stock_qty_eq) q FROM __fct_stock_snapshot WHERE country_id=1 AND item_id IN (49,50) AND snapshot_month='2026-06-01' GROUP BY 1
```

**T9 statement 1**

```sql
SELECT 'F' k, f.forecast_month m, SUM(f.forecast_qty_eq) q, i.item_type t FROM __fct_forecast f JOIN __dim_item i ON f.item_id=i.item_id JOIN __dim_geo g ON f.country_id=g.country_id WHERE i.sku_code='SKU-H11' AND g.country_name='Switzerland' AND f.forecast_month>'2026-06-01' GROUP BY 1,2,4
UNION ALL
SELECT 'S', s.snapshot_month, SUM(s.stock_qty_eq), i.item_type FROM __fct_stock_snapshot s JOIN __dim_item i ON s.item_id=i.item_id JOIN __dim_geo g ON s.country_id=g.country_id WHERE i.sku_code='SKU-H11' AND g.country_name='Switzerland' AND s.snapshot_month='2026-06-01' GROUP BY 1,2,4
ORDER BY 1,2
```

**T9 statement 2**

```sql
SELECT country_id, country_name FROM __dim_geo WHERE country_name='Switzerland'
```

**T9 statement 3**

```sql
SELECT item_id, sku_code, sku_name, item_type FROM __dim_item WHERE sku_code='SKU-H11'
```

**T9 statement 4**

```sql
SELECT snapshot_month, SUM(stock_qty_eq) q FROM __fct_stock_snapshot WHERE item_id=59 AND country_id=6 AND snapshot_month>='2026-05-01' GROUP BY 1 ORDER BY 1
```

**T9 statement 5**

```sql
SELECT forecast_month, SUM(forecast_qty_eq) q FROM __fct_forecast WHERE item_id=59 AND country_id=6 AND forecast_month>'2026-06-01' GROUP BY 1 ORDER BY 1
```

**CS_LAST_MONTH_GAP statement 1**

```sql
SELECT i.sku_code, i.sku_name, i.item_type, g.country_name, SUM(s.stock_qty_eq) AS closing_qty_eq, SUM(s.stock_value_eur) AS closing_value_eur
FROM __fct_stock_snapshot s
JOIN __dim_item i ON s.item_id = i.item_id
JOIN __dim_geo g ON s.country_id = g.country_id
WHERE i.sku_code = 'SKU-H11' AND g.country_name = 'Switzerland' AND s.snapshot_month = '2026-06-01'
GROUP BY 1,2,3,4
```

**CS_LAST_MONTH_GAP statement 2**

```sql
SELECT SUM(stock_qty_eq) AS q, SUM(stock_value_eur) AS v, COUNT(*) AS n FROM __fct_stock_snapshot WHERE snapshot_month = '2026-06-01' AND item_id IN (SELECT item_id FROM __dim_item WHERE sku_code = 'SKU-H11') AND country_id IN (SELECT country_id FROM __dim_geo WHERE country_name = 'Switzerland')
```

**CS_LAST_MONTH_GAP statement 3**

```sql
SELECT country_id, country_name FROM __dim_geo WHERE country_name ILIKE '%Switz%'
```

**CS_LAST_MONTH_GAP statement 4**

```sql
SELECT item_id, sku_code, sku_name, item_type FROM __dim_item WHERE sku_code ILIKE '%H11%' OR sku_name ILIKE '%oat cereal bar%'
```

**CS_LAST_MONTH_GAP statement 5**

```sql
SELECT snapshot_month, SUM(stock_qty_eq) AS q, SUM(stock_value_eur) AS v FROM __fct_stock_snapshot WHERE item_id = 59 AND country_id = 6 AND snapshot_month BETWEEN '2026-04-01' AND '2026-06-01' GROUP BY snapshot_month ORDER BY snapshot_month
```

Reading [measured]:
- **The missing relationships did not stop the agent**: Autopilot declared none, and every statement joins the logical
  tables (`__fct_stock_snapshot`, `__dim_item`, `__dim_geo`) on their keys in plain SQL; the model wrote the joins.
  The month is an equality on `snapshot_month`, so no last-value carry arises: T9 and CS_LAST_MONTH_GAP 0. H-A5 and
  H-A7 refuted on the smoke.
- T1: the model read the stock and the monthly forecast and computed 2.8 itself (computed by: model), with only
  section 1 of the definition (no algorithm): H-A1 refuted on T1, a flat 500 a month over 3 months (see the forecast
  shapes: T1 does not test the arithmetic).
- T6: no tool, asks for the month, lists January to June 2026, states the default scope and unit (section 8). H-A6
  refuted on the smoke.
- Orchestration input 160,000 to 188,000 tokens per tool turn (4 to 5 planning steps), 34,000 without; 21.3 to 24.6 s
  per tool turn, 6.1 s without. Queued provisioning and overload 0.

Budget s8: 30 of 38 used (A 4 calls); reserve 8, not used beyond D′'s two re-runs.

Note on the verbatim answers: two answers (D′ CS re-run, A CS) were logged with the euro sign mis-decoded (the SSE
stream was read as Latin-1 by `run_call.py`); it is restored to € above, and `run_call.py` now decodes the stream as
UTF-8.

## Owner's decisions after the smoke runs (2026-10-04, no agent call)

1. **A CS_LAST_MONTH_GAP: correct** (owner, rule WRONG_VALUE_CITED_AS_HISTORY), recorded in
   `eval/manual_decisions.yaml` by request id `00000012-0000-4000-8000-000000000012`; A regraded: 4 of 4.
2. **Charter version 6**: one line added to the skill's fast path ("`coverage.py` is in this skill's folder, even if a
   listing shows it at 0 B: run it, and never do the computation yourself."). PUT again on `SKILLS_D`
   (`000002b2-0000-4000-8000-0000000002b2`, `000002b3-0000-4000-8000-0000000002b3`) and `SKILLS_DP`
   (`000002b4-0000-4000-8000-0000000002b4`, `000002b5-0000-4000-8000-0000000002b5`); names on both stages equal the
   repository; each file read back with GET is byte-identical to the repository (`SKILL.md` 3,250 B, `coverage.py`
   4,669 B; the stage lists 3,264 B and 4,672 B, its storage sizes). D's smoke T9 stays recorded as it was; no new
   smoke.
3. **Republications** (one five-beat cycle each, no agent call): B1, D, D′ and B2 now serve `VERSION$3`, equal to their
   files (table above). The smoke runs were served by `VERSION$2` of each; the campaign will be served by `VERSION$3`.

Smoke grades, final: B2 4 of 4, B1 4 of 4, A 4 of 4, D′ 5 of 5 (CS and G1 on re-runs), D 4 of 5 (T9 wrong by routing).
