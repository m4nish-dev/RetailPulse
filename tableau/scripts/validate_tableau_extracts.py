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
  7  no live text-file (CSV) connection remains: every data source is an extract
  8  sort elements are declared (<SortTagCleanup />): no 'manual-sort' error D2E8DA72
  9  10 Tableau data sources (two-table views of the 6 registry data sources) + Parameters;
     8 relationships; all 100 calculated fields with formulas identical to the validated
     registry; 49 worksheets; 8 dashboards; 2 parameters; every dashboard zone, filter
     control, parameter control and action resolves
 10  nothing lost from RetailPulse_repaired.twb (captions, types, formats, calculations,
     relationships, KPI sheet sorts)
 11  valid against Tableau's official 2026.3 XSD; every element/attribute name also occurs in
     workbooks written by Tableau (Superstore and World Indicators samples of the installed app)

WHAT THIS CANNOT PROVE: that Tableau Desktop opens and draws the workbook. That is checked in
Tableau itself by tableau/scripts/tableau_runtime_check.py; saving to Tableau Public needs the
owner's sign-in.

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
import tableau_charts as C                                              # noqa: E402
import validate_tableau_workbook as V                                   # noqa: E402
import repair_tableau_workbook as REP                                   # noqa: E402
from build_tableau_extracts import FINAL, SCHEMA, hyper_file            # noqa: E402

