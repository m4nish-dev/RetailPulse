"""
RetailPulse - export the validated MySQL views that the Tableau dashboard reads.

Writes one CSV per view into tableau/data/ plus _manifest.csv (rows, columns,
size, MD5). Tableau Desktop Public Edition cannot connect to MySQL, so the
dashboard is built on these files; the published workbook therefore never
contains database connection details.

IMPORTANT: it exports the VIEWS, not the base tables. The views already solve
the grain problem: vw_order_summary has items, payments and reviews
pre-aggregated to one row per order, so a dashboard built on them cannot
produce the +4.54% revenue fan-out that joining the raw tables causes.

SAFETY
  * Read-only: the app account from .env (scripts/rp_db.py) in a READ ONLY
    session. Only SELECT * FROM <view> is executed.
  * Writes only to the output folder (default tableau/data/). Never run by
    scripts/run_all_validations.py; the source validators compare the existing
    files with live SQL instead.

Usage:
  ./venv/bin/python scripts/export_tableau_data.py                 # writes tableau/data/
  ./venv/bin/python scripts/export_tableau_data.py --out /tmp/x    # writes elsewhere (e.g. to compare)
"""
from pathlib import Path
import argparse
import hashlib
import sys
import warnings

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rp_db import ConfigError, get_connection                 # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "tableau" / "data"

VIEWS = [
    "vw_order_summary",        # one row per order  - the order fact
    "vw_review_summary",       # one row per review
    "vw_customer_summary",     # one row per PERSON (customer_unique_id)
    "vw_category_performance", # category x month
    "vw_seller_performance",   # one row per seller
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Export the dashboard view extracts")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output folder (default tableau/data/)")
    out = ap.parse_args().out
    out.mkdir(parents=True, exist_ok=True)
    # pandas warns that it only tests SQLAlchemy connections; the plain DBAPI
    # connection has produced byte-identical files since Phase 6, so keep it.
    warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
    try:
        conn = get_connection(read_only=True)                 # app account from .env
    except ConfigError as e:
        sys.exit(f"CONFIG ERROR: {e}")

    manifest = []
    for name in VIEWS:
        df = pd.read_sql(f"SELECT * FROM {name}", conn)
        path = out / f"{name}.csv"
        # Explicit format: pandas 3 otherwise writes date-only text for any
        # write chunk whose timestamps are all midnight, leaving one column
        # with two formats (seen on vw_review_summary.review_creation_date).
        df.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")
        mb = path.stat().st_size / 1024**2
        manifest.append({"object": name, "rows": len(df), "columns": df.shape[1],
                         "size_mb": round(mb, 2), "md5": hashlib.md5(path.read_bytes()).hexdigest()})
        print(f"  {name:<30}{len(df):>9,} rows x {df.shape[1]:>2} cols   {mb:>6.1f} MB")
    conn.close()

    mf = pd.DataFrame(manifest)
    mf.to_csv(out / "_manifest.csv", index=False, lineterminator="\n")
    print(f"\nTotal: {mf.rows.sum():,} rows, {mf.size_mb.sum():.1f} MB -> {out}")


if __name__ == "__main__":
    main()
