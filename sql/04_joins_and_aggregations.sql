-- =============================================================================
--  RetailPulse — 04_joins_and_aggregations.sql
--  Sections C, D, E: product, seller and delivery analysis
-- =============================================================================
--  Concepts: INNER JOIN · LEFT JOIN · multi-table joins · conditional
--            aggregation · correct grain handling · correct denominators
--
--  THE CENTRAL LESSON OF THIS FILE
--  -------------------------------
--  Every query states its grain and why its joins are safe. Two rules:
--
--  1. Never join two CHILD tables of orders directly. order_items has 112,650
--     rows and order_payments 103,886, both keyed on order_id. Joining them
--     multiplies rows. Measured in Phase 2: revenue inflates +4.54%.
--
--  2. Aggregate a child to order level FIRST (in a CTE), then join. Q15 and
--     Q17 below do exactly this.
-- =============================================================================
USE retailpulse;


-- =============================================================================
--  SECTION C — PRODUCT & CATEGORY ANALYSIS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q11. Which categories drive revenue, and how concentrated is the business?
-- -----------------------------------------------------------------------------
-- Business: where to focus merchandising and marketing spend.
-- Grain: order_items (category is a property of the product, not the order).
-- LEFT JOIN to products so that any item whose product is missing still shows
-- up rather than silently vanishing. Phase 1 proved there are no orphans, so
-- this is defensive, not corrective.
-- -----------------------------------------------------------------------------
SELECT
    p.product_category_name_english                       AS category,
    COUNT(*)                                              AS items_sold,
    COUNT(DISTINCT oi.order_id)                           AS orders,
    COUNT(DISTINCT oi.product_id)                         AS distinct_products,
    ROUND(SUM(oi.price), 2)                               AS revenue,
    ROUND(AVG(oi.price), 2)                               AS avg_price,
    ROUND(100.0 * SUM(oi.price) / SUM(SUM(oi.price)) OVER (), 2) AS pct_of_revenue
FROM order_items oi
INNER JOIN orders   o ON o.order_id   = oi.order_id
LEFT  JOIN products p ON p.product_id = oi.product_id
WHERE o.revenue_eligible = 1
GROUP BY p.product_category_name_english
ORDER BY revenue DESC
LIMIT 15;


-- -----------------------------------------------------------------------------
-- Q12. Which individual products sell best?
-- -----------------------------------------------------------------------------
-- Business: identifies hero products worth protecting stock for.
-- Grain: order_items grouped to product.
-- -----------------------------------------------------------------------------
SELECT
    oi.product_id,
    p.product_category_name_english         AS category,
    COUNT(*)                                AS times_sold,
    COUNT(DISTINCT oi.order_id)             AS distinct_orders,
    ROUND(SUM(oi.price), 2)                 AS revenue,
    ROUND(AVG(oi.price), 2)                 AS avg_price
FROM order_items oi
INNER JOIN orders   o ON o.order_id   = oi.order_id
LEFT  JOIN products p ON p.product_id = oi.product_id
WHERE o.revenue_eligible = 1
GROUP BY oi.product_id, p.product_category_name_english
ORDER BY revenue DESC
LIMIT 15;


-- -----------------------------------------------------------------------------
-- Q13. Which categories are growing and which are shrinking?
-- -----------------------------------------------------------------------------
-- Business: the single most actionable product question — where to invest and
-- where to withdraw. Compares the first and last quarter of the STABLE window.
--
-- Why the stable window matters: the dataset's edge months hold 4, 1, 16 and 4
-- orders, and November 2016 is absent entirely. Including them would show a
-- collapse that never happened.
--
-- A minimum of 50 items in each period keeps tiny categories from producing
-- meaningless percentage swings.
-- -----------------------------------------------------------------------------
WITH quarter_revenue AS (
    SELECT
        p.product_category_name_english AS category,
        SUM(CASE WHEN o.order_month BETWEEN '2017-01' AND '2017-03' THEN oi.price ELSE 0 END) AS first_q,
        SUM(CASE WHEN o.order_month BETWEEN '2018-06' AND '2018-08' THEN oi.price ELSE 0 END) AS last_q,
        SUM(CASE WHEN o.order_month BETWEEN '2017-01' AND '2017-03' THEN 1 ELSE 0 END)        AS first_q_items,
        SUM(CASE WHEN o.order_month BETWEEN '2018-06' AND '2018-08' THEN 1 ELSE 0 END)        AS last_q_items
    FROM order_items oi
    INNER JOIN orders   o ON o.order_id   = oi.order_id
    LEFT  JOIN products p ON p.product_id = oi.product_id
    WHERE o.revenue_eligible = 1
      AND o.in_stable_window = 1
    GROUP BY p.product_category_name_english
)
SELECT
    category,
    ROUND(first_q, 2)                                        AS revenue_2017_q1,
    ROUND(last_q, 2)                                         AS revenue_jun_aug_2018,  -- last 3 complete months, not calendar Q3 (renamed 2026-11-27)
    ROUND(last_q - first_q, 2)                               AS change_brl,
    ROUND(100.0 * (last_q - first_q) / NULLIF(first_q, 0), 1) AS change_pct,
    CASE
        WHEN last_q > first_q * 1.5 THEN 'Strong growth'
        WHEN last_q > first_q       THEN 'Growing'
        WHEN last_q < first_q * 0.5 THEN 'Sharp decline'
        ELSE                             'Declining'
    END                                                      AS trend
