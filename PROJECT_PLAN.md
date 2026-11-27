# RetailPulse — Project Plan

**Project type:** E-Commerce Business Intelligence & Customer Analytics
**Dataset:** Brazilian E-Commerce Public Dataset by Olist (Kaggle)
**Owner:** Manish
**Started:** 2026-11-12

> **Current status (2026-11-20).** Phases 1–5 and 7 are complete. The original
> Phase 6 (Power BI) is **prepared but not built**: data sources, data model,
> 90 logic-validated DAX measures and the page specification exist; the
> `.pbix` needs Windows. After the final audit, corrective work was done in
> addition to this plan: metric fixes, a data-quality investigation (issues
> Q18–Q19), Power BI analytical sources, a DAX audit, a consistency cleanup,
> security hardening (read-only MySQL account, `.env`) and a documentation
> audit. Phase-by-phase records below are kept as written at the time; figures
> superseded since are marked. Live checklist:
> `documentation/project_completion_checklist.md`.

---

## 1. Objective

Turn raw, multi-table e-commerce transaction data into validated business
insights and actionable recommendations, delivered through SQL analysis and
interactive Power BI dashboards.

The project answers questions a real business stakeholder would ask:

- Is revenue growing, and where is it coming from?
- Which customers are worth keeping, and which are slipping away?
- Which products and categories carry the business?
- Which sellers help or hurt the customer experience?
- Are we delivering on time, and what does it cost us when we do not?
- What drives customer satisfaction up or down?

---

## 2. Guiding rules

These rules apply to every phase. They are what separate a credible analytics
project from a tutorial.

1. **No fabricated numbers.** Every figure in any document, dashboard, or
   resume bullet must trace back to a query or notebook cell that produced it.
2. **Inspect, never assume.** Column names, data types, and row counts are
   confirmed by reading the actual files.
3. **Validate after every transformation.** Row counts, key uniqueness, and
   join coverage are checked and recorded before moving on.
4. **State methodology.** Any derived metric (RFM scores, CLV proxy, on-time
   definition) is documented with its exact formula and its assumptions.
5. **Separate fact from estimate.** Historical customer value is a fact.
   Lifetime value is a proxy estimate. They are never presented as the same thing.
6. **No profit margins.** The dataset has no product cost data, so margin
   cannot be computed. Revenue and freight cost only.
7. **Phase gate.** A phase is not finished until its deliverables exist and
   have been reviewed.

---

## 3. Technology stack

| Layer | Tool | Role in this project |
|---|---|---|
| Exploration | Excel / LibreOffice Calc | First look, pivot tables, sanity checks |
| Cleaning & analysis | Python 3, pandas, NumPy | Transformations, derived columns, validation |
| Visual exploration | Matplotlib (Seaborn planned, not used) | Distributions, trends, correlations |
| Notebooks | Jupyter Lab | Documented, reproducible analysis |
| Database | MySQL 8 | Relational schema, analytical SQL |
| Dashboards | Power BI Desktop | Six-page interactive BI layer |
| Metrics | DAX | KPI measures, time intelligence |
| Version control | Git + GitHub | History and public portfolio artefact |

Deliberately excluded: machine learning (no genuine business problem requires
it here), web frontends, cloud warehouses, orchestration tools. Scope is held
to what a Data Analyst job description actually asks for.

---

## 4. Analytical modules

| # | Module | Core questions |
|---|---|---|
| 1 | Executive Business Overview | Revenue, orders, customers, AOV, MoM/YoY growth, geography, top categories |
| 2 | Customer Intelligence & Retention | New vs returning, repeat rate, frequency, RFM, CLV proxy, cohorts, retention |
| 3 | Product & Category Intelligence | Best/worst sellers, category revenue, order frequency, contribution, monthly trends |
| 4 | Seller Performance Analytics | Seller revenue, order volume, delivery speed, late rate, review scores, scorecard |
| 5 | Order & Delivery Operations | Status mix, cancellations, delays, on-time rate, estimate vs actual, freight cost |
| 6 | Customer Satisfaction & Reviews | Average rating, distribution, 1 vs 5 star, trends, rating by category, delay-vs-rating link |

### Advanced features (built only after the underlying data is validated)

