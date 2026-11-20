"""
RetailPulse - validate the LOGIC of every Power BI DAX measure (rewritten in fix-Phase 4).

TWO INDEPENDENT PATHS PER CHECK
-------------------------------
  MODEL     The measure's DAX logic, emulated in pandas over the exact CSVs
            Power BI imports (powerbi/data/*.csv and powerbi/data/analytical/*.csv),
            including its filter behaviour: which filters it keeps, which it
            removes, where it returns BLANK.
  EXPECTED  The same business question answered in SQL against the BASE tables
            only (orders, order_items, customers, order_reviews, products,
            sellers) - never the views, never the exported sources, never a
            typed-in constant.

Each measure is checked in one or more FILTER CONTEXTS (unfiltered, a month, a
state, a category, a seller, a segment, a cohort cell ...). A third group of
checks, BUG REPRODUCTIONS, evaluates the superseded formulas and passes only if
they are shown to give the wrong answer - evidence that each fix was needed.

WHAT THIS CANNOT PROVE
----------------------
  * DAX syntax, or that Power BI's engine evaluates the formulas as emulated
  * relationship behaviour in the real model (cross-filter direction,
    cardinality), slicer interaction, visual-level totals
  * formatting
A PASS means: "typed as written in powerbi/dax_measures.md, on the model in
powerbi/data_model.md, this measure asks the right question of the right rows
and gets the number the base data supports." Running the measures in Power BI
needs Windows and remains outstanding.

Writes powerbi/dax_validation_results.csv (one row per check). Exit 1 on any failure.
Read-only: MySQL session is READ ONLY; nothing in the database or data changes.

Usage:  ./venv/bin/python scripts/validate_dax_logic.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

try:
    import mysql.connector
except ImportError:
    sys.exit("pip install mysql-connector-python")

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "powerbi" / "data"
A = D / "analytical"
STABLE = (pd.Period("2017-01", "M"), pd.Period("2018-08", "M"))

try:
    CONN = mysql.connector.connect(host="127.0.0.1", user="root", database="retailpulse")
except Exception as e:                                      # noqa: BLE001
    sys.exit(f"Cannot reach MySQL ({type(e).__name__}). brew services start mysql@8.4")
_c = CONN.cursor(); _c.execute("SET SESSION TRANSACTION READ ONLY"); _c.close()


def sql(query):
    """Run SQL on the base tables; returns a DataFrame with float-converted numerics."""
    cur = CONN.cursor(); cur.execute(query)
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(cur.fetchall(), columns=cols, dtype=object); cur.close()
    for c in df.columns:
        try:
            df[c] = pd.to_numeric(df[c])
        except (ValueError, TypeError):
            pass
    return df


def sv(query):
    """Scalar SQL value; None for NULL (= DAX BLANK)."""
    v = sql(query).iloc[0, 0]
    return None if pd.isna(v) else float(v)


# ---- DAX primitives ---------------------------------------------------------
def dsum(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    return None if s.empty else float(s.sum())


def dcount(df):
    return None if len(df) == 0 else float(len(df))


def divide(a, b):
    return None if a is None or b is None or b == 0 else a / b


def davg(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    return None if s.empty else float(s.mean())


# ---- model tables (exactly what Power BI imports) ---------------------------
O = pd.read_csv(D / "vw_order_summary.csv", parse_dates=["order_date"], low_memory=False)
C = pd.read_csv(D / "vw_customer_summary.csv", low_memory=False)
CAT = pd.read_csv(D / "vw_category_performance.csv")
SEL = pd.read_csv(D / "vw_seller_performance.csv")
REV = pd.read_csv(D / "vw_review_summary.csv", low_memory=False)
DIM = pd.read_csv(D / "dim_date.csv", parse_dates=["Date"])
DIM["InStableWindow"] = DIM.InStableWindow.astype(str).eq("True")
RFM = pd.read_csv(A / "rfm_customer_segments.csv")
COH = pd.read_csv(A / "cohort_retention.csv")
PROD = pd.read_csv(A / "product_performance.csv")
SC = pd.read_csv(A / "seller_category_performance.csv")
DSO = pd.read_csv(A / "delivery_stage_orders.csv")
CS = pd.read_csv(A / "category_satisfaction.csv")
SK = pd.read_csv(A / "seller_scorecard.csv")
DC = pd.read_csv(A / "dim_category.csv")

RESULTS = []


def check(mid, measure, context, model, expected, tol=0.0, kind="measure"):
    """Compare model vs expected. Both BLANK -> pass."""
    try:
        mv, ev = model(), expected()
        if mv is None or ev is None:
            ok = mv is None and ev is None
        else:
            ok = abs(mv - ev) <= tol + 1e-12
        err = ""
    except Exception as ex:                                  # noqa: BLE001
        mv = ev = None; ok = False; err = f"{type(ex).__name__}: {ex}"
    RESULTS.append({"id": mid, "measure": measure, "context": context, "kind": kind,
                    "model": mv, "expected": ev, "pass": ok, "error": err})


def bug(mid, measure, context, demonstrated, detail):
    """A superseded formula, evaluated: passes only if it is shown to be wrong."""
    try:
        ok = bool(demonstrated())
    except Exception as ex:                                  # noqa: BLE001
        ok, detail = False, f"{type(ex).__name__}: {ex}"
    RESULTS.append({"id": mid, "measure": measure, "context": context, "kind": "bug reproduction",
                    "model": None, "expected": None, "pass": ok, "error": "" if ok else detail,
                    "detail": detail})


NOTES = []


def semantic_note(mid, measure, text):
    """A DAX filter-semantics finding that cannot be executed on macOS: reported, never counted as a PASS."""
    NOTES.append((mid, measure, text))


MONEY = 0.005
RATE = 1e-9
HALF4 = 0.5e-4 + 1e-9

# =============================================================================
# Model helpers
# =============================================================================
def o_ctx(month=None, state=None, status=None):
    o = O
    if month is not None:
        dates = DIM.Date[DIM.YearMonth == month]
        o = o[o.order_date.isin(dates)]
    if state is not None:
        o = o[o.customer_state == state]
    if status is not None:
        o = o[o.order_status == status]
    return o


def total_revenue(o):
    return dsum(o.loc[o.revenue_eligible == 1, "order_revenue"])


def rev_dates(dates, o=None):
    o = O if o is None else o
    return total_revenue(o[o.order_date.isin(dates)])


def cur_idx(month):
    return int(DIM.loc[DIM.YearMonth == month, "MonthIndex"].max())


def stable_months_between(lo, hi):
    w = DIM[(DIM.MonthIndex >= lo) & (DIM.MonthIndex <= hi) & DIM.InStableWindow]
    return w.MonthIndex.nunique()


def m_revenue_pm(month):
    i = cur_idx(month)
    return rev_dates(DIM.Date[DIM.MonthIndex == i - 1])


def m_mom(month):
    i = cur_idx(month)
    if stable_months_between(i - 1, i) != 2:
        return None
    prev = m_revenue_pm(month)
    cur = total_revenue(o_ctx(month=month))
    return divide((cur or 0) - (prev or 0), prev)


def m_ma3(month):
    i = cur_idx(month)
    if stable_months_between(i - 2, i) != 3:
        return None
    return divide(rev_dates(DIM.Date[(DIM.MonthIndex > i - 3) & (DIM.MonthIndex <= i)]), 3)


def m_running(month, stable_slicer):
    last = DIM.Date[DIM.YearMonth == month].max()
    sel = DIM[DIM.InStableWindow] if stable_slicer else DIM
    return rev_dates(sel.Date[sel.Date <= last])


def m_janaug(year, state=None):
    dates = DIM.Date[(DIM.Year == year) & (DIM.MonthNo <= 8)]          # REMOVEFILTERS(dim_date)
    return rev_dates(dates, o_ctx(state=state))


# ---- expected helpers (base tables) -----------------------------------------
MONTHLY = sql("""SELECT DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m') ym, SUM(oi.price) rev
                 FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
                 WHERE o.revenue_eligible = 1 GROUP BY ym""")
MONTHLY = dict(zip(MONTHLY.ym.map(lambda x: pd.Period(x, "M")), MONTHLY.rev.astype(float)))


def in_stable(p):
    return STABLE[0] <= p <= STABLE[1]


def e_pm(month):
    return MONTHLY.get(pd.Period(month, "M") - 1)


def e_mom(month):
    p = pd.Period(month, "M")
    if not (in_stable(p) and in_stable(p - 1)):
        return None
    return (MONTHLY[p] - MONTHLY[p - 1]) / MONTHLY[p - 1]


def e_ma3(month):
    p = pd.Period(month, "M")
    win = [p - 2, p - 1, p]
    if not all(in_stable(x) for x in win):
        return None
    return sum(MONTHLY.get(x, 0) for x in win) / 3


def e_running(month, stable):
    p = pd.Period(month, "M")
    vals = [v for k, v in MONTHLY.items() if k <= p and (in_stable(k) or not stable)]
    return sum(vals) if vals else None


BASE_REV = "SELECT SUM(oi.price) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id {j} WHERE o.revenue_eligible=1 {w}"
CUST_J = "JOIN customers c ON c.customer_id=o.customer_id"

# =============================================================================
# PAGE 1 — Executive overview (M01-M15)
# =============================================================================
check("M01", "Total Revenue", "unfiltered", lambda: total_revenue(O),
      lambda: sv(BASE_REV.format(j="", w="")), MONEY)
check("M01", "Total Revenue", "month = 2017-11", lambda: total_revenue(o_ctx(month="2017-11")),
      lambda: sv(BASE_REV.format(j="", w="AND DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m')='2017-11'")), MONEY)
check("M01", "Total Revenue", "customer_state = SP", lambda: total_revenue(o_ctx(state="SP")),
      lambda: sv(BASE_REV.format(j=CUST_J, w="AND c.customer_state='SP'")), MONEY)
check("M02", "Total Orders", "unfiltered", lambda: dcount(O), lambda: sv("SELECT COUNT(*) FROM orders"))
check("M02", "Total Orders", "month = 2018-08", lambda: dcount(o_ctx(month="2018-08")),
      lambda: sv("SELECT COUNT(*) FROM orders WHERE DATE_FORMAT(order_purchase_timestamp,'%Y-%m')='2018-08'"))
check("M03", "Total Customers", "unfiltered (people, not customer_id)",
      lambda: float(O.customer_unique_id.nunique()),
      lambda: sv("SELECT COUNT(DISTINCT c.customer_unique_id) FROM orders o JOIN customers c ON c.customer_id=o.customer_id"))
check("M03", "Total Customers", "month = 2017-11 (people active that month)",
      lambda: float(o_ctx(month="2017-11").customer_unique_id.nunique()),
      lambda: sv("SELECT COUNT(DISTINCT c.customer_unique_id) FROM orders o JOIN customers c ON c.customer_id=o.customer_id "
                 "WHERE DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m')='2017-11'"))
ITEMS_ORDERS = "(SELECT DISTINCT order_id FROM order_items)"
check("M04", "Orders With Items", "unfiltered", lambda: dcount(O[O.item_count > 0]),
      lambda: sv(f"SELECT COUNT(*) FROM orders o JOIN {ITEMS_ORDERS} i ON i.order_id=o.order_id"))
aov_den = lambda o: dcount(o[(o.revenue_eligible == 1) & (o.item_count > 0)])
check("M05", "AOV Denominator", "unfiltered", lambda: aov_den(O),
      lambda: sv(f"SELECT COUNT(*) FROM orders o JOIN {ITEMS_ORDERS} i ON i.order_id=o.order_id WHERE o.revenue_eligible=1"))
check("M05", "AOV Denominator", "month = 2018-01", lambda: aov_den(o_ctx(month="2018-01")),
      lambda: sv(f"SELECT COUNT(*) FROM orders o JOIN {ITEMS_ORDERS} i ON i.order_id=o.order_id WHERE o.revenue_eligible=1 "
                 "AND DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m')='2018-01'"))
E_AOV = ("SELECT SUM(oi.price)/(COUNT(DISTINCT o.order_id)*1e0) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id "
         "WHERE o.revenue_eligible=1 {w}")
check("M06", "Average Order Value", "unfiltered", lambda: divide(total_revenue(O), aov_den(O)),
      lambda: sv(E_AOV.format(w="")), 1e-9)
for yr in (2017, 2018):
    check("M06", "Average Order Value", f"Jan-Aug {yr} (like-for-like)",
          lambda yr=yr: divide(m_janaug(yr), aov_den(O[O.order_date.isin(DIM.Date[(DIM.Year == yr) & (DIM.MonthNo <= 8)])])),
          lambda yr=yr: sv(E_AOV.format(w=f"AND YEAR(o.order_purchase_timestamp)={yr} AND MONTH(o.order_purchase_timestamp)<=8")), 1e-9)
check("M07", "Median Order Value", "unfiltered (computed, not a constant)",
      lambda: float(O.loc[(O.revenue_eligible == 1) & (O.item_count > 0), "order_revenue"].median()),
      lambda: float(sql("""WITH r AS (SELECT o.order_id, SUM(oi.price) v FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
                                     WHERE o.revenue_eligible=1 GROUP BY o.order_id),
                               k AS (SELECT v, ROW_NUMBER() OVER (ORDER BY v) rn, COUNT(*) OVER () n FROM r)
                          SELECT AVG(v) FROM k WHERE rn IN (FLOOR((n+1)/2), CEIL((n+1)/2))""").iloc[0, 0]), MONEY)
check("M08", "Total Freight", "unfiltered (eligible)",
      lambda: dsum(O.loc[O.revenue_eligible == 1, "order_freight"]),
      lambda: sv("SELECT SUM(oi.freight_value) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id WHERE o.revenue_eligible=1"), MONEY)

# ---- time intelligence, tested at the month boundaries ----------------------
for m in ["2016-12", "2017-01", "2017-11", "2018-08"]:
    check("M09", "Revenue PM", f"month = {m}", lambda m=m: m_revenue_pm(m), lambda m=m: e_pm(m), MONEY)
for m in ["2017-01", "2017-02", "2017-11", "2018-08", "2018-09"]:
    check("M10", "Revenue MoM %", f"month = {m}", lambda m=m: m_mom(m), lambda m=m: e_mom(m), RATE)
for m in ["2016-12", "2017-01", "2017-02", "2017-03", "2017-12", "2018-08", "2018-09"]:
    check("M11", "Revenue 3M Moving Avg", f"month = {m}", lambda m=m: m_ma3(m), lambda m=m: e_ma3(m), MONEY)
for m, st in [("2017-06", False), ("2017-06", True), ("2018-08", True), ("2018-10", False)]:
    check("M12", "Revenue Running Total", f"month = {m}, slicer {'stable window' if st else 'none'}",
          lambda m=m, st=st: m_running(m, st), lambda m=m, st=st: e_running(m, st), MONEY)
E_JA = BASE_REV.format(j=CUST_J, w="AND YEAR(o.order_purchase_timestamp)={y} AND MONTH(o.order_purchase_timestamp)<=8 {s}")
for yr, mid, nm in [(2017, "M13", "Revenue 2017 Jan-Aug"), (2018, "M14", "Revenue 2018 Jan-Aug")]:
    check(mid, nm, "unfiltered", lambda yr=yr: m_janaug(yr), lambda yr=yr: sv(E_JA.format(y=yr, s="")), MONEY)
    check(mid, nm, "page slicer YearMonth = 2018-01..08 (must be ignored)", lambda yr=yr: m_janaug(yr),
          lambda yr=yr: sv(E_JA.format(y=yr, s="")), MONEY)
    check(mid, nm, "customer_state = SP", lambda yr=yr: m_janaug(yr, "SP"),
          lambda yr=yr: sv(E_JA.format(y=yr, s="AND c.customer_state='SP'")), MONEY)
yoy = lambda st=None: divide(m_janaug(2018, st) - m_janaug(2017, st), m_janaug(2017, st))
e_yoy = lambda s="": (lambda a, b: (b - a) / a)(sv(E_JA.format(y=2017, s=s)), sv(E_JA.format(y=2018, s=s)))
check("M15", "YoY Growth Jan-Aug %", "unfiltered", lambda: yoy(), lambda: e_yoy(), RATE)
check("M15", "YoY Growth Jan-Aug %", "customer_state = SP", lambda: yoy("SP"),
      lambda: e_yoy("AND c.customer_state='SP'"), RATE)

# ---- bug reproductions: superseded time-intelligence formulas ---------------
def old_ma3(month):
    """AVERAGEX ( DATESINPERIOD ( dim_date[Date], MAX(Date), -3, MONTH ), [Total Revenue] )."""
    last = DIM.Date[DIM.YearMonth == month].max()
    days = DIM.Date[(DIM.Date > last - pd.DateOffset(months=3)) & (DIM.Date <= last)]
    daily = O[(O.revenue_eligible == 1) & O.order_date.isin(days)].groupby("order_date").order_revenue.sum()
    return daily.mean()                                       # AVERAGEX skips BLANK days


bug("M11", "Revenue 3M Moving Avg", "old DATESINPERIOD formula at 2018-03",
    lambda: old_ma3("2018-03") / e_ma3("2018-03") < 0.05,
    f"old formula averages DAILY revenue: {old_ma3('2018-03'):,.0f} vs correct monthly "
    f"{e_ma3('2018-03'):,.0f} (x{old_ma3('2018-03') / e_ma3('2018-03'):.3f})")
bug("M12", "Revenue Running Total", "old ALLSELECTED(dim_date[Date]) on a YearMonth axis at 2017-06",
    lambda: abs(total_revenue(o_ctx(month="2017-06")) - e_running("2017-06", False)) > 1e6,
    "the YearMonth axis filter survives, so the 'running total' equals that month's revenue only "
    f"({total_revenue(o_ctx(month='2017-06')):,.0f} vs {e_running('2017-06', False):,.0f})")
bug("M15", "YoY Growth Jan-Aug %", "old Year/MonthNo filters under a 2018-01..08 YearMonth slicer",
    lambda: len(O[O.order_date.isin(DIM.Date[(DIM.Year == 2017) & (DIM.MonthNo <= 8)
                                               & DIM.YearMonth.between("2018-01", "2018-08")])]) == 0,
    "the YearMonth slicer is kept, intersects 2017 with 2018 -> Revenue 2017 Jan-Aug is BLANK -> YoY BLANK")
bug("M10", "Revenue MoM %", "old DATEADD formula at 2017-01 (previous month is 1 order in Dec 2016)",
    lambda: (MONTHLY[pd.Period("2017-01", "M")] - MONTHLY[pd.Period("2016-12", "M")])
            / MONTHLY[pd.Period("2016-12", "M")] > 1000,
    f"old MoM at 2017-01 = {((MONTHLY[pd.Period('2017-01','M')]/MONTHLY[pd.Period('2016-12','M')])-1)*100:,.0f}% "
    "against a 1-order month; the fix returns BLANK unless both months are complete")

# =============================================================================
# PAGE 2 — Customers, RFM, cohorts (M16-M23, N01-N06)
# =============================================================================
check("M16", "Total People", "unfiltered", lambda: dcount(C),
      lambda: sv("SELECT COUNT(DISTINCT customer_unique_id) FROM customers"))
E_PER = ("SELECT COUNT(*) FROM (SELECT c.customer_unique_id, COUNT(*) n FROM orders o "
         "JOIN customers c ON c.customer_id=o.customer_id GROUP BY c.customer_unique_id) t WHERE {w}")
check("M17", "Repeat Customers", "unfiltered", lambda: dcount(C[C.total_orders >= 2]), lambda: sv(E_PER.format(w="n>=2")))
check("M18", "One-Time Customers", "unfiltered", lambda: dcount(C[C.total_orders == 1]), lambda: sv(E_PER.format(w="n=1")))
check("M19", "Repeat Purchase Rate", "unfiltered", lambda: divide(dcount(C[C.total_orders >= 2]), dcount(C)),
      lambda: sv(E_PER.format(w="n>=2")) / sv("SELECT COUNT(DISTINCT customer_unique_id) FROM customers"), RATE)
check("M20", "Avg Orders Per Customer", "unfiltered", lambda: davg(C.total_orders),
      lambda: sv("SELECT COUNT(*) FROM orders") / sv("SELECT COUNT(DISTINCT customer_unique_id) FROM customers"), RATE)
E_PSTATE = ("SELECT SUM(v) FROM (SELECT c.customer_unique_id, MIN(c.customer_state) st, "
            "SUM(CASE WHEN o.revenue_eligible=1 THEN i.r ELSE 0 END) v FROM orders o "
            "JOIN customers c ON c.customer_id=o.customer_id "
            "LEFT JOIN (SELECT order_id, SUM(price) r FROM order_items GROUP BY order_id) i ON i.order_id=o.order_id "
            "GROUP BY c.customer_unique_id) t {w}")
check("M21", "Historical Customer Value", "unfiltered", lambda: dsum(C.historical_value),
      lambda: sv(E_PSTATE.format(w="")), MONEY)
check("M21", "Historical Customer Value", "customer_state = SP", lambda: dsum(C.loc[C.customer_state == "SP", "historical_value"]),
      lambda: sv(E_PSTATE.format(w="WHERE st='SP'")), MONEY)

# ---- RFM: expected rebuilt from base tables with tie-consistent scoring -----
E_RFM = sql("""
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
E_RFM["fs"] = np.select([E_RFM.f >= 3, E_RFM.f == 2], [5, 3], 1)


