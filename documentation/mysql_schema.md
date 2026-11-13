# MySQL Schema Reference

**Database:** `retailpulse` · MySQL 8.4 LTS · InnoDB · utf8mb4
**Defined in:** [`sql/01_schema.sql`](../sql/01_schema.sql)

---

## 1. Entity relationship diagram

```
                  ┌─────────────────────────────┐
                  │ customers            99,441 │
                  │ PK customer_id              │
                  │ ── customer_unique_id ──────┼─► 96,096 real PEOPLE
                  └──────────────┬──────────────┘
                                 │ 1:1  (UNIQUE constraint)
                  ┌──────────────▼──────────────┐
                  │ orders               99,441 │
                  │ PK order_id                 │
                  │ FK customer_id  (UNIQUE)    │
                  └───┬───────────┬──────────┬──┘
          1:many      │           │ 1:many   │ 1:many
       (max 21)       │           │ (max 3)  │ (max 29)
    ┌─────────────────▼──┐  ┌─────▼───────┐  ┌▼──────────────────┐
    │ order_items 112,650│  │order_reviews│  │ order_payments    │
    │ PK (order_id,      │  │   99,224    │  │    103,886        │
    │     order_item_id) │  │ PK (review_ │  │ PK (order_id,     │
    │ FK product_id      │  │  id,order_id)│ │  payment_         │
    │ FK seller_id       │  │ FK order_id │  │  sequential)      │
    └───┬────────────┬───┘  └─────────────┘  └───────────────────┘
 many:1 │            │ many:1
┌───────▼──────┐  ┌──▼─────────────┐
│ products     │  │ sellers  3,095 │
│     32,951   │  │ PK seller_id   │
│ PK product_id│  └────────────────┘
└───────┬──────┘
        │ many:1
┌───────▼──────────────────────────────┐
│ product_category_translation  73 + 1 │
│ PK product_category_name             │
└──────────────────────────────────────┘

  geolocation  19,015   PK zip_prefix   (reference only, no FK)
```

---

## 2. Table summary

| Table | Rows | Primary key | Grain |
|---|---|---|---|
| `customers` | 99,441 | `customer_id` | one per **order-level customer record** |
| `orders` | 99,441 | `order_id` | one per **order** |
| `order_items` | 112,650 | `(order_id, order_item_id)` | one per **product line** |
| `order_payments` | 103,886 | `(order_id, payment_sequential)` | one per **payment** |
| `order_reviews` | 99,224 | `(review_id, order_id)` | one per **review record** |
| `products` | 32,951 | `product_id` | one per **product** |
| `sellers` | 3,095 | `seller_id` | one per **seller** |
| `product_category_translation` | 74 | `product_category_name` | lookup (73 loaded + 1 sentinel) |
| `geolocation` | 19,015 | `geolocation_zip_code_prefix` | one per **zip prefix** |

---

## 3. Six design decisions, and why

### 3.1 Four grains, four tables — never merged

Collapsing these into one wide table is the single most expensive mistake
available with this dataset. Measured on the real data in Phase 2:

| Approach | Revenue reported | Error |
|---|---|---|
| `SUM(price)` on `order_items` alone | 13,591,643.70 | — |
| `order_items` joined to `order_payments` | 14,209,115.34 | **+4.54%** |
| `order_items` INNER JOINed to `order_reviews` | 13,527,224.77 | **−0.47%** |

The payments join inflates because one order can have up to 29 instalment
rows, each duplicating every item line. The reviews join is subtler and more
dangerous — an INNER JOIN both duplicates (547 orders have 2–3 reviews) and
silently drops (768 orders have none), so the errors partly cancel and the
wrong number looks almost right.

`vw_order_summary` exists so nobody has to get this right by hand.

### 3.2 Money is `DECIMAL(10,2)`, never `FLOAT`

`FLOAT` is binary and cannot represent `0.10` exactly. Over 112,650 rows those
tiny errors accumulate and sums drift by cents. `DECIMAL` stores digits
exactly. This is the most common data-type mistake in financial tables, and
it is why `08_validation.sql` can assert revenue matches Python **to the
cent** rather than approximately.

