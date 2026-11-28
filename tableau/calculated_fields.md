# RetailPulse — Tableau Calculated Fields

> **Generated file.** Do not edit by hand: it is written by `scripts/validate_tableau_calcs.py --write-docs` from the same registry the validator tests, so a formula and its test values cannot drift apart.

**90 measures** (the approved catalogue M01–M49 and N01–N41) · **10 helper fields** · **2 parameters**. Data sources and relationships: [`data_model.md`](data_model.md). Step-by-step entry: [`mac_implementation_guide.md`](mac_implementation_guide.md).

> **Already in the workbook.** Every field, parameter and rename below is written into the generated `tableau/RetailPulse.twb` by `scripts/build_tableau_workbook.py`, from the same registry (`scripts/tableau_registry.py`). You only type these formulas if you build the data sources by hand (guide §2–§6).

## What "validated" means here

| | |
|---|---|
| ✅ **Verified on macOS (Python + SQL)** | each formula's logic, emulated with Tableau's rules (relationships, NULL handling, FIXED/INCLUDE, table calculations, table-calculation filters) over the exact CSVs, matches an independent SQL answer on the base tables in every reference context (`scripts/sql_reference.py`) |
| ❌ **Not verified (pending Tableau runtime test)** | that Tableau accepts the syntax as typed; that Tableau's engine evaluates it exactly as emulated; your sheet, filter, "Compute Using" and action settings |

Results: `tableau/tableau_calc_validation_results.csv` (one row per check). Re-run: `./venv/bin/python scripts/validate_tableau_calcs.py`.

## How to read each entry

- **Type**: *row-level* (computed per row), *aggregate* (computed per mark), *aggregate with LOD* (contains `{FIXED ...}` or `{INCLUDE ...}`), *table calculation* (computed across the marks of the view; set **Compute Using** exactly as stated: right-click the pill ▸ Compute Using).
- **Format**: set once on the field (Data pane ▸ right-click ▸ Default Properties ▸ Number Format). BRL: Currency (Custom), Decimal places 2, Prefix `R$ `.
- Field names are the CSV column names. Do the two naming steps in `mac_implementation_guide.md` §4 first (Reset name; rename duplicates) or the formulas will not find the fields.
- Every division is written `IF den > 0 THEN num / den END`: it returns NULL (blank) instead of an error or 0 where there is nothing to divide by.
- **Expected values** are the SQL reference values the formula reproduced; test the card against them in Tableau.
- **Revenue** everywhere is product revenue in BRL (item prices of revenue-eligible orders, freight excluded). It is not GMV (R$ 13,591,643.70, all statuses) and not profit (no cost data exists).

## Parameters

| Name | Data type | Current value | Allowable values | Purpose |
|---|---|---|---|---|
| `p_category` | String | `health_beauty` | All | Category shown on the Category Detail dashboard. Set by a parameter action from Products. |
| `p_seller` | String | `4869f7a5dfa277a7dca6462dcf3b52b2` | All | Seller shown on the Seller Detail dashboard. Set by a parameter action from Sellers. Default = the largest seller by revenue. |

## Field renames (required before entering formulas)

When two tables in one data source have a column with the same name, rename the later table's copy as below (Data Source page ▸ metadata grid ▸ find the row whose **Table** column matches ▸ click the field name ▸ Rename). Whatever label Tableau first shows for the duplicate, the final name must be exactly the **New name**.

**RP Orders**

| Table | CSV column | New name |
|---|---|---|
| `vw_review_summary` | `order_id` | `rev_order_id` |
| `vw_review_summary` | `order_month` | `rev_order_month` |
| `vw_review_summary` | `in_stable_window` | `rev_in_stable_window` |
| `vw_review_summary` | `customer_state` | `rev_customer_state` |
| `vw_review_summary` | `order_status` | `rev_order_status` |
| `vw_review_summary` | `delivery_days` | `rev_delivery_days` |
| `vw_review_summary` | `delay_days` | `rev_delay_days` |
| `vw_review_summary` | `is_late` | `rev_is_late` |
| `delivery_stage_orders` | `order_id` | `dso_order_id` |
| `delivery_stage_orders` | `order_month` | `dso_order_month` |
| `delivery_stage_orders` | `in_stable_window` | `dso_in_stable_window` |
| `delivery_stage_orders` | `customer_state` | `dso_customer_state` |

**RP Customers**

| Table | CSV column | New name |
|---|---|---|
| `rfm_customer_segments` | `customer_unique_id` | `rfm_customer_unique_id` |
| `rfm_customer_segments` | `recency_days` | `rfm_recency_days` |

**RP Categories**

| Table | CSV column | New name |
|---|---|---|
| `vw_category_performance` | `category` | `cat_category` |
| `product_performance` | `category` | `prod_category` |
| `product_performance` | `avg_item_price` | `prod_avg_item_price` |
| `category_satisfaction` | `category` | `cs_category` |
| `category_satisfaction` | `order_count` | `cs_order_count` |

**RP Sellers**

| Table | CSV column | New name |
|---|---|---|
| `seller_scorecard` | `seller_id` | `sk_seller_id` |
| `seller_scorecard` | `orders_served` | `sk_orders_served` |
| `seller_scorecard` | `poor_rated_orders` | `sk_poor_rated_orders` |
| `seller_category_performance` | `seller_id` | `scp_seller_id` |
| `seller_category_performance` | `seller_state` | `scp_seller_state` |
| `seller_category_performance` | `delivery_measurable_orders` | `scp_delivery_measurable_orders` |
| `seller_category_performance` | `avg_delivery_days` | `scp_avg_delivery_days` |
| `seller_category_performance` | `late_orders` | `scp_late_orders` |
| `seller_category_performance` | `late_pct` | `scp_late_pct` |

## Calculated fields by data source

### RP Orders

| ID | Name | Type |
|---|---|---|
| H01 | Order Month | row-level |
| H02 | Delivery Bucket Order | row-level |
| M01 | Total Revenue | aggregate |
| M02 | Total Orders | aggregate |
| M03 | Total Customers | aggregate |
| M04 | Orders With Items | aggregate |
| M05 | AOV Denominator | aggregate |
| M06 | Average Order Value | aggregate |
| M07 | Median Order Value | aggregate |
| M08 | Total Freight | aggregate |
| M09 | Revenue PM | table calculation |
| M10 | Revenue MoM % | table calculation |
| M11 | Revenue 3M Moving Avg | table calculation |
| M12 | Revenue Running Total | table calculation |
| M13 | Revenue 2017 Jan-Aug | aggregate |
| M14 | Revenue 2018 Jan-Aug | aggregate |
| M15 | YoY Growth Jan-Aug % | aggregate |
| M36 | Delivered Orders | aggregate |
| M37 | Delivery Denominator | aggregate |
| M38 | Late Orders | aggregate |
| M39 | Late Delivery Rate | aggregate |
| M40 | On-Time Delivery Rate | aggregate |
| M41 | Avg Delivery Days | aggregate |
| M42 | Avg Delay Days | aggregate |
| N41 | Avg Promised Days | aggregate |
| M43 | Cancelled Orders | aggregate |
| M44 | Cancellation Rate | aggregate |
| N17 | Stage Orders | aggregate |
| N18 | Purchase To Approval Days | aggregate |
| N19 | Approval To Carrier Days | aggregate |
| N20 | Carrier To Customer Days | aggregate |
| N21 | Stage Total Days | aggregate |
| N22 | Last Mile Share | aggregate |
| N23 | Dispatch Stage Share | aggregate |
| N24 | Approval Stage Share | aggregate |
| M45 | Total Reviews | aggregate |
| M46 | Avg Review Score | aggregate |
| M47 | One-Star Rate | aggregate |
| M48 | Five-Star Rate | aggregate |
| M49 | Avg Order Rating | aggregate |
| N25 | Pre-Delivery Reviews | aggregate |
| N26 | Pre-Delivery Review Share | aggregate |
| N27 | Avg Review Score After Arrival | aggregate |
| N28 | One-Star Rate After Arrival | aggregate |
| N35 | Avg Order Rating (Review Table) | aggregate with LOD |
| N34 | Avg Order Rating After Arrival | aggregate with LOD |

#### H01 · Order Month

- **Definition:** Calendar month in which the order was placed.
- **Data source:** RP Orders · **Type:** row-level · **Aggregation level / settings:** one value per order row · **Format:** Date, custom format yyyy-mm
- **Source fields:** `vw_order_summary.order_date`

```
DATETRUNC('month', [order_date])
```

- **Tableau notes:** The month axis of every trend sheet. Tableau's own date functions do the month arithmetic (DATEDIFF('month', ...)), so no separate date table is needed.

#### H02 · Delivery Bucket Order

- **Definition:** Position of each delivery bucket from earliest to latest.
- **Data source:** RP Orders · **Type:** row-level · **Aggregation level / settings:** one value per review row · **Format:** Number, 0 dp
- **Source fields:** `vw_review_summary.delivery_bucket`

```
CASE [delivery_bucket]
    WHEN '15+ days early'  THEN 1
    WHEN '7-15 days early' THEN 2
    WHEN 'on time'         THEN 3
    WHEN '1-7 days late'   THEN 4
    WHEN '8-15 days late'  THEN 5
    WHEN '15+ days late'   THEN 6
    WHEN 'not delivered'   THEN 7
END
```

- **Tableau notes:** Sort key for the delay-vs-score axis (Sort ▸ Field ▸ Delivery Bucket Order, Minimum, ascending).

#### M01 · Total Revenue

