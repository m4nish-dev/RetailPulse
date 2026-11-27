"""
RetailPulse - validate the generated Tableau workbook (read-only for the project).

Builds both workbooks into a temporary folder with scripts/build_tableau_workbook.py,
then checks them:

  SCHEMA     both files against Tableau's official 2026.3 XSD
             (tableau/schema/twb_2026.3.0.xsd). One schema rule is waived: the
             XSD lists <explain-data> as required, but workbooks saved by
             Tableau 2026.3.2 itself (and its bundled Superstore sample) omit
             it. Every other schema error fails the check.
  DATA       each connection points at an existing folder; each table's
             columns equal the CSV header in order; each declared type holds
             for every value in the CSV
  MODEL      6 data sources + Parameters; the 8 relationships of
             tableau/data_model.md (root table to related table, keys present
             on both sides); captions equal the documented field names
  FORMULAS   the 100 calculated fields: every formula, translated back to
             display names, is character-for-character the formula validated
             by scripts/validate_tableau_calcs.py; every reference resolves;
             number formats set; 2 parameters
  SHEETS     the 8 KPI check sheets: every column they use is declared,
             every Measure Names member points at a declared instance, every
             sheet has a window
  OTHER      no credentials in the file; generation is deterministic

WHAT THIS CANNOT PROVE: that Tableau opens the file and computes the
values. Tableau's own documentation: passing the XSD is syntactic validation
only. Opening the workbook in Tableau Desktop (manual step) is the proof.

Usage:  ./venv/bin/python scripts/validate_tableau_workbook.py
Exit code 1 on any failure.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tableau_registry import CALCS, DATA_SOURCES, FIELDS, HEADERS, PARAMETERS, TAB  # noqa: E402
import build_tableau_workbook as B                                              # noqa: E402

ROOT = TAB.parent
XSD = TAB / "schema" / "twb_2026.3.0.xsd"
WAIVED = ["Missing child element(s). Expected is one of ( datagraph, thumbnails, external, referenced-extensions, "
          "explain-data )", "Missing child element(s). Expected is one of ( thumbnails, external, "
          "referenced-extensions, explain-data )", "Missing child element(s). Expected is ( explain-data )"]
R: list[tuple[str, str, bool, str]] = []


def ck(area, name, ok, detail=""):
    R.append((area, name, bool(ok), detail))


def xsd_errors(path: Path) -> tuple[list[str], list[str]]:
    from lxml import etree
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "user_stub.xsd").write_text(
            '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.tableausoftware.com/xml/user">'
            '<xs:attributeGroup name="UserAttributes-AG"><xs:anyAttribute namespace="##targetNamespace" processContents="lax"/>'
            '</xs:attributeGroup></xs:schema>')
        (t / "xml_stub.xsd").write_text(
            '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.w3.org/XML/1998/namespace">'
            '<xs:attribute name="base" type="xs:anyURI"/><xs:attribute name="lang" type="xs:language"/>'
            '<xs:attribute name="space" type="xs:NCName"/></xs:schema>')
        text = XSD.read_text(encoding="utf-8")
        text = text.replace('<xs:import namespace="http://www.tableausoftware.com/xml/user"/>',
                            '<xs:import namespace="http://www.tableausoftware.com/xml/user" schemaLocation="user_stub.xsd"/>')
        text = text.replace('<xs:import namespace="http://www.w3.org/XML/1998/namespace"/>',
                            '<xs:import namespace="http://www.w3.org/XML/1998/namespace" schemaLocation="xml_stub.xsd"/>')
        (t / "twb.xsd").write_text(text, encoding="utf-8")
        schema = etree.XMLSchema(etree.parse(str(t / "twb.xsd")))
    schema.validate(etree.parse(str(path)))
    errors = [f"line {e.line}: {e.message}" for e in schema.error_log]
    waived = [e for e in errors if any(w in e for w in WAIVED) and "Element 'workbook'" in e]
    return [e for e in errors if e not in waived], waived


def sort_flag_ok(path: Path) -> bool:
    """<manual-sort>/<computed-sort>/<natural-sort> are only read by Tableau when the manifest declares
    SortTagCleanup (otherwise: error D2E8DA72, 'No declaration found for element manual-sort')."""
    root = ET.parse(path).getroot()
    uses = any(True for tag in ("manual-sort", "computed-sort", "natural-sort") for _ in root.iter(tag))
    declared = any(c.tag.split("...")[-1] == "SortTagCleanup" for c in root.find("document-format-change-manifest"))
    return declared or not uses


def holds(series: pd.Series, dtype: str) -> bool:
    v = series.dropna()
    if dtype == "integer":
        return pd.api.types.is_integer_dtype(series) or (pd.to_numeric(v, errors="coerce") % 1 == 0).all()
    if dtype == "real":
        return pd.to_numeric(v, errors="coerce").notna().all()
    if dtype == "date":
        return v.astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}").all() and pd.to_datetime(v, errors="coerce").notna().all()
    if dtype == "datetime":
        return pd.to_datetime(v, errors="coerce").notna().all()
    return True


def main():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        rc = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_tableau_workbook.py"), "--out-dir", str(out)],
                            capture_output=True, text=True)
        ck("build", "workbooks generate without error", rc.returncode == 0, rc.stderr.strip()[-200:])
        if rc.returncode:
            return finish()
        files = {"RetailPulse.twb": out / "RetailPulse.twb", "RetailPulse_model_only.twb": out / "RetailPulse_model_only.twb"}
        again = Path(tmp) / "again"
        again.mkdir()
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_tableau_workbook.py"), "--out-dir", str(again)],
                       capture_output=True, text=True)
        ck("build", "generation is deterministic (two builds byte-identical)",
           all((again / n).read_bytes() == p.read_bytes() for n, p in files.items()))

        # ---- schema ------------------------------------------------------------------------
        for name, path in files.items():
            bad, waived = xsd_errors(path)
            ck("schema", f"{name}: valid against Tableau's 2026.3 XSD", not bad,
               ("; ".join(bad[:3]) if bad else "no errors") + (f" (waived: {len(waived)} missing <explain-data>, "
                                                               "also absent from files Tableau 2026.3.2 writes)" if waived else ""))

        tree = ET.parse(files["RetailPulse.twb"])
        wb = tree.getroot()
        ck("model", "workbook version and build match the installed Tableau 2026.3.2",
           wb.get("version") == B.VERSION and wb.get("source-build") == B.SOURCE_BUILD)
        ds_els = {d.get("caption") or d.get("name"): d for d in wb.find("datasources")}
        ck("model", "6 data sources + Parameters, named as in data_model.md",
           set(ds_els) == set(DATA_SOURCES) | {"Parameters"}, f"{sorted(ds_els)}")

        # ---- per data source -------------------------------------------------------------------
        data_bad, rel_bad, cap_bad, f_bad, ref_bad, fmt_bad = [], [], [], [], [], []
        n_rel = n_calc = 0
        for ds, tables in DATA_SOURCES.items():
            d = ds_els[ds]
            conn = d.find("connection")
            folders = {nc.get("name"): Path(nc.find("connection").get("directory"))
                       for nc in conn.find("named-connections")}
            for nc_name, folder in folders.items():
                if not folder.is_dir():
                    data_bad.append(f"{ds}: folder missing {folder}")
            rels = conn.findall(".//relation[@type='table']")
            for rel in rels:
                t = rel.get("name")[:-4]
                folder = folders[rel.get("connection")]
                csv = folder / f"{t}.csv"
                if not csv.exists():
                    data_bad.append(f"{ds}: {csv} missing")
                    continue
                declared = [(c.get("name"), c.get("datatype")) for c in rel.find("columns")]
                if [n for n, _ in declared] != HEADERS[t]:
                    data_bad.append(f"{ds}.{t}: columns differ from the CSV header")
                df = pd.read_csv(csv, low_memory=False)
                for n, dt in declared:
                    if not holds(df[n], dt):
                        data_bad.append(f"{ds}.{t}.{n}: values do not fit {dt}")
            if {r.get("name")[:-4] for r in rels} != {t for t, *_ in tables}:
                data_bad.append(f"{ds}: tables differ from the registry")

            cols = {c.get("name"): c for c in d.findall("column")}
            locals_ = {}
            for mr in conn.find("metadata-records").findall("metadata-record[@class='column']"):
                locals_[mr.findtext("local-name")] = mr.findtext("parent-name")[1:-5]
            # relationships
            og = d.find("object-graph")
            if len(tables) > 1:
                objs = {o.get("id"): o.get("caption")[:-4] for o in og.find("objects")}
                for rel in og.find("relationships"):
                    n_rel += 1
                    l_tbl = objs.get(rel.find("first-end-point").get("object-id"))
                    r_tbl = objs.get(rel.find("second-end-point").get("object-id"))
                    exprs = [e.get("op") for e in rel.find("expression")]
                    want = next(((t, k) for t, _, k, _ in tables[1:] if t == r_tbl), None)
                    if l_tbl != tables[0][0] or want is None:
                        rel_bad.append(f"{ds}: {l_tbl} -> {r_tbl} not in the model")
                        continue
                    if locals_.get(exprs[0]) != l_tbl or locals_.get(exprs[1]) != r_tbl \
                            or exprs[0] != f"[{want[1]}]" or not exprs[1].startswith(f"[{want[1]}"):
                        rel_bad.append(f"{ds}: {l_tbl}->{r_tbl} keys {exprs}")
                if len(og.find("relationships")) != len(tables) - 1:
                    rel_bad.append(f"{ds}: expected {len(tables) - 1} relationships")
            # captions
            want_caps = {f"[{col}]" if True else None: cap for cap, (tbl, col) in FIELDS[ds].items()}
            m = B.SourceModel(ds, (TAB / "data"))
            for t, col, internal, caption, dtype, _ in m.columns:
                el = cols.get(internal)
                if el is None or el.get("caption") != caption:
                    cap_bad.append(f"{ds}: {internal} caption {el.get('caption') if el is not None else 'missing'} != {caption}")
            caps = [c.get("caption") for c in cols.values() if not c.get("name").startswith("[__tableau")]
            if len(caps) != len(set(caps)):
                cap_bad.append(f"{ds}: duplicate captions")
            # calculations
            internal_to_caption = {c.get("name"): c.get("caption") for c in cols.values()}
            for c in [c for c in CALCS if c["ds"] == ds]:
                n_calc += 1
                el = cols.get(f"[RP_{c['id']}]")
                if el is None or el.find("calculation") is None:
                    f_bad.append(f"{c['id']} missing")
                    continue
                formula = el.find("calculation").get("formula")
                for tok in re.findall(r"\[([^\]]+)\]", formula):
                    if tok == "Parameters":
                        continue
                    if f"[{tok}]" not in cols and tok not in PARAMETERS:
                        ref_bad.append(f"{c['id']}: [{tok}]")
                back = formula.replace("[Parameters].[", "[")
                back = re.sub(r"\[([^\]]+)\]", lambda mm: f"[{internal_to_caption.get('[' + mm.group(1) + ']', mm.group(1))}]", back)
                if el.get("caption") != c["name"] or back != c["formula"]:
                    f_bad.append(f"{c['id']} differs from the validated formula")
                if c["fmt"] in B.FORMATS and el.get("default-format") != B.FORMATS[c["fmt"]]:
                    fmt_bad.append(c["id"])
        ck("data", "connections point at existing folders; columns = CSV headers; declared types hold for every value",
           not data_bad, "; ".join(data_bad[:5]) or "14 tables")
        ck("model", "the 8 relationships of data_model.md, keys on both sides", not rel_bad and n_rel == 8,
           "; ".join(rel_bad[:5]) or f"{n_rel} relationships")
        ck("model", "every column caption equals the documented field name (28 renames included); no duplicates",
           not cap_bad, "; ".join(cap_bad[:5]) or "all captions match")
        ck("formulas", f"all 100 calculated fields present; formulas identical to the validated registry ({n_calc})",
           not f_bad and n_calc == len(CALCS), "; ".join(f_bad[:5]) or "identical")
        ck("formulas", "every field reference in every formula resolves in its data source", not ref_bad,
           "; ".join(ref_bad[:5]) or "all resolve")
        ck("formulas", "BRL / percentage / number formats set on every formatted field", not fmt_bad, f"{fmt_bad or 'all set'}")
        params = {c.get("caption"): c for c in ds_els["Parameters"].findall("column")}
        ck("formulas", "2 parameters with allowable values 'any' and the documented current values",
           set(params) == set(PARAMETERS) and all(params[p].get("param-domain-type") == "any"
                                                   and params[p].get("value") == f'"{PARAMETERS[p][1]}"' for p in PARAMETERS))

        # ---- worksheets --------------------------------------------------------------------------
        sheets = wb.find("worksheets").findall("worksheet")
        windows = {w.get("name") for w in wb.find("windows")}
        sh_bad = []
        for ws in sheets:
            deps = ws.find(".//datasource-dependencies")
            declared = {c.get("name") for c in deps.findall("column")}
            instances = {i.get("name"): i.get("column") for i in deps.findall("column-instance")}
            for col in deps.findall("column"):
                calc = col.find("calculation")
                if calc is not None:
                    for tok in re.findall(r"\[([^\]]+)\]", calc.get("formula")):
                        if tok != "Parameters" and f"[{tok}]" not in declared and tok not in PARAMETERS:
                            sh_bad.append(f"{ws.get('name')}: [{tok}] not declared")
            for inst, col in instances.items():
                if col not in declared:
                    sh_bad.append(f"{ws.get('name')}: instance {inst} without column")
            for g in ws.findall(".//groupfilter[@function='member']"):
                member = g.get("member").strip('"').split("].", 1)[1]
                if member not in instances:
                    sh_bad.append(f"{ws.get('name')}: member {member}")
            if ws.get("name") not in windows:
                sh_bad.append(f"{ws.get('name')}: no window")
        ck("sheets", f"{len(sheets)} KPI check sheets: dependencies declared, members resolve, windows present",
           not sh_bad and len(sheets) == len(B.KPI_SHEETS), "; ".join(sh_bad[:5]) or ", ".join(w.get("name") for w in sheets))
        ck("sheets", "sort elements are declared in the manifest (<SortTagCleanup />), as Tableau 2026.3.2 requires",
           all(sort_flag_ok(p) for p in files.values()))
        text = files["RetailPulse.twb"].read_text(encoding="utf-8")
        ck("other", "no credentials in the workbook (empty password attributes only)",
           not re.search(r"password='[^']+'", text) and "MYSQL" not in text)
    return finish()


def finish():
    for area, name, ok, detail in R:
        print(f"  {'PASS' if ok else 'FAIL'}  [{area}] {name}" + (f"  — {detail}" if detail else ""))
    n = sum(r[2] for r in R)
    print(f"checks: {len(R)}   PASS: {n}   FAIL: {len(R) - n}")
    print("SCOPE: structure and content checked against Tableau's XSD and the validated registry. NOT verified: that "
          "Tableau Desktop opens the workbook (manual step).")
    sys.exit(0 if n == len(R) else 1)


if __name__ == "__main__":
    main()
