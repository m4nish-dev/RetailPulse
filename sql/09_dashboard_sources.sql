-- =============================================================================
--  RetailPulse — 09 · Dashboard (Tableau) analytical data sources (fix-Phase 3)
-- =============================================================================
--  READ-ONLY. Every statement below is a SELECT. Nothing here creates, alters
--  or drops any object, so running this file can never change the database.
--
--  Each query is introduced by a marker line:   -- @source: <name>
--  scripts/export_tableau_sources.py splits the file on those markers, runs
--  each query, and writes tableau/data/analytical/<name>.csv.
--  scripts/validate_tableau_sources.py rebuilds every source independently in
--  pandas from dataset/cleaned/ and compares.
--
--  Documentation: documentation/analytical_sources.md
--
--  Shared conventions (same as kpi_definitions.md):
--    * Revenue        = SUM(order_items.price) on revenue_eligible orders
--                       (status not canceled/unavailable). Freight excluded.
--    * Customer       = customers.customer_unique_id (a person), never customer_id.
--    * Order item row = one unit sold (Olist numbers units 1..n per order).
--    * Child tables are aggregated to the grain of the output BEFORE joining,
--      or joined through DISTINCT keys, so no row multiplies revenue or reviews.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- @source: rfm_customer_segments
-- -----------------------------------------------------------------------------
-- GRAIN   one row per person (customer_unique_id) — all 96,096 people.
--         94,983 have revenue-eligible orders with items and are scored; the
--         other 1,113 (only canceled/unavailable/item-less orders) are kept
--         with rfm_scored = 0 so the table relates 1:1 to vw_customer_summary.
-- METHOD  Same population and segment rules as sql/06 Q32 (Insight 6):
--   R  days from the dataset's last purchase (2018-10-17) to the person's last
--      ELIGIBLE purchase, calendar-day difference. Scored 1-5 by quintile.
--   F  eligible orders. ORDINAL, NOT QUINTILES: 1 order -> 1, 2 -> 3, 3+ -> 5
--      (96.9% of people have one order; quintiles would invent distinctions).
--   M  eligible revenue. Scored 1-5 by quintile.
-- TIE HANDLING (the one change from Q32)
--   Q32 used NTILE(5), which splits customers with IDENTICAL recency or spend
--   across two scores at a quintile boundary, arbitrarily. Here
--      score = 1 + FLOOR(5 * (RANK() - 1) / N)
--   so tied customers always share a score, and pandas reproduces it exactly
--   (rank(method="min")). Segment counts therefore differ slightly from Q32;
--   see documentation/analytical_sources.md §A for the reconciliation.
-- -----------------------------------------------------------------------------
WITH dataset_end AS (
    SELECT MAX(order_purchase_timestamp) AS max_ts FROM orders
),
order_revenue AS (                       -- items -> one row per order first
    SELECT order_id, SUM(price) AS revenue
    FROM order_items
    GROUP BY order_id
),
all_orders AS (                          -- every order, any status
    SELECT c.customer_unique_id,
           COUNT(*)                               AS customer_order_count,
           DATE(MIN(o.order_purchase_timestamp))  AS first_purchase_date,
           DATE(MAX(o.order_purchase_timestamp))  AS last_purchase_date
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    GROUP BY c.customer_unique_id
),
eligible AS (
    SELECT c.customer_unique_id,
           DATEDIFF((SELECT max_ts FROM dataset_end),
                    MAX(o.order_purchase_timestamp))  AS recency_days,
           COUNT(*)                                   AS frequency,
           SUM(r.revenue)                             AS monetary_value,
           DATE(MAX(o.order_purchase_timestamp))      AS last_eligible_purchase_date
    FROM orders o
    JOIN customers     c ON c.customer_id = o.customer_id
    JOIN order_revenue r ON r.order_id    = o.order_id
    WHERE o.revenue_eligible = 1
    GROUP BY c.customer_unique_id
),
ranked AS (
    SELECT e.*,
           COUNT(*) OVER ()                               AS n,
           RANK()   OVER (ORDER BY recency_days DESC)     AS r_rank,   -- oldest first
           RANK()   OVER (ORDER BY monetary_value ASC)    AS m_rank    -- smallest first
    FROM eligible e
),
scored AS (
    SELECT customer_unique_id, recency_days, frequency, monetary_value,
           last_eligible_purchase_date,
           1 + FLOOR(5 * (r_rank - 1) / n)                AS r_score,
           CASE WHEN frequency >= 3 THEN 5
                WHEN frequency  = 2 THEN 3
                ELSE 1 END                                AS f_score,
           1 + FLOOR(5 * (m_rank - 1) / n)                AS m_score
    FROM ranked
),
segmented AS (
    SELECT s.*,
           CASE
               WHEN r_score >= 4 AND f_score >= 3 AND m_score >= 4 THEN 'Champions'
               WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal Customers'
               WHEN r_score >= 4 AND f_score  = 1 AND m_score >= 3 THEN 'Potential Loyalists'
               WHEN r_score <= 2 AND m_score >= 4                  THEN 'At Risk'
               WHEN r_score <= 2                                   THEN 'Lost'
               ELSE                                                     'Needs Attention'
           END AS rfm_segment
    FROM scored s
)
SELECT a.customer_unique_id,
       a.customer_order_count,
       a.first_purchase_date,
       a.last_purchase_date,
       s.last_eligible_purchase_date,
       s.recency_days,
       COALESCE(s.frequency, 0)                          AS frequency,
       COALESCE(s.monetary_value, 0.00)                  AS monetary_value,
       s.r_score,
       s.f_score,
       s.m_score,
       CASE WHEN s.customer_unique_id IS NULL THEN NULL
            ELSE CONCAT(s.r_score, s.f_score, s.m_score) END AS rfm_code,
       COALESCE(s.rfm_segment, 'Not scored')             AS rfm_segment,
       CASE WHEN s.customer_unique_id IS NULL THEN 0 ELSE 1 END AS rfm_scored
