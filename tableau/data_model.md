# RetailPulse — Tableau Data Model

**Target:** Tableau Desktop Public Edition (free) on macOS · text-file (CSV) connections · extracts
**Status:** designed and logic-validated on macOS; **not yet built in Tableau** (runtime test pending)

---

## 1. The data files

Tableau reads 14 CSV files exported from the validated MySQL database. Nothing in the
database changes; the files are regenerable and byte-identical on every export.

| Folder | Files | Rows / columns / MD5 | Exported by | Checked by |
|---|---|---|---|---|
| `tableau/data/` | 5 view extracts: `vw_order_summary`, `vw_review_summary`, `vw_customer_summary`, `vw_category_performance`, `vw_seller_performance` | `_manifest.csv` | `scripts/export_tableau_data.py` | `scripts/check_tableau_data.py` |
| `tableau/data/analytical/` | 9 analytical sources ([definitions](../documentation/analytical_sources.md)) | `_manifest.csv` | `scripts/export_tableau_sources.py` (`sql/09_dashboard_sources.sql`) | `scripts/validate_tableau_sources.py`, `scripts/check_tableau_data.py` |

The data files are git-ignored (derived data under the dataset's CC BY-NC-SA 4.0
licence). They hold only data: no credentials, no connection details.

**Why not connect Tableau to MySQL?** The free edition cannot. Its connectors are
"Google Drive, JSON files, Microsoft Excel 2007 or later, OData, PDF, Spatial files,
Statistical files, Text files" (Tableau help, *Desktop and Public Edition feature
comparison*). CSV is also the safer choice: the published workbook can never
contain database connection details or credentials.

---

## 2. Six data sources, not one

Tableau **relationships** (the "noodles" on the Data Source canvas) aggregate each
measure at its own table's grain, so a revenue sum is never multiplied by joining
reviews or payments (a physical join would: pitfall P05).

**Filters cross relationships in both directions.** In a Tableau data source, **a
filter on a field of one table also restricts the related tables**. The validator demonstrates the
consequence (pitfall P07). If the customer table sat in the orders data source, an
Order Month = 2017-11 filter would cut "Total People" from 96,096 lifetime people
to 7,430. The model therefore uses **separate data sources wherever a filter must
not cross**:

| Data source | Root (first) table | Related tables (key) | Used by dashboards |
|---|---|---|---|
| **RP Orders** | `vw_order_summary` (99,441, one per order) | `vw_review_summary` (99,224, per review) on `order_id`; `delivery_stage_orders` (95,088) on `order_id` | 1 Executive, 5 Operations, 6 Satisfaction |
| **RP Customers** | `vw_customer_summary` (96,096, one per person) | `rfm_customer_segments` (96,096) on `customer_unique_id` | 2 Customers |
| **RP Cohorts** | `cohort_retention` (400 cells) | none | 2 Customers |
| **RP Categories** | `dim_category` (74) | `vw_category_performance` (1,282, category × month), `product_performance` (32,951), `category_satisfaction` (74), all on `category` | 1 (top 10), 3 Products, 6 (category satisfaction), 7 Category Detail |
| **RP Sellers** | `vw_seller_performance` (3,053, one per seller) | `seller_scorecard` (3,053) on `seller_id`; `seller_category_performance` (6,545) on `seller_id` | 4 Sellers, 7 (top sellers in category), 8 Seller Detail |
| **RP Stage Summary** | `delivery_stage_summary` (4) | none | 5 Operations (stacked bar) |

Six data sources in total, counting the four-row stage summary. Largest data source: RP Orders, 293,753 rows, far
below the free edition's 15 million rows per data source.

### Why `seller_category_performance` appears only in RP Sellers

It could relate to both `dim_category` and `vw_seller_performance`, but a Tableau
relationship model is a tree (one path between any two tables), so it lives in
**RP Sellers**. The Category Detail dashboard filters it by category through the
parameter field H04. Its `product_revenue`, `item_count`, `late_orders` and
`delivery_measurable_orders` therefore never sit beside `product_performance` and
`category_satisfaction`, which also keeps field names unambiguous.

### Primary keys (grain) — verified unique and non-null

