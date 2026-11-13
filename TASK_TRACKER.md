# RetailPulse — Task Tracker

**Legend:** `[ ]` pending · `[~]` in progress · `[x]` done · `[!]` blocked

**Last updated:** 2026-11-12
**Current phase:** ✅ Phase 1 COMPLETE → ready for Phase 2
**Overall progress:** Environment built, all 9 tables profiled, keys and
relationships validated, 17 data quality issues logged, 25 KPIs defined and
26 business questions scoped. No data has been modified.

---

## Phase 1 — Project Setup & Dataset Understanding

| # | Task | Status | Notes |
|---|---|---|---|
| 1.1 | Inspect workspace | [x] | Folder was empty, not a git repo |
| 1.2 | Audit available tooling | [x] | Python 3.14 + 3.10 and Git present. pandas, Jupyter, MySQL, Excel, Kaggle CLI all missing |
| 1.3 | Create folder structure | [x] | 11 directories created |
| 1.4 | Create PROJECT_PLAN.md | [x] | All 9 phases documented |
| 1.5 | Create README.md | [x] | Initial overview; expanded in Phase 8 |
| 1.6 | Create TASK_TRACKER.md | [x] | This file |
| 1.7 | Create requirements.txt | [x] | Not installed yet — Phase 3 |
| 1.8 | Create .gitignore | [x] | Raw data and venv excluded |
| 1.9 | Write dataset download guide | [x] | `documentation/dataset_setup.md` |
| 1.10 | Write environment setup guide | [x] | `documentation/environment_setup.md` — covers the missing tools |
| 1.11 | **Download Olist dataset into `dataset/raw/`** | [x] | Extracted from `~/Desktop/archive.zip` on 2026-11-12 |
| 1.12 | Verify downloaded files (count, size, readability) | [x] | 9/9 files present, all readable, row counts + headers confirmed |
| 1.13 | Inspect every CSV: shape, columns, dtypes, nulls | [x] | All 9 tables, 52 columns profiled in `01_data_exploration.ipynb` |
| 1.14 | Map table relationships | [x] | 13 PK candidates + 7 FK relationships tested. 6 of 7 have zero orphans |
| 1.15 | Write `documentation/data_dictionary.md` | [x] | All 9 tables, measured values only |
| 1.16 | Write `documentation/business_questions.md` | [x] | 26 questions (15 P1), plus 9 the data cannot answer |
| 1.17 | Write `documentation/kpi_definitions.md` | [x] | 25 KPIs with formula, columns, validation, limitations |
| 1.18 | Write `documentation/architecture.md` | [ ] | Deferred to Phase 3 — schema is clearer once cleaning rules are fixed |
| 1.19 | Initialise git repository | [ ] | Not yet done — offered, awaiting your go-ahead |
| 1.20 | Phase 1 review gate | [x] | Notebook executes end-to-end, 0 errors, 26/26 cells |
| 1.21 | Write `documentation/data_quality_report.md` | [x] | 17 issues: 4 High, 3 Medium, 9 Low, 1 Info |
| 1.22 | Write `documentation/table_relationships.md` | [x] | PK/FK test results + ER diagram + join rules |
| 1.23 | Register Jupyter kernel | [x] | Kernel name `retailpulse` |

---

## Phase 2 — Excel Data Exploration

| # | Task | Status | Notes |
|---|---|---|---|
| 2.1 | Choose spreadsheet tool | [ ] | Excel not installed — LibreOffice recommended. All business tables fit a sheet; geolocation (1.00M rows) is Python-only |
| 2.2 | Missing-value audit per column | [ ] | |
| 2.3 | Duplicate ID check | [ ] | |
| 2.4 | Distribution review: price, freight, review score | [ ] | |
| 2.5 | Pivot: revenue by month | [ ] | |
| 2.6 | Pivot: orders by status | [ ] | |
| 2.7 | Pivot: orders by state | [ ] | |
| 2.8 | Record manual baseline metrics | [ ] | Used to verify Python later |
| 2.9 | Write `reports/excel_exploration_report.md` | [ ] | |
| 2.10 | Phase 2 review gate | [ ] | |

---

## Phase 3 — Python Data Cleaning

