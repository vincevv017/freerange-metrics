# Phase 1 notes: decisions the contract forced

> Session 4, 2026-10-03. This file lists every choice that writing `contract/` forced and that the plan's Decisions tab
> does not already record. Each carries one tag: **[documented]** (DEFINITION.md, the plan, or Snowflake docs),
> **[measured]** (run here, evidence in the repository), **[inferred]** (reasoned, not run). The choices still open
> are also listed in the contract's `open_decisions`. The owner decides; the contract applies the current choice
> until then.

## Vocabulary and structure

| # | Choice | Why | Tag |
|---|---|---|---|
| 1 | The metamodel names the class **SNAPSHOT_ONLY**, with `STOCK_ONLY` as its alias, not STOCK_ONLY | The metamodel must name nothing stock-specific. The depletion pattern is generic: a snapshot drained by a flow. The parity test maps schema v0's `STOCK_ONLY` onto it | inferred |
| 2 | Applicability is declared twice: a class per attribute, and an effect per measure (GROUP_AND_FILTER, IGNORED, REFUSED) | The brief asks for "a class per measure"; DEFINITION.md §3 reads as an effect per measure. A test enforces that the two agree | inferred |
| 3 | The analysis month is **not** an attribute. The depletion pattern's anchor (`anchor_parameter`, `time_filter_on_flow: SELECTS_ANCHOR_ONLY`) carries it | DEFINITION.md §3 gives time its own class whose effect on the forecast is a window, not a filter | documented |
| 4 | `DIM_ITEM` declares grain `item_id`, although `schema_v0.GRAINS` has none | The grain is what the contract promises. The v0 data breaks it on purpose (T7), which `QE_ITEM_GRAIN` detects | inferred |
| 5 | Each failure mode (trap) is a contract element, and rules point to the traps they prevent through `prevents` | This makes traceability a reference check rather than prose. A trap that nothing prevents fails the tests | inferred |
| 6 | A `BULK_SCOPE` failure mode is added, sourced from findings §8 | Decision 5 exists because of it. Without it, the default scope prevents nothing that is traceable | inferred |
| 7 | Codes (refusals, flags, enum values) are UPPER_CASE, so linkml-lint gets a config that accepts it | The codes travel verbatim to the procedure's JSON and to the tool description | inferred |

## The algorithm

| # | Choice | Why | Tag |
|---|---|---|---|
| 8 | Outcomes are evaluated in order: zero stock, then depleted within H, then no flow, then beyond H. Zero stock with no forecast therefore returns **0 with NO_STOCK**, not null with NO_DEMAND | This is the order of the C0 procedure and of `coverage_ref.py`. DEFINITION.md §2 lists both cases without saying which wins. With the spine, the case only arises for a stock row of quantity 0 | measured (C0 SQL), documented (ambiguity) |
| 9 | A **NO_STOCK** flag is part of the contract | Decision 2 gives the value (0) but no flag. C0 and `coverage_ref.py` already emit NO_STOCK | measured |
| 10 | The VALUE variant is stock at standard cost against forecast at cost of goods sold | DEFINITION.md §1. The C0 tool description says "EUR at standard cost" only. The generated description will follow the contract | documented |

## Decisions 3, 4, 5, 6, 8, and the totals parameter

