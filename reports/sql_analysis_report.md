# Phase 4 — MySQL Database & SQL Analysis Report

**Date:** 2026-11-13
**Database:** `retailpulse` · MySQL 8.4.13 LTS (Homebrew, Apple Silicon)
**Status:** ✅ **PASSED** — 34/34 queries executed, 7/7 views verified, **71/71 validation checks passed**
**Updated:** 2026-11-20 — Q18/Q19 flag columns added, Q20 corrected, Q26b sensitivity added, validation §13 (+10 checks)

---

## 1. Headline

| | |
|---|---|
| MySQL version | 8.4.13 LTS, running |
| Tables created | 9 |
| Rows imported | **569,776** (+1 documented sentinel) |
| Import warnings/errors | **0** |
| Queries written and executed | **34** |
| Queries failing | **0** |
| Views created and verified | **7** |
| Validation checks | **71 PASS, 0 FAIL** |
| Revenue agreement with Python | **to the cent** |

Three independent engines — pandas (Phase 3), LibreOffice Calc (Phase 2) and
MySQL (Phase 4) — now produce the same headline numbers. Agreement across
three implementations is strong evidence the figures are right.

---

## 2. Database design

Nine tables, InnoDB, `utf8mb4`. Full reference:
[`documentation/mysql_schema.md`](../documentation/mysql_schema.md).

| Table | Rows | Primary key |
|---|---|---|
| `customers` | 99,441 | `customer_id` |
| `orders` | 99,441 | `order_id` |
| `order_items` | 112,650 | `(order_id, order_item_id)` |
| `order_payments` | 103,886 | `(order_id, payment_sequential)` |
| `order_reviews` | 99,224 | `(review_id, order_id)` |
| `products` | 32,951 | `product_id` |
| `sellers` | 3,095 | `seller_id` |
| `product_category_translation` | 74 | `product_category_name` |
| `geolocation` | 19,015 | `geolocation_zip_code_prefix` |

Seven foreign keys, zero orphans.

### Decisions worth defending

**Money is `DECIMAL(10,2)`, never `FLOAT`.** FLOAT is binary and cannot hold
`0.10` exactly; over 112,650 rows the error accumulates. This is why
validation can assert revenue matches Python *to the cent* rather than
approximately.

**IDs are `CHAR(32)`; zip prefixes are `CHAR(5)`.** `'01037'` as an integer
becomes `1037` — a different, wrong place. Verified: 23,995 zips retain a
leading zero.

**`reviews` uses a composite key, not a surrogate.** `review_id` is not unique
— 789 ids appear against 2–3 different orders. A surrogate `AUTO_INCREMENT`
would have been easier to join on but would hide that quirk. The schema stays
honest about the source data.

**`orders.customer_id` is `UNIQUE`.** Phase 1 proved that relationship is
strictly 1:1; the constraint documents it and helps the optimiser.

**Aggregates are not stored.** `orders_clean.csv` carries `order_revenue` and
`review_count`; those are SUMs of child tables and would drift out of sync.
The views compute them, so they are correct by construction.

---

## 3. Import: three real problems found and fixed

The import did **not** work first time. All three failures are recorded here
because they are the most instructive part of this phase.

### 3.1 Two review rows were silently lost

First run loaded **99,222** of 99,224 reviews. No error — just two rows gone.

Tracing them: rows 77917 and 77918, **adjacent**. Row 77918 contained
`\r\n\r\n` — a blank line inside a quoted comment. One mis-parsed row had
swallowed its neighbour.

**Cause:** MySQL defaults to `ESCAPED BY '\\'` (backslash), but Python's CSV
writer follows RFC 4180 and escapes a quote by **doubling** it (`""`), never
with a backslash. The mismatch broke parsing on that one row.

**Fix:** `ESCAPED BY ''` disables backslash escaping, so MySQL reads the file
the way Python wrote it. Result: **99,224 / 99,224**, both rows intact with
their 176-character Portuguese comment and embedded carriage returns.

