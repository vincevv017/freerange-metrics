# Phase 0 findings

> Status: **in progress** (session 1, 2026-10-01; session 2, 2026-10-02; session 3, 2026-10-03; session 4 probe D, 2026-10-03). Every finding carries one tag:
> **[documented]** (Snowflake docs or release notes), **[measured here]** (run on this account, evidence below),
> **[inferred]** (reasoned from the two others, not run).

## 1. Account state

Read-only checks, run 2026-10-01 before any object was created.

| Item | Value | Tag |
|---|---|---|
| Region | `AWS_EU_WEST_3` (Paris) | [measured here] |
| Snowflake version | 10.35.101 | [measured here] |
| `CORTEX_ENABLED_CROSS_REGION` | `ANY_REGION`, set at account level (default `DISABLED`) | [measured here] |
| `CORTEX_MODELS_ALLOWLIST` | `ALL` | [measured here] |
| Models listed by `SHOW MODELS IN SCHEMA SNOWFLAKE.MODELS` | 114, incl. Claude (up to `CLAUDE-OPUS-5-5`, `CLAUDE-SONNET-5-5`), OpenAI GPT, Gemini | [measured here] |
| `SHOW CORTEX BASE MODELS` | returns "No data" under ACCOUNTADMIN; treated as a statement-shape question, not as absence | [measured here] |
| `FEATURE_CORTEX_CODE_SANDBOX` | `ENABLED` | [measured here] |
| `ENABLE_CORTEX_WEBSEARCH` | `false` | [measured here] |
| Cortex Agents available | yes: agents already exist in an unrelated database of this account | [measured here] |

Reading:
- The region imposes nothing: with `ANY_REGION`, models not deployed in EU_WEST_3 are reachable through cross-region inference. **[measured here]**
- With `ANY_REGION`, prompts and data sent to the model may be processed outside the EU. **[documented]** The model pinned in each agent spec must be named in the article.
- `FEATURE_CORTEX_CODE_SANDBOX = ENABLED` suggests the sandbox behind `code_toolset_all` is available. **[inferred]** Probe B is the real check.

### Project objects

`snowflake/00_setup.sql`, run as ACCOUNTADMIN, created `LINKML_METRICS_ROLE` (granted to SYSADMIN and <ADMIN_USER>), `LINKML_METRICS_WH` (XSMALL, auto-suspend 60 s), database `LINKML_METRICS` owned by the project role, schema `RAW`, and `SNOWFLAKE.CORTEX_USER`. **[measured here]** Everything after setup runs as `LINKML_METRICS_ROLE`.

### Synthetic dataset (grocery retail)

The synthetic data is a multi-country grocery retailer holding stock in distribution centres by supplier lot, with demand forecast by SKU x country. Ranges and families are generic grocery categories (Coffee & Tea, Pantry, Beverages, Snacks, Breakfast); a batch is a supplier lot with a best-before date; `batch_status` is RELEASED / QUALITY_HOLD / BLOCKED; QTY_EQ is kg or litres across pack sizes; `item_type` is STANDARD (forecast) or BULK (repacked in store, no forecast).

Only labels changed in the published dataset (data/output/); every other value is unchanged: **[measured here]**
- `FCT_STOCK_SNAPSHOT`, `FCT_FORECAST`, `DIM_CALENDAR` and `DIM_GEO` are byte-identical to session 1 (same sha256).
- In `DIM_ITEM`, `DIM_BATCH` and `DIM_WAREHOUSE`, only label columns differ, each through a one-to-one mapping of old to new values. Every id, quantity, cost and date is unchanged.
- `check_dataset.py` passes with the same expected and wrong values as session 1.
- After the reload (`load_snowflake.py --replace`), both probe A runners return the same values for every trap. `results.md` is identical to session 1 once query ids and family codes are masked.

Pack-size factors in DIM_ITEM (`qty_eq_factor`): case of 10 = 10, 1 kg or 1 L pack = 1, 500 g or 500 ml pack = 0.5.

Fingerprints (as_of 2026-06-01, sha256 of the CSV):

| Table | Rows | sha256 |
|---|---|---|
| `DIM_CALENDAR` | 72 | `f76cec1091ec3b273e9168c7ff1f7809fbdc54c744a6a6e34af223507d1b673b` |
| `DIM_GEO` | 10 | `18b9d94b4427ec0cc45cead4618fa5ce57beecdd57da6ec6f3eb7f7ff450d124` |
| `DIM_ITEM` | 59 | `055d32da807e7adbedc015b3605b9b937586a8e73cac627a8d141cb5fc8a8169` |
| `DIM_WAREHOUSE` | 15 | `aec1ff8005f127bc4a806ad504767c3f1797cc016bc3b5f507a032df6c7bb886` |
| `DIM_BATCH` | 4784 | `69006d328b89004d5661ca2305c0450db112f54424c3299f60ef1d1b12a9b7df` |
| `FCT_STOCK_SNAPSHOT` | 60911 | `0c3f75a68e5cfa0f57b6c36da6d68ff82d3872d7f8750d819f82582e0616e0da` |
| `FCT_FORECAST` | 15162 | `5ec30e129778d4edba9734a327906d30cbd642d342db230e5ce9b714b3656f6b` |

This session 2 table is superseded by `data/output/manifest.json`, the fingerprints of the published dataset (schema 0.5.0).

### Trap for the reader: secondary roles leak into the project role

The user has `DEFAULT_SECONDARY_ROLES = ALL`. A session opened with `--role LINKML_METRICS_ROLE` therefore still carries every other role granted to the user. **[measured here]**

```sql
SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES();
-- LINKML_METRICS_ROLE | {"roles":"ACCOUNTADMIN,<OTHER_ROLES>","value":"ALL"}
USE SECONDARY ROLES NONE;
SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES();
-- LINKML_METRICS_ROLE | {"roles":"","value":""}
```

After `USE SECONDARY ROLES NONE`, the databases owned by the other roles are no longer visible (`SHOW DATABASES LIKE '<OTHER_PROJECT>%'` returns 0 rows). **[measured here]**

