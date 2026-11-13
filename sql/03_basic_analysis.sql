-- =============================================================================
--  RetailPulse — 03_basic_analysis.sql
--  Section A (part 1): foundational SQL on the real data
-- =============================================================================
--  Concepts: SELECT · WHERE · ORDER BY · LIMIT · DISTINCT · BETWEEN · IN
--            LIKE · CASE WHEN · COUNT · SUM · AVG · MIN · MAX · GROUP BY · HAVING
--
--  A NOTE ON GRAIN, WHICH EVERY QUERY HERE RESPECTS
--  ------------------------------------------------
--  orders        = 1 row per order    (99,441)
--  order_items   = 1 row per line     (112,650) <- revenue lives here
--  order_payments= 1 row per payment  (103,886)
--  order_reviews = 1 row per review   (99,224)
--
--  Counting orders from order_items gives line counts, not order counts.
--  Summing price after joining payments inflates revenue by 4.54%.
--  Each query below states its grain.
-- =============================================================================
USE retailpulse;


-- -----------------------------------------------------------------------------
-- Q1. How many orders, and how are they distributed across statuses?
-- -----------------------------------------------------------------------------
-- Business: the first question any stakeholder asks. The status mix also shows
-- what share of demand never converts into a delivered sale.
-- Grain: orders. Safe — no joins.
-- -----------------------------------------------------------------------------
SELECT
    order_status,
    COUNT(*)                                               AS orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)     AS pct_of_all
FROM orders
GROUP BY order_status
ORDER BY orders DESC;


-- -----------------------------------------------------------------------------
-- Q2. What is total product revenue, and how much sits in orders that failed?
-- -----------------------------------------------------------------------------
-- Business: separates GMV (everything ordered) from revenue the business can
-- actually book. Conditional aggregation does both in one pass.
-- Grain: order_items. price only — freight is a separate metric, never revenue.
-- -----------------------------------------------------------------------------
SELECT
    ROUND(SUM(oi.price), 2)                                          AS gmv_all_statuses,
    ROUND(SUM(CASE WHEN o.revenue_eligible = 1 THEN oi.price END), 2) AS revenue_eligible,
    ROUND(SUM(CASE WHEN o.revenue_eligible = 0 THEN oi.price END), 2) AS revenue_lost_to_failed_orders,
    ROUND(SUM(oi.freight_value), 2)                                  AS freight_charged,
    COUNT(*)                                                         AS item_lines,
    COUNT(DISTINCT oi.order_id)                                      AS orders_with_items
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id;


-- -----------------------------------------------------------------------------
-- Q3. What is Average Order Value, and does the mean mislead?
-- -----------------------------------------------------------------------------
-- Business: AOV drives pricing, bundling and free-shipping thresholds.
-- Method: aggregate items to ORDER level first (a CTE), then average. Averaging
-- item prices directly would answer a different question (average line price).
-- Denominator = eligible orders that actually have items (98,199), not 99,441.
-- -----------------------------------------------------------------------------
WITH order_totals AS (
    SELECT oi.order_id, SUM(oi.price) AS order_revenue
    FROM   order_items oi
    JOIN   orders o ON o.order_id = oi.order_id
    WHERE  o.revenue_eligible = 1
    GROUP  BY oi.order_id
)
SELECT
    COUNT(*)                                     AS eligible_orders_with_items,
    ROUND(AVG(order_revenue), 2)                 AS average_order_value,
    ROUND(MIN(order_revenue), 2)                 AS smallest_order,
    ROUND(MAX(order_revenue), 2)                 AS largest_order,
    ROUND(STDDEV_SAMP(order_revenue), 2)         AS std_dev
FROM order_totals;


-- -----------------------------------------------------------------------------
-- Q4. How is the review score distributed?
-- -----------------------------------------------------------------------------
-- Business: the average alone hides the shape. If the distribution is J-shaped
-- the mean describes almost nobody and the 1-star group is the real target.
-- Grain: order_reviews.
-- -----------------------------------------------------------------------------
SELECT
    review_score,
    COUNT(*)                                            AS reviews,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)  AS pct,
    CASE review_score
        WHEN 5 THEN 'Delighted'
        WHEN 4 THEN 'Satisfied'
        WHEN 3 THEN 'Neutral'
        WHEN 2 THEN 'Dissatisfied'
        WHEN 1 THEN 'Angry — investigate'
    END                                                 AS interpretation
FROM order_reviews
GROUP BY review_score
ORDER BY review_score;


