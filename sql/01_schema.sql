-- =============================================================================
--  RetailPulse — Phase 4
--  01_schema.sql · MySQL 8.4 schema definition
-- =============================================================================
--  Creates the `retailpulse` database and nine tables modelling the cleaned
--  Olist dataset produced by notebooks/02_data_cleaning.ipynb.
--
--  Run:  mysql -u root < sql/01_schema.sql
--
--  DESIGN NOTES
--  ------------
--  1. GRAIN IS PRESERVED. Four different grains exist and each gets its own
--     table. Collapsing them would double-count revenue:
--         orders          one row per order            99,441
--         order_items     one row per product line    112,650
--         order_payments  one row per payment         103,886
--         order_reviews   one row per review record    99,224
--
--  2. MONEY IS DECIMAL, NEVER FLOAT. FLOAT is binary and cannot represent
--     0.10 exactly, so sums drift by cents over 112,650 rows. DECIMAL(10,2)
--     is exact. This is the single most common data-type mistake in finance
--     tables.
--
--  3. IDS ARE CHAR(32), NOT INT. They are fixed-length hexadecimal strings.
--     CHAR beats VARCHAR here because every value is exactly 32 characters,
--     so CHAR avoids VARCHAR's per-row length byte and compares faster.
--
--  4. ZIP PREFIXES ARE CHAR(5), NOT INT. '01037' stored as a number becomes
--     1037 — a different, wrong place. This is a real bug this schema prevents.
--
--  5. utf8mb4 THROUGHOUT. Review text is Portuguese with accented characters
--     (ç, ã, é). MySQL's old `utf8` is a 3-byte subset that mangles some
--     characters; utf8mb4 is true UTF-8.
--
--  6. DERIVED AGGREGATES ARE NOT STORED. The cleaned orders CSV carries
--     order_revenue, review_count, payment_total etc. Those are SUMs of child
--     tables, so storing them here would duplicate data that can drift out of
--     sync. They are computed by the views in 07_business_analysis.sql.
--     Row-level derived values that are NOT aggregates (delivery_days,
--     is_late, revenue_eligible) ARE stored, because they are properties of
--     the order itself and are expensive to recompute in every query.
-- =============================================================================

DROP DATABASE IF EXISTS retailpulse;
CREATE DATABASE retailpulse
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE retailpulse;


-- =============================================================================
--  DIMENSION TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
--  customers — one row per ORDER-LEVEL customer record (99,441)
-- -----------------------------------------------------------------------------
--  THE MOST IMPORTANT TABLE IN THE SCHEMA TO UNDERSTAND.
--
--  customer_id        is unique per ORDER. 99,441 distinct values.
--  customer_unique_id identifies the actual PERSON. 96,096 distinct values.
--
--  A person who buys twice appears as two rows with two different
--  customer_id values but the SAME customer_unique_id.
--
--  RULE: JOIN on customer_id. COUNT and SEGMENT on customer_unique_id.
--  Counting people with customer_id returns 99,441 and makes repeat-purchase
--  rate, retention, cohorts and RFM all collapse to zero.
-- -----------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id              CHAR(32)     NOT NULL,
    customer_unique_id       CHAR(32)     NOT NULL,
    customer_zip_code_prefix CHAR(5)      NOT NULL,
    customer_city            VARCHAR(60)  NOT NULL,
    customer_state           CHAR(2)      NOT NULL,
    PRIMARY KEY (customer_id),
    -- deliberately a plain INDEX, not UNIQUE: 3,345 rows share a value and
    -- that repetition is the entire basis of retention analysis
    INDEX idx_cust_unique (customer_unique_id),
    INDEX idx_cust_state  (customer_state),
    INDEX idx_cust_zip    (customer_zip_code_prefix)
) ENGINE=InnoDB;


-- -----------------------------------------------------------------------------
--  sellers — one row per seller (3,095)
-- -----------------------------------------------------------------------------
CREATE TABLE sellers (
    seller_id              CHAR(32)    NOT NULL,
    seller_zip_code_prefix CHAR(5)     NOT NULL,
    seller_city            VARCHAR(60) NOT NULL,
    seller_state           CHAR(2)     NOT NULL,
    PRIMARY KEY (seller_id),
    INDEX idx_seller_state (seller_state)
) ENGINE=InnoDB;


