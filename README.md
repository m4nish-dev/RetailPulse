# RetailPulse

**E-Commerce Business Intelligence & Customer Analytics**

An end-to-end analytics project on ~100,000 real Brazilian marketplace orders
(Olist, 2016–2018). Raw CSVs are profiled in a spreadsheet, cleaned and
validated in Python, modelled and analysed in MySQL, explored in pandas, and
turned into business recommendations. A Power BI data model, 90 DAX measures
and a six-page dashboard specification are prepared and logic-validated. **The
dashboard itself has not been built yet** (Power BI Desktop needs Windows).

| Area | Status |
|---|---|
| Data profiling, cleaning, MySQL model, SQL & pandas analysis, 14 business insights | ✅ Complete and validated |
| Data-quality investigation, metric audit, security hardening, one-command validation | ✅ Complete |
| Power BI data sources, data model, DAX measure logic | ✅ Prepared and validated on macOS |
| Power BI dashboard (`.pbix`), screenshots | 🔲 Outstanding — needs Windows |
| Manual Excel revenue chart (MT-01) | 🔲 Outstanding |

Full checklist: [`documentation/project_completion_checklist.md`](documentation/project_completion_checklist.md).

---

## Business problem

An online marketplace generates transaction data continuously, but raw order
tables tell management nothing on their own. Leadership needs to know where
revenue comes from, whether growth is healthy, which customers are worth
retaining, which sellers and categories damage the customer experience, and
whether delivery performance is linked to satisfaction.

## Objectives

1. Build a trustworthy analytical layer from raw transaction data, with every
   number traceable to a query or notebook cell.
2. Answer six business modules (below) with validated KPIs.
3. Turn the analysis into prioritised, evidence-backed recommendations, stating
   associations as associations and limitations openly.
4. Make the work reproducible and verifiable on another machine with one command.

---

## Dataset

**Brazilian E-Commerce Public Dataset by Olist** —
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce (CC BY-NC-SA 4.0).
Nine related CSVs: orders, items, payments, reviews, customers, products,
sellers, category translation and geolocation. Currency: Brazilian real (BRL).

| | |
|---|---|
| Rows across 9 tables | 1,551,933 |
| Orders | 99,441 |
| People (`customer_unique_id`) | 96,096 |
| Date range | 2016-09-04 → 2018-10-17; **trend window 2017-01 → 2018-08** |
| Data-quality issues | **19** logged and verified from raw (4 High, 4 Medium, 9 Low, 2 Info); 0 rows deleted |

Raw data is **not committed** (licence and size). See
[`dataset_setup.md`](documentation/dataset_setup.md).

**Dataset limitations:** historical, not live; no product cost (so no profit or
margin); Brazil only; review text in Portuguese (no sentiment analysis); edge
months are near-empty and November 2016 is missing entirely; `customer_id` is
per order, so people are identified by `customer_unique_id`.

---

## Technology stack

| Purpose | Tool |
|---|---|
| Spreadsheet exploration & KPI cross-check | Excel / LibreOffice Calc (`excel/RetailPulse_Phase2_Exploration.xlsx`) |
| Cleaning, analysis, validation | Python 3.14, pandas, NumPy |
| Charts | Matplotlib |
| Notebooks | Jupyter Lab, nbconvert |
| Database & SQL analysis | MySQL 8.4 (`mysql-connector-python`) |
| Configuration | `python-dotenv` (`.env`, never committed) |
| Dashboard (prepared, not built) | Power BI Desktop, DAX |
| Version control | Git, GitHub |

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
   │                                                        └──►  sql/09 Power BI sources ──► powerbi/data/
   ├──► notebooks/03  EDA (15 charts)   notebooks/04  data-quality investigation
   ▼
reports/business_insights.md  (14 insights, 5 priorities)