| Table | Primary key | One row = |
|---|---|---|
| `vw_order_summary` | `order_id` | order |
| `vw_review_summary` | `review_id` + `order_id` | review on an order (`review_id` alone repeats 814 times) |
| `delivery_stage_orders` | `order_id` | order with valid stage timing |
| `vw_customer_summary`, `rfm_customer_segments` | `customer_unique_id` | person |
| `cohort_retention` | `cohort_month` + `months_since_acquisition` | cohort cell |
| `dim_category`, `category_satisfaction` | `category` | category |
| `vw_category_performance` | `category` + `order_month` | category-month |
| `product_performance` | `product_id` | product |
| `vw_seller_performance`, `seller_scorecard` | `seller_id` | seller |
| `seller_category_performance` | `seller_id` + `category` | seller-category |
| `delivery_stage_summary` | `stage_order` | stage (plus a Total row) |

### Views that are not exported

`vw_monthly_revenue` and `vw_delivery_performance` stay in MySQL only. They are
pre-aggregated, and the monthly view has known boundary issues (see
`reports/phase6_documentation_audit.md` §5). Every monthly figure on the dashboard is
computed from `vw_order_summary`. Tableau's date functions
(`[Order Month] = DATETRUNC('month', [order_date])`, `DATEDIFF('month', ...)`) replace a
separate date table.

---

## 3. Relationships

**Already configured in the generated workbook** (`tableau/RetailPulse.twb`, built by
`scripts/build_tableau_workbook.py`). You only need §3a if you build the data sources by hand.
Each relationship links a related table to the **root** table of its data source.
Cardinality and orphans below were **measured on the CSVs**, not assumed, and are re-checked by
`scripts/check_tableau_data.py` (24/24).

**Performance options: leave Tableau's defaults** (Cardinality *Many* / *Many*, Referential
integrity *Some records match*). The defaults always return correct results. Tighter settings
only speed queries up, and a wrong one can drop rows. These files are small enough that speed
is not a concern.

| Data source | Left (root) table | Right table | Matching fields | Measured cardinality | Referential integrity (measured) | Analytical use | Fan-out / double-count risk |
|---|---|---|---|---|---|---|---|
| RP Orders | `vw_order_summary` | `vw_review_summary` | `order_id` = `order_id` | one-to-many: root key unique; up to 3 reviews per order (547 orders have 2–3) | every review has its order; 768 orders have no review | review KPIs filtered by order month, state, status; delay-vs-score | **none with relationships.** Each table aggregates at its own grain. A physical *join* would repeat order revenue per review (pitfall P05) |
| RP Orders | `vw_order_summary` | `delivery_stage_orders` | `order_id` = `order_id` | one-to-zero-or-one: both keys unique | every stage row has its order; 4,353 orders have no valid stage timing | stage days and shares filtered by month and state | none. Stage measures cover 95,088 orders by design (label it) |
| RP Customers | `vw_customer_summary` | `rfm_customer_segments` | `customer_unique_id` = `customer_unique_id` | one-to-one | complete both ways (96,096) | RFM by customer state | none |
| RP Categories | `dim_category` | `vw_category_performance` | `category` = `category` | one-to-many: up to 22 months per category | complete both ways (74 categories) | category revenue, trend, growth | none. Revenue summed at category-month grain |
| RP Categories | `dim_category` | `product_performance` | `category` = `category` | one-to-many: up to 3,029 products per category | complete | product drill-down | none |
| RP Categories | `dim_category` | `category_satisfaction` | `category` = `category` | one-to-one | complete | category review scores | category rows are **not additive** (multi-category orders count in each). The fields N29–N33 blank at totals |
| RP Sellers | `vw_seller_performance` | `seller_scorecard` | `seller_id` = `seller_id` | one-to-one | complete (3,053) | weighted seller rates | none |
| RP Sellers | `vw_seller_performance` | `seller_category_performance` | `seller_id` = `seller_id` | one-to-many: up to 27 categories per seller | complete | seller detail; top sellers in a category | `order_count` in this table is not additive. Use `item_count` / `product_revenue` (fields N13–N16) |

### Relationships investigated and deliberately NOT created

