# RetailPulse — Tableau Public Dashboard

**Status (2026-11-28): workbook with 8 dashboards and 49 worksheets generated and tested in Tableau; not published yet.**

**Open `tableau/RetailPulse_Final.twbx`.** It is generated from code and contains:
- the data as six Tableau **extracts** (`.hyper` files inside the package), which Tableau Public requires,
  read by 10 Tableau data sources (two-table views of the 6 registry data sources)
- 2 parameters, all 100 calculated fields, 49 worksheets (41 charts + 8 KPI strips) and **8 dashboards**
  (Executive, Customers, Products, Sellers, Operations, Satisfaction, Category Detail, Seller Detail)
  with filter controls, captions and drill-through actions

History of the generated workbook:
| Version | Result in Tableau Desktop Public Edition 2026.3.2 | Fix |
|---|---|---|
| `RetailPulse.twb` | did not open: error D2E8DA72 (`manual-sort` not declared) | `<SortTagCleanup />` declared (`reports/tableau_workbook_repair_report.md`) |
| `RetailPulse_repaired.twb` | **opened** (confirmed in Tableau's log), but could not be saved to Tableau Public: error 3C242D89 ("must use extracts", data source RP Cohorts) | all six data sources rebuilt on `.hyper` extracts (`reports/tableau_extract_report.md`) |
| `RetailPulse_Final.twbx` (KPI sheets only) | **opens; all 6 extracts connect; all 8 KPI sheets render** with values equal to the validated figures | `[:Measure Names]` declaration; N07 LOD grouping (`reports/tableau_validation_report.md`); kept as `RetailPulse_Final_kpi_only.twbx.backup` |
| `RetailPulse_Final.twbx` (published 2026-11-28) | published; post-deployment review found `###`, a blank MoM chart ("20 nulls"), cramped title and KPIs, and 10 issues on other pages | kept as `RetailPulse_Final_published_2026-11-28.twbx.backup`; fixes in `reports/tableau_post_deployment_fixes.md` |
| `RetailPulse_Final.twbx` (current, post-deployment fixes) | **8/8 dashboards, 49/49 sheets, 6/6 filter tests pass in Tableau; layouts checked in screenshots** | table-calc direction, fixed-size zones, line breaks, data-source colours, legends, table zoom (`reports/tableau_post_deployment_fixes.md`) |
| `RetailPulse_Final.twbx` (first dashboard build: 8 dashboards, 49 sheets) | **8/8 dashboards open with 0 error dialogs and 0 query errors; 49/49 sheets return the specified figures; filter logic 6/6** (`tableau/scripts/tableau_runtime_check.py`) | two-table data sources (error 1B885FB3); no buttons / parameter actions (D2E8DA72); see `reports/tableau_final_validation.md` |

Validated on macOS:
- every extract was opened and queried with Tableau's Hyper API, and every value equals the CSVs
- the workbook passes Tableau's official 2026.3 schema
- nothing of the earlier workbook is lost; every dashboard zone, filter control and action resolves (20 checks)
- **in Tableau itself:** every dashboard and every worksheet opened without an error dialog, and the SQL
  Tableau generated returned the specified figures (`reports/tableau_final_validation.md`)

Not tested: clicks (no UI scripting on this Mac). Not done: publishing (needs the owner's sign-in), screenshots.

## Why Tableau Public

Tableau Desktop Public Edition is free, runs natively on macOS (including Apple
silicon), reads CSV files and publishes to a public Tableau Public profile. It is the
project's only BI tool.

## Folder contents

| Path | What it is |
|---|---|
| [`mac_implementation_guide.md`](mac_implementation_guide.md) | **Start here.** Beginner step-by-step: install, connect, model, formulas, sheets, dashboards, actions, validation, publishing, screenshots |
| [`data_model.md`](data_model.md) | 6 data sources, 8 relationships, keys and grain, data types, nulls, date logic, filter rules |
| [`calculated_fields.md`](calculated_fields.md) | **Generated.** 90 measures + 10 helpers + 2 parameters. Each entry gives the definition, formula, source fields, aggregation level and settings, format, notes and expected values. Also lists the 28 field renames |
| [`dashboard_specification.md`](dashboard_specification.md) | 6 dashboards + 2 detail dashboards, 47 sheets: questions, KPIs, shelves, filters, actions, captions, expected values |
| [`tableau_completion_checklist.md`](tableau_completion_checklist.md) | What is done (with evidence) and every manual item with its expected value |
| `RetailPulse.twb` | **Generated** by `scripts/build_tableau_workbook.py`: 6 data sources, 8 relationships, captions, types, 2 parameters, 100 calculated fields, 8 KPI check sheets. Git-ignored (stores this Mac's data path); regenerate any time |
| `RetailPulse_model_only.twb` | **Generated** fallback: the same model with one empty sheet |
| `RetailPulse_Final.twbx` | **Open this one.** Packaged workbook with the six `.hyper` extracts inside (package-relative paths); built by `tableau/scripts/build_tableau_extracts.py`. Git-ignored (contains data) |
| `RetailPulse_Final.twb` | The same workbook reading the extracts from `tableau/extracts/` by absolute path (this Mac). Git-ignored |
| `extracts/` | `RP_Orders.hyper`, `RP_Customers.hyper`, `RP_Cohorts.hyper`, `RP_Categories.hyper`, `RP_Sellers.hyper`, `RP_Stage_Summary.hyper`: every table of each data source in schema "Extract", loaded with Hyper's CSV reader. Git-ignored |
| `scripts/` | `build_tableau_extracts.py` (extracts + Final workbook), `validate_tableau_extracts.py` (20 checks) and `tableau_runtime_check.py` (opens every dashboard and worksheet in Tableau Desktop itself and checks Tableau's own log and generated SQL, plus saved filter/parameter values; macOS, run with Tableau closed, ≈35 min) |
| `RetailPulse_repaired.twb` | Previous version (live CSV connections; opens, but cannot be saved to Tableau Public). Kept, with `RetailPulse_repaired.twb.backup`. `RetailPulse.twb.backup` is the original first version. Git-ignored |
| `schema/` | Tableau's official workbook schema 2026.3 (Apache 2.0), used by `scripts/validate_tableau_workbook.py` |
| `tableau_calc_validation_results.csv` | One row per validator check (264) |
| `data/` | 5 view extracts (**git-ignored**; regenerate with `scripts/export_tableau_data.py`) + `_manifest.csv` (rows, columns, MD5; committed) |
| `data/analytical/` | 9 analytical sources (**git-ignored**; regenerate with `scripts/export_tableau_sources.py`) + committed `_manifest.csv`; definitions in [`../documentation/analytical_sources.md`](../documentation/analytical_sources.md) |
| `RetailPulse_build.twbx` | Your working copy, saved from the Final workbook in Tableau. **Git-ignored** (contains data) |

## Verification (run from the project root)

```bash
./venv/bin/python scripts/check_tableau_data.py        # 24 checks: files, MD5, keys, 8 relationships, blanks
./venv/bin/python scripts/validate_tableau_sources.py  # 90 checks: analytical CSVs vs live SQL and a pandas rebuild
./venv/bin/python scripts/validate_tableau_calcs.py    # 264 checks: 90 measures in Tableau semantics vs SQL
./venv/bin/python scripts/validate_tableau_calcs.py --write-docs   # regenerate calculated_fields.md
./venv/bin/python scripts/build_tableau_workbook.py    # (re)generate RetailPulse.twb from the registry
./venv/bin/python scripts/validate_tableau_workbook.py # 16 checks: Tableau's XSD, model, captions, formulas, sheets, sort format
./venv/bin/python scripts/repair_tableau_workbook.py   # repair an older generated .twb (adds the sort-format declaration)
./venv/bin/python tableau/scripts/build_tableau_extracts.py     # 6 .hyper extracts + RetailPulse_Final.twbx/.twb (CSVs unchanged)
./venv/bin/python tableau/scripts/validate_tableau_extracts.py  # 19 checks: Hyper files queried and compared with the CSVs, workbook
./venv/bin/python tableau/scripts/tableau_runtime_check.py      # runtime test IN Tableau (launches the app; close Tableau first)
```

All Tableau definitions live in one place, `scripts/tableau_registry.py`. The documentation,
the formula validation and the workbook are all generated from it, so they cannot drift apart.

| | |
|---|---|
| ✅ Logic validated by Python + SQL | Each formula's logic was emulated with Tableau's rules over the exact CSVs. It equals an independent SQL answer on the base tables in all 223 reference contexts. Also checked: drill-through values, revenue reconciliation through every source, field references after the renames, and 9 wrong formulations shown to be wrong |
| ✅ Workbook structure validated | the generated `.twb` passes Tableau's official 2026.3 XSD. Its relationships, captions, types and 100 formulas equal the registry; a mutation test shows the schema check catches planted errors |
| 🔲 Pending manual Tableau runtime test | Tableau opening the workbook and computing the emulated values; chart sheets, dashboards, filters, actions, formatting; publication; screenshots |

One documented difference: 311 sellers that share a revenue value with another seller get
a slightly different cumulative share. The largest difference is 0.0201 percentage points,
and the first such seller is at position 865. Every value quoted in the specification is
unaffected. Other Tableau behaviours that matter, each with its workaround, are listed per
field in `calculated_fields.md` and in `data_model.md` §2–3.

## Publishing is public

Everything saved to Tableau Public, workbook and data alike, is visible to and
downloadable by anyone. The dashboard uses only the CSV files above: no database
connection, user name or password can end up in the workbook. Never type anything from
`.env` into Tableau. The guide's §11 lists the checks to make before publishing,
including the dataset licence attribution (Olist, CC BY-NC-SA 4.0).

## Sources for the Tableau Public facts (checked 2026-11-27)

* Tableau help, *Tableau Desktop and Tableau Desktop Public Edition Feature Comparison*.
  Product name, local saving, connectors, 15M rows, 10 GB, non-commercial:
  <https://help.tableau.com/current/pro/desktop/en-us/desktop_comparison.htm>
* Tableau help, *Save Workbooks to Tableau Public*. Menu path, sign-in, extract on publish,
  public visibility: <https://help.tableau.com/current/pro/desktop/en-us/publish_workbooks_tableaupublic.htm>
* Tableau help, *Text File*. CSV connector:
  <https://help.tableau.com/current/pro/desktop/en-us/examples_text.htm>
* Tableau help, *Understand Field Type Detection and Naming Improvements*. Automatic
  renaming and Reset name: <https://help.tableau.com/current/pro/desktop/en-us/data_clean_adm.htm>
* Tableau help, *Questions about Relationships, the Data Model and Data Sources*.
  `TableName(Count)`, LOD behaviour: <https://help.tableau.com/current/pro/desktop/en-us/datasource_datamodel_faq.htm>
* Tableau help, *Order of Operations*. FIXED before dimension filters; dimension filters
  before table calculations: <https://help.tableau.com/current/pro/desktop/en-us/order_of_operations.htm>
* Homebrew cask `tableau-public` (third-party package index): <https://formulae.brew.sh/cask/tableau-public>

Not confirmed from official pages, and therefore worded cautiously in the guide:
* the Apple-silicon download labels
* the local file extension (`.twbx` is Tableau's packaged-workbook format)
* the exact label of the Tableau Public download setting
* how Tableau names duplicate fields before you rename them
