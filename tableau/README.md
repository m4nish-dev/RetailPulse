# RetailPulse — Tableau Public Dashboard

**Status (2026-11-27): workbook generated; dashboards NOT built or published yet.**
`tableau/RetailPulse.twb` is generated from the validated registry. It already contains:
- the six data sources, their relationships, field names and types
- 2 parameters and all 100 calculated fields
- 8 KPI check sheets

It passes Tableau's official 2026.3 schema and 15 content checks, but **it has not been opened in
Tableau yet** (the first manual step). The chart sheets, the 8 dashboards, their filters and
actions are built by hand in Tableau Desktop Public Edition from the specification.

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
| `schema/` | Tableau's official workbook schema 2026.3 (Apache 2.0), used by `scripts/validate_tableau_workbook.py` |
| `tableau_calc_validation_results.csv` | One row per validator check (264) |
| `data/` | 5 view extracts (**git-ignored**; regenerate with `scripts/export_tableau_data.py`) + `_manifest.csv` (rows, columns, MD5; committed) |
| `data/analytical/` | 9 analytical sources (**git-ignored**; regenerate with `scripts/export_tableau_sources.py`) + committed `_manifest.csv`; definitions in [`../documentation/analytical_sources.md`](../documentation/analytical_sources.md) |
| `extracts/`, `RetailPulse_build.twbx` | Created by you in Tableau. **Git-ignored** (they contain data) |

## Verification (run from the project root)

```bash
./venv/bin/python scripts/check_tableau_data.py        # 24 checks: files, MD5, keys, 8 relationships, blanks
./venv/bin/python scripts/validate_tableau_sources.py  # 90 checks: analytical CSVs vs live SQL and a pandas rebuild
./venv/bin/python scripts/validate_tableau_calcs.py    # 264 checks: 90 measures in Tableau semantics vs SQL
./venv/bin/python scripts/validate_tableau_calcs.py --write-docs   # regenerate calculated_fields.md
./venv/bin/python scripts/build_tableau_workbook.py    # (re)generate RetailPulse.twb from the registry
./venv/bin/python scripts/validate_tableau_workbook.py # 15 checks: Tableau's XSD, model, captions, formulas, sheets
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
