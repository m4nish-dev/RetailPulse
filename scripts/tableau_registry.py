"""
RetailPulse - Tableau registry: the single definition of the dashboard's data
sources, field names, parameters and calculated fields.

Imported by
  scripts/validate_tableau_calcs.py    (emulates every formula and checks it against SQL;
                                        writes tableau/calculated_fields.md)
  scripts/build_tableau_workbook.py    (writes the Tableau workbook from the same definitions)
  scripts/validate_tableau_workbook.py (checks the generated workbook against this registry)

Keeping one registry guarantees that the formulas in the workbook, in the
documentation and in the validation are character-for-character the same.
Reads only the CSV headers in tableau/data/ (no database access).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TAB = ROOT / "tableau"
D = TAB / "data"
A = D / "analytical"

# =============================================================================
# 1. DATA SOURCES (logical tables in the order they are added; key to the root)
# =============================================================================
DATA_SOURCES = {
    "RP Orders": [("vw_order_summary", D, None, None),
                  ("vw_review_summary", D, "order_id", "rev_"),
                  ("delivery_stage_orders", A, "order_id", "dso_")],
    "RP Customers": [("vw_customer_summary", D, None, None),
                     ("rfm_customer_segments", A, "customer_unique_id", "rfm_")],
    "RP Cohorts": [("cohort_retention", A, None, None)],
    "RP Categories": [("dim_category", A, None, None),
                      ("vw_category_performance", D, "category", "cat_"),
                      ("product_performance", A, "category", "prod_"),
                      ("category_satisfaction", A, "category", "cs_")],
    "RP Sellers": [("vw_seller_performance", D, None, None),
                   ("seller_scorecard", A, "seller_id", "sk_"),
                   ("seller_category_performance", A, "seller_id", "scp_")],
    "RP Stage Summary": [("delivery_stage_summary", A, None, None)],
}
PARAMETERS = {
    "p_category": ("String", "health_beauty",
                   "Category shown on the Category Detail dashboard. Set by a parameter action from Products."),
    "p_seller": ("String", "4869f7a5dfa277a7dca6462dcf3b52b2",
                 "Seller shown on the Seller Detail dashboard. Set by a parameter action from Sellers. "
                 "Default = the largest seller by revenue."),
}

HEADERS = {t: list(pd.read_csv(d / f"{t}.csv", nrows=0).columns)
           for tables in DATA_SOURCES.values() for t, d, _, _ in tables}

# Field names as they must appear in Tableau after the guide's renaming step:
# the first table that has a column keeps its name; a later table's duplicate is
# renamed <prefix><column>.
RENAMES: dict[str, list[tuple[str, str, str]]] = {}
FIELDS: dict[str, dict[str, tuple[str, str]]] = {}
for ds, tables in DATA_SOURCES.items():
    seen: dict[str, tuple[str, str]] = {}
    RENAMES[ds] = []
    for t, _, _, prefix in tables:
        for col in HEADERS[t]:
            if col in seen:
                new = f"{prefix}{col}"
                RENAMES[ds].append((t, col, new))
                seen[new] = (t, col)
            else:
                seen[col] = (t, col)
    FIELDS[ds] = seen

# =============================================================================
# 2. CALCULATED FIELDS (Tableau formulas)
# =============================================================================
CALCS: list[dict] = []


def calc(cid, name, ds, kind, level, formula, definition, note, fmt=""):
    """definition = business meaning; note = Tableau behaviour, settings and pitfalls."""
    CALCS.append({"id": cid, "name": name, "ds": ds, "kind": kind, "level": level,
                  "formula": formula.strip("\n"), "definition": definition, "note": note, "fmt": fmt})


BRL, PCT, INT, DEC2, DAYS = "R$ currency, 2 dp", "Percentage, 2 dp", "Number, 0 dp", "Number, 4 dp", "Number, 2 dp"
ROW, AGG, LOD, TC = "row-level", "aggregate", "aggregate with LOD", "table calculation"
GUARD = "Ratio guarded with IF denominator > 0, so an empty context shows blank (NULL), never an error or 0."

# ---- helpers ------------------------------------------------------------------
calc("H01", "Order Month", "RP Orders", ROW, "one value per order row",
     "DATETRUNC('month', [order_date])",
     "Calendar month in which the order was placed.",
     "The month axis of every trend sheet. Tableau's own date functions do the month arithmetic "
     "(DATEDIFF('month', ...)), so no separate date table is needed.", "Date, custom format yyyy-mm")
calc("H02", "Delivery Bucket Order", "RP Orders", ROW, "one value per review row",
     """CASE [delivery_bucket]
    WHEN '15+ days early'  THEN 1
    WHEN '7-15 days early' THEN 2
    WHEN 'on time'         THEN 3
    WHEN '1-7 days late'   THEN 4
    WHEN '8-15 days late'  THEN 5
    WHEN '15+ days late'   THEN 6
    WHEN 'not delivered'   THEN 7
