# Phase 2 — Spreadsheet Exploration Report

**Date:** 2026-11-13
**Workbook:** `excel/RetailPulse_Phase2_Exploration.xlsx` (15 sheets, 22 MB)
**Engine:** LibreOffice Calc 26.8.3.1 (macOS, Apple Silicon)
**Status:** ✅ **PASSED** — 17 of 17 computable KPIs reconcile with Python; 0 formula errors

---

## 1. Purpose

Phase 1 profiled the data with pandas. Phase 2 re-derives the same headline
numbers in a spreadsheet, **independently**, using ordinary formulas.

The point is not redundancy. Two tools built by different people, using
different engines, arriving at the same number is real evidence the number is
right. If they disagree, one has a bug — and finding out which is worth more
than either answer alone.

There is a second reason: pivot tables, `SUMIFS` and spreadsheet reasoning are
still tested in Data Analyst interviews, and this phase produces the evidence
that the skill is real.

---

## 2. Methodology

### 2.1 Everything in the summary sheets is a live formula

No value in this workbook was pasted from Python. Every summary cell contains
a real `SUMIFS`, `COUNTIFS`, `AVERAGEIFS`, `MEDIAN` or `COUNTA` pointing at
the data sheets. Click any result and the formula appears in the formula bar.

Example — revenue for a given month:

```
=SUMIFS(DATA_Orders!$M$2:$M$99442,      <- order_revenue
        DATA_Orders!$H$2:$H$99442, A5,   <- order_month = this row's month
        DATA_Orders!$F$2:$F$99442, 1)    <- revenue_eligible = 1
```

Bounded ranges (`$M$2:$M$99442`) are used rather than whole columns (`M:M`).
LibreOffice evaluates a bounded range far faster than one spanning all
1,048,576 rows, and on 311,315 data rows that difference is the difference
between a workbook that recalculates and one that hangs.

### 2.2 Three sheets, three grains — kept deliberately apart

| Sheet | Rows | Grain |
|---|---|---|
| `DATA_Orders` | 99,441 | one row per **order** |
| `DATA_Items` | 112,650 | one row per **product line** |
| `DATA_Reviews` | 99,224 | one row per **review record** |

They are **not** merged into one table. Merging them is precisely what
produces double-counted revenue — quantified in section 5.

Order-level measures (revenue, AOV, delivery) come from `DATA_Orders`, where
items, payments and reviews have already been aggregated to one row per order.
Product and category measures come from `DATA_Items`, because a category
belongs to a product, not to an order.

### 2.3 Geolocation was deliberately excluded

The 1,000,163-row geolocation table is not in the workbook. It is reference
data for map visuals, no KPI depends on it, and including it would have more
than quadrupled the file for nothing. The business tables used here are
between 71 and 112,650 rows — comfortable for a spreadsheet.

### 2.4 How recalculation was verified

`openpyxl`, the Python library that wrote the workbook, writes formula *text*
but **cannot evaluate it**. Until a real spreadsheet engine opened the file,
every summary cell was just a string, and claiming validation at that point
would have been meaningless.

LibreOffice was therefore driven headlessly to open the workbook, evaluate
every formula, and write the results back:

```bash
soffice --headless --convert-to xlsx --outdir <tmp> \
        excel/RetailPulse_Phase2_Exploration.xlsx
```

The recalculated file was then read back with `openpyxl(data_only=True)` to
extract the computed values, scanned for errors, and installed over the
original — so the workbook you open already has its values calculated.

---

## 3. KPI validation results

**Spreadsheet (LibreOffice) vs Python (pandas). 17 of 17 computable KPIs agree.**

| # | KPI | Spreadsheet | Python | Diff |
|---|---|---|---|---|
| 1 | Total orders (all statuses) | 99,441 | 99,441 | 0 |
| 2 | Total orders with line items | 98,666 | 98,666 | 0 |
| 3 | Delivered orders | 96,478 | 96,478 | 0 |
| 4 | Canceled orders | 625 | 625 | 0 |
| 5 | Product revenue — all statuses | 13,591,643.70 | 13,591,643.70 | 0 |
| 6 | Product revenue — eligible | 13,494,400.74 | 13,494,400.74 | 0 |
| 7 | Freight charged | 2,251,909.54 | 2,251,909.54 | 0 |
| 8 | Average Order Value (eligible) | 137.4189 | 137.4189 | 0 |
| 9 | Median order value | *not computable* | 86.90 | — |
| 10 | Avg review score — review grain | 4.0864 | 4.0864 | 0 |
| 11 | Avg review score — order grain | 4.0868 | 4.0868 | 0 |
| 12 | Orders with ≥1 review | 98,673 | 98,673 | 0 |
| 13 | Orders with a real delivery date | 96,476 | 96,476 | 0 |
| 14 | Average delivery time (days) | 12.5587 | 12.5587 | 0 |
| 15 | Median delivery time (days) | 10.22 | 10.22 | 0 |
| 16 | Late deliveries | 7,827 | 7,827 | 0 |
| 17 | On-time delivery rate % | 91.8871 | 91.8871 | 0 |
| 18 | Cancellation rate % | 0.6285 | 0.6285 | 0 |
| 19 | Total customers (distinct people) | *not computable* | 96,096 | — |

