-- =============================================================================
--  RetailPulse — 11 · Evidence for two business recommendations (2026-11-27)
-- =============================================================================
--  READ-ONLY. Two SELECTs that supply evidence the final project audit found
--  missing behind recommendations in reports/business_insights.md:
--
--    E1  Time from first to second order (Insight 6: "time-boxed follow-up")
--    E2  Freight as a share of product value by order-value band
--        (Insight 2 / priority 3: "free-shipping threshold above the median")
--
--  Both are reproduced independently in pandas by
--  scripts/validate_insight_evidence.py, which run_all_validations.py runs.
-- =============================================================================
USE retailpulse;


-- -----------------------------------------------------------------------------
-- E1. How long do repeat customers take to place a second order?
-- -----------------------------------------------------------------------------
-- Population: the 2,997 people (customer_unique_id) with 2+ orders of ANY
-- status — the same definition as the 3.12% repeat rate (KPI 9).
-- Gap = calendar days between the first and second order's purchase dates.
-- Ties on the same timestamp are broken by order_id, as in the pandas check.
--
-- Finding: 897 second orders (29.9%) fall on the SAME DAY as the first, 863 of
-- them within an hour. Those look like a split checkout, not a return visit,
-- so the gap is reported with and without same-day orders.
-- -----------------------------------------------------------------------------
WITH ranked AS (
    SELECT c.customer_unique_id,
           o.order_purchase_timestamp AS ts,
           ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id
                              ORDER BY o.order_purchase_timestamp, o.order_id) AS n
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
),
gaps AS (
    SELECT f.customer_unique_id,
           DATEDIFF(s.ts, f.ts)                         AS gap_days,
           TIMESTAMPDIFF(SECOND, f.ts, s.ts)            AS gap_seconds
    FROM ranked f
    JOIN ranked s ON s.customer_unique_id = f.customer_unique_id AND s.n = 2
    WHERE f.n = 1
)
SELECT
    COUNT(*)                                                         AS repeat_customers,
    SUM(gap_days = 0)                                                AS same_day,
    ROUND(100 * SUM(gap_days = 0) / COUNT(*), 1)                     AS same_day_pct,
    SUM(gap_seconds < 3600)                                          AS within_one_hour,
    SUM(gap_days > 0)                                                AS returned_later_day,
    ROUND(100 * SUM(gap_days > 0) / (SELECT COUNT(DISTINCT customer_unique_id) FROM customers), 2)
                                                                     AS returned_later_day_pct_of_people,
    ROUND(100 * SUM(gap_days > 0 AND gap_days <= 30)  / SUM(gap_days > 0), 1) AS later_within_30d_pct,
    ROUND(100 * SUM(gap_days > 0 AND gap_days <= 90)  / SUM(gap_days > 0), 1) AS later_within_90d_pct,
    ROUND(100 * SUM(gap_days > 0 AND gap_days <= 180) / SUM(gap_days > 0), 1) AS later_within_180d_pct,
    ROUND(AVG(CASE WHEN gap_days > 0 THEN gap_days END), 1)          AS later_mean_days
FROM gaps;

-- Median and quartiles of the gap for later-day returns (MySQL has no
-- PERCENTILE function; positions follow the pandas 'linear' quantile method).
WITH ranked AS (
    SELECT c.customer_unique_id, o.order_purchase_timestamp AS ts,
           ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id
                              ORDER BY o.order_purchase_timestamp, o.order_id) AS n
    FROM orders o JOIN customers c ON c.customer_id = o.customer_id
),
later AS (
    SELECT DATEDIFF(s.ts, f.ts) AS gap_days
    FROM ranked f
    JOIN ranked s ON s.customer_unique_id = f.customer_unique_id AND s.n = 2
    WHERE f.n = 1 AND DATEDIFF(s.ts, f.ts) > 0
),
ordered AS (
    SELECT gap_days, ROW_NUMBER() OVER (ORDER BY gap_days) - 1 AS i, COUNT(*) OVER () AS cnt FROM later
),
q AS (SELECT 0.25 AS p UNION ALL SELECT 0.50 UNION ALL SELECT 0.75)
SELECT q.p AS quantile,
       ROUND(MIN(CASE WHEN o.i = FLOOR(q.p * (o.cnt - 1)) THEN o.gap_days END)
             + (q.p * (MAX(o.cnt) - 1) - FLOOR(q.p * (MAX(o.cnt) - 1)))
             * (MIN(CASE WHEN o.i = FLOOR(q.p * (o.cnt - 1)) + 1 THEN o.gap_days END)
                - MIN(CASE WHEN o.i = FLOOR(q.p * (o.cnt - 1)) THEN o.gap_days END)), 2) AS gap_days
FROM ordered o CROSS JOIN q
GROUP BY q.p
ORDER BY q.p;


