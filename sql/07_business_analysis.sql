-- =============================================================================
--  RetailPulse — 07_business_analysis.sql
--  Reusable VIEWS for Power BI (Phase 6) and ad-hoc analysis
-- =============================================================================
--  WHAT A VIEW IS, AND WHY THESE EXIST
--  -----------------------------------
--  A view is a saved query that behaves like a table. It stores no data — it
--  re-runs its SQL whenever you select from it, so it can never go stale.
--
--  Why that matters here: the hardest part of this dataset is getting the
--  GRAIN right. Every view below does the aggregation correctly ONCE, so that
--  anyone querying later — including Power BI — physically cannot make the
--  fan-out mistake that inflates revenue by 4.54%.
--
--  A view is only created where the grain and the arithmetic are provably
--  correct. 08_validation.sql checks each one against the Python reference.
-- =============================================================================
USE retailpulse;

DROP VIEW IF EXISTS vw_order_summary;
DROP VIEW IF EXISTS vw_monthly_revenue;
DROP VIEW IF EXISTS vw_customer_summary;
DROP VIEW IF EXISTS vw_category_performance;
DROP VIEW IF EXISTS vw_seller_performance;
DROP VIEW IF EXISTS vw_delivery_performance;
DROP VIEW IF EXISTS vw_review_summary;


-- =============================================================================
--  vw_order_summary — ONE ROW PER ORDER (99,441). The workhorse view.
-- =============================================================================
--  Purpose: a single safe, flat, order-grain table. Items, payments and
--  reviews are each collapsed to order level in their own subquery BEFORE
--  being joined, so no join can multiply rows.
--
--  This is the view Power BI should use for every order-level measure.
--
--  Columns:
--    order_id, customer_id, customer_unique_id   identity (count people on _unique_)
--    customer_state/city                          geography
--    order_status, revenue_eligible, is_delivered status
--    order_date/month/year, in_stable_window      calendar
--    item_count, n_sellers, order_revenue, order_freight   from order_items
--    payment_total, payment_count, max_installments        from order_payments
--    review_count, review_score_avg                        from order_reviews
--    delivery_days, delay_days, is_late, delivery_measurable
--
--  LEFT JOINs throughout: 775 orders have no items, 768 have no review and 1
--  has no payment. An INNER JOIN would silently delete them.
-- =============================================================================
CREATE VIEW vw_order_summary AS
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_state,
    c.customer_city,
    o.order_status,
    o.revenue_eligible,
    o.is_delivered,
    o.order_date,
    o.order_month,
    o.order_year,
    o.in_stable_window,
    COALESCE(i.item_count, 0)                  AS item_count,
    COALESCE(i.n_sellers, 0)                   AS n_sellers,
    COALESCE(i.order_revenue, 0.00)            AS order_revenue,   -- product only
    COALESCE(i.order_freight, 0.00)            AS order_freight,   -- kept separate
    p.payment_total,
    COALESCE(p.payment_count, 0)               AS payment_count,
    p.max_installments,
    COALESCE(r.review_count, 0)                AS review_count,
    r.review_score_avg,
    o.delivery_days,
    o.delay_days,
    o.is_late,
    o.delivery_measurable,
    o.has_date_anomaly,
    o.has_delivery_anomaly,
    o.carrier_before_approval,          -- Q18 flag
    o.stage_timing_valid                -- population for delivery-stage metrics
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN (
    SELECT order_id,
           COUNT(*)                 AS item_count,
           COUNT(DISTINCT seller_id) AS n_sellers,
           SUM(price)               AS order_revenue,
           SUM(freight_value)       AS order_freight
    FROM   order_items GROUP BY order_id
) i ON i.order_id = o.order_id
LEFT JOIN (
    SELECT order_id,
           SUM(payment_value)                AS payment_total,
           COUNT(*)                          AS payment_count,
           MAX(payment_installments_clean)   AS max_installments
    FROM   order_payments GROUP BY order_id
) p ON p.order_id = o.order_id
LEFT JOIN (
    SELECT order_id,
           COUNT(*)          AS review_count,
           AVG(review_score) AS review_score_avg
    FROM   order_reviews GROUP BY order_id
) r ON r.order_id = o.order_id;


