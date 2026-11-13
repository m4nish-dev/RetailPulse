-- =============================================================================
--  RetailPulse — 08_validation.sql
--  Does MySQL agree with the Python reference?
-- =============================================================================
--  Every expected value below comes from notebooks/02_data_cleaning.ipynb,
--  which passed 34/34 of its own checks and reconciles to the raw CSVs. Those
--  same figures were independently confirmed by LibreOffice in Phase 2.
--
--  So this is a THIRD independent implementation of the same metrics. Three
--  engines — pandas, a spreadsheet, and SQL — agreeing is strong evidence the
--  numbers are right.
--
--  RULE: if SQL disagrees with Python, investigate. Never edit a verified
--  Python reference to make SQL look correct.
--
--  Each check returns PASS or FAIL in a `result` column.
-- =============================================================================
USE retailpulse;


-- =============================================================================
--  1. ROW COUNTS vs the cleaned CSVs
-- =============================================================================
SELECT '1. ROW COUNTS' AS check_group, '' AS check_name, '' AS actual, '' AS expected, '' AS result;

SELECT 'customers'      AS table_name, COUNT(*) AS actual,  99441 AS expected,
       IF(COUNT(*) =  99441,'PASS','FAIL') AS result FROM customers
UNION ALL SELECT 'orders',         COUNT(*),  99441, IF(COUNT(*)= 99441,'PASS','FAIL') FROM orders
UNION ALL SELECT 'order_items',    COUNT(*), 112650, IF(COUNT(*)=112650,'PASS','FAIL') FROM order_items
UNION ALL SELECT 'order_payments', COUNT(*), 103886, IF(COUNT(*)=103886,'PASS','FAIL') FROM order_payments
UNION ALL SELECT 'order_reviews',  COUNT(*),  99224, IF(COUNT(*)= 99224,'PASS','FAIL') FROM order_reviews
UNION ALL SELECT 'products',       COUNT(*),  32951, IF(COUNT(*)= 32951,'PASS','FAIL') FROM products
UNION ALL SELECT 'sellers',        COUNT(*),   3095, IF(COUNT(*)=  3095,'PASS','FAIL') FROM sellers
UNION ALL SELECT 'geolocation',    COUNT(*),  19015, IF(COUNT(*)= 19015,'PASS','FAIL') FROM geolocation
-- 73 loaded from CSV + 1 explicit 'unknown' sentinel added in 02_import.sql
UNION ALL SELECT 'category_translation', COUNT(*), 74, IF(COUNT(*)=74,'PASS','FAIL')
          FROM product_category_translation;


-- =============================================================================
--  2. PRIMARY KEY UNIQUENESS
-- =============================================================================
--  A primary key must be unique AND never null. MySQL enforces this at insert
--  time, so these checks confirm the DECLARED key matches reality rather than
--  re-testing the engine. The interesting rows are the composite keys and the
--  deliberately NON-unique customer_unique_id.
-- =============================================================================
SELECT '2. PRIMARY KEYS' AS check_group, '' AS a, '' AS b, '' AS c, '' AS d;

SELECT 'orders.order_id unique' AS check_name,
       COUNT(DISTINCT order_id) AS distinct_vals, COUNT(*) AS total_rows,
       IF(COUNT(DISTINCT order_id) = COUNT(*),'PASS','FAIL') AS result FROM orders
UNION ALL
SELECT 'order_items composite (order_id, order_item_id)',
       COUNT(DISTINCT order_id, order_item_id), COUNT(*),
       IF(COUNT(DISTINCT order_id, order_item_id) = COUNT(*),'PASS','FAIL') FROM order_items
UNION ALL
SELECT 'payments composite (order_id, payment_sequential)',
       COUNT(DISTINCT order_id, payment_sequential), COUNT(*),
       IF(COUNT(DISTINCT order_id, payment_sequential) = COUNT(*),'PASS','FAIL') FROM order_payments
UNION ALL
SELECT 'reviews composite (review_id, order_id)',
       COUNT(DISTINCT review_id, order_id), COUNT(*),
       IF(COUNT(DISTINCT review_id, order_id) = COUNT(*),'PASS','FAIL') FROM order_reviews
