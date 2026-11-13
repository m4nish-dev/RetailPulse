# RetailPulse — DAX Measures

**Target:** Power BI Desktop (Windows) · Import mode
**Validation:** 37 of 37 measures' logic verified against MySQL — see the scope note below
**Theme:** `RetailPulse_Theme.json`

---

## ⚠ What "validated" means here, precisely

`scripts/validate_dax_logic.py` expresses each measure below as equivalent SQL
against the **same views Power BI imports**, and compares the result to values
already verified in Phases 3–5.

| | |
|---|---|
| ✅ **Verified** | filter context, grain, denominator, arithmetic — does the measure ask the right question of the right rows |
| ❌ **Not verified** | DAX syntax, `CALCULATE` evaluation at runtime, behaviour under slicer interaction |

**A PASS means "this will compute the right number if the DAX is typed
correctly" — not "this has been run in Power BI."** Execution requires Windows
and is outstanding. Re-run the check any time with:

```bash
./venv/bin/python scripts/validate_dax_logic.py
```

> **One real error this check caught.** An earlier draft carried a
> hand-written expected value for eligible freight (2,237,474.78) that had
> never been computed. The true figure is **2,241,126.29**. The validator
> flagged it immediately. That is the entire reason this script exists.

---

## Conventions

Measures live in a dedicated `_Measures` table (a blank table holding no data)
so they are not scattered across the model. Naming is Title Case with spaces.

| Rule | Why |
|---|---|
| **Revenue = `order_revenue`, never with freight** | `kpi_definitions.md`; freight is reported separately |
| **Always filter `revenue_eligible = 1` for revenue** | Excludes canceled and unavailable orders |
| **Count people on `customer_unique_id`** | `customer_id` is per-order; using it returns 99,441 instead of 96,096 |
| **Delivery metrics use `delivery_measurable = 1`** | 96,476, not the 96,478 marked delivered — 8 have no date |
| **Trends filter `in_stable_window = 1`** | 20 complete months; the edge months hold 4, 1, 16 and 4 orders |
| **`DIVIDE()` not `/`** | Returns BLANK on divide-by-zero instead of an error |
| **No profit or margin measures exist** | The dataset has no cost column |

---

## Page 1 — Executive Business Overview

```dax
Total Revenue =
CALCULATE (
    SUM ( vw_order_summary[order_revenue] ),
    vw_order_summary[revenue_eligible] = 1
)
-- verified: 13,494,400.74 BRL

Total Orders = COUNTROWS ( vw_order_summary )
-- verified: 99,441

Total Customers = DISTINCTCOUNT ( vw_order_summary[customer_unique_id] )
-- verified: 96,096 PEOPLE. Using customer_id here returns 99,441 and is wrong.

Orders With Items =
CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[item_count] > 0 )
-- verified: 98,666

AOV Denominator =
CALCULATE (
    COUNTROWS ( vw_order_summary ),
    vw_order_summary[revenue_eligible] = 1,
    vw_order_summary[item_count] > 0
)
-- verified: 98,199. NOT 99,441 - 775 orders have no line items and
-- including them understates AOV by about 0.8%.

Average Order Value = DIVIDE ( [Total Revenue], [AOV Denominator] )
-- verified: 137.42 BRL

Median Order Value =
MEDIANX (
    FILTER ( vw_order_summary,
             vw_order_summary[revenue_eligible] = 1 && vw_order_summary[item_count] > 0 ),
    vw_order_summary[order_revenue]
)
-- verified: 86.90 BRL. Show this BESIDE the mean: AOV sits 58% above the
-- median because of a long tail, so the mean alone overstates typical spend.

Total Freight =
CALCULATE ( SUM ( vw_order_summary[order_freight] ), vw_order_summary[revenue_eligible] = 1 )
-- verified: 2,241,126.29 BRL. Never added to revenue.
```

### Time intelligence

These require `dim_date` to be **marked as the model's date table**
(Modeling ▸ Mark as date table). Without that, `DATEADD` and
`SAMEPERIODLASTYEAR` silently return blank.

```dax
Revenue PM =                            -- previous month
CALCULATE ( [Total Revenue], DATEADD ( dim_date[Date], -1, MONTH ) )

Revenue MoM % =
VAR Prev = [Revenue PM]
RETURN DIVIDE ( [Total Revenue] - Prev, Prev )

Revenue 3M Moving Avg =
AVERAGEX (
    DATESINPERIOD ( dim_date[Date], MAX ( dim_date[Date] ), -3, MONTH ),
    [Total Revenue]
)

Revenue Running Total =
CALCULATE ( [Total Revenue],
    FILTER ( ALLSELECTED ( dim_date[Date] ), dim_date[Date] <= MAX ( dim_date[Date] ) ) )
```

