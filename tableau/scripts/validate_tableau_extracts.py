"""
RetailPulse - validate the Tableau extracts and the extract-based final workbook (read-only).

EXTRACTS (tableau/extracts/*.hyper, opened and queried with the Tableau Hyper API)
  1  every required .hyper file exists, opens, and holds exactly its data source's tables
  2  every table's row count = CSV rows = manifest rows
  3  column names and order = CSV header; Hyper types = the types the workbook declares
  4  no data lost or changed: every value of every column equals the CSV (NULLs included),
     plus revenue reconciliation (BRL 13,494,400.74) and the 190 unobserved cohort cells
  5  the CSVs themselves are unchanged (MD5 = manifests)

WORKBOOKS (tableau/RetailPulse_Final.twb and RetailPulse_Final.twbx)
  6  every extract reference points at an existing file (absolute in the .twb, inside the
     package in the .twbx); every referenced table exists in its .hyper
  7  no live text-file (CSV) connection remains: all six data sources are extracts
  8  sort elements are declared (<SortTagCleanup />): no 'manual-sort' error D2E8DA72
  9  6 data sources + Parameters; 8 relationships; 100 calculated fields with formulas
     identical to the validated registry; 8 worksheets; 2 parameters
 10  identical to RetailPulse_repaired.twb apart from the connection layer (captions,
     calculations, relationships, worksheets, sorts, parameters)
 11  valid against Tableau's official 2026.3 XSD; every element/attribute name also occurs in
     workbooks written by Tableau (Superstore and World Indicators samples of the installed app)

WHAT THIS CANNOT PROVE: that Tableau Desktop opens the workbook and accepts it for Tableau
Public. That is the manual test (open RetailPulse_Final.twbx, then Save to Tableau Public).

Usage:
  ./venv/bin/python tableau/scripts/validate_tableau_extracts.py           # the files in tableau/
  ./venv/bin/python tableau/scripts/validate_tableau_extracts.py --fresh   # build into a temp folder first
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pandas as pd
from tableauhyperapi import Connection, HyperProcess, TableName, Telemetry

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "tableau"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tableau_registry import CALCS, DATA_SOURCES, HEADERS, PARAMETERS  # noqa: E402
import build_tableau_workbook as B                                      # noqa: E402
import validate_tableau_workbook as V                                   # noqa: E402
import repair_tableau_workbook as REP                                   # noqa: E402
from build_tableau_extracts import FINAL, SCHEMA, hyper_file            # noqa: E402

HYPER_TYPE = {"integer": "BIG_INT", "real": "DOUBLE", "string": "TEXT", "date": "DATE", "datetime": "TIMESTAMP"}
APP = Path("/Applications/Tableau Public (Apple silicon).app/Contents/help/Workbooks/en_US")
# Formulas deliberately changed after the repaired workbook, from the Tableau runtime test (2026-11-28): the LODs
# group by a key of the SAME table as the aggregated measure (Tableau error 1B885FB3 otherwise). Their new formulas
# are still checked against the registry by the formula check.
RUNTIME_FIXES = {"[RP_N07]", "[RP_N34]", "[RP_N35]"}
R: list[tuple[str, str, bool, str]] = []


def ck(area, name, ok, detail=""):
    R.append((area, name, bool(ok), detail))


def as_text(v):
    """Hyper value -> comparable text (dates/timestamps as ISO, floats via repr)."""
    if v is None:
        return None
    if type(v).__name__ in ("Date", "Timestamp"):     # Hyper API types print as 'YYYY-MM-DD[ HH:MM:SS]'
        return str(v)
    return v


def _txt(v) -> str:
    """Type-stable text for sorting rows: NULL -> '', floats via repr (exact), others via str."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    return repr(float(v)) if isinstance(v, (float, np.floating)) else str(v)


def compare(csv: Path, rows: list, cols: list[str], types: dict[str, str]) -> tuple[list[str], int]:
    df = pd.read_csv(csv, low_memory=False, keep_default_na=False, na_values=[""])
    h = pd.DataFrame(rows, columns=cols).map(as_text)
    bad = []
    if len(df) != len(h):
        return [f"rows {len(h)} != {len(df)}"], len(df)
    # order-independent comparison: sort both on all columns as exact text
    key = lambda d: np.array(["\x1f".join(_txt(v) for v in row) for row in d.itertuples(index=False)])
    df = df.iloc[np.argsort(key(df), kind="stable")].reset_index(drop=True)
    h = h.iloc[np.argsort(key(h), kind="stable")].reset_index(drop=True)
    for c in cols:
        a, b = df[c], h[c]
        if a.isna().sum() != b.isna().sum():
            bad.append(f"{c}: NULLs {b.isna().sum()} != {a.isna().sum()}")
            continue
        m = a.notna()
        if types[c] in ("integer", "real"):
            x, y = a[m].astype(float).to_numpy(), b[m].astype(float).to_numpy()
            if not np.array_equal(x, y):
                bad.append(f"{c}: {int((x != y).sum())} numeric values differ")
        else:
            x, y = a[m].astype(str).to_numpy(), b[m].astype(str).to_numpy()
            if not (x == y).all():
                bad.append(f"{c}: {int((x != y).sum())} values differ")
    return bad, len(df)


