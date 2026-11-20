# Phase 5 — Exploratory Data Analysis Report

**Date:** 2026-11-13
**Notebook:** `notebooks/03_exploratory_data_analysis.ipynb` (57 cells, 30 code — executes end to end, 0 errors; 56 / 29 before the 2026-11-20 follow-up cell)
**Charts:** 15, saved to [`reports/eda_charts/`](eda_charts/)
**Validation:** ✅ **15/15 metrics agree with MySQL**
**Status:** ✅ **PASSED**

---

## 1. What this phase did

Phases 1–4 established *what the data is* and *that the numbers are right*.
Phase 5 asks **what the business should do about it**.

It is deliberately not a re-run of earlier work. Phase 1 already charted
missing values, monthly order counts, the delivery histogram, order status,
the review distribution and orders-per-customer. **None of those are
repeated.** Every chart here answers a question the earlier phases raised but
left open.

All analysis was done in pandas from the Phase 3 cleaned CSVs, then
cross-checked against the Phase 4 MySQL database — two independent engines
over two separately loaded copies of the data.

---

## 2. Charts produced

| # | Chart | Question it answers |
|---|---|---|
| A1 | `A1_revenue_trend_and_mom_growth` | Is growth real, and is it slowing? |
| A2 | `A2_growth_decomposition_indexed` | Is growth from more orders or bigger ones? |
| A3 | `A3_revenue_by_state_pareto` | How concentrated is revenue geographically? |
| B1 | `B1_customer_value_lorenz` | Is there a high-value customer core? |
| B2 | `B2_rfm_segments_customers_vs_revenue` | Which segment is actually worth targeting? |
| B3 | `B3_cohort_retention_heatmap` | Does any cohort retain? |
| C1 | `C1_category_revenue_and_concentration` | Which categories carry the business? |
| C2 | `C2_category_growth_vs_decline` | What is growing and what is dying? |
| D1 | `D1_seller_revenue_concentration` | How dependent is the platform on its sellers? |
| D2 | `D2_seller_scorecard_late_vs_review` | Which sellers should management call? |
| E1 | `E1_promised_vs_actual_delivery` | Are delivery promises honest? |
| E2 | `E2_delivery_by_state` | Where do deliveries fail? |
| F1 | `F1_delivery_delay_vs_review_score` | What does lateness cost in stars? |
| F2 | `F2_review_score_by_category` | Which categories disappoint customers? |
| F3 | `F3_review_score_by_order_status` | Do customers rate the product or the wait? |

Every chart answers a business question. None were created to raise the count.

---

## 3. Findings

### 3.1 Growth is volume, and it has stopped

**Volume vs basket size** — January–August 2018 against January–August 2017,
the only comparable period. Population: revenue-eligible orders that have
line items (the AOV definition in `kpi_definitions.md`).

| Jan–Aug, eligible orders with items | 2017 | 2018 | Change |
|---|---|---|---|
| Orders | 22,562 | 53,530 | **+137.3%** |
| Revenue (BRL) | 3,080,850.81 | 7,341,037.41 | **+138.3%** |
| AOV (BRL) | 136.55 | 137.14 | **+0.4%** |

**Growth rate** — compound monthly growth rate (CMGR), from the first to the
last month of each period:

| Period | CMGR | Log-linear trend (all months) |
|---|---|---|
| 2017, Jan → Dec | **+18.01%** | +15.1% |
| 2018, Jan → Aug | **−1.53%** | −1.1% |

2017 grew strongly; 2018 declined slightly. The 3-month moving average shows
a plateau at roughly 900k BRL/month through 2018.

Chart A2 indexes orders, customers and AOV to their **2017 average** (= 100):
orders and customers climb together while AOV stays in a narrow band around
100 (monthly range 124.76–152.60 BRL, standard deviation 7.44). Every bit of
growth came from acquiring more buyers, none from persuading them to spend
more.

> **Corrections (2026-11-20).**
> - AOV was previously reported as "−13.4%", comparing January 2017
>   (152.60 BRL) with August 2018 (132.20 BRL). January 2017 is a 787-order
>   ramp-up month and the **highest-AOV month of the whole window**, so the
>   comparison started from an outlier. Like-for-like, AOV is flat (+0.4%).
>   Chart A2 was previously indexed to that same January, which made AOV
>   appear to fall; it is now indexed to the 2017 average.
> - Growth was previously reported as the arithmetic mean of monthly %
>   changes (+22.7% for 2017, +2.5% for 2018). That is not a growth rate: it
>   is inflated by one +104% jump from a small base, and it showed 2018 as
>   growing when revenue declined. CMGR replaces it.

