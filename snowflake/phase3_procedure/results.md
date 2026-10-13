# Phase 3: the generated procedure, called directly (session 6)

Run 2026-10-03, connection perso, `USE SECONDARY ROLES NONE`, `LINKML_METRICS_ROLE`, RAW as reloaded in session 5
(AS_OF 2026-06-01). `compiler/gen_procedure.py` writes `generated/stock_coverage_procedure.sql` from contract 0.2.0;
`deploy.py` creates `LINKML_METRICS.RAW.STOCK_COVERAGE` (Python 3.12, `EXECUTE AS CALLER`). No agent call.
`STOCK_COVERAGE_PROBE` (probe C0) was dropped at the end of session 7; `parity_c0.py` and the C0 witness of `latency.py` need it recreated from `snowflake/probe_c0/10_stock_coverage_probe.sql`.

## Checks on numbers (`tests/test_procedure.py`)

63 tests, all passing (`python -m pytest tests/test_procedure.py`, skipped without a connection):

| Group | What is asserted | Result |
|---|---|---|
| Heroes, both units | T1 2.8, T2 7.0, T3 6.0, T4 8.5, T7 2.25, T8 0.0 (NO_STOCK), NO_DEMAND null, BEYOND_H 50.0 (BEYOND_HORIZON), in QTY_EQ and VALUE; T1 children 12.0 / 0.5; T3 hold 4.0, all 10.0, by status 6.0 / 4.0 | pass |
| Default scope (BULK_SCOPE) | HOT_GROUND 8.6735 QTY_EQ / 8.2821 VALUE with `DEFAULT_SCOPE_EXCLUDED` and 51,475.5 excluded; explicit `item_type IN (STANDARD, BULK)` 17.4424 / 22.1200, no warning | pass |
| Warnings scoped to the request | T2: `FORECAST_GAPS_FILLED` count **2** (377 on the whole table); T7: `MASTER_DATA_DUPLICATES` count 1, stock 900; T1: no warning | pass |
| Refusals of traps.yaml, both units | T6 `AS_OF_MISSING`, T7 lifecycle question `MASTER_DATA_FANOUT`, T5 `UNIT_RAW_NOT_ADDITIVE` (T5 in QTY_EQ: 2.3651) | pass |
| Every refusal reachable on v0 | 20 cases, 16 codes; every placeholder of the reason filled; earliest `check_order` wins when several faults coexist; `AS_OF_NO_SNAPSHOT` lists the 36 available months and LATEST | pass |
| Totals (T1), one per hierarchy level | sku to country (T1: 2.8, not 12.5, 6.25 or 10.36), sku to family, family to range, country to region, region to grand total: each total row equals a separate call at the total's grain and differs from the sum, mean and stock-weighted mean of its children; equal to the pandas reference (equivalence only) | pass |
| Series | 3 months, one TOTAL per month and none across months; T3 member 4.98, 7.5, 10.0 (probe A's values) | pass |
| Invariants on the 220 SKU x country members of LATEST | coverage >= 0, null only with NO_DEMAND; NO_STOCK iff S = 0, NO_DEMAND iff S > 0 and C(H) = 0, BEYOND_HORIZON iff S > C(H) > 0; <= 24 without BEYOND_HORIZON; filter `batch_status = RELEASED` keeps every member and its forecast; less stock never raises coverage; each series month equals the single-month call; default call equals explicit `item_type = STANDARD` but for the warning; deterministic | pass |

220, not the 229 of the dataset sweep: the 9 others are BULK-only members (stock, never forecast) that the default
scope excludes; the pandas reference with `item_type = STANDARD` gives the same 220 keys.

Not reachable on v0, so not exercised: `HORIZON_NOT_LOADED` (calendar and forecast reach 2029-06, LATEST + 24 is
2028-06), `DATA_QUALITY_FAILED` (every TABLE-scoped expectation is clean), `ATTRIBUTE_UNCLASSIFIED` and
`ATTRIBUTE_NOT_APPLICABLE` (the contract declares no such attribute).

## Parity with probe C0 (`parity_c0.py`)

The 25 checks of `snowflake/probe_c0/check_direct.py`, the same argument strings to both procedures.

| # | Case | Expected (traps.yaml) | C0 `STOCK_COVERAGE_PROBE` | Generated `STOCK_COVERAGE` | Same |
|---|---|---|---|---|---|
| 1 | T1 family x country (QTY_EQ) | 2.8 | ('ok', 2.8, None, 1400.0) | ('ok', 2.8, None, 1400.0) | yes |
| 2 | T1 same, VALUE variant | 2.8 | ('ok', 2.8, None, 16800.0) | ('ok', 2.8, None, 16800.0) | yes |
| 3 | T1 child SKU-H01 | 12.0 | ('ok', 12.0, None, 1200.0) | ('ok', 12.0, None, 1200.0) | yes |
| 4 | T1 child SKU-H02 | 0.5 | ('ok', 0.5, None, 200.0) | ('ok', 0.5, None, 200.0) | yes |
| 5 | T2 sparse months | 7.0 | ('ok', 7.0, None, 500.0) | ('ok', 7.0, None, 500.0) | yes |
| 6 | T3 released lots | 6.0 | ('ok', 6.0, None, 600.0) | ('ok', 6.0, None, 600.0) | yes |
| 7 | T3 quality hold only | 4.0 | ('ok', 4.0, None, 400.0) | ('ok', 4.0, None, 400.0) | yes |
| 8 | T3 all statuses | 10.0 | ('ok', 10.0, None, 1000.0) | ('ok', 10.0, None, 1000.0) | yes |
| 9 | T3 by status: RELEASED row | 6.0 | ('ok', 6.0, None, 600.0) | ('ok', 6.0, None, 600.0) | yes |
| 10 | T3 by status: QUALITY_HOLD row | 4.0 | ('ok', 4.0, None, 400.0) | ('ok', 4.0, None, 400.0) | yes |
| 11 | T4 as-of month | 8.5 | ('ok', 8.5, None, 1000.0) | ('ok', 8.5, None, 1000.0) | yes |
| 12 | T7 duplicated master data | 2.25 | ('ok', 2.25, None, 900.0) | ('ok', 2.25, None, 900.0) | yes |
| 13 | T8 forecast, no stock | 0.0 | ('ok', 0.0, 'NO_STOCK', 0.0) | ('ok', 0.0, 'NO_STOCK', 0.0) | yes |
| 14 | NO_DEMAND | NULL, NO_DEMAND | ('ok', None, 'NO_DEMAND', 500.0) | ('ok', None, 'NO_DEMAND', 500.0) | yes |
| 15 | BEYOND_H | 50.0 | ('ok', 50.0, 'BEYOND_HORIZON', 5000.0) | ('ok', 50.0, 'BEYOND_HORIZON', 5000.0) | yes |
| 16 | T6 no as-of month (NULL) | AS_OF_MISSING | ('refused', 'AS_OF_MISSING') | ('refused', 'AS_OF_MISSING') | yes |
| 17 | T6 no as-of month (empty) | AS_OF_MISSING | ('refused', 'AS_OF_MISSING') | ('refused', 'AS_OF_MISSING') | yes |
| 18 | mid-month as-of | AS_OF_NOT_MONTH_START | ('refused', 'AS_OF_NOT_MONTH_START') | ('refused', 'AS_OF_NOT_MONTH_START') | yes |
| 19 | malformed as-of | AS_OF_INVALID | ('refused', 'AS_OF_INVALID') | ('refused', 'AS_OF_INVALID') | yes |
| 20 | as-of without snapshot | AS_OF_NO_SNAPSHOT | ('refused', 'AS_OF_NO_SNAPSHOT') | ('refused', 'AS_OF_NO_SNAPSHOT') | yes |
| 21 | raw unit | UNIT_RAW_NOT_ADDITIVE | ('refused', 'UNIT_RAW_NOT_ADDITIVE') | ('refused', 'UNIT_RAW_NOT_ADDITIVE') | yes |
| 22 | lifecycle_status in the grain | ATTRIBUTE_UNCLASSIFIED | ('refused', 'ATTRIBUTE_UNCLASSIFIED') | ('ok', 2.8, None, 1400.0) | **no** |
| 23 | unknown attribute | ATTRIBUTE_UNKNOWN | ('refused', 'ATTRIBUTE_UNKNOWN') | ('refused', 'ATTRIBUTE_UNKNOWN') | yes |
| 24 | empty grain | GRAIN_EMPTY | ('refused', 'GRAIN_EMPTY') | ('refused', 'GRAIN_EMPTY') | yes |
| 25 | grain as a comma-separated list | 2.8 | ('ok', 2.8, None, 1400.0) | ('ok', 2.8, None, 1400.0) | yes |

24 / 25 identical

The one difference is intended: the contract declares `lifecycle_status` CONFORMED (decision 6 of session 4), and
the duplicated item (SKU-H06) is not in PANTRY_FLOUR / FR, so the request reads no conflicting row and the answer
is right (2.8). On a request that does read it (the T7 lifecycle question), the generated procedure refuses with
`MASTER_DATA_FANOUT` (tests above).

## Latency of direct calls (`latency.py`)

5 calls per shape, `USE_CACHED_RESULT = FALSE` for the session. From `INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION`:
the CALL's elapsed time, and its child queries (same session, inside the CALL's interval). "Before first child" is
the time from the CALL's start to its first child query; "handler overhead" is the CALL's time not covered by any
child query. Two witnesses were created for the run and dropped after it: an empty Python procedure (same runtime and
package as the generated one, returns a constant) and an empty Snowflake Scripting procedure.