> **⚠ Do not build a plain year-over-year measure.** 2016 contains only 329
> orders against 45,101 in 2017, so full-year YoY computes to roughly
> +13,600% — arithmetically true and completely misleading. Use the
> like-for-like comparison instead:

```dax
Revenue 2017 Jan-Aug =
CALCULATE ( [Total Revenue], dim_date[Year] = 2017, dim_date[MonthNo] <= 8 )
-- verified: 3,080,850.81

Revenue 2018 Jan-Aug =
CALCULATE ( [Total Revenue], dim_date[Year] = 2018, dim_date[MonthNo] <= 8 )
-- verified: 7,341,037.41

YoY Growth Jan-Aug % =
DIVIDE ( [Revenue 2018 Jan-Aug] - [Revenue 2017 Jan-Aug], [Revenue 2017 Jan-Aug] )
-- +138.3%, the only honest YoY figure this dataset supports
```

---

## Page 2 — Customer Intelligence & Retention

```dax
Total People = COUNTROWS ( vw_customer_summary )          -- verified: 96,096

Repeat Customers =
CALCULATE ( COUNTROWS ( vw_customer_summary ), vw_customer_summary[total_orders] >= 2 )
-- verified: 2,997

One-Time Customers =
CALCULATE ( COUNTROWS ( vw_customer_summary ), vw_customer_summary[total_orders] = 1 )
-- verified: 93,099

Repeat Purchase Rate = DIVIDE ( [Repeat Customers], [Total People] )
-- verified: 3.12%. This is a real property of the marketplace, not a bug.

Avg Orders Per Customer = AVERAGE ( vw_customer_summary[total_orders] )
-- verified: 1.0348

Historical Customer Value = SUM ( vw_customer_summary[historical_value] )
-- verified: 13,494,400.74
```

> **⚠ Label this "Historical Customer Value", never "Lifetime Value" or
> "CLV".** It is what customers actually spent. With a 3.12% repeat rate
> there is no basis for predicting future spend, and the distinction must be
> visible on the dashboard itself, not buried in a tooltip.

### RFM

Scored in Power Query or SQL, not DAX — segment assignment is a
transformation, not a measure.

> **⚠ The Frequency dimension is near-degenerate.** 96.88% of customers have
> exactly one order, so quintile scoring on F would invent distinctions that
> do not exist. F is a 1/3/5 ordinal instead. **A caption stating this must
> appear on the RFM visual**, because the segments look more informative than
> they are.

```dax
Customers In Segment = COUNTROWS ( vw_customer_summary )
Segment Revenue Share =
DIVIDE ( SUM ( vw_customer_summary[historical_value] ),
         CALCULATE ( SUM ( vw_customer_summary[historical_value] ), ALL ( vw_customer_summary ) ) )
```

---

## Page 3 — Product & Category Analytics

```dax
Category Revenue = SUM ( vw_category_performance[revenue] )   -- verified: 13,494,400.74
Category Items Sold = SUM ( vw_category_performance[items_sold] )
Distinct Categories = DISTINCTCOUNT ( vw_category_performance[category] )  -- verified: 74

Category Revenue Share =
DIVIDE ( [Category Revenue],
         CALCULATE ( [Category Revenue], ALL ( vw_category_performance[category] ) ) )

Category Rank =
RANKX ( ALL ( vw_category_performance[category] ), [Category Revenue], , DESC, DENSE )
```

---

## Page 4 — Seller Performance

```dax
Seller Revenue = SUM ( vw_seller_performance[revenue] )   -- verified: 13,494,400.74
Sellers With Revenue = COUNTROWS ( vw_seller_performance ) -- verified: 3,053 (not 3,095)
Seller Orders = SUM ( vw_seller_performance[orders_served] )
Seller Avg Delivery Days = AVERAGE ( vw_seller_performance[avg_delivery_days] )
Seller Late Rate = AVERAGE ( vw_seller_performance[late_pct] )

Largest Seller Share =
DIVIDE ( MAXX ( VALUES ( vw_seller_performance[seller_id] ), [Seller Revenue] ),
         CALCULATE ( [Seller Revenue], ALL ( vw_seller_performance ) ) )
-- verified: 1.70%

Seller Inherited Order Rating = AVERAGE ( vw_seller_performance[avg_review_score] )
```

