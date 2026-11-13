# RetailPulse

**E-Commerce Business Intelligence & Customer Analytics Platform**

An end-to-end analytics project built on ~100,000 real Brazilian e-commerce
orders. Raw CSV files are cleaned in Python, modelled in MySQL, analysed with
SQL and pandas, and delivered as a six-page interactive Power BI dashboard
with evidence-backed business recommendations.

> **Status:** 🚧 In development — **Phases 1–3 of 9 complete.**
> Dataset profiled · spreadsheet validation passed (17/17 KPIs) · data cleaned
> (34/34 checks, 0 rows deleted). Next: Phase 4, MySQL.
> This README is expanded into its final portfolio form in Phase 8.

---

## Problem statement

An online marketplace generates transaction data continuously, but raw order
tables do not tell management anything on their own. Leadership needs to know
where revenue comes from, which customers are worth retaining, which sellers
damage the customer experience, and whether delivery performance is costing
the business satisfaction and repeat purchases.

RetailPulse builds the analytical layer that answers those questions from
transaction data alone — and, critically, documents the method behind every
number so the conclusions can be challenged and reproduced.

---

## Dataset

**Brazilian E-Commerce Public Dataset by Olist**
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Approximately 100,000 orders placed between 2016 and 2018 on the Olist
marketplace, published by Olist under a CC BY-NC-SA 4.0 licence. The data is
anonymised and spread across multiple related CSV files covering orders,
order items, customers, products, sellers, payments, reviews, and geolocation.

**Profiled 2026-11-12 — measured, not quoted from the dataset description:**

| | |
|---|---|
| Tables | 9 |
| Total rows | 1,551,933 |
| Orders | 99,441 (97.0% delivered) |
| Distinct customers | 96,096 — only **3.12%** ordered more than once |
| Product revenue (GMV) | 13,591,643.70 BRL |
| Date range | 2016-09-04 → 2018-10-17 (stable window 2017-01 → 2018-08) |
| Referential integrity | Zero orphans in 6 of 7 relationships |
| Data quality issues | 17 logged (4 High, 3 Medium, 9 Low, 1 Info) |

Full detail: [`data_dictionary.md`](documentation/data_dictionary.md) ·
[`data_quality_report.md`](documentation/data_quality_report.md) ·
[`table_relationships.md`](documentation/table_relationships.md) ·
[`kpi_definitions.md`](documentation/kpi_definitions.md) ·
[`business_questions.md`](documentation/business_questions.md)

Raw data is **not committed to this repository** (licence and file size).
See [`documentation/dataset_setup.md`](documentation/dataset_setup.md) to
obtain it.

---

## Technology stack

| Purpose | Tool |
|---|---|
| Initial exploration & validation | Excel / LibreOffice Calc |
| Data cleaning & transformation | Python 3, pandas, NumPy |
| Exploratory visualisation | Matplotlib, Seaborn |
| Interactive analysis | Jupyter Lab |
| Database & SQL analysis | MySQL 8 |
| Dashboards | Power BI Desktop |
| Business metrics | DAX |
| Version control | Git, GitHub |

---

## Analytical modules

1. **Executive Business Overview** — revenue, orders, customers, average order
   value, monthly trends, month-over-month and year-over-year growth,
   geographic performance, top categories
2. **Customer Intelligence & Retention** — new vs returning, repeat purchase
   rate, purchase frequency, RFM segmentation, customer lifetime value proxy,
   cohort analysis, retention, high-value customer identification
3. **Product & Category Intelligence** — best and worst sellers, category
   revenue, order frequency, revenue contribution, performance ranking,
   monthly category trends
4. **Seller Performance Analytics** — seller revenue, order volume, average
   delivery time, late delivery rate, review scores, comparative scorecards
5. **Order & Delivery Operations** — status mix, cancellations, delays,
   on-time rate, estimated vs actual delivery, performance by location,
   freight cost analysis
6. **Customer Satisfaction & Reviews** — average rating, rating distribution,
   1-star and 5-star analysis, review trends, ratings by category, and the
   relationship between delivery delay and rating

---

## Project structure

```
RetailPulse/
├── dataset/
│   ├── raw/          # Original Olist CSVs (not committed)
│   ├── interim/      # Mid-pipeline outputs
│   └── cleaned/      # Analysis-ready tables
├── notebooks/
│   ├── 01_data_exploration.ipynb   # ✅ Phase 1 profiling (49 cells)
│   └── 02_data_cleaning.ipynb      # ✅ Phase 3 cleaning (42 cells, 34/34 checks)
├── sql/              # Schema, data load, and analytical queries
├── scripts/          # Reusable Python utilities
├── excel/            # Phase 2 exploration workbooks
├── powerbi/          # RetailPulse.pbix and theme JSON
├── reports/
│   ├── business_insights.md
│   └── dashboard_screenshots/
├── documentation/    # Data dictionary, KPI definitions, methodology
├── requirements.txt
├── PROJECT_PLAN.md   # All 9 phases and their deliverables
├── TASK_TRACKER.md   # Live task status
└── README.md
```