> This is exactly the "silently dropping records" failure mode to watch for.
> It produced no error and would have gone unnoticed without a row-count check.

### 3.2 Eleven rows diverged from Python on NULL handling

Validation initially showed MySQL with **more** NULLs than Python: 87,658 vs
87,656 titles, 58,256 vs 58,247 messages.

Investigating: exactly **2 titles and 9 messages consist only of space
characters** — matching the discrepancy precisely.

**Cause:** `utf8mb4_unicode_ci` is a **PAD SPACE** collation, so trailing
spaces are ignored in comparison and `' ' = ''` evaluates TRUE. `NULLIF(' ','')`
therefore returns NULL, while Python keeps `' '` as a value.

**Fix:** `IF(CHAR_LENGTH(@v) = 0, NULL, @v)`, which counts characters and
ignores collation entirely. The database should not silently change data
semantics that Phase 3 decided.

### 3.3 Geolocation coordinates were being truncated

`DECIMAL(11,8)` emitted 38,030 truncation notes against source values carrying
15 decimal places.

**Fix:** `DOUBLE`. Money uses `DECIMAL` because cents must be exact;
coordinates are measurements, and `DOUBLE` holds ~15 significant digits,
matching the source exactly. Verified: `-23.550380539269455` stored intact.

### 3.4 Final import result

| Table | Loaded | Expected |
|---|---|---|
| customers | 99,441 | 99,441 ✅ |
| orders | 99,441 | 99,441 ✅ |
| order_items | 112,650 | 112,650 ✅ |
| order_payments | 103,886 | 103,886 ✅ |
| order_reviews | 99,224 | 99,224 ✅ |
| products | 32,951 | 32,951 ✅ |
| sellers | 3,095 | 3,095 ✅ |
| geolocation | 19,015 | 19,015 ✅ |
| category_translation | 74 | 73 + 1 sentinel ✅ |

**Zero warnings, zero errors on a clean run.**

**The sentinel row explained:** 610 products carry the category `'unknown'`
(Phase 3 issue Q04), which has no natural translation. `02_import.sql` inserts
one explicit `'unknown' → 'unknown'` row so those products can satisfy a real
`FOREIGN KEY` instead of forcing the constraint to be dropped. Counted openly:
73 loaded from CSV + 1 sentinel = 74.

**Other verifications:** Portuguese accents stored correctly (hex `C3A3` = ã,
10,930 rows with accents); zip leading zeros preserved (23,995 rows, smallest
`01003`); 3,852 reviews with embedded newlines round-tripped intact.

---

## 4. SQL concepts demonstrated

All executed against the real database.

**Basic:** SELECT · WHERE · ORDER BY · LIMIT · DISTINCT · BETWEEN · IN · LIKE · CASE WHEN
**Aggregation:** COUNT · SUM · AVG · MIN · MAX · STDDEV_SAMP · GROUP BY · HAVING · WITH ROLLUP
**Joins:** INNER · LEFT · multi-table · correct grain handling
**Advanced:** subqueries · CTEs · ROW_NUMBER · RANK · DENSE_RANK · LAG · LEAD ·
running totals · moving averages · PARTITION BY · tie-consistent quintiles
(RANK) · conditional aggregation · date functions (DATEDIFF, TIMESTAMPDIFF,
PERIOD_DIFF, DATE_FORMAT, MONTH)

Concept-to-query map: [`documentation/sql_analysis_guide.md`](../documentation/sql_analysis_guide.md) §6.

---

## 5. View verification

| View | Rows | Expected grain | Result |
|---|---|---|---|
| `vw_order_summary` | 99,441 | one per order | ✅ |
| `vw_monthly_revenue` | 25 | one per month | ✅ |
| `vw_customer_summary` | **96,096** | one per **person** | ✅ |
| `vw_category_performance` | 1,282 | category × month | ✅ |
| `vw_seller_performance` | 3,053 | one per seller | ✅ see note |
| `vw_delivery_performance` | 556 | state × month | ✅ |
| `vw_review_summary` | 99,224 | one per review | ✅ |