> **⚠ The measure name is deliberate.** A review attaches to the **order**,
> not the seller. In a multi-seller order every seller inherits the same
> score. Calling this "Seller Rating" would present an inherited order rating
> as an independent seller rating. **The visual must carry this caveat as
> visible text, not only in a tooltip.**
>
> `vw_seller_performance` returns **3,053** of 3,095 sellers. The 42 missing
> had only canceled or unavailable orders. Verified, not a bug.

---

## Page 5 — Order & Delivery Operations

```dax
Delivered Orders =
CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[is_delivered] = 1 )
-- verified: 96,478

Delivery Denominator =
CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[delivery_measurable] = 1 )
-- verified: 96,476  <- USE THIS for every delivery average

Late Orders =
CALCULATE ( SUM ( vw_order_summary[is_late] ), vw_order_summary[delivery_measurable] = 1 )
-- verified: 7,827

Late Delivery Rate = DIVIDE ( [Late Orders], [Delivery Denominator] )      -- 8.11%
On-Time Delivery Rate = 1 - [Late Delivery Rate]                            -- 91.8871%

Avg Delivery Days =
CALCULATE ( AVERAGE ( vw_order_summary[delivery_days] ), vw_order_summary[delivery_measurable] = 1 )
-- verified: 12.5587

Avg Delay Days =
CALCULATE ( AVERAGE ( vw_order_summary[delay_days] ), vw_order_summary[delivery_measurable] = 1 )
-- verified: -11.1791  (negative = early)

Cancelled Orders =
CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[order_status] = "canceled" )
-- verified: 625

Cancellation Rate = DIVIDE ( [Cancelled Orders], [Total Orders] )          -- 0.6285%
```

> **⚠ `[Delivered Orders]` (96,478) and `[Delivery Denominator]` (96,476)
> differ by 8.** Eight orders are marked `delivered` with no delivery date
> (data quality issue Q01). Using `is_delivered` for a timing average
> includes rows with no value. Always use `delivery_measurable`.
>
> **⚠ "On time" is measured against Olist's own estimate**, which was padded
> by up to 27 days in early 2017. The 91.89% figure reflects cautious
> promising as much as fast logistics. A caption should say so.

---

## Page 6 — Customer Satisfaction

```dax
Total Reviews = COUNTROWS ( vw_review_summary )              -- verified: 99,224
Avg Review Score = AVERAGE ( vw_review_summary[review_score] ) -- verified: 4.0864

One-Star Rate =
DIVIDE ( CALCULATE ( COUNTROWS ( vw_review_summary ), vw_review_summary[review_score] = 1 ),
         [Total Reviews] )
-- verified: 11.5133%  <- show this as a KPI card beside the average

Five-Star Rate =
DIVIDE ( CALCULATE ( COUNTROWS ( vw_review_summary ), vw_review_summary[review_score] = 5 ),
         [Total Reviews] )
-- verified: 57.7763%

Avg Order Rating =
CALCULATE ( AVERAGE ( vw_order_summary[review_score_avg] ), vw_order_summary[review_count] > 0 )
-- verified: 4.0868
```

> **⚠ `[Avg Review Score]` (4.0864) and `[Avg Order Rating]` (4.0868) are
> different metrics and must never share a label.** 547 orders carry 2–3
> reviews, so averaging review *rows* weights those orders more heavily than
> averaging one figure *per order*. Both are correct; the grain differs.
>
> **⚠ The review distribution is J-shaped** — 57.78% five-star, 11.51%
> one-star, little between. The 4.09 mean describes almost nobody, which is
> why `[One-Star Rate]` belongs on the page as a headline, not a footnote.

---

## Measures deliberately NOT built

| Measure | Why not |
|---|---|
| Profit, Margin, COGS | No cost data exists anywhere in the dataset |
| Customer Lifetime Value | 3.12% repeat rate gives no basis for prediction. Only historical value is reported |
| Full-year YoY Growth | 2016 has 329 orders; the figure would be ~+13,600% and meaningless |
| Seller Rating | Reviews are order-level. Named `Seller Inherited Order Rating` instead |
| Customer Acquisition Cost | No marketing spend data |
| Return / Refund Rate | Not recorded; no negative values anywhere |
