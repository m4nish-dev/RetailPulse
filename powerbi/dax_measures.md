# RetailPulse — DAX Measures

**Target:** Power BI Desktop (Windows) · Import mode · **84 measures**: the original 49 (M01–M49), audited and corrected, plus 35 for the analytical sources (N01–N35)
**Logic validation:** `scripts/validate_dax_logic.py`: **227 / 227 checks pass**, covering every measure ID (2026-11-20)
**Audit report:** [`dax_measure_audit.md`](dax_measure_audit.md): all 84 measures, what changed and the evidence
**Theme:** `RetailPulse_Theme.json`

---

## ⚠ What "validated" means here, precisely

`scripts/validate_dax_logic.py` checks every measure along **two independent paths**:

| Path | What it is |
|---|---|
| **Model** | The measure's logic emulated in pandas over the **exact CSVs Power BI imports**, including its filter behaviour (which filters it keeps or removes, where it returns BLANK) |
| **Expected** | The same business question answered in **SQL on the base tables**. No views, no exported sources, **no typed-in constants** |

Each measure is checked in one or more **filter contexts** (unfiltered, a month,
a state, a category, a seller, a segment, a cohort cell, an empty context).
**Bug-reproduction** checks evaluate each superseded formula and pass only if
they show it giving the wrong answer.

| | |
|---|---|
| ✅ **Verified** | the rows each measure reads, its denominator, its grain, which filters it respects, its BLANK behaviour, the arithmetic |
| ❌ **Not verified** | DAX syntax; that Power BI's engine evaluates the formula exactly as emulated; relationship settings; slicer interaction; visual totals; formatting |

**A PASS means "typed as written below, on the model in `data_model.md`, this
measure asks the right question of the right rows."** It does **not** mean the
measure has run in Power BI. That needs Windows and remains outstanding.

```bash
./venv/bin/python scripts/validate_dax_logic.py     # writes powerbi/dax_validation_results.csv
```

---

## Conventions

Measures live in a blank `_Measures` table. Each block below is tagged
`-- [ID]`; the validator fails if any tagged measure has no passing check.

| Rule | Why |
|---|---|
| **Revenue = item `price`, freight excluded, `revenue_eligible = 1`** | KPI 1. Every revenue path reconciles to 13,494,400.74 |
| **People are `customer_unique_id`** | `customer_id` is per order (99,441 vs 96,096) |
| **Delivery averages use `delivery_measurable = 1`** | 96,476, not the 96,478 marked delivered |
| **Delivery *stages* use `delivery_stage_orders`** | the 95,088 orders with a valid timestamp sequence (Q18) |
| **Month arithmetic uses `dim_date[MonthIndex]`** | contiguous month number; avoids `DATESINPERIOD`'s day-level windows and end-of-month edge cases |
| **Growth and moving averages need complete months** | return BLANK unless every month involved is in the stable window (2017-01 … 2018-08); Nov 2016 is missing and Dec 2016 holds 1 order |
| **Averages across groups are ratio-of-sums** | `SUM(numerator) / SUM(denominator)`, never `AVERAGE` of per-group rates, which gives every seller or product equal weight |
| **Non-additive values return BLANK at totals** | `SELECTEDVALUE` / `HASONEVALUE` guards where a plain sum would double-count |
| **Category axes use `dim_category[category]`** | the shared dimension filtering four category tables; share and rank measures remove its filter explicitly |
| **Reviews at review grain; pre-arrival reviews identifiable** | `review_before_delivery`; after-arrival variants provided |
| **`DIVIDE()`, never `/`** | BLANK instead of an error on divide-by-zero |
| **"Historical Customer Value", never "CLV"** | 3.12% repeat rate: no basis for prediction |
| **No profit or margin measures** | no cost data |

**Model prerequisites** (see `data_model.md`): `dim_date` marked as the date
table and carrying `MonthIndex`; `dim_category` related to the four category
tables; `seller_scorecard`, `rfm_customer_segments` and `delivery_stage_orders`
related **many-to-one, single direction** to their parent tables.

---

## Page 1 — Executive Business Overview

