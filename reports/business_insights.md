# RetailPulse — Business Insights & Strategic Recommendations

**Prepared:** 2026-11-13
**Analyst:** Manish
**Data:** Olist Brazilian e-commerce marketplace, **September 2016 – October 2018**
**Scope:** 99,441 orders · 96,096 customers · 3,095 sellers · 13.59M BRL gross merchandise value

---

> ## ⚠ Read this first
>
> **These findings describe a historical period (2016–2018), not current
> business performance.** The dataset ends on 17 October 2018. Every trend,
> rate and recommendation below refers to how the marketplace behaved then.
> Anything described as "current" or "today" would be wrong.
>
> **No profit or margin figure appears anywhere in this report.** The dataset
> contains no product cost data, so margin cannot be calculated. All revenue
> figures are *product revenue* (`order_items.price`), excluding freight,
> which is reported separately.

---

## Executive summary

Olist in this period was a **fast-growing acquisition machine that stopped
growing, serving customers who never came back, with a delivery operation
that determined whether they were happy.**

Five things stand out:

1. **Growth stalled, then turned slightly negative.** Compound monthly revenue
   growth was **+18.0% across 2017** (Jan→Dec) and **−1.5% across Jan–Aug 2018**.
   Revenue plateaued at roughly 850–1,000k BRL/month.

2. **All growth came from new buyers, none from bigger baskets.** Comparing
   Jan–Aug 2018 with Jan–Aug 2017, orders grew **+137.3%** while average order
   value was **flat (+0.4%)**. Basket size has never been worked on.

3. **Customers do not come back.** Only **3.12%** ever placed a second order.
   Every cohort retained under 4.5%. This is not a leaky bucket — there is
   barely a bucket.

4. **The best customers are strangers.** The top 10% of spenders hold 41% of
   revenue, but **93% of the top 1% placed exactly one order**. There is no
   loyal elite to reward.

5. **Late delivery is strongly associated with lower satisfaction, but part
   of the effect is a survey-timing artefact.** Across all reviews, orders 1–7
   days late average **3.18** stars against 4.20 on time, and orders 8–15 days
   late average 1.73. Most of that 1.73 comes from customers who answered the
   survey **before their parcel arrived** (Olist sends it about two days after
   the promised date). Counting only reviews answered after arrival, 1–7 days
   late averages **3.86** and 8–15 days late **3.66** (small sample, n = 106).
   The association holds; the "cliff" does not.

**The strategic read:** with retention structurally near zero, the levers that
remain are (a) basket size, which is untouched, and (b) delivery reliability,
which is strongly associated with satisfaction and with the small amount of
repeat behaviour that does exist.

**Every number in this report was re-verified against the MySQL database on
2026-11-13**, independently of the earlier phase reports. The growth and AOV
figures in Insights 1 and 2 were corrected on 2026-11-20 and re-verified in
both SQL and pandas. Insights 9, 12 and 13 were re-tested on 2026-11-20 after a
data-quality investigation of two timestamp issues (Q18, Q19); Insight 9 was
revised, Insight 12 confirmed and Insight 13 strengthened.

---

## How to read an insight

Each insight below follows the same five-part structure: the **business
question**, the **method** (with the exact file and query), the **verified
finding**, what it **means**, and what to **do about it**.

Where a relationship is an association rather than a proven cause, it says so.
Where the evidence is thin, it says that too.

---

# A · Revenue and Business Growth

## Insight 1 — Growth stopped in 2018; the business plateaued

**1. Business question**
Is the marketplace still growing, or has expansion flattened?

**2. Analysis method**
Monthly eligible product revenue from `vw_monthly_revenue`, with
month-over-month growth via a `LAG()` window function.
Source: [`sql/05_advanced_sql.sql`](../sql/05_advanced_sql.sql) Q21 ·
[`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §A1 ·
chart [`A1_revenue_trend_and_mom_growth.png`](eda_charts/A1_revenue_trend_and_mom_growth.png)

Restricted to the **stable analysis window 2017-01 → 2018-08** (20 complete
months, 99.65% of all orders). The dataset's edge months hold just 4, 1, 16
and 4 orders and November 2016 is absent entirely, so including them would
show a collapse that never happened.

**3. Actual finding**

Growth is measured as the **compound monthly growth rate (CMGR)** — the
constant monthly rate that turns the first month's revenue into the last
month's: `(end ÷ start)^(1 ÷ intervals) − 1`.

| Period | Start → end revenue (BRL) | Intervals | **CMGR** | Log-linear trend (all months) |
|---|---|---|---|---|
| 2017 (Jan → Dec) | 120,098.27 → 742,183.79 | 11 | **+18.01%** | +15.1% |
| 2018 (Jan → Aug) | 945,456.29 → 848,860.10 | 7 | **−1.53%** | −1.1% |

The log-linear trend fits every month rather than only the two endpoints, and
confirms the same picture: strong growth through 2017, a slight decline in
2018. The 2018 decline is therefore not an artefact of which months were
chosen as start and end.

> **Correction (2026-11-20).** An earlier version of this insight reported
> the *arithmetic mean of month-over-month % changes* (+22.69% for 2017,
> +2.45% for 2018) as if it were the growth rate. That measure is not a
> growth rate: it is inflated by one +104% jump from a small January 2017
> base, and it showed 2018 as mildly *growing* when revenue in fact
> *declined*. The month-over-month series remains valid as a volatility view
> (chart A1, lower panel) but is no longer used to describe overall growth.

Revenue rose from 120,098 BRL (Jan 2017) to a plateau around 850–1,000k BRL
through 2018. The single peak month is **November 2017 at 1,003,862 BRL**
(Black Friday) — the only month to exceed 1M. December then *fell* to 742,184,
so the spike pulled demand forward rather than establishing a higher level.

**4. Business implication**
The business moved from rapid expansion to a plateau — and a slight decline —
in roughly 18 months. The decline is small (about −1.5% a month), but it
means the growth model that worked in 2017 had exhausted itself by 2018. Whatever drove 2017 — marketplace expansion,
seller onboarding, category breadth — had stopped producing incremental
revenue.

**5. Recommended action**
Treat 2018 as the baseline, not a disappointment, and shift planning from
"how do we keep growing at 20%?" to "which specific lever moves a flat
business?". Insights 2, 5 and 7 identify the three candidates: basket size,
first-to-second purchase conversion, and delivery reliability. Commit to
measuring one of them as a controlled change rather than assuming growth
resumes on its own.

**Classification:** Decision-ready: plan from the 2018 plateau (measured: compound monthly growth −1.5%). Hypothesis to test: the effect of any one growth lever.

---

## Insight 2 — Every bit of growth came from more orders, none from bigger ones

**1. Business question**
Did the business grow by acquiring more buyers, or by getting more from each?

**2. Analysis method**
A like-for-like comparison of **January–August 2018 against January–August
2017** — the only comparable period, because 2016 holds just 329 orders and
2018 stops in August. AOV uses the KPI definition from
`documentation/kpi_definitions.md`: eligible product revenue ÷ **eligible
orders that have line items** (canceled and unavailable orders excluded from
both numerator and denominator). Verified independently in SQL
([`sql/05_advanced_sql.sql`](../sql/05_advanced_sql.sql) Q22) and pandas
([`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §A2) ·
chart [`A2_growth_decomposition_indexed.png`](eda_charts/A2_growth_decomposition_indexed.png)