FROM all_orders a
LEFT JOIN segmented s ON s.customer_unique_id = a.customer_unique_id
ORDER BY a.customer_unique_id;


-- -----------------------------------------------------------------------------
-- @source: cohort_retention
-- -----------------------------------------------------------------------------
-- GRAIN   one row per (cohort_month, months_since_acquisition):
--         20 cohorts (2017-01 .. 2018-08) x offsets 0..19 = 400 rows.
-- COHORT  calendar month of the person's FIRST order of any status — the same
--         definition as vw_customer_summary.cohort_month and notebook 03 §B3.
-- OFFSET  calendar-month difference (Feb vs Jan = 1), as in notebook 03 §B3.
--         NOTE: sql/06 Q33 uses TIMESTAMPDIFF(MONTH ...) — elapsed whole months
--         — which is a different definition; see analytical_sources.md §B.
-- ACTIVE  a cohort member with >= 1 order (any status) in that activity month.
-- RIGHT-CENSORING
--   The last fully observed month is 2018-08 (2018-09 and 2018-10 hold 16 and
--   4 orders: an extract boundary, not behaviour). Cells whose activity month
--   is after 2018-08 were NEVER OBSERVED: is_observed = 0 and the counts and
--   percentage are NULL, never 0, so a heatmap shows them blank.
-- -----------------------------------------------------------------------------
WITH RECURSIVE offsets AS (
    SELECT 0 AS k
    UNION ALL
    SELECT k + 1 FROM offsets WHERE k < 19
),
first_order AS (
    SELECT c.customer_unique_id,
           MIN(o.order_purchase_timestamp) AS first_ts
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    GROUP BY c.customer_unique_id
),
members AS (
    SELECT customer_unique_id,
           DATE_FORMAT(first_ts, '%Y-%m-01') AS cohort_start
    FROM first_order
    WHERE first_ts >= '2017-01-01' AND first_ts < '2018-09-01'
),
activity AS (                         -- DISTINCT: one row per person per month
    SELECT DISTINCT m.cohort_start, m.customer_unique_id,
           PERIOD_DIFF(DATE_FORMAT(o.order_purchase_timestamp, '%Y%m'),
                       DATE_FORMAT(m.cohort_start, '%Y%m'))   AS k
    FROM members m
    JOIN customers c ON c.customer_unique_id = m.customer_unique_id
    JOIN orders    o ON o.customer_id        = c.customer_id
),
cohorts AS (
    SELECT cohort_start, COUNT(*) AS cohort_customers
    FROM members
    GROUP BY cohort_start
),
active AS (
    SELECT cohort_start, k, COUNT(*) AS active_customers
    FROM activity
    GROUP BY cohort_start, k
),
grid AS (
    SELECT c.cohort_start, c.cohort_customers, f.k,
           DATE_ADD(c.cohort_start, INTERVAL f.k MONTH) AS activity_start
    FROM cohorts c
    CROSS JOIN offsets f
)
SELECT DATE_FORMAT(g.cohort_start, '%Y-%m')                      AS cohort_month,
       g.k                                                       AS months_since_acquisition,
       DATE_FORMAT(g.activity_start, '%Y-%m')                    AS activity_month,
       g.cohort_customers,
       CASE WHEN g.activity_start <= '2018-08-01' THEN 1 ELSE 0 END AS is_observed,
       PERIOD_DIFF(201808, DATE_FORMAT(g.cohort_start, '%Y%m'))  AS max_observed_offset,
       CASE WHEN g.activity_start > '2018-08-01' THEN NULL
            ELSE COALESCE(a.active_customers, 0) END             AS active_customers,
       CASE WHEN g.activity_start > '2018-08-01' OR g.k = 0 THEN NULL
            ELSE COALESCE(a.active_customers, 0) END             AS returning_customers,
       CASE WHEN g.activity_start > '2018-08-01' THEN NULL
            ELSE ROUND(100 * COALESCE(a.active_customers, 0) / g.cohort_customers, 4)
       END                                                       AS retention_pct
