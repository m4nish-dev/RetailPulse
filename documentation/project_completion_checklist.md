# RetailPulse — Project Completion Checklist

**Updated:** 2026-11-20 (documentation audit) · **Overall status: NOT complete.**
The analysis is complete and validated; the Power BI dashboard, its
screenshots, one manual Excel chart and the final GitHub push are outstanding.

Legend: ✅ done · 🔲 outstanding · ⚠ done with a documented limitation

---

## 1. Completed technical work

| Item | Status | Evidence |
|---|---|---|
| Raw data profiled (9 tables, 1,551,933 rows) | ✅ | `notebooks/01_data_exploration.ipynb` |
| Spreadsheet exploration and KPI cross-check | ✅ | `excel/RetailPulse_Phase2_Exploration.xlsx`, `reports/excel_exploration_report.md` (17/17 computable KPIs) |
| Cleaning: flags, not deletions (0 rows deleted, 0 values imputed) | ✅ | `notebooks/02_data_cleaning.ipynb` (46/46 checks) |
| Data-quality register: 19 issues, recomputed from raw | ✅ | `scripts/verify_issue_register.py` (19/19) |
| Q18 / Q19 timestamp investigation | ✅ | `notebooks/04_data_quality_investigation.ipynb` (10/10) |
| MySQL 8.4 schema, import, 7 views | ✅ | `sql/01`, `02`, `07`; `sql/08_validation.sql` (71/71) |
| 34 analytical SQL queries | ✅ | `sql/03`–`06` |
| EDA, 15 charts | ✅ | `notebooks/03_exploratory_data_analysis.ipynb` (15/15 MySQL checks) |
| Power BI analytical sources (9) | ✅ | `sql/09_powerbi_sources.sql`, `scripts/validate_powerbi_sources.py` (90/90) |
| DAX measures (84) with logic validation | ⚠ | `powerbi/dax_measures.md`, `scripts/validate_dax_logic.py` (230/230). DAX syntax and runtime untested (needs Power BI) |
| Read-only MySQL account `retailpulse_app` | ✅ | `sql/10_app_user.sql` (template), permission tests in Phase 5 |
| Environment-based configuration | ✅ | `.env.example`, `scripts/rp_db.py`, `.env` git-ignored |
| One-command validation | ✅ | `scripts/run_all_validations.py` (12 PASS, 0 FAIL, 6 deliberate SKIP) |

## 2. Validated analytical outputs

| Output | Value | Status |
|---|---|---|
| Eligible orders with items (AOV denominator) | 98,199 | ✅ |
| Product revenue, freight excluded | BRL 13,494,400.74 | ✅ |
| All-status GMV | BRL 13,591,643.70 | ✅ |
| Average order value | BRL 137.42 | ✅ |
| Repeat purchase rate (`customer_unique_id`) | 3.12% (2,997 of 96,096) | ✅ |
| RFM | ordinal F (1/3/5), tie-consistent R and M; 94,983 scored | ✅ |
| Cohorts | calendar months; activity to 2018-08; 190 unobserved cells blank | ✅ |
| Category satisfaction | each review once per category | ✅ |
| Delivery-stage shares | 3.19% / 22.60% / 74.21% (95,088 orders) | ✅ |
| On-time delivery | 91.8871% of 96,476 orders with a delivery date | ✅ |
| 14 business insights, 5 priorities | `reports/business_insights.md` | ✅ |

## 3. Documentation completed

| Item | Status |
|---|---|
| README as project landing page | ✅ |
| KPI definitions, data dictionary, table relationships, schema | ✅ |
| Cleaning decisions and data-quality report (19 issues) | ✅ |
| EDA, SQL, cleaning, Excel and business-insight reports | ✅ |
| Power BI preparation: sources, model, DAX, audit, page spec | ✅ |
| Setup guides: environment, dataset, MySQL (admin vs app account), `.env` | ✅ |
| Documentation audit | ✅ `reports/phase6_documentation_audit.md` |
| Known technical items documented | ⚠ `vw_monthly_revenue` boundary values and monthly AOV (see audit §5) |

## 4. Remaining Power BI work (Windows required)

Detailed procedure and acceptance list: [`powerbi/windows_implementation_guide.md`](../powerbi/windows_implementation_guide.md) · [`powerbi/powerbi_completion_checklist.md`](../powerbi/powerbi_completion_checklist.md) · [`powerbi/dax_implementation_checklist.md`](../powerbi/dax_implementation_checklist.md).

| Item | Status |
|---|---|
| Data readiness for Power BI re-verified on macOS (30/30) | ✅ 2026-11-20 |
| Windows environment with Power BI Desktop | 🔲 |
| Load `powerbi/data/` and `powerbi/data/analytical/`; build the model per `powerbi/data_model.md` (one-to-many, single direction for the analytical tables) | 🔲 |
| Mark `dim_date` as the date table | 🔲 |
| Enter the 84 measures from `powerbi/dax_measures.md`; confirm syntax | 🔲 |
| Build the six pages per `powerbi/dashboard_specification.md`, with mandatory captions | 🔲 |
| Apply `powerbi/RetailPulse_Theme.json` | 🔲 |
| Test card values against `powerbi/dax_validation_results.csv` and the checks in `powerbi/README.md` | 🔲 |
| Capture dashboard screenshots into `reports/dashboard_screenshots/` | 🔲 |
| Final visual verification (slicers, drill-through, blank cohort cells, BRL formatting) | 🔲 |

## 5. Remaining manual Excel work

| Item | Status |
|---|---|
| **MT-01** line chart in `excel/RetailPulse_Phase2_Exploration.xlsx`, sheet `05_Revenue_By_Month`: X = Month (column A), Y = Revenue (column C), **2017-01 to 2018-08 only**. Steps in `MANUAL_TASKS.md` | 🔲 |

## 6. Final GitHub tasks

| Item | Status |
|---|---|
| Review the uncommitted documentation-audit changes | 🔲 |
| Final commit and push (author: you only; no co-author lines) | 🔲 |
| After the dashboard: commit screenshots and the `.pbix` (or document why the `.pbix` is excluded) | 🔲 |
| Confirm `.env`, raw and cleaned data are not tracked | ✅ verified 2026-11-20 |

## 7. Final project quality checks

| Check | Status |
|---|---|
| `scripts/run_all_validations.py` passes | ✅ 2026-11-20 |
| No password or secret in tracked files | ✅ |
| No application code connects as root | ✅ |
| Raw and cleaned datasets unchanged | ✅ |
| Documentation agrees with validated outputs | ✅ (see audit) |
| MySQL root password set (optional, owner's decision) | 🔲 |
| `vw_monthly_revenue` fix applied by an administrator (optional; proposal in audit §5) | 🔲 |
| Re-run the full validation after the Power BI build and before the final push | 🔲 |
