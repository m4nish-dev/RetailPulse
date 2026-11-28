# Tableau Public Post-Deployment Fixes

**Date:** 2026-11-28 · **Workbook:** `tableau/RetailPulse_Final.twbx` (regenerated) · **Tableau:** Tableau
Desktop Public Edition 2026.3.2 (macOS, Apple silicon)

**Backup of the published version** (byte copy taken before any change, git-ignored):
- `tableau/RetailPulse_Final_published_2026-11-28.twbx.backup`, the file you saved from Tableau and published
- `tableau/RetailPulse_Final_published_2026-11-28.twb.backup`

**Result:** the four reported issues and ten more found on the other dashboards are fixed. The workbook is
regenerated from the project's code (`scripts/tableau_charts.py`, `scripts/build_tableau_workbook.py`). No data,
KPI definition, formula or business metric was changed. See §6 for the Tableau test results and the readiness verdict.

## 1. How the issues were investigated

- **XML.** The published workbook was compared with the code-generated one. Your Tableau save had changed only
  the Executive dashboard's zone sizes (Tableau re-laid it out) and the bracket style of one shelf (8.2). No manual
  edits were lost.
- **Tableau-written reference files.** The Superstore and World Indicators samples installed with Tableau show how
  Tableau itself encodes table-calculation direction, colour assignments, line breaks and fixed-size zones.
- **Screenshots in Tableau.** Every dashboard was opened in a dedicated Tableau instance and its window captured,
  before and after the fixes. Evidence: `reports/tableau_post_deployment_screenshots/` (cropped to the dashboard).
  "Before" = the published file; "after" = the regenerated file.
- **Tableau's own logs and SQL.** `tableau/scripts/tableau_runtime_check.py` (§6).

## 2. Reported issues: root cause and fix

| # | Issue (published Executive Overview) | Root cause | Fix |
|---|---|---|---|
| A | YoY Jan–Aug panel showed `### ### ###` | The panel (about 330 px wide) showed 3 values side by side at 15 pt bold. "R$ 7,341,037.41" needs about 140 px but got about 100 px. Same squeeze on 5.6 Stage Shares and 7.5 Seller Delivery | Narrow KPI panels list one KPI per line, with a title. Values now read 138.28% · R$ 3,080,850.81 · R$ 7,341,037.41 |
| B | Title and subtitle too close | (1) The subtitle never got its own line: Tableau marks a line break in formatted text as `Æ` + newline, and the generator wrote a bare newline, so the subtitle ran on after the title. (2) When you saved the workbook, Tableau re-laid out the page and shrank the header from 62 to 51 px, because zone sizes were stored as proportions, not fixed | Line break written as Tableau writes it. Header 84 px. Header, KPI band, filter column, captions and footer marked **fixed size** (`is-fixed`, as in Tableau's World Indicators sample), so Tableau can no longer shrink them |
| C | Monthly revenue change chart blank, "20 nulls" | **Configuration bug, not missing data.** In Tableau's XML `ordering-type='Columns'` means "compute down the table" (Superstore's customer rank uses it with customers on Rows). The generator used it to mean "across". With months across the columns, each month became its own partition, so the previous month was always empty and MoM % was NULL for all 20 months. The extract and calculation were correct | Every table calculation now names its "compute using" dimension explicitly (Order Month, category, rfm_segment …). MoM % draws 19 bars; 2017-01 stays blank **by design** (December 2016 has one order), and that expected null is no longer flagged |
| D | KPI values cramped or clipped | (1) Each KPI zone showed its sheet title ("1.0 KPIs") above the values. (2) The KPI band was 104 px, and Tableau shrank it to 93 px when saving (see B) | KPI zones without the sheet-name title; band 118 px and fixed; values 14 pt bold, labels 9 pt grey; filter column 270 px |

The same direction bug (C) also affected two other charts, now fixed:
- **1.1:** the 3-month moving-average line was entirely NULL (invisible). It now draws from 2017-03, as specified.
- **3.5:** Category Rank showed 1 for every category. It now shows 1, 2, 3 … (health_beauty 1, watches_gifts 2).

## 3. Issues found on the other dashboards

