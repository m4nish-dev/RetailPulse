# Phase 3 — Data Cleaning Report

**Date:** 2026-11-13
**Notebook:** `notebooks/02_data_cleaning.ipynb` (44 cells — executes end to end, 0 errors)
**Updated:** 2026-11-20 — fix-Phase 2 added Q18 and Q19 flags and 12 validation checks
**Output:** 9 tables in `dataset/cleaned/` (569,776 rows, 90 MB)
**Status:** ✅ **PASSED** — 46 of 46 validation checks

---

## 1. Headline

| | |
|---|---|
| Issues resolved | **19 of 19** (Q18, Q19 added 2026-11-20) |
| Rows deleted | **0** |
| Values imputed or invented | **0** |
| Original columns overwritten | **0** |
| Validation checks | **46 passed, 0 failed** |
| Raw files modified | **None** |

Every exclusion in this project is scoped to a specific metric and recorded.
Nothing was silently removed.

---

## 2. Approach

### 2.1 Flag, don't delete

The notebook never calls `dropna()` or `drop_duplicates()`. Both would destroy
real data here:

- `dropna()` on `orders` would delete **2,965** orders whose only fault is
  never having been delivered.
- `drop_duplicates(subset='review_id')` would delete **814** genuine
  order-to-score links.

Instead, problems are flagged in new columns and exclusions are scoped to the
metric that needs them. An order missing a delivery date is excluded from
delivery-time averages and kept in revenue, order counts and everything else.

### 2.2 Validation that cannot be ignored

Checks are written as `assert`, so a regression **stops the notebook** rather
than writing a quietly wrong file. The notebook refuses to produce output it
cannot stand behind.

### 2.3 Conversions fail loudly

Two helpers, `to_numeric_strict` and `to_datetime_strict`, raise an exception
if *any* value fails to parse. The default `errors='coerce'` would turn a bad
value into `NaN` silently — which is precisely how a money column gets
corrupted without anyone noticing.

### 2.4 The issue register was re-verified first

Before cleaning anything, `scripts/verify_issue_register.py` recomputed all 17
issue counts directly from `dataset/raw/`. **All 17 matched; 0 mismatches.**
No cleaning decision rests on a number copied from an earlier run.

---

## 3. Raw vs cleaned row counts

| Table | Raw | Cleaned | Δ | Note |
|---|---|---|---|---|
| orders | 99,441 | 99,441 | 0 | unchanged |
| order_items | 112,650 | 112,650 | 0 | unchanged |
| payments | 103,886 | 103,886 | 0 | unchanged |
| reviews | 99,224 | 99,224 | 0 | unchanged |
| customers | 99,441 | 99,441 | 0 | unchanged |
| products | 32,951 | 32,951 | 0 | unchanged |
| sellers | 3,095 | 3,095 | 0 | unchanged |
| translation | 71 | **73** | **+2** | 2 English category names added by hand (Q03) |
| geolocation | 1,000,163 | **19,015** | **−981,148** | aggregated to one row per zip prefix (Q12) |

**Only two tables changed size, both deliberately.**

The geolocation reduction is an aggregation, not a deletion: 1,000,163
coordinate readings collapse to 19,015 zip prefixes using the **median**
lat/lng. Median rather than mean, because a median ignores the occasional
wildly wrong coordinate instead of being dragged toward it. This table is
reference data for maps; no KPI depends on it.

---

## 4. What was done, issue by issue

| ID | Severity | Records | Action taken |
|---|---|---|---|
| Q01 | 🔴 High | 8 | Flagged `has_delivery_anomaly`; excluded from delivery timing only |
| Q02 | 🔴 High | 1,603 rows / 789 ids | All rows kept; composite key `(review_id, order_id)` adopted |
| Q06 | 🔴 High | 4 months | `in_stable_window` flag added; no rows removed |
| Q07 | 🔴 High | 329 | YoY restricted to Jan–Aug like-for-like |
| Q03 | 🟠 Medium | 13 products | 2 English names added; LEFT JOIN preserved all products |
| Q04 | 🟠 Medium | 610 | Labelled `unknown`, not dropped |
| Q05 | 🟠 Medium | 775 | `has_items = False`; excluded from AOV denominator only |
| Q08 | 🟡 Low | 23 | Flagged `has_date_anomaly`; timestamps untouched |
| Q09 | 🟡 Low | 9 | Flagged, retained |
| Q10 | 🟡 Low | 2 | Corrected in a **new** column; original untouched |
| Q11 | 🟡 Low | 3 | Corrected in a **new** column; original untouched |
| Q12 | 🟡 Low | 261,831 | Aggregated to zip-prefix grain |
| Q13 | 🟡 Low | 2 | Left NULL |
| Q14 | 🟡 Low | 768 | `has_review = False`; LEFT JOIN enforced |
| Q15 | 🟡 Low | 160 | Left NULL |
| Q18 | 🟠 Medium | 1,359 | Flagged `carrier_before_approval`; `stage_timing_valid` defines the stage-metric population; timestamps untouched (added 2026-11-20) |
| Q19 | ⚪ Info | 4,795 reviews | Flagged `review_before_delivery` at review grain; no review removed (added 2026-11-20) |
| Q16 | 🟡 Low | 2 columns | `lenght` → `length` in the cleaned output |
| Q17 | ⚪ Info | 3,852 | CSV quoting verified by round-trip test |