- **Definition:** Product revenue in BRL: item prices of revenue-eligible orders, freight excluded. Not GMV, not profit.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders (vw_order_summary) · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_order_summary.order_revenue`, `vw_order_summary.revenue_eligible`

```
SUM(IF [revenue_eligible] = 1 THEN [order_revenue] END)
```

- **Tableau notes:** Row-level IF inside SUM: rows outside the condition become NULL and are ignored.
- **Expected values (3/3 checks pass):** unfiltered → **R$ 13,494,400.74**; month = 2017-11 → **R$ 1,003,862.14**; customer_state = SP → **R$ 5,163,867.22**

#### M02 · Total Orders

- **Definition:** Number of orders, all statuses.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 0 dp
- **Source fields:** `vw_order_summary.order_id`

```
COUNTD([order_id])
```

- **Tableau notes:** COUNTD of the primary key cannot double-count, even if a join is ever added by mistake.
- **Expected values (2/2 checks pass):** unfiltered → **99,441**; month = 2018-08 → **6,512**

#### M03 · Total Customers

- **Definition:** People who ordered in the filtered period (customer_unique_id, never the per-order customer_id).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 0 dp
- **Source fields:** `vw_order_summary.customer_unique_id`

```
COUNTD([customer_unique_id])
```

- **Tableau notes:** Responds to date filters: 2017-11 gives the people active that month.
- **Expected values (2/2 checks pass):** unfiltered (people, not customer_id) → **96,096**; month = 2017-11 (people active that month) → **7,430**

#### M04 · Orders With Items

- **Definition:** Orders that contain at least one item.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 0 dp
- **Source fields:** `vw_order_summary.item_count`, `vw_order_summary.order_id`

```
COUNTD(IF [item_count] > 0 THEN [order_id] END)
```

- **Tableau notes:** Conditional COUNTD.
- **Expected values (1/1 checks pass):** unfiltered → **98,666**

#### M05 · AOV Denominator

- **Definition:** Revenue-eligible orders that have items: the denominator of average order value (98,199).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 0 dp
- **Source fields:** `vw_order_summary.item_count`, `vw_order_summary.order_id`, `vw_order_summary.revenue_eligible`

```
COUNTD(IF [revenue_eligible] = 1 AND [item_count] > 0 THEN [order_id] END)
```

- **Tableau notes:** Conditional COUNTD.
- **Expected values (2/2 checks pass):** unfiltered → **98,199**; month = 2018-01 → **7,187**

#### M06 · Average Order Value

- **Definition:** Average product revenue per eligible order with items (BRL).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** R$ currency, 2 dp
- **Uses:** `AOV Denominator`, `Total Revenue`

```
IF [AOV Denominator] > 0 THEN [Total Revenue] / [AOV Denominator] END
```

- **Tableau notes:** Ratio guarded with IF denominator > 0, so an empty context shows blank (NULL), never an error or 0.
- **Expected values (3/3 checks pass):** unfiltered → **R$ 137.42**; Jan-Aug 2017 (like-for-like) → **R$ 136.55**; Jan-Aug 2018 (like-for-like) → **R$ 137.14**

#### M07 · Median Order Value

- **Definition:** Middle order value of eligible orders with items; shown beside the mean because the mean is pulled up by large orders.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_order_summary.item_count`, `vw_order_summary.order_revenue`, `vw_order_summary.revenue_eligible`

```
MEDIAN(IF [revenue_eligible] = 1 AND [item_count] > 0 THEN [order_revenue] END)
```

- **Tableau notes:** Text-file data runs through Tableau's extract engine, which supports MEDIAN.
- **Expected values (1/1 checks pass):** unfiltered (computed, not a constant) → **R$ 86.90**

#### M08 · Total Freight

- **Definition:** Freight charged on eligible orders (BRL). Never added to revenue.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_order_summary.order_freight`, `vw_order_summary.revenue_eligible`

```
SUM(IF [revenue_eligible] = 1 THEN [order_freight] END)
```

- **Tableau notes:** As M01.
- **Expected values (1/1 checks pass):** unfiltered (eligible) → **R$ 2,241,126.29**

#### M09 · Revenue PM

- **Definition:** Total revenue of the previous calendar month.
- **Data source:** RP Orders · **Type:** table calculation · **Aggregation level / settings:** Compute Using: Order Month (month marks) · **Format:** R$ currency, 2 dp
- **Uses:** `Order Month`, `Total Revenue`

```
IF DATEDIFF('month', LOOKUP(MIN([Order Month]), -1), MIN([Order Month])) = 1
THEN LOOKUP([Total Revenue], -1)
END
```

- **Tableau notes:** LOOKUP reads the previous MARK, not the previous calendar month. November 2016 has no orders, so without the DATEDIFF guard December 2016 would show October 2016 (pitfall P01). With the guard a missing month gives blank.
- **Expected values (4/4 checks pass):** month = 2016-12 → **NULL (blank)**; month = 2017-01 → **R$ 10.90**; month = 2017-11 → **R$ 660,179.62**; month = 2018-08 → **R$ 878,044.27**

#### M10 · Revenue MoM %

- **Definition:** Month-over-month revenue change, only when this month and the previous one are both complete months (2017-01 to 2018-08).
- **Data source:** RP Orders · **Type:** table calculation · **Aggregation level / settings:** Compute Using: Order Month · **Format:** Percentage, 2 dp
- **Source fields:** `vw_order_summary.in_stable_window`
- **Uses:** `Order Month`, `Total Revenue`

```
IF MIN([in_stable_window]) = 1
   AND LOOKUP(MIN([in_stable_window]), -1) = 1
   AND DATEDIFF('month', LOOKUP(MIN([Order Month]), -1), MIN([Order Month])) = 1
   AND LOOKUP([Total Revenue], -1) > 0
THEN ([Total Revenue] - LOOKUP([Total Revenue], -1)) / LOOKUP([Total Revenue], -1)
END
```

- **Tableau notes:** 2017-01 is blank by design: December 2016 holds a single order. Works with or without a stable-window filter on the sheet. Table calculations see only the months left in the view.
- **Expected values (5/5 checks pass):** month = 2017-01 → **NULL (blank)**; month = 2017-02 → **103.97%**; month = 2017-11 → **52.06%**; month = 2018-08 → **-3.32%**; month = 2018-09 → **NULL (blank)**

#### M11 · Revenue 3M Moving Avg

- **Definition:** Average of this month's and the two previous months' revenue totals, complete months only.
- **Data source:** RP Orders · **Type:** table calculation · **Aggregation level / settings:** Compute Using: Order Month · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_order_summary.in_stable_window`
- **Uses:** `Order Month`, `Total Revenue`

```
IF MIN([in_stable_window]) = 1
   AND LOOKUP(MIN([in_stable_window]), -2) = 1
   AND DATEDIFF('month', LOOKUP(MIN([Order Month]), -2), MIN([Order Month])) = 2
THEN WINDOW_SUM([Total Revenue], -2, 0) / 3
END
```

- **Tableau notes:** WINDOW_SUM over the current and two previous marks, divided by 3. First value 2017-03.
- **Expected values (7/7 checks pass):** month = 2016-12 → **NULL (blank)**; month = 2017-01 → **NULL (blank)**; month = 2017-02 → **NULL (blank)**; month = 2017-03 → **R$ 244,466.31**; month = 2017-12 → **R$ 802,075.18**; month = 2018-08 → **R$ 863,389.97** (+1 more in the results CSV)

#### M12 · Revenue Running Total

- **Definition:** Cumulative revenue up to each month.
- **Data source:** RP Orders · **Type:** table calculation · **Aggregation level / settings:** Compute Using: Order Month · **Format:** R$ currency, 2 dp
- **Uses:** `Total Revenue`

```
RUNNING_SUM([Total Revenue])
```

- **Tableau notes:** Respects the sheet's filters (table calculations run after them): with in_stable_window = 1 it starts at 2017-01 and reaches R$ 13,449,529.68 at 2018-08.
- **Expected values (4/4 checks pass):** month = 2017-06, no filter → **R$ 2,065,043.78**; month = 2017-06, filter in_stable_window = 1 → **R$ 2,020,317.72**; month = 2018-08, filter in_stable_window = 1 → **R$ 13,449,529.68**; month = 2018-10, no filter → **R$ 13,494,400.74**

#### M13 · Revenue 2017 Jan-Aug

- **Definition:** Revenue of January-August 2017, the like-for-like base for year-on-year growth.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_order_summary.order_date`, `vw_order_summary.order_revenue`, `vw_order_summary.revenue_eligible`

```
SUM(IF YEAR([order_date]) = 2017 AND MONTH([order_date]) <= 8 AND [revenue_eligible] = 1 THEN [order_revenue] END)
```

- **Tableau notes:** The YoY sheet must be EXCLUDED from the dashboard's date filters (filter ▸ Apply to Worksheets ▸ Selected Worksheets, untick 1.5). State filters still apply.
- **Expected values (3/3 checks pass):** unfiltered → **R$ 3,080,850.81**; dashboard date filter 2018-01..08 (YoY sheet excluded from it) → **R$ 3,080,850.81**; customer_state = SP → **R$ 1,111,718.45**

#### M14 · Revenue 2018 Jan-Aug

- **Definition:** Revenue of January-August 2018.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_order_summary.order_date`, `vw_order_summary.order_revenue`, `vw_order_summary.revenue_eligible`

```
SUM(IF YEAR([order_date]) = 2018 AND MONTH([order_date]) <= 8 AND [revenue_eligible] = 1 THEN [order_revenue] END)
```

- **Tableau notes:** As M13.
- **Expected values (3/3 checks pass):** unfiltered → **R$ 7,341,037.41**; dashboard date filter 2018-01..08 (YoY sheet excluded from it) → **R$ 7,341,037.41**; customer_state = SP → **R$ 2,960,326.25**

#### M15 · YoY Growth Jan-Aug %

- **Definition:** Like-for-like growth Jan-Aug 2018 vs Jan-Aug 2017. Full-year YoY is not reported (2016 has 329 orders).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Percentage, 2 dp
- **Uses:** `Revenue 2017 Jan-Aug`, `Revenue 2018 Jan-Aug`

