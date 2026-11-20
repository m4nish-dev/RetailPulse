# Cleaning Decisions — Definitive Issue Register

**Version 2.1** · 2026-11-20 · supersedes the register in `data_quality_report.md`
(2.1 adds Q18 and Q19 from the fix-Phase 2 data-quality investigation)
**Implemented by:** `notebooks/02_data_cleaning.ipynb`

---

## Reconciliation note

Earlier in this project the issue register drifted: the Phase 1 notebook and
`data_quality_report.md` briefly disagreed on both the total and the severity
split. That was reconciled at the end of Phase 1, and then **every count was
independently recomputed from `dataset/raw/`** by
`scripts/verify_issue_register.py` before any cleaning began.

**Result: 17 issues, all 17 counts verified, 0 mismatches.** The numbers below
are measured, not inherited.

**Version 2.1 (fix-Phase 2):** the final project audit found two timestamp issues the
original register missed. They were investigated in
`notebooks/04_data_quality_investigation.ipynb` before any treatment was chosen and
added as **Q18** and **Q19**. The register is now **19 issues, 19/19 verified from
`dataset/raw/`, 0 mismatches.**

| Severity | Count |
|---|---|
| 🔴 High | 4 |
| 🟠 Medium | 4 |
| 🟡 Low | 9 |
| ⚪ Info | 2 |
| **Total** | **19** |

Re-run the verification at any time:

```bash
./venv/bin/python -I scripts/verify_issue_register.py
```

---

## The governing principle

> **No row is deleted. No value is invented.**

A typical cleaning script calls `dropna()` and `drop_duplicates()`. Both would
be actively wrong here:

- `dropna()` on `orders` deletes 2,965 real orders whose only fault is never
  having been delivered.
- `drop_duplicates(subset='review_id')` deletes **814 genuine order-to-score
  links**, because `review_id` repeats for a reason unrelated to duplication.

Instead, problems are **flagged in new columns**, and exclusions are **scoped
to the single metric** that needs them. An order missing a delivery date is
excluded from delivery-time averages and kept everywhere else.

The payoff: every number later in this project traces back to the exact rows
behind it, and any exclusion can be explained and reversed.

---

## 🔴 High severity

### Q01 — 8 orders marked `delivered` with no delivery date
| | |
|---|---|
| **Table / column** | `orders.order_delivered_customer_date` |
| **Records affected** | **8** (verified) |
| **Decision** | Flag `has_delivery_anomaly = True`. Keep in revenue and order counts. Exclude from delivery timing **only**. |
| **Reason** | The status and the timestamp contradict each other. Too few to affect totals, but they corrupt any average assuming `delivered` implies a date. We cannot know the true delivery date, so inventing one is not an option. |
| **Validation** | `delivery_measurable` sums to **96,476**, not 96,478. Asserted in the notebook. |

> **Tempting and wrong:** copying `order_estimated_delivery_date` into the gap.
> It would make the data look complete and silently push on-time delivery to
> 100% — every order would arrive exactly as promised. The metric would be
> destroyed and the chart would look perfect.

### Q02 — `review_id` is not unique
| | |
|---|---|
| **Table / column** | `reviews.review_id` |
| **Records affected** | **789 ids** spanning **1,603 rows** (verified) |
| **Decision** | Keep every row. Adopt the composite key `(review_id, order_id)`. |
| **Reason** | Investigated before acting. Of the 789 repeated ids, **0 carry different scores** across their rows — each is the same survey response attached to a *different* order from one purchase event. The rows are not duplicates of each other. |
| **Validation** | Composite key asserted unique across 99,224 rows. Exact duplicate rows: **0**. |

### Q06 — Partial months distort every trend
| | |
|---|---|
| **Table** | `orders` |
| **Records affected** | **4 months** holding 25 orders |
| **Decision** | Add `in_stable_window` flag for 2017-01 … 2018-08. **No rows removed.** |
| **Reason** | 2016-09 (4 orders), 2016-12 (1), 2018-09 (16), 2018-10 (4) are extract boundaries, not business performance. Plotted raw they imply a collapse that never happened. |
| **Validation** | 99,092 orders inside the window (99.65%). |

> **Found during Phase 3:** **November 2016 is absent from the dataset
> entirely** — zero rows, not a low month. 2016 is therefore *discontinuous*,
> not merely thin, and a line chart spanning it would draw straight across a
> gap. This strengthens the case for starting at 2017-01 and was not recorded
> in Phase 1.

### Q07 — 2016 cannot support year-over-year growth
| | |
|---|---|
| **Table** | `orders` |
| **Records affected** | **329** orders in 2016 (vs 45,101 in 2017) |
| **Decision** | Report YoY only as 2018 Jan–Aug vs 2017 Jan–Aug. |
| **Reason** | Full-year 2017-vs-2016 growth computes to roughly +13,600% — arithmetically correct, completely misleading. |
| **Validation** | Like-for-like Jan–Aug: revenue **+138.3%** (revenue-eligible), orders **+135.1%** (all statuses) or **+137.3%** (eligible with items — the AOV population). |

