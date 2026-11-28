# RetailPulse — Tableau Dashboard Specification

Six dashboards and two detail (drill-through) dashboards, specified sheet by sheet so
the build is mechanical. Every sheet names the exact Tableau fields from
[`calculated_fields.md`](calculated_fields.md); every expected value is listed so each
card can be tested.

**Status (2026-11-28): built.** All sheets and the 8 dashboards are generated from code
(`scripts/tableau_charts.py` + `scripts/build_tableau_workbook.py`) into
`tableau/RetailPulse_Final.twbx` and tested in Tableau Desktop Public Edition 2026.3.2
(`tableau/scripts/tableau_runtime_check.py`; results in
[`reports/tableau_final_validation.md`](../reports/tableau_final_validation.md)). Where the
generated workbook differs from this specification (navigation buttons, parameter actions,
two-table data sources, a few chart details), the difference and the reason are listed in that
report. The specification below is kept as written; it remains the source of every expected value.
Every expected value below was computed on macOS. Each one comes from SQL on the base tables,
from the validated calculated-field emulation (`scripts/validate_tableau_calcs.py`, 264/264),
or, where marked *(CSV)*, from the validated CSVs with pandas.

Field and formula definitions: [`calculated_fields.md`](calculated_fields.md) ·
data sources: [`data_model.md`](data_model.md) ·
build steps: [`mac_implementation_guide.md`](mac_implementation_guide.md).

---

## Conventions