| Shape | Run | Status | Rows | Client ms | CALL elapsed ms | Before first child ms | Child queries | Children wall ms | Children sum ms (compile + exec) | After last child ms | Handler overhead ms | Handler timing (ms) | CALL query id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| single member (T2) | 1 | ok | 1 | 4493 | 4465 | 2227 | 9 | 1300 | 1835 (1613 + 222) | 226 | 3165 | context 270, coverage 1512, quality 1348, total 1783 | `000001be-0000-4000-8000-0000000001be` |
| single member (T2) | 2 | ok | 1 | 4569 | 4467 | 2161 | 9 | 1331 | 1912 (1722 + 190) | 225 | 3136 | context 290, coverage 1550, quality 1380, total 1840 | `000001bf-0000-4000-8000-0000000001bf` |
| single member (T2) | 3 | ok | 1 | 4798 | 4773 | 2266 | 9 | 1530 | 2213 (2021 + 192) | 221 | 3243 | context 331, coverage 1617, quality 1432, total 1948 | `000001c0-0000-4000-8000-0000000001c0` |
| single member (T2) | 4 | ok | 1 | 4597 | 4571 | 2227 | 9 | 1339 | 1934 (1748 + 186) | 220 | 3232 | context 289, coverage 1553, quality 1374, total 1843 | `000001c1-0000-4000-8000-0000000001c1` |
| single member (T2) | 5 | ok | 1 | 4547 | 4505 | 2166 | 9 | 1433 | 2034 (1846 + 188) | 230 | 3072 | context 284, coverage 1553, quality 1372, total 1838 | `000001c2-0000-4000-8000-0000000001c2` |
| family with totals | 1 | ok | 35 | 4932 | 4905 | 2193 | 9 | 2203 | 3243 (2596 + 647) | 221 | 2702 | context 280, coverage 1947, quality 1761, total 2228 | `000001c3-0000-4000-8000-0000000001c3` |
| family with totals | 2 | ok | 35 | 4602 | 4435 | 2140 | 9 | 1636 | 2326 (2112 + 214) | 220 | 2799 | context 290, coverage 1525, quality 819, total 1815 | `000001c4-0000-4000-8000-0000000001c4` |
| family with totals | 3 | ok | 35 | 4786 | 4725 | 2159 | 9 | 2013 | 2699 (2483 + 216) | 217 | 2712 | context 370, coverage 1588, quality 1412, total 1959 | `000001c5-0000-4000-8000-0000000001c5` |
| family with totals | 4 | ok | 35 | 4545 | 4490 | 2187 | 9 | 1677 | 2459 (2246 + 213) | 216 | 2813 | context 306, coverage 1518, quality 1344, total 1825 | `000001c6-0000-4000-8000-0000000001c6` |
| family with totals | 5 | ok | 35 | 5162 | 5090 | 2168 | 9 | 1614 | 2271 (2059 + 212) | 223 | 3476 | context 297, coverage 1529, quality 1363, total 1827 | `000001c7-0000-4000-8000-0000000001c7` |
| 3-month series (T3 member) | 1 | ok | 3 | 4453 | 4427 | 2158 | 9 | 1405 | 2007 (1791 + 216) | 225 | 3022 | context 269, coverage 1531, quality 1365, total 1801 | `000001c8-0000-4000-8000-0000000001c8` |
| 3-month series (T3 member) | 2 | ok | 3 | 4425 | 4399 | 2177 | 9 | 1383 | 1978 (1781 + 197) | 219 | 3016 | context 252, coverage 1500, quality 1330, total 1753 | `000001c9-0000-4000-8000-0000000001c9` |
| 3-month series (T3 member) | 3 | ok | 3 | 4628 | 4515 | 2214 | 9 | 1458 | 2180 (1979 + 201) | 219 | 3057 | context 287, coverage 1516, quality 1354, total 1804 | `000001ca-0000-4000-8000-0000000001ca` |
| 3-month series (T3 member) | 4 | ok | 3 | 5223 | 5196 | 2146 | 9 | 2187 | 3691 (3491 + 200) | 224 | 3009 | context 270, coverage 2311, quality 2165, total 2581 | `000001cb-0000-4000-8000-0000000001cb` |
| 3-month series (T3 member) | 5 | ok | 3 | 4393 | 4363 | 2116 | 9 | 1326 | 1900 (1704 + 196) | 221 | 3037 | context 256, coverage 1512, quality 1355, total 1768 | `000001cc-0000-4000-8000-0000000001cc` |
| single member (T2), probe C0 | 1 | ok | 1 | 3534 | 3506 | 2156 | 7 | 1009 | 1009 (933 + 76) | 229 | 2497 | n/a | `000001cd-0000-4000-8000-0000000001cd` |
| single member (T2), probe C0 | 2 | ok | 1 | 3940 | 3832 | 2457 | 7 | 1034 | 1034 (952 + 82) | 233 | 2798 | n/a | `000001ce-0000-4000-8000-0000000001ce` |
| single member (T2), probe C0 | 3 | ok | 1 | 3635 | 3610 | 2194 | 7 | 1069 | 1069 (990 + 79) | 234 | 2541 | n/a | `000001cf-0000-4000-8000-0000000001cf` |
| single member (T2), probe C0 | 4 | ok | 1 | 3508 | 3485 | 2130 | 7 | 1015 | 1015 (935 + 80) | 237 | 2470 | n/a | `000001d0-0000-4000-8000-0000000001d0` |
| single member (T2), probe C0 | 5 | ok | 1 | 3531 | 3505 | 2112 | 7 | 1051 | 1051 (973 + 78) | 231 | 2454 | n/a | `000001d1-0000-4000-8000-0000000001d1` |
| empty Python procedure (witness) | 1 | ok | n/a | 2676 | 2651 | 2163 | 4 | 219 | 219 (214 + 5) | 222 | 2432 | n/a | `000001d2-0000-4000-8000-0000000001d2` |
| empty Python procedure (witness) | 2 | ok | n/a | 2867 | 2835 | 2162 | 4 | 214 | 214 (206 + 8) | 416 | 2621 | n/a | `000001d3-0000-4000-8000-0000000001d3` |
| empty Python procedure (witness) | 3 | ok | n/a | 2706 | 2664 | 2201 | 4 | 205 | 205 (199 + 6) | 217 | 2459 | n/a | `000001d4-0000-4000-8000-0000000001d4` |
| empty Python procedure (witness) | 4 | ok | n/a | 2655 | 2630 | 2152 | 4 | 209 | 209 (201 + 8) | 226 | 2421 | n/a | `000001d5-0000-4000-8000-0000000001d5` |
| empty Python procedure (witness) | 5 | ok | n/a | 2752 | 2639 | 2182 | 4 | 201 | 201 (193 + 8) | 216 | 2438 | n/a | `000001d6-0000-4000-8000-0000000001d6` |
| empty SQL Scripting procedure (witness) | 1 | ok | n/a | 159 | 132 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 132 | n/a | `000001d7-0000-4000-8000-0000000001d7` |
| empty SQL Scripting procedure (witness) | 2 | ok | n/a | 137 | 113 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 113 | n/a | `000001d8-0000-4000-8000-0000000001d8` |
| empty SQL Scripting procedure (witness) | 3 | ok | n/a | 194 | 119 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 119 | n/a | `000001d9-0000-4000-8000-0000000001d9` |
| empty SQL Scripting procedure (witness) | 4 | ok | n/a | 161 | 115 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 115 | n/a | `000001da-0000-4000-8000-0000000001da` |
| empty SQL Scripting procedure (witness) | 5 | ok | n/a | 144 | 119 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 119 | n/a | `000001db-0000-4000-8000-0000000001db` |