**3. Actual finding**

| Jan–Aug, eligible orders with items | 2017 | 2018 | Change |
|---|---|---|---|
| Orders | 22,562 | 53,530 | **+137.3%** |
| Product revenue (BRL) | 3,080,850.81 | 7,341,037.41 | **+138.3%** |
| **Average order value** | **136.55 BRL** | **137.14 BRL** | **+0.4%** |

Revenue grew almost exactly in step with order volume. **AOV was flat.**
Across all 20 stable-window months, monthly AOV stayed in a narrow band
(124.76–152.60 BRL, mean 138.59, standard deviation 7.44) with no trend.

> **Correction (2026-11-20).** An earlier version reported AOV "falling
> 13.4%" by comparing two single months: January 2017 (152.60 BRL) and
> August 2018 (132.20 BRL). January 2017 is a 787-order ramp-up month and
> happens to be the **highest-AOV month of the entire 20-month window**, so
> that comparison starts from an outlier. Over comparable periods AOV did not
> fall — it did not move. The recommendation below is unchanged: a flat AOV
> is still an untouched lever.
>
> **Why other reports show slightly different figures.** The Phase 2
> spreadsheet report counts **all-status** orders for volume (22,968 →
> 53,991, +135.1%); that is a legitimate "orders placed" measure but it is not
> the AOV denominator. Single-month endpoints (787 → 6,421 orders) describe
> the ramp from launch and are not comparable periods.

Overall AOV across the full period is **137.42 BRL**, against a **median order
value of 86.90 BRL** — the mean sits 58% above the median because of a long
tail of expensive orders.

**4. Business implication**
The marketplace scaled by adding buyers one order at a time. Nothing in the
product — bundling, cross-sell, free-shipping thresholds, recommendations —
has measurably increased what a customer puts in a basket. Combined with the
plateau in Insight 1, this means the one growth engine that existed has
stalled and no second engine was ever built.

Note also that reporting AOV alone overstates the typical customer: half of
all orders are under 87 BRL.

**5. Recommended action**
Make AOV an explicit, owned KPI with a target — it currently behaves like a
number nobody is responsible for. The cheapest tests are a free-shipping
threshold set just above the median order value (~87 BRL), and
frequently-bought-together recommendations in the top categories from
Insight 7. Report median order value alongside the mean so the target
reflects typical customers rather than the tail.

> **Evidence for the free-shipping test** (added 2026-11-27, `sql/11` E2,
> checked in pandas). Freight is a heavy share of small orders and falls with
> order value: **48.5%** of product value under 50 BRL, **27.5%** at 50–86.90
> BRL, **21.2%** at 86.90–120 BRL and **6.2%** above 500 BRL. In the band just
> above the median, freight averages **21.81 BRL per order**: the per-order
> cost a threshold there would absorb. The dataset has no cost or margin
> data, so whether bigger baskets would pay for it **cannot be judged here**.
> It is a hypothesis for an A/B test, not a decision.
>
> **Threshold impact** (`sql/11` E3–E4, checked in pandas). Because 86.90 BRL
> is the *median* order, **49,119 orders (50.0%) already clear it** without
> any change in behaviour. Absorbing their freight in full would cost
> **1,423,461.81 BRL**: 63.5% of all freight and 10.5% of product revenue.
> Only **6,869 orders (7.0%)** fall just below it (70.00–86.89 BRL), the one
> group a threshold could plausibly move. Freight also weighs very
> differently across the country: **13.8%** of order value in São Paulo
> versus **22.7%** in the North (average 17.37 vs 41.39 BRL per order), and
> 15.7% for single-item versus 22.1% for multi-item orders. A threshold at the
> median would therefore mostly subsidise orders that happen anyway. A test
> should try a **higher or region-specific threshold** and measure the change
> in the near-miss band. No conversion or revenue effect can be claimed from
> this data.

**Classification:** Decision-ready: make AOV an owned KPI (AOV flat at +0.4% is measured). Hypothesis to test: the free-shipping threshold and bundles (no cost or conversion data; half of orders already clear the median).

---

## Insight 3 — Geographic concentration, not seller or category risk, is the structural exposure

**1. Business question**
Where is the business most fragile — if one thing went wrong, what would hurt?

