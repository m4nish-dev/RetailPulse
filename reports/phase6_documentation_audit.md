# RetailPulse — Documentation, Consistency & Readiness Audit

> **HISTORICAL RECORD.** This audit describes the project as it stood on its date. Its references to Power BI, DAX, Windows and the `powerbi/` folder are superseded: the dashboard is now built in **Tableau Public** (see [`../tableau/README.md`](../tableau/README.md)), the analytical CSVs live in `tableau/data/`, and the measure validation is `scripts/validate_tableau_calcs.py`. Kept unchanged as evidence of the checks done at the time; do not follow it as current instructions.


**Date:** 2026-11-20 · **Scope:** all project documentation and reports, checked
against the implementation and against figures recomputed during this audit.
**Result:** documentation corrected and consistent with validated outputs;
validation suite **12 PASS · 0 FAIL · 6 deliberate SKIP**. **The project is not
complete:** the Power BI dashboard, its screenshots, the MT-01 Excel chart and
the final GitHub push remain outstanding.

---

## 1. Files inspected

**Root:** `README.md`, `PROJECT_PLAN.md`, `TASK_TRACKER.md`, `MANUAL_TASKS.md`,
`requirements.txt`, `.env.example`, `.gitignore`.

**documentation/:** `business_questions.md`, `cleaning_decisions.md`,
`data_dictionary.md`, `data_quality_report.md`, `dataset_setup.md`,
`environment_setup.md`, `kpi_definitions.md`, `mysql_schema.md`,
`mysql_setup.md`, `sql_analysis_guide.md`, `table_relationships.md`.

**reports/:** `business_insights.md`, `eda_report.md`, `sql_analysis_report.md`,
`data_cleaning_report.md`, `excel_exploration_report.md`,
`final_project_audit.md`; charts in `eda_charts/` (15) and
`data_quality_charts/` (2).

**powerbi/:** `README.md`, `analytical_sources.md`, `data_model.md`,
`dax_measures.md`, `dax_measure_audit.md`, `dashboard_specification.md`.

**Other:** `dataset/cleaned/README.md`; `sql/07_business_analysis.sql` and
`sql/05_advanced_sql.sql` (for Task 3); the validation runner output;
installed package metadata.

## 2. Files modified or created

| File | Change |
|---|---|
| `README.md` | **Rewritten** as the project landing page (overview, problem, objectives, dataset and limitations, stack, architecture, modules, validated KPIs, findings, secure setup, validation suite, Power BI status, limitations, documentation map) |
| `documentation/project_completion_checklist.md` | **Created** |
| `reports/phase6_documentation_audit.md` | **Created** (this file) |
| `PROJECT_PLAN.md` | Current-status block; AOV denominator corrected; superseded Insight 9 and DAX figures marked; Seaborn noted as unused; Phase 8 checklist updated |
| `TASK_TRACKER.md` | Status updated; corrective fix phases F1–F7 recorded; Phase 8 rows updated; `vw_monthly_revenue` item added; superseded figures marked |
| `documentation/table_relationships.md` | AOV denominator corrected (98,666 → 98,199), history noted |
| `documentation/environment_setup.md` | Python ≥ 3.12 requirement; 3.10 fallback marked obsolete; Seaborn row corrected |
| `documentation/mysql_schema.md`, `documentation/sql_analysis_guide.md` | `vw_monthly_revenue` caveat |
| `reports/eda_report.md` | Notebook cell count (57 cells, 30 code) |
| `reports/final_project_audit.md` | "Historical snapshot" banner only; content preserved |
| `dataset/cleaned/README.md` | 46 checks (was 34); `orders_clean` 38 columns; review flag noted |
| `powerbi/analytical_sources.md`, `powerbi/data_model.md`, `powerbi/README.md` | Money columns labelled BRL (R$ kept only as a display symbol) |
| `requirements.txt` | Minimum Python stated (comment only; no package change) |
| `notebooks/03_exploratory_data_analysis.ipynb` + `reports/eda_charts/B3_cohort_retention_heatmap.png` | Chart presentation only (§5.2); re-executed, all other outputs and charts identical |

## 3. Inconsistencies found and corrected