UNION ALL
-- review_id alone must NOT be unique: 789 ids are reused across different
-- orders. PASS here means the known duplication is present as expected.
SELECT 'reviews.review_id is NOT unique (expected)',
       COUNT(DISTINCT review_id), COUNT(*),
       IF(COUNT(DISTINCT review_id) = 98410,'PASS','FAIL') FROM order_reviews
UNION ALL
-- Likewise customer_unique_id: 96,096 people across 99,441 order records.
SELECT 'customers.customer_unique_id is NOT unique (expected)',
       COUNT(DISTINCT customer_unique_id), COUNT(*),
       IF(COUNT(DISTINCT customer_unique_id) = 96096,'PASS','FAIL') FROM customers;


-- =============================================================================
--  3. FOREIGN KEY INTEGRITY — zero orphans expected
-- =============================================================================
--  InnoDB enforces these, so an orphan could not have been inserted. Running
--  them anyway proves the constraints are actually declared and active.
-- =============================================================================
SELECT '3. FOREIGN KEYS' AS check_group, '' AS a, '' AS b, '' AS c;

SELECT 'orders -> customers' AS relationship, COUNT(*) AS orphans,
       IF(COUNT(*) = 0,'PASS','FAIL') AS result
FROM orders o LEFT JOIN customers c ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL
UNION ALL
SELECT 'order_items -> orders', COUNT(*), IF(COUNT(*)=0,'PASS','FAIL')
FROM order_items oi LEFT JOIN orders o ON o.order_id = oi.order_id WHERE o.order_id IS NULL
UNION ALL
SELECT 'order_items -> products', COUNT(*), IF(COUNT(*)=0,'PASS','FAIL')
FROM order_items oi LEFT JOIN products p ON p.product_id = oi.product_id WHERE p.product_id IS NULL
UNION ALL
SELECT 'order_items -> sellers', COUNT(*), IF(COUNT(*)=0,'PASS','FAIL')
FROM order_items oi LEFT JOIN sellers s ON s.seller_id = oi.seller_id WHERE s.seller_id IS NULL
UNION ALL
SELECT 'payments -> orders', COUNT(*), IF(COUNT(*)=0,'PASS','FAIL')
FROM order_payments p LEFT JOIN orders o ON o.order_id = p.order_id WHERE o.order_id IS NULL
UNION ALL
SELECT 'reviews -> orders', COUNT(*), IF(COUNT(*)=0,'PASS','FAIL')
FROM order_reviews r LEFT JOIN orders o ON o.order_id = r.order_id WHERE o.order_id IS NULL
UNION ALL
SELECT 'products -> category_translation', COUNT(*), IF(COUNT(*)=0,'PASS','FAIL')
FROM products p LEFT JOIN product_category_translation t
     ON t.product_category_name = p.product_category_name
WHERE t.product_category_name IS NULL;


-- =============================================================================
--  4. NULL HANDLING — nulls should appear exactly where Phase 3 said
-- =============================================================================
SELECT '4. NULL HANDLING' AS check_group, '' AS a, '' AS b, '' AS c;

SELECT 'orders.order_approved_at NULL' AS check_name, SUM(order_approved_at IS NULL) AS actual,
       160 AS expected, IF(SUM(order_approved_at IS NULL)=160,'PASS','FAIL') AS result FROM orders
UNION ALL SELECT 'orders.order_delivered_carrier_date NULL', SUM(order_delivered_carrier_date IS NULL), 1783,
       IF(SUM(order_delivered_carrier_date IS NULL)=1783,'PASS','FAIL') FROM orders
UNION ALL SELECT 'orders.order_delivered_customer_date NULL', SUM(order_delivered_customer_date IS NULL), 2965,
       IF(SUM(order_delivered_customer_date IS NULL)=2965,'PASS','FAIL') FROM orders
UNION ALL SELECT 'orders.is_late NULL (no delivery date)', SUM(is_late IS NULL), 2965,
       IF(SUM(is_late IS NULL)=2965,'PASS','FAIL') FROM orders