FROM quarter_revenue
WHERE first_q_items >= 50 AND last_q_items >= 50
ORDER BY change_pct DESC;


-- =============================================================================
--  SECTION D — SELLER PERFORMANCE
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q14. Who are the top sellers, and how dependent is the platform on them?
-- -----------------------------------------------------------------------------
-- Business: concentration risk. If a handful of sellers carry the marketplace,
-- losing one is a material event.
-- Grain: order_items grouped to seller.
-- CAVEAT: an order can contain items from SEVERAL sellers, so seller order
-- counts legitimately sum to more than the platform's total order count.
-- -----------------------------------------------------------------------------
SELECT
    oi.seller_id,
    s.seller_state,
    s.seller_city,
    COUNT(*)                                AS items_sold,
    COUNT(DISTINCT oi.order_id)             AS orders_served,
    ROUND(SUM(oi.price), 2)                 AS revenue,
    ROUND(AVG(oi.price), 2)                 AS avg_item_price,
    ROUND(100.0 * SUM(oi.price) / SUM(SUM(oi.price)) OVER (), 3) AS pct_of_revenue
FROM order_items oi
INNER JOIN orders  o ON o.order_id  = oi.order_id
INNER JOIN sellers s ON s.seller_id = oi.seller_id
WHERE o.revenue_eligible = 1
GROUP BY oi.seller_id, s.seller_state, s.seller_city
ORDER BY revenue DESC
LIMIT 15;


-- -----------------------------------------------------------------------------
-- Q15. Seller scorecard — revenue, delivery speed, lateness and rating
-- -----------------------------------------------------------------------------
-- Business: the actionable seller list. A high-revenue seller with a bad late
-- rate is a priority intervention; a small seller with a bad rate is noise.
--
-- WHY THE CTEs: reviews live at review grain and orders at order grain. Joining
-- order_reviews straight into this query would multiply seller rows for the 547
-- orders with more than one review. So reviews are collapsed to ONE row per
-- order first, and only then joined.
--
-- Minimum 50 orders: averages over tiny samples are unstable and would put
-- one-order sellers at the top and bottom of every ranking.
--
-- CAVEAT: the review is attached to the ORDER, not the seller. In a
-- multi-seller order every seller inherits the same score. Delivery delay is
-- likewise not wholly the seller's fault — the carrier and distance matter.
-- -----------------------------------------------------------------------------
WITH order_review AS (            -- collapse reviews to one row per order
    SELECT order_id, AVG(review_score) AS order_score
    FROM   order_reviews
    GROUP  BY order_id
),
seller_orders AS (                -- one row per (seller, order) pair
    SELECT DISTINCT oi.seller_id, oi.order_id
    FROM   order_items oi
)
SELECT
    so.seller_id,
    s.seller_state,
    COUNT(DISTINCT so.order_id)                                   AS orders,
    ROUND(SUM(oi_agg.seller_revenue), 2)                          AS revenue,
    ROUND(AVG(o.delivery_days), 1)                                AS avg_delivery_days,
    ROUND(100.0 * AVG(CASE WHEN o.delivery_measurable = 1
                           THEN o.is_late END), 2)                AS late_pct,
    ROUND(AVG(r.order_score), 2)                                  AS avg_review,
    SUM(CASE WHEN r.order_score <= 2 THEN 1 ELSE 0 END)           AS orders_rated_1_or_2