| # | Choice | Why | Tag |
|---|---|---|---|
| 11 | **Totals** become a parameter `totals`: a JSON array of attribute arrays, each a subset of `grain`; `[]` means none and `[[]]` means a grand total. Each total is recomputed. Refusals: `TOTALS_MALFORMED`, `TOTALS_NOT_SUBSET` | Plan §4 names a "totals level" input; the owner confirmed it as a contract rule and parameter in session 4. Its shape is new | documented (input), inferred (shape) |
| 12 | `as_of_month` becomes **`as_of_months`**, a JSON array of `YYYY-MM-01` or `LATEST`, capped at **24** months (`AS_OF_TOO_MANY`). One invalid month refuses the whole call | Decision 4 allows series; decision 7 forces a JSON string. Neither sets a cap or says what happens on a partly invalid list (OD_AS_OF_CAP) | inferred |
| 13 | A valid month needs a snapshot **and** a loaded horizon. `LATEST` resolves to the most recent such month. On v0, all 36 snapshot months (2023-07 to 2026-06) are valid: the calendar reaches 2029-06 | Without the horizon condition, LATEST could name a month that `HORIZON_NOT_LOADED` then refuses | measured (data), inferred (rule) |
| 14 | **Decision 8, exposure.** The tool description carries `LATEST` and the first and last valid month, written at compile time. Every procedure answer and refusal carries the full list, read at call time. The registry holds it too | A full list compiled into the description goes stale at the next load. In C0 on T6 the agent proposed October 2026, a month with no snapshot | measured (C0), inferred (split) |
| 15 | **Decision 5, detail.** Only a **filter** on `item_type` lifts the default scope; grouping by `item_type` without a filter keeps it (OD_SCOPE_ON_GROUPING). The scope applies to the stock only. `DEFAULT_SCOPE_EXCLUDED` is raised only when the excluded stock is non-zero | The decision names an explicit filter. A warning on every answer would be noise | inferred |
| 16 | **Decision 5 versus C0.** The C0 procedure applies no default scope. Under the contract, family `HOT_GROUND` goes from 17.4 to 8.7 months by default | Findings §8 | measured |
| 17 | **Decision 6 versus T7.** `lifecycle_status` is CONFORMED, and T7 duplicates exactly that column. `QE_ITEM_GRAIN` is set to **REFUSE_IF_USED**: a query that uses an item attribute whose values disagree for some item is refused (`MASTER_DATA_FANOUT`); otherwise the answer carries `MASTER_DATA_DUPLICATES`, but only when a duplicated item is in scope (OD_T7_RESOLUTION) | A global refusal would refuse every query on v0, T7 itself included (expected 2.25). C0 deduplicated on a fixed column set that excluded `lifecycle_status` | measured (C0 check, v0 data), inferred (rule) |
| 18 | Consequence of 17: on v0, any query that groups or filters by `lifecycle_status` is refused while the T7 duplicate exists | Follows from 17. Phase 2 must choose whether the T7 hero keeps that shape | inferred |

## Parameters and refusals

| # | Choice | Why | Tag |
|---|---|---|---|
| 19 | `unit_variant` stays **required**, and QTY_EQ is marked `is_default` only as guidance for the description ("QTY_EQ unless value is asked") | This is the C0 shape, which worked through the agent | measured |
| 20 | `filters` stays required, with `"{}"` for no filter | Same C0 shape | measured |
| 21 | Each refusal carries an evidence tag. **MEASURED**: the 8 codes exercised directly in C0. **IMPLEMENTED**: the 7 codes present in C0 but never triggered. **DECIDED**: new codes (`AS_OF_TOO_MANY`, `ATTRIBUTE_NOT_APPLICABLE`, `TOTALS_*`). A test pins the C0 code set | Phase 4 must not report an IMPLEMENTED code as measured | measured |
| 22 | `ATTRIBUTE_UNCLASSIFIED` is kept, although the contract cannot produce it (the applicability class is required) | It guards a registry row added outside the compiler | inferred |
| 23 | `ATTRIBUTE_NOT_APPLICABLE` exists with no attribute using it in 0.1.0 | The metamodel offers the class; the procedure needs its refusal | inferred |
| 24 | Each refusal has a `check_order`: every check on the analysis month first (snapshot and horizon included), then unit, grain, filters and totals, then data quality | C0 checked month form, unit, grain and filters, and only then snapshot existence, horizon and fan-out together with the data. The contract moves the month-availability checks up with the month. A fixed order makes the refusal deterministic when several inputs are wrong | measured (C0 order), inferred (change) |

## Quality expectations

