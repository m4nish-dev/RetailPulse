"""
RetailPulse - validate the evidence behind two recommendations (2026-11-27).

Runs the read-only queries in sql/11_insight_evidence.sql through the
application account and compares every figure with an independent pandas
rebuild from dataset/cleaned/:

  E1  time from first to second order (Insight 6)
  E2  freight as a share of product value by order-value band (priority 3)
  E3  what a free-shipping threshold at the 86.90 BRL median would cover
  E4  freight share by customer region and by items per order

Read-only. Exit code 1 on any mismatch.
Usage:  ./venv/bin/python scripts/validate_insight_evidence.py
"""
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from rp_db import ConfigError, get_connection                    # noqa: E402

RESULTS = []


def check(name, sql_v, pd_v, tol=0.0):
    ok = (sql_v is None and pd_v is None) or (sql_v is not None and pd_v is not None
                                               and abs(float(sql_v) - float(pd_v)) <= tol + 1e-9)
    RESULTS.append((name, ok, sql_v, pd_v))


def sql_statements():
    text = (ROOT / "sql" / "11_insight_evidence.sql").read_text()
    body = "\n".join(l for l in text.splitlines() if not l.strip().startswith("--"))
    stmts = [s.strip() for s in body.split(";") if s.strip()]
    return [s for s in stmts if re.match(r"^(SELECT|WITH)\b", s, re.I)]