**No fan-out:** `vw_order_summary` returns exactly 99,441 rows for 99,441
distinct orders, and its revenue sums to 13,591,643.70 — identical to the item
table. The aggregation loses and invents nothing.

**`vw_seller_performance` returns 3,053, not 3,095.** Investigated: the 42
missing sellers have **no revenue-eligible orders at all** — every order they
touched was canceled or unavailable. Correct behaviour, not a bug.

---

## 6. Validation: 71 PASS, 0 FAIL

| Group | Checks | Result |
|---|---|---|
| 1. Row counts | 9 | ✅ |
| 2. Primary keys (incl. 3 composite + 2 deliberately non-unique) | 6 | ✅ |
| 3. Foreign key integrity | 7 | ✅ 0 orphans |
| 4. NULL handling | 8 | ✅ |
| 5. Data quality counts (Q01–Q14) | 6 | ✅ |
| 6. Revenue reconciliation | 5 | ✅ to the cent |
| 7. Count reconciliation | 8 | ✅ |
| 8. Delivery metrics | 4 | ✅ |
| 9. Review metrics incl. grain distinction | 3 | ✅ |
| 10. Fan-out detection | 1 | ✅ |
| 11. Duplicate detection | 3 | ✅ |
| 12. Zip leading zeros | 1 | ✅ |
| 13. Q18 / Q19 flags (added 2026-11-20) | 10 | ✅ |

### MySQL vs Python, side by side

| Metric | Python | MySQL | Match |
|---|---|---|---|
| Total orders | 99,441 | 99,441 | ✅ |
| Distinct people | 96,096 | 96,096 | ✅ |
| GMV all statuses | 13,591,643.70 | 13,591,643.70 | ✅ |
| Revenue eligible | 13,494,400.74 | 13,494,400.74 | ✅ |
| Freight | 2,251,909.54 | 2,251,909.54 | ✅ |
| AOV (eligible) | 137.42 | 137.42 | ✅ |
| Avg review (review grain) | 4.0864 | 4.0864 | ✅ |
| Avg review (order grain) | 4.0868 | 4.0868 | ✅ |
| Orders with delivery date | 96,476 | 96,476 | ✅ |
| Late deliveries | 7,827 | 7,827 | ✅ |
| On-time rate | 91.8871% | 91.8871% | ✅ |

**No Python reference was altered to force agreement.** Where SQL disagreed
(sections 3.1, 3.2), the SQL was wrong and the SQL was fixed.

### Fan-out reproduced independently in SQL

| Approach | Rows | Revenue | Error |
|---|---|---|---|
| Correct: `order_items` alone | 112,650 | 13,591,643.70 | — |
| `order_items` × `order_payments` | 117,601 | 14,209,115.34 | **+4.54%** |
| `order_items` × `order_reviews` (INNER) | 112,372 | 13,527,224.77 | **−0.47%** |

SQL reproduces Phase 2's spreadsheet measurements exactly.

---

## 7. Business findings

All from executed queries against the real database.

### 7.1 Late delivery is associated with lower satisfaction — but the "cliff" was mostly survey timing

> **Revised 2026-11-20.** The table below (Q26, all reviews) is unchanged
> arithmetic but is no longer read as a "cliff". Issue Q19 showed that 4,795
> reviews were answered before the parcel arrived. Q26b repeats the analysis
> with and without them; see the sensitivity table after this one.

Average review score by how the delivery landed against its promise (Q26,
all reviews):

| Delivery | Orders | Avg review | 1-star % | 5-star % |
|---|---|---|---|---|
| 15+ days early | 29,458 | 4.318 | 6.7% | 64.1% |
| 7–15 days early | 41,476 | 4.316 | 6.3% | 63.2% |
| On time (0–7 early) | 17,234 | 4.201 | 7.0% | 57.4% |
| **1–7 days late** | 4,409 | **3.184** | **29.5%** | 33.1% |
| **8–15 days late** | 1,918 | **1.733** | **68.5%** | 7.7% |
| 16–30 days late | 992 | 1.622 | 70.4% | 5.1% |
| 30+ days late | 343 | 2.025 | 64.1% | 13.1% |

