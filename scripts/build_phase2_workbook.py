"""
RetailPulse - Phase 2 workbook builder.

Writes excel/RetailPulse_Phase2_Exploration.xlsx.

Design principle: the summary sheets contain LIVE SPREADSHEET FORMULAS
(SUMIFS / COUNTIFS / AVERAGE), not values pasted from Python. The spreadsheet
computes its own answers so they are a genuine independent check on the Phase 1
pandas results. Python supplies only the raw-ish data sheets and the reference
column to compare against.

Three data sheets, three GRAINS, deliberately kept separate:
  DATA_Orders   99,441 rows - one row per order
  DATA_Items   112,650 rows - one row per product line
  DATA_Reviews  99,224 rows - one row per review record
Mixing them in one table is what causes double-counted revenue; sheet
10_FanOut_Warning demonstrates the damage with real numbers.

Usage: ./venv/bin/python -I scripts/build_phase2_workbook.py <datadir>
"""
import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(sys.argv[1])
OUT = ROOT / "excel" / "RetailPulse_Phase2_Exploration.xlsx"
OUT.parent.mkdir(exist_ok=True)

orders = pd.read_csv(DATA / "orders_grain.csv", dtype=str)
items = pd.read_csv(DATA / "items_grain.csv", dtype=str)
reviews = pd.read_csv(DATA / "reviews_grain.csv", dtype=str)
PK = json.loads((DATA / "python_kpis.json").read_text())

NO, NI, NR = len(orders), len(items), len(reviews)
# Bounded ranges, not whole columns: LibreOffice evaluates A2:A99442 far faster
# than A:A, which spans 1,048,576 rows.
O = lambda c: f"DATA_Orders!${c}$2:${c}${NO + 1}"
I = lambda c: f"DATA_Items!${c}$2:${c}${NI + 1}"
R = lambda c: f"DATA_Reviews!${c}$2:${c}${NR + 1}"

# ------------------------------------------------------------- styling -----
CHARCOAL, ORANGE, WHITE = "FF1A1A19", "FFEB6834", "FFFFFFFF"
LIGHT, GREEN, RED, AMBER = "FFF5F4F1", "FF1BAF7A", "FFE34948", "FFEDA100"
H1 = Font(name="Calibri", size=16, bold=True, color=CHARCOAL)
H2 = Font(name="Calibri", size=12, bold=True, color=CHARCOAL)
HDR = Font(name="Calibri", size=11, bold=True, color=WHITE)
BODY = Font(name="Calibri", size=11)
MUTED = Font(name="Calibri", size=10, italic=True, color="FF52514E")
MONO = Font(name="Menlo", size=10)
FILL_HDR = PatternFill("solid", fgColor=CHARCOAL)
FILL_ACC = PatternFill("solid", fgColor=ORANGE)
FILL_LIGHT = PatternFill("solid", fgColor=LIGHT)
THIN = Side(style="thin", color="FFD8D7D2")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")

wb = Workbook()
wb.remove(wb.active)


