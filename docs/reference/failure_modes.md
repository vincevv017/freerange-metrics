<!-- GENERATED from contract/stock_coverage.yaml and data/traps.yaml by compiler/gen_reference.py. Do not edit: run `python compiler/gen_reference.py`. tests/test_reference.py regenerates this file and fails on any difference. -->
# Failure modes

The 16 failure modes of `contract/stock_coverage.yaml` (contract stock_coverage, version 0.5.1): known ways to get the metric wrong. For each: the wrong behaviour it guards against, the correct one, its reference question, the contract elements that declare `prevents` on it, and its trap in `data/traps.yaml`: the member that forces the behaviour, the correct answer and the value each named wrong behaviour returns, at the analysis month AS_OF. The keys are explained in [metamodel.md](metamodel.md).

| Id | Name | Wrong behaviour |
|---|---|---|
| [T1](#t1) | Ratio re-aggregation | Sum or average of child coverages |
| [T2](#t2) | Sparse forecast months | A row-based window skips missing months |
| [T3](#t3) | Stock-only filter pushed to forecast | The filter removes forecast rows, so coverage goes to 0 or null |
| [T4](#t4) | Time filter pushed to forecast | The month filter kills the future forecast rows |
| [T5](#t5) | Heterogeneous units | Packs of different sizes summed |
| [T6](#t6) | Missing analysis month | Coverage over the year (meaningless) |
| [T7](#t7) | Master-data fan-out | Item with two statuses counted twice |
| [T8](#t8) | Forecast but no stock | Member disappears |
| [NO_DEMAND](#no_demand) | No forecast at all | A number (0 or a division error) where coverage is undefined |
| [BEYOND_H](#beyond_h) | Stock outlasts the horizon | Average over the full loaded forecast range |
| [BULK_SCOPE](#bulk_scope) | Bulk stock without forecast | BULK stock counted against STANDARD forecast inflates a family's coverage (17.4 against 8.7 on v0) |
| [DIM_MIX](#dim_mix) | Mass and volume added | kg and L added in quantity equivalent for a group that holds both (a country, a range) |
| [T9](#t9) | Stale stock in coverage | The latest snapshot before the analysis month is used as its stock (NON ADDITIVE BY on a range or with no month): a stockout shows a positive coverage |
| [CS_LAST_MONTH_GAP](#cs_last_month_gap) | No snapshot in the last month of the period | The member's last known snapshot is carried to the period's close (or the months are summed or averaged) |
| [CS_MIDDLE_MONTH_GAP](#cs_middle_month_gap) | Gap in a middle month of the period | The months of the period summed or averaged |
| [CS_FAMILY](#cs_family) | Family that holds both gaps | Months summed or averaged, or each member's last known value added up |

## T1

**Ratio re-aggregation**

- **Wrong behaviour:** Sum or average of child coverages.
- **Correct behaviour:** Recompute from aggregated S and f at each grain.
- **Reference question:** "Stock coverage of flour and baking in France at AS_OF".
- **Source:** `data/traps.yaml#T1`.
- **Prevented by:** metric `stock_coverage`; member selection `SELECT_MEMBERS`; totals rule `TOTALS_RECOMPUTE`; refusal code `TOTALS_NOT_SUBSET`; invariant `INV_RECOMPUTE_TOTAL`; invariant `INV_MATCHES_REFERENCE`.
- **Trap** (`data/traps.yaml`, coverage): family_code PANTRY_FLOUR; country_code FR; grain family_code, country_code.
- **Correct answer:** 2.8 months.
- **Wrong answers:** sum of children: 12.5; average of children: 6.25; stock weighted average of children: 10.3571.

## T2

**Sparse forecast months**

- **Wrong behaviour:** A row-based window skips missing months.
- **Correct behaviour:** Densify the calendar: a missing month is 0.
- **Reference question:** "Stock coverage of SKU-H03 in Germany at AS_OF".
- **Source:** `data/traps.yaml#T2`.
- **Prevented by:** metric `stock_coverage`; quality expectation `QE_FORECAST_DENSE`; invariant `INV_DENSIFY`; invariant `INV_MATCHES_REFERENCE`.
- **Trap** (`data/traps.yaml`, coverage): sku_code SKU-H03 (Salted almonds 1 kg); country_code DE; grain sku_code, country_code.
- **Correct answer:** 7 months, warning `FORECAST_GAPS_FILLED` (2).
- **Wrong answers:** row based window: 5.

## T3

**Stock-only filter pushed to forecast**

- **Wrong behaviour:** The filter removes forecast rows, so coverage goes to 0 or null.
- **Correct behaviour:** The forecast ignores stock-only attributes.
- **Reference question:** "Stock coverage of released lots of SKU-H04 in Italy at AS_OF".
- **Source:** `data/traps.yaml#T3`.
- **Prevented by:** attribute `batch_status`; attribute `expiry_bucket`; attribute `warehouse_code`; attribute `warehouse_type`; attribute `item_type`; refusal code `ATTRIBUTE_UNKNOWN`; refusal code `ATTRIBUTE_UNCLASSIFIED`; refusal code `ATTRIBUTE_NOT_APPLICABLE`; invariant `INV_SNAPSHOT_ONLY_FILTER_KEEPS_FLOW`; invariant `INV_MATCHES_REFERENCE`.
- **Trap** (`data/traps.yaml`, coverage): sku_code SKU-H04 (Green tea loose-leaf 1 kg); country_code IT; batch_status RELEASED; grain sku_code, country_code.
- **Correct answer:** 6 months.
- **Wrong answers:** filter pushed to forecast: no value (null).

## T4

**Time filter pushed to forecast**

- **Wrong behaviour:** The month filter kills the future forecast rows.
- **Correct behaviour:** The forecast window is relative to t, not filtered by it.
- **Reference question:** "Stock coverage of SKU-H05 in Spain for the AS_OF month".
- **Source:** `data/traps.yaml#T4`.
- **Prevented by:** metric `stock_coverage`; invariant `INV_WINDOW_EXCLUDES_ANCHOR`; invariant `INV_MATCHES_REFERENCE`.
- **Trap** (`data/traps.yaml`, coverage): sku_code SKU-H05 (Strawberry jam 1 kg); country_code ES; grain sku_code, country_code.
- **Correct answer:** 8.5 months.
- **Wrong answers:** filter pushed to forecast: no value (null); window starts at as of: 7.7143.

## T5

**Heterogeneous units**

- **Wrong behaviour:** Packs of different sizes summed.
- **Correct behaviour:** An item's own unit for one item only; across items, quantity equivalent or value; refuse the own unit across items (BASIS_NOT_COMPARABLE).
- **Reference question:** "Stock coverage of dry pasta in the United Kingdom in number of packs at AS_OF".
- **Source:** `data/traps.yaml#T5 (refusal trap; docs/DEFINITION.md#4)`.
- **Prevented by:** basis `NATIVE`; basis `QTY_EQ`; basis model `ITEM_BASIS`; refusal code `BASIS_NOT_COMPARABLE`; quality expectation `QE_EQ_FACTOR`; quality expectation `QE_ITEM_DIMENSION`; invariant `INV_UNIT_SCALE`; invariant `INV_NATIVE_EQUALS_QTY_EQ`.
- **Trap** (`data/traps.yaml`, coverage): family_code PANTRY_PASTA; country_code GB; grain family_code, country_code; basis NATIVE.
- **Correct answer:** refusal `BASIS_NOT_COMPARABLE`, bases allowed QTY_EQ, VALUE.
- **Wrong answers:** raw units summed: 8.4966.

## T6

**Missing analysis month**

- **Wrong behaviour:** Coverage over the year (meaningless).
- **Correct behaviour:** An explicit as-of month is required: ask or refuse.
- **Reference question:** "Stock coverage of flour and baking in France over the whole year 2026".
- **Source:** `data/traps.yaml#T6 (refusal trap; docs/DEFINITION.md#4)`.
- **Prevented by:** totals rule `TOTALS_RECOMPUTE`; analysis periods `AS_OF_MONTHS`; refusal code `AS_OF_MISSING`; refusal code `AS_OF_INVALID`; refusal code `AS_OF_NOT_MONTH_START`; refusal code `AS_OF_NO_SNAPSHOT`; quality expectation `QE_HORIZON_LOADED`; quality expectation `QE_FORECAST_REACH`; invariant `INV_SERIES_POINTWISE`.
- **Trap** (`data/traps.yaml`, coverage): family_code PANTRY_FLOUR; country_code FR; grain family_code, country_code.
- **Correct answer:** refusal `AS_OF_MISSING`.

## T7

**Master-data fan-out**

- **Wrong behaviour:** Item with two statuses counted twice.
- **Correct behaviour:** Enforce one row per item on the item dimension.
- **Reference question:** "Stock coverage of cooking oils in Sweden at AS_OF".
- **Source:** `data/traps.yaml#T7`.
- **Prevented by:** attribute `lifecycle_status`; refusal code `MASTER_DATA_FANOUT`; quality expectation `QE_ITEM_GRAIN`; quality expectation `QE_SKU_FAMILY`; invariant `INV_MATCHES_REFERENCE`.
- **Trap** (`data/traps.yaml`, coverage): family_code PANTRY_OIL; country_code SE; grain family_code, country_code.
- **Correct answer:** 2.25 months, warning `MASTER_DATA_DUPLICATES` (1).
- **Wrong answers:** naive join on duplicated item: 3; naive join stock qty eq: 1,500.

## T8

**Forecast but no stock**

- **Wrong behaviour:** Member disappears.
- **Correct behaviour:** Coverage 0, row kept (decision 2).
- **Reference question:** "Stock coverage of SKU-H08 in the Netherlands at AS_OF".
- **Source:** `data/traps.yaml#T8`.
- **Prevented by:** outcome 1 `SNAPSHOT_NULL_OR_ZERO`; member-set rule `MEMBERS_SPINE`; quality expectation `QE_STOCK_ITEM_REF`; invariant `INV_FLAG_CONSISTENT`; invariant `INV_MATCHES_REFERENCE`.
- **Trap** (`data/traps.yaml`, coverage): sku_code SKU-H08 (Cashew nuts 1 kg); country_code NL; grain sku_code, country_code.
- **Correct answer:** 0 months, flag `NO_STOCK`.
- **Wrong answers:** member disappears: missing.

## NO_DEMAND

**No forecast at all**

- **Wrong behaviour:** A number (0 or a division error) where coverage is undefined.
- **Correct behaviour:** Null with flag NO_DEMAND (decision 2).
- **Reference question:** "Stock coverage of SKU-H09 in Belgium at AS_OF".
- **Source:** `data/traps.yaml#NO_DEMAND`.
- **Prevented by:** outcome 3 `NO_FLOW_IN_WINDOW`; invariant `INV_FLAG_CONSISTENT`; invariant `INV_MATCHES_REFERENCE`.
- **Trap** (`data/traps.yaml`, coverage): sku_code SKU-H09 (Iced tea summer edition 1 L (discontinued)); country_code BE; grain sku_code, country_code.
- **Correct answer:** no value (null), flag `NO_DEMAND`.

## BEYOND_H

**Stock outlasts the horizon**

- **Wrong behaviour:** Average over the full loaded forecast range.
- **Correct behaviour:** Average of non-zero months bounded to H, flag BEYOND_HORIZON (decision 1).
- **Reference question:** "Stock coverage of SKU-H10 in Poland at AS_OF".
- **Source:** `data/traps.yaml#BEYOND_H`.
- **Prevented by:** beyond-horizon rule `beyond_horizon`; invariant `INV_FLAG_CONSISTENT`; invariant `INV_MATCHES_REFERENCE`.
- **Trap** (`data/traps.yaml`, coverage): sku_code SKU-H10 (Arabica beans 1 kg); country_code PL; grain sku_code, country_code.
- **Correct answer:** 50 months, flag `BEYOND_HORIZON`, warning `FORECAST_GAPS_FILLED` (2).
- **Wrong answers:** average over full forecast range: 11.9718.

## BULK_SCOPE

**Bulk stock without forecast**

- **Wrong behaviour:** BULK stock counted against STANDARD forecast inflates a family's coverage (17.4 against 8.7 on v0).
- **Correct behaviour:** Excluded by default, included on an explicit item_type filter, excluded amount reported (decision 5).
- **Reference question:** "Stock coverage of ground coffee at AS_OF".
- **Source:** `data/traps.yaml#BULK_SCOPE (HOT_GROUND; docs/phase0_findings.md#8)`.
- **Prevented by:** attribute `item_type`; default scope `SCOPE_ITEM_TYPE`; invariant `INV_DEFAULT_SCOPE`.
- **Trap** (`data/traps.yaml`, coverage): family_code HOT_GROUND; grain family_code.
- **Correct answer:** 8.6735 months, warning `FORECAST_GAPS_FILLED` (2), warning `DEFAULT_SCOPE_EXCLUDED` (51,475.5).
- **Wrong answers:** bulk counted by default: 17.4424.

## DIM_MIX

**Mass and volume added**

- **Wrong behaviour:** kg and L added in quantity equivalent for a group that holds both (a country, a range).
- **Correct behaviour:** Refuse quantity equivalent where a returned row mixes dimensions (BASIS_NOT_COMPARABLE, VALUE allowed); value is comparable.
- **Reference question:** "Stock coverage in France in AS_OF".
- **Source:** `data/traps.yaml#DIM_MIX (refusal trap; docs/DEFINITION.md#4)`.
- **Prevented by:** attribute `dimension`; basis `QTY_EQ`; basis model `ITEM_BASIS`; refusal code `BASIS_NOT_COMPARABLE`; quality expectation `QE_ITEM_DIMENSION`.
- **Trap** (`data/traps.yaml`, coverage): country_code FR; grain country_code; basis QTY_EQ.
- **Correct answer:** refusal `BASIS_NOT_COMPARABLE`, bases allowed VALUE.
- **Wrong answers:** kg and l added: 10.208.

## T9

**Stale stock in coverage**

- **Wrong behaviour:** The latest snapshot before the analysis month is used as its stock (NON ADDITIVE BY on a range or with no month): a stockout shows a positive coverage.
- **Correct behaviour:** Stock read at exactly the analysis month, absent = 0: coverage 0 with NO_STOCK; native consumers read the gap-filled snapshot.
- **Reference question:** "Stock coverage of SKU-H11 in Switzerland at AS_OF".
- **Source:** `data/traps.yaml#T9`.
- **Prevented by:** period aggregation `CLOSING_STOCK`; outcome 1 `SNAPSHOT_NULL_OR_ZERO`.
- **Trap** (`data/traps.yaml`, coverage): sku_code SKU-H11 (Oat cereal bar 1 kg); country_code CH; grain sku_code, country_code.
- **Correct answer:** 0 months, flag `NO_STOCK`.
- **Wrong answers:** last known stock over forecast: 3.5.

## CS_LAST_MONTH_GAP

**No snapshot in the last month of the period**

- **Wrong behaviour:** The member's last known snapshot is carried to the period's close (or the months are summed or averaged).
- **Correct behaviour:** Closing stock 0, the member keeps its row.
- **Reference question:** "Closing stock of SKU-H11 in Switzerland for Q2 2026".
- **Source:** `data/traps.yaml#CS_LAST_MONTH_GAP`.
- **Prevented by:** period aggregation `CLOSING_STOCK`; invariant `INV_CLOSING_LAST_PERIOD`.
- **Trap** (`data/traps.yaml`, closing stock): sku_code SKU-H11 (Oat cereal bar 1 kg); country_code CH; grain sku_code, country_code.
- **Correct answer:** 0 (closing stock, quantity equivalent).
- **Wrong answers:** sum over period: 750; last known value: 350; average over period: 250.

## CS_MIDDLE_MONTH_GAP

**Gap in a middle month of the period**

- **Wrong behaviour:** The months of the period summed or averaged.
- **Correct behaviour:** The snapshot of the last month.
- **Reference question:** "Closing stock of SKU-H12 in Switzerland for Q2 2026".
- **Source:** `data/traps.yaml#CS_MIDDLE_MONTH_GAP`.
- **Prevented by:** period aggregation `CLOSING_STOCK`; invariant `INV_CLOSING_LAST_PERIOD`.
- **Trap** (`data/traps.yaml`, closing stock): sku_code SKU-H12 (Nut cereal bar 1 kg); country_code CH; grain sku_code, country_code.
- **Correct answer:** 450 (closing stock, quantity equivalent).
- **Wrong answers:** sum over period: 950; average over period: 316.6667.

## CS_FAMILY

**Family that holds both gaps**

- **Wrong behaviour:** Months summed or averaged, or each member's last known value added up.
- **Correct behaviour:** Sum over the members of the last month's snapshot only.
- **Reference question:** "Closing stock of cereal bars in Switzerland for Q2 2026".
- **Source:** `data/traps.yaml#CS_FAMILY`.
- **Prevented by:** period aggregation `CLOSING_STOCK`; invariant `INV_CLOSING_LAST_PERIOD`.
- **Trap** (`data/traps.yaml`, closing stock): family_code SNACK_BARS; country_code CH; grain family_code, country_code.
- **Correct answer:** 450 (closing stock, quantity equivalent).
- **Wrong answers:** sum over period: 1,700; last known value per sku: 800; average over period: 566.6667.
