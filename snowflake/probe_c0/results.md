# Probe C0 raw results (config C, hand-written; session 3, step 3)

Run 2026-10-03, 06:48 to 06:59 UTC. Procedure `LINKML_METRICS.RAW.STOCK_COVERAGE_PROBE` (`10_stock_coverage_probe.sql`,
Python, `EXECUTE AS CALLER`, TEMPORARY), agent `LINKML_METRICS.RAW.LINKML_C0_PROBE` (`agent_spec.yaml`, permanent,
dropped at the end), called by `snowflake/probe_b/mount/run_call.py` as **LINKML_SVC** with a key-pair JWT and no
role or warehouse header. Orchestration model `claude-sonnet-5-5`. Cap: 10 agent calls, 6 used. Raw events stay
outside the repository.

## Direct calls (no agent)

`check_direct.py`, as LINKML_SVC. Expected values are read from `data/traps.yaml`; the script asserts numbers, refusal
codes, and the role seen inside the procedure. **25 / 25 pass**, after the grain change below.

| Case | Expected | Got (coverage, flag, stock) |
|---|---|---|
| T1 PANTRY_FLOUR x FR, QTY_EQ | 2.8 | 2.8, none, 1400 |
| T1 same, VALUE | 2.8 | 2.8, none, 16800 (EUR) |
| T1 children SKU-H01 / SKU-H02 | 12.0 / 0.5 | 12.0 / 0.5 |
| T1 grain passed as `family_code, country_code` | 2.8 | 2.8 |
| T2 SKU-H03 / DE (sparse months) | 7.0 | 7.0 |
| T3 SKU-H04 / IT, released | 6.0 | 6.0, none, 600 |
| T3 quality hold only / all statuses | 4.0 / 10.0 | 4.0 / 10.0 |
| T3 grain with `batch_status`: RELEASED row / QUALITY_HOLD row | 6.0 / 4.0 | 6.0 / 4.0 |
| T4 SKU-H05 / ES, as-of month = June 2026 | 8.5 | 8.5 |
| T7 PANTRY_OIL / SE (duplicated item) | 2.25, stock 900 | 2.25, stock 900 |
| T8 SKU-H08 / NL (forecast, no stock) | 0.0, row kept | 0.0, `NO_STOCK`, 0 |
| NO_DEMAND SKU-H09 / BE | NULL, NO_DEMAND | NULL, `NO_DEMAND` |
| BEYOND_H SKU-H10 / PL | 50.0, BEYOND_HORIZON | 50.0, `BEYOND_HORIZON` |
| T6 as-of NULL / empty string | refusal | `AS_OF_MISSING` / `AS_OF_MISSING` |
| as-of `2026-06-15` (mid-month) | refusal | `AS_OF_NOT_MONTH_START` |
| as-of `June 2026` | refusal | `AS_OF_INVALID` |
| as-of `2026-07-01` (no snapshot) | refusal | `AS_OF_NO_SNAPSHOT` |
| unit `RAW` | refusal | `UNIT_RAW_NOT_ADDITIVE` |
| grain with `lifecycle_status` | refusal | `ATTRIBUTE_UNCLASSIFIED` |
| filter on `brand` | refusal | `ATTRIBUTE_UNKNOWN` |
| empty grain | refusal | `GRAIN_EMPTY` |

Inside the procedure, called directly: `CURRENT_USER() = LINKML_SVC`, `CURRENT_ROLE() = LINKML_METRICS_ROLE`,
`CURRENT_SECONDARY_ROLES() = {"roles":"","value":""}`, `IS_AGENT_ACTIVATED = false`,
`ACTIVE_RESTRICTED_SESSION_SCOPES = []`.

T7 is right because the procedure joins `SELECT DISTINCT item_id, sku_code, family_code, range_code, item_type FROM
DIM_ITEM`: the duplicated row differs only on `lifecycle_status`, which the projection leaves out. The procedure also
refuses (`MASTER_DATA_FANOUT`) if that projection is still not one row per item.

## Agent calls