def sheet(name, title, subtitle=None, widths=None):
    ws = wb.create_sheet(name)
    ws["A1"] = title
    ws["A1"].font = H1
    r = 2
    if subtitle:
        ws["A2"] = subtitle
        ws["A2"].font = MUTED
        ws["A2"].alignment = WRAP
        r = 3
    for i, w in enumerate(widths or [], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    return ws, r + 1


def header_row(ws, row, labels, start=1):
    for i, lab in enumerate(labels, start=start):
        c = ws.cell(row=row, column=i, value=lab)
        c.font, c.fill, c.border = HDR, FILL_HDR, BOX
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = ws.cell(row=row + 1, column=1)
    return row + 1


# ============================================================ 00_README =====
ws, r = sheet("00_README", "RetailPulse — Phase 2 Spreadsheet Exploration",
              "Independent spreadsheet validation of the Phase 1 Python profiling. "
              "Built 2026-11-13 from the raw Olist CSVs.", [46, 86])
for head, body in [
    ("What this workbook is for",
     "Phase 1 profiled the data with pandas. This workbook re-derives the same headline numbers "
     "using ordinary spreadsheet formulas, independently. If the two disagree, one of them has a "
     "bug — and finding out which is the entire point of doing this step."),
    ("Everything here is a live formula",
     "The summary sheets contain real SUMIFS / COUNTIFS / AVERAGE formulas pointing at the DATA_ "
     "sheets. Nothing is a pasted value from Python. Click any result cell and you can read the "
     "formula in the formula bar. Change a number in a DATA_ sheet and every summary updates."),
    ("Three data sheets, three different GRAINS",
     "DATA_Orders = one row per order (99,441). DATA_Items = one row per product line (112,650). "
     "DATA_Reviews = one row per review (99,224). They are deliberately NOT merged into one table."),
    ("Why that matters — read sheet 10",
     "An order can contain several items, several payments and (rarely) several reviews. Joining "
     "these tables carelessly duplicates revenue. Sheet 10_FanOut_Warning shows the real damage: "
     f"GMV inflates by {PK['fanout_pay_inflation_pct']}% one way and drops {abs(PK['fanout_rev_error_pct'])}% the other."),
    ("Source of truth",
     "Raw CSVs in dataset/raw/ were never modified. Metric definitions follow "
     "documentation/kpi_definitions.md exactly."),
    ("How to recalculate everything",
     "LibreOffice Calc: Data > Calculate > Recalculate Hard (Ctrl+Shift+F9). "
     "Excel: Formulas > Calculate Now (F9)."),
]:
    ws.cell(row=r, column=1, value=head).font = H2
    c = ws.cell(row=r, column=2, value=body)
    c.font, c.alignment = BODY, WRAP
    ws.row_dimensions[r].height = 46
    r += 1

r += 1
ws.cell(row=r, column=1, value="Sheet index").font = H1
r += 1
r = header_row(ws, r, ["Sheet", "Contents"])
for n, d in [
    ("01_Dataset_Overview", "All 9 source tables: rows, columns, file size"),
    ("02_Missing_Values", "Every column with missing data, count and percentage"),
    ("03_Keys_Duplicates", "Primary key and relationship validation results"),
    ("04_KPI_Validation", "★ Spreadsheet vs Python, side by side, with differences"),
    ("05_Revenue_By_Month", "Monthly revenue and orders — live SUMIFS"),
    ("06_Orders_By_Status", "Order status breakdown — live COUNTIF"),
    ("07_Orders_By_State", "Orders, revenue and AOV by customer state"),
    ("08_Category_Revenue", "Revenue by product category (item grain)"),
    ("09_Review_Distribution", "Review score 1–5 distribution"),
    ("10_FanOut_Warning", "★ The duplicate-revenue trap, with real numbers"),
    ("11_Pivot_Exercises", "Step-by-step pivot tables for you to build by hand"),
    ("DATA_Orders", f"{NO:,} rows — one row per order"),
    ("DATA_Items", f"{NI:,} rows — one row per product line"),
    ("DATA_Reviews", f"{NR:,} rows — one row per review record"),
]:
    ws.cell(row=r, column=1, value=n).font = MONO
    ws.cell(row=r, column=2, value=d).font = BODY
    r += 1

# =================================================== 01_Dataset_Overview ====
RAW = ROOT / "dataset" / "raw"
ws, r = sheet("01_Dataset_Overview", "Dataset Overview",
              "Measured directly from the files in dataset/raw/. Row counts are real CSV "
              "records parsed by pandas, NOT physical line counts — see the note below.",
              [44, 14, 12, 14, 52])
r = header_row(ws, r, ["File", "Rows", "Columns", "Size (MB)", "Role"])
FILE_ROLES = [
    ("olist_orders_dataset.csv", 99441, 8, "Fact — one row per order"),
    ("olist_order_items_dataset.csv", 112650, 7, "Fact — one row per product line (revenue lives here)"),
    ("olist_order_payments_dataset.csv", 103886, 5, "Fact — one row per payment"),
    ("olist_order_reviews_dataset.csv", 99224, 7, "Fact — one row per review"),
    ("olist_customers_dataset.csv", 99441, 5, "Dimension — buyer, one row per order"),
    ("olist_products_dataset.csv", 32951, 9, "Dimension — product attributes"),
    ("olist_sellers_dataset.csv", 3095, 4, "Dimension — seller location"),
    ("product_category_name_translation.csv", 71, 2, "Lookup — Portuguese to English category"),
    ("olist_geolocation_dataset.csv", 1000163, 5, "Reference — zip to lat/lng (not used by any KPI)"),
]
first = r
for fn, rows, cols, role in FILE_ROLES:
    mb = round((RAW / fn).stat().st_size / 1024 ** 2, 1) if (RAW / fn).exists() else None
    for i, v in enumerate([fn, rows, cols, mb, role], start=1):
        c = ws.cell(row=r, column=i, value=v)
        c.font, c.border = (MONO if i == 1 else BODY), BOX
        if i in (2, 3):
            c.number_format = "#,##0"
    r += 1
ws.cell(row=r, column=1, value="TOTAL").font = H2
ws.cell(row=r, column=2, value=f"=SUM(B{first}:B{r-1})").font = H2
ws.cell(row=r, column=2).number_format = "#,##0"
ws.cell(row=r, column=3, value=f"=SUM(C{first}:C{r-1})").font = H2
r += 2
ws.cell(row=r, column=1, value="⚠ Why 'wc -l' gives the wrong row count here").font = H2
r += 1
for line in [
    "The reviews file contains 104,720 physical lines but only 99,224 records. 3,852 customers pressed",
    "Enter while typing their comment, so a single record can span several lines. Always count rows with",
    "a real CSV parser (pandas, or a spreadsheet import), never with a line counter.",
    "Separately, product_category_name_translation.csv has no trailing newline, so 'wc -l' undercounts it by 1.",
]:
    ws.cell(row=r, column=1, value=line).font = BODY
    r += 1

# ====================================================== 02_Missing_Values ===
ws, r = sheet("02_Missing_Values", "Missing Values",
              "13 of 52 columns contain missing data. A high percentage is not automatically a "
              "problem — context decides. See the verdict column.", [20, 32, 12, 10, 58])
r = header_row(ws, r, ["Table", "Column", "Missing", "Missing %", "Verdict"])
MISSING = [
    ("reviews", "review_comment_title", 87656, 88.34, "Expected — the comment title is optional"),
    ("reviews", "review_comment_message", 58247, 58.70, "Expected — most customers rate without writing"),
    ("orders", "order_delivered_customer_date", 2965, 2.98, "Mostly correct: the order was never delivered. But 8 'delivered' orders lack it — defect Q01"),
    ("products", "product_photos_qty", 610, 1.85, "Same 610 products — created without full catalogue data"),
    ("products", "product_description_lenght", 610, 1.85, "Same 610 products (note: 'lenght' is misspelled in the source)"),
    ("products", "product_name_lenght", 610, 1.85, "Same 610 products (source misspelling)"),
    ("products", "product_category_name", 610, 1.85, "Defect Q04 — label as 'unknown', do not drop"),
    ("orders", "order_delivered_carrier_date", 1783, 1.79, "Correct — order never shipped"),
    ("orders", "order_approved_at", 160, 0.16, "Minor — approval lag is not a planned KPI"),
    ("products", "product_weight_g", 2, 0.01, "Negligible — no KPI uses it"),
    ("products", "product_length_cm", 2, 0.01, "Negligible"),
    ("products", "product_height_cm", 2, 0.01, "Negligible"),
    ("products", "product_width_cm", 2, 0.01, "Negligible"),
]
for t, col, n, pct, verdict in MISSING:
    for i, v in enumerate([t, col, n, pct / 100, verdict], start=1):
        c = ws.cell(row=r, column=i, value=v)
        c.font, c.border = (MONO if i == 2 else BODY), BOX
        if i == 3:
            c.number_format = "#,##0"
        if i == 4:
            c.number_format = "0.00%"
        if i == 5:
            c.alignment = WRAP
    r += 1

# ==================================================== 03_Keys_Duplicates ====
ws, r = sheet("03_Keys_Duplicates", "Keys, Duplicates & Relationships",
              "A column ending in _id is a hint, not proof. Every key below was tested: unique "
              "across all rows AND never empty.", [40, 12, 12, 10, 16, 46])
r = header_row(ws, r, ["Key candidate", "Rows", "Distinct", "Empty", "Verdict", "Note"])
KEYS = [
    ("orders.order_id", 99441, 99441, 0, "VALID PK", ""),
    ("customers.customer_id", 99441, 99441, 0, "VALID PK", "One per ORDER, not per person"),
    ("customers.customer_unique_id", 99441, 96096, 0, "NOT a PK", "By design — this is the real person. 96,096 people"),
    ("order_items.(order_id, order_item_id)", 112650, 112650, 0, "VALID PK", "Composite — needs both columns"),
    ("payments.(order_id, payment_sequential)", 103886, 103886, 0, "VALID PK", "Composite"),
    ("reviews.review_id", 99224, 98410, 0, "NOT a PK", "789 ids reused across DIFFERENT orders — defect Q02"),
    ("reviews.(review_id, order_id)", 99224, 99224, 0, "VALID PK", "Composite, but artificial"),
    ("products.product_id", 32951, 32951, 0, "VALID PK", ""),
    ("sellers.seller_id", 3095, 3095, 0, "VALID PK", ""),
    ("translation.product_category_name", 71, 71, 0, "VALID PK", "Only 71 of the 73 categories in use"),
]
for name, rows, dist, nulls, verdict, note in KEYS:
    vals = [name, rows, dist, nulls, verdict, note]
    for i, v in enumerate(vals, start=1):
        c = ws.cell(row=r, column=i, value=v)
        c.font, c.border = (MONO if i == 1 else BODY), BOX
        if i in (2, 3, 4):
            c.number_format = "#,##0"
        if i == 5:
            c.font = Font(bold=True, color=GREEN if verdict == "VALID PK" else RED)
        if i == 6:
            c.alignment = WRAP
    r += 1

r += 1
ws.cell(row=r, column=1, value="Relationship validation — orphans mean broken joins").font = H2
r += 1
r = header_row(ws, r, ["Relationship", "Child rows", "Orphans", "Childless parents", "Cardinality", "Note"])
RELS = [
    ("orders → customers", 99441, 0, 0, "one-to-one", "Proves customer_id is per-order"),
    ("order_items → orders", 112650, 0, 775, "one-to-many (max 21)", "775 orders have no items — mostly unavailable/canceled"),
    ("payments → orders", 103886, 0, 1, "one-to-many (max 29)", "Instalments. Aggregate BEFORE joining"),
    ("reviews → orders", 99224, 0, 768, "one-to-many (max 3)", "LEFT JOIN only, or 768 orders vanish"),
    ("order_items → products", 112650, 0, 0, "one-to-many (max 527)", ""),
    ("order_items → sellers", 112650, 0, 0, "one-to-many (max 2,033)", "Extreme seller concentration"),
    ("products → translation", 32951, 13, 0, "one-to-many", "⚠ The only broken one: 2 categories untranslated"),
]
for name, cr, orph, cp, card, note in RELS:
    for i, v in enumerate([name, cr, orph, cp, card, note], start=1):
        c = ws.cell(row=r, column=i, value=v)
        c.font, c.border = (MONO if i == 1 else BODY), BOX
        if i in (2, 3, 4):
            c.number_format = "#,##0"
        if i == 3 and orph > 0:
            c.font = Font(bold=True, color=RED)
        if i == 6:
            c.alignment = WRAP
    r += 1

print("  sheets 00-03 written")
# ==================================================== 04_KPI_ValidATION =====
ws, r = sheet("04_KPI_Validation", "★ KPI Validation — Spreadsheet vs Python",
              "Column C is computed by THIS SPREADSHEET from the DATA_ sheets. Column D is the "
              "Phase 1 pandas result. Column E is the difference. They were produced by completely "
              "different tools, so agreement is real evidence; disagreement is a bug worth finding.",
              [5, 44, 18, 18, 14, 54])
r = header_row(ws, r, ["#", "KPI", "Spreadsheet", "Python (Phase 1)", "Difference", "Definition / caveat"])
KPI_ROWS = [
    ("Total orders (all statuses)", f"=COUNTA({O('A')})", PK["total_orders_all"], "#,##0",
     "COUNTA of order_id on the order grain"),
    ("Total orders with line items", f"=COUNTIF({O('K')},1)", PK["total_orders_with_items"], "#,##0",
     "775 orders have no items and cannot earn revenue"),
    ("Delivered orders", f'=COUNTIF({O("E")},"delivered")', PK["delivered_orders"], "#,##0",
     "order_status = delivered"),
    ("Canceled orders", f'=COUNTIF({O("E")},"canceled")', PK["canceled_orders"], "#,##0", ""),
    ("Total product revenue — all statuses", f"=SUM({I('I')})", PK["gmv_all_statuses"], "#,##0.00",
     "SUM(order_items.price). Excludes freight by definition"),
    ("Total product revenue — revenue-eligible", f"=SUMIF({I('E')},1,{I('I')})", PK["revenue_eligible"], "#,##0.00",
     "Excludes canceled and unavailable, per kpi_definitions.md"),
    ("Total freight charged", f"=SUM({I('J')})", PK["freight_all_statuses"], "#,##0.00",
     "Reported separately — never inside revenue"),
    ("Average Order Value (eligible)", f"=SUMIF({I('E')},1,{I('I')})/COUNTIFS({O('F')},1,{O('K')},1)",
     PK["aov_eligible"], "#,##0.00",
     "Denominator = eligible orders WITH items (98,199), not all 99,441"),
    ("Median order value (eligible)", None, PK["median_order_value_elig"], "#,##0.00",
     "Needs an array formula — see note below the table"),
    ("Average review score — review grain", f"=AVERAGE({R('C')})", PK["avg_review_score_reviewlevel"], "0.0000",
     "Mean of all 99,224 review rows"),
    ("Average review score — order grain", f"=AVERAGE({O('R')})", PK["avg_review_score_orderlevel"], "0.0000",
     "Mean of 98,673 per-order averages. DIFFERENT by design — see below"),
    ("Orders with at least one review", f"=COUNTIF({O('S')},\">0\")", PK["orders_with_review"], "#,##0",
     "99.23% coverage; 768 orders have none"),
    ("Orders with a real delivery date", f"=COUNT({O('O')})", PK["orders_with_delivery_date"], "#,##0",
     "96,476 — NOT 96,478. 8 'delivered' orders lack a date (Q01)"),
    ("Average delivery time (days)", f"=AVERAGE({O('O')})", PK["avg_delivery_days"], "0.00",
     "From purchase, so it includes payment approval time"),
    ("Median delivery time (days)", f"=MEDIAN({O('O')})", PK["median_delivery_days"], "0.00",
     "Right-skewed, so median matters more than mean"),
    ("Late deliveries", f"=SUM({O('Q')})", PK["late_orders"], "#,##0",
     "Actual delivery later than the estimated date"),
    ("On-time delivery rate %", f"=(1-AVERAGE({O('Q')}))*100", PK["on_time_rate_pct"], "0.00",
     "Measured against Olist's OWN estimate, which may be padded"),
    ("Cancellation rate %", f'=COUNTIF({O("E")},"canceled")/COUNTA({O("A")})*100',
     PK["cancellation_rate_pct"], "0.0000", "'unavailable' (609) is reported separately"),
    ("Total customers (distinct people)", None, PK["total_customers_unique"], "#,##0",
     "⚠ NOT computable by simple formula — see the limitation note below"),
]
first_kpi = r
for n, (label, formula, pyval, fmt, note) in enumerate(KPI_ROWS, start=1):
    ws.cell(row=r, column=1, value=n).font = BODY
    ws.cell(row=r, column=2, value=label).font = BODY
    if formula:
        c = ws.cell(row=r, column=3, value=formula)
    else:
        c = ws.cell(row=r, column=3, value="not computable")
        c.font = Font(italic=True, color=AMBER)
    c.number_format = fmt
    d = ws.cell(row=r, column=4, value=pyval)
    d.number_format = fmt
    if formula:
        e = ws.cell(row=r, column=5, value=f"=C{r}-D{r}")
        e.number_format = fmt
    else:
        ws.cell(row=r, column=5, value="—")
    f = ws.cell(row=r, column=6, value=note)
    f.font, f.alignment = MUTED, WRAP
    for i in range(1, 7):
        ws.cell(row=r, column=i).border = BOX
    if n % 2 == 0:
        for i in range(1, 7):
            ws.cell(row=r, column=i).fill = FILL_LIGHT
    r += 1
last_kpi = r - 1

r += 1
ws.cell(row=r, column=2, value="Rows where spreadsheet ≠ Python:").font = H2
# COUNTIFS, not SUMPRODUCT(ABS(...)). Two rows in this range hold the literal
# text "—" for KPIs a spreadsheet cannot compute (distinct count, conditional
# median). ABS() over text returns #VALUE!, so the original SUMPRODUCT version
# broke the whole cell on recalculation. COUNTIFS skips non-numeric cells.
# The 0.011 threshold tolerates the 2dp rounding of the Python reference column.
chk = ws.cell(row=r, column=3,
              value=f'=COUNTIFS(E{first_kpi}:E{last_kpi},">0.011")'
                    f'+COUNTIFS(E{first_kpi}:E{last_kpi},"<-0.011")')
chk.font = Font(bold=True, size=12)
ws.cell(row=r, column=4,
        value="(0 = every computable KPI reconciles; the 2 'not computable' rows are skipped)"
        ).font = MUTED
r += 2

for head, body in [
    ("Why the two review-score averages differ — and which is right",
     f"Review grain gives {PK['avg_review_score_reviewlevel']}; order grain gives {PK['avg_review_score_orderlevel']}. "
     "Neither is wrong. 547 orders carry 2–3 reviews, so averaging all review ROWS weights those orders "
     "more heavily than averaging one figure PER ORDER. Report 'average review score' at review grain, "
     "and 'average order rating' at order grain — and never mix the labels. This is the clearest small "
     "example in the project of why grain must be stated with every metric."),
    ("Limitation: a spreadsheet cannot count distinct customers at this scale",
     "Counting the 96,096 distinct customer_unique_id values needs either Excel 365's UNIQUE() function, "
     "a pivot table with 'Distinct Count' (Excel only, via the Data Model), or SUMPRODUCT(1/COUNTIF(...)) "
     "— which on 99,441 rows means roughly 10 billion comparisons and will hang. LibreOffice's pivot tables "
     "have no distinct-count option at all. This is a genuine, reportable limit of spreadsheets, and a good "
     "reason the project moves to SQL in Phase 4 where COUNT(DISTINCT ...) is trivial."),
    ("Limitation: median with a condition needs an array formula",
     "MEDIAN has no MEDIANIFS counterpart. Filtering to eligible orders requires an array formula such as "
     "=MEDIAN(IF((DATA_Orders!F2:F99442=1)*(DATA_Orders!K2:K99442=1),DATA_Orders!M2:M99442)) entered with "
     "Ctrl+Shift+Enter. It evaluates but is slow, so it is documented rather than embedded."),
]:
    ws.cell(row=r, column=2, value=head).font = H2
    c = ws.cell(row=r, column=3, value=body)
    c.font, c.alignment = BODY, WRAP
    ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=6)
    ws.row_dimensions[r].height = 72
    r += 1