END""", "Position of each delivery bucket from earliest to latest.",
     "Sort key for the delay-vs-score axis (Sort ▸ Field ▸ Delivery Bucket Order, Minimum, ascending).", INT)
calc("H03", "Is Selected Category", "RP Categories", ROW, "one value per dim_category row",
     "[category] = [p_category]",
     "True for the category chosen on the Products dashboard.",
     "Put on Filters = True on every Category Detail sheet of RP Categories, then Add to Context so Top N "
     "filters work inside the category. Not on sheet 7.1 (uses H05).")
calc("H04", "Is Selected Category", "RP Sellers", ROW, "one value per seller_category_performance row",
     "[category] = [p_category]",
     "True for seller-category rows of the chosen category.",
     "Same role as H03 in the RP Sellers data source (sheets 7.4 and 7.5), also added to context.")
calc("H05", "Selected Category TC", "RP Categories", TC, "Compute Using: category",
     "LOOKUP(MIN([category]), 0) = [p_category]",
     "True for the chosen category, decided after all categories have been ranked.",
     "A table-calculation filter is applied last, so rank and cumulative share are computed over all 74 "
     "categories before the others are hidden. A normal filter would leave one row and show rank 1 / 100%.")
calc("H06", "Is Selected Seller", "RP Sellers", ROW, "one value per seller row",
     "[seller_id] = [p_seller]",
     "True for the seller chosen on the Sellers dashboard.",
     "Filters = True on every Seller Detail sheet except the cumulative-share sheet (H07).")
calc("H07", "Selected Seller TC", "RP Sellers", TC, "Compute Using: seller_id",
     "LOOKUP(MIN([seller_id]), 0) = [p_seller]",
     "True for the chosen seller, decided after all sellers have been accumulated.",
     "Table-calculation filter for the Seller Detail cumulative-share card (see H05).")
calc("H08", "Seller Has 50+ Orders", "RP Sellers", ROW, "one value per seller",
     "[orders_served] >= 50",
     "Seller served at least 50 seller-order pairs.",
     "Minimum sample for seller rankings and the scatter: averages over a handful of orders are unstable.")
calc("H09", "Needs Intervention", "RP Sellers", AGG, "per seller (seller_id on Rows)",
     "SUM([orders_served]) >= 100 AND [Seller Inherited Order Rating] < 3.8",
     "Seller with real volume (>= 100 seller-order pairs) and a low inherited order rating (< 3.8).",
     "Filter = True on the intervention table; needs seller_id in the view so it is evaluated per seller.")
calc("H10", "Log10 Historical Value", "RP Customers", ROW, "one value per person",
     "IF [historical_value] > 0 THEN LOG([historical_value]) END",
     "Base-10 logarithm of what a person has spent.",
     "Binned (size 0.25) for the value histogram. The 1,113 people with no eligible spend get NULL; "
     "exclude the Null bin.", DAYS)

# ---- Executive --------------------------------------------------------------------
calc("M01", "Total Revenue", "RP Orders", AGG, "orders (vw_order_summary)",
     "SUM(IF [revenue_eligible] = 1 THEN [order_revenue] END)",
     "Product revenue in BRL: item prices of revenue-eligible orders, freight excluded. Not GMV, not profit.",
     "Row-level IF inside SUM: rows outside the condition become NULL and are ignored.", BRL)
calc("M02", "Total Orders", "RP Orders", AGG, "orders", "COUNTD([order_id])",
     "Number of orders, all statuses.",
     "COUNTD of the primary key cannot double-count, even if a join is ever added by mistake.", INT)
calc("M03", "Total Customers", "RP Orders", AGG, "orders", "COUNTD([customer_unique_id])",
     "People who ordered in the filtered period (customer_unique_id, never the per-order customer_id).",
     "Responds to date filters: 2017-11 gives the people active that month.", INT)
calc("M04", "Orders With Items", "RP Orders", AGG, "orders",
     "COUNTD(IF [item_count] > 0 THEN [order_id] END)",
     "Orders that contain at least one item.", "Conditional COUNTD.", INT)
calc("M05", "AOV Denominator", "RP Orders", AGG, "orders",
     "COUNTD(IF [revenue_eligible] = 1 AND [item_count] > 0 THEN [order_id] END)",
     "Revenue-eligible orders that have items: the denominator of average order value (98,199).",
     "Conditional COUNTD.", INT)
calc("M06", "Average Order Value", "RP Orders", AGG, "orders",
     "IF [AOV Denominator] > 0 THEN [Total Revenue] / [AOV Denominator] END",
     "Average product revenue per eligible order with items (BRL).", GUARD, BRL)
calc("M07", "Median Order Value", "RP Orders", AGG, "orders",
     "MEDIAN(IF [revenue_eligible] = 1 AND [item_count] > 0 THEN [order_revenue] END)",
     "Middle order value of eligible orders with items; shown beside the mean because the mean is pulled up by large orders.",
     "Text-file data runs through Tableau's extract engine, which supports MEDIAN.", BRL)
calc("M08", "Total Freight", "RP Orders", AGG, "orders",
     "SUM(IF [revenue_eligible] = 1 THEN [order_freight] END)",
     "Freight charged on eligible orders (BRL). Never added to revenue.", "As M01.", BRL)
calc("M09", "Revenue PM", "RP Orders", TC, "Compute Using: Order Month (month marks)",
     """IF DATEDIFF('month', LOOKUP(MIN([Order Month]), -1), MIN([Order Month])) = 1