FROM grid g
LEFT JOIN active a ON a.cohort_start = g.cohort_start AND a.k = g.k
ORDER BY cohort_month, months_since_acquisition;


-- -----------------------------------------------------------------------------
-- @source: product_performance
-- -----------------------------------------------------------------------------
-- GRAIN   one row per product (all 32,951 products; every one appears in
--         order_items). Built from order_items directly — item grain — with no
--         payment or review join, so revenue cannot fan out.
-- Sales columns use revenue_eligible orders only. 222 products sold only on
-- canceled/unavailable orders keep a row with zero eligible sales;
-- units_all_statuses shows they did appear on an order.
-- No cost data exists: there is no profit or margin column, by design.
-- -----------------------------------------------------------------------------
SELECT p.product_id,
       p.product_category_name_english                                      AS category,
       COUNT(DISTINCT CASE WHEN o.revenue_eligible = 1 THEN oi.order_id END) AS order_count,
       SUM(CASE WHEN o.revenue_eligible = 1 THEN 1 ELSE 0 END)              AS units_sold,
       SUM(CASE WHEN o.revenue_eligible = 1 THEN oi.price ELSE 0 END)       AS product_revenue,
       ROUND(AVG(CASE WHEN o.revenue_eligible = 1 THEN oi.price END), 4)    AS avg_item_price,
       SUM(CASE WHEN o.revenue_eligible = 1 THEN oi.freight_value ELSE 0 END) AS freight_value,
       ROUND(AVG(CASE WHEN o.revenue_eligible = 1 THEN oi.freight_value END), 4) AS avg_freight_value,
       COUNT(DISTINCT CASE WHEN o.revenue_eligible = 1 THEN oi.seller_id END) AS seller_count,
       MIN(CASE WHEN o.revenue_eligible = 1 THEN o.order_date END)          AS first_sale_date,
       MAX(CASE WHEN o.revenue_eligible = 1 THEN o.order_date END)          AS last_sale_date,
       COUNT(*)                                                             AS units_all_statuses