| Shape | Median CALL ms | Median before first child ms | Median children wall ms | Median handler overhead ms | Overhead share |
|---|---|---|---|---|---|
| single member (T2) | 4505 | 2227 | 1339 | 3165 | 70% |
| family with totals | 4725 | 2168 | 1677 | 2799 | 59% |
| 3-month series (T3 member) | 4427 | 2158 | 1405 | 3022 | 68% |
| single member (T2), probe C0 | 3506 | 2156 | 1034 | 2497 | 71% |
| empty Python procedure (witness) | 2651 | 2163 | 209 | 2438 | 92% |
| empty SQL Scripting procedure (witness) | 119 | n/a | 0 | 119 | 100% |

What the numbers say **[measured]**:

1. **About 2.2 s pass before the handler's first query**, in every Python procedure, the empty one included (2,116
   to 2,457 ms). The empty Python procedure costs 2.65 s in all; the empty SQL Scripting one 0.12 s. The Python
   runtime's start is about **2.5 s of the 4.4 to 4.7 s** of a generated call, and about 70% of probe C0's 3.5 s.
2. The 4 child queries of the empty Python procedure (`CURRENT_DATABASE()`, `CURRENT_SCHEMA()`,
   `SYSTEM$GET_DEFAULT_PYTHON_ARTIFACT_REPOSITORY`, `CURRENT_DATABASE()`) are the Snowpark session's own, about 0.2 s;
   about 0.22 s more pass after the last child query, before the CALL ends.
