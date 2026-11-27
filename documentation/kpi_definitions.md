# KPI Definitions

**Version 1.0** · 2026-11-12
**Status:** definitions validated against the raw data; **results not yet computed.**

> **Read this first.** Every formula below has been checked against the actual
> tables — the required columns exist, the joins work, and the denominators are
> known. **No KPI value is stated here.** Numbers appear in Phase 5 (analysis)
> and Phase 7 (insights), produced by code, never typed into a document.
>
> Three figures *are* quoted as raw totals because they were measured during
> profiling and are needed to explain the definitions:
> `SUM(order_items.price)` = 13,591,643.70,
> `SUM(order_items.freight_value)` = 2,251,909.54,
> `SUM(payments.payment_value)` = 16,008,872.12.

---

## Conventions that apply to every KPI

These exist so that two charts never disagree about what a word means.

| Rule | Definition |
|---|---|
| **Revenue** | `SUM(order_items.price)` — product revenue, **excluding freight** |
| **Revenue-eligible statuses** | All except `canceled` and `unavailable` |
| **Customer** | `customer_unique_id` (the person), **never** `customer_id` |
| **Order date** | `order_purchase_timestamp` — the date for all trends |
| **Trend window** | 2017-01 → 2018-08 (20 complete months) |
| **Totals window** | All data (2016-09 → 2018-10) |
| **Currency** | Brazilian Real (BRL), 2016–2018, no conversion |
| **Delivery denominator** | 96,476 orders with an actual delivery date |

### Why revenue is `order_items.price`, not `payments.payment_value`

The two differ by 165,318.88 (+1.04%), and the choice matters:

| | `SUM(order_items.price)` | `SUM(payments.payment_value)` |
|---|---|---|
| Value | 13,591,643.70 | 16,008,872.12 |
| Includes freight? | No | Yes |
| Attributable to a product / category / seller? | **Yes** | No |
| Orders covered | 98,666 | 99,440 |

`payment_value` cannot be broken down by product, category or seller, which
makes Modules 3 and 4 impossible. `order_items.price` can. Freight is reported
separately as a cost metric, not hidden inside revenue.

**Payments are still used** — for payment method mix and instalment behaviour,
which `order_items` cannot answer.

> ⚠ **Join warning.** `payments` has 103,886 rows against 99,440 orders. Joining
> it directly to orders multiplies rows and inflates every total. Always
> aggregate payments to order level *first*. The same applies to `reviews`
> (547 orders have more than one).

---

## Module 1 · Executive Business Overview

### KPI 1 — Total Revenue
**Business meaning:** total value of goods sold. The headline number.
**Formula:** `SUM(order_items.price)` where `order_status NOT IN ('canceled','unavailable')`
**Columns:** `order_items.price`, `orders.order_status`, `orders.order_id`
**Validated:** no nulls, no negatives, min 0.85, max 6,735.00.
**Limitations:**
- Excludes freight by definition. "Revenue including freight" is a separate measure.
- Revenue inside canceled/unavailable orders is 97,242.96 (0.72% of GMV), so the
  status filter barely moves the headline — but the rule must still be explicit.
- **Not profit.** No cost data exists anywhere in the dataset.

### KPI 2 — Total Orders
**Business meaning:** how many purchases were made.
**Formula:** `COUNT(DISTINCT orders.order_id)`
**Validated:** `order_id` confirmed unique across 99,441 rows.
**Limitations:** report *all* orders (99,441) for volume, but note that only
98,666 have line items. State which definition a chart uses.

### KPI 3 — Total Customers
**Business meaning:** how many distinct people bought.
**Formula:** `COUNT(DISTINCT customers.customer_unique_id)`
**Validated:** 96,096 distinct people vs 99,441 order-level IDs.
**Limitations:** ⚠ **Using `customer_id` gives 99,441 and is wrong.** It inflates
the count by 3.5% and makes repeat purchase rate collapse to zero.

### KPI 4 — Average Order Value (AOV)
**Business meaning:** average spend per order. Drives pricing and bundling decisions.
**Formula:** `SUM(order_items.price) / COUNT(DISTINCT order_items.order_id)`,
**both restricted to revenue-eligible orders** (status not canceled/unavailable).
**Validated:** 13,494,400.74 ÷ **98,199** eligible orders with items = **137.42 BRL**
(SQL, pandas and the Tableau measure check agree).
**Limitations:**
- ⚠ Numerator and denominator must describe **the same orders**. The
  denominator is eligible orders *with items* (98,199) — not all orders
  (99,441), and not all orders with items (98,666, which includes canceled
  ones and gives 137.75). Mixing populations, e.g. eligible revenue ÷
  all-status orders, silently understates AOV.
