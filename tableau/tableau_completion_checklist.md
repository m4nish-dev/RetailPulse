# RetailPulse — Tableau Completion Checklist

**Status (2026-11-27): preparation complete on macOS; dashboard NOT built yet.**
Tick a 🔲 item only after checking it in **Tableau Desktop Public Edition** or on the
published Tableau Public page. Write the evidence (value seen, screenshot name).
Procedure: [`mac_implementation_guide.md`](mac_implementation_guide.md) ·
design: [`dashboard_specification.md`](dashboard_specification.md) ·
formulas: [`calculated_fields.md`](calculated_fields.md).

Legend: ✅ done by Claude on macOS (evidence given) · 🔲 manual, to do in Tableau · ⚠ done with a documented limitation

---

## 1. Preparation done on macOS (no Tableau needed)

| Item | Status | Evidence |
|---|---|---|
| 14 CSV sources migrated to `tableau/data/` (5 views) and `tableau/data/analytical/` (9); re-export byte-identical; manifests with MD5 | ✅ | `check_tableau_data.py` 24/24 (files, MD5, keys, 8 relationships, blanks) |
| Analytical sources equal live SQL and an independent pandas rebuild | ✅ | `validate_tableau_sources.py` 90/90 |
| Data model designed: 6 data sources, 8 relationships, keys, grain, types, filter rules | ✅ | `data_model.md` |
| Field-rename list (28) generated from the CSV headers; no collisions | ✅ | `calculated_fields.md` § Field renames; static check |
| 90 approved measures (M01–M49, N01–N41) as Tableau calculated fields + 10 helpers + 2 parameters, each with a business definition | ✅ | `calculated_fields.md` (generated) |
| Every formula's `[field]` references exist after the renames; every field named in the specification exists | ✅ | `validate_tableau_calcs.py` static checks |
| Formula logic in Tableau semantics vs independent SQL: 223 reference contexts, 7 revenue fan-out guards, 10 drill-through/dashboard checks, 9 pitfalls | ✅ | `validate_tableau_calcs.py` **264/264** → `tableau_calc_validation_results.csv` |
| Documented difference: seller cumulative share at revenue ties (311 sellers, ≤ 0.0201 pp, first at position 865) | ⚠ | pitfall P08; spec values unaffected |
| Dashboard specification: 6 + 2 dashboards, 47 sheets, captions, actions, test values | ✅ | `dashboard_specification.md` |
| Beginner Mac guide (install → publish → screenshots, with glossary) | ✅ | `mac_implementation_guide.md` |
| Publishing workflow and privacy researched (Tableau help pages) | ✅ | guide §11–12; `README.md` § Sources |
| **Workbook generated**: `tableau/RetailPulse.twb` with 6 data sources, 2 folder connections, 8 relationships, captions (incl. 28 renames), data types and roles, 2 parameters, 100 calculated fields with formats, 8 KPI check sheets; plus `RetailPulse_model_only.twb` as fallback | ✅ | `scripts/build_tableau_workbook.py` |
| Workbook valid against Tableau's official 2026.3 XSD; formulas identical to the validated registry; types hold for every CSV value; relationships and captions as documented; deterministic | ✅ | `scripts/validate_tableau_workbook.py` **15/15** (structure; not a Tableau runtime test) |
| Data, extracts, workbooks git-ignored; repository checks pass | ✅ | `.gitignore`; `scripts/check_repository.py` |

## 2. Install and open the generated workbook

| Item | ☐/☑ | Evidence |
|---|---|---|
| ✅ Tableau Desktop Public Edition 2026.3.2 installed (Apple silicon) | ☑ | owner, 2026-11-27 |
| 🔲 Tableau Public account created | ☐ | |
| 🔲 `tableau/RetailPulse.twb` opens without an error (guide §1A). If not: error text, and whether `RetailPulse_model_only.twb` opens | ☐ | |
| 🔲 Data Source tab: six data sources `RP Orders`, `RP Customers`, `RP Cohorts`, `RP Categories`, `RP Sellers`, `RP Stage Summary`, with the relationships of `data_model.md` §3 | ☐ | |
| 🔲 Row counts in the data preview equal the manifests: 99,441 · 99,224 · 95,088 · 96,096 · 96,096 · 400 · 74 · 1,282 · 32,951 · 74 · 3,053 · 3,053 · 6,545 · 4 | ☐ | |
| 🔲 Saved as `tableau/RetailPulse_build.twbx` (git-ignored) | ☐ | |

## 3. Model (generated; confirm in Tableau)

