# RetailPulse

**End-to-end E-Commerce Data Analytics: Python · pandas · MySQL · SQL · Tableau Public**

RetailPulse analyses ~100,000 real orders from a Brazilian online marketplace (Olist,
2016–2018). Raw CSVs are profiled and cleaned in Python, modelled and queried in MySQL,
explored in Jupyter notebooks, and turned into 14 evidence-backed business insights.
Every number traces to a query or notebook cell and is re-checked by one validation
command. The interactive dashboard is designed for **Tableau Public**. A Tableau workbook
is **generated from code**. It contains the six data sources, relationships, field names, types,
2 parameters, 90 measures plus 10 helper fields, and KPI check sheets. It is validated against
Tableau's official 2026.3 schema, and its formulas against independent SQL.
**The chart sheets and dashboards have not been built or published yet.**

| Area | Status |
|---|---|
| Data profiling, cleaning, MySQL model, SQL and pandas analysis, 14 business insights | ✅ Complete and validated |
| Data-quality investigation, metric audit, security hardening, one-command validation | ✅ Complete |
| Tableau data sources, data model, 90 calculated fields (logic), dashboard specification, Mac build guide | ✅ Prepared and validated on macOS |
| Generated Tableau workbook (`tableau/RetailPulse.twb`: model, formulas, parameters, KPI check sheets) | ✅ Generated and schema-validated; opening it in Tableau is the first manual check |
| Tableau chart sheets and 8 dashboards, runtime test, publication on Tableau Public, screenshots | 🔲 Manual, in Tableau Desktop Public Edition |
| Manual Excel revenue chart (MT-01) | 🔲 Optional |

Full checklist: [`documentation/project_completion_checklist.md`](documentation/project_completion_checklist.md) ·
remaining manual steps: [`MANUAL_TASKS.md`](MANUAL_TASKS.md).

---

## Business problem

An online marketplace generates transaction data continuously, but raw order tables
tell management nothing on their own. Leadership needs to know:
- where revenue comes from, and whether growth is healthy
- which customers are worth retaining
- which sellers and categories damage the customer experience
- whether delivery performance is linked to satisfaction

## Objectives

1. Build a trustworthy analytical layer from raw transaction data, with every number
   traceable to a query or notebook cell.
2. Answer six business modules with validated KPIs.
3. Turn the analysis into prioritised, evidence-backed recommendations. State
   associations as associations, and state limitations openly.
4. Make the work reproducible and verifiable on another machine with one command.

---

## Dataset

**Brazilian E-Commerce Public Dataset by Olist**:
<https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce> (CC BY-NC-SA 4.0).
Nine related CSVs: orders, items, payments, reviews, customers, products, sellers,
category translation and geolocation. Currency: Brazilian real (BRL).

| | |
|---|---|
| Rows across 9 tables | 1,551,933 |
| Orders | 99,441 |
| People (`customer_unique_id`) | 96,096 |
| Date range | 2016-09-04 → 2018-10-17; **trend window 2017-01 → 2018-08** (the 20 complete months) |
| Data-quality issues | **19** logged and verified from raw (4 High, 4 Medium, 9 Low, 2 Info); 0 rows deleted |

Raw data is **not committed** (licence and size): see
[`dataset_setup.md`](documentation/dataset_setup.md).

**Limitations of the data**
- It is historical, not live.
- There is no product cost, so no profit or margin can be calculated.
- It covers Brazil only.
- Review text is in Portuguese, so there is no sentiment analysis.
- The edge months are near-empty, and November 2016 is missing entirely.
- `customer_id` is per order, so people are identified by `customer_unique_id`.

---

## Technology stack

| Purpose | Tool |
|---|---|
| Cleaning, analysis, validation | Python 3.14, pandas, NumPy |
| Notebooks and charts | Jupyter Lab, nbconvert, Matplotlib |
| Database and SQL analysis | MySQL 8.4 (`mysql-connector-python`), window functions, CTEs, views |
| Dashboard | **Tableau Desktop Public Edition → Tableau Public** (relationships, LOD expressions, table calculations, parameter actions) |
| Spreadsheet cross-check | Excel / LibreOffice Calc (`excel/RetailPulse_Phase2_Exploration.xlsx`) |
| Configuration and security | `python-dotenv` (`.env`, never committed), read-only MySQL account |
| Version control | Git, GitHub |

