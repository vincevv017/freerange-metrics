# Stock Coverage: definition

> Status: **draft**. The rules below are settled and encoded in [`contract/stock_coverage.yaml`](../contract/stock_coverage.yaml), the single source; the choices still to confirm are the contract's `open_decisions`. The definition follows a legacy BI implementation. It has been rewritten from scratch and uses only synthetic data.

## 1. Business definition

**Stock coverage** answers one question: *if nothing is replenished, how many months will the stock on hand last against the demand forecast?*

- **Stock**: closing stock in the analysis month *t*.
- **Forecast**: monthly demand forecast for months *t+1* to *t+H*. Coverage looks **forward** and starts the month **after** the analysis month.
- **Horizon** *H* = **24 months**.
- **Result**: always **months**, fractional, whatever the basis. The month in which the stock runs out is interpolated
  linearly. A coverage is never given in kg, L, EUR or packs.
- **Basis**: stock and forecast are measured on one basis before the ratio. The basis is not the unit of the result: it
  decides which quantities can be added.
  - **The item's own unit** (cases, packs, as the item is counted): for one item, with no total across items. The
    months are the same as on any other consistent basis.
  - **Quantity equivalent** in the base unit of the items' dimension: **kg** for items counted by weight, **L** for
    items counted by volume. Valid while every row and every total holds items of one dimension. It is the default.
  - **Value**: stock at standard cost against forecast at cost of goods sold. Valid for any group of items, and the
    only basis when items counted in kg and items counted in L are combined in one row or one total.
  - kg and L are never added, and the packs of different items are never added. A figure that would need either is
    given on an allowed basis, saying which and why, or not given.
- **Stockout month**: the analysis month plus the coverage rounded up to a whole month, since coverage counts from the
  month after the analysis month: a coverage of 0.5 or of 1.0 from June runs out in July. There is none when the stock
  outlasts the horizon or when there is no demand.

**Questions on stock-outs and dormant stock.**

- *"Which products will stock out within the next N months?"* keeps the products whose coverage is above 0 and at
  most *N*: they run out from the month after the analysis month up to month *N* included.
- *"Which products will stock out first?"* gives the 10 lowest coverages, lowest first, ties broken by the product
  codes.
- Products already out (coverage 0: no stock at the analysis month) and products with no demand are never in these
  lists: they are counted and named apart.
- *"Which products have more than N months of coverage?"* keeps the products whose coverage is above *N*. The stock
  they tie up is the sum of their stock on the basis asked; coverage itself is never summed or averaged.
- The grain follows the question. A question that asks for a list of products or items takes items as grain: with a country named, sku_code filtered on that country; worldwide or with no country, sku_code; for item and country pairs, sku_code and country_code. A question that asks for one figure for a scope (a country, a family, a region) takes that scope's grain and its filters, with no item rows and no grand total unless the question asks for them.
- The analysis month is the one the question gives, as for any coverage.

Provenance: decisions 1 to 3, 6 and 7 of session 8c-0; the contract's `measure_bases`, `basis_model`, `exhaustion_period` and `member_selection`.

## 2. Algorithm

Let *S* be the stock at *t*, *f(i)* the forecast for month *t+i*, and *C(n) = f(1) + … + f(n)*, with *C(0) = 0*.

| Case | Coverage |
|---|---|
| *S* is null or 0 | **0** |
| First *n* ≤ *H* such that *S ≤ C(n)* | **(n − 1) + (S − C(n−1)) / f(n)** |
| *S > C(H)* (stock outlasts the horizon) | **S / average monthly forecast**, where the average is taken over the months of the horizon *t+1 … t+H* with non-zero forecast |
| No forecast at all | **null** (no demand, so coverage is undefined) |

Provenance: the beyond-horizon rule is the contract's `beyond_horizon`.

Properties:
- The formula is the same on every basis and its result is in months. Scaling *S* and every *f(i)* by the same factor
  leaves it unchanged, which is why one item gives the same months in its own unit and in kg or L equivalent.
- A zero-forecast month **before** depletion counts as a fully covered month.
- *f(n) > 0* is guaranteed in the selected branch, so there is no division by zero.
- **Aggregate first, then compute.** *S* and *f* are summed to the requested grain *before* the algorithm runs. The coverage of a product family is **never** the sum, the average or the weighted average of the coverage of its SKUs.

### Worked example (synthetic)

*S* = 1,000. Forecasts from *t+1*: 120, 90, 150, 110, 130, 100, 140, 80, 160, …

The first 8 months accumulate to *C(8)* = 920 ≤ 1,000, and *C(9)* = 1,080 > 1,000. Coverage = 8 + (1,000 − 920) / 160 = **8.5 months**.

## 3. Attribute applicability (the semantic core)