3. The generated procedure's own SQL takes 1.3 to 2.2 s of wall time. **Compilation dominates it**: for a single
   member, about 1.8 s of compilation against 0.2 s of execution summed over the child queries. The coverage query
   compiles in about 0.5 s; the context query in about 0.2 s.
4. The quality and coverage queries run concurrently (`collect_nowait`), and each result is then read back with a
   `RESULT_SCAN` child query. The handler waits about 0.6 s more for them than the queries take (see one call in
   detail below): concurrency does not pay here, at this data size.
5. Shape barely matters: single member, family with totals (35 rows) and 3-month series are within 0.3 s of each
   other at the median.

One call in detail (single member, run outside the table above), offsets from the CALL's start: Snowpark queries at
2.20 s to 2.44 s; context query 2.46 s to 2.67 s; quality query 2.70 s to 3.35 s and coverage query 2.75 s to 3.25 s
(concurrent); `RESULT_SCAN` of each at 3.93 s and 4.07 s; CALL end 4.36 s.

## Objects

| Object | State |
|---|---|
| `LINKML_METRICS.RAW.STOCK_COVERAGE(VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR)` | created, generated, kept |
| `LINKML_METRICS.RAW.STOCK_COVERAGE_PROBE` | dropped at the end of session 7 (query `000001dc-0000-4000-8000-0000000001dc`) |
| `EMPTY_PY_PROBE`, `EMPTY_SQL_PROBE` | created and dropped by `latency.py` |
| `COVERAGE_SPINE_CLOSING_PROBE_SV` | created in step 0, kept (probe) |

## Session 7: cheap latency wins, measured and not kept (decision 2)

Run 2026-10-03, same conditions as above (`latency.py`, 5 calls per shape, `USE_CACHED_RESULT = FALSE`), contract
0.2.1. Three modes of the handler, each deployed in turn and measured in one `latency.py` run:

- **async** (session 6, kept): the quality and coverage queries start together (`collect_nowait`), each result read
  back with a `RESULT_SCAN`;
- **sync**: the quality query, then the coverage query, each with `collect()` (no `RESULT_SCAN`);
- **single**: quality and coverage in one statement (the quality columns `LEFT JOIN`ed to the coverage rows on TRUE),
  compiled once, read with `collect()`.

| Shape | async, median CALL ms | sync | single | async children wall ms | sync | single |
|---|---|---|---|---|---|---|
| single member (T2) | **3,855** | 4,433 | 4,174 | 1,101 | 1,784 | 1,607 |
| family with totals | **4,418** | 5,012 | 4,787 | 1,718 | 2,312 | 2,233 |
| 3-month series (T3 member) | 4,479 | 4,582 | **4,293** | 1,405 | 1,978 | 1,774 |
| witness: probe C0, single member | 3,833 | 3,631 | 3,899 | 1,291 | 1,055 | 1,167 |
| witness: empty Python procedure | 2,727 | 2,642 | 2,784 | 272 | 213 | 246 |

What it shows **[measured]**:

1. Neither change lowers the median on all three shapes: **sync** is slower everywhere (+0.1 to +0.6 s), **single** on
   two shapes of three (+0.3 to +0.4 s) and faster on the series (-0.2 s), within the run-to-run spread of the
   witnesses (C0 3.6 to 3.9 s). By the rule of decision 2, both are dropped; the handler stays as in session 6.
2. Why: **compilation dominates, and the two concurrent queries compile in parallel.** Single member, handler timings:
   async, quality about 0.75 s and coverage about 0.88 s, overlapping; sync, 0.75 s then 0.6 s in sequence; single,
   one statement of about 1.2 s. The single statement compiles faster than the two in a row but slower than the
   longer of the two in parallel; the `RESULT_SCAN` read-back (about 0.2 s each) costs less than that difference.
3. Session 6 measured the async mode at 4.5 s for a single member; today 3.7 to 4.8 s across its five calls (median
   3.9 s). The compile time of the same statements varies by about 0.6 s between calls (handler timings 0.75 s or
   1.33 s for the quality query): a gain below that size needs more than 5 calls per shape to be seen.
4. What remains fixed: about 2.2 s before the handler's first query, in every Python procedure. The rest is about 0.25 s
   of context query, 0.9 to 1.5 s of compile-bound SQL, and 0.2 s after the last query.

Tests: `python -m pytest`, **107 passed** (6 min 42 s) on the async procedure redeployed after the comparison. The two
variants are not kept in the handler; their SQL shape is described above.

### Raw output, async (before, kept)

