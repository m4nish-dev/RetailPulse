# Tableau Extract Report

**Date:** 2026-11-28 · **Scripts:** `tableau/scripts/build_tableau_extracts.py`,
`tableau/scripts/validate_tableau_extracts.py` · **Result:** 19/19 checks pass at XML and data level
(20/20 with the build check); **opened and tested in Tableau 2026.3.2 afterwards; see
`reports/tableau_validation_report.md`**

## Error reported by Tableau Desktop Public Edition 2026.3.2

> Workbooks saved to Tableau Public must use extracts. To create an extract, click the Data Source
> tab, then select Create Extract. The data source, RP Cohorts, is not an extract. (Error 3C242D89)

Tableau's log for that session also shows that `RetailPulse_repaired.twb` itself opened and drew its
sheets, so the earlier `manual-sort` repair worked.

## Root cause

All six data sources of the generated workbook were **live text-file connections** to the CSVs
(`class="textscan"`). RP Cohorts was only the first one Tableau checked. Tableau Public saves only
workbooks whose data sources are extracts.

| Data source | CSV files | Connection before | Connection now |
|---|---|---|---|
| RP Orders | `vw_order_summary`, `vw_review_summary`, `analytical/delivery_stage_orders` | live text | extract `RP_Orders.hyper` |
| RP Customers | `vw_customer_summary`, `analytical/rfm_customer_segments` | live text | extract `RP_Customers.hyper` |
| RP Cohorts | `analytical/cohort_retention` | live text | extract `RP_Cohorts.hyper` |
| RP Categories | `analytical/dim_category`, `vw_category_performance`, `analytical/product_performance`, `analytical/category_satisfaction` | live text | extract `RP_Categories.hyper` |
| RP Sellers | `vw_seller_performance`, `analytical/seller_scorecard`, `analytical/seller_category_performance` | live text | extract `RP_Sellers.hyper` |
| RP Stage Summary | `analytical/delivery_stage_summary` | live text | extract `RP_Stage_Summary.hyper` |

## How the extracts were made

- **Tool:** Tableau Hyper API (`tableauhyperapi` 0.0.26479, native Apple-silicon build). Usage data
  is not sent to Tableau.
- **Layout:** one `.hyper` per data source, with every table in schema `"Extract"`. That is the
  layout of the World Indicators sample shipped with Tableau Public.
- **Types:** each table is created with the types the workbook declares (BIG_INT, DOUBLE, TEXT,
  DATE, TIMESTAMP, all nullable).
- **Loading:** each table is loaded with Hyper's own CSV reader (`COPY … WITH (FORMAT CSV, HEADER,
  NULL '')`). Rows and values are not altered, and empty CSV fields become NULL.
- **Workbook connection:** each data source connects directly to its `.hyper` file (`class="hyper"`,
  tables `[Extract].[<table>]`), the pattern Tableau uses in that sample. In
  `RetailPulse_Final.twbx` the path is package-relative (`Data/extracts/RP_Orders.hyper` …). In
  `RetailPulse_Final.twb` it is the absolute path of `tableau/extracts/`.
- **What stayed the same:** the workbook comes from the same registry and generator as before.
  Captions, types, formats, 100 calculated fields, 8 relationships, 2 parameters, 8 KPI sheets,
  their sorts, and the `<SortTagCleanup />` declaration are unchanged. The validator confirms this
  against `RetailPulse_repaired.twb`.

## Row counts (extract = CSV = manifest)

| Table | Rows | Table | Rows |
|---|---|---|---|
| vw_order_summary | 99,441 | vw_category_performance | 1,282 |
| vw_review_summary | 99,224 | product_performance | 32,951 |
| delivery_stage_orders | 95,088 | category_satisfaction | 74 |
| vw_customer_summary | 96,096 | vw_seller_performance | 3,053 |
| rfm_customer_segments | 96,096 | seller_scorecard | 3,053 |
| cohort_retention | 400 | seller_category_performance | 6,545 |
| dim_category | 74 | delivery_stage_summary | 4 |

Extract sizes: RP_Orders 30.0 MB · RP_Customers 8.5 MB · RP_Categories 2.2 MB · RP_Sellers 1.2 MB ·
RP_Cohorts and RP_Stage_Summary 0.1 MB each. The packaged workbook is 23.2 MB.

## Validation (19/19)

| Check | Result |
|---|---|
| Source CSVs unchanged (MD5 = manifests, 14 files) | PASS |
| All 6 `.hyper` files exist; each opens and can be queried with the Hyper API | PASS |
| Each `.hyper` holds exactly its data source's tables | PASS |
| Row counts: extract = CSV = manifest, 14 tables | PASS |
| Column names, order and types = CSV header and the workbook's declared types | PASS |
| Every value of every column equals the CSV, NULLs included | PASS |
| Eligible revenue computed inside the extract = BRL 13,494,400.74 | PASS |
| Cohort extract keeps the 190 unobserved (blank) cells | PASS |
| `RetailPulse_Final.twb` and `.twbx` exist | PASS |
| Every extract reference resolves: 6 absolute paths in the `.twb`, 6 package members in the `.twbx` | PASS |
| No live CSV connection remains | PASS |
| Every table the workbook references exists in its `.hyper` | PASS |
| `<SortTagCleanup />` declared: no `manual-sort` error | PASS |
| 6 data sources + Parameters, 8 relationships, 8 worksheets, 2 parameters | PASS |
| 100 calculated fields, formulas identical to the validated registry | PASS |
| Identical to `RetailPulse_repaired.twb` apart from the connection layer | PASS |
| Valid against Tableau's official 2026.3 XSD | PASS (the optional `<explain-data>` rule waived, as Tableau's own files omit it) |
| Every element/attribute name also occurs in workbooks written by Tableau | PASS |

**The value comparison was shown to catch errors.** In a test it flagged a 0.01 change to one
value, one blank cohort cell set to 0, and one dropped row.

## Tested in Tableau afterwards

`RetailPulse_Final.twbx` was then opened in Tableau Desktop Public Edition 2026.3.2 by
`tableau/scripts/tableau_runtime_check.py`. It opened without the extract error 3C242D89, all six
extracts connected, and all 8 KPI sheets rendered with the validated values. That test found two issues
(a `[:Measure Names]` declaration and a cross-table LOD in N07), and both were fixed. Details are in
`reports/tableau_validation_report.md`. Saving to Tableau Public needs your Tableau Public sign-in, so
it has not been done.
