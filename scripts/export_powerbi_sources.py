"""
RetailPulse - export the Power BI analytical data sources (fix-Phase 3).

Runs the read-only queries in sql/09_powerbi_sources.sql and writes one CSV per
source into powerbi/data/analytical/, plus _manifest.csv.

SAFETY
  * The SQL file is split on "-- @source: <name>" markers. Every statement is
    checked before it runs: it must start with SELECT or WITH and must not
    contain any data-definition or data-modification keyword. Anything else
    aborts the export before touching the database.
  * The connection is opened READ ONLY (SET SESSION TRANSACTION READ ONLY), so
    even a statement that slipped past the check could not write.
  * Output goes only to powerbi/data/analytical/. Existing files there are
    overwritten (they are generated artefacts); nothing else is touched.

CSV conventions (Power BI friendly)
  UTF-8, comma-separated, header row, '.' decimal point, dates as YYYY-MM-DD,
  flags as 0/1, NULL as an empty field.

Usage:  ./venv/bin/python scripts/export_powerbi_sources.py
"""
from pathlib import Path
import hashlib
import re
import sys

import pandas as pd

try:
    import mysql.connector
except ImportError:
    sys.exit("mysql-connector-python not installed:  pip install mysql-connector-python")

ROOT = Path(__file__).resolve().parent.parent
SQL_FILE = ROOT / "sql" / "09_powerbi_sources.sql"
OUT = ROOT / "powerbi" / "data" / "analytical"

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|REPLACE|MERGE|DROP|CREATE|ALTER|TRUNCATE|RENAME|"
    r"GRANT|REVOKE|LOAD|CALL|HANDLER|LOCK|SET\s+GLOBAL|INTO\s+OUTFILE)\b", re.I)


def strip_comments(sql: str) -> str:
    return "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))


def load_sources() -> dict[str, str]:
    text = SQL_FILE.read_text(encoding="utf-8")
    parts = re.split(r"^--\s*@source:\s*(\w+)\s*$", text, flags=re.M)
    sources = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        sql = strip_comments(body).strip().rstrip(";").strip()
        if not re.match(r"^(SELECT|WITH)\b", sql, re.I):
            sys.exit(f"ABORT: source '{name}' is not a SELECT/WITH query")
        if FORBIDDEN.search(sql):
            sys.exit(f"ABORT: source '{name}' contains a forbidden keyword: "
                     f"{FORBIDDEN.search(sql).group(0)}")
        if ";" in sql:
            sys.exit(f"ABORT: source '{name}' contains more than one statement")
        sources[name] = sql
    if not sources:
        sys.exit("ABORT: no '-- @source:' markers found")
    return sources


def run(conn, sql: str) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    # dtype=object keeps the driver's Python types; otherwise pandas turns an
    # integer column containing NULLs into float and writes "160.0".
    df = pd.DataFrame(cur.fetchall(), columns=cols, dtype=object)
    cur.close()
    for c in df.columns:
        vals = df[c].dropna()
        if len(vals) and all(isinstance(v, int) and not isinstance(v, bool) for v in vals):
            df[c] = df[c].astype("Int64")           # nullable integer: "160", or empty
    return df


def main() -> None:
    sources = load_sources()
    try:
        conn = mysql.connector.connect(host="127.0.0.1", user="root",
                                       database="retailpulse")
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"Cannot reach MySQL ({type(e).__name__}). "
                 "Start it with:  brew services start mysql@8.4")
    cur = conn.cursor()
    cur.execute("SET SESSION TRANSACTION READ ONLY")
    cur.execute("SET SESSION cte_max_recursion_depth = 100")
    cur.close()

    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, sql in sources.items():
        df = run(conn, sql)
        path = OUT / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
        md5 = hashlib.md5(path.read_bytes()).hexdigest()
        mb = path.stat().st_size / 1024**2
        manifest.append({"source": name, "rows": len(df), "columns": df.shape[1],
                         "size_mb": round(mb, 3), "md5": md5})
        print(f"  {name:<30}{len(df):>9,} rows x {df.shape[1]:>2} cols   {mb:>6.2f} MB")
    conn.close()

    mf = pd.DataFrame(manifest)
    mf.to_csv(OUT / "_manifest.csv", index=False, lineterminator="\n")
    print(f"\n{len(mf)} sources, {mf.rows.sum():,} rows, {mf.size_mb.sum():.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