Consequence: a test that passes in such a session can pass on ACCOUNTADMIN privileges, not on the project role's. Every script and SQL session in this repo starts with `USE SECONDARY ROLES NONE;`. The same question applies to agents: tool execution runs with the caller's rights. **[documented]** Session 2 measured it: **secondary roles do reach agent tool calls.** With `X-Snowflake-Role: LINKML_METRICS_ROLE`, both the agent's SQL tool and code run inside its sandbox saw `CURRENT_SECONDARY_ROLES()` = `ACCOUNTADMIN,<OTHER_ROLES>`. The header sets the primary role only. **[measured here]** (section 3). An agent run by this user carries ACCOUNTADMIN privileges until `DEFAULT_SECONDARY_ROLES` changes. Session 3 moved every agent call to a service user with the project role only (section 4).

## 2. Probe A: native semantic view (config B)

**Verdict.** The best native build gets the right number on T1, T2, T4, T8, NO_DEMAND and BEYOND_H. It does so only by re-creating the legacy cascade inside the view: 24 generated cumulative metrics and a 25-branch CASE, with the forward window hand-written in SQL. It cannot express T3 (stock-only attribute against a forecast) in a single call. It passes on T7 the fanned-out number without a warning. With no analysis month (T6), it returns a plausible wrong number instead of refusing. **[measured here]**

**Session 2 addendum: two of those limits are not native limits, they are limits of the build.** **[measured here]**
- **T6 can refuse.** A semantic-view variable `analysis_month DATE` with no default, referenced by every coverage metric, makes the T6 query fail with `010930` "No value provided for variable 'ANALYSIS_MONTH'". Every other trap keeps its value with the month passed as a variable and no month dimension. The refusal covers omission only: a mid-month date or NULL returns 0.0, and a series question returns 0.0 for every month but the variable's.
- **T3 is expressible in one call.** A status bridge (the forward spine replicated once per batch status, related to a `status` table that stock reaches through `batch`) with every forward metric divided by `COUNT(DISTINCT batch_status)` returns 6.0 for released lots, 4.0 for quality hold, 10.0 for both, and leaves every other trap unchanged. Without the division the forecast is counted once per replica kept (100, 200, 300). On a status grain it adds a zero row for a status with no stock, which the reference does not.
- **T7 is unchanged**: no build tried detects the fan-out.

Both fixes are more hand-written structure per question shape (a variable threaded through 49 metrics; a replicated spine per stock-only attribute). They make config B stronger, and they make the case for generating it. **[inferred]**

Everything below was queried directly through `SEMANTIC_VIEW()`, with no agent and no LLM. It measures what the native objects can express, not what a model would write against them. Raw evidence with query ids: `snowflake/probe_a/results.md` (first build), `snowflake/probe_a/results_spine.md` (second build) and `snowflake/probe_a/results_addendum.md` (session 2 addendum, `run_probe_a_addendum.py`).

### Builds tried

| Build | What it declares | Outcome |
|---|---|---|
| B1-ROWS (`10_native_sv_rows.sql`) | RAW tables; stock `NON ADDITIVE BY (snapshot_month)`; forecast as a flow; `C1..C24` = forward window metrics `SUM(forecast) OVER (PARTITION BY EXCLUDING month ORDER BY month ROWS BETWEEN 1 FOLLOWING AND k FOLLOWING)`; non-zero month counter | Deploys. Coverage must be rebuilt outside the view |
| B1 + coverage metric (`09_..._REJECTED.sql`) | Same, plus a derived `coverage_months` CASE over `C1..C24` | **Rejected: `010273` Unsupported window metrics in derived metric** |
| B1-RANGE (`10_native_sv_range.sql`) | Same as B1-ROWS, with `RANGE BETWEEN 1 FOLLOWING AND k FOLLOWING` over a numeric month index | Deploys. Coverage must be rebuilt outside the view |
| B2-SPINE (`20_spine_sv.sql`) | Forecast moved into a **query-defined logical table**, one row per (analysis month, item, country) with `f01..f24` already offset and densified; `C1..C24` as plain metrics; `coverage_months` as a derived metric | Deploys. **Coverage is a single view metric** |
| B2 + VAR (`30_spine_asof_variable_PROBE.sql`, session 2) | B2-SPINE plus `VARIABLES (analysis_month DATE)` with no default; the stock metric and all 48 forward metrics keep only the rows where the month equals the variable | Deploys. Omitting the variable is an error (`010930`); a string literal is an error (`010916`, `DATE` literal required) |
| B2 + BRIDGE (`40_t3_status_bridge_PROBE.sql`, session 2) | B2-SPINE with the spine cross-joined to the distinct batch statuses; `status` table related to `batch` and to the spine; forward metrics `SUM(...) / COUNT(DISTINCT batch_status)`, plus `c01_naive` / `c24_naive` as plain `SUM` | Deploys. T3 answered in one call |

All six views are generated by `gen_native_sv.py` and `gen_spine_sv.py` (`--mode base | asof-variable | status-bridge`), like the legacy metrics: nobody writes 24 windows and a 25-branch CASE by hand. For B1, the probe rebuilds coverage from `stock_qty` and `C1..C24` with the reference cascade, as a consumer would have to.

### Per trap

