# RetailPulse — Dashboard Specification

Six pages, specified visual by visual so the build is mechanical rather than
improvised.

> **Updated 2026-11-20 (fix-Phase 3).** The RFM, cohort, drill-through, stage
> breakdown and category-satisfaction visuals now have dedicated, validated
> sources in `data/analytical/`. See [`analytical_sources.md`](analytical_sources.md).
> The stage figures and the delay-vs-score table below were corrected to the
> Phase 2 results. Every KPI names the DAX measure from
[`dax_measures.md`](dax_measures.md), all of which have had their logic
verified against MySQL.

**Theme:** `RetailPulse_Theme.json` (dark charcoal `#1A1A19`, white `#F0EFEC`,
orange `#D95926`). Import via View ▸ Themes ▸ Browse for themes.

---

## Global layout

Consistent across all six pages, so navigation feels like one product:

```
┌──────────────────────────────────────────────────────────────────────┐
│ RetailPulse            [page title]              Sep 2016 – Oct 2018 │  header, 60px
├────────┬─────────────────────────────────────────────────────────────┤
│  nav   │  KPI card row (4–5 cards, 110px tall)                       │
│ 1 Exec │                                                             │
│ 2 Cust ├─────────────────────────────────────────────────────────────┤
│ 3 Prod │  main visual (left, ~60%)      │  supporting visual (~40%)  │
│ 4 Sell │                                 │                            │
│ 5 Oper ├─────────────────────────────────┴────────────────────────────┤
│ 6 Sat  │  detail visual / table, full width                          │
├────────┴─────────────────────────────────────────────────────────────┤
│ Historical data 2016–2018 · revenue excludes freight · no margin data│  footer
└──────────────────────────────────────────────────────────────────────┘
```

- **Navigation:** left sidebar, 6 buttons with page navigation actions.
  Selected page highlighted in orange.
- **Footer disclaimer on every page** — the data is historical and carries
  real limitations; that belongs in permanent view, not a hidden tooltip.
- **Slicers** sit in a single row directly above the main visuals.
- Currency shown as **R$ (BRL)** throughout.

---

## Page 1 — Executive Business Overview

### KPI cards
| Card | Measure | Expected | Format |
|---|---|---|---|
| Total Revenue | `[Total Revenue]` | R$ 13,494,400.74 | R$ 0.0M |
| Total Orders | `[Total Orders]` | 99,441 | #,##0 |
| Total Customers | `[Total Customers]` | 96,096 | #,##0 |
| Avg Order Value | `[Average Order Value]` | R$ 137.42 | R$ 0.00 |
| Median Order Value | `[Median Order Value]` | R$ 86.90 | R$ 0.00 |

> Median sits beside the mean deliberately. AOV is 58% above the median, so
> the mean alone overstates what a typical customer spends.

### Visuals
1. **Monthly revenue and orders** — line + column combo, X = `dim_date[YearMonth]`,
   filtered `InStableWindow = TRUE`. Columns = orders, line = `[Total Revenue]`.
   *This is the one acceptable dual-axis use: a count and a currency that
   share a time axis and are not being compared to each other.* If in doubt,
   split into two stacked charts.
2. **Month-over-month growth** — column chart of `[Revenue MoM %]`, conditional
   colour (green ≥ 0, red < 0). 2017-01 is blank by design (December 2016
   holds one order); optional line `[Revenue 3M Moving Avg]` starts at 2017-03.
3. **Revenue by state** — map or horizontal bar, top 12. Include a caption:
   *top 3 of 27 states = 63.4% of revenue*.
4. **Top 10 categories** — horizontal bar on `[Category Revenue]`.
5. **YoY card** — `[YoY Growth Jan-Aug %]` with the caption *"Jan–Aug
   like-for-like; full-year YoY is not meaningful (2016 has 329 orders)"*.

### Slicers
`dim_date[Year]` · `dim_date[YearMonth]` range · `customer_state` · `order_status`

---

## Page 2 — Customer Intelligence & Retention

### KPI cards
| Card | Measure | Expected |
|---|---|---|
| Total Customers | `[Total People]` | 96,096 |
| Repeat Purchase Rate | `[Repeat Purchase Rate]` | 3.12% |
| One-Time Customers | `[One-Time Customers]` | 93,099 |
| Avg Orders / Customer | `[Avg Orders Per Customer]` | 1.03 |
| Historical Customer Value | `[Historical Customer Value]` | R$ 13,494,400.74 |

### Visuals
1. **One-time vs repeat** — donut, 93,099 vs 2,997.
2. **RFM segments** — bar chart, customers *and* revenue share side by side.
   The gap between the two bars is the insight. Source:
   `rfm_customer_segments` filtered `rfm_scored = 1`; values
   `[Segment Customer Share]` and `[Segment Revenue Share]`; tooltip
   `[Customers In Segment]`, `[Segment Avg Historical Value]`.
