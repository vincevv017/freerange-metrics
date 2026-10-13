# Figure 1: One missing month, two answers

**Caption.** The oat cereal bar 1 kg has no snapshot in Switzerland in June. Asked for its Q2 2026 closing stock, a native semantic view with NON ADDITIVE BY returns 350, May's stock carried into the close, and raises no error. The contract's rule gives 0.

**Alt text.** Bar chart of stock per month (April 400, May 350, June none); beside it, the quarter's closing stock: 350 from the native view, 0 under the contract's rule.

## Sources

- Stock per month: `data/traps.yaml`, hero_items, SKU-H11, stock_by_k (k = -2, -1; no row at k = 0) [documented].
- Months: k counted from the analysis month, as_of of `generated/reference_questions.yaml`; item, country and quarter from the question of CS_LAST_MONTH_GAP there [documented].
- Native value 350: `data/traps.yaml`, closing_stock, CS_LAST_MONTH_GAP, wrong.last_known_value; measured on the account in session 6 (`snowflake/probe_closing/results.md`, session 6 summary; README section 3) [measured].
- Contract value 0: the same trap, expected; the rule is `contract/stock_coverage.yaml`, invariant INV_CLOSING_LAST_PERIOD [documented].