| Trap | Expected | B1-ROWS | B1-RANGE | B2-SPINE | B2 + VAR | B2 + BRIDGE | What native expresses or not | Tag |
|---|---|---|---|---|---|---|---|---|
| T1 re-aggregation (PANTRY_FLOUR / FR) | 2.8 | not run (ROWS identical on dense data) | 2.8 (rebuilt outside) | **2.8** | 2.8 | 2.8 | Stock and forward forecast aggregate at the queried grain, so the recompute is right. In B1 the ratio is outside the view, and nothing stops a consumer from averaging SKU coverages | measured here |
| T2 sparse months (SKU-H03 / DE) | 7.0 | **5.0**: `C2..C8` = 200..800, the window skips the two missing months | **7.0**: `C2 = C3 = 100` | **7.0** | 7.0 | 7.0 | ROWS frames reproduce the legacy total-vs-detail defect. RANGE frames over a numeric month index fix it natively. B2 fixes it in its SQL | measured here |
| T3 stock-only filter (SKU-H04 / IT released) | 6.0 | n/a | **`010959`** "The entities 'BATCH' and 'FC' are not related", as a dimension and as a filter | **`010959`** (BATCH / FWD) | `010959` | **6.0** (hold 4.0, both 10.0, blocked 0.0) | Not expressible in one call: a stock-only attribute cannot be combined with any forecast metric. Two `SEMANTIC_VIEW()` calls joined by the consumer give 6.0 (stock filtered, forecast not), but the consumer then owns the applicability rule. Session 2: the status bridge makes it one call (6.0), at the cost of a replicated spine per stock-only attribute | measured here |
| T4 time filter (SKU-H05 / ES) | 8.5 | n/a | filter **inside** `SEMANTIC_VIEW`: `C1..C24` = **NULL**; filter **outside**: 8.5 | **8.5**, filter inside or month as filter only | 8.5 | 8.5 | B1: the WHERE runs before the window, so "coverage for June" kills the future months. Only an outer filter works, and a model has to know to write it. B2: the spine is keyed by analysis month, so the natural filter is right | measured here |
| T7 fan-out (PANTRY_OIL / SE) | 2.25 (stock 900) | n/a | **3.0** (stock 1500, C1 500) | **3.0** | **3.0** | **3.0** | `PRIMARY KEY (item_id)` on a duplicated dimension is accepted at create time and not checked at query time. The fanned-out number comes back with no warning. A data-quality check has to catch it, not the view | measured here |
| T8 forecast, no stock (SKU-H08 / NL) | 0.0 | n/a | row kept, `STOCK_QTY` NULL, 0.0 rebuilt | **0.0** | 0.0 | 0.0 | The multi-fact query keeps forecast-only members, like an outer join of the per-fact aggregates | measured here |
| NO_DEMAND (SKU-H09 / BE) | NULL | n/a | n/a | **NULL** | NULL | NULL | Expressed by the derived CASE. There is no flag column, only NULL | measured here |
| BEYOND_H (SKU-H10 / PL) | 50.0 | n/a | n/a | **50.0** | 50.0 | 50.0 | Average bounded to H, by a 24-term non-zero counter in the CASE | measured here |
| T6 no analysis month (PANTRY_FLOUR / FR) | refusal | n/a | n/a | **0.0394** | **refusal `010930`** | not run | `NON ADDITIVE BY` takes the latest stock (1400), but the forward forecast is summed across all 71 analysis months (`C1` = 35500). A plausible wrong number, no error. Session 2: with a required variable the same question is refused (`010930`) | measured here |
| Bad variable value: mid-month date or NULL (PANTRY_FLOUR / FR) | refusal | n/a | n/a | n/a | **0.0** | n/a | Required means supplied, not valid: no check that the value is a calendar month start | measured here |
| Series, 3 analysis months (SKU-H04 / IT) | 4.98, 7.5, 10.0 | n/a | n/a | **4.98, 7.5, 10.0** | **0.0, 0.0, 10.0** | not run | One row per month, no total across months. Session 2: on B2 + VAR the variable pins one month, so the other months return 0.0 (read as "out of stock") | measured here |

Other measured constraints:
- **`010277`** "Required dimensions [CAL.MONTH_INDEX] must also be requested in the semantic view query." A window metric forces its ORDER BY and EXCLUDING dimensions into every query that uses it. A consumer that forgets them gets an error, not a wrong number. **[measured here]**
- `NON ADDITIVE BY (snapshot_month)` returns the latest snapshot when the month is not requested: SKU-H04 / IT = 1000. **[measured here]**

### What this means for config B

- Native **can** carry the right number on 6 of the 10 session 1 rows, and on 7 with the bridge (T3), but only with the B2 shape. That shape is the legacy metric family (24 cumulative metrics + CASE) plus a hand-written forward-window query. It is generated code, not declared semantics. **[measured here]**
- ~~Native **cannot** apply a filter to stock while leaving the forecast at the parent grain (T3).~~ Corrected in session 2: it can, through a status bridge that replicates the forward spine per status and divides the replication back out. It is one hand-built bridge per stock-only attribute; two stock-only attributes in one query need the product of their values, which was not built. **[measured here]** for batch status, **[inferred]** for the combination.
- Native **can refuse a missing analysis month** (T6, required variable), but **not a wrong one** (mid-month, NULL), and the variable breaks series questions. T7 still returns a plausible wrong number. **[measured here]**
- An agent on B1 has to write the CASE itself (`010273`). On B2 without the bridge it has to split T3 into two calls and join them; with the bridge it does not. **[inferred]**

### Tried, and not tried

Tried: `NON ADDITIVE BY`; window metrics with `PARTITION BY EXCLUDING`; ROWS vs RANGE frames; derived metric over window metrics (rejected); filter inside vs outside `SEMANTIC_VIEW()`; stock-only attribute as dimension and as filter; two-call consumer join; query-defined logical table as a forward spine; derived metric over plain metrics; several analysis months. Session 2: a required semantic-view variable (T6); a per-status bridge with naive and de-replicated metrics (T3).

Not tried, and why:
- **ASOF relationships.** v0 has one forecast version and no SCD dimension. ASOF would apply to forecast versioning, which is out of v1 scope. It does not address the forward window.
- **A variable combined with the bridge**, and a bridge over two stock-only attributes at once. Each mechanism was tested alone.
- **A variable default** (for example the latest stock month). It would trade the T6 refusal for a silent default.
- **Verified queries, YAML dialect, Cortex Analyst, and any agent run.** Config B through an LLM is Phase 4.
- **T5 (raw units) and row access policies.** Not in the Phase 0 scope.
- **Credits and latency** of the spine. The spine is recomputed per query over 72 analysis months, which is small here and untested at scale. The bridge triples it.

### Probe objects

Kept from session 1: `COVERAGE_NATIVE_ROWS_SV`, `COVERAGE_NATIVE_RANGE_SV`, `COVERAGE_SPINE_SV`. Added in session 2, all in `LINKML_METRICS.RAW`: `COVERAGE_SPINE_ASOF_PROBE_SV`, `COVERAGE_T3_BRIDGE_PROBE_SV`.

## 3. Probe B: `code_toolset_all` and skill scripts (config D′)

