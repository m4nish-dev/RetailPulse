"""
RetailPulse - export the validated MySQL views as CSV for Power BI import.

WHY THIS EXISTS
Power BI Desktop runs only on Windows. On a Mac the database lives here but
the dashboard has to be built elsewhere, so these extracts make the import
turnkey: copy one folder to the Windows machine, no MySQL connector, no
networking, no credentials.

Connecting Power BI straight to MySQL is the better long-term option and is
documented in powerbi/README.md. These extracts are the fallback that works
without any database access at all.

IMPORTANT: it exports the VIEWS, not the base tables. The views already solve
the grain problem - vw_order_summary has items, payments and reviews
pre-aggregated to one row per order - so a Power BI model built on them
cannot produce the +4.54% revenue fan-out that joining raw tables causes.

Usage:  ./venv/bin/python scripts/export_powerbi_data.py
"""
from pathlib import Path
import sys

import pandas as pd

try:
    import mysql.connector
except ImportError:
    sys.exit("mysql-connector-python not installed:  pip install mysql-connector-python")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "powerbi" / "data"
OUT.mkdir(parents=True, exist_ok=True)

VIEWS = [
    "vw_order_summary",        # one row per order  - the fact table
    "vw_customer_summary",     # one row per PERSON (customer_unique_id)
    "vw_monthly_revenue",      # one row per month
    "vw_category_performance", # category x month
    "vw_seller_performance",   # one row per seller
    "vw_delivery_performance", # state x month
    "vw_review_summary",       # one row per review
]

# Small dimension tables Power BI needs for slicers and lookups.
TABLES = ["sellers", "products", "product_category_translation"]


def main() -> None:
    try:
        conn = mysql.connector.connect(host="127.0.0.1", user="root",
                                       database="retailpulse")
    except Exception as e:                                  # noqa: BLE001
        sys.exit(f"Cannot reach MySQL ({type(e).__name__}). "
                 "Start it with:  brew services start mysql@8.4")

    manifest = []
    for name in VIEWS + TABLES:
        df = pd.read_sql(f"SELECT * FROM {name}", conn)
        path = OUT / f"{name}.csv"
        df.to_csv(path, index=False)
        mb = path.stat().st_size / 1024**2
        manifest.append({"object": name, "rows": len(df),
                         "columns": df.shape[1], "size_mb": round(mb, 2)})
        print(f"  {name:<30}{len(df):>9,} rows x {df.shape[1]:>2} cols   {mb:>6.1f} MB")

    mf = pd.DataFrame(manifest)
    mf.to_csv(OUT / "_manifest.csv", index=False)
    print(f"\nTotal: {mf.rows.sum():,} rows, {mf.size_mb.sum():.1f} MB -> {OUT}")

    # Date table. Power BI time intelligence (DATEADD, SAMEPERIODLASTYEAR,
    # TOTALYTD) requires a contiguous, gap-free date dimension marked as the
    # model's date table. Generating it here means it cannot be forgotten.
    o = pd.read_sql("SELECT MIN(order_date) a, MAX(order_date) b FROM orders", conn)
    dates = pd.date_range(o.a.iloc[0], o.b.iloc[0], freq="D")
    dt = pd.DataFrame({"Date": dates})
    dt["Year"] = dt.Date.dt.year
    dt["Quarter"] = "Q" + dt.Date.dt.quarter.astype(str)
    dt["MonthNo"] = dt.Date.dt.month
    dt["MonthName"] = dt.Date.dt.strftime("%b")
    dt["YearMonth"] = dt.Date.dt.strftime("%Y-%m")
    dt["YearMonthSort"] = dt.Date.dt.year * 100 + dt.Date.dt.month
    dt["DayOfWeek"] = dt.Date.dt.day_name()
    # Flags the 20 complete months. The dataset's edge months hold 4, 1, 16
    # and 4 orders and November 2016 is absent entirely, so trend visuals must
    # filter on this or they show a collapse that never happened.
    dt["InStableWindow"] = dt.YearMonth.between("2017-01", "2018-08")
    dt.to_csv(OUT / "dim_date.csv", index=False)
    print(f"  {'dim_date (generated)':<30}{len(dt):>9,} rows x {dt.shape[1]:>2} cols")
    print(f"     range {dt.Date.min().date()} .. {dt.Date.max().date()}, "
          f"{int(dt.InStableWindow.sum())} days flagged in the stable window")
    conn.close()


if __name__ == "__main__":
    main()