| Item | ☐/☑ | Evidence |
|---|---|---|
| ✅ 8 relationships, defaults for performance options, no physical joins | generated | `validate_tableau_workbook.py` |
| ✅ Field names = CSV names; 28 duplicates captioned with their documented new names | generated | `validate_tableau_workbook.py` |
| ✅ Data types (`order_date` Date; `order_month`, `cohort_month`, IDs String) | generated | type inference equal to Tableau's own on 60 columns |
| ✅ 2 parameters (`p_category` = health_beauty, `p_seller` = 4869f7a5…) | generated | |
| 🔲 Spot-check in Tableau: one relationship's matching fields, one renamed field (`rev_order_id`), `order_month` shown as text | ☐ | |

## 4. Calculated fields and KPI values (runtime test)

| Item | ☐/☑ | Evidence |
|---|---|---|
| ✅ 100 calculated fields (90 measures + 10 helpers) with BRL / % / number formats | generated | |
| 🔲 No calculated field shows a red error mark in the Data pane; `Revenue MoM %` editor says "The calculation is valid." | ☐ | list any errors in §5 |
| 🔲 KPI check sheets 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 5.6, 6.0 show the values below | ☐ | |

**Card values, no filters** (expected values validated on macOS):

| Dashboard | Card | Expected | Seen | ☐/☑ |
|---|---|---|---|---|
| 1 | Total Revenue | R$ 13,494,400.74 | | ☐ |
| 1 | Total Orders | 99,441 | | ☐ |
| 1 | Total Customers | 96,096 | | ☐ |
| 1 | Average Order Value | R$ 137.42 | | ☐ |
| 1 | Median Order Value | R$ 86.90 | | ☐ |
| 1 | YoY Growth Jan-Aug % | 138.28% | | ☐ |
| 2 | Total People | 96,096 | | ☐ |
| 2 | Repeat Purchase Rate | 3.12% | | ☐ |
| 2 | One-Time Customers | 93,099 | | ☐ |
| 2 | Avg Orders Per Customer | 1.0348 | | ☐ |
| 2 | Historical Customer Value | R$ 13,494,400.74 | | ☐ |
| 3 | Category Revenue | R$ 13,494,400.74 | | ☐ |
| 3 | Distinct Categories | 74 | | ☐ |
| 3 | Category Items Sold | 112,101 | | ☐ |
| 3 | Top Category Revenue | R$ 1,255,695.13 | | ☐ |
| 4 | Sellers With Revenue | 3,053 | | ☐ |
| 4 | Seller Revenue | R$ 13,494,400.74 | | ☐ |
| 4 | Largest Seller Share | 1.70% | | ☐ |
| 4 | Seller Avg Delivery Days | 12.51 | | ☐ |
| 4 | Seller Late Rate | 8.02% | | ☐ |
| 5 | Delivered Orders | 96,478 | | ☐ |
| 5 | On-Time Delivery Rate | 91.89% | | ☐ |
| 5 | Avg Delivery Days | 12.56 | | ☐ |
| 5 | Late Orders | 7,827 | | ☐ |
| 5 | Cancellation Rate | 0.63% | | ☐ |
| 5 | Total Freight | R$ 2,241,126.29 | | ☐ |
| 5 | Last Mile Share | 74.21% | | ☐ |
| 6 | Avg Review Score | 4.0864 | | ☐ |
| 6 | One-Star Rate | 11.51% | | ☐ |
| 6 | Five-Star Rate | 57.78% | | ☐ |
| 6 | Total Reviews | 99,224 | | ☐ |
| 6 | Pre-Delivery Reviews | 4,795 | | ☐ |

## 5. Formula problems found in Tableau (fill in if any)

| Field ID | Error message or wrong value | Cause found | Fix applied (and validator re-run?) |
|---|---|---|---|
| | | | |

## 6. Worksheets, dashboards and interactions

| Item | ☐/☑ | Evidence |
|---|---|---|
| 🔲 39 chart/table worksheets built per the specification (the 8 KPI sheets already exist) | ☐ | |
| 🔲 Dashboard 1 Executive (sheets 1.0–1.5, filters, YoY excluded from date filters) | ☐ | |
| 🔲 Dashboard 2 Customers (2.0–2.5, three mandatory captions) | ☐ | |
| 🔲 Dashboard 3 Products (3.0–3.5, two actions) | ☐ | |
| 🔲 Dashboard 4 Sellers (4.0–4.4, inherited-rating caption, two actions) | ☐ | |
| 🔲 Dashboard 5 Operations (5.0–5.6, three captions) | ☐ | |
| 🔲 Dashboard 6 Satisfaction (6.0–6.4, correlation caption) | ☐ | |
| 🔲 Detail 7 Category Detail (context filters; TC filter on 7.1; back button) | ☐ | |
| 🔲 Detail 8 Seller Detail (TC filter on 8.1; back button) | ☐ | |
| 🔲 Navigation column on the 6 main dashboards; footer with licence attribution on all 8 | ☐ | |

