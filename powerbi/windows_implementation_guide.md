# RetailPulse — Power BI Windows Implementation Guide

**Purpose:** the ordered procedure to build, test and capture the RetailPulse
dashboard in **Power BI Desktop on Windows**, using the validated assets in
this folder. Nothing here has been executed yet: the project machine is macOS
15.8.1 (Apple Silicon) with no Power BI Desktop or Windows environment
(checked 2026-11-20).

| Prepared on macOS (done) | Requires Windows (outstanding) |
|---|---|
| 20 CSV data sources, data-readiness checks 30/30 | Import into Power BI Desktop |
| Data model design (`data_model.md`) | Relationships, date table, sort-by columns |
| 84 DAX measures, logic checks 230/230 | Entering the measures; syntax and runtime check |
| Six-page specification, theme JSON | Building the pages, applying the theme |
| Expected values for every measure | Comparing card values in Power BI |
| — | Slicer, cross-filter and drill-through tests; screenshots; saving the `.pbix` |

Companion files: [`dax_implementation_checklist.md`](dax_implementation_checklist.md)
(84 measures in entry order) · [`powerbi_completion_checklist.md`](powerbi_completion_checklist.md)
(page-by-page acceptance) · [`dashboard_specification.md`](dashboard_specification.md)
(source of truth for the design) · [`data_model.md`](data_model.md) ·
[`analytical_sources.md`](analytical_sources.md).

---

## 0. Prerequisites

1. A Windows 10/11 machine or VM with **Power BI Desktop** (free, Microsoft
   Store or download). Note the version for the test log.
2. Copy the whole `powerbi/` folder from the Mac, **including `data/` and
   `data/analytical/`** (about 77 MB). These CSVs are git-ignored, so a fresh
   clone does not contain them: zip the folder on the Mac, or regenerate it on
   a machine with MySQL access (`scripts/export_powerbi_data.py` and
   `scripts/export_powerbi_sources.py`, then
   `scripts/validate_powerbi_sources.py`, 90/90).
3. Confirm the copy: the row and column counts must match
   `data/_manifest.csv` and `data/analytical/_manifest.csv`. The analytical
   files' MD5 checksums are in their manifest.
4. **MySQL is not needed** for the CSV route. Do not connect Power BI to MySQL
   as root; if you choose a live connection, use the read-only
   `retailpulse_app` account (see `documentation/mysql_setup.md`).

## 1. Import the data (Get Data ▸ Text/CSV)

Import these **20 tables**, keeping each file name as the table name
(the DAX refers to these exact names):

| Folder | Tables |
|---|---|
| `data/` | `vw_order_summary`, `vw_customer_summary`, `vw_review_summary`, `vw_category_performance`, `vw_seller_performance`, `vw_delivery_performance`, `vw_monthly_revenue`, `dim_date`, `sellers`, `products`, `product_category_translation` |
| `data/analytical/` | `rfm_customer_segments`, `cohort_retention`, `product_performance`, `seller_category_performance`, `delivery_stage_orders`, `delivery_stage_summary`, `category_satisfaction`, `seller_scorecard`, `dim_category` |

Do not import the `_manifest.csv` files. `sellers`, `products`,
`product_category_translation` and `vw_monthly_revenue` are optional lookups:
no measure uses them, and `vw_monthly_revenue`'s MoM and moving-average
columns are known to be wrong around 2016/2017 (use the DAX measures).

**In Power Query, before loading:**

- **File origin / locale:** set *Locale = English (United States)* (or *Using
  locale…* on type changes). The CSVs use `.` as the decimal separator; a
  comma-decimal Windows locale will otherwise misread money and day values.
- **Types:**