UNION ALL SELECT 'reviews.review_comment_title NULL', SUM(review_comment_title IS NULL), 87656,
       IF(SUM(review_comment_title IS NULL)=87656,'PASS','FAIL') FROM order_reviews
UNION ALL SELECT 'reviews.review_comment_message NULL', SUM(review_comment_message IS NULL), 58247,
       IF(SUM(review_comment_message IS NULL)=58247,'PASS','FAIL') FROM order_reviews
UNION ALL SELECT 'products.product_weight_g NULL', SUM(product_weight_g IS NULL), 2,
       IF(SUM(product_weight_g IS NULL)=2,'PASS','FAIL') FROM products
UNION ALL SELECT 'no NULL order_id anywhere', SUM(order_id IS NULL), 0,
       IF(SUM(order_id IS NULL)=0,'PASS','FAIL') FROM orders;


-- =============================================================================
--  5. KNOWN DATA QUALITY COUNTS (Phase 3 issue register)
-- =============================================================================
SELECT '5. DATA QUALITY COUNTS' AS check_group, '' AS a, '' AS b, '' AS c;

SELECT 'Q01 delivered but no delivery date' AS issue, COUNT(*) AS actual, 8 AS expected,
       IF(COUNT(*)=8,'PASS','FAIL') AS result
FROM orders WHERE order_status='delivered' AND order_delivered_customer_date IS NULL
UNION ALL
SELECT 'Q02 review_id values reused', COUNT(*), 789, IF(COUNT(*)=789,'PASS','FAIL')
FROM (SELECT review_id FROM order_reviews GROUP BY review_id HAVING COUNT(*)>1) x
UNION ALL
SELECT 'Q04 products with unknown category', COUNT(*), 610, IF(COUNT(*)=610,'PASS','FAIL')
FROM products WHERE product_category_name='unknown'
UNION ALL
SELECT 'Q05 orders with no line items', COUNT(*), 775, IF(COUNT(*)=775,'PASS','FAIL')
FROM orders o LEFT JOIN order_items oi ON oi.order_id=o.order_id
WHERE oi.order_id IS NULL
UNION ALL
SELECT 'Q08 delivered before carrier handoff', COUNT(*), 23, IF(COUNT(*)=23,'PASS','FAIL')
FROM orders WHERE has_date_anomaly=1
UNION ALL
SELECT 'Q14 orders with no review', COUNT(*), 768, IF(COUNT(*)=768,'PASS','FAIL')
FROM orders o LEFT JOIN order_reviews r ON r.order_id=o.order_id
WHERE r.order_id IS NULL;


-- =============================================================================
--  6. REVENUE RECONCILIATION vs Python
-- =============================================================================
--  Money is DECIMAL, so these should match to the cent, not approximately.
-- =============================================================================
SELECT '6. REVENUE' AS check_group, '' AS a, '' AS b, '' AS c;

SELECT 'GMV all statuses' AS metric, ROUND(SUM(price),2) AS actual, 13591643.70 AS expected_python,
       IF(ABS(SUM(price) - 13591643.70) < 0.01,'PASS','FAIL') AS result FROM order_items
UNION ALL
SELECT 'Freight charged', ROUND(SUM(freight_value),2), 2251909.54,
       IF(ABS(SUM(freight_value) - 2251909.54) < 0.01,'PASS','FAIL') FROM order_items
UNION ALL
SELECT 'Payment total', ROUND(SUM(payment_value),2), 16008872.12,
       IF(ABS(SUM(payment_value) - 16008872.12) < 0.01,'PASS','FAIL') FROM order_payments
UNION ALL
SELECT 'Revenue eligible (excl. canceled/unavailable)',
       ROUND(SUM(oi.price),2), 13494400.74,
       IF(ABS(SUM(oi.price) - 13494400.74) < 0.01,'PASS','FAIL')
FROM order_items oi JOIN orders o ON o.order_id=oi.order_id WHERE o.revenue_eligible=1
UNION ALL
-- the view must reproduce GMV exactly, proving its aggregation loses nothing
SELECT 'vw_order_summary revenue = item GMV',
       ROUND(SUM(order_revenue),2), 13591643.70,
       IF(ABS(SUM(order_revenue) - 13591643.70) < 0.01,'PASS','FAIL') FROM vw_order_summary;