| # | Task | Status | Notes |
|---|---|---|---|
| 3.1 | Create virtual environment | [x] | `venv/` on Python 3.14.3 (done early — Phase 1 needed pandas) |
| 3.2 | Install dependencies from requirements.txt | [~] | Phase 1–3 packages installed. MySQL/Excel packages deferred to their phases |
| 3.3 | `01_data_exploration.ipynb` | [x] | 49 cells, 5 charts, executes clean end-to-end |
| 3.4 | Null-handling rule per column, documented | [ ] | |
| 3.5 | Duplicate resolution | [ ] | |
| 3.6 | Data type corrections | [ ] | |
| 3.7 | Referential integrity checks | [ ] | |
| 3.8 | Derived columns | [ ] | revenue, delivery_days, delay_days, on_time flag, order_month |
| 3.9 | Revenue-eligible status rule, documented | [ ] | |
| 3.10 | `02_data_cleaning.ipynb` | [ ] | |
| 3.11 | Export cleaned tables | [ ] | |
| 3.12 | Post-clean validation log | [ ] | |
| 3.13 | Phase 3 review gate | [ ] | |

---

## Phase 4 — MySQL Database Development

| # | Task | Status | Notes |
|---|---|---|---|
| 4.1 | Install / provision MySQL | [ ] | Not currently installed |
| 4.2 | Design relational schema | [ ] | |
| 4.3 | `sql/01_schema.sql` | [ ] | PKs, FKs, indexes |
| 4.4 | `sql/02_data_load.sql` | [ ] | |
| 4.5 | Validate row counts vs Python | [ ] | |
| 4.6 | Module 1 queries | [ ] | |
| 4.7 | Module 2 queries | [ ] | |
| 4.8 | Module 3 queries | [ ] | |
| 4.9 | Module 4 queries | [ ] | |
| 4.10 | Module 5 queries | [ ] | |
| 4.11 | Module 6 queries | [ ] | |
| 4.12 | Advanced queries: CTEs, window functions | [ ] | |
| 4.13 | Save real query results | [ ] | |
| 4.14 | Phase 4 review gate | [ ] | |

---

## Phase 5 — Exploratory Data Analysis

| # | Task | Status | Notes |
|---|---|---|---|
| 5.1 | Sales trend analysis | [ ] | |
| 5.2 | Customer behaviour analysis | [ ] | |
| 5.3 | Product analysis | [ ] | |
| 5.4 | Seller analysis | [ ] | |
| 5.5 | Delivery analysis | [ ] | |
| 5.6 | Review analysis | [ ] | |
| 5.7 | RFM segmentation + methodology writeup | [ ] | |
| 5.8 | Cohort & retention analysis | [ ] | |
| 5.9 | Delay vs rating relationship | [ ] | |
| 5.10 | Phase 5 review gate | [ ] | |

---

## Phase 6 — Power BI Dashboards

| # | Task | Status | Notes |
|---|---|---|---|
| 6.1 | Install Power BI Desktop | [ ] | Windows-only — see environment guide |
| 6.2 | Load data, build model + date table | [ ] | |
| 6.3 | Power Query transformations | [ ] | |
| 6.4 | DAX measures | [ ] | |
| 6.5 | Page 1 Executive Overview | [ ] | |
| 6.6 | Page 2 Customer Intelligence | [ ] | |
| 6.7 | Page 3 Product Analytics | [ ] | |
| 6.8 | Page 4 Seller Performance | [ ] | |
| 6.9 | Page 5 Order & Delivery Operations | [ ] | |
| 6.10 | Page 6 Customer Satisfaction | [ ] | |
| 6.11 | Slicers, drill-through, tooltips | [ ] | |
| 6.12 | Apply charcoal / white / orange theme | [ ] | |
| 6.13 | Capture screenshots | [ ] | |
| 6.14 | Phase 6 review gate | [ ] | |

---

## Phase 7 — Business Insights

| # | Task | Status | Notes |
|---|---|---|---|
| 7.1 | Draft 10-15 insights in the 5-part format | [ ] | |
| 7.2 | Verify every number against source query | [ ] | |
| 7.3 | Write `reports/business_insights.md` | [ ] | |
| 7.4 | Phase 7 review gate | [ ] | |

---

## Phase 8 — Final Documentation & GitHub

| # | Task | Status | Notes |
|---|---|---|---|
| 8.1 | Expand README to portfolio standard | [ ] | |
| 8.2 | Complete `methodology.md` | [ ] | |
| 8.3 | Write `limitations.md` | [ ] | |
| 8.4 | Setup / reproduction instructions | [ ] | |
| 8.5 | Embed dashboard screenshots | [ ] | |
| 8.6 | Push to GitHub | [ ] | |
| 8.7 | Phase 8 review gate | [ ] | |

---

## Phase 9 — Resume & Interview Preparation

