# Data Dictionary

**Dataset:** Brazilian E-Commerce Public Dataset by Olist
**Source:** https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
**Profiled:** 2026-11-12 · `notebooks/01_data_exploration.ipynb`
**Total:** 9 tables · 1,551,933 rows · 52 columns

Every figure below was measured from the actual CSV files. Nothing is taken
from the dataset's public description.

**Reading the columns:**
- *Raw type* — everything is text on load, by design (see the notebook, §2).
- *Target type* — what it becomes in Phase 3 / the MySQL schema.
- *Null %* — measured, not estimated.

---

## Table index

| Table | Rows | Cols | Primary key | Role |
|---|---|---|---|---|
| `olist_orders_dataset` | 99,441 | 8 | `order_id` | Fact — one row per order |
| `olist_order_items_dataset` | 112,650 | 7 | `(order_id, order_item_id)` | Fact — one row per product per order |
| `olist_order_payments_dataset` | 103,886 | 5 | `(order_id, payment_sequential)` | Fact — one row per payment |
| `olist_order_reviews_dataset` | 99,224 | 7 | `(review_id, order_id)` ⚠ | Fact — one row per review |
| `olist_customers_dataset` | 99,441 | 5 | `customer_id` | Dimension — buyer per order |
| `olist_products_dataset` | 32,951 | 9 | `product_id` | Dimension — product attributes |
| `olist_sellers_dataset` | 3,095 | 4 | `seller_id` | Dimension — seller location |
| `product_category_name_translation` | 71 | 2 | `product_category_name` | Lookup — PT→EN category names |
| `olist_geolocation_dataset` | 1,000,163 | 5 | none (not unique) | Reference — zip → lat/lng |

⚠ `reviews` has no natural single-column key. See the warning in its section.

---

## 1. `olist_orders_dataset` — 99,441 rows

The central fact table. One row per order, with the timestamps that drive all
delivery and trend analysis.

| Column | Raw type | Target type | Nulls | Null % | Meaning |
|---|---|---|---|---|---|
| `order_id` | text | VARCHAR(32) **PK** | 0 | 0.00% | Unique order identifier. Verified unique across all 99,441 rows |
| `customer_id` | text | VARCHAR(32) **FK** | 0 | 0.00% | → `customers.customer_id`. Unique per order, **not** per person |
| `order_status` | text | VARCHAR(20) | 0 | 0.00% | One of 8 values (see below) |
| `order_purchase_timestamp` | text | DATETIME | 0 | 0.00% | When the order was placed. **The date used for all trend analysis** |
| `order_approved_at` | text | DATETIME | 160 | 0.16% | Payment approval time |
| `order_delivered_carrier_date` | text | DATETIME | 1,783 | 1.79% | Handed to the logistics partner |
| `order_delivered_customer_date` | text | DATETIME | 2,965 | 2.98% | **Actual** delivery to customer |
| `order_estimated_delivery_date` | text | DATETIME | 0 | 0.00% | **Promised** delivery date, set at purchase |

**`order_status` values (measured):**

| Status | Orders | % | Has delivery date? |
|---|---|---|---|
| `delivered` | 96,478 | 97.02% | Yes — except 8 rows (defect Q01) |
| `shipped` | 1,107 | 1.11% | No — in transit |
| `canceled` | 625 | 0.63% | 6 of 625 do |
| `unavailable` | 609 | 0.61% | No |
| `invoiced` | 314 | 0.32% | No |
| `processing` | 301 | 0.30% | No |
| `created` | 5 | 0.01% | No |
| `approved` | 2 | 0.00% | No |

**Date coverage:** 2016-09-04 → 2018-10-17 (772 days, 25 months). Four months
are effectively empty (2016-09: 4 orders, 2016-12: 1, 2018-09: 16, 2018-10: 4).
**Stable analysis window: 2017-01 → 2018-08** (20 months, 99,092 orders, 99.65%).

**Derived columns to create in Phase 3:**
`delivery_days` = delivered − purchase · `delay_days` = delivered − estimated ·
`is_late` = delay_days > 0 · `order_month` = purchase truncated to month

---

## 2. `olist_order_items_dataset` — 112,650 rows

One row per **product line within an order**. An order with 3 products has 3
rows here. **This is the revenue table.**

| Column | Raw type | Target type | Nulls | Meaning |
|---|---|---|---|---|
| `order_id` | text | VARCHAR(32) **PK/FK** | 0 | → `orders.order_id`. 98,666 distinct |
| `order_item_id` | text | TINYINT **PK** | 0 | Line number within the order, 1–21 |
| `product_id` | text | VARCHAR(32) **FK** | 0 | → `products.product_id`. All 32,951 products appear |
| `seller_id` | text | VARCHAR(32) **FK** | 0 | → `sellers.seller_id`. All 3,095 sellers appear |
| `shipping_limit_date` | text | DATETIME | 0 | Seller's shipping deadline |
| `price` | text | DECIMAL(10,2) | 0 | **Product price for this line.** 0.85–6,735.00, mean 120.65 |
| `freight_value` | text | DECIMAL(10,2) | 0 | Shipping cost for this line. 0.00–409.68, mean 19.99. 383 rows are 0 |

