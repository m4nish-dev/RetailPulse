# RetailPulse — Final Project Audit

> **HISTORICAL RECORD.** This audit describes the project as it stood on its date. Its references to Power BI, DAX, Windows and the `powerbi/` folder are superseded: the dashboard is now built in **Tableau Public** (see [`../tableau/README.md`](../tableau/README.md)), the analytical CSVs live in `tableau/data/`, and the measure validation is `scripts/validate_tableau_calcs.py`. Kept unchanged as evidence of the checks done at the time; do not follow it as current instructions.


> **Historical snapshot (2026-11-20, before the fix phases).** This audit is
> preserved as written. Its findings have since been addressed or explicitly
> carried forward; the current state, and what remains outstanding, are in
> [`phase6_documentation_audit.md`](phase6_documentation_audit.md) and
> [`../documentation/project_completion_checklist.md`](../documentation/project_completion_checklist.md).


**Audit date:** 2026-11-20
**Repository state:** `main` @ `19fff0f`, in sync with `origin/main`, clean working tree
**Method:** read-only inspection plus *execution* of every existing validator, and an
isolated end-to-end reproduction of the pipeline in a scratch directory (raw data
symlinked read-only; nothing inside the project was written except this report).

> **How to read the evidence labels used throughout**
>
> | Label | Meaning |
> |---|---|
> | **[EXECUTED]** | A command was run during this audit and its output observed |
> | **[INSPECTED]** | Code or documentation was read; nothing was run |
> | **[PRIOR]** | Verified in an earlier phase; not re-run in this audit |
>
> Nothing below is called "tested" unless it carries **[EXECUTED]**.

---

## 1. Executive Summary

RetailPulse is **substantially built and its core numbers are trustworthy**. The data
pipeline (raw → cleaned → MySQL → analysis) reproduces byte-for-byte, and three
independent engines (pandas, LibreOffice, MySQL) agree on every headline KPI. That is
the hardest part of a data project, and it is done.

**But the project is not finished, and this audit found real defects** — several of
which were hidden behind green checkmarks.

**What is solid**
- Cleaning pipeline regenerates all 9 cleaned CSVs **byte-identically** from raw **[EXECUTED]**
- MySQL validation **61/61 PASS**, issue register **17/17**, workbook **17/17 KPIs** **[EXECUTED]**
- All 34 SQL queries run with 0 errors; all 3 notebooks re-run with 0 errors **[EXECUTED]**

**What is wrong or missing — the important findings**

| # | Finding | Severity |
|---|---|---|
| 1 | **Power BI dashboard does not exist.** No `.pbix`; blocked on Windows | Blocker |
| 2 | **6 of 14 specified dashboard visuals have no source data** in the Power BI exports — RFM, cohort matrix, both drill-throughs, delivery-stage breakdown, category satisfaction. They would be unbuildable *even on Windows* | Critical |
| 3 | **"AOV fell 13.4%" is an artefact** of comparing two single months. Like-for-like, AOV was flat (136.55 → 137.14, **+0.4%**). The claim appears in the business insights, EDA report and README | Critical (analytical) |
| 4 | **"2018 grew +2.5%/month" is misleading.** That is an arithmetic mean of monthly % changes. Compound monthly growth in 2018 was **−1.53%** | High (analytical) |
| 5 | **"37/37 DAX measures validated" overstates coverage.** 49 measures are defined; 12+ — including *every* time-intelligence measure — are unvalidated, and one (`Revenue 3M Moving Avg`) has a **logic bug** (~30× too small) | High |
| 6 | **The Excel workbook does not reproduce cleanly.** Rebuilding from `scripts/build_phase2_workbook.py` reintroduces the `#VALUE!` error that was hand-patched only in the `.xlsx` | High |
| 7 | **`requirements.txt` is incomplete.** `openpyxl` and `mysql-connector-python` are imported by 5 files but not listed; a fresh install cannot run them | High |
| 8 | **New data-quality issue: 1,350 orders show carrier handoff *before* payment approval.** Not in the issue register; distorts the delivery-stage analysis behind Insight 12 | High |
| 9 | **EDA notebook narrative contradicts its own output** in 3 places (e.g. text says 26 categories reach 80%; computed output says 18) | Medium |
| 10 | **MySQL runs with no root password and `local_infile` left ON**, and two scripts plus a notebook hard-code password-less root, so securing MySQL would break them | Medium |
| 11 | Phase 8 documentation (`methodology.md`, `limitations.md`, `architecture.md`) never created; `data_dictionary.md` references a file that does not exist | Medium |

**No external API, API key, token or cloud account is required by this project.**
The only hard external dependency is a Windows environment for Power BI.

**Technical completion estimate: ~67%** (§15). Not higher, because the single most
visible deliverable — the dashboard — is 0% built, and because several "complete"
items carry correctness defects that must be fixed before they can be called done.

---

## 2. Current Project Architecture

```
dataset/raw/ (9 CSVs, 1,551,933 rows, gitignored, licensed)
   │
   ├─► notebooks/01_data_exploration.ipynb ──► profiling, issue register (17)
   │
   ├─► notebooks/02_data_cleaning.ipynb ─────► dataset/cleaned/ (9 CSVs, 569,776 rows, gitignored)
   │                                              │
   │      scripts/build_phase2_data.py ◄──────────┤ (reads raw)
   │      scripts/build_phase2_workbook.py ──────► excel/RetailPulse_Phase2_Exploration.xlsx
   │      scripts/recalc_workbook.py (LibreOffice)┘
   │                                              │
   │      sql/01_schema.sql + 02_import.sql ◄─────┤
   │                 │                            │
   │      MySQL 8.4 `retailpulse` (9 tables, 7 views, 260.4 MB)
   │                 │
   │      sql/03–06 (34 queries) · 07 (views) · 08 (61 checks)
   │                 │
   │      scripts/export_powerbi_data.py ────────► powerbi/data/ (11 CSVs, gitignored)
   │      scripts/validate_dax_logic.py
   │                 │
   ├─► notebooks/03_exploratory_data_analysis.ipynb ► reports/eda_charts/ (15 PNGs)
   │                                                   + cross-check vs MySQL (15 checks)
   │
   └─► reports/ (6 reports) · documentation/ (12 docs) · powerbi/ (spec files, NO .pbix)
```