### 3.3 IDs are `CHAR(32)`, not `INT`

They are fixed-length hexadecimal strings such as
`e481f51cbdc54678b7cc49136f2d6af7`. `CHAR` rather than `VARCHAR` because every
value is exactly 32 characters — `CHAR` avoids `VARCHAR`'s per-row length byte
and compares faster.

### 3.4 Zip prefixes are `CHAR(5)`, not `INT`

`'01037'` stored as a number becomes `1037` — a different, wrong place. A real
bug this schema prevents, verified in `08_validation.sql` section 12.

### 3.5 `utf8mb4` throughout

Review text is Portuguese with accented characters (ç, ã, é). MySQL's legacy
`utf8` is a 3-byte subset that mangles some characters; `utf8mb4` is true UTF-8.

### 3.6 Aggregates are NOT stored

`orders_clean.csv` carries `order_revenue`, `review_count`, `payment_total`
and similar. Those are SUMs of child tables, so storing them in `orders` would
duplicate data that can drift out of sync with its source. The views compute
them instead, so they are correct by construction.

**Row-level derived values ARE stored** (`delivery_days`, `is_late`,
`revenue_eligible`, `in_stable_window`) because they are properties of the
order itself, not aggregates, and recomputing them in every query is wasteful.

---

## 4. The three keys worth understanding

### 4.1 `customers.customer_unique_id` is deliberately NOT unique

This is the most important fact in the schema.

| Column | Distinct values | Means |
|---|---|---|
| `customer_id` | 99,441 | one per **order** |
| `customer_unique_id` | 96,096 | one per **person** |

A person who buys twice appears as two rows, two `customer_id` values, one
`customer_unique_id`. It carries a plain `INDEX`, not `UNIQUE`, and that
3,345-row repetition is the entire basis of retention analysis.

> **RULE: JOIN on `customer_id`. COUNT and SEGMENT on `customer_unique_id`.**
>
> Counting people with `customer_id` returns 99,441 and silently forces repeat
> purchase rate, retention, cohorts and RFM all to zero.

### 4.2 `orders.customer_id` carries a `UNIQUE` constraint

Not a guess. Phase 1 validated `orders → customers` as strictly one-to-one:
every order has exactly one customer row and vice versa. Declaring it `UNIQUE`
documents that in the schema and lets the optimiser use it.

### 4.3 `order_reviews.review_id` is NOT unique — composite key instead

99,224 rows hold only 98,410 distinct review ids; 789 ids appear against 2–3
**different** orders.

Phase 3 investigated before acting: of those 789 repeated ids, **zero carry
differing scores**. Each is one survey response covering several orders from a
single purchase event — so the rows are not duplicates of one another, and
`drop_duplicates(subset='review_id')` would have deleted 814 genuine
order-to-score links.

The primary key is therefore `(review_id, order_id)`, which **is** unique
across all 99,224 rows.

**A surrogate `AUTO_INCREMENT` key was considered and rejected.** It would have
been easier to join on, but it would hide the fact that `review_id` repeats.
The schema should stay honest about the source data, and anyone reading this
table should discover that quirk from the key definition rather than from a
wrong number later.

---

## 5. Foreign keys

| Child | Column | Parent | Orphans |
|---|---|---|---|
| `orders` | `customer_id` | `customers` | 0 |
| `order_items` | `order_id` | `orders` | 0 |
| `order_items` | `product_id` | `products` | 0 |
| `order_items` | `seller_id` | `sellers` | 0 |
| `order_payments` | `order_id` | `orders` | 0 |
| `order_reviews` | `order_id` | `orders` | 0 |
| `products` | `product_category_name` | `product_category_translation` | 0 |

All use `ON UPDATE CASCADE ON DELETE RESTRICT` — a parent cannot be deleted
while children reference it, which is the safe default for analytical data.

**The sentinel row.** 610 products carry the category `'unknown'` (Phase 3
issue Q04), which has no natural translation. `02_import.sql` inserts one
explicit `'unknown' → 'unknown'` row so these products can satisfy a real
foreign key instead of forcing the constraint to be dropped. The insert is
counted openly: 73 loaded from CSV + 1 sentinel = 74.