-- =============================================================================
--  7. COUNT RECONCILIATION vs Python
-- =============================================================================
SELECT '7. COUNTS' AS check_group, '' AS a, '' AS b, '' AS c;

SELECT 'Total orders' AS metric, COUNT(*) AS actual, 99441 AS expected_python,
       IF(COUNT(*)=99441,'PASS','FAIL') AS result FROM orders
UNION ALL SELECT 'Delivered orders', SUM(is_delivered), 96478, IF(SUM(is_delivered)=96478,'PASS','FAIL') FROM orders
UNION ALL SELECT 'Canceled orders', COUNT(*), 625, IF(COUNT(*)=625,'PASS','FAIL') FROM orders WHERE order_status='canceled'
UNION ALL SELECT 'Orders with items', COUNT(DISTINCT order_id), 98666,
       IF(COUNT(DISTINCT order_id)=98666,'PASS','FAIL') FROM order_items
UNION ALL SELECT 'Orders with a review', COUNT(DISTINCT order_id), 98673,
       IF(COUNT(DISTINCT order_id)=98673,'PASS','FAIL') FROM order_reviews
UNION ALL SELECT 'Distinct PEOPLE (customer_unique_id)', COUNT(DISTINCT customer_unique_id), 96096,
       IF(COUNT(DISTINCT customer_unique_id)=96096,'PASS','FAIL') FROM customers
UNION ALL SELECT 'vw_customer_summary rows = people', COUNT(*), 96096,
       IF(COUNT(*)=96096,'PASS','FAIL') FROM vw_customer_summary
UNION ALL SELECT 'Eligible orders WITH items (AOV denominator)',
       COUNT(*), 98199, IF(COUNT(*)=98199,'PASS','FAIL')
FROM vw_order_summary WHERE revenue_eligible=1 AND item_count>0;


-- =============================================================================
--  8. DELIVERY METRICS vs Python
-- =============================================================================
SELECT '8. DELIVERY' AS check_group, '' AS a, '' AS b, '' AS c;

SELECT 'Orders with a real delivery date' AS metric, COUNT(*) AS actual, 96476 AS expected_python,
       IF(COUNT(*)=96476,'PASS','FAIL') AS result FROM orders WHERE delivery_measurable=1
UNION ALL SELECT 'Late deliveries', SUM(is_late), 7827, IF(SUM(is_late)=7827,'PASS','FAIL')
       FROM orders WHERE delivery_measurable=1
UNION ALL SELECT 'Avg delivery days (x10000)', ROUND(AVG(delivery_days)*10000), 125587,
       IF(ABS(AVG(delivery_days) - 12.5587) < 0.001,'PASS','FAIL') FROM orders WHERE delivery_measurable=1
UNION ALL SELECT 'On-time rate % (x10000)', ROUND(100*AVG(1-is_late)*10000), 918871,
       IF(ABS(100*AVG(1-is_late) - 91.8871) < 0.001,'PASS','FAIL') FROM orders WHERE delivery_measurable=1;


-- =============================================================================
--  9. REVIEW METRICS vs Python — and the grain distinction
-- =============================================================================
SELECT '9. REVIEWS' AS check_group, '' AS a, '' AS b, '' AS c;

SELECT 'Avg review score — REVIEW grain' AS metric, ROUND(AVG(review_score),4) AS actual,
       4.0864 AS expected_python, IF(ABS(AVG(review_score)-4.0864) < 0.0001,'PASS','FAIL') AS result
FROM order_reviews
UNION ALL
-- Deliberately different, and both are correct: 547 orders carry 2-3 reviews,
-- so averaging review ROWS weights those orders more than averaging per ORDER.
SELECT 'Avg review score — ORDER grain', ROUND(AVG(review_score_avg),4), 4.0868,
       IF(ABS(AVG(review_score_avg)-4.0868) < 0.0001,'PASS','FAIL')