**Verdict.** A skill read from a stage never loaded, on any path tried (9 agent calls of a cap of 10). Without a skill, code run in the `code_toolset_all` sandbox **does query data with its own connection**, which contradicts the documentation. Both that code and the agent's SQL tool run under the requested primary role **plus every secondary role of the user, ACCOUNTADMIN included**. The read-only SQL tool asked for no approval. Each turn costs about 132,000 input tokens before any work. **[measured here]** Raw evidence, approval requests verbatim and request ids: `snowflake/probe_b/results.md`.

> **Session 3 correction.** A stage skill does load, on a permanent agent, with or without a code tool, and its script runs and reads data; with the service user, script and SQL tool run as the project role only (sections 4 and 5). The "Does a stage skill load?" row below stands for the TEMPORARY and objectless paths tried in session 2. **[measured here]**

Setup: `run_probe_b.py`, the spec in `agent_spec.yaml` (`claude-sonnet-5-5`, `code_toolset_all`, `permission_policy: always_ask`, one stage skill `skills/linkml-probe/`), key-pair JWT for <ADMIN_USER> with `X-Snowflake-Role` and `X-Snowflake-Warehouse`, because the user has no default role or warehouse. Approval policy set by the project owner: allow only the two probe commands, deny everything else, every call counts.

| Question | Answer | Tag |
|---|---|---|
| Does a REST call see a TEMPORARY agent? | **Not with a JWT**: `401 / 399513` "does not exist or access is not authorized… with JWT authentication, the role will be the DEFAULT_ROLE". A JWT `GET …/agents` lists `[ ]`. **Yes with the creating session's token**: 200. The docs list REST invocation as supported and say the agent is bound to its session; how REST attaches is not documented | measured here |
| Does a stage skill load? (TEMPORARY or objectless; see section 5 for a permanent agent) | **No.** `Skill not found` on the named temporary agent, on the objectless endpoint, with an `instructions` frontmatter field, with a directory table, with a kebab-case name, on an SSE stage. The `skill` tool's catalog lists 93 skills, all `bundled`. The stored spec keeps the `skills` block. No warning or trace attribute explains it | measured here; cause unknown |
| Can sandbox code execute SQL itself? | **Yes.** `snowflake.connector.connect()` with no argument connects from the sandbox environment (`SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_HOST`, `SNOWFLAKE_TOKEN`, `SNOWFLAKE_TOKEN_FILE_PATH`, `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`, and others) and reads `FCT_FORECAST` (15,162 rows). The docs say the opposite: "The sandbox doesn't query your data… its session is granted no data access" | measured here, **conflicts with documented** |
| Under which role? | Primary `LINKML_METRICS_ROLE`, the header's (also `role.name` on the `CORTEX_AGENT_REQUEST` event). Secondary `ALL` = `ACCOUNTADMIN,<OTHER_ROLES>`, for the sandbox code and for `snowflake_sql_execute` alike. Secondary roles are not documented for agents | measured here |
| Approvals | bash: the platform classifies `python3 -c` as `RISK_LEVEL_HIGH` and offers `Allow this command` / `Allow all bash for this session` / `Deny`, not the documented `Allow Once` / `Deny`. `snowflake_sql_execute` on a SELECT: classified `RISK_LEVEL_NONE`, read-only, **no approval requested**, although the docs list it among the tools that require approval by default. No Deny was sent | measured here |
| Span names | Skill load: **`CodeExecutionTool_skill`** (on failure: status 500, `TOOL_INTERNAL_ERROR`, the message). Run: `CodingAgentRun`; planning: `CodingAgent.Step-N`; request: event `CORTEX_AGENT_REQUEST`; root `Agent`. Skill **resource read**: not observed, since no skill loaded. Objectless calls cannot be traced by agent name | measured here |
| Latency | 8.3 to 10.8 s per turn, about 1.2 s to the first byte, sandbox provisioning included | measured here |
| Tokens | About 132,000 orchestration input tokens per turn of 2 planning steps. The `skill` tool description alone is 140,581 characters: the 93-skill bundled catalog. `disabled_skills` exists to trim it. Plus a 340-token guardrail call to `cygnal-qwen3-8b-032026` per turn | measured here |
| Credits | **0.456 credits for 8 billed turns** (call 1, a 401, is not billed). About **0.11 per turn that writes the prompt cache** (66,000 tokens written) and **0.02 per turn that reads it**; 3 cache writes are 75% of the total. Read in session 3 with the query below; per-call table in `results.md` | measured here |

Credits query, approved as a single read-only statement under ACCOUNTADMIN and run at the start of session 3:

```sql
SELECT START_TIME, END_TIME, REQUEST_ID, AGENT_NAME, TOKEN_CREDITS, TOKENS, CREDITS_GRANULAR,
       METADATA:role_name::STRING AS role_name, METADATA:sql_query_credits AS sql_query_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY
WHERE USER_NAME = '<ADMIN_USER>'
  AND START_TIME >= '2026-10-02 18:35:00 +00:00' AND START_TIME < '2026-10-02 19:15:00 +00:00'
ORDER BY START_TIME;
-- probe window: 2026-10-02 18:38:44 to 19:07:10 UTC; expected 8 billed turns (call 1 was a 401)
```

Probe objects: stages `LINKML_METRICS.RAW.SKILLS_PROBE` and `LINKML_METRICS.RAW.SKILLS_SSE_PROBE`, dropped at the end of session 2. The temporary agent `LINKML_PROBE_B_TMP_PROBE` was dropped with its sessions.

## 4. Service user

**Verdict.** Every agent call now runs as `LINKML_SVC`, a service user that holds the project role and nothing else. Inside agent tools (the sandbox script, the SQL tool and the custom procedure), the role is `LINKML_METRICS_ROLE` with no secondary role, where session 2 measured ACCOUNTADMIN. **[measured here]**

Statements (`snowflake/01_service_user.sql`, shown to the project owner before running): `USERADMIN` creates `LINKML_SVC` with `TYPE = SERVICE`, a new key pair (private key outside the repo, path only in the local `linkml_svc` connection), `DEFAULT_ROLE = LINKML_METRICS_ROLE`, `DEFAULT_WAREHOUSE = LINKML_METRICS_WH`, `DEFAULT_SECONDARY_ROLES = ()`; `SECURITYADMIN` grants `LINKML_METRICS_ROLE` only. <ADMIN_USER> is unchanged.