THEN LOOKUP([Total Revenue], -1)
END""",
     "Total revenue of the previous calendar month.",
     "LOOKUP reads the previous MARK, not the previous calendar month. November 2016 has no orders, so "
     "without the DATEDIFF guard December 2016 would show October 2016 (pitfall P01). With the guard a "
     "missing month gives blank.", BRL)
calc("M10", "Revenue MoM %", "RP Orders", TC, "Compute Using: Order Month",
     """IF MIN([in_stable_window]) = 1
   AND LOOKUP(MIN([in_stable_window]), -1) = 1
   AND DATEDIFF('month', LOOKUP(MIN([Order Month]), -1), MIN([Order Month])) = 1
   AND LOOKUP([Total Revenue], -1) > 0
THEN ([Total Revenue] - LOOKUP([Total Revenue], -1)) / LOOKUP([Total Revenue], -1)
END""",
     "Month-over-month revenue change, only when this month and the previous one are both complete months "
     "(2017-01 to 2018-08).",
     "2017-01 is blank by design: December 2016 holds a single order. Works with or without a stable-window "
     "filter on the sheet. Table calculations see only the months left in the view.", PCT)
calc("M11", "Revenue 3M Moving Avg", "RP Orders", TC, "Compute Using: Order Month",
     """IF MIN([in_stable_window]) = 1
   AND LOOKUP(MIN([in_stable_window]), -2) = 1
   AND DATEDIFF('month', LOOKUP(MIN([Order Month]), -2), MIN([Order Month])) = 2
THEN WINDOW_SUM([Total Revenue], -2, 0) / 3
END""",
     "Average of this month's and the two previous months' revenue totals, complete months only.",
     "WINDOW_SUM over the current and two previous marks, divided by 3. First value 2017-03.", BRL)
calc("M12", "Revenue Running Total", "RP Orders", TC, "Compute Using: Order Month",
     "RUNNING_SUM([Total Revenue])",
     "Cumulative revenue up to each month.",
     "Respects the sheet's filters (table calculations run after them): with in_stable_window = 1 it starts "
     "at 2017-01 and reaches R$ 13,449,529.68 at 2018-08.", BRL)
calc("M13", "Revenue 2017 Jan-Aug", "RP Orders", AGG, "orders",
     "SUM(IF YEAR([order_date]) = 2017 AND MONTH([order_date]) <= 8 AND [revenue_eligible] = 1 THEN [order_revenue] END)",
     "Revenue of January-August 2017, the like-for-like base for year-on-year growth.",
     "The YoY sheet must be EXCLUDED from the dashboard's date filters (filter ▸ Apply to Worksheets ▸ "
     "Selected Worksheets, untick 1.5). State filters still apply.", BRL)
calc("M14", "Revenue 2018 Jan-Aug", "RP Orders", AGG, "orders",
     "SUM(IF YEAR([order_date]) = 2018 AND MONTH([order_date]) <= 8 AND [revenue_eligible] = 1 THEN [order_revenue] END)",
     "Revenue of January-August 2018.", "As M13.", BRL)
calc("M15", "YoY Growth Jan-Aug %", "RP Orders", AGG, "orders",
     """IF [Revenue 2017 Jan-Aug] > 0