```
IF [Revenue 2017 Jan-Aug] > 0
THEN ([Revenue 2018 Jan-Aug] - [Revenue 2017 Jan-Aug]) / [Revenue 2017 Jan-Aug]
END
```

- **Tableau notes:** As M13.
- **Expected values (2/2 checks pass):** unfiltered → **138.28%**; customer_state = SP → **166.28%**

#### M36 · Delivered Orders

- **Definition:** Orders with status delivered (96,478).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 0 dp
- **Source fields:** `vw_order_summary.is_delivered`, `vw_order_summary.order_id`

```
COUNTD(IF [is_delivered] = 1 THEN [order_id] END)
```

- **Tableau notes:** Conditional COUNTD.
- **Expected values (1/1 checks pass):** unfiltered → **96,478**

#### M37 · Delivery Denominator

- **Definition:** Orders with an actual delivery date (96,476): the denominator of every delivery average.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 0 dp
- **Source fields:** `vw_order_summary.delivery_measurable`, `vw_order_summary.order_id`

```
COUNTD(IF [delivery_measurable] = 1 THEN [order_id] END)
```

- **Tableau notes:** COUNTD returns 0 (not NULL) where nothing qualifies; the rates below guard against it.
- **Expected values (1/1 checks pass):** unfiltered → **96,476**

#### M38 · Late Orders

- **Definition:** Delivered after Olist's estimated date.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 0 dp
- **Source fields:** `vw_order_summary.delivery_measurable`, `vw_order_summary.is_late`

```
SUM(IF [delivery_measurable] = 1 THEN [is_late] END)
```

- **Tableau notes:** Sum of a 1/0 flag on measurable orders.
- **Expected values (1/1 checks pass):** unfiltered → **7,827**

#### M39 · Late Delivery Rate

- **Definition:** Share of delivered orders that arrived late (8.11%).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Percentage, 2 dp
- **Uses:** `Delivery Denominator`, `Late Orders`

```
IF [Delivery Denominator] > 0 THEN [Late Orders] / [Delivery Denominator] END
```

- **Tableau notes:** Ratio guarded with IF denominator > 0, so an empty context shows blank (NULL), never an error or 0.
- **Expected values (3/3 checks pass):** unfiltered → **8.11%**; month = 2018-03 → **21.36%**; order_status = unavailable (no deliveries -> blank) → **NULL (blank)**

#### M40 · On-Time Delivery Rate

- **Definition:** Share delivered on or before the estimated date (91.89%), measured against Olist's own padded estimate.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Percentage, 2 dp
- **Uses:** `Delivery Denominator`, `Late Orders`

```
IF [Delivery Denominator] > 0 THEN ([Delivery Denominator] - [Late Orders]) / [Delivery Denominator] END
```

- **Tableau notes:** Blank (not 100%) where there are no deliveries, e.g. status unavailable.
- **Expected values (3/3 checks pass):** unfiltered → **91.89%**; month = 2018-03 → **78.64%**; order_status = unavailable (no deliveries -> blank) → **NULL (blank)**

#### M41 · Avg Delivery Days

- **Definition:** Average days from purchase to delivery (12.56).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 2 dp
- **Source fields:** `vw_order_summary.delivery_days`, `vw_order_summary.delivery_measurable`

```
AVG(IF [delivery_measurable] = 1 THEN [delivery_days] END)
```

- **Tableau notes:** Measurable orders only.
- **Expected values (2/2 checks pass):** unfiltered → **12.5587**; customer_state = SP → **8.7614**

#### M42 · Avg Delay Days

- **Definition:** Average days delivered after (+) or before (-) the estimate.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 2 dp
- **Source fields:** `vw_order_summary.delay_days`, `vw_order_summary.delivery_measurable`

```
AVG(IF [delivery_measurable] = 1 THEN [delay_days] END)
```

- **Tableau notes:** Negative = early.
- **Expected values (2/2 checks pass):** unfiltered → **-11.1791**; customer_state = SP → **-10.3812**

#### N41 · Avg Promised Days

- **Definition:** Average days from purchase to the promised (estimated) date, delivered orders.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 2 dp
- **Source fields:** `vw_order_summary.delay_days`, `vw_order_summary.delivery_days`, `vw_order_summary.delivery_measurable`

```
AVG(IF [delivery_measurable] = 1 THEN [delivery_days] - [delay_days] END)
```

- **Tableau notes:** Plot beside Avg Delivery Days: 2017-01 39.51 promised vs 12.65 actual.
- **Expected values (4/4 checks pass):** unfiltered → **23.7378**; month = 2017-01 → **39.5088**; month = 2018-08 → **15.1863**; customer_state = SP → **19.1425**

#### M43 · Cancelled Orders

- **Definition:** Orders with status canceled (625).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 0 dp
- **Source fields:** `vw_order_summary.order_id`, `vw_order_summary.order_status`

```
COUNTD(IF [order_status] = 'canceled' THEN [order_id] END)
```

- **Tableau notes:** Conditional COUNTD.
- **Expected values (1/1 checks pass):** unfiltered → **625**

#### M44 · Cancellation Rate

- **Definition:** Share of orders canceled (0.63%).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Percentage, 2 dp
- **Uses:** `Cancelled Orders`, `Total Orders`

```
IF [Total Orders] > 0 THEN [Cancelled Orders] / [Total Orders] END
```

- **Tableau notes:** Ratio guarded with IF denominator > 0, so an empty context shows blank (NULL), never an error or 0.
- **Expected values (1/1 checks pass):** unfiltered → **0.63%**

#### N17 · Stage Orders

- **Definition:** Orders whose four timestamps are in a valid order (95,088).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** stage-valid orders (delivery_stage_orders) · **Format:** Number, 0 dp
- **Source fields:** `delivery_stage_orders.total_seconds`

```
COUNT([total_seconds])
```

- **Tableau notes:** Counts delivery_stage_orders rows through a column only that table has (never NULL). A table's (Count) field cannot be used inside a calculation.
- **Expected values (3/3 checks pass):** unfiltered → **95,088**; customer_state = SP → **39,903**; month = 2018-01 → **7,045**

#### N18 · Purchase To Approval Days

- **Definition:** Average days from purchase to payment approval (0.40).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** stage-valid orders · **Format:** Number, 2 dp
- **Source fields:** `delivery_stage_orders.purchase_to_approval_seconds`
- **Uses:** `Stage Orders`

```
IF [Stage Orders] > 0 THEN SUM([purchase_to_approval_seconds]) / ([Stage Orders] * 86400) END
```

- **Tableau notes:** Ratio guarded with IF denominator > 0, so an empty context shows blank (NULL), never an error or 0.
- **Expected values (3/3 checks pass):** unfiltered → **0.4021**; customer_state = SP → **0.3781**; month = 2018-01 → **0.4174**

#### N19 · Approval To Carrier Days

- **Definition:** Average days from approval to carrier handover (2.85).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** stage-valid orders · **Format:** Number, 2 dp
- **Source fields:** `delivery_stage_orders.approval_to_carrier_seconds`
- **Uses:** `Stage Orders`

```
IF [Stage Orders] > 0 THEN SUM([approval_to_carrier_seconds]) / ([Stage Orders] * 86400) END
```

- **Tableau notes:** Ratio guarded with IF denominator > 0, so an empty context shows blank (NULL), never an error or 0.
- **Expected values (3/3 checks pass):** unfiltered → **2.8520**; customer_state = SP → **2.8106**; month = 2018-01 → **3.1856**

#### N20 · Carrier To Customer Days

- **Definition:** Average days the carrier takes to deliver (9.36).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** stage-valid orders · **Format:** Number, 2 dp
- **Source fields:** `delivery_stage_orders.carrier_to_customer_seconds`
- **Uses:** `Stage Orders`

```
IF [Stage Orders] > 0 THEN SUM([carrier_to_customer_seconds]) / ([Stage Orders] * 86400) END
```

- **Tableau notes:** Ratio guarded with IF denominator > 0, so an empty context shows blank (NULL), never an error or 0.
- **Expected values (3/3 checks pass):** unfiltered → **9.3644**; customer_state = SP → **5.6140**; month = 2018-01 → **10.4768**

#### N21 · Stage Total Days

- **Definition:** Average purchase-to-delivery days on stage-valid orders (12.62).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** stage-valid orders · **Format:** Number, 2 dp
- **Source fields:** `delivery_stage_orders.total_seconds`
- **Uses:** `Stage Orders`

```
IF [Stage Orders] > 0 THEN SUM([total_seconds]) / ([Stage Orders] * 86400) END
```

- **Tableau notes:** Differs from Avg Delivery Days (12.56 on 96,476 orders) by population: label both.
- **Expected values (3/3 checks pass):** unfiltered → **12.6185**; customer_state = SP → **8.8027**; month = 2018-01 → **14.0797**

#### N22 · Last Mile Share

- **Definition:** Share of delivery time spent with the carrier (74.21%).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** stage-valid orders · **Format:** Percentage, 2 dp
- **Source fields:** `delivery_stage_orders.carrier_to_customer_seconds`, `delivery_stage_orders.total_seconds`

```
IF SUM([total_seconds]) > 0 THEN SUM([carrier_to_customer_seconds]) / SUM([total_seconds]) END
```

- **Tableau notes:** Ratio of summed seconds.
- **Expected values (3/3 checks pass):** unfiltered → **74.21%**; customer_state = SP → **63.78%**; month = 2018-01 → **74.41%**

#### N23 · Dispatch Stage Share

- **Definition:** Share of delivery time from approval to carrier (22.60%).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** stage-valid orders · **Format:** Percentage, 2 dp
- **Source fields:** `delivery_stage_orders.approval_to_carrier_seconds`, `delivery_stage_orders.total_seconds`

```
IF SUM([total_seconds]) > 0 THEN SUM([approval_to_carrier_seconds]) / SUM([total_seconds]) END
```

