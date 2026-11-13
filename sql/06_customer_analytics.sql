-- =============================================================================
--  RetailPulse — 06_customer_analytics.sql
--  Section B: customers, RFM, cohorts and retention
-- =============================================================================
--  THE RULE THAT GOVERNS EVERY QUERY IN THIS FILE
--  ----------------------------------------------
--      JOIN on customer_id.  COUNT and SEGMENT on customer_unique_id.
--
--  customer_id        is unique per ORDER  — 99,441 values
--  customer_unique_id identifies the PERSON — 96,096 values
--
--  Counting people with customer_id returns 99,441 and silently forces repeat
--  purchase rate, retention, cohorts and RFM all to zero, because every buyer
--  looks brand new. Most published versions of this project get this wrong.
--
--  AN HONEST WARNING BEFORE YOU READ THE RESULTS
--  ---------------------------------------------
--  Only about 3% of customers in this dataset ever place a second order. That
--  is a real property of the marketplace, not a bug and not something to write
--  around. It means:
--    * retention curves will be very low and very flat — that IS the finding
--    * RFM's Frequency dimension is nearly degenerate (see Q32)
--    * "lifetime value" here is HISTORICAL value, never a prediction
--  Nothing in this file inflates those numbers to look more impressive.
-- =============================================================================
USE retailpulse;


-- -----------------------------------------------------------------------------
-- Q28. How many customers are there really? (and why the answer is not 99,441)
-- -----------------------------------------------------------------------------
-- Business: the denominator for every per-customer metric in the project.
-- This query exists to make the customer_id / customer_unique_id trap visible.
-- -----------------------------------------------------------------------------
SELECT
    COUNT(*)                                                       AS customer_rows,
    COUNT(DISTINCT customer_id)                                    AS distinct_customer_id,
    COUNT(DISTINCT customer_unique_id)                             AS distinct_people,
    COUNT(DISTINCT customer_id) - COUNT(DISTINCT customer_unique_id) AS repeat_order_records,
    ROUND(100.0 * (COUNT(DISTINCT customer_id) - COUNT(DISTINCT customer_unique_id))
          / COUNT(DISTINCT customer_id), 2)                        AS pct_inflation_if_wrong_column
FROM customers;


