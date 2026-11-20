# RetailPulse

**E-Commerce Business Intelligence & Customer Analytics Platform**

An end-to-end analytics project built on ~100,000 real Brazilian e-commerce
orders. Raw CSV files are cleaned in Python, modelled in MySQL, analysed with
SQL and pandas, and delivered as a six-page interactive Power BI dashboard
with evidence-backed business recommendations.

> **Status:** 🚧 In development — **Phases 1–5 and 7 of 9 complete; Phase 6 prepared but blocked.**
> Dataset profiled · spreadsheet validation passed (17/17 KPIs) · data cleaned
> (46/46 checks, 0 rows deleted) · MySQL 8.4 database built and validated
> (71/71 checks, 34 queries, 7 views) · data-quality investigation of two
> timestamp issues (notebook 04; register now 19 issues, all verified) · EDA complete (15 charts, 15/15 metrics
> agree with MySQL) · 14 business insights, all 38 claims re-verified ·
> Power BI model, theme and 84 logic-validated DAX measures prepared (audit:
> 15 of the original 49 corrected; 230/230 checks) · six analytical Power BI
> data sources built and validated (90/90 checks).
> **Phase 6's dashboard is blocked: Power BI Desktop requires Windows.**
> Phase 8 is next.
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
│   ├── 02_data_cleaning.ipynb      # ✅ Phase 3 cleaning (44 cells, 46/46 checks)
│   ├── 03_exploratory_data_analysis.ipynb  # ✅ Phase 5 EDA (56 cells, 15 charts)
│   └── 04_data_quality_investigation.ipynb # ✅ Q18/Q19 investigation (10/10 cross-checks)
├── sql/              # ✅ 9 files: schema, import, 34 queries, 7 views, validation, Power BI sources
├── scripts/          # Reusable Python utilities
├── excel/            # Phase 2 exploration workbooks
├── powerbi/          # Model, theme, DAX, page spec, data extracts + analytical sources (no .pbix yet)
├── reports/
│   ├── eda_charts/                 # ✅ 15 analysis charts
│   ├── data_quality_charts/        # ✅ 2 Q18/Q19 investigation charts
│   ├── eda_report.md
│   ├── sql_analysis_report.md
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
- **Growth is volume, not price.** Comparing Jan–Aug 2018 with Jan–Aug 2017
  (revenue-eligible orders with line items), revenue rose **+138.3%** and
  orders **+137.3%**, while average order value was flat at **+0.4%**
  (R$136.55 → R$137.14).
- **Revenue is heavily concentrated**: the top 3 of 27 states hold **63.4%**,
  and delivery time varies 2.8× across the country (SP 8.8 days, AL 24.5).
- **Late delivery is associated with lower ratings, but much of the drop is
  survey timing.** Across all reviews, an order 8–15 days late averages 1.73
  stars. But 4,795 reviews were answered **before the parcel arrived**: Olist
  sends the survey about two days after the promised date. Counting only
  reviews answered after arrival, 1–7 days late averages **3.86** vs 4.20 on
  time, and 8–15 days late **3.66** (n = 106). The association holds; the
  "cliff" was mostly customers rating the wait.
- **Delivery promises are padded, but narrowing.** In Jan 2017 Olist promised
  39.5 days and delivered in 12.6; by Aug 2018 it promised 15.2 and delivered
  in **7.7**. Actual speed improved 39% while the promise tightened 62%.
- **74.2% of delivery time is last-mile carriage** (9.36 of 12.62 days, on the
  95,088 orders whose timestamps are in a valid sequence). Payment approval
  takes 0.40 days — the bottleneck is logistics, not process.
- **Champions hold only 2.4% of revenue.** RFM finds just 979 of them. The
  21,989 "Potential Loyalists" carry **34%** — first-to-second purchase
  conversion matters far more than a loyalty programme.
- **The best customers are not loyal.** The top 10% of spenders hold 41% of
  revenue, yet **93% of the top 1% placed exactly one order**. They are
  strangers who made a single expensive purchase, not customers to reward.
- **Growth stopped.** Compound monthly revenue growth was **+18.0% across 2017**
  (Jan→Dec) and **−1.5% across Jan–Aug 2018** — strong growth, then a slight
  decline, with AOV flat throughout.

## Business recommendations

Full detail in [`reports/business_insights.md`](reports/business_insights.md)
— 14 evidence-backed insights. The top five strategic priorities:

1. **Make "never miss the promised date" the operational goal, and hold the
   review survey until delivery.** Late orders are associated with lower
   ratings, and waiting customers who get surveyed average 1.8 stars;
   earliness is worth nothing.
2. **Build a first-to-second purchase programme** aimed at the 21,917
   "Potential Loyalists" holding 33.9% of revenue — not a VIP tier for the
   982 Champions holding 2.4%.
3. **Make average order value an owned KPI.** It has been flat (+0.4%,
   Jan–Aug like-for-like) while orders more than doubled — basket size is an
   untouched lever.
4. **Treat geographic concentration as the top business risk** — 3 of 27
   states hold 63.4% of revenue.
5. **Report the 1-star rate, not just the 4.09 average**, which hides a
   J-shaped distribution.

## Dashboard screenshots

🚧 **Not yet available.** Power BI Desktop runs only on Windows and this
project was built on macOS. No `.pbix` has been created and no placeholder
images have been fabricated.

Everything that does not depend on the tool is ready and validated: the data
model, a validated theme, 84 DAX measures whose logic has been checked
against independent SQL in 230 filter-context checks, a visual-by-visual specification of all six pages,
and six analytical data sources (RFM, cohort matrix, product and
seller × category drill-through, delivery stages, category satisfaction)
validated 90/90 against an independent pandas rebuild.
See [`powerbi/README.md`](powerbi/README.md) for the build guide and what is
required to finish.

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