| Set to | Columns |
|---|---|
| **Text** | every `*_id`, `customer_unique_id`, `order_month`, `YearMonth`, `cohort_month`, `activity_month`, `category`, `category_portuguese`, `product_category_name*`, `*_state`, `*_city`, `seller_zip_code_prefix` (keeps leading zeros), `rfm_code`, `rfm_segment`, `delivery_bucket`, `sentiment_band`, `order_status`, `stage`, `Quarter`, `MonthName`, `DayOfWeek` |
| **Date** | `dim_date[Date]`, `vw_order_summary[order_date]`, `*_purchase_date`, `first_*`/`last_*` date columns |
| **Date/Time** | `vw_review_summary[review_creation_date]` |
| **Fixed decimal (currency, BRL)** | `order_revenue`, `order_freight`, `payment_total`, `historical_value`, `avg_order_value`, `revenue`, `freight`, `avg_item_price`, `avg_order_revenue`, `product_revenue`, `freight_value`, `avg_freight_value`, `monetary_value` |
| **Whole number** | counts and 0/1 flags (`revenue_eligible`, `is_late`, `delivery_measurable`, `stage_timing_valid`, `rfm_scored`, `is_observed`, `review_before_delivery`, …), `*_seconds`, `months_since_acquisition`, scores `r_score`/`f_score`/`m_score`, `MonthIndex`, `YearMonthSort` |
| **True/False** | `dim_date[InStableWindow]` |
| Decimal number | remaining averages, rates and day values |

- **Blanks stay blank.** Do not replace nulls in `cohort_retention`
  (190 unobserved cells), `review_before_delivery` (undelivered orders) or
  the RFM score columns (1,113 unscored people).

**Check after load:** row counts per table equal the manifests (e.g.
`vw_order_summary` 99,441; `delivery_stage_orders` 95,088;
`cohort_retention` 400).

## 2. Configure the model

1. *File ▸ Options ▸ Current file ▸ Data load:* **turn off Auto date/time**
   (the model has its own date table).
2. Create these **10 relationships**, all **single cross-filter direction**,
   **one-to-many** (one side first):

| # | One side | Many side | Note |
|---|---|---|---|
| 1 | `dim_date[Date]` | `vw_order_summary[order_date]` | |
| 2 | `vw_order_summary[order_id]` | `vw_review_summary[order_id]` | 547 orders have 2–3 reviews: never 1:1 |
| 3 | `vw_customer_summary[customer_unique_id]` | `vw_order_summary[customer_unique_id]` | |
| 4 | `vw_customer_summary[customer_unique_id]` | `rfm_customer_segments[customer_unique_id]` | set **manually to one-to-many** |
| 5 | `vw_order_summary[order_id]` | `delivery_stage_orders[order_id]` | set **manually to one-to-many** |
| 6 | `vw_seller_performance[seller_id]` | `seller_scorecard[seller_id]` | set **manually to one-to-many** |
| 7 | `dim_category[category]` | `vw_category_performance[category]` | |
| 8 | `dim_category[category]` | `product_performance[category]` | |
| 9 | `dim_category[category]` | `seller_category_performance[category]` | |
| 10 | `dim_category[category]` | `category_satisfaction[category]` | set **manually to one-to-many** |

   Power BI auto-detects 4, 5, 6 and 10 as one-to-one (both keys are unique).
   **A one-to-one relationship always filters in both directions**, so change
   each to *Many to one (\*:1)* from the many side, single direction. The DAX
   assumes single direction.
   **Delete any relationship Power BI auto-creates that is not in this table**
   (e.g. on `seller_id` between `seller_category_performance` and
   `vw_seller_performance`, or `customer_state`).
   There are **no inactive relationships** in this design. The filter graph is
   a tree, so there are no ambiguous paths.
3. Leave unrelated: `cohort_retention`, `delivery_stage_summary`,
   `vw_delivery_performance`, `vw_monthly_revenue`, `sellers`, `products`,
   `product_category_translation`.
4. **Mark `dim_date` as the date table** (*Table tools ▸ Mark as date table ▸
   `Date`*).
5. **Sort-by columns:** `dim_date[MonthName]` by `MonthNo`;
   `delivery_stage_summary[stage]` by `stage_order`.
6. **Delivery-bucket order.** `delivery_bucket` would sort alphabetically, so
   add this **calculated column** to `vw_review_summary` and set
   `delivery_bucket` → *Sort by column* → `Delivery Bucket Order`:

   ```dax
   Delivery Bucket Order =
   SWITCH ( vw_review_summary[delivery_bucket],
            "15+ days early", 1, "7-15 days early", 2, "on time", 3,
            "1-7 days late", 4, "8-15 days late", 5, "15+ days late", 6,
            "not delivered", 7 )
   ```

   This is a display helper, not a metric. The labels were checked against
   the data on 2026-11-20 (7 values).