The workbook contains its own self-check (`04_KPI_Validation!C25`) which counts
rows differing by more than 0.011. **It reads 0.**

Breakdowns were spot-checked too, not just totals: the top five categories and
top three states by revenue agree with pandas **to the cent**.

### 3.1 Three apparent mismatches, and what they actually were

On the first comparison, three KPIs showed differences of −0.0011, −0.0013 and
−0.0029. These were investigated rather than waved away, and the cause was
**my own rounding, not a disagreement**: the Python reference values had been
rounded to 2 decimal places when stored, while the spreadsheet computed at full
precision.

| Metric | Python unrounded | Python stored (2dp) | Spreadsheet |
|---|---|---|---|
| Average Order Value | 137.4189 | 137.42 | 137.4189 |
| Average delivery days | 12.5587 | 12.56 | 12.5587 |
| On-time rate % | 91.8871 | 91.89 | 91.8871 |

Against the **unrounded** Python values the spreadsheet matches to 4 decimal
places on all three. No real discrepancy existed.

**The lesson is worth keeping:** a difference in the fourth decimal place is
almost always a formatting or rounding artifact. A difference in the first
significant figure is a logic bug. Knowing which you are looking at saves hours.

### 3.2 One genuine formula error — found and fixed

The first recalculation returned `#VALUE!` in `04_KPI_Validation!C25`, the
self-check cell. The original formula was:

```
=SUMPRODUCT(--(ABS(E5:E23)>0.01))
```

`ABS()` cannot operate on text, and two rows in that range hold the literal
`—` for the non-computable KPIs. Replaced with:

```
=COUNTIFS(E5:E23,">0.011")+COUNTIFS(E5:E23,"<-0.011")
```

`COUNTIFS` ignores non-numeric cells. After re-recalculation: **0 formula
errors across all 15 sheets.**

---

## 4. Two things a spreadsheet genuinely cannot do

Reported as findings, not worked around.

### 4.1 Distinct count at this scale

Counting the 96,096 distinct `customer_unique_id` values has no practical
spreadsheet solution here:

- `SUMPRODUCT(1/COUNTIF(range,range))` on 99,441 rows is roughly **10 billion
  comparisons** — it hangs.
- Excel 365's `UNIQUE()` would work, but is not available in LibreOffice Calc.
- LibreOffice pivot tables have **no Distinct Count option at all**. Excel has
  one, but only via the Data Model.

In SQL this is `COUNT(DISTINCT customer_unique_id)` — instant. **This is a
concrete reason the project moves to MySQL in Phase 4**, and a good answer to
the interview question *"when would you stop using Excel?"*

### 4.2 Conditional median

`MEDIAN` has no `MEDIANIFS` counterpart. Filtering to eligible orders needs an
array formula entered with Ctrl+Shift+Enter:

```
=MEDIAN(IF((DATA_Orders!F2:F99442=1)*(DATA_Orders!K2:K99442=1),
            DATA_Orders!M2:M99442))
```

It evaluates but is slow, so it is documented in the workbook rather than
embedded. Python returns **86.90 BRL** instantly.

### 4.3 On pivot tables — an honest limitation

The workbook ships **formula-driven summaries, not pre-built native pivot
tables.** `openpyxl` can read and preserve an existing pivot table but cannot
create one from scratch — the feature does not exist in the library.

Rather than substitute static tables and call them pivots, the workbook does
two things:

1. **Live formulas** that recalculate when data changes — genuinely dynamic,
   and verified above against Python.
2. **Sheet `11_Pivot_Exercises`** — eight pivot tables specified field by
   field (source sheet, rows, values, filter), each with the formula sheet to
   check your answer against.

