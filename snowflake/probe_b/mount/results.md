# Skill mount diagnosis: raw results (session 3, step 2)

Run 2026-10-03, 06:30 to 06:36 UTC, by `run_call.py`, as **LINKML_SVC** (service user, key-pair JWT, default role
`LINKML_METRICS_ROLE`, default warehouse `LINKML_METRICS_WH`, no secondary role), with **no** `X-Snowflake-Role` or
`X-Snowflake-Warehouse` header, on a **permanent** agent `LINKML_METRICS.RAW.LINKML_SKILL_PROBE` owned by the project
role. Orchestration model `claude-sonnet-5-5` (confirmed by `metadata.orchestration_model`). Cap: 6 agent calls, 6
used (call 6 below). Raw events and traces stay outside the repository.

Stage `LINKML_METRICS.RAW.SKILLS_PROBE`: plain `CREATE STAGE` (internal, `has_encryption_key = N`, no directory table),
files `PUT` with `AUTO_COMPRESS = FALSE` under `skills/linkml-echo/` and `skills/linkml-probe/`. Same settings as the
known-good stage measured by the project owner on another account. Both the agent and the stage were dropped at the
end of the step.

Known-good configuration, for comparison [measured, other account, by the project owner on 2026-10-02]: permanent
agent owned by a project role, `claude-sonnet-5`, skills block of the same shape with no pinned description, tools =
one `cortex_analyst_text_to_sql` and three generic procedures, no code tool, an instructions-only skill that loads.

## Calls

One spec change per call; each spec is in this folder. Question: "Run the linkml echo." (calls 1 to 3) or "Run the
linkml probe." (call 4). Neither question contains the expected answer.

| # | Spec | Request id | Seconds (first byte / total) | Skill tool | Result | Answer |
|---|---|---|---|---|---|---|
| 1 | `spec_1_no_code.yaml`: no tool, skill linkml-echo | `000002f2-0000-4000-8000-0000000002f2` | 1.5 / 6.7 | `server_skill`, input `{"skill_name": "linkml-echo"}` | `success`; content = the SKILL.md body | `SKILL LOADED: linkml-echo` exact |
| 2 | `spec_2_code_execution.yaml`: + `code_execution` (`always_ask`) | `000002f3-0000-4000-8000-0000000002f3` | 1.6 / 6.4 | `server_skill`, same input | `success` | exact |
| 3 | `spec_3_code_toolset_all.yaml`: `code_execution` replaced by `code_toolset_all` (`always_ask`) | `000002f4-0000-4000-8000-0000000002f4` | 4.4 / 17.1 | `skill` (sandbox), input `{"command": "linkml-echo"}` | `success`; `skill_path` = `/mnt/skills/stage/linkml_metrics_raw_skills_probe/skills/linkml-echo/`, `files: []` | exact |
| 4 | `spec_4_probe_code_toolset_all.yaml`: spec 3 with skill linkml-probe | `000002f5-0000-4000-8000-0000000002f5` | 1.6 / 15.4 | `skill`, `{"command": "linkml-probe"}` | `success`; `files: [probe.py]` | stops on a bash approval request |
| 5 | same, resumed with the decision | `000002f6-0000-4000-8000-0000000002f6` | 1.6 / 17.5 | n/a | bash succeeds | two fenced blocks, as the output contract says |
| 6 | `spec_1_no_code.yaml` again (agent and stage recreated), called as **<ADMIN_USER>** with a JWT and the session 2 headers `X-Snowflake-Role: LINKML_METRICS_ROLE`, `X-Snowflake-Warehouse: LINKML_METRICS_WH` | `000002f7-0000-4000-8000-0000000002f7` | 1.2 / 5.7 | `server_skill` | `success` | exact |

No `response.warning` on any call.

## Call 6: isolating the session 2 failure

Run at 07:01 UTC, after probe C0. <ADMIN_USER> is the session 2 caller: `TYPE = PERSON`, `DEFAULT_ROLE` and
`DEFAULT_WAREHOUSE` null, `DEFAULT_SECONDARY_ROLES = ["ALL"]`. The agent has no tool, so <ADMIN_USER>'s secondary roles
reach no data. **The skill loads**, with the same span (`ServerSkillTool_linkml-echo`, `SUCCESS`) and the same token
count as call 1 (35,735, cache read 22,274). Call 1, the first call of the session, already read 22,274 tokens from
cache, so that part is a platform prefix, not a cache shared between the two callers.

Reading: the caller's missing default role and warehouse did not stop the mount. What differs between every session 2
failure and every session 3 success is the agent object: session 2 used a TEMPORARY agent or the objectless endpoint,
session 3 a permanent agent. One combination is untested: <ADMIN_USER> on a permanent agent **with
`code_toolset_all`** (every session 2 run had it; call 6 has no tool, and calls 3 and 4 had LINKML_SVC).

## Call 4: the skill script and the SQL tool

Approval request (call 4), verbatim, and decision:

| Tool | Input | Options offered | Decision |
|---|---|---|---|
| `bash` | `cd /mnt/skills/stage/linkml_metrics_raw_skills_probe/skills/linkml-probe/ && python3 probe.py; env \| cut -d= -f1 \| grep -i snowflake \| sort` (description "Run linkml probe script") | `Allow this command`, `Allow all bash for this session`, `Deny` | `Allow this command` (rule: step 1 preceded by `cd` to the skill folder) |