---

## Methodology

| Step | What was done | Evidence |
|---|---|---|
| 1. Profile | 9 raw tables profiled; 19 data-quality issues logged | `notebooks/01_data_exploration.ipynb`, `documentation/data_quality_report.md` |
| 2. Spreadsheet cross-check | 17 computable KPIs reproduced independently in a workbook | `reports/excel_exploration_report.md` |
| 3. Clean | Flags, not deletions: 0 rows deleted, 0 values imputed, 46 checks | `notebooks/02_data_cleaning.ipynb`, `documentation/cleaning_decisions.md` |
| 4. Model | MySQL 8.4 schema, bulk import, 7 one-row-per-grain views that make revenue fan-out impossible | `sql/01`, `sql/02`, `sql/07`; 71 validation checks in `sql/08` |
| 5. Analyse | 34 SQL queries (joins, CTEs, window functions, RFM, cohorts); 15-chart EDA | `sql/03`–`sql/06`, `notebooks/03_exploratory_data_analysis.ipynb` |
| 6. Investigate | Timestamp anomalies and pre-arrival reviews tested for their effect on findings | `notebooks/04_data_quality_investigation.ipynb` |
| 7. Insights | 14 insights in a fixed format (question, method, result, implication, action), each labelled decision-ready or hypothesis | `reports/business_insights.md` |
| 8. Dashboard | Analytical sources exported from SQL; Tableau model and 90 calculated fields validated against independent SQL | `sql/09_dashboard_sources.sql`, `tableau/` |

**Key definitions:**
- **Revenue** is the item price on revenue-eligible orders (status not canceled or unavailable), **excluding freight**. It is **not GMV** and **not profit**.
- **Average order value** divides revenue by the **98,199** eligible orders with items.
- **People** are counted by `customer_unique_id`.
- **Cohorts** use calendar months; future (unobservable) cells stay blank.
- **Customer value** is **historical**, never a predicted lifetime value.
- **Reviews** are counted at review grain; category scores count each review once per category.

All definitions: [`kpi_definitions.md`](documentation/kpi_definitions.md).

---

## Main KPIs (validated)

| KPI | Value | Definition / population |
|---|---|---|
| Product revenue | **BRL 13,494,400.74** | eligible orders, freight excluded |
| All-status GMV | BRL 13,591,643.70 | item price, every order status |
| Freight charged | BRL 2,241,126.29 | eligible orders; reported separately |
| Average order value | **BRL 137.42** | ÷ **98,199** eligible orders with items |
| Median order value | BRL 86.90 | same population |
| People | 96,096 | `customer_unique_id` |
| Repeat purchase rate | **3.12%** | 2,997 people with 2+ orders |
| On-time delivery | **91.8871%** | of 96,476 orders with an actual delivery date (7,827 late) |
| Average delivery time | 12.56 days | same 96,476 orders |
| Delivery-stage shares | **3.19% / 22.60% / 74.21%** | approval / seller dispatch / carrier; 95,088 orders with valid timestamps |
| Average review | 4.0864 | review grain; 11.51% one-star, 57.78% five-star |

## Key findings

From [`reports/business_insights.md`](reports/business_insights.md) (14 insights):

- **Growth stalled.** Compound monthly revenue growth was **+18.0%** across 2017
  and **−1.5%** across Jan–Aug 2018. Like-for-like Jan–Aug revenue rose **+138.3%**.
  The rise came from more orders (+137.3%), not bigger baskets (AOV +0.4%, BRL 136.55 → 137.14).
- **Customers rarely return.** Only **3.12%** ordered twice, and 30% of those second
  orders came the same day (likely split checkouts). Just **2.19%** came back on a
  later day, after a median 72 days. 2017 cohorts returned at 1.75–4.32% by August
  2018. **93%** of the top 1% of spenders bought exactly once.
- **Potential Loyalists, not Champions, hold the value.** RFM: 21,427 Potential
  Loyalists hold **33.6%** of revenue; 951 Champions hold 2.3%.
- **Geography is the concentration risk.** 3 of 27 states hold 63.4% of revenue,
  while the largest seller holds only 1.70%.
- **Late delivery is associated with lower ratings, but survey timing inflates it.**
  4,795 reviews were answered **before** the parcel arrived (average 1.80 stars).
  Counting only reviews written after arrival, 1–7 days late averages 3.86 against
  4.20 on time. This is an association, not a proven cause.