```dax
-- [M01] Total Revenue
Total Revenue =
CALCULATE ( SUM ( vw_order_summary[order_revenue] ), vw_order_summary[revenue_eligible] = 1 )
-- 13,494,400.74

-- [M02] Total Orders
Total Orders = COUNTROWS ( vw_order_summary )
-- 99,441

-- [M03] Total Customers
Total Customers = DISTINCTCOUNT ( vw_order_summary[customer_unique_id] )
-- 96,096 people (customer_id would give 99,441). Date-responsive: people who ordered in the period.

-- [M04] Orders With Items
Orders With Items = CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[item_count] > 0 )
-- 98,666

-- [M05] AOV Denominator
AOV Denominator =
CALCULATE ( COUNTROWS ( vw_order_summary ),
            vw_order_summary[revenue_eligible] = 1, vw_order_summary[item_count] > 0 )
-- 98,199 (eligible orders that have items)

-- [M06] Average Order Value
Average Order Value = DIVIDE ( [Total Revenue], [AOV Denominator] )
-- 137.42; Jan-Aug 2017 136.55, Jan-Aug 2018 137.14

-- [M07] Median Order Value
Median Order Value =
MEDIANX ( FILTER ( vw_order_summary,
                   vw_order_summary[revenue_eligible] = 1 && vw_order_summary[item_count] > 0 ),
          vw_order_summary[order_revenue] )
-- 86.90 (now computed independently; the old check compared 86.90 with itself)

-- [M08] Total Freight
Total Freight =
CALCULATE ( SUM ( vw_order_summary[order_freight] ), vw_order_summary[revenue_eligible] = 1 )
-- 2,241,126.29. Never added to revenue.
```

### Time intelligence — rewritten 2026-11-20

`dim_date` must be marked as the date table and carry `MonthIndex`
(Year × 12 + Month). Use these at **month** grain (`dim_date[YearMonth]` axis).

```dax
-- [M09] Revenue PM
Revenue PM =
VAR CurIdx = MAX ( dim_date[MonthIndex] )
RETURN
    IF ( HASONEVALUE ( dim_date[YearMonth] ),
         CALCULATE ( [Total Revenue], REMOVEFILTERS ( dim_date ), dim_date[MonthIndex] = CurIdx - 1 ) )
-- previous calendar month; BLANK where that month has no orders (e.g. 2016-12, because Nov 2016 is missing)

-- [M10] Revenue MoM %
Revenue MoM % =
VAR CurIdx = MAX ( dim_date[MonthIndex] )
VAR BothComplete =
    CALCULATE ( DISTINCTCOUNT ( dim_date[MonthIndex] ), REMOVEFILTERS ( dim_date ),
                dim_date[MonthIndex] IN { CurIdx - 1, CurIdx }, dim_date[InStableWindow] = TRUE () ) = 2
VAR Prev = [Revenue PM]
RETURN IF ( BothComplete, DIVIDE ( [Total Revenue] - Prev, Prev ) )
-- BLANK unless both months are complete. 2017-01 is BLANK (the old DATEADD version
-- reported +1,101,719% against Dec 2016's single 10.90 BRL order). 2017-11: +52.06%.

-- [M11] Revenue 3M Moving Avg
Revenue 3M Moving Avg =
VAR CurIdx = MAX ( dim_date[MonthIndex] )
VAR CompleteMonths =
    CALCULATE ( DISTINCTCOUNT ( dim_date[MonthIndex] ), REMOVEFILTERS ( dim_date ),
                dim_date[MonthIndex] > CurIdx - 3, dim_date[MonthIndex] <= CurIdx,
                dim_date[InStableWindow] = TRUE () )
VAR Rev3 =
    CALCULATE ( [Total Revenue], REMOVEFILTERS ( dim_date ),
                dim_date[MonthIndex] > CurIdx - 3, dim_date[MonthIndex] <= CurIdx )
RETURN IF ( HASONEVALUE ( dim_date[YearMonth] ) && CompleteMonths = 3, DIVIDE ( Rev3, 3 ) )
-- mean of three monthly totals. First value 2017-03 (244,466.31), last 2018-08 (863,389.97).
-- The old AVERAGEX(DATESINPERIOD(...)) averaged DAILY revenue: 30,716 instead of 921,468 at 2018-03.

-- [M12] Revenue Running Total
Revenue Running Total =
VAR LastDate = MAX ( dim_date[Date] )
RETURN CALCULATE ( [Total Revenue], FILTER ( ALLSELECTED ( dim_date ), dim_date[Date] <= LastDate ) )
-- respects page slicers (stable-window slicer: 2018-08 = 13,449,529.68; none: 2018-10 = 13,494,400.74).
-- The old ALLSELECTED ( dim_date[Date] ) kept a YearMonth axis filter, so each "running total" was one month.
```

