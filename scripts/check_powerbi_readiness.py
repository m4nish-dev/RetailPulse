"""
RetailPulse - Power BI data-readiness check (read-only).

Confirms the CSVs Power BI imports are complete and consistent before (and
after) they are copied to the Windows build machine:

  * all 20 tables readable; row/column counts match both manifests;
    analytical files match their manifest MD5
  * extracts have the same row counts as live MySQL (skipped with --offline)
  * every Table[column] referenced by the DAX in powerbi/dax_measures.md exists
  * primary keys unique; the 11 model relationships have a unique one side,
    no orphans and no blank keys
  * dates valid and contiguous; blanks exactly where designed
  * eligible revenue identical across 7 sources (no join multiplication)

Usage:  ./venv/bin/python scripts/check_powerbi_readiness.py [--offline]
Exit code 1 on any failure.
"""
import argparse
import hashlib
from pathlib import Path
import re
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "powerbi" / "data"
A = D / "analytical"
R = []


def ck(area, name, ok, detail=""):
    R.append((area, name, bool(ok), detail))


PK = {"vw_order_summary": ["order_id"], "vw_customer_summary": ["customer_unique_id"],
      "vw_seller_performance": ["seller_id"], "vw_review_summary": ["review_id", "order_id"],
      "vw_category_performance": ["category", "order_month"], "vw_delivery_performance": ["customer_state", "order_month"],
      "vw_monthly_revenue": ["order_month"], "dim_date": ["Date"], "sellers": ["seller_id"], "products": ["product_id"],
      "product_category_translation": ["product_category_name"], "rfm_customer_segments": ["customer_unique_id"],
      "cohort_retention": ["cohort_month", "months_since_acquisition"], "product_performance": ["product_id"],
      "seller_category_performance": ["seller_id", "category"], "delivery_stage_orders": ["order_id"],
      "delivery_stage_summary": ["stage_order"], "category_satisfaction": ["category"],
      "seller_scorecard": ["seller_id"], "dim_category": ["category"]}