| Shape | Run | Status | Rows | Client ms | CALL elapsed ms | Before first child ms | Child queries | Children wall ms | Children sum ms (compile + exec) | After last child ms | Handler overhead ms | Handler timing (ms) | CALL query id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| single member (T2) | 1 | ok | 1 | 4945 | 4829 | 2330 | 9 | 1628 | 2228 (1710 + 518) | 225 | 3201 | context 527, coverage 1499, quality 1330, total 2026 | `000001dd-0000-4000-8000-0000000001dd` |
| single member (T2) | 2 | ok | 1 | 3880 | 3855 | 2294 | 9 | 1098 | 1605 (1420 + 185) | 218 | 2757 | context 237, coverage 886, quality 751, total 1124 | `000001de-0000-4000-8000-0000000001de` |
| single member (T2) | 3 | ok | 1 | 4400 | 4377 | 2146 | 9 | 1274 | 1872 (1686 + 186) | 218 | 3103 | context 258, coverage 1486, quality 1347, total 1744 | `000001df-0000-4000-8000-0000000001df` |
| single member (T2) | 4 | ok | 1 | 3718 | 3694 | 2158 | 9 | 1094 | 1572 (1389 + 183) | 224 | 2600 | context 221, coverage 880, quality 753, total 1102 | `000001e0-0000-4000-8000-0000000001e0` |
| single member (T2) | 5 | ok | 1 | 3701 | 3678 | 2150 | 9 | 1101 | 1603 (1417 + 186) | 214 | 2577 | context 224, coverage 882, quality 747, total 1107 | `000001e1-0000-4000-8000-0000000001e1` |
| family with totals | 1 | ok | 35 | 4400 | 4372 | 2185 | 9 | 1718 | 2362 (2154 + 208) | 212 | 2654 | context 262, coverage 1475, quality 1329, total 1738 | `000001e2-0000-4000-8000-0000000001e2` |
| family with totals | 2 | ok | 35 | 4475 | 4358 | 2142 | 9 | 1511 | 2188 (1979 + 209) | 236 | 2847 | context 253, coverage 1482, quality 803, total 1735 | `000001e3-0000-4000-8000-0000000001e3` |
| family with totals | 3 | ok | 35 | 5026 | 5002 | 2149 | 9 | 2142 | 3093 (2873 + 220) | 219 | 2860 | context 308, coverage 2063, quality 1354, total 2372 | `000001e4-0000-4000-8000-0000000001e4` |
| family with totals | 4 | ok | 35 | 4511 | 4485 | 2203 | 9 | 1882 | 2698 (2482 + 216) | 214 | 2603 | context 299, coverage 1491, quality 1345, total 1791 | `000001e5-0000-4000-8000-0000000001e5` |
| family with totals | 5 | ok | 35 | 4469 | 4418 | 2198 | 9 | 1714 | 2419 (2211 + 208) | 213 | 2704 | context 265, coverage 1507, quality 1334, total 1773 | `000001e6-0000-4000-8000-0000000001e6` |
| 3-month series (T3 member) | 1 | ok | 3 | 4328 | 4299 | 2153 | 9 | 1405 | 2025 (1840 + 185) | 217 | 2894 | context 257, coverage 1448, quality 1304, total 1705 | `000001e7-0000-4000-8000-0000000001e7` |
| 3-month series (T3 member) | 2 | ok | 3 | 4509 | 4479 | 2139 | 9 | 1335 | 1900 (1688 + 212) | 213 | 3144 | context 245, coverage 1652, quality 1492, total 1897 | `000001e8-0000-4000-8000-0000000001e8` |
| 3-month series (T3 member) | 3 | ok | 3 | 4125 | 4096 | 2066 | 9 | 1122 | 1624 (1433 + 191) | 207 | 2974 | context 224, coverage 1392, quality 1267, total 1616 | `000001e9-0000-4000-8000-0000000001e9` |
| 3-month series (T3 member) | 4 | ok | 3 | 5592 | 5507 | 2120 | 9 | 2287 | 3370 (3166 + 204) | 228 | 3220 | context 416, coverage 2306, quality 1871, total 2722 | `000001ea-0000-4000-8000-0000000001ea` |
| 3-month series (T3 member) | 5 | ok | 3 | 5654 | 5503 | 2372 | 9 | 2288 | 3093 (2897 + 196) | 227 | 3215 | context 404, coverage 2009, quality 1749, total 2413 | `000001eb-0000-4000-8000-0000000001eb` |
| single member (T2), probe C0 | 1 | ok | 1 | 4668 | 4547 | 2243 | 7 | 1940 | 1940 (1857 + 83) | 244 | 2607 | n/a | `000001ec-0000-4000-8000-0000000001ec` |
| single member (T2), probe C0 | 2 | ok | 1 | 3809 | 3725 | 2171 | 7 | 1197 | 1197 (1118 + 79) | 233 | 2528 | n/a | `000001ed-0000-4000-8000-0000000001ed` |
| single member (T2), probe C0 | 3 | ok | 1 | 3910 | 3877 | 2171 | 7 | 1337 | 1337 (1254 + 83) | 242 | 2540 | n/a | `000001ee-0000-4000-8000-0000000001ee` |
| single member (T2), probe C0 | 4 | ok | 1 | 3891 | 3833 | 2177 | 7 | 1291 | 1291 (1212 + 79) | 236 | 2542 | n/a | `000001ef-0000-4000-8000-0000000001ef` |
| single member (T2), probe C0 | 5 | ok | 1 | 3808 | 3780 | 2212 | 7 | 1175 | 1175 (1093 + 82) | 258 | 2605 | n/a | `000001f0-0000-4000-8000-0000000001f0` |
| empty Python procedure (witness) | 1 | ok | n/a | 2751 | 2727 | 2245 | 4 | 219 | 219 (213 + 6) | 213 | 2508 | n/a | `000001f1-0000-4000-8000-0000000001f1` |
| empty Python procedure (witness) | 2 | ok | n/a | 3327 | 3298 | 2151 | 4 | 805 | 805 (769 + 36) | 218 | 2493 | n/a | `000001f2-0000-4000-8000-0000000001f2` |
| empty Python procedure (witness) | 3 | ok | n/a | 2955 | 2773 | 2203 | 4 | 305 | 305 (298 + 7) | 215 | 2468 | n/a | `000001f3-0000-4000-8000-0000000001f3` |
| empty Python procedure (witness) | 4 | ok | n/a | 2743 | 2716 | 2161 | 4 | 272 | 272 (265 + 7) | 233 | 2444 | n/a | `000001f4-0000-4000-8000-0000000001f4` |
| empty Python procedure (witness) | 5 | ok | n/a | 2662 | 2572 | 2083 | 4 | 227 | 227 (219 + 8) | 214 | 2345 | n/a | `000001f5-0000-4000-8000-0000000001f5` |
| empty SQL Scripting procedure (witness) | 1 | ok | n/a | 165 | 141 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 141 | n/a | `000001f6-0000-4000-8000-0000000001f6` |
| empty SQL Scripting procedure (witness) | 2 | ok | n/a | 129 | 105 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 105 | n/a | `000001f7-0000-4000-8000-0000000001f7` |
| empty SQL Scripting procedure (witness) | 3 | ok | n/a | 135 | 109 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 109 | n/a | `000001f8-0000-4000-8000-0000000001f8` |
| empty SQL Scripting procedure (witness) | 4 | ok | n/a | 139 | 115 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 115 | n/a | `000001f9-0000-4000-8000-0000000001f9` |
| empty SQL Scripting procedure (witness) | 5 | ok | n/a | 156 | 110 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 110 | n/a | `000001fa-0000-4000-8000-0000000001fa` |