THEN ([Revenue 2018 Jan-Aug] - [Revenue 2017 Jan-Aug]) / [Revenue 2017 Jan-Aug]
END""", "Like-for-like growth Jan-Aug 2018 vs Jan-Aug 2017. Full-year YoY is not reported (2016 has 329 orders).",
     "As M13.", PCT)

# ---- Customers ----------------------------------------------------------------------
calc("M16", "Total People", "RP Customers", AGG, "people (vw_customer_summary)",
     "COUNTD([customer_unique_id])",
     "Distinct people who ever ordered (96,096).",
     "Lives in its own data source, so order-date filters elsewhere cannot touch it (lifetime figures). "
     "Inside the orders data source a date filter WOULD restrict it (pitfall P07).", INT)
calc("M17", "Repeat Customers", "RP Customers", AGG, "people",
     "COUNTD(IF [total_orders] >= 2 THEN [customer_unique_id] END)",
     "People with two or more orders.", "Conditional COUNTD.", INT)
calc("M18", "One-Time Customers", "RP Customers", AGG, "people",
     "COUNTD(IF [total_orders] = 1 THEN [customer_unique_id] END)",
     "People with exactly one order.", "Conditional COUNTD.", INT)
calc("M19", "Repeat Purchase Rate", "RP Customers", AGG, "people",
     "IF [Total People] > 0 THEN [Repeat Customers] / [Total People] END",
     "Share of people who ordered more than once (3.12%).", GUARD, PCT)
calc("M20", "Avg Orders Per Customer", "RP Customers", AGG, "people", "AVG([total_orders])",
     "Average number of orders per person (all statuses).", "One row per person, so AVG is a per-person average.", DEC2)
calc("M21", "Historical Customer Value", "RP Customers", AGG, "people", "SUM([historical_value])",
     "What customers actually spent (eligible product revenue). Historical, never a predicted lifetime value.",
     "Label it 'Historical Customer Value', never CLV.", BRL)
calc("N01", "RFM Scored Customers", "RP Customers", TC, "Compute Using: rfm_segment",
     "TOTAL(SUM([rfm_scored]))",
     "People with an RFM score (94,983); the denominator of segment shares.",
     "rfm_scored is 1/0 with one row per person, so SUM counts scored people. TOTAL() spans every segment "
     "in the view and keeps other filters (state).", INT)
calc("M22", "Customers In Segment", "RP Customers", AGG, "people (rfm_customer_segments)",
     "SUM([rfm_scored])", "Scored people in the segment of the mark.",
     "Sum of a 1/0 flag = conditional count.", INT)
calc("M23", "Segment Revenue Share", "RP Customers", TC, "Compute Using: rfm_segment",
     "IF TOTAL(SUM([monetary_value])) > 0 THEN SUM([monetary_value]) / TOTAL(SUM([monetary_value])) END",
     "Share of historical revenue held by the segment.",
     "The 1,113 unscored people have monetary_value 0, so including or excluding them does not change the share.", PCT)
calc("N02", "Segment Customer Share", "RP Customers", TC, "Compute Using: rfm_segment",
     "IF [RFM Scored Customers] > 0 THEN [Customers In Segment] / [RFM Scored Customers] END",
     "Share of scored people in the segment; compare with the revenue share.", "As N01.", PCT)
calc("N03", "Segment Avg Historical Value", "RP Customers", AGG, "people",
     """IF [Customers In Segment] > 0
THEN SUM(IF [rfm_scored] = 1 THEN [monetary_value] END) / [Customers In Segment]
END""", "Historical spend per scored person in the segment (BRL); not a prediction.", GUARD, BRL)
calc("N04", "Cohort Customers", "RP Cohorts", AGG, "cohort cells",
     "SUM(IF [months_since_acquisition] = 0 THEN [cohort_customers] END)",
     "People acquired in the cohort month (cohort size).", "Taken from the offset-0 row of each cohort.", INT)
calc("N05", "Cohort Retention %", "RP Cohorts", AGG, "cohort cells",
     """IF MIN([months_since_acquisition]) = MAX([months_since_acquisition])
   AND SUM(IF [is_observed] = 1 THEN [cohort_customers] END) > 0
THEN SUM([active_customers]) / SUM(IF [is_observed] = 1 THEN [cohort_customers] END)
END""",
     "Share of a cohort that ordered again N months after its first order (calendar months).",
     "Only defined for a single offset (MIN = MAX), so the grand total is blank. Unobserved (future) cells "
     "have NULL active_customers and no observed denominator: they stay blank, never 0. A column total "
     "weights only the cohorts observable at that offset.", PCT)
calc("N06", "Returning Customers", "RP Cohorts", AGG, "cohort cells", "SUM([returning_customers])",
     "Cohort members who came back in that month.", "NULL at offset 0 and in unobserved cells.", INT)

# ---- Products and categories ------------------------------------------------------
calc("M24", "Category Revenue", "RP Categories", AGG, "category x month (vw_category_performance)",
     "SUM([revenue])", "Product revenue by category (eligible items, BRL).", "Additive across months and categories.", BRL)
calc("M25", "Category Items Sold", "RP Categories", AGG, "category x month", "SUM([items_sold])",
     "Eligible items sold.", "Additive.", INT)
calc("M26", "Distinct Categories", "RP Categories", AGG, "category x month", "COUNTD([cat_category])",
     "Categories with sales.", "Counts the renamed vw_category_performance category column.", INT)
calc("M27", "Category Revenue Share", "RP Categories", LOD, "category; denominator = all categories",
     """IF MIN({FIXED : SUM([revenue])}) > 0