# (one table, key, many table, key) — must match powerbi/windows_implementation_guide.md §2
RELATIONSHIPS = [
    ("dim_date", "Date", "vw_order_summary", "order_date"),
    ("vw_order_summary", "order_id", "vw_review_summary", "order_id"),
    ("vw_customer_summary", "customer_unique_id", "vw_order_summary", "customer_unique_id"),
    ("vw_customer_summary", "customer_unique_id", "rfm_customer_segments", "customer_unique_id"),
    ("vw_order_summary", "order_id", "delivery_stage_orders", "order_id"),
    ("vw_seller_performance", "seller_id", "seller_scorecard", "seller_id"),
    ("dim_category", "category", "vw_category_performance", "category"),
    ("dim_category", "category", "product_performance", "category"),
    ("dim_category", "category", "seller_category_performance", "category"),
    ("dim_category", "category", "category_satisfaction", "category"),
    ("vw_seller_performance", "seller_id", "seller_category_performance", "seller_id"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip the live MySQL comparison")
    args = ap.parse_args()

    T = {p.stem: pd.read_csv(p, low_memory=False)
         for p in sorted(D.glob("*.csv")) + sorted(A.glob("*.csv")) if not p.name.startswith("_")}
    ck("files", "20 tables readable", len(T) == 20 and set(T) == set(PK), f"{len(T)} read")
    mf = pd.read_csv(D / "_manifest.csv").set_index("object")
    ma = pd.read_csv(A / "_manifest.csv").set_index("source")
    ck("files", "row/column counts match both manifests",
       all(T[o].shape == (r.rows, r.columns) for o, r in mf.iterrows())
       and all(T[o].shape == (r.rows, r.columns) for o, r in ma.iterrows()))
    ck("files", "analytical files byte-identical to manifest MD5",
       all(hashlib.md5((A / f"{s}.csv").read_bytes()).hexdigest() == r.md5 for s, r in ma.iterrows()))

    live_rev = None
    if args.offline:
        ck("files", "live MySQL comparison", True, "skipped (--offline)")
    else:
        sys.path.insert(0, str(ROOT / "scripts"))
        from rp_db import get_connection
        c = get_connection(); cur = c.cursor()
        same = []
        for v in mf.index:
            cur.execute(f"SELECT COUNT(*) FROM `{v}`"); same.append(cur.fetchone()[0] == len(T[v]))
        cur.execute("SELECT SUM(order_revenue) FROM vw_order_summary WHERE revenue_eligible = 1")
        live_rev = float(cur.fetchone()[0]); c.close()
        ck("files", "view/table extracts have the same row counts as live MySQL", all(same))

    doc = (ROOT / "powerbi" / "dax_measures.md").read_text()
    dax = "\n".join(re.findall(r"```dax\n(.*?)```", doc, flags=re.S))
    n_meas = len(re.findall(r"^-- \[[MN]\d{2}\] ", doc, flags=re.M))
    refs = set(re.findall(r"\b([a-z_]+)\[([A-Za-z_]+)\]", dax))
    missing = [f"{t}[{col}]" for t, col in sorted(refs) if t not in T or col not in T[t].columns]
    ck("DAX", f"every Table[column] referenced by the {n_meas} measures exists", not missing,
       f"{len(refs)} references; missing: {missing or 'none'}")

    bad = [t for t, k in PK.items() if T[t].duplicated(k).any() or T[t][k].isna().any().any()]
    ck("keys", "grain/primary key unique and non-null in all 20 tables", not bad, f"failures: {bad or 'none'}")
    for one, k1, many, k2 in RELATIONSHIPS:
        a = T[one][k1].astype(str); b = T[many][k2].dropna().astype(str)
        orphans = int((~b.isin(set(a))).sum()); nulls = int(T[many][k2].isna().sum())
        ck("relationships", f"{one}[{k1}] 1:* {many}[{k2}]", a.is_unique and orphans == 0 and nulls == 0,
           f"one side unique={a.is_unique}, orphans={orphans}, blank keys={nulls}")

    dd = pd.to_datetime(T["dim_date"].Date, errors="coerce")
    ck("dates", "dim_date parses, contiguous, no gaps",
       dd.notna().all() and (dd.diff().dropna() == pd.Timedelta(days=1)).all(),
       f"{dd.min().date()}..{dd.max().date()}, {len(dd)} days")
    od = pd.to_datetime(T["vw_order_summary"].order_date, errors="coerce")
    ck("dates", "order_date parses and lies inside dim_date", od.notna().all() and od.min() >= dd.min() and od.max() <= dd.max())
    mi = T["dim_date"]
    ck("dates", "MonthIndex = Year*12+MonthNo; 608 stable-window days",
       (mi.MonthIndex == mi.Year * 12 + mi.MonthNo).all() and int(mi.InStableWindow.astype(str).eq("True").sum()) == 608)
    rs = T["vw_review_summary"].review_creation_date.astype(str)
    ck("dates", "review_creation_date: one text format, all parse",
       pd.to_datetime(rs, errors="coerce").notna().all() and rs.str.len().nunique() == 1)

    coh = T["cohort_retention"]
    ck("blanks", "cohort: 190 unobserved cells blank, 210 observed non-blank",
       coh[coh.is_observed == 0].retention_pct.isna().all() and coh[coh.is_observed == 1].retention_pct.notna().all()
       and int((coh.is_observed == 0).sum()) == 190)
    rv = T["vw_review_summary"].review_before_delivery
    ck("blanks", "review_before_delivery: 4,795 = 1; blank only for undelivered orders",
       int((rv == 1).sum()) == 4795 and set(rv.dropna().unique()) <= {0, 1})
    rfm = T["rfm_customer_segments"]
    ck("blanks", "RFM scores blank exactly for the 1,113 unscored people",
       int(rfm.r_score.isna().sum()) == int((rfm.rfm_scored == 0).sum()) == 1113)

    money = {"vw_order_summary": T["vw_order_summary"].query("revenue_eligible == 1").order_revenue.sum(),
             "vw_category_performance": T["vw_category_performance"].revenue.sum(),
             "vw_seller_performance": T["vw_seller_performance"].revenue.sum(),
             "vw_customer_summary": T["vw_customer_summary"].historical_value.sum(),
             "product_performance": T["product_performance"].product_revenue.sum(),
             "seller_category_performance": T["seller_category_performance"].product_revenue.sum(),
             "rfm_customer_segments": T["rfm_customer_segments"].monetary_value.sum()}
    ref = live_rev if live_rev is not None else money["vw_order_summary"]
    ck("revenue", "eligible revenue identical in 7 sources" + ("" if args.offline else " and live MySQL"),
       all(round(v * 100) == round(ref * 100) for v in money.values()), f"BRL {ref:,.2f}")

    ck("types", "32-character hex IDs intact",
       all(T[t][c].astype(str).str.fullmatch(r"[0-9a-f]{32}").all()
           for t, c in [("vw_order_summary", "order_id"), ("vw_order_summary", "customer_unique_id"), ("sellers", "seller_id")]))
    z = pd.read_csv(D / "sellers.csv", dtype=str).seller_zip_code_prefix
    ck("types", "seller zip prefixes keep 5 characters (import as Text)", z.str.len().eq(5).all())

    for area, name, ok, detail in R:
        print(f"  {'PASS' if ok else 'FAIL'}  [{area}] {name}" + (f"  — {detail}" if detail else ""))
    n = sum(r[2] for r in R)
    print(f"checks: {len(R)}   PASS: {n}   FAIL: {len(R) - n}")
    sys.exit(0 if n == len(R) else 1)


if __name__ == "__main__":
    main()