Building those eight by hand is the actual learning, and it is the part an
interviewer can ask you about.

---

## 5. The fan-out problem — measured, not described

The most common way to get a wrong answer from this dataset, quantified on the
real data.

An order is **one** row in `orders`, but can be several rows in `order_items`
(one per product), several in `payments` (one per instalment) and occasionally
several in `reviews`. Join them on `order_id` and the rows multiply — every
duplicated row carrying a duplicated price.

| Approach | Rows produced | Revenue reported | Error |
|---|---|---|---|
| **Correct:** `SUM(price)` on `order_items` alone | 112,650 | **13,591,643.70** | — |
| `order_items` joined to `payments` | 117,601 | 14,209,115.34 | **+4.54%** |
| `order_items` inner-joined to `reviews` | 112,372 | 13,527,224.77 | **−0.47%** |

**Why payments inflate.** Brazilian customers frequently pay in instalments,
and one order can carry up to 29 payment rows. Joining items to payments turned
112,650 item rows into 117,601 and added **617,471 BRL of revenue that does not
exist**.

**Why the reviews join is more dangerous.** It moved revenue the *other* way,
by only −0.47%. An `INNER JOIN` both duplicates (547 orders have 2–3 reviews)
and silently deletes (768 orders have none). The two errors partly cancel,
leaving a number that looks almost right and is not. **A small error is far
harder to spot than a large one** — a 4.5% jump invites investigation; a 0.5%
drift gets shipped.

**The rule that prevents both:** decide the grain of your answer first, then
aggregate every other table *to that grain* before joining. That is exactly why
`DATA_Orders` exists in this workbook — items, payments and reviews are already
collapsed to one row per order, so it is safe to pivot.

---

## 6. Business observations

All figures computed by the spreadsheet and cross-checked against Python.

### 6.1 Growth is real, and it is volume, not price

Like-for-like January–August (the only honest year-over-year comparison, since
2016 holds just 329 orders):

| | 2017 Jan–Aug | 2018 Jan–Aug | Change |
|---|---|---|---|
| Revenue (revenue-eligible) | 3,080,850.81 | 7,341,037.41 | **+138.3%** |
| Orders placed (all statuses) | 22,968 | 53,991 | **+135.1%** |
| Orders in the AOV denominator (eligible, with items) | 22,562 | 53,530 | **+137.3%** |
| **AOV** (eligible revenue ÷ eligible orders with items) | **136.55** | **137.14** | **+0.4%** |

Revenue more than doubled, and almost all of it came from **more orders, not
bigger ones**. AOV did not move.

> **Correction (2026-11-20).** This table originally reported AOV as
> 134.14 → 135.97 (+1.4%). Those figures divided **revenue-eligible** revenue
> by **all-status** order counts, so the numerator excluded canceled and
> unavailable orders while the denominator included them. Numerator and
> denominator must describe the same orders; on the KPI definition AOV is
> 136.55 → 137.14 (+0.4%). The all-status order count is kept above because it
> is a legitimate "orders placed" volume measure — it is simply not the AOV
> denominator. The workbook itself was not affected: sheet
> `05_Revenue_By_Month` already uses the correct denominator. The growth engine is acquisition; basket size
has not been worked on. That is a strategic observation with an obvious
follow-up question for Module 2.

### 6.2 November 2017 is the only month to break 1 million BRL

7,544 orders and 1,003,862 BRL — roughly 50% above the surrounding months.
This is Black Friday. December then *drops* to 742,184, so the spike pulls
demand forward rather than starting a higher plateau.

Note the cost: **November 2017 has the worst review score of 2017 (3.91)**
against a 4.0864 overall average. Peak volume coincided with the worst
customer experience of the year.

### 6.3 Revenue is extremely concentrated geographically

| State | Orders | Revenue | Share | Avg delivery |
|---|---|---|---|---|
| SP (São Paulo) | 41,746 | 5,163,867 | **38.3%** | 8.8 days |
| RJ (Rio de Janeiro) | 12,852 | 1,811,623 | 13.4% | 15.3 days |
| MG (Minas Gerais) | 11,635 | 1,573,508 | 11.7% | 12.0 days |

**The top 3 of 27 states hold 63.4% of revenue.**

### 6.4 Delivery time varies 2.7× across the country

| Fastest | Days | | Slowest | Days |
|---|---|---|---|---|
| SP | 8.8 | | PA | 23.8 |
| PR | 12.0 | | MA | 21.6 |
| MG | 12.0 | | CE | 21.3 |

