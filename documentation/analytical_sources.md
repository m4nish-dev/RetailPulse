# RetailPulse — Analytical Data Sources

**Added:** 2026-11-20 (fix-Phase 3; `seller_scorecard` added in fix-Phase 4) · **Status:** built and validated on macOS, **90/90 checks pass**
**Used by:** the Tableau dashboard ([`../tableau/data_model.md`](../tableau/data_model.md)), alongside five view extracts in `tableau/data/`.

The MySQL views cover the order, customer, category-month, seller and review
grains. The dashboard specification also needs six things those views do not
provide. This document covers those six sources plus a small shared category
dimension and the seller counts behind the weighted seller rates.

| | Source file (`tableau/data/analytical/`) | Grain | Rows | Needed by |
|---|---|---|---|---|
| A | `rfm_customer_segments.csv` | one per person | 96,096 | Customers: RFM visual |
| B | `cohort_retention.csv` | cohort month × months since acquisition | 400 | Customers: cohort matrix |
| C | `product_performance.csv` | one per product | 32,951 | Category Detail |
| D | `seller_category_performance.csv` | seller × category | 6,545 | Category Detail, Seller Detail |
| E | `delivery_stage_orders.csv` | one per order with valid stage timing | 95,088 | Operations: stage shares |
| E | `delivery_stage_summary.csv` | one per stage (+ Total) | 4 | Operations: stage bar |
| F | `category_satisfaction.csv` | one per category | 74 | Satisfaction, Category Detail |
| — | `dim_category.csv` | one per category | 74 | shared key for C, D, F and `vw_category_performance` |
| — | `seller_scorecard.csv` | one per seller | 3,053 | counts behind the weighted seller measures (fix-Phase 4) |

---

## How the sources are built

```
sql/09_dashboard_sources.sql        9 read-only SELECT queries, one per source,
        │                           each introduced by "-- @source: <name>"
        ▼
scripts/export_tableau_sources.py   splits on the markers, refuses anything that is
        │                           not a single SELECT/WITH, opens a READ ONLY
        │                           session, writes one CSV per source + _manifest.csv
        ▼
tableau/data/analytical/*.csv       gitignored, regenerable (~24 MB), MD5 in _manifest.csv
        ▲
scripts/validate_tableau_sources.py rebuilds every source in pandas from
                                    dataset/cleaned/ and compares (90 checks)
```

```bash
./venv/bin/python scripts/export_tableau_sources.py     # build the CSVs (not needed if they exist)
./venv/bin/python scripts/validate_tableau_sources.py   # 90 checks, exit 1 on any failure
```

**No database object was created or changed.** The queries are ordinary
SELECTs, so they run against the existing `retailpulse` database without any
schema change. (The free Tableau Desktop Public Edition cannot connect to MySQL,
which is why the dashboard reads these exported files.)

### Conventions shared by every source

| Rule | Why |
|---|---|
| Revenue = `SUM(order_items.price)` on `revenue_eligible` orders; freight separate | Same as KPI 1. Every revenue column reconciles to **13,494,400.74** |
| A customer is `customer_unique_id` | `customer_id` is per order: 99,441 "customers" instead of 96,096 people |
| One `order_items` row = one unit | Olist numbers units 1..n within an order |
| Items are never joined to payments or reviews row-by-row | Measured fan-out: +4.54% revenue via payments, −0.47% via reviews |
| Flags are 0/1, dates `YYYY-MM-DD`, NULL is an empty field | Tableau's text-file connector reads these cleanly |
| Integer columns stay integer even when they contain NULLs | No `160.0` in a day count |

---

## A · `rfm_customer_segments.csv`

**Purpose.** RFM segment for every person, for the Customers dashboard RFM visual.
**Grain.** One row per `customer_unique_id`: **96,096 rows** (every person in
the data). **94,983** have revenue-eligible orders with items and are scored.
The other **1,113** have only canceled, unavailable or item-less orders. They
are kept with `rfm_segment = 'Not scored'` so the table relates 1:1 to
`vw_customer_summary`. Filter `rfm_scored = 1` on RFM visuals.

