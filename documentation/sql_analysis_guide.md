# SQL Analysis Guide

How the Phase 4 SQL is organised, how to run it, and the three rules that keep
the numbers correct.

**Database:** `retailpulse` · MySQL 8.4.13 LTS
**34 queries · 7 views · 61 validation checks**

---

## 1. Run order

The files must run in this order the first time. Parents before children,
tables before views.

```bash
cd /Users/manish/Desktop/RetailPulse
MYSQL=/opt/homebrew/opt/mysql@8.4/bin/mysql

$MYSQL -u root                      < sql/01_schema.sql            # tables
$MYSQL --local-infile=1 -u root retailpulse < sql/02_import.sql    # load data
$MYSQL -u root retailpulse          < sql/07_business_analysis.sql # views
$MYSQL -u root retailpulse --table  < sql/08_validation.sql        # verify
```

After that, the analysis files can be run in any order:

```bash
$MYSQL -u root retailpulse --table < sql/03_basic_analysis.sql
$MYSQL -u root retailpulse --table < sql/04_joins_and_aggregations.sql
$MYSQL -u root retailpulse --table < sql/05_advanced_sql.sql
$MYSQL -u root retailpulse --table < sql/06_customer_analytics.sql
```

`--table` draws the ASCII result grid. Without it you get tab-separated text.

> **Tip:** add `--default-character-set=utf8mb4` when reading Portuguese review
> text, or accented characters display as `?` in the terminal. The data is
> stored correctly either way — it is a client display setting, not corruption.

---

## 2. File map

| File | Queries | Covers |
|---|---|---|
| `01_schema.sql` | — | 9 tables, keys, indexes |
| `02_import.sql` | — | `LOAD DATA LOCAL INFILE` for all 9 CSVs |
| `03_basic_analysis.sql` | Q1–Q10 | SELECT, WHERE, GROUP BY, HAVING, CASE |
| `04_joins_and_aggregations.sql` | Q11–Q20 | joins, product, seller, delivery |
| `05_advanced_sql.sql` | Q21–Q27 | CTEs, window functions, growth, ranking |
| `06_customer_analytics.sql` | Q28–Q34 | customers, RFM, cohorts, retention |
| `07_business_analysis.sql` | — | 7 reusable views |
| `08_validation.sql` | 61 checks | SQL vs the Python reference |

---

## 3. The three rules

### Rule 1 — know your grain

Four tables, four different grains. Confusing them is the main way to get a
wrong answer from this dataset.

| Table | Rows | One row = |
|---|---|---|
| `orders` | 99,441 | one order |
| `order_items` | 112,650 | one product line |
| `order_payments` | 103,886 | one payment |
| `order_reviews` | 99,224 | one review |

Counting orders from `order_items` counts *lines*, not orders. Every query in
these files states its grain in a comment.

### Rule 2 — aggregate child tables before joining

Join two children of `orders` directly and the rows multiply. **Measured on
this data, reproduced in SQL by `08_validation.sql` section 10:**

| Approach | Revenue | Error |
|---|---|---|
| `SUM(price)` on `order_items` alone | 13,591,643.70 | — |
| `order_items` joined to `order_payments` | 14,209,115.34 | **+4.54%** |
| `order_items` INNER JOINed to `order_reviews` | 13,527,224.77 | **−0.47%** |

Payments inflate because one order can carry up to 29 instalment rows, each
duplicating every item line. The reviews join is the more dangerous one: it
both duplicates (547 orders have 2–3 reviews) and silently drops (768 have
none), so the errors partly cancel and the wrong number looks almost right.

**`vw_order_summary` solves this permanently** — items, payments and reviews
are pre-aggregated to order grain inside it, so a consumer cannot fan out.

### Rule 3 — join on `customer_id`, count on `customer_unique_id`

| Column | Distinct | Means |
|---|---|---|
| `customer_id` | 99,441 | one per **order** |
| `customer_unique_id` | 96,096 | one per **person** |

Counting people with `customer_id` inflates the answer by 3.36% and forces
repeat rate, retention, cohorts and RFM all to zero, because every buyer looks
brand new. Q28 exists specifically to make this visible.

---

## 4. Standard filters

| Filter | Meaning | Use when |
|---|---|---|
| `revenue_eligible = 1` | status NOT IN ('canceled','unavailable') | any revenue figure |
| `in_stable_window = 1` | purchase month in 2017-01 … 2018-08 | any trend, growth or cohort |
| `delivery_measurable = 1` | has a real delivery date (**96,476**) | any delivery timing metric |

> **`is_delivered` (96,478) ≠ `delivery_measurable` (96,476).** Eight orders
> are marked `delivered` but carry no delivery date (issue Q01). Timing
> averages must use `delivery_measurable`, or the denominator includes rows
> with no value.

**Why the stable window:** the dataset's edge months hold 4, 1, 16 and 4
orders, and **November 2016 is absent entirely**. Charting them shows a
collapse that never happened.

---

## 5. The views

Use these rather than base tables. The grain logic is already correct inside
them.

| View | Rows | Grain |
|---|---|---|
| `vw_order_summary` | 99,441 | order — **the workhorse** |
| `vw_monthly_revenue` | 25 | month, with MoM growth and moving average |
| `vw_customer_summary` | 96,096 | **person**, not order |
| `vw_category_performance` | 1,282 | category × month |
| `vw_seller_performance` | 3,053 | seller |
| `vw_delivery_performance` | 556 | state × month |
| `vw_review_summary` | 99,224 | review |

