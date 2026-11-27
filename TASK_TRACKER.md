# RetailPulse — Task Tracker

**Legend:** `[ ]` pending · `[~]` in progress · `[x]` done · `[!]` blocked

**Last updated:** 2026-11-27
**Current phase:** ✅ Phases 1–5 + 7 COMPLETE · ✅ corrective fix phases complete (see below) · 🚧 Power BI dashboard PREPARED but NOT BUILT (needs Windows)
**Overall progress:** All analysis is complete and validated by one command
(`scripts/run_all_validations.py`: 15 PASS, 0 FAIL). Power BI assets are
built and logic-validated as far as macOS allows (**90 DAX measures, 251/251
checks**; 9 analytical sources, 90/90), but **no .pbix exists**. Outstanding
manual work: MT-01 Excel chart, the Power BI build and screenshots, the final
GitHub push. Live checklist: `documentation/project_completion_checklist.md`.
Rows below record each phase as it was completed; superseded figures are marked.

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
| 1.18 | Write a separate architecture document | [x] | Superseded: the architecture diagram and folder map are in `README.md` (Architecture); the data flow is in `documentation/mysql_schema.md`. No separate file |
| 1.19 | Initialise git repository | [x] | Branch `main`; .gitignore hardened (removed over-broad `*.cfg`) |
| 1.20 | Phase 1 review gate | [x] | Notebook executes end-to-end, 0 errors, 26/26 cells |
| 1.21 | Write `documentation/data_quality_report.md` | [x] | 17 issues: 4 High, 3 Medium, 9 Low, 1 Info |
| 1.22 | Write `documentation/table_relationships.md` | [x] | PK/FK test results + ER diagram + join rules |
| 1.23 | Register Jupyter kernel | [x] | Kernel name `retailpulse` |

---

## Phase 2 — Excel Data Exploration

| # | Task | Status | Notes |
|---|---|---|---|
| 2.1 | Choose spreadsheet tool | [x] | LibreOffice Calc 26.8.3.1 via Homebrew (1st download failed mid-transfer; retry OK) |
| 2.2 | Missing-value audit per column | [x] | Sheet `02_Missing_Values` — 13 of 52 columns, each with a verdict |
| 2.3 | Duplicate ID check | [x] | Sheet `03_Keys_Duplicates` — 10 PK candidates + 7 relationships |
| 2.4 | Distribution review: price, freight, review score | [x] | Sheets 08, 09 |
| 2.5 | Revenue by month | [x] | Sheet `05` — live SUMIFS, 25 months |
| 2.6 | Orders by status | [x] | Sheet `06` — live COUNTIF |
| 2.7 | Orders by state | [x] | Sheet `07` — 27 states, revenue + AOV + delivery |
| 2.8 | KPI validation vs Python | [x] | **17/17 computable KPIs reconcile.** 2 not computable in a spreadsheet |
| 2.9 | Write `reports/excel_exploration_report.md` | [x] | Methodology, KPI table, fan-out, 8 observations |
| 2.10 | Phase 2 review gate | [x] | PASSED — workbook recalculated in LibreOffice, 0 formula errors |
| 2.11 | **MT-01 Monthly revenue trend chart** | [ ] | 🔲 **DEFERRED — manual task for you.** See `MANUAL_TASKS.md`. Blocks nothing |
| 2.12 | Build 8 pivot tables by hand | [ ] | Optional practice. Sheet `11_Pivot_Exercises` |

---

## Phase 3 — Python Data Cleaning

| # | Task | Status | Notes |
|---|---|---|---|
| 3.1 | Create virtual environment | [x] | `venv/` on Python 3.14.3 (done early — Phase 1 needed pandas) |
| 3.2 | Install dependencies from requirements.txt | [x] | + openpyxl for Phase 2. MySQL packages deferred to Phase 4 |
| 3.3 | `01_data_exploration.ipynb` | [x] | 49 cells, 5 charts, executes clean end-to-end |
| 3.4 | Null-handling rule per column, documented | [x] | All 13 null columns have a recorded decision; 0 values imputed |
| 3.5 | Duplicate resolution | [x] | review_id investigated: 0 of 789 carry differing scores → kept all rows |
| 3.6 | Data type corrections | [x] | Strict converters that raise on failure; IDs and zips kept as text |
| 3.7 | Referential integrity checks | [x] | 7 PKs + 4 FKs re-validated after conversion; 0 orphans |
| 3.8 | Derived columns | [x] | 28 added to orders_clean; `is_late` from UNROUNDED timestamps |
| 3.9 | Revenue-eligible status rule, documented | [x] | Excludes canceled + unavailable → 13,494,400.74 BRL |
| 3.10 | `02_data_cleaning.ipynb` | [x] | 42 cells, 14 sections, executes clean |
| 3.11 | Export cleaned tables | [x] | 9 files, 569,776 rows, 90 MB. Gitignored (derived) — see dataset/cleaned/README.md |
| 3.12 | Post-clean validation log | [x] | **34/34 checks passed.** reports/data_cleaning_report.md |
| 3.13 | Phase 3 review gate | [x] | PASSED |
| 3.14 | Re-verify the issue register from raw | [x] | `scripts/verify_issue_register.py` — all 17 counts match, 0 mismatches |
| 3.15 | Write `documentation/cleaning_decisions.md` | [x] | Definitive register with reason + validation per issue |