**Technology actually used:** Python 3.14.3, pandas 3.1.1, NumPy, Matplotlib,
Jupyter, MySQL 8.4.13, LibreOffice Calc 26.8.3.1 (Excel substitute), openpyxl,
mysql-connector-python. **Seaborn is listed in `requirements.txt` and the original
stack but is never imported anywhere.** Power BI: not available.

**Pipeline orchestration:** none. Each step is run by hand in an order documented
across several files; there is no single runner script.

---

## 3. Phase-by-Phase Completion Status

| Phase | Tracker says | Audit verdict | Evidence |
|---|---|---|---|
| 1 Dataset understanding | Complete | ✅ **Complete & verified** | Issue register 17/17 **[EXECUTED]**; notebook 01 clean **[EXECUTED stored outputs]** |
| 2 Excel exploration | Complete | ⚠️ **Implemented, needs fixing** | Committed workbook 17/17, 0 formula errors **[EXECUTED]** — but regenerating it reintroduces `#VALUE!` **[EXECUTED]**; manual chart MT-01 pending |
| 3 Python cleaning | Complete | ✅ **Complete & verified** | Re-run from raw → 9/9 files byte-identical **[EXECUTED]** |
| 4 MySQL & SQL | Complete | ✅ **Complete, config concerns** | 61/61 PASS **[EXECUTED]**; 34 queries 0 errors **[EXECUTED]**; no root password, `local_infile=1` **[EXECUTED]** |
| 5 EDA | Complete | ⚠️ **Implemented, narrative defects** | Re-run 0 errors, 15/15 vs MySQL **[EXECUTED]**; 3 narrative-vs-output contradictions **[EXECUTED]** |
| 6 Power BI | Blocked | 🚫 **Blocked + prep incomplete** | No `.pbix`; 6/14 visuals lack data; 12+ measures unvalidated; 1 DAX bug |
| 7 Business insights | Complete | ⚠️ **Implemented, 2 claims need correction** | 38/38 claims match MySQL **[PRIOR]**, but 2 headline framings are analytically misleading **[EXECUTED]** |
| 8 Documentation | Not started | ⬜ **Not started** (partial README exists) | Planned docs missing **[EXECUTED file check]** |
| 9 Resume/interview | Not started | — Out of scope for this audit | Excluded per instructions |

---

## 4. Verified Completed Components

Each item below was **executed during this audit** unless marked otherwise.

### 4.1 Data profiling and issue register
- **Supposed to:** profile all 9 tables, validate keys, log data-quality issues.
- **Exists:** `notebooks/01_data_exploration.ipynb` (49 cells), `scripts/profile_raw.py`,
  `scripts/verify_issue_register.py`, `documentation/data_dictionary.md`,
  `data_quality_report.md`, `table_relationships.md`, `cleaning_decisions.md`.
- **Tested:** `verify_issue_register.py` recomputes all 17 issue counts from raw →
  **17 matching, 0 mismatches [EXECUTED]**. Notebook stored outputs: 26/26 cells, 0 errors.
- **Missing:** the new carrier-before-approval anomaly (§7.5) is not in the register.

### 4.2 Cleaning pipeline
- **Supposed to:** produce analysis-ready tables without deleting rows.
- **Exists:** `notebooks/02_data_cleaning.ipynb` (42 cells, 34 internal assertions).
- **Tested:** re-executed in an isolated scratch project against the raw data →
  **all 9 cleaned CSVs byte-identical (MD5) to the committed pipeline output**, in ~10 s
  **[EXECUTED]**. This is strong evidence of determinism and reproducibility.
- **Missing:** nothing material.

### 4.3 MySQL database
- **Supposed to:** relational schema, bulk import, analytical views, validation.
- **Exists:** `sql/01_schema.sql` … `08_validation.sql`; database `retailpulse` live.
- **Tested:** `08_validation.sql` → **61 PASS, 0 FAIL [EXECUTED]**. All four analysis
  files (34 queries) → **0 errors [EXECUTED]**. Exact row counts match **[EXECUTED]**.
- **Not re-tested this audit:** a from-scratch rebuild (would `DROP DATABASE`) — **[PRIOR]**
  done at end of Phase 4 with 61/61.

### 4.4 Committed Excel workbook
- **Exists:** `excel/RetailPulse_Phase2_Exploration.xlsx` (15 sheets, 21.7 MB, live formulas).
- **Tested:** `scripts/recalc_workbook.py` (writes only to a temp dir) →
  **17 KPIs reconcile, 0 mismatches, 0 formula errors [EXECUTED]**.
- **Caveat:** the *committed file* is correct; the *build script* is not (§7.1).

### 4.5 EDA notebook
- **Tested:** re-executed in scratch against regenerated data → **0 errors,
  15/15 MySQL cross-checks PASS, 15 charts written [EXECUTED]**.
- **Caveat:** narrative defects (§7.4).

### 4.6 Power BI preparation assets (not the dashboard)
- `powerbi/RetailPulse_Theme.json` — valid JSON, CVD-validated palette **[PRIOR]**.
- `scripts/export_powerbi_data.py` — **regenerates 335,797 rows + dim_date [EXECUTED in scratch]**.
- `scripts/validate_dax_logic.py` — **37/37 PASS [EXECUTED]** — but see §5.1 for what this
  does and does not cover.

---

## 5. Incomplete Components

### 5.1 Phase 6 — Power BI (BLOCKED, and preparation has gaps)

**Three distinct layers, which must not be confused:**