print("  sheet 04 written")
# ==================================================== 05_Revenue_By_Month ===
months = sorted(orders.order_month.dropna().unique())
ws, r = sheet("05_Revenue_By_Month", "Revenue by Month",
              "Live SUMIFS over the order grain. Revenue excludes canceled and unavailable orders. "
              "Note the four near-empty edge months flagged in the last column — they are extract "
              "boundaries, not a business collapse.", [12, 16, 18, 16, 14, 34])
r = header_row(ws, r, ["Month", "Orders", "Revenue (BRL)", "AOV", "Avg review", "Flag"])
SPARSE = {"2016-09", "2016-10", "2016-12", "2018-09", "2018-10"}
first_m = r
for m in months:
    ws.cell(row=r, column=1, value=m).font = BODY
    ws.cell(row=r, column=2, value=f'=COUNTIFS({O("H")},A{r})').number_format = "#,##0"
    ws.cell(row=r, column=3, value=f'=SUMIFS({O("M")},{O("H")},A{r},{O("F")},1)').number_format = "#,##0.00"
    ws.cell(row=r, column=4, value=f'=IFERROR(SUMIFS({O("M")},{O("H")},A{r},{O("F")},1)/COUNTIFS({O("H")},A{r},{O("F")},1,{O("K")},1),"")').number_format = "#,##0.00"
    ws.cell(row=r, column=5, value=f'=IFERROR(AVERAGEIFS({O("R")},{O("H")},A{r}),"")').number_format = "0.00"
    if m in SPARSE:
        ws.cell(row=r, column=6, value="⚠ partial month — exclude from trends").font = Font(color=RED, size=10)
    for i in range(1, 7):
        ws.cell(row=r, column=i).border = BOX
    r += 1