THEN SUM([revenue]) / MIN({FIXED : SUM([revenue])})
END""",
     "Category revenue as a share of all product revenue.",
     "A FIXED total ignores dimension filters (category filter, Top N), so the share stays a share of ALL "
     "revenue on a Top-15 chart and on Category Detail; TOTAL() would give the share of the top 15 only "
     "(pitfall P04). FIXED also ignores a month filter unless that filter is added to context (pitfall P09); "
     "no month filter is specified on these sheets.", PCT)
calc("M28", "Category Rank", "RP Categories", TC, "Compute Using: category",
     "RANK_DENSE([Category Revenue], 'desc')",
     "Position of the category by revenue (1 = largest).",
     "Ranks the categories in the view. On Category Detail use the table-calculation filter H05 so all 74 "
     "are ranked before the others are hidden.", INT)
calc("N07", "Top Category Revenue", "RP Categories", LOD, "category, then max",
     "MAX({INCLUDE [category] : SUM([revenue])})",
     "Revenue of the largest category.", "INCLUDE computes revenue per category, then MAX picks the largest.", BRL)
calc("N36", "Category Cumulative Share", "RP Categories", TC,
     "Compute Using: category; sort category by Category Revenue descending",
     "RUNNING_SUM([Category Revenue]) / TOTAL([Category Revenue])",
     "Share of revenue held by this category and every larger one (Pareto curve).",
     "Defined as all categories with revenue >= this one; RUNNING_SUM equals that because no two "
     "categories tie (all 74 verified).", PCT)
calc("N37", "Category Revenue 2017 Q1", "RP Categories", AGG, "category x month",
     "SUM(IF [order_month] >= '2017-01' AND [order_month] <= '2017-03' THEN [revenue] END)",
     "Category revenue in January-March 2017.",
     "Text comparison on 'YYYY-MM' (sorts correctly). order_month must be typed String.", BRL)
calc("N38", "Category Revenue Jun-Aug 2018", "RP Categories", AGG, "category x month",
     "SUM(IF [order_month] >= '2018-06' AND [order_month] <= '2018-08' THEN [revenue] END)",
     "Category revenue in June-August 2018, the last three complete months (not calendar Q3).", "As N37.", BRL)
calc("N39", "Category Growth Q1 2017 to Jun-Aug 2018", "RP Categories", AGG, "category",
     """IF SUM(IF [order_month] >= '2017-01' AND [order_month] <= '2017-03' THEN [items_sold] END) >= 50
   AND SUM(IF [order_month] >= '2018-06' AND [order_month] <= '2018-08' THEN [items_sold] END) >= 50
   AND [Category Revenue 2017 Q1] > 0
THEN ([Category Revenue Jun-Aug 2018] - [Category Revenue 2017 Q1]) / [Category Revenue 2017 Q1]
END""", "Revenue growth from 2017 Q1 to Jun-Aug 2018, only for categories with at least 50 items in both periods.",
     "Blank below the 50-item floor (24 categories qualify; 22 grew).", PCT)
calc("N08", "Product Revenue", "RP Categories", AGG, "product", "SUM([product_revenue])",
     "Product revenue (eligible items, BRL).", "Additive.", BRL)
calc("N09", "Product Units Sold", "RP Categories", AGG, "product", "SUM([units_sold])",
     "Eligible units sold.", "Additive.", INT)
calc("N10", "Products Sold", "RP Categories", AGG, "product",
     "COUNTD(IF [units_sold] > 0 THEN [product_id] END)", "Products with at least one eligible sale.",
     "Conditional COUNTD.", INT)
calc("N11", "Product Avg Item Price", "RP Categories", AGG, "product",
     "IF [Product Units Sold] > 0 THEN [Product Revenue] / [Product Units Sold] END",
     "Average price per item sold (BRL), weighted by units.",
     "Ratio of sums; AVG of avg_item_price would over-weight rarely sold expensive products.", BRL)
calc("N12", "Product Avg Freight Per Item", "RP Categories", AGG, "product",
     "IF [Product Units Sold] > 0 THEN SUM([freight_value]) / [Product Units Sold] END",
     "Freight charged per item sold (BRL).", GUARD, BRL)
calc("N29", "Category Review Count", "RP Categories", AGG, "one category",
     "IF COUNTD([cs_category]) = 1 THEN SUM([review_count]) END",
     "Reviews on orders containing the category (each review once per category).",
     "Shown only when exactly one category is in the mark; blank at totals, because multi-category orders "
     "count in each category and a plain sum would exceed the reviews that exist.", INT)
calc("N30", "Category Avg Review Score", "RP Categories", AGG, "one category",
     "IF COUNTD([cs_category]) = 1 THEN SUM([avg_review_score]) END",
     "Average review score of the category's orders (review grain).", "As N29.", DEC2)
calc("N31", "Category One-Star Rate", "RP Categories", AGG, "one category",
     "IF COUNTD([cs_category]) = 1 THEN SUM([one_star_pct]) / 100 END",
     "Share of the category's reviews that are 1 star.", "As N29; the CSV stores percent units.", PCT)
calc("N32", "Category Avg Score After Arrival", "RP Categories", AGG, "one category",
     "IF COUNTD([cs_category]) = 1 THEN SUM([avg_review_score_after_arrival]) END",
     "Average score of reviews written after the parcel arrived.", "As N29.", DEC2)
calc("N33", "Category Pre-Delivery Review Share", "RP Categories", AGG, "one category",
     "IF COUNTD([cs_category]) = 1 THEN SUM([pct_reviews_before_delivery]) / 100 END",
     "Share of the category's reviews written before the parcel arrived.", "As N31.", PCT)

# ---- Sellers -------------------------------------------------------------------------
calc("M29", "Seller Revenue", "RP Sellers", AGG, "seller (vw_seller_performance)", "SUM([revenue])",
     "Product revenue of the seller(s) (BRL).", "Additive across sellers.", BRL)
calc("M30", "Sellers With Revenue", "RP Sellers", AGG, "seller", "COUNTD([seller_id])",
     "Sellers with at least one eligible sale (3,053; 42 more had only canceled/unavailable orders).",
     "COUNTD of the primary key.", INT)
calc("M31", "Seller Orders", "RP Sellers", AGG, "seller", "SUM([orders_served])",
     "Seller-order PAIRS: a two-seller order counts once for each seller. Not an order count.",
     "Label 'Seller-order pairs'. Use AOV Denominator (98,199) for orders.", INT)
calc("M32", "Seller Avg Delivery Days", "RP Sellers", AGG, "seller (seller_scorecard)",
     "IF SUM([delivery_measurable_orders]) > 0 THEN SUM([delivery_days_sum]) / SUM([delivery_measurable_orders]) END",
     "Average days from purchase to delivery across the seller's delivered orders.",
     "Weighted ratio of sums, so a total is weighted by volume, not the mean of 3,053 averages.", DAYS)
calc("M33", "Seller Late Rate", "RP Sellers", AGG, "seller (seller_scorecard)",
     "IF SUM([delivery_measurable_orders]) > 0 THEN SUM([late_orders]) / SUM([delivery_measurable_orders]) END",
     "Late deliveries across seller-order pairs (8.02%; the per-order platform rate is 8.11%).",
     "Weighted ratio of sums.", PCT)
calc("M34", "Largest Seller Share", "RP Sellers", LOD, "seller, then max; denominator = platform",
     """IF MIN({FIXED : SUM([revenue])}) > 0
