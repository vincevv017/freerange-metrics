# Research log

Checks run outside the campaign's record files, newest first. Tags: **[measured]**, **[documented]**, **[inferred]**.
Raw output stays in `../linkml-metrics-runs/` (not published).

## Session 17 (2026-10-13): checks before the article goes out

Scope: one SQL test on the account and a cross-check of the figures added to the article "Free the metric" after a
critical review. Nothing frozen changed: no contract, generator, generated file or published file was edited, no
agent was called, pytest was not run against the account.

### 1. NON ADDITIVE ALIGNED BY

**Documentation [documented, read 2026-10-13].**
- `https://docs.snowflake.com/en/user-guide/views-semantic/yaml-vs-ddl`: the only page found that names it, once, in
  the "Semi-additive metrics" row of the comparison table: "DDL also supports `NON ADDITIVE ALIGNED BY`." Nothing
  says what it does.
- `https://docs.snowflake.com/en/sql-reference/sql/create-semantic-view`, `.../views-semantic/sql`,
  `.../views-semantic/semantic-view-yaml-spec` and the release note of 2026-03-05 on semi-additive metrics: no
  "ALIGNED" anywhere.

**Test [measured, `../linkml-metrics-runs/s17/aligned_run{1,2,3}.json`, not published].** Connection perso,
`USE SECONDARY ROLES NONE`, `LINKML_METRICS_ROLE`, `LINKML_METRICS_WH` (X-Small), `USE_CACHED_RESULT = FALSE`,
2026-10-13 15:01:46 to 15:03:06 UTC. A throwaway view `LINKML_METRICS.RAW.TMP_S17_ALIGNED_PROBE_SV` on the raw
`FCT_STOCK_SNAPSHOT` with `DIM_ITEM`, `DIM_GEO` and `DIM_CALENDAR`. It has two metrics on `SUM(stock_qty_eq)`:
`stock_qty NON ADDITIVE BY (stock.snapshot_month ASC NULLS LAST)`, as in the closing probe of session 6, and
`stock_qty_aligned NON ADDITIVE ALIGNED BY (...)`. It was created and dropped three times: twice aligned on
`stock.snapshot_month`, once on `cal.month_start`. `SHOW SEMANTIC VIEWS` finds nothing after each drop.

- **The syntax is accepted** on both columns, and the view is created.
- **The clause is not kept.** `GET_DDL` gives back `non additive by (STOCK.SNAPSHOT_MONTH asc nulls last)`, or
  `(CAL.MONTH_START ...)`, with no ALIGNED. `DESCRIBE SEMANTIC VIEW` gives the two metrics the same
  `NON_ADDITIVE_DIMENSIONS` property. `SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW` gives them the same
  `non_additive_dimensions`.
- **The figures are identical** in all three runs. Q2 2026, CH, SKU-H11, which had 400 in April, 350 in May and no
  June snapshot (data/traps.yaml `CS_LAST_MONTH_GAP`, probe of session 6):

| Query (2026-Q2, CH) | NON ADDITIVE BY | NON ADDITIVE ALIGNED BY | `CLOSING_STOCK` | Expected |
|---|---|---|---|---|
| SKU-H11 x quarter | 350 | 350 | 0 (`closed_without_snapshot`) | 0 |
| SKU-H12 x quarter | 450 | 450 | 450 | 450 |
| SNACK_BARS x quarter (family) | 450 | 450 | 450 (TOTAL row, recomputed) | 450 |
| SKU-H11 / SKU-H12, no time dimension | 350 / 450 | 350 / 450 | | 0 / 450 |
| SKU rows add up to the family | 800 against 450: no | 800 against 450: no | 0 + 450 = 450: yes | yes |
| SKU-H11 June, month grain | no row | no row | | 0 |

`CLOSING_STOCK` was called as `('["2026-Q2"]', '["sku_code"]', '{"family_code": ["SNACK_BARS"], "country_code":
["CH"]}', 'QTY_EQ', '[[]]')`. SNACK_BARS in CH holds two SKUs, SKU-H11 and SKU-H12. The call took 7.6 to 8.9 s.

The last two runs read the view back. Whether the platform drops the word, or keeps it and does not show it, cannot
be told from outside **[inferred]**. Either way, on this data it changes nothing **[measured]**.

**Sentence for Limits:** "I tried NON ADDITIVE ALIGNED BY: Snowflake accepts the clause, but GET_DDL gives the metric
back as plain NON ADDITIVE BY, and on the same data it returns the same figures: 350 for SKU-H11 in Q2 2026, where the
procedure returns 0, and 350 + 450 for the SKUs against 450 for their family. The documentation names the clause once
and does not describe it."

**Cost [inferred, the harness rate].** The warehouse was resumed at 15:01:51 UTC and was still running at 15:04:11:
a metering read restarted its 60 s idle timer. About 190 s of running time comes to about 0.07 credits at the
measured 1.35 credits a running hour, about 0.27 USD, under the 0.5 credit ceiling. Nothing billed was read:
`INFORMATION_SCHEMA.WAREHOUSE_METERING_HISTORY` had no row yet, and the `ACCOUNT_USAGE` read needs ACCOUNTADMIN and the
owner's go.

### 2 to 5. Figures of the article, cross-checked

