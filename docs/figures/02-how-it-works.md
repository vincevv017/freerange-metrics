# Figure 2: How it works

**Caption.** A metric contract is the only hand-written source. The compiler validates it and writes files into generated/: two procedures, semantic views, data metric functions, the agent's definition and the reference questions. A script deploys those files in Snowflake; the compiler calls nothing. The agent picks the parameters and gets back a figure, a warning or a coded refusal; it never computes the metric. Data metric functions check the tables and are in no answer's path. The evaluation harness in eval/ asks the agent each reference question and grades the answer; it is not Snowflake's agent evaluations. The data tables are loaded from the published dataset, not generated.

**Alt text.** Diagram in four steps. Declare: the metric contract. Compile: the compiler writes files into generated/ (two procedures, semantic views, and the views they read, data metric functions, the agent's definition: instructions, tool descriptions, reference questions). Deploy: a script runs them in Snowflake. In Snowflake: the Cortex Agent calls STOCK_COVERAGE and CLOSING_STOCK or the semantic view, which read the seven data tables, not generated; data metric functions check those tables apart from any answer. Beside it, the evaluation harness (eval/ in the repository, not Snowflake's agent evaluations) asks the agent each reference question and grades the answer.

## Sources

- Procedures and semantic view, as the agent binds them: `generated/agent_c_raw.yaml`, tool_resources: STOCK_COVERAGE (coverage) and CLOSING_STOCK (closing stock), LINKML_C_RAW_SV [documented].
- What the compiler writes: README section 2, the table of generated files; each generator's docstring in `compiler/` (gen_procedure, gen_closing_procedure, gen_closing_sv, gen_native_sv, gen_craw, gen_dmf, gen_agent, gen_questions). No module of `compiler/` imports the Snowflake connector [documented].
- The agent's definition is generated: `generated/agent_c.yaml` and `generated/agent_c_raw.yaml` (instructions, tool descriptions, procedure bindings) [documented].
- Data metric functions: `generated/dmf.sql`, 17 custom functions and ad hoc checks; nothing attached to a table, no schedule (`compiler/gen_dmf.py`); run by `snowflake/phase2_dmf/run_dmf.py`. No procedure calls them: the procedures run their own in-call checks [documented].
- Reference questions: `generated/reference_questions.yaml`, 31 questions, the evaluation's question set (`compiler/gen_questions.py`) [documented].
- Evaluation harness: `eval/campaign.py` asks the agents over Snowflake's REST API through `snowflake/probe_b/mount/run_call.py`; `eval/grade.py` grades each answer with the deterministic rubric `eval/rubric.yaml` against the expected values of `generated/reference_questions.yaml`. No Snowflake agent evaluation is used [documented].
- Deployment: the scripts `snowflake/phase3_procedure/deploy.py` (SQL files), `snowflake/phase4_others/deploy_sv.py` (semantic view YAML), `snowflake/phase4_agent_c/deploy_agent.py` (agent C) read the generated files [documented].
- Not generated: the 7 tables of `contract/stock_coverage.yaml`, loaded by `data/load_snowflake.py` from the published dataset; the database, role and warehouse, `snowflake/00_setup.sql` [documented].
- Drawn by `tools/make_figures.py` since session 17c; `assets/docs/how-it-works.png`, the README's diagram, is a copy of this PNG.