| # | Choice | Why | Tag |
|---|---|---|---|
| 25 | `QE_FORECAST_DENSE` is a **WARN**: the engine densifies (correct for T2), and `FORECAST_GAPS_FILLED` says data was missing. On v0, the T2 and BEYOND_H heroes have absent rows, so their answers will carry the warning | Plan §5: quality reaches the answer. The Phase 4 expected answers must include it | inferred |
| 26 | Referential failures **WARN**, they do not refuse | An orphan row drops silently from an inner join and lowers coverage. A warning is enough to show it, and refusing every query would be too strong | inferred |
| 27 | DMF names (`SNOWFLAKE.CORE.DUPLICATE_COUNT`, `SNOWFLAKE.CORE.NULL_COUNT`) are written from the documentation as recalled, not checked on this account. Multi-column and cross-table checks are `CUSTOM` | To verify in Phase 2 or 3, before generating | inferred |
| 28 | Stock freshness age, and the stockout and expiry thresholds, are **TBD**. The expiry alert compares coverage at a grain that includes `expiry_bucket` against months to expiry, a provisional formula: buckets are coarse | Article 2 inputs; the owner sets the values | inferred |

## Tooling

| # | Finding | Tag |
|---|---|---|
| 29 | `linkml-validate` checks shapes and enum values but **not references**: an invalid `prevents: [T99]` passes. `tests/test_contract.py` resolves every reference | measured |
| 30 | `linkml-validate` rejects an unquoted YAML date (`datetime.date is not of type 'string'`), so dates are quoted | measured |
| 31 | `metamodel.yaml` validates against the LinkML meta schema (`-C schema_definition`) and passes linkml-lint with no problem; a broken copy is rejected | measured |
| 32 | A minimal evaluator that reads only the contract's parameters returns the traps.yaml values for T2, T4, T8, NO_DEMAND and BEYOND_H, and the DEFINITION.md worked example (8.5). Changing one parameter reproduces the documented wrong values: average over the full range gives 11.97 on BEYOND_H; a window that starts at the analysis month gives 7.71 on T4 | measured |
| 33 | Three deliberate mutations are caught by the tests: a trap left unprevented, a renamed measure column, a snapshot-only attribute reclassified as conformed | measured |

## Decision 5 against traps.yaml (checked, nothing changed)

Each `traps.yaml` query was recomputed on the v0 dataset with `data/coverage_ref.py`, once on all item types and once
restricted to `item_type = STANDARD`. **No expected value depends on BULK stock.** All ten heroes are STANDARD, and
families `PANTRY_FLOUR` (T1) and `PANTRY_OIL` (T7) have no BULK SKU. **[measured]**

| Trap | Query | Expected | All item types | STANDARD only | Explicit item_type filter needed in the reference question? |
|---|---|---|---|---|---|
| T1 | PANTRY_FLOUR x FR | 2.8 | 2.8 | 2.8 | No: value unchanged, no warning (no BULK stock in scope) |
| T2 | SKU-H03 x DE | 7.0 | 7.0 | 7.0 | No |
| T3 | SKU-H04 x IT, RELEASED | 6.0 | 6.0 | 6.0 | No: HOT_TEA has a BULK SKU (SKU-0012), but the query is at SKU level |
| T4 | SKU-H05 x ES | 8.5 | 8.5 | 8.5 | No |
| T7 | PANTRY_OIL x SE | 2.25 | 2.25 | 2.25 | No |
| T8 | SKU-H08 x NL | 0.0 (NO_STOCK) | 0.0 | 0.0 | No |
| NO_DEMAND | SKU-H09 x BE | null | null | null | No |
| BEYOND_H | SKU-H10 x PL | 50.0 | 50.0 | 50.0 | No |

The `related` and `children` values (T1 children 12.0 and 0.5, T3 hold 4.0 and all statuses 10.0) are at SKU level on
STANDARD heroes, so they are unchanged too. **[measured]** The only v0 case decision 5 moves is outside `traps.yaml`:
HOT_GROUND, 17.4 to 8.7. **[measured]**, findings §8.

## Carried to Phase 2

- Add **T5** (raw units) and **T6** (missing analysis month) to `traps.yaml` as refusal traps, with the expected
  refusal code instead of a value. Today the contract traces them from DEFINITION.md §4. (Owner request, session 4.)
- Add a **BULK_SCOPE** hero: a family with BULK stock. Expected: the STANDARD value by default with
  `DEFAULT_SCOPE_EXCLUDED`, and the inflated value with an explicit `item_type` filter.
- Decide whether the T7 hero keeps two `lifecycle_status` values (see 17 and 18), and add a question that uses
  `lifecycle_status` with the refusal it expects.
- Generate the schema module from the contract to replace `data/schema_v0.py`, and keep the parity test green
  against it.