1. RFM customer segmentation — Champions, Loyal, Potential Loyalists, At Risk, Lost
2. Cohort analysis by first-purchase month
3. Retention curves
4. Seller performance scorecards (composite, weighted)
5. Delivery performance analysis vs promised dates
6. Month-over-month KPI comparison
7. Power BI drill-through
8. Geographic sales analysis by state and city
9. Customer satisfaction driver analysis
10. Evidence-backed business recommendations

---

## 5. Development phases

### Phase 1 — Project Setup & Dataset Understanding
**Goal:** Know exactly what data exists before writing any analysis.

- [x] Inspect workspace and available tooling
- [x] Create folder structure
- [x] Create PROJECT_PLAN.md, README.md, TASK_TRACKER.md
- [x] Download Olist dataset into `dataset/raw/` — 9/9 files
- [x] Build Python environment (`venv`, Python 3.14.3)
- [x] Inspect every CSV: row counts, columns, data types, null counts
- [x] Map table relationships — 13 PK candidates, 7 FK relationships tested
- [x] Write `documentation/data_dictionary.md` from the actual files
- [x] Write `documentation/data_quality_report.md` — 17 issues logged
- [x] Write `documentation/table_relationships.md`
- [x] Write `documentation/business_questions.md` — 26 questions
- [x] Write `documentation/kpi_definitions.md` — 25 KPIs
- [x] ~~Write a separate architecture document~~ — superseded: the architecture diagram is in `README.md` (2026-11-27). Originally **deferred to Phase 3**, where the
      data flow can be drawn against final cleaning rules rather than guessed

**Deliverables:** ✅ folder structure · ✅ data dictionary · ✅ data quality
report · ✅ relationship validation · ✅ business questions · ✅ KPI definitions ·
⏭ architecture (Phase 3)

### Key decisions locked in Phase 1

Each is evidence-based and recorded with its justification:

1. **Revenue** = `SUM(order_items.price)` — excludes freight, excludes
   `canceled`/`unavailable`. Chosen over `payment_value` because only
   `order_items` can be attributed to a product, category or seller.
2. **Customers** are counted on `customer_unique_id` (96,096 people), never
   `customer_id` (99,441 order-level ids).
3. **Trend window** = 2017-01 → 2018-08. The four edge months hold 4, 1, 16 and
   4 orders and would imply a collapse that did not happen.
4. **YoY** is reported only as 2018 Jan–Aug vs 2017 Jan–Aug. 2016 has 329 orders.
5. **AOV denominator** = 98,199 revenue-eligible orders with line items, not
   all 99,441. *(Corrected 2026-11-20: the original text said 98,666, which
   includes canceled and unavailable orders.)*
6. **Delivery denominator** = 96,476 orders with an actual delivery date.
7. **RFM frequency** is scored as a 1/3/5 ordinal, not quintiles — 96.88% of
   customers have exactly one order, so quintiles are impossible.
8. **CLV** is reported as historical value and labelled as such.
9. **No row is ever deleted.** Exclusions are scoped per metric and documented.

---

### Phase 2 — Excel Data Exploration
**Goal:** Build intuition for the data by hand before automating anything.
This matters because Data Analyst interviews still test Excel, and because
eyeballing raw rows catches problems code can hide.

- [ ] Open the main CSVs in a spreadsheet tool
- [ ] Count missing values per column
- [ ] Look for duplicate IDs
- [ ] Inspect distributions of price, freight, review score
- [ ] Build pivot tables: revenue by month, orders by status, orders by state
- [ ] Record headline metrics by hand to later verify the Python pipeline

**Deliverable:** ✅ `reports/excel_exploration_report.md` + `excel/RetailPulse_Phase2_Exploration.xlsx`
(15 sheets, 22 MB, recalculated in LibreOffice Calc 26.8.3.1).

**Result: PASSED.** 17 of 17 computable spreadsheet KPIs reconcile with Python;
0 formula errors. Two KPIs are *not computable* in a spreadsheet at this scale
(distinct customer count, conditional median) — reported as findings and a
concrete reason to move to SQL. One manual chart (MT-01) deferred.

---

### Phase 3 — Python Data Cleaning
**Goal:** Produce trustworthy, analysis-ready tables.

Phase 3 now has a concrete worklist: the 17 issues in
`documentation/data_quality_report.md`, each with a decision already recorded.