| Column | Type | Meaning |
|---|---|---|
| `customer_unique_id` | text (key) | the person |
| `customer_order_count` | integer | orders of **any** status (= `vw_customer_summary.total_orders`) |
| `first_purchase_date` | date | first order, any status |
| `last_purchase_date` | date | last order, any status |
| `last_eligible_purchase_date` | date | last revenue-eligible order with items (basis of R); empty if not scored |
| `recency_days` | integer | days from the dataset's last purchase (2018-10-17) to `last_eligible_purchase_date` |
| `frequency` | integer | eligible orders with items (0 if not scored) |
| `monetary_value` | decimal (BRL) | eligible revenue (= `vw_customer_summary.historical_value`) |
| `r_score`, `m_score` | integer 1–5 | quintile scores (5 = most recent / highest spend) |
| `f_score` | integer 1, 3, 5 | **ordinal**: 1 order → 1, 2 → 3, 3+ → 5 |
| `rfm_code` | text | e.g. `414` |
| `rfm_segment` | text | Champions · Loyal Customers · Potential Loyalists · At Risk · Lost · Needs Attention · Not scored |
| `rfm_scored` | 0/1 | 1 = has eligible revenue and a segment |

**Method.** Population and segment rules are exactly those of `sql/06` Q32,
the source of Insight 6. Frequency keeps the existing ordinal scoring: 96.96% of
scored people have one order, so quintiles would invent distinctions. There is
no predicted lifetime value and no loyalty score.

**One deliberate change: tie handling.** Q32 used `NTILE(5)`. When many people
share the same recency (a whole-day count) or the same spend, `NTILE` splits that
tied group across two scores **arbitrarily**. The split is not even stable
between runs: Insight 6 published 21,917 Potential Loyalists, and the
same Q32 query run on 2026-11-20 returns **22,072**. This source uses

```
score = 1 + FLOOR(5 × (RANK() − 1) / N)
```

so **tied customers always share a score** and pandas reproduces it exactly.
Buckets are no longer exactly equal in size (R: 18,847–19,117 per score;
M: 17,724–19,735).

**Reconciliation with Q32.** Same 94,983 people, same 13,494,400.74 revenue.

| Segment | Q32 (NTILE), 2026-11-20 run | This source | Δ customers | Revenue share Q32 → source |
|---|---|---|---|---|
| Potential Loyalists | 22,072 | 21,427 | −645 | 34.04% → 33.61% |
| At Risk | 14,696 | 14,792 | +96 | 30.55% → 30.75% |
| Needs Attention | 33,061 | 33,498 | +437 | 22.04% → 22.27% |
| Lost | 23,298 | 23,420 | +122 | 9.69% → 9.75% |
| Champions | 957 | 951 | −6 | 2.32% → 2.31% |
| Loyal Customers | 899 | 895 | −4 | 1.35% → 1.32% |

Insight 6's conclusion is unchanged: Potential Loyalists hold about a third of
revenue and Champions about 2%. **Resolved 2026-11-20:** SQL Q32, notebook 03
§B2 and Insight 6 now use this tie-consistent method and match this source
customer by customer. The table above is kept as the historical reconciliation.

---

## B · `cohort_retention.csv`

**Purpose.** A long-format matrix for the Customers dashboard cohort matrix: rows =
`cohort_month`, columns = `months_since_acquisition`, values = `retention_pct`.
**Grain.** One row per (cohort_month, months_since_acquisition): 20 cohorts
(2017-01 … 2018-08) × offsets 0–19 = **400 rows**, 95,764 people.

| Column | Type | Meaning |
|---|---|---|
| `cohort_month` | text `YYYY-MM` | month of the person's **first order of any status** |
| `months_since_acquisition` | integer 0–19 | calendar-month difference (Feb vs Jan = 1) |
| `activity_month` | text `YYYY-MM` | cohort month + offset |
| `cohort_customers` | integer | people in the cohort |
| `is_observed` | 0/1 | 1 if `activity_month` ≤ 2018-08 (the data could show it) |
| `max_observed_offset` | integer | last offset this cohort can be observed at (2018-08 cohort = 0) |
| `active_customers` | integer / empty | cohort members with ≥ 1 order (any status) in that month; offset 0 = the cohort itself |
| `returning_customers` | integer / empty | same as `active_customers` for offset ≥ 1; empty at offset 0 |
| `retention_pct` | decimal / empty | `active_customers ÷ cohort_customers × 100`; 100 at offset 0 |

**Right-censoring.** The last fully observed month is **2018-08**. 2018-09 and
2018-10 hold 16 and 4 orders: they mark the end of the extract, not customer
behaviour. The 190 cells whose activity month is after 2018-08 were never
observed. Their counts and `retention_pct` are **empty, never 0**, so a heatmap
shows them blank instead of as "zero retention". The 210 observed cells form
the usual triangle.