-- -----------------------------------------------------------------------------
-- Q5. Which payment methods do Brazilian customers actually use?
-- -----------------------------------------------------------------------------
-- Business: payment mix affects cash flow and checkout design. `boleto` is a
-- Brazilian cash/bank voucher — paid AFTER the order is placed, so it can add
-- approval lag that card payments do not.
-- Grain: order_payments. DISTINCT order count because one order = several rows.
-- -----------------------------------------------------------------------------
SELECT
    payment_type_clean                                       AS payment_type,
    COUNT(*)                                                 AS payment_rows,
    COUNT(DISTINCT order_id)                                 AS distinct_orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)       AS pct_of_payments,
    ROUND(SUM(payment_value), 2)                             AS total_paid,
    ROUND(AVG(payment_value), 2)                             AS avg_payment,
    MAX(payment_installments_clean)                          AS max_installments
FROM order_payments
GROUP BY payment_type_clean
ORDER BY payment_rows DESC;


-- -----------------------------------------------------------------------------
-- Q6. Which states generate the most orders? (top 10)
-- -----------------------------------------------------------------------------
-- Business: shows geographic concentration, which is a risk as well as a
-- strength. Demonstrates INNER JOIN on a validated 1:1 relationship.
-- Grain: orders (safe — orders→customers is strictly one-to-one).
-- -----------------------------------------------------------------------------
SELECT
    c.customer_state,
    COUNT(*)                                              AS orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)    AS pct_of_orders,
    COUNT(DISTINCT c.customer_unique_id)                  AS distinct_people
FROM orders o
INNER JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.customer_state
ORDER BY orders DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- Q7. Which orders were placed during the 2017 Black Friday window?
-- -----------------------------------------------------------------------------
-- Business: isolates a known demand spike to size it.
-- Concepts: BETWEEN on dates, DATE() extraction.
-- -----------------------------------------------------------------------------
SELECT
    DATE(o.order_purchase_timestamp)  AS purchase_date,
    COUNT(*)                          AS orders,
    ROUND(SUM(oi.price), 2)           AS product_revenue
FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_purchase_timestamp BETWEEN '2017-11-22 00:00:00'
                                     AND '2017-11-28 23:59:59'
GROUP BY DATE(o.order_purchase_timestamp)
ORDER BY purchase_date;


-- -----------------------------------------------------------------------------
-- Q8. Which product categories mention health, beauty or perfume?
-- -----------------------------------------------------------------------------
-- Business: a quick way to scope a category family without hardcoding names.
-- Concepts: DISTINCT, LIKE with wildcards, IN.
-- -----------------------------------------------------------------------------
SELECT DISTINCT
    product_category_name_english                 AS category,
    COUNT(*) OVER (PARTITION BY product_category_name_english) AS products_in_category
FROM products
WHERE product_category_name_english LIKE '%health%'
   OR product_category_name_english LIKE '%beauty%'
   OR product_category_name_english LIKE '%perfum%'
ORDER BY category;


-- -----------------------------------------------------------------------------
-- Q9. Which categories clear 500,000 BRL in eligible revenue?
-- -----------------------------------------------------------------------------
-- Business: identifies the categories large enough to matter strategically.
-- Concepts: GROUP BY with HAVING. WHERE filters rows BEFORE grouping; HAVING
-- filters groups AFTER aggregation — you cannot use SUM() in a WHERE clause.
-- -----------------------------------------------------------------------------
SELECT
    p.product_category_name_english         AS category,
    COUNT(*)                                AS items_sold,
    ROUND(SUM(oi.price), 2)                 AS revenue,
    ROUND(AVG(oi.price), 2)                 AS avg_item_price
FROM order_items oi
JOIN orders   o ON o.order_id   = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.revenue_eligible = 1
GROUP BY p.product_category_name_english
HAVING SUM(oi.price) >= 500000
ORDER BY revenue DESC;


-- -----------------------------------------------------------------------------
-- Q10. How wide is the delivery-time spread, and is the mean trustworthy?
-- -----------------------------------------------------------------------------
-- Business: a mean hides a long tail. If mean >> median, some customers are
-- having a far worse experience than the headline suggests.
-- Denominator note: 96,476 orders have a real delivery date, NOT 96,478 —
-- 8 orders are marked 'delivered' but carry no date (data issue Q01).
-- -----------------------------------------------------------------------------
SELECT
    COUNT(*)                                                   AS orders_measured,
    ROUND(AVG(delivery_days), 2)                               AS mean_days,
    ROUND(MIN(delivery_days), 2)                               AS fastest,
    ROUND(MAX(delivery_days), 2)                               AS slowest,
    SUM(CASE WHEN delivery_days <=  7 THEN 1 ELSE 0 END)       AS within_1_week,
    SUM(CASE WHEN delivery_days > 30 THEN 1 ELSE 0 END)        AS over_30_days,
    SUM(CASE WHEN delivery_days > 60 THEN 1 ELSE 0 END)        AS over_60_days
FROM orders
WHERE delivery_measurable = 1;