- **Tableau notes:** Ratio of summed seconds.
- **Expected values (3/3 checks pass):** unfiltered → **22.60%**; customer_state = SP → **31.93%**; month = 2018-01 → **22.63%**

#### N24 · Approval Stage Share

- **Definition:** Share of delivery time waiting for payment approval (3.19%).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** stage-valid orders · **Format:** Percentage, 2 dp
- **Source fields:** `delivery_stage_orders.purchase_to_approval_seconds`, `delivery_stage_orders.total_seconds`

```
IF SUM([total_seconds]) > 0 THEN SUM([purchase_to_approval_seconds]) / SUM([total_seconds]) END
```

- **Tableau notes:** Ratio of summed seconds.
- **Expected values (3/3 checks pass):** unfiltered → **3.19%**; customer_state = SP → **4.30%**; month = 2018-01 → **2.96%**

#### M45 · Total Reviews

- **Definition:** Number of reviews (99,224).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** reviews (vw_review_summary) · **Format:** Number, 0 dp
- **Source fields:** `vw_review_summary.review_id`

```
COUNT([review_id])
```

- **Tableau notes:** COUNT, NOT COUNTD: 814 review rows repeat a review_id (one review covering several orders), so COUNTD would give 98,410 (pitfall P03).
- **Expected values (2/2 checks pass):** unfiltered → **99,224**; customer_state = SP (via vw_order_summary) → **41,690**

#### M46 · Avg Review Score

- **Definition:** Average score per review, 1-5 (4.0864, review grain).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** reviews · **Format:** Number, 4 dp
- **Source fields:** `vw_review_summary.review_score`

```
AVG([review_score])
```

- **Tableau notes:** Different metric from the order-grain M49.
- **Expected values (1/1 checks pass):** unfiltered (review grain) → **4.0864**

#### M47 · One-Star Rate

- **Definition:** Share of reviews with 1 star (11.51%).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** reviews · **Format:** Percentage, 2 dp
- **Source fields:** `vw_review_summary.review_id`, `vw_review_summary.review_score`
- **Uses:** `Total Reviews`

```
IF [Total Reviews] > 0 THEN COUNT(IF [review_score] = 1 THEN [review_id] END) / [Total Reviews] END
```

- **Tableau notes:** Conditional COUNT.
- **Expected values (1/1 checks pass):** unfiltered → **11.51%**

#### M48 · Five-Star Rate

- **Definition:** Share of reviews with 5 stars (57.78%).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** reviews · **Format:** Percentage, 2 dp
- **Source fields:** `vw_review_summary.review_id`, `vw_review_summary.review_score`
- **Uses:** `Total Reviews`

```
IF [Total Reviews] > 0 THEN COUNT(IF [review_score] = 5 THEN [review_id] END) / [Total Reviews] END
```

- **Tableau notes:** Conditional COUNT.
- **Expected values (1/1 checks pass):** unfiltered → **57.78%**

#### M49 · Avg Order Rating

- **Definition:** Average review score per order (4.0868): orders with 2-3 reviews count once.
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** orders · **Format:** Number, 4 dp
- **Source fields:** `vw_order_summary.review_count`, `vw_order_summary.review_score_avg`

```
AVG(IF [review_count] > 0 THEN [review_score_avg] END)
```

- **Tableau notes:** From vw_order_summary (review_score_avg stored to 4 decimals).
- **Expected values (1/1 checks pass):** unfiltered (order grain) → **4.0868**

#### N25 · Pre-Delivery Reviews

- **Definition:** Reviews answered before the parcel arrived (4,795).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** reviews · **Format:** Number, 0 dp
- **Source fields:** `vw_review_summary.review_before_delivery`, `vw_review_summary.review_id`

```
COUNT(IF [review_before_delivery] = 1 THEN [review_id] END)
```

- **Tableau notes:** Conditional COUNT.
- **Expected values (1/1 checks pass):** unfiltered → **4,795**

#### N26 · Pre-Delivery Review Share

- **Definition:** Share of reviews on delivered orders that were answered before arrival (4.98%).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** reviews · **Format:** Percentage, 2 dp
- **Source fields:** `vw_review_summary.review_before_delivery`, `vw_review_summary.review_id`
- **Uses:** `Pre-Delivery Reviews`

```
IF COUNT(IF NOT ISNULL([review_before_delivery]) THEN [review_id] END) > 0
THEN [Pre-Delivery Reviews] / COUNT(IF NOT ISNULL([review_before_delivery]) THEN [review_id] END)
END
```

- **Tableau notes:** The flag is NULL for undelivered orders, which are excluded from the denominator.
- **Expected values (1/1 checks pass):** unfiltered (of reviews on delivered orders) → **4.98%**

#### N27 · Avg Review Score After Arrival

- **Definition:** Average score of reviews answered after arrival (4.279).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** reviews · **Format:** Number, 4 dp
- **Source fields:** `vw_review_summary.review_before_delivery`, `vw_review_summary.review_score`

```
AVG(IF [review_before_delivery] = 0 THEN [review_score] END)
```

- **Tableau notes:** Review grain.
- **Expected values (1/1 checks pass):** unfiltered (review grain) → **4.2787**

#### N28 · One-Star Rate After Arrival

- **Definition:** Share of after-arrival reviews with 1 star (6.76%).
- **Data source:** RP Orders · **Type:** aggregate · **Aggregation level / settings:** reviews · **Format:** Percentage, 2 dp
- **Source fields:** `vw_review_summary.review_before_delivery`, `vw_review_summary.review_id`, `vw_review_summary.review_score`

```
IF COUNT(IF [review_before_delivery] = 0 THEN [review_id] END) > 0
THEN COUNT(IF [review_before_delivery] = 0 AND [review_score] = 1 THEN [review_id] END)
     / COUNT(IF [review_before_delivery] = 0 THEN [review_id] END)
END
```

- **Tableau notes:** Ratio guarded with IF denominator > 0, so an empty context shows blank (NULL), never an error or 0.
- **Expected values (1/1 checks pass):** unfiltered → **6.76%**

#### N35 · Avg Order Rating (Review Table)

- **Definition:** Average score per order, computed from the review table so it can sit on a delivery_bucket axis.
- **Data source:** RP Orders · **Type:** aggregate with LOD · **Aggregation level / settings:** per order, then averaged · **Format:** Number, 4 dp
- **Source fields:** `vw_review_summary.order_id` (as `rev_order_id`), `vw_review_summary.review_score`

```
AVG({INCLUDE [rev_order_id] : AVG([review_score])})
```

- **Tableau notes:** INCLUDE gives one value per order whatever its review count; averaging a FIXED value over review rows would over-weight the 547 multi-review orders (pitfall P02). Groups by the review table's own order_id (rev_order_id) so the LOD stays inside one table, the pattern Tableau 2026.3.2 evaluated correctly in the runtime test.
- **Expected values (5/5 checks pass):** delivery_bucket = 1-7 days late (all reviews) → **3.1839**; delivery_bucket = 8-15 days late (all reviews) → **1.7325**; delivery_bucket = on time (all reviews) → **4.2009**; delivery_bucket = 15+ days late (all reviews) → **1.7258**; unfiltered (must equal M49 at full precision) → **4.0868**

#### N34 · Avg Order Rating After Arrival

- **Definition:** Average score per order, using only reviews answered after the parcel arrived.
- **Data source:** RP Orders · **Type:** aggregate with LOD · **Aggregation level / settings:** per order, then averaged · **Format:** Number, 4 dp
- **Source fields:** `vw_review_summary.order_id` (as `rev_order_id`), `vw_review_summary.review_before_delivery`, `vw_review_summary.review_score`

```
AVG({INCLUDE [rev_order_id] : AVG(IF [review_before_delivery] = 0 THEN [review_score] END)})
```

- **Tableau notes:** The after-arrival condition goes INSIDE the LOD: in 115 orders the reviews disagree on timing, and a FIXED LOD would ignore a review_before_delivery filter (pitfall P06). Groups by rev_order_id (same table).
- **Expected values (4/4 checks pass):** delivery_bucket = 1-7 days late → **3.8604**; delivery_bucket = 8-15 days late → **3.6604**; delivery_bucket = on time → **4.2017**; delivery_bucket = 15+ days late → **2.8947**

### RP Customers

| ID | Name | Type |
|---|---|---|
| H10 | Log10 Historical Value | row-level |
| M16 | Total People | aggregate |
| M17 | Repeat Customers | aggregate |
| M18 | One-Time Customers | aggregate |
| M19 | Repeat Purchase Rate | aggregate |
| M20 | Avg Orders Per Customer | aggregate |
| M21 | Historical Customer Value | aggregate |
| N01 | RFM Scored Customers | table calculation |
| M22 | Customers In Segment | aggregate |
| M23 | Segment Revenue Share | table calculation |
| N02 | Segment Customer Share | table calculation |
| N03 | Segment Avg Historical Value | aggregate |

#### H10 · Log10 Historical Value

- **Definition:** Base-10 logarithm of what a person has spent.
- **Data source:** RP Customers · **Type:** row-level · **Aggregation level / settings:** one value per person · **Format:** Number, 2 dp
- **Source fields:** `vw_customer_summary.historical_value`

```
IF [historical_value] > 0 THEN LOG([historical_value]) END
```

- **Tableau notes:** Binned (size 0.25) for the value histogram. The 1,113 people with no eligible spend get NULL; exclude the Null bin.

#### M16 · Total People

- **Definition:** Distinct people who ever ordered (96,096).
- **Data source:** RP Customers · **Type:** aggregate · **Aggregation level / settings:** people (vw_customer_summary) · **Format:** Number, 0 dp
- **Source fields:** `vw_customer_summary.customer_unique_id`

```
COUNTD([customer_unique_id])
```