**Totals:** `SUM(price)` = **13,591,643.70** · `SUM(freight_value)` = **2,251,909.54**

**Important:** 775 orders have **no row here** (mostly `unavailable`/`canceled`).
They cannot contribute revenue and must be excluded from the AOV denominator.

---

## 3. `olist_order_payments_dataset` — 103,886 rows

One row per payment. An order can have several (instalments, split methods).

| Column | Raw type | Target type | Nulls | Meaning |
|---|---|---|---|---|
| `order_id` | text | VARCHAR(32) **PK/FK** | 0 | → `orders.order_id`. 99,440 distinct — one order has no payment |
| `payment_sequential` | text | TINYINT **PK** | 0 | Payment number within the order, 1–29 |
| `payment_type` | text | VARCHAR(20) | 0 | 5 values (below) |
| `payment_installments` | text | TINYINT | 0 | 0–24. **2 rows report 0**, not a valid count (defect Q10) |
| `payment_value` | text | DECIMAL(10,2) | 0 | Amount paid. 0.00–13,664.08. **9 rows are 0** (defect Q09) |

**`payment_type` values:** `credit_card` 76,795 (73.92%) · `boleto` 19,784
(19.04%) · `voucher` 5,775 (5.56%) · `debit_card` 1,529 (1.47%) ·
`not_defined` 3 (0.00%, defect Q11).

> *Boleto* is a Brazilian cash/bank voucher — the customer gets a slip and pays
> at a bank or online. At 19% of payments it matters: boleto orders are paid
> after the order is placed, which can add approval lag.

**`SUM(payment_value)` = 16,008,872.12**, which is **not** the project's revenue
figure — see `kpi_definitions.md`.

---

## 4. `olist_order_reviews_dataset` — 99,224 rows

> ### ⚠ Two traps in this table
> **1. `review_id` is NOT unique.** 99,224 rows hold only 98,410 distinct
> review IDs: 789 IDs appear on 2–3 different orders. One survey response is
> attached to several orders from the same purchase event. Only
> `(review_id, order_id)` together is unique.
>
> **2. Row count ≠ line count.** 3,852 reviews contain newlines inside the
> comment text, so the file has 104,720 physical lines but **99,224 records**.
> `wc -l` gives the wrong answer; always use a real CSV parser.

| Column | Raw type | Target type | Nulls | Null % | Meaning |
|---|---|---|---|---|---|
| `review_id` | text | VARCHAR(32) **PK** | 0 | 0.00% | Review identifier — **not unique** |
| `order_id` | text | VARCHAR(32) **PK/FK** | 0 | 0.00% | → `orders.order_id`. 98,673 distinct; 547 orders have >1 review |
| `review_score` | text | TINYINT | 0 | 0.00% | 1–5 stars |
| `review_comment_title` | text | VARCHAR(255) | 87,656 | 88.34% | Optional title, Portuguese |
| `review_comment_message` | text | TEXT | 58,247 | 58.70% | Optional body, Portuguese |
| `review_creation_date` | text | DATETIME | 0 | 0.00% | Survey sent (date only, time always 00:00:00) |
| `review_answer_timestamp` | text | DATETIME | 0 | 0.00% | Customer responded |

**Score distribution:** 5★ 57,328 (57.78%) · 4★ 19,142 (19.29%) ·
3★ 8,179 (8.24%) · 2★ 3,151 (3.18%) · 1★ 11,424 (11.51%). **Mean 4.0864.**

The distribution is J-shaped, not bell-shaped — the mean describes almost nobody.
**Coverage:** 98,673 of 99,441 orders (99.23%); 768 orders have no review.
The high null rates on the two text columns are **not defects** — comments are
optional.

---

## 5. `olist_customers_dataset` — 99,441 rows

> ### ⚠ The most important detail in the entire dataset
> This table has **two** ID columns and they mean different things:
>
> - **`customer_id`** — unique per **order**. 99,441 distinct. A person who
>   buys twice gets two different values.
> - **`customer_unique_id`** — the actual **person**. 96,096 distinct.
>
> Counting customers with `customer_id` makes every buyer look brand new, which
> silently destroys repeat-purchase rate, retention, cohort analysis and RFM.
>
> **Project rule: JOIN on `customer_id`, COUNT and SEGMENT on `customer_unique_id`.**

| Column | Raw type | Target type | Nulls | Meaning |
|---|---|---|---|---|
| `customer_id` | text | VARCHAR(32) **PK** | 0 | Per-order key → `orders.customer_id`. 1:1 with orders |
| `customer_unique_id` | text | VARCHAR(32) | 0 | **The person.** 96,096 distinct |
| `customer_zip_code_prefix` | text | CHAR(5) | 0 | First 5 digits of zip. 14,994 distinct. **Keep as text** — leading zeros |
| `customer_city` | text | VARCHAR(50) | 0 | 4,119 distinct, lowercase, unnormalised |
| `customer_state` | text | CHAR(2) | 0 | 27 Brazilian states |