- **The carrier leg is 74.21% of delivery time**; seller dispatch is 22.60%.
- **Below-average satisfaction reaches large categories.** 15 of 34 categories
  (45.1% of rated revenue) score below average, counting each review once per
  category. For `bed_bath_table` and `furniture_decor` the gap persists on on-time
  orders, which points to the product rather than delivery.

**Top recommendations:**
- Prevent late deliveries, and hold the review survey until delivery.
- Run a first-to-second purchase programme for Potential Loyalists within ~3 months
  of a first order (to test on a holdout group).
- Make AOV an owned KPI and A/B test a free-shipping threshold set above the median
  order or by region. At the BRL 86.90 median, half of orders already qualify, and
  full absorption would cost 63.5% of freight.
- Treat geographic concentration as the main risk.
- Report the one-star rate beside the average.

Each priority is labelled decision-ready or hypothesis in the insights report.

---

## Tableau dashboard (prepared; build pending)

Six dashboards and two drill-through dashboards, specified sheet by sheet in
[`tableau/dashboard_specification.md`](tableau/dashboard_specification.md):

| Dashboard | Answers | Data source |
|---|---|---|
| 1 Executive | revenue, orders, AOV and median, monthly trend and MoM %, states, top categories, Jan–Aug YoY | RP Orders |
| 2 Customers | repeat rate, RFM segments (customer vs revenue share), value distribution, cohort retention, frequency | RP Customers, RP Cohorts |
| 3 Products | category revenue, Pareto curve, top-5 trend, growth vs decline, category table | RP Categories |
| 4 Sellers | concentration curve, late-rate vs inherited-rating scatter, intervention list | RP Sellers |
| 5 Operations | on-time rate, promised vs actual delivery, state performance, delivery-stage breakdown | RP Orders |
| 6 Satisfaction | score distribution, delay vs score (all reviews / after arrival), trend, category satisfaction | RP Orders, RP Categories |
| 7 Category Detail | drill-through from Products (parameter action) | RP Categories, RP Sellers |
| 8 Seller Detail | drill-through from Sellers (parameter action) | RP Sellers |

The six data sources, their relationships, the 90 measures as calculated fields and the
step-by-step Mac build guide are in [`tableau/`](tableau/README.md). The workbook
`tableau/RetailPulse.twb` is generated from one registry (`scripts/tableau_registry.py`),
so the formulas in the workbook, the documentation and the validation are identical. The checks:
- the formulas' logic against independent SQL (`scripts/validate_tableau_calcs.py`, 264 checks)
- the workbook against Tableau's published 2026.3 XSD and the registry (`scripts/validate_tableau_workbook.py`, 15 checks)

**Opening it in Tableau and building the charts and dashboards is the remaining manual work.**

**Dashboard access:** not published yet. Once published, the Tableau Public link and
eight real screenshots (`reports/dashboard_screenshots/`) will be added here. No
screenshots exist yet, and none will be simulated.

---

## Architecture

```
dataset/raw (9 Olist CSVs)
   │  notebooks/01  profile            excel/  spreadsheet KPI cross-check
   ▼
notebooks/02  clean + flag (0 rows deleted, 46 checks)  ──►  dataset/cleaned/
   │
   ├──► sql/01–02  MySQL schema + import (admin)  ──►  sql/07 views  ──►  sql/03–06 analysis
   │                                                        │
   │                                                        ├──► scripts/export_tableau_data.py ──► tableau/data/
   │                                                        └──► sql/09 dashboard sources ──► tableau/data/analytical/
   │                                                                                              │
   │                                                                  Tableau Desktop Public Edition ──► Tableau Public
   ├──► notebooks/03  EDA (15 charts)   notebooks/04  data-quality investigation
   ▼
reports/business_insights.md  (14 insights, 5 priorities)

scripts/run_all_validations.py  ── re-checks all of it, read-only
```

## Repository structure