| Check | Result | Tag |
|---|---|---|
| Snowflake's default for a new user | `DEFAULT_SECONDARY_ROLES = ('ALL')` | documented; `DESC USER` shows it in its `default` column |
| `DESC USER LINKML_SVC` after `CREATE` and again after `ALTER USER … SET DEFAULT_SECONDARY_ROLES = ()` | `value = []`, `default = [ALL]` | measured here |
| Fresh session as LINKML_SVC, before any `USE SECONDARY ROLES` | `CURRENT_ROLE() = LINKML_METRICS_ROLE`, `CURRENT_SECONDARY_ROLES() = {"roles":"","value":""}`, warehouse `LINKML_METRICS_WH` | measured here |
| Same session after `USE SECONDARY ROLES ALL` | `{"roles":"","value":"ALL"}`: ALL of one granted role adds nothing | measured here |
| Agent call with a JWT and **no** role or warehouse header | Accepted; `CORTEX_AGENT_REQUEST` shows `user.name = LINKML_SVC`, `role.name = LINKML_METRICS_ROLE` | measured here |
| Inside agent tools: sandbox script, `snowflake_sql_execute` (section 5) and the custom procedure (section 6) | `LINKML_METRICS_ROLE`, secondary roles empty | measured here |

Reading: the empty `DEFAULT_SECONDARY_ROLES` is the first guarantee; holding one role is the effective one, since nothing can be added even on request. **[inferred]** The README section "Before you start" states the trap and this fix.

## 5. Skill mount diagnosis

**Verdict.** A stage skill loads on this account. On a permanent agent, the replica of the known-good configuration loads with no code tool, with `code_execution` and with `code_toolset_all`, and under `code_toolset_all` the skill's script runs and queries data. The session 2 hypothesis (a code tool hides stage skills) is **refuted**. The session 2 failures are explained by the agent object, not by the caller (call 6), with one combination untested. No support case was drafted: call 1 loaded. **[measured here]** Raw evidence and specs: `snowflake/probe_b/mount/`.

Setup: plain `CREATE STAGE SKILLS_PROBE` (internal, `has_encryption_key = N`, no directory table, files uncompressed), the same settings as the known-good stage **[measured, other account]**; a second skill `linkml-echo`, instructions only, whose description does not contain the expected answer; permanent agent `LINKML_SKILL_PROBE`, one spec change per call, called as LINKML_SVC. Cap 6 calls, 6 used. Agent and stage dropped at the end.

| # | Configuration | Skill tool | Loaded | Tag |
|---|---|---|---|---|
| 1 | No tool, skill `linkml-echo` | `server_skill` | **yes**: tool result `success`, answer exactly `SKILL LOADED: linkml-echo` | measured here |
| 2 | + `code_execution` | `server_skill` | **yes** | measured here |
| 3 | `code_toolset_all` instead | `skill` (sandbox), mounted at `/mnt/skills/stage/linkml_metrics_raw_skills_probe/skills/linkml-echo/` | **yes** | measured here |
| 4–5 | 3 with `linkml-probe` (script + SQL), session 2 approval rules | `skill`; then `bash` (approved, single use) and `snowflake_sql_execute` | **yes**; the script runs from the mounted folder and reads `FCT_FORECAST` (15,162 rows) with its own connector session | measured here |
| 6 | 1 again, called as **<ADMIN_USER>** (no default role or warehouse, session 2 headers) | `server_skill` | **yes** | measured here |

Findings:
- **Two load mechanisms.** Without a code tool, or with `code_execution`, the orchestrator loads the skill itself (`server_skill`, input `skill_name`, the SKILL.md body returned inline). With `code_toolset_all`, the sandbox's `skill` tool loads it from a mounted copy of the stage (input `command`, returns content, `skill_path` and a file list). **[measured here]**
- **The sandbox mounts the stage, not the declared skill.** In call 3 the sandbox catalog listed `linkml-echo` and `linkml-probe`, both `location: stage`, although the spec declared only `linkml-echo`; `linkml-probe` was only on the same stage. **[measured here]** A stage shared by several skills therefore exposes all of them to any `code_toolset_all` agent that declares one. **[inferred]**
- **Session 2 cause.** Every session 2 failure used a TEMPORARY agent or the objectless endpoint; every session 3 success used a permanent agent. Call 6 rules out the caller's missing default role. **[measured here]** The likely cause is the TEMPORARY / objectless path. **[inferred]** Untested: <ADMIN_USER> on a permanent agent with `code_toolset_all`.
- **Script and SQL tool run as the caller.** With LINKML_SVC both report `LINKML_METRICS_ROLE` and no secondary role. **[measured here]** Session 2's ACCOUNTADMIN reach came from the caller, not from the sandbox.
- **Approvals.** The bash call asked for approval (`Allow this command` / `Allow all bash for this session` / `Deny`); the read-only SQL tool asked for none and ran in the same planning step, before the bash decision was sent. **[measured here]**
- **Cost per turn.** About 33,000 to 36,000 orchestration input tokens with no code tool or with `code_execution`, about 133,000 with `code_toolset_all` (its bundled skill catalog). **[measured here]**

Trace spans **[measured here]**:
- Skill load through the orchestrator: **`ServerSkillTool_<skill name>`**, with `agent.tool.server_skill.status`, `.status.code`, `.duration`, `.already_loaded`, `.source_category = agent`. Other spans: `Agent`, `UserMemoryInjection`, `ReasoningAgentStepPlanning-N`, `ReasoningAgentStepResponseGeneration-N`, `LLM Suggested Queries`, `AgentV2RequestResponseInfo`.
- Skill load in the sandbox: **`CodeExecutionTool_skill`** (`agent.tool.code_execution.name = skill`, `.status = SUCCESS`, `.status.code = 200`), as in session 2 on failure.
- Skill **resource read**: under `code_toolset_all` a resource is a file in the mounted folder, read by an ordinary tool (`CodeExecutionTool_bash` here); no dedicated span. Under `server_skill`: not observed, since `linkml-echo` has no resource.

### Probe D (session 4): a skill script under `code_execution`

**Verdict.** Under `code_execution` the skill loads through `server_skill`, its script is mounted in the sandbox and
runs, and `snowflake.connector.connect()` succeeds, but every query on project data is refused by a restricted session
scope. The documented reading ("the sandbox doesn't query your data") holds for `code_execution`; the session 2 and 3
contradiction is specific to `code_toolset_all`. **[measured here]**, **[documented]** for the comparison. Raw
evidence: `snowflake/probe_d/results.md`.