| Candidate | Finding (measured) | Why it is unsafe | What the model does instead |
|---|---|---|---|
| Orders ↔ customers on `customer_unique_id` | one-to-many (up to 17 orders per person); keys complete. **41 orders carry a different `customer_state`** from the customer table, which keeps one state per person | Inside one data source an **order-date filter would cut lifetime customer figures** (Total People 96,096 → 7,430 for 2017-11: pitfall P07), and two different `customer_state` fields would sit side by side | Separate **RP Customers** data source; people counts on order dashboards use `COUNTD([customer_unique_id])` from the order table (M03) |
| Orders ↔ sellers | `vw_order_summary` has **no seller key**; 1,278 orders involve 2+ sellers | Linking needs order items as a bridge. Each multi-seller order would then count once per seller, and order revenue would repeat | Seller analysis uses seller-grain tables (`vw_seller_performance`, `seller_scorecard`, `seller_category_performance`) in **RP Sellers**; seller-order *pairs* are labelled as such (M31) |
| `seller_category_performance` ↔ `dim_category` (as well as sellers) | a relationship model must be a tree (one path between two tables) | a second parent would create two filter paths | it lives in RP Sellers; category selection reaches it through `Is Selected Category` (H04) |
| `cohort_retention`, `delivery_stage_summary` ↔ anything | pre-aggregated tables with no row-level key | any relationship would multiply or misalign their pre-computed values | stand-alone data sources |

> **Note on a draft workbook.** Tableau's recovery file shows a draft that put
> `vw_customer_summary` inside the orders data source (first row above). The generated
> workbook replaces that draft; you can close it without saving.

### 3a. Building the relationships by hand (only if not using the generated workbook)

On the Data Source page, drag the related table next to the root table. Tableau opens the
relationship dialog; pick the matching field on both sides as in the table above.

### Filter rules that follow from Tableau's two-way filtering

| Dashboard | Filter only on | Never filter on |
|---|---|---|
| Executive, Operations, Satisfaction (RP Orders) | `vw_order_summary` fields: `Order Month`, `order_date` year, `customer_state`, `order_status`, `in_stable_window` | fields of `vw_review_summary` or `delivery_stage_orders`. A filter on them would silently shrink order counts to reviewed or stage-valid orders. `delivery_bucket` may be an **axis** on the delay-vs-score sheet only |
| Customers (RP Customers) | `vw_customer_summary.customer_state`; `rfm_scored = 1` on the RFM sheet | n/a |
| Products, Category Detail (RP Categories) | `Is Selected Category` (H03); `in_stable_window` on trend sheets | a month filter on share sheets, unless it is added to context (pitfall P09) |
| Sellers, Seller Detail (RP Sellers) | `seller_state`, `Is Selected Seller` (H06), `Seller Has 50+ Orders` (H08) | a `category` filter on Seller sheets: it would restrict sellers to those who sold in it (wanted only on Category Detail) |

---

## 4. Field naming

> **Automated.** In the generated workbook every column already carries its final caption:
> the CSV name, or the documented rename for the 28 duplicates (e.g. `rev_order_id`).
> Internally Tableau names a duplicate `[order_id (vw_review_summary.csv)]`; the workbook
> keeps that internal name and sets the caption. The two steps below apply only to a
> hand-built data source.

1. **Reset Tableau's tidied names.** Tableau converts CSV names on connection.
   Underscores become spaces and all-lower-case names get a capital first letter,
   so `customer_state` would no longer match the formulas. On the Data Source
   page, open the metadata grid, select all fields, click any field's drop-down
   and choose **Reset name** (Tableau help, *Understand Field Type Detection and
   Naming Improvements*).