| Item | Rule |
|---|---|
| Sheet names | `<dashboard>.<n> <title>`, e.g. `1.1 Revenue and Orders by Month`. KPI sheets are `<dashboard>.0 KPIs` |
| Generated sheets | **1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 5.6 and 6.0 already exist** in the generated `tableau/RetailPulse.twb` (KPI strips built as described in the next row). Build the remaining 39 sheets by hand |
| KPI strip | One sheet per dashboard: **Columns** `Measure Names`; **Marks** = Text; **Text** `Measure Values`; **Filters** `Measure Names` = the listed KPIs. Each value uses its field's default number format |
| Currency | BRL: Currency (Custom), 2 decimals, prefix `R$ ` (set as each money field's default format) |
| Size | Dashboard ▸ Size ▸ Fixed size, **1400 × 1150** (main) and **1400 × 1000** (detail) |
| Layout | Header (title + "Sep 2016 – Oct 2018"), left navigation column, KPI strip, main sheet (~60%) + supporting sheet (~40%), full-width detail sheet, footer |
| Navigation | Objects ▸ **Navigation** button, one per dashboard (6), in a vertical container on the left of every main dashboard. The current dashboard's button is filled orange `#D95926`, the others charcoal `#2B2B29` |
| Footer (every dashboard) | Text object: *"Historical data 2016–2018 · revenue excludes freight · no margin data · Data: Olist Brazilian E-Commerce Public Dataset (Kaggle), CC BY-NC-SA 4.0"* |
| Colours (project palette) | primary series `#D95926`; secondary `#3987E5`; good `#199E70`; warning `#C98500`; bad `#E66767`; text `#1A1A19` on light or `#F0EFEC` on dark. The dark background `#1A1A19` is optional (Format ▸ Shading); legibility comes first |
| Captions | Text objects placed directly under the sheet they qualify (not hidden in tooltips) |
| Design rules kept | No dual axis for compared measures; no gauges, 3-D or extra pies (one binary pie/donut on Customers); single-series sheets have no legend; direct labels on bars; colour never the only signal (values are labelled) |
| Not built, deliberately | Profit, margin, COGS (no cost data); predicted CLV (3.12% repeat rate gives no basis); full-year YoY (2016 has 329 orders); "seller rating" (reviews attach to orders); a sum of seller-category order counts or of category review counts (not additive); acquisition cost and returns (no data) |

---

## 1 Executive — "How is the business doing overall?"

**Data sources:** RP Orders; RP Categories (sheet 1.4 only)

| KPI (sheet 1.0) | Field | Expected (no filters) |
|---|---|---|
| Total Revenue | `Total Revenue` | R$ 13,494,400.74 |
| Total Orders | `Total Orders` | 99,441 |
| Total Customers | `Total Customers` | 96,096 |
| Avg Order Value | `Average Order Value` | R$ 137.42 |
| Median Order Value | `Median Order Value` | R$ 86.90 |

| Sheet | Build | Expected |
|---|---|---|
| **1.1 Revenue and Orders by Month** | Columns `Order Month` (green, continuous **Month**); Rows `Total Orders` (Marks: Bar) and `Total Revenue` (Marks: Line) as **two separate rows, not dual axis**; add `Revenue 3M Moving Avg` to the revenue row via Measure Values (same axis, dashed). Filter `in_stable_window` = 1. Tooltip: month, revenue, orders, 3M average | 20 months 2017-01 … 2018-08; 2017-11 revenue R$ 1,003,862.14; 3M avg first point 2017-03 R$ 244,466.31, 2018-08 R$ 863,389.97 |
| **1.2 Revenue MoM %** | Columns `Order Month` (discrete month); Rows `Revenue MoM %` (Bar); Compute Using `Order Month`; Color `Revenue MoM %` diverging red–green, stepped 2, centre 0; Label on. Filter `in_stable_window` = 1 | 2017-01 **blank**; 2017-02 +103.97%; 2017-11 +52.06%; 2018-08 −3.32% |
| **1.3 Revenue by State (Top 12)** | Rows `customer_state`; Columns `Total Revenue` (Bar); sort descending; Filter `customer_state` ▸ Top ▸ By field: Top 12 by `Total Revenue`. Caption: *"Top 3 of 27 states = 63.4% of revenue."* | SP R$ 5,163,867.22; RJ R$ 1,811,623.42; MG R$ 1,573,508.20; top-3 share 63.35% |
| **1.4 Top 10 Categories** (RP Categories) | Rows `category`; Columns `Category Revenue`; Top 10 filter; sort descending. Caption: *"All periods; not affected by this dashboard's filters (separate data source)."* | 1st health_beauty R$ 1,255,695.13 |
| **1.5 YoY Jan–Aug** | Text: `YoY Growth Jan-Aug %`, `Revenue 2017 Jan-Aug`, `Revenue 2018 Jan-Aug`. Caption: *"Jan–Aug like-for-like; full-year YoY is not meaningful (2016 has 329 orders)."* | +138.28%; R$ 3,080,850.81 → R$ 7,341,037.41; with state SP +166.28% |

**Filters (single row above the main sheets):** `YEAR(order_date)` (multiple values list);
`Order Month` (range of dates); `customer_state` (multiple values dropdown); `order_status`.
**Apply to Worksheets ▸ Selected Worksheets:**

| Filter | 1.0 | 1.1 | 1.2 | 1.3 | 1.5 |
|---|---|---|---|---|---|
| Year, Order Month | ✓ | ✓ | ✓ | ✓ | **✗ (must ignore dates, like REMOVEFILTERS)** |
| customer_state, order_status | ✓ | ✓ | ✓ | ✓ | ✓ |

> **Tableau behaviour to know.** Table calculations see only the months left in the
> view. If the Order Month filter starts at, say, 2018-01, then 2018-01 has no MoM % and
> 2018-01/02 have no 3M average (the previous months are filtered out of the view). The
> running total (M12) also restarts at the first month shown. For the full history, leave
> the month filter at its full range on sheets 1.1 and 1.2.

**Interaction tests:** month 2017-11 → Total Revenue R$ 1,003,862.14 · state SP → Total
Revenue R$ 5,163,867.22 · status `unavailable` → Late Delivery Rate blank (Operations).

---

## 2 Customers — "Who buys, and do they come back?"

**Data sources:** RP Customers; RP Cohorts (2.4)

| KPI (2.0) | Field | Expected |
|---|---|---|
| Total Customers | `Total People` | 96,096 |
| Repeat Purchase Rate | `Repeat Purchase Rate` | 3.12% |
| One-Time Customers | `One-Time Customers` | 93,099 |
| Avg Orders / Customer | `Avg Orders Per Customer` | 1.0348 |
| Historical Customer Value | `Historical Customer Value` | R$ 13,494,400.74 |

Caption on the KPI strip (mandatory): *"Historical value: what customers actually spent.
This is NOT predicted lifetime value; a 3.12% repeat rate gives no basis for
prediction. Lifetime figures: not filtered by order date."*

| Sheet | Build | Expected |
|---|---|---|
| **2.1 One-time vs Repeat** | Marks: Pie; Color `is_repeat_customer` (aliases 0 = One-time, 1 = Repeat); Angle `Total People`; Label value + percent of total. Optional donut: duplicate `MIN(0)` on Rows, dual axis, inner circle white | One-time 93,099 · Repeat 2,997 |
| **2.2 RFM Segments** | Filter `rfm_scored` = 1. Rows `rfm_segment`, `Measure Names`; Columns `Measure Values`; Filter Measure Names = `Segment Customer Share`, `Segment Revenue Share`; Color `Measure Names`; both table calcs: Edit Table Calculation ▸ Specific Dimensions ▸ **rfm_segment only**. Tooltip `Customers In Segment`, `Segment Avg Historical Value`. Sort segments by `Segment Revenue Share` desc | Potential Loyalists 22.56% of customers / 33.61% of revenue; At Risk 15.57% / 30.75%; Needs Attention 35.27% / 22.27%; Lost 24.66% / 9.75%; Champions 1.00% / 2.31%; Loyal Customers 0.94% / 1.32%; customers in segment: 21,427 / 14,792 / 33,498 / 23,420 / 951 / 895; scored total 94,983 |
| **2.3 Customer Value Distribution** | Create bins on `Log10 Historical Value` (size 0.25). Columns the bin (discrete); Rows `Total People` (Bar). Axis title: "log10 of historical value (BRL)" | 94,983 people (the 1,113 with no eligible spend have no log value and are left out) *(CSV)* |
| **2.4 Cohort Retention Matrix** (RP Cohorts) | Rows `cohort_month` (String); Columns `months_since_acquisition` (discrete); Marks: Square; Color `Cohort Retention %` (sequential orange); Label `Cohort Retention %`; Filter `months_since_acquisition` ≥ 1 (offset 0 is 100% and would flatten the colour scale); Tooltip `MIN(cohort_customers)` labelled "Cohort size". Analysis ▸ Totals off | (2017-01, 1) 0.39%; (2018-07, 1) 0.72%; (2018-07, 2) **blank**; (2018-08, 1) **blank**; 190 blank cells in the full 20 × 20 grid |
| **2.5 Purchase Frequency** | Columns `total_orders` (dimension, discrete); Rows `Total People` (Bar); log axis optional; labels | 1: 93,099 · 2: 2,745 · 3: 203 · 4: 30 · 5: 8 · 6: 6 · 7: 3 · 9: 1 · 17: 1 *(CSV)* |

**Mandatory captions:** on 2.2: *"Frequency is scored 1/3/5, not quintiles: 96.88% of
customers have exactly one order, so quintile scoring would invent distinctions that
do not exist."* On 2.4: *"Later cohorts are right-censored: customers acquired near
the data's end had little time to return. Compare cohorts of similar age only."*

**Filter:** `customer_state` (from `vw_customer_summary`) applied to 2.0–2.3, 2.5.
Test: SP → Historical Customer Value R$ 5,162,518.20 and Potential Loyalists
revenue share 34.90%.

---

## 3 Products — "Which categories drive revenue and growth?"

**Data source:** RP Categories. Category axes use `category` from **dim_category**
(the root field), so one parameter selection passes to the detail dashboard.

| KPI (3.0) | Field | Expected |
|---|---|---|
| Category Revenue | `Category Revenue` | R$ 13,494,400.74 |
| Distinct Categories | `Distinct Categories` | 74 |
| Category Items Sold | `Category Items Sold` | 112,101 |
| Top Category Revenue | `Top Category Revenue` | R$ 1,255,695.13 |

| Sheet | Build | Expected |
|---|---|---|
| **3.1 Revenue by Category (Top 15)** | Rows `category`; Columns `Category Revenue`; Top 15 filter; sort desc; Tooltip `Category Revenue Share` (FIXED, correct under Top N), `Category Rank` | health_beauty 9.31%, rank 1; watches_gifts 8.88% |
| **3.2 Pareto** | Columns `category` sorted by `Category Revenue` desc (headers hidden); Rows `Category Cumulative Share` (Line), Compute Using `category`; Analytics ▸ Reference Line ▸ Constant 0.8. Caption: *"18 of 74 categories reach 80% of revenue."* | 1st 9.31%; 10th (garden_tools) 62.37%; 17th 79.68%; 18th (pet_shop) 81.26% *(CSV)*; first position ≥ 80% = 18 |
| **3.3 Monthly Trend (Top 5)** (generated name; a comma would break action sheet lists) | Columns `order_month` (String, discrete); Rows `Category Revenue` (Line); Color `category`; Filters `in_stable_window` = 1 and `category` Top 5 by `Category Revenue` | top 5: health_beauty, watches_gifts, bed_bath_table, sports_leisure, computers_accessories (same with or without the stable-window filter) *(CSV)* |
| **3.4 Growth vs Decline** | Rows `category`; Columns `Category Growth Q1 2017 to Jun-Aug 2018` (Bar); Filter on the growth field ▸ Special ▸ **Non-null values**; Color by sign (green ≥ 0, red < 0); sort desc; labels. Caption: *"2017 Q1 vs Jun–Aug 2018 (last three complete months); only categories with ≥ 50 items in both periods."* | 24 categories, 22 grew; housewares +532.22%; health_beauty +444.27%; decline: consoles_games −3.12%, unknown −45.79% *(CSV)* |
| **3.5 Category Table** | Rows `category`; Measure Values: `Category Revenue`, `Category Items Sold`, `SUM(orders)` (label "Orders"), `Product Avg Item Price`, `Category Revenue Share`, `Category Rank`; sort by revenue; **no grand total** (order counts are not additive across categories) | health_beauty R$ 1,255,695.13 · 9,634 items · R$ 130.34 avg price · 9.31% · 1 |

**Actions (Dashboard ▸ Actions):**

| Name | Type | Source sheets | Run on | Target / field |
|---|---|---|---|---|
| Set category | Change Parameter | 3.1, 3.2, 3.4, 3.5 | Select | Target parameter `p_category`; Source field `category`; Clearing the selection ▸ Keep current value |
| Open Category Detail | Go to Sheet | 3.1, 3.2, 3.4, 3.5 | **Menu** | Target sheet `7 Category Detail` (appears as a link in the tooltip menu: the drill-through) |

---

## 4 Sellers — "Which sellers matter, and which need help?"

**Data source:** RP Sellers

| KPI (4.0) | Field | Expected |
|---|---|---|
| Sellers With Revenue | `Sellers With Revenue` | 3,053 (not 3,095: 42 sellers had only canceled/unavailable orders) |
| Seller Revenue | `Seller Revenue` | R$ 13,494,400.74 |
| Largest Seller Share | `Largest Seller Share` | 1.70% |
| Seller Avg Delivery Days | `Seller Avg Delivery Days` | 12.51 |
| Seller Late Rate | `Seller Late Rate`, subtitle *"across seller-order pairs"* | 8.02% (Operations shows 8.11% per order: different grain) |

Never show `Seller Orders` (99,542 seller-order pairs) as an order count.

| Sheet | Build | Expected |
|---|---|---|
| **4.1 Top 20 Sellers** | Rows `seller_id`; Columns `Seller Revenue`; Filters `Seller Has 50+ Orders` = True, Top 20 by `Seller Revenue`; Tooltip `seller_state`, `Seller Orders`, `Seller Late Rate` | 1st 4869f7a5… (SP) R$ 229,237.63; the 20th still has ≥ 166 orders *(CSV)* |
| **4.2 Seller Concentration Curve** | Columns `seller_id` sorted by `Seller Revenue` desc (headers hidden); Rows `Seller Cumulative Share` (Line), Compute Using `seller_id`. Caption: *"Largest seller 1.70%; top 10% of sellers (306 of 3,053) 67.5%."* | position 1 1.70%; 305 67.43%; 306 67.50% |
| **4.3 Scorecard Scatter** | Columns `Seller Late Rate`; Rows `Seller Inherited Order Rating`; Detail `seller_id`; Size `Seller Revenue`; Filter `Seller Has 50+ Orders` = True; Analytics ▸ Reference Line ▸ **Median** on each axis (Per Table) to form quadrants | 428 sellers; medians: late rate 6.86%, rating 4.148 *(CSV)* |
| **4.4 Intervention Table** | Rows `seller_id`, `seller_state`; Measure Values `Seller Revenue`, `Seller Orders`, `Seller Inherited Order Rating`, `Seller Late Rate`; Filter `Needs Intervention` = True; sort by `Seller Revenue` desc; colour the rating/late cells green/amber/red | **21 sellers**; first 7c67e144… (SP) R$ 187,923.89, 982 pairs, rating 3.486 *(CSV)* |

**Mandatory caption on 4.3 and 4.4:** *"Reviews attach to the order, not the seller. In a
multi-seller order every seller inherits the same score, so this is an inherited
order rating, not an independent seller rating. Delivery delay is also not wholly
within a seller's control: the carrier accounts for 74.2% of delivery time."*

**Filter:** `seller_state` applied to 4.0–4.4. Test: SP → Seller Late Rate 8.67%,
Sellers With Revenue 1,822, Seller Revenue R$ 8,687,740.35.

**Actions:** *Set seller*: Change Parameter, sources 4.1, 4.3, 4.4, Run on Select,
parameter `p_seller`, field `seller_id`. *Open Seller Detail*: Go to Sheet, same sources,
Run on **Menu**, target `8 Seller Detail`.

---

## 5 Operations — "Are orders delivered on time, and where does time go?"

**Data sources:** RP Orders; RP Stage Summary (5.5)

| KPI (5.0) | Field | Expected |
|---|---|---|
| Delivered Orders | `Delivered Orders` | 96,478 |
| On-Time Rate | `On-Time Delivery Rate` | 91.89% |
| Avg Delivery Time | `Avg Delivery Days` | 12.56 days |
| Late Orders | `Late Orders` | 7,827 |
| Cancellation Rate | `Cancellation Rate` | 0.63% |
| Total Freight | `Total Freight` | R$ 2,241,126.29 |

| Sheet | Build | Expected |
|---|---|---|
| **5.1 Order Status** | Rows `order_status`; Columns `Total Orders` (Bar); right-click axis ▸ Edit Axis ▸ **Logarithmic**; sort desc; labels | delivered 96,478 · shipped 1,107 · canceled 625 · unavailable 609 · invoiced 314 · processing 301 · created 5 · approved 2 |
| **5.2 Promised vs Actual** (the page's key visual) | Columns `Order Month` (continuous); Rows `Measure Values` with `Avg Promised Days` and `Avg Delivery Days` (two lines, one axis); Filter `in_stable_window` = 1; label first and last points | 2017-01: promised 39.51 vs actual 12.65; 2018-08: 15.19 vs 7.73; overall promised 23.74 |
| **5.3 Delivery by State** | Rows `customer_state`; Columns `Late Delivery Rate` (Bar); Color `Late Delivery Rate` (sequential red); sort desc; Tooltip `Avg Delivery Days`, `Delivery Denominator` | SP: Avg Delivery Days 8.76 |
| **5.4 Delivery Time Distribution** | Create bins on `delivery_days` (size 1, then make the bin pill Continuous); Rows `Delivery Denominator`; add `MEDIAN(IF [delivery_measurable]=1 THEN [delivery_days] END)` to Detail and draw a Reference Line on the X axis with it (Per Table, label "Median") | median 10.22 days, mean 12.56 *(CSV)* |
| **5.5 Delivery Stage Breakdown** (RP Stage Summary) | Columns `SUM(avg_days)`; Color `stage` sorted by `stage_order`; Filter `stage_order` ≤ 3; Marks: Bar (one stacked bar); labels `avg_days` | 0.40 / 2.85 / 9.36 days, total 12.62 |
| **5.6 Stage Shares** (RP Orders) | Text table: `Approval Stage Share`, `Dispatch Stage Share`, `Last Mile Share`, `Stage Total Days`, `Stage Orders`; responds to the filters (5.5 does not) | 3.19% · 22.60% · 74.21% · 12.62 · 95,088; state SP: last-mile share 63.78% |

**Mandatory captions:** on-time card: *"Measured against Olist's own estimated date, which
was padded by up to 27 days in early 2017. This reflects cautious promising as much
as fast logistics."* Stage breakdown: *"74.2% of delivery time is the carrier leg
(95,088 orders whose four timestamps are in a valid order; 1,388 with missing or
impossible timestamps excluded). Stage total 12.62 days uses this smaller
population; the Avg Delivery Time card (12.56 days) uses 96,476 orders."*
Denominator note: *"Delivery averages use the 96,476 orders with an actual delivery
date, not the 96,478 marked delivered."*

**Filters:** `Order Month` (range), `customer_state` applied to 5.0–5.4, 5.6. Tests:
month 2018-03 → Late Delivery Rate 21.36%; status `unavailable` → On-Time and Late rate
**blank** (not 100%).

---

## 6 Satisfaction — "How do customers rate their orders, and why?"

**Data sources:** RP Orders; RP Categories (6.4)

| KPI (6.0) | Field | Expected |
|---|---|---|
| Avg Review Score | `Avg Review Score` | 4.0864 |
| One-Star Rate (headline, not a footnote) | `One-Star Rate` | 11.51% |
| Five-Star Rate | `Five-Star Rate` | 57.78% |
| Total Reviews | `Total Reviews` | 99,224 |
| Pre-Delivery Reviews | `Pre-Delivery Reviews` | 4,795 |

| Sheet | Build | Expected |
|---|---|---|
| **6.1 Score Distribution** | Columns `review_score` (discrete); Rows `Total Reviews` (Bar); labels | 1: 11,424 · 2: 3,151 · 3: 8,179 · 4: 19,142 · 5: 57,328 *(CSV)* |
| **6.2 Delay vs Score** | Rows `delivery_bucket` sorted by field `Delivery Bucket Order` (Minimum, ascending); exclude `not delivered`; Columns `Measure Values` = `Avg Order Rating (Review Table)` and `Avg Order Rating After Arrival`; Color `Measure Names`; labels; Tooltip `Total Reviews`, `One-Star Rate`, `One-Star Rate After Arrival` | on time 4.201 / 4.202 · 1–7 days late 3.184 / 3.860 · 8–15 days late 1.733 / 3.660 · 15+ days late 1.726 / 2.895 (all reviews / after arrival) |
| **6.3 Satisfaction Trend** | Columns `Order Month` (continuous); Rows `Avg Review Score` and `One-Star Rate` as two separate rows; Filter `in_stable_window` = 1 | 20 monthly points |
| **6.4 Category Satisfaction** (RP Categories) | Rows `category`; Columns `Category Avg Review Score` (Bar); Filter on `Category Items Sold` ▸ At least 300; sort ascending; Reference Line constant 4.0864 ("overall average"); Tooltip `Category One-Star Rate`, `Category Avg Score After Arrival`, `Category Review Count` | 35 categories; 15 below average; lowest office_furniture 3.6175; highest books_general_interest 4.4626 *(CSV)*. Insight 14 counts 34: its floor is 300 eligible items **on reviewed orders**, which excludes construction_tools_lights (302 eligible items; scores 4.128, above average). The "15 below average" finding is the same |

**Mandatory captions:** on 6.2: *"Correlation, not causation. A late delivery may share a
root cause with a bad experience (an unreliable seller, a difficult address) rather
than directly causing the low score. Arriving very early buys nothing: 15+ days
early scores 4.318 against 4.316 for 7–15 days early. 4,795 reviews were answered
before the parcel arrived; the after-arrival bars exclude them."* On 6.4: *"Reviews rate
the whole order, delivery included, not product quality alone."*

**Filters:** `Order Month`, `customer_state` applied to 6.0–6.3. Test: SP → Total Reviews
41,690.

---

## 7 Category Detail (drill-through)

**Opened from:** Products (action *Open Category Detail*). **Shows:** the category in
`p_category`. Not in the navigation column; a Navigation button **"← Back to Products"**
sits top-left. Title: a Text object "Category: " + Insert ▸ Parameters ▸ `p_category`.

All RP Categories sheets: Filter `Is Selected Category` (H03) = True, **added to
context** (right-click ▸ Add to Context) so Top N filters are computed inside the
category. RP Sellers sheet 7.4: `Is Selected Category` (H04) = True, also in context.

| Sheet | Build | Expected for `health_beauty` |
|---|---|---|
| **7.0 KPIs** | `Category Revenue`, `Category Revenue Share`, `Product Units Sold`, `Product Avg Item Price`, `Category Growth Q1 2017 to Jun-Aug 2018`, `Category Avg Review Score`, `Category One-Star Rate`, `Category Pre-Delivery Review Share` | R$ 1,255,695.13 · 9.31% · 9,634 · R$ 130.34 · +444.27% · 4.1822 · 10.19% · 5.37% |
| **7.1 Rank and Cumulative Share** | Rows `category` (header hidden), sorted by `Category Revenue` desc; Text `Category Rank`, `Category Cumulative Share` (Compute Using `category`); Filter **`Selected Category TC` (H05) = True** instead of H03, so all 74 are ranked first | rank 1 · cumulative 9.31% |
| **7.2 Monthly Trend** | Columns `order_month`; Rows `Category Revenue` (Line); Filter `in_stable_window` = 1 | 20 points |
| **7.3 Top 10 Products** | Rows `product_id`; Measure Values `Product Revenue`, `Product Units Sold`, `Product Avg Item Price`, `SUM(seller_count)`; Top 10 by `Product Revenue` | 10 rows, all health_beauty |
| **7.4 Top 10 Sellers in Category** (RP Sellers) | Rows `seller_id`, `seller_state`; Measure Values `Seller Category Revenue`, `Seller Category Items`, `Seller Category Late Rate`, `Seller Category Dispatch Days`; Top 10 by `Seller Category Revenue` | n/a |
| **7.5 Seller Delivery in Category** (RP Sellers) | Text: `Seller Category Late Rate`, `Seller Category Dispatch Days`, `Seller Category Revenue` | 8.93% · 2.69 days · R$ 1,255,695.13 |
| **7.6 Satisfaction** | Bars `Category Avg Review Score` vs `Category Avg Score After Arrival`; label `Category Review Count` | 4.1822 vs 4.3728 · 8,826 reviews |

**Caption:** *"Reviews rate the whole order, delivery included, not product quality
alone. Dispatch days use single-seller orders with valid timestamps."*

> **Design note.** The parameter carries only the category, not the other filters of
> the Products dashboard, so the detail dashboard always shows the category's full
> history.

---

## 8 Seller Detail (drill-through)

**Opened from:** Sellers (action *Open Seller Detail*). **Shows:** `p_seller`. Back button
**"← Back to Sellers"**; title "Seller: " + `p_seller`. Filter `Is Selected Seller` (H06)
= True on every sheet except 8.1.

| Sheet | Build | Expected for 4869f7a5dfa277a7dca6462dcf3b52b2 |
|---|---|---|
| **8.0 KPIs** | `Seller Revenue`, `Seller Orders`, `Seller Late Rate`, `Seller Avg Delivery Days`, `Seller Inherited Order Rating` | R$ 229,237.63 · 1,131 · 11.57% · 15.06 · 4.136 |
| **8.1 Cumulative Share** | Rows `seller_id` (hidden) sorted by `Seller Revenue` desc; Text `Seller Cumulative Share`, Compute Using `seller_id`; Filter **`Selected Seller TC` (H07) = True** | 1.70% |
| **8.2 Profile** | Text table: `seller_state`, `seller_city`, `first_sale`, `last_sale`, `SUM(poor_rated_orders)` | SP |
| **8.3 Categories Sold** | Rows `category`; Columns `Seller Category Revenue` (Bar), sort desc | 10 categories, summing to R$ 229,237.63 |
| **8.4 Category Breakdown** | Rows `category`; Measure Values `Seller Category Revenue`, `Seller Category Items`, `Seller Category Late Rate`, `Seller Category Dispatch Days` | 10 rows |

**Caption (mandatory):** *"Inherited order rating: reviews attach to the order, not the
seller. Delivery time is mostly the carrier's (74.2%)."*

---

## Screenshots (after the build)

Eight PNG files in `reports/dashboard_screenshots/`, taken from the **published**
Tableau Public view at the fixed dashboard size, no filters applied unless named:

| File | Dashboard |
|---|---|
| `01_executive.png` | 1 Executive |
| `02_customers.png` | 2 Customers |
| `03_products.png` | 3 Products |
| `04_sellers.png` | 4 Sellers |
| `05_operations.png` | 5 Operations |
| `06_satisfaction.png` | 6 Satisfaction |
| `07_category_detail_health_beauty.png` | 7 Category Detail, `p_category` = health_beauty |
| `08_seller_detail_largest_seller.png` | 8 Seller Detail, `p_seller` = 4869f7a5… |

Screenshots must be real captures of the built dashboard. None exist yet.