3. **Customer value distribution** — histogram of `historical_value`, log scale.
4. **Cohort retention matrix** — rows `cohort_month`, columns months-since,
   values `[Cohort Retention %]`, conditional-formatted background. Source:
   `cohort_retention`. Unobserved cells are blank by design, not 0; exclude
   offset 0 (100%) from the colour scale.
5. **Purchase frequency** — column chart, orders-per-person distribution.

### ⚠ Mandatory on-page captions
These are not optional polish — without them the page misleads:

- On the **RFM visual**: *"Frequency is scored 1/3/5, not quintiles: 96.88%
  of customers have exactly one order, so quintile scoring would invent
  distinctions that do not exist."*
- On the **value card**: *"Historical value — what customers actually spent.
  This is NOT predicted lifetime value; a 3.12% repeat rate gives no basis
  for prediction."*
- On the **cohort matrix**: *"Later cohorts are right-censored — customers
  acquired near the data's end had little time to return. Compare cohorts of
  similar age only."*

All customer counts use `customer_unique_id`. If a card reads 99,441 the
model is counting `customer_id` and is wrong.

---

## Page 3 — Product & Category Analytics

### KPI cards
`[Category Revenue]` R$ 13,494,400.74 · `[Distinct Categories]` 74 ·
`[Category Items Sold]` 112,101 · `[Top Category Revenue]` R$ 1,255,695

**Category axes and slicers use `dim_category[category]`**, so one selection
filters revenue, products, sellers and satisfaction together. `[Category
Revenue Share]` and `[Category Rank]` are written for that axis.

### Visuals
1. **Revenue by category** — horizontal bar, top 15, sorted desc.
2. **Pareto curve** — cumulative % by category rank, with a reference line at
   80%. Caption: *18 of 74 categories reach 80% of revenue*.
3. **Monthly category trend** — line chart, top 5 categories over time
   (max 5 series; beyond that, fold into "Other").
4. **Category growth vs decline** — diverging bar, 2017 Q1 vs 2018 Q3,
   minimum 50 items in both periods.
5. **Category table** — revenue, items, orders, avg price, share, rank.

### Drill-through
From any category → a detail page showing that category's monthly trend
(`vw_category_performance`), top products (`product_performance`), top
sellers (`seller_category_performance`) and satisfaction
(`category_satisfaction`), all filtered through `dim_category`.

---

## Page 4 — Seller Performance

### KPI cards
`[Sellers With Revenue]` 3,053 · `[Seller Revenue]` · `[Largest Seller Share]`
1.70% · `[Seller Avg Delivery Days]` 12.51 · `[Seller Late Rate]` 8.02%

> Seller rates are **weighted** (from `seller_scorecard`) and counted per
> seller-order pair. The late-rate card reads 8.02%, not the Page 5 figure of
> 8.11%, because a multi-seller order counts once per seller. Card subtitle:
> *"across seller-order pairs"*. Never show `[Seller Orders]` (99,542 pairs) as
> an order count.

### Visuals
1. **Top 20 sellers by revenue** — horizontal bar.
2. **Seller concentration curve** — cumulative revenue share. Caption:
   *largest seller 1.70%; top 10% of sellers 67.5%*.
3. **Scorecard scatter** — X = late %, Y = inherited order rating, size =
   revenue. Median reference lines creating quadrants.
4. **Intervention table** — sellers with ≥100 orders and rating < 3.8,
   sorted by revenue. This is the actionable output of the page.

### ⚠ Mandatory caption
On both the scatter and the table:

> *"Reviews attach to the **order**, not the seller. In a multi-seller order
> every seller inherits the same score, so this is an inherited order rating,
> not an independent seller rating. Delivery delay is also not wholly within
> a seller's control — the carrier accounts for 74.2% of delivery time."*

Minimum 50 orders on any seller ranking; averages over tiny samples are
unstable and would put one-order sellers at both extremes.

Note `[Sellers With Revenue]` is **3,053**, not 3,095 — 42 sellers had only
canceled or unavailable orders.

---

## Page 5 — Order & Delivery Operations

### KPI cards
| Card | Measure | Expected |
|---|---|---|
| Delivered Orders | `[Delivered Orders]` | 96,478 |
| On-Time Rate | `[On-Time Delivery Rate]` | 91.89% |
| Avg Delivery Time | `[Avg Delivery Days]` | 12.56 days |
| Late Orders | `[Late Orders]` | 7,827 |
| Cancellation Rate | `[Cancellation Rate]` | 0.63% |
| Total Freight | `[Total Freight]` | R$ 2,241,126.29 |

### Visuals
1. **Order status distribution** — horizontal bar, log scale (delivered
   dwarfs everything else).
