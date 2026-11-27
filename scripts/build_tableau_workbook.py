"""
RetailPulse - generate the Tableau workbook (.twb) from the validated registry.

WHAT IT WRITES
  tableau/RetailPulse.twb             6 data sources + 2 parameters + 100 calculated fields
                                      + 8 KPI check sheets (sheet names from the dashboard spec)
  tableau/RetailPulse_model_only.twb  the same model with one empty sheet: a fallback if
                                      the KPI sheets ever stop the workbook from opening

  For every data source: the text-file connections (tableau/data and
  tableau/data/analytical), the tables in the order of the registry, the
  relationships (root table to each related table, on the documented key),
  every column with its data type, role and FINAL caption (CSV name, or the
  documented rename such as rev_order_id), and the calculated fields with
  their number formats. Field and calculation names are exactly those in
  tableau/calculated_fields.md, so nothing has to be renamed or retyped.

HOW THE FORMAT WAS DETERMINED (no guessing)
  The XML mirrors what Tableau Desktop Public Edition 2026.3.2 itself writes:
  element order, attributes, internal names for duplicate columns
  ("[order_id (vw_review_summary.csv)]"), metadata-record type codes and the
  relationship ("object-graph") syntax were copied from a workbook saved by
  that build, and calculated-field / parameter / worksheet markup from the
  Superstore sample shipped with it. scripts/validate_tableau_workbook.py
  checks the result against Tableau's official 2026.3 XSD and against the
  registry.

WHAT IS NOT GENERATED (built by hand from tableau/dashboard_specification.md)
  chart worksheets, the 8 dashboards, filters, dashboard actions, formatting.

PATHS
  Tableau stores the absolute folder of each CSV. The default is this
  repository's tableau/data; pass --data-dir to point elsewhere. The generated
  .twb files are git-ignored (they contain this machine's path); re-run the
  script on any machine to regenerate them.

Usage:
  ./venv/bin/python scripts/build_tableau_workbook.py
  ./venv/bin/python scripts/build_tableau_workbook.py --data-dir /path/to/tableau/data
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys
import uuid
import xml.etree.ElementTree as ET

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tableau_registry import (BRL, CALCS, DATA_SOURCES, DAYS, DEC2, FIELDS, HEADERS, INT,  # noqa: E402
                              PARAMETERS, PCT, TAB)

SOURCE_BUILD = "2026.3.2 (20263.26.1120.1648)"     # the installed Tableau Desktop Public Edition
VERSION = "18.1"                                   # the document version that build writes
MANIFEST = ["AnimationOnByDefault", "MarkAnimation", "ObjectModelEncapsulateLegacy", "ObjectModelTableType",
            "SchemaViewerObjectModel", "SheetIdentifierTracking", "WindowsPersistSimpleIdentifiers"]
# Declared only when the workbook contains <manual-sort>/<computed-sort>: without it Tableau
# 2026.3.2 reads sorts in the older format and rejects <manual-sort> (error D2E8DA72). The
# Superstore sample shipped with that build declares it alongside its 14 <manual-sort> elements.
SORT_FLAG = "SortTagCleanup"
REMOTE_TYPE = {"string": "129", "integer": "20", "real": "5", "date": "133", "datetime": "135"}
AGGREGATION = {"string": "Count", "integer": "Sum", "real": "Sum", "date": "Year", "datetime": "Year"}
# numeric columns used as discrete axes (dimension), as the dashboard specification requires
NUMERIC_DIMENSIONS = {"months_since_acquisition", "review_score", "total_orders", "stage_order", "order_year",
                      "r_score", "f_score", "m_score"}
FORMATS = {BRL: 'c"R$ "#,##0.00;-"R$ "#,##0.00', PCT: "p0.00%", INT: "n#,##0", DEC2: "n#,##0.0000",
           DAYS: "n#,##0.00"}

# KPI check sheets: (sheet name from the specification, data source, measure IDs in display order)
KPI_SHEETS = [
    ("1.0 KPIs", "RP Orders", ["M01", "M02", "M03", "M06", "M07"]),
    ("1.5 YoY Jan–Aug", "RP Orders", ["M15", "M13", "M14"]),
    ("2.0 KPIs", "RP Customers", ["M16", "M19", "M18", "M20", "M21"]),
    ("3.0 KPIs", "RP Categories", ["M24", "M26", "M25", "N07"]),
    ("4.0 KPIs", "RP Sellers", ["M30", "M29", "M34", "M32", "M33"]),
    ("5.0 KPIs", "RP Orders", ["M36", "M40", "M41", "M38", "M44", "M08"]),
    ("5.6 Stage Shares", "RP Orders", ["N24", "N23", "N22", "N21", "N17"]),
    ("6.0 KPIs", "RP Orders", ["M46", "M47", "M48", "M45", "N25"]),
]


# ---- deterministic identifiers (same input -> same file) -----------------------------
def _h(text: str, n: int, alphabet: str) -> str:
    digest = int(hashlib.sha256(text.encode()).hexdigest(), 16)
    out = []
    for _ in range(n):
        digest, r = divmod(digest, len(alphabet))
        out.append(alphabet[r])
    return "".join(out)


LOWER = "0123456789abcdefghijklmnopqrstuvwxyz"
federated_name = lambda ds: "federated." + _h("ds:" + ds, 28, LOWER)
textscan_name = lambda ds, folder: "textscan." + _h(f"conn:{ds}:{folder}", 28, LOWER)
object_id = lambda ds, t: f"{t}.csv_" + hashlib.md5(f"obj:{ds}:{t}".encode()).hexdigest().upper()
det_uuid = lambda key: "{" + str(uuid.UUID(hashlib.md5(key.encode()).hexdigest())).upper() + "}"


# ---- column types from the actual CSVs ----------------------------------------------------
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def infer_types(folder: Path, table: str) -> dict[str, str]:
    df = pd.read_csv(folder / f"{table}.csv", low_memory=False)
    types = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_integer_dtype(s):
            types[col] = "integer"
        elif pd.api.types.is_float_dtype(s):
            types[col] = "real"
        else:
            v = s.dropna().astype(str)
            if len(v) and v.str.match(DATE_RE).all():
                types[col] = "date"
            elif len(v) and v.str.match(DATETIME_RE).all():
                types[col] = "datetime"
            else:
                types[col] = "string"
    return types


def role_type(col: str, dtype: str) -> tuple[str, str]:
    if dtype == "string":
        return "dimension", "nominal"
    if dtype in ("date", "datetime"):
        return "dimension", "ordinal"
    if col in NUMERIC_DIMENSIONS:
        return "dimension", "ordinal"
    return "measure", "quantitative"


# ---- model of one data source ---------------------------------------------------------------
class SourceModel:
    """Tables, internal names, captions and types for one data source (Tableau's naming rules)."""

    def __init__(self, ds: str, data_dir: Path):
        self.ds = ds
        self.name = federated_name(ds)
        self.tables = DATA_SOURCES[ds]
        self.folder_of = {t: (data_dir if d.name == "data" else data_dir / "analytical") for t, d, _, _ in self.tables}
        self.folders = []
        for t, *_ in self.tables:
            f = self.folder_of[t]
            if f not in self.folders:
                self.folders.append(f)
        self.conn_of_folder = {f: textscan_name(ds, f.name) for f in self.folders}
        self.types = {t: infer_types(self.folder_of[t], t) for t, *_ in self.tables}
        caption_of = {(tbl, col): cap for cap, (tbl, col) in FIELDS[ds].items()}
        self.columns = []           # (table, col, internal, caption, dtype, ordinal)
        seen, ordinal = set(), 0
        for t, *_ in self.tables:
            for col in HEADERS[t]:
                internal = f"[{col}]" if col not in seen else f"[{col} ({t}.csv)]"
                seen.add(col)
                self.columns.append((t, col, internal, caption_of[(t, col)], self.types[t][col], ordinal))
                ordinal += 1
        self.internal_of_caption = {c[3]: c[2] for c in self.columns}
        self.col_by_internal = {c[2]: c for c in self.columns}
        self.calcs = [c for c in CALCS if c["ds"] == ds]
        self.calc_internal = {c["name"]: f"[RP_{c['id']}]" for c in self.calcs}

    def translate(self, formula: str) -> str:
        """Display names in the registry formula -> Tableau internal names."""
        def sub(m):
            tok = m.group(1)
            if tok in self.calc_internal:
                return self.calc_internal[tok]
            if tok in PARAMETERS:
                return f"[Parameters].[{tok}]"
            if tok in self.internal_of_caption:
                return self.internal_of_caption[tok]
            raise KeyError(f"{self.ds}: unknown reference [{tok}] in formula")
        return re.sub(r"\[([^\]]+)\]", sub, formula)

    def calc_datatype(self, c) -> tuple[str, str, str]:
        f = c["formula"]
        if c["kind"] == "row-level":
            if f.startswith("DATETRUNC"):
                return "date", "dimension", "ordinal"
            if f.startswith("CASE"):
                return "integer", "dimension", "ordinal"
            if "=" in f and " THEN " not in f:
                return "boolean", "dimension", "nominal"
            return "real", "measure", "quantitative"
        if c["id"] in ("H05", "H07", "H09"):
            return "boolean", "dimension", "nominal"
        if c["fmt"] == INT:
            if re.search(r"\b(COUNTD?|RANK_DENSE)\(", f):
                return "integer", "measure", "quantitative"
            refs = [self.col_by_internal.get(self.internal_of_caption.get(r)) for r in re.findall(r"\[([^\]]+)\]", f)]
            if refs and all(r is not None and r[4] == "integer" for r in refs):
                return "integer", "measure", "quantitative"
        return "real", "measure", "quantitative"

    def calc_deps(self, ids: list[str]) -> tuple[list, list]:
        """Transitive closure: calculations and base columns the given calculations use."""
        by_name = {c["name"]: c for c in self.calcs}
        calcs, cols, todo = {}, {}, [c for c in self.calcs if c["id"] in ids]
        while todo:
            c = todo.pop()
            if c["id"] in calcs:
                continue
            calcs[c["id"]] = c
            for tok in re.findall(r"\[([^\]]+)\]", c["formula"]):
                if tok in by_name:
                    todo.append(by_name[tok])
                elif tok in self.internal_of_caption:
                    cols[self.internal_of_caption[tok]] = self.col_by_internal[self.internal_of_caption[tok]]
        return list(calcs.values()), list(cols.values())


# ---- XML helpers ---------------------------------------------------------------------------
def sub(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k.replace("_", "-"): str(v) for k, v in attrs.items()})