FROM seller_orders so
JOIN orders o  ON o.order_id  = so.order_id
JOIN sellers s ON s.seller_id = so.seller_id
LEFT JOIN order_review r ON r.order_id = so.order_id
JOIN (  -- revenue per (seller, order), so no double counting across sellers
        SELECT seller_id, order_id, SUM(price) AS seller_revenue
        FROM   order_items
        GROUP  BY seller_id, order_id
     ) oi_agg ON oi_agg.seller_id = so.seller_id AND oi_agg.order_id = so.order_id
WHERE o.revenue_eligible = 1
GROUP BY so.seller_id, s.seller_state
HAVING COUNT(DISTINCT so.order_id) >= 50
ORDER BY revenue DESC
LIMIT 20;


-- -----------------------------------------------------------------------------
-- Q16. Which high-volume sellers have the WORST late-delivery rate?
-- -----------------------------------------------------------------------------
-- Business: the intervention list. Sorted by late rate, not revenue, and
-- filtered to sellers big enough for the number to be meaningful.
-- -----------------------------------------------------------------------------
WITH seller_order AS (
    SELECT DISTINCT seller_id, order_id FROM order_items
)
SELECT
    so.seller_id,
    s.seller_state,
    COUNT(*)                                                      AS orders_measured,
    ROUND(100.0 * AVG(o.is_late), 2)                              AS late_pct,
    ROUND(AVG(o.delivery_days), 1)                                AS avg_delivery_days,
    ROUND(AVG(o.delay_days), 1)                                   AS avg_delay_vs_estimate
FROM seller_order so
JOIN orders  o ON o.order_id  = so.order_id
JOIN sellers s ON s.seller_id = so.seller_id
WHERE o.delivery_measurable = 1
GROUP BY so.seller_id, s.seller_state
HAVING COUNT(*) >= 100
ORDER BY late_pct DESC
LIMIT 15;


-- =============================================================================
--  SECTION E — ORDER & DELIVERY OPERATIONS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q17. On-time delivery rate, and how early orders actually arrive
-- -----------------------------------------------------------------------------
-- Business: THE key operations metric — but read the caveat.
--
-- CAVEAT WORTH MORE THAN THE METRIC: "on time" is measured against Olist's OWN
-- estimated delivery date, not an objective standard. If estimates are padded,
-- a high score reflects conservative promising rather than fast logistics.
-- Watch avg_delay_days below: a large negative number means orders arrive well
-- BEFORE the promise, which is evidence of padding.
--
-- Denominator: 96,476 orders with a real delivery date.
-- -----------------------------------------------------------------------------
SELECT
    COUNT(*)                                                      AS orders_measured,
    SUM(is_late)                                                  AS late_orders,
    SUM(1 - is_late)                                              AS on_time_orders,
    ROUND(100.0 * AVG(1 - is_late), 2)                            AS on_time_pct,
    ROUND(AVG(delay_days), 2)                                     AS avg_delay_days,
    ROUND(AVG(CASE WHEN is_late = 1 THEN delay_days END), 2)      AS avg_days_late_when_late,
    ROUND(AVG(CASE WHEN is_late = 0 THEN -delay_days END), 2)     AS avg_days_early_when_early
FROM orders
WHERE delivery_measurable = 1;


-- -----------------------------------------------------------------------------
-- Q18. Delivery performance by customer state
-- -----------------------------------------------------------------------------
-- Business: where logistics investment would pay off. Also tests whether slow
-- delivery and low revenue occur together.
-- -----------------------------------------------------------------------------
SELECT
    c.customer_state,
    COUNT(*)                                       AS delivered_orders,
    ROUND(AVG(o.delivery_days), 1)                 AS avg_delivery_days,
    ROUND(AVG(o.delay_days), 1)                    AS avg_vs_estimate,
    ROUND(100.0 * AVG(o.is_late), 2)               AS late_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.delivery_measurable = 1
GROUP BY c.customer_state
HAVING COUNT(*) >= 300
ORDER BY avg_delivery_days DESC;


-- -----------------------------------------------------------------------------
-- Q19. Freight cost analysis — what share of an order is shipping?
-- -----------------------------------------------------------------------------
-- Business: informs free-shipping thresholds and regional pricing.
-- NOTE: this is freight CHARGED to the customer, not Olist's cost. No cost
-- data exists in this dataset, so no margin conclusion can be drawn.
-- -----------------------------------------------------------------------------
SELECT
    c.customer_state,
    COUNT(*)                                                       AS item_lines,
    ROUND(SUM(oi.price), 2)                                        AS product_revenue,
    ROUND(SUM(oi.freight_value), 2)                                AS freight_charged,
    ROUND(100.0 * SUM(oi.freight_value) / SUM(oi.price), 1)        AS freight_pct_of_revenue,
    ROUND(AVG(oi.freight_value), 2)                                AS avg_freight_per_line,
    SUM(CASE WHEN oi.freight_value = 0 THEN 1 ELSE 0 END)          AS free_shipping_lines
