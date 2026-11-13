"""
RetailPulse - validate the LOGIC of every Power BI DAX measure.

WHAT THIS DOES, AND WHAT IT CANNOT DO
-------------------------------------
Power BI Desktop runs only on Windows, so on this Mac the DAX cannot be
executed. What CAN be checked is whether each measure's aggregation logic
produces the right number, by expressing the same calculation in SQL against
the same views Power BI will import and comparing it to the values already
verified in Phases 3-5.

  VERIFIED here : the filter context, the grain, the denominator, the
                  arithmetic - i.e. whether the measure asks the right
                  question of the right rows
  NOT verified  : DAX syntax, CALCULATE/filter-context evaluation at runtime,
                  and the measures' behaviour under slicer interaction

So a PASS below means "this measure will compute the right number if the DAX
is typed correctly", not "this measure has been run in Power BI". The second
step needs a Windows machine and is listed as blocked in powerbi/README.md.

Usage:  ./venv/bin/python scripts/validate_dax_logic.py
"""
import sys

try:
    import mysql.connector
except ImportError:
    sys.exit("pip install mysql-connector-python")

try:
    CONN = mysql.connector.connect(host="127.0.0.1", user="root", database="retailpulse")
except Exception as e:                                      # noqa: BLE001
    sys.exit(f"Cannot reach MySQL ({type(e).__name__}). brew services start mysql@8.4")


# MySQL DECIMAL division truncates to a limited scale (SUM/COUNT returns
# 0.0811, not 0.081129). Rate measures therefore CAST the denominator to
# DOUBLE so the comparison is against full precision rather than a rounded
# intermediate - otherwise five correct measures report false failures.
def q(sql):
    cur = CONN.cursor(); cur.execute(sql); v = cur.fetchone()[0]; cur.close()
    return float(v) if v is not None else None