def relation_el(parent, m: SourceModel, table: str):
    rel = sub(parent, "relation", connection=m.conn_of_folder[m.folder_of[table]], name=f"{table}.csv",
              table=f"[{table}#csv]", type="table")
    cols = sub(rel, "columns", character_set="UTF-8", header="yes", locale="en_US", separator=",")
    for i, col in enumerate(HEADERS[table]):
        sub(cols, "column", datatype=m.types[table][col], name=col, ordinal=i)
    return rel


def column_el(parent, internal, caption, dtype, role, typ, fmt=None):
    attrs = {"caption": caption, "datatype": dtype}
    if fmt:
        attrs["default-format"] = fmt
    attrs.update({"name": internal, "role": role, "type": typ})
    return ET.SubElement(parent, "column", attrs)


def calc_column_el(parent, m: SourceModel, c):
    dtype, role, typ = m.calc_datatype(c)
    el = column_el(parent, m.calc_internal[c["name"]], c["name"], dtype, role, typ, FORMATS.get(c["fmt"]))
    calc = sub(el, "calculation", **{"class": "tableau", "formula": m.translate(c["formula"])})
    if c["kind"] == "table calculation":
        sub(calc, "table-calc", ordering_type="Rows")
    return el


def datasource_el(parent, m: SourceModel):
    ds = sub(parent, "datasource", caption=m.ds, inline="true", name=m.name, version=VERSION)
    conn = sub(ds, "connection", **{"class": "federated"})
    named = sub(conn, "named-connections")
    for f in m.folders:
        nc = sub(named, "named-connection", caption=f.name, name=m.conn_of_folder[f])
        first = next(t for t, *_ in m.tables if m.folder_of[t] == f)
        sub(nc, "connection", **{"class": "textscan", "directory": str(f), "filename": f"{first}.csv",
                                 "password": "", "server": ""})
    if len(m.tables) == 1:
        relation_el(conn, m, m.tables[0][0])
    else:
        coll = sub(conn, "relation", type="collection")
        for t, *_ in m.tables:
            relation_el(coll, m, t)
        cols = sub(conn, "cols")
        for t, col, internal, *_ in sorted(m.columns, key=lambda c: c[2]):
            sub(cols, "map", key=internal, value=f"[{t}.csv].[{col}]")
    recs = sub(conn, "metadata-records")
    for t, *_ in m.tables:
        r = sub(recs, "metadata-record", **{"class": "capability"})
        for tag, val in [("remote-name", None), ("remote-type", "0"), ("parent-name", f"[{t}.csv]"),
                         ("remote-alias", None), ("aggregation", "Count"), ("contains-null", "true")]:
            e = sub(r, tag)
            if val is not None:
                e.text = val
        attrs = sub(r, "attributes")
        for k, v in [("character-set", '"UTF-8"'), ("collation", '"en_US"'), ("field-delimiter", '","'),
                     ("header-row", '"true"'), ("locale", '"en_US"'), ("single-char", '""')]:
            a = sub(attrs, "attribute", datatype="string", name=k)
            a.text = v
    for t, col, internal, caption, dtype, ordinal in m.columns:
        r = sub(recs, "metadata-record", **{"class": "column"})
        fields = [("remote-name", col), ("remote-type", REMOTE_TYPE[dtype]), ("local-name", internal),
                  ("parent-name", f"[{t}.csv]"), ("remote-alias", col), ("ordinal", str(ordinal)),
                  ("local-type", dtype), ("aggregation", AGGREGATION[dtype])]
        if dtype == "string":
            fields += [("scale", "1"), ("width", "1073741823")]
        fields += [("contains-null", "true")]
        for tag, val in fields:
            sub(r, tag).text = val
        if dtype == "string":
            sub(r, "collation", flag="0", name="LEN_RGB")
        sub(r, "object-id").text = f"[{object_id(m.ds, t)}]"
    sub(ds, "aliases", enabled="yes")
    if len(m.tables) > 1:
        for t, *_ in sorted(m.tables):
            column_el(ds, f"[__tableau_internal_object_id__].[{object_id(m.ds, t)}]", f"{t}.csv", "table",
                      "measure", "quantitative")
    entries = [(c[2], ("col", c)) for c in m.columns] + [(m.calc_internal[c["name"]], ("calc", c)) for c in m.calcs]
    for _, (kind, item) in sorted(entries, key=lambda e: e[0].lower()):
        if kind == "col":
            t, col, internal, caption, dtype, _ = item
            role, typ = role_type(col, dtype)
            column_el(ds, internal, caption, dtype, role, typ)
        else:
            calc_column_el(ds, m, item)
    sub(ds, "layout", dim_ordering="alphabetic", measure_ordering="alphabetic", show_structure="true")
    if len(m.tables) > 1:
        og = sub(ds, "object-graph")
        objs = sub(og, "objects")
        for t, *_ in m.tables:
            o = sub(objs, "object", caption=f"{t}.csv", id=object_id(m.ds, t))
            relation_el(sub(o, "properties", context=""), m, t)
        rels = sub(og, "relationships")
        root = m.tables[0][0]
        for t, _, key, _ in m.tables[1:]:
            rel = sub(rels, "relationship")
            e = sub(rel, "expression", op="=")
            sub(e, "expression", op=f"[{key}]")
            sub(e, "expression", op=f"[{key} ({t}.csv)]")
            sub(rel, "first-end-point", object_id=object_id(m.ds, root))
            sub(rel, "second-end-point", object_id=object_id(m.ds, t))
    return ds