scripts/run_all_validations.py  ── re-checks all of it, read-only
```

```
RetailPulse/
├── dataset/          raw/ (not committed) · cleaned/ (generated, not committed) · interim/
├── notebooks/        01 profiling · 02 cleaning · 03 EDA · 04 data-quality investigation
├── sql/              01 schema · 02 import · 03–06 analysis (34 queries) · 07 views ·
│                     08 validation · 09 Power BI sources · 10 app account (template) ·
│                     11 evidence for two recommendations
├── scripts/          rp_db.py (DB config/connection) · run_all_validations.py ·
│                     validators, exporters, workbook builders
├── excel/            spreadsheet exploration workbook
├── powerbi/          data model, DAX measures + audit, dashboard spec, theme,
│                     data/ and data/analytical/ CSV extracts (generated, not committed)
├── reports/          business insights, EDA, SQL, cleaning, Excel reports ·
│                     eda_charts/ (15) · data_quality_charts/ (2) · audits
├── documentation/    KPI definitions, data dictionary, cleaning decisions, data quality,
│                     schema, setup guides, completion checklist
├── .env.example      connection template (copy to .env)
└── requirements.txt
```

---

## Analytical modules

| Module | Delivered |
|---|---|
| 1. Executive overview | Revenue, orders, AOV, compound monthly growth, like-for-like YoY, geography |
| 2. Customers & retention | Repeat rate, purchase frequency, RFM segments (ordinal frequency), historical customer value (not predicted CLV), calendar-month cohorts |
| 3. Products & categories | Category revenue and concentration, growth, product drill-through |
| 4. Sellers | Revenue concentration, weighted delivery and rating scorecards, intervention list |
| 5. Delivery operations | On-time rate, promised vs actual, state performance, delivery-stage breakdown |
| 6. Satisfaction | Review distribution, delay vs rating (with pre-arrival review sensitivity), category satisfaction |

---

## Main KPIs (validated)

All money in **BRL**. Revenue is item price on revenue-eligible orders (status
not canceled or unavailable), **excluding freight**.

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

Definitions: [`kpi_definitions.md`](documentation/kpi_definitions.md).

## Key findings

From [`reports/business_insights.md`](reports/business_insights.md) (14 insights):

- **Growth stalled.** Compound monthly revenue growth was **+18.0%** across 2017
  and **−1.5%** across Jan–Aug 2018. Like-for-like Jan–Aug revenue rose
  **+138.3%**, driven by orders (+137.3%), not basket size (AOV +0.4%,
  BRL 136.55 → 137.14).
- **Customers rarely return.** Only **3.12%** ordered twice, and 30% of those
  second orders came the same day (likely split checkouts): just **2.19%**
  came back on a later day, after a median 72 days. 2017 cohorts returned at
  1.75–4.32% by August 2018. **93%** of the top 1% of spenders bought exactly once.
- **Potential Loyalists, not Champions, hold the value.** RFM: 21,427 Potential
  Loyalists hold **33.6%** of revenue; 951 Champions hold 2.3%.
- **Geography is the concentration risk**: 3 of 27 states hold 63.4% of revenue,
  while the largest seller holds only 1.70%.
- **Late delivery is associated with lower ratings, but survey timing inflates
  it.** 4,795 reviews were answered **before** the parcel arrived (average 1.80
  stars). Counting only reviews after arrival, 1–7 days late averages 3.86 vs
  4.20 on time. Association, not proven cause.
- **The carrier leg is 74.21% of delivery time**; seller dispatch 22.60%.
- **Below-average satisfaction reaches large categories**: 15 of 34 categories
  (45.1% of rated revenue) score below average, counting each review once per
  category. For `bed_bath_table` and `furniture_decor`, the gap persists on
  on-time orders, which points to product rather than delivery.

**Top recommendations:** prevent late deliveries and hold the review survey
until delivery; run a first-to-second purchase programme for Potential
Loyalists within ~3 months of a first order (to test on a holdout group); make
AOV an owned KPI and A/B test a free-shipping threshold (freight is 21% of
product value just above the median order); treat geographic concentration as
the main risk; report the one-star rate beside the average. Each priority is
labelled decision-ready or hypothesis in the insights report.

---

## Setup

Requirements: **Python 3.14** (pins tested on 3.14.3; the pinned NumPy needs ≥ 3.12), **MySQL 8.4**
(Homebrew `mysql@8.4` on macOS), and the 9 Olist CSVs. Detail:
[`environment_setup.md`](documentation/environment_setup.md) ·
[`dataset_setup.md`](documentation/dataset_setup.md) ·
[`mysql_setup.md`](documentation/mysql_setup.md).

```bash
# 1. Python environment
git clone <repository-url> && cd RetailPulse
python3.14 -m venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Data: put the 9 Olist CSVs in dataset/raw/, then generate dataset/cleaned/
jupyter nbconvert --to notebook --execute --inplace notebooks/02_data_cleaning.ipynb
```

### MySQL, configured securely

Two accounts with separate roles:

| Step | Account | Privilege |
|---|---|---|
| Build the database: `sql/01_schema.sql`, `sql/02_import.sql` (needs `--local-infile=1`), `sql/07_business_analysis.sql` | **administrator** (e.g. root), once | full |
| Create the app account: `sql/10_app_user.sql` with **your own** password (placeholder only in the file) | **administrator**, once | full |
| Everything else: scripts, validators, notebooks | **`retailpulse_app`** | `SELECT` on `retailpulse` only |

```bash
cp .env.example .env && chmod 600 .env    # set MYSQL_PASSWORD; .env is git-ignored
python scripts/rp_db.py                   # connection self-test
```

`scripts/rp_db.py` reads `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`,
`MYSQL_USER` and `MYSQL_PASSWORD`, refuses `root`, gives a clear error for any
missing setting, and opens read-only sessions. No credential is stored in any
committed file.

### Validation suite

```bash
python scripts/run_all_validations.py                  # ~3 minutes
python scripts/run_all_validations.py --skip-notebooks
```

Read-only. Prints PASS / FAIL / SKIP and exits with code 1 on any failure. It
checks each count against a recorded baseline:

| Check | Expected |
|---|---|
| App-account connection, read-only session | pass |
| Data-quality issue register (recomputed from raw) | 19 / 19 |
| `sql/08_validation.sql` | 71 / 71 |
| `sql/03`–`06`, `09`, `11` execute as the app account | no errors |
| Power BI analytical sources | 90 / 90 |
| DAX measure logic (90 measures) | 251 / 251 |
| Insight evidence (`sql/11` vs pandas) | 38 / 38 |
| Power BI data readiness (files, 11 relationships, dates, blanks) | 27 / 27 |
| Notebook 03 (30 code cells) · notebook 04 | 15 / 15 · 10 / 10 |

**Never run by the suite** (destructive or regenerating; admin or manual only):
`sql/01`, `sql/02`, `sql/07`, `sql/10`, notebook 02 (rewrites
`dataset/cleaned/`), and the `export_powerbi_*.py` scripts (rewrite
`powerbi/data/`). Notebooks run in a temporary folder, so the committed
notebooks are not rewritten.

### Notebooks

```bash
jupyter lab                                    # interactive
jupyter nbconvert --to notebook --execute --inplace notebooks/03_exploratory_data_analysis.ipynb
```

Notebooks 03 and 04 need `.env` for their MySQL cross-checks.

---

## Power BI dashboard status

**Not built.** No `.pbix` exists and no screenshots have been produced or
simulated. Ready for the build on Windows:

- 7 view extracts + `dim_date`, and 9 validated analytical sources (RFM, cohort
  matrix, product and seller × category drill-through, delivery stages,
  category satisfaction, seller counts, shared category dimension)
- data model with relationships ([`data_model.md`](powerbi/data_model.md))
- 90 DAX measures ([`dax_measures.md`](powerbi/dax_measures.md)); their logic is
  checked against independent SQL in 251 checks, but **DAX syntax and Power BI
  runtime behaviour are untested**
- six-page specification with mandatory captions
  ([`dashboard_specification.md`](powerbi/dashboard_specification.md)) and a theme

Build guide: [`powerbi/README.md`](powerbi/README.md).

---

## Limitations

- Historical data (2016–2018); no cost data, so no profit or margin.
- Trend analysis uses the 20 complete months (2017-01 → 2018-08); full-year YoY
  is not reported because 2016 holds only 329 orders.
- With a 3.12% repeat rate, cohort, retention and RFM frequency analysis carry
  little signal, and customer value is historical, never predicted.
- "On time" is measured against Olist's own, padded estimate.
- Reviews attach to orders, not sellers or products: seller ratings are
  inherited, and category scores mix product and delivery experience.
- 4.98% of reviews on delivered orders were answered before arrival; delay vs
  rating results are shown with and without them.
- Relationships are associations; the data cannot establish cause.
- Known technical items (documented, not hidden): the MySQL view
  `vw_monthly_revenue` computes MoM and 3-month averages across the 2016/2017
  data gap and its monthly AOV includes 8 item-less orders. No reported figure
  or DAX measure uses those columns. See
  [`reports/phase6_documentation_audit.md`](reports/phase6_documentation_audit.md).

---

## Documentation map

| Topic | File |
|---|---|
| Business insights and priorities | [`reports/business_insights.md`](reports/business_insights.md) |
| KPI definitions | [`documentation/kpi_definitions.md`](documentation/kpi_definitions.md) |
| Data dictionary · relationships · schema | [`data_dictionary.md`](documentation/data_dictionary.md) · [`table_relationships.md`](documentation/table_relationships.md) · [`mysql_schema.md`](documentation/mysql_schema.md) |
| Data quality and cleaning decisions | [`data_quality_report.md`](documentation/data_quality_report.md) · [`cleaning_decisions.md`](documentation/cleaning_decisions.md) |
| Reports | [`eda_report.md`](reports/eda_report.md) · [`sql_analysis_report.md`](reports/sql_analysis_report.md) · [`data_cleaning_report.md`](reports/data_cleaning_report.md) · [`excel_exploration_report.md`](reports/excel_exploration_report.md) |
| Power BI preparation | [`powerbi/`](powerbi/README.md) |
| Audits | [`final_project_audit.md`](reports/final_project_audit.md) (historical) · [`phase6_documentation_audit.md`](reports/phase6_documentation_audit.md) |

---

## Licence & attribution

Analysis code is available for reference and learning. The dataset belongs to
Olist and is used under its Kaggle licence (CC BY-NC-SA 4.0).

**Author:** Manish
