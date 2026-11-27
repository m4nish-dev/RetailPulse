"""
RetailPulse - SQL reference values for the 90 dashboard measures.

Every value here is computed in SQL on the BASE tables (orders, order_items,
customers, order_reviews, products, sellers). It never reads the views, the
exported CSVs or a typed-in constant, so it is an independent answer to each
business question in each filter context.

scripts/validate_tableau_calcs.py evaluates its Tableau formula emulation over
the CSVs in the same contexts and compares the two.

History: these queries are the "expected" side of the earlier measure
validator (fix-Phase 4, 2026-11-20; extended 2026-11-27), kept unchanged when
the dashboard moved to Tableau. Only the formula side was replaced.

Read-only: called with the read-only app-account connection.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MONEY = 0.005                 # half a centavo
RATE = 1e-9
HALF4 = 0.5e-4 + 1e-9         # values stored to 4 decimals in the CSVs
STABLE = (pd.Period("2017-01", "M"), pd.Period("2018-08", "M"))

BASE_REV = ("SELECT SUM(oi.price) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id {j} "
            "WHERE o.revenue_eligible=1 {w}")
CUST_J = "JOIN customers c ON c.customer_id=o.customer_id"
YM = "DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m')"


def build(sql, sv) -> list[dict]:
    """Return one dict per reference check: id, measure, context, expected (None = blank), tol, note."""
    out: list[dict] = []

    def ref(mid, measure, context, expected, tol=0.0, note=""):
        e = None if expected is None or (isinstance(expected, float) and np.isnan(expected)) else float(expected)
        out.append({"id": mid, "measure": measure, "context": context, "expected": e, "tol": tol, "note": note})

    # ------------------------------------------------------------------ Executive
    ref("M01", "Total Revenue", "unfiltered", sv(BASE_REV.format(j="", w="")), MONEY)
    ref("M01", "Total Revenue", "month = 2017-11", sv(BASE_REV.format(j="", w=f"AND {YM}='2017-11'")), MONEY)
    ref("M01", "Total Revenue", "customer_state = SP", sv(BASE_REV.format(j=CUST_J, w="AND c.customer_state='SP'")), MONEY)
    ref("M02", "Total Orders", "unfiltered", sv("SELECT COUNT(*) FROM orders"))
    ref("M02", "Total Orders", "month = 2018-08",
        sv("SELECT COUNT(*) FROM orders WHERE DATE_FORMAT(order_purchase_timestamp,'%Y-%m')='2018-08'"))
    ref("M03", "Total Customers", "unfiltered (people, not customer_id)",
        sv("SELECT COUNT(DISTINCT c.customer_unique_id) FROM orders o JOIN customers c ON c.customer_id=o.customer_id"))
    ref("M03", "Total Customers", "month = 2017-11 (people active that month)",
        sv(f"SELECT COUNT(DISTINCT c.customer_unique_id) FROM orders o {CUST_J} WHERE {YM}='2017-11'"))
    items_orders = "(SELECT DISTINCT order_id FROM order_items)"
    ref("M04", "Orders With Items", "unfiltered",
        sv(f"SELECT COUNT(*) FROM orders o JOIN {items_orders} i ON i.order_id=o.order_id"))
    ref("M05", "AOV Denominator", "unfiltered",
        sv(f"SELECT COUNT(*) FROM orders o JOIN {items_orders} i ON i.order_id=o.order_id WHERE o.revenue_eligible=1"))
    ref("M05", "AOV Denominator", "month = 2018-01",
        sv(f"SELECT COUNT(*) FROM orders o JOIN {items_orders} i ON i.order_id=o.order_id WHERE o.revenue_eligible=1 "
           f"AND {YM}='2018-01'"))
    e_aov = ("SELECT SUM(oi.price)/(COUNT(DISTINCT o.order_id)*1e0) FROM orders o JOIN order_items oi "
             "ON oi.order_id=o.order_id WHERE o.revenue_eligible=1 {w}")
    ref("M06", "Average Order Value", "unfiltered", sv(e_aov.format(w="")), 1e-9)
    for yr in (2017, 2018):
        ref("M06", "Average Order Value", f"Jan-Aug {yr} (like-for-like)",
            sv(e_aov.format(w=f"AND YEAR(o.order_purchase_timestamp)={yr} AND MONTH(o.order_purchase_timestamp)<=8")), 1e-9)
    ref("M07", "Median Order Value", "unfiltered (computed, not a constant)",
        float(sql("""WITH r AS (SELECT o.order_id, SUM(oi.price) v FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
                                WHERE o.revenue_eligible=1 GROUP BY o.order_id),
                          k AS (SELECT v, ROW_NUMBER() OVER (ORDER BY v) rn, COUNT(*) OVER () n FROM r)
                     SELECT AVG(v) FROM k WHERE rn IN (FLOOR((n+1)/2), CEIL((n+1)/2))""").iloc[0, 0]), MONEY)
    ref("M08", "Total Freight", "unfiltered (eligible)",
        sv("SELECT SUM(oi.freight_value) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id "
           "WHERE o.revenue_eligible=1"), MONEY)

    monthly = sql(f"SELECT {YM} ym, SUM(oi.price) rev FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
                  "WHERE o.revenue_eligible = 1 GROUP BY ym")
    monthly = dict(zip(monthly.ym.map(lambda x: pd.Period(x, "M")), monthly.rev.astype(float)))
    in_stable = lambda p: STABLE[0] <= p <= STABLE[1]
    for m in ["2016-12", "2017-01", "2017-11", "2018-08"]:
        ref("M09", "Revenue PM", f"month = {m}", monthly.get(pd.Period(m, "M") - 1), MONEY)
    for m in ["2017-01", "2017-02", "2017-11", "2018-08", "2018-09"]:
        p = pd.Period(m, "M")
        v = (monthly[p] - monthly[p - 1]) / monthly[p - 1] if in_stable(p) and in_stable(p - 1) else None
        ref("M10", "Revenue MoM %", f"month = {m}", v, RATE)
    for m in ["2016-12", "2017-01", "2017-02", "2017-03", "2017-12", "2018-08", "2018-09"]:
        p = pd.Period(m, "M"); win = [p - 2, p - 1, p]
        v = sum(monthly.get(x, 0) for x in win) / 3 if all(in_stable(x) for x in win) else None
        ref("M11", "Revenue 3M Moving Avg", f"month = {m}", v, MONEY)
    for m, st in [("2017-06", False), ("2017-06", True), ("2018-08", True), ("2018-10", False)]:
        p = pd.Period(m, "M")
        vals = [v for k, v in monthly.items() if k <= p and (in_stable(k) or not st)]
        ref("M12", "Revenue Running Total", f"month = {m}, " + ("filter in_stable_window = 1" if st else "no filter"),
            sum(vals) if vals else None, MONEY)
    e_ja = BASE_REV.format(j=CUST_J, w="AND YEAR(o.order_purchase_timestamp)={y} AND MONTH(o.order_purchase_timestamp)<=8 {s}")
    for yr, mid, nm in [(2017, "M13", "Revenue 2017 Jan-Aug"), (2018, "M14", "Revenue 2018 Jan-Aug")]:
        ref(mid, nm, "unfiltered", sv(e_ja.format(y=yr, s="")), MONEY)
        ref(mid, nm, "dashboard date filter 2018-01..08 (YoY sheet excluded from it)", sv(e_ja.format(y=yr, s="")), MONEY,
            "requires the YoY sheet to be excluded from the date filters")
        ref(mid, nm, "customer_state = SP", sv(e_ja.format(y=yr, s="AND c.customer_state='SP'")), MONEY)
    yoy = lambda s="": (lambda a, b: (b - a) / a)(sv(e_ja.format(y=2017, s=s)), sv(e_ja.format(y=2018, s=s)))
    ref("M15", "YoY Growth Jan-Aug %", "unfiltered", yoy(), RATE)
    ref("M15", "YoY Growth Jan-Aug %", "customer_state = SP", yoy("AND c.customer_state='SP'"), RATE)

    # ------------------------------------------------------------------ Customers
    people = sv("SELECT COUNT(DISTINCT customer_unique_id) FROM customers")
    e_per = ("SELECT COUNT(*) FROM (SELECT c.customer_unique_id, COUNT(*) n FROM orders o "
             "JOIN customers c ON c.customer_id=o.customer_id GROUP BY c.customer_unique_id) t WHERE {w}")
    ref("M16", "Total People", "unfiltered", people)
    ref("M17", "Repeat Customers", "unfiltered", sv(e_per.format(w="n>=2")))
    ref("M18", "One-Time Customers", "unfiltered", sv(e_per.format(w="n=1")))
    ref("M19", "Repeat Purchase Rate", "unfiltered", sv(e_per.format(w="n>=2")) / people, RATE)
    ref("M20", "Avg Orders Per Customer", "unfiltered", sv("SELECT COUNT(*) FROM orders") / people, RATE)
    e_pstate = ("SELECT SUM(v) FROM (SELECT c.customer_unique_id, MIN(c.customer_state) st, "
                "SUM(CASE WHEN o.revenue_eligible=1 THEN i.r ELSE 0 END) v FROM orders o "
                "JOIN customers c ON c.customer_id=o.customer_id "
                "LEFT JOIN (SELECT order_id, SUM(price) r FROM order_items GROUP BY order_id) i ON i.order_id=o.order_id "
                "GROUP BY c.customer_unique_id) t {w}")
    ref("M21", "Historical Customer Value", "unfiltered", sv(e_pstate.format(w="")), MONEY)
    ref("M21", "Historical Customer Value", "customer_state = SP", sv(e_pstate.format(w="WHERE st='SP'")), MONEY)

    rfm = sql("""
    WITH mx AS (SELECT MAX(order_purchase_timestamp) m FROM orders),
    orev AS (SELECT order_id, SUM(price) r FROM order_items GROUP BY order_id),
    st AS (SELECT c.customer_unique_id u, MIN(c.customer_state) st FROM orders o
           JOIN customers c ON c.customer_id=o.customer_id GROUP BY c.customer_unique_id),
    e AS (SELECT c.customer_unique_id u, DATEDIFF((SELECT m FROM mx), MAX(o.order_purchase_timestamp)) rec,
                 COUNT(*) f, SUM(orev.r) mon
          FROM orders o JOIN customers c ON c.customer_id=o.customer_id JOIN orev ON orev.order_id=o.order_id
          WHERE o.revenue_eligible=1 GROUP BY c.customer_unique_id),
    k AS (SELECT e.*, COUNT(*) OVER () n, RANK() OVER (ORDER BY rec DESC) rr, RANK() OVER (ORDER BY mon) mr FROM e)
    SELECT k.u, st.st, k.f, k.mon, 1+FLOOR(5*(rr-1)/n) r, 1+FLOOR(5*(mr-1)/n) m FROM k JOIN st ON st.u=k.u""")
    rfm["fs"] = np.select([rfm.f >= 3, rfm.f == 2], [5, 3], 1)

    def seg(r, f, m):
        if r >= 4 and f >= 3 and m >= 4: return "Champions"
        if r >= 3 and f >= 3: return "Loyal Customers"
        if r >= 4 and f == 1 and m >= 3: return "Potential Loyalists"
        if r <= 2 and m >= 4: return "At Risk"
        if r <= 2: return "Lost"
        return "Needs Attention"

    rfm["seg"] = [seg(*t) for t in zip(rfm.r, rfm.fs, rfm.m)]
    ref("N01", "RFM Scored Customers", "unfiltered", float(len(rfm)))
    ref("M22", "Customers In Segment", "all scored", float(len(rfm)))
    for s in sorted(rfm.seg.unique()):
        ref("M22", "Customers In Segment", f"segment = {s}", float((rfm.seg == s).sum()))
        ref("M23", "Segment Revenue Share", f"segment = {s}", rfm.loc[rfm.seg == s, "mon"].sum() / rfm.mon.sum(), RATE)
        ref("N02", "Segment Customer Share", f"segment = {s}", (rfm.seg == s).mean(), RATE)
        ref("N03", "Segment Avg Historical Value", f"segment = {s}", rfm.loc[rfm.seg == s, "mon"].mean(), MONEY)
    sp = rfm[rfm.st == "SP"]
    ref("M23", "Segment Revenue Share", "segment = Potential Loyalists within customer_state = SP",
        sp.loc[sp.seg == "Potential Loyalists", "mon"].sum() / sp.mon.sum(), RATE)

    act = sql("""
    WITH fo AS (SELECT c.customer_unique_id u, MIN(o.order_purchase_timestamp) f FROM orders o
                JOIN customers c ON c.customer_id=o.customer_id GROUP BY c.customer_unique_id),
    m AS (SELECT u, DATE_FORMAT(f,'%Y-%m') coh FROM fo WHERE f >= '2017-01-01' AND f < '2018-09-01'),
    a AS (SELECT DISTINCT m.coh, m.u, DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m') am FROM m
          JOIN customers c ON c.customer_unique_id=m.u JOIN orders o ON o.customer_id=c.customer_id)
    SELECT coh, am, COUNT(*) n FROM a GROUP BY coh, am""")
    act["k"] = [(pd.Period(a, "M") - pd.Period(c, "M")).n for c, a in zip(act.coh, act.am)]
    size = act[act.k == 0].set_index("coh").n
    cell = act.set_index(["coh", "k"]).n

    def ret(coh=None, k=None):
        if k is None:
            return None
        cohorts = [coh] if coh else list(size.index)
        obs = [c for c in cohorts if pd.Period(c, "M") + k <= STABLE[1]]
        return sum(cell.get((c, k), 0) for c in obs) / sum(size[c] for c in obs) if obs else None

    for coh in ["2017-01", "2018-08"]:
        ref("N04", "Cohort Customers", f"cohort = {coh}", float(size[coh]))
    for coh, k, note in [("2017-01", 1, "observed cell"), ("2018-07", 1, "last observed cell of a late cohort"),
                         ("2018-07", 2, "UNOBSERVED cell -> blank, not 0"), ("2018-08", 1, "UNOBSERVED (right-censored)"),
                         (None, 0, "offset 0 across cohorts = 100%"),
                         (None, 1, "offset 1 across cohorts: denominator = observed cohorts only"),
                         (None, 19, "offset 19: only 2017-01 observable"), (None, None, "grand total -> blank")]:
        ref("N05", "Cohort Retention %", f"cohort={coh or 'all'}, offset={k if k is not None else 'all'} ({note})",
            ret(coh, k), RATE)
    for coh, k in [("2017-01", 1), ("2018-07", 2), ("2017-01", 0)]:
        v = None if k == 0 or pd.Period(coh, "M") + k > STABLE[1] else float(cell.get((coh, k), 0))
        ref("N06", "Returning Customers", f"cohort={coh}, offset={k}", v)

    # ------------------------------------------------------------------ Products and categories
    cat = sql("""SELECT p.product_category_name_english cat, SUM(oi.price) rev, COUNT(*) items,
                        SUM(oi.freight_value) fr, COUNT(DISTINCT oi.product_id) prods
                 FROM order_items oi JOIN orders o ON o.order_id=oi.order_id JOIN products p ON p.product_id=oi.product_id
                 WHERE o.revenue_eligible=1 GROUP BY cat""").set_index("cat")
    ref("M24", "Category Revenue", "unfiltered", float(cat.rev.sum()), MONEY)
    ref("M24", "Category Revenue", "category = health_beauty", float(cat.rev["health_beauty"]), MONEY)
    ref("M24", "Category Revenue", "order_month = 2018-01", sv(BASE_REV.format(j="", w=f"AND {YM}='2018-01'")), MONEY)
    ref("M25", "Category Items Sold", "unfiltered", float(cat["items"].sum()))
    ref("M25", "Category Items Sold", "category = health_beauty", float(cat["items"]["health_beauty"]))
    ref("M26", "Distinct Categories", "unfiltered", float(len(cat)))
    for c in ["health_beauty", "watches_gifts", "security_and_services"]:
        ref("M27", "Category Revenue Share", f"category = {c}", float(cat.rev[c] / cat.rev.sum()), RATE)
    ref("M28", "Category Rank", "every category (74 checks in one)", float(len(cat)), 0,
        "count of categories whose rank equals the SQL dense rank")
    ref("N07", "Top Category Revenue", "unfiltered", float(cat.rev.max()), MONEY)
    n_prod = sv("SELECT COUNT(DISTINCT oi.product_id) FROM order_items oi JOIN orders o ON o.order_id=oi.order_id "
                "WHERE o.revenue_eligible=1")
    for c in [None, "health_beauty"]:
        lab = f"category = {c}" if c else "unfiltered"
        r = float(cat.rev[c] if c else cat.rev.sum()); i = float(cat["items"][c] if c else cat["items"].sum())
        fr = float(cat.fr[c] if c else cat.fr.sum())
        ref("N08", "Product Revenue", lab, r, MONEY)
        ref("N09", "Product Units Sold", lab, i)
        ref("N10", "Products Sold", lab, float(cat.prods[c]) if c else n_prod)
        ref("N11", "Product Avg Item Price", lab, r / i, RATE)
        ref("N12", "Product Avg Freight Per Item", lab, fr / i, RATE)

    sc = sql("""WITH t AS (SELECT DISTINCT oi.seller_id, p.product_category_name_english cat, oi.order_id
                           FROM order_items oi JOIN orders o ON o.order_id=oi.order_id JOIN products p ON p.product_id=oi.product_id
                           WHERE o.revenue_eligible=1),
                     ns AS (SELECT order_id, COUNT(DISTINCT seller_id) n FROM order_items GROUP BY order_id)
                SELECT t.cat, SUM(o.delivery_measurable) dm, SUM(CASE WHEN o.delivery_measurable=1 THEN o.is_late ELSE 0 END) late,
                       SUM(CASE WHEN ns.n=1 AND o.order_delivered_carrier_date>=o.order_approved_at
                                 AND o.order_approved_at>=o.order_purchase_timestamp
                                 AND o.order_delivered_customer_date>=o.order_delivered_carrier_date
                            THEN TIMESTAMPDIFF(SECOND,o.order_approved_at,o.order_delivered_carrier_date) END) disp_s,
                       SUM(CASE WHEN ns.n=1 AND o.order_delivered_carrier_date>=o.order_approved_at
                                 AND o.order_approved_at>=o.order_purchase_timestamp
                                 AND o.order_delivered_customer_date>=o.order_delivered_carrier_date THEN 1 ELSE 0 END) disp_n
                FROM t JOIN orders o ON o.order_id=t.order_id JOIN ns ON ns.order_id=t.order_id GROUP BY t.cat""").set_index("cat")
    top = sql("SELECT oi.seller_id, SUM(oi.price) r FROM order_items oi JOIN orders o ON o.order_id=oi.order_id "
              "WHERE o.revenue_eligible=1 GROUP BY oi.seller_id ORDER BY r DESC LIMIT 1").iloc[0]
    ref("N13", "Seller Category Revenue", "category = health_beauty", float(cat.rev["health_beauty"]), MONEY)
    ref("N13", "Seller Category Revenue", "seller = largest seller (all its categories)", float(top.r), MONEY)
    ref("N14", "Seller Category Items", "unfiltered", float(cat["items"].sum()))
    ref("N15", "Seller Category Late Rate", "category = health_beauty",
        float(sc.late["health_beauty"] / sc.dm["health_beauty"]), RATE)
    ref("N16", "Seller Category Dispatch Days", "category = health_beauty (single-seller, valid timing)",
        float(sc.disp_s["health_beauty"] / sc.disp_n["health_beauty"] / 86400), 1e-6)

    cum = sql("""WITH r AS (SELECT p.product_category_name_english cat, SUM(oi.price) rev
                            FROM order_items oi JOIN orders o ON o.order_id=oi.order_id
                            JOIN products p ON p.product_id=oi.product_id WHERE o.revenue_eligible=1 GROUP BY cat)
                 SELECT cat, rev, SUM(rev) OVER (ORDER BY rev DESC RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) * 1e0
                                  / SUM(rev) OVER () cum FROM r""").set_index("cat")
    for c in ["health_beauty", cum.sort_values("rev", ascending=False).index[9]]:
        ref("N36", "Category Cumulative Share", f"category = {c}", float(cum.cum[c]), RATE)
    ref("N36", "Category Cumulative Share", "all 74 categories (74 in one)", float(len(cum)), 0,
        "count of categories whose cumulative share equals SQL")
    ref("N36", "Category Cumulative Share", "categories needed to reach 80%", float((cum.cum < 0.8).sum() + 1))
    grow = sql(f"""SELECT p.product_category_name_english cat,
                     SUM(CASE WHEN {YM} BETWEEN '2017-01' AND '2017-03' THEN oi.price ELSE 0 END) r1,
                     SUM(CASE WHEN {YM} BETWEEN '2018-06' AND '2018-08' THEN oi.price ELSE 0 END) r2,
                     SUM({YM} BETWEEN '2017-01' AND '2017-03') i1, SUM({YM} BETWEEN '2018-06' AND '2018-08') i2
                   FROM order_items oi JOIN orders o ON o.order_id=oi.order_id JOIN products p ON p.product_id=oi.product_id
                   WHERE o.revenue_eligible=1 GROUP BY cat""").set_index("cat")
    grow["g"] = np.where((grow.i1 >= 50) & (grow.i2 >= 50), (grow.r2 - grow.r1) / grow.r1.replace(0, np.nan), np.nan)
    ref("N37", "Category Revenue 2017 Q1", "category = housewares", float(grow.r1["housewares"]), MONEY)
    ref("N37", "Category Revenue 2017 Q1", "unfiltered", float(grow.r1.sum()), MONEY)
    ref("N38", "Category Revenue Jun-Aug 2018", "category = housewares", float(grow.r2["housewares"]), MONEY)
    ref("N38", "Category Revenue Jun-Aug 2018", "unfiltered", float(grow.r2.sum()), MONEY)
    for c in ["housewares", "health_beauty"]:
        ref("N39", "Category Growth Q1 2017 to Jun-Aug 2018", f"category = {c}", grow.g[c], RATE)
    small = grow[(grow.i1 < 50) | (grow.i2 < 50)].index[0]
    ref("N39", "Category Growth Q1 2017 to Jun-Aug 2018", f"category = {small} (under 50 items -> blank)", None)
    ref("N39", "Category Growth Q1 2017 to Jun-Aug 2018", "categories meeting the floor that grew", float((grow.g > 0).sum()))
    ref("N39", "Category Growth Q1 2017 to Jun-Aug 2018", "every category matches (74 in one)", float(len(grow)), 0,
        "count of categories whose growth equals SQL")

    # ------------------------------------------------------------------ Sellers
    pairs = sql("""WITH p AS (SELECT DISTINCT oi.seller_id, oi.order_id FROM order_items oi
                              JOIN orders o ON o.order_id=oi.order_id WHERE o.revenue_eligible=1),
                        sc AS (SELECT order_id, SUM(review_score)/(COUNT(*)*1e0) s FROM order_reviews GROUP BY order_id)
                   SELECT p.seller_id, s.seller_state, o.delivery_measurable dm, o.is_late late, o.delivery_days dd, sc.s
                   FROM p JOIN orders o ON o.order_id=p.order_id JOIN sellers s ON s.seller_id=p.seller_id
                   LEFT JOIN sc ON sc.order_id=p.order_id""")
    sel_rev = sql("SELECT s.seller_state st, SUM(oi.price) r FROM order_items oi JOIN orders o ON o.order_id=oi.order_id "
                  "JOIN sellers s ON s.seller_id=oi.seller_id WHERE o.revenue_eligible=1 GROUP BY st").set_index("st").r

    def e_seller(df, what):
        m = df[df.dm == 1]
        return {"late": m.late.sum() / len(m), "days": m.dd.sum() / len(m), "rating": df.s.mean(),
                "orders": float(len(df)), "sellers": float(df.seller_id.nunique())}[what]

    for lab, st, sid in [("unfiltered", None, None), ("seller_state = SP", "SP", None),
                         ("seller = largest seller", None, top.seller_id)]:
        sub = pairs
        if st: sub = sub[sub.seller_state == st]
        if sid: sub = sub[sub.seller_id == sid]
        if sid is None:
            ref("M29", "Seller Revenue", lab, float(sel_rev[st] if st else sel_rev.sum()), MONEY)
            ref("M30", "Sellers With Revenue", lab, e_seller(sub, "sellers"))
            ref("M31", "Seller Orders", lab + " (seller-order pairs)", e_seller(sub, "orders"))
        ref("M32", "Seller Avg Delivery Days", lab, e_seller(sub, "days"), 1e-9)
        ref("M33", "Seller Late Rate", lab, e_seller(sub, "late"), RATE)
        ref("M35", "Seller Inherited Order Rating", lab, e_seller(sub, "rating"), 1e-6)
    ref("M34", "Largest Seller Share", "unfiltered", float(top.r) / float(sel_rev.sum()), RATE)
    cum_sel = sql("""WITH r AS (SELECT oi.seller_id, SUM(oi.price) rev FROM order_items oi JOIN orders o ON o.order_id=oi.order_id
                                WHERE o.revenue_eligible=1 GROUP BY oi.seller_id)
                     SELECT seller_id, rev, SUM(rev) OVER (ORDER BY rev DESC RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) * 1e0
                                            / SUM(rev) OVER () cum FROM r ORDER BY rev DESC""")
    for rank in (1, 305, 306):
        ref("N40", "Seller Cumulative Share", f"seller ranked {rank} by revenue", float(cum_sel.cum.iloc[rank - 1]), RATE)
    ref("N40", "Seller Cumulative Share", "every seller (3,053 in one)", float(cum_sel.rev.round(2).nunique()), 0,
        "DOCUMENTED DIFFERENCE: the definition gives tied sellers one shared value (all sellers with revenue >= "
        "this one); RUNNING_SUM matches it at the last seller of each tie group, so expected = number of distinct "
        "revenue values")

    # ------------------------------------------------------------------ Operations
    e_del = "SELECT {s} FROM orders o JOIN customers c ON c.customer_id=o.customer_id WHERE 1=1 {w}"
    ref("M36", "Delivered Orders", "unfiltered", sv(e_del.format(s="COUNT(*)", w="AND o.order_status='delivered'")))
    ref("M37", "Delivery Denominator", "unfiltered",
        sv(e_del.format(s="COUNT(*)", w="AND o.order_delivered_customer_date IS NOT NULL")))
    ref("M38", "Late Orders", "unfiltered",
        sv(e_del.format(s="SUM(o.order_delivered_customer_date > o.order_estimated_delivery_date)",
                        w="AND o.order_delivered_customer_date IS NOT NULL")))
    e_late = "SUM(o.order_delivered_customer_date > o.order_estimated_delivery_date)/(COUNT(*)*1e0)"
    for lab, w in [("unfiltered", ""), ("month = 2018-03", f"AND {YM}='2018-03'"),
                   ("order_status = unavailable (no deliveries -> blank)", "AND o.order_status='unavailable'")]:
        v = sv(e_del.format(s=e_late, w="AND o.order_delivered_customer_date IS NOT NULL " + w))
        ref("M39", "Late Delivery Rate", lab, v, RATE)
        ref("M40", "On-Time Delivery Rate", lab, None if v is None else 1 - v, RATE)
    e_days = "SUM(TIMESTAMPDIFF(SECOND,o.order_purchase_timestamp,o.order_delivered_customer_date))/86400e0/COUNT(*)"
    e_delay = "SUM(TIMESTAMPDIFF(SECOND,o.order_estimated_delivery_date,o.order_delivered_customer_date))/86400e0/COUNT(*)"
    for lab, w in [("unfiltered", ""), ("customer_state = SP", "AND c.customer_state='SP'")]:
        ref("M41", "Avg Delivery Days", lab,
            sv(e_del.format(s=e_days, w="AND o.order_delivered_customer_date IS NOT NULL " + w)), HALF4)
        ref("M42", "Avg Delay Days", lab,
            sv(e_del.format(s=e_delay, w="AND o.order_delivered_customer_date IS NOT NULL " + w)), HALF4)
    e_prom = ("SELECT SUM(TIMESTAMPDIFF(SECOND,o.order_purchase_timestamp,o.order_estimated_delivery_date))/86400e0/COUNT(*) "
              "FROM orders o JOIN customers c ON c.customer_id=o.customer_id WHERE o.order_delivered_customer_date IS NOT NULL {w}")
    for lab, w in [("unfiltered", ""), ("month = 2017-01", f"AND {YM}='2017-01'"), ("month = 2018-08", f"AND {YM}='2018-08'"),
                   ("customer_state = SP", "AND c.customer_state='SP'")]:
        ref("N41", "Avg Promised Days", lab, sv(e_prom.format(w=w)), 2 * HALF4)
    ref("M43", "Cancelled Orders", "unfiltered", sv("SELECT COUNT(*) FROM orders WHERE order_status='canceled'"))
    ref("M44", "Cancellation Rate", "unfiltered", sv("SELECT SUM(order_status='canceled')/(COUNT(*)*1e0) FROM orders"), RATE)
    e_stage = """SELECT COUNT(*) n,
      SUM(TIMESTAMPDIFF(SECOND,o.order_purchase_timestamp,o.order_approved_at)) s1,
      SUM(TIMESTAMPDIFF(SECOND,o.order_approved_at,o.order_delivered_carrier_date)) s2,
      SUM(TIMESTAMPDIFF(SECOND,o.order_delivered_carrier_date,o.order_delivered_customer_date)) s3,
      SUM(TIMESTAMPDIFF(SECOND,o.order_purchase_timestamp,o.order_delivered_customer_date)) t
    FROM orders o JOIN customers c ON c.customer_id=o.customer_id
    WHERE o.order_approved_at IS NOT NULL AND o.order_delivered_carrier_date IS NOT NULL
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_purchase_timestamp <= o.order_approved_at AND o.order_approved_at <= o.order_delivered_carrier_date
      AND o.order_delivered_carrier_date <= o.order_delivered_customer_date {w}"""
    for lab, w in [("unfiltered", ""), ("customer_state = SP", "AND c.customer_state='SP'"),
                   ("month = 2018-01", f"AND {YM}='2018-01'")]:
        x = sql(e_stage.format(w=w)).iloc[0].astype(float)
        ref("N17", "Stage Orders", lab, x.n)
        for mid, nm, k in [("N18", "Purchase To Approval Days", "s1"), ("N19", "Approval To Carrier Days", "s2"),
                           ("N20", "Carrier To Customer Days", "s3"), ("N21", "Stage Total Days", "t")]:
            ref(mid, nm, lab, x[k] / x.n / 86400, 1e-9)
        for mid, nm, k in [("N22", "Last Mile Share", "s3"), ("N23", "Dispatch Stage Share", "s2"),
                           ("N24", "Approval Stage Share", "s1")]:
            ref(mid, nm, lab, x[k] / x.t, RATE)

    # ------------------------------------------------------------------ Satisfaction
    e_r = "SELECT {s} FROM order_reviews r JOIN orders o ON o.order_id=r.order_id WHERE 1=1 {w}"
    ref("M45", "Total Reviews", "unfiltered", sv(e_r.format(s="COUNT(*)", w="")))
    ref("M45", "Total Reviews", "customer_state = SP (via vw_order_summary)",
        sv("SELECT COUNT(*) FROM order_reviews r JOIN orders o ON o.order_id=r.order_id "
           "JOIN customers c ON c.customer_id=o.customer_id WHERE c.customer_state='SP'"))
    ref("M46", "Avg Review Score", "unfiltered (review grain)", sv(e_r.format(s="SUM(r.review_score)/(COUNT(*)*1e0)", w="")), RATE)
    ref("M47", "One-Star Rate", "unfiltered", sv(e_r.format(s="SUM(r.review_score=1)/(COUNT(*)*1e0)", w="")), RATE)
    ref("M48", "Five-Star Rate", "unfiltered", sv(e_r.format(s="SUM(r.review_score=5)/(COUNT(*)*1e0)", w="")), RATE)
    e_og = ("SELECT AVG(s) FROM (SELECT r.order_id, SUM(r.review_score)/(COUNT(*)*1e0) s FROM order_reviews r "
            "JOIN orders o ON o.order_id=r.order_id WHERE 1=1 {w} GROUP BY r.order_id) t")
    ref("M49", "Avg Order Rating", "unfiltered (order grain)", sv(e_og.format(w="")), HALF4)
    ref("N25", "Pre-Delivery Reviews", "unfiltered",
        sv(e_r.format(s="SUM(r.review_answer_timestamp < o.order_delivered_customer_date)", w="")))
    ref("N26", "Pre-Delivery Review Share", "unfiltered (of reviews on delivered orders)",
        sv(e_r.format(s="SUM(r.review_answer_timestamp < o.order_delivered_customer_date)/(COUNT(*)*1e0)",
                      w="AND o.order_delivered_customer_date IS NOT NULL")), RATE)
    after = "AND r.review_answer_timestamp >= o.order_delivered_customer_date"
    ref("N27", "Avg Review Score After Arrival", "unfiltered (review grain)",
        sv(e_r.format(s="SUM(r.review_score)/(COUNT(*)*1e0)", w=after)), RATE)
    ref("N28", "One-Star Rate After Arrival", "unfiltered", sv(e_r.format(s="SUM(r.review_score=1)/(COUNT(*)*1e0)", w=after)), RATE)
    buckets = {"1-7 days late": "o.delay_days > 0 AND o.delay_days <= 7", "8-15 days late": "o.delay_days > 7 AND o.delay_days <= 15",
               "on time": "o.delay_days > -7 AND o.delay_days <= 0", "15+ days late": "o.delay_days > 15"}
    for b, cond in buckets.items():
        ref("N35", "Avg Order Rating (Review Table)", f"delivery_bucket = {b} (all reviews)",
            sv(e_og.format(w="AND o.delivery_measurable=1 AND " + cond)), 1e-9)
        ref("N34", "Avg Order Rating After Arrival", f"delivery_bucket = {b}",
            sv(e_og.format(w=f"AND o.delivery_measurable=1 {after} AND " + cond)), 1e-9)
    ref("N35", "Avg Order Rating (Review Table)", "unfiltered (must equal M49 at full precision)", sv(e_og.format(w="")), 1e-9)
    cs = sql("""WITH oc AS (SELECT DISTINCT oi.order_id, p.product_category_name_english cat
                            FROM order_items oi JOIN products p ON p.product_id=oi.product_id)
                SELECT oc.cat, COUNT(*) n, SUM(r.review_score)/(COUNT(*)*1e0) avg_s, SUM(r.review_score=1)/(COUNT(*)*1e0) one,
                       SUM(r.review_before_delivery=1)/(COUNT(*)*1e0) pre,
                       SUM(CASE WHEN r.review_before_delivery=0 THEN r.review_score END)/(SUM(r.review_before_delivery=0)*1e0) aft
                FROM oc JOIN order_reviews r ON r.order_id=oc.order_id GROUP BY oc.cat""").set_index("cat")
    for c in ["health_beauty", "office_furniture"]:
        ref("N29", "Category Review Count", f"category = {c}", float(cs.n[c]))
        ref("N30", "Category Avg Review Score", f"category = {c}", float(cs.avg_s[c]), HALF4)
        ref("N31", "Category One-Star Rate", f"category = {c}", float(cs.one[c]), HALF4 / 100)
        ref("N32", "Category Avg Score After Arrival", f"category = {c}", float(cs.aft[c]), HALF4)
        ref("N33", "Category Pre-Delivery Review Share", f"category = {c}", float(cs.pre[c]), HALF4 / 100)
    ref("N29", "Category Review Count", "no single category (total row) -> blank, not a double-counted sum", None)
    ref("N30", "Category Avg Review Score", "no single category (total row) -> blank", None)
    return out