| Layer | Status | Evidence |
|---|---|---|
| Preparation files (theme, model spec, page spec, data exports) | ⚠️ Exist, **incomplete** | See data-coverage gap below |
| DAX *logic* validation (SQL-equivalent) | ⚠️ **37 of 49 measures** | `validate_dax_logic.py` **[EXECUTED]** |
| A working, tested `.pbix` dashboard | ❌ **Does not exist** | No Windows environment |

**Gap A — 6 of 14 specified visuals have no source data [EXECUTED]**

The page specification asks for visuals that no exported table can feed:

| Specified visual | Why it cannot be built from current exports |
|---|---|
| P2 RFM segmentation | No table contains R/F/M scores or a segment column. `dax_measures.md` says RFM is "scored in Power Query or SQL" but no such view exists |
| P2 Cohort retention matrix | No cohort × months-since-first table exists; `vw_customer_summary` has `cohort_month` only |
| P3 Drill-through: top products per category | No item-level fact exported (`order_items` / product revenue absent) |
| P3 Drill-through: top sellers per category | No seller × category table exported |
| P5 Delivery-stage breakdown | `vw_order_summary` lacks `order_approved_at` and `order_delivered_carrier_date` |
| P6 Category-level satisfaction | No table joins category to review score |

**Gap B — measure coverage [EXECUTED]**
`dax_measures.md` defines **49** measures; the validator covers **37**. Unvalidated:
`Revenue PM`, `Revenue MoM %`, `Revenue 3M Moving Avg`, `Revenue Running Total`,
`YoY Growth Jan-Aug %`, `Category Revenue Share`, `Category Rank`, `Category Items Sold`,
`Segment Revenue Share`, `Customers In Segment`, `Seller Late Rate`,
`Seller Avg Delivery Days`, `Seller Inherited Order Rating`, `Seller Orders`, and others.
The README, plan and tracker say "37 logic-verified measures", which is literally true
but reads as "all measures verified".

**Gap C — one validator check is tautological [EXECUTED]**
`validate_dax_logic.py` line 79 validates `Median Order Value` with `"SELECT 86.90"` — a
constant compared with itself. The median was verified in pandas in Phase 3 **[PRIOR]**,
but this check proves nothing. (The same tautology was used once in the Phase 7 claim
verification.)

**Gap D — data model behaviour not specified**
- `vw_customer_summary → vw_order_summary` is single-direction, so **a date slicer will
  not filter Page 2 customer KPIs**. The specification does not acknowledge this.
- `vw_category_performance`, `vw_delivery_performance`, `vw_seller_performance` are
  deliberately unrelated to `dim_date` (correct, to avoid fan-out) but use a text
  `order_month`, so Pages 3–5 cannot use the shared date slicer.

### 5.2 Phase 2 — Excel
- **Manual chart MT-01** (monthly revenue trend) — pending, yours, by design.
- **Native pivot tables** — none; `11_Pivot_Exercises` sheet specifies 8 for manual
  building. Documented limitation of `openpyxl`, not a defect.
- **Build-script reproducibility bug** — §7.1.

### 5.3 Phase 7 — Business insights
Numbers match the database, but two headline *framings* need correction (§7.3).
Insight 14's open question was resolved in Phase 6 and appended correctly.

---

## 6. Missing Components

| Component | Planned in | Status |
|---|---|---|
| `powerbi/RetailPulse.pbix` | Phase 6 | ❌ Missing (blocked) |
| Dashboard screenshots | Phase 6 | ❌ `reports/dashboard_screenshots/` is empty |
| RFM / cohort / item-level / stage / category-satisfaction exports | Implied by Phase 6 spec | ❌ Missing (§5.1 Gap A) |
| `documentation/methodology.md` | Phase 8 | ❌ Missing — and **referenced** by `data_dictionary.md` line 179 |
| `documentation/limitations.md` | Phase 8 | ❌ Missing (limitations are scattered across 6 files) |
| `documentation/architecture.md` | Phase 1 → deferred ×3 | ❌ Missing |
| `documentation/project_overview.md` | Original structure | ❌ Missing (README covers it — likely unnecessary) |
| Pipeline runner (one command to rebuild everything) | Not planned | ❌ Missing — recommended |
| Automated test suite | Not planned | ❌ Validators exist as separate scripts; no single entry point |
| `LICENSE` | README implies one | ❌ Missing (dataset is CC BY-NC-SA 4.0) |
| Final README (portfolio standard) | Phase 8 | ⚠️ Partial |

---

## 7. Bugs and Technical Risks

Ordered by severity. Every item has evidence.

### 7.1 [HIGH] Excel workbook does not regenerate cleanly — **[EXECUTED]**
`scripts/build_phase2_workbook.py` **line 355** still writes:
```
=SUMPRODUCT(--(ABS(E{first}:E{last})>0.01))
```
This was fixed in Phase 2 by patching the `.xlsx` directly, not the script. Rebuilding
the workbook from scripts in scratch and recalculating produced:
```
Formula errors : 1    04_KPI_Validation!C25 = #VALUE!
```
Also: the build script writes a 27.4 MB file *without* cached values; a separate manual
`recalc_workbook.py --install` step is needed, and that two-step sequence is not
documented as a pipeline.
**Fix:** port the `COUNTIFS` formula into the script; document build → recalc order.

### 7.2 [HIGH] `requirements.txt` incomplete — **[EXECUTED]**
| Package | Imported by | In requirements? |
|---|---|---|
| `openpyxl` | `build_phase2_workbook.py`, `recalc_workbook.py` | **No** (commented out) |
| `mysql-connector-python` | `export_powerbi_data.py`, `validate_dax_logic.py`, notebook 03 | **No** (commented out) |
| `seaborn` | nothing | Yes — **unused** |

A fresh `pip install -r requirements.txt` cannot run the Phase 2 scripts, Phase 6
scripts, or notebook 03 §G. `pip check` passes only because the current venv has
extras installed by hand.

### 7.3 [CRITICAL — analytical] Two headline claims are misleading — **[EXECUTED]**

**(a) "AOV fell 13.4%"** — `business_insights.md` Insight 2 and Priority 3,
`eda_report.md` §3.1, `README.md` Business Recommendations #3.