> **⚠ No plain year-over-year measure.** 2016 holds 329 orders; full-year YoY
> would read about +13,600%. Use the like-for-like comparison:

```dax
-- [M13] Revenue 2017 Jan-Aug
Revenue 2017 Jan-Aug =
CALCULATE ( [Total Revenue], REMOVEFILTERS ( dim_date ), dim_date[Year] = 2017, dim_date[MonthNo] <= 8 )
-- 3,080,850.81. REMOVEFILTERS added: a page YearMonth slicer no longer blanks it.

-- [M14] Revenue 2018 Jan-Aug
Revenue 2018 Jan-Aug =
CALCULATE ( [Total Revenue], REMOVEFILTERS ( dim_date ), dim_date[Year] = 2018, dim_date[MonthNo] <= 8 )
-- 7,341,037.41

-- [M15] YoY Growth Jan-Aug %
YoY Growth Jan-Aug % =
DIVIDE ( [Revenue 2018 Jan-Aug] - [Revenue 2017 Jan-Aug], [Revenue 2017 Jan-Aug] )
-- +138.28%. Non-date filters still apply (SP: +166.28%).
```

---

## Page 2 — Customer Intelligence & Retention

```dax
-- [M16] Total People
Total People = COUNTROWS ( vw_customer_summary )
-- 96,096

-- [M17] Repeat Customers
Repeat Customers = CALCULATE ( COUNTROWS ( vw_customer_summary ), vw_customer_summary[total_orders] >= 2 )
-- 2,997

-- [M18] One-Time Customers
One-Time Customers = CALCULATE ( COUNTROWS ( vw_customer_summary ), vw_customer_summary[total_orders] = 1 )
-- 93,099

-- [M19] Repeat Purchase Rate
Repeat Purchase Rate = DIVIDE ( [Repeat Customers], [Total People] )
-- 3.12%

-- [M20] Avg Orders Per Customer
Avg Orders Per Customer = AVERAGE ( vw_customer_summary[total_orders] )
-- 1.0348

-- [M21] Historical Customer Value
Historical Customer Value = SUM ( vw_customer_summary[historical_value] )
-- 13,494,400.74. Label "Historical Customer Value", never "Lifetime Value" or "CLV".
```

> **⚠ Page 2 customer KPIs are lifetime figures.** `vw_customer_summary` sits on
> the *one* side of its relationship to the orders fact, so a **date slicer does
> not filter M16–M21** (state slicers do, via `customer_state`). Say so on the page.

### RFM — rewritten 2026-11-20 on `rfm_customer_segments`

The original two measures counted `vw_customer_summary`, which has no segment
column and cannot be filtered by one. Every segment would have shown 96,096.
Scores use tie-consistent quintiles and the ordinal F score; the RFM visual
must carry the Frequency caption.

```dax
-- [N01] RFM Scored Customers
RFM Scored Customers =
CALCULATE ( COUNTROWS ( rfm_customer_segments ),
            REMOVEFILTERS ( rfm_customer_segments[rfm_segment] ), rfm_customer_segments[rfm_scored] = 1 )
-- 94,983 (ignores the segment filter; denominator for shares)

-- [M22] Customers In Segment
Customers In Segment =
CALCULATE ( COUNTROWS ( rfm_customer_segments ), rfm_customer_segments[rfm_scored] = 1 )
-- Potential Loyalists 21,427 · At Risk 14,792 · Needs Attention 33,498 · Lost 23,420 · Champions 951 · Loyal 895

-- [M23] Segment Revenue Share
Segment Revenue Share =
DIVIDE ( SUM ( rfm_customer_segments[monetary_value] ),
         CALCULATE ( SUM ( rfm_customer_segments[monetary_value] ),
                     REMOVEFILTERS ( rfm_customer_segments[rfm_segment] ) ) )
-- Potential Loyalists 33.61%, At Risk 30.75%, Champions 2.31%. Other filters (e.g. state) are kept.

-- [N02] Segment Customer Share
Segment Customer Share = DIVIDE ( [Customers In Segment], [RFM Scored Customers] )

-- [N03] Segment Avg Historical Value
Segment Avg Historical Value =
DIVIDE ( CALCULATE ( SUM ( rfm_customer_segments[monetary_value] ), rfm_customer_segments[rfm_scored] = 1 ),
         [Customers In Segment] )
-- historical spend per person in the segment; not a prediction
```

