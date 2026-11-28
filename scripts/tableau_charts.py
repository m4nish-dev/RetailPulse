"""
RetailPulse - chart worksheets, dashboards and dashboard actions for the generated Tableau workbook.

Used by scripts/build_tableau_workbook.py. Every sheet below is built from the validated data
sources and calculated fields in scripts/tableau_registry.py (nothing is recomputed here) and
follows tableau/dashboard_specification.md. Where the generated sheet differs from the written
specification, the difference is listed in DEVIATIONS (and in reports/tableau_final_validation.md).

XML vocabulary: copied from workbooks written by Tableau Desktop 2026.3 (the Superstore and
World Indicators samples shipped with Tableau Public) and checked against Tableau's official
2026.3 XSD. Elements with no example in those samples (parameter actions, navigation buttons)
follow the XSD.

Pill notation used in the sheet specs
  "D:field"        discrete dimension (field caption)            -> [none:<col>:nk|ok]
  "C:Calc Name"    aggregate / table calculation (registry name)  -> [usr:RP_xxx:qk]
  "B:Calc Name"    row-level boolean calculation (filters)        -> [none:RP_xxx:nk]
  "S:field"        SUM of a base column                            -> [sum:<col>:qk]
  "M:Order Month"  continuous month of a date calculation          -> [tmn:RP_H01:qk]
  "Q:field"        all values of a base column (range filter)      -> [none:<col>:qk]
  "RANK:field"     rank of SUM(field) (quick table calculation)    -> [rank:sum:<col>:qk]
  "BIN:field"      the bin of a field (see BINS)                   -> [none:<col> (bin):ok]
  "MV" / "MN"      Measure Values / Measure Names
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

# ---- design system -----------------------------------------------------------------------
ORANGE, BLUE, GREEN, AMBER, RED = "#D95926", "#3987E5", "#199E70", "#C98500", "#E66767"
INK, GREY, LIGHT, BG, WHITE = "#1A1A19", "#6B6B6B", "#D9D7D2", "#F4F3EF", "#FFFFFF"
FONT, FONT_BOLD = "Tableau Book", "Tableau Semibold"
PERIOD = "Olist marketplace · orders Sep 2016 – Oct 2018 · historical data, not live performance"
FOOTER = ("Revenue = product revenue (item prices, freight excluded) in BRL · no cost data, so no profit or margin · "
          "Data: Olist Brazilian E-Commerce Public Dataset (Kaggle), CC BY-NC-SA 4.0")

# Tableau data sources: (registry data source, tables). Tableau 2026.3.2 cannot query a data source in which
# two or more related tables share the root key (error 1B885FB3, "Logical Query missing field [key (table A)]
# from relationOp table B", runtime test 2026-11-28), so each registry data source with several related tables
# is published as several Tableau data sources: the root plus ONE related table, over the same .hyper extract.
# Field names, internal names and formulas are the registry's, unchanged; each Tableau data source carries the
# calculations whose every reference is available in it.
SOURCES = {
    "RP Orders": ("RP Orders", ["vw_order_summary", "vw_review_summary"]),
    "RP Delivery Stages": ("RP Orders", ["vw_order_summary", "delivery_stage_orders"]),
    "RP Customers": ("RP Customers", None),
    "RP Cohorts": ("RP Cohorts", None),
    "RP Categories": ("RP Categories", ["dim_category", "vw_category_performance"]),
    "RP Products": ("RP Categories", ["dim_category", "product_performance"]),
    "RP Category Reviews": ("RP Categories", ["dim_category", "category_satisfaction"]),
    "RP Sellers": ("RP Sellers", ["vw_seller_performance", "seller_scorecard"]),
    "RP Seller Categories": ("RP Sellers", ["vw_seller_performance", "seller_category_performance"]),
    "RP Stage Summary": ("RP Stage Summary", None),
}
KPI_SOURCE = {"5.6 Stage Shares": "RP Delivery Stages"}

# bins: (data source, field caption, size)
BINS = {("RP Customers", "Log10 Historical Value"): 0.25, ("RP Orders", "delivery_days"): 1}

DELIVERY_BUCKETS = ["15+ days early", "7-15 days early", "on time", "1-7 days late", "8-15 days late",
                    "15+ days late"]

# Every spec: name, ds, mark, rows, cols, and optional
#   enc     {color, size, wedge, text: [..], tooltip: [..], lod: [..]}
#   mv      measures shown through Measure Values (in this order)
#   tc      {pill: ("Rows"|"Columns") | ("Field", "D:field")}  table-calculation addressing
#   filters list of (kind, pill, value)  kinds: member, exclude, range, min, nonnull, top, true
#   sort    (pill, direction, using pill) or ("manual", pill, [values])
#   color   single mark colour; palette {pill: {value: colour}}; diverge pill
#   labels  show mark labels; refline (axis pill, "median"); title
CHARTS: list[dict] = [
    # ---------------- 1 Executive (RP Orders) ----------------
    dict(name="1.1 Revenue and Orders by Month", ds="RP Orders", mark="Line",
         title="Monthly revenue (with 3-month moving average) and orders",
         rows=["MV", "C:Total Orders"], cols=["M:Order Month"],
         mv=["C:Total Revenue", "C:Revenue 3M Moving Avg"], tc={"C:Revenue 3M Moving Avg": "Columns"},
         enc=dict(color="MN", tooltip=["C:Total Orders"]),
         palette={"MN": {"C:Total Revenue": ORANGE, "C:Revenue 3M Moving Avg": GREY}},
         filters=[("range", "Q:in_stable_window", (1, 1))]),
    dict(name="1.2 Revenue MoM %", ds="RP Orders", mark="Bar", title="Month-over-month revenue change",
         rows=["C:Revenue MoM %"], cols=["MD:Order Month"], tc={"C:Revenue MoM %": "Columns"},
         enc=dict(color="C:Revenue MoM %"), diverge="C:Revenue MoM %",
         filters=[("range", "Q:in_stable_window", (1, 1))]),
    dict(name="1.3 Revenue by State (Top 12)", ds="RP Orders", mark="Bar", title="Revenue by customer state (top 12)",
         rows=["D:customer_state"], cols=["C:Total Revenue"], color=ORANGE, labels=True,
         enc=dict(tooltip=["C:Total Orders", "C:Average Order Value"]),
         filters=[("top", "D:customer_state", (12, "C:Total Revenue"))],
         sort=("D:customer_state", "DESC", "C:Total Revenue")),
    dict(name="1.4 Top 10 Categories", ds="RP Categories", mark="Bar", title="Top 10 categories by revenue (all periods)",
         rows=["D:category"], cols=["C:Category Revenue"], color=BLUE, labels=True,
         enc=dict(tooltip=["C:Category Revenue Share"]),
         filters=[("top", "D:category", (10, "C:Category Revenue"))],
         sort=("D:category", "DESC", "C:Category Revenue")),
    # ---------------- 2 Customers ----------------
    dict(name="2.1 One-time vs Repeat", ds="RP Customers", mark="Pie", title="One-time vs repeat customers",
         rows=[], cols=[], enc=dict(color="D:is_repeat_customer", wedge="C:Total People",
                                    text=["D:is_repeat_customer", "C:Total People"]),
         palette={"D:is_repeat_customer": {0: LIGHT, 1: ORANGE}}, labels=True,
         aliases={"is_repeat_customer": {0: "One-time", 1: "Repeat"}}),
    dict(name="2.2 RFM Segments", ds="RP Customers", mark="Bar", title="RFM segments: share of customers vs share of revenue",
         rows=["D:rfm_segment", "MN"], cols=["MV"], mv=["C:Segment Customer Share", "C:Segment Revenue Share"],
         tc={"C:Segment Customer Share": ("Field", "D:rfm_segment"), "C:Segment Revenue Share": ("Field", "D:rfm_segment")},
         enc=dict(color="MN", tooltip=["C:Customers In Segment", "C:Segment Avg Historical Value"]), labels=True,
         palette={"MN": {"C:Segment Customer Share": GREY, "C:Segment Revenue Share": ORANGE}},
         filters=[("range", "Q:rfm_scored", (1, 1))],
         sort=("D:rfm_segment", "DESC", "S:monetary_value")),
    dict(name="2.3 Customer Value Distribution", ds="RP Customers", mark="Bar",
         title="Distribution of historical customer value (log10 BRL, bins of 0.25)",
         rows=["C:Total People"], cols=["BIN:Log10 Historical Value"], color=ORANGE,
         filters=[("nonnull", "Q:Log10 Historical Value", None)]),
    dict(name="2.4 Cohort Retention Matrix", ds="RP Cohorts", mark="Square",
         title="Cohort retention: share of each monthly cohort ordering again N months later",
         rows=["D:cohort_month"], cols=["D:months_since_acquisition"],
         enc=dict(color="C:Cohort Retention %", text=["C:Cohort Retention %"], tooltip=["C:Cohort Customers"]),
         sequential="C:Cohort Retention %", labels=True,
         filters=[("range", "Q:months_since_acquisition", (1, None))]),
    dict(name="2.5 Purchase Frequency", ds="RP Customers", mark="Bar", title="Customers by number of orders",
         rows=["C:Total People"], cols=["D:total_orders"], color=ORANGE, labels=True),
    # ---------------- 3 Products (RP Categories) ----------------
    dict(name="3.1 Revenue by Category (Top 15)", ds="RP Categories", mark="Bar", title="Revenue by category (top 15)",
         rows=["D:category"], cols=["C:Category Revenue"], color=ORANGE, labels=True,
         enc=dict(tooltip=["C:Category Revenue Share", "C:Category Items Sold"]),
         filters=[("top", "D:category", (15, "C:Category Revenue"))],
         sort=("D:category", "DESC", "C:Category Revenue")),
    dict(name="3.2 Pareto", ds="RP Categories", mark="Circle",
         title="Pareto: cumulative share of revenue by category rank",
         rows=["C:Category Cumulative Share"], cols=["RANK:revenue"],
         tc={"C:Category Cumulative Share": ("Field", "D:category"), "RANK:revenue": ("Field", "D:category")},
         enc=dict(lod=["D:category"], tooltip=["C:Category Revenue"]), color=ORANGE,
         sort=("D:category", "DESC", "C:Category Revenue")),
    dict(name="3.3 Monthly Trend (Top 5)", ds="RP Categories", mark="Line", title="Monthly revenue of the top 5 categories",
         rows=["C:Category Revenue"], cols=["D:order_month"], enc=dict(color="D:category"),
         filters=[("range", "Q:in_stable_window", (1, 1)), ("top", "D:category", (5, "C:Category Revenue"))]),
    dict(name="3.4 Growth vs Decline", ds="RP Categories", mark="Bar",
         title="Revenue growth, 2017 Q1 to Jun–Aug 2018 (categories with 50+ items in both periods)",
         rows=["D:category"], cols=["C:Category Growth Q1 2017 to Jun-Aug 2018"], labels=True,
         enc=dict(color="C:Category Growth Q1 2017 to Jun-Aug 2018"), diverge="C:Category Growth Q1 2017 to Jun-Aug 2018",
         filters=[("nonnull", "C:Category Growth Q1 2017 to Jun-Aug 2018", None)],
         sort=("D:category", "DESC", "C:Category Growth Q1 2017 to Jun-Aug 2018")),
    dict(name="3.5 Category Table", ds="RP Categories", mark="Text", title="Category table",
         rows=["D:category"], cols=["MN"], enc=dict(text=["MV"]),
         mv=["C:Category Revenue", "C:Category Items Sold", "S:orders", "C:Category Revenue Share", "C:Category Rank"],
         tc={"C:Category Rank": "Rows"},
         sort=("D:category", "DESC", "C:Category Revenue")),
    # ---------------- 4 Sellers ----------------
    dict(name="4.1 Top 20 Sellers", ds="RP Sellers", mark="Bar", title="Top 20 sellers by revenue (sellers with 50+ orders)",
         rows=["D:seller_id"], cols=["C:Seller Revenue"], color=ORANGE, labels=True,
         enc=dict(tooltip=["C:Seller Orders", "C:Seller Late Rate"]),
         filters=[("true", "B:Seller Has 50+ Orders", None), ("top", "D:seller_id", (20, "C:Seller Revenue"))],
         sort=("D:seller_id", "DESC", "C:Seller Revenue")),
    dict(name="4.2 Seller Concentration Curve", ds="RP Sellers", mark="Circle",
         title="Seller concentration: cumulative share of revenue by seller rank",
         rows=["C:Seller Cumulative Share"], cols=["RANK:revenue"],
         tc={"C:Seller Cumulative Share": ("Field", "D:seller_id"), "RANK:revenue": ("Field", "D:seller_id")},
         enc=dict(lod=["D:seller_id"], tooltip=["C:Seller Revenue"]), color=ORANGE,
         sort=("D:seller_id", "DESC", "C:Seller Revenue")),
    dict(name="4.3 Scorecard Scatter", ds="RP Sellers", mark="Circle",
         title="Seller scorecard: late rate vs inherited order rating (sellers with 50+ orders)",
         rows=["C:Seller Inherited Order Rating"], cols=["C:Seller Late Rate"],
         enc=dict(lod=["D:seller_id"], size="C:Seller Revenue", tooltip=["C:Seller Orders"]),
         color=ORANGE, refline=["C:Seller Late Rate", "C:Seller Inherited Order Rating"],
         filters=[("true", "B:Seller Has 50+ Orders", None)]),
    dict(name="4.4 Intervention Table", ds="RP Sellers", mark="Text",
         title="Sellers needing intervention (100+ orders, inherited rating below 3.8)",
         rows=["D:seller_id", "D:seller_state"], cols=["MN"], enc=dict(text=["MV"]),
         mv=["C:Seller Revenue", "C:Seller Orders", "C:Seller Inherited Order Rating", "C:Seller Late Rate"],
         filters=[("true", "A:Needs Intervention", None)],
         sort=("D:seller_id", "DESC", "C:Seller Revenue")),
    # ---------------- 5 Operations ----------------
    dict(name="5.1 Order Status", ds="RP Orders", mark="Bar", title="Orders by status",
         rows=["D:order_status"], cols=["C:Total Orders"], color=BLUE, labels=True,
         sort=("D:order_status", "DESC", "C:Total Orders")),
    dict(name="5.2 Promised vs Actual", ds="RP Orders", mark="Line",
         title="Promised vs actual delivery time (days, delivered orders)",
         rows=["MV"], cols=["M:Order Month"], mv=["C:Avg Promised Days", "C:Avg Delivery Days"],
         enc=dict(color="MN"), palette={"MN": {"C:Avg Promised Days": GREY, "C:Avg Delivery Days": ORANGE}},
         filters=[("range", "Q:in_stable_window", (1, 1))]),
    dict(name="5.3 Delivery by State", ds="RP Orders", mark="Bar", title="Late delivery rate by customer state",
         rows=["D:customer_state"], cols=["C:Late Delivery Rate"], labels=True,
         enc=dict(color="C:Late Delivery Rate", tooltip=["C:Avg Delivery Days", "C:Delivery Denominator"]),
         sequential_red="C:Late Delivery Rate", sort=("D:customer_state", "DESC", "C:Late Delivery Rate")),
    dict(name="5.4 Delivery Time Distribution", ds="RP Orders", mark="Bar",
         title="Delivery time distribution (days from purchase to delivery, up to 60)",
         rows=["C:Delivery Denominator"], cols=["BIN:delivery_days"], color=BLUE,
         filters=[("range", "Q:delivery_days", (0, 60))]),
    dict(name="5.5 Delivery Stage Breakdown", ds="RP Stage Summary", mark="Bar",
         title="Where delivery time goes (average days per stage)",
         rows=[], cols=["S:avg_days"], enc=dict(color="D:stage", text=["S:avg_days"]), labels=True,
         palette={"D:stage": {"Purchase to approval": AMBER, "Approval to carrier handoff": BLUE,
                              "Carrier handoff to customer": ORANGE}},
         filters=[("range", "Q:stage_order", (1, 3))]),
    # ---------------- 6 Satisfaction ----------------
    dict(name="6.1 Score Distribution", ds="RP Orders", mark="Bar", title="Reviews by score",
         rows=["C:Total Reviews"], cols=["D:review_score"], color=ORANGE, labels=True),
    dict(name="6.2 Delay vs Score", ds="RP Orders", mark="Bar",
         title="Average order rating by delivery timing (all reviews vs after arrival)",
         rows=["D:delivery_bucket"], cols=["MV"], mv=["C:Avg Order Rating (Review Table)", "C:Avg Order Rating After Arrival"],
         enc=dict(color="MN", tooltip=["C:Total Reviews", "C:One-Star Rate", "C:One-Star Rate After Arrival"]),
         palette={"MN": {"C:Avg Order Rating (Review Table)": ORANGE, "C:Avg Order Rating After Arrival": GREY}},
         labels=True, filters=[("exclude", "D:delivery_bucket", ["not delivered"])],
         sort=("manual", "D:delivery_bucket", DELIVERY_BUCKETS)),
    dict(name="6.3 Satisfaction Trend", ds="RP Orders", mark="Line", title="Average review score and one-star rate by month",
         rows=["C:Avg Review Score", "C:One-Star Rate"], cols=["M:Order Month"], color=ORANGE,
         filters=[("range", "Q:in_stable_window", (1, 1))]),
    dict(name="6.4 Category Satisfaction", ds="RP Category Reviews", mark="Bar",
         title="Average review score by category (categories with 300+ items sold)",
         rows=["D:category"], cols=["C:Category Avg Review Score"], color=ORANGE, labels=True,
         enc=dict(tooltip=["C:Category One-Star Rate", "C:Category Avg Score After Arrival", "C:Category Review Count"]),
         filters=[("min", "S:item_count", 300)],
         sort=("D:category", "ASC", "C:Category Avg Review Score")),
    # ---------------- 7 Category Detail ----------------
    dict(name="7.0 KPIs", ds="RP Categories", kpi=["M24", "M27", "N39"],
         filters=[("true", "B:Is Selected Category", None)]),
    dict(name="7.0 Product KPIs", ds="RP Products", kpi=["N09", "N11"],
         filters=[("true", "B:Is Selected Category", None)]),
    dict(name="7.0 Review KPIs", ds="RP Category Reviews", kpi=["N30", "N31", "N33"],
         filters=[("true", "B:Is Selected Category", None)]),
    dict(name="7.1 Rank and Cumulative Share", ds="RP Categories", mark="Text", title="Rank among 74 categories",
         rows=["D:category"], cols=["MN"], enc=dict(text=["MV"]), mv=["C:Category Rank", "C:Category Cumulative Share"],
         tc={"C:Category Rank": ("Field", "D:category"), "C:Category Cumulative Share": ("Field", "D:category")},
         filters=[("tctrue", "C:Selected Category TC", ("Field", "D:category"))],
         sort=("D:category", "DESC", "C:Category Revenue")),
    dict(name="7.2 Monthly Trend", ds="RP Categories", mark="Line", title="Monthly revenue of the selected category",
         rows=["C:Category Revenue"], cols=["D:order_month"], color=ORANGE,
         filters=[("true", "B:Is Selected Category", None), ("range", "Q:in_stable_window", (1, 1))]),
    dict(name="7.3 Top 10 Products", ds="RP Products", mark="Text", title="Top 10 products in the category",
         rows=["D:product_id"], cols=["MN"], enc=dict(text=["MV"]),
         mv=["C:Product Revenue", "C:Product Units Sold", "C:Product Avg Item Price", "S:seller_count"],
         filters=[("ctxtrue", "B:Is Selected Category", None), ("top", "D:product_id", (10, "C:Product Revenue"))],
         sort=("D:product_id", "DESC", "C:Product Revenue")),
    dict(name="7.4 Top 10 Sellers in Category", ds="RP Seller Categories", mark="Text", title="Top 10 sellers in the category",
         rows=["D:seller_id", "D:seller_state"], cols=["MN"], enc=dict(text=["MV"]),
         mv=["C:Seller Category Revenue", "C:Seller Category Items", "C:Seller Category Late Rate",
             "C:Seller Category Dispatch Days"],
         filters=[("ctxtrue", "B:Is Selected Category", None), ("top", "D:seller_id", (10, "C:Seller Category Revenue"))],
         sort=("D:seller_id", "DESC", "C:Seller Category Revenue")),
    dict(name="7.5 Seller Delivery in Category", ds="RP Seller Categories", kpi=["N15", "N16", "N13"],
         filters=[("ctxtrue", "B:Is Selected Category", None)]),
    dict(name="7.6 Satisfaction", ds="RP Category Reviews", mark="Bar", title="Review score: all reviews vs after arrival",
         rows=["MN"], cols=["MV"], mv=["C:Category Avg Review Score", "C:Category Avg Score After Arrival"],
         enc=dict(color="MN", tooltip=["C:Category Review Count"]), labels=True,
         palette={"MN": {"C:Category Avg Review Score": ORANGE, "C:Category Avg Score After Arrival": GREY}},
         filters=[("true", "B:Is Selected Category", None)]),
    # ---------------- 8 Seller Detail ----------------
    dict(name="8.0 KPIs", ds="RP Sellers", kpi=["M29", "M31", "M33", "M32", "M35"],
         filters=[("true", "B:Is Selected Seller", None)]),
    dict(name="8.1 Cumulative Share", ds="RP Sellers", mark="Text", title="Cumulative revenue share at this seller",
         rows=["D:seller_id"], cols=["MN"], enc=dict(text=["MV"]), mv=["C:Seller Cumulative Share"],
         tc={"C:Seller Cumulative Share": ("Field", "D:seller_id")},
         filters=[("tctrue", "C:Selected Seller TC", ("Field", "D:seller_id"))],
         sort=("D:seller_id", "DESC", "C:Seller Revenue")),
    dict(name="8.2 Profile", ds="RP Sellers", mark="Text", title="Seller profile",
         rows=["D:seller_state", "D:seller_city", "D:first_sale", "D:last_sale"], cols=["MN"], enc=dict(text=["MV"]),
         mv=["S:poor_rated_orders"], filters=[("true", "B:Is Selected Seller", None)]),
    dict(name="8.3 Categories Sold", ds="RP Seller Categories", mark="Bar", title="Revenue by category for this seller",
         rows=["D:category"], cols=["C:Seller Category Revenue"], color=ORANGE, labels=True,
         filters=[("true", "B:Is Selected Seller", None)], sort=("D:category", "DESC", "C:Seller Category Revenue")),
    dict(name="8.4 Category Breakdown", ds="RP Seller Categories", mark="Text", title="Category breakdown",
         rows=["D:category"], cols=["MN"], enc=dict(text=["MV"]),
         mv=["C:Seller Category Revenue", "C:Seller Category Items", "C:Seller Category Late Rate",
             "C:Seller Category Dispatch Days"],
         filters=[("true", "B:Is Selected Seller", None)], sort=("D:category", "DESC", "C:Seller Category Revenue")),
]

# dashboard filter controls: (field pill, mode, title, [sheets]) per dashboard
STATE_ORDERS = "D:customer_state"
DASH_FILTERS = {
    "1 Executive": [("D:order_year", "checkdropdown", "Order year",
                     ["1.0 KPIs", "1.1 Revenue and Orders by Month", "1.2 Revenue MoM %", "1.3 Revenue by State (Top 12)"]),
                    (STATE_ORDERS, "checkdropdown", "Customer state",
                     ["1.0 KPIs", "1.1 Revenue and Orders by Month", "1.2 Revenue MoM %", "1.5 YoY Jan–Aug"]),
                    ("D:order_status", "checkdropdown", "Order status",
                     ["1.0 KPIs", "1.1 Revenue and Orders by Month", "1.2 Revenue MoM %", "1.3 Revenue by State (Top 12)",
                      "1.5 YoY Jan–Aug"])],
    "2 Customers": [("D:customer_state", "checkdropdown", "Customer state",
                     ["2.0 KPIs", "2.1 One-time vs Repeat", "2.2 RFM Segments", "2.3 Customer Value Distribution",
                      "2.5 Purchase Frequency"])],
    "4 Sellers": [("D:seller_state", "checkdropdown", "Seller state",
                   ["4.0 KPIs", "4.1 Top 20 Sellers", "4.2 Seller Concentration Curve", "4.3 Scorecard Scatter",
                    "4.4 Intervention Table"])],
    "5 Operations": [("D:order_year", "checkdropdown", "Order year",
                      ["5.0 KPIs", "5.1 Order Status", "5.2 Promised vs Actual", "5.3 Delivery by State",
                       "5.4 Delivery Time Distribution"]),
                     (STATE_ORDERS, "checkdropdown", "Customer state",
                      ["5.0 KPIs", "5.1 Order Status", "5.2 Promised vs Actual", "5.3 Delivery by State",
                       "5.4 Delivery Time Distribution"])],
    "6 Satisfaction": [("D:order_year", "checkdropdown", "Order year",
                        ["6.0 KPIs", "6.1 Score Distribution", "6.2 Delay vs Score", "6.3 Satisfaction Trend"]),
                       (STATE_ORDERS, "checkdropdown", "Customer state",
                        ["6.0 KPIs", "6.1 Score Distribution", "6.2 Delay vs Score", "6.3 Satisfaction Trend"])],
}

MAIN = ["1 Executive", "2 Customers", "3 Products", "4 Sellers", "5 Operations", "6 Satisfaction"]
NAV_LABEL = {"1 Executive": "Executive", "2 Customers": "Customers", "3 Products": "Products", "4 Sellers": "Sellers",
             "5 Operations": "Operations", "6 Satisfaction": "Satisfaction"}

# Dashboards: rows of (height px, [(sheet or text key, width fraction)])
DASHBOARDS = [
    dict(name="1 Executive", title="Executive overview", question="How is the business doing overall?",
         kpi="1.0 KPIs", rows=[(390, [("1.1 Revenue and Orders by Month", 0.62), ("1.2 Revenue MoM %", 0.38)]),
                               (380, [("1.3 Revenue by State (Top 12)", 0.38), ("1.4 Top 10 Categories", 0.38),
                                      ("1.5 YoY Jan–Aug", 0.24)])],
         captions=["Top 3 of 27 states = 63.4% of revenue. The YoY card compares Jan–Aug 2018 with Jan–Aug 2017 (2016 has "
                   "only 329 orders, so full-year growth is not meaningful) and ignores the year filter. Top 10 categories: "
                   "all periods, separate data source, not affected by these filters. Click a state to filter the page."]),
    dict(name="2 Customers", title="Customers", question="Who buys, and do they come back?", kpi="2.0 KPIs",
         rows=[(410, [("2.4 Cohort Retention Matrix", 0.6), ("2.2 RFM Segments", 0.4)]),
               (360, [("2.1 One-time vs Repeat", 0.26), ("2.3 Customer Value Distribution", 0.42),
                      ("2.5 Purchase Frequency", 0.32)])],
         captions=["Historical value is what customers actually spent; it is NOT predicted lifetime value (a 3.12% repeat rate "
                   "gives no basis for prediction). Later cohorts are right-censored: blank cells were not yet observable "
                   "(190 cells), never zero. RFM frequency is scored 1/3/5, not quintiles: 96.88% of customers ordered once. "
                   "Customer figures are lifetime totals and are not filtered by order date."]),
    dict(name="3 Products", title="Products", question="Which categories drive revenue and growth?", kpi="3.0 KPIs",
         rows=[(380, [("3.1 Revenue by Category (Top 15)", 0.5), ("3.2 Pareto", 0.5)]),
               (390, [("3.3 Monthly Trend (Top 5)", 0.36), ("3.4 Growth vs Decline", 0.30), ("3.5 Category Table", 0.34)])],
         captions=["18 of 74 categories reach 80% of revenue. Growth compares 2017 Q1 with Jun–Aug 2018 (the last three complete "
                   "months), only for categories with 50+ items in both periods. Click a category to select it, then use "
                   "'Category Detail' in a tooltip menu opens the detail page; choose the category there."]),
    dict(name="4 Sellers", title="Sellers", question="Which sellers matter, and which need help?", kpi="4.0 KPIs",
         rows=[(400, [("4.3 Scorecard Scatter", 0.58), ("4.1 Top 20 Sellers", 0.42)]),
               (370, [("4.2 Seller Concentration Curve", 0.42), ("4.4 Intervention Table", 0.58)])],
         captions=["Reviews attach to the order, not the seller: every seller in a multi-seller order inherits its score, so this "
                   "is an inherited order rating, not a seller rating. Delivery time is mostly the carrier's (74.2%). "
                   "Seller orders are seller-order pairs, not orders. Largest seller 1.70%; top 10% of sellers 67.5% of revenue. "
                   "Lines on the scatter are the medians. 'Seller Detail' in a tooltip menu opens the detail page; paste the seller_id there."]),
    dict(name="5 Operations", title="Operations", question="Are orders delivered on time, and where does time go?",
         kpi="5.0 KPIs",
         rows=[(390, [("5.2 Promised vs Actual", 0.6), ("5.3 Delivery by State", 0.4)]),
               (380, [("5.1 Order Status", 0.25), ("5.4 Delivery Time Distribution", 0.33),
                      ("5.5 Delivery Stage Breakdown", 0.24), ("5.6 Stage Shares", 0.18)])],
         captions=["On-time is measured against Olist's own estimated date, padded by up to 27 days in early 2017: it reflects "
                   "cautious promising as much as fast logistics. Delivery averages use the 96,476 orders with a delivery date. "
                   "Stage breakdown: 95,088 orders with four valid timestamps (12.62 days; carrier leg 74.2%); it ignores the "
                   "filters and the year filter. Distribution capped at 60 days (306 orders take longer; median 10.22, "
                   "mean 12.56). Click a state to filter the page (the stage shares too)."]),
    dict(name="6 Satisfaction", title="Customer satisfaction", question="How do customers rate their orders, and why?",
         kpi="6.0 KPIs",
         rows=[(400, [("6.2 Delay vs Score", 0.55), ("6.3 Satisfaction Trend", 0.45)]),
               (370, [("6.1 Score Distribution", 0.4), ("6.4 Category Satisfaction", 0.6)])],
         captions=["Correlation, not causation: a late delivery may share a cause with a bad experience. 4,795 reviews were "
                   "written before the parcel arrived; the after-arrival bars exclude them. Reviews rate the whole order, "
                   "delivery included, not product quality alone. Category chart: all periods, not filtered; categories with "
                   "300+ eligible items (35)."]),
    dict(name="7 Category Detail", title="Category detail", question="",
         kpi=["7.0 KPIs", "7.0 Product KPIs", "7.0 Review KPIs"], detail="p_category",
         back="3 Products", height=1000,
         rows=[(330, [("7.2 Monthly Trend", 0.5), ("7.6 Satisfaction", 0.3), ("7.1 Rank and Cumulative Share", 0.2)]),
               (330, [("7.3 Top 10 Products", 0.45), ("7.4 Top 10 Sellers in Category", 0.4),
                      ("7.5 Seller Delivery in Category", 0.15)])],
         captions=["Shows the category chosen in the p_category box (top right). "
                   "Full history; the Products page filters do not carry over. Reviews rate the whole order. Dispatch days use "
                   "single-seller orders with valid timestamps."]),
    dict(name="8 Seller Detail", title="Seller detail", question="", kpi="8.0 KPIs", detail="p_seller",
         back="4 Sellers", height=1000,
         rows=[(340, [("8.3 Categories Sold", 0.5), ("8.2 Profile", 0.3), ("8.1 Cumulative Share", 0.2)]),
               (320, [("8.4 Category Breakdown", 1.0)])],
         captions=["Shows the seller whose seller_id is in the p_seller box (top right; default: the largest seller). Inherited "
                   "order rating: reviews attach to the order, not the seller. Delivery time is mostly the carrier's (74.2%)."]),
]

# Dashboard actions
ACTIONS = [
    dict(kind="filter", caption="Filter page by state", dashboard="1 Executive", source="1.3 Revenue by State (Top 12)",
         exclude=["1.3 Revenue by State (Top 12)", "1.4 Top 10 Categories"]),
    dict(kind="filter", caption="Filter page by state", dashboard="5 Operations", source="5.3 Delivery by State",
         exclude=["5.3 Delivery by State", "5.5 Delivery Stage Breakdown"]),
    dict(kind="goto", caption="Category Detail", dashboard="3 Products", target="7 Category Detail",
         sources=["3.1 Revenue by Category (Top 15)", "3.2 Pareto", "3.4 Growth vs Decline", "3.5 Category Table"],
         keep=["7.0 KPIs"]),
    dict(kind="goto", caption="Seller Detail", dashboard="4 Sellers", target="8 Seller Detail",
         sources=["4.1 Top 20 Sellers", "4.3 Scorecard Scatter", "4.4 Intervention Table"], keep=["8.0 KPIs"]),
    dict(kind="goto", caption="Back to Products", dashboard="7 Category Detail", target="3 Products",
         sources=["7.0 KPIs", "7.2 Monthly Trend"], keep=[]),
    dict(kind="goto", caption="Back to Sellers", dashboard="8 Seller Detail", target="4 Sellers",
         sources=["8.0 KPIs", "8.3 Categories Sold"], keep=[]),
]


def kpis(d: dict) -> list[str]:
    return d["kpi"] if isinstance(d["kpi"], list) else [d["kpi"]]

DEVIATIONS = [
    ("1.1", "Orders drawn as a second line pane (spec: bars) so the sheet stays a single mark type; revenue and its "
            "3-month average share one axis as specified."),
    ("1.2", "Diverging orange-blue colour instead of red-green (colour-blind safe); values unchanged."),
    ("3.2, 4.2", "X axis = revenue rank (a rank table calculation) instead of 74 / 3,053 category or seller headers, which "
                 "are unreadable at dashboard size; the 80% reference line is described in the caption instead."),
    ("5.1", "Linear axis with value labels instead of a logarithmic axis."),
    ("5.4", "Bins up to 60 days (306 of 96,476 measurable orders take longer, stated in the caption); median and mean "
            "stated in the caption instead of a reference line."),
    ("data sources", "Registry data sources with several related tables are published as two-table Tableau data "
                     "sources (root + one related table) over the same extracts: Tableau 2026.3.2 returns error "
                     "1B885FB3 when two related tables share the root key. Formulas unchanged."),
    ("navigation", "No navigation buttons: Tableau 2026.3.2 rejected the generated button element (error D2E8DA72). "
                   "Dashboards are reached through the workbook tabs; detail pages open from tooltip-menu actions "
                   "and return through 'Back to …' menu actions."),
    ("3.5", "Avg item price column dropped (it lives in product_performance, a different related table)."),
    ("6.4", "The 300-item floor uses category_satisfaction.item_count (eligible items, the same data source as the "
            "scores) instead of Category Items Sold from another table; the same 35 categories qualify (checked)."),
    ("3.3", "Named '3.3 Monthly Trend (Top 5)': the comma of the specified name would break Tableau's comma-separated "
            "sheet lists in dashboard actions."),
    ("4.1, 4.3", "seller_state not in the tooltip: with seller_state both on the tooltip and in the dashboard's shared "
                 "seller-state filter, Tableau 2026.3.2 did not query the sheet at all (runtime test)."),
    ("7.0", "KPI strip split into three sheets by table (category, product, review KPIs)."),
    ("7, 8", "No parameter actions: Tableau 2026.3.2 rejected the edit-parameter-action element (error D2E8DA72, even "
             "empty). The detail pages are driven by a parameter control instead (category dropdown of the 74 "
             "categories; seller_id type-in box); the tooltip-menu actions from Products / Sellers open them."),
]


def pill_parts(p: str) -> tuple[str, str]:
    k, _, f = p.partition(":")
    return k, f


def mv_member_name(inst: str) -> str:
    return inst


def all_sheet_names() -> list[str]:
    return [c["name"] for c in CHARTS]


def text_runs(parent, runs):
    """runs: list of (text, attrs) appended to a <formatted-text>."""
    ft = ET.SubElement(parent, "formatted-text")
    for text, attrs in runs:
        r = ET.SubElement(ft, "run", attrs)
        r.text = text
    return ft


def sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", name)
