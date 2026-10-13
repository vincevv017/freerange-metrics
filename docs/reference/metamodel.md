<!-- GENERATED from contract/metamodel.yaml by compiler/gen_reference.py (LinkML gen-markdown-datadict, post-processed for GitHub). Do not edit: change the metamodel and run `python compiler/gen_reference.py`. tests/test_reference.py regenerates this file and fails on any difference. -->
# Metamodel reference: metric_semantics

The vocabulary of a metric contract: every class, its attributes (cardinality, range, description), every top-level slot and every enum with its values. `contract/stock_coverage.yaml` is an instance of it. The traps the contract guards against are in [failure_modes.md](failure_modes.md).

An attribute marked **Fixed** is not read by the compiler: the generated objects are written for one value, and a contract holding another one is refused by the generators that write its behaviour (`compiler/supported.py`). One marked **Documentation only** carries no behaviour.


**version:** 0.4.2


A generic vocabulary for declaring what a metric means and when its number can be trusted: measure types and additivity per dimension class, attribute applicability per measure, the bases on which measures are compared (an item's own unit, a base-unit equivalent per physical dimension, a value) and where each one is valid, a depletion pattern (a snapshot drained by a forward flow) with its member selection, totals and member-set rules, the parameter surface of the tool that computes the metric and its refusal codes, data-quality expectations and calculation invariants. Nothing here is specific to one metric: a contract instance (for example stock_coverage.yaml) fills it in, and the Phase 3 compiler generates the runtime objects from that instance.


## Classes


### Additivity

How a measure aggregates along one dimension class.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[aggregation](#slot-additivity__aggregation)** | <sub>1..1</sub> | [AggregationRule](#aggregationrule) | SUM, SELECT_PERIOD, SUM_OVER_WINDOW or NONE. The tests check it against measure_type (a snapshot selects its period on TIME, a flow sums over the window); the generated SQL implements it. |
| **[dimension_class](#slot-additivity__dimension_class)** | <sub>1..1</sub> | [DimensionClass](#dimensionclass) | The dimension class this rule covers. |
| **[note](#slot-additivity__note)** | <sub>0..1</sub> | string | A free note that explains the rule. |

#### Referenced by:

 *  **[Measure](#measure)** : measure__additivity  <sub>1..\*</sub> 


### AlertThreshold

A threshold that turns a metric value into an alert (consumed by the restitution layer).


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[compared_to](#slot-alertthreshold__compared_to)** | <sub>1..1</sub> | string | The quantity compared, as a formula over metric outputs and attributes. |
| **[comparison](#slot-alertthreshold__comparison)** | <sub>1..1</sub> | [Comparison](#comparison) | LT, LE, GT or GE. |
| **[metric](#slot-alertthreshold__metric)** | <sub>1..1</sub> | [DepletionMetric](#depletionmetric) | The metric compared. |
| **[raises_flag](#slot-alertthreshold__raises_flag)** | <sub>0..1</sub> | string | The flag a restitution layer would raise (STOCKOUT_RISK, EXPIRY_RISK). Declared, not read by the compiler; the values are TBD. **Documentation only.** |
| **[unit](#slot-alertthreshold__unit)** | <sub>1..1</sub> | string | The unit of the value (months). |
| **[value](#slot-alertthreshold__value)** | <sub>1..1</sub> | string | A number, or TBD while the owner has not set it. |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : alert_thresholds  <sub>0..\*</sub> 


### AnalysisPeriods

The anchor periods a caller may ask for, and where the list is exposed so that an agent proposes only periods that exist.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[exposed_in](#slot-analysisperiods__exposed_in)** | <sub>1..\*</sub> | [ExposureTarget](#exposuretarget) | Where the valid periods are shown. Declared, not read by the compiler: the agent's specification carries the first, last and LATEST months at generation, and every procedure answer carries them at call time. **Documentation only.** |
| **[latest_token](#slot-analysisperiods__latest_token)** | <sub>1..1</sub> | string | A literal the caller may pass for the most recent valid period. |
| **[max_periods](#slot-analysisperiods__max_periods)** | <sub>0..1</sub> | integer | The most analysis months per call (24); more is refused with AS_OF_TOO_MANY. |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[series_allowed](#slot-analysisperiods__series_allowed)** | <sub>1..1</sub> | boolean | True: several analysis months may be asked in one call; they give a series. Declared, not read by the compiler: the procedure accepts up to max_periods months. **Fixed: only true is supported by this compiler.** |
| **[source_column](#slot-analysisperiods__source_column)** | <sub>1..1</sub> | string | Its period column. |
| **[source_table](#slot-analysisperiods__source_table)** | <sub>1..1</sub> | [Table](#table) | The table whose period column lists the periods that exist (the stock snapshot). |
| **[validity](#slot-analysisperiods__validity)** | <sub>1..1</sub> | string | The condition a period must meet to be offered and accepted. The procedure and the agent's specification apply it: a snapshot exists for the month, and the calendar and the flow reach the month plus H. |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : analysis_periods  <sub>0..\*</sub> 


### Attribute

Something a user can group or filter by. It must declare its applicability to every measure of each metric it is used with; an attribute without a declaration cannot be used with the metric.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[applicability](#slot-attribute__applicability)** | <sub>1..\*</sub> | [MeasureApplicability](#measureapplicability) | Effect on each measure. Must agree with applicability_class: CONFORMED = every measure GROUP_AND_FILTER; SNAPSHOT_ONLY = snapshot measures GROUP_AND_FILTER, flow measures IGNORED; NOT_APPLICABLE = REFUSED. |
| **[applicability_class](#slot-attribute__applicability_class)** | <sub>1..1</sub> | [ApplicabilityClass](#applicabilityclass) | How the procedure routes the attribute. CONFORMED groups and filters stock and forecast; SNAPSHOT_ONLY restricts the stock and leaves the forecast at the conformed grain; NOT_APPLICABLE is refused (ATTRIBUTE_NOT_APPLICABLE). |
| **[column](#slot-attribute__column)** | <sub>1..1</sub> | string | The physical column grouped or filtered. |
| **[dimension_class](#slot-attribute__dimension_class)** | <sub>1..1</sub> | [DimensionClass](#dimensionclass) | The dimension class the attribute belongs to. Read by the tests, not by the compiler. |
| **[known_values](#slot-attribute__known_values)** | <sub>0..\*</sub> | string | Values listed in the agent's tool description and the semantic view; a VALUE_RANGE quality expectation on the column takes them as its accepted values. Empty means an open set. |
| **[label_column](#slot-attribute__label_column)** | <sub>0..1</sub> | string | Optional human-readable column shown next to the code. The tool description lists code = name pairs for an attribute with at most 30 codes, read from the dataset. |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[synonyms](#slot-synonyms)** | <sub>0..\*</sub> | string | Other words for the element. A metric's go into the tool description and B2's view; a basis's are accepted by the procedure as the basis parameter. |
| **[table](#slot-attribute__table)** | <sub>1..1</sub> | [Table](#table) | The table that holds the attribute's column; the procedure joins it from each fact through the declared relationships. |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : attributes  <sub>1..\*</sub> 
 *  **[MetricContract](#metriccontract)** : attributes  <sub>0..\*</sub> 
 *  **[DefaultScope](#defaultscope)** : defaultScope__attribute  <sub>1..1</sub> 


### BasisModel

Where each item's dimension and units are read, the default basis and how the validity of a basis is judged. One per contract.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[base_unit_column](#slot-basismodel__base_unit_column)** | <sub>1..1</sub> | string | The column that holds the base unit of the item's dimension (kg, L): the unit of a row on the equivalent basis. |
| **[default_basis](#slot-basismodel__default_basis)** | <sub>1..1</sub> | [MeasureBasis](#measurebasis) | The basis used when the caller names none. Refused like any other basis where it is not valid. |
| **[dimension_column](#slot-basismodel__dimension_column)** | <sub>1..1</sub> | string | The column that holds each item's dimension (MASS, VOLUME). |
| **[dimensions](#slot-basismodel__dimensions)** | <sub>1..\*</sub> | [ItemDimension](#itemdimension) | The physical dimensions declared, each with its base unit. A data metric function (QE_ITEM_DIMENSION) checks every item against this list. |
| **[equivalence_factor_column](#slot-basismodel__equivalence_factor_column)** | <sub>1..1</sub> | string | Base units per native unit (kg or L per pack). The facts carry the equivalent quantities in their own columns; the compiler lists this column in generated/schema.py and does not compute with it. |
| **[item_key](#slot-basismodel__item_key)** | <sub>1..1</sub> | string | The key column of the item table. |
| **[item_table](#slot-basismodel__item_table)** | <sub>1..1</sub> | [Table](#table) | The table that holds each item's dimension and units (DIM_ITEM). The procedure reads it to count the items and dimensions behind each row. |
| **[native_unit_column](#slot-basismodel__native_unit_column)** | <sub>1..1</sub> | string | The item's own unit: how the item is counted (a pack size). |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[refusal](#slot-basismodel__refusal)** | <sub>1..1</sub> | [RefusalCode](#refusalcode) | The refusal raised when the basis asked is not comparable (BASIS_NOT_COMPARABLE); the agent's tool description names it. |
| **[result_unit](#slot-basismodel__result_unit)** | <sub>1..1</sub> | string | The unit of the metric's result, the same on every basis. |
| **[validity_scope](#slot-basismodel__validity_scope)** | <sub>1..1</sub> | [BasisValidityScope](#basisvalidityscope) | Where the validity of a basis is judged. Declared, not read by the compiler: the procedure always judges the rows and totals the call returns (RETURNED_ROWS). **Fixed: only RETURNED_ROWS is supported by this compiler.** |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : basis_model  <sub>1..1</sub> 
 *  **[MetricContract](#metriccontract)** : basis_model  <sub>0..1</sub> 


### BeyondHorizonRule

How a level that outlasts the horizon is valued, and the flag that marks it.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[average_window](#slot-beyondhorizonrule__average_window)** | <sub>1..1</sub> | [AverageWindow](#averagewindow) | The flow periods the mean covers: HORIZON, the H periods of the window. Declared, not read by the compiler: the procedure's SQL implements it. **Fixed: only HORIZON is supported by this compiler.** |
| **[exclude_zero_periods](#slot-beyondhorizonrule__exclude_zero_periods)** | <sub>1..1</sub> | boolean | True: periods with no flow are left out of the mean, so a sparse forecast does not stretch the result. Declared, not read by the compiler: the procedure's SQL implements it. **Fixed: only true is supported by this compiler.** |
| **[flag](#slot-beyondhorizonrule__flag)** | <sub>1..1</sub> | [Flag](#flag) | The flag set on an extrapolated row (BEYOND_HORIZON); the procedure reads it. |
| **[method](#slot-beyondhorizonrule__method)** | <sub>1..1</sub> | [BeyondHorizonMethod](#beyondhorizonmethod) | SNAPSHOT_OVER_MEAN_FLOW: the level divided by the mean flow per period. Declared, not read by the compiler: the procedure's SQL implements this method only. **Fixed: only SNAPSHOT_OVER_MEAN_FLOW is supported by this compiler.** |
| **[prevents](#slot-beyondhorizonrule__prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this rule prevents. |

#### Referenced by:

 *  **[DepletionMetric](#depletionmetric)** : depletionMetric__beyond_horizon  <sub>1..1</sub> 


### CalculationInvariant

A property every correct result satisfies, turned into a property test on the procedure.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[statement](#slot-calculationinvariant__statement)** | <sub>1..1</sub> | string | The property, in words. Declared, not read by the compiler; tests/test_procedure.py checks several of them against the deployed procedure. **Documentation only.** |
| **[test_kind](#slot-calculationinvariant__test_kind)** | <sub>1..1</sub> | [TestKind](#testkind) | The shape of the test: PROPERTY, EXAMPLE or METAMORPHIC. |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : invariants  <sub>0..\*</sub> 


### Column

One physical column of a table: its name and its Snowflake type.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[name](#slot-column__name)** | <sub>1..1</sub> | string | Column name, in lower case here; Snowflake stores it in upper case. |
| **[description](#slot-column__description)** | <sub>0..1</sub> | string | Optional note on the column. |
| **[data_type](#slot-column__data_type)** | <sub>1..1</sub> | string | Physical type of the target platform (for example NUMBER(18,4)). |
| **[nullable](#slot-column__nullable)** | <sub>0..1</sub> | boolean | Whether the column may hold NULL. Declared, not read by the compiler: missing values are checked by COMPLETENESS quality expectations. **Documentation only.** |

#### Referenced by:

 *  **[Table](#table)** : table__columns  <sub>1..\*</sub> 


### ContractChange

One entry of the contract's change log.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[date](#slot-contractchange__date)** | <sub>1..1</sub> | date | The date the version was made (YYYY-MM-DD). |
| **[summary](#slot-contractchange__summary)** | <sub>1..1</sub> | string | What changed and why, and whether a rule changed or only its wording. |
| **[version](#slot-contractchange__version)** | <sub>1..1</sub> | string | The contract version this entry records, for example 0.5.1. |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : changes  <sub>0..\*</sub> 


### DefaultScope

A restriction applied when the caller does not ask otherwise. Lifted only by an explicit filter on the same attribute. The answer reports what the scope removed.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[applies_to_measures](#slot-defaultscope__applies_to_measures)** | <sub>1..\*</sub> | [Measure](#measure) | The measures whose rows the scope restricts, inside the metrics of applies_to_metrics only. |
| **[applies_to_metrics](#slot-defaultscope__applies_to_metrics)** | <sub>1..\*</sub> | [DepletionMetric](#depletionmetric) | The metrics whose computation applies the scope. Outside them (for example the snapshot measure's period aggregation, closing stock), the scope does not apply. |
| **[attribute](#slot-defaultscope__attribute)** | <sub>1..1</sub> | [Attribute](#attribute) | The attribute restricted by default (item_type). |
| **[included_values](#slot-defaultscope__included_values)** | <sub>1..\*</sub> | string | The values kept unless the caller filters the attribute (STANDARD). |
| **[lifted_by](#slot-defaultscope__lifted_by)** | <sub>1..1</sub> | [ScopeLift](#scopelift) | EXPLICIT_FILTER: a filter on the same attribute lifts the scope; grouping by it does not. Declared, not read by the compiler: the procedure implements it. **Fixed: only EXPLICIT_FILTER is supported by this compiler.** |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[warning](#slot-defaultscope__warning)** | <sub>1..1</sub> | [WarningCode](#warningcode) | The warning raised with the amount the scope removed, per analysis month and unit (DEFAULT_SCOPE_EXCLUDED). |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : default_scopes  <sub>0..\*</sub> 


### DepletionMetric

A snapshot drained by a forward flow: how many periods the level at the anchor period lasts against the flow of the following periods. Inputs are aggregated to the requested grain before the algorithm runs.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[name](#slot-name)** | <sub>0..1</sub> | string | A human-readable name. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[aggregate_before_compute](#slot-depletionmetric__aggregate_before_compute)** | <sub>1..1</sub> | boolean | True: stock and flow are summed to the requested grain before the algorithm runs, never computed per item and averaged (trap T1). Declared, not read by the compiler: the procedure implements it. **Fixed: only true is supported by this compiler.** |
| **[anchor_parameter](#slot-depletionmetric__anchor_parameter)** | <sub>1..1</sub> | [Parameter](#parameter) | The parameter that selects the analysis month (as_of_months). Read by the tests; the procedure's argument names are fixed in the compiler. **Fixed: only as_of_months is supported by this compiler.** |
| **[beyond_horizon](#slot-depletionmetric__beyond_horizon)** | <sub>1..1</sub> | [BeyondHorizonRule](#beyondhorizonrule) | The rule for a level that outlasts the horizon. |
| **[densify_missing_periods](#slot-depletionmetric__densify_missing_periods)** | <sub>1..1</sub> | boolean | True: a period with no flow row counts as zero, never as a skipped row (trap T2). Declared, not read by the compiler: the procedure crosses every member with every month of the window. **Fixed: only true is supported by this compiler.** |
| **[exhaustion_period](#slot-depletionmetric__exhaustion_period)** | <sub>0..1</sub> | [ExhaustionPeriodRule](#exhaustionperiodrule) | The period in which a member's snapshot runs out, carried by each result row. |
| **[flow_measure](#slot-depletionmetric__flow_measure)** | <sub>1..1</sub> | [Measure](#measure) | The amount that drains it (demand forecast), summed over the forward window. |
| **[horizon_periods](#slot-depletionmetric__horizon_periods)** | <sub>1..1</sub> | integer | Length H of the forward window, in periods (24): the flow of t+1 to t+24 is read. A month is a valid analysis month only when the calendar and the forecast reach it plus H. |
| **[interpolation](#slot-depletionmetric__interpolation)** | <sub>1..1</sub> | [Interpolation](#interpolation) | LINEAR: in the month the stock runs out, the fraction of that month's flow it covers is added. Declared, not read by the compiler: the procedure's SQL implements LINEAR. **Fixed: only LINEAR is supported by this compiler.** |
| **[member_selection](#slot-depletionmetric__member_selection)** | <sub>0..1</sub> | [MemberSelection](#memberselection) | How a caller keeps some members by their result (a window, the first n), and what comes back apart. |
| **[outcomes](#slot-depletionmetric__outcomes)** | <sub>1..\*</sub> | [DepletionOutcome](#depletionoutcome) | The outcomes, evaluated in order; the first matching condition decides the value and the flag. The procedure reads each outcome's flag; the value rules are written in its SQL in this order. **Fixed: only the four outcomes SNAPSHOT_NULL_OR_ZERO (0, member kept), DEPLETED_WITHIN_HORIZON (linear), NO_FLOW_IN_WINDOW (null, member kept), BEYOND_HORIZON (mean non-zero flow), in this order is supported by this compiler.** |
| **[output_unit](#slot-depletionmetric__output_unit)** | <sub>1..1</sub> | string | The unit of the result (months), the same on every basis. **Fixed: only months is supported by this compiler.** |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[reference_cases](#slot-depletionmetric__reference_cases)** | <sub>0..1</sub> | string | Path of the algorithm check that pins the formula on worked cases. |
| **[reference_sql](#slot-depletionmetric__reference_sql)** | <sub>0..1</sub> | string | Path of the reference SQL the generated procedure must match. |
| **[snapshot_measure](#slot-depletionmetric__snapshot_measure)** | <sub>1..1</sub> | [Measure](#measure) | The level that is drained (stock on hand), read at the analysis month. |
| **[synonyms](#slot-synonyms)** | <sub>0..\*</sub> | string | Other words for the element. A metric's go into the tool description and B2's view; a basis's are accepted by the procedure as the basis parameter. |
| **[time_filter_on_flow](#slot-depletionmetric__time_filter_on_flow)** | <sub>1..1</sub> | [TimeFilterRule](#timefilterrule) | SELECTS_ANCHOR_ONLY: the month asked selects the snapshot, and the flow window stays relative to it, never cut by the filter (trap T4). Declared, not read by the compiler: the procedure implements it. **Fixed: only SELECTS_ANCHOR_ONLY is supported by this compiler.** |
| **[time_grain](#slot-depletionmetric__time_grain)** | <sub>1..1</sub> | [TimeGrain](#timegrain) | The period of the anchor and of the window (MONTH). Declared, not read by the compiler: the generated SQL is monthly. **Fixed: only MONTH is supported by this compiler.** |
| **[window_start_offset](#slot-depletionmetric__window_start_offset)** | <sub>1..1</sub> | integer | First flow period counted, relative to the analysis month: 1 means the window starts the month after the analysis month, so the analysis month's own forecast never counts (trap T4). |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : metrics  <sub>1..\*</sub> 
 *  **[AlertThreshold](#alertthreshold)** : alertThreshold__metric  <sub>1..1</sub> 
 *  **[DefaultScope](#defaultscope)** : defaultScope__applies_to_metrics  <sub>1..\*</sub> 
 *  **[MetricContract](#metriccontract)** : metrics  <sub>0..\*</sub> 


### DepletionOutcome

One outcome of the depletion algorithm: a condition, the value returned and the flag set on the row.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[condition](#slot-depletionoutcome__condition)** | <sub>1..1</sub> | [DepletionCondition](#depletioncondition) | The condition tested. The procedure maps each condition to its flag. |
| **[flag](#slot-depletionoutcome__flag)** | <sub>0..1</sub> | [Flag](#flag) | The flag set on the row (NO_STOCK, NO_DEMAND); the procedure writes this code into the row's flag. |
| **[keeps_member](#slot-depletionoutcome__keeps_member)** | <sub>0..1</sub> | boolean | True when the member keeps its row although a measure is absent. |
| **[order](#slot-depletionoutcome__order)** | <sub>1..1</sub> | integer | Evaluation order, from 1; the first matching condition wins. Checked by the tests; the procedure's SQL evaluates the conditions in this order. |
| **[prevents](#slot-depletionoutcome__prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this outcome prevents. |
| **[result](#slot-depletionoutcome__result)** | <sub>1..1</sub> | string | The value returned, as a formula over the pattern's symbols. |

#### Referenced by:

 *  **[DepletionMetric](#depletionmetric)** : depletionMetric__outcomes  <sub>1..\*</sub> 


### DimensionClass

A class of dimension along which additivity is declared once (time, product, geography, location...). Attributes belong to one class; measures declare their additivity per class.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[is_time](#slot-dimensionclass__is_time)** | <sub>0..1</sub> | boolean | True for the class that carries calendar time. |

#### Referenced by:

 *  **[Additivity](#additivity)** : additivity__dimension_class  <sub>1..1</sub> 
 *  **[Attribute](#attribute)** : attribute__dimension_class  <sub>1..1</sub> 
 *  **[MetricContract](#metriccontract)** : dimension_classes  <sub>0..\*</sub> 


### ExhaustionPeriodRule

The period in which a member's level runs out, returned on every result row (stockout_month).


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[formula](#slot-exhaustionperiodrule__formula)** | <sub>1..1</sub> | string | The period, as a formula over the anchor and the result: t + ceil(coverage) months, so 0.5 and 1.0 from June both give July. The procedure's SQL implements it. **Documentation only.** |
| **[none_for_flags](#slot-exhaustionperiodrule__none_for_flags)** | <sub>0..\*</sub> | [Flag](#flag) | Flags for which no period is given (NO_DEMAND, BEYOND_HORIZON): the row's stockout_month is null. The procedure reads them. |

#### Referenced by:

 *  **[DepletionMetric](#depletionmetric)** : depletionMetric__exhaustion_period  <sub>0..1</sub> 


### FailureMode

A known way to get the metric wrong (a trap). Rules, refusals and expectations reference the failure modes they prevent; a failure mode nothing references is a gap.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[name](#slot-name)** | <sub>0..1</sub> | string | A human-readable name. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[correct_behaviour](#slot-failuremode__correct_behaviour)** | <sub>1..1</sub> | string | What a correct implementation does. |
| **[reference_question](#slot-failuremode__reference_question)** | <sub>0..1</sub> | string | A natural-language question that exercises the trap; compiler/gen_questions.py turns it into a campaign question. |
| **[source](#slot-failuremode__source)** | <sub>1..1</sub> | string | Where the trap is defined (file and section). |
| **[wrong_behaviour](#slot-failuremode__wrong_behaviour)** | <sub>1..1</sub> | string | What a wrong implementation does, in words; the trap in data/traps.yaml declares the value it returns. |

#### Referenced by:

 *  **[BeyondHorizonRule](#beyondhorizonrule)** : beyondHorizonRule__prevents  <sub>0..\*</sub> 
 *  **[DepletionOutcome](#depletionoutcome)** : depletionOutcome__prevents  <sub>0..\*</sub> 
 *  **[MetricContract](#metriccontract)** : failure_modes  <sub>0..\*</sub> 
 *  **[AnalysisPeriods](#analysisperiods)** : prevents  <sub>0..\*</sub> 
 *  **[Attribute](#attribute)** : prevents  <sub>0..\*</sub> 
 *  **[BasisModel](#basismodel)** : prevents  <sub>0..\*</sub> 
 *  **[CalculationInvariant](#calculationinvariant)** : prevents  <sub>0..\*</sub> 
 *  **[DefaultScope](#defaultscope)** : prevents  <sub>0..\*</sub> 
 *  **[DepletionMetric](#depletionmetric)** : prevents  <sub>0..\*</sub> 
 *  **[MeasureBasis](#measurebasis)** : prevents  <sub>0..\*</sub> 
 *  **[MemberSelection](#memberselection)** : prevents  <sub>0..\*</sub> 
 *  **[MemberSetRule](#membersetrule)** : prevents  <sub>0..\*</sub> 
 *  **[PeriodAggregation](#periodaggregation)** : prevents  <sub>0..\*</sub> 
 *  **[QualityExpectation](#qualityexpectation)** : prevents  <sub>0..\*</sub> 
 *  **[RefusalCode](#refusalcode)** : prevents  <sub>0..\*</sub> 
 *  **[TotalsRule](#totalsrule)** : prevents  <sub>0..\*</sub> 


### Flag

A code attached to a result row that changes how the number reads.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[value_semantics](#slot-flag__value_semantics)** | <sub>1..1</sub> | string | What the number means when this flag is set. Written into the agent's tool description. |

#### Referenced by:

 *  **[BeyondHorizonRule](#beyondhorizonrule)** : beyondHorizonRule__flag  <sub>1..1</sub> 
 *  **[DepletionOutcome](#depletionoutcome)** : depletionOutcome__flag  <sub>0..1</sub> 
 *  **[ExhaustionPeriodRule](#exhaustionperiodrule)** : exhaustionPeriodRule__none_for_flags  <sub>0..\*</sub> 
 *  **[MetricContract](#metriccontract)** : flags  <sub>0..\*</sub> 
 *  **[MemberSelection](#memberselection)** : memberSelection__set_apart_flags  <sub>1..\*</sub> 


### ItemDimension

A physical dimension in which items are counted (mass, volume). Quantities of two dimensions never add up, in any conversion.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[base_unit](#slot-itemdimension__base_unit)** | <sub>1..1</sub> | string | The unit of the quantity equivalent in this dimension (kg, L). |

#### Referenced by:

 *  **[BasisModel](#basismodel)** : basisModel__dimensions  <sub>1..\*</sub> 


### Measure

A numeric fact, typed as a snapshot (a level at a point in time) or a flow (an amount per period).


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[name](#slot-name)** | <sub>0..1</sub> | string | A human-readable name. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[additivity](#slot-measure__additivity)** | <sub>1..\*</sub> | [Additivity](#additivity) | One entry per dimension class. A class not listed is not additive. |
| **[columns](#slot-measure__columns)** | <sub>1..\*</sub> | [MeasureColumn](#measurecolumn) | The physical column of this measure on each measure basis. |
| **[measure_type](#slot-measure__measure_type)** | <sub>1..1</sub> | [MeasureType](#measuretype) | SNAPSHOT (a level read at one period) or FLOW (an amount per period, summed over a window). The tests check that the additivity agrees with it; the compiler takes each measure's role from the metric (snapshot_measure, flow_measure). |
| **[period_aggregation](#slot-measure__period_aggregation)** | <sub>0..1</sub> | [PeriodAggregation](#periodaggregation) | How the measure reads over a period longer than its time grain. Required for a SNAPSHOT measure (a level is never summed over time); a FLOW measure sums over the period and declares none. |
| **[table](#slot-measure__table)** | <sub>1..1</sub> | [Table](#table) | The fact table that holds the measure. |
| **[time_column](#slot-measure__time_column)** | <sub>1..1</sub> | string | Column of the table that carries the period. The procedure reads the snapshot at exactly the analysis month, and the flow over the forward window, each on its own time column. |
| **[time_grain](#slot-measure__time_grain)** | <sub>1..1</sub> | [TimeGrain](#timegrain) | The period of one row (MONTH here). Declared, not read by the compiler: the generated SQL counts months. **Fixed: only MONTH is supported by this compiler.** |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : measures  <sub>1..\*</sub> 
 *  **[DefaultScope](#defaultscope)** : defaultScope__applies_to_measures  <sub>1..\*</sub> 
 *  **[DepletionMetric](#depletionmetric)** : depletionMetric__flow_measure  <sub>1..1</sub> 
 *  **[DepletionMetric](#depletionmetric)** : depletionMetric__snapshot_measure  <sub>1..1</sub> 
 *  **[MeasureApplicability](#measureapplicability)** : measureApplicability__measure  <sub>1..1</sub> 
 *  **[MetricContract](#metriccontract)** : measures  <sub>0..\*</sub> 


### MeasureApplicability

The effect of an attribute on one measure.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[effect](#slot-measureapplicability__effect)** | <sub>1..1</sub> | [ApplicabilityEffect](#applicabilityeffect) | GROUP_AND_FILTER, IGNORED or REFUSED. The tests check that it agrees with the attribute's applicability_class; the closing view exposes the attributes that GROUP_AND_FILTER the snapshot. |
| **[measure](#slot-measureapplicability__measure)** | <sub>1..1</sub> | [Measure](#measure) | The measure. |

#### Referenced by:

 *  **[Attribute](#attribute)** : attribute__applicability  <sub>1..\*</sub> 


### MeasureBasis

A basis on which the snapshot and the flow are measured before a ratio, or summed. A basis is not the unit of a ratio's result: it decides which quantities are comparable. Each basis is valid only where its sums stay comparable (valid_when); elsewhere the call is refused, never switched to another basis silently.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[kind](#slot-measurebasis__kind)** | <sub>1..1</sub> | [BasisKind](#basiskind) | NATIVE_UNIT, BASE_UNIT_EQUIVALENT or MONETARY: what the basis measures. Declared, not read by the compiler: the procedure reads valid_when and unit_source. **Documentation only.** |
| **[not_comparable_reason](#slot-measurebasis__not_comparable_reason)** | <sub>1..1</sub> | string | Why a row or a total breaks valid_when, in business words, for the refusal reason. |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[synonyms](#slot-synonyms)** | <sub>0..\*</sub> | string | Other words for the element. A metric's go into the tool description and B2's view; a basis's are accepted by the procedure as the basis parameter. |
| **[unit_source](#slot-measurebasis__unit_source)** | <sub>1..1</sub> | [BasisUnitSource](#basisunitsource) | Where the unit of a figure on this basis comes from (the item, its dimension, or a fixed symbol). |
| **[unit_symbol](#slot-measurebasis__unit_symbol)** | <sub>0..1</sub> | string | The unit shown for every figure on this basis when unit_source is FIXED (EUR). |
| **[valid_when](#slot-measurebasis__valid_when)** | <sub>1..1</sub> | [BasisValidity](#basisvalidity) | Where the basis stays comparable: ONE_ITEM_PER_ROW, ONE_DIMENSION_PER_ROW or ALWAYS. The procedure counts the items and the dimensions behind every returned row and total, and refuses with BASIS_NOT_COMPARABLE where the rule breaks. |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : measure_bases  <sub>1..\*</sub> 
 *  **[BasisModel](#basismodel)** : basisModel__default_basis  <sub>1..1</sub> 
 *  **[MeasureColumn](#measurecolumn)** : measureColumn__basis  <sub>1..1</sub> 
 *  **[MetricContract](#metriccontract)** : measure_bases  <sub>0..\*</sub> 


### MeasureColumn

The physical column of a measure on one measure basis.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[basis](#slot-measurecolumn__basis)** | <sub>1..1</sub> | [MeasureBasis](#measurebasis) | The measure basis (QTY_EQ, VALUE, NATIVE). |
| **[column](#slot-measurecolumn__column)** | <sub>1..1</sub> | string | The column that holds the measure on that basis; the procedure reads it when the caller asks for that basis. |

#### Referenced by:

 *  **[Measure](#measure)** : measure__columns  <sub>1..\*</sub> 


### MemberSelection

Keeps the detail rows of a call by their result. The procedure filters and ranks; a consumer never sorts or filters results itself. Total rows are not selected: they keep their totals rule. Members whose result is set by a flag listed in set_apart_flags never mix with the kept rows: they come back apart, counted and named.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[grain_rule](#slot-memberselection__grain_rule)** | <sub>0..1</sub> | string | Which grain a question takes: a list question takes items, a question for one figure takes its scope's grain (metamodel 0.4.1). Given verbatim to every configuration. |
| **[lower_bound_parameter](#slot-memberselection__lower_bound_parameter)** | <sub>1..1</sub> | [Parameter](#parameter) | The parameter that keeps the members above N periods (coverage_above): result > N. With the upper bound, a window. |
| **[lower_bound_rule](#slot-memberselection__lower_bound_rule)** | <sub>1..1</sub> | string | The rows kept by the lower bound, as a condition. The procedure's SQL implements it. **Documentation only.** |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[rank_parameter](#slot-memberselection__rank_parameter)** | <sub>1..1</sub> | [Parameter](#parameter) | The parameter that keeps the first n members by result, lowest first (rank_first), per analysis month. |
| **[rank_rule](#slot-memberselection__rank_rule)** | <sub>1..1</sub> | string | The order of the rows and how ties are broken (by the grain codes, in grain order). The procedure's SQL implements it. **Documentation only.** |
| **[set_apart_flags](#slot-memberselection__set_apart_flags)** | <sub>1..\*</sub> | [Flag](#flag) | Flags whose members never mix with the kept rows (NO_STOCK, NO_DEMAND): the procedure returns them apart, counted and named. |
| **[summary_rule](#slot-memberselection__summary_rule)** | <sub>1..1</sub> | string | What the summary of the kept rows gives. The summary is a total: it follows the basis rule (a snapshot sum per comparable unit, never across units) and never sums or averages the metric's result. **Documentation only.** |
| **[upper_bound_parameter](#slot-memberselection__upper_bound_parameter)** | <sub>1..1</sub> | [Parameter](#parameter) | The parameter that keeps the members running out within N periods (coverage_below): 0 < result <= N. |
| **[upper_bound_rule](#slot-memberselection__upper_bound_rule)** | <sub>1..1</sub> | string | The rows kept by the upper bound, as a condition. The procedure's SQL implements it. **Documentation only.** |

#### Referenced by:

 *  **[DepletionMetric](#depletionmetric)** : depletionMetric__member_selection  <sub>0..1</sub> 


### MemberSetRule

Which members (rows) an answer contains.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[flow_members](#slot-membersetrule__flow_members)** | <sub>1..1</sub> | [MemberSource](#membersource) | When the flow contributes members. ONLY_ON_CONFORMED_GRAIN: a forecast creates a row only when the grain holds no snapshot-only attribute. The procedure reads it. |
| **[method](#slot-membersetrule__method)** | <sub>1..1</sub> | [MemberSetMethod](#membersetmethod) | SPINE: members are the union of the snapshot's and the flow's members, then both measures are left-joined. Declared, not read by the compiler: the procedure implements it. **Fixed: only SPINE is supported by this compiler.** |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[snapshot_members](#slot-membersetrule__snapshot_members)** | <sub>1..1</sub> | [MemberSource](#membersource) | When the snapshot contributes members (ALWAYS). Declared, not read by the compiler: the procedure implements it. **Fixed: only ALWAYS is supported by this compiler.** |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : member_set_rules  <sub>0..\*</sub> 


### MetricContract

One metric contract. The single hand-written source of truth for a metric and everything it needs.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[name](#slot-name)** | <sub>0..1</sub> | string | A human-readable name. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[alert_thresholds](#slot-alert_thresholds)** | <sub>0..\*</sub> | [AlertThreshold](#alertthreshold) | Thresholds for a later restitution layer; not compiled. |
| **[analysis_periods](#slot-analysis_periods)** | <sub>0..\*</sub> | [AnalysisPeriods](#analysisperiods) | The anchor periods a caller may ask for; the compiler reads the first entry. |
| **[attributes](#slot-attributes)** | <sub>1..\*</sub> | [Attribute](#attribute) | Everything a caller may group or filter by. An attribute not declared here is refused (ATTRIBUTE_UNKNOWN). |
| **[basis_model](#slot-basis_model)** | <sub>1..1</sub> | [BasisModel](#basismodel) | Where each item's dimension and units are read, and the default basis. |
| **[changes](#slot-changes)** | <sub>0..\*</sub> | [ContractChange](#contractchange) | The change log, one entry per version. |
| **[default_scopes](#slot-default_scopes)** | <sub>0..\*</sub> | [DefaultScope](#defaultscope) | Restrictions applied unless the caller lifts them. The procedure reads the first entry and needs one. |
| **[dimension_classes](#slot-dimension_classes)** | <sub>0..\*</sub> | [DimensionClass](#dimensionclass) | The classes along which additivity is declared (time, product, geography). |
| **[effective_date](#slot-effective_date)** | <sub>1..1</sub> | date | The date from which the version applies. |
| **[failure_modes](#slot-failure_modes)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | The traps: known ways to get the metric wrong, each with its wrong and correct behaviour. |
| **[flags](#slot-flags)** | <sub>0..\*</sub> | [Flag](#flag) | Codes on a result row that change how its number reads. |
| **[invariants](#slot-invariants)** | <sub>0..\*</sub> | [CalculationInvariant](#calculationinvariant) | Properties every correct result satisfies; several are tested against the deployed procedure. |
| **[measure_bases](#slot-measure_bases)** | <sub>1..\*</sub> | [MeasureBasis](#measurebasis) | The bases on which the measures are compared before the ratio. |
| **[measures](#slot-measures)** | <sub>1..\*</sub> | [Measure](#measure) | The numeric facts; a depletion metric has a snapshot and a flow. |
| **[member_set_rules](#slot-member_set_rules)** | <sub>0..\*</sub> | [MemberSetRule](#membersetrule) | Which members an answer contains; the compiler reads the first entry. |
| **[metrics](#slot-metrics)** | <sub>1..\*</sub> | [DepletionMetric](#depletionmetric) | The metrics of the contract. DepletionMetric is the only pattern; the compiler reads the first entry. |
| **[open_decisions](#slot-open_decisions)** | <sub>0..\*</sub> | [OpenDecision](#opendecision) | Choices the owner has not confirmed yet. |
| **[ownership](#slot-ownership)** | <sub>1..1</sub> | [Ownership](#ownership) | Who answers for the contract, by role. |
| **[parameters](#slot-parameters)** | <sub>1..\*</sub> | [Parameter](#parameter) | The tool's parameters. Each is one VARCHAR argument of the procedure and one string property of the tool. |
| **[quality_expectations](#slot-quality_expectations)** | <sub>0..\*</sub> | [QualityExpectation](#qualityexpectation) | Conditions on the data: compiled to data metric functions, and checked again in the call unless MONITOR. |
| **[refusal_codes](#slot-refusal_codes)** | <sub>0..\*</sub> | [RefusalCode](#refusalcode) | The refusals, in check order. Each must have a check in the procedure, or the generator fails. |
| **[relationships](#slot-relationships)** | <sub>0..\*</sub> | [Relationship](#relationship) | The join paths between the tables. |
| **[status](#slot-status)** | <sub>0..1</sub> | [ContractStatus](#contractstatus) | DRAFT, ACTIVE or DEPRECATED. |
| **[tables](#slot-tables)** | <sub>0..\*</sub> | [Table](#table) | The physical tables the metric reads. |
| **[totals_rules](#slot-totals_rules)** | <sub>0..\*</sub> | [TotalsRule](#totalsrule) | How totals are obtained; the compiler reads the first entry. |
| **[version](#slot-version)** | <sub>1..1</sub> | string | The contract's version. Every generated file names it in its header, and the procedure returns it with each answer. |
| **[warning_codes](#slot-warning_codes)** | <sub>0..\*</sub> | [WarningCode](#warningcode) | Messages attached to an answer that is still given. |


### OpenDecision

A choice the contract had to make that the owner has not confirmed. The compiler may refuse to build a release while an open decision marked blocking remains.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[blocking](#slot-opendecision__blocking)** | <sub>0..1</sub> | boolean | True when a release must wait for the owner's decision. Declared, not read by the compiler. **Documentation only.** |
| **[current_choice](#slot-opendecision__current_choice)** | <sub>1..1</sub> | string | The choice the contract applies today, until the owner confirms or changes it. |
| **[evidence](#slot-evidence)** | <sub>0..1</sub> | [EvidenceTag](#evidencetag) | How the element is known (documented, measured here, inferred). |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : open_decisions  <sub>0..\*</sub> 


### Ownership

Who answers for the contract. Roles, never personal names.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[business_owner](#slot-ownership__business_owner)** | <sub>1..1</sub> | string | Role accountable for the business meaning: the definition, the refusals and the traps. A role, never a person's name. |
| **[data_steward](#slot-ownership__data_steward)** | <sub>0..1</sub> | string | Role accountable for the data-quality expectations. |
| **[review_cadence](#slot-ownership__review_cadence)** | <sub>0..1</sub> | string | When the contract is reviewed, for example at every change of a rule and before each release. |
| **[technical_owner](#slot-ownership__technical_owner)** | <sub>1..1</sub> | string | Role accountable for the generated objects and their deployment. A role, never a person's name. |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : ownership  <sub>1..1</sub> 
 *  **[MetricContract](#metriccontract)** : ownership  <sub>0..1</sub> 


### Parameter

One parameter of the generated tool and procedure.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[allowed_values](#slot-parameter__allowed_values)** | <sub>0..\*</sub> | string | The values accepted, for an ENUM. Declared, not read by the compiler: the procedure accepts a basis by its id or one of its synonyms (measure_bases). **Fixed: only the ids of measure_bases, in order is supported by this compiler.** |
| **[data_type](#slot-parameter__data_type)** | <sub>1..1</sub> | [ParameterType](#parametertype) | The parameter's kind. The procedure parses the NUMBER and INTEGER selection parameters by it. |
| **[default_value](#slot-parameter__default_value)** | <sub>0..1</sub> | string | Used when the caller passes nothing: the argument's DEFAULT in the procedure, and stated in the tool description. |
| **[encoding](#slot-parameter__encoding)** | <sub>1..1</sub> | [ParameterEncoding](#parameterencoding) | PLAIN or JSON_STRING; the tool description says that a JSON value is passed as a string. |
| **[example](#slot-parameter__example)** | <sub>0..1</sub> | string | An example value, written into the tool description and the procedure's header. |
| **[exclusive_minimum](#slot-parameter__exclusive_minimum)** | <sub>0..1</sub> | float | A NUMBER or INTEGER parameter must be greater than this (0 here); the procedure refuses 0 or less with SELECTION_INVALID. |
| **[is_required](#slot-parameter__is_required)** | <sub>1..1</sub> | boolean | Required parameters come first in the procedure's signature and form the tool's required list. |
| **[json_shape](#slot-parameter__json_shape)** | <sub>0..1</sub> | string | JSON shape when encoding is JSON_STRING, for example array of string. |
| **[max_items](#slot-parameter__max_items)** | <sub>0..1</sub> | integer | The most items in a list. Declared, not read by the compiler: the cap on analysis months comes from analysis_periods.max_periods. **Fixed: only the analysis periods' max_periods is supported by this compiler.** |
| **[min_items](#slot-parameter__min_items)** | <sub>0..1</sub> | integer | The fewest items in a list. Declared, not read by the compiler: an empty list has its own refusal (AS_OF_MISSING, GRAIN_EMPTY). **Fixed: only 1 is supported by this compiler.** |
| **[refusal_codes](#slot-parameter__refusal_codes)** | <sub>0..\*</sub> | [RefusalCode](#refusalcode) | The refusal codes this parameter can raise; the tests check that each one exists. |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : parameters  <sub>1..\*</sub> 
 *  **[DepletionMetric](#depletionmetric)** : depletionMetric__anchor_parameter  <sub>1..1</sub> 
 *  **[MemberSelection](#memberselection)** : memberSelection__lower_bound_parameter  <sub>1..1</sub> 
 *  **[MemberSelection](#memberselection)** : memberSelection__rank_parameter  <sub>1..1</sub> 
 *  **[MemberSelection](#memberselection)** : memberSelection__upper_bound_parameter  <sub>1..1</sub> 
 *  **[MetricContract](#metriccontract)** : parameters  <sub>0..\*</sub> 
 *  **[TotalsRule](#totalsrule)** : totalsRule__parameter  <sub>0..1</sub> 


### PeriodAggregation

The value of a SNAPSHOT measure over a period (a range of its time grain, a quarter, a year): which snapshot is read, which members the period has, and what a member with no row in the selected snapshot is worth.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[forbidden_methods](#slot-periodaggregation__forbidden_methods)** | <sub>1..\*</sub> | [PeriodAggregationMethod](#periodaggregationmethod) | Methods a consumer must never apply over the period. Each one is a known wrong behaviour. |
| **[member_set](#slot-periodaggregation__member_set)** | <sub>1..1</sub> | [PeriodMemberSet](#periodmemberset) | Which members a period has. Declared, not read by the compiler: the gap-filled view implements ANY_SNAPSHOT_IN_PERIOD by giving each key a row from its first snapshot month to the month after its last. **Fixed: only ANY_SNAPSHOT_IN_PERIOD is supported by this compiler.** |
| **[method](#slot-periodaggregation__method)** | <sub>1..1</sub> | [PeriodAggregationMethod](#periodaggregationmethod) | How the snapshot reads over a period. The closing view supports LAST_PERIOD only: gen_closing_sv.py stops on any other method. |
| **[missing_value](#slot-periodaggregation__missing_value)** | <sub>1..1</sub> | string | Value of a member of the period with no row in the selected snapshot (0 here). The gap-filled view writes it into every measure column where the key has no row; the member keeps its row. |
| **[periods](#slot-periodaggregation__periods)** | <sub>1..\*</sub> | [PeriodKind](#periodkind) | Periods the rule applies to. Each becomes a dimension of the closing view: PERIOD_RANGE a range of months, QUARTER the year and quarter, YEAR the year. |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |

#### Referenced by:

 *  **[Measure](#measure)** : measure__period_aggregation  <sub>0..1</sub> 


### QualityExpectation

A condition on the data under which the metric's promise holds. Compiled to a data metric function and checked again by the procedure where on_failure says so.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[call_scope](#slot-qualityexpectation__call_scope)** | <sub>0..1</sub> | [CallScope](#callscope) | Rows the procedure checks again at call time. Required unless on_failure is MONITOR. A count over the whole table would warn on every answer; a check scoped to the request warns only when the answer reads the rows. |
| **[columns](#slot-qualityexpectation__columns)** | <sub>0..\*</sub> | string | The columns checked. For COMPLETENESS and FRESHNESS the time column comes first; a system data metric function is called once per column. |
| **[condition](#slot-qualityexpectation__condition)** | <sub>1..1</sub> | string | The condition, in words or as a SQL predicate. |
| **[dmf](#slot-qualityexpectation__dmf)** | <sub>1..1</sub> | string | A system data metric function (SNOWFLAKE.CORE.DUPLICATE_COUNT, NULL_COUNT, NEGATIVE_COUNT, FRESHNESS), or CUSTOM: gen_dmf.py then writes one from the kind. |
| **[kind](#slot-qualityexpectation__kind)** | <sub>1..1</sub> | [QualityKind](#qualitykind) | The kind of check; it picks the SQL template of the data metric function and of the in-call check. |
| **[on_failure](#slot-qualityexpectation__on_failure)** | <sub>1..1</sub> | [FailureAction](#failureaction) | What a failure does: REFUSE every query, REFUSE_IF_USED a query that uses the affected columns, WARN in the answer, or MONITOR (data metric function only). |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[references_columns](#slot-qualityexpectation__references_columns)** | <sub>0..\*</sub> | string | Its matching columns, in the order of columns. |
| **[references_table](#slot-qualityexpectation__references_table)** | <sub>0..1</sub> | [Table](#table) | For a check across tables (REFERENTIAL, some CARDINALITY): the table that must hold a match. |
| **[refusal](#slot-qualityexpectation__refusal)** | <sub>0..1</sub> | [RefusalCode](#refusalcode) | The refusal raised when the check fails in a call (REFUSE, REFUSE_IF_USED). |
| **[schedule](#slot-qualityexpectation__schedule)** | <sub>0..1</sub> | string | When the data metric function would run. Declared, not read by the compiler: generated/dmf.sql attaches nothing to a table and sets no schedule. **Fixed: only no schedule is supported by this compiler.** |
| **[severity](#slot-qualityexpectation__severity)** | <sub>1..1</sub> | [Severity](#severity) | ERROR, WARNING or INFO: a reading aid. What a failure does is set by on_failure. |
| **[table](#slot-qualityexpectation__table)** | <sub>1..1</sub> | [Table](#table) | The table checked. |
| **[threshold](#slot-qualityexpectation__threshold)** | <sub>1..1</sub> | string | The accepted violation count (0 here). TBD means no threshold yet: a FRESHNESS check with TBD is not run in the call. |
| **[warning](#slot-qualityexpectation__warning)** | <sub>0..1</sub> | [WarningCode](#warningcode) | The warning raised when the check fails in a call (WARN, REFUSE_IF_USED). |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : quality_expectations  <sub>0..\*</sub> 


### RefusalCode

A refusal the procedure returns instead of a number, with its reason.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[category](#slot-refusalcode__category)** | <sub>1..1</sub> | [RefusalCategory](#refusalcategory) | PARAMETER, SEMANTIC, DATA_QUALITY or AVAILABILITY: a reading aid, not read by the compiler. |
| **[check_order](#slot-refusalcode__check_order)** | <sub>0..1</sub> | integer | Validation order: lower checks run first and the first that fails ends the call. The generator fails when the order breaks a check's prerequisite. |
| **[evidence](#slot-evidence)** | <sub>0..1</sub> | [EvidenceTag](#evidencetag) | How the element is known (documented, measured here, inferred). |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[reason_template](#slot-refusalcode__reason_template)** | <sub>1..1</sub> | string | The reason returned with the code; the procedure fills the {placeholders} (the value given, the months available, the attributes allowed). |

#### Referenced by:

 *  **[BasisModel](#basismodel)** : basisModel__refusal  <sub>1..1</sub> 
 *  **[Parameter](#parameter)** : parameter__refusal_codes  <sub>0..\*</sub> 
 *  **[QualityExpectation](#qualityexpectation)** : qualityExpectation__refusal  <sub>0..1</sub> 
 *  **[MetricContract](#metriccontract)** : refusal_codes  <sub>0..\*</sub> 


### Relationship

A join path between two tables. The cardinality is declared and checked, never assumed.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[cardinality](#slot-relationship__cardinality)** | <sub>1..1</sub> | [Cardinality](#cardinality) | The declared cardinality. The procedure and the closing view join only MANY_TO_ONE relationships from a fact; whether the key is really unique is checked by a GRAIN_UNIQUENESS quality expectation. |
| **[from_columns](#slot-relationship__from_columns)** | <sub>1..\*</sub> | string | Its key columns, in the order of to_columns. |
| **[from_table](#slot-relationship__from_table)** | <sub>1..1</sub> | [Table](#table) | The table that holds the foreign key, usually a fact. |
| **[to_columns](#slot-relationship__to_columns)** | <sub>1..\*</sub> | string | The joined table's key columns. |
| **[to_table](#slot-relationship__to_table)** | <sub>1..1</sub> | [Table](#table) | The table joined to, usually a dimension. |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : relationships  <sub>0..\*</sub> 


### Table

A physical table read by the metric, with its declared grain.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[columns](#slot-table__columns)** | <sub>1..\*</sub> | [Column](#column) | The physical columns in load order, with their Snowflake types. generated/schema.py lists them for the loader; the data metric functions take their types. |
| **[grain](#slot-table__grain)** | <sub>1..\*</sub> | string | Columns whose values identify one row. Uniqueness is a quality expectation, not an assumption. The flow table's grain less its time column gives the members of the metric (item and country); the snapshot table's grain gives the keys of the gap-filled closing view. |
| **[kind](#slot-table__kind)** | <sub>1..1</sub> | [TableKind](#tablekind) | FACT for a table of measures, DIMENSION for a table of attributes. Declared, not read by the compiler. **Documentation only.** |

#### Referenced by:

 *  **[AnalysisPeriods](#analysisperiods)** : analysisPeriods__source_table  <sub>1..1</sub> 
 *  **[Attribute](#attribute)** : attribute__table  <sub>1..1</sub> 
 *  **[BasisModel](#basismodel)** : basisModel__item_table  <sub>1..1</sub> 
 *  **[Measure](#measure)** : measure__table  <sub>1..1</sub> 
 *  **[QualityExpectation](#qualityexpectation)** : qualityExpectation__references_table  <sub>0..1</sub> 
 *  **[QualityExpectation](#qualityexpectation)** : qualityExpectation__table  <sub>1..1</sub> 
 *  **[Relationship](#relationship)** : relationship__from_table  <sub>1..1</sub> 
 *  **[Relationship](#relationship)** : relationship__to_table  <sub>1..1</sub> 
 *  **[MetricContract](#metriccontract)** : tables  <sub>0..\*</sub> 


### TotalsRule

How a total (a coarser grain) is obtained.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[flow_aggregation](#slot-totalsrule__flow_aggregation)** | <sub>1..1</sub> | [TotalsProjection](#totalsprojection) | How the flow reaches it (CONFORMED_PROJECTION: the total's grain less its snapshot-only attributes). Declared, not read by the compiler: the procedure implements it. **Fixed: only CONFORMED_PROJECTION is supported by this compiler.** |
| **[method](#slot-totalsrule__method)** | <sub>1..1</sub> | [TotalsMethod](#totalsmethod) | RECOMPUTE: a total aggregates the inputs to its grain and runs the algorithm again. Declared, not read by the compiler: the procedure implements this one method. **Fixed: only RECOMPUTE is supported by this compiler.** |
| **[parameter](#slot-totalsrule__parameter)** | <sub>0..1</sub> | [Parameter](#parameter) | The parameter through which a caller asks for totals (totals). |
| **[prevents](#slot-prevents)** | <sub>0..\*</sub> | [FailureMode](#failuremode) | Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. |
| **[snapshot_aggregation](#slot-totalsrule__snapshot_aggregation)** | <sub>1..1</sub> | [TotalsProjection](#totalsprojection) | How the snapshot reaches the total's grain (TOTAL_GRAIN). Declared, not read by the compiler: the procedure implements it. **Fixed: only TOTAL_GRAIN is supported by this compiler.** |
| **[total_over_time](#slot-totalsrule__total_over_time)** | <sub>1..1</sub> | [TimeTotalRule](#timetotalrule) | FORBIDDEN: several analysis months give a series, never a total across months. Declared, not read by the compiler: the procedure implements it. **Fixed: only FORBIDDEN is supported by this compiler.** |

#### Referenced by:

 *  **[MetricContract](#metriccontract)** : totals_rules  <sub>0..\*</sub> 


### WarningCode

A message attached to a whole answer, raised by a rule or a failed quality expectation.


#### Attributes

| Name | Cardinality: | Type | Description |
| --- | --- | --- | --- |
| **[id](#slot-id)** | <sub>1..1</sub> | string | The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. |
| **[description](#slot-description)** | <sub>0..1</sub> | string | Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. |
| **[message_template](#slot-warningcode__message_template)** | <sub>1..1</sub> | string | The message attached to the answer; the procedure fills the {placeholders} (a count, an amount, a unit). |
| **[raised_by](#slot-warningcode__raised_by)** | <sub>1..1</sub> | string | Id of the rule or expectation that raises it. |

#### Referenced by:

 *  **[DefaultScope](#defaultscope)** : defaultScope__warning  <sub>1..1</sub> 
 *  **[QualityExpectation](#qualityexpectation)** : qualityExpectation__warning  <sub>0..1</sub> 
 *  **[MetricContract](#metriccontract)** : warning_codes  <sub>0..\*</sub> 


## Slots

| Name | Cardinality/Range | Used By |
| --- | --- | --- |
| <a id="slot-id"></a>**id**<br/>The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. | <sub>1..1</sub><br/>string | [AlertThreshold](#alertthreshold), [AnalysisPeriods](#analysisperiods), [Attribute](#attribute), [BasisModel](#basismodel), [CalculationInvariant](#calculationinvariant), [DefaultScope](#defaultscope), [DepletionMetric](#depletionmetric), [DimensionClass](#dimensionclass), [ExhaustionPeriodRule](#exhaustionperiodrule), [FailureMode](#failuremode), [Flag](#flag), [ItemDimension](#itemdimension), [Measure](#measure), [MeasureBasis](#measurebasis), [MemberSelection](#memberselection), [MemberSetRule](#membersetrule), [MetricContract](#metriccontract), [OpenDecision](#opendecision), [Parameter](#parameter), [PeriodAggregation](#periodaggregation), [QualityExpectation](#qualityexpectation), [RefusalCode](#refusalcode), [Relationship](#relationship), [Table](#table), [TotalsRule](#totalsrule), [WarningCode](#warningcode) |
| <a id="slot-name"></a>**name**<br/>A human-readable name. | <sub>0..1</sub><br/>string | [Column](#column), [DepletionMetric](#depletionmetric), [FailureMode](#failuremode), [Measure](#measure), [MetricContract](#metriccontract) |
| <a id="slot-description"></a>**description**<br/>Plain-language text. Some of it travels into generated objects: a metric's, a flag's and a basis's into the agent's tool description, an attribute's into view comments and the ATTRIBUTE_NOT_APPLICABLE reason. | <sub>0..1</sub><br/>string | [AlertThreshold](#alertthreshold), [AnalysisPeriods](#analysisperiods), [Attribute](#attribute), [BasisModel](#basismodel), [CalculationInvariant](#calculationinvariant), [Column](#column), [DefaultScope](#defaultscope), [DepletionMetric](#depletionmetric), [DimensionClass](#dimensionclass), [ExhaustionPeriodRule](#exhaustionperiodrule), [FailureMode](#failuremode), [Flag](#flag), [ItemDimension](#itemdimension), [Measure](#measure), [MeasureBasis](#measurebasis), [MemberSelection](#memberselection), [MemberSetRule](#membersetrule), [MetricContract](#metriccontract), [OpenDecision](#opendecision), [Parameter](#parameter), [PeriodAggregation](#periodaggregation), [QualityExpectation](#qualityexpectation), [RefusalCode](#refusalcode), [Relationship](#relationship), [Table](#table), [TotalsRule](#totalsrule), [WarningCode](#warningcode) |
| <a id="slot-metriccontract_attributes"></a>**MetricContract_attributes**<br/>Everything a caller may group or filter by. An attribute not declared here is refused (ATTRIBUTE_UNKNOWN). | <sub>1..\*</sub><br/>[Attribute](#attribute) |  |
| <a id="slot-metriccontract_basis_model"></a>**MetricContract_basis_model**<br/>Where each item's dimension and units are read, and the default basis. | <sub>1..1</sub><br/>[BasisModel](#basismodel) |  |
| <a id="slot-metriccontract_effective_date"></a>**MetricContract_effective_date**<br/>The date from which the version applies. | <sub>1..1</sub><br/>date |  |
| <a id="slot-metriccontract_id"></a>**MetricContract_id**<br/>The element's identifier, unique in its section. Codes in UPPER_CASE travel verbatim into the procedure's answer and the tool description. | <sub>1..1</sub><br/>string |  |
| <a id="slot-metriccontract_measure_bases"></a>**MetricContract_measure_bases**<br/>The bases on which the measures are compared before the ratio. | <sub>1..\*</sub><br/>[MeasureBasis](#measurebasis) |  |
| <a id="slot-metriccontract_measures"></a>**MetricContract_measures**<br/>The numeric facts; a depletion metric has a snapshot and a flow. | <sub>1..\*</sub><br/>[Measure](#measure) |  |
| <a id="slot-metriccontract_metrics"></a>**MetricContract_metrics**<br/>The metrics of the contract. DepletionMetric is the only pattern; the compiler reads the first entry. | <sub>1..\*</sub><br/>[DepletionMetric](#depletionmetric) |  |
| <a id="slot-metriccontract_ownership"></a>**MetricContract_ownership**<br/>Who answers for the contract, by role. | <sub>1..1</sub><br/>[Ownership](#ownership) |  |
| <a id="slot-metriccontract_parameters"></a>**MetricContract_parameters**<br/>The tool's parameters. Each is one VARCHAR argument of the procedure and one string property of the tool. | <sub>1..\*</sub><br/>[Parameter](#parameter) |  |
| <a id="slot-metriccontract_version"></a>**MetricContract_version**<br/>The contract's version. Every generated file names it in its header, and the procedure returns it with each answer. | <sub>1..1</sub><br/>string |  |
| <a id="slot-additivity__aggregation"></a>**additivity__aggregation**<br/>SUM, SELECT_PERIOD, SUM_OVER_WINDOW or NONE. The tests check it against measure_type (a snapshot selects its period on TIME, a flow sums over the window); the generated SQL implements it. | <sub>1..1</sub><br/>[AggregationRule](#aggregationrule) |  |
| <a id="slot-additivity__dimension_class"></a>**additivity__dimension_class**<br/>The dimension class this rule covers. | <sub>1..1</sub><br/>[DimensionClass](#dimensionclass) |  |
| <a id="slot-additivity__note"></a>**additivity__note**<br/>A free note that explains the rule. | <sub>0..1</sub><br/>string |  |
| <a id="slot-alertthreshold__compared_to"></a>**alertThreshold__compared_to**<br/>The quantity compared, as a formula over metric outputs and attributes. | <sub>1..1</sub><br/>string |  |
| <a id="slot-alertthreshold__comparison"></a>**alertThreshold__comparison**<br/>LT, LE, GT or GE. | <sub>1..1</sub><br/>[Comparison](#comparison) |  |
| <a id="slot-alertthreshold__metric"></a>**alertThreshold__metric**<br/>The metric compared. | <sub>1..1</sub><br/>[DepletionMetric](#depletionmetric) |  |
| <a id="slot-alertthreshold__raises_flag"></a>**alertThreshold__raises_flag**<br/>The flag a restitution layer would raise (STOCKOUT_RISK, EXPIRY_RISK). Declared, not read by the compiler; the values are TBD. **Documentation only.** | <sub>0..1</sub><br/>string |  |
| <a id="slot-alertthreshold__unit"></a>**alertThreshold__unit**<br/>The unit of the value (months). | <sub>1..1</sub><br/>string |  |
| <a id="slot-alertthreshold__value"></a>**alertThreshold__value**<br/>A number, or TBD while the owner has not set it. | <sub>1..1</sub><br/>string |  |
| <a id="slot-alert_thresholds"></a>**alert_thresholds**<br/>Thresholds for a later restitution layer; not compiled. | <sub>0..\*</sub><br/>[AlertThreshold](#alertthreshold) | [MetricContract](#metriccontract) |
| <a id="slot-analysisperiods__exposed_in"></a>**analysisPeriods__exposed_in**<br/>Where the valid periods are shown. Declared, not read by the compiler: the agent's specification carries the first, last and LATEST months at generation, and every procedure answer carries them at call time. **Documentation only.** | <sub>1..\*</sub><br/>[ExposureTarget](#exposuretarget) |  |
| <a id="slot-analysisperiods__latest_token"></a>**analysisPeriods__latest_token**<br/>A literal the caller may pass for the most recent valid period. | <sub>1..1</sub><br/>string |  |
| <a id="slot-analysisperiods__max_periods"></a>**analysisPeriods__max_periods**<br/>The most analysis months per call (24); more is refused with AS_OF_TOO_MANY. | <sub>0..1</sub><br/>integer |  |
| <a id="slot-analysisperiods__series_allowed"></a>**analysisPeriods__series_allowed**<br/>True: several analysis months may be asked in one call; they give a series. Declared, not read by the compiler: the procedure accepts up to max_periods months. **Fixed: only true is supported by this compiler.** | <sub>1..1</sub><br/>boolean |  |
| <a id="slot-analysisperiods__source_column"></a>**analysisPeriods__source_column**<br/>Its period column. | <sub>1..1</sub><br/>string |  |
| <a id="slot-analysisperiods__source_table"></a>**analysisPeriods__source_table**<br/>The table whose period column lists the periods that exist (the stock snapshot). | <sub>1..1</sub><br/>[Table](#table) |  |
| <a id="slot-analysisperiods__validity"></a>**analysisPeriods__validity**<br/>The condition a period must meet to be offered and accepted. The procedure and the agent's specification apply it: a snapshot exists for the month, and the calendar and the flow reach the month plus H. | <sub>1..1</sub><br/>string |  |
| <a id="slot-analysis_periods"></a>**analysis_periods**<br/>The anchor periods a caller may ask for; the compiler reads the first entry. | <sub>0..\*</sub><br/>[AnalysisPeriods](#analysisperiods) | [MetricContract](#metriccontract) |
| <a id="slot-attribute__applicability"></a>**attribute__applicability**<br/>Effect on each measure. Must agree with applicability_class: CONFORMED = every measure GROUP_AND_FILTER; SNAPSHOT_ONLY = snapshot measures GROUP_AND_FILTER, flow measures IGNORED; NOT_APPLICABLE = REFUSED. | <sub>1..\*</sub><br/>[MeasureApplicability](#measureapplicability) |  |
| <a id="slot-attribute__applicability_class"></a>**attribute__applicability_class**<br/>How the procedure routes the attribute. CONFORMED groups and filters stock and forecast; SNAPSHOT_ONLY restricts the stock and leaves the forecast at the conformed grain; NOT_APPLICABLE is refused (ATTRIBUTE_NOT_APPLICABLE). | <sub>1..1</sub><br/>[ApplicabilityClass](#applicabilityclass) |  |
| <a id="slot-attribute__column"></a>**attribute__column**<br/>The physical column grouped or filtered. | <sub>1..1</sub><br/>string |  |
| <a id="slot-attribute__dimension_class"></a>**attribute__dimension_class**<br/>The dimension class the attribute belongs to. Read by the tests, not by the compiler. | <sub>1..1</sub><br/>[DimensionClass](#dimensionclass) |  |
| <a id="slot-attribute__known_values"></a>**attribute__known_values**<br/>Values listed in the agent's tool description and the semantic view; a VALUE_RANGE quality expectation on the column takes them as its accepted values. Empty means an open set. | <sub>0..\*</sub><br/>string |  |
| <a id="slot-attribute__label_column"></a>**attribute__label_column**<br/>Optional human-readable column shown next to the code. The tool description lists code = name pairs for an attribute with at most 30 codes, read from the dataset. | <sub>0..1</sub><br/>string |  |
| <a id="slot-attribute__table"></a>**attribute__table**<br/>The table that holds the attribute's column; the procedure joins it from each fact through the declared relationships. | <sub>1..1</sub><br/>[Table](#table) |  |
| <a id="slot-attributes"></a>**attributes**<br/>Everything a caller may group or filter by. An attribute not declared here is refused (ATTRIBUTE_UNKNOWN). | <sub>0..\*</sub><br/>[Attribute](#attribute) | [MetricContract](#metriccontract) |
| <a id="slot-basismodel__base_unit_column"></a>**basisModel__base_unit_column**<br/>The column that holds the base unit of the item's dimension (kg, L): the unit of a row on the equivalent basis. | <sub>1..1</sub><br/>string |  |
| <a id="slot-basismodel__default_basis"></a>**basisModel__default_basis**<br/>The basis used when the caller names none. Refused like any other basis where it is not valid. | <sub>1..1</sub><br/>[MeasureBasis](#measurebasis) |  |
| <a id="slot-basismodel__dimension_column"></a>**basisModel__dimension_column**<br/>The column that holds each item's dimension (MASS, VOLUME). | <sub>1..1</sub><br/>string |  |
| <a id="slot-basismodel__dimensions"></a>**basisModel__dimensions**<br/>The physical dimensions declared, each with its base unit. A data metric function (QE_ITEM_DIMENSION) checks every item against this list. | <sub>1..\*</sub><br/>[ItemDimension](#itemdimension) |  |
| <a id="slot-basismodel__equivalence_factor_column"></a>**basisModel__equivalence_factor_column**<br/>Base units per native unit (kg or L per pack). The facts carry the equivalent quantities in their own columns; the compiler lists this column in generated/schema.py and does not compute with it. | <sub>1..1</sub><br/>string |  |
| <a id="slot-basismodel__item_key"></a>**basisModel__item_key**<br/>The key column of the item table. | <sub>1..1</sub><br/>string |  |
| <a id="slot-basismodel__item_table"></a>**basisModel__item_table**<br/>The table that holds each item's dimension and units (DIM_ITEM). The procedure reads it to count the items and dimensions behind each row. | <sub>1..1</sub><br/>[Table](#table) |  |
| <a id="slot-basismodel__native_unit_column"></a>**basisModel__native_unit_column**<br/>The item's own unit: how the item is counted (a pack size). | <sub>1..1</sub><br/>string |  |
| <a id="slot-basismodel__refusal"></a>**basisModel__refusal**<br/>The refusal raised when the basis asked is not comparable (BASIS_NOT_COMPARABLE); the agent's tool description names it. | <sub>1..1</sub><br/>[RefusalCode](#refusalcode) |  |
| <a id="slot-basismodel__result_unit"></a>**basisModel__result_unit**<br/>The unit of the metric's result, the same on every basis. | <sub>1..1</sub><br/>string |  |
| <a id="slot-basismodel__validity_scope"></a>**basisModel__validity_scope**<br/>Where the validity of a basis is judged. Declared, not read by the compiler: the procedure always judges the rows and totals the call returns (RETURNED_ROWS). **Fixed: only RETURNED_ROWS is supported by this compiler.** | <sub>1..1</sub><br/>[BasisValidityScope](#basisvalidityscope) |  |
| <a id="slot-basis_model"></a>**basis_model**<br/>Where each item's dimension and units are read, and the default basis. | <sub>0..1</sub><br/>[BasisModel](#basismodel) | [MetricContract](#metriccontract) |
| <a id="slot-beyondhorizonrule__average_window"></a>**beyondHorizonRule__average_window**<br/>The flow periods the mean covers: HORIZON, the H periods of the window. Declared, not read by the compiler: the procedure's SQL implements it. **Fixed: only HORIZON is supported by this compiler.** | <sub>1..1</sub><br/>[AverageWindow](#averagewindow) |  |
| <a id="slot-beyondhorizonrule__exclude_zero_periods"></a>**beyondHorizonRule__exclude_zero_periods**<br/>True: periods with no flow are left out of the mean, so a sparse forecast does not stretch the result. Declared, not read by the compiler: the procedure's SQL implements it. **Fixed: only true is supported by this compiler.** | <sub>1..1</sub><br/>boolean |  |
| <a id="slot-beyondhorizonrule__flag"></a>**beyondHorizonRule__flag**<br/>The flag set on an extrapolated row (BEYOND_HORIZON); the procedure reads it. | <sub>1..1</sub><br/>[Flag](#flag) |  |
| <a id="slot-beyondhorizonrule__method"></a>**beyondHorizonRule__method**<br/>SNAPSHOT_OVER_MEAN_FLOW: the level divided by the mean flow per period. Declared, not read by the compiler: the procedure's SQL implements this method only. **Fixed: only SNAPSHOT_OVER_MEAN_FLOW is supported by this compiler.** | <sub>1..1</sub><br/>[BeyondHorizonMethod](#beyondhorizonmethod) |  |
| <a id="slot-beyondhorizonrule__prevents"></a>**beyondHorizonRule__prevents**<br/>Failure modes this rule prevents. | <sub>0..\*</sub><br/>[FailureMode](#failuremode) |  |
| <a id="slot-calculationinvariant__statement"></a>**calculationInvariant__statement**<br/>The property, in words. Declared, not read by the compiler; tests/test_procedure.py checks several of them against the deployed procedure. **Documentation only.** | <sub>1..1</sub><br/>string |  |
| <a id="slot-calculationinvariant__test_kind"></a>**calculationInvariant__test_kind**<br/>The shape of the test: PROPERTY, EXAMPLE or METAMORPHIC. | <sub>1..1</sub><br/>[TestKind](#testkind) |  |
| <a id="slot-changes"></a>**changes**<br/>The change log, one entry per version. | <sub>0..\*</sub><br/>[ContractChange](#contractchange) | [MetricContract](#metriccontract) |
| <a id="slot-column__data_type"></a>**column__data_type**<br/>Physical type of the target platform (for example NUMBER(18,4)). | <sub>1..1</sub><br/>string |  |
| <a id="slot-column__description"></a>**column__description**<br/>Optional note on the column. | <sub>0..1</sub><br/>string |  |
| <a id="slot-column__name"></a>**column__name**<br/>Column name, in lower case here; Snowflake stores it in upper case. | <sub>1..1</sub><br/>string |  |
| <a id="slot-column__nullable"></a>**column__nullable**<br/>Whether the column may hold NULL. Declared, not read by the compiler: missing values are checked by COMPLETENESS quality expectations. **Documentation only.** | <sub>0..1</sub><br/>boolean |  |
| <a id="slot-contractchange__date"></a>**contractChange__date**<br/>The date the version was made (YYYY-MM-DD). | <sub>1..1</sub><br/>date |  |
| <a id="slot-contractchange__summary"></a>**contractChange__summary**<br/>What changed and why, and whether a rule changed or only its wording. | <sub>1..1</sub><br/>string |  |
| <a id="slot-contractchange__version"></a>**contractChange__version**<br/>The contract version this entry records, for example 0.5.1. | <sub>1..1</sub><br/>string |  |
| <a id="slot-defaultscope__applies_to_measures"></a>**defaultScope__applies_to_measures**<br/>The measures whose rows the scope restricts, inside the metrics of applies_to_metrics only. | <sub>1..\*</sub><br/>[Measure](#measure) |  |
| <a id="slot-defaultscope__applies_to_metrics"></a>**defaultScope__applies_to_metrics**<br/>The metrics whose computation applies the scope. Outside them (for example the snapshot measure's period aggregation, closing stock), the scope does not apply. | <sub>1..\*</sub><br/>[DepletionMetric](#depletionmetric) |  |
| <a id="slot-defaultscope__attribute"></a>**defaultScope__attribute**<br/>The attribute restricted by default (item_type). | <sub>1..1</sub><br/>[Attribute](#attribute) |  |
| <a id="slot-defaultscope__included_values"></a>**defaultScope__included_values**<br/>The values kept unless the caller filters the attribute (STANDARD). | <sub>1..\*</sub><br/>string |  |
| <a id="slot-defaultscope__lifted_by"></a>**defaultScope__lifted_by**<br/>EXPLICIT_FILTER: a filter on the same attribute lifts the scope; grouping by it does not. Declared, not read by the compiler: the procedure implements it. **Fixed: only EXPLICIT_FILTER is supported by this compiler.** | <sub>1..1</sub><br/>[ScopeLift](#scopelift) |  |
| <a id="slot-defaultscope__warning"></a>**defaultScope__warning**<br/>The warning raised with the amount the scope removed, per analysis month and unit (DEFAULT_SCOPE_EXCLUDED). | <sub>1..1</sub><br/>[WarningCode](#warningcode) |  |
| <a id="slot-default_scopes"></a>**default_scopes**<br/>Restrictions applied unless the caller lifts them. The procedure reads the first entry and needs one. | <sub>0..\*</sub><br/>[DefaultScope](#defaultscope) | [MetricContract](#metriccontract) |
| <a id="slot-depletionmetric__aggregate_before_compute"></a>**depletionMetric__aggregate_before_compute**<br/>True: stock and flow are summed to the requested grain before the algorithm runs, never computed per item and averaged (trap T1). Declared, not read by the compiler: the procedure implements it. **Fixed: only true is supported by this compiler.** | <sub>1..1</sub><br/>boolean |  |
| <a id="slot-depletionmetric__anchor_parameter"></a>**depletionMetric__anchor_parameter**<br/>The parameter that selects the analysis month (as_of_months). Read by the tests; the procedure's argument names are fixed in the compiler. **Fixed: only as_of_months is supported by this compiler.** | <sub>1..1</sub><br/>[Parameter](#parameter) |  |
| <a id="slot-depletionmetric__beyond_horizon"></a>**depletionMetric__beyond_horizon**<br/>The rule for a level that outlasts the horizon. | <sub>1..1</sub><br/>[BeyondHorizonRule](#beyondhorizonrule) |  |
| <a id="slot-depletionmetric__densify_missing_periods"></a>**depletionMetric__densify_missing_periods**<br/>True: a period with no flow row counts as zero, never as a skipped row (trap T2). Declared, not read by the compiler: the procedure crosses every member with every month of the window. **Fixed: only true is supported by this compiler.** | <sub>1..1</sub><br/>boolean |  |
| <a id="slot-depletionmetric__exhaustion_period"></a>**depletionMetric__exhaustion_period**<br/>The period in which a member's snapshot runs out, carried by each result row. | <sub>0..1</sub><br/>[ExhaustionPeriodRule](#exhaustionperiodrule) |  |
| <a id="slot-depletionmetric__flow_measure"></a>**depletionMetric__flow_measure**<br/>The amount that drains it (demand forecast), summed over the forward window. | <sub>1..1</sub><br/>[Measure](#measure) |  |
| <a id="slot-depletionmetric__horizon_periods"></a>**depletionMetric__horizon_periods**<br/>Length H of the forward window, in periods (24): the flow of t+1 to t+24 is read. A month is a valid analysis month only when the calendar and the forecast reach it plus H. | <sub>1..1</sub><br/>integer |  |
| <a id="slot-depletionmetric__interpolation"></a>**depletionMetric__interpolation**<br/>LINEAR: in the month the stock runs out, the fraction of that month's flow it covers is added. Declared, not read by the compiler: the procedure's SQL implements LINEAR. **Fixed: only LINEAR is supported by this compiler.** | <sub>1..1</sub><br/>[Interpolation](#interpolation) |  |
| <a id="slot-depletionmetric__member_selection"></a>**depletionMetric__member_selection**<br/>How a caller keeps some members by their result (a window, the first n), and what comes back apart. | <sub>0..1</sub><br/>[MemberSelection](#memberselection) |  |
| <a id="slot-depletionmetric__outcomes"></a>**depletionMetric__outcomes**<br/>The outcomes, evaluated in order; the first matching condition decides the value and the flag. The procedure reads each outcome's flag; the value rules are written in its SQL in this order. **Fixed: only the four outcomes SNAPSHOT_NULL_OR_ZERO (0, member kept), DEPLETED_WITHIN_HORIZON (linear), NO_FLOW_IN_WINDOW (null, member kept), BEYOND_HORIZON (mean non-zero flow), in this order is supported by this compiler.** | <sub>1..\*</sub><br/>[DepletionOutcome](#depletionoutcome) |  |
| <a id="slot-depletionmetric__output_unit"></a>**depletionMetric__output_unit**<br/>The unit of the result (months), the same on every basis. **Fixed: only months is supported by this compiler.** | <sub>1..1</sub><br/>string |  |
| <a id="slot-depletionmetric__reference_cases"></a>**depletionMetric__reference_cases**<br/>Path of the algorithm check that pins the formula on worked cases. | <sub>0..1</sub><br/>string |  |
| <a id="slot-depletionmetric__reference_sql"></a>**depletionMetric__reference_sql**<br/>Path of the reference SQL the generated procedure must match. | <sub>0..1</sub><br/>string |  |
| <a id="slot-depletionmetric__snapshot_measure"></a>**depletionMetric__snapshot_measure**<br/>The level that is drained (stock on hand), read at the analysis month. | <sub>1..1</sub><br/>[Measure](#measure) |  |
| <a id="slot-depletionmetric__time_filter_on_flow"></a>**depletionMetric__time_filter_on_flow**<br/>SELECTS_ANCHOR_ONLY: the month asked selects the snapshot, and the flow window stays relative to it, never cut by the filter (trap T4). Declared, not read by the compiler: the procedure implements it. **Fixed: only SELECTS_ANCHOR_ONLY is supported by this compiler.** | <sub>1..1</sub><br/>[TimeFilterRule](#timefilterrule) |  |
| <a id="slot-depletionmetric__time_grain"></a>**depletionMetric__time_grain**<br/>The period of the anchor and of the window (MONTH). Declared, not read by the compiler: the generated SQL is monthly. **Fixed: only MONTH is supported by this compiler.** | <sub>1..1</sub><br/>[TimeGrain](#timegrain) |  |
| <a id="slot-depletionmetric__window_start_offset"></a>**depletionMetric__window_start_offset**<br/>First flow period counted, relative to the analysis month: 1 means the window starts the month after the analysis month, so the analysis month's own forecast never counts (trap T4). | <sub>1..1</sub><br/>integer |  |
| <a id="slot-depletionoutcome__condition"></a>**depletionOutcome__condition**<br/>The condition tested. The procedure maps each condition to its flag. | <sub>1..1</sub><br/>[DepletionCondition](#depletioncondition) |  |
| <a id="slot-depletionoutcome__flag"></a>**depletionOutcome__flag**<br/>The flag set on the row (NO_STOCK, NO_DEMAND); the procedure writes this code into the row's flag. | <sub>0..1</sub><br/>[Flag](#flag) |  |
| <a id="slot-depletionoutcome__keeps_member"></a>**depletionOutcome__keeps_member**<br/>True when the member keeps its row although a measure is absent. | <sub>0..1</sub><br/>boolean |  |
| <a id="slot-depletionoutcome__order"></a>**depletionOutcome__order**<br/>Evaluation order, from 1; the first matching condition wins. Checked by the tests; the procedure's SQL evaluates the conditions in this order. | <sub>1..1</sub><br/>integer |  |
| <a id="slot-depletionoutcome__prevents"></a>**depletionOutcome__prevents**<br/>Failure modes this outcome prevents. | <sub>0..\*</sub><br/>[FailureMode](#failuremode) |  |
| <a id="slot-depletionoutcome__result"></a>**depletionOutcome__result**<br/>The value returned, as a formula over the pattern's symbols. | <sub>1..1</sub><br/>string |  |
| <a id="slot-dimensionclass__is_time"></a>**dimensionClass__is_time**<br/>True for the class that carries calendar time. | <sub>0..1</sub><br/>boolean |  |
| <a id="slot-dimension_classes"></a>**dimension_classes**<br/>The classes along which additivity is declared (time, product, geography). | <sub>0..\*</sub><br/>[DimensionClass](#dimensionclass) | [MetricContract](#metriccontract) |
| <a id="slot-effective_date"></a>**effective_date**<br/>The date from which the version applies. | <sub>0..1</sub><br/>date | [MetricContract](#metriccontract) |
| <a id="slot-evidence"></a>**evidence**<br/>How the element is known (documented, measured here, inferred). | <sub>0..1</sub><br/>[EvidenceTag](#evidencetag) | [OpenDecision](#opendecision), [RefusalCode](#refusalcode) |
| <a id="slot-exhaustionperiodrule__formula"></a>**exhaustionPeriodRule__formula**<br/>The period, as a formula over the anchor and the result: t + ceil(coverage) months, so 0.5 and 1.0 from June both give July. The procedure's SQL implements it. **Documentation only.** | <sub>1..1</sub><br/>string |  |
| <a id="slot-exhaustionperiodrule__none_for_flags"></a>**exhaustionPeriodRule__none_for_flags**<br/>Flags for which no period is given (NO_DEMAND, BEYOND_HORIZON): the row's stockout_month is null. The procedure reads them. | <sub>0..\*</sub><br/>[Flag](#flag) |  |
| <a id="slot-failuremode__correct_behaviour"></a>**failureMode__correct_behaviour**<br/>What a correct implementation does. | <sub>1..1</sub><br/>string |  |
| <a id="slot-failuremode__reference_question"></a>**failureMode__reference_question**<br/>A natural-language question that exercises the trap; compiler/gen_questions.py turns it into a campaign question. | <sub>0..1</sub><br/>string |  |
| <a id="slot-failuremode__source"></a>**failureMode__source**<br/>Where the trap is defined (file and section). | <sub>1..1</sub><br/>string |  |
| <a id="slot-failuremode__wrong_behaviour"></a>**failureMode__wrong_behaviour**<br/>What a wrong implementation does, in words; the trap in data/traps.yaml declares the value it returns. | <sub>1..1</sub><br/>string |  |
| <a id="slot-failure_modes"></a>**failure_modes**<br/>The traps: known ways to get the metric wrong, each with its wrong and correct behaviour. | <sub>0..\*</sub><br/>[FailureMode](#failuremode) | [MetricContract](#metriccontract) |
| <a id="slot-flag__value_semantics"></a>**flag__value_semantics**<br/>What the number means when this flag is set. Written into the agent's tool description. | <sub>1..1</sub><br/>string |  |
| <a id="slot-flags"></a>**flags**<br/>Codes on a result row that change how its number reads. | <sub>0..\*</sub><br/>[Flag](#flag) | [MetricContract](#metriccontract) |
| <a id="slot-invariants"></a>**invariants**<br/>Properties every correct result satisfies; several are tested against the deployed procedure. | <sub>0..\*</sub><br/>[CalculationInvariant](#calculationinvariant) | [MetricContract](#metriccontract) |
| <a id="slot-itemdimension__base_unit"></a>**itemDimension__base_unit**<br/>The unit of the quantity equivalent in this dimension (kg, L). | <sub>1..1</sub><br/>string |  |
| <a id="slot-measureapplicability__effect"></a>**measureApplicability__effect**<br/>GROUP_AND_FILTER, IGNORED or REFUSED. The tests check that it agrees with the attribute's applicability_class; the closing view exposes the attributes that GROUP_AND_FILTER the snapshot. | <sub>1..1</sub><br/>[ApplicabilityEffect](#applicabilityeffect) |  |
| <a id="slot-measureapplicability__measure"></a>**measureApplicability__measure**<br/>The measure. | <sub>1..1</sub><br/>[Measure](#measure) |  |
| <a id="slot-measurebasis__kind"></a>**measureBasis__kind**<br/>NATIVE_UNIT, BASE_UNIT_EQUIVALENT or MONETARY: what the basis measures. Declared, not read by the compiler: the procedure reads valid_when and unit_source. **Documentation only.** | <sub>1..1</sub><br/>[BasisKind](#basiskind) |  |
| <a id="slot-measurebasis__not_comparable_reason"></a>**measureBasis__not_comparable_reason**<br/>Why a row or a total breaks valid_when, in business words, for the refusal reason. | <sub>1..1</sub><br/>string |  |
| <a id="slot-measurebasis__unit_source"></a>**measureBasis__unit_source**<br/>Where the unit of a figure on this basis comes from (the item, its dimension, or a fixed symbol). | <sub>1..1</sub><br/>[BasisUnitSource](#basisunitsource) |  |
| <a id="slot-measurebasis__unit_symbol"></a>**measureBasis__unit_symbol**<br/>The unit shown for every figure on this basis when unit_source is FIXED (EUR). | <sub>0..1</sub><br/>string |  |
| <a id="slot-measurebasis__valid_when"></a>**measureBasis__valid_when**<br/>Where the basis stays comparable: ONE_ITEM_PER_ROW, ONE_DIMENSION_PER_ROW or ALWAYS. The procedure counts the items and the dimensions behind every returned row and total, and refuses with BASIS_NOT_COMPARABLE where the rule breaks. | <sub>1..1</sub><br/>[BasisValidity](#basisvalidity) |  |
| <a id="slot-measurecolumn__basis"></a>**measureColumn__basis**<br/>The measure basis (QTY_EQ, VALUE, NATIVE). | <sub>1..1</sub><br/>[MeasureBasis](#measurebasis) |  |
| <a id="slot-measurecolumn__column"></a>**measureColumn__column**<br/>The column that holds the measure on that basis; the procedure reads it when the caller asks for that basis. | <sub>1..1</sub><br/>string |  |
| <a id="slot-measure__additivity"></a>**measure__additivity**<br/>One entry per dimension class. A class not listed is not additive. | <sub>1..\*</sub><br/>[Additivity](#additivity) |  |
| <a id="slot-measure__columns"></a>**measure__columns**<br/>The physical column of this measure on each measure basis. | <sub>1..\*</sub><br/>[MeasureColumn](#measurecolumn) |  |
| <a id="slot-measure__measure_type"></a>**measure__measure_type**<br/>SNAPSHOT (a level read at one period) or FLOW (an amount per period, summed over a window). The tests check that the additivity agrees with it; the compiler takes each measure's role from the metric (snapshot_measure, flow_measure). | <sub>1..1</sub><br/>[MeasureType](#measuretype) |  |
| <a id="slot-measure__period_aggregation"></a>**measure__period_aggregation**<br/>How the measure reads over a period longer than its time grain. Required for a SNAPSHOT measure (a level is never summed over time); a FLOW measure sums over the period and declares none. | <sub>0..1</sub><br/>[PeriodAggregation](#periodaggregation) |  |
| <a id="slot-measure__table"></a>**measure__table**<br/>The fact table that holds the measure. | <sub>1..1</sub><br/>[Table](#table) |  |
| <a id="slot-measure__time_column"></a>**measure__time_column**<br/>Column of the table that carries the period. The procedure reads the snapshot at exactly the analysis month, and the flow over the forward window, each on its own time column. | <sub>1..1</sub><br/>string |  |
| <a id="slot-measure__time_grain"></a>**measure__time_grain**<br/>The period of one row (MONTH here). Declared, not read by the compiler: the generated SQL counts months. **Fixed: only MONTH is supported by this compiler.** | <sub>1..1</sub><br/>[TimeGrain](#timegrain) |  |
| <a id="slot-measure_bases"></a>**measure_bases**<br/>The bases on which the measures are compared before the ratio. | <sub>0..\*</sub><br/>[MeasureBasis](#measurebasis) | [MetricContract](#metriccontract) |
| <a id="slot-measures"></a>**measures**<br/>The numeric facts; a depletion metric has a snapshot and a flow. | <sub>0..\*</sub><br/>[Measure](#measure) | [MetricContract](#metriccontract) |
| <a id="slot-memberselection__grain_rule"></a>**memberSelection__grain_rule**<br/>Which grain a question takes: a list question takes items, a question for one figure takes its scope's grain (metamodel 0.4.1). Given verbatim to every configuration. | <sub>0..1</sub><br/>string |  |
| <a id="slot-memberselection__lower_bound_parameter"></a>**memberSelection__lower_bound_parameter**<br/>The parameter that keeps the members above N periods (coverage_above): result > N. With the upper bound, a window. | <sub>1..1</sub><br/>[Parameter](#parameter) |  |
| <a id="slot-memberselection__lower_bound_rule"></a>**memberSelection__lower_bound_rule**<br/>The rows kept by the lower bound, as a condition. The procedure's SQL implements it. **Documentation only.** | <sub>1..1</sub><br/>string |  |
| <a id="slot-memberselection__rank_parameter"></a>**memberSelection__rank_parameter**<br/>The parameter that keeps the first n members by result, lowest first (rank_first), per analysis month. | <sub>1..1</sub><br/>[Parameter](#parameter) |  |
| <a id="slot-memberselection__rank_rule"></a>**memberSelection__rank_rule**<br/>The order of the rows and how ties are broken (by the grain codes, in grain order). The procedure's SQL implements it. **Documentation only.** | <sub>1..1</sub><br/>string |  |
| <a id="slot-memberselection__set_apart_flags"></a>**memberSelection__set_apart_flags**<br/>Flags whose members never mix with the kept rows (NO_STOCK, NO_DEMAND): the procedure returns them apart, counted and named. | <sub>1..\*</sub><br/>[Flag](#flag) |  |
| <a id="slot-memberselection__summary_rule"></a>**memberSelection__summary_rule**<br/>What the summary of the kept rows gives. The summary is a total: it follows the basis rule (a snapshot sum per comparable unit, never across units) and never sums or averages the metric's result. **Documentation only.** | <sub>1..1</sub><br/>string |  |
| <a id="slot-memberselection__upper_bound_parameter"></a>**memberSelection__upper_bound_parameter**<br/>The parameter that keeps the members running out within N periods (coverage_below): 0 < result <= N. | <sub>1..1</sub><br/>[Parameter](#parameter) |  |
| <a id="slot-memberselection__upper_bound_rule"></a>**memberSelection__upper_bound_rule**<br/>The rows kept by the upper bound, as a condition. The procedure's SQL implements it. **Documentation only.** | <sub>1..1</sub><br/>string |  |
| <a id="slot-membersetrule__flow_members"></a>**memberSetRule__flow_members**<br/>When the flow contributes members. ONLY_ON_CONFORMED_GRAIN: a forecast creates a row only when the grain holds no snapshot-only attribute. The procedure reads it. | <sub>1..1</sub><br/>[MemberSource](#membersource) |  |
| <a id="slot-membersetrule__method"></a>**memberSetRule__method**<br/>SPINE: members are the union of the snapshot's and the flow's members, then both measures are left-joined. Declared, not read by the compiler: the procedure implements it. **Fixed: only SPINE is supported by this compiler.** | <sub>1..1</sub><br/>[MemberSetMethod](#membersetmethod) |  |
| <a id="slot-membersetrule__snapshot_members"></a>**memberSetRule__snapshot_members**<br/>When the snapshot contributes members (ALWAYS). Declared, not read by the compiler: the procedure implements it. **Fixed: only ALWAYS is supported by this compiler.** | <sub>1..1</sub><br/>[MemberSource](#membersource) |  |
| <a id="slot-member_set_rules"></a>**member_set_rules**<br/>Which members an answer contains; the compiler reads the first entry. | <sub>0..\*</sub><br/>[MemberSetRule](#membersetrule) | [MetricContract](#metriccontract) |
| <a id="slot-metrics"></a>**metrics**<br/>The metrics of the contract. DepletionMetric is the only pattern; the compiler reads the first entry. | <sub>0..\*</sub><br/>[DepletionMetric](#depletionmetric) | [MetricContract](#metriccontract) |
| <a id="slot-opendecision__blocking"></a>**openDecision__blocking**<br/>True when a release must wait for the owner's decision. Declared, not read by the compiler. **Documentation only.** | <sub>0..1</sub><br/>boolean |  |
| <a id="slot-opendecision__current_choice"></a>**openDecision__current_choice**<br/>The choice the contract applies today, until the owner confirms or changes it. | <sub>1..1</sub><br/>string |  |
| <a id="slot-open_decisions"></a>**open_decisions**<br/>Choices the owner has not confirmed yet. | <sub>0..\*</sub><br/>[OpenDecision](#opendecision) | [MetricContract](#metriccontract) |
| <a id="slot-ownership"></a>**ownership**<br/>Who answers for the contract, by role. | <sub>0..1</sub><br/>[Ownership](#ownership) | [MetricContract](#metriccontract) |
| <a id="slot-ownership__business_owner"></a>**ownership__business_owner**<br/>Role accountable for the business meaning: the definition, the refusals and the traps. A role, never a person's name. | <sub>1..1</sub><br/>string |  |
| <a id="slot-ownership__data_steward"></a>**ownership__data_steward**<br/>Role accountable for the data-quality expectations. | <sub>0..1</sub><br/>string |  |
| <a id="slot-ownership__review_cadence"></a>**ownership__review_cadence**<br/>When the contract is reviewed, for example at every change of a rule and before each release. | <sub>0..1</sub><br/>string |  |
| <a id="slot-ownership__technical_owner"></a>**ownership__technical_owner**<br/>Role accountable for the generated objects and their deployment. A role, never a person's name. | <sub>1..1</sub><br/>string |  |
| <a id="slot-parameter__allowed_values"></a>**parameter__allowed_values**<br/>The values accepted, for an ENUM. Declared, not read by the compiler: the procedure accepts a basis by its id or one of its synonyms (measure_bases). **Fixed: only the ids of measure_bases, in order is supported by this compiler.** | <sub>0..\*</sub><br/>string |  |
| <a id="slot-parameter__data_type"></a>**parameter__data_type**<br/>The parameter's kind. The procedure parses the NUMBER and INTEGER selection parameters by it. | <sub>1..1</sub><br/>[ParameterType](#parametertype) |  |
| <a id="slot-parameter__default_value"></a>**parameter__default_value**<br/>Used when the caller passes nothing: the argument's DEFAULT in the procedure, and stated in the tool description. | <sub>0..1</sub><br/>string |  |
| <a id="slot-parameter__encoding"></a>**parameter__encoding**<br/>PLAIN or JSON_STRING; the tool description says that a JSON value is passed as a string. | <sub>1..1</sub><br/>[ParameterEncoding](#parameterencoding) |  |
| <a id="slot-parameter__example"></a>**parameter__example**<br/>An example value, written into the tool description and the procedure's header. | <sub>0..1</sub><br/>string |  |
| <a id="slot-parameter__exclusive_minimum"></a>**parameter__exclusive_minimum**<br/>A NUMBER or INTEGER parameter must be greater than this (0 here); the procedure refuses 0 or less with SELECTION_INVALID. | <sub>0..1</sub><br/>float |  |
| <a id="slot-parameter__is_required"></a>**parameter__is_required**<br/>Required parameters come first in the procedure's signature and form the tool's required list. | <sub>1..1</sub><br/>boolean |  |
| <a id="slot-parameter__json_shape"></a>**parameter__json_shape**<br/>JSON shape when encoding is JSON_STRING, for example array of string. | <sub>0..1</sub><br/>string |  |
| <a id="slot-parameter__max_items"></a>**parameter__max_items**<br/>The most items in a list. Declared, not read by the compiler: the cap on analysis months comes from analysis_periods.max_periods. **Fixed: only the analysis periods' max_periods is supported by this compiler.** | <sub>0..1</sub><br/>integer |  |
| <a id="slot-parameter__min_items"></a>**parameter__min_items**<br/>The fewest items in a list. Declared, not read by the compiler: an empty list has its own refusal (AS_OF_MISSING, GRAIN_EMPTY). **Fixed: only 1 is supported by this compiler.** | <sub>0..1</sub><br/>integer |  |
| <a id="slot-parameter__refusal_codes"></a>**parameter__refusal_codes**<br/>The refusal codes this parameter can raise; the tests check that each one exists. | <sub>0..\*</sub><br/>[RefusalCode](#refusalcode) |  |
| <a id="slot-parameters"></a>**parameters**<br/>The tool's parameters. Each is one VARCHAR argument of the procedure and one string property of the tool. | <sub>0..\*</sub><br/>[Parameter](#parameter) | [MetricContract](#metriccontract) |
| <a id="slot-periodaggregation__forbidden_methods"></a>**periodAggregation__forbidden_methods**<br/>Methods a consumer must never apply over the period. Each one is a known wrong behaviour. | <sub>1..\*</sub><br/>[PeriodAggregationMethod](#periodaggregationmethod) |  |
| <a id="slot-periodaggregation__member_set"></a>**periodAggregation__member_set**<br/>Which members a period has. Declared, not read by the compiler: the gap-filled view implements ANY_SNAPSHOT_IN_PERIOD by giving each key a row from its first snapshot month to the month after its last. **Fixed: only ANY_SNAPSHOT_IN_PERIOD is supported by this compiler.** | <sub>1..1</sub><br/>[PeriodMemberSet](#periodmemberset) |  |
| <a id="slot-periodaggregation__method"></a>**periodAggregation__method**<br/>How the snapshot reads over a period. The closing view supports LAST_PERIOD only: gen_closing_sv.py stops on any other method. | <sub>1..1</sub><br/>[PeriodAggregationMethod](#periodaggregationmethod) |  |
| <a id="slot-periodaggregation__missing_value"></a>**periodAggregation__missing_value**<br/>Value of a member of the period with no row in the selected snapshot (0 here). The gap-filled view writes it into every measure column where the key has no row; the member keeps its row. | <sub>1..1</sub><br/>string |  |
| <a id="slot-periodaggregation__periods"></a>**periodAggregation__periods**<br/>Periods the rule applies to. Each becomes a dimension of the closing view: PERIOD_RANGE a range of months, QUARTER the year and quarter, YEAR the year. | <sub>1..\*</sub><br/>[PeriodKind](#periodkind) |  |
| <a id="slot-prevents"></a>**prevents**<br/>Failure modes this element prevents or detects. A failure mode that nothing prevents fails tests/test_contract.py. | <sub>0..\*</sub><br/>[FailureMode](#failuremode) | [AnalysisPeriods](#analysisperiods), [Attribute](#attribute), [BasisModel](#basismodel), [BeyondHorizonRule](#beyondhorizonrule), [CalculationInvariant](#calculationinvariant), [DefaultScope](#defaultscope), [DepletionMetric](#depletionmetric), [DepletionOutcome](#depletionoutcome), [MeasureBasis](#measurebasis), [MemberSelection](#memberselection), [MemberSetRule](#membersetrule), [PeriodAggregation](#periodaggregation), [QualityExpectation](#qualityexpectation), [RefusalCode](#refusalcode), [TotalsRule](#totalsrule) |
| <a id="slot-qualityexpectation__call_scope"></a>**qualityExpectation__call_scope**<br/>Rows the procedure checks again at call time. Required unless on_failure is MONITOR. A count over the whole table would warn on every answer; a check scoped to the request warns only when the answer reads the rows. | <sub>0..1</sub><br/>[CallScope](#callscope) |  |
| <a id="slot-qualityexpectation__columns"></a>**qualityExpectation__columns**<br/>The columns checked. For COMPLETENESS and FRESHNESS the time column comes first; a system data metric function is called once per column. | <sub>0..\*</sub><br/>string |  |
| <a id="slot-qualityexpectation__condition"></a>**qualityExpectation__condition**<br/>The condition, in words or as a SQL predicate. | <sub>1..1</sub><br/>string |  |
| <a id="slot-qualityexpectation__dmf"></a>**qualityExpectation__dmf**<br/>A system data metric function (SNOWFLAKE.CORE.DUPLICATE_COUNT, NULL_COUNT, NEGATIVE_COUNT, FRESHNESS), or CUSTOM: gen_dmf.py then writes one from the kind. | <sub>1..1</sub><br/>string |  |
| <a id="slot-qualityexpectation__kind"></a>**qualityExpectation__kind**<br/>The kind of check; it picks the SQL template of the data metric function and of the in-call check. | <sub>1..1</sub><br/>[QualityKind](#qualitykind) |  |
| <a id="slot-qualityexpectation__on_failure"></a>**qualityExpectation__on_failure**<br/>What a failure does: REFUSE every query, REFUSE_IF_USED a query that uses the affected columns, WARN in the answer, or MONITOR (data metric function only). | <sub>1..1</sub><br/>[FailureAction](#failureaction) |  |
| <a id="slot-qualityexpectation__references_columns"></a>**qualityExpectation__references_columns**<br/>Its matching columns, in the order of columns. | <sub>0..\*</sub><br/>string |  |
| <a id="slot-qualityexpectation__references_table"></a>**qualityExpectation__references_table**<br/>For a check across tables (REFERENTIAL, some CARDINALITY): the table that must hold a match. | <sub>0..1</sub><br/>[Table](#table) |  |
| <a id="slot-qualityexpectation__refusal"></a>**qualityExpectation__refusal**<br/>The refusal raised when the check fails in a call (REFUSE, REFUSE_IF_USED). | <sub>0..1</sub><br/>[RefusalCode](#refusalcode) |  |
| <a id="slot-qualityexpectation__schedule"></a>**qualityExpectation__schedule**<br/>When the data metric function would run. Declared, not read by the compiler: generated/dmf.sql attaches nothing to a table and sets no schedule. **Fixed: only no schedule is supported by this compiler.** | <sub>0..1</sub><br/>string |  |
| <a id="slot-qualityexpectation__severity"></a>**qualityExpectation__severity**<br/>ERROR, WARNING or INFO: a reading aid. What a failure does is set by on_failure. | <sub>1..1</sub><br/>[Severity](#severity) |  |
| <a id="slot-qualityexpectation__table"></a>**qualityExpectation__table**<br/>The table checked. | <sub>1..1</sub><br/>[Table](#table) |  |
| <a id="slot-qualityexpectation__threshold"></a>**qualityExpectation__threshold**<br/>The accepted violation count (0 here). TBD means no threshold yet: a FRESHNESS check with TBD is not run in the call. | <sub>1..1</sub><br/>string |  |
| <a id="slot-qualityexpectation__warning"></a>**qualityExpectation__warning**<br/>The warning raised when the check fails in a call (WARN, REFUSE_IF_USED). | <sub>0..1</sub><br/>[WarningCode](#warningcode) |  |
| <a id="slot-quality_expectations"></a>**quality_expectations**<br/>Conditions on the data: compiled to data metric functions, and checked again in the call unless MONITOR. | <sub>0..\*</sub><br/>[QualityExpectation](#qualityexpectation) | [MetricContract](#metriccontract) |
| <a id="slot-refusalcode__category"></a>**refusalCode__category**<br/>PARAMETER, SEMANTIC, DATA_QUALITY or AVAILABILITY: a reading aid, not read by the compiler. | <sub>1..1</sub><br/>[RefusalCategory](#refusalcategory) |  |
| <a id="slot-refusalcode__check_order"></a>**refusalCode__check_order**<br/>Validation order: lower checks run first and the first that fails ends the call. The generator fails when the order breaks a check's prerequisite. | <sub>0..1</sub><br/>integer |  |
| <a id="slot-refusalcode__reason_template"></a>**refusalCode__reason_template**<br/>The reason returned with the code; the procedure fills the {placeholders} (the value given, the months available, the attributes allowed). | <sub>1..1</sub><br/>string |  |
| <a id="slot-refusal_codes"></a>**refusal_codes**<br/>The refusals, in check order. Each must have a check in the procedure, or the generator fails. | <sub>0..\*</sub><br/>[RefusalCode](#refusalcode) | [MetricContract](#metriccontract), [Parameter](#parameter) |
| <a id="slot-relationship__cardinality"></a>**relationship__cardinality**<br/>The declared cardinality. The procedure and the closing view join only MANY_TO_ONE relationships from a fact; whether the key is really unique is checked by a GRAIN_UNIQUENESS quality expectation. | <sub>1..1</sub><br/>[Cardinality](#cardinality) |  |
| <a id="slot-relationship__from_columns"></a>**relationship__from_columns**<br/>Its key columns, in the order of to_columns. | <sub>1..\*</sub><br/>string |  |
| <a id="slot-relationship__from_table"></a>**relationship__from_table**<br/>The table that holds the foreign key, usually a fact. | <sub>1..1</sub><br/>[Table](#table) |  |
| <a id="slot-relationship__to_columns"></a>**relationship__to_columns**<br/>The joined table's key columns. | <sub>1..\*</sub><br/>string |  |
| <a id="slot-relationship__to_table"></a>**relationship__to_table**<br/>The table joined to, usually a dimension. | <sub>1..1</sub><br/>[Table](#table) |  |
| <a id="slot-relationships"></a>**relationships**<br/>The join paths between the tables. | <sub>0..\*</sub><br/>[Relationship](#relationship) | [MetricContract](#metriccontract) |
| <a id="slot-status"></a>**status**<br/>DRAFT, ACTIVE or DEPRECATED. | <sub>0..1</sub><br/>[ContractStatus](#contractstatus) | [MetricContract](#metriccontract) |
| <a id="slot-synonyms"></a>**synonyms**<br/>Other words for the element. A metric's go into the tool description and B2's view; a basis's are accepted by the procedure as the basis parameter. | <sub>0..\*</sub><br/>string | [Attribute](#attribute), [DepletionMetric](#depletionmetric), [MeasureBasis](#measurebasis) |
| <a id="slot-table__columns"></a>**table__columns**<br/>The physical columns in load order, with their Snowflake types. generated/schema.py lists them for the loader; the data metric functions take their types. | <sub>1..\*</sub><br/>[Column](#column) |  |
| <a id="slot-table__grain"></a>**table__grain**<br/>Columns whose values identify one row. Uniqueness is a quality expectation, not an assumption. The flow table's grain less its time column gives the members of the metric (item and country); the snapshot table's grain gives the keys of the gap-filled closing view. | <sub>1..\*</sub><br/>string |  |
| <a id="slot-table__kind"></a>**table__kind**<br/>FACT for a table of measures, DIMENSION for a table of attributes. Declared, not read by the compiler. **Documentation only.** | <sub>1..1</sub><br/>[TableKind](#tablekind) |  |
| <a id="slot-tables"></a>**tables**<br/>The physical tables the metric reads. | <sub>0..\*</sub><br/>[Table](#table) | [MetricContract](#metriccontract) |
| <a id="slot-totalsrule__flow_aggregation"></a>**totalsRule__flow_aggregation**<br/>How the flow reaches it (CONFORMED_PROJECTION: the total's grain less its snapshot-only attributes). Declared, not read by the compiler: the procedure implements it. **Fixed: only CONFORMED_PROJECTION is supported by this compiler.** | <sub>1..1</sub><br/>[TotalsProjection](#totalsprojection) |  |
| <a id="slot-totalsrule__method"></a>**totalsRule__method**<br/>RECOMPUTE: a total aggregates the inputs to its grain and runs the algorithm again. Declared, not read by the compiler: the procedure implements this one method. **Fixed: only RECOMPUTE is supported by this compiler.** | <sub>1..1</sub><br/>[TotalsMethod](#totalsmethod) |  |
| <a id="slot-totalsrule__parameter"></a>**totalsRule__parameter**<br/>The parameter through which a caller asks for totals (totals). | <sub>0..1</sub><br/>[Parameter](#parameter) |  |
| <a id="slot-totalsrule__snapshot_aggregation"></a>**totalsRule__snapshot_aggregation**<br/>How the snapshot reaches the total's grain (TOTAL_GRAIN). Declared, not read by the compiler: the procedure implements it. **Fixed: only TOTAL_GRAIN is supported by this compiler.** | <sub>1..1</sub><br/>[TotalsProjection](#totalsprojection) |  |
| <a id="slot-totalsrule__total_over_time"></a>**totalsRule__total_over_time**<br/>FORBIDDEN: several analysis months give a series, never a total across months. Declared, not read by the compiler: the procedure implements it. **Fixed: only FORBIDDEN is supported by this compiler.** | <sub>1..1</sub><br/>[TimeTotalRule](#timetotalrule) |  |
| <a id="slot-totals_rules"></a>**totals_rules**<br/>How totals are obtained; the compiler reads the first entry. | <sub>0..\*</sub><br/>[TotalsRule](#totalsrule) | [MetricContract](#metriccontract) |
| <a id="slot-version"></a>**version**<br/>The contract's version. Every generated file names it in its header, and the procedure returns it with each answer. | <sub>0..1</sub><br/>string | [ContractChange](#contractchange), [MetricContract](#metriccontract) |
| <a id="slot-warningcode__message_template"></a>**warningCode__message_template**<br/>The message attached to the answer; the procedure fills the {placeholders} (a count, an amount, a unit). | <sub>1..1</sub><br/>string |  |
| <a id="slot-warningcode__raised_by"></a>**warningCode__raised_by**<br/>Id of the rule or expectation that raises it. | <sub>1..1</sub><br/>string |  |
| <a id="slot-warning_codes"></a>**warning_codes**<br/>Messages attached to an answer that is still given. | <sub>0..\*</sub><br/>[WarningCode](#warningcode) | [MetricContract](#metriccontract) |

## Enums


### AggregationRule

How a measure aggregates along a dimension class.

| Text | Meaning: | Description |
| --- | --- | --- |
| NONE | None | Not aggregatable along this class. |
| SELECT_PERIOD | None | Not additive; one period is selected (the anchor), never summed. |
| SUM | None | Added up along the class. |
| SUM_OVER_WINDOW | None | Summed over a window defined by the metric pattern, not by a filter. |

#### Used by

 *  **[Additivity](#additivity)** *[additivity__aggregation](#slot-additivity__aggregation)*  <sub>1..1</sub> 

### ApplicabilityClass

How an attribute applies to the measures of a metric.

| Text | Meaning: | Description |
| --- | --- | --- |
| CONFORMED | None | Groups and filters every measure of the metric. |
| NOT_APPLICABLE | None | Cannot be used with the metric; the procedure refuses it. |
| SNAPSHOT_ONLY | None | Groups and filters the snapshot measure only; the flow stays at the parent conformed grain. Called stock-only in the stock coverage definition. |

#### Used by

 *  **[Attribute](#attribute)** *[attribute__applicability_class](#slot-attribute__applicability_class)*  <sub>1..1</sub> 

### ApplicabilityEffect

The effect of an attribute on one measure.

| Text | Meaning: | Description |
| --- | --- | --- |
| GROUP_AND_FILTER | None | The attribute groups and filters the measure. |
| IGNORED | None | The measure is neither grouped nor filtered by the attribute. |
| REFUSED | None | The attribute cannot be used with the measure; the procedure refuses it. |

#### Used by

 *  **[MeasureApplicability](#measureapplicability)** *[measureApplicability__effect](#slot-measureapplicability__effect)*  <sub>1..1</sub> 

### AverageWindow

The flow periods a mean covers.

| Text | Meaning: | Description |
| --- | --- | --- |
| FULL_RANGE | None | The mean is taken over every loaded flow period after the anchor. |
| HORIZON | None | The mean is taken over the horizon window only. |

#### Used by

 *  **[BeyondHorizonRule](#beyondhorizonrule)** *[beyondHorizonRule__average_window](#slot-beyondhorizonrule__average_window)*  <sub>1..1</sub> 

### BasisKind

What a measure basis measures.

| Text | Meaning: | Description |
| --- | --- | --- |
| BASE_UNIT_EQUIVALENT | None | The quantity in the base unit of the item's dimension (kg, L). |
| MONETARY | None | A value in one currency. Comparable across every item. |
| NATIVE_UNIT | None | Each item in its own unit (how it is counted). Comparable within one item only. |

#### Used by

 *  **[MeasureBasis](#measurebasis)** *[measureBasis__kind](#slot-measurebasis__kind)*  <sub>1..1</sub> 

### BasisUnitSource

Where the unit of a figure on a basis comes from.

| Text | Meaning: | Description |
| --- | --- | --- |
| FIXED | None | The basis's unit_symbol. |
| ITEM_BASE_UNIT | None | The base unit of the item's dimension. |
| ITEM_NATIVE_UNIT | None | The item's own unit. |

#### Used by

 *  **[MeasureBasis](#measurebasis)** *[measureBasis__unit_source](#slot-measurebasis__unit_source)*  <sub>1..1</sub> 

### BasisValidity

Where a measure basis stays comparable.

| Text | Meaning: | Description |
| --- | --- | --- |
| ALWAYS | None | Comparable on every row and total. |
| ONE_DIMENSION_PER_ROW | None | Every returned row and total holds items of one dimension. |
| ONE_ITEM_PER_ROW | None | Every returned row and total holds one item. |

#### Used by

 *  **[MeasureBasis](#measurebasis)** *[measureBasis__valid_when](#slot-measurebasis__valid_when)*  <sub>1..1</sub> 

### BasisValidityScope

Where the validity of a basis is judged.

| Text | Meaning: | Description |
| --- | --- | --- |
| RETURNED_ROWS | None | Judged on the rows and the totals the call returns, after any member selection. A summary of kept rows is a total that is split by unit, or omitted, where its basis is not comparable; it never refuses the call. |

#### Used by

 *  **[BasisModel](#basismodel)** *[basisModel__validity_scope](#slot-basismodel__validity_scope)*  <sub>1..1</sub> 

### BeyondHorizonMethod

How a level that outlasts the horizon is valued.

| Text | Meaning: | Description |
| --- | --- | --- |
| CAP_AT_HORIZON | None | The result capped at H. Not implemented by the procedure. |
| SNAPSHOT_OVER_MEAN_FLOW | None | The level divided by the mean flow per period of the averaging window. |

#### Used by

 *  **[BeyondHorizonRule](#beyondhorizonrule)** *[beyondHorizonRule__method](#slot-beyondhorizonrule__method)*  <sub>1..1</sub> 

### CallScope

The rows the procedure checks again at call time.

| Text | Meaning: | Description |
| --- | --- | --- |
| REQUEST_MEMBERS | None | The members (keys) the request selects, through its conformed and snapshot filters. |
| REQUEST_ROWS | None | The fact rows the request reads: the snapshots of its analysis months and the flow of their horizons. |
| TABLE | None | The whole table: the condition holds for every query or for none. |

#### Used by

 *  **[QualityExpectation](#qualityexpectation)** *[qualityExpectation__call_scope](#slot-qualityexpectation__call_scope)*  <sub>0..1</sub> 

### Cardinality

How many rows of one table match one row of another.

| Text | Meaning: | Description |
| --- | --- | --- |
| MANY_TO_ONE | None | Many rows of from_table match one row of to_table (a fact to its dimension). The only cardinality the compiler joins on. |
| ONE_TO_MANY | None | One row matches many rows. |
| ONE_TO_ONE | None | One row matches one row. |

#### Used by

 *  **[Relationship](#relationship)** *[relationship__cardinality](#slot-relationship__cardinality)*  <sub>1..1</sub> 

### Comparison

The comparison of an alert threshold.

| Text | Meaning: | Description |
| --- | --- | --- |
| GE | None | Raised when the value is at or above the threshold. |
| GT | None | Raised when the value is above the threshold. |
| LE | None | Raised when the value is at or below the threshold. |
| LT | None | Raised when the value is below the threshold. |

#### Used by

 *  **[AlertThreshold](#alertthreshold)** *[alertThreshold__comparison](#slot-alertthreshold__comparison)*  <sub>1..1</sub> 

### ContractStatus

The life stage of a contract.

| Text | Meaning: | Description |
| --- | --- | --- |
| ACTIVE | None | In force: the generated objects are released from it. |
| DEPRECATED | None | Kept for history; no longer released. |
| DRAFT | None | Being written; it may change at any version. |

#### Used by

 *  **[MetricContract](#metriccontract)** *[status](#slot-status)*  <sub>0..1</sub> 

### DepletionCondition

The conditions of the depletion outcomes.

| Text | Meaning: | Description |
| --- | --- | --- |
| BEYOND_HORIZON | None | The level outlasts the H periods: valued by the beyond-horizon rule. |
| DEPLETED_WITHIN_HORIZON | None | The cumulative flow reaches the level within H periods: the interpolated count of periods. |
| NO_FLOW_IN_WINDOW | None | A level but no flow in the window: the result is null (NO_DEMAND). |
| SNAPSHOT_NULL_OR_ZERO | None | No level at the anchor: the result is 0 and the member keeps its row (NO_STOCK). |

#### Used by

 *  **[DepletionOutcome](#depletionoutcome)** *[depletionOutcome__condition](#slot-depletionoutcome__condition)*  <sub>1..1</sub> 

### EvidenceTag

How an element is known.

| Text | Meaning: | Description |
| --- | --- | --- |
| DECIDED | None | A decision of the contract owner. |
| DOCUMENTED | None | Platform documentation or release notes. |
| IMPLEMENTED | None | Present in a probe implementation but not exercised. |
| INFERRED | None | Reasoned from the other two, not run. |
| MEASURED | None | Run on the project account, evidence in the repository. |

#### Used by

 *  **[OpenDecision](#opendecision)** *[evidence](#slot-evidence)*  <sub>0..1</sub> 
 *  **[RefusalCode](#refusalcode)** *[evidence](#slot-evidence)*  <sub>0..1</sub> 

### ExposureTarget

Where the valid analysis periods are shown.

| Text | Meaning: | Description |
| --- | --- | --- |
| PROCEDURE_RESPONSE | None | Returned by the procedure with every answer and refusal. |
| REGISTRY | None | Queryable in the generated registry. |
| TOOL_DESCRIPTION | None | Written into the generated tool description at compile time. |

#### Used by

 *  **[AnalysisPeriods](#analysisperiods)** *[analysisPeriods__exposed_in](#slot-analysisperiods__exposed_in)*  <sub>1..\*</sub> 

### FailureAction

What a failed expectation does in a call.

| Text | Meaning: | Description |
| --- | --- | --- |
| MONITOR | None | Checked by the data metric function only. |
| REFUSE | None | The procedure refuses every query. |
| REFUSE_IF_USED | None | The procedure refuses a query that uses the affected columns, else warns. |
| WARN | None | The answer carries a warning. |

#### Used by

 *  **[QualityExpectation](#qualityexpectation)** *[qualityExpectation__on_failure](#slot-qualityexpectation__on_failure)*  <sub>1..1</sub> 

### Interpolation

How a fraction of a period is counted.

| Text | Meaning: | Description |
| --- | --- | --- |
| LINEAR | None | In the period the level runs out, add the fraction of that period's flow it covers: (n - 1) + (S - C(n-1)) / f(n). |
| NONE | None | Count whole periods only. |

#### Used by

 *  **[DepletionMetric](#depletionmetric)** *[depletionMetric__interpolation](#slot-depletionmetric__interpolation)*  <sub>1..1</sub> 

### MeasureType

Whether a measure is a level or an amount per period.

| Text | Meaning: | Description |
| --- | --- | --- |
| FLOW | None | An amount per period (sales, forecast, receipts). Summed over a time window. |
| SNAPSHOT | None | A level at a point in time (stock, balance). Never summed over time. |

#### Used by

 *  **[Measure](#measure)** *[measure__measure_type](#slot-measure__measure_type)*  <sub>1..1</sub> 

### MemberSetMethod

How the members of an answer are formed.

| Text | Meaning: | Description |
| --- | --- | --- |
| SPINE | None | Members are the union of the measures' members, then every measure is left-joined. |

#### Used by

 *  **[MemberSetRule](#membersetrule)** *[memberSetRule__method](#slot-membersetrule__method)*  <sub>1..1</sub> 

### MemberSource

When a measure contributes members.

| Text | Meaning: | Description |
| --- | --- | --- |
| ALWAYS | None | Contributes members on every grain. |
| NEVER | None | Never contributes members. |
| ONLY_ON_CONFORMED_GRAIN | None | Contributes members only when the grain holds no snapshot-only attribute. |

#### Used by

 *  **[MemberSetRule](#membersetrule)** *[memberSetRule__flow_members](#slot-membersetrule__flow_members)*  <sub>1..1</sub> 
 *  **[MemberSetRule](#membersetrule)** *[memberSetRule__snapshot_members](#slot-membersetrule__snapshot_members)*  <sub>1..1</sub> 

### ParameterEncoding

How a parameter's value is passed.

| Text | Meaning: | Description |
| --- | --- | --- |
| JSON_STRING | None | A JSON value passed as a string, parsed and validated by the procedure. |
| PLAIN | None | A plain string. |

#### Used by

 *  **[Parameter](#parameter)** *[parameter__encoding](#slot-parameter__encoding)*  <sub>1..1</sub> 

### ParameterType

The kind of a parameter.

| Text | Meaning: | Description |
| --- | --- | --- |
| ATTRIBUTE_LIST | None | A list of attribute ids. |
| ENUM | None | One value of allowed_values. |
| FILTER_MAP | None | A map from an attribute id to a list of values. |
| GRAIN_LIST | None | A list of attribute lists, for example [["country_code"], []] for a total by country and a grand total. |
| INTEGER | None | An integer, passed as a string and parsed by the procedure. |
| NUMBER | None | A number, passed as a string and parsed by the procedure. |
| PERIOD | None | One period. |
| PERIOD_LIST | None | A list of periods (YYYY-MM-01), or the latest token. |

#### Used by

 *  **[Parameter](#parameter)** *[parameter__data_type](#slot-parameter__data_type)*  <sub>1..1</sub> 

### PeriodAggregationMethod

How a snapshot measure reads over a period longer than its time grain.

| Text | Meaning: | Description |
| --- | --- | --- |
| AVERAGE | None | The snapshots of the period averaged over its time grains. |
| LAST_NON_EMPTY | None | Each member's latest snapshot inside the period: carries a value forward. |
| LAST_PERIOD | None | The snapshot of the period's last time grain (the closing level), for every member. |
| SUM | None | The snapshots of the period added up. |

#### Used by

 *  **[PeriodAggregation](#periodaggregation)** *[periodAggregation__forbidden_methods](#slot-periodaggregation__forbidden_methods)*  <sub>1..\*</sub> 
 *  **[PeriodAggregation](#periodaggregation)** *[periodAggregation__method](#slot-periodaggregation__method)*  <sub>1..1</sub> 

### PeriodKind

The kinds of period a period aggregation applies to.

| Text | Meaning: | Description |
| --- | --- | --- |
| PERIOD_RANGE | None | A contiguous range of the measure's time grain (for example April to June). |
| QUARTER | None | A calendar quarter (year_quarter in the closing view). |
| YEAR | None | A calendar year. |

#### Used by

 *  **[PeriodAggregation](#periodaggregation)** *[periodAggregation__periods](#slot-periodaggregation__periods)*  <sub>1..\*</sub> 

### PeriodMemberSet

Which members a period has.

| Text | Meaning: | Description |
| --- | --- | --- |
| ANY_SNAPSHOT_IN_PERIOD | None | A member with a snapshot in any time grain of the period is a member of the period. |

#### Used by

 *  **[PeriodAggregation](#periodaggregation)** *[periodAggregation__member_set](#slot-periodaggregation__member_set)*  <sub>1..1</sub> 

### QualityKind

The kind of a quality check; it picks the SQL template.

| Text | Meaning: | Description |
| --- | --- | --- |
| CARDINALITY | None | Each value determines the next column's value (each sku_code one family), or a denormalised key agrees with its source; counts the violations. |
| COMPLETENESS | None | No value missing, or for the flow no month missing in the horizon window; counts what is missing. |
| FRESHNESS | None | The data reaches far enough: the calendar or the flow reach the latest snapshot plus H, or the latest snapshot is recent. |
| GRAIN_UNIQUENESS | None | One row per declared grain; counts the rows beyond the first. |
| REFERENTIAL | None | Every key has a match in references_table; counts the orphan rows. |
| VALUE_RANGE | None | Values in range: not negative, among the known values, or a declared dimension; counts the violations. |

#### Used by

 *  **[QualityExpectation](#qualityexpectation)** *[qualityExpectation__kind](#slot-qualityexpectation__kind)*  <sub>1..1</sub> 

### RefusalCategory

A reading aid that groups the refusal codes.

| Text | Meaning: | Description |
| --- | --- | --- |
| AVAILABILITY | None | The data asked for is not loaded. |
| DATA_QUALITY | None | The data breaks an expectation the answer depends on. |
| PARAMETER | None | A malformed or invalid parameter. |
| SEMANTIC | None | A well-formed request the metric cannot answer correctly. |

#### Used by

 *  **[RefusalCode](#refusalcode)** *[refusalCode__category](#slot-refusalcode__category)*  <sub>1..1</sub> 

### ScopeLift

What lifts a default scope.

| Text | Meaning: | Description |
| --- | --- | --- |
| EXPLICIT_FILTER | None | Lifted only by a filter on the same attribute. |

#### Used by

 *  **[DefaultScope](#defaultscope)** *[defaultScope__lifted_by](#slot-defaultscope__lifted_by)*  <sub>1..1</sub> 

### Severity

How serious a failed expectation is.

| Text | Meaning: | Description |
| --- | --- | --- |
| ERROR | None | The metric's promise breaks. |
| INFO | None | For the record only. |
| WARNING | None | The answer holds but the data is imperfect. |

#### Used by

 *  **[QualityExpectation](#qualityexpectation)** *[qualityExpectation__severity](#slot-qualityexpectation__severity)*  <sub>1..1</sub> 

### TableKind

The role of a table.

| Text | Meaning: | Description |
| --- | --- | --- |
| DIMENSION | None | Holds attributes, one row per key. |
| FACT | None | Holds measures: snapshot or flow rows. |

#### Used by

 *  **[Table](#table)** *[table__kind](#slot-table__kind)*  <sub>1..1</sub> 

### TestKind

The shape of an invariant's test.

| Text | Meaning: | Description |
| --- | --- | --- |
| EXAMPLE | None | Holds on worked examples (the traps' members). |
| METAMORPHIC | None | Compares two calls whose inputs differ in a controlled way. |
| PROPERTY | None | Holds for every result of every call. |

#### Used by

 *  **[CalculationInvariant](#calculationinvariant)** *[calculationInvariant__test_kind](#slot-calculationinvariant__test_kind)*  <sub>1..1</sub> 

### TimeFilterRule

What a time filter does to the flow.

| Text | Meaning: | Description |
| --- | --- | --- |
| SELECTS_ANCHOR_ONLY | None | A time filter selects the anchor period; the flow window stays relative to it. |

#### Used by

 *  **[DepletionMetric](#depletionmetric)** *[depletionMetric__time_filter_on_flow](#slot-depletionmetric__time_filter_on_flow)*  <sub>1..1</sub> 

### TimeGrain

The length of one period.

| Text | Meaning: | Description |
| --- | --- | --- |
| DAY | None | One day. |
| MONTH | None | One calendar month, the only grain the generated SQL supports. |
| QUARTER | None | One calendar quarter. |
| WEEK | None | One week. |
| YEAR | None | One calendar year. |

#### Used by

 *  **[DepletionMetric](#depletionmetric)** *[depletionMetric__time_grain](#slot-depletionmetric__time_grain)*  <sub>1..1</sub> 
 *  **[Measure](#measure)** *[measure__time_grain](#slot-measure__time_grain)*  <sub>1..1</sub> 

### TimeTotalRule

Whether a total across anchor periods is allowed.

| Text | Meaning: | Description |
| --- | --- | --- |
| FORBIDDEN | None | Several anchor periods give a series; no row totals across them. |

#### Used by

 *  **[TotalsRule](#totalsrule)** *[totalsRule__total_over_time](#slot-totalsrule__total_over_time)*  <sub>1..1</sub> 

### TotalsMethod

How a total is obtained.

| Text | Meaning: | Description |
| --- | --- | --- |
| RECOMPUTE | None | Aggregate the inputs to the total's grain, then run the algorithm. |

#### Used by

 *  **[TotalsRule](#totalsrule)** *[totalsRule__method](#slot-totalsrule__method)*  <sub>1..1</sub> 

### TotalsProjection

How a measure reaches the grain of a total.

| Text | Meaning: | Description |
| --- | --- | --- |
| CONFORMED_PROJECTION | None | Aggregated to the total's grain projected onto conformed attributes. |
| TOTAL_GRAIN | None | Aggregated to the total's grain. |

#### Used by

 *  **[TotalsRule](#totalsrule)** *[totalsRule__flow_aggregation](#slot-totalsrule__flow_aggregation)*  <sub>1..1</sub> 
 *  **[TotalsRule](#totalsrule)** *[totalsRule__snapshot_aggregation](#slot-totalsrule__snapshot_aggregation)*  <sub>1..1</sub>