---

## Phase 4 — MySQL Database Development

| # | Task | Status | Notes |
|---|---|---|---|
| 4.1 | Install / provision MySQL | [x] | MySQL **8.4.13 LTS** via `mysql@8.4`. Plain `mysql` would have given 26.10; 8.0 is EOL. No root password set — your call |
| 4.2 | Design relational schema | [x] | 9 tables, InnoDB, utf8mb4. DECIMAL for money, CHAR(32) ids, CHAR(5) zips |
| 4.3 | `sql/01_schema.sql` | [x] | 7 FKs, 3 composite PKs, 1 measured covering index |
| 4.4 | `sql/02_import.sql` | [x] | LOAD DATA LOCAL INFILE. 3 real bugs found and fixed — see 4.15 |
| 4.5 | Validate row counts vs Python | [x] | 569,776 rows, all 9 tables exact, **0 warnings** |
| 4.6 | Module 1 queries (executive) | [x] | Q1–Q10, Q21–Q23 |
| 4.7 | Module 2 queries (customer) | [x] | Q28–Q34 incl. RFM, cohorts |
| 4.8 | Module 3 queries (product) | [x] | Q11–Q13, Q24 |
| 4.9 | Module 4 queries (seller) | [x] | Q14–Q16 |
| 4.10 | Module 5 queries (delivery) | [x] | Q17–Q20, Q27 |
| 4.11 | Module 6 queries (satisfaction) | [x] | Q4, Q25, Q26 |
| 4.12 | Advanced queries: CTEs, window functions | [x] | ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, NTILE, running totals, moving averages |
| 4.13 | Save real query results | [x] | All 34 executed, 0 failures. Results in reports/sql_analysis_report.md |
| 4.14 | Phase 4 review gate | [x] | **PASSED** — rebuilt from scratch, 61/61 validation checks |
| 4.15 | Fix import bugs found during execution | [x] | (a) 2 review rows silently lost — MySQL's backslash escaping vs Python's RFC4180 quote-doubling → `ESCAPED BY ''` (b) 11 rows diverged on NULLs — PAD SPACE collation makes `' '=''` → `CHAR_LENGTH()=0` (c) geolocation truncation → DOUBLE |
| 4.16 | Create 7 analytical views | [x] | Grains verified; `vw_order_summary` proven free of fan-out |
| 4.17 | Performance check with EXPLAIN | [x] | 1 index added on evidence: 0.35s→0.21s, now a covering index |
| 4.18 | `documentation/mysql_setup.md` | [x] | Install, credentials, local_infile, troubleshooting |
| 4.19 | `documentation/mysql_schema.md` | [x] | ERD, design decisions, keys, views |
| 4.20 | `documentation/sql_analysis_guide.md` | [x] | Run order, the 3 rules, concept map |
| 4.21 | `reports/sql_analysis_report.md` | [x] | 9 business findings from executed queries |

---

## Phase 5 — Exploratory Data Analysis

| # | Task | Status | Notes |
|---|---|---|---|
| 5.1 | Sales trend analysis | [x] | A1, A2 — growth is volume not basket; 2018 is a plateau |
| 5.2 | Customer behaviour analysis | [x] | B1 — 93% of top-1% spenders bought exactly once |
| 5.3 | Product analysis | [x] | C1, C2 — 18 categories reach 80%; 22 of 24 growing |
| 5.4 | Seller analysis | [x] | D1, D2 — largest seller only 1.70%; intervention list produced |
| 5.5 | Delivery analysis | [x] | E1, E2 — padding 26.9d→7.5d; state spread 2.8× |
| 5.6 | Review analysis | [x] | F1, F2, F3 — 1–7 days late costs 1.02 stars |
| 5.7 | RFM segmentation + methodology writeup | [x] | B2 — Champions 2.4% of revenue; Potential Loyalists 33.9% |
| 5.8 | Cohort & retention analysis | [x] | B3 — every cohort cell under 1.5% |
| 5.9 | Delay vs rating relationship | [x] | F1 — the project's headline finding |
| 5.10 | Phase 5 review gate | [x] | **PASSED** — notebook clean, 15/15 vs MySQL |
| 5.11 | `notebooks/03_exploratory_data_analysis.ipynb` | [x] | 56 cells, 29 code, executes end to end |
| 5.12 | Save 15 charts to `reports/eda_charts/` | [x] | Each answers a business question; 4 inspected visually, 2 layout defects fixed |
| 5.13 | Validate EDA against MySQL | [x] | 15 metrics, all agree within 0.01 |
| 5.14 | `reports/eda_report.md` | [x] | 10 findings, limitations, corrections recorded |

