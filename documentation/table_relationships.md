# Table Relationships

**Validated:** 2026-11-12 · `notebooks/01_data_exploration.ipynb` §6
All figures measured from the actual files. No relationship was assumed from a
column name.

---

## How this was tested

Two separate questions, tested separately:

1. **Is the parent's key a real primary key?** A column qualifies only if it is
   *unique across every row* **and** *never null*. Both conditions.
2. **Does every child row find a parent?** A child key with no matching parent
   is an **orphan**. Orphans break joins and make foreign keys impossible.

Cardinality (one-to-one vs one-to-many) was measured as the maximum number of
child rows per parent key, not inferred.

---

## Entity relationship overview

```
                    ┌──────────────────────────┐
                    │  customers (99,441)      │
                    │  PK customer_id          │
                    │  ── customer_unique_id   │  96,096 real people
                    └────────────┬─────────────┘
                                 │ 1:1  (exactly one order each)
                    ┌────────────▼─────────────┐
                    │  orders (99,441)         │
                    │  PK order_id             │
                    └──┬──────────┬─────────┬──┘
            1:many     │          │ 1:many  │ 1:many
       (max 21)        │          │ (max 3) │ (max 29)
    ┌──────────────────▼──┐  ┌────▼──────┐  ┌▼──────────────────┐
    │ order_items         │  │ reviews   │  │ payments          │
    │ (112,650)           │  │ (99,224)  │  │ (103,886)         │
    │ PK (order_id,       │  │ PK (review│  │ PK (order_id,     │
    │     order_item_id)  │  │ _id,      │  │  payment_         │
    └───┬─────────────┬───┘  │  order_id)│  │  sequential)      │
        │             │      └───────────┘  └───────────────────┘
 many:1 │             │ many:1
┌───────▼──────┐  ┌───▼────────────┐
│ products     │  │ sellers        │
│ (32,951)     │  │ (3,095)        │
│ PK product_id│  │ PK seller_id   │
└───────┬──────┘  └────────────────┘
        │ many:1  (13 products have NO match)
┌───────▼─────────────────────────┐
│ product_category_name_translation│
│ (71)  PK product_category_name   │
└──────────────────────────────────┘

  geolocation (1,000,163) — reference only, no enforced key,
  joins loosely on zip_code_prefix. Not used by any KPI.
```

---

## Primary key validation results

| Candidate | Rows | Distinct | Nulls | Verdict |
|---|---|---|---|---|
| `orders.order_id` | 99,441 | 99,441 | 0 | ✅ **VALID PK** |
| `customers.customer_id` | 99,441 | 99,441 | 0 | ✅ **VALID PK** |
| `customers.customer_unique_id` | 99,441 | 96,096 | 0 | ❌ Not a PK — 3,345 repeats **(by design)** |
| `order_items.order_id` | 112,650 | 98,666 | 0 | ❌ Not a PK alone |
| `order_items.(order_id, order_item_id)` | 112,650 | 112,650 | 0 | ✅ **VALID composite PK** |
| `payments.order_id` | 103,886 | 99,440 | 0 | ❌ Not a PK alone |
| `payments.(order_id, payment_sequential)` | 103,886 | 103,886 | 0 | ✅ **VALID composite PK** |
| `reviews.review_id` | 99,224 | 98,410 | 0 | ❌ **Not a PK** — 789 IDs reused ⚠ |
| `reviews.order_id` | 99,224 | 98,673 | 0 | ❌ Not a PK alone |
| `reviews.(review_id, order_id)` | 99,224 | 99,224 | 0 | ✅ Valid composite — but artificial ⚠ |
| `products.product_id` | 32,951 | 32,951 | 0 | ✅ **VALID PK** |
| `sellers.seller_id` | 3,095 | 3,095 | 0 | ✅ **VALID PK** |
| `translation.product_category_name` | 71 | 71 | 0 | ✅ **VALID PK** |

### What the failures mean

**`customer_unique_id` is *supposed* to repeat.** It identifies the person, and
3,345 of the 99,441 order-level records belong to someone who ordered before.
This "failure" is the entire basis of retention analysis.

**`reviews` has no natural key.** `review_id` repeats across *different* orders:
one survey response attached to several orders from the same purchase event.
`(review_id, order_id)` is unique but artificial. For Phase 4 the options are
that composite key or a surrogate auto-increment; the composite is used so the
schema stays honest about the source data.

---

