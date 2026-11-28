# Tableau Validation Report

**Date:** 2026-11-28 · **Workbook:** `tableau/RetailPulse_Final.twbx` (and `RetailPulse_Final.twb`) ·
**Tableau:** Tableau Desktop Public Edition 2026.3.2 (20263.26.1120.1648), macOS Apple silicon

**Result:** the workbook **opens in Tableau**, all **six data sources are extracts and connect**, and all
**8 KPI sheets render** with no error dialog. The values Tableau computes match the validated project figures.
Tested in the Tableau application itself, as described below. Saving to Tableau Public needs your Tableau Public
sign-in, so that step was not performed.

## 1. Problems found and fixed

| # | Symptom in Tableau | Cause | Fix | Evidence |
|---|---|---|---|---|
| 1 | Workbook did not open: error D2E8DA72, *"No declaration found for element 'manual-sort'"* | the format manifest lacked `<SortTagCleanup />`, so Tableau read sorts in the older format | one line added (`scripts/repair_tableau_workbook.py`); generator fixed | `reports/tableau_workbook_repair_report.md` |
| 2 | Workbook opened but could not be saved to Tableau Public: error 3C242D89, *"must use extracts … RP Cohorts is not an extract"* (Tableau runs this check when a workbook opens) | all six data sources were live CSV connections | six `.hyper` extracts built with the Tableau Hyper API; every data source connects to its extract; packaged `.twbx` | `reports/tableau_extract_report.md` |
| 3 | Tableau log: *"Namespace unexpectedly missing field '[…].[:Measure Names]'"* when a KPI sheet was drawn | the data sources behind KPI sheets did not declare the built-in `[:Measure Names]` field, which Tableau-written workbooks do | declared on the four data sources with KPI sheets; validator check added | this report §3 |
| 4 | Sheet **3.0 KPIs**: error dialog 1B885FB3, *"Logical Query missing field [category (category_satisfaction)] from relationOp [Extract].[vw_category_performance]"* | `Top Category Revenue` (N07) grouped an INCLUDE LOD by the **root** table's `category` while summing a **related** table's `revenue` | the LOD now groups by the category column of the same table (`[cat_category]`). The same pattern was fixed preventively in N34/N35 (`[rev_order_id]`). Results are identical; logic re-validated 264/264 | this report §3 |

Problems 3 and 4 were found only by opening the workbook in Tableau. XML and Python checks could not have
caught them.

## 2. How the Tableau test was run

`tableau/scripts/tableau_runtime_check.py` runs the following for each of the 8 KPI sheets:
1. it writes a copy of `RetailPulse_Final.twbx` (to a scratch folder) with that sheet active
2. it opens the copy with macOS `open -a "Tableau Public (Apple silicon)"`, in a fresh Tableau instance;
   nothing is clicked or typed
3. it reads Tableau's own logs (`~/Documents/My Tableau Repository/Logs/`): workbook loaded, error dialogs,
   extract connections, missing-field warnings
4. it takes the SQL **Tableau generated** for the sheet from Hyper's log, re-executes it on the extract, and
   compares each KPI with the validated SQL reference value
5. it asks Tableau to quit

The files in `tableau/` are never modified.

## 3. Results (final run)

| Sheet | Opened | Error dialogs | Extracts connected | Missing-field warnings | KPI values (Tableau's SQL) |
|---|---|---|---|---|---|
| 1.0 KPIs | ✅ | 0 | 6/6 | 0 | revenue 13,494,400.74 · orders 99,441 · customers 96,096 · median 86.90 ✅ |
| 1.5 YoY Jan–Aug | ✅ | 0 | 6/6 | 0 | Jan–Aug 2017 3,080,850.81 · Jan–Aug 2018 7,341,037.41 ✅ |
| 2.0 KPIs | ✅ | 0 | 6/6 | 0 | one-time 93,099 · historical value 13,494,400.74 ✅ |
| 3.0 KPIs | ✅ | 0 | 6/6 | 0 | category revenue 13,494,400.74 · items 112,101 · categories 74 · top category 1,255,695.13 ✅ |
| 4.0 KPIs | ✅ | 0 | 6/6 | 0 | seller revenue 13,494,400.74 · sellers 3,053 ✅ |
| 5.0 KPIs | ✅ | 0 | 6/6 | 0 | freight 2,241,126.29 · delivered 96,478 · late 7,827 ✅ |
| 5.6 Stage Shares | ✅ | 0 | 6/6 | 0 | stage measures returned (N17, N21–N24) ✅ |
| 6.0 KPIs | ✅ | 0 | 6/6 | 0 | pre-delivery reviews 4,795 ✅ |

18 KPI values compared, 18 equal to the reference. Tableau computes ratio KPIs in the app from the
intermediate values its SQL returns. These were checked from Tableau's queries:

| Figure | From Tableau's SQL | Validated |
|---|---|---|
| Product revenue | 13,494,400.74 | BRL 13,494,400.74 ✅ |
| Eligible orders with items | 98,199 | 98,199 ✅ |
| Total customers | 96,096 | 96,096 ✅ |
| Average order value | 13,494,400.74 / 98,199 = 137.42 | BRL 137.42 ✅ |
| Repeat customer rate | 2,997 / 96,096 = 3.12% | 3.12% ✅ |
| On-time delivery rate | (96,476 − 7,827) / 96,476 = 91.8871% | 91.89% ✅ |

**Extract check at open time.** Opening the repaired workbook raised error 3C242D89 during
`tabui:open-workbook`. Opening `RetailPulse_Final.twbx` raised no error dialog in any of the runs.

**Remaining log messages (not errors):**
- "Lazy Connect" exceptions: Tableau's deferred connection mechanism, also present for working workbooks
- "connection-info-mismatch" (a runtime locale attribute not stored in the file)
- a failed download of Tableau's telemetry configuration (network, unrelated to the workbook)

## 4. Automated checks (repository)

| Suite | Result |
|---|---|
| `scripts/run_all_validations.py` | **18 PASS · 0 FAIL · 6 deliberate SKIP** |
| Tableau calculated fields vs independent SQL | 264/264 |
| Generated workbook (official XSD 2026.3, relationships, captions, formulas, sort format, Measure Names) | 17/17 |
| Extracts + final workbook (Hyper API: every value equals the CSVs; references; no live connections) | 20/20 |
| Tableau runtime check (in the application; run manually, launches Tableau) | 8/8 sheets, 18/18 values |

## 5. Scope

- **Preserved:** the 8 worksheets, 6 data sources, 8 relationships, 100 calculated fields, 2 parameters and sorts
  (verified against the repaired workbook, apart from the documented fixes).
- **No dashboards existed in the workbook at the time of this report.** They were generated and tested
  later the same day: see [`tableau_final_validation.md`](tableau_final_validation.md).
- **Not performed:** Save to Tableau Public. It needs your Tableau Public sign-in.
