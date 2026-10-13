# Probe B raw results (config D′: `code_toolset_all` + stage skill)

Run 2026-10-02, 18:38 to 19:07 UTC, by `run_probe_b.py`, as <ADMIN_USER> with `X-Snowflake-Role: LINKML_METRICS_ROLE` and
`X-Snowflake-Warehouse: LINKML_METRICS_WH` (the user has no default role and no default warehouse). Orchestration model
`claude-sonnet-5-5` (confirmed by `response.metadata.orchestration_model`). Cap: 10 agent calls, 9 used. Raw event logs
stay outside the repository because they carry the account host.

## Calls

| # | Path and auth | Spec change | HTTP | Seconds (first byte / total) | Request id | Outcome |
|---|---|---|---|---|---|---|
| 1 | Named TEMPORARY agent, key-pair JWT | as written | 401 | n/a / 0.2 | `000002f8-0000-4000-8000-0000000002f8` | `399513` "The agent does not exist or access is not authorized for the current role. If you are using JWT authentication, the role will be the "DEFAULT_ROLE" of the current user" |
| 2 | Named TEMPORARY agent, creating session's token | as written | 200 | 1.2 / 9.7 | `000002f9-0000-4000-8000-0000000002f9` | `skill` tool: `Skill not found: linkml_probe` |
| 3 | same as 2 | `instructions` added to the SKILL.md frontmatter | 200 | 1.6 / 10.8 | `000002fa-0000-4000-8000-0000000002fa` | `Skill not found: linkml_probe` |
| 4 | same as 2 | stage `DIRECTORY = (ENABLE = TRUE)` + `REFRESH` | 200 | 1.2 / 8.3 | `000002fb-0000-4000-8000-0000000002fb` | `Skill not found: linkml_probe` |
| 5 | Objectless `/api/v2/cortex/agent:run`, key-pair JWT, spec inline | same | 200 | 1.2 / 9.7 | `000002fc-0000-4000-8000-0000000002fc` | `Skill not found: linkml_probe` |
| 6 | Objectless, JWT (run A) | skill renamed `linkml-probe` everywhere, old folder removed from the stage | 200 | 1.1 / 10.0 | `000002fd-0000-4000-8000-0000000002fd` | `Skill not found: linkml-probe` |
| 7 | Objectless, JWT (run C) | no skill; the question names the bash command and the SELECT | 200 | not recorded | not recorded | Stops on a bash approval request (below) |
| 8 | Objectless, JWT (run C, resumed with the decision) | same | 200 | not recorded | not recorded | bash and SQL both succeed (below) |
| 9 | Objectless, JWT (run B) | skill on a new stage `SKILLS_SSE_PROBE`, `ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')`, directory enabled | 200 | 1.1 / 10.6 | `000002fe-0000-4000-8000-0000000002fe` | `Skill not found: linkml-probe` |

Calls 7 and 8: the driver crashed after call 8 while writing its summary (a resumed call had no `events` key, fixed
since). The event logs of both calls are complete; their timing and request id were not kept.

A preflight `GET /api/v2/databases/LINKML_METRICS/schemas/RAW/agents` with the same JWT, outside the cap, returned
200 and `[ ]` while the temporary agent existed in the creating session.

## Skill mounting

On every path the agent invoked the `skill` tool with the configured name and got `Skill not found`. The `skill` tool's
catalog, read from the `CodingAgent.Step-0` span, lists 93 skills, all with location `bundled`; the stage skill is never
in it. The stored spec (`DESCRIBE AGENT`) keeps the `skills` block. No `response.warning` and no trace attribute
mentions a mount, the stage, or an error before the `Skill not found`.

Zero-call checks between runs:
- 90 of the 93 bundled names are lowercase, digits and hyphens; 3 contain underscores (`data_to_dashboard`,
  `dcb_marketplace_sharing_availability`, `semantic_studio`). The catalog exposes no folder or path.
- `DESC STAGE` and `SHOW STAGES` do not expose the encryption type of `SKILLS_PROBE` (`has_encryption_key = N` is about
  external stages); the documented default for an internal stage is `SNOWFLAKE_FULL`.

Hypotheses tested and refuted, one call each: temporary agent or session-token path (objectless fails the same way);
missing `instructions` frontmatter field; no directory table; snake_case name; client-side stage encryption.

## Run C: sandbox code and the SQL tool

Question sent (call 7):

```
Run these two steps exactly once each, in order, and report each raw output verbatim in a fenced block, errors included. Do not retry, do not fix errors, do not use any other tool.
1. With bash, run exactly: python3 -c "import snowflake.connector as sc; print(sc.connect().cursor().execute('SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST').fetchall())"; env | cut -d= -f1 | grep -i snowflake | sort
2. With the Snowflake SQL tool, run exactly: SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST
```

Approval requests, verbatim, and decisions:

| Call | Tool | Input | Platform classification | Options offered | Decision |
|---|---|---|---|---|---|
| 7 | `bash` | `python3 -c "import snowflake.connector as sc; print(sc.connect().cursor().execute('SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST').fetchall())"; env \| cut -d= -f1 \| grep -i snowflake \| sort` (description: "Run Snowflake connector query and list env vars") | `RISK_LEVEL_HIGH`, reason "Python code execution (-c flag)" | `Allow this command`, `Allow all bash for this session`, `Deny` | `Allow this command`: exact match. The documented options are `Allow Once` / `Deny`; the single-use option was taken as the policy's "Allow Once", the session-wide option never |
| 8 | `snowflake_sql_execute` | `SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST` | `RISK_LEVEL_NONE`, "Read-only SQL", `CATEGORY_READ_ONLY` | **none: no approval was requested** | n/a |

