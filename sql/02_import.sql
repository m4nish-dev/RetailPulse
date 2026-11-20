-- =============================================================================
--  RetailPulse — Phase 4
--  02_import.sql · bulk-load the cleaned CSVs into MySQL 8.4
-- =============================================================================
--  Run FROM THE PROJECT ROOT so the relative paths resolve:
--
--      mysql --local-infile=1 -u root retailpulse < sql/02_import.sql
--
--  Requires local_infile enabled on BOTH sides:
--      server : SET GLOBAL local_infile = 1;   (done below)
--      client : --local-infile=1               (flag above)
--
--  WHY `LOAD DATA LOCAL INFILE` AND NOT INSERT STATEMENTS
--  ------------------------------------------------------
--  LOAD DATA is MySQL's bulk loader. It streams the file straight into the
--  storage engine instead of parsing 569,776 individual INSERT statements.
--  It is roughly two orders of magnitude faster here, and it is what you
--  would use in a real job.
--
--  FIVE THINGS THAT BREAK A NAIVE LOAD, AND HOW EACH IS HANDLED
--  ------------------------------------------------------------
--  1. NEWLINES INSIDE REVIEW TEXT. 3,852 review comments contain a newline
--     because customers pressed Enter. Without FIELDS ENCLOSED BY '"' the
--     loader treats each as a row break and the import shatters.
--
--     `ESCAPED BY ''` IS ALSO REQUIRED, AND THIS COST TWO ROWS TO LEARN.
--     MySQL defaults to ESCAPED BY '\\' (backslash), but Python's csv writer
--     follows RFC 4180 and escapes a quote by DOUBLING it (""), never with a
--     backslash. With the default, one review containing a blank line
--     (\\r\\n\\r\\n) was mis-parsed and swallowed its neighbouring row:
--     99,222 loaded instead of 99,224, silently. Setting ESCAPED BY to empty
--     disables backslash escaping and makes MySQL read the file the way
--     Python wrote it. Verified: 99,224/99,224.
--
--  2. BOOLEANS WRITTEN AS TEXT. pandas exports True/False, not 1/0. Loading
--     'True' into TINYINT silently yields 0 — every flag would read false.
--     Converted with CASE WHEN below.
--
--  3. EMPTY STRINGS ARE NOT NULL. A blank CSV field arrives as '', which in a
--     DATETIME column becomes '0000-00-00' and in a VARCHAR stays an empty
--     string. NULLIF(@v,'') turns it into a real NULL.
--
--  4. INTEGERS WRITTEN AS FLOATS. pandas writes a nullable integer column as
--     '40.0'. Loading that into SMALLINT truncates with a warning.
--     ROUND(NULLIF(@v,'')) converts cleanly.
--
--  5. LEADING ZEROS IN ZIP CODES. Handled by the schema (CHAR(5), not INT).
--     '01037' survives; as an INT it would become 1037.
--
--  LOAD ORDER follows the foreign keys: parents before children.
-- =============================================================================

SET GLOBAL local_infile = 1;
USE retailpulse;

-- Speed up the bulk load. Re-enabled at the end, which re-checks every
-- constraint, so nothing is skipped — only deferred.
SET autocommit = 0;
SET unique_checks = 0;
SET foreign_key_checks = 0;


-- =============================================================================
--  1. product_category_translation  (73 rows from CSV, + 1 sentinel)
-- =============================================================================
LOAD DATA LOCAL INFILE 'dataset/cleaned/category_translation_clean.csv'
INTO TABLE product_category_translation
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY ''
LINES  TERMINATED BY '\n'
IGNORE 1 ROWS
(product_category_name, product_category_name_english);

-- The sentinel. 610 products carry the category 'unknown' (Phase 3 issue Q04),
-- which has no translation row. Adding it explicitly lets products.
-- product_category_name keep a real FOREIGN KEY instead of dropping the
-- constraint. Counted openly: 73 loaded + 1 sentinel = 74.
INSERT INTO product_category_translation
       (product_category_name, product_category_name_english)
VALUES ('unknown', 'unknown');


-- =============================================================================
--  2. sellers  (3,095)
-- =============================================================================
LOAD DATA LOCAL INFILE 'dataset/cleaned/sellers_clean.csv'
INTO TABLE sellers
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY ''
LINES  TERMINATED BY '\n'
IGNORE 1 ROWS
(seller_id, seller_zip_code_prefix, seller_city, seller_state);


-- =============================================================================
--  3. customers  (99,441)
-- =============================================================================
LOAD DATA LOCAL INFILE 'dataset/cleaned/customers_clean.csv'
INTO TABLE customers
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY ''
LINES  TERMINATED BY '\n'
IGNORE 1 ROWS
(customer_id, customer_unique_id, customer_zip_code_prefix,
 customer_city, customer_state);