def parameters_el(parent):
    ds = sub(parent, "datasource", hasconnection="false", inline="true", name="Parameters", version=VERSION)
    sub(ds, "aliases", enabled="yes")
    for name, (dtype, value, _) in PARAMETERS.items():
        col = ET.SubElement(ds, "column", {"caption": name, "datatype": dtype.lower(), "name": f"[{name}]",
                                           "param-domain-type": "any", "role": "measure", "type": "nominal",
                                           "value": f'"{value}"'})
        sub(col, "calculation", **{"class": "tableau", "formula": f'"{value}"'})


def empty_table(ws):
    table = sub(ws, "table")
    view = sub(table, "view")
    sub(view, "datasources")
    sub(view, "aggregation", value="true")
    sub(table, "style")
    pane = sub(sub(table, "panes"), "pane", selection_relaxation_option="selection-relaxation-allow")
    sub(sub(pane, "view"), "breakdown", value="auto")
    sub(pane, "mark", **{"class": "Automatic"})
    sub(table, "rows")
    sub(table, "cols")


def kpi_worksheet(parent, sheet: str, m: SourceModel, ids: list[str]):
    ws = sub(parent, "worksheet", name=sheet)
    table = sub(ws, "table")
    view = sub(table, "view")
    dss = sub(view, "datasources")
    sub(dss, "datasource", caption=m.ds, name=m.name)
    deps = sub(view, "datasource-dependencies", datasource=m.name)
    calcs, cols = m.calc_deps(ids)
    entries = [(c[2], ("col", c)) for c in cols] + [(m.calc_internal[c["name"]], ("calc", c)) for c in calcs]
    for _, (kind, item) in sorted(entries, key=lambda e: e[0].lower()):
        if kind == "col":
            t, col, internal, caption, dtype, _ = item
            role, typ = role_type(col, dtype)
            column_el(deps, internal, caption, dtype, role, typ)
        else:
            calc_column_el(deps, m, item)
    inst = {cid: f"[usr:RP_{cid}:qk]" for cid in ids}
    for cid in sorted(ids):
        sub(deps, "column-instance", column=f"[RP_{cid}]", derivation="User", name=inst[cid], pivot="key",
            type="quantitative")
    flt = sub(view, "filter", **{"class": "categorical", "column": f"[{m.name}].[:Measure Names]"})
    union = ET.SubElement(flt, "groupfilter", {"function": "union", "user:op": "manual"})
    for cid in ids:
        sub(union, "groupfilter", function="member", level="[:Measure Names]", member=f'"[{m.name}].{inst[cid]}"')
    ms = sub(view, "manual-sort", column=f"[{m.name}].[:Measure Names]", direction="ASC")
    dic = sub(ms, "dictionary")
    for cid in ids:
        sub(dic, "bucket").text = f'"[{m.name}].{inst[cid]}"'
    sub(view, "aggregation", value="true")
    sub(table, "style")
    pane = sub(sub(table, "panes"), "pane", selection_relaxation_option="selection-relaxation-allow")
    sub(sub(pane, "view"), "breakdown", value="auto")
    sub(pane, "mark", **{"class": "Text"})
    enc = sub(pane, "encodings")
    sub(enc, "text", column=f"[{m.name}].[Multiple Values]")
    sub(table, "rows")
    sub(table, "cols").text = f"[{m.name}].[:Measure Names]"
    sub(ws, "simple-id", uuid=det_uuid("ws:" + sheet))
    return ws