### Cohort retention — new, on `cohort_retention`

Matrix: rows `cohort_month`, columns `months_since_acquisition`, values `[Cohort Retention %]`.

```dax
-- [N04] Cohort Customers
Cohort Customers =
CALCULATE ( SUM ( cohort_retention[cohort_customers] ), cohort_retention[months_since_acquisition] = 0 )
-- cohort size (2017-01: 764)

-- [N05] Cohort Retention %
Cohort Retention % =
IF ( HASONEVALUE ( cohort_retention[months_since_acquisition] ),
     DIVIDE ( SUM ( cohort_retention[active_customers] ),
              CALCULATE ( SUM ( cohort_retention[cohort_customers] ), cohort_retention[is_observed] = 1 ) ) )
-- cell (2017-01, 1) = 0.39%; UNOBSERVED cells = BLANK (never 0); a column total weights only the
-- cohorts that could be observed at that offset (offset 1: 0.506%, not 0.473% with the
-- right-censored 2018-08 cohort wrongly in the denominator); grand total = BLANK

-- [N06] Returning Customers
Returning Customers = SUM ( cohort_retention[returning_customers] )
-- BLANK at offset 0 and in unobserved cells
```

---

## Page 3 — Product & Category Analytics

Put **`dim_category[category]`** on category axes and slicers.

```dax
-- [M24] Category Revenue
Category Revenue = SUM ( vw_category_performance[revenue] )
-- 13,494,400.74; health_beauty 1,255,695.13

-- [M25] Category Items Sold
Category Items Sold = SUM ( vw_category_performance[items_sold] )
-- 112,101 eligible items

-- [M26] Distinct Categories
Distinct Categories = DISTINCTCOUNT ( vw_category_performance[category] )
-- 74

-- [M27] Category Revenue Share
Category Revenue Share =
DIVIDE ( [Category Revenue],
         CALCULATE ( [Category Revenue],
                     REMOVEFILTERS ( dim_category ), REMOVEFILTERS ( vw_category_performance[category] ) ) )
-- health_beauty 9.31%. The old ALL ( vw_category_performance[category] ) left the dim_category
-- filter in place: 100% for every category on a dim_category axis.

-- [M28] Category Rank
Category Rank =
IF ( HASONEVALUE ( dim_category[category] ),
     RANKX ( ALL ( dim_category[category] ), [Category Revenue], , DESC, DENSE ) )
-- all 74 ranks match. The old RANKX ( ALL ( vw_category_performance[category] ) ) ranked every category 1.

-- [N07] Top Category Revenue
Top Category Revenue = MAXX ( VALUES ( dim_category[category] ), [Category Revenue] )
-- 1,255,695.13 (health_beauty)
```

### Category drill-through — new

```dax
-- [N08] Product Revenue
Product Revenue = SUM ( product_performance[product_revenue] )
-- 13,494,400.74

-- [N09] Product Units Sold
Product Units Sold = SUM ( product_performance[units_sold] )
-- 112,101

-- [N10] Products Sold
Products Sold = CALCULATE ( COUNTROWS ( product_performance ), product_performance[units_sold] > 0 )
-- 32,729 of 32,951 products had an eligible sale

-- [N11] Product Avg Item Price
Product Avg Item Price = DIVIDE ( [Product Revenue], [Product Units Sold] )
-- 120.38 (weighted). AVERAGE ( avg_item_price ) would give 144.96, overweighting rarely sold expensive products.

-- [N12] Product Avg Freight Per Item
Product Avg Freight Per Item = DIVIDE ( SUM ( product_performance[freight_value] ), [Product Units Sold] )
-- 19.99: freight charged to the customer per item

-- [N13] Seller Category Revenue
Seller Category Revenue = SUM ( seller_category_performance[product_revenue] )
-- additive: rolls up to category and seller totals

-- [N14] Seller Category Items
Seller Category Items = SUM ( seller_category_performance[item_count] )
-- 112,101

-- [N15] Seller Category Late Rate
Seller Category Late Rate =
DIVIDE ( SUM ( seller_category_performance[late_orders] ),
         SUM ( seller_category_performance[delivery_measurable_orders] ) )
-- health_beauty 8.93%. Weighted; multi-seller orders count once per seller.

-- [N16] Seller Category Dispatch Days
Seller Category Dispatch Days =
DIVIDE ( SUMX ( seller_category_performance,
                seller_category_performance[dispatch_measurable_orders] * seller_category_performance[avg_dispatch_days] ),
         SUM ( seller_category_performance[dispatch_measurable_orders] ) )
-- approval -> carrier, single-seller orders with valid timing only (health_beauty 2.69 days)
```