Setup: permanent agent `LINKML_D_PROBE`, session 3 `spec_4` with `code_execution` in place of `code_toolset_all`
(`always_ask`), skill `linkml-probe-py` (Python version of `linkml-probe`, asked for by the project owner) alone on a
fresh stage `SKILLS_D_PROBE`, called as LINKML_SVC. Cap 3 calls, 1 used. Agent and stage dropped.

| Question | Answer | Tag |
|---|---|---|
| Load path | `server_skill` (span `ServerSkillTool_linkml-probe-py`, `SUCCESS`); the result lists the skill's files under `/mnt/skills/stage/<db>_<schema>_<stage>/skills/<skill>/` | measured here |
| Is the script in the sandbox? | Yes, at the mounted path; the listing reports `probe.py` as 0 B, yet `exec` of the file runs its code (staged size 192 B) | measured here |
| Which tool runs it? | `bash` (span `CodeExecutionTool_bash`), twice; no Python-specific tool appeared | measured here |
| Approval | **None requested** for either bash call, with `permission_policy: always_ask`. Under `code_toolset_all` (session 3) the same policy asked for bash approval | measured here |
| Data access | Connect succeeds; the query fails with `002003 ... Restricted session scope: USER SPECIFIED does not include USAGE or equivalent access to DATABASE LINKML_METRICS` | measured here |
| Environment | The same nine `SNOWFLAKE_*` variable names as under `code_toolset_all` | measured here |
| Instruction following | The agent excluded `/mnt` from the step 1 scan, against the skill text, citing "sandbox rules" | measured here |
| Latency, tokens | 2.0 s to first byte, 46.7 s in total (4 planning steps); 83,913 orchestration input tokens, 4,198 output | measured here |

Reading: under `code_execution` a skill script can compute only on what the orchestrator passes it; it cannot fetch
data itself. **[inferred]** The restricted scope is named `USER SPECIFIED`, while `ACTIVE_RESTRICTED_SESSION_SCOPES`
was empty inside the C0 procedure: the sandbox session carries a scope of its own, which `code_toolset_all` does not.
**[inferred]** from the two measurements.

