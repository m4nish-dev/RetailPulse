-- =============================================================================
--  RetailPulse — 05_advanced_sql.sql
--  Section A (part 2): trends, growth and ranking with window functions
-- =============================================================================
--  Concepts: CTEs · window functions · ROW_NUMBER · RANK · DENSE_RANK
--            LAG · LEAD · running totals · moving averages · date functions
--
--  WHAT A WINDOW FUNCTION IS, IN PLAIN ENGLISH
--  -------------------------------------------
--  GROUP BY collapses many rows into one. A window function keeps every row
--  and adds a column calculated across a "window" of related rows.
--
--  So to show each month's revenue AND the previous month's beside it, GROUP BY
--  cannot help — it would have thrown the detail away. LAG() looks back one row
--  while keeping the current one. That is the whole idea.
--
--  THE STABLE WINDOW
--  -----------------
--  Trend queries are restricted to 2017-01 .. 2018-08 (in_stable_window = 1).
--  The dataset's edge months hold 4, 1, 16 and 4 orders, and November 2016 is
--  absent entirely. Charting them would show a collapse that never happened.
-- =============================================================================
USE retailpulse;


-- -----------------------------------------------------------------------------
-- Q21. Monthly revenue with month-over-month growth
-- -----------------------------------------------------------------------------
-- Business: the headline trend chart. MoM growth answers "are we accelerating
-- or slowing?", which the raw revenue line alone does not.
-- Concepts: CTE + LAG() + a window-framed moving average.
-- Grain: aggregated to order_month from the item grain.
-- -----------------------------------------------------------------------------
WITH monthly AS (
    SELECT
        o.order_month,
        COUNT(DISTINCT o.order_id) AS orders,
        SUM(oi.price)              AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.revenue_eligible = 1
      AND o.in_stable_window = 1
    GROUP BY o.order_month
)
SELECT
    order_month,
    orders,
    ROUND(revenue, 2)                                              AS revenue,
    ROUND(LAG(revenue) OVER (ORDER BY order_month), 2)             AS prev_month_revenue,
    ROUND(revenue - LAG(revenue) OVER (ORDER BY order_month), 2)   AS change_brl,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_month))
          / NULLIF(LAG(revenue) OVER (ORDER BY order_month), 0), 1) AS mom_growth_pct,
    -- 3-month moving average smooths the Black Friday spike out of the trend
    ROUND(AVG(revenue) OVER (ORDER BY order_month
                             ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS moving_avg_3m,
    -- running total since the window opened
    ROUND(SUM(revenue) OVER (ORDER BY order_month
                             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_total
FROM monthly
ORDER BY order_month;


-- -----------------------------------------------------------------------------
-- Q22. Year-over-year comparison on comparable months only
-- -----------------------------------------------------------------------------
-- Business: the honest growth number.
--
-- WHY JANUARY–AUGUST ONLY: 2016 holds 329 orders against 45,101 in 2017, so a
-- full-year comparison computes to roughly +13,600% — arithmetically true and
-- completely misleading. 2018 also stops in August. Comparing Jan–Aug to
-- Jan–Aug is the only like-for-like window the data supports.
-- Concepts: conditional aggregation, MONTH(), CTE.
-- -----------------------------------------------------------------------------
WITH monthly AS (
    SELECT
        o.order_year,
        MONTH(o.order_purchase_timestamp) AS month_num,
        COUNT(DISTINCT o.order_id)        AS orders,
        SUM(oi.price)                     AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.revenue_eligible = 1
      AND MONTH(o.order_purchase_timestamp) BETWEEN 1 AND 8
      AND o.order_year IN (2017, 2018)
    GROUP BY o.order_year, MONTH(o.order_purchase_timestamp)
)
SELECT
    month_num,
    ROUND(SUM(CASE WHEN order_year = 2017 THEN revenue END), 2) AS revenue_2017,
    ROUND(SUM(CASE WHEN order_year = 2018 THEN revenue END), 2) AS revenue_2018,
    ROUND(100.0 * (SUM(CASE WHEN order_year = 2018 THEN revenue END)
                 - SUM(CASE WHEN order_year = 2017 THEN revenue END))
          / NULLIF(SUM(CASE WHEN order_year = 2017 THEN revenue END), 0), 1) AS yoy_growth_pct,
    SUM(CASE WHEN order_year = 2017 THEN orders END)            AS orders_2017,
    SUM(CASE WHEN order_year = 2018 THEN orders END)            AS orders_2018
FROM monthly
GROUP BY month_num WITH ROLLUP
ORDER BY month_num;


-- -----------------------------------------------------------------------------
-- Q23. Rank states by revenue — and the difference between the three rankers
-- -----------------------------------------------------------------------------
-- Business: a clean league table with cumulative share, showing how few states
-- carry the business.
--
-- ROW_NUMBER  always 1,2,3,4 — breaks ties arbitrarily
-- RANK        ties share a rank, then it SKIPS: 1,2,2,4
-- DENSE_RANK  ties share a rank, no gap:        1,2,2,3
-- Use RANK for "top 10 including ties", DENSE_RANK for distinct tiers.
-- -----------------------------------------------------------------------------
WITH state_revenue AS (
    SELECT
        c.customer_state,
        COUNT(DISTINCT o.order_id) AS orders,
        SUM(oi.price)              AS revenue
    FROM orders o
    JOIN customers   c ON c.customer_id = o.customer_id
    JOIN order_items oi ON oi.order_id  = o.order_id
    WHERE o.revenue_eligible = 1
    GROUP BY c.customer_state
)
SELECT
    ROW_NUMBER() OVER (ORDER BY revenue DESC)             AS row_num,
    RANK()       OVER (ORDER BY revenue DESC)             AS rank_pos,
    DENSE_RANK() OVER (ORDER BY revenue DESC)             AS dense_rank_pos,
    customer_state,
    orders,
    ROUND(revenue, 2)                                     AS revenue,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)      AS pct_of_total,
    ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC
                                     ROWS UNBOUNDED PRECEDING)
          / SUM(revenue) OVER (), 2)                      AS cumulative_pct
FROM state_revenue
ORDER BY revenue DESC
LIMIT 12;


-- -----------------------------------------------------------------------------
-- Q24. Top 3 products within each category
-- -----------------------------------------------------------------------------
-- Business: a per-category hero list, not one global list dominated by the
-- biggest category.
-- Concepts: PARTITION BY — restarts the ranking for each category. This is the
-- classic "top N per group" problem, and a very common interview question.
-- -----------------------------------------------------------------------------
WITH product_revenue AS (
    SELECT
        p.product_category_name_english AS category,
        oi.product_id,
        COUNT(*)      AS times_sold,
        SUM(oi.price) AS revenue
    FROM order_items oi
    JOIN orders   o ON o.order_id   = oi.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.revenue_eligible = 1
    GROUP BY p.product_category_name_english, oi.product_id
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) AS rank_in_category,
           SUM(revenue) OVER (PARTITION BY category)                       AS category_revenue
    FROM product_revenue
)
SELECT
    category,
    rank_in_category,
    product_id,
    times_sold,
    ROUND(revenue, 2)                                       AS revenue,
    ROUND(100.0 * revenue / category_revenue, 1)            AS pct_of_category