---

## Phase 6 — Power BI Dashboards

| # | Task | Status | Notes |
|---|---|---|---|
| 6.1 | Install Power BI Desktop | [!] | **BLOCKED.** Environment checked 2026-11-13: no Power BI, Parallels, VMware, UTM, VirtualBox, CrossOver, wine, Docker or QEMU. macOS cannot run Power BI Desktop |
| 6.1a | Export validated views for Power BI | [x] | `scripts/export_powerbi_data.py` — 11 CSVs + generated dim_date, 335,797 rows |
| 6.1b | Build + validate Power BI theme | [x] | `powerbi/RetailPulse_Theme.json` — valid JSON, palette passes CVD checks on dark surface |
| 6.1c | Write + verify 37 DAX measures | [x] | `powerbi/dax_measures.md`; **37/37 logic verified** via `scripts/validate_dax_logic.py`. Caught 1 fabricated expected value. *Superseded by fix-phase F4 (84 measures, 15 corrected, 230/230) and F8 (90 measures, 251/251)* |
| 6.1d | Specify data model | [x] | `powerbi/data_model.md` — 3 relationships, cardinality, Import rationale, 3 aggregate tables deliberately unrelated |
| 6.1e | Specify all 6 dashboard pages | [x] | `powerbi/dashboard_specification.md` — visual by visual, with mandatory caveat captions |
| 6.2 | Load data, build model + date table | [!] | Blocked — needs Windows. Spec ready in `powerbi/data_model.md` |
| 6.3 | Power Query transformations | [!] | Blocked. Views are pre-shaped, so minimal transformation needed |
| 6.4 | DAX measures | [~] | Written and logic-verified (90 measures, 251/251). **Not executed** — needs Power BI |
| 6.5 | Page 1 Executive Overview | [!] | Blocked — fully specified |
| 6.6 | Page 2 Customer Intelligence | [!] | Blocked — fully specified |
| 6.7 | Page 3 Product Analytics | [!] | Blocked — fully specified |
| 6.8 | Page 4 Seller Performance | [!] | Blocked — fully specified |
| 6.9 | Page 5 Order & Delivery Operations | [!] | Blocked — fully specified |
| 6.10 | Page 6 Customer Satisfaction | [!] | Blocked — fully specified |
| 6.11 | Slicers, drill-through, tooltips | [!] | Blocked — specified |
| 6.12 | Apply charcoal / white / orange theme | [x] | Theme file built and validated; **applying it needs Power BI** |
| 6.13 | Capture screenshots | [!] | Blocked — nothing to screenshot yet. No fake images created |
| 6.14 | Phase 6 review gate | [!] | **NOT PASSED — cannot pass without Windows.** Phase 6 is explicitly incomplete |

---

## Phase 7 — Business Insights

| # | Task | Status | Notes |
|---|---|---|---|
| 7.1 | Draft 10–15 insights in the 5-part format | [x] | **14 insights**, each with question / method / finding / implication / action |
| 7.2 | Verify every number against source query | [x] | **38/38 claims re-verified against MySQL**, independently of earlier reports |
| 7.3 | Write `reports/business_insights.md` | [x] | 850 lines: exec summary, 14 insights, top-5 priorities, 12 limitations |
| 7.4 | Phase 7 review gate | [x] | **PASSED** — 38/38 claims, 0 broken refs, 0 contradictions |
| 7.5 | QA: file references resolve | [x] | 23 references checked, all resolve |
| 7.6 | QA: no causation claimed from correlation | [x] | 5 explicit caveats; no unqualified causal language |
| 7.7 | QA: no profit/margin claims | [x] | None — dataset has no cost data |
| 7.8 | QA: historical framing | [x] | Explicit "not current performance" banner at the top |
| 7.9 | Resolve cross-document RFM count variance | [x] | NTILE vs qcut tie-breaking (~0.3%); disclosed in Insight 6. *Fully resolved in F5: tie-consistent scoring everywhere* |

---

## Corrective fix phases (2026-11-20, after the final project audit)