def window_el(parent, sheet: str, maximized: bool):
    attrs = {"class": "worksheet"}
    if maximized:
        attrs["maximized"] = "true"
    attrs["name"] = sheet
    w = ET.SubElement(parent, "window", attrs)
    cards = sub(w, "cards")
    left = sub(sub(cards, "edge", name="left"), "strip", size="160")
    for t in ("pages", "filters", "marks"):
        sub(left, "card", type=t)
    top = sub(cards, "edge", name="top")
    for size, t in (("2147483647", "columns"), ("2147483647", "rows"), ("31", "title")):
        sub(sub(top, "strip", size=size), "card", type=t)
    sub(w, "simple-id", uuid=det_uuid("win:" + sheet))


def build(data_dir: Path, with_kpi_sheets: bool) -> ET.ElementTree:
    wb = ET.Element("workbook", {"original-version": VERSION, "source-build": SOURCE_BUILD, "source-platform": "mac",
                                 "version": VERSION, "xmlns:user": "http://www.tableausoftware.com/xml/user"})
    man = sub(wb, "document-format-change-manifest")
    for f in sorted(MANIFEST + ([SORT_FLAG] if with_kpi_sheets else [])):
        sub(man, f)
    prefs = sub(wb, "preferences")
    sub(prefs, "preference", name="ui.encoding.shelf.height", value="24")
    sub(prefs, "preference", name="ui.shelf.height", value="26")
    dss = sub(wb, "datasources")
    parameters_el(dss)
    models = {ds: SourceModel(ds, data_dir) for ds in DATA_SOURCES}
    for m in models.values():
        datasource_el(dss, m)
    wss = sub(wb, "worksheets")
    sheets = []
    if with_kpi_sheets:
        for sheet, ds, ids in KPI_SHEETS:
            kpi_worksheet(wss, sheet, models[ds], ids)
            sheets.append(sheet)
    else:
        ws = sub(wss, "worksheet", name="Sheet 1")
        empty_table(ws)
        sub(ws, "simple-id", uuid=det_uuid("ws:Sheet 1"))
        sheets.append("Sheet 1")
    wins = sub(wb, "windows", source_height="30")
    for i, sheet in enumerate(sheets):
        window_el(wins, sheet, maximized=(i == 0))
    return ET.ElementTree(wb)


