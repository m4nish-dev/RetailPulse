# Manual Tasks

Tasks that require you to work in a GUI application. Each one is self-contained
and **does not block** any other project work.

**Legend:** 🔲 pending · ✅ done

---

## 🔲 MT-01 · Monthly Revenue Trend Chart

**Status:** PENDING — deferred by your request (2026-11-13)
**Blocks:** nothing. Phase 3 and all later work proceed without it.
**Estimated time:** 5–10 minutes
**Why you are doing this by hand:** building a chart in a spreadsheet is a
basic Data Analyst skill that interviewers assume. It is also the quickest way
to see for yourself why the edge months had to be excluded.

### What to build

| Setting | Value |
|---|---|
| Workbook | `excel/RetailPulse_Phase2_Exploration.xlsx` |
| Sheet | `05_Revenue_By_Month` |
| Chart type | Line chart |
| X-axis | Month (column A) |
| Y-axis | Revenue in BRL (column C) |
| **Data range** | **2017-01 to 2018-08 only** |
| Exclude | 2016-09, 2016-10, 2016-12, 2018-09, 2018-10 |

### Why exclude those five rows

They are the boundaries of the data extract, not real business performance:

| Month | Orders |
|---|---|
| 2016-09 | 4 |
| 2016-10 | 324 |
| **2016-11** | **0 — the month is absent from the data entirely** |
| 2016-12 | 1 |
| 2018-09 | 16 |
| 2018-10 | 4 |

Include them and the line plunges to near zero at both ends, implying a
collapse that never happened. The sheet flags these rows in column F.

> **A note on 2016-10, and on the hole in 2016.** 2016-10 has 324 orders,
> above the 200 threshold the profiling used to flag "sparse" months, so the
> sheet does not mark it. It is excluded anyway, for a stronger reason:
> **November 2016 is missing from the dataset completely** — not a low month, a
> month with no rows at all. So 2016 is not merely thin, it is *discontinuous*,
> and a line chart would draw a straight segment straight across a gap that has
> no data behind it.
>
> The stable window therefore starts at **2017-01**, the first month beginning
> an unbroken run. Say this out loud in an interview — knowing *why* a window
> starts where it does, and spotting a missing month rather than a small one,
> is exactly the kind of care the question is testing for.

### Steps in LibreOffice Calc

1. Open `excel/RetailPulse_Phase2_Exploration.xlsx`.
2. If prompted *"This file contains links to other files / recalculate?"*,
   choose **Yes / Recalculate**.
3. Go to the **`05_Revenue_By_Month`** sheet.
4. Find the first row where column A reads `2017-01`, and the row where column
   A reads `2018-08`.
5. Select the **Month** cells (column A) for that range. Then hold **⌘ (Cmd)**
   and select the matching **Revenue (BRL)** cells in column C. You now have
   two non-adjacent columns selected — this is how you chart X and Y without
   the columns in between.
6. Menu: **Insert ▸ Chart…**
7. **Step 1 – Chart Type:** choose **Line**, then the **Lines Only** subtype.
   Click **Next**.
8. **Step 2 – Data Range:** confirm **Data series in columns** is selected, and
   tick **First column as label**. Click **Next** twice to reach step 4.
9. **Step 4 – Chart Elements:**
   - Title: `Monthly Revenue, Jan 2017 – Aug 2018 (BRL)`
   - X axis: `Month`
   - Y axis: `Revenue (BRL)`
   - Untick **Display legend** — there is only one line, so a legend adds
     nothing and the title already names it.
10. Click **Finish**, then click once outside the chart to leave edit mode.
11. **Save as .xlsx** — when prompted, choose **Use Excel 2007-365!**, not ODF.
    The project standard is `.xlsx`.

### Optional polish

- Right-click the Y axis ▸ **Format Axis ▸ Numbers** ▸ set format code
  `#,##0` so revenue reads `1,200,000` rather than `1.2E6`.
- Right-click the line ▸ **Format Data Series ▸ Line** ▸ set the colour to the
  project orange `EB6834` and width to `0.08"` for consistency with the
  notebook charts and the future Power BI theme.
- Right-click the X axis ▸ **Format Axis ▸ Label** ▸ rotate labels 45° if the
  month names overlap.

### What you should see

A line that climbs steeply through 2017, spikes sharply in **2017-11**
(Black Friday), dips in December, then runs roughly flat through 2018 at a
higher level. If instead you see a line that drops to nearly zero at either
end, you included the edge months — undo and reselect the range.

### When you are done

Change this task's status line to ✅ and tick task 2.11 in `TASK_TRACKER.md`.

---

## Tasks that may appear later

| Phase | Likely manual task |
|---|---|
| 6 | Power BI Desktop requires Windows — a VM or cloud Windows machine. See `documentation/environment_setup.md` |
| 6 | Capturing dashboard screenshots into `reports/dashboard_screenshots/` |
| 8 | Creating the GitHub repository and pushing |
