# Figure 4: Two ways to apply the closing rule

**Caption.** Left, a gap-filled view fills the missing months of each member's span, then is recomputed over the whole table at every query: 4.1% more rows, and a quarter question scans the table 2.0 times. Right, a procedure applies the rule at question time to the raw rows of the period only: the same closing stock on 12,304 of 12,304 members, for about 5 s of compilation per call. How each grows at scale is inferred, not measured.

**Alt text.** Two columns. Left: a grid with the gaps of each member's span filled and all of it read. Right: a grid with gaps and only the quarter's columns read. Under each, the measured figures and the inferred growth.

## Sources

- Rows 63,428 for 60,915 (+4.1 percent) and the quarter scan (2.0 times): README section 3, the closing-stock trade-off table; `snowflake/session13_craw/results.md`, section 1b [measured].
- 12,304 of 12,304 members equal and 5.2 s of compilation: README section 3; `snowflake/session13_craw/results.md`, section 3 [measured].
- Growth of each: README section 3, the Growth row, a reading of the SQL [inferred].
- The grids are an illustration, not data.