**`geolocation` has no foreign key** — customer and seller zip prefixes are
not a perfect subset of it, and no KPI depends on it, so a constraint would
add friction for no benefit.

---

## 6. Indexes

Beyond the primary keys:

| Table | Index | Why |
|---|---|---|
| `customers` | `customer_unique_id` | every retention / RFM / cohort query groups on it |
| `customers` | `customer_state`, zip | geographic analysis |
| `orders` | `order_status` | status filters and breakdowns |
| `orders` | `order_purchase_timestamp` | date-range scans |
| `orders` | `order_month` | the monthly trend grouping |
| `orders` | `revenue_eligible`, `in_stable_window` | the two filters used by nearly every analytical query |
| `order_items` | `product_id`, `seller_id` | category and seller joins |
| `order_payments` | `payment_type_clean` | payment-mix analysis |
| `order_reviews` | `order_id`, `review_score` | joining to orders; score distribution |
| `products` | both category columns | category grouping |
| `sellers` | `seller_state` | regional seller analysis |

Foreign key columns are indexed automatically by InnoDB.

---

## 7. Derived columns on `orders`

Carried over from Phase 3 cleaning. Original timestamps are never altered.

| Column | Type | Meaning |
|---|---|---|
| `order_date`, `order_month`, `order_year` | DATE / CHAR(7) / SMALLINT | calendar helpers |
| `delivery_days` | DECIMAL(10,4) | purchase → delivery, NULL if undelivered |
| `delay_days` | DECIMAL(10,4) | actual − estimated. **Negative = early** |
| `is_late` | TINYINT(1) NULL | from the **unrounded** delay; NULL where no delivery date |
| `delivery_measurable` | TINYINT(1) | has a real delivery date — **the 96,476 denominator** |
| `is_delivered` | TINYINT(1) | status = 'delivered' (96,478 — note this differs from the above by 8) |
| `revenue_eligible` | TINYINT(1) | status NOT IN ('canceled','unavailable') |
| `in_stable_window` | TINYINT(1) | purchase month within 2017-01 … 2018-08 |
| `has_date_anomaly` | TINYINT(1) | 23 orders delivered before carrier handoff (Q08) |
| `has_delivery_anomaly` | TINYINT(1) | 8 orders 'delivered' with no date (Q01) |
| `date_anomaly_note` | VARCHAR(60) | free-text reason, NULL when clean |

> **`is_delivered` (96,478) and `delivery_measurable` (96,476) differ by 8.**
> That is not an error — it is data quality issue Q01. Delivery-timing metrics
> must use `delivery_measurable`, never `is_delivered`, or the averages are
> computed over a denominator that includes rows with no value.

---

## 8. Views

Defined in [`sql/07_business_analysis.sql`](../sql/07_business_analysis.sql).
A view stores no data — it re-runs its SQL each time, so it can never go stale.

| View | Grain | Purpose |
|---|---|---|
| `vw_order_summary` | one per **order** (99,441) | the workhorse. Items, payments and reviews pre-aggregated to order level, so no consumer can cause fan-out |
| `vw_monthly_revenue` | one per **month** (25) | trend table with MoM growth, 3-month moving average, running total |
| `vw_customer_summary` | one per **person** (96,096) | retention, RFM and value analysis. Grain is `customer_unique_id` |
| `vw_category_performance` | **category × month** | category trends over time |
| `vw_seller_performance` | one per **seller** (3,095) | seller scorecard |
| `vw_delivery_performance` | **state × month** | operations dashboard |
| `vw_review_summary` | one per **review** (99,224) | satisfaction with delivery context attached |

**Power BI (Phase 6) should connect to these views, not the base tables.** The
grain logic is already correct inside them, so the model physically cannot
double-count revenue.

> Note `vw_order_summary` (order grain) versus `vw_review_summary` (review
> grain). "Average review score" from the review grain is **4.0864**; "average
> order rating" from the order grain is **4.0868**. Both are correct; they are
> different metrics and must never share a label.