FROM order_items oi
JOIN orders   o ON o.order_id   = oi.order_id
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_category_name_english
ORDER BY p.product_id;


-- -----------------------------------------------------------------------------
-- @source: seller_category_performance
-- -----------------------------------------------------------------------------
-- GRAIN   one row per (seller_id, category) pair with eligible sales: 6,545.
-- ADDITIVITY
--   item_count, product_revenue, freight_value  -> item grain, ADDITIVE: they
--       sum exactly to the seller and category totals.
--   order_count  -> distinct orders containing that seller's items in that
--       category. NOT additive across rows: an order with two categories, or
--       two sellers, counts once in each pair it touches.
-- DELIVERY  Delivery is recorded once per ORDER, not per seller or item. Each
--   order counts once per pair (DISTINCT order list), population
--   delivery_measurable = 1. In a multi-seller order every seller inherits the
--   order's delivery outcome; orders_shared_with_other_sellers says how often.
-- DISPATCH  approval -> carrier handoff is attributed to the seller ONLY when
--   the order has a single seller and stage_timing_valid = 1 (Q18 excluded).
-- -----------------------------------------------------------------------------
WITH items AS (
    SELECT oi.seller_id, p.product_category_name_english AS category,
           oi.order_id, oi.price, oi.freight_value
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
    JOIN orders   o ON o.order_id   = oi.order_id
    WHERE o.revenue_eligible = 1
),
order_sellers AS (
    SELECT order_id, COUNT(DISTINCT seller_id) AS n_sellers
    FROM order_items
    GROUP BY order_id
),
pair_orders AS (                       -- one row per pair per order
    SELECT DISTINCT seller_id, category, order_id FROM items
),
sales AS (
    SELECT seller_id, category,
           COUNT(DISTINCT order_id) AS order_count,
           COUNT(*)                 AS item_count,
           SUM(price)               AS product_revenue,
           SUM(freight_value)       AS freight_value
    FROM items
    GROUP BY seller_id, category
),
delivery AS (
    SELECT po.seller_id, po.category,
           SUM(CASE WHEN s.n_sellers > 1 THEN 1 ELSE 0 END)                 AS orders_shared_with_other_sellers,
           SUM(o.delivery_measurable)                                       AS delivery_measurable_orders,
           AVG(CASE WHEN o.delivery_measurable = 1 THEN o.delivery_days END) AS avg_delivery_days,
           SUM(CASE WHEN o.delivery_measurable = 1 THEN o.is_late ELSE 0 END) AS late_orders,
           SUM(CASE WHEN o.stage_timing_valid = 1 AND s.n_sellers = 1 THEN 1 ELSE 0 END) AS dispatch_measurable_orders,
           AVG(CASE WHEN o.stage_timing_valid = 1 AND s.n_sellers = 1
                    THEN TIMESTAMPDIFF(SECOND, o.order_approved_at,
                                       o.order_delivered_carrier_date) / 86400e0 END)
                                                                            AS avg_dispatch_days
    FROM pair_orders po
    JOIN orders        o ON o.order_id = po.order_id
    JOIN order_sellers s ON s.order_id = po.order_id
    GROUP BY po.seller_id, po.category
)
SELECT sa.seller_id,
       se.seller_state,
       sa.category,
       sa.order_count,
       sa.item_count,
       sa.product_revenue,
       sa.freight_value,
       d.orders_shared_with_other_sellers,
       d.delivery_measurable_orders,
       ROUND(d.avg_delivery_days, 4)                                        AS avg_delivery_days,
       d.late_orders,
       ROUND(100 * d.late_orders / NULLIF(d.delivery_measurable_orders, 0), 4) AS late_pct,
       d.dispatch_measurable_orders,
       ROUND(d.avg_dispatch_days, 6)                                        AS avg_dispatch_days