No Deny was sent in the whole probe.

Outputs (call 8):

```
step 1 (bash, sandbox code with its own connector session):
[('LINKML_METRICS_ROLE', '{"roles":"ACCOUNTADMIN,<OTHER_ROLES>","value":"ALL"}', 15162)]
SNOWFLAKE_ACCOUNT
SNOWFLAKE_HOST
SNOWFLAKE_LOGIN_NAME
SNOWFLAKE_REQUEST_ID
SNOWFLAKE_ROLE
SNOWFLAKE_TOKEN
SNOWFLAKE_TOKEN_FILE_PATH
SNOWFLAKE_USERNAME
SNOWFLAKE_WAREHOUSE

step 2 (snowflake_sql_execute):
CURRENT_ROLE(),CURRENT_SECONDARY_ROLES(),COUNT(*)
LINKML_METRICS_ROLE,"{""roles"":""ACCOUNTADMIN,<OTHER_ROLES>"",""value"":""ALL""}",15162
```

15162 is the row count of `FCT_FORECAST` (manifest). Variable names only were printed, never values.

## Trace (named temporary agent, calls 2 to 4)

`SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS('LINKML_METRICS', 'RAW', 'LINKML_PROBE_B_TMP_PROBE', 'CORTEX AGENT')`, read
from the creating session, returned 6 records per turn:

| Record | Kind | Notes |
|---|---|---|
| `Agent` | span | root |
| `CodingAgentRun` | span | `agent.coding_agent.client_type`, `private_mode`, `thread_id` |
| `CodingAgent.Step-0`, `CodingAgent.Step-1` | span | planning steps; `planning.tool.name` lists 21 tools: bash, bash_output, dashboard_report, data_diff, data_to_dashboard, edit, fdbt, find_custom_python_environment, glob, grep, kill_shell, read, reflect_semantic_model, review, skill, snowflake_create_artifact, snowflake_sql_execute, system_todo_write, task, web_search, write |
| `CodeExecutionTool_skill` | span | **the skill load**; on failure `code_execution.status = ERROR`, `status.code = 500`, `ToolError type=internal_error code=TOOL_INTERNAL_ERROR message=Skill not found: linkml_probe` |
| `CORTEX_AGENT_REQUEST` | event | `role.name = LINKML_METRICS_ROLE`, `user.name = <ADMIN_USER>`, `session.id`, token counts |

No skill was ever loaded, so the span of a skill **resource read** was not observed. Objectless calls have no agent
object, so this function cannot return their trace.

## Tokens and credits

Every successful turn: about **132,000 orchestration input tokens** for 2 planning steps (cache write 66,105 on the
first call, then cache reads), 150 to 830 output tokens, plus a 340-token guardrail call to `cygnal-qwen3-8b-032026`.
The `skill` tool description alone is 140,581 characters (the 93-skill bundled catalog); `disabled_skills` exists to
trim it. Credits: `CORTEX_AGENT_USAGE_HISTORY` lags up to an hour; the query is recorded in docs/phase0_findings.md
section 3 for session 3.

## Credits (read in session 3)

Read 2026-10-03 with the approved query of docs/phase0_findings.md section 3 (ACCOUNTADMIN, one SELECT on
`SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY`). 8 rows, as expected: call 1 (401) is not billed.
`SQL_QUERY_CREDITS` is null on every row; `ROLE_NAME` is `LINKML_METRICS_ROLE` on every row. `AGENT_NAME` is null on
the objectless calls (5 to 9).

| Call | Request id | Tokens | Cache write | Cache read | Output | Token credits |
|---|---|---|---|---|---|---|
| 2 | `000002f9-0000-4000-8000-0000000002f9` | 132,320 | 0.1074 | 0.0086 | 0.0012 | **0.1172** |
| 3 | `000002fa-0000-4000-8000-0000000002fa` | 132,373 | 0.0002 | 0.0172 | 0.0013 | **0.0186** |
| 4 | `000002fb-0000-4000-8000-0000000002fb` | 132,288 | 0.0000 | 0.0172 | 0.0010 | **0.0181** |
| 5 | `000002fc-0000-4000-8000-0000000002fc` | 132,485 | 0.0003 | 0.0172 | 0.0017 | **0.0192** |
| 6 | `000002fd-0000-4000-8000-0000000002fd` | 132,494 | 0.1076 | 0.0086 | 0.0017 | **0.1179** |
| 7 | `000002ff-0000-4000-8000-0000000002ff` | 66,497 | 0.1077 | 0.0000 | 0.0015 | **0.1092** |
| 8 | `00000300-0000-4000-8000-000000000300` | 135,167 | 0.0019 | 0.0173 | 0.0054 | **0.0246** |
| 9 | `000002fe-0000-4000-8000-0000000002fe` | 132,490 | 0.0133 | 0.0161 | 0.0017 | **0.0312** |
| n/a | n/a | n/a | n/a | n/a | n/a | **0.4559** |

Calls 7 and 8 are matched to their rows by start time (19:05:05 and 19:06:05 UTC, between calls 6 and 9) and by
token count (66,497 = one planning step, the turn that stopped on the bash approval). Their request ids were lost in
session 2; these are recovered here.

Reading: a turn costs about **0.11 credit when it writes the prompt cache** (about 66,000 tokens written, the
93-skill catalog included) and **about 0.02 credit when it reads it**. The cache was rewritten at calls 2, 6 and 7
(6 and 7 changed the spec; 7 dropped the skill block), so 3 cache writes make 75% of the total. Mean: 0.057 credit
per billed turn.