def _seg(r, f, m):
    if r >= 4 and f >= 3 and m >= 4: return "Champions"
    if r >= 3 and f >= 3: return "Loyal Customers"
    if r >= 4 and f == 1 and m >= 3: return "Potential Loyalists"
    if r <= 2 and m >= 4: return "At Risk"
    if r <= 2: return "Lost"
    return "Needs Attention"


E_RFM["seg"] = [_seg(*t) for t in zip(E_RFM.r, E_RFM.fs, E_RFM.m)]
SCORED = RFM[RFM.rfm_scored == 1]
SEGMENTS = sorted(E_RFM.seg.unique())
cust_in_seg = lambda rf, s=None: dcount(rf[(rf.rfm_scored == 1) & ((rf.rfm_segment == s) if s else True)])
check("N01", "RFM Scored Customers", "unfiltered", lambda: dcount(SCORED), lambda: float(len(E_RFM)))
check("M22", "Customers In Segment", "all scored", lambda: cust_in_seg(RFM), lambda: float(len(E_RFM)))
for s in SEGMENTS:
    check("M22", "Customers In Segment", f"segment = {s}", lambda s=s: cust_in_seg(RFM, s),
          lambda s=s: float((E_RFM.seg == s).sum()))
    check("M23", "Segment Revenue Share", f"segment = {s}",
          lambda s=s: divide(dsum(RFM.loc[RFM.rfm_segment == s, "monetary_value"]), dsum(RFM.monetary_value)),
          lambda s=s: E_RFM.loc[E_RFM.seg == s, "mon"].sum() / E_RFM.mon.sum(), RATE)
    check("N02", "Segment Customer Share", f"segment = {s}",
          lambda s=s: divide(cust_in_seg(RFM, s), cust_in_seg(RFM)),
          lambda s=s: (E_RFM.seg == s).mean(), RATE)
    check("N03", "Segment Avg Historical Value", f"segment = {s}",
          lambda s=s: divide(dsum(SCORED.loc[SCORED.rfm_segment == s, "monetary_value"]), cust_in_seg(RFM, s)),
          lambda s=s: E_RFM.loc[E_RFM.seg == s, "mon"].mean(), MONEY)