| Article claim | In the article | Found | Source |
|---|---|---|---|
| Figure only, stage 1, C-raw | (not given in the brief) | 22 of 24 | `snowflake/session13_craw/results.md:235`; README.md:275 |
| Figure only, stage 1, Snowflake's assistant (A, Autopilot view) | 19 | 19 | `snowflake/phase5_campaign/stage1_results.md:438`; README.md:271 |
| Figure only, written by hand (B1) | 19 | 19 | stage1_results.md:439 |
| Figure only, generated semantic view alone (B2) | 19 | 19 | stage1_results.md:440 |
| Figure only, code-execution skill, inputs from that view (D) | 20 | 20 | stage1_results.md:442 |
| Figure only, code-execution skill, reading the raw tables (D′) | 19 | 19 | stage1_results.md:443 |
| Figure only, gap-filled view (C) | 24 | 24 | stage1_results.md:441 |
| Sweden fan-out, the question | | T7_R1, "What is the stock coverage of cooking oils in Sweden by lifecycle status as of June 2026?" | `generated/reference_questions.yaml:202` |
| Sweden fan-out, who gave 2.25 and 6.0 | | A, B1, B2, D (A also gave 1.0 and listed other members) | stage1_results.md:80, :108; `eval/fixtures/grades_campaign-s1.json` (T7_R1 records) |
| Sweden fan-out, refusal code | MASTER_DATA_FANOUT | `MASTER_DATA_FANOUT` (C, and C-raw in session 13); D′ refused in prose, no code | `generated/reference_questions.yaml:220`; stage1_results.md:83; grades_campaign-s1.json:6181 (C's answer) |
| Data size | about 61,000 stock and 15,000 forecast rows | 60,915 and 15,306 | README.md:410; `snowflake/phase4_basis/results.md:75-76` |
| Model served | claude-sonnet-5-5 | `claude-sonnet-5-5` on every turn | stage1_results.md:16; `snowflake/session13_craw/results.md:221` |
| Median latency per turn, generated tools | 16 to 19 s | C 16.3 and 17.5; C-raw 19.0 and 18.3 | stage1_results.md:67; `snowflake/phase5_campaign/stage2_results.md:116`; session13_craw/results.md:320-321 |
| Verdicts moved by rubric 3.3, six configurations | 15 | 15: 12 in stage 1, 3 in stage 2 (C 1, B2 2), all wrong to correct | stage1_results.md:450-465; stage2_results.md:276-282 |
| Verdicts moved by rubric 3.3, C-raw | 3 | 3: NO_DEMAND r1 (stage 1), NO_DEMAND r2 and T8 r2 (stage 2) | `eval/fixtures/grades_craw-s{1,2}.json` against `.rubric-3.3.json`; session13_craw/results.md:235, :241 |
| AI Credits per turn, stage 1 median | 0.020 against 0.104 | C 0.0195 (C-raw 0.0195), B2 0.1042 | stage1_results.md:221, :223; session13_craw/results.md:320 |
| AI Credits per turn, stage 2 mean | 0.04 against 0.11 | C 0.0379, B2 0.1087; C-raw 0.0243 | stage2_results.md:196; session13_craw/results.md:321 |
| Price of an AI Credit | 2.00 USD | 2.00 USD (the project's pricing, owner's decision 3) | `eval/guards.py:45`; stage2_results.md:137 |
| Total, about 52 USD | about 52 | 52.32 USD = campaign 44.93 (agent 33.32, guardrail 0.75, warehouse 10.86) + C-raw 7.39 (build and checks 2.37, arm 5.02); 52.40 with C-raw's guardrail (0.08); the step 0 incident of session 13 (1.15) is apart | stage2_results.md:244; README.md:470; session13_craw/results.md:322, :336-340 |
| Input tokens per closing-stock turn | 70,000 against 164,000 | C-raw 68,088 (stage 1) and 71,153 (stage 2) medians, C 164,278 and 164,112 | session13_craw/results.md:231, :236, :251 |
| Compilation of a `CLOSING_STOCK` call | about 5 s | 5.2 s of 6.4 s (median of 10 warm calls) | `docs/phase5_notes.md:359` (finding 147) |

Labels [measured, `docs/figures/05-trade-off.md:11`]:
- Snowflake's assistant = A: the Autopilot view, which only reads raw tables.
- Written by hand = B1.
- Generated semantic view alone = B2.
- Code-execution skill, inputs from that view = D.
- Code-execution skill, reading the raw tables = D′.
- Gap-filled view = C. The figures name C "Generated tools, gap-filled view". B2 also reads the gap-filled view
  **[documented, `docs/configurations.md`, section 2]**, so "gap-filled view" alone could be read as B2. The
  article's label is the shorter one.

### 5. Sources

- **[6] arXiv 2507.11538** ("How Many Instructions Can LLMs Follow at Once?", Jaroslawicz, Whiting, Shah, Maamari).
  The arXiv page has no comments or journal-ref field. NeurIPS 2025 lists it as a **workshop poster**: "Evaluating
  the Evolving LLM Lifecycle: Benchmarks, Emergent Abilities, and Scaling", `https://neurips.cc/virtual/2025/122417`.
  It is not in the main proceedings. The OpenReview page (`https://openreview.net/forum?id=UnWroaGuOa`) could not be
  read: it returned a bot check. Suggested citation: "NeurIPS 2025 Workshop on Evaluating the Evolving LLM Lifecycle"
  or "arXiv, 2025". "NeurIPS 2025" alone overstates it **[documented]**.
- **[4] `https://docs.snowflake.com/en/user-guide/views-semantic/sql`**, section "Identifying the dimensions that
  should be non-additive for a metric". It has the bank example. For cust-001 in 2024, "The last day of 2024 that
  contains data is 2024-03-30. There is no row with that date for the checking account, so the resulting metric is
  the balance of the savings account": 210, not 200 + 210. The page describes, with its own example, an account that
  has no row on the last date and drops out of the total **[documented]**. It shows that last date as the latest in
  the group the query asks for, not per account.
  - This matches the measured family case: SKU-H11 drops out of the SNACK_BARS total.
  - The page does not cover the per-member case: a row whose own group stops early keeps its last value (SKU-H11
    alone: 350). That is measured here, not documented.