| # | Question | Tool call (parameters) | Answer | Correct? | Request id | Seconds (first byte / total) | Orchestration input tokens (write / read) | Output |
|---|---|---|---|---|---|---|---|---|
| 1 | T3: "What is the stock coverage of released lots of green tea loose-leaf (SKU-H04) in Italy, as of June 2026?" | 2 calls, both `error`: `generic tool named stock_coverage uses argument type array which is not supported for execution environment type warehouse` | Reports the tool error, no number, offers to retry | n/a (instrument defect) | `00000301-0000-4000-8000-000000000301` | 0.8 / 10.4 | 56,084 (16,016 / 40,056) | 566 |
| 2 | T3, same question, after `grain` became a string | `as_of_month 2026-06-01`, `QTY_EQ`, grain `["sku_code"]`, filters `sku_code SKU-H04, country_code IT, batch_status RELEASED` | "6.0 months … RELEASED batch status … 600 units of stock compare with 2,400 units of forecast … no flags" | **yes (6.0)** | `00000302-0000-4000-8000-000000000302` | 0.8 / 11.6 | 46,814 (18,029 / 28,775) | 484 |
| 3 | T4: "What is the stock coverage of strawberry jam (SKU-H05) in Spain for June 2026?" | `2026-06-01`, `QTY_EQ`, grain `["sku_code", "country_code"]`, filters `sku_code SKU-H05, country_code ES` | "8.5 months … at the start of June 2026 … stock 1,000 against 2,580" | **yes (8.5)** | `00000303-0000-4000-8000-000000000303` | 0.8 / 11.8 | 46,875 (6,189 / 40,676) | 431 |
| 4 | T6: "What is the stock coverage of flour and baking (family PANTRY_FLOUR) in France over the whole year 2026?" | **none** | "The stock_coverage tool measures coverage at a single month, so I can't run it over a whole year. Which month in 2026 do you want? For example, January 2026 or October 2026." Restates family, country and unit | **yes (clarifying question, from the LLM)** | `00000304-0000-4000-8000-000000000304` | 1.9 / 5.5 | 28,468 (3,537 / 24,923) | 175 |
| 5 | Drill in the thread of call 2: "And by country?" | `2026-06-01`, `QTY_EQ`, grain `["country_code"]`, filters `sku_code SKU-H04, batch_status RELEASED` (Italy dropped, released kept) | "only one row for released lots as of June 2026, and it is Italy. Coverage there is 6.0 months, the same as before" | **yes** (reference `coverage_ref.py`: one row, IT 6.0) | `00000305-0000-4000-8000-000000000305` | 0.8 / 13.5 | 55,048 (8,865 / 46,173) | 528 |
| 6 | Governance, BEYOND_H: "What is the stock coverage of Arabica beans (SKU-H10) in Poland as of June 2026?" | `2026-06-01`, `QTY_EQ`, grain `["sku_code","country_code"]`, filters `SKU-H10, PL` | "50 months … flagged as beyond the horizon … extrapolated from average monthly demand" | **yes (50.0, flag explained)** | `00000306-0000-4000-8000-000000000306` | 0.8 / 11.8 | 47,062 (6,296 / 40,756) | 472 |

Calls 2 to 6 are each run once. The T6 refusal came from the **LLM**, before any tool call, following the tool
description ("If the user gives no month, or a period …, do not choose one: ask which month"). The procedure's own
refusal (`AS_OF_MISSING`) was not reached through the agent. The clarifying question suggests "October 2026", a month
with no stock snapshot; the procedure would refuse it (`AS_OF_NO_SNAPSHOT`).

No call raised a permission request: the `generic` tool ran without approval. No `response.warning`. Guardrail model
`cygnal-qwen3-8b-032026`: 922 to 1,944 input tokens per turn, absent on call 4 (no tool call).

## Governance inside the procedure, called by the agent

From the procedure's own `caller` block, in each successful tool result:

| Call | `CURRENT_USER()` | `CURRENT_ROLE()` | `CURRENT_SECONDARY_ROLES()` | `IS_AGENT_ACTIVATED` | `ACTIVE_RESTRICTED_SESSION_SCOPES` |
|---|---|---|---|---|---|
| 2, 3, 5 | LINKML_SVC | LINKML_METRICS_ROLE | `{"roles":"","value":""}` | not read yet | not read yet |
| 6 | LINKML_SVC | LINKML_METRICS_ROLE | `{"roles":"","value":""}` | **true** | **`[]`** |

The two `SYS_CONTEXT` fields were added to the procedure after call 5 (no other change; `check_direct.py` re-run,
25 / 25). `SHOW SESSION POLICIES IN ACCOUNT` as LINKML_SVC returns no row.

## Trace spans

Per turn with a tool call: `Agent`, `UserMemoryInjection`, **`SqlExecution`**, **`ToolCall-stock_coverage`**,
`ReasoningAgentStepPlanning-N`, `ReasoningAgentStepResponseGeneration-N`, `LLM Suggested Queries`,
`AgentV2RequestResponseInfo`, event `CORTEX_AGENT_REQUEST`. Call 1 shows two `ToolCall-stock_coverage` spans and no
`SqlExecution`: the error is raised while building the call. Call 4: no tool span.

## Instrument changes during the probe

1. After call 1: `grain` changed from `ARRAY` to `VARCHAR` (JSON array or comma-separated list), in the procedure
   and in the tool's `input_schema` (`type: array` to `type: string`). Nothing else changed.
2. After call 5: two `SYS_CONTEXT` reads added to the `caller` block.
3. Cosmetic, not fixed: `applicability` lists an attribute twice when it is both in the grain and in the filters.

## Credits

Read 2026-10-03 at 07:10 UTC, last in the session, with the approved query (ACCOUNTADMIN, one SELECT on
`SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY`, `USER_NAME IN ('LINKML_SVC', '<ADMIN_USER>')`, 06:25 to 07:10 UTC).
12 rows, none missing. `SQL_QUERY_CREDITS` is null on every row; `role_name` is `LINKML_METRICS_ROLE`.

| Call | Request id | Tokens | Token credits |
|---|---|---|---|
| 1 (array error) | `00000301-0000-4000-8000-000000000301` | 56,650 | 0.0349 (billed) |
| 2 T3 | `00000302-0000-4000-8000-000000000302` | 47,298 | 0.0362 |
| 3 T4 | `00000303-0000-4000-8000-000000000303` | 47,306 | 0.0182 |
| 4 T6 | `00000304-0000-4000-8000-000000000304` | 28,643 | 0.0101 |
| 5 drill | `00000305-0000-4000-8000-000000000305` | 55,576 | 0.0239 |
| 6 BEYOND_H | `00000306-0000-4000-8000-000000000306` | 47,534 | 0.0186 |
| n/a | n/a | n/a | **0.1419** (0.1070 without call 1) |

The procedure's warehouse time is not in this view.
