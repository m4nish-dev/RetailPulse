# Data Quality Report

**Assessed:** 2026-11-12 · `notebooks/01_data_exploration.ipynb`
**Scope:** all 9 raw tables, 1,551,933 rows

> **Nothing in this report has been fixed.** Phase 1 measures; Phase 3 fixes.
> Separating the two is deliberate: you cannot choose a sensible remedy before
> you know the size and cause of a problem, and a cleaning step with no recorded
> justification is indistinguishable from a bug.

---

## Verdict

**The dataset is in good condition.** Referential integrity is near-perfect
(zero orphans in 6 of 7 relationships), there are no negative prices, no
unparseable dates, and no exact duplicate rows in any business table.

The issues that exist are mostly *absences with a legitimate cause* rather than
corruption. Three are serious enough to change how analysis must be done.

| Severity | Count | Meaning |
|---|---|---|
| 🔴 High | 4 | Will produce wrong conclusions if ignored |
| 🟠 Medium | 3 | Will distort specific metrics |
| 🟡 Low | 9 | Small; flag and document |
| ⚪ Info | 1 | No defect; a trap to be aware of |

---

## 🔴 High severity

### Q01 · 8 orders are marked `delivered` but have no delivery date
**Table:** `orders` · **Count:** 8 of 96,478 delivered orders

A genuine contradiction: the status claims delivery, the timestamp is missing.
Too few to matter for totals, but they corrupt any average that assumes
`delivered` implies a date.

**Decision:** exclude from delivery-time and on-time metrics; keep in revenue
and order counts. **All delivery KPIs use a denominator of 96,476 orders with
an actual delivery date, not 96,478.** State the denominator on the dashboard.

---

### Q02 · `review_id` is not unique
**Table:** `reviews` · **Count:** 789 IDs reused across 1,603 rows

99,224 rows hold 98,410 distinct review IDs. One ID appears on up to 3
*different* orders — one survey response covering a multi-order purchase. In
addition, 547 orders carry more than one review.

**Why this is dangerous:** `drop_duplicates(subset='review_id')` looks like the
obvious fix and would silently discard real review scores attached to real
orders.

**Decision:** do **not** deduplicate on `review_id`. Use
`(review_id, order_id)` as the key. For order-level average rating, aggregate
to one score per order first, then join — otherwise the join multiplies order
rows and double-counts revenue.

---

### Q06 · Partial months at both ends of the date range
**Table:** `orders` · **Count:** 4 months, 25 orders total

| Month | Orders |
|---|---|
| 2016-09 | 4 |
| 2016-12 | 1 |
| 2018-09 | 16 |
| 2018-10 | 4 |

These are extract boundaries, not a business collapse. Plotted raw, the monthly
revenue chart appears to fall off a cliff — a completely wrong conclusion, and
a classic giveaway of an unexamined portfolio project.

**Decision:** trend, growth and cohort analysis uses the **stable window
2017-01 → 2018-08** (20 complete months, 99,092 orders, 99.65% of the data).
Grand totals use all data. Every chart states its window.

---

### Q07 · 2016 has only 329 orders, making year-over-year growth meaningless
**Table:** `orders` · 2016: 329 · 2017: 45,101 · 2018: 54,011

"2017 vs 2016 growth" would be roughly +13,600% — arithmetically true, utterly
misleading.

**Decision:** report YoY only as **2018 Jan–Aug vs 2017 Jan–Aug**, a
like-for-like comparison of complete months. Never quote a full-year 2016
comparison.

---

## 🟠 Medium severity

### Q03 · Two product categories have no English translation
**Tables:** `products` → `translation` · **Count:** 13 products

`pc_gamer` (3 products) and
`portateis_cozinha_e_preparadores_de_alimentos` (10 products) exist in
`products` but not in the translation lookup. An INNER JOIN drops them silently.

**Decision:** LEFT JOIN and supply the two names manually —
`pc_gamer` → `pc_gamer`,
`portateis_cozinha_e_preparadores_de_alimentos` → `portable_kitchen_food_preparers`.

---

### Q04 · 610 products have a NULL category
**Table:** `products` · **Count:** 610 (1.85%)