> **`vw_seller_performance` returns 3,053, not 3,095.** The 42 missing sellers
> have no revenue-eligible orders at all — every order they touched was
> canceled or unavailable. Verified, not a bug.

> **Review grain vs order grain.** "Average review score" from
> `vw_review_summary` is **4.0864**. "Average order rating" from
> `vw_order_summary` is **4.0868**. Both are correct — 547 orders carry 2–3
> reviews, so averaging review rows weights those orders more heavily. They
> are different metrics and must never share a label.

---

## 6. SQL concepts, and where to find each

| Concept | Query |
|---|---|
| `SELECT` / `WHERE` / `ORDER BY` / `LIMIT` | Q1, Q6 |
| `DISTINCT` | Q5, Q8, Q28 |
| `BETWEEN` | Q7, Q13 |
| `IN` | Q8, Q22 |
| `LIKE` | Q8 |
| `CASE WHEN` | Q2, Q4, Q13, Q26 |
| `COUNT` / `SUM` / `AVG` / `MIN` / `MAX` | throughout |
| `GROUP BY` | throughout |
| `HAVING` | Q9, Q15, Q16, Q18 |
| `INNER JOIN` | Q6, Q9, Q11 |
| `LEFT JOIN` | Q7, Q11, Q15 |
| Multi-table joins | Q15, Q19, Q34 |
| Subqueries | Q14, Q15, Q32 |
| **CTEs** (`WITH`) | Q3, Q13, Q21–Q26, Q29–Q34 |
| `ROW_NUMBER` | Q23, Q24 |
| `RANK` / `DENSE_RANK` | Q23 |
| `LAG` / `LEAD` | Q21, Q25 |
| Running totals | Q21, Q23, Q30 |
| Moving averages | Q21, Q25 |
| `PARTITION BY` | Q8, Q24 |
| `NTILE` (quintiles) | Q32 |
| Conditional aggregation | Q2, Q13, Q22, Q33 |
| Date functions | Q7, Q20, Q22, Q31, Q33 |
| `WITH ROLLUP` | Q22 |

---

## 7. Two things to understand before reading the results

### Window functions, in plain English

`GROUP BY` collapses many rows into one. A **window function** keeps every row
and adds a column calculated across a window of related rows.

To show each month's revenue *and* the previous month's beside it, `GROUP BY`
cannot help — it would have thrown the detail away. `LAG()` looks back one row
while keeping the current one. That is the whole idea.

```sql
LAG(revenue) OVER (ORDER BY order_month)                       -- previous row
AVG(revenue) OVER (ORDER BY order_month
                   ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)   -- 3-month average
SUM(revenue) OVER (ORDER BY order_month ROWS UNBOUNDED PRECEDING) -- running total
ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC)   -- rank per group
```

### The three ranking functions differ on ties

| Function | Output on ties |
|---|---|
| `ROW_NUMBER()` | 1, 2, 3, 4 — breaks ties arbitrarily |
| `RANK()` | 1, 2, 2, 4 — ties share, then **skips** |
| `DENSE_RANK()` | 1, 2, 2, 3 — ties share, **no gap** |

Use `RANK` for "top 10 including ties", `DENSE_RANK` for distinct tiers. Q23
shows all three side by side on the same data.

---

## 8. RFM: one deliberate departure from the textbook

Q32 scores Recency and Monetary with `NTILE(5)` quintiles, as usual. **Frequency
is not scored that way**, and the reason matters:

96.88% of customers have exactly **one** order. `NTILE(5)` on a near-constant
column would split it into five arbitrary buckets and invent differences that
do not exist. Frequency is therefore a small honest ordinal:

```sql
CASE WHEN frequency >= 3 THEN 5
     WHEN frequency  = 2 THEN 3
     ELSE 1 END AS f_score
```

**State this limitation wherever RFM appears.** Pretending the F dimension is
informative here would be fabrication, and an interviewer who knows the
dataset will ask.

---

## 9. Performance

The database is ~210 MB with 569,776 rows. Typical analytical queries run in
under a second; the views take 2–3 seconds because each aggregates three child
tables.

One index was added on measured evidence rather than instinct:

```sql
INDEX idx_orders_trend (revenue_eligible, in_stable_window, order_month)
```

The monthly trend query went **0.35s → 0.21s (~40% faster)**, and `EXPLAIN`
now reports `Using index` — a covering index, so MySQL answers from the index
alone without reading the table. Column order matters: the two equality
filters first, then the `GROUP BY` column.

No other indexes were added. At this scale they would cost write time and
disk for no measurable gain.

```sql
EXPLAIN SELECT ... ;   -- check `type`, `key` and `Extra` before adding any index
```

---

## 10. Common mistakes with this database

| Mistake | Symptom | Fix |
|---|---|---|
| Joining `order_items` to `order_payments` | revenue ~4.5% too high | aggregate to order grain first, or use `vw_order_summary` |
| `COUNT(DISTINCT customer_id)` for people | 99,441 instead of 96,096 | use `customer_unique_id` |
| `INNER JOIN` to reviews | 768 orders silently vanish | `LEFT JOIN` |
| `INNER JOIN` products to translation | 13 products disappear | `LEFT JOIN`; the `unknown` sentinel exists for this |
| Using `is_delivered` for timing | denominator includes 8 dateless orders | use `delivery_measurable` |
| Charting all 25 months | apparent collapse at both ends | filter `in_stable_window = 1` |
| Full-year 2017 vs 2016 growth | +13,600%, meaningless | compare Jan–Aug only |
| Including freight in revenue | overstates by ~16.6% | revenue is `price`; freight is separate |