- [x] Set up virtual environment and install dependencies *(done in Phase 1)*
- [ ] Load all CSVs, record shapes and dtypes
- [ ] Decide and document a handling rule for every column with nulls
- [ ] Detect and resolve duplicates
- [ ] Convert date columns to real datetimes, IDs to strings, money to float
- [ ] Verify referential integrity (do all foreign keys match a parent row?)
- [ ] Build derived columns: order revenue, delivery days, delay days,
      on-time flag, order month, English category name
- [ ] Decide and document which order statuses count as revenue
- [ ] Export cleaned tables to `dataset/cleaned/`
- [ ] Validate: row counts before/after, no unexpected nulls, totals reconcile

**Deliverables:** ✅ `notebooks/02_data_cleaning.ipynb` (42 cells, executes clean) ·
✅ 9 cleaned tables in `dataset/cleaned/` · ✅ `reports/data_cleaning_report.md` ·
✅ `documentation/cleaning_decisions.md`

**Result: PASSED.** 34/34 validation checks. **0 rows deleted, 0 values
imputed, 0 original columns overwritten.** All 17 issue counts were
independently re-verified from raw before cleaning began.

---

### Phase 4 — MySQL Database Development
**Goal:** Demonstrate relational modelling and real SQL fluency.

- [ ] Install / provision MySQL
- [ ] Design schema with correct data types, primary keys, foreign keys, indexes
- [ ] Write `sql/01_schema.sql`
- [ ] Load cleaned CSVs
- [ ] Validate row counts against the Python output
- [ ] Write 25-30 analytical queries, grouped by module
- [ ] Save each query's actual result for the insights report

Required SQL techniques: `GROUP BY` / `HAVING`, `INNER` and `LEFT JOIN`,
aggregates, `CASE`, subqueries, CTEs, window functions
(`ROW_NUMBER`, `RANK`, `LAG`, running totals), date functions.

**Deliverables:** ✅ 8 SQL files (`01_schema` → `08_validation`) · ✅ 34 executed
queries · ✅ 7 views · ✅ `documentation/mysql_setup.md`, `mysql_schema.md`,
`sql_analysis_guide.md` · ✅ `reports/sql_analysis_report.md`

**Result: PASSED.** MySQL 8.4.13 LTS. 569,776 rows imported with zero warnings.
**61/61 validation checks pass**; revenue reconciles with Python to the cent.
Three real import bugs were found by execution and fixed — two of them would
have silently corrupted data (2 lost review rows, 11 rows diverging on NULLs).

---

### Phase 5 — Exploratory Data Analysis
**Goal:** Find the real story in the data.

- [ ] Sales trends over time, seasonality, growth rates
- [ ] Customer behaviour: order frequency, basket size, payment behaviour
- [ ] Product and category performance
- [ ] Seller distribution and concentration
- [ ] Delivery performance and its drivers
- [ ] Review score analysis
- [ ] RFM segmentation with documented scoring method
- [ ] Cohort and retention analysis
- [ ] Correlation between delivery delay and review score

**Deliverables:** ✅ `notebooks/03_exploratory_data_analysis.ipynb` (56 cells,
executes clean) · ✅ 15 charts in `reports/eda_charts/` · ✅ `reports/eda_report.md`

RFM and cohort analysis are sections B2/B3 of the single notebook rather than
separate files — splitting them would have duplicated the shared customer-grain
setup for no benefit.

**Result: PASSED.** 29/29 cells, 0 errors, **15/15 metrics agree with MySQL**.
Headline finding at the time: an order 1–7 days late loses 1.02 stars and
quadruples 1-star reviews; 8–15 days late averages 1.73 stars. *(Superseded
2026-11-20: much of that drop comes from 4,795 reviews answered before the
parcel arrived; after arrival only, 1–7 days late averages 3.86 and 8–15 days
late 3.66. See Insight 9.)*

---

### Phase 6 — Power BI Dashboards
**Goal:** A BI layer a stakeholder could use without a tour guide.

- [ ] Load cleaned data, build star-schema-style model with a date table
- [ ] Shape in Power Query where needed
- [ ] Write DAX measures for every KPI in `kpi_definitions.md`
- [ ] Page 1 Executive Overview
- [ ] Page 2 Customer Intelligence
- [ ] Page 3 Product Analytics
- [ ] Page 4 Seller Performance
- [ ] Page 5 Order & Delivery Operations
- [ ] Page 6 Customer Satisfaction
- [ ] Add slicers, drill-through, tooltips, conditional formatting
- [ ] Apply theme: dark charcoal background, white text, orange accent
- [ ] Capture screenshots into `reports/dashboard_screenshots/`