-- =============================================================================
--  vw_monthly_revenue — ONE ROW PER MONTH (25)
-- =============================================================================
--  Purpose: the trend table for the executive dashboard, with MoM growth,
--  a 3-month moving average and a running total already computed.
--
--  `in_stable_window` is exposed as a column rather than used as a filter, so
--  a consumer can see all 25 months but filter to the trustworthy 20. The four
--  edge months hold 4, 1, 16 and 4 orders; November 2016 is absent entirely.
-- =============================================================================
CREATE VIEW vw_monthly_revenue AS
WITH monthly AS (
    SELECT
        order_month,
        MAX(in_stable_window)                                          AS in_stable_window,
        COUNT(*)                                                       AS total_orders,
        SUM(revenue_eligible)                                          AS eligible_orders,
        SUM(CASE WHEN revenue_eligible = 1 THEN order_revenue ELSE 0 END) AS revenue,
        SUM(CASE WHEN revenue_eligible = 1 THEN order_freight ELSE 0 END) AS freight,
        COUNT(DISTINCT customer_unique_id)                             AS distinct_customers,
        AVG(review_score_avg)                                          AS avg_review_score,
        AVG(delivery_days)                                             AS avg_delivery_days,
        AVG(is_late)                                                   AS late_rate
    FROM vw_order_summary
    GROUP BY order_month
)
SELECT
    order_month,
    in_stable_window,
    total_orders,
    eligible_orders,
    ROUND(revenue, 2)                                                  AS revenue,
    ROUND(freight, 2)                                                  AS freight,
    distinct_customers,
    ROUND(revenue / NULLIF(eligible_orders, 0), 2)                     AS avg_order_value,
    ROUND(LAG(revenue) OVER (ORDER BY order_month), 2)                 AS prev_month_revenue,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_month))
          / NULLIF(LAG(revenue) OVER (ORDER BY order_month), 0), 2)    AS mom_growth_pct,
    ROUND(AVG(revenue) OVER (ORDER BY order_month
                             ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS moving_avg_3m,
    ROUND(SUM(revenue) OVER (ORDER BY order_month
                             ROWS UNBOUNDED PRECEDING), 2)             AS running_total,
    ROUND(avg_review_score, 3)                                         AS avg_review_score,
    ROUND(avg_delivery_days, 2)                                        AS avg_delivery_days,
    ROUND(100.0 * late_rate, 2)                                        AS late_pct
FROM monthly;


-- =============================================================================
--  vw_customer_summary — ONE ROW PER PERSON (96,096)
-- =============================================================================
--  Purpose: the customer dimension for retention, RFM and value analysis.
--
--  ⚠ GRAIN IS customer_unique_id, THE PERSON — not customer_id. This is the
--  single most important design choice in the whole schema. Counting rows in
--  this view gives 96,096 real people, not 99,441 order records.
-- =============================================================================
CREATE VIEW vw_customer_summary AS
SELECT
    customer_unique_id,
    MIN(customer_state)                                       AS customer_state,
    COUNT(DISTINCT order_id)                                  AS total_orders,
    SUM(CASE WHEN revenue_eligible = 1 THEN order_revenue ELSE 0 END) AS historical_value,
    ROUND(SUM(CASE WHEN revenue_eligible = 1 THEN order_revenue ELSE 0 END)
          / NULLIF(SUM(revenue_eligible), 0), 2)              AS avg_order_value,
    SUM(item_count)                                           AS total_items,
    MIN(order_date)                                           AS first_order_date,
    MAX(order_date)                                           AS last_order_date,
    DATEDIFF(MAX(order_date), MIN(order_date))                AS customer_lifespan_days,
    DATE_FORMAT(MIN(order_date), '%Y-%m')                     AS cohort_month,
    CASE WHEN COUNT(DISTINCT order_id) >= 2
         THEN 1 ELSE 0 END                                    AS is_repeat_customer,
    ROUND(AVG(review_score_avg), 2)                           AS avg_review_given,
    ROUND(AVG(delivery_days), 2)                              AS avg_delivery_days,
    -- recency measured against the dataset's own end date, not today
    DATEDIFF((SELECT MAX(order_date) FROM orders), MAX(order_date)) AS recency_days
FROM vw_order_summary
GROUP BY customer_unique_id;


-- =============================================================================
--  vw_category_performance — ONE ROW PER CATEGORY PER MONTH
-- =============================================================================
--  Purpose: category trends over time for the product dashboard.
--  Grain: ITEM level aggregated to (category, month) — category belongs to the
--  product, not the order, so this cannot be built from vw_order_summary.
-- =============================================================================
CREATE VIEW vw_category_performance AS
SELECT
    p.product_category_name_english                  AS category,
    o.order_month,
    o.in_stable_window,
    COUNT(*)                                         AS items_sold,
    COUNT(DISTINCT oi.order_id)                      AS orders,
    COUNT(DISTINCT oi.product_id)                    AS distinct_products,
    COUNT(DISTINCT oi.seller_id)                     AS distinct_sellers,
    ROUND(SUM(oi.price), 2)                          AS revenue,
    ROUND(SUM(oi.freight_value), 2)                  AS freight,
    ROUND(AVG(oi.price), 2)                          AS avg_item_price
FROM order_items oi
JOIN orders   o ON o.order_id   = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.revenue_eligible = 1
GROUP BY p.product_category_name_english, o.order_month, o.in_stable_window;


-- =============================================================================
--  vw_seller_performance — ONE ROW PER SELLER (3,095)
-- =============================================================================
--  Purpose: the seller scorecard.
--
--  Two caveats baked into how this must be read:
--   1. An order can contain items from several sellers, so summing
--      orders_served across sellers exceeds the platform's total order count.
--      Revenue is computed per (seller, order) pair so it is NOT double counted.
--   2. A review attaches to the ORDER, not the seller. In a multi-seller order
--      every seller inherits the same score. Delivery delay likewise is not
--      wholly the seller's fault — carrier and distance matter.
-- =============================================================================
CREATE VIEW vw_seller_performance AS
WITH seller_order AS (
    SELECT seller_id, order_id,
           SUM(price)         AS seller_revenue,
           SUM(freight_value) AS seller_freight,
           COUNT(*)           AS items
    FROM   order_items
    GROUP  BY seller_id, order_id
)
SELECT
    so.seller_id,
    s.seller_state,
    s.seller_city,
    COUNT(DISTINCT so.order_id)                                    AS orders_served,
    SUM(so.items)                                                  AS items_sold,
    ROUND(SUM(so.seller_revenue), 2)                               AS revenue,
    ROUND(SUM(so.seller_freight), 2)                               AS freight,
    ROUND(AVG(so.seller_revenue), 2)                               AS avg_order_revenue,
    ROUND(AVG(os.delivery_days), 2)                                AS avg_delivery_days,
    ROUND(100.0 * AVG(os.is_late), 2)                              AS late_pct,
    ROUND(AVG(os.review_score_avg), 3)                             AS avg_review_score,
    SUM(CASE WHEN os.review_score_avg <= 2 THEN 1 ELSE 0 END)      AS poor_rated_orders,
    MIN(os.order_date)                                             AS first_sale,
    MAX(os.order_date)                                             AS last_sale
FROM seller_order so
JOIN sellers s          ON s.seller_id = so.seller_id
JOIN vw_order_summary os ON os.order_id = so.order_id
WHERE os.revenue_eligible = 1
GROUP BY so.seller_id, s.seller_state, s.seller_city;


-- =============================================================================
--  vw_delivery_performance — ONE ROW PER STATE PER MONTH
-- =============================================================================
--  Purpose: the operations dashboard — where and when deliveries go wrong.
--  Denominator care: only orders with a REAL delivery date are counted
--  (96,476), so the 8 'delivered'-with-no-date rows cannot skew the averages.
-- =============================================================================
CREATE VIEW vw_delivery_performance AS
SELECT
    customer_state,
    order_month,
    in_stable_window,
    COUNT(*)                                                   AS delivered_orders,
    ROUND(AVG(delivery_days), 2)                               AS avg_delivery_days,
    ROUND(MIN(delivery_days), 2)                               AS fastest_days,
    ROUND(MAX(delivery_days), 2)                               AS slowest_days,
    ROUND(AVG(delay_days), 2)                                  AS avg_delay_vs_estimate,
    SUM(is_late)                                               AS late_orders,
    ROUND(100.0 * AVG(is_late), 2)                             AS late_pct,
    ROUND(100.0 * AVG(1 - is_late), 2)                         AS on_time_pct,
    ROUND(AVG(review_score_avg), 3)                            AS avg_review_score
FROM vw_order_summary
WHERE delivery_measurable = 1
GROUP BY customer_state, order_month, in_stable_window;


-- =============================================================================
--  vw_review_summary — ONE ROW PER REVIEW RECORD (99,224), enriched
-- =============================================================================
--  Purpose: satisfaction analysis with delivery context attached.
--
--  ⚠ GRAIN IS THE REVIEW, NOT THE ORDER. 547 orders carry 2-3 reviews, so
--  counting rows here gives 99,224 reviews, not 98,673 orders. Use this view
--  for "average review score"; use vw_order_summary.review_score_avg for
--  "average order rating". They are different metrics and must never share a
--  label — review grain gives 4.0864, order grain gives 4.0868.
-- =============================================================================
CREATE VIEW vw_review_summary AS
SELECT
    r.review_id,
    r.order_id,
    r.review_score,
    CASE WHEN r.review_score >= 4 THEN 'Promoter'
         WHEN r.review_score  = 3 THEN 'Passive'
         ELSE 'Detractor' END                         AS sentiment_band,
    (r.review_comment_message IS NOT NULL)            AS has_comment,
    CHAR_LENGTH(COALESCE(r.review_comment_message,'')) AS comment_length,
    r.review_creation_date,
    TIMESTAMPDIFF(HOUR, r.review_creation_date,
                        r.review_answer_timestamp)    AS hours_to_answer,
    o.order_month,
    o.in_stable_window,
    o.customer_state,
    o.order_status,
    o.delivery_days,
    o.delay_days,
    o.is_late,
    CASE
        WHEN o.delay_days IS NULL  THEN 'not delivered'
        WHEN o.delay_days <= -15   THEN '15+ days early'
        WHEN o.delay_days <=  -7   THEN '7-15 days early'
        WHEN o.delay_days <=   0   THEN 'on time'
        WHEN o.delay_days <=   7   THEN '1-7 days late'
        WHEN o.delay_days <=  15   THEN '8-15 days late'
        ELSE                            '15+ days late'
    END                                               AS delivery_bucket,
    r.review_before_delivery                          -- Q19: answered before arrival
FROM order_reviews r
JOIN vw_order_summary o ON o.order_id = r.order_id;


-- =============================================================================
--  Confirm the views exist and report their row counts
-- =============================================================================
SELECT 'vw_order_summary'        AS view_name, COUNT(*) AS rows_returned FROM vw_order_summary
UNION ALL SELECT 'vw_monthly_revenue',      COUNT(*) FROM vw_monthly_revenue
UNION ALL SELECT 'vw_customer_summary',     COUNT(*) FROM vw_customer_summary
UNION ALL SELECT 'vw_category_performance', COUNT(*) FROM vw_category_performance
UNION ALL SELECT 'vw_seller_performance',   COUNT(*) FROM vw_seller_performance
UNION ALL SELECT 'vw_delivery_performance', COUNT(*) FROM vw_delivery_performance
UNION ALL SELECT 'vw_review_summary',       COUNT(*) FROM vw_review_summary;