Every attribute a user can slice or filter by has a declared **applicability** to the forecast measure. This declaration drives the SQL, and getting it wrong silently changes the answer.

| Class | Examples | Effect on stock | Effect on forecast |
|---|---|---|---|
| **Analysis time** | month | Selects the snapshot *t* | The filter is **not** applied: the forecast window is *t+1 … t+H* |
| **Conformed** | SKU, product family, brand, country, region | Grouped and filtered | Grouped and filtered the same way |
| **Stock-only** | batch status, best-before range, warehouse, business unit, ownership | Grouped and filtered | **Ignored**: the forecast stays at the parent conformed grain |
| **Stock-only by decision** | item type, when bulk items carry stock but no forecast | Grouped and filtered | Ignored |

Consequence: *"coverage of released batches in France"* means released stock in France divided by **total** French forecast. That is the intended business meaning, and no generic aggregation rule would produce it.

A new or derived attribute **must** declare its class before it can be used with coverage. In the legacy implementation, forgetting that declaration was the most frequent source of wrong numbers.

## 4. Edge cases and known traps

| # | Trap | Wrong behaviour | Correct behaviour |
|---|---|---|---|
| T1 | Ratio re-aggregation | Sum or average of child coverages | Recompute from aggregated *S* and *f* at each grain |
| T2 | Sparse forecast months | A row-based window ("next *n* rows") skips missing months, and totals disagree with drill-downs | **Densify** the calendar: a missing month is 0 |
| T3 | Stock-only filter pushed to forecast | The filter removes forecast rows, so coverage goes to 0 or null | The forecast ignores stock-only attributes |
| T4 | Time filter pushed to forecast | "Coverage for March" kills the future forecast rows | The forecast window is relative to *t*, not filtered by it |
| T5 | Heterogeneous units | Packs of different sizes summed, or kg and L summed | The item's own unit for one item only; quantity equivalent within one dimension; value across dimensions; refuse any other sum |
| T6 | Missing analysis month | Coverage "over the year" (meaningless) | An explicit as-of month is required: ask or refuse |
| T7 | Master-data fan-out | Item with two statuses counted twice | Enforce one-to-many on the item dimension |
| T8 | Forecast but no stock | Member disappears | Coverage = 0, row kept (contract: outcome `SNAPSHOT_NULL_OR_ZERO`, flag `NO_STOCK`) |

## 5. Reference SQL (Snowflake)

This is the parameterised template the custom tool binds at query time. `{conformed_grain}`, `{stock_only_grain}` and the filters are injected from the attribute-applicability declarations. `{full_grain}` is the conformed grain followed by the stock-only grain; `{full_join}` and `{conformed_join}` equate the member spine with the stock and forecast CTEs on those columns.

```sql
-- :as_of_month = first day of the analysis month; horizon H = 24
WITH months AS (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS k
    FROM TABLE(GENERATOR(ROWCOUNT => 24))
),
stock AS (                                   -- stock: all filters apply
    SELECT {conformed_grain}, {stock_only_grain}, SUM(s.stock_qty_eq) AS stock_qty
    FROM fct_stock_snapshot s
    JOIN dim_item i USING (item_id)
    JOIN dim_geo  g USING (country_id)
    WHERE s.snapshot_month = :as_of_month
      AND {conformed_filter} AND {stock_only_filter}
    GROUP BY ALL
),
fc AS (                                      -- forecast: conformed filters only (T3, T4)
    SELECT {conformed_grain},
           DATEDIFF(month, :as_of_month, f.forecast_month) AS k,
           SUM(f.forecast_qty_eq) AS fc_qty
    FROM fct_forecast f
    JOIN dim_item i USING (item_id)
    JOIN dim_geo  g USING (country_id)
    WHERE f.forecast_month >  :as_of_month
      AND f.forecast_month <= DATEADD(month, 24, :as_of_month)
      AND {conformed_filter}
    GROUP BY ALL
),
members AS (                                 -- member spine (T8): a member with forecast but no stock keeps its row
    SELECT {full_grain} FROM stock
    UNION                                     -- forecast members: only when {stock_only_grain} is empty
    SELECT {conformed_grain} FROM fc
),
dense AS (                                   -- dense calendar (T2)
    SELECT mb.*, m.k,
           COALESCE(s.stock_qty, 0) AS stock_qty,
           COALESCE(f.fc_qty, 0)    AS fc_qty
    FROM members mb
    CROSS JOIN months m
    LEFT JOIN stock s ON {full_join}
    LEFT JOIN fc f    ON f.k = m.k AND {conformed_join}
),
cum AS (
    SELECT *, SUM(fc_qty) OVER (PARTITION BY {full_grain} ORDER BY k
                                ROWS UNBOUNDED PRECEDING) AS cum_fc
    FROM dense
)
SELECT {full_grain},
       CASE
         WHEN ANY_VALUE(stock_qty) IS NULL OR ANY_VALUE(stock_qty) = 0 THEN 0
         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN
              SUM(CASE WHEN cum_fc - fc_qty >= stock_qty THEN 0     -- after depletion
                       WHEN cum_fc <= stock_qty          THEN 1     -- fully covered month
                       ELSE (stock_qty - (cum_fc - fc_qty)) / fc_qty -- depletion month
                  END)
         ELSE ANY_VALUE(stock_qty) / AVG(NULLIF(fc_qty, 0))        -- beyond horizon (average bounded to H)
       END AS coverage_months
FROM cum
GROUP BY {full_grain};
```

