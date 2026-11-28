"""
RetailPulse - build Tableau extracts (.hyper) from the CSVs and the extract-based final workbook.

WHY
  Tableau Public only saves workbooks whose data sources are extracts (error 3C242D89:
  "Workbooks saved to Tableau Public must use extracts. The data source, RP Cohorts, is
  not an extract."). All six data sources of the generated workbook were live text-file
  connections.

WHAT IT WRITES (all git-ignored: they contain data or this Mac's paths)
  tableau/extracts/RP_Orders.hyper, RP_Customers.hyper, RP_Cohorts.hyper,
                   RP_Categories.hyper, RP_Sellers.hyper, RP_Stage_Summary.hyper
      one file per data source; every table of the data source in schema "Extract",
      loaded with Hyper's own CSV reader (COPY): no row, column or value is changed,
      empty CSV fields stay NULL
  tableau/RetailPulse_Final.twbx
      packaged workbook: RetailPulse_Final.twb + Data/extracts/*.hyper, with package-relative
      paths. The portable file to open, save and publish.
  tableau/RetailPulse_Final.twb
      the same workbook pointing at tableau/extracts/*.hyper by absolute path (this Mac)

  The workbook comes from the same registry and generator as before
  (scripts/build_tableau_workbook.py): identical fields, captions, relationships, 100
  calculated fields, 2 parameters, 8 KPI check sheets and the sort-format declaration.
  Only the connection layer differs: each data source connects to its .hyper file, the
  pattern Tableau itself uses in the World Indicators sample shipped with Tableau Public
  (class='hyper', tables in schema "Extract", package-relative dbname in the .twbx).

SAFETY
  Reads the CSVs only; never modifies them, the database or any other workbook.
  RetailPulse_repaired.twb is left untouched (a byte copy is kept as
  RetailPulse_repaired.twb.backup). Hyper usage data is NOT sent to Tableau.

Usage:
  ./venv/bin/python tableau/scripts/build_tableau_extracts.py
  ./venv/bin/python tableau/scripts/build_tableau_extracts.py --out-dir /tmp/x   # build elsewhere (tests)
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import sys
import zipfile

from tableauhyperapi import (Connection, CreateMode, HyperProcess, Nullability, SqlType, TableDefinition,
                             TableName, Telemetry, escape_string_literal)

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "tableau"
sys.path.insert(0, str(ROOT / "scripts"))
from tableau_registry import DATA_SOURCES  # noqa: E402
import build_tableau_workbook as B          # noqa: E402

SCHEMA = B.HYPER_SCHEMA
SQL_TYPE = {"integer": SqlType.big_int(), "real": SqlType.double(), "string": SqlType.text(),
            "date": SqlType.date(), "datetime": SqlType.timestamp()}
FINAL = "RetailPulse_Final"


def hyper_file(ds: str) -> str:
    return ds.replace(" ", "_") + ".hyper"


def build_extract(hp: HyperProcess, ds: str, data_dir: Path, out: Path) -> dict[str, int]:
    """One .hyper per data source; returns {table: rows loaded}."""
    m = B.SourceModel(ds, data_dir)                  # same types the workbook declares
    loaded = {}
    with Connection(hp.endpoint, str(out), CreateMode.CREATE_AND_REPLACE) as conn:
        conn.catalog.create_schema(SCHEMA)
        for t, *_ in m.tables:
            cols = [TableDefinition.Column(c, SQL_TYPE[m.types[t][c]], Nullability.NULLABLE)
                    for c in B.HEADERS[t]]
            table = TableDefinition(TableName(SCHEMA, t), cols)
            conn.catalog.create_table(table)
            csv = m.folder_of[t] / f"{t}.csv"
            loaded[t] = conn.execute_command(
                f"COPY {table.table_name} FROM {escape_string_literal(str(csv))} "
                f"WITH (FORMAT CSV, HEADER, DELIMITER ',', QUOTE '\"', NULL '')")
    return loaded


def main():
    ap = argparse.ArgumentParser(description="Build Tableau extracts and the extract-based workbook")
    ap.add_argument("--data-dir", type=Path, default=TAB / "data")
    ap.add_argument("--out-dir", type=Path, default=TAB, help="writes <out>/extracts/*.hyper and <out>/RetailPulse_Final.*")
    args = ap.parse_args()
    data_dir, out = args.data_dir.resolve(), args.out_dir.resolve()
    ext_dir = out / "extracts"
    ext_dir.mkdir(parents=True, exist_ok=True)

    # keep the working repaired workbook recoverable (never modified by this script)
    repaired = TAB / "RetailPulse_repaired.twb"
    backup = TAB / "RetailPulse_repaired.twb.backup"
    if out == TAB and repaired.exists() and not backup.exists():
        shutil.copy2(repaired, backup)

    # 1. extracts
    params = {"log_config": ""}                      # no hyperd log files in the project folder
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters=params) as hp:
        for ds in DATA_SOURCES:
            loaded = build_extract(hp, ds, data_dir, ext_dir / hyper_file(ds))
            size = (ext_dir / hyper_file(ds)).stat().st_size / 1024 ** 2
            print(f"  {hyper_file(ds):<24} {size:6.1f} MB  " + ", ".join(f"{t} {n:,}" for t, n in loaded.items()))

    # 2. workbook pointing at the extracts (absolute paths) ...
    abs_dbs = {ds: str(ext_dir / hyper_file(ds)) for ds in DATA_SOURCES}
    twb = out / f"{FINAL}.twb"
    B.write(B.build(data_dir, True, hyper_dbs=abs_dbs), twb)
    # ... and the portable packaged workbook (package-relative paths, like Tableau's own .twbx)
    rel_dbs = {ds: f"Data/extracts/{hyper_file(ds)}" for ds in DATA_SOURCES}
    inner = out / f".{FINAL}.inner.twb"
    B.write(B.build(data_dir, True, hyper_dbs=rel_dbs), inner)
    twbx = out / f"{FINAL}.twbx"
    with zipfile.ZipFile(twbx, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(inner, f"{FINAL}.twb")
        for ds in DATA_SOURCES:
            z.write(ext_dir / hyper_file(ds), rel_dbs[ds])
    inner.unlink()
    for p in (twb, twbx):
        print(f"wrote {p.relative_to(ROOT) if p.is_relative_to(ROOT) else p}  ({p.stat().st_size / 1024 ** 2:.1f} MB)")


if __name__ == "__main__":
    main()