## Foreign key validation results

| Relationship | Child rows | Orphans | Childless parents | Cardinality |
|---|---|---|---|---|
| `orders` → `customers` | 99,441 | **0** | 0 of 99,441 | **one-to-one** |
| `order_items` → `orders` | 112,650 | **0** | 775 of 99,441 | one-to-many (max 21) |
| `payments` → `orders` | 103,886 | **0** | 1 of 99,441 | one-to-many (max 29) |
| `reviews` → `orders` | 99,224 | **0** | 768 of 99,441 | one-to-many (max 3) |
| `order_items` → `products` | 112,650 | **0** | 0 of 32,951 | one-to-many (max 527) |
| `order_items` → `sellers` | 112,650 | **0** | 0 of 3,095 | one-to-many (max 2,033) |
| `products` → `translation` | 32,951 | **13** ⚠ | 0 of 71 | one-to-many (max 3,029) |

**Six of seven relationships have zero orphans.** Referential integrity this
clean is unusual in real data and means Phase 4 can declare genuine `FOREIGN
KEY` constraints in MySQL rather than working around bad references.

---

## Relationship-by-relationship notes

### `orders` → `customers` · strictly one-to-one
Every order has exactly one customer row, and every customer row has exactly one
order. This is the structural proof that `customer_id` is per-order. To reach
the person, go `orders → customers → customer_unique_id`.

### `order_items` → `orders` · one-to-many, 775 childless parents
**775 orders have no line items.** By status: `unavailable` 603, `canceled` 164,
`created` 5, `invoiced` 2, `shipped` 1. Logically correct — these orders never
completed. **Consequence:** revenue and AOV must use the 98,666 orders that have
items, not all 99,441. Using the wrong denominator understates AOV by ~0.8%.

### `payments` → `orders` · one-to-many, 1 childless parent
One order has no payment record. An order can have up to 29 payment rows
(instalments or split methods), so **joining payments to orders multiplies rows**
— aggregate payments to order level *before* joining, or revenue will be
counted several times. This is the single most common beginner error with this
dataset.

### `reviews` → `orders` · one-to-many, 768 childless parents
Coverage is 99.23%. 547 orders carry more than one review (max 3). **Always
LEFT JOIN** when attaching ratings to orders; an INNER JOIN silently drops 768
orders. For an order-level rating, aggregate first (one score per order) or the
join will duplicate order rows.

### `order_items` → `products` · one-to-many, no orphans
All 32,951 products appear in at least one order. The most-ordered product
appears on 527 lines.

### `order_items` → `sellers` · one-to-many, no orphans
All 3,095 sellers have sales. **Extreme concentration:** the busiest seller
appears on 2,033 order items. Module 4 should quantify this dependence.

### `products` → `translation` · **13 orphans** ⚠
The only broken relationship. `products` has 73 distinct categories; the
translation table has 71.

| Missing category | Products |
|---|---|
| `pc_gamer` | 3 |
| `portateis_cozinha_e_preparadores_de_alimentos` | 10 |

Plus **610 products with a NULL category** (1.85%).

**Resolution for Phase 3:** LEFT JOIN, add the two English names manually
(`pc_gamer` → `pc_gamer`; `portateis_cozinha_e_preparadores_de_alimentos` →
`portable_kitchen_food_preparers`), and label NULL categories `unknown`. Nothing
is dropped — those products carry real revenue.

### `geolocation` · deliberately unconstrained
19,015 zip prefixes against 14,994 customer and 2,246 seller prefixes, with
261,831 duplicate rows. It is reference data for map visuals only. No foreign
key will be declared, and no KPI depends on it.

---

## Rules carried into Phases 3–6

1. **Join on `customer_id`; count and segment on `customer_unique_id`.**
2. **Aggregate payments to order level before joining to orders** — 103,886 rows
   against 99,440 orders will otherwise inflate every total.
3. **Aggregate reviews to order level before joining** — 547 orders have multiple.
4. **LEFT JOIN for reviews and category translation**; INNER JOIN loses 768
   orders and 13 products respectively.
5. **Revenue lives in `order_items`, not `payments`** — only `order_items` can
   be attributed to a product, category and seller.
6. **AOV denominator = 98,666 orders with items**, not 99,441.
7. In Power BI, model this as a **star schema**: `order_items` as the central
   fact, with `orders`, `products`, `sellers` and `customers` as dimensions, and
   a dedicated date table.