The set-based formula has been checked against a replica of the legacy cascade on 7 cases (`check_coverage_formula.py`): the worked example, an exact-depletion boundary, a zero month before depletion, zero stock, beyond-horizon stock, no demand, and forecast but no stock (T8). All 7 match. The same check asserts that a stock-driven member list, without the spine, loses the T8 member.

## 6. How the legacy BI platform did it

The legacy platform had no native function for this indicator, so each basis needed dozens of generated metrics:
- 24 windowed cumulative sums (`next 1..k rows`);
- 24 candidate coverages;
- a 25-branch `CASE`;
- the beyond-horizon average and its helpers.

The attribute-applicability rules were encoded **per metric** as level and filter overrides, which is why every new attribute risked breaking the calculation.

The thesis of this repo: declare applicability **once per attribute** and additivity **once per measure**, then generate the rest.

## 7. Closing stock over a period

Stock on hand is a level. Over a period (a quarter, a year, a range of months) it is read as **closing stock**:

- The closing stock of a period is the snapshot of the period's **last month**.
- A member (a SKU x country, a family x country...) that has a snapshot in some month of the period and **none in its
  last month closes at 0**, and keeps its row. It is not carried at its last known value.
- Closing stock is **never** the sum of the months of the period, their average, or the last non-empty month carried
  forward.
- Across members (SKUs, countries, batches, warehouses) closing stock adds up: a family's closing stock is the sum of
  its members' snapshots of the last month only.
- It counts every item type: the default scope (STANDARD items only) belongs to coverage, not to closing stock.

Provenance: the contract encodes this as the period aggregation `CLOSING_STOCK` of the snapshot measure (method `LAST_PERIOD`, missing value `0`, forbidden methods `SUM`, `AVERAGE`, `LAST_NON_EMPTY`).
Provenance: the traps `CS_LAST_MONTH_GAP`, `CS_MIDDLE_MONTH_GAP` and `CS_FAMILY` of `data/traps.yaml` test it.

Synthetic example: a SKU holds 400 in April, 350 in May and nothing in June. Its closing stock for the second quarter
is **0**, not 750 (sum), 250 (average) or 350 (May carried into June).

## 8. Default scope and analysis month

Three rules apply to every coverage question.

**BULK stock is excluded by default.** BULK items (repacked in store) carry stock but are never forecast. Counting
their stock against the forecast of the STANDARD items of the same family inflates its coverage. Coverage therefore
counts STANDARD stock only, unless the question filters the item type explicitly (for example "including bulk"), in
which case the filter applies as asked. The answer says how much BULK stock was left out. Grouping by item type
without such a filter keeps the default. This applies to coverage only: closing stock counts every item type
(section 7).

Provenance: decision 5 of session 4.

**Coverage is measured at one analysis month.** It is a point-in-time measure: the stock of one month against the
forecast that follows it. A question that gives no month, or gives a period (a year, a quarter, a range of months),
has no single analysis month: ask which month is meant, and say which months are available, rather than picking
one. Several months may be asked together, as a series with one value per month and no total across months.
Coverage is never summed or averaged over several months.

Provenance: decisions 4 and 8 of session 4.

**Basis.** Coverage is always in months. Stock and forecast are measured on one basis before the ratio: the item's own
unit for a single item; kg or L equivalent for items of the same dimension, unless the question asks for value (EUR);
value only when items of different dimensions are combined. Closing stock and forecast follow the same basis rule.

Provenance: decisions 1 to 4 of session 8c-0; the contract's `measure_bases` and `basis_model` (refusal `BASIS_NOT_COMPARABLE`).

Synthetic example: a family holds 300 of STANDARD stock and 200 of BULK stock, against a STANDARD forecast of 100 a
month. Its coverage is 3.0 months, with 200 of BULK stock reported as excluded; filtered explicitly on both item
types it would read 5.0. Asked "what is its coverage over 2026?", the answer is a question: which month of 2026?