2. **Rename duplicate columns** that appear in two tables of one data source.
   The exact list (28 renames) is generated from the CSV headers in
   [`calculated_fields.md` § Field renames](calculated_fields.md#field-renames-required-before-entering-formulas).
   Example: in RP Orders, `vw_review_summary.order_id` becomes `rev_order_id`.

The validator checks that every `[field]` referenced by every formula exists
after these two steps (static checks, 6/6).

---

## 5. Data types

> **Automated.** The generated workbook declares each column's type from the CSV values. That
> inference was checked against Tableau 2026.3.2's own inference on 60 columns: no difference.
> `scripts/validate_tableau_workbook.py` confirms every value fits its declared type. The table
> below documents the required types and applies to a hand-built data source.

| Field(s) | Required type | Why |
|---|---|---|
| `order_date` (RP Orders) | **Date** | basis of `Order Month` |
| `order_month` in `vw_category_performance` (RP Categories) | **String (Abc)** | formulas N37–N39 compare it as text `'2017-01'`; Tableau may otherwise guess Date |
| `cohort_month`, `activity_month` (RP Cohorts) | **String** | matrix rows sort correctly as `YYYY-MM` text |
| every `*_id` column, `customer_state`, `seller_state`, `category`, `rfm_segment`, `delivery_bucket`, `order_status` | **String** | IDs are 32-character hex. A mostly-numeric ID must never be read as a number |
| flags: `revenue_eligible`, `is_delivered`, `delivery_measurable`, `is_late`, `in_stable_window`, `review_before_delivery`, `rfm_scored`, `is_observed`, `is_repeat_customer` | **Number** (whole or decimal) | formulas compare `= 1` / `= 0`; the CSVs store 1/0 (blank = NULL) |
| `months_since_acquisition`, `review_score`, `total_orders` | Number (whole); use as **Dimension** on axes | matrix columns, score distribution, purchase frequency |
| money (`order_revenue`, `revenue`, `product_revenue`, `monetary_value`, `historical_value`, …) | Number (decimal) | formatted BRL by the calculated fields |

After loading, the row counts at the bottom of the Data Source preview must equal
`_manifest.csv` (checklist §2).

---

## 6. Grain, nulls and the date logic

| Topic | Rule in Tableau |
|---|---|
| Grain | Each measure aggregates its own table: orders (99,441), reviews (99,224), stage-valid orders (95,088), people (96,096), cohort cells (400), category × month (1,282), products (32,951), sellers (3,053), seller × category (6,545) |
| Counting rows | `COUNTD([primary key])` for orders, people and sellers. **`COUNT([review_id])` for reviews**, never COUNTD: 814 review rows repeat a `review_id` (pitfall P03) |
| NULL | A blank CSV cell is NULL. `SUM`/`AVG`/`MEDIAN` ignore NULL; `COUNTD` returns 0 for none. Every ratio is guarded `IF den > 0 THEN … END` |
| Unobserved cohort cells | 190 cells have NULL `active_customers` and stay **blank** in the matrix (never 0) |
| Pre-arrival flag | `review_before_delivery` is NULL for 2,865 reviews of undelivered orders, 1 for 4,795 and 0 for 91,564 |
| Months | `Order Month = DATETRUNC('month', [order_date])`. November 2016 has **no orders**, so on a discrete month axis it is simply absent. M09–M11 guard against it with `DATEDIFF` (pitfall P01) |
| Stable window | `in_stable_window = 1` (2017-01 to 2018-08, the 20 complete months). Trend sheets filter on it; growth and moving-average fields return NULL outside it |
| Future cohort months | Cohorts run 2017-01 … 2018-08 with offsets 0–19; activity after 2018-08 is unobserved (right-censored), hence blank cells and the mandatory caption |

---

## 7. Extract, packaging and publishing

> **Automated (2026-11-28).** `tableau/scripts/build_tableau_extracts.py` builds one `.hyper` extract per
> data source with the Tableau Hyper API and writes `RetailPulse_Final.twbx`. In it each data source
> connects to its extract inside the package, which is what Tableau Public requires (error 3C242D89
> otherwise). Every value is checked against the CSVs by `validate_tableau_extracts.py`. The
> notes below apply to a hand-built workbook.

* For each data source, set **Connection: Extract** (top right of the Data Source
  page). The free edition publishes an extract anyway: "the publishing process
  creates an extract of the data connection" (Tableau help, *Save Workbooks to
  Tableau Public*). Building on the extract means you test exactly what will be
  published.
* Save locally as a **packaged workbook** (data included) in `tableau/`. The free
  edition "can choose to either save workbooks to Tableau Public, or save
  workbooks locally".
* **Everything published to Tableau Public is public**, including the data, which
  anyone can download. See `mac_implementation_guide.md` §11 for the safety
  checklist and the dataset licence attribution (CC BY-NC-SA 4.0).

---

## 8. Model validation (what is done, what is pending)

| Check | Status |
|---|---|
| CSVs, row counts, MD5, keys, orphans, blanks | ✅ `check_tableau_data.py` 24/24 · `validate_tableau_sources.py` 90/90 |
| Every formula field reference exists after renames | ✅ `validate_tableau_calcs.py` static checks |
| 90 measures in Tableau semantics vs SQL (223 reference contexts) | ✅ `validate_tableau_calcs.py` 264/264 (logic only) |
| Generated workbook: XSD 2026.3, 8 relationships, captions, types, 100 formulas identical to the validated registry | ✅ `validate_tableau_workbook.py` 16/16 (structure only) |
| Workbook opens in Tableau Desktop and shows the expected KPI values | 🔲 in Tableau (**runtime test pending**) |
| Card values equal `tableau_completion_checklist.md` §4 | 🔲 in Tableau (**runtime test pending**) |