- **Tableau notes:** Lives in its own data source, so order-date filters elsewhere cannot touch it (lifetime figures). Inside the orders data source a date filter WOULD restrict it (pitfall P07).
- **Expected values (1/1 checks pass):** unfiltered → **96,096**

#### M17 · Repeat Customers

- **Definition:** People with two or more orders.
- **Data source:** RP Customers · **Type:** aggregate · **Aggregation level / settings:** people · **Format:** Number, 0 dp
- **Source fields:** `vw_customer_summary.customer_unique_id`, `vw_customer_summary.total_orders`

```
COUNTD(IF [total_orders] >= 2 THEN [customer_unique_id] END)
```

- **Tableau notes:** Conditional COUNTD.
- **Expected values (1/1 checks pass):** unfiltered → **2,997**

#### M18 · One-Time Customers

- **Definition:** People with exactly one order.
- **Data source:** RP Customers · **Type:** aggregate · **Aggregation level / settings:** people · **Format:** Number, 0 dp
- **Source fields:** `vw_customer_summary.customer_unique_id`, `vw_customer_summary.total_orders`

```
COUNTD(IF [total_orders] = 1 THEN [customer_unique_id] END)
```

- **Tableau notes:** Conditional COUNTD.
- **Expected values (1/1 checks pass):** unfiltered → **93,099**

#### M19 · Repeat Purchase Rate

- **Definition:** Share of people who ordered more than once (3.12%).
- **Data source:** RP Customers · **Type:** aggregate · **Aggregation level / settings:** people · **Format:** Percentage, 2 dp
- **Uses:** `Repeat Customers`, `Total People`

```
IF [Total People] > 0 THEN [Repeat Customers] / [Total People] END
```

- **Tableau notes:** Ratio guarded with IF denominator > 0, so an empty context shows blank (NULL), never an error or 0.
- **Expected values (1/1 checks pass):** unfiltered → **3.12%**

#### M20 · Avg Orders Per Customer

- **Definition:** Average number of orders per person (all statuses).
- **Data source:** RP Customers · **Type:** aggregate · **Aggregation level / settings:** people · **Format:** Number, 4 dp
- **Source fields:** `vw_customer_summary.total_orders`

```
AVG([total_orders])
```

- **Tableau notes:** One row per person, so AVG is a per-person average.
- **Expected values (1/1 checks pass):** unfiltered → **1.0348**

#### M21 · Historical Customer Value

- **Definition:** What customers actually spent (eligible product revenue). Historical, never a predicted lifetime value.
- **Data source:** RP Customers · **Type:** aggregate · **Aggregation level / settings:** people · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_customer_summary.historical_value`

```
SUM([historical_value])
```

- **Tableau notes:** Label it 'Historical Customer Value', never CLV.
- **Expected values (2/2 checks pass):** unfiltered → **R$ 13,494,400.74**; customer_state = SP → **R$ 5,162,518.20**

#### N01 · RFM Scored Customers

- **Definition:** People with an RFM score (94,983); the denominator of segment shares.
- **Data source:** RP Customers · **Type:** table calculation · **Aggregation level / settings:** Compute Using: rfm_segment · **Format:** Number, 0 dp
- **Source fields:** `rfm_customer_segments.rfm_scored`

```
TOTAL(SUM([rfm_scored]))
```

- **Tableau notes:** rfm_scored is 1/0 with one row per person, so SUM counts scored people. TOTAL() spans every segment in the view and keeps other filters (state).
- **Expected values (1/1 checks pass):** unfiltered → **94,983**

#### M22 · Customers In Segment

- **Definition:** Scored people in the segment of the mark.
- **Data source:** RP Customers · **Type:** aggregate · **Aggregation level / settings:** people (rfm_customer_segments) · **Format:** Number, 0 dp
- **Source fields:** `rfm_customer_segments.rfm_scored`

```
SUM([rfm_scored])
```

- **Tableau notes:** Sum of a 1/0 flag = conditional count.
- **Expected values (7/7 checks pass):** all scored → **94,983**; segment = At Risk → **14,792**; segment = Champions → **951**; segment = Lost → **23,420**; segment = Loyal Customers → **895**; segment = Needs Attention → **33,498** (+1 more in the results CSV)

#### M23 · Segment Revenue Share

- **Definition:** Share of historical revenue held by the segment.
- **Data source:** RP Customers · **Type:** table calculation · **Aggregation level / settings:** Compute Using: rfm_segment · **Format:** Percentage, 2 dp
- **Source fields:** `rfm_customer_segments.monetary_value`

```
IF TOTAL(SUM([monetary_value])) > 0 THEN SUM([monetary_value]) / TOTAL(SUM([monetary_value])) END
```

- **Tableau notes:** The 1,113 unscored people have monetary_value 0, so including or excluding them does not change the share.
- **Expected values (7/7 checks pass):** segment = At Risk → **30.75%**; segment = Champions → **2.31%**; segment = Lost → **9.75%**; segment = Loyal Customers → **1.32%**; segment = Needs Attention → **22.27%**; segment = Potential Loyalists → **33.61%** (+1 more in the results CSV)

#### N02 · Segment Customer Share

- **Definition:** Share of scored people in the segment; compare with the revenue share.
- **Data source:** RP Customers · **Type:** table calculation · **Aggregation level / settings:** Compute Using: rfm_segment · **Format:** Percentage, 2 dp
- **Uses:** `Customers In Segment`, `RFM Scored Customers`

```
IF [RFM Scored Customers] > 0 THEN [Customers In Segment] / [RFM Scored Customers] END
```

- **Tableau notes:** As N01.
- **Expected values (6/6 checks pass):** segment = At Risk → **15.57%**; segment = Champions → **1.00%**; segment = Lost → **24.66%**; segment = Loyal Customers → **0.94%**; segment = Needs Attention → **35.27%**; segment = Potential Loyalists → **22.56%**

#### N03 · Segment Avg Historical Value

- **Definition:** Historical spend per scored person in the segment (BRL); not a prediction.
- **Data source:** RP Customers · **Type:** aggregate · **Aggregation level / settings:** people · **Format:** R$ currency, 2 dp
- **Source fields:** `rfm_customer_segments.monetary_value`, `rfm_customer_segments.rfm_scored`
- **Uses:** `Customers In Segment`

```
IF [Customers In Segment] > 0
THEN SUM(IF [rfm_scored] = 1 THEN [monetary_value] END) / [Customers In Segment]
END
```

- **Tableau notes:** Ratio guarded with IF denominator > 0, so an empty context shows blank (NULL), never an error or 0.
- **Expected values (6/6 checks pass):** segment = At Risk → **R$ 280.49**; segment = Champions → **R$ 327.44**; segment = Lost → **R$ 56.15**; segment = Loyal Customers → **R$ 198.96**; segment = Needs Attention → **R$ 89.71**; segment = Potential Loyalists → **R$ 211.69**

### RP Cohorts

| ID | Name | Type |
|---|---|---|
| N04 | Cohort Customers | aggregate |
| N05 | Cohort Retention % | aggregate |
| N06 | Returning Customers | aggregate |

#### N04 · Cohort Customers

- **Definition:** People acquired in the cohort month (cohort size).
- **Data source:** RP Cohorts · **Type:** aggregate · **Aggregation level / settings:** cohort cells · **Format:** Number, 0 dp
- **Source fields:** `cohort_retention.cohort_customers`, `cohort_retention.months_since_acquisition`

```
SUM(IF [months_since_acquisition] = 0 THEN [cohort_customers] END)
```

- **Tableau notes:** Taken from the offset-0 row of each cohort.
- **Expected values (2/2 checks pass):** cohort = 2017-01 → **764**; cohort = 2018-08 → **6,271**

#### N05 · Cohort Retention %

- **Definition:** Share of a cohort that ordered again N months after its first order (calendar months).
- **Data source:** RP Cohorts · **Type:** aggregate · **Aggregation level / settings:** cohort cells · **Format:** Percentage, 2 dp
- **Source fields:** `cohort_retention.active_customers`, `cohort_retention.cohort_customers`, `cohort_retention.is_observed`, `cohort_retention.months_since_acquisition`

```
IF MIN([months_since_acquisition]) = MAX([months_since_acquisition])
   AND SUM(IF [is_observed] = 1 THEN [cohort_customers] END) > 0