| Shape | Median CALL ms | Median before first child ms | Median children wall ms | Median handler overhead ms | Overhead share |
|---|---|---|---|---|---|
| single member (T2) | 3855 | 2158 | 1101 | 2757 | 72% |
| family with totals | 4418 | 2185 | 1718 | 2704 | 61% |
| 3-month series (T3 member) | 4479 | 2139 | 1405 | 3144 | 70% |
| single member (T2), probe C0 | 3833 | 2177 | 1291 | 2542 | 66% |
| empty Python procedure (witness) | 2727 | 2161 | 272 | 2468 | 91% |
| empty SQL Scripting procedure (witness) | 110 | n/a | 0 | 110 | 100% |

### Raw output, sync (measured, dropped)

| Shape | Run | Status | Rows | Client ms | CALL elapsed ms | Before first child ms | Child queries | Children wall ms | Children sum ms (compile + exec) | After last child ms | Handler overhead ms | Handler timing (ms) | CALL query id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| single member (T2) | 1 | ok | 1 | 4874 | 4848 | 2421 | 7 | 2040 | 2040 (1558 + 482) | 261 | 2808 | context 482, coverage 593, quality 853, total 1928 | `000001fb-0000-4000-8000-0000000001fb` |
| single member (T2) | 2 | ok | 1 | 4497 | 4386 | 2229 | 7 | 1784 | 1784 (1591 + 193) | 241 | 2602 | context 271, coverage 656, quality 758, total 1687 | `000001fc-0000-4000-8000-0000000001fc` |
| single member (T2) | 3 | ok | 1 | 4552 | 4521 | 2340 | 7 | 1784 | 1784 (1594 + 190) | 248 | 2737 | context 283, coverage 575, quality 813, total 1672 | `000001fd-0000-4000-8000-0000000001fd` |
| single member (T2) | 4 | ok | 1 | 4417 | 4324 | 2210 | 7 | 1709 | 1709 (1518 + 191) | 254 | 2615 | context 270, coverage 589, quality 732, total 1592 | `000001fe-0000-4000-8000-0000000001fe` |
| single member (T2) | 5 | ok | 1 | 4460 | 4433 | 2216 | 7 | 1778 | 1778 (1580 + 198) | 277 | 2655 | context 310, coverage 647, quality 726, total 1684 | `000001ff-0000-4000-8000-0000000001ff` |
| family with totals | 1 | ok | 35 | 5040 | 5012 | 2232 | 7 | 2367 | 2367 (2148 + 219) | 265 | 2645 | context 277, coverage 1231, quality 780, total 2288 | `00000200-0000-4000-8000-000000000200` |
| family with totals | 2 | ok | 35 | 5182 | 5129 | 2267 | 7 | 2424 | 2424 (2203 + 221) | 257 | 2705 | context 335, coverage 1109, quality 815, total 2259 | `00000201-0000-4000-8000-000000000201` |
| family with totals | 3 | ok | 35 | 5356 | 5330 | 2632 | 7 | 2312 | 2312 (2096 + 216) | 251 | 3018 | context 292, coverage 1153, quality 735, total 2181 | `00000202-0000-4000-8000-000000000202` |
| family with totals | 4 | ok | 35 | 5031 | 4912 | 2203 | 7 | 2309 | 2309 (2083 + 226) | 272 | 2603 | context 259, coverage 1195, quality 758, total 2212 | `00000203-0000-4000-8000-000000000203` |
| family with totals | 5 | ok | 35 | 4693 | 4668 | 2217 | 7 | 2054 | 2054 (1838 + 216) | 249 | 2614 | context 251, coverage 980, quality 704, total 1935 | `00000204-0000-4000-8000-000000000204` |
| 3-month series (T3 member) | 1 | ok | 3 | 4458 | 4431 | 2209 | 7 | 1821 | 1821 (1624 + 197) | 262 | 2610 | context 265, coverage 620, quality 839, total 1725 | `00000205-0000-4000-8000-000000000205` |
| 3-month series (T3 member) | 2 | ok | 3 | 4733 | 4607 | 2210 | 7 | 2022 | 2022 (1822 + 200) | 243 | 2585 | context 314, coverage 727, quality 872, total 1915 | `00000206-0000-4000-8000-000000000206` |
| 3-month series (T3 member) | 3 | ok | 3 | 4607 | 4582 | 2212 | 7 | 1978 | 1978 (1782 + 196) | 264 | 2604 | context 267, coverage 699, quality 896, total 1863 | `00000207-0000-4000-8000-000000000207` |
| 3-month series (T3 member) | 4 | ok | 3 | 4440 | 4415 | 2216 | 7 | 1798 | 1798 (1602 + 196) | 247 | 2617 | context 273, coverage 608, quality 834, total 1715 | `00000208-0000-4000-8000-000000000208` |
| 3-month series (T3 member) | 5 | ok | 3 | 4716 | 4628 | 2189 | 7 | 2027 | 2027 (1820 + 207) | 276 | 2601 | context 269, coverage 687, quality 961, total 1918 | `00000209-0000-4000-8000-000000000209` |
| single member (T2), probe C0 | 1 | ok | 1 | 3710 | 3682 | 2219 | 7 | 1100 | 1100 (1016 + 84) | 248 | 2582 | n/a | `0000020a-0000-4000-8000-00000000020a` |
| single member (T2), probe C0 | 2 | ok | 1 | 3787 | 3631 | 2257 | 7 | 1019 | 1019 (937 + 82) | 248 | 2612 | n/a | `0000020b-0000-4000-8000-00000000020b` |
| single member (T2), probe C0 | 3 | ok | 1 | 3808 | 3683 | 2209 | 7 | 1116 | 1116 (1029 + 87) | 244 | 2567 | n/a | `0000020c-0000-4000-8000-00000000020c` |
| single member (T2), probe C0 | 4 | ok | 1 | 3700 | 3629 | 2176 | 7 | 1055 | 1055 (966 + 89) | 288 | 2574 | n/a | `0000020d-0000-4000-8000-00000000020d` |
| single member (T2), probe C0 | 5 | ok | 1 | 3614 | 3588 | 2186 | 7 | 1038 | 1038 (957 + 81) | 251 | 2550 | n/a | `0000020e-0000-4000-8000-00000000020e` |
| empty Python procedure (witness) | 1 | ok | n/a | 2762 | 2715 | 2211 | 4 | 213 | 213 (206 + 7) | 240 | 2502 | n/a | `0000020f-0000-4000-8000-00000000020f` |
| empty Python procedure (witness) | 2 | ok | n/a | 2702 | 2670 | 2193 | 4 | 205 | 205 (198 + 7) | 224 | 2465 | n/a | `00000210-0000-4000-8000-000000000210` |
| empty Python procedure (witness) | 3 | ok | n/a | 2655 | 2630 | 2142 | 4 | 216 | 216 (208 + 8) | 222 | 2414 | n/a | `00000211-0000-4000-8000-000000000211` |
| empty Python procedure (witness) | 4 | ok | n/a | 2666 | 2642 | 2104 | 4 | 244 | 244 (238 + 6) | 225 | 2398 | n/a | `00000212-0000-4000-8000-000000000212` |
| empty Python procedure (witness) | 5 | ok | n/a | 2789 | 2637 | 2174 | 4 | 198 | 198 (193 + 5) | 219 | 2439 | n/a | `00000213-0000-4000-8000-000000000213` |
| empty SQL Scripting procedure (witness) | 1 | ok | n/a | 147 | 124 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 124 | n/a | `00000214-0000-4000-8000-000000000214` |
| empty SQL Scripting procedure (witness) | 2 | ok | n/a | 130 | 109 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 109 | n/a | `00000215-0000-4000-8000-000000000215` |
| empty SQL Scripting procedure (witness) | 3 | ok | n/a | 135 | 108 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 108 | n/a | `00000216-0000-4000-8000-000000000216` |
| empty SQL Scripting procedure (witness) | 4 | ok | n/a | 134 | 109 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 109 | n/a | `00000217-0000-4000-8000-000000000217` |
| empty SQL Scripting procedure (witness) | 5 | ok | n/a | 129 | 106 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 106 | n/a | `00000218-0000-4000-8000-000000000218` |