`snowflake_sql_execute` asked for no approval and **ran in call 4, before the bash decision was sent**: the agent
issued both tool calls in one planning step, the SQL one executed, the bash one waited.

Outputs (call 5):

```
step 1
[('LINKML_METRICS_ROLE', '{"roles":"","value":""}', 15162)]
SNOWFLAKE_ACCOUNT
SNOWFLAKE_HOST
SNOWFLAKE_LOGIN_NAME
SNOWFLAKE_REQUEST_ID
SNOWFLAKE_ROLE
SNOWFLAKE_TOKEN
SNOWFLAKE_TOKEN_FILE_PATH
SNOWFLAKE_USERNAME
SNOWFLAKE_WAREHOUSE

step 2
CURRENT_ROLE(),CURRENT_SECONDARY_ROLES(),COUNT(*)
LINKML_METRICS_ROLE,"{""roles"":"""",""value"":""""}",15162
```

The skill **script** ran from the mounted stage folder and queried data with its own connector session. Both the
script and the SQL tool ran as `LINKML_METRICS_ROLE` with **no secondary role**. Session 2 measured the same two
paths with `ACCOUNTADMIN,<OTHER_ROLES>` as secondary roles under <ADMIN_USER>.

## Sandbox skill catalog (call 3)

The `CodingAgent.Step-0` span of call 3 lists the `skill` tool's catalog: the bundled skills plus **two** entries with
`<location>stage</location>`, `linkml-echo` **and `linkml-probe`**. The spec of call 3 declared linkml-echo only;
linkml-probe was only present on the same stage. In session 2 the catalog listed 93 skills, all `bundled`.

## Trace spans

`SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS('LINKML_METRICS', 'RAW', 'LINKML_SKILL_PROBE', 'CORTEX AGENT')`, read as
LINKML_SVC.

| Configuration | Spans per turn | Skill load span | Attributes on the skill span |
|---|---|---|---|
| No code tool, or `code_execution` (calls 1, 2) | `Agent`, `UserMemoryInjection`, `ServerSkillTool_linkml-echo`, `ReasoningAgentStepPlanning-0`, `ReasoningAgentStepResponseGeneration-1`, `LLM Suggested Queries`, `AgentV2RequestResponseInfo`, event `CORTEX_AGENT_REQUEST` | **`ServerSkillTool_<skill name>`** | `agent.tool.server_skill.status = SUCCESS`, `.status.code = 200`, `.duration` (419 ms on call 1), `.already_loaded = false`, `.source_category = agent`, `agent.tool.id` |
| `code_toolset_all` (calls 3 to 5) | `Agent`, `CodingAgentRun`, `CodingAgent.Step-N`, `CodeExecutionTool_<tool>`, event `CORTEX_AGENT_REQUEST` | **`CodeExecutionTool_skill`** | `agent.tool.code_execution.name = skill`, `.argument.name = command`, `.status = SUCCESS`, `.status.code = 200`, `.duration` (8 ms), `.request_id` |

Skill **resource read**: under `code_toolset_all`, a resource is a file in the mounted folder, read by an ordinary
tool (here `CodeExecutionTool_bash`, 5,170 ms); there is no dedicated span. Under `server_skill` no resource read was
observed: linkml-echo has no resource.

`CORTEX_AGENT_REQUEST`: `user.name = LINKML_SVC`, `role.name = LINKML_METRICS_ROLE` on calls 1 to 5;
`user.name = <ADMIN_USER>` on call 6.

## Tokens

| Call | Orchestration input tokens (cache write / read) | Output | Guardrail input |
|---|---|---|---|
| 1 | 35,735 (13,451 / 22,274) | 82 | 457 |
| 2 | 32,528 (12,382 / 20,136) | 82 | 453 |
| 3 | 132,716 (66,483 / 66,227) | 68 | 468 |
| 4 | 133,227 (8,803 / 124,418) | 344 | 778 |
| 5 | 67,727 (731 / 66,994) | n/a | 1,134 |
| 6 | 35,735 (13,451 / 22,274) | 82 | 452 |

Adding `code_execution` does not change the per-turn size (32,528 against 35,735). `code_toolset_all` multiplies it by
about 4 (the bundled catalog, as in session 2).

## Credits

Read at the end of session 3 (query and window in `snowflake/probe_c0/results.md`). `SQL_QUERY_CREDITS` null.

| Call | Request id | Tokens | Cache write / read / output credits | Token credits |
|---|---|---|---|---|
| 1 | `000002f2-0000-4000-8000-0000000002f2` | 35,817 | 0.0219 / 0.0029 / 0.0005 | **0.0253** |
| 2 | `000002f3-0000-4000-8000-0000000002f3` | 32,610 | 0.0201 / 0.0026 / 0.0005 | **0.0233** |
| 3 | `000002f4-0000-4000-8000-0000000002f4` | 132,784 | 0.1080 / 0.0086 / 0.0004 | **0.1171** |
| 4 | `000002f5-0000-4000-8000-0000000002f5` | 133,571 | 0.0143 / 0.0162 / 0.0022 | **0.0327** |
| 5 | `000002f6-0000-4000-8000-0000000002f6` | 68,016 | 0.0012 / 0.0087 / 0.0019 | **0.0118** |
| 6 (<ADMIN_USER>) | `000002f7-0000-4000-8000-0000000002f7` | 35,817 | 0.0219 / 0.0029 / 0.0005 | **0.0253** |
| n/a | n/a | n/a | n/a | **0.2355** |

Call 6 is billed exactly like call 1: same tokens, same cache write and read.