7. **Don't summarize** on every ID, score, `months_since_acquisition`,
   `retention_pct`, `MonthIndex`, `YearMonthSort`, year and month columns.
8. Hide technical columns from report view (keys on the many side,
   `*_seconds`, `MonthIndex`, `YearMonthSort`).

## 3. Create the 84 measures

1. *Home ▸ Enter data* → an empty table named **`_Measures`**; delete its
   placeholder column after the first measure exists.
2. Work down [`dax_implementation_checklist.md`](dax_implementation_checklist.md)
   **in its entry order**: each measure appears after the ones it uses. Copy
   the formatted DAX from [`dax_measures.md`](dax_measures.md).
3. After each measure: no red error bar → tick *Syntax OK*. Set the format
   string from the checklist.
4. When all 84 exist, test each unfiltered value on a scratch page with a card
   (or a table of measures) against *Test value*. Tick *Value OK* only on an
   exact match (to the cent for BRL; to the shown decimals otherwise).
5. Record any mismatch with the measure ID, the Power BI value and the
   expected value. **Do not change a formula to make a number match** without
   tracing why; the expected values come from independent SQL.

## 4. Build the six pages

Follow [`dashboard_specification.md`](dashboard_specification.md) visual by
visual, using the acceptance list in
[`powerbi_completion_checklist.md`](powerbi_completion_checklist.md). Notes
from the 2026-11-20 inspection:

- **Category axes and slicers:** use `dim_category[category]`.
- **Page 1 "Top 10 categories"** uses `vw_category_performance`, which is
  **not related to `dim_date`**. The page's date slicers will not filter it.
  Either set *Edit interactions → none* and caption it "all periods", or add
  `vw_category_performance[order_month]` as a visual filter matched to the
  slicer. Do not create a relationship (it would be many-to-many).
- **Page 2 KPIs** are lifetime figures (date slicers do not reach
  `vw_customer_summary`): caption as specified.
- **Page 4 late-rate card** reads 8.02% (seller-order pairs), not the Page 5
  8.11%: subtitle as specified.
- **Page 6 delay-vs-score:** axis `vw_review_summary[delivery_bucket]`
  (sorted by `Delivery Bucket Order`), filter out `not delivered`.

### Spec gaps: visuals without a measure among the 84

Four visuals in the specification need a calculation the 84 measures do not
provide. Proposed DAX is below. These are **not** part of the 84, **not** in
`dax_measures.md`, and **not** checked by the validator. Add them only after
approval, then add them to `dax_measures.md` and `scripts/validate_dax_logic.py`.
Reference values were computed on 2026-11-20 from the same CSVs Power BI
imports, and they reproduce the published findings.

| Visual | Proposed DAX (unvalidated) | Reference value |
|---|---|---|
| Page 3 Pareto curve | `Category Cumulative Share = VAR Cur = [Category Revenue] VAR T = ADDCOLUMNS ( ALL ( dim_category[category] ), "@r", [Category Revenue] ) RETURN DIVIDE ( SUMX ( FILTER ( T, [@r] >= Cur ), [@r] ), SUMX ( T, [@r] ) )` — or a *visual calculation* `RUNNINGSUM` | top 10 = 62.4%; 18 categories reach 80% (Insight 7) |
| Page 3 growth vs decline | `Category Revenue 2017 Q1 = CALCULATE ( [Category Revenue], vw_category_performance[order_month] IN { "2017-01", "2017-02", "2017-03" } )`; `Category Revenue Jun-Aug 2018 = CALCULATE ( [Category Revenue], vw_category_performance[order_month] IN { "2018-06", "2018-07", "2018-08" } )`; growth = `DIVIDE ( Jun-Aug − Q1, Q1 )`, shown only where both periods have ≥ 50 items (`[Category Items Sold]` with the same filters) | 24 categories meet the floor; 22 grew, 2 shrank; `housewares` +532.2% |
| Page 4 concentration curve | as the Pareto, over `ALL ( vw_seller_performance[seller_id] )` with `[Seller Revenue]` | largest seller 1.70%; top 306 sellers (10% of 3,053, rounded up) = 67.50%, top 305 = 67.43% |
| Page 5 promised vs actual | `Avg Promised Days = CALCULATE ( AVERAGEX ( vw_order_summary, vw_order_summary[delivery_days] - vw_order_summary[delay_days] ), vw_order_summary[delivery_measurable] = 1 )`, beside `[Avg Delivery Days]` | 2017-01: 39.51 promised vs 12.65 actual; 2018-08: 15.19 vs 7.73 (Insight 10 shows 39.5 / 12.6 and 15.2 / 7.7) |