```
RetailPulse/
├── dataset/          raw/ (not committed) · interim/ · cleaned/ (generated, not committed)
├── documentation/    KPI definitions, data dictionary, analytical sources, cleaning decisions,
│                     data quality, schema, business questions, setup guides, completion checklist
├── excel/            spreadsheet exploration workbook
├── notebooks/        01 profiling · 02 cleaning · 03 EDA · 04 data-quality investigation
├── reports/          business insights, EDA, SQL, cleaning, Excel reports, audits ·
│                     eda_charts/ (15) · data_quality_charts/ (2) · dashboard_screenshots/ (pending)
├── scripts/          rp_db.py (DB connection) · run_all_validations.py · validators ·
│                     Tableau registry, exporters and workbook generator · Excel workbook builders
├── sql/              01 schema · 02 import · 03–06 analysis (34 queries) · 07 views · 08 validation ·
│                     09 dashboard sources · 10 app account (template) · 11 insight evidence
├── tableau/          README · data model · calculated fields (generated) · dashboard spec ·
│                     Mac build guide · completion checklist · schema/ (Tableau XSD) ·
│                     data/ (CSV extracts, not committed) · RetailPulse.twb (generated, not committed)
├── .env.example      connection template (copy to .env)
├── LICENSE           MIT, for the project code only (dataset: CC BY-NC-SA 4.0)
├── MANUAL_TASKS.md · PROJECT_PLAN.md · TASK_TRACKER.md
└── requirements.txt
```

---

## Run it locally (macOS)

Requirements:
- **Python 3.14** (pins tested on 3.14.3; the pinned NumPy needs ≥ 3.12)
- **MySQL 8.4** (Homebrew `mysql@8.4`)
- the 9 Olist CSVs
- for the dashboard, **Tableau Desktop Public Edition** (free)

Details: [`environment_setup.md`](documentation/environment_setup.md) ·
[`dataset_setup.md`](documentation/dataset_setup.md) · [`mysql_setup.md`](documentation/mysql_setup.md).

```bash
# 1. Python environment
git clone <repository-url> && cd RetailPulse
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Data: put the 9 Olist CSVs in dataset/raw/, then generate dataset/cleaned/
jupyter nbconvert --to notebook --execute --inplace notebooks/02_data_cleaning.ipynb
```

### MySQL, configured securely

| Step | Account | Privilege |
|---|---|---|
| Build the database: `sql/01_schema.sql`, `sql/02_import.sql` (needs `--local-infile=1`), `sql/07_business_analysis.sql` | **administrator** (e.g. root), once | full |
| Create the app account: `sql/10_app_user.sql` with **your own** password (placeholder only in the file) | **administrator**, once | full |
| Everything else: scripts, validators, notebooks | **`retailpulse_app`** | `SELECT` on `retailpulse` only |

```bash
cp .env.example .env && chmod 600 .env    # set MYSQL_PASSWORD; .env is git-ignored
python scripts/rp_db.py                   # connection self-test
```

`scripts/rp_db.py` reads `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`
and `MYSQL_PASSWORD`, refuses `root`, gives a clear error for any missing setting, and
opens read-only sessions. No credential is stored in any committed file.

### Dashboard data

```bash
python scripts/export_tableau_data.py      # 5 view extracts   -> tableau/data/
python scripts/export_tableau_sources.py   # 9 analytical CSVs -> tableau/data/analytical/
python scripts/build_tableau_workbook.py   # tableau/RetailPulse.twb (data sources, relationships, 100 calcs)
```

Then follow [`tableau/mac_implementation_guide.md`](tableau/mac_implementation_guide.md).

### Validation suite

```bash
python scripts/run_all_validations.py                  # ~4 minutes
python scripts/run_all_validations.py --skip-notebooks
```

Read-only. Prints PASS / FAIL / SKIP and exits with code 1 on any failure. Each count is
compared with a recorded baseline:

| Check | Expected |
|---|---|
| App-account connection, read-only session | pass |
| Data-quality issue register (recomputed from raw) | 19 / 19 |
| `sql/08_validation.sql` | 71 / 71 |
| `sql/03`–`06`, `09`, `11` execute as the app account | no errors |
| Tableau analytical sources (vs live SQL and a pandas rebuild) | 90 / 90 |
| Tableau data readiness (files, MD5, keys, 8 relationships, blanks) | 24 / 24 |
| Tableau calculated fields (90 measures in Tableau semantics vs independent SQL) | 264 / 264 |
| Generated Tableau workbook (official XSD 2026.3, relationships, captions, formulas, sort format) | 16 / 16 |
| Insight evidence (`sql/11` vs pandas) | 78 / 78 |
| Notebook 03 (30 code cells) · notebook 04 | 15 / 15 · 10 / 10 |
| Repository: links, paths, references, secrets, ignores | all pass |