**Deliverables:** 🚧 **PARTIAL — the dashboard itself is BLOCKED.**

| Deliverable | Status |
|---|---|
| `powerbi/RetailPulse_Theme.json` | ✅ Built and validated (JSON + CVD checks) |
| `powerbi/dax_measures.md` (37 measures at the time; **84** after the 2026-11-20 audit, **90** on 2026-11-27) | ✅ Logic verified 37/37 then; now **251/251** checks, 15 original measures corrected |
| `powerbi/data_model.md` | ✅ Complete |
| `powerbi/dashboard_specification.md` | ✅ All 6 pages specified |
| `powerbi/data/` (11 CSV extracts) | ✅ Generated, 335,797 rows |
| `powerbi/data/analytical/` (9 sources, added 2026-11-20) | ✅ Validated 90/90 |
| **`powerbi/RetailPulse.pbix`** | ❌ **Does not exist** |
| Dashboard screenshots | ❌ Nothing to capture |

**Power BI Desktop runs only on Windows.** The environment was checked on
2026-11-13 and contains no Windows VM, emulation layer or Power BI install.
No `.pbix` was fabricated and no substitute tool was used.

**Verified as far as macOS permits:** every measure's filter context, grain,
denominator and arithmetic were checked by expressing them as SQL over the
same views Power BI will import — 37/37 agree. *(Since superseded by the
2026-11-20 DAX audit: 84 measures, 230/230 checks against independent SQL; 90 measures, 251/251 since 2026-11-27.)*
DAX *execution* remains untested.

**To finish:** one Windows environment. See `powerbi/README.md`.

---

### Phase 7 — Business Insights
**Goal:** 10-15 insights, each defensible.

Every insight documented in this exact shape:
1. Business question
2. Method (the SQL or Python that produced it)
3. Actual result (real numbers)
4. Business implication
5. Recommended action

**Deliverable:** ✅ [`reports/business_insights.md`](reports/business_insights.md)

**Result: PASSED.** 14 insights, each in the five-part format. **All 38
numeric claims were recomputed from MySQL during QA**, independently of the
Phase 4 and 5 reports — 38/38 agreed. All 23 file references resolve; no
contradictions; no causal claims from correlational evidence; no profit or
margin figures anywhere.

Phase 7 was completed ahead of Phase 6 because Power BI Desktop does not run
on macOS and the dashboard phase is blocked on a Windows environment. The
insights depend only on Phases 4–5, so the ordering costs nothing.

---

### Phase 8 — Final Documentation & GitHub
- [~] Professional README with findings — **done 2026-11-20**; screenshots wait for the dashboard
- [x] Methodology documented (`kpi_definitions.md`, `cleaning_decisions.md`, reports)
- [x] Documented limitations and assumptions
- [x] Setup and reproduction instructions, one-command validation
- [~] Clean commit history, pushed to GitHub — pushed through Phase 5; final push pending

---

### Phase 9 — Resume & Interview Preparation
- [ ] ATS-friendly project description
- [ ] 2-3 quantified resume bullets (real numbers only)
- [ ] Architecture walkthrough script
- [ ] SQL, Python, Power BI interview question banks from this project
- [ ] Business case questions
- [ ] Rationale for every analytical decision made

---

## 6. Known limitations to carry forward

Stated up front so they are never presented as oversights:

- Data covers roughly 2016-2018 and is historical, not live.
- Customer identity: `customer_id` is per-order; `customer_unique_id` is the
  real person. Repeat-purchase analysis must use `customer_unique_id`.
- No product cost data, therefore no profit or margin analysis.
- Review text is in Portuguese; sentiment analysis would need translation or a
  multilingual model. Treated as optional.
- Geography is Brazil only; findings are not globally generalisable.
- **Measured 2026-11-12:** only **3.12%** of customers (2,997 of 96,096) ever
  placed a second order. This bounds cohort, retention and CLV analysis, and
  makes the RFM frequency dimension nearly degenerate. The honest framing of
  that constraint is itself a finding, and is handled explicitly rather than
  worked around.
- **Measured 2026-11-12:** the dataset's edge months are near-empty and 2016
  holds just 329 orders, so trend analysis is restricted to 2017-01 → 2018-08
  and full-year YoY growth is not reported.