What the results decide for D and D′ (facts only; the decision is the project owner's):
- **D (skill + `code_execution`)**: the skill mounts with `code_execution` (call 2), and its script runs, but cannot read data: the sandbox session is cut off by a restricted session scope (probe D, session 4). **[measured here]** A D rung therefore needs the data handed to the script by another tool (for example the SQL tool or the custom procedure) through the orchestrator.
- **D′ (skill + `code_toolset_all`)**: runnable. The script executes and queries data, under the caller's roles only, behind one bash approval per run. **[measured here]** Each turn costs about 133,000 input tokens against 33,000 to 56,000 for the other configurations. **[measured here]**

## 6. Probe C0: a hand-written custom tool (config C)

**Verdict.** The procedure returns the `traps.yaml` value on every hero tried and refuses every invalid input, where the native view returned 0.0. Through the agent, the four questions and one extra (BEYOND_H) are answered correctly. The T6 clarifying question came from the LLM, before any tool call. Inside the procedure the role is `LINKML_METRICS_ROLE` with no secondary role and no session scope. One platform constraint shapes the contract: a custom tool on a warehouse accepts no array argument. **[measured here]** Raw evidence: `snowflake/probe_c0/results.md`.

Setup: `LINKML_METRICS.RAW.STOCK_COVERAGE_PROBE`, Python, `EXECUTE AS CALLER`, TEMPORARY. Python because validation, bind-parameter SQL assembly and a JSON answer take a few lines, and the Phase 3 compiler is Python. Logic = DEFINITION.md section 5 with the member spine; applicability hard-coded from `data/schema_v0.py`. Agent `LINKML_C0_PROBE`, permanent, one `generic` tool bound with `{type: procedure, identifier, execution_environment: {type: warehouse, warehouse, query_timeout}}`, the known-good shape **[measured, other account]**. Cap 10 calls, 6 used. Agent dropped; the procedure stays until Phase 3.

| Check | Result | Tag |
|---|---|---|
| Direct calls against `traps.yaml` (`check_direct.py`) | **25 / 25**: T1 2.8 (children 12.0 / 0.5, VALUE 2.8), T2 7.0, T3 6.0 (hold 4.0, all 10.0, by status 6.0 / 4.0), T4 8.5, T7 2.25 with stock 900, T8 0.0 row kept, NO_DEMAND, BEYOND_H 50.0 | measured here |
| Invalid inputs, direct | NULL or empty month `AS_OF_MISSING`; `2026-06-15` `AS_OF_NOT_MONTH_START`; `June 2026` `AS_OF_INVALID`; `2026-07-01` `AS_OF_NO_SNAPSHOT`; `RAW` `UNIT_RAW_NOT_ADDITIVE`; `lifecycle_status` `ATTRIBUTE_UNCLASSIFIED`; unknown attribute `ATTRIBUTE_UNKNOWN`; empty grain `GRAIN_EMPTY`. No number in any of them. The native required variable returned 0.0 on mid-month and NULL (section 2) | measured here |
| T3 via agent: released lots, SKU-H04, Italy, June 2026 | Grain `[sku_code]`, filters SKU-H04 / IT / RELEASED: **6.0**, correct | measured here |
| T4 via agent: SKU-H05, Spain, June 2026 | `2026-06-01`, grain SKU x country: **8.5**, correct | measured here |
| T6 via agent: flour and baking, France, "over the whole year 2026" | **No tool call**; the LLM asks which month, citing the tool's single-month rule. Origin: the LLM, following the tool description. It suggests "October 2026", a month with no snapshot, which the procedure would refuse | measured here |
| Drill "And by country?" in the T3 thread | Keeps SKU-H04 and RELEASED, drops Italy, grain country: one row, IT **6.0**, correct (`coverage_ref.py`: one row). Heroes are single-country, so this tests parameter carry-over, not numbers across countries | measured here |
| BEYOND_H via agent (extra call, governance read) | **50.0**, flag explained as extrapolated from average demand | measured here |
| Role inside the procedure, called by the agent | `LINKML_SVC`, `LINKML_METRICS_ROLE`, secondary roles empty; `IS_AGENT_ACTIVATED = true` (false when called directly); `ACTIVE_RESTRICTED_SESSION_SCOPES = []` | measured here |
| Array argument | `generic tool named stock_coverage uses argument type array which is not supported for execution environment type warehouse` (call 1, both tool calls). `grain` became a string holding a JSON array; the agent then passed `"[\"sku_code\"]"` correctly | measured here |
| Object argument | Not supported for custom tools, hence `filters` as a JSON string from the start | documented |
| Approval | The `generic` tool ran without any permission request (no `permission_policy` declared) | measured here |
| Latency | 10.4 to 13.5 s per turn with one tool call, 0.8 s to first byte; 5.5 s for the clarifying question | measured here |
| Tokens | 46,800 to 56,100 orchestration input tokens per turn with a tool call, 28,500 without; 430 to 570 output; guardrail 900 to 1,950 | measured here |
| Credits | Valid turns (calls 2 to 6): **0.010 to 0.036 per turn, 0.107 in total**, mean 0.021; the turn without a tool call (T6) is the cheapest. Call 1, which failed on the array argument, **is billed** (0.035). `SQL_QUERY_CREDITS` is null on every row: the procedure's warehouse time is billed apart. For comparison, mount calls 1 and 2 cost 0.025 and 0.023, a `code_toolset_all` turn that writes the cache 0.117. Session 3 total: **0.377 credits for 12 billed turns** | measured here |

Restricted Session Scope:
- Status **[documented]** (https://docs.snowflake.com/release-notes/2026/other/2026-09-03-restricted-session-scope, Sep 3, 2026): Restricted Session Scope is generally available; it is a privilege ceiling on what an agent does for a user and never grants more than the user's roles; it is activated by setting `AGENT_RESTRICTED_SESSION_SCOPE` on a session policy attached to the account or to users.
- On this account: no scope in force inside the agent-called procedure (`ACTIVE_RESTRICTED_SESSION_SCOPES = []`), and LINKML_SVC sees no session policy. **[measured here]**
- **Not tested.** Applying a scope means a session policy on the account or on LINKML_SVC, which needs the account-level `APPLY SESSION POLICY` privilege. Open.

Limits of this probe: one run per question, no repeats; questions name SKU codes, because the agent has no lookup tool; the tool description and instructions are hand-written, and Phase 3 generates them.

## 7. Go / no-go

Each point gives a recommendation and its basis. The decisions are the project owner's.

### Article angle

**Recommendation: lead with "declare once, generate everywhere", and keep "the LLM picks the parameters, it never computes" as the runtime claim that Phase 4 has to measure.**
- For every trap row except T7, some native build returns the right answer once enough structure is added: the spine, plus the bridge for T3 and the variable for T6. No single build gets all of them, because the variable that makes T6 refuse breaks the series row. Every piece of that structure is mechanical and per-attribute: 24 cumulative metrics, a 25-branch CASE, a variable threaded through 49 metrics, a replicated spine per stock-only attribute. **[measured here]** That is the legacy metric family again, and it is exactly what a declaration of applicability per attribute and additivity per measure can generate. **[inferred]**
- What native still cannot do: refuse a wrong analysis month (mid-month or NULL returns 0.0), answer series questions once the month is a required variable, or detect the T7 fan-out. **[measured here]** These are the cases where a custom tool, whose parameters a contract validates, should differ. "Never computes" stands or falls on that difference, which Phase 4 measures. **[inferred]**
- Probe B weakens any reading of "never computes" that relies on sandboxed code. The `code_toolset_all` sandbox can query data itself, with the caller's roles. **[measured here]** With the service user those roles shrink to the project role (section 5), but a skill-plus-script rung remains a computing path: the script, not a validated tool, decides what SQL runs. **[inferred]**
- Session 3, C0: a validated custom tool returns the trap values and refuses invalid months, units and attributes with a reason; through the agent, once the array parameter was fixed, the 4 questions and one extra were right, and the LLM chose parameters only. **[measured here]** That is one run per question on hand-written instructions, not the Phase 4 evaluation. **[inferred]**

### Definition of config B

Three options, with the argument for each:
- **B1-RANGE only** (hand-written native, RANGE frames). It is what a competent practitioner writes without a generator. It cannot hold coverage as a metric (`010273`), so the agent has to compute the cascade. Risk: reviewers call it a straw man, because the addendum shows native can do much better.
- **B2 only** (native objects plus a generated spine, bridge and, optionally, variable). It is native at its best. Risk: it already embodies the thesis, since it is generated, and the article loses the "what people build by hand" baseline.
- **Both, as two rungs**. B1-RANGE is native as written by hand; B2 is native as generated from the contract. The gap between the rungs measures what generation buys. The gap between B2 and C measures what a validated custom tool buys. Cost: one more configuration in the frugal evaluation, about 12 questions x 3 repeats. **[inferred]**

My recommendation is both. One constraint to settle with it: the required variable gives the T6 refusal but breaks series questions, and "several analysis months allowed" is a default decision. B2 either drops the variable (and returns 0.0394 on T6) or keeps it and loses series. **[measured here]**

### D and D′ (updated after session 3)

The session 2 recommendation was to drop D′, on the basis that the skill never mounted. **That basis no longer holds**: the skill mounts on a permanent agent, and D′'s script runs and queries data (section 5). **[measured here]** Options, with the facts behind each; the decision is the project owner's:
- **Keep D and D′ as two rungs.** Both are now runnable as far as mounting goes. D′ costs about 133,000 input tokens per turn against 33,000 to 56,000 for B, C and D, and needs one bash approval per run, so a non-interactive evaluation needs an approval policy written for it. **[measured here]**
- **Session 4, probe D: what D is, measured.** Under `code_execution` the script runs (as `bash`, with no approval asked under `always_ask`) and cannot query data: `002003`, restricted session scope `USER SPECIFIED`. One turn cost 83,913 input tokens. **[measured here]** Three shapes follow, none decided:
  - **D as "skill + data passed in"**: the orchestrator fetches the inputs (stock and forecast at the grain) with a data tool, then hands them to the skill script, which runs the depletion algorithm. The LLM moves numbers between tools, which is the path the thesis says to avoid; that is the point of the rung. **[inferred]**
  - **D as "skill only, no script"**: the skill carries the algorithm as instructions and the LLM computes. The cheapest D, and the clearest contrast with C. **[inferred]**
  - **Drop D, keep D′**: D′ is the only skill rung whose script reads data itself. **[inferred]**
- **Keep D, drop D′.** D is the cheaper rung; D′ adds the sandbox's broad toolset and its catalog cost for the same skill. Probe B's and session 3's findings on D′ stay in the article as platform facts. **[inferred]**
- **Drop both.** Only if the article's ladder is reduced to B versus C. Nothing measured forces it.

Facts that hold whichever option is chosen: a `code_toolset_all` agent sees every skill on the stage it mounts, not just the declared one, so each skill needs its own stage or a stage per agent **[measured here]** for the mount, **[inferred]** for the remedy; and the session 2 failure path (TEMPORARY or objectless) is to be avoided for any agent that uses a skill **[inferred]**.

### Inputs Phase 1 must settle

| Input | What the probes add | Proposal |
|---|---|---|
| Default `item_type` scope | `HOT_GROUND`: 17.4 months with BULK stock (3 of 5 SKUs, never forecast), 8.7 restricted to STANDARD, against a portfolio median of 6.8 over 217 SKU x country members **[measured here]** | Default to STANDARD; make BULK an explicit opt-in that the answer states |
| Class of `lifecycle_status` | It is an item attribute, so the forecast carries it too. T7 duplicates exactly this column **[measured here]** | Conformed, with one-row-per-item enforced as a contract invariant, so T7 fails a check rather than fanning out |
| Default: beyond horizon bounded to H | No new evidence; BEYOND_H = 50.0 on every build **[measured here]** | Keep |
| Default: forecast without stock = 0, row kept; no forecast = NULL, NO_DEMAND | DEFINITION.md section 5 now keeps the row (T8, 7/7 cases). Native multi-fact queries keep it too **[measured here]** | Confirm |
| Default: stock-only attributes allowed as a grouping | The bridge adds a 0.0 row for a status with no stock; the reference does not **[measured here]** | Decide whether a zero-stock member appears on a stock-only grain |
| Default: several analysis months allowed (series) | Conflicts with the native required-variable fix for T6 **[measured here]** | Confirm; in C the as-of months are a list parameter that the contract validates |
| Secondary roles of the caller | ~~Agent tools inherit `DEFAULT_SECONDARY_ROLES = ALL`~~ Done in session 3: LINKML_SVC, project role only (section 4) **[measured here]** | Every evaluation runs as LINKML_SVC |
| Parameter types of the generated tool | A custom tool on a warehouse rejects an array argument (measured) and an object argument (documented) **[measured here]**, **[documented]** | Every list or map parameter is generated as a JSON string with parsing and validation in the procedure, as in C0 |
| As-of months: one or a list | C0 takes one month. A series needs a list, so a JSON string under the constraint above **[measured here]** | Decide with "several analysis months allowed"; the T6 behaviour (ask, never pick) carries over |
| Refusal surface | T6 was refused by the LLM from the tool description, before any call; the procedure's refusal codes were exercised only directly **[measured here]** | Decide whether the evaluation must also see procedure refusals through the agent (for example a mid-month question) |

## 8. Open questions

- ~~**DEFINITION.md section 5 loses T8 members.**~~ Fixed in session 2: section 5 now builds a member spine (stock members UNION forecast members at the conformed grain), identical in logic to `data/coverage_ref.py`. `check_coverage_formula.py` has a T8 case (7 of 7 match the legacy replica) and asserts that the stock-driven shape loses the member. **[measured here]** Phase 3 must keep the spine.
- **Default item-type scope.** `item_type` is stock-only by decision, so a family total counts BULK stock (repacked in store, never forecast) against the STANDARD forecast. On v0, family `HOT_GROUND` (3 BULK SKUs out of 5) shows 17.4 months against a portfolio median of 6.8 over the 217 SKU x country members with a value; restricted to `item_type = STANDARD` it shows 8.7. **[measured here]** Phase 1 must decide whether coverage defaults to STANDARD items only.
- **Class of `lifecycle_status`.** It is left unclassified in the temporary schema, so it cannot be used with coverage until the contract declares it.
- ~~Can a required semantic-view variable for the analysis month make the native view refuse T6 instead of returning 0.0394?~~ Yes when it is omitted (`010930`), no when it is wrong (mid-month or NULL returns 0.0). See section 2. **[measured here]**
- Which form of `SHOW CORTEX BASE MODELS` lists the models a role can reach, given that it returns no rows under ACCOUNTADMIN here?
- ~~**Why does a stage skill never mount** (section 3)?~~ It mounts on a permanent agent, with or without a code tool (section 5). **[measured here]** Still open: why the TEMPORARY and objectless paths fail, and whether <ADMIN_USER> on a permanent agent with `code_toolset_all` loads (the one untested combination).
- **Sandbox data access contradicts the docs** (section 3). Is it intended, account-specific, or a defect? Worth a support case before the article states either reading.
- How does a REST call attach to a temporary agent, as documented? JWT fails, the creating session's token works.
- ~~Span name of a skill **resource read**~~: under `code_toolset_all` there is none, the file is read by an ordinary tool (`CodeExecutionTool_bash`). Under `server_skill`: still unobserved (no skill with a resource was loaded that way). **[measured here]**
- ~~Does a skill **script** run under `code_execution` (config D), and can that sandbox read data?~~ It runs, it cannot read data (restricted session scope), session 4. **[measured here]** New: why does `always_ask` ask for bash approval under `code_toolset_all` and not under `code_execution`? And credits of the probe D turn, to read.
- **Restricted Session Scope** on the custom procedure tool: no scope is in force here; applying one needs `APPLY SESSION POLICY` at account level. Untested.
- A `code_toolset_all` agent lists every skill on the mounted stage: is that the documented mount unit (stage, or the `skills/` folder)? **[measured here]** as behaviour, undocumented as intent.
- ~~Credits of probe B~~: 0.456 credits for 8 turns, read in session 3 (section 3). **[measured here]**