`seller_category_performance[order_count]` is **not additive** (an order spans
pairs). There is deliberately no measure that sums it.

---

## Page 4 — Seller Performance

Rates come from **`seller_scorecard`** (counts and sums per seller, related to
`vw_seller_performance`). They are weighted by seller-order pairs, so a filter to
one seller returns exactly that seller's published rate, and a total is weighted
by volume instead of being the mean of 3,053 rates.

```dax
-- [M29] Seller Revenue
Seller Revenue = SUM ( vw_seller_performance[revenue] )
-- 13,494,400.74

-- [M30] Sellers With Revenue
Sellers With Revenue = COUNTROWS ( vw_seller_performance )
-- 3,053 (not 3,095: 42 had only canceled/unavailable orders)

-- [M31] Seller Orders
Seller Orders = SUM ( vw_seller_performance[orders_served] )
-- 99,542 seller-order PAIRS, not orders: a 2-seller order counts for each seller.
-- Use [AOV Denominator] (98,199) for an order count. Label: "Seller-order pairs".

-- [M32] Seller Avg Delivery Days
Seller Avg Delivery Days =
DIVIDE ( SUM ( seller_scorecard[delivery_days_sum] ), SUM ( seller_scorecard[delivery_measurable_orders] ) )
-- 12.51 weighted (old unweighted AVERAGE: 12.21)

-- [M33] Seller Late Rate
Seller Late Rate =
DIVIDE ( SUM ( seller_scorecard[late_orders] ), SUM ( seller_scorecard[delivery_measurable_orders] ) )
-- 8.02% weighted, as a fraction like every other rate. Old version: AVERAGE ( late_pct ) = 8.42, in percent units.

-- [M34] Largest Seller Share
Largest Seller Share =
DIVIDE ( MAXX ( VALUES ( vw_seller_performance[seller_id] ), [Seller Revenue] ),
         CALCULATE ( [Seller Revenue], ALL ( vw_seller_performance ) ) )
-- 1.70% of PLATFORM revenue (denominator ignores slicers by design)

-- [M35] Seller Inherited Order Rating
Seller Inherited Order Rating =
DIVIDE ( SUM ( seller_scorecard[review_score_sum] ), SUM ( seller_scorecard[reviewed_orders] ) )
-- 4.099 weighted (old unweighted: 4.055)
```

> **⚠ Seller 8.02% vs platform 8.11% — both correct, different grain.** The
> platform rate counts each order once. The seller rate counts each
> seller-order pair, so the 1,277 multi-seller orders count once per seller,
> and those orders were late only 1.38% of the time (single-seller: 8.20%).
> Label the Page 4 card "late rate across seller-order pairs".
>
> **⚠ "Inherited order rating", never "seller rating".** Reviews attach to the
> order; every seller in a multi-seller order inherits its score.

---

## Page 5 — Order & Delivery Operations