| Test | Expected | Seen | ☐/☑ |
|---|---|---|---|
| Order Month = 2017-11 → Total Revenue | R$ 1,003,862.14 | | ☐ |
| customer_state = SP → Total Revenue | R$ 5,163,867.22 | | ☐ |
| customer_state = SP → YoY Growth Jan-Aug % | 166.28% | | ☐ |
| customer_state = SP → Last Mile Share | 63.78% | | ☐ |
| customer_state = SP → Total Reviews | 41,690 | | ☐ |
| customer_state = SP (Customers) → Historical Customer Value | R$ 5,162,518.20 | | ☐ |
| seller_state = SP → Seller Late Rate | 8.67% | | ☐ |
| Order Month = 2018-03 → Late Delivery Rate | 21.36% | | ☐ |
| order_status = unavailable → Late / On-Time rate | **blank** (not 0% / 100%) | | ☐ |
| Revenue MoM % at 2017-01 | **blank**; 2017-11 = 52.06% | | ☐ |
| Revenue 3M Moving Avg | blank 2017-01/02; 2017-03 = R$ 244,466.31 | | ☐ |
| Running total, stable-window filter, at 2018-08 | R$ 13,449,529.68 | | ☐ |
| Cohort cell (2017-01, 1) / (2018-07, 2) | 0.39% / **blank** | | ☐ |
| RFM Potential Loyalists: customer share / revenue share | 22.56% / 33.61% | | ☐ |
| Pareto: 10th category / first to reach 80% | 62.37% / 18th | | ☐ |
| Concentration curve: seller 1 / 305 / 306 | 1.70% / 67.43% / 67.50% | | ☐ |
| Category growth: categories shown / grew; housewares | 24 / 22; +532.22% | | ☐ |
| Delay vs score, 1–7 days late (all / after arrival) | 3.184 / 3.860 | | ☐ |
| Intervention table rows | 21 | | ☐ |
| Drill: health_beauty | R$ 1,255,695.13 · 9.31% · rank 1 · +444.27% · 8,826 reviews · 4.1822 · 10.19% · 5.37% · seller late 8.93% | | ☐ |
| Drill: seller 4869f7a5… | R$ 229,237.63 · 1,131 · 11.57% · 15.06 days · 4.136 · 1.70% · 10 categories summing to R$ 229,237.63 | | ☐ |

## 7. Performance and formatting

| Item | ☐/☑ |
|---|---|
| 🔲 Each dashboard redraws in a few seconds (Extract connections) | ☐ |
| 🔲 Hide All Unused Fields run on each data source before publishing | ☐ |
| 🔲 BRL shown as `R$ 1,234.56`; percentages 2 dp | ☐ |
| 🔲 No dual axis for compared measures; no gauges/3-D; one pie/donut only | ☐ |
| 🔲 Values labelled where colour carries meaning (late rate, rating, growth) | ☐ |

## 8. Publication

| Item | ☐/☑ | Evidence |
|---|---|---|
| 🔲 Safety checklist done (guide §11): CSV connections only, nothing from `.env`, attribution footer | ☐ | |
| 🔲 Saved locally as `tableau/RetailPulse_build.twbx` (git-ignored) | ☐ | |
| 🔲 Published with Server ▸ Tableau Public ▸ Save to Tableau Public | ☐ | URL: |
| 🔲 Published view verified in a private browser window (guide §13) | ☐ | |

## 9. Screenshots and final documentation

| Item | ☐/☑ | Evidence |
|---|---|---|
| 🔲 `01_executive.png` … `08_seller_detail_largest_seller.png` (8 real captures) in `reports/dashboard_screenshots/` | ☐ | |
| 🔲 README dashboard section: Tableau Public link + screenshots | ☐ | |
| 🔲 `documentation/project_completion_checklist.md` §4 and `TASK_TRACKER.md` updated | ☐ | |
| 🔲 `scripts/run_all_validations.py` re-run: 0 FAIL | ☐ | |
| 🔲 Commit and push (you as the only author) | ☐ | |