-- -----------------------------------------------------------------------------
-- E2. Freight as a share of product value, by order-value band
-- -----------------------------------------------------------------------------
-- Population: the 98,199 revenue-eligible orders with items (the AOV
-- population). Order value = SUM(item price); freight = SUM(item freight).
-- Bands straddle the 86.90 BRL median order value.
--
-- Finding: freight is 48% of product value under 50 BRL and falls steadily
-- with order value (21% at 86.90–120 BRL, 6% above 500 BRL). In the band just
-- above the median order value, freight averages 21.81 BRL per order
-- (341,739.87 / 15,669) — the per-order cost a free-shipping threshold there
-- would absorb. With no cost or margin data,
-- whether that pays back cannot be judged here: it is a hypothesis to test.
-- -----------------------------------------------------------------------------
WITH ord AS (
    SELECT o.order_id, SUM(oi.price) AS value_brl, SUM(oi.freight_value) AS freight_brl
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.revenue_eligible = 1
    GROUP BY o.order_id
),
banded AS (
    SELECT *,
           CASE WHEN value_brl <  50    THEN '1. <50'
                WHEN value_brl <  86.90 THEN '2. 50-86.90'
                WHEN value_brl < 120    THEN '3. 86.90-120'
                WHEN value_brl < 200    THEN '4. 120-200'
                WHEN value_brl < 500    THEN '5. 200-500'
                ELSE                         '6. 500+' END AS band
    FROM ord
)
SELECT band,
       COUNT(*)                                             AS orders,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)     AS pct_of_orders,
       ROUND(SUM(value_brl), 2)                             AS value_brl,
       ROUND(SUM(freight_brl), 2)                           AS freight_brl,
       ROUND(100 * SUM(freight_brl) / SUM(value_brl), 2)    AS freight_pct_of_value
FROM banded
GROUP BY band
ORDER BY band;


-- -----------------------------------------------------------------------------
-- E3. What a free-shipping threshold at the 86.90 BRL median would cover
-- -----------------------------------------------------------------------------
-- Same population as E2. Because 86.90 BRL is the MEDIAN order value, half
-- of all orders already clear it without any change in behaviour; their
-- freight is what the platform would absorb if it paid shipping in full.
-- "Near-miss" orders (70.00–86.89 BRL) are the only group a threshold could
-- plausibly move. Added 2026-11-27 (approved T05).
-- -----------------------------------------------------------------------------
WITH ord AS (
    SELECT o.order_id, SUM(oi.price) AS value_brl, SUM(oi.freight_value) AS freight_brl
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.revenue_eligible = 1
    GROUP BY o.order_id
)
SELECT
    COUNT(*)                                                              AS orders,
    SUM(value_brl >= 86.90)                                               AS qualifying_orders,
    ROUND(100 * SUM(value_brl >= 86.90) / COUNT(*), 2)                    AS qualifying_pct,
    ROUND(SUM(CASE WHEN value_brl >= 86.90 THEN freight_brl ELSE 0 END), 2) AS qualifying_freight_brl,
    ROUND(100 * SUM(CASE WHEN value_brl >= 86.90 THEN freight_brl ELSE 0 END) / SUM(freight_brl), 1)
                                                                          AS qualifying_pct_of_freight,
    ROUND(100 * SUM(CASE WHEN value_brl >= 86.90 THEN freight_brl ELSE 0 END) / SUM(value_brl), 1)
                                                                          AS qualifying_pct_of_product_revenue,
    SUM(value_brl >= 70 AND value_brl < 86.90)                            AS near_miss_orders,
    ROUND(100 * SUM(value_brl >= 70 AND value_brl < 86.90) / COUNT(*), 2) AS near_miss_pct
FROM ord;


-- -----------------------------------------------------------------------------
-- E4. Freight share by customer region and by items per order
-- -----------------------------------------------------------------------------
-- Same population. Regions follow the IBGE macro-regions, with São Paulo
-- shown separately because it holds 42% of these orders. Added 2026-11-27.
-- -----------------------------------------------------------------------------
WITH ord AS (
    SELECT o.order_id, c.customer_state AS st, COUNT(*) AS items,
           SUM(oi.price) AS value_brl, SUM(oi.freight_value) AS freight_brl
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    JOIN customers c    ON c.customer_id = o.customer_id
    WHERE o.revenue_eligible = 1
    GROUP BY o.order_id, c.customer_state
),
grouped AS (
    SELECT CONCAT('region: ',
             CASE WHEN st = 'SP' THEN 'SP'
                  WHEN st IN ('RJ','MG','ES') THEN 'Southeast excl. SP'
                  WHEN st IN ('PR','SC','RS') THEN 'South'
                  WHEN st IN ('DF','GO','MT','MS') THEN 'Centre-West'
                  WHEN st IN ('BA','PE','CE','MA','PB','RN','AL','PI','SE') THEN 'Northeast'
                  ELSE 'North' END) AS grp, value_brl, freight_brl
    FROM ord
    UNION ALL
    SELECT CONCAT('items: ', CASE WHEN items > 1 THEN '2+' ELSE '1' END), value_brl, freight_brl
    FROM ord
)
SELECT grp,
       COUNT(*)                                          AS orders,
       ROUND(100 * SUM(freight_brl) / SUM(value_brl), 2) AS freight_pct_of_value,
       ROUND(AVG(freight_brl), 2)                        AS avg_freight_brl,
       ROUND(100 * SUM(value_brl >= 86.90) / COUNT(*), 2) AS qualifying_pct
FROM grouped
GROUP BY grp
ORDER BY grp;