---

## 🟠 Medium severity

### Q03 — Two categories missing from the translation table
| | |
|---|---|
| **Table** | `products` → `product_category_name_translation` |
| **Records affected** | **13 products** in 2 categories (verified) |
| **Decision** | LEFT JOIN, and add the two English names by hand: `pc_gamer` → `pc_gamer`; `portateis_cozinha_e_preparadores_de_alimentos` → `portable_kitchen_food_preparers`. Translation table grows 71 → 73. |
| **Reason** | An INNER JOIN would have deleted **623 products** (13 untranslated + 610 with no category) with no error message — the quiet kind of bug that produces a plausible but wrong category report. |
| **Validation** | `products` stays at 32,951 rows. Every product has an English label. Asserted. |

### Q04 — 610 products have no category
| | |
|---|---|
| **Table / column** | `products.product_category_name` |
| **Records affected** | **610** (1.85%, verified) |
| **Decision** | Label `unknown`. Do not drop. |
| **Reason** | These products carry real revenue. Dropping them would understate category totals and quietly change the headline revenue figure. The same 610 rows are also null for three listing-attribute columns, consistent with products created without full catalogue data rather than random loss. |
| **Validation** | 610 rows labelled `unknown`; 0 left null. |

### Q05 — 775 orders have no line items
| | |
|---|---|
| **Table** | `orders` vs `order_items` |
| **Records affected** | **775** (verified) |
| **Decision** | Keep in `orders` with `has_items = False`. Exclude from the AOV denominator only. |
| **Reason** | By status: `unavailable` 603, `canceled` 164, `created` 5, `invoiced` 2, `shipped` 1. Orders that never completed, so the absence is correct — but they would deflate AOV if counted. |
| **Validation** | AOV denominator = 98,199 eligible orders with items. |

### Q18 — Carrier handoff recorded before payment approval
| | |
|---|---|
| **Table / column** | `orders.order_delivered_carrier_date` vs `orders.order_approved_at` |
| **Records affected** | **1,359** orders (verified): 1,350 delivered, 9 shipped. 1.40% of the 96,461 delivered orders with both timestamps |
| **Decision** | New flag `carrier_before_approval`. New flag `stage_timing_valid` (all four timestamps present and purchase ≤ approval ≤ carrier ≤ customer). Delivery-**stage** metrics use `stage_timing_valid = 1` only. **No row deleted, no timestamp altered.** |
| **Reason** | Both timestamps have full time precision, so this is not a rounding artefact. 61% of the flagged orders fall on two approval dates (2018-04-24 and 2018-07-05). On each, 3–4× a normal day's approvals were recorded within 7–9 hours, covering a week of earlier purchases. This is consistent with approvals being **recorded late in bulk**. It is not boleto (21% of flagged vs 20% of other orders) and not concentrated by seller (584 sellers) or state. A subset of 166 has the carrier handoff before the *purchase*, which a late approval cannot explain; those point to carrier-timestamp errors. The root cause cannot be proven from the data, so the timestamps are flagged, not "fixed". |
| **Scope of impact** | Overall delivery time (purchase → delivery), on-time rate and delay are **unaffected**: they do not use these two timestamps. Only the stage breakdown is affected. On the corrected population (95,088 orders) the last mile is **74.2%** of delivery time, versus 74.1% before, so Insight 12 stands. |
| **Validation** | 1,359 flagged; flag equals the recomputed condition; `stage_timing_valid` population has zero negative stage intervals and excludes every Q18 and Q08 row; original timestamps identical to raw. Asserted in notebook 02 and `08_validation.sql` §13. |