FROM vw_order_summary WHERE review_count > 0
UNION ALL
SELECT 'Review rows', COUNT(*), 99224, IF(COUNT(*)=99224,'PASS','FAIL') FROM order_reviews;


-- =============================================================================
--  10. JOIN FAN-OUT DETECTION
-- =============================================================================
--  The most important validation in this file. It proves the schema and views
--  avoid the error that silently inflates revenue.
--
--  Phase 2 measured the damage on the real data:
--      correct                        13,591,643.70
--      items joined to payments       14,209,115.34   +4.54%
--      items INNER JOINed to reviews  13,527,224.77   -0.47%
--
--  The second is the more dangerous: it both duplicates and drops, so the
--  errors partly cancel and the wrong number looks almost right.
-- =============================================================================
SELECT '10. FAN-OUT' AS check_group, '' AS a, '' AS b, '' AS c;

SELECT 'CORRECT: items alone' AS approach, ROUND(SUM(oi.price),2) AS revenue,
       COUNT(*) AS rows_produced, 'baseline' AS note
FROM order_items oi
UNION ALL
SELECT 'WRONG: items x payments', ROUND(SUM(oi.price),2), COUNT(*),
       CONCAT('inflated by ',
              ROUND(100.0*(SUM(oi.price)/13591643.70 - 1),2), '%')
FROM order_items oi JOIN order_payments p ON p.order_id = oi.order_id
UNION ALL
SELECT 'WRONG: items x reviews (INNER)', ROUND(SUM(oi.price),2), COUNT(*),
       CONCAT('error of ',
              ROUND(100.0*(SUM(oi.price)/13591643.70 - 1),2), '%')
FROM order_items oi JOIN order_reviews r ON r.order_id = oi.order_id;

-- And the proof that the view does NOT fan out: one row per order, exactly.
SELECT 'vw_order_summary has exactly one row per order' AS check_name,
       COUNT(*) AS rows_in_view, COUNT(DISTINCT order_id) AS distinct_orders,
       IF(COUNT(*) = COUNT(DISTINCT order_id) AND COUNT(*) = 99441,'PASS','FAIL') AS result
FROM vw_order_summary;


-- =============================================================================
--  11. DUPLICATE DETECTION
-- =============================================================================
SELECT '11. DUPLICATES' AS check_group, '' AS a, '' AS b, '' AS c;

SELECT 'duplicate full rows in order_items' AS check_name, COUNT(*) AS duplicates,
       IF(COUNT(*)=0,'PASS','FAIL') AS result FROM (
    SELECT order_id, order_item_id, product_id, seller_id, price, freight_value
    FROM order_items GROUP BY order_id, order_item_id, product_id, seller_id, price, freight_value
    HAVING COUNT(*) > 1) d
UNION ALL
SELECT 'duplicate full rows in order_reviews', COUNT(*), IF(COUNT(*)=0,'PASS','FAIL') FROM (
    SELECT review_id, order_id, review_score FROM order_reviews
    GROUP BY review_id, order_id, review_score HAVING COUNT(*) > 1) d
UNION ALL
-- Of the 789 reused review ids, ZERO carry differing scores. That is why
-- Phase 3 kept every row instead of deduplicating.
SELECT 'reused review_ids carrying DIFFERENT scores', COUNT(*), IF(COUNT(*)=0,'PASS','FAIL') FROM (
    SELECT review_id FROM order_reviews GROUP BY review_id
    HAVING COUNT(*) > 1 AND COUNT(DISTINCT review_score) > 1) d;


-- =============================================================================
--  12. ZIP CODE LEADING ZEROS — the CHAR(5) decision, verified
-- =============================================================================
SELECT '12. ZIP CODES' AS check_group, '' AS a, '' AS b, '' AS c;

SELECT 'customer zips starting with 0' AS check_name,
       COUNT(*) AS zips_with_leading_zero,
       MIN(customer_zip_code_prefix) AS example,
       IF(COUNT(*) > 0 AND CHAR_LENGTH(MIN(customer_zip_code_prefix))=5,'PASS','FAIL') AS result
FROM customers WHERE customer_zip_code_prefix LIKE '0%';