THEN MAX({INCLUDE [seller_id] : SUM([revenue])}) / MIN({FIXED : SUM([revenue])})
END""", "Revenue of the largest seller as a share of platform revenue (1.70%).",
     "The FIXED denominator ignores filters by design (platform revenue).", PCT)
calc("M35", "Seller Inherited Order Rating", "RP Sellers", AGG, "seller (seller_scorecard)",
     "IF SUM([reviewed_orders]) > 0 THEN SUM([review_score_sum]) / SUM([reviewed_orders]) END",
     "Average review score of the seller's orders. Reviews attach to orders, so every seller in a "
     "multi-seller order inherits its score.", "Weighted ratio. Never call it 'seller rating'.", DEC2)
calc("N40", "Seller Cumulative Share", "RP Sellers", TC,
     "Compute Using: seller_id; sort seller_id by Seller Revenue descending",
     "RUNNING_SUM([Seller Revenue]) / TOTAL([Seller Revenue])",
     "Share of revenue held by this seller and every larger one (concentration curve).",
     "DOCUMENTED DIFFERENCE: 495 sellers share a revenue value with another seller. The definition gives "
     "tied sellers one shared value; RUNNING_SUM accumulates them one by one. 311 sellers differ, by at most "
     "0.0201 percentage points, and the first tie is at position 865, so the quoted values (1.70%, 67.43% at "
     "305, 67.50% at 306) are exact.", PCT)
calc("N13", "Seller Category Revenue", "RP Sellers", AGG, "seller x category", "SUM([product_revenue])",
     "Product revenue per seller and category (BRL).", "Additive to seller and category totals.", BRL)
calc("N14", "Seller Category Items", "RP Sellers", AGG, "seller x category", "SUM([item_count])",
     "Eligible items per seller and category.", "Additive. order_count in this table is NOT additive and is not summed.", INT)
calc("N15", "Seller Category Late Rate", "RP Sellers", AGG, "seller x category",
     "IF SUM([scp_delivery_measurable_orders]) > 0 THEN SUM([scp_late_orders]) / SUM([scp_delivery_measurable_orders]) END",
     "Late deliveries per seller-category, weighted.", "Uses the renamed seller_category_performance columns (scp_...).", PCT)
calc("N16", "Seller Category Dispatch Days", "RP Sellers", AGG, "seller x category",
     """IF SUM([dispatch_measurable_orders]) > 0