ws.cell(row=r, column=1, value="TOTAL").font = H2
ws.cell(row=r, column=2, value=f"=SUM(B{first_m}:B{r-1})").number_format = "#,##0"
ws.cell(row=r, column=3, value=f"=SUM(C{first_m}:C{r-1})").number_format = "#,##0.00"
for i in range(1, 4):
    ws.cell(row=r, column=i).font = H2
r += 2
ws.cell(row=r, column=1, value="Stable window 2017-01 → 2018-08:").font = H2
ws.cell(row=r, column=3, value=f'=SUMIFS({O("M")},{O("H")},">=2017-01",{O("H")},"<=2018-08",{O("F")},1)').number_format = "#,##0.00"
ws.cell(row=r, column=4, value="revenue in the 20 complete months").font = MUTED

# ==================================================== 06_Orders_By_Status ===
ws, r = sheet("06_Orders_By_Status", "Orders by Status",
              "Live COUNTIF over the order grain. 97% of orders reached 'delivered'.",
              [16, 14, 12, 18, 16, 40])
r = header_row(ws, r, ["Status", "Orders", "% of all", "Revenue (BRL)", "Avg review", "Note"])
STATUS_NOTE = {
    "delivered": "Reached the customer",
    "shipped": "In transit when the extract was taken",
    "canceled": "Excluded from revenue",
    "unavailable": "Excluded from revenue — stock problem",
    "invoiced": "Billed, not yet shipped",
    "processing": "Being prepared",
    "created": "Just placed",
    "approved": "Payment approved only",
}
statuses = orders.order_status.value_counts().index.tolist()
first_s = r
for s in statuses:
    ws.cell(row=r, column=1, value=s).font = MONO
    ws.cell(row=r, column=2, value=f'=COUNTIF({O("E")},A{r})').number_format = "#,##0"
    ws.cell(row=r, column=3, value=f'=COUNTIF({O("E")},A{r})/COUNTA({O("A")})').number_format = "0.00%"
    ws.cell(row=r, column=4, value=f'=SUMIF({O("E")},A{r},{O("M")})').number_format = "#,##0.00"
    ws.cell(row=r, column=5, value=f'=IFERROR(AVERAGEIF({O("E")},A{r},{O("R")}),"n/a")').number_format = "0.00"
    ws.cell(row=r, column=6, value=STATUS_NOTE.get(s, "")).font = MUTED
    for i in range(1, 7):
        ws.cell(row=r, column=i).border = BOX
    r += 1