2. **Promised vs actual delivery** — two lines over time with the gap shaded.
   This is the page's most important visual.
3. **Delivery performance by state** — map or bar, coloured by late rate.
4. **Delivery time distribution** — histogram, median reference line.
5. **Delivery stage breakdown** — stacked bar from `delivery_stage_summary`
   (95,088 orders with valid stage timing): purchase→approval 0.40d,
   approval→carrier 2.85d, carrier→customer 9.36d (total 12.62d). Measures
   N18–N24 (`[Last Mile Share]` 74.21%) on `delivery_stage_orders` respond to
   state and date slicers.

### ⚠ Mandatory captions
- On the on-time card: *"Measured against Olist's own estimated date, which
  was padded by up to 27 days in early 2017. This reflects cautious promising
  as much as fast logistics."*
- On the stage breakdown: *"74.2% of delivery time is the carrier leg
  (95,088 orders whose four timestamps are in a valid order; 1,388 with
  missing or impossible timestamps excluded)."* The stage total (12.62d) uses
  a smaller population than the Avg Delivery Time card (12.56d, 96,476
  orders); label both.
- Denominator note: *"Delivery averages use the 96,476 orders with an actual
  delivery date, not the 96,478 marked delivered — 8 have no date recorded."*

---

## Page 6 — Customer Satisfaction

### KPI cards
| Card | Measure | Expected |
|---|---|---|
| Avg Review Score | `[Avg Review Score]` | 4.0864 |
| One-Star Rate | `[One-Star Rate]` | **11.51%** |
| Five-Star Rate | `[Five-Star Rate]` | 57.78% |
| Total Reviews | `[Total Reviews]` | 99,224 |

> One-star rate is a **headline card, not a footnote**. The distribution is
> J-shaped, so the 4.09 average describes almost nobody and hides the most
> actionable group.

### Visuals
1. **Review score distribution** — column chart, 1–5.
2. **Delivery delay vs review score** — show **both** analyses side by side
   (revised 2026-11-20, Insight 9): all reviews, and reviews answered after
   arrival only (`review_before_delivery = 0`), averaged per order. Axis
   `vw_review_summary[delivery_bucket]`; values `[Avg Order Rating (Review
   Table)]` and `[Avg Order Rating After Arrival]`. Card: `[Pre-Delivery
   Reviews]` 4,795.
   | Bucket | All reviews: avg / 1-star | After arrival: orders, avg / 1-star |
   |---|---|---|
   | 7–15 days early | 4.316 / 6.3% | 41,389 · 4.316 / 6.3% |
   | On time | 4.201 / 7.0% | 17,193 · 4.202 / 7.0% |
   | 1–7 days late | 3.184 / 29.5% | 3,055 · 3.860 / 11.1% |
   | 8–15 days late | 1.733 / 68.5% | 106 · 3.660 / 17.9% |
3. **Satisfaction trend** — monthly avg score and 1-star %, stable window.
4. **Category satisfaction** — best and worst rated, minimum 300 items, from
   `category_satisfaction` (review grain; after-arrival columns available):
   `[Category Avg Review Score]`, `[Category One-Star Rate]`, `[Category Avg
   Score After Arrival]`. These are blank at the total row by design (not
   additive across categories).
   Caption: *"Reviews rate the whole order, delivery included — not product
   quality alone."*

### ⚠ Mandatory caption
On the delay-vs-score visual:

> *"**Correlation, not causation.** A late delivery may share a root cause
> with a bad experience — an unreliable seller, a difficult address — rather
> than directly causing the low score. Note also that arriving very early
> buys nothing: 15+ days early scores 4.318 against 4.316 for 7–15 days
> early. 4,795 reviews were answered before the parcel arrived; the
> after-arrival bars exclude them."*

---

## Cross-cutting requirements

| Requirement | Implementation |
|---|---|
| Consistent theme | `RetailPulse_Theme.json` on every page |
| Currency | R$ with thousands separator, 2 dp |
| Navigation | Left sidebar on all six pages, current page highlighted |
| Cross-filtering | Within a page only (the aggregate tables are intentionally unrelated — see `data_model.md` §3) |
| Tooltips | Report-page tooltips on the trend and scatter visuals |
| Drill-through | Category detail (Page 3) and seller detail (Page 4) |
| Conditional formatting | Late rate and review score tables: green/amber/red |
| No decoration | No gauges, no 3-D, no pie beyond the single binary donut on Page 2 |
| Accessibility | Alt text on every visual; colour never the sole carrier of meaning |

### Design rules carried from the project's chart work
- **Never dual-axis two measures being compared** — two y-scales make
  unrelated series look correlated.
- Single-series visuals get no legend; the title names the series.
- Recessive gridlines; no chart junk.
- Direct labels on bars rather than forcing the reader to measure against an axis.