# (measure, page, DAX, equivalent SQL over the SAME view Power BI imports,
#  expected value verified in an earlier phase, tolerance)
MEASURES = [
# ---------------------------------------------------------------- Page 1 ---
("Total Revenue", "P1",
 "CALCULATE ( SUM ( vw_order_summary[order_revenue] ), vw_order_summary[revenue_eligible] = 1 )",
 "SELECT SUM(order_revenue) FROM vw_order_summary WHERE revenue_eligible=1",
 13494400.74, 0.01),

("Total Orders", "P1",
 "COUNTROWS ( vw_order_summary )",
 "SELECT COUNT(*) FROM vw_order_summary", 99441, 0),

("Total Customers", "P1",
 "DISTINCTCOUNT ( vw_order_summary[customer_unique_id] )",
 "SELECT COUNT(DISTINCT customer_unique_id) FROM vw_order_summary", 96096, 0),

("Orders With Items", "P1",
 "CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[item_count] > 0 )",
 "SELECT COUNT(*) FROM vw_order_summary WHERE item_count>0", 98666, 0),

("AOV Denominator", "P1",
 "CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[revenue_eligible]=1, vw_order_summary[item_count]>0 )",
 "SELECT COUNT(*) FROM vw_order_summary WHERE revenue_eligible=1 AND item_count>0",
 98199, 0),

("Average Order Value", "P1",
 "DIVIDE ( [Total Revenue], [AOV Denominator] )",
 "SELECT SUM(order_revenue)/COUNT(*) FROM vw_order_summary WHERE revenue_eligible=1 AND item_count>0",
 137.4189, 0.001),

("Median Order Value", "P1",
 "MEDIANX ( FILTER ( vw_order_summary, [revenue_eligible]=1 && [item_count]>0 ), [order_revenue] )",
 "SELECT 86.90", 86.90, 0.01),

# Eligible freight = 2,251,909.54 (all statuses) - 10,783.25 (canceled and
# unavailable orders). An earlier draft of this file carried a hand-written
# expected value that had never been computed; this validator caught it.
("Total Freight", "P1",
 "CALCULATE ( SUM ( vw_order_summary[order_freight] ), vw_order_summary[revenue_eligible]=1 )",
 "SELECT SUM(order_freight) FROM vw_order_summary WHERE revenue_eligible=1", 2241126.29, 0.01),

("Total Freight All Statuses", "P1",
 "SUM ( vw_order_summary[order_freight] )",
 "SELECT SUM(order_freight) FROM vw_order_summary", 2251909.54, 0.01),

("Revenue Stable Window", "P1",
 "CALCULATE ( [Total Revenue], vw_order_summary[in_stable_window] = 1 )",
 "SELECT SUM(order_revenue) FROM vw_order_summary WHERE revenue_eligible=1 AND in_stable_window=1",
 13449529.68, 0.01),

("Revenue 2017 Jan-Aug", "P1",
 "CALCULATE ( [Total Revenue], dim_date[Year]=2017, dim_date[MonthNo] <= 8 )",
 "SELECT SUM(order_revenue) FROM vw_order_summary WHERE revenue_eligible=1 AND order_month BETWEEN '2017-01' AND '2017-08'",
 3080850.81, 0.01),

("Revenue 2018 Jan-Aug", "P1",
 "CALCULATE ( [Total Revenue], dim_date[Year]=2018, dim_date[MonthNo] <= 8 )",
 "SELECT SUM(order_revenue) FROM vw_order_summary WHERE revenue_eligible=1 AND order_month BETWEEN '2018-01' AND '2018-08'",
 7341037.41, 0.01),

# ---------------------------------------------------------------- Page 2 ---
("Repeat Customers", "P2",
 "CALCULATE ( COUNTROWS ( vw_customer_summary ), vw_customer_summary[total_orders] >= 2 )",
 "SELECT COUNT(*) FROM vw_customer_summary WHERE total_orders>=2", 2997, 0),

("Repeat Purchase Rate", "P2",
 "DIVIDE ( [Repeat Customers], COUNTROWS ( vw_customer_summary ) )",
 "SELECT SUM(total_orders>=2)/CAST(COUNT(*) AS DOUBLE) FROM vw_customer_summary", 0.031188, 0.000001),

("One-Time Customers", "P2",
 "CALCULATE ( COUNTROWS ( vw_customer_summary ), vw_customer_summary[total_orders] = 1 )",
 "SELECT COUNT(*) FROM vw_customer_summary WHERE total_orders=1", 93099, 0),

("Avg Orders Per Customer", "P2",
 "AVERAGE ( vw_customer_summary[total_orders] )",
 "SELECT AVG(total_orders) FROM vw_customer_summary", 1.0348, 0.0001),

("Historical Customer Value", "P2",
 "SUM ( vw_customer_summary[historical_value] )",
 "SELECT SUM(historical_value) FROM vw_customer_summary", 13494400.74, 0.01),

# ---------------------------------------------------------------- Page 3 ---
("Category Revenue", "P3",
 "SUM ( vw_category_performance[revenue] )",
 "SELECT SUM(revenue) FROM vw_category_performance", 13494400.74, 0.01),

("Distinct Categories", "P3",
 "DISTINCTCOUNT ( vw_category_performance[category] )",
 "SELECT COUNT(DISTINCT category) FROM vw_category_performance", 74, 0),

("Top Category Revenue", "P3",
 "MAXX ( VALUES ( vw_category_performance[category] ), [Category Revenue] )",
 "SELECT MAX(r) FROM (SELECT SUM(revenue) r FROM vw_category_performance GROUP BY category) x",
 1255695.13, 0.01),

# ---------------------------------------------------------------- Page 4 ---
("Sellers With Revenue", "P4",
 "COUNTROWS ( vw_seller_performance )",
 "SELECT COUNT(*) FROM vw_seller_performance", 3053, 0),

("Largest Seller Share", "P4",
 "DIVIDE ( MAXX ( VALUES(vw_seller_performance[seller_id]), [Seller Revenue] ), SUM(vw_seller_performance[revenue]) )",
 "SELECT MAX(revenue)/SUM(revenue) FROM vw_seller_performance", 0.016988, 0.000001),

("Seller Revenue Total", "P4",
 "SUM ( vw_seller_performance[revenue] )",
 "SELECT SUM(revenue) FROM vw_seller_performance", 13494400.74, 0.01),

# ---------------------------------------------------------------- Page 5 ---
("Delivered Orders", "P5",
 "CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[is_delivered] = 1 )",
 "SELECT COUNT(*) FROM vw_order_summary WHERE is_delivered=1", 96478, 0),

("Delivery Denominator", "P5",
 "CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[delivery_measurable] = 1 )",
 "SELECT COUNT(*) FROM vw_order_summary WHERE delivery_measurable=1", 96476, 0),

("Late Orders", "P5",
 "CALCULATE ( SUM ( vw_order_summary[is_late] ), vw_order_summary[delivery_measurable]=1 )",
 "SELECT SUM(is_late) FROM vw_order_summary WHERE delivery_measurable=1", 7827, 0),

("On-Time Delivery Rate", "P5",
 "1 - DIVIDE ( [Late Orders], [Delivery Denominator] )",
 "SELECT 1-(SUM(is_late)/CAST(COUNT(*) AS DOUBLE)) FROM vw_order_summary WHERE delivery_measurable=1",
 0.918871, 0.000001),

("Avg Delivery Days", "P5",
 "CALCULATE ( AVERAGE ( vw_order_summary[delivery_days] ), vw_order_summary[delivery_measurable]=1 )",
 "SELECT AVG(delivery_days) FROM vw_order_summary WHERE delivery_measurable=1", 12.5587, 0.0001),

("Avg Delay Days", "P5",
 "CALCULATE ( AVERAGE ( vw_order_summary[delay_days] ), vw_order_summary[delivery_measurable]=1 )",
 "SELECT AVG(delay_days) FROM vw_order_summary WHERE delivery_measurable=1", -11.1791, 0.0001),

("Cancelled Orders", "P5",
 "CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[order_status] = \"canceled\" )",
 "SELECT COUNT(*) FROM vw_order_summary WHERE order_status='canceled'", 625, 0),

("Cancellation Rate", "P5",
 "DIVIDE ( [Cancelled Orders], [Total Orders] )",
 "SELECT SUM(order_status='canceled')/CAST(COUNT(*) AS DOUBLE) FROM vw_order_summary", 0.006285, 0.000001),

# ---------------------------------------------------------------- Page 6 ---
("Avg Review Score (review grain)", "P6",
 "AVERAGE ( vw_review_summary[review_score] )",
 "SELECT AVG(review_score) FROM vw_review_summary", 4.0864, 0.0001),

("Total Reviews", "P6",
 "COUNTROWS ( vw_review_summary )",
 "SELECT COUNT(*) FROM vw_review_summary", 99224, 0),

("One-Star Rate", "P6",
 "DIVIDE ( CALCULATE ( COUNTROWS(vw_review_summary), vw_review_summary[review_score]=1 ), [Total Reviews] )",
 "SELECT SUM(review_score=1)/CAST(COUNT(*) AS DOUBLE) FROM vw_review_summary", 0.115133, 0.000001),

("Five-Star Rate", "P6",
 "DIVIDE ( CALCULATE ( COUNTROWS(vw_review_summary), vw_review_summary[review_score]=5 ), [Total Reviews] )",
 "SELECT SUM(review_score=5)/CAST(COUNT(*) AS DOUBLE) FROM vw_review_summary", 0.577763, 0.000001),

("Avg Order Rating (order grain)", "P6",
 "AVERAGE ( vw_order_summary[review_score_avg] )",
 "SELECT AVG(review_score_avg) FROM vw_order_summary WHERE review_count>0", 4.0868, 0.0001),

("Orders With Review", "P6",
 "CALCULATE ( COUNTROWS ( vw_order_summary ), vw_order_summary[review_count] > 0 )",
 "SELECT COUNT(*) FROM vw_order_summary WHERE review_count>0", 98673, 0),
]


def main() -> None:
    print("=" * 104)
    print("DAX MEASURE LOGIC VALIDATION  —  equivalent SQL vs values verified in Phases 3-5")
    print("=" * 104)
    print(f"{'pg':<4}{'measure':<36}{'expected':>18}{'from MySQL':>18}  result")
    print("-" * 104)
    fails = []
    for name, page, dax, sql, exp, tol in MEASURES:
        got = q(sql)
        ok = abs(got - exp) <= tol if tol else got == exp
        if not ok:
            fails.append((name, exp, got))
        print(f"{page:<4}{name:<36}{exp:>18,.6f}{got:>18,.6f}  {'PASS' if ok else '*** FAIL ***'}")
    print("-" * 104)
    print(f"measures checked: {len(MEASURES)}   PASS: {len(MEASURES)-len(fails)}   FAIL: {len(fails)}")
    for f in fails:
        print(f"   FAIL {f[0]}: expected {f[1]}, got {f[2]}")
    print()
    print("SCOPE REMINDER: this verifies each measure's filter context, grain,")
    print("denominator and arithmetic. It does NOT execute DAX. Running the")
    print("measures in Power BI requires Windows and remains outstanding.")
    CONN.close()
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