```dax
-- [M36] Delivered Orders
Delivered Orders = CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[is_delivered] = 1 )
-- 96,478

-- [M37] Delivery Denominator
Delivery Denominator =
CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[delivery_measurable] = 1 )
-- 96,476  <- use for every delivery average

-- [M38] Late Orders
Late Orders =
CALCULATE ( SUM ( vw_order_summary[is_late] ), vw_order_summary[delivery_measurable] = 1 )
-- 7,827

-- [M39] Late Delivery Rate
Late Delivery Rate = DIVIDE ( [Late Orders], [Delivery Denominator] )
-- 8.11%

-- [M40] On-Time Delivery Rate
On-Time Delivery Rate = DIVIDE ( [Delivery Denominator] - [Late Orders], [Delivery Denominator] )
-- 91.89%. The old 1 - [Late Delivery Rate] returned 100% in any context with no deliveries (1 - BLANK = 1).

-- [M41] Avg Delivery Days
Avg Delivery Days =
CALCULATE ( AVERAGE ( vw_order_summary[delivery_days] ), vw_order_summary[delivery_measurable] = 1 )
-- 12.56 (96,476 orders)

-- [M42] Avg Delay Days
Avg Delay Days =
CALCULATE ( AVERAGE ( vw_order_summary[delay_days] ), vw_order_summary[delivery_measurable] = 1 )
-- -11.18 (negative = early)

-- [M43] Cancelled Orders
Cancelled Orders = CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[order_status] = "canceled" )
-- 625

-- [M44] Cancellation Rate
Cancellation Rate = DIVIDE ( [Cancelled Orders], [Total Orders] )
-- 0.63%
```

### Delivery stages — new, on `delivery_stage_orders` (95,088 orders)

Shares are ratio-of-sums of exact seconds.

```dax
-- [N17] Stage Orders
Stage Orders = COUNTROWS ( delivery_stage_orders )
-- 95,088

-- [N18] Purchase To Approval Days
Purchase To Approval Days =
DIVIDE ( SUM ( delivery_stage_orders[purchase_to_approval_seconds] ), [Stage Orders] * 86400 )
-- 0.40

-- [N19] Approval To Carrier Days
Approval To Carrier Days =
DIVIDE ( SUM ( delivery_stage_orders[approval_to_carrier_seconds] ), [Stage Orders] * 86400 )
-- 2.85

-- [N20] Carrier To Customer Days
Carrier To Customer Days =
DIVIDE ( SUM ( delivery_stage_orders[carrier_to_customer_seconds] ), [Stage Orders] * 86400 )
-- 9.36

-- [N21] Stage Total Days
Stage Total Days = DIVIDE ( SUM ( delivery_stage_orders[total_seconds] ), [Stage Orders] * 86400 )
-- 12.62 on 95,088 orders; differs from [Avg Delivery Days] 12.56 on 96,476 by population. Label both.

-- [N22] Last Mile Share
Last Mile Share =
DIVIDE ( SUM ( delivery_stage_orders[carrier_to_customer_seconds] ), SUM ( delivery_stage_orders[total_seconds] ) )
-- 74.21%

-- [N23] Dispatch Stage Share
Dispatch Stage Share =
DIVIDE ( SUM ( delivery_stage_orders[approval_to_carrier_seconds] ), SUM ( delivery_stage_orders[total_seconds] ) )
-- 22.60%

-- [N24] Approval Stage Share
Approval Stage Share =
DIVIDE ( SUM ( delivery_stage_orders[purchase_to_approval_seconds] ), SUM ( delivery_stage_orders[total_seconds] ) )
-- 3.19%
```

> **⚠ "On time" is measured against Olist's own padded estimate.** Caption the card.

---

## Page 6 — Customer Satisfaction

```dax
-- [M45] Total Reviews
Total Reviews = COUNTROWS ( vw_review_summary )
-- 99,224

-- [M46] Avg Review Score
Avg Review Score = AVERAGE ( vw_review_summary[review_score] )
-- 4.0864 (review grain)

-- [M47] One-Star Rate
One-Star Rate =
DIVIDE ( CALCULATE ( COUNTROWS ( vw_review_summary ), vw_review_summary[review_score] = 1 ), [Total Reviews] )
-- 11.51%  <- headline card beside the average

-- [M48] Five-Star Rate
Five-Star Rate =
DIVIDE ( CALCULATE ( COUNTROWS ( vw_review_summary ), vw_review_summary[review_score] = 5 ), [Total Reviews] )
-- 57.78%

-- [M49] Avg Order Rating
Avg Order Rating =
CALCULATE ( AVERAGE ( vw_order_summary[review_score_avg] ), vw_order_summary[review_count] > 0 )
-- 4.0868 (order grain; review_score_avg is stored to 4 dp)
```