| Dashboard · sheet | Issue | Root cause | Fix |
|---|---|---|---|
| 2 Customers · 2.2 RFM Segments | **Segment Customer Share showed 100.00% for every segment** | Nested table calculation: Segment Customer Share = Customers In Segment / RFM Scored Customers, and the inner TOTAL used its own default direction, so it totalled each segment by itself | Default direction of every table calculation set from the registry ("Compute Using: rfm_segment" …), plus the nested calculation's direction stored in the chart (`table-calc field=…`, defined in Tableau's 2026.3 schema). Now 22.56% / 15.57% / 35.27% / 24.66% / 1.00% / 0.94%, the specification's validated values |
| 2 Customers · 2.4 Cohort Retention | Every cell showed `####` | 380 percentage labels in cells about 40 px wide | Labels removed from the cells; the colour scale shows retention and the tooltip gives the exact % and cohort size. The 190 unobserved cells stay blank |
| all · categorical colours | Planned colours (grey comparison series, stage colours, grey "one-time" slice) ignored | Tableau reads category → colour assignments at data-source level (World Indicators sample); the generator wrote them in each worksheet | Written at data-source level; now applied |
| 1.1, 3.3, 5.2 | No colour legend (which line is which?) | Legends not placed on the dashboards | Colour legend beside each chart |
| 1.1 / 1.2 | Revenue-and-orders chart squeezed to about 15% of its row | Tableau gave the 20-column MoM chart its minimum width first, because zone widths were proportions | Chart widths fixed per zone; MoM on a continuous month axis |
| 3 Products · 3.5 | 74 table rows squashed into the panel, unreadable | Every sheet was set to "fit entire view" | Tables keep normal row height and scroll (fit width); full-width row |
| 3.4, 6.4 | 24 / 35 category labels overlapping | Rows too short for the number of bars | Taller rows, 8 pt row labels |
| 6 Satisfaction · 6.2 | **The two averages were stacked** (bars up to about 8.6 on a 1–5 scale) | Measure Values on columns with Measure Names only on colour stacks the bars | Measure Names on rows: side-by-side bars (e.g. on time 4.2009 all reviews · 4.2017 after arrival) |
| 5 Operations · 5.5 | Stage segments unlabelled | Two of the three segments of one stacked bar are too narrow for labels | One labelled bar per stage, in stage order: 0.40 / 2.85 / 9.36 days |
| 2.1 pie | Only the "Repeat" label showed | Tableau hid the large slice's label | All labels shown |
| 7, 8 detail pages | Selector labelled "p_category" / "p_seller" | Internal parameter names shown | Displayed as "Category" and "Seller (seller_id)"; formulas still use [p_category] / [p_seller] |
| 7.1, 8.1 | Narrow single-value tables at risk of `###` | Row header plus values in about 280 px | One value per line |
| 8.2, 3.5 | 151.0 orders | Count summed from a decimal column | Integer format |
| chart sheets | "custo..", "Month of Order Month" labels | Field-name labels above axes | Hidden on charts (axis and sheet titles remain) |

Nothing was found on 4 Sellers and 8 Seller Detail apart from the shared items above.

## 4. What did not change

- **Data and extracts:** rebuilt from the same CSVs; every value equals the CSVs (Hyper API check, below). The six
  `.hyper` files remain packaged in the `.twbx` with package-relative paths.
- **Calculations:** all 100 formulas are character-for-character those validated against SQL (264/264). Only the
  direction settings of the table calculations were corrected; the formulas themselves are unchanged.
- **Content:** no chart or dashboard removed; no metric added. All filters, parameters, the two click-a-state filter
  actions and the four drill-through / back menu actions are preserved.

## 5. Before / after

| Item | Before (published) | After |
|---|---|---|
| YoY panel | `### ### ###` | 138.28% · R$ 3,080,850.81 · R$ 7,341,037.41 |
| Title | subtitle running into the title | title on one line, subtitle below |
| MoM chart | empty, "20 nulls" | 19 bars (+103.97% Feb 2017 … −3.32% Aug 2018); 2017-01 blank by design |
| 3-month moving average | invisible (all NULL) | drawn from 2017-03 |
| KPI strip | values clipped | all KPIs fully visible |
| RFM customer share | 100% for every segment | 22.56 / 15.57 / 35.27 / 24.66 / 1.00 / 0.94% |
| Category rank | 1 for every category | 1, 2, 3 … |
| Delay vs score | stacked averages | side-by-side averages |
| Cohort heatmap | `####` in every cell | colour scale, values in the tooltip |