| # | Where | Problem | Correction |
|---|---|---|---|
| 1 | README | Opening line said the project "is delivered as a six-page interactive Power BI dashboard" | States the dashboard is not built; status table added |
| 2 | README | "Severe seller concentration: one seller appears on 2,033 order items" contradicted Insight 8 (largest seller 1.70% of revenue) | Removed; geography stated as the concentration risk |
| 3 | README | 17 data-quality issues (3 Medium, 1 Info) | 19 issues (4 / 4 / 9 / 2) |
| 4 | README | "Product revenue (GMV) 13,591,643.70" mixed two definitions | Product revenue BRL 13,494,400.74 (eligible, freight excluded) and all-status GMV BRL 13,591,643.70 shown separately |
| 5 | README | Seaborn listed in the stack (removed from the project in Fix-Phase 1) | Removed |
| 6 | README | "Key findings: produced in Phase 7"; stale status block; mixed R$ / BRL | Replaced with validated KPIs and findings, all in BRL |
| 7 | `PROJECT_PLAN.md`, `table_relationships.md` (2 places) | AOV denominator stated as 98,666 | 98,199 eligible orders with items, with history noted |
| 8 | `PROJECT_PLAN.md` | Phase 5 headline "8–15 days late collapses it to 1.73 stars" | Marked superseded; after-arrival figures given |
| 9 | `PROJECT_PLAN.md`, `TASK_TRACKER.md` | 37/37 DAX measures presented as current | Marked superseded: 84 measures, 230/230 |
| 10 | `TASK_TRACKER.md` | Last updated 2026-11-12; no record of the corrective work | Updated; F1–F7 recorded |
| 11 | `environment_setup.md` | Recommended a Python 3.10 fallback | Pinned NumPy requires ≥ 3.12 (checked from package metadata); fallback marked obsolete |
| 12 | `dataset/cleaned/README.md` | 34 checks; "+23 derived columns" | 46 checks; 38 columns (8 original + 30) |
| 13 | `eda_report.md` | Notebook 03 "56 cells, 29 code" | 57 cells, 30 code |
| 14 | Power BI docs | Money columns typed "R$" | BRL |

Phase-by-phase records (e.g. "61/61 checks" at Phase 4, "17 issues" in Phase 1)
were **left as written** where they correctly describe that point in time, and
labelled where a reader could mistake them for current figures.

## 4. KPI and methodology verification

Recomputed during this audit from MySQL (read-only account) and the validated
analytical CSVs, then compared with the documentation:

| # | Decision | Recomputed | Documents |
|---|---|---|---|
| 1 | Eligible orders with items | **98,199** | ✅ consistent (98,666 kept only where it means "orders with items, any status") |
| 2 | Product revenue, freight excluded | **BRL 13,494,400.74** | ✅ |
| 3 | All-status GMV | **BRL 13,591,643.70** | ✅ (README corrected) |
| 4 | Repeat rate, `customer_unique_id` | **3.12%** (2,997 / 96,096) | ✅ |
| 5 | RFM frequency ordinal 1/3/5 | F ∈ {1, 3, 5}; 94,983 scored | ✅ |
| 6 | Calendar-month cohorts, unobserved blank | 190 of 190 unobserved cells NULL | ✅ |
| 7 | Category satisfaction, review once per category | 99,273 category-review links = 98,465 reviews + 808 multi-category duplicates | ✅ |
| 8 | Delivery-stage shares | **3.1867% / 22.6017% / 74.2117%** | ✅ (3.19 / 22.60 / 74.21) |
| 9 | On-time delivery | **91.8871%** of 96,476 (7,827 late) | ✅ |
| 10 | Money labelled BRL | — | ✅ after corrections |

Also confirmed: AOV BRL 137.42; freight BRL 2,241,126.29 (eligible) vs
2,251,909.54 (all statuses); average delivery 12.56 days (96,476) vs stage
total 12.62 days (95,088), with both populations labelled; average review
4.0864. Growth is described as compound monthly growth (+18.0% / −1.5%) and
like-for-like Jan–Aug YoY; no average of monthly % changes is presented as
growth.

## 5. Outstanding technical issues

### 5.1 `vw_monthly_revenue` — a real calculation defect, documented, not fixed

| Column | Problem | Evidence |
|---|---|---|
| `mom_growth_pct` | `LAG()` over the months that exist, so 2017-01 (inside the stable window) is compared with Dec 2016's single 10.90 BRL order | 2017-01 = **+1,101,718.99%** |
| `moving_avg_3m` | `ROWS BETWEEN 2 PRECEDING` spans the missing Nov 2016 and partial edge months | 2017-01 = 54,872.16 BRL (mixes Oct 2016, Dec 2016, Jan 2017); 2017-02 includes Dec 2016 |
| `avg_order_value` | divides by eligible orders **including 8 with no items**, unlike KPI 4 | differs in 4 months: ≤ 0.05 BRL in 2017-11, 2017-12, 2018-02; 1.57 BRL in 2016-10 |