-- =============================================================================
--  4. geolocation  (19,015)
-- =============================================================================
LOAD DATA LOCAL INFILE 'dataset/cleaned/geolocation_clean.csv'
INTO TABLE geolocation
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY ''
LINES  TERMINATED BY '\n'
IGNORE 1 ROWS
(geolocation_zip_code_prefix, geolocation_lat, geolocation_lng,
 geolocation_city, geolocation_state, readings);


-- =============================================================================
--  5. products  (32,951)
-- =============================================================================
--  CSV column order differs from table column order, and the numeric columns
--  arrive as '40.0'. Both handled by loading into @variables then SET.
-- =============================================================================
LOAD DATA LOCAL INFILE 'dataset/cleaned/products_clean.csv'
INTO TABLE products
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY ''
LINES  TERMINATED BY '\n'
IGNORE 1 ROWS
(@product_id, @category, @name_len, @desc_len, @photos,
 @weight, @length, @height, @width, @category_en)
SET product_id                    = @product_id,
    product_category_name         = @category,
    product_category_name_english = @category_en,
    product_name_length           = ROUND(NULLIF(@name_len, '')),
    product_description_length    = ROUND(NULLIF(@desc_len, '')),
    product_photos_qty            = ROUND(NULLIF(@photos,   '')),
    product_weight_g              = ROUND(NULLIF(@weight,   '')),
    product_length_cm             = ROUND(NULLIF(@length,   '')),
    product_height_cm             = ROUND(NULLIF(@height,   '')),
    product_width_cm              = ROUND(NULLIF(@width,    ''));


-- =============================================================================
--  6. orders  (99,441)
-- =============================================================================
--  The cleaned CSV has 36 columns; this table stores 21 of them. The 15 left
--  out are either duplicated from customers (customer_state, customer_city,
--  customer_zip_code_prefix) or aggregates of child tables (order_revenue,
--  item_count, review_count, payment_total...). Storing an aggregate here
--  would duplicate data that can drift out of sync with its source; the views
--  in 07_business_analysis.sql compute them instead.
--
--  No ROW is dropped — only redundant columns are not copied.
-- =============================================================================
LOAD DATA LOCAL INFILE 'dataset/cleaned/orders_clean.csv'
INTO TABLE orders
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY ''
LINES  TERMINATED BY '\n'
IGNORE 1 ROWS
(@order_id, @customer_id, @order_status, @purchase, @approved,
 @carrier, @delivered, @estimated, @date_anom, @anom_note, @stable,
 @cust_unique, @cust_state, @cust_city, @cust_zip, @item_count,
 @order_revenue, @order_freight, @n_sellers, @review_avg, @review_count,
 @payment_total, @payment_count, @max_inst, @order_date, @order_month,
 @order_year, @is_delivered, @rev_eligible, @has_items, @has_review,
 @delivery_days, @delay_days, @is_late, @deliv_measurable, @deliv_anom,
 @carrier_before_approval, @stage_timing_valid)
SET order_id                      = @order_id,
    customer_id                   = @customer_id,
    order_status                  = @order_status,
    order_purchase_timestamp      = @purchase,
    order_approved_at             = NULLIF(@approved,  ''),
    order_delivered_carrier_date  = NULLIF(@carrier,   ''),
    order_delivered_customer_date = NULLIF(@delivered, ''),
    order_estimated_delivery_date = @estimated,
    order_date                    = @order_date,
    order_month                   = @order_month,
    order_year                    = @order_year,
    delivery_days                 = NULLIF(@delivery_days, ''),
    delay_days                    = NULLIF(@delay_days,    ''),
    is_late              = CASE @is_late          WHEN 'True' THEN 1 WHEN 'False' THEN 0 ELSE NULL END,
    delivery_measurable  = CASE @deliv_measurable WHEN 'True' THEN 1 ELSE 0 END,
    is_delivered         = CASE @is_delivered     WHEN 'True' THEN 1 ELSE 0 END,
    revenue_eligible     = CASE @rev_eligible     WHEN 'True' THEN 1 ELSE 0 END,
    in_stable_window     = CASE @stable           WHEN 'True' THEN 1 ELSE 0 END,
    has_date_anomaly     = CASE @date_anom        WHEN 'True' THEN 1 ELSE 0 END,
    has_delivery_anomaly = CASE @deliv_anom       WHEN 'True' THEN 1 ELSE 0 END,
    date_anomaly_note    = IF(CHAR_LENGTH(@anom_note) = 0, NULL, @anom_note),
    carrier_before_approval = CASE @carrier_before_approval WHEN 'True' THEN 1 ELSE 0 END,
    stage_timing_valid      = CASE @stage_timing_valid      WHEN 'True' THEN 1 ELSE 0 END;