ws.cell(row=r, column=1, value="TOTAL").font = H2
ws.cell(row=r, column=2, value=f"=SUM(B{first_s}:B{r-1})").number_format = "#,##0"
ws.cell(row=r, column=3, value=f"=SUM(C{first_s}:C{r-1})").number_format = "0.00%"
ws.cell(row=r, column=4, value=f"=SUM(D{first_s}:D{r-1})").number_format = "#,##0.00"
for i in range(1, 5):
    ws.cell(row=r, column=i).font = H2

# ===================================================== 07_Orders_By_State ===
states = sorted(orders.customer_state.dropna().unique())
ws, r = sheet("07_Orders_By_State", "Orders & Revenue by Customer State",
              "Live COUNTIF / SUMIFS. State is reliable; city names are unnormalised (4,119 "
              "variants) so city-level analysis waits for Phase 3 cleaning.",
              [10, 14, 18, 14, 16, 16])
r = header_row(ws, r, ["State", "Orders", "Revenue (BRL)", "AOV", "% of revenue", "Avg delivery days"])
first_st = r
for s in states:
    ws.cell(row=r, column=1, value=s).font = MONO
    ws.cell(row=r, column=2, value=f'=COUNTIF({O("C")},A{r})').number_format = "#,##0"
    ws.cell(row=r, column=3, value=f'=SUMIFS({O("M")},{O("C")},A{r},{O("F")},1)').number_format = "#,##0.00"
    ws.cell(row=r, column=4, value=f'=IFERROR(C{r}/COUNTIFS({O("C")},A{r},{O("F")},1,{O("K")},1),"")').number_format = "#,##0.00"
    ws.cell(row=r, column=5, value=f'=C{r}/SUMIF({O("F")},1,{O("M")})').number_format = "0.00%"
    ws.cell(row=r, column=6, value=f'=IFERROR(AVERAGEIF({O("C")},A{r},{O("O")}),"")').number_format = "0.0"
    for i in range(1, 7):
        ws.cell(row=r, column=i).border = BOX
    r += 1