FROM sales sa
JOIN delivery d  ON d.seller_id = sa.seller_id AND d.category = sa.category
JOIN sellers  se ON se.seller_id = sa.seller_id
ORDER BY sa.seller_id, sa.category;


-- -----------------------------------------------------------------------------
-- @source: delivery_stage_orders
-- -----------------------------------------------------------------------------
-- GRAIN   one row per order with stage_timing_valid = 1 (all four timestamps
--         present and purchase <= approval <= carrier <= customer). Relates 1:1
--         to vw_order_summary on order_id.
-- Exact second differences (TIMESTAMPDIFF SECOND), converted to days with
-- floating-point division. No stage can be negative on this population, and
-- the three stages sum exactly to the total. Original timestamps untouched.
-- Shares must be computed as ratio-of-sums: SUM(stage) / SUM(total).
-- -----------------------------------------------------------------------------
SELECT o.order_id,
       o.order_month,
       o.in_stable_window,
       c.customer_state,
       TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_approved_at)              AS purchase_to_approval_seconds,
       TIMESTAMPDIFF(SECOND, o.order_approved_at, o.order_delivered_carrier_date)          AS approval_to_carrier_seconds,
       TIMESTAMPDIFF(SECOND, o.order_delivered_carrier_date, o.order_delivered_customer_date) AS carrier_to_customer_seconds,
       TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date)  AS total_seconds,
       ROUND(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_approved_at) / 86400e0, 6)              AS purchase_to_approval_days,
       ROUND(TIMESTAMPDIFF(SECOND, o.order_approved_at, o.order_delivered_carrier_date) / 86400e0, 6)          AS approval_to_carrier_days,
       ROUND(TIMESTAMPDIFF(SECOND, o.order_delivered_carrier_date, o.order_delivered_customer_date) / 86400e0, 6) AS carrier_to_customer_days,
       ROUND(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date) / 86400e0, 6)  AS total_days
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.stage_timing_valid = 1
ORDER BY o.order_id;


-- -----------------------------------------------------------------------------
-- @source: delivery_stage_summary
-- -----------------------------------------------------------------------------
-- GRAIN   one row per stage (3) plus a Total row — long format for a stacked
--         bar. Same population as delivery_stage_orders. share_pct is the
--         ratio of summed seconds, so the three shares add to 100.
-- -----------------------------------------------------------------------------
WITH s AS (
    SELECT COUNT(*) AS orders,
           SUM(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_approved_at))                 AS s1,
           SUM(TIMESTAMPDIFF(SECOND, order_approved_at, order_delivered_carrier_date))             AS s2,
           SUM(TIMESTAMPDIFF(SECOND, order_delivered_carrier_date, order_delivered_customer_date))  AS s3,
           SUM(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_delivered_customer_date))     AS tot
    FROM orders
    WHERE stage_timing_valid = 1
)
SELECT 1 AS stage_order, 'Purchase to approval' AS stage, orders,
       ROUND(s1 / orders / 86400e0, 6) AS avg_days, ROUND(100e0 * s1 / tot, 4) AS share_pct FROM s
UNION ALL
SELECT 2, 'Approval to carrier handoff', orders,
       ROUND(s2 / orders / 86400e0, 6), ROUND(100e0 * s2 / tot, 4) FROM s
UNION ALL
SELECT 3, 'Carrier handoff to customer', orders,
       ROUND(s3 / orders / 86400e0, 6), ROUND(100e0 * s3 / tot, 4) FROM s
UNION ALL
SELECT 4, 'Total', orders,
       ROUND(tot / orders / 86400e0, 6), 100.0 FROM s
ORDER BY stage_order;