THEN SUM([active_customers]) / SUM(IF [is_observed] = 1 THEN [cohort_customers] END)
END
```

- **Tableau notes:** Only defined for a single offset (MIN = MAX), so the grand total is blank. Unobserved (future) cells have NULL active_customers and no observed denominator: they stay blank, never 0. A column total weights only the cohorts observable at that offset.
- **Expected values (8/8 checks pass):** cohort=2017-01, offset=1 (observed cell) → **0.39%**; cohort=2018-07, offset=1 (last observed cell of a late cohort) → **0.72%**; cohort=2018-07, offset=2 (UNOBSERVED cell -> blank, not 0) → **NULL (blank)**; cohort=2018-08, offset=1 (UNOBSERVED (right-censored)) → **NULL (blank)**; cohort=all, offset=0 (offset 0 across cohorts = 100%) → **100.00%**; cohort=all, offset=1 (offset 1 across cohorts: denominator = observed cohorts only) → **0.51%** (+2 more in the results CSV)

#### N06 · Returning Customers

- **Definition:** Cohort members who came back in that month.
- **Data source:** RP Cohorts · **Type:** aggregate · **Aggregation level / settings:** cohort cells · **Format:** Number, 0 dp
- **Source fields:** `cohort_retention.returning_customers`

```
SUM([returning_customers])
```

- **Tableau notes:** NULL at offset 0 and in unobserved cells.
- **Expected values (3/3 checks pass):** cohort=2017-01, offset=1 → **3**; cohort=2018-07, offset=2 → **NULL (blank)**; cohort=2017-01, offset=0 → **NULL (blank)**

### RP Categories

| ID | Name | Type |
|---|---|---|
| H03 | Is Selected Category | row-level |
| H05 | Selected Category TC | table calculation |
| M24 | Category Revenue | aggregate |
| M25 | Category Items Sold | aggregate |
| M26 | Distinct Categories | aggregate |
| M27 | Category Revenue Share | aggregate with LOD |
| M28 | Category Rank | table calculation |
| N07 | Top Category Revenue | aggregate with LOD |
| N36 | Category Cumulative Share | table calculation |
| N37 | Category Revenue 2017 Q1 | aggregate |
| N38 | Category Revenue Jun-Aug 2018 | aggregate |
| N39 | Category Growth Q1 2017 to Jun-Aug 2018 | aggregate |
| N08 | Product Revenue | aggregate |
| N09 | Product Units Sold | aggregate |
| N10 | Products Sold | aggregate |
| N11 | Product Avg Item Price | aggregate |
| N12 | Product Avg Freight Per Item | aggregate |
| N29 | Category Review Count | aggregate |
| N30 | Category Avg Review Score | aggregate |
| N31 | Category One-Star Rate | aggregate |
| N32 | Category Avg Score After Arrival | aggregate |
| N33 | Category Pre-Delivery Review Share | aggregate |

#### H03 · Is Selected Category

- **Definition:** True for the category chosen on the Products dashboard.
- **Data source:** RP Categories · **Type:** row-level · **Aggregation level / settings:** one value per dim_category row
- **Source fields:** `dim_category.category`
- **Uses:** `p_category`

```
[category] = [p_category]
```

- **Tableau notes:** Put on Filters = True on every Category Detail sheet of RP Categories, then Add to Context so Top N filters work inside the category. Not on sheet 7.1 (uses H05).

#### H05 · Selected Category TC

- **Definition:** True for the chosen category, decided after all categories have been ranked.
- **Data source:** RP Categories · **Type:** table calculation · **Aggregation level / settings:** Compute Using: category
- **Source fields:** `dim_category.category`
- **Uses:** `p_category`

```
LOOKUP(MIN([category]), 0) = [p_category]
```

- **Tableau notes:** A table-calculation filter is applied last, so rank and cumulative share are computed over all 74 categories before the others are hidden. A normal filter would leave one row and show rank 1 / 100%.

#### M24 · Category Revenue

- **Definition:** Product revenue by category (eligible items, BRL).
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** category x month (vw_category_performance) · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_category_performance.revenue`

```
SUM([revenue])
```

- **Tableau notes:** Additive across months and categories.
- **Expected values (3/3 checks pass):** unfiltered → **R$ 13,494,400.74**; category = health_beauty → **R$ 1,255,695.13**; order_month = 2018-01 → **R$ 945,456.29**

#### M25 · Category Items Sold

- **Definition:** Eligible items sold.
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** category x month · **Format:** Number, 0 dp
- **Source fields:** `vw_category_performance.items_sold`

```
SUM([items_sold])
```

- **Tableau notes:** Additive.
- **Expected values (2/2 checks pass):** unfiltered → **112,101**; category = health_beauty → **9,634**

#### M26 · Distinct Categories

- **Definition:** Categories with sales.
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** category x month · **Format:** Number, 0 dp
- **Source fields:** `vw_category_performance.category` (as `cat_category`)

```
COUNTD([cat_category])
```

- **Tableau notes:** Counts the renamed vw_category_performance category column.
- **Expected values (1/1 checks pass):** unfiltered → **74**

#### M27 · Category Revenue Share

- **Definition:** Category revenue as a share of all product revenue.
- **Data source:** RP Categories · **Type:** aggregate with LOD · **Aggregation level / settings:** category; denominator = all categories · **Format:** Percentage, 2 dp
- **Source fields:** `vw_category_performance.revenue`

```
IF MIN({FIXED : SUM([revenue])}) > 0
THEN SUM([revenue]) / MIN({FIXED : SUM([revenue])})
END
```

- **Tableau notes:** A FIXED total ignores dimension filters (category filter, Top N), so the share stays a share of ALL revenue on a Top-15 chart and on Category Detail; TOTAL() would give the share of the top 15 only (pitfall P04). FIXED also ignores a month filter unless that filter is added to context (pitfall P09); no month filter is specified on these sheets.
- **Expected values (3/3 checks pass):** category = health_beauty → **9.31%**; category = watches_gifts → **8.88%**; category = security_and_services → **0.00%**

#### M28 · Category Rank

- **Definition:** Position of the category by revenue (1 = largest).
- **Data source:** RP Categories · **Type:** table calculation · **Aggregation level / settings:** Compute Using: category · **Format:** Number, 0 dp
- **Uses:** `Category Revenue`

```
RANK_DENSE([Category Revenue], 'desc')
```

- **Tableau notes:** Ranks the categories in the view. On Category Detail use the table-calculation filter H05 so all 74 are ranked before the others are hidden.
- **Expected values (1/1 checks pass):** every category (74 checks in one) → **74**

#### N07 · Top Category Revenue

- **Definition:** Revenue of the largest category.
- **Data source:** RP Categories · **Type:** aggregate with LOD · **Aggregation level / settings:** category, then max · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_category_performance.category` (as `cat_category`), `vw_category_performance.revenue`

```
MAX({INCLUDE [cat_category] : SUM([revenue])})
```

- **Tableau notes:** INCLUDE computes revenue per category, then MAX picks the largest. The LOD groups by the category column of the SAME table as revenue (vw_category_performance): grouping by the root dim_category field made Tableau 2026.3.2 fail with 'Logical Query missing field [category (category_satisfaction)]' (runtime test).
- **Expected values (1/1 checks pass):** unfiltered → **R$ 1,255,695.13**

#### N36 · Category Cumulative Share

- **Definition:** Share of revenue held by this category and every larger one (Pareto curve).
- **Data source:** RP Categories · **Type:** table calculation · **Aggregation level / settings:** Compute Using: category; sort category by Category Revenue descending · **Format:** Percentage, 2 dp
- **Uses:** `Category Revenue`

```
RUNNING_SUM([Category Revenue]) / TOTAL([Category Revenue])
```

- **Tableau notes:** Defined as all categories with revenue >= this one; RUNNING_SUM equals that because no two categories tie (all 74 verified).
- **Expected values (4/4 checks pass):** category = health_beauty → **9.31%**; category = garden_tools → **62.37%**; all 74 categories (74 in one) → **7400.00%**; categories needed to reach 80% → **1800.00%**

#### N37 · Category Revenue 2017 Q1

- **Definition:** Category revenue in January-March 2017.
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** category x month · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_category_performance.order_month`, `vw_category_performance.revenue`

```
SUM(IF [order_month] >= '2017-01' AND [order_month] <= '2017-03' THEN [revenue] END)
```

- **Tableau notes:** Text comparison on 'YYYY-MM' (sorts correctly). order_month must be typed String.
- **Expected values (2/2 checks pass):** category = housewares → **R$ 28,295.96**; unfiltered → **R$ 733,398.94**

#### N38 · Category Revenue Jun-Aug 2018

- **Definition:** Category revenue in June-August 2018, the last three complete months (not calendar Q3).
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** category x month · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_category_performance.order_month`, `vw_category_performance.revenue`

```
SUM(IF [order_month] >= '2018-06' AND [order_month] <= '2018-08' THEN [revenue] END)
```

- **Tableau notes:** As N37.
- **Expected values (2/2 checks pass):** category = housewares → **R$ 178,893.66**; unfiltered → **R$ 2,590,169.90**

#### N39 · Category Growth Q1 2017 to Jun-Aug 2018

- **Definition:** Revenue growth from 2017 Q1 to Jun-Aug 2018, only for categories with at least 50 items in both periods.
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** category · **Format:** Percentage, 2 dp
- **Source fields:** `vw_category_performance.items_sold`, `vw_category_performance.order_month`
- **Uses:** `Category Revenue 2017 Q1`, `Category Revenue Jun-Aug 2018`

```
IF SUM(IF [order_month] >= '2017-01' AND [order_month] <= '2017-03' THEN [items_sold] END) >= 50
   AND SUM(IF [order_month] >= '2018-06' AND [order_month] <= '2018-08' THEN [items_sold] END) >= 50
   AND [Category Revenue 2017 Q1] > 0