def main():
    ap = argparse.ArgumentParser(description="Validate the Tableau extracts and the final workbook")
    ap.add_argument("--fresh", action="store_true", help="build into a temporary folder first")
    args = ap.parse_args()
    tmp = tempfile.TemporaryDirectory() if args.fresh else None
    base = Path(tmp.name) if tmp else TAB
    if tmp:
        rc = subprocess.run([sys.executable, str(Path(__file__).with_name("build_tableau_extracts.py")),
                             "--out-dir", str(base)], capture_output=True, text=True)
        ck("build", "extracts and workbooks build without error", rc.returncode == 0, rc.stderr.strip()[-200:])
    ext = base / "extracts"
    data = TAB / "data"
    manifest = {**pd.read_csv(data / "_manifest.csv").set_index("object").rows.to_dict(),
                **pd.read_csv(data / "analytical" / "_manifest.csv").set_index("source").rows.to_dict()}

    # ---- CSVs untouched -------------------------------------------------------------------
    md5s = {**pd.read_csv(data / "_manifest.csv").set_index("object").md5.to_dict(),
            **pd.read_csv(data / "analytical" / "_manifest.csv").set_index("source").md5.to_dict()}
    changed = [t for t, h in md5s.items()
               if hashlib.md5(((data if (data / f"{t}.csv").exists() else data / "analytical") / f"{t}.csv")
                              .read_bytes()).hexdigest() != h]
    ck("csv", "source CSVs unchanged (MD5 = manifests)", not changed, f"{changed or 'all 14 identical'}")

    # ---- extracts --------------------------------------------------------------------------
    missing = [hyper_file(ds) for ds in DATA_SOURCES if not (ext / hyper_file(ds)).exists()]
    ck("extracts", "every required .hyper file exists (6)", not missing, f"missing: {missing or 'none'}")
    open_bad, table_bad, count_bad, schema_bad, value_bad = [], [], [], [], []
    counts = {}
    rev = cohort_nulls = None
    if not missing:
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_config": ""}) as hp:
            for ds, tables in DATA_SOURCES.items():
                m = B.SourceModel(ds, data)
                try:
                    with Connection(hp.endpoint, str(ext / hyper_file(ds))) as c:
                        found = {t.name.unescaped for t in c.catalog.get_table_names(SCHEMA)}
                        if found != {t for t, *_ in tables}:
                            table_bad.append(f"{ds}: {sorted(found)}")
                        for t, *_ in tables:
                            tn = TableName(SCHEMA, t)
                            n = c.execute_scalar_query(f"SELECT COUNT(*) FROM {tn}")
                            counts[t] = n
                            csv = m.folder_of[t] / f"{t}.csv"
                            d = c.catalog.get_table_definition(tn)
                            got = [(col.name.unescaped, str(col.type)) for col in d.columns]
                            want = [(col, HYPER_TYPE[m.types[t][col]]) for col in HEADERS[t]]
                            if got != want:
                                schema_bad.append(f"{t}: {[g for g, w in zip(got, want) if g != w][:3]}")
                            rows = c.execute_list_query(f"SELECT * FROM {tn}")
                            diffs, csv_rows = compare(csv, rows, HEADERS[t], m.types[t])
                            value_bad += [f"{t}.{e}" for e in diffs]
                            if not (n == csv_rows == manifest[t]):
                                count_bad.append(f"{t}: extract {n}, CSV {csv_rows}, manifest {manifest[t]}")
                        if ds == "RP Orders":
                            rev = c.execute_scalar_query(
                                f"SELECT SUM(order_revenue) FROM {TableName(SCHEMA, 'vw_order_summary')} "
                                "WHERE revenue_eligible = 1")
                        if ds == "RP Cohorts":
                            cohort_nulls = c.execute_scalar_query(
                                f"SELECT COUNT(*) FROM {TableName(SCHEMA, 'cohort_retention')} WHERE active_customers IS NULL")
                except Exception as e:                                    # noqa: BLE001
                    open_bad.append(f"{ds}: {type(e).__name__}: {e}")
    ck("extracts", "every .hyper opens and can be queried with the Hyper API", not open_bad and not missing,
       "; ".join(open_bad) or "6 opened")
    ck("extracts", "each .hyper holds exactly its data source's tables (schema \"Extract\")", not table_bad and not missing,
       "; ".join(table_bad) or "14 tables in 6 files")
    ck("extracts", "row counts = CSV rows = manifest rows (14 tables)", not count_bad and len(counts) == 14,
       "; ".join(count_bad) or ", ".join(f"{t} {n:,}" for t, n in counts.items()))
    ck("extracts", "column names, order and types = CSV header and workbook types", not schema_bad and len(counts) == 14,
       "; ".join(schema_bad) or "all match")
    ck("extracts", "every value of every column equals the CSV, NULLs included (no data lost or changed)",
       not value_bad and len(counts) == 14, "; ".join(value_bad[:5]) or "identical")
    ck("extracts", "eligible revenue in the extract = BRL 13,494,400.74", rev is not None and round(rev, 2) == 13494400.74,
       f"{rev:,.2f}" if rev is not None else "not computed")
    ck("extracts", "cohort extract keeps the 190 unobserved (blank) cells", cohort_nulls == 190, f"{cohort_nulls}")

    # ---- workbooks ---------------------------------------------------------------------------
    twb, twbx = base / f"{FINAL}.twb", base / f"{FINAL}.twbx"
    ck("workbook", f"{FINAL}.twb and {FINAL}.twbx exist", twb.exists() and twbx.exists())
    if not (twb.exists() and twbx.exists()):
        return finish(tmp)
    root = ET.parse(twb).getroot()
    with zipfile.ZipFile(twbx) as z:
        names = set(z.namelist())
        inner_xml = z.read(f"{FINAL}.twb") if f"{FINAL}.twb" in names else b""
    inner = ET.fromstring(inner_xml) if inner_xml else None
    ref_bad, live, hyper_tables_bad = [], [], []
    for doc, label, resolve in ((root, ".twb", lambda db: Path(db).exists()),
                                (inner, ".twbx", lambda db: db in names)):
        if doc is None:
            ref_bad.append(f"{label}: no inner workbook")
            continue
        for ds in doc.find("datasources"):
            if ds.get("name") == "Parameters":
                continue
            for c in ds.iter("connection"):
                cls = c.get("class")
                if cls == "textscan":
                    live.append(f"{label}: {ds.get('caption')}")
                if cls == "hyper" and not resolve(c.get("dbname")):
                    ref_bad.append(f"{label}: {ds.get('caption')} -> {c.get('dbname')}")
    ck("workbook", "every extract reference points at an existing file (.twb absolute, .twbx inside the package)",
       not ref_bad, "; ".join(ref_bad) or "12 references resolve")
    ck("workbook", "no live CSV connection remains: all six data sources connect to their extract", not live,
       "; ".join(live) or "6 of 6 extracts in each file")
    for ds in root.find("datasources"):
        if ds.get("name") == "Parameters":
            continue
        tables = {t for t, *_ in DATA_SOURCES[ds.get("caption")]}
        refd = {r.get("name") for r in ds.find("connection").iter("relation") if r.get("type") == "table"}
        if refd != tables:
            hyper_tables_bad.append(ds.get("caption"))
    ck("workbook", "every table the workbook references exists in its .hyper", not hyper_tables_bad,
       f"{hyper_tables_bad or 'all present'}")
    ck("workbook", "sort elements declared (<SortTagCleanup />): no 'manual-sort' error D2E8DA72",
       V.sort_flag_ok(twb) and (inner is None or "SortTagCleanup" in [c.tag for c in inner.find("document-format-change-manifest")]))
    dss = [d.get("caption") or d.get("name") for d in root.find("datasources")]
    calcs = {c.get("name"): c for d in root.find("datasources") for c in d.findall("column") if c.find("calculation") is not None
             and d.get("name") != "Parameters"}
    sheets = [w.get("name") for w in root.find("worksheets")]
    params = [c.get("caption") for d in root.find("datasources") if d.get("name") == "Parameters" for c in d.findall("column")]
    ck("workbook", "6 data sources + Parameters; 8 relationships; 8 worksheets; 2 parameters",
       sorted(dss) == sorted(list(DATA_SOURCES) + ["Parameters"]) and len(list(root.iter("relationship"))) == 8
       and len(sheets) == 8 and sorted(params) == sorted(PARAMETERS), f"{len(sheets)} sheets: {', '.join(sheets)}")
    f_bad = []
    for d in root.find("datasources"):
        if d.get("name") == "Parameters":
            continue
        cap = {c.get("name"): c.get("caption") for c in d.findall("column")}
        for c in [c for c in CALCS if c["ds"] == d.get("caption")]:
            el = calcs.get(f"[RP_{c['id']}]")
            back = el.find("calculation").get("formula").replace("[Parameters].[", "[") if el is not None else ""
            back = re.sub(r"\[([^\]]+)\]", lambda mm: f"[{cap.get('[' + mm.group(1) + ']', mm.group(1))}]", back)
            if el is None or back != c["formula"]:
                f_bad.append(c["id"])
    ck("workbook", "100 calculated fields; formulas identical to the validated registry", not f_bad and len(calcs) == 100,
       f"{f_bad or 'identical'}")
    # regression vs the repaired workbook
    rep = TAB / "RetailPulse_repaired.twb"
    if rep.exists():
        o = ET.parse(rep).getroot()

        def essence(doc):
            out = {}
            for d in doc.find("datasources"):
                cap = {c.get("name"): c.get("caption") for c in d.findall("column")}
                cols = sorted((c.get("caption"), c.get("datatype"), c.get("role"), c.get("default-format"))
                              for c in d.findall("column") if not c.get("name", "").startswith("[__tableau")
                              and c.get("name") != "[:Measure Names]")       # added 2026-11-28 (Tableau log warning)
                forms = sorted(re.sub(r"\[([^\]]+)\]", lambda mm: f"[{cap.get('[' + mm.group(1) + ']', mm.group(1))}]",
                                      c.find("calculation").get("formula"))
                               for c in d.findall("column") if c.find("calculation") is not None
                               and c.get("name") not in RUNTIME_FIXES)
                rels = sorted(tuple(re.sub(r" \(.*\)\]$", "]", e.get("op")) for e in r.find("expression"))
                              for r in d.iter("relationship"))
                out[d.get("caption") or d.get("name")] = (cols, forms, rels)
            sh = [(w.get("name"), [(s.get("column"), s.get("direction"), [b.text for b in s.iter("bucket")])
                                   for s in w.iter("manual-sort")]) for w in doc.find("worksheets")]
            return out, sh
        ck("workbook", "identical to RetailPulse_repaired.twb apart from the connection layer and the 3 documented "
           "runtime fixes (captions, types, formats, calculations, relationships, worksheets, sorts, parameters)",
           essence(o) == essence(root))
    bad, waived = V.xsd_errors(twb)
    ck("workbook", "valid against Tableau's official 2026.3 XSD", not bad, (bad[0] if bad else "no errors")
       + (" (waived: missing <explain-data>, also absent from files Tableau writes)" if waived else ""))
    refs = []
    for name in ("Superstore.twbx", "World Indicators.twbx"):
        p = APP / name
        if p.exists():
            with zipfile.ZipFile(p) as z:
                refs.append(REP.parse(z.read(next(n for n in z.namelist() if n.endswith(".twb")))))
    rt, ra = set(), set()
    for t in refs:
        a, b = REP.vocabulary(t)
        rt |= a
        ra |= b
    tags, attrs = REP.vocabulary(REP.parse(twb))
    # written by Tableau 2026.3.2 itself in the owner's autosave (and defined in the 2026.3 XSD), though
    # absent from the two older bundled samples
    attrs -= {("workbook", "original-version")}
    ck("workbook", "every element/attribute name also occurs in workbooks written by Tableau",
       refs and not (tags - rt) and not (attrs - ra),
       f"unknown: {sorted(tags - rt) + sorted(attrs - ra) or 'none'} ({len(refs)} references)" if refs
       else "reference samples not found")
    return finish(tmp)


def finish(tmp):
    for area, name, ok, detail in R:
        print(f"  {'PASS' if ok else 'FAIL'}  [{area}] {name}" + (f"  — {detail}" if detail else ""))
    n = sum(r[2] for r in R)
    print(f"checks: {len(R)}   PASS: {n}   FAIL: {len(R) - n}")
    print("SCOPE: extracts queried with the Hyper API and compared with the CSVs; workbooks checked as XML. "
          "NOT verified: that Tableau Desktop opens the workbook and accepts it for Tableau Public (manual).")
    if tmp:
        tmp.cleanup()
    sys.exit(0 if n == len(R) else 1)


if __name__ == "__main__":
    main()