FROM ranked
WHERE rank_in_category <= 3
  AND category_revenue >= 300000      -- only categories large enough to matter
ORDER BY category_revenue DESC, rank_in_category;


-- -----------------------------------------------------------------------------
-- Q25. Monthly review score with LAG and LEAD
-- -----------------------------------------------------------------------------
-- Business: is satisfaction improving? LAG shows where it came from, LEAD shows
-- where it goes next — useful for spotting whether a bad month recovered.
-- Grain: reviews joined to orders, aggregated by the ORDER's purchase month.
-- -----------------------------------------------------------------------------
WITH monthly_reviews AS (
    SELECT
        o.order_month,
        COUNT(*)                                                   AS reviews,
        AVG(r.review_score)                                        AS avg_score,
        100.0 * AVG(CASE WHEN r.review_score = 1 THEN 1 ELSE 0 END) AS one_star_pct
    FROM order_reviews r
    JOIN orders o ON o.order_id = r.order_id
    WHERE o.in_stable_window = 1
    GROUP BY o.order_month
)
SELECT
    order_month,
    reviews,
    ROUND(avg_score, 3)                                                   AS avg_score,
    ROUND(LAG(avg_score)  OVER (ORDER BY order_month), 3)                 AS prev_month,
    ROUND(LEAD(avg_score) OVER (ORDER BY order_month), 3)                 AS next_month,
    ROUND(avg_score - LAG(avg_score) OVER (ORDER BY order_month), 3)      AS change_vs_prev,
    ROUND(one_star_pct, 2)                                                AS one_star_pct,
    ROUND(AVG(avg_score) OVER (ORDER BY order_month
                               ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 3) AS moving_avg_3m
FROM monthly_reviews
ORDER BY order_month;


-- -----------------------------------------------------------------------------
-- Q26. Does delivery delay actually damage review scores?
-- -----------------------------------------------------------------------------
-- Business: THE question that turns "we should improve delivery" into a costed
-- business case. If late orders score materially worse, the investment
-- argument writes itself.
--
-- Method: bucket orders by how early/late they arrived, then average the
-- review score per bucket.
-- Grain care: reviews are collapsed to one score per order FIRST, so the 547
-- multi-review orders do not get counted twice.
-- CAVEAT: correlation, not causation. A late delivery may share a root cause
-- with a bad experience (a poor seller) rather than directly causing it.
-- -----------------------------------------------------------------------------
WITH order_score AS (
    SELECT order_id, AVG(review_score) AS score
    FROM   order_reviews
    GROUP  BY order_id
)
SELECT
    CASE
        WHEN o.delay_days <= -15 THEN 'a. 15+ days EARLY'
        WHEN o.delay_days <=  -7 THEN 'b. 7-15 days early'
        WHEN o.delay_days <=   0 THEN 'c. 0-7 days early (on time)'
        WHEN o.delay_days <=   7 THEN 'd. 1-7 days LATE'
        WHEN o.delay_days <=  15 THEN 'e. 8-15 days late'
        WHEN o.delay_days <=  30 THEN 'f. 16-30 days late'
        ELSE                          'g. 30+ days late'
    END                                                            AS delivery_bucket,
    COUNT(*)                                                       AS orders,
    ROUND(AVG(s.score), 3)                                         AS avg_review_score,
    ROUND(100.0 * AVG(CASE WHEN s.score = 1 THEN 1 ELSE 0 END), 1) AS pct_one_star,
    ROUND(100.0 * AVG(CASE WHEN s.score = 5 THEN 1 ELSE 0 END), 1) AS pct_five_star
FROM orders o
JOIN order_score s ON s.order_id = o.order_id
WHERE o.delivery_measurable = 1
GROUP BY delivery_bucket
ORDER BY delivery_bucket;


-- -----------------------------------------------------------------------------
-- Q26b. Sensitivity check: does the Q26 pattern survive without reviews
--       answered before the parcel arrived?
-- -----------------------------------------------------------------------------
-- Why: Olist sends the survey the day after delivery - or, if the parcel has
-- not arrived, about two days after the ESTIMATED date. 4,795 reviews on
-- delivered orders (4.98%) were answered before delivery (issue Q19), and 94%
-- of those belong to late orders. If they alone created the "late = low score"
-- pattern, Q26 would be overstated.
--
-- Grain: ORDER (one average score per order), exactly as Q26.
--   all_reviews   : Q26's population - every review of the order
--   after_arrival : reviews filtered at REVIEW grain to review_before_delivery
--                   = 0 FIRST, then averaged per order. An order whose only
--                   reviews were answered early drops out; a mixed order keeps
--                   only its post-arrival review(s).
-- Denominator: delivered orders (delivery_measurable = 1) with >= 1 qualifying
-- review. Buckets match Q26, with 16-30 and 30+ days late combined as >15.
-- Association only: no causal claim.
-- -----------------------------------------------------------------------------
WITH bucketed AS (
    SELECT o.order_id,
           CASE
               WHEN o.delay_days <= -15 THEN 'a. 15+ days early'
               WHEN o.delay_days <=  -7 THEN 'b. 7-15 days early'
               WHEN o.delay_days <=   0 THEN 'c. 0-7 days early (on time)'
               WHEN o.delay_days <=   7 THEN 'd. 1-7 days late'
               WHEN o.delay_days <=  15 THEN 'e. 8-15 days late'
               ELSE                          'f. more than 15 days late'
           END AS bucket
    FROM orders o
    WHERE o.delivery_measurable = 1
),
all_scores AS (
    SELECT order_id, AVG(review_score) AS score FROM order_reviews GROUP BY order_id
),
after_scores AS (
    SELECT order_id, AVG(review_score) AS score FROM order_reviews
    WHERE review_before_delivery = 0 GROUP BY order_id
)
SELECT b.bucket,
       -- NULL for orders with no qualifying review, so AVG() ignores them:
       -- the denominator is exactly the orders that HAVE a qualifying review.
       COUNT(a.order_id)                                                       AS orders_all,
       ROUND(AVG(a.score), 3)                                                  AS avg_score_all,
       ROUND(100.0 * AVG(CASE WHEN a.order_id IS NULL THEN NULL
                              WHEN a.score = 1 THEN 1 ELSE 0 END), 1)          AS pct_1star_all,
       COUNT(f.order_id)                                                       AS orders_after_arrival,
       ROUND(AVG(f.score), 3)                                                  AS avg_score_after_arrival,
       ROUND(100.0 * AVG(CASE WHEN f.order_id IS NULL THEN NULL
                              WHEN f.score = 1 THEN 1 ELSE 0 END), 1)          AS pct_1star_after_arrival
FROM bucketed b
LEFT JOIN all_scores   a ON a.order_id = b.order_id
LEFT JOIN after_scores f ON f.order_id = b.order_id
GROUP BY b.bucket
ORDER BY b.bucket;


-- -----------------------------------------------------------------------------
-- Q27. Are the delivery estimates padded?
-- -----------------------------------------------------------------------------
-- Business: follows directly from Q17. If orders routinely arrive far earlier
-- than promised, Olist is quoting pessimistic dates — which protects the
-- on-time metric but may cost conversions at checkout.
-- Concepts: percentile-style bucketing with conditional aggregation.
-- -----------------------------------------------------------------------------
SELECT
    order_month,
    COUNT(*)                                                     AS orders,
    ROUND(AVG(delivery_days), 1)                                 AS actual_days,
    ROUND(AVG(TIMESTAMPDIFF(HOUR, order_purchase_timestamp,
                            order_estimated_delivery_date)/24), 1) AS promised_days,
    ROUND(AVG(-delay_days), 1)                                   AS avg_days_early,
    ROUND(100.0 * AVG(1 - is_late), 1)                           AS on_time_pct
FROM orders
WHERE delivery_measurable = 1
  AND in_stable_window    = 1
GROUP BY order_month
ORDER BY order_month;