---

## Methodology

The project follows a nine-phase pipeline. Full detail in
[`PROJECT_PLAN.md`](PROJECT_PLAN.md).

```
Raw CSVs  →  Excel exploration  →  Python cleaning  →  MySQL modelling
          →  SQL + pandas analysis  →  Power BI dashboards  →  Insights
```

Four principles govern the work:

- **Nothing is assumed about the data.** Structure is confirmed by reading files.
- **Nothing is fabricated.** Every number traces to a query or notebook cell.
- **Every transformation is validated.** Row counts, key uniqueness, and join
  coverage are checked and logged.
- **Every derived metric is documented.** Formula and assumptions stated,
  with historical fact kept distinct from estimate.

---

## Key findings

_Business insights are produced in Phase 7._ Phase 1 profiling established the
facts the analysis must respect:

- **Only 3.12% of customers ever ordered again.** This is the defining
  constraint of the customer-retention module, and it is reported rather than
  worked around — RFM scoring and CLV methodology are both adapted to it.
- **Delivery looks good for an unexpected reason.** 91.9% of orders arrived on
  or before the estimated date, averaging **11 days early**. That pattern
  suggests deliberately padded estimates rather than fast logistics — a
  distinction Module 5 will test.
- **Review scores are J-shaped**, not bell-shaped: 57.8% five-star and 11.5%
  one-star. The 4.09 average describes almost nobody.
- **Severe seller concentration**: one seller appears on 2,033 order items out
  of 3,095 sellers — a concentration risk worth quantifying.
- **Referential integrity is near-perfect**, so the MySQL schema in Phase 4 can
  declare genuine foreign key constraints.
- **Undelivered orders are savaged in reviews.** Orders still `processing`
  average **1.27 stars** against **4.16** for delivered. Customers are rating
  the wait, not the product — fulfilment, not product quality, dominates
  satisfaction here.
- **Growth is volume, not price.** Like-for-like Jan–Aug, revenue rose
  **+138.3%** and orders **+135.1%**, while AOV moved just **+1.4%**.
- **Revenue is heavily concentrated**: the top 3 of 27 states hold **63.4%**,
  and delivery time varies 2.7× across the country (SP 8.8 days, PA 23.8).

## Business recommendations

_To be completed in Phase 7, each tied to a specific finding._

## Dashboard screenshots

_To be added in Phase 6._

---

## Setup

Full instructions in [`documentation/environment_setup.md`](documentation/environment_setup.md)
and [`documentation/dataset_setup.md`](documentation/dataset_setup.md).

```bash
git clone <repository-url>
cd RetailPulse

python3.14 -m venv venv           # Python 3.14.3 verified; 3.11+ should work
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Place the Olist CSV files in dataset/raw/ — see dataset_setup.md
jupyter lab
```

---

## Limitations

Stated openly rather than discovered by a reviewer:

- Data is historical (2016–2018) and not live.
- No product cost data exists, so profit and margin analysis is not possible.
  Analysis covers revenue and freight cost only.
- `customer_id` is unique per order; `customer_unique_id` identifies the
  person. All repeat-purchase and retention analysis uses the latter.
- Review text is in Portuguese, so sentiment analysis requires translation or
  a multilingual model. Treated as an optional extension.
- Coverage is Brazil-only; conclusions are not globally generalisable.
- **Measured:** only 3.12% of customers placed a second order, which bounds
  cohort, retention and lifetime-value analysis. Reported as a finding rather
  than worked around.
- **Measured:** the dataset's edge months are near-empty (4, 1, 16 and 4 orders)
  and 2016 holds only 329 orders. Trend analysis is therefore restricted to
  2017-01 → 2018-08, and full-year year-over-year growth is not reported.
- On-time delivery is measured against Olist's own estimate, not an objective
  standard, so the rate reflects promise-setting as much as logistics.
- Reviews are attached to orders, not sellers; in a multi-seller order every
  seller inherits the same score.

---

## Licence & attribution

Analysis code in this repository is available for reference and learning.
The underlying dataset belongs to Olist and is used under its Kaggle licence
(CC BY-NC-SA 4.0).

**Author:** Manish