| Basis | Start | End | Change |
|---|---|---|---|
| Jan-2017 vs Aug-2018 (two single months) | 152.60 | 132.20 | −13.4% |
| **Jan–Aug 2017 vs Jan–Aug 2018** | **136.55** | **137.14** | **+0.4%** |
| Full 2017 vs Jan–Aug 2018 | 137.66 | 137.14 | −0.4% |

January 2017 is a 787-order ramp month; one noisy endpoint drives the −13.4%. The
defensible statement is **"AOV was flat"**, which still supports the recommendation
("AOV is an untouched lever") — but "fell 13.4%" is an overstatement that would not
survive scrutiny. The README also **contradicts itself**: it says "AOV moved just
+1.4%" in Key Findings and "It *fell* 13.4%" in Recommendations.

**(b) "Mean MoM growth +22.7% (2017) vs +2.5% (2018)"** — Insight 1, EDA §A1,
executive summary.

| | Arithmetic mean of MoM % | Compound monthly growth (CMGR) |
|---|---|---|
| 2017 | +22.69% | **+18.01%** |
| 2018 | +2.45% | **−1.53%** |

The mean is inflated by Feb-2017's +104% jump off a tiny base, and it hides that 2018
was a *slight decline*, not slight growth. "Plateau" remains correct; the numbers
attached to it should be CMGR.

**(c) Three different "AOV / Jan–Aug order growth" figures across reports**
`excel_exploration_report.md` (22,968 orders, AOV +1.4% — all statuses),
`sql_analysis_report.md` (22,562, +0.4% — eligible with items), EDA/insights (−13.4%,
endpoint months). Each is internally correct for its definition, but no report
reconciles them, so a reader sees three answers to one question.

### 7.4 [MEDIUM] EDA notebook narrative contradicts its own output — **[EXECUTED]**
In `notebooks/03_exploratory_data_analysis.ipynb`:

| Location | Text says | Computed output |
|---|---|---|
| §C1 "Reading it" | "it takes **26** of 74 categories to reach 80%" | **18** |
| §A1 "Reading it" | MoM growth "roughly **+18%** across 2017" | **+22.7%** (mean) |
| §D1 markdown + chart title | top 10% of sellers earn "roughly / about **three-quarters**" | **67.4%** (two-thirds) |

The markdown was written before the cells were executed and never reconciled.
`eda_report.md` and `business_insights.md` use the correct computed values, so the
reports are fine; the notebook is not.

### 7.5 [HIGH] New data-quality issue not in the register — **[EXECUTED]**
**1,350 delivered orders have `order_delivered_carrier_date` earlier than
`order_approved_at`** — the carrier collected the parcel before payment was approved.
Phase 1 checked carrier-before-*purchase* (0) and customer-before-carrier (23) but never
carrier-before-approval.

Impact: `sql/04_joins_and_aggregations.sql` **Q20** (and Insight 12) average
`approval → carrier` across these rows, so negative durations pull the reported
**2.78 days** down. The "74% of delivery time is last-mile" conclusion is probably
directionally right, but the stage figures are biased until these rows are handled.
Plausible cause: boleto payments approved after dispatch, or timestamp recording lag —
**not determinable from the data**.

### 7.6 [HIGH] DAX `Revenue 3M Moving Avg` is wrong — **[INSPECTED]**
```dax
Revenue 3M Moving Avg = AVERAGEX ( DATESINPERIOD ( dim_date[Date], MAX(dim_date[Date]), -3, MONTH ), [Total Revenue] )
```
`DATESINPERIOD` returns **days**, so this averages *daily* revenue over ~90 days —
roughly **1/30th** of the intended 3-month average of monthly revenue. It is not in the
validator, so the "37/37 PASS" did not catch it. (Cannot be executed without Power BI;
the logic error is evident from the DAX semantics.)

### 7.7 [MEDIUM] Seller measures will disagree with platform measures — **[EXECUTED]**
`Seller Late Rate = AVERAGE(vw_seller_performance[late_pct])` is an **unweighted mean of
per-seller rates = 8.42%**, while the platform order-weighted late rate is **8.11%**.
Page 4 and Page 5 cards would show two different "late rate" numbers with no
explanation. Same issue for `Seller Avg Delivery Days`.

### 7.8 [MEDIUM] MySQL security and configuration — **[EXECUTED]**
| Setting | Value | Risk |
|---|---|---|
| `root@localhost` password | **none** | Low while bound to localhost; becomes real if the port is exposed for a Windows VM |
| `bind_address` | `127.0.0.1` | ✅ Not network-exposed |
| `local_infile` (global) | **1 (ON)** | `02_import.sql` enables it and never disables it |

**Fragility:** `scripts/export_powerbi_data.py`, `scripts/validate_dax_logic.py` and
notebook 03 §G connect as password-less root with **no environment-variable or
option-file support**. Setting a root password — the recommended security step —
will break all three.

### 7.9 [LOW] Smaller issues — **[EXECUTED / INSPECTED]**
- `vw_customer_summary` assigns `MIN(customer_state)` — alphabetical, arbitrary — to
  **39 people** whose orders span more than one state.
- `vw_monthly_revenue.avg_order_value` divides by eligible orders *including* the **8**
  eligible orders with no items, deviating slightly from the KPI definition.
- Documentation states the database is "~210 MB"; measured **260.4 MB**
  (`sql_analysis_guide.md` l.239, `sql_analysis_report.md` l.409).
- Hard-coded absolute paths: `/Applications/LibreOffice.app` in `recalc_workbook.py`;
  `/Users/<name>/...` and `/opt/homebrew/...` in `mysql_setup.md` (8×),
  `dataset_setup.md` (4×), `sql_analysis_guide.md`, `sql_analysis_report.md`, and a stale
  scratch path in the `build_phase2_data.py` docstring. Scripts themselves resolve
  paths relative to the repo — good.
- `dashboard_specification.md` Page 1 recommends a dual-axis combo chart, contradicting
  the project's own stated "never dual-axis" rule.