- The mean is sensitive to the long right tail (max item price 6,735). Report
  **median order value alongside the mean.**

**Comparing AOV over time — rules:**
- Compare **equal, complete periods** (Jan–Aug 2017 vs Jan–Aug 2018: 136.55 →
  137.14, **+0.4%**). Never compare two single months: January 2017 is a
  787-order ramp month and the highest-AOV month of the window (152.60), so a
  single-month endpoint comparison reports a spurious −13.4%.
- Always state the population and date range beside the figure.

### KPI 5 — Monthly Revenue
**Formula:** revenue grouped by `DATE_FORMAT(order_purchase_timestamp, '%Y-%m')`
**Limitations:** ⚠ Must be restricted to **2017-01 → 2018-08**. The four edge
months (4, 1, 16 and 4 orders) make an unrestricted chart appear to show a
collapse that did not happen.

### KPI 6 — Month-over-Month Growth
**Formula:** `(revenue_this_month − revenue_prev_month) / revenue_prev_month`
(SQL: `LAG()` window function; Tableau: `LOOKUP` with a `DATEDIFF` month guard, see `tableau/calculated_fields.md` M10)
**Limitations:** undefined for the first month. Only meaningful inside the
stable window: **both** months must be complete, so 2017-01 (vs December
2016's single order) is blank on the dashboard. The 3-month moving average (M11) likewise
needs three complete months and starts at 2017-03. `vw_monthly_revenue`'s
`mom_growth_pct` and `moving_avg_3m` do not apply this rule at the 2016/2017
boundary; don't quote them for 2016-12 to 2017-02. **Month-over-month % is a volatility measure, not a growth
rate** — never average it to describe overall growth (see KPI 6a).

### KPI 6a — Compound Monthly Growth Rate (CMGR)
**Business meaning:** the single constant monthly rate that takes revenue from
the first month of a period to the last. This is the figure to quote for
"how fast did revenue grow?".
**Formula:** `(revenue_last_month / revenue_first_month) ^ (1 / intervals) − 1`,
where `intervals` = number of months − 1.
**Validated (SQL and pandas agree):**

| Period | Start → end (BRL) | Intervals | CMGR |
|---|---|---|---|
| 2017, Jan → Dec | 120,098.27 → 742,183.79 | 11 | **+18.01%** |
| 2018, Jan → Aug | 945,456.29 → 848,860.10 | 7 | **−1.53%** |

**Limitations:**
- ⚠ **Do not substitute the arithmetic mean of monthly % changes.** For 2017
  that gives +22.69% (inflated by one +104% jump from a small January base);
  for 2018 it gives +2.45% — showing growth where revenue actually declined.
- CMGR depends on its two endpoint months. Check it against a log-linear trend
  fitted to every month (2017: +15.1%/month; 2018: −1.1%/month). When the two
  agree in sign and rough size, the conclusion does not depend on endpoint choice.

### KPI 7 — Year-over-Year Growth
**Formula:** 2018 Jan–Aug revenue vs 2017 Jan–Aug revenue.
**Limitations:** ⚠ **A full-year YoY comparison is not possible.** 2016 holds
329 orders against 45,101 in 2017 — a +13,600% figure that is arithmetically
correct and completely misleading. Only the like-for-like Jan–Aug comparison is
reported.

### KPI 8 — Revenue by State / City
**Formula:** revenue grouped by `customers.customer_state` / `customer_city`
**Validated:** 27 states, 4,119 city values, no nulls.
**Limitations:** city names are lowercase and unnormalised (spelling variants
exist). **State-level analysis is reliable; city-level needs cleaning first.**

---

## Module 2 · Customer Intelligence & Retention

> ### ⚠ The constraint that governs this entire module
> **Only 3.12% of customers ever placed a second order** (2,997 of 96,096).
> 96.88% ordered exactly once. This is a real property of the marketplace, not
> a data error, and it limits what retention analysis can honestly claim.
> Every KPI below is written with that in mind.

### KPI 9 — Repeat Purchase Rate
**Business meaning:** share of customers who came back. The core loyalty metric.
**Formula:** `COUNT(customer_unique_id with >1 order) / COUNT(DISTINCT customer_unique_id)`
**Validated:** 2,997 of 96,096 people.
**Limitations:**
- ⚠ Must use `customer_unique_id`. With `customer_id` the answer is always 0%.
- The 25-month window truncates behaviour: someone who bought in August 2018
  had little chance to return before the data ends.
- **Same-day second orders (added 2026-11-27, `sql/11` E1).** 897 of the 2,997
  repeat customers (29.9%) placed their second order on the same day as the
  first, 863 within an hour, which looks like a split checkout. The stricter
  "came back on a later day" rate is **2.19%** (2,100 people; median gap 72
  days). Report 3.12% as the KPI and state the 2.19% beside it.

### KPI 10 — Customer Purchase Frequency
**Formula:** `COUNT(DISTINCT order_id) / COUNT(DISTINCT customer_unique_id)`
**Limitations:** the mean will sit just above 1.0 and is nearly uninformative.
**Report the distribution instead** (1, 2, 3, 4+ orders), which is.

### KPI 11 — RFM Segmentation
**Business meaning:** group customers by Recency (how recently), Frequency (how
often) and Monetary value (how much), then act differently on each group.

**Method:**
- **Population:** people with revenue-eligible orders that have items (94,983)
- **R** = days from the customer's last eligible order to the dataset's maximum
  date (2018-10-17), scored 1–5 by quintile (lower days = better score)
- **F** = order count. ⚠ **Not quintiles** — with 96.88% of customers at
  exactly 1 order, quintile scoring is impossible (most customers tie). F is
  scored as a small ordinal: **1 order = 1, 2 orders = 3, 3+ orders = 5**
- **M** = total historical revenue, scored 1–5 by quintile
- **Quintiles are tie-consistent** (2026-11-20): `score = 1 + floor(5 × (rank − 1) / N)`
  with tied values sharing the lowest rank, so identical customers always get
  the same score. Used identically by SQL Q32, notebook 03 §B2 and
  `rfm_customer_segments.csv`.

**Segments:** Champions · Loyal Customers · Potential Loyalists · At Risk · Lost
(exact score boundaries defined and justified in Phase 5).

**Limitations:**
- ⚠ The F dimension carries little information here. **This must be stated
  wherever RFM appears**, in the dashboard and in interviews.
- Recency is measured against the dataset end date, not today.

### KPI 12 — Customer Lifetime Value (proxy)
**Formula:** `SUM(order_items.price)` per `customer_unique_id` over the full window.
**Limitations:**
- ⚠ **This is historical value, not predicted lifetime value.** A true CLV model
  needs a churn or repeat-rate model; with 3.12% repeat behaviour there is no
  reliable basis for prediction.
- It will be labelled **"Historical Customer Value"** on every dashboard. The
  distinction between measured and predicted is the point.

### KPI 13 — Cohort Retention
**Method:** group customers by first-purchase month, then measure the share
active in each following month. Offsets are **calendar months** (February after
a January first order = 1), only activity up to 2018-08 counts, and months a
cohort could not yet reach are **blank, never 0**. Used identically by SQL Q33,
notebook 03 §B3 and `cohort_retention.csv` (2026-11-20).
**Limitations:** retention will be very low and the curves nearly flat — that is
the honest answer, not a broken chart. Later cohorts have fewer months to be
observed in (right-censoring) and must not be compared directly with earlier ones.

---

## Module 3 · Product & Category Intelligence

### KPI 14 — Category Revenue & Contribution
**Formula:** revenue grouped by `product_category_name_english`;
contribution = category revenue / total revenue
**Limitations:** ⚠ **LEFT JOIN to the translation table**, or 13 products in 2
untranslated categories vanish. 610 products have no category and are grouped
as `unknown`.

### KPI 15 — Product Performance Ranking
**Formula:** rank products by revenue and by order frequency (SQL `RANK()` /
`ROW_NUMBER()`).
**Limitations:** "lowest-selling" is ambiguous for the long tail — many products
sold once. Define the bottom group by a **minimum order threshold**, not by rank
alone, or the list is just noise.

> **No profit or margin KPI exists.** The dataset has no product cost column.
> Any margin figure would be invented. This is a stated limitation, not an
> oversight.

---

## Module 4 · Seller Performance Analytics

### KPI 16 — Seller Revenue & Order Volume
**Formula:** revenue and `COUNT(DISTINCT order_id)` grouped by `seller_id`
**Validated:** all 3,095 sellers appear in `order_items`; the busiest appears
on 2,033 lines.
**Limitations:** ⚠ An order can contain items from **several sellers**. Order
counts per seller therefore sum to more than total orders. Say so on the chart.

### KPI 17 — Seller Delivery Performance
**Formula:** average `delivery_days` and late-delivery rate per seller.
**Limitations:**
- ⚠ Delivery delay is **not wholly the seller's fault** — the carrier and the
  customer's distance matter. Attributing it entirely to the seller is unfair
  and would be a weak interview answer.
- Sellers with very few orders produce unstable averages. **Apply a minimum
  order threshold (e.g. 20) before ranking.**
- **Totals across sellers must be weighted** (added 2026-11-20): `SUM(late
  orders) / SUM(measurable orders)` from `seller_scorecard`, not the average of
  per-seller rates (8.42% unweighted vs **8.02%** weighted). The weighted seller
  figure counts seller-order pairs, so it differs from the platform's 8.11% at
  order grain: multi-seller orders count once per seller and were late only
  1.38% of the time.

### KPI 18 — Seller Review Score
**Formula:** average `review_score` of orders containing that seller's items.
**Limitations:** ⚠ The review is attached to the **order**, not the seller. In a
multi-seller order, every seller inherits the same score. Document this
attribution rule.

---

## Module 5 · Order & Delivery Operations

### KPI 19 — Average Delivery Time
**Formula:** `AVG(order_delivered_customer_date − order_purchase_timestamp)` in days
**Validated:** 96,476 orders have a real delivery date. Range 0.53–209.63 days,
no negatives.
**Limitations:**
- Denominator is **96,476**, not 99,441 or 96,478 (8 delivered orders lack a date).
- Strongly right-skewed — **report the median alongside the mean.**
- Measured from purchase, not from dispatch, so it includes payment approval time.
- Unaffected by Q18: it uses only the purchase and delivery timestamps.

### KPI 19a — Delivery-Stage Breakdown (added 2026-11-20)
**Business meaning:** which stage of the journey (payment approval, seller
dispatch, carrier) holds the delivery time.
**Population:** `stage_timing_valid = 1`, meaning all four timestamps present
and purchase ≤ approval ≤ carrier ≤ customer. **95,088 orders.**
**Formula:** for each stage, `AVG(TIMESTAMPDIFF(SECOND, start, end)) / 86400`;
share = `SUM(stage seconds) / SUM(purchase→delivery seconds)`. Stages sum
exactly to the total on this population.
**Validated:** 0.40 / 2.85 / 9.36 days, total 12.62; last-mile share **74.2%**.
Same figures in MySQL and pandas.
**Limitations:**
- Excludes 1,373 orders with an impossible sequence (1,350 Q18 carrier before
  approval, 23 Q08 customer before carrier) and 15 with a missing approval or
  carrier timestamp. Do **not** compute stages on all orders: negative stages
  would cancel against positive ones.
- Use exact seconds. Truncating each stage to whole hours (the superseded
  method) drops up to 59 minutes per stage.

### KPI 20 — On-Time Delivery Rate
**Formula:** `COUNT(order_delivered_customer_date <= order_estimated_delivery_date) / 96,476`
**Validated:** computable for all 96,476 orders with a delivery date.
**Limitations:**
- ⚠ "On time" is measured against Olist's **own estimate**, not an objective
  standard. If estimates are padded, a high score reflects conservative
  promising rather than fast delivery. Profiling shows orders arrive on average
  **11 days early**, which strongly suggests padding. **Module 5 must examine
  the estimate itself**, not just the pass rate — this is one of the more
  interesting findings available in this dataset.
- Undelivered orders are excluded, so the rate describes delivered orders only.

### KPI 21 — Cancellation Rate
**Formula:** `COUNT(order_status = 'canceled') / COUNT(*)`
**Validated:** 625 of 99,441.
**Limitations:** `unavailable` (609 orders) is arguably also a failure to fulfil.
Report both separately rather than merging them.

### KPI 22 — Freight Cost Analysis
**Formula:** `SUM(freight_value)`; freight ratio = freight / price
**Validated:** total 2,251,909.54; 383 items ship free.
**Limitations:** this is freight **charged**, not Olist's freight cost. It is a
revenue component from the platform's side, not a margin input.

---

## Module 6 · Customer Satisfaction & Reviews

### KPI 23 — Average Review Score
**Formula:** `AVG(review_score)`
**Validated:** mean 4.0864 across 99,224 reviews; all scores within 1–5.
**Limitations:** ⚠ The distribution is **J-shaped** (57.8% five-star, 11.5%
one-star, little in between), so the mean describes almost nobody. **Always
show the distribution with the average.** Coverage is 99.23% of orders.

### KPI 24 — Rating Distribution & 1-Star Share
**Formula:** count and share of each score 1–5.
**Validated:** 1★ 11,424 · 2★ 3,151 · 3★ 8,179 · 4★ 19,142 · 5★ 57,328.
**Limitations:** voluntary-response bias — people review when delighted or
angry, so this is not a representative satisfaction survey.

### KPI 25 — Delivery Delay vs Rating
**Business meaning:** does late delivery actually cost satisfaction? If so, the
delivery investment case writes itself.
**Formula:** average `review_score` bucketed by `delay_days`.
**Validated:** both columns exist for 96,476 orders; 7,827 (8.11%) were late.
**Limitations:**
- ⚠ **Correlation, not causation.** A late delivery may share a cause with a bad
  experience (a poor seller) rather than causing it.
- Needs a **LEFT JOIN** on reviews, and reviews aggregated to one score per
  order first.
- ⚠ **Review timing (Q19, added 2026-11-20).** 4,795 reviews (4.98%) were
  answered *before* the order arrived, because the survey goes out about two
  days after the estimated date when the parcel is late. They average 1.80
  stars. Always report KPI 25 **twice**: all reviews, and reviews with
  `review_before_delivery = 0` only. Filter at **review** grain, then average
  per order. Denominator = delivered orders with ≥ 1 qualifying review. Use
  `review_answer_timestamp`, not `review_creation_date` (a date-only send date).
- After-arrival samples beyond 7 days late are small (106 and 19 orders), so
  show confidence intervals there. SQL: `05_advanced_sql.sql` Q26 / Q26b.

---

## KPI readiness summary

| # | KPI | Computable? | Main caveat |
|---|---|---|---|
| 1 | Total Revenue | ✅ | Excludes freight by definition; no profit possible |
| 2 | Total Orders | ✅ | 99,441 total vs 98,666 with items |
| 3 | Total Customers | ✅ | **Must** use `customer_unique_id` |
| 4 | Average Order Value | ✅ | Denominator 98,199 (eligible with items); compare equal periods only; report median too |
| 5 | Monthly Revenue | ⚠ | Restrict to 2017-01 → 2018-08 |
| 6 | MoM Growth | ⚠ | Stable window only; volatility view, not a growth rate |
| 6a | CMGR | ✅ | 2017 +18.01%, 2018 Jan–Aug −1.53%; cross-check with log-linear trend |
| 7 | YoY Growth | ⚠ | **Jan–Aug 2018 vs Jan–Aug 2017 only** |
| 8 | Revenue by Geography | ⚠ | State reliable; city needs cleaning |
| 9 | Repeat Purchase Rate | ✅ | Only 3.12% — low by nature |
| 10 | Purchase Frequency | ⚠ | Mean uninformative; show distribution |
| 11 | RFM Segmentation | ⚠ | **F dimension nearly degenerate** |
| 12 | CLV proxy | ⚠ | **Historical value, not predicted** |
| 13 | Cohort Retention | ⚠ | Flat curves; right-censoring |
| 14 | Category Revenue | ⚠ | LEFT JOIN; 610 `unknown` |
| 15 | Product Ranking | ⚠ | Needs a minimum-order threshold |
| 16 | Seller Revenue | ✅ | Orders span multiple sellers |
| 17 | Seller Delivery | ⚠ | Not solely the seller's fault; min threshold |
| 18 | Seller Review Score | ⚠ | Review is order-level, not seller-level |
| 19 | Avg Delivery Time | ✅ | Denominator 96,476; show median |
| 20 | On-Time Rate | ⚠ | **Measured against a possibly padded estimate** |
| 21 | Cancellation Rate | ✅ | Report `unavailable` separately |
| 22 | Freight Analysis | ✅ | Charged, not cost |
| 23 | Avg Review Score | ⚠ | J-shaped; show distribution |
| 24 | Rating Distribution | ✅ | Voluntary-response bias |
| 25 | Delay vs Rating | ⚠ | Correlation, not causation |

**Not computable from this dataset — and why:**

| Metric | Reason |
|---|---|
| Profit / margin / COGS | No cost column exists in any table |
| True predictive CLV | 3.12% repeat rate gives no basis for prediction |
| Customer acquisition cost | No marketing spend data |
| Inventory / stock metrics | No inventory table |
| Returns / refunds | Not recorded (no negative values anywhere) |
| Customer demographics | Anonymised — no age, gender or income |
| Website / funnel behaviour | No clickstream data |
