---
name: linkml-coverage
description: "Computes stock coverage in months (months of cover) with the script coverage.py, from the stock at one analysis month and the monthly demand forecast of the 24 following months. Use for every stock coverage question. Do not use for closing stock, stock levels or demand forecast questions: answer those with the semantic view tool."
---

# linkml-coverage

Stock coverage: if nothing is replenished, how many months the stock on hand at the analysis month lasts against the
demand forecast of the 24 following months. `coverage.py` computes it; you never compute, add, average or adjust a
coverage yourself.

## Fast path

1. Decide before any call: the analysis month (one month, as YYYY-MM-01; if the question gives none or a period, ask
   which month and stop), the basis (coverage is always in months; stock and forecast in kg or L equivalent for
   items of one dimension, in value (EUR) when the user asks for value or when kg and L items are combined), and the
   filters and level of the question.
2. Get the two inputs at that level, once:
   - S, the stock at the analysis month;
   - the forecast of each month from the month after the analysis month to 24 months after it, as (month, quantity)
     pairs.
3. Run `coverage.py` once, then answer with its `coverage_months`, the analysis month, the basis and the filters. Do not
   reopen this skill or list its files.
4. `coverage.py` is in this skill's folder, even if a listing shows it at 0 B: run it, and never do the computation
   yourself.

## Step 2, by toolset

- **With bash (coding toolset)**: do not fetch the numbers yourself. Write the two queries against the RAW tables below
  and pass them to the script, which runs them with its own connection:
  `python3 coverage.py --as-of <YYYY-MM-01> --stock-sql "<one row, one number>" --forecast-sql "<rows: month, quantity>"`
- **With code execution only**: fetch the two inputs with the semantic view tool, then pass the numbers:
  `python3 coverage.py --as-of <YYYY-MM-01> --stock <S> --forecast '[["<YYYY-MM-01>", <quantity>], ...]'`

For a breakdown (by country, by SKU), run the script once per row; for a total, get the inputs at the total's level
and run it once more. Never add or average the rows' coverages.

## RAW tables (LINKML_METRICS.RAW)

| Table | Columns |
|---|---|
| FCT_STOCK_SNAPSHOT | snapshot_month, batch_id, warehouse_id, item_id, country_id, expiry_bucket, stock_qty_raw, stock_qty_eq, stock_value_eur |
| FCT_FORECAST | forecast_month, item_id, country_id, forecast_qty_raw, forecast_qty_eq, forecast_value_eur |
| DIM_ITEM | item_id, sku_code, sku_name, family_code, family_name, range_code, range_name, item_type, lifecycle_status, raw_unit, qty_eq_factor, std_cost_eur, cogs_eur |
| DIM_GEO | country_id, country_code, country_name, region_code, region_name |
| DIM_BATCH | batch_id, batch_code, item_id, batch_status, production_month, expiry_date |
| DIM_WAREHOUSE | warehouse_id, warehouse_code, warehouse_type, country_id |

## Output of the script

One JSON object: `analysis_month`, `horizon` (first and last forecast month), `stock`, `forecast_by_month` (24
values, a month with no forecast counted as 0), `months_without_forecast_counted_as_0`, `coverage_months` (null when
there is no forecast at all), `case`, and the queries with their ids when the script ran them.