- The seller city `santa barbara d´oeste` uses an acute accent (U+00B4) instead of an
  apostrophe — a source-data quirk, correctly stored; displays oddly in some terminals.
- `excel/…xlsx` (21.7 MB binary) is committed; every rebuild adds another ~22 MB to
  history.

### 7.10 Privacy and security review — **[EXECUTED]**
- No credentials, API keys, tokens, `.env` or key files in the repository.
- Raw and cleaned data correctly gitignored (licensed / derived).
- Dataset is anonymised (hashed IDs; no names, emails or addresses beyond zip prefix).
- Commit metadata contains the author's personal email address — publicly visible on
  GitHub. A personal choice, noted for awareness only.

---

## 8. Manual Actions Required from Me

| Requirement | Why it is needed | Where | Manual or automatic? | Mandatory or optional? |
|---|---|---|---|---|
| **Windows environment** (UTM free / Parallels / cloud x64 VM) | Power BI Desktop runs only on Windows | Phase 6 | **Manual** — you must install/approve or create the account | **Mandatory** to finish Phase 6 |
| **Power BI Desktop install** (inside Windows) | Build and test the `.pbix` | Phase 6 | **Manual** (Store install, no admin needed) | **Mandatory** |
| **Windows Update incl. KB5065789** (if Windows on ARM) | Microsoft's stated prerequisite for Power BI on ARM | Phase 6 | **Manual** | **Mandatory** on ARM |
| **Build the six dashboard pages** in Power BI | No automation possible from macOS | Phase 6 | **Manual**, guided by the spec | **Mandatory** |
| **Dashboard screenshots** | Evidence of a working dashboard | Phase 6 | **Manual** | Mandatory (per plan) |
| **MT-01 monthly revenue chart** in LibreOffice | Deferred by your request | Phase 2 | **Manual** | Mandatory to close Phase 2 as planned |
| **8 pivot tables** (`11_Pivot_Exercises`) | Hands-on Excel practice | Phase 2 | **Manual** | Optional |
| **Set a MySQL root password** | Required before exposing MySQL to a VM | Phase 4/6 | **Manual** (`mysql_secure_installation`) | Optional now; mandatory if Power BI connects to MySQL over the network |
| **Approve code changes** in §13 | Fixes to existing files | All | **Automatic after your permission** | — |
| Dataset download from Kaggle | Only for a *fresh clone* on another machine | Setup | Manual (browser) | Already done here |

### What you personally must do
Windows environment, Power BI install, building the six pages, screenshots, MT-01,
and optionally setting the MySQL password.

### What can be done automatically once you approve
Everything in P0/P1 that is code or documentation: fixing `requirements.txt`, the
workbook build script, the notebook narrative, the misleading claims, the DAX bug, the
missing exports and views, password-safe database connections, the issue-register
update, Phase 8 documentation, and a pipeline runner.

### What is NOT necessary
No API keys, no access tokens, no Kaggle API credentials (manual download works), no
cloud data warehouse, no environment variables (none are currently read by any code),
no third-party services. **This project does not use any external API.**

---

## 9. External Dependencies and API Requirements

| Dependency | Type | Status | Required? |
|---|---|---|---|
| Olist dataset (Kaggle) | Data, CC BY-NC-SA 4.0 | ✅ Downloaded | Yes (once per machine) |
| Python 3.11+ & packages | Local software | ✅ Installed (requirements incomplete — §7.2) | Yes |
| MySQL 8.4 (Homebrew `mysql@8.4`) | Local software | ✅ Running | Yes |
| LibreOffice Calc | Local software | ✅ Installed | Only to recalculate/regenerate the workbook |
| Power BI Desktop | Windows software | ❌ Not available | Yes, for Phase 6 |
| Windows OS / VM | Platform | ❌ Not available | Yes, for Phase 6 |
| **External APIs** | — | **None used** | **No** |
| **API keys / tokens / OAuth** | — | **None used** | **No** |
| **Environment variables** | — | **None read by any code** | **No** (recommended for DB password, §13 P1) |
| Cloud services | — | None used | No (cloud VM is one *optional* Windows route) |

---

## 10. Recommended Improvements

Only improvements with genuine analytical or reliability value. Complexity:
L = under an hour, M = a few hours, H = a day or more.

### 10.1 Data analytics

| Improvement | Why it is useful | Necessary? | Complexity | Manual/external? |
|---|---|---|---|---|
| **Replace mean-of-MoM with CMGR; report AOV like-for-like** | Fixes §7.3; the current figures overstate | **Necessary** | L | No |
| **Time-to-second-purchase analysis** for the 2,997 repeat buyers | Insight 6 recommends a "time-boxed follow-up" but no window is evidenced. The repeat-gap distribution would set it | Recommended | L | No |
| **Distance-adjusted delivery** using the unused `geolocation` table (seller→customer haversine) | Separates "slow because far" from "slow because poor seller/carrier" — currently confounded in Insights 8 and 11 | Recommended | M | No |
| **Seller dispatch metric** (approval→carrier, the part a seller controls) | Fairer seller scorecard than total delivery time, of which 74% is carrier — **must exclude the 1,350 anomalous rows first** | Recommended | L | No |
| **Confidence intervals** on repeat-vs-one-time and delay-bucket comparisons | Repeat vs one-time differences are small (+0.031 stars); CIs show whether they are real | Recommended | M | No |
| **Freight-to-price ratio by price band** | Insight 2 recommends a free-shipping threshold near R$87 without evidence of freight share at that price | Optional | L | No |
| **Handle reviews written before delivery** (8.6% of delivered-order reviews) | Affects Insight 9/13 interpretation — some "on time" and "late" ratings were written mid-transit | Recommended | L | No |
| Cohort retention on revenue, not just counts | Shows whether the few returners matter commercially | Optional | L | No |

**Not recommended:** predictive CLV or churn models (3.12% repeat rate gives no
signal to learn from), sentiment analysis (Portuguese text, optional at best, and
the satisfaction story is already explained by delivery).