def write(tree: ET.ElementTree, path: Path):
    ET.indent(tree, space="  ")
    body = ET.tostring(tree.getroot(), encoding="unicode")
    body = body.replace(" />", " />")
    path.write_text("<?xml version='1.0' encoding='utf-8' ?>\n\n<!-- build 20263.26.1120.1648 "
                    "(generated by scripts/build_tableau_workbook.py) -->\n" + body + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Generate the RetailPulse Tableau workbook")
    ap.add_argument("--data-dir", type=Path, default=TAB / "data", help="folder holding the CSVs and analytical/")
    ap.add_argument("--out-dir", type=Path, default=TAB, help="where to write the .twb files")
    args = ap.parse_args()
    data_dir = args.data_dir.resolve()
    missing = [f"{t}.csv" for ds in DATA_SOURCES for t, d, _, _ in DATA_SOURCES[ds]
               if not ((data_dir if d.name == "data" else data_dir / "analytical") / f"{t}.csv").exists()]
    if missing:
        sys.exit(f"ABORT: missing CSV files under {data_dir}: {missing}. Run scripts/export_tableau_*.py first.")
    for name, kpi in (("RetailPulse.twb", True), ("RetailPulse_model_only.twb", False)):
        path = args.out_dir / name
        write(build(data_dir, kpi), path)
        print(f"wrote {path.relative_to(TAB.parent) if path.is_relative_to(TAB.parent) else path}  "
              f"({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