THEN SUM([dispatch_measurable_orders] * [avg_dispatch_days]) / SUM([dispatch_measurable_orders])
END""", "Average days from approval to carrier handover; single-seller orders with valid timestamps only.",
     "Weighted average rebuilt from a row-level product.", DAYS)

# ---- Operations ----------------------------------------------------------------------
calc("M36", "Delivered Orders", "RP Orders", AGG, "orders", "COUNTD(IF [is_delivered] = 1 THEN [order_id] END)",
     "Orders with status delivered (96,478).", "Conditional COUNTD.", INT)
calc("M37", "Delivery Denominator", "RP Orders", AGG, "orders",
     "COUNTD(IF [delivery_measurable] = 1 THEN [order_id] END)",
     "Orders with an actual delivery date (96,476): the denominator of every delivery average.",
     "COUNTD returns 0 (not NULL) where nothing qualifies; the rates below guard against it.", INT)
calc("M38", "Late Orders", "RP Orders", AGG, "orders", "SUM(IF [delivery_measurable] = 1 THEN [is_late] END)",
     "Delivered after Olist's estimated date.", "Sum of a 1/0 flag on measurable orders.", INT)
calc("M39", "Late Delivery Rate", "RP Orders", AGG, "orders",
     "IF [Delivery Denominator] > 0 THEN [Late Orders] / [Delivery Denominator] END",
     "Share of delivered orders that arrived late (8.11%).", GUARD, PCT)
calc("M40", "On-Time Delivery Rate", "RP Orders", AGG, "orders",
     "IF [Delivery Denominator] > 0 THEN ([Delivery Denominator] - [Late Orders]) / [Delivery Denominator] END",
     "Share delivered on or before the estimated date (91.89%), measured against Olist's own padded estimate.",
     "Blank (not 100%) where there are no deliveries, e.g. status unavailable.", PCT)
calc("M41", "Avg Delivery Days", "RP Orders", AGG, "orders",
     "AVG(IF [delivery_measurable] = 1 THEN [delivery_days] END)",
     "Average days from purchase to delivery (12.56).", "Measurable orders only.", DAYS)
calc("M42", "Avg Delay Days", "RP Orders", AGG, "orders",
     "AVG(IF [delivery_measurable] = 1 THEN [delay_days] END)",
     "Average days delivered after (+) or before (-) the estimate.", "Negative = early.", DAYS)
calc("N41", "Avg Promised Days", "RP Orders", AGG, "orders",
     "AVG(IF [delivery_measurable] = 1 THEN [delivery_days] - [delay_days] END)",
     "Average days from purchase to the promised (estimated) date, delivered orders.",
     "Plot beside Avg Delivery Days: 2017-01 39.51 promised vs 12.65 actual.", DAYS)
calc("M43", "Cancelled Orders", "RP Orders", AGG, "orders",
     "COUNTD(IF [order_status] = 'canceled' THEN [order_id] END)", "Orders with status canceled (625).",
     "Conditional COUNTD.", INT)
calc("M44", "Cancellation Rate", "RP Orders", AGG, "orders",
     "IF [Total Orders] > 0 THEN [Cancelled Orders] / [Total Orders] END", "Share of orders canceled (0.63%).", GUARD, PCT)
calc("N17", "Stage Orders", "RP Orders", AGG, "stage-valid orders (delivery_stage_orders)", "COUNT([total_seconds])",
     "Orders whose four timestamps are in a valid order (95,088).",
     "Counts delivery_stage_orders rows through a column only that table has (never NULL). A table's (Count) "
     "field cannot be used inside a calculation.", INT)
calc("N18", "Purchase To Approval Days", "RP Orders", AGG, "stage-valid orders",
     "IF [Stage Orders] > 0 THEN SUM([purchase_to_approval_seconds]) / ([Stage Orders] * 86400) END",
     "Average days from purchase to payment approval (0.40).", GUARD, DAYS)
calc("N19", "Approval To Carrier Days", "RP Orders", AGG, "stage-valid orders",
     "IF [Stage Orders] > 0 THEN SUM([approval_to_carrier_seconds]) / ([Stage Orders] * 86400) END",
     "Average days from approval to carrier handover (2.85).", GUARD, DAYS)
calc("N20", "Carrier To Customer Days", "RP Orders", AGG, "stage-valid orders",
     "IF [Stage Orders] > 0 THEN SUM([carrier_to_customer_seconds]) / ([Stage Orders] * 86400) END",
     "Average days the carrier takes to deliver (9.36).", GUARD, DAYS)
calc("N21", "Stage Total Days", "RP Orders", AGG, "stage-valid orders",
     "IF [Stage Orders] > 0 THEN SUM([total_seconds]) / ([Stage Orders] * 86400) END",
     "Average purchase-to-delivery days on stage-valid orders (12.62).",
     "Differs from Avg Delivery Days (12.56 on 96,476 orders) by population: label both.", DAYS)
calc("N22", "Last Mile Share", "RP Orders", AGG, "stage-valid orders",
     "IF SUM([total_seconds]) > 0 THEN SUM([carrier_to_customer_seconds]) / SUM([total_seconds]) END",
     "Share of delivery time spent with the carrier (74.21%).", "Ratio of summed seconds.", PCT)
calc("N23", "Dispatch Stage Share", "RP Orders", AGG, "stage-valid orders",
     "IF SUM([total_seconds]) > 0 THEN SUM([approval_to_carrier_seconds]) / SUM([total_seconds]) END",
     "Share of delivery time from approval to carrier (22.60%).", "Ratio of summed seconds.", PCT)
calc("N24", "Approval Stage Share", "RP Orders", AGG, "stage-valid orders",
     "IF SUM([total_seconds]) > 0 THEN SUM([purchase_to_approval_seconds]) / SUM([total_seconds]) END",
     "Share of delivery time waiting for payment approval (3.19%).", "Ratio of summed seconds.", PCT)

# ---- Satisfaction --------------------------------------------------------------------
calc("M45", "Total Reviews", "RP Orders", AGG, "reviews (vw_review_summary)", "COUNT([review_id])",
     "Number of reviews (99,224).",
     "COUNT, NOT COUNTD: 814 review rows repeat a review_id (one review covering several orders), so COUNTD "
     "would give 98,410 (pitfall P03).", INT)
calc("M46", "Avg Review Score", "RP Orders", AGG, "reviews", "AVG([review_score])",
     "Average score per review, 1-5 (4.0864, review grain).", "Different metric from the order-grain M49.", DEC2)
calc("M47", "One-Star Rate", "RP Orders", AGG, "reviews",
     "IF [Total Reviews] > 0 THEN COUNT(IF [review_score] = 1 THEN [review_id] END) / [Total Reviews] END",
     "Share of reviews with 1 star (11.51%).", "Conditional COUNT.", PCT)
calc("M48", "Five-Star Rate", "RP Orders", AGG, "reviews",
     "IF [Total Reviews] > 0 THEN COUNT(IF [review_score] = 5 THEN [review_id] END) / [Total Reviews] END",
     "Share of reviews with 5 stars (57.78%).", "Conditional COUNT.", PCT)
calc("M49", "Avg Order Rating", "RP Orders", AGG, "orders",
     "AVG(IF [review_count] > 0 THEN [review_score_avg] END)",
     "Average review score per order (4.0868): orders with 2-3 reviews count once.",
     "From vw_order_summary (review_score_avg stored to 4 decimals).", DEC2)
calc("N25", "Pre-Delivery Reviews", "RP Orders", AGG, "reviews",
     "COUNT(IF [review_before_delivery] = 1 THEN [review_id] END)",
     "Reviews answered before the parcel arrived (4,795).", "Conditional COUNT.", INT)
calc("N26", "Pre-Delivery Review Share", "RP Orders", AGG, "reviews",
     """IF COUNT(IF NOT ISNULL([review_before_delivery]) THEN [review_id] END) > 0