**Repeat behaviour (measured):** 93,099 people ordered once (96.88%); 2,745
ordered twice; 203 three times; 48 four or more; maximum 17.
**Only 3.12% of customers ever ordered again** — this constrains Module 2 and is
discussed in `methodology.md`.

---

## 6. `olist_products_dataset` — 32,951 rows

| Column | Raw type | Target type | Nulls | Null % | Meaning |
|---|---|---|---|---|---|
| `product_id` | text | VARCHAR(32) **PK** | 0 | 0.00% | Verified unique |
| `product_category_name` | text | VARCHAR(60) **FK** | 610 | 1.85% | Portuguese category. **73 distinct, but only 71 translate** |
| `product_name_lenght` | text | SMALLINT | 610 | 1.85% | Characters in the product name. **Misspelled in source** |
| `product_description_lenght` | text | SMALLINT | 610 | 1.85% | Characters in the description. **Misspelled in source** |
| `product_photos_qty` | text | SMALLINT | 610 | 1.85% | Number of listing photos |
| `product_weight_g` | text | INT | 2 | 0.01% | Weight in grams |
| `product_length_cm` | text | SMALLINT | 2 | 0.01% | Length |
| `product_height_cm` | text | SMALLINT | 2 | 0.01% | Height |
| `product_width_cm` | text | SMALLINT | 2 | 0.01% | Width |

**Note the source misspellings** `lenght` (should be `length`) on two columns.
Load with the original names; rename in the cleaned output and document it.

**No cost or margin column exists** — this is why the project reports revenue
only and never profit.

The same 610 rows are null across the four listing-attribute columns, which
suggests products created without full catalogue data rather than random loss.

---

## 7. `olist_sellers_dataset` — 3,095 rows

| Column | Raw type | Target type | Nulls | Meaning |
|---|---|---|---|---|
| `seller_id` | text | VARCHAR(32) **PK** | 0 | Verified unique |
| `seller_zip_code_prefix` | text | CHAR(5) | 0 | 2,246 distinct. Keep as text |
| `seller_city` | text | VARCHAR(50) | 0 | 611 distinct |
| `seller_state` | text | CHAR(2) | 0 | 23 states (4 fewer than customers) |

Every seller appears in `order_items`. Concentration is extreme: the busiest
seller appears on 2,033 order items.

---

## 8. `product_category_name_translation` — 71 rows

| Column | Raw type | Target type | Nulls | Meaning |
|---|---|---|---|---|
| `product_category_name` | text | VARCHAR(60) **PK** | 0 | Portuguese name |
| `product_category_name_english` | text | VARCHAR(60) | 0 | English name |

> ### ⚠ Two encoding and coverage traps
> **1. UTF-8 BOM.** This is the only file with a byte-order mark. Read without
> `encoding='utf-8-sig'`, the first column name becomes
> `'﻿product_category_name'` and **every join silently returns nothing** —
> no error, just empty category names.
>
> **2. Incomplete coverage.** `products` contains 73 distinct categories; this
> table has 71. Missing: **`pc_gamer`** (3 products) and
> **`portateis_cozinha_e_preparadores_de_alimentos`** (10 products). An INNER
> JOIN drops those 13 products. Use LEFT JOIN and supply the two names manually.

---

## 9. `olist_geolocation_dataset` — 1,000,163 rows

Reference data only. No business KPI depends on it.

| Column | Raw type | Target type | Nulls | Meaning |
|---|---|---|---|---|
| `geolocation_zip_code_prefix` | text | CHAR(5) | 0 | 19,015 distinct |
| `geolocation_lat` | text | DECIMAL(10,8) | 0 | Latitude |
| `geolocation_lng` | text | DECIMAL(11,8) | 0 | Longitude |
| `geolocation_city` | text | VARCHAR(50) | 0 | 8,011 distinct — less clean than `customers.customer_city` |
| `geolocation_state` | text | CHAR(2) | 0 | 27 states |

**261,831 exact duplicate rows (26.2%)** — expected, not corruption: a zip
prefix covers an area, so many coordinate readings share one prefix (up to
1,146 rows for a single prefix). Aggregate to one point per prefix before
using it for maps.

---

## Cross-table notes

**Zip codes must stay text.** `01037` read as a number becomes `1037`. All four
zip columns are `CHAR(5)`.

**IDs are 32-character hexadecimal strings**, not integers. `VARCHAR(32)`.

**All money is Brazilian Real (BRL)**, 2016–2018. No currency column exists and
no conversion is applied.

**All timestamps are `YYYY-MM-DD HH:MM:SS`** with no timezone. Zero parse
failures across all 9 date columns. Assumed Brazil local time.