Full reasoning for each: [`documentation/cleaning_decisions.md`](../documentation/cleaning_decisions.md).

---

## 5. Two investigations worth reading

### 5.1 `review_id` repeats — investigated before acting

The obvious move is `drop_duplicates(subset='review_id')`. The notebook tested
the assumption first:

> Of the **789** repeated review ids, how many carry **different scores**
> across their rows? → **0**

Every repeated id carries the *same* score against a *different* `order_id`.
It is one survey response covering several orders from a single purchase event.
The rows are not duplicates of each other — each ties a real score to a real,
distinct order. Dropping them would have deleted **814 genuine order-to-score
links** and quietly biased every rating metric.

**This is the difference between cleaning and damaging data: one check.**

### 5.2 Rounding before classifying changes the answer

`delay_days` is rounded to 4 decimal places for display, but `is_late` is
derived from the **unrounded** timestamp difference.

An earlier version of this pipeline rounded to 2dp first. The result:

| Method | Late orders |
|---|---|
| Exact timestamp difference | **7,827** |
| Rounded to 2dp, then compared | 7,821 |

Six orders late by **under seven minutes** rounded to `0.00` and were
reclassified as on-time. Small, but it is a wrong answer produced by a step
that looks like tidying. The notebook prints this comparison so the reasoning
is visible.

---

## 6. Derived columns

`orders_clean.csv` carries **38 columns**: the 8 original plus 30
derived or joined. No original column was overwritten.

**Calendar:** `order_date` · `order_month` · `order_year`
**Money:** `order_revenue` · `order_freight` · `item_count` · `n_sellers`
**Delivery:** `delivery_days` · `delay_days` · `is_late` · `delivery_measurable`
**Status flags:** `is_delivered` · `revenue_eligible` · `has_items` · `has_review` · `in_stable_window`
**Quality flags:** `has_date_anomaly` · `date_anomaly_note` · `has_delivery_anomaly` · `carrier_before_approval` (Q18) · `stage_timing_valid` (Q18)
**Reviews:** `review_score_avg` · `review_count`
**Payments:** `payment_total` · `payment_count` · `max_installments`
**Customer:** `customer_unique_id` · `customer_state` · `customer_city` · `customer_zip_code_prefix`

`order_items_clean.csv` gains `product_category_name_english`, `seller_state`,
`seller_city`, order context and `item_total`.

`order_reviews_clean.csv` gains `review_before_delivery` (Q19): True/False when
the order has a delivery date, empty (NULL) otherwise.

### Aggregate before joining — enforced by assertion

Each child table was collapsed to one row per order *before* joining:

| Source | Raw rows | After aggregation |
|---|---|---|
| `order_items` | 112,650 | 98,666 orders |
| `reviews` | 99,224 | 98,673 orders |
| `payments` | 103,886 | 99,440 orders |

After all four joins the notebook asserts `len(orders) == 99,441`. Had any join
fanned out, execution would have stopped. Measured cost of getting this wrong:
**+4.54%** revenue via payments, **−0.47%** via reviews.

---

## 7. Validation results — 46 / 46 passed

| Group | Checks | Result |
|---|---|---|
| Row counts preserved (7 tables) | 7 | ✅ |
| Intentional size changes (translation, geolocation) | 2 | ✅ |
| Primary keys valid (incl. 3 composite) | 7 | ✅ |
| Foreign keys — zero orphans | 4 | ✅ |
| Money reconciliation | 4 | ✅ |
| Counts vs Phase 1 | 7 | ✅ |
| No silent data loss | 3 | ✅ |
| Q18 / Q19 flags (counts, flag = condition, valid population, NULL rule, timestamps and review keys unchanged vs raw) | 12 | ✅ |