| Shape | Median CALL ms | Median before first child ms | Median children wall ms | Median handler overhead ms | Overhead share |
|---|---|---|---|---|---|
| single member (T2) | 4433 | 2229 | 1784 | 2655 | 60% |
| family with totals | 5012 | 2232 | 2312 | 2645 | 53% |
| 3-month series (T3 member) | 4582 | 2210 | 1978 | 2604 | 57% |
| single member (T2), probe C0 | 3631 | 2209 | 1055 | 2574 | 71% |
| empty Python procedure (witness) | 2642 | 2174 | 213 | 2439 | 92% |
| empty SQL Scripting procedure (witness) | 109 | n/a | 0 | 109 | 100% |

### Raw output, single statement (measured, dropped)

| Shape | Run | Status | Rows | Client ms | CALL elapsed ms | Before first child ms | Child queries | Children wall ms | Children sum ms (compile + exec) | After last child ms | Handler overhead ms | Handler timing (ms) | CALL query id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| single member (T2) | 1 | ok | 1 | 5054 | 5028 | 2989 | 6 | 1696 | 1696 (1516 + 180) | 243 | 3332 | context 284, quality_and_coverage 1246, total 1530 | `00000219-0000-4000-8000-000000000219` |
| single member (T2) | 2 | ok | 1 | 4287 | 4174 | 2135 | 6 | 1696 | 1696 (1524 + 172) | 250 | 2478 | context 260, quality_and_coverage 1298, total 1559 | `0000021a-0000-4000-8000-00000000021a` |
| single member (T2) | 3 | ok | 1 | 4342 | 4312 | 2369 | 6 | 1607 | 1607 (1441 + 166) | 237 | 2705 | context 261, quality_and_coverage 1198, total 1459 | `0000021b-0000-4000-8000-00000000021b` |
| single member (T2) | 4 | ok | 1 | 4085 | 4060 | 2145 | 6 | 1573 | 1573 (1406 + 167) | 235 | 2487 | context 259, quality_and_coverage 1186, total 1445 | `0000021c-0000-4000-8000-00000000021c` |
| single member (T2) | 5 | ok | 1 | 4103 | 4077 | 2148 | 6 | 1589 | 1589 (1421 + 168) | 243 | 2488 | context 262, quality_and_coverage 1195, total 1458 | `0000021d-0000-4000-8000-00000000021d` |
| family with totals | 1 | ok | 35 | 4920 | 4787 | 2209 | 6 | 2227 | 2227 (2027 + 200) | 251 | 2560 | context 260, quality_and_coverage 1818, total 2079 | `0000021e-0000-4000-8000-00000000021e` |
| family with totals | 2 | ok | 35 | 5305 | 5278 | 2256 | 6 | 2651 | 2651 (2450 + 201) | 255 | 2627 | context 278, quality_and_coverage 2224, total 2503 | `0000021f-0000-4000-8000-00000000021f` |
| family with totals | 3 | ok | 35 | 4805 | 4779 | 2254 | 6 | 2181 | 2181 (1983 + 198) | 247 | 2598 | context 257, quality_and_coverage 1791, total 2049 | `00000220-0000-4000-8000-000000000220` |
| family with totals | 4 | ok | 35 | 5496 | 5370 | 2404 | 6 | 2600 | 2600 (2404 + 196) | 253 | 2770 | context 324, quality_and_coverage 2031, total 2355 | `00000221-0000-4000-8000-000000000221` |
| family with totals | 5 | ok | 35 | 4773 | 4745 | 2158 | 6 | 2233 | 2233 (2033 + 200) | 255 | 2512 | context 272, quality_and_coverage 1823, total 2096 | `00000222-0000-4000-8000-000000000222` |
| 3-month series (T3 member) | 1 | ok | 3 | 4270 | 4244 | 2211 | 6 | 1689 | 1689 (1521 + 168) | 241 | 2555 | context 276, quality_and_coverage 1273, total 1549 | `00000223-0000-4000-8000-000000000223` |
| 3-month series (T3 member) | 2 | ok | 3 | 4285 | 4258 | 2148 | 6 | 1774 | 1774 (1608 + 166) | 240 | 2484 | context 285, quality_and_coverage 1347, total 1632 | `00000224-0000-4000-8000-000000000224` |
| 3-month series (T3 member) | 3 | ok | 3 | 4488 | 4438 | 2235 | 6 | 1867 | 1867 (1698 + 169) | 244 | 2571 | context 291, quality_and_coverage 1418, total 1710 | `00000225-0000-4000-8000-000000000225` |
| 3-month series (T3 member) | 4 | ok | 3 | 4548 | 4440 | 2173 | 6 | 1840 | 1840 (1632 + 208) | 331 | 2600 | context 281, quality_and_coverage 1513, total 1794 | `00000226-0000-4000-8000-000000000226` |
| 3-month series (T3 member) | 5 | ok | 3 | 4422 | 4293 | 2163 | 6 | 1718 | 1718 (1551 + 167) | 308 | 2575 | context 292, quality_and_coverage 1292, total 1584 | `00000227-0000-4000-8000-000000000227` |
| single member (T2), probe C0 | 1 | ok | 1 | 4425 | 4365 | 2422 | 7 | 1502 | 1502 (1412 + 90) | 276 | 2863 | n/a | `00000228-0000-4000-8000-000000000228` |
| single member (T2), probe C0 | 2 | ok | 1 | 3928 | 3899 | 2321 | 7 | 1167 | 1167 (1083 + 84) | 276 | 2732 | n/a | `00000229-0000-4000-8000-000000000229` |
| single member (T2), probe C0 | 3 | ok | 1 | 3800 | 3772 | 2262 | 7 | 1120 | 1120 (1035 + 85) | 269 | 2652 | n/a | `0000022a-0000-4000-8000-00000000022a` |
| single member (T2), probe C0 | 4 | ok | 1 | 4313 | 4268 | 2237 | 7 | 1612 | 1612 (1525 + 87) | 293 | 2656 | n/a | `0000022b-0000-4000-8000-00000000022b` |
| single member (T2), probe C0 | 5 | ok | 1 | 3787 | 3709 | 2208 | 7 | 1132 | 1132 (1050 + 82) | 247 | 2577 | n/a | `0000022c-0000-4000-8000-00000000022c` |
| empty Python procedure (witness) | 1 | ok | n/a | 2846 | 2784 | 2279 | 4 | 216 | 216 (208 + 8) | 239 | 2568 | n/a | `0000022d-0000-4000-8000-00000000022d` |
| empty Python procedure (witness) | 2 | ok | n/a | 2793 | 2702 | 2166 | 4 | 246 | 246 (239 + 7) | 239 | 2456 | n/a | `0000022e-0000-4000-8000-00000000022e` |
| empty Python procedure (witness) | 3 | ok | n/a | 2860 | 2747 | 2225 | 4 | 234 | 234 (226 + 8) | 237 | 2513 | n/a | `0000022f-0000-4000-8000-00000000022f` |
| empty Python procedure (witness) | 4 | ok | n/a | 2950 | 2788 | 2238 | 4 | 254 | 254 (248 + 6) | 239 | 2534 | n/a | `00000230-0000-4000-8000-000000000230` |
| empty Python procedure (witness) | 5 | ok | n/a | 3071 | 2923 | 2364 | 4 | 275 | 275 (267 + 8) | 231 | 2648 | n/a | `00000231-0000-4000-8000-000000000231` |
| empty SQL Scripting procedure (witness) | 1 | ok | n/a | 179 | 144 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 144 | n/a | `00000232-0000-4000-8000-000000000232` |
| empty SQL Scripting procedure (witness) | 2 | ok | n/a | 191 | 129 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 129 | n/a | `00000233-0000-4000-8000-000000000233` |
| empty SQL Scripting procedure (witness) | 3 | ok | n/a | 151 | 126 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 126 | n/a | `00000234-0000-4000-8000-000000000234` |
| empty SQL Scripting procedure (witness) | 4 | ok | n/a | 144 | 118 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 118 | n/a | `00000235-0000-4000-8000-000000000235` |
| empty SQL Scripting procedure (witness) | 5 | ok | n/a | 195 | 135 | n/a | 0 | 0 | 0 (0 + 0) | n/a | 135 | n/a | `00000236-0000-4000-8000-000000000236` |

| Shape | Median CALL ms | Median before first child ms | Median children wall ms | Median handler overhead ms | Overhead share |
|---|---|---|---|---|---|
| single member (T2) | 4174 | 2148 | 1607 | 2488 | 60% |
| family with totals | 4787 | 2254 | 2233 | 2598 | 54% |
| 3-month series (T3 member) | 4293 | 2173 | 1774 | 2571 | 60% |
| single member (T2), probe C0 | 3899 | 2262 | 1167 | 2656 | 68% |
| empty Python procedure (witness) | 2784 | 2238 | 246 | 2534 | 91% |
| empty SQL Scripting procedure (witness) | 129 | n/a | 0 | 129 | 100% |