FROM order_items oi
JOIN orders    o ON o.order_id    = oi.order_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.revenue_eligible = 1
GROUP BY c.customer_state
HAVING COUNT(*) >= 500
ORDER BY freight_pct_of_revenue DESC;


-- -----------------------------------------------------------------------------
-- Q20. Where does the time actually go between purchase and delivery?
-- -----------------------------------------------------------------------------
-- Business: identifies the real bottleneck. If the delay sits in payment
-- approval rather than shipping, the fix belongs to finance, not logistics.
-- Concepts: TIMESTAMPDIFF, multi-stage conditional aggregation, UNION ALL.
--
-- CORRECTED (data quality issue Q18). 1,350 delivered orders have a carrier
-- handoff recorded BEFORE payment approval, and 23 (Q08) a delivery before the
-- carrier handoff. Those rows produce NEGATIVE stage durations, which pulled
-- the approval->carrier average down. The original query also truncated every
-- interval to whole hours (TIMESTAMPDIFF(HOUR)).
--
-- Three rows isolate the two effects:
--   1 superseded : original method, all orders with the timestamps
--   2 precision  : same orders, second-level precision (isolates truncation)
--   3 corrected  : second-level precision, stage_timing_valid = 1 only
-- Row 3 is the figure to use. On that population the three stages add up to
-- the total exactly, so the shares are well defined.
-- -----------------------------------------------------------------------------
WITH base AS (
    SELECT *,
           TIMESTAMPDIFF(SECOND, order_purchase_timestamp,     order_approved_at)             / 86400 AS s1,
           TIMESTAMPDIFF(SECOND, order_approved_at,            order_delivered_carrier_date)  / 86400 AS s2,
           TIMESTAMPDIFF(SECOND, order_delivered_carrier_date, order_delivered_customer_date) / 86400 AS s3
    FROM orders
    WHERE delivery_measurable = 1
      AND order_approved_at            IS NOT NULL
      AND order_delivered_carrier_date IS NOT NULL
)
SELECT '1 superseded: hour-truncated, all orders' AS method,
       COUNT(*) AS orders,
       ROUND(AVG(TIMESTAMPDIFF(HOUR, order_purchase_timestamp, order_approved_at))/24, 2)            AS days_purchase_to_approval,
       ROUND(AVG(TIMESTAMPDIFF(HOUR, order_approved_at, order_delivered_carrier_date))/24, 2)        AS days_approval_to_carrier,
       ROUND(AVG(TIMESTAMPDIFF(HOUR, order_delivered_carrier_date, order_delivered_customer_date))/24, 2) AS days_carrier_to_customer,
       ROUND(AVG(delivery_days), 2) AS total_days,
       SUM(s2 < 0) + SUM(s3 < 0)   AS negative_intervals
FROM base
UNION ALL
SELECT '2 exact, all orders', COUNT(*),
       ROUND(AVG(s1), 2), ROUND(AVG(s2), 2), ROUND(AVG(s3), 2), ROUND(AVG(delivery_days), 2),
       SUM(s2 < 0) + SUM(s3 < 0)
FROM base
UNION ALL
SELECT '3 CORRECTED: exact, stage_timing_valid = 1', COUNT(*),
       ROUND(AVG(s1), 2), ROUND(AVG(s2), 2), ROUND(AVG(s3), 2), ROUND(AVG(delivery_days), 2),
       SUM(s2 < 0) + SUM(s3 < 0)
FROM base
WHERE stage_timing_valid = 1;

-- Stage shares on the corrected population (stages sum to the total exactly).
SELECT
    COUNT(*)                                          AS orders,
    ROUND(100 * SUM(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_approved_at))
              / SUM(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_delivered_customer_date)), 1) AS pct_purchase_to_approval,
    ROUND(100 * SUM(TIMESTAMPDIFF(SECOND, order_approved_at, order_delivered_carrier_date))
              / SUM(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_delivered_customer_date)), 1) AS pct_approval_to_carrier,
    ROUND(100 * SUM(TIMESTAMPDIFF(SECOND, order_delivered_carrier_date, order_delivered_customer_date))
              / SUM(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_delivered_customer_date)), 1) AS pct_carrier_to_customer
FROM orders
WHERE stage_timing_valid = 1;