sp_people = set(C.loc[C.customer_state == "SP", "customer_unique_id"])          # vw_customer_summary -> rfm
RFM_SP = RFM[RFM.customer_unique_id.isin(sp_people)]
check("M23", "Segment Revenue Share", "segment = Potential Loyalists within customer_state = SP",
      lambda: divide(dsum(RFM_SP.loc[RFM_SP.rfm_segment == "Potential Loyalists", "monetary_value"]), dsum(RFM_SP.monetary_value)),
      lambda: (lambda t: t.loc[t.seg == "Potential Loyalists", "mon"].sum() / t.mon.sum())(E_RFM[E_RFM.st == "SP"]), RATE)
bug("M22", "Customers In Segment", "old COUNTROWS(vw_customer_summary) under a segment filter",
    lambda: "rfm_segment" not in C.columns and len(C) == 96096,
    "vw_customer_summary has no segment column and is on the ONE side, so a segment filter cannot reach it: "
    "every segment would show 96,096")

# ---- cohort retention: expected rebuilt from base tables --------------------
E_ACT = sql("""
WITH fo AS (SELECT c.customer_unique_id u, MIN(o.order_purchase_timestamp) f FROM orders o
            JOIN customers c ON c.customer_id=o.customer_id GROUP BY c.customer_unique_id),
m AS (SELECT u, DATE_FORMAT(f,'%Y-%m') coh FROM fo WHERE f >= '2017-01-01' AND f < '2018-09-01'),
a AS (SELECT DISTINCT m.coh, m.u, DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m') am FROM m
      JOIN customers c ON c.customer_unique_id=m.u JOIN orders o ON o.customer_id=c.customer_id)
SELECT coh, am, COUNT(*) n FROM a GROUP BY coh, am""")
E_ACT["k"] = [(pd.Period(a, "M") - pd.Period(c, "M")).n for c, a in zip(E_ACT.coh, E_ACT.am)]
E_SIZE = E_ACT[E_ACT.k == 0].set_index("coh").n
E_CELL = E_ACT.set_index(["coh", "k"]).n


