"""
RetailPulse - export the analytical data sources of the Tableau dashboard.

Runs the read-only queries in sql/09_dashboard_sources.sql and writes one CSV per
source into tableau/data/analytical/, plus _manifest.csv (rows, columns, size, MD5).

SAFETY
  * The SQL file is split on "-- @source: <name>" markers. Every statement is
    checked before it runs: it must start with SELECT or WITH and must not
    contain any data-definition or data-modification keyword. Anything else
    aborts the export before touching the database.
  * The connection uses the read-only application account (scripts/rp_db.py,
    credentials from .env) in a READ ONLY session, so even a statement that
    slipped past the check could not write.
  * Output goes only to the output folder (default tableau/data/analytical/).
    Existing files there are overwritten (they are generated artefacts);
    nothing else is touched. Never run by scripts/run_all_validations.py.

CSV conventions (Tableau text-file connector)
  UTF-8, comma-separated, header row, '.' decimal point, dates as YYYY-MM-DD,
  flags as 0/1, NULL as an empty field.

Usage:
  ./venv/bin/python scripts/export_tableau_sources.py                # writes tableau/data/analytical/
  ./venv/bin/python scripts/export_tableau_sources.py --out /tmp/x   # writes elsewhere (e.g. to compare)
"""
from pathlib import Path
import argparse
import hashlib
import re
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rp_db import ConfigError, get_connection                 # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SQL_FILE = ROOT / "sql" / "09_dashboard_sources.sql"
DEFAULT_OUT = ROOT / "tableau" / "data" / "analytical"

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
    ap = argparse.ArgumentParser(description="Export the dashboard analytical sources")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output folder (default tableau/data/analytical/)")
    out = ap.parse_args().out
    sources = load_sources()
    try:
        conn = get_connection(read_only=True)                 # app account from .env
    except ConfigError as e:
        sys.exit(f"CONFIG ERROR: {e}")
    cur = conn.cursor()
    cur.execute("SET SESSION cte_max_recursion_depth = 100")
    cur.close()

    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, sql in sources.items():
        df = run(conn, sql)
        path = out / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
        md5 = hashlib.md5(path.read_bytes()).hexdigest()
        mb = path.stat().st_size / 1024**2
        manifest.append({"source": name, "rows": len(df), "columns": df.shape[1],
                         "size_mb": round(mb, 3), "md5": md5})
        print(f"  {name:<30}{len(df):>9,} rows x {df.shape[1]:>2} cols   {mb:>6.2f} MB")
    conn.close()

    mf = pd.DataFrame(manifest)
    mf.to_csv(out / "_manifest.csv", index=False, lineterminator="\n")
    print(f"\n{len(mf)} sources, {mf.rows.sum():,} rows, {mf.size_mb.sum():.1f} MB -> {out}")


if __name__ == "__main__":
    main()