A customer in Pará waits **15 days longer** than one in São Paulo. Note that
the slow states are also the low-revenue ones — cause and effect run in both
directions, and Module 5 should test which dominates.

### 6.5 Undelivered orders get savagely bad reviews

Average review score by order status is the most striking pattern in the
workbook:

| Status | Avg review |
|---|---|
| delivered | **4.16** |
| approved | 2.50 |
| created | 2.33 |
| shipped | **2.00** |
| canceled | 1.80 |
| invoiced | 1.64 |
| unavailable | 1.53 |
| processing | **1.27** |

Customers whose order is still `processing` average **1.27 stars** — they are
reviewing the *wait*, not the product. The gap between delivered (4.16) and
everything else is enormous. Fulfilment, not product quality, is the dominant
driver of satisfaction in this marketplace.

### 6.6 Review scores are J-shaped, so the average misleads

| Score | Reviews | Share |
|---|---|---|
| 5 ★ | 57,328 | 57.78% |
| 4 ★ | 19,142 | 19.29% |
| 3 ★ | 8,179 | 8.24% |
| 2 ★ | 3,151 | 3.18% |
| 1 ★ | 11,424 | **11.51%** |

More 1-star reviews than 2-star and nearly as many as 3-star combined. The mean
of 4.09 describes almost nobody: the real story is 77% delighted and 11.5%
angry, with little in between. **Any dashboard showing only the average is
hiding the most actionable segment.**

### 6.7 Category revenue is broad, not top-heavy

| Category | Revenue | Share |
|---|---|---|
| health_beauty | 1,255,695 | 9.3% |
| watches_gifts | 1,198,185 | 8.9% |
| bed_bath_table | 1,035,964 | 7.7% |
| sports_leisure | 979,741 | 7.3% |
| computers_accessories | 904,322 | 6.7% |

The top 10 of 74 categories hold **62.4%** of revenue — concentrated, but far
less so than geography (63.4% in 3 states). No single category dominates, so
category risk is lower than regional risk.

### 6.8 The two review-score averages differ, and both are correct

Review grain gives **4.0864**; order grain gives **4.0868**. Neither is wrong.
547 orders carry 2–3 reviews, so averaging all review *rows* weights those
orders more heavily than averaging one figure *per order*.

The difference is tiny here, but the principle is not: **"average review score"
and "average order rating" are different metrics** and must never share a
label. This is the clearest small example in the project of why grain belongs
in every metric definition.

---

## 7. Limitations of this phase

| Limitation | Impact | Resolution |
|---|---|---|
| No distinct count | Cannot count customers in-sheet | SQL `COUNT(DISTINCT ...)` in Phase 4 |
| No `MEDIANIFS` | Conditional median needs a slow array formula | Python / SQL |
| No native pivot tables created programmatically | `openpyxl` cannot build them | Live formulas + 8 guided exercises in sheet 11 |
| Geolocation excluded | No map analysis in the workbook | Phase 6 dashboard (state-level bars; no map) |
| 22 MB workbook | Slow to open; heavy in Git | Regenerable via `scripts/build_phase2_workbook.py` |
| Recalculation takes minutes | 311k rows × many `SUMIFS` | Expected at this scale; itself an argument for SQL |

---

## 8. Deferred manual task

**MT-01 · Monthly Revenue Trend Chart — 🔲 PENDING**

Deliberately left for you to build by hand. Full click-by-click instructions in
[`MANUAL_TASKS.md`](../MANUAL_TASKS.md).

- Sheet `05_Revenue_By_Month`, line chart, Month vs Revenue (BRL)
- **Stable window 2017-01 to 2018-08 only**

Note while building it: **November 2016 is absent from the dataset entirely** —
not a low month, a month with no rows. A chart spanning it would draw a
straight line across a gap with no data behind it. That, more than the sparse
counts, is why the window starts at 2017-01.

This task blocks nothing. Phase 3 is complete without it.

---

## 9. Verdict

| Gate | Result |
|---|---|
| Workbook opens | ✅ 15 sheets, 22 MB |
| Formulas recalculate | ✅ LibreOffice 26.8.3.1 |
| Formula errors | ✅ 0 (1 found and fixed) |
| Computable KPIs reconciling | ✅ **17 / 17** |
| Breakdowns cross-checked | ✅ categories and states agree to the cent |
| Workbook saved with values | ✅ |
| Raw data modified | ✅ No |

**Phase 2: PASSED.**
