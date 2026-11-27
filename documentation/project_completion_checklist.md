# RetailPulse — Project Completion Checklist

**Updated:** 2026-11-27 (Tableau-only structure) · **Overall status: NOT complete.**
All repository work is done and validated. What remains is the manual work:
- the Tableau dashboard: build, runtime test, publication on Tableau Public, and 8 screenshots
- one optional Excel chart
- the final GitHub push

Legend: ✅ done · 🔲 outstanding (manual) · ⚠ done with a documented limitation

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
| Dashboard data: 5 view extracts + 9 analytical sources in `tableau/data/`, byte-identical re-export, MD5 manifests | ✅ | `scripts/export_tableau_data.py`, `scripts/export_tableau_sources.py`, `scripts/check_tableau_data.py` (24/24) |
| Analytical sources equal live SQL and a pandas rebuild | ✅ | `sql/09_dashboard_sources.sql`, `scripts/validate_tableau_sources.py` (90/90) |
| Tableau data model: 6 data sources, 8 relationships, keys, types, filter rules | ✅ | `tableau/data_model.md` |
| 90 measures as Tableau calculated fields (+10 helpers, 2 parameters), logic validated against independent SQL | ⚠ | `tableau/calculated_fields.md`, `scripts/validate_tableau_calcs.py` (264/264). Tableau syntax and runtime: pending the manual build |
| Tableau workbook generated from code (model, relationships, 100 calculated fields, parameters, 8 KPI check sheets) | ⚠ | `scripts/build_tableau_workbook.py`; `scripts/validate_tableau_workbook.py` (16/16, official XSD 2026.3). Not yet opened in Tableau |
| Read-only MySQL account `retailpulse_app` | ✅ | `sql/10_app_user.sql` (template), permission tests in Phase 5 |
| Environment-based configuration | ✅ | `.env.example`, `scripts/rp_db.py`, `.env` git-ignored |
| Evidence for recommendations (second-purchase timing, freight bands, free-shipping threshold impact, regional freight) | ✅ | `sql/11_insight_evidence.sql`, `scripts/validate_insight_evidence.py` (78/78) |
| Repository checks: links, paths, no retired-tool references, no secrets, ignores | ✅ | `scripts/check_repository.py` |
| One-command validation | ✅ | `scripts/run_all_validations.py` (17 PASS, 0 FAIL, 6 deliberate SKIP; 2026-11-27) |

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
| Category satisfaction | each review once per category; never summed across categories | ✅ |
| Delivery-stage shares | 3.19% / 22.60% / 74.21% (95,088 orders) | ✅ |
| On-time delivery | 91.8871% of 96,476 orders with a delivery date | ✅ |
| Average delivery time · average review | 12.56 days · 4.0864 | ✅ |
| 14 business insights, 5 priorities; every recommendation classified decision-ready or hypothesis | `reports/business_insights.md` | ✅ |
| Business-question answer map (19 answered, 5 partly, 2 not) | `documentation/business_questions.md` | ✅ |

## 3. Documentation completed

| Item | Status |
|---|---|
| README as portfolio landing page | ✅ |
| KPI definitions, data dictionary, table relationships, schema, analytical sources | ✅ |
| Cleaning decisions and data-quality report (19 issues) | ✅ |
| EDA, SQL, cleaning, Excel and business-insight reports | ✅ |
| Tableau package: README, data model, calculated fields, dashboard specification, Mac guide, completion checklist | ✅ `tableau/` |
| Setup guides: environment, dataset, MySQL (admin vs app account), `.env` | ✅ |
| Audits kept as historical records | ✅ `reports/final_project_audit.md`, `reports/phase6_documentation_audit.md`, `reports/metric_audit_history.md` |
| Known technical items documented | ⚠ `vw_monthly_revenue` boundary values and monthly AOV (not used by the dashboard) |

## 4. Remaining dashboard work (Tableau Public, on this Mac): MANUAL PENDING

Procedure: [`tableau/mac_implementation_guide.md`](../tableau/mac_implementation_guide.md) ·
acceptance list: [`tableau/tableau_completion_checklist.md`](../tableau/tableau_completion_checklist.md).

| Item | Status |
|---|---|
| Install Tableau Desktop Public Edition | ✅ 2026.3.2 (Apple silicon) |
| Create a Tableau Public account | 🔲 |
| Open the generated `tableau/RetailPulse.twb`; confirm model and KPI check sheets | 🔲 |
| Build 39 chart/table sheets, 6 dashboards + 2 detail dashboards, filters and actions, mandatory captions | 🔲 |
| Test every value in the Tableau checklist §4 and §6 (runtime test) | 🔲 |
| Publish to Tableau Public after the safety checklist; verify in a private window | 🔲 |
| Capture 8 real screenshots into `reports/dashboard_screenshots/` | 🔲 |

## 5. Remaining manual Excel work (optional)

| Item | Status |
|---|---|
| **MT-01** line chart in `excel/RetailPulse_Phase2_Exploration.xlsx`, sheet `05_Revenue_By_Month`: X = Month (column A), Y = Revenue (column C), **2017-01 to 2018-08 only**. Steps in `MANUAL_TASKS.md` | 🔲 |

## 6. Final GitHub tasks

| Item | Status |
|---|---|
| Review the uncommitted changes (T05/T06 work and the Tableau migration) | 🔲 |
| After the dashboard: README link to the Tableau Public viz and the 8 screenshots | 🔲 |
| Final commit and push (author: you only; no co-author lines) | 🔲 |
| `.env`, raw, cleaned and Tableau data, workbooks and extracts not tracked | ✅ verified 2026-11-27 (`scripts/check_repository.py`) |
| `LICENSE` added: MIT for the original code (© 2026 Manish Kumar); dataset stays CC BY-NC-SA 4.0 | ✅ 2026-11-27 |

## 7. Final project quality checks

| Check | Status |
|---|---|
| `scripts/run_all_validations.py` passes | ✅ 2026-11-27 |
| No password or secret in committable files | ✅ |
| No application code connects as root | ✅ |
| Raw and cleaned datasets unchanged | ✅ |
| Documentation agrees with validated outputs | ✅ |
| MySQL root password set (optional, owner's decision) | 🔲 |
| `vw_monthly_revenue` fix applied by an administrator (optional) | 🔲 |
| Re-run the full validation after the Tableau build and before the final push | 🔲 |