### 10.2 Data visualization (Power BI)

| Improvement | Why | Necessary? | Complexity | Manual? |
|---|---|---|---|---|
| **Add the 6 missing data sources** (§5.1 Gap A) | Without them 6 specified visuals cannot be built | **Necessary** | M | No |
| **Fix `Revenue 3M Moving Avg`; validate all 49 measures** | §7.6, §5.1 Gap B | **Necessary** | M | No |
| **Weighted seller late rate** | Avoids two conflicting late-rate figures (§7.7) | Necessary | L | No |
| **Numeric `YearMonthSort` on the aggregate views** | Lets Pages 3–5 sort and slice chronologically without fan-out | Recommended | L | No |
| **"Last refreshed / data period" card on every page** | The data is historical; this must stay visible | Recommended | L | Manual (in Power BI) |
| Bookmark-based "stable window vs all months" toggle | Shows *why* edge months are excluded | Optional | L | Manual |
| Replace the Page 1 dual-axis combo with two stacked charts | Consistency with the project's own design rule | Optional | L | Manual |

### 10.3 Data engineering and reliability

| Improvement | Why | Necessary? | Complexity | Manual? |
|---|---|---|---|---|
| **Complete `requirements.txt`** | §7.2 — fresh installs fail | **Necessary** | L | No |
| **Fix workbook build script** | §7.1 — regeneration reintroduces `#VALUE!` | **Necessary** | L | No |
| **Password-safe DB connections** (env var / `~/.my.cnf` via `option_files`) | §7.8 — securing MySQL currently breaks 3 components | **Necessary** before securing MySQL | L | No |
| **Disable `local_infile` after import** | Leaves a server-side feature on unnecessarily | Recommended | L | No |
| **Single pipeline runner** (`run_pipeline.sh` or `Makefile`) | Reproduce everything with one command; order is currently spread across docs | Recommended | M | No |
| **One test entry point** running all validators with non-zero exit on failure | Turns five scripts into one reproducible gate | Recommended | M | No |
| **Add the 1,350 carrier-before-approval anomaly to the register and a flag column** | §7.5 | **Necessary** | L | No |
| Make LibreOffice path configurable | Portability beyond macOS | Optional | L | No |

### 10.4 Business intelligence

| Improvement | Why | Necessary? | Complexity |
|---|---|---|---|
| **Reconcile the three AOV/growth figures in one place** | Readers currently see three answers to one question | **Necessary** | L |
| Quantify revenue at risk from lateness (late orders × rating impact × repeat propensity) | Turns Insight 9 into a costed business case | Optional | M |
| Separate "decision-ready" vs "hypothesis" recommendations explicitly | Several actions (padding vs conversion, regional experiment) are untested hypotheses | Recommended | L |

---

## 11. Data Quality and Analytical Limitations

### 11.1 Known limitations — are they handled correctly?

| Limitation | Handled? | Evidence |
|---|---|---|
| Historical period (Sep 2016 – Oct 2018) | ✅ | Banners in insights report; footer specified for every dashboard page |
| One-time vs repeat customers (3.12%) | ✅ | Consistently reported; RFM F-score adapted |
| `customer_id` vs `customer_unique_id` | ✅ | Validated in SQL (96,096) and pandas; views use the person key |
| Missing delivery dates (8 "delivered" with none) | ✅ | `delivery_measurable` flag; 96,476 denominator used everywhere |
| Canceled / unavailable orders | ✅ | `revenue_eligible` flag; never deleted |
| Revenue vs profit | ✅ | No margin computed anywhere; stated repeatedly |
| Freight | ✅ | Separate from revenue; eligible vs all-status distinguished in DAX |
| Review grain (547 orders with 2–3 reviews) | ✅ | Review-grain 4.0864 vs order-grain 4.0868 documented |
| Seller rating interpretation | ✅ | Named "inherited order rating"; captions specified |
| RFM frequency degeneracy | ✅ | 1/3/5 ordinal, disclosed |
| Historical vs predicted CLV | ✅ | "Historical Customer Value" throughout |
| Padded delivery estimates / on-time baseline | ✅ | Insight 10; captions specified |
| Cohort right-censoring | ✅ | Disclosed in notebook, insights and spec |
| Geographic quality (4,119 city variants) | ✅ | State-level only |

### 11.2 New limitations or incorrect assumptions found in this audit

| # | Issue | Evidence | Affects |
|---|---|---|---|
| N1 | **1,350 orders: carrier handoff before payment approval** | **[EXECUTED]** | Insight 12, Q20, any seller-dispatch metric |
| N2 | **8.6% of reviews on delivered orders (8,320 of 96,359) were written before delivery** | **[EXECUTED]** | Insights 9 & 13 — those ratings could not have reflected the parcel's arrival |
| N3 | **Endpoint-month AOV comparison** is unstable | **[EXECUTED]** | Insight 2, README, EDA |
| N4 | **Arithmetic mean of MoM %** misrepresents growth | **[EXECUTED]** | Insight 1, EDA §A1 |
| N5 | Payments vs items reconciliation: of orders *with* items, only **260** differ (net R$2,870); the rest of the R$165k aggregate gap sits in orders with no item rows | **[EXECUTED]** | Explains a long-standing open gap; worth one sentence in KPI docs |
| N6 | 39 customers span multiple states; `vw_customer_summary` picks one arbitrarily | **[EXECUTED]** | Customer-by-state breakdowns (negligible magnitude) |
| N7 | Timestamps have no timezone; assumed Brazil local | **[INSPECTED]** | Day-boundary cases only; negligible |

---

## 12. Reproducibility Assessment

Could another developer reproduce RetailPulse from the repository?

