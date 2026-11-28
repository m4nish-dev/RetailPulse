# RetailPulse — Tableau Public on macOS: Step-by-Step Build Guide

**For:** a first-time Tableau user on a Mac (Apple silicon, e.g. M2). Free software only; no MySQL
connection needed inside Tableau.
**You will build:** 6 dashboards and 2 detail dashboards from
[`dashboard_specification.md`](dashboard_specification.md), using the formulas in
[`calculated_fields.md`](calculated_fields.md) and the model in
[`data_model.md`](data_model.md).
**Tick progress in:** [`tableau_completion_checklist.md`](tableau_completion_checklist.md).

> **Honest status.** Everything that can be done without Tableau's screen is done and checked:
> - the data files
> - the logic of all 90 formulas (264 checks against SQL)
> - a **generated workbook** with all six data sources, relationships, field names, types,
>   100 calculated fields, 2 parameters and 8 KPI check sheets, checked against Tableau's official
>   2026.3 schema (16/16)
>
> **Nobody has opened that workbook in Tableau yet.** Opening it (§1A) is the first real test.
> If Tableau reports a problem, use the manual route (§2–§6) and note what happened in the
> checklist.

### What is already done for you, and what you do

| Step | Status |
|---|---|
| CSV data in `tableau/data/` and `tableau/data/analytical/`, verified | ✅ automated |
| 6 data sources, 2 folder connections, 8 relationships | ✅ in `tableau/RetailPulse.twb` |
| Field names (incl. the 28 renames), data types, dimension/measure roles | ✅ in the workbook |
| 2 parameters, 100 calculated fields with BRL / % / number formats | ✅ in the workbook |
| KPI check sheets 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 5.6, 6.0 | ✅ in the workbook |
| Open the workbook and compare the KPI sheets with the checklist (§1A) | 🔲 **you** |
| Build the 39 chart/table sheets, 8 dashboards, filters and actions (§7–§9) | 🔲 **you** (needs Tableau's canvas) |
| Validate, save, publish, verify, screenshots (§10–§14) | 🔲 **you** |

> **Menu names.** Paths marked *(Tableau help)* are quoted from Tableau's own help
> pages. The others are the standard Tableau Desktop menus. If your version words one
> differently, use **Help ▸ Search** with the words given.

Plan for 1–2 days of work. Save after every section (**⌘S**).

---

## 0. Before you start (5 minutes, Terminal)

```bash
cd ~/Desktop/RetailPulse
./venv/bin/python scripts/check_tableau_data.py         # expect: checks: 24 PASS: 24 FAIL: 0
./venv/bin/python scripts/validate_tableau_calcs.py     # expect: checks: 264 PASS: 264 FAIL: 0
./venv/bin/python scripts/build_tableau_workbook.py     # writes tableau/RetailPulse.twb (+ _model_only)
./venv/bin/python scripts/validate_tableau_workbook.py  # expect: checks: 16 PASS: 16 FAIL: 0
./venv/bin/python tableau/scripts/build_tableau_extracts.py     # 6 .hyper extracts + RetailPulse_Final.twbx/.twb
./venv/bin/python tableau/scripts/validate_tableau_extracts.py  # expect: checks: 19 PASS: 19 FAIL: 0
```

The workbook stores the full path of the data folder on this Mac. If you move or rename the
project folder, run `build_tableau_workbook.py` again.

The first command proves the 14 CSV files in `tableau/data/` are complete and match
their manifests byte for byte. The second proves the formulas you will type are
logically right. Both only read; they change nothing. If `tableau/data/` is empty
(for example on a fresh clone), regenerate the files first. This needs MySQL running and
`.env` filled in:

```bash
./venv/bin/python scripts/export_tableau_data.py        # 5 view extracts  -> tableau/data/
./venv/bin/python scripts/export_tableau_sources.py     # 9 analytical CSVs -> tableau/data/analytical/
```

Never edit the CSV files by hand.

### Words used in this guide

| Term | Meaning in plain English |
|---|---|
| **Data source** | A set of CSV files Tableau treats as one connected dataset (we build six) |
| **Relationship** | A link between two tables on a shared key column. Tableau adds up each table separately, so nothing is counted twice |
| **Join** | Merging two tables into one wide table. **Do not use it here**: it repeats rows and inflates totals |
| **Dimension / measure** | A dimension describes or groups (state, month, category). A measure is a number to add up or average (revenue) |
| **Calculated field** | A new field defined by a formula. The 90 measures and 10 helpers are calculated fields |
| **Aggregation** | How rows are combined: SUM, AVG, COUNT, COUNTD (count distinct) |
| **LOD expression** | A formula in `{ }` that fixes the level a number is computed at, e.g. `{FIXED : SUM([revenue])}` is the grand total whatever the view shows |
| **Table calculation** | A formula computed across the marks already in the view (running total, rank, previous month). Its **Compute Using** setting says along which field |
| **Mark** | One bar, point, cell or text value in a worksheet |
| **Worksheet / dashboard** | A worksheet holds one chart or table. A dashboard arranges several worksheets on one page |
| **Parameter** | A single value the viewer (or an action) can change, e.g. the selected category |
| **Context filter** | A filter applied before the others (grey pill), needed so "Top 10" is computed inside the selected category |
| **Extract** | Tableau's fast internal copy of the data (`.hyper` file) |
| **Packaged workbook (.twbx)** | One file containing your workbook and its data |

---

## 1. Download and install (free)

1. Create a free **Tableau Public** account at <https://public.tableau.com> (**Sign Up**).
   You need it to publish (§12), not to build.
2. Download **Tableau Desktop Public Edition**, the free desktop app. Go to
   <https://www.tableau.com/products/public/download>, or use the download link on
   <https://public.tableau.com>. On an Apple-silicon Mac
   (M1/M2/M3/M4), pick the **Mac (Apple Silicon)** installer if you are offered a choice.
   *Alternative:* `brew install --cask tableau-public` (the Homebrew package, listed
   for macOS 13 or later).
3. Open the downloaded `.dmg` and run the installer. Start the app from Applications.

What the free edition can and cannot do *(Tableau help, feature comparison)*:

| Can | Cannot |
|---|---|
| Connect to **Text files** (CSV), Excel, JSON, PDF, Google Drive, spatial and statistical files | Connect to MySQL or other databases (we do not need it) |
| Analyse up to **15 million rows** per data source (our largest: 293,753) | Keep published work private |
| **Save workbooks locally** or to Tableau Public (10 GB of storage) | Be used commercially |

---

## 1A. Open the prepared workbook (replaces §2–§6)

1. **Close any draft.** If Tableau is open with a draft workbook (for example "Book1"), choose
   **File ▸ Close** and click **Don't Save**. If Tableau offers to recover an unsaved workbook
   when it starts, decline: the generated workbook replaces that draft.
2. **Open the workbook.** **File ▸ Open…**, go to `~/Desktop/RetailPulse/tableau/`, choose
   **`RetailPulse_Final.twbx`**, click **Open**. (Double-clicking the file in Finder also works.)
   This packaged workbook contains its data as six Tableau **extracts** (`.hyper` files inside the
   package), which Tableau Public requires. It is self-contained: no folder paths to fix. **It already
   contains the 8 dashboards and all 49 worksheets** (charts, filters, captions, drill-through actions).
   It was tested in Tableau 2026.3.2: every dashboard opens without an error, all six extracts connect,
   and every sheet shows the specified figures (`reports/tableau_final_validation.md`). The dashboards
   are the tabs at the bottom; the chart sheets are hidden (right-click a tab ▸ **Unhide All Sheets**
   to see them).
   *History:* the first generated workbook failed with error **D2E8DA72** (`manual-sort`; fixed, see
   `reports/tableau_workbook_repair_report.md`). The repaired one opened but used live CSV
   connections, so Tableau Public refused it with error **3C242D89** ("must use extracts"). The
   Final workbook fixes both; see `reports/tableau_extract_report.md`.
3. **If Tableau shows an error when opening,** note the exact text and code. Then:
   * try `RetailPulse_Final.twb` (same workbook, reading the extracts from `tableau/extracts/`)
   * if that also fails, open `RetailPulse_repaired.twb` (live CSV connections, opens on this Mac)
     and turn each data source into an extract inside Tableau: **Data Source** tab ▸ pick the data
     source in the drop-down at the top left ▸ top right **Connection: Extract** ▸ click any sheet
     tab ▸ **Save** the extract in `~/Desktop/RetailPulse/tableau/extracts/`. Do this for all six
     data sources.

   Write the error in checklist §5. Tableau's log is `~/Documents/My Tableau Repository/Logs/log.txt`.
4. **Extracts are a snapshot.** If the CSVs ever change, rebuild with
   `./venv/bin/python tableau/scripts/build_tableau_extracts.py` and reopen the Final workbook.
5. **Check the data model.** Click the **Data Source** tab (bottom left). In the drop-down at
   the top left, pick each of the six data sources in turn:
   - The canvas shows the root table with lines (relationships) to the related tables, as in
     [`data_model.md` §3](data_model.md#3-relationships).
   - Click a line to see its matching fields, e.g. `order_id` = `order_id`.
   - The grid below shows the rows; the field names are the CSV names; `order_month` (in
     RP Categories) shows as text (Abc).
6. **Check the numbers.** Click each sheet tab at the bottom: **1.0 KPIs**, **1.5 YoY Jan–Aug**,
   **2.0 KPIs**, **3.0 KPIs**, **4.0 KPIs**, **5.0 KPIs**, **5.6 Stage Shares**, **6.0 KPIs**. Each
   shows its KPI values side by side. Compare them with
   [`tableau_completion_checklist.md` §4](tableau_completion_checklist.md) and tick each match.
   If a value differs, note it in §5 of the checklist before going on.
7. **Check one formula by eye.** In the Data pane, right-click **Revenue MoM %** ▸ **Edit…**:
   the formula matches [`calculated_fields.md`](calculated_fields.md) and the editor says
   "The calculation is valid." Close with **Cancel**.
8. **Save your own copy:** **File ▸ Save As…** → `~/Desktop/RetailPulse/tableau/RetailPulse_build.twbx`
   (packaged workbook; git-ignored; keeps the extracts). Work in this copy from now on, so the
   generated file stays a clean starting point.

Sections §2–§10 are **not needed any more**: the sheets, dashboards, filters and actions are already
built. Click through the dashboards once (try the state filter, click a state bar, and on Products right-click
a category ▸ *Category Detail*), then go to **§11 Before publishing** and **§12 Publish**.

---

> **Manual fallback: §2–§6.** Only needed if the generated workbook does not open. They build
> the same model by hand.

## 2. Connect the first data source: RP Orders

1. On the start page, under **Connect ▸ To a File**, click **Text file**.
2. Go to `~/Desktop/RetailPulse/tableau/data/`, choose **`vw_order_summary.csv`** and click **Open**.
   The Data Source page opens with this table on the canvas. It is the **root** table.
3. From the left panel (**Files**), drag **`vw_review_summary.csv`** onto the canvas next to
   it. A line (a *relationship*) appears and the **Edit Relationship** panel opens. Set
   `order_id` = `order_id`. Close the panel.
   *Never* double-click into a table to create a join. Joins multiply rows: the
   validator shows a join here changes revenue by R$ 62,515.94 (pitfall P05).
4. `delivery_stage_orders.csv` is in a different folder. In the left panel next to
   **Connections**, click **Add ▸ Text file**, open
   `~/Desktop/RetailPulse/tableau/data/analytical/delivery_stage_orders.csv`. Drag it from
   the new connection's file list onto the canvas, next to `vw_order_summary`.
   Relationship: `order_id` = `order_id`.
5. Leave **Performance Options** at the defaults (*Many*, *Some records match*).
6. Name the data source: click its name at the top of the page (e.g.
   "vw_order_summary+") and type **`RP Orders`**.
7. Top right, set **Connection** to **Extract**.

Check the relationships against [`data_model.md` §3](data_model.md#3-relationships).

## 3. Connect the other five data sources

Use **Data ▸ New Data Source** (or the **New Data Source** icon) each time, then repeat
the §2 pattern. The first file you open becomes the root table; every other table relates to the root
on the key shown.

| Data source name | First file (root) | Add, with relationship key | Folder(s) |
|---|---|---|---|
| `RP Customers` | `vw_customer_summary.csv` | `rfm_customer_segments.csv` on `customer_unique_id` | `tableau/data/` + `tableau/data/analytical/` (Add ▸ Text file) |
| `RP Cohorts` | `cohort_retention.csv` | n/a | `tableau/data/analytical/` |
| `RP Categories` | `dim_category.csv` | `vw_category_performance.csv` (from `tableau/data/`), then `product_performance.csv`, then `category_satisfaction.csv`, each on `category` | both |
| `RP Sellers` | `vw_seller_performance.csv` | `seller_scorecard.csv`, then `seller_category_performance.csv`, each on `seller_id` | both |
| `RP Stage Summary` | `delivery_stage_summary.csv` | n/a | `tableau/data/analytical/` |

**Add the tables in the order listed.** The rename list in §4 depends on it.
Set **Connection: Extract** on each.

## 4. Fix field names and data types (manual route only)

Do this on each data source's **Data Source page**.

**4a. Undo Tableau's automatic renaming.** Tableau tidies CSV names on connection.
Underscores become spaces and the first letter is capitalised, so `customer_state` no
longer matches the formulas. *(Tableau help: "Understand Field Type Detection and Naming
Improvements".)*
1. Below the canvas, click the **metadata grid** icon (the list view).
2. Select every row: click the first, then **Shift-click** the last. Use **⌘-click** to add rows.
3. Click the drop-down arrow on any selected field name and choose **Reset name**.
4. The names now match the CSV headers exactly (`customer_state`, `order_id`, …).

**4b. Rename duplicate columns.** In the same grid, the **Table** column shows each
field's table. For every row in
[`calculated_fields.md` § Field renames](calculated_fields.md#field-renames-required-before-entering-formulas)
(28 renames across RP Orders, RP Customers, RP Categories and RP Sellers), find the
field in the named table and set it to the **New name**. To rename, click its name ▸ Rename.
Whatever Tableau shows for the duplicate before you rename it, the result must
match exactly, e.g. `rev_order_id`, `scp_late_orders`.

**4c. Data types.** Click the small type icon (Abc / # / calendar) at the top of a column
to change it. Set the types in [`data_model.md` §5](data_model.md#5-data-types-set-on-the-data-source-page-click-the-type-icon-above-each-column).
The essentials:
* `order_date` → **Date**
* `order_month` in RP Categories, and `cohort_month` → **String**
* every `*_id` → **String**
* the 0/1 flags stay **Number**

**4d. Row counts.** Open a new sheet. For each table, drag its **`<table>(Count)`** field
(Tableau names it this way, *Tableau help*) onto **Text**. It must equal `_manifest.csv`:
* RP Orders: 99,441 orders, 99,224 reviews and 95,088 stage rows
* RP Customers: 96,096
* RP Cohorts: 400
* RP Categories: 74 categories, 1,282 category-month rows, 32,951 products and 74 satisfaction rows
* RP Sellers: 3,053 sellers, 3,053 scorecard rows and 6,545 seller-category rows

The first time you open a sheet with an Extract connection, Tableau asks where to save
the extract (`.hyper`). Save it in **`~/Desktop/RetailPulse/tableau/extracts/`**. That
folder is git-ignored, because extracts contain data.

## 5. Parameters (2)

**Data pane ▸ drop-down arrow (top right of the pane) ▸ Create Parameter…**

| Name | Data type | Current value | Allowable values |
|---|---|---|---|
| `p_category` | String | `health_beauty` | All |
| `p_seller` | String | `4869f7a5dfa277a7dca6462dcf3b52b2` | All |

Parameters belong to the workbook, so every data source can use them.

## 6. Calculated fields (100: 90 measures + 10 helpers)

For each entry in [`calculated_fields.md`](calculated_fields.md), in order (helpers H01–H10 first):

1. In the Data pane, select the **data source named in the entry** (e.g. *RP Orders*).
2. **Analysis ▸ Create Calculated Field…**
3. Type the **Name** exactly as given (e.g. `Total Revenue`). Later formulas refer to it.
4. Copy the formula from the grey box and paste it. The bottom of the editor must
   say **"The calculation is valid."** If it shows an error, check the field names
   (§4) first. If the error persists, record it in the checklist §5 and move on.
5. Click **OK**.
6. Set the format once. Right-click the new field ▸ **Default Properties ▸ Number Format…**:
   * **BRL** → Currency (Custom): Decimal places **2**, Display Units **None**, Prefix/Suffix **`R$ `**
   * **Percentage** → Percentage, **2** decimals
   * **Number, 0 dp** → Number (Custom), 0 decimals, thousands separator on

Tips:
* Names that contain `%` or brackets (e.g. `Revenue MoM %`,
  `Avg Order Rating (Review Table)`) are allowed.
* As you type `[`, Tableau suggests fields. Choosing a suggestion avoids typos.
* Table calculations (type *table calculation*, e.g. `Revenue MoM %`) are entered the same way. Their
  **Compute Using** is set later, on the sheet.

**Quick check after entering RP Orders' fields.** On a new sheet, put `Total Revenue`,
`Total Orders`, `Total Customers`, `Average Order Value` and `Median Order Value` on Text.
Expected: R$ 13,494,400.74 · 99,441 · 96,096 · R$ 137.42 · R$ 86.90.

## 7. Worksheets

> Sheets **1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 5.6 and 6.0 already exist** in the generated workbook.
> Build the other 39 sheets below. All fields and calculations they need are already in the
> Data pane, under their data source.

Build every sheet listed in [`dashboard_specification.md`](dashboard_specification.md)
(1.0–8.4, 47 sheets). Rename each tab to the sheet name given: double-click the tab at the bottom.
How to read a build line such as *"Rows `customer_state`; Columns `Total Revenue` (Bar)"*:

| Instruction | What you do |
|---|---|
| **Columns / Rows `field`** | Drag the field from the Data pane onto the **Columns** or **Rows** shelf |
| **(Bar) / (Line) / Square / Text / Pie** | Marks card ▸ drop-down ▸ choose the mark type |
| **Color / Size / Label / Detail / Tooltip `field`** | Drag the field onto that button of the Marks card |
| **`Order Month` (green, continuous Month)** | Drag `Order Month`, right-click the pill ▸ choose the lower **Month** (green = continuous) |
| **(discrete month)** | Right-click the pill ▸ the upper **Month** (blue = discrete) |
| **KPI strip** | Drag `Measure Names` to Columns, `Measure Values` to **Text**. Remove the unwanted measures from the **Measure Values** card (drag them off) |
| **Compute Using `X`** | Right-click the table-calculation pill ▸ **Compute Using ▸ X**. For several dimensions: **Edit Table Calculation… ▸ Specific Dimensions**, tick only X |
| **Filter `field` = 1 / True** | Drag the field to **Filters**, tick 1 (or True), OK |
| **Top 12 by `Total Revenue`** | Drag the dimension to **Filters** ▸ **Top** tab ▸ **By field** ▸ Top **12** by **Total Revenue** |
| **Add to context** | Right-click the filter pill ▸ **Add to Context** (the pill turns grey). Needed on detail sheets so Top 10 is computed *inside* the category |
| **Special ▸ Non-null values** | Drag the measure to Filters ▸ **Special** tab ▸ **Non-null values** |
| **Sort desc by a field** | Right-click the dimension pill ▸ **Sort…** ▸ Sort By **Field** ▸ Descending ▸ choose the field |
| **Logarithmic axis** | Right-click the axis ▸ **Edit Axis…** ▸ Scale ▸ **Logarithmic** |
| **Reference line** | **Analytics** pane (tab next to Data) ▸ drag **Reference Line** onto the view ▸ Value: Constant / Median |
| **Bins** | Right-click the measure (e.g. `delivery_days`) ▸ **Create ▸ Bins…** ▸ Size of bins |
| **Hide headers** | Right-click the header ▸ untick **Show Header** |

**Table-calculation filters (the detail dashboards).** On sheets 7.1 and 8.1, put
`Selected Category TC` / `Selected Seller TC` on Filters (tick True), **not** the
`Is Selected …` field. A table-calculation filter is applied last, after rank and
cumulative share have been computed over all categories or sellers. A normal filter
would leave one row and show rank 1 / 100% for everything.

## 8. Dashboards (6 + 2)

For each dashboard in the specification:

1. **Dashboard ▸ New Dashboard**; rename the tab (e.g. `1 Executive`).
2. Left **Dashboard** pane ▸ **Size** ▸ **Fixed size**: 1400 × 1150 (detail: 1400 × 1000).
3. Drag a **Vertical** container (Objects) to the left edge for navigation. Then drag a
   **Horizontal** container across the top for the title and filters.
4. Drag the sheets in. KPI strip at the top, main sheet left (~60%), supporting
   sheet right, detail sheet full width below.
5. **Captions:** drag a **Text** object under the sheet and paste the exact caption
   from the specification. The mandatory captions are marked there.
6. **Footer:** a Text object at the bottom with the footer text from the specification.
   It includes the dataset licence attribution.
7. **Navigation:** for each of the six main dashboards, drag **Navigation** (Objects)
   into the left container. Click the button's drop-down ▸ **Edit Button…** ▸
   **Navigate to** the dashboard, and set **Title** (e.g. "1 Executive"). Style the current
   dashboard's button orange `#D95926` and the others charcoal. Copy the finished
   column to the other dashboards: select the container ▸ ⌘C, then ⌘V on the next
   dashboard.
8. **Detail dashboards 7 and 8:** no navigation column. Add one Navigation button
   "← Back to Products" / "← Back to Sellers" top left. Add a Text object with
   "Category: " and **Insert ▸ Parameters.p_category** (or `p_seller`).

## 9. Filters, parameters and actions

**Filters on a dashboard.** Select a sheet on the dashboard ▸ its drop-down (▾) ▸
**Filters ▸** the field. The filter card appears. On the card's drop-down choose
**Apply to Worksheets ▸ Selected Worksheets…** and tick exactly the sheets listed in
the specification table. **Executive:** leave **1.5 YoY** unticked for the Year and
Order Month filters. It must ignore dates (it compares fixed Jan–Aug periods).

**Actions.** **Dashboard ▸ Actions… ▸ Add Action ▸**

| On dashboard | Action | Settings |
|---|---|---|
| 3 Products | **Change Parameter…** "Set category" | Source sheets 3.1, 3.2, 3.4, 3.5 · Run action on **Select** · Target parameter `p_category` · Source field `category` · Clearing the selection will **Keep current value** |
| 3 Products | **Go to Sheet…** "Open Category Detail" | same source sheets · Run action on **Menu** · Target sheet `7 Category Detail` |
| 4 Sellers | **Change Parameter…** "Set seller" | Source sheets 4.1, 4.3, 4.4 · **Select** · `p_seller` · Source field `seller_id` |
| 4 Sellers | **Go to Sheet…** "Open Seller Detail" | same sources · **Menu** · `8 Seller Detail` |

How it works for a viewer:
1. Click a category bar. This sets `p_category`.
2. Hover over it and click **Open Category Detail** in the tooltip menu.
3. The detail dashboard opens for that category.
4. "← Back to Products" returns.

## 10. Validate the numbers (record each in the checklist)

1. **Cards:** compare every KPI with
   [`tableau_completion_checklist.md` §4](tableau_completion_checklist.md). Every expected
   value there was computed on macOS (SQL and the validated emulation).
2. **Filter tests:** apply each test in the checklist §6, e.g. customer_state = SP → Total
   Revenue R$ 5,163,867.22, and compare.
3. **Blanks by design:** Revenue MoM % at 2017-01, the 3M average before 2017-03,
   unobserved cohort cells, and the late/on-time rates for status `unavailable`. These
   must be **empty**, not 0 or 100%.
4. **Drill-through:**
   * click `health_beauty` ▸ Open Category Detail → R$ 1,255,695.13 · 9.31% · rank 1 · +444.27% · 8,826 reviews · 4.1822
   * click the largest seller ▸ Open Seller Detail → R$ 229,237.63 · 1,131 · 11.57% · 15.06 · 4.136 · 1.70% · 10 categories
5. **If a value differs**, check in this order:
   * field names (§4)
   * the **Compute Using** of table calculations
   * whether a filter applies to that sheet
   * whether a detail filter is in context (grey)

   Then note it in the checklist. Do not "fix" a formula to force a number without
   finding the cause.
6. **Performance:** each dashboard should redraw in a few seconds. If not:
   * confirm every data source shows **Extract**
   * avoid a dropdown filter on `seller_id` or `product_id`
   * Data pane ▸ drop-down ▸ **Hide All Unused Fields** before publishing

## 11. Before publishing: safety checklist

From Tableau's help *(Save Workbooks to Tableau Public)*: "Workbooks and data published
to your Tableau Public profile are not private and are freely accessible to anyone",
and "anyone can interact with your views, or download your workbooks or data sources".
Publishing "creates an extract of the data connection".

| Check | Why |
|---|---|
| The workbook uses only the CSV connections above | the free edition cannot use MySQL anyway, so no database host, user or password can be embedded |
| Nothing from `.env` was typed into the workbook (no text box, caption or calculation) | `.env` holds the MySQL app password; Tableau never reads it, so keep it that way |
| You accept that the 14 CSV extracts become public and downloadable | they contain only the public Olist dataset (anonymised IDs, no names, emails or addresses) and derived aggregates |
| Footer attribution present: "Data: Olist Brazilian E-Commerce Public Dataset (Kaggle), CC BY-NC-SA 4.0" | the dataset licence requires attribution, non-commercial use and the same licence for shared derivatives; the free edition is non-commercial too |
| **Data ▸ (each data source) ▸ Hide All Unused Fields** | smaller workbook; fewer columns published |
| Publish from `RetailPulse_build.twbx` saved from `RetailPulse_Final.twbx` | its extracts are referenced inside the package (`Data/extracts/…`), so no folder path with your Mac user name is stored |

## 12. Publish to Tableau Public

1. Save locally first: **File ▸ Save** (⌘S) your `~/Desktop/RetailPulse/tableau/RetailPulse_build.twbx`
   (made in §1A; if you used the manual route, **File ▸ Save As…** with that name). The free
   edition can save locally; a packaged workbook (`.twbx`) includes the data. This file is
   git-ignored because it contains data.
2. **Server ▸ Tableau Public ▸ Save to Tableau Public…** *(Tableau help: "select Server >
   Tableau Public > Save to Tableau Public")*. It is only available once a sheet uses at
   least one field.
3. Sign in with your Tableau Public account (§1).
4. Type the name **RetailPulse — Brazilian E-Commerce Analytics** and click **Save**. Description to paste on
   the profile: *"Historical analysis of ~100,000 orders from the Olist Brazilian e-commerce marketplace
   (Sep 2016 – Oct 2018): revenue, customers and cohorts, categories, sellers, delivery and reviews. Revenue
   = product revenue in BRL, freight excluded; no cost data, so no profit. Data: Olist Brazilian E-Commerce
   Public Dataset (Kaggle), CC BY-NC-SA 4.0."*
5. Your browser opens the published viz on your profile. Copy its URL.
6. On your profile, open the viz's settings. Choose whether it shows on your profile and
   whether downloads are allowed. Tableau's help mentions hiding and downloading
   options; the exact labels were not confirmed for this guide.

**Republish after changes:** repeat step 2 with the same name. Tableau asks whether to overwrite.

## 13. Verify the published dashboard

Open the URL in a **private browser window** (so you see what the public sees):

* [ ] All 8 dashboards load; the tabs switch between them (no navigation buttons: Tableau rejected them)
* [ ] KPI cards equal the checklist §4 values (spot-check at least Executive and Customers)
* [ ] Filters work; the YoY card does not change when the month filter changes
* [ ] Clicking a category / seller and choosing *Category Detail* / *Seller Detail* in the tooltip menu opens the
  detail page; choosing a category in its dropdown (or pasting a seller_id) shows the test values
* [ ] Captions and the footer attribution are visible
* [ ] Values show as `R$ 1,234.56` and percentages with 2 decimals

## 14. Screenshots (8 real captures)

From the **published** view, at full dashboard size:
* **Mac:** press **⇧⌘4**, then **Space**, and click the browser window. This saves a PNG
  to the Desktop; crop it in Preview if needed.
* *Alternative in the app:* **Dashboard ▸ Export Image…** (desktop app).

Save as the eight names in
[`dashboard_specification.md` § Screenshots](dashboard_specification.md#screenshots-after-the-build)
in `reports/dashboard_screenshots/`. Use real captures only, never mock-ups.

## 15. Final documentation (after verification)

1. `README.md` ▸ Dashboard section: add the Tableau Public URL and the 8 screenshots.
   Change the status to "built and verified" only for what you actually verified.
2. Tick `tableau/tableau_completion_checklist.md` with evidence (value seen,
   screenshot name).
3. Update `documentation/project_completion_checklist.md` §4 and `TASK_TRACKER.md`.
4. Re-run `./venv/bin/python scripts/run_all_validations.py`. Expect 0 FAIL.
5. Review `git status`. **Do not commit** `tableau/*.twbx`, `tableau/extracts/` or any `.hyper`
   file (already git-ignored). Commit the screenshots and documentation. Commit and push
   when you decide to, as yourself only.