def e_ret(coh=None, k=None):
    if k is None:
        return None                                           # guard: no single offset -> BLANK
    cohorts = [coh] if coh else list(E_SIZE.index)
    obs = [c for c in cohorts if pd.Period(c, "M") + k <= STABLE[1]]
    if not obs:
        return None
    return sum(E_CELL.get((c, k), 0) for c in obs) / sum(E_SIZE[c] for c in obs)


def m_ret(coh=None, k=None):
    rows = COH
    if coh: rows = rows[rows.cohort_month == coh]
    if k is not None: rows = rows[rows.months_since_acquisition == k]
    if rows.months_since_acquisition.nunique() != 1:          # IF ( HASONEVALUE ( ... ) )
        return None
    return divide(dsum(rows.active_customers), dsum(rows.loc[rows.is_observed == 1, "cohort_customers"]))


for coh in ["2017-01", "2018-08"]:
    check("N04", "Cohort Customers", f"cohort = {coh}",
          lambda coh=coh: dsum(COH.loc[(COH.cohort_month == coh) & (COH.months_since_acquisition == 0), "cohort_customers"]),
          lambda coh=coh: float(E_SIZE[coh]))
for coh, k, note in [("2017-01", 1, "observed cell"), ("2018-07", 1, "last observed cell of a late cohort"),
                     ("2018-07", 2, "UNOBSERVED cell -> BLANK, not 0"), ("2018-08", 1, "UNOBSERVED (right-censored)"),
                     (None, 0, "offset 0 across cohorts = 100%"),
                     (None, 1, "offset 1 across cohorts: denominator = observed cohorts only"),
                     (None, 19, "offset 19: only 2017-01 observable"), (None, None, "grand total -> BLANK")]:
    check("N05", "Cohort Retention %", f"cohort={coh or 'all'}, offset={k if k is not None else 'all'} ({note})",
          lambda coh=coh, k=k: m_ret(coh, k), lambda coh=coh, k=k: e_ret(coh, k), RATE)
for coh, k in [("2017-01", 1), ("2018-07", 2), ("2017-01", 0)]:
    check("N06", "Returning Customers", f"cohort={coh}, offset={k}",
          lambda coh=coh, k=k: dsum(COH.loc[(COH.cohort_month == coh) & (COH.months_since_acquisition == k), "returning_customers"]),
          lambda coh=coh, k=k: (None if k == 0 or pd.Period(coh, "M") + k > STABLE[1] else float(E_CELL.get((coh, k), 0))))
bug("N05", "Cohort Retention %", "naive denominator (all cohort sizes) at offset 1",
    lambda: abs(dsum(COH.loc[COH.months_since_acquisition == 1, "active_customers"]) / E_SIZE.sum() - e_ret(None, 1)) > 0,
    "including the right-censored 2018-08 cohort in the denominator understates offset-1 retention "
    f"({dsum(COH.loc[COH.months_since_acquisition == 1, 'active_customers']) / E_SIZE.sum():.6f} vs {e_ret(None, 1):.6f})")

# =============================================================================
# PAGE 3 — Category, product, seller x category (M24-M28, N07-N16)
# =============================================================================
E_CAT = sql("""SELECT p.product_category_name_english cat, SUM(oi.price) rev, COUNT(*) items,
                      SUM(oi.freight_value) fr, COUNT(DISTINCT oi.product_id) prods
               FROM order_items oi JOIN orders o ON o.order_id=oi.order_id JOIN products p ON p.product_id=oi.product_id
               WHERE o.revenue_eligible=1 GROUP BY cat""").set_index("cat")
def mask(df, **eq):
    """Boolean row mask for column == value filters; None values are ignored (no filter)."""
    m = pd.Series(True, index=df.index)
    for col, val in eq.items():
        if val is not None:
            m &= df[col] == val
    return m


cat_rev = lambda c=None, month=None: dsum(CAT.loc[mask(CAT, category=c, order_month=month), "revenue"])
check("M24", "Category Revenue", "unfiltered", lambda: cat_rev(), lambda: float(E_CAT.rev.sum()), MONEY)
check("M24", "Category Revenue", "dim_category = health_beauty", lambda: cat_rev("health_beauty"),
      lambda: float(E_CAT.rev["health_beauty"]), MONEY)
check("M24", "Category Revenue", "order_month = 2018-01", lambda: cat_rev(month="2018-01"),
      lambda: sv(BASE_REV.format(j="", w="AND DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m')='2018-01'")), MONEY)
check("M25", "Category Items Sold", "unfiltered", lambda: dsum(CAT.items_sold), lambda: float(E_CAT["items"].sum()))
check("M25", "Category Items Sold", "dim_category = health_beauty", lambda: dsum(CAT.loc[CAT.category == "health_beauty", "items_sold"]),
      lambda: float(E_CAT["items"]["health_beauty"]))
check("M26", "Distinct Categories", "unfiltered", lambda: float(CAT.category.nunique()), lambda: float(len(E_CAT)))
for c in ["health_beauty", "watches_gifts", "security_and_services"]:
    check("M27", "Category Revenue Share", f"dim_category = {c}",
          lambda c=c: divide(cat_rev(c), cat_rev()),                        # REMOVEFILTERS(dim_category, vw[category])
          lambda c=c: float(E_CAT.rev[c] / E_CAT.rev.sum()), RATE)
m_rank = CAT.groupby("category").revenue.sum().rank(method="dense", ascending=False)
e_rank = E_CAT.rev.rank(method="dense", ascending=False)
check("M28", "Category Rank", "every category on a dim_category axis (74 checks in one)",
      lambda: float((m_rank.reindex(DC.category) == e_rank.reindex(DC.category)).sum()), lambda: float(len(DC)))