**Definitions, and one existing inconsistency.** Cohort month matches
`vw_customer_summary.cohort_month` (validated: all 20 cohort sizes equal).
Offsets use the calendar-month difference, as in notebook 03 §B3 (Insight 4).
`sql/06` Q33 originally used `TIMESTAMPDIFF(MONTH …)` (elapsed whole months),
so an order on 31 Jan followed by 1 Feb counted as month 0 there and month 1
here; month-1 returns were 348 vs 453. **Resolved 2026-11-20:** Q33 now uses
calendar months, counts activity only to 2018-08 and returns NULL for
unobservable months. Its m1–m3 match this source cell for cell, blanks included.

**Use in Tableau.** Square marks: rows `cohort_month`, columns
`months_since_acquisition`, colour `Cohort Retention %` (calculated field N05). Exclude offset 0 from the colour scale or it swamps
every other cell (every observed cell after offset 0 is below 0.8%). Keep the mandatory right-censoring caption.

---

## C · `product_performance.csv`

**Purpose.** Product rows for the category drill-through ("top products").
**Grain.** One row per product: all **32,951** (every product appears on at
least one order). Built at item grain from `order_items`, with no payment or
review join, so revenue cannot fan out.

| Column | Type | Meaning |
|---|---|---|
| `product_id` | text (key) | |
| `category` | text | English category (`unknown` for the 610 uncategorised, Q04) → `dim_category` |
| `order_count` | integer | distinct eligible orders containing the product |
| `units_sold` | integer | eligible item rows |
| `product_revenue` | decimal (BRL) | eligible `SUM(price)` |
| `avg_item_price` | decimal | eligible `AVG(price)`; empty if never sold on an eligible order |
| `freight_value` | decimal (BRL) | eligible `SUM(freight_value)`: freight **charged to the customer** |
| `avg_freight_value` | decimal | eligible `AVG(freight_value)` |
| `seller_count` | integer | distinct sellers of the product on eligible orders |
| `first_sale_date`, `last_sale_date` | date | eligible orders only |
| `units_all_statuses` | integer | item rows of any status (sums to 112,650) |

222 products appear only on canceled or unavailable orders. They keep a row with
zero eligible sales so the drill-through list is complete. **There is no cost,
profit or margin column**: the dataset has no product cost.

---

## D · `seller_category_performance.csv`

