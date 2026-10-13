# Figure 5: More right answers for fewer credits

**Caption.** Right figure, basis named, out of 24 questions, for seven ways to give an agent the same metric, best first, then cheapest first. Each label adds the agent's billed AI Credits per turn (median). The two versions with generated tools are in orange. One run per question, so the counts are counts, not rates. The raw-table version replayed the same questions after the campaign. The warehouse is billed apart.

**Alt text.** Seven horizontal bars, out of 24: Generated tools, gap-filled view, 24 of 24 · 0.020 credits per turn; Generated tools, raw tables, 22 of 24 · 0.020 credits per turn; Skill, script computes, 20 of 24 · 0.097 credits per turn; Hand-written semantic view, 19 of 24 · 0.055 credits per turn; Autopilot semantic view, 19 of 24 · 0.069 credits per turn; Skill, agent writes queries, 19 of 24 · 0.081 credits per turn; Generated semantic view, 19 of 24 · 0.104 credits per turn.

## Sources

- README section 4, stage 1 table: columns Right figure, basis named and Agent AI Credits per graded turn, billed, median; C-raw row included [measured].
- Credits rounded half up to three decimals from the README's four (0.0195 is 0.020).
- Underlying records: `snowflake/phase5_campaign/stage1_results.md`, sections 8 and 9; `snowflake/session13_craw/results.md`, sections 4 and 5 [measured].
- The score: `eval/grade.py`, grade_turn (verdict_figure_only), basis_named [documented].
- Plain names: Generated tools, gap-filled view = README row C; Generated tools, raw tables = README row C-raw; Skill, script computes = README row D; Hand-written semantic view = README row B1; Autopilot semantic view = README row A; Skill, agent writes queries = README row D′; Generated semantic view = README row B2.