check("N07", "Top Category Revenue", "unfiltered", lambda: float(CAT.groupby("category").revenue.sum().max()),
      lambda: float(E_CAT.rev.max()), MONEY)
semantic_note("M27", "Category Revenue Share",
     "old ALL(vw_category_performance[category]) does not remove a filter arriving from dim_category, so on a "
     "dim_category axis the denominator equals the category itself and every category shows 100%. Correct on the "
     "original model (axis = vw_category_performance[category]); broken by the new shared dimension.")
semantic_note("M28", "Category Rank",
     "old RANKX(ALL(vw_category_performance[category]), ...) on a dim_category axis iterates only the category that "
     "survives the dim_category filter, so every category ranks 1. Fixed by iterating ALL(dim_category[category]).")

prod_ctx = lambda c=None: PROD[(PROD.category == c)] if c else PROD
E_PRODN = sv("SELECT COUNT(DISTINCT oi.product_id) FROM order_items oi JOIN orders o ON o.order_id=oi.order_id WHERE o.revenue_eligible=1")
for c in [None, "health_beauty"]:
    lab = f"dim_category = {c}" if c else "unfiltered"
    er = (lambda c=c: float(E_CAT.rev[c] if c else E_CAT.rev.sum()))
    ei = (lambda c=c: float(E_CAT["items"][c] if c else E_CAT["items"].sum()))
    check("N08", "Product Revenue", lab, lambda c=c: dsum(prod_ctx(c).product_revenue), er, MONEY)
    check("N09", "Product Units Sold", lab, lambda c=c: dsum(prod_ctx(c).units_sold), ei)
    check("N10", "Products Sold", lab, lambda c=c: dcount(prod_ctx(c)[prod_ctx(c).units_sold > 0]),
          lambda c=c: float(E_CAT.prods[c]) if c else E_PRODN)
    check("N11", "Product Avg Item Price", lab,
          lambda c=c: divide(dsum(prod_ctx(c).product_revenue), dsum(prod_ctx(c).units_sold)),
          lambda c=c: er() / ei(), RATE)
    check("N12", "Product Avg Freight Per Item", lab,
          lambda c=c: divide(dsum(prod_ctx(c).freight_value), dsum(prod_ctx(c).units_sold)),
          lambda c=c: float((E_CAT.fr[c] if c else E_CAT.fr.sum())) / ei(), RATE)
bug("N11", "Product Avg Item Price", "AVERAGE(product_performance[avg_item_price]) instead of revenue / units",
    lambda: abs(PROD.avg_item_price.mean() - E_CAT.rev.sum() / E_CAT["items"].sum()) > 1,
    f"unweighted mean of product prices {PROD.avg_item_price.mean():.2f} vs true average item price "
    f"{E_CAT.rev.sum() / E_CAT['items'].sum():.2f}")

