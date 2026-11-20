# RetailPulse — Power BI Completion Checklist

**Status (2026-11-20): NOT STARTED in Power BI.** Nothing below can be ticked
on macOS. Tick each item only after checking it in **Power BI Desktop on
Windows**, and note the evidence (value seen, screenshot name).
Procedure: [`windows_implementation_guide.md`](windows_implementation_guide.md) ·
design: [`dashboard_specification.md`](dashboard_specification.md) ·
measures: [`dax_implementation_checklist.md`](dax_implementation_checklist.md).

Legend: ☐ to do · ☑ done (with evidence)

---

## 0. Readiness verified on macOS (2026-11-20)

| Check | Result |
|---|---|
| 20 CSV sources readable; row and column counts = manifests; analytical MD5 = manifest | ✅ |
| View extracts' row counts = live MySQL | ✅ |
| All 62 `Table[column]` references in the 84 measures exist in the CSVs | ✅ |
| Primary keys unique and non-null in all 20 tables | ✅ |
| 10 relationships: one side unique, 0 orphans, 0 blank keys | ✅ |
| `dim_date` contiguous 2016-09-04 … 2018-10-17 (774 days); `order_date` inside it; `MonthIndex` correct; 608 stable-window days | ✅ |
| Blanks as designed: 190 unobserved cohort cells; 4,795 pre-arrival reviews flagged; 1,113 unscored RFM rows | ✅ |
| Eligible revenue BRL 13,494,400.74 identical in 7 sources and live MySQL (no multiplication) | ✅ |
| IDs intact as 32-character hex; zip prefixes 5 characters; 19 flag columns 0/1 | ✅ |
| Every `[measure]` named in the specification is among the 84 | ✅ (47 of 47) |
| `scripts/validate_powerbi_sources.py` / `validate_dax_logic.py` | ✅ 90/90 · 230/230 (logic only, not Power BI runtime) |

## 1. Environment and import

| Item | ☐/☑ | Evidence |
|---|---|---|
| Power BI Desktop installed (record version) | ☐ | |
| `powerbi/` copied with `data/` and `data/analytical/`; counts match manifests | ☐ | |
| 20 tables imported with US-English locale; types set per guide §1 | ☐ | |
| Row counts after load match manifests | ☐ | |
| Refresh completes with no errors or warnings | ☐ | |

## 2. Model

| Item | ☐/☑ | Evidence |
|---|---|---|
| Auto date/time off | ☐ | |
| 10 relationships exactly as guide §2; all one-to-many, single direction | ☐ | |
| The four auto-detected one-to-one relationships changed to many-to-one | ☐ | |
| No extra auto-created relationships; none inactive; no ambiguity warning | ☐ | |
| `dim_date` marked as the date table | ☐ | |
| Sort-by: `MonthName`→`MonthNo`; `stage`→`stage_order`; `delivery_bucket`→`Delivery Bucket Order` | ☐ | |
| "Don't summarize" on IDs, scores and helper columns | ☐ | |

## 3. Measures and KPI cards

| Item | ☐/☑ | Evidence |
|---|---|---|
| All 84 measures entered in `_Measures` (count shown in the model view) | ☐ | |
| 84 / 84 with no syntax error | ☐ | |
| 84 / 84 test values match `dax_implementation_checklist.md` | ☐ | |
| Spec-gap measures (guide §4): approved? added to `dax_measures.md` and validator? | ☐ | |

**Card values (unfiltered):**

| Page | Card | Expected | Seen | ☐/☑ |
|---|---|---|---|---|
| 1 | Total Revenue | BRL 13,494,400.74 | | ☐ |
| 1 | Total Orders | 99,441 | | ☐ |
| 1 | Total Customers | 96,096 | | ☐ |
| 1 | Average Order Value | BRL 137.42 | | ☐ |
| 1 | Median Order Value | BRL 86.90 | | ☐ |
| 1 | YoY Growth Jan-Aug % | 138.28% | | ☐ |
| 2 | Total People | 96,096 | | ☐ |
| 2 | Repeat Purchase Rate | 3.12% | | ☐ |
| 2 | One-Time Customers | 93,099 | | ☐ |
| 2 | Avg Orders Per Customer | 1.03 (1.0348) | | ☐ |
| 2 | Historical Customer Value | BRL 13,494,400.74 | | ☐ |
| 3 | Category Revenue | BRL 13,494,400.74 | | ☐ |
| 3 | Distinct Categories | 74 | | ☐ |
| 3 | Category Items Sold | 112,101 | | ☐ |
| 3 | Top Category Revenue | BRL 1,255,695.13 | | ☐ |
| 4 | Sellers With Revenue | 3,053 | | ☐ |
| 4 | Seller Revenue | BRL 13,494,400.74 | | ☐ |
| 4 | Largest Seller Share | 1.70% | | ☐ |
| 4 | Seller Avg Delivery Days | 12.51 | | ☐ |
| 4 | Seller Late Rate | 8.02% | | ☐ |
| 5 | Delivered Orders | 96,478 | | ☐ |
| 5 | On-Time Delivery Rate | 91.89% (91.8871%) | | ☐ |
| 5 | Avg Delivery Days | 12.56 | | ☐ |
| 5 | Late Orders | 7,827 | | ☐ |
| 5 | Cancellation Rate | 0.63% | | ☐ |
| 5 | Total Freight | BRL 2,241,126.29 | | ☐ |
| 5 | Last Mile Share | 74.21% | | ☐ |
| 6 | Avg Review Score | 4.0864 | | ☐ |
| 6 | One-Star Rate | 11.51% | | ☐ |
| 6 | Five-Star Rate | 57.78% | | ☐ |
| 6 | Total Reviews | 99,224 | | ☐ |
| 6 | Pre-Delivery Reviews | 4,795 | | ☐ |