> **Disclosure.** The Phase 3 notebook printed a related count ("carrier handoff
> before purchase: 166") but it was never entered in the register. Later summaries
> wrongly implied that Q08's 23 rows were the only sequence failures. Q18 corrects that.

---

## 🟡 Low severity

| ID | Table / column | Records | Decision | Reason | Validation |
|---|---|---|---|---|---|
| **Q08** | `orders` date sequence | **23** | Flag `has_date_anomaly`; **do not alter timestamps** | Delivered to customer before carrier handoff. Likely a scanning lag. The true values are unknowable, so recording beats guessing | 23 flagged, 0 timestamps changed |
| **Q09** | `payments.payment_value` | **9** | Flag `payment_anomaly`, retain | Payments of zero. Too few to affect totals | Payment total preserved exactly |
| **Q10** | `payments.payment_installments` | **2** | New column `payment_installments_clean` reads 1; **original untouched** | 0 instalments is not a valid count. Correcting in a new column keeps the assumption auditable | Original column unchanged |
| **Q11** | `payments.payment_type` | **3** | New column `payment_type_clean` reads `unknown`; original untouched | `not_defined` is not a usable category label | Original column unchanged |
| **Q12** | `geolocation` duplicates | **261,831** | Aggregate to one row per zip prefix using **median** lat/lng and modal city/state | A zip prefix covers an *area*, so many readings share one — not corruption. Median ignores the occasional wildly wrong coordinate instead of being dragged toward it | 1,000,163 → 19,015 rows |
| **Q13** | `products` weight/dimensions | **2** | Keep NULL | No planned KPI uses them | 2 nulls retained |
| **Q14** | `orders` with no review | **768** | Flag `has_review = False`; always LEFT JOIN | An INNER JOIN would silently drop 768 orders from any rating analysis | Review coverage 98,673 (99.23%) |
| **Q15** | `orders.order_approved_at` | **160** | Keep NULL | Approval lag is not a planned KPI | 160 nulls retained |
| **Q16** | `products` column names | **2 columns** | Rename `product_name_lenght` → `product_name_length`, `product_description_lenght` → `product_description_length` | Misspelled in the source data. Renamed only in the cleaned output, with the rename documented | Both columns present and correctly named |

---

## ⚪ Informational

### Q17 — Review text contains embedded newlines
| | |
|---|---|
| **Records affected** | **3,852** records, 5,495 newline characters |
| **Decision** | No change. Ensure proper CSV quoting on export. |
| **Reason** | Not a defect — customers pressed Enter while typing. But it makes line-counting wrong: the file has **104,720 physical lines** and **99,224 records**. Reconciliation: 99,224 + 1 header + 5,495 = 104,720 ✓ |
| **Validation** | Round-trip tested: the exported file re-reads with exactly 99,224 rows and its embedded newlines intact. |

> **Relevant again in Phase 4.** MySQL `LOAD DATA INFILE` must be given the
> correct `ENCLOSED BY '"'` clause or these 3,852 records will break the import.

### Q19 — Reviews answered before the order was delivered
| | |
|---|---|
| **Table / column** | `order_reviews.review_answer_timestamp` vs `orders.order_delivered_customer_date` |
| **Records affected** | **4,795** reviews (verified), 4.98% of reviews on delivered orders |
| **Decision** | New flag `review_before_delivery`, at **review grain**. NULL when the order has no delivery date. **No review removed.** Satisfaction results are reported both with all reviews and with after-arrival reviews only. |
| **Reason** | Not invalid data. It is an **analytical limitation** created by the survey process. The survey is sent the day after delivery, or about **two days after the estimated date** if the parcel hasn't arrived. 94% of these reviews belong to late orders, so late customers are often surveyed while still waiting. |
| **Why 4,795 and not 8,320** | The audit compared `review_creation_date` with the delivery time. That field is the date the survey was *sent*, stored as a date (99.91% at 00:00:00), so a survey sent on the morning of a 15:00 delivery counted as "before". 3,193 of the 8,320 were same-day cases like this. The question that matters is when the customer *answered*: `review_answer_timestamp`. |
| **Scope of impact** | Pre-arrival reviews average **1.80** stars (67% one-star) vs **4.28** after arrival. The late-delivery association weakens sharply once they are excluded: for orders 8–15 days late the average goes from 1.73 to 3.66 (n = 106). See Insights 9 and 13. |
| **Validation** | 4,795 flagged; flag equals the recomputed condition; NULL exactly where the order has no delivery date; review (review_id, order_id) pairs identical to raw. |

---

## Decisions not tied to a logged issue

| Decision | Reason |
|---|---|
| All IDs kept as **text**, never numeric | 32-character hex strings. Numeric conversion invites float rounding |
| Zip prefixes kept as **text** | `01037` as a number becomes `1037` — a different, wrong place |
| Loaded raw with `dtype=str`, converted deliberately | Stops pandas guessing a type and corrupting data before anyone looks at it |
| Conversions **fail loudly** | `to_numeric_strict` / `to_datetime_strict` raise if any value fails to parse. A silent `NaN` is how money columns get quietly corrupted |
| `is_late` computed from **unrounded** timestamps | Rounding to 2dp first reclassified **6 orders** late by under 7 minutes as on-time — a real bug caught and fixed in this project |
| Child tables aggregated to order grain **before** joining | Joining raw would fan out and double-count. Measured: +4.54% via payments, −0.47% via reviews |
| Revenue excludes freight | Per `kpi_definitions.md`. Freight reported separately as a cost metric |
| Original columns never overwritten | Every derived value goes in a new column beside its source |

---

## Summary

| | |
|---|---|
| Issues in register | **19** (all counts independently verified) |
| Issues resolved in Phase 3 | **17** (Q18 and Q19 added and treated in fix-Phase 2) |
| Rows deleted | **0** |
| Values imputed or invented | **0** |
| Original columns overwritten | **0** |
| Validation checks in the notebook | **46, all passing** |
| Rows intentionally aggregated | 981,148 geolocation readings → 19,015 zip prefixes (Q12) |
| Rows intentionally added | 2 category translations (Q03) |