**Q26b sensitivity** — reviews filtered at review grain
(`review_before_delivery = 0`), then averaged per order:

| Delivery vs promise | All reviews: avg / 1-star | After arrival only: orders, avg / 1-star |
|---|---|---|
| On time (0–7 early) | 4.201 / 7.0% | 17,193 · 4.202 / 7.0% |
| 1–7 days late | 3.184 / 29.5% | 3,055 · **3.860 / 11.1%** |
| 8–15 days late | 1.733 / 68.5% | 106 · **3.660 / 17.9%** |
| Over 15 days late | 1.726 / 68.8% | 19 · 2.895 / 31.6% |

Once pre-arrival reviews are removed, late orders still score lower and the
one-star share still rises with lateness, so the **association survives**. The
**magnitude does not**: 8–15 days late goes from 1.73 to 3.66. Most of the
original drop came from customers surveyed while still waiting. Beyond 7 days
late, only 106 and 19 orders remain, so those rows are indicative only.
Arriving *very* early still buys nothing over arriving moderately early
(4.318 vs 4.316).

**Action:** the 7,827 late orders remain a concentrated, addressable
satisfaction problem. Prevent the slip, and stop surveying customers whose
parcel has not arrived. These are associations, not proof that lateness
causes the lower score.

### 7.2 Delivery estimates are heavily padded — and the padding is shrinking

On-time performance is 91.89%, but orders arrive **11.18 days early on
average**. That is promise-setting, not speed.

| Month | Actual days | Promised days | Days early | On-time % |
|---|---|---|---|---|
| 2017-01 | 12.6 | **39.5** | **26.9** | 96.9% |
| 2017-02 | 13.2 | 31.8 | 18.7 | 96.8% |
| 2018-03 | 16.3 | 22.0 | 5.7 | 78.6% |
| 2018-06 | 9.2 | 27.8 | 18.5 | 98.6% |
| 2018-08 | **7.7** | **15.2** | 7.5 | 89.6% |

In January 2017 Olist promised 39.5 days and delivered in 12.6. By August 2018
it promised 15.2 and delivered in 7.7 — **actual delivery time improved 39%**
while the promise tightened 62%.

**Action:** the padding is real but narrowing. Since §7.1 shows lateness is
associated with lower ratings, the conservative promise is rational — but a 15-day quote
on a 7.7-day delivery still likely costs conversions at checkout. This is a
measurable trade-off worth testing.

### 7.3 Growth is volume, not basket size

Like-for-like January–August (the only honest comparison — 2016 holds 329
orders):

| Jan–Aug, revenue-eligible orders with items | 2017 | 2018 | Change |
|---|---|---|---|
| Revenue | 3,080,850.81 | 7,341,037.41 | **+138.3%** |
| Orders | 22,562 | 53,530 | **+137.3%** |
| AOV | 136.55 | 137.14 | **+0.4%** |

The order population matches Q22: `orders JOIN order_items` with
`revenue_eligible = 1`, i.e. the AOV denominator defined in
`kpi_definitions.md`.

Revenue more than doubled almost entirely through **more orders**, not bigger
ones. Monthly YoY growth decelerates steadily: +687% in January to **+49.4% by
August**.

**Action:** acquisition is working; basket size has never been worked on. AOV
is the untouched lever.

### 7.4 The bottleneck is last-mile carriage, not payment

Average 12.62 days from purchase to delivery on the **95,088 orders with a
valid stage sequence** (`stage_timing_valid = 1`), split:

| Stage | Days | Share |
|---|---|---|
| Purchase → payment approval | 0.40 | 3.2% |
| Approval → carrier handoff | 2.85 | 22.6% |
| **Carrier → customer** | **9.36** | **74.2%** |

