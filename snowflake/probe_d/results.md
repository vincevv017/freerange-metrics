# Probe D: a skill script under `code_execution` (session 4)

Run 2026-10-03, 07:30 UTC, by `snowflake/probe_b/mount/run_call.py --budget d --policy stop`, as **LINKML_SVC**
(key-pair JWT, no role or warehouse header), on a **permanent** agent `LINKML_METRICS.RAW.LINKML_D_PROBE` owned by
`LINKML_METRICS_ROLE`. Spec: `spec_d_probe.yaml` (session 3 `spec_4` with `code_execution` in place of
`code_toolset_all`, `permission_policy: always_ask`, orchestration `claude-sonnet-5-5`). Skill: `skills/linkml-probe-py`
(SKILL.md + `probe.py`, written for Python, three steps), alone on a fresh plain internal stage
`LINKML_METRICS.RAW.SKILLS_D_PROBE`. Setup and teardown: `setup.py`, as perso with the project role and no secondary
role. Cap 3 agent calls, **1 used**: the question was answered by call 1. Agent and stage dropped right after. Raw
events and trace rows stay outside the repository.

Why a new skill: `linkml-probe` (sessions 2 and 3) is written for `bash` and the SQL tool, which `code_execution` was
not expected to offer, so its failure would have said nothing about D. The project owner asked for a Python version.

## Call

| # | Request id | Seconds (first byte / total) | Approval requests | Result |
|---|---|---|---|---|
| 1 | `0000032a-0000-4000-8000-00000000032a` | 2.0 / 46.7 | **none** | script runs; its Snowflake query is refused by a restricted session scope |

## What happened, in order

1. **Load path: `server_skill`.** Tool use `server_skill`, input `{"skill_name": "linkml-probe-py"}`, status
   `success`. The result returns the SKILL.md body inline plus a "Skill Directory Contents" table listing
   `/mnt/skills/stage/linkml_metrics_raw_skills_d_probe/skills/linkml-probe-py/probe.py` with size **0 B** (the staged
   file is 192 bytes; `LIST @stage` before the call).
2. **The code tool is `bash`.** Under `code_execution`, the agent issued two `bash` tool calls (type `bash`, name
   `bash`), not a Python tool. The first ran steps 1 and 3 as `python3 - <<'E' ...` and `python3 -c ...`; the second
   ran `python3 -c 'exec(open("/mnt/skills/stage/linkml_metrics_raw_skills_d_probe/skills/linkml-probe-py/probe.py").read())'`.
3. **No approval was asked**, for either bash call, although the spec sets `permission_policy: always_ask` on
   `code_execution`. Session 3 measured a bash approval request on `code_toolset_all` with the same policy. The stop
   policy had nothing to stop on.
4. **Step 1 deviated from the skill.** The agent added `/mnt` to the excluded directories, and said it did so because
   "the sandbox rules forbid walking it". The scan therefore listed only bundled skills and vendored `probe.py` files
   under `/app`, `/opt` and `/snowflake/skills-cli`, not the stage skill. `cwd` = `/home/nonroot/workspace`.
5. **Script present and executed.** The agent took the path from the skill's file table. `exec` of `probe.py` reached
   `cursor.execute`: the file is not empty in the sandbox, whatever the table says.
6. **Data access refused.** `snowflake.connector.connect()` with no argument succeeded; the query failed with, verbatim:

   ```
   snowflake.connector.errors.ProgrammingError: 002003 (02000): SQL compilation error:
   Database 'LINKML_METRICS' does not exist or not authorized. Restricted session scope: USER SPECIFIED does not include USAGE or equivalent access to DATABASE LINKML_METRICS.
   ```
7. **Environment.** Variable names only: `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_HOST`, `SNOWFLAKE_LOGIN_NAME`,
   `SNOWFLAKE_REQUEST_ID`, `SNOWFLAKE_ROLE`, `SNOWFLAKE_TOKEN`, `SNOWFLAKE_TOKEN_FILE_PATH`, `SNOWFLAKE_USERNAME`,
   `SNOWFLAKE_WAREHOUSE`: the same nine names as under `code_toolset_all` in session 3.
8. The answer followed the output contract (three blocks and a line on `probe.py`); the agent said it shortened paths
   in the traceback with `...`. The tool result above is the unshortened one.

## Trace spans

`Agent`, `UserMemoryInjection`, **`ServerSkillTool_linkml-probe-py`** (`status = SUCCESS`, `.status.code = 200`,
`.duration = 605` ms, `.already_loaded = false`, `.source_category = agent`), `ReasoningAgentStepPlanning-0..3`, two
**`CodeExecutionTool_bash`** (`agent.tool.code_execution.name = bash`, `.argument.name = description,command`,
`SUCCESS`, 2,742 ms and 5,075 ms), `ReasoningAgentStepResponseGeneration-4`, `LLM Suggested Queries`,
`AgentV2RequestResponseInfo`; event `CORTEX_AGENT_REQUEST` with `user.name = LINKML_SVC`,
`role.name = LINKML_METRICS_ROLE`. No `CodingAgentRun` span: the sandbox is driven by the orchestrator here, not by
the coding agent of `code_toolset_all`. The `bash` span reports `SUCCESS` although the Python inside it raised.

## Tokens

| Orchestration input (cache write / read / uncached) | Output | Guardrail input |
|---|---|---|
| 83,913 (20,964 / 62,933 / 16) | 4,198 | 3,912 |

About 2.5 times a no-code-tool turn (33,000 to 36,000) and below a `code_toolset_all` turn (about 133,000), for four
planning steps.

## Credits

Read 2026-10-03 (session 5) with the session 3 query, the single read-only SELECT approved under ACCOUNTADMIN:
`SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY`, `USER_NAME = 'LINKML_SVC'`, 2026-10-03 07:29 to 07:32 UTC.
**1 row, as expected**: request `0000032a-0000-4000-8000-00000000032a`, agent `LINKML_D_PROBE`, `role_name` =
`LINKML_METRICS_ROLE`, `SQL_QUERY_CREDITS` null.

| Tokens (billed) | Token credits | Cache write input | Cache read input | Uncached input | Output |
|---|---|---|---|---|---|
| 88,111 | **0.0696** | 0.0341 | 0.0082 | 0.00002 | 0.0273 |

The billed tokens are the orchestration input plus output above (83,913 + 4,198); the guardrail tokens are not in
this row. All credits are attributed to `claude-sonnet-5-5`. One `code_execution` turn costs about 3.5 times a
cache-reading no-code turn of session 3 (0.02) and below a cache-writing `code_toolset_all` turn (about 0.11).