THEN [Pre-Delivery Reviews] / COUNT(IF NOT ISNULL([review_before_delivery]) THEN [review_id] END)
END""", "Share of reviews on delivered orders that were answered before arrival (4.98%).",
     "The flag is NULL for undelivered orders, which are excluded from the denominator.", PCT)
calc("N27", "Avg Review Score After Arrival", "RP Orders", AGG, "reviews",
     "AVG(IF [review_before_delivery] = 0 THEN [review_score] END)",
     "Average score of reviews answered after arrival (4.279).", "Review grain.", DEC2)
calc("N28", "One-Star Rate After Arrival", "RP Orders", AGG, "reviews",
     """IF COUNT(IF [review_before_delivery] = 0 THEN [review_id] END) > 0
THEN COUNT(IF [review_before_delivery] = 0 AND [review_score] = 1 THEN [review_id] END)
     / COUNT(IF [review_before_delivery] = 0 THEN [review_id] END)
END""", "Share of after-arrival reviews with 1 star (6.76%).", GUARD, PCT)
calc("N35", "Avg Order Rating (Review Table)", "RP Orders", LOD, "per order, then averaged",
     "AVG({INCLUDE [order_id] : AVG([review_score])})",
     "Average score per order, computed from the review table so it can sit on a delivery_bucket axis.",
     "INCLUDE gives one value per order whatever its review count; averaging a FIXED value over review rows "
     "would over-weight the 547 multi-review orders (pitfall P02).", DEC2)
calc("N34", "Avg Order Rating After Arrival", "RP Orders", LOD, "per order, then averaged",
     "AVG({INCLUDE [order_id] : AVG(IF [review_before_delivery] = 0 THEN [review_score] END)})",
     "Average score per order, using only reviews answered after the parcel arrived.",
     "The after-arrival condition goes INSIDE the LOD: in 115 orders the reviews disagree on timing, and a "
     "FIXED LOD would ignore a review_before_delivery filter (pitfall P06).", DEC2)

CALC_BY_NAME = {(c["ds"], c["name"]): c for c in CALCS}