**Corrected 2026-11-20.** The original Q20 used all 96,461 orders, including
1,373 with an impossible sequence (1,350 carrier-before-approval, issue Q18;
23 customer-before-carrier, Q08), and truncated stages to whole hours. It gave
0.41 / 2.78 / 9.31 days (74.1%). The finding is unchanged.

**Action:** three-quarters of delivery time sits with the carrier. Payment
approval is near-instant and seller dispatch is already fast. Logistics
investment belongs in last-mile, not internal process.

### 7.5 Only 3.12% of customers ever return

96,096 distinct people; **93,099 (96.88%) ordered exactly once**. Cohort
analysis (Q33, calendar months, corrected 2026-11-20) confirms it: the share
returning by 2018-08 runs **1.75%–4.32%** across 2017 cohorts, and lower for
2018 cohorts purely because they had less time (right-censoring). Months a
cohort could not yet reach are NULL, not 0. (The first Q33 used elapsed whole
months and reported 1.05%–3.93%.)

RFM segmentation is correspondingly skewed:

| Segment | Customers | % | Revenue share |
|---|---|---|---|
| Potential Loyalists | 21,427 | 22.6% | **33.6%** |
| At Risk | 14,792 | 15.6% | 30.7% |
| Needs Attention | 33,498 | 35.3% | 22.3% |
| Lost | 23,420 | 24.7% | 9.7% |
| **Champions** | **951** | **1.0%** | 2.3% |
| Loyal Customers | 895 | 0.9% | 1.3% |

(Q32 now uses tie-consistent quintiles, corrected 2026-11-20, and matches the
Power BI source exactly; the earlier `NTILE` run gave 22,072 / 957.)

**Champions hold just 2.3% of revenue.** A VIP retention programme has almost
nothing to work with. The 21,427 Potential Loyalists — recent, high-value,
single-purchase — carry **34% of revenue** and are the only segment large
enough to matter.

**Action:** target first-to-second purchase conversion, not loyalty rewards.

> **Methodology caveat, stated wherever RFM appears:** with 96.88% of
> customers at exactly one order, the Frequency dimension is nearly
> degenerate. It is scored as a 1/3/5 ordinal, not quintiles, because quintiles
> on a near-constant column invent differences that do not exist.

### 7.6 Repeat buyers had a measurably better first experience

| | One-time (91,994 orders) | Repeat (6,205 orders) |
|---|---|---|
| Avg order value | 138.29 | **124.47** |
| Avg delivery days | 12.57 | **12.31** |
| Late % | 8.19% | **7.03%** |
| Avg review | 4.113 | **4.167** |
| 1-star % | 10.68% | **9.75%** |

Repeat buyers experienced **14% fewer late deliveries** and gave better
ratings — consistent with §7.1. They also spend **10% less per order**, so
they are more frequent but not more valuable per transaction.

**Caveat: correlation, not causation**, and the gaps are small. It is
supporting evidence for the delivery→retention link, not proof.

### 7.7 Revenue is geographically concentrated; delivery is wildly uneven

Top 3 of 27 states hold **63.4%** of revenue (SP 38.3%, RJ 13.4%, MG 11.7%).

Delivery time ranges from **8.8 days (SP)** to **24.5 days (AL)** — a 2.8×
spread. AL also has a **23.93% late rate** against a 8.11% national average.

Freight as a share of revenue: SP 13.8%, DF 16.8%, MS 16.4%.

**Action:** the slow states are also the low-revenue states. Whether poor
logistics suppresses demand or low volume prevents logistics investment is a
genuine open question this data cannot settle — but it is testable.

### 7.8 Seller concentration is lower than expected

The largest seller holds **1.70%** of revenue; the top 15 together hold about
16%. Platform-level concentration risk is **lower** than the geographic risk
in §7.7.

But individual seller quality varies sharply. Among sellers with 100+ measured
deliveries, late rates run from under 5% to **23.14%** — a seller in Maranhão
with 389 orders. Among the top 20 by revenue, one has a **3.49 average review
across 982 orders with 251 rated 1–2 stars**.

