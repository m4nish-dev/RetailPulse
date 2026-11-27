# Tableau Workbook Repair Report

**Date:** 2026-11-27 · **Script:** `scripts/repair_tableau_workbook.py` · **Input:** `tableau/RetailPulse.twb` · **Output:** `tableau/RetailPulse_repaired.twb` · **Backup:** `tableau/RetailPulse.twb.backup`

## Error reported by Tableau Desktop Public Edition 2026.3.2

Error code D2E8DA72: *No declaration found for element 'manual-sort'*; *attributes 'column' and 'direction' are not declared*; *element 'manual-sort' is not allowed for content model '(datasources?,mapsources?,datasource-dependencies\*,filter,sort,perspectives,slices?,aggregation)'*. Reported twice per KPI sheet: at the `<manual-sort>` line and at the closing `</view>`.

## Root cause

Tableau reads sort elements in one of two formats, selected by the workbook's `<document-format-change-manifest>`. The current format (`<manual-sort>`, `<computed-sort>`, `<natural-sort>`, as in Tableau's published 2026.3 XSD) applies only when the manifest declares `<SortTagCleanup />`. Otherwise Tableau uses the older content model quoted in the error, which has no `<manual-sort>`. The workbook generator copied its manifest from a workbook Tableau 2026.3.2 had saved **without** any sorting, so the declaration was missing.

**Evidence:**
- **Superstore sample (Tableau 2026.3.2 app bundle)**: 20 current-format sort elements; manifest declares `SortTagCleanup`: **yes**
- **book1.xml**: 0 current-format sort elements; manifest declares `SortTagCleanup`: **no**
- **Generated workbook (before repair)**: 8 `<manual-sort>` elements; manifest declares `SortTagCleanup`: **no**
- Every other element and attribute name in the workbook also occurs in the Tableau-written reference files (check below), so no other unsupported markup was found.

## Invalid elements found

**8** `<manual-sort>` elements, one per KPI check sheet. Each sets the left-to-right order of the KPI values (Measure Names) to the order listed in the dashboard specification:

| Sheet | Element | Column | Direction | Intended order (buckets) |
|---|---|---|---|---|
| 1.0 KPIs | `manual-sort` | Measure Names | ASC | RP_M01, RP_M02, RP_M03, RP_M06, RP_M07 |
| 1.5 YoY Jan–Aug | `manual-sort` | Measure Names | ASC | RP_M15, RP_M13, RP_M14 |
| 2.0 KPIs | `manual-sort` | Measure Names | ASC | RP_M16, RP_M19, RP_M18, RP_M20, RP_M21 |
| 3.0 KPIs | `manual-sort` | Measure Names | ASC | RP_M24, RP_M26, RP_M25, RP_N07 |
| 4.0 KPIs | `manual-sort` | Measure Names | ASC | RP_M30, RP_M29, RP_M34, RP_M32, RP_M33 |
| 5.0 KPIs | `manual-sort` | Measure Names | ASC | RP_M36, RP_M40, RP_M41, RP_M38, RP_M44, RP_M08 |
| 5.6 Stage Shares | `manual-sort` | Measure Names | ASC | RP_N24, RP_N23, RP_N22, RP_N21, RP_N17 |
| 6.0 KPIs | `manual-sort` | Measure Names | ASC | RP_M46, RP_M47, RP_M48, RP_M45, RP_N25 |

(`RP_M01` = Total Revenue etc.; IDs as in `tableau/calculated_fields.md`.)

## Repair applied

- inserted <SortTagCleanup /> into <document-format-change-manifest> as entry 7 of 8 (alphabetical, between <SheetIdentifierTracking /> and <WindowsPersistSimpleIdentifiers />), file line 12
- The `<manual-sort>` elements were **kept unchanged**: sorting behaviour is preserved exactly. Nothing was deleted or converted.
- The generator (`scripts/build_tableau_workbook.py`) now declares the same flag, so regenerated workbooks do not repeat the problem.

## Validation

| Check | Result | Detail |
|---|---|---|
| repaired file parses as XML | PASS |  |
| text diff: exactly one line added, every other line byte-identical | PASS | added: ['<SortTagCleanup />'] |
| manifest declares <SortTagCleanup /> (required for 8 sort elements) | PASS |  |
| only change: one manifest element added | PASS | {'SortTagCleanup': 1} |
| worksheets unchanged (8) | PASS |  |
| dashboards unchanged (0) | PASS |  |
| datasources unchanged (7) | PASS |  |
| calculations (incl. sheet copies) unchanged (145) | PASS |  |
| datasource calculations unchanged (100) | PASS |  |
| parameters unchanged (2) | PASS |  |
| filters unchanged (8) | PASS |  |
| relationships unchanged (8) | PASS |  |
| every sort element preserved (sheet, column, direction, bucket order) | PASS | 8 sorts |
| all workbook sections other than the manifest are byte-identical | PASS |  |
| every element name also appears in Tableau-written reference files | PASS | none unknown (2 reference file(s)) |
| every element/attribute pair also appears in Tableau-written reference files | PASS | none unknown |
| all 14 CSV dependencies exist | PASS | all present |
| valid against Tableau's official 2026.3 XSD | PASS | no errors (waived: missing <explain-data>, also absent from files Tableau writes) |

## Structure before and after

| Item | Before | After |
|---|---|---|
| worksheets | 8 | 8 |
| dashboards | 0 | 0 |
| datasources | 7 | 7 |
| parameters | 2 | 2 |
| datasource calculations | 100 | 100 |
| calculations (incl. sheet copies) | 145 | 145 |
| filters | 8 | 8 |
| relationships | 8 | 8 |
| sort elements | 8 | 8 |
| manifest flags | 7 | 8 |

## Not verified here

Opening the workbook in Tableau Desktop Public Edition was **not** done by this script: there is no supported way to drive Tableau's window from a script. XSD validation is syntactic only (Tableau's own note). The manual test is to open `tableau/RetailPulse_repaired.twb` in Tableau.