> **Label correction for the growth chart.** The specification says "2017 Q1
> vs 2018 Q3", but the analysis it reproduces (`sql/04` Q13, Insight 7)
> compares **June–August 2018**, the last three complete months, and labels it
> "2018_q3". Calendar Q3 would be July–September, and September 2018 holds 16
> orders. Title the chart "2017 Q1 vs Jun–Aug 2018".

## 5. Apply the theme

*View ▸ Themes ▸ Browse for themes ▸ `RetailPulse_Theme.json`*. Then set the
page background and the header, nav and footer layout from the
specification's *Global layout*.

## 6. Test slicers and cross-filtering

For each page, with the expected values in `dax_validation_results.csv`:

- Date slicer on `dim_date[YearMonth]` = 2017-11: `[Total Revenue]` must read
  the 2017-11 value (validator context "month = 2017-11").
- `customer_state` = SP: `[Total Revenue]`, `[Avg Delivery Days]`,
  `[Last Mile Share]` must match the "customer_state = SP" contexts.
- `seller_state` = SP on Page 4: `[Seller Late Rate]` = 8.67%.
- One category on Page 3 (`health_beauty`): `[Category Revenue Share]` 9.31%;
  `[Category Rank]` 1.
- Cohort matrix: blank (not 0) below the diagonal; column totals of
  `[Cohort Retention %]` match the "offset" contexts; grand total blank.
- Within-page cross-highlighting works; aggregate tables do not filter other
  pages (by design).

## 7. Test drill-through

- **Category detail page** (drill-through field `dim_category[category]`):
  monthly trend (`[Category Revenue]` by `vw_category_performance[order_month]`),
  top products (`product_performance`), top sellers
  (`seller_category_performance`), satisfaction (`category_satisfaction`
  measures). Drill from `health_beauty`: revenue 1,255,695.13 BRL; 8,826
  reviews; average 4.1822.
- **Seller detail page** (drill-through field `vw_seller_performance[seller_id]`):
  seller revenue, weighted rates (one seller returns its published values in
  `vw_seller_performance`), categories sold (`seller_category_performance`).

## 8. Check KPI cards

Every card in the specification has an expected value. Cards must match it,
and the same figure must appear in `dax_validation_results.csv`. Record the
results in `powerbi_completion_checklist.md` §3.

## 9. Save and capture

1. Save as **`powerbi/RetailPulse.pbix`**. Check its size before any commit:
   GitHub rejects files over 100 MB. If it is too large, publish screenshots
   only and keep the `.pbix` out of Git (state this in the README).
2. Screenshots at full-page size into `reports/dashboard_screenshots/`:
   `01_executive_overview.png`, `02_customer_intelligence.png`,
   `03_product_category.png`, `04_seller_performance.png`,
   `05_delivery_operations.png`, `06_customer_satisfaction.png`,
   `07_category_drillthrough.png`, `08_seller_drillthrough.png`. Take them
   unfiltered (default state), with captions visible.
3. Never edit screenshots to change values.

## 10. When the dashboard may be called complete

Only when **all** of these hold, with evidence in
`powerbi_completion_checklist.md`:

- the `.pbix` opens without errors and refreshes from the CSVs without warnings
- all 84 measures are entered, with no syntax errors, and their values match
- all six pages are built per the specification, with mandatory captions
- slicer, cross-filter and drill-through tests pass
- the screenshots are captured from the real file

Then update `README.md` (dashboard status and screenshots) and
`documentation/project_completion_checklist.md` §4.