**Action:** a named, actionable intervention list exists. `vw_seller_performance`
produces it directly.

### 7.9 Payment behaviour is distinctly Brazilian

| Method | Share | Max instalments |
|---|---|---|
| credit_card | 73.9% | **24** |
| boleto | 19.0% | 1 |
| voucher | 5.6% | 1 |
| debit_card | 1.5% | 1 |

Nearly a fifth of orders use *boleto*, a cash/bank voucher paid **after** the
order is placed. Credit card instalments run up to 24 months. **This is the
root cause of the payments fan-out** (§6) — one order, up to 29 payment rows.

---

## 8. Performance

Database ~210 MB. Typical analytical queries run in under a second; views take
2–3 seconds because each aggregates three child tables.

**One index was added, on measured evidence:**

```sql
INDEX idx_orders_trend (revenue_eligible, in_stable_window, order_month)
```

| | Before | After |
|---|---|---|
| Monthly trend query | 0.35s | **0.21s** (~40% faster) |
| `EXPLAIN` Extra | `Using where; Using temporary` | **`Using index`** |

`Using index` means a covering index — MySQL answers from the index alone
without reading the table. Column order matters: equality filters first, then
the `GROUP BY` column.

No other indexes were added. At this scale they would cost write time and disk
for no measurable gain.

---

## 9. Limitations and open issues

| Item | Status |
|---|---|
| **No profit or margin analysis** | No cost column exists anywhere. Revenue and freight only — any margin figure would be invented |
| **RFM Frequency dimension is weak** | 96.88% of customers have one order. Documented wherever RFM appears |
| **CLV is historical, not predicted** | A 3.12% repeat rate gives no basis for prediction. Labelled "historical value" throughout |
| **"On time" is self-referential** | Measured against Olist's own estimate, which §7.2 shows is padded |
| **Reviews attach to orders, not sellers** | In a multi-seller order every seller inherits the score |
| **City names unnormalised** | 4,119 variants. Geography stays state-level |
| **23 impossible date sequences** | Flagged, not fixable — cause unknowable from this data |
| **Cohort right-censoring** | Later cohorts had less time to return; not comparable with earlier ones |
| **MySQL has no root password** | Deliberate — a fresh Homebrew install. Not secured without your permission. See `mysql_setup.md` §2 |
| **Views take 2–3s** | Acceptable here; Power BI should import rather than DirectQuery |

---

## 10. Reproducibility

The whole database rebuilds from the committed SQL in about three minutes:

```bash
MYSQL=/opt/homebrew/opt/mysql@8.4/bin/mysql
$MYSQL -u root                              < sql/01_schema.sql
$MYSQL --local-infile=1 -u root retailpulse < sql/02_import.sql
$MYSQL -u root retailpulse                  < sql/07_business_analysis.sql
$MYSQL -u root retailpulse --table          < sql/08_validation.sql   # 61 PASS
```

This was executed end-to-end from scratch as the final verification step, and
returned 61 PASS / 0 FAIL.

**Prerequisite:** `dataset/cleaned/` must hold the 9 cleaned CSVs. They are
gitignored (90 MB derived artifact) — regenerate with
`notebooks/02_data_cleaning.ipynb`.

---

## 11. Verdict

| Gate | Result |
|---|---|
| MySQL 8.4 installed and running | ✅ 8.4.13 LTS |
| Database and 9 tables created | ✅ |
| All CSVs imported, counts verified | ✅ 569,776 rows, 0 warnings |
| 34 queries executed | ✅ 34 succeeded, 0 failed |
| 7 views created and grain-verified | ✅ |
| Validation vs Python | ✅ **61 PASS, 0 FAIL** |
| Revenue reconciles | ✅ to the cent |
| Raw data modified | ✅ No |
| Credentials in Git | ✅ None |

**Phase 4: PASSED.** Ready for Phase 5 — exploratory analysis and
visualisation in Python.