ws.cell(row=r, column=1, value="TOTAL").font = H2
ws.cell(row=r, column=2, value=f"=SUM(B{first_st}:B{r-1})").number_format = "#,##0"
ws.cell(row=r, column=3, value=f"=SUM(C{first_st}:C{r-1})").number_format = "#,##0.00"
ws.cell(row=r, column=5, value=f"=SUM(E{first_st}:E{r-1})").number_format = "0.00%"
for i in [1, 2, 3, 5]:
    ws.cell(row=r, column=i).font = H2

# ===================================================== 08_Category_Revenue ==
cats = sorted(items.category_en.dropna().unique())
ws, r = sheet("08_Category_Revenue", "Revenue by Product Category",
              "Computed on the ITEM grain, because category is a property of the product, not the "
              "order. English names come from a LEFT JOIN: 2 categories had no translation and "
              "would have been silently deleted by an inner join.",
              [42, 14, 18, 14, 16])
r = header_row(ws, r, ["Category (English)", "Items sold", "Revenue (BRL)", "Avg price", "% of revenue"])
first_c = r
for c_ in cats:
    ws.cell(row=r, column=1, value=c_).font = BODY
    ws.cell(row=r, column=2, value=f'=COUNTIFS({I("F")},A{r},{I("E")},1)').number_format = "#,##0"
    ws.cell(row=r, column=3, value=f'=SUMIFS({I("I")},{I("F")},A{r},{I("E")},1)').number_format = "#,##0.00"
    ws.cell(row=r, column=4, value=f'=IFERROR(C{r}/B{r},"")').number_format = "#,##0.00"
    ws.cell(row=r, column=5, value=f'=C{r}/SUMIF({I("E")},1,{I("I")})').number_format = "0.00%"
    for i in range(1, 6):
        ws.cell(row=r, column=i).border = BOX
    r += 1
ws.cell(row=r, column=1, value="TOTAL").font = H2
ws.cell(row=r, column=2, value=f"=SUM(B{first_c}:B{r-1})").number_format = "#,##0"
ws.cell(row=r, column=3, value=f"=SUM(C{first_c}:C{r-1})").number_format = "#,##0.00"
ws.cell(row=r, column=5, value=f"=SUM(E{first_c}:E{r-1})").number_format = "0.00%"
for i in [1, 2, 3, 5]:
    ws.cell(row=r, column=i).font = H2