-- =============================================================================
--  7. order_items  (112,650)
-- =============================================================================
--  18 CSV columns; 7 stored. The rest (category, seller_state, order_status,
--  order_month, customer_state, item_total) are all reachable by joining
--  products, sellers and orders, so copying them here would be duplication.
-- =============================================================================
LOAD DATA LOCAL INFILE 'dataset/cleaned/order_items_clean.csv'
INTO TABLE order_items
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY ''
LINES  TERMINATED BY '\n'
IGNORE 1 ROWS
(@order_id, @item_id, @product_id, @seller_id, @ship_limit, @price,
 @freight, @cat, @cat_en, @seller_state, @seller_city, @status,
 @order_date, @order_month, @order_year, @eligible, @cust_state, @item_total)
SET order_id            = @order_id,
    order_item_id       = @item_id,
    product_id          = @product_id,
    seller_id           = @seller_id,
    shipping_limit_date = @ship_limit,
    price               = @price,
    freight_value       = @freight;


-- =============================================================================
--  8. order_payments  (103,886)
-- =============================================================================
LOAD DATA LOCAL INFILE 'dataset/cleaned/order_payments_clean.csv'
INTO TABLE order_payments
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY ''
LINES  TERMINATED BY '\n'
IGNORE 1 ROWS
(@order_id, @seq, @type, @inst, @value, @anomaly, @inst_clean, @type_clean)
SET order_id                   = @order_id,
    payment_sequential         = @seq,
    payment_type               = @type,
    payment_installments       = @inst,
    payment_value              = @value,
    payment_type_clean         = @type_clean,
    payment_installments_clean = @inst_clean,
    payment_anomaly            = IF(CHAR_LENGTH(@anomaly) = 0, NULL, @anomaly);


-- =============================================================================
--  9. order_reviews  (99,224)
-- =============================================================================
--  The table where ENCLOSED BY '"' earns its keep: 3,852 of these rows
--  contain a newline inside the comment text.
-- =============================================================================
LOAD DATA LOCAL INFILE 'dataset/cleaned/order_reviews_clean.csv'
INTO TABLE order_reviews
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY ''
LINES  TERMINATED BY '\n'
IGNORE 1 ROWS
(@review_id, @order_id, @score, @title, @message, @created, @answered, @before_delivery)
SET review_id               = @review_id,
    order_id                = @order_id,
    review_score            = @score,
    -- CHAR_LENGTH()=0, NOT NULLIF(@v,''). This matters:
    -- utf8mb4_unicode_ci is a PAD SPACE collation, so trailing spaces are
    -- ignored in comparison and ' ' = '' evaluates TRUE. NULLIF(' ','')
    -- therefore returns NULL, which nulled 2 titles and 9 messages that
    -- Python keeps as single-space strings -- a silent 11-row divergence
    -- between the database and the verified reference.
    -- CHAR_LENGTH() counts characters and ignores collation entirely.
    review_comment_title    = IF(CHAR_LENGTH(@title)   = 0, NULL, @title),
    review_comment_message  = IF(CHAR_LENGTH(@message) = 0, NULL, @message),
    review_creation_date    = @created,
    review_answer_timestamp = @answered,
    -- nullable boolean: '' (no delivery date) must become NULL, not 0
    review_before_delivery  = CASE @before_delivery WHEN 'True' THEN 1
                                                    WHEN 'False' THEN 0 ELSE NULL END;


-- =============================================================================
--  Re-enable constraint checking and commit
-- =============================================================================
SET foreign_key_checks = 1;
SET unique_checks = 1;
COMMIT;
SET autocommit = 1;

-- Refresh optimiser statistics so the query planner makes good choices
ANALYZE TABLE customers, sellers, products, geolocation,
              product_category_translation, orders, order_items,
              order_payments, order_reviews;


-- =============================================================================
--  Row-count verification against the cleaned CSVs
-- =============================================================================
SELECT 'product_category_translation' AS table_name, COUNT(*) AS loaded, 74     AS expected FROM product_category_translation
UNION ALL SELECT 'sellers',       COUNT(*),   3095   FROM sellers
UNION ALL SELECT 'customers',     COUNT(*),  99441   FROM customers
UNION ALL SELECT 'geolocation',   COUNT(*),  19015   FROM geolocation
UNION ALL SELECT 'products',      COUNT(*),  32951   FROM products
UNION ALL SELECT 'orders',        COUNT(*),  99441   FROM orders
UNION ALL SELECT 'order_items',   COUNT(*), 112650   FROM order_items
UNION ALL SELECT 'order_payments',COUNT(*), 103886   FROM order_payments
UNION ALL SELECT 'order_reviews', COUNT(*),  99224   FROM order_reviews;