-- -----------------------------------------------------------------------------
-- Q29. New vs returning customers, and the repeat purchase rate
-- -----------------------------------------------------------------------------
-- Business: the core loyalty metric, and a strategic fork. A marketplace that
-- cannot retain customers must either fix retention or accept a pure
-- acquisition model — the number forces that conversation.
-- -----------------------------------------------------------------------------
WITH per_person AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS order_count
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    GROUP BY c.customer_unique_id
)
SELECT
    COUNT(*)                                                          AS total_people,
    SUM(CASE WHEN order_count  = 1 THEN 1 ELSE 0 END)                 AS one_time_buyers,
    SUM(CASE WHEN order_count >= 2 THEN 1 ELSE 0 END)                 AS repeat_buyers,
    ROUND(100.0 * SUM(CASE WHEN order_count >= 2 THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                              AS repeat_purchase_rate_pct,
    ROUND(AVG(order_count), 4)                                        AS avg_orders_per_person,
    MAX(order_count)                                                  AS most_orders_by_one_person
FROM per_person;


-- -----------------------------------------------------------------------------
-- Q30. Distribution of orders per person
-- -----------------------------------------------------------------------------
-- Business: the mean (just above 1.0) is useless here. The distribution is the
-- real answer and shows exactly how thin the repeat segment is.
-- -----------------------------------------------------------------------------
WITH per_person AS (
    SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count
    FROM   orders o
    JOIN   customers c ON c.customer_id = o.customer_id
    GROUP  BY c.customer_unique_id
)
SELECT
    order_count                                                     AS orders_placed,
    COUNT(*)                                                        AS people,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 3)              AS pct_of_people,
    ROUND(100.0 * SUM(COUNT(*)) OVER (ORDER BY order_count)
          / SUM(COUNT(*)) OVER (), 3)                               AS cumulative_pct
FROM per_person
GROUP BY order_count
ORDER BY order_count;


-- -----------------------------------------------------------------------------
-- Q31. Top customers by historical value
-- -----------------------------------------------------------------------------
-- Business: identifies who is worth a retention programme — or shows that no
-- one is concentrated enough to justify one.
--
-- NOTE THE LABEL: this is HISTORICAL value (what they actually spent), NOT
-- predicted lifetime value. With a ~3% repeat rate there is no reliable basis
-- for predicting future spend, so the project never calls this CLV.
-- -----------------------------------------------------------------------------
SELECT
    c.customer_unique_id,
    c.customer_state,
    COUNT(DISTINCT o.order_id)                   AS orders,
    ROUND(SUM(oi.price), 2)                      AS historical_value,
    ROUND(AVG(oi.price), 2)                      AS avg_item_price,
    MIN(DATE(o.order_purchase_timestamp))        AS first_order,
    MAX(DATE(o.order_purchase_timestamp))        AS last_order,
    DATEDIFF(MAX(o.order_purchase_timestamp), MIN(o.order_purchase_timestamp)) AS days_active
FROM orders o
JOIN customers   c  ON c.customer_id = o.customer_id
JOIN order_items oi ON oi.order_id   = o.order_id
WHERE o.revenue_eligible = 1
GROUP BY c.customer_unique_id, c.customer_state
ORDER BY historical_value DESC
LIMIT 20;


-- -----------------------------------------------------------------------------
-- Q32. RFM segmentation
-- -----------------------------------------------------------------------------
-- Business: group customers by Recency, Frequency and Monetary value so each
-- group can be treated differently.
--
-- METHOD, AND ONE DELIBERATE DEPARTURE FROM THE TEXTBOOK
-- ------------------------------------------------------
--   R = days since the person's last order, measured against the dataset's
--       maximum date (2018-10-17), NOT today. Scored 1-5 by quintile with
--       NTILE; fewer days = better score, so the order is reversed.
--   M = total historical revenue, scored 1-5 by quintile.
--   F = order count. *** NOT quintiles. ***
--
--       Why: 96.88% of people have exactly ONE order. NTILE(5) on that column
--       would split a near-constant into five arbitrary buckets and invent
--       differences that do not exist. Instead F is a small honest ordinal:
--           1 order = 1,  2 orders = 3,  3+ orders = 5
--       This limitation must be stated wherever RFM appears. Pretending the
--       F dimension is informative here would be fabrication.
--
-- Concepts: multiple CTEs, NTILE, CASE segmentation, date arithmetic.
-- -----------------------------------------------------------------------------
WITH dataset_end AS (
    SELECT MAX(order_purchase_timestamp) AS max_date FROM orders
),
customer_rfm AS (
    SELECT
        c.customer_unique_id,
        DATEDIFF((SELECT max_date FROM dataset_end),
                 MAX(o.order_purchase_timestamp))  AS recency_days,
        COUNT(DISTINCT o.order_id)                 AS frequency,
        SUM(oi.price)                              AS monetary
    FROM orders o
    JOIN customers   c  ON c.customer_id = o.customer_id
    JOIN order_items oi ON oi.order_id   = o.order_id
    WHERE o.revenue_eligible = 1
    GROUP BY c.customer_unique_id
),
scored AS (
    SELECT
        customer_unique_id, recency_days, frequency, monetary,
        -- fewer days since last order = better, so DESC puts recent buyers in bucket 5
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        CASE WHEN frequency >= 3 THEN 5
             WHEN frequency  = 2 THEN 3
             ELSE 1 END                            AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
    FROM customer_rfm
),
segmented AS (
    SELECT *,
        CASE
            WHEN r_score >= 4 AND f_score >= 3 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score  = 1 AND m_score >= 3 THEN 'Potential Loyalists'
            WHEN r_score <= 2 AND m_score >= 4                  THEN 'At Risk'
            WHEN r_score <= 2                                   THEN 'Lost'
            ELSE                                                     'Needs Attention'
        END AS segment
    FROM scored
)
SELECT
    segment,
    COUNT(*)                                                AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)      AS pct_of_customers,
    ROUND(AVG(recency_days), 0)                             AS avg_days_since_last_order,
    ROUND(AVG(frequency), 2)                                AS avg_orders,
    ROUND(AVG(monetary), 2)                                 AS avg_historical_value,
    ROUND(SUM(monetary), 2)                                 AS segment_revenue,
    ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 2) AS pct_of_revenue
FROM segmented
GROUP BY segment
ORDER BY segment_revenue DESC;