| Step | Reproducible? | Evidence / gap |
|---|---|---|
| Recreate Python environment | ⚠️ **Partially** | `requirements.txt` misses `openpyxl` and `mysql-connector-python` (§7.2). Python 3.14 pinned versions may not resolve on older Pythons; README says "3.11+ should work" — untested |
| Obtain raw data | ✅ | `documentation/dataset_setup.md` (manual Kaggle download) |
| Regenerate cleaned data | ✅ **Byte-identical** | **[EXECUTED]** in scratch |
| Recreate MySQL database | ✅ | `documentation/mysql_setup.md`; **[PRIOR]** rebuilt from scratch → 61/61. **Not in README** |
| Rerun SQL analysis | ✅ | **[EXECUTED]** 0 errors |
| Regenerate Excel workbook | ❌ **No** | Reintroduces `#VALUE!` (§7.1); two-step build→recalc undocumented as a sequence; requires LibreOffice at a hard-coded macOS path |
| Rerun EDA notebook | ✅ | **[EXECUTED]** 0 errors, 15/15 |
| Regenerate Power BI exports | ✅ | **[EXECUTED]** 335,797 rows — but exports are incomplete for the spec (§5.1) |
| Build the dashboard | ❌ | No `.pbix`; Windows required |
| File paths | ⚠️ | Scripts are repo-relative ✅; several docs hard-code `/Users/<name>/...` |
| Setup instructions complete | ❌ | README setup omits MySQL install, schema/import, `--local-infile`, LibreOffice, and the Power BI export step. The information exists, but scattered across `mysql_setup.md`, `environment_setup.md`, `dataset/cleaned/README.md`, `powerbi/README.md` |
| Undocumented manual steps | ⚠️ | Pipeline order (raw → clean → MySQL → views → exports → workbook → recalc) is never stated in one place |

**Verdict:** a careful developer *could* reproduce the core pipeline by reading four
documents, after discovering two missing packages. The Excel artefact does not
reproduce correctly, and there is no single command or single document for the whole
pipeline.

---

## 13. Prioritized Remaining Work

### P0 — Critical (required for the existing project to be correct and functional)

| # | Task | Reason | Files | Dependencies | Manual? | Testing criteria | Cx |
|---|---|---|---|---|---|---|---|
| P0-1 | Add `openpyxl` and `mysql-connector-python` to `requirements.txt` (pin versions); decide on unused `seaborn` | Fresh installs fail (§7.2) | `requirements.txt` | — | No | Fresh scratch venv installs and runs all 8 scripts + 3 notebooks | L |
| P0-2 | Port the `COUNTIFS` fix into the workbook build script | Regeneration reintroduces `#VALUE!` (§7.1) | `scripts/build_phase2_workbook.py` | LibreOffice | No | Rebuild in scratch + `recalc_workbook.py` → 0 formula errors, 17/17 | L |
| P0-3 | Correct the AOV claim to like-for-like (flat, +0.4%) and reconcile the three figures | Misleading headline (§7.3a,c) | `reports/business_insights.md`, `eda_report.md`, `README.md`, notebook 03 §A2 | — | No | Every AOV figure states its basis; no "fell 13.4%" without qualification; README consistent | L |
| P0-4 | Replace mean-of-MoM with CMGR (2017 +18.0%, 2018 −1.5%) | Misleading growth figures (§7.3b) | `business_insights.md`, `eda_report.md`, notebook 03 §A1 | — | No | Figures recomputed and matched to SQL | L |
| P0-5 | Fix notebook 03 narrative contradictions | Text contradicts output (§7.4) | `notebooks/03_exploratory_data_analysis.ipynb` | — | No | Re-execute; narrative numbers equal computed output | L |
| P0-6 | Register the carrier-before-approval anomaly (Q18), add a flag, exclude from stage averages, re-check Insight 12 | Biased stage figures (§7.5) | `02_data_cleaning.ipynb`, `cleaning_decisions.md`, `verify_issue_register.py`, `sql/04` Q20, `business_insights.md` | Rebuild cleaned + MySQL | No | Register shows 18 issues, 18/18; Q20 recomputed; Insight 12 updated or confirmed | M |
| P0-7 | Add the 6 missing Power BI data sources (RFM, cohort, item-level, stage timestamps, category×review, seller×category) | 6 of 14 visuals unbuildable (§5.1 A) | `sql/07_business_analysis.sql`, `scripts/export_powerbi_data.py`, `powerbi/data_model.md` | MySQL | No | Each specified visual maps to a table; new views validated vs pandas | M |
| P0-8 | Fix `Revenue 3M Moving Avg`; extend validator to all 49 measures; replace tautological median check | Bug + coverage gap (§5.1 B/C, §7.6) | `powerbi/dax_measures.md`, `scripts/validate_dax_logic.py` | P0-7 | No | Validator covers every defined measure; 0 constant-vs-constant checks | M |
| P0-9 | **Build and test the Power BI dashboard** | The Phase 6 deliverable | `powerbi/RetailPulse.pbix` | **Windows + Power BI**, P0-7, P0-8 | **Yes** | Every KPI card matches `powerbi/README.md` expected values; slicers, drill-through, captions verified | H |

### P1 — Important (completeness, reliability, analytical quality)

