# Figure 3: One question, two calls

**Caption.** Asked for France's stock coverage, the agent with generated tools on raw tables picks the parameters and calls the generated procedure. The procedure refuses the kg or L equivalent basis with BASIS_NOT_COMPARABLE: France mixes kg and L. The agent calls again on value; the procedure sums the stock and forecast of France's standard items and computes the coverage once, 8.7 months, which the agent relays. Every number comes from the procedure.

**Alt text.** Five blocks: the question; the agent picks June 2026, France, kg or L equivalent; the procedure refuses with BASIS_NOT_COMPARABLE, France mixes kg and L; the agent retries on value and the procedure computes 8.7 months; the answer's first sentence, quoted: France's stock coverage in June 2026 is about 8.7 months.

## Sources

- Question and parameters (month, grain, filter, basis): `generated/reference_questions.yaml`, DIM_MIX, question and tool_parameters [documented].
- Refusal code, bases allowed and the second call's basis: the same entry, expected.refusal, allowed_bases, offer_instead.basis [documented].
- Refusal reason: expected.reason_template filled with the QTY_EQ not_comparable_reason of `contract/stock_coverage.yaml` [documented]. The turn's two calls (QTY_EQ, then VALUE), its refusal code and this reason text are those of summary_cr_dim_mix_craw_s1_r1.json in ../linkml-metrics-runs/campaign/ (session 13) [measured, run folder, not published]; the same procedure returned the same text and calls in the recorded turn c_dim_mix of `eval/fixtures/recorded_turns.jsonl` (session 8) [measured].
- Value 8.70: offer_instead.value, recomputed from the dataset by two oracle references [measured, the offline suite].
- Summed, then computed once: `generated/stock_coverage_procedure_sql.sql`, the coverage statement (CTEs stock and fc sum stock and monthly forecast at the grain asked; the coverage is computed on those sums); the default scope keeps STANDARD items only, BULK stock is left out unless item_type is filtered: `contract/stock_coverage.yaml`, default_scopes, SCOPE_ITEM_TYPE [documented].
- Answer: `eval/fixtures/grades_craw-s1.json`, CR_DIM_MIX_craw-s1_r1, verdict correct (rubric 3.2); the first sentence quoted verbatim, the whole answer in figures.json [measured].