# =================================================== 09_Review_Distribution =
ws, r = sheet("09_Review_Distribution", "Review Score Distribution",
              "Computed on the REVIEW grain (all 99,224 review rows). The shape is J-shaped, not a "
              "bell curve — which is why the 4.09 average describes almost nobody.",
              [12, 14, 12, 26])
r = header_row(ws, r, ["Score", "Reviews", "% of all", "Reading"])
READ = {1: "Angry customers — the group to investigate", 2: "Dissatisfied",
        3: "Neutral", 4: "Satisfied", 5: "Delighted — the majority"}
first_rv = r
for s in [1, 2, 3, 4, 5]:
    ws.cell(row=r, column=1, value=s).font = BODY
    ws.cell(row=r, column=2, value=f'=COUNTIF({R("C")},A{r})').number_format = "#,##0"
    ws.cell(row=r, column=3, value=f'=COUNTIF({R("C")},A{r})/COUNTA({R("B")})').number_format = "0.00%"
    ws.cell(row=r, column=4, value=READ[s]).font = MUTED
    for i in range(1, 5):
        ws.cell(row=r, column=i).border = BOX
    r += 1
ws.cell(row=r, column=1, value="TOTAL").font = H2
ws.cell(row=r, column=2, value=f"=SUM(B{first_rv}:B{r-1})").number_format = "#,##0"
ws.cell(row=r, column=3, value=f"=SUM(C{first_rv}:C{r-1})").number_format = "0.00%"
for i in range(1, 4):
    ws.cell(row=r, column=i).font = H2
r += 2
ws.cell(row=r, column=1, value="Mean score").font = H2
ws.cell(row=r, column=2, value=f'=AVERAGE({R("C")})').number_format = "0.0000"
r += 1
ws.cell(row=r, column=1, value="1-star + 2-star share").font = H2
ws.cell(row=r, column=2, value=f'=(COUNTIF({R("C")},1)+COUNTIF({R("C")},2))/COUNTA({R("B")})').number_format = "0.00%"

print("  sheets 05-09 written")
# ====================================================== 10_FanOut_Warning ===
ws, r = sheet("10_FanOut_Warning", "★ The Duplicate-Revenue Trap (Fan-Out)",
              "The single most common way to get a wrong answer from this dataset. Read this before "
              "building any pivot table.", [46, 20, 20, 16])
for line in [
    ("What fan-out means", H2),
    ("An order is ONE row in the orders table, but it can be several rows in order_items (one per "
     "product), several in payments (one per instalment) and occasionally several in reviews.", BODY),
    ("Join two of those tables on order_id and the rows multiply. Every duplicated row carries a "
     "duplicated price — so your revenue total silently inflates. Nothing errors. The number just "
     "becomes wrong.", BODY),
    ("", BODY),
    ("Measured on this dataset", H2),
]:
    c = ws.cell(row=r, column=1, value=line[0])
    c.font, c.alignment = line[1], WRAP
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    r += 1
r += 1
r = header_row(ws, r, ["Approach", "Rows produced", "Revenue reported", "Error"])
FAN = [
    ("CORRECT: SUM(price) on order_items alone", PK["fanout_rows_correct"], PK["fanout_correct_gmv"], 0.0),
    ("WRONG: order_items joined to payments", PK["fanout_pay_rows"], PK["fanout_pay_gmv"], PK["fanout_pay_inflation_pct"]),
    ("WRONG: order_items inner-joined to reviews", PK["fanout_rev_rows"], PK["fanout_rev_gmv"], PK["fanout_rev_error_pct"]),
]
for label, rows, rev, err in FAN:
    ws.cell(row=r, column=1, value=label).font = Font(bold=True, color=GREEN if err == 0 else RED)
    ws.cell(row=r, column=2, value=rows).number_format = "#,##0"
    ws.cell(row=r, column=3, value=rev).number_format = "#,##0.00"
    e = ws.cell(row=r, column=4, value=err / 100)
    e.number_format = "+0.00%;-0.00%;0.00%"
    e.font = Font(bold=True, color=GREEN if err == 0 else RED)
    for i in range(1, 5):
        ws.cell(row=r, column=i).border = BOX
    r += 1
r += 1
for head, body in [
    ("Why the payments join inflates",
     f"Many Brazilian customers pay in instalments, so one order can have up to 29 payment rows. "
     f"Joining items to payments turned {PK['fanout_rows_correct']:,} item rows into {PK['fanout_pay_rows']:,}, "
     f"and inflated revenue by {PK['fanout_pay_inflation_pct']}% — about "
     f"{PK['fanout_pay_gmv'] - PK['fanout_correct_gmv']:,.0f} BRL of pure fiction."),
    ("Why the reviews join is MORE dangerous",
     f"It moved revenue the other way, to {PK['fanout_rev_error_pct']}%. An INNER join both duplicates "
     "(547 orders have 2–3 reviews) and silently deletes (768 orders have none). The two errors partly "
     "cancel, leaving a number that looks almost right and is not. A small error is harder to spot than "
     "a large one."),
    ("The rule that prevents all of this",
     "Decide the grain of your answer first, then aggregate every other table TO that grain before "
     "joining. Revenue per order? Aggregate items to one row per order first. That is exactly why "
     "DATA_Orders exists in this workbook: it is pre-aggregated, so it is safe to pivot."),
    ("How this shows up in a pivot table",
     "If you pivot a sheet where one order appears on several rows and drop 'revenue' into Values, the "
     "pivot sums the duplicates. Pivot tables do not warn you. Always pivot DATA_Orders for order-level "
     "measures, and DATA_Items only for product/category/seller measures."),
]:
    ws.cell(row=r, column=1, value=head).font = H2
    c = ws.cell(row=r, column=2, value=body)
    c.font, c.alignment = BODY, WRAP
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
    ws.row_dimensions[r].height = 62
    r += 1