**Never run by the suite** (destructive or regenerating; admin or manual only):
`sql/01`, `sql/02`, `sql/07`, `sql/10`, notebook 02 (rewrites `dataset/cleaned/`), and
the `export_tableau_*.py` scripts (rewrite `tableau/data/`). Notebooks run in a temporary
folder, so the committed notebooks are not rewritten.

### Notebooks

```bash
jupyter lab                                    # interactive
jupyter nbconvert --to notebook --execute --inplace notebooks/03_exploratory_data_analysis.ipynb
```

Notebooks 03 and 04 need `.env` for their MySQL cross-checks.

---

## Limitations

- Historical data (2016–2018); no cost data, so no profit or margin.
- Trend analysis uses the 20 complete months (2017-01 → 2018-08). Full-year YoY is not
  reported, because 2016 holds only 329 orders.
- With a 3.12% repeat rate, cohort, retention and RFM frequency analysis carry little
  signal, and customer value is historical, never predicted.
- "On time" is measured against Olist's own padded estimate.
- Reviews attach to orders, not sellers or products. Seller ratings are inherited, and
  category scores mix product and delivery experience.
- 4.98% of reviews on delivered orders were answered before arrival. Delay-vs-rating
  results are shown with and without them.
- Relationships are associations; the data cannot establish cause.
- Known technical item (documented, not hidden): the MySQL view `vw_monthly_revenue`
  computes MoM and 3-month averages across the 2016/2017 data gap, and its monthly AOV
  includes 8 item-less orders. No reported figure or dashboard measure uses those
  columns. See [`reports/phase6_documentation_audit.md`](reports/phase6_documentation_audit.md).

---

## Documentation map

| Topic | File |
|---|---|
| Business insights and priorities | [`reports/business_insights.md`](reports/business_insights.md) |
| Business questions → answers | [`documentation/business_questions.md`](documentation/business_questions.md) |
| KPI definitions | [`documentation/kpi_definitions.md`](documentation/kpi_definitions.md) |
| Data dictionary · relationships · schema | [`data_dictionary.md`](documentation/data_dictionary.md) · [`table_relationships.md`](documentation/table_relationships.md) · [`mysql_schema.md`](documentation/mysql_schema.md) |
| Analytical sources for the dashboard | [`documentation/analytical_sources.md`](documentation/analytical_sources.md) |
| Data quality and cleaning decisions | [`data_quality_report.md`](documentation/data_quality_report.md) · [`cleaning_decisions.md`](documentation/cleaning_decisions.md) |
| Reports | [`eda_report.md`](reports/eda_report.md) · [`sql_analysis_report.md`](reports/sql_analysis_report.md) · [`data_cleaning_report.md`](reports/data_cleaning_report.md) · [`excel_exploration_report.md`](reports/excel_exploration_report.md) |
| Tableau dashboard | [`tableau/README.md`](tableau/README.md) |
| Audits (historical records) | [`final_project_audit.md`](reports/final_project_audit.md) · [`phase6_documentation_audit.md`](reports/phase6_documentation_audit.md) · [`metric_audit_history.md`](reports/metric_audit_history.md) |

---

## Licence & attribution

This repository contains two kinds of material under **two separate licences**:

| Material | Licence |
|---|---|
| **Original project code**: Python scripts, notebook code, SQL files, Tableau calculated-field definitions | **MIT License**, © 2026 Manish Kumar. See [`LICENSE`](LICENSE) |
| **The Olist dataset**: *Brazilian E-Commerce Public Dataset by Olist* ([Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)) | **CC BY-NC-SA 4.0**, owned by Olist. **Not covered by the MIT License** |

- The raw and cleaned CSVs, and the Tableau data extracts, are **not redistributed** in
  this repository. Download the dataset from Kaggle under its own terms (see
  [`dataset_setup.md`](documentation/dataset_setup.md)).
- Figures, charts, reported results and the published Tableau dashboard are derived from
  the Olist data. If you reuse them, follow the dataset's CC BY-NC-SA 4.0 terms:
  attribution, non-commercial use, share-alike.
- Dataset attribution: Olist, *Brazilian E-Commerce Public Dataset by Olist*, Kaggle,
  CC BY-NC-SA 4.0.

**Author:** Manish Kumar