| # | Task | Reason | Files | Dependencies | Manual? | Testing criteria | Cx |
|---|---|---|---|---|---|---|---|
| P1-1 | Password-safe DB connections (env var / option file) | Securing MySQL breaks 3 components (§7.8) | `export_powerbi_data.py`, `validate_dax_logic.py`, notebook 03 | — | No | Works with and without a root password | L |
| P1-2 | Disable `local_infile` after import | Unneeded server feature left on | `sql/02_import.sql` | — | No | `@@global.local_infile = 0` after import | L |
| P1-3 | Weighted seller late rate & delivery days | Conflicting late-rate cards (§7.7) | `dax_measures.md`, `vw_seller_performance` | P0-8 | No | Page-level late rate = 8.11% when unfiltered | L |
| P1-4 | Single pipeline runner | One-command reproducibility | new `run_pipeline.sh` / `Makefile` | P0-1, P0-2 | No | Clean clone + raw data → all artefacts + all validators green | M |
| P1-5 | One test entry point for all validators | Single reproducible quality gate | new `scripts/run_all_checks.py` | P0-1 | No | Non-zero exit on any failure | M |
| P1-6 | Phase 8 docs: `methodology.md`, `limitations.md`, `architecture.md`; complete README setup | Missing docs; broken reference in `data_dictionary.md` | `documentation/`, `README.md` | P0 items | No | No reference to a missing file; README alone sufficient to reproduce | M |
| P1-7 | Handle reviews written before delivery (flag; sensitivity check on Insights 9/13) | N2 | notebook / SQL, `business_insights.md` | — | No | Insight 9 table recomputed with and without them | L |
| P1-8 | Time-to-second-purchase analysis | Evidence for Insight 6's follow-up window | SQL or notebook | — | No | Distribution reported; recommendation cites it | L |
| P1-9 | Seller dispatch metric (excl. anomalies) | Fairer seller assessment | `vw_seller_performance` | P0-6 | No | Matches pandas | L |
| P1-10 | MT-01 manual chart | Closes Phase 2 as planned | Excel workbook | — | **Yes** | Chart present, stable window only | L |
| P1-11 | Fix minor doc inaccuracies (DB size, hard-coded paths, dual-axis contradiction) | Accuracy | several `.md` | — | No | Grep finds no `/Users/<name>`, no "210 MB" | L |

### P2 — Optional enhancements

| # | Task | Value | Cx | Manual? |
|---|---|---|---|---|
| P2-1 | Distance-adjusted delivery analysis via `geolocation` | Separates distance from performance | M | No |
| P2-2 | Confidence intervals on key comparisons | Shows which differences are real | M | No |
| P2-3 | Freight ratio by price band (supports free-shipping recommendation) | Evidence for a stated recommendation | L | No |
| P2-4 | Revenue-at-risk model for late deliveries | Costed business case | M | No |
| P2-5 | Revenue-weighted cohort retention | Commercial weight of returners | L | No |
| P2-6 | Configurable LibreOffice path | Portability | L | No |
| P2-7 | Add `LICENSE` file | Clarity on code licence vs dataset licence | L | No |
| P2-8 | 8 manual pivot tables | Hands-on Excel practice | L | **Yes** |

---

## 14. Recommended Next Step

**Do P0-1 through P0-8 next, in one batch, before touching Power BI.**

Reasoning:
1. They are all **code and documentation fixes I can make automatically** after your
   approval — none needs Windows, money, or accounts.
2. **P0-7 and P0-8 must precede the dashboard build.** Building Power BI today would
   hit six visuals with no data and a broken moving-average measure — wasting the
   Windows session you set up.
3. P0-3 and P0-4 correct claims that currently sit in the README and business report,
   which is where a reader looks first.

Then, in parallel:
- **You** set up the Windows environment (the earlier recommendation stands: UTM
  free, cloud x64 as fallback if Power BI misbehaves under ARM emulation).
- Once it exists, **P0-9** (build + test the dashboard) using the corrected exports and
  measures.

Then P1 (reliability, Phase 8 docs), then P2 at your discretion.

---

## 15. Final Technical Completion Estimate

Phase 9 (resume/interview) is excluded from the technical scope. Weights reflect
effort for a project of this kind.

| Phase | Weight | Achieved | Rationale |
|---|---|---|---|
| 1 Dataset understanding | 8 | 8 | Complete; one new issue belongs in a later fix |
| 2 Excel exploration | 8 | 6.5 | Committed workbook correct; script bug; MT-01 pending |
| 3 Python cleaning | 12 | 12 | Reproduces byte-identically |
| 4 MySQL & SQL | 15 | 14 | 61/61, 34 queries; config/security and connection fragility |
| 5 EDA | 12 | 10.5 | Re-runs clean; narrative contradicts output; misleading growth framing |
| 6 Power BI | 25 | 6 | Theme, spec, 37 measures, exports exist; 6 data gaps, DAX bug; **dashboard 0%** |
| 7 Business insights | 8 | 6.5 | Numbers verified; two headline framings need correction |
| 8 Documentation | 12 | 3 | Extensive phase docs exist; planned Phase 8 docs and full setup guide missing |
| **Total** | **100** | **≈ 66.5** | |

### **Final estimate: ~67% technically complete.**

This is **lower than the ~72% stated at the end of Phase 6**, for two reasons this audit
established by execution rather than inspection: the Power BI preparation is less
complete than recorded (six visuals have no data source; only 37 of 49 measures are
validated, one with a bug), and three "complete" phases carry correctness defects
(workbook regeneration, misleading AOV/growth claims, notebook narrative errors).

The foundation — data, cleaning, database, validation — is genuinely strong and
reproducible. The remaining work is concentrated and well-defined: eight automatable
P0 fixes, then one Windows-dependent dashboard build.

---

### Appendix — commands executed during this audit

All read-only with respect to the project, or run inside an isolated scratch copy:

```
scripts/verify_issue_register.py                 → 17/17, 0 mismatches
sql/08_validation.sql                             → 61 PASS, 0 FAIL
scripts/validate_dax_logic.py                     → 37/37 PASS (coverage gap noted)
scripts/recalc_workbook.py (temp only)            → 17 KPIs, 0 formula errors (committed file)
sql/03..06 (34 queries)                           → 0 errors
02_data_cleaning.ipynb  (scratch)                 → 9/9 cleaned CSVs byte-identical
03_exploratory_data_analysis.ipynb (scratch)      → 0 errors, 15/15 vs MySQL, 15 charts
build_phase2_data.py + build_phase2_workbook.py
  + recalc_workbook.py (scratch)                  → 1 formula error: C25 #VALUE!
export_powerbi_data.py (scratch)                  → 335,797 rows; 6 spec visuals uncovered
Read-only MySQL probes                            → AOV bases, CMGR, security settings,
                                                    1,350 carrier-before-approval rows,
                                                    8,320 reviews before delivery,
                                                    39 multi-state customers,
                                                    seller late rate 8.42% vs 8.11%
```