-- -----------------------------------------------------------------------------
--  product_category_translation — Portuguese to English lookup (73 + 1)
-- -----------------------------------------------------------------------------
--  Source CSV holds 73 rows: the 71 original translations plus 2 added by hand
--  in Phase 3 (pc_gamer, portateis_cozinha_e_preparadores_de_alimentos), which
--  existed in products but were missing from the lookup.
--
--  02_import.sql then adds ONE sentinel row, 'unknown' -> 'unknown', so that
--  the 610 products with no category can satisfy a real foreign key instead of
--  forcing us to drop the constraint. The insert is explicit and counted, not
--  hidden, so 73 loaded + 1 sentinel = 74 reconciles against the CSV.
-- -----------------------------------------------------------------------------
CREATE TABLE product_category_translation (
    product_category_name         VARCHAR(60) NOT NULL,
    product_category_name_english VARCHAR(60) NOT NULL,
    PRIMARY KEY (product_category_name)
) ENGINE=InnoDB;


-- -----------------------------------------------------------------------------
--  products — one row per product (32,951)
-- -----------------------------------------------------------------------------
--  No cost or COGS column exists anywhere in this dataset. That is why this
--  project reports revenue only and never profit or margin.
-- -----------------------------------------------------------------------------
CREATE TABLE products (
    product_id                    CHAR(32)    NOT NULL,
    product_category_name         VARCHAR(60) NOT NULL,  -- 'unknown' for 610 rows
    product_category_name_english VARCHAR(60) NOT NULL,
    product_name_length           SMALLINT UNSIGNED NULL, -- source misspelled
    product_description_length    SMALLINT UNSIGNED NULL, -- these two as 'lenght'
    product_photos_qty            SMALLINT UNSIGNED NULL,
    product_weight_g              INT      UNSIGNED NULL,
    product_length_cm             SMALLINT UNSIGNED NULL,
    product_height_cm             SMALLINT UNSIGNED NULL,
    product_width_cm              SMALLINT UNSIGNED NULL,
    PRIMARY KEY (product_id),
    INDEX idx_prod_cat     (product_category_name),
    INDEX idx_prod_cat_en  (product_category_name_english),
    CONSTRAINT fk_products_category
        FOREIGN KEY (product_category_name)
        REFERENCES product_category_translation (product_category_name)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;


-- -----------------------------------------------------------------------------
--  geolocation — one row per zip prefix (19,015)
-- -----------------------------------------------------------------------------
--  Phase 3 aggregated 1,000,163 raw coordinate readings to one median point
--  per zip prefix. Reference data for maps; no KPI depends on it, so no
--  foreign key is declared against it (customer and seller zips are not a
--  perfect subset of these prefixes).
-- -----------------------------------------------------------------------------
CREATE TABLE geolocation (
    geolocation_zip_code_prefix CHAR(5)        NOT NULL,
    -- DOUBLE, not DECIMAL. Money uses DECIMAL because cents must be exact;
    -- coordinates are measurements, and the source carries 15 decimal places.
    -- DECIMAL(11,8) truncated every row and emitted 38,030 truncation notes.
    -- DOUBLE holds ~15 significant digits, matching the source exactly.
    geolocation_lat             DOUBLE         NOT NULL,
    geolocation_lng             DOUBLE         NOT NULL,
    geolocation_city            VARCHAR(60)    NOT NULL,
    geolocation_state           CHAR(2)        NOT NULL,
    readings                    INT UNSIGNED   NOT NULL,  -- raw points behind the median
    PRIMARY KEY (geolocation_zip_code_prefix),
    INDEX idx_geo_state (geolocation_state)
) ENGINE=InnoDB;


-- =============================================================================
--  FACT TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
--  orders — one row per order (99,441). The central fact table.
-- -----------------------------------------------------------------------------
--  customer_id carries a UNIQUE constraint. That is not a guess: Phase 1
--  validated orders -> customers as strictly one-to-one (every order has
--  exactly one customer row and vice versa). Declaring it UNIQUE documents
--  that fact in the schema and lets the optimiser use it.
--
--  The derived columns below are ROW-LEVEL properties of the order, not
--  aggregates of other tables, so storing them is normalisation-safe:
--      delivery_days / delay_days  computed from this row's own timestamps
--      is_late                     derived from UNROUNDED delay (rounding
--                                  first misclassified 6 orders in testing)
--      revenue_eligible            status NOT IN ('canceled','unavailable')
--      in_stable_window            purchase month within 2017-01 .. 2018-08
--      delivery_measurable         has a real delivered-to-customer date
-- -----------------------------------------------------------------------------
CREATE TABLE orders (
    order_id                      CHAR(32)      NOT NULL,
    customer_id                   CHAR(32)      NOT NULL,
    order_status                  VARCHAR(20)   NOT NULL,

    -- original timestamps, never altered
    order_purchase_timestamp      DATETIME      NOT NULL,
    order_approved_at             DATETIME      NULL,  -- 160 NULL
    order_delivered_carrier_date  DATETIME      NULL,  -- 1,783 NULL
    order_delivered_customer_date DATETIME      NULL,  -- 2,965 NULL
    order_estimated_delivery_date DATETIME      NOT NULL,

    -- derived calendar helpers
    order_date                    DATE          NOT NULL,
    order_month                   CHAR(7)       NOT NULL,  -- 'YYYY-MM'
    order_year                    SMALLINT      NOT NULL,

    -- derived delivery metrics (NULL where no delivery date exists)
    delivery_days                 DECIMAL(10,4) NULL,
    delay_days                    DECIMAL(10,4) NULL,     -- negative = early
    is_late                       TINYINT(1)    NULL,
    delivery_measurable           TINYINT(1)    NOT NULL,

    -- derived status flags
    is_delivered                  TINYINT(1)    NOT NULL,
    revenue_eligible              TINYINT(1)    NOT NULL,
    in_stable_window              TINYINT(1)    NOT NULL,

    -- data quality flags from Phase 3 (issues Q01, Q08)
    has_date_anomaly              TINYINT(1)    NOT NULL,
    has_delivery_anomaly          TINYINT(1)    NOT NULL,
    date_anomaly_note             VARCHAR(60)   NULL,

    PRIMARY KEY (order_id),
    UNIQUE KEY uq_orders_customer (customer_id),   -- validated 1:1
    INDEX idx_orders_status    (order_status),
    INDEX idx_orders_purchase  (order_purchase_timestamp),
    INDEX idx_orders_month     (order_month),
    INDEX idx_orders_eligible  (revenue_eligible),
    INDEX idx_orders_stable    (in_stable_window),
    -- Composite COVERING index for the monthly trend query, which is the
    -- single most-run analytical query in the project and the one behind the
    -- executive dashboard. Measured, not assumed: 0.35s -> 0.21s (~40%
    -- faster), and EXPLAIN reports "Using index", meaning MySQL answers from
    -- the index alone without reading the table at all.
    -- Column order matters: the two equality filters first, then the GROUP BY
    -- column. Reversing it would not allow the index-only scan.
    INDEX idx_orders_trend     (revenue_eligible, in_stable_window, order_month),
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;


-- -----------------------------------------------------------------------------
--  order_items — one row per PRODUCT LINE within an order (112,650)
-- -----------------------------------------------------------------------------
--  COMPOSITE PRIMARY KEY. order_id alone is NOT unique here: 112,650 rows
--  cover only 98,666 orders, because an order can contain up to 21 lines.
--  (order_id, order_item_id) together are unique — verified in Phase 1.
--
--  This is the revenue table. price is product revenue; freight_value is
--  shipping and is kept strictly separate, never folded into revenue.
-- -----------------------------------------------------------------------------
CREATE TABLE order_items (
    order_id            CHAR(32)      NOT NULL,
    order_item_id       SMALLINT UNSIGNED NOT NULL,  -- line number, 1..21
    product_id          CHAR(32)      NOT NULL,
    seller_id           CHAR(32)      NOT NULL,
    shipping_limit_date DATETIME      NOT NULL,
    price               DECIMAL(10,2) NOT NULL,
    freight_value       DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id),
    INDEX idx_items_product (product_id),
    INDEX idx_items_seller  (seller_id),
    CONSTRAINT fk_items_order
        FOREIGN KEY (order_id)   REFERENCES orders (order_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_items_product
        FOREIGN KEY (product_id) REFERENCES products (product_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_items_seller
        FOREIGN KEY (seller_id)  REFERENCES sellers (seller_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;


-- -----------------------------------------------------------------------------
--  order_payments — one row per PAYMENT (103,886)
-- -----------------------------------------------------------------------------
--  COMPOSITE PRIMARY KEY (order_id, payment_sequential). One order can carry
--  up to 29 payment rows — Brazilian instalment plans.
--
--  ⚠ Joining this table straight to order_items multiplies rows and inflates
--  revenue by +4.54% (measured in Phase 2). Always aggregate to order level
--  first. vw_order_summary does exactly that.
--
--  The *_clean columns hold Phase 3 corrections; the originals are kept
--  untouched beside them so every assumption stays auditable.
-- -----------------------------------------------------------------------------
CREATE TABLE order_payments (
    order_id                   CHAR(32)      NOT NULL,
    payment_sequential         SMALLINT UNSIGNED NOT NULL,
    payment_type               VARCHAR(20)   NOT NULL,  -- original, incl. 'not_defined'
    payment_installments       SMALLINT UNSIGNED NOT NULL,  -- original, incl. 0
    payment_value              DECIMAL(10,2) NOT NULL,
    payment_type_clean         VARCHAR(20)   NOT NULL,  -- 'not_defined' -> 'unknown'
    payment_installments_clean SMALLINT UNSIGNED NOT NULL,  -- 0 -> 1
    payment_anomaly            VARCHAR(80)   NULL,      -- NULL when clean
    PRIMARY KEY (order_id, payment_sequential),
    INDEX idx_pay_type (payment_type_clean),
    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;


-- -----------------------------------------------------------------------------
--  order_reviews — one row per REVIEW RECORD (99,224)
-- -----------------------------------------------------------------------------
--  ⚠ review_id IS NOT UNIQUE. 99,224 rows hold only 98,410 distinct review
--  ids: 789 ids appear against 2-3 DIFFERENT orders.
--
--  Phase 3 investigated before acting: of those 789 repeated ids, ZERO carry
--  differing scores. Each is one survey response covering several orders from
--  a single purchase event. The rows are therefore not duplicates of one
--  another — each ties a real score to a real, distinct order.
--
--  So the primary key is the composite (review_id, order_id), which IS unique
--  across all 99,224 rows. A surrogate AUTO_INCREMENT id was considered and
--  rejected: it would hide the fact that review_id repeats, and this schema
--  should stay honest about the source data.
-- -----------------------------------------------------------------------------
CREATE TABLE order_reviews (
    review_id               CHAR(32)     NOT NULL,
    order_id                CHAR(32)     NOT NULL,
    review_score            TINYINT UNSIGNED NOT NULL,  -- 1..5
    review_comment_title    VARCHAR(255) NULL,  -- 88.34% NULL, optional field
    review_comment_message  TEXT         NULL,  -- 58.70% NULL, Portuguese
    review_creation_date    DATETIME     NOT NULL,
    review_answer_timestamp DATETIME     NOT NULL,
    PRIMARY KEY (review_id, order_id),
    INDEX idx_rev_order (order_id),
    INDEX idx_rev_score (review_score),
    CONSTRAINT fk_reviews_order
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_review_score CHECK (review_score BETWEEN 1 AND 5)
) ENGINE=InnoDB;


-- =============================================================================
--  Confirm what was created
-- =============================================================================
SELECT TABLE_NAME, ENGINE, TABLE_COLLATION
FROM   information_schema.TABLES
WHERE  TABLE_SCHEMA = 'retailpulse'
ORDER  BY TABLE_NAME;