**Classification:** actual defect in the view, with **no current consumer of
the affected values**. No DAX measure uses these columns (M10 and M11 compute
their own and blank the incomplete months). No report figure quotes them
(Insight 1 uses the view's `revenue` column, which is correct).
`sql/08_validation.sql` does not test this view. The view is exported to
`powerbi/data/vw_monthly_revenue.csv`; the data model and dashboard
specification do not use those columns.

**Proposed fix (NOT applied).** It needs an administrator account (the app
account is read-only by design) and a view change counts as a schema change:

```sql
-- inside vw_monthly_revenue, replace the window columns with:
CASE WHEN in_stable_window = 1 THEN
    ROUND(LAG(revenue) OVER (PARTITION BY in_stable_window ORDER BY order_month), 2) END
                                                         AS prev_month_revenue,
CASE WHEN in_stable_window = 1 THEN
    ROUND(100.0 * (revenue - LAG(revenue) OVER (PARTITION BY in_stable_window ORDER BY order_month))
          / NULLIF(LAG(revenue) OVER (PARTITION BY in_stable_window ORDER BY order_month), 0), 2) END
                                                         AS mom_growth_pct,
CASE WHEN in_stable_window = 1
      AND COUNT(*) OVER (PARTITION BY in_stable_window ORDER BY order_month
                         ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) = 3 THEN
    ROUND(AVG(revenue) OVER (PARTITION BY in_stable_window ORDER BY order_month
                             ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) END
                                                         AS moving_avg_3m,
-- and in the monthly CTE, an AOV denominator matching KPI 4:
SUM(CASE WHEN revenue_eligible = 1 AND item_count > 0 THEN 1 ELSE 0 END) AS aov_orders
```

**Impact if applied:** values change only in the window columns for months
outside or at the start of the stable window (2016-09 … 2017-02, 2018-09/10
become NULL), plus four monthly AOV values. Revenue, orders and running total
are unchanged. Afterwards, re-export `powerbi/data/` and re-run
`scripts/run_all_validations.py` (expected unchanged: no check reads these
columns). Rollback: re-run the current `sql/07_business_analysis.sql`.

### 5.2 B3 cohort heatmap — presentation limitation, resolved

Genuine 0% cells (pale orange) and unobservable cells (plain background) looked
almost identical. The data was always correct and matched
`cohort_retention.csv`. **Fixed in the chart code only:** unobservable cells are
now hatched grey with a legend ("not yet observable (after 2018-08)"), and
observed zero cells are labelled "0". Notebook 03 was re-executed: every text
output identical (one blank-line difference), all other 14 charts
byte-identical, 15/15 MySQL checks.

### 5.3 Other known limitations (unchanged, documented)

- **SQL Q21 and Q25:** they filter to the stable window first, so their
  3-month averages for 2017-01 and 2017-02 use partial (1- and 2-month)
  windows. The DAX measure blanks these months instead.
- **MySQL root** still has no password; application code doesn't use it.
  Setting one is the owner's decision.
- **DAX:** syntax and Power BI runtime behaviour are untested (needs Windows).

## 6. Final validation results

`./venv/bin/python scripts/run_all_validations.py` — exit code 0.

| Check | Result |
|---|---|
| App-account connection, read-only session | PASS (`retailpulse_app@127.0.0.1`) |
| Issue register | 19 / 19 |
| `sql/08_validation.sql` | 71 / 71 |
| `sql/03`, `04`, `05`, `06`, `09` | execute without errors |
| Power BI analytical sources | 90 / 90 |
| DAX measure logic | 230 / 230 |
| Notebook 03 | 30 / 30 code cells, 15 / 15 checks |
| Notebook 04 | 17 / 17 code cells, 10 / 10 checks |
| Deliberately skipped | `sql/01`, `02`, `07`, `10`, notebook 02, `export_powerbi_*.py` |

| Security and hygiene check | Result |
|---|---|
| `.env` ignored, never tracked | ✅ |
| Real password in tracked or committable files (89 scanned) | none |
| Secret patterns (private keys, tokens, literal passwords) | none |
| Application code connecting as root | 0 occurrences |
| Stray generated or temporary files | none; only new documentation is untracked |

## 7. Remaining manual tasks

1. **MT-01:** line chart in `excel/RetailPulse_Phase2_Exploration.xlsx`, sheet
   `05_Revenue_By_Month`, Month (column A) × Revenue (column C), 2017-01 to
   2018-08 (`MANUAL_TASKS.md`).
2. **Power BI:** build and test the dashboard on Windows
   (`powerbi/README.md`, `documentation/project_completion_checklist.md` §4).
3. **Screenshots** and final visual verification.
4. **Final GitHub commit and push**, after review.
5. Optional: set a MySQL root password; apply the §5.1 view fix as an administrator.

## 8. Database and datasets not modified

- **No SQL DDL or DML was run in this audit.** All database access used the
  read-only `retailpulse_app` account in `READ ONLY` sessions.
- **The database still holds 9 tables and 7 views** with the expected row counts
  (orders 99,441 · order_items 112,650 · order_payments 103,886 · order_reviews
  99,224 · customers 99,441 · products 32,951 · sellers 3,095 · geolocation
  19,015 · category translation 74).
- **The latest table create/update time is 17:46 on 2026-11-20**, the Fix-Phase 2
  rebuild, before this audit.
- **Raw and cleaned data:** MD5 of every CSV in `dataset/raw/` and
  `dataset/cleaned/` is identical to the Fix-Phase 2 baseline.

## 9. Git status

Latest commit: `b6eb1a6` — *Phase 4 consistency cleanup and Phase 5 security,
automation, reproducibility* (author Manish Kumar; pushed to `origin/main`).

This audit's changes are **uncommitted**, by instruction: the modified files in
§2 plus two new files (`documentation/project_completion_checklist.md`,
`reports/phase6_documentation_audit.md`). Nothing was committed or pushed.