The same 610 rows are also null for `product_name_lenght`,
`product_description_lenght` and `product_photos_qty` — consistent with
products created without full catalogue data, not random loss.

**Decision:** label the category `unknown` rather than dropping. These products
carry real revenue; removing them would understate category totals and quietly
change the revenue figure.

---

### Q05 · 775 orders have no line items
**Table:** `orders` vs `order_items` · **Count:** 775

By status: `unavailable` 603, `canceled` 164, `created` 5, `invoiced` 2,
`shipped` 1. Orders that never completed, so the absence is correct.

**Decision:** keep them in `orders` (they are real orders and part of the
cancellation story) but **exclude them from the AOV denominator**. AOV uses the
98,666 orders that have items.

---

## 🟡 Low severity

| ID | Table | Issue | Count | Decision |
|---|---|---|---|---|
| **Q08** | `orders` | Delivered to customer **before** carrier handoff — an impossible sequence | 23 | Add a `data_quality_flag` column. Do not alter timestamps. Almost certainly a scanning lag |
| **Q09** | `payments` | `payment_value` = 0 | 9 | Flag and retain. Too few to affect totals |
| **Q10** | `payments` | `payment_installments` = 0 (not a valid count) | 2 | Treat as 1 instalment; document the assumption |
| **Q11** | `payments` | `payment_type` = `not_defined` | 3 | Map to `unknown`; retain the rows |
| **Q12** | `geolocation` | 261,831 exact duplicate rows (26.2%) | 261,831 | Expected — a zip prefix is an area, so many readings share one. Aggregate to one point per prefix if maps are used |
| **Q13** | `products` | Missing weight / dimensions | 2 | Leave NULL. No planned KPI uses them |
| **Q14** | `orders` | 768 orders have no review (99.23% coverage) | 768 | LEFT JOIN for ratings, never INNER |
| **Q15** | `orders` | Missing `order_approved_at` | 160 | Leave NULL. Approval lag is not a planned KPI |
| **Q16** | `products` | Source column names misspelled: `product_name_lenght`, `product_description_lenght` | 2 cols | Load with original names; rename in cleaned output and document |

---

## ⚪ Informational

### Q17 · Review text contains embedded newlines
**Table:** `reviews` · **Count:** 3,852 records, 5,495 newline characters

Not a defect — customers pressed Enter while typing. But it makes naive line
counting wrong: the file has **104,720 physical lines** and **99,224 records**.

Reconciliation: 99,224 records + 1 header + 5,495 embedded newlines = 104,720. ✓

**Relevant twice more:** when importing to MySQL (use proper quoting and
`LINES TERMINATED BY`), and whenever anyone sanity-checks a row count with
`wc -l`. Separately, `product_category_name_translation.csv` has no trailing
newline, so `wc -l` undercounts it by one.

---

## Checks that passed

Worth recording — a clean result is a finding too.

| Check | Result |
|---|---|
| Exact duplicate rows in business tables | **0** in all 8 (only `geolocation` has any) |
| Negative prices, freight or payments | **0** |
| Unparseable dates across 9 date columns | **0** |
| Orphan foreign keys | **0** in 6 of 7 relationships |
| Delivered before purchased | **0** |
| Approved before purchased | **0** |
| Estimated delivery before purchase | **0** |
| Nulls in any key column | **0** |
| `order_status` unexpected values | **0** — all 8 are valid |
| `review_score` out of the 1–5 range | **0** |

---

## Summary of Phase 3 actions

| Action | Rows affected | Issue |
|---|---|---|
| Flag, do not drop | 23 | Q08 impossible date sequence |
| Flag, do not drop | 14 | Q09, Q10, Q11 payment anomalies |
| Relabel to `unknown` | 610 | Q04 null category |
| Add missing translations | 13 | Q03 |
| Exclude from delivery metrics only | 8 | Q01 |
| Exclude from AOV denominator only | 775 | Q05 |
| Restrict trend window | — | Q06, Q07 |
| Rename columns in cleaned output | 2 cols | Q16 |
| **Rows deleted from the dataset** | **0** | — |

**No row will be deleted.** Every exclusion is scoped to a specific metric and
documented, so any number can be traced back to the rows behind it.