-- -----------------------------------------------------------------------------
-- Q33. Cohort analysis — do customers acquired later behave differently?
-- -----------------------------------------------------------------------------
-- Business: groups people by the month of their FIRST purchase, then tracks
-- how many come back in later months.
--
-- EXPECT VERY LOW NUMBERS. With a ~3% repeat rate the retention columns will
-- be near zero. That is the honest result, not a broken query. The useful
-- question becomes "does ANY cohort retain measurably better than the rest?"
--
-- Also note RIGHT-CENSORING: a customer acquired in 2018-08 has had almost no
-- time to return before the data ends, so later cohorts are not comparable
-- with earlier ones.
-- -----------------------------------------------------------------------------
WITH first_order AS (
    SELECT
        c.customer_unique_id,
        MIN(o.order_purchase_timestamp)                        AS first_purchase,
        DATE_FORMAT(MIN(o.order_purchase_timestamp), '%Y-%m')  AS cohort_month
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    GROUP BY c.customer_unique_id
),
activity AS (
    SELECT
        f.cohort_month,
        f.customer_unique_id,
        TIMESTAMPDIFF(MONTH, f.first_purchase, o.order_purchase_timestamp) AS months_since_first
    FROM orders o
    JOIN customers  c ON c.customer_id       = o.customer_id
    JOIN first_order f ON f.customer_unique_id = c.customer_unique_id
)
SELECT
    cohort_month,
    COUNT(DISTINCT CASE WHEN months_since_first = 0 THEN customer_unique_id END) AS cohort_size,
    COUNT(DISTINCT CASE WHEN months_since_first = 1 THEN customer_unique_id END) AS m1,
    COUNT(DISTINCT CASE WHEN months_since_first = 2 THEN customer_unique_id END) AS m2,
    COUNT(DISTINCT CASE WHEN months_since_first = 3 THEN customer_unique_id END) AS m3,
    COUNT(DISTINCT CASE WHEN months_since_first BETWEEN 4 AND 6  THEN customer_unique_id END) AS m4_6,
    COUNT(DISTINCT CASE WHEN months_since_first BETWEEN 7 AND 12 THEN customer_unique_id END) AS m7_12,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN months_since_first >= 1 THEN customer_unique_id END)
          / NULLIF(COUNT(DISTINCT CASE WHEN months_since_first = 0 THEN customer_unique_id END), 0), 2)
                                                                                 AS ever_returned_pct
FROM activity
WHERE cohort_month BETWEEN '2017-01' AND '2018-08'
GROUP BY cohort_month
ORDER BY cohort_month;


-- -----------------------------------------------------------------------------
-- Q34. Do repeat customers behave differently from one-time buyers?
-- -----------------------------------------------------------------------------
-- Business: if the ~3,000 repeat buyers differ measurably — better first
-- delivery, higher rating, particular categories — that difference is a lever
-- worth pulling. This is the most actionable retention question the data can
-- answer.
-- -----------------------------------------------------------------------------
WITH per_person AS (
    SELECT c.customer_unique_id,
           COUNT(DISTINCT o.order_id) AS order_count
    FROM   orders o
    JOIN   customers c ON c.customer_id = o.customer_id
    GROUP  BY c.customer_unique_id
),
order_score AS (
    SELECT order_id, AVG(review_score) AS score FROM order_reviews GROUP BY order_id
),
enriched AS (
    SELECT
        CASE WHEN pp.order_count >= 2 THEN 'Repeat buyer' ELSE 'One-time buyer' END AS buyer_type,
        o.order_id,
        o.delivery_days,
        o.is_late,
        s.score,
        oi.order_revenue
    FROM orders o
    JOIN customers  c  ON c.customer_id       = o.customer_id
    JOIN per_person pp ON pp.customer_unique_id = c.customer_unique_id
    LEFT JOIN order_score s ON s.order_id = o.order_id
    JOIN ( SELECT order_id, SUM(price) AS order_revenue
           FROM order_items GROUP BY order_id ) oi ON oi.order_id = o.order_id
    WHERE o.revenue_eligible = 1
)
SELECT
    buyer_type,
    COUNT(*)                                         AS orders,
    ROUND(AVG(order_revenue), 2)                     AS avg_order_value,
    ROUND(AVG(delivery_days), 2)                     AS avg_delivery_days,
    ROUND(100.0 * AVG(is_late), 2)                   AS late_pct,
    ROUND(AVG(score), 3)                             AS avg_review_score,
    ROUND(100.0 * AVG(CASE WHEN score = 1 THEN 1 ELSE 0 END), 2) AS one_star_pct
FROM enriched
GROUP BY buyer_type
ORDER BY buyer_type;