**2. Analysis method**
Revenue share and cumulative share by `customer_state`, compared against the
equivalent concentration for categories and sellers.
Source: [`sql/05_advanced_sql.sql`](../sql/05_advanced_sql.sql) Q23 (ranking
window functions) · [`sql/04_joins_and_aggregations.sql`](../sql/04_joins_and_aggregations.sql) Q11, Q14 ·
[`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §A3 ·
chart [`A3_revenue_by_state_pareto.png`](eda_charts/A3_revenue_by_state_pareto.png)

**3. Actual finding**

| State | Orders | Revenue (BRL) | Share | Cumulative | AOV |
|---|---|---|---|---|---|
| SP (São Paulo) | 41,127 | 5,163,867 | **38.27%** | 38.27% | **125.56** |
| RJ (Rio de Janeiro) | 12,698 | 1,811,623 | 13.43% | 51.69% | 142.67 |
| MG (Minas Gerais) | 11,496 | 1,573,508 | 11.66% | **63.35%** | 136.87 |

**Three of 27 states produce 63.4% of revenue.**

By contrast:

| Dimension | Concentration |
|---|---|
| States | Top 3 of 27 = **63.4%** |
| Categories | Top 10 of 74 = 62.4%; 18 categories needed to reach 80% |
| Sellers | Largest single seller = **1.70%**; top 10 = 13.2% |

Note that SP has the **lowest AOV** of the three — it wins on volume, not
basket size.

**4. Business implication**
This inverts normal retail intuition. The catalogue is well diversified and no
single seller is close to critical — losing the biggest seller would cost
1.7% of revenue. But the business is **structurally dependent on the São
Paulo region**. A logistics disruption, a regional competitor, or a regulatory
change affecting the southeast would hit roughly two-thirds of revenue at once.

**5. Recommended action**
Stop treating seller diversification as the main risk-management activity and
start treating geographic reach as one. Before investing in expansion, read
Insight 9 — the under-served states are also the ones with the worst delivery
performance, and the two facts are probably connected.

**Classification:** Decision-ready: treat geography as the main concentration risk (3 states = 63.4% of revenue). Hypothesis to test: that better delivery would grow volume there (correlation only).

---

# B · Customer Intelligence

## Insight 4 — Only 3.12% of customers ever return; this is an acquisition business, not a retention one

**1. Business question**
Do customers come back, and is a retention strategy viable?

**2. Analysis method**
Order counts per **`customer_unique_id`** — the identifier for a *person*.
This distinction is critical: `customer_id` is unique per *order* (99,441
values), and using it would make every buyer look brand new and force the
repeat rate to zero.
Source: [`sql/06_customer_analytics.sql`](../sql/06_customer_analytics.sql) Q28–Q30 ·
`vw_customer_summary` · [`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §B

**3. Actual finding**

| | Value |
|---|---|
| Distinct people | **96,096** |
| Placed exactly one order | **93,099 (96.88%)** |
| Placed two or more | **2,997 (3.12%)** |
| Mean orders per person | 1.0348 |
| Most orders by one person | 17 |

**Time to the second order** (added 2026-11-27, `sql/11_insight_evidence.sql`
E1, checked in pandas): **897 of the 2,997 repeat customers (29.9%) placed
their second order on the same day as the first, 863 of them within an
hour.** Those look like a split checkout rather than a return visit. Counting
only second orders on a later day, **2,100 people (2.19%) came back**; their
median gap was **72 days** (interquartile range 23–177), 55.3% returned within
90 days and 75.7% within 180. The 3.12% headline keeps the project's
definition (2+ orders); 2.19% is the stricter "came back another day" view.

Cohort analysis confirms it independently: of customers acquired in each 2017
month, the share who returned (by 2018-08) ranges from **1.75% to 4.32%**,
with a mean of **3.07%** across 2017 cohorts. Every cell in the monthly retention
matrix is below 1.5%.
Chart: [`B3_cohort_retention_heatmap.png`](eda_charts/B3_cohort_retention_heatmap.png)

> *Method note:* cohorts and offsets use **calendar months**, the project
> convention since 2026-11-20 in SQL Q33, notebook 03 and the dashboard source
> `cohort_retention.csv` (all three agree). Only activity up to 2018-08 counts,
> and months a cohort could not yet reach are blank, not 0. (Historical: Q33
> once used elapsed whole months, which gave 3.93% for the best cohort.)
>
> *Right-censoring:* customers acquired in mid-2018 had only weeks before the
> data ends, so later cohorts look worse than they are. Compare cohorts of
> similar age only.

**4. Business implication**
This is a structural property of the marketplace, not a fixable leak. Customers
arrive via search for a specific product, buy once, and never form a
relationship with the platform. Any business plan assuming repeat revenue
would be building on sand — and conversely, the cost of acquiring each order
must be justified by that **single** order, because on average there is no second.

**5. Recommended action**
Make the acquisition-economics assumption explicit in planning: model customer
value at roughly **one order**, not a lifetime. Before funding any loyalty
initiative, run a small controlled test of post-purchase follow-up on recent
first-time buyers (Insight 6 identifies the target group) and require it to
beat the 3.12% baseline before scaling. Do not assume a loyalty programme will
work here simply because it works elsewhere.

**Classification:** Decision-ready: plan on about one order per customer (3.12%; 2.19% returned on a later day). Hypothesis to test: whether post-purchase follow-up beats that baseline (holdout test).

---

## Insight 5 — The highest-value customers are one-time buyers, not loyal ones

**1. Business question**
Is there a high-value customer core worth protecting with a VIP programme?

**2. Analysis method**
Customers ranked by historical revenue from `vw_customer_summary`, then — the
decisive step — checking **how many orders those top spenders actually placed**.
Source: [`sql/06_customer_analytics.sql`](../sql/06_customer_analytics.sql) Q31 ·
[`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §B1 ·
chart [`B1_customer_value_lorenz.png`](eda_charts/B1_customer_value_lorenz.png)

**3. Actual finding**

Value *is* concentrated, though less than a textbook 80/20:

| Top decile | People | Revenue share | Cumulative |
|---|---|---|---|
| 1st (top 10%) | 9,499 | **41.14%** | 41.1% |
| 2nd | 9,499 | 15.54% | 56.7% |
| 3rd | 9,499 | 11.06% | 67.7% |

But the composition is the finding:

| Group | People | Placed exactly ONE order | Mean orders | Mean value |
|---|---|---|---|---|
| **Top 1% of spenders** | 950 | **92.9%** | 1.09 | 1,626 BRL |
| Top 2–5% | 3,800 | 90.8% | 1.13 | 629 BRL |
| Top 6–10% | 4,750 | 91.0% | 1.10 | 341 BRL |
| Everyone else | 85,483 | 97.5% | 1.03 | 93 BRL |

**4. Business implication**
The "best customers" are people who made one expensive purchase and left. They
displayed no loyalty behaviour, so there is nothing to reward and no
relationship to deepen. A VIP programme aimed at the top 1% would be marketing
to 950 people who have already gone, 93% of whom were never repeat buyers in
the first place.

What the concentration *does* show is that order value varies enormously —
the top 1% average 1,626 BRL against 93 BRL for everyone else — which supports
Insight 2's argument that basket size is the real opportunity.

**5. Recommended action**
Do not build a loyalty or VIP tier. Instead, investigate *what* the top 1%
bought: if high-value orders cluster in particular categories or price bands,
that is a merchandising opportunity to move more customers up the value curve.
Target the behaviour (large basket), not the person (who has left).

**Classification:** Decision-ready: do not build a VIP tier (93% of the top 1% bought once). Open analysis: what the top 1% bought has not been studied yet.

---

## Insight 6 — "Potential Loyalists" hold 34% of revenue; Champions hold 2.3%

**1. Business question**
Which customer segment is actually worth a marketing budget?

**2. Analysis method**
RFM segmentation of the 94,983 people with revenue-eligible orders. Recency
measured from the person's last eligible order to the dataset end date
(2018-10-17), **not today**. R and M scored in **tie-consistent quintiles**:
customers with identical recency or spend always share a score.
Source: [`sql/06_customer_analytics.sql`](../sql/06_customer_analytics.sql) Q32 ·
[`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §B2 ·
`tableau/data/analytical/rfm_customer_segments.csv` (all three agree customer by customer) ·
chart [`B2_rfm_segments_customers_vs_revenue.png`](eda_charts/B2_rfm_segments_customers_vs_revenue.png)

> **Corrected 2026-11-20.** The first version of this insight used `NTILE(5)`,
> which splits customers with identical values across two scores arbitrarily.
> Its counts (21,917 Potential Loyalists, 982 Champions; the notebook's `qcut`
> gave 21,989 / 979) were not reproducible: the same query later returned
> 22,072. SQL Q32, notebook 03 and the dashboard source now share one
> tie-consistent method and give identical results. **The finding did not
> change** (34% vs 2% of revenue).
>
> **Methodology caveat — a deliberate departure from the textbook.**
> Frequency is **not** scored in quintiles. With 96.96% of scored customers at
> exactly one order, quintile scoring would split a near-constant column into
> five arbitrary buckets and invent distinctions that do not exist. F is
> scored as an honest ordinal: 1 order → 1, 2 orders → 3, 3+ orders → 5.
> **The F dimension carries little information in this dataset**, and any
> presentation of these segments must say so.

**3. Actual finding**

| Segment | Customers | % of customers | Avg value | Revenue | **% of revenue** |
|---|---|---|---|---|---|
| **Potential Loyalists** | 21,427 | 22.6% | 211.69 | 4,535,822 | **33.6%** |
| At Risk | 14,792 | 15.6% | 280.49 | 4,149,075 | 30.7% |
| Needs Attention | 33,498 | 35.3% | 89.71 | 3,004,951 | 22.3% |
| Lost | 23,420 | 24.7% | 56.15 | 1,315,083 | 9.7% |
| **Champions** | **951** | **1.0%** | 327.44 | 311,400 | **2.3%** |
| Loyal Customers | 895 | 0.9% | 198.96 | 178,069 | 1.3% |

**4. Business implication**
The standard RFM playbook — *protect your Champions* — would direct effort at
951 people holding 2.3% of revenue. That is close to worthless here.

**Potential Loyalists are the only segment large enough to matter**: recent,
decent spend, exactly one order. They are 23% of scored customers and the
single largest revenue block, and critically **they have not yet been lost**.
The *At Risk* group (30.7% of revenue) is similar but older — the same people a
few months later.

**5. Recommended action**
Point retention spend at Potential Loyalists with a **first-to-second purchase**
programme: a time-boxed follow-up within the window where At Risk customers
are still Potential Loyalists. The evidence sets that window (Insight 4,
`sql/11` E1): genuine returners came back after a median **72 days**, and
55% within 90 days, so the follow-up should run inside the first **~3 months**
after a first order. Treat Champions as a reporting curiosity, not a
target. Set the success bar at beating the 3.12% baseline repeat rate
(Insight 4) on a holdout group — anything less is noise.

**Classification:** Hypothesis to test: target segment (21,427 people, 33.6% of revenue) and ~3-month window are evidenced; the uplift is not. Run on a holdout group.

---

# C · Product and Category Performance

## Insight 7 — Category revenue is broad and healthy, and 22 of 24 measurable categories grew

**1. Business question**
Does the business depend on a few categories, and which are rising or dying?

**2. Analysis method**
Revenue by English category name from `vw_category_performance` (item grain —
category is a property of the product, not the order). Growth compares the
first and last quarter of the stable window, with a floor of 50 items sold in
**both** periods so small categories cannot produce meaningless percentages.
Source: [`sql/04_joins_and_aggregations.sql`](../sql/04_joins_and_aggregations.sql) Q11, Q13 ·
[`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §C ·
charts [`C1`](eda_charts/C1_category_revenue_and_concentration.png), [`C2`](eda_charts/C2_category_growth_vs_decline.png)

**3. Actual finding**

74 categories carry eligible revenue. The largest, `health_beauty`, is only
**9.3%**. The top 10 together hold **62.4%**, and it takes **18 categories to
reach 80%** of revenue.

Of the 24 categories meeting the volume floor in both comparison periods,
**22 grew and 2 shrank**. Fastest growth: `housewares` at **+532%**.

**4. Business implication**
Category risk is genuinely low — this is a diversified catalogue, and the
breadth of growth suggests demand expansion rather than a single category
carrying the business. Set against Insight 3, the contrast is instructive:
**the catalogue is the resilient part of this business and geography is the
fragile part.**

**5. Recommended action**
Do not spend effort diversifying the catalogue further; it is already
diversified. Redirect that effort to the geographic and delivery problems in
Insights 3 and 9. Use the growth list to prioritise seller recruitment in
expanding categories rather than adding new categories from scratch.

**Classification:** Decision-ready: no further catalogue diversification (top 10 categories = 62.4%). Hypothesis to test: the payoff of recruiting sellers in growing categories.

---

# D · Seller Performance

## Insight 8 — No single seller is critical, but a few hundred determine the platform's reputation

**1. Business question**
How exposed is the marketplace to its sellers, and which ones need intervention?

**2. Analysis method**
`vw_seller_performance`, which computes revenue per (seller, order) pair so an
order spanning several sellers is never double-counted. Scorecard restricted
to sellers with 50+ orders, because averages over tiny samples are unstable.
Source: [`sql/04_joins_and_aggregations.sql`](../sql/04_joins_and_aggregations.sql) Q14–Q16 ·
[`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §D ·
charts [`D1`](eda_charts/D1_seller_revenue_concentration.png), [`D2`](eda_charts/D2_seller_scorecard_late_vs_review.png)

**3. Actual finding**

3,053 of 3,095 sellers earned eligible revenue (the other 42 had only
canceled or unavailable orders).

- **Largest single seller: 1.70%** of revenue
- **Top 10% of sellers: 67.5%** of revenue

Among the 428 sellers with 50+ orders, late-delivery rate and average review
score correlate at **−0.52** — real, but only moderate.

**Intervention list — high volume, rated below average:**

| Seller | State | Orders | Revenue (BRL) | Late % | Avg review |
|---|---|---|---|---|---|
| 7c67e144… | SP | 982 | 187,924 | 10.07% | **3.49** |
| 2eb70248… | SP | 202 | 42,629 | 13.90% | **2.69** |
| 1835b56c… | SP | 423 | 33,344 | 11.75% | 3.63 |
| 855668e0… | SP | 310 | 31,918 | 14.00% | 3.79 |
| 88460e8e… | PR | 247 | 31,397 | **19.51%** | 3.43 |
| 70a12e78… | SP | 315 | 30,859 | 10.90% | 3.80 |

**4. Business implication**
Single-seller dependency is not a real risk — losing the biggest costs 1.7%.
The exposure is at the **tier** level: a few hundred sellers generate
two-thirds of revenue and therefore set the customer experience.

The moderate correlation matters: late delivery explains **part** of a poor
rating, not all of it. Several sellers have low late rates and poor scores
anyway, which points at product quality or listing accuracy — a different
problem needing a different fix.

> **Caveat:** a review attaches to the **order**, not the seller. In a
> multi-seller order every seller inherits the same score. These figures are
> indicative, not a clean per-seller measurement.

**5. Recommended action**
The list above is short enough for a person to work through this week. Split
it in two: sellers with high late rates get a fulfilment conversation; sellers
with good delivery but poor ratings get a product-quality and listing review.
Make a seller scorecard a standing monthly report from `vw_seller_performance`
rather than a one-off.

**Classification:** Decision-ready: work through the intervention list and publish the scorecard monthly (descriptive and operational; ratings are inherited from orders).

---

# E · Delivery and Operations

## Insight 9 — Late delivery is associated with lower satisfaction, but the "cliff" was mostly a survey-timing effect

> **Revised 2026-11-20.** The original version of this insight said a late order
> "loses a full star" and that 8–15 days late "collapses" the score to 1.73. A
> data-quality investigation (issue **Q19**,
> [`notebooks/04_data_quality_investigation.ipynb`](../notebooks/04_data_quality_investigation.ipynb))
> found that **4,795 reviews (4.98%) were answered before the parcel arrived**,
> and these are concentrated in late orders. The original figures are kept
> below as *Analysis 1*. They are correct arithmetic, but they mix reviews of
> the wait with reviews of the delivered order.

**1. Business question**
How is late delivery related to customer satisfaction?

**2. Analysis method**
Orders bucketed by `delay_days` (actual minus promised delivery date), with
average review score per bucket. Reviews are aggregated to **one score per
order first**, because 547 orders carry 2–3 reviews and counting those twice
would bias the result. The population is the **96,476 orders with a real
delivery date** (not the 96,478 marked `delivered`, since 8 have no date).

Two analyses:

- **Analysis 1, all reviews:** the original method.
- **Analysis 2, reviews answered after arrival only:** reviews with
  `review_before_delivery = 1` are removed *at review grain* first, then the
  remaining reviews are averaged per order.

95% intervals use a normal approximation for averages and the Wilson method
for the one-star share, because some Analysis 2 groups are small.

Source: [`sql/05_advanced_sql.sql`](../sql/05_advanced_sql.sql) Q26 and Q26b ·
[`notebooks/04_data_quality_investigation.ipynb`](../notebooks/04_data_quality_investigation.ipynb) §C ·
chart [`DQ2_review_timing_sensitivity.png`](data_quality_charts/DQ2_review_timing_sensitivity.png)

**3. Actual finding**

| Delivery vs promise | A1 orders | A1 avg | A1 1-star | A2 orders | A2 avg (95% CI) | A2 1-star (95% CI) |
|---|---|---|---|---|---|---|
| 15+ days early | 29,458 | 4.318 | 6.7% | 29,414 | 4.319 (±0.01) | 6.7% (6.4–7.0) |
| 7–15 days early | 41,476 | 4.316 | 6.3% | 41,389 | 4.316 (±0.01) | 6.3% (6.0–6.5) |
| On time (0–7 early) | 17,234 | 4.201 | 7.0% | 17,193 | 4.202 (±0.02) | 7.0% (6.7–7.4) |
| **1–7 days late** | 4,409 | 3.184 | 29.5% | **3,055** | **3.860 (±0.05)** | **11.1% (10.0–12.3)** |
| **8–15 days late** | 1,918 | 1.733 | 68.5% | **106** | **3.660 (±0.28)** | **17.9% (11.8–26.3)** |
| **Over 15 days late** | 1,335 | 1.726 | 68.8% | **19** | **2.895 (±0.73)** | **31.6% (15.4–54.0)** |

What survives:

- **The direction.** Among reviews written after arrival, late orders still
  score lower than on-time ones (all late orders 3.85 vs 4.30 for orders not late),
  and the one-star share still rises with lateness. For 1–7 days late
  (n = 3,055) the gap of about **0.34 stars** and **1.6× the one-star rate** is
  well outside the confidence interval.
- **Earliness buys nothing.** 15+ days early and 7–15 days early are
  indistinguishable in both analyses (4.32 vs 4.32).

What does not survive:

- **The size of the drop.** The "8–15 days late → 1.73 stars, 68.5% one-star"
  figure becomes **3.66 stars and about 18% one-star**. The steep cliff in
  Analysis 1 is mostly customers rating **while still waiting**: the survey
  reaches them about two days after the promised date.
- **Precision beyond 7 days late.** Only 106 of 1,918 orders 8–15 days late,
  and 19 of 1,335 orders over 15 days late, have a review answered after
  arrival. Those intervals are wide, and those customers may differ from the
  ones who reviewed while waiting. No precise conclusion is drawn for them.

Across the whole period, **7,827 of 96,476 orders (8.11%) arrived late.**

**4. Business implication**
Late delivery and low ratings go together, but through **two channels** that
the original analysis merged:

1. **Waiting customers get surveyed.** About two days after a missed date the
   survey goes out, and customers still waiting score it around **1.8 stars**
   (two-thirds one-star). That depresses the public rating regardless of what
   happens when the parcel arrives.
2. **Delivered-late customers rate somewhat lower.** Once the parcel arrives, a
   1–7 day slip is associated with about a third of a star less and a higher
   one-star rate. This is real, but far gentler than "a full star".

> **Association, not causation.** A late delivery may share a root cause with a
> bad experience (an unreliable seller, a difficult address) rather than
> directly causing the low score.

**5. Recommended action**
Keep **"never miss the promise"** as the operational target: it addresses both
channels. Build an at-risk alert for orders approaching their estimated date
without a delivery scan, so the problem is handled before the survey reaches a
waiting customer. Separately, **review the survey trigger** (Insight 13):
holding it until delivery would stop the platform rating the wait instead of
the order. When reporting satisfaction by delivery timing, show both analyses.

**Classification:** Decision-ready: the at-risk alert and the survey-timing change (late orders and 4,795 pre-arrival reviews are measured facts). Hypothesis to test: the size of any rating gain (association only).

---

## Insight 10 — Delivery promises are heavily padded, but the padding is being squeezed out

**1. Business question**
Is the 91.89% on-time rate a sign of fast delivery, or of cautious promising?

**2. Analysis method**
Promised days (`order_estimated_delivery_date` minus purchase) compared with
actual delivery days, month by month.
Source: [`sql/05_advanced_sql.sql`](../sql/05_advanced_sql.sql) Q27 ·
[`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §E1 ·
chart [`E1_promised_vs_actual_delivery.png`](eda_charts/E1_promised_vs_actual_delivery.png)

**3. Actual finding**

| Month | Promised | Actual | Padding | On-time % |
|---|---|---|---|---|
| 2017-01 | **39.5 days** | 12.6 | 26.9 | 96.9% |
| 2018-08 | **15.2 days** | 7.7 | 7.5 | 89.6% |

Across the whole period orders arrive **11.18 days early on average**. Actual
delivery improved **39%**; the quoted promise tightened **62%**.

**4. Business implication**
The headline on-time rate overstates logistics performance — it is measured
against Olist's own estimate, and that estimate was padded by nearly four
weeks in early 2017.

But read alongside Insight 9, the padding was **rational**: lateness is
associated with lower ratings (and, once the date passes, triggers a survey to
a customer still waiting) while earliness earns nothing, so a conservative
promise was the correct risk trade. And the company has been steadily removing it as
actual performance improved, which is exactly the right direction.

**5. Recommended action**
Keep tightening, but tie it to the risk curve rather than to ambition. Since
earliness has no satisfaction value, the optimal promise is the shortest date
the operation can hit reliably — not the fastest it can sometimes hit.

> **An open question this data cannot answer:** whether the remaining ~7 days
> of padding costs conversions at checkout. There is no browsing or cart data
> in this dataset, so this is a **hypothesis to test**, not a finding. An A/B
> test on quoted dates would settle it.

**Classification:** Hypothesis to test: tighter promises may lift conversion but risk more late orders; the dataset has no checkout data (A/B test on quoted dates).

---

## Insight 11 — Delivery quality varies 2.8× across the country, and the worst-served states are the smallest markets

**1. Business question**
Where does the delivery operation fail, and does it relate to where revenue is?

**2. Analysis method**
Delivery days, late rate and review score by `customer_state` from
`vw_delivery_performance`, with a floor of 300 delivered orders per state.
Source: [`sql/04_joins_and_aggregations.sql`](../sql/04_joins_and_aggregations.sql) Q18 ·
[`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §E2 ·
chart [`E2_delivery_by_state.png`](eda_charts/E2_delivery_by_state.png)

**3. Actual finding**

| | State | Orders | Avg days | Late % | Avg review |
|---|---|---|---|---|---|
| **Fastest** | SP | 40,495 | **8.8** | 5.9% | 4.25 |
| | MG | 11,355 | 12.0 | 5.6% | 4.19 |
| | PR | 4,923 | 12.0 | 5.0% | 4.24 |
| **Slowest** | AL | 397 | **24.5** | **23.9%** | **3.85** |
| | PA | 946 | 23.8 | 12.4% | 3.91 |
| | MA | 717 | 21.6 | 19.7% | 3.83 |

A customer in Alagoas waits **2.8× longer** than one in São Paulo and is
**four times more likely** to receive a late order. Across states, average
delivery time and average review score correlate at **−0.83**.

**4. Business implication**
The slow states are also the low-revenue states from Insight 3. Two
explanations fit equally well:

- poor logistics suppresses demand in those regions, or
- low volume makes logistics investment uneconomic there.

**This dataset cannot distinguish between them** — it contains no information
about customers who did not buy. The distinction matters commercially, because
one implies an opportunity and the other implies a cost.

**5. Recommended action**
Run a bounded experiment rather than a national programme: pick one
under-served state with reasonable population, improve delivery there (a
regional partner or fulfilment point), and measure whether order volume
responds. That converts an unanswerable correlation into a testable business
case at limited cost.

**Classification:** Hypothesis to test: explicitly a bounded experiment; the state-level link between delivery and volume is a correlation.

---

## Insight 12 — Three-quarters of delivery time sits with the carrier, not with Olist or the seller

**1. Business question**
Which stage of the journey should an operational improvement target?

**2. Analysis method**
Delivery decomposed into three stages using exact (second-precision)
`TIMESTAMPDIFF` across the order timestamps. **Corrected 2026-11-20:** the
calculation now uses only orders whose four timestamps are in a possible
order (`stage_timing_valid = 1`: purchase ≤ approval ≤ carrier ≤ customer).
The original version included 1,373 orders where a stage was negative: 1,350
with the carrier handoff recorded *before* payment approval (issue **Q18**)
and 23 delivered before carrier handoff (Q08). It also truncated each stage
to whole hours.
Source: [`sql/04_joins_and_aggregations.sql`](../sql/04_joins_and_aggregations.sql) Q20 ·
[`notebooks/04_data_quality_investigation.ipynb`](../notebooks/04_data_quality_investigation.ipynb) §A4

**3. Actual finding**

Across **95,088** orders with a valid stage sequence:

| Stage | Days | Share of total |
|---|---|---|
| Purchase → payment approval | 0.40 | 3.2% |
| Approval → carrier handoff (seller dispatch) | 2.85 | 22.6% |
| **Carrier → customer (last mile)** | **9.36** | **74.2%** |
| **Total** | **12.62** | |

**Robustness:** the superseded calculation on all 96,461 orders gave 0.41 /
2.78 / 9.31 days (74.1% last mile). Removing the impossible sequences moves no
stage by more than 0.07 days. **The finding is unchanged.** The Q18 anomaly is
real but small (1.4% of orders) and short (two-thirds under 24 hours), and it
looks like approvals recorded late in bulk on two dates rather than a
logistics effect.

**4. Business implication**
Payment approval is effectively instantaneous and seller dispatch is already
fast at under three days. **Nearly three-quarters of the wait is the carrier
leg** — the part Olist controls least directly.

This reframes Insights 9 and 11. Pressuring sellers to dispatch faster could
at best remove a couple of days from a 12.5-day journey. The lever that
matters is carrier performance and network design.

**5. Recommended action**
Direct logistics investment and carrier negotiation at the last mile, and hold
carriers to delivery-date commitments the way sellers are held to dispatch
times. When assessing seller performance (Insight 8), separate dispatch speed
— which a seller controls — from total delivery time, which they largely do not.

**Classification:** Decision-ready: judge sellers on dispatch speed, not total delivery time (measurement change). Hypothesis to test: the payoff of last-mile investment (74.2% is time spent, not proven controllable gain).

---

# F · Customer Satisfaction

## Insight 13 — Customers review the wait, not the product

**1. Business question**
When customers leave a bad review, what are they actually unhappy about?

**2. Analysis method**
Average review score grouped by order status, with reviews aggregated to one
score per order and a floor of 100 orders per status.
Source: [`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §F3 ·
chart [`F3_review_score_by_order_status.png`](eda_charts/F3_review_score_by_order_status.png)

**3. Actual finding**

| Order status | Orders reviewed | Avg review | vs delivered |
|---|---|---|---|
| **delivered** | 95,832 | **4.16** | — |
| shipped | 1,032 | 2.00 | −2.16 |
| canceled | 605 | 1.80 | −2.36 |
| invoiced | 309 | 1.64 | −2.52 |
| unavailable | 595 | 1.53 | −2.63 |
| **processing** | 295 | **1.27** | **−2.89** |

An order still `processing` scores **2.89 stars below** a delivered one.

**Added 2026-11-20 (issue Q19), from the review timestamps directly:** of
96,359 reviews on delivered orders, **4,795 were answered before the parcel
arrived**. Those reviews average **1.80 stars with 67.2% one-star**, against
**4.28 stars and 6.8% one-star** for reviews answered after arrival. 94% of
them belong to orders that were delivered late. For a parcel that has not
arrived, Olist sends the survey about two days after the promised date. The same pattern appears inside the `delivered` status, not only in
undelivered statuses.

Separately, the overall review distribution is J-shaped rather than
bell-shaped: **57.78% five-star, 11.51% one-star**, little in between, with a
mean of **4.0864** that describes almost nobody.

**4. Business implication**
Customers who review an order that has not reached them are rating **the
absence of their parcel**, not the merchandise. The review-timing evidence
makes this direct rather than inferred: it shows up both in undelivered
statuses and among delivered orders reviewed too early. Taken with Insights 9
and 12, **fulfilment, more than product quality, is the dominant factor
associated with satisfaction in this marketplace.** (Association: the data
cannot rule out other differences between these customers.)

The J-shaped distribution also means any dashboard reporting only the 4.09
average hides the most actionable group — the 11.5% who are actively angry.

**5. Recommended action**
Report the **1-star rate** as a headline KPI alongside the average; the mean
alone conceals the problem. **Change when the satisfaction survey is
triggered:** today it goes to customers whose order has not arrived. Those
4,795 reviews average 1.8 stars, depress the platform's public rating, and
produce no usable product feedback. Holding the survey until a delivery scan
exists is a cheap, testable change.

**Classification:** Decision-ready: report the one-star rate and hold the survey until delivery (a reporting change and a measured survey artefact).

---

## Insight 14 — Below-average satisfaction reaches the revenue core, but not most rated revenue

> **Revised 2026-11-20 (measure audit).** The original version said **20 of 34**
> categories, holding **60.0%** of rated revenue, score below average. That
> scored each category by repeating every order's rating **once per item**, so
> a 6-unit order counted six times. The project's review-grain convention
> counts each review once per category it touches
> (`tableau/data/analytical/category_satisfaction.csv`, validated). On that
> basis it is **15 of 34 categories and 45.1%**: no longer "most". Five
> categories near the line move above average (auto, drinks, electronics,
> garden_tools, housewares). Restricting reviews to eligible orders gives
> 13 of 34 and 42.7%, so the conclusion does not depend on that choice. The
> original also called the four categories below "four of the five largest";
> by rated revenue they rank 2nd, 3rd, 5th and 6th.

**1. Business question**
Is weak satisfaction concentrated in small categories, or does it affect the
ones that matter?

**2. Analysis method**
Average review score per category at **review grain** (each review once per
category in its order), with a floor of 300 eligible items sold. Revenue =
eligible item revenue on orders that have a review ("rated revenue").
Source: [`tableau/data/analytical/category_satisfaction.csv`](../documentation/analytical_sources.md) ·
Tableau field `Category Avg Review Score` (N30). The original item-weighted figures come
from [`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) §F2
and chart [`F2_review_score_by_category.png`](eda_charts/F2_review_score_by_category.png), which have **not**
been regenerated and still show the superseded method.

**3. Actual finding**

Of 34 categories meeting the volume floor, **15 score below the 4.0864 overall
average**, and they account for **5,591,643 BRL — 45.1% of rated revenue**
(superseded item-weighted figure: 20 categories, 60.0%).

Three of the five largest categories are among them, plus the sixth:

| Category | Revenue rank | Rated revenue (BRL) | Avg score (review grain) | 1-star % | Score after arrival |
|---|---|---|---|---|---|
| watches_gifts | 2 | 1,189,934 | 4.07 | 11.7% | 4.26 |
| bed_bath_table | 3 | 1,025,168 | **3.97** | 12.7% | 4.13 |
| computers_accessories | 5 | 899,479 | 4.03 | 12.7% | 4.19 |
| furniture_decor | 6 | 721,187 | **4.01** | 12.9% | 4.18 |

**4. Business implication**
Weak satisfaction still reaches the revenue core: three of the five largest
categories sit below average. But it covers less than half of rated revenue,
and the gaps are small (3.97 to 4.07 against 4.09). This is a mild, broad
underperformance in a few large categories, not a majority problem.

Given Insights 9 and 13, part of this is likely delivery rather than product:
bulky categories such as `bed_bath_table` and `furniture_decor` plausibly ship
slower. **This analysis does not separate the two effects**, and that
separation would be the natural next piece of work.

**5. Recommended action**
The on-time versus late split has now been done (follow-up below). Act on its
result: give `bed_bath_table`, `furniture_decor`, `office_furniture` and
`home_confort`, whose deficit persists on on-time orders, a merchandising and
seller-quality review (listing accuracy, dimensions, damage in transit). Route
`watches_gifts`, `electronics` and `baby`, whose gap vanishes on on-time
orders, to the delivery work in Insights 9 and 12.

**Classification:** Decision-ready: the merchandising review of the four product-problem categories (supported by the on-time split). Hypothesis to test: how much a fix would raise their ratings.

---

### ✅ RESOLVED — follow-up analysis, 2026-11-13

> **Re-computed 2026-11-20 at review grain** (each review once per category;
> notebook 03 §F2 follow-up cell). The first version weighted each order's
> rating by its item count; its figures (baselines 4.0820 / 4.2115 / 2.5489,
> `office_furniture` −0.569 → −0.598) are superseded. **The conclusions held**,
> except `audio`, which now only partly recovers on time.

The query above was run. This section answers the question the original
insight left open.

**Method.** Hold delivery constant by comparing each category's average
review score **using on-time orders only**. If a category's deficit vanishes
once lateness is removed, it was a logistics problem. If it persists, it is
a product problem. Reviews on delivered, revenue-eligible orders, review grain:

| Baseline | Avg review |
|---|---|
| All delivered orders | 4.1557 |
| On-time orders only | **4.2937** |
| Late orders only | **2.5665** |

**The answer is category-specific, not one global story** (categories with
300+ items that score below the overall baseline; verdict: on-time gap ≥ −0.02
→ delivery; shrinks by more than half → mostly delivery; otherwise product):

| Category | Items | Gap overall | Gap when on-time only | Verdict |
|---|---|---|---|---|
| `office_furniture` | 1,676 | −0.51 | **−0.54** | **Product** — deficit *widens* |
| `home_confort` | 432 | −0.27 | −0.25 | Product |
| `home_construction` | 599 | −0.17 | −0.20 | Product |
| `audio` | 359 | −0.32 | −0.19 | Product, partly delivery (deficit shrinks 40%) |
| **`bed_bath_table`** | **10,964** | −0.16 | **−0.16** | **Product** |
| `market_place` | 308 | −0.07 | −0.14 | Product |
| `unknown` | 1,575 | −0.14 | −0.13 | Product |
| `telephony` | 4,496 | −0.10 | −0.12 | Product |
| **`furniture_decor`** | **8,215** | −0.10 | **−0.10** | **Product** |
| `computers_accessories` | 7,738 | −0.07 | −0.09 | Product |
| `furniture_living_room` | 496 | −0.09 | −0.08 | Product |
| `electronics` | 2,736 | −0.03 | −0.02 | **Delivery** — gap vanishes |
| `construction_tools_construction` | 922 | −0.03 | −0.02 | **Delivery** — gap vanishes |
| `watches_gifts` | 5,920 | −0.04 | **−0.02** | **Delivery** — gap vanishes |
| `baby` | 3,018 | −0.05 | −0.01 | **Delivery** — gap vanishes |
| `auto` | 4,161 | −0.01 | −0.00 | **Delivery** — gap vanishes |

**Finding: for the largest affected categories, delivery does NOT explain the
deficit.** `bed_bath_table` (1.03M BRL) and `furniture_decor` (721k BRL) keep
their entire gap once only on-time orders are counted. These are genuine
product or merchandising problems.

`office_furniture` is the clearest case and the worst: a −0.51 deficit that
**widens to −0.54** when delivery is held constant, despite also having the
slowest average delivery in the dataset at 20.8 days. It is both slow *and*
intrinsically poorly rated — two separate problems in one category.

Conversely `watches_gifts`, `electronics`, `baby` and `auto` were delivery
victims: remove late orders and they rate at baseline.

**Revised action.** Split the fix by owner:

- **Merchandising and seller quality** own `bed_bath_table`,
  `furniture_decor`, `office_furniture` and `home_confort`. Investigate
  listing accuracy, product descriptions, dimensions and damage in transit
  for bulky goods.
- **Logistics** owns `watches_gifts`, `electronics` and `baby`: these need
  no product intervention, only the delivery work in Insights 9 and 12.
  `audio` is mixed and needs both.
- **`office_furniture` needs both**, and given it is the largest single
  deficit in the dataset it is the obvious place to start.

> **Caveat.** Holding delivery constant controls for *lateness*, not for
> total delivery time, handling damage, or packaging. A bulky item that
> arrives on time but damaged still rates badly, and this dataset has no
> damage or returns field. So "product problem" here means "not explained by
> lateness" — it does not isolate product quality from every other
> non-delivery factor.

---

# Top five strategic priorities

Ranked by evidence strength × size of the opportunity. Each priority is
labelled **decision-ready** (supported by the data as it stands) or
**hypothesis to test** (plausible, but the data cannot prove the payoff).

### 1. Make "never miss the promised date" the primary operational goal
*Decision-ready for the alert and the survey timing; the rating gain is an association, so measure it.*
**From Insights 9, 10, 12, 13.** Late orders are associated with lower ratings
(3.86 vs 4.20 stars for 1–7 days late, reviews answered after arrival), and a
missed date also triggers a survey to a customer still waiting, which averages
1.8 stars. Earliness is worth nothing. 7,827 orders arrived late. **Start
with:** an at-risk alert before the promised date passes, holding the review
survey until delivery, and carrier accountability for the last mile, which is
74.2% of delivery time.

### 2. Build a first-to-second purchase programme aimed at Potential Loyalists
*Hypothesis to test on a holdout group: the target segment and the ~3-month window are evidenced; the uplift is not.*
**From Insights 4, 5, 6.** 21,427 customers holding 33.6% of revenue, recent,
one order each, not yet lost. The 3.12% baseline repeat rate is the bar to
beat. Genuine returners come back after a median 72 days (55% within 90), so
time the follow-up inside the first three months. **Do not** build a VIP tier — Champions are 951 people and 2.3% of
revenue.

### 3. Make average order value an owned KPI with a target
*Decision-ready as a KPI; the free-shipping threshold is a hypothesis to A/B test (no cost data).*
**From Insights 1, 2, 5.** Growth has stalled (−1.5% compound monthly in
2018) and AOV has been flat (+0.4%, Jan–Aug like-for-like) while orders more
than doubled. With retention structurally near zero, basket size is the
only lever that does not depend on customers returning. **Start with:** an
A/B test of a free-shipping threshold, set **above** the 86.90 BRL median or
by region. At the median, half of all orders already qualify and full
absorption would cost 1.42M BRL (63.5% of freight); only 7.0% of orders sit
just below it. Measure the effect on that near-miss band.

### 4. Treat geographic concentration as the top business risk
*Decision-ready as a risk statement; whether better delivery creates volume is a hypothesis (the bounded experiment tests it).*
**From Insights 3, 11.** Three states hold 63.4% of revenue while the largest
seller holds 1.70%. The under-served states are also the worst-served on
delivery. **Start with:** one bounded regional delivery experiment to test
whether service improvement generates volume.

### 5. Report the 1-star rate, not just the average review score
*Decision-ready (a reporting change).*
**From Insights 13, 14.** The 4.09 mean hides a J-shaped distribution with
11.51% one-star reviews, and 45% of rated revenue sits in below-average
categories, including three of the five largest (review grain; the earlier 60%
used item weighting). **Start with:** the categories whose deficit persists on
on-time orders (Insight 14 follow-up): `office_furniture`, `bed_bath_table` and
`furniture_decor` for merchandising; `watches_gifts`, `electronics` and `baby`
for logistics.

---

# Analytical limitations

Stated plainly, because every one of them bounds a conclusion above.

| Limitation | What it prevents |
|---|---|
| **Historical data (Sep 2016 – Oct 2018)** | Nothing here describes current performance. The marketplace has had years to change |
| **No product cost data** | No profit, margin or contribution analysis is possible anywhere in this project |
| **3.12% repeat rate** | Bounds all cohort, retention and lifetime-value work. RFM's Frequency dimension is near-degenerate and is scored as an ordinal, not quintiles |
| **Right-censoring in cohorts** | Customers acquired near the data's end had little time to return. Only compare cohorts of similar age |
| **Reviews attach to orders, not sellers** | In multi-seller orders every seller inherits the same score, so per-seller ratings are indicative only |
| **"On time" is self-referential** | Measured against Olist's own estimate, which Insight 10 shows was padded by up to 27 days |
| **No browsing, cart or marketing data** | Cannot test whether padded promises cost conversions, cannot compute acquisition cost, cannot analyse abandonment |
| **No data on non-customers** | Cannot distinguish "bad logistics suppressed demand" from "low demand prevented logistics investment" (Insight 11) |
| **Correlation, not causation** | Delivery↔satisfaction, delivery↔retention, and seller↔rating are **associations**. The data cannot establish direction |
| **City names unnormalised** | 4,119 spelling variants. All geographic analysis is state-level |
| **Category ratings confound product and delivery** | Insight 14 cannot separate the two; this is flagged as the next piece of work |
| **8 orders marked delivered with no date** | Delivery metrics use a 96,476 denominator, not 96,478 |
| **Carrier handoff before approval (Q18, 1,359 orders)** | Delivery-*stage* figures use the 95,088 orders with a valid timestamp sequence. The cause (likely late-recorded approvals) cannot be proven from the data |
| **Reviews answered before delivery (Q19, 4,795 reviews)** | Satisfaction by delivery timing is reported with and without them. After-arrival samples beyond 7 days late are small (106 and 19 orders), so no precise conclusion is drawn there, and those reviewers may not represent all late customers |

---

# Verification

**2026-11-27 approved T05/T06 update** — Free-shipping threshold impact and
regional freight shares added to Insight 2 and priority 3 (`sql/11` E3–E4,
validator 78/78). Every insight's recommended action now carries a
decision-ready / hypothesis-to-test classification. Insight 14's action was
replaced, because the on-time split it asked for has been done.

**2026-11-27 evidence update** — Two recommendations gained evidence from
`sql/11_insight_evidence.sql`, reproduced in pandas
(`scripts/validate_insight_evidence.py`, 38/38): time to the second order
(Insights 4 and 6; 29.9% of second orders are same-day, so 2.19% returned on a
later day, median 72 days) and freight share by order value (Insight 2,
priority 3). The free-shipping threshold is now labelled a hypothesis, and
each priority is labelled decision-ready or hypothesis to test.

**2026-11-20 consistency cleanup** — SQL Q32, notebook 03 §B2 and Insight 6
now use tie-consistent RFM scoring (identical to `rfm_customer_segments.csv`);
SQL Q33 and notebook 03 §B3 use calendar-month cohorts with blank unobserved
cells (identical to `cohort_retention.csv`); notebook 03 §F2, chart F2 and the
Insight 14 follow-up use review-grain category scores (identical to
`category_satisfaction.csv`). Insight 6's conclusion and the follow-up verdicts
held, except `audio`.

**2026-11-20 measure audit (fix-Phase 4)** — Insight 14 re-tested at review grain
(each review once per category, the project convention): **15 of 34 categories,
45.1% of rated revenue** below average, replacing the item-weighted 20 / 60.0%.
The title and implication were revised. Insight 6 gained a dependency note
with tie-consistent RFM counts; its conclusion is unchanged. Both new figures
come from validated sources (source validator 90/90 and measure validator 230/230 at
the time; today `scripts/validate_tableau_sources.py` and `scripts/validate_tableau_calcs.py`).

**2026-11-20 data-quality re-test (fix-Phase 2)** — Insight 12 recomputed on
the `stage_timing_valid` population (74.2% last mile, unchanged in substance).
Insight 9 re-run with and without reviews answered before delivery (Q26b);
its magnitude claims were revised. Insight 13 gained the review-timing
evidence. All figures were reproduced independently in pandas
(`notebooks/04_data_quality_investigation.ipynb`, 10/10 cross-checks against
the stored flags and MySQL), and `sql/08_validation.sql` passes 71/71.

**2026-11-20 corrections** — Insight 1 now reports compound monthly growth
(2017 +18.01%, 2018 Jan–Aug −1.53%) instead of the arithmetic mean of monthly
% changes; Insight 2 now compares AOV like-for-like (Jan–Aug 2017 136.55 vs
Jan–Aug 2018 137.14 BRL, +0.4%) instead of two single months. Both were
computed independently in SQL and pandas and agree to the cent.

Every figure in this report was **recomputed from the MySQL database on
2026-11-13**, independently of the Phase 4 and Phase 5 reports, using
`vw_order_summary`, `vw_customer_summary`, `vw_seller_performance`,
`vw_category_performance`, `vw_delivery_performance` and direct table queries.

Underlying validation already established in earlier phases:

| Check | Result |
|---|---|
| MySQL vs Python reference (Phase 4; 71/71 after the 2026-11-20 flag checks) | 61/61 PASS |
| Python EDA vs MySQL (Phase 5) | 15/15 PASS |
| Spreadsheet vs Python (Phase 2) | 17/17 computable KPIs reconcile |
| Revenue reconciliation across all three engines | Agrees to the cent |

Three engines — pandas, LibreOffice Calc and MySQL — independently produce the
same headline numbers.

**Source files referenced:**
[`sql/04_joins_and_aggregations.sql`](../sql/04_joins_and_aggregations.sql) ·
[`sql/05_advanced_sql.sql`](../sql/05_advanced_sql.sql) ·
[`sql/06_customer_analytics.sql`](../sql/06_customer_analytics.sql) ·
[`sql/07_business_analysis.sql`](../sql/07_business_analysis.sql) ·
[`notebooks/03_exploratory_data_analysis.ipynb`](../notebooks/03_exploratory_data_analysis.ipynb) ·
[`reports/eda_report.md`](eda_report.md) ·
[`reports/sql_analysis_report.md`](sql_analysis_report.md) ·
[`documentation/kpi_definitions.md`](../documentation/kpi_definitions.md)