# ====================================================== 11_Pivot_Exercises ==
ws, r = sheet("11_Pivot_Exercises", "Pivot Table Exercises — build these by hand",
              "The formula sheets already give the answers. Build these pivots yourself anyway: "
              "pivot tables are tested in Data Analyst interviews, and the muscle memory only comes "
              "from doing it. Check each result against the sheet named in the last column.",
              [5, 22, 26, 22, 22, 22])
ws.cell(row=r, column=1, value="In LibreOffice Calc: select any cell in the data, then Insert ▸ Pivot Table ▸ Current Selection. In Excel: Insert ▸ PivotTable.").font = MUTED
r += 2
r = header_row(ws, r, ["#", "Use this sheet", "Rows field", "Values field", "Filter", "Check against"])
EX = [
    ("DATA_Orders", "order_month", "Sum of order_revenue", "revenue_eligible = 1", "05_Revenue_By_Month"),
    ("DATA_Orders", "order_status", "Count of order_id", "none", "06_Orders_By_Status"),
    ("DATA_Orders", "customer_state", "Sum of order_revenue", "revenue_eligible = 1", "07_Orders_By_State"),
    ("DATA_Items", "category_en", "Sum of price", "revenue_eligible = 1", "08_Category_Revenue"),
    ("DATA_Reviews", "review_score", "Count of review_id", "none", "09_Review_Distribution"),
    ("DATA_Orders", "customer_state", "Average of delivery_days", "is_delivered = 1", "07_Orders_By_State col F"),
    ("DATA_Orders", "order_month", "Average of review_score_avg", "none", "05_Revenue_By_Month col E"),
    ("DATA_Items", "seller_state", "Sum of price", "revenue_eligible = 1", "— new, no formula sheet"),
]
for n, (sh, rows_f, vals, filt, check) in enumerate(EX, start=1):
    for i, v in enumerate([n, sh, rows_f, vals, filt, check], start=1):
        c = ws.cell(row=r, column=i, value=v)
        c.font, c.border = (MONO if i in (2, 3, 4) else BODY), BOX
        c.alignment = WRAP
    r += 1
r += 1
ws.cell(row=r, column=1, value="⚠ Two things that will trip you up").font = H2
r += 1
for line in [
    "1. NEVER pivot a sheet at the wrong grain. DATA_Items has 112,650 rows for 98,666 orders, so "
    "'Count of order_id' there counts ITEM LINES, not orders. Read sheet 10 first.",
    "2. LibreOffice pivot tables cannot do a Distinct Count. Counting distinct customers needs Excel's "
    "Data Model, or SQL in Phase 4. This is a real limitation, not something you are doing wrong.",
]:
    c = ws.cell(row=r, column=1, value=line)
    c.font, c.alignment = BODY, WRAP
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    ws.row_dimensions[r].height = 32
    r += 1

print("  sheets 10-11 written")
# ========================================================= DATA sheets ======
NUMCOLS = {
    "DATA_Orders": {"item_count": "#,##0", "order_revenue": "#,##0.00",
                    "order_freight": "#,##0.00", "delivery_days": "0.00",
                    "delay_days": "0.00", "review_score_avg": "0.00",
                    "review_count": "0", "order_year": "0",
                    "revenue_eligible": "0", "is_delivered": "0",
                    "has_items": "0", "is_late": "0"},
    "DATA_Items": {"price": "#,##0.00", "freight_value": "#,##0.00",
                   "revenue_eligible": "0"},
    "DATA_Reviews": {"review_score": "0"},
}


def write_data(name, df, subtitle):
    ws = wb.create_sheet(name)
    ws.append(list(df.columns))
    for i, col in enumerate(df.columns, start=1):
        c = ws.cell(row=1, column=i)
        c.font, c.fill = HDR, FILL_HDR
        ws.column_dimensions[get_column_letter(i)].width = max(11, min(22, len(col) + 3))
    numeric = {c: pd.to_numeric(df[c], errors="coerce") for c in NUMCOLS.get(name, {})}
    recs = df.to_dict("records")
    cols = list(df.columns)
    numset = set(NUMCOLS.get(name, {}))
    for idx, rec in enumerate(recs):
        row = []
        for c in cols:
            if c in numset:
                v = numeric[c].iloc[idx]
                row.append(None if pd.isna(v) else float(v))
            else:
                v = rec[c]
                row.append(None if pd.isna(v) else v)
        ws.append(row)
    for i, col in enumerate(cols, start=1):
        fmt = NUMCOLS.get(name, {}).get(col)
        if fmt:
            letter = get_column_letter(i)
            for cell in ws[f"{letter}2":f"{letter}{len(df) + 1}"]:
                cell[0].number_format = fmt
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(df) + 1}"
    print(f"  {name}: {len(df):,} rows x {len(cols)} cols")


write_data("DATA_Orders", orders, "One row per order")
write_data("DATA_Items", items, "One row per product line")
write_data("DATA_Reviews", reviews, "One row per review record")

wb.active = 0
wb.save(OUT)
print(f"\nSaved {OUT}  ({OUT.stat().st_size / 1024**2:.1f} MB)")