**Implication.** Acquisition is working and has saturated. AOV is a
completely untouched lever — and given near-zero retention (3.4), it may be
the only one that does not depend on customers coming back.

### 3.2 Geography is the real concentration risk — not categories

| Dimension | Concentration |
|---|---|
| **States** | Top 3 of 27 = **63.4%** of revenue (SP alone 38%) |
| **Categories** | Top 10 of 74 = 62.4%; it takes **18 categories** to reach 80% |
| **Sellers** | Largest single seller = **1.70%**; top 10 = 13.2% |

This is the opposite of standard retail intuition. The catalogue is
well-diversified and no single seller is critical. **The fragility is
geographic.** Losing or under-serving São Paulo would be existential; losing
the biggest category or the biggest seller would not.

Note also that SP has the *lowest* AOV among the major states — it wins on
volume, not basket size.

### 3.3 High-value customers exist, but they are not loyal

| Top N% of customers | Share of revenue |
|---|---|
| 1% | 11.5% |
| 10% | **41.4%** |
| 20% | 57.0% |

Concentration is real but milder than a textbook 80/20 (top 20% hold 57%, not
80%).

**The composition check is the actual finding:**

| Group | Placed exactly ONE order | Mean orders | Mean value |
|---|---|---|---|
| Top 1% of spenders | **92.9%** | 1.09 | 1,627 BRL |
| Top 10% of spenders | 91.1% | 1.11 | 584 BRL |
| All customers | 96.9% | 1.03 | 140 BRL |

The best customers are **strangers who made one expensive purchase and never
returned**. They exhibited no loyalty behaviour to reward.

> **A correction worth recording.** An earlier draft of this analysis
> described the customer base as having "no high-value core". That was wrong —
> 41% of revenue from 10% of customers is genuine concentration. The accurate
> and more useful statement is that the core exists but consists of one-time
> buyers. The conclusion (no VIP programme) survives; the reasoning changed
> completely.

### 3.4 Retention is effectively zero, and RFM proves it twice

Cohort analysis (calendar months, activity to 2018-08, unobserved cells
blank): **every observed cell in the retention matrix is below 1.5%.** The
mean returned-by-2018-08 rate across 2017 cohorts is **3.07%** (range 1.75%
to 4.32%).
Later cohorts look worse only because of right-censoring — someone acquired
in August 2018 had almost no time to return.

RFM segmentation reaches the same conclusion independently:

| Segment | Customers | % of customers | % of revenue |
|---|---|---|---|
| **Potential Loyalists** | 21,427 | 22.6% | **33.6%** |
| At Risk | 14,792 | 15.6% | 30.7% |
| Needs Attention | 33,498 | 35.3% | 22.3% |
| Lost | 23,420 | 24.7% | 9.7% |
| **Champions** | **951** | **1.0%** | **2.3%** |
| Loyal Customers | 895 | 0.9% | 1.3% |

(Tie-consistent scoring, corrected 2026-11-20; the first run's `qcut` version
reported 21,989 Potential Loyalists and 979 Champions.)

The standard RFM playbook says *protect your Champions*. Here that advice is
close to worthless: Champions are 951 people holding 2.3% of revenue.

**The segment that matters is Potential Loyalists** — recent, decent spend,
exactly one order. 23% of customers, **34% of revenue**, the largest block in
the business, and every one of them is a first-purchase customer not yet lost.

> **Methodology caveat, stated wherever RFM appears.** With 96.9% of customers
> at exactly one order, the Frequency dimension is nearly degenerate. It is
> scored as a 1/3/5 ordinal, not quintiles, because quintiles on a near-constant
> column invent distinctions that do not exist.

**Implication.** The retention question is not "how do we keep our best
customers?" but "how do we get a second order out of a recent first-time
buyer?" That is onboarding and follow-up, not VIP perks.

### 3.5 Lateness is associated with lower satisfaction (revised 2026-11-20)

> **Revised.** The table below uses all reviews. Issue Q19 later showed that
> 4,795 reviews were answered before the parcel arrived, concentrated in late
> orders. The "cliff" reading is superseded; see the sensitivity table below
> and `notebooks/04_data_quality_investigation.ipynb` §C.