**Money reconciliation** deserves a note. Beyond checking that raw and cleaned
totals match, the notebook asserts that `SUM(orders.order_revenue)` equals
`SUM(order_items.price)` — proving the item-to-order aggregation lost and
invented nothing.

| Check | Raw | Cleaned |
|---|---|---|
| Product revenue (GMV) | 13,591,643.70 | 13,591,643.70 ✅ |
| Freight | 2,251,909.54 | 2,251,909.54 ✅ |
| Payment total | 16,008,872.12 | 16,008,872.12 ✅ |
| Order-level revenue vs item GMV | — | matches to the cent ✅ |

**Round-trip test.** Every exported file was re-read and compared. All 9
returned identical row counts and columns — including the 3,852 reviews whose
comment text contains newlines, confirming CSV quoting survived export.

---

## 8. Headline figures from the cleaned data

| Metric | Value |
|---|---|
| Total orders | 99,441 |
| Orders with line items | 98,666 |
| Delivered orders | 96,478 |
| Distinct customers (people) | 96,096 |
| Product revenue — all statuses | 13,591,643.70 BRL |
| Product revenue — eligible | 13,494,400.74 BRL |
| Freight charged | 2,251,909.54 BRL |
| Average Order Value (eligible) | 137.42 BRL |
| Median order value (eligible) | 86.90 BRL |
| Average delivery time | 12.56 days |
| Median delivery time | 10.22 days |
| On-time delivery rate | 91.89% |
| Average review score | 4.0864 |
| Cancellation rate | 0.6285% |

Note AOV (137.42) against median order value (86.90). The mean sits **58%
above** the median — a long right tail of expensive orders. Any dashboard
quoting only the average overstates what a typical customer spends.

---

## 9. New finding from this phase

**November 2016 is absent from the dataset entirely.** Not a sparse month — a
month with zero rows.

Phase 1 recorded four *sparse* months. Phase 3's month-by-month listing shows
the sequence runs 2016-09, 2016-10, **[nothing]**, 2016-12. 2016 is therefore
**discontinuous**, not merely thin, and any line chart spanning it would draw
a straight segment across a gap with no data behind it.

This strengthens the existing decision to start the analysis window at
2017-01 and has been added to `cleaning_decisions.md` under Q06.

---

## 10. Unresolved items carried forward

| Item | Phase | Why it is still open |
|---|---|---|
| `reviews` has no natural single-column key | 4 | Composite `(review_id, order_id)` vs a surrogate auto-increment is a schema decision |
| City names unnormalised (4,119 variants) | 4/5 | Geography stays state-level until normalised. Needs a mapping, not a rule |
| 23 impossible date sequences | — | Flagged. Cause unknowable from this data; **not resolvable**, only recorded |
| Are delivery estimates padded? | 5 | Orders arrive ~11 days early on average. A finding to investigate, not a defect |
| Portuguese review text | 5 | Sentiment analysis needs a multilingual model. Optional |
| Cleaned data not in Git | — | 90 MB derived artifact; regenerable in ~2 min. See `dataset/cleaned/README.md` |

---

## 11. Files produced

| File | Rows | Cols | Size |
|---|---|---|---|
| `orders_clean.csv` | 99,441 | 38 | 34 MB |
| `order_items_clean.csv` | 112,650 | 18 | 24 MB |
| `order_reviews_clean.csv` | 99,224 | 8 | 14 MB |
| `customers_clean.csv` | 99,441 | 5 | 8.2 MB |
| `order_payments_clean.csv` | 103,886 | 8 | 6.7 MB |
| `products_clean.csv` | 32,951 | 10 | 3.1 MB |
| `geolocation_clean.csv` | 19,015 | 6 | 1.1 MB |
| `sellers_clean.csv` | 3,095 | 4 | 161 KB |
| `category_translation_clean.csv` | 73 | 2 | 2.6 KB |

**Not committed to Git** — a 90 MB derived artifact that regenerates from
`dataset/raw/` in about two minutes. Instructions:
[`dataset/cleaned/README.md`](../dataset/cleaned/README.md).

---

## 12. Verdict

| Gate | Result |
|---|---|
| Notebook executes end to end | ✅ 28/28 code cells, 0 errors |
| Validation checks | ✅ 46 / 46 |
| Raw data unmodified | ✅ |
| Rows deleted | ✅ 0 |
| Values imputed | ✅ 0 |
| Revenue reconciles to raw | ✅ to the cent |
| Keys and relationships intact | ✅ 0 orphans |
| Exported files round-trip | ✅ 9 / 9 |

**Phase 3: PASSED.** Ready for Phase 4 — MySQL schema design and analytical queries.