-- -----------------------------------------------------------------------------
-- @source: category_satisfaction
-- -----------------------------------------------------------------------------
-- GRAIN   one row per category (74).
-- REVIEW GRAIN  A review belongs to an ORDER, identified by (review_id,
--   order_id). An order is linked to each DISTINCT category it contains, so a
--   review counts once per category it touches — never once per item.
-- MULTI-CATEGORY ORDERS  786 orders span 2+ categories; their reviews count in
--   every category they contain. Category rows are therefore NOT additive:
--   review counts summed across categories exceed the review total by exactly
--   the multi-category duplicates (reviews_from_multi_category_orders).
-- POPULATION  All order statuses (a review of a canceled order is still a
--   review). 759 reviews on orders with no items have no category and are
--   excluded.
-- REVIEW TIMING (Q19)  review_before_delivery: 1 = answered before the parcel
--   arrived, 0 = after, NULL = order never delivered. The after-arrival columns
--   use review_before_delivery = 0 only.
-- Reviews describe the whole order experience (delivery included); a category
-- score is NOT a measure of product quality alone.
-- -----------------------------------------------------------------------------
WITH order_cat AS (
    SELECT DISTINCT oi.order_id, p.product_category_name_english AS category
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
),
order_ncat AS (
    SELECT order_id, COUNT(*) AS n_categories FROM order_cat GROUP BY order_id
),
cat_items AS (
    SELECT p.product_category_name_english AS category,
           COUNT(*)                        AS item_count,
           COUNT(DISTINCT oi.order_id)     AS order_count
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
    GROUP BY p.product_category_name_english
),
cat_delivery AS (
    SELECT oc.category,
           SUM(o.delivery_measurable)                                        AS delivery_measurable_orders,
           SUM(CASE WHEN o.delivery_measurable = 1 THEN o.is_late ELSE 0 END) AS late_orders
    FROM order_cat oc
    JOIN orders o ON o.order_id = oc.order_id
    GROUP BY oc.category
),
cat_reviews AS (
    SELECT oc.category,
           COUNT(DISTINCT r.order_id)                                             AS reviewed_orders,
           COUNT(*)                                                               AS review_count,
           AVG(r.review_score)                                                    AS avg_review_score,
           100 * AVG(CASE WHEN r.review_score = 1 THEN 1 ELSE 0 END)             AS one_star_pct,
           100 * AVG(CASE WHEN r.review_score = 5 THEN 1 ELSE 0 END)             AS five_star_pct,
           SUM(CASE WHEN r.review_before_delivery = 1 THEN 1 ELSE 0 END)         AS reviews_before_delivery,
           SUM(CASE WHEN r.review_before_delivery IS NULL THEN 1 ELSE 0 END)     AS reviews_order_not_delivered,
           SUM(CASE WHEN r.review_before_delivery = 0 THEN 1 ELSE 0 END)         AS reviews_after_arrival,
           AVG(CASE WHEN r.review_before_delivery = 0 THEN r.review_score END)   AS avg_review_score_after_arrival,
           100 * AVG(CASE WHEN r.review_before_delivery = 0
                          THEN CASE WHEN r.review_score = 1 THEN 1 ELSE 0 END END) AS one_star_pct_after_arrival,
           SUM(CASE WHEN n.n_categories > 1 THEN 1 ELSE 0 END)                   AS reviews_from_multi_category_orders
    FROM order_cat oc
    JOIN order_reviews r ON r.order_id = oc.order_id
    JOIN order_ncat    n ON n.order_id = oc.order_id
    GROUP BY oc.category
)
SELECT ci.category,
       ci.order_count,
       ci.item_count,
       cr.reviewed_orders,
       cr.review_count,
       ROUND(cr.avg_review_score, 4)                                          AS avg_review_score,
       ROUND(cr.one_star_pct, 4)                                              AS one_star_pct,
       ROUND(cr.five_star_pct, 4)                                             AS five_star_pct,
       cr.reviews_before_delivery,
       ROUND(100 * cr.reviews_before_delivery / cr.review_count, 4)           AS pct_reviews_before_delivery,
       cr.reviews_order_not_delivered,
       cr.reviews_after_arrival,
       ROUND(cr.avg_review_score_after_arrival, 4)                            AS avg_review_score_after_arrival,
       ROUND(cr.one_star_pct_after_arrival, 4)                                AS one_star_pct_after_arrival,
       cr.reviews_from_multi_category_orders,
       cd.delivery_measurable_orders,
       cd.late_orders,
       ROUND(100 * cd.late_orders / NULLIF(cd.delivery_measurable_orders, 0), 4) AS late_pct