| Delivery vs promise | Orders | Avg review | 1-star % |
|---|---|---|---|
| 15+ days early | 29,458 | 4.318 | 6.7% |
| 7–15 days early | 41,476 | 4.316 | 6.3% |
| On time (0–7 early) | 17,234 | 4.201 | 7.0% |
| **1–7 days LATE** | 4,409 | **3.18** | **29.5%** |
| **8–15 days late** | 1,918 | **1.73** | **68.5%** |
| 16–30 days late | 992 | 1.62 | 70.4% |
| 30+ days late | 343 | 2.02 | 64.1% |

Across all reviews, 1–7 days late scores 1.02 stars below on time and 8–15
days late has 9.7× the one-star share. **Counting only reviews answered after
arrival**, those gaps shrink sharply:

| Delivery vs promise | All reviews: avg / 1-star | After arrival only: orders, avg / 1-star |
|---|---|---|
| On time (0–7 early) | 4.201 / 7.0% | 17,193 · 4.202 / 7.0% |
| 1–7 days late | 3.184 / 29.5% | 3,055 · **3.860 / 11.1%** |
| 8–15 days late | 1.733 / 68.5% | 106 · **3.660 / 17.9%** |
| Over 15 days late | 1.726 / 68.8% | 19 · 2.895 / 31.6% |

The association survives; its size does not. Beyond 7 days late the
after-arrival samples are small (106 and 19 orders).

Two consequences that are easy to miss:

1. **Arriving very early buys nothing.** 15+ days early scores 4.318 against
   4.316 for 7–15 days early — indistinguishable. All padding produces zero
   satisfaction upside; it only protects against downside.
2. **Prevention still matters most.** Once the promised date passes, a
   waiting customer is surveyed within about two days. Preventing the slip
   avoids both the pre-arrival review and the lower after-arrival rating.

> **Correlation, not causation.** A late delivery may share a root cause with
> a bad experience (an unreliable seller) rather than directly causing the low
> score.

### 3.6 Delivery promises are padded — but converging fast

| Month | Promised | Actual | Padding |
|---|---|---|---|
| 2017-01 | **39.5 days** | 12.6 | 26.9 |
| 2018-08 | **15.2 days** | 7.7 | 7.5 |

Actual delivery improved **39%**; the quoted promise tightened **62%**. Mean
padding across the window is 12.3 days.

Given 3.5 — that lateness is punished savagely while earliness earns nothing
— the conservative promise is a **rational** strategy, not an error. Whether
the remaining ~7 days still costs conversions at checkout is **not answerable
from this dataset** (no browsing or cart data). It is a testable hypothesis.

### 3.7 Delivery quality varies 2.8× across the country

| | Avg delivery | Late rate |
|---|---|---|
| **SP (fastest)** | 8.8 days | 5.9% |
| **AL (slowest)** | 24.5 days | 23.9% |

Across states, average delivery time and average review score correlate at
**−0.83** — strong and negative.

Cross-referencing 3.2: the slow states are also the low-revenue states.
**Whether poor logistics suppresses demand, or low volume prevents logistics
investment, this data cannot settle.** Both stories fit equally well. It is a
genuine open question worth an experiment, not a conclusion.

### 3.8 Seller risk is tier-wide, not single-seller

The largest seller holds 1.70% of revenue — losing any one is survivable. But
the top 10% of sellers earn **67%**. The risk is not "a seller leaves" but
"a few hundred sellers determine the platform's reputation".

Among the 428 sellers with 50+ orders, late rate and review score correlate at
**−0.52** — real, but only moderate. Several sellers sit bottom-**left**: low
late rate, poor reviews. Something other than logistics is wrong there
(product quality, listing accuracy), which is a different intervention.

**Intervention list — high volume, rated below average:**

| Seller | State | Orders | Revenue | Late % | Avg review |
|---|---|---|---|---|---|
| 7c67e144… | SP | 982 | 187,924 | 10.1% | **3.49** |
| 2eb70248… | SP | 202 | 42,629 | 13.9% | **2.69** |
| 1835b56c… | SP | 423 | 33,344 | 11.8% | 3.63 |
| 88460e8e… | PR | 247 | 31,397 | **19.5%** | 3.43 |

> A review attaches to the *order*, not the seller. In a multi-seller order
> every seller inherits the same score, so these are indicative.