E_SC = sql("""WITH t AS (SELECT DISTINCT oi.seller_id, p.product_category_name_english cat, oi.order_id
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
TOP_SELLER = sql("SELECT oi.seller_id, SUM(oi.price) r FROM order_items oi JOIN orders o ON o.order_id=oi.order_id "
                 "WHERE o.revenue_eligible=1 GROUP BY oi.seller_id ORDER BY r DESC LIMIT 1").iloc[0]
scc = SC[SC.category == "health_beauty"]
check("N13", "Seller Category Revenue", "dim_category = health_beauty", lambda: dsum(scc.product_revenue),
      lambda: float(E_CAT.rev["health_beauty"]), MONEY)
check("N13", "Seller Category Revenue", "seller = largest seller (all its categories)",
      lambda: dsum(SC.loc[SC.seller_id == TOP_SELLER.seller_id, "product_revenue"]), lambda: float(TOP_SELLER.r), MONEY)
check("N14", "Seller Category Items", "unfiltered", lambda: dsum(SC.item_count), lambda: float(E_CAT["items"].sum()))
check("N15", "Seller Category Late Rate", "dim_category = health_beauty",
      lambda: divide(dsum(scc.late_orders), dsum(scc.delivery_measurable_orders)),
      lambda: float(E_SC.late["health_beauty"] / E_SC.dm["health_beauty"]), RATE)
check("N16", "Seller Category Dispatch Days", "dim_category = health_beauty (single-seller, valid timing)",
      lambda: divide(float((scc.avg_dispatch_days * scc.dispatch_measurable_orders).sum()), dsum(scc.dispatch_measurable_orders)),
      lambda: float(E_SC.disp_s["health_beauty"] / E_SC.disp_n["health_beauty"] / 86400), 1e-6)

# =============================================================================
# PAGE 4 — Sellers (M29-M35)
# =============================================================================
E_PAIRS = sql("""WITH p AS (SELECT DISTINCT oi.seller_id, oi.order_id FROM order_items oi
                            JOIN orders o ON o.order_id=oi.order_id WHERE o.revenue_eligible=1),
                      sc AS (SELECT order_id, SUM(review_score)/(COUNT(*)*1e0) s FROM order_reviews GROUP BY order_id)
                 SELECT p.seller_id, s.seller_state, o.delivery_measurable dm, o.is_late late, o.delivery_days dd, sc.s
                 FROM p JOIN orders o ON o.order_id=p.order_id JOIN sellers s ON s.seller_id=p.seller_id
                 LEFT JOIN sc ON sc.order_id=p.order_id""")


def e_seller(df, what):
    m = df[df.dm == 1]
    return {"late": m.late.sum() / len(m), "days": m.dd.sum() / len(m), "rating": df.s.mean(),
            "orders": float(len(df)), "sellers": float(df.seller_id.nunique())}[what]


def m_seller(state=None, seller=None):
    sel = SEL
    if state: sel = sel[sel.seller_state == state]
    if seller: sel = sel[sel.seller_id == seller]
    return sel, SK[SK.seller_id.isin(sel.seller_id)]


E_SEL_REV = sql("SELECT s.seller_state st, SUM(oi.price) r FROM order_items oi JOIN orders o ON o.order_id=oi.order_id "
                "JOIN sellers s ON s.seller_id=oi.seller_id WHERE o.revenue_eligible=1 GROUP BY st").set_index("st").r
for lab, st, sid in [("unfiltered", None, None), ("seller_state = SP", "SP", None),
                     ("seller = largest seller", None, TOP_SELLER.seller_id)]:
    sub = E_PAIRS[mask(E_PAIRS, seller_state=st, seller_id=sid)]
    sel_m = lambda st=st, sid=sid: m_seller(st, sid)
    if sid is None:
        check("M29", "Seller Revenue", lab, lambda s=sel_m: dsum(s()[0].revenue),
              lambda st=st: float(E_SEL_REV[st] if st else E_SEL_REV.sum()), MONEY)
        check("M30", "Sellers With Revenue", lab, lambda s=sel_m: dcount(s()[0]), lambda sub=sub: e_seller(sub, "sellers"))
        check("M31", "Seller Orders", lab + " (seller-order pairs)", lambda s=sel_m: dsum(s()[0].orders_served),
              lambda sub=sub: e_seller(sub, "orders"))
    check("M32", "Seller Avg Delivery Days", lab,
          lambda s=sel_m: divide(dsum(s()[1].delivery_days_sum), dsum(s()[1].delivery_measurable_orders)),
          lambda sub=sub: e_seller(sub, "days"), 1e-9)
    check("M33", "Seller Late Rate", lab,
          lambda s=sel_m: divide(dsum(s()[1].late_orders), dsum(s()[1].delivery_measurable_orders)),
          lambda sub=sub: e_seller(sub, "late"), RATE)
    check("M35", "Seller Inherited Order Rating", lab,
          lambda s=sel_m: divide(dsum(s()[1].review_score_sum), dsum(s()[1].reviewed_orders)),
          lambda sub=sub: e_seller(sub, "rating"), 1e-6)
check("M34", "Largest Seller Share", "unfiltered", lambda: divide(float(SEL.revenue.max()), dsum(SEL.revenue)),
      lambda: float(TOP_SELLER.r) / float(E_SEL_REV.sum()), RATE)
PLATFORM_LATE = sv("SELECT SUM(is_late)/(COUNT(*)*1e0) FROM orders WHERE delivery_measurable=1")
bug("M33", "Seller Late Rate", "old AVERAGE(vw_seller_performance[late_pct])",
    lambda: abs(SEL.late_pct.mean() / 100 - e_seller(E_PAIRS, "late")) > 0.002,
    f"unweighted mean of seller rates {SEL.late_pct.mean():.2f}% (and in percent units, unlike every other rate) "
    f"vs weighted {e_seller(E_PAIRS, 'late') * 100:.2f}% (platform order-level {PLATFORM_LATE * 100:.2f}%)")
bug("M32", "Seller Avg Delivery Days", "old AVERAGE(vw_seller_performance[avg_delivery_days])",
    lambda: abs(SEL.avg_delivery_days.mean() - e_seller(E_PAIRS, "days")) > 0.1,
    f"unweighted {SEL.avg_delivery_days.mean():.2f} vs weighted {e_seller(E_PAIRS, 'days'):.2f} days")
bug("M35", "Seller Inherited Order Rating", "old AVERAGE(vw_seller_performance[avg_review_score])",
    lambda: abs(SEL.avg_review_score.mean() - e_seller(E_PAIRS, "rating")) > 0.01,
    f"unweighted {SEL.avg_review_score.mean():.3f} vs weighted {e_seller(E_PAIRS, 'rating'):.3f}")

# =============================================================================
# PAGE 5 — Delivery operations and stages (M36-M44, N17-N24)
# =============================================================================
E_DEL = "SELECT {s} FROM orders o JOIN customers c ON c.customer_id=o.customer_id WHERE 1=1 {w}"
meas = lambda o: o[o.delivery_measurable == 1]
check("M36", "Delivered Orders", "unfiltered", lambda: dcount(O[O.is_delivered == 1]),
      lambda: sv(E_DEL.format(s="COUNT(*)", w="AND o.order_status='delivered'")))
check("M37", "Delivery Denominator", "unfiltered", lambda: dcount(meas(O)),
      lambda: sv(E_DEL.format(s="COUNT(*)", w="AND o.order_delivered_customer_date IS NOT NULL")))
check("M38", "Late Orders", "unfiltered", lambda: dsum(meas(O).is_late),
      lambda: sv(E_DEL.format(s="SUM(o.order_delivered_customer_date > o.order_estimated_delivery_date)",
                              w="AND o.order_delivered_customer_date IS NOT NULL")))
late_rate = lambda o: divide(dsum(meas(o).is_late), dcount(meas(o)))
on_time = lambda o: divide((dcount(meas(o)) or 0) - (dsum(meas(o).is_late) or 0), dcount(meas(o)))
E_LATE = ("SUM(o.order_delivered_customer_date > o.order_estimated_delivery_date)/(COUNT(*)*1e0)")
for lab, kw, w in [("unfiltered", {}, ""),
                   ("month = 2018-03", {"month": "2018-03"}, "AND DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m')='2018-03'"),
                   ("order_status = unavailable (no deliveries -> BLANK)", {"status": "unavailable"}, "AND o.order_status='unavailable'")]:
    check("M39", "Late Delivery Rate", lab, lambda kw=kw: late_rate(o_ctx(**kw)),
          lambda w=w: sv(E_DEL.format(s=E_LATE, w="AND o.order_delivered_customer_date IS NOT NULL " + w)), RATE)
    check("M40", "On-Time Delivery Rate", lab, lambda kw=kw: on_time(o_ctx(**kw)),
          lambda w=w: (lambda v: None if v is None else 1 - v)(
              sv(E_DEL.format(s=E_LATE, w="AND o.order_delivered_customer_date IS NOT NULL " + w))), RATE)
bug("M40", "On-Time Delivery Rate", "old 1 - [Late Delivery Rate] with no measurable orders",
    lambda: late_rate(o_ctx(status="unavailable")) is None,
    "1 - BLANK evaluates to 1, so an empty context (e.g. order_status = unavailable) showed 100% on time")
E_DAYS = "SUM(TIMESTAMPDIFF(SECOND,o.order_purchase_timestamp,o.order_delivered_customer_date))/86400e0/COUNT(*)"
E_DELAY = "SUM(TIMESTAMPDIFF(SECOND,o.order_estimated_delivery_date,o.order_delivered_customer_date))/86400e0/COUNT(*)"
for lab, kw, w in [("unfiltered", {}, ""), ("customer_state = SP", {"state": "SP"}, "AND c.customer_state='SP'")]:
    check("M41", "Avg Delivery Days", lab, lambda kw=kw: davg(meas(o_ctx(**kw)).delivery_days),
          lambda w=w: sv(E_DEL.format(s=E_DAYS, w="AND o.order_delivered_customer_date IS NOT NULL " + w)), HALF4)
    check("M42", "Avg Delay Days", lab, lambda kw=kw: davg(meas(o_ctx(**kw)).delay_days),
          lambda w=w: sv(E_DEL.format(s=E_DELAY, w="AND o.order_delivered_customer_date IS NOT NULL " + w)), HALF4)
check("M43", "Cancelled Orders", "unfiltered", lambda: dcount(O[O.order_status == "canceled"]),
      lambda: sv("SELECT COUNT(*) FROM orders WHERE order_status='canceled'"))
check("M44", "Cancellation Rate", "unfiltered", lambda: divide(dcount(O[O.order_status == "canceled"]), dcount(O)),
      lambda: sv("SELECT SUM(order_status='canceled')/(COUNT(*)*1e0) FROM orders"), RATE)

# ---- delivery stages: expected from the raw timestamps -----------------------
E_STAGE = """SELECT COUNT(*) n,
  SUM(TIMESTAMPDIFF(SECOND,o.order_purchase_timestamp,o.order_approved_at)) s1,
  SUM(TIMESTAMPDIFF(SECOND,o.order_approved_at,o.order_delivered_carrier_date)) s2,
  SUM(TIMESTAMPDIFF(SECOND,o.order_delivered_carrier_date,o.order_delivered_customer_date)) s3,
  SUM(TIMESTAMPDIFF(SECOND,o.order_purchase_timestamp,o.order_delivered_customer_date)) t
FROM orders o JOIN customers c ON c.customer_id=o.customer_id
WHERE o.order_approved_at IS NOT NULL AND o.order_delivered_carrier_date IS NOT NULL
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_purchase_timestamp <= o.order_approved_at AND o.order_approved_at <= o.order_delivered_carrier_date
  AND o.order_delivered_carrier_date <= o.order_delivered_customer_date {w}"""
for lab, kw, w in [("unfiltered", {}, ""), ("customer_state = SP", {"state": "SP"}, "AND c.customer_state='SP'"),
                   ("month = 2018-01", {"month": "2018-01"}, "AND DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m')='2018-01'")]:
    st = lambda kw=kw: DSO[DSO.order_id.isin(o_ctx(**kw).order_id)]          # vw_order_summary -> delivery_stage_orders
    ex = lambda w=w: sql(E_STAGE.format(w=w)).iloc[0].astype(float)
    check("N17", "Stage Orders", lab, lambda st=st: dcount(st()), lambda ex=ex: ex().n)
    for mid, nm, col, k in [("N18", "Purchase To Approval Days", "purchase_to_approval_seconds", "s1"),
                            ("N19", "Approval To Carrier Days", "approval_to_carrier_seconds", "s2"),
                            ("N20", "Carrier To Customer Days", "carrier_to_customer_seconds", "s3"),
                            ("N21", "Stage Total Days", "total_seconds", "t")]:
        check(mid, nm, lab, lambda st=st, col=col: divide(dsum(st()[col]), (dcount(st()) or 0) * 86400),
              lambda ex=ex, k=k: ex()[k] / ex().n / 86400, 1e-9)
    for mid, nm, col, k in [("N22", "Last Mile Share", "carrier_to_customer_seconds", "s3"),
                            ("N23", "Dispatch Stage Share", "approval_to_carrier_seconds", "s2"),
                            ("N24", "Approval Stage Share", "purchase_to_approval_seconds", "s1")]:
        check(mid, nm, lab, lambda st=st, col=col: divide(dsum(st()[col]), dsum(st().total_seconds)),
              lambda ex=ex, k=k: ex()[k] / ex().t, RATE)

# =============================================================================
# PAGE 6 — Satisfaction (M45-M49, N25-N35)
# =============================================================================
E_R = "SELECT {s} FROM order_reviews r JOIN orders o ON o.order_id=r.order_id WHERE 1=1 {w}"
check("M45", "Total Reviews", "unfiltered", lambda: dcount(REV), lambda: sv(E_R.format(s="COUNT(*)", w="")))
check("M45", "Total Reviews", "customer_state = SP (via vw_order_summary)",
      lambda: dcount(REV[REV.order_id.isin(o_ctx(state="SP").order_id)]),
      lambda: sv("SELECT COUNT(*) FROM order_reviews r JOIN orders o ON o.order_id=r.order_id "
                 "JOIN customers c ON c.customer_id=o.customer_id WHERE c.customer_state='SP'"))
check("M46", "Avg Review Score", "unfiltered (review grain)", lambda: davg(REV.review_score),
      lambda: sv(E_R.format(s="SUM(r.review_score)/(COUNT(*)*1e0)", w="")), RATE)
check("M47", "One-Star Rate", "unfiltered", lambda: divide(dcount(REV[REV.review_score == 1]), dcount(REV)),
      lambda: sv(E_R.format(s="SUM(r.review_score=1)/(COUNT(*)*1e0)", w="")), RATE)
check("M48", "Five-Star Rate", "unfiltered", lambda: divide(dcount(REV[REV.review_score == 5]), dcount(REV)),
      lambda: sv(E_R.format(s="SUM(r.review_score=5)/(COUNT(*)*1e0)", w="")), RATE)
E_ORDER_GRAIN = ("SELECT AVG(s) FROM (SELECT r.order_id, SUM(r.review_score)/(COUNT(*)*1e0) s FROM order_reviews r "
                 "JOIN orders o ON o.order_id=r.order_id WHERE 1=1 {w} GROUP BY r.order_id) t")
check("M49", "Avg Order Rating", "unfiltered (order grain)", lambda: davg(O.loc[O.review_count > 0, "review_score_avg"]),
      lambda: sv(E_ORDER_GRAIN.format(w="")), HALF4)
known = REV[REV.review_before_delivery.notna()]
check("N25", "Pre-Delivery Reviews", "unfiltered", lambda: dcount(REV[REV.review_before_delivery == 1]),
      lambda: sv(E_R.format(s="SUM(r.review_answer_timestamp < o.order_delivered_customer_date)", w="")))
check("N26", "Pre-Delivery Review Share", "unfiltered (of reviews on delivered orders)",
      lambda: divide(dcount(REV[REV.review_before_delivery == 1]), dcount(known)),
      lambda: sv(E_R.format(s="SUM(r.review_answer_timestamp < o.order_delivered_customer_date)/(COUNT(*)*1e0)",
                            w="AND o.order_delivered_customer_date IS NOT NULL")), RATE)
after = REV[REV.review_before_delivery == 0]
check("N27", "Avg Review Score After Arrival", "unfiltered (review grain)", lambda: davg(after.review_score),
      lambda: sv(E_R.format(s="SUM(r.review_score)/(COUNT(*)*1e0)",
                            w="AND r.review_answer_timestamp >= o.order_delivered_customer_date")), RATE)
check("N28", "One-Star Rate After Arrival", "unfiltered", lambda: divide(dcount(after[after.review_score == 1]), dcount(after)),
      lambda: sv(E_R.format(s="SUM(r.review_score=1)/(COUNT(*)*1e0)",
                            w="AND r.review_answer_timestamp >= o.order_delivered_customer_date")), RATE)

BUCKETS = {"1-7 days late": "o.delay_days > 0 AND o.delay_days <= 7", "8-15 days late": "o.delay_days > 7 AND o.delay_days <= 15",
           "on time": "o.delay_days > -7 AND o.delay_days <= 0", "15+ days late": "o.delay_days > 15"}


def m_order_rating(rows):
    """AVERAGEX ( VALUES ( vw_review_summary[order_id] ), CALCULATE ( AVERAGE ( review_score ) ) )."""
    return davg(rows.groupby("order_id").review_score.mean()) if len(rows) else None


for b, cond in BUCKETS.items():
    rb = REV[REV.delivery_bucket == b]
    check("N35", "Avg Order Rating (Review Table)", f"delivery_bucket = {b} (all reviews)",
          lambda rb=rb: m_order_rating(rb), lambda cond=cond: sv(E_ORDER_GRAIN.format(w="AND o.delivery_measurable=1 AND " + cond)), 1e-9)
    check("N34", "Avg Order Rating After Arrival", f"delivery_bucket = {b}",
          lambda rb=rb: m_order_rating(rb[rb.review_before_delivery == 0]),
          lambda cond=cond: sv(E_ORDER_GRAIN.format(
              w="AND o.delivery_measurable=1 AND r.review_answer_timestamp >= o.order_delivered_customer_date AND " + cond)), 1e-9)
check("N35", "Avg Order Rating (Review Table)", "unfiltered (must equal M49 at full precision)", lambda: m_order_rating(REV),
      lambda: sv(E_ORDER_GRAIN.format(w="")), 1e-9)

E_CS = sql("""WITH oc AS (SELECT DISTINCT oi.order_id, p.product_category_name_english cat
                          FROM order_items oi JOIN products p ON p.product_id=oi.product_id)
              SELECT oc.cat, COUNT(*) n, SUM(r.review_score)/(COUNT(*)*1e0) avg_s, SUM(r.review_score=1)/(COUNT(*)*1e0) one,
                     SUM(r.review_before_delivery=1)/(COUNT(*)*1e0) pre,
                     SUM(CASE WHEN r.review_before_delivery=0 THEN r.review_score END)/(SUM(r.review_before_delivery=0)*1e0) aft
              FROM oc JOIN order_reviews r ON r.order_id=oc.order_id GROUP BY oc.cat""").set_index("cat")
sel1 = lambda c, col: (lambda v: None if len(v) != 1 or pd.isna(v.iloc[0]) else float(v.iloc[0]))(
    CS.loc[CS.category == c, col] if c else CS[col])                       # SELECTEDVALUE / HASONEVALUE guard
for c in ["health_beauty", "office_furniture"]:
    check("N29", "Category Review Count", f"dim_category = {c}", lambda c=c: sel1(c, "review_count"), lambda c=c: float(E_CS.n[c]))
    check("N30", "Category Avg Review Score", f"dim_category = {c}", lambda c=c: sel1(c, "avg_review_score"),
          lambda c=c: float(E_CS.avg_s[c]), HALF4)
    check("N31", "Category One-Star Rate", f"dim_category = {c}", lambda c=c: divide(sel1(c, "one_star_pct"), 100),
          lambda c=c: float(E_CS.one[c]), HALF4 / 100)
    check("N32", "Category Avg Score After Arrival", f"dim_category = {c}", lambda c=c: sel1(c, "avg_review_score_after_arrival"),
          lambda c=c: float(E_CS.aft[c]), HALF4)
    check("N33", "Category Pre-Delivery Review Share", f"dim_category = {c}",
          lambda c=c: divide(sel1(c, "pct_reviews_before_delivery"), 100), lambda c=c: float(E_CS.pre[c]), HALF4 / 100)
check("N29", "Category Review Count", "no single category (total row) -> BLANK, not a double-counted sum",
      lambda: sel1(None, "review_count"), lambda: None)
check("N30", "Category Avg Review Score", "no single category (total row) -> BLANK", lambda: sel1(None, "avg_review_score"),
      lambda: None)
bug("N29", "Category Review Count", "plain SUM(category_satisfaction[review_count]) at the total",
    lambda: CS.review_count.sum() > sv("SELECT COUNT(*) FROM order_reviews r WHERE EXISTS "
                                       "(SELECT 1 FROM order_items oi WHERE oi.order_id=r.order_id)"),
    f"a plain SUM gives {int(CS.review_count.sum()):,}, more than the reviews that exist, because multi-category "
    "orders count in each category")
E_IW = sql("""WITH os AS (SELECT order_id, SUM(review_score)/(COUNT(*)*1e0) s FROM order_reviews GROUP BY order_id)
              SELECT p.product_category_name_english cat, COUNT(*) items, AVG(os.s) iw
              FROM order_items oi JOIN orders o ON o.order_id=oi.order_id JOIN products p ON p.product_id=oi.product_id
              JOIN os ON os.order_id=oi.order_id WHERE o.revenue_eligible=1 GROUP BY cat HAVING COUNT(*) >= 300""").set_index("cat")
OVERALL = sv(E_R.format(s="SUM(r.review_score)/(COUNT(*)*1e0)", w=""))
FLIPS = sorted(c for c in E_IW.index if (E_IW.iw[c] < OVERALL) != (E_CS.avg_s[c] < OVERALL))
bug("N30", "Category Avg Review Score", "item-weighted, eligible-only category score (notebook 03 / Insight 14 method)",
    lambda: len(FLIPS) > 0,
    f"repeating each order's score per item moves {len(FLIPS)} of {len(E_IW)} categories (>=300 items) across the "
    f"overall average {OVERALL:.4f}: {', '.join(FLIPS)}")

# =============================================================================
# REVENUE-MULTIPLICATION DETECTION
# =============================================================================
TOTAL = sv(BASE_REV.format(j="", w=""))
for nm, val in [("vw_order_summary", total_revenue(O)), ("vw_category_performance", dsum(CAT.revenue)),
                ("vw_seller_performance", dsum(SEL.revenue)), ("vw_customer_summary", dsum(C.historical_value)),
                ("product_performance", dsum(PROD.product_revenue)), ("seller_category_performance", dsum(SC.product_revenue)),
                ("rfm_customer_segments", dsum(RFM.monetary_value))]:
    check("X01", "Revenue reconciliation", f"total via {nm} = base item revenue", lambda val=val: val, lambda: TOTAL,
          MONEY, kind="fan-out guard")
inflated_pay = sv("SELECT SUM(oi.price) FROM order_items oi JOIN orders o ON o.order_id=oi.order_id "
                  "JOIN order_payments p ON p.order_id=oi.order_id WHERE o.revenue_eligible=1")
inflated_rev = sv("SELECT SUM(oi.price) FROM order_items oi JOIN orders o ON o.order_id=oi.order_id "
                  "JOIN order_reviews r ON r.order_id=oi.order_id WHERE o.revenue_eligible=1")
bug("X02", "Revenue reconciliation", "naive items x payments join",
    lambda: abs(inflated_pay - TOTAL) > 1000, f"would report {inflated_pay:,.2f} ({(inflated_pay / TOTAL - 1) * 100:+.2f}%)")
bug("X03", "Revenue reconciliation", "naive items x reviews inner join",
    lambda: abs(inflated_rev - TOTAL) > 1000, f"would report {inflated_rev:,.2f} ({(inflated_rev / TOTAL - 1) * 100:+.2f}%)")

# ---- supporting checks carried over from the original validator -------------
check("S01", "Total Freight All Statuses", "unfiltered", lambda: dsum(O.order_freight),
      lambda: sv("SELECT SUM(freight_value) FROM order_items"), MONEY, kind="supporting")
check("S02", "Revenue Stable Window", "in_stable_window = 1", lambda: total_revenue(O[O.in_stable_window == 1]),
      lambda: sv(BASE_REV.format(j="", w="AND o.order_purchase_timestamp >= '2017-01-01' AND o.order_purchase_timestamp < '2018-09-01'")),
      MONEY, kind="supporting")
check("S03", "Orders With Review", "unfiltered", lambda: dcount(O[O.review_count > 0]),
      lambda: sv("SELECT COUNT(DISTINCT order_id) FROM order_reviews"), kind="supporting")

CONN.close()

# =============================================================================
# COVERAGE — every measure documented in dax_measures.md has checks, and vice versa
# =============================================================================
import re                                                    # noqa: E402
DOC = (ROOT / "powerbi" / "dax_measures.md").read_text(encoding="utf-8")
documented = dict(re.findall(r"^-- \[([MN]\d{2})\] (.+?)\s*$", DOC, flags=re.M))
checked = {r["id"]: r["measure"] for r in RESULTS if r["kind"] == "measure"}
missing = sorted(set(documented) - set(checked))
undocumented = sorted(set(checked) - set(documented))
renamed = sorted(i for i in set(documented) & set(checked) if documented[i] != checked[i])
for label, bad in [("every documented measure has >= 1 check", missing),
                   ("every checked measure is documented", undocumented),
                   ("documented and checked names agree", renamed)]:
    RESULTS.append({"id": "COV", "measure": "Coverage", "context": label, "kind": "coverage",
                    "model": float(len(documented)), "expected": float(len(checked)), "pass": not bad,
                    "error": ", ".join(bad)})

# =============================================================================
# Report
# =============================================================================
res = pd.DataFrame(RESULTS)
res.to_csv(ROOT / "powerbi" / "dax_validation_results.csv", index=False)
fmt = lambda v: "BLANK" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:,.6f}"
print("=" * 120)
print("DAX MEASURE LOGIC VALIDATION — model (pandas over imported CSVs) vs expected (SQL over base tables)")
print("=" * 120)
for kind in ["measure", "supporting", "fan-out guard", "coverage", "bug reproduction"]:
    part = res[res.kind == kind]
    if part.empty:
        continue
    print(f"\n--- {kind.upper()} CHECKS ({int(part['pass'].sum())}/{len(part)}) ---")
    for _, r in part.iterrows():
        flag = "PASS" if r["pass"] else "FAIL"
        if kind == "bug reproduction":
            print(f"  {flag}  {r.id:<4} {r.measure:<32} {r.context}\n               {r.get('detail', '')}")
        else:
            print(f"  {flag}  {r.id:<4} {r.measure:<32} {r.context:<62} model {fmt(r.model):>20}  expected {fmt(r.expected):>20}"
                  + (f"  {r.error}" if r.error else ""))
print(f"\n--- DAX SEMANTICS NOTES (not executable on macOS; not counted) ---")
for mid, nm, text in NOTES:
    print(f"  NOTE  {mid:<4} {nm:<32} {text}")
meas_ids = res[res.kind == "measure"].groupby("id")["pass"].all()
orig = meas_ids[meas_ids.index.str.startswith("M")]
new = meas_ids[meas_ids.index.str.startswith("N")]
print("\n" + "-" * 120)
print(f"original measures (M01-M49): {int(orig.sum())}/{len(orig)} pass   |   new measures (N01-N{len(new):02d}): {int(new.sum())}/{len(new)} pass")
print(f"checks: {len(res)}   PASS: {int(res['pass'].sum())}   FAIL: {int((~res['pass']).sum())}")
print("\nSCOPE: emulated DAX logic over the imported CSVs, compared with independent SQL on the base tables.")
print("NOT verified: DAX syntax, Power BI engine evaluation, relationship settings, slicer interaction.")
sys.exit(0 if res["pass"].all() else 1)