def main():
    try:
        conn = get_connection()
    except ConfigError as e:
        sys.exit(f"CONFIG ERROR: {e}")
    q = sql_statements()
    if len(q) != 5:
        sys.exit(f"expected 5 queries in sql/11_insight_evidence.sql, found {len(q)}")

    def run(s):
        cur = conn.cursor(); cur.execute(s)
        cols = [d[0] for d in cur.description]; rows = cur.fetchall(); cur.close()
        return pd.DataFrame(rows, columns=cols, dtype=object)

    e1, e1q, e2, e3, e4 = run(q[0]).iloc[0], run(q[1]), run(q[2]), run(q[3]).iloc[0], run(q[4])
    conn.close()

    # ---- pandas rebuild ------------------------------------------------------
    o = pd.read_csv(ROOT / "dataset/cleaned/orders_clean.csv", low_memory=False,
                    usecols=["order_id", "customer_unique_id", "order_purchase_timestamp",
                             "revenue_eligible", "has_items", "order_revenue", "order_freight",
                             "customer_state", "item_count"],
                    parse_dates=["order_purchase_timestamp"])
    people = o.customer_unique_id.nunique()
    o = o.sort_values(["customer_unique_id", "order_purchase_timestamp", "order_id"])
    o["n"] = o.groupby("customer_unique_id").cumcount() + 1
    f = o[o.n == 1].set_index("customer_unique_id").order_purchase_timestamp
    s = o[o.n == 2].set_index("customer_unique_id").order_purchase_timestamp
    f = f.loc[s.index]
    gap_days = (s.dt.normalize() - f.dt.normalize()).dt.days
    gap_sec = (s - f).dt.total_seconds()
    later = gap_days[gap_days > 0]

    check("E1 repeat customers", e1.repeat_customers, len(gap_days))
    check("E1 second order on the same day", e1.same_day, int((gap_days == 0).sum()))
    check("E1 same-day %", e1.same_day_pct, round((gap_days == 0).mean() * 100, 1), 0.05)
    check("E1 second order within one hour", e1.within_one_hour, int((gap_sec < 3600).sum()))
    check("E1 returned on a later day", e1.returned_later_day, len(later))
    check("E1 later-day returners % of all people", e1.returned_later_day_pct_of_people,
          round(len(later) / people * 100, 2), 0.005)
    for d, col in [(30, "later_within_30d_pct"), (90, "later_within_90d_pct"), (180, "later_within_180d_pct")]:
        check(f"E1 later returns within {d} days %", e1[col], round((later <= d).mean() * 100, 1), 0.05)
    check("E1 later returns mean days", e1.later_mean_days, round(later.mean(), 1), 0.05)
    for _, r in e1q.iterrows():
        check(f"E1 later-return gap quantile {float(r["quantile"]):.2f}", r.gap_days,
              round(float(later.quantile(float(r["quantile"]))), 2), 0.005)

    e = o[o.revenue_eligible.astype(str).eq("True") & o.has_items.astype(str).eq("True")].copy()
    bins = [0, 50, 86.90, 120, 200, 500, np.inf]
    labels = ["1. <50", "2. 50-86.90", "3. 86.90-120", "4. 120-200", "5. 200-500", "6. 500+"]
    e["band"] = pd.cut(e.order_revenue.round(2), bins=bins, labels=labels, right=False)
    g = e.groupby("band", observed=True).agg(orders=("order_id", "size"), value=("order_revenue", "sum"),
                                             freight=("order_freight", "sum"))
    check("E2 orders in population", sum(e2.orders.astype(int)), len(e))
    for _, r in e2.iterrows():
        p = g.loc[r.band]
        check(f"E2 {r.band} orders", r.orders, p.orders)
        check(f"E2 {r.band} value BRL", r.value_brl, round(p.value, 2), 0.01)
        check(f"E2 {r.band} freight BRL", r.freight_brl, round(p.freight, 2), 0.01)
        check(f"E2 {r.band} freight % of value", r.freight_pct_of_value, round(p.freight / p.value * 100, 2), 0.005)


    # ---- E3 threshold impact -------------------------------------------------
    v = e.order_revenue.round(2)
    qual, near = v >= 86.90, (v >= 70) & (v < 86.90)
    check("E3 qualifying orders (>= 86.90)", e3.qualifying_orders, int(qual.sum()))
    check("E3 qualifying %", e3.qualifying_pct, round(qual.mean() * 100, 2), 0.005)
    check("E3 freight on qualifying orders BRL", e3.qualifying_freight_brl, round(e.loc[qual, "order_freight"].sum(), 2), 0.01)
    check("E3 qualifying freight % of all freight", e3.qualifying_pct_of_freight,
          round(e.loc[qual, "order_freight"].sum() / e.order_freight.sum() * 100, 1), 0.05)
    check("E3 qualifying freight % of product revenue", e3.qualifying_pct_of_product_revenue,
          round(e.loc[qual, "order_freight"].sum() / e.order_revenue.sum() * 100, 1), 0.05)
    check("E3 near-miss orders (70.00-86.89)", e3.near_miss_orders, int(near.sum()))
    check("E3 near-miss %", e3.near_miss_pct, round(near.mean() * 100, 2), 0.005)

    # ---- E4 by region and items ----------------------------------------------
    reg = {"SP": "SP", **{x: "Southeast excl. SP" for x in ["RJ", "MG", "ES"]}, **{x: "South" for x in ["PR", "SC", "RS"]},
           **{x: "Centre-West" for x in ["DF", "GO", "MT", "MS"]},
           **{x: "Northeast" for x in ["BA", "PE", "CE", "MA", "PB", "RN", "AL", "PI", "SE"]}}
    e["grp_r"] = "region: " + e.customer_state.map(reg).fillna("North")
    e["grp_i"] = "items: " + np.where(e.item_count > 1, "2+", "1")
    for col in ["grp_r", "grp_i"]:
        gg = e.groupby(col).agg(orders=("order_id", "size"), value=("order_revenue", "sum"), freight=("order_freight", "sum"),
                                avg_fr=("order_freight", "mean"), qual=("order_revenue", lambda x: (x.round(2) >= 86.90).mean() * 100))
        for name, p in gg.iterrows():
            r = e4[e4.grp == name].iloc[0]
            check(f"E4 {name} orders", r.orders, p.orders)
            check(f"E4 {name} freight % of value", r.freight_pct_of_value, round(p.freight / p.value * 100, 2), 0.005)
            check(f"E4 {name} avg freight BRL", r.avg_freight_brl, round(p.avg_fr, 2), 0.005)
            check(f"E4 {name} qualifying %", r.qualifying_pct, round(p.qual, 2), 0.005)
    check("E4 group rows returned", len(e4), 8)

    print("INSIGHT EVIDENCE — sql/11_insight_evidence.sql vs independent pandas")
    for name, ok, a, b in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<46} SQL {a}  pandas {b}")
    n_pass = sum(r[1] for r in RESULTS)
    print(f"checks: {len(RESULTS)}   PASS: {n_pass}   FAIL: {len(RESULTS) - n_pass}")
    sys.exit(0 if n_pass == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