HYPER_TYPE = {"integer": "BIG_INT", "real": "DOUBLE", "string": "TEXT", "date": "DATE", "datetime": "TIMESTAMP"}
APP = Path("/Applications/Tableau Public (Apple silicon).app/Contents/help/Workbooks/en_US")
# Formulas deliberately changed after the repaired workbook, from the Tableau runtime test (2026-11-28): the LODs
# group by a key of the SAME table as the aggregated measure (Tableau error 1B885FB3 otherwise). Their new formulas
# are still checked against the registry by the formula check.
RUNTIME_FIXES = {"[RP_N07]", "[RP_N34]", "[RP_N35]"}
# 0/1 flag shown as a dimension with aliases (One-time / Repeat) on chart 2.1
ROLE_CHANGES = {"is_repeat_customer"}
RUNTIME_VERIFIED_TAGS = {"wedge-size"}                                   # pie chart 2.1
RUNTIME_VERIFIED_ATTRS = {("wedge-size", "column"), ("size", "maxwidth")}  # pie 2.1; fixed dashboard size
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
       not ref_bad, "; ".join(ref_bad) or "all references resolve")
    ck("workbook", "no live CSV connection remains: every data source connects to an extract", not live,
       "; ".join(live) or "all data sources are extracts in each file")
    for ds in root.find("datasources"):
        if ds.get("name") == "Parameters":
            continue
        reg, subset = C.SOURCES[ds.get("caption")]
        tables = {t for t, *_ in DATA_SOURCES[reg]} if subset is None else set(subset)
        refd = {r.get("name") for r in ds.find("connection").iter("relation") if r.get("type") == "table"}
        dbs = {Path(c.get("dbname")).name for c in ds.iter("connection") if c.get("class") == "hyper"}
        if refd != tables or dbs != {hyper_file(reg)}:
            hyper_tables_bad.append(ds.get("caption"))
    ck("workbook", "every table the workbook references exists in its .hyper (each Tableau data source reads its "
       "registry data source's extract)", not hyper_tables_bad, f"{hyper_tables_bad or 'all present'}")
    ck("workbook", "sort elements declared (<SortTagCleanup />): no 'manual-sort' error D2E8DA72",
       V.sort_flag_ok(twb) and (inner is None or "SortTagCleanup" in [c.tag for c in inner.find("document-format-change-manifest")]))
    dss = [d.get("caption") or d.get("name") for d in root.find("datasources")]
    sheets = [w.get("name") for w in root.find("worksheets")]
    dashes = [d.get("name") for d in root.find("dashboards")] if root.find("dashboards") is not None else []
    params = [c.get("caption") for d in root.find("datasources") if d.get("name") == "Parameters" for c in d.findall("column")]
    want_sheets = sorted([s for s, *_ in B.KPI_SHEETS] + [c["name"] for c in C.CHARTS])
    ck("workbook", f"{len(C.SOURCES)} Tableau data sources + Parameters; 8 relationships; {len(want_sheets)} worksheets "
       f"(8 KPI + {len(C.CHARTS)} charts); {len(C.DASHBOARDS)} dashboards; 2 parameters",
       sorted(dss) == sorted(list(C.SOURCES) + ["Parameters"]) and len(list(root.iter("relationship"))) == 8
       and sorted(sheets) == want_sheets and sorted(dashes) == sorted(d["name"] for d in C.DASHBOARDS)
       and sorted(params) == sorted(PARAMETERS), f"{len(dss) - 1} data sources, {len(sheets)} sheets, {len(dashes)} dashboards")
    f_bad, covered = [], set()
    by_id = {c["id"]: c for c in CALCS}
    for d in root.find("datasources"):
        if d.get("name") == "Parameters":
            continue
        reg = C.SOURCES[d.get("caption")][0]
        cap = {c.get("name"): c.get("caption") for c in d.findall("column")}
        for el in d.findall("column"):
            if el.find("calculation") is None or el.find("calculation").get("class") != "tableau":
                continue
            cid = el.get("name")[4:-1]
            c = by_id.get(cid)
            back = el.find("calculation").get("formula").replace("[Parameters].[", "[")
            back = re.sub(r"\[([^\]]+)\]", lambda mm: f"[{cap.get('[' + mm.group(1) + ']', mm.group(1))}]", back)
            if c is None or c["ds"] != reg or back != c["formula"] or el.get("caption") != c["name"]:
                f_bad.append(f"{d.get('caption')}:{cid}")
            else:
                covered.add(cid)
    ck("workbook", "all 100 calculated fields present (each in every Tableau data source that has its inputs); "
       "formulas identical to the validated registry", not f_bad and covered == set(by_id),
       f"{f_bad[:5] or 'identical'}; covered {len(covered)}/{len(by_id)}")
    # references: dashboards -> worksheets, filter controls -> sheet filters, actions -> sheets/dashboards, windows
    ref_bad = []
    ws_by = {w.get("name"): w for w in root.find("worksheets")}
    for d in root.find("dashboards"):
        for z in d.iter("zone"):
            n, t = z.get("name"), z.get("type-v2")
            if n and n not in ws_by:
                ref_bad.append(f"{d.get('name')}: zone -> {n}")
            if t == "filter":
                cols = {f.get("column") for f in ws_by[n].iter("filter")} if n in ws_by else set()
                if z.get("param") not in cols:
                    ref_bad.append(f"{d.get('name')}: filter control {z.get('param')} not on {n}")
            if t == "paramctrl" and z.get("param", "").replace("[Parameters].[", "").rstrip("]") not in PARAMETERS:
                ref_bad.append(f"{d.get('name')}: parameter control {z.get('param')}")
    for a in root.find("actions"):
        src = a.find("source")
        if src.get("dashboard") not in dashes or (src.get("worksheet") and src.get("worksheet") not in ws_by):
            ref_bad.append(f"action {a.get('caption')}: source")
        for e in src.findall("exclude-sheet"):
            if e.get("name") not in ws_by:
                ref_bad.append(f"action {a.get('caption')}: exclude-sheet {e.get('name')}")
        for prm in a.iter("param"):
            if prm.get("name") == "target" and prm.get("value") not in dashes:
                ref_bad.append(f"action {a.get('caption')}: target {prm.get('value')}")
            if prm.get("name") == "exclude":
                ref_bad += [f"action {a.get('caption')}: exclude {x}" for x in prm.get("value").split(",")
                            if x and x not in ws_by]
    wins = {w.get("name") for w in root.find("windows")}
    ref_bad += [f"no window for {n}" for n in sheets + dashes if n not in wins]
    on_dash = {z.get("name") for d in root.find("dashboards") for z in d.iter("zone") if z.get("name")}
    ref_bad += [f"{n} is on no dashboard" for n in sheets if n not in on_dash]
    ck("workbook", "every dashboard zone, filter control, parameter control and action points at an existing "
       "worksheet / dashboard / filter / parameter; every sheet is on a dashboard and has a window",
       not ref_bad, "; ".join(ref_bad[:5]) or f"{len(on_dash)} zones, {len(list(root.find('actions')))} actions resolve")
    # regression vs the repaired workbook (per registry data source: union of its Tableau data sources)
    rep = TAB / "RetailPulse_repaired.twb"
    if rep.exists():
        o = ET.parse(rep).getroot()

        def essence(doc, split):
            out = {}
            for d in doc.find("datasources"):
                name = d.get("caption") or d.get("name")
                reg = C.SOURCES[name][0] if split and name in C.SOURCES else name
                cap = {c.get("name"): c.get("caption") for c in d.findall("column")}
                cols = {(c.get("caption"), c.get("datatype"), c.get("default-format"),
                         "role-allowed" if c.get("caption") in ROLE_CHANGES else c.get("role"))
                        for c in d.findall("column") if not c.get("name", "").startswith("[__tableau")
                        and c.get("name") != "[:Measure Names]" and not c.get("name", "").endswith(" (bin)]")}
                forms = {re.sub(r"\[([^\]]+)\]", lambda mm: f"[{cap.get('[' + mm.group(1) + ']', mm.group(1))}]",
                                c.find("calculation").get("formula"))
                         for c in d.findall("column") if c.find("calculation") is not None
                         and c.find("calculation").get("class") == "tableau" and c.get("name") not in RUNTIME_FIXES
                         and d.get("name") != "Parameters"}
                rels = {tuple(re.sub(r" \(.*\)\]$", "]", e.get("op")) for e in r.find("expression"))
                        for r in d.iter("relationship")}
                prev = out.setdefault(reg, (set(), set(), set()))
                out[reg] = (prev[0] | cols, prev[1] | forms, prev[2] | rels)
            sh = {w.get("name"): [re.sub(r"\[federated\.[a-z0-9]+\]", "[ds]", b.text)
                                  for s in w.iter("manual-sort") for b in s.iter("bucket")]
                  for w in doc.find("worksheets") if w.get("name") in {k for k, *_ in B.KPI_SHEETS}}
            return out, sh
        e_old, e_new = essence(o, False), essence(root, True)
        diff = [k for k in e_old[0] if e_old[0][k] != e_new[0].get(k)] + \
               [k for k in e_old[1] if e_old[1][k] != e_new[1].get(k)]
        ck("workbook", "nothing lost from RetailPulse_repaired.twb: every field (caption, type, format), formula, "
           "relationship and KPI sheet sort is still present (connection layer, data-source split, the 3 documented "
           "runtime fixes and the is_repeat_customer role excepted)", not diff, f"{diff or 'all preserved'}")
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
    # names absent from the two samples but defined in the 2026.3 XSD and exercised in Tableau 2026.3.2 by
    # tableau/scripts/tableau_runtime_check.py (top-N filters, pie wedges, bins, list parameters, fixed size)
    tags -= RUNTIME_VERIFIED_TAGS
    attrs -= RUNTIME_VERIFIED_ATTRS
    ck("workbook", "every element/attribute name occurs in workbooks written by Tableau, or is defined in the XSD and "
       "exercised in the Tableau runtime test", refs and not (tags - rt) and not (attrs - ra),
       f"unknown: {sorted(tags - rt) + sorted(attrs - ra) or 'none'} ({len(refs)} references)" if refs
       else "reference samples not found")
    return finish(tmp)


def finish(tmp):
    for area, name, ok, detail in R:
        print(f"  {'PASS' if ok else 'FAIL'}  [{area}] {name}" + (f"  — {detail}" if detail else ""))
    n = sum(r[2] for r in R)
    print(f"checks: {len(R)}   PASS: {n}   FAIL: {len(R) - n}")
    print("SCOPE: extracts queried with the Hyper API and compared with the CSVs; workbooks checked as XML. "
          "Tableau itself: tableau/scripts/tableau_runtime_check.py (launches Tableau, run separately).")
    if tmp:
        tmp.cleanup()
    sys.exit(0 if n == len(R) else 1)


if __name__ == "__main__":
    main()