FROM cat_items ci
LEFT JOIN cat_reviews  cr ON cr.category = ci.category
LEFT JOIN cat_delivery cd ON cd.category = ci.category
ORDER BY ci.category;


-- -----------------------------------------------------------------------------
-- @source: seller_scorecard
-- -----------------------------------------------------------------------------
-- GRAIN   one row per seller with eligible sales (3,053) — same sellers as
--         vw_seller_performance, which it complements 1:1 on seller_id.
-- WHY     vw_seller_performance exposes per-seller RATES (late_pct,
--         avg_delivery_days, avg_review_score) but not the counts behind them,
--         so any cross-seller total could only average the rates — giving
--         every seller equal weight (an unweighted late rate of 8.42% against
--         the platform's 8.11%). These additive COUNTS and SUMS let the dashboard build
--         properly weighted measures:  SUM(late_orders) / SUM(delivery_measurable_orders).
-- GRAIN OF THE COUNTS  seller-order pairs: an eligible order is counted once
--   for each seller in it (1,277 eligible orders have 2+ sellers), exactly as
--   vw_seller_performance counts orders_served.
-- Reviews: one score per ORDER (mean of its reviews), inherited by every
--   seller in the order — an inherited order rating, not a seller rating.
-- -----------------------------------------------------------------------------
WITH seller_orders AS (
    SELECT DISTINCT oi.seller_id, oi.order_id
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    WHERE o.revenue_eligible = 1
),
order_score AS (                     -- exact mean: AVG() on TINYINT returns 4 dp
    SELECT order_id, SUM(review_score) / (COUNT(*) * 1e0) AS score
    FROM order_reviews
    GROUP BY order_id
)
SELECT so.seller_id,
       COUNT(*)                                                            AS orders_served,
       SUM(o.delivery_measurable)                                          AS delivery_measurable_orders,
       SUM(CASE WHEN o.delivery_measurable = 1 THEN o.is_late ELSE 0 END)  AS late_orders,
       SUM(CASE WHEN o.delivery_measurable = 1 THEN o.delivery_days ELSE 0 END) AS delivery_days_sum,
       COUNT(r.order_id)                                                   AS reviewed_orders,
       COALESCE(ROUND(SUM(r.score), 6), 0)                                 AS review_score_sum,
       SUM(CASE WHEN r.score <= 2 THEN 1 ELSE 0 END)                       AS poor_rated_orders
FROM seller_orders so
JOIN orders o           ON o.order_id = so.order_id
LEFT JOIN order_score r ON r.order_id = so.order_id
GROUP BY so.seller_id
ORDER BY so.seller_id;


-- -----------------------------------------------------------------------------
-- @source: dim_category
-- -----------------------------------------------------------------------------
-- GRAIN   one row per English category (74). The shared key that lets the
--         product, seller-category, category-satisfaction and
--         vw_category_performance tables filter together in Tableau
--         (relationships from dim_category.category to each; see tableau/data_model.md).
-- -----------------------------------------------------------------------------
SELECT p.product_category_name_english                 AS category,
       MIN(COALESCE(p.product_category_name, 'unknown')) AS category_portuguese,
       COUNT(*)                                        AS product_count
FROM products p
GROUP BY p.product_category_name_english
ORDER BY category;