| # | Task | Status | Notes |
|---|---|---|---|
| F1 | Audit P0 fixes | [x] | requirements, workbook COUNTIFS, like-for-like AOV, CMGR, notebook narrative |
| F2 | Data-quality investigation | [x] | Q18 carrier-before-approval (1,359), Q19 reviews before delivery (4,795); flags added, 0 rows deleted; Insight 9 revised; register 19 issues |
| F3 | Power BI analytical sources | [x] | 6 sources + `dim_category` (later + `seller_scorecard`); `sql/09`, validated 90/90 |
| F4 | DAX audit | [x] | 49 audited, 15 corrected, 35 added; validator rewritten, 230/230; Insight 14 revised |
| F5 | Consistency cleanup | [x] | RFM, cohort and category methods aligned across SQL, notebook 03, reports and sources |
| F6 | Security & reproducibility | [x] | read-only `retailpulse_app`, `.env`, `scripts/rp_db.py`, `scripts/run_all_validations.py` |
| F8 | Remaining Mac-side work (2026-11-27) | [x] | 11th Power BI relationship (seller drill-through); N36–N41 for four spec visuals (251/251); `sql/11` evidence for Insights 4/6 and priority 3 (38/38); priorities labelled decision-ready/hypothesis; business-question answer map; readiness script (27/27); `local_infile` reset in `sql/02`; doc fixes |
| F9 | Re-verification of T01/T03/T07–T10a (2026-11-27) | [x] | All six confirmed in the files; four leftovers fixed: `data_model.md` "not related" text now matches the 11 relationships; `sql/04` Q13 column `revenue_2018_q3` → `revenue_jun_aug_2018`; chart C2 axis label "2018 Q3" → "Jun–Aug 2018" (data unchanged); plan's architecture deliverable marked superseded |
| F7 | Documentation audit | [x] | README rewritten, inconsistencies corrected, B3 chart clarified; `reports/phase6_documentation_audit.md` |

---

## Phase 8 — Final Documentation & GitHub

| # | Task | Status | Notes |
|---|---|---|---|
| 8.1 | Expand README to portfolio standard | [x] | Rewritten 2026-11-20 (F7) |
| 8.2 | Methodology documentation | [x] | Covered by `kpi_definitions.md`, `cleaning_decisions.md` and the reports; no separate `methodology.md` |
| 8.3 | Limitations | [x] | README, `business_insights.md` and `kpi_definitions.md`; no separate `limitations.md` |
| 8.4 | Setup / reproduction instructions | [x] | README, `mysql_setup.md`, `.env.example`, validation runner |
| 8.5 | Embed dashboard screenshots | [!] | Waits for the Power BI build (Windows) |
| 8.6 | Push to GitHub | [~] | Pushed through F6 (commit b6eb1a6); final push pending your instruction |
| 8.7 | Phase 8 review gate | [ ] | After screenshots and final push |

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
| ~~`reviews` primary key~~ | 4 | ✅ Resolved: composite `(review_id, order_id)`. Surrogate rejected — it would hide that review_id repeats |
| City names are unnormalised (4,119 variants) | 3 | Geographic analysis is state-level until this is cleaned |
| 23 orders show delivery before carrier handoff | 3 | Flag only; cause unknowable from the data |
| Are delivery estimates deliberately padded? | 5 | Orders arrive ~11 days early on average. A finding, not a defect — needs Q19 to confirm |
| Portuguese review text | 5 | Sentiment analysis needs a multilingual model. Optional |
| ~~Separate architecture document~~ | 3 | ✅ Resolved 2026-11-27: covered by `README.md` § Architecture; no separate file |
| ~~Git repository not initialised~~ | 1 | ✅ Done — branch `main` |
| MT-01 monthly revenue chart | 2 | 🔲 Manual, deferred by your request. Blocks nothing |
| MySQL root has no password | 4 | Deliberate — fresh Homebrew default. Application code no longer uses root (F6); `mysql_secure_installation` is your call |
| `vw_monthly_revenue` MoM / moving average across the 2016/2017 gap; monthly AOV includes 8 item-less orders | F7 | Documented, fix proposed in `reports/phase6_documentation_audit.md`; needs an admin to apply. No reported figure or DAX measure uses these columns |
| Views take 2–3s | 4 | Fine here; Power BI should Import, not DirectQuery |
| **Power BI needs Windows** | 6 | **HARD BLOCKER — Phase 6 cannot be completed on this machine.** Verified absent: Power BI, Parallels, VMware, UTM, VirtualBox, CrossOver, wine, Docker, QEMU. All non-Windows assets are built and validated |
| ~~Insight 14: product vs delivery~~ | 7 | ✅ **Resolved 2026-11-13.** Category-specific: `bed_bath_table` and `furniture_decor` keep their full deficit on on-time orders (product); `watches_gifts` and `electronics` lose theirs entirely (delivery) |
| Cleaned data not in version control | 3 | 90 MB derived artifact; regenerates in ~2 min |
| 2016-11 absent from the dataset entirely | 3 | New finding. Reinforces the 2017-01 window start |