THEN ([Category Revenue Jun-Aug 2018] - [Category Revenue 2017 Q1]) / [Category Revenue 2017 Q1]
END
```

- **Tableau notes:** Blank below the 50-item floor (24 categories qualify; 22 grew).
- **Expected values (5/5 checks pass):** category = housewares → **532.22%**; category = health_beauty → **444.27%**; category = books_technical (under 50 items -> blank) → **NULL (blank)**; categories meeting the floor that grew → **2200.00%**; every category matches (74 in one) → **7400.00%**

#### N08 · Product Revenue

- **Definition:** Product revenue (eligible items, BRL).
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** product · **Format:** R$ currency, 2 dp
- **Source fields:** `product_performance.product_revenue`

```
SUM([product_revenue])
```

- **Tableau notes:** Additive.
- **Expected values (2/2 checks pass):** unfiltered → **R$ 13,494,400.74**; category = health_beauty → **R$ 1,255,695.13**

#### N09 · Product Units Sold

- **Definition:** Eligible units sold.
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** product · **Format:** Number, 0 dp
- **Source fields:** `product_performance.units_sold`

```
SUM([units_sold])
```

- **Tableau notes:** Additive.
- **Expected values (2/2 checks pass):** unfiltered → **112,101**; category = health_beauty → **9,634**

#### N10 · Products Sold

- **Definition:** Products with at least one eligible sale.
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** product · **Format:** Number, 0 dp
- **Source fields:** `product_performance.product_id`, `product_performance.units_sold`

```
COUNTD(IF [units_sold] > 0 THEN [product_id] END)
```

- **Tableau notes:** Conditional COUNTD.
- **Expected values (2/2 checks pass):** unfiltered → **32,729**; category = health_beauty → **2,430**

#### N11 · Product Avg Item Price

- **Definition:** Average price per item sold (BRL), weighted by units.
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** product · **Format:** R$ currency, 2 dp
- **Uses:** `Product Revenue`, `Product Units Sold`

```
IF [Product Units Sold] > 0 THEN [Product Revenue] / [Product Units Sold] END
```

- **Tableau notes:** Ratio of sums; AVG of avg_item_price would over-weight rarely sold expensive products.
- **Expected values (2/2 checks pass):** unfiltered → **R$ 120.38**; category = health_beauty → **R$ 130.34**

#### N12 · Product Avg Freight Per Item

- **Definition:** Freight charged per item sold (BRL).
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** product · **Format:** R$ currency, 2 dp
- **Source fields:** `product_performance.freight_value`
- **Uses:** `Product Units Sold`

```
IF [Product Units Sold] > 0 THEN SUM([freight_value]) / [Product Units Sold] END
```

- **Tableau notes:** Ratio guarded with IF denominator > 0, so an empty context shows blank (NULL), never an error or 0.
- **Expected values (2/2 checks pass):** unfiltered → **R$ 19.99**; category = health_beauty → **R$ 18.89**

#### N29 · Category Review Count

- **Definition:** Reviews on orders containing the category (each review once per category).
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** one category · **Format:** Number, 0 dp
- **Source fields:** `category_satisfaction.category` (as `cs_category`), `category_satisfaction.review_count`

```
IF COUNTD([cs_category]) = 1 THEN SUM([review_count]) END
```

- **Tableau notes:** Shown only when exactly one category is in the mark; blank at totals, because multi-category orders count in each category and a plain sum would exceed the reviews that exist.
- **Expected values (3/3 checks pass):** category = health_beauty → **8,826**; category = office_furniture → **1,268**; no single category (total row) -> blank, not a double-counted sum → **NULL (blank)**

#### N30 · Category Avg Review Score

- **Definition:** Average review score of the category's orders (review grain).
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** one category · **Format:** Number, 4 dp
- **Source fields:** `category_satisfaction.avg_review_score`, `category_satisfaction.category` (as `cs_category`)

```
IF COUNTD([cs_category]) = 1 THEN SUM([avg_review_score]) END
```

- **Tableau notes:** As N29.
- **Expected values (3/3 checks pass):** category = health_beauty → **4.1822**; category = office_furniture → **3.6175**; no single category (total row) -> blank → **NULL (blank)**

#### N31 · Category One-Star Rate

- **Definition:** Share of the category's reviews that are 1 star.
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** one category · **Format:** Percentage, 2 dp
- **Source fields:** `category_satisfaction.category` (as `cs_category`), `category_satisfaction.one_star_pct`

```
IF COUNTD([cs_category]) = 1 THEN SUM([one_star_pct]) / 100 END
```

- **Tableau notes:** As N29; the CSV stores percent units.
- **Expected values (2/2 checks pass):** category = health_beauty → **10.19%**; category = office_furniture → **17.90%**

#### N32 · Category Avg Score After Arrival

- **Definition:** Average score of reviews written after the parcel arrived.
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** one category · **Format:** Number, 4 dp
- **Source fields:** `category_satisfaction.avg_review_score_after_arrival`, `category_satisfaction.category` (as `cs_category`)

```
IF COUNTD([cs_category]) = 1 THEN SUM([avg_review_score_after_arrival]) END
```

- **Tableau notes:** As N29.
- **Expected values (2/2 checks pass):** category = health_beauty → **4.3728**; category = office_furniture → **3.7515**

#### N33 · Category Pre-Delivery Review Share

- **Definition:** Share of the category's reviews written before the parcel arrived.
- **Data source:** RP Categories · **Type:** aggregate · **Aggregation level / settings:** one category · **Format:** Percentage, 2 dp
- **Source fields:** `category_satisfaction.category` (as `cs_category`), `category_satisfaction.pct_reviews_before_delivery`

```
IF COUNTD([cs_category]) = 1 THEN SUM([pct_reviews_before_delivery]) / 100 END
```

- **Tableau notes:** As N31.
- **Expected values (2/2 checks pass):** category = health_beauty → **5.37%**; category = office_furniture → **5.84%**

### RP Sellers

| ID | Name | Type |
|---|---|---|
| H04 | Is Selected Category | row-level |
| H06 | Is Selected Seller | row-level |
| H07 | Selected Seller TC | table calculation |
| H08 | Seller Has 50+ Orders | row-level |
| H09 | Needs Intervention | aggregate |
| M29 | Seller Revenue | aggregate |
| M30 | Sellers With Revenue | aggregate |
| M31 | Seller Orders | aggregate |
| M32 | Seller Avg Delivery Days | aggregate |
| M33 | Seller Late Rate | aggregate |
| M34 | Largest Seller Share | aggregate with LOD |
| M35 | Seller Inherited Order Rating | aggregate |
| N40 | Seller Cumulative Share | table calculation |
| N13 | Seller Category Revenue | aggregate |
| N14 | Seller Category Items | aggregate |
| N15 | Seller Category Late Rate | aggregate |
| N16 | Seller Category Dispatch Days | aggregate |

#### H04 · Is Selected Category

- **Definition:** True for seller-category rows of the chosen category.
- **Data source:** RP Sellers · **Type:** row-level · **Aggregation level / settings:** one value per seller_category_performance row
- **Source fields:** `seller_category_performance.category`
- **Uses:** `p_category`

```
[category] = [p_category]
```

- **Tableau notes:** Same role as H03 in the RP Sellers data source (sheets 7.4 and 7.5), also added to context.

#### H06 · Is Selected Seller

- **Definition:** True for the seller chosen on the Sellers dashboard.
- **Data source:** RP Sellers · **Type:** row-level · **Aggregation level / settings:** one value per seller row
- **Source fields:** `vw_seller_performance.seller_id`
- **Uses:** `p_seller`

```
[seller_id] = [p_seller]
```

- **Tableau notes:** Filters = True on every Seller Detail sheet except the cumulative-share sheet (H07).

#### H07 · Selected Seller TC

- **Definition:** True for the chosen seller, decided after all sellers have been accumulated.
- **Data source:** RP Sellers · **Type:** table calculation · **Aggregation level / settings:** Compute Using: seller_id
- **Source fields:** `vw_seller_performance.seller_id`
- **Uses:** `p_seller`

```
LOOKUP(MIN([seller_id]), 0) = [p_seller]
```

- **Tableau notes:** Table-calculation filter for the Seller Detail cumulative-share card (see H05).

#### H08 · Seller Has 50+ Orders

- **Definition:** Seller served at least 50 seller-order pairs.
- **Data source:** RP Sellers · **Type:** row-level · **Aggregation level / settings:** one value per seller
- **Source fields:** `vw_seller_performance.orders_served`

```
[orders_served] >= 50
```

- **Tableau notes:** Minimum sample for seller rankings and the scatter: averages over a handful of orders are unstable.

#### H09 · Needs Intervention

- **Definition:** Seller with real volume (>= 100 seller-order pairs) and a low inherited order rating (< 3.8).
- **Data source:** RP Sellers · **Type:** aggregate · **Aggregation level / settings:** per seller (seller_id on Rows)
- **Source fields:** `vw_seller_performance.orders_served`
- **Uses:** `Seller Inherited Order Rating`

```
SUM([orders_served]) >= 100 AND [Seller Inherited Order Rating] < 3.8
```

- **Tableau notes:** Filter = True on the intervention table; needs seller_id in the view so it is evaluated per seller.

#### M29 · Seller Revenue

- **Definition:** Product revenue of the seller(s) (BRL).
- **Data source:** RP Sellers · **Type:** aggregate · **Aggregation level / settings:** seller (vw_seller_performance) · **Format:** R$ currency, 2 dp
- **Source fields:** `vw_seller_performance.revenue`

```
SUM([revenue])
```

- **Tableau notes:** Additive across sellers.
- **Expected values (2/2 checks pass):** unfiltered → **R$ 13,494,400.74**; seller_state = SP → **R$ 8,687,740.35**

#### M30 · Sellers With Revenue

- **Definition:** Sellers with at least one eligible sale (3,053; 42 more had only canceled/unavailable orders).
- **Data source:** RP Sellers · **Type:** aggregate · **Aggregation level / settings:** seller · **Format:** Number, 0 dp
- **Source fields:** `vw_seller_performance.seller_id`

```
COUNTD([seller_id])
```

- **Tableau notes:** COUNTD of the primary key.
- **Expected values (2/2 checks pass):** unfiltered → **3,053**; seller_state = SP → **1,822**

#### M31 · Seller Orders

- **Definition:** Seller-order PAIRS: a two-seller order counts once for each seller. Not an order count.
- **Data source:** RP Sellers · **Type:** aggregate · **Aggregation level / settings:** seller · **Format:** Number, 0 dp
- **Source fields:** `vw_seller_performance.orders_served`

```
SUM([orders_served])
```

- **Tableau notes:** Label 'Seller-order pairs'. Use AOV Denominator (98,199) for orders.
- **Expected values (2/2 checks pass):** unfiltered (seller-order pairs) → **99,542**; seller_state = SP (seller-order pairs) → **70,616**

#### M32 · Seller Avg Delivery Days

- **Definition:** Average days from purchase to delivery across the seller's delivered orders.
- **Data source:** RP Sellers · **Type:** aggregate · **Aggregation level / settings:** seller (seller_scorecard) · **Format:** Number, 2 dp
- **Source fields:** `seller_scorecard.delivery_days_sum`, `seller_scorecard.delivery_measurable_orders`

```
IF SUM([delivery_measurable_orders]) > 0 THEN SUM([delivery_days_sum]) / SUM([delivery_measurable_orders]) END
```

- **Tableau notes:** Weighted ratio of sums, so a total is weighted by volume, not the mean of 3,053 averages.
- **Expected values (3/3 checks pass):** unfiltered → **12.5110**; seller_state = SP → **12.3167**; seller = largest seller → **15.0624**

#### M33 · Seller Late Rate

- **Definition:** Late deliveries across seller-order pairs (8.02%; the per-order platform rate is 8.11%).
- **Data source:** RP Sellers · **Type:** aggregate · **Aggregation level / settings:** seller (seller_scorecard) · **Format:** Percentage, 2 dp
- **Source fields:** `seller_scorecard.delivery_measurable_orders`, `seller_scorecard.late_orders`

```
IF SUM([delivery_measurable_orders]) > 0 THEN SUM([late_orders]) / SUM([delivery_measurable_orders]) END
```

- **Tableau notes:** Weighted ratio of sums.
- **Expected values (3/3 checks pass):** unfiltered → **8.02%**; seller_state = SP → **8.67%**; seller = largest seller → **11.57%**

#### M34 · Largest Seller Share

- **Definition:** Revenue of the largest seller as a share of platform revenue (1.70%).
- **Data source:** RP Sellers · **Type:** aggregate with LOD · **Aggregation level / settings:** seller, then max; denominator = platform · **Format:** Percentage, 2 dp
- **Source fields:** `vw_seller_performance.revenue`, `vw_seller_performance.seller_id`

```
IF MIN({FIXED : SUM([revenue])}) > 0
THEN MAX({INCLUDE [seller_id] : SUM([revenue])}) / MIN({FIXED : SUM([revenue])})
END
```

- **Tableau notes:** The FIXED denominator ignores filters by design (platform revenue).
- **Expected values (1/1 checks pass):** unfiltered → **1.70%**

#### M35 · Seller Inherited Order Rating

- **Definition:** Average review score of the seller's orders. Reviews attach to orders, so every seller in a multi-seller order inherits its score.
- **Data source:** RP Sellers · **Type:** aggregate · **Aggregation level / settings:** seller (seller_scorecard) · **Format:** Number, 4 dp
- **Source fields:** `seller_scorecard.review_score_sum`, `seller_scorecard.reviewed_orders`

```
IF SUM([reviewed_orders]) > 0 THEN SUM([review_score_sum]) / SUM([reviewed_orders]) END
```

- **Tableau notes:** Weighted ratio. Never call it 'seller rating'.
- **Expected values (3/3 checks pass):** unfiltered → **4.0992**; seller_state = SP → **4.0732**; seller = largest seller → **4.1362**

#### N40 · Seller Cumulative Share

- **Definition:** Share of revenue held by this seller and every larger one (concentration curve).
- **Data source:** RP Sellers · **Type:** table calculation · **Aggregation level / settings:** Compute Using: seller_id; sort seller_id by Seller Revenue descending · **Format:** Percentage, 2 dp
- **Uses:** `Seller Revenue`

```
RUNNING_SUM([Seller Revenue]) / TOTAL([Seller Revenue])
```

- **Tableau notes:** DOCUMENTED DIFFERENCE: 495 sellers share a revenue value with another seller. The definition gives tied sellers one shared value; RUNNING_SUM accumulates them one by one. 311 sellers differ, by at most 0.0201 percentage points, and the first tie is at position 865, so the quoted values (1.70%, 67.43% at 305, 67.50% at 306) are exact.
- **Expected values (4/4 checks pass):** seller ranked 1 by revenue → **1.70%**; seller ranked 305 by revenue → **67.43%**; seller ranked 306 by revenue → **67.50%**; every seller (3,053 in one) → **274200.00%**

#### N13 · Seller Category Revenue

- **Definition:** Product revenue per seller and category (BRL).
- **Data source:** RP Sellers · **Type:** aggregate · **Aggregation level / settings:** seller x category · **Format:** R$ currency, 2 dp
- **Source fields:** `seller_category_performance.product_revenue`

```
SUM([product_revenue])
```

- **Tableau notes:** Additive to seller and category totals.
- **Expected values (2/2 checks pass):** category = health_beauty → **R$ 1,255,695.13**; seller = largest seller (all its categories) → **R$ 229,237.63**

#### N14 · Seller Category Items

- **Definition:** Eligible items per seller and category.
- **Data source:** RP Sellers · **Type:** aggregate · **Aggregation level / settings:** seller x category · **Format:** Number, 0 dp
- **Source fields:** `seller_category_performance.item_count`

```
SUM([item_count])
```

- **Tableau notes:** Additive. order_count in this table is NOT additive and is not summed.
- **Expected values (1/1 checks pass):** unfiltered → **112,101**

#### N15 · Seller Category Late Rate

- **Definition:** Late deliveries per seller-category, weighted.
- **Data source:** RP Sellers · **Type:** aggregate · **Aggregation level / settings:** seller x category · **Format:** Percentage, 2 dp
- **Source fields:** `seller_category_performance.delivery_measurable_orders` (as `scp_delivery_measurable_orders`), `seller_category_performance.late_orders` (as `scp_late_orders`)

```
IF SUM([scp_delivery_measurable_orders]) > 0 THEN SUM([scp_late_orders]) / SUM([scp_delivery_measurable_orders]) END
```

- **Tableau notes:** Uses the renamed seller_category_performance columns (scp_...).
- **Expected values (1/1 checks pass):** category = health_beauty → **8.93%**

#### N16 · Seller Category Dispatch Days

- **Definition:** Average days from approval to carrier handover; single-seller orders with valid timestamps only.
- **Data source:** RP Sellers · **Type:** aggregate · **Aggregation level / settings:** seller x category · **Format:** Number, 2 dp
- **Source fields:** `seller_category_performance.avg_dispatch_days`, `seller_category_performance.dispatch_measurable_orders`

```
IF SUM([dispatch_measurable_orders]) > 0
THEN SUM([dispatch_measurable_orders] * [avg_dispatch_days]) / SUM([dispatch_measurable_orders])
END
```

- **Tableau notes:** Weighted average rebuilt from a row-level product.
- **Expected values (1/1 checks pass):** category = health_beauty (single-seller, valid timing) → **2.6923**

## Pitfalls shown to be wrong (why the formulas look the way they do)

| ID | Field | Wrong formulation | Evidence | Shown |
|---|---|---|---|---|
| P01 | Revenue PM | LOOKUP(-1) without the DATEDIFF guard at 2016-12 | returns October 2016 revenue 44,507.30; correct value is BLANK (November 2016 has no orders) | ✅ |
| P02 | Avg Order Rating (Review Table) | AVG over review rows of {FIXED [order_id]: AVG([review_score])} | gives 4.086421 (multi-review orders counted once per review) vs order-grain 4.086793 | ✅ |
| P03 | Total Reviews | COUNTD([review_id]) instead of COUNT | COUNTD gives 98,410; there are 99,224 reviews (814 rows repeat a review_id) | ✅ |
| P04 | Category Revenue Share | SUM/TOTAL(SUM) on a chart with a Top-15 filter | health_beauty would show 12.19% of the top 15 instead of 9.31% of all revenue | ✅ |
| P05 | Total Revenue | physical JOIN of vw_order_summary and vw_review_summary instead of a relationship | join gives 13,431,884.80 vs 13,494,400.74 (orders with 2-3 reviews repeat; orders without a review drop) | ✅ |
| P06 | Avg Order Rating After Arrival | FIXED order average + review_before_delivery = 0 as a normal filter | gives 3.861 for '1-7 days late' (FIXED ignores the filter, so pre-arrival reviews leak in) vs 3.860 | ✅ |
| P07 | Total People | customer table in the orders data source with an Order Month = 2017-11 filter | the relationship would cut lifetime people to 7,430 (those who ordered that month) instead of 96,096; hence a separate RP Customers data source | ✅ |
| P08 | Seller Cumulative Share | RUNNING_SUM vs the '>=' definition on tied seller revenues (documented difference) | 311 sellers differ, max 0.0201 percentage points, first at position 865 (after the 306 sellers in the specification caption) | ✅ |
| P09 | Category Revenue Share | FIXED denominator with a NON-context month filter (order_month = 2018-01) | gives 0.535% (share of all-time revenue) vs 7.636% within the month; add any month filter on these sheets to context | ✅ |

## Drill-through and dashboard checks

| ID | Field | Context | Tableau (emulated) | SQL expected | Pass |
|---|---|---|---|---|---|
| D01 | Category Rank | Category Detail, p_category = health_beauty (TC filter H05) | 1 | 1 | ✅ |
| D02 | Category Cumulative Share | Category Detail, p_category = health_beauty (TC filter H05) | 0.093053 | 0.093053 | ✅ |
| D03 | Category Revenue Share | Category Detail, p_category = health_beauty (FIXED denominator) | 0.093053 | 0.093053 | ✅ |
| D04 | Seller Cumulative Share | Seller Detail, p_seller = largest seller (TC filter H07) | 0.0169876 | 0.0169876 | ✅ |
| D05 | Categories sold (COUNTD category) | Seller Detail, p_seller = largest seller | 10 | 10 | ✅ |
| D06 | Seller Category Revenue (sum of category rows) | Seller Detail, p_seller = largest seller | 229,237.63 | 229,237.63 | ✅ |
| D07 | Seller Orders | Seller Detail, p_seller = largest seller | 1,131.00 | 1,131.00 | ✅ |
| D08 | Top-3 state revenue share (caption) | Executive, revenue by state | 0.633522 | 0.633522 | ✅ |
| D09 | Needs Intervention (row count) | Sellers, intervention table | 21 | 21 | ✅ |
| D10 | Seller Has 50+ Orders (row count) | Sellers, rankings and scatter | 428 | 428 | ✅ |