**Purpose.** Seller × category rows for the drill-through ("top sellers in this
category", "categories this seller sells").
**Grain.** One row per (seller_id, category) with eligible sales: **6,545 rows**.

| Column | Type | Meaning | Additive across rows? |
|---|---|---|---|
| `seller_id` | text | | key |
| `seller_state` | text | | — |
| `category` | text | → `dim_category` | key |
| `order_count` | integer | distinct eligible orders with this seller's items in this category | **No** |
| `item_count` | integer | eligible item rows | Yes |
| `product_revenue` | decimal (BRL) | eligible `SUM(price)` | Yes |
| `freight_value` | decimal (BRL) | eligible `SUM(freight_value)` | Yes |
| `orders_shared_with_other_sellers` | integer | of `order_count`, orders that also contain another seller | No |
| `delivery_measurable_orders` | integer | of `order_count`, orders with a real delivery date | No |
| `avg_delivery_days` | decimal | purchase → delivery, measurable orders | — |
| `late_orders` | integer | measurable orders delivered after the estimate | No |
| `late_pct` | decimal | `late_orders ÷ delivery_measurable_orders × 100`; empty if none | — |
| `dispatch_measurable_orders` | integer | single-seller orders with `stage_timing_valid = 1` | No |
| `avg_dispatch_days` | decimal | approval → carrier handoff on those orders | — |

**Multi-item orders.** Revenue, items and freight are at item grain, so they sum
exactly to the seller totals (`vw_seller_performance`) and the category totals
(`vw_category_performance`); both are validated. `order_count` counts an order
once **in each pair it touches**: an order with two categories, or two sellers,
appears in two rows. Summed over all rows it gives 99,744, against 98,199
distinct eligible orders. Aggregate orders with `vw_order_summary`, never by
summing this column.

**Delivery.** Delivery is recorded once per **order**. Each order counts once
per pair, and in a multi-seller order (1,277 eligible orders) every seller
inherits the same delivery outcome. Dispatch time is attributed to a seller only
on **single-seller** orders with valid stage timing, so Q18 orders and shared
orders are excluded rather than misattributed.

---

## E · `delivery_stage_orders.csv` and `delivery_stage_summary.csv`

**Purpose.** The Operations stage breakdown, using the corrected Phase 2 logic.
**Population.** `stage_timing_valid = 1`: all four timestamps present and
purchase ≤ approval ≤ carrier ≤ customer. **95,088 orders**, computed by the
query and independently by pandas from the raw timestamps, not hardcoded.
Excluded from the 96,476 orders with a delivery date: 1,388. That is 1,350
carrier-before-approval (Q18), 23 delivered-before-carrier (Q08) and 15 with a
missing approval or carrier timestamp.

`delivery_stage_orders.csv` relates **1:1 to `vw_order_summary`** on `order_id`.

| Column | Type | Meaning |
|---|---|---|
| `order_id` | text (key) | |
| `order_month` | text | purchase month |
| `in_stable_window` | 0/1 | 2017-01 … 2018-08 |
| `customer_state` | text | |
| `purchase_to_approval_seconds` … `total_seconds` | integer | exact `TIMESTAMPDIFF(SECOND)`; stages sum exactly to total |
| `purchase_to_approval_days` … `total_days` | decimal (6 dp) | seconds ÷ 86,400 |

`delivery_stage_summary.csv` (long format for a stacked bar):

| stage_order | stage | orders | avg_days | share_pct |
|---|---|---|---|---|
| 1 | Purchase to approval | 95,088 | 0.402 | 3.19 |
| 2 | Approval to carrier handoff | 95,088 | 2.852 | 22.60 |
| 3 | Carrier handoff to customer | 95,088 | 9.364 | **74.21** |
| 4 | Total | 95,088 | 12.618 | 100 |

**Shares are ratio-of-sums** (`SUM(stage seconds) ÷ SUM(total seconds)`), not an
average of per-order percentages. In Tableau (field N22):
`SUM([carrier_to_customer_seconds]) / SUM([total_seconds])`.

> **Two "average delivery" numbers, both correct.** KPI 19 (Average Delivery
> Time, Operations card) is **12.56 days** over the 96,476 orders with a delivery
> date. The stage total here is **12.62 days** over the 95,088 orders whose
> stages can be measured. They answer different questions; label each with its
> population.

---

## F · `category_satisfaction.csv`

**Purpose.** Category-level satisfaction for the Satisfaction and Category Detail dashboards.
**Grain.** One row per category: **74 rows**.

| Column | Type | Meaning |
|---|---|---|
| `category` | text (key) | → `dim_category` |
| `order_count`, `item_count` | integer | orders / items containing the category, **any status** (use for volume floors, e.g. ≥ 300 items) |
| `reviewed_orders` | integer | of those orders, how many have a review |
| `review_count` | integer | reviews linked to the category, each `(review_id, order_id)` once |
| `avg_review_score` | decimal | review-grain mean, all reviews |
| `one_star_pct`, `five_star_pct` | decimal | % of reviews scored 1 / 5 |
| `reviews_before_delivery` | integer | Q19: answered before the parcel arrived |
| `pct_reviews_before_delivery` | decimal | of `review_count` |
| `reviews_order_not_delivered` | integer | review on an order with no delivery date (flag NULL) |
| `reviews_after_arrival` | integer | `review_before_delivery = 0` |
| `avg_review_score_after_arrival` | decimal | sensitivity: after-arrival reviews only |
| `one_star_pct_after_arrival` | decimal | sensitivity: after-arrival reviews only |
| `reviews_from_multi_category_orders` | integer | of `review_count`, reviews on orders spanning 2+ categories |
| `delivery_measurable_orders`, `late_orders`, `late_pct` | integer / decimal | delivery context for the category's orders |

**Review grain.** Reviews belong to **orders**, not products or sellers. Each
order is linked to each **distinct** category it contains, and its reviews come
with it. A review therefore counts once per category, **never once per item**.
A 3-unit order contributes its review once, not three times.

**Multi-category orders.** 786 orders span 2+ categories. Their reviews count in
each category they contain, so category rows are **not additive**: summed
`review_count` (99,273) exceeds the 98,465 distinct reviews that have a
category by exactly those 808 duplicates. 759 reviews belong to orders with no
items, have no category, and are excluded.

**Review timing.** All 4,795 Q19 pre-arrival reviews are on orders with items
and stay identifiable. The after-arrival columns give the sensitivity view;
`late_pct` is included because delivery, not only the product, shapes these
scores.

> **A category score is not a product-quality score.** Reviews describe the
> whole order experience, delivery included. This table cannot separate
> product from logistics, and no visual built on it should imply that it can.

**Difference from notebook 03 / Insight 14.** That analysis averaged one score
per order **repeated for every item** (item-weighted), on revenue-eligible
items only. This source counts each review once per category, on all statuses,
which is the requested review grain. For the 34 categories with ≥ 300 items the
averages differ by a median of 0.03 stars (max 0.13, `office_furniture`).
**Five categories near the overall average switch side** (auto, drinks,
electronics, garden_tools, housewares). See *Unresolved inconsistencies*.

---

## `dim_category.csv`

74 rows: `category` (English, key), `category_portuguese`, `product_count`
(sums to 32,951). It exists so the product, seller-category and
category-satisfaction tables, plus `vw_category_performance`, can share one
category filter.

---

## `seller_scorecard.csv` (added in the measure audit)

**Purpose.** `vw_seller_performance` publishes per-seller **rates** (late %,
average delivery days, average rating) but not the counts behind them. The
only way to total them across sellers was therefore `AVERAGE` of the rates,
which gives a 1-order seller the same weight as a 2,000-order seller (late
rate 8.42% unweighted). This table supplies the counts, so the seller measures
are ratio-of-sums.
**Grain.** One row per seller with eligible sales: **3,053** (same sellers as
`vw_seller_performance`).

| Column | Type | Meaning |
|---|---|---|
| `seller_id` | text (key) | |
| `orders_served` | integer | eligible orders containing the seller (= `vw_seller_performance.orders_served`) |
| `delivery_measurable_orders` | integer | of those, orders with a real delivery date |
| `late_orders` | integer | measurable orders delivered after the estimate |
| `delivery_days_sum` | decimal | sum of purchase→delivery days over measurable orders |
| `reviewed_orders` | integer | orders with at least one review |
| `review_score_sum` | decimal | sum of each order's exact mean review score (0 when none) |
| `poor_rated_orders` | integer | orders whose mean score ≤ 2 |

Counts are at **seller-order pair** grain: an order with two sellers counts
for each. Divided per seller, they reproduce every seller's published rate
(validated for all 3,053). Summed, the late rate is **8.02%**, against the
platform's 8.11% at order grain. The difference is the 1,277 multi-seller
orders, which count once per seller and were late only 1.38% of the time.
Ratings are inherited order ratings, not seller ratings.

---

## Relationships and use in Tableau

The Tableau relationships, data types and filter rules are in
[`../tableau/data_model.md`](../tableau/data_model.md) (§3–§5), and the keys and
orphans are re-checked by `scripts/check_tableau_data.py`. In short:
`dim_category` relates to `vw_category_performance`, `product_performance` and
`category_satisfaction`; `vw_seller_performance` to `seller_scorecard` and
`seller_category_performance`; `vw_customer_summary` to `rfm_customer_segments`;
`vw_order_summary` to `delivery_stage_orders`. `cohort_retention` and
`delivery_stage_summary` stand alone.

Quick checks once loaded in Tableau (expected values validated on macOS):

- `SUM([product_revenue])` (product_performance) = R$ 13,494,400.74
- `SUM([product_revenue])` (seller_category_performance, RP Sellers) = R$ 13,494,400.74
- `SUM([monetary_value])` = R$ 13,494,400.74; `rfm_customer_segments(Count)` = 96,096; scored = 94,983
- Cohort matrix shows **blank**, not 0, in the 190 unobserved cells
- `Last Mile Share` = 74.21%

---

## Validation results — 90 / 90 PASS (2026-11-20)

`scripts/validate_tableau_sources.py` compares three independent paths: the
exported CSV, the live SQL result, and a pandas rebuild from `dataset/cleaned/`
that never reads the SQL. It also reconciles against the existing validated
views. No expected value is typed in by hand.

| Source | Checks | Highlights |
|---|---|---|
| Every source | 4 each | CSV identical to live SQL; grain unique; no duplicate rows; no NULLs in required columns |
| A RFM | 13 | all 96,096 rows identical to pandas (R/F/M, scores, segments, dates); `customer_unique_id` not `customer_id`; monetary = 13,494,400.74 to the cent; per-person match with `vw_customer_summary`; ties share scores; F ∈ {1,3,5} |
| B Cohort | 12 | all 400 cells identical to pandas; sizes = `vw_customer_summary`; 190 unobserved cells NULL, not 0; offset 0 = 100%; retention arithmetic |
| C Product | 10 | every row identical to pandas; revenue to the cent; units = 112,101 eligible items (no multiplication); category roll-up = `vw_category_performance` |
| D Seller × category | 11 | every row identical to pandas; revenue and items roll up exactly to `vw_seller_performance` (3,053 sellers) and `vw_category_performance`; non-additive `order_count` as documented |
| E Stages (2 files) | 20 | population 95,088 derived from timestamps = flag; every order's seconds identical to pandas; no negatives; stages sum to total; shares 3.19 / 22.60 / 74.21% recomputed |
| F Category satisfaction | 10 | every row identical to pandas; no review counted twice in a category; totals reconcile after the 808 multi-category duplicates; all 4,795 Q19 reviews accounted for |
| dim_category | 6 | covers every category in C, D, F and `vw_category_performance` |
| seller_scorecard | 8 | every row identical to pandas; same 3,053 sellers and `orders_served` as `vw_seller_performance`; reproduces every seller's published late %, delivery days, rating and poor-rated count; pair grain documented |

**The checks catch real errors.** In a mutation test on scratch copies, four
planted faults were all caught (13 failures): a 1-cent revenue change on one
product, a 0 in an unobserved cohort cell, one customer's segment swapped, and
one category's review count +1.

**Rounding.** SQL rounds averages to 4 or 6 decimals (exact decimal, half-up).
The pandas rebuild keeps the exact value, and the comparison allows at most half
a unit in the last place, which is what correct rounding guarantees. An earlier
run with pandas also rounding produced 24 false mismatches, all on exact ties
such as 129.86625.

---

## Unresolved inconsistencies (recorded, not silently fixed)

| # | Where | Issue | Status |
|---|---|---|---|
| 1 | `documentation/data_quality_report.md` Q05 | Says AOV uses **98,666** orders (all orders with items). The validated denominator is **98,199** eligible orders with items (`kpi_definitions.md` KPI 4) | Correction note added beside the original text on 2026-11-20; original wording preserved |
| 2 | `reports/business_insights.md` Insight 6 | Counts came from `NTILE`, which splits ties arbitrarily (21,917 / 982; later 22,072 / 957) | **Resolved 2026-11-20.** Q32, notebook 03 §B2 and Insight 6 use tie-consistent scoring; identical to this source |
| 3 | `sql/06` Q33 vs notebook 03 §B3 | Elapsed months vs calendar months; month-1 returns 348 vs 453 | **Resolved 2026-11-20.** Q33 uses calendar months with NULL for unobservable months; notebook 03 §B3 now also leaves unobserved cells blank; both match `cohort_retention.csv` |
| 4 | Insight 14 / notebook 03 §F2 | Category ratings were item-weighted (20 categories / 60.0%) | **Resolved 2026-11-20.** Notebook 03 §F2, chart F2, Insight 14 and its follow-up gap table use review grain (15 / 45.1%); identical to `category_satisfaction.csv` |
| 5 | dashboard specification | Listed the superseded stage figures (0.41 / 2.78 / 9.31, 74%) and the all-review "cliff" table | **Corrected** on 2026-11-20 to the Phase 2 figures |
| 6 | KPI 19 vs stage total | 12.56 days (96,476 orders) vs 12.62 days (95,088): different populations, both correct | Documented above; label both |
| 7 | the view-export script under pandas 3 (now `scripts/export_tableau_data.py`) | Wrote `review_creation_date` in two formats in one column (5,882 date-only values) | **Fixed** (explicit timestamp format); every existing extract re-verified byte-identical to the 13 Nov export apart from the three new Phase 2 columns |
| 8 | `vw_monthly_revenue` (MySQL view) | `moving_avg_3m` and `mom_growth_pct` use `ROWS BETWEEN 2 PRECEDING`/`LAG` over the months that exist, so 2016-12 and 2017-01 average across the missing Nov 2016 and 2017-01 MoM compares with Dec 2016's single order | **Open.** The dashboard measures (M10, M11) blank those months and the dashboard does not use this view; the view is unchanged (changing it is a schema change). Don't use the view's columns for those months |
| 9 | Seller late rate 8.02% vs platform 8.11% | Pair grain vs order grain; both correct | Documented in `dax_measures.md`; label the Page 4 card |