| # | Task | Status | Notes |
|---|---|---|---|
| 9.1 | ATS-friendly project description | [ ] | |
| 9.2 | 2-3 quantified resume bullets | [ ] | Real numbers only |
| 9.3 | Architecture walkthrough script | [ ] | |
| 9.4 | SQL interview question bank | [ ] | |
| 9.5 | Python interview question bank | [ ] | |
| 9.6 | Power BI / DAX question bank | [ ] | |
| 9.7 | Business case questions | [ ] | |
| 9.8 | Decision rationale document | [ ] | |

---

## Open decisions

Recorded here so they are made deliberately, not by accident.

| Decision | Options | Status |
|---|---|---|
| Spreadsheet tool for Phase 2 | LibreOffice Calc (free, full pivot tables) · Numbers (installed, weaker pivots) · Excel 365 trial | Pending |
| MySQL installation route | Homebrew `mysql` · Docker container · MySQL Workbench bundle | Pending |
| Power BI access on macOS | Windows VM (Parallels/UTM) · cloud Windows VM · Power BI Service web authoring · Tableau Public substitute | Pending |
| Python version for the venv | 3.10 · **3.14** | ✅ **Resolved: 3.14.3.** Prebuilt wheels confirmed for the whole stack, and 3.10 reached end-of-life in Oct 2026 |

---

## Verified dataset inventory

Confirmed by reading the actual files on 2026-11-12. This supersedes any
expected-contents list elsewhere in the documentation.

| File | Data rows | Size | Columns |
|---|---|---|---|
| olist_customers_dataset.csv | 99,441 | 8.6M | 5 |
| olist_geolocation_dataset.csv | 1,000,163 | 58M | 5 |
| olist_order_items_dataset.csv | 112,650 | 15M | 7 |
| olist_order_payments_dataset.csv | 103,886 | 5.5M | 5 |
| olist_order_reviews_dataset.csv | 99,224 | 14M | 7 |
| olist_orders_dataset.csv | 99,441 | 17M | 8 |
| olist_products_dataset.csv | 32,951 | 2.3M | 9 |
| olist_sellers_dataset.csv | 3,095 | 171K | 4 |
| product_category_name_translation.csv | 71 | 2.6K | 2 |

Source archive: `~/Desktop/archive.zip` (43 MB, 9 files, flat structure).

> **Correction (2026-11-12):** the reviews and translation row counts above were
> first measured with `wc -l` and were wrong. `wc -l` counts physical lines;
> 3,852 reviews contain newlines inside the comment text, and the translation
> file has no trailing newline. The values shown are the corrected pandas counts.
> Full explanation in `documentation/data_quality_report.md` (Q17).

### Quirks noted during verification (to handle in Phase 3)

- `product_name_lenght` and `product_description_lenght` are **misspelled in
  the source data**. Keep the original names when loading; rename only in the
  cleaned output, and document the rename.
- `product_category_name_translation.csv` is unquoted and carries a UTF-8 BOM,
  unlike the other eight files which are fully quoted. Load with
  `encoding='utf-8-sig'` to strip the BOM, or the first column name arrives
  with an invisible character attached and joins fail silently.
- `orders` and `customers` both have exactly 99,441 rows, consistent with
  `customer_id` being one-per-order. Needs confirming as a true 1:1 join.
- `order_items` (112,650) exceeds `orders` (99,441), as expected — multiple
  items per order.
- ~~`reviews` exceeds `orders`~~ — **retracted.** Reviews total 99,224, fewer
  than orders. The earlier figure was a `wc -l` artefact. Separately confirmed:
  `review_id` genuinely is **not** unique (789 ids reused) and 547 orders do
  carry multiple reviews — see Q02.

---

## Blockers

None.

---

## Unresolved items carried into later phases

| Item | Phase | Note |
|---|---|---|
| `reviews` has no natural single-column primary key | 4 | Use `(review_id, order_id)` composite, or a surrogate key. Decide when writing the schema |
| City names are unnormalised (4,119 variants) | 3 | Geographic analysis is state-level until this is cleaned |
| 23 orders show delivery before carrier handoff | 3 | Flag only; cause unknowable from the data |
| Are delivery estimates deliberately padded? | 5 | Orders arrive ~11 days early on average. A finding, not a defect — needs Q19 to confirm |
| Portuguese review text | 5 | Sentiment analysis needs a multilingual model. Optional |
| `documentation/architecture.md` | 3 | Deferred — the data flow diagram is more accurate once cleaning rules are final |
| Git repository not yet initialised | 1 | Awaiting your go-ahead |