> **⚠ 4.0864 (review grain) and 4.0868 (order grain) are different metrics.**
> 547 orders carry 2–3 reviews. Never give them the same label.

### Review timing (Q19) — new

```dax
-- [N25] Pre-Delivery Reviews
Pre-Delivery Reviews =
CALCULATE ( COUNTROWS ( vw_review_summary ), vw_review_summary[review_before_delivery] = 1 )
-- 4,795

-- [N26] Pre-Delivery Review Share
Pre-Delivery Review Share =
DIVIDE ( [Pre-Delivery Reviews],
         CALCULATE ( COUNTROWS ( vw_review_summary ), NOT ISBLANK ( vw_review_summary[review_before_delivery] ) ) )
-- 4.98% of reviews on delivered orders

-- [N27] Avg Review Score After Arrival
Avg Review Score After Arrival =
CALCULATE ( AVERAGE ( vw_review_summary[review_score] ), vw_review_summary[review_before_delivery] = 0 )
-- 4.279 (review grain)

-- [N28] One-Star Rate After Arrival
One-Star Rate After Arrival =
DIVIDE ( CALCULATE ( COUNTROWS ( vw_review_summary ), vw_review_summary[review_score] = 1,
                     vw_review_summary[review_before_delivery] = 0 ),
         CALCULATE ( COUNTROWS ( vw_review_summary ), vw_review_summary[review_before_delivery] = 0 ) )
-- 6.76%

-- [N35] Avg Order Rating (Review Table)
Avg Order Rating (Review Table) =
AVERAGEX ( VALUES ( vw_review_summary[order_id] ), CALCULATE ( AVERAGE ( vw_review_summary[review_score] ) ) )
-- order grain from the review table, so it can sit on a delivery_bucket axis.
-- Unfiltered 4.086793 (= M49 at full precision); 1-7 days late 3.184; 8-15 days late 1.733

-- [N34] Avg Order Rating After Arrival
Avg Order Rating After Arrival =
CALCULATE ( [Avg Order Rating (Review Table)], vw_review_summary[review_before_delivery] = 0 )
-- Insight 9's sensitivity view: 1-7 days late 3.860; 8-15 days late 3.660 (106 orders); on time 4.202
```

Delay-vs-score visual: axis `vw_review_summary[delivery_bucket]`, values
`[Avg Order Rating (Review Table)]` and `[Avg Order Rating After Arrival]` side
by side, with the association-not-causation caption.

### Category satisfaction — new, on `category_satisfaction`

Category rows are **not additive** (a multi-category order's reviews count in
each category), so these return BLANK unless exactly one category is in context.

```dax
-- [N29] Category Review Count
Category Review Count = SELECTEDVALUE ( category_satisfaction[review_count] )
-- health_beauty 8,826. A plain SUM at the total would give 99,273 (> 98,465 reviews that exist).

-- [N30] Category Avg Review Score
Category Avg Review Score = SELECTEDVALUE ( category_satisfaction[avg_review_score] )
-- review grain: health_beauty 4.1822, office_furniture 3.6175

-- [N31] Category One-Star Rate
Category One-Star Rate = DIVIDE ( SELECTEDVALUE ( category_satisfaction[one_star_pct] ), 100 )

-- [N32] Category Avg Score After Arrival
Category Avg Score After Arrival = SELECTEDVALUE ( category_satisfaction[avg_review_score_after_arrival] )

-- [N33] Category Pre-Delivery Review Share
Category Pre-Delivery Review Share = DIVIDE ( SELECTEDVALUE ( category_satisfaction[pct_reviews_before_delivery] ), 100 )
```

Caption: *"Reviews rate the whole order, delivery included — not product quality alone."*

---

## Measures deliberately NOT built

| Measure | Why not |
|---|---|
| Profit, Margin, COGS | No cost data |
| Customer Lifetime Value / predicted CLV | 3.12% repeat rate gives no basis for prediction |
| Full-year YoY Growth | 2016 has 329 orders (~+13,600%) |
| Seller Rating | Reviews are order-level → `Seller Inherited Order Rating` |
| Sum of `seller_category_performance[order_count]` | Not additive across pairs |
| Total of category review counts / scores | Not additive across categories |
| Customer Acquisition Cost, Return Rate | No marketing or returns data |