### 3.9 Customers rate the wait, not the product

| Order status | Avg review |
|---|---|
| delivered | **4.16** |
| shipped | 2.00 |
| canceled | 1.80 |
| invoiced | 1.64 |
| unavailable | 1.53 |
| processing | **1.27** |

An order still `processing` scores **2.89 stars below** a delivered one.
These customers are reviewing the *absence of their parcel*.

Combined with 3.5, the conclusion is consistent from three angles:
**fulfilment, not product quality, is the dominant driver of satisfaction in
this marketplace.**

### 3.10 Category risk is low, but below-average ratings reach the revenue core

Category scores count **each review once per category** in its order (review
grain, corrected 2026-11-20; identical to `category_satisfaction.csv`). Of 34
categories with 300+ items sold, **15 score below the 4.09 overall average,
holding 5.59M BRL — 45.1% of rated revenue**, including three of the five
largest:

| Category | Rated revenue | Avg score | 1-star % |
|---|---|---|---|
| watches_gifts | 1,189,934 | 4.07 | 11.7% |
| bed_bath_table | 1,025,168 | **3.97** | 12.7% |
| computers_accessories | 899,479 | 4.03 | 12.7% |
| furniture_decor | 721,187 | **4.01** | 12.9% |

(Historical: the first version repeated each order's rating once per item and
reported 20 categories and 60% of rated revenue. Chart F2 has been regenerated
with the corrected method.)

Of 24 categories meeting the volume floor in both comparison periods, **22
grew and 2 shrank**. Fastest growth: `housewares` **+532%**.

---

## 4. Validation against MySQL

Every headline metric was recomputed in pandas and compared to the Phase 4
MySQL database — a different engine over a separately loaded copy.

**15 checks, 15 PASS, 0 FAIL**, all agreeing within 0.01:

total orders · distinct people · GMV · eligible revenue · freight · orders
with items · AOV denominator · delivered orders · orders with a delivery date
· late deliveries · average delivery days · average review score ·
stable-window revenue · SP state revenue · health_beauty category revenue

The notebook degrades gracefully: if MySQL is not running it reports that and
skips, rather than failing. The analysis stands on its own.

---

## 5. Issues found and fixed during this phase

| Issue | Resolution |
|---|---|
| `is_late` has NaN for 2,965 undelivered orders; the boolean map produced an `object` dtype that crashed matplotlib's colormap | Stored as float (1.0/0.0/NaN). Mapping to bool would have turned undelivered orders into "on time" — a silent correctness bug, not just a crash |
| A chart loop rebound the variable `v`, breaking the summary cell | Renamed loop variables; the Lorenz data now uses explicit `cust_values` / `N_CUSTOMERS` |
| Seller scatter labels collided with each other and the axis | Point labels removed; the chart shows the pattern, the printed table names the sellers |
| **Narrative claimed "no high-value customer core"** | **Wrong** — top 10% hold 41%. Corrected, and the composition check (93% of top spenders bought once) replaced it with a stronger finding |

---

## 6. Limitations

| Limitation | Effect |
|---|---|
| No cost data anywhere | No profit or margin analysis is possible, in this or any phase |
| ~3% repeat rate | Cohort, retention and CLV analysis are bounded. RFM's F dimension is near-degenerate |
| Right-censoring | Later cohorts had less time to return; compare within a column, not across |
| Reviews are order-level | In multi-seller orders every seller inherits the score |
| "On time" is self-referential | Measured against Olist's own estimate, which 3.6 shows is padded |
| No browsing or cart data | Whether padded promises cost conversions cannot be tested here |
| Correlation only | Delivery↔satisfaction and delivery↔retention are associations; the data cannot establish direction |
| City names unnormalised | Geographic analysis is state-level only |

---

## 7. Verdict

| Gate | Result |
|---|---|
| Notebook executes end to end | ✅ 29/29 code cells, 0 errors |
| Charts rendered and saved | ✅ 15 of 15 |
| Charts visually inspected | ✅ 4 reviewed, 2 layout defects fixed |
| KPIs validated against MySQL | ✅ 15/15 PASS |
| Findings traceable to a cell | ✅ no figure asserted without code |
| Correlation vs causation | ✅ labelled throughout |
| Phase 1–4 work modified | ✅ No |

**Phase 5: PASSED.** Ready for Phase 6 — Power BI dashboards on the Phase 4
SQL views.