## 4. Pages (per `dashboard_specification.md`)

| Page | Visuals | Slicers / captions | ☐/☑ |
|---|---|---|---|
| Global | Header, left nav (6 buttons, current page highlighted), footer disclaimer on every page | — | ☐ |
| 1 Executive | Monthly revenue (line) + orders (column) on `dim_date[YearMonth]`, stable window · `[Revenue MoM %]` columns, green/red · revenue by state, top 12 · top 10 categories · YoY card | Slicers: Year, YearMonth range, customer_state, order_status · captions: top-3 states 63.4%; Jan–Aug like-for-like · top-10 categories interaction handled (guide §4) | ☐ |
| 2 Customers | One-time vs repeat donut (93,099 / 2,997) · RFM segments: customer share vs revenue share · value distribution (log) · cohort matrix `[Cohort Retention %]` · purchase frequency | Mandatory captions: ordinal F score; historical (not predicted) value; right-censoring · blank cells below the diagonal | ☐ |
| 3 Products | Revenue by category, top 15 · Pareto with 80% line · top-5 monthly trend · growth vs decline (2017 Q1 vs **Jun–Aug 2018**, ≥ 50 items) · category table | Category axes on `dim_category` · drill-through to category detail | ☐ |
| 4 Sellers | Top 20 sellers · concentration curve · scatter: late % × inherited rating, size = revenue, median lines · intervention table (≥ 100 orders, rating < 3.8) | Inherited-rating caption on scatter and table; ≥ 50 orders on rankings; late-rate subtitle (seller-order pairs) · drill-through to seller detail | ☐ |
| 5 Operations | Status distribution (log) · promised vs actual over time · state performance by late rate · delivery-time histogram + median · stage breakdown (0.40 / 2.85 / 9.36 days) | Captions: padded estimate; 74.2% carrier leg (95,088 orders); 96,476-order denominator; 12.62 vs 12.56 days labelled | ☐ |
| 6 Satisfaction | Score distribution 1–5 · delay vs score, both analyses (all reviews / after arrival) · monthly trend, stable window · category best/worst (≥ 300 items) | Association-not-causation caption; pre-arrival note; "whole order, not product quality alone" | ☐ |
| Drill-through | Category detail page · seller detail page (guide §7) | Back button | ☐ |

## 5. Interaction tests (guide §6–7)

| Test | Expected | Seen | ☐/☑ |
|---|---|---|---|
| YearMonth = 2017-11 → Total Revenue | value in `dax_validation_results.csv` (M01, "month = 2017-11") | | ☐ |
| customer_state = SP → Total Revenue | M01 "customer_state = SP" | | ☐ |
| customer_state = SP → Last Mile Share | N22 "customer_state = SP" | | ☐ |
| seller_state = SP → Seller Late Rate | 8.67% | | ☐ |
| health_beauty → Category Revenue Share / Rank | 9.31% / 1 | | ☐ |
| Revenue MoM % at 2017-01 | BLANK | | ☐ |
| Revenue 3M Moving Avg at 2017-03 | BRL 244,466.31 (BLANK for 2017-01/02) | | ☐ |
| Cohort matrix grand total | BLANK | | ☐ |
| Drill-through health_beauty | revenue BRL 1,255,695.13; 8,826 reviews; avg 4.1822 | | ☐ |
| Drill-through largest seller | late 11.57%; delivery 15.06 days; rating 4.136 | | ☐ |

## 6. Formatting and accessibility

| Item | ☐/☑ |
|---|---|
| `RetailPulse_Theme.json` applied on every page | ☐ |
| Currency BRL (R$ symbol), thousands separator, 2 dp | ☐ |
| No dual-axis comparisons; no gauges, 3-D or extra pies | ☐ |
| Alt text on every visual; colour never the only signal | ☐ |
| Conditional formatting (late rate, review score) green/amber/red | ☐ |

## 7. Deliverables

| Item | ☐/☑ | Evidence |
|---|---|---|
| `powerbi/RetailPulse.pbix` saved; size checked (< 100 MB for GitHub) | ☐ | |
| 8 screenshots in `reports/dashboard_screenshots/` (names in guide §9) | ☐ | |
| README dashboard section updated with the real screenshots | ☐ | |
| `documentation/project_completion_checklist.md` §4 updated | ☐ | |