Screenshots: `reports/tableau_post_deployment_screenshots/0N_<dashboard>_before.jpg` and `…_after.jpg`. They
are window captures of Tableau Desktop showing the top ~85% of each 1400 × 1150 page; the bottom row needs
scrolling there.

## 6. Validation

### In Tableau Desktop Public Edition 2026.3.2 (`tableau/scripts/tableau_runtime_check.py`, final workbook)

Each check opened a scratch copy of the final `.twbx` in its own Tableau instance, read Tableau's logs, and
re-executed the SQL Tableau generated on the extracts. Full output:
[`tableau_runtime_check_output.txt`](tableau_runtime_check_output.txt).

| Check | Result |
|---|---|
| All 8 dashboards open: 0 error dialogs, 0 query errors, every sheet on them queries | **8/8 pass** |
| Six extracts connected on every dashboard | **6/6 on all 8** |
| All 49 worksheets return the specification's figures from Tableau's own SQL | **49/49 pass** |
| KPI values equal the validated figures (revenue 13,494,400.74 · 99,441 orders · 96,096 customers · AOV 137.42 · median 86.90 · repeat 3.12% · on-time 91.89% · review 4.0864 …) | **all equal** |
| Filters and parameter, saved into a copy: state = SP on 5 dashboards, category = watches_gifts | **6/6 equal the specification** |
| Last change (shorter filter titles on Executive) re-checked: dashboard, its 6 sheets, SP filter | **all pass** |
| Layout at the published size: every dashboard captured in Tableau after the fixes | no `###`, no clipped KPI, no overlapping labels, no blank chart (screenshots) |

The table-calculation outputs (MoM %, moving average, rank, RFM shares) are computed by Tableau after the
query. They were checked in the screenshots against the specification's values, e.g. the RFM customer shares
22.56 / 15.57 / 35.27 / 24.66 / 1.00 / 0.94% and ranks 1, 2, 3.

### Repository checks

| Suite | Result |
|---|---|
| `tableau/scripts/validate_tableau_extracts.py` | **20/20**. Every extract value equals the CSVs; revenue 13,494,400.74; 190 blank cohort cells; all references resolve (6 extracts inside the `.twbx`, no local path, no credentials); 10 data sources, 49 worksheets, 8 dashboards; 100/100 formulas identical to the registry; every dashboard zone, filter, parameter and action resolves; nothing lost from the earlier workbook; official 2026.3 XSD valid |
| `scripts/run_all_validations.py` | **18 PASS · 0 FAIL · 6 deliberate SKIP** (SQL 71/71, calculations 264/264, sources 90/90, data readiness 24/24, KPI workbook 17/17, extracts 21/21, insight evidence 78/78, notebooks, repository 18/18) |

## 7. Remaining issues and limits

- **Clicks not tested.** UI scripting is not available on this Mac, so the click-a-state filter actions and
  the drill-through / back menu actions were not clicked. Their markup is unchanged from the published version.
  Filter and parameter logic was tested with saved values (§6).
- **Screenshots** are Tableau Desktop window captures (top ~85% of each page), not the Tableau Public view.
  Please check the republished pages once in a browser.
- **Recent-files list.** The scratch copies opened by the tests (names starting `RP_`, `shot_`, `fix_`) appear
  in Tableau's start-page list of recent workbooks. You can remove them there; they are temporary files.
- Cosmetic, not fixed: the stage chart shows 3 decimals (0.402) instead of 2; Tableau appends "along category" to
  two measure labels on the Products table and Category Detail.

## 8. Ready for republishing?

**Yes.** `tableau/RetailPulse_Final.twbx` is fixed, validated in Tableau and packaged with the six extracts. To
republish (your action):
1. Open `tableau/RetailPulse_Final.twbx` in Tableau Public Desktop.
2. Choose **Server ▸ Tableau Public ▸ Save to Tableau Public**, sign in, and keep the same name
   (*RetailPulse — Brazilian E-Commerce Analytics*) so it overwrites the published version.
3. Check the eight pages once in a browser.

Nothing was published or pushed to GitHub by Claude.
